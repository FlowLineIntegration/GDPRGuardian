"""Version 1.0.1 : formats du quotidien, adresses, retours des tests terrain du 26 octobre 2026.

Release 1.0.1: everyday formats, addresses, field-test findings of 26 October 2026. Chaque cas tourne sur le noyau
Rust (s'il est installé) et sur la référence Python, qui doivent rendre le même texte. Every case runs on the Rust core
(when installed) and on the Python reference, which must render the same text. Données fictives / fictitious data.
"""

from __future__ import annotations

import re

import pytest

from gdprguardian import Anonymizer, _native

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]


@pytest.fixture(scope="module", params=_ENGINES)
def engine(request) -> Anonymizer:
    anonymizer = Anonymizer(countries=("FR",), native=request.param)
    assert anonymizer.native == request.param
    return anonymizer


def _masked(engine: Anonymizer, text: str) -> str:
    return engine.anonymize(text).text


# --- Formats du quotidien (couche 0) / everyday formats (layer 0) ------------------------------------------------


@pytest.mark.parametrize("text, secrets", [
    ("Tél.\t06\t12\t34\t56\t78", ["06\t12\t34\t56\t78"]),
    ("NIR 1  85  05  78  006  084  91", ["1  85  05  78  006  084  91"]),
    ("Téléphone : 06 12 34\n56 78, NIR 1 85 05 78 006\r\n084 91",
     ["06 12 34\n56 78", "1 85 05 78 006\r\n084 91"]),
    ("Joignable au 06/12/34/56/78, IBAN FR76.3000.6000.0112.3456.7890.189.",
     ["06/12/34/56/78", "FR76.3000.6000.0112.3456.7890.189"]),
])
def test_identifier_groups_split_by_everyday_separators(engine, text, secrets):
    out = _masked(engine, text)
    for secret in secrets:
        assert secret not in out, out
    assert not re.search(r"[0-9]", re.sub(r"\[[A-Z_]+_[0-9]+\]", "", out)), out


def test_windows_line_endings_mask_like_unix_ones(engine):
    lines = ["Madame Claire Martin", "12 rue des Lilas", "75011 Paris", "Tél. : 06 12 34 56 78",
             "NIR : 1 85 05 78 006 084 91"]
    unix = _masked(engine, "\n".join(lines))
    windows = _masked(engine, "\r\n".join(lines))
    assert windows.replace("\r\n", "\n") == unix
    assert "Martin" not in windows and "06 12" not in windows


# --- Adresses et champs de formulaire / addresses and form fields --------------------------------------------------


def test_address_field_masks_the_whole_line(engine):
    text = ("Nom complet : Conseil départemental\n"
            "Adresse : Pôle des Solidarités, Direction des Affaires Administratives, 4 rue Paraire, CS 23109, "
            "12000 Rodez\nTél : (+33) -05-65-75-80-00\nAdresse internet : https://www.exemple.fr\n")
    out = _masked(engine, text)
    assert "Adresse : [ADRESSE_1]\n" in out, out
    assert "Tél : [TEL_1]\n" in out, out
    assert "https://www.exemple.fr" in out


@pytest.mark.parametrize("text", ["Adresse : 31650 SAINT ORENS DE GAMEVILLE\n", "Adresse : voir ci-dessous\n",
                                  "Adresse internet : https://www.exemple.fr/2024\n"])
def test_address_field_keeps_postcode_and_town_alone(engine, text):
    assert _masked(engine, text) == text


# Revue du 26/10 : la valeur s'arrête à une fin de phrase après la commune et à « ; » ; le reste de la ligne revient
# aux autres détecteurs ; une parenthèse ouverte dans la valeur s'y ferme. Review: the value stops at a sentence end
# after the town and at ";"; a parenthesis opened in the value closes in it.
@pytest.mark.parametrize("text, expected", [
    ("Adresse : 4 rue des Prés, 12000 Rodez. Le dossier n° 2024-15 concerne M. Paul Durand qui réside ailleurs.",
     "Adresse : [ADRESSE_1]. Le dossier n° [IDENTIFIANT_1] concerne M. [PERSONNE_1] qui réside ailleurs."),
    ("Adresse du site : 4 rue des Prés, 12000 Rodez. Ouvert du lundi au vendredi de 9 h à 17 h.",
     "Adresse du site : [ADRESSE_1]. Ouvert du lundi au vendredi de 9 h à 17 h."),
    ("Adresse : 3 rue des Lilas, 75011 Paris (depuis 2019)", "Adresse : [ADRESSE_1]"),
    ("Adresse : 27, rue des Essais – CS 61107, 97404 Saint-Denis Cedex (La Réunion). Accueil le matin.",
     "Adresse : [ADRESSE_1]. Accueil le matin."),
    ("Adresse : 3 rue des Lilas, 75011 Paris ; bureau 4", "Adresse : [ADRESSE_1] ; bureau 4"),
    ("Adresse : 3 rue des Lilas, 75011 Paris.", "Adresse : [ADRESSE_1]."),
    ("Adresse : 12 bd. Haussmann, 75009 Paris", "Adresse : [ADRESSE_1]"),
])
def test_address_field_value_stops_at_the_end_of_the_address(engine, text, expected):
    assert _masked(engine, text) == expected


# Revue du 26/10 : « Tél : » ne prend que les chiffres d'un seul numéro ; deux numéros sur la ligne, ou des chiffres
# de la ligne suivante, reviennent aux détecteurs ordinaires. Review: one phone's worth of digits only.
@pytest.mark.parametrize("text, expected", [
    ("Tél : 06 12 34 56 78 / 07 98 76 54 32", "Tél : [TEL_1] / [TEL_2]"),
    ("Tél : 01 23 45 67 89 - 06 12 34 56 78", "Tél : [TEL_1] - [TEL_2]"),
    ("Tél : +33 1 23 45 67 89 / +33 6 12 34 56 78", "Tél : [TEL_1] / [TEL_2]"),
    ("Tél : 0123456789 / 0612345678", "Tél : [TEL_1] / [TEL_2]"),
    ("Tél : 06 12 34 56 78\n07 98 76 54 32", "Tél : [TEL_1]\n[TEL_2]"),
    ("Tél : 01 23 45 67 89\n3 participants confirmés", "Tél : [TEL_1]\n3 participants confirmés"),
    ("Tél : (+33) -05-65-75-80-00", "Tél : [TEL_1]"),
    ("Tél : (+33) 1-01-23-45-60-22", "Tél : [TEL_1]"),
    # Forme libre « (+ » des avis, outre-mer mal formé compris : 8 à 15 chiffres / "(+" free form: 8 to 15 digits.
    ("Tél : (+33) 3-89-30-63", "Tél : [TEL_1]"),
    ("Fax : (+02) 6-22-62-52-14-13", "Fax : [TEL_1]"),
    ("Tél : (+59)6- 0-59-60-63-10-08", "Tél : [TEL_1]"),
])
def test_phone_field_takes_one_number(engine, text, expected):
    assert _masked(engine, text) == expected


@pytest.mark.parametrize("text", ["Tél : (+33) 1 23 45 67 89 / (+33) 6 12 34 56 78",
                                  "Tél : (+33) 1 23 45 67 89 - (+33) 6 12 34 56 78"])
def test_phone_field_two_international_numbers(engine, text):
    out = _masked(engine, text)
    assert "[TEL_2]" in out and not re.search(r"[0-9]", re.sub(r"\[[A-Z_]+_[0-9]+\]", "", out)), out


# Adresses électroniques déguisées (équipe rouge) / disguised e-mail addresses (red team).
@pytest.mark.parametrize("text, expected", [
    ("Écrire à jean.dupont&#64;exemple.fr demain.", "Écrire à [EMAIL_1] demain."),
    ("Mail : claire_martin%40mairie-exemple.fr, merci", "Mail : [EMAIL_1], merci"),
    ("Contact : jean.dupont@exemple [dot] fr ou c@mail.exemple(point)fr.", "Contact : [EMAIL_1] ou [EMAIL_2]."),
    ("Le prix baisse de 10%40 sur https://exemple.fr/a%40b", "Le prix baisse de 10%40 sur https://exemple.fr/a%40b"),
])
def test_disguised_email_addresses(engine, text, expected):
    assert _masked(engine, text) == expected


def test_event_date_right_before_the_birth_keyword(engine):
    out = _masked(engine, "Mme Claire Martin, hospitalisée le 14/09/2026, née le 12/03/1985.")
    assert "hospitalisée le 14/09/2026" in out and "12/03/1985" not in out, out


def test_code_article_numbers_are_not_addresses(engine):
    text = "Articles L. 1221-3, R. 111-2 du code du travail."
    assert _masked(engine, text) == text


# --- Identifiants après un libellé explicite / identifiers after an explicit label --------------------------------


def test_labelled_identifiers(engine):
    out = _masked(engine, "Dr Paul Auger, RPPS 10001234567 (matricule 004587), contrat n° 2024-778899.")
    for secret in ("10001234567", "004587", "778899", "Auger"):
        assert secret not in out, out
    assert "RPPS [RPPS_1]" in out


# --- Dates de naissance / birth dates -------------------------------------------------------------------------------


@pytest.mark.parametrize("text", [
    "Le contrat a été signé le 4 mars 2024.",
    "Le tribunal a ordonné le 20 juin 2024 une expertise.",
])
def test_event_dates_are_not_birth_dates(engine, text):
    assert _masked(engine, text) == text


def test_nearest_event_cancels_the_birth_context(engine):
    out = _masked(engine, "Patient né le 01/07/1990. Hospitalisé le 14/09/2026, désigné le 15/09/2026.")
    assert "01/07/1990" not in out
    assert "14/09/2026" in out and "15/09/2026" in out


# --- Personnes / persons --------------------------------------------------------------------------------------------


def test_part_of_a_hyphenated_surname_keeps_the_person(engine):
    out = _masked(engine, "Mme Solène Kervadec-Moulin est salariée. Mme Kervadec a été absente.")
    assert out == "Mme [PERSONNE_1] est salariée. Mme [PERSONNE_1] a été absente.", out


def test_rib_laid_out_field_by_field_and_grouped_phones(engine):
    text = ("Code banque : 14445\nCode guichet : 63965\nN° de compte : 83286587466\nClé RIB : 67\n"
            "Joignable au 0690 21 78 59 ou au 0298 55 21 76.")
    out = _masked(engine, text)
    assert not re.search(r"[0-9]", re.sub(r"\[[A-Z_]+_[0-9]+\]", "", out)), out


def test_rust_and_python_render_the_same_text():
    if not _native.available():
        pytest.skip("noyau Rust absent / no Rust core")
    native, python = Anonymizer(countries=("FR",)), Anonymizer(countries=("FR",), native=False)
    samples = [
        "Tél.\t06\t12\t34\t56\t78 ; NIR 1  85  05  78  006  084  91 ; IBAN FR76/3000/6000/0112/3456/7890/189",
        "Adresse : 2-4, boulevard des Essais -B.P.30322, 95027 Cergy-Pontoise Cedex\r\nTél : (+33) 1-01-23-45-60-22",
        "Patient né le 01/07/1990. Hospitalisé le 14/09/2026.\nDr Paul Auger, RPPS 10001234567",
        "Mme Solène Kervadec-Moulin, M. Didier Le Floch et Mme Yvette Le Floch. Mme Kervadec, M. Le Floch.",
        "Code banque : 14445\nCode guichet : 63965\nN° de compte : 83286587466\nClé RIB : 67\n0690 21 78 59",
        "Tél : 06 12 34 56 78 / 07 98 76 54 32\nTél : 01 23 45 67 89\n3 participants\nTél : 0123456789 / 0612345678",
        "Adresse : 4 rue des Prés, 12000 Rodez. Le dossier n° 2024-15 concerne M. Paul Durand.\n"
        "Adresse : 3 rue des Lilas, 75011 Paris (depuis 2019) ; bureau 4\nAdresse : 12 bd. Haussmann, 75009 Paris\n"
        "Adresse : 27, rue des Essais – CS 61107, 97404 Saint-Denis Cedex (La Réunion). Accueil le matin.",
        "Tél : (+02) 6-22-62-52-30-02\nFax : (+33) 3-89-30-63\nMail : a.b&#64;exemple.fr, c%40exemple.fr, "
        "d@exemple [dot] fr\nMme Claire Martin, hospitalisée le 14/09/2026, née le 12/03/1985.",
    ]
    for text in samples:
        assert native.anonymize(text).text == python.anonymize(text).text, text
