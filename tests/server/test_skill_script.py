"""Script de la skill légère gdprguardian-online, de bout en bout sur un vrai serveur local.

Light skill gdprguardian-online script, end to end against a real local server.
"""

from __future__ import annotations

import http.server
import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import ClassVar

import pytest
import uvicorn
from server_testkit import EMAIL, IBAN, INTEGRATIONS, KEY_A, NIR, SENSITIVE_TEXT, load_script

from gdprguardian.server import ServerConfig, create_app

SCRIPT = INTEGRATIONS / "plugin-online" / "skills" / "gdprguardian-online" / "scripts" / "gdprguardian_online.py"


@pytest.fixture(scope="module")
def skill() -> ModuleType:
    return load_script(SCRIPT, "gdprguardian_online_skill_script")


def _serve(app: object) -> Iterator[str]:
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_config=None, access_log=False,
                                           lifespan="on"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            pytest.fail("le serveur n'a pas démarré / server did not start")
        time.sleep(0.02)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=15)


@pytest.fixture
def server_url(fake_documents: None) -> Iterator[str]:
    """Serveur uvicorn réel à clés sur 127.0.0.1 / real keyed uvicorn server on loopback."""
    yield from _serve(create_app(ServerConfig(api_keys=(KEY_A,), page_chars=1000, isolation=False)))


@pytest.fixture
def public_url(fake_documents: None) -> Iterator[str]:
    """Serveur en mode public, sans clé / public-mode server, no key."""
    yield from _serve(create_app(ServerConfig(public=True, isolation=False)))


@pytest.fixture
def document(tmp_path: Path) -> Path:
    path = tmp_path / "dossier_jean_dupont.txt"
    path.write_text(SENSITIVE_TEXT + "".join(f"Ligne {i} : {i}@exemple.fr\n" for i in range(100)), encoding="utf-8")
    return path


def test_prints_only_the_anonymised_markdown(skill: ModuleType, server_url: str, document: Path,
                                             monkeypatch: pytest.MonkeyPatch,
                                             capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setenv("GDPRGUARDIAN_URL", server_url + "/")
    monkeypatch.setenv("GDPRGUARDIAN_API_KEY", KEY_A)
    monkeypatch.setattr(skill, "PAGE_CHARS", 1000)  # plusieurs pages / several pages
    assert skill.main([str(document), "--countries", "FR", "--report"]) == 0
    out, err = (stream.decode("utf-8") for stream in capsysbinary.readouterr())
    # Ni titre ni nom de fichier : le Markdown commence par le contenu / no title, no file name: content first.
    assert out.startswith("Dossier de M. [PERSONNE_1]") and "dupont" not in out.lower()
    assert out.count("\n") == 101  # toutes les pages, sans perte / every page, nothing lost
    for secret in (NIR, EMAIL, IBAN, "@exemple.fr", KEY_A):
        assert secret not in out and secret not in err
    assert '"total_replaced"' in err


def test_works_without_a_key_against_the_public_mode(skill: ModuleType, public_url: str, document: Path,
                                                     monkeypatch: pytest.MonkeyPatch,
                                                     capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setenv("GDPRGUARDIAN_URL", public_url)
    monkeypatch.delenv("GDPRGUARDIAN_API_KEY", raising=False)
    assert skill.main([str(document), "--explain"]) == 0
    out, err = (stream.decode("utf-8") for stream in capsysbinary.readouterr())
    assert "[NIR_1]" in out and NIR not in out
    # --explain : la règle et la raison de chaque balise, jamais la valeur / rule and reason, never the value.
    report = json.loads(err.strip().splitlines()[-1])
    assert report["explain"] and all("tag" in row and "reason" in row for row in report["explain"])
    assert NIR not in err and EMAIL not in err


def test_text_mode(skill: ModuleType, public_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                   capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setenv("GDPRGUARDIAN_URL", public_url)
    note = tmp_path / "note.txt"
    note.write_text(SENSITIVE_TEXT, encoding="utf-8")
    assert skill.main(["--text", str(note), "--label-language", "en"]) == 0
    out = capsysbinary.readouterr().out.decode("utf-8")
    assert "[PERSON_1]" in out and "[EMAIL_1]" in out and EMAIL not in out
    monkeypatch.setattr(skill, "MAX_TEXT_CHARS", 10)
    assert skill.main(["--text", str(note)]) == 2
    assert b"text too long" in capsysbinary.readouterr().err


def test_a_large_result_goes_to_a_file(skill: ModuleType, public_url: str, document: Path,
                                       monkeypatch: pytest.MonkeyPatch,
                                       capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setenv("GDPRGUARDIAN_URL", public_url)
    monkeypatch.setattr(skill, "PRINT_LIMIT", 500)
    assert skill.main([str(document)]) == 0
    out = capsysbinary.readouterr().out.decode("utf-8")
    assert "dupont" not in out.lower() and out.startswith("[gdprguardian]") and len(out) < 400
    written = Path(out.split(": ", 1)[1].rsplit(" (", 1)[0])
    try:
        text = written.read_text(encoding="utf-8")
        assert text.startswith("Dossier de M. [PERSONNE_1]") and NIR not in text
        assert not written.with_name(written.name + ".part").exists()
    finally:
        written.unlink()


def test_falls_back_to_the_public_service(skill: ModuleType, capsys: pytest.CaptureFixture[str],
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    assert skill.base_url({}) == skill.PUBLIC_URL == "https://api.gardienrgpd.fr"
    monkeypatch.delenv("GDPRGUARDIAN_URL", raising=False)
    assert skill.main(["--limits"]) == 0
    limits = json.loads(capsys.readouterr().out)
    assert limits == {"service": "https://api.gardienrgpd.fr", "max_file_mb": 50, "max_text_chars": 1_000_000,
                      "public": True}


def test_too_large_a_file_is_refused_before_any_network(skill: ModuleType, document: Path,
                                                        monkeypatch: pytest.MonkeyPatch,
                                                        capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setenv("GDPRGUARDIAN_URL", "http://127.0.0.1:9")  # rien n'écoute / nothing listens
    monkeypatch.setattr(skill, "MAX_FILE_BYTES", 100)
    assert skill.main([str(document)]) == 2
    assert b"file too large" in capsysbinary.readouterr().err


def test_rules_are_sent_only_when_asked(skill: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Une liste de noms à masquer est une donnée personnelle : rien ne part vers le service sans --rules.
    # A deny-list of names is personal data: nothing goes to the service without --rules.
    monkeypatch.chdir(tmp_path)
    assert skill.load_rules(None) is None and not skill.unsent_rules({})
    (tmp_path / ".gdprguardian").mkdir()
    (tmp_path / ".gdprguardian" / "rules.json").write_text('{"rules": [{"label": "X", "pattern": "Y"}]}', "utf-8")
    assert skill.load_rules(None) is None and skill.unsent_rules({})
    assert skill.unsent_rules({"GDPRGUARDIAN_RULES": "elsewhere.json"})
    assert skill.load_rules(".gdprguardian/rules.json")["rules"][0]["label"] == "X"
    with pytest.raises(skill.Failure, match="introuvable"):
        skill.load_rules(str(tmp_path / "absent.json"))
    (tmp_path / "bad.json").write_text("[1, 2]", "utf-8")
    with pytest.raises(skill.Failure, match="objet"):
        skill.load_rules(str(tmp_path / "bad.json"))


def test_project_rules_stay_home_unless_passed(skill: ModuleType, public_url: str, tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch,
                                               capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDPRGUARDIAN_URL", public_url)
    (tmp_path / ".gdprguardian").mkdir()
    rules = tmp_path / ".gdprguardian" / "rules.json"
    rules.write_text('{"deny": {"PROJET": ["Zorglub"]}}', "utf-8")
    note = tmp_path / "note.txt"
    note.write_text("Le projet Zorglub avance.", encoding="utf-8")
    assert skill.main(["--text", str(note)]) == 0
    out, err = capsysbinary.readouterr()
    assert b"Zorglub" in out and b"project rules NOT sent" in err  # règles restées sur le poste / rules stayed home
    assert skill.main(["--text", str(note), "--rules", str(rules)]) == 0
    out, err = capsysbinary.readouterr()
    assert b"Zorglub" not in out and b"NOT sent" not in err


@pytest.mark.parametrize(("name", "expected"), [
    ("CV_Jean_Dupont.PDF", "document.pdf"), ("notes", "document"), ("a.tar.gz", "document.gz"),
    ("bizarre.p df", "document"), ("x.é", "document"),
])
def test_only_the_extension_is_sent(skill: ModuleType, name: str, expected: str) -> None:
    assert skill.upload_name(Path(name)) == expected


def test_unexpected_errors_print_no_traceback(skill: ModuleType, document: Path, monkeypatch: pytest.MonkeyPatch,
                                              capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setenv("GDPRGUARDIAN_URL", "https://rgpd.example.eu")
    monkeypatch.setenv("GDPRGUARDIAN_API_KEY", KEY_A)

    def stalled(*_args: object, **_kwargs: object) -> None:
        raise TimeoutError(f"read timed out on {document}")

    monkeypatch.setattr(skill, "request", stalled)
    assert skill.main([str(document)]) == 1
    out, err = capsysbinary.readouterr()
    assert out == b"" and b"TimeoutError" in err and b"Traceback" not in err and b"dupont" not in err


def test_server_error_messages_are_bounded(skill: ModuleType) -> None:
    body = b'{"error": {"code": "x", "message": "' + b"A" * 5000 + b'\\u001b[2J"}}'
    with pytest.raises(skill.Failure) as caught:
        skill._check(500, body, (200,))
    assert len(str(caught.value)) < 250 and "\x1b" not in str(caught.value)


def test_writes_to_an_output_file(skill: ModuleType, server_url: str, document: Path, tmp_path: Path,
                                  monkeypatch: pytest.MonkeyPatch, capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setenv("GDPRGUARDIAN_URL", server_url)
    monkeypatch.setenv("GDPRGUARDIAN_API_KEY", KEY_A)
    target = tmp_path / "dossier.anon.md"
    assert skill.main([str(document), "-o", str(target)]) == 0
    out, _ = capsysbinary.readouterr()
    assert out == b""
    assert NIR not in target.read_text(encoding="utf-8")
    assert skill.main([str(document), "-o", str(document)]) == 2


def test_wrong_key_is_reported_without_secrets(skill: ModuleType, server_url: str, document: Path,
                                               monkeypatch: pytest.MonkeyPatch,
                                               capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    monkeypatch.setenv("GDPRGUARDIAN_URL", server_url)
    monkeypatch.setenv("GDPRGUARDIAN_API_KEY", "wrong-" + KEY_A)
    assert skill.main([str(document)]) == 1
    out, err = capsysbinary.readouterr()
    assert out == b"" and b"HTTP 401 unauthorized" in err and KEY_A.encode() not in err


class _Busy(http.server.BaseHTTPRequestHandler):
    """Service chargé : 429 avec Retry-After, puis réponse si `free_after` est atteint / busy service."""

    calls: ClassVar[list[str]] = []
    free_after: ClassVar[int] = 10**6

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        _Busy.calls.append(self.path)
        if len(_Busy.calls) > _Busy.free_after:
            body, status = b'{"text": "[PERSONNE_1]", "report": {}}', 200
        else:
            body, status = b'{"error": {"code": "rate_limited", "message": "too many requests"}}', 429
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Retry-After", "0.5")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        """Silencieux / quiet."""


@pytest.mark.parametrize(("free_after", "code"), [(2, 0), (10**6, 3)])
def test_429_is_retried_after_retry_after_then_reported(skill: ModuleType, tmp_path: Path, free_after: int, code: int,
                                                        monkeypatch: pytest.MonkeyPatch,
                                                        capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Busy)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _Busy.calls.clear()
    _Busy.free_after = free_after
    note = tmp_path / "note.txt"
    note.write_text("Jean Dupont", encoding="utf-8")
    monkeypatch.setenv("GDPRGUARDIAN_URL", f"http://127.0.0.1:{server.server_port}")
    try:
        started = time.monotonic()
        assert skill.main(["--text", str(note)]) == code
        elapsed = time.monotonic() - started
    finally:
        server.shutdown()
        server.server_close()
    out, err = capsysbinary.readouterr()
    if code == 0:
        assert out == b"[PERSONNE_1]" and len(_Busy.calls) == 3 and elapsed >= 1.0
    else:
        # Trois nouveaux essais, puis un message clair avec le délai demandé / three retries, then a clear message.
        assert len(_Busy.calls) == 4 and out == b""
        assert b"HTTP 429 rate_limited" in err and b"Retry-After: 0.5 s" in err and b"gdprguardian-local" in err


class _Burnt(http.server.BaseHTTPRequestHandler):
    """Premier PUT refusé après traitement (429, jeton consommé), puis 404 ; second ticket accepté.

    First PUT refused after processing (429, token consumed), then 404; the second ticket goes through.
    """

    log: ClassVar[list[str]] = []

    def _send(self, status: int, payload: dict[str, object], retry: str | None = None) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if retry:
            self.send_header("Retry-After", retry)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        number = sum(entry.startswith("POST") for entry in _Burnt.log) + 1
        _Burnt.log.append("POST")
        self._send(201, {"upload_id": f"up_{number}", "upload_url": f"http://x/v1/uploads/tok{number}",
                         "max_bytes": 10**6})

    def do_PUT(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        _Burnt.log.append(f"PUT {self.path}")
        if self.path.endswith("tok1"):
            first = sum(entry == "PUT /v1/uploads/tok1" for entry in _Burnt.log) == 1
            self._send(429 if first else 404, {"error": {"code": "too_many_unread_results" if first else "not_found",
                                                         "message": "x"}}, "0.5" if first else None)
        else:
            self._send(200, {"status": "ready"})

    def do_GET(self) -> None:
        _Burnt.log.append(f"GET {self.path.split('?')[0]}")
        self._send(200, {"markdown": "[PERSONNE_1]", "next_page": None, "report": {}})

    def do_DELETE(self) -> None:
        _Burnt.log.append("DELETE")
        self._send(204, {})

    def log_message(self, *_args: object) -> None:
        """Silencieux / quiet."""


def test_a_burnt_upload_url_is_replaced_once(skill: ModuleType, document: Path, monkeypatch: pytest.MonkeyPatch,
                                             capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    # Le service consomme l'adresse d'envoi quand il refuse un résultat après traitement : nouvelle adresse, une fois.
    # The service burns the upload URL when it refuses a result after processing: a new URL, once.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Burnt)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _Burnt.log.clear()
    monkeypatch.setattr(skill, "_RETICKET_WAIT_S", 0.1)
    monkeypatch.setenv("GDPRGUARDIAN_URL", f"http://127.0.0.1:{server.server_port}")
    try:
        assert skill.main([str(document)]) == 0
    finally:
        server.shutdown()
        server.server_close()
    assert capsysbinary.readouterr().out == b"[PERSONNE_1]"
    assert _Burnt.log == ["POST", "PUT /v1/uploads/tok1", "PUT /v1/uploads/tok1", "POST", "PUT /v1/uploads/tok2",
                          "GET /v1/results/up_2"]


class _Redirecting(http.server.BaseHTTPRequestHandler):
    """Serveur qui redirige tout ailleurs / a server redirecting everything elsewhere."""

    def do_GET(self) -> None:
        self.send_response(307)
        self.send_header("Location", "http://127.0.0.1:9/elsewhere")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *_args: object) -> None:
        """Silencieux / quiet."""


def test_redirects_are_never_followed(skill: ModuleType) -> None:
    # Une redirection emporterait la clé ailleurs : refusée / a redirect would carry the key elsewhere: refused.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Redirecting)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(skill.Failure, match="redirect"):
            skill.request("GET", f"http://127.0.0.1:{server.server_port}/v1/packs/", KEY_A)
    finally:
        server.shutdown()
        server.server_close()


def test_the_service_never_redirects_a_trailing_slash(server_url: str) -> None:
    # Derrière TLS, la redirection de Starlette visait http:// : le corps repartait en clair. Désormais un 404 JSON.
    # Behind TLS, Starlette's redirect targeted http://, resending the body in clear. Now a JSON 404.
    request = urllib.request.Request(f"{server_url}/v1/anonymize/text/", data=b'{"text": "x"}', method="POST",
                                     headers={"Authorization": f"Bearer {KEY_A}", "Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request, timeout=10)
    assert caught.value.code == 404 and caught.value.headers.get("location") is None


@pytest.mark.parametrize(("url", "expected"), [
    ("https://rgpd.example.eu", "https://rgpd.example.eu"), ("http://127.0.0.1:8000", "http://127.0.0.1:8000"),
    ("http://localhost:8000/", "http://localhost:8000"), ("", "https://api.gardienrgpd.fr"),
    ("  ", "https://api.gardienrgpd.fr"), ("http://rgpd.example.eu", None), ("ftp://rgpd.example.eu", None),
])
def test_base_url_requires_tls_outside_localhost(skill: ModuleType, url: str, expected: str | None) -> None:
    if expected is not None:
        assert skill.base_url({"GDPRGUARDIAN_URL": url}) == expected
    else:
        with pytest.raises(skill.Failure):
            skill.base_url({"GDPRGUARDIAN_URL": url})


def test_usage_errors(skill: ModuleType, document: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        skill.main([])
    assert caught.value.code == 2
    with pytest.raises(SystemExit):
        skill.main([str(document), "--text", "-"])
    assert "document OR --text" in capsys.readouterr().err
