"""Organisations : formes juridiques, règle physicomorale, politique de masquage / organisations."""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer
from gdprguardian.heuristics.organizations import OrganizationDetector
from gdprguardian.types import PRIORITY_HEURISTIC, PRIORITY_PROPAGATED

NAMES = [
    ("Le contrat lie Acme SAS et Globex SARL.", ["Acme", "Globex"]),
    ("Volkswagen AG, Siemens GmbH et Philips N.V. sont cités.", ["Volkswagen", "Siemens", "Philips"]),
    ("Les sociétés Initech Ltd, Hooli Inc. et Globex LLC.", ["Initech", "Hooli", "Globex"]),
    ("Fournisseur : Ferrovia S.p.A., Telar S.L. et Bouwbedrijf B.V.", ["Ferrovia", "Telar", "Bouwbedrijf"]),
    ("La société Globex a été rachetée.", ["Globex"]),
    ("Hier Acme SAS a payé la facture.", ["Acme"]),
    ("Les Jardins de Provence SARL embauchent.", ["Les Jardins de Provence"]),
    ("La SCI du Moulin vend un terrain.", ["du Moulin"]),
]


@pytest.mark.parametrize(("text", "expected"), NAMES)
def test_organisation_names(found, text, expected):
    assert found(text, "ORG") == expected


def test_companies_are_reported_but_kept_by_default(fr):
    result = fr.anonymize("Acme SAS a signé avec la société Globex.")
    assert result.text == "Acme SAS a signé avec la société Globex."
    assert result.report["kept_by_policy"] == {"ORG": 2}


def test_company_ids_mask_policy_masks_organisations():
    out = Anonymizer(countries="FR", company_ids="mask").anonymize("Acme SAS a signé avec la société Globex.").text
    assert out == "[ORG_1] SAS a signé avec la société [ORG_2]."


def test_strict_profile_masks_organisations():
    out = Anonymizer(countries="FR", profile="strict").anonymize("Acme SAS a signé.").text
    assert out == "[ORG_1] SAS a signé."


def test_physicomorale_company_named_after_a_person_is_masked(fr):
    out = fr.anonymize("La SARL Durand et Fils et le Cabinet Martin & Associés sont mandatés.").text
    assert out == "La SARL [ORG_1] et le [ORG_2] sont mandatés."


def test_company_name_with_a_legal_form_stays_readable_and_the_person_is_masked(fr):
    # Règle produit du 26/10 : « Dupont SARL » est une personne morale (considérant 14), lisible ; « M. Dupont »
    # est masqué ; « Jean Dupont EI » (entrepreneur individuel) est une personne. Product rule of 26/10: a company
    # name with a legal-entity form stays readable; the person and the sole trader are masked.
    out = fr.anonymize("Dupont SARL a livré. M. Dupont a signé. Jean Dupont EI facture.").text
    assert out == "Dupont SARL a livré. M. [PERSONNE_1] a signé. [PERSONNE_1] EI facture."


@pytest.mark.parametrize(("text", "expected"), [
    # Forme juridique de personne morale juste avant ou après : nom de société, lisible / company name, readable.
    ("Petit SARL a livré la commande.", "Petit SARL a livré la commande."),
    ("Blanc SAS et la SARL Martin ont signé.", "Blanc SAS et la SARL Martin ont signé."),
    # Sans forme juridique collée : nom de personne ambigu, masqué / no legal form next to it: masked as a person.
    ("La société Petit a livré.", "La société [PERSONNE_1] a livré."),
])
def test_company_named_like_a_person(fr, text, expected):
    assert fr.anonymize(text).text == expected


def test_family_business_words_are_not_person_names(fr):
    # « & Fils » relève de la raison sociale, pas d'une seconde personne / part of the company name.
    assert fr.anonymize("Lefort & Fils a livré.").text == "[ORG_1] a livré."


def test_articles_and_particles_are_not_given_names(found):
    # « Le » a un rang de prénom dans le fichier Insee : il ne fait pas d'« Le Monde » une personne.
    assert found("Le Monde SA publie ses comptes.", "ORG") == ["Le Monde"]
    assert found("Le Monde SA publie ses comptes.") == []


def test_kept_organisation_never_shields_a_person_name(fr):
    out = fr.anonymize("M. Petit est le gérant de la Boulangerie Petit SARL.").text
    assert "Petit" not in out


def test_sole_trader_context_masks_the_company(fr):
    out = fr.anonymize("Acme SAS, entrepreneur individuel, facture ses prestations.").text
    assert "Acme" not in out


def test_priorities(context):
    # Une organisation conservée a la priorité minimale : elle ne protège jamais un nom de personne.
    # A kept organisation has the lowest priority: it never shields a person name.
    ctx = context("Acme SAS et la SARL Durand et Fils.")
    spans = {ctx.text[s.start:s.end]: s for s in OrganizationDetector(None).detect(ctx)}
    assert (spans["Acme"].personal, spans["Acme"].priority) == (False, PRIORITY_PROPAGATED)
    assert (spans["Durand et Fils"].personal, spans["Durand et Fils"].priority) == (True, PRIORITY_HEURISTIC)
    assert all(s.entity == "ORG" and s.label == "ORG" and s.propagate for s in spans.values())


@pytest.mark.parametrize("text", [
    "L'AG du 12 mars a validé les comptes.",
    "SA Majesté la reine.",
    "La société a été créée en 1990.",
    "Le groupe se réunit demain.",
])
def test_negatives(found, text):
    assert found(text, "ORG") == []
