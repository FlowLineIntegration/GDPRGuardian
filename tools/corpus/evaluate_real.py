"""Évalue Gardien RGPD sur les corpus réels (outil de dev) / evaluates GDPR Guardian on the real corpora.

Reads the JSONL built by build_bodacc.py, build_boamp.py and fetch_real.py in the cache folder (outside the
repository) and writes SCORES ONLY (no text, no example value) to benchmarks/results/:
real-<corpus>-<date>.{md,json} and real-summary-<date>.json.

Metrics, on alphanumeric characters only (spaces and punctuation are ignored, as in docs/EVALUATION.md):
- mention recall: a gold mention counts when NONE of its alphanumeric characters stays visible (strict), and
  "recall@80" when the masked spans cover at least 80% of them (the threshold of evaluate_public.py);
- character recall over personal gold characters;
- precision: masked characters that fall inside personal gold, over all masked characters of the scored zone;
- over-masking: masked characters outside any gold span (personal or kept) over all such characters;
- document leak rate (documents holding personal gold): strict (one alphanumeric character of a personal
  mention left visible) and literal (the mention's text, NFKC/casefold, 3+ alphanumeric characters, still
  present as a word in the output);
- kept families (ORG, ORG_ID, LOCATION, DATE, OTHER): share of mentions touched by a mask, for information.
Scored zone = the document minus its "ignore" zones (unannotated free text). Precision and over-masking are
reported as "not measurable" when the corpus gold is incomplete (real_registry.Corpus.gold_complete).
95% intervals: bootstrap over DOCUMENTS (1,000 resamples, seed 0, tools.eval.metrics.bootstrap).

Negative control (no gold, e.g. Judilibre): detections per 10,000 characters, documents with a detection,
detected labels; the manual review of a sample (spotcheck_real.py --detections) is attached when present.

Usage:
    python tools/corpus/evaluate_real.py --cache DIR [--corpora bodacc_fr boamp_fr ...] [--countries XX]
                                        [--tag NAME] [--date 2026-10-25] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import time
from collections import Counter
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.corpus.real_common import (  # noqa: E402
    KEPT,
    PERSONAL,
    RESULTS,
    SPLIT_SEED,
    SPLITS,
    alnum_mask,
    canon,
    check_outside_repo,
    corpus_path,
    default_cache,
    read_jsonl,
    read_manifest,
    split_of,
)
from tools.corpus.real_registry import CORPORA  # noqa: E402
from tools.eval.metrics import bootstrap  # noqa: E402

COVERAGE = 0.8
LITERAL_MIN_ALNUM = 3
BASE_FIELDS = ("m_total", "m_full", "m_cov80", "m_literal_checked", "m_literal", "c_gold", "c_gold_masked", "c_pred",
               "c_pred_tp", "c_neutral", "c_neutral_masked", "d_has_gold", "d_leak", "d_leak_literal", "k_total",
               "k_touched", "chars", "detections", "d_detection")


def mention_status(text: str, start: int, end: int, masked: bytearray, alnum: bytearray) -> tuple[int, int]:
    """(caractères alphanumériques, dont masqués) d'une zone / (alnum chars, masked alnum chars) of a span."""
    total = hit = 0
    for i in range(start, end):
        if alnum[i]:
            total += 1
            hit += masked[i]
    return total, hit


def literal_leak(value: str, output_canon: str) -> bool:
    needle = canon(value)
    if not needle:
        return False
    return re.search(rf"(?<![^\W_]){re.escape(needle)}(?![^\W_])", output_canon) is not None


def doc_stats(rec: dict[str, Any], detected: Sequence[tuple[int, int]], output: str,
              families: Sequence[str]) -> dict[str, int]:
    """Statistiques entières d'un document (pures, testées) / integer statistics of one document (pure, tested).

    `detected`: (start, end) of the engine's personal spans in the ORIGINAL text; `output`: anonymised text.
    """
    text = rec["text"]
    n = len(text)
    masked = bytearray(n)
    for start, end in detected:
        masked[max(0, start):min(n, end)] = b"\x01" * (min(n, end) - max(0, start))
    alnum = alnum_mask(text)
    scored = bytearray(b"\x01") * n
    for start, end in rec.get("ignore", []):
        scored[start:end] = b"\x00" * (end - start)
    personal_gold = bytearray(n)
    any_gold = bytearray(n)
    st = dict.fromkeys(BASE_FIELDS, 0)
    for fam in families:
        st[f"g_{fam}"] = 0
        st[f"f_{fam}"] = 0
    out_canon = canon(output)
    leak = leak_literal = False
    for g in rec["spans"]:
        s, e, label = g["start"], g["end"], g["label"]
        any_gold[s:e] = b"\x01" * (e - s)
        total, hit = mention_status(text, s, e, masked, alnum)
        if total == 0:
            continue
        if label in PERSONAL:
            personal_gold[s:e] = b"\x01" * (e - s)
            full = hit == total
            st["m_total"] += 1
            st["m_full"] += full
            st["m_cov80"] += hit / total >= COVERAGE
            if total >= LITERAL_MIN_ALNUM:
                st["m_literal_checked"] += 1
                lit = literal_leak(g["text"], out_canon)
                st["m_literal"] += lit
                leak_literal |= lit
            leak |= not full
            if label in families:
                st[f"g_{label}"] += 1
                st[f"f_{label}"] += full
        else:
            st["k_total"] += 1
            st["k_touched"] += hit > 0
    for i in range(n):
        if not alnum[i]:
            continue
        if personal_gold[i]:
            st["c_gold"] += 1
            st["c_gold_masked"] += masked[i]
        if not scored[i]:
            continue
        if masked[i]:
            st["c_pred"] += 1
            st["c_pred_tp"] += personal_gold[i]
        if not any_gold[i]:
            st["c_neutral"] += 1
            st["c_neutral_masked"] += masked[i]
    st["d_has_gold"] = int(st["m_total"] > 0)
    st["d_leak"] = int(leak)
    st["d_leak_literal"] = int(leak_literal)
    st["chars"] = n
    st["detections"] = len(detected)
    st["d_detection"] = int(bool(detected))
    return st


def ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def headline(totals: dict[str, float], docs: int, families: Sequence[str]) -> dict[str, float | None]:
    out = {
        "mention_recall": ratio(totals["m_full"], totals["m_total"]),
        "mention_recall_at80": ratio(totals["m_cov80"], totals["m_total"]),
        "char_recall": ratio(totals["c_gold_masked"], totals["c_gold"]),
        "precision": ratio(totals["c_pred_tp"], totals["c_pred"]),
        "over_masking": ratio(totals["c_neutral_masked"], totals["c_neutral"]),
        "doc_leak_rate": ratio(totals["d_leak"], totals["d_has_gold"]),
        "doc_literal_leak_rate": ratio(totals["d_leak_literal"], totals["d_has_gold"]),
        "mention_literal_leak_rate": ratio(totals["m_literal"], totals["m_literal_checked"]),
        "kept_touched_rate": ratio(totals["k_touched"], totals["k_total"]),
        "detections_per_10k_chars": ratio(10000 * totals["detections"], totals["chars"]),
        "docs_with_detection": ratio(totals["d_detection"], docs),
    }
    for fam in families:
        out[f"recall_{fam}"] = ratio(totals[f"f_{fam}"], totals[f"g_{fam}"])
    return out


def evaluate(name: str, records: list[dict[str, Any]], countries: str, profile: str,
             resamples: int) -> dict[str, Any]:
    from gdprguardian import Anonymizer
    anonymizer = Anonymizer(countries=countries, profile=profile)
    families = sorted({g["label"] for r in records for g in r["spans"] if g["label"] in PERSONAL},
                      key=PERSONAL.index)
    keys = list(BASE_FIELDS) + [f"{p}_{f}" for f in families for p in ("g", "f")]
    vectors: list[list[int]] = []
    errors: Counter[str] = Counter()
    detected_labels: Counter[str] = Counter()
    kept_by_family: dict[str, list[int]] = {}
    seconds = 0.0
    origins: dict[str, list[int]] = {}
    for rec in records:
        t0 = time.perf_counter()
        try:
            result = anonymizer.anonymize(rec["text"])
        except Exception as exc:  # compté, jamais levé / counted, never raised
            errors[type(exc).__name__] += 1
            continue
        seconds += time.perf_counter() - t0
        spans = [s for s in result.analysis.spans if s.personal]
        detected_labels.update(s.label for s in spans)
        st = doc_stats(rec, [(s.start, s.end) for s in spans], result.text, families)
        vectors.append([st[k] for k in keys])
        # par famille conservée et par origine du gold / per kept family and per gold origin
        masked = bytearray(len(rec["text"]))
        for s in spans:
            masked[s.start:s.end] = b"\x01" * (s.end - s.start)
        alnum = alnum_mask(rec["text"])
        for g in rec["spans"]:
            total, hit = mention_status(rec["text"], g["start"], g["end"], masked, alnum)
            if not total:
                continue
            if g["label"] in KEPT:
                kept = kept_by_family.setdefault(g["label"], [0, 0])
                kept[0] += 1
                kept[1] += hit > 0
            elif g.get("origin"):
                org = origins.setdefault(f"{g['label']}:{g['origin']}", [0, 0])
                org[0] += 1
                org[1] += hit == total
    docs = len(vectors)
    sums = [sum(col) for col in zip(*vectors, strict=True)] if vectors else [0] * len(keys)
    totals = dict(zip(keys, sums, strict=True))
    point = headline(totals, docs, families)

    def metric(sums: Sequence[float], count: int) -> dict[str, float | None]:
        return headline(dict(zip(keys, sums, strict=True)), count, families)

    intervals = bootstrap(vectors, metric, resamples=resamples, seed=0) if vectors and resamples else {}
    meta = CORPORA[name]
    if not meta.gold_complete:
        for key in ("precision", "over_masking"):
            point[key] = None
            intervals.pop(key, None)
    return {
        "documents": len(records), "evaluated": docs, "errors": dict(errors), "chars": totals["chars"],
        "seconds": round(seconds, 3), "chars_per_second": round(totals["chars"] / seconds) if seconds else None,
        "families": families, "totals": totals, "metrics": point,
        "intervals_95": {k: [round(v[0], 4), round(v[1], 4)] for k, v in intervals.items()
                         if v[0] is not None and v[1] is not None},
        "kept_families": {k: {"mentions": v[0], "touched": v[1], "touched_rate": ratio(v[1], v[0])}
                          for k, v in sorted(kept_by_family.items())},
        "by_origin": {k: {"mentions": v[0], "masked": v[1], "recall": ratio(v[1], v[0])}
                      for k, v in sorted(origins.items())},
        "detected_labels": dict(detected_labels.most_common()),
    }


def engine_info() -> dict[str, Any]:
    import gdprguardian
    from gdprguardian import _native
    return {"package": "gdprguardian", "version": getattr(gdprguardian, "__version__", "?"),
            "native_core": _native.available(), "python": platform.python_version(),
            "platform": f"{platform.system()} {platform.release()}", "machine": platform.machine()}


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def ci(res: dict[str, Any], key: str, percent: bool = True) -> str:
    value = res["metrics"].get(key)
    interval = res["intervals_95"].get(key)
    if value is None:
        return "n/a"
    fmt = pct if percent else (lambda x: f"{x:.2f}")
    return f"{fmt(value)} [{fmt(interval[0])}–{fmt(interval[1])}]" if interval else fmt(value)


def to_markdown(name: str, res: dict[str, Any], run: dict[str, Any], build: dict[str, Any] | None = None) -> str:
    meta = CORPORA[name]
    t = res["totals"]
    window = (build or {}).get("window")
    lines = [
        f"# GDPR Guardian on real corpus `{name}` ({run['date']})",
        "",
        f"- Corpus: {meta.title}. Language `{meta.language}`. Licence: {meta.licence}. Source: {meta.url} "
        f"({meta.revision}).",
    ]
    if window:
        # Le manifeste du cache fait foi (ensemble inédit d'une autre période) / the cache manifest is authoritative.
        lines.append(f"- This build: publications {window[0]}..{window[-1]} (cache manifest).")
    if run.get("split", "all") != "all":
        lines.append(f"- Split: {run['split']} half only; {run['split_rule']}.")
    lines += [
        f"- Real text: {meta.real_text}.",
        f"- Gold: {meta.gold}.",
        f"- Engine: gdprguardian {run['engine']['version']} (native core: {run['engine']['native_core']}), "
        f"`Anonymizer(countries=\"{run['countries']}\", profile=\"{run['profile']}\")`.",
        f"- Documents: {res['evaluated']}/{res['documents']} evaluated, engine errors: {res['errors'] or 0}; "
        f"{t['chars']:,} characters; throughput {res['chars_per_second']} chars/s (one thread, shared machine).",
        f"- Personal gold mentions: {t['m_total']:,}; kept-by-policy mentions: {t['k_total']:,}.",
        "",
    ]
    if meta.negative_control:
        lines += [
            "## Negative control (no gold)", "",
            "| indicator | value [95% CI] |", "|---|---|",
            f"| masked spans per 10,000 characters | {ci(res, 'detections_per_10k_chars', percent=False)} |",
            f"| documents with at least one masked span | {ci(res, 'docs_with_detection')} |",
            f"| masked spans | {t['detections']:,} |",
            "", "Masked labels: " + ", ".join(f"{k} {v}" for k, v in res["detected_labels"].items()), "",
        ]
    else:
        lines += [
            "## Headline (95% bootstrap intervals over documents)", "",
            "| indicator | value [95% CI] |", "|---|---|",
            f"| mention recall, strict (no character left) | {ci(res, 'mention_recall')} |",
            f"| mention recall@80 (>= 80% of characters masked) | {ci(res, 'mention_recall_at80')} |",
            f"| character recall | {ci(res, 'char_recall')} |",
            f"| precision (characters, scored zone) | {ci(res, 'precision')} |",
            f"| over-masking of non-gold text | {ci(res, 'over_masking')} |",
            f"| documents leaking a personal mention (strict) | {ci(res, 'doc_leak_rate')} |",
            f"| documents leaking a mention verbatim (literal) | {ci(res, 'doc_literal_leak_rate')} |",
            f"| mentions found verbatim in the output | {ci(res, 'mention_literal_leak_rate')} |",
            "",
        ]
        if not meta.gold_complete:
            lines += ["Precision and over-masking are not measurable here: the gold does not cover every person "
                      "named in the text.", ""]
        lines += ["## Per family (strict mention recall)", "", "| family | mentions | recall [95% CI] |",
                  "|---|---:|---|"]
        for fam in res["families"]:
            lines.append(f"| {fam} | {t[f'g_{fam}']:,} | {ci(res, f'recall_{fam}')} |")
        if res["by_origin"]:
            lines += ["", "## Per gold origin", "", "| family:origin | mentions | strict recall |", "|---|---:|---:|"]
            for key, v in res["by_origin"].items():
                lines.append(f"| {key} | {v['mentions']:,} | {pct(v['recall'])} |")
        if res["kept_families"]:
            lines += ["", "## Kept by policy (share of mentions touched by a mask, for information)", "",
                      "| family | mentions | touched |", "|---|---:|---:|"]
            for key, v in res["kept_families"].items():
                lines.append(f"| {key} | {v['mentions']:,} | {pct(v['touched_rate'])} |")
    review = run.get("review")
    if review:
        lines += ["", "## Manual review of a sample", "", f"- {review.get('summary', '')}"]
        for key, value in review.items():
            if key != "summary":
                lines.append(f"- {key}: {value}")
    lines += ["", "## Reproduce", "", "```", meta.build.replace("<CACHE>", "DIR"),
              f"python tools/corpus/evaluate_real.py --cache DIR --corpora {name}"
              + (f" --countries {run['countries']}" if run["countries"] != meta.countries else "")
              + (f" --tag {run['tag']}" if run.get("tag") else ""), "```", "",
              "No document text or gold value is stored in this report; the corpus stays in the local cache.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", type=Path, default=default_cache())
    parser.add_argument("--corpora", nargs="*", help="corpus names (default: every built corpus)")
    parser.add_argument("--countries", default=None, help="override the registry countries (variant run)")
    parser.add_argument("--profile", default="standard")
    parser.add_argument("--tag", default="", help="suffix for a variant run (e.g. with-fr)")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--reviews", type=Path, default=None, help="JSON of manual review counts per corpus")
    parser.add_argument("--split", choices=("all", *SPLITS), default="all",
                        help="dev or test half by a fixed hash of the document id (real_common.split_of)")
    parser.add_argument("--summary", default=None,
                        help="summary file name (default real-summary-<date>.json; give a new name for a variant)")
    parser.add_argument("--no-overwrite", action="store_true", help="refuse to replace an existing result file")
    parser.add_argument("--out", type=Path, default=RESULTS)
    args = parser.parse_args()
    cache = check_outside_repo(args.cache)
    manifest = read_manifest(cache)
    names = args.corpora or [n for n in CORPORA if corpus_path(cache, n).exists()]
    reviews_path = args.reviews or cache / "spotcheck" / "reviews.json"
    reviews = json.loads(reviews_path.read_text(encoding="utf-8")) if reviews_path.exists() else {}
    if args.split != "all":
        reviews = {}  # la relecture porte sur le corpus entier / the manual review covers the whole corpus
    engine = engine_info()
    summary_path = args.out / (args.summary or f"real-summary-{args.date}.json")
    if args.no_overwrite and args.summary and summary_path.exists():
        raise SystemExit(f"{summary_path.name} exists (--no-overwrite)")
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {
        "date": args.date, "engine": engine, "corpora": {}}
    summary["engine"] = engine
    for name in names:
        meta = CORPORA[name]
        countries = args.countries or meta.countries
        records = list(read_jsonl(corpus_path(cache, name), args.limit))
        if args.split != "all":
            records = [r for r in records if split_of(r["id"]) == args.split]
        res = evaluate(name, records, countries, args.profile, args.resamples)
        run = {"date": args.date, "countries": countries, "profile": args.profile, "engine": engine,
               "tag": args.tag, "review": reviews.get(name), "split": args.split,
               "split_rule": None if args.split == "all" else
               f"SHA-256('{SPLIT_SEED}|' + document id): first 32 bits even -> dev, odd -> test"}
        stem = f"real-{name.replace('_', '-')}" + (f"-{args.tag}" if args.tag else "") + f"-{args.date}"
        if args.no_overwrite and ((args.out / f"{stem}.json").exists() or (args.out / f"{stem}.md").exists()):
            raise SystemExit(f"{stem} exists (--no-overwrite)")
        payload = {"corpus": name, "title": meta.title, "language": meta.language, "licence": meta.licence,
                   "source": meta.url, "revision": meta.revision, "real_text": meta.real_text, "gold": meta.gold,
                   "gold_complete": meta.gold_complete, "negative_control": meta.negative_control,
                   "measures": meta.measures, "cannot_measure": meta.cannot_measure,
                   "build": {k: v for k, v in manifest.get(name, {}).items() if k not in ("labels",)},
                   "gold_labels": manifest.get(name, {}).get("labels"), "run": run, **res}
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / f"{stem}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8", newline="\n")
        (args.out / f"{stem}.md").write_text(to_markdown(name, res, run, payload["build"]), encoding="utf-8",
                                             newline="\n")
        key = name + (f"@{args.tag}" if args.tag else "")
        summary["corpora"][key] = {
            "name": name, "variant": args.tag or None, "title": meta.title, "language": meta.language,
            "licence": meta.licence, "real_text": True, "real_text_note": meta.real_text, "gold_type": meta.gold,
            "gold_complete": meta.gold_complete, "negative_control": meta.negative_control,
            "countries": countries, "profile": args.profile, "split": args.split, "documents": res["evaluated"],
            "mentions_personal": res["totals"]["m_total"], "mentions_kept": res["totals"]["k_total"],
            "chars": res["totals"]["chars"], "metrics": res["metrics"], "intervals_95": res["intervals_95"],
            "kept_families": res["kept_families"], "review": reviews.get(name),
            "reproduce": [meta.build.replace("<CACHE>", "DIR"),
                          f"python tools/corpus/evaluate_real.py --cache DIR --corpora {name}"
                          + (f" --countries {countries}" if countries != meta.countries else "")
                          + (f" --tag {args.tag}" if args.tag else "")],
            "report": f"benchmarks/results/{stem}.md",
        }
        m = res["metrics"]
        density = m["detections_per_10k_chars"]
        print(f"{key}: {res['evaluated']} docs, recall {pct(m['mention_recall'])} "
              f"(@80 {pct(m['mention_recall_at80'])}), precision {pct(m['precision'])}, "
              f"doc leak {pct(m['doc_leak_rate'])}, literal {pct(m['doc_literal_leak_rate'])}, "
              f"det/10k {density and round(density, 2)}, errors {sum(res['errors'].values())}", flush=True)
    summary["corpora"] = dict(sorted(summary["corpora"].items()))
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                            newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
