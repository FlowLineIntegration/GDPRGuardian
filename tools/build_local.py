"""Construction locale d'une version, sans GitHub Actions (phase de R&D) / local release build, no GitHub Actions.

    python tools/build_local.py                 noyau pour ce système, sources, roues pures, paquet MCPB
    python tools/build_local.py --linux         en plus : roues Linux x86_64 manylinux du noyau (Docker)
    python tools/build_local.py --image         en plus : image Docker (noyau PGO) et son archive
    python tools/build_local.py --linux --image --skip-host   sous Linux (WSL), pour compléter un dist/ existant

Tout va dans dist/<version>/ : roues et sources à la racine, claude/ (paquet MCPB), docker/ (archive de l'image),
SHA256SUMS. Contrôles : `release.py check` avant, `release.py dists` après. Requiert maturin et uv ; Docker pour
--linux et --image ; la CLI mcpb pour le paquet MCPB (--mcpb, sinon celle du PATH ; absente, l'étape est sautée).
Enfin, les archives des skills Claude (skills/*.zip, suivies dans le dépôt) sont reconstruites avec les roues de
cette version (`tools/build_skills.py build`, réseau pour les roues tierces absentes du cache) ; --no-skills saute
l'étape. Chaque passage vérifie le noyau de son propre système (skills/core_contracts.json) : lancer la version sous
Windows puis sous Linux (WSL), sinon `build_skills.py check` refuse le noyau non vérifié. Everything goes to
dist/<version>/. Requires maturin and uv; Docker for --linux and --image; the mcpb CLI. Last, the Claude skill
archives (skills/*.zip, tracked in the repository) are rebuilt with this version's wheels; each run verifies its own
system's core, so run it on Windows and then on Linux (WSL).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATURIN_IMAGE = "ghcr.io/pyo3/maturin:v1.15.0"


def run(command: list[str], cwd: Path = ROOT) -> None:
    print("$", " ".join(command), flush=True)
    if subprocess.run(command, cwd=cwd, check=False).returncode:
        sys.exit(f"build_local: commande en échec / command failed: {command[0]}")


def tool(name: str) -> str:
    """Exécutable du PATH ou du venv courant / executable from PATH or the current venv."""
    found = shutil.which(name) or shutil.which(name, path=str(Path(sys.executable).parent))
    if not found:
        sys.exit(f"build_local: {name} introuvable / not found")
    return found


def version() -> str:
    sys.path.insert(0, str(ROOT / "tools"))
    import release

    problems = release.check(ROOT)
    if problems:
        sys.exit("build_local: versions incohérentes / inconsistent versions:\n  " + "\n  ".join(problems))
    return release.reference_version(ROOT)


def core(out: Path) -> None:
    """Roue du noyau pour ce système et ses sources (la licence est copiée le temps de la construction)."""
    license_copy = ROOT / "rust" / "LICENSE"
    created = not license_copy.exists()
    if created:
        shutil.copy2(ROOT / "LICENSE", license_copy)
    try:
        run([tool("maturin"), "build", "--release", "-m", "rust/Cargo.toml", "--out", str(out)])
        run([tool("maturin"), "sdist", "-m", "rust/Cargo.toml", "--out", str(out)])
    finally:
        if created:
            license_copy.unlink()


def pure(out: Path) -> None:
    """Roue et sources de gdprguardian et du paquet gdprguardian-mcp / pure wheels and sdists."""
    run([tool("uv"), "build", "--no-sources", "--out-dir", str(out), str(ROOT)])
    run([tool("uv"), "build", "--no-sources", "--out-dir", str(out), str(ROOT / "packaging" / "gdprguardian-mcp")])


def mcpb(out: Path, cli: str | None) -> None:
    cli = cli or shutil.which("mcpb")
    if not cli:
        print("paquet MCPB sauté : CLI mcpb absente / MCPB bundle skipped: no mcpb CLI", flush=True)
        return
    run([sys.executable, str(ROOT / "packaging" / "mcpb" / "build.py"), "--mcpb", cli, "--out", str(out / "claude")])


def linux(out: Path) -> None:
    """Roue manylinux_2_17 x86_64 du noyau, construite dans l'image officielle de maturin / manylinux wheel."""
    license_copy = ROOT / "rust" / "LICENSE"
    created = not license_copy.exists()
    if created:
        shutil.copy2(ROOT / "LICENSE", license_copy)
    try:
        run([tool("docker"), "run", "--rm", "-v", f"{ROOT}:/io", "-w", "/io",
             "-e", "CARGO_TARGET_DIR=/io/rust/target/manylinux", MATURIN_IMAGE, "build", "--release",
             "-m", "rust/Cargo.toml", "--compatibility", "manylinux2014", "--out", f"dist/{out.name}"])
    finally:
        if created:
            license_copy.unlink()


def image(out: Path, tag: str) -> None:
    """Image Docker du service (noyau PGO par défaut) et son archive compressée / service image and its archive."""
    run([tool("docker"), "build", "-f", "deploy/Dockerfile", "-t", tag, "."])
    target = out / "docker" / f"{tag.replace(':', '-')}.tar.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = target.with_suffix("")
    run([tool("docker"), "save", "-o", str(raw), tag])
    with raw.open("rb") as source, gzip.open(target, "wb", compresslevel=6) as sink:
        shutil.copyfileobj(source, sink, 1 << 20)
    raw.unlink()
    print("image :", target, f"({target.stat().st_size // 2**20} Mo)", flush=True)


def skills(out: Path) -> None:
    """Archives des skills Claude avec les roues de cette version (noyaux présents dans dist/) / skill archives."""
    run([sys.executable, str(ROOT / "tools" / "build_skills.py"), "build", "--wheelhouse", str(out)])


def checksums(out: Path) -> None:
    lines = []
    # Sans les fichiers cachés (uv dépose un .gitignore) / hidden files left out (uv drops a .gitignore).
    for path in sorted(p for p in out.rglob("*")
                       if p.is_file() and p.name != "SHA256SUMS" and not p.name.startswith(".")):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        lines.append(f"{digest.hexdigest()}  {path.relative_to(out).as_posix()}")
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(*lines, sep="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    parser.add_argument("--linux", action="store_true", help="roues Linux du noyau (Docker) / Linux core wheels")
    parser.add_argument("--image", action="store_true", help="image Docker et archive / Docker image and archive")
    parser.add_argument("--skip-host", action="store_true",
                        help="ne pas reconstruire noyau, sources ni MCPB pour ce système / skip host artefacts")
    parser.add_argument("--mcpb", help="CLI mcpb / mcpb CLI")
    parser.add_argument("--no-skills", action="store_true",
                        help="ne pas reconstruire skills/*.zip / do not rebuild the skill archives")
    args = parser.parse_args()
    current = version()
    out = ROOT / "dist" / current
    out.mkdir(parents=True, exist_ok=True)
    if not args.skip_host:
        core(out)
        pure(out)
        mcpb(out, args.mcpb)
    if args.linux:
        linux(out)
    if args.image:
        image(out, f"gdprguardian:{current}")
    if not args.no_skills:
        skills(out)
    run([sys.executable, str(ROOT / "tools" / "release.py"), "dists", str(out)])
    checksums(out)
    print("version", current, "->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
