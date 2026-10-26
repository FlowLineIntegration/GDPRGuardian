"""Générateurs d'identifiants VALIDES ; clés recalculées ici, indépendamment du moteur.

VALID identifier generators; check digits are recomputed here, independently of the engine, and
cross-checked against python-stdnum (test oracle only) in tests/eval. Every function takes a seeded
`random.Random` and returns the canonical compact value; `fmt_*` functions give printed forms.
"""

from __future__ import annotations

from datetime import date
from random import Random

DIGITS = "0123456789"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Plaques SIV : ni I, O, U ; paires SS et WW exclues / SIV plates: no I, O, U; SS and WW pairs excluded.
SIV_LETTERS = "ABCDEFGHJKLMNPQRSTVWXYZ"
_SIV_FORBIDDEN_PAIRS = frozenset({"SS", "WW"})
LA_POSTE_SIREN = "356000000"
LA_POSTE_HEAD_OFFICE = "35600000000048"  # siège : Luhn classique / head office: plain Luhn
_CORSICA = {"2A": "19", "2B": "18"}
# Codes banque réels (publics) / real (public) French bank codes.
BANK_CODES = ("30004", "30003", "30002", "20041", "10278", "30066", "18206", "13306", "11306", "17806",
              "10107", "17515", "40618", "16606", "12506", "14445")
# Pays de naissance (code INSEE 99xxx) / birth country (INSEE 99xxx code).
BIRTH_COUNTRIES = {"350": "Maroc", "352": "Algérie", "351": "Tunisie", "109": "Allemagne", "134": "Espagne",
                   "139": "Portugal", "127": "Italie", "131": "Belgique", "341": "Sénégal", "243": "Viêt Nam"}
_FR_MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
              "novembre", "décembre")


def digits(rng: Random, count: int) -> str:
    return "".join(rng.choices(DIGITS, k=count))


def group(value: str, sizes: tuple[int, ...], sep: str = " ") -> str:
    """Découpe positionnelle / positional grouping: group('123456', (2, 4)) -> '12 3456'."""
    parts, pos = [], 0
    for size in sizes:
        parts.append(value[pos:pos + size])
        pos += size
    if pos < len(value):
        parts.append(value[pos:])
    return sep.join(p for p in parts if p)


def chunks(value: str, size: int, sep: str = " ") -> str:
    return sep.join(value[i:i + size] for i in range(0, len(value), size))


# --- Clés de contrôle / check digits ---------------------------------------------------------------


def luhn_digit(body: str) -> str:
    """Chiffre de Luhn à ajouter / Luhn digit to append (ISO/IEC 7812)."""
    total = 0
    for i, ch in enumerate(reversed(body)):
        value = int(ch)
        if i % 2 == 0:  # doublé une fois le chiffre ajouté / doubled once the digit is appended
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return str(-total % 10)


def nir_key(body: str) -> str:
    """Clé NIR : 97 - (n mod 97), 2A -> 19 et 2B -> 18 / NIR key, Corsica mapped to digits."""
    dept = body[5:7]
    numeric = body[:5] + _CORSICA[dept] + body[7:13] if dept in _CORSICA else body[:13]
    return f"{97 - int(numeric) % 97:02d}"


def _rib_value(ch: str) -> int:
    """Lettre de RIB : A-I = 1-9, J-R = 1-9, S-Z = 2-9 / RIB letter conversion."""
    if ch.isdigit():
        return int(ch)
    index = ord(ch) - ord("A")
    return index % 9 + 1 if index < 18 else index - 16


def rib_key(bank: str, branch: str, account: str) -> str:
    """Clé RIB : 97 - ((89 x banque + 15 x guichet + 3 x compte) mod 97) / RIB key."""
    account_number = int("".join(str(_rib_value(c)) for c in account))
    return f"{97 - (89 * int(bank) + 15 * int(branch) + 3 * account_number) % 97:02d}"


def iban_check(country: str, bban: str) -> str:
    """Clé IBAN ISO 13616 : 98 - (BBAN + pays + 00 mod 97), lettres A=10..Z=35 / IBAN check digits."""
    numeric = "".join(str(int(c, 36)) for c in bban + country + "00")
    return f"{98 - int(numeric) % 97:02d}"


def ean13_digit(body: str) -> str:
    total = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(body))
    return str(-total % 10)


# --- Identifiants de personnes / personal identifiers --------------------------------------------


def nir_place(rng: Random, dept: str) -> str:
    """Lieu de naissance du NIR (5 caractères) / NIR birthplace field (5 chars).

    Métropole : dépt (2) + commune (3) ; DOM : dépt (3) + commune (2) ; étranger : 99 + pays (3).
    """
    if dept == "99":
        return "99" + rng.choice(tuple(BIRTH_COUNTRIES))
    if len(dept) == 3:
        return dept + f"{rng.randint(1, 34):02d}"
    return dept + f"{rng.randint(1, 899):03d}"


def nir(rng: Random, sex_digit: str, year: int, month: int, place: str) -> str:
    """NIR à 15 caractères ; `month` peut être fictif (20-42, 50-99) / 15-char NIR, month may be fictitious."""
    body = f"{sex_digit}{year % 100:02d}{month:02d}{place}{rng.randint(1, 999):03d}"
    return body + nir_key(body)


def fmt_nir(value: str, style: str) -> str:
    if style == "compact":
        return value
    if style == "key_apart":
        return f"{value[:13]} {value[13:]}"
    return group(value, (1, 2, 2, 2, 3, 3, 2))


def siren(rng: Random) -> str:
    body = str(rng.randint(1, 9)) + digits(rng, 7)
    return body + luhn_digit(body)


def siret(rng: Random, siren_value: str) -> str:
    """SIRET = SIREN + NIC ; Luhn sur les 14 chiffres / Luhn over all 14 digits."""
    nic = rng.randint(1, 99) if rng.random() < 0.8 else rng.randint(100, 9999)
    body = f"{siren_value}{nic:04d}"
    return body + luhn_digit(body)


def siret_la_poste(rng: Random) -> str:
    """Établissement de La Poste : somme des chiffres multiple de 5 / digit sum multiple of 5."""
    while True:
        body = LA_POSTE_SIREN + digits(rng, 4)
        check = -sum(map(int, body)) % 5 + rng.choice((0, 5))
        value = body + str(check)
        if value != LA_POSTE_HEAD_OFFICE:
            return value


def fmt_siret(value: str, style: str) -> str:
    return value if style == "compact" else group(value, (3, 3, 3, 5))


def fmt_siren(value: str, style: str) -> str:
    return value if style == "compact" else group(value, (3, 3, 3))


def vat_fr(siren_value: str) -> str:
    """TVA intracommunautaire, clé numérique (12 + 3 x (SIREN mod 97)) mod 97 / numeric-key French VAT."""
    return f"FR{(12 + 3 * (int(siren_value) % 97)) % 97:02d}{siren_value}"


def fmt_vat(value: str, style: str) -> str:
    if style == "compact":
        return value
    if style == "half":
        return f"{value[:4]} {value[4:]}"
    return group(value, (2, 2, 3, 3, 3))


def rib(rng: Random) -> str:
    """RIB 23 caractères : banque, guichet, compte (lettre possible), clé / 23-char RIB."""
    bank = rng.choice(BANK_CODES)
    branch = digits(rng, 5)
    account = digits(rng, 11)
    if rng.random() < 0.12:  # compte avec lettre (style Banque Postale) / account with a letter
        position = rng.randint(6, 8)
        account = account[:position] + rng.choice(UPPER) + account[position + 1:]
    return bank + branch + account + rib_key(bank, branch, account)


def fmt_rib(value: str, style: str) -> str:
    return value if style == "compact" else group(value, (5, 5, 11, 2))


def iban_fr(rib_value: str) -> str:
    return "FR" + iban_check("FR", rib_value) + rib_value


def iban_foreign(rng: Random) -> str:
    """IBAN DE, BE ou ES valides (clés nationales comprises) / valid DE, BE or ES IBANs."""
    country = rng.choice(("DE", "BE", "ES"))
    if country == "DE":
        bban = digits(rng, 18)
    elif country == "BE":
        # Codes banque réels : BNP Paribas Fortis, Belfius, ING, KBC / real bank code ranges.
        low, high = rng.choice(((0, 49), (50, 99), (300, 399), (733, 741)))
        head = f"{rng.randint(low, high):03d}" + digits(rng, 7)
        bban = head + f"{int(head) % 97 or 97:02d}"
    else:
        bank_branch, account = digits(rng, 8), digits(rng, 10)
        bban = bank_branch + _es_check("00" + bank_branch) + _es_check(account) + account
    return country + iban_check(country, bban) + bban


def _es_check(ten_digits: str) -> str:
    weights = (1, 2, 4, 8, 5, 10, 9, 7, 3, 6)
    value = 11 - sum(int(c) * w for c, w in zip(ten_digits, weights, strict=True)) % 11
    return str({10: 1, 11: 0}.get(value, value))


def fmt_iban(value: str, style: str) -> str:
    return value if style == "compact" else chunks(value, 4)


def card(rng: Random) -> str:
    """Visa, Mastercard (51-55 et 2221-2720) ou Amex, Luhn valide / Luhn-valid card number."""
    draw = rng.random()
    if draw < 0.55:
        body = "4" + digits(rng, 14)
    elif draw < 0.8:
        body = str(rng.randint(51, 55)) + digits(rng, 13)
    elif draw < 0.9:
        body = str(rng.randint(2221, 2720)) + digits(rng, 11)
    else:
        body = rng.choice(("34", "37")) + digits(rng, 12)
    return body + luhn_digit(body)


def fmt_card(value: str, style: str) -> str:
    if style == "compact":
        return value
    sep = "-" if style == "dashes" else " "
    return group(value, (4, 6, 5), sep) if len(value) == 15 else chunks(value, 4, sep)


# Indicatifs mobiles des DOM / overseas mobile prefixes: national prefix -> country code.
DOM_MOBILE = {"0692": "262", "0693": "262", "0639": "262", "0690": "590", "0691": "590", "0696": "596",
              "0697": "596", "0694": "594"}


def phone_fr(rng: Random, mobile: bool = True) -> str:
    """Numéro national à 10 chiffres ; 07 suivi de 3 à 9 / 10-digit national number; 07 then 3-9."""
    if not mobile:
        return rng.choice(("01", "02", "03", "04", "05", "09")) + digits(rng, 8)
    if rng.random() < 0.6:
        return "06" + digits(rng, 8)
    return "07" + str(rng.randint(3, 9)) + digits(rng, 7)


def phone_dom(rng: Random) -> str:
    return rng.choice(tuple(DOM_MOBILE)) + digits(rng, 6)


def fmt_phone(national: str, style: str) -> str:
    """Formes écrites courantes / common written forms of a French number."""
    pairs = chunks(national, 2)
    rest = national[1:]
    if style == "dots":
        return chunks(national, 2, ".")
    if style == "dashes":
        return chunks(national, 2, "-")
    if style == "compact":
        return national
    if style == "intl":
        return f"+33 {rest[0]} {chunks(rest[1:], 2)}"
    if style == "intl_paren":
        return f"+33 (0){rest[0]} {chunks(rest[1:], 2)}"
    if style == "intl_compact":
        return "+33" + rest
    if style == "intl_00":
        return f"0033 {rest[0]} {chunks(rest[1:], 2)}"
    if style == "dom_intl":
        return f"+{DOM_MOBILE[national[:4]]} {rest[:3]} {chunks(rest[3:], 2)}"
    if style == "dom_local":
        return f"{national[:4]} {chunks(national[4:], 2)}"
    return pairs


def ipv4(rng: Random) -> str:
    first = rng.choice((2, 5, 31, 37, 46, 62, 77, 78, 82, 86, 90, 92, 109, 176, 178, 185, 188, 193, 212, 217))
    return f"{first}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def ipv6(rng: Random) -> str:
    groups = ["2a01", rng.choice(("cb04", "e0a", "cb1d", "e34"))]
    groups += [f"{rng.randint(0, 0xFFFF):x}" for _ in range(6)]
    return ":".join(groups)


def plate_siv(rng: Random) -> str:
    """Plaque SIV compacte (7 caractères) / compact SIV plate."""
    while True:
        left = "".join(rng.choices(SIV_LETTERS, k=2))
        right = "".join(rng.choices(SIV_LETTERS, k=2))
        if left not in _SIV_FORBIDDEN_PAIRS and right not in _SIV_FORBIDDEN_PAIRS:
            return f"{left}{rng.randint(1, 999):03d}{right}"


def fmt_plate(value: str, style: str) -> str:
    if style == "compact":
        return value
    sep = " " if style == "spaced" else "-"
    return group(value, (2, 3, 2), sep)


def plate_fni(rng: Random) -> str:
    """Ancien format FNI « 1234 AB 75 » / old FNI format."""
    letters = "".join(rng.choices(SIV_LETTERS, k=rng.randint(2, 3)))
    dept = rng.choice(("75", "69", "13", "33", "59", "2A", "974", "44", "67", "31"))
    return f"{rng.randint(1, 9999)} {letters} {dept}"


def passport_fr(rng: Random) -> str:
    return digits(rng, 2) + "".join(rng.choices(UPPER, k=2)) + digits(rng, 5)


def id_card_fr(rng: Random) -> str:
    """CNI : ancien format (12 caractères) ou CNIe (9 alphanumériques) / old or new French ID card."""
    if rng.random() < 0.5:
        return f"{rng.randint(0, 99):02d}{rng.randint(1, 12):02d}{rng.randint(1, 95):02d}{rng.randint(1, 9)}" \
               + digits(rng, 5)
    alphabet = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    while True:
        value = "".join(rng.choices(alphabet, k=9))
        if any(c.isdigit() for c in value) and any(c.isalpha() for c in value):
            return value


def spi(rng: Random) -> str:
    """Numéro fiscal (SPI) : clé = 10 premiers chiffres mod 511 / tax number, key = first 10 mod 511."""
    head = str(rng.randint(0, 3)) + digits(rng, 9)
    return head + f"{int(head) % 511:03d}"


def fmt_spi(value: str, style: str) -> str:
    return value if style == "compact" else group(value, (2, 2, 3, 3, 3))


def rpps(rng: Random) -> str:
    body = "10" + digits(rng, 8)
    return body + luhn_digit(body)


def finess(rng: Random) -> str:
    body = f"{rng.choice((1, 6, 13, 31, 33, 35, 38, 44, 59, 67, 69, 75, 92, 93)):02d}" + digits(rng, 6)
    return body + luhn_digit(body)


def caf_number(rng: Random) -> str:
    return str(rng.randint(1, 9)) + digits(rng, 6)


def france_travail_id(rng: Random) -> str:
    return digits(rng, 7) + rng.choice(UPPER)


def customer_id(rng: Random) -> str:
    style = rng.random()
    if style < 0.4:
        return str(rng.randint(100000, 9999999))
    if style < 0.7:
        return f"CLI-{rng.randint(1, 999999):06d}"
    return f"{rng.choice(UPPER)}{rng.choice(UPPER)}{rng.randint(2019, 2026)}{rng.randint(1, 99999):05d}"


# --- Leurres / decoys ---------------------------------------------------------------------------------


def luhn_order_number(rng: Random) -> str:
    """Numéro de commande à 9 chiffres Luhn-valide : ressemble à un SIREN / Luhn-valid, SIREN look-alike."""
    return siren(rng)


def ean13(rng: Random) -> str:
    body = rng.choice(("300", "301", "340", "376", "400")) + digits(rng, 9)
    return body + ean13_digit(body)


def amount(rng: Random) -> str:
    low, high = rng.choice(((5, 999), (1000, 9999), (10000, 250000)))
    euros = f"{rng.randint(low, high):,}".replace(",", " ")
    style = rng.random()
    if style < 0.45:
        return f"{euros},{rng.randint(0, 99):02d} €"
    if style < 0.75:
        return f"{euros} €"
    return f"{euros},{rng.randint(0, 99):02d} EUR"


def date_text(day: date) -> str:
    """« 1er mars 2025 », « 12 mars 1985 »."""
    prefix = "1er" if day.day == 1 else str(day.day)
    return f"{prefix} {_FR_MONTHS[day.month - 1]} {day.year}"


def date_numeric(day: date, style: str = "slash") -> str:
    if style == "iso":
        return day.isoformat()
    return f"{day.day:02d}/{day.month:02d}/{day.year}"


def random_date(rng: Random, start: date, end: date) -> date:
    return date.fromordinal(rng.randint(start.toordinal(), end.toordinal()))
