"""Compteur d'usage : un datagramme de métadonnées par anonymisation / usage counter: one metadata datagram each.

Sous Linux et macOS, un démon factice (socket Unix en datagrammes) reçoit ce que le service envoie ; sous
Windows, le compteur ne fait rien et les requêtes passent. On Linux and macOS a fake daemon (Unix datagram
socket) receives what the service sends; on Windows the counter does nothing and requests go through.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from server_testkit import (
    AUTH_A,
    EMAIL,
    IBAN,
    KEY_A,
    KEY_A_SHA256,
    KEY_B,
    MCP_HEADERS,
    NIR,
    PUBLIC,
    SENSITIVE_TEXT,
    from_ip,
    mcp_call,
)

from gdprguardian.documents import ConversionTimeoutError
from gdprguardian.server import ServerConfig, create_app
from gdprguardian.server.config import ConfigError, scrub_settings
from gdprguardian.server.isolation import DOCUMENT_KINDS
from gdprguardian.server.limiter import LimitPolicy
from gdprguardian.server.security import ApiKeyAuthenticator
from gdprguardian.server.usage import (
    FORMATS,
    KINDS,
    MAX_DATAGRAM_BYTES,
    MAX_REPORTED_BYTES,
    MAX_REPORTED_MS,
    UsageReporter,
    encode_usage,
    sender_name,
    usage_format,
)

UNIX_DGRAM = hasattr(socket, "AF_UNIX")
needs_unix = pytest.mark.skipif(not UNIX_DGRAM, reason="socket Unix en datagrammes : Linux et macOS / Linux, macOS")
LINUX = sys.platform.startswith("linux")
needs_linux = pytest.mark.skipif(not LINUX, reason="espace de noms abstrait : Linux / abstract namespace: Linux")
FIELDS = {"v", "kind", "fmt", "bytes", "ms", "ok", "src"}
# Nom de fichier porteur de données personnelles, qui ne doit jamais ressortir / a file name carrying personal data.
FILE_NAME = "CV_Jean_Dupont.txt"
BODY = SENSITIVE_TEXT.encode()
_CREDENTIALS = struct.Struct("iII")  # struct ucred : pid, uid, gid


class Daemon:
    """Démon factice : socket lié, lu sans attente / fake daemon: bound socket, read without waiting."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(path)
        self.sock.setblocking(False)
        # Linux : le noyau joint le PID de l'expéditeur à chaque datagramme / the kernel attaches the sender's PID.
        self.credentials = hasattr(socket, "SO_PASSCRED")
        if self.credentials:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        self.raw: list[bytes] = []
        self.senders: list[int] = []
        # Adresse de l'expéditeur de chaque datagramme / each datagram's sender address.
        self.addresses: list[Any] = []

    @property
    def front_address(self) -> bytes:
        """Adresse abstraite que le vrai démon exige (Linux) / abstract address the real daemon requires."""
        return b"\0" + sender_name(self.path)

    def drain(self) -> list[dict[str, Any]]:
        """Datagrammes reçus depuis le dernier appel, forme vérifiée / datagrams since the last call, checked."""
        received = []
        ancillary_size = socket.CMSG_SPACE(_CREDENTIALS.size) if self.credentials else 0
        while True:
            try:
                data, ancillary, _, address = self.sock.recvmsg(4096, ancillary_size)
            except BlockingIOError:
                return received
            for level, kind, payload in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
                    self.senders.append(_CREDENTIALS.unpack(payload[:_CREDENTIALS.size])[0])
            self.raw.append(data)
            self.addresses.append(address)
            received.append(well_formed(data))


def well_formed(raw: bytes) -> dict[str, Any]:
    """Le contrat, champ par champ / the contract, field by field."""
    assert len(raw) <= MAX_DATAGRAM_BYTES and raw.isascii()
    record = json.loads(raw)
    assert set(record) == FIELDS and record["v"] == 1
    assert record["kind"] in KINDS and record["fmt"] in FORMATS
    assert type(record["bytes"]) is int and record["bytes"] >= 0
    assert type(record["ms"]) is int and record["ms"] >= 0
    assert type(record["ok"]) is bool
    assert record["src"] in ("public", "protocol")
    return record


@pytest.fixture
def daemon() -> Iterator[Daemon]:
    # Dossier court : un chemin de socket Unix tient en 104 à 108 octets / short dir: socket paths are bounded.
    folder = tempfile.mkdtemp(prefix="gg-usage-")
    sink = Daemon(os.path.join(folder, "usage.sock"))
    try:
        yield sink
    finally:
        sink.sock.close()
        shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture
def counted(make_client: Callable[..., TestClient], daemon: Daemon) -> TestClient:
    return make_client(usage_socket=daemon.path, limits=LimitPolicy(mode="off"))


def mcp(client: TestClient, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A}, json=mcp_call(name, arguments))
    assert response.status_code == 200, response.text
    return response.json()["result"]


def path_of(url: str) -> str:
    return url.removeprefix("http://testserver")


def only(daemon: Daemon) -> tuple[str, str, int, bool]:
    records = daemon.drain()
    assert len(records) == 1, records
    record = records[0]
    return record["kind"], record["fmt"], record["bytes"], record["ok"]


# --- Linux et macOS : un vrai socket / Linux and macOS: a real socket ------------------------------------------


@needs_unix
def test_each_anonymisation_sends_one_datagram_without_any_identifier(counted: TestClient, daemon: Daemon) -> None:
    identifiers: list[str] = []
    assert counted.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT}).status_code == 200
    assert only(daemon) == ("text", "text", len(BODY), True)
    assert counted.post("/v1/detect", headers=AUTH_A, json={"text": SENSITIVE_TEXT}).status_code == 200
    assert only(daemon) == ("text", "text", len(BODY), True)
    response = counted.post("/v1/anonymize/file", headers=AUTH_A, files={"file": (FILE_NAME, BODY, "text/plain")})
    assert response.status_code == 200
    assert only(daemon) == ("file", "text", len(BODY), True)

    # Envoi hors bande REST : rien au ticket ni à la lecture, un datagramme au traitement.
    # REST out-of-band upload: nothing at ticket or read time, one datagram at processing.
    ticket = counted.post("/v1/uploads", headers=AUTH_A, json={"filename": FILE_NAME}).json()
    assert daemon.drain() == []
    assert counted.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=BODY).status_code == 200
    assert only(daemon) == ("upload", "text", len(BODY), True)
    assert counted.get(path_of(ticket["result_url"]), headers=AUTH_A).status_code == 200
    assert daemon.drain() == []
    identifiers += [ticket["upload_id"], ticket["upload_url"].rsplit("/", 1)[-1]]

    # MCP : l'outil texte, puis l'entrée de document (create_upload, PUT, get_anonymized).
    # MCP: the text tool, then the document intake.
    assert mcp(counted, "anonymize_text", {"text": SENSITIVE_TEXT})["isError"] is False
    assert only(daemon) == ("mcp_text", "text", len(BODY), True)
    ticket = mcp(counted, "create_upload", {"filename": FILE_NAME})["structuredContent"]
    assert daemon.drain() == []
    assert counted.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=BODY).status_code == 200
    assert only(daemon) == ("mcp_file", "text", len(BODY), True)
    assert mcp(counted, "get_anonymized", {"upload_id": ticket["upload_id"]})["isError"] is False
    assert daemon.drain() == []
    identifiers += [ticket["upload_id"], ticket["upload_url"].rsplit("/", 1)[-1]]

    authenticator = ApiKeyAuthenticator((KEY_A, KEY_B))
    principals = [authenticator.authenticate(f"Bearer {key}") for key in (KEY_A, KEY_B)]
    forbidden = [NIR, EMAIL, IBAN, "Jean", "Dupont", FILE_NAME, "CV_", KEY_A, KEY_B, "testclient", "testserver",
                 "127.0.0.1", *identifiers, *(principal for principal in principals if principal)]
    assert len(daemon.raw) == 6
    leaks = [secret for raw in daemon.raw for secret in forbidden if secret.encode() in raw]
    assert leaks == []
    if LINUX:  # tous du nom que le démon exige / all from the name the daemon requires
        assert daemon.addresses == [daemon.front_address] * 6


@needs_unix
def test_failed_anonymisations_are_counted_with_ok_false(counted: TestClient, daemon: Daemon,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    # Le faux convertisseur ne lit que .txt/.md : un PDF est refusé (415), format tiré de l'extension.
    # The fake converter only reads .txt/.md: a PDF is refused (415), format taken from the extension.
    pdf = b"%PDF-1.7 Jean Dupont"
    response = counted.post("/v1/anonymize/file", headers=AUTH_A,
                            files={"file": ("Rapport_Dupont.pdf", pdf, "application/pdf")})
    assert response.status_code == 415
    assert only(daemon) == ("file", "pdf", len(pdf), False)
    ticket = counted.post("/v1/uploads", headers=AUTH_A, json={"filename": "Contrat_Dupont.docx"}).json()
    assert counted.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=pdf).status_code == 415
    assert only(daemon) == ("upload", "docx", len(pdf), False)

    def past_deadline(*_: Any) -> Any:
        raise ConversionTimeoutError("délai dépassé / deadline exceeded")

    monkeypatch.setattr(counted.app.state.service.runner, "run", past_deadline)
    response = counted.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
    assert response.status_code == 422 and response.json()["error"]["code"] == "processing_timeout"
    assert only(daemon) == ("text", "text", len(BODY), False)
    assert mcp(counted, "anonymize_text", {"text": SENSITIVE_TEXT})["isError"] is True
    assert only(daemon) == ("mcp_text", "text", len(BODY), False)
    assert not any(secret in raw for raw in daemon.raw for secret in (b"Dupont", b"Rapport", b"Contrat", NIR.encode()))


@needs_unix
def test_requests_refused_at_the_door_are_not_anonymisations(make_client: Callable[..., TestClient],
                                                             daemon: Daemon) -> None:
    client = make_client(usage_socket=daemon.path, limits=LimitPolicy(mode="off"), max_text_chars=1_000,
                         max_upload_bytes=2**20)
    refused = [
        client.post("/v1/anonymize/text", json={"text": SENSITIVE_TEXT}),                     # sans clé / no key
        client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x", "profile": "turbo"}),
        client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": "x" * 1_001}),       # trop long / too long
        client.post("/v1/anonymize/text", headers={**AUTH_A, "Content-Type": "application/json"},
                    content=b'{"text": "\\ud800"}'),                                         # substitut isolé
        client.post("/v1/anonymize/file", headers=AUTH_A,
                    files={"file": (FILE_NAME, b"x" * (2**20 + 1), "text/plain")}),           # trop gros / too big
    ]
    assert [response.status_code for response in refused] == [401, 422, 413, 422, 413]
    ticket = client.post("/v1/uploads", headers=AUTH_A, json={"filename": FILE_NAME}).json()
    assert client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x" * (2**20 + 1)).status_code == 413
    assert daemon.drain() == []


@needs_unix
def test_nothing_is_sent_when_the_variable_is_unset(make_client: Callable[..., TestClient], daemon: Daemon) -> None:
    client = make_client()
    assert client.app.state.service.usage.enabled is False
    assert client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT}).status_code == 200
    assert mcp(client, "anonymize_text", {"text": SENSITIVE_TEXT})["isError"] is False
    assert daemon.drain() == []


@needs_unix
@pytest.mark.parametrize("state", ["missing", "stale", "regular_file", "full", "forbidden"])
def test_a_dead_full_or_forbidden_socket_never_breaks_a_request(make_client: Callable[..., TestClient],
                                                                 state: str) -> None:
    folder = tempfile.mkdtemp(prefix="gg-usage-")
    path = os.path.join(folder, "usage.sock")
    keep: list[socket.socket] = []
    try:
        if state == "regular_file":
            Path(path).write_bytes(b"")
        elif state != "missing":
            sink = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sink.bind(path)
            if state == "stale":
                sink.close()  # le fichier reste, plus personne n'écoute / the file stays, nobody listens
            else:
                keep.append(sink)
            if state == "forbidden":
                os.chmod(path, 0)  # sans effet pour root : la requête doit passer de toute façon / no effect as root
        client = make_client(usage_socket=path, limits=LimitPolicy(mode="off"))
        if state == "full":
            for _ in range(5_000):  # file du démon remplie, jamais lue / daemon queue filled, never read
                client.app.state.service.usage.report("text", "text", 1, 1.0, True)
        started = time.perf_counter()
        for _ in range(3):
            response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
            assert response.status_code == 200 and NIR not in response.text
        response = client.post("/v1/anonymize/file", headers=AUTH_A, files={"file": (FILE_NAME, BODY, "text/plain")})
        assert response.status_code == 200
        assert mcp(client, "anonymize_text", {"text": SENSITIVE_TEXT})["isError"] is False
        assert time.perf_counter() - started < 30
    finally:
        for sink in keep:
            sink.close()
        shutil.rmtree(folder, ignore_errors=True)


@needs_unix
def test_report_never_waits_on_a_full_queue(daemon: Daemon) -> None:
    reporter = UsageReporter(daemon.path)
    started = time.perf_counter()
    for _ in range(5_000):
        reporter.report("upload", "pdf", 10, 1.0, True)
    assert time.perf_counter() - started < 5
    assert daemon.drain()  # reçus jusqu'à la limite de la file, le reste perdu / received up to the queue limit
    reporter.close()


@needs_unix
def test_measure_reports_the_outcome_even_on_an_exception(daemon: Daemon) -> None:
    reporter = UsageReporter(daemon.path)
    with pytest.raises(RuntimeError), reporter.measure("file", 12, "pdf"):
        raise RuntimeError
    with reporter.measure("mcp_file", 12, "pdf") as measure:
        measure.fmt, measure.ok = "docx", True
    reporter.close()
    reporter.report("text", "text", 3, 0.4, True)  # rouvert à la demande / reopened on demand
    reporter.close()
    assert [(r["kind"], r["fmt"], r["bytes"], r["ok"]) for r in daemon.drain()] == [
        ("file", "pdf", 12, False), ("mcp_file", "docx", 12, True), ("text", "text", 3, True)]


@pytest.mark.skipif(not hasattr(socket, "SO_PASSCRED"), reason="SO_PASSCRED : Linux")
def test_datagrams_come_from_the_front_process_never_from_a_worker(daemon: Daemon) -> None:
    # Service réel isolé : chaque requête dans un processus neuf ; le PID de l'expéditeur, joint par le noyau,
    # est celui de ce processus. Real isolated service; the sender's PID, attached by the kernel, is ours.
    config = ServerConfig(api_keys=(KEY_A,), prewarm_workers=1, max_concurrency=1, limits=LimitPolicy(mode="off"),
                          usage_socket=daemon.path)
    assert config.isolation
    with TestClient(create_app(config)) as client:
        assert client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT}).status_code == 200
        response = client.post("/v1/anonymize/file", headers=AUTH_A,
                               files={"file": ("clients.csv", f"nom;nir\nJean Dupont;{NIR}\n".encode(), "text/csv")})
        assert response.status_code == 200
    records = daemon.drain()
    assert [(r["kind"], r["fmt"], r["ok"]) for r in records] == [("text", "text", True), ("file", "csv", True)]
    assert daemon.senders == [os.getpid(), os.getpid()]
    assert daemon.addresses == [daemon.front_address] * 2


@needs_unix
def test_the_real_service_reads_the_variable_before_scrubbing_and_sends_from_its_front(daemon: Daemon,
                                                                                         tmp_path: Path) -> None:
    # `gdprguardian serve` tel qu'en production : réglages lus puis retirés, processus durci, travailleurs isolés.
    # `gdprguardian serve` as in production: settings read then scrubbed, hardened process, isolated workers.
    api, log = tmp_path / "api.sock", tmp_path / "server.log"
    env = {name: value for name, value in os.environ.items() if not name.startswith("GDPRGUARDIAN_")}
    env.update(GDPRGUARDIAN_API_KEY_SHA256=KEY_A_SHA256, GDPRGUARDIAN_MAX_CONCURRENCY="1",
               GDPRGUARDIAN_PREWARM_WORKERS="0", GDPRGUARDIAN_USAGE_SOCKET=daemon.path)
    code = "import sys; from gdprguardian.cli import main; sys.exit(main(sys.argv[1:]))"
    with log.open("wb") as stderr:
        server = subprocess.Popen([sys.executable, "-c", code, "serve", "--uds", str(api), "--log-level", "warning"],
                                  env=env, stdout=subprocess.DEVNULL, stderr=stderr)
    try:
        deadline = time.monotonic() + 60
        while not api.exists():
            assert server.poll() is None, log.read_text(errors="replace")[-2000:]
            assert time.monotonic() < deadline, "socket absent après 60 s / socket missing after 60 s"
            time.sleep(0.2)
        body = json.dumps({"text": SENSITIVE_TEXT}).encode()
        request = (b"POST /v1/anonymize/text HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n"
                   b"Authorization: Bearer " + KEY_A.encode() + b"\r\nContent-Type: application/json\r\n"
                   b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body)
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(60)
            client.connect(str(api))
            client.sendall(request)
            reply = b""
            while chunk := client.recv(65536):
                reply += chunk
        assert reply.startswith(b"HTTP/1.1 200") and b"[NIR_1]" in reply, reply[:300]
        records = daemon.drain()
        assert [(r["kind"], r["fmt"], r["bytes"], r["ok"]) for r in records] == [("text", "text", len(BODY), True)]
        if daemon.credentials:
            assert daemon.senders == [server.pid]  # le processus d'accueil, pas un travailleur / the front process
        if LINUX:
            assert daemon.addresses == [daemon.front_address]
            # Le nom est tenu par le service : un autre processus ne peut pas le prendre / held by the service.
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as intruder, pytest.raises(OSError):
                intruder.bind(daemon.front_address)
        assert not any(secret.encode() in daemon.raw[0] for secret in (NIR, EMAIL, IBAN, "Dupont", KEY_A))
    finally:
        server.terminate()
        server.wait(timeout=30)


@needs_linux
def test_the_reporter_holds_its_sender_name_from_construction(daemon: Daemon) -> None:
    # Pris avant tout envoi, donc avant tout travailleur / taken before any send, hence before any worker.
    reporter = UsageReporter(daemon.path)
    assert reporter.sender == daemon.front_address
    # Un second expéditeur (un travailleur compromis à sa place) ne peut pas prendre le nom ; il n'envoie rien.
    # A second sender (a compromised worker in its place) cannot take the name; it sends nothing.
    intruder = UsageReporter(daemon.path)
    assert intruder.sender is None
    intruder.report("text", "text", 1, 1.0, True)
    reporter.report("text", "text", 2, 1.0, True)
    assert [record["bytes"] for record in daemon.drain()] == [2]
    assert daemon.addresses == [daemon.front_address]
    # Rendu à la fermeture (arrêt du service), repris au premier envoi suivant / released at close, taken again.
    reporter.close()
    intruder.close()
    reporter.report("upload", "pdf", 3, 1.0, True)
    assert reporter.sender == daemon.front_address
    assert [record["bytes"] for record in daemon.drain()] == [3]
    reporter.close()


def test_the_sender_name_matches_the_daemon() -> None:
    # Même dérivation que `usage_sender_name` du démon (site/src/server.rs) / same derivation as the daemon.
    production = "/run/gdprguardian-stats/usage.sock"
    assert sender_name(production) == b"gdprguardian-usage:" + production.encode()
    long = "/" + "x" * 106
    assert len(sender_name(long)) == 107 and sender_name(long).startswith(b"gdprguardian-usage:/xxx")


@needs_unix
@pytest.mark.anyio
async def test_local_mcp_tools_are_counted_as_mcp(daemon: Daemon, fake_documents: None, tmp_path: Path) -> None:
    from fastmcp import Client

    from gdprguardian.server.mcp_local import build_local_mcp

    folder = tmp_path / "dossiers"
    folder.mkdir()
    (folder / FILE_NAME).write_bytes(BODY)
    server = build_local_mcp([folder], ServerConfig(dev_no_auth=True, limits=LimitPolicy(mode="off"), isolation=False,
                                                    usage_socket=daemon.path))
    async with Client(server) as client:
        await client.call_tool("anonymize_file", {"path": str(folder / FILE_NAME)})
        await client.call_tool("anonymize_text", {"text": SENSITIVE_TEXT})
    assert [(r["kind"], r["fmt"], r["bytes"], r["ok"]) for r in daemon.drain()] == [
        ("mcp_file", "text", len(BODY), True), ("mcp_text", "text", len(BODY), True)]
    assert not any(b"Dupont" in raw or str(folder).encode() in raw for raw in daemon.raw)


# --- toutes plates-formes / every platform ---------------------------------------------------------------------


def test_requests_succeed_with_a_configured_counter_on_every_platform(make_client: Callable[..., TestClient]) -> None:
    # Windows : rien à envoyer (pas de AF_UNIX) ; ailleurs : aucun démon à ce chemin, l'envoi échoue en silence.
    # Windows: nothing to send; elsewhere: no daemon at this path, sending fails silently.
    client = make_client(usage_socket="/run/gdprguardian-stats-absent/usage.sock", limits=LimitPolicy(mode="off"))
    assert client.app.state.service.usage.enabled is UNIX_DGRAM
    assert client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT}).status_code == 200
    response = client.post("/v1/anonymize/file", headers=AUTH_A, files={"file": (FILE_NAME, BODY, "text/plain")})
    assert response.status_code == 200
    ticket = client.post("/v1/uploads", headers=AUTH_A, json={"filename": FILE_NAME}).json()
    assert client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=BODY).status_code == 200
    assert mcp(client, "anonymize_text", {"text": SENSITIVE_TEXT})["isError"] is False


def test_without_unix_datagram_sockets_the_counter_is_a_silent_no_op(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(socket, "AF_UNIX", raising=False)  # comme sous Windows / as on Windows
    reporter = UsageReporter("/run/gdprguardian-stats/usage.sock")
    assert reporter.enabled is False
    with reporter.measure("text", 10, "text") as measure:
        measure.ok = True
    reporter.report("mcp_file", "pdf", 10, 1.0, True)
    reporter.close()


@pytest.mark.parametrize("value", [None, "", "   "])
def test_unset_or_empty_variable_disables_the_counter(value: str | None) -> None:
    env = {"GDPRGUARDIAN_API_KEY_SHA256": KEY_A_SHA256} | (
        {} if value is None else {"GDPRGUARDIAN_USAGE_SOCKET": value})
    config = ServerConfig.from_env(env)
    assert config.usage_socket is None and UsageReporter(config.usage_socket).enabled is False


def test_variable_is_read_then_scrubbed_before_any_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "environ", {"GDPRGUARDIAN_API_KEY_SHA256": KEY_A_SHA256,
                                        "GDPRGUARDIAN_USAGE_SOCKET": " /run/gdprguardian-stats/usage.sock "})
    config = ServerConfig.from_env()
    scrub_settings()
    assert config.usage_socket == "/run/gdprguardian-stats/usage.sock"
    assert os.environ == {}


@pytest.mark.parametrize("value", ["usage.sock", "run/usage.sock", "C:\\run\\usage.sock", "/" + "x" * 107,
                                   "/run/a\x00b"])
def test_an_invalid_socket_path_refuses_to_start(value: str) -> None:
    with pytest.raises(ConfigError, match="GDPRGUARDIAN_USAGE_SOCKET"):
        ServerConfig.from_env({"GDPRGUARDIAN_API_KEY_SHA256": KEY_A_SHA256, "GDPRGUARDIAN_USAGE_SOCKET": value})
    assert ServerConfig.from_env({"GDPRGUARDIAN_API_KEY_SHA256": KEY_A_SHA256,
                                  "GDPRGUARDIAN_USAGE_SOCKET": "/" + "x" * 106}).usage_socket == "/" + "x" * 106


def test_provenance_is_a_closed_value() -> None:
    assert encode_usage("text", "text", 1, 1.0, True, "protocol").endswith(b',"src":"protocol"}')
    assert encode_usage("text", "text", 1, 1.0, True, "203.0.113.7").endswith(b',"src":"public"}')  # hors liste


@needs_unix
def test_requests_from_the_server_itself_are_marked_protocol(make_client: Callable[..., TestClient],
                                                              daemon: Daemon) -> None:
    # Sans en-tête d'adresse (protocole lancé sur le serveur) : « protocol » ; via Nginx : « public ».
    # Without the address header (protocol run on the server): "protocol"; through Nginx: "public".
    client = make_client(**PUBLIC, usage_socket=daemon.path)
    assert client.post("/v1/anonymize/text", json={"text": SENSITIVE_TEXT}).status_code == 200
    assert client.post("/v1/anonymize/text", headers=from_ip("203.0.113.7"),
                       json={"text": SENSITIVE_TEXT}).status_code == 200
    ticket = client.post("/v1/uploads", headers=from_ip("203.0.113.7"), json={"filename": "a.txt"}).json()
    assert client.put(path_of(ticket["upload_url"]), content=BODY).status_code == 200  # PUT du serveur / local PUT
    records = daemon.drain()
    assert [(r["kind"], r["src"]) for r in records] == [("text", "protocol"), ("text", "public"),
                                                        ("upload", "protocol")]
    assert not any(b"203.0.113" in raw for raw in daemon.raw)


def test_datagram_is_built_from_closed_values_only() -> None:
    assert encode_usage("mcp_file", "pdf", 10_485_760, 2.6, True) == (
        b'{"v":1,"kind":"mcp_file","fmt":"pdf","bytes":10485760,"ms":3,"ok":true,"src":"public"}')
    # Format inconnu : « other » ; négatifs bornés à 0 ; seul True vaut réussite.
    # Unknown format: "other"; negatives clamped to 0; only True means success.
    assert encode_usage("upload", "exe", -5, -1.0, 1) == (
        b'{"v":1,"kind":"upload","fmt":"other","bytes":0,"ms":0,"ok":false,"src":"public"}')
    assert encode_usage("Jean Dupont", "pdf", 1, 1.0, True) is None  # origine hors liste : rien / unknown origin
    # Bornes du démon (256 Mio, une heure) : jamais dépassées, le datagramme reste compté / daemon's bounds kept.
    largest = encode_usage("mcp_text", "other", 2**63, 1e15, True)
    assert largest is not None and len(largest) <= MAX_DATAGRAM_BYTES
    record = well_formed(largest)
    assert (record["bytes"], record["ms"]) == (MAX_REPORTED_BYTES, MAX_REPORTED_MS) == (2**28, 3_600_000)


@pytest.mark.parametrize(("name", "expected"), [
    ("txt", "text"), ("odf-xml", "odt"), ("xlsm", "xlsx"), ("xlsb", "xlsx"), ("PDF", "pdf"), (".docx", "docx"),
    ("htm", "html"), ("markdown", "md"), ("csv", "csv"), ("msg", "msg"), ("odg", "other"), ("zip", "other"),
    ("exe", "other"), ("", "other"), (None, "other"), ("Jean_Dupont", "other"),
])
def test_formats_map_to_the_closed_list(name: str | None, expected: str) -> None:
    assert usage_format(name) == expected


def test_every_detected_document_kind_maps_to_the_closed_list() -> None:
    mapped = {kind: usage_format(kind) for kind in DOCUMENT_KINDS}
    assert set(mapped.values()) <= FORMATS
    # Conteneurs non identifiés et dessins seulement en « other » / only unidentified containers and drawings.
    assert {kind for kind, fmt in mapped.items() if fmt == "other"} == {"zip", "ole", "odg"}
