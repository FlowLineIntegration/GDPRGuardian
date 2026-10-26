"""Une seule version pour toute la publication de Gardien RGPD / one version for the whole GDPR Guardian release.

La version de référence est `[project] version` de pyproject.toml. Les autres champs (noyau Rust, paquet MCP,
server.json, plugin Claude, bundle MCPB, versions épinglées des commandes documentées) en sont des copies : `set`
les réécrit, `check` refuse tout écart. Les fichiers créés ailleurs dans le dépôt peuvent manquer.
The reference version is pyproject.toml's `[project] version`. Every other field is a copy: `set` rewrites them,
`check` refuses any drift. Files created elsewhere in the repository may be missing.

    python tools/release.py version                        (version de référence / reference version)
    python tools/release.py check [--tag v0.2.0] [--release]
    python tools/release.py set 0.3.0                      (ou / or 0.3.0rc1 : 0.3.0-rc.1 dans / in Cargo)
    python tools/release.py set-owner <compte GitHub>      (remplace / replaces REPLACE-WITH-GITHUB-OWNER)
    python tools/release.py dists dist/ [--complete]       (archives construites / built archives)
    python tools/release.py smoke [--gdprguardian EXE] [--native | --pure] [-- COMMANDE DU SERVEUR MCP...]

Bibliothèque standard seule, données fictives seules / standard library only, fictitious data only.
"""

from __future__ import annotations

import argparse
import email.parser
import json
import os
import queue
import re
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import tomllib
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "REPLACE-WITH-GITHUB-OWNER"
_GITHUB_LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}")
# Versions acceptées : finale ou préversion, forme PEP 440 ; Cargo écrit les préversions en SemVer.
# Accepted versions: final or pre-release, PEP 440 form; Cargo writes pre-releases as SemVer.
_PEP440 = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?")
_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?")
_TO_SEMVER = {"a": "alpha", "b": "beta", "rc": "rc"}
_TO_PEP440 = {value: key for key, value in _TO_SEMVER.items()}
# Version épinglée d'un de nos paquets, dans une commande ou une dépendance : `gdprguardian[local]==0.2.0`,
# `gdprguardian-core==0.2.0; …`, `uvx gdprguardian-mcp@0.2.0`. One of our packages pinned in a command or dependency.
PIN = re.compile(r"(?<![\w.-])(?P<name>gdprguardian(?:-core|-mcp)?)(?:\[[\w,\s-]*\])?\s*(?:==|@)\s*"
                 r"(?P<v>\d+(?:\.\d+)+(?:(?:a|b|rc)\d+)?)(?![\w.]*\d)")
# Nom du paquet MCPB cité dans les guides : `gdprguardian-0.2.0.mcpb` / MCPB bundle name quoted in the guides.
BUNDLE = re.compile(r"(?<![\w.-])(?P<name>gdprguardian)-(?P<v>\d+(?:\.\d+)+(?:(?:a|b|rc)\d+)?)\.mcpb\b")
# Fichiers dont les épinglages doivent suivre la version / files whose pins must follow the version.
PIN_FILES = ("pyproject.toml", "server.json", "README.md", "deploy/README.md", "docs/*.md", "rust/README.md",
             "packaging/**/*.toml", "packaging/**/*.json", "packaging/**/*.md", "integrations/**/*.json",
             "integrations/**/*.md")
# Fichiers publiés où le nom du compte GitHub apparaît / published files naming the GitHub account.
OWNER_FILES = ("pyproject.toml", "rust/pyproject.toml", "server.json", "packaging/**/*", "integrations/**/*")


@dataclass(frozen=True, slots=True)
class Field:
    """Champ de version dans un fichier / a version field in a file.

    `count` : nombre exact d'occurrences (None : au moins une). `required=False` : fichier créé ailleurs dans le
    dépôt, ignoré tant qu'il n'existe pas. `count`: exact number of occurrences (None: at least one).
    `required=False`: file created elsewhere in the repository, skipped while missing.
    """

    path: str
    label: str
    pattern: str
    cargo: bool = False
    required: bool = True
    count: int | None = 1


_TOML_VERSION = r'(?m)^version = "(?P<v>[^"]+)"'
_JSON_VERSION = r'"version"\s*:\s*"(?P<v>[^"]+)"'
FIELDS = (
    Field("pyproject.toml", "[project] version (référence / reference)", _TOML_VERSION),
    Field("src/gdprguardian/__init__.py", "__version__", r'(?m)^__version__ = "(?P<v>[^"]+)"'),
    Field("rust/Cargo.toml", "[package] version", _TOML_VERSION, cargo=True),
    Field("rust/Cargo.lock", "gdprguardian-core", r'(?m)^name = "gdprguardian-core"\r?\nversion = "(?P<v>[^"]+)"',
          cargo=True),
    Field("packaging/gdprguardian-mcp/pyproject.toml", "[project] version", _TOML_VERSION),
    Field("server.json", "version, packages[].version", _JSON_VERSION, count=2),
    Field("integrations/claude/plugin/.claude-plugin/plugin.json", "version", _JSON_VERSION, required=False,
          count=None),
    Field("integrations/claude/plugin-online/.claude-plugin/plugin.json", "version", _JSON_VERSION, required=False,
          count=None),
    Field("packaging/mcpb/manifest.json", "version", _JSON_VERSION, required=False, count=None),
    Field(".claude-plugin/marketplace.json", "metadata.version, plugins[].version", _JSON_VERSION, required=False,
          count=2),
    Field("packaging/mcpb/pyproject.toml", "[project] version", _TOML_VERSION, required=False),
    Field("deploy/server/compose.yaml", "image", r"(?m)^\s*image: gdprguardian:(?P<v>[^\s\"']+)", required=False),
    # Démon du site (crate autonome) / site daemon (standalone crate).
    Field("site/Cargo.toml", "[package] version", _TOML_VERSION, cargo=True, required=False),
    Field("site/Cargo.lock", "gdprguardian-site", r'(?m)^name = "gdprguardian-site"\r?\nversion = "(?P<v>[^"]+)"',
          cargo=True, required=False),
)


@dataclass(frozen=True, slots=True)
class Occurrence:
    """Une version lue dans un fichier, avec sa position / a version read in a file, with its position."""

    path: str
    label: str
    value: str
    span: tuple[int, int]
    cargo: bool = False


class ReleaseError(Exception):
    """Erreur affichée telle quelle / error printed as is."""


# --- versions -----------------------------------------------------------------------------------------------


def parse_version(version: str) -> tuple[int, int, int, str, int]:
    """Version PEP 440 acceptée par `set` / PEP 440 version accepted by `set`."""
    match = _PEP440.fullmatch(version)
    if match is None:
        raise ReleaseError(f"version invalide / invalid version: {version!r} (X.Y.Z, X.Y.ZaN, X.Y.ZbN, X.Y.ZrcN)")
    major, minor, patch, pre, number = match.groups()
    return int(major), int(minor), int(patch), pre or "", int(number or 0)


def cargo_form(version: str) -> str:
    """0.3.0rc1 -> 0.3.0-rc.1 (SemVer de Cargo) ; une version finale ne change pas / finals are unchanged."""
    major, minor, patch, pre, number = parse_version(version)
    base = f"{major}.{minor}.{patch}"
    return f"{base}-{_TO_SEMVER[pre]}.{number}" if pre else base


def python_form(version: str) -> str:
    """Forme PEP 440 d'une version écrite en PEP 440 ou en SemVer (Cargo) / PEP 440 form of either spelling."""
    if _PEP440.fullmatch(version):
        return version
    match = _SEMVER.fullmatch(version)
    if match is None:
        return version
    major, minor, patch, pre, number = match.groups()
    return f"{major}.{minor}.{patch}{_TO_PEP440[pre]}{number}" if pre else f"{major}.{minor}.{patch}"


def reference_version(root: Path = ROOT) -> str:
    """`[project] version` de pyproject.toml / pyproject.toml's `[project] version`."""
    with (root / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


# --- lecture et contrôle / reading and checking --------------------------------------------------------------


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:  # fins de ligne conservées / line endings kept
        return handle.read()


def _text(path: Path) -> str:
    """Texte d'un fichier, vide s'il est binaire (icône) / a file's text, empty when binary (icon)."""
    try:
        return _read(path)
    except UnicodeDecodeError:
        return ""


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _expand(root: Path, patterns: Sequence[str]) -> list[Path]:
    """Fichiers désignés par des motifs, sans les dossiers de construction / files matched, build dirs excluded."""
    found: dict[Path, None] = {}
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            parts = path.relative_to(root).parts
            if path.is_file() and not {"target", "node_modules", "__pycache__", ".venv", "dist"} & set(parts):
                found[path] = None
    return list(found)


def occurrences(root: Path = ROOT) -> tuple[list[Occurrence], list[str]]:
    """Toutes les versions de la publication, et les problèmes de forme / every version, and shape problems."""
    found: list[Occurrence] = []
    problems: list[str] = []
    for field in FIELDS:
        path = root / field.path
        if not path.is_file():
            if field.required:
                problems.append(f"{field.path}: fichier absent / missing file")
            continue
        matches = list(re.finditer(field.pattern, _read(path)))
        if not matches or (field.count is not None and len(matches) != field.count):
            expected = "au moins une / at least one" if field.count is None else str(field.count)
            problems.append(f"{field.path}: {field.label}: {len(matches)} occurrence(s), attendu / expected "
                            f"{expected}")
        found.extend(Occurrence(field.path, field.label, match["v"], match.span("v"), field.cargo)
                     for match in matches)
    for path in _expand(root, PIN_FILES):
        relative, text = path.relative_to(root).as_posix(), _text(path)
        found.extend(Occurrence(relative, f"{match['name']} épinglé / pinned", match["v"], match.span("v"))
                     for pattern in (PIN, BUNDLE) for match in pattern.finditer(text))
    return found, problems


def consistency(root: Path = ROOT) -> list[str]:
    """Règles entre fichiers / cross-file rules: dynamic core version, registry name and package."""
    problems: list[str] = []
    try:
        with (root / "rust/pyproject.toml").open("rb") as handle:
            core = tomllib.load(handle)["project"]
        if "version" in core or "version" not in core.get("dynamic", []):
            problems.append("rust/pyproject.toml: la version doit venir de Cargo.toml (dynamic = [\"version\"]) / "
                            "the version must come from Cargo.toml")
        server = json.loads(_read(root / "server.json"))
        marker = re.search(r"mcp-name:\s*(\S+)", _read(root / "packaging/gdprguardian-mcp/README.md"))
        if marker is None or marker.group(1) != server.get("name"):
            problems.append("packaging/gdprguardian-mcp/README.md: « mcp-name: » doit valoir le nom de server.json / "
                            "must equal server.json's name")
        with (root / "packaging/gdprguardian-mcp/pyproject.toml").open("rb") as handle:
            meta = tomllib.load(handle)["project"]
        identifiers = [package.get("identifier") for package in server.get("packages", [])]
        if identifiers != [meta["name"]]:
            problems.append(f"server.json: packages[].identifier {identifiers} != [{meta['name']!r}]")
    except (OSError, KeyError, ValueError) as exc:
        problems.append(f"lecture impossible / unreadable: {exc}")
    return problems


def check(root: Path = ROOT, tag: str | None = None, release: bool = False) -> list[str]:
    """Liste des problèmes ; vide si tout concorde / list of problems, empty when everything agrees."""
    version = reference_version(root)
    try:
        expected = {False: version, True: cargo_form(version)}
    except ReleaseError as exc:
        return [f"pyproject.toml: {exc}"]
    found, problems = occurrences(root)
    problems.extend(f"{item.path}: {item.label} = {item.value}, attendu / expected {expected[item.cargo]}"
                    for item in found if item.value != expected[item.cargo])
    problems.extend(consistency(root))
    if tag is not None and tag != f"v{version}":
        problems.append(f"étiquette / tag {tag} != v{version}")
    if release:
        problems.extend(f"{path.relative_to(root).as_posix()}: {PLACEHOLDER} (python tools/release.py set-owner "
                        f"<compte>)" for path in _expand(root, OWNER_FILES) if PLACEHOLDER in _text(path))
    return problems


def set_version(version: str, root: Path = ROOT) -> list[str]:
    """Réécrit chaque champ ; seules les versions changent / rewrites every field, only versions change."""
    parse_version(version)
    found, problems = occurrences(root)
    if problems:
        raise ReleaseError("\n".join(problems))
    by_file: dict[str, list[Occurrence]] = {}
    for item in found:
        by_file.setdefault(item.path, []).append(item)
    changed: list[str] = []
    for relative, items in by_file.items():
        path = root / relative
        text = original = _read(path)
        # De la fin vers le début : les positions restent justes / from the end: positions stay valid.
        for item in sorted({item.span: item for item in items}.values(), key=lambda item: item.span, reverse=True):
            start, end = item.span
            text = text[:start] + (cargo_form(version) if item.cargo else version) + text[end:]
        if text != original:
            _write(path, text)
            changed.append(relative)
    return changed


def set_owner(login: str, root: Path = ROOT) -> list[str]:
    """Remplace le nom provisoire du compte GitHub / replaces the GitHub account placeholder."""
    if not _GITHUB_LOGIN.fullmatch(login):
        raise ReleaseError(f"compte GitHub invalide / invalid GitHub account: {login!r}")
    changed = []
    for path in _expand(root, OWNER_FILES):
        text = _text(path)
        if PLACEHOLDER in text:
            _write(path, text.replace(PLACEHOLDER, login))
            changed.append(path.relative_to(root).as_posix())
    return changed


# --- archives construites / built archives --------------------------------------------------------------------

# Plateformes des roues du noyau publiées / platforms of the published core wheels.
CORE_PLATFORMS = {
    "Windows x64": re.compile(r"win_amd64"),
    "macOS x86_64": re.compile(r"macosx_\d+_\d+_x86_64"),
    "macOS arm64": re.compile(r"macosx_\d+_\d+_arm64"),
    "Linux x86_64 glibc": re.compile(r"manylinux_\d+_\d+_x86_64"),
    "Linux aarch64 glibc": re.compile(r"manylinux_\d+_\d+_aarch64"),
    "Linux x86_64 musl": re.compile(r"musllinux_\d+_\d+_x86_64"),
    "Linux aarch64 musl": re.compile(r"musllinux_\d+_\d+_aarch64"),
}
_WHEEL = re.compile(r"(?P<name>[A-Za-z0-9_]+)-(?P<version>[^-]+)-(?P<python>[^-]+)-(?P<abi>[^-]+)-(?P<platform>[^-]+)"
                    r"\.whl")
_SDIST = re.compile(r"(?P<name>[A-Za-z0-9_]+)-(?P<version>[^-]+)\.tar\.gz")
_LICENSE = re.compile(r"(?:^|/)(?:licenses/)?LICEN[CS]E[^/]*$")


def _metadata(raw: bytes) -> Any:
    return email.parser.BytesParser().parsebytes(raw)


def check_wheel(path: Path, version: str) -> tuple[list[str], str]:
    """Problèmes d'une roue et sa famille de plateforme / a wheel's problems and its platform family."""
    match = _WHEEL.fullmatch(path.name)
    if match is None:
        return [f"{path.name}: nom de roue invalide / invalid wheel name"], ""
    problems: list[str] = []
    name = match["name"]
    if match["version"] != version:
        problems.append(f"{path.name}: version {match['version']} != {version}")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        info = next((n for n in names if n.endswith(".dist-info/METADATA")), None)
        metadata = _metadata(archive.read(info)) if info else None
        entry_points = next((archive.read(n).decode() for n in names if n.endswith(".dist-info/entry_points.txt")),
                            "")
    if metadata is None or metadata["Version"] != version:
        problems.append(f"{path.name}: METADATA absent ou d'une autre version / missing or other version")
    if not any(_LICENSE.search(n) and ".dist-info/" in n for n in names):
        problems.append(f"{path.name}: licence absente de .dist-info / no licence in .dist-info")
    if any("__pycache__" in n or n.endswith((".pyc", ".pyo")) for n in names):
        problems.append(f"{path.name}: contient du code compilé Python / contains Python bytecode")
    requires = [str(item) for item in (metadata.get_all("Requires-Dist") or [])] if metadata else []
    family = ""
    if name == "gdprguardian":
        if (match["python"], match["abi"], match["platform"]) != ("py3", "none", "any"):
            problems.append(f"{path.name}: roue pure attendue / pure wheel expected")
        if not any(req.replace(" ", "").startswith(f"gdprguardian-core=={version};") for req in requires):
            problems.append(f"{path.name}: dépendance gdprguardian-core=={version} (avec marqueurs) absente / missing")
    elif name == "gdprguardian_core":
        if (match["python"], match["abi"]) != ("cp311", "abi3"):
            problems.append(f"{path.name}: roue abi3 cp311 attendue / abi3 cp311 wheel expected")
        family = next((label for label, rule in CORE_PLATFORMS.items() if rule.search(match["platform"])), "")
        if not family:
            problems.append(f"{path.name}: plateforme inattendue / unexpected platform")
    elif name == "gdprguardian_mcp":
        if not any(req.replace(" ", "") == f"gdprguardian[local]=={version}" for req in requires):
            problems.append(f"{path.name}: dépendance gdprguardian[local]=={version} absente / missing")
        if not re.search(r"(?m)^gdprguardian-mcp\s*=\s*gdprguardian\.cli:mcp_main\s*$", entry_points):
            problems.append(f"{path.name}: commande gdprguardian-mcp absente / missing command")
    else:
        problems.append(f"{path.name}: paquet inattendu / unexpected package")
    return problems, family


def check_sdist(path: Path, version: str) -> list[str]:
    match = _SDIST.fullmatch(path.name)
    if match is None or match["name"] not in {"gdprguardian", "gdprguardian_core", "gdprguardian_mcp"}:
        return [f"{path.name}: archive source inattendue / unexpected sdist"]
    problems = [] if match["version"] == version else [f"{path.name}: version {match['version']} != {version}"]
    with tarfile.open(path) as archive:
        names = archive.getnames()
        info = next((n for n in names if n.count("/") == 1 and n.endswith("/PKG-INFO")), None)
        metadata = _metadata(archive.extractfile(info).read()) if info else None  # type: ignore[union-attr]
    if metadata is None or metadata["Version"] != version:
        problems.append(f"{path.name}: PKG-INFO absent ou d'une autre version / missing or other version")
    if not any(_LICENSE.search(n) for n in names):
        problems.append(f"{path.name}: licence absente / no licence")
    return problems


def check_dists(folder: Path, version: str, complete: bool) -> list[str]:
    """Contrôle les archives d'un dossier avant publication / checks a folder's archives before publishing."""
    problems: list[str] = []
    families: set[str] = set()
    names: set[str] = set()
    files = sorted(p for p in folder.iterdir() if p.suffix == ".whl" or p.name.endswith(".tar.gz"))
    for path in files:
        if path.suffix == ".whl":
            found, family = check_wheel(path, version)
            families.add(family)
            names.add(path.name.split("-", 1)[0] + ":wheel")
        else:
            found = check_sdist(path, version)
            names.add(path.name.split("-", 1)[0] + ":sdist")
        problems.extend(found)
    if not files:
        problems.append(f"{folder}: aucune archive / no archive")
    if complete:
        problems.extend(f"roue du noyau manquante / missing core wheel: {label}" for label in CORE_PLATFORMS
                        if label not in families)
        expected = {f"{name}:{kind}" for name in ("gdprguardian", "gdprguardian_core", "gdprguardian_mcp")
                    for kind in ("wheel", "sdist")}
        problems.extend(f"archive manquante / missing archive: {item}" for item in sorted(expected - names))
    return problems


# --- essai d'une installation / smoke test of an installation ----------------------------------------------

# Données entièrement fictives (valeurs des jeux de test) / entirely fictitious data (test-fixture values).
SAMPLE = ("Dossier de M. Jean Dupont, NIR 1 85 05 78 006 084 91, courriel jean.dupont@exemple.fr, "
          "IBAN FR76 3000 6000 0112 3456 7890 189.")
SAMPLE_CSV = "nom;courriel;telephone\nJean Dupont;jean.dupont@exemple.fr;06 12 34 56 78\n"
SECRETS = ("1 85 05 78 006 084 91", "jean.dupont@exemple.fr", "FR76 3000 6000 0112 3456 7890 189", "06 12 34 56 78")
MCP_TOOLS = {"anonymize_file", "anonymize_text", "get_anonymized", "list_packs"}
_PROTOCOL_VERSION = "2025-06-18"


class _StdioPeer:
    """Client MCP minimal sur stdio (JSON-RPC, une ligne par message) / minimal stdio MCP client."""

    def __init__(self, command: Sequence[str], env: dict[str, str], log: Path) -> None:
        self._stderr = log.open("wb")
        self.process = subprocess.Popen(list(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self._stderr, env=env)
        self._lines: queue.Queue[bytes] = queue.Queue()
        self._ids = iter(range(1, 1 << 30))
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self._lines.put(line)
        self._lines.put(b"")

    def send(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}).encode("utf-8") + b"\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        ident = next(self._ids)
        self.send({"id": ident, "method": method, "params": params})
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                line = self._lines.get(timeout=max(0.0, deadline - time.monotonic()))
            except queue.Empty:
                raise ReleaseError(f"MCP {method}: pas de réponse en {timeout_s:g} s / no reply") from None
            if not line:
                raise ReleaseError(f"MCP {method}: le serveur s'est arrêté / the server stopped")
            try:
                message = json.loads(line)
            except ValueError:
                raise ReleaseError("MCP: stdout porte autre chose que le protocole / stdout carries non-protocol "
                                   "output") from None
            if message.get("id") != ident:
                continue  # notification ou journal du serveur / server notification or log
            if "error" in message:
                raise ReleaseError(f"MCP {method}: {message['error'].get('message', 'error')}")
            return dict(message["result"])

    def close(self) -> int:
        assert self.process.stdin is not None
        self.process.stdin.close()  # fin de stdin : le serveur s'arrête / end of stdin: the server stops
        try:
            code = self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.kill()
            code = self.process.wait()
        self._stderr.close()
        return code


def _clean(text: str, what: str) -> str:
    leaked = [secret for secret in SECRETS if secret in text]
    if leaked:
        raise ReleaseError(f"{what}: valeur non anonymisée / value left in clear ({len(leaked)})")
    return text


def _tool_text(result: dict[str, Any], what: str) -> str:
    if result.get("isError"):
        raise ReleaseError(f"{what}: erreur de l'outil / tool error")
    return _clean("\n".join(item.get("text", "") for item in result.get("content", [])), what)


def _run_cli(command: list[str], stdin: bytes = b"") -> str:
    """Sortie d'une commande ; en cas d'échec, son stderr (sans contenu de document par construction).

    A command's output; on failure, its stderr (no document content by design of the CLI).
    """
    # UTF-8 aussi pour print() sous Windows, sortie redirigée / UTF-8 for print() too on Windows, piped output.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    done = subprocess.run(command, input=stdin, capture_output=True, timeout=300, check=False, env=env)
    if done.returncode:
        raise ReleaseError(f"{' '.join(command[1:])}: code {done.returncode}\n"
                           f"{done.stderr.decode('utf-8', 'replace')[-3000:]}")
    return done.stdout.decode("utf-8")


def smoke_cli(executable: str, version: str, native: bool | None) -> Iterator[str]:
    """`gdprguardian --version`, une anonymisation, la liste des packs / version, one anonymisation, packs."""
    shown = _run_cli([executable, "--version"])
    if shown.split() != ["gdprguardian", version]:
        raise ReleaseError(f"gdprguardian --version: {shown.strip()!r}, attendu / expected 'gdprguardian {version}'")
    yield f"gdprguardian --version -> {version}"
    payload = json.loads(_run_cli([executable, "anonymize", "-", "--format", "json", "--countries", "FR"],
                                  SAMPLE.encode("utf-8")))
    text = _clean(payload["text"], "gdprguardian anonymize")
    if not {"[NIR_1]", "[EMAIL_1]", "[IBAN_1]"} <= set(re.findall(r"\[[A-Z_]+_\d+\]", text)):
        raise ReleaseError(f"gdprguardian anonymize: balises attendues absentes / expected placeholders missing: "
                           f"{text}")
    engine = "rust" if payload["report"]["native"] else "python"
    if native is not None and payload["report"]["native"] is not native:
        raise ReleaseError(f"moteur / engine: {engine}, attendu / expected {'rust' if native else 'python'}")
    yield f"gdprguardian anonymize -> {text} (moteur / engine: {engine})"
    if "FR" not in {row["id"] for row in json.loads(_run_cli([executable, "packs", "--json"]))}:
        raise ReleaseError("gdprguardian packs: pack FR absent / missing")
    yield "gdprguardian packs -> FR présent / present"


def _session(peer: _StdioPeer, allowed: Path, version: str, timeout_s: float) -> Iterator[str]:
    init = peer.request("initialize", {"protocolVersion": _PROTOCOL_VERSION, "capabilities": {},
                                       "clientInfo": {"name": "gdprguardian-smoke", "version": version}}, timeout_s)
    server = init.get("serverInfo", {})
    if server.get("version") != version:
        raise ReleaseError(f"serverInfo {server}: version attendue / expected {version}")
    peer.send({"method": "notifications/initialized"})
    yield f"initialize -> {server.get('name')} {server.get('version')} (MCP {init.get('protocolVersion')})"
    tools = {tool["name"] for tool in peer.request("tools/list", {}, timeout_s)["tools"]}
    if not tools >= MCP_TOOLS:
        raise ReleaseError(f"tools/list: {sorted(tools)}")
    yield f"tools/list -> {', '.join(sorted(tools))}"
    text = _tool_text(peer.request("tools/call", {"name": "anonymize_text", "arguments": {"text": SAMPLE}},
                                   timeout_s), "anonymize_text")
    if "[EMAIL_1]" not in text:
        raise ReleaseError(f"anonymize_text: {text}")
    yield f"anonymize_text -> {text}"
    page = _tool_text(peer.request("tools/call", {"name": "anonymize_file", "arguments": {
        "path": str(allowed / "clients.csv")}}, timeout_s), "anonymize_file")
    if "[EMAIL_1]" not in page:
        raise ReleaseError("anonymize_file: [EMAIL_1] absent / missing")
    yield "anonymize_file -> Markdown anonymisé / anonymised Markdown"


def smoke_mcp(command: Sequence[str], version: str, timeout_s: float = 300) -> Iterator[str]:
    """Poignée de main MCP sur stdio puis appels d'outils / MCP stdio handshake, then tool calls.

    En cas d'échec, la fin de stderr du serveur accompagne l'erreur (données fictives, aucun contenu réel).
    On failure, the tail of the server's stderr comes with the error (fictitious data, no real content).
    """
    with tempfile.TemporaryDirectory(prefix="gdprguardian-smoke-") as tmp:
        allowed = Path(tmp) / "dossiers"
        allowed.mkdir()
        (allowed / "clients.csv").write_text(SAMPLE_CSV, encoding="utf-8")
        env = {**os.environ, "GDPRGUARDIAN_ALLOWED_DIRS": str(allowed), "PYTHONIOENCODING": "utf-8"}
        log = Path(tmp) / "stderr.log"
        peer = _StdioPeer(command, env, log)
        try:
            yield from _session(peer, allowed, version, timeout_s)
        except BaseException as exc:
            peer.close()
            if not isinstance(exc, ReleaseError):
                raise
            tail = log.read_text(encoding="utf-8", errors="replace")[-3000:]
            raise ReleaseError(f"{exc}\n--- stderr du serveur / server stderr ---\n{tail}") from None
        code = peer.close()
        if code != 0:
            raise ReleaseError(f"fin de session / session end: code {code}")
        yield "fin de stdin -> arrêt propre / end of stdin -> clean exit (code 0)"


# --- interface / command line ------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release.py", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version", help="affiche la version de référence / prints the reference version")
    check_cmd = commands.add_parser("check", help="toutes les versions égales / every version field equal")
    check_cmd.add_argument("--tag", help="étiquette Git attendue, ex. v0.2.0 / expected Git tag")
    check_cmd.add_argument("--release", action="store_true", help="refuse les noms provisoires / no placeholder")
    set_cmd = commands.add_parser("set", help="réécrit chaque champ de version / rewrites every version field")
    set_cmd.add_argument("version")
    owner_cmd = commands.add_parser("set-owner", help=f"remplace / replaces {PLACEHOLDER}")
    owner_cmd.add_argument("login")
    dists_cmd = commands.add_parser("dists", help="contrôle les archives construites / checks built archives")
    dists_cmd.add_argument("folder", type=Path)
    dists_cmd.add_argument("--complete", action="store_true", help="toutes les plateformes / every platform")
    smoke_cmd = commands.add_parser("smoke", help="essai d'une installation / smoke test of an installation")
    smoke_cmd.add_argument("--gdprguardian", metavar="EXE",
                           help="commande gdprguardian à essayer / gdprguardian to test")
    engine = smoke_cmd.add_mutually_exclusive_group()
    engine.add_argument("--native", dest="native", action="store_const", const=True, help="noyau Rust attendu")
    engine.add_argument("--pure", dest="native", action="store_const", const=False, help="moteur Python attendu")
    smoke_cmd.add_argument("--version", help="version attendue (défaut : pyproject.toml) / expected version")
    smoke_cmd.add_argument("server", nargs=argparse.REMAINDER, help="-- commande du serveur MCP stdio / server")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # UTF-8 même redirigé sous Windows / UTF-8 even when piped on Windows
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        return _run(args)
    except (ReleaseError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"[!!] ÉCHEC / FAILED: {exc}", file=sys.stderr)
        return 1


def _report(problems: list[str], success: str) -> int:
    for problem in problems:
        print(f"[!!] {problem}")
    if not problems:
        print(f"[ok] {success}")
    return 1 if problems else 0


def _run(args: argparse.Namespace) -> int:
    if args.command == "version":
        print(reference_version())
        return 0
    if args.command == "check":
        version = reference_version()
        return _report(check(tag=args.tag, release=args.release),
                       f"{len(occurrences()[0])} champs de version, tous à {version} / version fields, all at "
                       f"{version}")
    if args.command == "set":
        for path in set_version(args.version):
            print(f"     {path}")
        return _report(check(), f"version {args.version} écrite partout / written everywhere")
    if args.command == "set-owner":
        for path in set_owner(args.login):
            print(f"     {path}")
        return _report([], f"compte / account {args.login}")
    if args.command == "dists":
        return _report(check_dists(args.folder, reference_version(), args.complete),
                       f"archives de {args.folder} conformes / archives OK")
    version = args.version or reference_version()
    server = args.server[1:] if args.server[:1] == ["--"] else args.server
    if not args.gdprguardian and not server:
        raise ReleaseError("rien à essayer : --gdprguardian et/ou -- commande / nothing to test")
    if args.gdprguardian:
        for line in smoke_cli(args.gdprguardian, version, args.native):
            print(f"[ok] {line}", flush=True)
    if server:
        for line in smoke_mcp(server, version):
            print(f"[ok] {line}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
