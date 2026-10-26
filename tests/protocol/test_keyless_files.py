"""Fichiers remis au service public sans clé (lot du protocole) / files moved to the keyless public service.

Le script de la skill Claude marche sans clé et n'envoie une clé que si elle est configurée ; `server.json` déclare
les points MCP publics sans en-tête ; l'image ne porte plus de sonde TCP. The Claude skill script works without a
key and only sends one when configured; `server.json` declares the public MCP endpoints without a header; the image
no longer carries a TCP probe.
"""

from __future__ import annotations

import http.server
import importlib.util
import json
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

import pytest
import uvicorn

from gdprguardian.server import ServerConfig, create_app

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "integrations" / "claude" / "plugin-online" / "skills" / "gdprguardian-online" / "scripts" / \
    "gdprguardian_online.py"
SECRET_KEY = "kilo-key-0123456789-abcdefghijklmnop"


@pytest.fixture(scope="module")
def skill() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gg_skill_keyless", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.fixture
def public_url() -> Iterator[str]:
    """Vrai service en mode public (sans clé), en boucle locale / real public-mode service on loopback."""
    app = create_app(ServerConfig(public=True, isolation=False, page_chars=1000))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_config=None, access_log=False,
                                           lifespan="on"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            pytest.fail("le serveur n'a pas démarré / server did not start")
        time.sleep(0.02)
    yield f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"
    server.should_exit = True
    thread.join(timeout=15)


def test_script_works_without_a_key(skill: ModuleType, public_url: str, tmp_path: Path,
                                    monkeypatch: pytest.MonkeyPatch,
                                    capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    document = tmp_path / "notes_claire_martin.md"
    document.write_text("Rappeler Claire Martin au 06 12 34 56 78 ou claire.martin@exemple.fr.\n", encoding="utf-8")
    monkeypatch.setenv("GDPRGUARDIAN_URL", public_url)
    monkeypatch.delenv("GDPRGUARDIAN_API_KEY", raising=False)
    assert skill.main([str(document), "--countries", "FR"]) == 0
    out = capsysbinary.readouterr().out.decode("utf-8")
    assert "[PERSONNE_1]" in out and "Claire" not in out and "06 12" not in out and "martin" not in out.lower()
    # --report --explain : la règle et la raison de chaque balise, jamais la valeur / rule and reason, never value.
    assert skill.main([str(document), "--countries", "FR", "--report", "--explain"]) == 0
    captured = capsysbinary.readouterr()
    report = json.loads(captured.err.decode("utf-8").strip().splitlines()[-1])
    assert report["explain"] and all("tag" in row and "reason" in row for row in report["explain"])
    err = captured.err.decode("utf-8")
    assert "Claire" not in err and "06 12" not in err and "martin" not in err.lower()


class _Recorder(http.server.BaseHTTPRequestHandler):
    """Enregistre la présence de l'en-tête Authorization, répond 401 / records the Authorization header."""

    seen: ClassVar[list[str | None]] = []

    def do_POST(self) -> None:
        _Recorder.seen.append(self.headers.get("Authorization"))
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        body = b'{"error": {"code": "unauthorized", "message": "x"}}'
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        """Silencieux / quiet."""


def test_key_is_sent_only_when_configured(skill: ModuleType, tmp_path: Path,
                                          capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    document = tmp_path / "x.txt"
    document.write_text("x", encoding="utf-8")
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        _Recorder.seen.clear()
        with pytest.raises(skill.Failure, match="401"):
            skill.anonymize(document, {"GDPRGUARDIAN_URL": url}, countries="FR", profile="standard",
                            label_language="fr", timeout=10)
        with pytest.raises(skill.Failure, match="401") as caught:
            skill.anonymize(document, {"GDPRGUARDIAN_URL": url, "GDPRGUARDIAN_API_KEY": SECRET_KEY},
                            countries="FR", profile="standard", label_language="fr", timeout=10)
    finally:
        server.shutdown()
        server.server_close()
    assert _Recorder.seen == [None, f"Bearer {SECRET_KEY}"]
    assert SECRET_KEY not in str(caught.value)


def test_busy_service_is_retried_after_retry_after(skill: ModuleType) -> None:
    answers = [(429, {"Retry-After": "2"}, b""), (503, {"retry-after": "100"}, b""), (201, {}, b"{}")]
    waits: list[float] = []
    status, _, _ = skill.with_retries(lambda: answers.pop(0), time.monotonic() + 600, sleep=waits.append)
    assert status == 201 and waits == [2.0, 30.0]  # borné à 30 s / capped at 30 s
    # Échéance trop proche : on rend le 429 au lieu d'attendre / deadline too close: the 429 is returned.
    status, _, _ = skill.with_retries(lambda: (429, {"Retry-After": "20"}, b""), time.monotonic() + 1,
                                      sleep=waits.append)
    assert status == 429


def test_missing_url_falls_back_to_the_public_service(skill: ModuleType) -> None:
    # La skill légère vise le service public par défaut ; GDPRGUARDIAN_URL désigne un autre serveur.
    # The light skill targets the public service by default; GDPRGUARDIAN_URL points to another server.
    assert skill.base_url({}) == "https://api.gardienrgpd.fr"


def test_server_json_declares_keyless_remotes() -> None:
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    remotes: list[dict[str, Any]] = server["remotes"]
    assert {r["url"] for r in remotes} == {"https://api.gdprguardian.com/mcp", "https://api.gardienrgpd.fr/mcp"}
    assert all(r["type"] == "streamable-http" and "headers" not in r for r in remotes)
    assert len(server["description"]) <= 100


def test_dockerfile_assumes_no_key_and_no_tcp_probe() -> None:
    lines = (ROOT / "deploy" / "Dockerfile").read_text(encoding="utf-8").splitlines()
    instructions = [line for line in lines if line and not line.startswith("#")]
    assert not any(line.startswith("HEALTHCHECK") for line in instructions)
    usage = [line for line in lines if "docker run" in line and line.startswith("#")]
    assert usage and all("GDPRGUARDIAN_API_KEYS" not in line for line in usage)
