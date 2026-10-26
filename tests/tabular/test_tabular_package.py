"""Garde du paquet : format, archive, chiffrement, inventaire, étendue / package guard."""

from __future__ import annotations

import io
import re
import struct
import zipfile

import pytest
from python_calamine import CalamineWorkbook
from tabular_factories import cfb_bytes, ods_row, rezip, xlsx_bytes

from gdprguardian.documents import (
    DocumentError,
    DocumentTooLargeError,
    EncryptedDocumentError,
    MaliciousDocumentError,
    UnsupportedFormatError,
)
from gdprguardian.tabular._package import (
    MAX_MEMBERS,
    _xlsx_extent_exact,
    ods_extents,
    open_package,
    xlsb_extent,
    xlsx_extent,
)

SHEET = "xl/worksheets/sheet1.xml"


def _simple_xlsx() -> bytes:
    return xlsx_bytes(lambda wb: wb.add_worksheet("S").write("B2", "x"))


def _zip(members: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
    return output.getvalue()


def _patch_central(data: bytes, name: str, offset: int, value: int, fmt: str = "<I") -> bytes:
    """Modifie un champ de l'entrée centrale d'un membre / patches a central-directory field of a member."""
    position = data.index(b"PK\x01\x02")
    while True:
        name_length = struct.unpack_from("<H", data, position + 28)[0]
        if data[position + 46:position + 46 + name_length] == name.encode():
            break
        position = data.index(b"PK\x01\x02", position + 4)
    patched = bytearray(data)
    struct.pack_into(fmt, patched, position + offset, value)
    return bytes(patched)


# --- format / sniffing ---


def test_formats_are_sniffed_from_content() -> None:
    assert open_package(_simple_xlsx(), "renamed.csv").kind == "xlsx"
    assert open_package(b"Nom;Ville\nDupont;Lyon\n", "export.csv").kind == "csv"
    assert open_package(b"Nom\tVille\n", "export.tsv").kind == "tsv"
    # Les « .xls » exportés en texte sont lus comme du CSV / text ".xls" exports are read as CSV.
    assert open_package(b"Nom;Ville\n", "export.xls").kind == "csv"
    with pytest.raises(UnsupportedFormatError):
        open_package(b"\x00\x01garbage\x00" * 10, "fake.xlsx")
    with pytest.raises(UnsupportedFormatError):
        open_package(_zip({"readme.txt": b"hello"}), "archive.xlsx")


# --- archive ---


def test_zip_member_count_is_capped() -> None:
    with pytest.raises(MaliciousDocumentError):
        open_package(_zip({f"x{i}": b"" for i in range(MAX_MEMBERS + 1)}), "many.xlsx")


def test_zip_bomb_ratio_is_rejected() -> None:
    with pytest.raises(MaliciousDocumentError):
        open_package(_zip({"xl/workbook.xml": b"<w/>", SHEET: b"\0" * (4 << 20)}), "bomb.xlsx")


def test_encrypted_zip_member_is_rejected() -> None:
    data = _patch_central(_simple_xlsx(), "xl/workbook.xml", 8, 0x1, "<H")
    with pytest.raises(EncryptedDocumentError):
        open_package(data, "x.xlsx")


def test_lying_uncompressed_size_is_caught_by_the_crc() -> None:
    data = _simple_xlsx()
    real = zipfile.ZipFile(io.BytesIO(data)).getinfo("xl/sharedStrings.xml").file_size
    with pytest.raises(MaliciousDocumentError):
        open_package(_patch_central(data, "xl/sharedStrings.xml", 24, real // 2), "x.xlsx")


def test_dtd_in_workbook_xml_is_forbidden() -> None:
    def add_dtd(raw: bytes) -> bytes:
        return raw.replace(b"?>", b'?><!DOCTYPE w [<!ENTITY a "aaaaaaaaaa">]>', 1)

    with pytest.raises(MaliciousDocumentError):
        open_package(rezip(_simple_xlsx(), replace={"xl/workbook.xml": add_dtd}), "x.xlsx")


def test_corrupted_zip_is_a_safe_document_error() -> None:
    data = _simple_xlsx()
    with pytest.raises(DocumentError) as error:
        open_package(data[:200] + b"\0" * 64, "x.xlsx")
    assert "x.xlsx" not in str(error.value)


# --- chiffrement / encryption ---


def test_encrypted_ooxml_container_is_rejected_with_a_safe_message() -> None:
    data = cfb_bytes({"EncryptionInfo": b"\x04\x00\x04\x00", "EncryptedPackage": b"\x10" * 64})
    with pytest.raises(EncryptedDocumentError) as error:
        open_package(data, "paie.xlsx")
    message = str(error.value)
    assert "paie" not in message and "chiffré" in message


def test_xls_with_filepass_is_rejected() -> None:
    bof = struct.pack("<HH", 0x0809, 16) + b"\0" * 16
    filepass = struct.pack("<HH", 0x002F, 6) + b"\x01\x00\x01\x00\x01\x00"
    with pytest.raises(EncryptedDocumentError):
        open_package(cfb_bytes({"Workbook": bof + filepass}), "ancien.xls")


def test_plain_xls_container_is_inventoried() -> None:
    bof = struct.pack("<HH", 0x0809, 16) + b"\0" * 16
    eof = struct.pack("<HH", 0x000A, 0)
    package = open_package(cfb_bytes({"Workbook": bof + eof, "\x05SummaryInformation": b"\0" * 64}), "a.xls")
    assert package.kind == "xls"
    assert package.dropped["document_properties"] == 1
    assert package.sheet_extent("Feuil1") is None  # borné par le format BIFF8 / bounded by BIFF8 itself


def test_ole_container_without_workbook_is_unsupported() -> None:
    with pytest.raises(UnsupportedFormatError):
        open_package(cfb_bytes({"WordDocument": b"\0" * 32}), "x.xls")


# --- inventaire / inventory ---


def test_inventory_counts_hidden_parts_without_reading_them_into_the_output() -> None:
    def build(wb):
        wb.set_properties({"author": "Sébastien Secret", "company": "Société Secrète"})
        wb.set_custom_property("MSIP_Label_0000_SiteId", "11111111-2222-3333-4444-555555555555")
        sheet = wb.add_worksheet("S")
        sheet.write("A1", "x")
        sheet.write_comment("A1", "Arrêt maladie", {"author": "Sébastien Secret"})
        sheet.write_comment("A2", "Autre note")
        sheet.write_url("B1", "mailto:sebastien.secret@exemple.fr", string="Contact")
        sheet.write_formula("C1", "=1+1", None, 2)
        sheet.set_header("&CConfidentiel Sébastien")

    threaded = (b'<ThreadedComments><threadedComment ref="A1" personId="{1}"><text>Avis</text>'
                b'</threadedComment><threadedComment ref="A2" personId="{1}"><text>Ok</text></threadedComment>'
                b"</ThreadedComments>")
    data = rezip(xlsx_bytes(build), add={
        "xl/threadedComments/threadedComment1.xml": threaded,
        "xl/persons/person.xml": b'<personList><person displayName="S. Secret" id="{1}" userId="s@x.fr"/>'
                                 b"</personList>",
        "xl/pivotCache/pivotCacheDefinition1.xml": b"<pivotCacheDefinition/>",
        "xl/pivotCache/pivotCacheRecords1.xml": b"<pivotCacheRecords/>",
        "xl/externalLinks/externalLink1.xml": b"<externalLink/>",
        "xl/vbaProject.bin": b"\0" * 16,
        "docMetadata/LabelInfo.xml": b"<labelList/>",
        "customXml/item1.xml": b"<x/>",
        "xl/revisions/revisionHeaders.xml": b"<headers/>",
    })
    package = open_package(data, "inventaire.xlsm")
    assert package.sheet_extent("S") is not None  # lit la feuille : formules, en-têtes / reads the sheet
    package.tables("S")
    dropped = package.dropped
    assert dropped["comments"] == 2
    assert dropped["threaded_comments"] == 2 and dropped["comment_persons"] == 1
    assert dropped["pivot_caches"] == 1 and dropped["external_links"] == 1 and dropped["vba_projects"] == 1
    assert dropped["sensitivity_labels"] == 2 and dropped["custom_xml"] == 1 and dropped["revisions"] == 1
    assert dropped["document_properties"] == 3 and dropped["formulas"] == 1
    assert dropped["headers_footers"] == 1 and dropped["hyperlinks"] == 1
    assert package.kind == "xlsm"
    assert any("Auteur" in warning for warning in package.warnings)
    text = repr(package.warnings) + repr(dict(dropped))
    assert "Secret" not in text and "Sébastien" not in text and "1111" not in text


def test_date_1904_system_is_reported() -> None:
    package = open_package(xlsx_bytes(lambda wb: wb.add_worksheet().write("A1", 1), {"date_1904": True}), "a.xlsx")
    assert package.date1904 and any("1904" in warning for warning in package.warnings)


def test_excel_tables_are_read_from_their_parts() -> None:
    def build(wb):
        sheet = wb.add_worksheet("T")
        sheet.add_table("B3:D5", {"name": "Salaries_Dupont", "total_row": True,
                                  "columns": [{"header": "Nom"}, {"header": "Ligne_x000a_Deux"}, {"header": "Tel"}]})

    [spec] = open_package(xlsx_bytes(build), "t.xlsx").tables("T")
    assert (spec.top, spec.left, spec.bottom, spec.right) == (2, 1, 4, 3)
    assert spec.header_rows == 1 and spec.totals_rows == 1
    assert spec.columns == ("Nom", "Ligne\nDeux", "Tel")


# --- étendue / extent ---


def _sheet_xml(extra: bytes) -> tuple[bytes, bytes]:
    data = rezip(_simple_xlsx(), replace={SHEET: lambda raw: raw.replace(b"</sheetData>", extra + b"</sheetData>")})
    return data, zipfile.ZipFile(io.BytesIO(data)).read(SHEET)


@pytest.mark.parametrize("extra", [
    b'<row r="300"><c r="Z300"><v>1</v></c></row>',
    b"<row r='300'><c r='Z300'><v>1</v></c></row>",
    b'<row r = "300"><c r = "Z300"><v>1</v></c></row>',
    b'<row\tr="300"><c\tr="Z300"><v>1</v></c></row>',
    b'<row r="300"><c t="n" r="z300"><v>1</v></c></row>',
    b'<row r="300"><c r="A300" r="Z300"><v>1</v></c></row>',
    b'<row r="300"><c><v>1</v></c><c><v>1</v></c><c><v>1</v></c></row>',
    b'<row><c r="Z300"><v>1</v></c></row>',
    b'<x:row r="300" xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><x:c r="Z300">'
    b"<x:v>1</x:v></x:c></x:row>",
    b'<!-- <c r="ZZ900"> --><row r="300"><c r="Z300" s=">"><v>1</v></c></row>',
    b'<row r="3"><c r="Z300"><v>1</v></c></row>',
    b'<row r="300"><c r="Z300" s="0"/></row>',
])
def test_extent_bounds_what_calamine_allocates(extra: bytes) -> None:
    data, xml = _sheet_xml(extra)
    sheet = CalamineWorkbook.from_filelike(io.BytesIO(data)).get_sheet_by_name("S")
    rows, columns = xlsx_extent(xml)
    exact_rows, exact_columns = _xlsx_extent_exact(xml)
    assert sheet.end is not None
    assert rows >= exact_rows >= sheet.end[0] + 1
    assert columns >= exact_columns >= sheet.end[1] + 1


def test_exact_extent_is_tight_for_canonical_sheets() -> None:
    _, xml = _sheet_xml(b'<row r="300"><c r="Z300"><v>1</v></c></row>')
    assert _xlsx_extent_exact(xml) == (300, 26)
    assert xlsx_extent(xml, limit=100) == (300, 26)  # maxima exacts sous une petite limite / exact under a low limit


def test_far_cell_is_measured_without_loading_the_sheet() -> None:
    _, xml = _sheet_xml(b'<row r="1048576"><c r="XFD1048576"><v>1</v></c></row>')
    rows, columns = xlsx_extent(xml)
    assert rows * columns >= 1048576 * 16384


def test_ods_extents_count_materialised_repeats_only() -> None:
    cell = '<table:table-cell office:value-type="string"><text:p>x</text:p></table:table-cell>'
    content = (
        '<office:document-content xmlns:office="o" xmlns:table="t" xmlns:text="x"><office:body><office:spreadsheet>'
        f'<table:table table:name="A &amp; B">{ods_row("a", "b")}'
        f'<table:table-row table:number-rows-repeated="1000"><table:table-cell/></table:table-row></table:table>'
        f'<table:table table:name="Wide"><table:table-row table:number-rows-repeated="300">'
        f'<table:table-cell table:number-columns-repeated="200" office:value-type="float" office:value="1"/>'
        f"{cell}</table:table-row></table:table>"
        "</office:spreadsheet></office:body></office:document-content>").encode()
    assert ods_extents(content) == {"A & B": (1, 2), "Wide": (300, 201)}


def _record(kind: int, payload: bytes) -> bytes:
    header = bytes([kind]) if kind < 0x80 else bytes([(kind & 0x7F) | 0x80, kind >> 7])
    size, encoded = len(payload), b""
    while True:
        byte = size & 0x7F
        size >>= 7
        encoded += bytes([byte | (0x80 if size else 0)])
        if not size:
            return header + encoded + payload


def test_xlsb_extent_walks_biff12_records() -> None:
    stream = (_record(148, b"\0" * 16) + _record(0, struct.pack("<I", 4) + b"\0" * 8)
              + _record(7, struct.pack("<III", 9, 0, 0)) + _record(0, struct.pack("<I", 1_000_000) + b"\0" * 200)
              + _record(5, struct.pack("<II", 2, 0) + b"\0" * 8))
    assert xlsb_extent(stream) == (1_000_001, 10)
    with pytest.raises(DocumentError):
        xlsb_extent(stream + b"\x85")  # en-tête d'enregistrement tronqué / truncated record header


def test_oversized_xlsb_sheet_rejects_the_document() -> None:
    sheet = _record(0, struct.pack("<I", 1_048_575) + b"\0" * 8) + _record(7, struct.pack("<III", 16_383, 0, 0))
    data = _zip({"[Content_Types].xml": b"<Types/>", "xl/workbook.bin": b"\0", "xl/worksheets/sheet1.bin": sheet})
    with pytest.raises(DocumentTooLargeError):
        open_package(data, "big.xlsb")


def test_ods_encryption_is_detected() -> None:
    from tabular_factories import ods_bytes

    data = ods_bytes({"S": ods_row("x")}, manifest_extra='<manifest:encryption-data manifest:checksum="x"/>')
    with pytest.raises(EncryptedDocumentError):
        open_package(data, "c.ods")


def test_every_tabular_regex_has_bounded_quantifiers() -> None:
    import importlib

    from gdprguardian.scope import PLACEHOLDER_RE

    for name in ("_package", "_columns", "_persons", "_render", "_values", "_reader", "_structure", "_pipeline"):
        module = importlib.import_module(f"gdprguardian.tabular.{name}")
        for value in vars(module).values():
            if not isinstance(value, re.Pattern) or value is PLACEHOLDER_RE:  # motif du cœur / core pattern
                continue
            pattern = value.pattern if isinstance(value.pattern, str) else value.pattern.decode("latin-1")
            stripped = re.sub(r"\[[^\]]*\]", "", re.sub(r"\\.", "", pattern))
            assert "*" not in stripped and "+" not in stripped, f"{name}: {pattern}"


def test_unterminated_comments_are_stripped_in_linear_time() -> None:
    import time

    from gdprguardian.tabular._package import _strip_markup_noise

    hostile = b"<!--" * 200_000
    started = time.perf_counter()
    assert _strip_markup_noise(hostile) == b""
    assert time.perf_counter() - started < 1.0
    assert _strip_markup_noise(b"a<!-- x -->b<![CDATA[<c r='Z9'>]]>c<?pi?>d") == b"abcd"


def test_unparsable_tag_makes_the_sheet_unmeasurable() -> None:
    # Le commentaire force le chemin exact / the comment forces the exact path.
    _, xml = _sheet_xml(b'<!-- x --><row r="2"><c r="A2" s=unquoted><v>1</v></c></row>')
    rows, columns = xlsx_extent(xml)
    assert rows * columns > 1 << 24
