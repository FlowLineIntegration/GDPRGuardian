"""Filtre fort 1.0.2, détecteurs : identifiants techniques, codes d'identifiant, identités en ligne, téléphones.

Strong filter 1.0.2, detectors: technical identifiers, identifier codes, online identities, phones (REGLES.md § 2).
Chaque cas tourne sur le noyau Rust (s'il est installé) et sur la référence Python, qui doivent rendre le même texte.
Every case runs on the Rust core (when installed) and on the Python reference, which must render the same text.
Données fictives / fictitious data.
"""

from __future__ import annotations

import random

import pytest

from gdprguardian import Anonymizer, _native
from gdprguardian.detectors import codes
from gdprguardian.detectors.codes import exclusion, is_code
from gdprguardian.validators import fr, intl

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]


@pytest.fixture(scope="module", params=_ENGINES)
def engine(request) -> Anonymizer:
    anonymizer = Anonymizer(countries=("FR",), native=request.param, explain=True)
    assert anonymizer.native == request.param
    return anonymizer


def _masked(engine: Anonymizer, text: str) -> str:
    return engine.anonymize(text).text


def _reasons(engine: Anonymizer, text: str) -> dict[str, str]:
    """Règle → raison des lignes `explain` / rule → reason of the explain lines."""
    return {line["rule"]: line["reason"] for line in engine.anonymize(text).report["explain"]}


# --- Item 3 : identifiants techniques / technical identifiers ------------------------------------------------------


@pytest.mark.parametrize("text, secret, tag", [
    ("connexion depuis 2a01:e0a:4d43:d2::7639 hier", "2a01", "[IP_1]"),
    ("hôte 2001:db8:85a3::8a2e:370:7334 joint", "85a3", "[IP_1]"),
    ("lien local fe80::1%eth0 actif", "fe80", "[IP_1]"),
    ("borne 001a.2b3c.4d5e en panne", "2b3c", "[MAC_1]"),
    ("ticket 550e8400-e29b-41d4-a716-446655440000 ouvert", "550e8400", "[IDENTIFIANT_1]"),
    ("Cookie: sid=a8f5f167f44f4964e6c998dee827110c; lang=fr", "a8f5f167", "[SECRET_1]"),
    ("PHPSESSID=9b2c7d1e4f5a6b8c dans le journal", "9b2c7d1e", "[SECRET_1]"),
    ("X-Api-Key: 0123456789abcdef0123456789abcdef", "0123456789abcdef", "[SECRET_1]"),
    ("client_secret=Zx81kq0Pw2Lr7Tn5Vb4M", "Zx81kq0", "[SECRET_1]"),
    ("Authorization: Basic dXNlcjpwYXNzd29yZA==", "dXNlcjpw", "[SECRET_1]"),
    ("voiceprint_id=vp_29dded3w6o enregistré", "vp_29dded3w6o", "[IDENTIFIANT_1]"),
    ("gabarit biométrique BIO-184665 associé", "BIO-184665", "[IDENTIFIANT_1]"),
])
def test_technical_identifiers_are_masked(engine, text, secret, tag):
    out = _masked(engine, text)
    assert secret not in out and tag in out, out


@pytest.mark.parametrize("text", [
    "Rendez-vous à 12:30:45 précises.",
    "Utiliser std::vector et a::b dans le code.",
    "La session de formation commence lundi.",
    "Session : printemps, salle 4.",
    "Poser l'empreinte digitale pour ouvrir.",
])
def test_technical_lookalikes_stay(engine, text):
    assert _masked(engine, text) == text


def test_cookie_header_values_are_masked(engine):
    text = "Cookie: theme=dark; prefs=Zq81Lm2nPx; lang=fr\nSet-Cookie: tracker=AbCdEf123456; Path=/; Max-Age=31536000"
    out = _masked(engine, text)
    assert out == ("Cookie: theme=dark; prefs=[SECRET_1]; lang=fr\n"
                   "Set-Cookie: tracker=[SECRET_2]; Path=/; Max-Age=31536000"), out
    assert _reasons(engine, text) == {"SECRET_COOKIE": "keyword"}


def test_six_group_mac_is_never_read_as_ipv6(engine):
    out = _masked(engine, "carte réseau 00:1A:2B:3C:4D:5E branchée")
    assert out == "carte réseau [MAC_1] branchée", out


def test_ipv6_and_dotted_mac_canonical_values():
    assert intl.ipv6("a::b") is None
    assert intl.ipv6("fe80::1%eth0") == "fe80::1"
    assert intl.mac("001a.2b3c.4d5e") == "00:1A:2B:3C:4D:5E"
    assert intl.mac("1234.5678.9012") is None


def test_technical_reasons(engine):
    reasons = _reasons(engine, "PHPSESSID=9b2c7d1e4f5a6b8c ; uuid 550e8400-e29b-41d4-a716-446655440000")
    assert reasons == {"SECRET_SESSION": "keyword", "UUID": "format"}, reasons


# --- Item 2 : codes d'identifiant / identifier codes ---------------------------------------------------------------


@pytest.mark.parametrize("code", ["CLT-172620", "CLT185818", "EMP-0042", "INC-2024-0012", "TCK022609",
                                  "VOX-6940-AK84", "AY-543-SS", "a3f5c2d19e8b7a6f5c4d3e2f1a0b9c8d"])
def test_identifier_codes_are_masked(engine, code):
    out = _masked(engine, f"Référence {code} transmise.")
    assert code not in out and "[IDENTIFIANT_1]" in out, out


def test_glued_plate_shape_is_a_plate(engine):
    """« ab123cd » : forme SIV collée, masquée comme plaque (second test terrain, item H/M) / a glued SIV plate."""
    out = _masked(engine, "Référence ab123cd transmise.")
    assert "ab123cd" not in out and "[PLAQUE_1]" in out, out


@pytest.mark.parametrize("token, name", [
    ("v1.2.3", "version"), ("1.2.3-beta", "version"), ("14h30-16h00", "time"), ("L1234-5", "legal_article"),
    ("R.4127-1", "legal_article"), ("1920x1080", "dimensions"), ("T1-2024", "period"), ("Q3-2024", "period"),
    ("COVID-19", "short_list"), ("SARS-CoV-2", "short_list"), ("AGRIFRPP882", "bic"),
    ("2024Nombre", "digits_glued_to_word"), ("1234EUR", "unit_suffix"), ("250km", "unit_suffix"),
    ("12mars2024", "month_name"), ("2024-03-12T14", "iso_timestamp"), ("ISO-27001", "standard"),
])
def test_identifier_code_exclusions_are_named(token, name):
    assert exclusion(token) == name


@pytest.mark.parametrize("text", [
    "Version v1.2.3 publiée à 14h30.",
    "Article L1234-5 et R.4127-1 du code.",
    "Écran 1920x1080, bilan T1-2024, COVID-19, SARS-CoV-2.",
    "BIC AGRIFRPP882, en 2024Nombre de cas, le 1er, à 250km.",
    "Voir [IDENTIFIANT_12] et [PERSONNE_1].",
])
def test_identifier_code_exclusions_stay(engine, text):
    assert _masked(engine, text) == text


def test_url_path_keeps_its_domain_and_masks_only_a_code_segment(engine):
    out = _masked(engine, "Voir https://www.exemple.fr/particuliers/F1234 et exemple.fr/dossiers/CLT-204518 ici.")
    assert out == "Voir https://www.exemple.fr/particuliers/F1234 et exemple.fr/dossiers/[IDENTIFIANT_1] ici.", out


def test_digit_anchored_tokens_match_a_full_scan():
    # Le détecteur ne visite que les jetons qui portent un chiffre : mêmes jetons qu'un `finditer` complet.
    # The detector only visits tokens holding a digit: the same tokens as a full `finditer`.
    rng = random.Random(102)
    for _ in range(3000):
        text = "".join(rng.choice("aB1.-_/ Xyé@Z9") for _ in range(rng.randint(0, 24)))
        full = [m.span() for m in codes._TOKEN.finditer(text) if codes._DIGIT.search(m.group())]
        anchored, pos = [], 0
        while (digit := codes._DIGIT.search(text, pos)) is not None:
            m = codes._TOKEN.match(text, codes._token_start(text, digit.start()))
            anchored.append(m.span())
            pos = m.end()
        assert anchored == full, text


def test_pure_digit_tokens_are_never_codes():
    assert not is_code("2024123456")
    assert not is_code("AB12")  # moins de 6 caractères / fewer than 6 characters
    assert is_code("AB1234")


@pytest.mark.parametrize("text, code", [
    ("facture FA-2024-00123 jointe", "FA-2024-00123"),
    ("commande CMD-2024-000123 expédiée", "CMD-2024-000123"),
    ("réf produit SKU-ALPHA-0042 en stock", "SKU-ALPHA-0042"),
    ("lot BATCH-OPS-2026-042 livré", "BATCH-OPS-2026-042"),
    ("devis DEV-778812 signé", "DEV-778812"),
])
def test_every_code_is_masked_whatever_its_prefix(engine, text, code):
    # Choix du propriétaire : aucun indice métier ni liste de préfixes ne garde un code ; une organisation garde
    # les siens par ses règles « keep ». Owner's choice: no business cue or prefix list keeps a code.
    out = _masked(engine, text)
    assert code not in out and "[IDENTIFIANT_1]" in out, out


def test_client_and_order_codes_are_both_masked(engine):
    out = _masked(engine, "client CLT-2024-0012 (commande CMD-2024-000123)")
    assert out == "client [IDENTIFIANT_1] (commande [IDENTIFIANT_2])", out


# --- Règles « keep » de l'organisation : elles l'emportent / the organisation's keep rules win ---------------------

_SKU_RULES = {"rules": [{"label": "SKU", "pattern": "SKU-[0-9]{6}", "action": "keep"}]}


@pytest.fixture(scope="module", params=_ENGINES)
def keeping(request) -> Anonymizer:
    from gdprguardian.custom import parse_rules
    anonymizer = Anonymizer(countries=("FR",), native=request.param, explain=True, rules=parse_rules(_SKU_RULES))
    assert anonymizer.native == request.param
    return anonymizer


def test_keep_rule_wins_over_the_code_rule(keeping):
    out = keeping.anonymize("Article SKU-123456 pour le client CLT-204518.").text
    assert out == "Article SKU-123456 pour le client [IDENTIFIANT_1].", out


def test_keep_rule_wins_over_value_propagation(keeping):
    # « sku123456 » (hors motif) est masqué ; sa valeur ne se propage pas dans la zone gardée « SKU-123456 ».
    # "sku123456" (outside the pattern) is masked; its value never propagates into the kept zone.
    out = keeping.anonymize("Code sku123456 noté. Article SKU-123456 en stock.").text
    assert out == "Code [IDENTIFIANT_1] noté. Article SKU-123456 en stock.", out
    explain = keeping.anonymize("Article SKU-123456 en stock.").report["explain"]
    assert explain == [{"kept": "IDENTIFIANT", "rule": "CUSTOM_1_SKU", "reason": "keep_rule", "count": 1}], explain


# --- Longues suites de chiffres / long digit runs (ID_LONG_NUMBER) -------------------------------------------------


@pytest.mark.parametrize("text, run", [
    ("Référence 20240012345 transmise.", "20240012345"),
    ("voir 98765432 au registre", "98765432"),
])
def test_bare_long_digit_runs_are_masked(engine, text, run):
    out = _masked(engine, text)
    assert run not in out and "[IDENTIFIANT_1]" in out, out
    assert _reasons(engine, text) == {"ID_LONG_NUMBER": "long_number"}


@pytest.mark.parametrize("text", [
    "Un budget de 12500000 € voté.",
    "Montant 12500000,50 réglé.",
    "Capital : 15000000 EUR.",
    "Fichier daté 20240315 archivé.",
    "Horodatage 20240315143000 relevé.",
    "Période 2023-2024 close, le 12.345.678 inchangé.",
    "Un nombre court 1234567 reste.",
    "Voir [IDENTIFIANT_12].",
    "Code CPV : 37400000 / Code nuts : FRK26",
    "Codes CPV : 45000000, 45231110 publiés.",
    "Annonce publiée au BODACC A n° 20260169 du 4 septembre.",
])
def test_long_digit_run_exclusions_stay(engine, text):
    assert _masked(engine, text) == text


@pytest.mark.parametrize("text, number", [
    ("ticket 4471 ouvert", "4471"),
    ("commande n° 20512 expédiée", "20512"),
    ("facture 88123 réglée", "88123"),
    ("salarié : 7781 absent", "7781"),
    ("compte utilisateur 55021 bloqué", "55021"),
    ("n° 99812 enregistré", "99812"),
])
def test_number_after_a_label_is_masked(engine, text, number):
    out = _masked(engine, text)
    assert number not in out and "[IDENTIFIANT_1]" in out, out
    rule = "FR_LABELLED_NUMBER_START" if text.startswith("n°") else "FR_LABELLED_NUMBER"
    assert _reasons(engine, text) == {rule: "keyword"}


@pytest.mark.parametrize("text", [
    "facture 1500 € réglée",
    "commande 1234,56 payée",
    "décret n° 2019-1234 publié",
    "le ticket 12 est clos",
    "Annonce n° 3151 du bulletin",
    "Lot n° 2306 : voirie",
])
def test_number_after_a_label_lookalikes_stay(engine, text):
    assert _masked(engine, text) == text


def test_identifier_code_reason(engine):
    assert _reasons(engine, "Référence TCK022609 transmise.") == {"ID_CODE": "identifier_code"}


@pytest.mark.parametrize("text, kept", [
    ("dossier 696936 en cours", "696936"),
    ("incident 20240012 clos", "20240012"),
    ("n° client 4471203 vérifié", "4471203"),
])
def test_bare_number_after_a_case_label_is_masked(engine, text, kept):
    out = _masked(engine, text)
    assert kept not in out and "[IDENTIFIANT_1]" in out, out


def test_matricule_unchanged(engine):
    assert _masked(engine, "matricule 008030") == "matricule [IDENTIFIANT_1]"


def test_codes_and_plates_have_uppercase_skeleton_values():
    assert fr.contextual_id("clt-204518") == "CLT204518"
    assert fr.contextual_id("CLT 204518") == "CLT204518"
    assert fr.siv_plate("ab-123-cd") == "AB123CD"


def test_same_code_written_twice_shares_one_tag(engine):
    out = _masked(engine, "Ticket TCK022609 ouvert ; rappel du TCK022609 demain.")
    assert out == "Ticket [IDENTIFIANT_1] ouvert ; rappel du [IDENTIFIANT_1] demain.", out


# --- Item 5 : identités en ligne / online identities ---------------------------------------------------------------


@pytest.mark.parametrize("text, secret", [
    ("Awa Mallet (@awa.m) a répondu.", "awa.m"),
    ("Merci à @ine_14 pour le signalement.", "ine_14"),
    ("connu sous l'alias « Tigrou44 » sur le forum", "Tigrou44"),
    ("son pseudo : lune_noire", "lune_noire"),
    ("journal : user=vasseurf refusé", "vasseurf"),
    ("identifiant de connexion : nadege.kerbrat", "nadege.kerbrat"),
    ("login: jdupont42 bloqué", "jdupont42"),
])
def test_online_identities_are_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out and "[PSEUDO_" in out, out


@pytest.mark.parametrize("text", [
    "« Je viens », dit-il.",
    "Il a dit « oui ».",
    "Le pseudo de l'utilisateur est libre.",
    "uid=1001 sur le serveur",
])
def test_online_identity_lookalikes_stay(engine, text):
    assert _masked(engine, text) == text


def test_pseudonym_field_of_a_notice_stays_with_the_name_detector(engine):
    # Le champ en tête de ligne reste au détecteur de noms, qui propage la valeur / the line-start field stays with
    # the name detector, which propagates the value.
    text = "Nom : Testix\nPrénom : Jean\nPseudonyme : TESTOFLAMME\nNom commercial : TESTOFLAMME\n"
    out = _masked(engine, text)
    assert "TESTOFLAMME" not in out and "[PSEUDO_" not in out, out


def test_email_stays_an_email(engine):
    out = _masked(engine, "Écrire à jean@exemple.fr ou login: jean@exemple.fr")
    assert out == "Écrire à [EMAIL_1] ou login: [EMAIL_1]", out


def test_handle_label_and_reasons(engine):
    reasons = _reasons(engine, "Merci @ine_14 ; user=vasseurf")
    assert reasons == {"HANDLE": "format", "LOGIN": "keyword"}, reasons


# --- Item 7 : téléphones / phones ----------------------------------------------------------------------------------


@pytest.mark.parametrize("text, secret", [
    ("sms sent to=0317495060 ok", "0317495060"),
    ("joindre le (+33) 7 10 02 19 76 demain", "10 02"),
    ("ou le +33 701 20 01 57 après 18h", "701 20"),
    ("ou le (0033) 6 12 34 56 78", "12 34"),
    ("rappeler le 06 xx xx 22 67 svp", "22 67"),
    ("rappeler le 06.XX.XX.22.67 svp", "22.67"),
    ("le numéro finissant par 59 65 est bloqué", "59 65"),
    ("la ligne en …24 71 est coupée", "24 71"),
    ("son portable se terminant par 4471", "4471"),
])
def test_phone_forms_are_masked(engine, text, secret):
    out = _masked(engine, text)
    assert secret not in out and "[TEL_" in out, out


@pytest.mark.parametrize("text", [
    "le contrat finissant par 2026",
    "rappeler le 06 xx xx xx xx",
])
def test_phone_lookalikes_stay(engine, text):
    assert _masked(engine, text) == text


def test_phone_end_after_fin_du_numero_is_masked(engine):
    out = _masked(engine, "Une fiche abîmée garde la fin du numéro : 45 67. Rien d'autre.")
    assert "45 67" not in out and "[TEL_1]" in out, out


@pytest.mark.parametrize("text, secret", [
    ("Domicile : 4, allée des Saules, 99950 Combe-aux-Brumes, France.", ("99950", "Combe", "Brumes")),
    ("Il loge au 7 rue du Puits 99910 Haut-de-Lande.", ("99910", "Haut", "Lande")),
])
def test_unverified_postcode_and_town_after_a_street_are_masked(engine, text, secret):
    out = _masked(engine, text)
    assert not any(part in out for part in secret) and "[ADRESSE_1]" in out, out


def test_invalid_plan_number_is_a_long_number_not_a_phone(engine):
    # Hors plan de numérotation : pas un téléphone, mais une suite nue de 10 chiffres (ID_LONG_NUMBER).
    # Outside the numbering plan: not a phone, but a bare run of 10 digits.
    assert _masked(engine, "code 0012345678 refusé") == "code [IDENTIFIANT_1] refusé"


def test_phone_reasons(engine):
    reasons = _reasons(engine, "sms sent to=0317495060 ; le numéro finissant par 59 65")
    assert reasons == {"FR_PHONE_COMPACT": "phone_numbering_plan", "FR_PHONE_FRAGMENT": "phone_fragment"}, reasons


def test_bracketed_country_code_validates():
    assert fr.phone("(+33) 7 10 02 19 76") == "+33710021976"
    assert fr.phone("(0033) 6 12 34 56 78") == "+33612345678"


# --- Item 1 (valeurs canoniques) / canonical values ----------------------------------------------------------------


@pytest.mark.parametrize("candidate, value", [
    ("12 mars 1985", "1985-03-12"), ("1er août 1990", "1990-08-01"), ("3 Février 1975", "1975-02-03"),
    ("12/03/1985", "1985-03-12"), ("31 février 1985", None), ("12 mai", None),
])
def test_birth_dates_in_words_have_iso_values(candidate, value):
    assert intl.calendar_date(candidate) == value


def test_birth_date_in_words_and_digits_share_one_tag(engine):
    out = _masked(engine, "Né le 12 mars 1985 à Lyon. Date de naissance : 12/03/1985.")
    assert out.count("[DATE_NAISSANCE_1]") == 2, out


# --- Idempotence -----------------------------------------------------------------------------------------------------


def test_running_on_its_own_output_changes_nothing(engine):
    text = ("Ticket TCK022609 de @ine_14 (user=vasseurf), IP fe80::1%eth0, PHPSESSID=9b2c7d1e4f5a6b8c, "
            "tél 0317495060, rappeler le 06 xx xx 22 67.")
    once = _masked(engine, text)
    assert _masked(engine, once) == once
