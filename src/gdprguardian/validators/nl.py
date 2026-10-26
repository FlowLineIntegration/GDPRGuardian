"""Validateurs Pays-Bas, écrits d'après les règles publiques (Logius, Belastingdienst, PostNL).

Dutch validators, written from public rules. Chaque fonction renvoie la valeur canonique (sans
séparateurs) ou None / each function returns the canonical value (no separators) or None.
"""

from __future__ import annotations

import re

from .._text import strip_separators
from .checksums import is_digits, mod97_10_ok

# 11-proef : 9a + 8b + … + 2h - i ≡ 0 (mod 11) / BSN and RSIN eleven test.
# Spec: https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef
_BSN_WEIGHTS = (9, 8, 7, 6, 5, 4, 3, 2, -1)
_DOCUMENT_RE = re.compile(r"[A-NP-Z]{2}[A-NP-Z0-9]{6}[0-9]")
_POSTCODE_EXCLUDED = frozenset({"SA", "SD", "SS"})
_NON_DIGIT_RE = re.compile(r"[^0-9]")


def eleven_test(digits: str) -> bool:
    """11-proef sur 9 chiffres / eleven test on 9 digits."""
    return sum(int(d) * w for d, w in zip(digits, _BSN_WEIGHTS, strict=True)) % 11 == 0


def bsn(candidate: str) -> str | None:
    """Burgerservicenummer : 9 chiffres (8 si Excel a retiré le 0 initial), 11-proef.

    Citizen service number: 9 digits (8 when Excel dropped the leading 0), eleven test.
    """
    value = strip_separators(candidate)
    if not 8 <= len(value) <= 9 or not is_digits(value):
        return None
    value = value.zfill(9)
    return value if value != "000000000" and eleven_test(value) else None


def _btw_shape(candidate: str) -> str | None:
    """NL + 9 chiffres + B + 2 chiffres, ni zéros seuls / NL + 9 digits + B + 2 digits, not all zeros."""
    value = strip_separators(candidate).upper()
    if len(value) != 14 or not value.startswith("NL") or value[11] != "B":
        return None
    digits, suffix = value[2:11], value[12:]
    if not (is_digits(digits) and is_digits(suffix)) or digits == "000000000" or suffix == "00":
        return None
    return value


def btw(candidate: str) -> str | None:
    """Btw-id : NL + 9 chiffres + B + 2 chiffres ; MOD 97-10 (depuis 2020) ou 11-proef (avant).

    VAT id: NL + 9 digits + B + 2 digits; MOD 97-10 (since 2020) or eleven test (older, BSN/RSIN-based).
    Spec: https://nl.wikipedia.org/wiki/Btw-nummer_(Nederland)
    """
    value = _btw_shape(candidate)
    return value if value is not None and (mod97_10_ok(value) or eleven_test(value[2:11])) else None


def btw_person(candidate: str) -> str | None:
    """Btw-id MOD 97-10 : réservé depuis 2020 aux eenmanszaken, donc à une personne physique.

    MOD 97-10 VAT id: issued since 2020 to sole traders only, hence to a natural person (personal data).
    Ref: https://www.belastingdienst.nl/ (nieuw btw-identificatienummer voor eenmanszaken, 2020)
    """
    value = _btw_shape(candidate)
    return value if value is not None and mod97_10_ok(value) else None


def btw_company(candidate: str) -> str | None:
    """Btw-nummer à 11-proef (RSIN d'une personne morale, ou ancien numéro fondé sur le BSN).

    Eleven-test VAT number: a legal entity's RSIN, or an older BSN-based number (sole-trader cues apply).
    """
    value = _btw_shape(candidate)
    if value is None or mod97_10_ok(value):
        return None
    return value if eleven_test(value[2:11]) else None


def kvk(candidate: str) -> str | None:
    """KvK-nummer : 8 chiffres, sans clé / Chamber of Commerce number: 8 digits, no check digit."""
    value = strip_separators(candidate)
    return value if len(value) == 8 and is_digits(value) else None


def document_number(candidate: str) -> str | None:
    """Paspoort / identiteitskaart : 2 lettres, 6 caractères, 1 chiffre ; jamais la lettre O.

    Passport / ID card number: 2 letters, 6 characters, 1 digit; the letter O is never used.
    Spec: https://www.rvig.nl/sites/default/files/2023-02/Kenmerkenbrochure%20paspoorten%20en%20identiteitskaarten%20model%202014%20NL.pdf
    """
    value = strip_separators(candidate).upper()
    return value if _DOCUMENT_RE.fullmatch(value) else None


def postcode(candidate: str) -> str | None:
    """Postcode : 4 chiffres (sans 0 initial) + 2 lettres, jamais SA, SD ni SS -> « 1234 AB ».

    Postcode: 4 digits (no leading 0) + 2 letters, never SA, SD or SS. Spec: https://nl.wikipedia.org/wiki/Postcodes_in_Nederland
    """
    value = candidate.replace(" ", "").upper()
    if len(value) != 6 or value[0] == "0" or not is_digits(value[:4]):
        return None
    letters = value[4:]
    if not ("A" <= letters[0] <= "Z" and "A" <= letters[1] <= "Z") or letters in _POSTCODE_EXCLUDED:
        return None
    return f"{value[:4]} {letters}"


def phone(candidate: str) -> str | None:
    """Numéro national : 0 + 9 chiffres -> E.164 / national number: 0 + 9 digits -> E.164.

    Plan: https://en.wikipedia.org/wiki/Telephone_numbers_in_the_Netherlands (ACM)
    """
    digits = _NON_DIGIT_RE.sub("", candidate)
    if len(digits) != 10 or digits[0] != "0" or digits[1] == "0":
        return None
    return "+31" + digits[1:]


def phone_mobile(candidate: str) -> str | None:
    """Mobile 06 + 8 chiffres / mobile 06 + 8 digits."""
    value = phone(candidate)
    return value if value is not None and value[3] == "6" else None
