"""Moteur avec et sans Rust : zones strictement identiques / engine with and without Rust: identical spans."""

from __future__ import annotations

import random
import re
import time
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from gdprguardian import Anonymizer, _native
from gdprguardian._text import fold, normalize
from gdprguardian.engine import markdown_table_zones
from gdprguardian.packs import available_packs, load_pack

pytest.importorskip("gdprguardian_core")

_CORPUS = Path(__file__).resolve().parents[1] / "datasets" / "fr" / "docs"

_SAMPLES = [
    "NIR 1 85 05 78 006 084 91, IBAN FR76 3000 6000 0112 3456 7890 189, tél 06 12 34 56 78.",
    "Corse : 2 69 05 2A 004 123 14. DOM : +262 692 12 34 56. Carte 4111 1111 1111 1111.",
    "ACME SAS, SIREN 732 829 320, RCS Paris B 732 829 320, TVA FR44 732829320, entrepreneur individuel.",
    "Passeport n° 12AB34567, permis de conduire 123456 789012, immatriculation AB-123-CD.",
    "n° client : CLT-2024-0098, né le 3 mars 1985, date de naissance 03/03/1985.",
    "IP 192.168.1.42 et 2001:db8::1, MAC 00:1A:2B:3C:4D:5E, clé AKIAABCDEFGHIJKLMNOP.",
    "mot de passe : S3cr3t!x, bearer abcdefghijklmnopqrstuvwxyz0123456789, jean [at] mail [dot] fr",
    "Sécu 1 85 05 78 006 084 91 et numéro fiscal 12 34 567 890 123.",
    "Commande 732829320 expédiée ; référence 12AB34567 ; montant 1 234,56 €.",
    "Élève Zoé Ñúñez, téléphone 01 23 45 67 89, RIB 30006 00001 12345678901 89.",
    "Carte bancaire Diners 3056 9309 0259 04 ; plus loin, sans mot-clé, la référence 3056 9309 0259 04.",
    "Je suis né le 24 juillet 1953. Pour la réunion du 12/02/2026 ; réunion avec Jean, né le 03/03/1985.",
    # Clés fausses près d'un mot-clé, puis sans / wrong keys next to a keyword, then without.
    "N° de sécu 1 85 05 78 006 084 92, numéro fiscal 0535211664078, carte bancaire 4111 1111 1111 1112, "
    "SIRET 732 829 320 00075 ; référence 1 85 05 78 006 084 92. Né le 6 October 1950.",
    # Tableau Markdown : l'en-tête sert de contexte à sa colonne / header is context for its column.
    "| Nom | Date de naissance | Passeport | N° SIRET |\n|:---|:---:|---|---|\n"
    + "".join(f"| Agent {i} | 0{i + 1}/04/1990 | 1{i}AB34567 | 73282932000074 |\n" for i in range(6))
    + "\nHors tableau : 05/05/2005, 12AB34567.",
]

_ALPHABET = "|0123456789 .-/:@ABFRSTVWXYZabcdefnoprst°éèàç +()\n"


def _spans(anonymizer: Anonymizer, text: str) -> list[tuple]:
    return [(s.start, s.end, s.entity, s.label, s.source, s.value, round(s.score, 9), s.personal)
            for s in anonymizer.analyze(text).spans]


@pytest.fixture(scope="module")
def engines():
    native = Anonymizer(countries=("FR",))
    python = Anonymizer(countries=("FR",), native=False)
    assert native.native and not python.native
    return native, python


@pytest.mark.parametrize("text", _SAMPLES)
@pytest.mark.parametrize("profile", ["standard", "strict"])
def test_samples_identical(text, profile):
    native = Anonymizer(countries=("FR",), profile=profile)
    python = Anonymizer(countries=("FR",), profile=profile, native=False)
    assert _spans(native, text) == _spans(python, text)
    assert native.anonymize(text).text == python.anonymize(text).text


@settings(max_examples=300, deadline=None)
@given(st.lists(st.sampled_from(_SAMPLES) | st.text(alphabet=_ALPHABET, max_size=60), max_size=6))
def test_random_compositions_identical(engines, parts):
    native, python = engines
    text = " ".join(parts)
    assert _spans(native, text) == _spans(python, text)


@settings(max_examples=150, deadline=None)
@given(st.lists(st.sampled_from(_SAMPLES) | st.text(alphabet=_ALPHABET, max_size=60), max_size=4),
       st.integers(0, 400))
def test_keyword_last_end_identical(engines, parts, pos):
    native, python = engines
    folded = fold(" ".join(parts))
    left, right = native._scan_keywords(folded), python._scan_keywords(folded)
    for group in set(left.groups()) | set(right.groups()):
        for lo in (0, pos // 2):
            assert left.last_end(group, pos, lo) == right.last_end(group, pos, lo)


def test_segments_identical(engines):
    native, python = engines
    cells = ["73282932000074", "Jean", "06 12 34 56 78", "1 85 05 78 006 084 91", "x"]
    forced = [native.context_groups("N° SIRET"), frozenset(), frozenset(), frozenset(), frozenset()]
    left = [[(s.start, s.end, s.label) for s in cell] for cell in native.analyze_segments(cells, forced)[0]]
    right = [[(s.start, s.end, s.label) for s in cell] for cell in python.analyze_segments(cells, forced)[0]]
    assert left == right


@pytest.mark.parametrize("mode", ["auto", "all"])
def test_country_modes_identical(mode):
    native = Anonymizer(countries=mode)
    python = Anonymizer(countries=mode, native=False)
    for text in _SAMPLES:
        assert _spans(native, text) == _spans(python, text)


# --- Bornes : classes de caractères de Python / boundaries: Python's character classes ----------------

# Classes différentes en Rust et en Python : marques Other_Alphabetic (U+0345, U+05B0, U+093E), lettres
# cerclées (U+24B6), exposants et fractions (isdigit / isnumeric), chiffres romains, lettres hors BMP.
# Classes that differ between Rust and Python: Other_Alphabetic marks, circled letters, superscripts and
# fractions, Roman numerals, astral letters.
_BOUNDARY_CHARS = "ְͅाःⒶⓐ²½Ⅰ⁰\U0001d400\U0001d7ce\U00010400ⓐ"
_IDS = ["06 12 34 56 78", "tél 06 12 34 56 78", "IBAN FR76 3000 6000 0112 3456 7890 189",
        "SIRET 732 829 320 00074", "né le 03/03/1985", "192.168.1.42", "4111 1111 1111 1111",
        "AB-123-CD", "n° client : CLT-2024-0098", "carte bancaire 4111 1111 1111 1112"]


@pytest.mark.parametrize("ch", list(_BOUNDARY_CHARS))
@pytest.mark.parametrize("text", _IDS)
def test_boundary_characters_identical(engines, ch, text):
    native, python = engines
    for probe in (ch + text, text + ch, text.replace(" ", ch, 1), ch + text.split()[0] + " " + text):
        assert _spans(native, probe) == _spans(python, probe), ascii(probe)


_BOUNDARY_SAMPLES = _IDS + _SAMPLES


@settings(max_examples=300, deadline=None)
@given(st.lists(st.sampled_from(_BOUNDARY_SAMPLES) | st.text(alphabet=_BOUNDARY_CHARS + " -.:/0123456789",
                                                             max_size=8), max_size=8))
def test_boundary_compositions_identical(engines, parts):
    native, python = engines
    text = "".join(parts)
    assert _spans(native, text) == _spans(python, text)


# --- Classes des motifs : celles de Python / pattern classes: Python's own ---------------------------------

# Là où les tables de Rust et de Python divergent : « ² » et « Ⅻ » sont `\w` pour Python, les marques combinantes
# ne le sont pas ; `\x1c`-`\x1f` sont `\s` ; sous `re.IGNORECASE`, « İ », « ı », « ſ » et « K » égalent des lettres
# ASCII. Where Rust's and Python's tables differ: "²" and "Ⅻ" are `\w` for Python, combining marks are not;
# `\x1c`-`\x1f` are `\s`; under `re.IGNORECASE`, "İ", "ı", "ſ" and "K" equal ASCII letters.
_CLASS_TRAPS = [
    "jean [at] mail [dot] fr²", "jean² [at] mail [dot] fr", "jeán [at] máil [dot] fr",
    "jeanͅ [at] mail [dot] frⅫ", "x‿y [at] mail [dot] fr", "ｊｅａｎ [at] mail [dot] fr",
    "née\x1cle\x1d3\x1emars\x1f1985", "née le 3 mars 1985", "née\u0085le 3 mars 1985",
    "İdentifiant client : ABC-123", "ıd client : ABC-123", "numéro de dossıer : 12AB34", "N° KLIENT : X1",
    "Mot de paſſe : S3cr3t!x", "BEARER abcdefghijklmnopqrstuvwxyz0123", "RCS Paris B 732 829 320",
    "https://www.lınkedin.com/in/jean", "RCS\x1cParis\x1dB\x1e732 829 320",
]


@pytest.mark.parametrize("text", _CLASS_TRAPS)
def test_pattern_classes_follow_python(engines, text):
    """Ancien écart connu, fermé : `\\w`, `\\s`, `\\d` et `re.IGNORECASE` des motifs natifs sont ceux de Python.

    Formerly a known gap, now closed: the native patterns' classes and case folding are Python's.
    """
    native, python = engines
    for probe in (text, text + " " + text, "x" + text, text.upper(), text.lower()):
        assert _spans(native, probe) == _spans(python, probe), ascii(probe)


# --- Motifs intégrés contre `re` : chaque correspondance, à l'identique / built-in patterns against `re` -----

def _python_matches(regex: re.Pattern[str], group: int | str, text: str) -> list[tuple[int, int, str]]:
    """La boucle de recherche du moteur Python (borne « none », sans validateur) / the Python engine's loop.

    Elle s'arrête une fois la fin dépassée, comme le noyau : `re.search` ramènerait la position à la fin et
    retrouverait sans fin une correspondance vide finale. It stops once past the end, like the core: `re.search`
    would clamp the position to the end and find a final empty match forever.
    """
    found, pos = [], 0
    while pos <= len(text) and (m := regex.search(text, pos)) is not None:
        start, end = m.span(group)
        if start < 0:
            pos = m.start() + 1
            continue
        found.append((start, end, text[start:end]))
        pos = m.end() if m.end() > m.start() else m.start() + 1
    return found


def _raw_spec(regex: re.Pattern[str], group: int | str = 0) -> dict:
    """Recognizer réduit à son motif : tier A, sans borne, validateur ni contexte / reduced to its pattern."""
    return {"syntax": _native.syntax(regex), "pattern": regex.pattern, "flags": "", "group": group,
            "validator": None, "tier": "A", "boundary": "none", "prefilter": None, "score": 0.9}


def _native_matches(scanner, text: str) -> list[tuple[int, int, str]]:
    hits = scanner.keywords(text)
    args = (hits, text, text, [True] * len(scanner.supported), False, "auto", False, [])
    windowed, full = scanner.scan(*args, windows=True), scanner.scan(*args, windows=False)
    assert windowed == full, ascii(text)
    return [(start, end, value) for start, end, _, value, *_ in full]


def _builtin_recognizers() -> list:
    return [rec for pack in available_packs() for rec in load_pack(pack).recognizers]


# Pièges du balayage : séparateurs, chiffres non ASCII, marques, invisibles, CRLF, plans astraux.
# Scanning traps: separators, non-ASCII digits, marks, invisibles, CRLF, astral planes.
_PIECES = [*"0123456789 .-/:+()ABCDEFGHIJKLMNOPQRSTUVWXYZabcxyz\n\t_²½ⒶⅠ٣０𝟎éÉİıſKßẞͅ​\x1c\x1f　",
           " ", "\U0001d400", "日", "\r\n", "😀", "12", "123", "1234", "00", "B-", "CH-", "L-", "756", "04",
           "  ", "́"]


@pytest.mark.parametrize("rec", _builtin_recognizers(), ids=lambda rec: rec.id)
def test_builtin_pattern_matches_python_re(rec):
    """Chaque motif intégré compilé en natif trouve exactement ce que trouve `re`, fenêtres ou non ; ceux qui
    restent à Python disent pourquoi. Each built-in pattern compiled natively finds exactly what `re` finds,
    windows or not; those left to Python say why."""
    scanner = _native._core.Scanner([_raw_spec(rec.regex, rec.group)], [], _native.unicode_tables())
    if not scanner.supported[0]:
        assert rec.id == "NL_POSTCODE_LABELED" and "look-behind" in scanner.errors[0]
        return
    rng = random.Random(rec.id)
    literal = [c for c in rec.regex.pattern if c.isalnum() or c in " .-/:+()"]
    pieces = _PIECES + literal
    for _ in range(150):
        text = "".join(rng.choice(pieces) for _ in range(rng.choice([0, 1, 3, 8, 20, 60])))
        assert _native_matches(scanner, text) == _python_matches(rec.regex, rec.group, text), ascii(text)


# Formes de look-around des packs, en généré : premier caractère et look-behind (macro LB), caractère facultatif
# avant lui, alternatives de tête, look-ahead final simple, double, imbriqué, positif borné.
# The packs' look-around shapes, generated: first character then look-behind (LB macro), optional character
# before it, leading alternatives, simple, double, nested and bounded positive final look-aheads.
_LOOK_SHAPES = [
    r"[A-Z](?<![0-9A-Za-z]{2})[A-Z]{1,2}[0-9]{2}(?![0-9A-Za-z])",
    r"\(?0(?<![0-9A-Za-z\+]0)[1-9][0-9](?:\)?(?: ?/ ?|[ \-]{1,3})?[0-9]){2,4}(?![0-9A-Za-z])",
    r"(?:[A-Z](?<![0-9A-Za-z]{2})[A-Z][0-9]{3}|U(?<![0-9A-Za-z]{2})1[A-Z0-9]{3})[A-Z](?![0-9A-Za-z])",
    r"[6-9](?<![0-9A-Za-z\+][0-9])[0-9](?:[ \-]?[0-9]){3}(?![0-9A-Za-z])",
    r"B-[1-9][0-9]{2}(?=\s{1,3}[A-ZÀ-Ý])",
    r"[1-9]-[A-Z]{2}-[0-9]{2}(?![^\W_])",
    r"(?:A[GIR]|B[ELS]|FR) ?[1-9][0-9]{0,2}(?: ?[0-9]{3})?(?![^\W_])(?! ?[0-9]{3}(?![0-9]))",
    r"(?:18|19|20)[0-9]{2}[ .\-]?[0-9]{2}(?![ .\-]?[0-9])(?![^\W_])",
    r"(?P<v>[0-9]{2} ?P ?[0-9]{2})(?![^\W_])",
    r"\b[0-9]{3,5}\b",
    r"\bCLT-\d+\b",
    r"\B[0-9]{2}",
    r"[a-z]+\B",
    r"(?<!\d)[0-9]{4}(?!\d)",
    r"(?<=°)[0-9]{3}",
    r"n°(?<=n°)[0-9]{3}",
    r"(?<=\s)x[0-9]",
    r"[0-9]{2}$",
    r"(?i)client\s?[0-9]{2}$",
    r"(?m)^[0-9]{2}$",
    r"(?s)A.{0,3}B\Z",
]
_LOOK_PIECES = [*"0123456789 -/()+.AUBELSFRPZÀxn°\n\t", "n°", "B-", "AG", "BE", "FR", "CLT-", "Ü", "²", "\x1c",
                "client", "CLIENT", "\r\n", "İ"]


@pytest.mark.parametrize("pattern", _LOOK_SHAPES)
@settings(max_examples=250, deadline=None)
@given(st.lists(st.sampled_from(_LOOK_PIECES), max_size=40))
def test_lookaround_shapes_match_python_re(pattern, parts):
    regex = re.compile(pattern)
    group = "v" if "(?P<v>" in pattern else 0
    scanner = _look_scanner(pattern, group)
    assert scanner.supported[0], scanner.errors[0]
    text = "".join(parts)
    assert _native_matches(scanner, text) == _python_matches(regex, group, text), ascii(text)


_SCANNERS: dict[str, object] = {}


def _look_scanner(pattern: str, group: int | str):
    if pattern not in _SCANNERS:
        _SCANNERS[pattern] = _native._core.Scanner([_raw_spec(re.compile(pattern), group)], [],
                                                    _native.unicode_tables())
    return _SCANNERS[pattern]


@pytest.mark.parametrize(("pattern", "reason"), [
    (r"(?<=n°)[0-9]{3}", "look-behind"),          # deux caractères avant la correspondance / two characters before
    (r"[a-z]+(?<!x)[0-9]", "look-behind"),        # après une répétition / after a repetition
    (r"a(?=b)c", "look-ahead"),                   # au milieu / in the middle
    (r"(?:a(?!b)|c)d", "look-ahead"),
    (r"[\w-]\b", "\\b"),                          # classe mixte / mixed class
    (r"a$b", "$"),
    (r"(a)\1", "GROUPREF"),
    (r"(?>ab)c", "ATOMIC_GROUP"),
    (r"a*+b", "POSSESSIVE_REPEAT"),
    (r"(?a)\w+", "re.ASCII"),
    (r"(?:a?)*b", "vide"),                        # répétition d'un motif vide / repeated empty sub-pattern
])
def test_unsupported_constructs_are_refused_with_a_reason(pattern, reason):
    scanner = _native._core.Scanner([_raw_spec(re.compile(pattern))], [], _native.unicode_tables())
    assert not scanner.supported[0] and reason in scanner.errors[0], scanner.errors[0]


@pytest.mark.parametrize(("pattern", "reason"), [
    # Chaque caractère facultatif avant une assertion doublait les chemins / each optional character doubled paths.
    ("a?" * 18 + r"(?<!x)b", "optional"),
    # Complément exponentiel en profondeur des séquences interdites / exponential complement of forbidden sequences.
    ("x(?!" + "|".join(["[ab]{16}", *(f"[ab]{{{k}}}ac" for k in range(16))]) + ")", "too large"),
])
def test_hostile_assertions_are_refused_quickly(pattern, reason):
    """Motif court et hostile (règle personnalisée non sûre) : refusé vite, mémoire bornée ; autrefois des secondes à
    des heures de compilation. Short hostile pattern (untrusted custom rule): refused quickly, bounded memory;
    formerly seconds to hours of compilation."""
    t0 = time.perf_counter()
    scanner = _native._core.Scanner([_raw_spec(re.compile(pattern))], [], _native.unicode_tables())
    assert time.perf_counter() - t0 < 5
    assert not scanner.supported[0] and reason in scanner.errors[0], scanner.errors[0]


def test_lookaround_recognizers_run_natively():
    """Les recognizers à look-around autrefois refusés sont natifs ; aucun n'est refusé pour son motif.

    The look-around recognizers once refused are native; none is refused for its pattern.
    """
    scanner = Anonymizer(countries="all")._native
    by_id = {r.id: (ok, error) for r, ok, error in zip(scanner.recognizers, scanner.flags, scanner.errors,
                                                        strict=True)}
    for rid in ("BE_PLATE", "BE_POSTCODE", "CH_AVS_OLD", "CH_PLATE", "CH_POSTCODE", "ES_PASSPORT", "IT_ID_CARD",
                "IT_PASSPORT", "IT_DRIVER_LICENSE", "LU_POSTCODE", "NL_DRIVER_LICENSE", "PT_PASSPORT",
                "PT_POSTAL_CODE"):
        assert by_id[rid] == (True, None), rid
    # Seul refus de motif : le look-behind après une répétition paresseuse de NL_POSTCODE_LABELED.
    # Only pattern refusal: NL_POSTCODE_LABELED's look-behind after a lazy repetition.
    refused = {rid: error for rid, (ok, error) in by_id.items() if not ok and "validat" not in error}
    assert set(refused) <= {"NL_POSTCODE_LABELED"}, refused


# --- Fenêtres de recherche : identiques au balayage complet / search windows: same as the full scan ----

def _scan_both(anonymizer: Anonymizer, text: str, strict: bool, segments=None) -> tuple[list, list]:
    """Balayage Rust avec et sans fenêtres, comme le moteur l'appelle / Rust scan with and without windows."""
    native = anonymizer._native
    norm = normalize(text)[0]
    folded = fold(norm)
    hits = native.keywords(folded)
    zones = [(start, end, sorted(groups)) for start, end, groups in markdown_table_zones(norm,
                                                                                          anonymizer.context_groups)]
    active = list(native.flags)
    args = (hits, norm, folded, active, strict, "auto", strict, list(anonymizer._ei_groups), segments, None, zones)
    return native._scanner.scan(*args, windows=True), native._scanner.scan(*args, windows=False)


@pytest.fixture(scope="module", params=["FR", "all"])
def scan_engine(request):
    return Anonymizer(countries=request.param if request.param == "all" else ("FR",))


@pytest.mark.skipif(not _CORPUS.exists(), reason="corpus absent")
def test_windows_identical_on_corpus(scan_engine):
    docs = sorted(_CORPUS.glob("*.md"))
    assert docs
    found = 0
    for path in docs:
        text = path.read_text(encoding="utf-8")
        for strict in (False, True):
            windowed, full = _scan_both(scan_engine, text, strict)
            assert windowed == full, path.name
            found += len(full)
    assert found > len(docs)  # le test porte sur de vraies détections / real detections are compared


# Entrées adverses : longues suites de chiffres et de séparateurs, chiffres non ASCII, marques, hors BMP.
# Adversarial inputs: long digit and separator runs, non-ASCII digits, marks, astral characters.
_ADVERSARIAL = ("0123456789 .-/:+()ABabFR°\n\t" + _BOUNDARY_CHARS + "٣۵０𝟎éÉ​ [at](dot)"
                "xoxp-sk-ghp_eyJAKIA")


@settings(max_examples=400, deadline=None)
@given(st.lists(st.sampled_from(_SAMPLES + _IDS) | st.text(alphabet=_ADVERSARIAL, max_size=120)
                | st.text(max_size=20), max_size=8),
       st.booleans())
@example(["1" * 5000], False)
@example(["1 " * 2000, "06 12 34 56 78"], True)
@example(["IBAN FR76 3000 6000 0112 3456 7890 189" * 50], False)
def test_windows_identical_adversarial(scan_engine, parts, strict):
    text = "".join(parts)
    windowed, full = _scan_both(scan_engine, text, strict)
    assert windowed == full


# Motifs aléatoires en syntaxe de Python : littéraux piégeux (casse turque, s long, signe kelvin, astraux), classes
# `\w` `\d` `\s` et leurs négations, ensembles, assertions, look-arounds de tête, de fin et ailleurs (refusés).
# Random patterns in Python syntax: tricky literals, Perl classes and negations, sets, assertions, look-arounds at
# the start, at the end and elsewhere (refused).
_LITERALS = [*"abxyzABXZ0129 -._@:/,", "é", "É", "ß", "ſ", "k", "K", "K", "𝐚", "٣", "²", "ͅ", "€", "ı", "İ"]
_CLASSES = [r"[a-z]", r"[0-9]", r"[^0-9 ]", r"[a-zé]", r"[\-.]", r"\d", r"\D", r"\w", r"\W", r"\s", r"\S", ".",
            r"[^\n]", r"[𝐚-𝐳]", r"[A-Z0-9]", r"[^\W\d_]", r"[\w.%+-]", r"[^\s]", r"[iI]", r"[\sx]", r"[^\Wa]"]
_LOOKS = [r"\b", r"\B", "^", "$", r"\A", r"\Z"]
_AROUND = [r"(?<![0-9A-Za-z])", r"(?<=[a-z])", r"(?<!\w)", r"(?![0-9A-Za-z])", r"(?=\s)", r"(?![^\W_])",
           r"(?!\d{2})", r"(?! ?[0-9](?![0-9]))", r"(?<=x\d)"]
_QUANTIFIERS = ["*", "+", "?", "{0,2}", "{1,3}", "{2}", "{2,}", "*?", "+?", "??", "{1,3}?", "{,2}"]
_GROUPS = ["(", "(?:", "(?i:", "(?s:", "(?m:", "(?-i:", "(?x:"]


_UNBOUNDED = ("*", "+", "{2,}", "*?", "+?")


def _random_pattern(rng: random.Random, depth: int = 0, budget: list[int] | None = None) -> str:
    """Motif aléatoire : littéraux, classes, assertions, look-arounds, groupes, quantificateurs, alternatives.

    Random pattern: literals, classes, assertions, look-arounds, groups, quantifiers, alternations. La référence
    `re` revient en arrière : groupes à quantificateurs bornés et deux quantificateurs non bornés au plus, pour
    qu'elle reste rapide. The `re` reference backtracks: bounded quantifiers on groups and at most two unbounded
    quantifiers, so that it stays fast.
    """
    budget = [2] if budget is None else budget

    def atom() -> tuple[str, bool]:
        r = rng.random()
        if depth > 2 or r < 0.35:
            c = rng.choice(_LITERALS)
            return ("\\" + c if c in ".^$*+?()[]{}|\\-" else c), False
        if r < 0.6:
            return rng.choice(_CLASSES), False
        if r < 0.75:
            return rng.choice(_LOOKS + _AROUND), False
        return rng.choice(_GROUPS) + _random_pattern(rng, depth + 1, budget) + ")", True

    def piece() -> str:
        a, group = atom()
        if a in _LOOKS + _AROUND or rng.random() >= 0.35:
            return a
        quantifier = rng.choice(["?", "{0,2}", "{1,2}", "??"] if group else _QUANTIFIERS)
        if quantifier in _UNBOUNDED:
            if budget[0] > 0:
                budget[0] -= 1
            else:
                quantifier = "?"
        return a + quantifier

    branches = 1 if rng.random() < 0.7 else rng.randint(2, 3)
    return "|".join("".join(piece() for _ in range(rng.randint(1, 5))) for _ in range(branches))


@pytest.mark.skipif(not _native.available(), reason="noyau Rust désactivé / Rust core disabled")
@settings(max_examples=150, deadline=None)
@given(st.integers(0, 2**32))
def test_random_patterns_match_python_re(seed):
    """Tout motif (règles personnalisées comprises) : refusé avec une raison, ou mêmes correspondances que `re`,
    avec ou sans fenêtres. 20 motifs aléatoires, 20 textes chacun. Any pattern (custom rules included): refused
    with a reason, or the same matches as `re`, with or without windows. 20 random patterns, 20 texts each.
    """
    rng = random.Random(seed)
    alphabet = [*_LITERALS, "\n", "\r", "\t", " ", "1", "2", "a", "b", "-", ".", "​", "Ⅰ", "½", "AB-12",
                "\x1c", "́", "x1"]
    for _ in range(20):
        pattern = _random_pattern(rng)
        flags = sum(flag for flag in (re.IGNORECASE, re.MULTILINE, re.DOTALL) if rng.random() < 0.25)
        try:
            regex = re.compile(pattern, flags)
        except (re.error, OverflowError):
            continue
        scanner = _native._core.Scanner([_raw_spec(regex)], [], _native.unicode_tables())
        if not scanner.supported[0]:
            assert scanner.errors[0], pattern
            continue
        for _ in range(20):
            text = "".join(rng.choice(alphabet) for _ in range(rng.choice([0, 1, 5, 20, 60])))
            assert _native_matches(scanner, text) == _python_matches(regex, 0, text), (pattern, ascii(text))


@pytest.mark.skipif(not _native.available(), reason="noyau Rust désactivé / Rust core disabled")
@settings(max_examples=60, deadline=None)
@given(st.integers(0, 2**32))
def test_windows_identical_random_patterns(seed):
    """Fenêtres sûres pour tout motif accepté, toutes bornes : 30 motifs aléatoires, 20 textes.

    Windows are safe for any accepted pattern, every boundary: 30 random patterns, 20 texts each.
    """
    rng = random.Random(seed)
    specs = []
    for _ in range(30):
        try:
            regex = re.compile(_random_pattern(rng), re.IGNORECASE if rng.random() < 0.2 else 0)
        except (re.error, OverflowError):
            continue
        specs.append({**_raw_spec(regex), "boundary": rng.choice(["none", "alnum", "word", "ip", "hex", "phone",
                                                                  "digit"])})
    scanner = _native._core.Scanner(specs, [("g", ["ab"])], _native.unicode_tables())
    alphabet = [*_LITERALS, "\n", "\r", "\t", " ", "1", "2", "a", "b", "-", ".", "​", "Ⅰ", "½", "AB-12"]
    for _ in range(20):
        text = "".join(rng.choice(alphabet) for _ in range(rng.choice([0, 1, 5, 40, 200])))
        args = (scanner.keywords(text.lower()), text, text.lower(), [True] * len(specs), False, "auto", False, [])
        assert scanner.scan(*args, windows=True) == scanner.scan(*args, windows=False), ascii(text)


# --- Règles personnalisées : même compilateur, même sémantique / custom rules: same compiler, same semantics ---

_RULES = {"rules": [
    {"label": "CLIENT", "pattern": r"\bCLT-\d{4,6}\b", "whole_word": False},
    {"label": "DOSSIER", "pattern": r"(?<![A-Z])DOS[0-9]{3}(?![0-9])"},
    {"label": "FIN", "pattern": r"ref [a-z]{2}\d$", "case_sensitive": True},
    {"label": "IDENT", "pattern": r"identifiant ?: ?(?P<v>[A-Z0-9]{4})"},
]}


@pytest.mark.parametrize("text", [
    "client CLT-12345, CLT-123, xCLT-12345, CLT-1234567 ; dossier DOS123 ADOS123 dos1234",
    "İDENTIFIANT : AB12, ıdentifiant: CD34\nref ab1\n", "ref ab1\n\n", "réf ab1", "ref AB1",
    "CLT-²²²² CLT-1234² CLT-1234́ DOS123²", "",
])
def test_custom_rules_with_assertions_match_python(text):
    from gdprguardian.custom import parse_rules

    native = Anonymizer(countries=("FR",), rules=parse_rules(_RULES, trusted=False))
    python = Anonymizer(countries=("FR",), rules=parse_rules(_RULES, trusted=True), native=False)
    assert native._custom_native is not None and all(native._custom_native.flags)
    assert _spans(native, text) == _spans(python, text)


def test_windows_identical_with_segments(scan_engine):
    cells = ["73282932000074", "Jean", "06 12 34 56 78", "1 85 05 78 006 084 91", "x", "4111 1111 1111 1111"]
    text = "\n\n".join(cells)
    segments, cursor = [], 0
    for cell in cells:
        segments.append((cursor, cursor + len(cell)))
        cursor += len(cell) + 2
    windowed, full = _scan_both(scan_engine, text, False, segments)
    assert windowed == full and full


# --- Formes finales exactes, refus précis / exact trailing forms, precise refusals ---------------------------------

# `$` en dernière position d'un look-ahead positif final ou d'une alternative finale, `(?=$)`, `(?=\b)`, et leurs
# voisins : look-ahead dans une branche, alternative imbriquée, filtre de tête, groupe nommé, MULTILINE.
# `$` last in a final positive look-ahead or a final alternation, `(?=$)`, `(?=\b)`, and their neighbours.
_TRAILING_SHAPES = [
    r"XY[0-9]{3}(?=\s|$)",
    r"XY[0-9]{3}(?=$)",
    r"XY[0-9]{3}(?:$|\s)",
    r"XY[0-9]{3}(?:\s|$)",
    r"XY[0-9]{3}(?=[.,;]|$)",
    r"XY[0-9]{3}(?=\b)",
    r"[a-z]+(?=\B)",
    r"[0-9]{2}(?:[.,]|$|\s\s)",
    r"a|b$|c(?=d)",
    r"\d+(?:$|(?=x)|y)",
    r"[A-Z]{2}(?:\d(?:$|\.)|-)",
    r"x(?!$)",
    r"x(?!\n$)",
    r"x(?!\s|$)",
    r"(?<!\w)[0-9]{3}(?=\s|$)",
    r"\b[0-9]{3}(?:$|\s)",
    r"(?P<v>[0-9]{3})(?:$|-)",
    r"(?i)client\s?(?:[0-9]{2}$|-)",
    r"(?m)[0-9]{2}(?:$|;)",
    r"\d\d?(?:\s*$|,)",
]
_TRAILING_PIECES = [*"0123456789 -.,;xyabcdXYz\n\t", "XY", "\n\n", "client", "CLIENT", "İ", "\r\n", "²", "ab"]


@pytest.mark.parametrize("pattern", _TRAILING_SHAPES)
@settings(max_examples=200, deadline=None)
@given(st.lists(st.sampled_from(_TRAILING_PIECES), max_size=30))
def test_trailing_forms_match_python_re(pattern, parts):
    """Formes finales documentées : acceptées, et exactement les correspondances de `re`, fenêtres ou non.

    Documented trailing forms: accepted, with exactly `re`'s matches, windows or not.
    """
    regex = re.compile(pattern)
    group = "v" if "(?P<v>" in pattern else 0
    scanner = _look_scanner(pattern, group)
    assert scanner.supported[0], scanner.errors[0]
    text = "".join(parts)
    assert _native_matches(scanner, text) == _python_matches(regex, group, text), ascii(text)


@pytest.mark.parametrize(("pattern", "reason"), [
    (r"x(?!$\n)", "$"),            # le `$` développé consommait le « \n » / the expanded `$` consumed the "\n"
    (r"x(?!$\s)", "$"),
    (r"x(?!(?:$)\n)", "$"),
    (r"x(?=$\n)", "$"),
    (r"x(?:$a|b)", "$"),
    (r"(?:x|$)y", "$"),            # alternative non finale / not a final alternation
    (r"(x|$)", "$"),               # groupe capturant : le suffixe s'y mêlerait / capturing group
    (r"x(?=(?:a(?=b))c)", "look-ahead"),
    (r"x(?!(?:a(?=b))c)", "élémentaire"),
    (r"x(?!(?:a(?!b)){2})", "élémentaire"),
    (r"x\b(?=\s)", "combin"),
])
def test_trailing_forms_outside_the_exact_ones_are_refused(pattern, reason):
    """Hors des formes exactes : refus avec la raison, jamais un résultat différent de `re`.

    Outside the exact forms: refused with the reason, never a result different from `re`.
    """
    scanner = _native._core.Scanner([_raw_spec(re.compile(pattern))], [], _native.unicode_tables())
    assert not scanner.supported[0] and reason in scanner.errors[0], scanner.errors[0]


def test_dollar_inside_a_negative_look_ahead_now_matches_python():
    """Revue de parité n°3 : `(?!$\\n)` donnait un autre résultat que `re` ; refusé, la référence Python sert.

    Parity review #3: `(?!$\\n)` gave a different result from `re`; refused, the Python reference serves.
    """
    from gdprguardian.custom import RuleError, parse_rules

    data = {"rules": [{"label": "X", "pattern": r"XY[0-9]{3}(?!$\n)", "whole_word": False}]}
    trusted = Anonymizer(countries=("FR",), rules=parse_rules(data))
    python = Anonymizer(countries=("FR",), rules=parse_rules(data), native=False)
    for text in ("id XY123\n", "id XY123\n\n", "id XY123", "XY123 XY456\n"):
        assert trusted.anonymize(text).text == python.anonymize(text).text, ascii(text)
    assert trusted.anonymize("id XY123\n").text == "id XY123\n"
    with pytest.raises(RuleError, match=r"\$"):
        Anonymizer(countries=("FR",), rules=parse_rules(data, trusted=False))


# Fins de motif aléatoires : look-ahead positif ou négatif, alternative finale (capturante ou non), contenus
# mêlant `$`, `\Z`, `\b`, classes et assertions imbriquées. Random pattern ends: positive or negative look-ahead,
# final alternation (capturing or not), contents mixing `$`, `\Z`, `\b`, classes and nested assertions.
_TAIL_ITEMS = ["$", r"\Z", r"\s", r"[.,;]", "x", r"\d", r"\b", r"\B", r"(?=x)", r"(?!\d)", r"\n", "", r"\w", "-",
               r"$\n", r"$\s", r"\n$"]


def _random_tail(rng: random.Random, depth: int = 0) -> str:
    def alternative() -> str:
        items = [rng.choice(_TAIL_ITEMS) for _ in range(rng.randint(1, 2))]
        if depth == 0 and rng.random() < 0.25:
            items.append(_random_tail(rng, depth + 1))
        return "".join(items)

    body = "|".join(alternative() for _ in range(rng.randint(1, 3)))
    return rng.choice(["(?={})", "(?!{})", "(?:{})", "({})", "{}"]).format(body)


@pytest.mark.skipif(not _native.available(), reason="noyau Rust désactivé / Rust core disabled")
@settings(max_examples=120, deadline=None)
@given(st.integers(0, 2**32))
def test_random_trailing_forms_match_python_re(seed):
    """Motif aléatoire suivi d'une fin aléatoire : refusé avec une raison, ou les correspondances de `re`.

    Random pattern followed by a random end: refused with a reason, or `re`'s matches. 20 motifs, 20 textes.
    """
    rng = random.Random(seed)
    alphabet = [*"xab12-.,;", "\n", "\n", " ", "\t", "XY", "x\n", "1\n", "İ", "ſ", "²", "\r\n"]
    for _ in range(20):
        pattern = _random_pattern(rng) + _random_tail(rng)
        flags = sum(flag for flag in (re.IGNORECASE, re.MULTILINE) if rng.random() < 0.25)
        try:
            regex = re.compile(pattern, flags)
        except (re.error, OverflowError):
            continue
        scanner = _native._core.Scanner([_raw_spec(regex)], [], _native.unicode_tables())
        if not scanner.supported[0]:
            assert scanner.errors[0], pattern
            continue
        for _ in range(20):
            text = "".join(rng.choice(alphabet) for _ in range(rng.choice([0, 1, 4, 12, 40])))
            assert _native_matches(scanner, text) == _python_matches(regex, 0, text), (pattern, ascii(text))


# --- Ensembles insensibles à la casse : résolution rapide et exacte / case-insensitive sets: fast and exact -------

def _cased_reference(negate: bool, items: list[tuple]) -> list[int]:
    """Résolution d'origine : `re` sur l'ensemble tel qu'écrit, 65 536 pas par intervalle (exacte, lente).

    The original resolution: `re` on the set as written, 65,536 steps per range (exact, slow).
    """
    from re import _compiler

    def escape(cp: int) -> str:
        return f"\\U{cp:08x}"

    parts = [escape(item[1]) if item[0] == "lit" else f"{escape(item[1])}-{escape(item[2])}" if item[0] == "range"
             else _native._ESCAPES[item[1]] for item in items]
    text = "[" + "^" * negate + "".join(parts) + "]"
    return sorted(map(ord, _compiler.compile(text, re.IGNORECASE).findall(_native._ignorecase_candidates())))


# Bornes piégeuses : İ ı ſ K Ω ŉ ʼ ß ẞ, U+FFFF/U+10000, Deseret, Adlam, fin d'Unicode / tricky bounds.
_CASED_POINTS = [0, 0x40, 0x41, 0x5A, 0x61, 0x7F, 0xB5, 0xDF, 0xFF, 0x130, 0x131, 0x149, 0x17F, 0x1C5, 0x2BC,
                 0x345, 0x390, 0x3C2, 0x1E9E, 0x212A, 0x2126, 0xFB05, 0xFFFF, 0x10000, 0x10400, 0x10427, 0x10428,
                 0x1E900, 0x1E943, 0x10FFFF]


def test_cased_sets_resolve_exactly_as_before():
    """Version rapide (candidats de chaque intervalle, règle RANGE_UNI_IGNORE de `re` au-delà du BMP) : mêmes
    points que la résolution d'origine, sur des cas fixes et aléatoires. Fast version: the same points as the
    original resolution, on fixed and random cases."""
    from gdprguardian import _text

    candidates = _text.ignorecase_data()["candidates"]
    points = sorted(set(candidates[::9]) | set(_CASED_POINTS))
    rng = random.Random(2512)
    cases = [(False, [("range", 0, 0xFFFF)]), (True, [("range", 0, 0x10FFFF)]), (False, [("range", 380, 125195)]),
             (False, [("range", 0x49, 0x49), ("range", 0x10000, 0x10001)]), (False, [("range", 0x10400, 0x1E943)]),
             (True, [("range", 0x41, 0x5A), ("cat", "digit")]), (False, [("range", 0xD800, 0xDFFF)]),
             (False, [("range", 0x2BC, 0x2BC)]), (False, [("range", 0x2BC, 0x10000)]), (True, [("cat", "word")]),
             (False, [("lit", 0x10400), ("lit", 0x149)]), (True, [("range", 0x10000, 0x10001)]),
             (False, [("range", 0x100, 0x17F)])]
    for _ in range(160):
        items: list[tuple] = []
        for _ in range(rng.randint(1, 3)):
            kind = rng.random()
            if kind < 0.3:
                items.append(("lit", rng.choice(points)))
            elif kind < 0.9:
                low = rng.randrange(len(points))
                high = min(len(points) - 1, low + rng.choice([0, 1, 3, 12, 60, len(points)]))
                items.append(("range", points[low], points[high]))
            else:
                items.append(("cat", rng.choice(list(_native._ESCAPES))))
        cases.append((rng.random() < 0.3, items))
    for negate, items in cases:
        assert _native._cased_matches(negate, items, {}) == _cased_reference(negate, items), (negate, items)


def test_wide_cased_sets_resolve_quickly():
    """165 intervalles larges : quelques ms, contre plus d'une seconde (relu à chaque règle personnalisée).

    165 wide ranges: a few ms, against over a second (re-read for every custom rule).
    """
    for top in (0xFFFF, 0x10FFFF):
        items = [("range", 0, top - k) for k in range(165)]
        started = time.perf_counter()
        _native._cased_matches(False, items, {})
        assert time.perf_counter() - started < 0.5
