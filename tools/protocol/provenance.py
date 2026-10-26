"""Provenance de l'outil : paquet, fichiers `tools/`, texte du protocole / tool provenance.

Chaque campagne recopie ces empreintes dans son point de reprise et dans ses résultats ; publiées AVANT le lancement
(`python -m tools.protocol registration`), elles prouvent que les définitions n'ont pas bougé après coup. Une reprise
avec un autre outil est refusée. Every campaign copies these digests into its checkpoint and results; published BEFORE
the launch, they show the definitions did not move afterwards. Resuming with another tool is refused.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from tools.protocol import spec


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bundle_path() -> Path | None:
    """Le paquet .pyz quand l'outil en tourne, sinon None / the .pyz when the tool runs from it, else None."""
    for parent in Path(spec.__file__).parents:
        if parent.is_file():
            return parent if zipfile.is_zipfile(parent) else None
    return None


def faker_version() -> str:
    try:
        from importlib.metadata import version

        return version("faker")
    except Exception:  # paquet autonome : Faker embarqué sans métadonnées / bundle: vendored Faker
        import faker

        return str(getattr(faker, "VERSION", "?"))


_FAKER_VERSION_RE = re.compile(rb"""^VERSION\s*=\s*["']([^"']+)["']""", re.MULTILINE)


def verify_bundle(archive: Path) -> dict[str, Any]:
    """Empreintes RECALCULÉES depuis le contenu du paquet, comparées à son manifeste ; SystemExit si elles diffèrent.

    Digests RECOMPUTED from the bundle's contents and compared with its manifest (BUNDLE.json); SystemExit when they
    differ: a bundle whose files were edited after the build is refused instead of reporting its build-time digests.
    """
    from tools.protocol.bundle import PROTOCOL_TEXT, tools_digest

    data = archive.read_bytes()
    with zipfile.ZipFile(archive) as bundle:
        entries = [(name, bundle.read(name)) for name in bundle.namelist() if not name.endswith("/")]
    contents = dict(entries)
    try:
        manifest = json.loads(contents.pop("BUNDLE.json"))
    except (KeyError, ValueError):
        raise SystemExit("paquet sans manifeste lisible / bundle without a readable manifest") from None
    actual = {name: _sha256(blob) for name, blob in contents.items()}
    tools = tools_digest(contents.items())
    match = _FAKER_VERSION_RE.search(contents.get("faker/__init__.py", b""))
    faker = match.group(1).decode() if match else None
    problems = []
    if actual != manifest.get("sha256"):
        listed = manifest.get("sha256") or {}
        changed = sorted(n for n in set(actual) | set(listed) if actual.get(n) != listed.get(n))
        problems.append(f"{len(changed)} fichier(s) / file(s): {', '.join(changed[:5])}")
    if tools != manifest.get("tools_sha256"):
        problems.append("tools_sha256")
    if faker != manifest.get("faker"):
        problems.append("faker")
    if problems:
        raise SystemExit("paquet altéré après sa construction / bundle altered after its build: " + "; ".join(problems))
    return {"bundle_sha256": _sha256(data), "tools_sha256": tools, "spec_sha256": actual.get("tools/protocol/spec.py"),
            "protocole_md_sha256": actual.get(PROTOCOL_TEXT), "faker": faker}


def provenance() -> dict[str, Any]:
    """Empreintes de l'outil qui tourne, recalculées / digests of the running tool, recomputed."""
    archive = bundle_path()
    if archive is not None:
        return {"source": "bundle", **verify_bundle(archive)}
    from tools.protocol.bundle import PROTOCOL_TEXT, ROOT, tools_digest, tools_entries

    text = ROOT / "docs" / PROTOCOL_TEXT
    return {"source": "repository", "bundle_sha256": None, "tools_sha256": tools_digest(tools_entries()),
            "spec_sha256": _sha256(Path(spec.__file__).read_bytes()),
            "protocole_md_sha256": _sha256(text.read_bytes()) if text.exists() else None, "faker": faker_version()}


def registration(bundle: Path | None = None) -> dict[str, Any]:
    """Ce qu'il faut publier avant le lancement / what to publish before the launch."""
    out: dict[str, Any] = {"protocol": spec.PROTOCOL_VERSION, "written": spec.PROTOCOL_REGISTERED, **provenance(),
                           "registered_plan": spec.REGISTERED_PLAN}
    if bundle is not None:
        digests = verify_bundle(bundle)
        out["bundle"] = {"path": bundle.name, **digests,
                         "matches_repository": all(digests[k] == out[k] for k in ("tools_sha256", "spec_sha256",
                                                                                   "protocole_md_sha256", "faker"))}
    return out


def plan_matches_registration(observed: dict[str, Any]) -> bool:
    """Décompte observé (documents, empreintes, Faker) = décompte enregistré / observed count = registered count."""
    expected = spec.REGISTERED_PLAN
    return all(observed.get(key) == expected[key] for key in expected)
