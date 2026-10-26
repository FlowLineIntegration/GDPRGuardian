"""Outils texte bas niveau / Low-level text helpers.

Toutes les transformations sont faites en code C (`str.translate`, regex) et préservent la longueur,
sauf la suppression des caractères invisibles et des césures de fin de ligne, qui produit une table de
positions. All transforms run in C code and keep the length, except removing invisible characters and
end-of-line hyphenation, which yields an offset map.

Ces fonctions sont la référence. `prepare(text, native=True)` en fait autant en un appel Rust, construit
à partir des tables de ce module (mêmes résultats, prouvés par tests différentiels). These functions are
the reference; `prepare(text, native=True)` does the same in one Rust call built from this module's tables.
"""

from __future__ import annotations

import re
import unicodedata
from array import array
from functools import cache
from typing import Any

# Séparateur de groupes de chiffres après normalisation / digit-group separator after normalisation.
SEP = r"[ .\-]"

# Caractères invisibles ou ignorables par défaut (Unicode), retirés avant détection : un seul suffirait à
# cacher un identifiant. Invisible or default-ignorable characters, removed before detection: a single
# one would hide an identifier (soft hyphen, ZW*, bidi, word joiners, Hangul fillers, variation selectors, tags).
INVISIBLE_RE = re.compile(
    "[­͏؜ᅟᅠ឴឵᠋-᠏​-‏‪-‮⁠-⁤"
    "⁦-⁯ㅤ︀-️﻿ﾠ\U0001bca0-\U0001bca3\U000e0000-\U000e0fff]"
)
# Césure de fin de ligne entre deux lettres (PDF) / end-of-line hyphenation between two letters (PDF).
_HYPHEN_BREAK_RE = re.compile(r"-(?<=[^\W\d_]-)[ \t]{0,2}\r?\n[ \t]{0,2}(?=[^\W\d_])")
# Gras Markdown hors d'un mot (« **N° client :** ») : remplacé par des espaces, longueur gardée. Motif
# sans assertion en tête (3x plus rapide), le contrôle du mot se fait dans `_unbold`.
# Markdown bold outside a word: replaced by spaces, length kept. No leading assertion (3x faster).
_EMPHASIS_RE = re.compile(r"[*_]{2,3}")


def _build_normalize_table() -> dict[int, int]:
    table: dict[int, int] = {}
    # Espaces Unicode -> espace / Unicode spaces -> space
    for cp in (0x00A0, 0x1680, *range(0x2000, 0x200B), 0x202F, 0x205F, 0x3000):
        table[cp] = 0x20
    # Tirets -> '-' / dashes -> '-'
    for cp in (*range(0x2010, 0x2016), 0x2212, 0xFE58, 0xFE63):
        table[cp] = 0x2D
    for cp in (0x2018, 0x2019, 0x02BC, 0x2032):
        table[cp] = 0x27
    table[0x2028] = table[0x2029] = 0x0A
    # Pleine chasse -> ASCII (chiffres, lettres, '@') / fullwidth -> ASCII
    for cp in range(0xFF01, 0xFF5F):
        table[cp] = cp - 0xFF01 + 0x21
    # Chiffres décimaux Unicode -> ASCII / Unicode decimal digits -> ASCII
    starts = (0x0660, 0x06F0, 0x07C0, 0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66,
              0x0CE6, 0x0D66, 0x0DE6, 0x0E50, 0x0ED0, 0x0F20, 0x1040, 0x1090, 0x17E0, 0x1810,
              0x1D7CE, 0x1D7D8, 0x1D7E2, 0x1D7EC, 0x1D7F6)
    for start in starts:
        for i in range(10):
            table[start + i] = 0x30 + i
    # Homoglyphes cyrilliques et grecs courants / common Cyrillic and Greek look-alikes
    for src, dst in zip("АВЕКМНОРСТХаеорсухіјѕΑΒΕΖΗΙΚΜΝΟΡΤΥΧο", "ABEKMHOPCTXaeopcyxijsABEZHIKMNOPTYXo",
                        strict=True):
        table[ord(src)] = ord(dst)
    return table


def _build_fold_table() -> dict[int, int]:
    """Minuscules sans accents, longueur préservée / lowercase without accents, length-preserving."""
    table: dict[int, int] = {cp: cp + 32 for cp in range(0x41, 0x5B)}
    for cp in range(0xC0, 0x250):
        ch = chr(cp)
        base = unicodedata.normalize("NFD", ch)[0]
        if base.isascii() and base.isalpha():
            table[cp] = ord(base.lower())
    for src, dst in zip("ŒœÆæØøĐđŁłÐð", "ooaaooddlldd", strict=True):
        table[ord(src)] = ord(dst)
    table[0x2019] = 0x27
    table[0x00BA] = 0x00B0  # 'nº' -> 'n°'
    return table


NORMALIZE_TABLE = _build_normalize_table()
FOLD_TABLE = _build_fold_table()


def _dense_bmp(table: dict[int, int]) -> str:
    """Table dense (chaîne de 65 536 caractères) : 4x plus rapide qu'un dict pour `str.translate`.

    Dense table (65,536-char string): 4x faster than a dict for `str.translate`.
    """
    chars = [chr(cp) for cp in range(0x10000)]
    for cp, target in table.items():
        if cp < 0x10000:
            chars[cp] = chr(target)
    return "".join(chars)


_NORMALIZE_BMP = _dense_bmp(NORMALIZE_TABLE)
_FOLD_BMP = _dense_bmp(FOLD_TABLE)
_ASTRAL_NORMALIZE = {cp: target for cp, target in NORMALIZE_TABLE.items() if cp >= 0x10000}
_ASTRAL_RE = re.compile("[\U00010000-\U0010ffff]")


def _unbold(match: re.Match[str]) -> str:
    start, end = match.span()
    text = match.string
    # Dans un mot (« snake__case », e-mails) : inchangé / inside a word: unchanged.
    if start > 0 and text[start - 1].isalnum() and end < len(text) and text[end].isalnum():
        return match.group()
    return " " * (end - start)


def normalize(text: str) -> tuple[str, array | None]:
    """Texte de détection et table de positions / detection text and offset map.

    La table vaut None si aucune suppression n'a eu lieu (cas courant, coût nul).
    The map is None when nothing was removed (common case, zero cost).
    """
    if text.isascii():
        mapped = text
    else:
        mapped = text.translate(_NORMALIZE_BMP)
        if _ASTRAL_RE.search(mapped) is not None:
            mapped = mapped.translate(_ASTRAL_NORMALIZE)
    if "**" in mapped or "__" in mapped:
        mapped = _EMPHASIS_RE.sub(_unbold, mapped)
    cuts = [] if mapped.isascii() else [m.span() for m in INVISIBLE_RE.finditer(mapped)]
    if "-" in mapped and "\n" in mapped:
        # « Du-\npont » -> « Dupont » ; « Jean-\nPierre » garde son trait d'union / keeps its hyphen.
        cuts.extend((m.start() if mapped[m.end()].islower() else m.start() + 1, m.end())
                    for m in _HYPHEN_BREAK_RE.finditer(mapped))
        cuts.sort()
    if not cuts:
        return mapped, None
    parts: list[str] = []
    offsets = array("q")
    last = 0
    for start, end in cuts:
        start = max(start, last)
        parts.append(mapped[last:start])
        offsets.extend(range(last, start))
        last = max(last, end)
    parts.append(mapped[last:])
    offsets.extend(range(last, len(mapped)))
    offsets.append(len(mapped))
    return "".join(parts), offsets


def fold(text: str) -> str:
    """Repliement pour les mots-clés / folding for keyword matching."""
    if text.isascii():
        return text.lower()
    return text.translate(_FOLD_BMP)


def prepare(text: str, *, native: bool = False) -> tuple[str, str, array | None]:
    """`normalize` puis `fold`, en un appel : (texte de détection, texte replié, table de positions).

    `normalize` then `fold` in one call. `native=True` : noyau Rust s'il est installé (mêmes résultats,
    sans GIL), sinon ces fonctions Python, qui restent la référence. Rust core when installed (same
    results, GIL released), otherwise these Python functions, which remain the reference.
    """
    preparer = _native_preparer() if native else None
    if preparer is not None:
        try:
            norm, folded, raw = preparer.prepare(text)
        except UnicodeEncodeError:  # demi-codet isolé, hors UTF-8 : voie Python / lone surrogate: Python path
            pass
        else:
            if raw is None:
                return norm, folded, None
            offsets = array("q")
            offsets.frombytes(raw)
            return norm, folded, offsets
    norm, offsets = normalize(text)
    return norm, fold(norm), offsets


@cache
def _native_preparer() -> Any:
    from . import _native  # import différé : _native dépend de ce module / deferred: _native depends on us

    return _native.preparer()


# --- Classes de caractères pour le noyau Rust / character classes for the Rust core ------------------------
#
# Une seule table pour tout le noyau (rust/src/unicode.rs), construite une fois par processus à partir des
# prédicats de CET interpréteur (`str`, `re`) : le noyau ne devine jamais une propriété Unicode. Le plan de
# base est calculé à la construction, chaque autre plan au premier de ses caractères que le noyau rencontre.
# One table for the whole core, built once per process from THIS interpreter's predicates (`str`, `re`): the
# core never guesses a Unicode property. The Basic Multilingual Plane is computed at construction, any other
# plane when the core first meets one of its characters.

# Bits de la table, dans l'ordre de rust/src/unicode.rs / table bits, in the order of rust/src/unicode.rs.
(WORD, ALNUM, LETTER, DECIMAL, DIGIT, SPACE, ALPHA, UPPER, LOWER, TITLE, UPPER_SAFE, CAPITAL, INVISIBLE,
 MAPS_UPPER, MAPS_LOWER) = (1 << bit for bit in range(15))
PLANE = 0x10000
# Version d'Unicode la plus récente dont les plans 4 à 16 sont vérifiés : aucune lettre, aucun chiffre, aucun
# espace ni aucune casse (plans 4 à 13 vides, 14 étiquettes et sélecteurs, 15 et 16 privés). Au-delà, tout est
# relu. Latest Unicode version whose planes 4-16 are known to hold no letter, digit, space nor case; beyond it,
# every plane is read.
_VERIFIED_UNICODE = (17, 0, 0)
_BLOCK = 256
_CLASSES_RE = re.compile(r"([^\W\d_]+)|(\d+)|(_+)|(\s+)")
_ANY_CLASS_RE = re.compile(r"[\w\s]")
_ONES_RE = re.compile(rb"\x01+")
# Intervalles [début, fin) de points dans un plan / [start, end) point runs within a plane.
Runs = list[tuple[int, int]]


def code_points(start: int, end: int) -> str:
    """Points de code de [start, end) (plans entiers), substituts compris, sans boucle Python : UTF-32 construit
    par tranches. Code points of [start, end) (whole planes), surrogates included, without a Python loop.
    """
    planes = range(start // PLANE, end // PLANE)
    raw = bytearray(4 * (end - start))
    raw[0::4] = bytes(range(256)) * ((end - start) // 256)
    raw[1::4] = b"".join(bytes((byte,)) * 256 for byte in range(256)) * len(planes)
    raw[2::4] = b"".join(bytes((plane,)) * PLANE for plane in planes)
    return raw.decode("utf-32-le", "surrogatepass")


def char_flags(ch: str, capital: str | None = None) -> int:
    """Référence, caractère par caractère (tests) : les bits de la table, chacun par un prédicat de `str`.

    Reference, one character at a time (tests): every table bit, each from a `str` predicate. `capital` : classe
    des capitales des heuristiques (`heuristics._lexicon.UPPER` par défaut) / the heuristics' capital class.
    """
    if capital is None:
        from .heuristics._lexicon import UPPER as capital  # import différé : _lexicon importe ce module
    alnum, decimal = ch.isalnum(), ch.isdecimal()
    lower, title = ch.islower(), unicodedata.category(ch) == "Lt"
    return ((alnum or ch == "_") * WORD | alnum * ALNUM | (alnum and not decimal) * LETTER | decimal * DECIMAL
            | ch.isdigit() * DIGIT | ch.isspace() * SPACE | ch.isalpha() * ALPHA | ch.isupper() * UPPER
            | lower * LOWER | title * TITLE | ("A" + ch).isupper() * UPPER_SAFE
            | (re.fullmatch(f"[{capital}]", ch) is not None) * CAPITAL
            | (INVISIBLE_RE.fullmatch(ch) is not None) * INVISIBLE
            | (ch.upper() != ch) * MAPS_UPPER | (ch.lower() != ch) * MAPS_LOWER)


def _runs(flags: bytes, offset: int) -> Runs:
    return [(offset + m.start(), offset + m.end()) for m in _ONES_RE.finditer(flags)]


def _has_case(chars: str) -> bool:
    """Un caractère majuscule, minuscule, de titre, ou à correspondance de casse ? / any cased character?"""
    return not ((chars + "a").islower() and (chars + "A").isupper() and chars.upper() == chars
                and chars.lower() == chars)


def _class_runs(pattern: str, chars: str, first: int) -> Runs:
    """Intervalles d'une classe `[...]` de littéraux et d'intervalles dans un plan, lus dans l'arbre de `re`
    (sans balayer le plan) ; autre forme : balayage par `re`. Runs of a `[...]` class of literals and ranges
    within a plane, read from `re`'s own parse tree (no scan); any other shape: scanned by `re`.
    """
    from re import _parser  # arbre de syntaxe de `re` / `re`'s syntax tree

    tree = list(_parser.parse(pattern))
    if len(tree) == 1 and str(tree[0][0]) == "IN" and all(str(op) in ("LITERAL", "RANGE") for op, _ in tree[0][1]):
        runs = []
        for op, av in tree[0][1]:
            lo, hi = (av, av) if str(op) == "LITERAL" else av
            lo, hi = max(lo, first), min(hi, first + PLANE - 1)
            if lo <= hi:
                runs.append((lo - first, hi + 1 - first))
        return runs
    return [m.span() for m in re.finditer(f"(?:{pattern})+", chars)]


def plane_classes(plane: int, capital: str = "") -> tuple[list[tuple[int, Runs]], list[tuple[int, str]],
                                                          list[tuple[int, str]]]:
    """Classes et casse des 65 536 points d'un plan, en code C (`re`, méthodes `str`) : quelques ms par plan.

    Classes and case of a plane's 65,536 points, in C code: a few ms per plane. Renvoie, en positions dans le
    plan, les intervalles [début, fin) de chaque bit, puis `str.upper()` et `str.lower()` des caractères qu'ils
    changent. Returns, as offsets within the plane, the [start, end) runs of each bit, then `str.upper()` and
    `str.lower()` of the characters they change. ALNUM, UPPER_SAFE et MAPS_* se déduisent / are derived.
    """
    chars = code_points(plane * PLANE, (plane + 1) * PLANE)
    letters: Runs = []
    decimals: Runs = []
    underscores: Runs = []
    spaces: Runs = []
    groups = (letters, decimals, underscores, spaces)
    # `\w` = lettres `[^\W\d_]` + `\d` + « _ », un seul balayage, sur les blocs qui en contiennent.
    # `\w` = letters + `\d` + '_', one pass, over the blocks holding any.
    for start in range(0, PLANE, _BLOCK) if _ANY_CLASS_RE.search(chars) is not None else ():
        if _ANY_CLASS_RE.search(chars, start, start + _BLOCK) is not None:
            for m in _CLASSES_RE.finditer(chars, start, start + _BLOCK):
                groups[m.lastindex - 1].append(m.span())
    alpha: Runs = []
    digits: Runs = list(decimals)
    for start, end in letters:
        run = chars[start:end]
        if run.isalpha():
            alpha.append((start, end))
            continue
        # Lettres au sens de `re` qui ne sont pas `isalpha` : nombres non décimaux (« ² », « Ⅻ »).
        # Letters for `re` that are not `isalpha`: non-decimal numbers.
        alpha += _runs(bytes(map(str.isalpha, run)), start)
        digits += _runs(bytes(not c.isalpha() and c.isdigit() for c in run), start)
    upper: Runs = []
    lower: Runs = []
    title: Runs = []
    upper_map: list[tuple[int, str]] = []
    lower_map: list[tuple[int, str]] = []
    for start in range(0, PLANE, _BLOCK) if _has_case(chars) else ():
        block = chars[start:start + _BLOCK]
        if not _has_case(block):
            continue
        singles = list(block)
        upper += _runs(bytes(map(str.isupper, singles)), start)
        lower += _runs(bytes(map(str.islower, singles)), start)
        title += _runs(bytes(unicodedata.category(c) == "Lt" for c in singles), start)
        upper_map += [(start + i, u) for i, (c, u) in enumerate(zip(singles, map(str.upper, singles), strict=True))
                      if u != c]
        lower_map += [(start + i, u) for i, (c, u) in enumerate(zip(singles, map(str.lower, singles), strict=True))
                      if u != c]
    first = plane * PLANE
    runs = [(WORD, letters + decimals + underscores), (LETTER, letters), (DECIMAL, decimals), (DIGIT, digits),
            (SPACE, spaces), (ALPHA, alpha), (UPPER, upper), (LOWER, lower), (TITLE, title),
            (INVISIBLE, _class_runs(INVISIBLE_RE.pattern, chars, first))]
    if capital:
        runs.append((CAPITAL, _class_runs(f"[{capital}]", chars, first)))
    return runs, upper_map, lower_map


def verified_planes() -> bool:
    """Les plans 4 à 16 de cet interpréteur sont-ils connus vides de lettres, chiffres, espaces et casse ?

    Are this interpreter's planes 4-16 known to hold no letter, digit, space nor case (Unicode version)?
    """
    return tuple(map(int, unicodedata.unidata_version.split("."))) <= _VERIFIED_UNICODE


@cache
def ignorecase_data() -> dict[str, Any]:
    """Données de `re.IGNORECASE`, tirées de `re` lui-même, une fois / `re.IGNORECASE` data, from `re`, once.

    `candidates` : tout caractère dont la correspondance insensible à la casse peut différer de la sensible
    (caractères à casse de `_sre`, leurs minuscules simples, cas supplémentaires de `re`) ; `lower` : minuscule
    simple de `_sre` de chacun ; `cased` : ceux à casse ; `fixes` : cas supplémentaires. Every character whose
    case-insensitive match may differ from the case-sensitive one, with `_sre`'s simple lowercase.
    """
    import _sre
    from re._casefix import _EXTRA_CASES

    planes = range(2) if verified_planes() else range(17)
    cased: list[int] = []
    for plane in planes:
        chars = code_points(plane * PLANE, (plane + 1) * PLANE)
        for start in range(0, PLANE, _BLOCK):
            block = chars[start:start + _BLOCK]
            # `_sre` : minuscule ou majuscule simple différente ; les complètes en sont un sur-ensemble.
            # `_sre`: different simple lowercase or uppercase; the full mappings are a superset.
            if block.upper() != block or block.lower() != block:
                first = plane * PLANE + start
                cased += filter(_sre.unicode_iscased, range(first, first + _BLOCK))
    candidates = set(cased) | set(map(_sre.unicode_tolower, cased)) | set(_EXTRA_CASES)
    candidates.update(cp for fixes in _EXTRA_CASES.values() for cp in fixes)
    ordered = sorted(candidates)
    return {
        "candidates": ordered,
        "lower": [(cp, _sre.unicode_tolower(cp)) for cp in ordered],
        "cased": cased,
        "fixes": sorted((cp, list(fixes)) for cp, fixes in _EXTRA_CASES.items()),
    }


def strip_separators(value: str) -> str:
    return value.translate(_STRIP_TABLE)


_STRIP_TABLE = {ord(" "): None, ord("."): None, ord("-"): None, ord("/"): None}
