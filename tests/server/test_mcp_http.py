"""MCP en ligne sur HTTP : authentification, isolement, débit / online MCP over HTTP: auth, isolation, rate."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, AUTH_B, KEY_A, MCP_HEADERS, NIR, SENSITIVE_TEXT, mcp_call

from gdprguardian.server.limiter import LimitPolicy

LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


def call(client: TestClient, headers: dict[str, str], name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/mcp", headers={**MCP_HEADERS, **headers}, json=mcp_call(name, arguments))
    assert response.status_code == 200, response.text
    return response.json()["result"]


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer nope"}, {"Authorization": f"Basic {KEY_A}"}])
def test_mcp_requires_a_valid_key(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post("/mcp", headers={**MCP_HEADERS, **headers}, json=LIST_TOOLS)
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")
    assert response.headers["x-content-type-options"] == "nosniff"


def test_mcp_endpoint_answers_without_redirect(client: TestClient) -> None:
    response = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A}, json=LIST_TOOLS, follow_redirects=False)
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert names == {"create_upload", "get_anonymized", "anonymize_text", "list_packs"}


def test_full_flow_over_http_and_principal_isolation(client: TestClient) -> None:
    ticket = call(client, AUTH_A, "create_upload", {"filename": "dossier.txt"})["structuredContent"]
    assert KEY_A not in str(ticket)
    put = client.put(ticket["upload_url"].removeprefix("http://testserver"), headers=AUTH_A,
                     content=SENSITIVE_TEXT.encode())
    assert put.status_code == 202 and put.json()["stage"] == "queued"
    assert f"get_anonymized(upload_id='{ticket['upload_id']}')" in put.json()["next_step"]
    stolen = call(client, AUTH_B, "get_anonymized", {"upload_id": ticket["upload_id"]})
    assert stolen["isError"] is True and "not_found" in stolen["content"][0]["text"]
    page = call(client, AUTH_A, "get_anonymized", {"upload_id": ticket["upload_id"]})
    assert page["isError"] is False
    assert "[NIR_1]" in page["content"][0]["text"] and NIR not in page["content"][0]["text"]
    structured = page["structuredContent"]
    assert structured["deleted"] is True and structured["stage"] == "done"
    # Le texte et le rapport sont aussi dans le contenu structuré / text and report in structured content too.
    assert "[NIR_1]" in structured["markdown"] and NIR not in structured["markdown"]
    assert structured["report"]["entities"]["NIR"] == 1 and isinstance(structured["report"]["warnings"], list)
    # Relecture possible pendant le délai de grâce (réponse perdue) / re-read during the grace period.
    again = call(client, AUTH_A, "get_anonymized", {"upload_id": ticket["upload_id"]})
    assert again["isError"] is False and again["content"][0]["text"].count("[NIR_1]") >= 1


def test_upload_made_through_rest_is_readable_through_mcp(client: TestClient) -> None:
    ticket = client.post("/v1/uploads", headers=AUTH_A, json={"filename": "a.txt"}).json()
    client.put(ticket["upload_url"].removeprefix("http://testserver"), headers=AUTH_A, content=b"mail a@b.fr")
    page = call(client, AUTH_A, "get_anonymized", {"upload_id": ticket["upload_id"]})
    assert "[EMAIL_1]" in page["content"][0]["text"]


def test_mcp_requests_are_rate_limited_per_key(make_client: Callable[..., TestClient]) -> None:
    # Chaque requête HTTP compte, tools/list et JSON-RPC invalide compris / every HTTP request counts.
    client = make_client(limits=LimitPolicy(cheap_burst=1, cheap_rate=0.01))
    assert call(client, AUTH_A, "anonymize_text", {"text": "x"})["isError"] is False
    for payload in (mcp_call("anonymize_text", {"text": "x"}), LIST_TOOLS, {"jsonrpc": "2.0"}):
        limited = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A}, json=payload)
        assert limited.status_code == 429 and limited.json()["error"]["code"] == "rate_limited"
        assert int(limited.headers["retry-after"]) >= 1
    assert call(client, AUTH_B, "anonymize_text", {"text": "x"})["isError"] is False


def test_dev_mode_mcp_needs_no_key(make_client: Callable[..., TestClient]) -> None:
    client = make_client(dev_no_auth=True)
    result = call(client, {}, "anonymize_text", {"text": "mail a@b.fr"})
    assert result["content"][0]["text"] == "mail [EMAIL_1]"


def test_mcp_body_limit(make_client: Callable[..., TestClient]) -> None:
    client = make_client(max_json_bytes=4096)
    response = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A},
                           json=mcp_call("anonymize_text", {"text": "x" * 10_000}))
    assert response.status_code == 413
