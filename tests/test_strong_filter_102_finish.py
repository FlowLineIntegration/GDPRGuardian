"""Filtre fort 1.0.2, finition : jumeau Rust du détecteur de codes et contrôle final de sortie.

Strong filter 1.0.2, finish: the Rust twin of the code detector (`ID_CODE`, `ID_LONG_NUMBER`, `SECRET_COOKIE`) and
the output self-check (`output_check`). Chaque cas tourne sur le noyau Rust (s'il est installé) et sur la référence
Python, qui doivent rendre le même texte et les mêmes zones. Every case runs on the Rust core (when installed) and on
the Python reference, which must give the same text and spans. Données fictives / fictitious data.
"""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer, _native
from gdprguardian.selfcheck import CHECK_REASON, output_check
from gdprguardian.types import Span

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]
_KEEP_SKU = {"rules": [{"label": "SKU", "pattern": "SKU-[0-9]{6}", "action": "keep"}]}


@pytest.fixture(scope="module", params=_ENGINES)
def engine(request) -> Anonymizer:
    anonymizer = Anonymizer(countries=("FR",), native=request.param)
    assert anonymizer.native == request.param
    return anonymizer


@pytest.fixture(scope="module", params=_ENGINES)
def keep_engine(request) -> Anonymizer:
    anonymizer = Anonymizer(countries=("FR",), native=request.param, rules=_KEEP_SKU)
    assert anonymizer.native == request.param
    return anonymizer


# --- Détecteur de codes (jumeau Rust) / code detector (Rust twin) ---------------------------------------------------


@pytest.mark.parametrize("text, secrets", [
    ("Client CLT-204518, ticket TCK022609, appel VOX-6940-AK84.", ["CLT-204518", "TCK022609", "VOX-6940-AK84"]),
    ("Voir https://portail.exemple.fr/dossiers/CLT-204518 pour la suite.", ["CLT-204518"]),
    ("Compteur 912345678 ; Débiteur 12345678 ; dossier 123456789.", ["912345678", "12345678", "123456789"]),
    ("Set-Cookie: sid=abcdef123456789; Path=/; Max-Age=31536000", ["abcdef123456789"]),
])
def test_codes_and_long_numbers_are_masked(engine, text, secrets):
    out = engine.anonymize(text).text
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("text, kept", [
    ("Montant 12500000 € ; 15000000 EUR ; 2500000,50 réglés.", ["12500000", "15000000", "2500000,50"]),
    ("Set-Cookie: sid=abcdef123456789; Path=/; Max-Age=31536000", ["Path=/", "Max-Age=31536000"]),
    ("Code CPV : 37400000 ; BODACC A n° 20260169 ; date 20260131.", ["37400000", "20260169", "20260131"]),
    ("Norme ISO 27001, COVID-19, article L1234-5, période T1-2024, à 14h30, écran 1920x1080.",
     ["ISO 27001", "COVID-19", "L1234-5", "T1-2024", "14h30", "1920x1080"]),
    ("Balise déjà produite : [IDENTIFIANT_12].", ["[IDENTIFIANT_12]"]),
])
def test_what_is_not_an_identifier_stays(engine, text, kept):
    out = engine.anonymize(text).text
    for word in kept:
        assert word in out, out


def test_keep_rule_wins_over_codes_and_the_self_check(keep_engine):
    text = "Produit SKU-123456 et client CLT-204518 ; réfSKU-123456 et réfCLT-204518."
    result = keep_engine.anonymize(text)
    assert result.text.count("SKU-123456") == 2, result.text
    assert "CLT-204518" not in result.text, result.text


@pytest.mark.skipif(not _native.available(), reason="noyau Rust absent / no Rust core")
@pytest.mark.parametrize("text", [
    "Client CLT-204518, ticket TCK022609 ; voir site.fr/a/B12345/c.d et AB12.Le dossier ; [IDENTIFIANT_3].",
    "Compteur 912345678 ; Débiteur 12345678 ; Ｆacteur 12345678 ; montant 12500000 € ; 1234567890,12.",
    "Code CPV : 37400000, 45000000 ; NAF n° 47110000 ; BODACC A n° 20260169 ; JORF n° 0123456789.",
    "SET-COOKIE: sid=abcdef123456789; Path=/; Max-Age=31536000\r\ncookie : uid = user-000123456 ; theme=dark",
    "réfCLT-204518 ; CLT-204518 ; Télé0612345678 ; Tél : 0612345678 ; éjean.dupont@exemple.fr",
    "BNPAFRPPXXX, DEUTDEFF500, AB12CD34, x9y8z7w6, 12x34x56, 3.14.159.26, 2026-10-26T14, H1N1, MP4, CO2.",
])
def test_rust_twin_matches_python(text):
    rust, python = Anonymizer(native=True), Anonymizer(native=False)
    left, right = rust.anonymize(text), python.anonymize(text)
    assert left.text == right.text
    key = lambda s: (s.start, s.end, s.source, s.value, s.reason)  # noqa: E731
    assert [key(s) for s in left.analysis.spans] == [key(s) for s in right.analysis.spans]


# --- Contrôle final de sortie / output self-check -------------------------------------------------------------------


def _phone(start: int, end: int, value: str = "612345678") -> Span:
    return Span(start, end, "PHONE", "PHONE", "FR_PHONE", 0.9, 80, value)


def test_self_check_masks_a_glued_occurrence_with_the_same_value():
    text = "Tél 0612345678 ; noté Télé0612345678."
    spans = output_check(text, text.lower(), [_phone(4, 14)])
    assert [(s.start, s.end, s.value, s.reason, s.source) for s in spans] == [
        (4, 14, "612345678", None, "FR_PHONE"),
        (26, 36, "612345678", CHECK_REASON, "output_check:FR_PHONE")]


@pytest.mark.parametrize("text", [
    "Tél 0612345678 ; compteur 90612345678.",   # au milieu d'un nombre / inside a number
    "Tél 0612345678 ; compteur 06123456789.",
    "Tél 0612345678.",                           # aucune autre occurrence / no other occurrence
])
def test_self_check_never_cuts_a_number(text):
    spans = output_check(text, text.lower(), [_phone(4, 14)])
    assert len(spans) == 1


def test_self_check_skips_existing_and_kept_spans():
    text = "Code AB-123456 ; ref AB-123456."
    source = Span(5, 14, "ID", "ID", "ID_CODE", 0.8, 50, "AB123456")
    kept = Span(21, 30, "ID", "SKU", "keep:SKU", 1.0, 99, None, False)
    assert output_check(text, text.lower(), [source, kept]) == [source, kept]


def test_self_check_folds_case_and_skips_short_or_plain_values():
    text = "Mail JEAN.DUPONT@EXEMPLE.FR ; relance éjean.dupont@exemple.fr ; nom Martin ; Martin."
    email = Span(5, 27, "EMAIL", "EMAIL", "INTL_EMAIL", 0.95, 80, "jean.dupont@exemple.fr")
    person = Span(68, 74, "PERSON", "PERSON", "FR_NAMES", 0.8, 60, "Martin")
    spans = output_check(text, text.lower(), [email, person])
    added = [s for s in spans if s.reason == CHECK_REASON]
    assert [(text[s.start:s.end], s.value) for s in added] == [("jean.dupont@exemple.fr", "jean.dupont@exemple.fr")]


@pytest.mark.parametrize("text, tag_text", [
    ("Tél : 0612345678 ; ancien numéro noté Télé0612345678 sur la fiche.", "Télé[TEL_1]"),
    ("Client CLT-204518 ; fiche réfCLT-204518 archivée.", "réf[IDENTIFIANT_1]"),
])
def test_self_check_in_the_engine(engine, text, tag_text):
    result = engine.anonymize(text)
    assert tag_text in result.text, result.text
    assert any(s.reason == CHECK_REASON for s in result.analysis.spans)


def test_self_check_reason_in_explain():
    result = Anonymizer(countries=("FR",), explain=True).anonymize("Client CLT-204518 ; fiche réfCLT-204518.")
    assert CHECK_REASON in str(result.report), result.report
