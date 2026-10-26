"""Finalisation en Rust contre la référence Python : zones, textes et rapports strictement identiques.

Rust finalisation against the Python reference: strictly identical spans, texts and reports (resolution,
propagation, rendering, irreversible scope). Corpus de 1 000 documents et fuzzing Hypothesis avec de
l'Unicode adverse (accents, marques combinantes, caractères astraux, invisibles, substituts isolés, jetons
très longs). 1,000-document corpus and Hypothesis fuzzing with adversarial Unicode.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gdprguardian import Anonymizer, Scope, _native, operators
from gdprguardian._text import fold
from gdprguardian.custom import KEEP_ENTITY
from gdprguardian.engine import DetectionContext, Settings
from gdprguardian.scope import native_rules, split_person_name
from gdprguardian.types import Span

# Noyau absent ou désactivé (GDPRGUARDIAN_PURE_PYTHON=1) : rien à comparer / no core (or disabled): nothing to compare.
pytestmark = pytest.mark.skipif(not _native.available(), reason="noyau Rust absent / no Rust core")

_DOCS = sorted((Path(__file__).resolve().parents[1] / "datasets" / "fr" / "docs").glob("*.md"))
# Une règle « keep » active `_apply_keep` sans rien trouver / a keep rule enables `_apply_keep`, matching nothing.
_KEEP_RULES = {"rules": [{"label": "REF", "pattern": "QZQZQZ", "action": "keep"}]}
_VARIANTS: dict[str, dict[str, Any]] = {
    "default": {},
    "explain_operators": {"explain": True, "operators": {"PHONE": "mask", "BIRTH_DATE": "generalize",
                                                         "POSTAL_CODE": "generalize", "EMAIL": "redact",
                                                         "ORG": "keep", "SECRET": "keep"}},
    "english_neutral": {"label_language": "en", "neutral_labels": True, "company_ids": "mask"},
    "auto_labels_rules": {"label_language": "auto", "rules": _KEEP_RULES, "allow_list": ["Jourdan Industries SA"],
                          "deny_list": {"Projet": ["Florence"]}, "profile": "strict"},
}
_FUZZ = settings(max_examples=250, deadline=None, suppress_health_check=[HealthCheck.too_slow])

# Unicode adverse : casses spéciales, marques combinantes, chiffres non ASCII, espaces, invisibles, astraux.
# Adversarial Unicode: special casing, combining marks, non-ASCII digits, spaces, invisibles, astral characters.
_ADVERSARIAL = [
    "é", "É", "ß", "ĸ", "ǅ", "İ", "ŉ", "ﬁ", "\u0301", "\u0345", "Ⓐ", "ⓐ", "²", "٣", "①", "Ⅻ", "\u00a0", "\u2009",
    "\u3000", "\x1c", "\u200b", "\u00ad", "\ufeff", "\u2060", "’", "'", "-", ".", " ", "\n", "\t", "[", "]", "_",
    "😀", "𝐀", "𐐀", "𐐨", "𞤀", "\U0001f1eb", "\U000e0041", "\U0010fffd",
]
_WORDS = [
    "Jean", "Dupont", "DUPONT", "Marie", "M.", "Mme", "Dr", "Monsieur", "J.", "Pierre", "O'Neil", "Jean-Pierre",
    "Zoé", "Ñúñez", "ÉLODIE", "Ǆemal", "𐐀𐐨𐐨", "[PERSONNE_1]", "[TEL_2]", "[ORG_A_12]", "06 12 34 56 78",
    "jean.dupont@exemple.fr", "75011", "97400", "né le 03/03/1985", "1 85 05 78 006 084 91", "SAS", "Paris",
    "12 rue de la Paix", "entrepreneur individuel", "SIREN 732 829 320", "Commande 732829320", "A" * 3000,
    "\U0001f1eb\U0001f1f7 Jean\u0301 Dupont", "e\u0301le\u0300ve DUPONT\u0345",
]
_PIECES = st.sampled_from(_WORDS) | st.sampled_from(_ADVERSARIAL) | st.text(
    alphabet=st.sampled_from([*_ADVERSARIAL, *"aZ09 "]), max_size=12)
_TEXT = st.lists(_PIECES, max_size=30)


def _span_tuple(span: Span) -> tuple:
    return (span.start, span.end, span.entity, span.label, span.source, span.value, round(span.score, 9),
            span.priority, span.personal, span.forms, span.propagate)


def _spans(spans: list[Span]) -> list[tuple]:
    return [_span_tuple(span) for span in spans]


def _report(report: dict[str, Any]) -> dict[str, Any]:
    """Rapport sans les mesures de temps ni l'indicateur du moteur / report without timings and engine flag."""
    return {k: v for k, v in report.items() if k not in ("timings_ms", "native")}


class _Strict:
    """Finaliseur qui refuse tout repli sur Python : le chemin natif est bien celui testé.

    Finalizer that refuses any Python fallback: the native path is really the one under test.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        method = getattr(self._inner, name)
        if not callable(method):
            return method

        def call(*args: Any, **kwargs: Any) -> Any:
            result = method(*args, **kwargs)
            assert result is not None, f"repli Python inattendu / unexpected Python fallback: {name}"
            return result

        return call


def _pair(**overrides: Any) -> tuple[Anonymizer, Anonymizer]:
    """Moteur natif complet et moteur Python complet (`native=False`) / full native and full Python engines."""
    native = Anonymizer(**overrides)
    python = Anonymizer(**overrides, native=False)
    assert native._finalizer is not None and python._finalizer is None
    return native, python


def _reference(**overrides: Any) -> Anonymizer:
    """Même détection que le moteur natif, finalisation et portée Python de référence.

    Same detection as the native engine, reference Python finalisation and scope: isolates this layer from
    the scanner (whose own differential tests live in test_native_engine.py).
    """
    engine = Anonymizer(**overrides)
    engine._finalizer = None
    engine.new_scope = lambda language="und": Scope(engine._label_language(language), engine.settings.neutral_labels,
                                                    native=False)
    return engine


def _strict_pair(**overrides: Any) -> tuple[Anonymizer, Anonymizer]:
    """Finalisation Rust stricte (aucun repli) contre la référence Python / strict Rust versus the reference."""
    native = Anonymizer(**overrides)
    native._finalizer = _Strict(native._finalizer)
    return native, _reference(**overrides)


def _same_anonymization(native: Anonymizer, python: Anonymizer, text: str) -> None:
    left, right = native.anonymize(text), python.anonymize(text)
    assert left.text == right.text
    assert _report(left.report) == _report(right.report)
    # Mêmes étapes mesurées ; « native » est le temps de l'analyseur Rust / same stages; "native" is the Rust scan.
    assert ([k for k in left.report["timings_ms"] if k != "native"]
            == [k for k in right.report["timings_ms"] if k != "native"])
    assert _spans(left.analysis.spans) == _spans(right.analysis.spans)
    assert _spans(native.analyze(text).spans) == _spans(python.analyze(text).spans)


def _same_segments(native: Anonymizer, python: Anonymizer, cells: list[str],
                   forced: list[frozenset[str]] | None = None) -> None:
    left, right = native.analyze_segments(cells, forced), python.analyze_segments(cells, forced)
    assert [_spans(segment) for segment in left[0]] == [_spans(segment) for segment in right[0]]
    assert _spans(left[1].spans) == _spans(right[1].spans)
    with native.new_scope("fr") as scope_n, python.new_scope("fr") as scope_p:
        assert scope_n.native and not scope_p.native
        for scope in (scope_n, scope_p):
            scope.reserve("[PERSONNE_2] [TEL_1]")
        out_n, report_n = native.anonymize_segments(cells, scope_n, forced)
        out_p, report_p = python.anonymize_segments(cells, scope_p, forced)
    assert out_n == out_p
    assert _report(report_n) == _report(report_p)


@pytest.fixture(scope="module")
def corpus() -> list[str]:
    return [path.read_text(encoding="utf-8") for path in _DOCS]


@pytest.fixture(scope="module")
def engines() -> dict[str, tuple[Anonymizer, Anonymizer]]:
    """Finalisation Rust stricte contre la référence Python / strict Rust finalisation versus the reference."""
    return {name: _strict_pair(**options) for name, options in _VARIANTS.items()}


# --- Corpus -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("variant", list(_VARIANTS))
def test_corpus_identical(corpus, engines, variant):
    native, reference = engines[variant]
    full_native, full_python = _pair(**_VARIANTS[variant])
    assert native._finalizer.renders
    # Corpus complet pour le réglage par défaut, un document sur cinq sinon / full corpus by default.
    texts = corpus if variant == "default" else corpus[::5]
    assert len(texts) >= 200
    for text in texts:
        _same_anonymization(native, reference, text)
        # De bout en bout : native=True contre native=False / end to end: native=True versus native=False.
        _same_anonymization(full_native, full_python, text)


def test_large_documents_identical(corpus, engines):
    """Grands textes : la propagation passe par l'automate Aho-Corasick / large texts use the automaton."""
    native, python = engines["default"]
    joined = "\n\n".join(corpus[:80])
    assert len(joined) > 100_000
    _same_anonymization(native, python, joined)
    for unit in ("Jean Dupont ", "M. Dupont, Mme Martin ; ", "DUPONT Jean\n", "Zoé Ñúñez 😀 "):
        _same_anonymization(native, python, unit * (40_000 // len(unit)))


def test_corpus_segments_identical(corpus, engines):
    native, python = engines["default"]
    for text in corpus[:150]:
        cells = [cell for cell in re.split(r"\n+", text) if cell]
        _same_segments(native, python, cells, [native.context_groups(cell[:20]) for cell in cells])


# --- Textes adverses / adversarial texts ----------------------------------------------------------------


@_FUZZ
@given(words=_TEXT, variant=st.sampled_from(list(_VARIANTS)), separator=st.sampled_from([" ", "\n", ""]))
def test_random_texts_identical(engines, words, variant, separator):
    native, python = engines[variant]
    text = separator.join(words)
    _same_anonymization(native, python, text)
    _same_segments(native, python, text.split("["))


# --- Zones arbitraires injectées par un détecteur / arbitrary spans injected by a detector ---------------

_ENTITIES = ["PERSON", "ORG", "ADDRESS", "LOCATION", "EMAIL", "PHONE", "NATIONAL_ID", KEEP_ENTITY, "SECRET",
             "BIRTH_DATE", "POSTAL_CODE", "DATE", "CUSTOM", "IBAN"]
_LABELS = ["PERSON", "ORG", "ADDRESS", "PHONE", "NIR", "TVA", "PROJET", "BIRTH_DATE", "POSTAL_CODE", "IBAN", "s"]
_SOURCES = ["FR_NAMES", "INTL_IBAN", "NER_x", "ner", "deny_list", "CUSTOM_1_REF", "FR_NIR", "FR_SIREN", "a+b",
            "keep:z", "propagated:q", "ORGANIZATIONS", "FR_ADDRESS", "detector", "İNER", "FR_NIR+X", "😀"]


class _Injector:
    """Détecteur rejouant une spécification, avec des zones fraîches à chaque appel / replays a spec."""

    id = "INJECT"

    def __init__(self) -> None:
        self.spec: list[tuple] = []

    def detect(self, ctx: DetectionContext) -> list[Span]:
        length = len(ctx.text)
        spans = []
        for start, size, entity, label, source, score, priority, value, personal, forms, propagate in self.spec:
            start = min(start, length)
            spans.append(Span(start, min(start + size, length), entity, label, source, score, priority, value,
                              personal, forms, propagate))
        return spans


_SPAN_SPEC = st.tuples(
    st.integers(0, 120), st.integers(0, 40), st.sampled_from(_ENTITIES), st.sampled_from(_LABELS),
    st.sampled_from(_SOURCES), st.floats(0.0, 1.0) | st.sampled_from([0.0, -0.0, 0.5, 1.0]),
    st.sampled_from([50, 55, 60, 70, 80, 85, 95, 99, 100]),
    st.none() | st.sampled_from(["", "x", "Jean Dupont", "06 12 34 56 78"])
    | st.text(st.sampled_from([*_ADVERSARIAL, *"aZ09"]), max_size=8),
    st.booleans(), st.lists(st.sampled_from([*_WORDS, "", " ", "ab", "Dupont "]), max_size=3).map(tuple),
    st.booleans())


@pytest.fixture(scope="module")
def injected() -> tuple[Anonymizer, Anonymizer, _Injector]:
    injector = _Injector()
    native, python = _strict_pair(detectors=(injector,), rules=_KEEP_RULES, explain=True, operators={
        "PHONE": "mask", "DATE": "generalize", "POSTAL_CODE": "generalize", "BIRTH_DATE": "generalize",
        "ORG": "redact", "LOCATION": "keep"})
    return native, python, injector


@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(words=_TEXT, spec=st.lists(_SPAN_SPEC, max_size=14))
def test_injected_spans_identical(injected, words, spec):
    native, python, injector = injected
    injector.spec = spec
    text = " ".join(words)
    _same_anonymization(native, python, text)
    _same_segments(native, python, text.split("["))


@st.composite
def _text_spans(draw: Any) -> tuple[str, list[tuple]]:
    """Zones tirées du texte même : formes et valeurs en sont des sous-chaînes, que la propagation retrouve.

    Spans drawn from the text itself: forms and values are substrings of it, which propagation finds again.
    """
    text = " ".join(draw(_TEXT))
    length = len(text)
    spec = []
    for _ in range(draw(st.integers(0, 16))):
        start, size = draw(st.integers(0, length)), draw(st.integers(0, 30))
        cuts = draw(st.lists(st.tuples(st.integers(0, length), st.integers(0, length)), max_size=2))
        spec.append((start, size, draw(st.sampled_from(["PERSON", "PERSON", *_ENTITIES])),
                     draw(st.sampled_from(_LABELS)), draw(st.sampled_from(_SOURCES)),
                     draw(st.sampled_from([0.3, 0.5, 0.9, 1.0, -0.0])), draw(st.sampled_from([50, 60, 70, 95, 100])),
                     draw(st.none() | st.just(text[start:start + size])), draw(st.booleans()),
                     tuple(text[a:b] for a, b in cuts if a < b), draw(st.booleans())))
    return text, spec


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(case=_text_spans(), cuts=st.lists(st.integers(0, 300), max_size=5))
def test_spans_drawn_from_the_text_identical(injected, case, cuts):
    native, python, injector = injected
    text, injector.spec = case[0], case[1]
    _same_anonymization(native, python, text)
    # Segments coupés n'importe où, même au milieu d'un mot / segments cut anywhere, even inside a word.
    edges = sorted({min(cut, len(text)) for cut in cuts})
    _same_segments(native, python, [text[a:b] for a, b in zip([0, *edges], [*edges, len(text)], strict=True)])


def test_spans_outside_the_native_domain_fall_back_to_python():
    class Twice:
        """Le même objet deux fois : Python le modifie deux fois / the same object twice, mutated twice."""

        id = "TWICE"

        @staticmethod
        def detect(ctx: DetectionContext) -> list[Span]:
            shared = Span(0, 4, "PERSON", "PERSON", "x", 0.9, 60, propagate=True)
            return [shared, shared] if len(ctx.text) >= 4 else []

    native, python = _pair(detectors=(Twice(),))
    finalizer = native._finalizer
    shared = Span(0, 4, "PERSON", "PERSON", "x", 0.9, 60)
    assert finalizer.analyze([shared, shared], "Jean Dupont") is None  # même objet deux fois / same object twice
    assert finalizer.analyze([Span(0, 99, "PERSON", "PERSON", "x")], "Jean") is None  # hors du texte / out of text
    assert finalizer.analyze([Span(0, 2, "PERSON", "PERSON", "x", 1)], "Jean") is None  # score entier / int score
    assert finalizer.analyze([Span(0, 2, "PERSON", "PERSON", "x", float("nan"))], "Jean") is None
    assert finalizer.analyze([], "Jean \ud800") is None  # substitut isolé / lone surrogate
    assert finalizer.analyze([], "Jean") == []
    _same_anonymization(native, python, "Jean Dupont")


def test_custom_operator_keeps_python_rendering():
    native, python = _pair(operators={"EMAIL": "mask"})
    assert native._finalizer.renders
    custom = {"EMAIL": lambda span, original, scope: "<email>"}
    native._operators, python._operators = dict(custom), dict(custom)
    native._finalizer = native._native_finalizer()
    assert not native._finalizer.renders
    _same_anonymization(native, python, "Écrire à jean.dupont@exemple.fr ou à Jean Dupont, 06 12 34 56 78.")
    assert operators.NATIVE_NAMES[operators.mask] == "mask"


def test_parallel_calls_are_consistent(corpus, engines):
    native, python = engines["default"]
    texts = corpus[:64]
    expected = [python.anonymize(text).text for text in texts]
    with ThreadPoolExecutor(8) as pool:
        assert list(pool.map(lambda text: native.anonymize(text).text, texts)) == expected


# --- Portée / scope -------------------------------------------------------------------------------------

_NAMES = ["Jean Dupont", "M. Dupont", "J. Dupont", "DUPONT Jean", "jean dupont", "Marie Dupont", "Dupont", "Pierre",
          "Pierre Martin", "Mme Martin", "MARTIN", "P. Martin", "Dr Ǆemal ÉLODIE", "Zoé", "Zoé Ñúñez", "ÑÚÑEZ Zoé",
          "42", "", "  ", "O'Neil-Smith", "𐐀𐐨𐐨 Dupont", "Jean-Pierre Dupont", "ﬁona Dupont", "İlker DUPONT"]
_VALUES = st.sampled_from(_NAMES) | st.text(st.sampled_from([*_ADVERSARIAL, *"aZ "]), max_size=10)


@_FUZZ
@given(calls=st.lists(st.tuples(st.sampled_from(["PERSON", "EMAIL", "NIR", "PROJET"]),
                                st.sampled_from(["PERSON", "EMAIL", "NATIONAL_ID", "CUSTOM"]), _VALUES), max_size=25),
       reserved=st.lists(st.sampled_from(["[PERSONNE_1]", "[EMAIL_2]", "[NIR_1] [NIR_3]", "[PROJET_9999999]", "x"]),
                         max_size=3),
       language=st.sampled_from(["fr", "en"]), neutral=st.booleans())
def test_scope_numbering_identical(calls, reserved, language, neutral):
    with Scope(language, neutral) as left, Scope(language, neutral, native=False) as right:
        assert left.native and not right.native
        for text in reserved:
            left.reserve(text)
            right.reserve(text)
        for label, entity, value in calls:
            assert left.placeholder(label, entity, value) == right.placeholder(label, entity, value)
            # Grappe « p<n> » et clé brute identiques ; « s<empreinte> » dépend de la clé / digest keys differ.
            key_n, key_p = left.person_key(value), right.person_key(value)
            assert key_n == key_p or (key_n.startswith("s\x1f") and key_p.startswith("s\x1f"))


@_FUZZ
@given(_VALUES | st.text(st.sampled_from([*_ADVERSARIAL, *"aZ-'. "]), max_size=24))
def test_split_person_name_identical(text):
    assert native_rules().split_person_name(text) == split_person_name(text)


def test_lone_surrogates_in_scope_values():
    with Scope() as left, Scope(native=False) as right:
        assert left.placeholder("PERSON", "PERSON", "Jean\ud800Dupont") == right.placeholder(
            "PERSON", "PERSON", "Jean\ud800Dupont")
        for scope in (left, right):
            scope.reserve("\ud800[TEL_1]")
            with pytest.raises(UnicodeEncodeError):
                scope.placeholder("EMAIL", "EMAIL", "a\ud800@b.fr")
            with pytest.raises(UnicodeEncodeError):
                scope.placeholder("PERSON", "PERSON", "\ud800 42")
        assert left.placeholder("PHONE", "PHONE", "x") == right.placeholder("PHONE", "PHONE", "x") == "[TEL_2]"
        assert left.person_key("x\ud800 1") == right.person_key("x\ud800 1")


def test_unicode_semantics_match_python_on_every_code_point():
    """Chaque propriété lue par Rust, sur chaque point de code hors substituts / every property, every code point.

    Les règles de texte lisent la table unique du noyau, plans hors BMP compris (chargés une fois, jamais par
    un appel à chaque document). The text rules read the core's single table, astral planes included.
    """
    every = "".join(chr(cp) for cp in range(0x110000) if not 0xD800 <= cp < 0xE000)
    rules = native_rules()
    flags = rules.flags(every)
    T = _native.core().UnicodeTables
    tests = ((T.ALNUM, str.isalnum), (T.ALPHA, str.isalpha), (T.DECIMAL, str.isdecimal), (T.DIGIT, str.isdigit),
             (T.SPACE, str.isspace), (T.UPPER, str.isupper))
    for bit, test in tests:
        expected = bytes(map(test, every))
        assert all(bool(f & bit) == bool(e) for f, e in zip(flags, expected, strict=True)), test.__name__
    upper_safe = bytes(map(str.isupper, map("A".__add__, every)))
    assert all(bool(f & T.UPPER_SAFE) == bool(e) for f, e in zip(flags, upper_safe, strict=True))
    # Classes des regex Python telles que le noyau les reproduit / Python regex classes as the core rebuilds them.
    letter = T.ALNUM | T.DECIMAL
    assert {m.start() for m in re.finditer(r"[^\W\d_]", every)} == {i for i, f in enumerate(flags)
                                                                     if f & letter == T.ALNUM}
    assert {m.start() for m in re.finditer(r"\s", every)} == {i for i, f in enumerate(flags) if f & T.SPACE}
    assert {m.start() for m in re.finditer(r"\d", every)} == {i for i, f in enumerate(flags) if f & T.DECIMAL}
    assert rules.upper(every) == every.upper()
    assert rules.fold(every) == fold(every)


def test_native_scope_keeps_no_value_in_python():
    scope = Scope()
    assert scope.native
    scope.placeholder("PERSON", "PERSON", "Jean Dupont")
    assert not hasattr(scope._native_scope, "__dict__")
    assert "Dupont" not in repr(scope._native_scope)
    for name in ("_indices", "_clusters", "_key", "_hasher"):
        assert not hasattr(scope, name)
    scope.close()
    assert scope.closed
    with pytest.raises(RuntimeError, match="scope closed"):
        scope.placeholder("EMAIL", "EMAIL", "a@b.fr")


def test_closed_scope_raises_like_python(engines):
    native, python = engines["default"]
    for engine in (native, python):
        scope = engine.new_scope()
        scope.close()
        with pytest.raises(RuntimeError, match="scope closed"):
            engine.anonymize("Écrire à a@b.fr, merci.", scope)
        assert engine.anonymize("Rien à masquer.", scope).text == "Rien à masquer."


def test_settings_native_false_is_pure_python():
    python = Anonymizer(Settings(native=False))
    assert python._finalizer is None and not python.native
    assert not python.new_scope().native


def test_truthy_explain_and_out_of_domain_settings_match_python():
    """`explain=1` reste natif ; un réglage hors domaine (substitut isolé, seuil géant) repasse à Python.

    `explain=1` stays native; a setting outside the native domain falls back to Python, same results.
    """
    text = "Écrire à Jean Dupont, 06 12 34 56 78, jean.dupont@exemple.fr."
    assert Anonymizer(explain=1)._finalizer is not None
    for overrides in ({"explain": 1}, {"explain": "oui"}, {"allow_list": ["\ud800x"]},
                      {"operators": {"\ud800": "mask"}}, {"min_score": 10**400}):
        _same_anonymization(Anonymizer(**overrides), Anonymizer(**overrides, native=False), text)
    assert Anonymizer(min_score=10**400)._finalizer is None


def test_scope_entity_with_lone_surrogate_matches_python():
    with Scope() as left, Scope(native=False) as right:
        for entity in ("EM\ud800", "PERSON", "EMAIL"):
            assert left.placeholder("EMAIL", entity, "a@b.fr") == right.placeholder("EMAIL", entity, "a@b.fr")


# --- Verrou de la portée : jamais attendu GIL tenu, jamais de Python dessous / scope lock --------------------------

# Lancé dans un processus à part, borné dans le temps : un interblocage échoue au lieu de figer la suite.
# Run in a separate process, under a timeout: a deadlock fails instead of freezing the suite.
_SCOPE_LOCK = r'''
import json, sys, threading, time
from pathlib import Path
from gdprguardian import Anonymizer, Scope

mode = sys.argv[1]
stop = threading.Event()
if mode in ("same_thread", "other_thread"):
    scope = Scope()
    assert scope.native

    class Value(str):
        def encode(self, *args, **kwargs):
            if mode == "same_thread":
                scope.closed  # la portée, depuis le même fil / the scope, from the same thread
            else:
                time.sleep(0.05)  # GIL rendu pendant qu'un autre fil l'interroge / GIL released, polled elsewhere
            return str.encode(self, *args, **kwargs)

    def poll():
        while not stop.is_set():
            scope.closed
            time.sleep(0.001)

    poller = threading.Thread(target=poll)
    poller.start()
    try:
        scope.placeholder("EMAIL", "EMAIL", Value("a\ud800b@exemple.fr"))
        outcome = "returned"
    except UnicodeEncodeError:
        outcome = "UnicodeEncodeError"
    stop.set()
    poller.join()
    print(json.dumps(outcome))
else:
    # Rendu de cellules (verrou pris sans GIL) pendant qu'un fil interroge la portée et que le fil principal compte.
    # Rendering cells (lock taken without the GIL) while a thread polls the scope and the main thread ticks.
    anonymizer = Anonymizer()
    docs = sorted(Path(sys.argv[2]).glob("*.md"))
    cells = [line for doc in docs for line in doc.read_text(encoding="utf-8").split("\n") if line] * 3
    waits, ticks = [], []
    with anonymizer.new_scope() as scope:
        def render():
            for _ in range(3):
                anonymizer.anonymize_segments(cells, scope)
            stop.set()

        def poll():
            while not stop.is_set():
                started = time.perf_counter()
                scope.closed
                waits.append((started, time.perf_counter()))
                time.sleep(0.001)

        threads = [threading.Thread(target=render), threading.Thread(target=poll)]
        for thread in threads:
            thread.start()
        while not stop.is_set():
            ticks.append(time.perf_counter())
            time.sleep(0.001)
        for thread in threads:
            thread.join()
    start, end = max(waits, key=lambda w: w[1] - w[0])
    print(json.dumps({"longest_ms": (end - start) * 1000, "ticks": sum(start < t < end for t in ticks)}))
'''


def _scope_lock(mode: str) -> Any:
    import json
    import subprocess
    import sys

    corpus = str(Path(_DOCS[0]).parent)
    done = subprocess.run([sys.executable, "-c", _SCOPE_LOCK, mode, corpus], capture_output=True, text=True,
                          timeout=180, check=False)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("mode", ["same_thread", "other_thread"])
def test_python_code_never_runs_under_the_scope_lock(mode):
    """Valeur à demi-codet isolé d'une sous-classe de `str` : son `encode` (Python) touche la portée, depuis le même
    fil ou en rendant le GIL à un autre fil qui l'interroge ; il n'est appelé qu'une fois le verrou rendu, sans
    interblocage. A lone-surrogate value of a `str` subclass: its Python `encode` touches the scope, from the same
    thread or while another thread polls it; it is called only once the lock is released, without deadlock.
    """
    assert _scope_lock(mode) == "UnicodeEncodeError"


def test_waiting_for_the_scope_lock_releases_the_gil():
    """Un fil qui interroge une portée pendant son rendu attend sans le GIL : l'interpréteur continue (le fil
    principal compte pendant l'attente). A thread polling a scope while it renders waits without the GIL: the
    interpreter goes on (the main thread ticks during the wait).
    """
    seen = _scope_lock("render")
    # Rendu d'environ 6 Mo, verrou tenu ~0,1 s : une attente est observée ; GIL tenu, aucun pas pendant elle.
    # About 6 MB rendered, lock held ~0.1 s: a wait is observed; with the GIL held, no tick during it.
    if seen["longest_ms"] > 10:
        assert seen["ticks"] >= 2, seen
