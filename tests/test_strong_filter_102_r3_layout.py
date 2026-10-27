"""Filtre fort 1.0.2, troisième tour, mise en page : numéro ou plaque coupés par un saut de ligne (règles BREAK_NUMBER,
BREAK_PLATE), voie coupée en fin de ligne (STREET_WRAP, CRLF comme LF), étiquette d'adresse devant un code postal
(ADDRESS_LABEL), numéro de bureau en fin de ligne (OFFICE_NUMBER), code après une voie (CODE_HEAD).

Strong filter 1.0.2, third round, layout: a number or a plate split by a line break (BREAK_NUMBER, BREAK_PLATE), a
street cut at the line end (STREET_WRAP, CRLF exactly like LF), an address label before a postcode (ADDRESS_LABEL), an
office number ending a line (OFFICE_NUMBER), a code after a street (CODE_HEAD). Chaque cas tourne sur le noyau Rust
(s'il est installé) et sur la référence Python. Every case runs on the Rust core (when installed) and on the Python
reference. Données fictives (clés calculées) / fictitious data.
"""

from __future__ import annotations

import pytest

from gdprguardian import Anonymizer, _native, _text

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]
_MODES = ("fort", "essentiel")


@pytest.fixture(scope="module", params=_ENGINES)
def native(request) -> bool:
    return request.param


def _engine(native: bool, mode: str = "fort") -> Anonymizer:
    anonymizer = Anonymizer(countries=("FR",), native=native, mode=mode)
    assert anonymizer.native == native
    return anonymizer


# --- BREAK_NUMBER : numéro prouvé coupé par un saut de ligne / a proven number split by a line break ---------------


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("breaker", ["\n", "\r\n"])
@pytest.mark.parametrize("text, secrets, tag", [
    ("Appelez le 07{br}-93-28-03-42 avant vendredi.", ["07", "93-28"], "[TEL_1]"),
    ("Tél. 07.42.66.93{br}.70 merci", ["07.42", ".70"], "[TEL_1]"),
    ("Mon adresse IP est 5.46{br}.239.23, au cas où.", ["5.46", "239.23"], "[IP_1]"),
    ("Mon adresse IP est 109{br}.230.125.136, au cas où.", ["109", "230.125"], "[IP_1]"),
    ("numéro de sécurité sociale 1{br}85059912345607, merci", ["85059912345607"], "[NIR_1]"),
    ("Micro-entrepreneur – SIREN 12345{br}6782", ["12345", "6782"], "[SIREN_1]"),
    ("IBAN FR{br}7612345678901234567890104", ["7612345678901234567890104"], "[IBAN_1]"),
    # « FR76 » seul a une clé juste par hasard : ce n'est pas un IBAN déjà entier / "FR76" alone is not a whole IBAN.
    ("IBAN : FR76{br}12345678901234567890104{br}BIC : AGRIFRPP882", ["FR76", "12345678901234567890104"], "[IBAN_1]"),
    ("Véhicule immatriculé WB 864{br}SW (ancienne)", ["WB", "864", "SW"], "[PLAQUE_1]"),
    ("Véhicule immatriculé DV-185{br}-FP le 2 mai", ["DV", "185", "FP"], "[PLAQUE_1]"),
    ("immatriculation SF-112-{br}ES{br}Titulaire", ["SF", "112", "ES"], "[PLAQUE_1]"),
    ("(ancienne immatriculation 8871{br}LZ 59), première", ["8871", "LZ 59"], "[PLAQUE_1]"),
])
def test_number_split_by_a_line_break_is_rebuilt(native, mode, breaker, text, secrets, tag):
    text = text.format(br=breaker)
    out = _engine(native, mode).anonymize(text).text
    assert tag in out, out
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("breaker", ["\n", "\r\n"])
@pytest.mark.parametrize("text", [
    "Total 12{br}-5 articles",                      # aucun numéro prouvé / no proven number
    "Ligne 1 : 123{br}Ligne 2 : 456",               # deux lignes indépendantes / two separate lines
    "Dossier 56 78{br}75011 Paris",                 # code postal et ville en tête / postcode and town lead
    "Réf 1234{br}12345;abc;def",                    # ligne de tableau CSV / a CSV row
    "Réf. 12-34{br}.56 fin",                        # ni téléphone ni IPv4 / neither a phone nor an IPv4
])
def test_two_independent_lines_are_not_joined(native, breaker, text):
    norm, _, _ = _text.prepare(text.format(br=breaker), native=native)
    assert "\n" in norm, norm


def test_crlf_and_lf_give_the_same_text(native):
    engine = _engine(native)
    for text in ("Appelez le 07{br}-93-28-03-42.", "SIREN 12345{br}6782",
                 "Il habite au 59{br}place Carnot, 81000 Albi."):
        lf = engine.anonymize(text.format(br="\n")).text
        crlf = engine.anonymize(text.format(br="\r\n")).text
        assert lf.replace("\n", "") == crlf.replace("\r\n", "").replace("\n", ""), (lf, crlf)


# --- Adresses coupées / split addresses --------------------------------------------------------------------------


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("breaker", ["\n", "\r\n"])
@pytest.mark.parametrize("text, secrets", [
    ("Il habite au 59{br}place de la République, 75011 Paris.", ["59", "République"]),
    ("domicilié 84 rue{br}des Lilas, 97600 Mamoudzou, que j'ai vu", ["84", "Lilas"]),
    ("le logement situé 41 impasse{br}de la Mairie – 68100 Mulhouse.", ["41", "Mairie"]),
    ("Il habite au 116 allée{br}du Moulin, 75011 Paris.", ["116", "Moulin"]),
    # COMMUNE_WRAP : commune vérifiée en tête de la ligne suivante / verified town heading the next line.
    ("domicilié 84 rue des Lilas, 97600{br}Mamoudzou, que j'ai vu", ["84", "Lilas", "97600", "Mamoudzou"]),
    ("Vendeur : 158 place des Vignes, 12320{br}Conques-en-Rouergue{br}Acheteur", ["158", "12320", "Conques"]),
])
def test_street_split_by_a_line_break_is_one_address(native, mode, breaker, text, secrets):
    out = _engine(native, mode).anonymize(text.format(br=breaker)).text
    assert out.count("[ADRESSE_1]") == 1, out
    for secret in secrets:
        assert secret not in out, out


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text, expected", [
    ("Bureau 1\nrue de la Paix, 75002 Paris", "Bureau 1\n[ADRESSE_1]"),
    ("Bureau 1\r\nrue de la Paix, 75002 Paris", "Bureau 1\r\n[ADRESSE_1]"),
    ("Salle 12\nboulevard Voltaire, 75011 Paris", "Salle 12\n[ADRESSE_1]"),
])
def test_office_number_stays_out_of_the_address(native, mode, text, expected):
    assert _engine(native, mode).anonymize(text).text == expected


@pytest.mark.parametrize("text, code", [
    ("Livraison au 12 rue des Lilas SKU-123456 demain.", "SKU-123456"),
    ("domicilié 4 rue Haute FAC-2024-0012", "FAC-2024-0012"),
])
def test_address_does_not_swallow_the_next_code(native, text, code):
    fort = _engine(native, "fort").anonymize(text).text
    assert "[ADRESSE_1] [IDENTIFIANT_1]" in fort, fort
    essentiel = _engine(native, "essentiel").anonymize(text).text
    assert f"[ADRESSE_1] {code}" in essentiel, essentiel


def test_glued_postcode_is_not_a_code_head(native):
    # Cinq chiffres après le tiret : un code postal collé, la voie garde son dernier mot (forme vue sur BOAMP,
    # adresse fictive). Five digits after the dash: a glued postcode, the street keeps its last word (fictitious).
    out = _engine(native).anonymize("sise 87 route du Moulin de la Croix-99900 Val-des-Nuages et").text
    assert out.startswith("sise [ADRESSE_1]") and "Croix" not in out and "Moulin" not in out, out


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("text", [
    "Adresse du salarié : 75011 Paris",
    "Adresse du domicile : 69003 Lyon",
    "Adresse personnelle du client : 75011 Paris\nTél : 06 12 34 56 78",
])
def test_personal_address_label_then_postcode_and_town_leaves_nothing_readable(native, mode, text):
    out = _engine(native, mode).anonymize(text).text
    assert "[ADRESSE_1]" in out, out
    assert "75011" not in out and "69003" not in out and "Paris" not in out and "Lyon" not in out, out


@pytest.mark.parametrize("text", [
    "Adresse : 75017 PARIS",                    # étiquette seule : adresse d'organisation (§ 2) / bare label
    "Adresse de livraison : 69003 Lyon",        # l'étiquette ne nomme personne / names nobody
    "Code adresse : 12345\nfin",                # pas de commune / no town
    "Adresse IP : 10.0.0.1",                    # pas un code postal / not a postcode
])
def test_address_label_without_postcode_and_town_adds_no_address(native, text):
    out = _engine(native).anonymize(text).text
    assert "[ADRESSE" not in out, out
