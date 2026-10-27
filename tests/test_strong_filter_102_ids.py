"""Filtre fort 1.0.2, second tour, voie « identifiants » (items H, I, J, M du second test terrain) : identifiants
directs dans des formats courants, SIRET d'un entrepreneur individuel, identifiants de connexion, mots de passe,
jetons et sites personnels, bonnes étiquettes.

Strong filter 1.0.2, second round, "identifiers" lane (field test 2, items H, I, J, M): direct identifiers in common
formats, a sole trader's SIRET, logins, passwords, tokens and personal sites, right labels. Chaque cas tourne sur le
noyau Rust (s'il est installé) et sur la référence Python, qui doivent rendre le même texte. Every case runs on the
Rust core (when installed) and on the Python reference, which must render the same text. Données fictives /
fictitious data.
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


def _luhn(prefix: str) -> str:
    """Complète `prefix` d'une clé de Luhn / completes `prefix` with a Luhn check digit."""
    for digit in "0123456789":
        candidate = prefix + digit
        total = 0
        for i, ch in enumerate(reversed(candidate)):
            n = int(ch) * (2 if i % 2 else 1)
            total += n - 9 if n > 9 else n
        if total % 10 == 0:
            return candidate
    raise AssertionError(prefix)


_CARD = _luhn("497010123456789")
_SIREN = "552100554"  # SIREN fictif à clé de Luhn juste / fictitious SIREN with a valid Luhn key
_VAT = f"FR{(12 + 3 * (int(_SIREN) % 97)) % 97:02d}{_SIREN}"


# --- Item H : formats courants / common formats ---------------------------------------------------------------------


@pytest.mark.parametrize("text, secrets, tag", [
    ("iban : fr76 3000 6000 0112 3456 7890 189", ["fr76", "3000", "189"], "[IBAN_1]"),
    ("Virement sur fr7630006000011234567890189 demain.", ["fr7630006000011234567890189"], "[IBAN_1]"),
    ("Véhicule AB123CD stationné.", ["AB123CD"], "[PLAQUE_1]"),
    ("Garée : ab123cd", ["ab123cd"], "[PLAQUE_1]"),
    ("Véhicule ab-123-cd stationné.", ["ab-123-cd"], "[PLAQUE_1]"),
    ("Véhicule ab 123 cd stationné.", ["ab 123 cd"], "[PLAQUE_1]"),
    ("Liste : 1234 AB 75, 567 XY 29", ["1234 AB", "567 XY"], "[PLAQUE_2]"),
    ("Le VIN VF1RFB00X56789012 du véhicule.", ["VF1RFB00X56789012"], "[IDENTIFIANT_1]"),
    (f"Carte : {_CARD}", [_CARD], "[CARTE_1]"),
    (f"{_CARD}", [_CARD], "[CARTE_1]"),
    (f"Payé avec {_CARD[:4]}.{_CARD[4:8]}.{_CARD[8:12]}.{_CARD[12:]} hier.", [_CARD[4:8], _CARD[12:]], "[CARTE_1]"),
    ("Il a transmis la copie de sa carte d'identité n° X4RTBPFW4\npasseport n° 19AB45218 en cours.",
     ["X4RTBPFW4", "19AB45218"], "[PASSEPORT_1]"),
    ("Mme Anne Mercier, n° ADELI : 75 99 1234 5, infirmière.", ["1234"], "[ADELI_1]"),
    ("Dr Paul Auger, N° Ordre 75/12345.", ["12345"], "[IDENTIFIANT_1]"),
    ("Kinésithérapeute, n° AM 29 1 23456 7.", ["23456"], "[ADELI_1]"),
    ("Merci de rappeler la référence 987654321 au guichet.", ["987654321", "321"], "[IDENTIFIANT_1]"),
    ("numéro de dossier MDPH 2026-0045", ["2026", "0045"], "[IDENTIFIANT_1]"),
    ("dossier 2026-0045", ["2026", "0045"], "[IDENTIFIANT_1]"),
    ("dossier MDPH n° 2026-0045", ["2026", "0045"], "[IDENTIFIANT_1]"),
    ("Numéro 4970 1012 3456 7899 utilisé.", ["4970", "1012", "7899"], "[IDENTIFIANT_1]"),
])
def test_common_formats_are_masked_whole(engine, text, secrets, tag):
    out = _masked(engine, text)
    for secret in secrets:
        assert secret not in out, out
    assert tag in out, out


@pytest.mark.parametrize("text", [
    "Total 1500 HT 20 % de remise",
    "Article 1234 CE 75 du code",
    "Version 2024 RC 12 publiée",
    "Prix 1250 EUR 30 jours net",
    "La facture 2024-2025 est due.",
    "dossier 2024-03-15 ouvert",
    "facture 1500,50 € réglée",
])
def test_numbers_that_are_not_identifiers_stay_readable(engine, text):
    assert _masked(engine, text) == text


def test_labelled_number_keeps_the_time_and_the_amount(engine):
    assert _masked(engine, "dossier 1234 12:30") == "dossier [IDENTIFIANT_1] 12:30"
    assert _masked(engine, "contrat 2024 1500 €") == "contrat [IDENTIFIANT_1] 1500 €"
    assert _masked(engine, "commande 20512 15 articles") == "commande [IDENTIFIANT_1] 15 articles"


@pytest.mark.parametrize("text, expected", [
    ("Client 987 654 321 merci", "Client [IDENTIFIANT_1] merci"),
    ("Client 12/345/678 merci", "Client [IDENTIFIANT_1] merci"),
    ("ticket #987 654 321.", "ticket #[IDENTIFIANT_1]."),
    ("id 987 654 321", "id [IDENTIFIANT_1]"),
    ("badge 4471 2209", "badge [IDENTIFIANT_1]"),
    ("abonné n° 778 899 120", "abonné n° [IDENTIFIANT_1]"),
    ("client 06 12 34 56 78", "client [TEL_1]"),
])
def test_labelled_number_in_short_groups_is_one_span(engine, text, expected):
    assert _masked(engine, text) == expected


@pytest.mark.parametrize("text", [
    "dossier 12/03/2024",
    "commande 25 000 pièces",
    "facture 12 500,00 €",
    "client 10 000 €",
    "L'idée 1234 est bonne",
    "dossier 12 h 30",
    "Commande du 12/03/2024",
])
def test_labelled_number_never_takes_a_date_an_amount_or_a_quantity(engine, text):
    assert _masked(engine, text) == text


# --- Item I : SIRET, SIREN et TVA d'un entrepreneur individuel / a sole trader's company numbers -------------------


@pytest.mark.parametrize("text, secret, tag", [
    ("Il exploite en nom propre (SIRET 552 100 554 00013).", "552 100 554", "[SIRET_1]"),
    ("Plombier : Hervé Clément, artisan, SIRET 55210055400013", "55210055400013", "[SIRET_1]"),
    ("Dr Anne Mercier, médecin libéral, SIRET 552 100 554 00013.", "552 100 554", "[SIRET_1]"),
    ("M. Hervé Clément\nSIRET 55210055400013", "55210055400013", "[SIRET_1]"),
    ("Il exploite en nom propre (SIREN 552 100 554).", "552 100 554", "[SIREN_1]"),
    (f"Hervé Clément, artisan, TVA {_VAT}", _VAT, "[TVA_1]"),
])
def test_sole_trader_number_next_to_the_person_is_masked(engine, text, secret, tag):
    out = _masked(engine, text)
    assert secret not in out and tag in out, out


@pytest.mark.parametrize("text", [
    "La société Armor Services SAS (SIRET 552 100 554 00013) a proposé 15 500 €.",
    f"La société Armor Services SAS, TVA {_VAT}, a signé.",
    "Contact Hervé Clément de la SARL Armor, SIRET 55210055400013",
])
def test_company_number_stays_readable(engine, text):
    out = _masked(engine, text)
    assert ("552 100 554" in out) or ("55210055400013" in out) or (_VAT in out), out


# --- Item J : connexion, mots de passe, jetons, sites personnels / logins, passwords, tokens, personal sites -------


@pytest.mark.parametrize("text, secret, tag", [
    ("identifiant : jdupont", "jdupont", "[PSEUDO_1]"),
    ("login : a.roux", "a.roux", "[PSEUDO_1]"),
    ("Nom d'utilisateur : marie.leclerc", "marie.leclerc", "[PSEUDO_1]"),
    ("login jdupont", "jdupont", "[PSEUDO_1]"),
    ("identifiant jdupont, mot de passe Zx9!kLm27pQ", "jdupont", "[SECRET_1]"),
    ("utilisateur jdupont a été bloqué", "jdupont", "[PSEUDO_1]"),
    ("connecté en tant que jdupont hier", "jdupont", "[PSEUDO_1]"),
    ("mot de passe : Zx9!kLm27pQ", "Zx9!kLm27pQ", "[SECRET_1]"),
    ("mdp: Zx9!kLm27pQ", "Zx9!kLm27pQ", "[SECRET_1]"),
    ("password = Zx9!kLm27pQ", "Zx9!kLm27pQ", "[SECRET_1]"),
    ("Lien : https://app.exemple.fr/reset?token=abcDEF1234567890 merci", "abcDEF1234567890", "[SECRET_1]"),
    ("https://api.exemple.fr/v1/data?key=Zt8kQ2pLmN4x&format=json", "Zt8kQ2pLmN4x", "[SECRET_1]"),
    ("Kevin Lambert (@jdupont sur X) a répondu.", "jdupont", "[PSEUDO_1]"),
    ("Portfolio sophiemartin.com", "sophiemartin", "[URL_1]"),
    ("Mon blog https://jdupont.blog", "jdupont", "[URL_1]"),
    ("Site perso : https://www.kevin-lambert.fr", "kevin-lambert", "[URL_1]"),
])
def test_logins_secrets_and_personal_sites_are_masked(engine, text, secret, tag):
    out = _masked(engine, text)
    assert secret not in out and tag in out, out


@pytest.mark.parametrize("text, secret", [
    ("Kevin Lambert, voir https://kevinlambert.fr pour son portfolio.", "kevinlambert"),
    ("Kevin Lambert : https://kevinlambert.fr", "kevinlambert"),
    ("LAMBERT Kevin écrit sur www.kevin-lambert.fr chaque semaine.", "kevin-lambert"),
    ("Jean Dupont tient le blog jdupont.blog depuis 2019.", "jdupont"),
])
def test_site_named_after_a_quoted_person_is_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out and "[URL_1]" in out, out


@pytest.mark.parametrize("text", [
    "Kevin Lambert recommande https://www.service-public.fr pour la démarche.",
    "Voir https://exemple.fr/aide, Kevin Lambert répondra.",
])
def test_site_not_named_after_a_person_stays_readable(engine, text):
    out = _masked(engine, text)
    assert "https://" in out and "[URL" not in out, out


def test_sentence_full_stop_stays_after_a_password(engine):
    assert _masked(engine, "Son mot de passe est Zx9!kLm27pQ.") == "Son mot de passe est [SECRET_1]."
    assert _masked(engine, "mot de passe : Zx9!kLm27pQ, puis valider") == "mot de passe : [SECRET_1], puis valider"


@pytest.mark.parametrize("text", [
    "L'utilisateur clique sur le bouton.",
    "L'identifiant unique est généré.",
    "Le login sur le portail échoue.",
    "Utilisateur standard sans droits.",
    "identifiant de connexion oublié",
    "Votre identifiant personnel vous sera envoyé.",
    "Le mot de passe est oublié.",
    "Lire le blog https://www.exemple.fr/article/12.",
    # Corpus du propriétaire (datasets/audit/pack-v1) / the owner's pack.
    "Le compte rendu doit protéger tout identifiant pouvant être relié à la personne.",
    "Le protocole associe un identifiant participant et un contexte de collecte.",
])
def test_common_words_after_a_login_cue_stay_readable(engine, text):
    assert _masked(engine, text) == text


# --- Item M : bonnes étiquettes / right labels ---------------------------------------------------------------------


@pytest.mark.parametrize("text, tag, wrong", [
    ("passeport n° 19AB45218", "[PASSEPORT_1]", "[CNI"),
    ("IBAN : FR76 3000 6000 1112", "[IBAN_1]", "[CARTE"),
    ("Garée : AB123CD", "[PLAQUE_1]", "[IDENTIFIANT"),
    (f"Réf transaction {_CARD} ok", "[CARTE_1]", "[IDENTIFIANT"),
])
def test_right_label(engine, text, tag, wrong):
    out = _masked(engine, text)
    assert tag in out and wrong not in out, out


@pytest.mark.parametrize("text", [
    "Établissement FINESS 290000017.",
    "TVA BE 0477.472.701 pour la facture.",
])
def test_facility_and_foreign_company_numbers_never_become_a_person_number(engine, text):
    out = _masked(engine, text)
    assert "[ADELI" not in out and "[TEL" not in out, out


def test_matricule_and_next_line_phone_stay_two_values(engine):
    out = _masked(engine, "Matricule 0049217\n06 74 28 19 53")
    assert out == "Matricule [IDENTIFIANT_1]\n[TEL_1]", out


# --- Explication / explain ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text, reason", [
    ("login jdupont", "keyword"),
    ("Son mot de passe est Zx9!kLm27pQ.", "keyword"),
    ("dossier 2026-0045", "keyword"),
    ("Liste : 1234 AB 75", "format"),
    ("Garée : AB123CD", "validated"),
    ("Portfolio sophiemartin.com", "keyword"),
    ("Kevin Lambert : https://kevinlambert.fr", "personal_site_name"),
])
def test_every_new_rule_has_a_named_reason(engine, text, reason):
    report = Anonymizer(countries=("FR",), native=engine.native, explain=True).anonymize(text).report
    reasons = [item["reason"] for item in report["explain"]]
    assert reason in reasons, reasons
