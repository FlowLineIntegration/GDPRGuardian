"""Données figées : taille, forme des clés, provenance, cohérence avec le script de construction.

Frozen data: size, key shape, provenance, consistency with the build script.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from importlib import resources
from pathlib import Path

import pytest

from gdprguardian._text import fold
from gdprguardian.heuristics import _lexicon
from gdprguardian.heuristics._lexicon import (
    AMB_ENTITY,
    AMB_NONE,
    AMB_STRONG,
    AMB_WORD,
    ambiguity,
    given_rank,
    lexicon,
    place_key,
    surname_rank,
)

DATA = Path(str(resources.files("gdprguardian.heuristics") / "data"))
ROOT = Path(__file__).resolve().parents[2]


def _lines(name: str) -> list[str]:
    raw = gzip.decompress((DATA / name).read_bytes()).decode("utf-8")
    return [line for line in raw.splitlines() if line and not line.startswith("#")]


@pytest.fixture
def build_script(monkeypatch):
    """Le script de construction, chargé sans réseau ni effet de bord / the build script, loaded offline."""
    spec = importlib.util.spec_from_file_location("build_gazetteers", ROOT / "tools" / "build_gazetteers.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)  # requis par les dataclasses / needed by dataclasses
    spec.loader.exec_module(module)
    return module


def test_data_files_are_small():
    sizes = {p.name: p.stat().st_size for p in DATA.iterdir() if p.is_file()}
    assert {"names.tsv.gz", "words.txt.gz", "postal.tsv.gz", "sources.json", "SOURCES.md"} <= set(sizes)
    assert sum(sizes.values()) < 3_000_000


def test_keys_are_folded_and_well_formed():
    for line in _lines("names.tsv.gz"):
        token, given, sex, surname, amb = line.split("\t")
        assert token == fold(token) and token.strip() == token
        assert given in ("", "c") or given.isdigit()
        assert sex in ("", "M", "F", "X") and amb in ("", "w", "s", "e")
        assert surname == "" or int(surname) >= 8  # au moins 256 porteurs / at least 256 bearers
    words = _lines("words.txt.gz")
    assert all(w == fold(w) for w in words)
    for line in _lines("postal.tsv.gz"):
        code, keys = line.split("\t")
        assert len(code) == 5 and code.isdigit()
        assert all(k == place_key(k) for k in keys.split("|"))


def test_provenance_and_attribution():
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    assert {"prenoms", "noms", "hexasmal", "cog_communes", "lexemes", "lexemes_en"} <= set(sources)
    for entry in sources.values():
        assert len(entry["sha256"]) == 64 and entry["bytes"] > 0 and entry["licence"] and entry["attribution"]
    notice = (DATA / "SOURCES.md").read_text(encoding="utf-8")
    assert "Source : Insee" in notice and "Source : La Poste" in notice and "CC0" in notice
    assert "Licence Ouverte" in notice


@pytest.mark.parametrize(("token", "given", "surname", "amb"), [
    ("thomas", True, True, AMB_NONE),
    ("jean", True, True, AMB_WORD),  # « jean » (toile) est aussi un mot anglais / also an English word
    ("dupont", False, True, AMB_NONE),
    ("petit", False, True, AMB_WORD),
    ("rose", True, True, AMB_STRONG),
    ("paris", True, True, AMB_ENTITY),
    ("krzysztof", True, False, AMB_NONE),
    ("le goff", False, True, AMB_NONE),
])
def test_gazetteer_spot_checks(token, given, surname, amb):
    code = lexicon().names[token]
    assert bool(given_rank(code)) is given and bool(surname_rank(code)) is surname and ambiguity(code) == amb


@pytest.mark.parametrize("token", ["rendu", "donne", "fini", "choisi", "clos"])
def test_verb_forms_are_never_safe_names(token):
    # « Rendu le 3 mars » : le fichier Insee en fait un nom, la build exclut les verbes / verb forms are words.
    code = lexicon().names[token]
    assert ambiguity(code) == AMB_WORD and surname_rank(code)


@pytest.mark.parametrize("token", ["facture", "paie", "virement", "licenciement", "embauche", "releve"])
def test_common_words_missing_from_wikidata_are_supplied(token):
    assert token in lexicon().words and token not in lexicon().names


@pytest.mark.parametrize(("code", "commune"), [
    ("75001", "paris"), ("20000", "ajaccio"), ("98000", "monaco"), ("97400", "st denis"),
    ("01000", "bourg en bresse"), ("69003", "lyon"),
])
def test_postal_spot_checks(code, commune):
    assert commune in lexicon().postal[code]


def test_build_script_shares_the_runtime_normalisation(build_script):
    for sample in ("Œdipe Noël-Zoë", "SAINT-ÉTIENNE", "L'Haÿ-les-Roses", "Ærø Łódź"):
        assert build_script.fold(sample) == fold(sample)
        assert build_script.place_key(sample) == place_key(sample)


def test_build_script_ambiguity_classes(build_script):
    places = {"lyon", "aude"}
    assert build_script.ambiguity("avril", 1000, set(), places) == "e"       # mois / month
    assert build_script.ambiguity("lyon", 0, set(), places) == "e"          # lieu / place
    assert build_script.ambiguity("aude", 40_000, set(), places) == "w"     # prénom fréquent homonyme d'un lieu
    assert build_script.ambiguity("rose", 100_000, {"rose"}, set()) == "s"  # mot très courant / very common word
    assert build_script.ambiguity("petit", 0, {"petit"}, set()) == "w"
    assert build_script.ambiguity("dupont", 0, set(), set()) == ""


def test_build_script_refuses_a_cache_inside_the_repository(build_script):
    with pytest.raises(SystemExit):
        build_script.main(["--cache", str(ROOT / "tools"), "--offline"])


def test_lexicon_is_loaded_once_and_shared(monkeypatch):
    monkeypatch.setattr(_lexicon, "_LEXICON", None)
    calls = []
    real = _lexicon._load

    def counting() -> _lexicon.Lexicon:
        calls.append(1)
        return real()

    monkeypatch.setattr(_lexicon, "_load", counting)
    with ThreadPoolExecutor(max_workers=8) as pool:
        loaded = list(pool.map(lambda _: lexicon(), range(16)))
    assert len(calls) == 1 and all(x is loaded[0] for x in loaded)
