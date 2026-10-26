"""Lecture : encodages, séparateurs, CSV irréguliers, limites / reading: encodings, delimiters, caps."""

from __future__ import annotations

import pytest

from gdprguardian.documents import DocumentError, DocumentOptions
from gdprguardian.tabular._reader import MAX_COLUMNS, decode_text, read_delimited, sniff_delimiter

FRENCH = "Nom;Prénom;Ville\nLefèvre;Hélène;Évreux\nGarçon;Noël;Nîmes\n"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "cp1252"])
def test_french_text_round_trips(encoding: str) -> None:
    assert decode_text(FRENCH.encode(encoding)) == FRENCH


def test_short_cp1252_is_not_mistaken_for_cp1250() -> None:
    assert decode_text("Nom;Prénom\nHélène;Zoé\n".encode("cp1252")) == "Nom;Prénom\nHélène;Zoé\n"


def test_bom_is_stripped() -> None:
    assert decode_text("﻿Nom;Ville\n".encode()) == "Nom;Ville\n"


@pytest.mark.parametrize(("text", "expected"), [
    ("Nom;Montant\nDupont;1,5\nMartin;2,25\n", ";"),
    ('Nom;Montant\n"Dupont, Jean";"1 234,56"\n"Martin";"12,5"\n', ";"),
    ("Nom\tVille\nDupont\tLyon\n", "\t"),
    ("Nom,Ville\nDupont,Lyon\nMartin,Paris\n", ","),
    ("Nom|Ville\nDupont|Lyon\n", "|"),
    ("Nom\nDupont\nMartin\n", ","),
])
def test_delimiter_sniffing(text: str, expected: str) -> None:
    assert sniff_delimiter(text) == expected


def test_ragged_rows_are_padded_and_multiline_fields_kept() -> None:
    data = b'Nom;Commentaire;Ville\nDupont;"ligne 1\nligne 2"\nMartin;ok;Lyon;extra\n'
    result = read_delimited(data, "csv", "export", DocumentOptions())
    [sheet] = result.sheets
    assert sheet.rows[1] == ["Dupont", "ligne 1\nligne 2", "", ""]
    assert all(len(row) == 4 for row in sheet.rows) and sheet.total_rows == 3


def test_row_and_cell_caps() -> None:
    data = "".join(f"v{i};w{i}\n" for i in range(100)).encode()
    capped = read_delimited(data, "csv", "x", DocumentOptions(max_rows_per_sheet=10)).sheets[0]
    assert len(capped.rows) == 10 and capped.total_rows == 100
    limited = read_delimited(data, "csv", "x", DocumentOptions(max_cells=20))
    assert len(limited.sheets[0].rows) == 10 and limited.cell_limit_reached


def test_wide_rows_are_cut_and_padding_honours_the_cell_budget() -> None:
    wide = ";".join(["x"] * 20_000) + "\n" + "a\n" * 50
    result = read_delimited(wide.encode(), "csv", "x", DocumentOptions())
    sheet = result.sheets[0]
    assert sheet.width == MAX_COLUMNS and result.skipped["truncated_rows"] == 1
    assert len(sheet.rows) == 51 and not result.cell_limit_reached
    # Une ligne large puis des lignes courtes : la grille complétée reste sous max_cells.
    # One wide row then short ones: the padded grid stays under max_cells.
    padded = read_delimited(wide.encode(), "csv", "x", DocumentOptions(max_cells=100_000))
    assert len(padded.sheets[0].rows) * padded.sheets[0].width <= 100_000 and padded.cell_limit_reached
    first_only = read_delimited(b"a;b;c;d;e\n1;2;3;4;5\n", "csv", "x", DocumentOptions(max_cells=3))
    assert first_only.sheets[0].rows == [["a", "b", "c"]] and first_only.cell_limit_reached


def test_worker_reply_round_trips_and_is_shape_checked() -> None:
    import datetime as dt
    import json

    from gdprguardian.tabular._package import Package, TableSpec
    from gdprguardian.tabular._reader import RawSheet, ReadResult, _decode, _encode

    values = ["x", 1.5, 7, True, None, dt.datetime(2024, 1, 2, 3, 4, 5), dt.date(1985, 3, 14), dt.time(8, 30),
              dt.timedelta(days=2, seconds=5)]
    sheet = RawSheet("S", [values], 1, 2, 3, True, [(0, 0, 0, 1)], [TableSpec(0, 0, 1, 1, 1, 0, ("Nom",))])
    reply = json.loads(json.dumps(_encode(Package("xlsx"), ReadResult([sheet]))))
    package, read = _decode(reply)
    assert package.kind == "xlsx" and read.sheets[0].rows == [values]
    assert read.sheets[0].tables == sheet.tables and read.sheets[0].merged == [(0, 0, 0, 1)]
    for broken in ({}, {**reply, "sheets": [["S", [[1], [1, 2]], 0, 0, 0, False, [], []]]},
                   {**reply, "sheets": [["S", [[{"zz": 1}]], 0, 0, 0, False, [], []]]},
                   {**reply, "sheets": [["S", [[{"td": [10 ** 12, 0, 0]}]], 0, 0, 0, False, [], []]]}):
        with pytest.raises(DocumentError):
            _decode(broken)


def test_oversized_field_is_a_safe_error() -> None:
    data = ("Nom;Note\nDupont;" + "x" * 200_000 + "\n").encode()
    with pytest.raises(DocumentError) as error:
        read_delimited(data, "csv", "x", DocumentOptions())
    assert "Dupont" not in str(error.value)
