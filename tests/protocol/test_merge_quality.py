"""Report des clés du protocole dans le contrat de qualité du site / merging protocol keys into the site contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tools.protocol.merge_quality import HARD_KEYS, HEADLINE_KEYS, PROTOCOL_KEYS, merge, quality_values

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


def test_protocol_1_1_result_merges_and_recalls_1_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Résultat 1.1 : cinq familles, campagne 1.0 listée, résultat 1.0 rappelé / 1.1 result over the 1.0 one."""
    quality = _quality(tmp_path)
    first = tmp_path / "first.json"
    first.write_text(json.dumps(_results(protocol_engine="1.0.0+0c3ff9fc1fb0")), encoding="utf-8")
    assert merge(first, quality) == 0
    four = ["synthetic_fr", "bodacc_fr", "boamp_fr", "parlamint_fr"]
    v11 = _with_hard(_results(protocol_date="2026-10-27", protocol_engine="1.0.1+0123456789ab", protocol_families=4,
                              protocol={"version": "1.1", "previous_versions": [
                                  {"version": "1.0", "confidence_index": "61.8 % [58.6-66.9]",
                                   "results": "benchmarks/results/protocol-2026-10-26.md"}]},
                              registration={"fingerprints_match_registration": True, "earlier_campaigns": [
                                  {"date": "2026-10-26", "engine": "1.0.0+0c3ff9fc1fb0"}]}))
    v11["confidence_index"] = {"families": four}  # bloc du résultat, pas la clé du site / results block, not the key
    second = tmp_path / "second.json"
    second.write_text(json.dumps(v11), encoding="utf-8")
    assert merge(second, quality) == 0
    assert json.loads(quality.read_text(encoding="utf-8"))["protocol_families"] == 4
    assert "61.8 % [58.6-66.9]" in capsys.readouterr().err
    # Familles publiées à part jamais comptées dans la clé / apart families never counted in the key.
    v11["quality_keys"]["protocol_families"] = 9
    with pytest.raises(ValueError, match="familles"):
        quality_values(v11)


def test_protocol_1_1_refuses_a_site_still_showing_1_0_text(tmp_path: Path,
                                                            capsys: pytest.CaptureFixture[str]) -> None:
    """Indice 1.1 jamais sous le texte 1.0 (« 7 familles ») ; le rappel 1.0 reste permis / never under 1.0 text."""
    (tmp_path / "site" / "data").mkdir(parents=True)
    (tmp_path / "site" / "templates").mkdir()
    quality = _quality(tmp_path / "site" / "data")
    template = tmp_path / "site" / "templates" / "index.fr.html"
    template.write_text("<p>Indice : moyenne des 7 familles</p>\n", encoding="utf-8")
    v11 = _with_hard(_results(protocol_families=4,
                              protocol={"version": "1.1", "previous_versions": [{"version": "1.0"}]}))
    results = tmp_path / "v11.json"
    results.write_text(json.dumps(v11), encoding="utf-8")
    assert merge(results, quality) == 2
    assert "index.fr.html:1" in capsys.readouterr().err
    assert json.loads(quality.read_text(encoding="utf-8"))["protocol_families"] == "—"  # rien écrit / nothing written
    template.write_text("<p>Protocole 1.0 : 61,8 % [58,6–66,9], 7 familles</p>\n<p>4 familles</p>\n", encoding="utf-8")
    assert merge(results, quality) == 0
    template.write_text("<p>moteur 1.0.1, 7 familles</p>\n", encoding="utf-8")  # 1.0.1 n'est pas « 1.0 »
    assert merge(results, quality) == 2
    assert merge(results, quality, site_text_checked=True) == 0


def test_site_contract_has_every_protocol_key() -> None:
    data = json.loads(SITE_QUALITY.read_text(encoding="utf-8"))
    missing = [k for k in HEADLINE_KEYS if k not in data]
    assert not missing, missing
    for key in PROTOCOL_KEYS:
        if key in data:
            value = data[key]
            assert value == "—" or isinstance(value, (int, float, str)), key


def test_site_contract_has_the_difficult_index_keys() -> None:
    """Clés hard_* (1.1) dans site/data/quality.json, « — » tant que non mesurées / hard_* keys in the site file."""
    data = json.loads(SITE_QUALITY.read_text(encoding="utf-8"))
    missing = [k for k in HARD_KEYS if k not in data]
    if missing:
        pytest.xfail(f"site/data/quality.json n'a pas encore / does not have yet: {', '.join(missing)}")


def _with_hard(results: dict[str, Any], **hard: Any) -> dict[str, Any]:
    keys = {"hard_index": 74.04, "hard_ci_low": 73.5, "hard_ci_high": 74.6, "hard_docs": 548_907,
            "hard_mention_recall_pct": 90.03, **hard}
    results["quality_keys"].update(keys)
    return results


def test_difficult_index_keys() -> None:
    """1.1 : les deux indices passent ensemble ; un résultat 1.0 n'a pas d'indice difficile / both indexes in 1.1."""
    v11 = _with_hard(_results(protocol={"version": "1.1"}, protocol_families=4))
    values = quality_values(v11)
    assert (values["hard_index"], values["hard_docs"], values["hard_mention_recall_pct"]) == (74.0, 548_907, 90.0)
    assert values["confidence_index"] == 91.2
    # 1.1 sans indice difficile : refusé / 1.1 without the difficult index: refused.
    with pytest.raises(ValueError, match="hard_index"):
        quality_values(_results(protocol={"version": "1.1"}))
    with pytest.raises(ValueError, match="difficiles"):
        quality_values(_with_hard(_results(protocol={"version": "1.1"}), hard_ci_low=80.0))
    with pytest.raises(ValueError, match="entier"):
        quality_values(_with_hard(_results(protocol={"version": "1.1"}), hard_docs=1.5))
    # Résultat 1.0 (ou sans version) : clés hard_* absentes, non écrites / 1.0 result: hard_* not written.
    assert not set(HARD_KEYS) & set(quality_values(_results(protocol={"version": "1.0"})))


def test_difficult_index_keys_are_merged(tmp_path: Path) -> None:
    quality = _quality(tmp_path)
    results = tmp_path / "protocol.json"
    results.write_text(json.dumps(_with_hard(_results(protocol={"version": "1.1"}))), encoding="utf-8")
    assert merge(results, quality) == 0
    after = json.loads(quality.read_text(encoding="utf-8"))
    assert after["hard_index"] == 74.0 and after["hard_ci_high"] == 74.6 and after["hard_docs"] == 548_907


def test_new_1_1_wording_is_accepted(tmp_path: Path) -> None:
    """Le texte des deux indices passe ; celui du premier jet (cinq familles) est refusé / new wording accepted."""
    (tmp_path / "site" / "data").mkdir(parents=True)
    (tmp_path / "site" / "templates").mkdir()
    quality = _quality(tmp_path / "site" / "data")
    template = tmp_path / "site" / "templates" / "index.en.html"
    v11 = _with_hard(_results(protocol={"version": "1.1", "previous_versions": [{"version": "1.0"}]},
                              protocol_families=4))
    results = tmp_path / "v11.json"
    results.write_text(json.dumps(v11), encoding="utf-8")
    template.write_text(
        "<p>Normalised documents: equal-weight mean of the 4 families, target 95%.</p>\n"
        "<p>Documents normalisés : moyenne à poids égal des 4 familles.</p>\n"
        "<p>Difficult documents: the red team, 51 ways to damage or disguise an identifier, 51 operators.</p>\n"
        "<p>Documents difficiles : 51 façons d'abîmer ou de déguiser un identifiant.</p>\n", encoding="utf-8")
    assert merge(results, quality) == 0
    template.write_text("<dt>Five families</dt>\n", encoding="utf-8")
    assert merge(results, quality) == 2
    template.write_text("<p>FR restricted to 25 everyday formats</p>\n", encoding="utf-8")
    assert merge(results, quality) == 2
