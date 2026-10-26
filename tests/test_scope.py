"""Portée irréversible et coréférence / irreversible scope and coreference.

Chaque test tourne sur la portée Rust (si le noyau est installé) et sur la référence Python.
Each test runs on the Rust scope (when the core is installed) and on the Python reference.
"""

from __future__ import annotations

import pytest

from gdprguardian import _native
from gdprguardian.scope import Scope, split_person_name

_IMPLEMENTATIONS = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                         reason="noyau Rust absent / no Rust core")),
                    pytest.param(False, id="python")]


@pytest.fixture(params=_IMPLEMENTATIONS)
def native(request) -> bool:
    return request.param


def _person(scope: Scope, text: str) -> str:
    return scope.placeholder("PERSON", "PERSON", text)


def test_name_variants_share_one_placeholder(native):
    with Scope(native=native) as scope:
        assert scope.native == native
        first = _person(scope, "Jean Dupont")
        assert _person(scope, "M. Dupont") == first
        assert _person(scope, "J. Dupont") == first
        assert _person(scope, "DUPONT Jean") == first
        assert _person(scope, "jean dupont") == first
        assert _person(scope, "Claire Martin") != first


def test_surname_first_then_full_name(native):
    with Scope(native=native) as scope:
        bare = _person(scope, "M. Dupont")
        assert _person(scope, "Jean Dupont") == bare


def test_same_surname_two_people_stay_distinct(native):
    with Scope(native=native) as scope:
        jean = _person(scope, "Jean Dupont")
        marie = _person(scope, "Marie Dupont")
        assert jean != marie
        # Ambigu : ni Jean ni Marie / ambiguous: neither Jean nor Marie.
        assert _person(scope, "M. Dupont") not in (jean, marie)


def test_part_of_a_hyphenated_surname_joins_that_person(native):
    # Tests terrain du 26/10 : « Mme Kervadec » après « Mme Solène Kervadec-Moulin » / field test, 26 October.
    with Scope(native=native) as scope:
        solene = _person(scope, "Solène Kervadec-Moulin")
        assert _person(scope, "Mme Kervadec") == solene
        assert _person(scope, "MOULIN") == solene
        assert _person(scope, "Mme Kervadec-Moulin") == solene
        assert _person(scope, "Jean Martin") != solene
    with Scope(native=native) as scope:
        # Deux noms composés partagent « Martin » : ambigu, nouvelle personne / two share a part: a new person.
        first = _person(scope, "Anne Martin-Durand")
        second = _person(scope, "Paul Martin-Petit")
        assert _person(scope, "Mme Martin") not in (first, second)
        assert _person(scope, "Mme Durand") == first
    with Scope(native=native) as scope:
        # Un prénom vu seul, puis le nom composé : les parties suivent la personne / parts follow the person.
        alone = _person(scope, "Hélène")
        assert _person(scope, "Hélène Le-Gall") == alone
        assert _person(scope, "Mme Gall") == alone


def test_given_name_alone_then_full_name(native):
    with Scope(native=native) as scope:
        alone = _person(scope, "Pierre")
        assert _person(scope, "Pierre Martin") == alone


def test_numbering_per_label_and_consistency(native):
    with Scope(native=native) as scope:
        assert scope.placeholder("EMAIL", "EMAIL", "a@b.fr") == "[EMAIL_1]"
        assert scope.placeholder("EMAIL", "EMAIL", "c@d.fr") == "[EMAIL_2]"
        assert scope.placeholder("EMAIL", "EMAIL", "A@B.FR") == "[EMAIL_1]"
        assert scope.placeholder("NIR", "NATIONAL_ID", "185057800608491") == "[NIR_1]"


def test_reserved_placeholders_are_never_reused(native):
    with Scope(native=native) as scope:
        scope.reserve("Déjà présent : [PERSONNE_1] et [PERSONNE_2].")
        assert _person(scope, "Jean Dupont") == "[PERSONNE_3]"


def test_neutral_and_english_labels(native):
    with Scope(label_language="en", neutral=True, native=native) as scope:
        assert scope.placeholder("NIR", "NATIONAL_ID", "x") == "[NATIONAL_ID_1]"
        assert scope.placeholder("PERSON", "PERSON", "Jean Dupont") == "[PERSON_1]"


def test_scope_keeps_no_original_value():
    scope = Scope(native=False)
    scope.placeholder("PERSON", "PERSON", "Jean Dupont")
    scope.placeholder("EMAIL", "EMAIL", "jean.dupont@exemple.fr")
    stored = [*scope._indices, *(c.surname for c in scope._clusters)]
    assert all(isinstance(item, bytes) and len(item) == 16 for item in stored)
    blob = b"".join(stored)
    assert b"dupont" not in blob.lower() and b"jean" not in blob.lower()


@pytest.mark.skipif(not _native.available(), reason="noyau Rust absent / no Rust core")
def test_native_scope_keeps_key_and_digests_outside_python():
    scope = Scope()
    scope.placeholder("PERSON", "PERSON", "Jean Dupont")
    # Ni clé, ni empreinte, ni valeur côté Python / no key, digest or value on the Python side.
    assert scope.native and not any(hasattr(scope, name) for name in ("_key", "_hasher", "_indices", "_clusters"))
    assert not hasattr(scope._native_scope, "__dict__")
    scope.close()
    assert scope.closed


def test_closed_scope_is_unusable_and_wiped(native):
    scope = Scope(native=native)
    scope.placeholder("EMAIL", "EMAIL", "a@b.fr")
    scope.close()
    assert scope.closed
    with pytest.raises(RuntimeError):
        scope.placeholder("EMAIL", "EMAIL", "a@b.fr")


def test_split_person_name():
    assert split_person_name("M. Jean Dupont") == ("Jean", "Dupont")
    assert split_person_name("DUPONT Jean") == ("Jean", "DUPONT")
    assert split_person_name("Mme Martin") == (None, "Martin")
    assert split_person_name("J. Dupont") == ("J", "Dupont")
