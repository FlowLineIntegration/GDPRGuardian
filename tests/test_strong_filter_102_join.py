"""Filtre fort 1.0.2, jonction du second tour : corrections trouvées en assemblant les voies.

Strong filter 1.0.2, second-round join: fixes found while putting the lanes together. Chaque cas tourne sur le noyau
Rust (s'il est installé) et sur la référence Python / every case runs on the Rust core (when installed) and on the
Python reference. Données fictives / fictitious data.
"""

from __future__ import annotations

import time

import pytest

from gdprguardian import Anonymizer, _native
from gdprguardian.detectors.intl import PersonalSiteDetector

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]


def _out(text: str, native: bool, **settings) -> str:
    return Anonymizer(countries=("FR",), native=native, **settings).anonymize(text).text


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("text, expected", [
    # La tête d'un code n'est jamais rattachée au nom (fuite « [PERSONNE_1]-204518 » en 1.0.1).
    # The head of a code is never part of the name (the 1.0.1 leak "[PERSONNE_1]-204518").
    ("client Jean Dupont CLT-204518.", "client [PERSONNE_1] [IDENTIFIANT_1]."),
    ("Le client Jean Dupont EMP_100101 a appelé.", "Le client [PERSONNE_1] [IDENTIFIANT_1] a appelé."),
    # Carte groupée par des points / a card grouped with dots.
    ("Numéro 4970.1012.3456.7899", "Numéro [CARTE_1]"),
])
def test_join_fixes(native, text, expected):
    assert _out(text, native) == expected


# Une règle attrape-tout coupée (codes, nombres longs) ne protège jamais l'identifiant validé qu'elle recouvre.
# A switched-off catch-all rule never shields the validated identifier it overlaps.
_VALIDATED = [
    ("Passeport : 12AB34567", "12AB34567"),
    ("IBAN FR7630006000011234567890189", "FR7630006000011234567890189"),
    ("Carte 4970101234567899", "4970101234567899"),
]


@pytest.mark.parametrize("native", _ENGINES)
@pytest.mark.parametrize("modes", [{"mode": "essentiel"}, {"disable": ["codes", "nombres_longs"]}])
@pytest.mark.parametrize("text, value", _VALIDATED)
def test_catch_all_rules_never_shield_a_validated_identifier(native, modes, text, value):
    assert value not in _out(text, native, **modes)


@pytest.mark.parametrize("native", _ENGINES)
def test_self_check_stays_linear_on_one_huge_value(native):
    start = time.perf_counter()
    _out("1" * 100_000, native)
    assert time.perf_counter() - start < 5


def test_personal_site_scan_matches_the_whole_text_scan():
    texts = ["Kevin Lambert\nvoir https://kevinlambert.fr.\nwww.service-public.fr", "a.fr.b.com\r\nx@y.fr",
             "Site : kevin-lambert.FR/page,\n(jdupont.blog)"]
    for text in texts:
        whole = [m.span() for m in PersonalSiteDetector._url.finditer(text)]
        assert [m.span() for m in PersonalSiteDetector(None)._urls(text)] == whole
