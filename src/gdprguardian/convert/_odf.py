"""OpenDocument (ODT, ODP, ODG, XML plat) -> Markdown, analysé par defusedxml.

OpenDocument (ODT, ODP, ODG, flat XML) -> Markdown, parsed with defusedxml.
Politique / policy : révisions acceptées (text:tracked-changes, qui contient le texte supprimé, n'est
jamais lu), commentaires sans auteur ni date et seulement si `include_comments`, notes de bas de page
en [^n], en-têtes et pieds de page des pages maîtresses, meta.xml jamais émis, sections, paragraphes et
passages masqués selon `include_hidden`. Les répétitions de colonnes ou de lignes (bombes ODS) ne sont
jamais développées.
Tracked changes accepted (text:tracked-changes, which holds deleted text, is never read), comments
without author or date and only with `include_comments`, footnotes as [^n], master-page headers and
footers, meta.xml never output, hidden sections, paragraphs and spans per `include_hidden`. Repeated
columns or rows (ODS bombs) are never expanded.
"""

from __future__ import annotations

from collections.abc import Iterator
from xml.etree.ElementTree import Element

from ..documents import ConvertedDocument, DocumentOptions
from ._archive import odf_meta_fields, odf_metadata_count, parse_xml
from ._base import Report, Source, corrupt, too_large, unsupported
from ._markdown import bullet_list, gfm_table, heading, image, inline, join_blocks, section


def _tags(namespace: str, *names: str) -> tuple[str, ...]:
    return tuple(f"{{urn:oasis:names:tc:opendocument:xmlns:{namespace}}}{name}" for name in names)


_OFFICE_BODY, _OFFICE_TEXT, _OFFICE_PRESENTATION, _OFFICE_DRAWING, _OFFICE_SPREADSHEET, _ANNOTATION = _tags(
    "office:1.0", "body", "text", "presentation", "drawing", "spreadsheet", "annotation")
_P, _H, _LIST, _LIST_ITEM, _LIST_HEADER, _SPACE, _TAB, _LINE_BREAK, _NOTE, _NOTE_BODY = _tags(
    "text:1.0", "p", "h", "list", "list-item", "list-header", "s", "tab", "line-break", "note", "note-body")
_TRACKED_CHANGES, _DELETION, _OUTLINE_LEVEL, _SPACE_COUNT = _tags(
    "text:1.0", "tracked-changes", "deletion", "outline-level", "c")
_SECTION, _SPAN, _LINK, _DISPLAY, _TEXT_STYLE, _HIDDEN_PARAGRAPH, _IS_HIDDEN = _tags(
    "text:1.0", "section", "span", "a", "display", "style-name", "hidden-paragraph", "is-hidden")
_HREF = "{http://www.w3.org/1999/xlink}href"
_TABLE, _ROW = _tags("table:1.0", "table", "table-row")
_DRAW_NS = "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}"
_FRAME, _IMAGE, _TEXT_BOX, _PAGE, _STYLE_NAME = _tags("drawing:1.0", "frame", "image", "text-box", "page", "style-name")
_NOTES, _CLASS, _VISIBILITY = _tags("presentation:1.0", "notes", "class", "visibility")
_MASTER_PAGE, _STYLE, _FAMILY, _NAME, _PAGE_PROPERTIES, _TEXT_PROPERTIES = _tags(
    "style:1.0", "master-page", "style", "family", "name", "drawing-page-properties", "text-properties")
_ALT_TEXT = frozenset(_tags("svg-compatible:1.0", "title", "desc"))

_EMPTY_INLINE = frozenset(_tags("office:1.0", "annotation-end") + _tags(
    "text:1.0", "change-start", "change-end", "change", "bookmark", "bookmark-start", "bookmark-end",
    "soft-page-break", "reference-mark-start", "reference-mark-end", "alphabetical-index-mark", "toc-mark"))
_SKIPPED_BLOCKS = frozenset(_tags("office:1.0", "forms") + _tags(
    "text:1.0", "sequence-decls", "variable-decls", "user-field-decls", "dde-connection-decls",
    "alphabetical-index-source", "table-of-content-source") + _tags("drawing:1.0", "page-thumbnail") + tuple(_ALT_TEXT))
_EMBEDDED = frozenset(_tags("drawing:1.0", "object", "object-ole", "plugin", "applet"))
_ROW_CONTAINERS = frozenset(_tags("table:1.0", "table-header-rows", "table-rows", "table-row-group"))
_CELLS = frozenset(_tags("table:1.0", "table-cell", "covered-table-cell"))
_HEADER_FOOTERS = frozenset(_tags("style:1.0", "header", "header-first", "header-left", "footer", "footer-first",
                                  "footer-left"))
_PAGE_DECLS = frozenset(_tags("presentation:1.0", "header-decl", "footer-decl"))


class _Walker:
    """Parcours du XML OpenDocument vers des blocs Markdown / OpenDocument XML walk into Markdown blocks."""

    def __init__(self, options: DocumentOptions, report: Report, hidden_styles: frozenset[str]) -> None:
        self.options = options
        self.report = report
        # Styles « text:display=none » ; vide si le texte masqué est demandé / empty when hidden text is wanted.
        self.hidden_styles = frozenset() if options.include_hidden else hidden_styles
        self.notes: list[str] = []
        self.comments: list[str] = []
        self.stories: list[str] = []
        self.cells = 0

    # --- blocs / blocks ---

    def blocks(self, element: Element) -> list[str]:
        out: list[str] = []
        for child in element:
            tag = child.tag
            if not self.options.include_hidden and self._hidden_block(child):
                continue
            if tag in (_P, _H):
                extra: list[str] = []
                text = inline(self.inline(child, extra)) if tag == _H else self.inline(child, extra).strip()
                if text:
                    out.append(heading(_int(child.get(_OUTLINE_LEVEL), 1), text) if tag == _H else text)
                out.extend(extra)
            elif tag == _LIST:
                out.append(self.list(child, 0))
            elif tag == _TABLE:
                out.append(self.table(child))
            elif tag == _TRACKED_CHANGES:
                # Contient le texte supprimé : jamais lu, seulement compté / holds deleted text: counted only.
                self.report.drop("tracked_deletions", sum(1 for _ in child.iter(_DELETION)))
            elif tag == _ANNOTATION:
                self.annotation(child)
            elif tag == _FRAME:
                out.extend(self.frame(child))
            elif tag in _PAGE_DECLS:
                self.story(" ".join(self.blocks(child)) or (child.text or ""))
            elif tag not in _SKIPPED_BLOCKS:
                out.extend(self.blocks(child))  # section, zone de texte, index... / section, text box, index...
        return out

    def inline(self, element: Element, extra: list[str]) -> str:
        """Texte d'un paragraphe ; les cadres ancrés vont dans `extra` / paragraph text; anchored frames to `extra`."""
        parts: list[str] = []
        self._inline(element, parts, extra)
        return "".join(parts)

    def _inline(self, element: Element, parts: list[str], extra: list[str]) -> None:
        if element.text:
            parts.append(element.text)
        for child in element:
            tag = child.tag
            if tag == _SPACE:
                parts.append(" " * min(_int(child.get(_SPACE_COUNT), 1), 16))
            elif tag == _TAB:
                parts.append("\t")
            elif tag == _LINE_BREAK:
                parts.append("\n")
            elif tag == _NOTE:
                parts.append(self.note(child))
            elif tag == _ANNOTATION:
                self.annotation(child)
            elif tag == _FRAME:
                extra.extend(self.frame(child))
            elif tag.startswith(_DRAW_NS):
                extra.extend(self.blocks(child))  # formes dessinées ancrées / anchored drawing shapes
            elif tag == _SPAN and child.get(_TEXT_STYLE) in self.hidden_styles:
                self.report.drop("hidden_text")
            elif tag not in _EMPTY_INLINE:
                if tag == _LINK and not child.get(_HREF, "#").startswith("#"):
                    self.report.drop("links")  # cible jamais émise, texte gardé / target never output, text kept
                self._inline(child, parts, extra)  # span, lien, champ... / span, link, field...
            if child.tail:
                parts.append(child.tail)

    def _hidden_block(self, element: Element) -> bool:
        """Section ou paragraphe masqué, compté / hidden section or paragraph, counted."""
        tag = element.tag
        if tag == _SECTION:
            hidden = element.get(_DISPLAY) == "none"
        elif tag in (_P, _H):
            marker = element.find(_HIDDEN_PARAGRAPH)
            hidden = element.get(_TEXT_STYLE) in self.hidden_styles or (
                marker is not None and marker.get(_IS_HIDDEN) == "true")
        else:
            return False
        if hidden:
            self.report.drop("hidden_content")
        return hidden

    def list(self, element: Element, depth: int) -> str:
        lines: list[str] = []
        indent = "  " * min(depth, 8)
        for item in element:
            if item.tag not in (_LIST_ITEM, _LIST_HEADER):
                continue
            for child in item:
                if not self.options.include_hidden and self._hidden_block(child):
                    continue
                if child.tag in (_P, _H):
                    extra: list[str] = []
                    text = inline(self.inline(child, extra))
                    if text:
                        lines.append(f"{indent}- {text}")
                    lines.extend(extra)
                elif child.tag == _LIST:
                    lines.append(self.list(child, depth + 1))
                else:
                    lines.extend(self.blocks(_wrap(child)))
        return "\n".join(line for line in lines if line)

    def table(self, element: Element) -> str:
        rows: list[list[str]] = []
        for row in _table_rows(element):
            # number-columns-repeated jamais développé (bombe ODS) / never expanded (ODS bomb).
            cells = [" ".join(self.blocks(cell)) for cell in row if cell.tag in _CELLS]
            while cells and not cells[-1]:
                cells.pop()
            if cells:
                self.cells += len(cells)
                if self.cells > self.options.max_cells:
                    raise too_large("cellules de tableau", "table cells", self.options.max_cells)
                rows.append(cells)
        return gfm_table(rows)

    def frame(self, element: Element) -> list[str]:
        out: list[str] = []
        for child in element:
            tag = child.tag
            if tag == _IMAGE:
                self.report.drop("images")
                out.append(image(" ".join(alt.text or "" for alt in element if alt.tag in _ALT_TEXT)))
            elif tag in _EMBEDDED:
                self.report.drop("embedded_objects")
            elif tag == _TEXT_BOX:
                out.extend(self.blocks(child))
            elif tag not in _SKIPPED_BLOCKS:
                out.extend(self.blocks(_wrap(child)))
        return out

    # --- annexes / side channels ---

    def note(self, element: Element) -> str:
        body = element.find(_NOTE_BODY)
        text = inline(" ".join(self.blocks(body))) if body is not None else ""
        if not text:
            return ""
        self.notes.append(f"[^{len(self.notes) + 1}]: {text}")
        return f"[^{len(self.notes)}]"

    def annotation(self, element: Element) -> None:
        """Texte du commentaire seulement : dc:creator et dc:date ne sont jamais lus / text only, no creator."""
        holder = Element("holder")
        holder.extend([child for child in element if child.tag in (_P, _LIST)])
        text = inline(" ".join(self.blocks(holder)))
        if not text:
            return
        if self.options.include_comments:
            self.comments.append(text)
        else:
            self.report.drop("comments")

    def story(self, text: str) -> None:
        text = inline(text)
        if text and text not in self.stories:
            self.stories.append(text)

    def master_pages(self, root: Element) -> None:
        for master in root.iter(_MASTER_PAGE):
            for child in master:
                if child.tag in _HEADER_FOOTERS:
                    for block in self.blocks(child):
                        self.story(block)

    def slides(self, container: Element, hidden_styles: frozenset[str], label: str) -> list[str]:
        pages = [child for child in container if child.tag == _PAGE]
        if len(pages) > self.options.max_pages:
            raise too_large("diapositives", "slides", self.options.max_pages)
        for child in container:
            if child.tag in _PAGE_DECLS:
                self.story(" ".join(self.blocks(child)) or (child.text or ""))
        out: list[str] = []
        for number, page in enumerate(pages, 1):
            hidden = page.get(_STYLE_NAME) in hidden_styles
            if hidden and not self.options.include_hidden:
                self.report.drop("hidden_slides")
                continue
            title = ""
            body: list[str] = []
            notes = ""
            for child in page:
                if child.tag == _NOTES:
                    notes = "\n\n".join(self.blocks(child))
                elif child.tag == _FRAME and child.get(_CLASS) == "title" and not title:
                    title = inline(" ".join(self.frame(child)))
                elif child.tag == _FRAME:
                    body.extend(self.frame(child))
                elif child.tag not in _SKIPPED_BLOCKS:
                    body.extend(self.blocks(_wrap(child)))
            name = f"{label} {number}" + (" (masquée)" if hidden else "")
            out.append(heading(2, f"{name} : {title}" if title else name))
            out.extend(body)
            if notes.strip():
                if self.options.include_speaker_notes:
                    out.append(section("Notes", notes, level=3))
                else:
                    self.report.drop("speaker_notes")
        return out


def _int(value: str | None, default: int) -> int:
    try:
        return max(int(value), 1) if value is not None else default
    except ValueError:
        return default


def _wrap(element: Element) -> Element:
    """Conteneur factice pour traiter un élément comme un bloc / dummy container to walk one element."""
    holder = Element("holder")
    holder.append(element)
    return holder


def _table_rows(table: Element) -> Iterator[Element]:
    for child in table:
        if child.tag == _ROW:
            yield child
        elif child.tag in _ROW_CONTAINERS:
            yield from _table_rows(child)


def _hidden_styles(*roots: Element | None) -> tuple[frozenset[str], frozenset[str]]:
    """Styles masqués : pages ODP (« visibility=hidden ») et texte (« text:display=none »).

    Hidden styles: ODP pages (visibility=hidden) and text or paragraphs (text:display=none).
    """
    pages: set[str] = set()
    text: set[str] = set()
    for root in roots:
        for style in root.iter(_STYLE) if root is not None else ():
            family = style.get(_FAMILY)
            if family == "drawing-page":
                properties = style.find(_PAGE_PROPERTIES)
                if properties is not None and properties.get(_VISIBILITY) == "hidden":
                    pages.add(style.get(_NAME, ""))
            elif family in ("text", "paragraph"):
                properties = style.find(_TEXT_PROPERTIES)
                if properties is not None and properties.get(_DISPLAY) == "none":
                    text.add(style.get(_NAME, ""))
    return frozenset(pages), frozenset(text)


def convert(source: Source, options: DocumentOptions) -> ConvertedDocument:
    report = Report()
    kind = "odt" if source.kind == "odf-xml" else source.kind
    if source.archive is None:  # XML plat (.fodt, .fodp) / flat XML
        content = styles = parse_xml(source.data, kind)
        report.drop("metadata", odf_meta_fields(content))
    else:
        content = source.archive.xml("content.xml")
        if content is None:
            raise corrupt(kind)
        styles = source.archive.xml("styles.xml")
        report.drop("metadata", odf_metadata_count(source.archive))
    body = content.find(_OFFICE_BODY)
    if body is None:
        raise corrupt(kind)
    hidden_pages, hidden_text = _hidden_styles(content, styles if styles is not content else None)
    walker = _Walker(options, report, hidden_text)
    pages: int | None = None
    text = body.find(_OFFICE_TEXT)
    deck = body.find(_OFFICE_PRESENTATION)
    if deck is None:
        deck = body.find(_OFFICE_DRAWING)
    if text is not None:
        kind, blocks = "odt", walker.blocks(text)
        if styles is not None:
            walker.master_pages(styles)
    elif deck is not None:
        kind = "odg" if deck.tag == _OFFICE_DRAWING else "odp"
        blocks = walker.slides(deck, hidden_pages, "Page" if kind == "odg" else "Diapositive")
        pages = sum(1 for child in deck if child.tag == _PAGE)
    elif body.find(_OFFICE_SPREADSHEET) is not None:
        raise unsupported("classeur détecté : utiliser une extension de tableur (.ods)",
                          "spreadsheet detected: use a spreadsheet file extension (.ods)")
    else:
        raise corrupt(kind)
    markdown = join_blocks([*blocks, section("En-têtes et pieds de page", bullet_list(walker.stories)),
                            section("Commentaires", bullet_list(walker.comments)), "\n".join(walker.notes)])
    return report.document(markdown, kind, pages)


__all__ = ["convert"]
