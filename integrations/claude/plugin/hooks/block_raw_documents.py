#!/usr/bin/env python3
"""Hook PreToolUse de Claude Code : bloque la lecture directe des documents bruts.

Claude Code PreToolUse hook: blocks direct reads of raw documents (Read, Grep, shell readers such as cat,
head, type, Get-Content or Import-Csv in Bash and PowerShell, and MCP tools given a document path) and
tells Claude to use the GDPR Guardian skill.

Configuration (environnement / environment):
  GDPRGUARDIAN_PROTECTED_DIRS        dossiers protégés, séparés par os.pathsep (« ; » sous Windows) ;
                                     vide = protection partout / protected dirs; empty = protect everywhere
  GDPRGUARDIAN_PROTECTED_EXTENSIONS  remplace la liste d'extensions, ex. ".pdf,.docx" / overrides the extensions

Refus : décision « deny » en JSON sur stdout, raison sur stderr, code 2 (bloquant quel que soit le mode de
permission) ; aucune sortie et code 0 = pas de décision. Deny: a JSON "deny" decision on stdout, the
reason on stderr, exit code 2 (blocking whatever the permission mode); no output and exit 0 = no decision.
Garde-fou, pas un bac à sable : ajoutez aussi des règles permissions.deny / a guardrail, not a sandbox.
Bibliothèque standard uniquement, Python 3.9+ / standard library only.
"""

from __future__ import annotations

import base64
import fnmatch
import json
import ntpath
import os
import re
import sys
from collections.abc import Iterable, Iterator, Mapping
from pathlib import PurePath
from typing import Any
from urllib.parse import unquote

EXIT_DENY = 2
DEFAULT_EXTENSIONS = frozenset({
    ".pdf", ".doc", ".docx", ".docm", ".dot", ".dotx", ".odt", ".ott", ".rtf",
    ".xls", ".xlsx", ".xlsm", ".xlsb", ".xltx", ".ods", ".csv", ".tsv",
    ".ppt", ".pptx", ".pptm", ".odp", ".msg", ".eml", ".mbox", ".vcf", ".pages", ".numbers",
})
# Commandes qui affichent un contenu de fichier / commands that print file contents.
READERS = frozenset({
    "cat", "tac", "nl", "more", "less", "most", "head", "tail", "bat", "batcat", "strings", "xxd", "od",
    "hexdump", "base64", "base32", "dd", "type", "get-content", "gc", "select-string", "sls", "findstr", "find",
    "grep", "egrep", "fgrep", "zgrep", "rg", "ag", "ack", "awk", "gawk", "mawk", "sed", "cut", "sort", "uniq",
    "column", "paste", "join", "comm", "diff", "cmp", "rev", "tr", "fold", "fmt", "pr", "expand", "split", "iconv",
    "jq", "yq", "xmllint", "zcat", "zless", "zmore", "bzcat", "xzcat", "tar", "bsdtar", "unzip", "7z", "7za",
    "pdftotext", "pdftohtml", "pdfinfo", "mutool", "qpdf", "exiftool", "tesseract", "pandoc", "markitdown",
    "soffice", "libreoffice", "unoconv", "textutil", "docx2txt", "antiword", "catdoc", "xls2csv", "ssconvert",
    "in2csv", "csvlook", "csvcut", "csvstat", "csvgrep", "csvjson", "csvsql", "csvformat", "mlr", "xsv", "qsv",
    "duckdb", "sqlite3", "vd", "visidata", "vi", "vim", "nvim", "view", "nano", "emacs",
    # PowerShell
    "import-csv", "ipcsv", "import-excel", "format-hex", "fhx", "select-xml", "import-clixml",
})
# Lecteurs PowerShell qui lisent les fichiers reçus par le tube / PowerShell readers fed files by the pipeline.
PIPELINE_READERS = frozenset({"get-content", "gc", "cat", "type", "import-csv", "ipcsv", "select-string", "sls",
                              "format-hex", "fhx", "import-excel"})
GIT_READERS = frozenset({"show", "diff", "log", "blame", "grep", "cat-file"})
POWERSHELLS = frozenset({"pwsh", "powershell"})
SHELLS = POWERSHELLS | {"bash", "sh", "zsh", "dash", "ksh", "fish", "cmd"}
INTERPRETERS = SHELLS | {"python", "python3", "py", "pypy", "pypy3", "node", "deno", "bun", "ruby", "perl", "php",
                         "lua", "rscript", "julia", "osascript"}
INLINE_FLAGS = frozenset({"-c", "-e", "-p", "-r", "--eval", "--print", "/c", "/k"})
# Préfixes qui lancent la commande suivante / prefixes that run the next command.
WRAPPERS = frozenset({"sudo", "doas", "env", "exec", "nohup", "nice", "ionice", "time", "timeout", "stdbuf",
                      "command", "builtin", "noglob", "watch", "xargs", "busybox", "unbuffer"})
CHANGE_DIR = frozenset({"cd", "pushd", "chdir", "set-location", "sl"})
FIND_EXEC = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
SHELL_TOOLS = frozenset({"Bash", "PowerShell"})
# Outils MCP de Gardien RGPD (ils reçoivent un chemin pour anonymiser) / GDPR Guardian's own MCP tools.
GDPRGUARDIAN_MCP_TOOLS = frozenset({"anonymize_file", "create_upload", "get_anonymized", "anonymize_text",
                                    "list_packs"})
# Outils MCP qui ne renvoient pas de contenu de fichier / MCP tools that return no file content.
SAFE_MCP_VERBS = frozenset({"write", "create", "move", "rename", "delete", "remove", "list", "mkdir", "stat",
                            "exists", "upload", "send"})
MCP_PATH_KEYS = frozenset({"file_path", "filepath", "path", "paths", "file", "files", "filename", "uri", "uris",
                           "source", "src", "input", "target", "document"})
REASON = (
    "GDPR Guardian: reading raw documents directly is blocked to protect personal data. Do not retry another way. "
    "Anonymise the document first with gdprguardian-local whenever it is available (the local MCP tool "
    "anonymize_file, or the skill's bundled engine: nothing leaves the computer); older installs call the skill "
    "gdprguardian-anonymize. Only if no local route works, and only after the user agrees to send the document to "
    "the public service, use gdprguardian-online (its script, or create_upload then get_anonymized). Work only "
    "from the anonymised Markdown. / Lecture directe des documents bruts bloquée : anonymisez d'abord avec la "
    "skill gdprguardian-local ; gdprguardian-online (service public) seulement à défaut, avec l'accord de "
    "l'utilisateur."
)
# Jetons du shell : chaînes entre guillemets intactes, opérateurs à part / quoted strings kept, operators apart.
_TOKEN = re.compile(r'"[^"]*"|\'[^\']*\'|\|\||&&|\$\(|[;&|\n`()<]|[^\s"\'|&;`()<]+')
_OPERATORS = frozenset({"||", "&&", "$(", ";", "&", "|", "\n", "`", "(", ")", "{", "}"})
# Chemins cités dans du code (python -c "open('a.csv')", here-doc) / paths quoted inside code.
_PATHLIKE = re.compile(r"[^\s\"'()\[\]{},;=<>|`]+\.[A-Za-z0-9*?]{1,8}")
# Lectures par API .NET ou par lecteur de variable PowerShell (${C:\f.csv}) / .NET or variable-drive reads.
_READ_API = re.compile(r"(?i)readall(?:text|lines|bytes)|\breadlines\b|openread|opentext|streamreader|"
                       r"filestream|\$\{[a-z]:")
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
_PS_ASSIGNMENT = re.compile(r"\$[\w:]+=(.*)")
_OPTION_VALUE = re.compile(r"-{1,2}[A-Za-z][\w-]*[:=](.+)")
_MSYS_DRIVE = re.compile(r"^/([A-Za-z])(?=/|$)")
_BRACES = re.compile(r"\{([^{}]*)\}")
_BRACE_SPLIT = re.compile(r"([{}])")
_GLOB_TOKEN = re.compile(r"[*?]|\[[^\]]*\]")
_MAX_EXPANSIONS = 64
_MAX_DEPTH = 3


class Policy:
    """Extensions et dossiers protégés / protected extensions and directories."""

    def __init__(self, env: Mapping[str, str]) -> None:
        raw_ext = env.get("GDPRGUARDIAN_PROTECTED_EXTENSIONS", "")
        extensions = {e.strip().lower() for e in raw_ext.split(",") if e.strip()}
        self.extensions = frozenset(e if e.startswith(".") else f".{e}" for e in extensions) or DEFAULT_EXTENSIONS
        dirs = env.get("GDPRGUARDIAN_PROTECTED_DIRS", "")
        self.dirs = tuple(_normalize(d.strip()) for d in dirs.split(os.pathsep) if d.strip())

    def protected_extension(self, path: str) -> bool:
        """Extension protégée, y compris via un motif (« *.pd? », « *.{csv,md} ») / globs and braces included."""
        name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
        return any(PurePath(candidate).suffix in self.extensions or self._glob_matches(candidate)
                   for variant in _expand_braces(name) for candidate in _name_variants(variant))

    def _glob_matches(self, pattern: str) -> bool:
        # Motif d'extension explicite (« a.pd? », « *.p* ») ; « * » seul ne compte pas / bare "*" does not count.
        stem, dot, _ = pattern.rpartition(".")
        if not dot or not _GLOB_TOKEN.search(pattern):
            return False
        stems = {_GLOB_TOKEN.sub("", stem), _GLOB_TOKEN.sub("a", stem)}
        return any(fnmatch.fnmatchcase(prefix + ext, pattern) for prefix in stems for ext in self.extensions)

    def in_protected_dir(self, path: str, cwd: str) -> bool:
        if not self.dirs:
            return True
        full = _normalize(path if _is_absolute(path) else os.path.join(cwd, path))
        return any(full == d or full.startswith(d.rstrip(os.sep) + os.sep) for d in self.dirs)

    def protected_file(self, path: str, cwd: str) -> bool:
        return self.protected_extension(path) and self.in_protected_dir(path, cwd)


def _name_variants(name: str) -> Iterator[str]:
    """Nom tel quel, sans flux NTFS (« a.pdf::$DATA ») ni points ou espaces finaux (ignorés par Windows)."""
    base = name.split(":", 1)[0]
    yield from (name, base, base.rstrip(". "), name.rstrip(". "))


def _expand_braces(text: str) -> list[str]:
    """« *.{csv,pdf} » -> « *.csv », « *.pdf » (bornée) / bounded brace expansion."""
    results = [text]
    while len(results) <= _MAX_EXPANSIONS:
        expanded: list[str] = []
        for item in results:
            match = _BRACES.search(item)
            if match is None:
                expanded.append(item)
            else:
                expanded.extend(item[:match.start()] + part + item[match.end():]
                                for part in match.group(1).split(","))
        if expanded == results:
            break
        results = expanded
    return results


def _is_absolute(path: str) -> bool:
    return os.path.isabs(path) or ntpath.isabs(path) or path.startswith("/")


def _normalize(path: str) -> str:
    if os.name == "nt":
        path = _MSYS_DRIVE.sub(lambda m: f"{m.group(1)}:", path)  # /c/Users -> c:/Users (Git Bash)
    return os.path.normcase(os.path.normpath(os.path.expanduser(path)))


def _segments(command: str) -> Iterator[list[str]]:
    """Commandes simples, jetons sans guillemets / simple commands, unquoted tokens.

    Une accolade isolée ou collée (« {cat », « a.pdf} ») sépare ; « a.{pdf,csv} » reste un mot.
    A lone or glued brace (script block) separates; brace expansion stays one word.
    """
    segment: list[str] = []
    for token in _TOKEN.findall(command):
        if token[0] in "\"'" and len(token) >= 2 and token[0] == token[-1]:
            segment.append(token[1:-1])
            continue
        glued_brace = ("{" in token) != ("}" in token)
        for part in filter(None, _BRACE_SPLIT.split(token)) if glued_brace else (token,):
            if part in _OPERATORS:
                yield segment
                segment = []
            else:
                segment.append(part)
    yield segment


def _program(token: str) -> str:
    name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in (".exe", ".com", ".cmd", ".bat"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _strip_wrappers(tokens: list[str]) -> tuple[list[str], bool]:
    """Retire « VAR=x », « $x = », sudo, env, « timeout 5 », xargs… ; indique si xargs lit l'entrée.

    Drops assignments and wrappers; tells whether xargs feeds paths from standard input.
    """
    tokens = list(tokens)
    index, piped, wrapped = 0, False, False
    while index < len(tokens):
        token = tokens[index]
        program = _program(token)
        powershell_assignment = _PS_ASSIGNMENT.fullmatch(token)
        if powershell_assignment and powershell_assignment.group(1):
            tokens[index] = powershell_assignment.group(1)  # « $x=Get-Content » -> « Get-Content »
            continue
        if token.startswith("$") and index + 1 < len(tokens) and tokens[index + 1] == "=":
            index += 2
            continue
        if powershell_assignment or _ASSIGNMENT.fullmatch(token) or program in WRAPPERS:
            piped = piped or program == "xargs"
            wrapped = wrapped or program in WRAPPERS
        elif not (wrapped and (token.startswith("-") or token.replace(".", "").isdigit())):
            break
        index += 1
    return tokens[index:], piped


def _candidates(tokens: Iterable[str]) -> Iterator[str]:
    """Chemins possibles : « @f », « --file=f », « -Path:f », « if=f » / path-like argument values."""
    for token in tokens:
        if token == "<":
            continue
        yield token.lstrip("@")
        option = _OPTION_VALUE.fullmatch(token)
        if option:
            yield option.group(1)
        elif "=" in token:
            yield token.split("=", 1)[1]


def _quoted(code: str, cwd: str, policy: Policy) -> bool:
    return any(policy.protected_file(path, cwd) for path in _PATHLIKE.findall(code))


def shell_reads_protected(command: str, cwd: str, policy: Policy, *, powershell: bool = False,
                          depth: int = 0) -> bool:
    """Une commande shell affiche-t-elle un document protégé ? / does a shell command print a protected file?"""
    if depth > _MAX_DEPTH:
        return False
    if _READ_API.search(command) and _quoted(command, cwd, policy):
        return True
    previous_has_paths = False
    for raw in _segments(command):
        tokens, piped = _strip_wrappers(raw)
        if not tokens:
            continue
        program, arguments = _program(tokens[0]), tokens[1:]
        lowered = [token.lower() for token in arguments]
        if program in CHANGE_DIR:
            target = next((token for token in arguments if not token.startswith("-")), "")
            cwd = target if _is_absolute(target) else os.path.join(cwd, target)
            continue
        if program in INTERPRETERS and _inline_reads(program, arguments, lowered, command, cwd, policy, depth):
            return True
        own_paths = any(c and policy.protected_file(c, cwd) for c in _candidates(arguments))
        reader = (program in READERS
                  or (program == "git" and next((t for t in lowered if not t.startswith("-")), "") in GIT_READERS)
                  or any(flag in FIND_EXEC and i + 1 < len(arguments) and _program(arguments[i + 1]) in READERS
                         for i, flag in enumerate(lowered)))
        if own_paths and (reader or "<" in arguments):
            return True
        # « ls *.pdf | xargs cat », et en PowerShell « Get-ChildItem *.csv | Get-Content ».
        fed = piped or (powershell and program in PIPELINE_READERS and previous_has_paths)
        if reader and fed and _quoted(command, cwd, policy):
            return True
        previous_has_paths = previous_has_paths or own_paths
    return False


def _inline_reads(program: str, arguments: list[str], lowered: list[str], command: str, cwd: str, policy: Policy,
                  depth: int) -> bool:
    """Code en ligne (-c, -Command, /c), here-doc ou entrée standard d'un interpréteur / interpreter inline code."""
    code = _inline_code(program, arguments, lowered)
    if code is not None:
        if program in SHELLS:
            # Shell dans le shell : analyse récursive / shell in a shell: recursive analysis.
            return shell_reads_protected(code, cwd, policy, powershell=program in POWERSHELLS, depth=depth + 1)
        return _quoted(code, cwd, policy)
    # « python - <<EOF … », « node < script » : le code suit dans la commande / the code follows in the command.
    return ("-" in arguments or "<" in arguments) and _quoted(command, cwd, policy)


def _inline_code(program: str, arguments: list[str], lowered: list[str]) -> str | None:
    """Code passé en argument, ou None / code passed as an argument, or None.

    PowerShell accepte les préfixes (« -c », « -enc ») et décode -EncodedCommand (base64 UTF-16) ; sans option,
    Windows PowerShell exécute ses arguments comme une commande. PowerShell accepts prefixes and base64
    -EncodedCommand; without options, Windows PowerShell runs its arguments as a command.
    """
    for index, flag in enumerate(lowered):
        rest = " ".join(arguments[index + 1:])
        if program not in POWERSHELLS:
            if flag in INLINE_FLAGS:
                return rest
        elif flag in ("-e", "-ec") or (len(flag) >= 3 and "-encodedcommand".startswith(flag)):
            try:
                return base64.b64decode(rest.strip()).decode("utf-16-le", "ignore")
            except ValueError:
                return ""
        elif len(flag) >= 2 and "-command".startswith(flag):
            return rest
    if program == "powershell" and arguments and not arguments[0].startswith("-"):
        return " ".join(arguments)
    return None


def grep_reads_protected(tool_input: Mapping[str, Any], cwd: str, policy: Policy) -> bool:
    path = str(tool_input.get("path") or cwd)
    if policy.protected_file(path, cwd):
        return True
    glob = str(tool_input.get("glob") or "")
    file_type = str(tool_input.get("type") or "").lower()
    targets_protected = policy.protected_extension(glob) or f".{file_type}" in policy.extensions
    if targets_protected and policy.in_protected_dir(path, cwd):
        return True
    return bool(policy.dirs) and policy.in_protected_dir(path, cwd)


def _mcp_paths(value: Any, key: str = "", depth: int = 0) -> Iterator[str]:
    """Chemins dans les arguments d'un outil MCP (clés connues, URI file://) / paths in MCP tool arguments."""
    if depth > _MAX_DEPTH:
        return
    if isinstance(value, str):
        if value[:5].lower() == "file:":
            path = unquote(value[5:]).lstrip("/")
            yield path if re.match(r"[A-Za-z]:", path) else "/" + path
        elif key.lower() in MCP_PATH_KEYS:
            yield value
    elif isinstance(value, Mapping):
        for child_key, child in value.items():
            yield from _mcp_paths(child, str(child_key), depth + 1)
    elif isinstance(value, list):
        for child in value[:256]:
            yield from _mcp_paths(child, key, depth + 1)


def mcp_reads_protected(tool: str, tool_input: Mapping[str, Any], cwd: str, policy: Policy) -> bool:
    """Tout outil MCP qui reçoit un document protégé, sauf écriture ou Gardien RGPD / any MCP tool given a document."""
    action = tool.rsplit("__", 1)[-1].lower()
    verb = re.split(r"[_\-.]", action, maxsplit=1)[0]
    if action in GDPRGUARDIAN_MCP_TOOLS or verb in SAFE_MCP_VERBS:
        return False
    return any(policy.protected_file(path, cwd) for path in _mcp_paths(tool_input))


def decide(event: Mapping[str, Any], env: Mapping[str, str]) -> str | None:
    """Raison du refus, ou None / denial reason, or None."""
    if event.get("hook_event_name") not in (None, "PreToolUse"):
        return None
    tool = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, Mapping):
        return None
    cwd = str(event.get("cwd") or os.getcwd())
    policy = Policy(env)
    if tool == "Read":
        blocked = policy.protected_file(str(tool_input.get("file_path") or ""), cwd)
    elif tool == "Grep":
        blocked = grep_reads_protected(tool_input, cwd, policy)
    elif tool in SHELL_TOOLS:
        blocked = shell_reads_protected(str(tool_input.get("command") or ""), cwd, policy,
                                        powershell=tool == "PowerShell")
    elif tool.startswith("mcp__"):
        blocked = mcp_reads_protected(tool, tool_input, cwd, policy)
    else:
        blocked = False
    return REASON if blocked else None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (ValueError, UnicodeDecodeError):
        return 0  # entrée illisible : pas de décision / unreadable input: no decision
    if not isinstance(event, dict):
        return 0
    reason = decide(event, os.environ)
    if reason is None:
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                      "permissionDecisionReason": reason}}, sys.stdout)
    print(reason, file=sys.stderr)
    return EXIT_DENY


if __name__ == "__main__":
    sys.exit(main())
