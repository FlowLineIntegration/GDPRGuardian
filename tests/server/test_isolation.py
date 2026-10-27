"""Une requête, un processus : traitement isolé de bout en bout / one request, one process, end to end.

Ces tests lancent de vrais travailleurs (zygote et fork sous Linux, spawn ailleurs) ; les autres tests du
service suivent le même protocole dans le processus de test. These tests start real workers (zygote and fork
on Linux, spawn elsewhere); the other service tests follow the same protocol inside the test process.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import anyio
import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, EMAIL, KEY_A, MCP_HEADERS, NIR, SENSITIVE_TEXT, load_script, mcp_call

from gdprguardian import Anonymizer, _native
from gdprguardian.convert import _sandbox
from gdprguardian.convert._base import CRASH_MESSAGE
from gdprguardian.documents import ConversionTimeoutError, DocumentError
from gdprguardian.server import ServerConfig, create_app
from gdprguardian.server import options as options_module
from gdprguardian.server.isolation import DOCUMENT_KINDS, JobError, decode_document, decode_text
from gdprguardian.server.limiter import LimitPolicy
from gdprguardian.server.options import AnonymizeOptions
from gdprguardian.server.service import Service

SAMPLES = load_script(Path(__file__).resolve().parents[1] / "convert" / "convert_samples.py", "convert_samples_iso")
CORPUS = sorted((Path(__file__).resolve().parents[2] / "datasets" / "fr" / "docs").glob("fr-*.md"))
WORKER_RE = re.compile(r"\bworker=(\d+)")
RULES = {"name": "acme", "rules": [{"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}", "context": ["client"]}],
         "deny": {"PROJET": ["Opération Phénix"]}, "allow": ["support@acme.fr"]}


@pytest.fixture(scope="module")
def isolated() -> Iterator[TestClient]:
    """Service réel, isolé : un processus neuf par requête / real isolated service, a fresh process per request."""
    config = ServerConfig(api_keys=(KEY_A,), prewarm_workers=2, max_concurrency=2, limits=LimitPolicy(mode="off"),
                          page_chars=1000)
    assert config.isolation
    with TestClient(create_app(config)) as client:
        yield client


@pytest.fixture
def worker_pids(caplog: pytest.LogCaptureFixture) -> Callable[[], list[int]]:
    caplog.set_level(logging.DEBUG, logger="gdprguardian.server")  # événements par requête / per-request events
    return lambda: [int(pid) for record in caplog.records for pid in WORKER_RE.findall(record.getMessage())]


def test_every_request_runs_in_its_own_process_and_never_in_the_main_one(
        isolated: TestClient, worker_pids: Callable[[], list[int]]) -> None:
    options_module._anonymizer.cache_clear()
    for _ in range(3):
        text = isolated.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
        assert text.status_code == 200 and "[NIR_1]" in text.json()["text"]
        assert NIR not in text.text and "timings_ms" not in text.json()["report"]
    detect = isolated.post("/v1/detect", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
    assert detect.json()["report"]["entities"]["NIR"] == 1
    upload = isolated.post("/v1/anonymize/file", headers=AUTH_A,
                           files={"file": ("dossier.txt", SENSITIVE_TEXT.encode(), "text/plain")})
    assert upload.status_code == 200 and "[NIR_1]" in upload.json()["markdown"]
    tool = isolated.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                         json=mcp_call("anonymize_text", {"text": f"mail {EMAIL}"})).json()["result"]
    assert tool["content"][0]["text"] == "mail [EMAIL_1]"
    pids = worker_pids()
    assert len(pids) == 6 and os.getpid() not in pids
    # Sous Linux les PID ne reviennent pas si vite ; Windows les recycle dès la fin d'un processus.
    # On Linux PIDs do not come back that fast; Windows recycles them as soon as a process ends.
    assert len(set(pids)) == 6 if sys.platform.startswith("linux") else len(set(pids)) >= 2
    # Le texte n'a jamais été anonymisé ici : aucun moteur construit / no engine built in this process.
    assert options_module._anonymizer.cache_info().currsize == 0


def test_isolated_results_are_identical_to_the_in_process_engine(isolated: TestClient) -> None:
    # Même texte, même rapport (hors mesures internes) : l'isolement ne change rien au résultat.
    # Same text, same report (internal timings aside): isolation changes nothing in the result.
    reference = Anonymizer(countries=("FR",))
    for path in CORPUS[:4]:
        text = path.read_text(encoding="utf-8")
        body = isolated.post("/v1/anonymize/text", headers=AUTH_A, json={"text": text}).json()
        expected = reference.anonymize(text)
        report = {key: value for key, value in expected.report.items() if key != "timings_ms"}
        # Le service donne toujours une liste d'avertissements (vide ici) / the service always gives a warnings list.
        report["warnings"] = list(report.get("warnings", []))
        # Mode par défaut (fort) et catégories coupées toujours rapportés / default mode always reported.
        report = AnonymizeOptions().annotate(report)
        assert body["text"] == expected.text and body["report"] == json.loads(json.dumps(report))


@pytest.mark.parametrize(("name", "builder", "kind"), [
    ("contrat.pdf", "contract_pdf", "pdf"), ("contrat.docx", "make_docx", "docx"), ("message.eml", "make_eml", "eml"),
])
def test_real_formats_are_converted_and_anonymised_in_the_worker(isolated: TestClient, name: str, builder: str,
                                                                  kind: str) -> None:
    data = getattr(SAMPLES, builder)()
    response = isolated.post("/v1/anonymize/file", headers=AUTH_A,
                             files={"file": (name, data, "application/octet-stream")})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == kind and f"document.{name.rsplit('.', 1)[1]}" not in body["markdown"]
    planted = {*SAMPLES.SECRETS, *(secret.replace(" ", "") for secret in SAMPLES.SECRETS), SAMPLES.AUTHOR}
    assert [secret for secret in planted if secret in body["markdown"]] == []
    assert body["report"]["total_replaced"] >= 3 and "timings_ms" not in body["report"]


def test_spreadsheets_go_through_the_tabular_pipeline_in_the_worker(isolated: TestClient) -> None:
    csv = f"nom;nir;courriel\nJean Dupont;{NIR};{EMAIL}\n".encode()
    response = isolated.post("/v1/anonymize/file", headers=AUTH_A, files={"file": ("clients.csv", csv, "text/csv")})
    assert response.status_code == 200 and response.json()["kind"] == "csv"
    assert NIR not in response.text and EMAIL not in response.text


@pytest.mark.parametrize(("name", "data", "status", "code"), [
    ("scan.pdf", None, 422, "encrypted_document"),
    ("broken.pdf", b"%PDF-1.7\n%%EOF", 422, "document_error"),
    ("blob.bin", b"\x00\x01\x02\x03" * 64, 415, "unsupported_format"),
])
def test_document_errors_cross_the_process_boundary_with_fixed_messages(isolated: TestClient, name: str,
                                                                         data: bytes | None, status: int,
                                                                         code: str) -> None:
    data = data or SAMPLES.encrypt_pdf(SAMPLES.contract_pdf(), "secret")
    response = isolated.post("/v1/anonymize/file", headers=AUTH_A, files={"file": (name, data, "application/pdf")})
    assert response.status_code == status and response.json()["error"]["code"] == code
    assert "Dupont" not in response.text


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
def test_organisation_rules_travel_as_json_and_apply_in_the_worker(isolated: TestClient) -> None:
    text = f"Client CLT-204518, NIR {NIR}, Opération Phénix, support@acme.fr."
    response = isolated.post("/v1/anonymize/text", headers=AUTH_A, json={"text": text, "rules": RULES, "explain": True})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Client [CLIENT_ID_1], NIR [NIR_1], [PROJET_1], support@acme.fr."
    assert body["report"]["rules"] == "acme" and body["report"]["explain"]


@pytest.mark.skipif(not _native.available(), reason="noyau Rust requis / Rust core required")
def test_rules_are_compiled_and_refused_in_the_worker_never_in_the_front(isolated: TestClient,
                                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    original = _native.build
    monkeypatch.setattr(_native, "build", lambda *args, **kwargs: calls.append(1) or original(*args, **kwargs))
    # Jeu hostile de la revue (\b\w{600} x 20, ~1 Ko) : autrefois 1,5 Go et des secondes dans l'accueil.
    # The review's hostile set: formerly 1.5 GB and seconds in the front.
    hostile = {"rules": [{"label": f"R{i}", "pattern": r"\b\w{600}"} for i in range(20)]}
    started = time.perf_counter()
    response = isolated.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT, "rules": hostile})
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_request"
    assert "size limit" in response.json()["error"]["message"] and time.perf_counter() - started < 30
    # Création d'envoi : règles compilées dans un travailleur, refus avant que le fichier parte.
    # Creating an upload: rules compiled in a worker, refused before the file leaves.
    ticket = isolated.post("/v1/uploads", headers=AUTH_A, json={"filename": "dossier.txt", "rules": hostile})
    assert ticket.status_code == 422 and "size limit" in ticket.json()["error"]["message"]
    tool = isolated.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                         json=mcp_call("anonymize_text", {"text": SENSITIVE_TEXT, "rules": hostile})).json()["result"]
    assert tool["isError"] is True and tool["content"][0]["text"].startswith("invalid_request:")
    assert calls == []  # rien de compilé dans ce processus / nothing compiled in this process


def test_upload_flow_is_isolated_too(isolated: TestClient) -> None:
    ticket = isolated.post("/v1/uploads", headers=AUTH_A, json={"filename": "dossier.txt"}).json()
    put = isolated.put(ticket["upload_url"].removeprefix("http://testserver"), headers=AUTH_A,
                       content=SENSITIVE_TEXT.encode())
    assert put.status_code == 202 and put.json()["status"] == "processing"
    result = isolated.get(ticket["result_url"].removeprefix("http://testserver"), headers=AUTH_A).json()
    assert "[NIR_1]" in result["markdown"] and NIR not in result["markdown"] and result["deleted"] is True


def test_options_round_trip_through_json_with_untrusted_rules() -> None:
    options = AnonymizeOptions.build(["BE", "fr"], "strict", "en", RULES, True) if _native.available() else (
        AnonymizeOptions.build(["BE", "fr"], "strict", "en", None, True))
    restored = AnonymizeOptions.from_json(json.loads(json.dumps(options.to_json())))
    # « strict » (profil déprécié) devient le mode fort / deprecated profile "strict" becomes mode fort.
    assert (restored.countries, restored.mode, restored.disable, restored.label_language, restored.explain) == (
        ("BE", "FR"), "fort", (), "en", True)
    custom = AnonymizeOptions.build("FR", None, "fr", None, False, disable=["codes", "functional_mailboxes"])
    assert AnonymizeOptions.from_json(json.loads(json.dumps(custom.to_json()))).disable == (
        "boites_fonctionnelles", "codes")
    if options.rules is not None:
        assert restored.rules is not None and restored.rules.trusted is False
        assert (restored.rules.rules, restored.rules.deny, restored.rules.allow) == (
            options.rules.rules, options.rules.deny, options.rules.allow)
    assert AnonymizeOptions.from_json(AnonymizeOptions(countries="all").to_json()).countries == "all"


@pytest.mark.parametrize("value", [
    None, "texte", {"error": "surprise"}, {"error": ["internal"]}, _sandbox.Body(["not", "a", "dict"], "x"),
    _sandbox.Body({"report": []}, "x"),
])
def test_text_replies_are_shape_checked(value: Any) -> None:
    with pytest.raises(DocumentError, match=re.escape(CRASH_MESSAGE[:20])):
        decode_text(value)
    assert decode_text(_sandbox.Body({"report": {}, "worker": 12}, "ok")).worker == 12


@pytest.mark.parametrize("meta", [
    {"kind": "exe"}, {"kind": ["pdf"]}, {"kind": "pdf", "pages": "2"}, {"kind": "pdf", "warnings": [3]},
    {"kind": "pdf", "dropped": {"Images": 1}}, {"kind": "pdf", "dropped": {"images": "1"}},
    {"kind": "pdf", "report": []},
])
def test_document_replies_are_shape_checked(meta: dict[str, Any]) -> None:
    valid = {"kind": "pdf", "pages": 2, "warnings": ["w"], "dropped": {"images": 1}, "report": {}, "worker": 7}
    with pytest.raises(DocumentError, match=re.escape(CRASH_MESSAGE[:20])):
        decode_document(_sandbox.Body({**valid, **meta}, "md"))
    result, worker = decode_document(_sandbox.Body(valid, "md"))
    assert (result.kind, result.pages, worker) == ("pdf", 2, 7) and {"xlsx", "csv", "odf-xml"} <= DOCUMENT_KINDS


def test_application_errors_keep_only_a_closed_code() -> None:
    with pytest.raises(JobError) as caught:
        decode_text({"error": "internal", "type": "Jean Dupont", "message": "Jean Dupont"})
    assert caught.value.code == "internal" and caught.value.error_type == "unknown" and caught.value.message == ""


def test_a_rule_refusal_keeps_a_bounded_encodable_reason() -> None:
    with pytest.raises(JobError) as caught:
        decode_text({"error": "invalid_rules", "message": "Règle n°1 (X) : \ud800" + "x" * 5000})
    message = caught.value.message
    assert caught.value.code == "invalid_rules" and message.startswith("Règle n°1 (X) : ?")
    assert len(message) <= 600 and message.encode("utf-8")
    with pytest.raises(JobError) as caught:
        decode_text({"error": "invalid_rules", "message": ["pas", "un texte"]})
    assert caught.value.message and "refusées" in caught.value.message


def test_a_worker_dying_with_organisation_rules_is_a_client_error(make_client: Callable[..., TestClient],
                                                                   monkeypatch: pytest.MonkeyPatch,
                                                                   caplog: pytest.LogCaptureFixture) -> None:
    """Filet de sécurité derrière le budget de compilation : un texte n'a pas de convertisseur, sa mort avec des
    règles leur revient (422, DEBUG), jamais 500/ERROR. Safety net behind the compile budget: a text has no
    converter, its death with rules is theirs (422, DEBUG), never 500/ERROR."""
    caplog.set_level(logging.DEBUG, logger="gdprguardian.server")
    client = make_client()

    def crashing(*_args: object) -> None:
        raise DocumentError(CRASH_MESSAGE)

    monkeypatch.setattr(client.app.state.service.runner, "run", crashing)
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT, "rules": RULES})
    assert response.status_code == 422 and response.json()["error"]["code"] == "rules_too_costly"
    assert "event=text_rejected code=rules_too_costly" in caplog.text and "ERROR" not in caplog.text
    assert NIR not in response.text and "Dupont" not in caplog.text
    # Sans règles, la même mort reste une erreur du service / without rules, the same death stays a server error.
    assert client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT}).status_code == 500


def test_the_warm_up_loads_plane_14_without_changing_any_result() -> None:
    """Le zygote charge le plan 14 (étiquettes) en se chauffant ; un résultat ne dépend jamais des plans déjà
    chargés. The zygote loads plane 14 (tags) while warming up; a result never depends on the planes loaded."""
    import subprocess

    code = (
        "from gdprguardian import _native\n"
        "from gdprguardian.server.isolation import _WARM_UP_TEXT\n"
        "from gdprguardian.server.options import AnonymizeOptions\n"
        "assert any(0xE0000 <= ord(c) <= 0xEFFFF for c in _WARM_UP_TEXT)\n"
        "text = 'M. Jean Martin\\U000E0041, jean.martin@exemple.fr\\U000E0067 \\U0001F3F4\\U000E007F 06 12 34 56 78'\n"
        "engine = AnonymizeOptions().anonymizer()\n"
        "cold = engine.anonymize(text).text\n"
        "tables = _native.unicode_tables()\n"
        "assert tables is None or 14 in tables.loaded_planes\n"
        "engine.anonymize(_WARM_UP_TEXT)\n"
        "assert engine.anonymize(text).text == cold\n"
        "print(cold.encode('unicode_escape').decode())\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300, env=os.environ)
    assert done.returncode == 0, done.stderr[-2000:]
    assert "[EMAIL_1]" in done.stdout and "[TEL_1]" in done.stdout


@pytest.mark.parametrize(("failure", "status", "code", "logged"), [
    # Échéance dépassée : erreur documentée du client, comme `conversion_timeout` / documented client error.
    (ConversionTimeoutError("délai"), 422, "processing_timeout", "event=text_rejected code=processing_timeout"),
    (DocumentError(CRASH_MESSAGE), 500, "internal_error", "error=worker_failure"),
    (_sandbox.WorkerStartError("start"), 503, "service_busy", None),
])
def test_worker_failures_on_texts_use_fixed_errors(make_client: Callable[..., TestClient],
                                                   monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
                                                   failure: Exception, status: int, code: str,
                                                   logged: str | None) -> None:
    # Refus du client journalisés en DEBUG (aucun journal d'activité en service) / client refusals at DEBUG.
    caplog.set_level(logging.DEBUG, logger="gdprguardian.server")
    client = make_client()

    def failing(*_args: object) -> None:
        raise failure

    monkeypatch.setattr(client.app.state.service.runner, "run", failing)
    response = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": SENSITIVE_TEXT})
    assert response.status_code == status and response.json()["error"]["code"] == code
    assert NIR not in response.text and "Dupont" not in caplog.text
    if status == 503:
        assert int(response.headers["retry-after"]) >= 1
    if logged:
        assert logged in caplog.text


def _alive(worker: Any) -> bool:
    if hasattr(worker, "process"):
        return bool(worker.process.is_alive())
    try:
        with open(f"/proc/{worker.pid}/stat", encoding="ascii") as handle:
            return handle.read().rsplit(")", 1)[1].split()[0] not in ("Z", "X")
    except OSError:
        return False


@pytest.mark.anyio
async def test_a_cancelled_request_kills_its_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    service = Service(ServerConfig(dev_no_auth=True, max_concurrency=1, prewarm_workers=1))
    attached: list[Any] = []
    original = _sandbox.CancelHandle._attach

    def spy(handle: _sandbox.CancelHandle, worker: Any) -> bool:
        attached.append(worker)
        return original(handle, worker)

    monkeypatch.setattr(_sandbox.CancelHandle, "_attach", spy)
    service.start_workers()
    try:
        with anyio.fail_after(120):
            while not service.runner.pool._idle:  # réserve prête / reserve ready
                await anyio.sleep(0.05)
        long_text = SENSITIVE_TEXT * (service.config.max_text_chars // len(SENSITIVE_TEXT))
        finished: list[bool] = []

        async def client() -> None:
            await service.anonymize_text(long_text, AnonymizeOptions(), "dev")
            finished.append(True)

        # Le client part dès que son travailleur a reçu la requête (pas de pari sur la lenteur du moteur).
        # The client leaves as soon as its worker has the request (no bet on how slow the engine is).
        async with anyio.create_task_group() as group:
            group.start_soon(client)
            with anyio.fail_after(60):
                while not attached:
                    await anyio.sleep(0.001)
            group.cancel_scope.cancel()
        assert not finished, "terminé avant l'annulation / finished before the cancellation"
        assert len(attached) == 1
        with anyio.fail_after(10):
            while _alive(attached[0]):
                await anyio.sleep(0.05)
        assert service.scheduler.busy == 0 and service.scheduler.waiting == 0
        result = await service.anonymize_text(f"mail {EMAIL}", AnonymizeOptions(), "dev")
        assert result.text == "mail [EMAIL_1]"  # le service continue / the service carries on
    finally:
        service.stop_workers()
