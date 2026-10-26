"""Identification du format par les octets / format identification from bytes."""

from __future__ import annotations

import pytest
from convert_samples import AUTHOR, contract_pdf, make_cfb, make_docx, make_odt, make_pptx, png_bytes, zip_bytes

from gdprguardian.convert import to_markdown
from gdprguardian.convert._detect import identify, sniff
from gdprguardian.documents import DocumentOptions, EncryptedDocumentError, UnsupportedFormatError

LOCAL = DocumentOptions(sandbox=False)


@pytest.mark.parametrize(("data", "extension", "family"), [
    (b"%PDF-1.7\n...", ".bin", "pdf"),
    (b"\n\n%PDF-1.4", "", "pdf"),
    (b"{\\rtf1\\ansi hello}", ".doc", "rtf"),
    (b"\xef\xbb\xbf{\\rtf1 x}", "", "rtf"),
    (b"<!DOCTYPE html><p>x</p>", ".txt", "html"),
    (b"<?xml version='1.0'?><!-- c --><html><body/></html>", "", "html"),
    (b"<div>bonjour</div>", ".md", "html"),
    (b"<note>pas du HTML</note>", ".txt", "txt"),
    (b"From: a@b.fr\nTo: c@d.fr\nSubject: x\n\nCorps", "", "eml"),
    (b"Subject: x\n\nCorps", ".eml", "eml"),
    (b"Titre: pas un courriel\nTexte", ".txt", "txt"),
    (b"# Titre\n\nTexte", ".md", "md"),
    (b"Texte simple", ".TXT", "txt"),
    ("Café".encode("utf-16"), ".txt", "txt"),
    (b"PK\x03\x04rest", ".pdf", "zip"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest", ".docx", "ole"),
])
def test_sniff_reads_bytes_not_extension(data: bytes, extension: str, family: str) -> None:
    assert sniff(data, extension) == family


@pytest.mark.parametrize("data", [png_bytes(), b"\xff\xd8\xff\xe0JFIF", b"GIF89a....", b"RIFF\0\0\0\0WEBPVP8 "])
def test_images_are_rejected_with_a_clear_message(data: bytes) -> None:
    with pytest.raises(UnsupportedFormatError, match="OCR"):
        sniff(data, ".pdf")


@pytest.mark.parametrize("data", [b"\x1f\x8b\x08\x00gzip", b"7z\xbc\xaf\x27\x1crest", b"MZ\x90\x00\x03\x00\x00\x00"])
def test_archives_and_binaries_are_rejected(data: bytes) -> None:
    with pytest.raises(UnsupportedFormatError):
        sniff(data, "")


@pytest.mark.parametrize(("builder", "kind"), [(contract_pdf, "pdf"), (make_docx, "docx"), (make_pptx, "pptx"),
                                               (make_odt, "odt")])
def test_misleading_extension_is_converted_and_reported(builder, kind: str) -> None:
    result = to_markdown(builder(), "rapport.txt", LOCAL)
    assert result.kind == kind
    assert any("Extension trompeuse" in warning for warning in result.warnings)


def test_pdf_with_a_prefix_is_still_a_pdf() -> None:
    # Les lecteurs PDF acceptent un préfixe ; lu en texte, le PDF brut livrait /Author / raw PDF leaked /Author.
    data = b"JUNK\r\n" + contract_pdf()
    assert sniff(data, "") == "pdf"
    result = to_markdown(data, "piece-jointe", LOCAL)
    assert result.kind == "pdf" and AUTHOR not in result.markdown
    assert sniff(b"Ce texte cite %PDF-1.7 sans en etre un.", ".txt") == "txt"


@pytest.mark.parametrize("data", [
    b'<?xml version="1.0"?><pkg:package xmlns:pkg="http://schemas.microsoft.com/office/2006/xmlPackage"/>',
    b'<?xml version="1.0"?><?mso-application progid="Word.Document"?><w:wordDocument/>',
    b'<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"/>',
])
def test_office_xml_is_rejected_rather_than_dumped_as_text(data: bytes) -> None:
    # Son XML brut contiendrait les propriétés du document (auteur...) / raw XML holds the document properties.
    with pytest.raises(UnsupportedFormatError, match="XML Office"):
        to_markdown(data, "export.xml", LOCAL)


def test_matching_extension_has_no_warning() -> None:
    assert not any("trompeuse" in w for w in to_markdown(make_docx(), "a.docx", LOCAL).warnings)


@pytest.mark.parametrize(("streams", "match"), [
    ({"WordDocument": b"x" * 600, "1Table": b"y"}, r"\.docx"),
    ({"PowerPoint Document": b"x"}, r"\.pptx"),
    ({"Workbook": b"x"}, "tableur"),
    ({"Random": b"x"}, "OLE"),
])
def test_legacy_ole_formats_are_rejected(streams: dict[str, bytes], match: str) -> None:
    with pytest.raises(UnsupportedFormatError, match=match):
        identify(make_cfb(streams), "ole")


def test_password_protected_office_file_is_reported_as_encrypted() -> None:
    # Un DOCX protégé par mot de passe est un conteneur OLE « EncryptedPackage » / OLE-wrapped.
    data = make_cfb({"EncryptionInfo": b"\x04\x00\x04\x00", "EncryptedPackage": b"\x00" * 5000})
    with pytest.raises(EncryptedDocumentError):
        to_markdown(data, "secret.docx", LOCAL)


@pytest.mark.parametrize(("members", "match"), [
    ({"mimetype": b"application/vnd.oasis.opendocument.spreadsheet", "content.xml": b"<x/>"}, "tableur"),
    ({"[Content_Types].xml": b"<Types/>", "xl/workbook.xml": b"<x/>"}, "tableur"),
    ({"readme.txt": b"hello"}, "ZIP"),
    ({"mimetype": b"application/epub+zip"}, "ZIP"),
])
def test_unsupported_zip_packages(members: dict[str, bytes], match: str) -> None:
    with pytest.raises(UnsupportedFormatError, match=match):
        identify(zip_bytes(members), "zip")


def test_ooxml_main_part_found_from_content_types() -> None:
    types = (b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override '
             b'PartName="/doc/main.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.'
             b'document.main+xml"/></Types>')
    assert identify(zip_bytes({"[Content_Types].xml": types, "doc/main.xml": b"<x/>"}), "zip").kind == "docx"
