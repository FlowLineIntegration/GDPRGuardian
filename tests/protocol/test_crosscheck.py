"""Résumé du contrôle croisé : chaque écart rangé et expliqué / cross-check summary: every difference classified."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.protocol.crosscheck import HEADLINE_KEYS, classify, compare, write_summary


def _summary(**changes: float) -> dict[str, Any]:
    base = {"headline": dict.fromkeys(HEADLINE_KEYS, 0.5), "ci95": [0.4, 0.6],
            "labels": {"PERSON": {"precision": 0.9, "f2": 0.9, "char_recall": 0.95}},
            "confusion": [{"gold": "PERSON", "system": "PERSON", "count": 10}],
            "leaks": {"strict": {"k": 3, "rate": 0.1}}}
    for path, value in changes.items():
        target = base
        *parents, leaf = path.split(".")
        for key in parents:
            target = target[key]
        target[leaf] = value
    return base


def _run(service: dict[str, Any], inprocess: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    return {"corpus": {"seed": 20261024, "base_docs": 540, "mutated_docs": 0, "countries": "FR"},
            "service_docs_per_second": 100.0, "service_errors": {"base": {}, "mutated": {}},
            "headline": {"service": service["headline"], "inprocess": inprocess["headline"],
                         "reference": reference["headline"]},
            "vs_inprocess_base": compare(service, inprocess), "vs_reference_base": compare(service, reference)}


def test_boundary_and_engine_differences_are_explained(tmp_path: Path) -> None:
    # Service et en processus : seule la précision par libellé du système diffère (frontière) ; tous deux diffèrent
    # de la référence sur une fuite (moteur changé) et sur l'intervalle (tirages).
    service = _summary(**{"labels.PERSON.precision": 0.8})
    inprocess = _summary()
    reference = _summary(**{"leaks.strict.k": 4})
    reference["ci95"] = [0.41, 0.6]
    run = _run(service, inprocess, reference)
    parts = classify(run, "base")
    assert parts["service_vs_inprocess"] == {"leaves": parts["service_vs_inprocess"]["leaves"], "different": 1,
                                             "boundary": 1, "unexplained": []}
    ref = parts["service_vs_reference"]
    assert (ref["engine"], ref["random_draws"], ref["boundary"], ref["unexplained"]) == (1, 1, 1, [])
    paths, verdict = write_summary({"FR": run}, tmp_path, "2026-10-26", "frozen copy abc")
    assert verdict == {"tool_validated": True, "runs": {"FR": True}}
    saved = json.loads(paths[0].read_text(encoding="utf-8"))
    assert saved["runs"]["FR"]["headline_service_equals_inprocess"] is True
    assert "Outil validé / tool validated: oui / yes" in paths[1].read_text(encoding="utf-8")


def test_a_tool_difference_outside_the_boundary_is_not_validated(tmp_path: Path) -> None:
    service = _summary(**{"leaks.strict.k": 5, "labels.PERSON.char_recall": 0.9})
    run = _run(service, _summary(), _summary())
    parts = classify(run, "base")
    assert parts["service_vs_inprocess"]["unexplained"] == ["labels.PERSON.char_recall", "leaks.strict.k"]
    _, verdict = write_summary({"auto": run}, tmp_path, "2026-10-26", "x")
    assert verdict["tool_validated"] is False
    # Une erreur du service suffit aussi / a service error is enough too.
    clean = _run(_summary(), _summary(), _summary())
    clean["service_errors"] = {"base": {"doc-1": "DocumentRefused"}, "mutated": {}}
    assert write_summary({"auto": clean}, tmp_path, "2026-10-27", "x")[1]["tool_validated"] is False
