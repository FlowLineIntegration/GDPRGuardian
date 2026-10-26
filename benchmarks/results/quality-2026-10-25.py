"""Assemble site/data/quality.json from today's raw outputs (2026-10-25).

Usage : python benchmarks/results/quality-2026-10-25.py site/data/quality.json
(copie du script execute le 2026-10-25, completee ensuite : cle docs_leak_direct_pct, et cles du protocole public
reprises du fichier existant, « — » tant qu'aucune campagne n'a eu lieu ; elles ne s'ecrivent qu'avec
tools/protocol/merge_quality.py. Amended afterwards: docs_leak_direct_pct, and the public protocol keys kept from the
existing file, "—" until a campaign has run; only tools/protocol/merge_quality.py writes them.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
TEXTUAL = {"PERSON", "ADDRESS", "LOCATION", "ORG"}
PENDING = "—"
# Cles du protocole public (docs/PROTOCOLE.md) : jamais calculees ici / public protocol keys, never computed here.
PROTOCOL_KEYS = ("confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct", "protocol_docs",
                 "protocol_families", "real_corpora", "real_docs", "protocol_date", "protocol_engine")


def load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def pct(value: float) -> float:
    return float(f"{100 * value:.1f}")


def eval_numbers(report: dict) -> dict:
    base = report["profiles"]["standard"]["base"]
    head = base["headline"]
    structured = {k: v for k, v in base["system_labels"].items() if k not in TEXTUAL}
    chars = sum(v["chars"] for v in structured.values())
    ok = sum(v["chars"] * v["precision"] for v in structured.values())
    return {
        "docs": report["meta"]["base_docs"],
        "mentions": sum(v["mentions"] for v in base["labels"].values()),
        "decoys": sum(v["n"] for v in base["decoys"].values()),
        "redteam_docs": report["meta"]["mutated_docs"],
        "redteam_operators": len(report["meta"]["mutations"]),
        "errors_base": base["errors"]["count"],
        "errors_mutated": report["profiles"]["standard"]["mutated"]["errors"]["count"],
        "recall_structured": head["recall_structured"],
        "recall_direct": head["recall_direct"],
        "precision_all": head["precision"],
        "precision_structured": ok / chars,
        "structured_masked_chars": chars,
        "doc_leak_structured": head["doc_leak_rate_structured"],
        "doc_leak_strict": head["doc_leak_rate"],
        "over_masking": head["over_masking"],
        "decoys_masked": head["decoy_false_mask_rate"],
        "f2": head["f2"],
        "ci95": base["ci95"],
        "countries": report["meta"]["countries"],
        "wall_seconds": report["meta"]["wall_seconds"],
    }


def main() -> int:
    out = Path(sys.argv[1])
    ev = eval_numbers(load("eval-2026-10-25-standard.json"))
    engine = load("engine-2026-10-25.json")
    bench = load("bench-2026-10-25-standard.json")
    corpus = load("corpus_fr_standard-2026-10-25.json")
    extra_eval = RESULTS / "eval-2026-10-25-standard-fr.json"
    fr = eval_numbers(load(extra_eval.name)) if extra_eval.exists() else None

    bench_docs = sum(row["docs"] for row in bench["profiles"]["standard"]["kinds"].values() if "docs" in row)
    # tools/corpus/evaluate.py : 1 000 documents + 300 variantes par perturbation / 300 variants per mutation.
    corpus_docs = corpus["documents"] + len(corpus["mutations"]) * min(corpus["documents"], 300)
    runs = {
        "eval_standard_auto": ev["docs"] + ev["redteam_docs"],
        "engine_bench_1000": engine["corpus"]["docs"],
        "tools_bench_per_document": bench_docs,
        "corpus_planted_values": corpus_docs,
    }
    if fr is not None:
        runs["eval_standard_fr"] = fr["docs"] + fr["redteam_docs"]
    docs_tested = sum(runs.values())

    native = engine["native_fr"]
    assert engine["parity"]["identical_text"] == engine["parity"]["identical_spans"] == engine["parity"]["docs"]
    quality = {
        "tests_windows": 3751,
        "tests_linux": 3701,
        "tests_offline_image": 12,
        "parity_docs": engine["parity"]["docs"],
        "eval_docs": ev["docs"],
        "eval_mentions": ev["mentions"],
        "eval_decoys": ev["decoys"],
        "redteam_docs": ev["redteam_docs"],
        "redteam_operators": ev["redteam_operators"],
        "docs_tested": docs_tested,
        "recall_structured_pct": pct(ev["recall_structured"]),
        "precision_structured_pct": pct(ev["precision_structured"]),
        "recall_direct_pct": pct(ev["recall_direct"]),
        "docs_leak_structured_pct": pct(ev["doc_leak_structured"]),
        "docs_leak_direct_pct": pct(ev["doc_leak_strict"]),
        "overmask_pct": pct(ev["over_masking"]),
        "ms_per_doc": float(f"{native['ms_per_doc_median']:.2f}"),
        "mb_per_s": float(f"{native['mb_per_s_median']:.1f}"),
        "text_10mb_s": float(f"{engine['text_10mb']['median_s']:.1f}"),
        "service_p50_ms": 5.2,
        "service_p99_ms": 8.6,
        "pdf100_s": 8.7,
        "image_mb": 103,
        "core_mb": 3.6,
        "measured_on": "2026-10-25",
    }
    # Cles du protocole : valeurs deja reportees par merge_quality.py gardees, sinon « — » (mesure en cours).
    # Protocol keys: values already merged by merge_quality.py are kept, otherwise "—" (measurement pending).
    previous = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    for key in PROTOCOL_KEYS:
        quality[key] = previous.get(key, PENDING)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(quality, ensure_ascii=False, indent=2))
    print("runs", runs)
    print("eval auto", {k: v for k, v in ev.items() if k != "ci95"})
    print("ci95", ev["ci95"])
    if fr is not None:
        print("eval FR", {k: v for k, v in fr.items() if k != "ci95"})
    print("engine native", {k: v for k, v in native.items()})
    print("engine python", engine["python_fr"])
    print("engine all", engine["native_all"])
    print("10MB", engine["text_10mb"])
    print("corpus", {k: corpus[k] for k in ("documents", "errors", "throughput_mb_s", "latency_ms", "native")})
    print("corpus values", corpus["values"])
    print("corpus names", corpus["names"], "decoys", corpus["decoys"], "policy", corpus["policy_company_ids"])
    print("corpus consistency", corpus["consistency"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
