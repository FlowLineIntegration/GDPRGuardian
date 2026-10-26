"""Archives des skills (skills/*.zip) : conformes aux sources et au verrou, reproductibles, prêtes pour claude.ai.

Skill archives: matching the sources and the lock, reproducible, ready for claude.ai. Sans réseau / offline.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # les dataclasses cherchent leur module / dataclasses look their module up
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.fixture(scope="module")
def build() -> ModuleType:
    return load(ROOT / "tools" / "build_skills.py", "build_skills_for_tests")


def test_committed_archives_match_the_sources(build: ModuleType) -> None:
    problems = build.check()
    assert not problems, "\n".join(problems) + (
        "\nArchives à reconstruire / archives to rebuild: python tools/build_local.py (ou / or: uv build --no-sources "
        "--wheel --out-dir <dossier> . puis / then python tools/build_skills.py build --wheelhouse <dossier>)")


def test_each_archive_holds_one_skill_folder_at_its_root(build: ModuleType) -> None:
    for archive in build.ARCHIVES:
        with zipfile.ZipFile(build.SKILLS / archive.filename) as handle:
            names = handle.namelist()
            infos = handle.infolist()
        # claude.ai cherche <skill>/SKILL.md : le dossier à la racine, rien à côté / the folder at the root, alone.
        assert {name.split("/", 1)[0] for name in names} == {archive.skill}
        assert f"{archive.skill}/SKILL.md" in names
        assert names == sorted(names) and all(info.date_time == build.FIXED_TIME for info in infos)
        assert sum(info.file_size for info in infos) < build.UPLOAD_LIMIT


def test_light_archive_is_tiny_and_heavy_ones_carry_the_engine(build: ModuleType) -> None:
    online, linux, desktop = (build.SKILLS / archive.filename for archive in build.ARCHIVES)
    assert online.stat().st_size < 200_000
    with zipfile.ZipFile(online) as handle:
        assert not [name for name in handle.namelist() if name.endswith(".whl")]
    release = build.version()
    for path, platforms in ((linux, ("linux_x86_64", "linux_aarch64")), (desktop, ("win_amd64", "macos_arm64"))):
        with zipfile.ZipFile(path) as handle:
            wheels = [name.rsplit("/", 1)[-1] for name in handle.namelist() if name.endswith(".whl")]
            manifest = json.loads(handle.read("gdprguardian-local/wheels/MANIFEST.json"))
            requirements = handle.read("gdprguardian-local/wheels/requirements.txt").decode().split()
        assert manifest["gdprguardian"] == release and manifest["platforms"] == list(platforms)
        assert requirements[0] == f"gdprguardian=={release}" and f"gdprguardian-{release}-py3-none-any.whl" in wheels
        for platform in platforms:
            rule = build.PLATFORMS[platform]
            # Chaque version de Python couverte trouve ses roues natives / every Python version finds its wheels.
            for python in build.PYTHONS:
                for project in ("ahocorasick_rs", "python_calamine"):
                    assert [w for w in wheels if w.startswith(project) and rule.search(w) and f"-{python}-" in w], \
                        (project, platform, python)
            assert [w for w in wheels if w.startswith("pypdfium2-") and rule.search(w)], platform
        cores = {platform for platform in platforms for w in wheels
                 if w.startswith("gdprguardian_core-") and build.PLATFORMS[platform].search(w)}
        assert set(manifest["engine_without_core"]) == set(platforms) - cores


@pytest.mark.parametrize("folder", ["plugin-online/skills/gdprguardian-online", "plugin/skills/gdprguardian-local"])
def test_skill_frontmatter_follows_the_rules(build: ModuleType, folder: str) -> None:
    path = ROOT / "integrations" / "claude" / folder
    assert build.check_skill(path, path.name) == []
    fields = build.frontmatter((path / "SKILL.md").read_text(encoding="utf-8").replace("\r\n", "\n"))
    # Spécification Agent Skills : description ≤ 1 024, compatibility ≤ 500 ; aucun champ inconnu.
    assert len(fields["description"]) <= 1024 and len(fields["compatibility"]) <= 500
    assert set(fields) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    text = (path / "SKILL.md").read_text(encoding="utf-8")
    assert text.count("\n") < 500  # SKILL.md court, lu en entier à chaque chargement / short, read in full each load
    # Un vrai analyseur YAML lit le même bloc (pas de « : » piégeux dans une valeur) / a real YAML parser agrees.
    yaml = pytest.importorskip("yaml")
    parsed = yaml.safe_load(text.split("---", 2)[1])
    assert parsed["name"] == path.name and parsed["description"] == fields["description"]
    assert parsed["license"].startswith("MIT") and all(isinstance(tool, str) for tool in parsed["allowed-tools"])
    # Claude Code ne remplace ${CLAUDE_SKILL_DIR} que dans les règles Bash / only Bash rules get the substitution.
    assert all(tool.startswith(("Bash(", "mcp__")) for tool in parsed["allowed-tools"])
    # La skill lourde renvoie aux licences des roues embarquées / the heavy skill points to the bundled licences.
    assert ("THIRD_PARTY_NOTICES.md" in parsed["license"]) == (path.name == "gdprguardian-local")


def test_archives_carry_the_licence_and_the_third_party_notices(build: ModuleType) -> None:
    licence = (ROOT / "LICENSE").read_bytes().replace(b"\r\n", b"\n")
    notices = build.NOTICES.read_text(encoding="utf-8")
    crates: set[tuple[str, str]] = set()
    for archive in build.ARCHIVES:
        with zipfile.ZipFile(build.SKILLS / archive.filename) as handle:
            assert handle.read(f"{archive.skill}/LICENSE") == licence
            names = handle.namelist()
            if not archive.platforms:
                assert f"{archive.skill}/THIRD_PARTY_NOTICES.md" not in names
                continue
            assert handle.read(f"{archive.skill}/THIRD_PARTY_NOTICES.md").decode("utf-8") == notices
            cores = [name for name in names if name.rsplit("/", 1)[-1].startswith("gdprguardian_core-")]
            crates |= {(crate, ver) for name in cores for crate, ver, _ in build.sbom_components(handle.read(name))}
    listed = build.notice_components(notices)
    # Chaque roue tierce et chaque crate liée au noyau est citée, avec sa version / every wheel and crate is listed.
    assert {(entry["project"], entry["version"]) for entry in build.read_lock()["wheels"]} <= listed
    assert crates and crates <= listed
    # FreeType exige une mention dans la documentation ; cobble n'a pas de fichier de licence dans sa roue.
    # FreeType requires a credit in the documentation; cobble's wheel has no licence file.
    assert "The FreeType Project (www.freetype.org)" in notices and "### cobble 0.1.4 (BSD-2-Clause)" in notices


def test_bundled_cores_carry_the_sources_contract(build: ModuleType) -> None:
    expected = build.source_contract()
    record = build.read_contracts()
    for archive in build.ARCHIVES[1:]:
        with zipfile.ZipFile(build.SKILLS / archive.filename) as handle:
            manifest = json.loads(handle.read(f"{archive.skill}/wheels/MANIFEST.json"))
            for name, contract in manifest["core_contracts"].items():
                assert contract == expected == record[name]["contract"], name
                assert build.core_problems(name, handle.read(f"{archive.skill}/wheels/{name}"), record, contract,
                                           expected) == []
    # Un noyau d'un autre arbre (contrat différent) ou jamais vérifié est signalé / a stale or unverified core fails.
    assert build.core_problems("c.whl", b"x", {}, expected, expected)
    stale = {"c.whl": {"sha256": hashlib.sha256(b"x").hexdigest(), "contract": expected - 1}}
    assert "stale core" in build.core_problems("c.whl", b"x", stale, expected - 1, expected)[0]


@pytest.mark.parametrize("script", [
    "plugin-online/skills/gdprguardian-online/scripts/gdprguardian_online.py",
    "plugin/skills/gdprguardian-local/scripts/gdprguardian_local.py",
])
def test_scripts_parse_on_old_pythons(script: str) -> None:
    # Script léger : Python 3.9+ ; script lourd : doit au moins dire clairement « Python 3.11+ requis » sur un 3.9.
    # Light script: Python 3.9+; heavy script: must at least say "Python 3.11+ required" on a 3.9.
    source = (ROOT / "integrations" / "claude" / script).read_text(encoding="utf-8")
    ast.parse(source, feature_version=(3, 9))
    assert "from __future__ import annotations" in source


def test_zip_writer_is_reproducible(build: ModuleType) -> None:
    entries = {"s/b.txt": b"b", "s/a/SKILL.md": b"x", "s/w/z.whl": b"\x00" * 10}
    first, second = build.write_zip(entries), build.write_zip(dict(reversed(list(entries.items()))))
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as handle:
        assert handle.namelist() == ["s/", "s/a/", "s/a/SKILL.md", "s/b.txt", "s/w/", "s/w/z.whl"]
        assert {info.compress_type for info in handle.infolist()} == {zipfile.ZIP_STORED}


def test_lock_follows_the_pins(build: ModuleType) -> None:
    lock = build.read_lock()
    assert lock["pins"] == dict(sorted(build.PINS.items())) and lock["pythons"] == list(build.PYTHONS)
    names = {archive.filename for archive in build.ARCHIVES if archive.platforms}
    for entry in lock["wheels"]:
        assert build.project_of(entry["file"]) == entry["project"] and build.PINS[entry["project"]] == entry["version"]
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) and set(entry["archives"]) <= names
        assert entry["url"].startswith("https://files.pythonhosted.org/")
