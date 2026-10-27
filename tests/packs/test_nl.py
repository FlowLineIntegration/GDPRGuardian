"""Pack NL : validateurs (oracle python-stdnum, en test seulement), mode auto et anonymisation de bout en bout.

NL pack: validators (python-stdnum oracle, test-only, LGPL, never shipped), auto mode and end-to-end runs.
"""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.nl import bsn as std_bsn
from stdnum.nl import btw as std_btw
from stdnum.nl import identiteitskaartnummer as std_document
from stdnum.nl import postcode as std_postcode

from gdprguardian import Anonymizer
from gdprguardian.packs import load_pack
from gdprguardian.validators import nl

from . import DUTCH_DOCUMENT, FRENCH_DOCUMENT

LETTER = (
    "Geachte heer De Vries,\n"
    "Uw burgerservicenummer 1234.56.782 en uw paspoort XR1001R58 zijn gecontroleerd.\n"
    "Woonadres: Kerkstraat 12, 1234 AB Amsterdam.\n"
    "Mobiel 06-12345678, tel. (020) 123 4567.\n"
    "Vermeld altijd uw BSN 123456782.\n"
)


@pytest.fixture(scope="module")
def anonymizer_nl() -> Anonymizer:
    return Anonymizer(countries=("NL",))


# --- BSN, btw-id ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "canonical"), [
    ("123456782", "123456782"), ("1234.56.782", "123456782"), ("111 222 333", "111222333"),
    ("12345672", "012345672"),  # 0 initial retiré par Excel / leading zero dropped by Excel
])
def test_bsn_examples(value, canonical):
    assert nl.bsn(value) == canonical


@pytest.mark.parametrize("value", ["111222334", "000000000", "1234567", "1234567890"])
def test_bsn_rejections(value):
    assert nl.bsn(value) is None


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=8, max_size=9))
def test_bsn_matches_stdnum(value):
    assert (nl.bsn(value) is not None) == std_bsn.is_valid(value)


@pytest.mark.parametrize("value", ["NL002455799B11", "NL004495445B01", "NL 0044.95.445 B01"])
def test_btw_examples(value):
    assert nl.btw(value) == re.sub(r"[ .]", "", value)


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9), st.text(alphabet="0123456789", min_size=2,
                                                                       max_size=2))
def test_btw_matches_stdnum(digits, suffix):
    value = f"NL{digits}B{suffix}"
    assert (nl.btw(value) is not None) == std_btw.is_valid(value)
    # Partition : eenmanszaak (MOD 97-10, depuis 2020) ou RSIN (11-proef), jamais les deux / never both.
    assert (nl.btw_person(value) is not None) + (nl.btw_company(value) is not None) == (nl.btw(value) is not None)


def test_btw_holder():
    assert nl.btw_person("NL002455799B11") == "NL002455799B11"   # btw-id d'eenmanszaak / sole trader's
    assert nl.btw_company("NL002455799B11") is None
    assert nl.btw_company("NL004495445B01") == "NL004495445B01"  # RSIN d'une B.V. / a B.V.'s RSIN
    assert nl.btw_person("NL004495445B01") is None


# --- Documents, postcode, téléphone / documents, postcode, phone --------------------------------------


@settings(max_examples=300)
@given(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=9, max_size=9))
def test_document_number_matches_stdnum(value):
    assert (nl.document_number(value) is not None) == std_document.is_valid(value)


@pytest.mark.parametrize(("value", "canonical"), [("1234 AB", "1234 AB"), ("1234ab", "1234 AB"),
                                                  ("9999 ZZ", "9999 ZZ")])
def test_postcode_examples(value, canonical):
    assert nl.postcode(value) == canonical
    assert std_postcode.is_valid(value)


@pytest.mark.parametrize("value", ["0123 AB", "1234 SA", "1234 SD", "1234 SS", "1234 A1", "12345 AB"])
def test_postcode_rejections(value):
    assert nl.postcode(value) is None


def test_phone_numbers():
    assert nl.phone("020-1234567") == "+31201234567"
    assert nl.phone("(010) 123 45 67") == "+31101234567"
    assert nl.phone_mobile("06 1234 5678") == "+31612345678"
    assert nl.phone_mobile("020-1234567") is None
    assert nl.phone("0031201234567") is None
    assert nl.phone("06-1234567") is None


# --- Pack et moteur / pack and engine --------------------------------------------------------------


def test_pack_is_well_formed():
    pack = load_pack("NL")
    assert pack.country == "NL" and pack.locale["phone_codes"] == ["31"]
    for recognizer in pack.recognizers:
        assert not re.search(r"(?<!\\)[+*]", recognizer.regex.pattern), recognizer.id
        assert recognizer.tier == "A" or recognizer.contexts, recognizer.id


def test_letter_is_anonymized(anonymizer_nl):
    result = anonymizer_nl.anonymize(LETTER)
    for secret in ("1234.56.782", "123456782", "XR1001R58", "1234 AB", "06-12345678", "(020) 123 4567"):
        assert secret not in result.text
        assert secret not in str(result.report)
    for placeholder in ("[BSN_1]", "[PASSEPORT_1]", "[CODE_POSTAL_1]", "[TEL_1]", "[TEL_2]"):
        assert placeholder in result.text
    assert result.text.count("[BSN_1]") == 2 and "[BSN_2]" not in result.text


def test_auto_mode_activates_netherlands(anonymizer):
    analysis = anonymizer.analyze(LETTER)
    assert "NL" in analysis.countries
    assert not {"DE", "ES", "IT", "PT"} & set(analysis.countries)
    assert "[BSN_1]" in anonymizer.anonymize(LETTER).text


def test_french_and_english_documents_do_not_activate_netherlands(anonymizer):
    # Pièges : « BTW » (anglais familier), « postcode » (anglais), « adres » (polonais), « gsm » (belge).
    text = ("Bonjour, mon GSM est le 06 12 34 56 78. BTW, the postcode is SW1A 1AA. Adres: ul. Długa 1. "
            "Votre numéro de TVA et votre passeport sont à jour.")
    assert "NL" not in anonymizer.analyze(text).countries
    assert "NL" not in anonymizer.analyze(FRENCH_DOCUMENT).countries


def test_shared_dutch_reference_document(anonymizer):
    result = anonymizer.anonymize(DUTCH_DOCUMENT)
    assert "NL" in result.analysis.countries
    assert "111222333" not in result.text and "06 12345678" not in result.text


def test_weak_tier_needs_context(anonymizer_nl):
    # 1.0.2 : sans contexte ce n'est pas un BSN, mais une suite nue de 8 chiffres ou plus est un identifiant
    # générique. Without context no BSN, but a bare run of 8+ digits is a generic identifier.
    assert anonymizer_nl.anonymize("Factuur 123456782 betaald.").text == "Factuur [IDENTIFIANT_1] betaald."
    assert "123456782" not in Anonymizer(countries=("NL",), profile="strict").anonymize(
        "Factuur 123456782 betaald.").text
    assert "1234 AB" in anonymizer_nl.anonymize("Bestelling 1234 AB verzonden").text


def test_dates_are_not_phone_numbers(anonymizer_nl):
    text = "Afspraak op 06-12-2024 12:00, telefoon volgt."
    assert anonymizer_nl.anonymize(text).text == text


def test_company_ids_follow_policy(anonymizer_nl):
    text = "Bakkerij B.V., KvK-nummer 12345678, btw-nummer NL004495445B01."
    assert anonymizer_nl.anonymize(text).text == text
    sole = anonymizer_nl.anonymize("Jan Jansen, eenmanszaak, KvK-nummer 12345678, btw-nummer NL004495445B01.").text
    assert "12345678" not in sole and "NL004495445B01" not in sole


def test_sole_trader_btw_id_is_always_masked(anonymizer_nl):
    # Depuis 2020, un btw-id MOD 97-10 n'est attribué qu'à une eenmanszaak : donnée personnelle, sans indice.
    # Since 2020 a MOD 97-10 btw-id is only issued to a sole trader: personal data, no cue needed.
    assert anonymizer_nl.anonymize("Jan Jansen, btw-id NL002455799B11.").text == "Jan Jansen, btw-id [TVA_1]."


@pytest.mark.parametrize(("text", "expected"), [
    ("Adres: Kerkstraat 12, 1234 AB Amsterdam", "Adres: Kerkstraat 12, [CODE_POSTAL_1] Amsterdam"),
    ("Postcode: 1234 AB", "Postcode: [CODE_POSTAL_1]"),
    ("Bezoekadres: Kerkstraat 12, 1234 AB Amsterdam", "Bezoekadres: Kerkstraat 12, [CODE_POSTAL_1] Amsterdam"),
    ("Adres: Postbus 12345 AB", "Adres: Postbus 12345 AB"),
    ("Telefoon 020 1234567 10 uur", "Telefoon [TEL_1] 10 uur"),
    ("Tel. (020) 123 4567", "Tel. [TEL_1]"),
    ("Tel. (werk): 0111 123456", "Tel. (werk): [TEL_1]"),
])
def test_postcode_and_phone_layouts(anonymizer_nl, text, expected):
    assert anonymizer_nl.anonymize(text).text == expected


@settings(max_examples=300)
@given(st.text(alphabet="0123456789ABLNOSZaı .-", max_size=16))
def test_validators_never_raise(text):
    for validator in (nl.bsn, nl.btw, nl.btw_person, nl.btw_company, nl.kvk, nl.document_number, nl.postcode,
                      nl.phone, nl.phone_mobile):
        result = validator(text)
        assert result is None or isinstance(result, str)
