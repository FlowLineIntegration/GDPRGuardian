"""Texte de détection : normalisation et table de positions / detection text and offset map."""

from __future__ import annotations

from itertools import pairwise

from hypothesis import given
from hypothesis import strategies as st

from gdprguardian._text import (
    ALNUM,
    ALPHA,
    CAPITAL,
    DECIMAL,
    DIGIT,
    INVISIBLE,
    LETTER,
    LOWER,
    MAPS_LOWER,
    MAPS_UPPER,
    PLANE,
    TITLE,
    UPPER,
    UPPER_SAFE,
    WORD,
    char_flags,
    fold,
    normalize,
    plane_classes,
    prepare,
)
from gdprguardian.heuristics._lexicon import UPPER as CAPITALS


def _source(text: str, offsets, start: int, end: int) -> str:
    """Extrait d'origine d'une zone du texte de détection / original slice of a detection-text span."""
    return text[start:end] if offsets is None else text[offsets[start]:offsets[end - 1] + 1]


def test_default_ignorable_characters_are_removed():
    # Un seul remplissage hangul (U+3164) suffisait à cacher un NIR / one Hangul filler used to hide a NIR.
    text = "NIR 1 85ㅤ 05 78 006͏ 084️ 91"
    norm, offsets = normalize(text)
    assert norm == "NIR 1 85 05 78 006 084 91"
    start = norm.index("1 85")
    assert _source(text, offsets, start, len(norm)) == text[text.index("1 85"):]


def test_pdf_hyphenation_is_joined():
    text = "M. Du-\npont et Jean-\n  Pierre Martin, 12-\n14 rue"
    norm, offsets = normalize(text)
    # Minuscule : mot coupé ; majuscule : trait d'union gardé ; chiffres : intacts.
    # Lowercase: split word; uppercase: hyphen kept; digits: untouched.
    assert norm == "M. Dupont et Jean-Pierre Martin, 12-\n14 rue"
    start = norm.index("Dupont")
    assert _source(text, offsets, start, start + 6) == "Du-\npont"


def test_gap_rule_joins_identifier_groups():
    # Tabulation, blancs doublés, saut de ligne entre deux chiffres : une espace, positions d'origine gardées.
    # Tab, doubled blanks, line break between two digits: one space, original positions kept.
    text = "Tél.\t06\t12  34 \t56\r\n78, NIR 1 85 05 78 006\n084 91"
    norm, offsets = normalize(text)
    assert norm == "Tél.\t06 12 34 56 78, NIR 1 85 05 78 006 084 91"
    start = norm.index("06 12")
    assert _source(text, offsets, start, start + 14) == "06\t12  34 \t56\r\n78"
    # Inchangés : mots, blanc simple, ligne vide, plus de 4 blancs, sauts entre lettres, ligne MRZ.
    # Unchanged: words, single blank, blank line, more than 4 blanks, breaks between letters, MRZ line.
    for kept in ("Nom\tPrénom", "a  b", "12 34", "12\n\n34", "12     34", "Jean\nDupont", "12\nrue",
                 "IDFRADUPONT<<<<<<<<<<<<<<<<<<<123456\n1234567890123JEAN<<<<<<<<8001019M5",
                 "1234567890123\n45", "12\r\r\n34", "12\t\r 34"):
        assert normalize(kept) == (kept, None), kept


def test_separator_runs_become_spaces():
    # « / » en 4 groupes ou plus, « . » en 5 groupes ou plus : espaces, longueur gardée (pas de table de positions).
    # "/" in 4 groups or more, "." in 5 or more: spaces, length kept (no offset map).
    text = "Tél 06/12/34/56/78, IBAN FR76.3000.4065.0400.7691.1357.791. NIR 1/85/05/78/006/084/91/"
    norm, offsets = normalize(text)
    assert offsets is None
    assert norm == "Tél 06 12 34 56 78, IBAN FR76 3000 4065 0400 7691 1357 791. NIR 1 85 05 78 006 084 91/"
    # Inchangés : dates, IPv4, version, groupes sans chiffre ou en minuscules, groupe trop long, mot collé.
    # Unchanged: dates, IPv4, versions, groups without digit or lower-case, too long a group, glued word.
    for kept in ("12/03/1992", "193.97.106.210", "v1.2.3.4", "AB/CD/EF/GH", "ab/12/34/56", "1/2/3/4567890",
                 "x1/2/3/4", "1/2/3/4//", "/1/2/3/4", "S.A.R.L.1.2", "1.2.3.4.5x", "2024/10/26/article"):
        assert normalize(kept) == (kept, None), kept


def test_markdown_bold_is_blanked_in_place():
    # À l'intérieur d'un mot (identifiants, e-mails), rien ne bouge / inside a word, nothing changes.
    text = "**N° client :** 12345, __Jean__ et snake__case, mot**gras**fin"
    norm, offsets = normalize(text)
    assert offsets is None and len(norm) == len(text)
    assert norm == "  N° client :   12345,   Jean   et snake__case, mot**gras**fin"


@given(st.text(alphabet="ab1-\n\r\t *_​ㅤé ", max_size=60))
def test_offsets_are_increasing_and_in_bounds(text):
    norm, offsets = normalize(text)
    if offsets is None:
        assert len(norm) == len(text)
        return
    assert len(offsets) == len(norm) + 1 and offsets[-1] == len(text)
    assert all(a < b for a, b in pairwise(offsets))


@given(st.text(alphabet="Ab-\n *_​é ", max_size=40))
def test_prepare_is_normalize_then_fold(text):
    # Voie Python par défaut, avec ou sans noyau Rust / Python path by default, with or without the core.
    norm, offsets = normalize(text)
    assert prepare(text) == (norm, fold(norm), offsets)


def test_char_flags():
    letter = WORD | ALNUM | LETTER | ALPHA
    assert char_flags("a") == letter | LOWER | MAPS_UPPER
    assert char_flags("A") == letter | UPPER | UPPER_SAFE | CAPITAL | MAPS_LOWER
    assert char_flags("7") == WORD | ALNUM | DECIMAL | DIGIT | UPPER_SAFE
    assert char_flags("_") == WORD | UPPER_SAFE
    # Chiffre non décimal : lettre pour `re`, pas pour `str.isalpha` / non-decimal digit.
    assert char_flags("²") == WORD | ALNUM | LETTER | DIGIT | UPPER_SAFE
    assert char_flags("́") == UPPER_SAFE  # marque combinante / combining mark
    # Minuscule (Other_Lowercase) mais pas alphanumérique : d'où les classes prises à Python.
    # Lowercase (Other_Lowercase) yet not alphanumeric: hence classes taken from Python.
    assert char_flags("ͅ") == LOWER | MAPS_UPPER
    assert char_flags("​") == INVISIBLE | UPPER_SAFE
    assert char_flags("\U000e0041") == INVISIBLE | UPPER_SAFE


def _flags(plane: int) -> list[int]:
    """Drapeaux d'un plan reconstruits depuis `plane_classes` (bits déduits compris) / rebuilt from runs."""
    runs, upper, lower = plane_classes(plane, CAPITALS)
    flags = [0] * PLANE
    for bit, spans in runs:
        for start, end in spans:
            for i in range(start, end):
                flags[i] |= bit
    for i in range(PLANE):
        if flags[i] & WORD and not (plane == 0 and i == ord("_")):
            flags[i] |= ALNUM
        if not flags[i] & (LOWER | TITLE):
            flags[i] |= UPPER_SAFE
    for i, _ in upper:
        flags[i] |= MAPS_UPPER
    for i, _ in lower:
        flags[i] |= MAPS_LOWER
    return flags


def test_plane_classes_are_char_flags():
    """Construction vectorisée = référence caractère par caractère (échantillon de chaque plan habité).

    Vectorised construction = per-character reference (a sample of each populated plane).
    """
    for plane in (0, 1, 2, 14):
        flags = _flags(plane)
        for low in range(0, PLANE, 37):
            cp = plane * PLANE + low
            if not 0xD800 <= cp <= 0xDFFF:
                assert flags[low] == char_flags(chr(cp), CAPITALS), hex(cp)
