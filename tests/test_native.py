"""Noyau Rust : sorties identiques à la référence Python / Rust core: outputs identical to the Python reference."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gdprguardian.validators import resolve

core = pytest.importorskip("gdprguardian_core")

_DIGITS = "0123456789"
_SEPARATORS = " .-/"
_ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"

# Alphabets d'entrée réalistes par validateur / realistic input alphabets per validator.
_ALPHABETS = {
    "fr.nir": _DIGITS + "ABab" + _SEPARATORS,
    "fr.nir_without_key": _DIGITS + "AB" + _SEPARATORS,
    "fr.spi": _DIGITS + _SEPARATORS,
    "fr.siren": _DIGITS + " ",
    "fr.siret": _DIGITS + " ",
    "fr.tva": "FR" + _DIGITS + "ABCHKZ" + " ",
    "fr.rib": _DIGITS + "AJSZ" + " ",
    "fr.luhn_digits": _DIGITS + " ",
    "fr.finess": _DIGITS + "AB ",
    "fr.siv_plate": "ABCDISUOW" + _DIGITS + "-",
    "fr.alnum_mixed": _ALNUM,
    "fr.contextual_id": _ALNUM + _SEPARATORS,
    "fr.phone_field": _DIGITS + "+() ./-",
    "fr.phone": _DIGITS + "+() .",
    "fr.phone_overseas": _DIGITS + "+ ",
    "fr.eori": "FR" + _DIGITS,
    "intl.iban": "FRDEGB" + _DIGITS + "ABCWEST ",
    "intl.card": _DIGITS + " -",
    "intl.card14": "0123689 -",
    "intl.imei": _DIGITS + " -",
    "intl.ipv4": _DIGITS + ".",
    "intl.ipv6": "0123456789abcdefABCDEF:",
    "intl.mac": "0123456789abcdefABCDEF:-",
    "intl.btc": "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyzbc",
    "intl.eth": "0x123456789abcdefABCDEF",
    "intl.email": "abcXYZ.@-_12",
    "intl.digits_e164": _DIGITS + "+ ",
    "intl.calendar_date": _DIGITS + "/.-",
}

_KNOWN = [
    ("fr.nir", "2 69 05 49 588 157 80"), ("fr.nir", "2 69 05 2A 004 123 14"), ("fr.siret", "35600000049837"),
    ("fr.tva", "FR44 732829320"), ("intl.iban", "FR76 3000 6000 0112 3456 7890 189"),
    ("intl.card", "4111 1111 1111 1111"), ("intl.card", "3056 9309 0259 04"),
    ("intl.card14", "3056 9309 0259 04"), ("intl.card14", "4111 1111 1111 1111"),
    ("intl.eth", "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"),
    ("intl.btc", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"),
    ("intl.btc", "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0"),
    ("intl.ipv6", "2001:0db8:0000:0000:0000:ff00:0042:8329"), ("intl.ipv6", "fe80::1:0:0:1"),
    ("fr.phone", "+33 (0)6 12 34 56 78"), ("intl.calendar_date", "29/02/2024"),
    ("intl.calendar_date", "29/02/2023"), ("intl.email", "Jean.Dupont@Exemple.FR"),
]


def test_native_list_matches_python_registry():
    for name in core.native_validators():
        assert callable(resolve(name))


@pytest.mark.parametrize(("name", "value"), _KNOWN)
def test_known_values(name, value):
    assert core.validate(name, value) == resolve(name)(value)


@pytest.mark.parametrize("name", sorted(_ALPHABETS))
def test_random_inputs_agree(name):
    python_validator = resolve(name)

    @settings(max_examples=400, deadline=None)
    @given(st.text(alphabet=_ALPHABETS[name], min_size=0, max_size=45))
    def check(candidate):
        assert core.validate(name, candidate) == python_validator(candidate)

    check()


@settings(max_examples=300, deadline=None)
@given(st.integers(min_value=0, max_value=2**128 - 1))
def test_ipv6_compression_agrees(number):
    import ipaddress

    text = ipaddress.IPv6Address(number).exploded
    assert core.validate("intl.ipv6", text) == resolve("intl.ipv6")(text)
