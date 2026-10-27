#!/usr/bin/env python3
"""Gardien RGPD sur le poste : anonymise un document ou un texte ici même, n'affiche que le Markdown anonymisé.

GDPR Guardian on this machine: anonymises a document or a text right here, prints ONLY the anonymised Markdown.
Rien ne quitte la machine, aucun réseau / nothing leaves the machine, no network.

    python gdprguardian_local.py contrat.pdf -o contrat.anon.md      un document / a document (PDF, DOCX, XLSX...)
    python gdprguardian_local.py --text notes.txt                     un texte UTF-8 (fichier ou « - ») / a UTF-8 text
    python gdprguardian_local.py --check                              moteur, formats / engine, formats
    python gdprguardian_local.py --setup [--pip]                      installation hors ligne / offline install

Le moteur vient des roues du dossier `wheels/` de la skill (Gardien RGPD, son noyau Rust et leurs dépendances),
installées sans réseau dans un dossier privé à la première utilisation (ou, avec --setup --pip, dans
l'environnement Python courant par `pip --no-index`). Sans roues, un Gardien RGPD déjà installé sert. The engine
comes from the skill's `wheels/` folder, installed offline into a private folder on first use (or, with
--setup --pip, into the current Python environment through `pip --no-index`). Without wheels, an installed
GDPR Guardian is used.

Bibliothèque standard seule pour l'amorçage, Python 3.11 à 3.14 / standard library only for the bootstrap.
"""

from __future__ import annotations

import argparse
import atexit
import contextlib
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import sysconfig
import tempfile
import warnings
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
WHEELS = SKILL_DIR / "wheels"
MANIFEST = WHEELS / "MANIFEST.json"
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
MIN_PYTHON = (3, 11)
PRINT_LIMIT = 100_000            # au-delà, le Markdown va dans un fichier / beyond, the Markdown goes to a file
DEFAULT_MAX_MB = 50              # même plafond que le service / same cap as the service
_MARKER = ".gdprguardian-runtime.json"
_WHEEL_NAME = re.compile(r"^(?P<name>[^-]+)-(?P<version>[^-]+)(?:-(?P<build>\d[^-]*))?-(?P<py>[^-]+)-(?P<abi>[^-]+)"
                         r"-(?P<plat>[^-]+)\.whl$")
# Formats et paquets nécessaires, pour des messages utiles / formats and the packages they need, for clear messages.
FORMAT_MODULES = {
    "PDF": ("pypdfium2",), "Word (DOCX)": ("mammoth", "defusedxml"), "HTML": ("bs4", "markdownify"),
    "Excel (XLSX, XLS, ODS)": ("python_calamine",), "CSV": (), "PowerPoint (PPTX)": ("pptx",),
    "Outlook (MSG)": ("oxmsg", "olefile"), "E-mail (EML)": (), "OpenDocument (ODT)": ("defusedxml",),
}
_EXTENSION_HINTS = {
    ".pptx": "python-pptx (pip install python-pptx), ou exportez en PDF / or export to PDF",
    ".xls": "python-calamine", ".xlsb": "python-calamine", ".ods": "python-calamine",
    ".msg": "python-oxmsg",
}


class Failure(Exception):
    """Erreur sans contenu du document / error without document content."""

    def __init__(self, message: str, code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.code = code


class NotCovered(Failure):
    """Les roues de cette copie ne couvrent pas cet interpréteur / this copy's wheels do not cover this interpreter.

    Cas typique : l'archive Linux téléversée dans claude.ai, synchronisée vers Claude Code sous Windows ou macOS.
    Typical case: the Linux archive uploaded to claude.ai, synced into Claude Code on Windows or macOS.
    """

    def __init__(self, manifest: Mapping[str, Any]) -> None:
        covered = ", ".join(manifest.get("platforms", [])) or "?"
        pythons = ", ".join(manifest.get("pythons", [])) or "?"
        major, minor, _ = _interpreter()
        here = f"Python {major}.{minor}, {_machine()}, {sysconfig.get_platform()}"
        super().__init__(
            f"plateforme non couverte par cette archive / platform not covered by this archive ({here}) ; "
            f"couvertes / covered: {covered}, Python {pythons}. Utilisez l'outil local anonymize_file (plugin "
            f"gdprguardian), l'autre archive gdprguardian-local (Windows x64 et macOS Apple Silicon : "
            f"gdprguardian-local-windows-macos.zip ; Linux : gdprguardian-local.zip), ou pip install "
            f"\"gdprguardian[local]\" dans ce Python / use the local anonymize_file tool (gdprguardian plugin), the "
            f"other gdprguardian-local archive, or pip install \"gdprguardian[local]\" into this Python")


# --- Choix des roues pour cet interpréteur / picking the wheels for this interpreter ---------------------------


def _system() -> str:
    return sys.platform


def _glibc() -> tuple[int, int] | None:
    try:
        raw = os.confstr("CS_GNU_LIBC_VERSION") or ""
    except (AttributeError, OSError, ValueError):
        return None
    match = re.fullmatch(r"glibc (\d+)\.(\d+).*", raw)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _mac_release() -> tuple[int, int]:
    major, minor = [*(int(part) for part in re.findall(r"\d+", platform.mac_ver()[0] or "0")[:2]), 0, 0][:2]
    return major, minor


def _windows_platform() -> str:
    """Plateforme de l'interpréteur sous Windows (« win-amd64 ») / the interpreter's own platform on Windows."""
    return sysconfig.get_platform()


def _machine() -> str:
    if _system() == "win32":
        # L'interpréteur lui-même, pas PROCESSOR_ARCHITECTURE (absente d'un environnement minimal, d'où un
        # platform.machine() vide) ; un Python x64 émulé sur ARM prend aussi les roues x64. The interpreter itself,
        # not PROCESSOR_ARCHITECTURE (missing from a minimal environment, leaving platform.machine() empty).
        plat = _windows_platform().lower()
        return {"win-amd64": "x86_64", "win-arm64": "arm64", "win32": "x86"}.get(plat, plat)
    machine = platform.machine().lower()
    linux = _system().startswith("linux")
    return {"amd64": "x86_64", "x64": "x86_64", "arm64": "aarch64" if linux else "arm64",
            "aarch64": "aarch64" if linux else "arm64"}.get(machine, machine)


def _platform_rank(tag: str) -> int | None:
    """Rang d'une étiquette de plateforme (petit = meilleur), None si incompatible / platform tag rank or None."""
    if tag == "any":
        return 100
    machine, system = _machine(), _system()
    if system == "win32":
        wanted = {"x86_64": "win_amd64", "arm64": "win_arm64", "x86": "win32"}.get(machine)
        return 0 if tag == wanted else None
    if system.startswith("linux"):
        glibc = _glibc()
        legacy = {"manylinux1": (2, 5), "manylinux2010": (2, 12), "manylinux2014": (2, 17)}
        match = re.fullmatch(r"(manylinux1|manylinux2010|manylinux2014)_(\w+)", tag)
        if match:
            needed, arch = legacy[match.group(1)], match.group(2)
        else:
            match = re.fullmatch(r"manylinux_(\d+)_(\d+)_(\w+)", tag)
            if not match:
                return None  # musllinux, linux_x86_64 : non fournis / not shipped
            needed, arch = (int(match.group(1)), int(match.group(2))), match.group(3)
        if glibc is None or arch != machine or needed > glibc:
            return None
        return 1
    if system == "darwin":
        match = re.fullmatch(r"macosx_(\d+)_(\d+)_(\w+)", tag)
        if not match:
            return None
        release = _mac_release()
        needed = (int(match.group(1)), int(match.group(2)))
        arch = match.group(3)
        ok_arch = arch == machine or arch == "universal2" or (arch == "intel" and machine == "x86_64")
        if not ok_arch or (release[0] < 11 and needed > release) or (release[0] >= 11 and needed[0] > release[0]):
            return None
        return 0 if arch == machine else 2
    return None


def _interpreter() -> tuple[int, int, bool]:
    free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    return sys.version_info[0], sys.version_info[1], free_threaded


def wheel_rank(filename: str) -> int | None:
    """Rang d'une roue pour cet interpréteur (petit = meilleur), None si incompatible / wheel rank or None."""
    match = _WHEEL_NAME.match(filename)
    if not match:
        return None
    major, minor, free_threaded = _interpreter()
    cpython = sys.implementation.name == "cpython"
    best: int | None = None
    for py in match["py"].split("."):
        for abi in match["abi"].split("."):
            if abi == "none":
                py_ok = py in ("py3", f"py{major}{minor}") or (py == f"cp{major}{minor}" and cpython)
                rank = 30
            elif abi == "abi3":
                found = re.fullmatch(r"cp(\d)(\d+)", py)
                py_ok = (cpython and not free_threaded and found is not None and int(found.group(1)) == major
                         and int(found.group(2)) <= minor)
                rank = 20 + (minor - int(found.group(2)) if found else 0)
            else:
                own_abi = f"cp{major}{minor}" + ("t" if free_threaded else "")
                py_ok = cpython and py == f"cp{major}{minor}" and abi == own_abi
                rank = 10
            if not py_ok:
                continue
            for plat in match["plat"].split("."):
                platform_rank = _platform_rank(plat)
                if platform_rank is not None:
                    total = rank * 1000 + platform_rank
                    best = total if best is None else min(best, total)
    return best


def _project(filename: str) -> str:
    match = _WHEEL_NAME.match(filename)
    return re.sub(r"[-_.]+", "-", match["name"]).lower() if match else filename


def select_wheels(files: Iterable[str]) -> dict[str, str]:
    """Meilleure roue compatible par projet / best compatible wheel per project."""
    chosen: dict[str, tuple[int, str]] = {}
    for name in sorted(files):
        rank = wheel_rank(name)
        if rank is None:
            continue
        project = _project(name)
        if project not in chosen or rank < chosen[project][0]:
            chosen[project] = (rank, name)
    return {project: name for project, (_, name) in sorted(chosen.items())}


def _interpreter_tag() -> str:
    major, minor, free_threaded = _interpreter()
    return f"cp{major}{minor}{'t' if free_threaded else ''}"


def _platform_tag() -> str:
    return re.sub(r"[^A-Za-z0-9_.]+", "_", sysconfig.get_platform())


# --- Dossier privé du moteur / private engine folder ---------------------------------------------------------------


def load_manifest() -> dict[str, Any] | None:
    if not MANIFEST.is_file():
        return None
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Failure("wheels/MANIFEST.json illisible : retéléchargez la skill / unreadable manifest: download the "
                      "skill again") from None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("wheels"), dict):
        raise Failure("wheels/MANIFEST.json invalide / invalid manifest")
    return manifest


def _private_dir(path: Path) -> bool:
    """Dossier à soi, non modifiable par d'autres (POSIX) / own folder, not writable by others (POSIX)."""
    if os.name != "posix":
        return True
    info = path.stat()
    return info.st_uid == os.getuid() and not info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)


def cache_root(env: Mapping[str, str]) -> Path:
    """Dossier de cache de l'utilisateur ; à défaut, un dossier temporaire privé / user cache, else a private temp."""
    explicit = env.get("GDPRGUARDIAN_SKILL_CACHE", "").strip()
    if explicit:
        base = Path(explicit).expanduser()
    elif sys.platform == "win32":
        base = Path(env.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "gdprguardian" / "skill"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches" / "gdprguardian" / "skill"
    else:
        base = Path(env.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "gdprguardian" / "skill"
    if _usable(base):
        return base
    # Dossier personnel non accessible en écriture (bac à sable) : un dossier temporaire à soi, le même à chaque
    # appel (sinon 26 Mo de plus par appel). Home not writable (sandbox): one private temporary folder per user,
    # reused by every run (otherwise 26 MB more per run).
    owner = os.getuid() if hasattr(os, "getuid") else re.sub(r"\W+", "_", env.get("USERNAME", "") or "user")
    shared = Path(tempfile.gettempdir()) / f"gdprguardian-skill-{owner}"
    if _usable(shared):
        return shared
    # Dossier partagé pris par un autre utilisateur : dossier neuf, effacé à la sortie / squatted: a fresh folder,
    # removed at exit.
    fresh = Path(tempfile.mkdtemp(prefix="gdprguardian-skill-"))
    atexit.register(shutil.rmtree, fresh, True)
    return fresh


def _usable(base: Path) -> bool:
    """Dossier créé au besoin (0700), inscriptible, à soi et fermé aux autres, pas un lien symbolique.

    Folder created if needed (0700), writable, owned by this user and closed to others, not a symbolic link.
    """
    try:
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        if base.is_symlink() or not base.is_dir() or not _private_dir(base):
            return False
        probe = base / f".probe-{os.getpid()}"
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _extract(wheel: Path, target: Path) -> None:
    """Installe une roue par simple extraction (purelib et platlib), sans chemin hors du dossier.

    Installs a wheel by plain extraction (purelib and platlib), with no path outside the folder.
    """
    with zipfile.ZipFile(wheel) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            if not parts or info.filename.startswith(("/", "\\")) or ".." in parts or ":" in parts[0]:
                raise Failure(f"roue invalide / invalid wheel: {wheel.name}")
            if parts[0].endswith(".data"):
                if len(parts) < 3 or parts[1] not in ("purelib", "platlib"):
                    continue  # scripts, en-têtes, données : inutiles ici / scripts, headers, data: not needed
                parts = parts[2:]
            destination = target.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("wb") as sink:
                shutil.copyfileobj(source, sink, 1 << 20)


def ensure_runtime(manifest: dict[str, Any], env: Mapping[str, str]) -> tuple[Path, dict[str, str]]:
    """Dossier privé prêt (extrait une seule fois, vérifié par empreintes) / private folder, extracted once."""
    selected = select_wheels(manifest["wheels"])
    if "ahocorasick-rs" not in selected or "gdprguardian" not in selected:
        raise NotCovered(manifest)
    digest = hashlib.sha256(json.dumps(selected, sort_keys=True).encode()
                            + json.dumps([manifest["wheels"][name] for name in selected.values()]).encode()).hexdigest()
    root = cache_root(env)
    final = root / f"{manifest.get('gdprguardian', 'x')}-{digest[:12]}-{_interpreter_tag()}-{_platform_tag()}"
    marker = final / _MARKER
    if marker.is_file():
        return final, selected
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=root))
    try:
        for name in selected.values():
            wheel = WHEELS / name
            if not wheel.is_file() or _sha256(wheel) != manifest["wheels"][name]:
                raise Failure(f"roue absente ou altérée / missing or altered wheel: {name} ; retéléchargez la skill / "
                              f"download the skill again")
            _extract(wheel, staging)
        (staging / _MARKER).write_text(json.dumps({"wheels": selected}, indent=1), encoding="utf-8")
        try:
            os.replace(staging, final)
        except OSError:
            if not marker.is_file():  # autre processus plus rapide ? sinon erreur réelle / raced, or a real error
                raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return final, selected


def _installed_version() -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover
        return None
    try:
        return version("gdprguardian")
    except PackageNotFoundError:
        return None


def activate(env: Mapping[str, str]) -> dict[str, Any]:
    """Rend `gdprguardian` importable et dit d'où il vient / makes `gdprguardian` importable, says from where."""
    if sys.version_info[:2] < MIN_PYTHON:
        raise Failure(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} ou plus requis (trouvé {sys.version_info[0]}."
                      f"{sys.version_info[1]}) / Python 3.11+ required", EXIT_USAGE)
    manifest = load_manifest()
    installed = _installed_version()
    # GDPRGUARDIAN_SKILL_RUNTIME=bundled : roues de la skill même si la version est déjà installée (essais).
    # GDPRGUARDIAN_SKILL_RUNTIME=bundled: the skill's wheels even when that version is installed (tests).
    forced = env.get("GDPRGUARDIAN_SKILL_RUNTIME", "").strip().lower() == "bundled"
    if manifest is not None and (forced or installed != manifest.get("gdprguardian")):
        try:
            path, selected = ensure_runtime(manifest, env)
        except NotCovered:
            if installed is None or forced:
                raise
            # Roues d'une autre plateforme, mais Gardien RGPD installé dans ce Python : il sert.
            # Wheels for another platform, but GDPR Guardian is installed in this Python: use it.
            return {"source": "environment", "version": installed,
                    "note": "roues de l'archive pour une autre plateforme / archive wheels for another platform"}
        sys.path.insert(0, str(path))
        return {"source": "bundled", "path": str(path), "wheels": sorted(selected.values())}
    if installed is None:
        raise Failure("moteur absent : cette copie de la skill n'a pas de roues. Prenez l'archive gdprguardian-local "
                      "(skills/ du dépôt), installez \"gdprguardian[local]\", ou utilisez l'outil MCP local "
                      "anonymize_file / engine missing: this copy of the skill has no wheels. Use the "
                      "gdprguardian-local archive, install \"gdprguardian[local]\", or the local MCP tool "
                      "anonymize_file")
    return {"source": "environment", "version": installed}


def _pip_install(manifest: dict[str, Any]) -> int:
    """Installe les roues choisies dans l'environnement courant, sans index / installs them here, no index."""
    selected = select_wheels(manifest["wheels"])
    if "gdprguardian" not in selected or "ahocorasick-rs" not in selected:
        raise NotCovered(manifest)
    for name in selected.values():
        if _sha256(WHEELS / name) != manifest["wheels"][name]:
            raise Failure(f"roue altérée / altered wheel: {name}")
    command = [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps", "--disable-pip-version-check",
               *(str(WHEELS / name) for name in selected.values())]
    completed = subprocess.run(command, check=False)
    return EXIT_OK if completed.returncode == 0 else EXIT_ERROR


# --- Anonymisation / anonymisation ---------------------------------------------------------------------------------


def _engine_report() -> dict[str, Any]:
    from gdprguardian import __version__, _native

    return {"gdprguardian": __version__, "engine": "rust" if _native.available() else "python"}


def _import_engine() -> list[str]:
    """Importe le moteur ; avertissements (noyau écarté…) rendus à part / imports the engine, warnings returned."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import gdprguardian  # noqa: F401
        from gdprguardian import _native  # noqa: F401
    return ["".join(ch for ch in str(item.message) if ch.isprintable())[:300] for item in caught]


def load_rules(explicit: str | None, env: Mapping[str, str]) -> Any:
    """Règles de l'organisation (JSON ou TOML, de confiance en local) : --rules, GDPRGUARDIAN_RULES, sinon
    .gdprguardian/rules.json ou rules.toml du projet. The organisation's rules (trusted locally)."""
    from gdprguardian.custom import RuleError
    from gdprguardian.custom import load_rules as load

    candidate = explicit or env.get("GDPRGUARDIAN_RULES", "").strip() or None
    paths = [Path(candidate)] if candidate else [Path(".gdprguardian") / "rules.json",
                                                 Path(".gdprguardian") / "rules.toml"]
    path = next((item for item in paths if item.is_file()), None)
    if path is None:
        if candidate:
            raise Failure("fichier de règles introuvable / rules file not found", EXIT_USAGE)
        return None
    try:
        return load(path)
    except (OSError, UnicodeDecodeError, ValueError, RuleError) as exc:
        message = str(exc) if isinstance(exc, RuleError) else "JSON ou TOML attendu / JSON or TOML expected"
        raise Failure(f"règles invalides / invalid rules: {message}"[:300], EXIT_USAGE) from None


def build_anonymizer(args: argparse.Namespace, env: Mapping[str, str]) -> Any:
    from gdprguardian.engine import Anonymizer
    from gdprguardian.server.options import AnonymizeOptions

    try:
        # Sans --mode : le mode fort, défaut du moteur ; --profile n'est plus qu'un alias déprécié.
        # Without --mode: the engine's default fort mode; --profile is only a deprecated alias.
        options = AnonymizeOptions.build(args.countries, args.profile, args.label_language, None, args.explain,
                                         mode=args.mode, disable=args.disable)
    except ValueError as exc:
        raise Failure(str(exc), EXIT_USAGE) from None
    rules = load_rules(args.rules, env)
    if rules is None:
        return options.anonymizer()
    extra = {} if options.profile is None else {"profile": options.profile}
    return Anonymizer(countries=options.countries, mode=options.mode, disable=options.disable,
                      label_language=options.label_language, rules=rules, explain=options.explain, **extra)


def anonymize_file(path: Path, anonymizer: Any, *, max_mb: float, timeout: float, in_process: bool
                   ) -> tuple[str, dict[str, Any]]:
    from gdprguardian import documents
    from gdprguardian.documents import DocumentError, DocumentOptions
    from gdprguardian.server.errors import from_document_error
    from gdprguardian.server.filenames import neutral_filename

    if not path.is_file():
        raise Failure("fichier introuvable / file not found", EXIT_USAGE)
    limit = int(max_mb * 1024 * 1024)
    size = path.stat().st_size
    if size > limit:
        raise Failure(f"fichier trop volumineux ({size / 2**20:.1f} Mo > {max_mb:g} Mo) : relancez avec --max-mb ou "
                      f"découpez-le / file too large: rerun with --max-mb or split it", EXIT_USAGE)
    if _is_powerpoint(path) and importlib.util.find_spec("pptx") is None:
        # Sinon « document_error » sans explication, qui pourrait inviter à ouvrir le fichier pour « vérifier ».
        # Otherwise an unexplained "document_error", which could invite opening the file "to check".
        raise Failure("unsupported_format: PowerPoint exige python-pptx, absent ici (trop lourd pour l'archive) ; "
                      "demandez un export PDF, n'ouvrez jamais le fichier / PowerPoint needs python-pptx, missing "
                      "here (too heavy for the archive); ask for a PDF export, never open the file")
    options = DocumentOptions(max_bytes=limit, timeout_s=timeout, sandbox=not in_process)
    hint = _EXTENSION_HINTS.get(path.suffix.lower())
    try:
        # Seule l'extension sert : le nom n'entre jamais dans le résultat / only the extension is used.
        result = documents.anonymize_document(path.read_bytes(), neutral_filename(path.name), anonymizer, options)
    except DocumentError as exc:
        if type(exc).__name__ == "WorkerStartError":
            raise Failure("le bac à sable de conversion ne démarre pas ici ; relancez avec --in-process (conversion "
                          "dans ce processus) / the conversion sandbox cannot start here; rerun with --in-process") \
                from None
        error = from_document_error(exc)
        extra = f" ; composant requis / component needed: {hint}" if hint and error.code == "unsupported_format" else ""
        raise Failure(f"{error.code}: {error.message}{extra}") from None
    except (ImportError, NotImplementedError):
        raise Failure("convertisseur indisponible pour ce format / converter unavailable for this format"
                      + (f" ; composant requis / component needed: {hint}" if hint else "")) from None
    report = dict(result.report)
    report.update({"kind": result.kind, "pages": result.pages, "conversion_warnings": len(result.warnings)})
    return result.markdown, report


_POWERPOINT = frozenset({".pptx", ".pptm", ".ppsx", ".potx"})


def _is_powerpoint(path: Path) -> bool:
    """PowerPoint par l'extension ou par le répertoire du zip (noms des parties seulement, jamais leur contenu).

    PowerPoint by extension or by the zip directory (part names only, never their content).
    """
    if path.suffix.lower() in _POWERPOINT:
        return True
    try:
        with zipfile.ZipFile(path) as archive:
            return "ppt/presentation.xml" in archive.namelist()
    except (OSError, zipfile.BadZipFile, ValueError):
        return False


class Output:
    """Sortie standard pour un petit résultat, fichier sinon / stdout for a small result, else a file."""

    def __init__(self, target: Path | None, source: Path | None) -> None:
        self.target = target
        self.source = source

    def check(self) -> None:
        target, source = self.target, self.source
        if target is not None and source is not None and target.exists() and target.resolve() == source.resolve():
            raise Failure("la sortie écraserait l'original / output would overwrite the original", EXIT_USAGE)

    def emit(self, markdown: str) -> None:
        target, automatic = self.target, False
        if target is None and len(markdown) > PRINT_LIMIT:
            fd, name = tempfile.mkstemp(prefix="gdprguardian-", suffix=".anon.md")
            os.close(fd)
            target, automatic = Path(name), True
        if target is None:
            sys.stdout.buffer.write(markdown.encode("utf-8"))
            sys.stdout.buffer.flush()
            return
        part = target.with_name(target.name + ".part")
        part.write_text(markdown, encoding="utf-8", newline="")
        os.replace(part, target)
        notice = (f"[gdprguardian] Markdown anonymisé écrit / anonymised Markdown written: {target} "
                  f"({len(markdown)} caractères/chars)")
        if automatic:
            print(notice + " ; lisez-le par parties / read it in parts")
        else:
            print(f"gdprguardian: {notice}", file=sys.stderr)


def _read_text(source: str) -> str:
    try:
        raw = sys.stdin.buffer.read() if source == "-" else Path(source).read_bytes()
    except OSError:
        raise Failure("texte illisible / unreadable text", EXIT_USAGE) from None
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Failure("texte : UTF-8 attendu (sinon, anonymisez le fichier) / text: UTF-8 expected (else, anonymise "
                      "the file)", EXIT_USAGE) from None


def _summary(report: dict[str, Any], engine: dict[str, Any], notes: list[str]) -> None:
    # `explain` : règle et raison de chaque balise, jamais la valeur / rule and reason of each placeholder, never value.
    summary = {k: report[k] for k in ("entities", "total_replaced", "countries", "notice", "warnings", "explain",
                                      "kind", "pages", "conversion_warnings") if k in report}
    summary.update(engine)
    if notes:
        summary["engine_notes"] = notes
    sys.stderr.buffer.write((json.dumps(summary, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stderr.buffer.flush()


def _formats() -> dict[str, bool]:
    return {label: all(importlib.util.find_spec(module) is not None for module in modules)
            for label, modules in FORMAT_MODULES.items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    parser.add_argument("file", nargs="?", help="document à anonymiser / document to anonymise")
    parser.add_argument("--text", metavar="SOURCE",
                        help="texte UTF-8 : un fichier, ou « - » pour l'entrée standard / UTF-8 text: a file, or '-'")
    parser.add_argument("--countries", default="FR",
                        help="packs pays, ex. FR (défaut), FR,BE, all, auto (expérimental) / country packs")
    parser.add_argument("--mode", choices=("fort", "essentiel", "personnalise", "strong", "essential", "custom"),
                        help="fort (défaut : tout ce qu'on peut, codes compris), essentiel (codes métier lisibles), "
                             "personnalise (le fort moins --disable) / fort (default), essentiel, personnalise")
    parser.add_argument("--disable", help="catégories laissées en clair, séparées par des virgules (mode "
                                          "personnalise ; jamais secrets) / categories left in clear (custom mode)")
    parser.add_argument("--profile", choices=("fast", "standard", "strict"),
                        help="ancien réglage, déprécié : standard = essentiel, strict = fort / deprecated")
    parser.add_argument("--label-language", default="fr", choices=("fr", "en", "auto"))
    parser.add_argument("--rules", help="règles de l'organisation (JSON ou TOML) ; défaut : GDPRGUARDIAN_RULES ou "
                                        ".gdprguardian/rules.json / organisation rules")
    parser.add_argument("--explain", action="store_true",
                        help="règle et raison de chaque balise, dans le rapport sur stderr / rule and reason of each "
                             "placeholder, in the report on stderr")
    parser.add_argument("-o", "--output", help="écrire le Markdown dans ce fichier / write the Markdown to a file")
    parser.add_argument("--report", action="store_true", help="résumé du rapport sur stderr / report on stderr")
    parser.add_argument("--max-mb", type=float, default=DEFAULT_MAX_MB, help="taille maximale / maximum size (MB)")
    parser.add_argument("--timeout", type=float, default=300.0, help="délai de conversion / conversion timeout (s)")
    parser.add_argument("--in-process", action="store_true",
                        help="conversion dans ce processus (bac à sable sans sous-processus) / conversion in-process")
    parser.add_argument("--check", action="store_true", help="moteur et formats disponibles / engine and formats")
    parser.add_argument("--setup", action="store_true", help="installe le moteur sans réseau / offline install")
    parser.add_argument("--pip", action="store_true",
                        help="avec --setup : pip --no-index dans l'environnement courant / into this environment")
    return parser


def utf8_streams() -> None:
    """Sorties en UTF-8 même redirigées sous Windows (sinon cp1252) / UTF-8 output even when piped on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):
                reconfigure(encoding="utf-8", errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.setup and args.pip:
            manifest = load_manifest()
            if manifest is None:
                raise Failure("aucune roue dans cette copie de la skill / no wheels in this copy of the skill")
            return _pip_install(manifest)
        origin = activate(os.environ)
        notes = _import_engine()
        if args.setup or args.check:
            info = {**origin, **_engine_report(), "python": platform.python_version(),
                    "platform": sysconfig.get_platform()}
            if notes:
                info["engine_notes"] = notes
            if args.check:
                info["formats"] = _formats()
            print(json.dumps(info, ensure_ascii=False, indent=1))
            return EXIT_OK
        if (args.file is None) == (args.text is None):
            parser.error("un document OU --text / a document OR --text")
        source = Path(args.file) if args.file is not None else None
        output = Output(Path(args.output) if args.output else None, source)
        output.check()
        anonymizer = build_anonymizer(args, os.environ)
        if source is None:
            result = anonymizer.anonymize(_read_text(args.text))
            markdown, report = result.text, dict(result.report)
        else:
            markdown, report = anonymize_file(source, anonymizer, max_mb=args.max_mb, timeout=args.timeout,
                                              in_process=args.in_process)
        output.emit(markdown)
    except Failure as failure:
        print(f"gdprguardian: {failure}", file=sys.stderr)
        return failure.code
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        # Jamais de trace ni de message tiers : il pourrait citer le document / never a traceback or third-party text.
        print(f"gdprguardian: échec / failed ({type(exc).__name__})", file=sys.stderr)
        return EXIT_ERROR
    if args.report or args.explain:
        _summary(report, _engine_report(), notes)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
