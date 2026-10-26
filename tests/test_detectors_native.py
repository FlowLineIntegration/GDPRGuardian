"""Détecteurs natifs (Rust) : résultats identiques aux détecteurs Python de référence.

Native (Rust) detectors: results identical to the reference Python detectors. Adresses, organisations, e-mails,
IBAN, MRZ et dates de naissance liées au NIR : même zones (positions, valeurs, scores, priorités, politique), sur
le corpus, sur des textes générés (Unicode piégeux compris) et à travers le moteur complet.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gdprguardian import Anonymizer, _native
from gdprguardian._text import fold, normalize
from gdprguardian.engine import DetectionContext, markdown_table_zones
from gdprguardian.heuristics._lexicon import UPPER
from gdprguardian.types import Span

core = pytest.importorskip("gdprguardian_core")
if not _native.available():
    pytest.skip("noyau Rust désactivé / Rust core disabled", allow_module_level=True)

ANON = Anonymizer(countries=("FR",))
PURE = Anonymizer(countries=("FR",), native=False)
NATIVE = ANON.settings
PYTHON = replace(NATIVE, native=False)
DETECTORS = {type(d).__name__: d for pack in ANON.packs for d in ANON._detectors[pack.id]}
PORTED = ("FrenchAddressDetector", "OrganizationDetector", "EmailDetector", "IbanDetector", "MrzDetector",
          "NirBirthDateDetector")
CORPUS = Path(__file__).resolve().parents[1] / "datasets" / "fr" / "docs"
FUZZ = settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])

# Caractères piégeux : casse spéciale (İ, ı, ſ, K), diacritiques combinants, espaces et séparateurs Unicode,
# invisibles, chiffres non ASCII, astraux, idéogrammes. Tricky characters: special case mappings, combining marks,
# Unicode spaces and separators, invisibles, non-ASCII digits, astral characters, ideographs.
TRAPS = ["İ", "ı", "ſ", "K", "Å", "ß", "Σ", "ς", "ʕ", "É", "Î", "Â", "é", "́", "̧", " ", " ",
         "　", "\u0085", " ", "​", "­", "﻿", "’", "–", "—", "²", "①", "Ⅻ", "𝟏", "٣",
         "😀", "𝔸", "🄰", "Ⓐ", "日本", "\U00020000", "\U000e0041", "\t", "\r\n", "\n", "\x0b", "\x1c", "_", "ª"]


def _key(span: Span) -> tuple:
    return (span.start, span.end, span.entity, span.label, span.source, span.value, round(span.score, 9),
            span.priority, span.personal, span.forms, span.propagate)


def _contexts(text: str, normalized: bool = True, found: list[Span] | None = None) -> list[DetectionContext]:
    """Deux contextes identiques sauf `Settings.native` / two contexts that differ only by `Settings.native`."""
    norm = normalize(text)[0] if normalized else text
    folded = fold(norm)
    hits = ANON._scan_keywords(folded)
    zones = markdown_table_zones(norm, ANON.context_groups)
    contexts = []
    for settings_ in (NATIVE, PYTHON):
        ctx = DetectionContext(norm, folded, hits, ("FR",), "fr", settings_, zones=zones)
        ctx.found = list(found or ())
        contexts.append(ctx)
    return contexts


def _assert_same(name: str, text: str, normalized: bool = True, found: list[Span] | None = None) -> list[tuple]:
    native_ctx, python_ctx = _contexts(text, normalized, found)
    detector = DETECTORS[name]
    native = [_key(s) for s in detector.detect(native_ctx)]
    python = [_key(s) for s in detector.detect(python_ctx)]
    assert native == python, (name, text)
    return native


def _pieces(*groups: list[str]) -> st.SearchStrategy[str]:
    parts = st.one_of(*(st.sampled_from(g) for g in groups), st.sampled_from(TRAPS), st.text(max_size=6))
    return st.lists(parts, max_size=40).map("".join)


def test_native_twins_are_active():
    assert _native.available()
    for name in PORTED:
        assert DETECTORS[name]._native is not None, name


# --- Table Unicode / Unicode table -----------------------------------------------------------------------------


def _all_characters() -> str:
    every = _native.code_points(0, 0x110000)
    return every[:0xD800] + every[0xE000:]  # sans substituts / without surrogates


def test_unicode_table_matches_the_interpreter_on_every_code_point():
    """Chaque classe lue par les détecteurs, pour chaque point de code, par une méthode indépendante (`str`, pas
    `re`) ; la table est l'unique table du noyau. Every class the detectors read, for every code point, through
    an independent method (`str` predicates, not `re`); the table is the core's single table.
    """
    table = _native.unicode_table()
    assert table is _native.unicode_tables()
    chars = _all_characters()
    capital = re.compile(f"[{UPPER}]")
    T = core.UnicodeTables
    used = T.WORD | T.ALNUM | T.LETTER | T.DECIMAL | T.SPACE | T.UPPER | T.LOWER | T.DIGIT | T.CAPITAL
    actual = [flags & used for flags in table.flags_of(chars)]
    expected = [
        (T.WORD if c.isalnum() or c == "_" else 0) | (T.ALNUM if c.isalnum() else 0)
        | (T.LETTER if c.isalnum() and not c.isdecimal() else 0) | (T.DECIMAL if c.isdecimal() else 0)
        | (T.SPACE if c.isspace() else 0) | (T.UPPER if c.isupper() else 0) | (T.LOWER if c.islower() else 0)
        | (T.DIGIT if c.isdigit() else 0) | (T.CAPITAL if capital.fullmatch(c) else 0)
        for c in chars]
    wrong = [f"U+{ord(c):04X}" for c, a, e in zip(chars, actual, expected, strict=True) if a != e]
    assert not wrong, wrong[:20]


def test_regex_classes_are_the_str_predicates():
    # Les détecteurs Python emploient `\w`, `\d`, `\s` ; la table vient des prédicats `str` (test ci-dessus).
    # The Python detectors use `\w`, `\d`, `\s`; the table checked above comes from the `str` predicates.
    chars = _all_characters()
    for pattern, predicate in ((r"\w", lambda c: c.isalnum() or c == "_"), (r"\d", str.isdecimal),
                               (r"\s", str.isspace)):
        assert set(re.findall(pattern, chars)) == {c for c in chars if predicate(c)}, pattern


def test_case_insensitive_letters_match_re_ignorecase():
    table = _native.unicode_table()
    chars = _all_characters()
    for letter in "abcdefghilmnopqrstuxâéî":
        expected = set(re.findall(re.escape(letter), chars, re.IGNORECASE))
        candidates = expected | set(chars[:0x2200]) | {"İ", "ı", "ſ", "K", "Å", "ﬀ", "ﬅ"}
        assert {c for c in candidates if table.case_insensitive_eq(letter, c)} == expected, letter
    # Les classes des motifs Rust sont des unions de lettres / the Rust patterns' classes are unions of letters.
    for klass, letters in (("[aâ]", "aâ"), ("[ée]", "ée"), ("[iî]", "iî"), ("[a-h]", "abcdefgh")):
        expected = set(re.findall(klass, chars, re.IGNORECASE))
        assert expected == {c for c in expected | set(chars[:0x2200]) if any(
            table.case_insensitive_eq(letter, c) for letter in letters)}, klass


def test_detectors_refuse_another_table_type():
    # Les détecteurs n'acceptent que la table unique du noyau / detectors only take the core's single table.
    with pytest.raises(TypeError):
        core.EmailDetector(b"\x00" * 10)


# --- Corpus -----------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def corpus() -> list[str]:
    paths = sorted(CORPUS.glob("*.md"))
    if not paths:
        pytest.skip("corpus absent / corpus missing")
    return [p.read_text(encoding="utf-8") for p in paths]


def test_corpus_detectors_identical(corpus):
    """Les 1 000 documents : chaque détecteur, natif et Python, sur le contexte du moteur / every document."""
    packs = frozenset(p.id for p in ANON.packs)
    count = 0
    for text in corpus:
        native_ctx, python_ctx = _contexts(text)
        ANON._detect(native_ctx, {}, packs, extras=True)  # zones déjà trouvées (NIR…) / spans already found
        python_ctx.found = list(native_ctx.found)
        for name in PORTED:
            native = [_key(s) for s in DETECTORS[name].detect(native_ctx)]
            assert native == [_key(s) for s in DETECTORS[name].detect(python_ctx)], name
            count += len(native)
    assert count > 5000  # le corpus exerce vraiment les détecteurs / the corpus really exercises them


def test_corpus_engine_identical(corpus):
    for text in corpus[:250]:
        left, right = ANON.anonymize(text), PURE.anonymize(text)
        assert [_key(s) for s in left.analysis.spans] == [_key(s) for s in right.analysis.spans]
        assert left.text == right.text
        assert ({k: v for k, v in left.report.items() if k not in ("timings_ms", "native")}
                == {k: v for k, v in right.report.items() if k not in ("timings_ms", "native")})


# --- Adresses / addresses ----------------------------------------------------------------------------------------

ADDRESS = ["12", "12 bis", "3", "40", "7-9", "12/14", "8 Ter", "5a", "rue", "Rue", "RUE", "avenue", "av.", "Av",
           "bd", "boulevard", "place", "impasse", "allée", "chemin", "route", "quai", "lieu-dit", "lieu dit",
           "zone industrielle", "rés.", "de la", "du", "des", "de l'", "d'", "Paix", "Victor Hugo",
           "Général Leclerc", "8 Mai 1945", "Champs-Élysées", "l'Église", "Arc", "grande", "depuis", "et", ",", ", ",
           " ", "  ", "\n", "\r\n", "\t", "-", " - ", ";", "75002", "75017", "69003", "13008", "20000", "97400",
           "98000", "01000", "00100", "99999", "123456", "75002.5", "Paris", "PARIS", "Lyon", "Saint-Denis",
           "St-Denis", "Fort-de-France", "Bourg-en-Bresse", "Levallois-Perret", "Marseille", "Cedex", "CEDEX 08",
           "cedex 3", "2e", "1er", "3ème", "2eme", "BP 42", "B.P. 12", "BP.7", "CS 70001", "TSA 1234",
           "Case postale 12", "boîte postale 5", "BOÎTE POSTALE 9", "Bât. B", "Bâtiment C", "Résidence Les Lilas",
           "Appartement 12", "Appt. 4", "Esc. A", "étage 3", "Immeuble Le Phénix", "Tour B", "domicilié",
           "demeurant", "sis", "sise", "réside", "habite", "adresse", "(", ")", "Lyon (69003)", "Rennes", ".",
           # Règles « rules2 » : lieux-dits, adjectifs, boîtes en minuscules, Cédex, tirets, cellules, communes.
           "Le Bourg", "la Testière", "Kertestou", "Grande", "Petite Rue", "Contre", "ZAC des Prés", "Parc", "Hôtel",
           "Hôtel de Ville", "Cédex", "cédex 2", "Bp 107", "bp 12", "cs 41234", "–", "—", "\n– ", "| ", " |",
           "Adresse : ", ":", "l'adresse", "Vouziers", "VOUZIERS", "Cordialement", "Monsieur", "12a,", "3 ter",
           "Contour", "lieutenant", "Arts et Métiers", "Villa Essai", "Le Village",
           # Lignes d'adresse : segments séparés, numéros en intervalle, mots d'adresse / address lines.
           "Rue des prés", "rue des Essais", "Gymnase Essai", ",,", "18-20", "3/5b", "RD 901", "CD 12", "Cedex 02",
           "un voisin", "| Adresse :"]


@FUZZ
@given(_pieces(ADDRESS), st.booleans())
def test_addresses_identical(text, normalized):
    _assert_same("FrenchAddressDetector", text, normalized)


@pytest.mark.parametrize("text", [
    "Il habite au 12 bis rue de la Paix, 75002 Paris depuis 2010.",
    "Bât. B, Résidence Les Lilas, 5 allée des Roses 13008 Marseille",
    "Appartement 12\r\n3 rue des Lilas\r\n33000 Bordeaux",
    "Envoyer à BP 42 - 69441 Lyon Cedex 03. Courrier : CS 70001 - 75381 Paris Cedex 08",
    "Rendez-vous à Lyon (69003) ; elle est domiciliée rue du Général Leclerc à Rennes.",
    "Le colis est au 40 avenue de la Grande Armée 75017.",
    unicodedata.normalize("NFD", "Il habite 12 rue de la République, 69002 Lyon depuis 2010."),
    "Tour İmmeuble ſis 4 rue Kléber, 67000 Strasbourg",
    "12\nrue de la Paix\n75002 Paris",
    "Adresse : 2 la Testière 50700 Saussemesnil ; Adresse : La Testière 16570 Marsac",
    "| Adresse | Le Bourg, 20250 Corte |\nM. Paul Essai\nLe Bourg\n29200 Brest\nTél.",
    "Livré à l'adresse Le Bourg, 66000 Perpignan. Cordialement\n29200 Brest",
    "Adresse : 14 grande rue 92350 Le Plessis-Robinson\nAdresse : 6 Boulevard Paul et Jeanne Essai 05000 Gap",
    "Adresse : BP2031 - 17 rue Paul Essai, 97488 Saint-Denis Cédex\nZac Essai Bp 107 17700 Surgères",
    "Adresse : ZAC des Essais - 4 rue du Verger, 57530 Ars-Laquenexy ; 6 rue de Testval, VOUZIERS.",
    "Il habite au 35 allée des Essais\n– 59000 Lille. Adresse : 5 Contour des Essais CS 41234, 35044 Rennes cedex",
    "Adresse : 75017 PARIS ; 29 rue du lieutenant Testeur, 57400 Sarrebourg ; "
    "41 Route De Testval l'Essai a 06600 Antibes",
    "Adresse : Gymnase Essai, rue des Essais, 38000 Grenoble\nAdresse : BP 71234 Cedex 02, 49000 ANGERS\n"
    "Adresse : CS 41234,, 60200 Compiègne cedex\nAdresse : 18-20 Viaduc Essai - RD 901, 54000 Nancy Cedex",
    "Livré chez un voisin, 33000 Bordeaux. Jean Essai, rue des prés - 38000 Grenoble | Adresse : , 75017 PARIS",
    "> Commande 12345678, colis 1L00000000000, toujours pas livré à l'adresse Le Bourg, 66000 PERPIGNAN. Merci. "
    "Une très longue ligne de prose sans retour, puis 12 la Testière 50700 Saussemesnil et 175 Essai 50700 Valognes",
])
def test_address_samples_identical(text):
    _assert_same("FrenchAddressDetector", text)


# --- Organisations ---------------------------------------------------------------------------------------------

ORGS = ["SAS", "SARL", "S.A.S.", "S.A.", "SA", "EI", "EIRL", "SCI", "GmbH", "AG", "Ltd.", "Inc.", "S.p.A.", "B.V.",
        "e.V.", "& Fils", "et Fils", "& Associés", "et Associés", "Conseil", "Group", "Holding", "société", "Société",
        "cabinet", "Cabinet", "groupe", "la société", "Ets", "Banque", "étude", "Boulangerie", "Dupont", "Martin",
        "Petit", "Durand", "Acme", "Globex", "L'Oréal", "d'Artois", "Les Jardins", "du Moulin", "de la Fontaine",
        "de l'Est", "123", "de", "du", "des", "et", "&", "and", "l'", "d'", "Le", "La", "M.", "Mme", "Hier", "(", ")",
        "«", "»", "“", "\"", "'", "[", ",", ".", "-", " ", "  ", "\n", "Associées", "Compagnie", "Co", "Söhne",
        "Frères", "entrepreneur individuel", "Dupont-Martin", "ACME", "X" * 45]


@FUZZ
@given(_pieces(ORGS), st.booleans())
def test_organisations_identical(text, normalized):
    _assert_same("OrganizationDetector", text, normalized)


@pytest.mark.parametrize("text", [
    "Le contrat lie Acme SAS et Globex SARL. Volkswagen AG, Siemens GmbH et Philips N.V. sont cités.",
    "La SARL Durand et Fils et le Cabinet Martin & Associés sont mandatés.",
    "Dupont SARL a livré. Jean Dupont EI facture. Petit SARL et la société Petit.",
    "Les Jardins de Provence SARL ; la SCI du Moulin ; (Acme SAS) ; « Globex » SA.",
    "Acme SAS, entrepreneur individuel, facture ses prestations.",
])
def test_organisation_samples_identical(text):
    _assert_same("OrganizationDetector", text)


# --- E-mails --------------------------------------------------------------------------------------------------

EMAILS = ["jean", "Jean.Dupont", ".dupont", "dupont.", "a..b", "zoé", "ÉLISE", "x_y", "a+b", "a%b", "a-b", "@", "@@",
          "exemple", "Exemple", "mail", "sous-domaine", "é", "Σ", "ʕ", "fr", "FR", "com", "c", "c0m", "x" * 63,
          "y" * 64, "z" * 25, "q" * 24, ".", "..", "-", "\n", " ", "@exemple.fr", "jean@exemple.fr",
          "a@b.c.d.e.f.g.h.i.fr", "1" * 70]


@FUZZ
@given(_pieces(EMAILS), st.booleans())
def test_emails_identical(text, normalized):
    _assert_same("EmailDetector", text, normalized)


@pytest.mark.parametrize("text", [
    "Écrire à jean.dupont@exemple.fr ou à Zoé.Ñúñez@Sous-Domaine.Exemple.COM.",
    "abc\n@x.fr, .\n@y.fr, ..a@b.fr, a.@b.fr, mail.example.c0m@x, " + "x" * 70 + "@exemple.fr",
    "a@" + "b" * 63 + ".fr a@" + "b" * 64 + ".fr a@b." + "c" * 24 + " a@b." + "c" * 25,
    "ΣΑΣ@ΕΞΑΜΠΛΣ.fr İ@İ.fr",
    # « ʕ » : minuscule (Ll) pour Unicode 15, lettre sans casse (Lo) depuis Unicode 16 ; le sigma final qui le
    # précède ou le suit dépend donc de la version d'Unicode. Lowercase (Ll) in Unicode 15, uncased (Lo) since
    # Unicode 16: the final sigma next to it depends on the Unicode version.
    "x@aΣʕ-b.fr x@ʕΣ-b.fr x@ΣʕΣ.fr",
])
def test_email_samples_identical(text):
    _assert_same("EmailDetector", text)


def test_email_domains_lowercase_like_the_interpreter():
    """Chaque caractère de mot, seul et contre un sigma majuscule : `str.lower` de l'interpréteur.

    Every word character, alone and next to a capital sigma: the interpreter's `str.lower`.
    """
    chars = [c for c in _all_characters() if c.isalnum() or c == "_"]
    for template in ("x@{c}b.fr", "x@aΣ{c}-b.fr", "x@{c}Σ-b.fr"):
        for i in range(0, len(chars), 4096):
            _assert_same("EmailDetector", " ".join(template.format(c=c) for c in chars[i:i + 4096]), False)


# --- IBAN -------------------------------------------------------------------------------------------------------


def _iban(country: str, bban: str) -> str:
    """IBAN valide pour un BBAN donné (clé ISO 7064 MOD 97-10) / valid IBAN for a BBAN."""
    numeric = "".join(str(int(c, 36)) for c in bban + country + "00")
    return f"{country}{98 - int(numeric) % 97:02d}{bban}"


VALID_IBANS = [_iban("FR", "30006000011234567890189"), _iban("DE", "370400440532013000"),
               _iban("GB", "NWBK60161331926819"), _iban("BE", "096123456769"), _iban("NL", "ABNA0417164300"),
               _iban("MC", "11222000010123456789030"), _iban("NO", "86011117947")]


def _layouts(iban: str) -> list[str]:
    groups = [iban[i:i + 4] for i in range(0, len(iban), 4)]
    wrong = iban[:-1] + ("0" if iban[-1] != "0" else "1")
    return [iban, " ".join(groups), "-".join(groups), iban.lower(), wrong, " ".join(wrong[i:i + 4] for i in
                                                                                     range(0, len(wrong), 4))]


IBANS = [layout for iban in VALID_IBANS for layout in _layouts(iban)] + [
    "IBAN", "IBAN :", "RIB", "iban", "FR", "76", "FR76", " ", "-", "\n", "X", "a", "é", "0", "FR76 3000"]


@FUZZ
@given(_pieces(IBANS), st.booleans())
def test_ibans_identical(text, normalized):
    _assert_same("IbanDetector", text, normalized)


@pytest.mark.parametrize("text", [f"IBAN : {iban}." for iban in (VALID_IBANS[0], *_layouts(VALID_IBANS[2]))] + [
    "Compte FR76 3000 6000 0112 3456 7890 188 et FR7630006000011234567890189X et xFR76 3000 6000 0112 3456 7890 189",
    "IBAN FR763000600001123456789018 9 ; RIB : FR76-3000-6000-0112-3456-7890-188é",
])
def test_iban_samples_identical(text):
    _assert_same("IbanDetector", text)


# --- MRZ ----------------------------------------------------------------------------------------------------------

LINE1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
LINE2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
MRZ = [LINE1, LINE2, LINE1[:27], LINE1 + "<<<", "I<UTO" + "<" * 25, "X" + LINE1[1:], LINE2[:28], "\n", "\r\n",
       " \n", "\t", "  ", "<", "<<<<", "ABC", "123"]


@FUZZ
@given(_pieces(MRZ), st.booleans())
def test_mrz_identical(text, normalized):
    _assert_same("MrzDetector", text, normalized)


@pytest.mark.parametrize("text", [
    f"Passeport :\n  {LINE1}\r\n{LINE2}\nfin", f"{LINE1}\n{LINE2}\n{LINE1}", f"{LINE1}{LINE1}\n{LINE2}",
    f"{LINE1}\n{LINE2}{LINE2}\n{LINE1}", f"\n{LINE1}  \n  {LINE2[:30]}",
])
def test_mrz_samples_identical(text):
    _assert_same("MrzDetector", text)


# --- Dates de naissance liées au NIR / NIR birth dates ------------------------------------------------------------

DATES = ["03/03/1985", "3/3/1985", "03.05.1985", "03-05-1985", "31/05/1985", "11/1/2019", "1/10/2020", "29/02/1985",
         "03/05/2085", "1er mai 1985", "3 mai 1985", "12 mai 1953", "1er  mars   1986", "15 decembre 1885",
         "3 mai 1985", "3　mai 1985", "3\u0085mai 1985", "3 Mai 1985", "03/05/19851", "103/05/1985",
         "Né le ", "le ", " ", "\n", "/", ".", "-", "mai", "1985", "05"]
NIRS = st.lists(st.sampled_from(["185057800608491", "269054958815780", "186056064342490", "1850", "", "X1985"])
                | st.from_regex(r"[12][0-9]{14}", fullmatch=True), max_size=3)


def _nir_spans(values: list[str]) -> list[Span]:
    return [Span(0, 0, "NATIONAL_ID", "NIR", "FR_NIR", 1.0, 100, value) for value in values]


@FUZZ
@given(_pieces(DATES), NIRS, st.booleans())
def test_nir_birth_dates_identical(text, nirs, normalized):
    _assert_same("NirBirthDateDetector", text, normalized, _nir_spans(nirs))


def test_nir_birth_date_samples_identical():
    text = "Né le 03/05/1985 (1er mai 1985), NIR 1 85 05 78 006 084 91 ; rendez-vous le 3 mai 1986."
    assert len(_assert_same("NirBirthDateDetector", text, found=_nir_spans(["185057800608491"]))) == 2


# --- Moteur complet, segments, réglages / whole engine, segments, settings ----------------------------------------

ALL = ADDRESS + ORGS + EMAILS + IBANS + MRZ + DATES + ["Jean Dupont", "NIR 1 85 05 78 006 084 91", "M. Martin"]


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_pieces(ALL))
def test_engine_identical(text):
    left, right = ANON.anonymize(text), PURE.anonymize(text)
    assert [_key(s) for s in left.analysis.spans] == [_key(s) for s in right.analysis.spans]
    assert left.text == right.text


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(_pieces(ALL), min_size=1, max_size=5))
def test_segments_identical(cells):
    left = ANON.analyze_segments(cells)[0]
    right = PURE.analyze_segments(cells)[0]
    assert [[_key(s) for s in cell] for cell in left] == [[_key(s) for s in cell] for cell in right]


def test_native_false_never_calls_rust(monkeypatch):
    class Refuse:
        def __getattr__(self, name):
            raise AssertionError(f"jumeau Rust appelé / Rust twin called: {name}")

    text = "Acme SAS, 12 rue de la Paix 75002 Paris, jean@ex.fr, FR7630006000011234567890189, né le 03/05/1985."
    expected = [_key(s) for s in ANON.analyze(text).spans]
    # Les détecteurs du moteur pur Python eux-mêmes (les jumeaux sont partagés entre moteurs).
    # The pure-Python engine's own detectors (twins are shared between engines).
    pure = {type(d).__name__: d for pack in PURE.packs for d in PURE._detectors[pack.id]}
    for name in PORTED:
        monkeypatch.setattr(pure[name], "_native", Refuse())
    assert [_key(s) for s in PURE.analyze(text).spans] == expected


def test_pure_python_environment_disables_the_twins():
    script = ("from gdprguardian import _native; from gdprguardian.heuristics import fr_address; "
              "assert _native.core() is None and fr_address.FrenchAddressDetector()._native is None")
    env = {**os.environ, "GDPRGUARDIAN_PURE_PYTHON": "1"}
    assert subprocess.run([sys.executable, "-c", script], env=env, check=False).returncode == 0


# --- Robustesse / robustness ------------------------------------------------------------------------------------


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text(max_size=300))
def test_arbitrary_unicode_identical(text):
    for name in PORTED:
        _assert_same(name, text, normalized=False, found=_nir_spans(["185057800608491"]))


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text(max_size=200), st.text(max_size=200), st.booleans(), st.booleans(), st.booleans())
def test_twins_answer_or_refuse_inconsistent_inputs(text, other, has_digit, has_trigger, has_box):
    """Repli sans rapport avec le texte, de même longueur ou non : un résultat ou ValueError, jamais de panique.

    Folded text unrelated to the text, of the same length or not: a result or a ValueError, never a panic.
    """
    folded = (other + " " * len(text))[:len(text)]
    address = DETECTORS["FrenchAddressDetector"]._native
    organizations = DETECTORS["OrganizationDetector"]._native
    for candidate in (folded, other):
        try:
            address.detect(text, candidate, has_digit, has_trigger, has_box)
            organizations.candidates(text, candidate)
        except ValueError:
            assert len(candidate) != len(text)
        DETECTORS["NirBirthDateDetector"]._native.detect(text, candidate, {("85", "05"), (other[:2], text[:2])})
    DETECTORS["EmailDetector"]._native.detect(text + other)
    DETECTORS["IbanDetector"]._native.detect(text + other)
    DETECTORS["MrzDetector"]._native(text + other)


@pytest.mark.parametrize("text", [
    "12 rue " * 5_000, "75002 Paris " * 3_000, "Bât. B, " * 5_000 + "12 rue de la Paix 75002 Paris",
    "rue " + "Aaaa " * 10_000, "@" * 20_000, "a@" * 10_000, "a" * 50_000 + "@b.fr", "FR76 " * 10_000,
    "<" * 50_000, (LINE1 + "\n") * 2_000, "03/05/1985 " * 5_000, "S.A. " * 10_000, "Société " * 10_000,
    "\n" * 50_000, ("x" * 300 + "\n") * 200 + "Bât. A\n12 rue X 75002 Paris",
], ids=lambda t: repr(t[:12]))
def test_pathological_inputs_are_fast_and_identical(text):
    nirs = _nir_spans(["185057800608491"])
    for name in PORTED:
        native_ctx, python_ctx = _contexts(text, found=nirs)
        start = time.perf_counter()
        native = [_key(s) for s in DETECTORS[name].detect(native_ctx)]
        assert time.perf_counter() - start < 2.0, name
        assert native == [_key(s) for s in DETECTORS[name].detect(python_ctx)], name
