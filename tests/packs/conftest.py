"""Fixtures des packs pays / country-pack fixtures.

Ici, `anonymizer` est en mode « auto » : ces tests vérifient que les preuves de pays (indicatif, IBAN,
mots-clés) activent le bon pack. Le défaut de la bibliothèque reste `countries=("FR",)`.
Here `anonymizer` runs in "auto" mode: these tests check that country evidence activates the right
pack. The library default stays `countries=("FR",)`.
"""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer


@pytest.fixture(scope="session")
def anonymizer() -> Anonymizer:
    return Anonymizer(countries="auto")
