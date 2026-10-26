"""PDF -> Markdown : pypdfium2 page par page, titres par la taille réelle des glyphes, champs via pypdf.

PDF -> Markdown: pypdfium2 page by page, headings from the real glyph size, form fields through pypdf.
La taille vient de la boîte « large » des caractères (matrice de texte comprise), pas de la taille de police
déclarée, souvent égale à 1. Les lignes d'un même paragraphe sont recollées (un IBAN coupé en fin de ligne
reste détectable) ; les pages sans texte mais couvertes d'images sont signalées comme numérisées.
Size comes from the loose glyph box (text matrix included), not the declared font size, often 1. Lines of
one paragraph are re-joined (an IBAN split across lines stays detectable); text-less, image-covered pages
are reported as scanned.
"""

from __future__ import annotations

import ctypes
import io
import re
import threading
from dataclasses import dataclass
from typing import Any

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from ..documents import ConvertedDocument, DocumentOptions
from ._base import Report, Source, corrupt, encrypted, too_large
from ._markdown import attachment, bullet_list, clip, heading, join_blocks, section

_LOCK = threading.Lock()  # pdfium n'est pas sûr entre threads / pdfium is not thread-safe
_MAX_ITEMS = 10_000
_MAX_VALUE = 10_000
_MAX_NAME = 255
_COLUMN_STEP = 12.0  # pas de regroupement des marges gauches (pt) / left-margin bucket size (pt)
_BOLD_MARKERS = (b"bold", b"black", b"heavy", b"semibold", b"demibold")
_FORCE_BOLD = 1 << 18
_SKIPPED_ANNOTS = frozenset({pdfium_c.FPDF_ANNOT_LINK, pdfium_c.FPDF_ANNOT_POPUP, pdfium_c.FPDF_ANNOT_WIDGET})
# Puces, dont celles des polices Symbol et Wingdings (zone privée) / bullets, incl. Symbol and Wingdings (PUA).
_BULLETS = frozenset("\N{BULLET}\N{BLACK SMALL SQUARE}\N{WHITE BULLET}\N{BLACK CIRCLE}\N{BLACK SQUARE}"
                     "\N{WHITE SQUARE}\N{EN DASH}\U0000f0b7\U0000f0a7\U0000f076\U0000f0d8\U0000f0fc")
_LETTER_RE = re.compile(r"[^\W\d_]")
# pdfium marque par U+FFFE (ou U+0002) le tiret de césure retiré / pdfium marks a removed hyphenation dash.
_SOFT_HYPHEN_RE = re.compile("[\U0000fffe\x02](?=[a-z\xe0-\xf6\xf8-\xff])")
_HARD_HYPHEN_RE = re.compile("[\U0000fffe\x02]")
SCANNED_PLACEHOLDER = "[PAGE NUMÉRISÉE SANS TEXTE]"


@dataclass(slots=True)
class _Line:
    text: str
    height: float  # hauteur de la boîte large = taille effective / loose box height = effective size
    left: float
    right: float
    top: float
    bottom: float
    bold: bool
    level: int = 0  # 0 : corps ; 1 à 3 : titre / 0: body; 1-3: heading


@dataclass(slots=True)
class _Extracted:
    """Ce que pdfium a lu / what pdfium read."""

    blocks: list[str]  # pages rendues, marqueurs compris / rendered pages, markers included
    added: list[str]
    comments: list[str]
    attachments: list[str]
    page_count: int
    form_type: int


def convert(source: Source, options: DocumentOptions) -> ConvertedDocument:
    report = Report()
    with _LOCK:
        try:
            pdf = pdfium.PdfDocument(source.data)
        except pdfium.PdfiumError as exc:
            if getattr(exc, "err_code", None) in (pdfium_c.FPDF_ERR_PASSWORD, pdfium_c.FPDF_ERR_SECURITY):
                raise encrypted() from None
            raise corrupt("pdf") from None
        try:
            extracted = _extract(pdf, options, report)
        finally:
            pdf.close()
    # pypdf (Python pur, sûr entre threads) tourne hors du verrou de pdfium / pypdf runs outside pdfium's lock.
    fields = _form_fields(extracted.form_type, source.data, report)
    markdown = join_blocks([*extracted.blocks, section("Champs de formulaire", bullet_list(fields)),
                            section("Texte ajouté (annotations)", bullet_list(extracted.added)),
                            section("Commentaires", bullet_list(extracted.comments)),
                            section("Pièces jointes", bullet_list(extracted.attachments))])
    return report.document(markdown, "pdf", extracted.page_count)


def _extract(pdf: Any, options: DocumentOptions, report: Report) -> _Extracted:
    page_count = len(pdf)
    if page_count > options.max_pages:
        raise too_large("pages", "pages", options.max_pages)
    report.drop("metadata", _metadata_count(pdf))
    pages: list[list[_Line]] = []
    scanned: set[int] = set()
    comments: list[str] = []
    added: list[str] = []
    for index in range(page_count):
        try:
            page = pdf[index]
        except pdfium.PdfiumError:
            report.warn("Page PDF illisible ignorée / unreadable PDF page skipped")
            pages.append([])
            continue
        try:
            lines = _page_lines(page)
            if _is_scanned(page, lines):
                scanned.add(index)
            _annotations(page, index + 1, options, report, comments, added)
        finally:
            page.close()
        pages.append(lines)
    _classify(pages)

    blocks: list[str] = []
    for index, lines in enumerate(pages):
        blocks.append(f"<!-- page {index + 1} -->")
        if index in scanned:
            blocks.append(SCANNED_PLACEHOLDER)
        blocks.extend(_render_page(lines))
    if scanned:
        report.drop("scanned_pages", len(scanned))
        report.warn(f"{len(scanned)} page(s) numérisée(s) sans couche texte : contenu non extrait / {len(scanned)} "
                    "scanned page(s) without a text layer: content not extracted")
        if options.ocr:
            report.warn("OCR demandé mais aucun moteur OCR n'est disponible / OCR requested but no OCR engine is "
                        "available")
    return _Extracted(blocks, added, comments, _attachments(pdf, report), page_count,
                      pdfium_c.FPDF_GetFormType(pdf.raw))


def _metadata_count(pdf: Any) -> int:
    """Entrées /Info non vides, comptées sans être lues / non-empty /Info entries, counted, never read."""
    return sum(1 for key in pdf.METADATA_KEYS
               if pdfium_c.FPDF_GetMetaText(pdf.raw, f"{key}\x00".encode("ascii"), None, 0) > 2)


# --- texte et géométrie / text and geometry -----------------------------------------------------------


def _page_text(raw: Any) -> str:
    count = pdfium_c.FPDFText_CountChars(raw)
    if count <= 0:
        return ""
    last = pdfium_c.FPDFText_GetTextIndexFromCharIndex(raw, count - 1)
    units = max(count, last + 1) * 2 + 2  # marge pour les paires de substitution / room for surrogate pairs
    buffer = (ctypes.c_ushort * units)()
    written = pdfium_c.FPDFText_GetText(raw, 0, count, buffer)
    return bytes(memoryview(buffer)[:max(min(written, units) - 1, 0)]).decode("utf-16-le", errors="ignore")


def _page_lines(page: Any) -> list[_Line]:
    textpage = page.get_textpage()
    try:
        raw = textpage.raw
        text = _page_text(raw)
        if not text.strip():
            return []
        rect = pdfium_c.FS_RECTF()
        flags = ctypes.c_int()
        name = ctypes.create_string_buffer(256)
        lines: list[_Line] = []
        pos = 0
        for line in text.split("\r\n"):
            content = line.strip()
            if content:
                first = _char_box(raw, pos + len(line) - len(line.lstrip()), rect)
                last = _char_box(raw, pos + len(line.rstrip()) - 1, rect)
                if first is not None and last is not None:
                    char_index, left, top, _right, bottom = first
                    _, _, last_top, right, last_bottom = last
                    bold = _is_bold(raw, char_index, name, flags)
                    lines.append(_Line(content, top - bottom, left, max(right, left), max(top, last_top),
                                       min(bottom, last_bottom), bold))
                else:
                    lines.append(_Line(content, 0.0, 0.0, 0.0, 0.0, 0.0, False))
            pos += len(line) + 2
        return lines
    finally:
        textpage.close()


def _char_box(raw: Any, text_index: int, rect: Any) -> tuple[int, float, float, float, float] | None:
    char_index = pdfium_c.FPDFText_GetCharIndexFromTextIndex(raw, text_index)
    if char_index < 0 or not pdfium_c.FPDFText_GetLooseCharBox(raw, char_index, rect):
        return None
    return char_index, rect.left, rect.top, rect.right, rect.bottom


def _is_bold(raw: Any, char_index: int, name: Any, flags: Any) -> bool:
    if pdfium_c.FPDFText_GetFontWeight(raw, char_index) >= 600:
        return True
    if not pdfium_c.FPDFText_GetFontInfo(raw, char_index, name, len(name), ctypes.byref(flags)):
        return False
    font = name.value.lower()
    return bool(flags.value & _FORCE_BOLD) or any(marker in font for marker in _BOLD_MARKERS)


def _is_scanned(page: Any, lines: list[_Line]) -> bool:
    """Peu de texte et images couvrant plus de la moitié de la page / little text, images over half the page."""
    if sum(len(line.text) for line in lines) >= 20:
        return False
    width, height = page.get_size()
    area = width * height
    if area <= 0:
        return False
    covered = 0.0
    for image in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=4):
        left, bottom, right, top = image.get_bounds()
        covered += max(0.0, right - left) * max(0.0, top - bottom)
        if covered >= 0.5 * area:
            return True
    return False


def _classify(pages: list[list[_Line]]) -> None:
    """Corps = taille dominante (pondérée par les caractères) ; titres = nettement plus grands ou gras.

    Body = dominant size (character-weighted); headings = clearly larger, or slightly larger and bold.
    """
    weights: dict[float, int] = {}
    for lines in pages:
        for line in lines:
            key = round(line.height * 2) / 2
            weights[key] = weights.get(key, 0) + len(line.text)
    if not weights:
        return
    body = max(weights, key=weights.__getitem__)
    if body <= 0:
        return
    candidates = [line for lines in pages for line in lines if _heading_candidate(line, body)]
    sizes = sorted({round(line.height * 2) / 2 for line in candidates}, reverse=True)
    levels = {size: min(rank, 3) for rank, size in enumerate(sizes, 1)}
    for line in candidates:
        line.level = levels[round(line.height * 2) / 2]


def _heading_candidate(line: _Line, body: float) -> bool:
    ratio = line.height / body
    text = line.text
    return ((ratio >= 1.15 or (ratio >= 1.05 and line.bold)) and len(text) <= 120 and text[-1] not in ".,;:"
            and _LETTER_RE.search(text) is not None)


def _starts_with_bullet(text: str) -> bool:
    return len(text) > 2 and text[0] in _BULLETS and text[1] in " \t\xa0"


def _render_page(lines: list[_Line]) -> list[str]:
    # Marge droite de chaque colonne (lignes de même marge gauche, à 12 pt près).
    # Right margin of each column (lines sharing a left margin, within 12 pt).
    margins: dict[int, float] = {}
    for line in lines:
        if not line.level:
            key = int(line.left // _COLUMN_STEP)
            margins[key] = max(margins.get(key, 0.0), line.right)
    blocks: list[str] = []
    block: list[_Line] = []
    for line in lines:
        if block and _new_block(block, line):
            blocks.append(_render_block(block, margins))
            block = []
        block.append(line)
    if block:
        blocks.append(_render_block(block, margins))
    return blocks


def _new_block(block: list[_Line], line: _Line) -> bool:
    previous = block[-1]
    if previous.level != line.level or (line.level and len(block) >= 2):
        return True
    if _starts_with_bullet(line.text) or previous.height <= 0 or line.height <= 0:
        return True
    if abs(line.height - previous.height) > 0.15 * max(line.height, previous.height):
        return True
    gap = previous.bottom - line.top
    # Grand blanc, ou remontée (colonne suivante) / large gap, or moving up (next column).
    return gap > 0.6 * previous.height or line.top > previous.top + 0.5 * previous.height


def _render_block(block: list[_Line], margins: dict[int, float]) -> str:
    texts = [_dehyphenate(line.text) for line in block]
    if block[0].level:
        return heading(block[0].level, " ".join(texts))
    if _starts_with_bullet(texts[0]):
        texts[0] = "- " + texts[0][2:].lstrip()
    parts = [texts[0]]
    for previous, text in zip(block, texts[1:], strict=False):
        key = int(previous.left // _COLUMN_STEP)
        margin = max(margins.get(key - 1, 0.0), margins.get(key, 0.0), margins.get(key + 1, 0.0))
        width = margin - previous.left
        # Ligne pleine = retour automatique : on recolle ; sinon vrai saut de ligne (adresse, liste...).
        # Full line = automatic wrap: re-join; otherwise a real line break (address, list...).
        if previous.right < margin - min(4 * previous.height, 0.2 * width):
            parts.append("\n")
        elif not parts[-1].endswith("-"):
            parts.append(" ")
        parts.append(text)
    return "".join(parts)


def _dehyphenate(text: str) -> str:
    if "\U0000fffe" in text or "\x02" in text:
        text = _HARD_HYPHEN_RE.sub("-", _SOFT_HYPHEN_RE.sub("", text))
    return text


# --- annotations, formulaires, pièces jointes / annotations, forms, attachments -----------------------


def _annotations(page: Any, number: int, options: DocumentOptions, report: Report, comments: list[str],
                 added: list[str]) -> None:
    """Texte libre ajouté (visible) toujours émis ; notes et surlignages selon `include_comments`.

    Added free text (visible) is always output; notes and highlights follow `include_comments`.
    """
    raw = page.raw
    for index in range(min(pdfium_c.FPDFPage_GetAnnotCount(raw), _MAX_ITEMS)):
        annot = pdfium_c.FPDFPage_GetAnnot(raw, index)
        if not annot:
            continue
        try:
            subtype = pdfium_c.FPDFAnnot_GetSubtype(annot)
            if subtype in _SKIPPED_ANNOTS:
                continue
            text = _annotation_contents(annot)
            if not text:
                continue
            if subtype == pdfium_c.FPDF_ANNOT_FREETEXT:
                added.append(f"page {number} : {text}")
            elif options.include_comments:
                comments.append(f"page {number} : {text}")
            else:
                report.drop("comments")
        finally:
            pdfium_c.FPDFPage_CloseAnnot(annot)


def _annotation_contents(annot: Any) -> str:
    size = pdfium_c.FPDFAnnot_GetStringValue(annot, b"Contents", None, 0)
    if size <= 2:
        return ""
    buffer = ctypes.create_string_buffer(size)
    pdfium_c.FPDFAnnot_GetStringValue(annot, b"Contents", ctypes.cast(buffer, ctypes.POINTER(pdfium_c.FPDF_WCHAR)),
                                      size)
    return clip(buffer.raw[:size - 2].decode("utf-16-le", errors="ignore"), _MAX_VALUE)


def _form_fields(form_type: int, data: bytes, report: Report) -> list[str]:
    if form_type == pdfium_c.FORMTYPE_NONE:
        return []
    if form_type in (pdfium_c.FORMTYPE_XFA_FULL, pdfium_c.FORMTYPE_XFA_FOREGROUND):
        report.warn("Formulaire XFA : valeurs dynamiques non extraites / XFA form: dynamic values not extracted")
    import pypdf

    try:
        reader = pypdf.PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError
        fields = reader.get_fields() or {}
        items = []
        for name, field in list(fields.items())[:_MAX_ITEMS]:
            value = _field_value(field.get("/V"))
            if value:
                items.append(f"{clip(str(name), _MAX_NAME)} : {value}")
        return items
    except Exception:  # pypdf lève des types variés sur un PDF abîmé / pypdf raises assorted types
        report.warn("Champs de formulaire illisibles / unreadable form fields")
        return []


def _field_value(value: Any, depth: int = 0) -> str:
    """Valeur lisible d'un champ (texte, case, liste) / readable field value (text, checkbox, list)."""
    if value is None or depth > 4:
        return ""
    if hasattr(value, "get_object"):
        value = value.get_object()
    if isinstance(value, (list, tuple)):
        return ", ".join(filter(None, (_field_value(item, depth + 1) for item in value[:100])))
    if isinstance(value, bytes):
        value = value.decode("latin-1")
    text = clip(str(value), _MAX_VALUE)
    if text.startswith("/"):  # nom PDF : case cochée / PDF name: checkbox state
        text = "" if text == "/Off" else text[1:]
    return text


def _attachments(pdf: Any, report: Report) -> list[str]:
    """Pièces jointes par numéro et extension, jamais par nom (souvent celui d'une personne) / by number and
    extension, never by name (often a person's)."""
    count = pdf.count_attachments()
    report.drop("attachments", count)
    listed = []
    for index in range(min(count, 1000)):
        try:
            name = clip(pdf.get_attachment(index).get_name(), _MAX_NAME)
        except (pdfium.PdfiumError, UnicodeError):
            name = ""
        stem, dot, extension = name.rpartition(".")
        listed.append(attachment(index + 1, extension.lower() if dot and stem else None))
    return listed


__all__ = ["SCANNED_PLACEHOLDER", "convert"]
