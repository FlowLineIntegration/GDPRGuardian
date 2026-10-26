"""Validateurs Portugal, écrits d'après les règles publiques (AT, Segurança Social, AMA).

Portuguese validators, written from public rules. Chaque fonction renvoie la valeur canonique (sans
séparateurs) ou None / each function returns the canonical value (no separators) or None.
"""

from __future__ import annotations

import re

from .._text import strip_separators
from .checksums import is_digits

# NIF : clé = 11 - (Σ d_i × (9 - i) mod 11), 10 et 11 donnent 0 / check = 11 - weighted sum mod 11.
# Spec: https://pt.wikipedia.org/wiki/N%C3%BAmero_de_identifica%C3%A7%C3%A3o_fiscal
_NIF_WEIGHTS = (9, 8, 7, 6, 5, 4, 3, 2)
# Personnes morales (5) et organismes publics (6) : politique « entreprise » / legal persons, public bodies.
_COLLECTIVE_PREFIXES = ("5", "6")
# NISS : poids 29…2, clé = 9 - (somme mod 10) (django-localflavor, BSD) / NISS weights, check digit.
_NISS_WEIGHTS = (29, 23, 19, 17, 13, 11, 7, 5, 3, 2)
# Fixes 2x, mobiles 91/92/93/96, nomades 30, services / landlines, mobiles, nomadic, services.
_PHONE_PREFIXES = ("2", "91", "92", "93", "96", "30", "707", "708", "760", "761", "762", "800", "808")
_NON_DIGIT_RE = re.compile(r"[^0-9]")


def nif(candidate: str) -> str | None:
    """NIF / NIPC : 9 chiffres, premier non nul, clé mod 11 / 9 digits, mod-11 check digit."""
    value = strip_separators(candidate)
    if len(value) != 9 or not is_digits(value) or value[0] == "0":
        return None
    total = sum(int(d) * w for d, w in zip(value[:8], _NIF_WEIGHTS, strict=True))
    return value if (11 - total % 11) % 11 % 10 == int(value[8]) else None


def nif_person(candidate: str) -> str | None:
    """NIF d'une personne physique ou d'un cas assimilé (préfixes autres que 5 et 6) / natural persons."""
    value = nif(candidate)
    return value if value is not None and not value.startswith(_COLLECTIVE_PREFIXES) else None


def nipc(candidate: str) -> str | None:
    """NIPC d'une personne morale (5) ou d'un organisme public (6) / legal persons and public bodies."""
    value = nif(candidate)
    return value if value is not None and value.startswith(_COLLECTIVE_PREFIXES) else None


def vat_person(candidate: str) -> str | None:
    """TVA PT d'un entrepreneur individuel : PT + NIF de la personne / PT VAT of a sole trader: PT + NIF."""
    value = strip_separators(candidate).upper()
    return value if value.startswith("PT") and nif_person(value[2:]) else None


def vat_company(candidate: str) -> str | None:
    """TVA PT d'une personne morale : PT + NIPC / PT VAT of a legal person: PT + NIPC."""
    value = strip_separators(candidate).upper()
    return value if value.startswith("PT") and nipc(value[2:]) else None


def niss(candidate: str) -> str | None:
    """NISS : 11 chiffres, premier 1 ou 2, clé = 9 - (Σ poids mod 10) / 11 digits, first 1 or 2."""
    value = strip_separators(candidate)
    if len(value) != 11 or not is_digits(value) or value[0] not in "12":
        return None
    total = sum(int(d) * w for d, w in zip(value[:10], _NISS_WEIGHTS, strict=True))
    return value if 9 - total % 10 == int(value[10]) else None


def cc(candidate: str) -> str | None:
    """Cartão de Cidadão (numéro de document) : NIC (8), clé, version (2), clé finale.

    Luhn en base 36 depuis la droite : un caractère sur deux doublé, moins 9 au-delà de 9.
    Base-36 Luhn from the right: every second character doubled, minus 9 above 9.
    Spec: https://www.autenticacao.gov.pt/ (Validação de Número de Documento do Cartão de Cidadão)
    """
    value = strip_separators(candidate).upper()
    if len(value) != 12 or not value.isascii() or not (is_digits(value[:9]) and value[11].isdigit()):
        return None
    if not value[9:11].isalnum():
        return None
    total = 0
    for position, char in enumerate(reversed(value)):
        number = int(char, 36)
        if position % 2:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return value if total % 10 == 0 else None


def nic(candidate: str) -> str | None:
    """Número de identificação civil (ex-BI) : 7-8 chiffres, clé facultative ; valeur canonique sans clé.

    Civil identification number (former BI): 7-8 digits, optional check digit; canonical value without it.
    """
    value = strip_separators(candidate)
    if not 7 <= len(value) <= 9 or not is_digits(value):
        return None
    return value[:8] if len(value) == 9 else value.zfill(8)


def sns(candidate: str) -> str | None:
    """Número de utente du SNS : 9 chiffres, sans clé publiée / 9 digits, no published check."""
    value = strip_separators(candidate)
    return value if len(value) == 9 and is_digits(value) else None


def phone(candidate: str) -> str | None:
    """Numéro national : 9 chiffres, fixes 2x, mobiles 91/92/93/96, nomades 30, services -> E.164.

    National number: 9 digits, landlines 2x, mobiles 91/92/93/96, nomadic 30, services -> E.164.
    Plan: https://en.wikipedia.org/wiki/Telephone_numbers_in_Portugal (ANACOM)
    """
    digits = _NON_DIGIT_RE.sub("", candidate)
    return "+351" + digits if len(digits) == 9 and digits.startswith(_PHONE_PREFIXES) else None
