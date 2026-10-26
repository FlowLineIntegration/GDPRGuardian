"""Valeurs de cellules : texte canonique, zéros initiaux, préfiltres / cell values."""

from __future__ import annotations

import datetime as dt

import pytest

from gdprguardian.tabular._values import (
    column_letter,
    float_text,
    is_null_marker,
    kind_of,
    may_hold_identifier,
    pad_fixed_width,
    to_text,
)


@pytest.mark.parametrize(("value", "expected"), [
    (42.0, "42"),
    (-7.0, "-7"),
    (0.1 + 0.2, "0.3"),  # 15 chiffres significatifs, comme Excel / 15 significant digits, as Excel
    (1234.5, "1234.5"),
    (185057800608491.0, "185057800608491"),  # NIR stocké en nombre : exact / NIR stored as a number: exact
    (4111111111111111.0, "4111111111111111"),  # 16 chiffres < 2**53 : exact
    (4.11111111111111e18, "4111111111111110000"),  # carte tronquée par Excel / card truncated by Excel
    (1e300, "1e+300"),
])
def test_float_text_matches_excel_display(value: float, expected: str) -> None:
    assert float_text(value) == expected


def test_to_text_covers_every_calamine_type() -> None:
    assert to_text("  ") == ""
    assert to_text("Dupont") == "Dupont"
    assert to_text(True) == "VRAI" and to_text(False, ("TRUE", "FALSE")) == "FALSE"
    assert to_text(7) == "7"
    assert to_text(dt.date(1985, 3, 14)) == "1985-03-14"
    assert to_text(dt.datetime(1985, 3, 14)) == "1985-03-14"
    assert to_text(dt.datetime(2024, 5, 6, 7, 8, 9)) == "2024-05-06 07:08:09"
    assert to_text(dt.time(13, 45, 30)) == "13:45:30"
    assert to_text(dt.timedelta(days=1, seconds=43200)) == "36:00:00"
    assert to_text(dt.timedelta(seconds=-90)) == "-0:01:30"


@pytest.mark.parametrize(("text", "label", "expected"), [
    ("1000", "POSTAL_CODE", "01000"),
    ("75001", "POSTAL_CODE", "75001"),
    ("612345678", "PHONE", "0612345678"),
    ("12345674", "SIREN", "012345674"),
    ("100", "POSTAL_CODE", "100"),  # trop court : pas un code postal / too short: left alone
    ("1000", None, "1000"),
    ("10 00", "POSTAL_CODE", "10 00"),
])
def test_leading_zeros_restored_only_for_fixed_width_headers(text: str, label: str | None, expected: str) -> None:
    assert pad_fixed_width(text, label) == expected


def test_null_markers_are_never_identifiers() -> None:
    for marker in ("n/a", "N/A", " - ", "?", "Inconnu", "néant", "NULL", "---", "x"):
        assert is_null_marker(marker), marker
    for value in ("Dupont", "06 12 34 56 78", "Xavier", "a"):
        assert not is_null_marker(value), value


def test_prefilter_skips_cells_that_cannot_hold_identifiers() -> None:
    assert may_hold_identifier("Dupont", "Dupont")
    assert may_hold_identifier(185057800608491.0, "185057800608491")
    assert not may_hold_identifier(1234.5, "1234.5")
    assert not may_hold_identifier(75001.0, "75001")
    assert not may_hold_identifier(dt.date(1985, 3, 14), "1985-03-14")
    assert not may_hold_identifier(True, "VRAI")
    assert may_hold_identifier("--", "--")  # tout texte passe par le nettoyage du moteur / all text is sanitised


def test_column_letters() -> None:
    assert [column_letter(i) for i in (0, 25, 26, 701, 702, 16383)] == ["A", "Z", "AA", "ZZ", "AAA", "XFD"]


def test_kinds() -> None:
    assert kind_of(1.0, "1") == "n"
    assert kind_of("1 234,56", "1 234,56") == "n"
    assert kind_of("14/03/1985", "14/03/1985") == "d"
    assert kind_of(dt.date(2024, 1, 1), "2024-01-01") == "d"
    assert kind_of(True, "VRAI") == "b"
    assert kind_of("Nom", "Nom") == "t"
    assert kind_of("", "") == ""
