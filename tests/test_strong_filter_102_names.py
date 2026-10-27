"""Noms, sociétés et entrepreneurs individuels (1.0.2, deuxième essai terrain) : noms en minuscules sans indice,
civilité après un éponyme, c'h breton, Prénom_Nom dans un nom de fichier, précision (verbes, sigles, lieux, labels),
raison sociale entière lisible avec sa forme juridique, portée de l'entrepreneur individuel.

Names, companies and sole traders (1.0.2, second field test). Chaque cas tourne sur le noyau Rust (s'il est
installé) et sur la référence Python, qui doivent rendre le même texte. Every case runs on the Rust core (when
installed) and on the Python reference, which must render the same text. Données fictives / fictitious data.
"""

from __future__ import annotations

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


# --- B. Noms en minuscules sans indice / lowercase names with no cue ---------------------------------------------


@pytest.mark.parametrize("text, secrets", [
    ("rdv avec sophie martin demain", ["sophie", "martin"]),
    ("merci à sandrine lacroix", ["sandrine", "lacroix"]),
    ("josette dubois a appelé hier.", ["josette", "dubois"]),
    ("Rappeler josette dubois demain.", ["josette", "dubois"]),
])
def test_lowercase_given_name_and_surname_are_masked(engine, text, secrets):
    out = _masked(engine, text)
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("text", [
    "Il faut voir avec le service demain matin.",
    "Nous irons à paris lundi pour la réunion.",
    "Un martin pêcheur sur la rivière.",
    "La pierre blanche reste au jardin.",
    "Adresse : sophie.martin@exemple.fr",
])
def test_ordinary_lowercase_prose_is_kept(engine, text):
    out = _masked(engine, text)
    assert "PERSONNE" not in out, out


# --- D. Civilité après un éponyme / a civility after an eponym ---------------------------------------------------


@pytest.mark.parametrize("text, secrets", [
    ("Je vous transmets l'arrêt maladie de M. Jean Dupont, reçu ce matin.", ["Jean", "Dupont"]),
    ("Ci-joint l'arrêt maladie de Mme Nadia Ouazzani", ["Nadia", "Ouazzani"]),
])
def test_civility_after_an_eponym_names_the_person(engine, text, secrets):
    out = _masked(engine, text)
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("text", [
    "La rue du Docteur Roux est fermée.",
    "Le patient présente un syndrome de Down.",
    "La maladie de Parkinson évolue.",
])
def test_eponyms_stay_readable(engine, text):
    assert _masked(engine, text) == text


# --- E. Autres formes de noms / other name forms -----------------------------------------------------------------


def test_breton_ch_belongs_to_the_name(engine):
    out = _masked(engine, "Cc : Solenn Guivarc'h")
    assert "Solenn" not in out and "Guivarc" not in out, out


def test_given_surname_in_a_file_name_is_masked(engine):
    out = _masked(engine, "PJ : CV_Nadia_Haddad.pdf, passeport_Karim_Idrissi.jpg")
    for secret in ("Nadia", "Haddad", "Karim", "Idrissi"):
        assert secret not in out, out
    assert out.startswith("PJ : CV_") and ".pdf, passeport_" in out and out.endswith(".jpg"), out


@pytest.mark.parametrize("text", ["Voir rapport_Annuel_Final.pdf", "Fichier export_Paris_Lyon.csv"])
def test_file_names_without_a_given_name_are_kept(engine, text):
    assert _masked(engine, text) == text


@pytest.mark.parametrize("text, secrets", [
    ("Jean-Marc Delaunay (JMD) valide.", ["Delaunay", "JMD"]),
    ("Le trigramme ASM signe le compte rendu.", ["ASM"]),
    ("Paraphes : JBR / MEA", ["JBR", "MEA"]),
])
def test_initials_are_masked(engine, text, secrets):
    out = _masked(engine, text)
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("text", [
    "Jean-Marc Delaunay (RH) valide.",        # pas ses initiales / not his initials
    "Le trigramme CSE est réservé.",           # sigle exclu / excluded acronym
])
def test_other_capitals_after_a_person_or_cue_are_kept(engine, text):
    out = _masked(engine, text)
    assert "RH" in out or "CSE" in out, out


# --- K. Précision : verbes, sigles, lieux, labels / precision ----------------------------------------------------


@pytest.mark.parametrize("text", [
    "Le salarié doit être convoqué.",
    "Le juge doit statuer. Le président doit signer. Le médecin doit voir. Le formateur doit venir.",
    "Chantier de Pont-l'Abbé. Montant facturé : 84,00 €.\nMontant facturé : 12,00 €.",
    "Ville: Meylan",
    "Suivi par l'UDAF 44 depuis 2020.",
    "Marié le 12/06/2015, il a deux enfants.",
    "Mariée, deux enfants.",
])
def test_ordinary_words_never_become_people(engine, text):
    assert _masked(engine, text) == text


def test_acronym_mailbox_part_is_not_a_person(engine):
    out = _masked(engine, "Le CSE se réunira jeudi. Secrétariat : cse.morez@mpj-sa.fr.")
    assert out.startswith("Le CSE se réunira jeudi."), out
    assert "morez" not in out, out


def test_sentence_initial_imperative_is_a_word(engine):
    out = _masked(engine, "J.D. Contactez P. Lemoine")
    assert "Contactez" in out and "Lemoine" not in out, out


def test_town_glued_to_saint_is_not_propagated(engine):
    out = _masked(engine, "TOULOUSE Bernard a saisi le tribunal. Il habite Saint-Claude. CLAUDE Martin aussi.")
    assert "Saint-Claude" in out and "Bernard" not in out and "CLAUDE" not in out, out


# --- L. Raison sociale entière lisible, portée de l'entrepreneur individuel / company names, sole-trader scope -----


@pytest.mark.parametrize("text", [
    "SARL DUPONT BÂTIMENT a facturé.",
    "La SAS Dupont Frères a signé.",
    "SCP Lambert & Associés représente le client.",
    "SARL Kerbrat Services a livré.",
    "Clinique Jules Verne SAS accueille le patient.",
    "La SELARL VIDAL & ASSOCIÉS plaide. Le cabinet SELARL VIDAL & ASSOCIÉS a écrit.",
    "Biscuiterie de l'Ouest SA a recruté.",
    "SARL DUPONT, DUPONT SARL, SA Michelin, Martin SAS.",
])
def test_company_name_with_a_legal_form_stays_whole(engine, text):
    assert _masked(engine, text) == text


def test_sole_trader_cue_is_scoped_to_its_paragraph(engine):
    filler = "Texte neutre sans rien. " * 30
    text = ("la société Armor Services SAS a proposé 15 500 €, SIREN 552 100 554. " + filler
            + "Entrepreneur individuel concerné : Christophe Morel, SIRET 812 345 670 00127.")
    out = _masked(engine, text)
    assert "SIREN 552 100 554" in out, out           # société, loin du repère / a company, far from the cue
    assert "812 345 670 00127" not in out and "Morel" not in out, out


def test_sole_trader_record_over_several_lines_is_masked(engine):
    out = _masked(engine, "Entrepreneur individuel\nNom : Christophe Morel\nSIRET : 812 345 670 00127")
    assert "812 345 670 00127" not in out, out


def test_far_sole_trader_cue_still_covers_a_number_with_no_company_nearby(engine):
    text = "Jean Martin exerce comme entrepreneur individuel." + " Texte sans rapport." * 30 + " SIREN 732 829 320."
    assert "732 829 320" not in _masked(engine, text)
