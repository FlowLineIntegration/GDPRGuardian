"""Envoi hors bande : usage unique, durée de vie, isolement, pagination, effacement / out-of-band upload flow."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import anyio
import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, AUTH_B, EMAIL, KEY_A, NIR, SENSITIVE_TEXT, FakeClock

import gdprguardian.documents as documents
from gdprguardian.server import ServerConfig, create_app
from gdprguardian.server.clients import LOCAL_CLIENT, REQUEST, RequestContext
from gdprguardian.server.errors import UploadTimeout
from gdprguardian.server.limiter import Ticket
from gdprguardian.server.options import AnonymizeOptions
from gdprguardian.server.security import DEV_PRINCIPAL, ApiKeyAuthenticator, result_id
from gdprguardian.server.service import Service


def start_upload(client: TestClient, filename: str = "dossier.txt", headers: dict[str, str] = AUTH_A,
                 **options: Any) -> dict[str, Any]:
    response = client.post("/v1/uploads", headers=headers, json={"filename": filename, **options})
    assert response.status_code == 201, response.text
    return response.json()


def path_of(url: str) -> str:
    return url.removeprefix("http://testserver")


def test_complete_flow(client: TestClient, clock: FakeClock) -> None:
    ticket = start_upload(client, countries="FR")
    assert ticket["method"] == "PUT" and ticket["expires_in"] == 300
    assert ticket["upload_url"].startswith("http://testserver/v1/uploads/")
    assert ticket["upload_id"] not in ticket["upload_url"]
    receipt = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=SENSITIVE_TEXT.encode())
    # 202 dès le corps reçu ; le traitement suit en arrière-plan / 202 once received; processing follows.
    assert receipt.status_code == 202, receipt.text
    accepted = receipt.json()
    assert accepted["status"] == "processing" and accepted["stage"] == "queued"
    assert accepted["received_bytes"] == len(SENSITIVE_TEXT.encode()) and accepted["retry_after_s"] >= 1
    assert "result_url" not in accepted and accepted["upload_id"] == ticket["upload_id"]
    assert receipt.headers["retry-after"] == str(accepted["retry_after_s"])
    assert NIR not in receipt.text and EMAIL not in receipt.text  # métadonnées seulement / metadata only
    result = client.get(path_of(ticket["result_url"]), headers=AUTH_A).json()
    assert result["page"] == 1 and result["pages"] == 1 and result["next_page"] is None
    assert result["deleted"] is True and result["expires_in"] <= 120 and result["stage"] == "done"
    assert "document.txt" not in result["markdown"] and "[NIR_1]" in result["markdown"]
    assert NIR not in result["markdown"]
    assert result["report"]["entities"]["NIR"] == 1
    # Lu en entier : relisible pendant le délai de grâce, puis effacé / fully read: grace period, then deleted.
    assert client.get(path_of(ticket["result_url"]), headers=AUTH_A).status_code == 200
    clock.advance(121)
    gone = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert gone.status_code == 404 and gone.json()["error"]["code"] == "already_read"


def test_upload_url_is_single_use(client: TestClient) -> None:
    ticket = start_upload(client)
    url = path_of(ticket["upload_url"])
    assert client.put(url, headers=AUTH_A, content=b"premier").status_code == 202
    again = client.put(url, headers=AUTH_A, content=b"second")
    # Déjà utilisé, faux ou expiré : la même réponse, rien n'indique que le jeton a existé.
    # Already used, wrong or expired: the same answer, nothing tells that the token existed.
    wrong = client.put("/v1/uploads/" + "x" * 43, headers=AUTH_A, content=b"second")
    assert again.status_code == wrong.status_code == 404 and again.json() == wrong.json()


def test_upload_and_results_are_bound_to_the_principal(client: TestClient) -> None:
    ticket = start_upload(client)
    url = path_of(ticket["upload_url"])
    stolen = client.put(url, headers=AUTH_B, content=b"x")
    assert stolen.status_code == 404
    # La tentative d'un autre principal ne consomme pas le jeton / another principal does not burn the token.
    assert client.put(url, headers=AUTH_A, content=SENSITIVE_TEXT.encode()).status_code == 202
    result_url = path_of(ticket["result_url"])
    assert client.get(result_url, headers=AUTH_B).status_code == 404
    assert client.delete(result_url, headers=AUTH_B).status_code == 404
    assert client.get(result_url, headers=AUTH_A).status_code == 200


def test_pending_before_upload(client: TestClient) -> None:
    ticket = start_upload(client)
    response = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert response.status_code == 202
    assert response.json() == {"upload_id": ticket["upload_id"], "status": "pending", "expires_in": 300,
                               "stage": "awaiting_upload", "percent": 0, "pages_done": None, "pages_total": None,
                               "elapsed_s": None, "estimated_remaining_s": None, "retry_after_s": 5}
    assert response.headers["retry-after"] == "5"


def test_progress_while_processing(client: TestClient, clock: FakeClock) -> None:
    # Reçu, en attente d'un travailleur, puis converti : étape, pages et délai conseillé, jamais une donnée.
    # Received, queued, then converting: stage, pages and advised delay, never any data.
    store = client.app.state.service.store
    ticket = start_upload(client)
    principal = ApiKeyAuthenticator([KEY_A]).authenticate(AUTH_A["Authorization"])
    assert principal is not None
    token = path_of(ticket["upload_url"]).rsplit("/", 1)[-1]
    job = store.claim(token, principal)
    store.received(job, 5_000_000)
    queued = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert queued.status_code == 202 and queued.json()["stage"] == "queued" and queued.json()["percent"] == 0
    store.start(job)
    store.progress(job, "converting", 10, 40)
    clock.advance(3)
    converting = client.get(path_of(ticket["result_url"]), headers=AUTH_A).json()
    assert converting["stage"] == "converting" and (converting["pages_done"], converting["pages_total"]) == (10, 40)
    assert 5 < converting["percent"] < 65 and converting["elapsed_s"] == 3
    assert 2 <= converting["retry_after_s"] <= 5 and converting["estimated_remaining_s"] >= 1
    store.progress(job, "anonymising")
    store.progress(job, "nonsense", 1, 2)  # étape inconnue ignorée / unknown stage ignored
    anonymising = client.get(path_of(ticket["result_url"]), headers=AUTH_A).json()
    assert anonymising["stage"] == "anonymising" and anonymising["pages_total"] is None
    assert 65 <= anonymising["percent"] <= 99


def test_upload_token_ttl(make_client: Callable[..., TestClient], clock: FakeClock) -> None:
    client = make_client(upload_ttl_s=60)
    ticket = start_upload(client)
    clock.advance(61)
    assert client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x").status_code == 404
    assert client.get(path_of(ticket["result_url"]), headers=AUTH_A).status_code == 404


def test_result_ttl(make_client: Callable[..., TestClient], clock: FakeClock) -> None:
    client = make_client(result_ttl_s=120)
    ticket = start_upload(client)
    client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x" * 10)
    clock.advance(119)
    assert client.get(path_of(ticket["result_url"]), headers=AUTH_A, params={"page": 1}).status_code == 200
    second = start_upload(client)
    client.put(path_of(second["upload_url"]), headers=AUTH_A, content=b"y" * 10)
    clock.advance(121)
    assert client.get(path_of(second["result_url"]), headers=AUTH_A).status_code == 404
    assert client.app.state.service.store.stats() == {"jobs": 0, "stored_chars": 0}


def test_sweeper_deletes_expired_results_without_any_request(make_client: Callable[..., TestClient],
                                                            clock: FakeClock) -> None:
    client = make_client(sweep_interval_s=0.02)
    ticket = start_upload(client)
    client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=SENSITIVE_TEXT.encode())
    store = client.app.state.service.store
    assert len(store) == 1
    clock.advance(601)
    deadline = time.monotonic() + 5
    while len(store) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert len(store) == 0  # balayé sans aucune requête / swept without any request


def test_pagination_and_deletion_after_every_page(client: TestClient, clock: FakeClock) -> None:
    ticket = start_upload(client)
    body = "".join(f"Ligne {i} : contact {i}@exemple.fr\n" for i in range(3000))
    assert client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=body.encode()).status_code == 202
    url = path_of(ticket["result_url"])
    pages: list[str] = []
    page: int | None = 1
    while page is not None:
        data = client.get(url, headers=AUTH_A, params={"page": page, "page_chars": 20_000}).json()
        assert len(data["markdown"]) <= 20_000 and data["markdown"].endswith("\n")
        # Rapport et avertissements à chaque page / report and warnings on every page.
        assert data["report"] is not None and isinstance(data["warnings"], list)
        pages.append(data["markdown"])
        assert data["deleted"] == (data["next_page"] is None)
        page = data["next_page"]
    assert len(pages) > 1
    markdown = "".join(pages)
    assert markdown.count("\n") == 3000 and "@exemple.fr" not in markdown
    assert "[EMAIL_3000]" in markdown
    # Délai de grâce : une page perdue se relit, puis tout est effacé / grace period, then deleted.
    assert client.get(url, headers=AUTH_A, params={"page": 1, "page_chars": 20_000}).status_code == 200
    clock.advance(121)
    assert client.get(url, headers=AUTH_A).status_code == 404


def test_markdown_format(client: TestClient) -> None:
    ticket = start_upload(client)
    client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=SENSITIVE_TEXT.encode())
    response = client.get(path_of(ticket["result_url"]), headers=AUTH_A, params={"format": "markdown"})
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["x-gdprguardian-pages"] == "1" and response.headers["x-gdprguardian-deleted"] == "True"
    assert "[NIR_1]" in response.text and "document.txt" not in response.text and NIR not in response.text


@pytest.mark.parametrize("params", [{"page": 0}, {"page_chars": 10}, {"page_chars": 10**7}, {"format": "pdf"}])
def test_invalid_result_parameters(client: TestClient, params: dict[str, Any]) -> None:
    ticket = start_upload(client)
    assert client.get(path_of(ticket["result_url"]), headers=AUTH_A, params=params).status_code == 422


def test_page_out_of_range(client: TestClient) -> None:
    ticket = start_upload(client)
    client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x")
    response = client.get(path_of(ticket["result_url"]), headers=AUTH_A, params={"page": 9})
    assert response.status_code == 404 and response.json()["error"]["code"] == "page_not_found"


def test_explicit_delete(client: TestClient) -> None:
    ticket = start_upload(client)
    client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x")
    assert client.delete(path_of(ticket["result_url"]), headers=AUTH_A).status_code == 204
    assert client.get(path_of(ticket["result_url"]), headers=AUTH_A).status_code == 404


@pytest.mark.parametrize("token", ["short", "x" * 44, "%2e%2e%2fetc", "x" * 42 + "!"])
def test_malformed_tokens(client: TestClient, token: str) -> None:
    assert client.put(f"/v1/uploads/{token}", headers=AUTH_A, content=b"x").status_code == 404


def test_upload_size_limit_and_failure_report(make_client: Callable[..., TestClient], clock: FakeClock) -> None:
    client = make_client(max_upload_bytes=1024)
    ticket = start_upload(client)
    response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x" * 2048)
    assert response.status_code == 413
    # L'échec est signalé au lecteur du résultat, relisible pendant le délai de grâce, puis oublié.
    # The failure is reported to the reader, again during the grace period, then forgotten.
    failed = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert failed.status_code == 413
    assert client.get(path_of(ticket["result_url"]), headers=AUTH_A).status_code == 413
    clock.advance(121)
    gone = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert gone.status_code == 404 and gone.json()["error"]["code"] == "already_read"


def test_chunked_upload_over_limit(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_upload_bytes=1024)
    ticket = start_upload(client)
    response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A,
                          content=iter([b"x" * 600, b"x" * 600, b"x" * 600]))
    assert response.status_code == 413


def test_unsupported_format_is_reported(client: TestClient) -> None:
    ticket = start_upload(client, filename="scan.pdf")
    response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"%PDF-1.7")
    # Reçu (202) ; le refus du format arrive à la lecture / received (202); the refusal comes when reading.
    assert response.status_code == 202
    failed = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert failed.status_code == 415 and failed.json()["error"]["code"] == "unsupported_format"


@pytest.mark.parametrize("filename", ["photo.png", "archive.zip", "setup.exe", "film.mp4"])
def test_unconvertible_extensions_are_refused_before_the_upload(client: TestClient, filename: str) -> None:
    response = client.post("/v1/uploads", headers=AUTH_A, json={"filename": filename})
    assert response.status_code == 415 and response.json()["error"]["code"] == "unsupported_format"
    assert "PDF" in response.json()["error"]["message"] and "DOCX" in response.json()["error"]["message"]
    assert len(client.app.state.service.store) == 0


def test_quota_of_active_uploads(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_active_per_principal=2)
    start_upload(client)
    start_upload(client)
    response = client.post("/v1/uploads", headers=AUTH_A, json={"filename": "c.txt"})
    assert response.status_code == 429 and response.json()["error"]["code"] == "too_many_active_uploads"
    start_upload(client, headers=AUTH_B)


def test_public_url_is_used_for_links(make_client: Callable[..., TestClient]) -> None:
    ticket = start_upload(make_client(public_url="https://rgpd.example.eu"))
    assert ticket["upload_url"].startswith("https://rgpd.example.eu/v1/uploads/")
    assert ticket["result_url"].startswith("https://rgpd.example.eu/v1/results/up_")


def test_links_follow_the_declared_host_the_client_used(make_client: Callable[..., TestClient]) -> None:
    # Le client a joint api.gardienrgpd.fr : l'URL d'envoi reste sur ce domaine déclaré (même schéma que l'URL
    # publique) ; un hôte local ou non déclaré garde l'URL publique. The client used a declared host: the upload URL
    # stays on it; a loopback or undeclared host keeps the public URL.
    client = make_client(public_url="https://api.gdprguardian.com",
                         allowed_hosts=("api.gdprguardian.com", "api.gardienrgpd.fr", "*.example.eu"))
    french = start_upload(client, headers={**AUTH_A, "Host": "api.gardienrgpd.fr"})
    assert french["upload_url"].startswith("https://api.gardienrgpd.fr/v1/uploads/")
    assert french["result_url"].startswith("https://api.gardienrgpd.fr/v1/results/")
    local = start_upload(client, headers={**AUTH_A, "Host": "127.0.0.1:8000"})
    assert local["upload_url"].startswith("https://api.gdprguardian.com/v1/uploads/")
    pattern = start_upload(client, headers={**AUTH_A, "Host": "rgpd.example.eu"})  # motif, pas un nom exact
    assert pattern["upload_url"].startswith("https://api.gdprguardian.com/v1/uploads/")
    refused = client.post("/v1/uploads", headers={**AUTH_A, "Host": "evil.example"}, json={"filename": "a.txt"})
    assert refused.status_code == 421


@pytest.mark.parametrize("filename", ["/home/jdupont/clients/CV_Jean_Dupont.txt", ".txt", "TXT_jdupont.TXT"])
def test_file_name_is_never_kept(client: TestClient, filename: str) -> None:
    ticket = start_upload(client, filename=filename)
    principal = ApiKeyAuthenticator([KEY_A]).authenticate(AUTH_A["Authorization"])
    assert principal is not None
    job = client.app.state.service.store.get(ticket["upload_id"], principal)
    assert job.filename == "document.txt"  # même en mémoire / not even in memory
    client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x")
    markdown = client.get(path_of(ticket["result_url"]), headers=AUTH_A).json()["markdown"]
    assert markdown.strip() == "x" and "dupont" not in markdown.lower()


def test_oversized_single_chunk_is_reported_as_too_large(make_client: Callable[..., TestClient]) -> None:
    # Au-delà de la marge de l'intergiciel : l'échec enregistré reste « trop volumineux » / beyond the envelope.
    client = make_client(max_upload_bytes=1024)
    ticket = start_upload(client)
    response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=iter([b"x" * 200_000]))
    assert response.status_code == 413
    failed = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert failed.status_code == 413 and failed.json()["error"]["code"] == "payload_too_large"


def test_busy_service_keeps_the_upload_token(client: TestClient) -> None:
    ticket = start_upload(client)
    budget = client.app.state.service.budget
    assert budget.acquire("someone-else", budget.limit)
    try:
        busy = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x")
    finally:
        budget.release("someone-else", budget.limit)
    assert busy.status_code == 503 and int(busy.headers["retry-after"]) >= 1
    # Le jeton n'a pas été consommé : nouvel essai possible / the token was not burned: retry works.
    assert client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x").status_code == 202


@pytest.mark.anyio
async def test_slow_upload_is_cut_and_reported(clock: FakeClock) -> None:
    # Client trop lent (slowloris) : le corps est abandonné au bout de son délai (base + taille au débit minimal),
    # filet derrière l'intergiciel des corps. Slow body dropped after its deadline, behind the body middleware.
    service = Service(ServerConfig(dev_no_auth=True, max_upload_bytes=1024, body_base_s=0.05), clock=clock)
    job, token = service.create_upload(DEV_PRINCIPAL, "a.txt", AnonymizeOptions())

    async def slow() -> AsyncIterator[bytes]:
        yield b"x"
        await anyio.sleep(5)
        yield b"y"

    with pytest.raises(UploadTimeout):
        await service.receive_upload(token, DEV_PRINCIPAL, slow())
    with pytest.raises(UploadTimeout):
        service.read_result(DEV_PRINCIPAL, result_id(token), 1, None)  # échec signalé au lecteur / reported
    assert job.state.value == "failed"


async def _once(data: bytes) -> AsyncIterator[bytes]:
    yield data


async def _until(condition: Callable[[], bool]) -> None:
    with anyio.fail_after(5):
        while not condition():
            await anyio.sleep(0)


@pytest.mark.anyio
@pytest.mark.usefixtures("fake_documents")
async def test_time_queued_does_not_count_against_a_processed_upload(clock: FakeClock) -> None:
    # Une file profonde retient l'envoi bien au-delà de son délai de traitement : il aboutit quand même.
    # A deep queue holds the upload far beyond its processing delay: it still succeeds.
    service = Service(ServerConfig(dev_no_auth=True, max_concurrency=1, isolation=False, result_ttl_s=60,
                                   conversion_timeout_s=5), clock=clock)
    job, token = service.create_upload(DEV_PRINCIPAL, "a.txt", AnonymizeOptions())
    gate = anyio.Event()
    received: list[tuple[Any, Any]] = []

    async def other_key() -> None:
        async with service.scheduler.slot("someone-else"):
            await gate.wait()

    async def upload() -> None:
        received.append(await service.receive_upload(token, DEV_PRINCIPAL, _once(SENSITIVE_TEXT.encode())))

    async with anyio.create_task_group() as tasks:
        tasks.start_soon(other_key)
        await _until(lambda: service.scheduler.busy == 1)
        tasks.start_soon(upload)
        await _until(lambda: service.scheduler.waiting == 1)
        for _ in range(10):  # dix délais de traitement en file, balayeur compris / ten delays queued, sweeper too
            clock.advance(service.store._processing_ttl)
            service.store.purge()
        assert len(service.store) == 1
        gate.set()
    assert received and received[0][0] is job
    view = service.read_result(DEV_PRINCIPAL, result_id(token), 1, None)
    assert view.markdown is not None and "[NIR_1]" in view.markdown and NIR not in view.markdown


@pytest.mark.anyio
@pytest.mark.usefixtures("fake_documents")
async def test_processing_after_the_202_frees_the_body_place(clock: FakeClock,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    # Après le 202, la requête passe « en traitement » pour le limiteur (le suivi du même client n'est plus
    # refusé) ; le chemin synchrone (MCP local) ne change rien. After the 202 the request counts as "processing"
    # for the limiter (polling from the same client is no longer refused); the synchronous path changes nothing.
    service = Service(ServerConfig(dev_no_auth=True, isolation=False), clock=clock)
    marked: list[Any] = []
    monkeypatch.setattr(service.limiter, "mark_processing", marked.append)
    ticket = Ticket(LOCAL_CLIENT, 0.0, True, constrained=False, max_running=1, max_running_prefix=1)
    for raise_errors in (False, True):
        job, token = service.create_upload(DEV_PRINCIPAL, "a.txt", AnonymizeOptions())
        received, data = await service.accept_upload(token, DEV_PRINCIPAL, _once(SENSITIVE_TEXT.encode()))
        reset = REQUEST.set(RequestContext(client=LOCAL_CLIENT, ticket=ticket))
        try:
            await service.process_upload(received, data, DEV_PRINCIPAL, raise_errors=raise_errors)
        finally:
            REQUEST.reset(reset)
        assert job.state.value == "ready"
    assert marked == [ticket]


def test_real_conversion_of_a_text_file(clock: FakeClock) -> None:
    """Vraie façade documents (sans faux convertisseur) ; ignoré tant que `gdprguardian.convert` manque.

    Real documents facade (no fake converter); skipped while `gdprguardian.convert` is missing.
    """
    assert documents.anonymize_document.__module__ == "gdprguardian.documents"
    with TestClient(create_app(ServerConfig(api_keys=(KEY_A,)), clock=clock)) as client:
        ticket = start_upload(client, filename="notes.txt")
        response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=SENSITIVE_TEXT.encode())
        assert response.status_code == 202, response.text
        result = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
        if result.status_code == 501:
            pytest.skip("gdprguardian.convert indisponible / not available yet")
        markdown = result.json()["markdown"]
    assert NIR not in markdown and EMAIL not in markdown
