"""Une seule version partout, un paquet MCP cohérent / one version everywhere, a consistent MCP package."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

import gdprguardian
from gdprguardian import _native, cli

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "release.py"


@pytest.fixture(scope="module")
def release() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gdprguardian_release_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses résout les annotations par le module / dataclasses need it
    spec.loader.exec_module(module)
    return module


def _toml(relative: str) -> dict:
    with (ROOT / relative).open("rb") as handle:
        return tomllib.load(handle)


VERSION = _toml("pyproject.toml")["project"]["version"]


# --- une version / one version ------------------------------------------------------------------------------


def test_every_version_field_is_equal(release: ModuleType) -> None:
    assert release.check(ROOT) == []
    found, problems = release.occurrences(ROOT)
    assert problems == []
    seen = {(item.path, item.label) for item in found}
    # Les champs obligatoires sont tous lus / every mandatory field is read.
    for field in release.FIELDS:
        if field.required:
            assert any(path == field.path for path, _ in seen), field.path
    assert {release.python_form(item.value) for item in found} == {VERSION}


def test_package_and_core_versions_match() -> None:
    assert gdprguardian.__version__ == VERSION
    if not _native.available():
        pytest.skip("noyau Rust absent ou désactivé / Rust core missing or disabled")
    core = _native.core()
    # Le noyau publie la version de Cargo.toml (SemVer) / the core exposes Cargo.toml's version (SemVer).
    assert core.__version__ == _toml("rust/Cargo.toml")["package"]["version"]
    assert core.__version__.replace("-rc.", "rc").replace("-alpha.", "a").replace("-beta.", "b") == VERSION


def test_core_version_comes_from_cargo() -> None:
    core = _toml("rust/pyproject.toml")["project"]
    assert "version" not in core and "version" in core["dynamic"]


def test_cli_reports_the_version(capsys: pytest.CaptureFixture[str]) -> None:
    for entry in (cli.main, cli.mcp_main):
        with pytest.raises(SystemExit) as caught:
            entry(["--version"])
        assert caught.value.code == 0
        assert capsys.readouterr().out.split()[-1] == VERSION


# --- release.py set / check sur une copie / on a copy ----------------------------------------------------------


@pytest.fixture
def tree(tmp_path: Path, release: ModuleType) -> Path:
    """Copie des fichiers versionnés / copy of the versioned files."""
    for relative in {field.path for field in release.FIELDS} | {"rust/pyproject.toml",
                                                                "packaging/gdprguardian-mcp/README.md"}:
        if (ROOT / relative).is_file():
            (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, tmp_path / relative)
    return tmp_path


def test_set_rewrites_only_versions(tree: Path, release: ModuleType) -> None:
    before = {path: path.read_bytes() for path in tree.rglob("*") if path.is_file()}
    changed = release.set_version("9.8.7", tree)
    assert release.check(tree) == []
    assert "rust/Cargo.lock" in changed and "server.json" in changed
    for path, old in before.items():
        new = path.read_bytes()
        # Même fichier, version près / same file, version aside.
        assert new.replace(b"9.8.7", VERSION.encode()) == old, path


def test_prerelease_uses_semver_in_cargo(tree: Path, release: ModuleType) -> None:
    release.set_version("1.2.0rc1", tree)
    assert release.check(tree) == []
    assert 'version = "1.2.0-rc.1"' in (tree / "rust/Cargo.toml").read_text(encoding="utf-8")
    assert '__version__ = "1.2.0rc1"' in (tree / "src/gdprguardian/__init__.py").read_text(encoding="utf-8")
    assert "gdprguardian-core==1.2.0rc1;" in (tree / "pyproject.toml").read_text(encoding="utf-8")
    with pytest.raises(release.ReleaseError):
        release.set_version("1.2", tree)


def test_drift_is_refused(tree: Path, release: ModuleType) -> None:
    init = tree / "src/gdprguardian/__init__.py"
    init.write_text(init.read_text(encoding="utf-8").replace(VERSION, "0.0.1"), encoding="utf-8")
    problems = release.check(tree)
    assert len(problems) == 1 and "__version__ = 0.0.1" in problems[0]
    assert release.check(tree, tag=f"v{VERSION}") == problems
    assert any("tag" in problem for problem in release.check(tree, tag="v9.9.9"))


def test_files_of_the_other_tracks_are_optional_then_checked(tree: Path, release: ModuleType) -> None:
    plugin = tree / "integrations/claude/plugin"
    manifest = plugin / ".claude-plugin/plugin.json"
    if manifest.exists():
        manifest.unlink()
    shutil.rmtree(tree / "packaging/mcpb", ignore_errors=True)
    assert release.check(tree) == []
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"name": "gdprguardian", "version": "0.0.9"}, indent=2), encoding="utf-8")
    (plugin / ".mcp.json").write_text(json.dumps({"mcpServers": {"gdprguardian": {
        "command": "uvx", "args": ["--from", "gdprguardian[local]==0.0.9", "gdprguardian", "mcp", "--stdio"]}}}),
        encoding="utf-8")
    mcpb = tree / "packaging/mcpb/manifest.json"
    mcpb.parent.mkdir(parents=True)
    mcpb.write_text(json.dumps({"manifest_version": "0.4", "version": "0.0.9", "server": {"mcp_config": {
        "command": "uvx", "args": ["gdprguardian-mcp@0.0.9"]}}}), encoding="utf-8")
    assert len(release.check(tree)) == 4
    release.set_version(VERSION, tree)
    assert release.check(tree) == []
    assert json.loads(mcpb.read_text(encoding="utf-8"))["manifest_version"] == "0.4"


def test_pins_in_commands(release: ModuleType) -> None:
    text = ('uvx --from "gdprguardian[local]==0.2.0" gdprguardian ; uvx gdprguardian-mcp@0.2.0. '
            "pip install gdprguardian==0.2.0rc1 gdprguardian-core==0.2.0; x ; io.github.someone/gdprguardian ; "
            "gdprguardian>=0.1 ; contact@gdprguardian.com")
    assert [(m["name"], m["v"]) for m in release.PIN.finditer(text)] == [
        ("gdprguardian", "0.2.0"), ("gdprguardian-mcp", "0.2.0"), ("gdprguardian", "0.2.0rc1"),
        ("gdprguardian-core", "0.2.0")]
    # Nom du paquet MCPB, suivi lui aussi / the MCPB bundle name is tracked too.
    bundles = ("dist/gdprguardian-0.2.0.mcpb ; gdprguardian-1.0.0rc2.mcpb ; gdprguardian-mcp-0.2.0.tar.gz ; "
               "xgdprguardian-0.2.0.mcpb")
    assert [m["v"] for m in release.BUNDLE.finditer(bundles)] == ["0.2.0", "1.0.0rc2"]


def test_owner_placeholder(tree: Path, release: ModuleType) -> None:
    # Le dépôt peut déjà porter son vrai compte : la copie retrouve le marqueur pour éprouver set-owner.
    # The repository may already carry its real account: the copy gets the placeholder back to exercise set-owner.
    owner = json.loads((tree / "server.json").read_text(encoding="utf-8"))["name"].split(".", 2)[2].split("/")[0]
    if owner != release.PLACEHOLDER:
        for path in tree.rglob("*"):
            if path.is_file() and owner in (text := release._text(path)):
                path.write_text(text.replace(owner, release.PLACEHOLDER), encoding="utf-8", newline="")
    assert any(release.PLACEHOLDER in problem for problem in release.check(tree, release=True))
    changed = release.set_owner("flowline-integration", tree)
    assert "server.json" in changed and "packaging/gdprguardian-mcp/README.md" in changed
    assert release.check(tree, release=True) == []
    assert json.loads((tree / "server.json").read_text(encoding="utf-8"))["name"] == (
        "io.github.flowline-integration/gdprguardian")
    for login in ("", "-x", "a b", "x" * 40, "ab--c"):
        with pytest.raises(release.ReleaseError):
            release.set_owner(login, tree)


# --- paquet MCP et registre / MCP package and registry --------------------------------------------------------


def test_server_json_describes_the_local_package() -> None:
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert server["$schema"].endswith("/2025-12-11/server.schema.json")
    assert server["name"].startswith("io.github.") and server["name"].endswith("/gdprguardian")
    assert len(server["description"]) <= 100  # limite du schéma / schema limit
    (package,) = server["packages"]
    assert (package["registryType"], package["identifier"], package["runtimeHint"]) == (
        "pypi", "gdprguardian-mcp", "uvx")
    assert package["transport"] == {"type": "stdio"}
    assert [variable["name"] for variable in package["environmentVariables"]] == ["GDPRGUARDIAN_ALLOWED_DIRS"]


def test_meta_package_pins_the_local_extra() -> None:
    meta = _toml("packaging/gdprguardian-mcp/pyproject.toml")["project"]
    assert meta["name"] == "gdprguardian-mcp" and meta["version"] == VERSION
    assert meta["dependencies"] == [f"gdprguardian[local]=={VERSION}"]
    assert meta["scripts"] == {"gdprguardian-mcp": "gdprguardian.cli:mcp_main"}
    readme = (ROOT / "packaging/gdprguardian-mcp/README.md").read_text(encoding="utf-8")
    name = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))["name"]
    assert f"<!-- mcp-name: {name} -->" in readme
    assert (ROOT / "packaging/gdprguardian-mcp/LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes()


def test_local_extra_and_core_markers() -> None:
    markers = pytest.importorskip("packaging.markers")
    requirements = pytest.importorskip("packaging.requirements")
    project = _toml("pyproject.toml")["project"]
    assert project["optional-dependencies"]["local"] == ["gdprguardian[mcp,office,phone]"]
    (core,) = [requirements.Requirement(d) for d in project["dependencies"] if d.startswith("gdprguardian-core")]
    assert str(core.specifier) == f"=={VERSION}"
    marker: markers.Marker = core.marker

    def picks(system: str, machine: str, implementation: str = "CPython") -> bool:
        return marker.evaluate({"sys_platform": system, "platform_machine": machine,
                                "platform_python_implementation": implementation})

    # Windows x64 : « AMD64 » pour CPython, « x86_64 » pour uv --python-platform / uv cross-resolution.
    built = [("win32", "AMD64"), ("win32", "x86_64"), ("darwin", "x86_64"), ("darwin", "arm64"), ("linux", "x86_64"),
             ("linux", "aarch64")]
    assert all(picks(*platform) for platform in built)
    others = [("win32", "ARM64"), ("win32", "x86"), ("linux", "armv7l"), ("linux", "arm"), ("linux", "ppc64le"),
              ("linux", "s390x"), ("freebsd14", "amd64"), ("darwin", "arm")]
    assert not any(picks(*platform) for platform in others)
    assert not picks("linux", "x86_64", "PyPy")


def test_mcp_main_forwards_to_the_stdio_server(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(cli, "main", lambda argv: seen.append(list(argv)) or 0)
    assert cli.mcp_main([]) == 0
    assert cli.mcp_main(["--stdio", "--allow-dir", "/a", "--allow-dir=-b"]) == 0
    # Sélecteur MCPB à plusieurs dossiers : « --allow-dir A B » / MCPB multi-folder picker.
    assert cli.mcp_main(["--allow-dir", "/a", "/b c"]) == 0
    assert seen == [["mcp", "--stdio"], ["mcp", "--stdio", "--allow-dir=/a", "--allow-dir=-b"],
                    ["mcp", "--stdio", "--allow-dir=/a", "--allow-dir=/b c"]]
    with pytest.raises(SystemExit):
        cli.mcp_main(["--http"])  # pas de transport réseau / no network transport
