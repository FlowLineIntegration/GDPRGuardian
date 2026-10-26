"""Détecteurs propres à la France / France-specific detectors."""

from __future__ import annotations

import re
from collections.abc import Iterator
from functools import cache, cached_property
from typing import Any, ClassVar

from .. import _native
from ..types import PRIORITY_CONTEXT, Span
from ..validators.intl import calendar_date


class NirBirthDateDetector:
    """Date dont l'année et le mois sont ceux d'un NIR validé du document : c'est une date de naissance.

    A date whose year and month match a validated NIR of the same document is a birth date: the NIR encodes
    both (characters 2 to 5), so a chance match is rare (about 1 in 1,200 per date and NIR). Les NIR viennent
    des zones déjà trouvées (`ctx.found`), sans nouvelle recherche / NIRs come from spans already found.
    Jumeau Rust aux résultats identiques si le noyau est installé / identical Rust twin when the core is installed.
    """

    id = "FR_NIR_BIRTH_DATE"
    _nir_source = "FR_NIR"
    _numeric = re.compile(
        r"(?<![0-9])(?:0?[1-9]|[12][0-9]|3[01])([/.\-])(0?[1-9]|1[0-2])\1(?:19|20)([0-9]{2})(?![0-9])"
    )
    # Sur le texte replié (minuscules, sans accents), de même longueur / on the folded text, same length.
    _words = re.compile(
        r"(?<![0-9])(?:1er|0?[1-9]|[12][0-9]|3[01])\s{1,3}(janvier|fevrier|mars|avril|mai|juin|juillet|aout"
        r"|septembre|octobre|novembre|decembre)\s{1,3}(?:18|19|20)([0-9]{2})(?![0-9])"
    )
    _months: ClassVar[dict[str, str]] = {name: f"{i:02d}" for i, name in enumerate(
        ("janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre",
         "novembre", "decembre"), start=1)}

    def __init__(self, pack: Any) -> None:
        self.pack = pack

    @cached_property
    def _native(self) -> Any:
        """Jumeau Rust, construit au premier usage natif / Rust twin, built on first native use."""
        return _native_twin()

    def detect(self, ctx: Any) -> list[Span]:
        births = {(s.value[1:3], s.value[3:5]) for s in ctx.found if s.source == self._nir_source and s.value}
        if not births:
            return []
        text = ctx.text
        if ctx.settings.native and self._native is not None:
            numeric, words = self._native.detect(text, ctx.folded, births)
            return [*(self._span(start, end, value) for start, end, value in numeric),
                    *(self._span(start, end, text[start:end]) for start, end in words)]
        return list(self._dates(text, ctx.folded, births))

    def _dates(self, text: str, folded: str, births: set[tuple[str, str]]) -> Iterator[Span]:
        for m in self._numeric.finditer(text):
            value = calendar_date(m.group())
            if value is not None and (m.group(3), m.group(2).zfill(2)) in births:
                yield self._span(m.start(), m.end(), value)
        for m in self._words.finditer(folded):
            if (m.group(2), self._months[m.group(1)]) in births:
                yield self._span(m.start(), m.end(), text[m.start():m.end()])

    def _span(self, start: int, end: int, value: str) -> Span:
        return Span(start, end, "BIRTH_DATE", "BIRTH_DATE", self.id, 0.9, PRIORITY_CONTEXT, value)

    def native_plan(self) -> dict[str, Any] | None:
        """Moteur fusionné : NIR du passage lus en Rust / fused engine: the pass's NIRs read in Rust."""
        if self._native is None:
            return None
        return {"kind": "birth_dates", "twin": self._native, "prototype": self._span(0, 0, ""),
                "nir_source": self._nir_source}


@cache
def _native_twin() -> Any:
    core = _native.core()
    months = list(NirBirthDateDetector._months.items())  # ordre du motif `_words` / `_words` pattern order
    return None if core is None else core.BirthDateDetector(_native.unicode_table(), months)
