"""1.0.2, second test de terrain, voie serveur (N à R) / second field test, server lane (items N to R).

Exemples fictifs du test de terrain (fieldtest2-synthesis) : erreurs visibles par un agent MCP (retry_after_s),
avertissements hors du texte, envois rejoués, messages de validation, langue des étiquettes d'un texte court.
Fictitious field-test examples: errors an MCP agent can read, warnings outside the text, replayed uploads,
validation messages, label language of a short text. Moteurs Python et Rust là où le moteur intervient (R).
"""

from __future__ import annotations

import json
from typing import Any

import anyio
import pytest
from fastapi.testclient import TestClient
from fastmcp import Client
from fastmcp.exceptions import ToolError

from gdprguardian import Anonymizer, _native
from gdprguardian.server import ServerConfig, create_app
from gdprguardian.server.errors import UPLOAD_INTERRUPTED_MESSAGE, ServiceBusy, UploadTimeout
from gdprguardian.server.limiter import LimitPolicy
from gdprguardian.server.mcp_online import build_online_mcp
from gdprguardian.server.mcp_tools import retry_hint
from gdprguardian.server.middleware import BodySizeLimitMiddleware, JsonRpcIdProbe, jsonrpc_error_body
from gdprguardian.server.options import AnonymizeOptions
from gdprguardian.server.service import Service

KEY = "alpha-key-0123456789-abcdefghijklmnop"
AUTH = {"Authorization": f"Bearer {KEY}"}
MCP = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
ALICE = {"X-GG-Client": "203.0.113.7"}
CONFIG = ServerConfig(dev_no_auth=True, limits=LimitPolicy(mode="off"), isolation=False)
_ENGINES = [pytest.param(True, id="rust", marks=pytest.mark.skipif(not _native.available(),
                                                                   reason="noyau Rust absent / no Rust core")),
            pytest.param(False, id="python")]


def call(name: str, arguments: dict[str, Any], request_id: int | str = 1) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}}


@pytest.fixture
def client() -> Any:
    with TestClient(create_app(ServerConfig(api_keys=(KEY,), isolation=False))) as test_client:
        yield test_client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --- N : refus visibles par l'agent MCP / refusals an MCP agent can read -------------------------------------------


def test_rate_limit_on_mcp_is_a_jsonrpc_error_with_retry_after() -> None:
    config = ServerConfig(public=True, client_ip_header="X-GG-Client", api_keys=(), isolation=False,
                          limits=LimitPolicy(cost_burst=0.006, cost_rate=0.001))
    with TestClient(create_app(config)) as client:
        first = client.post("/mcp", headers={**MCP, **ALICE}, json=call("anonymize_text", {"text": "Jean Dupont"}))
        assert first.status_code == 200 and "result" in first.json()
        limited = client.post("/mcp", headers={**MCP, **ALICE}, json=call("anonymize_text", {"text": "x"}, 5))
        # HTTP 200 + erreur JSON-RPC : un client MCP ne lit jamais le corps d'un 429 / an MCP client never reads a 429.
        body = limited.json()
        assert limited.status_code == 200 and body["id"] == 5 and body["error"]["code"] == -32000
        wait = int(limited.headers["retry-after"])
        assert body["error"]["data"] == {"code": "rate_limited", "http_status": 429, "retry_after_s": wait}
        assert body["error"]["message"].startswith("rate_limited: ") and f"retry_after_s={wait}" in body["error"][
            "message"]
        # Clients HTTP ordinaires : statut et en-têtes gardés, secondes dans le corps / plain HTTP clients unchanged.
        rest = client.post("/v1/anonymize/text", headers=ALICE, json={"text": "x"})
        assert rest.status_code == 429 and rest.json()["error"]["retry_after_s"] == int(rest.headers["retry-after"])


@pytest.mark.parametrize(("body", "expected"), [
    (b'{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"arguments":{"text":"' + b"x" * 20_000 + b'"}}}', 7),
    (b'{"method":"tools/call","params":{"arguments":{"text":"' + b"y" * 20_000 + b'"}},"jsonrpc":"2.0","id":"a-1"}',
     "a-1"),
    # Un « "id" » dans le texte est échappé : jamais pris pour l'id / an "id" inside the text is escaped: ignored.
    (b'{"method":"tools/call","params":{"arguments":{"text":"\\"id\\": 99"}},"jsonrpc":"2.0","id":3}', 3),
    (b'{"jsonrpc":"2.0","method":"notifications/initialized"}', None),
])
def test_jsonrpc_id_probe_keeps_only_the_ends_of_the_body(body: bytes, expected: object) -> None:
    probe = JsonRpcIdProbe()
    for start in range(0, len(body), 4096):
        probe.feed(body[start:start + 4096])
    assert probe.request_id() == expected
    assert len(probe.head) <= 8 * 1024 and len(probe.tail) <= 512


@pytest.mark.anyio
async def test_slow_mcp_body_becomes_a_jsonrpc_upload_timeout() -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        while (await receive()).get("more_body"):
            pass

    middleware = BodySizeLimitMiddleware(app, limit_for=lambda _scope: 10**6, base_s=0.05, min_rate=10**9)
    scope = {"type": "http", "method": "POST", "path": "/mcp", "headers": [(b"content-length", b"5000")]}
    chunks = [{"type": "http.request", "body": b'{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{',
               "more_body": True}]
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        if chunks:
            return chunks.pop()
        await anyio.sleep(5)  # le client goutte / the client trickles
        raise AssertionError

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await middleware(scope, receive, send)
    start = next(message for message in sent if message["type"] == "http.response.start")
    body = json.loads(b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body"))
    assert start["status"] == 200 and body["id"] == 11 and body["error"]["data"]["code"] == "upload_timeout"
    assert "create_upload" in body["error"]["message"]


def test_busy_tool_error_and_jsonrpc_body_carry_the_wait() -> None:
    assert retry_hint(None) == "" and "retry_after_s=12" in retry_hint(12)
    body = jsonrpc_error_body(ServiceBusy(retry_after=12), 4)
    assert body["error"]["data"] == {"code": "service_busy", "http_status": 503, "retry_after_s": 12}


@pytest.mark.anyio
async def test_fair_use_is_described_to_the_agent() -> None:
    server = build_online_mcp(Service(CONFIG), auth=None)
    async with Client(server) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
    for text in (server.instructions or "", tools["anonymize_text"].description or ""):
        assert "one request at a time" in text and "retry_after_s" in text


# --- O : avertissements hors du texte / warnings outside the text ---------------------------------------------------


@pytest.mark.anyio
async def test_countries_be_on_a_french_text_warns_in_a_second_block() -> None:
    text = "Kevin Lambert, NIR 1 85 05 78 006 084 91, tél. 06 12 34 56 78."
    async with Client(build_online_mcp(Service(CONFIG), auth=None)) as client:
        result = await client.call_tool("anonymize_text", {"text": text, "countries": "BE"})
    assert len(result.content) == 2 and result.content[0].text == result.structured_content["text"]
    warning = result.content[1].text
    assert warning.startswith("[GDPR Guardian] Warning, not part of the text above")
    for kind in ("names and addresses", "NIR", "French-format phone numbers", "SIRET/SIREN/VAT", "plates",
                 "birth dates"):
        assert kind in warning, kind


# --- P : envois / uploads ------------------------------------------------------------------------------------------


def test_replayed_upload_url_says_upload_used(client: TestClient) -> None:
    ticket = client.post("/v1/uploads", headers=AUTH, json={"filename": "dossier.txt"}).json()
    path = ticket["upload_url"].removeprefix("http://testserver")
    assert client.put(path, headers=AUTH, content=b"Dossier de Jean Dupont.").status_code == 202
    again = client.put(path, headers=AUTH, content=b"Dossier de Jean Dupont.")
    assert again.status_code == 404 and again.json()["error"]["code"] == "upload_used"
    assert "create_upload" in again.json()["error"]["message"]
    # Jeton inconnu : toujours la même réponse / unknown token: always the same answer.
    unknown = client.put("/v1/uploads/" + "A" * 43, headers=AUTH, content=b"x")
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "not_found"


def test_failed_upload_errors_say_to_call_create_upload_again() -> None:
    assert "create_upload" in UPLOAD_INTERRUPTED_MESSAGE and "create_upload" in UploadTimeout().message


@pytest.mark.anyio
async def test_upload_limits_and_states_are_documented() -> None:
    service = Service(CONFIG)
    async with Client(build_online_mcp(service, auth=None)) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
    create = tools["create_upload"].description or ""
    assert f"{service.config.max_output_chars:,} characters of anonymised Markdown" in create
    assert "KB/s or faster" in create and "call create_upload again" in create
    get = tools["get_anonymized"].description or ""
    assert "'pending' (stage 'awaiting_upload')" in get and "upload_timeout" in get and "deleted: true" in get
    deleted = tools["get_anonymized"].outputSchema["properties"]["deleted"]["description"]
    assert "still readable for expires_in_seconds" in deleted


# --- Q : messages de validation / validation messages --------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(("arguments", "match"), [
    ({"text": "x", "dupont": "y"},
     r"\? \(unexpected_keyword_argument; unknown argument; allowed: text, countries, mode, disable, label_language, "
     r"rules, explain\)"),
    ({"text": "x", "contries": "FR"}, r"contries \(unexpected_keyword_argument; unknown argument, did you mean "
                                      r"countries\?\)"),
    ({"text": "x", "countries": "FR;BE"}, r"separate codes with a comma, not ';'"),
    ({"text": "x", "explain": "yes"}, r"explain \(bool_type; allowed: true \| false\)"),
])
async def test_validation_messages_name_the_fix(arguments: dict[str, Any], match: str) -> None:
    async with Client(build_online_mcp(Service(CONFIG), auth=None)) as client:
        with pytest.raises(ToolError, match=match) as caught:
            await client.call_tool("anonymize_text", arguments)
    assert "INTL" not in str(caught.value)  # toujours actif, jamais proposé / always on, never offered


@pytest.mark.anyio
async def test_rules_description_matches_what_is_refused() -> None:
    async with Client(build_online_mcp(Service(CONFIG), auth=None)) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
    rules = json.dumps(tools["anonymize_text"].inputSchema["properties"]["rules"])
    assert "look-behind ((?<=...), (?<!...))" in rules and "refused" in rules
    assert '\\"window\\" [before, after]' in rules and "[48, 16]" in rules


# --- S : détails du protocole / protocol details -------------------------------------------------------------------


@pytest.mark.parametrize("payload", [
    [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
      "params": {"name": "anonymize_text", "arguments": {"text": "Jean Dupont, NIR 1 85 05 78 006 084 91"}}}],
    {"id": 1, "method": "tools/call", "params": {"name": "anonymize_text",
                                                 "arguments": {"text": "Jean Dupont, NIR 1 85 05 78 006 084 91"}}},
])
def test_invalid_jsonrpc_gets_32600_without_echo(client: TestClient, payload: object) -> None:
    response = client.post("/mcp", headers={**MCP, **AUTH}, json=payload)
    assert response.status_code == 400 and response.json()["error"]["code"] == -32600
    assert "batches are not supported" in response.json()["error"]["message"]
    assert "Dupont" not in response.text and "1 85 05" not in response.text  # jamais d'écho / never echoed


def test_unparsable_body_gets_32700(client: TestClient) -> None:
    response = client.post("/mcp", headers={**MCP, **AUTH}, content=b'{"jsonrpc": "2.0", "id": 1, "Dupont')
    assert response.status_code == 400 and response.json()["error"]["code"] == -32700
    assert "Dupont" not in response.text


def test_allow_header_names_post_only(client: TestClient) -> None:
    response = client.get("/mcp", headers={**MCP, **AUTH})
    assert response.status_code == 405 and response.headers["allow"] == "POST"


# --- R : langue des étiquettes d'un texte court / label language of a short text ----------------------------------

SHORT_FRENCH = "Kevin Lambert conteste son solde, il dit qu'il n'a rien reçu."


@pytest.mark.parametrize("native", _ENGINES)
def test_short_french_text_gets_french_labels_with_auto(native: bool) -> None:
    options = AnonymizeOptions.build("FR", None, "auto").for_text(SHORT_FRENCH)
    assert options.label_language == "fr"  # deux « il » comptés italiens : détection peu sûre / unsure detection
    engine = Anonymizer(countries=options.countries, mode=options.mode, label_language=options.label_language,
                        native=native)
    assert engine.anonymize(SHORT_FRENCH).text.startswith("[PERSONNE_1] conteste")


@pytest.mark.parametrize("native", _ENGINES)
def test_sure_english_text_keeps_english_labels_with_auto(native: bool) -> None:
    text = ("Please call the client at +44 20 7946 0958 and send the invoice to the accounts team with the reference "
            "that was agreed.")
    options = AnonymizeOptions.build("FR", None, "auto").for_text(text)
    assert options.label_language == "auto"  # détection sûre : le moteur décide / sure detection: the engine decides
    engine = Anonymizer(countries=options.countries, label_language=options.label_language, native=native)
    assert "[PHONE_1]" in engine.anonymize(text).text


def test_short_text_without_french_country_gets_english_labels() -> None:
    assert AnonymizeOptions.build("DE", None, "auto").for_text("Termin morgen.").label_language == "en"
    assert AnonymizeOptions.build("BE", None, "auto").for_text("rdv demain").label_language == "fr"
    assert AnonymizeOptions.build("FR", None, "fr").for_text("the and is").label_language == "fr"


def test_rest_auto_labels_follow_the_countries_on_a_short_text(client: TestClient) -> None:
    body = client.post("/v1/anonymize/text", headers=AUTH, json={"text": SHORT_FRENCH, "label_language": "auto"})
    assert body.json()["text"].startswith("[PERSONNE_1] conteste")
