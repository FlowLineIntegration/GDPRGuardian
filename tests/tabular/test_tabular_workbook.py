"""Bout en bout : aucune valeur plantée ne sort, cohérence entre feuilles, contenus masqués / end to end."""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
import xlsxwriter
from tabular_factories import luhn_complete, nir, ods_bytes, ods_row, xlsx_bytes

from gdprguardian import Anonymizer
from gdprguardian.documents import DocumentResult, anonymize_document

PEOPLE = [
    # nom, prénom, e-mail, téléphone (nombre), code postal (nombre), naissance, corps du NIR
    ("Delacroix", "Hélène", "helene.delacroix@exemple.fr", 612345678, 1000, dt.datetime(1985, 3, 14), "2850375056042"),
    ("Fontaine", "Mathis", "m.fontaine@exemple.fr", 698765432, 75001, dt.datetime(1990, 7, 1), "1900775101234"),
    ("Marchetti", "Zoé", "zoe.marchetti@exemple.fr", 145678901, 13001, dt.datetime(1978, 12, 25), "2781213055123"),
    ("Nguyen", "Baptiste", "b.nguyen@exemple.fr", 756123456, 6000, dt.datetime(2001, 2, 3), "1010206088456"),
]
HEADERLESS = ["Inès BERTRAND", "Gaspard Lemoine", "Clémence ROUSSEL", "Anatole Vasseur", "Maëlle GUERIN",
              "Théodore Blanchard"]
NIRS = [nir(body) for *_, body in PEOPLE]
NIRS[3] = NIRS[3][:-2] + f"{(int(NIRS[3][-2:]) + 1) % 100:02d}"  # clé fausse : coquille / wrong key: a typo
SIRET = luhn_complete("7328293200007")
SIREN_WITH_ZERO = luhn_complete("01234567")
CARD_TRUNCATED = 4111111111111110  # 4111 1111 1111 1111 après la perte du 16e chiffre par Excel

SECRETS = [
    *(p[0] for p in PEOPLE), *(p[1] for p in PEOPLE if p[1] != "Zoé"), *(p[2] for p in PEOPLE), *NIRS,
    *(f"0{p[3]}" for p in PEOPLE), *(str(p[3]) for p in PEOPLE), "06 12 34 56 78",
    *(p[5].strftime("%Y-%m-%d") for p in PEOPLE), *(p[5].strftime("%d/%m/%Y") for p in PEOPLE),
    *(name.split()[0] for name in HEADERLESS), *(name.split()[1] for name in HEADERLESS),
    "Secretnom", "Archivenom", "185057800608491", "arrêt maladie", "Rhône", "Auteur Confidentiel",
    "Société Secrète", "11111111-2222-3333-4444-555555555555", "4111111111111111", str(CARD_TRUNCATED),
    "Salaries_Delacroix",
]


def _hr_workbook() -> bytes:
    def build(wb: xlsxwriter.Workbook) -> None:
        wb.set_properties({"author": "Auteur Confidentiel", "company": "Société Secrète"})
        wb.set_custom_property("MSIP_Label_0000_SiteId", "11111111-2222-3333-4444-555555555555")
        date = wb.add_format({"num_format": "dd/mm/yyyy"})
        staff = wb.add_worksheet("Personnel")
        staff.write("A1", "Liste du personnel")
        staff.merge_range("A3:B3", "Identité", None)
        staff.merge_range("C3:D3", "Coordonnées", None)
        staff.write_row("A4", ["Nom", "Prénom", "Email", "Téléphone", "Code postal", "Date de naissance", "N° SS",
                               "Commentaire"])
        notes = ["RDV avec Mme Fontaine mardi", "Voir Delacroix Hélène", "", "n/a"]
        for row, (person, number, note) in enumerate(zip(PEOPLE, NIRS, notes, strict=True), start=4):
            surname, given, email, phone, postcode, born, _ = person
            staff.write_row(row, 0, [surname, given, email])
            staff.write_number(row, 3, phone)
            staff.write_number(row, 4, postcode)
            staff.write_datetime(row, 5, born, date)
            staff.write_number(row, 6, float(number))
            staff.write(row, 7, note)
        staff.write_comment("A5", "Salarié en arrêt maladie", {"author": "Marie Rhône"})

        form = wb.add_worksheet("Dossier Delacroix")
        form.write_column("A1", ["Nom :", "Prénom :", "Date de naissance :", "Téléphone :", "Ville :"])
        form.write_column("B1", ["Delacroix", "Hélène"])
        form.write_datetime("B3", PEOPLE[0][5], date)
        form.write("B4", "06 12 34 56 78")
        form.write("B5", "Lyon")

        loose = wb.add_worksheet("Sans en-tête")
        for row, name in enumerate(HEADERLESS):
            loose.write_row(row, 0, [name, 1200.0 + row, "Paris"])

        ids = wb.add_worksheet("Identifiants")
        ids.add_table("A1:C3", {"name": "Salaries_Delacroix",
                                "columns": [{"header": "SIRET"}, {"header": "SIREN"}, {"header": "Numéro de carte"}]})
        ids.write_number("A2", float(SIRET))
        ids.write_number("B2", float(SIREN_WITH_ZERO))
        ids.write_number("C2", 4111111111111111.0)
        ids.write_number("A3", float(SIRET))
        ids.write_number("B3", float(SIREN_WITH_ZERO))
        ids.write_number("C3", float(CARD_TRUNCATED))

        contacts = wb.add_worksheet("Contacts")
        contacts.write_row("A1", ["Courriel", "Téléphone portable"])
        contacts.write_row("A2", [PEOPLE[1][2], "06 98 76 54 32"])

        hidden = wb.add_worksheet("Référentiel")
        hidden.write_row("A1", ["Nom", "NIR"])
        hidden.write_row("A2", ["Secretnom", "185057800608491"])
        hidden.hide()
        very_hidden = wb.add_worksheet("Archive")
        very_hidden.write_row("A1", ["Nom", "Montant"])
        very_hidden.write_row("A2", ["Archivenom", 12.0])
        very_hidden.very_hidden()

    return xlsx_bytes(build)


@pytest.fixture(scope="module")
def hr_workbook() -> bytes:
    return _hr_workbook()


def _sections(markdown: str) -> list[str]:
    return markdown.split("\n## Feuille : ")[1:]


def _row(section: str, number: int) -> list[str]:
    line = next(line for line in section.splitlines() if line.startswith(f"| {number} |"))
    return [cell.strip() for cell in line.strip().strip("|").split(" | ")][1:]


def _leaks(result: DocumentResult, secrets: list[str]) -> list[str]:
    everything = "\n".join([result.markdown, json.dumps(result.report, ensure_ascii=False),
                            json.dumps(result.warnings, ensure_ascii=False), json.dumps(result.dropped)])
    return [secret for secret in secrets if secret in everything]


def test_no_planted_value_leaks(run: Callable[..., DocumentResult], hr_workbook: bytes) -> None:
    result = run(hr_workbook, "Paie Delacroix 2024.xlsx")
    assert _leaks(result, SECRETS) == []
    # Le nom de fichier ne sort jamais, seule l'extension reste / the file name never leaves, only the extension.
    assert result.markdown.startswith("## ") and "document.xlsx" not in result.markdown
    assert result.report["irreversible"] is True and result.kind == "xlsx"


def test_hidden_parts_are_excluded_and_reported(run: Callable[..., DocumentResult], hr_workbook: bytes) -> None:
    result = run(hr_workbook)
    assert result.dropped["hidden_sheets"] == 2
    assert result.dropped["comments"] == 1 and result.dropped["document_properties"] >= 2
    assert result.dropped["sensitivity_labels"] == 1
    assert any("masquée" in warning for warning in result.warnings)
    assert any("Auteur" in warning for warning in result.warnings)
    assert len(_sections(result.markdown)) == 5
    summary = result.markdown.split("## Feuille", 1)[0]
    assert "2 feuille(s) masquée(s)" in summary and "1 commentaire(s)" in summary


def test_hidden_sheets_on_request_are_anonymised(run: Callable[..., DocumentResult], hr_workbook: bytes) -> None:
    result = run(hr_workbook, include_hidden=True)
    sections = _sections(result.markdown)
    assert len(sections) == 7
    assert sum("(masquée)" in section.splitlines()[0] for section in sections) == 2
    assert _leaks(result, ["Secretnom", "Archivenom", "185057800608491"]) == []


def test_columns_are_typed_and_values_normalised(run: Callable[..., DocumentResult], hr_workbook: bytes) -> None:
    result = run(hr_workbook)
    staff = _sections(result.markdown)[0]
    assert "| # | Identité / Nom | Identité / Prénom | Coordonnées / Email | Coordonnées / Téléphone |" in staff
    first = _row(staff, 5)
    assert first[0] == first[1] and first[0].startswith("[PERSONNE_")  # prénom et nom : même personne
    assert first[2].startswith("[EMAIL_") and first[3].startswith("[TEL_")
    assert first[4] == "01000"  # zéro initial rétabli / leading zero restored
    assert first[5] == "1985"  # date de naissance -> année / birth date -> year
    assert first[6].startswith("[NIR_")
    assert _row(staff, 8)[6].startswith("[NIR_")  # clé fausse, masquée par la colonne / wrong key, masked
    assert _row(staff, 8)[7] == "n/a"
    columns = {c["column"]: c for c in result.report["sheets"][0]["columns"]}
    assert (columns["A"]["type"], columns["A"]["action"]) == ("PERSON", "mask")
    assert (columns["F"]["type"], columns["F"]["action"]) == ("BIRTH_DATE", "year")
    assert (columns["H"]["type"], columns["H"]["action"]) == (None, "detect")


def test_consistency_across_sheets(run: Callable[..., DocumentResult], hr_workbook: bytes) -> None:
    result = run(hr_workbook)
    staff, form, _loose, _ids, contacts = _sections(result.markdown)
    delacroix, fontaine = _row(staff, 5), _row(staff, 6)
    # Nom de feuille anonymisé ; les bornes exactes relèvent du détecteur de noms / sheet name anonymised.
    assert "[PERSONNE_" in form.splitlines()[0] and "Delacroix" not in form.splitlines()[0]
    assert f"- **Nom** : {delacroix[0]}" in form and f"- **Prénom** : {delacroix[0]}" in form
    assert f"- **Téléphone** : {delacroix[3]}" in form  # 612345678 et « 06 12 34 56 78 » : même numéro
    assert "- **Date de naissance** : 1985" in form and "- **Ville** : Lyon" in form
    assert _row(contacts, 2)[0] == fontaine[2]  # même e-mail, même balise / same e-mail, same placeholder
    assert fontaine[0] in _row(staff, 5)[7]  # nom propagé dans le texte libre / name propagated into free text
    assert delacroix[0] in _row(staff, 6)[7]


def test_headerless_names_and_identifier_columns(run: Callable[..., DocumentResult], hr_workbook: bytes) -> None:
    result = run(hr_workbook)
    _staff, _form, loose, ids, _contacts = _sections(result.markdown)
    assert all(_row(loose, row)[0].startswith("[PERSONNE_") for row in range(1, 7))
    assert _row(loose, 1)[2] == "Paris"
    first, second = _row(ids, 2), _row(ids, 3)
    assert first[0] == SIRET and first[1] == SIREN_WITH_ZERO  # entreprises : conservés / companies kept
    assert first[2].startswith("[CARTE_") and second[2].startswith("[CARTE_")
    assert any("carte" in warning for warning in result.warnings)


def test_operators_and_settings_are_honoured(hr_workbook: bytes, run: Callable[..., DocumentResult]) -> None:
    replaced = run(hr_workbook, anonymizer=Anonymizer(countries=("FR",), operators={"BIRTH_DATE": "replace"}))
    assert _row(_sections(replaced.markdown)[0], 5)[5].startswith("[DATE_NAISSANCE_")
    no_people = run(hr_workbook, anonymizer=Anonymizer(countries=("FR",), exclude_entities=frozenset({"PERSON"})))
    assert _row(_sections(no_people.markdown)[0], 5)[0] == "Delacroix"
    allowed = run(hr_workbook, anonymizer=Anonymizer(countries=("FR",), allow_list=["Marchetti"]))
    assert _row(_sections(allowed.markdown)[0], 7)[0] == "Marchetti"
    companies = run(hr_workbook, anonymizer=Anonymizer(countries=("FR",), company_ids="mask"))
    assert SIRET not in companies.markdown


def test_csv_cp1252_with_semicolons(run: Callable[..., DocumentResult]) -> None:
    text = ("Nom;Prénom;Ville;Montant;Téléphone;Commentaire\n"
            "Lefèvre;Hélène;Évreux;1 234,56;0612345678;Client fidèle\n"
            "Garçon;Noël;Nîmes;12,5;0698765432;Appeler Hélène Lefèvre\n"
            "Dupré;Zoé;Orléans;3,14;145678901;=HYPERLINK(\"http://x\")\n")
    result = run(text.encode("cp1252"), "export Lefèvre.csv")
    assert _leaks(result, ["Lefèvre", "Hélène", "Garçon", "Noël", "Dupré", "0612345678", "145678901"]) == []
    section = _sections(result.markdown)[0]
    first, second, third = _row(section, 2), _row(section, 3), _row(section, 4)
    assert first[2] == "Évreux" and first[3] == "1 234,56"  # accents décodés, montants intacts
    assert first[0] == first[1] and "[PERSONNE_" in second[5]
    assert third[4].startswith("[TEL_")  # 145678901 -> 0145678901 d'après l'en-tête
    assert result.kind == "csv"


def test_tsv_and_csv_output_with_formula_neutralisation(run: Callable[..., DocumentResult]) -> None:
    text = "Nom\tMontant\tNote\nDurand\t-12.5\t=1+1\nMoreau\t3\t@SUM(A1)\n"
    result = run(text.encode(), "export.tsv", table_format="csv")
    assert "```csv" in result.markdown and "Durand" not in result.markdown
    block = result.markdown.split("```csv\n", 1)[1].split("\n```", 1)[0].splitlines()
    assert block[0] == "#,Nom,Montant,Note"
    assert block[1].endswith(",-12.5,'=1+1") and block[2].endswith(",3,'@SUM(A1)")


def test_wide_sheets_are_rendered_as_records(run: Callable[..., DocumentResult]) -> None:
    headers = ["Nom", *(f"Mesure {i}" for i in range(24))]

    def build(wb: xlsxwriter.Workbook) -> None:
        sheet = wb.add_worksheet("Large")
        sheet.write_row(0, 0, headers)
        sheet.write_row(1, 0, ["Delacroix", *range(24)])

    result = run(xlsx_bytes(build))
    assert "### Ligne 2" in result.markdown and "| # |" not in result.markdown
    assert "- Nom : [PERSONNE_1]" in result.markdown and "- Mesure 23 : 23" in result.markdown


def test_pipes_and_newlines_are_escaped(run: Callable[..., DocumentResult]) -> None:
    def build(wb: xlsxwriter.Workbook) -> None:
        sheet = wb.add_worksheet("S")
        sheet.write_row(0, 0, ["Produit", "Détail", "Quantité"])
        sheet.write_row(1, 0, ["a|b", "ligne 1\nligne 2", 3])

    section = _sections(run(xlsx_bytes(build)).markdown)[0]
    assert "| 2 | a\\|b | ligne 1<br>ligne 2 | 3 |" in section


def test_truncation_is_explicit(run: Callable[..., DocumentResult]) -> None:
    def build(wb: xlsxwriter.Workbook) -> None:
        sheet = wb.add_worksheet("S")
        sheet.write_row(0, 0, ["Produit", "Quantité"])
        for row in range(1, 50):
            sheet.write_row(row, 0, [f"P{row}", row])
        wb.add_worksheet("T").write("A1", "x")

    capped = run(xlsx_bytes(build), max_rows_per_sheet=10)
    assert "_Feuille tronquée : 10 lignes émises sur 50._" in capped.markdown
    assert any("tronquée" in warning for warning in capped.warnings)
    limited = run(xlsx_bytes(build), max_cells=20)
    assert limited.dropped.get("cell_limit_sheets") == 1
    assert "Limite de cellules atteinte" in limited.markdown


def test_ods_workbook(run: Callable[..., DocumentResult]) -> None:
    data = ods_bytes({
        "Clients": ods_row("Nom", "Email", "Montant") + ods_row("Delacroix", "h.d@exemple.fr", 12.5)
        + ods_row("Fontaine", "m.f@exemple.fr", 3.0) + ods_row("", "", "", repeat=500),
        "Caché": ods_row("Nom") + ods_row("Secretnom"),
    }, hidden=("Caché",), extra_parts={"meta.xml": b"<meta/>"})
    result = run(data, "clients.ods")
    assert result.kind == "ods"
    assert _leaks(result, ["Delacroix", "Fontaine", "h.d@exemple.fr", "Secretnom"]) == []
    assert result.dropped["hidden_sheets"] == 1 and result.dropped["document_properties"] == 1
    assert _row(_sections(result.markdown)[0], 2)[2] == "12.5"


def test_far_away_cell_does_not_crash_the_process(run: Callable[..., DocumentResult]) -> None:
    def build(wb: xlsxwriter.Workbook) -> None:
        bomb = wb.add_worksheet("Bombe")
        bomb.write(0, 0, "a")
        bomb.write(1_048_575, 16_383, "z")
        wb.add_worksheet("Saine").write_row(0, 0, ["Email", "x@exemple.fr"])

    result = run(xlsx_bytes(build))
    assert result.dropped["oversized_sheets"] == 1
    assert "x@exemple.fr" not in result.markdown and len(_sections(result.markdown)) == 1


def test_empty_workbook_and_sheet(run: Callable[..., DocumentResult]) -> None:
    result = run(xlsx_bytes(lambda wb: wb.add_worksheet("Vide")))
    assert "_Feuille vide._" in result.markdown


def test_deterministic_and_thread_safe(run: Callable[..., DocumentResult], hr_workbook: bytes) -> None:
    expected = run(hr_workbook).markdown
    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(pool.map(lambda _: run(hr_workbook).markdown, range(8)))
    assert all(output == expected for output in outputs)


def test_documents_facade_dispatches_spreadsheets(hr_workbook: bytes) -> None:
    result = anonymize_document(hr_workbook, "rh.xlsx")
    assert result.kind == "xlsx" and "Delacroix" not in result.markdown


def test_report_counts_replacements_per_cell(run: Callable[..., DocumentResult], hr_workbook: bytes) -> None:
    result = run(hr_workbook)
    entities = result.report["entities"]
    assert entities["EMAIL"] == 5  # 4 dans « Personnel » + 1 dans « Contacts »
    assert entities["DATE_NAISSANCE"] == 5  # 4 années + 1 dans le formulaire / 4 years + 1 in the form
    assert result.report["total_replaced"] == sum(entities.values())
    placeholders = re.findall(r"\[([A-Z_]+)_\d+\]", result.markdown.split("## Feuille", 1)[1])
    # Balises émises + 5 dates de naissance réduites à l'année / emitted placeholders + 5 years.
    assert len(placeholders) + 5 == result.report["total_replaced"]
