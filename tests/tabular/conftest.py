"""Fixtures des tests tableur / spreadsheet test fixtures."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from gdprguardian import Anonymizer
from gdprguardian.documents import DocumentOptions, DocumentResult
from gdprguardian.tabular import anonymize_workbook


@pytest.fixture(scope="session")
def fr_anonymizer() -> Anonymizer:
    return Anonymizer(countries=("FR",))


@pytest.fixture
def run(fr_anonymizer: Anonymizer) -> Callable[..., DocumentResult]:
    """anonymize_workbook avec l'anonymiseur FR et des options / with the FR anonymizer and options."""

    def _run(data: bytes, filename: str = "classeur.xlsx", anonymizer: Anonymizer | None = None,
             **options: Any) -> DocumentResult:
        return anonymize_workbook(data, filename, anonymizer or fr_anonymizer, DocumentOptions(**options))

    return _run
