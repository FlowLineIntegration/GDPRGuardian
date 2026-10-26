#!/usr/bin/env python3
"""Construit dist/gdprguardian-<version>.mcpb avec la CLI officielle : mcpb validate, puis mcpb pack. Jamais signé.

Builds dist/gdprguardian-<version>.mcpb with the official CLI: mcpb validate, then mcpb pack. Never signed.

    npm install -g @anthropic-ai/mcpb      # une fois / once
    python packaging/mcpb/build.py         # ou / or: --mcpb <chemin de la CLI / path of the CLI>

Le paquet ne contient que manifest.json, icon.png et LICENSE : au premier lancement, uvx installe Gardien RGPD à la
version épinglée, la même que celle du plugin Claude et du service en ligne. The bundle only holds manifest.json,
icon.png and LICENSE: at first start, uvx installs GDPR Guardian at the pinned version, the same as the Claude plugin's
and the online service's. Bibliothèque standard uniquement / standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN_MANIFEST = REPO / "integrations" / "claude" / "plugin" / ".claude-plugin" / "plugin.json"
# Une seule icône, celle du plugin Claude / a single icon, the Claude plugin's.
ICON = PLUGIN_MANIFEST.parent / "icon.png"
STAGE = REPO / "build" / "mcpb"
_PIN = re.compile(r"gdprguardian\[local\]==(\S+)")


class BuildError(Exception):
    """Échec de construction, message pour l'éditeur / build failure, message for the publisher."""


def check_versions(manifest: dict[str, Any], plugin: dict[str, Any]) -> str:
    """Une seule version : paquet MCPB, épinglage de uvx et plugin Claude / one version everywhere."""
    version = str(manifest["version"])
    pins = [match.group(1) for arg in manifest["server"]["mcp_config"]["args"] if (match := _PIN.fullmatch(arg))]
    if pins != [version]:
        raise BuildError(f"épinglage {pins} différent de la version {version} / pin differs from the version")
    if plugin.get("version") != version:
        raise BuildError(f"plugin Claude en {plugin.get('version')}, paquet MCPB en {version} / versions differ")
    return version


def find_mcpb(explicit: str | None) -> str:
    command = explicit or shutil.which("mcpb")
    if not command:
        raise BuildError("CLI mcpb introuvable : npm install -g @anthropic-ai/mcpb / mcpb CLI not found")
    return command


def stage(target: Path = STAGE) -> Path:
    """Dossier du paquet : seulement les fichiers voulus (mcpb pack prend tout le dossier) / only wanted files."""
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    shutil.copy2(HERE / "manifest.json", target / "manifest.json")
    shutil.copy2(ICON, target / "icon.png")
    shutil.copy2(REPO / "LICENSE", target / "LICENSE")
    return target


def run(command: list[str]) -> None:
    print("$", " ".join(command), flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise BuildError(f"commande en échec / command failed ({completed.returncode})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    parser.add_argument("--mcpb", help="CLI mcpb (défaut : celle du PATH) / mcpb CLI (default: the one on PATH)")
    parser.add_argument("--out", type=Path, default=REPO / "dist", help="dossier de sortie / output directory")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
        plugin = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        version = check_versions(manifest, plugin)
        mcpb = find_mcpb(args.mcpb)
        bundle = stage()
        output = args.out.resolve() / f"gdprguardian-{version}.mcpb"
        output.parent.mkdir(parents=True, exist_ok=True)
        run([mcpb, "validate", str(bundle / "manifest.json")])
        run([mcpb, "pack", str(bundle), str(output)])
    except (BuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"build: {exc}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"{output}\nsha256 {digest}\nnon signé : la signature (mcpb sign) revient à l'éditeur / unsigned: signing "
          "(mcpb sign) is up to the publisher")
    return 0


if __name__ == "__main__":
    sys.exit(main())
