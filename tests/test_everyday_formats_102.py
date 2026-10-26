"""Formats du quotidien, deuxième passe : saut de ligne dans un identifiant (règle BREAK), lettres espacées d'un PDF,
groupes de chiffres regroupés librement, étage écrit avec son rang.

Everyday formats, second pass: line break inside an identifier (BREAK rule), letter spacing from a copied PDF,
freely regrouped digit groups, floor written with its rank. Chaque cas tourne sur le noyau Rust (s'il est installé)
et sur la référence Python, qui doivent rendre le même texte. Every case runs on the Rust core (when installed) and
on the Python reference, which must render the same text. Données fictives / fictitious data.
"""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer, _native, _text

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


# --- Règle BREAK : saut de ligne dans un identifiant / line break inside an identifier ----------------------------


@pytest.mark.parametrize("text, secrets", [
    ("Contact : david.ledoux72@cuis\nines-conseil.fr merci", ["ledoux72", "cuis", "ines-conseil"]),
    ("Contact : margot.ferrei\r\nra62@outlook.fr.", ["margot", "ferrei", "ra62"]),
    ("Écrire à franck_lefevre@gmai\nl.com avant lundi.", ["franck", "gmai", "l.com"]),
    ("IBAN : FR763000333162\n8644745376855\nBIC : BNPAFRPPXXX", ["FR763000333162", "8644745376855"]),
    ("passeport n° 47CY\n74524 ;", ["47CY", "74524"]),
])
def test_identifier_cut_by_a_line_break_is_masked_across_it(engine, text, secrets):
    out = _masked(engine, text)
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("text", [
    "Merci de contacter\ninfo@exemple.fr pour tout.",  # mot courant avant : rien n'est recollé / common word
    "Total 2024\nLe client",                            # lettres minuscules : deux lignes / two lines
    "Réf. AB12\nCD",                                    # pas de chiffre à droite / no digit on the right
])
def test_two_separate_lines_are_not_joined(text):
    norm, _, _ = _text.prepare(text, native=False)
    assert "\n" in norm, norm


@pytest.mark.parametrize("text, secrets", [
    # Revue du 26/10 : un numéro en fin de ligne n'est jamais collé au courriel de la ligne suivante.
    # Review of 26/10: a number ending a line is never glued onto the e-mail on the next line.
    ("Jean Dupont\n06 12 34 56 78\njean.dupont@exemple.fr", ["12 34", "78", "jean.dupont"]),
    ("Cordialement,\nJean Dupont\nTél. 01 23 45 67 89\nj.dupont@exemple.fr", ["23 45", "89", "j.dupont"]),
    ("Tél. 06.12.34.56.78\r\njean.dupont@exemple.fr", ["34.56", "78"]),
    ("CB 4970 1012 3456 7890\njean.dupont@exemple.fr", ["4970", "7890"]),
    ("Né le 12/03/1980\njean.dupont@exemple.fr", ["12/03", "1980"]),
])
def test_number_ending_a_line_stays_out_of_the_next_email(engine, text, secrets):
    out = _masked(engine, text)
    for secret in secrets:
        assert secret not in out, out


def test_break_rule_offsets_cover_the_break():
    text = "x jean.du\npont@exemple.fr y"
    norm, _, offsets = _text.prepare(text, native=False)
    assert "jean.dupont@exemple.fr" in norm
    assert offsets is not None and len(offsets) == len(norm) + 1


# --- Lettres espacées / letter spacing ------------------------------------------------------------------------------


def test_letter_spaced_values_are_masked(engine):
    text = ("M. J e a n   D u p o n t habite ici, tél 0 6   1 2   3 4   5 6   7 8, "
            "j e a n . d u p o n t @ x . f r")
    out = _masked(engine, text)
    assert "J e a n" not in out and "D u p o n t" not in out, out
    assert "0 6" not in out and "j e a n" not in out, out


@pytest.mark.parametrize("text, expected", [
    ("à J e a n", "à Jean"),           # minuscule puis majuscule : deux mots / lowercase then capital: two words
    ("Il y a 3 ou 4", "Il y a 3 ou 4"),  # trois caractères isolés : rien / three single characters: nothing
    ("a b", "a b"),                    # moins de quatre caractères isolés / fewer than four single characters
    # Revue du 26/10 : français ordinaire et numéros de voie intacts / ordinary French and house numbers intact.
    ("RAYNAUD Pascal, 4 à 6 Rue Pétillat", "RAYNAUD Pascal, 4 à 6 Rue Pétillat"),
    ("Demeurant (89330), 4 B Rue des Vignes", "Demeurant (89330), 4 B Rue des Vignes"),
    ("il y a l'article R2161-1 à 5", "il y a l'article R2161-1 à 5"),
    ("1 2 3 4 à 6 7 8 9", "1234 à 6789"),  # « chiffre à chiffre » jamais recollé / never collapsed
    ("Hi Z o é,", "Hi Zoé,"),              # mot capitalisé de trois lettres / capitalised three-letter word
    ("au 0 7 - 9 3 - 2 8", "au 07-93-28"),  # tirets dans la suite, non comptés / dashes inside, not counted
])
def test_letter_spacing_detection_text(text, expected):
    assert _text.prepare(text, native=False)[0] == expected
    if _native.available():
        assert _text.prepare(text, native=True)[0] == expected


# --- Groupes regroupés librement / freely regrouped groups ---------------------------------------------------------


@pytest.mark.parametrize("text, secret", [
    ("Je suis joignable au 0764 945 16 3, merci.", "945"),
    ("joignable au 07/865/471/79,", "865"),
    ("RPPS : 1044/37321/76", "37321"),
    ("carte nationale d'identité n° 42067 58727 49, valide", "58727"),
    ("passeport n° 67FO 43 43 9 ;", "67FO"),
    ("payé avec ma carte bancaire 41111 1111 111 1111 hier", "41111"),
])
def test_freely_regrouped_identifiers_are_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out, out


def test_regrouped_phone_is_not_cut_out_of_a_longer_number(engine):
    # Le NIR sans clé garde une seule balise : pas de téléphone « 07 99 350 329 » au milieu.
    # The NIR without key keeps one tag: no phone carved out of it.
    out = _masked(engine, "N° d'immatriculation : 1 47 07 99 350 329")
    assert out == "N° d'immatriculation : [NIR_1]", out


# --- Nom de société avec sa forme juridique / company name with its legal form ------------------------------------


@pytest.mark.parametrize("text, kept, masked", [
    ("La SARL DUPONT a livré le chantier. M. Dupont a signé le bon.", "SARL DUPONT", "M. Dupont"),
    ("DUPONT SARL, 12 rue des Lilas, 75011 Paris. Contact : M. Dupont.", "DUPONT SARL", "M. Dupont"),
])
def test_company_name_with_a_legal_form_stays_readable(engine, text, kept, masked):
    out = _masked(engine, text)
    assert kept in out and masked not in out, out


@pytest.mark.parametrize("text, secret", [
    # Revue du 26/10 : civilité ou titre devant, ou forme suivie d'un autre nom : une personne.
    # Review of 26/10: a civility or title before, or a form followed by another name: a person.
    ("Mme Durand SARL", "Durand"),
    ("Gérant : M. Jean Dupont SARL Lumière", "Dupont"),
    ("contrat signé par M. Martin SA", "Martin"),
    ("Me Jean Dupont SCP", "Dupont"),
    ("Le gérant Jean Dupont SARL Lumière", "Dupont"),
])
def test_person_next_to_a_legal_form_stays_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out, out


@pytest.mark.parametrize("text, secret", [
    # Revue du 26/10 : un verbe de lieu ne rend pas lisible un prénom ou un nom seul.
    # Review of 26/10: a place verb does not unmask a lone first name or surname.
    ("Merci de rejoindre Marie à 14h", "Marie"),
    ("Je vais quitter Jean demain", "Jean"),
    ("Il doit regagner Bernard au bureau", "Bernard"),
])
def test_name_after_a_place_verb_stays_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out, out


def test_town_after_a_place_verb_stays_a_town(engine):
    out = _masked(engine, "Mme Claire Lyon souhaite quitter Lyon pour Nantes. Mme Lyon a donné son préavis.")
    assert "quitter Lyon pour Nantes" in out and "Claire" not in out and "Mme Lyon" not in out, out


def test_sole_trader_name_stays_masked(engine):
    out = _masked(engine, "Facture de Jean Dupont EI, 12 rue des Lilas, 75011 Paris.")
    assert "Dupont" not in out, out


# --- Civilité : le mot capitalisé qui suit le nom / civility: the capitalised word after the name -----------------


@pytest.mark.parametrize("text, secret", [
    ("La parole est à M. Matthieu Orphelin, pour soutenir l'amendement.", "Orphelin"),
    ("La parole est à Mme Christine Pires Beaune. Cet amendement vise à aider.", "Beaune"),
])
def test_capitalised_word_after_a_civility_name_is_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out, out


def test_civility_extension_stops_at_a_lowercase_word(engine):
    out = _masked(engine, "M. Paul Martin a signé le bon le 3 mars.")
    assert out.endswith("a signé le bon le 3 mars."), out


# --- Étage écrit avec son rang / floor written with its rank -------------------------------------------------------


@pytest.mark.parametrize("text", [
    "Livrer au 3e étage, 75 cours des Vignes, 73000 Chambéry.",
    "demeurant 1er étage, 12 rue des Lilas, 75011 Paris,",
])
def test_floor_rank_stays_inside_the_address(engine, text):
    out = _masked(engine, text)
    assert "étage" not in out and "Vignes" not in out and "Lilas" not in out, out
