"""Personnes des colonnes de noms : découpage, formes, propagation / persons from name columns."""

from __future__ import annotations

import time
from collections.abc import Callable

import xlsxwriter
from tabular_factories import xlsx_bytes

from gdprguardian import Anonymizer
from gdprguardian.documents import DocumentResult
from gdprguardian.tabular._persons import KnownPersons, split_people


def _tag(form: str, canonical: str) -> str:
    return f"<{canonical}>"


def test_several_people_in_one_cell_are_split() -> None:
    assert split_people("Jean Dupont ; Marie Durand") == ["Jean Dupont", " ; ", "Marie Durand"]
    assert split_people("Jean Dupont et Marie Durand") == ["Jean Dupont", " et ", "Marie Durand"]
    assert split_people("Jean Dupont") is None
    assert split_people("Dupont (CDD) ; 3 mois") is None  # morceau qui n'est pas un nom / not a name


def test_forms_keep_their_canonical_identity_and_both_casings() -> None:
    persons = KnownPersons()
    persons.add("Hélène Delacroix", tokens=False)
    persons.add("Delacroix Hélène", tokens=False, canonical="Hélène Delacroix")
    persons.add("Delacroix")
    texts = ["Voir Delacroix Hélène", "DELACROIX absente", "Delacroixville", "dossier [DELACROIX_1]"]
    count = persons.apply(texts, range(len(texts)), _tag)
    assert texts == ["Voir <Hélène Delacroix>", "<Delacroix> absente", "Delacroixville", "dossier [DELACROIX_1]"]
    assert count == 2


def test_existing_placeholders_give_no_word_and_are_never_rewritten() -> None:
    persons = KnownPersons()
    persons.add("[PERSONNE_1]")
    texts = ["Personne n'est venu", "[PERSONNE_1] était là"]
    persons.apply(texts, range(2), _tag)
    assert texts == ["Personne n'est venu", "[PERSONNE_1] était là"]


def test_propagation_is_linear_with_many_placeholders() -> None:
    # 100 000 balises et autant de correspondances dans une cellule : jamais quadratique.
    # 100,000 placeholders and as many matches in one cell: never quadratic.
    persons = KnownPersons()
    persons.add("Bob")
    texts = [" ".join(["Bob [X_1]"] * 100_000)]
    started = time.perf_counter()
    assert persons.apply(texts, [0], _tag) == 100_000
    assert time.perf_counter() - started < 3.0
    assert texts[0].startswith("<Bob> [X_1] <Bob>")


def test_redacted_placeholders_are_counted(run: Callable[..., DocumentResult]) -> None:
    def build(wb: xlsxwriter.Workbook) -> None:
        sheet = wb.add_worksheet("S")
        sheet.write_row(0, 0, ["Nom", "Ville"])
        for row, name in enumerate(["Durand", "Martin", "Lefort"], start=1):
            sheet.write_row(row, 0, [name, "Lyon"])

    anonymizer = Anonymizer(countries=("FR",), operators={"PERSON": "redact"})
    result = run(xlsx_bytes(build), anonymizer=anonymizer)
    assert result.markdown.count("| [PERSONNE] |") == 3
    assert result.report["entities"]["PERSONNE"] == 3


def test_already_anonymised_person_column_is_kept(run: Callable[..., DocumentResult]) -> None:
    def build(wb: xlsxwriter.Workbook) -> None:
        sheet = wb.add_worksheet("S")
        sheet.write_row(0, 0, ["Nom", "Prénom", "Commentaire"])
        sheet.write_row(1, 0, ["[PERSONNE_1]", "[PERSONNE_1]", "RAS"])
        sheet.write_row(2, 0, ["Durand", "Paul", "Rappeler Durand"])
        sheet.write_row(3, 0, ["Martin", "Anne", "RAS"])
        sheet.write_row(4, 0, ["Lefort", "Luc", "RAS"])

    result = run(xlsx_bytes(build))
    # Entrée déjà anonymisée : balise conservée, jamais renumérotée / already anonymised: kept, never renumbered.
    assert "| 2 | [PERSONNE_1] | [PERSONNE_1] | RAS |" in result.markdown
    assert "[PERSONNE_1] | [PERSONNE_1] | Rappeler" not in result.markdown
    assert not any(name in result.markdown for name in ("Durand", "Paul", "Martin", "Anne", "Lefort", "Luc"))
