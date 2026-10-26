"""Décompte à blanc du plan, sans service : nombre exact de documents et empreintes / dry run, no service.

Génère chaque document synthétique et muté du plan exactement comme la campagne (même ordre, même empreinte), sans
rien envoyer ni écrire : le nombre de documents et les empreintes SHA-256 se publient AVANT la campagne, et chacun
peut vérifier qu'il régénère les mêmes documents (même version de Faker). Generates every synthetic and mutated
document of the plan exactly as the campaign does, sends and writes nothing: counts and SHA-256 fingerprints are
published BEFORE the campaign, and anyone can check that they regenerate the same documents.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

from tools.protocol.plan import Plan, synthetic_documents, track
from tools.protocol.provenance import faker_version


def count_plan(plan: Plan) -> dict[str, Any]:
    from tools.eval.generate import CorpusGenerator

    generators: dict[int, Any] = {}
    counts: Counter[str] = Counter()
    chars: Counter[str] = Counter()
    family = {"synthetic": hashlib.sha256(), "redteam": hashlib.sha256()}
    for unit in plan.units:
        if unit.kind == "real":
            continue
        seed = unit.seed or 0
        generator = generators.setdefault(seed, CorpusGenerator(seed))
        digest = hashlib.sha256()
        for key, doc, _ in synthetic_documents(unit, generator):
            group = key.split("/", 1)[0]
            counts[group] += 1
            chars[group] += len(doc.text)
            track(digest, doc.doc_id, doc.text)
        family[unit.kind].update(digest.hexdigest().encode())
    return {"documents": dict(counts), "documents_total_synthetic": sum(counts.values()), "chars": dict(chars),
            "synthetic_sha256": family["synthetic"].hexdigest(), "redteam_sha256": family["redteam"].hexdigest(),
            "faker": faker_version()}
