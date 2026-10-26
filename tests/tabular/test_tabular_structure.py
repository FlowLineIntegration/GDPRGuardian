"""Structure : zones, en-têtes, formulaires, totaux / structure: regions, headers, forms, totals."""

from __future__ import annotations

import time
from typing import Any

from gdprguardian import Anonymizer
from gdprguardian.tabular._columns import ColumnTyper
from gdprguardian.tabular._package import TableSpec
from gdprguardian.tabular._structure import Region, detect_regions
from gdprguardian.tabular._values import to_text

_ANONYMIZER = Anonymizer(countries=("FR",))
_TYPER = ColumnTyper(_ANONYMIZER.packs, _ANONYMIZER.settings)


def _regions(rows: list[list[Any]], merged: list[tuple[int, int, int, int]] | None = None,
             tables: list[TableSpec] | None = None) -> list[Region]:
    width = max(len(row) for row in rows)
    raws = [row + [""] * (width - len(row)) for row in rows]
    texts = [[to_text(value) for value in row] for row in raws]
    return detect_regions(texts, raws, merged or [], tables or [],
                          lambda text: _TYPER.is_label(text, _ANONYMIZER.context_groups))


def test_simple_table_with_header() -> None:
    [region] = _regions([["Nom", "Montant"], ["Dupont", 12.5], ["Martin", 3.0]])
    assert region.kind == "table"
    assert region.headers == ["Nom", "Montant"]
    assert region.header_rows == [0] and region.data_rows == [1, 2]


def test_numeric_data_reveals_an_unknown_header() -> None:
    [region] = _regions([["Produit", "Quantité"], ["Vis", 12.0], ["Écrou", 3.0]])
    assert region.headers == ["Produit", "Quantité"]


def test_headerless_table_keeps_its_first_row_as_data() -> None:
    [region] = _regions([["Paris", "France"], ["Rome", "Italie"], ["Oslo", "Norvège"]])
    assert region.header_rows == [] and region.data_rows == [0, 1, 2]


def test_title_above_table_and_notes_below() -> None:
    rows = [["Liste du personnel", "", ""], ["", "", ""], ["Nom", "Service", "Salaire"], ["Dupont", "RH", 2100.0],
            ["Martin", "IT", 2500.0], ["Total", "", 4600.0], ["Source : paie de mars", "", ""]]
    [region] = _regions(rows)
    assert region.title_rows == [0]
    assert region.header_rows == [2]
    assert region.total_rows == {5}
    assert region.note_rows == [6]


def test_stacked_and_side_by_side_tables() -> None:
    rows = [["Nom", "Age", "", "", "Ville", "CP"], ["Dupont", 40.0, "", "", "Paris", 75001.0],
            ["", "", "", "", "Lyon", 69001.0], ["", "", "", "", "", ""], ["Email", "Statut", "", "", "", ""],
            ["a@b.fr", "actif", "", "", "", ""]]
    regions = _regions(rows)
    spans = [(region.top, region.columns) for region in regions]
    assert spans == [(0, [0, 1]), (0, [4, 5]), (4, [0, 1])]


def test_merged_two_row_header_is_joined() -> None:
    rows = [["Identité", "", "Contact"], ["Nom", "Prénom", "Email"], ["Dupont", "Jean", "j@d.fr"],
            ["Martin", "Anne", "a@m.fr"]]
    [region] = _regions(rows, merged=[(0, 0, 0, 1)])
    assert region.headers == ["Identité / Nom", "Identité / Prénom", "Contact / Email"]
    assert region.header_rows == [0, 1]


def test_two_row_header_without_merge_information_is_forward_filled() -> None:
    rows = [["Identité", "", "Contact", ""], ["Nom", "Prénom", "Email", "Tél"], ["Dupont", "Jean", "j@d.fr", "06"],
            ["Martin", "Anne", "a@m.fr", "07"]]
    [region] = _regions(rows)
    assert region.headers == ["Identité / Nom", "Identité / Prénom", "Contact / Email", "Contact / Tél"]


def test_key_value_form() -> None:
    rows = [["Nom :", "Dupont"], ["Prénom :", "Jean"], ["Date de naissance :", "14/03/1985"], ["Ville :", "Lyon"]]
    [region] = _regions(rows)
    assert region.kind == "form"
    assert region.pairs == [(0, 0, 1), (1, 0, 1), (2, 0, 1), (3, 0, 1)]


def test_two_column_table_is_not_a_form() -> None:
    rows = [["Nom", "Email"], *([f"Nom{i}", f"p{i}@x.fr"] for i in range(10))]
    [region] = _regions(rows)
    assert region.kind == "table" and region.headers == ["Nom", "Email"]


def test_excel_table_comes_first_and_masks_its_cells() -> None:
    rows = [["Note libre", "", "", "", ""], ["", "", "", "", ""], ["Nom", "Tel", "Ville", "", "à part"],
            ["Dupont", "0612345678", "Lyon", "", ""]]
    spec = TableSpec(2, 0, 3, 2, 1, 0, ("Nom", "Tel", "Ville"))
    regions = _regions(rows, tables=[spec])
    table = next(region for region in regions if region.header_rows == [2])
    assert table.headers == ["Nom", "Tel", "Ville"] and table.data_rows == [3]
    # Une cellule seule juste au-dessus devient le titre / a lone cell just above becomes the title.
    assert table.title_rows == [0]
    assert [(region.kind, region.columns) for region in regions if region is not table] == [("text", [4])]


def test_isolated_cells() -> None:
    regions = _regions([["seul", "", ""], ["", "", ""], ["", "", "autre"]])
    assert [region.kind for region in regions] == ["text", "text"]


def test_vertical_merge_links_rows_across_a_gap() -> None:
    rows = [["Nom", "Service", "Note"], ["Dupont", "RH", "x"], ["", "", ""], ["Martin", "IT", "y"]]
    assert len(_regions(rows)) == 2
    [region] = _regions(rows, merged=[(1, 2, 3, 2)])
    assert region.data_rows == [1, 2, 3]


def test_crafted_merges_stay_linear() -> None:
    # 20 000 fusions sur toute la hauteur : un balayage par ligne et par fusion serait quadratique.
    # 20,000 full-height merges: a per-row, per-merge loop would be quadratic.
    rows = [["Nom", "Ville", ""], *([f"Nom{i}", "Lyon", ""] for i in range(5_000))]
    merged = [(0, 2, 5_000, 2)] * 20_000 + [(0, 0, 0, 1)] * 20_000
    started = time.perf_counter()
    regions = _regions(rows, merged=merged)
    assert time.perf_counter() - started < 2.0
    assert len(regions) == 1


def test_overlapping_excel_tables_are_kept_once() -> None:
    rows = [["Nom", "Ville"], ["Dupont", "Lyon"], ["Martin", "Nice"]]
    spec = TableSpec(0, 0, 2, 1, 1, 0, ("Nom", "Ville"))
    inner = TableSpec(1, 1, 2, 1, 0, 0, ())
    regions = _regions(rows, tables=[spec, spec, inner])
    assert len(regions) == 1 and regions[0].data_rows == [1, 2]


def test_merge_owners_are_found_in_one_sweep() -> None:
    from gdprguardian.tabular._structure import _span_owners

    assert _span_owners([(4, 6), (0, 1), (2, 9)], range(11)) == {0: 0, 1: 0, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2,
                                                                 8: 2, 9: 2}
    assert _span_owners([], range(3)) == {}
