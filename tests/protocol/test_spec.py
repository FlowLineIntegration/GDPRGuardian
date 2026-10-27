"""Définitions du protocole 1.1 : groupes d'opérateurs, familles, périmètre / protocol 1.1 definitions."""

from __future__ import annotations

import pytest
from tools.eval.mutate import MUTATIONS
from tools.eval.schema import DIRECT, GOLD_LABELS
from tools.protocol import spec


def test_operator_groups_partition_the_red_team() -> None:
    """Chaque opérateur de tools/eval/mutate.py est dans un seul groupe / every operator sits in exactly one group."""
    names = [m.name for m in MUTATIONS]
    grouped = [name for group in spec.REDTEAM_GROUPS.values() for name in group]
    assert len(grouped) == len(set(grouped)), "opérateur dans deux groupes / operator in two groups"
    assert sorted(grouped) == sorted(names)
    assert (len(spec.REDTEAM_EVERYDAY), len(spec.REDTEAM_OBFUSCATION), len(spec.REDTEAM_OCR)) == (25, 25, 1)
    # Lettres espacées d'un PDF copié : du quotidien (mutate.py la classe « layout ») / PDF letter spacing: everyday.
    assert "letter_spacing" in spec.REDTEAM_EVERYDAY


def test_two_indexes_and_apart_families() -> None:
    """Documents normalisés (4 familles), documents difficiles (équipe rouge entière), le reste à part."""
    assert [f.name for f in spec.FAMILIES] == ["synthetic_fr", "bodacc_fr", "boamp_fr", "parlamint_fr"]
    assert not [f for f in spec.FAMILIES if f.kind == "redteam"]  # aucune équipe rouge / no red team in it
    assert [f.name for f in spec.HARD_FAMILIES] == ["redteam_fr", "redteam_obfuscation_fr", "redteam_ocr_fr"]
    assert [f.name for f in spec.APART_FAMILIES] == ["old_press_fr", "mapa_fr"]
    # Indice difficile : les trois groupes, donc les 51 opérateurs, chacun une fois / all 51 operators, once each.
    assert {spec.HARD_GROUP_FAMILY[g]: spec.REDTEAM_GROUPS[g] for g in spec.REDTEAM_GROUPS} == {
        f.name: f.operators for f in spec.HARD_FAMILIES}
    hard_ops = [op for f in spec.HARD_FAMILIES for op in f.operators]
    assert sorted(hard_ops) == sorted(m.name for m in MUTATIONS)
    # La clé redteam_fr reste celle des formats du quotidien (le site lit f_red_*) / redteam_fr stays everyday.
    assert spec.HARD_FAMILIES[0].operators == spec.REDTEAM_EVERYDAY
    assert set(spec.INDEXES) == {"normalised", "hard"} and spec.NORMALISED_TARGET == 0.95
    # Chaque corpus réel français est soit dans l'indice, soit à part, soit témoin ; jamais deux fois.
    french = [c for c in spec.REAL_CORPORA if c not in spec.OUT_OF_SCOPE and c not in spec.NEGATIVE_CONTROL]
    placed = [c for f in spec.FAMILIES + spec.HARD_FAMILIES + spec.APART_FAMILIES for c in f.corpora]
    assert sorted(placed) == sorted(french)
    assert set(spec.INDEX_CORPORA) == {"bodacc_fr", "boamp_fr", "parlamint_fr"}
    # Le plan de campagne ne change pas : tous les corpus passent encore par le service / same campaign plan.
    assert len(spec.REAL_CORPORA) == 15


def test_scope_of_a_leak() -> None:
    """Noms de sociétés et villes seules hors calcul ; personnes et coordonnées comptées / scope of a leak."""
    assert not {"ORG", "LOCATION"} & spec.REAL_DIRECT_LABELS
    assert {"PERSON", "ADDRESS", "EMAIL", "PHONE"} <= spec.REAL_DIRECT_LABELS
    for label in ("ORG", "LOCATION", "COMPANY_ID"):
        assert GOLD_LABELS[label] != DIRECT
    for label in ("PERSON", "ADDRESS", "EMAIL", "PHONE", "SIRET", "SIREN"):  # SIRET/SIREN : entrepreneurs individuels
        assert GOLD_LABELS[label] == DIRECT


def test_history_is_kept() -> None:
    """La campagne 1.0 est listée : les moitiés test ne sont plus aveugles / the 1.0 campaign is listed."""
    assert spec.PROTOCOL_VERSION == "1.2" and spec.SUPPORTED_VERSIONS == ("1.1", "1.2")
    assert any(c["date"] == "2026-10-26" and c["engine"] == "1.0.0+0c3ff9fc1fb0" for c in spec.EARLIER_CAMPAIGNS)
    assert any(t["by"] == "public protocol campaign 1.0" for t in spec.TEST_HALVES_MEASURED_BEFORE)
    assert spec.PREVIOUS_VERSIONS[0]["version"] == "1.0"
    assert spec.PREVIOUS_VERSIONS[0]["confidence_index"].startswith("61.8")
    # 1.2 : la campagne 1.1 reste publiée et rend les moitiés test encore moins aveugles / the 1.1 campaign is listed.
    assert spec.PREVIOUS_VERSIONS[1]["version"] == "1.1"
    assert spec.PREVIOUS_VERSIONS[1]["confidence_index"].startswith("96.9")
    assert any(c["protocol"] == "1.1" and c["engine"] == "1.0.1+4bb5c465425e" for c in spec.EARLIER_CAMPAIGNS)
    assert any(t.get("added_by") == "1.2" for t in spec.TEST_HALVES_MEASURED_BEFORE)


def test_modes_1_2() -> None:
    """Deux modes, le défaut d'abord ; garde-fou des leurres en essentiel seulement / two modes, decoy guard."""
    assert spec.MODES == ("fort", "essentiel")
    assert spec.DECOY_GUARD_MODES == ("essentiel",)
    assert set(spec.MODE_SITE_PREFIX) == set(spec.MODES) == set(spec.MODE_TITLES)
    from tools.protocol.plan import build_plan, check_modes, service_options

    assert service_options("FR", None) == {"countries": "FR", "profile": "standard", "label_language": "fr"}
    assert service_options("FR", "fort") == {"countries": "FR", "mode": "fort", "label_language": "fr"}
    with pytest.raises(ValueError):
        check_modes(("fort", "fort"))
    with pytest.raises(ValueError):
        check_modes(("personnalise",))
    legacy = build_plan(synthetic_seeds=(2026102581,), synthetic_docs_per_seed=4, redteam_seeds=(),
                        redteam_bases_per_seed=0)
    modal = build_plan(synthetic_seeds=(2026102581,), synthetic_docs_per_seed=4, redteam_seeds=(),
                       redteam_bases_per_seed=0, modes=spec.MODES)
    assert legacy.protocol == "1.1" and modal.protocol == "1.2" and legacy.units == modal.units
    assert legacy.plan_id != modal.plan_id
    # Empreinte d'un plan 1.1 inchangée par la 1.2 / a 1.1 plan's fingerprint is unchanged by 1.2.
    import hashlib
    import json

    payload = json.dumps({"protocol": "1.1", "units": [u.uid + f"+{u.count}" for u in legacy.units]},
                         separators=(",", ":"))
    assert legacy.plan_id == hashlib.sha256(payload.encode()).hexdigest()[:16]
