"""Moteur fusionné contre la référence Python : tout doit être identique.

Fused engine against the Python reference: everything must be identical. Détection puis finalisation : deux
appels Rust par document / detection then finalisation: two Rust calls per document. Zones
(champ par champ, score arrondi à 9 décimales), texte anonymisé, rapport (explications comprises), clés et ordre
des mesures, chemin des cellules (tableurs). Corpus complet sur une matrice de réglages, fuzzing Hypothesis en
Unicode adverse, détecteurs Python branchés, mode auto, replis. Spans field by field, anonymised text, report
(explanations included), timing keys and order, the cells path. Full corpus over a settings matrix, Hypothesis
fuzzing with adversarial Unicode, plugged-in Python detectors, auto mode, fallbacks.
"""

from __future__ import annotations

import gc
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from functools import cache, partial
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from gdprguardian import Anonymizer, _native
from gdprguardian._text import fold
from gdprguardian.detectors.intl import InternationalPhoneDetector
from gdprguardian.engine import DetectionContext, _FoundView, markdown_table_zones
from gdprguardian.sanitize import sanitize_output
from gdprguardian.types import Span

pytestmark = pytest.mark.skipif(not _native.provides_engine(), reason="noyau sans moteur fusionné / no fused engine")

_DOCS = sorted((Path(__file__).resolve().parents[1] / "datasets" / "fr" / "docs").glob("*.md"))
_RULES = {"name": "acme", "rules": [
    {"label": "CLIENT", "pattern": "CLT-[0-9]{4}-[0-9]{4}"},
    {"label": "REF", "pattern": "[0-9]{6}", "action": "keep", "context": ["commande"]},
    {"label": "DOSSIER", "pattern": "D[0-9]{5}", "context": ["dossier"], "window": [30, 10]}],
    "deny": {"PROJET": ["Phénix", "Opération Orion"]}, "allow": ["Jourdan Industries SA", "support@acme.fr"]}
# Matrice de réglages / settings matrix.
_VARIANTS: dict[str, dict[str, Any]] = {
    "default": {},
    "strict": {"profile": "strict"},
    "auto": {"countries": "auto"},
    "all": {"countries": "all"},
    "operators_explain": {"explain": True, "operators": {
        "PHONE": "mask", "BIRTH_DATE": "generalize", "POSTAL_CODE": "generalize", "EMAIL": "redact", "ORG": "keep",
        "ADDRESS": "redact", "IBAN": "mask", "SECRET": "keep", "NIR": "generalize", "PERSON": "replace"}},
    "english_neutral_mask": {"label_language": "en", "neutral_labels": True, "company_ids": "mask"},
    "auto_labels_keep": {"label_language": "auto", "company_ids": "keep", "facility_ids": "mask"},
    "rules": {"rules": _RULES, "explain": True},
    "entities": {"exclude_entities": frozenset({"ADDRESS", "EMAIL"}), "min_score": 0.7},
}


def _key(span: Span) -> tuple:
    return (span.start, span.end, span.entity, span.label, span.source, span.value, round(span.score, 9),
            span.priority, span.personal, span.forms, span.propagate)


def _report(report: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in report.items() if k not in ("timings_ms", "native")}


def _timing_keys(report: dict[str, Any]) -> list[str]:
    """Mêmes étapes mesurées, dans le même ordre ; « native » n'existe qu'avec Rust / "native" exists with Rust."""
    return [k for k in report["timings_ms"] if k != "native"]


class _NoStaged:
    """Interdit le chemin par étapes : le moteur fusionné doit tout faire / forbids the staged path."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, anonymizer: Anonymizer) -> None:
        def refuse(*_args: Any, **_kwargs: Any) -> Any:
            raise AssertionError("chemin par étapes inattendu / unexpected staged path")

        for name in ("_detect_text", "_detect_segments", "_fused_fallback"):
            monkeypatch.setattr(anonymizer, name, refuse)


def _pair(**options: Any) -> tuple[Anonymizer, Anonymizer]:
    fused, python = Anonymizer(**options), Anonymizer(**options, native=False)
    assert fused._fused is not None and python._fused is None
    return fused, python


def _same(fused: Anonymizer, python: Anonymizer, text: str, *, analyze: bool = True) -> None:
    left, right = fused.anonymize(text), python.anonymize(text)
    assert left.text == right.text
    assert _report(left.report) == _report(right.report)
    assert _timing_keys(left.report) == _timing_keys(right.report)
    assert [_key(s) for s in left.analysis.spans] == [_key(s) for s in right.analysis.spans]
    if analyze:
        a, b = fused.analyze(text), python.analyze(text)
        assert [_key(s) for s in a.spans] == [_key(s) for s in b.spans]
        assert (a.countries, a.country_reasons, a.language) == (b.countries, b.country_reasons, b.language)
        assert [k for k in a.timings_ms if k != "native"] == [k for k in b.timings_ms if k != "native"]


def _same_cells(fused: Anonymizer, python: Anonymizer, cells: list[str],
                forced: list[frozenset[str]] | None = None) -> None:
    left, right = fused.analyze_segments(cells, forced), python.analyze_segments(cells, forced)
    assert [[_key(s) for s in cell] for cell in left[0]] == [[_key(s) for s in cell] for cell in right[0]]
    assert [_key(s) for s in left[1].spans] == [_key(s) for s in right[1].spans]
    assert left[1].text == right[1].text
    with fused.new_scope("fr") as scope_f, python.new_scope("fr") as scope_p:
        for scope in (scope_f, scope_p):
            scope.reserve("[PERSONNE_2] [TEL_1]")
        out_f, report_f = fused.anonymize_segments(cells, scope_f, forced)
        out_p, report_p = python.anonymize_segments(cells, scope_p, forced)
    assert out_f == out_p
    assert _report(report_f) == _report(report_p)
    assert _timing_keys(report_f) == _timing_keys(report_p)


@pytest.fixture(scope="module")
def corpus() -> list[str]:
    return [path.read_text(encoding="utf-8") for path in _DOCS]


@pytest.fixture(scope="module")
def engines() -> dict[str, tuple[Anonymizer, Anonymizer]]:
    return {name: _pair(**options) for name, options in _VARIANTS.items()}


# --- Corpus -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("variant", list(_VARIANTS))
def test_corpus_identical(corpus, engines, variant, monkeypatch):
    """Les 1 000 documents, chaque réglage, sans aucun repli / the 1,000 documents, every setting, no fallback."""
    fused, python = engines[variant]
    _NoStaged(monkeypatch, fused)
    assert len(corpus) >= 1000
    for index, text in enumerate(corpus):
        # `analyze` sur un document sur trois (même code de détection) / on one document in three.
        _same(fused, python, text, analyze=index % 3 == 0)


def test_corpus_cells_identical(corpus, engines, monkeypatch):
    """Chemin des tableurs : cellules et en-têtes imposés / spreadsheet path: cells and forced headers."""
    fused, python = engines["default"]
    _NoStaged(monkeypatch, fused)
    for text in corpus[:200]:
        cells = [cell for cell in re.split(r"\n+", text) if cell]
        _same_cells(fused, python, cells, [fused.context_groups(cell[:20]) for cell in cells])
    explain, reference = engines["operators_explain"]
    for text in corpus[200:260]:
        _same_cells(explain, reference, [cell for cell in text.split("\n\n") if cell])


def test_large_text_identical(corpus, engines):
    fused, python = engines["default"]
    _same(fused, python, "\n\n".join(corpus[:60]))


# --- Unicode adverse / adversarial Unicode ------------------------------------------------------------------------

_ADVERSARIAL = [
    "é", "É", "ß", "ĸ", "ǅ", "İ", "ı", "ŉ", "ﬁ", "ͅ", "Ⓐ", "ⓐ", "²", "٣", "①", "Ⅻ", " ", " ",
    "　", "\x1c", "\x1d", "\x1e", "\x1f", "\x85", "​", "­", "﻿", "⁠", "’", "'", "-", ".",
    " ", "\n", "\r\n", "\t", "[", "]", "_", "|", "😀", "𝐀", "𐐀", "𐐨", "𞤀", "\U0001f1eb", "\U000e0041", "\U0010fffd",
    "Σ", "ς", "ʕ", "K", "Å", "<", "@", "+", "00",
]
_WORDS = [
    "Jean", "Dupont", "DUPONT", "Marie", "M.", "Mme", "Dr", "Monsieur", "J.", "Pierre", "O'Neil", "Jean-Pierre",
    "Zoé", "Ñúñez", "ÉLODIE", "Ǆemal", "𐐀𐐨𐐨", "[PERSONNE_1]", "[TEL_2]", "06 12 34 56 78", "+33 6 12 34 56 78",
    "0033 (0)6 12 34 56 78", "+41 44 668 18 00", "jean.dupont@exemple.fr", "ΣΑΣ@ΕΞΑΜΠΛΣ.fr", "75011", "97400",
    "né le 03/03/1985", "1er mai 1985", "1 85 05 78 006 084 91", "185057800608491", "SAS", "SARL", "Acme SAS",
    "Dupont SARL", "la société Martin", "Cabinet Durand & Associés", "entrepreneur individuel", "Paris",
    "12 rue de la Paix", "75002 Paris", "BP 42", "Bât. B", "domicilié", "SIREN 732 829 320",
    "IBAN FR76 3000 6000 0112 3456 7890 189", "FR7630006000011234567890189", "commande 123456", "CLT-2024-0098",
    "dossier D12345", "Phénix",
    "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\nL898902C36UTO7408122F1204159ZE184226B<<<<<10",
    "| Nom | Date de naissance |\n|---|---|\n| Jean Dupont | 03/03/1985 |", "A" * 400, "Nom : dupont",
    "\U0001f1eb\U0001f1f7 Jean Dupont",
]
_PIECES = st.sampled_from(_WORDS) | st.sampled_from(_ADVERSARIAL) | st.text(
    alphabet=st.sampled_from([c for c in [*_ADVERSARIAL, *"aZ09 :/"] if len(c) == 1]), max_size=12)
_TEXTS = st.lists(_PIECES, max_size=30)
_FUZZ = settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@_FUZZ
@given(words=_TEXTS, variant=st.sampled_from(list(_VARIANTS)), separator=st.sampled_from([" ", "\n", "", "\r\n"]))
@example(words=["élève DUPONT", " ", "Jean"], variant="default", separator=" ")
def test_random_texts_identical(engines, words, variant, separator):
    fused, python = engines[variant]
    text = separator.join(words)
    _same(fused, python, text)
    _same_cells(fused, python, text.split("["))


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(rows=st.lists(st.lists(_PIECES, min_size=2, max_size=2), max_size=5),
       header=st.sampled_from(["| Nom | Date de naissance |", "|  | N° SIRET |", "Nom \\| alias | Passeport"]),
       delimiter=st.sampled_from(["|---|---|", "|:---|:---:|", "-|-", "| --- | --- |\r"]))
def test_markdown_tables_identical(engines, rows, header, delimiter):
    """Zones de tableau Markdown (en-têtes porteurs de contexte) / Markdown table zones."""
    fused, python = engines["default"]
    body = "\n".join("| " + " | ".join(cell.replace("\n", " ") for cell in row) + " |" for row in rows)
    text = f"Avant\n{header}\n{delimiter}\n{body}\n\nAprès 03/03/1985"
    _same(fused, python, text)
    document = fused._fused.detect(text, fused._host)
    zones = [(start, end, frozenset(groups)) for start, end, groups in document.zones]
    assert zones == markdown_table_zones(document.text, fused.context_groups)


@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.sampled_from(["+", "00", "0", "33", " ", ".", "-", "(", ")", "6", "12", "a", "_", "²", "é", "\n",
                                 "+33 6 12 34 56 78", "0033612345678", "1" * 25, "Ⅻ", "٣"]), max_size=20).map("".join))
def test_phone_candidates_match_the_python_regex(text):
    search = _native.core().phone_candidates
    expected = [m.span() for m in InternationalPhoneDetector._candidate.finditer(text)]
    assert search(_native.unicode_table(), text) == expected


_SANITIZE = ["![", "]", "(", ")", "](", "http:", "https:", "//", " ", "\t", "　", "\x1c", "\n", "alt", "x",
             "<img", "<IMG", "<İmg", "<ıMG", "<Kmg", "<imgx", "<img_", "<img ", ">", "<!--", "-->",
             "--", "->", " page", "page ", "pagex", "page_", "­", "​", "‍", "﻿", "\U000e0041",
             "😀", "é", "!", "<", "a" * 199, "b" * 200, "c" * 1999, "<img" + "f" * 2000 + ">",
             "![a](//" + "g" * 2000 + ")", "<!--" + "h" * 20000 + "-->"]


@settings(max_examples=600, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.sampled_from(_SANITIZE) | st.text(max_size=4), max_size=14).map("".join))
def test_sanitize_twin_matches_python(text):
    """`sanitize_output` en Rust (moteur fusionné) contre Python : images, commentaires, casse, invisibles.

    Rust `sanitize_output` (fused engine) versus Python: images, comments, case, invisibles.
    """
    assert _native.core().sanitize_output(_native.unicode_table(), text) == sanitize_output(text)


def test_sanitize_twin_on_every_code_point():
    every = "".join(chr(cp) for cp in range(0x110000) if not 0xD800 <= cp < 0xE000)
    assert _native.core().sanitize_output(_native.unicode_table(), every) == sanitize_output(every)


# --- Détecteurs Python branchés / plugged-in Python detectors -------------------------------------------------------


class _Injector:
    """Détecteur Python rejouant une spécification, et qui lit `ctx.found` / replays a spec, reads `ctx.found`."""

    id = "INJECT"

    def __init__(self) -> None:
        self.spec: list[tuple] = []
        self.seen: list[list[tuple]] = []

    def detect(self, ctx: DetectionContext) -> list[Span]:
        # Zones déjà trouvées, à l'ordre près (Rust analyse tous les packs d'abord) ; relire un élément rend le même
        # objet. Spans found so far, up to order (Rust scans every pack first); reading an item again gives the
        # same object.
        self.seen.append(sorted((s.start, s.end, s.entity, s.source, s.value or "") for s in ctx.found))
        if len(ctx.found):
            assert ctx.found[-1] is ctx.found[len(ctx.found) - 1]
        length = len(ctx.text)
        spans = []
        for start, size, entity, label, source, score, priority, value, personal, forms, propagate in self.spec:
            start = min(start, length)
            spans.append(Span(start, min(start + size, length), entity, label, source, score, priority, value,
                              personal, forms, propagate))
        return spans


_SPAN_SPEC = st.tuples(
    st.integers(0, 120), st.integers(0, 40),
    st.sampled_from(["PERSON", "ORG", "ADDRESS", "EMAIL", "PHONE", "NATIONAL_ID", "_KEEP", "SECRET", "CUSTOM"]),
    st.sampled_from(["PERSON", "ORG", "PHONE", "NIR", "PROJET", "s"]),
    st.sampled_from(["FR_NAMES", "INTL_IBAN", "NER_x", "deny_list", "CUSTOM_1_REF", "FR_NIR", "a+b", "keep:z", "😀"]),
    st.floats(0.0, 1.0) | st.sampled_from([0.0, -0.0, 0.5, 1.0]), st.sampled_from([50, 55, 60, 70, 80, 95, 100]),
    st.none() | st.sampled_from(["", "x", "Jean Dupont", "185057800608491"]), st.booleans(),
    st.lists(st.sampled_from(["Jean", "Dupont ", "", "ab"]), max_size=3).map(tuple), st.booleans())


@pytest.fixture(scope="module")
def injected() -> tuple[Anonymizer, Anonymizer, _Injector]:
    injector = _Injector()
    fused, python = _pair(detectors=(injector,), rules=_RULES, explain=True,
                          operators={"PHONE": "mask", "ORG": "redact", "ADDRESS": "keep"})
    return fused, python, injector


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(words=_TEXTS, spec=st.lists(_SPAN_SPEC, max_size=12))
def test_python_detector_spans_identical(injected, words, spec):
    fused, python, injector = injected
    injector.spec = spec
    text = " ".join(words)
    injector.seen = []
    _same(fused, python, text, analyze=False)
    assert injector.seen[0] == injector.seen[1]  # même `ctx.found` des deux côtés / same `ctx.found` both sides
    _same_cells(fused, python, text.split("["))


def test_python_spans_outside_the_native_domain_fall_back_to_python():
    """Objet rendu deux fois, score entier, NaN : la référence Python finalise, sans redétecter.

    Object returned twice, int score, NaN: the Python reference finalises, without detecting again.
    """
    calls: list[int] = []

    class Odd:
        id = "ODD"

        def __init__(self, kind: str) -> None:
            self.kind = kind

        def detect(self, ctx: DetectionContext) -> list[Span]:
            calls.append(1)
            if len(ctx.text) < 4:
                return []
            if self.kind == "twice":
                shared = Span(0, 4, "PERSON", "PERSON", "x", 0.9, 60, propagate=True)
                return [shared, shared]
            return [Span(0, 4, "PERSON", "PERSON", "x", 1 if self.kind == "int" else float("nan"))]

    for kind in ("twice", "int", "nan"):
        fused, python = _pair(detectors=(Odd(kind),))
        calls.clear()
        _same(fused, python, "Jean Dupont, 06 12 34 56 78.")
        assert len(calls) == 4  # une détection par appel, sans reprise / one detection per call, no rerun


def test_python_contexts_are_released(injected):
    """Le contexte des détecteurs Python voit le document : il est libéré à la fin, aucun cycle ne reste.

    The Python detectors' context sees the document: it is released at the end, no cycle remains.
    """
    fused, _, injector = injected
    injector.spec = [(0, 4, "PERSON", "PERSON", "INJECT", 0.9, 60, None, True, (), True)]
    for _ in range(20):
        fused.anonymize("Jean Dupont, 06 12 34 56 78.")
        fused.analyze_segments(["Jean Dupont", "06 12 34 56 78"])
    gc.collect()
    assert not [o for o in gc.get_objects() if type(o) is _FoundView]


def test_anonymize_builds_no_span_object(corpus, monkeypatch):
    """`anonymize` ne crée aucun objet `Span` tant qu'on ne lit pas `analysis.spans` / no object until read."""
    fused = Anonymizer()
    fused.anonymize(corpus[0])
    built: list[int] = []
    original = Span.__init__

    def counting(self: Span, *args: Any, **kwargs: Any) -> None:
        built.append(1)
        original(self, *args, **kwargs)

    monkeypatch.setattr(Span, "__init__", counting)
    results = [fused.anonymize(text) for text in corpus[:50]]
    with fused.new_scope() as scope:
        fused.anonymize_segments(corpus[0].split("\n"), scope)
    assert built == []
    count = sum(len(result.analysis.spans) for result in results)
    assert len(built) == count > 100  # créés à la lecture, une fois / built when read, once
    assert sum(len(result.analysis.spans) for result in results) == count == len(built)


def test_parallel_calls_are_consistent(corpus, engines):
    fused, python = engines["default"]
    texts = corpus[:64]
    expected = [python.anonymize(text).text for text in texts]
    with ThreadPoolExecutor(8) as pool:
        assert list(pool.map(lambda text: fused.anonymize(text).text, texts)) == expected


# --- Replis vers le chemin par étapes / fallbacks to the staged path ---------------------------------------------


def test_inputs_outside_the_native_domain_take_the_staged_path():
    """Demi-codet isolé, groupes imposés incohérents : chemin par étapes ; un texte décomposé (NFD) reste dans le
    moteur fusionné. Lone surrogate, inconsistent forced groups: staged path; a decomposed text stays fused.
    """
    fused, python = _pair()
    decomposed = ("Le patient Ce\N{COMBINING ACUTE ACCENT}dric DUPONT, ne\N{COMBINING ACUTE ACCENT} le 03/03/1985, "
                  "12 rue de la Paix 75002 Paris.")
    assert fused._fused.detect(decomposed, fused._host) is not None
    _same(fused, python, decomposed)
    assert fused._fused.detect("Jean \ud800 Dupont", fused._host) is None
    assert fused._fused.detect_cells(["a", "b"], [frozenset()], fused._host) is None  # longueurs / lengths


def test_replaced_finalizer_disables_the_fused_engine():
    fused, python = _pair(operators={"EMAIL": "mask"})
    custom = {"EMAIL": lambda span, original, scope: "<email>"}
    fused._operators, python._operators = dict(custom), dict(custom)
    fused._finalizer = fused._native_finalizer()
    assert fused._fused_document("x") is None
    _same(fused, python, "Écrire à jean.dupont@exemple.fr ou à Jean Dupont, 06 12 34 56 78.")


def test_detector_subclass_keeps_its_own_detect():
    """Une classe dérivée peut changer `detect` : jamais de jumeau hérité / a subclass never inherits the twin."""
    from gdprguardian.heuristics.fr_names import FrenchNameDetector

    class Silent(FrenchNameDetector):
        def detect(self, ctx: Any) -> list[Span]:
            return []

    fused, python = _pair()
    for anonymizer in (fused, python):
        anonymizer._detectors["FR"] = [Silent(anonymizer.packs[1]) if type(d) is FrenchNameDetector else d
                                       for d in anonymizer._detectors["FR"]]
    fused._fused = fused._fused_engine()
    _same(fused, python, "Bonjour Jean Dupont, M. Martin vous rappellera.")
    assert "Dupont" in fused.anonymize("Bonjour Jean Dupont.").text


# --- Vérification adverse : corpus muté, portées partagées, objets de `ctx.found` ------------------------------------
# --- Adversarial verification: mutated corpus, shared scopes, `ctx.found` objects -----------------------------------

# Insertions adverses / adversarial insertions.
_INSERTS = ["\N{NO-BREAK SPACE}", "\N{NARROW NO-BREAK SPACE}", "\N{ZERO WIDTH SPACE}", "\N{SOFT HYPHEN}",
            "\N{WORD JOINER}", "\N{ZERO WIDTH NO-BREAK SPACE}", "\t", "\r", "\n", "\r\n", "\x0b", "\x0c", "\x85",
            "\x1c", "\x1d", "\x1e", "\x1f", "\x1f\x1f",
            "\N{LINE SEPARATOR}", "\N{PARAGRAPH SEPARATOR}", "\N{IDEOGRAPHIC SPACE}", "\N{COMBINING ACUTE ACCENT}",
            "\N{COMBINING CEDILLA}", "e\N{COMBINING ACUTE ACCENT}", "\U0001d400", "\U00010400", "\U0001f600",
            "\U0001f1eb\U0001f1f7", "\U000e0041", "\U0010ffff", "|", "\\|", "\n| a | Né le |\n|---|---|\n", "@",
            "+33 ", "00", "<!--", "![x](//e.fr)", "<img src=x>", "ß", "İ", "ﬁ", "Σ", "ς", "\N{KELVIN SIGN}", "\x00",
            "-", "'", "’", ".", " ", "  ", "M. ", "Mme ", "née le ", "SARL ", "IBAN ", "NIR "]
_CASES = {"keep": str, "upper": str.upper, "lower": str.lower, "title": str.title, "swapcase": str.swapcase}


def _mutated(text: str, cut: tuple[float, float], case: str, newline: str,
             inserts: list[tuple[float, str]]) -> str:
    """Extrait coupé en plein mot, casse changée, fins de ligne changées, insertions à des positions relatives.

    Excerpt cut mid-word, case changed, line endings changed, insertions at relative positions.
    """
    lo, hi = sorted(int(c * len(text)) for c in cut)
    piece = _CASES[case](text[lo:hi]).replace("\n", newline)
    for where, insert in inserts:
        at = int(where * len(piece))
        piece = piece[:at] + insert + piece[at:]
    return piece


def _outcome(anonymizer: Anonymizer, text: str) -> tuple:
    """Tout ce qu'un appel rend, mesures exceptées (sauf l'ordre des clés) / everything a call returns."""
    result, analysis = anonymizer.anonymize(text), anonymizer.analyze(text)
    keys = [k for k in result.report["timings_ms"] if k != "native"]
    return (result.text, _report(result.report), keys, [_key(s) for s in result.analysis.spans],
            [_key(s) for s in analysis.spans], analysis.countries, analysis.country_reasons, analysis.language,
            [k for k in analysis.timings_ms if k != "native"])


@settings(max_examples=250, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(index=st.integers(0, 999), cut=st.tuples(st.floats(0, 1), st.floats(0, 1)),
       case=st.sampled_from(list(_CASES)), newline=st.sampled_from(["\n", "\r\n", "\r", "\N{LINE SEPARATOR}"]),
       inserts=st.lists(st.tuples(st.floats(0, 1), st.sampled_from(_INSERTS)), max_size=10),
       variant=st.sampled_from(list(_VARIANTS)))
def test_mutated_corpus_identical(corpus, engines, index, cut, case, newline, inserts, variant):
    """Extraits du corpus coupés, recasés et truffés d'insertions adverses / cut, recased, adversarially seeded."""
    fused, python = engines[variant]
    text = _mutated(corpus[index], cut, case, newline, inserts)
    assert _outcome(fused, text) == _outcome(python, text)


@cache
def _explained() -> tuple[Anonymizer, Anonymizer]:
    return _pair(explain=True)


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(index=st.integers(0, 999), inserts=st.lists(
    st.tuples(st.floats(0, 1), st.sampled_from(["\x1c", "\x1d", "\x1e", "\x1f", "\x1f\x1f"])), min_size=1, max_size=8))
def test_unit_separators_identical(corpus, index, inserts):
    """U+001C-U+001F : `\\s` de `re` les compte comme blancs, et le noyau aussi (table Unicode partagée,
    rust/src/unicode.rs) : moteur fusionné et référence Python identiques. `re`'s `\\s` counts them as blanks, and
    so does the core (shared Unicode table): fused engine and Python reference are identical.
    """
    fused, python = _explained()
    text = _mutated(corpus[index], (0.0, 1.0), "keep", "\n", inserts)
    assert _outcome(fused, text) == _outcome(python, text)


def test_shared_scope_across_documents_identical(corpus):
    """Une portée partagée entre documents : mêmes balises d'un document à l'autre / one scope over documents."""
    for options in ({}, {"label_language": "en", "explain": True}, {"countries": "auto", "rules": _RULES}):
        fused, python = _pair(**options)
        with fused.new_scope("fr") as scope_f, python.new_scope("fr") as scope_p:
            for scope in (scope_f, scope_p):
                scope.reserve("[PERSONNE_3] [EMAIL_1]")
            for text in corpus[:120]:
                left, right = fused.anonymize(text, scope_f), python.anonymize(text, scope_p)
                assert left.text == right.text
                assert _report(left.report) == _report(right.report)
                assert [_key(s) for s in left.analysis.spans] == [_key(s) for s in right.analysis.spans]


class _Mutator:
    """Détecteur Python qui modifie les objets de `ctx.found` (hors contrat, mais vu par la référence).

    Python detector that changes `ctx.found` objects (outside the contract, but seen by the reference).
    """

    id = "MUTATOR"

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def detect(self, ctx: DetectionContext) -> list[Span]:
        found = list(ctx.found)
        if self.mode == "shift":
            for span in found:
                span.start = max(0, span.start - 1)
        elif self.mode == "unmask":
            for span in found:
                span.personal = span.entity != "PHONE"
        elif self.mode == "return":
            return [s for s in found if s.entity == "PERSON"]  # le même objet deux fois / the same object twice
        elif self.mode == "read":
            assert all(a is b for a, b in zip(found, ctx.found, strict=True))  # mêmes objets / same objects
        return []


@pytest.mark.parametrize("mode", ["shift", "unmask", "return", "read"])
def test_python_changes_to_found_objects_are_seen(corpus, mode):
    """Comme la liste `ctx.found` de Python, chaque zone garde son objet et ses modifications comptent.

    As Python's `ctx.found` list, each span keeps its object and changes to it count.
    """
    fused, python = _pair(detectors=(_Mutator(mode),), explain=True)
    for text in ["Jean Dupont, 06 12 34 56 78, jean.dupont@exemple.fr, NIR 1 85 05 78 006 084 91.", *corpus[:40]]:
        _same(fused, python, text)
        _same_cells(fused, python, text.split("\n"))


def test_results_stay_dataclasses_and_pickle():
    """`Analysis` différée : toujours une dataclass, copiable et sérialisable (`multiprocessing`).

    Deferred `Analysis`: still a dataclass, copyable and picklable (`multiprocessing`).
    """
    import copy
    import dataclasses
    import pickle

    fused, python = _pair()
    text = "Bonjour Jean Dupont, 06 12 34 56 78."
    left, right = fused.anonymize(text), python.anonymize(text)
    assert dataclasses.is_dataclass(left.analysis)
    assert [f.name for f in dataclasses.fields(left.analysis)] == [f.name for f in dataclasses.fields(right.analysis)]
    assert pickle.loads(pickle.dumps(left)) == left
    assert left.analysis.spans == right.analysis.spans
    assert copy.deepcopy(fused.anonymize(text)).analysis.spans == right.analysis.spans
    as_dict = dataclasses.asdict(fused.anonymize(text))
    assert as_dict["analysis"]["spans"] == dataclasses.asdict(right)["analysis"]["spans"]
    assert dataclasses.replace(fused.anonymize(text).analysis, text="x").spans == right.analysis.spans


def test_auto_mode_builds_no_span_object(corpus, monkeypatch):
    """Mode auto : les preuves du premier passage sont lues en Rust, sans objet `Span` / read in Rust, no object."""
    fused = Anonymizer(countries="auto")
    fused.anonymize(corpus[0])
    built: list[int] = []
    original = Span.__init__

    def counting(self: Span, *args: Any, **kwargs: Any) -> None:
        built.append(1)
        original(self, *args, **kwargs)

    monkeypatch.setattr(Span, "__init__", counting)
    for text in corpus[:100]:
        fused.anonymize(text)
    assert built == []


class _Evidence:
    """Zones Python du second passage (mode auto), pour comparer les preuves / second-pass Python spans."""

    id = "EVIDENCE"

    def __init__(self) -> None:
        self.values: list[tuple[str, str | None]] = []

    def detect(self, ctx: DetectionContext) -> list[Span]:
        return [Span(0, 1, entity, entity, "X", 0.9, 60, value) for entity, value in self.values]


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(values=st.lists(st.tuples(st.sampled_from(["IBAN", "PHONE", "EMAIL", "PERSON"]), st.none() | st.text(
    alphabet=st.sampled_from(["a", "Z", ".", "+", "3", "ß", "İ", "ﬁ", "é", "\U0001d400", "@"]), max_size=7)),
    max_size=8))
def test_evidence_port_matches_python(values):
    """Preuves du mode auto lues en Rust : celles de `locale.evidence`, ou `None` (casse de Python requise).

    Auto-mode evidence read in Rust: `locale.evidence`'s, or `None` (Python's case rules needed).
    """
    from gdprguardian.locale import evidence

    injector = _Evidence()
    injector.values = values
    fused = Anonymizer(countries="auto", detectors=(injector,))
    document = fused._fused.detect("Jean Dupont, +33 6 12 34 56 78, jean@exemple.be, FR7630006000011234567890189",
                                   fused._host)
    native, expected = document.evidence(), evidence(document.found())
    if native is None:
        assert any(e in ("IBAN", "EMAIL") and v and not v.isascii() for e, v in values)
    else:
        assert native == expected


@pytest.mark.parametrize("make", [
    lambda ctx: [Span(5, 10**6, "PERSON", "PERSON", "H", 0.9, 60)],
    lambda ctx: [Span(-5, 3, "PERSON", "PERSON", "H", 0.9, 60)],
    lambda ctx: [Span(8, 2, "PERSON", "PERSON", "H", 0.9, 60)],
    lambda ctx: [Span(0, 4, "PERSON", "PERSON", "H", 0.9, 10**30)],
    lambda ctx: [Span(0, 4, "PERSON", "PERSON", "H", float("inf"), 60)],
    lambda ctx: [Span(0, 4, "PERSON", "PERSON", "H", 0.9, 60, None, True, ["Jean"], True)],
    lambda ctx: [(0, 4, "PERSON")],
    lambda ctx: (Span(0, 4, "PERSON", "PERSON", "H", 0.9, 60) for _ in range(2)),
    lambda ctx: 1 / 0,
    lambda ctx: [Span(0, len(ctx.text), "_KEEP", "KEEP", "H", 1.0, 100)],
], ids=["beyond", "negative", "reversed", "huge-priority", "inf-score", "list-forms", "tuple", "generator",
        "raises", "keep-all"])
def test_hostile_python_spans_identical(make):
    """Zones Python hors du domaine natif : même résultat, ou même exception, que la référence.

    Python spans outside the native domain: the same result, or the same exception, as the reference.
    """
    class Hostile:
        id = "HOSTILE"

        def detect(self, ctx: DetectionContext) -> Any:
            return make(ctx)

    def run(anonymizer: Anonymizer, text: str) -> Any:
        try:
            return _outcome(anonymizer, text)
        except Exception as exc:  # l'exception elle-même est comparée / the exception itself is compared
            return type(exc), str(exc)

    fused, python = _pair(detectors=(Hostile(),), explain=True)
    for text in ["Jean Dupont, 06 12 34 56 78, né le 03/03/1985, NIR 1 85 05 78 006 084 91.", "abc", ""]:
        assert run(fused, text) == run(python, text)


@pytest.mark.parametrize("filler", ["x", "é", "\U0001f600", "-", ">", " ", "\n"])
def test_sanitize_twin_at_the_closing_limits(filler):
    """Fermetures à la limite exacte : `-->` à 20 000 caractères, `>` à 2 000, en caractères et non en octets.

    Closings right at the limit: `-->` within 20,000 characters, `>` within 2,000, counted in characters.
    """
    twin = partial(_native.core().sanitize_output, _native.unicode_table())
    for size in (0, 1, 1999, 2000, 2001, 19_999, 20_000, 20_001):
        for text in (f"a<!--{filler * size}-->b<!--c-->", f"<img{' ' if size else ''}{filler * size}>z<IMG>",
                     f"<!--{filler * size}<!--x-->-->", f"<img {filler * size}<img a>>"):
            assert twin(text) == sanitize_output(text)


def test_sanitize_twin_is_linear_on_hostile_text():
    """« <!-- » ou « <img » répétés sans fermeture : chaque octet lu une fois, pas 20 000 caractères par ouverture.

    Repeated unclosed openings: every byte read once, not 20,000 characters per opening.
    """
    twin = partial(_native.core().sanitize_output, _native.unicode_table())
    for unit in ("<!--", "<img ", "<!-- -- -"):
        small = unit * 2_000
        assert twin(small + "-->") == sanitize_output(small + "-->")
        started = time.perf_counter()
        twin(unit * 500_000)  # 2 à 4,5 Mo / 2 to 4.5 MB
        assert time.perf_counter() - started < 10  # ~ 0,05 s ; > 60 s par ouverture / per-opening reading


def _best_time(function: Any, text: str, rounds: int = 5) -> float:
    """Meilleur temps de `function(text)` sur quelques essais / best time over a few runs."""
    times = []
    for _ in range(rounds):
        started = time.perf_counter()
        function(text)
        times.append(time.perf_counter() - started)
    return min(times)


def test_sanitize_twin_is_not_slower_than_python():
    """Un « < » par caractère : les équivalents de « img » sont calculés une fois par appel, rien par « < » (une
    allocation par comparaison rendait le jumeau 6 à 15 fois plus lent que Python). One `<` per character: the
    equivalents of "img" are computed once per call, nothing per `<` (one allocation per comparison made the twin
    6 to 15 times slower than Python).
    """
    twin = partial(_native.core().sanitize_output, _native.unicode_table())
    for text in ("<" * 400_000, "<im " * 100_000, "<İMG " * 80_000):
        assert twin(text) == sanitize_output(text)
        assert _best_time(twin, text) <= 2 * _best_time(sanitize_output, text), repr(text[:5])


# --- Texte décomposé (NFD) : moteur fusionné, trois détecteurs à vue NFC en Python ---------------------------------
# --- Decomposed (NFD) text: fused engine, three NFC-view detectors in Python ---------------------------------------

# Diacritiques combinants, avec ou sans forme composée (« x̄ », yoruba) / combining marks, composable or not.
_MARKS = ["\N{COMBINING ACUTE ACCENT}", "\N{COMBINING GRAVE ACCENT}", "\N{COMBINING CIRCUMFLEX ACCENT}",
          "\N{COMBINING DIAERESIS}", "\N{COMBINING CEDILLA}", "\N{COMBINING TILDE}", "\N{COMBINING DOT BELOW}",
          "\N{COMBINING HORN}", "\N{COMBINING OGONEK}", "x\N{COMBINING MACRON}", "e\N{COMBINING ACUTE ACCENT}",
          "Ade\N{COMBINING DOT BELOW}s\N{COMBINING DOT BELOW}o\N{COMBINING DOT BELOW}\N{COMBINING GRAVE ACCENT}la"
          "\N{COMBINING ACUTE ACCENT}"]
_ACCENTED = ["Hélène Lefèvre", "née le 3 décembre 1985", "Société Générale SAS", "rue de l'Église", "Brûlé",
             "Mme Françoise Céleste", "12 avenue des Prés 75011 Paris", "SARL Les Frères Pérès", "Noël", "Ø"]
_NFD_PIECES = (st.sampled_from([*_WORDS, *_ACCENTED]).map(partial(unicodedata.normalize, "NFD"))
               | st.sampled_from(_MARKS) | _PIECES)


@pytest.mark.parametrize("variant", list(_VARIANTS))
def test_decomposed_corpus_identical(corpus, engines, variant, monkeypatch):
    """Corpus en NFD (macOS, texte brut, cellules) : le document reste dans le moteur fusionné, sans repli ; seuls
    noms, adresses et organisations passent par leur `detect` Python (vue NFC). NFD corpus: the document stays in
    the fused engine, without fallback; only names, addresses and organisations run their Python `detect`.
    """
    fused, python = engines[variant]
    _NoStaged(monkeypatch, fused)
    for index, text in enumerate(corpus[::8]):
        decomposed = unicodedata.normalize("NFD", text)
        _same(fused, python, decomposed, analyze=index % 3 == 0)
    for text in corpus[3:400:20]:
        cells = [unicodedata.normalize("NFD", cell) for cell in re.split(r"\n+", text) if cell]
        _same_cells(fused, python, cells, [fused.context_groups(cell[:20]) for cell in cells])


@_FUZZ
@given(words=st.lists(_NFD_PIECES, max_size=30), variant=st.sampled_from(list(_VARIANTS)),
       separator=st.sampled_from([" ", "\n", ""]))
@example(words=["Ade\N{COMBINING DOT BELOW}la", " ", "Dupont"], variant="default", separator=" ")
def test_decomposed_texts_identical(engines, words, variant, separator):
    """Diacritiques combinants partout, composables ou non / combining marks everywhere, composable or not."""
    fused, python = engines[variant]
    text = separator.join(words)
    _same(fused, python, text)
    _same_cells(fused, python, text.split("["))


# --- Robustesse / robustness --------------------------------------------------------------------------------------


def test_forced_groups_must_match_the_segments():
    """Un ensemble imposé par segment : sinon ValueError sur les deux chemins, jamais de panique du noyau.

    One forced set per segment: otherwise a ValueError on both paths, never a core panic.
    """
    fused, python = _pair()
    cells = ["Jean Dupont", "06 12 34 56 78"]
    for forced in ([frozenset()], [], [frozenset()] * 3):
        for anonymizer in (fused, python):
            with pytest.raises(ValueError, match="forced"):
                anonymizer.analyze_segments(cells, forced)
            with anonymizer.new_scope() as scope, pytest.raises(ValueError, match="forced"):
                anonymizer.anonymize_segments(cells, scope, forced)
    # Analyseur natif appelé directement : ValueError aussi / native scanner called directly: ValueError too.
    text = "\n\n".join(cells)
    folded = fold(text)
    scanner = fused._native
    with pytest.raises(ValueError, match="forced"):
        scanner.scan(scanner.keywords(folded), text, folded, frozenset(p.id for p in fused.packs), False, "auto",
                     False, (), [(0, 11), (13, 27)], [frozenset()])


def _flaky_tables(error: type[BaseException], plane: int = 1) -> Any:
    """Table Unicode dont le chargeur échoue une fois sur `plane` (mémoire épuisée, interruption…).

    Unicode table whose loader fails once for `plane` (out of memory, interrupt…).
    """
    from gdprguardian import _text
    from gdprguardian.heuristics._lexicon import UPPER

    loader = partial(_text.plane_classes, capital=UPPER)
    failures = [plane]

    def flaky(index: int) -> Any:
        if index in failures:
            failures.remove(index)
            raise error("échec simulé / simulated failure")
        return loader(index)

    return _native.core().UnicodeTables(bmp=loader(0), loader=flaky, fold=sorted(_text.FOLD_TABLE.items()),
                                        ignorecase=_text.ignorecase_data(), perl_planes=[1, 2, 3])


def test_plane_loading_errors_propagate(monkeypatch):
    """Une erreur de Python au chargement d'un plan remonte de chaque liaison qui rend le GIL, au lieu d'un plan vide
    et d'un résultat approché (adresse e-mail tronquée, IBAN de trop) ; l'appel suivant charge le plan et rend le
    résultat exact. A Python error while loading a plane propagates from every binding that releases the GIL,
    instead of an empty plane and an approximate result; the next call loads the plane and is exact.
    """
    from gdprguardian.detectors import fr as fr_detectors
    from gdprguardian.detectors import intl
    from gdprguardian.heuristics import fr_address, fr_names, organizations
    from gdprguardian.validators.intl import IBAN_LENGTHS

    core = _native.core()
    bold = "\U0001d41a\U0001d41b"  # lettres du plan 1 / plane-1 letters
    text = (f"Contact : {bold}.dupont@example.com, 12 rue de la Paix 75002 Paris {bold}, Acme SAS {bold}, Jean Dupont"
            f" {bold}, né le 03/05/1985 {bold}, IBAN FR7630006000011234567890189\U0001d7cf, +33 6 12 34 56 78, "
            f"<img{bold} src=x>")
    folded = fold(text)

    # Chaque liaison, construite sur `table` (jumeaux des modules, sans leur cache) / each binding, over `table`.
    calls = {
        "email": lambda table: core.EmailDetector(table).detect(text),
        "iban": lambda table: core.IbanDetector(table, IBAN_LENGTHS).detect(text),
        "birth_dates": lambda _: fr_detectors._native_twin.__wrapped__().detect(text, folded, {("85", "05")}),
        "address": lambda _: fr_address._native_twin.__wrapped__().detect(text, folded, True, True, False),
        "organizations": lambda _: organizations._native_twin.__wrapped__().candidates(text, folded),
        "names": lambda _: _native.name_detector(fr_names._native_data).detect(text, folded),
        "sanitize": lambda table: core.sanitize_output(table, text),
        "phone": lambda _: intl._native_phone.__wrapped__()(text),
    }

    def run(name: str, table: Any) -> Any:
        monkeypatch.setattr(_native, "unicode_table", lambda: table)
        monkeypatch.setattr(_native, "unicode_tables", lambda: table)
        return calls[name](table)

    fresh = _native.unicode_tables.__wrapped__  # table neuve et saine / a fresh, sound table
    for name in calls:
        expected = run(name, fresh())
        flaky = _flaky_tables(MemoryError)
        with pytest.raises(MemoryError):
            run(name, flaky)
        assert run(name, flaky) == expected, name
    flaky = _flaky_tables(KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        run("email", flaky)
    assert run("email", flaky) == run("email", fresh())
