"""Vue NFC d'un texte décomposé (macOS, certains PDF) / NFC view of a decomposed text.

Les détecteurs travaillent sur la vue composée ; les zones sont ramenées au texte d'origine, diacritiques
combinants compris. Detectors run on the composed view; spans are mapped back, combining marks included.
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_left, bisect_right
from collections.abc import Callable, Sequence
from functools import wraps
from typing import Any, TypeVar

from .._text import fold
from ..types import Span

# Blocs Unicode des diacritiques combinants / Unicode combining-mark blocks.
_MARK_BLOCKS = ((0x0300, 0x036F), (0x1AB0, 0x1AFF), (0x1DC0, 0x1DFF), (0x20D0, 0x20FF), (0xFE20, 0xFE2F))
_MARKS = "".join(f"\\u{low:04x}-\\u{high:04x}" for low, high in _MARK_BLOCKS)
# Caractère de base suivi de ses diacritiques (borné) / base character and its combining marks (bounded).
_CLUSTER_RE = re.compile(f"[^{_MARKS}][{_MARKS}]{{1,16}}")
# Diacritiques des langues latines et du vietnamien, testés par `ctx.has` (mis en cache par le contexte, quasi
# gratuit : le texte replié n'a en général aucun caractère au-delà de U+00FF).
# Latin and Vietnamese combining marks, tested through the context's cached `has`.
_COMMON_MARKS = tuple(map(chr, (0x300, 0x301, 0x302, 0x303, 0x304, 0x306, 0x307, 0x308, 0x309, 0x30A, 0x30B,
                                0x30C, 0x31B, 0x323, 0x326, 0x327, 0x328)))

D = TypeVar("D")


class ComposedView:
    """Contexte de détection sur le texte composé NFC / detection context over the NFC-composed text.

    Construite une fois par contexte et partagée par les détecteurs qui l'utilisent : pays, langue et réglages
    sont lus en direct sur le contexte (le mode auto les change entre ses deux passes). Built once per context
    and shared by the detectors using it; countries, language and settings are read live from the context.
    """

    __slots__ = ("_ctx", "_sources", "folded", "seg_ends", "seg_starts", "text")

    def __init__(self, ctx: Any) -> None:
        source: str = ctx.text
        parts: list[str] = []
        sources: list[int] = []  # position d'origine de chaque caractère composé / source index of each char
        last = 0
        for m in _CLUSTER_RE.finditer(source):
            start, end = m.span()
            parts.append(source[last:start])
            sources.extend(range(last, start))
            composed = unicodedata.normalize("NFC", m.group())
            parts.append(composed)
            sources.extend(range(start, start + len(composed)))
            last = end
        parts.append(source[last:])
        sources.extend(range(last, len(source)))
        sources.append(len(source))
        self._ctx = ctx
        self._sources = sources
        self.text = "".join(parts)
        self.folded = fold(self.text)
        self.seg_starts = self._forward(ctx.seg_starts)
        self.seg_ends = self._forward(ctx.seg_ends)

    @property
    def countries(self) -> tuple[str, ...]:
        return self._ctx.countries

    @property
    def language(self) -> str:
        return self._ctx.language

    @property
    def settings(self) -> Any:
        return self._ctx.settings

    @property
    def strict(self) -> bool:
        return self._ctx.strict

    @property
    def forced(self) -> Any:
        return self._ctx.forced

    def _forward(self, positions: Sequence[int] | None) -> list[int] | None:
        # Les bornes de segment tombent entre deux grappes / segment bounds fall between clusters.
        return None if positions is None else [bisect_left(self._sources, p) for p in positions]

    def has(self, feature: str | tuple[str, ...]) -> bool:
        if isinstance(feature, tuple):
            return any(self.has(f) for f in feature)
        return bool(self._ctx.has("digit")) if feature == "digit" else feature in self.folded

    def near(self, groups: Sequence[str], start: int, end: int, before: int, after: int) -> bool:
        return bool(self._ctx.near(groups, self._sources[start], self._sources[end], before, after))

    def any_context(self, groups: Sequence[str]) -> bool:
        return bool(self._ctx.any_context(groups))

    def segment(self, pos: int) -> tuple[int, int, int]:
        if self.seg_starts is None or self.seg_ends is None:
            return -1, 0, len(self.text)
        index = bisect_right(self.seg_starts, pos) - 1
        return index, self.seg_starts[index], self.seg_ends[index]

    def to_source(self, span: Span) -> Span:
        """Ramène une zone au texte d'origine ; formes propagées sous les deux écritures / maps a span back.

        La fin pointe sur le caractère suivant d'origine : les diacritiques du dernier caractère sont inclus.
        The end maps to the next source character, so trailing combining marks stay inside the span.
        """
        span.start, span.end = self._sources[span.start], self._sources[span.end]
        if span.forms:
            span.forms = tuple(dict.fromkeys((*span.forms, *(unicodedata.normalize("NFD", f) for f in span.forms))))
        return span


def decomposed(ctx: Any) -> bool:
    """Le texte contient-il des diacritiques combinants ? / does the text hold combining marks?"""
    return not ctx.text.isascii() and bool(ctx.has(_COMMON_MARKS))


def _view_of(ctx: Any) -> ComposedView:
    """Vue NFC du contexte, construite à la première demande et gardée par lui seul (jamais d'un document à
    l'autre). The context's NFC view, built on first request and kept by the context only (never across documents).
    """
    try:
        view = ctx._composed
    except AttributeError:  # contexte sans emplacement prévu (tests) / context without the slot (tests)
        return ComposedView(ctx)
    if view is None:
        view = ctx._composed = ComposedView(ctx)
    return view


def composed_view(detect: Callable[[D, Any], list[Span]]) -> Callable[[D, Any], list[Span]]:
    """Décorateur de `detect` : texte décomposé -> vue NFC, zones ramenées / runs `detect` on an NFC view."""

    @wraps(detect)
    def wrapper(self: D, ctx: Any) -> list[Span]:
        if not decomposed(ctx):
            return detect(self, ctx)
        view = _view_of(ctx)
        return [view.to_source(span) for span in detect(self, view)]

    return wrapper


__all__ = ["ComposedView", "composed_view", "decomposed"]
