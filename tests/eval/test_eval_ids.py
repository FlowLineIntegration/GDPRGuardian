"""Générateurs d'identifiants : validité croisée moteur + python-stdnum (oracle de test uniquement).

Identifier generators: cross-checked against the engine validators and python-stdnum (LGPL, used here
as a test oracle only, never imported from src/).
"""

from __future__ import annotations

from random import Random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum import ean, iban, luhn
from stdnum.fr import nif, nir, siren, siret, tva
from tools.eval import ids

from gdprguardian._text import strip_separators
from gdprguardian.validators import fr as fr_validators
from gdprguardian.validators import intl as intl_validators

SEEDS = range(300)
PLACES = ("75056", "2A004", "2B033", "97105", "97411", "99350", "13055", "69123")


def _flip_digit(value: str, position: int) -> str:
    digit = value[position]
    return value[:position] + str((int(digit) + 1) % 10) + value[position + 1:]


def test_luhn_digit_matches_oracle():
    for seed in SEEDS:
        body = ids.digits(Random(seed), 1 + seed % 18)
        assert luhn.calc_check_digit(body) == ids.luhn_digit(body)


@pytest.mark.parametrize("sex", "123478")
def test_nir_extended_ranges_are_valid(sex):
    # Mois réels, fictifs (20-42), état civil incomplet (50-99) ; Corse, DOM, étranger.
    for seed in SEEDS:
        rng = Random(seed)
        month = rng.choice((rng.randint(1, 12), rng.randint(20, 42), rng.randint(50, 99)))
        value = ids.nir(rng, sex, rng.randint(1900, 2025), month, rng.choice(PLACES))
        assert nir.is_valid(value), value
        assert fr_validators.nir(ids.fmt_nir(value, "spaced")) == value
        assert fr_validators.nir(ids.fmt_nir(value, "key_apart")) == value


def test_nir_corsica_uses_19_and_18():
    assert ids.nir_key("185052A004084") == f"{97 - 1850519004084 % 97:02d}"
    assert ids.nir_key("185052B004084") == f"{97 - 1850518004084 % 97:02d}"
    # Vecteurs de la documentation python-stdnum / python-stdnum doctest vectors.
    assert ids.nir_key("253072B073004") == "70"
    assert ids.nir_key("253072A073004") == "43"


def test_siren_siret_vat():
    for seed in SEEDS:
        rng = Random(seed)
        siren_value = ids.siren(rng)
        siret_value = ids.siret(rng, siren_value)
        vat_value = ids.vat_fr(siren_value)
        assert siren.is_valid(siren_value) and fr_validators.siren(siren_value) == siren_value
        assert siret.is_valid(siret_value) and fr_validators.siret(ids.fmt_siret(siret_value, "spaced"))
        assert tva.is_valid(vat_value) and fr_validators.tva(ids.fmt_vat(vat_value, "grouped")) == vat_value


def test_la_poste_siret_exception():
    values = [ids.siret_la_poste(Random(seed)) for seed in SEEDS]
    assert all(siret.is_valid(v) and fr_validators.siret(v) == v for v in values)
    assert ids.LA_POSTE_HEAD_OFFICE not in values
    # L'exception est bien exercée : la plupart ne passent pas Luhn / the exception is exercised.
    assert sum(not luhn.is_valid(v) for v in values) > len(values) // 2


def test_rib_key_and_iban():
    for seed in SEEDS:
        rib_value = ids.rib(Random(seed))
        assert fr_validators.rib(ids.fmt_rib(rib_value, "spaced")) == rib_value
        # Oracle indépendant : forme concaténée de la clé RIB / independent concatenated-form oracle.
        converted = "".join(str(ids._rib_value(c)) for c in rib_value[:21])
        assert int(rib_value[21:]) == 97 - int(converted + "00") % 97
        iban_value = ids.iban_fr(rib_value)
        assert iban.is_valid(iban_value)
        assert intl_validators.iban(ids.fmt_iban(iban_value, "spaced")) == iban_value


def test_rib_with_letters_is_exercised():
    assert any(not ids.rib(Random(seed))[10:21].isdigit() for seed in SEEDS)


def test_foreign_iban_valid_with_national_checks():
    for seed in SEEDS:
        value = ids.iban_foreign(Random(seed))
        assert iban.is_valid(value), value  # stdnum vérifie aussi les clés nationales BE/ES / also BE/ES keys


def test_cards_spi_rpps_finess_ean():
    for seed in SEEDS:
        rng = Random(seed)
        card = ids.card(rng)
        assert luhn.is_valid(card) and intl_validators.card(ids.fmt_card(card, "spaced")) == card
        spi = ids.spi(rng)
        assert nif.is_valid(spi) and fr_validators.spi(ids.fmt_spi(spi, "spaced")) == spi
        assert luhn.is_valid(ids.rpps(rng))
        assert fr_validators.finess(ids.finess(rng)) is not None
        assert ean.is_valid(ids.ean13(rng))


def test_phones_and_plates_validate():
    styles = ("spaced", "dots", "dashes", "compact", "intl", "intl_paren", "intl_compact", "intl_00")
    for seed in SEEDS:
        rng = Random(seed)
        national = ids.phone_fr(rng, mobile=seed % 2 == 0)
        expected = "+33" + national[1:]
        for style in styles:
            assert fr_validators.phone(ids.fmt_phone(national, style)) == expected, style
        dom = ids.phone_dom(rng)
        assert fr_validators.phone_overseas(ids.fmt_phone(dom, "dom_intl")) is not None
        plate = ids.plate_siv(rng)
        assert fr_validators.siv_plate(ids.fmt_plate(plate, "dashes")) == plate
        assert not set(plate) & set("IOU")


def test_formats_round_trip():
    rng = Random(7)
    value = ids.nir(rng, "2", 1985, 5, "75056")
    for style in ("spaced", "compact", "key_apart"):
        assert strip_separators(ids.fmt_nir(value, style)) == value
    iban_value = ids.iban_fr(ids.rib(rng))
    assert strip_separators(ids.fmt_iban(iban_value, "spaced")) == iban_value


@settings(max_examples=150, deadline=None, derandomize=True)
@given(seed=st.integers(0, 2**32 - 1), position=st.integers(0, 12))
def test_single_digit_change_is_rejected(seed, position):
    rng = Random(seed)
    nir_value = ids.nir(rng, "1", 1980, 7, "75056")
    if nir_value[position].isdigit():
        assert not nir.is_valid(_flip_digit(nir_value, position))
        assert fr_validators.nir(_flip_digit(nir_value, position)) is None
    siret_value = ids.siret(rng, ids.siren(rng))
    assert not siret.is_valid(_flip_digit(siret_value, position))
    iban_value = ids.iban_fr(ids.rib(rng))
    flipped = _flip_digit(iban_value, 4 + position) if iban_value[4 + position].isdigit() else None
    if flipped:
        assert not iban.is_valid(flipped)
