"""Campagne : envoi au service, notation, points de reprise (agrégats seuls) / campaign runner with checkpoints.

Fils de travail (un par requête en vol, 3 par défaut : 2 en cours au service, plafond LOCAL, et 1 en file) et le fil
principal, qui lit `/status` toutes les 2 secondes (des visiteurs occupent ou attendent une place : une seule requête
en vol ; des compteurs qui baissent : le service a redémarré), contrôle le moteur, fusionne les unités terminées et
écrit le point de reprise de façon atomique et durable. Rien d'autre que des compteurs n'est écrit ni affiché :
jamais de texte, de valeur annotée ni de sortie du service.

Une campagne = un moteur. L'empreinte du moteur (image du service, version, packs, sorties sur une sonde fixe) est
prise au départ et recontrôlée à chaque point de reprise, après toute panne de connexion ou tout redémarrage du
service, et à la fin. Un soupçon de redémarrage abandonne les unités en cours (refaites ensuite) et bloque les
nouvelles jusqu'au contrôle ; une unité n'est fusionnée qu'après un relevé de `/status` sans redémarrage postérieur
à sa fin. Un moteur changé arrête la campagne sans rien écrire après le dernier contrôle réussi.

Worker threads (one per in-flight request) and the main thread, which reads `/status` every 2 seconds (visitors
holding or waiting for a slot: one request in flight; counters going down: the service restarted), checks the
engine, merges finished units and writes the checkpoint atomically and durably. Nothing but counters is ever written
or printed. One campaign = one engine: its fingerprint (service image, version, packs, outputs on a fixed probe) is
taken at start and checked again at every checkpoint, after any connection failure or service restart, and at the
end. A suspected restart drops the units in progress (redone later) and holds new ones until the check; a unit is
merged only after a `/status` reading without restart taken after it finished. A changed engine stops the campaign
without writing anything after the last passing check.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import shutil
import signal
import sys
import threading
import time
from collections import Counter, deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.corpus.real_common import split_of
from tools.protocol import spec
from tools.protocol.align import AlignmentError, align
from tools.protocol.outcomes import Cell, pack_bits, real_failure, score_real, score_synthetic, synthetic_failure
from tools.protocol.plan import Plan, Unit, mode_key, service_options, synthetic_documents, track
from tools.protocol.transport import (
    DocumentRefused,
    Gate,
    ServiceClient,
    ServiceDown,
    counters_total,
    local_principal,
    visitors_active,
)

CHECKPOINT = "checkpoint.json"
EXIT_DONE, EXIT_DOWN, EXIT_PAUSED, EXIT_REFUSED = 0, 3, 4, 5
# Empreintes de l'outil qui doivent rester les mêmes d'une reprise à l'autre / tool digests that must not change.
TOOL_KEYS = ("tools_sha256", "spec_sha256", "protocole_md_sha256", "faker")


class UnitAborted(RuntimeError):
    pass


class ProbeFailed(RuntimeError):
    """Un document de la sonde du moteur n'a pas été rendu (code HTTP seulement) / a probe document failed."""


@dataclass(slots=True)
class UnitResult:
    uid: str
    cells: dict[str, Cell]
    bits: list[int]
    digest: str
    docs: int
    seconds: float
    epoch: int = 0
    finished: float = 0.0


@dataclass(slots=True)
class State:
    """Point de reprise : agrégats, unités faites, empreintes ; jamais de contenu / checkpoint, never content."""

    plan_id: str
    started: str
    engine: dict[str, Any]
    real_sources: dict[str, str] = field(default_factory=dict)
    done: dict[str, dict[str, Any]] = field(default_factory=dict)
    cells: dict[str, Cell] = field(default_factory=dict)
    active_s: float = 0.0
    retries: Counter[str] = field(default_factory=Counter)
    throttled_s: float = 0.0
    runs: list[dict[str, Any]] = field(default_factory=list)
    tool: dict[str, Any] = field(default_factory=dict)
    engine_checks: int = 0
    engine_check_docs: int = 0
    real_wiped: bool = False
    disclosures: list[str] = field(default_factory=list)   # écarts à déclarer (spec.DISCLOSURES) / to disclose
    protocol: str = "1.1"                                   # version du plan (1.2 : avec modes) / the plan's version
    modes: list[str] = field(default_factory=list)          # modes déclarés (1.2) / declared modes (1.2)

    def disclose(self, items: list[str] | tuple[str, ...]) -> None:
        """Ajoute des écarts à déclarer, sans doublon ; code inconnu refusé / adds departures to disclose."""
        for item in items:
            check_disclosure(item)
            if item not in self.disclosures:
                self.disclosures.append(item)

    def merge(self, result: UnitResult) -> None:
        for key, cell in result.cells.items():
            self.cells.setdefault(key, Cell()).merge(cell)
        self.done[result.uid] = {"docs": result.docs, "bits": pack_bits(result.bits), "n": len(result.bits),
                                 "digest": result.digest, "seconds": round(result.seconds, 3)}

    @property
    def docs(self) -> int:
        return sum(item["docs"] for item in self.done.values())

    def to_json(self) -> dict[str, Any]:
        out = {"protocol": self.protocol, "plan_id": self.plan_id, "started": self.started,
               "engine": self.engine, "tool": self.tool, "real_sources": self.real_sources, "done": self.done,
               "cells": {k: c.to_json() for k, c in sorted(self.cells.items())}, "active_s": round(self.active_s, 3),
               "retries": dict(self.retries), "throttled_s": round(self.throttled_s, 3), "runs": self.runs,
               "engine_checks": self.engine_checks, "engine_check_docs": self.engine_check_docs,
               "real_wiped": self.real_wiped, "disclosures": self.disclosures}
        if self.modes:
            out["modes"] = list(self.modes)
        return out

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> State:
        # Un point de reprise 1.1 (sans modes) se relit encore / a 1.1 checkpoint (no modes) still loads.
        protocol = data.get("protocol")
        if protocol not in spec.SUPPORTED_VERSIONS:
            raise SystemExit("point de reprise d'une autre version du protocole / checkpoint of another version")
        modes = list(data.get("modes", []))
        if bool(modes) != (protocol != "1.1"):
            raise SystemExit("point de reprise incohérent : modes et version du protocole / inconsistent checkpoint")
        return cls(plan_id=data["plan_id"], started=data["started"], engine=data["engine"],
                   real_sources=data.get("real_sources", {}), done=data["done"],
                   cells={k: Cell.from_json(v) for k, v in data["cells"].items()}, active_s=data["active_s"],
                   retries=Counter(data.get("retries", {})), throttled_s=data.get("throttled_s", 0.0),
                   runs=data.get("runs", []), tool=data.get("tool", {}),
                   engine_checks=data.get("engine_checks", 0), engine_check_docs=data.get("engine_check_docs", 0),
                   real_wiped=data.get("real_wiped", False), disclosures=list(data.get("disclosures", [])),
                   protocol=str(protocol), modes=modes)


def check_disclosure(item: str) -> str:
    """« code » ou « code:détail » (sans espace), code de spec.DISCLOSURES / "code" or "code:detail", known code."""
    code, _, detail = item.partition(":")
    if code not in spec.DISCLOSURES or any(c.isspace() for c in detail) or len(item) > 200:
        raise ValueError(f"écart inconnu / unknown disclosure: {code!r} (connus / known: "
                         f"{', '.join(sorted(spec.DISCLOSURES))})")
    return item


# --- Point de reprise durable / durable checkpoint -------------------------------------------------------------------


def _write_durable(path: Path, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())


def _fsync_dir(folder: Path) -> None:
    if os.name != "posix":
        return
    fd = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_state(state: State, work: Path) -> None:
    """Écriture atomique et durable ; le précédent est COPIÉ (jamais déplacé) en `.prev` avant.

    Atomic, durable write; the previous checkpoint is COPIED (never moved) to `.prev` first: at every instant a complete
    checkpoint exists on disk, and a power loss falls back to `.prev`.
    """
    path = work / CHECKPOINT
    data = (json.dumps(state.to_json(), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if path.exists():
        prev_part = work / (CHECKPOINT + ".prev.part")
        with open(path, "rb") as src, open(prev_part, "wb") as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(prev_part, work / (CHECKPOINT + ".prev"))
    part = work / (CHECKPOINT + ".part")
    _write_durable(part, data)
    os.replace(part, path)
    _fsync_dir(work)


def load_state(work: Path, log: Callable[[str], None] | None = None) -> State | None:
    """Point de reprise, ou le précédent s'il est illisible ; None : dossier neuf / checkpoint, else the previous one.

    Refuse de repartir de zéro quand un point de reprise existe mais qu'aucun n'est lisible.
    Refuses to restart from zero when a checkpoint exists but none can be read.
    """
    found = False
    for name in (CHECKPOINT, CHECKPOINT + ".prev"):
        path = work / name
        if not path.exists():
            continue
        found = True
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            if log is not None:
                log(f"point de reprise illisible / unreadable checkpoint: {name}")
            continue
        if name != CHECKPOINT and log is not None:
            log("point de reprise précédent utilisé / previous checkpoint used")
        return State.from_json(data)
    if found:
        raise SystemExit("aucun point de reprise lisible : refus de repartir de zéro dans ce dossier / no readable "
                         "checkpoint: refusing to restart from zero in this folder")
    return None


# --- Empreinte du moteur / engine fingerprint ------------------------------------------------------------------------

_PROBE_TEXTS: list[tuple[str, str]] = []
_PROBE_LOCK = threading.Lock()


def _probe_texts(count: int) -> list[tuple[str, str]]:
    """Documents de la sonde (graine de développement, jamais notés), gardés en mémoire / probe documents, in memory."""
    with _PROBE_LOCK:
        if len(_PROBE_TEXTS) < count:
            from tools.eval.generate import CorpusGenerator

            generator = CorpusGenerator(spec.ENGINE_PROBE_SEED)
            for index in range(len(_PROBE_TEXTS), count):
                doc = generator.document(index)
                _PROBE_TEXTS.append((doc.doc_id, doc.text))
        return _PROBE_TEXTS[:count]


def probe_digest(client: ServiceClient, count: int = spec.ENGINE_PROBE_DOCS, modes: Sequence[str] = ()) -> str:
    """SHA-256 des sorties du service sur la sonde (jamais conservées) / digest of the service's probe outputs.

    Plan 1.2 : la sonde passe dans chaque mode déclaré (le nom du mode entre dans l'empreinte) ; plan 1.1 : comme
    avant. 1.2 plan: the probe goes through every declared mode (its name enters the digest); 1.1 plan: as before.
    """
    digest = hashlib.sha256()
    for mode in tuple(modes) or (None,):
        options = service_options(spec.FRENCH_COUNTRIES, mode)
        for doc_id, text in _probe_texts(count):
            try:
                output = client.anonymize(text, options)
            except DocumentRefused as exc:
                raise ProbeFailed(exc.kind) from None
            track(digest, doc_id if mode is None else f"{mode}{spec.MODE_SEP}{doc_id}", output)
    return digest.hexdigest()


def engine_fingerprint(client: ServiceClient, image: str | None = None,
                       probe_docs: int = spec.ENGINE_PROBE_DOCS, modes: Sequence[str] = ()) -> dict[str, Any]:
    """Image (run-protocol.sh), version (/health), packs (/v1/packs) et sorties sur la sonde / engine fingerprint."""
    health = client.get_json("/health")
    packs = client.get_json("/v1/packs")
    digest = hashlib.sha256(json.dumps(packs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"version": str(health.get("version")), "packs_sha256": digest, "image": image,
            "probe_docs": probe_docs,
            "probe_sha256": probe_digest(client, probe_docs, modes) if probe_docs else None}


def _differences(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[str]:
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


class EngineWatch:
    """Soupçon de redémarrage du service / suspected service restart.

    `suspect` (panne de connexion, compteurs de /status en baisse) change d'époque : toute unité commencée avant est
    abandonnée (refaite plus tard) et aucune nouvelle ne part tant que le fil principal n'a pas recontrôlé le moteur.
    `suspect` (connection failure, /status counters going down) starts a new epoch: every unit started before is
    dropped (redone later) and no new one starts until the main thread has checked the engine again.
    """

    def __init__(self) -> None:
        self.epoch = 0
        self.reasons: Counter[str] = Counter()
        self.suspected = threading.Event()
        self.open = threading.Event()
        self.open.set()
        self._lock = threading.Lock()

    def suspect(self, reason: str) -> None:
        with self._lock:
            if not self.suspected.is_set():
                self.epoch += 1
                self.reasons[reason] += 1
                self.open.clear()
                self.suspected.set()

    def resolve(self) -> None:
        with self._lock:
            self.suspected.clear()
            self.open.set()

    def wait_open(self, stop: threading.Event) -> bool:
        while not self.open.wait(0.2):
            if stop.is_set():
                return False
        return not stop.is_set()


# --- Unité de travail / work unit ------------------------------------------------------------------------------------

# Exceptions qui interrompent l'unité au lieu de compter le document / exceptions that stop the unit.
_STOP_UNIT = (UnitAborted, ServiceDown)


class Worker:
    """Contexte d'un fil : client du service, générateurs (Faker n'est pas partagé entre fils) / per-thread context."""

    def __init__(self, client: ServiceClient, label_keys: Mapping[str, str],
                 real: Mapping[str, list[dict[str, Any]]], abort: threading.Event,
                 watch: EngineWatch | None = None, modes: Sequence[str] = ()) -> None:
        self.client = client
        self.label_keys = label_keys
        self.real = real
        self.abort = abort
        self.watch = watch
        # Plan 1.2 : chaque document passe une fois par mode ; plan 1.1 : une fois, sans mode / once per mode (1.2).
        self.modes: tuple[str | None, ...] = tuple(modes) or (None,)
        self._epoch = 0
        self._generators: dict[int, Any] = {}

    def _generator(self, seed: int) -> Any:
        if seed not in self._generators:
            from tools.eval.generate import CorpusGenerator
            self._generators[seed] = CorpusGenerator(seed)
        return self._generators[seed]

    def _send(self, text: str, countries: str, mode: str | None = None) -> str:
        watch = self.watch
        if self.abort.is_set() or (watch is not None and (watch.epoch != self._epoch or not watch.open.is_set())):
            raise UnitAborted
        return self.client.anonymize(text, service_options(countries, mode))

    def run(self, unit: Unit) -> UnitResult:
        """Une unité ; un document en échec (HTTP, alignement, exception) compte comme une fuite, jamais ne l'arrête.

        One unit; a failed document (HTTP, alignment, exception) counts as a leak and never stops it. Plan 1.2 : chaque
        document est envoyé et noté une fois par mode, dans les cellules de ce mode ; l'empreinte de ce qui est envoyé
        le compte une fois (mêmes empreintes que le décompte à blanc). 1.2 plan: every document is sent and scored once
        per mode, in that mode's cells; the sent-content fingerprint counts it once (same as the dry run).
        """
        started = time.monotonic()
        self._epoch = self.watch.epoch if self.watch is not None else 0
        cells: dict[str, Cell] = {}
        bits: list[int] = []
        docs = 0
        digest = hashlib.sha256()

        def cell(key: str) -> Cell:
            return cells.setdefault(key, Cell())

        def synthetic(doc: Any, key: str, baseline: list[bool] | None = None,
                      mode: str | None = None) -> list[bool] | None:
            target = cell(mode_key(mode, key))
            target.docs += 1
            target.chars += len(doc.text)
            try:
                output = self._send(doc.text, spec.FRENCH_COUNTRIES, mode)
                alignment = align(doc.text, output)
                flags, leak = score_synthetic(target, doc, output, alignment, self.label_keys, baseline)
            except _STOP_UNIT:
                raise
            except DocumentRefused as exc:
                kind = exc.kind
            except AlignmentError:
                kind = "alignment"
            except Exception as exc:  # erreur de notation : comptée comme fuite, jamais muette / counted as a leak
                kind = f"exception:{type(exc).__name__}"
            else:
                bits.append(leak)
                return flags
            bits.append(synthetic_failure(target, doc, kind))
            return None

        if unit.kind in ("synthetic", "redteam"):
            flags: dict[str | None, list[bool] | None] = {}
            for key, doc, is_base in synthetic_documents(unit, self._generator(unit.seed or 0)):
                docs += 1
                track(digest, doc.doc_id, doc.text)
                for mode in self.modes:
                    if is_base:
                        flags[mode] = synthetic(doc, key, None, mode)
                    else:
                        synthetic(doc, key, flags.get(mode) if unit.kind == "redteam" else None, mode)
        elif unit.kind == "real":
            corpus = unit.corpus or ""
            records = self.real[corpus]
            countries = spec.REAL_CORPORA[corpus]
            for record in records[unit.start:unit.start + unit.count]:
                docs += 1
                track(digest, record["id"], record["text"])
                for mode in self.modes:
                    target = cell(mode_key(mode, f"{corpus}/{split_of(record['id'])}"))
                    target.docs += 1
                    target.chars += len(record["text"])
                    try:
                        output = self._send(record["text"], countries, mode)
                        alignment = align(record["text"], output)
                        leak = score_real(target, record, output, alignment, spec.REAL_DIRECT_LABELS)
                    except _STOP_UNIT:
                        raise
                    except DocumentRefused as exc:
                        kind = exc.kind
                    except AlignmentError:
                        kind = "alignment"
                    except Exception as exc:  # comptée comme fuite / counted as a leak
                        kind = f"exception:{type(exc).__name__}"
                    else:
                        bits.append(leak)
                        continue
                    bits.append(real_failure(target, record, kind, spec.REAL_DIRECT_LABELS))
        else:
            raise ValueError(unit.kind)
        # Bits : un par document et par mode, dans l'ordre d'envoi / one bit per document and mode, in sending order.
        return UnitResult(unit.uid, cells, bits, digest.hexdigest(), docs, time.monotonic() - started,
                          self._epoch, time.monotonic())


# --- Campagne / campaign ---------------------------------------------------------------------------------------------


@dataclass(slots=True)
class Settings:
    work: Path
    threads: int = spec.CLIENT_THREADS
    hours: float | None = None
    checkpoint_s: float = spec.CHECKPOINT_S
    progress_s: float = 30.0
    status_s: float = 2.0
    tick_s: float = 0.2                   # boucle du fil principal / main-thread loop
    log: Callable[[str], None] = lambda line: print(line, file=sys.stderr, flush=True)
    engine_id: str | None = None          # image du conteneur du service (run-protocol.sh) / service image id
    require_local: bool = False           # plan standard : jeton local obligatoire / standard plan: local token
    probe_docs: int = spec.ENGINE_PROBE_DOCS
    wipe_real: Path | None = None         # paquet effacé dès les unités réelles faites / pack wiped once real done
    tool: dict[str, Any] | None = None    # provenance de l'outil / tool provenance
    disclosures: tuple[str, ...] = ()     # écarts à déclarer (spec.DISCLOSURES) / departures to disclose


def run_campaign(plan: Plan, settings: Settings, make_client: Callable[[Gate | None], ServiceClient],
                 label_keys: Mapping[str, str], real: Mapping[str, list[dict[str, Any]]] | None = None,
                 real_sources: Mapping[str, str] | None = None) -> int:
    """Lance ou reprend la campagne ; code de sortie 0 (terminée), 3 (service absent), 4 (pause), 5 (refus).

    Runs or resumes the campaign; exit code 0 (complete), 3 (service down), 4 (paused), 5 (refused).
    """
    work = settings.work
    work.mkdir(parents=True, exist_ok=True)
    log = settings.log
    watch = EngineWatch()
    clients: list[ServiceClient] = []

    def watched(gate: Gate | None) -> ServiceClient:
        client = make_client(gate)
        client.on_connection_error = watch.suspect
        clients.append(client)
        return client

    probe = watched(None)
    try:
        local = local_principal(probe)
    except (DocumentRefused, ServiceDown) as exc:
        log(f"service : sonde profonde en échec ({exc}) / service deep probe failed")
        return EXIT_DOWN
    if not local:
        if settings.require_local:
            log("refus : le service ne reconnaît pas le jeton local (requêtes vues comme publiques) ; vérifier "
                "--token-stdin et le fichier d'en-tête local / refused: the service does not accept the local token "
                "(requests seen as public); check --token-stdin and the local header file")
            return EXIT_REFUSED
        log("ATTENTION : jeton local absent ou refusé, requêtes comptées comme publiques (essai seulement) / "
            "WARNING: local token missing or refused, requests counted as public (trial only)")
    try:
        engine = engine_fingerprint(probe, settings.engine_id, settings.probe_docs, plan.modes)
    except (ServiceDown, ProbeFailed) as exc:
        log(f"service : empreinte du moteur impossible ({type(exc).__name__} {exc}) / engine fingerprint failed")
        return EXIT_DOWN
    tool = dict(settings.tool or {})
    state = load_state(work, log)
    if state is None:
        state = State(plan.plan_id, datetime.now(UTC).date().isoformat(), engine, dict(real_sources or {}),
                      tool=tool, protocol=plan.protocol, modes=list(plan.modes))
    else:
        if (state.protocol, state.modes) != (plan.protocol, list(plan.modes)):
            log("refus : le point de reprise vient d'une autre version ou d'autres modes / refused: checkpoint of "
                "another protocol version or other modes")
            return EXIT_REFUSED
        if state.plan_id != plan.plan_id:
            log("refus : le point de reprise vient d'un autre plan / refused: checkpoint of another plan")
            return EXIT_REFUSED
        if state.engine != engine:
            log("refus : le moteur du service a changé depuis le début de la campagne (une campagne = un moteur ; "
                f"diffère : {', '.join(_differences(state.engine, engine))}) ; redéployer le moteur de la campagne ou "
                "repartir d'un dossier vide / refused: the service engine changed since the campaign started")
            return EXIT_REFUSED
        changed_tool = [k for k in TOOL_KEYS if state.tool.get(k) != tool.get(k)] if state.tool or tool else []
        if changed_tool:
            log(f"refus : l'outil a changé depuis le début de la campagne ({', '.join(changed_tool)}) / "
                "refused: the tool changed since the campaign started")
            return EXIT_REFUSED
    pending = deque(u for u in plan.units if u.uid not in state.done)
    if not pending:
        log("refus : campagne déjà terminée dans ce dossier (résultats dans results/, `report` les réécrit) ; une "
            "nouvelle campagne part d'un dossier vide (run-protocol.sh finish archive celui-ci) / refused: campaign "
            "already complete in this folder; a new campaign starts from an empty folder")
        return EXIT_REFUSED
    if any(u.kind == "real" for u in pending):
        if real is None:
            log("refus : corpus réels requis pour les unités restantes (--real) / real corpora required")
            return EXIT_REFUSED
        for corpus, digest in (real_sources or {}).items():
            if state.real_sources.get(corpus, digest) != digest:
                log(f"refus : corpus réel différent de celui du début / refused: different real corpus ({corpus})")
                return EXIT_REFUSED
        state.real_sources.update(real_sources or {})
    state.disclose(settings.disclosures)
    run_info: dict[str, Any] = {"started": datetime.now(UTC).isoformat(timespec="seconds"),
                                "units_pending": len(pending), "threads": settings.threads, "local_principal": local}
    state.runs.append(run_info)
    state.engine_checks += 1
    state.engine_check_docs += settings.probe_docs * max(len(plan.modes), 1)
    save_state(state, work)  # point de reprise dès le départ / a checkpoint from the very start

    gate = Gate(settings.threads)
    abort = threading.Event()
    no_new = threading.Event()
    lock = threading.Lock()
    results: deque[tuple[str, Unit, UnitResult | None]] = deque()
    outcome: dict[str, str] = {}
    deadline = time.monotonic() + settings.hours * 3600 if settings.hours else None
    checker = watched(gate)          # sonde en cours de campagne, sous le même plafond / probe under the same cap
    checker.priority = True          # prioritaire au portillon / first at the gate
    status_client = watched(None)    # /status : une seule nouvelle tentative / one retry only
    status_client.policy = dataclasses.replace(status_client.policy, down_s=0.0)

    def on_signal(_signum: int, _frame: object) -> None:
        abort.set()
        no_new.set()

    previous = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, on_signal)

    def stop(kind: str, detail: str) -> None:
        outcome.setdefault(kind, detail)
        abort.set()
        no_new.set()

    def work_loop() -> None:
        worker = Worker(watched(gate), label_keys, real or {}, abort, watch, plan.modes)
        while not no_new.is_set():
            if not watch.wait_open(no_new):
                return
            with lock:
                if not pending:
                    return
                unit = pending.popleft()
            try:
                result = worker.run(unit)
            except UnitAborted:
                results.append(("aborted", unit, None))
                continue
            except ServiceDown as exc:
                stop("down", f"{type(exc).__name__} {exc}")
                results.append(("aborted", unit, None))
                return
            except Exception as exc:  # jamais un fil qui meurt en silence / never a thread dying silently
                stop("crash", f"{unit.uid}: {type(exc).__name__}")
                results.append(("aborted", unit, None))
                return
            results.append(("done", unit, result))

    def check_engine(when: str) -> bool:
        """Recontrôle ; False et `outcome["changed"]` si le moteur a changé / check again; False if it changed."""
        current = engine_fingerprint(checker, settings.engine_id, settings.probe_docs, plan.modes)
        state.engine_checks += 1
        state.engine_check_docs += settings.probe_docs * max(len(plan.modes), 1)
        if current != state.engine:
            stop("changed", f"{when}: {', '.join(_differences(state.engine, current))}")
            return False
        return True

    def guarded_check(when: str) -> bool:
        try:
            return check_engine(when)
        except (ServiceDown, ProbeFailed) as exc:
            stop("down", f"{type(exc).__name__} {exc}")
            return False

    def wipe_real_pack() -> None:
        target = settings.wipe_real
        if state.real_wiped or target is None or any(u.kind == "real" and u.uid not in state.done
                                                     for u in plan.units):
            return
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            log(f"ATTENTION : paquet des corpus réels non effacé ({type(exc).__name__}) / WARNING: pack not wiped")
            return
        if isinstance(real, dict):
            real.clear()
        state.real_wiped = True
        # Enregistré tout de suite : un arrêt brutal ou la fin de la campagne ne doivent pas laisser « non effacé ».
        # Saved at once: an abrupt stop or the end of the campaign must not leave "not wiped" on disk. Rien d'autre n'a
        # changé depuis l'enregistrement qui précède, fait après un contrôle du moteur réussi / nothing else changed
        # since the save just before, made after a passing engine check.
        save_state(state, work)
        log("corpus réels faits : paquet effacé de la mémoire vive / real corpora done: pack wiped from RAM")

    threads = [threading.Thread(target=work_loop, name=f"protocol-{i}", daemon=True) for i in range(settings.threads)]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    last_save = last_progress = time.monotonic()
    last_status = -math.inf
    clean_since = -math.inf          # début du dernier relevé sans redémarrage / start of the last clean reading
    last_total: int | None = None
    busy_streak = calm = 0
    docs_at_start = state.docs
    active_at_start = state.active_s
    throttled_at_start = state.throttled_s
    retries_at_start = Counter(state.retries)
    total_units = len(plan.units)

    def save(now: float) -> None:
        state.active_s = active_at_start + (now - started)
        state.throttled_s = throttled_at_start + gate.throttled_s
        _merge_retries(state, retries_at_start, clients, watch)
        save_state(state, work)
        wipe_real_pack()

    try:
        while True:
            alive = any(t.is_alive() for t in threads)
            now = time.monotonic()
            # 1. /status : visiteurs, redémarrage / visitors, restart. Deux relevés de suite avec un visiteur pour
            # ralentir, trois relevés calmes pour reprendre. Two readings in a row with a visitor to slow down,
            # three calm readings to resume.
            if not outcome and (now - last_status >= settings.status_s or (results and not alive)):
                last_status = now
                try:
                    status = status_client.get_json("/status")
                except ServiceDown:
                    watch.suspect("status")
                    status = None
                except Exception:  # réponse illisible : pas un relevé propre / unreadable: not a clean reading
                    status = None
                if status is not None:
                    total = counters_total(status)
                    if total is not None and last_total is not None and total < last_total:
                        watch.suspect("restart")
                    else:
                        clean_since = now
                    if total is not None:
                        last_total = total
                    if visitors_active(status, gate.inflight):
                        calm = 0
                        busy_streak += 1
                        if busy_streak >= 2:
                            gate.set_throttle(True)
                    else:
                        busy_streak = 0
                        calm += 1
                        if calm >= 3:
                            gate.set_throttle(False)
            # 2. Soupçon de redémarrage : contrôle du moteur avant toute nouvelle unité / suspected restart.
            if not outcome and watch.suspected.is_set():
                log("[protocole] panne de connexion ou redémarrage possible : contrôle du moteur / connection failure "
                    "or possible restart: checking the engine")
                check_start = time.monotonic()
                if guarded_check("restart"):
                    watch.resolve()
                    last_status = -math.inf
                    clean_since = max(clean_since, check_start)
                    log("[protocole] même moteur : la campagne continue / same engine: the campaign goes on")
            # 3. Fusion : unités de l'époque courante, finies avant le dernier relevé propre / merge.
            if results:
                keep: list[tuple[str, Unit, UnitResult | None]] = []
                while results:
                    item = results.popleft()
                    kind, unit, result = item
                    if kind != "done" or result is None or result.epoch != watch.epoch or outcome:
                        with lock:
                            pending.appendleft(unit)
                    elif result.finished < clean_since:
                        state.merge(result)
                    else:
                        keep.append(item)
                results.extend(keep)
            if not alive and not results:
                break
            now = time.monotonic()
            if deadline is not None and now >= deadline and not no_new.is_set():
                no_new.set()
                log("budget de temps atteint : fin des unités en cours puis pause / time budget reached: pausing")
            # 4. Point de reprise, après un contrôle du moteur réussi / checkpoint, after a passing engine check.
            if not outcome and not watch.suspected.is_set() and now - last_save >= settings.checkpoint_s:
                # Le point de reprise ne contient que des unités fusionnées AVANT ce contrôle réussi.
                # The checkpoint only holds units merged BEFORE this passing check.
                check_start = time.monotonic()
                if guarded_check("checkpoint"):
                    clean_since = max(clean_since, check_start)
                    last_save = time.monotonic()
                    save(last_save)
            if now - last_progress >= settings.progress_s:
                last_progress = now
                rate = (state.docs - docs_at_start) / max(now - started, 1e-9)
                log(f"[protocole] unités {len(state.done)}/{total_units}, documents {state.docs:,}, "
                    f"{rate:,.0f} doc/s, ralenti {gate.throttled_s:,.0f} s, en vol {gate.inflight}, "
                    f"contrôles du moteur {state.engine_checks}")
            time.sleep(settings.tick_s)
    finally:
        no_new.set()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    gate.set_throttle(False)
    # Dernier contrôle du moteur, puis écriture ; sinon le dernier point de reprise vérifié reste.
    # Last engine check, then write; otherwise the last verified checkpoint stays.
    verified = not outcome and guarded_check("end")
    now = time.monotonic()
    run_info.update({"ended": datetime.now(UTC).isoformat(timespec="seconds"),
                     "docs": state.docs - docs_at_start, "seconds": round(now - started, 1)})
    if verified:
        save(now)
    if "changed" in outcome:
        log(f"refus : le moteur du service a changé pendant la campagne ({outcome['changed']}) ; rien n'est écrit "
            "après le dernier contrôle réussi ; reprendre exige le moteur du début / refused: the service engine "
            "changed during the campaign; nothing written after the last passing check")
        return EXIT_REFUSED
    if "crash" in outcome:
        log(f"refus : erreur de l'outil dans l'unité {outcome['crash']} (le contenu n'est jamais affiché) / refused: "
            "tool error in a unit (content never printed)")
        return EXIT_REFUSED
    if not verified:
        log(f"service injoignable ({outcome.get('down', '?')}) : dernier point de reprise vérifié conservé, `start` "
            "reprend / service unreachable: last verified checkpoint kept, `start` resumes")
        return EXIT_DOWN
    remaining = [u for u in plan.units if u.uid not in state.done]
    rate = (state.docs - docs_at_start) / max(now - started, 1e-9)
    log(f"[protocole] {state.docs - docs_at_start:,} documents en {now - started:,.0f} s ({rate:,.0f} doc/s) ; "
        f"unités restantes / units left: {len(remaining)} ; contrôles du moteur / engine checks: "
        f"{state.engine_checks}")
    if not remaining:
        return EXIT_DONE
    return EXIT_DOWN if "down" in outcome else EXIT_PAUSED


def _merge_retries(state: State, base: Counter[str], clients: list[ServiceClient], watch: EngineWatch) -> None:
    """Reprises : base du point de reprise + compteurs des fils (copie atomique) / retries: base + thread counters."""
    total = Counter(base)
    for client in list(clients):
        total.update(dict.copy(client.retries))
    total.update({f"engine_recheck:{reason}": n for reason, n in watch.reasons.items()})
    state.retries = total
