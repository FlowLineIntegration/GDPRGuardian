"""Compare deux séries de résultats réels (avant / après), par corpus et par moitié (outil de dev).

Compares two series of real-corpus result files (before / after), per corpus and per split (dev, test, unseen,
variants). Reads the JSON files written by evaluate_real.py and writes SCORES ONLY: a Markdown table and a JSON
file. Each run is identified by its tag stem: real-<corpus>-<split>-<label>-<date>.json.

Usage:
    python tools/corpus/compare_real.py --results AFTER_DIR --before-results BEFORE_DIR --before base \
        --after rules2 --date 2026-10-25 --out benchmarks/results --name real-rules2-comparison
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FAMILIES = ("PERSON", "ADDRESS", "EMAIL", "PHONE", "ID")
_STEM = re.compile(r"real-(?P<corpus>[a-z0-9-]+?)-(?P<split>dev|test|unseen-[0-9-]+|with-fr)-(?P<label>[a-z0-9]+)-"
                   r"(?P<date>\d{4}-\d{2}-\d{2})\.json")


def load(results: Path, label: str, date: str) -> dict[tuple[str, str], dict[str, Any]]:
    """(corpus, moitié) -> résultat / (corpus, split) -> result."""
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(results.glob(f"real-*-{label}-{date}.json")):
        m = _STEM.fullmatch(path.name)
        if m is None or m.group("label") != label:
            continue
        out[(m.group("corpus"), m.group("split"))] = json.loads(path.read_text(encoding="utf-8"))
    return out


def row(result: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    totals = result["totals"]
    kept = result.get("kept_families", {})
    return {
        "documents": result["evaluated"],
        "mentions": totals["m_total"],
        "mention_recall": m["mention_recall"],
        "precision": m["precision"],
        "doc_leak_rate": m["doc_leak_rate"],
        "doc_literal_leak_rate": m["doc_literal_leak_rate"],
        "detections_per_10k_chars": m["detections_per_10k_chars"],
        "families": {f: m.get(f"recall_{f}") for f in FAMILIES if m.get(f"recall_{f}") is not None},
        "org_id_touched": kept.get("ORG_ID", {}).get("touched_rate"),
        "location_touched": kept.get("LOCATION", {}).get("touched_rate"),
        "intervals_95": {k: v for k, v in result.get("intervals_95", {}).items()
                         if k in ("mention_recall", "precision", "doc_leak_rate")},
        "chars_per_second": result.get("chars_per_second"),
        "errors": sum(result.get("errors", {}).values()),
    }


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, required=True, help="folder holding the 'after' series (and the "
                        "'before' one unless --before-results is given)")
    parser.add_argument("--before-results", type=Path, default=None, help="folder holding the 'before' series")
    parser.add_argument("--before", default="base")
    parser.add_argument("--after", default="rules2")
    parser.add_argument("--date", default="2026-10-25")
    parser.add_argument("--before-date", default=None, help="date of the 'before' series (default: --date)")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks" / "results")
    parser.add_argument("--name", default="real-rules2-comparison")
    args = parser.parse_args()
    before = load(args.before_results or args.results, args.before, args.before_date or args.date)
    after = load(args.results, args.after, args.date)
    keys = sorted(set(before) & set(after), key=lambda k: (k[1] != "dev", k[1] != "test", k[1], k[0]))
    table = []
    lines = [f"# Real corpora: {args.before} -> {args.after} ({args.date})", "",
             "Strict mention recall, character precision on the scored zone, documents leaking a personal mention. "
             "Scores only; no text. Dev halves were used to design the rules; test halves and unseen sets were not "
             "looked at.", "",
             "| corpus | split | docs | recall before | recall after | precision before | precision after | "
             "doc leak before | doc leak after | per family (after) |", "|---|---|---:|---|---|---|---|---|---|---|"]
    for corpus, split in keys:
        b, a = row(before[(corpus, split)]), row(after[(corpus, split)])
        table.append({"corpus": corpus, "split": split, "before": b, "after": a})
        families = ", ".join(f"{f} {pct(b['families'].get(f))}→{pct(v)}" for f, v in a["families"].items())
        lines.append(f"| {corpus} | {split} | {a['documents']} | {pct(b['mention_recall'])} | "
                     f"{pct(a['mention_recall'])} | {pct(b['precision'])} | {pct(a['precision'])} | "
                     f"{pct(b['doc_leak_rate'])} | {pct(a['doc_leak_rate'])} | {families} |")
    lines += ["", "Split rule: SHA-256('gdprguardian-rules2-2026-10-25|' + document id), first 32 bits even -> dev, "
              "odd -> test (tools/corpus/real_common.split_of).", ""]
    args.out.mkdir(parents=True, exist_ok=True)
    for suffix in (".json", ".md"):
        target = args.out / f"{args.name}-{args.date}{suffix}"
        if target.exists():
            raise SystemExit(f"{target.name} exists: never overwritten")
    (args.out / f"{args.name}-{args.date}.json").write_text(
        json.dumps({"before": args.before, "after": args.after, "date": args.date, "rows": table}, indent=2,
                   ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (args.out / f"{args.name}-{args.date}.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
