"""Pack IT : validateurs (oracle python-stdnum, en test seulement), mode auto et anonymisation de bout en bout.

IT pack: validators (python-stdnum oracle, test-only, LGPL, never shipped), auto mode and end-to-end runs.
"""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.it import codicefiscale as std_cf
from stdnum.it import iva as std_iva

from gdprguardian import Anonymizer
from gdprguardian.packs import load_pack
from gdprguardian.validators import it
from gdprguardian.validators.checksums import luhn_ok

from . import FRENCH_DOCUMENT

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LETTER = (
    "Gentile Sig. Rossi,\n"
    "le confermiamo i dati: codice fiscale RSSMRA80A01H501U, carta d'identità CA00000AA.\n"
    "Cellulare 333 123 4567, tel. 06 1234 5678.\n"
    "Il codice fiscale rssmra80a01h501u è stato verificato.\n"
)


@pytest.fixture(scope="module")
def anonymizer_it() -> Anonymizer:
    return Anonymizer(countries=("IT",))


# --- Codice fiscale ---------------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "canonical"), [
    ("RSSMRA80A01H501U", "RSSMRA80A01H501U"),
    ("RCCMNL83S18D969H", "RCCMNL83S18D969H"),
    ("RCCMNL83S18D96VW", "RCCMNL83S18D96VW"),   # omocodia, une substitution / one substitution
    ("RCCMNLUPSMUDVSVO", "RCCMNLUPSMUDVSVO"),   # omocodia complète / all seven substitutions
    ("rssmra80a01h501u", "RSSMRA80A01H501U"),
    ("RSS MRA 80A01 H501U", "RSSMRA80A01H501U"),
])
def test_codice_fiscale_examples(value, canonical):
    assert it.codice_fiscale(value) == canonical


@pytest.mark.parametrize("value", [
    "RSSMRA80A01H501A",  # mauvaise clé / wrong check letter
    "RSSMRA80F01H501U",  # mois F inexistant / no month F
    "RSSMRA80A32H501U",  # jour 32 / day 32
    "RSSMRA80B30H501U",  # 30 février / 30 February
    "RSSMRA80A01H501",   # 15 caractères / 15 characters
])
def test_codice_fiscale_rejections(value):
    assert it.codice_fiscale(value) is None


@st.composite
def codici_fiscali(draw) -> str:
    """Codes structurés valides, omocodia comprise ; clé calculée par l'oracle stdnum."""
    names = draw(st.text(alphabet=LETTERS, min_size=6, max_size=6))
    year, month = draw(st.integers(0, 99)), draw(st.sampled_from("ABCDEHLMPRST"))
    day = draw(st.integers(1, 28)) + draw(st.sampled_from((0, 40)))
    town = draw(st.sampled_from(LETTERS)) + f"{draw(st.integers(0, 999)):03d}"
    chars = list(f"{names}{year:02d}{month}{day:02d}{town}")
    for position in (14, 13, 12, 10, 9, 7, 6)[:draw(st.integers(0, 7))]:
        chars[position] = "LMNPQRSTUV"[int(chars[position])]
    body = "".join(chars)
    return body + std_cf.calc_check_digit(body)


@settings(max_examples=400)
@given(codici_fiscali())
def test_codice_fiscale_matches_stdnum(value):
    assert std_cf.is_valid(value)
    assert it.codice_fiscale(value) == value
    wrong = value[:15] + LETTERS[(LETTERS.index(value[15]) + 1) % 26]
    assert it.codice_fiscale(wrong) is None and not std_cf.is_valid(wrong)


# --- Partita IVA -------------------------------------------------------------------------------------


def test_partita_iva_examples():
    assert it.partita_iva("00743110157") == "00743110157"
    assert it.partita_iva("00743110158") is None
    assert it.partita_iva("00000000000") is None
    assert it.vat("IT 00743110157") == "IT00743110157"


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=11, max_size=11))
def test_partita_iva_matches_stdnum(value):
    ours = it.partita_iva(value) is not None
    if value[0] in "89":
        # Codes fiscaux d'associations : pas de code bureau, nous acceptons plus / we accept more.
        assert ours or not std_iva.is_valid(value)
    else:
        assert ours == std_iva.is_valid(value)


def test_association_tax_code_without_office_code():
    # 8… : code fiscal d'association, « 500 » n'est pas un code bureau / "500" is no office code.
    value = next(f"8000000500{c}" for c in "0123456789" if it.partita_iva(f"8000000500{c}"))
    assert not std_iva.is_valid(value)
    company = next(f"1000000500{c}" for c in "0123456789" if luhn_ok(f"1000000500{c}"))
    assert it.partita_iva(company) is None


# --- Téléphone / phone ---------------------------------------------------------------------------------


def test_phone_numbers():
    assert it.phone("06 1234 5678") == "+390612345678"
    assert it.phone("02-12345678") == "+390212345678"
    assert it.phone("333 123 4567") == "+393331234567"
    assert it.phone_mobile("333 123 4567") == "+393331234567"
    assert it.phone_mobile("06 1234 5678") is None
    assert it.phone("303 123 4567") is None
    assert it.phone("0012345678") is None


# --- Pack et moteur / pack and engine --------------------------------------------------------------


def test_pack_is_well_formed():
    pack = load_pack("IT")
    assert pack.country == "IT" and pack.locale["phone_codes"] == ["39"]
    for recognizer in pack.recognizers:
        assert not re.search(r"(?<!\\)[+*]", recognizer.regex.pattern), recognizer.id
        assert recognizer.tier == "A" or recognizer.contexts, recognizer.id


def test_letter_is_anonymized(anonymizer_it):
    result = anonymizer_it.anonymize(LETTER)
    for secret in ("RSSMRA80A01H501U", "rssmra80a01h501u", "CA00000AA", "333 123 4567", "06 1234 5678"):
        assert secret not in result.text
        assert secret not in str(result.report)
    for placeholder in ("[CODICE_FISCALE_1]", "[CNI_1]", "[TEL_1]", "[TEL_2]"):
        assert placeholder in result.text
    assert result.text.count("[CODICE_FISCALE_1]") == 2 and "[CODICE_FISCALE_2]" not in result.text


def test_auto_mode_activates_italy(anonymizer):
    analysis = anonymizer.analyze(LETTER)
    assert "IT" in analysis.countries
    assert not {"DE", "ES", "NL", "PT"} & set(analysis.countries)
    assert "[CODICE_FISCALE_1]" in anonymizer.anonymize(LETTER).text


def test_french_document_does_not_activate_italy(anonymizer):
    # Pièges : « cf. », « Cie », « cap », « patente », « CIE », « IVA », « P.I. », « tél. ».
    text = ("Cf. annexe 2 : Dupont & Cie garde le cap. Votre patente et votre CIE sont à jour. "
            "Taux d'IVA, P.I. de la société. Tél. 01 23 45 67 89. Numéro de la carte d'identité : 123.")
    assert "IT" not in anonymizer.analyze(text).countries
    assert "IT" not in anonymizer.analyze(FRENCH_DOCUMENT).countries


def test_weak_tier_and_company_policy(anonymizer_it):
    # 1.0.2 : sans contexte ce n'est pas une P.IVA, mais une suite nue de 8 chiffres ou plus est un identifiant
    # générique. Without context no P.IVA, but a bare run of 8+ digits is a generic identifier.
    assert anonymizer_it.anonymize("Ordine 00743110157 spedito.").text == "Ordine [IDENTIFIANT_1] spedito."
    assert "00743110157" in anonymizer_it.anonymize("Rossi S.p.A., P.IVA 00743110157").text
    sole = anonymizer_it.anonymize("Mario Rossi, ditta individuale, P.IVA 00743110157").text
    assert "00743110157" not in sole
    masked = Anonymizer(countries=("IT",), company_ids="mask").anonymize("Partita IVA: IT00743110157").text
    assert "00743110157" not in masked


def test_context_only_documents_and_dates(anonymizer_it):
    # 1.0.2 : pas une carte d'identité sans contexte, mais tout code est masqué / no ID card, but every code is masked.
    assert anonymizer_it.anonymize("Codice prodotto CA00000AA").text == "Codice prodotto [IDENTIFIANT_1]"
    text = "Riunione del 06-12-2024 alle 10, numero di telefono 06 1234 5678."
    assert anonymizer_it.anonymize(text).text == "Riunione del 06-12-2024 alle 10, numero di telefono [TEL_1]."


@pytest.mark.parametrize(("text", "expected"), [
    ("Codice fiscale: Rssmra80a01h501u", "Codice fiscale: [CODICE_FISCALE_1]"),  # majuscule de Word / Word caps
    ("tel. 06 1234 5678 10 interno", "tel. [TEL_1] 10 interno"),
    ("Tel. 0471 123456", "Tel. [TEL_1]"),
    ("Cell. (personale) 345 678 901", "Cell. (personale) [TEL_1]"),
    ("Contattare il 333-123-4567 per informazioni", "Contattare il [TEL_1] per informazioni"),
    # Mobile sans libellé : seule la forme à 10 chiffres est de niveau A / unlabelled: only 10 digits is tier A.
    ("Totale 345 678 901 pezzi", "Totale 345 678 901 pezzi"),
])
def test_phone_and_code_layouts(anonymizer_it, text, expected):
    assert anonymizer_it.anonymize(text).text == expected


def test_french_document_with_an_italian_phone(anonymizer):
    # Un +39 active l'Italie : les montants et le SIREN au format 3-3-3 ne deviennent pas des téléphones.
    # A +39 number activates Italy: 3-3-3 amounts and the SIREN must not become phone numbers.
    text = "Société ACME, tél. +39 02 1234 5678. Capital social de 350 000 000 euros, SIREN 332 829 320."
    result = anonymizer.anonymize(text)
    assert "IT" in result.analysis.countries
    assert "350 000 000 euros" in result.text and "332 829 320" in result.text
    assert "+39 02 1234 5678" not in result.text


def test_moroccan_patente_does_not_activate_italy(anonymizer):
    # « Patente n° » (taxe professionnelle) figure sur toutes les factures marocaines / on every Moroccan invoice.
    text = "Patente n° 12345678, IF 1234567, RC 12345, ICE 001234567000012. Tél. 0522 123456."
    assert "IT" not in anonymizer.analyze(text).countries


def test_header_lexicon_has_no_ambiguous_words():
    # Lexique commun à tous les packs en mode auto : « CF » (cash-flow), « via » (« Ship via »).
    # Lexicon shared by every pack in auto mode: "CF" (cash flow), "via" ("Ship via").
    words = {word for words in load_pack("IT").headers.values() for word in words}
    assert not {"cf", "c.f.", "via"} & words


@settings(max_examples=300)
@given(st.text(alphabet="0123456789ABHLMRSTUVaı .-/", max_size=18))
def test_validators_never_raise(text):
    for validator in (it.codice_fiscale, it.partita_iva, it.vat, it.phone, it.phone_mobile):
        result = validator(text)
        assert result is None or isinstance(result, str)
