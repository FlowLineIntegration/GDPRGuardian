"""Validateurs internationaux / international validators."""

from __future__ import annotations

import ipaddress

from .._text import strip_separators
from .checksums import base58check_ok, bech32_ok, eip55_ok, is_digits, luhn_ok, mod97_10_ok

# Longueurs IBAN par pays (registre SWIFT) / IBAN lengths per country (SWIFT registry).
IBAN_LENGTHS: dict[str, int] = {
    "AD": 24, "AE": 23, "AL": 28, "AT": 20, "AZ": 28, "BA": 20, "BE": 16, "BG": 22, "BH": 22, "BI": 27,
    "BR": 29, "BY": 28, "CH": 21, "CR": 22, "CY": 28, "CZ": 24, "DE": 22, "DJ": 27, "DK": 18, "DO": 28,
    "EE": 20, "EG": 29, "ES": 24, "FI": 18, "FK": 18, "FO": 18, "FR": 27, "GB": 22, "GE": 22, "GI": 23,
    "GL": 18, "GR": 27, "GT": 28, "HN": 28, "HR": 21, "HU": 28, "IE": 22, "IL": 23, "IQ": 23, "IS": 26,
    "IT": 27, "JO": 30, "KW": 30, "KZ": 20, "LB": 28, "LC": 32, "LI": 21, "LT": 20, "LU": 20, "LV": 21,
    "LY": 25, "MC": 27, "MD": 24, "ME": 22, "MK": 19, "MN": 20, "MR": 27, "MT": 31, "MU": 30, "NI": 28,
    "NL": 18, "NO": 15, "OM": 23, "PK": 24, "PL": 28, "PS": 29, "PT": 25, "QA": 29, "RO": 24, "RS": 22,
    "RU": 33, "SA": 24, "SC": 31, "SD": 18, "SE": 24, "SI": 19, "SK": 24, "SM": 27, "SO": 23, "ST": 25,
    "SV": 28, "TL": 23, "TN": 24, "TR": 26, "UA": 29, "VA": 22, "VG": 24, "XK": 20, "YE": 30,
}


def iban(candidate: str) -> str | None:
    value = strip_separators(candidate).upper()
    expected = IBAN_LENGTHS.get(value[:2])
    if expected is None or len(value) != expected or not value[2:4].isdigit():
        return None
    return value if mod97_10_ok(value[4:] + value[:4]) else None


# Préfixes (IIN) et longueurs des réseaux de cartes (ISO/IEC 7812) / card network prefixes and lengths.
# Sans cette table, tout SIRET Luhn-valide de 14 chiffres passerait pour une carte.
# Without this table, any Luhn-valid 14-digit SIRET would pass as a card.
_CARD_RULES: tuple[tuple[int, int, frozenset[int]], ...] = (
    (4, 4, frozenset({13, 16, 19})),            # Visa
    (51, 55, frozenset({16})),                  # Mastercard
    (2221, 2720, frozenset({16})),              # Mastercard (série 2)
    (34, 34, frozenset({15})),                  # American Express
    (37, 37, frozenset({15})),
    (300, 305, frozenset({14, 16})),            # Diners Club
    (36, 36, frozenset({14, 16})),
    (38, 39, frozenset({14, 16})),
    (6011, 6011, frozenset({16, 17, 18, 19})),  # Discover
    (644, 649, frozenset({16, 17, 18, 19})),
    (65, 65, frozenset({16, 17, 18, 19})),
    (3528, 3589, frozenset({16, 17, 18, 19})),  # JCB
    (62, 62, frozenset({16, 17, 18, 19})),      # UnionPay
    (2200, 2204, frozenset({16, 17, 18, 19})),  # Mir
    (50, 50, frozenset({16, 17, 18, 19})),      # Maestro
    (56, 69, frozenset({16, 17, 18, 19})),
)


def _card_network_ok(value: str) -> bool:
    for low, high, lengths in _CARD_RULES:
        width = len(str(low))
        if len(value) in lengths and low <= int(value[:width]) <= high:
            return True
    return False


def _card_value(candidate: str) -> str | None:
    value = strip_separators(candidate)
    if not 13 <= len(value) <= 19 or not is_digits(value) or len(set(value)) == 1:
        return None
    return value if _card_network_ok(value) and luhn_ok(value) else None


def card(candidate: str) -> str | None:
    """Carte bancaire : préfixe et longueur d'un réseau réel, puis Luhn ; 14 chiffres exclus (voir `card14`).

    Payment card: real network prefix and length, then Luhn; 14 digits excluded (see `card14`).
    """
    value = _card_value(candidate)
    return value if value is not None and len(value) != 14 else None


def card14(candidate: str) -> str | None:
    """Carte Diners à 14 chiffres : même forme qu'un SIRET (Luhn compris), donc à exiger avec un mot-clé.

    14-digit Diners card: same shape as a SIRET (Luhn included), so it must come with a keyword.
    """
    value = _card_value(candidate)
    return value if value is not None and len(value) == 14 else None


def imei(candidate: str) -> str | None:
    value = strip_separators(candidate)
    return value if len(value) == 15 and luhn_ok(value) else None


def ipv4(candidate: str) -> str | None:
    first = candidate.split(".", 1)[0]
    if first in ("0", "127", "255"):
        return None
    return candidate


def _compress_ipv6(packed: bytes) -> str:
    """Forme RFC 5952 en hexadécimal, stable quelle que soit la version de Python (identique au noyau Rust).

    RFC 5952 hex form, stable across Python versions (identical to the Rust core).
    """
    groups = [int.from_bytes(packed[i:i + 2], "big") for i in range(0, 16, 2)]
    best_start, best_len, i = -1, 0, 0
    while i < 8:
        if groups[i] == 0:
            start = i
            while i < 8 and groups[i] == 0:
                i += 1
            if i - start > best_len:
                best_start, best_len = start, i - start
        else:
            i += 1
    if best_len > 1:
        left = ":".join(f"{g:x}" for g in groups[:best_start])
        right = ":".join(f"{g:x}" for g in groups[best_start + best_len:])
        return f"{left}::{right}"
    return ":".join(f"{g:x}" for g in groups)


def ipv6(candidate: str) -> str | None:
    if candidate.count(":") < 2 or sum(c.isalnum() for c in candidate) < 3:
        return None
    try:
        address = ipaddress.IPv6Address(candidate)
    except ValueError:
        return None
    value = int(address)
    mapped = address.ipv4_mapped
    # Boucle locale, non spécifiée, ou leur forme IPv4 encapsulée : jamais une donnée personnelle.
    # Loopback, unspecified, or their IPv4-mapped form: never personal data.
    if value in (0, 1) or (mapped is not None and (mapped.is_loopback or mapped.is_unspecified)):
        return None
    return _compress_ipv6(address.packed)


def mac(candidate: str) -> str | None:
    value = candidate.replace("-", ":").upper()
    return None if value in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF") else value


def btc(candidate: str) -> str | None:
    if candidate[:3].lower() in ("bc1", "tb1"):
        return candidate.lower() if bech32_ok(candidate) else None
    return candidate if base58check_ok(candidate) else None


def eth(candidate: str) -> str | None:
    return candidate.lower() if eip55_ok(candidate) else None


def email(candidate: str) -> str | None:
    local, _, domain = candidate.rpartition("@")
    if not local or local[0] == "." or local[-1] == "." or ".." in local:
        return None
    return local + "@" + domain.lower()


def digits_e164(candidate: str) -> str | None:
    """Numéro international (+CC) : 8 à 15 chiffres / 8 to 15 digits."""
    digits = "".join(c for c in candidate if c.isdigit())
    if candidate.lstrip().startswith("00"):
        digits = digits[2:]
    return "+" + digits if 8 <= len(digits) <= 15 and is_digits(digits) else None


def calendar_date(candidate: str) -> str | None:
    """Date jj/mm/aaaa, jj.mm.aaaa ou aaaa-mm-jj valide / valid calendar date."""
    import datetime as _dt

    parts = [p for p in candidate.replace(".", "/").replace("-", "/").split("/") if p]
    if len(parts) != 3:
        return None
    try:
        if len(parts[0]) == 4:
            year, month, day = (int(p) for p in parts)
        else:
            day, month, year = (int(p) for p in parts)
        date = _dt.date(year, month, day)
    except (ValueError, OverflowError):
        return None
    return date.isoformat()
