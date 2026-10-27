"""Noms, troisième tour (1.0.2, revue du 26/10) : sociétés à forme juridique lisibles en entier, nom coupé par un
saut de ligne, initiales pointées, prénom seul en minuscules après une préposition, « née Leclerc », « DUPONT, Jean ».

Names, third round: companies with a legal form readable as a whole, a name cut by a line break, dotted initials, a
lone lowercase given name after a preposition, maiden names, "DUPONT, Jean". Chaque cas tourne sur le noyau Rust (s'il
est installé) et sur la référence Python, en modes fort et essentiel (règles des personnes). Every case runs on the
Rust core (when installed) and on the Python reference, in modes fort and essentiel. Données fictives / fictitious data.
"""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer, _native

_PARAMS = [(native, mode) for native in (True, False) for mode in ("fort", "essentiel")]


@pytest.fixture(scope="module", params=_PARAMS, ids=[f"{'rust' if n else 'python'}-{m}" for n, m in _PARAMS])
def engine(request) -> Anonymizer:
    native, mode = request.param
    if native and not _native.available():
        pytest.skip("noyau Rust absent / no Rust core")
    anonymizer = Anonymizer(countries=("FR",), native=native, mode=mode)
    assert anonymizer.native == native
    return anonymizer


def _masked(engine: Anonymizer, text: str) -> str:
    return engine.anonymize(text).text


# --- Sociétés à forme juridique / companies with a legal form --------------------------------------------------


@pytest.mark.parametrize("text, readable, secrets", [
    ("Le stage a lieu chez Dupont Frères SAS à Lyon.", ["Dupont Frères SAS"], []),
    ("Facture émise par Martin & Fils SARL pour Jean Durand.", ["Martin & Fils SARL"], ["Durand"]),
    ("Le cabinet SELARL VIDAL & ASSOCIÉS représente Mme Claire Martin.", ["SELARL VIDAL & ASSOCIÉS"],
     ["Claire", "Martin"]),
])
def test_company_name_with_legal_form_stays_readable_as_a_whole(engine, text, readable, secrets):
    out = _masked(engine, text)
    for value in readable:
        assert value in out, out
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("text, secret", [
    ("Contact : M. Jean Dupont SARL Lumière.", "Dupont"),   # civilité : une personne / civility: a person
    ("J'ai vu Jean Dupont. Nouvelle SARL créée.", "Dupont"),  # phrase suivante / next sentence
])
def test_person_next_to_a_legal_form_elsewhere_stays_masked(engine, text, secret):
    assert secret not in _masked(engine, text)


# --- Nom coupé par un saut de ligne / name cut by a line break ---------------------------------------------------


def test_capitals_particle_and_surname_on_the_next_line_are_one_person(engine):
    out = _masked(engine, "Cordialement,\nYann LE\nGALL\nResponsable achats")
    assert "GALL" not in out and "LE\n" not in out, out
    assert "Responsable achats" in out


def test_signature_given_name_and_surname_on_two_lines_share_one_tag(engine):
    out = _masked(engine, "Bien à vous,\nJean\nDupont\n06 12 34 56 78")
    assert "Jean" not in out and "Dupont" not in out, out
    assert "[PERSONNE_2]" not in out, out


def test_list_of_surnames_one_per_line_keeps_one_tag_each(engine):
    out = _masked(engine, "Participants :\nMartin\nDurand\nfin")
    assert "Martin" not in out and "Durand" not in out, out
    assert "[PERSONNE_2]" in out, out


# --- Initiales / initials ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("text, secrets", [
    ("Réunion validée (M. T.) hier.", ["M. T."]),
    ("Présents : Paul Morel, Sophie Blanc, C.M.", ["C.M."]),
    ("Adresse de I.P. : voir dossier.", ["I.P."]),
    ("J.D. Contactez P. Lemoine au plus vite.", ["J.D.", "Lemoine"]),
    ("Visa : FXLD / CN", ["FXLD", "CN"]),
    ("Rapport rédigé par J.-B. de La Fontaine.", ["J.-B.", "Fontaine"]),
    ("Signataire : Lefebvre-Durand M.-H.", ["Lefebvre", "M.-H."]),
    ("Rédigée par M.-C.D.", ["M.-C.D."]),
    ("Présents : Quentin Moreau, Mathéo Moreau, AC", ["AC"]),
    ("Présents : Thibault Nguyen, Mathéo Haddad, M. L.", ["M. L."]),
])
def test_initials_are_masked(engine, text, secrets):
    out = _masked(engine, text)
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("text", [
    "N.B. Merci de répondre.",
    "Prix H.T. de 100 euros, voir R.C. et C.C.A.P.",
    "A. Objet du marché\nB. Durée",
    "Envoyé par S.A. le 3 mars ; voir P.J. et chez E.D.F.",
    "Le Cahier des Clauses Particulières (C.C.P.) est joint.",
    "Véhicules de 3,5 tonnes de P.M.A. uniquement.",
])
def test_dotted_acronyms_and_section_letters_stay_readable(engine, text):
    assert _masked(engine, text) == text


# --- Prénom en minuscules après une préposition / lowercase given name after a preposition ----------------------


@pytest.mark.parametrize("text, secret", [
    ("Patient pris en charge par mathéo hier soir.", "mathéo"),
    ("Rendez-vous avec chloé demain.", "chloé"),
])
def test_lowercase_given_name_after_a_preposition_is_masked(engine, text, secret):
    assert secret not in _masked(engine, text)


@pytest.mark.parametrize("text", [
    "Merci par avance, rendez-vous avec plaisir.",
    "Un bouquet pour rose et pour lui.",  # mot courant / common word
])
def test_common_word_after_a_preposition_stays_readable(engine, text):
    assert _masked(engine, text) == text


# --- Nom de naissance, « DUPONT, Jean » / maiden name, "DUPONT, Jean" --------------------------------------------


@pytest.mark.parametrize("text, secret", [
    ("Mme Martin née Leclerc est venue.", "Leclerc"),
    ("Mme Durand née LECLERC le 3 mars.", "LECLERC"),
])
def test_maiden_name_after_nee_is_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out and "née" in out, out


def test_capitals_surname_comma_given_name_is_one_person(engine):
    out = _masked(engine, 'Destinataire : "DUPONT, Jean"')
    assert out == 'Destinataire : "[PERSONNE_1]"', out
