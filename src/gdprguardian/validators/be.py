"""Validateurs Belgique, écrits d'après les spécifications publiques (Registre national, BCE, BIPT).

Belgian validators, written from public specifications. Chaque fonction renvoie la valeur
canonique (sans séparateurs) ou None / each function returns the canonical value or None.
"""

from __future__ import annotations

import re
from datetime import date

from .._text import strip_separators
from .checksums import is_digits

_NON_DIGITS = re.compile(r"[^0-9]")
# Mois : 0-12 au registre national (0 = inconnu), +20 ou +40 pour un numéro BIS.
# Months: 0-12 in the national register (0 = unknown), +20 or +40 for a BIS number.
_NN_MONTHS = frozenset(range(13))
_BIS_MONTHS = frozenset((*range(20, 33), *range(40, 53)))
_NISS_MONTHS = _NN_MONTHS | _BIS_MONTHS
_YEAR_2000_PREFIX = 2_000_000_000


def _niss(value: str, months: frozenset[int]) -> str | None:
    """Clé = 97 - (9 premiers chiffres mod 97), précédés d'un 2 pour les naissances depuis 2000.

    Key = 97 - (first 9 digits mod 97), prefixed with a 2 for births from 2000 on.
    Source : https://fr.wikipedia.org/wiki/Numéro_de_registre_national
    """
    if len(value) != 11 or not is_digits(value):
        return None
    month, day = int(value[2:4]), int(value[4:6])
    if month not in months:
        return None
    # Mois inconnu (0, 20, 40) : le jour sert de compteur une fois les rangs épuisés ; sinon jour <= 31.
    # Unknown month (0, 20, 40): the day counts on once serials run out; otherwise day <= 31.
    if day > 31 and month % 20:
        return None
    body, key = int(value[:9]), int(value[9:])
    if key == 97 - body % 97:
        return value
    # Branche 2000 seulement pour une année déjà atteinte / 2000s branch only for a year already reached.
    if 2000 + int(value[:2]) <= date.today().year and key == 97 - (_YEAR_2000_PREFIX + body) % 97:
        return value
    return None


def nn(candidate: str) -> str | None:
    """Numéro de registre national (NN, RRN) / national register number."""
    return _niss(strip_separators(candidate), _NN_MONTHS)


def bis(candidate: str) -> str | None:
    """Numéro BIS (mois + 20 ou + 40) / BIS number (month + 20 or + 40)."""
    return _niss(strip_separators(candidate), _BIS_MONTHS)


def niss(candidate: str) -> str | None:
    """NISS / INSZ : numéro de registre national ou numéro BIS / national register or BIS number."""
    return _niss(strip_separators(candidate), _NISS_MONTHS)


def niss_unpadded(candidate: str) -> str | None:
    """NISS dont un tableur a retiré les zéros de tête (8 à 10 chiffres) / NISS stripped of leading zeros."""
    value = strip_separators(candidate)
    return _niss(value.zfill(11), _NISS_MONTHS) if 8 <= len(value) <= 10 else None


def enterprise_number(candidate: str) -> str | None:
    """Numéro d'entreprise BCE/KBO, qui est aussi le numéro de TVA (BE + 10 chiffres).

    Enterprise number, also the VAT number: 10 digits starting with 0 or 1, key =
    97 - (first 8 digits mod 97), so 97 and never 00 for a zero remainder; legacy 9-digit and
    "BE (0)" forms accepted. Returns the 10 digits.
    """
    value = strip_separators(candidate).upper().removeprefix("BE").replace("(0)", "0")
    if len(value) == 9:
        value = "0" + value
    if len(value) != 10 or not is_digits(value) or value[0] not in "01":
        return None
    return value if int(value[8:]) == 97 - int(value[:8]) % 97 else None


def _mod97_tail(value: str) -> bool:
    """12 chiffres, clé = 10 premiers mod 97, 97 si le reste est nul / key = first 10 mod 97, 97 for 0."""
    return len(value) == 12 and is_digits(value) and int(value[10:]) == (int(value[:10]) % 97 or 97)


def eid(candidate: str) -> str | None:
    """Numéro de carte eID (xxx-xxxxxxx-yy) / eID card number."""
    value = strip_separators(candidate)
    return value if _mod97_tail(value) else None


def bban(candidate: str) -> str | None:
    """Ancien numéro de compte bancaire (xxx-xxxxxxx-yy, même clé que l'eID) / legacy bank account."""
    value = strip_separators(candidate)
    return value if _mod97_tail(value) else None


def phone(candidate: str) -> str | None:
    """Téléphone belge, forme E.164 : 9 chiffres pour un mobile (4…), 8 sinon, après le 0 ou le +32.

    Belgian phone, E.164 form: 9 national digits for a mobile (4…), 8 otherwise.
    Source : https://en.wikipedia.org/wiki/Telephone_numbers_in_Belgium
    """
    digits = _NON_DIGITS.sub("", candidate)
    if candidate.lstrip().startswith("+") or digits.startswith("00"):
        digits = digits.removeprefix("00")
        if not digits.startswith("32"):
            return None
        digits = digits[2:]
    # Préfixe interurbain, ou « (0) » écrit après l'indicatif / trunk prefix, or "(0)" after the code.
    digits = digits.removeprefix("0")
    if (len(digits) == 9 and digits[0] == "4") or (len(digits) == 8 and digits[0] != "0"):
        return "+32" + digits
    return None
