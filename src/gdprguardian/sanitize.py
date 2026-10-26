"""Nettoyage de la sortie contre l'injection de prompt / output hygiene against prompt injection."""

from __future__ import annotations

import re

# Invisibles, contrôles bidi et caractères « tag » (ZWJ des émojis conservé) / emoji ZWJ kept.
_INVISIBLE_RE = re.compile("[­᠎​‌‎‏‪-‮⁠-⁤⁦-⁩"
                           "﻿\U000e0000-\U000e007f]")
# Image Markdown distante = canal d'exfiltration / remote Markdown image = exfiltration channel.
_REMOTE_IMAGE_RE = re.compile(r"!\[([^\]\n]{0,200})\]\(\s*(?:https?:)?//[^)\n]{1,2000}\)")
_HTML_IMG_RE = re.compile(r"<img\b[^>]{0,2000}>", re.IGNORECASE)
_HTML_COMMENT_RE = re.compile(r"<!--(?!\s*page\b)[\s\S]{0,20000}?-->")


def sanitize_output(text: str) -> str:
    text = _INVISIBLE_RE.sub("", text)
    text = _REMOTE_IMAGE_RE.sub(lambda m: f"[image: {m.group(1)}]" if m.group(1) else "[image]", text)
    text = _HTML_IMG_RE.sub("[image]", text)
    return _HTML_COMMENT_RE.sub("", text)
