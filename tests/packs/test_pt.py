"""Pack PT : validateurs (oracle python-stdnum, en test seulement), mode auto et anonymisation de bout en bout.

PT pack: validators (python-stdnum oracle, test-only, LGPL, never shipped), auto mode and end-to-end runs.
"""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.pt import cc as std_cc
from stdnum.pt import nif as std_nif

from gdprguardian import Anonymizer
from gdprguardian.packs import load_pack
from gdprguardian.validators import pt

from . import FRENCH_DOCUMENT

LETTER = (
    "Exmo. Senhor João Silva,\n"
    "Confirmamos os seus dados: NIF 123 456 789, NISS 12347312896,\n"
    "Cartão de Cidadão n.º 13201144 1 ZZ8, número de utente 987 654 321.\n"
    "Morada: Rua das Flores 10, 1000-001 Lisboa. Telemóvel 912 345 678.\n"
    "O contribuinte n.º 123456789 deve assinar.\n"
)


@pytest.fixture(scope="module")
def anonymizer_pt() -> Anonymizer:
    return Anonymizer(countries=("PT",))


# --- NIF / NIPC ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["123456789", "136695973", "123 456 789", "232013969"])
def test_nif_person_examples(value):
    assert pt.nif_person(value) == value.replace(" ", "")
    assert pt.nipc(value) is None


def test_nipc_examples():
    assert pt.nipc("501964843") == "501964843"
    assert pt.nif_person("501964843") is None
    assert pt.nif("501964844") is None
    assert pt.nif("012345678") is None


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9))
def test_nif_matches_stdnum(value):
    assert (pt.nif(value) is not None) == std_nif.is_valid(value)
    # Partition : personne physique ou personne morale, jamais les deux / natural xor legal person.
    assert (pt.nif_person(value) is not None) + (pt.nipc(value) is not None) == (pt.nif(value) is not None)


# --- NISS, Cartão de Cidadão, NIC --------------------------------------------------------------------


@pytest.mark.parametrize("value", ["12347312896", "21865241240", "17512436983", "21467822675", "14652348947"])
def test_niss_reference_examples(value):
    # Exemples des tests de django-localflavor (BSD) / django-localflavor test vectors.
    assert pt.niss(value) == value


@pytest.mark.parametrize("value", ["12347312892", "21865241241", "01467822673", "31467822675", "1234731289"])
def test_niss_rejections(value):
    assert pt.niss(value) is None


@settings(max_examples=200)
@given(st.sampled_from("12"), st.text(alphabet="0123456789", min_size=9, max_size=9))
def test_niss_single_check_digit_detects_typos(first, rest):
    body = first + rest
    valid = [body + c for c in "0123456789" if pt.niss(body + c)]
    assert len(valid) == 1
    for i in range(10):
        typo = valid[0][:i] + str((int(valid[0][i]) + 1) % 10) + valid[0][i + 1:]
        assert pt.niss(typo) is None or typo[0] not in "12"


@pytest.mark.parametrize("value", ["132011441ZZ8", "129463833ZY7", "129463833ZZ5", "13201144-1ZZ8", "000000000ZZ4"])
def test_cc_examples(value):
    assert pt.cc(value) == value.replace("-", "")
    assert std_cc.is_valid(value.replace("-", ""))


@pytest.mark.parametrize("value", ["13201144-1ZZ7", "13201144-3ZZ8", "12946383-3ZY5", "13201144AZZ8", "13201144"])
def test_cc_rejections(value):
    assert pt.cc(value) is None


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=9, max_size=9),
       st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=2, max_size=2),
       st.sampled_from("0123456789"))
def test_cc_matches_stdnum(nic, version, check):
    value = nic + version + check
    assert (pt.cc(value) is not None) == std_cc.is_valid(value)


def test_nic_canonical_form():
    assert pt.nic("13201144 1") == "13201144"
    assert pt.nic("1320114") == "01320114"
    assert pt.nic("123456") is None


def test_phone_numbers():
    assert pt.phone("912 345 678") == "+351912345678"
    assert pt.phone("21 123 4567") == "+351211234567"
    assert pt.phone("808 200 520") == "+351808200520"
    assert pt.phone("942 345 678") is None
    assert pt.phone("12 345 678") is None


# --- Pack et moteur / pack and engine --------------------------------------------------------------


def test_pack_is_well_formed():
    pack = load_pack("PT")
    assert pack.country == "PT" and pack.locale["phone_codes"] == ["351"]
    for recognizer in pack.recognizers:
        assert not re.search(r"(?<!\\)[+*]", recognizer.regex.pattern), recognizer.id
        assert recognizer.tier == "A" or recognizer.contexts, recognizer.id


def test_letter_is_anonymized(anonymizer_pt):
    result = anonymizer_pt.anonymize(LETTER)
    for secret in ("123 456 789", "123456789", "12347312896", "13201144 1 ZZ8", "987 654 321", "1000-001",
                   "912 345 678"):
        assert secret not in result.text
        assert secret not in str(result.report)
    for placeholder in ("[NIF_1]", "[NISS_1]", "[CNI_1]", "[UTENTE_SNS_1]", "[CODE_POSTAL_1]", "[TEL_1]"):
        assert placeholder in result.text
    assert result.text.count("[NIF_1]") == 2 and "[NIF_2]" not in result.text


def test_auto_mode_activates_portugal(anonymizer):
    analysis = anonymizer.analyze(LETTER)
    assert "PT" in analysis.countries
    assert not {"DE", "ES", "IT", "NL"} & set(analysis.countries)
    assert "[NIF_1]" in anonymizer.anonymize(LETTER).text


def test_other_documents_do_not_activate_portugal(anonymizer):
    # Pièges : NIF (français), NISS (belge), « BI-mensuel », « CC : », « utente » (italien).
    french = ("Votre NIF figure sur l'avis d'imposition. NISS belge 85.07.30-033.28. Revue bi-mensuelle. "
              "CC : direction. Contribution sociale, code postal 75001, téléphone 01 23 45 67 89.")
    assert "PT" not in anonymizer.analyze(french).countries
    assert "PT" not in anonymizer.analyze(FRENCH_DOCUMENT).countries
    italian = "Gentile utente, il servizio clienti risponde al numero indicato."
    assert "PT" not in anonymizer.analyze(italian).countries


def test_labels_and_context(anonymizer_pt):
    assert anonymizer_pt.anonymize("NIF: 123456789").text == "NIF: [NIF_1]"
    assert anonymizer_pt.anonymize("NISS n.º 21865241240").text == "NISS n.º [NISS_1]"
    assert anonymizer_pt.anonymize("BI n.º 13201144").text == "BI n.º [NIC_1]"
    assert "123456789" in anonymizer_pt.anonymize("Encomenda 123456789 enviada.").text
    assert "1000-001" in anonymizer_pt.anonymize("Referência 1000-001").text


def test_company_ids_follow_policy(anonymizer_pt):
    text = "Empresa Exemplo, Lda., NIPC 501964843."
    assert anonymizer_pt.anonymize(text).text == text
    assert "501964843" not in Anonymizer(countries=("PT",), company_ids="mask").anonymize(text).text


def test_vat_numbers(anonymizer_pt):
    # Un empresário em nome individual facture sous son NIF : donnée personnelle / a sole trader's VAT is his NIF.
    assert pt.vat_person("PT 123 456 789") == "PT123456789" and pt.vat_company("PT123456789") is None
    assert pt.vat_company("PT501964843") == "PT501964843" and pt.vat_person("PT501964843") is None
    assert pt.vat_person("PT123456788") is None
    assert anonymizer_pt.anonymize("João Silva, NIF PT 123 456 789").text == "João Silva, NIF [TVA_1]"
    company = "Empresa Exemplo, Lda., NIF PT501964843."
    assert anonymizer_pt.anonymize(company).text == company


def test_nif_patterns_split_by_first_digit():
    # Le premier chiffre de chaque motif est celui qu'accepte son validateur / each pattern's first digit.
    regexes = {r.id: r.regex for r in load_pack("PT").recognizers}
    assert regexes["PT_NIF"].fullmatch("123456789") and not regexes["PT_NIF"].fullmatch("501964843")
    assert regexes["PT_NIPC"].fullmatch("501964843") and not regexes["PT_NIPC"].fullmatch("123456789")


@pytest.mark.parametrize(("text", "expected"), [
    ("N.I.S.S. 12347312896", "N.I.S.S. [NISS_1]"),
    ("Telefone (casa): 212 345 678", "Telefone (casa): [TEL_1]"),
    ("Contribuinte n.º 123456789", "Contribuinte n.º [NIF_1]"),
])
def test_labels(anonymizer_pt, text, expected):
    assert anonymizer_pt.anonymize(text).text == expected


def test_street_word_activates_portugal(anonymizer):
    result = anonymizer.anonymize("Rua das Flores 10, 1000-001 Lisboa.")
    assert "PT" in result.analysis.countries and "1000-001" not in result.text


def test_header_lexicon_has_no_ambiguous_words():
    # Lexique commun à tous les packs en mode auto : « CC » (copie carbone, centre de coûts) ; « utente » seul
    # désigne la personne. Lexicon shared by every pack in auto mode: "CC" (carbon copy, cost centre); a bare
    # "utente" names the person.
    headers = load_pack("PT").headers
    assert "cc" not in headers["ID_CARD"] and "utente" not in headers["PT_SNS"] and "utente" in headers["PERSON"]


@settings(max_examples=300)
@given(st.text(alphabet="0123456789PTZaı .-/", max_size=16))
def test_validators_never_raise(text):
    for validator in (pt.nif, pt.nif_person, pt.nipc, pt.vat_person, pt.vat_company, pt.niss, pt.cc, pt.nic,
                      pt.sns, pt.phone):
        result = validator(text)
        assert result is None or isinstance(result, str)
