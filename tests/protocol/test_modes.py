"""Protocole 1.2 : deux modes, deux chiffres par mode ; le résultat 1.1 se relit à l'identique / protocol 1.2."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from test_campaign import _factory, _real, _settings, _sources
from tools.protocol import spec
from tools.protocol.campaign import EXIT_DONE, State, load_state, run_campaign
from tools.protocol.cli import load_label_keys
from tools.protocol.merge_quality import MODE_KEYS, mode_values, quality_values
from tools.protocol.plan import Unit, build_plan
from tools.protocol.report import build_report, to_markdown, write_report

ROOT = Path(__file__).resolve().parents[2]
RESULT_1_1 = ROOT / "benchmarks" / "results" / "protocol-1.1-2026-10-26.json"


def _protocol_table() -> Any:
    path = ROOT / "site" / "tools" / "protocol_table.py"
    module_spec = importlib.util.spec_from_file_location("protocol_table_under_test", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _modal_plan(real: dict[str, list[dict[str, Any]]]) -> Any:
    return build_plan(synthetic_seeds=(2026102581,), synthetic_docs_per_seed=24, redteam_seeds=(2026102591,),
                      redteam_bases_per_seed=1, real_counts={k: len(v) for k, v in real.items()},
                      unit_synthetic=12, unit_redteam=1, unit_real=4, modes=spec.MODES)


@pytest.fixture(scope="module")
def modal_run(tmp_path_factory: pytest.TempPathFactory,
              engine_transport: Any) -> tuple[State, Any, Any, dict[str, Any]]:
    # Par la fixture : « from conftest import » prend tests/tabular/conftest.py dans la suite complète.
    # Through the fixture: "from conftest import" picks tests/tabular/conftest.py in the full suite.
    work = tmp_path_factory.mktemp("modes")
    real = _real()
    plan = _modal_plan(real)
    transport = engine_transport()
    code = run_campaign(plan, _settings(work), _factory(transport), load_label_keys(), real, _sources(real))
    assert code == EXIT_DONE
    state = load_state(work)
    assert state is not None
    return state, plan, transport, build_report(state, plan, resamples=100)


def test_each_document_scored_once_per_mode(modal_run: Any) -> None:
    state, plan, transport, report = modal_run
    assert state.protocol == "1.2" and state.modes == list(spec.MODES)
    # Le service reçoit « mode », jamais « profile » (qui vaut essentiel et contredirait fort) / never "profile".
    assert all("profile" not in names and "mode" in names for names in transport.options_seen)
    assert transport.mode_calls["fort"] == transport.mode_calls["essentiel"]
    # Documents comptés une fois, cellules une fois par mode / documents counted once, cells once per mode.
    assert all(spec.MODE_SEP in key for key in state.cells)
    for mode in spec.MODES:
        assert sum(c.docs for k, c in state.cells.items() if k.startswith(f"{mode}{spec.MODE_SEP}")) == state.docs
    assert report["quality_keys"]["protocol_docs"] == state.docs
    # Empreintes du contenu envoyé : une fois par document, comme le décompte à blanc / dry-run fingerprints.
    from tools.protocol.dryrun import count_plan

    assert count_plan(plan)["synthetic_sha256"] == report["fingerprints"]["synthetic_sha256"]
    assert count_plan(plan)["redteam_sha256"] == report["fingerprints"]["redteam_sha256"]


def test_report_gives_two_numbers_per_mode(modal_run: Any) -> None:
    _state, _plan, _transport, report = modal_run
    assert report["protocol"]["version"] == "1.2"
    assert [p["version"] for p in report["protocol"]["previous_versions"]] == ["1.0", "1.1"]
    assert report["registration"]["earlier_campaigns"] == list(spec.EARLIER_CAMPAIGNS)
    modes = report["modes"]
    assert list(modes) == list(spec.MODES) and modes["fort"]["default"] and not modes["essentiel"]["default"]
    for mode, entry in modes.items():
        a, lost = entry["anonymisation"], entry["useful_codes_lost"]
        assert a["normalised_ci95"][0] <= a["normalised"] <= a["normalised_ci95"][1]
        assert a["hard"] is not None and lost["value"] is not None and lost["decoys"] > 0
        assert set(entry["precision"]) == {f.name for f in spec.FAMILIES}
        assert lost["guard_max"] == (spec.GUARD_MAX_DECOY_MASKED if mode == "essentiel" else None)
    # Le haut du résultat est le mode par défaut (fort) / the top level is the default mode.
    assert report["confidence_index"]["value"] == modes["fort"]["anonymisation"]["normalised"]
    # Garde-fous : lisibilité pour les deux modes, leurres pour essentiel seulement ; fort : perte publiée.
    checks, reported = report["guards"]["checks"], report["guards"]["reported"]
    assert "essentiel/decoys_masked_synthetic" in checks and "fort/decoys_masked_synthetic" not in checks
    assert {"fort/overmask_synthetic", "essentiel/overmask_synthetic", "fort/precision_bodacc_fr",
            "essentiel/precision_boamp_fr"} <= set(checks)
    assert set(reported) == {"fort/decoys_masked_synthetic"}
    assert reported["fort/decoys_masked_synthetic"]["value"] == modes["fort"]["useful_codes_lost"]["value"]
    keys = report["quality_keys"]
    assert keys["modes_source"] == "protocole 1.2" and keys["modes_date"] == report["campaign"]["date"]
    assert keys["fort_index"] == round(100 * modes["fort"]["anonymisation"]["normalised"], 1)
    assert keys["ess_code_loss"] == round(100 * modes["essentiel"]["useful_codes_lost"]["value"], 1)
    assert set(MODE_KEYS) <= set(keys)
    text = to_markdown(report)
    assert "## Deux modes, deux chiffres chacun" in text and "Mode essentiel / Essential mode" in text
    assert "fort/decoys_masked_synthetic" in text and "sans garde-fou" in text


def test_fort_code_loss_never_fails_the_merge(modal_run: Any, tmp_path: Path) -> None:
    """Un mode fort qui masque plus de 10 % des leurres passe le report ; un mode essentiel, non / fort never fails."""
    _state, _plan, _transport, report = modal_run
    result = json.loads(json.dumps(report))
    result["campaign"]["standard_plan"] = True
    result["campaign"]["local_principal"] = True
    result["registration"]["fingerprints_match_registration"] = True
    result["guards"]["checks"] = {k: {**v, "passed": True} for k, v in result["guards"]["checks"].items()}
    result["guards"]["passed"] = True
    result["guards"]["reported"]["fort/decoys_masked_synthetic"]["value"] = 0.17
    result["quality_keys"]["fort_code_loss"] = 17.0
    values = quality_values(result)
    assert values["fort_code_loss"] == 17.0 and values["modes_source"] == "protocole 1.2"
    result["guards"]["checks"]["essentiel/decoys_masked_synthetic"]["passed"] = False
    result["guards"]["passed"] = False
    with pytest.raises(ValueError, match="essentiel/decoys_masked_synthetic"):
        quality_values(result)
    # Un résultat 1.2 sans les chiffres par mode est refusé / a 1.2 result without per-mode figures is refused.
    result["guards"]["checks"]["essentiel/decoys_masked_synthetic"]["passed"] = True
    result["guards"]["passed"] = True
    del result["quality_keys"]["ess_index"]
    with pytest.raises(ValueError, match="mode"):
        quality_values(result)
    # Table du site : clés par mode depuis un résultat 1.2 / site table: per-mode keys from a 1.2 result.
    table = _protocol_table()
    result["quality_keys"]["ess_index"] = report["quality_keys"]["ess_index"]
    values = table.table_values(result)
    assert values["protocol_version"] == "1.2" and values["modes_source"] == "protocole 1.2"
    assert values["fort_code_loss"] == 17.0
    essentiel_decoys = result["guards"]["checks"]["essentiel/decoys_masked_synthetic"]["value"]
    assert values["g_decoys"] == round(100 * essentiel_decoys, 1)
    path = write_report(report, tmp_path)[0]
    assert path.name == f"protocol-1.2-{report['campaign']['date']}.json"


def test_result_1_1_reads_and_reports_as_before() -> None:
    """Le résultat 1.1 publié : même Markdown, mêmes clés du site, même report / the 1.1 result, unchanged."""
    if not RESULT_1_1.exists():
        pytest.skip("résultat 1.1 absent / 1.1 result missing")
    result = json.loads(RESULT_1_1.read_text(encoding="utf-8"))
    assert to_markdown(result) == RESULT_1_1.with_suffix(".md").read_text(encoding="utf-8")
    values = quality_values(result)
    assert values == {k: result["quality_keys"][k] for k in values}
    assert not set(MODE_KEYS) & set(values)
    table = _protocol_table().table_values(result)
    assert table["protocol_version"] == "1.1" and not set(MODE_KEYS) & set(table)
    assert table["g_decoys"] == round(100 * result["guards"]["checks"]["decoys_masked_synthetic"]["value"], 1)
    quality = json.loads((ROOT / "site" / "data" / "quality.json").read_text(encoding="utf-8"))
    if quality.get("protocol_version") == "1.1":
        assert all(quality[k] == v for k, v in table.items() if k in quality)


def test_checkpoint_1_1_still_loads(tmp_path: Path) -> None:
    from tools.protocol.campaign import save_state

    state = State("p", "2026-10-26", {"version": "1.0.1"})
    save_state(state, tmp_path)
    loaded = load_state(tmp_path)
    assert loaded is not None and loaded.protocol == "1.1" and loaded.modes == []
    data = json.loads((tmp_path / "checkpoint.json").read_text(encoding="utf-8"))
    assert data["protocol"] == "1.1" and "modes" not in data
    data["modes"] = ["fort"]  # 1.1 avec des modes : incohérent / 1.1 with modes: inconsistent
    with pytest.raises(SystemExit):
        State.from_json(data)


def test_modes_file_written_as_internal_measure(tmp_path: Path) -> None:
    table = _protocol_table()
    quality = tmp_path / "quality.json"
    quality.write_text(json.dumps({"confidence_index": 96.9, "fort_index": "—"}), encoding="utf-8")
    keys = {"fort_index": 96.2, "fort_ci_low": 95.2, "fort_ci_high": 97.0, "fort_hard_index": 83.9,
            "fort_code_loss": 14.5, "ess_index": "—", "ess_ci_low": "—", "ess_ci_high": "—", "ess_hard_index": "—",
            "ess_code_loss": "—", "modes_source": "mesure interne, moitié dev", "modes_date": "2026-10-26",
            "modes_engine": "1.0.2+src.0123456789ab"}
    measure = tmp_path / "modes.json"
    measure.write_text(json.dumps({"keys": keys}), encoding="utf-8")
    assert table.main(["--modes-file", str(measure), "--quality", str(quality)]) == 0
    written = json.loads(quality.read_text(encoding="utf-8"))
    assert written["fort_index"] == 96.2 and written["ess_index"] == "—" and written["confidence_index"] == 96.9
    assert written["modes_source"] == "mesure interne, moitié dev"
    # Jamais par-dessus un résultat du protocole / never over a protocol result.
    written["modes_source"] = "protocole 1.2"
    quality.write_text(json.dumps(written), encoding="utf-8")
    assert table.main(["--modes-file", str(measure), "--quality", str(quality)]) == 2
    # Une mesure interne ne se fait pas passer pour le protocole / an internal measure never claims the protocol.
    with pytest.raises(ValueError):
        mode_values({**keys, "modes_source": "protocole 1.2"}, "mesure interne, moitié dev")
    with pytest.raises(ValueError):
        mode_values({**keys, "fort_ci_low": 99.0}, "mesure interne, moitié dev")


def test_modes_file_refuses_unreleased_engine_and_can_hold_back_essentiel(tmp_path: Path) -> None:
    table = _protocol_table()
    quality = tmp_path / "quality.json"
    quality.write_text(json.dumps({"confidence_index": 96.9}), encoding="utf-8")
    keys = {"fort_index": 96.2, "fort_ci_low": 95.2, "fort_ci_high": 97.0, "fort_hard_index": 83.9,
            "fort_code_loss": 14.5, "ess_index": 81.6, "ess_ci_low": 80.5, "ess_ci_high": 82.5,
            "ess_hard_index": 48.0, "ess_code_loss": 5.2, "modes_source": "mesure interne, moitié dev",
            "modes_date": "2026-10-26", "modes_engine": "1.0.1+src.7523e373e71e"}
    measure = tmp_path / "modes.json"
    # Moteur antérieur aux modes : sources en chantier, refusé / engine before modes: refused.
    measure.write_text(json.dumps({"keys": keys}), encoding="utf-8")
    assert table.main(["--modes-file", str(measure), "--quality", str(quality)]) == 2
    assert "fort_index" not in json.loads(quality.read_text(encoding="utf-8"))
    # --only-fort : l'essentiel reste « — » / the essentiel keys stay pending.
    measure.write_text(json.dumps({"keys": {**keys, "modes_engine": "1.0.2+src.0123456789ab"}}), encoding="utf-8")
    assert table.main(["--modes-file", str(measure), "--quality", str(quality), "--only-fort"]) == 0
    written = json.loads(quality.read_text(encoding="utf-8"))
    assert written["fort_index"] == 96.2 and written["fort_code_loss"] == 14.5
    assert all(written[k] == "—" for k in ("ess_index", "ess_ci_low", "ess_ci_high", "ess_hard_index", "ess_code_loss"))
    assert written["modes_engine"] == "1.0.2+src.0123456789ab"


def test_modes_dev_scores_like_the_campaign() -> None:
    from tools.protocol import modes_dev

    modes_dev.check_engine_modes(spec.MODES)
    unit = Unit(f"syn:{spec.DEV_SEED}:0", "synthetic", 0, 6, seed=spec.DEV_SEED)
    cells_json, docs = modes_dev._run_unit(unit, spec.MODES, None)
    assert docs == 6
    from tools.protocol.outcomes import Cell

    cells = {k: Cell.from_json(v) for k, v in cells_json.items()}
    assert {k.split(spec.MODE_SEP)[0] for k in cells} == set(spec.MODES)
    figures = {m: modes_dev.mode_figures(cells, m, 20) for m in spec.MODES}
    keys = modes_dev.site_keys(figures, "2026-10-26", "1.0.2+src.0123456789ab")
    assert keys["modes_source"] == "mesure interne, moitié dev" and set(keys) == set(MODE_KEYS)
    assert "decoys_masked_synthetic" in figures["essentiel"]["guards"]
    assert "decoys_masked_synthetic" not in figures["fort"]["guards"]


def test_modes_dev_refuses_an_engine_without_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools.protocol import modes_dev

    import gdprguardian

    def old_engine(**kwargs: Any) -> None:
        if "mode" in kwargs:
            raise TypeError("unexpected keyword argument 'mode'")

    monkeypatch.setattr(gdprguardian, "Anonymizer", old_engine)
    with pytest.raises(SystemExit, match=r"1\.0\.2"):
        modes_dev.check_engine_modes(spec.MODES)
