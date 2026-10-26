"""Évaluation de fumée : identifiants à clé masqués à ≥ 99 % et aucun document qui fuit, en < 10 s.

Smoke evaluation: checksum-validated identifiers (NIR, IBAN, RIB, SIRET in sole-trader context, cards,
e-mails) are masked with recall >= 0.99 and no document leaks them, in under 10 seconds.
"""

from __future__ import annotations

from time import perf_counter

import pytest
from tools.eval.evaluate import evaluate, markdown, run
from tools.eval.generate import generate_corpus
from tools.eval.mutate import mutate_corpus, select
from tools.eval.schema import CHECKSUM_LABELS
from tools.eval.templates import KINDS

from gdprguardian import Anonymizer

MIN_SUPPORT = 8
# Obfuscations que le moteur neutralise par construction (normalisation) / defeated by normalisation.
NORMALISED = "nbsp,narrow_nbsp,thin_space,zero_width_space,word_joiner,soft_hyphen,bidi_mark,tag_chars,fullwidth"


@pytest.fixture(scope="module")
def corpus():
    return generate_corpus(20 * len(KINDS), seed=2026)


def test_engine_never_raises_on_ordinary_documents(corpus):
    # Un plantage n'est pas une fuite (rien n'est produit) mais rend le service indisponible.
    # A crash is not a leak (nothing is output) but makes the service unavailable.
    errors = run(Anonymizer(), corpus).errors
    assert not errors, f"{len(errors)} document(s) font planter le moteur / crash the engine: " \
                       f"{sorted(set(errors.values()))}, ex. {sorted(errors)[:3]}"


def test_checksum_identifiers_recall_and_no_leak(corpus):
    started = perf_counter()
    tally = run(Anonymizer(), corpus).tally
    for label in sorted(CHECKSUM_LABELS):
        mentions = tally.mentions[label]
        assert mentions >= MIN_SUPPORT, f"{label}: support insuffisant / not enough support ({mentions})"
        recall = tally.mentions_masked[label] / mentions
        assert recall >= 0.99, f"{label}: rappel / recall {recall:.3f}"
        assert tally.docs_leak_label[label] == 0, f"{label}: {tally.docs_leak_label[label]} document(s) leak"
    assert perf_counter() - started < 10


def test_normalised_obfuscations_do_not_leak_checksum_identifiers(corpus):
    mutated = list(mutate_corpus(corpus[:3 * len(KINDS)], select(NORMALISED), seed=1))
    tally = run(Anonymizer(), mutated).tally
    for label in sorted(CHECKSUM_LABELS):
        assert tally.docs_leak_label[label] == 0, f"{label}: fuite après obfuscation / leak after obfuscation"


class _Exploding:
    """Moteur factice qui plante / fake engine that crashes."""

    def anonymize(self, text: str) -> None:
        raise RuntimeError("boom")


def test_engine_exceptions_are_reported_not_fatal(corpus):
    result = run(_Exploding(), corpus[:3])
    assert result.errors == {doc.doc_id: "RuntimeError" for doc in corpus[:3]}
    assert result.tally.docs == 0 and result.stats == []


def test_full_pipeline_writes_a_report():
    report = evaluate(docs=18, mutation_docs=9, seed=3, profiles=("standard",), mutation_names="nbsp,at_brackets",
                      resamples=20, samples=1)
    text = markdown(report)
    assert "## Indicateurs principaux" in text and "nbsp" in text
    base = report["profiles"]["standard"]["base"]
    assert base["docs"] + base["errors"]["count"] == 18  # les plantages sont comptés à part / crashes apart
    assert 0.0 <= base["headline"]["precision"] <= 1.0
    assert {d["id"] for d in report["meta"]["detectors"]} >= {"EMAIL", "INTL_IBAN"}
