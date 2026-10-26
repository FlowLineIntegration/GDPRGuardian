"""Validateurs Suisse, écrits d'après les spécifications publiques (OFAS/ZAS, OFS, OFCOM).

Swiss validators, written from public specifications. Chaque fonction renvoie la valeur
canonique (sans séparateurs) ou None / each function returns the canonical value or None.
"""

from __future__ import annotations

import re

from .._text import strip_separators
from .checksums import is_digits, weighted_mod

_NON_DIGITS = re.compile(r"[^0-9]")
# EAN-13 : poids 1, 3, 1, 3… depuis la gauche, clé comprise / weights 1, 3, 1, 3… from the left, key included.
_EAN13_WEIGHTS = (1, 3) * 6 + (1,)
_UID_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4)
# Suffixes TVA de l'IDE : allemand, français, italien, romanche / UID VAT suffixes (de, fr, it, rm).
_VAT_SUFFIXES = ("MWST", "TVA", "IVA", "TPV")


def avs(candidate: str) -> str | None:
    """Numéro AVS/AHV à 13 chiffres : 756, 9 chiffres aléatoires, clé EAN-13.

    AHVN13: 756 + 9 random digits + EAN-13 check digit (https://de.wikipedia.org/wiki/Sozialversicherungsnummer).
    """
    value = strip_separators(candidate)
    if len(value) != 13 or not value.startswith("756") or not is_digits(value):
        return None
    return value if weighted_mod(value, _EAN13_WEIGHTS, 10) == 0 else None


def uid(candidate: str) -> str | None:
    """IDE/UID (CHE-123.456.789), aussi numéro de TVA avec MWST/TVA/IVA/TPV ; forme canonique CHE + 9 chiffres.

    Business identification number, also the VAT number with a language suffix. Clé = 11 - (somme
    pondérée 5,4,3,2,7,6,5,4 mod 11) ; 10 n'existe pas / key = 11 - weighted sum mod 11, 10 never issued.
    """
    value = strip_separators(candidate).upper()
    for suffix in _VAT_SUFFIXES:
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    value = value.removeprefix("CHE")
    if len(value) != 9 or not is_digits(value):
        return None
    key = (11 - weighted_mod(value, _UID_WEIGHTS, 11)) % 11
    return "CHE" + value if key == int(value[8]) else None


def phone(candidate: str) -> str | None:
    """Téléphone suisse, forme E.164 : 9 chiffres après le 0 ou le +41 / Swiss phone, 9 national digits.

    Source : https://en.wikipedia.org/wiki/Telephone_numbers_in_Switzerland
    """
    digits = _NON_DIGITS.sub("", candidate)
    if candidate.lstrip().startswith("+") or digits.startswith("00"):
        digits = digits.removeprefix("00")
        if not digits.startswith("41"):
            return None
        digits = digits[2:]
    digits = digits.removeprefix("0")
    return "+41" + digits if len(digits) == 9 and digits[0] in "23456789" else None
