"""MCP local = MCP en ligne : mêmes outils, schémas, descriptions et résultats, au transport près.

Local MCP = online MCP: same tools, schemas, descriptions and results; only the document intake differs
(anonymize_file locally, create_upload online). Même version dans serverInfo sur les deux transports.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client, FastMCP
from server_testkit import AUTH_A, MCP_HEADERS, SENSITIVE_TEXT

from gdprguardian import __version__
from gdprguardian.server.config import ServerConfig
from gdprguardian.server.limiter import LimitPolicy
from gdprguardian.server.mcp_local import build_local_mcp
from gdprguardian.server.mcp_online import build_online_mcp
from gdprguardian.server.security import DEV_PRINCIPAL
from gdprguardian.server.service import Service

pytestmark = [pytest.mark.anyio, pytest.mark.usefixtures("fake_documents")]
SHARED = {"get_anonymized", "anonymize_text", "list_packs"}
OPTIONS = {"countries", "profile", "label_language", "rules", "explain"}
NONCE = re.compile(r"(GDPRGUARDIAN_DOCUMENT) [0-9a-f]{12}")
CONFIG = ServerConfig(dev_no_auth=True, limits=LimitPolicy(mode="off"), page_chars=1000, isolation=False)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    (tmp_path / "dossier.txt").write_text(SENSITIVE_TEXT * 40, encoding="utf-8")
    return tmp_path


@pytest.fixture
def service() -> Service:
    return Service(CONFIG)


@pytest.fixture
def servers(folder: Path, service: Service) -> tuple[FastMCP, FastMCP]:
    return build_local_mcp([folder], CONFIG), build_online_mcp(service, auth=None)


async def tool_map(server: FastMCP) -> dict[str, dict[str, Any]]:
    async with Client(server) as client:
        # Forme JSON du protocole (inputSchema, outputSchema...) / the protocol's JSON form.
        return {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                for tool in await client.list_tools()}


async def test_tool_lists_differ_only_by_the_document_intake(servers: tuple[FastMCP, FastMCP]) -> None:
    local, online = [await tool_map(server) for server in servers]
    assert set(local) == SHARED | {"anonymize_file"} and set(online) == SHARED | {"create_upload"}
    for name in sorted(SHARED):
        # Nom, description, schémas d'entrée et de sortie, annotations : à l'identique / identical, all of it.
        assert local[name] == online[name], name


async def test_intake_tools_share_the_same_options(servers: tuple[FastMCP, FastMCP]) -> None:
    local, online = [await tool_map(server) for server in servers]
    upload, file = online["create_upload"]["inputSchema"], local["anonymize_file"]["inputSchema"]
    assert set(upload["properties"]) - {"filename"} == set(file["properties"]) - {"path"} == OPTIONS
    for option in sorted(OPTIONS):
        assert file["properties"][option] == upload["properties"][option], option
    assert file["properties"]["countries"]["default"] == "FR"
    assert file["required"] == ["path"] and upload["required"] == ["filename"]
    shared_text = (await tool_map(servers[0]))["anonymize_text"]["inputSchema"]["properties"]
    assert all(shared_text[option] == file["properties"][option] for option in OPTIONS)


@pytest.mark.parametrize("mode", ["legacy", "auto"])
async def test_server_info_reports_the_package_version_in_memory(servers: tuple[FastMCP, FastMCP], mode: str) -> None:
    # « legacy » : poignée de main initialize ; « auto » : server/discover / initialize handshake or server/discover.
    for server in servers:
        async with Client(server, mode=mode) as client:
            info = client.server_info
        assert info is not None and (info.name, info.version) == ("gdprguardian", __version__)


def test_server_info_reports_the_package_version_over_http(make_client: Callable[..., TestClient]) -> None:
    client = make_client()
    initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}}
    response = client.post("/mcp", headers={**MCP_HEADERS, **AUTH_A}, json=initialize)
    assert response.status_code == 200
    assert response.json()["result"]["serverInfo"] == {"name": "gdprguardian", "version": __version__}


async def once(data: bytes) -> AsyncIterator[bytes]:
    yield data


async def test_same_results_on_both_transports(servers: tuple[FastMCP, FastMCP], folder: Path,
                                               service: Service) -> None:
    local, online = servers
    arguments = {"text": SENSITIVE_TEXT, "label_language": "en", "explain": True}
    async with Client(local) as local_client, Client(online) as online_client:
        for tool, args in (("anonymize_text", arguments), ("list_packs", {})):
            a, b = [await client.call_tool(tool, args) for client in (local_client, online_client)]
            assert a.content[0].text == b.content[0].text and a.structured_content == b.structured_content, tool

        # Même document, deux entrées : pages identiques (au nonce et à l'upload_id près).
        # Same document, two intakes: identical pages (but for the nonce and the upload_id).
        first = await local_client.call_tool("anonymize_file", {"path": str(folder / "dossier.txt")})
        ticket = (await online_client.call_tool("create_upload", {"filename": ".txt"})).structured_content
        await service.receive_upload(ticket["upload_url"].rsplit("/", 1)[-1], DEV_PRINCIPAL,
                                     once((folder / "dossier.txt").read_bytes()))
        pages = [(first, await online_client.call_tool("get_anonymized", {"upload_id": ticket["upload_id"]}))]
        assert first.structured_content["next_page"] == 2
        pages.append(tuple([await client.call_tool("get_anonymized", {"upload_id": upload_id, "page": 2})
                            for client, upload_id in ((local_client, first.structured_content["upload_id"]),
                                                      (online_client, ticket["upload_id"]))]))
    for a, b in pages:
        text_a, text_b = (NONCE.sub(r"\1", page.content[0].text).replace(page.structured_content["upload_id"], "ID")
                          for page in (a, b))
        assert text_a == text_b
        meta_a, meta_b = ({k: v for k, v in page.structured_content.items() if k not in ("upload_id",
                                                                                          "expires_in_seconds")}
                          for page in (a, b))
        assert meta_a == meta_b
