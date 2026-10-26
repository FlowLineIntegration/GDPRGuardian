"""HTML -> Markdown sûr (BeautifulSoup + markdownify) / safe HTML -> Markdown (BeautifulSoup + markdownify).

Scripts, styles, cadres, objets, métadonnées et commentaires sont supprimés avec leur contenu (markdownify
seul garde le texte des scripts), les images deviennent [IMAGE: alt], les liens gardent leur texte sans
leur cible. Rien n'est jamais téléchargé. Sert aussi aux sorties de mammoth et aux courriels HTML.
Scripts, styles, frames, objects, metadata and comments are removed with their content (markdownify alone
keeps script text), images become [IMAGE: alt], links keep their text without their target. Nothing is
ever fetched. Also used for mammoth output and HTML e-mails.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from bs4 import BeautifulSoup, CData, Comment, Declaration, Doctype, NavigableString, ProcessingInstruction, Tag
from markdownify import MarkdownConverter

from ..documents import ConvertedDocument, DocumentOptions, DocumentTooLargeError
from ._base import Report, Source, too_large
from ._encoding import decode_text
from ._markdown import image

# Balises au plus, ouvrantes et fermantes (« <x », « </x », « <! », « <? » ; un « < » isolé du texte ne compte pas),
# comptées avant l'analyse : l'arbre de BeautifulSoup pèse environ 600 octets et 27 µs par balise (mesuré sous
# Linux : 1,19 million en 32 s et 720 Mio). Un million garde l'arbre vers 600 Mio, sous la mémoire d'un travailleur
# du service (1 280 Mio), moteur compris ; au-delà, refus avant d'allouer. Tags at most, opening and closing (a lone
# "<" in the text does not count), counted before parsing: the tree weighs about 600 bytes and 27 µs per tag. One
# million keeps the tree near 600 MiB, under a service worker's memory, engine included.
MAX_TAGS = 1_000_000
# Niveaux d'imbrication au plus, vérifiés après l'analyse (parcours itératif) : markdownify descend récursivement,
# deux appels par niveau, sous la limite de récursion de Python (1 000). Nesting levels at most, checked after parsing
# (iterative walk): markdownify recurses, two calls per level, under Python's recursion limit (1,000).
MAX_DEPTH = 256
_TAG_START_RE = re.compile(r"<[A-Za-z/!?]")

# Balise -> clé du rapport (None : retirée sans compte) / tag -> report key (None: removed, not counted).
_REMOVED: dict[str, str | None] = {
    "script": "scripts", "noscript": "scripts", "template": "scripts", "style": None, "link": None, "base": None,
    "iframe": "embedded_objects", "frame": "embedded_objects", "frameset": "embedded_objects",
    "object": "embedded_objects", "embed": "embedded_objects", "applet": "embedded_objects",
    "video": "embedded_objects", "audio": "embedded_objects", "canvas": None, "svg": "images", "map": None,
    "input": None, "button": None, "select": None, "datalist": None, "dialog": None,
}
_HIDDEN_STYLE_RE = re.compile(r"display\s{0,8}:\s{0,8}none|visibility\s{0,8}:\s{0,8}hidden", re.I)
_CHARSET_RE = re.compile(rb"""<meta[^>]{0,512}?charset\s{0,8}=\s{0,8}["']?([A-Za-z0-9_.:-]{1,40})"""
                         rb"""|<\?xml[^>]{0,256}?encoding\s{0,8}=\s{0,8}["']([A-Za-z0-9_.:-]{1,40})""", re.I)
_PIPE_RE = re.compile(r"(?<!\\)\|")
_BACKREF_PREFIXES = ("#footnote-ref", "#endnote-ref", "#comment-ref")
_NON_TEXT = (Comment, CData, ProcessingInstruction, Declaration, Doctype)

try:
    import lxml  # noqa: F401  # analyseur C, 5 à 10 fois plus rapide / C parser, 5-10x faster

    _PARSER = "lxml"
except ImportError:  # pragma: no cover
    _PARSER = "html.parser"


class _Converter(MarkdownConverter):
    """Cellules GFM sur une ligne avec « | » échappé / single-line GFM cells with escaped pipes."""

    def convert_td(self, el: Any, text: str, parent_tags: Any) -> str:
        return super().convert_td(el, _PIPE_RE.sub(r"\\|", text), parent_tags)

    def convert_th(self, el: Any, text: str, parent_tags: Any) -> str:
        return super().convert_th(el, _PIPE_RE.sub(r"\\|", text), parent_tags)


# Aucun échappement : « jean_dupont@x.fr » ou « 06-12-34 » doivent rester détectables.
# No escaping: "jean_dupont@x.fr" or "06-12-34" must stay detectable.
_MARKDOWN = _Converter(heading_style="atx", bullets="-", escape_asterisks=False, escape_underscores=False,
                       escape_misc=False, table_infer_header=True, strip_document="strip", wrap=False)


def decode_html(data: bytes, fallback: str | None = None) -> str:
    """Jeu déclaré par <meta> ou <?xml?>, sinon `fallback`, sinon détection / declared charset, else fallback."""
    match = _CHARSET_RE.search(data, 0, 4096)
    declared = (match.group(1) or match.group(2)).decode("ascii") if match else fallback
    return decode_text(data, declared)


def _is_hidden(tag: Tag) -> bool:
    if tag.has_attr("hidden"):
        return True
    style = tag.get("style")
    return isinstance(style, str) and _HIDDEN_STYLE_RE.search(style) is not None


def _placeholder(tag: Tag) -> str:
    alt = tag.get("alt") or tag.get("title") or ""
    return image(alt if isinstance(alt, str) else " ".join(alt))


def _tag_count_over(markup: str, limit: int) -> bool:
    """Plus de `limit` balises ? Compte exact seulement au-delà du compte rapide des « < » / exact count only when
    the quick count of "<" goes beyond."""
    if markup.count("<") <= limit:
        return False
    return any(count > limit for count, _ in enumerate(_TAG_START_RE.finditer(markup), 1))


def _deeper_than(soup: BeautifulSoup, limit: int) -> bool:
    """Imbrication des éléments au-delà de `limit` niveaux (parcours itératif, linéaire) / nesting beyond `limit`."""
    stack: list[tuple[Tag, int]] = [(soup, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > limit:
            return True
        stack.extend((child, depth + 1) for child in node.contents if isinstance(child, Tag))
    return False


def html_to_markdown(markup: str, options: DocumentOptions, report: Report,
                     too_complex: Callable[[], DocumentTooLargeError] | None = None) -> str:
    """Convertit du HTML en Markdown et compte ce qui a été écarté / converts and counts what was dropped.

    Plus de `MAX_TAGS` balises : refusé avant l'analyse ; plus de `MAX_DEPTH` niveaux d'imbrication : refusé avant
    la conversion (« trop volumineux », limite nommée). `too_complex` : refus à donner au lieu de celui des balises
    (le DOCX nomme sa propre limite). More than `MAX_TAGS` tags: refused before parsing; more than `MAX_DEPTH` nesting
    levels: refused before conversion ("too large", limit named). `too_complex`: refusal given instead of the tags'
    one (DOCX names its own limit).
    """
    if _tag_count_over(markup, MAX_TAGS):
        raise too_complex() if too_complex is not None else too_large("balises HTML", "HTML tags", MAX_TAGS)
    soup = BeautifulSoup(markup, _PARSER)
    if _deeper_than(soup, MAX_DEPTH):
        raise too_large("niveaux d'imbrication HTML", "HTML nesting levels", MAX_DEPTH)
    # Éléments retirés avec leurs descendants. Pas `Tag.decomposed` : faute d'attribut, BeautifulSoup y cherche une
    # balise « _decomposed » dans tout le sous-arbre (quadratique sur un HTML imbriqué). Elements removed with their
    # descendants. Not `Tag.decomposed`: lacking the attribute, BeautifulSoup searches the whole subtree for a
    # "_decomposed" tag (quadratic on nested HTML).
    gone: set[int] = set()

    def remove(tag: Tag) -> None:
        gone.update(id(node) for node in tag.descendants if isinstance(node, Tag))
        tag.decompose()

    for tag in soup.find_all(True):
        if id(tag) in gone:
            continue
        name = tag.name
        if name in _REMOVED:
            key = _REMOVED[name]
            if key is not None:
                report.drop(key)
            remove(tag)
        elif name in ("title", "meta"):
            if tag.get("content") or (name == "title" and tag.get_text(strip=True)):
                report.drop("metadata")
            remove(tag)
        elif name == "head":
            continue  # vidé ici, retiré après la boucle / emptied here, removed after the loop
        elif not options.include_hidden and _is_hidden(tag):
            report.drop("hidden_content")
            remove(tag)
        elif name == "img":
            report.drop("images")
            tag.replace_with(NavigableString(_placeholder(tag)))
        elif name in ("a", "area"):
            href = tag.get("href")
            href = href if isinstance(href, str) else ""
            if href.startswith(_BACKREF_PREFIXES):
                remove(tag)  # flèche de retour des notes / note back-reference arrow
                continue
            if href and not href.startswith("#"):
                report.drop("links")
            if name == "area":
                remove(tag)
            else:
                tag.unwrap()
    for head in soup.find_all("head"):
        head.decompose()
    # Commentaires, CDATA, instructions : jamais émis / comments, CDATA, processing instructions: never output.
    for node in soup.find_all(string=lambda s: isinstance(s, _NON_TEXT)):
        if isinstance(node, Comment):
            report.drop("comments")
        node.extract()
    return _MARKDOWN.convert_soup(soup)


def convert(source: Source, options: DocumentOptions) -> ConvertedDocument:
    report = Report()
    markdown = html_to_markdown(decode_html(source.data), options, report)
    return report.document(markdown, "html")


__all__ = ["convert", "decode_html", "html_to_markdown"]
