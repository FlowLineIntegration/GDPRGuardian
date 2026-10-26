"""Contrats Python -> Rust : modifier une référence Python sans son jumeau Rust échoue ici, précisément.

Python -> Rust contracts: editing a Python reference without its Rust twin fails here, precisely.

Le moteur Python est la référence ; le noyau Rust recopie à la main des motifs `re`, des listes, des seuils et des
fonctions (rust/src/names, rust/src/detectors, rust/src/finalize, rust/src/validators, rust/src/engine,
rust/src/unicode.rs, rust/src/pattern, rust/src/tabular…). Les données passées à la construction (lexiques, listes
de mots, tables Unicode, prototypes de zones) ont une seule source et ne figurent pas ici.
The Python engine is the reference; the Rust core hand-copies `re` patterns, lists, thresholds and functions.
Data passed at construction (lexicons, word lists, Unicode tables, span prototypes) has a single source and is
not listed here.

Chaque entrée enregistre l'empreinte de la SOURCE Python (arbre syntaxique sans commentaires ni docstrings :
reformater ou commenter ne change rien) et le jumeau Rust à mettre à jour. Quatre gardes / four guards:
1. empreinte de chaque cible Python recopiée / fingerprint of every hand-copied Python target;
2. chaque jumeau Rust cité existe encore / every cited Rust twin still exists;
3. les constantes Rust recopiées valent leurs sources Python / copied Rust constants equal their Python sources;
4. noyau présent : chaque jumeau se construit (pas de repli silencieux sur Python) et chaque validateur natif a
   son contrat / with the core: every twin builds (no silent Python fallback), every native validator is listed.

Après une modification voulue : mettre à jour le jumeau Rust, relancer les tests différentiels cités, puis
imprimer la table à jour avec `python tests/test_native_contracts.py` et la recopier ici.
After an intended change: update the Rust twin, rerun the cited differential tests, then print the updated
table with `python tests/test_native_contracts.py` and paste it here.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import re
import sys
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUST = ROOT / "rust" / "src"

# Tests différentiels de chaque famille / differential tests of each family.
NAMES = "tests/heuristics/test_names_native.py"
DETECTORS = "tests/test_detectors_native.py"
SCANNER = "tests/test_native.py, tests/test_native_engine.py"
PREPARE = "tests/test_prepare_native.py"
FINALIZE = "tests/test_finalize_native.py"
UNICODE = "tests/test_unicode_native.py"
FUSED = "tests/test_engine_fused.py"
TABULAR = "tests/test_tabular_native.py"
VALIDATION = "tests/test_validators_native.py"
_FAMILIES = {NAMES: "NAMES", DETECTORS: "DETECTORS", SCANNER: "SCANNER", PREPARE: "PREPARE", FINALIZE: "FINALIZE",
             UNICODE: "UNICODE", FUSED: "FUSED", TABULAR: "TABULAR", VALIDATION: "VALIDATION"}

# (tests différentiels, module, ((cible, jumeau(x) Rust sous rust/src, empreinte), …)).
# (differential tests, module, ((target, Rust twin(s) under rust/src, fingerprint), …)).
# Jumeaux : « fichier.rs: symbole, symbole ; autre.rs: symbole » / twins: "file.rs: symbol, …; other.rs: symbol".
CONTRACTS: tuple[tuple[str, str, tuple[tuple[str, str, str], ...]], ...] = (
    # BEGIN CONTRACTS
    (NAMES, "gdprguardian.heuristics.fr_names", (
        ("_PARTICLES", "names/patterns.rs: GAP_PARTICLES, space_gap", "c07e959762f4888e"),
        ("_SPACE_GAP_RE", "names/patterns.rs: space_gap, MAX_SPACE_GAP", "36bcecaeabbb7e9b"),
        ("_NEWLINE_GAP_RE", "names/patterns.rs: newline_gap", "4d528743943ef8aa"),
        ("_INITIAL_GAP_RE", "names/patterns.rs: initial_gap", "2615cbbd97be72b7"),
        ("_PARTICLE_AT_RE", "names/patterns.rs: particle_at, SHIFT_PARTICLES", "663467b64172373e"),
        ("_AFTER_HONORIFIC_RE", "names/patterns.rs: after_honorific", "cf89726b001e0f7e"),
        ("_ARTICLE_AT_RE", "names/patterns.rs: article_at", "4e8df88a9e8d2971"),
        ("_AFTER_CUE_RE", "names/patterns.rs: after_cue", "0bdb5a29510b5941"),
        ("_AFTER_EPONYM_RE", "names/patterns.rs: after_eponym, eponym_article", "25798604ce6ee398"),
        ("_AFTER_DIRECT_RE", "names/patterns.rs: after_direct", "b9812b5fbf9167e2"),
        ("_AFTER_LABEL_RE", "names/patterns.rs: after_label", "98243b16040bf182"),
        ("_LABEL_SPLIT_RE", "names/patterns.rs: after_last_label_separator", "b7d73844de1ecdf6"),
        ("_LIST_GAP_RE", "names/patterns.rs: list_gap, CONJUNCTIONS", "f071d587583f189c"),
        ("_DISPLAY_AT_RE", "names/patterns.rs: display_opener", "d3d4437bb33edb30"),
        ("_EMAIL_LOCAL_RE", "names/patterns.rs: email_locals", "70e595536da75ec7"),
        ("_LOCAL_SPLIT_RE", "names/cues.rs: email_names", "99e828d3de877bf6"),
        ("_WORD4_RE", "names/decide.rs: line_style", "68b1669eaed45f9d"),
        ("_TABLE_SEP_RE", "names/patterns.rs: table_separator", "39f76f9a89642f1b"),
        ("_HYPHEN_WRAP_RE", "names/patterns.rs: hyphen_wrap, hyphen_wrap_at, unwrap", "9392afda3a269af8"),
        ("_FIELD_WORD_RE", "names/patterns.rs: field_word", "d5410e49c2ee09b2"),
        ("_FIELD_GAP_RE", "names/patterns.rs: field_gap", "b9812b5fbf9167e2"),
        ("_FIELD_END_RE", "names/patterns.rs: field_end", "775af6eca8db83f7"),
        ("_NAME_CELL_RE", "names/patterns.rs: name_cell", "1aa686521b1b705b"),
        ("_NUMBER_AFTER_RE", "names/patterns.rs: number_after", "aa05e37f25be4439"),
        ("_YEAR_AFTER_RE", "names/patterns.rs: year_after", "53f6d2f313fc40f3"),
        ("_NEXT_WORD_RE", "names/patterns.rs: next_word", "a31a6b59a89daa10"),
        ("_VOCATIVE_RE", "names/patterns.rs: vocative", "0ee9df290c0fe22f"),
        ("_DOTTED_AC", "names/py.rs: PyNameDetector", "19f6df4bd7cb2ff2"),
        ("_Triggers", "names/py.rs: PyNameDetector; names/mod.rs: Trigger", "9630a745303a365f"),
        ("NEG", "names/mod.rs: NEG", "793ffdb356af726c"),
        ("NONE", "names/mod.rs: NONE", "3665a31e7cefc7e4"),
        ("WEAK", "names/mod.rs: WEAK", "dcce64221460ae02"),
        ("MEDIUM", "names/mod.rs: MEDIUM", "72263497eca1fae0"),
        ("STRONG", "names/mod.rs: STRONG", "9084d9e7883c1863"),
        ("_given_bias", "names/lexicon.rs: given_bias", "020dba03d8e7758f"),
        ("_unwrap", "names/patterns.rs: unwrap", "4cf6be9fb75f0c53"),
        ("_Element", "names/mod.rs: Element, given, surname, amb, solid, safe", "993c95ca2a857f61"),
        ("_Cues.inside", "names/mod.rs: inside", "0707d8932871cd5a"),
        ("_native_data", "names/py.rs: PyNameDetector, VOCABULARY", "c7874fccd9817660"),
        ("FrenchNameDetector._detect_native", "names/py.rs: detect; engine/passes.rs: names", "3a0b2c712438fa13"),
        ("FrenchNameDetector._detect_python", "names/mod.rs: detect", "25e20f2e9f97681e"),
        ("FrenchNameDetector._tokens", "names/tokens.rs: tokens", "e2182dbac5f3bdc9"),
        ("FrenchNameDetector._dotted_forms", "names/tokens.rs: dotted_forms, covers", "ba652b052ed3a2d3"),
        ("FrenchNameDetector._joins", "names/tokens.rs: joins", "cc9fe0aad3bcada8"),
        ("FrenchNameDetector._runs", "names/tokens.rs: runs", "a5139eec53ff552e"),
        ("FrenchNameDetector._split", "names/tokens.rs: split", "f75860f8a57c54c2"),
        ("FrenchNameDetector._merge", "names/tokens.rs: merge", "36bf3e6283bb4448"),
        ("FrenchNameDetector._cues", "names/cues.rs: cues, put", "45b1140c476f587b"),
        ("FrenchNameDetector._label_cues", "names/cues.rs: label_cues", "a9c99d4656143bb0"),
        ("FrenchNameDetector._lowercase_fields", "names/fields.rs: lowercase_fields, field_value", "f1d2309fb0186fee"),
        ("FrenchNameDetector._field_values", "names/fields.rs: field_values, trimmed_key", "8bccedcff824af9d"),
        ("FrenchNameDetector._field_safe", "names/fields.rs: field_safe", "623011ab52c69be2"),
        ("FrenchNameDetector._lowercase_after_cues", "names/fields.rs: lowercase_after_cues", "90215a8124725293"),
        ("FrenchNameDetector._signature_zone", "names/cues.rs: signature_zone", "5afd713e06ba8a39"),
        ("FrenchNameDetector._display_ends", "names/cues.rs: display_ends", "5ce883097d0727a0"),
        ("FrenchNameDetector._email_names", "names/cues.rs: email_names, strip_digits", "8923896ca12133e3"),
        ("FrenchNameDetector._structured", "names/tables.rs: structured", "6c4a70a3ed298a5c"),
        ("FrenchNameDetector._cells", "names/tables.rs: cells", "e1e7c8221c840f7e"),
        ("FrenchNameDetector._table_rows", "names/tables.rs: table_rows", "57b3456ae246c1e7"),
        ("FrenchNameDetector._row_spans", "names/tables.rs: row_spans", "ffd6dfee7cae1ca3"),
        ("FrenchNameDetector._decide", "names/decide.rs: decide", "a113674a23ab3066"),
        ("FrenchNameDetector._marker", "names/decide.rs: marker", "4be293f7b5f21d3b"),
        ("FrenchNameDetector._evidence", "names/decide.rs: evidence", "e8324b22b4ace0ac"),
        ("FrenchNameDetector._score", "names/decide.rs: score", "452a9b87c145dec5"),
        ("FrenchNameDetector._score_cued", "names/decide.rs: score_cued", "e3afd18ce4bfccc3"),
        ("FrenchNameDetector._score_pair", "names/decide.rs: score_pair", "237087eb1d5aa36f"),
        ("FrenchNameDetector._score_single", "names/decide.rs: score_single", "97859255fbbc3986"),
        ("FrenchNameDetector._sentence_start", "names/decide.rs: sentence_start", "dbc3e9b3fff8ac33"),
        ("FrenchNameDetector._line_start", "names/decide.rs: line_start", "3a25c7f3f946ec60"),
        ("FrenchNameDetector._previous_word", "names/decide.rs: previous_word", "8175f1b2eaa19a0c"),
        ("FrenchNameDetector._after_determiner", "names/decide.rs: after_determiner", "e8008aafe7b15f9e"),
        ("FrenchNameDetector._after_locative", "names/decide.rs: after_locative", "7fd7160946d385d5"),
        ("FrenchNameDetector._line_style", "names/decide.rs: line_style", "2c2e783e9f9c206c"),
        ("FrenchNameDetector._span", "names/spans.rs: span", "eb502b5b8efea4ad"),
        ("FrenchNameDetector._canonical", "names/spans.rs: canonical, last_word", "2d84ee6ccd9ce8b0"),
        ("_POSTCODE_CUE_RE", "names/cues.rs: postcode_ends", "43d1125bd7337709"),
        ("FrenchNameDetector._compound_tokens", "names/tokens.rs: compound_tokens", "41f7d0b5eea00643"),
        ("FrenchNameDetector._organisation_value", "names/cues.rs: organisation_value", "43f0beedda59def2"),
        ("FrenchNameDetector._last_name", "names/spans.rs: last_word", "73d8dc91c8cb326c"),
        ("_LABEL_AHEAD_RE", "names/patterns.rs: label_ahead", "ce8639438e894b3f"),
        ("_SERIES_AFTER_RE", "names/patterns.rs: series_after", "17ef66da6dfb4dfd"),
        ("_VALUE_STOPS", "names/cues.rs: VALUE_STOPS, organisation_value", "bf3bee11a48f3e1c"),
        ("_VALUE_DASHES", "names/cues.rs: organisation_value", "240882dd98d26634"),
        ("_PLACE_HEAD_RE", "names/cues.rs: cues", "2fd270c4a972454d"),
        ("_postcode_heads", "names/py.rs: PyNameDetector, VOCABULARY; names/vocab.rs: POSTCODE_HEAD",
         "a3269e5c77dc6264"),
        ("FrenchNameDetector._particle_surname", "names/cues.rs: particle_surname", "2bfefa28d96f5061"),
    )),
    (FUSED, "gdprguardian.heuristics.fr_names", (
        ("surname_form", "engine/passes.rs: ascii_surname_form", "4b9964476c5b6a5c"),
        ("FrenchNameDetector.detect", "engine/passes.rs: names, within_segment", "43010d5df20c2791"),
        ("FrenchNameDetector._native_span", "engine/passes.rs: names", "6890d11b000000dd"),
        ("FrenchNameDetector.native_plan", "engine/plan.rs: slot, Names", "7028b88dd32270c3"),
        ("FrenchNameDetector._person_rows", "engine/passes.rs: person_rows", "51a23ee6ce9bcb8f"),
    )),
    (NAMES, "gdprguardian.heuristics._lexicon", (
        ("GIVEN_MASK", "names/lexicon.rs: GIVEN_MASK", "61b93ad822112282"),
        ("SURNAME_SHIFT", "names/lexicon.rs: SURNAME_SHIFT", "8101619acb0f71cd"),
        ("RANK_MASK", "names/lexicon.rs: RANK_MASK", "f42d245032241f40"),
        ("AMB_SHIFT", "names/lexicon.rs: AMB_SHIFT", "a2838193f9273215"),
        ("AMB_NONE", "names/lexicon.rs: AMB_NONE", "3665a31e7cefc7e4"),
        ("AMB_WORD", "names/lexicon.rs: AMB_WORD", "dcce64221460ae02"),
        ("AMB_STRONG", "names/lexicon.rs: AMB_STRONG", "72263497eca1fae0"),
        ("AMB_ENTITY", "names/lexicon.rs: AMB_ENTITY", "9084d9e7883c1863"),
        ("K_COMMON", "names/lexicon.rs: Kind", "0b05bf6ec919b3d2"),
        ("ORDINAL_RE", "names/patterns.rs: ordinal", "4f6030668b742061"),
        ("TOKEN_RE", "names/patterns.rs: token", "f9a36dc2bb37a98f"),
        ("LINE_WINDOW", "names/decide.rs: LINE_WINDOW", "bbe11898f6ee4b58"),
        ("line_bounds", "names/decide.rs: line_bounds", "d4a7d78d48aa20d2"),
        ("given_rank", "names/lexicon.rs: given_rank", "aede4f6f40bcab9b"),
        ("surname_rank", "names/lexicon.rs: surname_rank", "cec5571d3c6e63ce"),
        ("ambiguity", "names/lexicon.rs: ambiguity", "606d3a7c8f67fdce"),
        ("Lexicon.code", "names/lexicon.rs: code, first_truthy", "73de410c37ea9598"),
        ("Lexicon.classify", "names/lexicon.rs: classify", "3423fd42a4bd24cd"),
        ("Lexicon._elision", "names/lexicon.rs: elision", "1d77ab1ff71e343d"),
        ("Lexicon._compound", "names/lexicon.rs: compound", "740aa4c59cbefca7"),
        ("PLACE_TOKEN_RE", "detectors/address.rs: place_token", "2fd270c4a972454d"),
        ("department", "detectors/address.rs: department", "d53c89eb1afb7bf7"),
    )),
    (DETECTORS, "gdprguardian.heuristics.fr_address", (
        ("_POSTCODE_RE", "detectors/address.rs: postcode_at, anchors", "68ea002d7a7f0f0d"),
        ("_COMMUNE_GAP_RE", "detectors/address.rs: commune_gap", "4bfc292638f34b9c"),
        ("_PLACE_GAP_RE", "detectors/address.rs: place_gap", "23921f115c58ca5f"),
        ("_SUFFIX_RE", "detectors/address.rs: suffix, district, cedex_suffix", "1849204a5b5cfc4d"),
        ("_CEDEX_RE", "detectors/address.rs: commune", "493d7420e68f3423"),
        ("_POSTCODE_TAIL_RE", "detectors/address.rs: postcode_tail", "895b82695deaf336"),
        ("_CAPITAL_WORDS_RE", "detectors/address.rs: capital_words", "53d35c71806abfd9"),
        ("_NUMBER_BEFORE_RE", "detectors/address.rs: number_before, house_number_at, separator_then_end",
         "968a472403eec33c"),
        ("_NAME_WORD_RE", "detectors/address.rs: name_word, name_word_at", "037ec99fb544f0e5"),
        ("_BOX_RE", "detectors/address.rs: boxes, box_at, dotted_ends, box_number", "bc3330739b0164c6"),
        ("_BOX_ALONE_DIGITS", "detectors/address.rs: BOX_ALONE_DIGITS", "9084d9e7883c1863"),
        ("_BOX_SURE_DIGITS", "detectors/address.rs: BOX_SURE_DIGITS", "8101619acb0f71cd"),
        ("_BOX_NEAR_BEFORE", "detectors/address.rs: BOX_NEAR_BEFORE", "136a684d5960a3ed"),
        ("_BOX_NEAR_AFTER", "detectors/address.rs: BOX_NEAR_AFTER", "7e1c938a4c64c47b"),
        ("_BOX_NEAR_RE", "detectors/address.rs: near_postcode", "34fa9c4882585632"),
        ("_lone_box", "detectors/address.rs: lone_box", "2025234ffd25023f"),
        ("_LINK_RE", "detectors/address.rs: link", "1cd7ea7491c12c9b"),
        ("_COMPLEMENT", "detectors/address.rs: COMPLEMENT_WORDS, COMPLEMENT_TAIL_MAX, complement_unit_starts",
         "cbc5da7e62bcff62"),
        ("_COMPLEMENT_RE", "detectors/address.rs: complement_starts, COMPLEMENT_UNITS", "ae0805847ca536d5"),
        ("_COMPLEMENT_LINE_RE", "detectors/address.rs: complement_line, COMPLEMENT_LINE_INDENT", "5a56023142cfd50d"),
        ("_TRIGGER_RE", "detectors/address.rs: trigger_at", "1d9b8afbaddba3c4"),
        ("_TYPE_AC", "detectors/address.rs: new, streets", "f5fcf1dd937941aa"),
        ("FrenchAddressDetector.detect", "detectors/address.rs: detect; engine/passes.rs: address", "d4cc89b0d89fb62d"),
        ("FrenchAddressDetector._spans", "detectors/address.rs: detect", "8140c376c8cc3e49"),
        ("FrenchAddressDetector._anchors", "detectors/address.rs: anchors", "7531353de98484d8"),
        ("FrenchAddressDetector._commune", "detectors/address.rs: commune, COMMUNE_WINDOW, COMMUNE_TOKENS",
         "34415b9a6b6be796"),
        ("FrenchAddressDetector._commune_before",
         "detectors/address.rs: commune_before, joined_keys, COMMUNE_BEFORE_WINDOW, COMMUNE_BEFORE_TOKENS",
         "f3aef6ba1e022df6"),
        ("FrenchAddressDetector._streets", "detectors/address.rs: streets, NUMBER_WINDOW", "8d4da4fb0d95c11b"),
        ("FrenchAddressDetector._street_name", "detectors/address.rs: street_name, elided", "8968674b0d9bf58c"),
        ("FrenchAddressDetector._before", "detectors/address.rs: before", "b54534fe971c7bff"),
        ("FrenchAddressDetector._complement", "detectors/address.rs: complement", "189aa7299ceb2b78"),
        ("FrenchAddressDetector._cued", "detectors/address.rs: cued, CUE_WINDOW", "edc696b938e2546f"),
        ("_ADJECTIVE_BEFORE_RE", "detectors/address.rs: adjective_before, ADJECTIVE_WINDOW", "d54d5ab118d97698"),
        ("_HOUSE_NUMBER_RE", "detectors/address.rs: house_number_token", "97d116417d4e8b86"),
        ("_PLACE_WORD_RE", "detectors/address.rs: place_word", "fbc2ea6d8fa388e7"),
        ("_TOWN_GAP_RE", "detectors/address.rs: town_gap", "f56eafb6214c13a3"),
        ("_TOWN_END_RE", "detectors/address.rs: town_end_at", "4ad61b4ca2bcd214"),
        ("FrenchAddressDetector._place_before", "detectors/address.rs: place_before, PLACE_SEGMENT_MAX",
         "5109247b528e47ea"),
        ("FrenchAddressDetector._place_words", "detectors/address.rs: place_words, PLACE_WORDS_MAX",
         "f34c20b5aeb32ac4"),
        ("FrenchAddressDetector._street_near", "detectors/address.rs: street_near, NEAR_STREET", "50b6b00e5a275738"),
        ("FrenchAddressDetector._town_after", "detectors/address.rs: town_after, TOWN_WINDOW", "326ad552df6563cb"),
        ("FrenchAddressDetector._address_line", "detectors/address.rs: address_line", "4d77f0281110a355"),
        ("FrenchAddressDetector._address_chunk", "detectors/address.rs: address_chunk", "f782128a5f2d2968"),
        ("_CHUNK_NUMBER_RE", "detectors/address.rs: chunk_number_token", "c7ef9986c57f13fe"),
        ("_LINE_SEPARATORS", "detectors/address.rs: address_line", "ca358506a34cac8a"),
        ("_TOWN_TAIL_RE", "detectors/address.rs: town_tail, TOWN_PARTICLES", "01f2240e553f227e"),
        ("_HOME_RE", "detectors/address.rs: home_at, HOME_WORDS", "99315d320a7f9cd4"),
        ("_HOME_WINDOW", "detectors/address.rs: home, HOME_WINDOW", "a1209c690dac8a9d"),
        ("FrenchAddressDetector._home", "detectors/address.rs: home", "c7b7ca37ca878e68"),
        ("FrenchAddressDetector._named", "detectors/address.rs: named, is_upper_word", "49bdf6217c4d43da"),
        ("_given_names", "detectors/python.rs: PyAddressDetector; detectors/address.rs: AddressData",
         "6df06988ff677a42"),
        ("STREET_NUMBERED", "detectors/address.rs: STREET_NUMBERED", "77d8f7d76b567fa9"),
        ("STREET_CUED", "detectors/address.rs: STREET_CUED", "c70b36935d93dc50"),
        ("_native_twin", "detectors/python.rs: PyAddressDetector; detectors/address.rs: AddressData",
         "da823bf832263748"),
    )),
    (FUSED, "gdprguardian.heuristics.fr_address", (
        ("FrenchAddressDetector.native_plan", "engine/plan.rs: slot, Address", "5a192d02228596aa"),
    )),
    (DETECTORS, "gdprguardian.heuristics.organizations", (
        ("_WORD", "detectors/organizations.rs: company_word", "637eeef916bd0919"),
        ("_FAMILY", "detectors/organizations.rs: FAMILY, family_at", "8d65d8a3060c7a36"),
        ("_JOINER", "detectors/organizations.rs: FAMILY_JOINERS, NAME_JOINERS, joiner_ends", "c35a059e6ded484c"),
        ("_NAME", "detectors/organizations.rs: name_end", "dbd6ad5f84ccf2cc"),
        ("_WORD_RE", "detectors/organizations.rs: word_fullmatch", "4ab176fc6397b00c"),
        ("_OPENING", "detectors/organizations.rs: OPENING", "a42b4a1bf51b3bdc"),
        ("_NAME_RIGHT_RE", "detectors/organizations.rs: name_right, RIGHT_PREFIXES", "0c0aea74635fe303"),
        ("_PIECE_RE", "detectors/organizations.rs: next_piece", "86f94e37c7d4070f"),
        ("_CASE_AC", "detectors/organizations.rs: new, candidates", "16629ff1f5ddfe12"),
        ("_KEYWORD_AC", "detectors/organizations.rs: new, candidates", "b323450f27d0e439"),
        ("OrganizationDetector._candidates", "detectors/organizations.rs: candidates", "5a3971deec96fba1"),
        ("OrganizationDetector._legal_form", "detectors/organizations.rs: candidates", "c8cd7d19eb83124f"),
        ("OrganizationDetector._left_name", "detectors/organizations.rs: left_name, MAX_WORD, MAX_PIECES",
         "6dc414da997eb2a4"),
        ("OrganizationDetector._right_name", "detectors/organizations.rs: right_name", "cb5cedb1f7974650"),
        ("_bounded", "detectors/organizations.rs: bounded", "4645e6233ad3cda7"),
        ("_native_twin", "detectors/python.rs: PyOrganizationDetector; detectors/organizations.rs: OrganizationData",
         "d3020450a2c59ac2"),
    )),
    (FUSED, "gdprguardian.heuristics.organizations", (
        ("_WORDS_RE", "engine/organizations.rs: words", "aa5c8d594b835724"),
        ("OrganizationDetector.detect", "engine/passes.rs: organizations", "c45983fa52d102ec"),
        ("OrganizationDetector._spans", "engine/organizations.rs: spans, segment_end", "6b7a674a0aca40cb"),
        ("OrganizationDetector.native_plan", "engine/plan.rs: slot, Organizations; engine/organizations.rs: Decision",
         "5860b6fc824df352"),
        ("OrganizationDetector._person_content", "engine/organizations.rs: person_content; names/py.rs: lexicon_ranks",
         "3ad830868e68dd42"),
    )),
    (DETECTORS, "gdprguardian.detectors.fr", (
        ("NirBirthDateDetector._numeric", "detectors/fr.rs: numeric_date, day_ends, month_ends", "a790ace827d57142"),
        ("NirBirthDateDetector._words", "detectors/fr.rs: written_date, spaces", "77387424f677ae6d"),
        ("NirBirthDateDetector._dates", "detectors/fr.rs: detect", "4336081ed0ac9ca7"),
        ("NirBirthDateDetector.detect", "detectors/python.rs: PyBirthDateDetector; engine/passes.rs: birth_dates",
         "a24f785f2e2db948"),
        ("_native_twin", "detectors/python.rs: PyBirthDateDetector", "546da849a44e30c6"),
    )),
    (FUSED, "gdprguardian.detectors.fr", (
        ("NirBirthDateDetector.native_plan", "engine/plan.rs: slot, BirthDates", "e73612c5efbbb742"),
    )),
    (DETECTORS, "gdprguardian.detectors.intl", (
        ("EmailDetector._local", "detectors/intl.rs: around, LOCAL_WINDOW", "56fcf7349a58a96c"),
        ("EmailDetector._domain", "detectors/intl.rs: domain_end", "e0f0db16efe3cbc0"),
        ("EmailDetector._candidates", "detectors/intl.rs: detect, around", "43fa9de5d904c906"),
        ("IbanDetector._anchor", "detectors/intl.rs: iban_anchor", "ddf97bef316ea5e1"),
        ("IbanDetector._candidates", "detectors/intl.rs: IbanDetector", "aa6ad641d3f0eaf7"),
        ("_printed_in_fours", "detectors/intl.rs: printed_in_fours", "f9e3955f59744779"),
        ("MrzDetector._block", "detectors/intl.rs: mrz_block", "e42837cf6546cba4"),
        ("MrzDetector._bands", "detectors/intl.rs: mrz", "61311cce462a686c"),
        ("_mrz_check_ratio", "detectors/intl.rs: mrz_check_ratio", "a98c54e8b82de265"),
    )),
    (FUSED, "gdprguardian.detectors.intl", (
        ("_native_phone", "engine/python.rs: phone_candidates", "0b8a60fc205fbc97"),
        ("EmailDetector.detect", "engine/passes.rs: email", "663823e053016d5d"),
        ("EmailDetector.native_plan", "engine/plan.rs: slot, Email", "f438bdc651cd4e43"),
        ("IbanDetector.detect", "engine/passes.rs: iban", "75dcff035d784e49"),
        ("IbanDetector.native_plan", "engine/plan.rs: slot, Iban", "a6622cc3a073170a"),
        ("MrzDetector.detect", "engine/passes.rs: mrz; detectors/python.rs: mrz_spans", "3750557b0c2b5340"),
        ("MrzDetector.native_plan", "engine/plan.rs: slot, Mrz", "cfe1831c238b92ae"),
        ("InternationalPhoneDetector._candidate", "engine/phone.rs: candidates, match_at, body", "8c4a1fecaa4d3a6a"),
        ("InternationalPhoneDetector.detect", "engine/passes.rs: phone", "ac3bf403b172a878"),
        ("InternationalPhoneDetector.value", "engine/passes.rs: phone", "3131e10b38357e10"),
        ("InternationalPhoneDetector.native_plan", "engine/plan.rs: slot, Phone", "1f9ab210eac3fad6"),
    )),
    (DETECTORS, "gdprguardian.validators.checksums", (
        ("icao_check_digit", "detectors/intl.rs: icao_check_digit, WEIGHTS; validators/checksums.rs: icao_check_digit",
         "c25a915e7b22ea93"),
    )),
    (PREPARE, "gdprguardian._text", (
        ("normalize", "prepare.rs: normalize_text, cuts, assemble", "f0895d38e30eb98a"),
        ("fold", "prepare.rs: fold_text; unicode.rs: fold; finalize/chars.rs: folded; names/chars.rs: push_fold",
         "ca89090e445165de"),
        ("prepare", "prepare.rs: prepare_text, prepare_parts", "7b24217f6cbd73ad"),
        ("_unbold", "prepare.rs: unbold", "97f97e9b9882eee0"),
        ("_EMPHASIS_RE", "prepare.rs: unbold, is_emphasis", "c9984bc731b50912"),
        ("_HYPHEN_BREAK_RE", "prepare.rs: hyphen_break_end, cuts", "0aa26983d1c9a439"),
        ("_gaps", "prepare.rs: gaps, normalize_text", "80321d71f0fe650e"),
        ("_group_longer", "prepare.rs: group_longer, GAP_GROUP", "801eed8f9e788e20"),
        ("_GAP_BLANKS_RE", "prepare.rs: gaps", "55f12798d4f65d16"),
        ("_GAP_BREAK_RE", "prepare.rs: gaps, break_shape", "28fcb63a88c01fe3"),
        ("_sep_runs", "prepare.rs: sep_runs, normalize_text", "6c40e7c139b9cea8"),
        ("_SEP_RUNS", "prepare.rs: sep_runs, SEP_RUNS, SEP_GROUP", "2ac32e0d0fd4b595"),
        ("_breaks", "prepare.rs: breaks, BREAK_GROUP, normalize_text", "190530e3f8011477"),
        ("_token", "prepare.rs: token", "4a87bede1b8c9f52"),
        ("_email_join", "prepare.rs: email_join, BREAK_LOCAL", "b557863385576619"),
        ("_iban_complete", "prepare.rs: iban_complete", "10f9db339df1e453"),
        ("_BREAK_RE", "prepare.rs: breaks, email_part", "64d83e38944599c3"),
        ("_DOMAIN_RE", "prepare.rs: domain_ok", "a203904012c70caa"),
        ("_IBAN_HEAD_RE", "prepare.rs: iban_head", "44e4e79eea32d832"),
        ("_spaced_cuts", "prepare.rs: spaced_cuts, normalize_text", "39278fb7ad2eaf16"),
        ("_spaced_block", "prepare.rs: spaced_block", "26c771e6b2b7a19f"),
        ("_SPACED_RE", "prepare.rs: spaced_cuts, spaced_cell", "82f989ff9c5afea2"),
        ("_SPACED_MIN", "prepare.rs: spaced_block", "7fa6730d4945a002"),
        ("_SPACED_HINT_RE", "prepare.rs: spaced_hint", "48df3b9d63bd72de"),
        ("_SPACED_MARKS", "prepare.rs: spaced_block, spaced_cell", "e971dabeba150001"),
        ("_ASCII_LETTERS", "prepare.rs: email_join", "9550714eab4fe0b8"),
        ("_EMAIL_PART", "prepare.rs: email_part", "fbc7206b9d63fc34"),
        ("_BREAK_GROUP", "prepare.rs: BREAK_GROUP", "dc8bd17100f676e7"),
        ("_BREAK_LOCAL", "prepare.rs: BREAK_LOCAL", "362cbe23adbe8089"),
    )),
    (UNICODE, "gdprguardian._text", (
        ("_dense_bmp", "unicode.rs: Unicode, new, fold", "e0403a66267247b0"),
        ("WORD", "unicode.rs: WORD", "1c3fe8eaeaabbcce"),
        ("ALNUM", "unicode.rs: ALNUM", "1c3fe8eaeaabbcce"),
        ("LETTER", "unicode.rs: LETTER", "1c3fe8eaeaabbcce"),
        ("DECIMAL", "unicode.rs: DECIMAL", "1c3fe8eaeaabbcce"),
        ("DIGIT", "unicode.rs: DIGIT", "1c3fe8eaeaabbcce"),
        ("SPACE", "unicode.rs: SPACE", "1c3fe8eaeaabbcce"),
        ("ALPHA", "unicode.rs: ALPHA", "1c3fe8eaeaabbcce"),
        ("UPPER", "unicode.rs: UPPER", "1c3fe8eaeaabbcce"),
        ("LOWER", "unicode.rs: LOWER", "1c3fe8eaeaabbcce"),
        ("TITLE", "unicode.rs: TITLE", "1c3fe8eaeaabbcce"),
        ("UPPER_SAFE", "unicode.rs: UPPER_SAFE", "1c3fe8eaeaabbcce"),
        ("CAPITAL", "unicode.rs: CAPITAL", "1c3fe8eaeaabbcce"),
        ("INVISIBLE", "unicode.rs: INVISIBLE", "1c3fe8eaeaabbcce"),
        ("MAPS_UPPER", "unicode.rs: MAPS_UPPER", "1c3fe8eaeaabbcce"),
        ("MAPS_LOWER", "unicode.rs: MAPS_LOWER", "1c3fe8eaeaabbcce"),
        ("char_flags", "unicode.rs: GIVEN, Plane, new", "6bd4a1c551570f80"),
        ("plane_classes", "unicode.rs: PlaneData, GIVEN, Plane, new", "254e8b23cf6e9147"),
        ("ignorecase_data", "unicode.rs: IgnoreCaseData, IgnoreCase, equivalents, ignorecase_candidates",
         "78d056c50a98c228"),
    )),
    (UNICODE, "gdprguardian._native", (
        ("unicode_tables", "unicode.rs: PyUnicodeTables, new", "f46607f7854564f5"),
    )),
    (PREPARE, "gdprguardian._native", (
        ("preparer", "prepare.rs: Preparer, new", "3d8a294be5201cc3"),
        ("language_detector", "prepare.rs: LanguageDetector, new", "44d33f9058c2b59c"),
    )),
    (PREPARE, "gdprguardian.locale", (
        ("_WORD_RE", "prepare.rs: LanguageDetector, pack", "d3395c0314a99a51"),
        ("detect_language", "prepare.rs: LanguageDetector, detect, language_of", "335eee7475f695eb"),
    )),
    (FUSED, "gdprguardian.locale", (
        ("evidence", "engine/document.rs: evidence", "57afdef4c51ac6de"),
    )),
    (SCANNER, "gdprguardian.keywords", (
        ("MAX_KEYWORD_LEN", "keywords.rs: MAX_KEYWORD_LEN", "e440aefe6556a296"),
        ("KeywordHits.near", "keywords.rs: near", "ab9ad38039281b79"),
        ("KeywordHits.last_end", "keywords.rs: last_end", "351ae30069a072b5"),
        ("KeywordHits.finalize", "keywords.rs: finalize; lib.rs: present, counts", "66718f7b1206b7ab"),
        ("KeywordHits.groups", "lib.rs: groups, present", "30aee006c349e68a"),
        ("KeywordIndex.__init__", "keywords.rs: KeywordIndex, new", "76b35c6e7a896072"),
        ("KeywordIndex.scan", "keywords.rs: scan", "c7e3fac0ef0b1919"),
        ("KeywordIndex.groups_in", "engine/python.rs: groups_of", "1251f5eb799a8871"),
        ("longest_matches", "finalize/propagate.rs: longest_matches", "ed76aaab90817d15"),
    )),
    (SCANNER, "gdprguardian._native", (
        ("_CATEGORIES", "pattern/node.rs: Sets, category", "6e8e496633201377"),
        ("_AT", "pattern/node.rs: At, node", "da4cf3e538b49701"),
        ("_AT_MULTILINE", "pattern/node.rs: At, node", "032928d40315fbab"),
        ("_ignorecase_candidates", "unicode.rs: ignorecase_candidates; pattern/node.rs: Sets", "3ff235888354d2aa"),
        ("_cased_matches", "pattern/node.rs: node, Sets", "3915d704fad5d137"),
        ("_nodes", "pattern/node.rs: nodes, node, Node", "a4018c8fa9336980"),
        ("syntax", "pattern/node.rs: read, Tree", "fdd82e2db97bfd84"),
        ("_spec", "lib.rs: source, parse_recognizer; pattern/node.rs: read; scanner.rs: compile_all",
         "4a8c7aaeceeccb58"),
        ("NativeScanner.__init__", "lib.rs: PyScanner, new", "36e2da9b5413f6a5"),
        ("NativeScanner.scan", "lib.rs: scan", "763320498d5ace7d"),
        ("text_rules", "finalize/python.rs: PyTextRules, new", "b6057b0589ea6c53"),
    )),
    (FUSED, "gdprguardian._native", (
        ("engine", "engine/python.rs: PyEngine, new", "75b3760628946038"),
    )),
    (SCANNER, "gdprguardian.engine", (
        ("DetectionContext.has",
         "scanner.rs: Gate, Literals, present; engine/passes.rs: address, mrz, phone; engine/python.rs: run",
         "8ab3a50b44e825c3"),
        ("_DIGIT_RE", "scanner.rs: Gate, present; engine/python.rs: run", "2b40e9bcdd4894b8"),
        ("_not_alnum", "scanner.rs: left_ok, right_ok", "fb66f1c2af2f44df"),
        ("DetectionContext.segment",
         "scanner.rs: segment; finalize/propagate.rs: locate; engine/document.rs: segment_end",
         "7cd396137cd2c64e"),
        ("DetectionContext.any_context", "scanner.rs: any_context", "ce0f149bfdc76485"),
        ("DetectionContext._header_context", "scanner.rs: header_context", "0b0f32eb7c889040"),
        ("_check_forced", "lib.rs: scan; scanner.rs: header_context", "a0c46dd83013a280"),
        ("DetectionContext.near", "scanner.rs: near", "7442a0c33d3b4121"),
        ("DetectionContext.vetoed", "scanner.rs: vetoed, VETO_ADJACENT", "9eac4ddb4bce71f9"),
        ("_boundary_checks", "scanner.rs: left_ok, right_ok, Boundary", "9d3acb9f3ae59abe"),
        ("_SKIP_RUN", "scanner.rs: next_start", "8406a303819d8b94"),
        ("_next_start", "scanner.rs: next_start", "5d0c3ecaf9107690"),
        ("Anonymizer._detect", "scanner.rs: scan; engine/passes.rs: pass, scan", "7aa12c125c268c6c"),
        ("Anonymizer._recognizer_spans", "scanner.rs: scan", "fb4944408328aba6"),
        ("Anonymizer._run", "scanner.rs: run", "6f567f7ac6d62043"),
        ("Anonymizer._personal", "scanner.rs: run, Policy, NATURAL_PERSON_WINDOW, LEGAL_ENTITY_WINDOW",
         "8fa18fcd5e2decf5"),
        ("_no_legal_entity", "scanner.rs: no_legal_entity, REGISTER_LABELS, ENTITY_WORDS, ENTITY_FORMS, SHORT_LINE",
         "63792ef50c341270"),
        ("Anonymizer._civil_status", "scanner.rs: civil_status, near_within", "57f3e49ff2d8736d"),
        ("_line_bounds", "scanner.rs: line_bounds", "4567028b5dff87eb"),
        ("_block_bounds", "scanner.rs: block_bounds", "c783ac27c516a243"),
    )),
    (FUSED, "gdprguardian.engine", (
        ("_SEGMENT_SEPARATOR", "engine/python.rs: SEPARATOR", "9cc2fcad2f99749b"),
        ("_FoundView", "engine/document.rs: found, found_key", "176b34cf68e3f236"),
        ("_Host", "engine/passes.rs: python, python_context, detect", "386dfab70d06fb7b"),
        ("_TABLE_DELIMITER_RE", "engine/tables.rs: is_delimiter_row", "55b5dad1a836bd86"),
        ("_PIPE_RE", "engine/tables.rs: cells", "b36dfbdce7c157fb"),
        ("_cells", "engine/tables.rs: cells", "a484e16a87e3fda0"),
        ("markdown_table_zones", "engine/tables.rs: zones, Cursor", "e72e0ecdf26dfd45"),
        ("_priority", "engine/passes.rs: scan; engine/plan.rs: Recognizer", "6066d1bb6b903d7d"),
        ("Anonymizer._fused_engine",
         "engine/python.rs: PyEngine, new; engine/plan.rs: Reader, pack, slot, recognizer, custom",
         "12474c39bd39bca1"),
        ("Anonymizer._entity_allowed", "engine/plan.rs: allowed", "476479d51e71e308"),
        ("Anonymizer.context_groups", "engine/python.rs: groups_of", "0215967acf817c34"),
        ("Anonymizer._fused_document", "engine/python.rs: detect", "63d41e3bcf075a7e"),
        ("Anonymizer._fused_cells", "engine/python.rs: detect_cells", "e684729df6570b20"),
        ("Anonymizer._fused_context",
         "engine/document.rs: text, folded, hits, countries, language, segments, forced, zones",
         "efecd422c160127b"),
        ("Anonymizer._fused_select", "engine/document.rs: evidence, found; engine/passes.rs: detect",
         "9a9f7cfc6315dc6f"),
        ("Anonymizer._fused_countries", "engine/document.rs: countries, reasons", "3a1e38f8f7d33bf7"),
        ("Anonymizer._fused_fallback", "engine/document.rs: detected, offsets, timings", "82298519bc0b3700"),
        ("Anonymizer._fused_cells_fallback", "engine/document.rs: cell_offsets", "77c26e3db9161bc1"),
        ("Anonymizer.analyze", "engine/document.rs: analyze; finalize/fused.rs: analyze_detected", "d772b58c0a5d2db4"),
        ("Anonymizer._detect_text", "engine/python.rs: detect, run", "69bf754967d39325"),
        ("Anonymizer.analyze_segments", "engine/document.rs: analyze_cells; finalize/fused.rs: analyze_detected_cells",
         "44e0565303a47038"),
        ("Anonymizer._detect_segments", "engine/python.rs: detect_cells, run", "6a0018115f9f682f"),
        ("Anonymizer._detect_all", "engine/passes.rs: detect", "d5897db642ac57fe"),
        ("Anonymizer._detector_spans", "engine/passes.rs: push", "6ed1b528cca074ad"),
        ("Anonymizer._custom_spans", "engine/passes.rs: custom", "f04ff2b5d9460741"),
        ("Anonymizer.anonymize",
         "engine/document.rs: anonymize, sanitized; finalize/fused.rs: anonymize_detected, PyFinalSpans",
         "70d857c762084c00"),
        ("Anonymizer._labels", "finalize/fused.rs: displayed_labels; finalize/python.rs: anonymize",
         "39894be10c5e0dd2"),
        ("Anonymizer.anonymize_segments",
         "engine/document.rs: anonymize_cells; finalize/fused.rs: anonymize_detected_cells",
         "8e0b5f07b35ffa72"),
        ("_display_all", "finalize/fused.rs: displayed_labels", "b5f1430982f92788"),
        ("_offset_array", "engine/document.rs: offsets, cell_offsets", "c79c6f2258fc1224"),
    )),
    (FUSED, "gdprguardian.heuristics._compose", (
        ("decomposed", "engine/python.rs: decomposed", "f034ca08ad2274c2"),
    )),
    (FUSED, "gdprguardian.sanitize", (
        ("_INVISIBLE_RE", "engine/sanitize.rs: invisible", "9feb2a50d01c3f8f"),
        ("_REMOTE_IMAGE_RE", "engine/sanitize.rs: remote_image, run_until", "a0c8498e27f9d52e"),
        ("_HTML_IMG_RE", "engine/sanitize.rs: html_img, Closer", "20f8970344b78939"),
        ("_HTML_COMMENT_RE", "engine/sanitize.rs: html_comment, Closer", "61641b103a18739a"),
        ("sanitize_output", "engine/sanitize.rs: sanitize, substitute", "0bfcd3a6952705ec"),
    )),
    (FINALIZE, "gdprguardian.engine", (
        ("_trim", "finalize/resolve.rs: trim", "66507f66e415ce35"),
        ("merge_same_entity", "finalize/resolve.rs: merge_same_entity; finalize/span.rs: py_max", "158bcae96f039c52"),
        ("resolve", "finalize/resolve.rs: resolve", "44dfc83a8912681b"),
        ("_apply_keep", "finalize/resolve.rs: apply_keep", "6ea751725ec78cb6"),
        ("_trim_honorific", "finalize/resolve.rs: trim_honorific; finalize/chars.rs: is_honorific", "f6fde15b8a1fcb8e"),
        ("Anonymizer._finalize", "finalize/resolve.rs: filter; finalize/pipeline.rs: finalize", "32fe81aac013118b"),
        ("Anonymizer._propagate", "finalize/propagate.rs: propagate, sources", "83d32939bb976bd3"),
        ("_company_named", "finalize/pipeline.rs: company_named, COMPANY_FORMS, COMPANY_SUFFIX_ONLY",
         "7eca590a87a569f3"),
        ("_extend_after_civility", "finalize/pipeline.rs: extend_after_civility, civility_before, CIVILITIES",
         "a3f30be3fa54ef1e"),
        ("_surname_end", "finalize/pipeline.rs: surname_end", "283885ebe08af5e0"),
        ("_drop_company_names", "finalize/pipeline.rs: drop_company_names, form_right_before", "570d041c5670d0e3"),
        ("PARTNERSHIP_FORMS", "finalize/pipeline.rs: PARTNERSHIP_FORMS", "70728ac5af7f36c3"),
        ("_FIRM_LINK_RE", "finalize/pipeline.rs: firm_link, FIRM_LINKS", "9244256f23c35cb0"),
        ("_FIRM_BLANKS", "finalize/pipeline.rs: FIRM_BLANKS", "c04a6046592860c9"),
        ("_civility_surnames", "finalize/pipeline.rs: civility_surnames, PRIORITY_HEURISTIC", "7d8638cacfe3e59d"),
        ("CIVILITY_WORDS", "finalize/pipeline.rs: CIVILITY_WORDS", "ec5918d0372fd49c"),
        ("NOT_SURNAMES", "finalize/pipeline.rs: NOT_SURNAMES", "9f3da2ffef9ef753"),
        ("COMPANY_FORMS", "finalize/pipeline.rs: COMPANY_FORMS", "ba96e46e65385c1f"),
        ("COMPANY_SUFFIX_FORMS", "finalize/pipeline.rs: COMPANY_SUFFIX_ONLY", "a0ea6840bd85d61d"),
        ("_COMPANY_BEFORE_RE", "finalize/pipeline.rs: company_named", "4c3a30f82b7e8bc9"),
        ("_COMPANY_AFTER_RE", "finalize/pipeline.rs: company_named", "f4b2bf5fd4ac3405"),
        ("_CIVILITY_BEFORE_RE", "finalize/pipeline.rs: civility_before, CIVILITIES", "04cf7a4231486bcb"),
        ("_TITLE_BEFORE_RE", "finalize/pipeline.rs: titled_before, title_in, TITLES", "28567652bbee6da7"),
        ("Anonymizer._final_spans", "finalize/pipeline.rs: map_offsets; finalize/python.rs: analyze",
         "b0d64f735f0f45f3"),
        ("Anonymizer._segment_spans", "finalize/pipeline.rs: split_segments; finalize/python.rs: analyze_segments",
         "dfb3cb11ed7573de"),
        ("Anonymizer._render_text", "finalize/python.rs: anonymize", "7c0fb601be20daf9"),
        ("Anonymizer._render", "finalize/render.rs: render", "44f14fce12de28a8"),
        ("Anonymizer._reason", "finalize/render.rs: reason", "4958340d231d5dbd"),
        ("Anonymizer._native_finalizer", "finalize/python.rs: PyFinalizer", "cb50157071376a88"),
        ("_rule_of", "finalize/render.rs: rule_of", "e29d604f02e958aa"),
        ("_aggregate", "finalize/python.rs: explain_lines; finalize/render.rs: ExplainLine", "122e88f7cf9ad742"),
    )),
    (FINALIZE, "gdprguardian.scope", (
        ("PLACEHOLDER_RE", "finalize/scope.rs: placeholder_at", "8a7674ceec02ae4d"),
        ("_NAME_TOKEN_RE", "finalize/scope.rs: name_tokens", "11db144bae0310b6"),
        ("split_person_name", "finalize/scope.rs: split_person_name, split_name", "a4961adc711651d3"),
        ("Scope._digest", "finalize/scope.rs: digest, digest_parts, digest_folded", "49590d0c1e35daa4"),
        ("Scope.reserve", "finalize/scope.rs: reserve", "d1a922083951a300"),
        ("Scope._next_index", "finalize/scope.rs: next_index", "717e191ab20e6275"),
        ("Scope.placeholder", "finalize/scope.rs: placeholder, placeholder_into", "3fbaef248c4361c3"),
        ("Scope.person_key", "finalize/scope.rs: person_key, person, PersonKey", "4d87b5fac1c826c4"),
        ("Scope._new_cluster", "finalize/scope.rs: new_cluster", "86634b8d59b053ea"),
        ("Scope._set_given", "finalize/scope.rs: set_given", "f3106d6d43bb6009"),
        ("Scope._set_parts", "finalize/scope.rs: set_parts", "97fd15bd94669222"),
        ("_SPACE_RE", "finalize/scope.rs: canonical_into", "69bcb8e34b589b33"),
        ("_canonical", "finalize/scope.rs: canonical_text, canonical_into", "19f78ea3c0ff24b5"),
    )),
    (FINALIZE, "gdprguardian.operators", (
        ("_YEAR_RE", "finalize/render.rs: year", "f2b2a96af8e8cf8d"),
        ("replace", "finalize/render.rs: apply", "cd5654578f68c015"),
        ("redact", "finalize/render.rs: apply", "e1093eb46cbe15ed"),
        ("mask", "finalize/render.rs: mask", "8b633fda60978d99"),
        ("generalize", "finalize/render.rs: apply, year", "ed334bb03d724a93"),
        ("keep", "finalize/render.rs: apply", "3ad891f97d008460"),
        ("OPERATORS", "finalize/render.rs: Operator, from_name", "bdc98e69c8f3e825"),
    )),
    (FINALIZE, "gdprguardian.types", (
        ("Span", "finalize/span.rs: Span; finalize/python.rs: read_span, span_object", "aa8a5a08cd64597b"),
    )),
    (TABULAR, "gdprguardian.tabular._package", (
        ("MAX_MEMBERS", "tabular/zip.rs: MAX_ENTRIES, open", "e55f51a0d5ea5371"),
        ("MAX_UNCOMPRESSED", "tabular/zip.rs: MAX_TOTAL, open", "a5273ee316c3e174"),
        ("MAX_RATIO", "tabular/zip.rs: MAX_RATIO, central_entry", "d88a6bda7f761d2f"),
        ("MAX_PART", "tabular/zip.rs: MAX_PART, reader", "4d492d5e182aa99b"),
        ("_RATIO_FLOOR", "tabular/zip.rs: RATIO_FLOOR, central_entry", "8870d68e5f2c8f5a"),
        ("_BOM", "tabular/extent.rs: BOM", "e0316ea73aeb690d"),
        ("Package.adopt_measure",
         "tabular/python.rs: PyXlsxSheet, measured, PartMeasure; tabular/zip.rs: PartIdentity, identity",
         "84a64dad23d571b3"),
        ("_check_archive", "tabular/zip.rs: open, central_entry", "4b1091589c3f2aa5"),
        ("_WS_QUOTES", "tabular/extent.rs: seen", "e327a07e5bfdef20"),
        ("_FAST_BLOCKERS", "tabular/extent.rs: tag, colon, reference", "5e22774c260f840f"),
        ("_ODD_REF", "tabular/extent.rs: reference, MAX_LETTERS, MAX_DIGITS", "c38006fd576e11fe"),
        ("_REF_DIGITS", "tabular/extent.rs: reference", "197d3a345959d860"),
        ("_REF_LETTERS", "tabular/extent.rs: reference", "bfa17bf4a5212dc5"),
        ("_ROWS_OVER_99999", "tabular/extent.rs: reference, result", "7793d73157aa3949"),
        ("_TWO_LETTERS", "tabular/extent.rs: reference, result", "084a62243049e9d0"),
        ("_THREE_LETTERS", "tabular/extent.rs: reference, result", "3ce6ea10de52dbef"),
        ("_as_utf8", "tabular/extent.rs: probe, close, UTF16_PROBE", "8adeede1deeab1dd"),
        ("column_index", "tabular/extent.rs: reference", "38034c26b3859393"),
        ("_measuring_core", "tabular/python.rs: sheet_measure", "c22eb63fcb5efdce"),
        ("sheet_measure", "tabular/extent.rs: measure, tag, colon, close; tabular/python.rs: sheet_measure",
         "7edfd6ac6c6a167d"),
        ("xlsx_extent", "tabular/extent.rs: Measure, measure, scan, opener, tag, counts, reference, result",
         "35a9fa9061a2d3ae"),
    )),
    (TABULAR, "gdprguardian.tabular._reader", (
        ("_WORKSHEET", "tabular/python.rs: sheets", "ad850f0e52b144ea"),
        ("_CHARTSHEET", "tabular/python.rs: sheets", "0cd4744173559b93"),
        ("_open_book", "tabular/python.rs: PyXlsxBook, register", "613650455bd39fcb"),
        ("_NativeSheet", "tabular/python.rs: PyXlsxSheet, start, height, width, merged, rows", "86dd67f37fec5605"),
        ("_NativeBook", "tabular/python.rs: PyXlsxBook, sheets, sheet, measured", "37995dde85b62f25"),
    )),
    # END CONTRACTS
)

VALIDATORS: tuple[tuple[str, str], ...] = (
    # BEGIN VALIDATORS
    ("fr.nir", "2cbf0c84e4ece675"),
    ("fr.nir_without_key", "84b1349ac7369408"),
    ("fr.spi", "cc6800c41762b249"),
    ("fr.siren", "604e76862bf06fa1"),
    ("fr.siret", "31386f6e9b489078"),
    ("fr.tva", "8141ad2f6130373a"),
    ("fr.rib", "61631e3dd0a99797"),
    ("fr.luhn_digits", "36199a34aba60f9c"),
    ("fr.finess", "b46111477cd8e042"),
    ("fr.siv_plate", "d0bf963468312c12"),
    ("fr.alnum_mixed", "1f703deff4224010"),
    ("fr.contextual_id", "cf8d1ab22d851a6b"),
    ("fr.phone_field", "86a06843b8e5e533"),
    ("fr.phone", "71a7c64ffda9e57c"),
    ("fr.phone_overseas", "e1c0662ae71e93fc"),
    ("fr.eori", "00da88337abfa473"),
    ("intl.iban", "32df7435885bd5ce"),
    ("intl.card", "a440173c51cb7c29"),
    ("intl.card14", "6b2d08fe1a04cead"),
    ("intl.imei", "e3745d932301e04f"),
    ("intl.ipv4", "ea399ad32663f713"),
    ("intl.ipv6", "0af738be665c99c9"),
    ("intl.mac", "1027c8f391d3f995"),
    ("intl.btc", "e6f2424d5da30a30"),
    ("intl.eth", "250ed146104c354c"),
    ("intl.email", "51b71c75190212cb"),
    ("intl.digits_e164", "7c38ffdf868eab91"),
    ("intl.calendar_date", "584caf086c9b8c74"),
    ("be.nn", "dee3299ba692d5a6"),
    ("be.bis", "b697ed5fc9f8148c"),
    ("be.niss", "fb60a384affdc41d"),
    ("be.niss_unpadded", "73f73ae2100f222e"),
    ("be.enterprise_number", "1f7903a497dc7714"),
    ("be.eid", "9bda0c9b098668eb"),
    ("be.bban", "3a2d8f489669b61f"),
    ("be.phone", "55a1fbf55ae9a238"),
    ("ch.avs", "5123e61e34255144"),
    ("ch.uid", "284e69f97f48146d"),
    ("ch.phone", "7c755b9949b8fdff"),
    ("de.steuer_id", "a6fb14543e7e7dad"),
    ("de.steuernummer", "8d95a592bd9f5463"),
    ("de.rvnr", "7d94df377cae4803"),
    ("de.kvnr", "78b6f3bd589d04fe"),
    ("de.id_document", "2a2c7fcfd62df1a9"),
    ("de.fuehrerschein", "21238917df1f1aee"),
    ("de.ust_idnr", "76c2ee852391023a"),
    ("de.phone", "4d90e8dc3bda0b7d"),
    ("de.phone_mobile", "5a2ab1cfba7d5fab"),
    ("es.dni", "8326653a29da41bd"),
    ("es.nie", "5fb23bda6e2b42af"),
    ("es.cif", "5ee991febb2d2d59"),
    ("es.nif_person", "2fc4a326e4dad7a4"),
    ("es.vat_person", "9cbb07b0f65b21bb"),
    ("es.vat_company", "df226697e8be268a"),
    ("es.nss", "5300ce28195a1076"),
    ("es.phone", "1f669637e28d7187"),
    ("it.codice_fiscale", "bd3691db4b277e07"),
    ("it.partita_iva", "c91e3ce454a051a9"),
    ("it.vat", "1472971987c782f7"),
    ("it.phone", "d5c62bdc8d780eb2"),
    ("it.phone_mobile", "75213ee3a49e95ba"),
    ("lu.matricule", "c850b0e211a55cf9"),
    ("lu.matricule_legacy", "ac4a3655ee34240f"),
    ("lu.tva", "07be9ac599fd6cf4"),
    ("lu.rcs", "b181ca98fd3211ba"),
    ("lu.phone", "4cb1222c84e79320"),
    ("mc.tva", "c98c229e2d18fa35"),
    ("mc.rci", "e16743d276df6a18"),
    ("mc.phone", "c4c055cc85ca8633"),
    ("nl.bsn", "e8bcc8243573068a"),
    ("nl.btw", "a98175285a807fc1"),
    ("nl.btw_person", "13cdaf125ee0b5d9"),
    ("nl.btw_company", "28db7a81e7f8f7c4"),
    ("nl.kvk", "55c5424a6f7d400a"),
    ("nl.document_number", "5bcfbade7b892d50"),
    ("nl.postcode", "9d838226187108db"),
    ("nl.phone", "68d5c5cfa6a28eb5"),
    ("nl.phone_mobile", "6e3d0a8cd0c6d9b3"),
    ("pt.nif", "b961354abebfb231"),
    ("pt.nif_person", "9646b7824af54911"),
    ("pt.nipc", "4f184aa74bac2cdf"),
    ("pt.vat_person", "375dc92d4c8eee80"),
    ("pt.vat_company", "bca17dd7193e5948"),
    ("pt.niss", "0a9c704bc94f1b89"),
    ("pt.cc", "0d7b131f658706c1"),
    ("pt.nic", "67039591f545cb21"),
    ("pt.sns", "6bfb1e48b284ad77"),
    ("pt.phone", "5993756a42b30b87"),
    # END VALIDATORS
)


# --- empreintes de source / source fingerprints -------------------------------------------------------------

_SKIPPED_FIELDS = frozenset({"ctx", "kind", "type_comment", "type_params"})
_DOCUMENTED = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _canonical(node: Any) -> str:
    """Forme canonique d'un arbre : sans positions, docstrings ni champs vides ; chaînes contiguës d'une f-string
    fusionnées, éléments d'un ensemble triés : stable d'une version de Python à l'autre.

    Canonical form of a tree: no positions, docstrings or empty fields; adjacent f-string parts merged, set
    elements sorted: stable across Python versions.
    """
    if isinstance(node, list):
        return "[" + ",".join(_canonical(item) for item in node) + "]"
    if not isinstance(node, ast.AST):
        return repr(node)
    fields = []
    for name, value in ast.iter_fields(node):
        if name in _SKIPPED_FIELDS or value is None or value == []:
            continue
        if name == "body" and isinstance(node, _DOCUMENTED) and ast.get_docstring(node, clean=False) is not None:
            value = value[1:]
        if isinstance(node, ast.JoinedStr) and name == "values":
            value = _merge_constants(value)
        if isinstance(node, ast.Set) and name == "elts":
            fields.append(f"elts=[{','.join(sorted(_canonical(item) for item in value))}]")
            continue
        fields.append(f"{name}={_canonical(value)}")
    return f"{type(node).__name__}({','.join(fields)})"


def _merge_constants(values: list[ast.expr]) -> list[ast.expr]:
    merged: list[ast.expr] = []
    for value in values:
        if merged and isinstance(value, ast.Constant) and isinstance(merged[-1], ast.Constant):
            merged[-1] = ast.Constant(merged[-1].value + value.value)
        else:
            merged.append(value)
    return merged


@cache
def _module_tree(module: str) -> ast.Module:
    spec = importlib.util.find_spec(module)
    assert spec is not None and spec.origin is not None, module
    return ast.parse(Path(spec.origin).read_text(encoding="utf-8"))


def _definition(scope: ast.AST, name: str) -> ast.AST:
    """Définition de `name` dans le corps de `scope` : fonction, classe ou affectation (valeur seule ; pour un
    tuple de noms sans tuple de même longueur en face, l'affectation entière : l'ordre des noms compte).

    Definition of `name` in `scope`'s body: function, class or assignment (value only; for a tuple of names
    without a same-length tuple value, the whole assignment: the order of the names matters).
    """
    for statement in getattr(scope, "body", ()):
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and statement.name == name:
            return statement
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) \
                and statement.target.id == name:
            return statement.value or statement
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return statement.value
                if isinstance(target, ast.Tuple):
                    names = [t.id if isinstance(t, ast.Name) else None for t in target.elts]
                    if name in names:
                        value = statement.value
                        same = isinstance(value, ast.Tuple) and len(value.elts) == len(names)
                        return value.elts[names.index(name)] if same else statement
    raise LookupError(name)


def source_node(target: str) -> ast.AST:
    """« module:Classe.methode » -> nœud de sa définition / its definition node."""
    module, _, qualname = target.partition(":")
    node: ast.AST = _module_tree(module)
    for part in qualname.split("."):
        node = _definition(node, part)
    return node


def fingerprint(*nodes: ast.AST) -> str:
    digest = hashlib.sha256("\n".join(_canonical(node) for node in nodes).encode("utf-8"))
    return digest.hexdigest()[:16]


# --- fermeture des validateurs / validator closure ----------------------------------------------------------


def _imports(module: str) -> dict[str, tuple[str, str]]:
    """Noms importés depuis le paquet : alias -> (module, nom) / package imports: alias -> (module, name)."""
    found: dict[str, tuple[str, str]] = {}
    package = module.rsplit(".", 1)[0]
    for statement in _module_tree(module).body:
        if isinstance(statement, ast.ImportFrom) and statement.level:
            base = package.rsplit(".", statement.level - 1)[0] if statement.level > 1 else package
            source = f"{base}.{statement.module}" if statement.module else base
            for alias in statement.names:
                found[alias.asname or alias.name] = (source, alias.name)
    return found


def closure(module: str, name: str) -> list[str]:
    """Cibles « module:nom » dont dépend `name`, dans le paquet `gdprguardian`, triées / dependencies, sorted."""
    seen: set[str] = set()
    pending = [(module, name)]
    while pending:
        current_module, current = pending.pop()
        key = f"{current_module}:{current}"
        if key in seen:
            continue
        seen.add(key)
        imports = _imports(current_module)
        for node in ast.walk(source_node(key)):
            if not isinstance(node, ast.Name):
                continue
            if node.id in imports and imports[node.id][0].startswith("gdprguardian."):
                pending.append(imports[node.id])
                continue
            try:
                _definition(_module_tree(current_module), node.id)
            except LookupError:
                continue
            pending.append((current_module, node.id))
    return sorted(seen)


def validator_fingerprint(name: str) -> tuple[str, list[str]]:
    country, function = name.split(".")
    members = closure(f"gdprguardian.validators.{country}", function)
    return fingerprint(*(source_node(member) for member in members)), members


def validator_twin(name: str) -> tuple[str, str]:
    """« fr.nir » -> (`validators/fr.rs`, `nir`) : fonction Rust du même nom / Rust function of the same name."""
    country, function = name.split(".")
    return f"validators/{country}.rs", function


# --- inventaire / inventory ----------------------------------------------------------------------------------


def _entries() -> Iterator[tuple[str, str, str, str]]:
    for tests, module, entries in CONTRACTS:
        for target, twins, recorded in entries:
            yield f"{module}:{target}", twins, tests, recorded


def _twins(spec: str) -> Iterator[tuple[str, str]]:
    for part in spec.split(";"):
        file, _, symbols = part.partition(":")
        for symbol in symbols.split(","):
            yield file.strip(), symbol.strip()


@cache
def _rust_source(file: str) -> str:
    return (RUST / file).read_text(encoding="utf-8")


def _rust_defines(file: str, symbol: str) -> bool:
    return re.search(rf"\b(?:fn|const|static|struct|enum|type)\s+{re.escape(symbol)}\b", _rust_source(file)) is not None


def _message(target: str, twins: str, tests: str, recorded: str, current: str, members: list[str] | None = None,
             ) -> str:
    covered = f"\n  couvre / covers: {', '.join(members)}" if members else ""
    return (f"Contrat Python -> Rust rompu / Python -> Rust contract broken: {target}{covered}\n"
            f"  empreinte enregistrée / recorded fingerprint {recorded or '(aucune / none)'}, "
            f"actuelle / current {current}\n"
            f"  1. jumeau Rust à mettre à jour / Rust twin to update: rust/src/{twins}\n"
            f"  2. tests différentiels / differential tests: {tests}\n"
            f"  3. empreinte à enregistrer / fingerprint to record: python tests/test_native_contracts.py")


ENTRIES = list(_entries())


def test_fingerprints_ignore_comments_and_layout_but_not_code() -> None:
    def of(source: str) -> str:
        return fingerprint(ast.parse(source).body[0])

    reference = of('def f(x):\n    """Doc."""\n    return re.compile(r"[ \\t]{1,2}").match(x)\n')
    assert reference == of('def f(x):  # commentaire / comment\n    return re.compile(\n        r"[ \\t]{1,2}",\n'
                           "    ).match(x)\n")
    assert reference != of('def f(x):\n    return re.compile(r"[ \\t]{1,3}").match(x)\n')
    assert of("S = frozenset({'de', 'du'})") == of("S = frozenset({'du', 'de'})")
    assert of("L = ('de', 'du')") != of("L = ('du', 'de')")  # l'ordre d'un motif compte / pattern order counts
    assert of('P = rf"[{U}]{{1,2}}" "x"') == of('P = rf"[{U}]{{1,2}}x"')

    def named(source: str, name: str) -> str:
        return fingerprint(_definition(ast.parse(source), name))

    # Noms en tuple : valeur propre si le tuple d'en face a la même longueur, sinon toute l'affectation (ordre des
    # noms compris). Tuple of names: own value for a same-length tuple, else the whole assignment (name order).
    assert named("A, B = 1, 2", "A") == named("A, C = 1, 3", "A")
    assert named("A, B = (1 << i for i in range(2))", "A") != named("B, A = (1 << i for i in range(2))", "A")
    # Fermeture d'un validateur : ses aides du paquet, pas la bibliothèque standard / package helpers only.
    members = closure("gdprguardian.validators.fr", "nir")
    assert {"gdprguardian.validators.fr:_nir_body", "gdprguardian.validators.checksums:is_digits",
            "gdprguardian._text:strip_separators"} <= set(members)
    assert all(member.startswith("gdprguardian.") for member in members)


def test_every_contract_is_listed_once() -> None:
    targets = [target for target, _, _, _ in ENTRIES]
    assert sorted({t for t in targets if targets.count(t) > 1}) == []
    names = [name for name, _ in VALIDATORS]
    assert sorted({n for n in names if names.count(n) > 1}) == []


@pytest.mark.parametrize(("target", "twins", "tests", "recorded"), ENTRIES, ids=[e[0] for e in ENTRIES])
def test_python_reference_matches_its_recorded_fingerprint(target: str, twins: str, tests: str,
                                                           recorded: str) -> None:
    current = fingerprint(source_node(target))
    assert current == recorded, _message(target, twins, tests, recorded, current)


@pytest.mark.parametrize(("name", "recorded"), VALIDATORS, ids=[v[0] for v in VALIDATORS])
def test_native_validator_matches_its_recorded_fingerprint(name: str, recorded: str) -> None:
    current, members = validator_fingerprint(name)
    file, function = validator_twin(name)
    twin = f"{file}: {function} (registre / registry: validators/mod.rs)"
    assert current == recorded, _message(name, twin, VALIDATION, recorded, current, members)


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
def test_every_cited_rust_twin_exists() -> None:
    cited = [(target, file, symbol) for target, twins, _, _ in ENTRIES for file, symbol in _twins(twins)]
    cited += [(name, *validator_twin(name)) for name, _ in VALIDATORS]
    missing = [f"{file}: {symbol} (cité par / cited by {target})" for target, file, symbol in cited
               if not (RUST / file).is_file() or not _rust_defines(file, symbol)]
    assert not missing, f"jumeaux Rust introuvables, inventaire à corriger / Rust twins not found: {missing}"


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
def test_rust_validator_registry_matches_the_contracts() -> None:
    # Registre `validators/mod.rs` (« "fr.nir" => fr::nir, ») : chaque nom vers la fonction du même nom de son
    # fichier pays, et exactement les validateurs de VALIDATORS, dans les deux sens, sans noyau compilé.
    # The registry maps each name to the same-named function of its country file, exactly the VALIDATORS names.
    registry = re.findall(r'"(\w+)\.(\w+)" => (\w+)::(\w+),', _rust_source("validators/mod.rs"))
    renamed = [f"{c}.{f} => {m}::{r}" for c, f, m, r in registry if (c, f) != (m, r)]
    assert renamed == [], f"registre Rust : nom et fonction diffèrent / registry name and function differ: {renamed}"
    native = {f"{country}.{function}" for country, function, _, _ in registry}
    recorded = {name for name, _ in VALIDATORS}
    assert native == recorded, (f"registre sans contrat / registered without a contract: {sorted(native - recorded)}; "
                                f"contrats hors registre / contracts not registered: {sorted(recorded - native)}")


# --- constantes recopiées / copied constants -----------------------------------------------------------------


def _rust_const(file: str, name: str) -> str:
    """Valeur littérale d'une constante Rust (texte entre `=` et `;`) / a Rust constant's literal value."""
    match = re.search(rf"\bconst {name}\s*:[^=]*=\s*(.*?);\s*$", _rust_source(file), re.S | re.M)
    assert match is not None, f"{file}: {name}"
    return match.group(1)


def _unescape(literal: str) -> str:
    escapes = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", "'": "'", '"': '"'}
    return re.sub(r"\\(u\{([0-9a-fA-F]+)\}|.)",
                  lambda m: chr(int(m.group(2), 16)) if m.group(2) else escapes[m.group(1)], literal)


def _rust_strings(file: str, name: str) -> list[str]:
    return [_unescape(s) for s in re.findall(r'"((?:[^"\\]|\\.)*)"', _rust_const(file, name))]


def _rust_chars(file: str, name: str) -> list[str]:
    return [_unescape(c) for c in re.findall(r"'((?:[^'\\]|\\.|\\u\{[0-9a-fA-F]+\}))'", _rust_const(file, name))]


def _rust_ints(file: str, name: str) -> list[int]:
    """Entiers d'un tableau Rust, imbriqué ou non, dans l'ordre / integers of a (nested) Rust array, in order."""
    literals = re.findall(r"-?\b(?:0x[0-9A-Fa-f_]+|[0-9][0-9_]*)\b", _rust_const(file, name))
    return [int(literal.replace("_", ""), 0) for literal in literals]


def _rust_int(file: str, name: str) -> int:
    expression = re.sub(r"(?<=[0-9])_(?=[0-9a-fA-F])|\b(?:u8|u16|u32|u64|usize|i64) ?|as \w+", "",
                        _rust_const(file, name))
    tree = ast.parse(expression.strip(), mode="eval").body

    def evaluate(node: ast.AST) -> int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -evaluate(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.LShift, ast.BitOr, ast.Add, ast.Mult)):
            left, right = evaluate(node.left), evaluate(node.right)
            return {ast.LShift: left << right, ast.BitOr: left | right, ast.Add: left + right,
                    ast.Mult: left * right}[type(node.op)]
        if isinstance(node, ast.Name):  # constante voisine du même fichier / sibling constant
            return _rust_int(file, node.id)
        raise ValueError(f"{file}: {name}: {ast.dump(node)}")

    return evaluate(tree)


def _rust_char_class(file: str, function: str) -> set[int]:
    """Points de code d'un `matches!` de caractères Rust (`'\\u{ad}'`, `'\\u{2060}'..='\\u{2064}'`) dans `function`.

    Code points of a Rust character `matches!` (singles and inclusive ranges) inside `function`.
    """
    body = re.search(rf"\bfn {function}\b.*?\n\}}", _rust_source(file), re.S)
    assert body is not None, f"{file}: {function}"
    points: set[int] = set()
    for low, high in re.findall(r"'\\u\{([0-9a-fA-F]+)\}'(?:\s*\.\.=\s*'\\u\{([0-9a-fA-F]+)\}')?", body.group()):
        points.update(range(int(low, 16), int(high or low, 16) + 1))
    return points


def _class_points(pattern: str) -> set[int]:
    """Points de code d'une classe `[...]` de littéraux et d'intervalles, lus dans l'arbre de `re` lui-même.

    Code points of a `[...]` class of literals and ranges, read from `re`'s own parse tree.
    """
    from re import _parser  # analyseur de `re` lui-même / `re`'s own parser

    ((op, items),) = list(_parser.parse(pattern))
    assert op.name == "IN", pattern
    points: set[int] = set()
    for kind, value in items:
        if kind.name == "LITERAL":
            points.add(value)
        elif kind.name == "RANGE":
            points.update(range(value[0], value[1] + 1))
        else:
            raise ValueError(f"classe non littérale / non-literal class: {pattern}")
    return points


def _expand(pattern: str) -> list[str]:
    """Mots d'une expression rationnelle finie (alternatives, classes, `?`), dans l'ordre / words, in order."""
    from re import _parser  # analyseur de `re` lui-même / `re`'s own parser

    def words(items: Any) -> list[str]:
        out = [""]
        for op, value in items:
            name = op.name
            if name == "LITERAL":
                options = [chr(value)]
            elif name == "IN":
                options = [chr(v) for o, v in value if o.name == "LITERAL"]
                assert len(options) == len(value), pattern
            elif name == "SUBPATTERN":
                options = words(value[-1])
            elif name == "BRANCH":
                options = [w for branch in value[1] for w in words(branch)]
            elif name in ("MAX_REPEAT", "MIN_REPEAT") and value[:2] == (0, 1):
                options = [*words(value[2]), ""]
            elif name == "ASSERT_NOT":
                continue  # assertion de fin (`(?![\w])`) : sans effet sur les mots / no effect on the words
            else:
                raise ValueError(f"motif non fini / non-finite pattern: {pattern}")
            out = [prefix + option for prefix in out for option in options]
        return out

    return words(_parser.parse(pattern))


def _module(name: str) -> Any:
    return importlib.import_module(name)


def _unicode_bits() -> list[str]:
    """Noms des bits de la table Unicode, dans l'ordre de `_text` (affectation en tuple) / bit names, in order."""
    for statement in _module_tree("gdprguardian._text").body:
        if isinstance(statement, ast.Assign) and isinstance(statement.targets[0], ast.Tuple):
            names = [target.id for target in statement.targets[0].elts if isinstance(target, ast.Name)]
            if "WORD" in names:
                return names
    raise LookupError("WORD")


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
def test_copied_name_constants_equal_their_python_sources() -> None:
    names = _module("gdprguardian.heuristics.fr_names")
    lexicon = _module("gdprguardian.heuristics._lexicon")
    particles = _expand(names._PARTICLES)
    assert _rust_strings("names/patterns.rs", "GAP_PARTICLES") == particles
    shift = re.match(r"\(\?:\(\?:([a-z|]+)\)", names._PARTICLE_AT_RE.pattern)
    assert shift is not None and _rust_strings("names/patterns.rs", "SHIFT_PARTICLES") == shift.group(1).split("|")
    conjunctions = set(re.findall(r"\(\?:((?:[a-z]+\|)+[a-z]+)\)\[ \\t\]\{1,2\}", names._LIST_GAP_RE.pattern))
    assert conjunctions == {"|".join(_rust_strings("names/patterns.rs", "CONJUNCTIONS"))}
    # Écart le plus long de `_SPACE_GAP_RE` : 2 + 2 × (particule + 2) + 2 / longest `_SPACE_GAP_RE` gap.
    assert _rust_int("names/patterns.rs", "MAX_SPACE_GAP") == 2 + 2 * (max(map(len, particles)) + 2) + 2
    for name in ("NEG", "NONE", "WEAK", "MEDIUM", "STRONG", "T_HONORIFIC", "T_GREETING", "T_CLOSING", "T_ROLE",
                 "T_EPONYM", "T_EPONYM_DIRECT", "GIVEN_ALONE_MIN", "SURNAME_ALONE_MIN", "GIVEN_START_MIN",
                 "COMMUNE_SURNAME_MIN", "CAPS_ALONE_MIN", "MAX_RUN"):
        assert _rust_int("names/mod.rs", name) == getattr(names, name), name
    assert _rust_int("names/mod.rs", "ENTITY_GIVEN_MIN") == names._ENTITY_GIVEN_MIN
    # Valeur d'une étiquette examinée pour une organisation / field value examined for an organisation.
    assert _rust_int("names/cues.rs", "LABEL_VALUE_MAX") == names._LABEL_VALUE_MAX
    assert _rust_strings("names/cues.rs", "VALUE_STRIP") == [names._VALUE_STRIP]
    assert set(_rust_strings("names/cues.rs", "VALUE_STOPS")) == names._VALUE_STOPS
    for name in ("GIVEN_MASK", "SURNAME_SHIFT", "AMB_SHIFT", "RANK_MASK", "AMB_NONE", "AMB_WORD", "AMB_STRONG",
                 "AMB_ENTITY"):
        assert _rust_int("names/lexicon.rs", name) == getattr(lexicon, name), name
    assert _rust_int("names/decide.rs", "LINE_WINDOW") == lexicon.LINE_WINDOW
    # Verbes de lieu, copiés de `_vocab.PLACE_VERBS` (même ordre) / place verbs, same order.
    vocab = _module("gdprguardian.heuristics._vocab")
    assert _rust_strings("names/decide.rs", "PLACE_VERBS") == list(vocab.PLACE_VERBS)


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
def test_copied_detector_constants_equal_their_python_sources() -> None:
    orgs = _module("gdprguardian.heuristics.organizations")
    address = _module("gdprguardian.heuristics.fr_address")
    assert set(_rust_chars("detectors/organizations.rs", "OPENING")) == orgs._OPENING
    assert set(_rust_strings("detectors/organizations.rs", "FAMILY")) == set(_expand(orgs._FAMILY))
    family_joiners, name_joiners, elided = re.fullmatch(
        r"\(\?:\(\?:(.*?)\)\[ \\t\]\{1,2\}\(\?=.*\)\|\(\?:(.*?)\)\[ \\t\]\{1,2\}\|(.*)\)", orgs._JOINER).groups()
    assert _rust_strings("detectors/organizations.rs", "FAMILY_JOINERS") == _expand(f"(?:{family_joiners})")
    assert _rust_strings("detectors/organizations.rs", "NAME_JOINERS") == _expand(f"(?:{name_joiners})")
    assert set(_expand(f"(?:{name_joiners})")) == orgs._JOINERS and _expand(elided) == ["d'", "l'"]
    prefixes = re.search(r"\(\?:\(\?:(.*?)\)\[ \\t\]\{0,2\}\)\?", orgs._NAME_RIGHT_RE.pattern)
    assert prefixes is not None
    assert _rust_strings("detectors/organizations.rs", "RIGHT_PREFIXES") == _expand(f"(?:{prefixes.group(1)})")
    # Mots de complément : options développées en Rust, classes gardées (motif insensible à la casse ; les
    # équivalents de `re.IGNORECASE` de chaque lettre viennent de la table Unicode partagée, pour toute lettre).
    # Complement keywords: optional parts expanded in Rust, classes kept (case-insensitive pattern; each letter's
    # `re.IGNORECASE` equivalents come from the shared Unicode table, for any letter).
    keywords = re.match(r"\(\?:\(\?<!\[\\w\]\)\(\?:\(\?i:(.*?)\)\[ \\t\]\{0,2\}", address._COMPLEMENT)
    assert keywords is not None
    # Étage avec son rang (« 3e étage ») : seconde branche, jumeau `floor_rank` / floor with its rank: `floor_rank`.
    assert r"|[0-9]{1,2}(?i:er|re|e|[eè]me)[ \t]{1,2}(?i:[ée]tage))" in address._COMPLEMENT
    assert _rust_strings("detectors/address.rs", "COMPLEMENT_WORDS") and "fn floor_rank" in (
        RUST / "detectors/address.rs").read_text(encoding="utf-8")
    complement = _rust_strings("detectors/address.rs", "COMPLEMENT_WORDS")
    rust_words = {w for p in complement for w in _expand(p.replace(".", r"\."))}
    assert rust_words == set(_expand(f"(?:{keywords.group(1)})"))
    # Lieux-dits et voie proche / named places and nearby street.
    assert _rust_int("detectors/address.rs", "PLACE_WORDS_MAX") == address._PLACE_WORDS_MAX
    assert _rust_int("detectors/address.rs", "PLACE_SEGMENT_MAX") == address._PLACE_SEGMENT_MAX
    assert _rust_int("detectors/address.rs", "NEAR_STREET") == address._NEAR_STREET
    # Mot de domicile, fin de commune, raisons propres / home word, town tail, own reasons.
    assert _rust_int("detectors/address.rs", "HOME_WINDOW") == address._HOME_WINDOW
    home = re.fullmatch(r"\(\?<!\\w\)\(\?:(.*)\)", address._HOME_RE.pattern)
    assert home is not None and _rust_strings("detectors/address.rs", "HOME_WORDS") == home.group(1).split("|")
    particles = re.search(r"\(\?i:([^)]*)\)", address._TOWN_TAIL_RE.pattern)
    assert particles is not None
    assert _rust_strings("detectors/address.rs", "TOWN_PARTICLES") == particles.group(1).split("|")
    assert _rust_strings("detectors/address.rs", "STREET_NUMBERED") == [address.STREET_NUMBERED]
    assert _rust_strings("detectors/address.rs", "STREET_CUED") == [address.STREET_CUED]


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
@pytest.mark.parametrize(("file", "constant", "target"), [
    ("detectors/address.rs", "NUMBER_WINDOW", "gdprguardian.heuristics.fr_address:FrenchAddressDetector._streets"),
    ("detectors/address.rs", "COMMUNE_WINDOW", "gdprguardian.heuristics.fr_address:FrenchAddressDetector._commune"),
    ("detectors/address.rs", "COMMUNE_TOKENS", "gdprguardian.heuristics.fr_address:FrenchAddressDetector._commune"),
    ("detectors/address.rs", "COMMUNE_BEFORE_WINDOW",
     "gdprguardian.heuristics.fr_address:FrenchAddressDetector._commune_before"),
    ("detectors/address.rs", "COMMUNE_BEFORE_TOKENS",
     "gdprguardian.heuristics.fr_address:FrenchAddressDetector._commune_before"),
    ("detectors/address.rs", "CUE_WINDOW", "gdprguardian.heuristics.fr_address:FrenchAddressDetector._cued"),
    ("detectors/address.rs", "TOWN_WINDOW", "gdprguardian.heuristics.fr_address:FrenchAddressDetector._town_after"),
    ("detectors/address.rs", "ADJECTIVE_WINDOW", "gdprguardian.heuristics.fr_address:FrenchAddressDetector._streets"),
    ("detectors/organizations.rs", "MAX_WORD", "gdprguardian.heuristics.organizations:OrganizationDetector._left_name"),
    ("detectors/organizations.rs", "MAX_PIECES",
     "gdprguardian.heuristics.organizations:OrganizationDetector._left_name"),
    ("detectors/intl.rs", "LOCAL_WINDOW", "gdprguardian.detectors.intl:EmailDetector._candidates"),
    ("tabular/extent.rs", "UTF16_PROBE", "gdprguardian.tabular._package:_as_utf8"),
])
def test_copied_window_sizes_appear_in_their_python_sources(file: str, constant: str, target: str) -> None:
    # Fenêtres écrites en littéraux dans la référence : la valeur Rust doit y figurer / literal windows.
    literals = {node.value for node in ast.walk(source_node(target))
                if isinstance(node, ast.Constant) and type(node.value) is int}
    assert _rust_int(file, constant) in literals, f"{file}: {constant} absent de / missing from {target}"


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
def test_copied_core_constants_equal_their_python_sources() -> None:
    text = _module("gdprguardian._text")
    lexicon = _module("gdprguardian.heuristics._lexicon")
    keywords = _module("gdprguardian.keywords")
    engine = _module("gdprguardian.engine")
    sanitize = _module("gdprguardian.sanitize")
    intl = _module("gdprguardian.validators.intl")
    # Table Unicode unique (rust/src/unicode.rs) : mêmes bits, mêmes noms, sur 16 bits, dans les deux sens.
    # The single Unicode table: same bits, same names, on 16 bits, both ways.
    bits = _unicode_bits()
    rust_bits = re.findall(r"^pub const (\w+): u16 = ", _rust_source("unicode.rs"), re.M)
    assert rust_bits == bits, f"unicode.rs : bits Rust / Rust bits {rust_bits} != _text {bits}"
    for name in bits:
        rust, python = _rust_int("unicode.rs", name), getattr(text, name)
        assert rust == python, f"unicode.rs: {name} = {rust:#06x} != _text.{name} = {python:#06x}"
    assert max(getattr(text, name) for name in bits) < 1 << 16, "table Rust sur 16 bits / Rust table on 16 bits"
    # Bits que Python calcule (`plane_classes`) : `GIVEN` en Rust, qui déduit les autres (ALNUM, UPPER_SAFE…).
    # Bits Python computes: `GIVEN` in Rust, which derives the others.
    runs, _, _ = text.plane_classes(0, lexicon.UPPER)
    given = 0
    for bit, _ in runs:
        given |= bit
    rust_given = _rust_int("unicode.rs", "GIVEN")
    assert rust_given == given, (f"unicode.rs: GIVEN = {rust_given:#06x} != bits de _text.plane_classes / bits "
                                 f"from _text.plane_classes {given:#06x}")
    assert _rust_int("keywords.rs", "MAX_KEYWORD_LEN") == keywords.MAX_KEYWORD_LEN, "keywords.rs: MAX_KEYWORD_LEN"
    assert _rust_int("prepare.rs", "GAP_GROUP") == text._GAP_GROUP, "prepare.rs: GAP_GROUP"
    # Identifiant d'entreprise d'une personne physique : fenêtres de l'état civil et de la personne morale.
    # Company number of a natural person: civil-status and legal-entity windows.
    for name in ("NATURAL_PERSON_WINDOW", "LEGAL_ENTITY_WINDOW"):
        assert _rust_ints("scanner.rs", name) == list(getattr(engine, name)), f"scanner.rs: {name}"
    # Raisons propres d'un numéro d'entreprise masqué : littéraux de `_personal` / own reasons, `_personal` literals.
    personal = {node.value for node in ast.walk(source_node("gdprguardian.engine:Anonymizer._personal"))
                if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    for name in ("SOLE_TRADER", "CIVIL_STATUS"):
        assert _rust_strings("scanner.rs", name)[0] in personal, f"scanner.rs: {name}"
    separator = _rust_strings("engine/python.rs", "SEPARATOR")
    assert separator == [engine._SEGMENT_SEPARATOR], (f"engine/python.rs: SEPARATOR {separator} != "
                                                      f"engine._SEGMENT_SEPARATOR {engine._SEGMENT_SEPARATOR!r}")
    rust_invisible = _rust_char_class("engine/sanitize.rs", "invisible")
    python_invisible = _class_points(sanitize._INVISIBLE_RE.pattern)
    assert rust_invisible == python_invisible, (
        f"engine/sanitize.rs: invisible != sanitize._INVISIBLE_RE ; Rust seul / Rust only "
        f"{sorted(map(hex, rust_invisible - python_invisible))}, Python seul / Python only "
        f"{sorted(map(hex, python_invisible - rust_invisible))}")
    table = re.findall(r'\("([A-Z]{2})", (\d+)\)', _rust_const("validators/intl.rs", "TABLE"))
    assert {code: int(length) for code, length in table} == intl.IBAN_LENGTHS, "validators/intl.rs: TABLE"
    rules = re.findall(r"\((\d+), (\d+), &\[([\d, ]+)\]\)", _rust_const("validators/intl.rs", "CARD_RULES"))
    assert [(int(lo), int(hi), frozenset(map(int, lengths.split(", ")))) for lo, hi, lengths in rules] == list(
        intl._CARD_RULES), "validators/intl.rs: CARD_RULES"


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
def test_copied_tabular_constants_equal_their_python_sources() -> None:
    package = _module("gdprguardian.tabular._package")
    reader = _module("gdprguardian.tabular._reader")
    for rust, python in (("MAX_ENTRIES", "MAX_MEMBERS"), ("MAX_TOTAL", "MAX_UNCOMPRESSED"), ("MAX_PART", "MAX_PART"),
                         ("MAX_RATIO", "MAX_RATIO"), ("RATIO_FLOOR", "_RATIO_FLOOR")):
        value, expected = _rust_int("tabular/zip.rs", rust), getattr(package, python)
        assert value == expected, f"tabular/zip.rs: {rust} = {value} != _package.{python} = {expected}"
    assert ast.literal_eval(_rust_const("tabular/extent.rs", "BOM")) == package._BOM, "tabular/extent.rs: BOM"
    # Bornes `{0,16}` et `{1,16}` de `_ODD_REF` : lettres puis chiffres / letters then digits.
    bounds = [int(b) for b in re.findall(rb"\{\d+,(\d+)\}", package._ODD_REF.pattern)]
    rust_bounds = [_rust_int("tabular/extent.rs", "MAX_LETTERS"), _rust_int("tabular/extent.rs", "MAX_DIGITS")]
    assert bounds == rust_bounds, f"tabular/extent.rs: MAX_LETTERS, MAX_DIGITS {rust_bounds} != _ODD_REF {bounds}"
    # Surface dense du noyau : jamais sous la borne de la garde (sinon refus silencieux) / never below the guard's.
    dense = _rust_int("tabular/python.rs", "MAX_DENSE")
    assert dense >= package.MAX_SHEET_AREA, f"tabular/python.rs: MAX_DENSE {dense} < MAX_SHEET_AREA"
    sheets = _rust_source("tabular/python.rs")
    kinds = (reader._WORKSHEET, reader._CHARTSHEET, "visible")
    assert all(f'"{kind}"' in sheets for kind in kinds), f"tabular/python.rs: sheets ne rend pas / lacks {kinds}"


def _rib_groups(letters: dict[str, str]) -> list[str]:
    return ["".join(sorted(c for c, digit in letters.items() if digit == str(v))) for v in range(10)]


def _translated(table: dict[int, int]) -> str:
    return "".join(chr(key) for key, _ in sorted(table.items(), key=lambda item: item[1]))


# (fichier Rust, constante, « module:nom » Python, forme) / (Rust file, constant, Python "module:name", shape).
_VALIDATOR_TABLES = (
    ("validators/checksums.rs", "LUHN_DOUBLE", "gdprguardian.validators.checksums:_LUHN_DOUBLE", "ints"),
    ("validators/checksums.rs", "LUHN_DOUBLE", "gdprguardian.validators.es:_LUHN_DOUBLE", "ints"),
    ("validators/checksums.rs", "VERHOEFF_D", "gdprguardian.validators.checksums:_VERHOEFF_D", "ints"),
    ("validators/checksums.rs", "VERHOEFF_P", "gdprguardian.validators.checksums:_VERHOEFF_P", "ints"),
    ("validators/checksums.rs", "GEN", "gdprguardian.validators.checksums:_BECH32_GEN", "ints"),
    ("validators/checksums.rs", "B58_ALPHABET", "gdprguardian.validators.checksums:_B58_ALPHABET", "text"),
    ("validators/checksums.rs", "BECH32_CHARSET", "gdprguardian.validators.checksums:_BECH32_CHARSET", "text"),
    ("validators/fr.rs", "SEX_DIGITS", "gdprguardian.validators.fr:_SEX_DIGITS", "chars"),
    ("validators/fr.rs", "TVA_ALPHABET", "gdprguardian.validators.fr:_TVA_ALPHABET", "text"),
    ("validators/fr.rs", "GROUPS", "gdprguardian.validators.fr:_RIB_LETTERS", "rib"),
    ("validators/ch.rs", "EAN13_WEIGHTS", "gdprguardian.validators.ch:_EAN13_WEIGHTS", "ints"),
    ("validators/ch.rs", "UID_WEIGHTS", "gdprguardian.validators.ch:_UID_WEIGHTS", "ints"),
    ("validators/ch.rs", "VAT_SUFFIXES", "gdprguardian.validators.ch:_VAT_SUFFIXES", "strings"),
    ("validators/de.rs", "STNR_LAENDER", "gdprguardian.validators.de:_STNR_LAENDER", "strings"),
    ("validators/de.rs", "DOCUMENT_ALPHABET", "gdprguardian.validators.de:_DOCUMENT_ALPHABET", "chars"),
    ("validators/de.rs", "RVNR_WEIGHTS", "gdprguardian.validators.de:_RVNR_WEIGHTS", "ints"),
    ("validators/de.rs", "KVNR_WEIGHTS", "gdprguardian.validators.de:_KVNR_WEIGHTS", "ints"),
    ("validators/de.rs", "LICENSE_WEIGHTS", "gdprguardian.validators.de:_LICENSE_WEIGHTS", "ints"),
    ("validators/es.rs", "DNI_LETTERS", "gdprguardian.validators.es:DNI_LETTERS", "text"),
    ("validators/es.rs", "CIF_KINDS", "gdprguardian.validators.es:_CIF_KINDS", "chars"),
    ("validators/es.rs", "CIF_LETTER_KINDS", "gdprguardian.validators.es:_CIF_LETTER_KINDS", "chars"),
    ("validators/es.rs", "CIF_DIGIT_KINDS", "gdprguardian.validators.es:_CIF_DIGIT_KINDS", "chars"),
    ("validators/es.rs", "CIF_LETTERS", "gdprguardian.validators.es:_CIF_LETTERS", "text"),
    ("validators/it.rs", "MONTHS", "gdprguardian.validators.it:_MONTHS", "text"),
    ("validators/it.rs", "MONTH_DAYS", "gdprguardian.validators.it:_MONTH_DAYS", "ints"),
    ("validators/it.rs", "HOMOCODY", "gdprguardian.validators.it:_UNDO_HOMOCODY", "translation"),
    ("validators/it.rs", "ODD_TABLE", "gdprguardian.validators.it:_ODD_TABLE", "ints"),
    ("validators/nl.rs", "BSN_WEIGHTS", "gdprguardian.validators.nl:_BSN_WEIGHTS", "ints"),
    ("validators/pt.rs", "NIF_WEIGHTS", "gdprguardian.validators.pt:_NIF_WEIGHTS", "ints"),
    ("validators/pt.rs", "NISS_WEIGHTS", "gdprguardian.validators.pt:_NISS_WEIGHTS", "ints"),
    ("validators/pt.rs", "PHONE_PREFIXES", "gdprguardian.validators.pt:_PHONE_PREFIXES", "strings"),
)


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
@pytest.mark.parametrize(("file", "constant", "target", "shape"), _VALIDATOR_TABLES,
                         ids=[f"{t[0]}:{t[1]}<-{t[2].rsplit('.', 1)[1]}" for t in _VALIDATOR_TABLES])
def test_copied_validator_tables_equal_their_python_sources(file: str, constant: str, target: str,
                                                            shape: str) -> None:
    module, _, name = target.partition(":")
    value = getattr(_module(module), name)
    if shape == "ints":
        flat: list[int] = []
        pending = [value]
        while pending:  # tuples imbriqués aplatis dans l'ordre / nested tuples flattened in order
            item = pending.pop(0)
            if isinstance(item, (tuple, list)):
                pending[:0] = list(item)
            else:
                flat.append(item)
        rust, python = _rust_ints(file, constant), flat
    elif shape == "chars":
        rust, python = set(_rust_strings(file, constant)[0]), set(value)
    elif shape == "strings":
        rust, python = _rust_strings(file, constant), list(value)
    elif shape == "rib":
        rust, python = _rust_strings(file, constant), _rib_groups(value)
    elif shape == "translation":
        rust, python = _rust_strings(file, constant), [_translated(value)]
    else:
        rust, python = _rust_strings(file, constant), [value]
    assert rust == python, f"{file}: {constant} = {rust} != {target} = {python}"


# --- noyau présent : aucun repli silencieux / with the core: no silent fallback ---------------------------------


def test_every_native_twin_builds_when_the_core_is_present() -> None:
    from gdprguardian import Anonymizer, _native

    if not _native.available():
        pytest.skip("noyau Rust absent ou désactivé / Rust core missing or disabled")
    from gdprguardian import locale
    from gdprguardian.detectors import fr as fr_detectors
    from gdprguardian.detectors import intl as intl_detectors
    from gdprguardian.heuristics import fr_address, fr_names, organizations

    # Un écart de contrat (constantes, signature) ferait retomber en silence sur Python : 3 à 4 fois plus lent.
    # A contract mismatch (constants, signature) would silently fall back to Python: 3-4 times slower.
    twins = {"FrenchNameDetector": fr_names._native_detector(), "FrenchAddressDetector": fr_address._native_twin(),
             "OrganizationDetector": organizations._native_twin(), "NirBirthDateDetector": fr_detectors._native_twin(),
             "EmailDetector": intl_detectors._native_email(), "IbanDetector": intl_detectors._native_iban(),
             "InternationalPhoneDetector": intl_detectors._native_phone(), "UnicodeTables": _native.unicode_tables(),
             "Preparer": _native.preparer(), "LanguageDetector": locale._native_detector()}
    assert [name for name, twin in twins.items() if twin is None] == []
    anonymizer = Anonymizer(countries="all")
    assert anonymizer.native and anonymizer._finalizer is not None
    # Moteur fusionné construit (un plan refusé rendrait None en silence), et chaque détecteur intégré qui a un
    # plan natif le fournit : aucun ne retombe sur un appel Python. Fused engine built (a refused plan would
    # silently give None), and every built-in detector with a native plan provides it: none falls back to Python.
    assert anonymizer._fused is not None
    without_plan = [type(detector).__name__ for pack in anonymizer.packs for detector in anonymizer._detectors[pack.id]
                    if "native_plan" in vars(type(detector)) and detector.native_plan() is None]
    assert without_plan == []


def test_every_native_validator_has_a_contract() -> None:
    from gdprguardian import _native

    if not _native.available():
        pytest.skip("noyau Rust absent ou désactivé / Rust core missing or disabled")
    native = set(_native.core().native_validators())
    recorded = {name for name, _ in VALIDATORS}
    assert native == recorded, (f"validateurs natifs sans contrat / native validators without a contract: "
                                f"{sorted(native - recorded)}; contrats sans validateur natif / contracts without a "
                                f"native validator: {sorted(recorded - native)}")


# Classes Perl (`\s`, `\w`…) des motifs de packs analysés par le noyau : elles suivent `re`, pas les propriétés
# Unicode de Rust (U+001C-U+001F sont des blancs pour `\s` ; marques combinantes, `‿` et `²` diffèrent pour `\w`).
# Perl classes of pack patterns scanned by the core follow `re`, not Rust's Unicode properties.
_CLASS_PROBES = (
    ("Mme Claire Dubois, née le 12\x1cmai 1985 à Lyon.", "FR_BIRTH_DATE_TEXT"),
    ("Société X, RCS\x1fParis B 732 829 320, capital 1000 €", "FR_RCS"),
    ("Écrire à jean\N{SUPERSCRIPT TWO} [at] exemple [dot] fr demain", "EMAIL_OBFUSCATED"),
    ("Profil : https://github.com/jeanx\N{COMBINING ACUTE ACCENT}dupont merci", "URL_PERSONAL"),
)


@cache
def _engine(native: bool) -> Any:
    from gdprguardian import Anonymizer

    return Anonymizer(countries="all", native=native)


@pytest.mark.parametrize(("text", "recognizer"), _CLASS_PROBES, ids=[p[1] for p in _CLASS_PROBES])
def test_perl_classes_of_natively_scanned_patterns_follow_python_re(text: str, recognizer: str) -> None:
    from gdprguardian import _native

    if not _native.available():
        pytest.skip("noyau Rust absent ou désactivé / Rust core missing or disabled")

    def spans(native: bool) -> list[tuple[int, int, str | None]]:
        return [(s.start, s.end, s.value) for s in _engine(native).analyze(text).spans if s.source == recognizer]

    assert spans(True) == spans(False), recognizer


# --- contrat du noyau : même version que le paquet / core contract: same version as the package -----------------


@pytest.mark.skipif(not RUST.is_dir(), reason="sources Rust absentes / Rust sources missing")
def test_rust_contract_matches_the_package() -> None:
    from gdprguardian import _native

    declared = re.findall(r'm\.add\("CONTRACT", (\d+)u32\)', _rust_source("lib.rs"))
    assert declared == [str(_native.CONTRACT)], f"lib.rs CONTRACT {declared} != _native.CONTRACT {_native.CONTRACT}"


def test_loaded_core_contract_matches_the_package() -> None:
    from gdprguardian import _native

    if not _native.available():
        pytest.skip("noyau Rust absent ou désactivé / Rust core missing or disabled")
    assert _native.core().CONTRACT == _native.CONTRACT


# Noyau factice placé en tête du chemin / fake core put first on the path. `{contract}` : ligne du contrat.
_FAKE_CORE = '''
"""Noyau factice / fake core."""
__version__ = "0.1.0"
{contract}


class UnicodeTables:  # signature d'un noyau ancien / an older core's signature
    def __init__(self, bmp, plane_flags):
        raise AssertionError("noyau écarté appelé / set-aside core called")


def __getattr__(name):
    raise {missing}(f"noyau factice appelé / fake core called: {{name}}")
'''
# Lancé avec le noyau factice : avertissements, noyau retenu, résultats / run over the fake core.
_WITH_FAKE_CORE = r'''
import json, sys, warnings
sys.path.insert(0, sys.argv[1])
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    from gdprguardian import Anonymizer, _native
    from gdprguardian.engine import Settings
engines = [Anonymizer(countries="all", native=False), Anonymizer(Settings(countries="all", native=False))]
if sys.argv[2] == "all":
    engines.append(Anonymizer(countries="all"))
outputs = []
for engine in engines:
    for text in json.loads(sys.argv[3]):
        result = engine.anonymize(text)
        report = {k: v for k, v in result.report.items() if k not in ("timings_ms", "native")}
        outputs.append([result.text, report, [repr(s) for s in result.analysis.spans]])
messages = [str(w.message) for w in caught if issubclass(w.category, RuntimeWarning)]
print(json.dumps({"core": _native.core() is not None, "warnings": messages, "outputs": outputs}))
'''


def _with_fake_core(tmp_path: Path, contract: str, missing: str, engines: str, texts: list[str]) -> dict[str, Any]:
    import json
    import subprocess

    (tmp_path / "gdprguardian_core.py").write_text(_FAKE_CORE.format(contract=contract, missing=missing),
                                               encoding="utf-8")
    done = subprocess.run([sys.executable, "-c", _WITH_FAKE_CORE, str(tmp_path), engines, json.dumps(texts)],
                          capture_output=True, text=True, timeout=300, check=False)
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def _pure_outputs(texts: list[str], engines: int) -> list[list[Any]]:
    """Mêmes sorties, référence Python de ce processus / the same outputs, this process's Python reference."""
    from gdprguardian import Anonymizer

    outputs = []
    for _ in range(engines):
        for text in texts:
            result = Anonymizer(countries="all", native=False).anonymize(text)
            report = {k: v for k, v in result.report.items() if k not in ("timings_ms", "native")}
            outputs.append([result.text, report, [repr(s) for s in result.analysis.spans]])
    return outputs


_SAMPLES = ["Contact : M. Jean Dupont, 12 rue de la Paix 75002 Paris, jean.dupont@exemple.fr, IBAN FR76 3000 6000 "
            "0112 3456 7890 189, NIR 1 85 05 78 006 084 91, né le 03/05/1985, tél. +33 6 12 34 56 78, Acme SAS.",
            "Hélène Lefèvre, née le 3 décembre 1985, 4 avenue des Prés 75011 Paris."]


@pytest.mark.parametrize("contract", ["", "CONTRACT = 1", "CONTRACT = 999"], ids=["absent", "older", "newer"])
def test_core_of_another_contract_is_set_aside(tmp_path: Path, contract: str) -> None:
    """Noyau d'une autre version : un avertissement nomme le remède, le noyau est écarté et tout `Anonymizer`, natif
    demandé ou non, rend exactement la référence Python. Core of another version: a warning names the fix, the core
    is set aside and every `Anonymizer`, native requested or not, gives exactly the Python reference.
    """
    seen = _with_fake_core(tmp_path, contract, "AttributeError", "all", _SAMPLES)
    assert not seen["core"]
    assert len(seen["warnings"]) == 1 and "pip install --force-reinstall" in seen["warnings"][0]
    assert seen["outputs"] == _pure_outputs(_SAMPLES, 3)


def test_native_false_never_touches_the_core(tmp_path: Path) -> None:
    """`Settings(native=False)` : aucun jumeau construit, aucun attribut du noyau lu (le noyau factice échoue au
    moindre accès). No twin built, no core attribute read (the fake core fails on any access).
    """
    from gdprguardian import _native

    seen = _with_fake_core(tmp_path, f"CONTRACT = {_native.CONTRACT}", "AssertionError", "pure", _SAMPLES)
    assert seen["core"] and seen["warnings"] == []
    assert seen["outputs"] == _pure_outputs(_SAMPLES, 2)


# --- table à jour / updated table ---------------------------------------------------------------------------


def _print_tables() -> None:
    """Imprime les tables avec les empreintes actuelles (à recopier après revue) / prints the current tables."""
    out = ["    # BEGIN CONTRACTS"]
    for tests, module, entries in CONTRACTS:
        out.append(f'    ({_FAMILIES[tests]}, "{module}", (')
        for target, twins, _ in entries:
            parts = [f'"{target}"', f'"{twins}"', f'"{fingerprint(source_node(f"{module}:{target}"))}"']
            line = f"        ({', '.join(parts)}),"
            if len(line) > 120:  # longueur de ligne de Ruff / Ruff's line length
                line = f"        ({', '.join(parts[:2])},\n         {parts[2]}),"
            if max(map(len, line.splitlines())) > 120:
                line = f"        ({parts[0]},\n         {parts[1]},\n         {parts[2]}),"
            out.append(line)
        out.append("    )),")
    out.append("    # END CONTRACTS")
    out.append("    # BEGIN VALIDATORS")
    out.extend(f'    ("{name}", "{validator_fingerprint(name)[0]}"),' for name, _ in VALIDATORS)
    out.append("    # END VALIDATORS")
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    _print_tables()
