"""Notation d'un document et agrégats / scoring one document and aggregates."""

from __future__ import annotations

from collections import Counter

from tools.corpus.evaluate_real import doc_stats
from tools.corpus.real_common import PERSONAL, record
from tools.eval.metrics import Tally
from tools.protocol import spec
from tools.protocol.align import align
from tools.protocol.outcomes import (
    Cell,
    direct_outcome,
    pack_bits,
    real_failure,
    score_real,
    unpack_bits,
)


def test_direct_outcome_strict() -> None:
    text = "Nom : Jean Martin, tél. 06 12 34 56 78."
    gold = [(6, 17, "PERSON"), (24, 38, "PHONE")]
    visible = bytearray(b"\x01") * len(text)
    visible[6:17] = b"\x00" * 11            # nom masqué / name masked
    visible[24:37] = b"\x00" * 13           # dernier chiffre visible / last digit visible
    outcome = direct_outcome(text, gold, visible)
    assert (outcome.mentions, outcome.masked, outcome.leak) == (2, 1, True)
    assert outcome.labels == (("PERSON", True), ("PHONE", False))


def test_mention_without_alphanumeric_is_not_scored() -> None:
    outcome = direct_outcome("a -- b", [(2, 4, "PERSON")], bytearray(b"\x01" * 6))
    assert outcome.mentions == 0 and not outcome.leak


def test_failure_counts_as_leak_with_nothing_masked() -> None:
    cell = Cell()
    rec = record("x1", "t", "fr", "Contact : Jean Martin.", [(10, 21, "PERSON", "field")])
    assert real_failure(cell, rec, "http_422", spec.REAL_DIRECT_LABELS) == 1
    assert cell.hist == Counter({(1, 0): 1}) and cell.errors["http_422"] == 1
    assert cell.passed == 0 and cell.mention_total == 1


def test_real_score_matches_tools_corpus() -> None:
    """Sans date de naissance, l'issue protocole = la fuite stricte de tools.corpus / same as tools.corpus."""
    text = "Nom : Jean Martin\nAdresse : 3 rue des Lilas 75011 Paris\nSociété Acme SA"
    raw = [(6, 17, "PERSON", "field"), (28, 55, "ADDRESS", "field"), (64, 71, "ORG", "field")]
    rec = record("r1", "t", "fr", text, raw)
    output = "Nom : [PERSONNE_1]\nAdresse : 3 rue des Lilas [ADRESSE_1]\nSociété Acme SA"
    cell = Cell()
    leak = score_real(cell, rec, output, align(text, output), spec.REAL_DIRECT_LABELS)
    alignment = align(text, output)
    stats = doc_stats(rec, [(s, e) for s, e, _ in alignment.masked], output, PERSONAL)
    assert leak == stats["d_leak"] == 1
    assert cell.mention_masked == stats["m_full"] == 1
    assert cell.real["c_pred"] == stats["c_pred"]
    assert len(cell.vectors) == 1


def test_cell_json_round_trip() -> None:
    cell = Cell(docs=3, chars=30, no_direct=1)
    cell.hist.update({(2, 2): 1, (3, 1): 1})
    cell.errors["alignment"] = 1
    cell.label_mentions.update({"PERSON": 4})
    cell.label_masked.update({"PERSON": 3})
    cell.tally = Tally(docs=2)
    cell.tally.mentions["PERSON"] = 4
    cell.tally.mutation_mentions[("nbsp", "PERSON")] = 2
    cell.tally.confusion[("PERSON", "ORG")] = 1
    cell.vectors.append([1, 2, 3])
    again = Cell.from_json(cell.to_json())
    assert again.to_json() == cell.to_json()
    assert again.tally is not None and again.tally.mutation_mentions[("nbsp", "PERSON")] == 2
    merged = Cell().merge(again).merge(cell)
    assert merged.docs == 6 and merged.hist[(2, 2)] == 2 and merged.tally.mentions["PERSON"] == 8


def test_bits_round_trip() -> None:
    bits = [1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1]
    assert unpack_bits(pack_bits(bits), len(bits)) == bits
