"""Serveur MCP local (stdio) : dossiers autorisés, lecture bornée / local stdio server: allowed dirs, bounded reads."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError
from server_testkit import EMAIL, NIR, SENSITIVE_TEXT

from gdprguardian import __version__
from gdprguardian.server.config import ServerConfig
from gdprguardian.server.errors import NotFound
from gdprguardian.server.limiter import LimitPolicy
from gdprguardian.server.mcp_local import allowed_dirs_from_env, build_local_mcp, resolve_allowed, resolve_roots

pytestmark = pytest.mark.anyio


@pytest.fixture
def allowed(tmp_path: Path) -> Path:
    folder = tmp_path / "dossiers"
    folder.mkdir()
    (folder / "client.txt").write_text(SENSITIVE_TEXT, encoding="utf-8")
    return folder


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    folder = tmp_path / "prive"
    folder.mkdir()
    (folder / "secret.txt").write_text(SENSITIVE_TEXT, encoding="utf-8")
    return folder


@pytest.fixture
def server(allowed: Path, fake_documents: None) -> FastMCP:
    return build_local_mcp([allowed], ServerConfig(dev_no_auth=True, limits=LimitPolicy(mode="off"), page_chars=1000,
                                                   isolation=False))


async def test_anonymize_allowed_file(server: FastMCP, allowed: Path) -> None:
    async with Client(server) as client:
        tools = {tool.name for tool in await client.list_tools()}
        result = await client.call_tool("anonymize_file", {"path": str(allowed / "client.txt"), "countries": "FR"})
    assert tools == {"anonymize_file", "get_anonymized", "anonymize_text", "list_packs"}
    text = result.content[0].text
    assert "document.txt" not in text and "[NIR_1]" in text and "client" not in text
    assert NIR not in text and EMAIL not in text
    assert result.structured_content["deleted"] is True


async def test_a_slow_file_returns_the_progress_then_the_pages(server: FastMCP, allowed: Path,
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
    # Au-delà de l'attente, l'outil rend l'avancement au lieu de bloquer ; get_anonymized prend le relais.
    # Past the wait, the tool returns the progress instead of blocking; get_anonymized takes over.
    import anyio

    from gdprguardian.server import mcp_local

    monkeypatch.setattr(mcp_local, "_LOCAL_WAIT_S", 0.0)
    async with Client(server) as client:
        first = await client.call_tool("anonymize_file", {"path": str(allowed / "client.txt")})
        meta = first.structured_content
        if meta["page"] is None:
            assert meta["status"] == "processing" and meta["retry_after_s"] >= 2
            assert "call get_anonymized" in first.content[0].text
        for _ in range(500):
            page = await client.call_tool("get_anonymized", {"upload_id": meta["upload_id"]})
            if page.structured_content["page"] is not None:
                break
            await anyio.sleep(0.01)
    assert page.structured_content["page"] == 1 and "[NIR_1]" in page.content[0].text


async def test_large_file_is_paginated(server: FastMCP, allowed: Path) -> None:
    (allowed / "long.txt").write_text("".join(f"{i} : {i}@exemple.fr\n" for i in range(300)), encoding="utf-8")
    async with Client(server) as client:
        first = await client.call_tool("anonymize_file", {"path": str(allowed / "long.txt")})
        meta = first.structured_content
        assert meta["next_page"] == 2
        second = await client.call_tool("get_anonymized", {"upload_id": meta["upload_id"], "page": 2})
    assert "@exemple.fr" not in second.content[0].text


@pytest.mark.parametrize("relative", ["../prive/secret.txt", "..\\prive\\secret.txt", "missing.txt", "."])
async def test_paths_outside_allowed_dirs_are_refused_alike(server: FastMCP, allowed: Path, outside: Path,
                                                             relative: str) -> None:
    async with Client(server) as client:
        with pytest.raises(ToolError) as caught:
            await client.call_tool("anonymize_file", {"path": str(allowed) + os.sep + relative})
    assert "not_found" in str(caught.value) and NIR not in str(caught.value)


async def test_absolute_path_outside_and_relative_path(server: FastMCP, outside: Path) -> None:
    async with Client(server) as client:
        with pytest.raises(ToolError, match="not_found"):
            await client.call_tool("anonymize_file", {"path": str(outside / "secret.txt")})
        with pytest.raises(ToolError, match="invalid_request"):
            await client.call_tool("anonymize_file", {"path": "dossiers/client.txt"})


async def test_symlink_escape_is_refused(server: FastMCP, allowed: Path, outside: Path) -> None:
    link = allowed / "lien.txt"
    try:
        link.symlink_to(outside / "secret.txt")
    except OSError:
        pytest.skip("liens symboliques non autorisés / symlinks not permitted")
    async with Client(server) as client:
        with pytest.raises(ToolError, match="not_found"):
            await client.call_tool("anonymize_file", {"path": str(link)})


async def test_no_allowed_dirs(fake_documents: None, allowed: Path) -> None:
    async with Client(build_local_mcp([], ServerConfig(dev_no_auth=True, isolation=False))) as client:
        with pytest.raises(ToolError, match=r"no_allowed_dirs: .*--allow-dir DIR \[DIR \.\.\.\]"):
            await client.call_tool("anonymize_file", {"path": str(allowed / "client.txt")})


async def test_folder_created_after_start_is_used_without_restart(tmp_path: Path, fake_documents: None) -> None:
    # Défaut du plugin (~/GDPRGuardian) pas encore créé : message exploitable, puis il sert dès sa création.
    # Plugin default not created yet: actionable message, then it works as soon as it exists.
    later = tmp_path / "GDPRGuardian"
    async with Client(build_local_mcp([later], ServerConfig(dev_no_auth=True, isolation=False))) as client:
        with pytest.raises(ToolError) as caught:
            await client.call_tool("anonymize_file", {"path": str(later / "client.txt")})
        assert str(caught.value).startswith("no_allowed_dirs") and f'"{later}"' in str(caught.value)
        assert "create this folder" in str(caught.value) and "no restart needed" in str(caught.value)
        later.mkdir()
        (later / "client.txt").write_text(SENSITIVE_TEXT, encoding="utf-8")
        result = await client.call_tool("anonymize_file", {"path": str(later / "client.txt")})
    assert "[NIR_1]" in result.content[0].text and NIR not in result.content[0].text


async def test_refusal_names_the_allowed_folders_as_written(tmp_path: Path, allowed: Path, outside: Path,
                                                            fake_documents: None,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    # « ~ » développé par le serveur, mais cité tel qu'écrit : pas de chemin personnel dans le message.
    # "~" expanded by the server, but quoted as written: no personal path in the message.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    config = ServerConfig(dev_no_auth=True, isolation=False)
    async with Client(build_local_mcp(["~/dossiers"], config)) as client:
        found = await client.call_tool("anonymize_file", {"path": str(allowed / "client.txt")})
        with pytest.raises(ToolError) as caught:
            await client.call_tool("anonymize_file", {"path": str(outside / "secret.txt")})
    assert "[NIR_1]" in found.content[0].text
    assert str(caught.value).startswith("not_found") and '("~/dossiers")' in str(caught.value)
    assert str(tmp_path) not in str(caught.value) and NIR not in str(caught.value)


async def test_file_size_limit(allowed: Path, fake_documents: None) -> None:
    server = build_local_mcp([allowed], ServerConfig(dev_no_auth=True, max_upload_bytes=16, isolation=False))
    async with Client(server) as client:
        with pytest.raises(ToolError, match="payload_too_large"):
            await client.call_tool("anonymize_file", {"path": str(allowed / "client.txt")})


def test_roots_and_env_parsing(tmp_path: Path, allowed: Path) -> None:
    env = {"GDPRGUARDIAN_ALLOWED_DIRS": os.pathsep.join([str(allowed), " ", str(tmp_path / "absent"), "relative"])}
    dirs = allowed_dirs_from_env(env)
    assert dirs == [str(allowed), str(tmp_path / "absent"), "relative"]
    roots = resolve_roots(dirs)
    assert roots.real == (allowed.resolve(),) and len(roots.written) == 1 and roots.shown == (str(allowed),)
    missing = "introuvable ou pas un dossier / not found or not a directory"
    assert roots.unusable == ((str(tmp_path / "absent"), missing), ("relative", "chemin relatif / relative path"))
    assert resolve_allowed(str(allowed / "client.txt"), roots) == (allowed / "client.txt").resolve()
    assert not resolve_roots([])


def test_network_paths_are_refused_without_any_disk_access(allowed: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Sous Windows, résoudre \\hôte\partage ouvre une session SMB et envoie le hachage NTLM de l'utilisateur.
    # On Windows, resolving \\host\share opens an SMB session and sends the user's NTLM hash.
    roots = resolve_roots([allowed])

    def no_disk(*_args: object, **_kwargs: object) -> None:
        pytest.fail("accès disque hors des dossiers autorisés / disk access outside the allowed dirs")

    monkeypatch.setattr(Path, "resolve", no_disk)
    monkeypatch.setattr(Path, "is_file", no_disk)
    for path in ("//attacker.invalid/share/x.txt", str(allowed.parent / "prive" / "secret.txt"),
                 str(allowed) + os.sep + ".." + os.sep + "secret.txt"):
        with pytest.raises(NotFound):
            resolve_allowed(path, roots)


def test_allowed_dir_reached_through_a_link(tmp_path: Path, allowed: Path) -> None:
    link = tmp_path / "raccourci"
    try:
        link.symlink_to(allowed, target_is_directory=True)
    except OSError:
        pytest.skip("liens symboliques non autorisés / symlinks not permitted")
    roots = resolve_roots([link])
    assert resolve_allowed(str(link / "client.txt"), roots) == (allowed / "client.txt").resolve()


async def test_real_stdio_subprocess(allowed: Path, outside: Path) -> None:
    """Vrai processus stdio : stdout ne porte que le protocole / real stdio process: stdout carries only MCP.

    Deux dossiers après un seul --allow-dir, comme un sélecteur MCPB développé ; GDPRGUARDIAN_ALLOWED_DIRS ignoré.
    Two folders after a single --allow-dir, as an expanded MCPB picker; GDPRGUARDIAN_ALLOWED_DIRS is ignored.
    """
    env = {**os.environ, "GDPRGUARDIAN_ALLOWED_DIRS": str(allowed.parent), "PYTHONIOENCODING": "utf-8"}
    args = ["-m", "gdprguardian.cli", "mcp", "--stdio", "--allow-dir", str(allowed), str(outside)]
    async with Client(StdioTransport(sys.executable, args, env=env, keep_alive=False), mode="legacy") as client:
        info = client.server_info
        tools = {tool.name for tool in await client.list_tools()}
        result = await client.call_tool("anonymize_text", {"text": f"mail {EMAIL}"})
        second = await client.call_tool("anonymize_file", {"path": str(outside / "secret.txt")})
        with pytest.raises(ToolError, match="not_found"):
            await client.call_tool("anonymize_file", {"path": str(allowed.parent / "elsewhere.txt")})
    assert info is not None and (info.name, info.version) == ("gdprguardian", __version__)
    assert tools == {"anonymize_file", "get_anonymized", "anonymize_text", "list_packs"}
    assert result.content[0].text == "mail [EMAIL_1]"
    assert "[NIR_1]" in second.content[0].text and NIR not in second.content[0].text
