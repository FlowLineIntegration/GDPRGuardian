"""Banc de performance : mesure, entrées adverses, sous-processus et rapport, sans lancer le banc complet.

Benchmark: measurement, adversarial inputs, subprocesses and report, without running the full bench.
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest
from tools.bench import bench

from gdprguardian import Anonymizer


@pytest.mark.parametrize("name", sorted(bench.ADVERSARIAL))
def test_adversarial_inputs_have_the_requested_size(name):
    build = bench.ADVERSARIAL[name]
    for size in (0, 1, 997, 5_000):
        assert len(build(size)) == size + (5 if name == "email_like" else 0)
    assert build(5_000) == build(5_000)


def test_quantile_is_nearest_rank():
    values = [5.0, 1.0, 3.0, 2.0, 4.0]
    assert [bench._quantile(values, q) for q in (0.0, 0.5, 1.0)] == [1.0, 3.0, 5.0]
    assert bench._quantile([7.0], 0.95) == 7.0


def test_measure_calibrates_the_loop():
    calls: list[int] = []
    stats = bench.measure(lambda: calls.append(1), samples=3, min_sample_s=0.002, warmup=1)
    assert stats["loops"] > 1 and stats["samples"] == 3
    assert 0 < stats["min_s"] <= stats["median_s"] <= stats["p95_s"]
    assert len(calls) >= 1 + 3 * stats["loops"]


def test_build_text_has_the_exact_size():
    assert len(bench.build_text(["abc", "de"], 1_000)) == 1_000
    assert bench.build_text(["abc"], 5) == "abc\n\n"  # dernier séparateur non compté / last separator not counted
    assert bench.build_text(["abc"], 3) == "abc"
    with pytest.raises(ValueError):
        bench.build_text(["", ""], 10)


def test_pii_free_text_has_the_exact_size():
    text = bench.pii_free_text(3_000, seed=1)
    assert len(text) == 3_000 and text == bench.pii_free_text(3_000, seed=1)


_FAILURES: list[tuple[Any, str]] = [
    (subprocess.TimeoutExpired("python", 1), "timeout"),
    (subprocess.CompletedProcess([], 1, "", "Traceback\nValueError: boom"), "ValueError: boom"),
    (subprocess.CompletedProcess([], 0, "pas du JSON", ""), "illisible"),
    (subprocess.CompletedProcess([], 0, "[1, 2]", ""), "inattendue"),
]


@pytest.mark.parametrize(("outcome", "expected"), _FAILURES, ids=["timeout", "crash", "garbage", "not-a-dict"])
def test_subprocess_failures_become_results(monkeypatch, outcome, expected):
    # Le banc doit survivre pour signaler (y compris un démarrage à froid qui ne répond plus).
    # The bench must survive to report (including a cold start that hangs).
    def fake(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(bench, "_python", fake)
    assert expected in bench._child("adversarial", "dashes", timeout=1)["error"]
    assert expected in bench.cold_start("standard", runs=2)["error"]


def test_cold_start_reports_medians(monkeypatch):
    runs = iter(['{"import_s": 1, "init_s": 4, "first_call_s": 0.1, "total_s": 5.1}',
                 '{"import_s": 3, "init_s": 2, "first_call_s": 0.3, "total_s": 5.3}',
                 '{"import_s": 2, "init_s": 3, "first_call_s": 0.2, "total_s": 5.2}'])
    monkeypatch.setattr(bench, "_python", lambda args, timeout: subprocess.CompletedProcess([], 0, next(runs), ""))
    assert bench.cold_start("standard", runs=3) == {"import_s": 2, "init_s": 3, "first_call_s": 0.2,
                                                   "total_s": 5.2, "runs": 3}


def test_adversarial_child_runs_in_a_fresh_process():
    result = bench._child("adversarial", "dashes", timeout=120)
    assert "error" not in result, result
    assert result["chars"] == bench.ADVERSARIAL_SIZE and result["seconds"] > 0


def test_adversarial_verdicts():
    assert bench._adversarial_row("x", {"seconds": 2.0, "chars_per_second": 5e4, "growth_exponent": 1.9})[-1] \
        == "LENT, SUPER-LINÉAIRE"
    assert bench._adversarial_row("x", {"seconds": 0.1, "chars_per_second": 2e6, "growth_exponent": 1.0})[-1] == "ok"
    assert bench._adversarial_row("x", {"error": "timeout > 60 s"})[-1].startswith("ÉCHEC")


def test_regex_costs_use_the_engine_prefilter():
    anonymizer = Anonymizer()
    rows = bench.regex_costs("Bonjour, aucune donnée ici.", anonymizer, top=100_000)
    states = {(row["pack"], row["id"]): row["prefilter"] for row in rows}
    digit_only = [(p.id, r.id) for p in anonymizer.packs for r in p.recognizers if r.prefilter == "digit"]
    assert digit_only and all(states[key] == "sauté" for key in digit_only)
    assert {row["prefilter"] for row in rows} <= {"aucun", "satisfait", "sauté"}
    assert [row["ms"] for row in rows] == sorted((row["ms"] for row in rows), reverse=True)


def test_markdown_renders_failures():
    error = {"error": "timeout > 60 s"}
    report = {
        "env": {"date_utc": "2026-10-24T00:00:00+00:00", "python": "3.12.11 (x)", "platform": "test",
                "processor": "cpu", "cpu_count": 1, "gdprguardian": None, "gc_enabled": True},
        "countries": "auto", "packs": ["INTL 1", "FR 1"], "kind_chars": {"email": 500.0},
        "input_chars": {"mixed_1k": 1_000},
        "profiles": {"standard": {"kinds": {"email": error}, "sizes": {"mixed_1k": error}, "stages_ms": error,
                                  "regex_costs_100k": [], "cold_start": error, "memory": error}},
        "adversarial": {"street_storm": error},
    }
    text = bench.markdown(report)
    assert "Pays : auto" in text and "ÉCHEC : timeout > 60 s" in text and "erreur : timeout" in text


@pytest.mark.parametrize("child", [["nope", "x"], ["adversarial", "unknown_input"], ["memory", "turbo"]])
def test_child_arguments_are_validated(child):
    with pytest.raises(SystemExit):
        bench.main(["--child", *child])
