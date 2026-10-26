"""Service public face aux abus : corps lents, rotation d'adresses, envois en attente, dépôt, pages tierces, sorties.

Public service under abuse: slow bodies, address rotation, pending uploads, store, third-party pages, outputs. Chaque
test rejoue une attaque de la revue adverse contre l'application réelle (horloge pilotée, travailleurs dans ce
processus). Each test replays an attack from the adversarial review against the real application.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import anyio
import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, CLIENT_HEADER, KEY_A, MCP_HEADERS, NIR, PUBLIC, SENSITIVE_TEXT, FakeClock, from_ip
from starlette.types import ASGIApp, Message

from gdprguardian.server import ServerConfig, create_app
from gdprguardian.server import middleware as middleware_module
from gdprguardian.server.limiter import LimitPolicy, Ticket

MB = 2**20
ALICE = from_ip("203.0.113.7")
BOB = from_ip("198.51.100.23")
LOCAL_TOKEN = "e" * 64


def path_of(url: str) -> str:
    return url.removeprefix("http://testserver")


def scope_for(method: str, path: str, headers: dict[str, str]) -> dict[str, Any]:
    return {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "scheme": "http",
            "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
            "headers": [(b"host", b"testserver"), *((k.lower().encode(), v.encode()) for k, v in headers.items())],
            "client": None, "server": ("testserver", 80)}


class Exchange:
    """Une requête ASGI dont le corps arrive au rythme voulu / an ASGI request whose body arrives at will."""

    def __init__(self, first: bytes = b"", *, then_wait: bool = True) -> None:
        self._pending = [{"type": "http.request", "body": first, "more_body": then_wait}]
        self.status = 0
        self.headers: dict[bytes, bytes] = {}
        self.body = b""

    async def receive(self) -> Message:
        if self._pending:
            return self._pending.pop()
        await anyio.sleep_forever()  # le client goutte, ou se tait / the client trickles, or stays silent
        raise AssertionError

    async def send(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            self.status = message["status"]
            self.headers = dict(message["headers"])
        elif message["type"] == "http.response.body":
            self.body += message.get("body", b"")

    async def run(self, app: ASGIApp, method: str, path: str, headers: dict[str, str]) -> None:
        await app(scope_for(method, path, headers), self.receive, self.send)


async def _until(condition: Callable[[], bool]) -> None:
    with anyio.fail_after(10):
        while not condition():
            await anyio.sleep(0.01)


def public_app(clock: FakeClock | None = None, **settings: Any) -> ASGIApp:
    return create_app(ServerConfig(**PUBLIC, isolation=False, **settings), clock=clock or FakeClock())


async def with_lifespan(app: Any, body: Callable[[], Awaitable[None]]) -> None:
    async with app.router.lifespan_context(app):
        await body()


# --- corps lents (B1) / slow bodies --------------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(("path", "content_type"), [
    ("/v1/anonymize/text", "application/json"), ("/v1/detect", "application/json"),
    ("/v1/uploads", "application/json"), ("/mcp", "application/json"),
    ("/v1/anonymize/file", "multipart/form-data; boundary=x"),
])
async def test_a_trickling_body_is_cut_with_408_on_every_route(path: str, content_type: str) -> None:
    # Un octet toutes les 14 s passe le délai de Nginx entre deux lectures : le service coupe le corps entier à
    # base + taille / débit minimal (408, connexion fermée), et rend sa mémoire. One byte every 14 s passes Nginx's
    # between-reads timeout: the service cuts the whole body at base + size / minimal rate, and frees its memory.
    app: Any = public_app(body_base_s=0.3)
    service = app.state.service
    first = (b'--x\r\nContent-Disposition: form-data; name="file"; filename="a.txt"\r\n\r\nJean'
             if content_type.startswith("multipart/") else b'{"text": "')

    async def body() -> None:
        exchange = Exchange(first)
        headers = {**ALICE, "content-type": content_type, "content-length": "1000",
                   **({"accept": MCP_HEADERS["Accept"]} if path == "/mcp" else {})}
        with anyio.fail_after(10):
            await exchange.run(app, "POST", path, headers)
        assert exchange.status == 408 and exchange.headers[b"connection"] == b"close"
        assert json.loads(exchange.body)["error"]["code"] == "upload_timeout"
        assert service.budget.used == 0 and service.limiter.stats()["in_flight"] == 0

    await with_lifespan(app, body)


@pytest.mark.anyio
async def test_slow_upload_tickets_are_budgeted_and_counted_in_flight() -> None:
    # P6 : 16 POST /v1/uploads lents d'une seule IPv4 tenaient 128 Mio hors budget ; désormais 3 en vol au plus,
    # dans le budget, 256 Kio chacun au plus. 16 slow POST /v1/uploads from one IPv4 held 128 MiB outside the budget;
    # now 3 in flight at most, within the budget, 256 KiB each at most.
    app: Any = public_app()
    service = app.state.service
    middleware_module._DRAIN_S, drain = 0.05, middleware_module._DRAIN_S
    exchanges = [Exchange(b" " * 1000) for _ in range(16)]
    headers = {**ALICE, "content-type": "application/json", "content-length": str(200_000)}
    try:
        async def body() -> None:
            async with anyio.create_task_group() as tasks:
                for exchange in exchanges:
                    tasks.start_soon(exchange.run, app, "POST", "/v1/uploads", headers)
                await _until(lambda: sum(e.status == 429 for e in exchanges) == 13)
                assert service.limiter.stats()["in_flight"] == 3 and service.budget.used == 3 * 200_000
                too_big = Exchange(b"", then_wait=False)
                await too_big.run(app, "POST", "/v1/uploads", {**BOB, "content-type": "application/json",
                                                                 "content-length": str(8 * MB)})
                assert too_big.status == 413  # un jeu de règles tient en 256 Kio / a rule set fits in 256 KiB
                tasks.cancel_scope.cancel()

        await with_lifespan(app, body)
    finally:
        middleware_module._DRAIN_S = drain


@pytest.mark.anyio
async def test_rotating_64s_of_one_48_cannot_hold_the_memory_budget() -> None:
    # P4 : 128 /64 d'un /48 tenaient tout le budget avec des corps lents de 8 Mio ; désormais 12 en vol par préfixe,
    # et l'équité du budget suit le préfixe : la réserve reste aux autres. 128 /64s of one /48 held the whole budget;
    # now 12 in flight per prefix, and budget fairness follows the prefix: the reserve stays for the others.
    app: Any = public_app(queue_bytes=32 * MB, max_upload_bytes=MB)
    service = app.state.service
    middleware_module._DRAIN_S, drain = 0.05, middleware_module._DRAIN_S
    attackers = [Exchange(b"{") for _ in range(128)]
    try:
        async def body() -> None:
            async with anyio.create_task_group() as tasks:
                for index, exchange in enumerate(attackers):
                    tasks.start_soon(exchange.run, app, "POST", "/v1/anonymize/text",
                                     {CLIENT_HEADER: f"2001:db8:bb:{index:x}::1", "content-type": "application/json",
                                      "content-length": str(4 * MB)})
                await _until(lambda: sum(e.status in (429, 503) for e in attackers) >= 128 - 12)
                held = service.budget.used
                assert held <= service.budget.limit - service.budget.reserve and service.limiter.stats()[
                    "in_flight"] <= 12
                legit = Exchange(json.dumps({"text": SENSITIVE_TEXT}).encode(), then_wait=False)
                await legit.run(app, "POST", "/v1/anonymize/text",
                                {**BOB, "content-type": "application/json",
                                 "content-length": str(len(json.dumps({"text": SENSITIVE_TEXT})))})
                assert legit.status == 200 and NIR not in legit.body.decode()
                tasks.cancel_scope.cancel()

        await with_lifespan(app, body)
    finally:
        middleware_module._DRAIN_S = drain
    assert service.budget.used == 0


# --- envois en attente, dépôt (M1, M5, B2) / pending uploads, store ------------------------------------------------


def test_pending_uploads_of_one_48_leave_room_for_everyone(make_client: Callable[..., TestClient],
                                                          clock: FakeClock) -> None:
    # P2 : 100 /64 × 10 envois d'un /48 remplissaient les 1 000 places ; désormais 40 par préfixe.
    # 100 /64s × 10 uploads from one /48 filled the 1,000 places; now 40 per prefix.
    client = make_client(**PUBLIC)
    statuses: dict[int, int] = {}
    for net in range(100):
        for _ in range(10):
            response = client.post("/v1/uploads", headers=from_ip(f"2001:db8:aa:{net:x}::1"), json={"filename": "a"})
            statuses[response.status_code] = statuses.get(response.status_code, 0) + 1
            clock.advance(0.03)
    assert statuses.get(201, 0) == 40 and set(statuses) <= {201, 429}
    assert client.post("/v1/uploads", headers=BOB, json={"filename": "a.txt"}).status_code == 201


def test_one_client_cannot_fill_the_result_store(make_client: Callable[..., TestClient]) -> None:
    # P7 : un résultat de 999 996 caractères faisait échouer l'envoi de 11 octets d'une victime ; désormais un
    # résultat ne dépasse pas 1/8 du dépôt (413 dans le travailleur) et un client n'en tient pas plus.
    # A 999,996-character result made a victim's 11-byte upload fail; now a result never exceeds 1/8 of the store
    # (413 in the worker) and one client holds no more.
    client = make_client(**PUBLIC, max_store_chars=1_000_000)
    service = client.app.state.service
    huge = client.post("/v1/uploads", headers=ALICE, json={"filename": "a.txt"}).json()
    # Reçu (202), refusé au traitement : l'échec attend le lecteur / received, refused when processed.
    assert client.put(path_of(huge["upload_url"]), headers=ALICE, content=b"x " * 499_990).status_code == 202
    assert client.get(path_of(huge["result_url"]), headers=ALICE).status_code == 413
    kept = client.post("/v1/uploads", headers=ALICE, json={"filename": "a.txt"}).json()
    assert client.put(path_of(kept["upload_url"]), headers=ALICE, content=b"x" * 120_000).status_code == 202
    created = client.post("/v1/uploads", headers=ALICE, json={"filename": "a.txt"})
    assert created.status_code == 201, created.text
    second = created.json()
    assert client.put(path_of(second["upload_url"]), headers=ALICE, content=b"y" * 120_000).status_code == 202
    refused = client.get(path_of(second["result_url"]), headers=ALICE)
    assert refused.status_code == 429 and refused.json()["error"]["code"] == "too_many_unread_results"
    victim = client.post("/v1/uploads", headers=BOB, json={"filename": "a.txt"}).json()
    response = client.put(path_of(victim["upload_url"]), headers=BOB, content=b"Jean Dupont")
    assert response.status_code == 202 and service.store.stats()["stored_chars"] < 125_000 + 100
    assert client.get(path_of(victim["result_url"]), headers=BOB).status_code == 200


def test_a_shared_connector_does_not_share_its_quota_with_its_users(make_client: Callable[..., TestClient]) -> None:
    # Connecteur MCP distant (une adresse pour tous) : les envois reçus comptent pour la machine qui envoie (PUT).
    # Remote MCP connector (one address for all): received uploads count against the sending machine (PUT).
    client = make_client(**PUBLIC, max_active_per_principal=2)
    connector = from_ip("160.79.104.10")
    tickets = [client.post("/mcp", headers={**MCP_HEADERS, **connector}, json={
        "jsonrpc": "2.0", "id": n, "method": "tools/call",
        "params": {"name": "create_upload", "arguments": {"filename": "a.txt"}}}).json()["result"]["structuredContent"]
        for n in range(6)]
    users = [from_ip(f"192.0.2.{n}") for n in range(1, 4)]
    for ticket, user in zip(tickets, users * 2, strict=True):
        response = client.put(path_of(ticket["upload_url"]), headers=user, content=SENSITIVE_TEXT.encode())
        assert response.status_code == 202


# --- pages tierces (M4) / third-party pages ------------------------------------------------------------------------


@pytest.mark.parametrize(("site", "expected"), [("cross-site", 403), ("same-site", 403), ("same-origin", 200),
                                                ("none", 200), (None, 200)])
def test_other_sites_cannot_make_their_visitors_use_the_service(make_client: Callable[..., TestClient],
                                                               site: str | None, expected: int) -> None:
    # P8 : un formulaire multipart d'une autre page passe sans contrôle CORS préalable ; refusé avant tout compte.
    # A multipart form from another page needs no CORS preflight; refused before anything is counted.
    client = make_client(**PUBLIC)
    limiter = client.app.state.service.limiter
    before = limiter.stats()["accepted"]
    headers = {**ALICE, **({"Sec-Fetch-Site": site} if site else {}), "Origin": "https://evil.example"}
    response = client.post("/v1/anonymize/file", headers=headers,
                           files={"file": ("a.txt", SENSITIVE_TEXT.encode(), "text/plain")})
    assert response.status_code == expected
    if expected == 403:
        assert response.json()["error"]["code"] == "cross_site_request"
        assert limiter.stats()["accepted"] == before and response.headers["cache-control"] == "no-store"


# --- sorties des travailleurs (B2) / worker outputs ----------------------------------------------------------------


def test_results_longer_than_the_output_cap_never_reach_the_main_process(
        make_client: Callable[..., TestClient]) -> None:
    client = make_client(**PUBLIC, max_store_chars=80_000)  # plafond : 10 000 caractères / cap: 10,000 characters
    assert client.app.state.service.config.max_output_chars == 10_000
    text = client.post("/v1/anonymize/text", headers=ALICE, json={"text": "a" * 20_000})
    assert text.status_code == 413 and text.json()["error"]["code"] == "payload_too_large"
    document = client.post("/v1/anonymize/file", headers=BOB, files={"file": ("a.txt", b"b" * 20_000, "text/plain")})
    assert document.status_code == 413 and document.json()["error"]["code"] == "document_too_large"
    assert client.post("/v1/anonymize/text", headers=ALICE, json={"text": "a" * 5_000}).status_code == 200


def test_worker_output_is_reserved_in_the_memory_budget(make_client: Callable[..., TestClient],
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(**PUBLIC)
    service = client.app.state.service
    seen: list[int] = []
    run = service.runner.run

    def recording(*args: Any) -> Any:
        seen.append(service.budget.used)
        return run(*args)

    monkeypatch.setattr(service.runner, "run", recording)
    assert client.post("/v1/anonymize/text", headers=ALICE, json={"text": SENSITIVE_TEXT}).status_code == 200
    # Pendant le travail : le corps et deux réponses maximales ; ensuite, plus rien / during the work: body and two
    # maximal replies; afterwards, nothing.
    assert seen and seen[0] > 2 * 4 * 64 * 1024 and service.budget.used == 0


def test_a_budget_too_full_for_the_output_answers_503_and_refunds(make_client: Callable[..., TestClient],
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(**PUBLIC, queue_bytes=8 * MB + 65_536, max_upload_bytes=MB)
    service = client.app.state.service
    finished: list[Ticket] = []
    finish = service.limiter.finish
    monkeypatch.setattr(service.limiter, "finish", lambda ticket: (finished.append(ticket), finish(ticket)))
    assert service.budget.acquire("someone-else", 7 * MB)
    try:
        response = client.post("/v1/anonymize/text", headers=ALICE, json={"text": SENSITIVE_TEXT})
    finally:
        service.budget.release("someone-else", 7 * MB)
    assert response.status_code == 503 and int(response.headers["retry-after"]) >= 1
    ticket = finished[-1]
    assert ticket.waived and not ticket.worked and service.budget.used == 0  # rien n'est dû / nothing is due


def test_a_put_refused_for_its_output_keeps_its_upload_url(make_client: Callable[..., TestClient]) -> None:
    # La sortie est réservée avant de consommer le jeton : 503, puis le même PUT réussit.
    # The output is reserved before burning the token: 503, then the same PUT succeeds.
    # Budget de 32 Mio, réserve de 8 ; sortie réservée : 2 × (4 × 500 000 + 1 Mio) = 6 Mio.
    # 32 MiB budget, 8 MiB reserve; output reserved: 2 × (4 × 500,000 + 1 MiB) = 6 MiB.
    client = make_client(**PUBLIC, queue_bytes=32 * MB, max_upload_bytes=MB, max_store_chars=4_000_000)
    service = client.app.state.service
    ticket = client.post("/v1/uploads", headers=ALICE, json={"filename": "a.txt"}).json()
    assert service.budget.acquire("someone-else", 27 * MB)
    try:
        busy = client.put(path_of(ticket["upload_url"]), headers=ALICE, content=SENSITIVE_TEXT.encode())
    finally:
        service.budget.release("someone-else", 27 * MB)
    assert busy.status_code == 503 and int(busy.headers["retry-after"]) >= 1
    retry = client.put(path_of(ticket["upload_url"]), headers=ALICE, content=SENSITIVE_TEXT.encode())
    assert retry.status_code == 202 and service.budget.used == 0


# --- divers / misc -------------------------------------------------------------------------------------------------


def test_unauthenticated_mcp_calls_of_a_keyed_service_use_the_network_client(
        make_client: Callable[..., TestClient]) -> None:
    # Avant : un seul seau « anonymous » ; un client le vidait et les 401 des autres devenaient 429.
    # Before: one shared "anonymous" bucket; one client drained it and the others' 401 became 429.
    client = make_client(client_ip_header=CLIENT_HEADER, limits=LimitPolicy(cheap_burst=3, cheap_rate=0.01))
    initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}
    codes = [client.post("/mcp", headers={**MCP_HEADERS, **ALICE}, json=initialize).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    assert client.post("/mcp", headers={**MCP_HEADERS, **BOB}, json=initialize).status_code == 401
    assert client.post("/mcp", headers={**MCP_HEADERS, **BOB, **AUTH_A}, json=initialize).status_code == 200


def test_the_deep_health_probe_is_for_the_server_itself(make_client: Callable[..., TestClient]) -> None:
    open_service = make_client(**PUBLIC)
    assert open_service.get("/health/deep").json() == {"status": "ok", "version": open_service.get("/health").json()[
        "version"]}
    hidden = open_service.get("/health/deep", headers=ALICE)
    assert hidden.status_code == 404 and hidden.json() == open_service.get("/nowhere", headers=ALICE).json()
    guarded = make_client(**PUBLIC, local_token_sha256=hashlib.sha256(LOCAL_TOKEN.encode()).hexdigest())
    assert guarded.get("/health/deep").status_code == 404  # sans jeton : pas le serveur / no token: not the server
    assert guarded.get("/health/deep", headers={"X-GG-Local": LOCAL_TOKEN}).status_code == 200


def test_the_deep_health_probe_reports_a_broken_worker_pool(make_client: Callable[..., TestClient],
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(**PUBLIC)

    def broken(*_args: object) -> None:
        raise OSError("fork")

    monkeypatch.setattr(client.app.state.service.runner, "run", broken)
    assert client.get("/health").status_code == 200  # la boucle répond / the event loop answers
    failed = client.get("/health/deep")
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "service_busy"


def test_no_activity_is_logged_below_warning(make_client: Callable[..., TestClient],
                                             caplog: pytest.LogCaptureFixture) -> None:
    # Décision : aucun journal d'accès ni d'activité ; au niveau de production (warning), rien par requête.
    # Decision: no access or activity log; at the production level (warning), nothing per request.
    client = make_client(**PUBLIC, local_token_sha256=None)
    caplog.set_level(logging.INFO, logger="gdprguardian.server")
    caplog.clear()
    client.post("/v1/anonymize/text", headers=ALICE, json={"text": SENSITIVE_TEXT})
    client.post("/v1/anonymize/file", headers=ALICE, files={"file": ("a.txt", b"x", "text/plain")})
    ticket = client.post("/v1/uploads", headers=ALICE, json={"filename": "a.txt"}).json()
    client.put(path_of(ticket["upload_url"]), headers=ALICE, content=SENSITIVE_TEXT.encode())
    client.get(path_of(ticket["result_url"]), headers=ALICE)
    client.get("/v1/results/up_" + "z" * 43, headers=BOB)
    assert [record for record in caplog.records if record.name.startswith("gdprguardian")] == []


def test_a_keyless_client_never_sees_the_api_key_of_another(make_client: Callable[..., TestClient]) -> None:
    # Garde-fou : le service public n'expose jamais KEY_A dans une réponse / the public service never echoes KEY_A.
    client = make_client(**PUBLIC)
    response = client.post("/v1/anonymize/text", headers={**ALICE, **AUTH_A}, json={"text": "x"})
    assert response.status_code == 200 and KEY_A not in response.text
