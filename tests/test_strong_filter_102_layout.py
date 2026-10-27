"""Filtre fort 1.0.2, mise en page (2e test terrain) : tableaux TSV et prose à tabulations, rien ne franchit un retour
à la ligne par accident, adresses coupées par un retour à la ligne et lieux-dits, liaison de l'indice de naissance.

Strong filter 1.0.2, layout (second field test): TSV tables and tab-spaced prose, nothing crosses a line break by
accident, addresses cut by a line break and named places, birth cue binding. Chaque cas tourne sur le noyau Rust
(s'il est installé) et sur la référence Python, qui doivent rendre le même texte. Every case runs on the Rust core
(when installed) and on the Python reference. Données fictives / fictitious data.
"""

from __future__ import annotations

import re

import pytest

from gdprguardian import Anonymizer, _native, _text
from gdprguardian.engine import _date_seen

_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                    reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]


@pytest.fixture(scope="module", params=_ENGINES)
def engine(request) -> Anonymizer:
    anonymizer = Anonymizer(countries=("FR",), native=request.param)
    assert anonymizer.native == request.param
    return anonymizer


def _masked(engine: Anonymizer, text: str) -> str:
    return engine.anonymize(text).text


def _tags(out: str, label: str) -> set[str]:
    return set(re.findall(rf"\[{label}_[0-9]+\]", out))


# --- Tableaux TSV et prose à tabulations / TSV tables and tab-spaced prose -----------------------------------------


_TAB_PROSE = "Le\tdossier\tde\tJean\tDupont\test\tclos.\nLa\tdemande\tde\tMarie\tCurie\test\tpartie."
_TAB_TABLE = "nom\tprénom\tville\nDupont\tJean\tLyon\nMartin\tClaire\tNantes\n"


def test_tab_spaced_prose_is_not_a_table(engine):
    # Régression du 1er assemblage (red team « tab ») : une prose dont les espaces sont des tabulations garde ses noms
    # entiers. Regression of the first join: prose whose spaces are tabs keeps whole names.
    out = _masked(engine, _TAB_PROSE)
    assert "Dupont" not in out and "Curie" not in out, out
    assert out.count("[PERSONNE_") == 2, out
    assert "\tde\t[PERSONNE_1]\test\t" in out, out


def test_tab_row_is_only_a_delimited_table_row():
    assert not _text._tab_row(_TAB_PROSE, _TAB_PROSE.index("Jean"))
    assert _text._tab_row(_TAB_TABLE, _TAB_TABLE.index("Dupont"))
    assert _text._tab_row(_TAB_TABLE, 0)  # l'en-tête compte / the header counts


def test_tsv_table_cells_stay_columns(engine):
    out = _masked(engine, _TAB_TABLE)
    assert "Dupont" not in out and "Claire" not in out, out
    assert out.startswith("nom\tprénom\tville\n"), out
    assert out.count("\t") == _TAB_TABLE.count("\t"), out


# --- Rien ne franchit un retour à la ligne par accident / nothing crosses a line break by accident ------------------


@pytest.mark.parametrize("text, kept", [
    ("Agence de Tours\nkarine.lopez@exemple.fr", "Agence de Tours\n"),
    ("ACME France SAS\nsophie.lemoine@exemple.fr", "ACME France SAS\n"),
    ("Écrivez à paul@exemple.fr.\nIl répondra.", ".\nIl répondra."),
    ("Contact : s.rochefort@rochefort-avocat.example.\r\nMme Aubry a téléphoné hier.", ".\r\nMme "),
])
def test_an_email_never_swallows_the_neighbouring_line(engine, text, kept):
    out = _masked(engine, text)
    assert kept in out, out
    assert "@" not in out, out


@pytest.mark.parametrize("text", [
    "Agence de Tours\nkarine.lopez@exemple.fr",
    "ACME France SAS\nsophie.lemoine@exemple.fr",
    "Écrire à mon adresse\nkarine.lopez@exemple.fr",
])
def test_break_rule_keeps_two_lines_around_a_complete_email(text):
    norm, _, _ = _text.prepare(text, native=False)
    assert "\n" in norm, norm


def test_a_wrapped_email_is_still_joined():
    norm, _, _ = _text.prepare("x jean.du\npont@exemple.fr y", native=False)
    assert "jean.dupont@exemple.fr" in norm, norm


def test_a_number_and_the_phone_on_the_next_line_stay_two_values(engine):
    text = "Matricule 0049217\n06 74 28 19 53"
    norm, _, _ = _text.prepare(text, native=False)
    assert "\n" in norm, norm
    out = _masked(engine, text)
    assert "0049217" not in out and "06 74" not in out, out
    first, second = out.split("\n")
    assert first.startswith("Matricule [") and second.startswith("[TEL_"), out


def test_a_number_wrapped_inside_still_joins():
    # GAP : « 06 12 34⏎56 78 » n'est pas un téléphone entier de chaque côté / not a whole phone on either side.
    norm, _, _ = _text.prepare("Tél 06 12 34\n56 78", native=False)
    assert "\n" not in norm, norm


def test_a_full_stop_after_an_identifier_stays(engine):
    assert _masked(engine, "IPP 887766.").endswith("].")


# --- Adresses coupées par un retour à la ligne, lieux-dits / addresses cut by a line break, named places -----------


@pytest.mark.parametrize("text, expected", [
    ("Il habite au 29 avenue de la\nGare.", "Il habite au [ADRESSE_1]."),
    ("Il habite au 29 avenue de la\r\nGare.", "Il habite au [ADRESSE_1]."),
    ("demeurant 4 impasse des\n> Camélias, 29900 Concarneau", "demeurant [ADRESSE_1]"),
])
def test_street_name_cut_after_a_particle_continues_on_the_next_line(engine, text, expected):
    assert _masked(engine, text) == expected


def test_a_street_name_does_not_run_into_the_next_line_otherwise(engine):
    out = _masked(engine, "Il habite au 29 avenue Foch\nLe dossier est clos.")
    assert out.endswith("\nLe dossier est clos."), out


@pytest.mark.parametrize("text, expected", [
    ("Domicile : lieu dit La Croix Blanche, commune de Plouay.", "Domicile : [ADRESSE_1]."),
    ("Rendez-vous au lieu-dit Kerhuel demain.", "Rendez-vous au [ADRESSE_1] demain."),
])
def test_a_named_place_is_masked_without_number_or_cue(engine, text, expected):
    assert _masked(engine, text) == expected
    spans = [s for s in engine.analyze(text).spans if s.entity == "ADDRESS"]
    assert [s.reason for s in spans] == ["named_place"], spans


@pytest.mark.parametrize("text, expected", [
    ("Il habite 6 rue des Essais, commune de Vouziers.", "Il habite [ADRESSE_1]."),
    ("Il habite 6 rue des Essais, commune de la région.", "Il habite [ADRESSE_1], commune de la région."),
])
def test_commune_de_before_a_known_town(engine, text, expected):
    assert _masked(engine, text) == expected


@pytest.mark.parametrize("text", [
    "12 rue des Lilas\nBât. C, 3e étage\n75011 Paris",
    "BP 24\n12 rue des Lilas\n75011 Paris",
])
def test_an_address_block_across_lines_has_one_tag(engine, text):
    assert _masked(engine, text) == "[ADRESSE_1]"


def test_a_lieu_dit_without_a_name_stays(engine):
    text = "Le lieu-dit de la bataille est connu."
    assert _masked(engine, text) == text


# --- Liaison de l'indice de naissance / birth cue binding -----------------------------------------------------------


@pytest.mark.parametrize("text, kept, gone", [
    ("M. Paul Durand, né le 12 juin 1934 à Nantes, entré le 5 janvier 2024.", "5 janvier 2024", "12 juin 1934"),
    ("Date de naissance : 12/05/1984\n[21/10/2026 09:10] Agnès : ok", "[21/10/2026 09:10]", "12/05/1984"),
    # Année sur deux chiffres : la date passée lie l'indice même si elle n'est pas masquée ici.
    # Two-digit year: the passed date binds the cue even when it is not masked here.
    ("Né le 12/05/84 à Brest, entré le 05/01/2024.", "05/01/2024", None),
])
def test_a_birth_cue_binds_only_to_its_first_date(engine, text, kept, gone):
    out = _masked(engine, text)
    assert kept in out, out
    assert gone is None or gone not in out, out


def test_a_birth_name_is_not_a_birth_date_cue(engine):
    out = _masked(engine, "Son nom de naissance est Perrin. Il est décédé le 3 mars 2025.")
    assert "3 mars 2025" in out and "Perrin" not in out, out


@pytest.mark.parametrize("text, gone", [
    ("Date de naissance : 12/05/1984", ["1984"]),
    ("Né le 3 mai 1979 ; sa sœur, née le 4 juin 1981.", ["1979", "1981"]),
    ("Arrivée le 12/05/2024. Date de naissance : 03/05/1979.", ["1979"]),
    ("Le 12/05/1984 (date de naissance), dossier ouvert.", ["1984"]),
])
def test_every_cued_birth_date_is_still_masked(engine, text, gone):
    out = _masked(engine, text)
    for value in gone:
        assert value not in out, out


def test_one_birth_date_written_twice_has_one_tag(engine):
    out = _masked(engine, "Né le 3 mai 1979. Date de naissance confirmée : 03/05/1979.")
    assert len(_tags(out, "DATE_NAISSANCE")) == 1, out


@pytest.mark.parametrize("part, seen", [
    (" le 12 juin 1934 à Nantes, entré le ", True),
    (" : 12/05/84 puis ", True),
    (" : dossier 29200, pièce 12 ", False),
    (" le ", False),
    (" 2.5.2 ", False),
])
def test_date_seen(part, seen):
    assert _date_seen(part, 0, len(part)) is seen
