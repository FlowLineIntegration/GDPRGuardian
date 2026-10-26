"""Pack Belgique : validateurs, mode auto, anonymisation de bout en bout.

Belgium pack: validators (python-stdnum and phonenumbers as test-only oracles; stdnum is LGPL and never
shipped), auto-mode activation, end-to-end anonymisation.
"""

from __future__ import annotations

from datetime import date
from time import perf_counter

import phonenumbers
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from stdnum.be import bis as std_bis
from stdnum.be import eid as std_eid
from stdnum.be import nn as std_nn
from stdnum.be import vat as std_vat

from gdprguardian import Anonymizer
from gdprguardian.packs import load_pack
from gdprguardian.validators import be

from . import DUTCH_DOCUMENT, FRENCH_DOCUMENT, GENERIC_HEADERS, GERMAN_DOCUMENT, foreign_header_conflicts

NN_MONTHS = list(range(13))
BIS_MONTHS = [*range(20, 33), *range(40, 53)]


def niss_key(body9: str, born_2000s: bool) -> str:
    """Clé recalculée d'après la définition publique / key recomputed from the public definition."""
    return f"{97 - int(('2' if born_2000s else '') + body9) % 97:02d}"


@st.composite
def niss_bodies(draw: st.DrawFn, months: list[int]) -> str:
    year, month = draw(st.integers(0, 99)), draw(st.sampled_from(months))
    day, serial = draw(st.integers(0, 31)), draw(st.integers(1, 998))
    return f"{year:02d}{month:02d}{day:02d}{serial:03d}"


# --- NISS : registre national et BIS / national register and BIS numbers ---


@pytest.mark.parametrize("value", [
    "85.07.30-033.28",   # fr.wikipedia : 97 - (850730033 mod 97) = 28
    "17.07.30-033.84",   # fr.wikipedia : 97 - (2170730033 mod 97) = 84
    "90.02.01-997-04",   # nl.wikipedia : homme né le 1er février 1990
    "40 00 00 955-79",   # fr.wikipedia : date de naissance incomplète
    "00 00 01 003-64",   # fr.wikipedia : date inconnue (00 00 01)
    "40 00 01 001-33",   # fr.wikipedia : compteur épuisé, jour 01
])
def test_national_number_published_examples(value):
    canonical = value.replace(".", "").replace("-", "").replace(" ", "")
    assert be.nn(value) == be.niss(value) == canonical
    assert std_nn.is_valid(value)


@pytest.mark.parametrize("value", ["98.47.28-997.65", "01.49.07-001.85", "85.20.00-033.49"])
def test_bis_examples(value):
    assert be.bis(value) is not None
    assert be.niss(value) is not None
    assert be.nn(value) is None
    assert std_bis.is_valid(value)


@settings(max_examples=400)
@given(niss_bodies(NN_MONTHS + BIS_MONTHS), st.integers(0, 99))
def test_niss_agrees_with_stdnum(body, key):
    value = f"{body}{key:02d}"
    assert (be.nn(value) is not None) == std_nn.is_valid(value)
    assert (be.bis(value) is not None) == std_bis.is_valid(value)
    assert (be.niss(value) is not None) == (std_nn.is_valid(value) or std_bis.is_valid(value))


@settings(max_examples=300)
@given(niss_bodies(NN_MONTHS + BIS_MONTHS))
def test_niss_correct_key_is_always_accepted(body):
    value = body + niss_key(body, born_2000s=False)
    assert be.niss(value) == value
    wrong = body + f"{(int(value[9:]) % 97) + 1:02d}"
    assert be.niss(wrong) is None or wrong[9:] == niss_key(body, born_2000s=True)


def test_niss_2000s_branch_only_for_years_already_reached():
    this_year = date.today().year % 100
    past = f"{this_year:02d}0101001"
    assert be.niss(past + niss_key(past, born_2000s=True)) is not None
    if this_year < 99:
        future = f"{this_year + 1:02d}0101001"
        assert be.niss(future + niss_key(future, born_2000s=True)) is None


def test_niss_day_counter_only_when_month_is_unknown():
    # Mois inconnu (00, 20, 40) : le jour sert de compteur ; sinon un jour > 31 est rejeté.
    # Différence assumée avec stdnum, qui accepte tout jour / deliberate difference: stdnum accepts any day.
    for body in ("850045001", "852045001", "854045001"):
        assert be.niss(body + niss_key(body, born_2000s=False)) is not None
    known_month = "850745001"
    value = known_month + niss_key(known_month, born_2000s=False)
    assert be.niss(value) is None
    assert std_nn.is_valid(value)


@pytest.mark.parametrize("value", [
    "85.07.30-033.29",   # mauvaise clé / wrong key
    "85.13.01-033.67",   # mois 13 / month 13
    "85.33.00-033.43",   # mois BIS hors plage / BIS month out of range
    "85.53.00-033.86",
    "8507300332",        # 10 chiffres / 10 digits
    "85073003328a",
    "",
])
def test_niss_rejects(value):
    assert be.niss(value) is None


def test_niss_unpadded_restores_spreadsheet_zeros():
    assert be.niss_unpadded("5060712337") == "05060712337"
    assert be.niss_unpadded("10100105") == "00010100105"
    assert be.niss_unpadded("85073003328") is None
    assert be.niss_unpadded("5060712338") is None


# --- BCE / KBO et TVA / enterprise and VAT number ---


@pytest.mark.parametrize(("value", "expected"), [
    ("BE0403019261", "0403019261"),
    ("0403.019.261", "0403019261"),
    ("BE 0428.759.497", "0428759497"),   # reste nul : clé 97 / zero remainder: key 97
    ("BE403019261", "0403019261"),       # ancienne forme à 9 chiffres / legacy 9-digit form
    ("BE (0) 403 019 261", "0403019261"),
    ("BE431150351", None),
    ("2403019261", None),                # premier chiffre 0 ou 1 / first digit 0 or 1
    ("0403019262", None),
])
def test_enterprise_number_examples(value, expected):
    assert be.enterprise_number(value) == expected
    assert std_vat.is_valid(value) == (expected is not None)


@settings(max_examples=400)
@given(st.text(alphabet="0123456789", min_size=9, max_size=10), st.booleans())
def test_enterprise_number_agrees_with_stdnum(digits, fix_key):
    if fix_key and len(digits) == 10:
        digits = digits[:8] + f"{97 - int(digits[:8]) % 97:02d}"
    # Différence assumée : la clé attribuée va de 01 à 97 ; stdnum vérifie seulement la congruence modulo 97 et
    # accepte aussi 00 (pour 97), 98 (pour 01) et 99 (pour 02). Deliberate difference: issued keys run from
    # 01 to 97; stdnum only checks the congruence mod 97 and also accepts 00, 98 and 99.
    issued = digits[-2:] not in ("00", "98", "99")
    assert (be.enterprise_number(digits) is not None) == (std_vat.is_valid(digits) and issued)
    assert (be.enterprise_number("BE" + digits) is not None) == (std_vat.is_valid("BE" + digits) and issued)


def test_enterprise_number_key_00_is_never_issued():
    # 05820873 est divisible par 97 : la clé est 97 / divisible by 97, so the key is 97.
    assert be.enterprise_number("0582087397") == "0582087397"
    assert be.enterprise_number("0582087300") is None


def test_enterprise_number_keys_98_and_99_are_never_issued():
    # 00485872 mod 97 = 96 : la clé est 01 ; 98 lui est congru mais n'est jamais attribué (stdnum l'accepte).
    # 00485872 mod 97 = 96: the key is 01; 98 is congruent but never issued (stdnum accepts it).
    assert be.enterprise_number("0048587201") == "0048587201"
    assert be.enterprise_number("0048587298") is None
    assert std_vat.is_valid("0048587298")
    assert std_vat.is_valid("0582087300")


# --- Carte eID et ancien compte bancaire / eID card and legacy bank account ---


@pytest.mark.parametrize("value", ["000-0011032-71", "591-1917064-58", "591-2010999-97"])
def test_eid_examples(value):
    assert be.eid(value) == value.replace("-", "")
    assert std_eid.is_valid(value)


@settings(max_examples=300)
@given(st.text(alphabet="0123456789", min_size=10, max_size=10), st.integers(0, 99))
def test_eid_agrees_with_stdnum(body, key):
    for value in (f"{body}{key:02d}", f"{body}{int(body) % 97 or 97:02d}"):
        assert (be.eid(value) is not None) == std_eid.is_valid(value)


def test_legacy_account_is_the_iban_bban():
    # BE68 5390 0754 7034 : le BBAN porte sa propre clé mod 97 / the BBAN carries its own mod-97 key.
    assert be.bban("539-0075470-34") == "539007547034"
    assert be.bban("539-0075470-35") is None


# --- Téléphone / phone ---


@pytest.mark.parametrize(("value", "expected"), [
    ("0474 12 34 56", "+32474123456"),
    ("0474/12.34.56", "+32474123456"),
    ("02/513.23.45", "+3225132345"),
    ("050 12 34 56", "+3250123456"),
    ("+32 (0)474 12 34 56", "+32474123456"),
    ("0032 2 513 23 45", "+3225132345"),
    ("+33 6 12 34 56 78", None),
    ("0612345678", None),                # 9 chiffres nationaux hors 4… / 9 national digits not a mobile
    ("02 513 23 4", None),
])
def test_phone_canonical(value, expected):
    assert be.phone(value) == expected


@settings(max_examples=400)
@given(st.one_of(st.text(alphabet="0123456789", min_size=8, max_size=8).filter(lambda s: s[0] != "0"),
                 st.text(alphabet="0123456789", min_size=8, max_size=8).map(lambda s: "4" + s)))
def test_phone_accepts_every_number_valid_for_libphonenumber(national):
    # Rappel d'abord : tout numéro valide pour libphonenumber doit passer / recall first.
    number = phonenumbers.parse("+32" + national)
    if phonenumbers.is_valid_number(number):
        assert be.phone("0" + national) == "+32" + national


# --- Mode auto / auto mode ---


def test_purely_french_document_does_not_activate_belgium(anonymizer):
    assert "BE" not in anonymizer.analyze(FRENCH_DOCUMENT).countries


def test_netherlands_dutch_document_does_not_activate_belgium(anonymizer):
    assert "BE" not in anonymizer.analyze(DUTCH_DOCUMENT).countries


@pytest.mark.parametrize("text", [
    GERMAN_DOCUMENT,
    # Mandat SEPA français : « N° national d'émetteur » / French SEPA mandate.
    "Mandat de prélèvement SEPA. N° national d'émetteur : 123456. Référence unique du mandat : 2024-118.",
    # Québec : « numéro d'entreprise du Québec » (NEQ) / Quebec enterprise number.
    "Numéro d'entreprise du Québec (NEQ) : 1173456789, Revenu Québec, Montréal.",
    "Indiquez votre numéro d'entreprise (SIREN) sur la facture.",
    # « KBO » : association néerlandaise de seniors, cliniques bavaroises / Dutch seniors' union, Bavarian clinics.
    "De KBO-PCOB organiseert een bijeenkomst voor senioren in Utrecht.",
    "Die kbo-Kliniken suchen Pflegekräfte. Unternehmensnummer der Berufsgenossenschaft: 123456789012345.",
    "Die deutschsprachige Gemeinschaft in Rumänien feiert ihr Jubiläum.",
])
def test_lookalike_words_do_not_activate_belgium(anonymizer, text):
    assert "BE" not in anonymizer.analyze(text).countries


@pytest.mark.parametrize(("text", "reason"), [
    ("Contact : +32 474 12 34 56", "phone:+32"),
    ("Virement sur BE68 5390 0754 7034", "iban:BE"),
    ("Rijksregisternummer van de aanvrager", "keywords:1"),
    ("Publié au Moniteur belge", "keywords:1"),
])
def test_belgian_evidence_activates_the_pack(anonymizer, text, reason):
    analysis = anonymizer.analyze(text)
    assert "BE" in analysis.countries
    assert reason in analysis.country_reasons["BE"]


# --- Bout en bout / end to end ---

LETTER = """\
Royaume de Belgique — SPF Finances
Madame Claire Dubois, NISS 85.07.30-033.28, travailleuse frontalière (BIS 98.47.28-997.65).
GSM : 0474 12 34 56 — tél. bureau : 02/513.23.45 — tél. : 0475123456 — Liège : 04 223 45 67.
Compte : IBAN BE68 5390 0754 7034. Carte d'identité n° 591-1917064-58. Véhicule 1-ABC-123.
Adresse : rue de la Loi 16, B-1000 Bruxelles. Rappel : NISS 85073003328.
"""


LETTER_SECRETS = ("85.07.30-033.28", "85073003328", "98.47.28-997.65", "0474 12 34 56", "02/513.23.45",
                  "0475123456", "04 223 45 67", "BE68 5390 0754 7034", "591-1917064-58", "1-ABC-123", "B-1000")


def test_belgian_letter_is_fully_anonymised():
    result = Anonymizer(countries="BE,FR").anonymize(LETTER)
    text = result.text
    for secret in LETTER_SECRETS:
        assert secret not in text
        assert secret not in repr(result.report)
    # Même personne, deux écritures : même balise / same person, two spellings: same placeholder.
    assert text.count("[NISS_1]") == 2
    assert "[NISS_2]" in text
    # Champ « Adresse : » (1.0.1) : toute l'adresse, rue comprise, jusqu'à la fin de phrase.
    # "Adresse:" field (1.0.1): the whole address, street included, up to the sentence end.
    for placeholder in ("[TEL_1]", "[TEL_2]", "[TEL_3]", "[TEL_4]", "[IBAN_1]", "[CNI_1]", "[PLAQUE_1]",
                        "Adresse : [ADRESSE_1]. Rappel"):
        assert placeholder in text
    assert result.report["irreversible"] is True


def test_auto_mode_anonymises_the_belgian_letter(anonymizer):
    result = anonymizer.anonymize(LETTER)
    assert "BE" in result.report["countries"]
    assert not [secret for secret in LETTER_SECRETS if secret in result.text]


def test_enterprise_number_follows_the_company_policy():
    text = "ACME SA — BCE 0403.019.261 — TVA BE 0403.019.261 — numéro d'entreprise 0428.759.497."
    kept = Anonymizer(countries="BE").anonymize(text)
    assert kept.text == text
    assert kept.report["kept_by_policy"] == {"BE_BCE": 3}
    masked = Anonymizer(countries="BE", company_ids="mask").anonymize(text)
    # Numéro d'entreprise et TVA : même numéro, même balise / same number, same placeholder.
    assert masked.text == "ACME SA — BCE [BCE_1] — TVA [BCE_1] — numéro d'entreprise [BCE_2]."


def test_sole_trader_enterprise_number_is_personal():
    result = Anonymizer(countries="BE").anonymize("Jan Peeters, eenmanszaak, ondernemingsnummer 0403.019.261.")
    assert "0403.019.261" not in result.text


@pytest.mark.parametrize("text", [
    "Numéro d'entreprise : 0428.759.497",
    "N° d'entreprise (BCE) : 0428.759.497",
    "no d'entreprise 0428 759 497",
    "KBO-nr. 0428.759.497",
    "Unternehmensnummer 0428.759.497",
    "TVA be 0428.759.497",
])
def test_labelled_enterprise_numbers(text):
    # Libellés ambigus ancrés dans le motif, et non mots de contexte / ambiguous labels anchored in the pattern.
    spans = Anonymizer(countries="BE").analyze(text).spans
    assert [(s.label, s.value) for s in spans] == [("BE_BCE", "0428759497")]


def test_quebec_enterprise_number_is_not_belgian():
    assert Anonymizer(countries="BE").analyze("Numéro d'entreprise du Québec (NEQ) : 1173456789").spans == []


def test_weak_identifiers_need_context():
    a = Anonymizer(countries="BE,FR")
    assert "591-1917064-58" in a.anonymize("Référence interne 591-1917064-58.").text
    assert a.anonymize("Carte eID 591-1917064-58.").text == "Carte eID [CNI_1]."
    assert a.anonymize("IBAN ancien : 539-0075470-34.").text == "IBAN ancien : [RIB_1]."
    assert "0475123456" in a.anonymize("Commande 0475123456 livrée.").text


def test_invalid_or_ambiguous_numbers_are_kept():
    a = Anonymizer(countries="BE")
    text = "Dossier 85.07.30-033.29, échéance 02/03/2024, code 1-AB-123, total 0474."
    assert a.anonymize(text).text == text


def test_explicit_country_works_without_france():
    a = Anonymizer(countries="BE")
    assert [p.id for p in a.packs] == ["INTL", "BE"]
    assert a.anonymize("INSZ 85.07.30-033.28").text == "INSZ [NISS_1]"


def test_neutral_and_english_labels():
    text = "NISS 85.07.30-033.28"
    assert Anonymizer(countries="BE", neutral_labels=True).anonymize(text).text == "NISS [ID_NATIONAL_1]"
    english = Anonymizer(countries="BE", label_language="en", company_ids="mask")
    assert english.anonymize("BCE 0403.019.261").text == "BCE [CBE_1]"


@pytest.mark.parametrize(("unit", "repeat"), [("1", 100_000), ("12 ", 35_000), ("1.2-", 25_000),
                                              ("BCE n° ", 15_000), ("n° d'entreprise ", 10_000), ("04 ", 35_000),
                                              ("B-1000 ", 15_000)])
def test_hostile_inputs_stay_linear(unit, repeat):
    # Quantificateurs bornés : pas d'explosion du retour arrière / bounded quantifiers, no backtracking blow-up.
    a = Anonymizer(countries="BE")
    t0 = perf_counter()
    a.analyze(unit * repeat)
    assert perf_counter() - t0 < 5.0


def test_spreadsheet_column_restores_stripped_niss(anonymizer):
    # L'en-tête « NISS » force le contexte de la colonne / the header forces the column context.
    header_groups = anonymizer.context_groups("NISS")
    assert "BE:niss" in header_groups
    per_cell, analysis = anonymizer.analyze_segments(["NISS", "5060712337", "1234"],
                                                     [frozenset(), header_groups, header_groups])
    assert "BE" in analysis.countries
    assert [s.label for s in per_cell[1]] == ["BE_NISS"]
    assert per_cell[1][0].value == "05060712337"
    assert per_cell[2] == []


def test_header_lexicon_claims_no_foreign_column():
    headers = {word for words in load_pack("BE").headers.values() for word in words}
    assert not headers & GENERIC_HEADERS
    # NISS belge et portugais : même entité, même balise affichée / same entity, same displayed placeholder.
    assert set(foreign_header_conflicts("BE")) <= {"niss"}
