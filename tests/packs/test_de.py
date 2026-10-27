"""Pack DE : validateurs (oracle python-stdnum, en test seulement), mode auto et anonymisation de bout en bout.

DE pack: validators (python-stdnum oracle, test-only, LGPL, never shipped), auto mode and end-to-end runs.
"""

from __future__ import annotations

import dataclasses
import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.de import idnr as std_idnr
from stdnum.de import stnr as std_stnr
from stdnum.de import vat as std_vat
from stdnum.iso7064 import mod_11_10

from gdprguardian import Anonymizer
from gdprguardian._text import fold
from gdprguardian.engine import DetectionContext
from gdprguardian.packs import load_pack
from gdprguardian.validators import de

from . import FRENCH_DOCUMENT, GERMAN_DOCUMENT

EU_PACKS = ("DE", "ES", "IT", "NL", "PT")
# Bornes gauches d'optimisation (voir de.toml), pas la borne fonctionnelle « (?<![0-9A-Za-z]) » seule ; la borne
# finale, elle, change volontairement le résultat (repli sur un candidat plus court). Left optimisation
# boundaries (see de.toml), not the functional lone "(?<![0-9A-Za-z])"; the final boundary deliberately changes
# the result (backing off to a shorter candidate).
_PREFILTER_BOUNDARY_RE = re.compile(r"\(\?<!\[0-9A-Za-z(?:\\\+)?\](?:\{2\}|\[0-9\]|[0-9])\)")
# Identifiants valides des cinq packs, collés à des chiffres, lettres et séparateurs par le test de propriété.
# Valid identifiers of the five packs, glued to digits, letters and separators by the property test.
_TOKENS = (
    "36 574 261 809", "15070649C103", "A123456780", "L01X00T471", "B072RRE2I55", "181/815/08155", "0171 1234567",
    "030 12345678", "12345678Z", "X1234567L", "B64717838", "281234567840", "612 345 678", "RSSMRA80A01H501U",
    "rssmra80a01h501u", "00743110157", "333 123 4567", "06 1234 5678", "CA00000AA", "123456782", "1234 AB",
    "XR1001R58", "06-12345678", "123456789", "501964843", "12347312896", "13201144 1 ZZ8", "1000-001",
    "912 345 678", "K1234567L", "PAA123456", "YA1234567", "AR1234567B", "C123456", "Tel. 030 12345678",
    "Tel. 06 1234 5678", "Tel. 020 123 4567", "NIF 123456789", "NIPC 501964843", "0", "1", "9", "12", " ", "-",
    ".", "/", "(", ")", "+", "A", "Z", "a", "é", "\n", "NISS ", "BI ", "NSS ", "Adres ", "Postcode ",
)

STEUER_ID = "36 574 261 809"
SV_NUMMER = "15 070649 C 103"
LETTER = (
    "Sehr geehrte Frau Schmidt,\n"
    f"Ihre Steuer-ID lautet {STEUER_ID}, Ihre Sozialversicherungsnummer {SV_NUMMER}.\n"
    "Krankenversichertennummer: A123456780. Personalausweis: L01X00T471.\n"
    "Führerschein B072RRE2I55, Steuernummer 181/815/08155.\n"
    "Tel.: 030 12345678, Handy: 0171 1234567.\n"
    "Zur Erinnerung: Steuer-ID 36574261809.\n"
)


@pytest.fixture(scope="module")
def anonymizer_de() -> Anonymizer:
    return Anonymizer(countries=("DE",))


def _valid_with_check(body: str, validator, alphabet: str = "0123456789") -> list[str]:
    return [body + c for c in alphabet if validator(body + c)]


# --- Steuer-ID ----------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["36574261809", "86095742719", "65929970489", "12345678911", "36 574 261 809"])
def test_steuer_id_examples(value):
    assert de.steuer_id(value) == value.replace(" ", "")
    assert std_idnr.is_valid(value)


@pytest.mark.parametrize("value", [
    "36574261890",  # mauvaise clé / wrong check digit
    "36554266806",  # deux chiffres répétés / two repeated digits
    "06574261809",  # zéro initial / leading zero
    "1234567890",   # 10 chiffres / 10 digits
    "11111111116",  # un chiffre 10 fois / one digit ten times
])
def test_steuer_id_rejections(value):
    assert de.steuer_id(value) is None


def test_steuer_id_three_in_a_row_is_stricter_than_stdnum():
    # BZSt, propriété 6e : jamais trois chiffres égaux consécutifs ; stdnum ne le vérifie pas.
    body = "1112345678"
    value = body + mod_11_10.calc_check_digit(body)
    assert std_idnr.is_valid(value) and de.steuer_id(value) is None
    spread = "1121345678"
    value = spread + mod_11_10.calc_check_digit(spread)
    assert std_idnr.is_valid(value) and de.steuer_id(value) == value


@st.composite
def idnr_bodies(draw) -> str:
    """Corps de 10 chiffres respectant la règle de répétition (doublon ou triplet), mélangés."""
    digits = draw(st.permutations("0123456789"))
    triple = draw(st.booleans())
    kept = list(digits[:8] if triple else digits[:9])
    repeated = draw(st.sampled_from(kept))
    body = draw(st.permutations([*kept, repeated, repeated] if triple else [*kept, repeated]))
    return "".join(body)


@settings(max_examples=400)
@given(idnr_bodies())
def test_steuer_id_matches_stdnum(body):
    value = body + mod_11_10.calc_check_digit(body)
    expected = std_idnr.is_valid(value) and re.search(r"(\d)\1\1", body) is None
    assert (de.steuer_id(value) is not None) == expected
    wrong = value[:-1] + str((int(value[-1]) + 1) % 10)
    assert de.steuer_id(wrong) is None


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=11, max_size=11))
def test_steuer_id_never_accepts_what_stdnum_rejects(value):
    if de.steuer_id(value) is not None:
        assert std_idnr.is_valid(value)


# --- USt-IdNr, Steuernummer -------------------------------------------------------------------


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9))
def test_vat_matches_stdnum(digits):
    value = "DE" + digits
    assert (de.ust_idnr(value) is not None) == std_vat.is_valid(value)


def test_vat_example():
    assert de.ust_idnr("DE 136 695 976") == "DE136695976"
    assert de.ust_idnr("DE136695978") is None


@pytest.mark.parametrize("value", [
    "93/815/08152", "181/815/08155", "21/815/08150", "048/815/08155", "013/815/08153", "133/8150/8159",
    "2893081508152", "9181081508155", "1121081508150", "3048081508155", "5133081508159", "4151081508156",
])
def test_steuernummer_wikipedia_table(value):
    # Exemples de la table par Land (de.wikipedia) ; stdnum ne contrôle que la forme / format only.
    assert de.steuernummer(value) == value.replace("/", "")
    assert std_stnr.is_valid(value)


@pytest.mark.parametrize("value", ["289381508152", "918181508155", "304881508155", "513381508159", "415181508156"])
def test_steuernummer_twelve_digit_federal_form(value):
    # Vereinheitlichtes Bundesschema (de.wikipedia) : préfixe Land, sans le 0 inséré / Land prefix, no inserted 0.
    assert de.steuernummer(value) == value


@pytest.mark.parametrize("value", ["2893181508152", "6181081508155", "689381508152", "123456789", "12345678901234"])
def test_steuernummer_rejections(value):
    assert de.steuernummer(value) is None


# --- RVNR, KVNR -----------------------------------------------------------------------------------


def test_rvnr_vkvv_example():
    assert de.rvnr("15070649C103") == "15070649C103"
    assert de.rvnr("15 070649 c 103") == "15070649C103"
    assert de.rvnr("15070649C104") is None


@pytest.mark.parametrize("body", ["15070649C10", "65311290M55", "04560100X01", "12000000A00"])
def test_rvnr_single_check_digit_and_mutations(body):
    valid = _valid_with_check(body, de.rvnr)
    assert len(valid) == 1
    value = valid[0]
    for i, char in enumerate(value):
        if char.isdigit():
            assert de.rvnr(value[:i] + str((int(char) + 1) % 10) + value[i + 1:]) is None


@pytest.mark.parametrize("value", ["15321349C10", "15071349C10", "15829949C10"])
def test_rvnr_rejects_impossible_dates(value):
    assert not _valid_with_check(value, de.rvnr)


def test_kvnr_wikipedia_example():
    assert de.kvnr("A123456780") == "A123456780"
    assert de.kvnr("A123456789") is None
    assert len(_valid_with_check("Z98765432", de.kvnr)) == 1


# --- Pièces d'identité, permis / identity documents, driving licence --------------------------------


@pytest.mark.parametrize(("number", "check"), [("T22000129", "3"), ("122000129", "7"), ("L01X00T47", "1"),
                                               ("C01X00T47", "8")])
def test_id_document_icao_specimens(number, check):
    assert de.id_document(number) == number
    assert de.id_document(number + check) == number
    assert de.id_document(number + str((int(check) + 1) % 10)) is None


@pytest.mark.parametrize("value", ["A01X00T47", "L01X00T4", "L01X00T47AB", "LO1X00T47"])
def test_id_document_alphabet_and_length(value):
    assert de.id_document(value) is None


def test_fuehrerschein_specimen_and_x_check():
    assert de.fuehrerschein("B072RRE2I55") == "B072RRE2I5"
    assert de.fuehrerschein("B072RRE2I45") is None
    x_value = next(f"J{n:08d}X1" for n in range(1000) if de.fuehrerschein(f"J{n:08d}X1"))
    assert de.fuehrerschein(x_value) == x_value[:10]


def test_phone_numbers():
    assert de.phone("030 12345678") == "+493012345678"
    assert de.phone("(030) 1234567") == "+49301234567"
    assert de.phone("0171-1234567") == "+491711234567"
    assert de.phone_mobile("0151 23456789") == "+4915123456789"
    assert de.phone_mobile("030 12345678") is None
    assert de.phone("0049 30 1234567") is None
    assert de.phone("030 1") is None


# --- Pack et moteur / pack and engine ----------------------------------------------------------


def test_pack_is_well_formed():
    pack = load_pack("DE")
    assert pack.country == "DE" and pack.locale["phone_codes"] == ["49"]
    for recognizer in pack.recognizers:
        assert not re.search(r"(?<!\\)[+*]", recognizer.regex.pattern), recognizer.id
        assert recognizer.tier == "A" or recognizer.contexts, recognizer.id


def test_letter_is_anonymized(anonymizer_de):
    result = anonymizer_de.anonymize(LETTER)
    for secret in (STEUER_ID, SV_NUMMER, "A123456780", "L01X00T471", "B072RRE2I55", "181/815/08155",
                   "030 12345678", "0171 1234567", "36574261809"):
        assert secret not in result.text
        assert secret not in str(result.report)
    for placeholder in ("[STEUER_ID_1]", "[SV_NUMMER_1]", "[KVNR_1]", "[CNI_1]", "[PERMIS_1]",
                        "[STEUERNUMMER_1]", "[TEL_1]", "[TEL_2]"):
        assert placeholder in result.text
    # Même identifiant, deux écritures : même balise / same identifier, two spellings: same placeholder.
    assert result.text.count("[STEUER_ID_1]") == 2 and "[STEUER_ID_2]" not in result.text


def test_auto_mode_activates_germany(anonymizer):
    analysis = anonymizer.analyze(LETTER)
    assert "DE" in analysis.countries
    assert any(reason.startswith("keywords") for reason in analysis.country_reasons["DE"])
    assert "[STEUER_ID_1]" in anonymizer.anonymize(LETTER).text


def test_auto_mode_other_evidence(anonymizer):
    assert "DE" in anonymizer.analyze("Rückruf unter +49 30 1234567").countries
    assert "DE" in anonymizer.analyze("IBAN DE89 3704 0044 0532 0130 00").countries


def test_french_document_does_not_activate_germany(anonymizer):
    # Pièges : « tél. », « fax », « mobil-home », « TIN » (formulaires internationaux), « handy » (anglais).
    text = ("Bonjour Madame Martin, tél. 06 12 34 56 78, fax 01 23 45 67 89. Votre mobil-home est réservé. "
            "Indiquez votre NIF/TIN sur le formulaire. It is handy. Numéro fiscal 1234567890123.")
    assert "DE" not in anonymizer.analyze(text).countries
    assert "DE" not in anonymizer.analyze(FRENCH_DOCUMENT).countries


def test_shared_german_reference_document(anonymizer):
    result = anonymizer.anonymize(GERMAN_DOCUMENT)
    assert "DE" in result.analysis.countries
    assert "089 1234567" not in result.text and "0151 23456789" not in result.text


def test_weak_and_context_only_tiers(anonymizer_de):
    # Sans mot-clé, pas une KVNR ; depuis 1.0.2, un code masqué en identifiant (filtre fort, `ID_CODE`).
    # No keyword, no KVNR; since 1.0.2 a code masked as a plain identifier (strong filter).
    assert anonymizer_de.anonymize("Artikel A123456780 geliefert.").text == "Artikel [IDENTIFIANT_1] geliefert."
    assert "[KVNR_1]" in anonymizer_de.anonymize("Krankenkasse: AOK, Versichertennummer A123456780").text
    strict = Anonymizer(countries=("DE",), profile="strict")
    assert "A123456780" not in strict.anonymize("Artikel A123456780 geliefert.").text
    assert "181/815/08155" in anonymizer_de.anonymize("Aktenzeichen 181/815/08155").text
    # Pas un téléphone berlinois ; depuis 1.0.2, la suite nue de 10 chiffres est un identifiant (`ID_LONG_NUMBER`).
    # Not a Berlin phone; since 1.0.2 the bare run of 10 digits is an identifier.
    out = anonymizer_de.anonymize("Bestellung 030 1234567890 vom Lager").text
    assert out == "Bestellung 030 [IDENTIFIANT_1] vom Lager"


def test_vat_follows_company_policy(anonymizer_de):
    text = "Muster GmbH, USt-IdNr. DE136695976."
    assert "DE136695976" in anonymizer_de.anonymize(text).text
    assert "DE136695976" not in Anonymizer(countries=("DE",), company_ids="mask").anonymize(text).text
    sole = anonymizer_de.anonymize("Hans Weber, Einzelunternehmer, USt-IdNr. DE136695976.")
    assert "DE136695976" not in sole.text


def test_labels_neutral_and_english():
    text = "Steuer-ID 36574261809"
    assert Anonymizer(countries=("DE",), neutral_labels=True).anonymize(text).text == "Steuer-ID [NUM_FISCAL_1]"
    assert Anonymizer(countries=("DE",), label_language="en").anonymize(text).text == "Steuer-ID [STEUER_ID_1]"


def test_dates_are_not_phone_numbers(anonymizer_de):
    for text in ("Telefonisch vereinbart am 01.02.2024 um 10:30, Rufnummer folgt.", "Rufnummer folgt 01-02-2024."):
        assert anonymizer_de.anonymize(text).text == text


@pytest.mark.parametrize(("text", "expected"), [
    # Un nombre voisin ne fait plus rejeter le numéro / a neighbouring number no longer voids the phone number.
    ("erreichbar unter 0171 1234567 10 Uhr", "erreichbar unter [TEL_1] 10 Uhr"),
    ("Tel. 030 12345678 12345 Berlin", "Tel. [TEL_1] 12345 Berlin"),
    ("Telefon (privat): 030 1234567", "Telefon (privat): [TEL_1]"),
    ("Tel. 030 / 1234567", "Tel. [TEL_1]"),
    ("Tel. (030) 1234567", "Tel. [TEL_1]"),
    ("Handynummer (0171) 1234567", "Handynummer [TEL_1]"),
])
def test_phone_layouts(anonymizer_de, text, expected):
    assert anonymizer_de.anonymize(text).text == expected


@pytest.mark.parametrize(("text", "expected"), [
    ("Steuernummer 93815/08152", "Steuernummer [STEUERNUMMER_1]"),      # ancienne forme BW / older BW form
    ("Steuernummer 22/815/0815/4", "Steuernummer [STEUERNUMMER_1]"),    # ancienne forme RP / older RP form
    ("Steuernummer 289381508152", "Steuernummer [STEUERNUMMER_1]"),     # Bundesschema à 12 chiffres
    ("Steuer-ID: 365 742 618 09", "Steuer-ID: [STEUER_ID_1]"),
    ("SV-Nummer 15 070649 C 10 3", "SV-Nummer [SV_NUMMER_1]"),
])
def test_identifier_layouts(anonymizer_de, text, expected):
    assert anonymizer_de.anonymize(text).text == expected


def test_identifiers_inside_longer_numbers_are_left_alone(anonymizer_de):
    # Bornes dans la regex : aucune fenêtre prise dans un nombre plus long / no window inside a longer number.
    # Filtre fort 1.0.2 : chaque nombre entier est masqué en code ou longue suite (`ID_CODE`, `ID_LONG_NUMBER`),
    # jamais une fenêtre d'identifiant allemand prise dedans. Strong filter 1.0.2: each whole number is masked as a
    # code or a long run, never a German identifier window taken inside it.
    text = "Steuer-ID Referenz 1365742618090, Sozialversicherungsnummer 915070649C1031."
    expected = "Steuer-ID Referenz [IDENTIFIANT_1], Sozialversicherungsnummer [IDENTIFIANT_2]."
    assert anonymizer_de.anonymize(text).text == expected


@pytest.fixture(scope="module")
def anonymizer_eu() -> Anonymizer:
    return Anonymizer(countries=EU_PACKS)


@settings(max_examples=150, deadline=None)
@given(text=st.lists(st.sampled_from(_TOKENS), max_size=40).map("".join))
def test_left_boundaries_only_prefilter(anonymizer_eu, text):
    """Les bornes gauches dans les motifs ne font que préfiltrer : avec ou sans elles, mêmes zones.

    Left in-pattern boundaries only prefilter: same zones with or without them (engine loop, all contexts forced).
    """
    folded = fold(text)
    groups = frozenset(g for pack in anonymizer_eu.packs for g in pack.context)
    ctx = DetectionContext(text, folded, anonymizer_eu._keywords.scan(folded), EU_PACKS, "und",
                           anonymizer_eu.settings, [0], [len(text)], [groups])
    for pack in anonymizer_eu.packs:
        if pack.id not in EU_PACKS:
            continue
        for rec in pack.recognizers:
            plain = dataclasses.replace(rec, regex=re.compile(_PREFILTER_BOUNDARY_RE.sub("", rec.regex.pattern),
                                                              rec.regex.flags))
            found = []
            for candidate in (rec, plain):
                spans: list = []
                anonymizer_eu._run(candidate, ctx, spans)
                found.append([(s.start, s.end, s.value) for s in spans])
            assert found[0] == found[1], rec.id


@settings(max_examples=300)
@given(st.text(alphabet="0123456789ACKLXZaß .-/", max_size=16))
def test_validators_never_raise(text):
    for validator in (de.steuer_id, de.steuernummer, de.rvnr, de.kvnr, de.id_document, de.fuehrerschein,
                      de.ust_idnr, de.phone, de.phone_mobile):
        result = validator(text)
        assert result is None or (isinstance(result, str) and result.isascii())
