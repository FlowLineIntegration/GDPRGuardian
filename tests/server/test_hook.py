"""Hook Claude Code qui bloque la lecture des documents bruts / Claude Code hook blocking raw-document reads."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from server_testkit import PLUGIN, load_script

HOOK = PLUGIN / "hooks" / "block_raw_documents.py"


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    return load_script(HOOK, "block_raw_documents")


def event(tool: str, cwd: str = "/work", **tool_input: Any) -> dict[str, Any]:
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": cwd}


@pytest.mark.parametrize(("tool", "tool_input", "blocked"), [
    ("Read", {"file_path": "/work/Contrat.PDF"}, True),
    ("Read", {"file_path": "/work/paie.xlsx", "offset": 1, "limit": 10}, True),
    ("Read", {"file_path": "C:\\Users\\me\\export.csv"}, True),
    ("Read", {"file_path": "/work/notes.md"}, False),
    ("Read", {"file_path": "/work/contrat.anon.md"}, False),
    ("Read", {"file_path": "/work/src/app.py"}, False),
    ("Grep", {"pattern": "Dupont", "path": "/work/clients.csv"}, True),
    ("Grep", {"pattern": "Dupont", "glob": "*.csv"}, True),
    ("Grep", {"pattern": "Dupont", "type": "csv"}, True),
    ("Grep", {"pattern": "TODO", "glob": "*.py"}, False),
    ("Bash", {"command": "cat clients.csv"}, True),
    ("Bash", {"command": "head -n 5 \"Mes documents/paie.xlsx\""}, True),
    ("Bash", {"command": "type C:\\docs\\contrat.docx"}, True),
    ("Bash", {"command": "Get-Content -Path .\\export.csv -TotalCount 3"}, True),
    ("Bash", {"command": "ls *.pdf && cat *.csv | sort"}, True),
    ("Bash", {"command": "python -c \"print(open('clients.csv').read())\""}, True),
    ("Bash", {"command": "wc -l < clients.csv"}, True),
    ("Bash", {"command": "python /home/me/.claude/skills/gdprguardian-anonymize/scripts/anonymize_file.py contrat.pdf"},
     False),
    ("Bash", {"command": "curl -sS -X PUT --data-binary @\"contrat.pdf\" https://rgpd.example.eu/v1/uploads/x"},
     False),
    ("Bash", {"command": "ls -la *.pdf"}, False),
    ("Bash", {"command": "cat README.md"}, False),
    ("Bash", {"command": "mv a.pdf archive/a.pdf"}, False),
    ("mcp__filesystem__read_file", {"path": "/work/contrat.pdf"}, True),
    ("mcp__filesystem__write_file", {"path": "/work/contrat.pdf"}, False),
    ("Write", {"file_path": "/work/rapport.csv", "content": "a;b"}, False),
])
def test_decisions_without_protected_dirs(hook: ModuleType, tool: str, tool_input: dict[str, Any],
                                          blocked: bool) -> None:
    reason = hook.decide(event(tool, **tool_input), {})
    assert (reason is not None) is blocked
    if blocked:
        assert "gdprguardian-anonymize" in reason


# Contournements qu'un agent essaie après un premier refus / workarounds an agent tries after a first denial.
@pytest.mark.parametrize("command", [
    # PowerShell (outil dédié sous Windows) / PowerShell tool on Windows
    "Get-Content C:\\docs\\clients.csv -TotalCount 5",
    "Import-Csv .\\clients.csv | Select-Object -First 3",
    "$rows = Import-Csv clients.csv",
    "$c=gc clients.csv",
    "(Get-Content 'C:\\docs\\paie.xlsx')[0]",
    "[System.IO.File]::ReadAllText('C:\\docs\\contrat.docx')",
    "${C:\\docs\\clients.csv}",
    "Get-ChildItem C:\\docs\\*.csv | Get-Content",
    "Get-Content -Path:C:\\docs\\clients.csv",
    "& { type clients.csv }",
    "powershell Get-Content clients.csv",
    "pwsh -NoProfile -enc " + base64.b64encode("Get-Content clients.csv".encode("utf-16-le")).decode(),
])
def test_powershell_readers_are_blocked(hook: ModuleType, command: str) -> None:
    assert hook.decide(event("PowerShell", command=command), {})


@pytest.mark.parametrize("command", [
    "sudo cat clients.csv", "env LC_ALL=C cat clients.csv", "timeout 5 head clients.csv", "LANG=C sort clients.csv",
    "find . -name '*.csv' -exec cat {} \\;", "ls *.pdf | xargs cat", "git show HEAD:data/clients.csv",
    "bash -c 'cat clients.csv'", "cmd /c type contrat.docx", "python -c \"print(open('clients.csv').read())\"",
    "python3 - <<'EOF'\nprint(open('/data/clients.csv').read())\nEOF", "node -e \"fs.readFileSync('a.xlsx')\"",
    "cat clients.pd?", "cat contrat.[pP][dD][fF]", "cat a.{md,csv}", "cat 'clients.csv::$DATA'", "type clients.csv.",
    "dd if=clients.csv", "pdftotext contrat.pdf -", "unzip -p contrat.docx word/document.xml", "less < clients.csv",
    "x=$(cat clients.csv)", "{ cat clients.csv; }",
])
def test_shell_workarounds_are_blocked(hook: ModuleType, command: str) -> None:
    assert hook.decide(event("Bash", command=command), {})


@pytest.mark.parametrize(("tool", "command"), [
    ("Bash", "bash -c 'mv contrat.pdf archive/'"),
    ("Bash", "python -X utf8 /skills/gdprguardian-anonymize/scripts/anonymize_file.py contrat.pdf -o contrat.anon.md"),
    ("PowerShell", "python \"C:\\skills\\gdprguardian-anonymize\\scripts\\anonymize_file.py\" "
                   "\"C:\\docs\\contrat.pdf\""),
    ("PowerShell", "Move-Item C:\\docs\\contrat.pdf C:\\archive\\"),
    ("PowerShell", "Get-ChildItem C:\\docs\\*.pdf"),
    ("PowerShell", "Get-Content README.md"),
    ("Bash", "ls *.pdf | head"),
    ("Bash", "cat *"),
    ("Bash", "cat *.md"),
    ("Bash", "git add contrat.pdf"),
    ("Bash", "curl -sS -X PUT --data-binary @contrat.pdf https://rgpd.example.eu/v1/uploads/x"),
])
def test_harmless_commands_are_allowed(hook: ModuleType, tool: str, command: str) -> None:
    assert hook.decide(event(tool, command=command), {}) is None


@pytest.mark.parametrize(("tool", "tool_input", "blocked"), [
    ("mcp__filesystem__read_text_file", {"path": "/work/clients.csv", "head": 5}, True),
    ("mcp__filesystem__read_multiple_files", {"paths": ["/work/a.md", "/work/b.xlsx"]}, True),
    ("mcp__filesystem__edit_file", {"path": "/work/clients.csv", "edits": []}, True),
    ("mcp__docs__extract_text", {"document": {"uri": "file:///C:/docs/contrat%20bail.pdf"}}, True),
    ("mcp__any__summarize", {"source": "file:///home/me/paie.xlsx"}, True),
    ("mcp__filesystem__list_directory", {"path": "/work"}, False),
    ("mcp__filesystem__move_file", {"source": "/work/a.pdf", "destination": "/archive/a.pdf"}, False),
    ("mcp__gdprguardian__create_upload", {"filename": "contrat.pdf"}, False),
    ("mcp__gdprguardian-local__anonymize_file", {"path": "/work/contrat.pdf"}, False),
    # Nom des outils du plugin (serveur « gdprguardian » du plugin « gdprguardian ») / the plugin's tool name.
    ("mcp__plugin_gdprguardian_gdprguardian__anonymize_file", {"path": "/work/contrat.pdf"}, False),
    ("mcp__slack__send_message", {"text": "voir contrat.pdf"}, False),
])
def test_mcp_tools(hook: ModuleType, tool: str, tool_input: dict[str, Any], blocked: bool) -> None:
    assert (hook.decide(event(tool, **tool_input), {}) is not None) is blocked


def test_change_directory_is_followed(hook: ModuleType, tmp_path: Path) -> None:
    protected = tmp_path / "Clients"
    env = {"GDPRGUARDIAN_PROTECTED_DIRS": str(protected)}
    command = f'cd "{protected}" && cat export.csv'
    assert hook.decide(event("Bash", cwd=str(tmp_path), command=command), env)
    assert hook.decide(event("Bash", cwd=str(tmp_path), command="cd public && cat export.csv"), env) is None


def test_protected_dirs_limit_the_scope(hook: ModuleType, tmp_path: Path) -> None:
    protected = tmp_path / "Clients"
    env = {"GDPRGUARDIAN_PROTECTED_DIRS": str(protected)}
    assert hook.decide(event("Read", file_path=str(protected / "a" / "contrat.pdf")), env)
    assert hook.decide(event("Read", file_path=str(tmp_path / "public" / "doc.pdf")), env) is None
    assert hook.decide(event("Bash", cwd=str(protected), command="cat export.csv"), env)
    assert hook.decide(event("Bash", cwd=str(tmp_path), command="cat export.csv"), env) is None
    assert hook.decide(event("Grep", cwd=str(protected), pattern="x"), env)
    assert hook.decide(event("Grep", cwd=str(tmp_path / "src"), pattern="x"), env) is None


def test_custom_extensions(hook: ModuleType) -> None:
    env = {"GDPRGUARDIAN_PROTECTED_EXTENSIONS": "json, .xml"}
    assert hook.decide(event("Read", file_path="/work/export.json"), env)
    assert hook.decide(event("Read", file_path="/work/contrat.pdf"), env) is None


@pytest.mark.parametrize("payload", [b"", b"not json", b"[1, 2]", json.dumps({"tool_name": "Read"}).encode()])
def test_malformed_input_gives_no_decision(payload: bytes) -> None:
    completed = subprocess.run([sys.executable, "-I", str(HOOK)], input=payload, capture_output=True, timeout=30,
                               check=False)
    assert completed.returncode == 0 and completed.stdout == b""


def test_script_emits_a_blocking_deny_decision() -> None:
    # Code 2 : bloquant quel que soit le mode (bypassPermissions compris) ; raison sur stderr et en JSON.
    # Exit 2 blocks whatever the permission mode; the reason is on stderr and in the JSON decision.
    payload = json.dumps(event("Read", file_path="/work/contrat.pdf")).encode()
    env = {key: value for key, value in os.environ.items() if not key.startswith("GDPRGUARDIAN_")}
    completed = subprocess.run([sys.executable, "-I", str(HOOK)], input=payload, capture_output=True, timeout=30,
                               check=False, env=env)
    assert completed.returncode == 2
    decision = json.loads(completed.stdout)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse" and decision["permissionDecision"] == "deny"
    assert "gdprguardian-anonymize" in decision["permissionDecisionReason"]
    assert b"gdprguardian-anonymize" in completed.stderr
    allowed = json.dumps(event("Read", file_path="/work/notes.md")).encode()
    passed = subprocess.run([sys.executable, "-I", str(HOOK)], input=allowed, capture_output=True, timeout=30,
                            check=True, env=env)
    assert passed.stdout == b"" and passed.stderr == b""
