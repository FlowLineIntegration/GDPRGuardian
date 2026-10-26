"""Alignement de la sortie du service sur l'entrée / aligning the service output with its input."""

from __future__ import annotations

import pytest
from tools.eval.generate import CorpusGenerator
from tools.eval.metrics import significant_mask
from tools.eval.mutate import MUTATIONS, mutate_corpus
from tools.protocol.align import DROPPED_CLASS, AlignmentError, align, masked_bytes
from tools.protocol.align import PLACEHOLDER_RE as COPY

from gdprguardian import Anonymizer, sanitize
from gdprguardian.scope import PLACEHOLDER_RE


def test_copies_match_the_engine() -> None:
    # Copies figées dans l'outil autonome : toute dérive du moteur doit casser ce test / drift guard.
    assert COPY.pattern == PLACEHOLDER_RE.pattern
    assert sanitize._INVISIBLE_RE.pattern == DROPPED_CLASS


def _truth(text: str, anonymizer: Anonymizer) -> tuple[bytearray, str]:
    result = anonymizer.anonymize(text)
    mask = bytearray(len(text))
    for span in result.analysis.spans:
        if span.personal:
            mask[span.start:span.end] = b"\x01" * (span.end - span.start)
    return mask, result.text


@pytest.mark.parametrize("countries", [("FR",), "auto"])
def test_rebuilt_masks_equal_engine_spans(countries: object) -> None:
    """Sur du synthétique et ses mutations : zones reconstruites = zones du moteur (caractères alphanumériques)."""
    anonymizer = Anonymizer(countries=countries, profile="standard")
    base = list(CorpusGenerator(2026102599).corpus(60))
    docs = base + list(mutate_corpus(base[:3], MUTATIONS, 2026102599))
    assert len(docs) > 150
    for doc in docs:
        truth, output = _truth(doc.text, anonymizer)
        alignment = align(doc.text, output)
        rebuilt = masked_bytes(len(doc.text), alignment.masked)
        sig = significant_mask(doc.text)
        for i, significant in enumerate(sig):
            if not significant:
                continue
            assert rebuilt[i] == truth[i], doc.doc_id
            # Borne prudente : un caractère vraiment visible est toujours « peut-être visible ».
            if not truth[i]:
                assert alignment.maybe_visible[i], doc.doc_id


def test_ambiguous_segment_marks_every_possible_place() -> None:
    text = "Alpha x Beta x Gamma"
    output = "[PERSONNE_1] x [PERSONNE_2]"
    alignment = align(text, output)
    assert alignment.placeholders == 2
    assert alignment.ambiguous_segments == 1
    # Les deux « x » peuvent être le segment littéral : tous deux comptent comme peut-être visibles.
    assert alignment.maybe_visible[6] == 1 and alignment.maybe_visible[13] == 1
    # Placement représentatif : le plus à gauche / representative placement: leftmost.
    assert alignment.masked[0][:2] == (0, 5)


def test_invisible_characters_dropped_by_the_service() -> None:
    text = "Bonjour​ Jean Martin⁠, merci."
    output = "Bonjour [PERSONNE_1], merci."
    alignment = align(text, output)
    start, end, label = alignment.masked[0]
    assert label == "PERSONNE"
    assert text[start:end] == "Jean Martin"
    assert alignment.maybe_visible[text.index("merci")] == 1


def test_placeholder_already_in_the_input_stays_literal() -> None:
    text = "Voir [PERSONNE_1] et Jean Martin."
    output = "Voir [PERSONNE_1] et [PERSONNE_2]."
    alignment = align(text, output)
    assert alignment.placeholders == 1
    assert text[alignment.masked[0][0]:alignment.masked[0][1]] == "Jean Martin"


def test_adjacent_placeholders() -> None:
    text = "Ref JeanMartin fin"
    output = "Ref [PERSONNE_1][PERSONNE_2] fin"
    alignment = align(text, output)
    covered = masked_bytes(len(text), alignment.masked)
    assert covered[4:14] == b"\x01" * 10
    assert alignment.ambiguous_segments == 1


@pytest.mark.parametrize(("text", "output"), [
    ("Jean Martin", "Jean Martin modifié"),
    ("Jean Martin", "[PERSONNE_1] [PERSONNE_2] [PERSONNE_3] [PERSONNE_4] [PERSONNE_5] [PERSONNE_6]"),
    ("a b", "x [EMAIL_1]"),
    ("abc", "[image]"),
])
def test_impossible_alignment_fails_cleanly(text: str, output: str) -> None:
    with pytest.raises(AlignmentError) as caught:
        align(text, output)
    assert text not in str(caught.value)


def test_no_placeholder_means_everything_visible() -> None:
    alignment = align("rien à masquer", "rien à masquer")
    assert alignment.masked == ()
    assert all(alignment.maybe_visible)
