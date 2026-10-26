"""Report des clés du protocole dans le contrat de qualité du site / merging protocol keys into the site contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tools.protocol.merge_quality import PROTOCOL_KEYS, merge, quality_values

SITE_QUALITY = Path(__file__).resolve().parents[2] / "site" / "data" / "quality.json"


def _results(**overrides: Any) -> dict[str, Any]:
    keys = {"confidence_index": 91.234, "confidence_ci_low": 90.1, "confidence_ci_high": 92.4,
            "mention_recall_pct": 97.06, "protocol_docs": 1_012_345, "protocol_families": 7, "real_corpora": 14,
            "real_docs": 8178, "protocol_date": "2026-10-26", "protocol_engine": "1.0.0"}
    results = {"campaign": {"complete": True, "standard_plan": True, "local_principal": True, "errors": {}},
               "registration": {"fingerprints_match_registration": True},
               "guards": {"passed": True, "checks": {}}, "quality_keys": keys}
    for key, value in overrides.items():
        if key in keys:
            keys[key] = value
        else:
            results[key] = value
    return results


def _quality(tmp_path: Path) -> Path:
    path = tmp_path / "quality.json"
    data = {"tests_windows": 1, "recall_direct_pct": 99.2, **dict.fromkeys(PROTOCOL_KEYS, "—"), "measured_on": "x"}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_merge_keeps_other_keys_and_order(tmp_path: Path) -> None:
    quality = _quality(tmp_path)
    before = list(json.loads(quality.read_text(encoding="utf-8")))
    results = tmp_path / "protocol.json"
    results.write_text(json.dumps(_results()), encoding="utf-8")
    assert merge(results, quality) == 0
    after = json.loads(quality.read_text(encoding="utf-8"))
    assert list(after) == before
    assert after["confidence_index"] == 91.2 and after["mention_recall_pct"] == 97.1
    assert after["protocol_docs"] == 1_012_345 and after["protocol_date"] == "2026-10-26"
    assert after["recall_direct_pct"] == 99.2 and after["measured_on"] == "x"


_OK = {"complete": True, "standard_plan": True, "local_principal": True, "errors": {}}


@pytest.mark.parametrize(("override", "reason"), [
    ({"campaign": {"complete": False, "standard_plan": True}}, "incomplète"),
    ({"campaign": {"complete": True, "standard_plan": False}}, "plan réduit"),
    ({"registration": {"fingerprints_match_registration": False}}, "enregistrées"),
    ({"registration": {}}, "enregistrées"),
    ({"campaign": {**_OK, "local_principal": False}}, "jeton local"),
    ({"campaign": {**_OK, "errors": {"http_503": 2, "alignment": 1}}}, "http_503"),
    ({"protocol_engine": "moteur"}, "version"),
    ({"guards": {"passed": False, "checks": {"precision_boamp_fr": {"passed": False}}}}, "precision_boamp_fr"),
    ({"confidence_index": None}, "manquante"),
    ({"confidence_ci_low": 95.0}, "intervalle"),
    ({"protocol_docs": 12.5}, "entier"),
    ({"protocol_date": "26/10/2026"}, "date"),
])
def test_refusals(override: dict[str, Any], reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        quality_values(_results(**override))


def test_forced_guards_and_scaled_flag() -> None:
    failed = _results(guards={"passed": False, "checks": {}})
    assert quality_values(failed, force_guards=True)["confidence_index"] == 91.2
    scaled = _results(campaign={"complete": True, "standard_plan": False})
    assert quality_values(scaled, allow_scaled=True)["protocol_families"] == 7
    # Moteur nommé par sa version et son image / engine named by version and image.
    assert quality_values(_results(protocol_engine="1.0.0+0123456789ab"))["protocol_engine"] == "1.0.0+0123456789ab"


def test_messages_are_utf8_on_every_console(tmp_path: Path) -> None:
    """Refus lisible en UTF-8 même quand la console attend cp1252 / refusal readable in UTF-8 under cp1252."""
    import os
    import subprocess
    import sys

    quality = _quality(tmp_path)
    results = tmp_path / "protocol.json"
    results.write_text(json.dumps(_results(campaign={"complete": False})), encoding="utf-8")
    script = Path(__file__).resolve().parents[2] / "tools" / "protocol" / "merge_quality.py"
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    out = subprocess.run([sys.executable, str(script), str(results), str(quality)], capture_output=True,
                         env=env, timeout=60)
    assert out.returncode == 2
    assert "campagne incomplète" in out.stderr.decode("utf-8")


def test_refused_merge_leaves_the_file_untouched(tmp_path: Path) -> None:
    quality = _quality(tmp_path)
    before = quality.read_bytes()
    results = tmp_path / "protocol.json"
    results.write_text(json.dumps(_results(campaign={"complete": False})), encoding="utf-8")
    assert merge(results, quality) == 2
    assert quality.read_bytes() == before


def test_a_repeat_campaign_must_list_the_published_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Après une campagne publiée, la suivante la liste (moitiés test vues) / a repeat lists the earlier one."""
    quality = _quality(tmp_path)
    first = tmp_path / "first.json"
    first.write_text(json.dumps(_results(protocol_engine="1.0.0+0123456789ab")), encoding="utf-8")
    assert merge(first, quality) == 0
    assert merge(first, quality) == 0  # le même résultat deux fois / the same result twice
    second = tmp_path / "second.json"
    second.write_text(json.dumps(_results(protocol_date="2026-11-20", protocol_engine="1.0.1+fedcba987654")),
                      encoding="utf-8")
    before = quality.read_bytes()
    assert merge(second, quality) == 2
    assert "campagne répétée" in capsys.readouterr().err and quality.read_bytes() == before
    listed = _results(protocol_date="2026-11-20", protocol_engine="1.0.1+fedcba987654",
                      registration={"fingerprints_match_registration": True,
                                    "earlier_campaigns": [{"date": "2026-10-26", "engine": "1.0.0+0123456789ab"}]})
    second.write_text(json.dumps(listed), encoding="utf-8")
    assert merge(second, quality) == 0
    assert json.loads(quality.read_text(encoding="utf-8"))["protocol_date"] == "2026-11-20"


def test_disclosed_departures_are_recalled(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    quality = _quality(tmp_path)
    results = tmp_path / "protocol.json"
    disclosed = {**_OK, "disclosures": [{"code": "allow_swap", "detail": "", "fr": "swap actif", "en": "swap on"}]}
    results.write_text(json.dumps(_results(campaign=disclosed)), encoding="utf-8")
    assert merge(results, quality) == 0
    assert "ÉCART DÉCLARÉ" in capsys.readouterr().err


def test_site_contract_has_every_protocol_key() -> None:
    data = json.loads(SITE_QUALITY.read_text(encoding="utf-8"))
    missing = [k for k in PROTOCOL_KEYS if k not in data]
    assert not missing, missing
    for key in PROTOCOL_KEYS:
        value = data[key]
        assert value == "—" or isinstance(value, (int, float, str)), key
