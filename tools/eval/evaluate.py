"""Évaluation de bout en bout de Gardien RGPD sur le corpus synthétique / end-to-end GDPR Guardian evaluation.

Lance `Anonymizer.anonymize` sur le corpus de base et sur le corpus muté (équipe rouge), pour chaque
profil, puis écrit un rapport JSON et Markdown. Runs the anonymizer over the base and red-team corpora
for each profile and writes JSON + Markdown reports (default: benchmarks/results/eval.{json,md}).

Usage : python -m tools.eval.evaluate --docs 540 --mutation-docs 135 --profiles fast,standard,strict
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from time import perf_counter
from typing import Any

if __package__ in (None, ""):  # lancé comme script / run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.eval.generate import DEFAULT_SEED, CorpusGenerator
from tools.eval.metrics import (
    STAT_FIELDS,
    TEXTUAL_LABELS,
    Masked,
    Tally,
    bootstrap,
    f_beta,
    headline,
    label_group,
    ratio,
    score_document,
    wilson,
)
from tools.eval.mutate import mutate_corpus, select
from tools.eval.schema import GOLD_LABELS, NO_MASK, Document
from tools.eval.templates import KINDS

from gdprguardian import Anonymizer

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ("fast", "standard", "strict")


@dataclass(slots=True)
class Run:
    """Résultat brut d'un profil sur un corpus / raw result of one profile on one corpus."""

    tally: Tally
    stats: list[list[int]]
    seconds: float
    chars: int
    masked: dict[str, list[bool]]  # doc_id -> zones entièrement masquées / fully masked spans
    errors: dict[str, str] = field(default_factory=dict)  # doc_id -> type d'exception / exception type


def masked_spans(anonymizer: Anonymizer, text: str) -> tuple[list[Masked], str]:
    """Zones réellement remplacées (positions originales) et texte de sortie / replaced zones and output."""
    result = anonymizer.anonymize(text)
    spans = [Masked(s.start, s.end, s.label, s.source) for s in result.analysis.spans if s.personal]
    return spans, result.text


def run(anonymizer: Anonymizer, docs: Sequence[Document], baselines: Mapping[str, list[bool]] | None = None,
        warmup: int = 3) -> Run:
    """Anonymise et note chaque document ; préchauffage hors chronométrage / warm-up is not timed.

    `baselines` : zones masquées des documents d'origine, pour la survie des documents mutés.
    `baselines`: masked spans of the original documents, for the survival of mutated documents.
    """
    for doc in docs[:warmup]:
        try:
            anonymizer.anonymize(doc.text)
        except Exception:  # compté plus bas / counted below
            continue
    result = Run(Tally(), [], 0.0, 0, {})
    for doc in docs:
        start = perf_counter()
        try:
            spans, output = masked_spans(anonymizer, doc.text)
        except Exception as error:  # un plantage est un résultat / a crash is a result
            # Aucune sortie (échec fermé) : document compté à part, jamais noté / fail-closed, reported apart.
            result.errors[doc.doc_id] = type(error).__name__
            continue
        result.seconds += perf_counter() - start
        result.chars += len(doc.text)
        baseline = baselines.get(doc.meta.get("base", "")) if baselines else None
        score = score_document(doc, spans, output, baseline)
        result.tally.merge(score.tally)
        result.stats.append(score.stats)
        result.masked[doc.doc_id] = score.masked
    return result


# --- Synthèse / summary ---------------------------------------------------------------------------------


def _rate(k: int, n: int) -> dict[str, Any]:
    low, high = wilson(k, n)
    return {"k": k, "n": n, "rate": ratio(k, n), "ci95": [low, high]}


def _samples(rows: Sequence[dict[str, Any]], keys: tuple[str, ...], per_bucket: int) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        bucket = buckets[tuple(row.get(k) for k in keys)]
        if len(bucket) < per_bucket:
            bucket.append(row)
    return [row for _, rows_ in sorted(buckets.items(), key=lambda kv: str(kv[0])) for row in rows_]


_MUTATION_COUNTERS = ("mutation_mentions", "mutation_masked", "mutation_chars", "mutation_hit",
                      "mutation_leak_lenient", "mutation_baseline", "mutation_survived")


def _mutation_row(counts: Mapping[str, int]) -> dict[str, Any]:
    return {
        "mention_recall": _rate(counts["mutation_masked"], counts["mutation_mentions"]),
        # Survie : parmi les mentions masquées sans mutation / survival among mentions caught unmutated.
        "survival": _rate(counts["mutation_survived"], counts["mutation_baseline"]),
        "char_recall": ratio(counts["mutation_hit"], counts["mutation_chars"]),
        "lenient_leak_rate": ratio(counts["mutation_leak_lenient"], counts["mutation_mentions"]),
    }


def _mutations(tally: Tally) -> dict[str, dict[str, Any]]:
    """Par opérateur : groupes (structurés, textuels) et détail par libellé / per operator: groups and labels."""
    per_label: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for counter_name in _MUTATION_COUNTERS:
        for (name, label), value in getattr(tally, counter_name).items():
            per_label[name][label][counter_name] += value
    summary: dict[str, dict[str, Any]] = {}
    for name, labels in sorted(per_label.items()):
        groups: dict[str, Counter[str]] = defaultdict(Counter)
        for label, counts in labels.items():
            groups[label_group(label)].update(counts)
        summary[name] = {group: _mutation_row(counts) for group, counts in sorted(groups.items())}
        summary[name]["labels"] = {label: _mutation_row(counts) for label, counts in sorted(labels.items())}
    return summary


def summarize(result: Run, *, resamples: int, seed: int, samples: int) -> dict[str, Any]:
    tally = result.tally
    docs = tally.docs
    totals = [sum(column) for column in zip(*result.stats, strict=True)] if result.stats else [0] * len(STAT_FIELDS)
    head = headline(totals, docs)
    ci = bootstrap(result.stats, headline, resamples, seed) if resamples else {}
    labels: dict[str, Any] = {}
    decoys: dict[str, Any] = {}
    for label in sorted(tally.mentions):
        n = tally.mentions[label]
        if GOLD_LABELS[label] == NO_MASK:
            decoys[label] = _rate(tally.mentions_masked[label], n)
            continue
        recall = ratio(tally.hit_chars[label], tally.gold_chars[label])
        precision = ratio(tally.pred_ok_chars[label], tally.pred_chars[label])
        labels[label] = {
            "identifier_type": GOLD_LABELS[label],
            "mentions": n,
            "mention_recall": _rate(tally.mentions_masked[label], n),
            "doc_leaks": _rate(tally.docs_leak_label[label], tally.docs_with_label[label]),
            "char_recall": recall,
            "strict_recall": ratio(tally.mentions_strict[label], n),
            "lenient_leak_rate": ratio(tally.mentions_leak_lenient[label], n),
            "typed_rate": ratio(tally.mentions_typed[label], n),
            "iou90_rate": ratio(tally.mentions_iou[label], n),
            "precision": precision,
            "f2": f_beta(precision, recall),
        }
    entities = {key: {"n": n, "masked": tally.entities_masked[key], "rate": ratio(tally.entities_masked[key], n),
                      "strict_rate": ratio(tally.entities_strict[key], n)}
                for key, n in sorted(tally.entities.items())}
    system = {label: {"spans": tally.pred_spans[label], "chars": chars,
                      "precision": ratio(tally.pred_ok_chars[label], chars),
                      "iou90_precision": ratio(tally.pred_spans_iou[label], tally.pred_spans[label])}
              for label, chars in sorted(tally.pred_chars.items())}
    false_mask_counts = Counter((row["label"], row["source"]) for row in tally.false_masks)
    return {
        "docs": docs,
        "errors": {"count": len(result.errors), "by_type": dict(Counter(result.errors.values()).most_common()),
                   "doc_ids": sorted(result.errors)[:50]},
        "chars": result.chars,
        "seconds": result.seconds,
        "ms_per_doc": 1000 * result.seconds / docs if docs else None,
        "chars_per_second": result.chars / result.seconds if result.seconds else None,
        "headline": head,
        "ci95": ci,
        "leaks": {"strict": _rate(tally.docs_leak_strict, docs),
                  "structured": _rate(tally.docs_leak_structured, docs),
                  "lenient": _rate(tally.docs_leak_lenient, docs),
                  "verbatim": _rate(tally.docs_leak_verbatim, docs)},
        "precision_detail": {"masked_chars": tally.pred_total, "on_pii": tally.pred_ok_total,
                             "on_decoys": tally.pred_on_decoys, "on_neutral_text": tally.neutral_masked,
                             "neutral_chars": tally.neutral_chars},
        "labels": labels,
        "decoys": decoys,
        "entities": entities,
        "system_labels": system,
        "kinds": {kind: {"all": _rate(tally.kind_leaks[kind], n),
                         "structured": _rate(tally.kind_leaks_structured[kind], n)}
                  for kind, n in sorted(tally.kind_docs.items())},
        "mutations": _mutations(tally),
        "confusion": [{"gold": g, "system": s, "count": c} for (g, s), c in tally.confusion.most_common() if g != s],
        "sources": dict(tally.sources.most_common()),
        "false_masks": [{"label": label, "source": source, "count": count}
                        for (label, source), count in false_mask_counts.most_common()],
        "miss_examples": _samples(tally.misses, ("label", "mutation"), samples),
        "false_mask_examples": _samples(tally.false_masks, ("label", "source"), samples),
    }


# --- Environnement / environment ----------------------------------------------------------------------


def detectors(anonymizer: Anonymizer) -> list[dict[str, str]]:
    """Détecteurs déclarés par les packs chargés / detectors declared by the loaded packs."""
    rows = []
    for pack in anonymizer.packs:
        for spec in pack.detector_specs:
            module_name, class_name = spec.split(":", 1)
            cls = getattr(importlib.import_module(module_name), class_name)
            rows.append({"pack": pack.id, "spec": spec, "id": getattr(cls, "id", class_name)})
    return rows


def environment() -> dict[str, Any]:
    def version(name: str) -> str | None:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            return None

    return {
        "date_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "gdprguardian": version("gdprguardian"),
        "faker": version("faker"),
    }


# --- Rapport Markdown / Markdown report ---------------------------------------------------------------


def _pct(value: float | None, digits: int = 1) -> str:
    return "–" if value is None else f"{100 * value:.{digits}f} %"


def _number(value: float | None) -> str:
    """Nombre lisible ; « – » si indéfini (aucun document noté) / readable number, "–" when undefined."""
    return "–" if value is None else f"{value:,.0f}"


def _pct_ci(value: float | None, ci: Sequence[float | None] | None) -> str:
    if value is None:
        return "–"
    if not ci or ci[0] is None:
        return _pct(value)
    return f"{_pct(value)} [{100 * ci[0]:.1f}–{100 * ci[1]:.1f}]"


def _table(header: Sequence[str], rows: Iterable[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def markdown(report: dict[str, Any]) -> str:
    meta = report["meta"]
    profiles = list(report["profiles"])
    base = {p: report["profiles"][p]["base"] for p in profiles}
    lines = [
        "# Évaluation Gardien RGPD – corpus synthétique / GDPR Guardian synthetic corpus evaluation",
        "",
        f"Généré le {meta['env']['date_utc']} · Gardien RGPD {meta['env']['gdprguardian']}"
        f" · Python {meta['env']['python']} · Faker {meta['env']['faker']} · graine/seed {meta['seed']}",
        f"Corpus de base : {meta['base_docs']} documents ({meta['base_chars']:,} caractères), "
        f"corpus muté : {meta['mutated_docs']} documents ({len(meta['mutations'])} opérateurs). "
        "Données entièrement synthétiques ; à ne pas confondre avec une mesure sur documents réels.",
        "Packs chargés : " + ", ".join(f"{p['id']} {p['version']}" for p in meta["packs"]) + ".",
        "",
    ]
    for profile in profiles:
        for corpus in ("base", "mutated"):
            errors = report["profiles"][profile].get(corpus, {}).get("errors", {})
            if errors.get("count"):
                lines += [f"**Attention** : {errors['count']} document(s) du corpus `{corpus}` font lever une "
                          f"exception au moteur (profil {profile}) : {errors['by_type']} ; exclus des mesures.", ""]
    lines += ["## Détecteurs déclarés / declared detectors", ""]
    lines += _table(("Pack", "Détecteur", "Zones émises (corpus de base, standard)", "État"),
                    ((d["pack"], d["id"], str(d["spans"]), "actif" if d["spans"] else "inactif (aucune zone)")
                     for d in meta["detectors"]))
    lines += ["", "## Indicateurs principaux (corpus de base) / headline metrics", "",
              "Rappel et précision au caractère alphanumérique ; IC bootstrap 95 % sur les documents.", ""]
    keys = (("recall_direct", "Rappel identifiants directs"),
            ("recall_structured", "… dont identifiants structurés (motifs, clés)"), ("recall", "Rappel direct + quasi"),
            ("precision", "Précision"), ("f2", "F2"), ("entity_recall_direct", "Rappel entités directes (TAB)"),
            ("doc_leak_rate", "Documents avec fuite (stricte, tout direct)"),
            ("doc_leak_rate_structured", "Documents avec fuite d'identifiant structuré"),
            ("over_masking", "Sur-masquage texte neutre"), ("decoy_false_mask_rate", "Leurres masqués à tort"))
    rows = [[title] + [_pct_ci(base[p]["headline"][key], base[p]["ci95"].get(key)) for p in profiles]
            for key, title in keys]
    rows.append(["Fuite souple (≥ 4 car. consécutifs)"] + [_pct(base[p]["leaks"]["lenient"]["rate"]) for p in profiles])
    rows.append(["Fuite littérale (valeur retrouvée)"] + [_pct(base[p]["leaks"]["verbatim"]["rate"]) for p in profiles])
    rows.append(["Débit (car./s, indicatif)"] + [_number(base[p]["chars_per_second"]) for p in profiles])
    rows.append(["Documents en échec (exception du moteur)"] + [str(base[p]["errors"]["count"]) for p in profiles])
    lines += _table(["Indicateur", *profiles], rows)

    lines += ["", "## Par type d'identifiant (profil standard) / per label", ""]
    ref = base.get("standard") or base[profiles[0]]
    label_rows = []
    for label, row in sorted(ref["labels"].items(), key=lambda kv: (kv[1]["identifier_type"], kv[0])):
        recall = row["mention_recall"]
        per_profile = " / ".join(_pct(base[p]["labels"].get(label, {}).get("mention_recall", {}).get("rate"))
                                 for p in profiles)
        label_rows.append([label, row["identifier_type"], str(row["mentions"]), _pct_ci(recall["rate"], recall["ci95"]),
                           _pct(row["char_recall"]), _pct(row["precision"]), _pct(row["f2"]),
                           _pct(row["doc_leaks"]["rate"]), per_profile])
    lines += _table(("Libellé", "Type", "Mentions", "Rappel mentions [IC 95 %]", "Rappel car.", "Précision",
                     "F2", "Docs avec fuite", f"Rappel ({' / '.join(profiles)})"), label_rows)

    lines += ["", "## Leurres (ne doivent pas être masqués) / decoys", ""]
    decoy_labels = sorted({label for p in profiles for label in base[p]["decoys"]})
    lines += _table(["Leurre", "Occurrences"] + [f"masqués ({p})" for p in profiles],
                    ([label, str(ref["decoys"].get(label, {}).get("n", 0))]
                     + [_pct(base[p]["decoys"].get(label, {}).get("rate")) for p in profiles]
                     for label in decoy_labels))

    lines += ["", "## Entités (TAB : toutes les mentions masquées) / entity recall", ""]
    entity_keys = [k for k in ref["entities"] if ":" not in k]
    lines += _table(["Type", "Entités", *profiles],
                    ([key, str(ref["entities"][key]["n"])]
                     + [_pct(base[p]["entities"].get(key, {}).get("rate")) for p in profiles]
                     for key in entity_keys))

    lines += ["", "## Fuites par type de document (profil standard) / leaks per document kind", ""]
    lines += _table(("Type de document", "Documents", "Fuite (tout direct)", "Fuite (identifiant structuré)"),
                    ((kind, str(v["all"]["n"]), _pct(v["all"]["rate"]), _pct(v["structured"]["rate"]))
                     for kind, v in ref["kinds"].items()))

    mutated = {p: report["profiles"][p].get("mutated") for p in profiles}
    if all(mutated.values()):
        lines += ["", "## Équipe rouge : survie aux mutations / red-team survival per operator", "",
                  "Survie = part des mentions masquées sans mutation qui le restent après mutation (n = ces "
                  "mentions). « Structurés » : identifiants à motif ou à clé ; « textuels » : personnes, adresses, "
                  "lieux, organisations (heuristiques, NER). Les libellés les plus touchés sont dans le JSON.", ""]
        families = {m["name"]: m["family"] for m in meta["mutations"]}
        lines += _table(["Opérateur", "Famille", "n structurés", *(f"survie {p}" for p in profiles),
                         "n textuels", *(f"survie {p}" for p in profiles)],
                        (_mutation_cells(mutated, profiles, name, families[name])
                         for name in (m["name"] for m in meta["mutations"])))

    lines += ["", "## Confusions de libellé (profil standard) / label confusions", ""]
    lines += _table(("Référence", "Système", "Mentions"),
                    ((row["gold"], row["system"], str(row["count"])) for row in ref["confusion"][:15]))
    lines += ["", "## Masquages hors annotation (profil standard) / masks outside gold PII", ""]
    lines += _table(("Libellé système", "Source", "Zones"),
                    ((row["label"], row["source"], str(row["count"])) for row in ref["false_masks"][:15]))
    lines += ["", "## Exemples (valeurs synthétiques, profil standard) / examples (synthetic values)", ""]
    examples = [row for row in ref["miss_examples"] if row["label"] not in TEXTUAL_LABELS][:20]
    examples += ref["false_mask_examples"][:10]
    lines += _table(("Cas", "Libellé", "Valeur", "Détail"),
                    (("faux négatif" if "visible" in row else "faux positif", row["label"], _code(row["value"]),
                      f"masqué comme {row['masked_as']}" if row.get("masked_as") else row.get("source", "–"))
                     for row in examples))
    lines.append("")
    return "\n".join(lines)


def _mutation_cells(mutated: Mapping[str, Any], profiles: Sequence[str], name: str, family: str) -> list[str]:
    reference = mutated["standard" if "standard" in mutated else profiles[0]]["mutations"].get(name, {})
    cells = [name, family]
    for group in ("structured", "textual"):
        cells.append(str(reference.get(group, {}).get("survival", {}).get("n", 0)))
        for profile in profiles:
            row = mutated[profile]["mutations"].get(name, {}).get(group)
            cells.append(_pct(row["survival"]["rate"]) if row else "–")
    return cells


def _code(value: str) -> str:
    """Valeur affichable dans un tableau Markdown / value printable in a Markdown table cell."""
    shown = value.encode("unicode_escape").decode("ascii") if not value.isprintable() else value
    return "`" + shown.replace("|", "\\|").replace("`", "'")[:60] + "`"


# --- Programme / program ------------------------------------------------------------------------------


def evaluate(docs: int, mutation_docs: int, seed: int, profiles: Sequence[str], mutation_names: str | None,
             resamples: int, samples: int, countries: str = "auto") -> dict[str, Any]:
    generator = CorpusGenerator(seed)
    base = list(generator.corpus(docs))
    mutations = select(mutation_names) if mutation_docs else ()
    subset = base[:mutation_docs]
    mutated = list(mutate_corpus(subset, mutations, seed)) if mutations else []
    report: dict[str, Any] = {"profiles": {}}
    declared: list[dict[str, str]] = []
    packs: list[dict[str, Any]] = []
    for profile in profiles:
        anonymizer = Anonymizer(profile=profile, countries=countries)
        declared = declared or detectors(anonymizer)
        packs = packs or [{"id": p.id, "version": p.version, "recognizers": len(p.recognizers),
                           "detectors": list(p.detector_specs)} for p in anonymizer.packs]
        base_run = run(anonymizer, base)
        entry = {"base": summarize(base_run, resamples=resamples, seed=seed, samples=samples)}
        if mutated:
            mutated_run = run(anonymizer, mutated, baselines=base_run.masked)
            # Un exemple par (libellé, opérateur) suffit / one example per (label, operator) is enough.
            entry["mutated"] = summarize(mutated_run, resamples=0, seed=seed, samples=min(samples, 1))
        report["profiles"][profile] = entry
    reference = report["profiles"].get("standard") or next(iter(report["profiles"].values()))
    sources = reference["base"]["sources"]
    for row in declared:
        row["spans"] = sum(c for s, c in sources.items() if s == row["id"] or s.endswith(f":{row['id']}"))
    report["meta"] = {
        "seed": seed,
        "countries": countries,
        "base_docs": len(base),
        "base_chars": sum(len(d.text) for d in base),
        "kinds": list(KINDS),
        "mutated_docs": len(mutated),
        "mutation_base_docs": len(subset),
        "mutations": [{"name": m.name, "family": m.family, "description": m.description} for m in mutations],
        "detectors": declared,
        "packs": packs,
        "env": environment(),
        "notes": ("Corpus synthétique (Faker fr_FR + lexiques) ; rappel au caractère alphanumérique ; "
                  "leurres = NO_MASK ; identifiants d'entreprise de personnes morales = NO_MASK."),
    }
    return report


def int_at_least(minimum: int) -> Callable[[str], int]:
    """Type argparse : entier ≥ `minimum` / argparse type: integer >= `minimum`."""

    def parse(raw: str) -> int:
        value = int(raw)
        if value < minimum:
            raise argparse.ArgumentTypeError(f"{value} < {minimum}")
        return value

    return parse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Évaluation Gardien RGPD / GDPR Guardian evaluation")
    count, non_negative = int_at_least(1), int_at_least(0)
    parser.add_argument("--docs", type=count, default=540, help="documents de base / base documents")
    parser.add_argument("--mutation-docs", type=non_negative, default=135, help="base de l'équipe rouge (0 = aucune)")
    parser.add_argument("--mutations", default=None, help="opérateurs (virgules) / operators (comma-separated)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--profiles", default=",".join(PROFILES))
    parser.add_argument("--countries", default="auto", help="auto, all ou liste / auto, all or list (FR,BE)")
    parser.add_argument("--bootstrap", type=non_negative, default=1000, help="rééchantillonnages / resamples (0 = off)")
    parser.add_argument("--samples", type=non_negative, default=3, help="exemples par catégorie / examples per bucket")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks" / "results")
    parser.add_argument("--name", default="eval")
    args = parser.parse_args(argv)
    profiles = tuple(p.strip() for p in args.profiles.split(",") if p.strip())
    if set(profiles) - set(PROFILES):
        parser.error(f"profils inconnus / unknown profiles: {sorted(set(profiles) - set(PROFILES))}")
    started = perf_counter()
    report = evaluate(args.docs, args.mutation_docs, args.seed, profiles, args.mutations, args.bootstrap,
                      args.samples, args.countries)
    report["meta"]["wall_seconds"] = round(perf_counter() - started, 2)
    args.out.mkdir(parents=True, exist_ok=True)
    json_path, md_path = args.out / f"{args.name}.json", args.out / f"{args.name}.md"
    # Fins de ligne LF sur tous les systèmes (rapports comparables) / LF everywhere (comparable reports).
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(markdown(report), encoding="utf-8", newline="\n")
    for profile, entry in report["profiles"].items():
        head = entry["base"]["headline"]
        print(f"{profile:9} rappel direct {_pct(head['recall_direct'])}  précision {_pct(head['precision'])}  "
              f"F2 {_pct(head['f2'])}  fuites {_pct(head['doc_leak_rate'])}  "
              f"sur-masquage {_pct(head['over_masking'], 2)}")
    print(f"-> {json_path}\n-> {md_path}  ({report['meta']['wall_seconds']} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
