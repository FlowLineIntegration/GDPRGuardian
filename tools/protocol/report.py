"""Résultats de la campagne : JSON et Markdown, scores seulement / campaign results, scores only.

Chiffres publiés (docs/PROTOCOLE.md, section 6 et « Version 1.1 ») : les deux indices, « documents normalisés »
(l'indice de confiance principal) et « documents difficiles » (équipe rouge, détail par groupe), chacun avec son IC et
son rappel des mentions directes ; détail par famille, par corpus, par type d'identifiant, par opérateur d'équipe rouge
et par graine, autres langues (hors périmètre), témoin négatif Judilibre, garde-fous, et les clés du site.
Published figures: the two indexes, "normalised documents" (the headline confidence index) and "difficult documents"
(red team, per-group breakdown), each with its CI and direct-mention recall; per family, corpus, identifier type,
red-team operator and seed, other languages (out of scope), Judilibre negative control, guards, and the site keys.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from tools.corpus.evaluate_real import headline as real_headline
from tools.corpus.real_common import PERSONAL
from tools.eval.schema import DIRECT, GOLD_LABELS, NO_MASK
from tools.protocol import spec
from tools.protocol.campaign import State
from tools.protocol.outcomes import REAL_FIELDS, Cell, merge_cells
from tools.protocol.plan import Plan
from tools.protocol.stats import (
    bootstrap_index,
    bootstrap_pooled,
    bootstrap_ratio,
    family_rates,
    index_point,
    pooled_point,
    wilson,
)

# Indice « documents normalisés » : clés historiques du site ; indice « documents difficiles » : clés hard_* (1.1).
# "Normalised documents" index: the site's historical keys; "difficult documents" index: hard_* keys (1.1).
QUALITY_KEYS = ("confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct", "protocol_docs",
                "protocol_families", "real_corpora", "real_docs", "protocol_date", "protocol_engine")
HARD_QUALITY_KEYS = ("hard_index", "hard_ci_low", "hard_ci_high", "hard_docs", "hard_mention_recall_pct")


def _ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def _pct(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(100 * value, digits)


def _cells(state: State, prefix: str, splits: Iterable[str] | None = None) -> list[Cell]:
    """Cellules d'un préfixe (« synthetic_fr/ », « bodacc_fr/test »…) / cells under a prefix."""
    out = []
    for key, cell in state.cells.items():
        head, _, tail = key.partition("/")
        if head != prefix:
            continue
        if splits is not None and tail not in splits:
            continue
        out.append(cell)
    return out


def family_cell(state: State, family: spec.Family, splits: Sequence[str]) -> Cell:
    if family.kind == "synthetic":
        return merge_cells(_cells(state, "synthetic_fr"))
    if family.kind == "redteam":
        # Seuls les opérateurs de la famille (1.1) / only the family's operators (1.1).
        keep = {f"op={name}" for name in family.operators}
        return merge_cells(cell for key, cell in state.cells.items()
                           if key.partition("/")[0] == "redteam_fr" and key.partition("/")[2] in keep)
    return merge_cells(c for corpus in family.corpora for c in _cells(state, corpus, splits))


def operator_group(name: str) -> str | None:
    """Groupe d'un opérateur d'équipe rouge (spec.REDTEAM_GROUPS) / red-team operator group."""
    return next((group for group, names in spec.REDTEAM_GROUPS.items() if name in names), None)


def family_entry(state: State, family: spec.Family, resamples: int, seed: int) -> tuple[dict[str, Any], Cell, Cell,
                                                                                     Cell]:
    """Résumé d'une famille (moitié test, tous, dev) et ses cellules / family summary and its cells."""
    test_cell = family_cell(state, family, (spec.HEADLINE_SPLIT,))
    all_cell = family_cell(state, family, ("dev", "test"))
    dev_cell = family_cell(state, family, ("dev",))
    entry: dict[str, Any] = {"title_fr": family.title_fr, "title_en": family.title_en, "kind": family.kind,
                             "corpora": list(family.corpora), "headline": outcome_summary(test_cell)}
    if family.operators:
        entry["operators"] = list(family.operators)
    if family.kind == "real":
        entry["all_docs"] = outcome_summary(all_cell)
        entry["dev_half"] = outcome_summary(dev_cell)
        entry["measures"] = real_measures(test_cell, family.corpora[0] if len(family.corpora) == 1 else family.name,
                                          resamples, seed)
        entry["measures_all_docs"] = real_measures(all_cell, family.name, resamples, seed)
    else:
        entry["measures"] = synthetic_measures(test_cell)
    return entry, test_cell, all_cell, dev_cell


def _labels(cell: Cell) -> dict[str, Any]:
    return {label: {"mentions": n, "masked": cell.label_masked.get(label, 0),
                    "recall": _ratio(cell.label_masked.get(label, 0), n)}
            for label, n in sorted(cell.label_mentions.items())}


def outcome_summary(cell: Cell) -> dict[str, Any]:
    """Issue protocole d'un ensemble de documents / protocol outcome of a document set."""
    rate, recall = family_rates(cell.hist)
    interval = wilson(cell.passed, cell.scored)
    return {"docs": cell.docs, "chars": cell.chars, "scored": cell.scored, "no_direct": cell.no_direct,
            "passed": cell.passed, "no_leak_rate": rate, "no_leak_ci95_wilson": list(interval) if interval else None,
            "mentions": cell.mention_total, "mentions_masked": cell.mention_masked, "mention_recall": recall,
            "errors": dict(cell.errors), "ambiguous_docs": cell.ambiguous_docs,
            "ambiguous_segments": cell.ambiguous_segments, "placeholders": cell.placeholders,
            "per_label": _labels(cell)}


def synthetic_measures(cell: Cell) -> dict[str, Any]:
    """Mesures de tools.eval depuis le compteur additif / tools.eval measures from the additive tally."""
    t = cell.tally
    if t is None:
        return {}
    direct = [label for label in t.gold_chars if GOLD_LABELS.get(label) == DIRECT]
    textual = {"PERSON", "ADDRESS", "LOCATION", "ORG"}
    gold = sum(t.gold_chars.values())
    hit = sum(t.hit_chars.values())
    direct_gold = sum(t.gold_chars[label] for label in direct)
    direct_hit = sum(t.hit_chars[label] for label in direct)
    structured_gold = sum(t.gold_chars[label] for label in direct if label not in textual)
    structured_hit = sum(t.hit_chars[label] for label in direct if label not in textual)
    decoys = sum(n for label, n in t.mentions.items() if GOLD_LABELS.get(label) == NO_MASK)
    decoys_hit = sum(n for label, n in t.mentions_masked.items() if GOLD_LABELS.get(label) == NO_MASK)
    return {
        "docs_scored": t.docs,
        "recall_direct_chars": _ratio(direct_hit, direct_gold),
        "recall_structured_chars": _ratio(structured_hit, structured_gold),
        "recall_chars": _ratio(hit, gold),
        "precision": _ratio(t.pred_ok_total, t.pred_total),
        "over_masking": _ratio(t.neutral_masked, t.neutral_chars),
        "decoy_false_mask_rate": _ratio(decoys_hit, decoys),
        "decoys": decoys,
        "doc_leak_rate_eval": _ratio(t.docs_leak_strict, t.docs),
        "doc_leak_rate_structured_eval": _ratio(t.docs_leak_structured, t.docs),
        "doc_literal_leak_rate_eval": _ratio(t.docs_leak_verbatim, t.docs),
        "entity_recall_direct": _ratio(t.entities_masked.get(DIRECT, 0), t.entities.get(DIRECT, 0)),
    }


def real_measures(cell: Cell, corpus: str, resamples: int, seed: int) -> dict[str, Any]:
    """Mesures de tools.corpus (évaluateur réel) et IC de la précision / tools.corpus measures, precision CI."""
    docs = len(cell.vectors)
    if not docs:
        return {}
    families = [f for f in PERSONAL if cell.real.get(f"g_{f}", 0)]
    totals = {k: cell.real.get(k, 0) for k in REAL_FIELDS}
    metrics = real_headline(totals, docs, families)
    if corpus in spec.PARTIAL_GOLD:
        metrics["precision"] = metrics["over_masking"] = None
    index = {name: i for i, name in enumerate(REAL_FIELDS)}
    precision_ci = None
    if metrics.get("precision") is not None:
        # Ordre canonique : l'IC ne dépend pas de l'ordre d'arrivée des unités / canonical order, CI independent of
        # the order in which units finished.
        pairs = sorted((v[index["c_pred_tp"]], v[index["c_pred"]]) for v in cell.vectors)
        precision_ci = bootstrap_ratio(pairs, resamples, seed)
    return {"metrics": metrics, "precision_ci95": list(precision_ci) if precision_ci else None,
            "detections": totals["detections"], "chars": totals["chars"]}


def _digest(state: State, plan: Plan, kind: str) -> str:
    h = hashlib.sha256()
    for unit in plan.units:
        if unit.kind == kind and unit.uid in state.done:
            h.update(state.done[unit.uid]["digest"].encode())
    return h.hexdigest()


def _guards(state: State, families: Mapping[str, Any]) -> dict[str, Any]:
    synthetic = merge_cells(_cells(state, "synthetic_fr") + _cells(state, "redteam_fr"))
    t = synthetic.tally
    overmask = _ratio(t.neutral_masked, t.neutral_chars) if t else None
    decoy = families["synthetic_fr"]["measures"].get("decoy_false_mask_rate")
    precision = {name: families[name]["measures"].get("metrics", {}).get("precision")
                 for name in spec.GUARD_PRECISION_FAMILIES}
    checks = {
        "overmask_synthetic": {"value": overmask, "max": spec.GUARD_MAX_OVERMASK,
                               "passed": overmask is not None and overmask <= spec.GUARD_MAX_OVERMASK},
        "decoys_masked_synthetic": {"value": decoy, "max": spec.GUARD_MAX_DECOY_MASKED,
                                    "passed": decoy is not None and decoy <= spec.GUARD_MAX_DECOY_MASKED},
        **{f"precision_{name}": {"value": value, "min": spec.GUARD_MIN_PRECISION,
                                  "passed": value is not None and value >= spec.GUARD_MIN_PRECISION}
           for name, value in precision.items()},
    }
    return {"checks": checks, "passed": all(c["passed"] for c in checks.values())}


def engine_label(engine: Mapping[str, Any]) -> str | None:
    """« 1.0.0+<12 caractères de l'image> » : deux moteurs de même version restent distincts / version+image."""
    version = engine.get("version")
    if version is None:
        return None
    image = str(engine.get("image") or "")
    digest = image.split(":", 1)[-1]
    if len(digest) >= 12 and all(c in "0123456789abcdef" for c in digest[:12]):
        return f"{version}+{digest[:12]}"
    return str(version)


def registration_check(state: State, plan: Plan, standard: bool) -> dict[str, Any]:
    """Ce qui a été envoyé, comparé au décompte enregistré (plan standard seulement) / sent vs registered."""
    from tools.protocol.provenance import plan_matches_registration

    documents = {group: sum(c.docs for k, c in state.cells.items() if k.split("/", 1)[0] == group)
                 for group in ("synthetic_fr", "redteam_bases", "redteam_fr")}
    observed = {"faker": state.tool.get("faker"), "documents": documents,
                "synthetic_sha256": _digest(state, plan, "synthetic"),
                "redteam_sha256": _digest(state, plan, "redteam")}
    return {"expected": spec.REGISTERED_PLAN, "observed": observed,
            "fingerprints_match_registration": plan_matches_registration(observed) if standard else None,
            "tool": state.tool,
            # Ce que les moitiés test ont déjà vu (docs/PROTOCOLE.md, section 3) / what the test halves already saw.
            "test_halves_measured_before": [dict(item) for item in spec.TEST_HALVES_MEASURED_BEFORE],
            "earlier_campaigns": [dict(item) for item in spec.EARLIER_CAMPAIGNS]}


def disclosure_text(item: str) -> dict[str, str]:
    """Écart déclaré : code, détail, explication FR et EN / disclosed departure, explained."""
    code, _, detail = item.partition(":")
    fr, en = spec.DISCLOSURES.get(code, ("écart non reconnu", "unknown departure"))
    return {"code": code, "detail": detail, "fr": fr, "en": en}


def build_report(state: State, plan: Plan, *, standard: bool = False, resamples: int = spec.BOOTSTRAP_RESAMPLES,
                 seed: int = spec.BOOTSTRAP_SEED) -> dict[str, Any]:
    complete = all(u.uid in state.done for u in plan.units)
    families: dict[str, Any] = {}
    headline_hists = []
    all_hists = []
    dev_hists = []
    for family in spec.FAMILIES:
        entry, test_cell, all_cell, dev_cell = family_entry(state, family, resamples, seed)
        families[family.name] = entry
        headline_hists.append(test_cell.hist)
        all_hists.append(all_cell.hist)
        dev_hists.append(dev_cell.hist if family.kind == "real" else test_cell.hist)
    point, recall = index_point(headline_hists)
    intervals = bootstrap_index(headline_hists, resamples, seed)
    all_point, all_recall = index_point(all_hists)
    dev_point, dev_recall = index_point(dev_hists)
    # Hors de l'indice « documents normalisés », mêmes mesures (1.1) : les groupes de l'équipe rouge, qui font l'indice
    # « documents difficiles » ("index": "hard"), puis presse ancienne et MAPA FR (dans aucun indice). Une seule section
    # du résultat, que le site lit déjà (site/tools/protocol_table.py). Outside the normalised index, same measures:
    # the red-team groups, which make the difficult index, then old press and MAPA FR (in neither index); one results
    # section, which the site already reads.
    apart: dict[str, Any] = {}
    hard_hists = []
    for family in spec.HARD_FAMILIES:
        entry, test_cell, _, _ = family_entry(state, family, resamples, seed)
        apart[family.name] = {**entry, "index": "hard"}
        hard_hists.append(test_cell.hist)
    for family in spec.APART_FAMILIES:
        apart[family.name] = {**family_entry(state, family, resamples, seed)[0], "index": None}
    hard_point, hard_recall = pooled_point(hard_hists)
    hard_intervals = bootstrap_pooled(hard_hists, resamples, seed)
    hard_scored = sum(sum(h.values()) for h in hard_hists)
    hard_groups = {}
    for group, name in spec.HARD_GROUP_FAMILY.items():
        h = apart[name]["headline"]
        hard_groups[group] = {"family": name, "operators": len(spec.REDTEAM_GROUPS[group]), "scored": h["scored"],
                              "passed": h["passed"], "weight": _ratio(h["scored"], hard_scored),
                              "no_leak_rate": h["no_leak_rate"], "no_leak_ci95_wilson": h["no_leak_ci95_wilson"],
                              "mention_recall": h["mention_recall"]}

    # Corpus de l'indice, corpus français publiés à part et autres langues, chacun dans sa section.
    # Index corpora, French corpora published apart and other languages, each in its own section.
    corpora: dict[str, Any] = {}
    french_apart: dict[str, Any] = {}
    out_of_scope: dict[str, Any] = {}
    for corpus in spec.REAL_CORPORA:
        if corpus in spec.NEGATIVE_CONTROL:
            continue
        per_split = {}
        for split in ("test", "dev"):
            cell = merge_cells(_cells(state, corpus, (split,)))
            per_split[split] = {"outcome": outcome_summary(cell), "measures": real_measures(cell, corpus, resamples,
                                                                                             seed)}
        whole = merge_cells(_cells(state, corpus))
        per_split["all"] = {"outcome": outcome_summary(whole), "measures": real_measures(whole, corpus, resamples,
                                                                                          seed)}
        if corpus in spec.OUT_OF_SCOPE:
            target, scope = out_of_scope, "out_of_scope"
        elif corpus in spec.INDEX_CORPORA:
            target, scope = corpora, "french"
        else:
            target, scope = french_apart, "french_apart"
        target[corpus] = {"countries": spec.REAL_CORPORA[corpus], "scope": scope, **per_split}

    control = {}
    for corpus in spec.NEGATIVE_CONTROL:
        cell = merge_cells(_cells(state, corpus))
        totals = {k: cell.real.get(k, 0) for k in REAL_FIELDS}
        docs = len(cell.vectors)
        control[corpus] = {"docs": cell.docs, "chars": cell.chars, "errors": dict(cell.errors),
                           "masked_spans": totals["detections"],
                           "masked_spans_per_10k_chars": _ratio(10_000 * totals["detections"], totals["chars"]),
                           "docs_with_masked_span": _ratio(totals["d_detection"], docs),
                           "note": "pas de gold : précision seulement par relecture manuelle / no gold: precision "
                                   "only through a manual review (docs/CORPUS_REELS.md, section 7)"}

    operators = {}
    for key, cell in sorted(state.cells.items()):
        if key.startswith("redteam_fr/op="):
            t = cell.tally
            survival = None
            if t is not None:
                base = sum(t.mutation_baseline.values())
                survival = _ratio(sum(t.mutation_survived.values()), base)
            rate, mention_recall = family_rates(cell.hist)
            name = key.split("=", 1)[1]
            operators[name] = {"group": operator_group(name), "docs": cell.docs, "no_leak_rate": rate,
                               "mention_recall": mention_recall, "survival": survival, "errors": dict(cell.errors)}
    seeds = {}
    for key, cell in sorted(state.cells.items()):
        if key.startswith(("synthetic_fr/seed=", "redteam_bases/seed=")):
            rate, mention_recall = family_rates(cell.hist)
            seeds[key] = {"docs": cell.docs, "no_leak_rate": rate, "mention_recall": mention_recall}

    errors: Counter[str] = Counter()
    ambiguous = 0
    for cell in state.cells.values():
        errors.update(cell.errors)
        ambiguous += cell.ambiguous_docs
    docs_total = state.docs
    real_annotated = [c for c in spec.REAL_CORPORA if c not in spec.NEGATIVE_CONTROL]
    real_docs = sum(merge_cells(_cells(state, c)).docs for c in real_annotated)
    guards = _guards(state, families)
    low, high = intervals["index"] or (None, None)
    quality = {
        "confidence_index": _pct(point), "confidence_ci_low": _pct(low), "confidence_ci_high": _pct(high),
        "mention_recall_pct": _pct(recall), "protocol_docs": docs_total, "protocol_families": len(spec.FAMILIES),
        "real_corpora": sum(1 for c in real_annotated if merge_cells(_cells(state, c)).docs),
        "real_docs": real_docs, "protocol_date": state.started, "protocol_engine": engine_label(state.engine),
    }
    hard_low, hard_high = hard_intervals["index"] or (None, None)
    quality.update({"hard_index": _pct(hard_point), "hard_ci_low": _pct(hard_low), "hard_ci_high": _pct(hard_high),
                    "hard_docs": hard_scored, "hard_mention_recall_pct": _pct(hard_recall)})
    return {
        "protocol": {"version": spec.PROTOCOL_VERSION, "registered": spec.PROTOCOL_REGISTERED,
                     "definition": "docs/PROTOCOLE.md", "spec": "tools/protocol/spec.py",
                     "use_case": {"fr": spec.USE_CASE[0], "en": spec.USE_CASE[1]},
                     "previous_versions": [dict(item) for item in spec.PREVIOUS_VERSIONS]},
        "registration": registration_check(state, plan, standard),
        "campaign": {
            "complete": complete, "standard_plan": standard, "date": state.started, "engine": state.engine,
            "plan_id": state.plan_id, "units_done": len(state.done), "units_planned": len(plan.units),
            "docs": docs_total, "local_principal": bool(state.runs) and all(r.get("local_principal", False)
                                                                            for r in state.runs),
            "engine_checks": state.engine_checks, "engine_check_docs": state.engine_check_docs,
            "real_pack_wiped": state.real_wiped,
            "disclosures": [disclosure_text(item) for item in state.disclosures],
            "active_seconds": round(state.active_s, 1),
            "docs_per_second": round(docs_total / state.active_s, 1) if state.active_s else None,
            "throttled_seconds": round(state.throttled_s, 1), "retries": dict(state.retries),
            "errors": dict(errors), "ambiguous_docs": ambiguous, "runs": state.runs,
            "route": f"POST {spec.TEXT_ROUTE} on the service Unix socket, LOCAL principal (local token): "
                     "counted as \"protocol\" in the public statistics",
            "options": {"profile": spec.PROFILE, "label_language": spec.LABEL_LANGUAGE,
                        "countries_french_scope": spec.FRENCH_COUNTRIES},
        },
        "confidence_index": {
            "index": "normalised", "title_fr": spec.INDEXES["normalised"][0],
            "title_en": spec.INDEXES["normalised"][1], "target": spec.NORMALISED_TARGET,
            "value": point, "ci95": list(intervals["index"]) if intervals["index"] else None,
            "mention_recall": recall,
            "mention_recall_ci95": list(intervals["mention_recall"]) if intervals["mention_recall"] else None,
            "families": [f.name for f in spec.FAMILIES], "weights": f"equal (1/{len(spec.FAMILIES)} each)",
            "real_split": spec.HEADLINE_SPLIT, "bootstrap": {"resamples": resamples, "seed": seed,
                                                              "method": "stratified by family, multinomial over "
                                                                        "per-document outcomes (exact)"},
        },
        "hard_index": {
            "index": "hard", "title_fr": spec.INDEXES["hard"][0], "title_en": spec.INDEXES["hard"][1],
            "value": hard_point, "ci95": list(hard_intervals["index"]) if hard_intervals["index"] else None,
            "mention_recall": hard_recall,
            "mention_recall_ci95": (list(hard_intervals["mention_recall"]) if hard_intervals["mention_recall"]
                                    else None),
            "docs": hard_scored, "families": [f.name for f in spec.HARD_FAMILIES],
            "operators": sum(len(f.operators) for f in spec.HARD_FAMILIES),
            "weights": "every mutated document counts once (all operators pooled; a group weighs its share of the "
                       "documents)",
            "groups": hard_groups,
            "bootstrap": {"resamples": resamples, "seed": seed,
                          "method": "stratified by red-team group, multinomial over per-document outcomes (exact); "
                                    "mutated documents of one base document are not resampled together"},
        },
        "confidence_index_all_real_docs": {"value": all_point, "mention_recall": all_recall},
        "confidence_index_dev_real_docs": {"value": dev_point, "mention_recall": dev_recall},
        "families": families,
        "families_apart": apart,
        "corpora": corpora,
        "corpora_french_apart": french_apart,
        "out_of_scope": out_of_scope,
        "negative_control": control,
        "redteam_operators": operators,
        "seeds": seeds,
        "guards": guards,
        "fingerprints": {"plan_id": state.plan_id, "synthetic_sha256": _digest(state, plan, "synthetic"),
                         "redteam_sha256": _digest(state, plan, "redteam"), "real_sha256": state.real_sources},
        "quality_keys": quality,
    }


# --- Markdown ------------------------------------------------------------------------------------------------------


def _p(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{100 * value:.{digits}f} %"


def _ci(interval: Sequence[float] | None) -> str:
    return "" if not interval else f" [{100 * interval[0]:.1f}–{100 * interval[1]:.1f}]"


def _short(value: Any) -> str:
    return "—" if not value else str(value).split(":", 1)[-1][:12]


def _family_table(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    lines = ["| Famille / family | Documents notés / scored | Sans fuite / no leak [Wilson 95 %] | Rappel mentions / "
             "mention recall | Précision / precision | Erreurs / errors |", "|---|---:|---|---|---|---|"]
    for f in rows:
        h = f["headline"]
        m = f.get("measures", {})
        precision = m.get("precision") if f["kind"] != "real" else m.get("metrics", {}).get("precision")
        lines.append(f"| {f['title_fr']} / {f['title_en']} | {h['scored']:,} | {_p(h['no_leak_rate'])}"
                     f"{_ci(h['no_leak_ci95_wilson'])} | {_p(h['mention_recall'])} | {_p(precision)} | "
                     f"{sum(h['errors'].values())} |")
    return lines


def _corpus_table(rows: Mapping[str, Any]) -> list[str]:
    lines = ["| Corpus | Pays / countries | Sans fuite test / dev / all | Rappel mentions test / all | "
             "Précision test / all |", "|---|---|---|---|---|"]
    for name, row in rows.items():
        t, d, a = row["test"], row["dev"], row["all"]
        lines.append(
            f"| {name} | {row['countries']} | {_p(t['outcome']['no_leak_rate'])} / "
            f"{_p(d['outcome']['no_leak_rate'])} / {_p(a['outcome']['no_leak_rate'])} | "
            f"{_p(t['outcome']['mention_recall'])} / {_p(a['outcome']['mention_recall'])} | "
            f"{_p(t['measures'].get('metrics', {}).get('precision'))} / "
            f"{_p(a['measures'].get('metrics', {}).get('precision'))} |")
    return lines


def to_markdown(report: Mapping[str, Any]) -> str:
    c = report["campaign"]
    ci = report["confidence_index"]
    q = report["quality_keys"]
    reg = report.get("registration", {})
    tool = reg.get("tool") or {}
    engine = c["engine"]
    lines = [f"# Protocole public Gardien RGPD · GDPR Guardian public protocol — {c['date']}", ""]
    if not c.get("standard_plan"):
        lines += [f"> **PLAN RÉDUIT — essai, jamais publié / SCALED PLAN — trial, never published** (plan "
                  f"{c['plan_id']}). Ces chiffres ne sont pas un résultat du protocole / these figures are not a "
                  "protocol result.", ""]
    if not c.get("local_principal"):
        lines += ["> **Jeton local absent ou refusé : requêtes comptées comme publiques / local token missing or "
                  "refused: requests counted as public.**", ""]
    disclosures = c.get("disclosures") or []
    if disclosures:
        lines += ["> **Écarts déclarés / disclosed departures**"]
        for d in disclosures:
            detail = f" ({d['detail']})" if d.get("detail") else ""
            lines.append(f"> - {d['fr']} / {d['en']}{detail}")
        lines += [""]
    match = reg.get("fingerprints_match_registration")
    lines += [
        f"Protocole {report['protocol']['version']} (écrit le {report['protocol']['registered']}, "
        "docs/PROTOCOLE.md). Scores seulement : aucun texte, aucune valeur annotée. "
        "Scores only: no text, no annotated value.",
        "",
    ]
    previous = report["protocol"].get("previous_versions") or []
    if previous:
        lines += ["Versions précédentes, résultats gardés publiés / previous versions, results kept published : "
                  + " ; ".join(f"{p.get('version')} : {p.get('confidence_index')} ({p.get('families')} familles / "
                               f"families, campagne / campaign {p.get('campaign')}, {p.get('results')})"
                               for p in previous) + ".", ""]
    earlier = reg.get("earlier_campaigns") or []
    if earlier:
        # Dérogation déclarée à la section 3 (données neuves) / declared departure from section 3 (fresh data).
        lines += ["> **Moitiés `test` non aveugles / test halves not blind** : déjà notées par la campagne "
                  + ", ".join(f"{e.get('date')} ({e.get('engine')})" for e in earlier)
                  + ", scores par famille publiés pendant la mise au point du moteur : chiffres des corpus réels "
                  "optimistes (docs/PROTOCOLE.md, « Version 1.1 ») / already scored by that campaign, per-family "
                  "scores published while the engine was tuned: real-corpus figures are optimistic.", ""]
    lines += [
        f"- Campagne / campaign : {'terminée / complete' if c['complete'] else '**INCOMPLÈTE / INCOMPLETE**'} ; "
        f"plan {c['plan_id']} ; {c['docs']:,} documents ; {c['units_done']}/{c['units_planned']} unités ; "
        f"{c['active_seconds']:,} s actives, {c['docs_per_second']} doc/s ; ralenti pour les visiteurs / yielded to "
        f"visitors {c['throttled_seconds']:,} s.",
        f"- Moteur / engine : {q['protocol_engine']} (image {_short(engine.get('image'))}, packs "
        f"{_short(engine.get('packs_sha256'))}, sonde / probe {_short(engine.get('probe_sha256'))} sur "
        f"{engine.get('probe_docs')} documents) ; contrôlé / checked {c.get('engine_checks', 0)} fois / times, "
        "identique à chaque fois / identical every time.",
        f"- Enregistrement / registration : empreintes du plan conformes / plan fingerprints match: "
        f"{'—' if match is None else ('oui / yes' if match else '**NON / NO**')} ; outil / tool "
        f"{_short(tool.get('tools_sha256'))}, spec.py {_short(tool.get('spec_sha256'))}, PROTOCOLE.md "
        f"{_short(tool.get('protocole_md_sha256'))}, paquet / bundle {_short(tool.get('bundle_sha256'))}, Faker "
        f"{tool.get('faker', '—')}.",
        f"- Erreurs du service (comptées comme fuites) / service errors (counted as leaks) : {c['errors'] or 0} ; "
        f"documents à alignement ambigu (comptés prudemment) / ambiguous alignments (scored conservatively) : "
        f"{c['ambiguous_docs']}.",
        f"- Moitiés test déjà mesurées avant cette campagne / test halves measured before this campaign : "
        f"{len(reg.get('test_halves_measured_before') or [])} mesures (docs/PROTOCOLE.md, section 3) ; campagnes "
        f"antérieures / earlier campaigns : "
        + (", ".join(f"{e.get('date')} ({e.get('engine')})" for e in reg.get("earlier_campaigns") or [])
           or "aucune / none") + ".",
        "",
        "Deux indices, même mesure : part des documents dont aucun identifiant direct ne reste lisible (pas un seul "
        "caractère alphanumérique d'une mention du gold). Les intervalles ne couvrent que le tirage des documents. "
        "Two indexes, same measure: share of documents in which no direct identifier stays readable (not one "
        "alphanumeric character of a gold mention). The intervals cover document sampling only.",
        "",
        "## Indice de confiance, documents normalisés / confidence index, normalised documents",
        "",
        f"**{_p(ci['value'])}**{_ci(ci['ci95'])} — moyenne à poids égal des {len(ci['families'])} familles "
        f"(moitié test des corpus réels) ; cible / target ≥ {_p(ci.get('target'), 0)}. Equal-weight mean of the "
        f"{len(ci['families'])} families (test half of the real corpora).",
        "",
        f"Rappel des mentions directes / direct-mention recall : **{_p(ci['mention_recall'])}**"
        f"{_ci(ci['mention_recall_ci95'])}. Tous les documents réels (dev + test) / all real documents : "
        f"{_p(report['confidence_index_all_real_docs']['value'])} ; moitié dev (règles conçues dessus) / dev half "
        f"(rules designed on it) : {_p(report['confidence_index_dev_real_docs']['value'])}.",
        "",
    ]
    lines += _family_table(report["families"].values())
    lines += ["", "## Par corpus réel de l'indice / per index real corpus (test · dev · all)", ""]
    lines += _corpus_table(report["corpora"])
    hard = report.get("hard_index") or {}
    apart_rows = report.get("families_apart") or {}
    lines += ["", "## Documents difficiles / difficult documents", "",
              f"**{_p(hard.get('value'))}**{_ci(hard.get('ci95'))} — équipe rouge, {hard.get('operators')} "
              f"opérateurs, {hard.get('docs') or 0:,} documents mutés notés : chaque document muté compte une fois "
              "(un groupe pèse sa part des documents), intervalle par bootstrap stratifié par groupe. Red team, "
              f"{hard.get('operators')} operators: every mutated document counts once (a group weighs its share of "
              "the documents), interval by a bootstrap stratified by group. Rappel des mentions / mention recall : "
              f"{_p(hard.get('mention_recall'))}{_ci(hard.get('mention_recall_ci95'))}.", "",
              "| Groupe / group | Opérateurs | Documents notés / scored | Poids / weight | Sans fuite / no leak "
              "[Wilson 95 %] | Rappel mentions / mention recall |", "|---|---:|---:|---:|---|---|"]
    group_titles = {"everyday": "Formats du quotidien abîmés / damaged everyday formats",
                    "obfuscation": "Déguisements volontaires / deliberate obfuscations",
                    "ocr": "Bruit d'OCR / OCR noise"}
    for group, row in (hard.get("groups") or {}).items():
        lines.append(f"| {group_titles.get(group, group)} | {row['operators']} | {row['scored']:,} | "
                     f"{_p(row['weight'])} | {_p(row['no_leak_rate'])}{_ci(row['no_leak_ci95_wilson'])} | "
                     f"{_p(row['mention_recall'])} |")
    lines += ["", *_family_table(row for row in apart_rows.values() if row.get("index") == "hard")]
    lines += ["", "## Publiés à part, dans aucun indice / published apart, in neither index", "",
              "Presse ancienne (OCR de mauvaise qualité : performance dégradée), MAPA FR (textes juridiques de l'UE, "
              "trop peu de documents). Mêmes mesures. Old press (low-quality OCR: degraded performance), MAPA FR (EU "
              "legal texts, too few documents). Same measures.", ""]
    lines += _family_table(row for row in apart_rows.values() if row.get("index") != "hard")
    if report.get("corpora_french_apart"):
        lines += ["", *_corpus_table(report["corpora_french_apart"])]
    lines += ["", "## Autres langues, hors périmètre : jamais dans l'indice / other languages, out of scope: never in "
              "the index", "",
              "Mêmes mesures que le périmètre français, publiées à part : elles disent ce que le service fait des "
              "documents d'autres pays. Same measures as the French scope, published apart: they show what the "
              "service does with documents from other countries.", ""]
    lines += _corpus_table(report.get("out_of_scope") or {})
    lines += ["", "## Témoin négatif / negative control", ""]
    for name, row in report["negative_control"].items():
        density = row["masked_spans_per_10k_chars"]
        lines.append(f"- {name} : {row['docs']:,} décisions, {row['masked_spans']:,} zones masquées "
                     f"({'—' if density is None else f'{density:.1f}'} pour 10 000 caractères / per 10,000 chars), "
                     f"{_p(row['docs_with_masked_span'])} des documents avec au moins une zone. {row['note']}")
    lines += ["", "## Équipe rouge par opérateur / red team per operator", "",
              "Les trois groupes font l'indice « documents difficiles » ; aucun n'est dans l'indice « documents "
              "normalisés ». The three groups make the difficult-documents index; none is in the normalised one.", "",
              "| Opérateur | Groupe / group | Documents | Sans fuite / no leak | Rappel mentions | Survie / survival |",
              "|---|---|---:|---|---|---|"]
    group_names = {"everyday": "quotidien / everyday", "obfuscation": "déguisement / obfuscation", "ocr": "OCR"}
    for name, row in report["redteam_operators"].items():
        group = group_names.get(row.get("group") or "", "—")
        lines.append(f"| {name} | {group} | {row['docs']:,} | {_p(row['no_leak_rate'])} | "
                     f"{_p(row['mention_recall'])} | {_p(row['survival'])} |")
    lines += ["", "## Garde-fous / guards", ""]
    for name, g in report["guards"]["checks"].items():
        bound = f"≤ {_p(g['max'])}" if "max" in g else f"≥ {_p(g['min'])}"
        lines.append(f"- {name} : {_p(g['value'], 2)} ({bound}) — {'ok' if g['passed'] else '**ÉCHEC / FAILED**'}")
    lines += ["", "## Clés du site / site quality keys", "", "```json",
              json.dumps(q, ensure_ascii=False, indent=2), "```", "",
              "Rejouer / replay: docs/PROTOCOLE.md, section 10.", ""]
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # La version est dans le nom : un résultat 1.1 n'écrase jamais protocol-2026-10-26 (1.0) / version in the name.
    stem = spec.RESULTS_STEM.format(date=report["campaign"]["date"])
    json_path, md_path = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(to_markdown(report), encoding="utf-8", newline="\n")
    return json_path, md_path
