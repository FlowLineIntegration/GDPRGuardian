"""Pack Suisse : validateurs, mode auto, anonymisation de bout en bout.

Switzerland pack: validators (python-stdnum and phonenumbers as test-only oracles; stdnum is LGPL and never
shipped), auto-mode activation, end-to-end anonymisation.
"""

from __future__ import annotations

from time import perf_counter

import phonenumbers
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.ch import ssn as std_ssn
from stdnum.ch import uid as std_uid
from stdnum.ch import vat as std_vat

from gdprguardian import Anonymizer
from gdprguardian.packs import load_pack
from gdprguardian.validators import ch

from . import FRENCH_DOCUMENT, GENERIC_HEADERS, GERMAN_DOCUMENT, foreign_header_conflicts


def ean13_digit(payload12: str) -> int:
    """Clé EAN-13 : poids 1 et 3 alternés depuis la gauche / alternating weights 1 and 3 from the left."""
    total = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(payload12))
    return (10 - total % 10) % 10


# --- AVS / AHV ---


def test_avs_examples():
    assert ch.avs("756.9217.0769.85") == "7569217076985"
    assert ch.avs("7569217076985") == "7569217076985"
    assert ch.avs("756.9217.0769.84") is None
    assert ch.avs("757.9217.0769.85") is None   # préfixe pays 756 obligatoire / country prefix 756


def test_avs_accepts_hyphens_unlike_stdnum():
    # Différence assumée : stdnum ne retire que les espaces et les points / deliberate difference.
    assert ch.avs("756-9217-0769-85") == "7569217076985"
    assert not std_ssn.is_valid("756-9217-0769-85")


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9), st.integers(0, 9), st.booleans())
def test_avs_agrees_with_stdnum(random_part, digit, fix_key):
    payload = "756" + random_part
    value = payload + str(ean13_digit(payload) if fix_key else digit)
    assert (ch.avs(value) is not None) == std_ssn.is_valid(value)


# --- IDE / UID et TVA / business identifier and VAT ---


@pytest.mark.parametrize(("value", "expected"), [
    ("CHE-100.155.212", "CHE100155212"),
    ("CHE-107.787.577 IVA", "CHE107787577"),
    ("CHE-107.787.577 MWST", "CHE107787577"),
    ("CHE107787577TVA", "CHE107787577"),
    ("CHE-107.787.578 IVA", None),
    ("CHE-100.155.213", None),
])
def test_uid_examples(value, expected):
    assert ch.uid(value) == expected


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9), st.sampled_from(["", " MWST", " TVA", " IVA"]))
def test_uid_agrees_with_stdnum(digits, suffix):
    value = f"CHE-{digits[:3]}.{digits[3:6]}.{digits[6:]}{suffix}"
    oracle = std_vat if suffix else std_uid
    assert (ch.uid(value) is not None) == oracle.is_valid(value)


@settings(max_examples=200)
@given(st.text(alphabet="0123456789", min_size=8, max_size=8))
def test_uid_key_ten_is_never_issued(payload):
    weighted = sum(int(d) * w for d, w in zip(payload, (5, 4, 3, 2, 7, 6, 5, 4), strict=True))
    key = (11 - weighted % 11) % 11
    if key == 10:
        assert all(ch.uid(f"CHE{payload}{d}") is None for d in "0123456789")
    else:
        assert ch.uid(f"CHE{payload}{key}") == f"CHE{payload}{key}"


# --- Téléphone / phone ---


@pytest.mark.parametrize(("value", "expected"), [
    ("079 123 45 67", "+41791234567"),
    ("044 668 18 00", "+41446681800"),
    ("+41 (0)79 123 45 67", "+41791234567"),
    ("0041 22 345 67 89", "+41223456789"),
    ("012 345 67 89", None),
    ("079 123 45 6", None),
])
def test_phone(value, expected):
    assert ch.phone(value) == expected


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9))
def test_phone_accepts_every_number_valid_for_libphonenumber(national):
    number = phonenumbers.parse("+41" + national)
    if phonenumbers.is_valid_number(number):
        assert ch.phone("0" + national) == "+41" + national


# --- Mode auto / auto mode ---


def test_purely_french_document_does_not_activate_switzerland(anonymizer):
    # « AVS » (auxiliaire de vie scolaire), « IDE », « conseil fédéral » : aucun indice suisse.
    assert "CH" not in anonymizer.analyze(FRENCH_DOCUMENT).countries


def test_german_document_does_not_activate_switzerland(anonymizer):
    # « MwSt. », « UID-Nr. » (Autriche), « Sozialversicherungsnummer » : pas propres à la Suisse.
    assert "CH" not in anonymizer.analyze(GERMAN_DOCUMENT).countries


def test_liechtenstein_iban_does_not_activate_switzerland(anonymizer):
    assert "CH" not in anonymizer.analyze("IBAN LI21 0881 0000 2324 013A A").countries


@pytest.mark.parametrize("text", [
    # Offices fédéraux allemands nommés en français / German federal offices named in French.
    "L'Office fédéral des migrations et des réfugiés (BAMF) a transmis le dossier à l'OFII.",
    "Selon l'Office fédéral de la statistique allemand (Destatis), l'inflation recule.",
    "L'IDE de nuit a prévenu le médecin de garde.",
])
def test_lookalike_words_do_not_activate_switzerland(anonymizer, text):
    assert "CH" not in anonymizer.analyze(text).countries


@pytest.mark.parametrize(("text", "reason"), [
    ("Natel +41 79 123 45 67", "phone:+41"),
    ("IBAN CH93 0076 2011 6238 5295 7", "iban:CH"),
    ("Bitte AHV-Nummer angeben.", "keywords:1"),
    ("Confédération suisse — Office fédéral de la statistique", "keywords:1"),
])
def test_swiss_evidence_activates_the_pack(anonymizer, text, reason):
    analysis = anonymizer.analyze(text)
    assert "CH" in analysis.countries
    assert reason in analysis.country_reasons["CH"]


@pytest.mark.parametrize("text", ["Assurée : AVS 756.9217.0769.85.", "AVS : 756 9217 0769 85", "AVS: 756.9217.0769.85"])
def test_lone_avs_number_is_masked_in_auto_mode(anonymizer, text):
    # « AVS 756… » suffit : le sigle suivi du préfixe suisse / the acronym followed by the Swiss prefix is enough.
    result = anonymizer.anonymize(text)
    assert "CH" in result.report["countries"]
    assert "0769" not in result.text


# --- Bout en bout / end to end ---

LETTER = """\
Schweizerische Eidgenossenschaft — Ausgleichskasse
Frau Anna Keller, AHV-Nr. 756.9217.0769.85, alte AHV-Nummer 123.45.678.901.
Natel 079 123 45 67, Tel. 044 668 18 00, IBAN CH93 0076 2011 6238 5295 7.
Kontrollschild ZH 123 456. Adresse: Bahnhofstrasse 1, CH-8001 Zürich. Rückfragen: AHV 7569217076985.
"""


LETTER_SECRETS = ("756.9217.0769.85", "7569217076985", "123.45.678.901", "079 123 45 67", "044 668 18 00",
                  "CH93 0076 2011 6238 5295 7", "ZH 123 456", "CH-8001")


def test_swiss_letter_is_fully_anonymised():
    result = Anonymizer(countries="CH").anonymize(LETTER)
    text = result.text
    for secret in LETTER_SECRETS:
        assert secret not in text
        assert secret not in repr(result.report)
    assert text.count("[AVS_1]") == 2
    assert "[AVS_2]" in text
    for placeholder in ("[TEL_1]", "[TEL_2]", "[IBAN_1]", "[PLAQUE_1]", "[CODE_POSTAL_1]"):
        assert placeholder in text


def test_auto_mode_anonymises_the_swiss_letter(anonymizer):
    result = anonymizer.anonymize(LETTER)
    assert "CH" in result.report["countries"]
    assert not [secret for secret in LETTER_SECRETS if secret in result.text]


def test_uid_follows_the_company_policy():
    text = "Muster AG, CHE-107.787.577 MWST, UID CHE-107.787.577."
    assert Anonymizer(countries="CH").anonymize(text).text == text
    masked = Anonymizer(countries="CH", company_ids="mask")
    assert masked.anonymize(text).text == "Muster AG, [IDE_1] MWST, UID [IDE_1]."
    # Suffixe collé : il reste visible hors de la balise / glued suffix stays visible outside the placeholder.
    assert masked.anonymize("CHE-107.787.577MWST").text == "[IDE_1]MWST"
    sole = Anonymizer(countries="CH").anonymize("Hans Meier, Einzelfirma, CHE-107.787.577 MWST").text
    assert "107.787.577" not in sole


def test_context_only_identifiers_need_context():
    a = Anonymizer(countries="CH")
    assert a.anonymize("Version 123.45.678.901").text == "Version 123.45.678.901"
    assert a.anonymize("Kanton BE 12345, Seite 2").text == "Kanton BE 12345, Seite 2"
    assert a.anonymize("Kontrollschild BE 12345").text == "Kontrollschild [PLAQUE_1]"


@pytest.mark.parametrize("text", ["Kontrollschild ZH 123 456 789", "Plaque de contrôle FR 12 345 678 901"])
def test_plate_never_cuts_a_longer_number(text):
    # Couper « FR 12 345 » dans un numéro plus long laisserait la fin en clair / a cut would leave the tail visible.
    assert Anonymizer(countries="CH").analyze(text).spans == []


def test_plate_followed_by_a_date_is_still_masked():
    text = "Kontrollschild VD 123 456 12.03.2024"
    assert Anonymizer(countries="CH").anonymize(text).text == "Kontrollschild [PLAQUE_1] 12.03.2024"


def test_lowercase_uid_is_detected():
    masked = Anonymizer(countries="CH", company_ids="mask")
    assert masked.anonymize("UID che-107.787.577 mwst").text == "UID [IDE_1] mwst"


def test_swiss_grouping_is_not_mistaken_for_a_french_number():
    a = Anonymizer(countries="CH,FR")
    result = a.analyze("Tél. 01 23 45 67 89 et 021 345 67 89")
    assert [(s.source, s.value) for s in result.spans] == [("FR_PHONE", "+33123456789"),
                                                          ("CH_PHONE", "+41213456789")]


@pytest.mark.parametrize(("unit", "repeat"), [("7", 100_000), ("756 ", 25_000), ("CHE-", 25_000), ("che-", 25_000),
                                              ("Kontrollschild ZH 1 ", 5_000), ("Kontrollschild ZH 123 ", 5_000),
                                              ("079 ", 25_000)])
def test_hostile_inputs_stay_linear(unit, repeat):
    a = Anonymizer(countries="CH")
    t0 = perf_counter()
    a.analyze(unit * repeat)
    assert perf_counter() - t0 < 5.0


def test_labels():
    text = "AHV-Nr. 756.9217.0769.85"
    assert Anonymizer(countries="CH", neutral_labels=True).anonymize(text).text == "AHV-Nr. [ID_NATIONAL_1]"
    assert Anonymizer(countries="CH", label_language="en").anonymize(text).text == "AHV-Nr. [AHV_1]"


def test_header_lexicon_claims_no_foreign_column():
    # « Sozialversicherungsnummer » d'un classeur allemand ne doit pas devenir [AVS_1].
    # A German "Sozialversicherungsnummer" column must not become [AVS_1].
    headers = {word for words in load_pack("CH").headers.values() for word in words}
    assert not headers & GENERIC_HEADERS
    assert foreign_header_conflicts("CH") == {}
