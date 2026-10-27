"""Filtre fort 1.0.2, troisième tour : dates de naissance sous toutes leurs formes courantes.

Strong filter 1.0.2, third round: birth dates in every common form. Après un indice de naissance (« né le », « DDN »,
« date de naissance », « naissance », « birthdate », « née Leclerc le ») : année sur deux chiffres (« 06/04/69 »,
« 3 mars 85 »), mois abrégés (« 12 jui. 1979 », « 1er janv. 1990 »), forme compacte « 19751021 », nom de naissance
entre « née » et la date. L'indice ne vaut que pour sa première date ; toutes les graphies d'une même date de naissance
partagent une balise. Modes fort et essentiel (et personnalisé, catégorie dates_naissance). Chaque cas tourne sur le
noyau Rust (s'il est installé) et sur la référence Python, qui doivent rendre le même texte. Every case runs on the
Rust core (when installed) and on the Python reference. Données fictives / fictitious data.
"""

from __future__ import annotations

import re

import pytest

from gdprguardian import Anonymizer, _native
from gdprguardian.engine import _date_seen
from gdprguardian.validators.intl import calendar_date

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]
_MODES = ["fort", "essentiel"]


@pytest.fixture(scope="module", params=[(n, m) for n in (True, False) for m in _MODES],
                ids=lambda p: f"{'rust' if p[0] else 'python'}-{p[1]}")
def engine(request) -> Anonymizer:
    native, mode = request.param
    if native and not _native.available():
        pytest.skip("noyau Rust absent / no Rust core")
    anonymizer = Anonymizer(countries=("FR",), native=native, mode=mode)
    assert anonymizer.native == native
    return anonymizer


def _masked(engine: Anonymizer, text: str) -> str:
    return engine.anonymize(text).text


def _birth_tags(out: str) -> set[str]:
    return set(re.findall(r"\[DATE_NAISSANCE_\d+\]", out))


# --- Formes nouvelles après un indice / new forms after a birth cue -------------------------------------------------


@pytest.mark.parametrize("text, secret", [
    ("Patient né le 06/04/69 à Lyon.", "06/04/69"),
    ("DDN 08/04/79, suivi depuis 2020.", "08/04/79"),
    ("Date de naissance : 03.05.79", "03.05.79"),
    ("Né le 3/5/38 à Brest.", "3/5/38"),
    ("Elle est née, naissance le 14.03.85 à Nice.", "14.03.85"),
    ("Jean Martin, né le 3 mars 85, habite Lyon.", "3 mars 85"),
    ("Sophie Durand, née le 12 jui. 1979 à Metz.", "12 jui. 1979"),
    ("Paul Petit, né le 1er janv. 1990 à Tours.", "1er janv. 1990"),
    ("né(e) le 4 févr. 1981", "4 févr. 1981"),
    ("Date de naissance : 19751021", "19751021"),
    ("DDN : 19751021", "19751021"),
    ("Marie Dupont née Leclerc le 21 janvier 1972 à Lille.", "21 janvier 1972"),
    ("Mme Dupont, née Leclerc le 21/01/1972.", "21/01/1972"),
    ("Mme Dupont, née Leclerc le 21 janv. 72.", "21 janv. 72"),
    ("birthdate: 1985-03-12", "1985-03-12"),
    ("Birthdate: 12/03/85", "12/03/85"),
    ("born 3 Mar 1985 in Leeds", "3 Mar 1985"),
    ("Born Sept. 3, 1985 in York.", "Sept. 3, 1985"),
    ("Né à Lyon le 06/04/1969, il a travaillé chez nous.", "06/04/1969"),
    ("Né à Lyon le 06/04/69, il a travaillé chez nous.", "06/04/69"),
    ("Paul, né à Saint-Étienne (42), le 3 mars 1985.", "3 mars 1985"),
    ("née à Paris le 12 jui. 1979", "12 jui. 1979"),
    ("née Durand-Petit, le 3 sept. 81", "3 sept. 81"),
    ("D.D.N. : 06/04/69", "06/04/69"),
    ("Date de naiss. : 06/04/69", "06/04/69"),
    ("date de naissance: 1975.10.21", "1975.10.21"),
])
def test_birth_date_new_forms_are_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out, out
    assert len(_birth_tags(out)) == 1, out


# --- Liaison à la première date / first-date binding -----------------------------------------------------------------


@pytest.mark.parametrize("text, kept", [
    ("Né le 12 juin 1934 à Nantes, entré le 5 janvier 2024.", "5 janvier 2024"),
    ("Né le 12 juin 1934 à Nantes.\nEntré le 5 janvier 2024 au service.", "5 janvier 2024"),
    ("DDN 08/04/79, consultation le 12/05/24.", "12/05/24"),
    ("Né le 3 mars 85 à Agen, entré le 05/01/2024.", "05/01/2024"),
    ("Né le 1er janv. 90 à Agen, arrivé le 12/05/24.", "12/05/24"),
    ("Date de naissance : 19751021, arrivée le 05/01/2024.", "05/01/2024"),
    ("Né à Lyon le 06/04/69, entré le 05/01/2024.", "05/01/2024"),
    ("née le 12/03/1985 et mariée le 03/06/2010", "03/06/2010"),
])
def test_birth_cue_binds_only_its_first_date(engine, text, kept):
    out = _masked(engine, text)
    assert kept in out, out
    assert len(_birth_tags(out)) == 1, out


# --- Une date, une balise / one date, one tag ------------------------------------------------------------------------


@pytest.mark.parametrize("text, forms", [
    ("Né le 06/04/69. Le 06/04/1969 il a vu le jour.", ["06/04/69", "06/04/1969"]),
    ("Né le 3 mars 85 ; rappel : 03/03/1985 et 1985-03-03.", ["3 mars 85", "03/03/1985", "1985-03-03"]),
    ("Né le 19751021, le 21/10/1975.", ["19751021", "21/10/1975"]),
    ("Née le 1er janv. 1990. Fiche : 01/01/1990.", ["1er janv. 1990", "01/01/1990"]),
    ("Né le 3 oct. 1985 ; fiche : 03/10/1985.", ["3 oct. 1985", "03/10/1985"]),
])
def test_every_written_form_shares_one_tag(engine, text, forms):
    out = _masked(engine, text)
    for form in forms:
        assert form not in out, out
    assert len(_birth_tags(out)) == 1, out


# --- Témoins : sans indice de naissance, la date reste lisible / controls ---------------------------------------------


@pytest.mark.parametrize("text, kept", [
    ("Réunion du 06/04/69 au siège.", "06/04/69"),
    ("Le 3 mars 85 la loi a changé.", "3 mars 85"),
    ("Le 12 jui. 1979, inauguration du pont.", "12 jui. 1979"),
    ("Version 1.2.33 publiée.", "1.2.33"),
    ("Une idée née de rien, signée le 12/03/2024.", "12/03/2024"),
    ("Né en 1969 à Lyon.", "1969"),
    ("Elle est née Leclerc. Le 21/01/2024, réunion.", "21/01/2024"),
])
def test_dates_without_a_birth_cue_stay_readable(engine, text, kept):
    out = _masked(engine, text)
    assert kept in out, out
    assert not _birth_tags(out), out


def test_two_digit_year_is_never_a_piece_of_a_longer_run(engine):
    out = _masked(engine, "Date de naissance : inconnue. Tél : 01.02.03.04.05")
    assert not _birth_tags(out), out
    assert "03.04" not in out, out


# --- Validateur et indice consommé (Python) / validator and spent cue ------------------------------------------------


@pytest.mark.parametrize("candidate, value", [
    ("06/04/69", "1969-04-06"),
    ("3/5/38", "1938-05-03"),
    ("14.03.85", "1985-03-14"),
    ("12-05-24", "2024-05-12"),
    ("01/01/26", "2026-01-01"),
    ("01/01/27", "1927-01-01"),
    ("19751021", "1975-10-21"),
    ("19751321", None),
    ("3 mars 85", "1985-03-03"),
    ("1er janv. 1990", "1990-01-01"),
    ("4 févr. 1981", "1981-02-04"),
    ("4 FÉV 81", "1981-02-04"),
    ("12 sept. 1979", "1979-09-12"),
    ("12 jui. 1979", "12 jui. 1979"),
    ("05 jui. 79", "5 jui. 1979"),
    ("12 jui 1979", None),
    ("31/02/85", None),
    ("12/03/1985", "1985-03-12"),
    ("1985-03-12", "1985-03-12"),
    ("12 mars 1985", "1985-03-12"),
])
def test_calendar_date_third_round(candidate, value):
    assert calendar_date(candidate) == value


@pytest.mark.parametrize("between, seen", [
    (" 3 mars 85 à Agen, entré le ", True),
    (" 1er janv. 90, ", True),
    (" 19751021, arrivée le ", True),
    (" 12/05/84 puis ", True),
    (" 1985 ", True),
    (" en mars, ", False),
    (" 3 pommes 85 ", False),
    (" 12345678 ", False),
])
def test_date_seen_third_round(between, seen):
    assert _date_seen(between, 0, len(between)) is seen
