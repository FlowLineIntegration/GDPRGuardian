"""Archives des skills Claude, prêtes à téléverser et reproductibles / reproducible, ready-to-upload skill archives.

    python tools/build_skills.py build [--wheelhouse dist/<version>]    construit skills/*.zip / builds skills/*.zip
    python tools/build_skills.py check                                  archives conformes aux sources (sans réseau)
    python tools/build_skills.py lock                                   réécrit skills/wheels.lock.json (PyPI)
    python tools/build_skills.py notices [--wheelhouse dist/<version>]  réécrit skills/THIRD_PARTY_NOTICES.md

Trois archives, chacune avec le dossier de la skill à sa racine (ce qu'attend claude.ai) / three archives, each with
the skill folder at its root (what claude.ai expects):

- `gdprguardian-online.zip` : la skill légère (service en ligne avec clé API, MCP ou API REST) / the light skill;
- `gdprguardian-local.zip` : la skill lourde, moteur complet pour Linux x86_64 et aarch64 (bac à sable de claude.ai
  et de la conversation de Claude Desktop, Linux, WSL) / the heavy skill, full engine for Linux;
- `gdprguardian-local-windows-macos.zip` : la même skill lourde, roues Windows x64 et macOS Apple Silicon (Claude Code
  sur le poste) / the same heavy skill, Windows x64 and Apple-silicon macOS wheels.

Chaque archive porte LICENSE (MIT) ; les archives lourdes portent aussi THIRD_PARTY_NOTICES.md (licences des roues et
des crates Rust liées au noyau). Each archive carries LICENSE; the heavy ones also carry THIRD_PARTY_NOTICES.md.

Reproductible à partir des mêmes roues : entrées triées, date fixe, droits fixes, aucune compression (des roues sont
déjà compressées ; ainsi aucune version de zlib n'entre dans le résultat), fins de ligne LF pour les textes. Roues
tierces épinglées par leur empreinte dans skills/wheels.lock.json ; roues de Gardien RGPD prises dans le dossier de
la version (dist/<version>/), la roue pure devant correspondre aux sources et chaque noyau porter le contrat des
sources (vérifié sur sa plateforme, consigné dans skills/core_contracts.json). Reproducible from the same wheels:
sorted entries, fixed date and modes, no compression, LF line endings. Third-party wheels pinned by digest; GDPR
Guardian's wheels come from dist/<version>/, the pure one matching the sources and each core carrying the sources'
contract (verified on its platform, recorded in skills/core_contracts.json). Bibliothèque standard seule.
"""

from __future__ import annotations

import argparse
import email.parser
import hashlib
import io
import json
import platform
import re
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
LOCK = SKILLS / "wheels.lock.json"
NOTICES = SKILLS / "THIRD_PARTY_NOTICES.md"
CONTRACTS = SKILLS / "core_contracts.json"
LICENSE = ROOT / "LICENSE"
SOURCE = ROOT / "src" / "gdprguardian"
ONLINE = ROOT / "integrations" / "claude" / "plugin-online" / "skills" / "gdprguardian-online"
LOCAL = ROOT / "integrations" / "claude" / "plugin" / "skills" / "gdprguardian-local"
CACHE = ROOT / "build" / "skills" / "wheels"
REGISTRY = Path.home() / ".cargo" / "registry" / "src"
# Limite de claude.ai et de l'API pour une skill : 30 Mo, fichiers décompressés / upload limit, uncompressed files.
UPLOAD_LIMIT = 30_000_000
PYTHONS = ("cp311", "cp312", "cp313", "cp314")
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
TEXT_SUFFIXES = frozenset({".md", ".py", ".txt", ".json", ".toml", ".tsv"})
_SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

# Dépendances tierces de la skill lourde, aux versions essayées dans le dépôt : moteur (ahocorasick-rs), téléphones,
# convertisseurs PDF, Word, HTML, tableurs, courriels. Ni lxml ni Pillow (python-pptx) : trop lourds pour la limite de
# 30 Mo ; un python-pptx déjà présent (bac à sable de claude.ai) sert. Third-party dependencies of the heavy skill,
# at the versions tested in the repository; no lxml or Pillow (python-pptx): too heavy for the 30 MB limit.
PINS = {
    "ahocorasick-rs": "1.0.3", "pypdfium2": "5.14.0", "python-calamine": "0.9.0", "pypdf": "6.21.2",
    "mammoth": "1.13.0", "cobble": "0.1.4", "markdownify": "1.2.3", "beautifulsoup4": "4.15.0",
    "soupsieve": "3.0.4", "six": "1.17.0", "typing-extensions": "4.16.0", "defusedxml": "0.7.1",
    "charset-normalizer": "3.5.2", "olefile": "0.47", "python-oxmsg": "0.0.2", "click": "8.5.0",
    "colorama": "0.4.6", "phonenumberslite": "9.0.41",
}
NATIVE = frozenset({"ahocorasick-rs", "pypdfium2", "python-calamine"})
# Paquets demandés par wheels/requirements.txt (pip résout le reste dans wheels/) / top-level requirements.
TOP_LEVEL = ("phonenumberslite", "pypdf", "pypdfium2", "mammoth", "markdownify", "beautifulsoup4",
             "python-calamine", "charset-normalizer", "defusedxml", "olefile", "python-oxmsg")
PLATFORMS = {
    "linux_x86_64": re.compile(r"manylinux(?:1|2010|2014|_\d+_\d+)_x86_64"),
    "linux_aarch64": re.compile(r"manylinux(?:2014|_\d+_\d+)_aarch64"),
    "win_amd64": re.compile(r"win_amd64"),
    "macos_arm64": re.compile(r"macosx_\d+_\d+_(?:arm64|universal2)"),
}


@dataclass(frozen=True, slots=True)
class Archive:
    """Une archive : nom du fichier, skill, dossier source, plateformes des roues / one archive."""

    filename: str
    skill: str
    source: Path
    platforms: tuple[str, ...] = ()


ARCHIVES = (
    Archive("gdprguardian-online.zip", "gdprguardian-online", ONLINE),
    Archive("gdprguardian-local.zip", "gdprguardian-local", LOCAL, ("linux_x86_64", "linux_aarch64")),
    Archive("gdprguardian-local-windows-macos.zip", "gdprguardian-local", LOCAL, ("win_amd64", "macos_arm64")),
)


class BuildError(Exception):
    """Erreur affichée telle quelle / error printed as is."""


def version(root: Path = ROOT) -> str:
    with (root / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def normalized(path: Path) -> bytes:
    """Octets d'un fichier, fins de ligne LF pour un texte / a file's bytes, LF line endings for text."""
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n") if path.suffix.lower() in TEXT_SUFFIXES else data


def text_bytes(path: Path) -> bytes:
    """Octets d'un texte sans suffixe connu (LICENSE), fins de ligne LF / a text file's bytes, LF line endings."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def source_files(folder: Path) -> list[Path]:
    """Fichiers d'une skill, sans caches ni fichiers cachés / a skill's files, no caches or hidden files."""
    return sorted(path for path in folder.rglob("*")
                  if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo")
                  and not any(part.startswith(".") for part in path.relative_to(folder).parts))


def frontmatter(text: str) -> dict[str, str]:
    """Champs simples du bloc YAML de SKILL.md (une ligne par champ) / simple SKILL.md frontmatter fields."""
    if not text.startswith("---\n"):
        raise BuildError("SKILL.md : bloc --- attendu en tête / frontmatter expected")
    block = text[4:text.index("\n---\n", 4)]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        match = re.match(r"([a-z][a-z-]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def check_skill(folder: Path, name: str) -> list[str]:
    """Règles de claude.ai et de la spécification Agent Skills / claude.ai and Agent Skills rules."""
    try:
        fields = frontmatter((folder / "SKILL.md").read_text(encoding="utf-8").replace("\r\n", "\n"))
    except (OSError, ValueError, BuildError) as exc:
        return [f"{folder.name}: {exc}"]
    problems = []
    if fields.get("name") != name or folder.name != name or not _SKILL_NAME.fullmatch(name) or len(name) > 64:
        problems.append(f"{name}: name, dossier et règles de nom / name, folder and naming rules")
    if any(word in name for word in ("anthropic", "claude")):
        problems.append(f"{name}: mot réservé dans le nom / reserved word in the name")
    description = fields.get("description", "")
    if not description or len(description) > 1024 or "<" in description or ">" in description:
        problems.append(f"{name}: description vide, trop longue (> 1024) ou avec < > / bad description")
    return problems


# --- Roues / wheels ------------------------------------------------------------------------------------------------

_WHEEL = re.compile(r"^(?P<name>[^-]+)-(?P<version>[^-]+)(?:-\d[^-]*)?-(?P<py>[^-]+)-(?P<abi>[^-]+)"
                    r"-(?P<plat>[^-]+)\.whl$")


def project_of(filename: str) -> str:
    match = _WHEEL.match(filename)
    if match is None:
        raise BuildError(f"nom de roue invalide / invalid wheel name: {filename}")
    return re.sub(r"[-_.]+", "-", match["name"]).lower()


def _fits(filename: str, python: str) -> bool:
    """La roue convient-elle à cette version de CPython (non « free-threaded ») ? / fits this CPython version?"""
    match = _WHEEL.match(filename)
    assert match is not None
    minor = int(python[3:])
    for py in match["py"].split("."):
        for abi in match["abi"].split("."):
            if abi == "none" and py in ("py3", "py2"):
                return True
            if abi == "abi3" and (found := re.fullmatch(r"cp3(\d+)", py)) and int(found.group(1)) <= minor:
                return True
            if abi == python and py == python:
                return True
    return False


def _glibc_or_macos(filename: str) -> tuple[int, int]:
    """Version minimale de glibc ou de macOS exigée, pour préférer la plus basse / lowest requirement first."""
    match = re.search(r"manylinux_(\d+)_(\d+)|macosx_(\d+)_(\d+)", filename)
    if match is None:
        return (2, 17) if "manylinux2014" in filename else (0, 0)
    numbers = [int(group) for group in match.groups() if group is not None]
    return numbers[0], numbers[1]


def pick(files: Sequence[dict[str, Any]], project: str, platform: str | None) -> list[dict[str, Any]]:
    """Roues d'un projet pour une plateforme (toutes versions de Python), ou la roue pure / wheels of a project."""
    if platform is None:
        pure = [entry for entry in files if entry["filename"].endswith(("-py3-none-any.whl", "-py2.py3-none-any.whl"))]
        if not pure:
            raise BuildError(f"{project}: aucune roue pure / no pure wheel")
        return [min(pure, key=lambda entry: entry["filename"])]
    rule = PLATFORMS[platform]
    chosen: dict[str, dict[str, Any]] = {}
    for python in PYTHONS:
        candidates = [entry for entry in files if rule.search(entry["filename"]) and _fits(entry["filename"], python)]
        if platform == "macos_arm64":
            # Roue arm64 dédiée plutôt qu'universelle (deux fois plus lourde) / dedicated arm64 over universal2.
            candidates = [c for c in candidates if "universal2" not in c["filename"]] or candidates
        if not candidates:
            raise BuildError(f"{project}: aucune roue pour / no wheel for {platform} {python}")
        best = min(candidates, key=lambda entry: (_glibc_or_macos(entry["filename"]), entry["filename"]))
        chosen[best["filename"]] = best
    return [chosen[name] for name in sorted(chosen)]


def lock(root: Path = ROOT) -> dict[str, Any]:
    """Interroge PyPI et rend le verrou des roues tierces / queries PyPI, returns the lock of third-party wheels."""
    wheels: dict[str, dict[str, Any]] = {}
    for project, pinned in sorted(PINS.items()):
        with urllib.request.urlopen(f"https://pypi.org/pypi/{project}/{pinned}/json", timeout=60) as response:
            data = json.load(response)
        files = [entry for entry in data["urls"] if entry["filename"].endswith(".whl") and not entry.get("yanked")]
        for archive in ARCHIVES:
            if not archive.platforms:
                continue
            selected = (pick(files, project, None) if project not in NATIVE else
                        [entry for platform in archive.platforms for entry in pick(files, project, platform)])
            for entry in selected:
                row = wheels.setdefault(entry["filename"], {
                    "project": project, "version": pinned, "file": entry["filename"],
                    "sha256": entry["digests"]["sha256"], "size": entry["size"], "url": entry["url"],
                    "archives": []})
                if archive.filename not in row["archives"]:
                    row["archives"].append(archive.filename)
    return {"comment": "Roues tierces de la skill lourde, épinglées par empreinte ; `python tools/build_skills.py "
                       "lock` réécrit ce fichier / third-party wheels of the heavy skill, pinned by digest",
            "pythons": list(PYTHONS), "pins": dict(sorted(PINS.items())),
            "wheels": [wheels[name] for name in sorted(wheels)]}


def read_lock(path: Path = LOCK) -> dict[str, Any]:
    try:
        return dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise BuildError(f"{path}: verrou illisible / unreadable lock ({exc})") from None


def fetch(entry: dict[str, Any], cache: Path) -> bytes:
    """Roue du cache, sinon téléchargée ; empreinte toujours vérifiée / cached or downloaded, digest always checked."""
    path = cache / entry["file"]
    if path.is_file():
        data = path.read_bytes()
    else:
        print(f"téléchargement / download {entry['file']}", flush=True)
        with urllib.request.urlopen(entry["url"], timeout=300) as response:
            data = response.read()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise BuildError(f"{entry['file']}: empreinte différente du verrou / digest differs from the lock")
    if not path.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data


def wheel_matches_sources(data: bytes, source: Path = SOURCE) -> list[str]:
    """La roue pure contient-elle exactement src/gdprguardian ? / does the pure wheel hold exactly the sources?"""
    expected = {path.relative_to(source.parent).as_posix(): normalized(path)
                for path in source_files(source) if path.suffix != ".pyc"}
    problems = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        found = {name: archive.read(name) for name in archive.namelist()
                 if name.startswith("gdprguardian/") and not name.endswith("/")}
    for name in sorted(set(expected) | set(found)):
        if name not in found:
            problems.append(f"absent de la roue / missing from the wheel: {name}")
        elif name not in expected:
            problems.append(f"en trop dans la roue / extra in the wheel: {name}")
        else:
            text = PurePosixPath(name).suffix.lower() in TEXT_SUFFIXES
            if (found[name].replace(b"\r\n", b"\n") if text else found[name]) != expected[name]:
                problems.append(f"différent des sources / differs from the sources: {name}")
    return problems


def own_wheels(wheelhouse: Path, archive: Archive, release: str) -> tuple[dict[str, bytes], list[str]]:
    """Roues de Gardien RGPD pour une archive, et plateformes sans noyau / own wheels, and platforms without core."""
    pure = wheelhouse / f"gdprguardian-{release}-py3-none-any.whl"
    if not pure.is_file():
        raise BuildError(f"{pure}: roue pure absente (uv build --no-sources --out-dir {wheelhouse}) / missing")
    data = pure.read_bytes()
    problems = wheel_matches_sources(data)
    if problems:
        raise BuildError(f"{pure.name} ne correspond pas aux sources, reconstruisez-la / does not match the sources, "
                         f"rebuild it:\n  " + "\n  ".join(problems[:20]))
    wheels = {pure.name: data}
    without_core = []
    for target in archive.platforms:
        cores = core_wheels(wheelhouse, release, target)
        if cores:
            wheels[cores[0].name] = cores[0].read_bytes()
        else:
            without_core.append(target)
    return wheels, without_core


def core_wheels(wheelhouse: Path, release: str, target: str) -> list[Path]:
    return sorted(path for path in wheelhouse.glob(f"gdprguardian_core-{release}-cp311-abi3-*.whl")
                  if PLATFORMS[target].search(path.name))


# --- Contrat des noyaux / core contracts ---------------------------------------------------------------------------


def source_contract(root: Path = ROOT) -> int:
    """`CONTRACT` de src/gdprguardian/_native.py : le noyau doit porter le même / the core must carry the same."""
    found = re.search(r"(?m)^CONTRACT = (\d+)$", (root / "src" / "gdprguardian" / "_native.py").read_text("utf-8"))
    if found is None:
        raise BuildError("CONTRACT introuvable dans _native.py / CONTRACT not found in _native.py")
    return int(found.group(1))


def read_contracts(path: Path = CONTRACTS) -> dict[str, dict[str, Any]]:
    """Contrats vérifiés, par roue de noyau et empreinte / verified contracts, per core wheel and digest."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BuildError(f"{path}: illisible / unreadable ({exc})") from None
    return {name: dict(entry) for name, entry in dict(data.get("cores", {})).items()}


def write_contracts(record: dict[str, dict[str, Any]], path: Path = CONTRACTS) -> None:
    payload = {"comment": "Contrat de chaque noyau, vérifié en l'important sur sa plateforme (build) ; check exige le "
                          "contrat des sources / each core's contract, verified by importing it on its platform",
               "cores": {name: record[name] for name in sorted(record)}}
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def host_platform() -> str | None:
    machine = platform.machine().lower()
    if sys.platform == "win32" and machine in ("amd64", "x86_64"):
        return "win_amd64"
    if sys.platform.startswith("linux") and machine in ("x86_64", "aarch64"):
        return f"linux_{machine}"
    if sys.platform == "darwin" and machine == "arm64":
        return "macos_arm64"
    return None


def probe_contract(wheel: Path) -> int | None:
    """Importe le noyau dans un interpréteur nu et lit son contrat / imports the core in a bare interpreter."""
    with tempfile.TemporaryDirectory(prefix="gdprguardian-core-") as tmp:
        with zipfile.ZipFile(wheel) as handle:
            handle.extractall(tmp)
        probe = "import sys; sys.path.insert(0, sys.argv[1]); import gdprguardian_core as c; print(c.CONTRACT)"
        done = subprocess.run([sys.executable, "-I", "-S", "-c", probe, tmp], capture_output=True, timeout=120,
                              check=False)
    found = done.stdout.decode("ascii", "replace").strip()
    return int(found) if found.isdigit() else None


def verify_host_cores(wheelhouse: Path, release: str, record: dict[str, dict[str, Any]], expected: int) -> list[str]:
    """Vérifie le noyau de ce poste et le consigne ; un noyau d'un autre arbre serait écarté à l'import, en silence
    pour l'utilisateur. Verifies this host's core and records it; a core from another tree would be dropped at
    import, silently for the user."""
    host = host_platform()
    lines = []
    for wheel in core_wheels(wheelhouse, release, host) if host else []:
        found = probe_contract(wheel)
        if found != expected:
            raise BuildError(f"{wheel.name}: contrat {found if found is not None else '?'} au lieu de {expected} : "
                             f"noyau d'un autre arbre, reconstruisez-le / core from another tree, rebuild it "
                             f"(python tools/build_local.py)")
        record[wheel.name] = {"sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "contract": found}
        lines.append(f"noyau vérifié / core verified: {wheel.name} (contrat / contract {found})")
    return lines


def core_problems(name: str, data: bytes, record: dict[str, dict[str, Any]], manifest_contract: Any,
                  expected: int) -> list[str]:
    """Un noyau embarqué est-il vérifié et au contrat des sources ? / is a bundled core verified and current?"""
    entry = record.get(name) or {}
    if entry.get("sha256") != hashlib.sha256(data).hexdigest():
        return [f"{name}: noyau non vérifié sur sa plateforme, lancez build sur cette plateforme (WSL pour Linux) / "
                f"core not verified on its platform, run build there (WSL for Linux)"]
    if entry.get("contract") != expected or manifest_contract != expected:
        return [f"{name}: contrat {entry.get('contract')} au lieu de {expected} : noyau périmé, reconstruisez-le / "
                f"stale core, rebuild it (python tools/build_local.py)"]
    return []


# --- Avis de tiers / third-party notices ---------------------------------------------------------------------------

# Licences que les métadonnées des roues ne disent pas clairement / licences the wheel metadata leaves unclear.
LICENCE_OVERRIDES = {
    "cobble": "BSD-2-Clause (README du projet / project README)",
    "pypdfium2": "BSD-3-Clause OR Apache-2.0, CC-BY-4.0 ; PDFium et ses dépendances / PDFium and its dependencies",
}
# Texte BSD-2-Clause de cobble, dont la roue ne porte aucun fichier de licence ; détenteur : l'auteur déclaré dans
# ses métadonnées. cobble's BSD-2-Clause text (its wheel ships no licence file); holder: the author in its metadata.
COBBLE_LICENCE = """Copyright (c) Michael Williamson
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
   disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
   following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
# Crates de la nomenclature compilées seulement pour d'autres cibles / SBOM crates compiled only for other targets.
OTHER_TARGETS = {"r-efi": "UEFI (getrandom) ; non compilée dans ces roues / not compiled into these wheels"}
_LICENCE_FILE = re.compile(r"(?i)(licen[cs]e|copying|notice|unlicense)")


def _wheel_licence(handle: zipfile.ZipFile, project: str) -> tuple[str, list[str]]:
    """Licence déclarée et fichiers de licence d'une roue / declared licence and licence files of a wheel."""
    names = handle.namelist()
    meta_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
    meta = email.parser.Parser().parsestr(handle.read(meta_name).decode("utf-8", "replace"))
    files = sorted(name for name in names if ".dist-info/licenses/" in name
                   or (".dist-info/" in name and _LICENCE_FILE.search(name.rsplit("/", 1)[-1])))
    if project in LICENCE_OVERRIDES:
        return LICENCE_OVERRIDES[project], files
    declared = meta.get("License-Expression") or ""
    short = (meta.get("License") or "").strip()
    if not declared and short and "\n" not in short and len(short) < 60:
        declared = short
    if not declared:
        classifiers = [c.rsplit("::", 1)[-1].strip() for c in meta.get_all("Classifier") or []
                       if c.startswith("License ::")]
        declared = ", ".join(classifiers) or "?"
    return declared, files


def sbom_components(core: bytes) -> list[tuple[str, str, str]]:
    """Crates de la nomenclature CycloneDX d'un noyau : nom, version, licence / a core's SBOM crates."""
    with zipfile.ZipFile(io.BytesIO(core)) as handle:
        name = next((n for n in handle.namelist() if n.endswith(".cyclonedx.json")), None)
        if name is None:
            raise BuildError("noyau sans nomenclature CycloneDX / core without a CycloneDX SBOM")
        sbom = json.loads(handle.read(name))
    found = []
    for component in sbom.get("components", []):
        licences = [item.get("expression") or (item.get("license") or {}).get("id") or "?"
                    for item in component.get("licenses", [])] or ["?"]
        found.append((component["name"], str(component.get("version")), " AND ".join(licences)))
    return sorted(set(found))


def _crate_texts(registry: Path, crate: str, release: str, expression: str) -> list[tuple[str, str]]:
    """Textes à reproduire pour une crate (MIT choisi quand il est offert) / texts to reproduce (MIT when offered)."""
    folders = sorted(registry.glob(f"*/{crate}-{release}"))
    if not folders:
        raise BuildError(f"{crate} {release}: absente du registre cargo / missing from the cargo registry "
                         f"({registry}); lancez / run: cargo fetch --manifest-path rust/Cargo.toml")
    files = {path.name.upper(): path for path in folders[0].iterdir() if path.is_file()}
    wanted: list[str] = []
    if "MIT" in expression.split() or "MIT" in re.findall(r"[\w.-]+", expression):
        mit = next((name for name in ("LICENSE-MIT", "LICENSE-MIT.MD", "LICENSE.MIT") if name in files), None)
        wanted.append(mit or "LICENSE")
    else:
        wanted.append("LICENSE")
    if "Unicode-3.0" in expression:
        wanted.append("LICENSE-UNICODE")
    texts = []
    for name in wanted:
        if name not in files:
            raise BuildError(f"{crate} {release}: {name} absent du registre / missing from the registry")
        texts.append((name, files[name].read_text(encoding="utf-8").replace("\r\n", "\n").strip() + "\n"))
    return texts


def notices(wheelhouse: Path, cache: Path = CACHE, registry: Path = REGISTRY, root: Path = ROOT) -> str:
    """THIRD_PARTY_NOTICES.md des archives lourdes, depuis les roues et le registre cargo / from the wheels."""
    release = version(root)
    lock_data = read_lock()
    lines = [
        "# Avis de tiers / Third-party notices", "",
        "Gardien RGPD / GDPR Guardian (scripts, roue `gdprguardian`, roues `gdprguardian_core`) : licence MIT "
        "(`LICENSE`). Les archives lourdes `gdprguardian-local*.zip` embarquent aussi, dans `wheels/`, les composants "
        "ci-dessous, chacun sous sa propre licence. Les roues Python gardent leurs textes de licence dans leur dossier "
        "`.dist-info` ; les textes qu'elles ne portent pas sont reproduits plus bas.",
        "",
        "GDPR Guardian is MIT-licensed. The heavy archives also bundle, in `wheels/`, the components below, each under "
        "its own licence. Python wheels keep their licence texts in their `.dist-info` folder; the texts they do not "
        "carry are reproduced below.",
        "",
        "Ce logiciel utilise le code de FreeType, par PDFium dans pypdfium2 / This software uses the FreeType code, "
        "through PDFium in pypdfium2: portions of this software are copyright © The FreeType Project "
        "(www.freetype.org). All rights reserved.",
        "", "## Roues Python / Python wheels", "",
        "| Composant / Component | Version | Licence | Textes / Texts |", "|---|---|---|---|",
    ]
    seen: set[str] = set()
    for entry in sorted(lock_data["wheels"], key=lambda item: (item["project"], item["file"])):
        if entry["project"] in seen:
            continue
        seen.add(entry["project"])
        with zipfile.ZipFile(io.BytesIO(fetch(entry, cache))) as handle:
            declared, files = _wheel_licence(handle, entry["project"])
        if not files and entry["project"] != "cobble":
            raise BuildError(f"{entry['file']}: aucun fichier de licence, reproduisez son texte ici / no licence file, "
                             f"reproduce its text here")
        where = ("reproduit plus bas / reproduced below" if not files else f"`{files[0]}`" if len(files) == 1 else
                 f"`{files[0].split('.dist-info/', 1)[0]}.dist-info/` ({len(files)} fichiers / files)")
        lines.append(f"| {entry['project']} | {entry['version']} | {declared} | {where} |")
    cores: dict[tuple[str, str], str] = {}
    for target in PLATFORMS:
        for wheel in core_wheels(wheelhouse, release, target):
            cores.update({(name, ver): lic for name, ver, lic in sbom_components(wheel.read_bytes())})
    if not cores:
        raise BuildError(f"{wheelhouse}: aucune roue gdprguardian_core / no core wheel")
    lines += ["", "## Crates Rust du noyau `gdprguardian_core` / Rust crates of the core", "",
              "Liste tirée de la nomenclature CycloneDX de chaque roue de noyau (crates de compilation comprises). "
              "Pour une crate à double licence, la licence MIT est retenue. Listed from each core wheel's CycloneDX "
              "SBOM (build-time crates included). For dual-licensed crates, MIT is chosen.", "",
              "| Crate | Version | Licence |", "|---|---|---|"]
    lines += [f"| {name} | {ver} | {lic} |" for (name, ver), lic in sorted(cores.items())]
    lines += ["", "## Textes de licence / Licence texts", "",
              "### cobble 0.1.4 (BSD-2-Clause)", "",
              "La roue ne porte aucun fichier de licence ; le projet se déclare « 2-Clause BSD » / the wheel ships no "
              "licence file; the project declares the 2-Clause BSD licence.", "", "```text", COBBLE_LICENCE.strip(),
              "```"]
    grouped: dict[str, list[str]] = {}
    for (name, ver), lic in sorted(cores.items()):
        if name in OTHER_TARGETS:
            lines += ["", f"### {name} {ver} ({lic})", "", f"Cible / target: {OTHER_TARGETS[name]}."]
            continue
        for _, text in _crate_texts(registry, name, ver, lic):
            grouped.setdefault(text, []).append(f"{name} {ver}")
    for text, crates in sorted(grouped.items(), key=lambda item: item[1][0]):
        lines += ["", f"### {', '.join(crates)}", "", "```text", text.rstrip("\n"), "```"]
    return "\n".join(lines) + "\n"


def notice_components(text: str) -> set[tuple[str, str]]:
    """(nom, version) des tableaux de THIRD_PARTY_NOTICES.md / (name, version) of the notices' tables."""
    rows = set()
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("| ") and len(cells) >= 3 and re.fullmatch(r"\d[\w.+-]*", cells[1]):
            rows.add((cells[0], cells[1]))
    return rows


# --- Archive / archive ---------------------------------------------------------------------------------------------


def write_zip(entries: dict[str, bytes]) -> bytes:
    """Zip reproductible : ordre trié, date fixe, droits fixes, sans compression / reproducible zip."""
    names = set(entries)
    for name in list(entries):
        parents = PurePosixPath(name).parents
        names.update(f"{parent.as_posix()}/" for parent in parents if parent.as_posix() != ".")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(names):
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.create_system = 3  # Unix : droits lus partout de la même façon / modes read the same everywhere
            info.compress_type = zipfile.ZIP_STORED
            if name.endswith("/"):
                info.external_attr = (0o40755 << 16) | 0x10
                archive.writestr(info, b"")
            else:
                info.external_attr = 0o100644 << 16
                archive.writestr(info, entries[name])
    return buffer.getvalue()


def extra_files(archive: Archive) -> dict[str, bytes]:
    """Fichiers ajoutés aux sources de la skill : LICENSE, et les avis de tiers des archives lourdes."""
    extras = {f"{archive.skill}/LICENSE": text_bytes(LICENSE)}
    if archive.platforms:
        extras[f"{archive.skill}/THIRD_PARTY_NOTICES.md"] = normalized(NOTICES)
    return extras


def archive_entries(archive: Archive, lock_data: dict[str, Any], wheelhouse: Path, cache: Path,
                    release: str, contracts: dict[str, dict[str, Any]] | None = None
                    ) -> tuple[dict[str, bytes], list[str]]:
    """Contenu d'une archive : la skill, LICENSE, et pour la skill lourde ses roues / content of an archive."""
    problems = check_skill(archive.source, archive.skill)
    if problems:
        raise BuildError("\n".join(problems))
    prefix = archive.skill
    entries = {f"{prefix}/{path.relative_to(archive.source).as_posix()}": normalized(path)
               for path in source_files(archive.source)}
    entries.update(extra_files(archive))
    if not archive.platforms:
        return entries, []
    wheels, without_core = own_wheels(wheelhouse, archive, release)
    for entry in lock_data["wheels"]:
        if archive.filename in entry["archives"]:
            wheels[entry["file"]] = fetch(entry, cache)
    digests = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(wheels.items())}
    record = contracts or {}
    core_contracts = {name: (record.get(name, {}).get("contract")
                             if record.get(name, {}).get("sha256") == digests[name] else None)
                      for name in digests if name.startswith("gdprguardian_core-")}
    manifest = {"gdprguardian": release, "archive": archive.filename, "platforms": list(archive.platforms),
                "pythons": [f"3.{python[3:]}" for python in PYTHONS],
                "engine_without_core": without_core, "core_contracts": core_contracts, "wheels": digests}
    requirements = [f"gdprguardian=={release}", *(f"{project}=={PINS[project]}" for project in TOP_LEVEL)]
    entries[f"{prefix}/wheels/MANIFEST.json"] = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode()
    entries[f"{prefix}/wheels/requirements.txt"] = ("\n".join(requirements) + "\n").encode()
    entries.update({f"{prefix}/wheels/{name}": data for name, data in wheels.items()})
    return entries, without_core


def uncompressed_size(entries: dict[str, bytes]) -> int:
    return sum(len(data) for data in entries.values())


def build(wheelhouse: Path, cache: Path = CACHE, out: Path = SKILLS, root: Path = ROOT) -> list[str]:
    release = version(root)
    lock_data = read_lock()
    contracts = read_contracts()
    expected = source_contract(root)
    lines = verify_host_cores(wheelhouse, release, contracts, expected)
    write_contracts(contracts)
    unverified: set[str] = set()
    for archive in ARCHIVES:
        entries, without_core = archive_entries(archive, lock_data, wheelhouse, cache, release, contracts)
        size = uncompressed_size(entries)
        if size >= UPLOAD_LIMIT:
            raise BuildError(f"{archive.filename}: {size} octets décompressés, limite / bytes uncompressed, limit "
                             f"{UPLOAD_LIMIT}")
        for name, data in entries.items():
            core = name.rsplit("/", 1)[-1]
            if core.startswith("gdprguardian_core-") and core_problems(core, data, contracts, expected, expected):
                unverified.add(core)
        data = write_zip(entries)
        out.mkdir(parents=True, exist_ok=True)
        (out / archive.filename).write_bytes(data)
        note = f", moteur Python seul sur / Python engine only on {', '.join(without_core)}" if without_core else ""
        lines.append(f"{archive.filename}: {len(data)} octets/bytes ({size / 1e6:.1f} Mo décompressés/uncompressed), "
                     f"sha256 {hashlib.sha256(data).hexdigest()}{note}")
    lines += [f"[!!] {core} : non vérifié, lancez build sur sa plateforme (check échouera) / not verified, run build "
              f"on its platform (check will fail)" for core in sorted(unverified)]
    return lines


# --- Contrôle / check ----------------------------------------------------------------------------------------------


def check(out: Path = SKILLS, root: Path = ROOT) -> list[str]:
    """Archives présentes, reproductibles et conformes aux sources, au verrou, aux contrats et aux avis, sans réseau
    ni reconstruction des roues. Archives present, reproducible and matching the sources, lock, contracts and
    notices, offline."""
    release = version(root)
    lock_data = read_lock()
    locked = {entry["file"]: entry for entry in lock_data["wheels"]}
    contracts = read_contracts()
    expected = source_contract(root)
    problems: list[str] = []
    for archive in ARCHIVES:
        path = out / archive.filename
        if not path.is_file():
            problems.append(f"{archive.filename}: absente, lancez / missing, run: python tools/build_skills.py build")
            continue
        data = path.read_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as handle:
            content = {name: handle.read(name) for name in handle.namelist() if not name.endswith("/")}
        problems.extend(check_skill(archive.source, archive.skill))
        prefix = f"{archive.skill}/"
        if not all(name.startswith(prefix) for name in content):
            problems.append(f"{archive.filename}: tout doit être sous / everything must be under {prefix}")
        sources = {f"{prefix}{p.relative_to(archive.source).as_posix()}": normalized(p)
                   for p in source_files(archive.source)}
        sources.update(extra_files(archive))
        for name, wanted in sources.items():
            if content.get(name) != wanted:
                problems.append(f"{archive.filename}: {name} diffère des sources / differs from the sources")
        wheel_names = {name for name in content if name.startswith(f"{prefix}wheels/") and name.endswith(".whl")}
        others = set(content) - set(sources) - wheel_names - {f"{prefix}wheels/MANIFEST.json",
                                                             f"{prefix}wheels/requirements.txt"}
        problems.extend(f"{archive.filename}: {name} absent des sources / not in the sources"
                        for name in sorted(others))
        if archive.platforms:
            problems.extend(_check_wheels(archive, content, wheel_names, locked, release, contracts, expected))
        elif wheel_names:
            problems.append(f"{archive.filename}: roues inattendues / unexpected wheels")
        if write_zip(content) != data:
            problems.append(f"{archive.filename}: pas reproductible (ordre, dates, droits) / not reproducible")
        if uncompressed_size(content) >= UPLOAD_LIMIT:
            problems.append(f"{archive.filename}: au-delà de / beyond {UPLOAD_LIMIT} octets/bytes")
    return problems


def _check_wheels(archive: Archive, content: dict[str, bytes], wheel_names: Iterable[str],
                  locked: dict[str, dict[str, Any]], release: str, contracts: dict[str, dict[str, Any]],
                  expected: int) -> list[str]:
    prefix = f"{archive.skill}/wheels/"
    problems = []
    names = {name[len(prefix):] for name in wheel_names}
    expected_third = {name for name, entry in locked.items() if archive.filename in entry["archives"]}
    own = {name for name in names if project_of(name) in ("gdprguardian", "gdprguardian-core")}
    if names - own != expected_third:
        problems.append(f"{archive.filename}: roues tierces différentes du verrou / third-party wheels differ from "
                        f"the lock: {sorted((names - own) ^ expected_third)}")
    problems.extend(f"{archive.filename}: {name} : empreinte différente du verrou / digest differs"
                    for name in sorted((names - own) & expected_third)
                    if hashlib.sha256(content[prefix + name]).hexdigest() != locked[name]["sha256"])
    pure = f"gdprguardian-{release}-py3-none-any.whl"
    if pure not in names:
        problems.append(f"{archive.filename}: {pure} absente (version de pyproject.toml) / missing")
    else:
        stale = wheel_matches_sources(content[prefix + pure])[:10]
        problems.extend(f"{archive.filename}: {problem} : python tools/build_local.py, puis / then python "
                        f"tools/build_skills.py build" for problem in stale)
    problems.extend(f"{archive.filename}: {name} : autre version que / other version than {release}"
                    for name in sorted(own - {pure}) if not name.startswith(f"gdprguardian_core-{release}-"))
    manifest: dict[str, Any] = {}
    try:
        manifest = json.loads(content[prefix + "MANIFEST.json"])
        digests = {name: hashlib.sha256(content[prefix + name]).hexdigest() for name in sorted(names)}
        if manifest.get("wheels") != digests or manifest.get("gdprguardian") != release:
            problems.append(f"{archive.filename}: MANIFEST.json ne décrit pas les roues / does not match the wheels")
    except (KeyError, ValueError):
        problems.append(f"{archive.filename}: MANIFEST.json absent ou illisible / missing or unreadable")
    cores = sorted(name for name in own if name.startswith("gdprguardian_core-"))
    for name in cores:
        problems.extend(f"{archive.filename}: {problem}" for problem in core_problems(
            name, content[prefix + name], contracts, (manifest.get("core_contracts") or {}).get(name), expected))
    # Avis de tiers : chaque roue tierce et chaque crate des noyaux y figure / every wheel and core crate is listed.
    listed = notice_components(content.get(f"{archive.skill}/THIRD_PARTY_NOTICES.md", b"").decode("utf-8"))
    needed = {(locked[name]["project"], locked[name]["version"]) for name in (names - own) & expected_third}
    for name in cores:
        needed |= {(crate, ver) for crate, ver, _ in sbom_components(content[prefix + name])}
    missing = sorted(needed - listed)
    if missing:
        problems.append(f"{archive.filename}: THIRD_PARTY_NOTICES.md ne cite pas / does not list {missing[:10]} : "
                        f"python tools/build_skills.py notices")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)
    build_cmd = commands.add_parser("build", help="construit skills/*.zip / builds skills/*.zip")
    build_cmd.add_argument("--wheelhouse", type=Path,
                           help="roues de Gardien RGPD (défaut : dist/<version>) / GDPR Guardian's wheels")
    build_cmd.add_argument("--cache", type=Path, default=CACHE, help="cache des roues tierces / third-party cache")
    commands.add_parser("check", help="archives conformes, sans réseau / archives match, offline")
    commands.add_parser("lock", help="réécrit le verrou depuis PyPI / rewrites the lock from PyPI")
    notices_cmd = commands.add_parser("notices", help="réécrit THIRD_PARTY_NOTICES.md / rewrites the notices")
    notices_cmd.add_argument("--wheelhouse", type=Path, help="roues de noyau (défaut : dist/<version>) / core wheels")
    notices_cmd.add_argument("--cache", type=Path, default=CACHE, help="cache des roues tierces / third-party cache")
    notices_cmd.add_argument("--registry", type=Path, default=REGISTRY, help="registre cargo / cargo registry src")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        if args.command == "lock":
            LOCK.parent.mkdir(parents=True, exist_ok=True)
            LOCK.write_text(json.dumps(lock(), indent=1) + "\n", encoding="utf-8", newline="\n")
            print(f"{LOCK} écrit / written")
            return 0
        if args.command == "notices":
            text = notices(args.wheelhouse or ROOT / "dist" / version(), args.cache, args.registry)
            NOTICES.write_text(text, encoding="utf-8", newline="\n")
            print(f"{NOTICES} écrit / written ({len(text)} caractères/chars)")
            return 0
        if args.command == "build":
            lines = build(args.wheelhouse or ROOT / "dist" / version(), args.cache)
            for line in lines:
                print(line)
            return 0
        problems = check()
    except (BuildError, OSError, KeyError, ValueError) as exc:
        print(f"build_skills: {exc}", file=sys.stderr)
        return 1
    for problem in problems:
        print(f"[!!] {problem}")
    if not problems:
        print("[ok] archives des skills conformes / skill archives match")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
