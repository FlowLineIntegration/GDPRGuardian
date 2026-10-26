"""Banc de débit et de mémoire de Gardien RGPD / GDPR Guardian throughput and memory benchmark.

Protocole : préchauffage, échantillons d'au moins 50 ms, médiane, p95 et minimum (jamais la moyenne),
GC actif comme en production. Démarrage à froid, mémoire et entrées adverses (retour arrière
catastrophique) tournent dans des processus neufs avec délai maximal.
Protocol: warm-up, samples of at least 50 ms, median/p95/min (never the mean), GC enabled. Cold start,
memory and adversarial inputs run in fresh processes with a timeout, so a pathological regex cannot
hang the run.

Usage : python -m tools.bench.bench [--quick] [--profiles standard] [--out benchmarks/results]
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from functools import partial
from importlib import metadata
from itertools import cycle
from pathlib import Path
from time import perf_counter, perf_counter_ns
from typing import Any

if __package__ in (None, ""):  # lancé comme script / run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.eval.evaluate import int_at_least
from tools.eval.generate import DEFAULT_SEED, CorpusGenerator
from tools.eval.templates import KINDS

from gdprguardian import Anonymizer
from gdprguardian._text import fold, normalize
from gdprguardian.engine import DetectionContext

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ("fast", "standard", "strict")
SIZES = {"1k": 1_000, "10k": 10_000, "100k": 100_000, "1m": 1_000_000}
SLOW_CHARS_PER_SECOND = 100_000  # en dessous : entrée suspecte / below: suspicious input
SUPERLINEAR_EXPONENT = 1.3       # au-delà : croissance super-linéaire / above: super-linear growth
ADVERSARIAL_SIZE = 200_000
CHILD_MODES = ("adversarial", "memory")


def _repeat(unit: str) -> Callable[[int], str]:
    """Motif répété puis tronqué à n caractères / unit repeated, then cut to n characters."""
    return lambda n: (unit * (n // len(unit) + 1))[:n]


# Entrées adverses : longues séquences qui piègent les regex mal bornées et les balayages répétés
# (une recherche depuis le début de la ligne pour chaque candidat donne un coût quadratique).
# Adversarial inputs: long runs that trap poorly bounded regexes and repeated scans (searching back to
# the line start for every candidate is quadratic on a single long line).
ADVERSARIAL: dict[str, Callable[[int], str]] = {
    "digits_run": _repeat("1234567890"),
    "spaced_digits": _repeat("1 "),
    "digit_pairs": _repeat("12 "),
    "dotted_digits": _repeat("1."),
    "dashed_digits": _repeat("1-"),
    "at_signs": _repeat("@"),
    "at_words": _repeat("a@"),
    "email_like": lambda n: _repeat("a.b")(n) + "@x.fr",
    "plus_prefixes": _repeat("+33 "),
    "uppercase_run": _repeat("A"),
    "uppercase_words": _repeat("DUPONT "),
    "capitalized_words": _repeat("Jean Dupont "),
    "honorific_names": _repeat("M. Dupont "),
    "capital_lines": _repeat("Jean\n"),
    "colon_labels": _repeat("Nom : Dupont "),
    "street_storm": _repeat("12 rue de la Paix "),
    "address_lines": _repeat("Bât. B, Résidence Les Pins\n12 rue de la Paix\n75011 Paris\n"),
    "address_list": _repeat("12 rue de la Paix, 75011 Paris ; "),
    "postcode_storm": _repeat("75011 "),
    "legal_forms": _repeat("SARL Société "),
    "sole_trader_ids": _repeat("entrepreneur individuel SIRET 732 829 320 00074 "),
    "mrz_like": _repeat("<" * 44 + "\n"),
    "dashes": _repeat("-"),
    "invisible": _repeat("\u200b"),
    "whitespace_run": _repeat(" "),
    "newline_run": _repeat("\n"),
    "keyword_storm": _repeat("né le iban siret n° client "),
    "single_token": _repeat("x"),
    "hex_colons": _repeat("ab:"),
    "brackets": _repeat("[at] (dot) "),
}


# --- Mesure / measurement -----------------------------------------------------------------------------


def _quantile(values: Sequence[float], q: float) -> float:
    """Quantile par rang le plus proche (petits échantillons) / nearest-rank quantile."""
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def measure(fn: Callable[[], object], *, samples: int, min_sample_s: float = 0.05, warmup: int = 3) -> dict[str, Any]:
    """Temps par appel : boucle calibrée pour que chaque échantillon dure ≥ `min_sample_s`.

    Per-call time: the loop is calibrated so that each sample lasts at least `min_sample_s`.
    """
    for _ in range(warmup):
        fn()
    loops = 1
    while True:
        start = perf_counter_ns()
        for _ in range(loops):
            fn()
        elapsed = (perf_counter_ns() - start) / 1e9
        if elapsed >= min_sample_s or loops >= 1 << 20:
            break
        loops = max(loops * 2, int(loops * min_sample_s / max(elapsed, 1e-9) * 1.1))
    times = []
    for _ in range(samples):
        start = perf_counter_ns()
        for _ in range(loops):
            fn()
        times.append((perf_counter_ns() - start) / 1e9 / loops)
    median = statistics.median(times)
    return {"median_s": median, "p95_s": _quantile(times, 0.95), "min_s": min(times),
            "mad_s": statistics.median(abs(t - median) for t in times), "loops": loops, "samples": samples}


def per_document(anonymizer: Anonymizer, texts: Sequence[str], repeats: int) -> dict[str, Any]:
    """Latence par document (médiane de `repeats` appels) puis p50/p95 sur les documents.

    Per-document latency (median of `repeats` calls), then p50/p95 across documents.
    """
    for text in texts[:3]:
        anonymizer.anonymize(text)
    latencies = []
    for text in texts:
        runs = []
        for _ in range(repeats):
            start = perf_counter_ns()
            anonymizer.anonymize(text)
            runs.append((perf_counter_ns() - start) / 1e9)
        latencies.append(statistics.median(runs))
    chars = sum(len(t) for t in texts)
    return {"docs": len(texts), "chars": chars, "mean_doc_chars": chars / len(texts),
            "p50_ms": 1000 * _quantile(latencies, 0.5), "p95_ms": 1000 * _quantile(latencies, 0.95),
            "max_ms": 1000 * max(latencies), "chars_per_second": chars / sum(latencies)}


def _joined(pieces: Iterator[str], size: int) -> str:
    """Morceaux séparés par une ligne vide, coupés à exactement `size` caractères / exactly `size` chars."""
    parts: list[str] = []
    total = -2  # longueur de "\n\n".join(parts) / length of the joined text
    while total < size:
        piece = next(pieces)
        parts.append(piece)
        total += len(piece) + 2
    return "\n\n".join(parts)[:size]


def build_text(texts: Sequence[str], size: int) -> str:
    """Concatène des documents (en boucle) jusqu'à `size` caractères / cycles documents up to `size` chars."""
    if not any(texts):
        raise ValueError("aucun texte / no text")
    return _joined(cycle(texts), size)


def pii_free_text(size: int, seed: int) -> str:
    from faker import Faker

    fake = Faker("fr_FR")
    fake.seed_instance(seed)
    return _joined(iter(lambda: fake.paragraph(nb_sentences=8), None), size)


def pii_dense_text(generator: CorpusGenerator, size: int) -> str:
    tables = [d.text for d in generator.corpus(60, ("table",))]
    return build_text(tables, size)


# --- Sous-processus / subprocesses ----------------------------------------------------------------------

_COLD_START = """
import json, time
t0 = time.perf_counter()
import gdprguardian
t1 = time.perf_counter()
anonymizer = gdprguardian.Anonymizer(profile={profile!r})
t2 = time.perf_counter()
anonymizer.anonymize("Jean Dupont, NIR 1 85 05 78 006 084 91, jean.dupont@exemple.fr, 06 12 34 56 78.")
t3 = time.perf_counter()
print(json.dumps({{"import_s": t1 - t0, "init_s": t2 - t1, "first_call_s": t3 - t2, "total_s": t3 - t0}}))
"""


def _python(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONUTF8": "1"}
    return subprocess.run([sys.executable, "-I", *args], capture_output=True, text=True, timeout=timeout,
                          env=env, check=False)


def _run_json(args: list[str], timeout: float) -> dict[str, Any]:
    """Processus neuf qui imprime un objet JSON ; toute défaillance devient {"error": …}.

    Fresh process printing one JSON object; any failure (timeout, crash, garbage) becomes {"error": …}.
    """
    try:
        done = _python(args, timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"timeout > {timeout:.0f} s"}
    if done.returncode != 0:
        return {"error": (done.stderr.strip().splitlines() or ["?"])[-1][:200]}
    try:
        result = json.loads(done.stdout)
    except json.JSONDecodeError:
        return {"error": "sortie JSON illisible / unreadable JSON output"}
    return result if isinstance(result, dict) else {"error": "sortie JSON inattendue / unexpected JSON output"}


def cold_start(profile: str, runs: int) -> dict[str, Any]:
    """Import + construction + premier appel, processus neuf à chaque fois / fresh process each time."""
    results = []
    for _ in range(runs):
        result = _run_json(["-c", _COLD_START.format(profile=profile)], timeout=120)
        if "error" in result:
            return result
        results.append(result)
    return {key: statistics.median(r[key] for r in results) for key in results[0]} | {"runs": runs}


def _child(mode: str, argument: str, timeout: float) -> dict[str, Any]:
    return _run_json([str(Path(__file__).resolve()), "--child", mode, argument], timeout)


def _peak_rss_bytes() -> int | None:
    """Pic de mémoire résidente du processus (Windows, Linux, macOS) / process peak RSS."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

        # Signatures explicites : un HANDLE 64 bits passé comme int C serait tronqué / explicit signatures.
        current_process = ctypes.windll.kernel32.GetCurrentProcess
        current_process.restype = wintypes.HANDLE
        memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        memory_info.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        memory_info.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        if not memory_info(current_process(), ctypes.byref(counters), counters.cb):
            return None
        return int(counters.PeakWorkingSetSize)
    try:
        import resource
    except ImportError:  # pragma: no cover
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def _child_adversarial(name: str) -> dict[str, Any]:
    """Deux tailles : l'exposant de croissance révèle un coût super-linéaire / two sizes reveal the growth."""
    anonymizer = Anonymizer()
    anonymizer.anonymize("échauffement / warm-up 06 12 34 56 78")
    timings = []
    for size in (ADVERSARIAL_SIZE // 4, ADVERSARIAL_SIZE):
        text = ADVERSARIAL[name](size)
        runs = []
        for _ in range(3):  # minimum de 3 : borne basse, peu bruitée / min of 3: low-noise lower bound
            start = perf_counter()
            anonymizer.anonymize(text)
            runs.append(perf_counter() - start)
        timings.append(min(runs))
    small, large = timings
    # Temps ∝ tailleᵏ : k = log(t2/t1) / log(4) ; k ≈ 1 linéaire, k ≈ 2 quadratique / k ≈ 1 linear.
    exponent = math.log(large / small) / math.log(4) if small > 0 and large > 0 else None
    return {"chars": ADVERSARIAL_SIZE, "seconds": large, "chars_per_second": ADVERSARIAL_SIZE / large,
            "seconds_quarter": small, "growth_exponent": exponent}


def regex_costs(text: str, anonymizer: Anonymizer, top: int = 12) -> list[dict[str, Any]]:
    """Coût brut de chaque motif (balayage complet, sans validation) / raw cost of each pattern (full scan).

    Indique où concentrer l'optimisation ; le moteur saute les motifs à contexte absent.
    Shows where to optimise; the engine skips context-gated patterns when no keyword is present.
    """
    shadow, _ = normalize(text)
    # Préfiltre évalué par le code même du moteur / prefilter evaluated by the engine's own code.
    ctx = DetectionContext(shadow, fold(shadow), None, (), "fr", anonymizer.settings)
    rows = []
    for pack in anonymizer.packs:
        for recognizer in pack.recognizers:
            start = perf_counter()
            matches = sum(1 for _ in recognizer.regex.finditer(shadow))
            elapsed_ms = 1000 * (perf_counter() - start)
            prefilter = recognizer.prefilter
            state = "aucun" if not prefilter else "satisfait" if ctx.has(prefilter) else "sauté"
            rows.append({"pack": pack.id, "id": recognizer.id, "tier": recognizer.tier, "prefilter": state,
                         "ms": elapsed_ms, "matches": matches})
    rows.sort(key=lambda row: -row["ms"])
    return rows[:top]


def _child_memory(profile: str) -> dict[str, Any]:
    import tracemalloc

    generator = CorpusGenerator(DEFAULT_SEED)
    text = build_text([d.text for d in generator.corpus(180)], SIZES["1m"])
    anonymizer = Anonymizer(profile=profile)
    anonymizer.anonymize("échauffement / warm-up")
    gc.collect()
    rss_before = _peak_rss_bytes()
    start = perf_counter()
    anonymizer.anonymize(text)
    seconds = perf_counter() - start
    rss_after = _peak_rss_bytes()
    tracemalloc.start()
    anonymizer.anonymize(text)
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"input_chars": len(text), "seconds_untraced": seconds, "tracemalloc_peak_bytes": peak,
            "tracemalloc_peak_per_input_char": peak / len(text), "peak_rss_before_bytes": rss_before,
            "peak_rss_after_bytes": rss_after}


# --- Programme / program --------------------------------------------------------------------------------


def environment() -> dict[str, Any]:
    clock = time.get_clock_info("perf_counter")
    try:
        version = metadata.version("gdprguardian")
    except metadata.PackageNotFoundError:
        version = None
    return {"date_utc": datetime.now(UTC).isoformat(timespec="seconds"), "python": sys.version,
            "platform": platform.platform(), "processor": platform.processor() or platform.machine(),
            "cpu_count": os.cpu_count(), "gdprguardian": version, "gc_enabled": gc.isenabled(),
            "perf_counter_resolution_s": clock.resolution}


def benchmark(profiles: Sequence[str], *, quick: bool, docs_per_kind: int, samples: int, seed: int,
              cold: bool, memory: bool, adversarial: bool) -> dict[str, Any]:
    generator = CorpusGenerator(seed)
    by_kind = {kind: [d.text for d in generator.corpus(docs_per_kind, (kind,))] for kind in KINDS}
    mixed = [text for texts in by_kind.values() for text in texts]
    sizes = {k: v for k, v in SIZES.items() if not quick or k != "1m"}
    inputs = {f"mixed_{k}": build_text(mixed, v) for k, v in sizes.items()}
    inputs["pii_free_100k"] = pii_free_text(SIZES["100k"], seed)
    inputs["pii_dense_100k"] = pii_dense_text(generator, SIZES["100k"])
    report: dict[str, Any] = {
        "env": environment(), "seed": seed, "quick": quick, "profiles": {},
        "kind_chars": {kind: sum(map(len, texts)) / len(texts) for kind, texts in by_kind.items()},
        "input_chars": {name: len(text) for name, text in inputs.items()},
    }
    for profile in profiles:
        anonymizer = Anonymizer(profile=profile)
        report.setdefault("packs", [f"{p.id} {p.version}" for p in anonymizer.packs])
        countries = anonymizer.settings.countries
        report.setdefault("countries", countries if isinstance(countries, str) else ",".join(countries))
        entry: dict[str, Any] = {"kinds": {}, "sizes": {}}
        for kind, texts in by_kind.items():
            entry["kinds"][kind] = _guarded(partial(per_document, anonymizer, texts, 3 if quick else 5))
        for name, text in inputs.items():
            entry["sizes"][name] = _guarded(partial(_size_stats, anonymizer, text, samples))
        biggest = inputs["mixed_1m" if "mixed_1m" in inputs else "mixed_100k"]
        entry["stages_ms"] = _guarded(partial(_stages, anonymizer, biggest))
        entry["regex_costs_100k"] = regex_costs(inputs["mixed_100k"], anonymizer)
        if cold:
            entry["cold_start"] = cold_start(profile, runs=3 if quick else 5)
        if memory:
            entry["memory"] = _child("memory", profile, timeout=600)
        report["profiles"][profile] = entry
    if adversarial:
        report["adversarial"] = {name: _child("adversarial", name, timeout=60) for name in ADVERSARIAL}
    return report


def _guarded(measurement: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Une exception du moteur devient un résultat, pas un arrêt du banc / an engine exception is a result."""
    try:
        return measurement()
    except Exception as error:  # le banc doit survivre pour signaler / the bench must survive to report
        return {"error": type(error).__name__}


def _size_stats(anonymizer: Anonymizer, text: str, samples: int) -> dict[str, Any]:
    stats = measure(partial(anonymizer.anonymize, text), samples=samples)
    stats["chars_per_second"] = len(text) / stats["median_s"]
    stats["best_chars_per_second"] = len(text) / stats["min_s"]
    return stats


def _stages(anonymizer: Anonymizer, text: str) -> dict[str, float]:
    """Médiane des temps par étape rapportés par le moteur / median of the engine's per-stage timings."""
    timings = [anonymizer.anonymize(text).report["timings_ms"] for _ in range(3)]
    return {key: statistics.median(t.get(key, 0.0) for t in timings) for key in timings[0]}


def _fmt_rate(value: float | None) -> str:
    return "–" if value is None else f"{value / 1e6:.2f} M"


def _cell(row: dict[str, Any], render: Callable[[dict[str, Any]], str]) -> str:
    return f"erreur : {row['error']}" if "error" in row else render(row)


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return lines + ["| " + " | ".join(row) + " |" for row in rows]


def _cold_row(profile: str, cold: dict[str, Any]) -> list[str]:
    if not cold or "error" in cold:
        return [profile, f"erreur : {cold.get('error')}", "", "", ""]
    return [profile, *(f"{1000 * cold[k]:.1f}" for k in ("import_s", "init_s", "first_call_s", "total_s"))]


def _memory_row(profile: str, mem: dict[str, Any]) -> list[str]:
    if not mem or "error" in mem:
        return [profile, f"erreur : {mem.get('error')}", "", ""]
    before, after = mem["peak_rss_before_bytes"], mem["peak_rss_after_bytes"]
    rss = f"{before / 2**20:.0f} → {after / 2**20:.0f}" if before and after else "–"
    return [profile, f"{mem['tracemalloc_peak_bytes'] / 2**20:.1f}", f"{mem['tracemalloc_peak_per_input_char']:.0f}",
            rss]


def _adversarial_row(name: str, row: dict[str, Any]) -> list[str]:
    if "error" in row:
        return [name, "–", "–", "–", f"ÉCHEC : {row['error']}"]
    exponent = row.get("growth_exponent")
    verdicts = []
    if row["chars_per_second"] < SLOW_CHARS_PER_SECOND:
        verdicts.append("LENT")
    if exponent is not None and exponent > SUPERLINEAR_EXPONENT:
        verdicts.append("SUPER-LINÉAIRE")
    shown = "–" if exponent is None else f"{exponent:.2f}"
    return [name, f"{1000 * row['seconds']:.0f}", _fmt_rate(row["chars_per_second"]), shown,
            ", ".join(verdicts) or "ok"]


def markdown(report: dict[str, Any]) -> str:
    env = report["env"]
    runs = report["profiles"]
    profiles = list(runs)
    first = runs[profiles[0]]
    lines = ["# Banc de performance Gardien RGPD / GDPR Guardian benchmark", "",
             f"{env['date_utc']} · Python {env['python'].split()[0]} · {env['platform']} · {env['processor']} · "
             f"{env['cpu_count']} cœurs logiques · Gardien RGPD {env['gdprguardian']} · GC actif : {env['gc_enabled']}",
             f"Pays : {report.get('countries', '?')} ; packs chargés : {', '.join(report.get('packs', []))}.",
             "", "Un seul cœur (appels séquentiels). Débits en millions de caractères par seconde (M car./s).", "",
             "## Par type de document / per document kind", ""]
    lines += _table(
        ["Type", "Taille moy. (car.)", *(f"{p} p50 / p95 (ms)" for p in profiles),
         *(f"{p} M car./s" for p in profiles)],
        [[kind, f"{report['kind_chars'][kind]:.0f}",
          *(_cell(runs[p]["kinds"][kind], lambda r: f"{r['p50_ms']:.2f} / {r['p95_ms']:.2f}") for p in profiles),
          *(_cell(runs[p]["kinds"][kind], lambda r: _fmt_rate(r["chars_per_second"])) for p in profiles)]
         for kind in report["kind_chars"]])
    lines += ["", "## Par taille d'entrée / per input size", "",
              "Débit à la médiane des échantillons ; entre parenthèses, au meilleur échantillon (borne basse peu "
              "sensible à la charge de la machine).", ""]
    lines += _table(
        ["Entrée", "Caractères", *(f"{p} médiane (ms)" for p in profiles), *(f"{p} M car./s" for p in profiles)],
        [[name, f"{chars:,}",
          *(_cell(runs[p]["sizes"][name], lambda r: f"{1000 * r['median_s']:.2f}") for p in profiles),
          *(_cell(runs[p]["sizes"][name], lambda r: f"{_fmt_rate(r['chars_per_second'])} "
                                                    f"({_fmt_rate(r['best_chars_per_second'])})") for p in profiles)]
         for name, chars in report["input_chars"].items()])
    lines += ["", "## Répartition du temps (plus grosse entrée, ms) / stage breakdown", ""]
    stages = list(dict.fromkeys(stage for p in profiles for stage in runs[p]["stages_ms"] if stage != "error"))
    lines += _table(["Étape", *profiles],
                    [[stage, *(_cell(runs[p]["stages_ms"], lambda r, s=stage: f"{r.get(s, 0):.1f}")
                               for p in profiles)] for stage in stages])
    if any("cold_start" in runs[p] for p in profiles):
        lines += ["", "## Démarrage à froid (processus neuf, médiane) / cold start", ""]
        lines += _table(("Profil", "import (ms)", "construction (ms)", "premier appel (ms)", "total (ms)"),
                        [_cold_row(p, runs[p].get("cold_start", {})) for p in profiles])
    if any("memory" in runs[p] for p in profiles):
        lines += ["", "## Mémoire (entrée de 1 M car.) / memory", ""]
        lines += _table(("Profil", "pic tracemalloc (Mo)", "octets alloués / car.", "pic RSS avant → après (Mo)"),
                        [_memory_row(p, runs[p].get("memory", {})) for p in profiles])
    if any("regex_costs_100k" in runs[p] for p in profiles):
        lines += ["", f"## Motifs les plus coûteux (balayage brut, 100 k car., profil {profiles[0]}) / costliest "
                  "patterns", ""]
        lines += ["Coût d'un balayage complet ; « sauté » : le préfiltre du moteur évite ce motif sur ce texte "
                  "(les niveaux B/C sont aussi sautés sans mot de contexte).", ""]
        lines += _table(("Pack", "Motif", "Niveau", "Préfiltre", "ms", "Correspondances"),
                        [[row["pack"], row["id"], row["tier"], row.get("prefilter", "–"), f"{row['ms']:.1f}",
                          str(row["matches"])] for row in first.get("regex_costs_100k", [])])
    if "adversarial" in report:
        lines += ["", f"## Entrées adverses ({ADVERSARIAL_SIZE:,} car., profil standard) / adversarial inputs", "",
                  f"Alerte si moins de {SLOW_CHARS_PER_SECOND:,} car./s, ou si l'exposant de croissance "
                  f"(temps à {ADVERSARIAL_SIZE // 4:,} puis {ADVERSARIAL_SIZE:,} car.) dépasse "
                  f"{SUPERLINEAR_EXPONENT} (1 = linéaire, 2 = quadratique).", ""]
        lines += _table(("Entrée", "Durée (ms)", "M car./s", "Exposant", "Verdict"),
                        [_adversarial_row(name, row) for name, row in report["adversarial"].items()])
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Banc de performance Gardien RGPD / GDPR Guardian benchmark")
    parser.add_argument("--profiles", default=",".join(PROFILES))
    parser.add_argument("--quick", action="store_true", help="version courte (CI) / short run")
    parser.add_argument("--docs-per-kind", type=int_at_least(1), default=None)
    parser.add_argument("--samples", type=int_at_least(1), default=None, help="échantillons par mesure / samples")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--no-cold", action="store_true")
    parser.add_argument("--no-memory", action="store_true")
    parser.add_argument("--no-adversarial", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks" / "results")
    parser.add_argument("--name", default="bench")
    parser.add_argument("--child", nargs=2, metavar=("MODE", "ARG"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child:
        mode, argument = args.child
        if mode not in CHILD_MODES or argument not in (ADVERSARIAL if mode == "adversarial" else PROFILES):
            parser.error(f"--child {mode} {argument} : inconnu / unknown")
        result = _child_adversarial(argument) if mode == "adversarial" else _child_memory(argument)
        print(json.dumps(result))
        return 0
    profiles = tuple(p.strip() for p in args.profiles.split(",") if p.strip())
    if set(profiles) - set(PROFILES):
        parser.error(f"profils inconnus / unknown profiles: {sorted(set(profiles) - set(PROFILES))}")
    started = perf_counter()
    report = benchmark(profiles, quick=args.quick, docs_per_kind=args.docs_per_kind or (12 if args.quick else 40),
                       samples=args.samples or (5 if args.quick else 15), seed=args.seed, cold=not args.no_cold,
                       memory=not args.no_memory, adversarial=not args.no_adversarial)
    report["wall_seconds"] = round(perf_counter() - started, 1)
    args.out.mkdir(parents=True, exist_ok=True)
    json_path, md_path = args.out / f"{args.name}.json", args.out / f"{args.name}.md"
    # Fins de ligne LF sur tous les systèmes / LF line endings everywhere.
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(markdown(report), encoding="utf-8", newline="\n")
    print(f"-> {json_path}\n-> {md_path}  ({report['wall_seconds']} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
