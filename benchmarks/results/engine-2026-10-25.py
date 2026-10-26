"""Banc moteur sur le corpus de 1 000 documents / engine bench on the 1,000-document corpus (2026-10-25).

- Rust core (default Anonymizer: countries FR, profile standard, native) : passes completes sur les 1 000
  documents, temps total par passe (perf_counter), mediane et minimum des passes ; latence par document.
- Parite : sorties du moteur natif et du moteur Python seul (native=False) comparees sur les 1 000 documents
  (texte de sortie et zones).
- Moteur Python seul : memes passes, pour comparaison.
- Texte de 10 Mo (10 000 000 octets UTF-8, documents du corpus concatenes) : 3 essais.
- Supplement : countries="all".

Usage : python benchmarks/results/engine-2026-10-25.py benchmarks/results/engine-2026-10-25.json
(copie du script execute le 2026-10-25 ; seule la ligne ROOT differe : chemin absolu du poste -> relatif au fichier.
Copy of the script run on 2026-10-25; only the ROOT line differs: absolute path -> relative to this file.)
"""

from __future__ import annotations

import gc
import json
import os
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from time import perf_counter, perf_counter_ns

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from gdprguardian import Anonymizer  # noqa: E402

CORPUS = ROOT / "datasets" / "fr" / "docs"


def quantile(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))]


def passes(anonymizer, docs, count):
    """Temps total de chaque passe complete sur les documents / total time of each full pass."""
    for text in docs:  # prechauffage / warm-up (non chronometre)
        anonymizer.anonymize(text)
    times = []
    for _ in range(count):
        start = perf_counter()
        for text in docs:
            anonymizer.anonymize(text)
        times.append(perf_counter() - start)
    return times


def latencies(anonymizer, docs):
    values = []
    for text in docs:
        start = perf_counter_ns()
        anonymizer.anonymize(text)
        values.append((perf_counter_ns() - start) / 1e6)
    return {"p50_ms": quantile(values, 0.5), "p95_ms": quantile(values, 0.95), "p99_ms": quantile(values, 0.99),
            "max_ms": max(values)}


def summary(times, docs, nbytes, nchars):
    median, best = statistics.median(times), min(times)
    return {
        "passes": len(times), "pass_seconds": [round(t, 4) for t in times],
        "ms_per_doc_median": 1000 * median / docs, "ms_per_doc_best": 1000 * best / docs,
        "mb_per_s_median": nbytes / median / 1e6, "mb_per_s_best": nbytes / best / 1e6,
        "mchars_per_s_median": nchars / median / 1e6,
    }


def key(result):
    return (result.text, [(s.start, s.end, s.entity, s.label) for s in result.analysis.spans if s.personal])


def main() -> int:
    out = Path(sys.argv[1])
    paths = sorted(CORPUS.glob("*.md"))
    docs = [p.read_text(encoding="utf-8") for p in paths]
    nbytes = sum(len(t.encode("utf-8")) for t in docs)
    nchars = sum(len(t) for t in docs)
    report = {
        "env": {"date_utc": datetime.now(UTC).isoformat(timespec="seconds"), "python": sys.version.split()[0],
                "platform": platform.platform(), "processor": platform.processor(), "cpu_count": os.cpu_count(),
                "gdprguardian": metadata.version("gdprguardian"), "gc_enabled": gc.isenabled(),
                "one_core": "appels sequentiels dans un seul processus / sequential calls, one process"},
        "corpus": {"path": "datasets/fr/docs/*.md", "docs": len(docs), "utf8_bytes": nbytes, "chars": nchars,
                   "mean_doc_bytes": nbytes / len(docs)},
    }
    started = perf_counter()

    native = Anonymizer()
    python = Anonymizer(native=False)
    assert native.settings.countries == ("FR",) and native.settings.profile == "standard"
    probe = native.anonymize(docs[0]).report
    report["native_flag"] = probe.get("native")
    report["python_flag"] = python.anonymize(docs[0]).report.get("native")

    # Parite / parity
    same_text = same_spans = 0
    mismatches = []
    for path, text in zip(paths, docs, strict=True):
        a, b = key(native.anonymize(text)), key(python.anonymize(text))
        same_text += a[0] == b[0]
        same_spans += a[1] == b[1]
        if a != b and len(mismatches) < 10:
            mismatches.append(path.name)
    report["parity"] = {"docs": len(docs), "identical_text": same_text, "identical_spans": same_spans,
                        "mismatch_examples": mismatches}
    print("parity", report["parity"], flush=True)

    # Rust : 9 passes / 9 passes
    report["native_fr"] = summary(passes(native, docs, 9), len(docs), nbytes, nchars)
    report["native_fr"]["latency"] = latencies(native, docs)
    print("native FR", {k: v for k, v in report["native_fr"].items() if k != "pass_seconds"}, flush=True)

    # Python seul / Python only
    report["python_fr"] = summary(passes(python, docs, 3), len(docs), nbytes, nchars)
    print("python FR", {k: v for k, v in report["python_fr"].items() if k != "pass_seconds"}, flush=True)

    # Tous pays / all countries
    all_countries = Anonymizer(countries="all")
    report["native_all"] = summary(passes(all_countries, docs, 5), len(docs), nbytes, nchars)
    print("native all", {k: v for k, v in report["native_all"].items() if k != "pass_seconds"}, flush=True)

    # Texte de 10 Mo / 10 MB text
    parts, size = [], 0
    while size < 10_000_000:
        for text in docs:
            parts.append(text)
            size += len(text.encode("utf-8")) + 2
            if size >= 10_000_000:
                break
    big = "\n\n".join(parts)
    while len(big.encode("utf-8")) > 10_000_000:
        big = big[:-1]
    runs = []
    for _ in range(3):
        start = perf_counter()
        result = native.anonymize(big)
        runs.append(perf_counter() - start)
    report["text_10mb"] = {"utf8_bytes": len(big.encode("utf-8")), "chars": len(big),
                           "seconds": [round(r, 3) for r in runs], "best_s": min(runs),
                           "median_s": statistics.median(runs), "native": result.report.get("native"),
                           "personal_spans": sum(1 for s in result.analysis.spans if s.personal)}
    print("10 MB", report["text_10mb"], flush=True)

    report["wall_seconds"] = round(perf_counter() - started, 1)
    report["documents_processed_distinct"] = {
        "corpus_1000": len(docs), "note": "memes 1 000 documents dans chaque mesure ; passes repetees non comptees"}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("->", out, report["wall_seconds"], "s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
