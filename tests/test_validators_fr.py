"""Validateurs France : tests différentiels contre python-stdnum (oracle de test uniquement, LGPL).

French validators: differential tests against python-stdnum (test-only oracle, LGPL, never shipped).
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.fr import nif as std_nif
from stdnum.fr import nir as std_nir
from stdnum.fr import siren as std_siren
from stdnum.fr import siret as std_siret
from stdnum.fr import tva as std_tva

from gdprguardian.validators import fr

digits = st.text(alphabet="0123456789", min_size=1, max_size=1)


def _nir_key(body13: str) -> str:
    converted = body13[:5] + {"2A": "19", "2B": "18"}.get(body13[5:7], body13[5:7]) + body13[7:]
    return f"{97 - int(converted) % 97:02d}"


@st.composite
def nir_bodies(draw):
    sex = draw(st.sampled_from("123478"))
    year = draw(st.integers(0, 99))
    month = draw(st.integers(1, 99))
    dept = draw(st.sampled_from(["75", "13", "2A", "2B", "97", "99", "01"]))
    rest = draw(st.text(alphabet="0123456789", min_size=6, max_size=6))
    return f"{sex}{year:02d}{month:02d}{dept}{rest}"


@settings(max_examples=300)
@given(nir_bodies())
def test_nir_matches_stdnum(body):
    value = body + _nir_key(body)
    assert fr.nir(value) == value
    assert std_nir.is_valid(value)
    wrong = value[:-1] + str((int(value[-1]) + 1) % 10)
    assert fr.nir(wrong) is None
    assert not std_nir.is_valid(wrong)


def test_nir_published_example_and_separators():
    assert fr.nir("2 69 05 49 588 157 80") == "269054958815780"
    assert fr.nir("2.69.05.49.588.157.80") == "269054958815780"
    assert fr.nir("2-69-05-49-588-157-81") is None
    assert fr.nir("5 69 05 49 588 157 80") is None


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=10, max_size=10).filter(lambda s: s[0] in "0123"))
def test_spi_matches_stdnum(body):
    value = body + f"{int(body) % 511:03d}"
    assert fr.spi(value) == value
    assert std_nif.is_valid(value)


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9))
def test_siren_matches_stdnum(value):
    assert (fr.siren(value) is not None) == (std_siren.is_valid(value) and value != "000000000")


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=14, max_size=14))
def test_siret_matches_stdnum(value):
    assert (fr.siret(value) is not None) == std_siret.is_valid(value)


def test_siret_la_poste():
    assert fr.siret("35600000049837") == "35600000049837"
    assert std_siret.is_valid("35600000049837")
    assert fr.siret("35600000000048") == "35600000000048"


@settings(max_examples=200)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9))
def test_tva_numeric_matches_stdnum(siren):
    key = (12 + 3 * (int(siren) % 97)) % 97
    value = f"FR{key:02d}{siren}"
    assert (fr.tva(value) is not None) == std_tva.is_valid(value)


@pytest.mark.parametrize("value", ["FRK7399859412", "FR4Z123456782", "FR11 732 829 320"])
def test_tva_agrees_with_stdnum(value):
    assert (fr.tva(value) is not None) == std_tva.is_valid(value)


def test_rib_key():
    bank, branch, account = "30006", "00001", "12345678901"
    key = 97 - (89 * int(bank) + 15 * int(branch) + 3 * int(account)) % 97
    assert fr.rib(f"{bank} {branch} {account} {key:02d}") is not None
    assert fr.rib(f"{bank} {branch} {account} {(key % 97) + 1:02d}") is None


def test_phone_canonical():
    assert fr.phone("06 12 34 56 78") == "+33612345678"
    assert fr.phone("+33 6 12 34 56 78") == "+33612345678"
    assert fr.phone("+33 (0)6 12 34 56 78") == "+33612345678"
    assert fr.phone("0033612345678") == "+33612345678"


def test_siv_plate():
    assert fr.siv_plate("AB-123-CD") == "AB123CD"
    assert fr.siv_plate("SS-123-CD") is None
    assert fr.siv_plate("AB-000-CD") is None
    assert fr.siv_plate("AI-123-CD") is None
