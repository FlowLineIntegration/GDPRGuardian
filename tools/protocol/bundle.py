"""Paquet autonome du protocole pour le serveur (zipapp) / self-contained protocol bundle for the server (zipapp).

    python -m tools.protocol bundle --out DIR/gg-protocol.pyz
    python gg-protocol.pyz run …        (Python 3.12+, bibliothèque standard seulement / standard library only)

Contenu : tools/eval (générateur, mutations, métriques), les trois modules de tools/corpus utilisés (format,
partition dev/test, mesures), tools/protocol, le texte du protocole (docs/PROTOCOLE.md, dont l'empreinte entre dans
chaque résultat) et Faker (MIT, pur Python, version de l'environnement de développement, pour régénérer exactement
les mêmes documents). Ni le moteur ni aucun corpus réel n'y entrent. Construction reproductible au bit près, sous
Windows comme sous Linux : ordre trié, dates figées, fichiers stockés sans compression. Contents: tools/eval, the
three tools/corpus modules used, tools/protocol, the protocol text (its digest goes into every result) and Faker (MIT,
pure Python). Neither the engine nor any real corpus. Bit-for-bit reproducible build on Windows and Linux alike.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from collections.abc import Iterable
from importlib import metadata
from pathlib import Path
from typing import Any

from tools.protocol import spec

ROOT = Path(__file__).resolve().parents[2]
FIXED_DATE = (2026, 10, 25, 0, 0, 0)
CORPUS_MODULES = ("real_common.py", "real_registry.py", "evaluate_real.py")
PROTOCOL_TEXT = "PROTOCOLE.md"
MAIN = '''"""Gardien RGPD · GDPR Guardian : protocole public, paquet autonome / public protocol, bundle."""
import sys

if sys.version_info < (3, 12):
    raise SystemExit("Python 3.12+ requis / required (random.binomialvariate)")
if sys.argv and sys.argv[0] and sys.argv[0] not in sys.path:
    sys.path.insert(0, sys.argv[0])
from tools.protocol.cli import main

raise SystemExit(main())
'''


def _python_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and p.suffix in (".py", ".json", ".txt"))


def tools_entries(root: Path = ROOT) -> list[tuple[str, bytes]]:
    """Fichiers `tools/` du paquet, tels qu'ils y entrent / the bundle's `tools/` files, as they go in."""
    entries: list[tuple[str, bytes]] = [("tools/__init__.py", b"")]
    entries.extend((p.relative_to(root).as_posix(), p.read_bytes()) for p in _python_files(root / "tools" / "eval"))
    entries.append(("tools/corpus/__init__.py", b""))
    entries.extend((f"tools/corpus/{name}", (root / "tools" / "corpus" / name).read_bytes()) for name in CORPUS_MODULES)
    for path in _python_files(root / "tools" / "protocol"):
        if "server" in path.relative_to(root / "tools" / "protocol").parts:
            continue
        entries.append((path.relative_to(root).as_posix(), path.read_bytes()))
    return entries


def tools_digest(entries: Iterable[tuple[str, bytes]]) -> str:
    """Empreinte des fichiers `tools/` (noms et SHA-256), la même depuis le dépôt et depuis le paquet.

    Digest of the `tools/` files (names and SHA-256), the same from the repository and from the bundle.
    """
    files = {name: hashlib.sha256(data).hexdigest() for name, data in entries if name.startswith("tools/")}
    return hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(files.items())).encode()).hexdigest()


def build_bundle(out: Path) -> tuple[Path, dict[str, Any]]:
    entries: list[tuple[str, bytes]] = [("__main__.py", MAIN.encode())]
    entries.extend(tools_entries())
    entries.append((PROTOCOL_TEXT, (ROOT / "docs" / PROTOCOL_TEXT).read_bytes()))
    found = importlib.util.find_spec("faker")
    if found is None or not found.submodule_search_locations:
        raise SystemExit("Faker introuvable : pip install faker / Faker not found")
    faker_root = Path(next(iter(found.submodule_search_locations)))
    for path in sorted(p for p in faker_root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        if path.suffix in (".pyc", ".pyo"):
            continue
        entries.append(("faker/" + path.relative_to(faker_root).as_posix(), path.read_bytes()))
    faker_version = metadata.version("faker")
    dist = metadata.distribution("faker")
    licence = next((f for f in dist.files or () if f.name.upper().startswith("LICENSE")), None)
    if licence is not None:
        entries.append(("faker-LICENSE.txt", Path(dist.locate_file(licence)).read_bytes()))
    files = {name: hashlib.sha256(data).hexdigest() for name, data in entries}
    info = {"protocol": spec.PROTOCOL_VERSION, "faker": faker_version, "files": len(files),
            "tools_sha256": tools_digest(entries)}
    entries.append(("BUNDLE.json", json.dumps({**info, "sha256": files}, indent=1, sort_keys=True).encode()))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    # Sans compression : la sortie de zlib varie d'une plateforme à l'autre (Windows et Linux donnaient deux paquets
    # aux contenus identiques) ; stockés tels quels, les octets ne dépendent que des fichiers (~10 Mo).
    # Stored, not deflated: zlib's output varies across platforms (Windows and Linux gave two bundles with identical
    # contents); stored as is, the bytes depend on the files only (~10 MB).
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(entries, key=lambda item: (item[0] != "__main__.py", item[0])):
            item = zipfile.ZipInfo(name, FIXED_DATE)
            item.compress_type = zipfile.ZIP_STORED
            item.external_attr = 0o644 << 16
            item.create_system = 3  # Unix, quelle que soit la plateforme de construction / Unix on every platform
            archive.writestr(item, data)
    tmp.replace(out)
    info["bundle_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
    info["bytes"] = out.stat().st_size
    info["spec_sha256"] = files["tools/protocol/spec.py"]
    info["protocole_md_sha256"] = files[PROTOCOL_TEXT]
    return out, info
