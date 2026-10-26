"""Validateurs Italie, écrits d'après les règles publiques (DM 23/12/1976, DPR 633/1972).

Italian validators, written from public rules. Chaque fonction renvoie la valeur canonique (sans
séparateurs) ou None / each function returns the canonical value (no separators) or None.
"""

from __future__ import annotations

import re

from .._text import strip_separators
from .checksums import is_digits, luhn_ok

# Codice fiscale : https://it.wikipedia.org/wiki/Codice_fiscale (DM 23/12/1976, omocodia comprise)
_CF_RE = re.compile(r"[A-Z]{6}[0-9LMNP-V]{2}[ABCDEHLMPRST][0-9LMNP-V]{2}[A-Z][0-9LMNP-V]{3}[A-Z]")
_MONTHS = "ABCDEHLMPRST"
_MONTH_DAYS = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
# Omocodia : chiffres remplacés par LMNPQRSTUV / homocody: digits replaced by LMNPQRSTUV.
_UNDO_HOMOCODY = str.maketrans("LMNPQRSTUV", "0123456789")
_ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Rangs impairs (1re, 3e…) : table officielle, chiffres = lettres A-J ; rangs pairs : 0-9 puis A=0…Z=25.
# Odd positions: official table, digits = letters A-J; even positions: 0-9 then A=0..Z=25.
_ODD_TABLE = (1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23)
_ODD = {c: _ODD_TABLE[i if i < 10 else i - 10] for i, c in enumerate(_ALNUM)}
_EVEN = {c: i if i < 10 else i - 10 for i, c in enumerate(_ALNUM)}

# Partita IVA : bureaux provinciaux 001-100, 120-121 (Bologne 2, Naples 2), 888, 999.
# VAT number office codes. Spec: https://it.wikipedia.org/wiki/Partita_IVA
_IVA_OFFICES = frozenset({*(f"{i:03d}" for i in range(1, 101)), "120", "121", "888", "999"})
_NON_DIGIT_RE = re.compile(r"[^0-9]")


def codice_fiscale_check(body: str) -> str:
    """Caractère de contrôle des 15 premiers caractères / check character of the first 15 characters."""
    total = sum(map(_ODD.__getitem__, body[0::2])) + sum(map(_EVEN.__getitem__, body[1::2]))
    return chr(65 + total % 26)


def codice_fiscale(candidate: str) -> str | None:
    """Codice fiscale d'une personne : 16 caractères, date (jour +40 pour les femmes), clé mod 26.

    Personal tax code: 16 characters, date (day +40 for women), mod-26 check letter; homocodes accepted.
    """
    value = strip_separators(candidate).upper()
    if len(value) != 16 or _CF_RE.fullmatch(value) is None:
        return None
    day = int(value[9:11].translate(_UNDO_HOMOCODY)) % 40
    if not 1 <= day <= _MONTH_DAYS[_MONTHS.index(value[8])]:
        return None
    return value if codice_fiscale_check(value[:15]) == value[15] else None


def partita_iva(candidate: str) -> str | None:
    """Partita IVA (ou codice fiscale numérique) : 11 chiffres, bureau, Luhn.

    Les codes fiscaux d'associations (8xxxxxxxxxx, 9xxxxxxxxxx) n'ont pas de code bureau.
    Association tax codes (8…, 9…) carry no office code, only the Luhn check.
    """
    value = strip_separators(candidate)
    if len(value) != 11 or not is_digits(value) or value[:7] == "0000000":
        return None
    if value[0] not in "89" and value[7:10] not in _IVA_OFFICES:
        return None
    return value if luhn_ok(value) else None


def vat(candidate: str) -> str | None:
    """TVA intracommunautaire : IT + partita IVA / EU VAT number: IT + partita IVA."""
    value = strip_separators(candidate).upper()
    return value if value.startswith("IT") and partita_iva(value[2:]) else None


def phone(candidate: str) -> str | None:
    """Fixe 0x (6 à 11 chiffres, 0 conservé) ou mobile 3x (9-10 chiffres) -> E.164.

    Landline 0x (6 to 11 digits, the 0 is kept) or mobile 3x (9-10 digits) -> E.164.
    Plan: https://en.wikipedia.org/wiki/Telephone_numbers_in_Italy (AGCOM)
    """
    digits = _NON_DIGIT_RE.sub("", candidate)
    if digits[:1] == "0" and digits[1:2] not in ("", "0") and 6 <= len(digits) <= 11:
        return "+39" + digits
    return phone_mobile(digits)


def phone_mobile(candidate: str) -> str | None:
    """Mobile : 3 puis 8 ou 9 chiffres / mobile: 3 then 8 or 9 digits."""
    digits = _NON_DIGIT_RE.sub("", candidate)
    if digits[:1] == "3" and digits[1:2] != "0" and 9 <= len(digits) <= 10:
        return "+39" + digits
    return None
