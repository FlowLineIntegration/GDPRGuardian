"""Contrôle croisé : l'évaluation synthétique par le SERVICE contre la même évaluation en processus.

Cross-check: the synthetic evaluation through the SERVICE against the same evaluation in process. Le corpus de
tools.eval (540 documents de base, 135 bases mutées par les 51 opérateurs, graine 20261024) passe par le service
(socket Unix, jeton local) ; ses zones masquées sont reconstruites par l'alignement, puis notées par
`score_document` et résumées par `summarize`, exactement comme `tools/eval/evaluate.py`. On compare chaque nombre du
résumé avec (1) l'évaluation en processus relancée à l'instant sur le même moteur et (2) le fichier de référence
du dépôt. Every number of the summary is compared with (1) the in-process evaluation re-run now on the same engine
and (2) the repository's reference file. Requires the `gdprguardian` package for part (1) (development machine).
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from typing import Any

from tools.eval.metrics import Masked, Tally, score_document
from tools.protocol.align import AlignmentError, align
from tools.protocol.cli import load_label_keys
from tools.protocol.transport import DocumentRefused, Gate, RetryPolicy, ServiceClient, UnixTransport

# Champs qui ne dépendent pas du moteur (temps, environnement) ou qui portent des exemples avec valeurs.
# Fields that do not depend on the engine (timings, environment) or that carry examples with values.
_IGNORED = ("seconds", "ms_per_doc", "chars_per_second", "miss_examples", "false_mask_examples")
# Le service ne dit pas quel détecteur a masqué : la « source » d'une zone y est « service ».
# The service does not say which detector masked: a zone's "source" is "service" there.
_SOURCE_ONLY = ("sources", "false_masks")


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in _IGNORED:
                continue
            out.update(_flatten(item, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, (list, tuple)) and value and isinstance(value[0], Mapping):
        for i, item in enumerate(value):
            out.update(_flatten(item, f"{prefix}[{i}]"))
    else:
        out[prefix] = list(value) if isinstance(value, tuple) else value
    return out


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return a == b or (math.isnan(a) and math.isnan(b))
    return a == b


def compare(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Différences feuille à feuille, groupées par rubrique / leaf-by-leaf differences, grouped by section."""
    a, b = _flatten(left), _flatten(right)
    diffs = {k: [a.get(k), b.get(k)] for k in sorted(set(a) | set(b)) if not _same(a.get(k), b.get(k))}
    groups: dict[str, int] = {}
    for key in diffs:
        section = key.split(".", 1)[0].split("[", 1)[0]
        groups[section] = groups.get(section, 0) + 1
    return {"leaves": len(set(a) | set(b)), "different": len(diffs), "by_section": groups, "diffs": diffs}


def service_run(client_factory: Any, docs: Sequence[Any], countries: str, threads: int,
                baselines: Mapping[str, list[bool]] | None = None) -> Any:
    """Comme `tools.eval.evaluate.run`, mais par le service / like `evaluate.run`, through the service."""
    from tools.eval.evaluate import Run

    labels = load_label_keys()
    local = {}

    def one(doc: Any) -> tuple[str, Any]:
        import threading

        key = threading.get_ident()
        if key not in local:
            local[key] = client_factory()
        try:
            output = local[key].anonymize(doc.text, {"countries": countries, "profile": "standard",
                                                     "label_language": "fr"})
            alignment = align(doc.text, output)
        except (DocumentRefused, AlignmentError) as exc:
            return "error", type(exc).__name__
        masked = [Masked(s, e, labels.get(label, label), "service") for s, e, label in alignment.masked]
        baseline = baselines.get(doc.meta.get("base", "")) if baselines else None
        return "ok", (score_document(doc, masked, output, baseline), len(doc.text))

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=threads) as pool:
        outcomes = list(pool.map(one, docs))
    result = Run(Tally(), [], 0.0, 0, {})
    for doc, (status, value) in zip(docs, outcomes, strict=True):
        if status == "error":
            result.errors[doc.doc_id] = value
            continue
        score, chars = value
        result.chars += chars
        result.tally.merge(score.tally)
        result.stats.append(score.stats)
        result.masked[doc.doc_id] = score.masked
    result.seconds = perf_counter() - started
    return result


def main(args: argparse.Namespace, header: tuple[str, str] | None) -> int:
    from tools.eval.evaluate import evaluate, summarize
    from tools.eval.generate import CorpusGenerator
    from tools.eval.mutate import mutate_corpus, select

    gate = Gate(args.threads)

    def factory() -> ServiceClient:
        return ServiceClient(UnixTransport(args.socket, header), gate, RetryPolicy())

    generator = CorpusGenerator(args.seed)
    base = list(generator.corpus(args.docs))
    mutated = list(mutate_corpus(base[:args.mutation_docs], select(None), args.seed)) if args.mutation_docs else []
    t0 = perf_counter()
    base_run = service_run(factory, base, args.countries, args.threads)
    mutated_run = service_run(factory, mutated, args.countries, args.threads, base_run.masked) if mutated else None
    service_seconds = perf_counter() - t0
    service = {"base": summarize(base_run, resamples=1000, seed=args.seed, samples=3)}
    if mutated_run is not None:
        service["mutated"] = summarize(mutated_run, resamples=0, seed=args.seed, samples=1)
    t1 = perf_counter()
    inprocess = evaluate(args.docs, args.mutation_docs, args.seed, ("standard",), None, 1000, 3,
                         args.countries)["profiles"]["standard"]
    inprocess_seconds = perf_counter() - t1
    reference_path = Path(args.reference)
    reference = (json.loads(reference_path.read_text(encoding="utf-8"))["profiles"]["standard"]
                 if reference_path.exists() else None)

    def strip(summary: Mapping[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in summary.items() if k not in _SOURCE_ONLY}

    out: dict[str, Any] = {
        "corpus": {"seed": args.seed, "base_docs": len(base), "mutated_docs": len(mutated),
                   "countries": args.countries},
        "service_seconds": round(service_seconds, 1), "inprocess_seconds": round(inprocess_seconds, 1),
        "service_docs_per_second": round((len(base) + len(mutated)) / service_seconds, 1),
        "service_errors": {"base": base_run.errors, "mutated": mutated_run.errors if mutated_run else {}},
        "headline": {"service": service["base"]["headline"], "inprocess": inprocess["base"]["headline"],
                     "reference": reference["base"]["headline"] if reference else None},
    }
    for corpus in ("base", "mutated"):
        if corpus not in service:
            continue
        out[f"vs_inprocess_{corpus}"] = compare(strip(service[corpus]), strip(inprocess[corpus]))
        out[f"vs_inprocess_{corpus}_sources_only"] = compare(
            {k: service[corpus].get(k) for k in _SOURCE_ONLY}, {k: inprocess[corpus].get(k) for k in _SOURCE_ONLY})
        if reference is not None and corpus in reference:
            out[f"vs_reference_{corpus}"] = compare(strip(service[corpus]), strip(reference[corpus]))
            out[f"inprocess_vs_reference_{corpus}"] = compare(strip(inprocess[corpus]), strip(reference[corpus]))
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for key, value in out.items():
        if key.startswith(("vs_", "inprocess_vs")):
            print(f"{key}: {value['different']}/{value['leaves']} différents / different {value['by_section']}")
    print(f"service {out['service_docs_per_second']} doc/s, erreurs / errors {out['service_errors']}")
    return 0


# --- Résumé publié / published summary -------------------------------------------------------------------------------

HEADLINE_KEYS = ("recall_direct", "recall_structured", "recall", "precision", "f2", "entity_recall_direct",
                 "doc_leak_rate", "doc_leak_rate_structured", "over_masking", "decoy_false_mask_rate")
# Feuilles qui dépendent de la frontière entre deux balises voisines, que la sortie seule ne dit pas : seul écart
# admis entre le service et l'évaluation en processus sur le même moteur. Leaves that depend on the boundary between
# two neighbouring placeholders, which the output alone does not give: the only difference allowed between the service
# and the in-process evaluation on the same engine.
_BOUNDARY_LABEL_FIELDS = ("precision", "f2", "iou90_rate", "typed_rate", "strict_recall")
EXPLANATIONS = {
    "boundary": "per system label (confusion, per-label precision, F2, IoU>=90%, typed rate, strict recall, strict "
                "entity rate, characters per system label): the boundary between two placeholders separated only by "
                "spaces cannot be recovered from the output (leftmost placement used); nothing that is masked depends "
                "on it",
    "engine": "the service and the in-process evaluation agree with each other and differ from the reference file: "
              "the engine changed since the reference file was written",
    "random_draws": "interval bounds only, the service and the in-process evaluation agree: bootstrap draws differ "
                    "between the reference environment and this one (numpy or the pure-Python fallback), or the engine "
                    "changed",
}


def _is_boundary(leaf: str) -> bool:
    head = leaf.split(".", 1)[0].split("[", 1)[0]
    if head in ("confusion", "system_labels"):
        return True
    if head == "labels":
        return leaf.rsplit(".", 1)[-1] in _BOUNDARY_LABEL_FIELDS
    return head == "entities" and leaf.endswith(".strict_rate")


def _is_interval(leaf: str) -> bool:
    return leaf.startswith("ci95") or ".ci95" in leaf


def classify(run: Mapping[str, Any], corpus: str) -> dict[str, Any]:
    """Chaque écart d'un corpus, rangé et expliqué ; « unexplained » doit rester vide / every difference, classified."""
    tool = run.get(f"vs_inprocess_{corpus}") or {"different": 0, "leaves": 0, "diffs": {}}
    tool_unexplained = sorted(k for k in tool["diffs"] if not _is_boundary(k))
    out: dict[str, Any] = {
        "service_vs_inprocess": {"leaves": tool["leaves"], "different": tool["different"],
                                 "boundary": tool["different"] - len(tool_unexplained),
                                 "unexplained": tool_unexplained},
    }
    reference = run.get(f"vs_reference_{corpus}")
    if reference is not None:
        tool_diffs = tool["diffs"]
        counts = {"engine": 0, "random_draws": 0, "boundary": 0}
        unexplained = []
        for leaf in reference["diffs"]:
            if leaf not in tool_diffs:  # service = en processus / service equals in process
                counts["random_draws" if _is_interval(leaf) else "engine"] += 1
            elif _is_boundary(leaf):
                counts["boundary"] += 1
            else:
                unexplained.append(leaf)
        out["service_vs_reference"] = {"leaves": reference["leaves"], "different": reference["different"], **counts,
                                       "unexplained": sorted(unexplained)}
    return out


def write_summary(runs: Mapping[str, Mapping[str, Any]], out_dir: Path, date: str,
                  engine_note: str) -> tuple[list[Path], dict[str, Any]]:
    """`benchmarks/results/protocol-crosscheck-<date>.{json,md}` depuis les sorties de `crosscheck` (scores seuls).

    From the `crosscheck` outputs (scores only). Le service est validé quand, sur le même moteur, les dix indicateurs
    principaux sont identiques, aucun document n'échoue et chaque autre écart est un effet de frontière. The tool is
    validated when, on the same engine, the ten headline indicators are identical, no document fails and every other
    difference is a boundary effect.
    """
    summary: dict[str, Any] = {"date": date, "engine": engine_note,
                               "what": "The synthetic development evaluation (540 documents, seed 20261024, and their "
                                       "mutations by the 51 red-team operators) sent through a local GDPR Guardian "
                                       "service (public mode, local token, Unix socket) by tools/protocol, masked "
                                       "zones rebuilt from the output alone, scored with tools.eval (score_document, "
                                       "summarize) and compared leaf by leaf with the in-process evaluation of the "
                                       "same engine and with the repository's reference file.",
                               "explanations": EXPLANATIONS, "runs": {}}
    validated = True
    for label, run in runs.items():
        headline = run["headline"]
        same = all(headline["service"][k] == headline["inprocess"][k] for k in HEADLINE_KEYS)
        reference = headline.get("reference")
        entry = {"corpus": run["corpus"], "service_docs_per_second": run.get("service_docs_per_second"),
                 "service_errors": run.get("service_errors"), "headline": headline,
                 "headline_service_equals_inprocess": same,
                 "headline_service_equals_reference": (all(headline["service"][k] == reference[k]
                                                           for k in HEADLINE_KEYS) if reference else None),
                 "base": classify(run, "base")}
        if "vs_inprocess_mutated" in run:
            entry["mutated"] = classify(run, "mutated")
        errors = any((run.get("service_errors") or {}).values())
        unexplained = any(entry[c][part]["unexplained"] for c in ("base", "mutated") if c in entry
                          for part in entry[c])
        entry["tool_validated"] = same and not errors and not unexplained
        validated = validated and entry["tool_validated"]
        summary["runs"][label] = entry
    summary["tool_validated"] = validated
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / f"protocol-crosscheck-{date}"
    json_path, md_path = stem.with_suffix(".json"), stem.with_suffix(".md")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(_summary_markdown(summary), encoding="utf-8", newline="\n")
    return [json_path, md_path], {"tool_validated": validated,
                                  "runs": {k: v["tool_validated"] for k, v in summary["runs"].items()}}


def _summary_markdown(summary: Mapping[str, Any]) -> str:
    def pct(x: Any) -> str:
        return "—" if x is None else f"{100 * x:.2f} %"

    lines = [f"# Contrôle croisé de l'outil du protocole / protocol tool cross-check — {summary['date']}", "",
             "L'évaluation synthétique de développement (540 documents, graine 20261024, et leurs mutations par les "
             "51 opérateurs) passe par un service local en mode public avec jeton local (socket Unix), via "
             "`tools/protocol` ; les zones masquées sont reconstruites depuis la seule sortie, notées par "
             "`tools.eval`, puis comparées feuille à feuille avec l'évaluation en processus du même moteur et avec le "
             "fichier de référence du dépôt. Scores seulement. " + summary["what"], "",
             f"Moteur contrôlé / engine checked: {summary['engine']}.", "",
             f"**Outil validé / tool validated: {'oui / yes' if summary['tool_validated'] else 'NON / NO'}** (même "
             "moteur : dix indicateurs identiques, aucun échec, tout autre écart est un effet de frontière / same "
             "engine: ten identical indicators, no failure, every other difference is a boundary effect).", ""]
    for label, run in summary["runs"].items():
        h = run["headline"]
        ref = h.get("reference") or {}
        corpus = run["corpus"]
        lines += [f"## Pays / countries `{label}` — {corpus['base_docs']} + {corpus['mutated_docs']} documents", "",
                  "| Indicateur / indicator | Service | En processus / in process | Référence / reference |",
                  "|---|---|---|---|"]
        lines += [f"| {k} | {pct(h['service'][k])} | {pct(h['inprocess'][k])} | {pct(ref.get(k))} |"
                  for k in HEADLINE_KEYS]
        lines += ["", f"- Service = en processus (10 indicateurs) / service = in process: "
                      f"{run['headline_service_equals_inprocess']} ; service = référence / reference: "
                      f"{run['headline_service_equals_reference']} ; erreurs du service / service errors: "
                      f"{run['service_errors']} ; {run['service_docs_per_second']} doc/s."]
        for corpus_name in ("base", "mutated"):
            if corpus_name not in run:
                continue
            tool = run[corpus_name]["service_vs_inprocess"]
            lines.append(f"- `{corpus_name}`, service contre en processus / vs in process: {tool['different']} "
                         f"feuilles sur / leaves of {tool['leaves']}, dont effet de frontière / boundary "
                         f"{tool['boundary']}, inexpliquées / unexplained {len(tool['unexplained'])}.")
            ref_part = run[corpus_name].get("service_vs_reference")
            if ref_part:
                lines.append(f"- `{corpus_name}`, service contre la référence / vs the reference: "
                             f"{ref_part['different']} feuilles sur / leaves of {ref_part['leaves']} : moteur changé "
                             f"depuis la référence / engine changed {ref_part['engine']}, bornes d'intervalle / "
                             f"interval bounds {ref_part['random_draws']}, frontière / boundary "
                             f"{ref_part['boundary']}, inexpliquées / unexplained {len(ref_part['unexplained'])}.")
        lines.append("")
    lines += ["## Explication de chaque catégorie / every category explained", ""]
    lines += [f"- `{k}` : {v}" for k, v in summary["explanations"].items()]
    lines.append("")
    return "\n".join(lines)
