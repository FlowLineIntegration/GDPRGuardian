"""Texte brut et Markdown : décodage seul, contenu conservé tel quel / plain text and Markdown: decoding only.

Le texte n'est pas échappé : « jean_dupont@exemple.fr » doit rester détectable.
Text is not escaped: "jean_dupont@exemple.fr" must stay detectable.
"""

from __future__ import annotations

from ..documents import ConvertedDocument, DocumentOptions
from ._base import Report, Source
from ._encoding import decode_text


def convert(source: Source, options: DocumentOptions) -> ConvertedDocument:
    return Report().document(decode_text(source.data), source.kind)


__all__ = ["convert"]
