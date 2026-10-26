"""Pack Luxembourg : validateurs, mode auto, anonymisation de bout en bout.

Luxembourg pack: validators (independent reference implementations, python-stdnum as a test-only oracle
for the VAT number), auto-mode activation, end-to-end anonymisation.
"""

from __future__ import annotations

from datetime import date
from time import perf_counter

import phonenumbers
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.lu import tva as std_tva

from gdprguardian import Anonymizer
from gdprguardian.packs import load_pack
from gdprguardian.validators import lu

from . import FRENCH_DOCUMENT, GENERIC_HEADERS, GERMAN_DOCUMENT, foreign_header_conflicts

# --- Références indépendantes, écrites d'après les définitions publiques ---
# --- Independent references, written from the public definitions ---


def luhn_digit(payload: str) -> int:
    """Chiffre de Luhn : on double un chiffre sur deux en partant de la droite / doubling from the right."""
    total = 0
    for i, ch in enumerate(reversed(payload)):
        value = int(ch) * (2 if i % 2 == 0 else 1)
        total += value - 9 if value > 9 else value
    return (10 - total % 10) % 10


def _d5(j: int, k: int) -> int:
    """Produit du groupe diédral D5 (0-4 rotations, 5-9 symétries) / dihedral group D5 product."""
    if j < 5:
        return (j + k) % 5 if k < 5 else 5 + (j + k - 5) % 5
    return 5 + (j - 5 - k) % 5 if k < 5 else (j - k) % 5


_SIGMA = (1, 5, 7, 6, 2, 8, 3, 0, 9, 4)  # permutation de Verhoeff / Verhoeff's permutation


def verhoeff_digit(payload: str) -> int:
    """Chiffre de Verhoeff calculé par l'algèbre de D5, sans tables / computed from D5 algebra, no tables.

    https://en.wikipedia.org/wiki/Verhoeff_algorithm
    """
    check = 0
    for i, ch in enumerate(reversed(payload)):
        digit = int(ch)
        for _ in range(i + 1):
            digit = _SIGMA[digit]
        check = _d5(check, digit)
    return (5 - check) % 5 if check < 5 else check


def matricule_of(payload11: str) -> str:
    return f"{payload11}{luhn_digit(payload11)}{verhoeff_digit(payload11)}"


@st.composite
def payloads(draw: st.DrawFn) -> str:
    year = draw(st.integers(1900, date.today().year))
    month, day, serial = draw(st.integers(1, 12)), draw(st.integers(1, 28)), draw(st.integers(0, 999))
    return f"{year:04d}{month:02d}{day:02d}{serial:03d}"


# --- Matricule ---


def test_synthetic_matricule():
    assert matricule_of("19850115001") == "1985011500173"
    assert lu.matricule("1985 0115 001 73") == "1985011500173"
    assert lu.matricule("1985011500174") is None   # mauvais Verhoeff / wrong Verhoeff digit
    assert lu.matricule("1985011500163") is None   # mauvais Luhn / wrong Luhn digit


@settings(max_examples=300)
@given(payloads())
def test_matricule_accepts_both_keys(payload):
    assert lu.matricule(matricule_of(payload)) == matricule_of(payload)


@settings(max_examples=300)
@given(payloads(), st.integers(0, 12), st.integers(1, 9))
def test_matricule_detects_every_single_digit_error(payload, position, delta):
    value = matricule_of(payload)
    wrong = value[:position] + str((int(value[position]) + delta) % 10) + value[position + 1:]
    assert lu.matricule(wrong) is None


@settings(max_examples=300)
@given(payloads(), st.integers(0, 9))
def test_matricule_detects_adjacent_transpositions(payload, position):
    value = matricule_of(payload)
    swapped = value[:position] + value[position + 1] + value[position] + value[position + 2:]
    if swapped != value:
        assert lu.matricule(swapped) is None


@pytest.mark.parametrize("payload", [
    "17991231001",          # avant 1800 / before 1800
    "19851315001",          # mois 13 / month 13
    "19850132001",          # jour 32 / day 32
    f"{date.today().year + 1}0101001",   # naissance future / future birth
])
def test_matricule_rejects_impossible_dates(payload):
    assert lu.matricule(matricule_of(payload)) is None


def test_matricule_legacy_is_structural():
    assert lu.matricule_legacy("1985 0115 001") == "19850115001"
    assert lu.matricule_legacy("19851315001") is None
    assert lu.matricule_legacy("1985011500173") is None


# --- TVA, RCS, téléphone / VAT, RCS, phone ---


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=6, max_size=6), st.integers(0, 99), st.booleans())
def test_tva_agrees_with_stdnum(body, key, fix_key):
    value = f"LU{body}{int(body) % 89 if fix_key else key:02d}"
    assert (lu.tva(value) is not None) == std_tva.is_valid(value)


def test_tva_examples():
    assert lu.tva("LU 150 274 42") == "LU15027442"
    assert lu.tva("LU15027443") is None


@pytest.mark.parametrize(("value", "expected"), [
    ("B 123 456", "B123456"), ("B123456", "B123456"), ("A12345", "A12345"), ("F 1.234", "F1234"),
    ("Z1234", None), ("B1234567", None), ("B", None),
])
def test_rcs(value, expected):
    assert lu.rcs(value) == expected


@pytest.mark.parametrize(("value", "expected"), [
    ("621 123 456", "+352621123456"),
    ("691 12 34 56", "+352691123456"),
    ("26 12 34 56", "+35226123456"),
    ("45 67 89", "+352456789"),
    ("+352 621 123 456", "+352621123456"),
    ("00352 26 12 34 56", "+35226123456"),
    ("+32 474 12 34 56", None),
    ("12 34 56", None),
    ("6211234567", None),
])
def test_phone(value, expected):
    assert lu.phone(value) == expected


@settings(max_examples=400)
@given(st.one_of(st.text(alphabet="0123456789", min_size=6, max_size=6),
                 st.text(alphabet="0123456789", min_size=8, max_size=8),
                 st.text(alphabet="0123456789", min_size=8, max_size=8).map(lambda s: "6" + s)))
def test_phone_accepts_every_number_valid_for_libphonenumber(national):
    # Rappel d'abord, pour les longueurs que les motifs produisent (6 ou 8 chiffres, mobiles à 9).
    # Recall first, for the lengths the patterns produce (6 or 8 digits, 9-digit mobiles).
    if phonenumbers.is_valid_number(phonenumbers.parse("+352" + national)):
        assert lu.phone(national) == "+352" + national


# --- Mode auto / auto mode ---


def test_purely_french_document_does_not_activate_luxembourg(anonymizer):
    # « Jardin du Luxembourg », « matricule » d'un salarié : aucun indice luxembourgeois.
    assert "LU" not in anonymizer.analyze(FRENCH_DOCUMENT).countries


def test_german_document_does_not_activate_luxembourg(anonymizer):
    assert "LU" not in anonymizer.analyze(GERMAN_DOCUMENT).countries


@pytest.mark.parametrize("text", [
    # Coquille courante du RCS français / common misspelling of the French register.
    "ACME SAS, immatriculée au Registre de Commerce et des Sociétés de Lyon sous le n° 732 829 320.",
    "Das Großherzogtum Baden und die großherzogliche Familie.",
])
def test_lookalike_words_do_not_activate_luxembourg(anonymizer, text):
    assert "LU" not in anonymizer.analyze(text).countries


@pytest.mark.parametrize(("text", "reason"), [
    ("Contact : +352 621 123 456", "phone:+352"),
    ("IBAN LU28 0019 4006 4475 0000", "iban:LU"),
    ("Société anonyme, R.C.S. Luxembourg B 123456", "keywords:1"),
    ("Règlement grand-ducal du 19 juin 2013", "keywords:1"),
])
def test_luxembourg_evidence_activates_the_pack(anonymizer, text, reason):
    analysis = anonymizer.analyze(text)
    assert "LU" in analysis.countries
    assert reason in analysis.country_reasons["LU"]


# --- Bout en bout / end to end ---

LETTER = """\
Grand-Duché de Luxembourg — Centre commun de la sécurité sociale
M. Paul Weber, matricule 1985 0115 001 73, demeurant 12, rue de la Gare, L-1611 Luxembourg.
Tél. : 621 123 456 — tél. fixe : 26 12 34 56 — IBAN LU28 0019 4006 4475 0000.
Ancien matricule : 1985 0115 001. Rappel : 1985011500173.
"""


LETTER_SECRETS = ("1985 0115 001 73", "1985011500173", "1985 0115 001", "L-1611", "621 123 456", "26 12 34 56",
                  "LU28 0019 4006 4475 0000")


def test_luxembourg_letter_is_fully_anonymised():
    result = Anonymizer(countries="LU,FR").anonymize(LETTER)
    text = result.text
    for secret in LETTER_SECRETS:
        assert secret not in text
        assert secret not in repr(result.report)
    assert text.count("[MATRICULE_LU_1]") == 2
    assert "[MATRICULE_LU_2]" in text
    for placeholder in ("[CODE_POSTAL_1]", "[TEL_1]", "[TEL_2]", "[IBAN_1]"):
        assert placeholder in text


def test_auto_mode_anonymises_the_luxembourg_letter(anonymizer):
    result = anonymizer.anonymize(LETTER)
    assert "LU" in result.report["countries"]
    assert not [secret for secret in LETTER_SECRETS if secret in result.text]


def test_rcs_sections_follow_the_company_policy():
    a = Anonymizer(countries="LU")
    company = "ACME S.A., R.C.S. Luxembourg B 123456, TVA LU 150 274 42."
    assert a.anonymize(company).text == company
    masked = Anonymizer(countries="LU", company_ids="mask").anonymize(company).text
    assert masked == "ACME S.A., R.C.S. Luxembourg [RCS_1], TVA [TVA_1]."
    # Section A : commerçant personne physique, toujours masqué / natural-person trader, always masked.
    assert a.anonymize("Jean Muller, RCS Luxembourg A 12345.").text == "Jean Muller, RCS Luxembourg [RCS_1]."
    long_form = ("immatriculée au registre de commerce et des sociétés de Luxembourg sous le numéro B 123.456")
    analysis = a.analyze(long_form)
    assert [(s.label, s.value) for s in analysis.spans] == [("RCS", "B123456")]


def test_french_rcs_is_not_read_as_luxembourgish():
    analysis = Anonymizer(countries="LU,FR").analyze("RCS Paris B 732 829 320")
    assert [s.source for s in analysis.spans] == ["FR_RCS"]


@pytest.mark.parametrize("text", ["R.C.S. A 123 456 789", "RCS B 732 829 320", "RCS Luxembourg B 123.456.789"])
def test_rcs_never_cuts_a_longer_number(text):
    # Un SIREN français après « RCS » : couper à 6 chiffres laisserait « 789 » en clair.
    # A French SIREN after "RCS": cutting at 6 digits would leave "789" visible.
    assert Anonymizer(countries="LU", company_ids="mask").analyze(text).spans == []


def test_rcs_anchor_variants():
    a = Anonymizer(countries="LU", company_ids="mask")
    assert a.anonymize("R. C. S. Luxembourg B 123456").text == "R. C. S. Luxembourg [RCS_1]"
    assert a.anonymize("RCS Luxembourg B123456, 12 rue").text == "RCS Luxembourg [RCS_1], 12 rue"
    assert a.anonymize("TVA lu 150 274 42").text == "TVA [TVA_1]"


def test_phones_without_prefix_need_context():
    a = Anonymizer(countries="LU,FR")
    assert a.anonymize("Montant : 621 123 456 EUR.").text == "Montant : 621 123 456 EUR."
    assert a.anonymize("GSM 691 12 34 56, tél. 26 12 34 56").text == "GSM [TEL_1], tél. [TEL_2]"


def test_postcode_requires_a_locality():
    a = Anonymizer(countries="LU")
    assert a.anonymize("L-1611 Luxembourg").text == "[CODE_POSTAL_1] Luxembourg"
    assert a.anonymize("Modèle L-1611 en stock").text == "Modèle L-1611 en stock"


@pytest.mark.parametrize(("unit", "repeat"), [("1", 100_000), ("19 ", 35_000), ("R.C.S. Luxembourg ", 6_000),
                                              ("registre de commerce et des sociétés ", 3_000),
                                              ("matricule 1985 ", 7_000), ("L-1611 ", 15_000)])
def test_hostile_inputs_stay_linear(unit, repeat):
    a = Anonymizer(countries="LU")
    t0 = perf_counter()
    a.analyze(unit * repeat)
    assert perf_counter() - t0 < 5.0


def test_labels():
    text = "Matricule 1985 0115 001 73"
    assert Anonymizer(countries="LU", neutral_labels=True).anonymize(text).text == "Matricule [ID_NATIONAL_1]"
    assert Anonymizer(countries="LU", label_language="en").anonymize(text).text == "Matricule [LU_NATIONAL_ID_1]"


def test_header_lexicon_claims_no_foreign_column():
    # « Matricule » d'un classeur RH français ne doit pas devenir [MATRICULE_LU_1].
    # A French HR "Matricule" column must not become [MATRICULE_LU_1].
    headers = {word for words in load_pack("LU").headers.values() for word in words}
    assert not headers & GENERIC_HEADERS
    assert foreign_header_conflicts("LU") == {}
