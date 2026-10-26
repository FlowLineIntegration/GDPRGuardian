"""Tests des outils communs des corpus réels (données inventées) / tests of the shared real-corpus helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.corpus.real_common import (
    ROOT,
    TextBuilder,
    bio_spans,
    canon,
    check_outside_repo,
    detokenize,
    find_all,
    merge_zones,
    record,
    resolve_spans,
    trim_person,
)


def test_find_all_respects_word_boundaries() -> None:
    text = "DUPONT et DUPONTEL, puis dupont et DUPONT."
    assert find_all(text, "DUPONT") == [(0, 6), (35, 41)]
    assert find_all(text, "DUPONT", ignore_case=True) == [(0, 6), (25, 31), (35, 41)]
    assert find_all(text, "  ") == []


def test_text_builder_tracks_values_and_ignored_zones() -> None:
    tb = TextBuilder()
    tb.line("Nom : ", "MARTIN", "PERSON")
    tb.line("Commentaires : ", "texte libre", ignore=True)
    tb.line("Vide : ", "   ", "PERSON")
    text = tb.text
    assert text == "Nom : MARTIN\nCommentaires : texte libre\n"
    (start, end, label, origin), = tb.spans
    assert text[start:end] == "MARTIN" and label == "PERSON" and origin == "field"
    (zs, ze), = tb.ignore
    assert text[zs:ze] == "texte libre"


def test_resolve_spans_prefers_personal_then_longer_and_trims() -> None:
    text = "Mme Jeanne MARTIN habite 3 rue Haute."
    raw = [
        (0, 17, "PERSON", "field"),     # « Mme » retirée / honorific removed
        (11, 17, "ORG", "field"),       # chevauche une zone personnelle / overlaps a personal span
        (25, 36, "ADDRESS", "field"),
        (25, 36, "ADDRESS", "repeat"),  # doublon / duplicate
        (40, 50, "PERSON", "field"),    # hors bornes / out of bounds
    ]
    spans = resolve_spans(text, raw)
    assert [(s["text"], s["label"]) for s in spans] == [("Jeanne MARTIN", "PERSON"), ("3 rue Haute", "ADDRESS")]


@pytest.mark.parametrize(("value", "kept"), [
    ("M. Jean Dupont", "Jean Dupont"), ("Mme DURAND", "DURAND"), ("Mr Smith", "Smith"), ("Dr. Who", "Who"),
    ("Monsieur", "Monsieur"), ("Maître Paul Martin", "Paul Martin"), ("Jean Dupont", "Jean Dupont"),
])
def test_trim_person_keeps_at_least_one_word(value: str, kept: str) -> None:
    assert value[trim_person(value, 0, len(value)):] == kept
    # au milieu d'un texte, pas seulement au début / inside a text, not only at its start
    text = "représenté par " + value + ", avocat"
    start = len("représenté par ")
    assert text[trim_person(text, start, start + len(value)):start + len(value)] == kept


def test_bio_spans_accepts_io_and_bio_schemes() -> None:
    assert bio_spans(["B-PER", "I-PER", "O", "B-LOC", "B-LOC", "I-ORG"]) == [
        (0, 2, "PER"), (3, 4, "LOC"), (4, 5, "LOC"), (5, 6, "ORG")]
    assert bio_spans(["I-PER", "I-PER", "O", "I-LOC"]) == [(0, 2, "PER"), (3, 4, "LOC")]
    assert bio_spans(["O", "O"]) == []


def test_detokenize_offsets_match_tokens() -> None:
    tokens = ["M", ".", "de", "Testeville", ",", "l'", "avocat", "(", "Paris", ")"]
    text, offsets = detokenize(tokens)
    assert text == "M. de Testeville, l'avocat (Paris)"
    assert all(text[s:e] == tok for tok, (s, e) in zip(tokens, offsets, strict=True))
    text2, offsets2 = detokenize(["l", "'", "impôt", "est"], [True, True, False, False])
    assert text2 == "l'impôt est"
    assert [text2[s:e] for s, e in offsets2] == ["l", "'", "impôt", "est"]


def test_record_merges_ignore_zones_and_keeps_metadata() -> None:
    rec = record("x:1", "src", "fr", "abc def ghi", [(4, 7, "PERSON", "field")], [(0, 3), (2, 5), (8, 11)],
                 {"family": "test"})
    assert rec["ignore"] == [[0, 5], [8, 11]]
    assert rec["spans"] == [{"start": 4, "end": 7, "label": "PERSON", "text": "def", "origin": "field"}]
    assert merge_zones([(5, 5)]) == []


def test_canon_normalises_for_literal_leaks() -> None:
    assert canon("ＤＵＰＯＮＴ​  Jean") == "dupont jean"


def test_cache_inside_repository_is_refused(tmp_path: Path) -> None:
    assert check_outside_repo(tmp_path) == tmp_path.resolve()
    with pytest.raises(SystemExit):
        check_outside_repo(ROOT / "datasets" / "real")
