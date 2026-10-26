"""DOCX -> Markdown : mammoth pour le corps, XML direct (defusedxml) pour en-têtes, pieds de page et commentaires.

DOCX -> Markdown: mammoth for the body, direct XML (defusedxml) for headers, footers and comments.
Politique / policy : révisions acceptées (insertions gardées, suppressions jamais émises, comptées) ;
commentaires seulement si `include_comments`, sans auteur ni initiales ; images -> [IMAGE: alt] sans
lire leurs octets ; métadonnées (docProps) jamais émises ; texte masqué (w:vanish en mise en forme
directe) selon `include_hidden`. Lire les en-têtes directement évite une seconde analyse complète de
document.xml (python-docx analyse toutes les parties à l'ouverture).
Tracked changes accepted (insertions kept, deletions never output, counted); comments only with
`include_comments`, without author or initials; images -> [IMAGE: alt] without reading their bytes;
metadata (docProps) never output; hidden text (direct w:vanish) per `include_hidden`. Reading headers
directly avoids a second full parse of document.xml (python-docx parses every part on open).

mammoth construit son arbre XML avec minidom (Python pur, ~95 % de son temps). On lui fournit le même
arbre construit par defusedxml : 5 fois plus rapide, et aucune DTD acceptée (`_install_fast_parser`).
mammoth builds its XML tree with minidom (pure Python, ~95% of its time). It is handed the same tree
built by defusedxml instead: 5x faster, and no DTD ever accepted (`_install_fast_parser`).
"""

from __future__ import annotations

import html
import io
import itertools
import re
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import IO, Any
from xml.etree.ElementTree import Element

import mammoth
from defusedxml import ElementTree as SafeElementTree
from mammoth.docx import office_xml, xmlparser

from ..documents import ConvertedDocument, DocumentOptions, DocumentTooLargeError
from ._archive import SafeArchive, main_part, ooxml_metadata_count, relationships
from ._base import Report, Source, corrupt, too_large
from ._html import html_to_markdown
from ._markdown import bullet_list, inline, join_blocks, section

# Limites comptées dans le XML avant mammoth (document, notes de bas de page et de fin, commentaires) : mammoth, puis
# l'arbre HTML et markdownify, coûtent environ 0,15 ms par paragraphe, 0,27 ms par cellule de tableau (qui tient au
# moins un paragraphe) et 20 µs par autre élément XML (mesuré sous Linux, un seul processus). Au pire 30 s pour
# 100 000 paragraphes en cellules, 25 s pour un million d'éléments : la moitié au plus de l'échéance d'un petit
# document (60 s), et l'arbre sous la mémoire d'un travailleur. Limits counted in the XML before mammoth (document,
# footnotes and endnotes, comments): about 0.15 ms per paragraph, 0.27 ms per table cell (which holds at least one
# paragraph) and 20 µs per other XML element (measured on Linux, one process). At worst 30 s for 100,000 paragraphs
# in cells, 25 s for one million elements: at most half a small document's deadline, the tree under a worker's memory.
MAX_PARAGRAPHS = 100_000
MAX_ELEMENTS = 1_000_000
# Parties que mammoth lit en plus du document / parts mammoth reads besides the document.
_MAMMOTH_PARTS = frozenset({"footnotes", "endnotes", "comments"})
# Paragraphe, quel que soit le préfixe d'espace de noms (w:pPr exclu) / paragraph, whatever the prefix (not w:pPr).
_PARAGRAPH_RE = re.compile(rb"<(?:[A-Za-z_][\w.-]{0,30}:)?p[\s>/]")

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
_P, _R, _T, _TAB, _BR, _CR = f"{_W}p", f"{_W}r", f"{_W}t", f"{_W}tab", f"{_W}br", f"{_W}cr"
_RUN_PROPERTIES, _VAL = f"{_W}rPr", f"{_W}val"
_VANISH = frozenset({f"{_W}vanish", f"{_W}specVanish"})
_FALSE = frozenset({"0", "false", "off"})
_SKIPPED = frozenset({f"{_W}del", f"{_W}moveFrom", f"{_W}instrText", _MC_FALLBACK})
_TEXT_BOX, _SIMPLE_FIELD, _COMMENT = f"{_W}txbxContent", f"{_W}fldSimple", f"{_W}comment"
_STYLE_MAP = "p[style-name='Title'] => h1:fresh\np[style-name='Subtitle'] => h2:fresh"
# Suppressions suivies, quel que soit le préfixe d'espace de noms / tracked deletions, whatever the prefix.
_DELETION_RE = re.compile(rb"<(?:[A-Za-z_][\w.-]{0,30}:)?(?:del|moveFrom)[\s>/]")
_TAG_RE = re.compile(r"<[^>]{0,4096}>")
_IMAGE = mammoth.images.img_element(lambda image: {})  # jamais d'octets d'image lus / image bytes never read


class _HiddenRuns:
    """Écarte les passages masqués (w:vanish) et les compte / drops hidden runs (w:vanish) and counts them."""

    __slots__ = ("count",)

    def __init__(self) -> None:
        self.count = 0

    def drops(self, element: Element) -> bool:
        if element.tag != _R:
            return False
        properties = element.find(_RUN_PROPERTIES)
        if properties is None or not any(flag.tag in _VANISH and flag.get(_VAL) not in _FALSE for flag in properties):
            return False
        self.count += 1
        return True


# État de la conversion en cours dans ce fil, lu par l'analyseur de mammoth : `_OUTSIDE` hors de nos
# conversions (mammoth garde alors son analyseur d'origine), sinon le compteur des passages masqués à
# écarter, ou None pour tout garder. State of the conversion running in this thread, read by mammoth's
# parser: `_OUTSIDE` outside our conversions (mammoth then keeps its own parser), else the hidden-run
# counter, or None to keep everything.
_OUTSIDE: Any = object()
_STATE: ContextVar[_HiddenRuns | None] = ContextVar("gdprguardian_docx_state", default=_OUTSIDE)
_MINIDOM_PARSE = xmlparser.parse_xml


@contextmanager
def fast_parsing(hidden: _HiddenRuns | None) -> Iterator[None]:
    """Active l'analyseur defusedxml pour mammoth dans ce fil / enables the defusedxml parser in this thread."""
    token = _STATE.set(hidden)
    try:
        yield
    finally:
        _STATE.reset(token)


def parse_for_mammoth(fileobj: IO[bytes], namespace_mapping: Iterable[tuple[str, str]] | None = None
                      ) -> xmlparser.XmlElement:
    """Équivalent de `mammoth.docx.xmlparser.parse_xml`, via defusedxml (DTD interdite).

    Drop-in for `mammoth.docx.xmlparser.parse_xml`, through defusedxml (DTD forbidden). Same nodes:
    elements named « préfixe:local » or « {uri}local », text nodes in document order, no comments.
    Hidden runs are left out of the tree when asked. Outside `fast_parsing`, mammoth's own parser runs:
    importing this module never changes how the host application's own mammoth calls behave.
    """
    hidden = _STATE.get()
    if hidden is _OUTSIDE:
        return _MINIDOM_PARSE(fileobj, namespace_mapping)
    prefixes = {uri: prefix for prefix, uri in namespace_mapping or ()}
    names: dict[str, str] = {}

    def name(tag: str) -> str:
        converted = names.get(tag)
        if converted is None:
            converted = tag
            if tag.startswith("{"):
                uri, local = tag[1:].split("}", 1)
                prefix = prefixes.get(uri)
                if prefix is not None:
                    converted = f"{prefix}:{local}"
            names[tag] = converted
        return converted

    def convert(element: Element) -> xmlparser.XmlElement:
        children: list[Any] = [xmlparser.XmlText(element.text)] if element.text else []
        for child in element:
            if hidden is None or not hidden.drops(child):
                children.append(convert(child))
            if child.tail:
                children.append(xmlparser.XmlText(child.tail))
        return xmlparser.XmlElement(name(element.tag), {name(key): value for key, value in element.attrib.items()},
                                    children)

    return convert(SafeElementTree.parse(fileobj, forbid_dtd=True).getroot())


def _install_fast_parser() -> None:
    """Aiguille l'analyseur de mammoth, si sa structure est celle attendue / routes mammoth's parser if as expected."""
    if getattr(office_xml, "parse_xml", None) is _MINIDOM_PARSE:
        office_xml.parse_xml = parse_for_mammoth


_install_fast_parser()


def _too_complex() -> DocumentTooLargeError:
    return too_large("éléments Word", "Word elements", MAX_ELEMENTS)


def check_size(archive: SafeArchive, main: str, document_xml: bytes) -> None:
    """Refuse, avant mammoth, un document de plus de `MAX_PARAGRAPHS` paragraphes ou `MAX_ELEMENTS` éléments XML.

    Refuses, before mammoth, a document over `MAX_PARAGRAPHS` paragraphs or `MAX_ELEMENTS` XML elements, counted in
    the parts mammoth reads (document, notes, comments), whatever the namespace prefix. Les deux au-delà : les
    paragraphes, plus parlants / both over: the paragraphs, more telling.
    """
    # Une partie à la fois en mémoire, en plus du document / one part at a time in memory, besides the document.
    others = (rel.target for rel in relationships(archive, main) if not rel.external and rel.type in _MAMMOTH_PARTS)
    limit = archive.limits.max_xml_size
    parts = itertools.chain((document_xml,), (archive.read(name, limit) or b"" for name in others))
    elements = paragraphs_seen = 0
    for xml in parts:
        elements += xml.count(b"<") - xml.count(b"</") - xml.count(b"<?") - xml.count(b"<!")
        for _ in _PARAGRAPH_RE.finditer(xml):
            paragraphs_seen += 1
            if paragraphs_seen > MAX_PARAGRAPHS:
                raise too_large("paragraphes Word", "Word paragraphs", MAX_PARAGRAPHS)
    if elements > MAX_ELEMENTS:
        raise _too_complex()


def convert(source: Source, options: DocumentOptions) -> ConvertedDocument:
    archive = source.archive
    if archive is None:  # pragma: no cover - toujours fourni par identify() / always set by identify()
        archive = SafeArchive(source.data)
    report = Report()
    hidden = None if options.include_hidden else _HiddenRuns()
    # Parties relues ici après mammoth (déjà comptées) : écartées sans compte / re-read parts: dropped, uncounted.
    uncounted = None if options.include_hidden else _HiddenRuns()
    main = main_part(archive, "word/document.xml")
    document_xml = archive.read(main, archive.limits.max_xml_size) or b""
    check_size(archive, main, document_xml)
    try:
        with fast_parsing(hidden):
            result = mammoth.convert_to_html(io.BytesIO(source.data), style_map=_STYLE_MAP, convert_image=_IMAGE,
                                             include_embedded_style_map=False, external_file_access=False)
    except Exception:  # mammoth lève des types variés / mammoth raises assorted types
        raise corrupt("docx") from None
    # Sortie de mammoth au-delà des balises HTML : la limite du Word est nommée / mammoth's output over the HTML tags.
    body = html_to_markdown(result.value, options, report, too_complex=_too_complex)

    report.drop("tracked_deletions", len(_DELETION_RE.findall(document_xml)))
    boxes = _missing_text(archive, main, document_xml, result.value, uncounted)

    stories: list[str] = []
    comments: list[str] = []
    for rel in relationships(archive, main):
        if rel.external:
            continue
        if rel.type in ("header", "footer"):
            root = archive.xml(rel.target)
            for text in paragraphs(root, hidden) if root is not None else ():
                if text not in stories:  # chaque en-tête une seule fois / each header once
                    stories.append(text)
        elif rel.type == "comments":
            # mammoth lit aussi comments.xml : ses passages masqués sont déjà comptés / already counted.
            root = archive.xml(rel.target)
            if root is not None:
                found = [inline(" ".join(paragraphs(comment, uncounted))) for comment in root.iter(_COMMENT)]
                if options.include_comments:
                    comments.extend(text for text in found if text)
                else:
                    report.drop("comments", len(found))
    if hidden is not None:
        report.drop("hidden_text", hidden.count)
    report.drop("metadata", ooxml_metadata_count(archive))
    markdown = join_blocks([body, section("Zones de texte", bullet_list(boxes)),
                            section("En-têtes et pieds de page", bullet_list(stories)),
                            section("Commentaires", bullet_list(comments))])
    return report.document(markdown, "docx")


def paragraphs(root: Element, hidden: _HiddenRuns | None = None) -> list[str]:
    """Texte de chaque paragraphe (zones de texte comprises), sans texte supprimé ni codes de champ.

    Text of each paragraph (text boxes included), without deleted text nor field codes; hidden runs are
    dropped (and counted) when `hidden` is given.
    """
    found: list[str] = []

    def walk(element: Element, buffer: list[str]) -> None:
        for child in element:
            tag = child.tag
            if tag == _T:
                buffer.append(child.text or "")
            elif hidden is not None and hidden.drops(child):
                continue
            elif tag == _P:
                inner: list[str] = []
                walk(child, inner)
                text = inline("".join(inner))
                if text:
                    found.append(text)
            elif tag == _TAB:
                buffer.append("\t")
            elif tag in (_BR, _CR):
                buffer.append(" ")
            elif tag not in _SKIPPED:
                walk(child, buffer)

    loose: list[str] = []  # passages hors paragraphe (w:fldSimple) / runs outside a paragraph (w:fldSimple)
    walk(root, loose)
    if text := inline("".join(loose)):
        found.append(text)
    return found


def _missing_text(archive: SafeArchive, main: str, document_xml: bytes, rendered_html: str,
                  hidden: _HiddenRuns | None) -> list[str]:
    """Zones de texte et champs simples que mammoth n'a pas rendus / text boxes and simple fields mammoth skipped.

    mammoth ne lit que la branche mc:Fallback et ignore w:fldSimple : on rattrape ce texte.
    mammoth only reads the mc:Fallback branch and ignores w:fldSimple: that text is recovered here.
    """
    if b"txbxContent" not in document_xml and b"fldSimple" not in document_xml:
        return []
    root: Any = archive.xml(main)
    if root is None:
        return []
    rendered = " ".join(html.unescape(_TAG_RE.sub(" ", rendered_html)).split())
    missing: dict[str, None] = {}  # ordonné, recherche en O(1) / ordered, O(1) lookup
    for container in (*root.iter(_TEXT_BOX), *root.iter(_SIMPLE_FIELD)):
        for text in paragraphs(container, hidden):
            if text not in missing and text not in rendered:
                missing[text] = None
    return list(missing)


__all__ = ["MAX_ELEMENTS", "MAX_PARAGRAPHS", "check_size", "convert", "paragraphs"]
