"""Noyau Rust optimisé par profil d'exécution (PGO) / profile-guided build of the Rust core.

    python tools/pgo.py --out dist/                        # roue PGO / PGO wheel
    python tools/pgo.py --out dist/ --plain                # même chaîne, sans profil (comparaison A/B)
    python tools/pgo.py --out dist/ --target-cpu x86-64-v2 # jeu d'instructions de base relevé (mesure)

Trois étapes / three steps:
1. noyau instrumenté (`-Cprofile-generate`) / instrumented core;
2. charge représentative, données fictives seulement : corpus `datasets/fr/docs`, gros textes, pays « FR » et
   « all », règles de l'organisation, explications, segments de tableur, finaliseur / representative workload,
   fictitious data only;
3. fusion des profils (`llvm-profdata`, même LLVM que rustc : `rustup component add llvm-tools-preview`), puis
   construction optimisée (`-Cprofile-use`) / profiles merged, then the optimised build.

Utilisé tel quel par `deploy/Dockerfile` avec `--build-arg PGO=1` (mesures et décision : deploy/README.md) / used
as is by the Dockerfile with `--build-arg PGO=1`. Aucune donnée réelle : le profil ne contient que des compteurs
de branches, jamais de texte / no real data: the profile only holds branch counters, never text.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rust" / "Cargo.toml"
CORPUS = ROOT / "datasets" / "fr" / "docs"
# Lignes de tableur fictives (prénom, nom) / fictitious spreadsheet rows.
_GIVEN = ("Jean", "Claire", "Pierre", "Sophie", "Nicolas", "Isabelle", "Thomas", "Nathalie", "Karim", "Léa")
_SURNAMES = ("Martin", "Dubois", "Lefèvre", "Moreau", "Garcia", "Nguyen", "Bernard", "Petit", "Roux", "Fontaine")


def log(message: str) -> None:
    sys.stderr.write(f"[pgo] {message}\n")


# --- construction / build ---------------------------------------------------------------------------------


def llvm_profdata() -> Path:
    """`llvm-profdata` de la chaîne Rust active (même version de LLVM) / from the active Rust toolchain."""
    explicit = os.environ.get("LLVM_PROFDATA")
    if explicit:
        return Path(explicit)
    sysroot = subprocess.run(["rustc", "--print", "sysroot"], check=True, capture_output=True, text=True).stdout
    version = subprocess.run(["rustc", "-vV"], check=True, capture_output=True, text=True).stdout
    host = next(line.split(": ", 1)[1] for line in version.splitlines() if line.startswith("host: "))
    tool = Path(sysroot.strip()) / "lib" / "rustlib" / host / "bin" / "llvm-profdata"
    tool = tool.with_suffix(".exe") if os.name == "nt" else tool
    if not tool.exists():
        raise SystemExit(f"llvm-profdata introuvable / not found: {tool}\n"
                         "  rustup component add llvm-tools-preview")
    return tool


def build(maturin: str, out: Path, target: Path, rustflags: Sequence[str]) -> Path:
    """`maturin build --release` avec ces drapeaux ; renvoie la roue / returns the wheel."""
    out.mkdir(parents=True, exist_ok=True)
    before = set(out.glob("gdprguardian_core-*.whl"))
    flags = " ".join([os.environ.get("RUSTFLAGS", ""), *rustflags]).strip()
    env = {**os.environ, "RUSTFLAGS": flags, "CARGO_TARGET_DIR": str(target)}
    log(f"maturin build --release (RUSTFLAGS={flags or '-'})")
    started = time.perf_counter()
    subprocess.run([maturin, "build", "--release", "--quiet", "-m", str(MANIFEST), "--out", str(out)],
                   check=True, env=env)
    wheels = sorted(set(out.glob("gdprguardian_core-*.whl")) - before) or sorted(out.glob("gdprguardian_core-*.whl"))
    if not wheels:
        raise SystemExit(f"aucune roue produite / no wheel in {out}")
    log(f"  {wheels[-1].name} ({time.perf_counter() - started:.0f} s)")
    return wheels[-1]


def extract(wheel: Path, into: Path) -> Path:
    """Le paquet `gdprguardian_core` de la roue, prêt à importer / the wheel's package, ready to import."""
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(into, [name for name in archive.namelist() if name.startswith("gdprguardian_core/")])
    return into


def profile(python: str, core: Path, profiles: Path) -> list[Path]:
    """Charge de travail dans un processus neuf, avec le noyau instrumenté / workload in a fresh process.

    Dossier propre à la charge : les scripts de construction et macros instrumentés pendant la compilation
    écrivent aussi des profils, hors sujet / own directory: instrumented build scripts and proc macros also write
    profiles while compiling, which are irrelevant.
    """
    profiles = profiles / "workload"
    profiles.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "LLVM_PROFILE_FILE": str(profiles / "gdprguardian-%p-%m.profraw")}
    command = [python, "-I", str(Path(__file__).resolve()), "--workload", "--core", str(core),
               "--src", str(ROOT / "src"), "--corpus", str(CORPUS)]
    started = time.perf_counter()
    subprocess.run(command, check=True, env=env)
    raw = sorted(profiles.glob("*.profraw"))
    if not raw:
        raise SystemExit("aucun profil écrit : noyau non instrumenté ? / no profile written")
    log(f"charge de travail / workload: {time.perf_counter() - started:.0f} s, {len(raw)} profil(s)")
    return raw


def merge(raw: Sequence[Path], merged: Path) -> Path:
    subprocess.run([str(llvm_profdata()), "merge", "-o", str(merged), *map(str, raw)], check=True)
    log(f"profil fusionné / merged profile: {merged.stat().st_size // 1024} Kio")
    return merged


def main_build(args: argparse.Namespace) -> int:
    maturin = args.maturin or shutil.which("maturin") or str(Path(sys.executable).with_name("maturin"))
    base = [f"-Ctarget-cpu={args.target_cpu}"] if args.target_cpu else []
    out = Path(args.out).resolve()
    if args.plain:
        build(maturin, out, Path(args.target_dir or ROOT / "rust" / "target"), base)
        return 0
    work = Path(args.work).resolve() if args.work else Path(tempfile.mkdtemp(prefix="gdprguardian-pgo-"))
    try:
        profiles = work / "profiles"
        # Répertoires de compilation distincts : les drapeaux diffèrent, rien n'est partagé / distinct targets.
        instrumented = build(maturin, work / "instrumented", work / "target-generate",
                             [*base, f"-Cprofile-generate={profiles}"])
        core = extract(instrumented, work / "core")
        merged = merge(profile(args.python, core, profiles), work / "merged.profdata")
        build(maturin, out, work / "target-use", [*base, f"-Cprofile-use={merged}"])
    finally:
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)
    return 0


# --- charge de travail / workload -------------------------------------------------------------------------


def _documents(corpus: Path) -> list[str]:
    docs = [path.read_text(encoding="utf-8") for path in sorted(corpus.glob("*.md"))] if corpus.is_dir() else []
    if docs:
        return docs
    # Sans corpus : courriers fictifs générés / without a corpus: generated fictitious letters.
    return [f"Objet : dossier n° {i}\n\nMadame, Monsieur,\n\nM. {_GIVEN[i % 10]} {_SURNAMES[i % 10]}, né le "
            f"12/03/1985 (NIR 1 85 05 78 006 084 91), joignable au 06 12 34 56 78 ou à "
            f"{_GIVEN[i % 10].lower()}.{_SURNAMES[i % 10].lower()}@exemple.fr, demeure 12 rue de la Paix, "
            f"75002 Paris. IBAN FR76 3000 6000 0112 3456 7890 189, société Exemple SAS (SIRET 732 829 320 00074).\n"
            for i in range(1000)]


def _rows(count: int) -> bytes:
    """CSV fictif : noms, courriels, téléphones, IBAN et NIR d'exemple / fictitious CSV."""
    lines = ["prenom;nom;email;telephone;iban;nir;commentaire"]
    for i in range(count):
        given, surname = _GIVEN[i % len(_GIVEN)], _SURNAMES[(i * 7) % len(_SURNAMES)]
        lines.append(f"{given};{surname};{given.lower()}.{surname.lower()}{i}@exemple.fr;"
                     f"06 {i % 100:02d} 34 56 78;FR76 3000 6000 0112 3456 7890 189;1 85 05 78 006 084 91;"
                     f"Dossier {i} suivi par M. {surname}")
    return "\n".join(lines).encode()


def workload(core: Path, src: Path, corpus: Path) -> None:
    """Chemins chauds du noyau, sur des données fictives / the core's hot paths, on fictitious data."""
    sys.path[:0] = [str(core), str(src)]
    import gdprguardian_core

    from gdprguardian import Anonymizer
    from gdprguardian.documents import DocumentOptions

    if not Path(gdprguardian_core.__file__).resolve().is_relative_to(core.resolve()):
        raise SystemExit("noyau importé hors de la roue instrumentée / core imported from elsewhere")
    docs = _documents(corpus)
    rules = {"name": "pgo", "rules": [{"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}", "context": ["client"]}],
             "deny": {"PROJET": ["Opération Phénix"]}, "allow": ["support@exemple.fr"]}
    engines = {
        "fr": Anonymizer(countries="FR"),
        "all": Anonymizer(countries="all"),
        "strict": Anonymizer(countries="FR", profile="strict", explain=True, label_language="en", rules=rules),
    }
    if not all(engine.native for engine in engines.values()):
        raise SystemExit("noyau Rust inutilisé / Rust core not in use")
    started = time.perf_counter()
    for _ in range(2):
        for text in docs:
            engines["fr"].anonymize(text)
    for text in docs:
        engines["all"].anonymize(text)
    for text in docs[::3]:
        engines["strict"].anonymize(text)
        engines["fr"].analyze(text)
    # Gros textes : un document de plusieurs Mo, puis un tableau Markdown / large texts, then a Markdown table.
    big = "\n\n".join(docs)
    engines["fr"].anonymize(big)
    engines["all"].anonymize(big[: len(big) // 4])
    table = "| Prénom | Nom | Courriel |\n|---|---|---|\n" + "".join(
        f"| {_GIVEN[i % 10]} | {_SURNAMES[i % 10]} | {_GIVEN[i % 10].lower()}{i}@exemple.fr |\n" for i in range(3000))
    engines["fr"].anonymize(table)
    # Segments de tableur : moteur direct, puis le pipeline CSV complet / spreadsheet segments, then CSV.
    cells = [line for text in docs[:300] for line in text.splitlines() if line.strip()]
    engine = engines["fr"]
    for countries_engine in (engine, engines["all"]):
        scope = countries_engine.new_scope("fr")
        try:
            countries_engine.anonymize_segments(cells, scope)
        finally:
            scope.close()
    engine.analyze_segments(cells[:2000])
    from gdprguardian.tabular import anonymize_workbook

    for name in ("people.csv", "people.tsv"):
        data = _rows(5000) if name.endswith(".csv") else _rows(5000).replace(b";", b"\t")
        anonymize_workbook(data, name, engine, DocumentOptions(sandbox=False))
    log(f"charge exécutée / workload ran in {time.perf_counter() - started:.1f} s ({len(docs)} documents)")


# --- ligne de commande / command line ---------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", help="dossier de la roue / wheel directory")
    parser.add_argument("--plain", action="store_true", help="sans PGO (référence A/B) / without PGO")
    parser.add_argument("--target-cpu", help="ex. x86-64-v2 ; défaut : cible de base / default: baseline target")
    parser.add_argument("--maturin", help="exécutable maturin / maturin executable")
    parser.add_argument("--python", default=sys.executable, help="interpréteur de la charge / workload interpreter")
    parser.add_argument("--target-dir", help="CARGO_TARGET_DIR de --plain")
    parser.add_argument("--work", help="dossier de travail (défaut : temporaire) / work directory")
    parser.add_argument("--keep", action="store_true", help="garde le dossier de travail / keeps the work directory")
    parser.add_argument("--workload", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--core", help=argparse.SUPPRESS)
    parser.add_argument("--src", default=str(ROOT / "src"), help=argparse.SUPPRESS)
    parser.add_argument("--corpus", default=str(CORPUS), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.workload:
        workload(Path(args.core), Path(args.src), Path(args.corpus))
        return 0
    if not args.out:
        parser.error("--out est requis / is required")
    return main_build(args)


if __name__ == "__main__":
    sys.exit(main())
