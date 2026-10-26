"""Rendu Markdown des feuilles anonymisées / Markdown rendering of anonymised sheets.

Tableaux GFM (colonne « # » = numéro de ligne Excel), fiches pour les feuilles larges, ou CSV clôturé avec
neutralisation des formules. GFM tables ("#" = Excel row number), records for wide sheets, or fenced CSV
with formula neutralisation.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

WIDE_COLUMNS = 20
_PIPE_ESCAPE_RE = re.compile(r"\\(?=\|)")
_NEWLINE_RE = re.compile(r"\r\n|[\r\n\u2028\u2029]")
# Caractères que `escape_cell` transforme / characters `escape_cell` rewrites.
_ESCAPED_RE = re.compile(r"[|\r\n\u2028\u2029]")
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")
_NUMBER_RE = re.compile(r"[+\-]?[0-9]{1,40}(?:[.,][0-9]{1,40})?(?:[eE][+\-]?[0-9]{1,4})?")
_BACKTICKS_RE = re.compile(r"`{1,256}")
_BLOCK_MARKERS = frozenset("#>-*+|`~=_<")
_LIST_NUMBER_RE = re.compile(r"([0-9]{1,9})[.)]")

TEXTS = {
    "fr": {
        "sheet": "Feuille", "hidden": "masquée", "column": "Colonne", "row": "Ligne", "table": "Tableau",
        "form": "Formulaire", "cells": "Cellules isolées", "empty": "_Feuille vide._", "summary": "Résumé",
        "truncated": "_Feuille tronquée : {shown} lignes émises sur {total}._",
    },
    "en": {
        "sheet": "Sheet", "hidden": "hidden", "column": "Column", "row": "Row", "table": "Table",
        "form": "Form", "cells": "Isolated cells", "empty": "_Empty sheet._", "summary": "Summary",
        "truncated": "_Sheet truncated: {shown} of {total} rows emitted._",
    },
}


@dataclass(slots=True)
class TableView:
    """Tableau prêt à rendre (valeurs déjà anonymisées) / render-ready table (values already anonymised)."""

    span: str
    headers: list[str]
    rows: list[tuple[int, list[str]]]
    titles: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FormView:
    span: str
    items: list[tuple[str, str]]
    titles: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TextView:
    items: list[tuple[str, str]]


@dataclass(slots=True)
class SheetView:
    name: str
    hidden: bool = False
    blocks: list[TableView | FormView | TextView] = field(default_factory=list)
    shown_rows: int = 0
    total_rows: int = 0


def escape_cell(text: str) -> str:
    """Cellule GFM : « | » échappé, retours à la ligne -> <br> / GFM cell: pipes escaped, newlines -> <br>."""
    if "|" in text:
        text = _PIPE_ESCAPE_RE.sub(r"\\\\", text).replace("|", r"\|")
    if "\n" in text or "\r" in text or "\u2028" in text or "\u2029" in text:
        text = _NEWLINE_RE.sub("<br>", text)
    return text.strip()


def _table_lines(rows: list[tuple[int, list[str]]]) -> list[str]:
    """Lignes GFM des données. `escape_cell` se réduit à `strip` sur une cellule sans `|` ni saut de ligne : le
    choix se fait colonne par colonne, en une recherche, puis chaque colonne est traitée en C.
    GFM data lines. `escape_cell` reduces to `strip` on a cell without `|` or line break: the choice is made
    column by column, in one search, then each column is processed in C.
    """
    widths = {len(cells) for _, cells in rows}
    if len(widths) != 1:
        return [f"| {row} | " + " | ".join(map(escape_cell, cells)) + " |" for row, cells in rows]
    columns = [list(map(str.strip if _ESCAPED_RE.search("\x00".join(column)) is None else escape_cell, column))
               for column in zip(*(cells for _, cells in rows), strict=True)]
    if not columns:
        return [f"| {row} |  |" for row, _ in rows]
    return [f"| {row} | " + " | ".join(cells) + " |"
            for (row, _), cells in zip(rows, zip(*columns, strict=True), strict=True)]


def inline(text: str) -> str:
    """Texte sur une ligne (titres, fiches) / single-line text (headings, records)."""
    return _NEWLINE_RE.sub("<br>", text).strip()


def paragraph(text: str) -> str:
    """Ligne libre : un marqueur de bloc initial est échappé, une cellule ne peut pas forger de section.

    Free-text line: a leading block marker is escaped, so a cell cannot forge a section heading.
    """
    line = inline(text)
    if line[:1] in _BLOCK_MARKERS:
        return "\\" + line
    number = _LIST_NUMBER_RE.match(line)
    return f"{number.group(1)}\\{line[number.end(1):]}" if number else line


def neutralize_formula(text: str) -> str:
    """Préfixe « ' » contre l'injection de formules (CSV) ; les nombres restent intacts / CSV injection guard."""
    if text.startswith(_FORMULA_TRIGGERS) and not _NUMBER_RE.fullmatch(text):
        return "'" + text
    return text


def render_sheets(sheets: list[SheetView], table_format: str, language: str) -> list[str]:
    words = TEXTS.get(language, TEXTS["fr"])
    lines: list[str] = []
    for sheet in sheets:
        suffix = f" ({words['hidden']})" if sheet.hidden else ""
        lines += [f"## {words['sheet']} : {inline(sheet.name)}{suffix}", ""]
        if sheet.total_rows > sheet.shown_rows:
            lines += [words["truncated"].format(shown=sheet.shown_rows, total=sheet.total_rows), ""]
        if not sheet.blocks:
            lines += [words["empty"], ""]
        several = sum(isinstance(block, TableView) for block in sheet.blocks) > 1
        number = 0
        for block in sheet.blocks:
            if isinstance(block, TableView):
                number += 1
                lines += _render_table(block, number if several else 0, table_format, words)
            elif isinstance(block, FormView):
                lines += _render_form(block, words)
            else:
                lines += [f"### {words['cells']}", ""]
                lines += [f"- {ref} : {inline(text)}" for ref, text in block.items]
                lines.append("")
    return lines


def _render_table(table: TableView, number: int, table_format: str, words: dict[str, str]) -> list[str]:
    lines: list[str] = []
    if number:
        lines += [f"### {words['table']} {number} ({table.span})", ""]
    for title in table.titles:
        lines += [paragraph(title), ""]
    headers = [header or f"{words['column']} {index + 1}" for index, header in enumerate(table.headers)]
    if table_format == "csv":
        lines += _render_csv(headers, table.rows)
    elif len(headers) > WIDE_COLUMNS:
        lines += _render_records(headers, table.rows, words)
    else:
        lines.append("| # | " + " | ".join(escape_cell(header) for header in headers) + " |")
        lines.append("|---:|" + "---|" * len(headers))
        lines += _table_lines(table.rows)
    lines.append("")
    for note in table.notes:
        lines += [paragraph(note), ""]
    return lines


def _render_records(headers: list[str], rows: list[tuple[int, list[str]]], words: dict[str, str]) -> list[str]:
    """Feuilles larges : une fiche par ligne, valeurs vides omises / wide sheets: one record per row."""
    labels = [inline(header) for header in headers]
    lines: list[str] = []
    for row, cells in rows:
        lines += [f"### {words['row']} {row}", ""]
        lines += [f"- {label} : {inline(cell)}" for label, cell in zip(labels, cells, strict=True) if cell.strip()]
        lines.append("")
    return lines


def _render_csv(headers: list[str], rows: list[tuple[int, list[str]]]) -> list[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["#", *map(neutralize_formula, headers)])
    for row, cells in rows:
        writer.writerow([row, *map(neutralize_formula, cells)])
    body = buffer.getvalue().rstrip("\n")
    fence = "`" * max(3, _longest_backtick_run(body) + 1)
    return [f"{fence}csv", body, fence]


def _longest_backtick_run(text: str) -> int:
    """Plus longue suite de backticks, sans borne de longueur : les morceaux contigus sont additionnés.

    Longest run of backticks, unbounded: contiguous chunks are added up (the regex itself stays bounded).
    """
    longest = run = 0
    end = -1
    for found in _BACKTICKS_RE.finditer(text):
        size = found.end() - found.start()
        run = run + size if found.start() == end else size
        end = found.end()
        longest = max(longest, run)
    return longest


def _render_form(form: FormView, words: dict[str, str]) -> list[str]:
    lines = [f"### {words['form']} ({form.span})", ""]
    for title in form.titles:
        lines += [paragraph(title), ""]
    lines += [f"- **{_label(label)}** : {inline(value)}" for label, value in form.items]
    lines.append("")
    return lines


def _label(text: str) -> str:
    """Libellé en gras sans « : » final ni astérisque non échappé / bold label, no trailing ':' or bare '*'."""
    return inline(text).rstrip(" :").replace("*", r"\*") or "?"
