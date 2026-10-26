"""Outils partagés des tests d'heuristiques / shared helpers for heuristics tests."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from gdprguardian import Anonymizer
from gdprguardian._text import fold, normalize
from gdprguardian.engine import DetectionContext


@pytest.fixture(scope="session")
def fr() -> Anonymizer:
    return Anonymizer(countries="FR")


@pytest.fixture(scope="session")
def found(fr: Anonymizer) -> Callable[[str, str], list[str]]:
    """Textes des zones d'une entité, dans l'ordre / texts of an entity's spans, in order."""

    def run(text: str, entity: str = "PERSON") -> list[str]:
        return [text[s.start:s.end] for s in fr.analyze(text).spans if s.entity == entity]

    return run


@pytest.fixture(scope="session")
def context(fr: Anonymizer) -> Callable[[str], DetectionContext]:
    """Contexte de détection brut, comme le construit le moteur / raw detection context, as the engine builds it."""

    def build(text: str) -> DetectionContext:
        norm, _ = normalize(text)
        folded = fold(norm)
        return DetectionContext(norm, folded, fr._keywords.scan(folded), ("FR",), "fr", fr.settings)

    return build
