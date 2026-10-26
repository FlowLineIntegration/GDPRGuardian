"""Valeurs de cellules : texte canonique, largeurs fixes, formes / cell values: canonical text, widths, shapes.

Les nombres sont rendus comme Excel les affiche (15 chiffres significatifs), sans jamais évaluer de formule.
Numbers are rendered as Excel displays them (15 significant digits); no formula is ever evaluated.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal
from typing import Any

from .._text import fold

# Entiers exacts en double précision / integers exactly representable as a double.
_EXACT_INT = 2.0**53
# Largeur fixe impliquée par l'en-tête : (largeur, longueur minimale à compléter) / (width, min length to pad).
FIXED_WIDTHS: dict[str, tuple[int, int]] = {
    "POSTAL_CODE": (5, 4),
    "PHONE": (10, 9),
    "SIREN": (9, 8),
    "SIRET": (14, 13),
}
_ALNUM_RE = re.compile(r"[^\W_]")
_NULL_MARKERS = frozenset({
    "na", "n/a", "n.a.", "nan", "null", "none", "nil", "neant", "inconnu", "inconnue", "aucun", "aucune", "nc",
    "n.c.", "nr", "n.r.", "nd", "n.d.", "x", "xx", "xxx", "sans", "vide", "unknown", "empty", "tbd", "?", "-",
})
_NULL_MARKER_MAX = 16  # au-delà, seule l'absence d'alphanumérique compte / beyond, only "no alphanumeric" counts


def float_text(value: float) -> str:
    """Flottant -> texte affiché par Excel ; entiers sans exposant / float -> Excel display text."""
    if value != value or value in (float("inf"), float("-inf")):
        return str(value)
    if value.is_integer():
        if -_EXACT_INT < value < _EXACT_INT:
            return str(int(value))
        if abs(value) < 1e21:
            # Excel ne garde que 15 chiffres significatifs / Excel keeps only 15 significant digits.
            return str(int(Decimal(format(value, ".15g"))))
    return format(value, ".15g")


def timedelta_text(value: dt.timedelta) -> str:
    """Durée au format [h]:mm:ss / duration as [h]:mm:ss."""
    total = int(value.total_seconds())
    sign = "-" if total < 0 else ""
    hours, rest = divmod(abs(total), 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{sign}{hours}:{minutes:02d}:{seconds:02d}"


def to_text(value: Any, booleans: tuple[str, str] = ("VRAI", "FAUX")) -> str:
    """Valeur calamine -> texte ; '' pour une cellule vide / calamine value -> text, '' when empty."""
    kind = type(value)
    if kind is str:
        return "" if not value or value.isspace() else value
    if kind is float:
        return float_text(value)
    if kind is bool:
        return booleans[0] if value else booleans[1]
    if kind is int:
        return str(value)
    if kind is dt.date:
        return value.isoformat()
    if kind is dt.datetime:
        if not (value.hour or value.minute or value.second or value.microsecond):
            return value.date().isoformat()
        return value.isoformat(sep=" ", timespec="seconds")
    if kind is dt.time:
        return value.isoformat(timespec="seconds")
    if kind is dt.timedelta:
        return timedelta_text(value)
    return "" if value is None else str(value)


def texts_of(rows: list[list[Any]], booleans: tuple[str, str]) -> list[list[str]]:
    """`to_text` sur toute une grille ; une chaîne non blanche est gardée telle quelle, sans appel.

    `to_text` over a whole grid; a non-blank string is kept as is, without a call.
    """
    return [[value if type(value) is str and value and not value.isspace() else to_text(value, booleans)
             for value in row] for row in rows]


def pad_fixed_width(text: str, label: str | None) -> str:
    """Rétablit les zéros initiaux perdus (code postal 1000 -> 01000) / restores lost leading zeros."""
    spec = FIXED_WIDTHS.get(label) if label else None
    if spec is None or not text.isdigit() or not text.isascii():
        return text
    width, minimum = spec
    return text.zfill(width) if minimum <= len(text) < width else text


def may_hold_identifier(raw: Any, text: str) -> bool:
    """Préfiltre : la cellule doit-elle passer par le moteur ? / must the cell go through the engine?

    Tout texte y passe (détection et nettoyage de sortie) ; dates, heures, booléens et petits nombres jamais,
    les dates de naissance étant traitées par colonne. All text does (detection and output hygiene); dates,
    times, booleans and short numbers never do, birth dates being handled per column.
    """
    kind = type(raw)
    if kind is str:
        return bool(text)
    if kind is float or kind is int:
        # Un identifiant numérique compte au moins 7 chiffres / a numeric identifier has at least 7 digits.
        return text.isdigit() and len(text) >= 7
    return False


def is_null_marker(text: str) -> bool:
    """« n/a », « - », « inconnu »… : jamais masqués comme identifiants / never masked as identifiers."""
    if len(text) > _NULL_MARKER_MAX:
        return _ALNUM_RE.search(text) is None
    stripped = text.strip()
    return _ALNUM_RE.search(stripped) is None or fold(stripped) in _NULL_MARKERS


def is_temporal(raw: Any) -> bool:
    return type(raw) in (dt.date, dt.datetime)


def column_letter(index: int) -> str:
    """0 -> 'A', 16383 -> 'XFD'."""
    letters = ""
    index += 1
    while index > 0:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


_NUMERIC_TEXT = re.compile(r"[+\-]?(?:[0-9]{1,3}(?:[  .,'][0-9]{3}){1,8}|[0-9]{1,40})(?:[.,][0-9]{1,20})?\s?%?")
_DATE_TEXT = re.compile(r"[0-9]{1,2}[/.\-][0-9]{1,2}[/.\-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[ T][0-9:]{5,8})?")
# Premier caractère possible d'un nombre ou d'une date en texte / possible first character of both patterns.
_NUMBER_OR_DATE_STARTS = frozenset("+-0123456789")


def kind_of(raw: Any, text: str) -> str:
    """'' vide, 'n' nombre, 'd' date, 'b' booléen, 't' texte / empty, number, date, boolean, text."""
    if not text:
        return ""
    kind = type(raw)
    if kind is float or kind is int:
        return "n"
    if kind is bool:
        return "b"
    if kind is not str:
        return "d"
    stripped = text.strip()
    if stripped[:1] not in _NUMBER_OR_DATE_STARTS:
        return "t"  # ni nombre ni date ne commencent ainsi / neither pattern can start here
    if _NUMERIC_TEXT.fullmatch(stripped):
        return "n"
    if _DATE_TEXT.fullmatch(stripped):
        return "d"
    return "t"
