"""Évalue Gardien RGPD sur les jeux publics convertis par fetch_public.py (outil de dev).

Evaluates GDPR Guardian on the public datasets converted by fetch_public.py (dev tooling).

Per dataset and per label family:
- gold spans, "masked" rate: a gold span is masked when the detected (personal) spans cover >= 80 % of its characters;
- exact-string leak: the gold span text still appears anywhere in the anonymised output;
- over-masking: detected characters outside any gold span, as a share of non-gold characters;
- throughput, and exceptions (counted, never raised).

DATE, LOCATION, ORG and OTHER are reported apart: GDPR Guardian masks direct identifiers and keeps generic dates,
cities and organisations by policy, so a low masked rate there is not a defect.

Usage: python tools/corpus/evaluate_public.py [--datasets fr_pii_bench ...] [--countries FR|all] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from gdprguardian import Anonymizer
from gdprguardian.packs import available_packs

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "datasets" / "public" / "cache"
RESULTS = ROOT / "benchmarks" / "results"
COVERAGE_THRESHOLD = 0.8
# Familles non attendues par politique / families not expected to be masked by policy.
POLICY_KEPT = ("DATE", "LOCATION", "ORG", "OTHER")
ORDER = ("PERSON", "ADDRESS", "EMAIL", "PHONE", "NATIONAL_ID", "TAX_ID", "IBAN", "BANK_ACCOUNT", "CARD",
         "BIRTH_DATE", "ID", "URL", "IP", *POLICY_KEPT)


def load_records(name: str, limit: int | None) -> list[dict[str, Any]]:
    path = CACHE / f"{name}.jsonl"
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                records.append(json.loads(line))
            if limit and len(records) >= limit:
                break
    return records


def rate(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def new_family() -> dict[str, int]:
    return {"gold": 0, "masked": 0, "leaked": 0}


def evaluate_dataset(name: str, anonymizer: Anonymizer, records: list[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, dict[str, int]] = defaultdict(new_family)
    misses: dict[str, list[str]] = defaultdict(list)
    errors: dict[str, int] = defaultdict(int)
    error_samples: list[str] = []
    chars = non_gold_chars = over_chars = false_masks = detected_total = evaluated = 0
    seconds = 0.0
    for rec in records:
        text = rec["text"]
        t0 = time.perf_counter()
        try:
            result = anonymizer.anonymize(text)
        except Exception as exc:  # errors are counted, not raised
            errors[type(exc).__name__] += 1
            if len(error_samples) < 5:
                error_samples.append(f"{rec['id']}: {type(exc).__name__}: {exc}")
            continue
        seconds += time.perf_counter() - t0
        evaluated += 1
        detected = [s for s in result.analysis.spans if s.personal]
        mask = bytearray(len(text))
        for s in detected:
            mask[s.start:s.end] = b"\x01" * (s.end - s.start)
        gold_mask = bytearray(len(text))
        for g in rec["spans"]:
            gold_mask[g["start"]:g["end"]] = b"\x01" * (g["end"] - g["start"])
        output = result.text
        for g in rec["spans"]:
            fam = families[g["label"]]
            fam["gold"] += 1
            length = g["end"] - g["start"]
            if mask[g["start"]:g["end"]].count(1) / length >= COVERAGE_THRESHOLD:
                fam["masked"] += 1
            elif len(misses[g["label"]]) < 8:
                misses[g["label"]].append(g["text"][:80])
            if g["text"].strip() and g["text"] in output:
                fam["leaked"] += 1
        chars += len(text)
        gold_count = gold_mask.count(1)
        non_gold_chars += len(text) - gold_count
        over_chars += sum(1 for m, gm in zip(mask, gold_mask, strict=True) if m and not gm)
        detected_total += len(detected)
        false_masks += sum(1 for s in detected if not gold_mask[s.start:s.end].count(1))
    per_family = {}
    for label in sorted(families, key=lambda x: (ORDER.index(x) if x in ORDER else 99, x)):
        f = families[label]
        per_family[label] = {
            **f, "masked_rate": rate(f["masked"], f["gold"]), "leak_rate": rate(f["leaked"], f["gold"]),
            "expected_masked_by_policy": label not in POLICY_KEPT, "missed_examples": misses[label],
        }
    scored = [f for k, f in families.items() if k not in POLICY_KEPT]
    gold_scored = sum(f["gold"] for f in scored)
    return {
        "dataset": name,
        "records": len(records),
        "evaluated": evaluated,
        "errors": dict(errors),
        "error_samples": error_samples,
        "chars": chars,
        "seconds": round(seconds, 3),
        "chars_per_second": round(chars / seconds) if seconds else None,
        "docs_per_second": round(evaluated / seconds, 2) if seconds else None,
        "over_masking": {"detected_spans": detected_total, "false_mask_spans": false_masks,
                         "chars_outside_gold": over_chars, "non_gold_chars": non_gold_chars,
                         "char_rate": rate(over_chars, non_gold_chars)},
        "direct_identifiers": {"gold": gold_scored, "masked": sum(f["masked"] for f in scored),
                               "leaked": sum(f["leaked"] for f in scored),
                               "masked_rate": rate(sum(f["masked"] for f in scored), gold_scored),
                               "leak_rate": rate(sum(f["leaked"] for f in scored), gold_scored)},
        "families": per_family,
    }


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def to_markdown(res: dict[str, Any], meta: dict[str, Any]) -> str:
    di = res["direct_identifiers"]
    om = res["over_masking"]
    lines = [
        f"# GDPR Guardian on public dataset `{res['dataset']}` (countries={meta['countries']})",
        "",
        f"- Records: {res['evaluated']}/{res['records']} evaluated, errors: {res['errors'] or 0}",
        f"- Throughput: {res['chars_per_second']} chars/s, {res['docs_per_second']} docs/s "
        f"({res['chars']} chars in {res['seconds']} s, single thread)",
        f"- Direct identifiers (policy-scored families): {di['gold']} gold, masked {pct(di['masked_rate'])}, "
        f"exact-string leak {pct(di['leak_rate'])}",
        f"- Over-masking: {om['chars_outside_gold']} detected chars outside gold / {om['non_gold_chars']} non-gold "
        f"= {pct(om['char_rate'])}; {om['false_mask_spans']} of {om['detected_spans']} detected spans "
        "touch no gold span",
        f"- Masked = detected spans cover >= {int(COVERAGE_THRESHOLD * 100)}% of the gold span characters. "
        "Leak = gold span text still present anywhere in the output (also true for repeated short strings).",
        f"- Source revision: {meta['revision']}",
        "",
        "## Direct identifiers (expected to be masked)",
        "",
        "| family | gold | masked | masked rate | exact leaks | leak rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    kept_lines = []
    for label, f in res["families"].items():
        row = (f"| {label} | {f['gold']} | {f['masked']} | {pct(f['masked_rate'])} | {f['leaked']} | "
               f"{pct(f['leak_rate'])} |")
        (lines if f["expected_masked_by_policy"] else kept_lines).append(row)
    lines += ["", "## Not expected to be masked by policy (generic dates, places, organisations, other)", "",
              "| family | gold | masked | masked rate | exact leaks | leak rate |", "|---|---:|---:|---:|---:|---:|",
              *kept_lines, "", "## Missed examples (masked < 80%)", ""]
    for label, f in res["families"].items():
        if f["missed_examples"] and f["expected_masked_by_policy"]:
            shown = "; ".join(f"`{m}`".replace("\n", " ") for m in f["missed_examples"][:6])
            lines.append(f"- {label}: {shown}")
    if res["error_samples"]:
        lines += ["", "## Errors", ""] + [f"- {e}" for e in res["error_samples"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", nargs="*", help="dataset names (default: every jsonl in the cache)")
    parser.add_argument("--countries", default="FR", help='"FR" (default), a comma list, or "all"')
    parser.add_argument("--limit", type=int, default=None, help="max records per dataset")
    parser.add_argument("--out", type=Path, default=RESULTS)
    args = parser.parse_args()

    names = args.datasets or sorted(p.stem for p in CACHE.glob("*.jsonl"))
    if not names:
        print("No dataset in cache: run tools/corpus/fetch_public.py first", file=sys.stderr)
        return 2
    if args.countries.lower() == "all":
        countries: str | tuple[str, ...] = tuple(p for p in available_packs() if p != "INTL")
    else:
        countries = args.countries
    anonymizer = Anonymizer(countries=countries)
    meta_path = CACHE / "meta.json"
    sources = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    args.out.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.countries.upper() == "FR" else f"_{args.countries.lower().replace(',', '-')}"
    for name in names:
        records = load_records(name, args.limit)
        res = evaluate_dataset(name, anonymizer, records)
        meta = {"countries": args.countries, "revision": sources.get(name, {}).get("file", name)}
        # Revision complète lue depuis fetch_public / full pinned revision from fetch_public
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from fetch_public import SOURCES
            meta["revision"] = f"{SOURCES[name].repo}@{SOURCES[name].revision} ({SOURCES[name].licence})"
        except Exception:
            pass
        res["meta"] = meta
        stem = args.out / f"public_{name}{suffix}"
        stem.with_suffix(".json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        stem.with_suffix(".md").write_text(to_markdown(res, meta), encoding="utf-8", newline="\n")
        di = res["direct_identifiers"]
        print(f"{name}: {res['evaluated']} docs, direct masked {pct(di['masked_rate'])}, leak {pct(di['leak_rate'])}, "
              f"over-masking {pct(res['over_masking']['char_rate'])}, {res['chars_per_second']} chars/s, "
              f"errors {sum(res['errors'].values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
