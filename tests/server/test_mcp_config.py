"""`gdprguardian mcp-config <client>` : extraits prêts à coller, version épinglée / ready-to-paste, pinned snippets."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gdprguardian import __version__, cli

PIN = f"gdprguardian[local]=={__version__}"


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def expected_args(*dirs: str) -> list[str]:
    return ["--from", PIN, "gdprguardian", "mcp", "--stdio", "--allow-dir", *dirs]


@pytest.mark.parametrize(("client", "root_key", "server"), [
    ("claude-desktop", "mcpServers", {}),
    ("cursor", "mcpServers", {}),
    ("vscode", "servers", {"type": "stdio"}),
])
def test_json_clients_use_their_documented_keys(client: str, root_key: str, server: dict[str, str], tmp_path: Path,
                                                capsys: pytest.CaptureFixture[str]) -> None:
    other = tmp_path / "RH"
    code, out, err = run(["mcp-config", client, "--allow-dir", str(tmp_path), str(other)], capsys)
    config = json.loads(out)
    assert code == 0 and list(config) == [root_key] and list(config[root_key]) == ["gdprguardian"]
    args = expected_args(str(tmp_path), str(other))
    assert config[root_key]["gdprguardian"] == {**server, "command": "uvx", "args": args}
    # Conseils et avertissements sur stderr : stdout reste du JSON pur / hints on stderr, stdout stays pure JSON.
    # `uv tool install` : sans lui, uvx a besoin du réseau à chaque démarrage une fois sa copie de l'index périmée.
    # `uv tool install`: without it, uvx needs the network at every start once its index copy is stale.
    assert f'uv tool install "{PIN}"' in err and f'directory not found on this computer: "{other}"' in err


def test_json_is_ascii_so_any_redirection_keeps_accents(capsys: pytest.CaptureFixture[str]) -> None:
    folder = "/home/hélène/Données RH"
    code, out, _ = run(["mcp-config", "cursor", "--allow-dir", folder], capsys)
    assert code == 0 and out.isascii() and json.loads(out)["mcpServers"]["gdprguardian"]["args"][-1] == folder


def test_vscode_keeps_its_own_variables(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["mcp-config", "vscode", "--allow-dir", "${workspaceFolder}/Documents"], capsys)
    assert json.loads(out)["servers"]["gdprguardian"]["args"][-1] == "${workspaceFolder}/Documents"
    assert code == 0 and "not found" not in err


def test_relative_dirs_become_absolute_and_home_is_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                        capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(["mcp-config", "claude-desktop", "--allow-dir", "Clients", "~/GDPRGuardian"], capsys)
    args = json.loads(out)["mcpServers"]["gdprguardian"]["args"]
    assert code == 0 and args[-2:] == [str(tmp_path / "Clients"), "~/GDPRGuardian"]


@pytest.mark.parametrize("client", ["claude-code", "generic"])
def test_posix_commands_split_back_to_the_exact_arguments(client: str, capsys: pytest.CaptureFixture[str]) -> None:
    folder = "/home/marie/Mes documents/GDPRGuardian"
    code, out, _ = run(["mcp-config", client, "--allow-dir", folder, "--shell", "posix"], capsys)
    words = shlex.split(out)
    command = ["uvx", *expected_args(folder)]
    if client == "claude-code":
        command = ["claude", "mcp", "add", "--scope", "user", "--transport", "stdio", "gdprguardian", "--", *command]
    assert code == 0 and words == command and out.count("\n") == 1


def test_powershell_quoting_rules() -> None:
    words = ["claude", "--", "gdprguardian[local]==0.2.0", r"C:\Users\Marie\GDPRGuardian", "C:\\Mes documents\\RH",
             "l'équipe", "$HOME"]
    assert cli.join_command(words, "powershell") == (
        r"claude '--' 'gdprguardian[local]==0.2.0' C:\Users\Marie\GDPRGuardian 'C:\Mes documents\RH' "
        r"'l''équipe' '$HOME'")


def test_unknown_client_and_missing_directory(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValueError, match="unknown client"):
        cli.mcp_client_config("emacs", ["/x"])
    with pytest.raises(SystemExit) as caught:
        cli.main(["mcp-config", "cursor"])
    assert caught.value.code == 2 and "--allow-dir" in capsys.readouterr().err


ARGV_SCRIPT = "import json, sys; print(json.dumps(sys.argv[1:]))"
TRICKY = ["--", "gdprguardian[local]==0.2.0", "--allow-dir", "Mes documents/GDPRGuardian", "l'équipe", "$HOME",
          "a;b", "~/x"]


@pytest.mark.skipif(sys.platform != "win32" or not (shutil.which("pwsh") or shutil.which("powershell")),
                    reason="PowerShell requis / requires PowerShell")
def test_powershell_command_round_trip(tmp_path: Path) -> None:
    """La ligne produite, exécutée par PowerShell, rend exactement les arguments / PowerShell yields the argv."""
    script = tmp_path / "argv.py"
    script.write_text(ARGV_SCRIPT, encoding="utf-8")
    line = f"& '{sys.executable}' -I '{script}' " + cli.join_command(TRICKY, "powershell")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    completed = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", line], capture_output=True,
                               text=True, encoding="utf-8", timeout=120, check=True)
    assert json.loads(completed.stdout) == TRICKY


@pytest.mark.skipif(sys.platform == "win32" or not shutil.which("bash"), reason="bash requis / requires bash")
def test_posix_command_round_trip(tmp_path: Path) -> None:
    script = tmp_path / "argv.py"
    script.write_text(ARGV_SCRIPT, encoding="utf-8")
    line = cli.join_command([sys.executable, "-I", str(script), *TRICKY], "posix")
    completed = subprocess.run(["bash", "-c", line], capture_output=True, text=True, encoding="utf-8", timeout=60,
                               check=True)
    assert json.loads(completed.stdout) == TRICKY
