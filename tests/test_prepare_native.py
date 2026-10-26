"""Préparation du texte en Rust : résultats identiques à la référence Python.

Rust text preparation: results identical to the Python reference (normalize, fold, offsets, language),
on the corpus and under adversarial Unicode (astral planes, combining marks, every invisible range,
hyphen breaks, emphasis runs, CRLF).
"""

from __future__ import annotations

import re
from array import array
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from gdprguardian import _native
from gdprguardian._text import (
    ALNUM,
    INVISIBLE,
    INVISIBLE_RE,
    LETTER,
    char_flags,
    code_points,
    fold,
    normalize,
    prepare,
)
from gdprguardian.locale import _STOPWORDS, _native_detector, detect_language

pytest.importorskip("gdprguardian_core")
# Sans noyau actif, `native=True` retomberait sur Python et ces tests ne prouveraient rien.
# Without an active core, `native=True` would fall back to Python and these tests would prove nothing.
pytestmark = pytest.mark.skipif(not _native.available(), reason="noyau Rust désactivé / Rust core disabled")

_CORPUS = Path(__file__).resolve().parents[1] / "datasets" / "fr" / "docs"

# Un représentant de chaque plage invisible, ses bornes comprises / every invisible range, bounds included.
_INVISIBLE = "".join(
    chr(cp) for cp in (
        0x00AD, 0x034F, 0x061C, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x180B, 0x180F, 0x200B, 0x200F, 0x202A,
        0x202E, 0x2060, 0x2064, 0x2066, 0x206F, 0x3164, 0xFE00, 0xFE0F, 0xFEFF, 0xFFA0, 0x1BCA0, 0x1BCA3,
        0xE0000, 0xE0041, 0xE0FFF,
    )
)
# Caractères piégeux : marques combinantes (dont Other_Alphabetic), chiffres non ASCII et hors BMP, lettres
# hors BMP, pleine chasse (« ＊＊ » devient « ** »), espaces Unicode, casse turque, emoji, ligatures.
# Tricky characters: combining marks, non-ASCII and astral digits, astral letters, fullwidth forms, Unicode
# spaces, Turkish casing, emoji, ligatures.
_TRICKY = (
    "ְ́ͅःा⃝ⒶⅠ²½٣۵１\U0001d7ce\U0001d7f6"
    "\U0001d400\U0001d41a\U00010400\U00010428\U0002070e\U0001f600＊＿－  　"
    " ’İıſKẞßŒœǅ‐−﹣"
)
_SPECIAL = "*_-\n\r\t  aZéÉ1" + _INVISIBLE + _TRICKY


def test_native_objects_are_used():
    assert _native.preparer() is not None and _native_detector() is not None


def _python(text: str) -> tuple[str, str, array | None]:
    norm, offsets = normalize(text)
    return norm, fold(norm), offsets


def _check(text: str) -> None:
    norm, folded, offsets = prepare(text, native=True)
    expected = _python(text)
    assert (norm, folded) == expected[:2]
    assert type(offsets) is type(expected[2])
    if offsets is not None:
        assert offsets.typecode == "q" and offsets == expected[2]
    assert prepare(text) == expected  # voie Python par défaut / Python path by default


def test_flags_table_matches_char_flags_and_regex_classes():
    """La table partagée = `char_flags` = classes des motifs, sur les points du BMP (hors substituts).

    The shared table equals `char_flags` and the patterns' classes, on the BMP points (surrogates aside).
    """
    chars = code_points(0, 0x10000)
    chars = chars[:0xD800] + chars[0xE000:]
    table = _native.unicode_tables().flags_of(chars)
    alnum, letter = re.compile(r"[^\W_]"), re.compile(r"[^\W\d_]")
    for ch, flags in zip(chars, table, strict=True):
        assert flags == char_flags(ch), hex(ord(ch))
        assert bool(flags & ALNUM) == (alnum.match(ch) is not None), hex(ord(ch))
        assert bool(flags & LETTER) == (letter.match(ch) is not None), hex(ord(ch))
        assert bool(flags & INVISIBLE) == (INVISIBLE_RE.match(ch) is not None), hex(ord(ch))


@pytest.mark.parametrize("ch", list(_TRICKY + _INVISIBLE[-5:]))
def test_rust_reads_python_flags(ch):
    """Rust lit les drapeaux de Python, y compris hors BMP / Rust reads Python's flags, beyond the BMP too."""
    assert _native.unicode_tables().flags(ch) == char_flags(ch)


def test_rust_reads_every_plane():
    """Un caractère de chaque plan, dont les plans vides 4 à 13 / one character per plane, empty ones too."""
    tables = _native.unicode_tables()
    for plane in range(17):
        for low in (0x0000, 0x0041, 0x0345, 0xD400, 0xFFFD, 0xFFFF):
            cp = plane << 16 | low
            if not 0xD800 <= cp <= 0xDFFF:
                assert tables.flags(chr(cp)) == char_flags(chr(cp)), hex(cp)
    text = "".join(chr(plane << 16 | 0x0041) + "-\n" + chr(plane << 16 | 0xD41A) + " **x** " for plane in range(17))
    _check(text)


def test_astral_table_applies_after_dense_table():
    """Comme Python, une cible hors BMP de la table dense passe par la table hors BMP, une seule fois.

    As in Python, an astral target of the dense table goes through the astral table, exactly once.
    """
    dense = [chr(cp) for cp in range(0x10000)]
    dense[0xE9] = "\U0001d400"  # é -> 𝐀
    dense = "".join(dense)
    astral = {0x1D400: ord("Z"), 0x1D41A: 0x1D400}  # 𝐀 -> Z ; 𝐚 -> 𝐀 (pas de second passage / no second pass)
    preparer = _native._core.Preparer(_native.unicode_tables(), dense.encode("utf-32-le", "surrogatepass"),
                                      list(astral.items()))
    for text in ("é", "aé\U0001d41a\U0001d400 é", "\U0001d41a", "plain"):
        expected = text if text.isascii() else text.translate(dense).translate(astral)
        assert preparer.normalize(text)[0] == expected, ascii(text)


@pytest.mark.skipif(not _CORPUS.exists(), reason="corpus absent")
def test_corpus_identical():
    docs = sorted(_CORPUS.glob("*.md"))
    assert docs
    for path in docs:
        _check(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("text", [
    "",
    "plain ascii text, no change",
    "**N° client :** 12345, __Jean__ et snake__case, mot**gras**fin",
    "*" * 7 + "x" + "_" * 5 + "é**é" + "ְ**ְ" + "1**²" + "\U0001d400**\U0001d400",
    "＊＊gras＊＊ et ＿＿souligné＿＿, Ｄu－\npont",
    "M. Du-\npont et Jean-\n  Pierre Martin, 12-\n14 rue, Du-\r\npont, Du- \t\n\t pont, Du-   \npont",
    "Du-\n   pont, Du-\r\rpont, Du-\r pont, é-\nÉ, ß-\nx, \U0001d41a-\n\U0001d41a, ²-\nb, a-\n²",
    "NIR 1 85ㅤ 05 78 006͏ 084️ 91",
    "a­-\nb, a-\n­b, a-​\nb",
    "CRLF\r\nline\r\n**bold**\r\n",
    # Règle GAP / GAP rule
    "Tél.\t06\t12  34 \t56\r\n78, NIR 1 85 05 78 006\n084 91, é\t1, 1\té, a\t\tb, 1\t\t\t\t\t2, 1 \t \t2",
    "IDFRADUPONT<<<<<<<<<<<<<<<<<<<123456\n1234567890123JEAN<<<<<<<<8001019M5\n123456789012\n345678901234",
    "1\n2\n3, 12\n\n34, 12\r\r\n34, 12\t\r 34, 12   \r\n   34, 12    \n34, \t1\t2\t, 9​\t8, 1-\n2",
    "Du-\npont 1\n2 **x**\t3 ab­\t4",
    # Groupes séparés par « / » ou « . » / groups split by "/" or "."
    "06/12/34/56/78, FR76.3000.4065.0400.7691.1357.791. 1/85/05/78/006/084/91/ 12/03/1992 193.97.106.210",
    "AB/CD/EF/GH ab/12/34/56 1/2/3/4567890 x1/2/3/4 1/2/3/4// /1/2/3/4 S.A.R.L.1.2 1.2.3.4.5x é1/2/3/4é",
    "1/2/3/4/5/6/7.8.9.1.2 1.2.3.4.5/6/7/8 1/2/3/4.",
    "\U0001d7ce\U0001d7cf 𝟐𝟑 ٣٤ ０６ １２",
    "x" * 5000 + "-\n" + "y" * 5000,
    _INVISIBLE * 3 + "fin",
])
def test_edge_cases_identical(text):
    _check(text)


@settings(max_examples=1500, deadline=None)
@given(st.text(alphabet=st.sampled_from(_SPECIAL) | st.characters(exclude_categories=("Cs",)), max_size=80))
@example("a-\nb")
@example("**\U000e0001**")
def test_adversarial_unicode_identical(text):
    _check(text)


@settings(max_examples=300, deadline=None)
@given(st.lists(st.sampled_from(["**", "__", "*_", "-\n", "-\r\n", " -\n ", "a", "É", "1", "é", "​",
                                 "\U000e0020", "ͅ", " ", "\t", "\n", "\r", "12", "345", "Z9",
                                 "1234567890123", "/", ".", "AB", "x"]), max_size=40))
def test_emphasis_and_hyphen_runs_identical(parts):
    _check("".join(parts))


def test_lone_surrogate_falls_back_to_python():
    text = "a\ud800-\nb **x**"
    assert prepare(text, native=True) == _python(text)


def test_unchanged_text_is_returned_as_is():
    text = "deja normalise"
    norm, folded, offsets = prepare(text, native=True)
    assert norm is text and folded is text and offsets is None


# --- Langue / language --------------------------------------------------------------------------------

_WORDS = sorted({w for words in _STOPWORDS.values() for w in words})


@pytest.mark.skipif(not _CORPUS.exists(), reason="corpus absent")
def test_language_corpus_identical():
    for path in sorted(_CORPUS.glob("*.md")):
        folded = fold(normalize(path.read_text(encoding="utf-8"))[0])
        for minimum in (0, 2, 5):
            assert detect_language(folded, minimum, native=True) == detect_language(folded, minimum)


@settings(max_examples=800, deadline=None)
@given(st.lists(st.sampled_from(_WORDS) | st.text(alphabet="abcdefz é1-'", max_size=6), max_size=60),
       st.sampled_from([" ", "-", "'", "é", "\n", "", "𝐚"]), st.integers(-1, 6))
def test_language_identical(words, separator, minimum):
    folded = separator.join(words)
    assert detect_language(folded, minimum, native=True) == detect_language(folded, minimum)


def test_language_edge_inputs_identical():
    for folded, minimum in (("the and the", 2**70), ("le la les", -(2**70)), ("a\ud800 le la les", 2), ("", 0),
                            ("le la les", -(2**63)), ("the", -(2**63)), ("le", 2**63 - 1), ("", -(2**63))):
        assert detect_language(folded, minimum, native=True) == detect_language(folded, minimum)


def test_language_sample_boundary_identical():
    # Le mot coupé à la limite de l'échantillon compte comme Python le voit / word cut at the sample edge.
    for shift in range(-4, 5):
        folded = "x" * (3000 - 3 + shift) + " the and pour avec les"
        assert detect_language(folded, 1, native=True) == detect_language(folded, 1)
    assert detect_language("é" * 2999 + "les la", 1, native=True) == detect_language("é" * 2999 + "les la", 1)
