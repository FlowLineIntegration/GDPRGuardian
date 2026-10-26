"""Tests du rendu BODACC et de son gold (annonces inventées) / BODACC rendering and gold tests (made-up notices)."""

from __future__ import annotations

import json
from typing import Any

from tools.corpus.build_bodacc import address_parts, fr_date, render


def spans_of(rec: dict[str, Any], label: str) -> list[str]:
    return [s["text"] for s in rec["spans"] if s["label"] == label]


def notice(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "A2026TEST1", "publicationavis": "A", "parution": "20260101", "dateparution": "2026-01-02",
        "numeroannonce": 7, "typeavis_lib": "Avis initial", "familleavis_lib": "Procédures collectives",
        "tribunal": "Greffe du Tribunal de Commerce de Testville", "numerodepartement": "99",
        "listepersonnes": json.dumps({"personne": {
            "typePersonne": "pp",
            "numeroImmatriculation": {"numeroIdentification": "123 456 789", "codeRCS": "RCS",
                                      "nomGreffeImmat": "Testville"},
            "nom": "EXEMPLE (EI)", "prenom": "Jeanne, Marie", "nomCommercial": "Chez Jeanne EXEMPLE",
            "activite": "Boulangerie",
            "adressePP": {"numeroVoie": "12", "typeVoie": "rue", "nomVoie": "des Essais", "codePostal": "99000",
                          "ville": "Testville"}}}),
        "jugement": json.dumps({"famille": "Jugement d'ouverture", "nature": "Liquidation judiciaire",
                                "date": "2026-01-01",
                                "complementJugement": "désignant liquidateur Me Autre Personne. Contre Jeanne "
                                                      "EXEMPLE."}),
        "acte": json.dumps({"descriptif": "Adresse de l'ancien propriétaire : 5 place Neuve 99100 AUTREVILLE. "
                                          "Fin."}),
    }
    base.update(overrides)
    return base


def test_natural_person_fields_are_gold() -> None:
    rec = render(notice())
    assert rec is not None
    text = rec["text"]
    assert "Nom : EXEMPLE (EI)" in text and "n° RCS : 123 456 789 RCS Testville" in text
    persons = spans_of(rec, "PERSON")
    assert "EXEMPLE" in persons and "(EI)" not in " ".join(persons)
    assert {"Jeanne", " Marie".strip()} <= set(persons)
    assert spans_of(rec, "ID") == ["123 456 789"]
    assert "12 rue des Essais 99000 Testville" in spans_of(rec, "ADDRESS")
    assert "5 place Neuve 99100 AUTREVILLE" in spans_of(rec, "ADDRESS")
    assert spans_of(rec, "DATE") == ["1 janvier 2026"]


def test_repeats_and_trade_names_are_gold_but_officers_are_not() -> None:
    rec = render(notice())
    assert rec is not None
    origins = {(s["text"], s["origin"]) for s in rec["spans"] if s["label"] == "PERSON"}
    assert ("Jeanne EXEMPLE", "repeat") in origins          # in the judgment complement
    assert any(o == "trade_name" or t == "Jeanne EXEMPLE" for t, o in origins)
    assert "Autre Personne" not in spans_of(rec, "PERSON")  # court officer: not described by any field
    text = rec["text"]
    zone_texts = [text[s:e] for s, e in rec["ignore"]]
    assert any("liquidateur" in z for z in zone_texts)


def test_company_identifiers_are_kept_family() -> None:
    company = {"typePersonne": "pm", "numeroImmatriculation": {"numeroIdentification": "987 654 321"},
               "denomination": "SOCIETE TEST", "adresseSiegeSocial": {"codePostal": "99000", "ville": "Testville"}}
    pers = json.loads(notice()["listepersonnes"])["personne"]
    rec = render(notice(listepersonnes=json.dumps({"personne": [pers, company]})))
    assert rec is not None
    assert spans_of(rec, "ORG_ID") == ["987 654 321"]
    assert "SOCIETE TEST" in spans_of(rec, "ORG")
    assert "99000 Testville" in spans_of(rec, "LOCATION")


def test_notice_without_natural_person_is_skipped() -> None:
    company = {"typePersonne": "pm", "denomination": "SOCIETE TEST"}
    assert render(notice(listepersonnes=json.dumps({"personne": company}))) is None


def test_helpers() -> None:
    assert fr_date("2026-08-04") == "4 août 2026"
    assert fr_date("bad") == "bad"
    assert address_parts({"codePostal": "99000", "ville": "Testville"}) == ("99000 Testville", False)
    assert address_parts({"numeroVoie": "3", "nomVoie": "Haute", "codePostal": "99000",
                          "ville": "Testville", "pays": "Belgique"}) == ("3 Haute 99000 Testville Belgique", True)
