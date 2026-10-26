"""Garde contre l'allocation de calamine : lectures divergentes, polyglottes, bac à sable / allocation guard.

calamine résout les feuilles à sa façon (attribut `id` sans espace de noms, chemin littéral « .. », noms non
normalisés…) : pour chaque variante, chaque feuille que calamine annonce doit être jugée trop étendue. Seules
les métadonnées sont lues ici ; charger ces feuilles tuerait le processus de test.
calamine resolves sheets its own way: for every variant, each sheet calamine lists must be judged oversized.
Only metadata is read here; loading these sheets would kill the test process.
"""

from __future__ import annotations

import io
import struct
import time
import zipfile
from collections.abc import Callable

import pytest
from python_calamine import CalamineWorkbook
from tabular_factories import (
    FAR_SHEET,
    WORKSHEET_REL,
    cfb_bytes,
    ods_bytes,
    ods_row,
    raw_xlsx,
    rezip,
    sheet_xml,
    xlsx_bytes,
    zip_bytes,
)

from gdprguardian.documents import (
    DocumentError,
    DocumentOptions,
    DocumentResult,
    DocumentTooLargeError,
    MaliciousDocumentError,
    UnsupportedFormatError,
)
from gdprguardian.tabular._package import MAX_SHEET_AREA, ods_extents, open_package, xlsx_extent

SMALL = sheet_xml("B2")
ONE = '<sheet name="S" sheetId="1" r:id="rId1"/>'

HOSTILE = {
    # Chemin littéral : calamine lit « xl/worksheets/../evil.xml », pas « xl/evil.xml » / literal path.
    "dot-dot": raw_xlsx(ONE, {"rId1": "worksheets/../evil.xml"},
                        [("xl/evil.xml", SMALL), ("xl/worksheets/../evil.xml", FAR_SHEET)]),
    # r:id lié à un autre espace de noms : calamine ne lit que le préfixe / r:id bound to another namespace.
    "foreign-namespace": raw_xlsx(ONE, {"rId1": "evil.xml"}, [("xl/evil.xml", FAR_SHEET)], rel_ns="urn:other"),
    "unprefixed-id": raw_xlsx('<sheet name="S" sheetId="1" id="rId1"/>', {"rId1": "evil.xml"},
                              [("xl/evil.xml", FAR_SHEET)]),
    # Deux feuilles « S » : calamine charge la première pour les deux / both names load the first part.
    "duplicate-names": raw_xlsx(ONE + '<sheet name="S" sheetId="2" r:id="rId2"/>',
                                {"rId1": "a.xml", "rId2": "b.xml"}, [("xl/a.xml", FAR_SHEET), ("xl/b.xml", SMALL)]),
    # Tabulation littérale : normalisée par ElementTree, pas par calamine / literal tab, normalised by one parser.
    "tab-in-name": raw_xlsx('<sheet name="A&#9;B\tC" sheetId="1" r:id="rId1"/>', {"rId1": "evil.xml"},
                            [("xl/evil.xml", FAR_SHEET)]),
    "tab-in-target": raw_xlsx(ONE, {"rId1": "a\tb.xml"}, [("xl/a\tb.xml", FAR_SHEET), ("xl/a b.xml", SMALL)]),
    "duplicate-rel-ids": rezip(
        raw_xlsx(ONE, {"rId1": "a.xml"}, [("xl/a.xml", FAR_SHEET), ("xl/b.xml", SMALL)]),
        replace={"xl/_rels/workbook.xml.rels": lambda raw: raw.replace(b"</Relationships>", (
            f'<Relationship Id="rId1" Type="{WORKSHEET_REL}" Target="b.xml"/></Relationships>').encode())}),
    "percent-encoded": raw_xlsx(ONE, {"rId1": "worksheets/sheet%31.xml"},
                                [("xl/worksheets/sheet1.xml", SMALL), ("xl/worksheets/sheet%31.xml", FAR_SHEET)]),
}


@pytest.mark.parametrize("variant", sorted(HOSTILE))
def test_every_sheet_calamine_lists_is_judged_oversized(variant: str) -> None:
    data = HOSTILE[variant]
    names = [meta.name for meta in CalamineWorkbook.from_filelike(io.BytesIO(data)).sheets_metadata]
    assert names, variant
    package = open_package(data, "x.xlsx")
    for name in names:
        rows, columns = package.sheet_extent(name)
        assert rows * columns > MAX_SHEET_AREA, (variant, name)


@pytest.mark.parametrize("variant", ["dot-dot", "foreign-namespace", "tab-in-name", "duplicate-names"])
def test_hostile_variants_are_skipped_in_process(run: Callable[..., DocumentResult], variant: str) -> None:
    # Sans bac à sable : une garde défaillante tuerait ce processus / without sandbox, a failing guard kills us.
    result = run(HOSTILE[variant], sandbox=False)
    assert result.dropped["oversized_sheets"] >= 1


def test_legitimate_names_keep_per_sheet_decisions() -> None:
    def build(wb):
        wb.add_worksheet("Grande").write(1_048_575, 16_383, "z")
        wb.get_worksheet_by_name("Grande").write(0, 0, "a")
        wb.add_worksheet("Petite").write("A1", "x")

    package = open_package(xlsx_bytes(build), "x.xlsx")
    big, small = package.sheet_extent("Grande"), package.sheet_extent("Petite")
    assert big[0] * big[1] > MAX_SHEET_AREA and small[0] * small[1] <= MAX_SHEET_AREA


def test_duplicate_and_ambiguous_archives_are_rejected() -> None:
    sheet = ("xl/worksheets/sheet1.xml", SMALL)
    with pytest.raises(MaliciousDocumentError):
        open_package(raw_xlsx(ONE, {"rId1": "worksheets/sheet1.xml"}, [sheet, sheet]), "x.xlsx")
    with pytest.raises(MaliciousDocumentError):
        open_package(raw_xlsx(ONE, {"rId1": "worksheets/sheet1.xml"},
                              [sheet, ("xl/worksheets/SHEET1.xml", FAR_SHEET)]), "x.xlsx")
    # calamine essaierait l'ODS après un xlsx rejeté / calamine would try the ODS after a rejected xlsx.
    with pytest.raises(MaliciousDocumentError):
        open_package(raw_xlsx(ONE, {"rId1": "worksheets/sheet1.xml"}, [sheet, ("content.xml", b"<x/>")]), "x.xlsx")


def test_non_utf8_workbook_part_is_refused() -> None:
    latin = ('<?xml version="1.0" encoding="ISO-8859-1"?><workbook xmlns="urn:m" xmlns:r="urn:r"><sheets>'
             '<sheet name="A\x80" sheetId="1" r:id="rId1"/></sheets></workbook>').encode("latin-1")
    data = rezip(raw_xlsx(ONE, {"rId1": "worksheets/sheet1.xml"}, [("xl/worksheets/sheet1.xml", SMALL)]),
                 replace={"xl/workbook.xml": latin})
    with pytest.raises(UnsupportedFormatError):
        open_package(data, "x.xlsx")


def test_unsupported_zip_compression_is_a_safe_error() -> None:
    data = xlsx_bytes(lambda wb: wb.add_worksheet("S").write("A1", "x"))
    position = data.index(b"PK\x01\x02")
    while data[position + 46:position + 46 + len(b"xl/workbook.xml")] != b"xl/workbook.xml":
        position = data.index(b"PK\x01\x02", position + 4)
    patched = bytearray(data)
    struct.pack_into("<H", patched, position + 10, 9)  # Deflate64, inconnu de zipfile / unknown to zipfile
    with pytest.raises(UnsupportedFormatError):
        open_package(bytes(patched), "x.xlsx")


def test_ole_zip_polyglot_is_guarded() -> None:
    garbage_biff = cfb_bytes({"Workbook": b"\x09\x08\x10\x00" + b"\xff" * 64})

    def far(wb):
        sheet = wb.add_worksheet("P")
        sheet.write(0, 0, "a")
        sheet.write(1_048_575, 16_383, "z")

    # calamine rejette le BIFF puis lit l'archive en fin de fichier / calamine falls back to the trailing archive.
    with pytest.raises(MaliciousDocumentError):
        open_package(garbage_biff + xlsx_bytes(far), "x.xls")
    small = garbage_biff + xlsx_bytes(lambda wb: wb.add_worksheet("P").write("A1", "x"))
    assert open_package(small, "x.xls").kind == "xls"


def test_utf16_sheet_is_measured_after_decoding() -> None:
    xml = FAR_SHEET.decode().replace('encoding="UTF-8"', 'encoding="UTF-16"')
    rows, columns = xlsx_extent(b"\xff\xfe" + xml.encode("utf-16-le"))
    assert rows * columns > MAX_SHEET_AREA
    assert xlsx_extent(b"\xff\xfe\x00") == (1 << 31, 1 << 31)  # indécodable / undecodable


def test_ods_nested_table_and_duplicate_names() -> None:
    inner = ('<table:table-cell office:value-type="string"><table:table table:name="in">'
             f'{ods_row("x", repeat=5)}</table:table></table:table-cell>')
    content = ('<office:document-content xmlns:office="o" xmlns:table="t" xmlns:text="x"><office:body>'
               f'<office:spreadsheet><table:table table:name="N"><table:table-row>{inner}</table:table-row>'
               f'</table:table><table:table table:name="D">{ods_row("a", "b", "c", repeat=40)}</table:table>'
               f'<table:table table:name="D">{ods_row("a")}</table:table>'
               "</office:spreadsheet></office:body></office:document-content>").encode()
    extents = ods_extents(content)
    assert extents["N"][0] * extents["N"][1] > MAX_SHEET_AREA  # calamine lit la table imbriquée / reads it
    assert extents["D"] == (40, 3)
    assert ods_extents(b'<table:table table:name="X">')[""][0] > 1 << 24  # table non fermée / unclosed


def test_ods_sheet_names_are_matched_leniently() -> None:
    package = open_package(ods_bytes({"Feuille  Un": ods_row("x")}), "x.ods")
    assert package.sheet_extent("Feuille Un") == (1, 1)
    assert package.sheet_extent("feuille un") == (1, 1)


def _record(kind: int, payload: bytes) -> bytes:
    header = bytes([kind]) if kind < 0x80 else bytes([(kind & 0x7F) | 0x80, kind >> 7])
    return header + bytes([len(payload)]) + payload


def test_xlsb_sheets_are_found_through_their_relationships() -> None:
    rel_id = "rId7".encode("utf-16-le")
    bundle = _record(156, struct.pack("<II", 0, 1) + struct.pack("<I", 4) + rel_id + struct.pack("<I", 1) + b"S\0")
    far = (_record(0, struct.pack("<I", 0) + b"\0" * 8) + _record(7, struct.pack("<III", 0, 0, 0))
           + _record(0, struct.pack("<I", 1_048_575) + b"\0" * 8) + _record(7, struct.pack("<III", 16_383, 0, 0)))
    rels = (b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="urn:r"><Relationship Id="rId7" Type="t" '
            b'Target="../hors/feuille.bin"/></Relationships>')
    data = zip_bytes([("[Content_Types].xml", b"<Types/>"), ("xl/workbook.bin", bundle),
                      ("xl/_rels/workbook.bin.rels", rels), ("hors/feuille.bin", far)])
    with pytest.raises(DocumentTooLargeError):
        open_package(data, "x.xlsb")


def test_native_crash_is_confined_to_the_sandbox() -> None:
    from gdprguardian.convert import _sandbox

    data = raw_xlsx(ONE, {"rId1": "worksheets/sheet1.xml"}, [("xl/worksheets/sheet1.xml", FAR_SHEET)])
    started = time.perf_counter()
    with pytest.raises(DocumentError) as error:
        _sandbox.run("tabular_factories:load_without_guard", data, (".xlsx", DocumentOptions()), 120)
    assert "brutalement" in str(error.value) and time.perf_counter() - started < 120


def test_sandbox_and_in_process_reading_agree(run: Callable[..., DocumentResult]) -> None:
    def build(wb):
        sheet = wb.add_worksheet("Équipe")
        sheet.write_row(0, 0, ["Nom", "Email", "Téléphone"])
        sheet.write_row(1, 0, ["Delacroix", "h.delacroix@exemple.fr", "06 12 34 56 78"])
        sheet.write_row(2, 0, ["Fontaine", "m.fontaine@exemple.fr", "07 98 76 54 32"])

    data = xlsx_bytes(build)
    sandboxed, local = run(data, sandbox=True), run(data, sandbox=False)
    assert sandboxed.markdown == local.markdown and sandboxed.dropped == local.dropped
    assert "Delacroix" not in sandboxed.markdown


def test_out_of_range_values_skip_only_their_sheet(run: Callable[..., DocumentResult]) -> None:
    def build(wb):
        duration = wb.add_format({"num_format": "[h]:mm:ss"})
        wb.add_worksheet("Cassée").write_number("A1", 1e12, duration)
        wb.add_worksheet("Saine").write_row("A1", ["Email", "x@exemple.fr"])

    for sandbox in (True, False):
        result = run(xlsx_bytes(build), sandbox=sandbox)
        assert result.dropped["unreadable_sheets"] == 1
        assert "x@exemple.fr" not in result.markdown and "## Feuille" in result.markdown
        assert any("illisible" in warning for warning in result.warnings)


def test_crafted_merges_and_tables_stay_linear(run: Callable[..., DocumentResult]) -> None:
    def build(wb):
        sheet = wb.add_worksheet("S")
        sheet.write_row(0, 0, ["Nom", "Ville"])
        for row in range(1, 2_000):
            sheet.write_row(row, 0, [f"Nom{row}", "Lyon"])

    # Milliers de fusions verticales sur toute la hauteur, et tableaux identiques empilés.
    # Thousands of full-height vertical merges, and identical stacked tables.
    merges = "".join(f'<mergeCell ref="C1:C{1_000 + i}"/>' for i in range(3_000))
    table = ('<?xml version="1.0" encoding="UTF-8"?><table xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main" id="{n}" name="T{n}" displayName="T{n}" ref="A1:B2000">'
             '<tableColumns count="2"><tableColumn id="1" name="Nom"/><tableColumn id="2" name="Ville"/>'
             "</tableColumns></table>")
    rels = "".join(f'<Relationship Id="rT{n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                   f'relationships/table" Target="../tables/table{n}.xml"/>' for n in range(1, 200))
    data = rezip(xlsx_bytes(build), replace={"xl/worksheets/sheet1.xml": lambda raw: raw.replace(
        b"</sheetData>", f"</sheetData><mergeCells>{merges}</mergeCells>".encode())}, add={
        "xl/worksheets/_rels/sheet1.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8"?><Relationships '
            f'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>').encode(),
        **{f"xl/tables/table{n}.xml": table.format(n=n).encode() for n in range(1, 200)}})
    started = time.perf_counter()
    result = run(data, sandbox=False)
    assert time.perf_counter() - started < 20
    assert result.markdown.count("| 1999 |") == 1  # une seule fois, malgré 199 tableaux / once only


def test_unreadable_trailing_archive_leaves_the_xls_alone() -> None:
    # Signature de fin d'archive sans archive lisible : rien à garder / end signature without a readable archive.
    bof = struct.pack("<HH", 0x0809, 16) + b"\0" * 16 + struct.pack("<HH", 0x000A, 0)
    data = cfb_bytes({"Workbook": bof}) + b"PK\x05\x06" + b"\0" * 10
    assert not zipfile.is_zipfile(io.BytesIO(data))
    assert open_package(data, "x.xls").kind == "xls"
