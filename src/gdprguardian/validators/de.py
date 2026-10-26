"""Validateurs Allemagne, écrits d'après les textes officiels (BZSt, VKVV, FeV, ICAO 9303).

German validators, written from official texts. Chaque fonction renvoie la valeur canonique (sans
séparateurs) ou None / each function returns the canonical value (no separators) or None.
"""

from __future__ import annotations

import re

from .._text import strip_separators
from .checksums import icao_check_digit, is_digits, iso7064_mod11_10_ok

_TRIPLE_RE = re.compile(r"([0-9])\1\1")
_NON_DIGIT_RE = re.compile(r"[^0-9]")

# Préfixe Land des formes fédérales à 12 et 13 chiffres (ELSTER : 0 inséré en 5e position).
# Land prefix of the 12- and 13-digit federal forms (ELSTER: a 0 inserted as 5th digit).
_STNR_LAENDER = ("10", "11", "21", "22", "23", "24", "26", "27", "28", "30", "31", "32", "40", "41", "5", "9")
_DOCUMENT_ALPHABET = frozenset("0123456789CFGHJKLMNPRTVWXYZ")
_RVNR_WEIGHTS = (2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1)
_KVNR_WEIGHTS = (1, 2) * 5
_LICENSE_WEIGHTS = tuple(range(9, 0, -1))


def _cross_sum_mod10(digits: str, weights: tuple[int, ...]) -> int:
    """Somme des sommes de chiffres des produits, modulo 10 / sum of the products' digit sums, mod 10."""
    return sum(sum(divmod(int(d) * w, 10)) for d, w in zip(digits, weights, strict=True)) % 10


def _letter_code(letter: str) -> str:
    """Rang alphabétique sur deux chiffres (A=01 ... Z=26) / alphabet rank on two digits."""
    return f"{ord(letter) - 64:02d}"


def steuer_id(candidate: str) -> str | None:
    """Steuer-ID (IdNr, § 139b AO) : 11 chiffres, ISO 7064 MOD 11,10 et règle de répétition du BZSt.

    Parmi les 10 premiers chiffres, une seule valeur se répète, 2 ou 3 fois, jamais 3 fois de suite.
    Among the first 10 digits one value repeats, twice or three times, never three times in a row.
    Spec: https://media.frag-den-staat.de/files/foi/607002/erzeugung-von-identifikationsnummern-grundlegende-beschreibung-der-struktur-und-merkmale.pdf
    """
    value = strip_separators(candidate)
    if len(value) != 11 or not is_digits(value) or value[0] == "0":
        return None
    body = value[:10]
    distinct = set(body)
    # 9 valeurs distinctes = un doublon ; 8 = un triplet ou deux doublons / 9 = one pair; 8 = one triple or two pairs.
    if len(distinct) == 8:
        if max(map(body.count, distinct)) != 3 or _TRIPLE_RE.search(body):
            return None
    elif len(distinct) != 9:
        return None
    return value if iso7064_mod11_10_ok(value) else None


def steuernummer(candidate: str) -> str | None:
    """Steuernummer : forme régionale (10-11 chiffres) ou fédérale (12 chiffres, ou 13 avec un 0 en 5e position).

    Regional form (10-11 digits) or federal form (12 digits, or 13 with a 0 as 5th digit) behind a Land prefix.
    Clés par Land non publiées : structure seule, à combiner avec un contexte / per-Land keys unpublished.
    Formats: https://de.wikipedia.org/wiki/Steuernummer
    """
    value = strip_separators(candidate)
    if not is_digits(value):
        return None
    size = len(value)
    if size in (12, 13):
        federal = value.startswith(_STNR_LAENDER) and (size == 12 or value[4] == "0")
        return value if federal else None
    return value if size in (10, 11) else None


def rvnr(candidate: str) -> str | None:
    """Rentenversicherungsnummer (VKVV § 2) : zone, JJMMAA, initiale, série, clé.

    Clé : lettre -> rang sur 2 chiffres, poids 2,1,2,5,7,1,2,1,2,1,2,1, somme des sommes de chiffres mod 10.
    Key: letter -> 2-digit rank, weights above, sum of the products' digit sums mod 10.
    Spec: https://www.gesetze-im-internet.de/vkvv/__2.html
    """
    value = strip_separators(candidate).upper()
    if len(value) != 12 or not value.isascii() or not (is_digits(value[:8]) and is_digits(value[9:])):
        return None
    letter = value[8]
    if not "A" <= letter <= "Z":
        return None
    # Jour +50 toléré (numéros de série épuisés), 00 pour une date inconnue / day +50 and 00 tolerated.
    day, month = int(value[2:4]), int(value[4:6])
    if month > 12 or not (day <= 31 or 50 <= day <= 81):
        return None
    digits = value[:8] + _letter_code(letter) + value[9:11]
    return value if _cross_sum_mod10(digits, _RVNR_WEIGHTS) == int(value[11]) else None


def kvnr(candidate: str) -> str | None:
    """Krankenversichertennummer (§ 290 SGB V), partie fixe : lettre, 8 chiffres, clé.

    Clé : lettre -> rang sur 2 chiffres, poids 1,2,1,2…, somme des sommes de chiffres mod 10.
    Key: letter -> 2-digit rank, weights 1,2,1,2…, sum of the products' digit sums mod 10.
    Spec: https://de.wikipedia.org/wiki/Krankenversichertennummer
    """
    value = strip_separators(candidate).upper()
    if len(value) != 10 or not value.isascii() or not ("A" <= value[0] <= "Z" and is_digits(value[1:])):
        return None
    digits = _letter_code(value[0]) + value[1:9]
    return value if _cross_sum_mod10(digits, _KVNR_WEIGHTS) == int(value[9]) else None


def id_document(candidate: str) -> str | None:
    """Personalausweis / Reisepass : 9 caractères (chiffres et CFGHJKLMNPRTVWXYZ), clé ICAO facultative.

    La clé 7-3-1 est un 10e caractère distinct (MRZ) : vérifiée seulement si présente ; valeur canonique
    sur 9 caractères. The 7-3-1 check digit is a separate 10th character: checked only when present.
    Spec: https://de.wikipedia.org/wiki/Ausweisnummer ; ICAO Doc 9303 part 3.
    """
    value = strip_separators(candidate).upper()
    if len(value) not in (9, 10) or not _DOCUMENT_ALPHABET.issuperset(value):
        return None
    if len(value) == 10:
        if not value[9].isdigit() or icao_check_digit(value[:9]) != int(value[9]):
            return None
        return value[:9]
    return value


def fuehrerschein(candidate: str) -> str | None:
    """Führerscheinnummer (FeV Anlage 8, champ 5) : 9 caractères, clé, numéro d'exemplaire.

    Clé : A=10…Z=35, poids 9…1, somme mod 11, 10 s'écrit X. Valeur canonique sans le numéro
    d'exemplaire (11e caractère), qui change à chaque réédition / canonical value without the issue number.
    Key: A=10..Z=35, weights 9..1, sum mod 11, 10 written X. Spec: https://de.wikipedia.org/wiki/Führerscheinnummer
    """
    value = strip_separators(candidate).upper()
    if len(value) != 11 or not value.isascii() or not value.isalnum():
        return None
    remainder = sum(int(c, 36) * w for c, w in zip(value[:9], _LICENSE_WEIGHTS, strict=True)) % 11
    return value[:10] if value[9] == ("X" if remainder == 10 else str(remainder)) else None


def ust_idnr(candidate: str) -> str | None:
    """USt-IdNr : DE + 9 chiffres (premier non nul), ISO 7064 MOD 11,10 / DE + 9 digits, MOD 11,10."""
    value = strip_separators(candidate).upper()
    if len(value) != 11 or not value.startswith("DE"):
        return None
    digits = value[2:]
    if not is_digits(digits) or digits[0] == "0" or not iso7064_mod11_10_ok(digits):
        return None
    return value


def phone(candidate: str) -> str | None:
    """Numéro national (0 + indicatif + abonné, 6 à 11 chiffres utiles) -> E.164.

    National number (trunk 0 + area code + subscriber, 6 to 11 significant digits) -> E.164.
    Plan: https://www.bundesnetzagentur.de/ (Nummernplan) ; https://en.wikipedia.org/wiki/Telephone_numbers_in_Germany
    """
    digits = _NON_DIGIT_RE.sub("", candidate)
    if digits[:1] != "0" or digits[1:2] in ("", "0") or not 6 <= len(digits) - 1 <= 11:
        return None
    return "+49" + digits[1:]


def phone_mobile(candidate: str) -> str | None:
    """Mobile 015x, 016x, 017x : 10 ou 11 chiffres utiles / mobile ranges, 10 or 11 significant digits."""
    value = phone(candidate)
    return value if value is not None and value[3:5] in ("15", "16", "17") and len(value) in (13, 14) else None
