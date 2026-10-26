"""Interface en ligne de commande / command-line interface."""

from __future__ import annotations

import io
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from server_testkit import EMAIL, KEY_A_SHA256, NIR, SENSITIVE_TEXT

import gdprguardian.documents as documents
from gdprguardian import cli
from gdprguardian.server import logs


@pytest.fixture(autouse=True)
def keep_test_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    # `serve` reconfigure le journal racine : sans effet pendant les tests / no root-logger rewiring in tests.
    monkeypatch.setattr(logs, "configure_logging", lambda level="INFO": None)
    # `serve` retire les réglages GDPRGUARDIAN_* : sur une copie, pas sur l'environnement des tests suivants.
    # `serve` scrubs the GDPRGUARDIAN_* settings: on a copy, not on the environment of the following tests.
    monkeypatch.setattr(os, "environ", dict(os.environ))


def run(argv: list[str], capsysbinary: pytest.CaptureFixture[bytes]) -> tuple[int, str, str]:
    code = cli.main(argv)
    out, err = capsysbinary.readouterr()
    return code, out.decode("utf-8"), err.decode("utf-8")


def test_anonymize_stdin(monkeypatch: pytest.MonkeyPatch, capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(("﻿" + SENSITIVE_TEXT).encode("utf-8"))))
    code, out, err = run(["anonymize", "-", "--countries", "FR"], capsysbinary)
    assert code == 0 and err == ""
    assert "[NIR_1]" in out and NIR not in out and EMAIL not in out
    assert out.startswith("Dossier") and out.endswith("\n")


def test_anonymize_stdin_json(monkeypatch: pytest.MonkeyPatch, capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(SENSITIVE_TEXT.encode())))
    code, out, _ = run(["anonymize", "-", "--format", "json", "--label-language", "en"], capsysbinary)
    payload = json.loads(out)
    assert code == 0 and "[EMAIL_1]" in payload["text"] and payload["report"]["irreversible"] is True


def test_anonymize_defaults_to_france(monkeypatch: pytest.MonkeyPatch,
                                      capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    # Pays explicite, FR par défaut, comme l'API et le MCP ; « auto » reste possible et signalé expérimental.
    # Explicit country, FR by default, as in the API and MCP; "auto" stays available and flagged experimental.
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(SENSITIVE_TEXT.encode())))
    code, out, _ = run(["anonymize", "-", "--format", "json"], capsysbinary)
    report = json.loads(out)["report"]
    assert code == 0 and report["country_mode"] == "explicit" and report["countries"] == ["FR"]
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(SENSITIVE_TEXT.encode())))
    code, out, _ = run(["anonymize", "-", "--format", "json", "--countries", "auto"], capsysbinary)
    assert code == 0 and json.loads(out)["report"]["country_mode"] == "auto"
    with pytest.raises(SystemExit):
        cli.main(["anonymize", "--help"])
    assert "(default: FR)" in " ".join(capsysbinary.readouterr().out.decode("utf-8").split())


def test_anonymize_file_to_output(tmp_path: Path, fake_documents: None,
                                  capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    source = tmp_path / "dossier.txt"
    source.write_text(SENSITIVE_TEXT, encoding="utf-8")
    target = tmp_path / "dossier.anon.md"
    code, out, _ = run(["anonymize", str(source), "-o", str(target), "--profile", "strict"], capsysbinary)
    assert code == 0 and out == ""
    markdown = target.read_text(encoding="utf-8")
    assert "document.txt" not in markdown and "[NIR_1]" in markdown and NIR not in markdown


def test_file_name_never_reaches_the_output(tmp_path: Path, fake_documents: None,
                                            capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    source = tmp_path / "CV_Jean_Dupont_1985.txt"
    source.write_text("Bonjour", encoding="utf-8")
    code, out, _ = run(["anonymize", str(source)], capsysbinary)
    assert code == 0 and out.strip() == "Bonjour" and "document" not in out
    assert "Dupont" not in out and "Jean" not in out


def test_unexpected_errors_print_no_traceback_nor_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                         capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    # Un agent IA lit stderr : ni trace ni message tiers / an AI agent reads stderr: no traceback, no message.
    source = tmp_path / "dossier.txt"
    source.write_text(SENSITIVE_TEXT, encoding="utf-8")

    def explode(*_args: object, **_kwargs: object) -> None:
        raise ValueError(f"ligne illisible : {SENSITIVE_TEXT}")

    monkeypatch.setattr(documents, "anonymize_document", explode)
    code, out, err = run(["anonymize", str(source)], capsysbinary)
    assert code == 1 and out == ""
    assert "ValueError" in err and "Traceback" not in err
    assert NIR not in err and "Dupont" not in err


def test_io_errors_hide_the_path(tmp_path: Path, fake_documents: None,
                                 capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    source = tmp_path / "dossier.txt"
    source.write_text("Bonjour", encoding="utf-8")
    target = tmp_path / "absent_jdupont" / "sortie.md"
    code, _, err = run(["anonymize", str(source), "-o", str(target)], capsysbinary)
    assert code == 1 and "I/O error" in err and "jdupont" not in err


def test_anonymize_file_json(tmp_path: Path, fake_documents: None, capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    source = tmp_path / "dossier.txt"
    source.write_text(SENSITIVE_TEXT, encoding="utf-8")
    code, out, _ = run(["anonymize", str(source), "--format", "json"], capsysbinary)
    payload = json.loads(out)
    assert code == 0 and payload["kind"] == "txt" and payload["dropped"] == {"comments": 1}


def test_refuses_to_overwrite_the_original(tmp_path: Path, fake_documents: None,
                                           capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    source = tmp_path / "dossier.txt"
    source.write_text(SENSITIVE_TEXT, encoding="utf-8")
    code, _, err = run(["anonymize", str(source), "-o", str(source)], capsysbinary)
    assert code == 2 and "overwrite" in err
    assert source.read_text(encoding="utf-8") == SENSITIVE_TEXT


def test_errors(tmp_path: Path, fake_documents: None, monkeypatch: pytest.MonkeyPatch,
                capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    code, _, err = run(["anonymize", str(tmp_path / "absent.txt")], capsysbinary)
    assert code == 2 and "not found" in err
    code, _, err = run(["anonymize", "-", "--countries", "ZZ"], capsysbinary)
    assert code == 2 and "unknown country" in err
    scan = tmp_path / "scan.pdf"
    scan.write_bytes(b"%PDF-1.7 " + NIR.encode())
    code, _, err = run(["anonymize", str(scan)], capsysbinary)
    assert code == 1 and "unsupported_format" in err and NIR not in err

    def missing(*_args: object, **_kwargs: object) -> None:
        raise ImportError("No module named 'gdprguardian.convert'")

    monkeypatch.setattr(documents, "anonymize_document", missing)
    code, _, err = run(["anonymize", str(scan)], capsysbinary)
    assert code == 1 and "converter unavailable" in err


def test_packs(capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    code, out, _ = run(["packs"], capsysbinary)
    assert code == 0 and "FR" in out and "INTL" in out
    code, out, _ = run(["packs", "--json"], capsysbinary)
    assert {row["id"] for row in json.loads(out)} >= {"FR", "INTL"}


def test_serve_refuses_dev_mode_on_a_public_interface(monkeypatch: pytest.MonkeyPatch,
                                                      capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    import uvicorn

    monkeypatch.setenv("GDPRGUARDIAN_DEV_NO_AUTH", "1")
    monkeypatch.delenv("GDPRGUARDIAN_API_KEY_SHA256", raising=False)
    monkeypatch.setattr(uvicorn, "run", lambda *_a, **_k: pytest.fail("ne doit pas démarrer / must not start"))
    code, _, err = run(["serve", "--host", "0.0.0.0"], capsysbinary)
    assert code == 2 and "loopback" in err
    code, _, err = run(["mcp", "--http", "--host", "192.168.1.10"], capsysbinary)
    assert code == 2
    # Socket Unix : joint par un proxy ouvert sur l'extérieur, donc jamais sans clé / reached through a proxy.
    # `serve` vient de retirer ses réglages de l'environnement : on les remet / `serve` just scrubbed its settings.
    monkeypatch.setenv("GDPRGUARDIAN_DEV_NO_AUTH", "1")
    code, _, err = run(["serve", "--uds", "/run/gdprguardian/app.sock"], capsysbinary)
    assert code == 2 and "--uds" in err


def test_serve_fails_closed_without_keys(monkeypatch: pytest.MonkeyPatch,
                                         capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.delenv("GDPRGUARDIAN_API_KEY_SHA256", raising=False)
    monkeypatch.delenv("GDPRGUARDIAN_DEV_NO_AUTH", raising=False)
    code, _, err = run(["serve"], capsysbinary)
    assert code == 2 and "fail closed" in err


def test_serve_starts_uvicorn_with_safe_options(monkeypatch: pytest.MonkeyPatch,
                                                capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    import uvicorn

    started: dict[str, object] = {}
    monkeypatch.setenv("GDPRGUARDIAN_API_KEY_SHA256", KEY_A_SHA256)
    monkeypatch.setenv("GDPRGUARDIAN_MAX_CONCURRENCY", "2")
    monkeypatch.delenv("GDPRGUARDIAN_DEV_NO_AUTH", raising=False)
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: started.update(options, app=app))
    code, _, _ = run(["serve", "--port", "9999"], capsysbinary)
    assert code == 0
    assert started["access_log"] is False and started["server_header"] is False and started["port"] == 9999
    assert started["host"] == "127.0.0.1" and started["uds"] is None
    # Réglages lus puis retirés avant le zygote : ni clé ni réglage dans son bloc d'environnement.
    # Settings read then removed before the zygote: neither key nor setting in its environment block.
    assert started["app"].state.service.config.max_concurrency == 2  # type: ignore[attr-defined]
    assert [name for name in os.environ
            if name.startswith("GDPRGUARDIAN_") and name != "GDPRGUARDIAN_PURE_PYTHON"] == []


def test_serve_passes_the_unix_socket_to_uvicorn(monkeypatch: pytest.MonkeyPatch,
                                                 capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    import uvicorn

    started: dict[str, object] = {}
    monkeypatch.setenv("GDPRGUARDIAN_API_KEY_SHA256", KEY_A_SHA256)
    monkeypatch.delenv("GDPRGUARDIAN_DEV_NO_AUTH", raising=False)
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: started.update(options))
    code, _, _ = run(["serve", "--uds", "/run/gdprguardian/app.sock"], capsysbinary)
    assert code == 0 and started["uds"] == "/run/gdprguardian/app.sock"


@pytest.mark.skipif(sys.platform == "win32", reason="socket Unix de uvicorn : Linux et macOS / Linux and macOS only")
def test_serve_answers_on_a_unix_socket(tmp_path: Path) -> None:
    # Déploiement derrière Nginx (deploy/server) : le service n'écoute que sur un socket Unix.
    # Deployment behind Nginx (deploy/server): the service only listens on a Unix socket.
    path, log = tmp_path / "app.sock", tmp_path / "server.log"
    env = dict(os.environ, GDPRGUARDIAN_API_KEY_SHA256=KEY_A_SHA256, GDPRGUARDIAN_MAX_CONCURRENCY="1",
               GDPRGUARDIAN_PREWARM_WORKERS="0")
    code = "import sys; from gdprguardian.cli import main; sys.exit(main(sys.argv[1:]))"
    with log.open("wb") as stderr:
        server = subprocess.Popen([sys.executable, "-c", code, "serve", "--uds", str(path), "--log-level", "warning"],
                                  env=env, stdout=subprocess.DEVNULL, stderr=stderr)
    try:
        deadline = time.monotonic() + 60
        while not path.exists():
            assert server.poll() is None, log.read_text(errors="replace")[-2000:]
            assert time.monotonic() < deadline, "socket absent après 60 s / socket missing after 60 s"
            time.sleep(0.2)
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(10)
            client.connect(str(path))
            client.sendall(b"GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            reply = b""
            while chunk := client.recv(4096):
                reply += chunk
        assert reply.startswith(b"HTTP/1.1 200") and b'"status":"ok"' in reply
    finally:
        server.terminate()
        server.wait(timeout=30)


@pytest.fixture
def started_stdio(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Dossiers passés au serveur stdio, sans le démarrer / directories handed to the stdio server, not started."""
    from gdprguardian.server import mcp_local

    calls: list[list[str]] = []
    monkeypatch.setattr(mcp_local, "run_stdio", lambda dirs: calls.append(list(dirs)))
    monkeypatch.delenv("GDPRGUARDIAN_ALLOWED_DIRS", raising=False)
    return calls


@pytest.mark.parametrize("argv", [["mcp", "--stdio"], ["mcp", "--stdio", "--allow-dir", ""],
                                  ["mcp", "--allow-dir", " ", ""]])
def test_mcp_stdio_refuses_to_start_without_any_directory(argv: list[str], started_stdio: list[list[str]],
                                                         monkeypatch: pytest.MonkeyPatch,
                                                         capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    # Option de plugin sans valeur : Claude Code passe « --allow-dir "" » / unset plugin option: an empty value.
    if len(argv) > 2:
        monkeypatch.setenv("GDPRGUARDIAN_ALLOWED_DIRS", "/ignored/because/the/flag/wins")
    code, out, err = run(argv, capsysbinary)
    assert code == 2 and out == "" and started_stdio == []
    assert "--allow-dir DIR [DIR ...]" in err and "GDPRGUARDIAN_ALLOWED_DIRS" in err


def test_mcp_stdio_messages_reach_the_client_in_utf8() -> None:
    # Un client MCP lit stderr en UTF-8 (journal de Claude Desktop) ; sous Windows, un tube serait en cp1252.
    # An MCP client reads stderr as UTF-8; on Windows a pipe would otherwise be cp1252.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("PYTHONUTF8", "PYTHONIOENCODING", "GDPRGUARDIAN_"))}
    completed = subprocess.run([sys.executable, "-m", "gdprguardian.cli", "mcp", "--stdio", "--allow-dir", ""],
                               capture_output=True, env=env, timeout=120, check=False)
    assert completed.returncode == 2 and completed.stdout == b""
    assert "Aucun dossier autorisé" in completed.stderr.decode("utf-8")


def test_mcp_allow_dir_takes_several_directories_and_wins_over_the_environment(
        tmp_path: Path, started_stdio: list[list[str]], monkeypatch: pytest.MonkeyPatch,
        capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    # Un sélecteur MCPB à choix multiple se développe en « --allow-dir A B » / an MCPB multi-picker expands so.
    a, b, c = (tmp_path / name for name in "abc")
    for folder in (a, b, c):
        folder.mkdir()
    monkeypatch.setenv("GDPRGUARDIAN_ALLOWED_DIRS", str(tmp_path))
    code, _, err = run(["mcp", "--stdio", "--allow-dir", str(a), str(b), "--allow-dir", str(c)], capsysbinary)
    assert code == 0 and err == "" and started_stdio == [[str(a), str(b), str(c)]]
    code, _, _ = run(["mcp", "--stdio"], capsysbinary)
    assert code == 0 and started_stdio[-1] == [str(tmp_path)]


def test_mcp_warns_about_unusable_directories_but_starts(tmp_path: Path, started_stdio: list[list[str]],
                                                         capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    # Dossier pas encore créé : le serveur démarre et le relira à chaque appel / folder not created yet: it starts.
    missing = tmp_path / "GDPRGuardian"
    code, _, err = run(["mcp", "--stdio", "--allow-dir", str(missing)], capsysbinary)
    assert code == 0 and started_stdio == [[str(missing)]]
    assert "no_allowed" not in err and f'"{missing}": introuvable' in err and "no restart needed" in err
    code, _, err = run(["mcp", "--stdio", "--allow-dir", str(tmp_path), "relatif"], capsysbinary)
    assert code == 0 and err.strip() == 'gdprguardian: dossier ignoré / directory ignored: "relatif": chemin ' \
                                       "relatif / relative path"


@pytest.mark.parametrize(("host", "expected"), [
    ("127.0.0.1", True), ("localhost", True), ("::1", True), ("[::1]", True), ("0.0.0.0", False),
    ("10.0.0.1", False), ("example.org", False),
])
def test_is_loopback(host: str, expected: bool) -> None:
    assert cli.is_loopback(host) is expected


def test_version(capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(["--version"])
    assert caught.value.code == 0
    assert "gdprguardian" in capsysbinary.readouterr().out.decode()
