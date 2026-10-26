"""Plan de la campagne : unités de travail déterministes et sources de documents / campaign plan and sources.

Unité = tranche de documents rejouable à l'identique (graine et positions, ou corpus et lignes) : la reprise
après coupure refait seulement les unités non terminées. Les documents synthétiques naissent en mémoire, à la
demande, du générateur du dépôt ; les corpus réels sont lus dans un paquet gzip placé en mémoire vive (tmpfs).
Unit = a replayable slice of documents; resuming only redoes unfinished units. Synthetic documents are generated in
memory on demand; real corpora are read from a gzip pack placed in RAM-backed storage (tmpfs).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.protocol import spec

PACK_FORMAT = "gdprguardian-protocol-real"
PACK_VERSION = 1
RAM_FILESYSTEMS = frozenset({"tmpfs", "ramfs"})


@dataclass(frozen=True, slots=True)
class Unit:
    uid: str
    kind: str              # "real", "synthetic", "redteam"
    start: int
    count: int
    seed: int | None = None
    corpus: str | None = None


@dataclass(frozen=True, slots=True)
class Plan:
    units: tuple[Unit, ...]
    synthetic_seeds: tuple[int, ...]
    synthetic_docs_per_seed: int
    redteam_seeds: tuple[int, ...]
    redteam_bases_per_seed: int
    real_counts: Mapping[str, int]

    @property
    def plan_id(self) -> str:
        """Empreinte du plan (unités et paramètres, jamais de contenu) / plan fingerprint (no content)."""
        payload = json.dumps({"protocol": spec.PROTOCOL_VERSION, "units": [u.uid + f"+{u.count}" for u in self.units]},
                             separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _slices(total: int, size: int) -> Iterator[tuple[int, int]]:
    for start in range(0, total, size):
        yield start, min(size, total - start)


def build_plan(*, synthetic_seeds: Sequence[int] = spec.SYNTHETIC_SEEDS,
               synthetic_docs_per_seed: int = spec.SYNTHETIC_DOCS_PER_SEED,
               redteam_seeds: Sequence[int] = spec.REDTEAM_SEEDS,
               redteam_bases_per_seed: int = spec.REDTEAM_BASES_PER_SEED,
               real_counts: Mapping[str, int] | None = None,
               unit_synthetic: int = spec.UNIT_SYNTHETIC_DOCS, unit_redteam: int = spec.UNIT_REDTEAM_BASES,
               unit_real: int = spec.UNIT_REAL_DOCS) -> Plan:
    """Corpus réels d'abord (effacés de la mémoire au plus tôt), puis synthétique et équipe rouge en alternance.

    Real corpora first (out of RAM as early as possible), then synthetic and red-team units interleaved.
    """
    real_counts = dict(real_counts or {})
    if spec.DEV_SEED in set(synthetic_seeds) | set(redteam_seeds):
        raise ValueError("la graine de développement est exclue / the development seed is excluded")
    units: list[Unit] = []
    for corpus in spec.REAL_CORPORA:
        for start, count in _slices(real_counts.get(corpus, 0), unit_real):
            units.append(Unit(f"real:{corpus}:{start}", "real", start, count, corpus=corpus))
    synthetic = [Unit(f"syn:{seed}:{start}", "synthetic", start, count, seed=seed)
                 for seed in synthetic_seeds for start, count in _slices(synthetic_docs_per_seed, unit_synthetic)]
    redteam = [Unit(f"red:{seed}:{start}", "redteam", start, count, seed=seed)
               for seed in redteam_seeds for start, count in _slices(redteam_bases_per_seed, unit_redteam)]
    # Alternance proportionnelle : une campagne interrompue a avancé partout / proportional interleaving.
    merged: list[Unit] = []
    i = j = 0
    while i < len(synthetic) or j < len(redteam):
        if j >= len(redteam) or (i < len(synthetic) and i * max(len(redteam), 1) <= j * max(len(synthetic), 1)):
            merged.append(synthetic[i])
            i += 1
        else:
            merged.append(redteam[j])
            j += 1
    units.extend(merged)
    return Plan(tuple(units), tuple(synthetic_seeds), synthetic_docs_per_seed, tuple(redteam_seeds),
                redteam_bases_per_seed, real_counts)


# --- Documents synthétiques d'une unité / synthetic documents of a unit ------------------------------------------


def synthetic_documents(unit: Unit, generator: Any) -> Iterator[tuple[str, Any, bool]]:
    """(cellule, document, est_une_base) dans l'ordre d'envoi ; une base précède ses variantes mutées.

    (cell, document, is_base) in sending order; a base document precedes its mutated variants. Même ordre pour la
    campagne et le décompte à blanc (empreintes identiques) / same order for the campaign and the dry run.
    """
    if unit.kind == "synthetic":
        for index in range(unit.start, unit.start + unit.count):
            yield f"synthetic_fr/seed={unit.seed}", generator.document(index), False
        return
    if unit.kind != "redteam":
        raise ValueError(unit.kind)
    from random import Random

    from tools.eval.mutate import MUTATIONS, mutate_document

    for index in range(unit.start, unit.start + unit.count):
        base = generator.document(index)
        yield f"redteam_bases/seed={unit.seed}", base, True
        for mutation in MUTATIONS:
            mutated = mutate_document(base, mutation, Random(f"{unit.seed}/{mutation.name}/{base.doc_id}"))
            if mutated is not None:
                yield f"redteam_fr/op={mutation.name}", mutated, False


def track(digest: Any, doc_id: str, text: str) -> None:
    """Empreinte de ce qui est envoyé (identifiant et texte) / fingerprint of what is sent (id and text)."""
    digest.update(doc_id.encode("utf-8") + b"\x1f" + text.encode("utf-8", "surrogatepass") + b"\x1e")


# --- Corpus réels en mémoire vive / real corpora in RAM ------------------------------------------------------------


def filesystem_type(path: Path) -> str | None:
    """Type du système de fichiers qui porte `path` (Linux, /proc/self/mounts) ; None ailleurs / None elsewhere."""
    mounts = Path("/proc/self/mounts")
    if not mounts.exists():
        return None
    target = os.path.realpath(path)
    best, best_type = "", None
    for line in mounts.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        point = parts[1].replace("\\040", " ")
        if (target == point or target.startswith(point.rstrip("/") + "/")) and len(point) >= len(best):
            best, best_type = point, parts[2]
    return best_type


def check_ram_storage(path: Path, allow_disk: bool = False) -> str:
    """Refuse un paquet de corpus réels hors mémoire vive / refuses a real-corpus pack outside RAM storage."""
    kind = filesystem_type(path)
    if kind in RAM_FILESYSTEMS:
        return kind
    if allow_disk:
        return f"{kind or 'unknown'} (accepté : --allow-disk-real, essais seulement / tests only)"
    raise SystemExit(f"le paquet des corpus réels doit être en mémoire vive (tmpfs, /dev/shm), pas sur {kind!r} / "
                     "the real-corpus pack must live in RAM-backed storage (tmpfs, /dev/shm)")


def corpus_digest(records: Iterable[Mapping[str, Any]]) -> str:
    """Empreinte d'un corpus (identifiants, textes, zones) ; jamais publiée avec son contenu / corpus fingerprint."""
    h = hashlib.sha256()
    for rec in records:
        h.update(json.dumps({"id": rec["id"], "text": rec["text"], "spans": rec["spans"]}, ensure_ascii=False,
                            sort_keys=True, separators=(",", ":")).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


PACK_SPLITS = ("all", "dev", "test")


def write_pack(cache: Path, out: Path, corpora: Sequence[str] = tuple(spec.REAL_CORPORA),
               split: str = "all") -> dict[str, Any]:
    """Paquet gzip des corpus réels depuis le cache de tools.corpus (hors dépôt) / gzip pack from the cache.

    `split="dev"` : moitié dev seulement, pour tout essai avant la campagne (la moitié test reste intacte) ; une
    campagne standard exige le paquet complet. `split="dev"`: dev half only, for any trial before the campaign (the
    test half stays untouched); a standard campaign requires the full pack.
    """
    from tools.corpus.real_common import split_of

    if split not in PACK_SPLITS:
        raise ValueError(split)
    root = Path(__file__).resolve().parents[2]
    for path in (cache, out):
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        raise SystemExit("cache et paquet hors du dépôt : données personnelles / cache and pack outside the repository")
    loaded: dict[str, list[dict[str, Any]]] = {}
    for name in corpora:
        source = cache / "corpora" / f"{name}.jsonl"
        if not source.exists():
            raise SystemExit(f"corpus absent du cache / corpus missing from the cache: {name}")
        with source.open(encoding="utf-8") as fh:
            records = (json.loads(line) for line in fh if line.strip())
            loaded[name] = [r for r in records if split == "all" or split_of(r["id"]) == split]
    header = {"pack": PACK_FORMAT, "version": PACK_VERSION, "split": split,
              "corpora": {name: {"docs": len(recs), "sha256": corpus_digest(recs)} for name, recs in loaded.items()}}
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(header, ensure_ascii=False) + "\n")
        for name, recs in loaded.items():
            for rec in recs:
                fh.write(json.dumps({"corpus": name, "record": rec}, ensure_ascii=False) + "\n")
    tmp.replace(out)
    return header


def read_pack(path: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Paquet -> (en-tête, corpus en mémoire), empreintes vérifiées / pack -> (header, corpora), digests checked."""
    corpora: dict[str, list[dict[str, Any]]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        if header.get("pack") != PACK_FORMAT or header.get("version") != PACK_VERSION:
            raise SystemExit("paquet de corpus réels inconnu / unknown real-corpus pack")
        for line in fh:
            if line.strip():
                item = json.loads(line)
                corpora.setdefault(item["corpus"], []).append(item["record"])
    for name, info in header["corpora"].items():
        recs = corpora.get(name, [])
        if len(recs) != info["docs"] or corpus_digest(recs) != info["sha256"]:
            raise SystemExit(f"paquet altéré / corrupted pack: {name}")
    return header, corpora
