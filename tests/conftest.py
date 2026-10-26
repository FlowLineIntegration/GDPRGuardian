"""Fixtures partagées / shared fixtures."""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer


@pytest.fixture(scope="session")
def anonymizer() -> Anonymizer:
    return Anonymizer()


@pytest.fixture(scope="session")
def anonymizer_fr() -> Anonymizer:
    return Anonymizer(countries=("FR",))
