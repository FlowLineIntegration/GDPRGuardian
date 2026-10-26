"""Intergiciels : hôte (DNS rebinding), ordre authentification / corps / middleware: host check, auth before body."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A, MCP_HEADERS

from gdprguardian.server import ServerConfig, create_app
from gdprguardian.server.middleware import host_name, is_loopback_host

LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


@pytest.mark.parametrize(("header", "expected"), [
    ("rgpd.example.eu", "rgpd.example.eu"), ("RGPD.example.eu:443", "rgpd.example.eu"), ("[::1]:8000", "::1"),
    ("[::1]", "::1"), ("127.0.0.1:8000", "127.0.0.1"), ("", ""), ("::1", "::1"),
])
def test_host_name(header: str, expected: str) -> None:
    assert host_name(header) == expected


@pytest.mark.parametrize(("host", "expected"), [
    ("localhost", True), ("127.0.0.1", True), ("127.5.6.7", True), ("::1", True), ("10.0.0.1", False),
    ("evil.example", False), ("localhost.evil.example", False), ("", False),
])
def test_is_loopback_host(host: str, expected: bool) -> None:
    assert is_loopback_host(host) is expected


def test_configured_hosts_protect_every_route(make_client: Callable[..., TestClient]) -> None:
    client = make_client(allowed_hosts=("rgpd.example.eu", "*.rgpd.example.eu"))
    refused = client.get("/v1/packs", headers={**AUTH_A, "Host": "evil.example"})
    assert refused.status_code == 421 and refused.json()["error"]["code"] == "misdirected_request"
    assert refused.headers["x-content-type-options"] == "nosniff"
    assert client.get("/v1/packs", headers={**AUTH_A, "Host": "rgpd.example.eu"}).status_code == 200
    assert client.get("/v1/packs", headers={**AUTH_A, "Host": "api.rgpd.example.eu:443"}).status_code == 200
    # Sonde de santé locale (Docker HEALTHCHECK) toujours acceptée / local health probe always accepted.
    assert client.get("/health", headers={"Host": "127.0.0.1:8000"}).status_code == 200


def test_loopback_server_refuses_foreign_hosts(fake_documents: None) -> None:
    """Mode sans clé sur 127.0.0.1 : une page piégée (DNS rebinding) n'atteint pas l'API / dev mode is shielded."""
    app = create_app(ServerConfig(dev_no_auth=True, isolation=False))
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        rebound = client.post("/v1/anonymize/text", json={"text": "x"}, headers={"Host": "evil.example:8000"})
        assert rebound.status_code == 421
        mcp = client.post("/mcp", headers={**MCP_HEADERS, "Host": "evil.example:8000"}, json=LIST_TOOLS)
        assert mcp.status_code == 421
        assert client.post("/v1/anonymize/text", json={"text": "x"}).status_code == 200
        assert client.post("/v1/anonymize/text", json={"text": "x"},
                           headers={"Host": "localhost:8000"}).status_code == 200


def test_non_loopback_server_without_configuration_is_not_restricted(client: TestClient) -> None:
    assert client.get("/v1/packs", headers={**AUTH_A, "Host": "anything.example"}).status_code == 200


def test_mcp_keeps_its_own_authentication(client: TestClient) -> None:
    response = client.post("/mcp", headers=MCP_HEADERS, json=LIST_TOOLS)
    assert response.status_code == 401 and response.headers["www-authenticate"].startswith("Bearer")
