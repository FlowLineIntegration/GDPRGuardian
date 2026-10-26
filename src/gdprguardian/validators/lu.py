"""Validateurs Luxembourg, écrits d'après les textes publics (loi du 19 juin 2013, LBR, ILR).

Luxembourg validators, written from public texts. Chaque fonction renvoie la valeur canonique
(sans séparateurs) ou None / each function returns the canonical value or None.
"""

from __future__ import annotations

import re
from datetime import date

from .._text import strip_separators
from .checksums import is_digits, luhn_ok, verhoeff_ok

_NON_DIGITS = re.compile(r"[^0-9]")
# Section du RCS (A : commerçants personnes physiques, B : sociétés commerciales…) + 1 à 6 chiffres.
# RCS section (A: sole traders, B: commercial companies…) + 1 to 6 digits.
_RCS_RE = re.compile(r"[A-O][0-9]{1,6}")


def _plausible_birth_date(value: str) -> bool:
    """AAAAMMJJ ; 00 toléré pour un mois ou un jour inconnu / 00 tolerated for an unknown month or day."""
    year, month, day = int(value[:4]), int(value[4:6]), int(value[6:8])
    return 1800 <= year <= date.today().year and month <= 12 and day <= 31


def matricule(candidate: str) -> str | None:
    """Matricule national (13 chiffres) : AAAAMMJJ, rang (3), clé Luhn, clé Verhoeff.

    National identification number: YYYYMMDD, serial (3), Luhn digit, Verhoeff digit. Ordre des champs :
    projet de règlement grand-ducal 49.421, art. 1 / field order: draft regulation 49.421, art. 1
    (https://conseil-etat.public.lu/content/dam/conseil_etat/fr/avis/2013/11/49_421/49421_Texte.pdf).
    Les deux clés portent sur les 11 premiers chiffres, comme dans les validateurs publics
    (https://github.com/grischard/lu.snj.matricule) / both keys cover the first 11 digits.
    """
    value = strip_separators(candidate)
    if len(value) != 13 or not is_digits(value) or not _plausible_birth_date(value):
        return None
    payload = value[:11]
    return value if luhn_ok(payload + value[11]) and verhoeff_ok(payload + value[12]) else None


def matricule_legacy(candidate: str) -> str | None:
    """Ancien matricule à 11 chiffres (avant juillet 2014), sans clé connue : structure seule.

    Pre-July-2014 11-digit matricule, no known check digit: structure only, use with context.
    """
    value = strip_separators(candidate)
    return value if len(value) == 11 and is_digits(value) and _plausible_birth_date(value) else None


def tva(candidate: str) -> str | None:
    """TVA : LU + 8 chiffres, les 2 derniers = 6 premiers mod 89 / last 2 digits = first 6 mod 89."""
    value = strip_separators(candidate).upper().removeprefix("LU")
    if len(value) != 8 or not is_digits(value):
        return None
    return "LU" + value if int(value[6:]) == int(value[:6]) % 89 else None


def rcs(candidate: str) -> str | None:
    """Numéro RCS (Luxembourg Business Registers) : lettre de section + chiffres, ex. B123456."""
    value = strip_separators(candidate).upper()
    return value if _RCS_RE.fullmatch(value) else None


def phone(candidate: str) -> str | None:
    """Téléphone luxembourgeois, forme E.164 : mobile 6xx xxx xxx, fixe 6 à 8 chiffres, sans préfixe 0.

    Luxembourg phone, E.164 form: 9-digit mobile (6…), 6 to 8-digit landline, no trunk prefix.
    Source : https://en.wikipedia.org/wiki/Telephone_numbers_in_Luxembourg
    """
    digits = _NON_DIGITS.sub("", candidate)
    if candidate.lstrip().startswith("+") or digits.startswith("00"):
        digits = digits.removeprefix("00")
        if not digits.startswith("352"):
            return None
        digits = digits[3:]
    if (len(digits) == 9 and digits[0] == "6") or (6 <= len(digits) <= 8 and digits[0] in "2345789"):
        return "+352" + digits
    return None
