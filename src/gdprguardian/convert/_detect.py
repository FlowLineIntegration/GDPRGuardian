"""Identification du format par les octets, jamais par l'extension seule / format from bytes, never extension alone.

`sniff` ne lit que les premiers octets (sûr hors bac à sable) ; `identify` ouvre les conteneurs ZIP et OLE
(dans le bac à sable) pour distinguer DOCX, PPTX, ODT, MSG, .doc hérité ou document chiffré.
`sniff` only reads leading bytes (safe outside the sandbox); `identify` opens ZIP and OLE containers
(inside the sandbox) to tell DOCX, PPTX, ODT, MSG, legacy .doc or encrypted documents apart.
"""

from __future__ import annotations

import io
import re

from ._archive import SafeArchive
from ._base import Source, corrupt, encrypted, unsupported

PDF_MAGIC = b"%PDF-"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06")
_IMAGE_MAGICS = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"II*\x00", b"MM\x00*")
_ARCHIVE_MAGICS = (b"\x1f\x8b", b"7z\xbc\xaf\x27\x1c", b"Rar!\x1a\x07", b"BZh", b"\xfd7zXZ\x00", b"\x28\xb5\x2f\xfd")
_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")

HTML_EXTENSIONS = frozenset({".html", ".htm", ".xhtml", ".shtml"})
MAIL_EXTENSIONS = frozenset({".eml", ".mht", ".mhtml"})
MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown", ".mdown", ".mkd"})

_HEAD_SIZE = 16384
_SPREADSHEET = ("classeur détecté : utiliser une extension de tableur (.xlsx, .ods, .xls, .csv)",
                "spreadsheet detected: use a spreadsheet file extension (.xlsx, .ods, .xls, .csv)")

# Prologue HTML/XML ignoré avant la première balise / HTML/XML prolog skipped before the first tag.
_PROLOG_RE = re.compile(r"\s{0,256}(?:<\?[^>]{0,512}>|<!--.{0,8192}?-->|<!doctype\s[^>]{0,512}>)", re.S)
_FIRST_TAG_RE = re.compile(r"\s{0,256}<([a-z][a-z0-9:-]{0,31})[\s/>]")
_HTML_TAGS = frozenset({
    "html", "head", "body", "meta", "title", "base", "link", "style", "script", "div", "p", "span", "table",
    "br", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "header", "main", "nav", "ul", "ol", "a",
    "b", "i", "em", "strong", "font", "center", "form", "img", "pre", "blockquote", "hr",
})
# Racines des formats XML d'Office (Flat OPC, WordprocessingML 2003, SpreadsheetML 2003) / Office XML roots.
_OFFICE_XML_TAGS = frozenset({"pkg:package", "w:worddocument", "workbook", "ss:workbook"})
_HEADER_LINE_RE = re.compile(r"([!-9;-~]{1,76}):")
_MAIL_HEADERS = frozenset({
    "from", "to", "cc", "subject", "date", "message-id", "mime-version", "received", "return-path", "reply-to",
    "delivered-to", "content-type", "sender", "in-reply-to", "references", "x-mailer", "dkim-signature",
    "authentication-results", "thread-topic", "x-originating-ip",
})
_MAIL_CORE = frozenset({"from", "subject", "date", "message-id", "received", "mime-version"})


def sniff(data: bytes, extension: str) -> str:
    """Famille de format d'après les octets de tête / format family from the leading bytes.

    Renvoie / returns: pdf, zip, ole, rtf, html, eml, odf-xml, txt ou md. Lève `UnsupportedFormatError`
    pour les images, archives, XML Office et binaires inconnus / raises for images, archives, Office XML
    and unknown binaries.
    """
    head = data[:_HEAD_SIZE]
    stripped = head.lstrip(b" \t\r\n\x0c")
    if stripped.startswith(PDF_MAGIC) or (head.find(PDF_MAGIC, 0, 1024) >= 0 and (
            extension == ".pdf" or data.rfind(b"%%EOF", -2048) >= 0)):
        # Les lecteurs PDF tolèrent un préfixe : sinon le PDF brut (/Author compris) partirait en texte.
        # PDF readers accept a prefix: otherwise the raw PDF (/Author included) would be read as text.
        return "pdf"
    if head.startswith(_ZIP_MAGICS):
        return "zip"
    if head.startswith(OLE_MAGIC):
        return "ole"
    if stripped.lstrip(b"\xef\xbb\xbf").startswith(b"{\\rtf"):
        return "rtf"
    if head.startswith(_IMAGE_MAGICS) or (head[:4] == b"RIFF" and head[8:12] == b"WEBP") or (
            head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"avif", b"mif1")):
        raise unsupported("image sans couche texte, OCR non disponible", "image without a text layer, no OCR")
    if head.startswith(_ARCHIVE_MAGICS):
        raise unsupported("archive compressée", "compressed archive")
    if head.startswith(_UTF16_BOMS):
        text = head.decode("utf-16", errors="replace")
    elif b"\x00" in head and not head.startswith(b"\x00\x00\xfe\xff"):
        raise unsupported("binaire non reconnu", "unrecognised binary")
    else:
        text = head.decode("latin-1")
    return _text_family(text, extension)


def _text_family(text: str, extension: str) -> str:
    body = text.lstrip("\N{BYTE ORDER MARK}\xef\xbb\xbf \t\r\n")
    if body.startswith("<"):
        lower = body[:4096].lower()
        tag = _first_tag(lower)
        if tag == "!doctype" or tag in _HTML_TAGS or extension in HTML_EXTENSIONS:
            return "html"
        if tag in ("office:document", "office:document-content") and "urn:oasis:names:tc:opendocument" in lower:
            return "odf-xml"
        if tag in _OFFICE_XML_TAGS or "<?mso-application" in lower:
            # Lu comme du texte, son XML brut livrerait les métadonnées (auteur...) / raw XML would leak metadata.
            raise unsupported("XML Office (Word ou Excel 2003, « Flat OPC »), à enregistrer en .docx ou .xlsx",
                              "Office XML (Word or Excel 2003, Flat OPC), save it as .docx or .xlsx")
    elif _looks_like_mail(body, extension):
        return "eml"
    return "md" if extension in MARKDOWN_EXTENSIONS else "txt"


def _first_tag(lower: str) -> str | None:
    pos = 0
    for _ in range(32):
        match = _PROLOG_RE.match(lower, pos)
        if match is None:
            break
        if "<!doctype" in match.group() and "html" in match.group():
            return "!doctype"
        pos = match.end()
    match = _FIRST_TAG_RE.match(lower, pos)
    return match.group(1) if match else None


def _looks_like_mail(text: str, extension: str) -> bool:
    known = core = 0
    for index, line in enumerate(text.split("\n", 64)[:64]):
        line = line.rstrip("\r")
        if not line:
            break
        if index == 0 and line.startswith("From "):
            continue  # enveloppe mbox, comprise par le module email / mbox envelope, handled by the email module
        if line[0] in " \t" and index:
            continue  # ligne de continuation / folded header line
        match = _HEADER_LINE_RE.match(line)
        if match is None:
            return False
        name = match.group(1).lower()
        known += name in _MAIL_HEADERS
        core += name in _MAIL_CORE
    return (known >= 2 and core >= 1) or (extension in MAIL_EXTENSIONS and known >= 1)


# --- conteneurs (dans le bac à sable) / containers (inside the sandbox) ----------------------------

_ODF_KINDS = {
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.text-template": "odt",
    "application/vnd.oasis.opendocument.text-master": "odt",
    "application/vnd.oasis.opendocument.presentation": "odp",
    "application/vnd.oasis.opendocument.presentation-template": "odp",
    "application/vnd.oasis.opendocument.graphics": "odg",
    "application/vnd.oasis.opendocument.graphics-template": "odg",
}
_MAIN_PART_RE = re.compile(
    rb'ContentType="application/vnd\.(?:openxmlformats-officedocument\.(wordprocessingml|presentationml|spreadsheetml)'
    rb'|ms-(word|powerpoint|excel))\.[A-Za-z.]{1,64}\.main(?:\+xml)?"')
_OOXML_FAMILIES = {b"wordprocessingml": "docx", b"word": "docx", b"presentationml": "pptx", b"powerpoint": "pptx",
                   b"spreadsheetml": "xlsx", b"excel": "xlsx"}


def identify(data: bytes, family: str) -> Source:
    """Identification fine des conteneurs ; la garde ZIP s'exécute ici / fine identification, ZIP guard runs here."""
    if family == "zip":
        archive = SafeArchive(data)
        kind = _zip_kind(archive)
        archive.check_xml_prologs()
        return Source(data, kind, archive)
    if family == "ole":
        return Source(data, _ole_kind(data))
    return Source(data, family)


def _zip_kind(archive: SafeArchive) -> str:
    mimetype = archive.read("mimetype", 256)
    if mimetype is not None:
        name = mimetype.strip().decode("ascii", errors="replace")
        if name in _ODF_KINDS:
            return _odf_checked(archive, _ODF_KINDS[name])
        if name.startswith("application/vnd.oasis.opendocument.spreadsheet"):
            raise unsupported(*_SPREADSHEET)
        raise unsupported("archive ZIP non bureautique", "non-office ZIP archive")
    if archive.has("[Content_Types].xml"):
        kind = _ooxml_kind(archive)
        if kind == "xlsx":
            raise unsupported(*_SPREADSHEET)
        if kind is not None:
            return kind
        raise unsupported("paquet Office non pris en charge", "unsupported Office package")
    if archive.has("content.xml") and archive.has("META-INF/manifest.xml"):
        return _odf_checked(archive, "odt")
    raise unsupported("archive ZIP non bureautique", "non-office ZIP archive")


def _ooxml_kind(archive: SafeArchive) -> str | None:
    for part, kind in (("word/document.xml", "docx"), ("ppt/presentation.xml", "pptx"),
                       ("xl/workbook.xml", "xlsx"), ("xl/workbook.bin", "xlsx")):
        if archive.has(part):
            return kind
    types = archive.read("[Content_Types].xml", 1 << 20) or b""
    match = _MAIN_PART_RE.search(types)
    return _OOXML_FAMILIES[match.group(1) or match.group(2)] if match else None


def _odf_checked(archive: SafeArchive, kind: str) -> str:
    manifest = archive.read("META-INF/manifest.xml", 4 << 20) or b""
    if b"encryption-data" in manifest:
        raise encrypted()
    return kind


def _ole_kind(data: bytes) -> str:
    import olefile

    try:
        with olefile.OleFileIO(io.BytesIO(data)) as ole:
            names = {entry.name.lower() for entry in ole.root.kids}
    except Exception:  # olefile lève des types variés sur un fichier abîmé / olefile raises assorted types
        raise corrupt("ole") from None
    if "encryptedpackage" in names or "encryptioninfo" in names:
        raise encrypted()
    if "__properties_version1.0" in names and any(name.startswith("__substg1.0_") for name in names):
        return "msg"
    if "worddocument" in names:
        raise unsupported("Word 97-2003 (.doc), à enregistrer en .docx", "Word 97-2003 (.doc), save it as .docx")
    if "powerpoint document" in names:
        raise unsupported("PowerPoint 97-2003 (.ppt), à enregistrer en .pptx",
                          "PowerPoint 97-2003 (.ppt), save it as .pptx")
    if "workbook" in names or "book" in names:
        raise unsupported(*_SPREADSHEET)
    raise unsupported("conteneur OLE non reconnu", "unrecognised OLE container")


__all__ = ["HTML_EXTENSIONS", "MAIL_EXTENSIONS", "MARKDOWN_EXTENSIONS", "identify", "sniff"]
