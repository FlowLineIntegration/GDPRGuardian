"""Campagne de bout en bout avec un faux service (moteur en processus) / end-to-end campaign with a fake service."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from tools.corpus.real_common import record
from tools.eval.generate import CorpusGenerator
from tools.eval.metrics import significant_mask
from tools.eval.schema import DIRECT
from tools.protocol import spec
from tools.protocol.campaign import EXIT_DONE, EXIT_DOWN, EXIT_REFUSED, Settings, load_state, run_campaign
from tools.protocol.cli import load_label_keys
from tools.protocol.plan import build_plan
from tools.protocol.report import build_report, write_report
from tools.protocol.transport import RetryPolicy, ServiceClient

from gdprguardian import Anonymizer

SYN_SEED, RED_SEED = 2026102581, 2026102591


def _real() -> dict[str, list[dict[str, Any]]]:
    """Petits corpus inventés au format de tools.corpus / small invented corpora in the tools.corpus format."""
    people = ["Jean Martin", "Claire Dubois", "Paul Lefèvre", "Anne Moreau", "Luc Garnier", "Marie Petit"]
    real: dict[str, list[dict[str, Any]]] = {}
    for corpus in ("bodacc_fr", "boamp_fr", "parlamint_fr", "europeana_fr", "mapa_fr", "tab_en"):
        rows = []
        for i, name in enumerate(people):
            text = f"Annonce {i}. Nom : {name}, demeurant 12 rue des Lilas 75011 Paris. Contact : {name}."
            start = text.index(name)
            address = text.index("12 rue")
            second = text.rindex(name)
            rows.append(record(f"{corpus}-{i}", corpus, "fr", text,
                               [(start, start + len(name), "PERSON", "field"),
                                (address, address + len("12 rue des Lilas 75011 Paris"), "ADDRESS", "field"),
                                (second, second + len(name), "PERSON", "repeat")]))
        real[corpus] = rows
    real["judilibre_fr"] = [record("j-0", "judilibre_fr", "fr", "La cour statue, M. [X] présent.", [])]
    return real


def _plan(real: dict[str, list[dict[str, Any]]]) -> Any:
    return build_plan(synthetic_seeds=(SYN_SEED,), synthetic_docs_per_seed=40, redteam_seeds=(RED_SEED,),
                      redteam_bases_per_seed=2, real_counts={k: len(v) for k, v in real.items()},
                      unit_synthetic=10, unit_redteam=1, unit_real=4)


def _settings(work: Path, logs: list[str] | None = None) -> Settings:
    sink = logs.append if logs is not None else (lambda _line: None)
    return Settings(work, threads=2, checkpoint_s=0.0, progress_s=3600, status_s=0.0, tick_s=0.01, log=sink,
                    probe_docs=1)


def _factory(transport: Any) -> Callable[[Any], ServiceClient]:
    def make(gate: Any) -> ServiceClient:
        return ServiceClient(transport, gate, RetryPolicy(down_s=0.0, sleep=lambda _s: None))

    return make


def _sources(real: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    from tools.protocol.plan import corpus_digest

    return {name: corpus_digest(rows) for name, rows in real.items()}


def test_campaign_matches_in_process_truth(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    code = run_campaign(plan, _settings(tmp_path), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real))
    assert code == EXIT_DONE
    state = load_state(tmp_path)
    assert state is not None and len(state.done) == len(plan.units)
    # Vérité en processus pour la famille synthétique / in-process truth for the synthetic family.
    anonymizer = Anonymizer(countries=("FR",), profile="standard")
    passed = scored = 0
    generator = CorpusGenerator(SYN_SEED)
    for index in range(40):
        doc = generator.document(index)
        result = anonymizer.anonymize(doc.text)
        mask = bytearray(len(doc.text))
        for span in result.analysis.spans:
            if span.personal:
                mask[span.start:span.end] = b"\x01" * (span.end - span.start)
        sig = significant_mask(doc.text)
        direct = [s for s in doc.spans if s.identifier_type == DIRECT and sig[s.start:s.end].count(1)]
        if not direct:
            continue
        scored += 1
        passed += all(all(mask[i] for i in range(s.start, s.end) if sig[i]) for s in direct)
    report = build_report(state, plan, resamples=200)
    synthetic = report["families"]["synthetic_fr"]["headline"]
    assert (synthetic["scored"], synthetic["passed"]) == (scored, passed)
    assert report["campaign"]["complete"]
    assert report["confidence_index"]["value"] is not None
    low, high = report["confidence_index"]["ci95"]
    assert low <= report["confidence_index"]["value"] <= high
    assert report["quality_keys"]["protocol_docs"] == state.docs
    assert report["quality_keys"]["real_docs"] == sum(len(v) for k, v in real.items() if k != "judilibre_fr")
    assert report["negative_control"]["judilibre_fr"]["docs"] == 1
    assert "nbsp" in report["redteam_operators"]
    # Hors périmètre publié à part, jamais mêlé au périmètre français / out of scope published apart.
    assert "tab_en" in report["out_of_scope"] and "tab_en" not in report["corpora"]
    assert "bodacc_fr" in report["corpora"] and "bodacc_fr" not in report["out_of_scope"]
    from tools.protocol.report import to_markdown

    text = to_markdown(report)
    assert "## Autres langues, hors périmètre" in text
    assert text.index("| tab_en |") > text.index("## Autres langues, hors périmètre") > text.index("| bodacc_fr |")
    # Ce que les moitiés test ont déjà vu, recopié dans chaque résultat / test-half history in every result.
    # Plan 1.1 (sans modes) : l'historique qu'il avait, rien de ce que la 1.2 ajoute / a 1.1 plan keeps its history.
    registration = report["registration"]
    before_1_1 = [e for e in spec.TEST_HALVES_MEASURED_BEFORE if "added_by" not in e]
    assert registration["test_halves_measured_before"] == before_1_1 and len(before_1_1) >= 7
    earlier_1_1 = [e for e in spec.EARLIER_CAMPAIGNS if e["protocol"] == "1.0"]
    assert registration["earlier_campaigns"] == earlier_1_1
    assert report["protocol"]["version"] == "1.1" and "modes" not in report
    assert [p["version"] for p in report["protocol"]["previous_versions"]] == ["1.0"]
    earlier = ", ".join(f"{e['date']} ({e['engine']})" for e in earlier_1_1) or "aucune / none"
    assert f"campagnes antérieures / earlier campaigns : {earlier}." in text
    # 1.1 : indice « documents normalisés » sur quatre familles, indice « documents difficiles » sur l'équipe rouge,
    # le reste à part / normalised index on four families, difficult index on the red team, the rest apart.
    assert report["confidence_index"]["families"] == [f.name for f in spec.FAMILIES]
    assert report["confidence_index"]["index"] == "normalised" and report["confidence_index"]["target"] == 0.95
    assert set(report["families_apart"]) == {f.name for f in spec.HARD_FAMILIES + spec.APART_FAMILIES}
    assert {k for k, v in report["families_apart"].items() if v["index"] == "hard"} == {
        f.name for f in spec.HARD_FAMILIES}
    assert report["quality_keys"]["protocol_families"] == len(spec.FAMILIES) == 4
    hard = report["hard_index"]
    operators = report["redteam_operators"]
    scored = sum(report["families_apart"][f.name]["headline"]["scored"] for f in spec.HARD_FAMILIES)
    passed = sum(report["families_apart"][f.name]["headline"]["passed"] for f in spec.HARD_FAMILIES)
    assert hard["docs"] == scored == report["quality_keys"]["hard_docs"] > 0
    assert hard["value"] == passed / scored  # chaque document muté compte une fois / every mutated doc counts once
    assert hard["ci95"][0] <= hard["value"] <= hard["ci95"][1]
    assert hard["operators"] == 51 and set(operators) <= {op for f in spec.HARD_FAMILIES for op in f.operators}
    assert abs(sum(g["weight"] for g in hard["groups"].values()) - 1) < 1e-9
    keys = report["quality_keys"]
    assert keys["hard_ci_low"] <= keys["hard_index"] <= keys["hard_ci_high"]
    assert keys["hard_mention_recall_pct"] is not None
    assert text.index("## Documents difficiles") > text.index("## Indice de confiance, documents normalisés")
    assert "europeana_fr" in report["corpora_french_apart"] and "mapa_fr" in report["corpora_french_apart"]
    assert "europeana_fr" not in report["corpora"] and "mapa_fr" not in report["corpora"]
    assert report["redteam_operators"]["nbsp"]["group"] == "everyday"
    assert text.index("## Publiés à part") > text.index("| bodacc_fr |")
    assert text.index("| europeana_fr |") > text.index("## Publiés à part")
    # La famille redteam_fr = ses seuls opérateurs du quotidien / redteam_fr = everyday operators only.
    everyday = sum(row["docs"] for row in report["redteam_operators"].values() if row["group"] == "everyday")
    assert report["families_apart"]["redteam_fr"]["headline"]["docs"] == everyday
    assert "redteam_fr" not in report["families"]
    obfuscation = sum(row["docs"] for row in report["redteam_operators"].values() if row["group"] == "obfuscation")
    assert report["families_apart"]["redteam_obfuscation_fr"]["headline"]["docs"] == obfuscation


def test_resume_gives_the_same_aggregates(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    whole = tmp_path / "whole"
    assert run_campaign(plan, _settings(whole), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    cut = tmp_path / "cut"
    # Panne du service après 60 documents : pause (code 3), puis reprise / service down after 60 documents.
    code = run_campaign(plan, _settings(cut), _factory(engine_transport(fail_after=60, delay=0.004)),
                        load_label_keys(), real, _sources(real))
    assert code == EXIT_DOWN
    partial = load_state(cut)
    assert partial is not None and 0 < len(partial.done) < len(plan.units)
    assert run_campaign(plan, _settings(cut), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    a, b = load_state(whole), load_state(cut)
    assert a is not None and b is not None
    _assert_same_aggregates(a, b)


def _canonical(cell: Any) -> dict[str, Any]:
    data = cell.to_json()
    data["vectors"] = sorted(data["vectors"])  # ordre d'arrivée des unités / unit completion order
    return data


def _assert_same_aggregates(a: Any, b: Any) -> None:
    assert {k: _canonical(c) for k, c in a.cells.items()} == {k: _canonical(c) for k, c in b.cells.items()}
    assert {u: (d["bits"], d["digest"]) for u, d in a.done.items()} == {u: (d["bits"], d["digest"])
                                                                         for u, d in b.done.items()}


def test_engine_change_refuses_to_resume(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    assert run_campaign(plan, _settings(tmp_path), _factory(engine_transport(fail_after=5)), load_label_keys(),
                        real, _sources(real)) == EXIT_DOWN
    other = engine_transport(packs=[{"id": "FR", "version": "autre"}])
    assert run_campaign(plan, _settings(tmp_path), _factory(other), load_label_keys(), real,
                        _sources(real)) == EXIT_REFUSED


def test_no_document_text_is_ever_written(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    run_campaign(plan, _settings(tmp_path), _factory(engine_transport()), load_label_keys(), real, _sources(real))
    state = load_state(tmp_path)
    assert state is not None
    write_report(build_report(state, plan, resamples=50), tmp_path / "results")
    written = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.rglob("*") if p.is_file())
    values = {g["text"] for rows in real.values() for rec in rows for g in rec["spans"]}
    generator = CorpusGenerator(SYN_SEED)
    for index in range(40):
        doc = generator.document(index)
        values.update(doc.text[s.start:s.end] for s in doc.spans if s.end - s.start >= 6)
    leaked = sorted(v for v in values if len(v) >= 6 and re.search(rf"(?<!\w){re.escape(v)}(?!\w)", written))
    assert not leaked, f"{len(leaked)} valeurs écrites / values written"
    for rows in real.values():
        for rec in rows:
            assert rec["text"][:30] not in written


def test_campaign_yields_to_waiting_visitors(tmp_path: Path, engine_transport: Any) -> None:
    """Des visiteurs attendent une place : la campagne passe à une requête en vol / visitors waiting: one in flight."""
    real = {"judilibre_fr": _real()["judilibre_fr"]}
    plan = build_plan(synthetic_seeds=(SYN_SEED,), synthetic_docs_per_seed=60, redteam_seeds=(), real_counts={},
                      unit_synthetic=10)
    settings = _settings(tmp_path)
    settings.status_s = 0.01
    code = run_campaign(plan, settings, _factory(engine_transport(visitors=3, delay=0.002)), load_label_keys(), real,
                        _sources(real))
    state = load_state(tmp_path)
    assert code == EXIT_DONE and state is not None and state.throttled_s > 0


def test_429_backs_off_then_succeeds(engine_transport: Any) -> None:
    waits: list[float] = []
    client = ServiceClient(engine_transport(statuses=[429, 503, 200]), None,
                           RetryPolicy(sleep=waits.append))
    out = client.anonymize("Contact : Jean Martin.", {"countries": "FR", "profile": "standard"})
    assert "Jean Martin" not in out
    assert len(waits) == 2 and all(0.5 <= w <= 0.6 for w in waits)
    assert client.retries == {"http_429": 1, "http_503": 1}


def test_refusal_is_a_failure_not_a_crash(tmp_path: Path, engine_transport: Any) -> None:
    from tools.protocol.campaign import Worker

    worker = Worker(ServiceClient(engine_transport(statuses=[422]), None, RetryPolicy(sleep=lambda _s: None)),
                    load_label_keys(), _real(), __import__("threading").Event())
    unit = build_plan(synthetic_seeds=(SYN_SEED,), synthetic_docs_per_seed=1, redteam_seeds=(), real_counts={},
                      unit_synthetic=1).units[0]
    result = worker.run(unit)
    cell = result.cells[f"synthetic_fr/seed={SYN_SEED}"]
    assert cell.errors == {"http_422": 1} and cell.passed == 0 and result.bits == [1]


def test_plan_is_deterministic_and_excludes_the_dev_seed() -> None:
    a = build_plan(real_counts={"bodacc_fr": 250})
    b = build_plan(real_counts={"bodacc_fr": 250})
    assert a.plan_id == b.plan_id and a.units == b.units
    assert a.units[0].kind == "real" and a.units[2].uid == "real:bodacc_fr:200"
    assert sum(u.count for u in a.units if u.kind == "synthetic") == 450_000
    assert sum(u.count for u in a.units if u.kind == "redteam") == 12_000
    with pytest.raises(ValueError):
        build_plan(synthetic_seeds=(spec.DEV_SEED,))


def test_pack_round_trip_and_refusals(tmp_path: Path) -> None:
    from tools.protocol.plan import RAM_FILESYSTEMS, check_ram_storage, filesystem_type, read_pack, write_pack

    cache = tmp_path / "cache"
    (cache / "corpora").mkdir(parents=True)
    rows = _real()["bodacc_fr"]
    (cache / "corpora" / "bodacc_fr.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                                                        encoding="utf-8")
    pack = tmp_path / "pack.jsonl.gz"
    header = write_pack(cache, pack, ("bodacc_fr",))
    assert header["corpora"]["bodacc_fr"]["docs"] == len(rows)
    _, corpora = read_pack(pack)
    assert corpora["bodacc_fr"] == rows
    with pytest.raises(SystemExit):
        write_pack(cache, Path(__file__).resolve().parents[2] / "pack.jsonl.gz", ("bodacc_fr",))
    # Disque ordinaire : refusé, sauf drapeau d'essai / ordinary disk refused unless the test flag.
    if filesystem_type(pack) not in RAM_FILESYSTEMS:
        with pytest.raises(SystemExit):
            check_ram_storage(pack)
        assert "tests only" in check_ram_storage(pack, allow_disk=True)
    # Paquet altéré : refusé / corrupted pack refused.
    import gzip

    lines = gzip.decompress(pack.read_bytes()).decode("utf-8").splitlines()
    lines[1] = lines[1].replace("Jean Martin", "Jean Martine", 1)
    pack.write_bytes(gzip.compress(("\n".join(lines) + "\n").encode("utf-8")))
    with pytest.raises(SystemExit):
        read_pack(pack)
    # Moitié dev seulement (essais) : aucune pièce de la moitié test / dev half only (trials): no test document.
    from tools.corpus.real_common import split_of

    dev = write_pack(cache, tmp_path / "dev.jsonl.gz", ("bodacc_fr",), split="dev")
    header, corpora = read_pack(tmp_path / "dev.jsonl.gz")
    assert dev["split"] == header["split"] == "dev"
    assert corpora.get("bodacc_fr", []) == [r for r in rows if split_of(r["id"]) == "dev"]


# --- Une campagne = un moteur / one campaign = one engine ------------------------------------------------------------


def test_engine_change_mid_run_writes_nothing_after_the_last_check(tmp_path: Path, engine_transport: Any) -> None:
    """Le moteur cesse de masquer en pleine campagne : refus, et rien d'écrit qu'il aurait noté.

    The engine stops masking mid-run: refused, and nothing it scored is written. Reprise avec le moteur d'origine :
    mêmes agrégats qu'une campagne sans incident / resuming on the original engine: same aggregates as a clean run.
    """
    real = _real()
    plan = _plan(real)
    whole = tmp_path / "whole"
    assert run_campaign(plan, _settings(whole), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    cut = tmp_path / "cut"
    logs: list[str] = []
    code = run_campaign(plan, _settings(cut, logs), _factory(engine_transport(switch_after=80, delay=0.004)),
                        load_label_keys(), real, _sources(real))
    assert code == EXIT_REFUSED
    assert any("probe_sha256" in line for line in logs)
    saved = load_state(cut)
    assert saved is not None and len(saved.done) < len(plan.units)
    # Le moteur changé ne reprend pas / the changed engine cannot resume.
    assert run_campaign(plan, _settings(cut), _factory(engine_transport(switch_after=0)), load_label_keys(), real,
                        _sources(real)) == EXIT_REFUSED
    assert run_campaign(plan, _settings(cut), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    a, b = load_state(whole), load_state(cut)
    assert a is not None and b is not None
    _assert_same_aggregates(a, b)


def test_restart_is_detected_and_the_engine_checked_again(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    whole = tmp_path / "whole"
    assert run_campaign(plan, _settings(whole), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    restarted = tmp_path / "restarted"
    transport = engine_transport(counters=True, restart_after=70, delay=0.004)
    assert run_campaign(plan, _settings(restarted), _factory(transport), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    a, b = load_state(whole), load_state(restarted)
    assert a is not None and b is not None
    assert b.retries.get("engine_recheck:restart", 0) >= 1
    _assert_same_aggregates(a, b)


def test_image_id_is_part_of_the_engine(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    image = "sha256:" + "0123456789ab" + "c" * 52
    settings = _settings(tmp_path)
    settings.engine_id = image
    assert run_campaign(plan, settings, _factory(engine_transport(fail_after=5)), load_label_keys(), real,
                        _sources(real)) == EXIT_DOWN
    settings.engine_id = "sha256:" + "f" * 64
    assert run_campaign(plan, settings, _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_REFUSED
    settings.engine_id = image
    assert run_campaign(plan, settings, _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    state = load_state(tmp_path)
    assert state is not None
    report = build_report(state, plan, resamples=20)
    assert report["quality_keys"]["protocol_engine"] == "1.0.0+0123456789ab"
    assert report["campaign"]["engine_checks"] >= 3
    from tools.protocol.cli import main as cli_main

    assert cli_main(["verify-engine", "--work", str(tmp_path), "--engine-id", image]) == 0
    assert cli_main(["verify-engine", "--work", str(tmp_path), "--engine-id", "sha256:" + "f" * 64]) == EXIT_REFUSED


def test_completed_campaign_is_never_run_again(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    assert run_campaign(plan, _settings(tmp_path), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    before = (tmp_path / "checkpoint.json").read_bytes()
    assert run_campaign(plan, _settings(tmp_path), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_REFUSED
    assert (tmp_path / "checkpoint.json").read_bytes() == before


def test_local_token_is_required_for_a_standard_campaign(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    settings = _settings(tmp_path / "required")
    settings.require_local = True
    assert run_campaign(plan, settings, _factory(engine_transport(deep=404)), load_label_keys(), real,
                        _sources(real)) == EXIT_REFUSED
    # Essai : accepté mais signalé partout / trial: accepted but flagged everywhere.
    trial = tmp_path / "trial"
    assert run_campaign(plan, _settings(trial), _factory(engine_transport(deep=404)), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    state = load_state(trial)
    assert state is not None
    report = build_report(state, plan, resamples=20)
    assert report["campaign"]["local_principal"] is False
    from tools.protocol.report import to_markdown

    text = to_markdown(report)
    assert "PLAN RÉDUIT" in text and "Jeton local absent" in text and state.plan_id in text


def test_document_exception_is_a_leak_and_a_unit_crash_is_loud(tmp_path: Path, engine_transport: Any,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    import threading

    from tools.protocol import campaign

    real_score = campaign.score_synthetic
    seen = {"n": 0}

    def flaky(*args: Any, **kwargs: Any) -> Any:
        seen["n"] += 1
        if seen["n"] == 1:
            raise ZeroDivisionError("scoring bug")
        return real_score(*args, **kwargs)

    monkeypatch.setattr(campaign, "score_synthetic", flaky)
    worker = campaign.Worker(ServiceClient(engine_transport(), None, RetryPolicy(sleep=lambda _s: None)),
                             load_label_keys(), {}, threading.Event())
    unit = build_plan(synthetic_seeds=(SYN_SEED,), synthetic_docs_per_seed=3, redteam_seeds=(), real_counts={},
                      unit_synthetic=3).units[0]
    result = worker.run(unit)
    cell = result.cells[f"synthetic_fr/seed={SYN_SEED}"]
    assert cell.errors == {"exception:ZeroDivisionError": 1} and cell.docs == 3 and len(result.bits) == 3
    assert result.bits[0] == 1
    monkeypatch.undo()

    def broken(*_args: Any, **_kwargs: Any) -> Any:
        raise KeyError("generator bug")

    monkeypatch.setattr(campaign, "synthetic_documents", broken)
    logs: list[str] = []
    plan = build_plan(synthetic_seeds=(SYN_SEED,), synthetic_docs_per_seed=20, redteam_seeds=(), real_counts={},
                      unit_synthetic=10)
    code = run_campaign(plan, _settings(tmp_path, logs), _factory(engine_transport()), load_label_keys(), {}, {})
    assert code == EXIT_REFUSED and any("KeyError" in line and "syn:" in line for line in logs)


def test_checkpoint_falls_back_to_the_previous_copy(tmp_path: Path) -> None:
    from tools.protocol.campaign import CHECKPOINT, State, save_state

    state = State("plan", "2026-10-25", {"version": "1.0.0"})
    save_state(state, tmp_path)
    state.engine_checks = 7
    save_state(state, tmp_path)
    assert (tmp_path / (CHECKPOINT + ".prev")).exists() and (tmp_path / CHECKPOINT).exists()
    (tmp_path / CHECKPOINT).write_text("{tronqué", encoding="utf-8")
    loaded = load_state(tmp_path)
    assert loaded is not None and loaded.engine_checks == 0  # la copie précédente / the previous copy
    (tmp_path / CHECKPOINT).unlink()
    loaded = load_state(tmp_path)
    assert loaded is not None and loaded.plan_id == "plan"
    (tmp_path / (CHECKPOINT + ".prev")).write_text("", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_state(tmp_path)


def test_lasting_overload_pauses_instead_of_counting_leaks(tmp_path: Path, engine_transport: Any) -> None:
    from tools.protocol.transport import ServiceSaturated

    client = ServiceClient(engine_transport(statuses=[503] * 10), None,
                           RetryPolicy(max_doc_wait_s=2.0, sleep=lambda _s: None))
    with pytest.raises(ServiceSaturated):
        client.anonymize("Contact : Jean Martin.", {"countries": "FR"})
    plan = build_plan(synthetic_seeds=(SYN_SEED,), synthetic_docs_per_seed=20, redteam_seeds=(), real_counts={},
                      unit_synthetic=10)

    shared = engine_transport(statuses=[200] * 4 + [503] * 400)

    def make(gate: Any) -> ServiceClient:
        return ServiceClient(shared, gate, RetryPolicy(max_doc_wait_s=2.0, down_s=0.0, sleep=lambda _s: None))

    assert run_campaign(plan, _settings(tmp_path), make, load_label_keys(), {}, {}) == EXIT_DOWN
    state = load_state(tmp_path)
    assert state is not None
    assert not any(k.startswith("http_") for cell in state.cells.values() for k in cell.errors)


def test_real_pack_is_wiped_once_the_real_units_are_saved(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    pack = tmp_path / "pack.jsonl.gz"
    pack.write_bytes(b"x")
    settings = _settings(tmp_path / "work")
    settings.wipe_real = pack
    assert run_campaign(plan, settings, _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    state = load_state(tmp_path / "work")
    assert not pack.exists() and state is not None and state.real_wiped and real == {}


def test_wiped_flag_is_saved_by_the_very_save_that_wipes(tmp_path: Path, engine_transport: Any) -> None:
    """Corpus réels seuls : le dernier enregistrement efface le paquet, et le point de reprise doit le dire.

    Real corpora only: the last save wipes the pack, and the checkpoint on disk must say so (a kill -9 right after a
    wipe, or the end of the campaign, used to leave `real_wiped: false`).
    """
    real = _real()
    plan = build_plan(synthetic_seeds=(), redteam_seeds=(), real_counts={k: len(v) for k, v in real.items()},
                      unit_real=4)
    pack = tmp_path / "pack.jsonl.gz"
    pack.write_bytes(b"x")
    settings = _settings(tmp_path / "work")
    settings.checkpoint_s = 3600.0   # un seul enregistrement, celui de la fin / one save only, at the end
    settings.wipe_real = pack
    assert run_campaign(plan, settings, _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    state = load_state(tmp_path / "work")
    assert not pack.exists() and state is not None and state.real_wiped
    assert build_report(state, plan, resamples=20)["campaign"]["real_pack_wiped"] is True


def test_disclosures_are_kept_in_the_checkpoint_and_the_results(tmp_path: Path, engine_transport: Any) -> None:
    from tools.protocol.cli import main as cli_main
    from tools.protocol.report import to_markdown

    real = _real()
    plan = _plan(real)
    settings = _settings(tmp_path)
    settings.disclosures = ("allow_swap",)
    assert run_campaign(plan, settings, _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    params = {"plan_id": plan.plan_id, "standard": False, "real_counts": {k: len(v) for k, v in real.items()},
              "synthetic_seeds": [SYN_SEED], "synthetic_docs": 40, "redteam_seeds": [RED_SEED], "redteam_bases": 2,
              "units": [10, 1, 4]}
    (tmp_path / "plan.json").write_text(json.dumps(params), encoding="utf-8")
    image = "sha256:" + "b" * 64
    assert cli_main(["report", "--work", str(tmp_path), "--out", str(tmp_path / "results"),
                     "--disclose", f"redeployed_after:{image}"]) == 0
    state = load_state(tmp_path)
    assert state is not None and state.disclosures == ["allow_swap", f"redeployed_after:{image}"]
    results = json.loads(next((tmp_path / "results").glob("protocol-*.json")).read_text(encoding="utf-8"))
    codes = [(d["code"], d["detail"]) for d in results["campaign"]["disclosures"]]
    assert codes == [("allow_swap", ""), ("redeployed_after", image)]
    text = to_markdown(results)
    assert "Écarts déclarés" in text and "GG_PROTOCOL_ALLOW_SWAP=1" in text and image in text
    # Même écart deux fois : une seule fois / same departure twice: kept once.
    state.disclose(("allow_swap",))
    assert state.disclosures.count("allow_swap") == 1
    with pytest.raises(ValueError):
        state.disclose(("inconnu",))


def test_tool_change_refuses_to_resume(tmp_path: Path, engine_transport: Any) -> None:
    real = _real()
    plan = _plan(real)
    settings = _settings(tmp_path)
    settings.tool = {"tools_sha256": "a", "spec_sha256": "b", "protocole_md_sha256": "c", "faker": "40.43.0"}
    assert run_campaign(plan, settings, _factory(engine_transport(fail_after=5)), load_label_keys(), real,
                        _sources(real)) == EXIT_DOWN
    settings.tool = {**settings.tool, "spec_sha256": "changed"}
    assert run_campaign(plan, settings, _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_REFUSED


def test_registration_is_checked_in_the_report(tmp_path: Path, engine_transport: Any) -> None:
    from tools.protocol.provenance import plan_matches_registration

    registered = dict(spec.REGISTERED_PLAN)
    assert plan_matches_registration(registered)
    assert not plan_matches_registration({**registered, "redteam_sha256": "0" * 64})
    assert not plan_matches_registration({**registered, "faker": "41.0.0"})
    real = _real()
    plan = _plan(real)
    assert run_campaign(plan, _settings(tmp_path), _factory(engine_transport()), load_label_keys(), real,
                        _sources(real)) == EXIT_DONE
    state = load_state(tmp_path)
    assert state is not None
    scaled = build_report(state, plan, resamples=20)
    assert scaled["registration"]["fingerprints_match_registration"] is None
    assert scaled["registration"]["observed"]["documents"]["synthetic_fr"] == 40
    standard = build_report(state, plan, standard=True, resamples=20)
    assert standard["registration"]["fingerprints_match_registration"] is False
