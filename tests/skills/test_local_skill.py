"""Skill lourde gdprguardian-local : choix des roues, installation hors ligne, anonymisation de bout en bout.

Heavy skill gdprguardian-local: wheel selection, offline install, end-to-end anonymisation from the committed archive
(fictitious data only).
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import platform
import subprocess
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

from gdprguardian import __version__

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "integrations" / "claude" / "plugin" / "skills" / "gdprguardian-local"
SCRIPT = SKILL / "scripts" / "gdprguardian_local.py"
NIR = "1 85 05 78 006 084 91"
EMAIL = "jean.dupont@exemple.fr"
IBAN = "FR76 3000 6000 0112 3456 7890 189"
SECRETS = (NIR, EMAIL, IBAN, "Dupont")
TEXT = f"Dossier de M. Jean Dupont, NIR {NIR}, courriel {EMAIL}, IBAN {IBAN}.\n"


def load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.fixture(scope="module")
def local() -> ModuleType:
    return load(SCRIPT, "gdprguardian_local_skill_script")


@pytest.fixture(scope="module")
def locked() -> list[str]:
    lock = json.loads((ROOT / "skills" / "wheels.lock.json").read_text(encoding="utf-8"))
    return [entry["file"] for entry in lock["wheels"]] + [
        "gdprguardian-1.0.0-py3-none-any.whl",
        "gdprguardian_core-1.0.0-cp311-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        "gdprguardian_core-1.0.0-cp311-abi3-win_amd64.whl"]


def _as(monkeypatch: pytest.MonkeyPatch, local: ModuleType, system: str, machine: str, python: tuple[int, int],
        glibc: tuple[int, int] | None = (2, 39), mac: tuple[int, int] = (14, 0)) -> None:
    monkeypatch.setattr(local, "_system", lambda: system)
    monkeypatch.setattr(local.platform, "machine", lambda: machine)
    windows = {"amd64": "win-amd64", "x86_64": "win-amd64", "arm64": "win-arm64", "x86": "win32"}
    monkeypatch.setattr(local, "_windows_platform", lambda: windows.get(machine.lower(), "win-amd64"))
    monkeypatch.setattr(local, "_glibc", lambda: glibc)
    monkeypatch.setattr(local, "_mac_release", lambda: mac)
    monkeypatch.setattr(local, "_interpreter", lambda: (*python, False))


@pytest.mark.skipif(sys.implementation.name != "cpython", reason="CPython")
@pytest.mark.parametrize(("system", "machine", "python", "expected"), [
    # Bac à sable de claude.ai : Linux x86_64, Python 3.11 / claude.ai sandbox.
    ("linux", "x86_64", (3, 11), {"ahocorasick-rs": "cp311-cp311-manylinux_2_17_x86_64",
                                  "gdprguardian-core": "abi3-manylinux_2_17_x86_64",
                                  "pypdfium2": "manylinux_2_17_x86_64",
                                  "python-calamine": "cp311-cp311-manylinux_2_17_x86_64"}),
    ("linux", "aarch64", (3, 12), {"ahocorasick-rs": "cp312-cp312-manylinux_2_17_aarch64", "gdprguardian-core": None,
                                   "pypdfium2": "manylinux_2_17_aarch64"}),
    ("win32", "AMD64", (3, 14), {"ahocorasick-rs": "cp314-cp314-win_amd64", "gdprguardian-core": "abi3-win_amd64",
                                 "pypdfium2": "win_amd64", "python-calamine": "cp314-cp314-win_amd64"}),
    ("darwin", "arm64", (3, 13), {"ahocorasick-rs": "cp313-cp313-macosx_10_12_x86_64.macosx_11_0_arm64",
                                  "gdprguardian-core": None, "pypdfium2": "macosx_13_0_arm64",
                                  "python-calamine": "cp313-cp313-macosx_11_0_arm64"}),
])
def test_wheel_selection(local: ModuleType, locked: list[str], monkeypatch: pytest.MonkeyPatch, system: str,
                         machine: str, python: tuple[int, int], expected: dict[str, str | None]) -> None:
    _as(monkeypatch, local, system, machine, python)
    chosen = local.select_wheels(locked)
    # Une seule roue par projet, toujours la roue pure de Gardien RGPD / one wheel per project, the pure engine always.
    assert chosen["gdprguardian"] == "gdprguardian-1.0.0-py3-none-any.whl" and chosen["mammoth"].endswith("-any.whl")
    for project, fragment in expected.items():
        if fragment is None:
            assert project not in chosen, chosen.get(project)
        else:
            assert fragment in chosen[project], (project, chosen.get(project))


def test_unsupported_platforms_are_reported(local: ModuleType, locked: list[str],
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    # Python 3.15, Linux musl (sans glibc) : aucune roue native / no native wheel.
    for system, machine, python, glibc in (("linux", "x86_64", (3, 15), (2, 39)), ("linux", "x86_64", (3, 12), None)):
        _as(monkeypatch, local, system, machine, python, glibc=glibc)
        assert "ahocorasick-rs" not in local.select_wheels(locked)
    # Mac Intel : moteur Python par la roue universelle, ni PDF ni Excel / Intel Mac: Python engine, no PDF, no Excel.
    _as(monkeypatch, local, "darwin", "x86_64", (3, 12))
    chosen = local.select_wheels(locked)
    assert "ahocorasick-rs" in chosen and not {"pypdfium2", "python-calamine", "gdprguardian-core"} & set(chosen)
    # macOS 12 : pypdfium2 exige macOS 13, le reste convient / pypdfium2 needs macOS 13, the rest fits.
    _as(monkeypatch, local, "darwin", "arm64", (3, 12), mac=(12, 6))
    chosen = local.select_wheels(locked)
    assert "pypdfium2" not in chosen and "ahocorasick-rs" in chosen
    manifest = {"gdprguardian": "1.0.0", "platforms": ["win_amd64"], "pythons": ["3.11"],
                "wheels": {name: "0" * 64 for name in locked if "win_amd64" in name or name.endswith("any.whl")}}
    _as(monkeypatch, local, "linux", "x86_64", (3, 12))
    with pytest.raises(local.Failure, match="not covered"):
        local.ensure_runtime(manifest, {})


def test_windows_architecture_comes_from_the_interpreter(local: ModuleType, locked: list[str],
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    # Environnement minimal sans PROCESSOR_ARCHITECTURE : platform.machine() vide, l'interpréteur dit win-amd64.
    # Minimal environment without PROCESSOR_ARCHITECTURE: empty platform.machine(), the interpreter says win-amd64.
    _as(monkeypatch, local, "win32", "", (3, 11))
    monkeypatch.setattr(local, "_windows_platform", lambda: "win-amd64")
    chosen = local.select_wheels(locked)
    assert "win_amd64" in chosen["ahocorasick-rs"] and "win_amd64" in chosen["gdprguardian-core"]
    # Un Python ARM64 sous Windows n'a pas de roues : message cohérent / an ARM64 Python: no wheels, a clear message.
    monkeypatch.setattr(local, "_windows_platform", lambda: "win-arm64")
    assert "ahocorasick-rs" not in local.select_wheels(locked)
    manifest = {"gdprguardian": "1.0.0", "platforms": ["win_amd64", "macos_arm64"], "pythons": ["3.11"],
                "wheels": {name: "0" * 64 for name in locked}}
    with pytest.raises(local.NotCovered, match=r"not covered .*arm64.* covered: win_amd64"):
        local.ensure_runtime(manifest, {})


def test_uncovered_platform_falls_back_to_an_installed_engine(local: ModuleType, monkeypatch: pytest.MonkeyPatch
                                                              ) -> None:
    # Archive Linux synchronisée vers Claude Code sous Windows : un Gardien RGPD installé dans ce Python sert.
    # Linux archive synced into Claude Code on Windows: an installed GDPR Guardian in this Python is used.
    manifest = {"gdprguardian": "1.0.0", "platforms": ["linux_x86_64"], "pythons": ["3.11"], "wheels": {}}

    def not_covered(*_args: object) -> None:
        raise local.NotCovered(manifest)

    monkeypatch.setattr(local, "load_manifest", lambda: manifest)
    monkeypatch.setattr(local, "ensure_runtime", not_covered)
    monkeypatch.setattr(local, "_installed_version", lambda: "0.9.0")
    assert local.activate({})["source"] == "environment"
    with pytest.raises(local.NotCovered):
        local.activate({"GDPRGUARDIAN_SKILL_RUNTIME": "bundled"})
    monkeypatch.setattr(local, "_installed_version", lambda: None)
    with pytest.raises(local.NotCovered, match="anonymize_file"):
        local.activate({})


def test_an_unwritable_home_reuses_one_private_temporary_folder(local: ModuleType, tmp_path: Path,
                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    # Cache impossible à créer (son parent est un fichier) : même dossier temporaire à chaque appel, pas un neuf.
    # The cache cannot be created (its parent is a file): the same temporary folder every time, not a new one.
    blocker = tmp_path / "not-a-folder"
    blocker.write_bytes(b"")
    monkeypatch.setattr(local.tempfile, "tempdir", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    env = {"GDPRGUARDIAN_SKILL_CACHE": str(blocker / "cache")}
    first, second = local.cache_root(env), local.cache_root(env)
    assert first == second and first.parent == tmp_path / "tmp" and first.name.startswith("gdprguardian-skill-")
    assert [path.name for path in (tmp_path / "tmp").iterdir()] == [first.name]


def test_powerpoint_without_python_pptx_is_explained(local: ModuleType, tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    real = local.importlib.util.find_spec
    monkeypatch.setattr(local.importlib.util, "find_spec", lambda name, *a: None if name == "pptx" else real(name, *a))
    deck = tmp_path / "budget.bin"  # extension trompeuse : le répertoire du zip suffit / misleading extension
    with zipfile.ZipFile(deck, "w") as archive:
        archive.writestr("ppt/presentation.xml", "<p:presentation/>")
    for path in (deck, tmp_path / "x.pptx"):
        path.touch()
        with pytest.raises(local.Failure, match=r"needs python-pptx.*never open the file"):
            local.anonymize_file(path, None, max_mb=1, timeout=5, in_process=True)
    assert not local._is_powerpoint(tmp_path / "x.docx")


def test_extraction_refuses_paths_outside_the_folder(local: ModuleType, tmp_path: Path) -> None:
    for evil in ("../evil.py", "/abs/evil.py", "pkg/../../evil.py"):
        wheel = tmp_path / "evil-1.0-py3-none-any.whl"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(evil, b"print('x')")
        wheel.write_bytes(buffer.getvalue())
        with pytest.raises(local.Failure, match="invalid wheel"):
            local._extract(wheel, tmp_path / "target")
    assert not (tmp_path / "evil.py").exists()


def test_data_folders_are_flattened(local: ModuleType, tmp_path: Path) -> None:
    wheel = tmp_path / "x-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("x/__init__.py", b"")
        archive.writestr("x-1.0.data/purelib/y.py", b"")
        archive.writestr("x-1.0.data/scripts/run", b"")
    local._extract(wheel, tmp_path / "t")
    assert sorted(p.relative_to(tmp_path / "t").as_posix() for p in (tmp_path / "t").rglob("*.py")) == [
        "x/__init__.py", "y.py"]


def _host_archive() -> Path | None:
    """Archive dont les roues couvrent ce poste / the archive whose wheels cover this computer."""
    machine = platform.machine().lower()
    if sys.platform == "win32" and machine in ("amd64", "x86_64"):
        return ROOT / "skills" / "gdprguardian-local-windows-macos.zip"
    if sys.platform.startswith("linux") and machine in ("x86_64", "aarch64"):
        return ROOT / "skills" / "gdprguardian-local.zip"
    if sys.platform == "darwin" and machine == "arm64":
        return ROOT / "skills" / "gdprguardian-local-windows-macos.zip"
    return None


@pytest.fixture(scope="module")
def unpacked(tmp_path_factory: pytest.TempPathFactory) -> Path:
    archive = _host_archive()
    if archive is None or not archive.is_file() or not (3, 11) <= sys.version_info[:2] <= (3, 14):
        pytest.skip("aucune archive pour ce poste / no archive for this computer")
    target = tmp_path_factory.mktemp("skill")
    with zipfile.ZipFile(archive) as handle:
        handle.extractall(target)
    return target / "gdprguardian-local"


def _run(unpacked: Path, cache: Path, *args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    # -I -S : ni site-packages ni variables Python, comme un interpréteur nu / no site-packages, a bare interpreter.
    env = {key: value for key, value in os.environ.items() if not key.startswith(("GDPRGUARDIAN_", "PYTHON"))}
    env["GDPRGUARDIAN_SKILL_CACHE"] = str(cache)
    return subprocess.run([sys.executable, "-I", "-S", str(unpacked / "scripts" / "gdprguardian_local.py"), *args],
                          input=stdin, capture_output=True, env=env, timeout=600, check=False)


@pytest.mark.slow
def test_archive_runs_on_a_bare_interpreter(unpacked: Path, tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    check = _run(unpacked, cache, "--check")
    assert check.returncode == 0, check.stderr.decode("utf-8", "replace")
    info = json.loads(check.stdout)
    assert info["source"] == "bundled" and info["gdprguardian"] == __version__
    assert info["formats"]["PDF"] and info["formats"]["Word (DOCX)"] and info["formats"]["CSV"]
    expected_engine = "rust" if any("gdprguardian_core" in name for name in info["wheels"]) else "python"
    assert info["engine"] == expected_engine and "engine_notes" not in info
    (runtime,) = [path for path in cache.iterdir() if not path.name.startswith(".")]

    text = _run(unpacked, cache, "--text", "-", "--report", "--explain", stdin=TEXT.encode("utf-8"))
    assert text.returncode == 0, text.stderr.decode("utf-8", "replace")
    out, err = text.stdout.decode("utf-8"), text.stderr.decode("utf-8")
    assert "[PERSONNE_1]" in out and "[NIR_1]" in out and "[IBAN_1]" in out
    assert not [secret for secret in SECRETS if secret in out or secret in err]
    report = json.loads(err.strip().splitlines()[-1])
    assert report["engine"] == expected_engine and {row["reason"] for row in report["explain"]} >= {"validated"}
    # Un seul dossier privé, réutilisé / one private folder, reused.
    assert [path for path in cache.iterdir() if not path.name.startswith(".")] == [runtime]

    sample = tmp_path / "Contrat_Jean_Dupont.pdf"
    convert_samples = load(ROOT / "tests" / "convert" / "convert_samples.py", "convert_samples_for_skill")
    sample.write_bytes(convert_samples.contract_pdf())
    output = tmp_path / "contrat.anon.md"
    pdf = _run(unpacked, cache, str(sample), "-o", str(output), "--report")
    assert pdf.returncode == 0, pdf.stderr.decode("utf-8", "replace")
    markdown = output.read_text(encoding="utf-8")
    assert "[NIR_1]" in markdown and "[IBAN_1]" in markdown and "Contrat de travail" in markdown
    assert not [secret for secret in (*SECRETS, convert_samples.AUTHOR) if secret in markdown]
    assert b"Dupont" not in pdf.stderr and b"Contrat_" not in pdf.stdout + pdf.stderr
    assert json.loads(pdf.stderr.decode("utf-8").strip().splitlines()[-1])["kind"] == "pdf"


@pytest.mark.slow
def test_bundled_engine_errors_are_clear(unpacked: Path, tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    missing = _run(unpacked, cache, str(tmp_path / "absent.pdf"))
    assert missing.returncode == 2 and b"file not found" in missing.stderr and b"Traceback" not in missing.stderr
    fake = tmp_path / "faux.pdf"
    fake.write_bytes(b"%PDF-1.7 pas un vrai PDF " + NIR.encode())
    broken = _run(unpacked, cache, str(fake))
    assert broken.returncode == 1 and b"Traceback" not in broken.stderr and NIR.encode() not in broken.stderr
    big = _run(unpacked, cache, str(fake), "--max-mb", "0.00001")
    assert big.returncode == 2 and b"file too large" in big.stderr
    # PowerPoint sans python-pptx (absent de l'archive) : un message qui dit quoi faire / a message saying what to do.
    deck = tmp_path / "budget.pptx"
    with zipfile.ZipFile(deck, "w") as archive:
        archive.writestr("ppt/presentation.xml", f"<p:presentation>{NIR}</p:presentation>")
    pptx = _run(unpacked, cache, str(deck))
    assert pptx.returncode == 1 and b"needs python-pptx" in pptx.stderr and b"PDF export" in pptx.stderr
    assert NIR.encode() not in pptx.stderr and b"Traceback" not in pptx.stderr
