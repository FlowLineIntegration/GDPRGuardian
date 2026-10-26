"""Tests du rendu BOAMP et de son gold (avis inventés) / BOAMP rendering and gold tests (made-up notices)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from tools.corpus.build_boamp import STREET, STREET_IN_TOWN, clean, person_spans, render, sole_trader


def labelled(value: str) -> list[tuple[str, str]]:
    return [(value[s:e], label) for s, e, label in person_spans(value)]


@pytest.mark.parametrize(("value", "expected"), [
    ("Jeanne EXEMPLE", [("Jeanne EXEMPLE", "PERSON")]),
    ("Paul TESTEUR, Directeur Général", [("Paul TESTEUR", "PERSON")]),
    ("Paul Testeur Directeur Général", [("Paul Testeur", "PERSON")]),
    ("M. Le Président, Jean Essai", [("Jean Essai", "PERSON")]),
    ("Mesdames ESSAI Anne et Lucie TEST", [("ESSAI Anne", "PERSON"), ("Lucie TEST", "PERSON")]),
    ("Mme ESSAI a.essai@exemple.fr, ou Mme TEST", [("ESSAI", "PERSON"), ("a.essai@exemple.fr", "EMAIL"),
                                                   ("TEST", "PERSON")]),
    ("M. le Maire", []),
    ("Service des marchés publics", []),
    ("Direction de la Commande Publique", []),
    ("Hôtel de Ville", []),
    ("https://marches.exemple.fr", []),
    # Protocole 1.1 : un service n'est pas une personne / protocol 1.1: a service is not a person.
    ("Groupe Maintenance Essais", []),
    ("Maintenance Garage", []),
    ("DGTEST-Direction Ressources Essais", []),
    ("Jean-Paul ESSAI", [("Jean-Paul ESSAI", "PERSON")]),
])
def test_person_spans(value: str, expected: list[tuple[str, str]]) -> None:
    assert labelled(value) == expected


@pytest.mark.parametrize(("street", "is_street"), [
    ("12 rue des Essais", True), ("BP 429", True), ("Place du Marché", True),
    ("91108 Testville", False), ("Direction des achats", False),
    # Protocole 1.1 : boîtes postales collées ou pointées / protocol 1.1: glued or dotted postal boxes.
    ("BP60120", True), ("CS44416", True), ("C.S.80794", True), ("B.P. 40011", True),
    ("ABCS99999", False), ("Hôtel du Département", False),
])
def test_street_rule(street: str, is_street: bool) -> None:
    assert bool(STREET.search(street)) is is_street


@pytest.mark.parametrize(("town", "is_address"), [
    ("97122 Rue des Essais", True), ("99000 39 avenue des Tests", True), ("CS70001, 99037 TESTVILLE CEDEX", True),
    ("99000 Testville", False), ("TESTVILLE CEDEX 2", False), ("COURS", False), ("99420 ISOLA 2000", False),
])
def test_street_in_town_fields(town: str, is_address: bool) -> None:
    """Protocole 1.1 : voie ou boîte postale écrite dans les champs code postal et ville / street in town fields."""
    assert bool(STREET_IN_TOWN.search(town)) is is_address


def row(donnees: dict[str, Any]) -> dict[str, Any]:
    return {"idweb": "22-1", "famille_libelle": "Marchés", "nature_libelle": "Avis de marché",
            "code_departement": ["99"], "dateparution": "2022-03-01", "procedure_libelle": "Ouverte",
            "famille": "FNS", "nature": "APPEL_OFFRE", "source_schema": "test", "donnees": json.dumps(donnees)}


def test_render_party_blocks_and_free_text() -> None:
    long_text = "Renseignements : écrire à achats@exemple.fr pour toute question sur le dossier de consultation."
    donnees = {
        "IDENTITE": {"DENOMINATION": "Ville de Testville", "CODE_IDENT_NATIONAL": "21990000000000",
                     "CONTACT": "Jeanne EXEMPLE", "ADRESSE": "1 place de la Mairie", "CP": "99000",
                     "VILLE": "Testville", "TEL": "(+33) 1-02-03-04-05", "MEL": "achats@exemple.fr"},
        "OBJET": {"TITRE_MARCHE": "Fournitures", "OBJET_COMPLET": long_text},
        "ATTRIBUTION": {"DECISION": {"TITULAIRE": {"DENOMINATION": "Maître Paul TESTEUR", "CP": "99100",
                                                   "VILLE": "Autreville"}}},
    }
    rec = render(row(donnees))
    assert rec is not None
    got = {(s["text"], s["label"], s["origin"]) for s in rec["spans"]}
    assert ("Jeanne EXEMPLE", "PERSON", "field") in got
    assert ("1 place de la Mairie, 99000 Testville", "ADDRESS", "field") in got
    assert ("(+33) 1-02-03-04-05", "PHONE", "field") in got
    assert ("achats@exemple.fr", "EMAIL", "field") in got
    assert ("achats@exemple.fr", "EMAIL", "repeat") in got   # repeated inside the free text
    assert ("Paul TESTEUR", "PERSON", "field") in got        # individual awardee
    assert ("21990000000000", "ORG_ID", "field") in got
    assert ("99100 Autreville", "LOCATION", "field") in got
    text = rec["text"]
    assert any(text[s:e] == long_text for s, e in rec["ignore"])


def test_render_skips_other_schemas() -> None:
    assert render({**row({}), "donnees": json.dumps({"EFORMS": {}})}) is None


@pytest.mark.parametrize(("raw", "expected"), [
    ("Ville d&#x27;Essai &amp; Cie", "Ville d'Essai & Cie"),
    ("&amp;quot;Projet&amp;quot;", '"Projet"'),       # échappé deux fois / escaped twice
    ("l\x92ouverture des plis", "l’ouverture des plis"),  # C1 de Windows-1252 / Windows-1252 C1 control
    ("Texte ordinaire", "Texte ordinaire"),
])
def test_clean_decodes_source_artefacts(raw: str, expected: str) -> None:
    assert clean(raw) == expected


@pytest.mark.parametrize(("name", "person"), [
    ("TESTEURIX JEANNE", True), ("TESTEURIX Jeanne", True), ("TESTEURIX JEANNE LUCIE", True),
    ("JEANNE TESTEURIX", False),          # prénom en tête : souvent une société / given name first: often a company
    ("TESTEURIX FRANCE", False),          # lieu, pas un prénom / a place, not a given name
    ("TAXI JEANNE", False), ("SARL TESTEURIX", False), ("ESSAI", False), ("ABC JEANNE", False),
])
def test_sole_trader(name: str, person: bool) -> None:
    assert sole_trader(name) is person


def test_render_decodes_entities_and_labels_new_fields() -> None:
    donnees = {
        "IDENTITE": {"DENOMINATION": "Ville d&#x27;Essai", "ADRESSE": "1 place de la Mairie", "CP": "99000",
                     "VILLE": "Testville"},
        "CONDITION_ADMINISTRATIVE": {"LIEU_OUVERTURE_OFFRES": "Service des achats - 3 rue des Essais, 99000 Testville",
                                     "DATE_OUVERTURE_OFFRES": "2022-03-04"},
        "ATTRIBUTION": {"DECISION": {"TITULAIRE": {"DENOMINATION": "TESTEURIX JEANNE", "VILLE": "Autreville"}}},
    }
    rec = render(row(donnees))
    assert rec is not None
    assert "&#x27;" not in rec["text"] and "Ville d'Essai" in rec["text"]
    got = {(s["text"], s["label"]) for s in rec["spans"]}
    assert ("Service des achats - 3 rue des Essais, 99000 Testville", "ADDRESS") in got
    assert ("TESTEURIX JEANNE", "PERSON") in got
    other = render(row({**donnees, "CONDITION_ADMINISTRATIVE": {"LIEU_OUVERTURE_OFFRES": "Testville (99)"}}))
    assert other is not None and not any(s["label"] == "ADDRESS" and "(99)" in s["text"] for s in other["spans"])
