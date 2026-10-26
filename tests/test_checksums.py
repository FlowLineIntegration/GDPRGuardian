"""Sommes de contrôle : vecteurs publiés par les normes / checksums: vectors published by the standards."""

from __future__ import annotations

from gdprguardian.validators.checksums import (
    base58check_ok,
    bech32_ok,
    eip55_ok,
    icao_check_digit,
    iso7064_mod11_2_check,
    iso7064_mod11_10_ok,
    keccak256,
    luhn_ok,
    mod97_10_ok,
    verhoeff_ok,
)


def test_luhn_reference():
    assert luhn_ok("79927398713")
    assert not luhn_ok("79927398710")
    assert not luhn_ok("")


def test_mod97_iban_examples():
    for iban in ("FR7630006000011234567890189", "DE89370400440532013000", "GB82WEST12345698765432"):
        assert mod97_10_ok(iban[4:] + iban[:4])
    assert not mod97_10_ok("30006000011234567890189FR77")


def test_verhoeff_reference():
    assert verhoeff_ok("2363")
    assert not verhoeff_ok("2364")


def test_iso7064():
    # Exemple ISO 7064 MOD 11-2 (carte d'identité chinoise) / Chinese resident ID example.
    assert iso7064_mod11_2_check("11010519491231002") == "X"
    assert iso7064_mod11_10_ok("65929970489")


def test_icao_check_digit():
    # Exemple ICAO 9303 (spécimen) : L898902C3 -> 6 / ICAO specimen.
    assert icao_check_digit("L898902C3") == 6
    assert icao_check_digit("740812") == 2


def test_keccak256_empty():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_eip55_reference():
    assert eip55_ok("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
    assert not eip55_ok("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAeD")
    assert eip55_ok("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed")


def test_bitcoin_addresses():
    assert base58check_ok("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert not base58check_ok("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb")
    assert bech32_ok("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    assert bech32_ok("bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0")
    assert not bech32_ok("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5")
