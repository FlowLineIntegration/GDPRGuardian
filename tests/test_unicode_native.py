"""Table Unicode unique du noyau Rust : chaque propriété, chaque point de code, contre l'interpréteur.

The Rust core's single Unicode table: every property, every code point, against the interpreter. Classes de `str`
et de `re`, casse complète, repliement, équivalences de `re.IGNORECASE`, classes `\\w`, `\\d`, `\\s` des motifs ;
plans hors BMP chargés à la demande, une fois, jamais par un appel Python à chaque document. Classes of `str`
and `re`, full case, folding, `re.IGNORECASE` equivalences, the patterns' `\\w`, `\\d`, `\\s`; astral planes loaded
on demand, once, never through a per-document Python call.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from array import array
from functools import partial

import pytest

from gdprguardian import _native, _text
from gdprguardian._text import FOLD_TABLE, INVISIBLE_RE, PLANE, code_points
from gdprguardian.heuristics._lexicon import UPPER

core = pytest.importorskip("gdprguardian_core")
if not _native.available():
    pytest.skip("noyau Rust désactivé / Rust core disabled", allow_module_level=True)

TABLES = _native.unicode_tables()
T = core.UnicodeTables


def _plane(plane: int) -> str:
    chars = code_points(plane * PLANE, (plane + 1) * PLANE)
    return chars[:0xD800] + chars[0xE000:] if plane == 0 else chars  # sans substituts / without surrogates


def _bit(flags: list[int], bit: int) -> bytes:
    """Bit `bit` de chaque drapeau, en octets 0/1, en code C / one 0/1 byte per flag, in C code."""
    raw = array("H", flags)
    if sys.byteorder != "little":
        raw.byteswap()
    data = raw.tobytes()
    shift = bit.bit_length() - 1
    half = data[0::2] if shift < 8 else data[1::2]
    return half.translate(bytes((value >> (shift % 8)) & 1 for value in range(256)))


def _expected(chars: str) -> dict[int, bytes]:
    """Chaque bit par une méthode indépendante de la construction : prédicats `str`, catégories, `re` pour les deux
    classes définies par motif. Each bit through a method independent of the construction."""
    capital = re.compile(f"[{UPPER}]")
    singles = list(chars)
    alnum = bytes(map(str.isalnum, singles))
    decimal = bytes(map(str.isdecimal, singles))
    return {
        T.WORD: bytes(a or c == "_" for a, c in zip(alnum, singles, strict=True)),
        T.ALNUM: alnum,
        T.LETTER: bytes(a and not d for a, d in zip(alnum, decimal, strict=True)),
        T.DECIMAL: decimal,
        T.DIGIT: bytes(map(str.isdigit, singles)),
        T.SPACE: bytes(map(str.isspace, singles)),
        T.ALPHA: bytes(map(str.isalpha, singles)),
        T.UPPER: bytes(map(str.isupper, singles)),
        T.LOWER: bytes(map(str.islower, singles)),
        T.TITLE: bytes(unicodedata.category(c) == "Lt" for c in singles),
        T.UPPER_SAFE: bytes(map(str.isupper, map("A".__add__, singles))),
        T.CAPITAL: bytes(capital.fullmatch(c) is not None for c in singles),
        T.INVISIBLE: bytes(INVISIBLE_RE.fullmatch(c) is not None for c in singles),
        T.MAPS_UPPER: bytes(u != c for u, c in zip(map(str.upper, singles), singles, strict=True)),
        T.MAPS_LOWER: bytes(u != c for u, c in zip(map(str.lower, singles), singles, strict=True)),
    }


@pytest.mark.parametrize("plane", range(17))
def test_every_property_of_every_code_point(plane):
    """Les 17 plans, chaque bit, contre les prédicats de `str` / all 17 planes, every bit, against `str`."""
    chars = _plane(plane)
    flags = TABLES.flags_of(chars)
    assert len(flags) == len(chars)
    for bit, expected in _expected(chars).items():
        actual = _bit(flags, bit)
        wrong = [f"U+{ord(c):04X}" for c, a, e in zip(chars, actual, expected, strict=True) if a != e]
        assert not wrong, (bit, wrong[:10])
    assert plane in TABLES.loaded_planes


def test_regex_classes_are_the_str_predicates():
    """`\\w`, `\\d`, `\\s` de `re` = prédicats `str` de la table, sur tout l'espace Unicode.

    `re`'s `\\w`, `\\d`, `\\s` equal the table's `str` predicates over the whole code space.
    """
    every = "".join(_plane(p) for p in range(17))
    for pattern, predicate in ((r"\w", lambda c: c.isalnum() or c == "_"), (r"\d", str.isdecimal),
                               (r"\s", str.isspace)):
        assert set(re.findall(pattern, every)) == {c for c in every if predicate(c)}, pattern


def test_pattern_classes_cover_every_plane():
    """Classes `\\w`, `\\d`, `\\s` du compilateur de motifs = celles de `re`, intervalle par intervalle.

    The pattern compiler's `\\w`, `\\d`, `\\s` equal `re`'s, range by range.
    """
    every = "".join(_plane(p) for p in range(17))
    for name, pattern in (("w", r"\w+"), ("d", r"\d+"), ("s", r"\s+")):
        expected = [(ord(m.group()[0]), ord(m.group()[-1])) for m in re.finditer(pattern, every)]
        merged: list[tuple[int, int]] = []
        for lo, hi in expected:
            if merged and lo == merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], hi)
            elif merged and merged[-1][1] == 0xD7FF and lo == 0xE000:
                merged[-1] = (merged[-1][0], hi)  # le saut des substituts / the surrogate gap
            else:
                merged.append((lo, hi))
        actual = TABLES.perl_class(name)
        assert {cp for lo, hi in actual for cp in range(lo, hi + 1)} == {
            cp for lo, hi in merged for cp in range(lo, hi + 1) if not 0xD800 <= cp <= 0xDFFF}, name


def test_planes_beyond_three_hold_no_class_or_case():
    """Hypothèse des classes de motifs et de `re.IGNORECASE`, vérifiée pour cet interpréteur : rien au-delà.

    Assumption of the pattern classes and `re.IGNORECASE`, checked for this interpreter: nothing beyond.
    """
    assert _text.verified_planes()
    for plane in range(4, 17):
        chars = _plane(plane)
        assert not any(map(str.isalnum, chars)) and not any(map(str.isspace, chars)), plane
    for plane in range(2, 17):
        chars = _plane(plane)
        assert chars.lower() == chars and chars.upper() == chars, plane
        assert not any(map(str.isupper, chars)) and not any(map(str.islower, chars)), plane


def test_case_mappings_and_fold():
    for plane in (0, 1, 2, 14):
        chars = _plane(plane)
        assert TABLES.upper(chars) == "".join(map(str.upper, chars)), plane
        assert TABLES.lower(chars) == "".join(map(str.lower, chars)), plane
    bmp = _plane(0)
    assert TABLES.fold(bmp) == _text.fold(bmp)
    assert TABLES.fold("\U0001d400\U0001f600") == _text.fold("\U0001d400\U0001f600")
    assert dict(_text.ignorecase_data()["lower"])  # données présentes / data present


# Lettres des motifs `(?i)` des packs et des détecteurs, et pièges classiques de `re.IGNORECASE`.
# Letters of the packs' and detectors' `(?i)` patterns, and classic `re.IGNORECASE` traps.
_LETTERS = "abcdefghijklmnopqrstuvwxyzàâäçéèêëîïôöùûüÿABCDEFGHIJKLMNOPQRSTUVWXYZÉİıſKµμΣσςßẞǅǄΩΩθϑ"


def test_ignorecase_equivalents_match_re():
    """Équivalents de chaque lettre sous `re.IGNORECASE`, sur tout l'espace Unicode, par `re` lui-même.

    Each letter's `re.IGNORECASE` equivalents, over the whole code space, by `re` itself.
    """
    every = "".join(_plane(p) for p in range(17))
    for letter in _LETTERS:
        expected = set(re.findall(re.escape(letter), every, re.IGNORECASE))
        assert set(TABLES.equivalents(letter)) == expected, letter
        assert all(TABLES.case_insensitive_eq(letter, c) for c in expected)


def _counting_tables(calls: list[int]):
    """Table neuve dont le chargeur de plans compte ses appels / fresh table whose plane loader counts calls."""
    loader = partial(_text.plane_classes, capital=UPPER)

    def counted(plane: int):
        calls.append(plane)
        return loader(plane)

    return core.UnicodeTables(bmp=loader(0), loader=counted, fold=sorted(FOLD_TABLE.items()),
                              ignorecase=_text.ignorecase_data(), perl_planes=[1, 2, 3])


def test_astral_planes_are_loaded_once_never_per_call():
    """Plan hors BMP : un seul appel à Python par processus, quel que soit le nombre de documents.

    Astral plane: a single Python call per process, however many documents.
    """
    calls: list[int] = []
    tables = _counting_tables(calls)
    rules = core.TextRules(tables, ["m"], ["le"])
    assert tables.loaded_planes == [0] and calls == []
    text = "Jean 😀 𝐀𝐛 Dupont \U000e0041 " * 50
    for _ in range(200):
        assert rules.upper(text) == text.upper()
        assert rules.fold(text) == _text.fold(text)
    assert sorted(calls) == [1, 14]
    assert tables.loaded_planes == [0, 1, 14]


def test_planes_load_lazily_in_a_fresh_process():
    """Processus neuf : seul le BMP au départ ; un détecteur sans GIL charge un plan au besoin (GIL repris).

    Fresh process: only the BMP at first; a GIL-free detector loads a plane when needed (GIL taken back).
    """
    code = (
        "from gdprguardian import _native\n"
        "from gdprguardian.heuristics.fr_names import _native_detector\n"
        "t = _native.unicode_tables()\n"
        "assert t.loaded_planes == [0], t.loaded_planes\n"
        "d = _native_detector()\n"
        "assert d is not None\n"
        "text = 'Bonjour Jean Dupont \\U0001d400 et \\U00020000.'\n"
        "d.detect(text, text.lower())\n"
        "assert 1 in t.loaded_planes and 2 in t.loaded_planes, t.loaded_planes\n"
        "print('ok')\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and result.stdout.strip() == "ok", result.stderr


def test_malformed_tables_are_refused():
    loader = partial(_text.plane_classes, capital=UPPER)
    good = {"bmp": loader(0), "loader": loader, "fold": sorted(FOLD_TABLE.items()),
            "ignorecase": _text.ignorecase_data(), "perl_planes": [1, 2, 3]}
    core.UnicodeTables(**good)
    for change in ({"bmp": ([(T.WORD, [(0, PLANE + 1)])], [], [])},
                   {"bmp": ([(T.ALNUM, [(0, 1)])], [], [])},
                   {"bmp": ([], [(PLANE, "x")], [])},
                   {"perl_planes": [0]},
                   {"fold": [(0x41, 0xD800)]},
                   {"ignorecase": {"lower": [], "cased": []}}):
        with pytest.raises(ValueError):
            core.UnicodeTables(**{**good, **change})
