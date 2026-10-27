"""Mesure interne par mode, sur les moitiés dev, avec le moteur installé / internal per-mode measure, dev halves.

    python -I -m tools.protocol modes-dev --out FICHIER.json [--cache DOSSIER] [--jobs N]

Donne, pour chaque mode (fort, essentiel), les deux chiffres du protocole 1.2 : « anonymisation » (indice « documents
normalisés » avec son intervalle, et indice « documents difficiles ») et « codes utiles perdus » (leurres masqués,
famille synthétique). Même notation que la campagne (`campaign.Worker` : envoi, alignement de la sortie, notation),
mais en processus, avec le moteur INSTALLÉ (jamais le serveur public), sur des données déjà vues par la conception
des règles : moitiés `dev` de BODACC, BOAMP et ParlaMint-FR, et la graine de développement 20261024 (documents
synthétiques avec leurres, et leurs mutations par les 51 opérateurs de l'équipe rouge). Aucune moitié `test` n'est
lue. Le fichier écrit porte `modes_source` = « mesure interne, moitié dev » : jamais un résultat du protocole.

For each mode, the two 1.2 numbers, scored like the campaign but in process with the INSTALLED engine (never the
public server), on data rule design already saw (dev halves, development seed). No test half is read. The file
written says `modes_source` = "mesure interne, moitié dev": never a protocol result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.protocol import spec
from tools.protocol.outcomes import Cell, merge_cells

SOURCE = "mesure interne, moitié dev"
REAL_INDEX_CORPORA = ("bodacc_fr", "boamp_fr", "parlamint_fr")
UNIT_SYNTHETIC = 250
UNIT_REDTEAM = 2
UNIT_REAL = 50


class EngineWithoutModes(SystemExit):
    pass


def check_engine_modes(modes: Sequence[str]) -> None:
    """Le moteur installé accepte-t-il « mode » ? Sinon, arrêt avec un message clair / clear stop otherwise."""
    try:
        from gdprguardian import Anonymizer
    except ImportError:
        raise EngineWithoutModes("moteur gdprguardian absent : installer le dépôt (pip install -e .) / gdprguardian "
                                 "engine not installed") from None
    for mode in modes:
        try:
            Anonymizer(countries=("FR",), mode=mode, label_language=spec.LABEL_LANGUAGE)
        except (TypeError, ValueError) as exc:
            raise EngineWithoutModes(
                f"le moteur installé ne connaît pas le réglage « mode » ({mode}) : il faut le moteur 1.0.2 (src/ à "
                f"jour, pip install -e .) / the installed engine does not know the 'mode' setting ({mode}): engine "
                f"1.0.2 required ({type(exc).__name__})") from None


def engine_label() -> str:
    """Version du moteur installé et empreinte de ses sources Python / installed engine version and source digest."""
    import gdprguardian

    root = Path(gdprguardian.__file__).resolve().parent
    h = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        h.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return f"{gdprguardian.__version__}+src.{h.hexdigest()[:12]}"


class InProcessClient:
    """Même interface que `transport.ServiceClient.anonymize`, moteur en processus, un moteur par (pays, mode).

    Same interface as the service client, in-process engine, one engine per (countries, mode).
    """

    def __init__(self) -> None:
        self._engines: dict[tuple[str, str | None, str | None], Any] = {}
        self._lock = threading.Lock()

    def anonymize(self, text: str, options: Mapping[str, Any]) -> str:
        from gdprguardian import Anonymizer

        key = (str(options.get("countries", "FR")), options.get("mode"), options.get("profile"))
        with self._lock:
            if key not in self._engines:
                countries = tuple(c for c in key[0].split(",") if c)
                extra = {"mode": key[1]} if key[1] else {"profile": key[2]}
                self._engines[key] = Anonymizer(countries=countries, label_language=spec.LABEL_LANGUAGE, **extra)
            engine = self._engines[key]
        return engine.anonymize(text).text


# --- Travail d'un processus / one process's work --------------------------------------------------------------------

_WORKER: Any = None


def _run_unit(unit: Any, modes: tuple[str, ...], records: list[dict[str, Any]] | None) -> tuple[dict[str, Any], int]:
    """Une unité notée comme dans la campagne ; cellules en JSON (rien d'autre) / one unit, cells as JSON only."""
    global _WORKER
    from tools.protocol.campaign import Worker
    from tools.protocol.cli import load_label_keys

    if _WORKER is None:
        _WORKER = Worker(InProcessClient(), load_label_keys(), {}, threading.Event(), None, modes)  # type: ignore[arg-type]
    real = {unit.corpus: [None] * unit.start + list(records)} if records is not None else {}
    _WORKER.real = real
    result = _WORKER.run(unit)
    return {key: cell.to_json() for key, cell in result.cells.items()}, result.docs


# --- Données / data --------------------------------------------------------------------------------------------------


def load_dev_real(cache: Path, limit: int | None) -> dict[str, list[dict[str, Any]]]:
    """Moitiés dev des corpus réels de l'indice (jamais la moitié test) / dev halves only, never the test half."""
    from tools.corpus.real_common import split_of

    out: dict[str, list[dict[str, Any]]] = {}
    for name in REAL_INDEX_CORPORA:
        path = cache / "corpora" / f"{name}.jsonl"
        if not path.exists():
            raise SystemExit(f"corpus absent du cache / corpus missing from the cache: {path}")
        rows = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if split_of(rec["id"]) == "dev":
                    rows.append(rec)
                    if limit is not None and len(rows) >= limit:
                        break
        out[name] = rows
    return out


def units(synthetic_docs: int, redteam_bases: int, real: Mapping[str, list[dict[str, Any]]]) -> list[Any]:
    from tools.protocol.plan import Unit

    seed = spec.DEV_SEED
    out: list[Any] = []
    for corpus, rows in real.items():
        out += [Unit(f"real:{corpus}:{s}", "real", s, min(UNIT_REAL, len(rows) - s), corpus=corpus)
                for s in range(0, len(rows), UNIT_REAL)]
    out += [Unit(f"red:{seed}:{s}", "redteam", s, min(UNIT_REDTEAM, redteam_bases - s), seed=seed)
            for s in range(0, redteam_bases, UNIT_REDTEAM)]
    out += [Unit(f"syn:{seed}:{s}", "synthetic", s, min(UNIT_SYNTHETIC, synthetic_docs - s), seed=seed)
            for s in range(0, synthetic_docs, UNIT_SYNTHETIC)]
    return out


# --- Chiffres par mode / per-mode figures ----------------------------------------------------------------------------


def mode_figures(cells: Mapping[str, Cell], mode: str, resamples: int) -> dict[str, Any]:
    """Les deux chiffres d'un mode et leur détail (moitiés dev) / one mode's two numbers and detail (dev halves)."""
    from tools.protocol.report import real_measures, synthetic_measures
    from tools.protocol.stats import bootstrap_index, bootstrap_pooled, family_rates, index_point, pooled_point

    prefix = f"{mode}{spec.MODE_SEP}"
    view = {k[len(prefix):]: c for k, c in cells.items() if k.startswith(prefix)}

    def under(head: str, tail: str | None = None) -> Cell:
        return merge_cells(c for k, c in view.items() if k.partition("/")[0] == head
                           and (tail is None or k.partition("/")[2] == tail))

    families: dict[str, Cell] = {"synthetic_fr": under("synthetic_fr")}
    families.update({name: under(name, "dev") for name in REAL_INDEX_CORPORA})
    hists = [families[f.name].hist for f in spec.FAMILIES]
    point, recall = index_point(hists)
    ci = bootstrap_index(hists, resamples, spec.BOOTSTRAP_SEED)
    groups = {f.name: merge_cells(c for k, c in view.items() if k.partition("/")[0] == "redteam_fr"
                                  and k.partition("/")[2] in {f"op={op}" for op in f.operators})
              for f in spec.HARD_FAMILIES}
    hard_hists = [g.hist for g in groups.values()]
    hard_point, hard_recall = pooled_point(hard_hists)
    hard_ci = bootstrap_pooled(hard_hists, resamples, spec.BOOTSTRAP_SEED)
    synthetic = synthetic_measures(families["synthetic_fr"])
    overmask_cell = merge_cells([families["synthetic_fr"], under("redteam_fr")])
    t = overmask_cell.tally
    overmask = t.neutral_masked / t.neutral_chars if t is not None and t.neutral_chars else None
    detail = {}
    for name, cell in families.items():
        rate, mention_recall = family_rates(cell.hist)
        precision = (synthetic.get("precision") if name == "synthetic_fr"
                     else (real_measures(cell, name, 0, spec.BOOTSTRAP_SEED).get("metrics") or {}).get("precision"))
        if name in spec.PARTIAL_GOLD:
            precision = None
        detail[name] = {"docs": cell.docs, "scored": cell.scored, "passed": cell.passed, "no_leak_rate": rate,
                        "mention_recall": mention_recall, "precision": precision, "errors": dict(cell.errors),
                        # Rappel par type d'identifiant (où un mode laisse fuir) / recall per identifier type.
                        "per_label": {label: {"mentions": n, "recall": cell.label_masked.get(label, 0) / n}
                                      for label, n in sorted(cell.label_mentions.items()) if n}}
    for name, cell in groups.items():
        rate, mention_recall = family_rates(cell.hist)
        detail[name] = {"docs": cell.docs, "scored": cell.scored, "passed": cell.passed, "no_leak_rate": rate,
                        "mention_recall": mention_recall, "errors": dict(cell.errors)}
    decoy = synthetic.get("decoy_false_mask_rate")
    guards = {"overmask_synthetic": {"value": overmask, "max": spec.GUARD_MAX_OVERMASK},
              **{f"precision_{n}": {"value": detail[n]["precision"], "min": spec.GUARD_MIN_PRECISION}
                 for n in spec.GUARD_PRECISION_FAMILIES}}
    if mode in spec.DECOY_GUARD_MODES:
        guards["decoys_masked_synthetic"] = {"value": decoy, "max": spec.GUARD_MAX_DECOY_MASKED}
    for g in guards.values():
        v = g["value"]
        g["passed"] = v is not None and (v <= g["max"] if "max" in g else v >= g["min"])
    return {"mode": mode, "normalised": point, "normalised_ci95": list(ci["index"]) if ci["index"] else None,
            "mention_recall": recall, "hard": hard_point,
            "hard_ci95": list(hard_ci["index"]) if hard_ci["index"] else None, "hard_mention_recall": hard_recall,
            "useful_codes_lost": decoy, "decoys": synthetic.get("decoys"), "families": detail,
            "guards": guards, "guards_passed": all(g["passed"] for g in guards.values())}


def site_keys(figures: Mapping[str, Mapping[str, Any]], date: str, engine: str) -> dict[str, Any]:
    """Clés partagées avec le site (fort_*, ess_*, modes_*), « — » pour un mode non mesuré / shared site keys."""

    def pct(value: Any) -> Any:
        return "—" if value is None else round(100 * float(value), 1)

    keys: dict[str, Any] = {}
    for mode, prefix in spec.MODE_SITE_PREFIX.items():
        f = figures.get(mode)
        low, high = (f or {}).get("normalised_ci95") or (None, None)
        keys.update({f"{prefix}_index": pct((f or {}).get("normalised")), f"{prefix}_ci_low": pct(low),
                     f"{prefix}_ci_high": pct(high), f"{prefix}_hard_index": pct((f or {}).get("hard")),
                     f"{prefix}_code_loss": pct((f or {}).get("useful_codes_lost"))})
    keys.update({"modes_source": SOURCE, "modes_date": date, "modes_engine": engine})
    return keys


def main(args: argparse.Namespace) -> int:
    from tools.corpus.real_common import default_cache

    modes = tuple(args.modes)
    check_engine_modes(modes)
    cache = Path(args.cache) if args.cache else default_cache()
    real = load_dev_real(cache, args.real_limit)
    work = units(args.synthetic_docs, args.redteam_bases, real)
    jobs = args.jobs or max(1, (os.cpu_count() or 2) // 2)
    started = time.monotonic()
    cells: dict[str, Cell] = {}
    docs = 0
    print(f"[modes-dev] {len(work)} unités, {jobs} processus, modes {', '.join(modes)}, moitiés dev seulement",
          file=sys.stderr, flush=True)
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(_run_unit, unit, modes,
                               real[unit.corpus][unit.start:unit.start + unit.count] if unit.kind == "real" else None)
                   for unit in work]
        for i, future in enumerate(futures, 1):
            unit_cells, unit_docs = future.result()
            docs += unit_docs
            for key, data in unit_cells.items():
                cells.setdefault(key, Cell()).merge(Cell.from_json(data))
            if i % 25 == 0 or i == len(futures):
                print(f"[modes-dev] {i}/{len(futures)} unités, {docs:,} documents, "
                      f"{time.monotonic() - started:,.0f} s", file=sys.stderr, flush=True)
    figures = {mode: mode_figures(cells, mode, args.resamples) for mode in modes}
    date = datetime.now(UTC).date().isoformat()
    engine = engine_label()
    out = {
        "what": "mesure interne par mode, moitiés dev et graine de développement, moteur installé en processus ; "
                "jamais un résultat du protocole / internal per-mode measure, dev halves and development seed, "
                "installed engine in process; never a protocol result",
        "modes_source": SOURCE, "date": date, "engine": engine, "protocol_definitions": spec.PROTOCOL_VERSION,
        "sample": {"synthetic_seed": spec.DEV_SEED, "synthetic_docs": args.synthetic_docs,
                   "redteam_bases": args.redteam_bases, "real_split": "dev",
                   "real_docs": {k: len(v) for k, v in real.items()}, "documents": docs,
                   "requests": docs * len(modes)},
        "seconds": round(time.monotonic() - started, 1),
        "keys": site_keys(figures, date, engine),
        "modes": figures,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out["keys"], ensure_ascii=False, indent=1))
    print(f"[modes-dev] {path} ({out['seconds']:,} s)", file=sys.stderr)
    return 0
