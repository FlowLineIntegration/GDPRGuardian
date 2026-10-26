"""Service public sans clé : identité par adresse, limites, isolation des résultats, en-têtes, cockpit.

Keyless public service: identity by address, limits, result isolation, headers, cockpit contract.
"""

from __future__ import annotations

import json
import logging
import secrets
from collections.abc import Callable, Mapping
from typing import Any, Protocol

import anyio
import pytest
from fastapi.testclient import TestClient
from server_testkit import (
    AUTH_A,
    CLIENT_HEADER,
    KEY_A_SHA256,
    MCP_HEADERS,
    NIR,
    PUBLIC,
    SENSITIVE_TEXT,
    from_ip,
    mcp_call,
)
from starlette.types import ASGIApp, Message

from gdprguardian.server import ServerConfig, create_app
from gdprguardian.server.limiter import LimitPolicy

ALICE = from_ip("203.0.113.7")
BOB = from_ip("198.51.100.23")
INITIALIZE = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "test", "version": "1"}}}


@pytest.fixture
def public(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client(**PUBLIC)


class HasHeaders(Protocol):
    headers: Mapping[str, str]


def path_of(url: str) -> str:
    return url.removeprefix("http://testserver")


def no_store(response: HasHeaders) -> bool:
    return response.headers.get("cache-control") == "no-store"


async def asgi_post(app: ASGIApp, path: str, headers: dict[str, str], payload: dict[str, Any]
                    ) -> tuple[int, dict[str, str], dict[str, Any]]:
    """Requête ASGI directe, sans client HTTP tiers / direct ASGI request, no third-party HTTP client."""
    body = json.dumps(payload).encode()
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http",
             "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
             "headers": [(b"host", b"testserver"), (b"content-type", b"application/json"),
                         (b"content-length", str(len(body)).encode()),
                         *((name.lower().encode(), value.encode()) for name, value in headers.items())],
             "client": ("127.0.0.1", 50000), "server": ("testserver", 80)}
    pending = [{"type": "http.request", "body": body, "more_body": False}]
    sent: list[Message] = []

    async def receive() -> Message:
        if pending:
            return pending.pop()
        await anyio.sleep_forever()  # le client reste connecté / the client stays connected
        raise AssertionError

    async def send(message: Message) -> None:
        sent.append(message)

    await app(scope, receive, send)
    start = next(message for message in sent if message["type"] == "http.response.start")
    content = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    return (start["status"], {name.decode(): value.decode() for name, value in start["headers"]},
            json.loads(content))


# --- sans clé / keyless ------------------------------------------------------------------------------------------


def test_rest_and_mcp_answer_without_any_key(public: TestClient) -> None:
    text = public.post("/v1/anonymize/text", headers=ALICE, json={"text": SENSITIVE_TEXT})
    assert text.status_code == 200 and "[NIR_1]" in text.json()["text"] and NIR not in text.text
    upload = public.post("/v1/anonymize/file", headers=ALICE,
                         files={"file": ("dossier.txt", SENSITIVE_TEXT.encode(), "text/plain")})
    assert upload.status_code == 200 and NIR not in upload.text
    assert public.get("/v1/packs", headers=ALICE).status_code == 200
    initialize = public.post("/mcp", headers={**MCP_HEADERS, **ALICE}, json=INITIALIZE)
    assert initialize.status_code == 200 and initialize.json()["result"]["serverInfo"]["name"] == "gdprguardian"
    tools = public.post("/mcp", headers={**MCP_HEADERS, **ALICE}, json={"jsonrpc": "2.0", "id": 2,
                                                                        "method": "tools/list"})
    assert {tool["name"] for tool in tools.json()["result"]["tools"]} >= {"create_upload", "anonymize_text"}
    result = public.post("/mcp", headers={**MCP_HEADERS, **ALICE},
                         json=mcp_call("anonymize_text", {"text": "mail jean.dupont@exemple.fr"})).json()["result"]
    assert result["content"][0]["text"] == "mail [EMAIL_1]"


def test_an_old_key_header_is_simply_ignored(public: TestClient) -> None:
    # Les clients configurés avant le service public envoient encore leur clé : rien ne casse.
    # Clients set up before the public service still send their key: nothing breaks.
    response = public.post("/v1/anonymize/text", headers={**ALICE, **AUTH_A}, json={"text": "x"})
    assert response.status_code == 200


def test_upload_commands_need_no_key(public: TestClient) -> None:
    ticket = public.post("/mcp", headers={**MCP_HEADERS, **ALICE},
                         json=mcp_call("create_upload", {"filename": "a.txt"})).json()["result"]["structuredContent"]
    assert all("Authorization" not in command for command in ticket["commands"].values())


# --- limites par client / per-client limits ---------------------------------------------------------------------


def test_each_client_has_its_own_budget(make_client: Callable[..., TestClient]) -> None:
    client = make_client(**PUBLIC, limits=LimitPolicy(cheap_burst=3, cheap_rate=0.01))
    assert [client.get("/v1/packs", headers=ALICE).status_code for _ in range(4)] == [200, 200, 200, 429]
    assert client.get("/v1/packs", headers=BOB).status_code == 200
    # Même /64 IPv6 : même client, quelle que soit l'adresse / same IPv6 /64: same client, whatever the address.
    v6 = [client.get("/v1/packs", headers=from_ip(f"2001:db8:5:6::{n:x}")).status_code for n in range(1, 5)]
    assert v6 == [200, 200, 200, 429]


def test_limited_answers_are_closed_json_with_retry_after(make_client: Callable[..., TestClient]) -> None:
    client = make_client(**PUBLIC, limits=LimitPolicy(cost_burst=0.006, cost_rate=0.001))
    assert client.post("/v1/anonymize/text", headers=ALICE, json={"text": "x"}).status_code == 200
    limited = client.post("/v1/anonymize/text", headers={**ALICE, "Content-Type": "application/json"},
                          content=b'{"text": "' + NIR.encode())  # jamais lu / never read
    assert limited.status_code == 429 and limited.json() == {"error": {
        "code": "rate_limited", "message": "Trop de requêtes, réessayez après Retry-After / too many requests, retry "
                                           "after Retry-After"}}
    assert int(limited.headers["retry-after"]) >= 1
    assert limited.headers["ratelimit-policy"].startswith('"cpu";q=6;qu="worker-ms"')
    assert no_store(limited) and NIR not in limited.text


def test_shedding_answers_503_before_reading_the_body(public: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    service = public.app.state.service
    monkeypatch.setattr(service.limiter, "_estimated_wait", lambda _principal, _small: 42.0)
    busy = public.post("/v1/anonymize/text", headers=ALICE, json={"text": SENSITIVE_TEXT})
    assert busy.status_code == 503 and busy.json()["error"]["code"] == "service_busy"
    assert 32 <= int(busy.headers["retry-after"]) <= 39 and no_store(busy)
    assert public.get("/v1/packs", headers=ALICE).status_code == 200  # sans contenu, pas délesté / not shed
    assert public.get("/status").json()["counters"]["shed"] == 1


def test_requests_from_the_server_itself_are_exempt(make_client: Callable[..., TestClient]) -> None:
    client = make_client(**PUBLIC, limits=LimitPolicy(cheap_burst=1, cheap_rate=0.001))
    assert all(client.get("/health").status_code == 200 for _ in range(50))  # sonde locale / local probe
    local = client.post("/v1/anonymize/text", json={"text": "x"})
    assert local.status_code == 200 and "ratelimit" not in local.headers
    assert client.get("/health", headers=ALICE).status_code == 200
    assert client.get("/health", headers=ALICE).status_code == 429


def test_successful_answers_advertise_the_remaining_budget(public: TestClient) -> None:
    response = public.post("/v1/anonymize/text", headers=ALICE, json={"text": "x"})
    assert response.headers["ratelimit-policy"] == '"cpu";q=20000;qu="worker-ms";w=40'
    assert response.headers["ratelimit"].startswith('"cpu";r=199')


# --- aucune adresse ne ressort / no address ever comes back ------------------------------------------------------


def test_the_client_address_never_comes_back(public: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    address = "203.0.113.77"
    responses = [
        public.post("/v1/anonymize/text", headers=from_ip(address), json={"text": "x"}),
        public.post("/v1/uploads", headers=from_ip(address), json={"filename": "a.txt"}),
        public.get("/v1/results/up_" + "z" * 43, headers=from_ip(address)),
        public.post("/mcp", headers={**MCP_HEADERS, **from_ip(address)}, json=INITIALIZE),
        public.get("/status", headers=from_ip(address)),
    ]
    for response in responses:
        assert address not in response.text and address not in str(response.headers)
    assert address not in caplog.text and "203.0.113" not in caplog.text


def test_status_shows_aggregates_only(public: TestClient) -> None:
    public.post("/v1/anonymize/text", headers=ALICE, json={"text": "x"})
    status = public.get("/status", headers=BOB).json()
    assert status["public"] is True and status["limits"] == "enforce" and status["version"]
    assert set(status["workers"]) == {"slots", "reserved_small", "busy", "waiting"}
    assert status["counters"]["accepted"] >= 1 and status["counters"]["tracked_clients"] >= 1
    assert "c_" not in str(status)  # aucun pseudonyme / no pseudonym


# --- isolation des résultats / result isolation ------------------------------------------------------------------


def test_deferred_results_are_reachable_through_their_capability_only(public: TestClient) -> None:
    tickets = {}
    for name, who in (("alice", ALICE), ("bob", BOB)):
        ticket = public.post("/v1/uploads", headers=who, json={"filename": "a.txt"}).json()
        put = public.put(path_of(ticket["upload_url"]), headers=who, content=f"{name} {NIR}".encode())
        assert put.status_code == 200 and put.json()["upload_id"] == ticket["upload_id"]
        tickets[name] = ticket
    assert tickets["alice"]["upload_id"] != tickets["bob"]["upload_id"]
    # Bob ne connaît que sa capacité : énumérer ne donne rien, toujours la même réponse.
    # Bob only knows his capability: enumerating yields nothing, always the same answer.
    answers = {public.get(f"/v1/results/up_{secrets.token_urlsafe(32)}", headers=BOB).text for _ in range(20)}
    answers.add(public.get("/v1/results/up_" + "a" * 43, headers=BOB).text)
    answers.add(public.delete(f"/v1/results/up_{secrets.token_urlsafe(32)}", headers=BOB).text)
    assert len(answers) == 1 and '"not_found"' in answers.pop()
    bob = public.get(path_of(tickets["bob"]["result_url"]), headers=BOB).json()
    assert "bob" in bob["markdown"] and "alice" not in bob["markdown"] and bob["deleted"]
    # Lu : consommé ; la réponse est celle d'une capacité fausse / read: consumed; same answer as a wrong one.
    consumed = public.get(path_of(tickets["bob"]["result_url"]), headers=BOB)
    wrong = public.get("/v1/results/up_" + "b" * 43, headers=BOB)
    assert consumed.status_code == wrong.status_code == 404 and consumed.json() == wrong.json()
    # L'agent change d'adresse entre ses appels : la capacité suffit / the agent's address changes: capability works.
    alice = public.get(path_of(tickets["alice"]["result_url"]), headers=from_ip("192.0.2.200"))
    assert alice.status_code == 200 and "alice" in alice.json()["markdown"]


def test_a_used_upload_url_answers_like_a_wrong_one(public: TestClient) -> None:
    ticket = public.post("/v1/uploads", headers=ALICE, json={"filename": "a.txt"}).json()
    assert public.put(path_of(ticket["upload_url"]), headers=ALICE, content=b"x").status_code == 200
    again = public.put(path_of(ticket["upload_url"]), headers=BOB, content=b"y")
    wrong = public.put("/v1/uploads/" + secrets.token_urlsafe(32), headers=BOB, content=b"y")
    assert again.status_code == wrong.status_code == 404 and again.json() == wrong.json()


def test_a_keyed_upload_stays_bound_to_its_key(make_client: Callable[..., TestClient]) -> None:
    # Déploiement public avec quelques clés : l'envoi d'une clé exige la clé ET la capacité.
    # Public deployment with a few keys: a keyed upload needs the key AND the capability.
    client = make_client(**PUBLIC, api_keys=(), api_key_sha256=(KEY_A_SHA256,))
    ticket = client.post("/v1/uploads", headers={**ALICE, **AUTH_A}, json={"filename": "a.txt"}).json()
    assert client.put(path_of(ticket["upload_url"]), headers=BOB, content=b"x").status_code == 404
    assert client.put(path_of(ticket["upload_url"]), headers={**BOB, **AUTH_A}, content=b"x").status_code == 200
    assert client.get(path_of(ticket["result_url"]), headers=ALICE).status_code == 404
    assert client.get(path_of(ticket["result_url"]), headers={**BOB, **AUTH_A}).status_code == 200


def test_mcp_upload_commands_carry_the_key_only_for_keyed_callers(make_client: Callable[..., TestClient]) -> None:
    client = make_client(**PUBLIC, api_keys=(), api_key_sha256=(KEY_A_SHA256,))

    def commands(headers: dict[str, str]) -> dict[str, str]:
        return client.post("/mcp", headers={**MCP_HEADERS, **headers}, json=mcp_call(
            "create_upload", {"filename": "a.txt"})).json()["result"]["structuredContent"]["commands"]

    assert all("GDPRGUARDIAN_API_KEY" in command for command in commands({**ALICE, **AUTH_A}).values())
    assert all("Authorization" not in command for command in commands(ALICE).values())


def test_mcp_results_need_the_capability_not_the_session(public: TestClient) -> None:
    def call(who: dict[str, str], name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return public.post("/mcp", headers={**MCP_HEADERS, **who}, json=mcp_call(name, arguments)).json()["result"]

    ticket = call(ALICE, "create_upload", {"filename": "a.txt"})["structuredContent"]
    assert public.put(path_of(ticket["upload_url"]), content=SENSITIVE_TEXT.encode()).status_code == 200
    guess = call(BOB, "get_anonymized", {"upload_id": "up_" + secrets.token_urlsafe(32)})
    assert guess["isError"] is True and "not_found" in guess["content"][0]["text"]
    page = call(ALICE, "get_anonymized", {"upload_id": ticket["upload_id"]})
    assert page["isError"] is False and "[NIR_1]" in page["content"][0]["text"]


@pytest.mark.anyio
async def test_concurrent_synchronous_requests_never_mix_results(fake_documents: None) -> None:
    # 10 clients, 3 requêtes chacun, en même temps : chaque réponse ne porte que son propre texte.
    # 10 clients, 3 requests each, at once: every response carries its own text only.
    app = create_app(ServerConfig(**PUBLIC, isolation=False, max_concurrency=3))
    responses: dict[str, tuple[int, dict[str, str], dict[str, Any]]] = {}

    async def send(index: int) -> None:
        marker = f"Dossier {index:03d} de M. Jean Dupont, NIR {NIR}"
        headers = {CLIENT_HEADER: f"203.0.{index // 3}.7"}  # dix réseaux /24 / ten /24 networks
        responses[f"{index:03d}"] = await asgi_post(app, "/v1/anonymize/text", headers, {"text": marker})

    with anyio.fail_after(60):
        async with anyio.create_task_group() as tasks:
            for index in range(30):
                tasks.start_soon(send, index)
    assert len(responses) == 30
    for marker, (status, headers, body) in responses.items():
        assert status == 200, body
        text = body["text"]
        assert f"Dossier {marker}" in text and NIR not in text
        assert all(f"Dossier {other}" not in text for other in responses if other != marker)
        assert headers["cache-control"] == "no-store"


def test_nothing_is_ever_cacheable(public: TestClient) -> None:
    for response in (public.get("/health"), public.get("/status"), public.get("/nowhere"),
                     public.post("/v1/anonymize/text", headers=ALICE, json={"text": "x"}),
                     public.get("/v1/results/up_" + "c" * 43, headers=ALICE)):
        assert no_store(response) and "expires" not in response.headers and "etag" not in response.headers


# --- même origine pour le cockpit / same origin for the cockpit -------------------------------------------------


def test_cockpit_calls_through_the_site_host_work(make_client: Callable[..., TestClient]) -> None:
    # Nginx renvoie /v1/ des sites vers le service, Host réécrit au nom api.* (contrat C).
    # Nginx forwards the sites' /v1/ to the service with Host rewritten to the api.* name (contract C).
    client = make_client(**PUBLIC, allowed_hosts=("api.gdprguardian.com", "api.gardienrgpd.fr"))
    host = {"Host": "api.gdprguardian.com", **ALICE}
    assert client.post("/v1/anonymize/text", headers=host, json={"text": "x"}).status_code == 200
    file = client.post("/v1/anonymize/file", headers=host, files={"file": ("a.txt", b"x", "text/plain")})
    assert file.status_code == 200
    # Un hôte de site non réécrit est refusé : seul Nginx décide / an unrewritten site host is refused.
    assert client.post("/v1/anonymize/text", headers={"Host": "gdprguardian.com", **ALICE},
                       json={"text": "x"}).status_code == 421


def test_trailing_slashes_are_not_redirected(public: TestClient) -> None:
    response = public.post("/v1/anonymize/text/", headers=ALICE, json={"text": "x"}, follow_redirects=False)
    assert response.status_code == 404 and "location" not in response.headers
