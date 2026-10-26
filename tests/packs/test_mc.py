"""Pack Monaco : validateurs, mode auto, anonymisation de bout en bout.

Monaco pack: validators (python-stdnum as a test-only oracle, LGPL, never shipped), auto-mode activation,
end-to-end anonymisation.
"""

from __future__ import annotations

from time import perf_counter

import phonenumbers
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.mc import tva as std_tva

from gdprguardian import Anonymizer
from gdprguardian.packs import load_pack
from gdprguardian.validators import mc

from . import FRENCH_DOCUMENT, GENERIC_HEADERS, foreign_header_conflicts


def french_vat_key(body9: str) -> int:
    return (12 + 3 * (int(body9) % 97)) % 97


# --- TVA / VAT ---


@pytest.mark.parametrize(("value", "expected"), [
    ("FR53 000 004 605", "FR53000004605"),
    ("FR53000004605", "FR53000004605"),
    ("53 0000 04605", "FR53000004605"),
    ("FR 61 954 506 077", None),          # numéro français, pas monégasque / French, not Monaco
    ("FR54 000 004 605", None),
])
def test_tva_examples(value, expected):
    assert mc.tva(value) == expected
    assert std_tva.is_valid(value) == (expected is not None)


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=6, max_size=6), st.integers(0, 99), st.booleans())
def test_tva_agrees_with_stdnum(serial, key, fix_key):
    body = "000" + serial
    value = f"FR{french_vat_key(body) if fix_key else key:02d}{body}"
    assert (mc.tva(value) is not None) == std_tva.is_valid(value)


# --- RCI et téléphone / RCI and phone ---


@pytest.mark.parametrize(("value", "expected"), [
    ("99 S 03847", "99S03847"), ("76S01561", "76S01561"), ("76 SC 01561", "76SC01561"), ("12 P 00042", "12P00042"),
    ("99 X 03847", None), ("99 S 3847", None), ("S 03847", None),
])
def test_rci(value, expected):
    assert mc.rci(value) == expected


@pytest.mark.parametrize(("value", "expected"), [
    ("93 15 20 00", "+37793152000"),
    ("+377 93 15 20 00", "+37793152000"),
    ("+377 6 12 34 56 78", "+377612345678"),
    ("00377 44 12 34 56", "+37744123456"),
    ("+33 6 12 34 56 78", None),
    ("13 15 20 00", None),
])
def test_phone(value, expected):
    assert mc.phone(value) == expected


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=8, max_size=9))
def test_phone_accepts_every_number_valid_for_libphonenumber(national):
    # Rappel d'abord, et même forme E.164 que libphonenumber (qui retire aussi le 0 de tête).
    # Recall first, with libphonenumber's own E.164 form (it drops the trunk 0 as well).
    number = phonenumbers.parse("+377" + national)
    if phonenumbers.is_valid_number(number):
        assert mc.phone(national) == phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


# --- Mode auto / auto mode ---


def test_purely_french_document_does_not_activate_monaco(anonymizer):
    # « RCI Banque », « Grand Prix de Monaco » : aucun indice monégasque.
    assert "MC" not in anonymizer.analyze(FRENCH_DOCUMENT).countries


@pytest.mark.parametrize(("text", "reason"), [
    ("Contact : +377 93 15 20 00", "phone:+377"),
    ("Société anonyme monégasque au capital de 150 000 euros", "keywords:1"),
    ("Principauté de Monaco", "keywords:1"),
])
def test_monaco_evidence_activates_the_pack(anonymizer, text, reason):
    analysis = anonymizer.analyze(text)
    assert "MC" in analysis.countries
    assert reason in analysis.country_reasons["MC"]


# --- Bout en bout / end to end ---


LETTER = ("Principauté de Monaco. M. Louis Rossi, commerçant, RCI 12 P 00042, tél. 93 15 20 00 "
          "(ou +377 93 15 20 00), 7 avenue de la Costa, MC 98000 Monaco.")
LETTER_SECRETS = ("12 P 00042", "93 15 20 00")


def test_monaco_letter_is_fully_anonymised():
    result = Anonymizer(countries="MC,FR").anonymize(LETTER)
    for secret in LETTER_SECRETS:
        assert secret not in result.text
        assert secret not in repr(result.report)
    # National et international : même numéro, même balise / national and international: same placeholder.
    assert result.text.count("[TEL_1]") == 2
    assert "RCI [RCI_1]" in result.text


def test_principality_postcode_is_not_personal():
    # 98000 couvre toute la Principauté : le masquer ne cacherait rien / covers the whole principality.
    assert Anonymizer(countries="MC").anonymize("MC 98000 Monaco").text == "MC 98000 Monaco"


def test_auto_mode_anonymises_the_monaco_letter(anonymizer):
    result = anonymizer.anonymize(LETTER)
    assert "MC" in result.report["countries"]
    assert not [secret for secret in LETTER_SECRETS if secret in result.text]


def test_company_identifiers_follow_the_company_policy():
    text = ("ACME S.A.M., inscrite au Répertoire du Commerce et de l'Industrie sous le numéro 99 S 03847, "
            "TVA FR53 000 004 605.")
    assert Anonymizer(countries="MC").anonymize(text).text == text
    masked = Anonymizer(countries="MC", company_ids="mask").anonymize(text).text
    assert masked.endswith("sous le numéro [RCI_1], TVA [TVA_1].")


def test_rci_banque_is_not_an_rci_number():
    text = "Financement RCI Banque, contrat 2024 S 12345."
    assert Anonymizer(countries="MC").anonymize(text).text == text


def test_identifier_spelling_variants():
    masked = Anonymizer(countries="MC", company_ids="mask")
    assert masked.anonymize("R. C. I. 99 S 03847").text == "R. C. I. [RCI_1]"
    assert masked.anonymize("tva fr53 000 004 605").text == "tva [TVA_1]"


def test_header_lexicon_claims_no_foreign_column():
    headers = {word for words in load_pack("MC").headers.values() for word in words}
    assert not headers & GENERIC_HEADERS
    assert foreign_header_conflicts("MC") == {}


@pytest.mark.parametrize(("unit", "repeat"), [("9", 100_000), ("93 ", 35_000), ("RCI de Monaco n° ", 6_000),
                                              ("Répertoire du Commerce et de l'Industrie ", 2_500),
                                              ("FR53 000 ", 12_000)])
def test_hostile_inputs_stay_linear(unit, repeat):
    a = Anonymizer(countries="MC")
    t0 = perf_counter()
    a.analyze(unit * repeat)
    assert perf_counter() - t0 < 5.0


def test_fixed_phone_needs_context():
    a = Anonymizer(countries="MC,FR")
    assert a.anonymize("Lot 93 15 20 00.").text == "Lot 93 15 20 00."
    assert a.anonymize("Standard : 93 15 20 00.").text == "Standard : [TEL_1]."
