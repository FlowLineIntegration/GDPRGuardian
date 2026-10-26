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
from gdprguardian.server.errors import UploadTimeout
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


def test_complete_flow(client: TestClient) -> None:
    ticket = start_upload(client, countries="FR")
    assert ticket["method"] == "PUT" and ticket["expires_in"] == 300
    assert ticket["upload_url"].startswith("http://testserver/v1/uploads/")
    assert ticket["upload_id"] not in ticket["upload_url"]
    receipt = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=SENSITIVE_TEXT.encode())
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["status"] == "ready" and receipt.json()["pages"] == 1
    assert NIR not in receipt.text and EMAIL not in receipt.text  # métadonnées seulement / metadata only
    result = client.get(path_of(ticket["result_url"]), headers=AUTH_A).json()
    assert result["page"] == 1 and result["pages"] == 1 and result["next_page"] is None
    assert result["deleted"] is True
    assert "document.txt" not in result["markdown"] and "[NIR_1]" in result["markdown"]
    assert NIR not in result["markdown"]
    assert result["report"]["entities"]["NIR"] == 1
    # Lu en entier, donc effacé / fully read, hence deleted.
    assert client.get(path_of(ticket["result_url"]), headers=AUTH_A).status_code == 404


def test_upload_url_is_single_use(client: TestClient) -> None:
    ticket = start_upload(client)
    url = path_of(ticket["upload_url"])
    assert client.put(url, headers=AUTH_A, content=b"premier").status_code == 200
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
    assert client.put(url, headers=AUTH_A, content=SENSITIVE_TEXT.encode()).status_code == 200
    result_url = path_of(ticket["result_url"])
    assert client.get(result_url, headers=AUTH_B).status_code == 404
    assert client.delete(result_url, headers=AUTH_B).status_code == 404
    assert client.get(result_url, headers=AUTH_A).status_code == 200


def test_pending_before_upload(client: TestClient) -> None:
    ticket = start_upload(client)
    response = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert response.status_code == 202
    assert response.json() == {"upload_id": ticket["upload_id"], "status": "pending", "expires_in": 300}
    assert response.headers["retry-after"] == "1"


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


def test_pagination_and_deletion_after_every_page(client: TestClient) -> None:
    ticket = start_upload(client)
    body = "".join(f"Ligne {i} : contact {i}@exemple.fr\n" for i in range(3000))
    receipt = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=body.encode()).json()
    assert receipt["pages"] > 1
    url = path_of(ticket["result_url"])
    pages: list[str] = []
    page: int | None = 1
    while page is not None:
        data = client.get(url, headers=AUTH_A, params={"page": page, "page_chars": 20_000}).json()
        assert len(data["markdown"]) <= 20_000 and data["markdown"].endswith("\n")
        assert (data["report"] is not None) == (page == 1)
        pages.append(data["markdown"])
        assert data["deleted"] == (data["next_page"] is None)
        page = data["next_page"]
    markdown = "".join(pages)
    assert markdown.count("\n") == 3000 and "@exemple.fr" not in markdown
    assert "[EMAIL_3000]" in markdown
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


def test_upload_size_limit_and_failure_report(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_upload_bytes=1024)
    ticket = start_upload(client)
    response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x" * 2048)
    assert response.status_code == 413
    # L'échec est signalé une fois au lecteur du résultat / the failure is reported once to the reader.
    failed = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert failed.status_code == 413
    assert client.get(path_of(ticket["result_url"]), headers=AUTH_A).status_code == 404


def test_chunked_upload_over_limit(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_upload_bytes=1024)
    ticket = start_upload(client)
    response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A,
                          content=iter([b"x" * 600, b"x" * 600, b"x" * 600]))
    assert response.status_code == 413


def test_unsupported_format_is_reported(client: TestClient) -> None:
    ticket = start_upload(client, filename="scan.pdf")
    response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"%PDF-1.7")
    assert response.status_code == 415
    failed = client.get(path_of(ticket["result_url"]), headers=AUTH_A)
    assert failed.status_code == 415 and failed.json()["error"]["code"] == "unsupported_format"


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
    assert client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=b"x").status_code == 200


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


def test_real_conversion_of_a_text_file(clock: FakeClock) -> None:
    """Vraie façade documents (sans faux convertisseur) ; ignoré tant que `gdprguardian.convert` manque.

    Real documents facade (no fake converter); skipped while `gdprguardian.convert` is missing.
    """
    assert documents.anonymize_document.__module__ == "gdprguardian.documents"
    with TestClient(create_app(ServerConfig(api_keys=(KEY_A,)), clock=clock)) as client:
        ticket = start_upload(client, filename="notes.txt")
        response = client.put(path_of(ticket["upload_url"]), headers=AUTH_A, content=SENSITIVE_TEXT.encode())
        if response.status_code == 501:
            pytest.skip("gdprguardian.convert indisponible / not available yet")
        assert response.status_code == 200, response.text
        markdown = client.get(path_of(ticket["result_url"]), headers=AUTH_A).json()["markdown"]
    assert NIR not in markdown and EMAIL not in markdown
