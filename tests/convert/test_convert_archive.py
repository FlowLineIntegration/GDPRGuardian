"""Garde ZIP et refus des DTD / ZIP guard and DTD rejection."""

from __future__ import annotations

import io
import zipfile

import pytest
from convert_samples import make_docx, make_odt, make_pptx, rewrite_zip, zip_bytes

from gdprguardian.convert import to_markdown
from gdprguardian.convert._archive import SafeArchive, ZipLimits, relationships
from gdprguardian.documents import DocumentError, DocumentOptions, EncryptedDocumentError, MaliciousDocumentError

LOCAL = DocumentOptions(sandbox=False)
BOMB_XML = (b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>'
            b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">&lol2;</w:document>')
XXE_XML = (b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
           b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">&xxe;</w:document>')


def test_zip_bomb_is_rejected_from_declared_sizes() -> None:
    bomb = zip_bytes({"[Content_Types].xml": b"<Types/>", "word/document.xml": b"\0" * (32 << 20)})
    assert len(bomb) < 64 << 10  # 32 Mio dans moins de 64 Kio / 32 MiB in under 64 KiB
    with pytest.raises(MaliciousDocumentError, match="bombe ZIP"):
        to_markdown(bomb, "a.docx", LOCAL)


def test_oversized_member_is_rejected() -> None:
    data = zip_bytes({"a.bin": bytes(range(256)) * 8192}, zipfile.ZIP_STORED)
    with pytest.raises(MaliciousDocumentError, match="volumineuse"):
        SafeArchive(data, ZipLimits(max_member_size=1 << 20))


def test_too_many_members_is_rejected() -> None:
    with pytest.raises(MaliciousDocumentError, match="entrées"):
        SafeArchive(zip_bytes({f"f{i}.xml": b"x" for i in range(60)}), ZipLimits(max_members=50))


def test_total_expanded_size_is_capped() -> None:
    data = zip_bytes({f"m{i}.bin": bytes(range(256)) * 4096 for i in range(4)}, zipfile.ZIP_STORED)
    with pytest.raises(MaliciousDocumentError):
        SafeArchive(data, ZipLimits(max_total_size=3 << 20))


@pytest.mark.parametrize("name", ["../evil.xml", "/abs.xml", "C:/x.xml", "a/../../b.xml", "a\\..\\b.xml"])
def test_path_traversal_is_rejected(name: str) -> None:
    with pytest.raises(MaliciousDocumentError, match="chemin"):
        SafeArchive(zip_bytes({name: b"x"}))


def test_duplicate_members_are_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", b"<a/>")
        archive.writestr("WORD/document.xml", b"<b/>")
    with pytest.raises(MaliciousDocumentError, match="double"):
        SafeArchive(buffer.getvalue())


def test_encrypted_member_is_reported() -> None:
    data = bytearray(zip_bytes({"word/document.xml": b"<a/>"}))
    data[6] |= 0x1  # drapeau « chiffré » de l'en-tête local / local header "encrypted" flag
    central = data.rfind(b"PK\x01\x02")
    data[central + 8] |= 0x1
    with pytest.raises(EncryptedDocumentError):
        SafeArchive(bytes(data))


def test_garbage_zip_is_a_document_error() -> None:
    with pytest.raises(DocumentError, match="ZIP"):
        SafeArchive(b"PK\x03\x04 not really a zip")


def test_bounded_read_refuses_oversized_member() -> None:
    archive = SafeArchive(zip_bytes({"big.xml": b"<a>" + b"x" * 5000 + b"</a>"}))
    assert archive.read("missing.xml") is None
    assert archive.read("BIG.XML") is not None  # casse ignorée (OPC) / case-insensitive (OPC)
    with pytest.raises(MaliciousDocumentError):
        archive.read("big.xml", limit=100)


@pytest.mark.parametrize("payload", [BOMB_XML, XXE_XML])
def test_dtd_in_any_member_is_rejected_before_parsers(payload: bytes) -> None:
    for builder, member in ((make_docx, "word/document.xml"), (make_pptx, "ppt/presentation.xml"),
                            (make_odt, "content.xml"), (make_docx, "customXml/item1.xml")):
        data = rewrite_zip(builder(), {member: payload})
        with pytest.raises(MaliciousDocumentError, match="DTD"):
            to_markdown(data, "doc", LOCAL)


def test_dtd_in_an_encoding_expat_cannot_read_is_still_found() -> None:
    # expat refuse Shift_JIS ou UTF-7, que lxml (python-pptx) sait lire : la DTD est cherchée après décodage.
    # expat rejects Shift_JIS or UTF-7, which lxml (python-pptx) reads: the DTD is searched after decoding.
    for encoding, dtd in (("Shift_JIS", b"<!DOCTYPE x [<!ENTITY a 'b'>]>"), ("UTF-7", b"+ADw-!DOCTYPE x+AD4-")):
        payload = b'<?xml version="1.0" encoding="' + encoding.encode() + b'"?>' + dtd + b"<x/>"
        with pytest.raises(MaliciousDocumentError, match="DTD"):
            to_markdown(rewrite_zip(make_docx(), {"customXml/item1.xml": payload}), "a.docx", LOCAL)
    unknown = b'<?xml version="1.0" encoding="x-inconnu"?><x/>'
    with pytest.raises(DocumentError, match="ZIP"):
        to_markdown(rewrite_zip(make_docx(), {"customXml/item1.xml": unknown}), "a.docx", LOCAL)


def test_dtd_after_long_prolog_is_still_found() -> None:
    payload = b'<?xml version="1.0"?>' + b"<!--" + b"x" * 200_000 + b"-->" + BOMB_XML[21:]
    with pytest.raises(MaliciousDocumentError):
        to_markdown(rewrite_zip(make_docx(), {"word/document.xml": payload}), "a.docx", LOCAL)


def test_binary_members_do_not_trip_the_prolog_check() -> None:
    archive = SafeArchive(zip_bytes({"media/image.png": b"\x89PNG\r\n\x1a\n" + bytes(range(256)),
                                     "a.xml": b"<?xml version='1.0'?><root/>", "empty.xml": b""}))
    archive.check_xml_prologs()


def test_relationships_resolve_relative_and_absolute_targets() -> None:
    rels = (b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="r1" Type="http://x/header" Target="header1.xml"/>'
            b'<Relationship Id="r2" Type="http://x/footer" Target="/word/footer1.xml"/>'
            b'<Relationship Id="r3" Type="http://x/image" Target="../media/a.png"/>'
            b'<Relationship Id="r4" Type="http://x/hyperlink" Target="https://evil.example" TargetMode="External"/>'
            b"</Relationships>")
    archive = SafeArchive(zip_bytes({"word/_rels/document.xml.rels": rels}))
    found = {(rel.type, rel.target, rel.external) for rel in relationships(archive, "word/document.xml")}
    assert found == {("header", "word/header1.xml", False), ("footer", "word/footer1.xml", False),
                     ("image", "media/a.png", False), ("hyperlink", "https://evil.example", True)}
