"""Validateurs natifs de tous les packs : identiques à la référence Python, sur toute entrée.

Native validators of every pack: identical to the Python reference, on any input. Chaque validateur Rust est
comparé à sa référence sur au moins 20 000 candidats construits d'après son format (clés valides, chaque chiffre
muté, transpositions, séparateurs, longueurs ±1, préfixes, casse, chiffres non ASCII, blancs Unicode, caractères
invisibles), puis sur des chaînes adverses (Hypothesis). Les tables (lettres, bureaux, préfixes, longueurs IBAN)
sont parcourues en entier, les blancs de `str.isspace()` sur tout Unicode, la casse sur les plans 0 et 1, l'année
en cours à ses bornes. Enfin, le moteur `countries="all"` donne les mêmes zones, le même texte et le même rapport
avec et sans Rust, caractères pièges compris (U+001C–U+001F, « İ », « ı »).
Each Rust validator is compared with its reference on at least 20,000 format-aware candidates, then on
adversarial strings (Hypothesis). Tables are walked exhaustively, `str.isspace()` over all of Unicode, case over
planes 0 and 1, the current year at its edges. Finally the `countries="all"` engine gives the same spans, text and
report, trap characters included.

`GDPRGUARDIAN_VALIDATOR_CASES` fixe le nombre de candidats par validateur (20 000 par défaut) / sets the number of
candidates per validator (20,000 by default).
"""

from __future__ import annotations

import ast
import contextlib
import os
import random
import re
import string
from collections.abc import Callable, Iterator
from datetime import date
from functools import cache
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gdprguardian import Anonymizer, _native
from gdprguardian.packs import PatternRecognizer
from gdprguardian.validators import resolve
from gdprguardian.validators.checksums import luhn_ok
from gdprguardian.validators.intl import IBAN_LENGTHS

core = pytest.importorskip("gdprguardian_core")

_CASES = int(os.environ.get("GDPRGUARDIAN_VALIDATOR_CASES", "20000"))
_RAISES = "<exception Python>"
# Validateurs dont la référence peut lever une exception là où Rust rejette : aucun depuis que
# `checksums.mod97_10_ok` vérifie `isdecimal()` (« ² » ne fait plus lever `int()`). Validators whose reference
# may raise where Rust rejects: none since `mod97_10_ok` checks `isdecimal()`.
_MAY_RAISE: frozenset[str] = frozenset()


@cache
def _python(name: str) -> Callable[[str], str | None]:
    function = resolve(name)

    def call(candidate: str) -> str | None:
        try:
            return function(candidate)
        except ValueError:
            return _RAISES

    return call


def _mismatches(name: str, candidates) -> list[tuple[str, str | None, str | None]]:
    """Candidats où Rust et Python divergent / candidates where Rust and Python differ."""
    python, bad = _python(name), []
    for candidate in candidates:
        expected, got = python(candidate), core.validate(name, candidate)
        agree = (got is None and name in _MAY_RAISE) if expected is _RAISES else got == expected
        if not agree:
            bad.append((candidate, expected, got))
    return bad


def _assert_agree(name: str, candidates) -> None:
    bad = _mismatches(name, candidates)
    assert not bad, f"{name}: {len(bad)} écarts / mismatches, ex. {[ascii(b) for b in bad[:5]]}"


# --- Formats : valeurs plausibles, la clé trouvée par la référence / formats: plausible values ----------------

_DIGITS = string.digits
_UPPER = string.ascii_uppercase
_KEYS1 = list(_DIGITS)
_KEYS2 = [f"{k:02d}" for k in range(100)]


def _d(rng: random.Random, n: int) -> str:
    return "".join(rng.choices(_DIGITS, k=n))


def _letters(rng: random.Random, n: int, alphabet: str = _UPPER) -> str:
    return "".join(rng.choices(alphabet, k=n))


def _keyed(name: str, head: str, tails) -> str:
    """`head` suivi de la première fin que la référence accepte, sinon de la première / first accepted tail."""
    check = resolve(name)
    tails = list(tails)
    return next((head + tail for tail in tails if check(head + tail) is not None), head + tails[0])


def _spaced(rng: random.Random, value: str, sizes: tuple[int, ...]) -> str:
    """Groupes séparés comme dans un document, ou forme compacte / grouped as in a document, or compact."""
    if rng.random() < 0.4:
        return value
    parts, start = [], 0
    for size in sizes:
        parts.append(value[start:start + size])
        start += size
    if start < len(value):
        parts.append(value[start:])
    separator = rng.choice([" ", ".", "-", "/", None])
    if separator is None:
        return "".join(p + rng.choice(" .-/") for p in parts[:-1]) + parts[-1]
    return separator.join(p for p in parts if p)


def _phone(rng: random.Random, national: str, code: str, trunk: bool = True) -> str:
    """Numéro national, ou international avec « + » / « 00 », « (0) » parfois / national or international."""
    digits = national[1:] if trunk and national.startswith("0") else national
    form = rng.random()
    if form < 0.4:
        return _spaced(rng, national, (2, 2, 2, 2, 2, 2))
    if form < 0.7:
        return f"+{code} " + _spaced(rng, digits, (1, 2, 2, 2, 2, 2))
    if form < 0.85:
        return f"00{code} " + _spaced(rng, digits, (2, 3, 2, 2))
    return f"+{code} (0)" + _spaced(rng, digits, (3, 2, 2, 2))


def _nir_body(rng: random.Random) -> str:
    month = rng.choice([*(f"{m:02d}" for m in (*range(1, 14), *range(20, 43), *range(50, 100))), "00", "14", "45"])
    dept = rng.choice(["2A", "2B", "75", "97", "99", _d(rng, 2)])
    return rng.choice("123478") + _d(rng, 2) + month + dept + _d(rng, 6)


def _siren(rng: random.Random) -> str:
    return _keyed("fr.siren", _d(rng, 8), _KEYS1)


def _siret(rng: random.Random) -> str:
    head = "356000000" if rng.random() < 0.1 else _siren(rng)
    return _keyed("fr.siret", head + _d(rng, 4), _KEYS1)


def _tva_key(rng: random.Random) -> list[str]:
    alphabet = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return [*_KEYS2, *(rng.choice(alphabet) + rng.choice(alphabet) for _ in range(40))]


def _iban(rng: random.Random) -> str:
    country, length = rng.choice(sorted(IBAN_LENGTHS.items()))
    bban = "".join(rng.choice(_DIGITS * 3 + _UPPER) for _ in range(length - 4))
    return _spaced(rng, _keyed("intl.iban", country, [k + bban for k in _KEYS2]), (4,) * 9)


_CARD_NETWORKS = [("4", 16), ("4", 13), ("4", 19), ("51", 16), ("55", 16), ("2221", 16), ("2720", 16), ("34", 15),
                  ("37", 15), ("6011", 16), ("644", 17), ("65", 19), ("3528", 16), ("62", 18), ("2200", 16),
                  ("50", 17), ("56", 16), ("300", 16), ("36", 16), ("38", 16), ("1", 16), ("7", 16)]


def _card(rng: random.Random, networks=_CARD_NETWORKS, name: str = "intl.card") -> str:
    prefix, length = rng.choice(networks)
    number = _keyed(name, prefix + _d(rng, length - len(prefix) - 1), _KEYS1)
    return _spaced(rng, number, (4, 4, 4, 4))


def _ipv6(rng: random.Random) -> str:
    groups = [rng.choice([0, 0, 0, rng.randrange(0x10000)]) for _ in range(8)]
    if rng.random() < 0.2:
        groups[:6] = [0, 0, 0, 0, 0, 0xFFFF]
    text = ":".join(f"{g:x}" if rng.random() < 0.8 else f"{g:04X}" for g in groups)
    if rng.random() < 0.6:
        text = text.replace(":0:0:", "::", 1)
    if rng.random() < 0.15:
        text = ":".join(text.split(":")[:6]) + f":{rng.randrange(256)}.{rng.randrange(256)}.1.{rng.randrange(256)}"
    if rng.random() < 0.1:
        text += rng.choice(["%eth0", "%1", "%", "%a%b", "/64"])
    return text


_BTC = ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
        "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
        "BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4",
        "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0",
        "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7"]
_ETH = ["0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed", "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
        "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB", "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb"]


def _btc(rng: random.Random) -> str:
    if rng.random() < 0.7:
        return rng.choice(_BTC)
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    if rng.random() < 0.5:
        return rng.choice("13") + _letters(rng, rng.randint(25, 34), alphabet)
    return rng.choice(["bc1", "tb1", "BC1"]) + _letters(rng, rng.randint(11, 60), "qpzry9x8gf2tvdw0s3jn54khce6mua7l")


def _eth(rng: random.Random) -> str:
    if rng.random() < 0.5:
        return rng.choice(_ETH)
    body = _letters(rng, 40, "0123456789abcdefABCDEF")
    return "0x" + rng.choice([body, body.lower(), body.upper()])


def _calendar(rng: random.Random) -> str:
    day, month, year = rng.randint(0, 32), rng.randint(0, 13), rng.choice([rng.randint(1890, 2030), 2024, 1900, 2000])
    separator = rng.choice("/.-")
    day_text = f"{day:02d}" if rng.random() < 0.7 else str(day)
    if rng.random() < 0.3:
        return f"{year}-{month:02d}-{day:02d}"
    return f"{day_text}{separator}{month:02d}{separator}{year if rng.random() < 0.9 else year % 100}"


def _niss_body(rng: random.Random, months: list[int]) -> str:
    day = rng.choice([rng.randint(0, 31), rng.randint(32, 99)])
    return f"{rng.randint(0, 99):02d}{rng.choice(months):02d}{day:02d}{rng.randint(1, 998):03d}"


_NISS_MONTHS = [*range(13), *range(20, 33), *range(40, 53), 13, 33, 60]


def _niss(rng: random.Random, name: str = "be.niss") -> str:
    value = _keyed(name, _niss_body(rng, _NISS_MONTHS), _KEYS2)
    return rng.choice([value, f"{value[:2]}.{value[2:4]}.{value[4:6]}-{value[6:9]}.{value[9:]}",
                       f"{value[:6]} {value[6:9]}-{value[9:]}"])


def _niss_unpadded(rng: random.Random) -> str:
    value = _keyed("be.niss", f"0{rng.randint(0, 9)}" + _niss_body(rng, _NISS_MONTHS)[2:], _KEYS2)
    return value.lstrip("0") or value


def _enterprise(rng: random.Random) -> str:
    value = _keyed("be.enterprise_number", rng.choice("0011122") + _d(rng, 7), _KEYS2)
    form = rng.choice(["BE {0}.{1}.{2}", "BE{0}{1}{2}", "{0}.{1}.{2}", "BE (0) {3} {1} {2}", "{3}{1}{2}",
                       "be {0} {1} {2}", "{0}{1}{2}"])
    return form.format(value[:4], value[4:7], value[7:], value[1:4])


def _steuer_id(rng: random.Random) -> str:
    body = rng.sample(_DIGITS, 10)
    for _ in range(rng.choice([1, 1, 2])):
        body[rng.randrange(10)] = rng.choice(_DIGITS)
    if body[0] == "0" and rng.random() < 0.9:
        body[0] = rng.choice("123456789")
    return _spaced(rng, _keyed("de.steuer_id", "".join(body), _KEYS1), (2, 3, 3, 3))


def _rvnr(rng: random.Random) -> str:
    day = rng.choice([rng.randint(0, 31), rng.randint(50, 81), rng.randint(32, 99)])
    head = f"{rng.randint(0, 99):02d}{day:02d}{rng.randint(0, 13):02d}{rng.randint(0, 99):02d}"
    return _keyed("de.rvnr", head + rng.choice(_UPPER) + _d(rng, 2), _KEYS1)


def _id_document(rng: random.Random) -> str:
    alphabet = "0123456789CFGHJKLMNPRTVWXYZ"
    body = _letters(rng, 9, alphabet if rng.random() < 0.9 else alphabet + "ABO")
    return body if rng.random() < 0.4 else _keyed("de.id_document", body, _KEYS1)


def _fuehrerschein(rng: random.Random) -> str:
    body = _letters(rng, 9, _DIGITS + _UPPER)
    return _keyed("de.fuehrerschein", body, [k + rng.choice(_DIGITS) for k in [*_KEYS1, "X"]])


def _dni(rng: random.Random) -> str:
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    if rng.random() < 0.2:
        return _keyed("es.dni", rng.choice("KLM") + _d(rng, 7), list(letters))
    return _keyed("es.dni", _d(rng, rng.choice([8, 8, 7])), list(letters))


def _nie(rng: random.Random) -> str:
    head = rng.choice("XYZ") + _d(rng, 7) if rng.random() < 0.8 else "X" + _d(rng, 8)
    return _keyed("es.nie", head, list("TRWAGMYFPDXBNJZSQVHLCKE"))


def _cif(rng: random.Random) -> str:
    head = rng.choice("ABCDEFGHJNPQRSUVWXZ") + rng.choice(["00", _d(rng, 2)]) + _d(rng, 5)
    return _keyed("es.cif", head, list("0123456789JABCDEFGHI"))


def _codice_fiscale(rng: random.Random) -> str:
    def number_like(n: int) -> str:
        return "".join(rng.choice(_DIGITS * 3 + "LMNPQRSTUV") for _ in range(n))

    day = rng.choice([rng.randint(1, 31), rng.randint(41, 71), rng.randint(0, 99)])
    body = (_letters(rng, 6) + number_like(2) + rng.choice("ABCDEHLMPRST") + f"{day:02d}" + rng.choice(_UPPER)
            + number_like(3))
    return _keyed("it.codice_fiscale", body, list(_UPPER))


def _partita_iva(rng: random.Random) -> str:
    office = rng.choice([f"{rng.randint(1, 100):03d}", "120", "121", "888", "999", _d(rng, 3)])
    return _keyed("it.partita_iva", rng.choice(["0", "1", "8", "9"]) + _d(rng, 6) + office, _KEYS1)


def _matricule_date(rng: random.Random) -> str:
    year = rng.choice([rng.randint(1790, date.today().year + 2), rng.randint(1940, 2010)])
    return f"{year}{rng.randint(0, 13):02d}{rng.randint(0, 32):02d}"


def _matricule(rng: random.Random) -> str:
    return _spaced(rng, _keyed("lu.matricule", _matricule_date(rng) + _d(rng, 3), _KEYS2), (4, 2, 2, 3, 2))


def _btw(rng: random.Random) -> str:
    if rng.random() < 0.5:
        nine = _keyed("nl.bsn", _d(rng, 8), _KEYS1)
        return f"NL{nine}B{rng.choice(['01', '02', '00', _d(rng, 2)])}"
    return _keyed("nl.btw_person", "NL" + _d(rng, 9) + "B", _KEYS2)


def _nif(rng: random.Random) -> str:
    return _keyed("pt.nif", rng.choice("123456789") + _d(rng, 7), _KEYS1)


def _pt_phone(rng: random.Random) -> str:
    prefix = rng.choice(["2", "91", "92", "93", "96", "30", "707", "760", "808", "94", "1"])
    return prefix + _d(rng, 9 - len(prefix))


def _cc(rng: random.Random) -> str:
    head = _d(rng, 9) + rng.choice(["ZZ", "ZY", "1A", "A0", _letters(rng, 2, _DIGITS + _UPPER)])
    return _spaced(rng, _keyed("pt.cc", head, _KEYS1), (8, 1, 3))


def _spi(rng: random.Random) -> str:
    head = rng.choice("01234") + _d(rng, 9)
    return _spaced(rng, head + f"{int(head) % 511:03d}", (2, 2, 3, 3, 3))


def _fr_tva(rng: random.Random, name: str = "fr.tva") -> str:
    body = rng.choice([_siren(rng), "000" + _d(rng, 6)])
    return _spaced(rng, _keyed(name, "FR", [key + body for key in _tva_key(rng)]), (4, 3, 3, 3))


def _finess(rng: random.Random) -> str:
    if rng.random() < 0.2:
        return rng.choice(["2A", "2B"]) + _d(rng, 7)
    return _keyed("fr.finess", _d(rng, 8), _KEYS1)


def _overseas(rng: random.Random) -> str:
    code = rng.choice(["262", "590", "594", "596", "269", "508", "681", "687", "689"])
    return rng.choice(["+", "00", ""]) + code + " " + _d(rng, rng.randint(5, 10))


def _mac(rng: random.Random) -> str:
    pairs = [rng.choice(["00", "FF", "ff", _letters(rng, 2, "0123456789abcdefABCDEF")]) for _ in range(6)]
    return rng.choice(":-").join(pairs)


def _email(rng: random.Random) -> str:
    local, domain = _letters(rng, rng.randint(0, 8), "abcXYZ.-_12"), _letters(rng, rng.randint(1, 8), "abcDEF.")
    return f"{local}@{domain}{rng.choice(['.fr', '.COM', ''])}"


def _e164(rng: random.Random) -> str:
    prefix = rng.choice(["+", "00", "", " 00"]) + rng.choice(["44", "1", "49", "352"])
    return prefix + " " + _spaced(rng, _d(rng, rng.randint(5, 13)), (2, 3, 4))


def _be_phone(rng: random.Random) -> str:
    national = rng.choice(["4" + rng.choice("56789"), rng.choice("2349"), rng.choice("15678")]) + _d(rng, 7)
    return _phone(rng, "0" + national, "32")


def _uid(rng: random.Random) -> str:
    suffix = rng.choice(["", " MWST", " TVA", " IVA", " TPV", "MWST", " HR"])
    return _spaced(rng, _keyed("ch.uid", "CHE" + _d(rng, 8), _KEYS1), (3, 3, 3, 3)) + suffix


def _steuernummer(rng: random.Random) -> str:
    head = rng.choice(["10", "21", "41", "5", "9", "12", "0"])
    return _spaced(rng, head + _d(rng, rng.randint(8, 12)), (2, 3, 5))


def _lu_tva(rng: random.Random) -> str:
    head = _d(rng, 6)
    return "LU " + _spaced(rng, head + f"{int(head) % 89:02d}", (3, 3, 2))


def _lu_phone(rng: random.Random) -> str:
    national = rng.choice(["6" + _d(rng, 8), rng.choice("234578") + _d(rng, rng.randint(5, 7))])
    return _phone(rng, national, "352", trunk=False)


def _mc_phone(rng: random.Random) -> str:
    national = rng.choice(["9" + _d(rng, 7), "4" + _d(rng, 7), "06" + _d(rng, 8), "3" + _d(rng, 7)])
    return _phone(rng, national, "377", trunk=False)


def _rci(rng: random.Random) -> str:
    return f"{_d(rng, 2)} {rng.choice(['S', 'C', 'P', 'SC', 'X', 'SS'])} {_d(rng, rng.choice([5, 5, 4, 6]))}"


def _nl_document(rng: random.Random) -> str:
    return _letters(rng, 2, "ABCNOPZ") + _letters(rng, 6, _DIGITS + "AOZ") + rng.choice(_DIGITS + "O")


def _postcode(rng: random.Random) -> str:
    letters = rng.choice(["SA", "SD", "SS", "AB", "zz", _letters(rng, 2)])
    return f"{rng.randint(0, 9999):04d}{rng.choice([' ', '', '  '])}{letters}"


_FORMATS: dict[str, Callable[[random.Random], str]] = {
    "fr.nir": lambda r: _spaced(r, _keyed("fr.nir", _nir_body(r), _KEYS2), (1, 2, 2, 2, 3, 3, 2)),
    "fr.nir_without_key": lambda r: _spaced(r, _nir_body(r), (1, 2, 2, 2, 3, 3)),
    "fr.spi": _spi,
    "fr.siren": lambda r: _spaced(r, _siren(r), (3, 3, 3)),
    "fr.siret": lambda r: _spaced(r, _siret(r), (3, 3, 3, 5)),
    "fr.tva": _fr_tva,
    "fr.rib": lambda r: _spaced(r, _keyed("fr.rib", _d(r, 10) + _letters(r, 11, _DIGITS * 4 + _UPPER), _KEYS2),
                                (5, 5, 11, 2)),
    "fr.luhn_digits": lambda r: _spaced(r, _keyed("fr.luhn_digits", _d(r, r.randint(8, 14)), _KEYS1), (3, 3, 3, 3)),
    "fr.finess": _finess,
    "fr.siv_plate": lambda r: f"{_letters(r, 2)}-{_d(r, 3)}-{_letters(r, 2)}",
    "fr.alnum_mixed": lambda r: _letters(r, r.randint(1, 12), _DIGITS + _UPPER + "abcé"),
    "fr.contextual_id": lambda r: r.choice(["", " ", "-", "/ "]) + _letters(r, r.randint(1, 10), _DIGITS + "ABC-/. "),
    "fr.phone": lambda r: _phone(r, "0" + r.choice("1234567896") + _d(r, 8), "33"),
    "fr.phone_overseas": _overseas,
    "fr.eori": lambda r: "FR" + _siret(r),
    "intl.iban": _iban,
    "intl.card": _card,
    "intl.card14": lambda r: _card(r, [("300", 14), ("305", 14), ("36", 14), ("38", 14), ("39", 14), ("4", 14)],
                                   "intl.card14"),
    "intl.imei": lambda r: _spaced(r, _keyed("intl.imei", _d(r, 14), _KEYS1), (2, 6, 6, 1)),
    "intl.ipv4": lambda r: ".".join(str(r.choice([0, 127, 255, r.randrange(256)])) for _ in range(4)),
    "intl.ipv6": _ipv6,
    "intl.mac": _mac,
    "intl.btc": _btc,
    "intl.eth": _eth,
    "intl.email": _email,
    "intl.digits_e164": _e164,
    "intl.calendar_date": _calendar,
    "be.nn": lambda r: _niss(r, "be.nn"),
    "be.bis": lambda r: _niss(r, "be.bis"),
    "be.niss": _niss,
    "be.niss_unpadded": _niss_unpadded,
    "be.enterprise_number": _enterprise,
    "be.eid": lambda r: _spaced(r, _keyed("be.eid", _d(r, 10), _KEYS2), (3, 7, 2)),
    "be.bban": lambda r: _spaced(r, _keyed("be.bban", _d(r, 10), _KEYS2), (3, 7, 2)),
    "be.phone": _be_phone,
    "ch.avs": lambda r: _spaced(r, _keyed("ch.avs", r.choice(["756", "756", "757"]) + _d(r, 9), _KEYS1), (3, 4, 4, 2)),
    "ch.uid": _uid,
    "ch.phone": lambda r: _phone(r, "0" + r.choice("234567891") + _d(r, 8), "41"),
    "de.steuer_id": _steuer_id,
    "de.steuernummer": _steuernummer,
    "de.rvnr": _rvnr,
    "de.kvnr": lambda r: _keyed("de.kvnr", r.choice(_UPPER) + _d(r, 8), _KEYS1),
    "de.id_document": _id_document,
    "de.fuehrerschein": _fuehrerschein,
    "de.ust_idnr": lambda r: _keyed("de.ust_idnr", "DE" + r.choice(_DIGITS + "123456789") + _d(r, 7), _KEYS1),
    "de.phone": lambda r: _spaced(r, "0" + r.choice("123456789") + _d(r, r.randint(4, 11)), (4, 3, 4)),
    "de.phone_mobile": lambda r: _spaced(r, "01" + r.choice("5675") + _d(r, r.randint(7, 9)), (4, 3, 4)),
    "es.dni": _dni,
    "es.nie": _nie,
    "es.cif": _cif,
    "es.nif_person": lambda r: r.choice([_dni, _nie])(r),
    "es.vat_person": lambda r: "ES" + r.choice([_dni, _nie])(r),
    "es.vat_company": lambda r: "ES" + _cif(r),
    "es.nss": lambda r: _spaced(r, _keyed("es.nss", f"{r.randint(0, 53):02d}" + _d(r, 8), _KEYS2), (2, 8, 2)),
    "es.phone": lambda r: _phone(r, r.choice("67895") + _d(r, 8), "34", trunk=False),
    "it.codice_fiscale": _codice_fiscale,
    "it.partita_iva": _partita_iva,
    "it.vat": lambda r: "IT" + _partita_iva(r),
    "it.phone": lambda r: _phone(r, "0" + r.choice("123456789") + _d(r, r.randint(4, 9)), "39", trunk=False),
    "it.phone_mobile": lambda r: _phone(r, "3" + r.choice("1234567890") + _d(r, r.randint(7, 8)), "39", trunk=False),
    "lu.matricule": _matricule,
    "lu.matricule_legacy": lambda r: _spaced(r, _matricule_date(r) + _d(r, 3), (4, 2, 2, 3)),
    "lu.tva": _lu_tva,
    "lu.rcs": lambda r: r.choice(_UPPER) + r.choice(["", " "]) + _d(r, r.randint(0, 7)),
    "lu.phone": _lu_phone,
    "mc.tva": lambda r: _fr_tva(r, "mc.tva"),
    "mc.rci": _rci,
    "mc.phone": _mc_phone,
    "nl.bsn": lambda r: _keyed("nl.bsn", _d(r, r.choice([8, 8, 7])), _KEYS1),
    "nl.btw": _btw,
    "nl.btw_person": _btw,
    "nl.btw_company": _btw,
    "nl.kvk": lambda r: _spaced(r, _d(r, r.choice([8, 8, 7, 9])), (4, 4)),
    "nl.document_number": _nl_document,
    "nl.postcode": _postcode,
    "nl.phone": lambda r: _spaced(r, "0" + r.choice("612345") + _d(r, 8), (2, 4, 4)),
    "nl.phone_mobile": lambda r: _spaced(r, "06" + _d(r, 8), (2, 4, 4)),
    "pt.nif": lambda r: _spaced(r, _nif(r), (3, 3, 3)),
    "pt.nif_person": lambda r: _spaced(r, _nif(r), (3, 3, 3)),
    "pt.nipc": lambda r: _spaced(r, _keyed("pt.nif", r.choice("56") + _d(r, 7), _KEYS1), (3, 3, 3)),
    "pt.vat_person": lambda r: "PT" + _nif(r),
    "pt.vat_company": lambda r: "PT " + _keyed("pt.nif", r.choice("5612") + _d(r, 7), _KEYS1),
    "pt.niss": lambda r: _keyed("pt.niss", r.choice("123") + _d(r, 9), _KEYS1),
    "pt.cc": _cc,
    "pt.nic": lambda r: _spaced(r, _d(r, r.randint(6, 10)), (2, 3, 3)),
    "pt.sns": lambda r: _spaced(r, _d(r, r.choice([9, 9, 8, 10])), (3, 3, 3)),
    "pt.phone": lambda r: _phone(r, _pt_phone(r), "351", trunk=False),
}

# --- Variantes : ce qu'un document ou un adversaire peut produire / what a document or an adversary produces ---

# Chiffres non ASCII de même valeur (arabes, persans, pleine chasse, mathématiques, devanagari) et chiffres
# non décimaux (« ² », « ① ») / same-value non-ASCII digits and non-decimal digits.
_FOREIGN = [[chr(0x0660 + d), chr(0x06F0 + d), chr(0xFF10 + d), chr(0x1D7CE + d), chr(0x0966 + d),
             "⁰¹²³⁴⁵⁶⁷⁸⁹"[d], "⓪①②③④⑤⑥⑦⑧⑨"[d]] for d in range(10)]
# Blancs Unicode (dont U+001C–U+001F), invisibles, marque combinante, CRLF, caractère astral.
# Unicode blanks (U+001C–U+001F included), invisibles, combining mark, CRLF, astral character.
_BLANKS = ["\x1c", "\x1d", "\x1e", "\x1f", "\xa0", "\x85", "\N{EM SPACE}", "\N{IDEOGRAPHIC SPACE}",
           "\N{NARROW NO-BREAK SPACE}", "\t", "\n", "\r\n", "\N{ZERO WIDTH SPACE}", "\N{WORD JOINER}",
           "\N{ZERO WIDTH NO-BREAK SPACE}", "\N{SOFT HYPHEN}", "\N{COMBINING ACUTE ACCENT}", "\N{GRINNING FACE}"]
# Lettres dont la casse surprend : « ſ » et « ı » deviennent S et I, « ß » SS, « ﬁ » FI, « ɤ » diffère selon
# la version d'Unicode. Letters with surprising case mappings.
_CASE_TRAPS = "ſıßﬁ\N{KELVIN SIGN}İɤǅΣéÉ"
_PREFIXES = ["+", "00", "0", "(0)", "BE", "BE ", "be", "CHE", "CHE-", "DE", "ES", "es", "IT", "LU", "MC", "NL", "PT",
             "FR", "fr", "+32 ", "+41 ", "+49 ", "+34 ", "+39 ", "+352 ", "+377 ", "+31 ", "+351 ", "+33 ", "0032 ",
             "X", "K", "Z", "1", " ", "\xa0+"]
_NOISE = _DIGITS + "ABKLSXYZabsxz .-/+()_%:@" + _CASE_TRAPS + "".join(_BLANKS) + "٣０²①"


def _variants(rng: random.Random, sample: str) -> Iterator[str]:
    """Le candidat et ses voisins : mutations, transpositions, longueurs ±1, préfixes, blancs, casse.

    The candidate and its neighbours: mutations, transpositions, lengths ±1, prefixes, blanks, case.
    """
    yield sample
    for i, c in enumerate(sample):
        head, tail = sample[:i], sample[i + 1:]
        if c in _DIGITS:
            yield from (head + d + tail for d in _DIGITS if d != c)
            yield head + rng.choice(_FOREIGN[int(c)]) + tail
        elif c.isalpha():
            yield head + rng.choice(_UPPER) + tail
            yield head + rng.choice(_CASE_TRAPS) + tail
        yield head + tail
        yield head + rng.choice(_NOISE) + c + tail
    for i in range(len(sample) - 1):
        yield sample[:i] + sample[i + 1] + sample[i] + sample[i + 2:]
    compact = sample.translate({ord(c): None for c in " .-/"})
    yield from (sample.lower(), sample.swapcase(), compact, compact + rng.choice(_NOISE), " ".join(compact))
    yield from (prefix + sample for prefix in _PREFIXES)
    for blank in _BLANKS:
        yield from (blank + sample, sample + blank, sample.replace(" ", blank), blank + compact)
    yield from (sample * 2, sample + "0" * 40, "0" * 40 + compact, "", " ", "\x1c")


def _format_aware(name: str, count: int = _CASES) -> Iterator[str]:
    """Au moins `count` candidats d'après le format du validateur / at least `count` format-aware candidates."""
    rng = random.Random(f"validators:{name}")
    produced = 0
    while produced < count:
        for candidate in _variants(rng, _FORMATS[name](rng)):
            produced += 1
            yield candidate


_NAMES = sorted(core.native_validators())


# --- Registre / registry -----------------------------------------------------------------------------------------

def test_every_pack_validator_is_native():
    """Plus aucun recognizer de motif ne reste en Python faute de validateur / no recognizer lacks its validator."""
    engine = Anonymizer(countries="all")
    referenced = {rec.validator_name for pack in engine.packs for rec in pack.recognizers
                  if isinstance(rec, PatternRecognizer) and rec.validator_name}
    assert referenced <= set(_NAMES)
    assert all(callable(resolve(name)) for name in _NAMES)
    if engine._native is not None:
        errors = [e for e in engine._native.errors if e and "valid" in e]
        assert not errors


def test_every_native_validator_has_a_format():
    assert sorted(_FORMATS) == _NAMES


# --- Différentiel par format / format-aware differential ----------------------------------------------------------

@pytest.mark.parametrize("name", _NAMES)
def test_format_aware_candidates_agree(name):
    candidates = list(_format_aware(name))
    assert len(candidates) >= _CASES
    # Le générateur produit aussi des valeurs valides / the generator also yields valid values.
    python = _python(name)
    assert any(python(c) not in (None, _RAISES) for c in candidates[:5000]), name
    _assert_agree(name, candidates)


_ADVERSARIAL = (_DIGITS + "ABCDEFHKLMNPRSTXYZabcdefklnoprsx .-/+()_:%@" + "".join(_BLANKS) + _CASE_TRAPS
                + "٣۵０𝟎²①½Ⅻ\N{COMBINING GREEK YPOGEGRAMMENI}")


@pytest.mark.parametrize("name", _NAMES)
def test_adversarial_strings_agree(name):
    @settings(max_examples=40, deadline=None)
    @given(st.lists(st.text(alphabet=_ADVERSARIAL, max_size=30) | st.text(max_size=12), min_size=1, max_size=40))
    def check(batch):
        _assert_agree(name, batch)

    check()


# --- Unicode exhaustif / exhaustive Unicode -----------------------------------------------------------------------

def _code_points(planes: int = 17) -> list[str]:
    return [chr(cp) for cp in range(planes * 0x10000) if not 0xD800 <= cp <= 0xDFFF]


def test_isspace_mirror_matches_python_over_all_unicode():
    # « c+32474123456 » est un mobile belge si et seulement si `lstrip()` efface `c` (ou si `c` est « + »).
    # "c+32474123456" is a Belgian mobile if and only if `lstrip()` removes `c` (or `c` is "+").
    chars = _code_points()
    native = {c for c in chars if core.validate("be.phone", c + "+32474123456") is not None}
    assert native == {c for c in chars if c.isspace()} | {"+"}


@pytest.mark.parametrize(("name", "template"), [
    ("fr.alnum_mixed", "{}1"), ("fr.contextual_id", "12{}34"), ("intl.mac", "{}:1a"), ("intl.email", "a@b{}"),
    ("fr.siv_plate", "A{}-123-CD"), ("intl.btc", "bc1{}w508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"),
])
def test_case_mappings_match_python_over_two_planes(name, template):
    """Casse et classes de chaque caractère des plans 0 et 1, telles que l'interpréteur les voit.

    Case and classes of every character of planes 0 and 1, as the interpreter sees them.
    """
    _assert_agree(name, [template.format(c) for c in _code_points(planes=2)])


@cache
def _case_traps() -> list[str]:
    """Pièges de casse selon cet interpréteur : `upper()` ou `lower()` change la longueur ou atteint l'ASCII.

    Case traps per this interpreter: `upper()` or `lower()` changes the length or reaches ASCII ("ﬀ" -> "FF",
    "ŉ" -> "ʼN", "K" -> "k", "ı" -> "I"…), computed rather than hand-picked.
    """
    def changes(mapped: str) -> bool:
        return len(mapped) != 1 or any(x.isascii() for x in mapped)

    return [c for c in _code_points(planes=2) if not c.isascii()
            and ((c.upper() != c and changes(c.upper())) or (c.lower() != c and changes(c.lower())))]


@pytest.mark.parametrize("name", _NAMES)
def test_interpreter_case_traps_agree(name):
    """Chaque piège de casse inséré dans des valeurs valides, ou mis à la place d'un de leurs caractères.

    Every case trap inserted into valid values, or put in place of one of their characters.
    """
    rng = random.Random(f"traps:{name}")
    traps = _case_traps()
    assert len(traps) > 100
    candidates = []
    for _ in range(8):
        sample = _valid(rng, name)
        for trap in traps:
            i = rng.randrange(len(sample) + 1)
            candidates += [sample[:i] + trap + sample[i:], sample[:i] + trap + sample[i + 1:]]
    _assert_agree(name, candidates)


@cache
def _unicode_digits() -> list[str]:
    """Chiffres et nombres Unicode selon cet interpréteur / Unicode digits and numbers per this interpreter."""
    return [c for c in _code_points() if c.isdigit() or c.isdecimal() or c.isnumeric()]


@pytest.mark.parametrize(("name", "sample"), [
    ("fr.phone", "+33 6 12 34 56 78"), ("fr.phone", "06 12 34 56 78"), ("fr.phone_overseas", "+262 692 12 34 56"),
    ("intl.digits_e164", "0044 20 7946 0958"), ("intl.iban", "FR76 3000 6000 0112 3456 7890 189"),
    ("intl.calendar_date", "03/03/1985"), ("fr.alnum_mixed", "AB"), ("fr.contextual_id", "CLT-"),
    ("intl.ipv6", "fe80::1"), ("be.phone", "0474 12 34 56"), ("nl.bsn", "11122233"), ("es.dni", "1234567Z"),
])
def test_every_unicode_digit_agrees(name, sample):
    """Chaque chiffre Unicode (décimal ou non) à chaque position / every Unicode digit at every position."""
    candidates = [sample[:i] + c + sample[i + 1:] for c in _unicode_digits() for i in range(len(sample))]
    candidates += [sample + c for c in _unicode_digits()]
    _assert_agree(name, candidates)


@pytest.mark.parametrize("part", ["3", " 3", "3 ", "+3", "03", "0_3", "3_", "_3", "0__3", "\t3\n", "\x1c3",
                                  "\N{EN QUAD}3", "\x853", "٣", "0٣", "²", "①", "\x003", "-0", "+0", "0" * 700 + "3",
                                  "0" * 5000 + "3", "9" * 25, "3\N{COMBINING ACUTE ACCENT}"],
                         ids=lambda part: ascii(part) if len(part) < 30 else f"{len(part)}-chars")
def test_calendar_date_reads_parts_with_python_int(part):
    """`int()` de Python : blancs, signe, soulignés, chiffres non ASCII, limite de 4 300 chiffres."""
    _assert_agree("intl.calendar_date", [f"{part}/03/1985", f"03/{part}/1985", f"03/03/19{part}",
                                         f"1985-03-{part}", f"{part}-03-03"])


# --- Tables parcourues en entier / tables walked exhaustively ------------------------------------------------------

def _iban_key(country: str, bban: str) -> str:
    """Clé IBAN standard (ISO 13616) : la somme MOD 97-10 passe quelle que soit la table des longueurs.

    Standard IBAN check digits: the MOD 97-10 sum holds whatever the length table says.
    """
    numeric = "".join(str(int(c, 36)) for c in bban + country + "00")
    return f"{98 - int(numeric) % 97:02d}"


def test_iban_length_table_matches_python():
    rng = random.Random(13616)
    candidates = []
    for first in _UPPER:
        for second in _UPPER:
            for length in range(5, 41):
                bban = _d(rng, length - 4)
                candidates.append(first + second + _iban_key(first + second, bban) + bban)
    _assert_agree("intl.iban", candidates)
    assert sum(resolve("intl.iban")(c) is not None for c in candidates) == len(IBAN_LENGTHS)


def test_card_network_table_matches_python():
    rng = random.Random(7812)
    candidates = []
    for prefix in range(10000):
        for length in range(13, 20):
            body = f"{prefix:04d}" + _d(rng, length - 5)
            candidates.append(next(body + k for k in _KEYS1 if luhn_ok(body + k)))
    for name in ("intl.card", "intl.card14"):
        _assert_agree(name, candidates)


def test_codice_fiscale_tables_match_python():
    """Chaque caractère permis à chaque position, avec chacune des 26 lettres de contrôle.

    Every allowed character at every position, with each of the 26 check letters.
    """
    base = "RSSMRA85T10A562S"
    candidates = [base[:position] + c + base[position + 1:15] + check
                  for position in range(15) for c in _DIGITS + _UPPER for check in _UPPER]
    _assert_agree("it.codice_fiscale", candidates)


def test_partita_iva_offices_match_python():
    candidates = [f"{head}{office:03d}{key}" for head in ("1234567", "0000001", "8123456") for office in range(1000)
                  for key in _DIGITS]
    _assert_agree("it.partita_iva", candidates)
    _assert_agree("it.vat", ["IT" + c for c in candidates[::7]])


def test_prefix_tables_match_python():
    """Préfixes des Länder (Steuernummer) et du plan portugais, sur toutes les têtes possibles.

    Land prefixes (Steuernummer) and the Portuguese plan, over every possible head.
    """
    _assert_agree("de.steuernummer", [f"{head:03d}{tail}" for head in range(1000)
                                      for tail in ("012345678", "0123456789", "123456789")])
    _assert_agree("pt.phone", [f"{head:03d}456789" for head in range(1000)])


def test_letter_tables_match_python():
    """Lettres du DNI, du NIE et du CIF : chaque reste, chaque lettre / every remainder, every letter."""
    numbers = [f"{n:08d}" for n in range(0, 2300, 7)]
    _assert_agree("es.dni", [n + c for n in numbers for c in _UPPER])
    _assert_agree("es.nie", [p + n[1:] + c for p in "XYZ" for n in numbers[::3] for c in _UPPER])
    _assert_agree("es.cif", [kind + province + "34567" + c for kind in _UPPER for province in ("00", "28")
                             for c in _DIGITS + _UPPER])


def test_alphabet_tables_match_python():
    """Alphabets des documents allemands et néerlandais, des RCS et RCI : chaque caractère ASCII à chaque position.

    German and Dutch document alphabets, RCS and RCI: every ASCII character at every position.
    """
    printable = string.printable
    for name, base in (("de.id_document", "T22000129"), ("de.id_document", "T220001293"),
                       ("nl.document_number", "SPECI2014"), ("lu.rcs", "B123456"), ("mc.rci", "99S03847"),
                       ("mc.rci", "12SC12345"), ("nl.postcode", "1234AB"), ("de.kvnr", "A123456780"),
                       ("pt.cc", "000000000ZZ4")):
        _assert_agree(name, [base[:i] + c + base[i + 1:] for i in range(len(base)) for c in printable])


# --- Année en cours, à l'horloge locale / current year, on the local clock ----------------------------------------

def test_current_year_edges_match_python():
    """Naissances autour de l'année en cours : branche 2000 du NISS, date plausible du matricule luxembourgeois.

    Births around the current year: the NISS 2000s branch, the Luxembourg matricule's plausible date.
    """
    year = date.today().year
    candidates = {"be.niss": [], "be.nn": [], "lu.matricule": [], "lu.matricule_legacy": []}
    for y in range(year - 3, year + 4):
        body = f"{y % 100:02d}0101001"
        candidates["be.niss"] += [body + k for k in _KEYS2]
        candidates["be.nn"] += [body + k for k in _KEYS2]
        head = f"{y}0101123"
        candidates["lu.matricule"] += [head + k for k in _KEYS2]
        candidates["lu.matricule_legacy"] += [head, f"{y}1231999"]
    for name, values in candidates.items():
        _assert_agree(name, values)
    assert core.validate("lu.matricule_legacy", f"{year}0101123") == f"{year}0101123"
    assert core.validate("lu.matricule_legacy", f"{year + 2}0101123") is None


# --- Appel depuis le balayage, GIL relâché / called from the scan, GIL released -----------------------------------

@pytest.mark.skipif(not _native.available(), reason="noyau Rust désactivé / Rust core disabled")
def test_scan_asks_the_interpreter_with_the_gil_released():
    """Hors ASCII, un validateur appelé par le balayage (sans GIL) reprend l'interpréteur le temps d'une question.

    Beyond ASCII, a validator called by the scan (without the GIL) takes the interpreter back for one question.
    """
    names = ["fr.alnum_mixed", "fr.phone", "intl.calendar_date", "intl.mac", "be.niss", "lu.matricule_legacy"]
    specs = [{"syntax": _native.syntax(re.compile(r"[^ ]+")), "pattern": r"[^ ]+", "flags": "", "group": 0,
              "validator": name, "tier": "A", "boundary": "none", "prefilter": None, "score": 0.9} for name in names]
    scanner = _native._core.Scanner(specs, [("g", ["ab"])], _native.unicode_tables())
    year = date.today().year
    text = (f"ɤ1 Ǆ2 +33٦١٢٣٤٥٦٧٨ 0٦12345678 ٠٣/03/1985 03/+3/1985 0a:1b:ɤc:3d:4e:5f "
            f"{year % 100:02d}010100154 {year}0101123 {year + 1}0101123")
    folded = text.lower()
    found = scanner.scan(scanner.keywords(folded), text, folded, [True] * len(names), False, "auto", False, [])
    got = {(start, end, names[index], value) for start, end, index, value, *_ in found}
    # Chaque valeur trouvée est celle de Python sur la même zone / every value found is Python's on the same span.
    assert all(resolve(name)(text[start:end]) == value for start, end, name, value in got)
    # Chaque mot entier que Python accepte est trouvé / every whole word Python accepts is found.
    words = []
    for token in text.split(" "):
        start = words[-1][1] + 1 if words else 0
        words.append((start, start + len(token)))
    expected = {(start, end, name, resolve(name)(text[start:end])) for start, end in words for name in names}
    assert {item for item in expected if item[3] is not None} <= got
    assert {(name, value) for _, _, name, value in got} >= {("fr.alnum_mixed", "ɤ1"), ("intl.calendar_date",
                                                                                          "1985-03-03")}


# --- Chiffres non décimaux dans MOD 97-10 / non-decimal digits in MOD 97-10 ---------------------------------------

def test_mod97_rejects_non_decimal_digits_in_python_and_rust():
    # « ² » est un chiffre (`isdigit`) que `int()` refuse : la référence vérifie `isdecimal` et rejette, sans
    # exception. "²" is a digit `int()` rejects: the reference checks `isdecimal` and rejects, no exception.
    assert _python("intl.iban")("FR76 3000 6000 0112 3456 7890 18²") is None
    assert core.validate("intl.iban", "FR76 3000 6000 0112 3456 7890 18²") is None
    # Chiffres décimaux non ASCII : `int()` les lit, Rust aussi / non-ASCII decimals: read by `int()`, and by Rust.
    arabic = "FR76 3000 6000 0112 3456 7890 1٨٩"
    assert core.validate("intl.iban", arabic) == resolve("intl.iban")(arabic) is not None


# --- Bout en bout, tous les pays / end to end, every country ------------------------------------------------------

_LINES = [
    ("BE", "Madame Claire Dubois, NISS {be.niss}, BIS {be.bis}, GSM {be.phone}, carte eID n° {be.eid}."),
    ("BE", "Ondernemingsnummer {be.enterprise_number}, BTW BE {be.enterprise_number}, rekening {be.bban}."),
    ("CH", "AHV-Nr. {ch.avs}, UID {ch.uid}, Telefon {ch.phone}."),
    ("DE", "Steuer-ID {de.steuer_id}, Steuernummer {de.steuernummer}, SV-Nummer {de.rvnr}, KVNR {de.kvnr}."),
    ("DE", "Personalausweis {de.id_document}, Führerschein {de.fuehrerschein}, USt-IdNr. {de.ust_idnr}, "
           "Handy {de.phone_mobile}, Telefon {de.phone}."),
    ("ES", "DNI {es.dni}, NIE {es.nie}, CIF {es.cif}, NIF IVA {es.vat_person}, Seguridad Social {es.nss}, "
           "teléfono {es.phone}."),
    ("IT", "Codice fiscale {it.codice_fiscale}, partita IVA {it.partita_iva}, P.IVA {it.vat}, cellulare "
           "{it.phone_mobile}, telefono {it.phone}."),
    ("LU", "Matricule {lu.matricule}, ancien matricule {lu.matricule_legacy}, RCS {lu.rcs}, TVA {lu.tva}, "
           "tél. {lu.phone}."),
    ("MC", "RCI {mc.rci}, TVA {mc.tva}, téléphone {mc.phone}."),
    ("NL", "BSN {nl.bsn}, btw-nummer {nl.btw_person}, btw {nl.btw_company}, KvK-nummer {nl.kvk}, paspoort "
           "{nl.document_number}, postcode {nl.postcode} Amsterdam, mobiel {nl.phone_mobile}."),
    ("PT", "NIF {pt.nif_person}, NIPC {pt.nipc}, NISS {pt.niss}, cartão de cidadão {pt.cc}, BI {pt.nic}, "
           "utente SNS {pt.sns}, telemóvel {pt.phone}."),
    ("FR", "NIR {fr.nir}, SIRET {fr.siret}, TVA {fr.tva}, tél. {fr.phone}, IBAN {intl.iban}, né le "
           "{intl.calendar_date}."),
]


def _valid(rng: random.Random, name: str) -> str:
    """Une valeur que la référence accepte (au plus 200 essais) / a value the reference accepts."""
    for _ in range(200):
        value = _FORMATS[name](rng)
        if resolve(name)(value) is not None:
            return value
    return value


# Colonnes de tableau : l'en-tête sert de contexte à sa colonne / table columns: the header is their context.
_COLUMNS = [("NISS", "be.niss"), ("BSN", "nl.bsn"), ("Steuer-ID", "de.steuer_id"), ("DNI", "es.dni"),
            ("Codice fiscale", "it.codice_fiscale"), ("Matricule", "lu.matricule"), ("NIF", "pt.nif_person"),
            ("AHV-Nr.", "ch.avs"), ("Téléphone", "be.phone"), ("TVA", "lu.tva"), ("BCE", "be.enterprise_number"),
            ("NIE", "es.nie"), ("KvK", "nl.kvk"), ("SNS", "pt.sns"), ("NSS", "es.nss"),
            ("Partita IVA", "it.partita_iva")]


def _table(rng: random.Random) -> str:
    columns = rng.sample(_COLUMNS, rng.randint(2, 5))
    head = ["| Nom | " + " | ".join(header for header, _ in columns) + " |", "|---" * (len(columns) + 1) + "|"]
    rows = [f"| Agent {row} | " + " | ".join(_valid(rng, name) for _, name in columns) + " |"
            for row in range(rng.randint(2, 8))]
    return "\n".join(head + rows)


def _document(rng: random.Random) -> str:
    """Lignes de plusieurs pays, parfois un tableau Markdown, parfois en CRLF / lines from several countries."""
    def fill(line: str) -> str:
        # Ordre fixe (le plus long nom d'abord) : même document pour une même graine, d'un processus à l'autre.
        # Fixed order (longest name first): the same document for the same seed, from one process to the next.
        for name in sorted(_FORMATS, key=lambda name: (-len(name), name)):
            while "{" + name + "}" in line:
                line = line.replace("{" + name + "}", _valid(rng, name), 1)
        return line

    lines = rng.sample(_LINES, rng.randint(1, len(_LINES)))
    text = "\n".join(fill(line) for _, line in lines)
    if rng.random() < 0.4:
        text += "\n\n" + _table(rng) + "\n"
    return text.replace("\n", "\r\n") if rng.random() < 0.2 else text


def _fields(span) -> tuple:
    return (span.start, span.end, span.entity, span.label, span.source, span.value, round(span.score, 9),
            span.priority, span.personal, span.forms, span.propagate)


def _spans(engine: Anonymizer, text: str) -> list[tuple]:
    return [_fields(s) for s in engine.analyze(text).spans]


def _report(report: dict) -> dict:
    """Rapport sans ce qui dépend du moteur choisi (drapeau `native`, durées) / without engine-dependent keys."""
    return {key: value for key, value in report.items() if key not in ("native", "timings_ms")}


# Expressions de chaînes seulement : littéraux, f-chaînes, noms déjà lus, n-uplets, concaténations.
# String expressions only: literals, f-strings, names already read, tuples, concatenations.
_STRING_NODES = (ast.Expression, ast.Constant, ast.JoinedStr, ast.FormattedValue, ast.Name, ast.Load, ast.Tuple,
                 ast.BinOp, ast.Add)


def _string_constants(path: Path) -> dict[str, object]:
    """Constantes de chaînes d'un module de test, évaluées sans l'importer ni rien exécuter d'autre.

    String constants of a test module, evaluated without importing it or running anything else.
    """
    values: dict[str, object] = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            continue
        expression = ast.Expression(node.value)
        if all(isinstance(part, _STRING_NODES) for part in ast.walk(expression)):
            with contextlib.suppress(NameError, TypeError):
                code = compile(expression, str(path), "eval")
                values[node.targets[0].id] = eval(code, {"__builtins__": {}}, dict(values))
    return values


def _pack_samples() -> list[str]:
    """Textes de référence des tests des packs (`LETTER`, `*_DOCUMENT`, jetons valides mis bout à bout).

    The pack tests' reference texts (letters, documents, valid tokens laid end to end).
    """
    texts = []
    for path in sorted((Path(__file__).parent / "packs").glob("*.py")):
        for name, value in _string_constants(path).items():
            if (name == "LETTER" or name.endswith("_DOCUMENT")) and isinstance(value, str):
                texts.append(value)
            elif name.endswith("_TOKENS") and isinstance(value, tuple):
                texts.append(" ".join(map(str, value)))
    return texts


_ENGINE_NATIVE = pytest.mark.skipif(not _native.available(), reason="noyau Rust désactivé / Rust core disabled")


@_ENGINE_NATIVE
@pytest.mark.parametrize("countries", ["all", "auto"])
@pytest.mark.parametrize("profile", ["standard", "strict"])
def test_pack_sample_texts_identical(countries, profile):
    native = Anonymizer(countries=countries, profile=profile, explain=True)
    python = Anonymizer(countries=countries, profile=profile, explain=True, native=False)
    samples = _pack_samples()
    assert len(samples) >= 10
    for text in samples:
        assert _spans(native, text) == _spans(python, text), text
        left, right = native.anonymize(text), python.anonymize(text)
        assert left.text == right.text
        assert _report(left.report) == _report(right.report)


@pytest.fixture(scope="module")
def all_countries():
    if not _native.available():
        pytest.skip("noyau Rust désactivé / Rust core disabled")
    native = Anonymizer(countries="all", explain=True)
    python = Anonymizer(countries="all", explain=True, native=False)
    assert native.native and not python.native
    return native, python


def test_multi_country_documents_identical(all_countries):
    native, python = all_countries
    rng = random.Random(2026)
    for _ in range(60):
        text = _document(rng)
        assert _spans(native, text) == _spans(python, text), text
        left, right = native.anonymize(text), python.anonymize(text)
        assert left.text == right.text
        assert _report(left.report) == _report(right.report)
        assert left.report["explain"]


def test_spreadsheet_columns_identical(all_countries):
    """Cellules d'une colonne sous son en-tête (contexte forcé), valeurs valides et voisines.

    Cells of a column under its header (forced context), valid and neighbouring values.
    """
    native, python = all_countries
    rng = random.Random(1904)
    for header, name in _COLUMNS:
        cells = [header] + [_valid(rng, name) for _ in range(6)] + [_FORMATS[name](rng) for _ in range(6)]
        results = []
        for engine in (native, python):
            forced = [frozenset()] + [engine.context_groups(header)] * (len(cells) - 1)
            per_cell, _ = engine.analyze_segments(cells, forced)
            results.append([[_fields(s) for s in spans] for spans in per_cell])
        assert results[0] == results[1], header


@settings(max_examples=60, deadline=None)
@given(st.integers(0, 2**32), st.lists(st.text(alphabet="".join(sorted(set(_ADVERSARIAL))), max_size=20), max_size=6))
def test_mutated_multi_country_documents_identical(all_countries, seed, noise):
    """Documents dont les identifiants sont mutés et bruités / documents with mutated, noisy identifiers."""
    native, python = all_countries
    rng = random.Random(seed)
    words = _document(rng).split(" ")
    for i, word in enumerate(words):
        if any(c.isdigit() for c in word) and rng.random() < 0.3:
            words[i] = rng.choice(list(_variants(rng, word)))
    for chunk in noise:
        words.insert(rng.randrange(len(words) + 1), chunk)
    text = " ".join(words)
    assert _spans(native, text) == _spans(python, text)
    assert native.anonymize(text).text == python.anonymize(text).text


@_ENGINE_NATIVE
@pytest.mark.parametrize(("countries", "text"), [
    ("PT", "Telemóvel:\x1c912 345 678"),                                       # `\s` : U+001C
    ("PT", "NISS\x1d12345678902"),                                             # `\s` : U+001D
    ("PT", "BI\x1f12345678"),                                                  # `\s` : U+001F
    ("ES", "NSS\x1e28 12345678 40"),                                           # `\s` : U+001E
    # `(?i)` : « İ » vaut « i » pour `re` / "İ" equals "i" for `re`.
    ("ES", "M\N{LATIN CAPITAL LETTER O WITH ACUTE}V\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}L 612 345 678"),
])
def test_labelled_patterns_follow_python_classes(countries, text):
    """`\\s` et `(?i)` des motifs étiquetés suivent `re` (U+001C–U+001F, « İ », « ı ») avec Rust comme sans.

    Pattern `\\s` and `(?i)` of the labelled recognizers follow `re` with and without Rust: PT_PHONE_LABELED,
    PT_NISS_LABELED, PT_NIC_LABELED, ES_NSS_LABELED, ES_PHONE_LABELED.
    """
    native, python = Anonymizer(countries=countries), Anonymizer(countries=countries, native=False)
    assert _spans(native, text) == _spans(python, text)
