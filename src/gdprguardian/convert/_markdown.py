"""Aides Markdown communes / shared Markdown helpers.

Nettoyage du texte extrait (contrôles, ligatures, NFC), tableaux GFM et mise en forme finale.
Cleaning of extracted text (controls, ligatures, NFC), GFM tables and final layout.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence

# Séparateurs de ligne ou de page : un saut de ligne, sinon « Jean\fDupont » deviendrait « JeanDupont ».
# Line and page separators: a newline, else "Jean\fDupont" would become "JeanDupont" and escape detection.
_BREAKS_RE = re.compile("[\x0b\x0c\x1c-\x1e\x85\u2028\u2029]")
# Autres contrôles C0/C1 (sauf tabulation et saut de ligne), demi-codets isolés, non-caractères.
# Other C0/C1 controls (except tab and newline), lone surrogates, noncharacters.
_JUNK_RE = re.compile("[\x00-\x08\x0e-\x1b\x1f\x7f-\x84\x86-\x9f\ud800-\udfff\ufffe\uffff]")
_LIGATURES = {0xFB00: "ff", 0xFB01: "fi", 0xFB02: "fl", 0xFB03: "ffi", 0xFB04: "ffl", 0xFB05: "st", 0xFB06: "st"}
_LIGATURE_RE = re.compile("[\ufb00-\ufb06]")
# Préfiltre : un seul balayage quand le texte est déjà propre / prefilter: a single scan for clean text.
_SPECIAL_RE = re.compile("[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029\ud800-\udfff\ufb00-\ufb06"
                         "\ufffe\uffff]")
_PIPE_RE = re.compile(r"(?<!\\)\|")
_DIGIT_RE = re.compile(r"\d")
MAX_ALT = 300  # texte de remplacement d'image, en caractères / image alternative text, in characters
# Ouverture de balise HTML (« <img », « </script ») ; ni « <jean@x.fr> » ni « <!-- page 2 --> ».
# HTML tag opener ("<img", "</script"); neither "<jean@x.fr>" nor "<!-- page 2 -->".
_TAG_OPEN_RE = re.compile(r"<(?=/?[A-Za-z][A-Za-z0-9-]{0,30}[\s/>])")


def clean_text(text: str) -> str:
    """Texte brut sûr : fins de ligne LF, sans contrôles, ligatures dépliées, NFC.

    Safe raw text: LF line ends, no controls, ligatures expanded, NFC.
    """
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if _SPECIAL_RE.search(text) is not None:
        text = _JUNK_RE.sub("", _BREAKS_RE.sub("\n", text))
        if _LIGATURE_RE.search(text) is not None:
            text = text.translate(_LIGATURES)
    if not unicodedata.is_normalized("NFC", text):
        text = unicodedata.normalize("NFC", text)
    return text


def finalize(text: str) -> str:
    """Nettoie, neutralise le HTML brut, retire les espaces de fin de ligne, réduit les lignes vides.

    Cleans, neutralises raw HTML, strips trailing spaces and collapses runs of blank lines. A tag found in
    the document text (« <img src=…> ») becomes « &lt;img src=…> »: shown as text, never rendered.
    """
    text = clean_text(text)
    if "<" in text:
        text = _TAG_OPEN_RE.sub("&lt;", text)
    lines: list[str] = []
    blank = True  # supprime aussi les lignes vides de tête / also drops leading blank lines
    for line in text.split("\n"):
        line = line.rstrip()
        if line:
            lines.append(line)
            blank = False
        elif not blank:
            lines.append("")
            blank = True
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def inline(text: str) -> str:
    """Une seule ligne, espaces réduits / single line, collapsed whitespace."""
    return " ".join(text.split())


def clip(text: str, limit: int) -> str:
    """Une ligne d'au plus `limit` caractères, coupée entre deux mots, jamais dans un identifiant.

    Single line of at most `limit` characters, cut between words. Trailing digit groups are dropped
    too: a cut inside a spaced identifier (« 1 85 05 78 006… ») would leave a partial number that no
    checksum can recognise, hence that would never be masked.
    """
    text = inline(text)
    if len(text) <= limit:
        return text
    cut = text.rfind(" ", 0, limit + 1)
    head = text[:cut] if cut > 0 else text[:limit]
    for _ in range(16):  # groupes de chiffres en fin de coupe / digit groups at the cut
        before, _space, last = head.rpartition(" ")
        if not before or _DIGIT_RE.search(last) is None:
            break
        head = before
    return f"{head} […]"


def image(alt: str) -> str:
    """Image remplacée par son texte de remplacement / image replaced by its alternative text."""
    alt = clip(alt, MAX_ALT)
    return f"[IMAGE: {alt}]" if alt else "[IMAGE]"


def escape_cell(text: str) -> str:
    """Cellule GFM : une ligne, barres verticales échappées / GFM cell: one line, escaped pipes."""
    return _PIPE_RE.sub(r"\\|", inline(text))


def gfm_table(rows: Sequence[Sequence[str]]) -> str:
    """Tableau GFM ; la première ligne sert d'en-tête / GFM table; the first row is the header."""
    cleaned = [[escape_cell(cell) for cell in row] for row in rows]
    cleaned = [row for row in cleaned if any(row)]
    if not cleaned:
        return ""
    width = max(len(row) for row in cleaned)
    padded = [row + [""] * (width - len(row)) for row in cleaned]
    out = ["| " + " | ".join(padded[0]) + " |", "|" + " --- |" * width]
    out.extend("| " + " | ".join(row) + " |" for row in padded[1:])
    return "\n".join(out)


def heading(level: int, text: str) -> str:
    return "#" * min(max(level, 1), 6) + " " + inline(text)


def bullet_list(items: Iterable[str]) -> str:
    return "\n".join(f"- {inline(item)}" for item in items if item and not item.isspace())


def section(title: str, body: str, level: int = 2) -> str:
    """Section titrée, vide si le corps est vide / titled section, empty when the body is empty."""
    return f"{heading(level, title)}\n\n{body}" if body.strip() else ""


def join_blocks(blocks: Iterable[str]) -> str:
    return "\n\n".join(block for block in blocks if block and block.strip())


_ATTACHMENT_KIND_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+/-]{0,79}")


def attachment(index: int, kind: str | None) -> str:
    """« Pièce jointe 2 (application/pdf) » : numéro et type (MIME ou extension), jamais le nom de fichier, qui porte
    souvent celui d'une personne (« CV_Jean_Dupont.pdf »). Number and type (MIME or extension), never the file
    name, which often carries a person's name.
    """
    shown = kind if kind and _ATTACHMENT_KIND_RE.fullmatch(kind) else "type inconnu"
    return f"Pièce jointe {index} ({shown})"


__all__ = ["MAX_ALT", "attachment", "bullet_list", "clean_text", "clip", "escape_cell", "finalize", "gfm_table",
           "heading", "image", "inline", "join_blocks", "section"]
