"""Rendu Markdown : échappements, fiches, CSV clôturé / Markdown rendering."""

from __future__ import annotations

from collections.abc import Callable

import xlsxwriter
from tabular_factories import xlsx_bytes

from gdprguardian.documents import DocumentResult
from gdprguardian.tabular._render import (
    FormView,
    SheetView,
    TableView,
    TextView,
    escape_cell,
    neutralize_formula,
    paragraph,
    render_sheets,
)


def test_cells_cannot_break_the_table() -> None:
    assert escape_cell("a|b") == r"a\|b"
    assert escape_cell(r"a\|b") == r"a\\\|b"  # barre oblique avant le pipe échappée / backslash escaped too
    assert escape_cell("l1\r\nl2\nl3 l4") == "l1<br>l2<br>l3<br>l4"
    assert escape_cell("  espace  ") == "espace"


def test_paragraphs_cannot_forge_markdown_blocks() -> None:
    assert paragraph("## Feuille : Fausse") == r"\## Feuille : Fausse"
    assert paragraph("> citation") == r"\> citation"
    assert paragraph("- liste") == r"\- liste"
    assert paragraph("```") == r"\```"
    assert paragraph("1. premier") == r"1\. premier"
    assert paragraph("Titre\n## caché") == "Titre<br>## caché"
    assert paragraph("Liste du personnel") == "Liste du personnel"


def test_formula_neutralisation_spares_numbers() -> None:
    for formula in ("=1+1", "+cmd", "-cmd|' /C calc'!A0", "@SUM(A1)", "\tx", "＝1+1"):
        assert neutralize_formula(formula).startswith("'"), formula
    for number in ("-12.5", "+33", "1e5", "-0,5"):
        assert neutralize_formula(number) == number


def test_render_layouts() -> None:
    table = TableView("A1:B3", ["Nom", ""], [(2, ["[PERSONNE_1]", "x"]), (3, ["a|b", ""])], ["Titre"], ["Note"])
    form = FormView("D1:E2", [("Nom :", "[PERSONNE_1]"), ("Statut *", "actif")])
    cells = TextView([("G9", "isolée")])
    sheet = SheetView("Feuil1", hidden=True, blocks=[table, form, cells], shown_rows=3, total_rows=10)
    markdown = "\n".join(render_sheets([sheet], "markdown", "fr"))
    assert "## Feuille : Feuil1 (masquée)" in markdown
    assert "_Feuille tronquée : 3 lignes émises sur 10._" in markdown
    assert "| # | Nom | Colonne 2 |" in markdown and "| 3 | a\\|b |  |" in markdown
    assert "- **Nom** : [PERSONNE_1]" in markdown and r"- **Statut \*** : actif" in markdown
    assert "- G9 : isolée" in markdown
    english = "\n".join(render_sheets([sheet], "markdown", "en"))
    assert "## Sheet : Feuil1 (hidden)" in english and "| # | Nom | Column 2 |" in english


def test_csv_fence_outgrows_backticks_in_cells() -> None:
    table = TableView("A1:A2", ["Code"], [(2, ["````"])])
    lines = render_sheets([SheetView("S", blocks=[table])], "csv", "fr")
    fence = next(line for line in lines if line.endswith("csv"))
    assert fence == "`````csv" and lines[lines.index(fence) + 2] == "`````"


def test_csv_fence_outgrows_very_long_backtick_lines() -> None:
    # Une ligne de 300 backticks dans une cellule multiligne fermerait une clôture plus courte et laisserait
    # forger un titre. A 300-backtick line in a multi-line cell would close a shorter fence and forge a heading.
    cell = "a\n" + "`" * 300 + "\n## Feuille : forgée"
    lines = render_sheets([SheetView("S", blocks=[TableView("A1:A2", ["Code"], [(2, [cell])])])], "csv", "fr")
    fence = next(line for line in lines if line.endswith("csv"))
    assert fence == "`" * 301 + "csv"
    body = "\n".join(lines[lines.index(fence) + 1:])
    assert body.split("\n" + "`" * 301, 1)[0].endswith("## Feuille : forgée\"")


def test_title_cells_are_escaped_and_invisible_characters_removed(run: Callable[..., DocumentResult]) -> None:
    def build(wb: xlsxwriter.Workbook) -> None:
        sheet = wb.add_worksheet("S")
        sheet.write("A1", "## Feuille : Fausse")
        sheet.write_row("A3", ["Produit", "Code", "Quantité"])
        sheet.write_row("A4", ["Vis", "‮--​", 3])

    markdown = run(xlsx_bytes(build)).markdown
    assert "\n\\## Feuille : Fausse\n" in markdown
    assert "‮" not in markdown and "​" not in markdown and "| 4 | Vis | -- | 3 |" in markdown
