"""Exécution de l'évaluation : positions d'origine, survie, rapports robustes et reproductibles.

Evaluation runner: original offsets, survival plumbing, robust and reproducible reports.
"""

from __future__ import annotations

import json
from random import Random

import pytest
from tools.eval import ids
from tools.eval.evaluate import _code, environment, main, markdown, masked_spans, run, summarize
from tools.eval.generate import generate_corpus
from tools.eval.mutate import mutate_corpus, select

from gdprguardian import Anonymizer


class _Exploding:
    """Moteur factice qui plante / fake engine that crashes."""

    def anonymize(self, text: str) -> None:
        raise RuntimeError("boom")


@pytest.fixture(scope="module")
def anonymizer() -> Anonymizer:
    return Anonymizer()


def test_masked_spans_are_in_original_offsets(anonymizer):
    # Un invisible dans la valeur décale le texte normalisé : les zones doivent revenir au texte d'origine.
    # An invisible char shifts the normalised text: zones must map back to the original text.
    spaced = ids.fmt_nir(ids.nir(Random(7), "2", 1985, 5, "75056"), "spaced")
    value = spaced[:7] + "\u200b" + spaced[7:]
    text = f"Bonjour,\u200b\u200b votre NIR est {value}."
    spans, output = masked_spans(anonymizer, text)
    assert [text[s.start:s.end] for s in spans if s.label == "NIR"] == [value]
    assert spaced[-6:] not in output


def test_survival_uses_the_flags_of_the_base_document(anonymizer):
    base = generate_corpus(6, seed=5)
    base_run = run(anonymizer, base)
    mutated_run = run(anonymizer, list(mutate_corpus(base, select("nbsp"), seed=0)), baselines=base_run.masked)
    tally = mutated_run.tally
    assert sum(tally.mutation_baseline.values()) > 0
    assert sum(tally.mutation_survived.values()) <= sum(tally.mutation_baseline.values())


def test_markdown_survives_a_run_where_every_document_crashes():
    # Le rapport est le plus utile justement quand tout plante / the report matters most when all crashes.
    summary = summarize(run(_Exploding(), generate_corpus(3, seed=1)), resamples=0, seed=0, samples=1)
    report = {"profiles": {"standard": {"base": summary}},
              "meta": {"env": environment(), "seed": 1, "base_docs": 3, "base_chars": 0, "mutated_docs": 0,
                       "mutations": [], "packs": [], "detectors": []}}
    text = markdown(report)
    assert "3 document(s)" in text and "RuntimeError" in text
    assert summary["docs"] == 0 and summary["headline"]["recall"] is None


def test_code_cell_escapes_control_characters_and_pipes():
    assert _code("a|b") == "`a\\|b`"
    assert _code("x\ny") == "`x\\ny`"
    assert _code("a`b") == "`a'b`"
    assert len(_code("9" * 200)) == 62


def test_main_writes_lf_reports(tmp_path, capsys):
    argv = ["--docs", "9", "--mutation-docs", "3", "--mutations", "nbsp,upper", "--profiles", "standard",
            "--bootstrap", "10", "--samples", "1", "--out", str(tmp_path), "--name", "t"]
    assert main(argv) == 0
    for suffix in ("json", "md"):
        assert b"\r\n" not in (tmp_path / f"t.{suffix}").read_bytes()  # LF partout / LF everywhere
    report = json.loads((tmp_path / "t.json").read_text(encoding="utf-8"))
    assert report["meta"]["base_docs"] == 9 and report["meta"]["mutated_docs"] > 0
    assert "standard" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["--docs", "0"], ["--bootstrap", "-1"], ["--samples", "x"],
                                  ["--profiles", "turbo"]])
def test_main_rejects_bad_arguments(argv):
    with pytest.raises(SystemExit):
        main(argv)
