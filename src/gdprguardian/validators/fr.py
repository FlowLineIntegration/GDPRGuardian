"""Validateurs France, écrits d'après les spécifications publiques (INSEE, DGFiP, ANS, ANTS).

French validators, written from public specifications. Chaque fonction renvoie la valeur
canonique (sans séparateurs) ou None / each function returns the canonical value or None.
"""

from __future__ import annotations

from .._text import strip_separators
from .checksums import is_digits, luhn_ok

_SEX_DIGITS = frozenset("123478")
_CORSICA = {"2A": "19", "2B": "18"}
# Mois du NIR : 01-12, 13 (inconnu), 20-42 (fictifs), 50-99 (état civil incomplet).
# NIR months: 01-12, 13 (unknown), 20-42 (fictitious), 50-99 (incomplete civil status).
_NIR_MONTHS = frozenset(
    [f"{m:02d}" for m in range(1, 14)] + [f"{m:02d}" for m in range(20, 43)]
    + [f"{m:02d}" for m in range(50, 100)]
)


def _nir_body(value: str) -> str | None:
    """13 premiers caractères avec la Corse convertie, ou None / first 13 chars, Corsica converted."""
    if len(value) < 13 or value[0] not in _SEX_DIGITS:
        return None
    dept = value[5:7]
    body = value[:5] + _CORSICA.get(dept, dept) + value[7:13]
    return body if is_digits(body) else None


def nir(candidate: str) -> str | None:
    """NIR / INS : clé = 97 - (13 chiffres mod 97), 2A->19, 2B->18 (INSEE)."""
    value = strip_separators(candidate).upper()
    if len(value) != 15:
        return None
    body = _nir_body(value)
    key = value[13:]
    if body is None or not is_digits(key):
        return None
    # Ni le mois ni le département ne sont filtrés : la clé tranche (mois fictifs, NIA, DOM).
    # Neither month nor department is filtered: the key decides (fictitious months, NIA, overseas).
    return value if int(key) == 97 - int(body) % 97 else None


def nir_without_key(candidate: str) -> str | None:
    """NIR sans clé (13 caractères) : structure seule, à combiner avec un contexte / structure only."""
    value = strip_separators(candidate).upper()
    if len(value) != 13 or _nir_body(value) is None or value[3:5] not in _NIR_MONTHS:
        return None
    return value


def spi(candidate: str) -> str | None:
    """Numéro fiscal (SPI) : 13 chiffres, premier 0-3, 3 derniers = 10 premiers mod 511."""
    value = strip_separators(candidate)
    if len(value) != 13 or not is_digits(value) or value[0] not in "0123":
        return None
    return value if int(value[10:]) == int(value[:10]) % 511 else None


def siren(candidate: str) -> str | None:
    value = strip_separators(candidate)
    if len(value) != 9 or value == "000000000" or not luhn_ok(value):
        return None
    return value


def siret(candidate: str) -> str | None:
    """SIRET : Luhn, sauf La Poste (356000000…, hors siège) : somme des chiffres multiple de 5."""
    value = strip_separators(candidate)
    if len(value) != 14 or not is_digits(value):
        return None
    if value.startswith("356000000") and value != "35600000000048":
        return value if sum(map(int, value)) % 5 == 0 else None
    return value if luhn_ok(value) and luhn_ok(value[:9]) else None


_TVA_ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def tva(candidate: str) -> str | None:
    """TVA intracommunautaire FR : clé numérique (12 + 3 x (SIREN mod 97)) mod 97, ou clé alphanumérique."""
    value = strip_separators(candidate).upper()
    if len(value) != 13 or not value.startswith("FR"):
        return None
    key, body = value[2:4], value[4:]
    if not is_digits(body):
        return None
    # Les numéros monégasques (000…) ne sont pas des SIREN / Monaco numbers are not SIREN.
    if body[:3] != "000" and not luhn_ok(body):
        return None
    if is_digits(key):
        return value if int(key) == (12 + 3 * (int(body) % 97)) % 97 else None
    if key[0] not in _TVA_ALPHABET or key[1] not in _TVA_ALPHABET:
        return None
    first, second = _TVA_ALPHABET.index(key[0]), _TVA_ALPHABET.index(key[1])
    check = first * 24 + second - 10 if key[0].isdigit() else first * 34 + second - 100
    return value if (int(body) + 1 + check // 11) % 11 == check % 11 else None


_RIB_LETTERS = {c: str(v) for v, letters in enumerate(("", "AJ", "BKS", "CLT", "DMU", "ENV", "FOW",
                                                       "GPX", "HQY", "IRZ")) for c in letters}


def rib(candidate: str) -> str | None:
    """RIB : clé = 97 - ((89 x banque + 15 x guichet + 3 x compte) mod 97), lettres converties."""
    value = strip_separators(candidate).upper()
    if len(value) != 23:
        return None
    converted = "".join(_RIB_LETTERS.get(c, c) for c in value)
    if not is_digits(converted):
        return None
    bank, branch, account, key = converted[:5], converted[5:10], converted[10:21], converted[21:]
    expected = 97 - (89 * int(bank) + 15 * int(branch) + 3 * int(account)) % 97
    return value if int(key) == expected else None


def eori(candidate: str) -> str | None:
    """EORI français : FR + SIRET (Luhn) / French EORI: FR + SIRET."""
    value = strip_separators(candidate).upper()
    if not value.startswith("FR"):
        return None
    return value if siret(value[2:]) else None


def luhn_digits(candidate: str) -> str | None:
    """RPPS, IMEI… : chiffres + Luhn / digits + Luhn."""
    value = strip_separators(candidate)
    return value if luhn_ok(value) else None


def finess(candidate: str) -> str | None:
    """FINESS : 9 caractères ; Luhn hors Corse (2A/2B, contrôle structurel seul)."""
    value = strip_separators(candidate).upper()
    if len(value) != 9:
        return None
    if value[:2] in _CORSICA:
        return value if is_digits(value[2:]) else None
    return value if luhn_ok(value) else None


_SIV_EXCLUDED = frozenset("IOU")


def siv_plate(candidate: str) -> str | None:
    """Plaque SIV AA-123-AA : pas de I/O/U, pas de 'SS', pas de '000'."""
    value = strip_separators(candidate).upper()
    if len(value) != 7:
        return None
    letters = value[:2] + value[5:]
    if any(c in _SIV_EXCLUDED for c in letters) or value[2:5] == "000":
        return None
    if value[:2] == "SS" or value[5:] == "SS":
        return None
    return value


def alnum_mixed(candidate: str) -> str | None:
    """Identifiant alphanumérique avec au moins une lettre et un chiffre (CNIe…)."""
    value = strip_separators(candidate).upper()
    has_digit = any(c.isdigit() for c in value)
    has_alpha = any(c.isalpha() for c in value)
    return value if has_digit and has_alpha else None


def contextual_id(candidate: str) -> str | None:
    """Valeur après un libellé (« n° client : … ») : au moins un chiffre / at least one digit."""
    value = candidate.strip(" .-/")
    return value.upper() if any(c.isdigit() for c in value) and len(value) >= 4 else None


def phone_field(candidate: str) -> str | None:
    """Champ « Tél : … » : les chiffres d'un seul numéro, sinon les détecteurs ordinaires décident (deux numéros sur
    la ligne, chiffres de la ligne suivante). Phone field: one phone's worth of digits, else the ordinary detectors
    decide ("(+" free form of public notices, malformed overseas numbers included: 8 to 15 digits; else "00": 11 to
    15, "0": 10, "33": 10 to 13, otherwise 9 to 13).
    """
    digits = "".join(c for c in candidate if c.isdigit())
    if candidate.startswith("(+"):
        # Un seul indicatif, pas de « / » : jamais deux numéros / one country code, no "/": never two numbers.
        ok = 8 <= len(digits) <= 15 and candidate.count("+") == 1 and "/" not in candidate
    elif digits.startswith("00"):
        ok = 11 <= len(digits) <= 15
    elif digits.startswith("0"):
        ok = len(digits) == 10
    elif digits.startswith("33"):
        ok = 10 <= len(digits) <= 13
    else:
        ok = 9 <= len(digits) <= 13
    return contextual_id(candidate) if ok else None


def phone(candidate: str) -> str | None:
    """Téléphone français, forme canonique E.164 / French phone, canonical E.164."""
    digits = "".join(c for c in candidate if c.isdigit())
    if digits.startswith("0033"):
        digits = digits[4:]
    elif digits.startswith("33") and candidate.lstrip().startswith("+"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    elif len(digits) == 10 and digits[:2] == "00":
        return None
    if digits.startswith("0") and len(digits) == 9:
        digits = digits[1:]
    return "+33" + digits if len(digits) == 9 and digits[0] != "0" else None


def phone_overseas(candidate: str) -> str | None:
    """+262, +590, +594, +596, +269, +508, +681, +687, +689 : forme E.164."""
    digits = "".join(c for c in candidate if c.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if not 9 <= len(digits) <= 12:
        return None
    return "+" + digits
