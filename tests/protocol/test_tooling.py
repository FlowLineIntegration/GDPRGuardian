"""Transport, jeton local, paquet autonome, table des libellés / transport, local token, bundle, label table."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from tools.protocol.cli import load_label_keys
from tools.protocol.transport import Gate, parse_local_header, visitors_active

from gdprguardian.labels import LABELS

TOKEN = "a1" * 32


def test_label_table_matches_the_engine() -> None:
    """Table figée du paquet autonome = libellés du moteur (pack FR et libellés communs) / frozen table drift guard.

    En cas d'échec : `python -m tools.protocol labels` la régénère / on failure, regenerate it.
    """
    table = load_label_keys()
    for display, key in table.items():
        assert display in (LABELS.display(key, "fr", False), LABELS.display(key, "en", False)), display
    # Interpréteur neuf : seuls le pack FR et les libellés communs sont chargés / fresh interpreter, FR pack only.
    root = Path(__file__).resolve().parents[2]
    code = "import json; from tools.protocol.cli import label_table; print(json.dumps(label_table()))"
    out = subprocess.run([sys.executable, "-W", "ignore", "-c", code], capture_output=True, text=True, cwd=root,
                         timeout=300, check=True)
    assert table == json.loads(out.stdout)


def test_local_header_parsing_never_echoes_the_token() -> None:
    assert parse_local_header(f"X-GG-Local: {TOKEN}\n".encode()) == ("X-GG-Local", TOKEN)
    assert parse_local_header(f"x-gg-local:{TOKEN}") == ("X-GG-Local", TOKEN)
    for raw in (f"Authorization: {TOKEN}", f"X-GG-Local: {TOKEN}\nX-GG-Local: {TOKEN}", "X-GG-Local: court", ""):
        with pytest.raises(ValueError) as caught:
            parse_local_header(raw)
        assert TOKEN not in str(caught.value)


def test_visitors_detection() -> None:
    assert not visitors_active({"workers": {"busy": 2, "waiting": 1}}, own_inflight=3)
    assert visitors_active({"workers": {"busy": 3, "waiting": 0}}, own_inflight=2)
    assert visitors_active({"workers": {"busy": 2, "waiting": 2}}, own_inflight=3)
    assert not visitors_active({"workers": {"busy": "x"}}, own_inflight=0)


def test_gate_throttles_to_one() -> None:
    gate = Gate(3)
    gate.set_throttle(True)
    assert gate.limit == 1
    gate.set_throttle(False)
    assert gate.limit == 3 and gate.throttled_s >= 0


def test_bundle_is_self_contained(tmp_path: Path) -> None:
    from tools.protocol.bundle import build_bundle

    path, info = build_bundle(tmp_path / "gg-protocol.pyz")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("BUNDLE.json"))
    assert {"__main__.py", "tools/protocol/cli.py", "tools/protocol/labels.json", "tools/eval/generate.py",
            "tools/corpus/evaluate_real.py", "faker/__init__.py", "faker-LICENSE.txt"} <= names
    assert not any(n.endswith((".jsonl", ".gz", ".pyc")) or "server/" in n for n in names)
    assert manifest["faker"] == info["faker"]
    assert info["spec_sha256"] == manifest["sha256"]["tools/protocol/spec.py"]
    # Reproductible : deux constructions, mêmes octets / reproducible build.
    again, _ = build_bundle(tmp_path / "again.pyz")
    assert again.read_bytes() == path.read_bytes()
    # Lancé seul, isolé (-I), hors du dépôt : le plan s'affiche / runs alone, isolated, outside the repository.
    out = subprocess.run([sys.executable, "-I", str(path), "plan"], capture_output=True, text=True, cwd=tmp_path,
                         timeout=120, check=True)
    plan = json.loads(out.stdout)
    assert plan["base_documents"] == {"synthetic": 450_000, "redteam": 12_000}
    # Le paquet porte le texte du protocole ; ses empreintes = celles du dépôt / the bundle carries the protocol
    # text; its digests equal the repository's.
    from tools.protocol.provenance import provenance

    assert "PROTOCOLE.md" in names
    out = subprocess.run([sys.executable, "-I", str(path), "registration"], capture_output=True, text=True,
                         cwd=tmp_path, timeout=120, check=True)
    registered = json.loads(out.stdout)
    repo = provenance()
    assert registered["source"] == "bundle" and repo["source"] == "repository"
    assert registered["bundle_sha256"] == info["bundle_sha256"]
    for key in ("tools_sha256", "spec_sha256", "protocole_md_sha256", "faker"):
        assert registered[key] == repo[key] == info.get(key, registered[key]), key
    assert registered["registered_plan"]["synthetic_sha256"].startswith("0b91be78")


def test_standard_run_refusals_happen_before_any_request(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """Une campagne standard mal réglée est refusée avant toute requête, avec sa raison (le socket n'existe pas).

    A badly set standard campaign is refused before any request, with its reason (the socket does not exist): no
    service image, test-only flags, non-registered unit sizes, a dev-only pack, a pack missing a corpus.
    """
    from tools.protocol import plan as plan_module
    from tools.protocol import spec
    from tools.protocol.cli import main
    from tools.protocol.plan import write_pack

    socket = str(tmp_path / "absent.sock")
    image = ["--engine-id", "sha256:" + "a" * 64]

    def refused(args: list[str], reason: str) -> None:
        assert main(["run", "--socket", socket, *args]) == 5
        assert reason in capsys.readouterr().err

    refused(["--work", str(tmp_path / "w1")], "--engine-id")
    refused([*image, "--allow-disk-real", "--work", str(tmp_path / "w2")], "--allow-disk-real")
    refused([*image, "--probe-docs", "3", "--work", str(tmp_path / "w3")], "sonde du moteur")
    refused([*image, "--unit-synthetic", "1000", "--work", str(tmp_path / "w4")], "tailles d'unité")
    assert not any((tmp_path / f"w{i}").exists() for i in range(1, 5))  # rien d'écrit / nothing written
    # Paquets en mémoire vive (simulée ici) / packs in RAM storage (simulated here).
    monkeypatch.setattr(plan_module, "check_ram_storage", lambda _path, _allow=False: "tmpfs")
    cache = tmp_path / "cache"
    (cache / "corpora").mkdir(parents=True)
    for name in spec.REAL_CORPORA:
        rows = [json.dumps({"id": f"{name}-{i}", "corpus": name, "lang": "fr", "text": "x", "spans": []})
                for i in range(4)]
        (cache / "corpora" / f"{name}.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    write_pack(cache, tmp_path / "dev.jsonl.gz", split="dev")
    refused([*image, "--real", str(tmp_path / "dev.jsonl.gz"), "--work", str(tmp_path / "w5")], "moitié 'dev'")
    write_pack(cache, tmp_path / "partial.jsonl.gz", ("bodacc_fr", "boamp_fr"))
    refused([*image, "--real", str(tmp_path / "partial.jsonl.gz"), "--work", str(tmp_path / "w6")], "parlamint_fr")
    # Un essai (plan réduit) accepte tout cela / a trial (scaled plan) accepts all this.
    import argparse

    from tools.protocol.cli import _pack_refusal, _standard_refusal
    from tools.protocol.plan import read_pack

    trial = argparse.Namespace(synthetic_seeds=spec.SYNTHETIC_SEEDS, synthetic_docs=10,
                               redteam_seeds=spec.REDTEAM_SEEDS, redteam_bases=spec.REDTEAM_BASES_PER_SEED,
                               unit_synthetic=5, unit_redteam=1, unit_real=1, engine_id=None, allow_disk_real=True,
                               probe_docs=1)
    assert _standard_refusal(trial) is None
    assert _pack_refusal(read_pack(tmp_path / "dev.jsonl.gz")[0], standard=False) is None
    assert _pack_refusal(read_pack(tmp_path / "partial.jsonl.gz")[0], standard=False) is None


def test_server_script_guards() -> None:
    """run-protocol.sh : pas de fichier core, écarts inscrits, campagne incomplète jamais effacée / script guards."""
    script = (Path(__file__).resolve().parents[2] / "tools" / "protocol" / "server" / "run-protocol.sh").read_text(
        encoding="utf-8")
    assert script.count("docker run") == 2 and script.count("--ulimit core=0") == 2
    assert "extra+=(--disclose allow_swap)" in script
    assert 'report --work /work --disclose "redeployed_after:$current"' in script
    incomplete = script[script.index("# Campagne incomplète"):]
    assert incomplete.index("return") < incomplete.index("wipe_ram")
    assert '"$RESULTS/trial-' in script  # essais rangés à part / trials kept apart


def test_unknown_disclosure_is_refused_by_the_parser() -> None:
    from tools.protocol.cli import main

    with pytest.raises(SystemExit) as caught:
        main(["report", "--work", "x", "--disclose", "whatever"])
    assert caught.value.code == 2
    with pytest.raises(SystemExit):
        main(["report", "--work", "x", "--disclose", "allow_swap:with space"])


def test_a_bundle_edited_after_its_build_is_refused(tmp_path: Path) -> None:
    """Empreintes recalculées depuis le contenu, pas lues dans le manifeste / digests recomputed, not trusted."""
    from tools.protocol.bundle import build_bundle
    from tools.protocol.provenance import registration, verify_bundle

    path, info = build_bundle(tmp_path / "gg-protocol.pyz")
    assert verify_bundle(path)["tools_sha256"] == info["tools_sha256"]
    assert registration(path)["bundle"]["matches_repository"] is True
    tampered = tmp_path / "tampered.pyz"
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(tampered, "w", zipfile.ZIP_STORED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "tools/protocol/spec.py":
                data = data.replace(b"GUARD_MIN_PRECISION = 0.70", b"GUARD_MIN_PRECISION = 0.10")
            target.writestr(item, data)
    with pytest.raises(SystemExit, match=r"tools/protocol/spec\.py"):
        verify_bundle(tampered)
    out = subprocess.run([sys.executable, "-I", str(tampered), "registration"], capture_output=True,
                         encoding="utf-8", errors="replace", cwd=tmp_path, timeout=120)
    assert out.returncode != 0 and "altéré" in out.stderr
