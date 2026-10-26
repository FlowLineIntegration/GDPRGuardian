"""Validateurs internationaux / international validators."""

from __future__ import annotations

from gdprguardian.validators import intl


def test_iban_lengths_and_checksum():
    assert intl.iban("FR76 3000 6000 0112 3456 7890 189") == "FR7630006000011234567890189"
    assert intl.iban("DE89 3704 0044 0532 0130 00") == "DE89370400440532013000"
    assert intl.iban("FR76 3000 6000 0112 3456 7890 18") is None
    assert intl.iban("FR77 3000 6000 0112 3456 7890 189") is None


def test_cards():
    assert intl.card("4111 1111 1111 1111") == "4111111111111111"
    assert intl.card("5555-5555-5555-4444") == "5555555555554444"
    assert intl.card("3782 822463 10005") == "378282246310005"
    assert intl.card("4111 1111 1111 1112") is None
    assert intl.card("1111 1111 1111 1117") is None


def test_siret_is_never_a_card():
    # Régression : un SIRET (14 chiffres, Luhn-valide par construction) passait pour une carte Visa.
    # Regression: a SIRET (14 digits, Luhn-valid by design) used to pass as a Visa card.
    from gdprguardian.validators.checksums import luhn_ok

    siret = next(f"4123456789012{d}" for d in "0123456789" if luhn_ok(f"4123456789012{d}"))
    assert intl.card(siret) is None
    # Diners à 14 chiffres : validateur séparé, exigé avec un mot-clé / separate validator, keyword required.
    assert intl.card("3056 9309 0259 04") is None
    assert intl.card14("3056 9309 0259 04") == "30569309025904"
    assert intl.card14("4111 1111 1111 1111") is None


def test_ipv4_mapped_addresses():
    assert intl.ipv6("::ffff:127.0.0.1") is None
    assert intl.ipv6("::ffff:0.0.0.0") is None
    assert intl.ipv6("::ffff:1.2.3.4") == "::ffff:102:304"


def test_ip_and_mac():
    assert intl.ipv4("192.168.1.42") == "192.168.1.42"
    assert intl.ipv4("127.0.0.1") is None
    assert intl.ipv6("2001:db8::1") == "2001:db8::1"
    assert intl.ipv6("10:20:30") is None
    assert intl.ipv6("::1") is None
    assert intl.mac("00-1A-2B-3C-4D-5E") == "00:1A:2B:3C:4D:5E"


def test_crypto():
    assert intl.btc("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert intl.eth("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
    assert intl.eth("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAeD") is None


def test_calendar_date():
    assert intl.calendar_date("03/03/1985") == "1985-03-03"
    assert intl.calendar_date("1985-03-03") == "1985-03-03"
    assert intl.calendar_date("31/02/1985") is None
