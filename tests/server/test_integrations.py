"""Plugins Claude, marketplace et paquet MCPB : cohérents entre eux et avec les serveurs.

Claude plugins, marketplace and MCPB bundle: consistent with each other and with the servers. Une seule ligne
de lancement (`cli.local_server_args`), une seule version, les mêmes outils. Deux plugins : local (serveur MCP
local, skill gdprguardian-local, garde-fou) et léger (MCP en ligne sur HTTP, skill gdprguardian-online).
One launch line, one version, the same tools. Two plugins: local and light (online MCP over HTTP).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client
from server_testkit import INTEGRATIONS, PLUGIN, REPO, load_script

from gdprguardian import __version__
from gdprguardian.cli import local_server_args
from gdprguardian.server.config import ServerConfig
from gdprguardian.server.mcp_local import build_local_mcp

MCPB = REPO / "packaging" / "mcpb"
ONLINE_PLUGIN = INTEGRATIONS / "plugin-online"
ONLINE_SCRIPT = ONLINE_PLUGIN / "skills" / "gdprguardian-online" / "scripts" / "gdprguardian_online.py"
PLACEHOLDER = re.compile(r"\$\{user_config\.([^}]+)\}")
HOOK_COMMAND = ('uv run --no-project --no-config --quiet "${CLAUDE_PLUGIN_ROOT}/hooks/block_raw_documents.py"; '
                "exit $LASTEXITCODE")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def skill_frontmatter(path: Path) -> tuple[str, str]:
    front, body = path.read_text(encoding="utf-8").split("---", 2)[1:]
    return front, body


@pytest.fixture(scope="module")
def plugin() -> dict[str, Any]:
    return load(PLUGIN / ".claude-plugin" / "plugin.json")


@pytest.fixture(scope="module")
def online_plugin() -> dict[str, Any]:
    return load(ONLINE_PLUGIN / ".claude-plugin" / "plugin.json")


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    return load(MCPB / "manifest.json")


@pytest.fixture(scope="module")
def marketplace() -> dict[str, Any]:
    return load(REPO / ".claude-plugin" / "marketplace.json")


def numbers(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


def test_one_version_everywhere(plugin: dict[str, Any], online_plugin: dict[str, Any], manifest: dict[str, Any],
                                marketplace: dict[str, Any]) -> None:
    version = plugin["version"]
    assert marketplace["plugins"][0]["version"] == marketplace["metadata"]["version"] == manifest["version"] == version
    # Plugin léger : version dans plugin.json seulement (release.py ne la suit pas encore) / light plugin: version in
    # plugin.json only; an entry version, if any, must agree.
    assert online_plugin["version"] == version
    assert all(entry.get("version", version) == version for entry in marketplace["plugins"])
    # Les intégrations épinglent la version en préparation, jamais une plus ancienne que le paquet.
    # The integrations pin the version being prepared, never one older than the package.
    assert numbers(version) >= numbers(__version__)


def test_every_documented_pin_is_the_release_version(plugin: dict[str, Any]) -> None:
    # Les commandes à copier (README, description du paquet MCPB) suivent la version publiée.
    # The copyable commands (READMEs, MCPB description) follow the released version.
    docs = [*(REPO / "integrations").rglob("*.md"), MCPB / "README.md", MCPB / "manifest.json"]
    pins = {(path.relative_to(REPO).as_posix(), pin) for path in docs
            for pin in re.findall(r"gdprguardian\[local\]==(\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?)",
                                  path.read_text(encoding="utf-8"))}
    assert pins and {pin for _, pin in pins} == {plugin["version"]}, sorted(pins)


def test_plugin_and_mcpb_launch_the_same_pinned_server(plugin: dict[str, Any], manifest: dict[str, Any]) -> None:
    server = load(PLUGIN / ".mcp.json")["mcpServers"]["gdprguardian"]
    assert server == {"type": "stdio", "command": "uvx",
                      "args": local_server_args(["${user_config.allowed_dir}"], plugin["version"])}
    config = manifest["server"]["mcp_config"]
    assert config["command"] == "uvx"
    assert config["args"] == local_server_args(["${user_config.allowed_directories}"], manifest["version"])
    # Le sélecteur multiple ne se développe en arguments séparés que pour un élément exactement « ${user_config.X} ».
    # The multiple picker expands into separate arguments only for an element that is exactly "${user_config.X}".
    assert PLACEHOLDER.fullmatch(config["args"][-1])
    for platform, override in config["platform_overrides"].items():
        assert set(override) == {"env"} and override["env"]["PATH"].startswith("${HOME}/.local/bin:"), platform


def test_plugin_manifest_follows_the_platform_rules(plugin: dict[str, Any]) -> None:
    assert plugin["name"] == "gdprguardian" and not plugin["name"].startswith(("claude-", "anthropic-"))
    for key, option in plugin["userConfig"].items():
        assert re.fullmatch(r"[A-Za-z_]\w*", key) and {"type", "title", "description"} <= set(option)
    # Cowork ignore un serveur MCP de plugin dont une option référencée n'a pas de valeur par défaut.
    # Cowork ignores a plugin MCP server whose referenced option has no default.
    referenced = set(PLACEHOLDER.findall((PLUGIN / ".mcp.json").read_text(encoding="utf-8")))
    assert referenced == {"allowed_dir"} and all("default" in plugin["userConfig"][key] for key in referenced)
    assert plugin["userConfig"]["allowed_dir"]["default"] == "~/GDPRGuardian"
    assert not (PLUGIN / "bin").exists() and (PLUGIN / "README.md").is_file()


def test_marketplace_lists_both_plugins(plugin: dict[str, Any], online_plugin: dict[str, Any],
                                        marketplace: dict[str, Any]) -> None:
    local, light = marketplace["plugins"]
    assert marketplace["name"] == local["name"] == plugin["name"] and marketplace["owner"]["name"]
    assert (REPO / local["source"]).resolve() == PLUGIN.resolve()
    assert light["name"] == online_plugin["name"] == "gdprguardian-online"
    assert (REPO / light["source"]).resolve() == ONLINE_PLUGIN.resolve()
    for entry in (local, light):
        assert entry["source"].startswith("./") and entry["description"] and entry["license"] == "MIT"
        assert not entry["name"].startswith(("claude-", "anthropic-"))


def test_light_plugin_sends_the_api_key_to_the_online_mcp(online_plugin: dict[str, Any]) -> None:
    servers = load(ONLINE_PLUGIN / ".mcp.json")["mcpServers"]
    script = load_script(ONLINE_SCRIPT, "gdprguardian_online_for_plugin")
    # Service en ligne réservé aux clés : Claude Code développe ${GDPRGUARDIAN_API_KEY}, variable de l'utilisateur,
    # dans l'en-tête ; jamais de clé en clair dans le dépôt, aucune option : rien à installer. Keyed online service:
    # Claude Code expands the user's ${GDPRGUARDIAN_API_KEY} in the header; never a plaintext key in the repository.
    assert servers == {"gdprguardian": {"type": "http", "url": f"{script.PUBLIC_URL}/mcp",
                                        "headers": {"Authorization": "Bearer ${GDPRGUARDIAN_API_KEY}"}}}
    assert "GDPRGUARDIAN_API_KEY" in online_plugin["description"]
    assert "userConfig" not in online_plugin and not (ONLINE_PLUGIN / "hooks").exists()
    assert sorted(path.name for path in (ONLINE_PLUGIN / "skills").iterdir()) == ["gdprguardian-online"]
    assert (ONLINE_PLUGIN / "README.md").is_file()


def test_hooks_point_to_the_shipped_script() -> None:
    entries = load(PLUGIN / "hooks" / "hooks.json")["hooks"]["PreToolUse"]
    assert {entry["matcher"] for entry in entries} == {"Read|Grep|Bash|PowerShell", "mcp__.*"}
    for entry in entries:
        (hook,) = entry["hooks"]
        # Forme shell, chemin entre guillemets, sans « args » : un hôte qui ignorerait « args » lancerait « uv »
        # seul, qui sort en code 2 et bloquerait chaque appel d'outil. « exit $LASTEXITCODE » : PowerShell
        # (-Command) rendrait 1 au lieu de 2, un refus non bloquant ; bash et sh, la variable étant vide,
        # rendent le code de la dernière commande. Shell form, quoted path, no "args" (a host ignoring "args" would
        # run bare "uv", exit 2, blocking every tool call). "exit $LASTEXITCODE": PowerShell would turn 2 into 1,
        # a non-blocking denial; in bash and sh the variable is empty, so the last command's code is kept.
        assert hook == {"type": "command", "command": HOOK_COMMAND, "timeout": 10}
    assert (PLUGIN / "hooks" / "block_raw_documents.py").is_file()


def _hook_shells() -> dict[str, list[str]]:
    """Shells des hooks : bash ou sh sous POSIX ; Git Bash, sinon PowerShell, sous Windows."""
    if os.name != "nt":
        return {name: [found, "-c"] for name in ("bash", "sh") if (found := shutil.which(name))}
    shells = {name: [found, "-NoProfile", "-NonInteractive", "-Command"]
              for name in ("pwsh", "powershell") if (found := shutil.which(name))}
    git_bash = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"
    if git_bash.is_file():
        shells["git bash"] = [str(git_bash), "-c"]
    return shells


@pytest.mark.skipif(shutil.which("uv") is None or not _hook_shells(), reason="uv et un shell requis")
@pytest.mark.parametrize("shell", sorted(_hook_shells()))
def test_hook_runs_exactly_as_declared_and_denies_a_raw_read(shell: str, tmp_path: Path) -> None:
    """La commande de hooks.json, lancée comme Claude Code 2.1.305 lance un hook en forme shell, sous un dossier avec
    espace, accent et apostrophe : refus bloquant (code 2) dans le délai déclaré, quel que soit le shell. Claude Code
    met CLAUDE_PLUGIN_ROOT dans l'environnement (barres obliques pour Git Bash) ; pour PowerShell, il réécrit
    ${CLAUDE_PLUGIN_ROOT} en ${env:CLAUDE_PLUGIN_ROOT} et lance « -Command » sans reprendre le code de sortie.

    The hooks.json command, run as Claude Code 2.1.305 runs a shell-form hook, under a folder with a space, an accent
    and an apostrophe: a blocking denial (exit 2) within the declared timeout, whatever the shell. Claude Code puts
    CLAUDE_PLUGIN_ROOT in the environment; for PowerShell it rewrites the placeholder to ${env:CLAUDE_PLUGIN_ROOT}
    and runs "-Command" without propagating the exit code.
    """
    root = tmp_path / "Hélène O'Brien" / "plugin"
    (root / "hooks").mkdir(parents=True)
    shutil.copy2(PLUGIN / "hooks" / "block_raw_documents.py", root / "hooks" / "block_raw_documents.py")
    hook = load(PLUGIN / "hooks" / "hooks.json")["hooks"]["PreToolUse"][0]["hooks"][0]
    command = hook["command"]
    env = {key: value for key, value in os.environ.items() if not key.startswith("GDPRGUARDIAN_")}
    env["CLAUDE_PLUGIN_ROOT"] = str(root).replace("\\", "/") if shell == "git bash" else str(root)
    if shell in ("pwsh", "powershell"):
        command = command.replace("${CLAUDE_PLUGIN_ROOT}", "${env:CLAUDE_PLUGIN_ROOT}")
    for event, expected in (({"tool_name": "Read", "tool_input": {"file_path": "/work/paie.xlsx"}}, 2),
                            ({"tool_name": "Read", "tool_input": {"file_path": "/work/notes.md"}}, 0)):
        payload = json.dumps({"hook_event_name": "PreToolUse", "cwd": "/work", **event}).encode()
        started = time.monotonic()
        completed = subprocess.run([*_hook_shells()[shell], command], input=payload, capture_output=True, env=env,
                                   timeout=120, check=False)
        assert completed.returncode == expected, completed.stderr
        assert time.monotonic() - started < hook["timeout"]
        if expected:
            assert json.loads(completed.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_local_skill_prefers_the_local_tool_then_its_bundled_engine(plugin: dict[str, Any]) -> None:
    skill = PLUGIN / "skills" / "gdprguardian-local"
    front, body = skill_frontmatter(skill / "SKILL.md")
    assert sorted(path.name for path in (PLUGIN / "skills").iterdir()) == ["gdprguardian-local"]
    assert re.search(r"(?m)^name: gdprguardian-local$", front)
    assert re.search(r"(?m)^description: .*never leaves", front)
    server_key = next(iter(load(PLUGIN / ".mcp.json")["mcpServers"]))
    assert f"mcp__plugin_{plugin['name']}_{server_key}__anonymize_file" in front
    assert body.index("Route 1: the local MCP tool") < body.index("Route 2: the bundled engine")
    assert "Never fall back to" in body and "~/GDPRGuardian" in body and "create_upload" in body
    assert (skill / "scripts" / "gdprguardian_local.py").is_file()
    # Les roues ne vivent que dans les archives de skills/ / wheels only live in the skills/ archives.
    assert not (skill / "wheels").exists()


def test_online_skill_names_its_plugin_tools(online_plugin: dict[str, Any]) -> None:
    skill = ONLINE_PLUGIN / "skills" / "gdprguardian-online"
    front, body = skill_frontmatter(skill / "SKILL.md")
    assert re.search(r"(?m)^name: gdprguardian-online$", front)
    server_key = next(iter(load(ONLINE_PLUGIN / ".mcp.json")["mcpServers"]))
    for tool in ("create_upload", "get_anonymized", "anonymize_text", "list_packs"):
        assert f"mcp__plugin_{online_plugin['name']}_{server_key}__{tool}" in front
        assert f"mcp__gdprguardian__{tool}" in front
    flat = " ".join(body.split())
    assert body.index("Route A") < body.index("Route B") and "Never fall back to reading the original file" in flat
    assert (skill / "scripts" / "gdprguardian_online.py").is_file()


def test_local_comes_first_and_uploads_need_consent() -> None:
    # Deux skills installées : la locale gagne ; la skill en ligne prévient avant le premier envoi ; le hook le dit.
    # Both skills installed: the local one wins; the online one asks before the first upload; the hook agrees.
    online_front, online_body = skill_frontmatter(ONLINE_PLUGIN / "skills" / "gdprguardian-online" / "SKILL.md")
    local_front, local_body = skill_frontmatter(PLUGIN / "skills" / "gdprguardian-local" / "SKILL.md")
    assert "gdprguardian-local skill or a local anonymize_file tool is available, use that instead" in online_front
    assert "wait for their agreement before the first upload" in online_front
    assert "Always use this skill rather than gdprguardian-online" in local_front
    online, local = (" ".join(body.split()) for body in (online_body, local_body))
    assert online.index("**Local first.**") < online.index("**Ask before the first upload.**") < online.index("Route A")
    assert "Showing it to the user is the intended use" in online and "only if this skill cannot run" in local
    reason = load_script(PLUGIN / "hooks" / "block_raw_documents.py", "gdprguardian_hook_for_skills").REASON
    assert reason.index("gdprguardian-local") < reason.index("gdprguardian-online") and "user agrees" in reason


def test_skill_limits_are_quoted_from_the_script() -> None:
    # Les limites publiées vivent dans le script (MAX_FILE_MB, MAX_TEXT_CHARS) ; les textes les citent.
    # The published limits live in the script; the texts quote them.
    script = load_script(ONLINE_SCRIPT, "gdprguardian_online_limits")
    raw = (ONLINE_PLUGIN / "skills" / "gdprguardian-online" / "SKILL.md").read_text(encoding="utf-8")
    text = " ".join(raw.split())
    assert f"{script.MAX_FILE_MB} MB per file" in text and f"{script.MAX_TEXT_CHARS:,} characters" in text
    assert "MAX_FILE_MB" in text and "MAX_TEXT_CHARS" in text


@pytest.mark.anyio
async def test_mcpb_manifest_matches_the_local_server(manifest: dict[str, Any]) -> None:
    # 0.2 : version finalisée, connue de tout hôte ; rien de 0.3 (icons, localization, _meta) n'est utilisé.
    # 0.2: the finalised version every host knows; nothing from 0.3 (icons, localization, _meta) is used.
    assert manifest["manifest_version"] == "0.2" and manifest["server"]["type"] == "binary"
    option = manifest["user_config"]["allowed_directories"]
    assert option["type"] == "directory" and option["multiple"] is True and option["required"] is True
    # Rien ne quitte le poste : pas de politique de confidentialité de service tiers / nothing leaves the computer.
    assert "privacy_policies" not in manifest
    assert {"darwin", "win32"} <= set(manifest["compatibility"]["platforms"])
    async with Client(build_local_mcp([], ServerConfig(dev_no_auth=True, isolation=False))) as client:
        tools = {tool.name for tool in await client.list_tools()}
    assert sorted(tool["name"] for tool in manifest["tools"]) == sorted(tools)


def test_icon_is_a_square_png_of_at_least_512_px() -> None:
    data = (PLUGIN / ".claude-plugin" / "icon.png").read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and width == height >= 512 and len(data) < 2 * 2**20


def test_mcpb_build_checks_versions_and_stages_only_the_bundle(tmp_path: Path, plugin: dict[str, Any],
                                                               manifest: dict[str, Any]) -> None:
    build = load_script(MCPB / "build.py", "gdprguardian_mcpb_build")
    assert build.check_versions(manifest, plugin) == manifest["version"]
    for broken in ({**manifest, "version": "9.9.9"}, {**plugin, "version": "9.9.9"}):
        with pytest.raises(build.BuildError):
            build.check_versions(*((broken, plugin) if "server" in broken else (manifest, broken)))
    staged = build.stage(tmp_path / "bundle")
    assert sorted(path.name for path in staged.iterdir()) == ["LICENSE", "icon.png", "manifest.json"]
    assert build.find_mcpb("mcpb-explicit") == "mcpb-explicit"
