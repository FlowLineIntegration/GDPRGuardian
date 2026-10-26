"""Robustesse : aucune entrée ne fait échouer les détecteurs ; zones bornées / robustness on arbitrary input."""

from __future__ import annotations

import time
import unicodedata

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gdprguardian import Anonymizer
from gdprguardian._text import fold, normalize
from gdprguardian.engine import DetectionContext
from gdprguardian.heuristics._compose import ComposedView
from gdprguardian.heuristics.fr_names import FrenchNameDetector
from gdprguardian.types import Span

_ANONYMIZER = Anonymizer(countries="FR")


def _context(text: str) -> DetectionContext:
    norm, _ = normalize(text)
    folded = fold(norm)
    return DetectionContext(norm, folded, _ANONYMIZER._keywords.scan(folded), ("FR",), "fr", _ANONYMIZER.settings)


# Texte décomposé construit explicitement (lisible dans le source) / decomposed text built explicitly.
ACUTE = chr(0x301)
NFD_NAME = unicodedata.normalize("NFD", "Zélie")

# Morceaux piégeux : civilités, particules, ponctuation, codes postaux, formes juridiques, tableaux, Unicode.
# Tricky pieces: honorifics, particles, punctuation, postcodes, legal forms, tables, Unicode.
PIECES = st.sampled_from([
    "M.", "Mme", "Dr", "de", "d'", "Le", "La", "van", "Jean", "Dupont", "DUPONT", "Rose", "Pierre", "Blanc",
    "Saint-", "-", "'", "’", ",", ".", ":", "|", "---", "\n", "\n\n", " ", "  ", "\t", "75002", "Paris", "rue",
    "12", "bis", "BP", "Cedex", "SAS", "S.p.A.", "Acme", "&", "Fils", "@", "jean.dupont@ex.fr", "<", "(", ")",
    "Bonjour", "Cordialement", "Nom", "é", "Œ", "ß", "İ", " ", "​", "Ⅻ", "😀", "日本", "XIV", "Ier",
    # Fins de ligne Windows, texte décomposé (NFD), diacritique isolé / CRLF, decomposed text, lone mark.
    "\r\n", NFD_NAME, unicodedata.normalize("NFD", "Lefèvre"), ACUTE, "e" + ACUTE * 2, "Nom : ", "dupont", "Merci,",
])
TEXTS = st.lists(st.one_of(PIECES, st.text(max_size=8)), max_size=40).map("".join)


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(TEXTS)
def test_detectors_never_fail_and_spans_are_bounded(text):
    analysis = _ANONYMIZER.analyze(text)
    for span in analysis.spans:
        assert 0 <= span.start < span.end <= len(text)
    result = _ANONYMIZER.anonymize(text)
    assert isinstance(result.text, str)


@settings(max_examples=150, deadline=None)
@given(st.lists(TEXTS, min_size=1, max_size=6))
def test_segments_are_never_crossed(cells):
    per_cell, _ = _ANONYMIZER.analyze_segments(cells)
    for spans, cell in zip(per_cell, cells, strict=True):
        for span in spans:
            assert 0 <= span.start < span.end <= len(cell)


@settings(max_examples=100, deadline=None)
@given(TEXTS)
def test_detection_is_deterministic(text):
    first = [(s.start, s.end, s.entity, s.value) for s in _ANONYMIZER.analyze(text).spans]
    second = [(s.start, s.end, s.entity, s.value) for s in _ANONYMIZER.analyze(text).spans]
    assert first == second


def test_pathological_inputs_stay_fast():
    samples = ["A" * 50_000, "Jean " * 10_000, "M. " * 10_000, "12 rue " * 5_000, "75002 " * 5_000,
               "| a |" * 5_000, "de " * 10_000, "Dupont-" * 5_000, "S.A. " * 5_000, "Nom : " * 10_000,
               "e" + ACUTE * 20_000, ("e" + ACUTE) * 20_000, "Anne-\n" * 10_000]
    for text in samples:
        start = time.perf_counter()
        _ANONYMIZER.analyze(text)
        assert time.perf_counter() - start < 5.0, text[:20]


@pytest.mark.parametrize("text", [
    " " * 50_000 + "x\n|---|---|",       # espaces en tête de ligne / leading spaces
    "|---|---" + " " * 50_000 + "x",     # espaces en fin de séparateur / trailing spaces
    "| a | b |\n" + "|" + " :---- |" * 2_000 + "x",
], ids=["leading-spaces", "trailing-spaces", "many-cells"])
def test_table_separator_scan_is_linear(text):
    # Deux `[ \t]*` voisins rendaient la recherche quadratique : 30 s pour 50 Ko / was quadratic: 30 s for 50 KB.
    start = time.perf_counter()
    FrenchNameDetector(None).detect(_context(text))
    assert time.perf_counter() - start < 0.5


def test_composed_view_maps_spans_back_with_their_marks():
    name = "Zélie Lefèvre"
    text = unicodedata.normalize("NFD", f"Mme {name}, CEDEX")
    view = ComposedView(_context(text))
    assert view.text == f"Mme {name}, CEDEX"
    start = view.text.index(name)
    span = view.to_source(Span(start, start + len(name), "PERSON", "PERSON", "t", forms=("Lefèvre",)))
    assert text[span.start:span.end] == unicodedata.normalize("NFD", name)
    assert set(span.forms) == {"Lefèvre", unicodedata.normalize("NFD", "Lefèvre")}
