"""Pack ES : validateurs (oracle python-stdnum, en test seulement), mode auto et anonymisation de bout en bout.

ES pack: validators (python-stdnum oracle, test-only, LGPL, never shipped), auto mode and end-to-end runs.
"""

from __future__ import annotations

import re

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from stdnum.es import cif as std_cif
from stdnum.es import dni as std_dni
from stdnum.es import nie as std_nie
from stdnum.es import nif as std_nif

from gdprguardian import Anonymizer
from gdprguardian.packs import load_pack
from gdprguardian.validators import es

from . import FRENCH_DOCUMENT

LETTER = (
    "Estimado Sr. García:\n"
    "Le confirmamos los datos de su expediente: DNI 12.345.678-Z, NIE de su cónyuge X1234567L,\n"
    "número de afiliación a la Seguridad Social 28/12345678/40 y NSS de su hija 280123456742.\n"
    "Móvil 612 345 678, Tel. 912-345-678.\n"
    "Recuerde: su DNI 12345678Z figura en el contrato.\n"
)


@pytest.fixture(scope="module")
def anonymizer_es() -> Anonymizer:
    return Anonymizer(countries=("ES",))


# --- DNI, NIE, NIF ------------------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "canonical"), [
    ("12345678Z", "12345678Z"), ("12.345.678-Z", "12345678Z"), ("54362315k", "54362315K"),
    ("1234567L", "01234567L"), ("K1234567L", "K1234567L"), ("M-1234567-L", "M1234567L"),
])
def test_dni_examples(value, canonical):
    assert es.dni(value) == canonical


@pytest.mark.parametrize("value", ["12345678A", "00000000T", "K12345678L", "123456789", "12345678I"])
def test_dni_rejections(value):
    assert es.dni(value) is None


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=8, max_size=8), st.sampled_from(es.DNI_LETTERS + "IOU"))
def test_dni_matches_stdnum(number, letter):
    assume(int(number) != 0)
    value = number + letter
    assert (es.dni(value) is not None) == std_dni.is_valid(value)
    right = number + es.DNI_LETTERS[int(number) % 23]
    assert es.dni(right) == right and std_dni.is_valid(right)


@settings(max_examples=300)
@given(st.sampled_from("XYZ"), st.text(alphabet="0123456789", min_size=7, max_size=7),
       st.sampled_from(es.DNI_LETTERS))
def test_nie_matches_stdnum(prefix, number, letter):
    value = prefix + number + letter
    assert (es.nie(value) is not None) == std_nie.is_valid(value)


@settings(max_examples=200)
@given(st.sampled_from("KLM"), st.text(alphabet="0123456789", min_size=7, max_size=7))
def test_klm_nif_matches_stdnum(prefix, number):
    assume(int(number) != 0)
    value = prefix + number + es.DNI_LETTERS[int(number) % 23]
    assert es.dni(value) == value and std_nif.is_valid(value)


def test_nie_examples():
    assert es.nie("X1234567L") == "X1234567L"
    assert es.nie("X-2482300-W") == "X2482300W"
    assert es.nie("X01234567L") == "X01234567L"  # ancien format X + 8 chiffres / pre-2008 X + 8 digits
    assert es.nie("Y01234567L") is None
    assert es.nie("X1234567A") is None


# --- CIF, TVA -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["A58818501", "J99216582", "B64717838", "Q2826000H", "B-64.717.838"])
def test_cif_examples(value):
    assert es.cif(value) == value.replace("-", "").replace(".", "")


def test_cif_follows_the_official_letter_or_digit_rule():
    # stdnum accepte les deux formes pour tous les types ; la règle officielle est plus stricte.
    for value in ("A5881850A", "Q28260008"):
        assert std_cif.is_valid(value) and es.cif(value) is None


@settings(max_examples=300)
@given(st.sampled_from("ABCDEFGHJNPQRSUVW"), st.text(alphabet="0123456789", min_size=7, max_size=7),
       st.sampled_from("0123456789ABCDEFGHIJ"))
def test_cif_is_a_subset_of_stdnum(kind, digits, control):
    value = kind + digits + control
    if es.cif(value) is not None:
        assert std_cif.is_valid(value)
    elif kind in "CDFGJUV" and digits[:2] != "00":
        assert not std_cif.is_valid(value)


def test_vat_numbers():
    assert es.vat_person("ES12345678Z") == "ES12345678Z"
    assert es.vat_person("ES X1234567L") == "ESX1234567L"
    assert es.vat_company("ESB64717838") == "ESB64717838"
    assert es.vat_person("ESB64717838") is None and es.vat_company("ES12345678Z") is None
    for value in ("ES12345678Z", "ESX1234567L", "ESB64717838"):
        assert std_nif.is_valid(value)


# --- NSS, téléphone / NSS, phone ----------------------------------------------------------------------


def test_nss_variants():
    assert es.nss("281234567840") == "281234567840"   # les deux variantes / both variants
    assert es.nss("280123456742") == "280123456742"   # variante TGSS (province × 10^7) / TGSS variant
    assert es.nss("28/01234567/85") == "280123456785"  # variante concaténée (Faker) / concatenated variant
    assert es.nss("281234567841") is None
    assert es.nss("001234567840") is None


@settings(max_examples=200)
@given(st.integers(1, 53), st.integers(0, 99_999_999))
def test_nss_check_is_unique_and_detects_errors(province, number):
    body = f"{province:02d}{number:08d}"
    valid = [body + f"{c:02d}" for c in range(97) if es.nss(body + f"{c:02d}")]
    assert 1 <= len(valid) <= 2


def test_phone_numbers():
    assert es.phone("612 345 678") == "+34612345678"
    assert es.phone("91 123 45 67") == "+34911234567"
    assert es.phone("512 345 678") is None
    assert es.phone("6123456789") is None


# --- Pack et moteur / pack and engine ----------------------------------------------------------------


def test_pack_is_well_formed():
    pack = load_pack("ES")
    assert pack.country == "ES" and pack.locale["phone_codes"] == ["34"]
    for recognizer in pack.recognizers:
        assert not re.search(r"(?<!\\)[+*]", recognizer.regex.pattern), recognizer.id
        assert recognizer.tier == "A" or recognizer.contexts, recognizer.id


def test_letter_is_anonymized(anonymizer_es):
    result = anonymizer_es.anonymize(LETTER)
    for secret in ("12.345.678-Z", "X1234567L", "28/12345678/40", "280123456742", "612 345 678",
                   "912-345-678", "12345678Z"):
        assert secret not in result.text
        assert secret not in str(result.report)
    for placeholder in ("[DNI_1]", "[NIE_1]", "[NSS_1]", "[NSS_2]", "[TEL_1]", "[TEL_2]"):
        assert placeholder in result.text
    assert result.text.count("[DNI_1]") == 2 and "[DNI_2]" not in result.text


def test_auto_mode_activates_spain(anonymizer):
    analysis = anonymizer.analyze(LETTER)
    assert "ES" in analysis.countries
    assert not {"DE", "IT", "NL", "PT"} & set(analysis.countries)
    assert "[DNI_1]" in anonymizer.anonymize(LETTER).text
    assert "ES" in anonymizer.analyze("Llámeme al +34 612 345 678").countries


def test_french_document_does_not_activate_spain(anonymizer):
    # Pièges : NIF et NSS (identifiants français), CIF (Incoterm), « nie » (verbe), code NAF, C.P., IVA.
    text = ("Monsieur, votre NIF figure sur l'avis ; NSS 1 85 05 78 006 084 91. Livraison prix CIF Marseille. "
            "Le prévenu nie les faits. Code NAF 6201Z, C.P. 75001. Taux d'IVA non applicable. Téléphone mobile.")
    assert "ES" not in anonymizer.analyze(text).countries
    assert "ES" not in anonymizer.analyze(FRENCH_DOCUMENT).countries


def test_weak_tier_needs_context(anonymizer_es):
    # 1.0.2 : sans son contexte ce n'est pas un NSS, mais une suite nue de 8 chiffres ou plus est un identifiant
    # générique (`ID_LONG_NUMBER`). Without its context it is no NSS, but a bare run of 8+ digits is a generic ID.
    assert anonymizer_es.anonymize("Pedido 281234567840 enviado.").text == "Pedido [IDENTIFIANT_1] enviado."
    assert "[NSS_1]" in anonymizer_es.anonymize("Seguridad Social: 281234567840").text
    assert "[NSS_1]" in anonymizer_es.anonymize("NUSS: 28 12345678 40").text
    assert "612 345 678" in anonymizer_es.anonymize("Importe: 612 345 678 euros").text


def test_units_are_not_dni_letters(anonymizer_es):
    text = "Superficie de 12 345 678 m y caudal de 1.234.567 l."
    assert anonymizer_es.anonymize(text).text == text


@pytest.mark.parametrize(("text", "expected"), [
    ("N. S. S. 28 12345678 40", "N. S. S. [NSS_1]"),
    ("Teléfono (móvil): 612 345 678", "Teléfono (móvil): [TEL_1]"),
    # Fenêtres valides prises dans des nombres plus longs, contexte présent : jamais un TEL ni un NSS ; depuis 1.0.2
    # le nombre entier est un identifiant générique. Valid windows in longer numbers: never a TEL or an NSS; since
    # 1.0.2 the whole number is a generic identifier (`ID_LONG_NUMBER`).
    ("Teléfono y Seguridad Social: ref. 9123456780123 / 128123456784012",
     "Teléfono y Seguridad Social: ref. [IDENTIFIANT_1] / [IDENTIFIANT_2]"),
])
def test_labels_and_number_boundaries(anonymizer_es, text, expected):
    assert anonymizer_es.anonymize(text).text == expected


def test_header_lexicon_leaves_the_french_naf_code_alone():
    # Le lexique d'en-têtes est commun à tous les packs en mode auto : « NAF » est le code APE en France.
    # The header lexicon is shared by every pack in auto mode: "NAF" is the French APE activity code.
    words = {word for words in load_pack("ES").headers.values() for word in words}
    assert "naf" not in words and "nss" in words


@settings(max_examples=300)
@given(st.text(alphabet="0123456789ABJKLXZaz .-/ßı", max_size=16))
def test_validators_never_raise(text):
    for validator in (es.dni, es.nie, es.cif, es.nif_person, es.vat_person, es.vat_company, es.nss, es.phone):
        result = validator(text)
        assert result is None or isinstance(result, str)


def test_company_ids_follow_policy(anonymizer_es):
    text = "Construcciones Pérez S.L., CIF B64717838, NIF-IVA ESB64717838."
    assert anonymizer_es.anonymize(text).text == text
    masked = Anonymizer(countries=("ES",), company_ids="mask").anonymize(text).text
    assert "B64717838" not in masked
    autonomo = anonymizer_es.anonymize("Juan Pérez, autónomo, NIF-IVA ES12345678Z.").text
    assert "ES12345678Z" not in autonomo
