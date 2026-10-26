"""Validateurs Espagne, écrits d'après les règles publiques (Interior, AEAT, TGSS).

Spanish validators, written from public rules. Chaque fonction renvoie la valeur canonique (sans
séparateurs) ou None / each function returns the canonical value (no separators) or None.
"""

from __future__ import annotations

import re

from .._text import strip_separators
from .checksums import is_digits

# Lettre de contrôle = table[nombre mod 23] ; I, Ñ, O, U jamais utilisées / check letter = table[n mod 23].
# Spec: https://es.wikipedia.org/wiki/N%C3%BAmero_de_identificaci%C3%B3n_fiscal (Ministerio del Interior)
DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
_NIE_PREFIX = {"X": "0", "Y": "1", "Z": "2"}
_LUHN_DOUBLE = (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)
_CIF_KINDS = frozenset("ABCDEFGHJNPQRSUVW")
_CIF_LETTER_KINDS = frozenset("NPQRSW")
_CIF_DIGIT_KINDS = frozenset("ABEH")
_CIF_LETTERS = "JABCDEFGHI"
_NON_DIGIT_RE = re.compile(r"[^0-9]")


def dni(candidate: str) -> str | None:
    """DNI / NIF de personne physique : 7 ou 8 chiffres + lettre ; K, L, M + 7 chiffres + lettre.

    Un ancien DNI à 7 chiffres est complété par un 0 (même reste mod 23) / 7-digit DNIs are zero-padded.
    K (mineur), L (non-résident), M (étranger sans NIE) : lettre calculée sur les 7 chiffres.
    """
    value = strip_separators(candidate).upper()
    if not 8 <= len(value) <= 9:
        return None
    if value[0] in "KLM":
        prefix, number = value[0], value[1:-1]
        canonical = value
    else:
        prefix, number = "", value[:-1]
        canonical = value.zfill(9)
    if not is_digits(number) or (prefix and len(number) != 7) or int(number) == 0:
        return None
    return canonical if value[-1] == DNI_LETTERS[int(number) % 23] else None


def nie(candidate: str) -> str | None:
    """NIE : X, Y ou Z (-> 0, 1, 2) + 7 chiffres + lettre du DNI / X, Y or Z + 7 digits + DNI letter.

    Les NIE en X délivrés avant le 16/07/2008 peuvent avoir 8 chiffres / pre-2008 X numbers may have 8 digits.
    """
    value = strip_separators(candidate).upper()
    size = len(value)
    if not (size == 9 or (size == 10 and value[0] == "X")) or value[0] not in _NIE_PREFIX:
        return None
    number = value[1:-1]
    if not is_digits(number):
        return None
    return value if value[-1] == DNI_LETTERS[int(_NIE_PREFIX[value[0]] + number) % 23] else None


def cif_control(digits: str) -> int:
    """Clé du CIF : chiffre de Luhn des 7 chiffres centraux / CIF key: Luhn check digit of the 7 digits."""
    total = sum(map(int, digits[1::2])) + sum(_LUHN_DOUBLE[int(d)] for d in digits[0::2])
    return -total % 10


def cif(candidate: str) -> str | None:
    """CIF (NIF de personne morale) : type, 7 chiffres, clé chiffre ou lettre (JABCDEFGHI).

    Lettre exigée pour N, P, Q, R, S, W et les non-résidents (province 00) ; chiffre pour A, B, E, H.
    Letter required for N, P, Q, R, S, W and non-residents (province 00); digit for A, B, E, H.
    Spec: https://es.wikipedia.org/wiki/C%C3%B3digo_de_identificaci%C3%B3n_fiscal (règle plus stricte que stdnum)
    """
    value = strip_separators(candidate).upper()
    if len(value) != 9 or value[0] not in _CIF_KINDS or not is_digits(value[1:8]):
        return None
    control = cif_control(value[1:8])
    kind, last = value[0], value[8]
    if kind in _CIF_LETTER_KINDS:
        allowed: tuple[str, ...] = (_CIF_LETTERS[control],)
    elif kind in _CIF_DIGIT_KINDS:
        allowed = (str(control),)
    elif value[1:3] == "00":
        allowed = (_CIF_LETTERS[control],)
    else:
        allowed = (str(control), _CIF_LETTERS[control])
    return value if last in allowed else None


def nif_person(candidate: str) -> str | None:
    """NIF d'une personne physique (DNI, K/L/M ou NIE) / natural-person NIF."""
    return dni(candidate) or nie(candidate)


def vat_person(candidate: str) -> str | None:
    """TVA ES d'une personne physique (autónomo) : ES + DNI ou NIE / ES VAT of a natural person."""
    value = strip_separators(candidate).upper()
    if not value.startswith("ES"):
        return None
    body = nif_person(value[2:])
    return "ES" + body if body is not None and len(body) == 9 else None


def vat_company(candidate: str) -> str | None:
    """TVA ES d'une personne morale : ES + CIF / ES VAT of a legal person."""
    value = strip_separators(candidate).upper()
    return value if value.startswith("ES") and cif(value[2:]) else None


def nss(candidate: str) -> str | None:
    """Número de la Seguridad Social : province (2), numéro (8), clé (2) = N mod 97.

    N = province × 10^7 + numéro si numéro < 10^7, sinon concaténation (TGSS, variante Intervia) ;
    la variante « toujours concaténée » (Faker) est aussi acceptée, faute de source primaire.
    N = province × 10^7 + number below 10^7, else concatenation; the always-concatenated variant is
    also accepted, as no primary source settles it. Ref: https://intervia.com/doc/validar-numeros-de-la-seguridad-social/
    """
    value = strip_separators(candidate)
    if len(value) != 12 or not is_digits(value) or value[:2] == "00":
        return None
    province, number, control = int(value[:2]), int(value[2:10]), int(value[10:])
    concatenated = int(value[:10]) % 97
    official = (province * 10_000_000 + number) % 97 if number < 10_000_000 else concatenated
    return value if control in (official, concatenated) else None


def phone(candidate: str) -> str | None:
    """Numéro national : 9 chiffres, 6/7 mobiles, 8/9 fixes et services -> E.164.

    National number: 9 digits, 6/7 mobile, 8/9 landline and services -> E.164.
    Plan: https://en.wikipedia.org/wiki/Telephone_numbers_in_Spain (CNMC)
    """
    digits = _NON_DIGIT_RE.sub("", candidate)
    return "+34" + digits if len(digits) == 9 and digits[0] in "6789" else None
