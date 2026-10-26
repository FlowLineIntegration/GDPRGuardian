"""Typage des colonnes : statistiques, lexique d'en-têtes, preuves / column typing."""

from __future__ import annotations

import math
import random

import pytest
from tabular_factories import luhn_complete, nir

from gdprguardian import Anonymizer
from gdprguardian.tabular._columns import DETECT, MASK, YEAR, ColumnTyper, binomial_tail, sample_evenly, wilson_lower


@pytest.fixture(scope="module")
def typer() -> ColumnTyper:
    anonymizer = Anonymizer(countries=("FR",))
    return ColumnTyper(anonymizer.packs, anonymizer.settings)


def test_statistics_match_reference_values() -> None:
    # Valeurs de référence de la recherche (docs/research/gap-spreadsheet-structure-column-typing).
    assert binomial_tail(8, 20, 0.1) == pytest.approx(4.3e-4, rel=0.1)
    assert binomial_tail(3, 10, 1 / 97) == pytest.approx(1.2e-4, rel=0.1)
    assert wilson_lower(24, 30) == pytest.approx(0.627, abs=0.002)
    assert binomial_tail(0, 10, 0.5) == 1.0
    assert binomial_tail(11, 10, 0.5) == 0.0
    assert wilson_lower(0, 0) == 0.0


def test_binomial_tail_against_exact_sum() -> None:
    for n, k, p in ((50, 20, 0.1), (30, 5, 0.2), (12, 12, 0.5)):
        exact = sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))
        assert binomial_tail(k, n, p) == pytest.approx(exact, rel=1e-9)


def test_even_sample_keeps_head_middle_and_tail() -> None:
    items = list(range(10_000))
    sample = sample_evenly(items, 100)
    assert len(sample) == 100 and sample[0] == 0 and sample[-1] > 9_800
    assert sample_evenly([1, 2], 100) == [1, 2]


@pytest.mark.parametrize(("header", "label", "role"), [
    ("Nom", "PERSON", "surname"),
    ("Prénom", "PERSON", "given"),
    ("NOM PRENOM", "PERSON", "full"),
    ("Nom du client", "PERSON", "full"),
    ("Adresse e-mail", "EMAIL", ""),
    ("Téléphone du contact", "PHONE", ""),
    ("N° SS", "NIR", ""),
    ("Date de naissance", "BIRTH_DATE", ""),
    ("Code postal", "POSTAL_CODE", ""),
    ("N° client", "ID", ""),
    ("Code client", "ID", ""),
    ("Matricule", "ID", ""),
    ("First name", "PERSON", "given"),
    ("Date of birth", "BIRTH_DATE", ""),
    ("Nom de naissance", "PERSON", "surname"),
])
def test_header_lexicon(typer: ColumnTyper, header: str, label: str, role: str) -> None:
    match = typer.match_header(header)
    assert match is not None and (match.label, match.role) == (label, role)


@pytest.mark.parametrize("header", ["Nom du produit", "Nom de l'entreprise", "Lieu de naissance", "Ville",
                                    "Montant", "Statut", "Type de contrat"])
def test_negative_cues_and_non_pii_headers(typer: ColumnTyper, header: str) -> None:
    assert typer.match_header(header) is None


def test_checksum_evidence_types_a_headerless_nir_column(typer: ColumnTyper) -> None:
    rng = random.Random(1)
    values = [nir(f"1{rng.randrange(10**12):012d}") for _ in range(40)]
    values[3] = values[3][:-1] + str((int(values[3][-1]) + 1) % 10)  # une coquille / one typo
    ctype = typer.classify("", [(float(v), v) for v in values], len(values), frozenset())
    assert (ctype.label, ctype.action) == ("NIR", MASK)
    assert ctype.evidence.startswith("checksum 39/40")


def test_random_luhn_numbers_are_not_typed_without_header(typer: ColumnTyper) -> None:
    rng = random.Random(2)
    values = [f"{rng.randrange(10**8, 10**9)}" for _ in range(60)]
    ctype = typer.classify("Commande", [(v, v) for v in values], len(values), frozenset())
    assert ctype.action == DETECT and ctype.label is None


def test_company_ids_follow_the_policy() -> None:
    sirets = [luhn_complete(f"7328293200{i:03d}") for i in range(20)]
    values = [(s, s) for s in sirets]
    kept = Anonymizer(countries=("FR",))
    masked = Anonymizer(countries=("FR",), company_ids="mask")
    keep_type = ColumnTyper(kept.packs, kept.settings).classify("SIRET", values, 20, kept.context_groups("SIRET"))
    mask_type = ColumnTyper(masked.packs, masked.settings).classify("SIRET", values, 20,
                                                                    masked.context_groups("SIRET"))
    assert (keep_type.label, keep_type.action) == ("SIRET", DETECT)
    assert (mask_type.label, mask_type.action) == ("SIRET", MASK)


def test_header_breaks_the_siret_card_tie(typer: ColumnTyper) -> None:
    # Un SIRET compact commençant par 4 passe aussi Luhn comme une carte / compact SIRETs pass Luhn like cards.
    siren = luhn_complete("44306184")
    sirets = [luhn_complete(f"{siren}{i:04d}") for i in range(30)]
    ctype = typer.classify("SIRET", [(s, s) for s in sirets], 30, frozenset({"FR:siret"}))
    assert ctype.label == "SIRET"


def test_header_needs_values_that_do_not_contradict_it(typer: ColumnTyper) -> None:
    names = [("Dupont", "Dupont"), ("Martin", "Martin"), ("Le Gall", "Le Gall")]
    assert typer.classify("Nom", names, 3, frozenset()).action == MASK
    numbers = [(1.0, "1"), (2.0, "2"), (3.0, "3")]
    assert typer.classify("Nom", numbers, 3, frozenset()).action == DETECT


def test_birth_date_column_is_generalised(typer: ColumnTyper) -> None:
    import datetime as dt

    values = [(dt.date(1985, 3, 14), "1985-03-14"), ("14/03/1990", "14/03/1990")]
    assert typer.classify("Date de naissance", values, 2, frozenset()).action == YEAR


def test_headerless_full_names(typer: ColumnTyper) -> None:
    names = ["Jean DUPONT", "Marie Durand", "Pierre MARTIN", "Sophie Bernard", "Luc PETIT", "Anne Moreau"]
    ctype = typer.classify("", [(n, n) for n in names], len(names), frozenset())
    assert (ctype.label, ctype.action, ctype.evidence) == ("PERSON", MASK, "values")
    cities = ["PARIS", "LYON", "NANTES", "LILLE", "BREST", "NICE"]
    assert typer.classify("", [(c, c) for c in cities], 6, frozenset()).action == DETECT


def test_excluded_entities_are_never_masked() -> None:
    anonymizer = Anonymizer(countries=("FR",), exclude_entities=frozenset({"PERSON"}))
    typer = ColumnTyper(anonymizer.packs, anonymizer.settings)
    assert typer.classify("Nom", [("Dupont", "Dupont")], 1, frozenset()).action == DETECT


def test_canonical_values_match_the_engine(typer: ColumnTyper) -> None:
    assert typer.canonical("PHONE", "06 12 34 56 78") == typer.canonical("PHONE", "0612345678") == "+33612345678"
    assert typer.canonical("EMAIL", "Jean@Exemple.FR") == "Jean@exemple.fr"
    assert typer.canonical("PERSON", " Dupont ") == "Dupont"
