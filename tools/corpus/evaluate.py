"""Évaluation massive sur le corpus à valeurs plantées / massive evaluation on the planted-value corpus.

Aucune annotation manuelle : les valeurs à masquer et les leurres à conserver sont connus par construction.
No manual annotation: values to mask and decoys to keep are known by construction.

Mesures / metrics :
- fuite (leak) : une valeur plantée reste lisible dans la sortie, par type, avec intervalle de Wilson à 95 % ;
- personnes : un jeton de nom (prénom, nom) reste lisible ;
- sur-masquage : un leurre a été modifié ;
- cohérence : toutes les formes d'une personne -> une seule balise ; deux personnes -> deux balises ;
- robustesse : mêmes mesures sur des variantes perturbées (espaces insécables, invisibles, pleine chasse,
  homoglyphes, fautes de frappe qui rendent la clé de contrôle fausse) ;
- débit et latence.

Usage : python tools/corpus/evaluate.py [--limit N] [--profile standard] [--no-mutations] [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from gdprguardian import Anonymizer
from gdprguardian.operators import get_operator
from gdprguardian.scope import Scope

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "datasets" / "fr"
PERSON_KEYS = ("email", "phone", "nir", "birth_date", "address", "iban", "card", "passport", "plate")
_DIGITS = re.compile(r"\D")
_FULLWIDTH = {ord(c): ord(c) - 0x30 + 0xFF10 for c in "0123456789"}
_HOMOGLYPHS = {ord("a"): "а", ord("e"): "е", ord("o"): "о", ord("p"): "р", ord("c"): "с"}


def wilson_upper(failures: int, total: int, z: float = 1.96) -> float:
    """Borne haute à 95 % du taux d'échec / 95 % upper bound of the failure rate."""
    if total == 0:
        return 0.0
    p = failures / total
    centre = p + z * z / (2 * total)
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return min(1.0, (centre + margin) / (1 + z * z / total))


# --- Perturbations (appliquées aux valeurs plantées dans le texte) / mutations of planted values -------------

def _nbsp(value: str) -> str:
    return value.replace(" ", " ")


def _narrow(value: str) -> str:
    return value.replace(" ", " ")


def _zero_width(value: str) -> str:
    return value[: len(value) // 2] + "​" + value[len(value) // 2:] if len(value) > 4 else value


def _fullwidth(value: str) -> str:
    return value.translate(_FULLWIDTH)


def _homoglyph(value: str) -> str:
    return value.translate(_HOMOGLYPHS) if "@" in value else value


def _typo(value: str) -> str:
    """Faute de frappe : dernier chiffre changé, la clé devient fausse / last digit changed, key becomes wrong."""
    for i in range(len(value) - 1, -1, -1):
        if value[i].isdigit():
            return value[:i] + str((int(value[i]) + 1) % 10) + value[i + 1:]
    return value


MUTATIONS = {"nbsp": _nbsp, "narrow_nbsp": _narrow, "zero_width": _zero_width, "fullwidth": _fullwidth,
             "homoglyph_email": _homoglyph, "typo": _typo}


@dataclass
class Tally:
    total: Counter = field(default_factory=Counter)
    leaks: Counter = field(default_factory=Counter)
    examples: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add(self, kind: str, leaked: bool, example: str) -> None:
        self.total[kind] += 1
        if leaked:
            self.leaks[kind] += 1
            if len(self.examples[kind]) < 8:
                self.examples[kind].append(example)

    def table(self) -> list[dict]:
        rows = []
        for kind in sorted(self.total):
            n, k = self.total[kind], self.leaks[kind]
            rows.append({"type": kind, "n": n, "leaks": k, "recall": round(1 - k / n, 5),
                         "leak_rate_upper95": round(wilson_upper(k, n), 5)})
        return rows


def _leaked(value: str, output: str) -> bool:
    """Une valeur fuit si elle reste telle quelle, ou si sa suite de chiffres (≥ 8) reste / leak check."""
    if value in output:
        return True
    digits = _DIGITS.sub("", value)
    return len(digits) >= 8 and digits in _DIGITS.sub("", output)


def _name_tokens(person: dict) -> list[str]:
    tokens = re.findall(r"[^\W\d_]{3,}", f"{person['given']} {person['surname']}")
    return [t for t in tokens if t.lower() not in {"van", "der", "den", "des", "del", "dos", "las"}]


def _token_count(token: str, text: str) -> int:
    return len(re.findall(rf"(?<![\w]){re.escape(token)}(?![\w])", text))


def load_corpus(limit: int | None) -> list[tuple[dict, str]]:
    items = []
    with (CORPUS / "manifests.jsonl").open(encoding="utf-8") as handle:
        for manifest in map(json.loads, handle):
            path = CORPUS / "docs" / f"{manifest['id']}.md"
            if path.exists():
                items.append((manifest, path.read_text(encoding="utf-8")))
            if limit and len(items) >= limit:
                break
    return items


def evaluate_document(anonymizer: Anonymizer, manifest: dict, text: str, values: Tally, persons: Tally,
                      decoys: Tally, policy: Tally, consistency: Counter) -> float:
    started = time.perf_counter()
    result = anonymizer.anonymize(text)
    elapsed = time.perf_counter() - started
    output = result.text
    for person in manifest["persons"]:
        for key in PERSON_KEYS:
            value = person.get(key)
            if value and value in text:
                values.add(key, _leaked(value, output), f"{manifest['id']}: {value}")
        for token in _name_tokens(person):
            present = _token_count(token, text)
            if not present:
                continue
            kept_in_decoys = sum(_token_count(token, d) for d in manifest["decoys"] if d in output)
            leaked = _token_count(token, output) - kept_in_decoys > 0
            persons.add("name_token", leaked, f"{manifest['id']}: {token}")
    company = manifest["company"]
    for key in ("siret", "tva"):
        if company[key] in text:
            if company["sole_trader"]:
                values.add(f"company_{key}_sole_trader", _leaked(company[key], output), f"{manifest['id']}")
            else:
                # Personne morale : conservé par défaut (politique) / legal person: kept by default.
                policy.add(f"company_{key}_kept", company[key] not in output, f"{manifest['id']}")
    for decoy in manifest["decoys"]:
        if decoy in text:
            names = {t for p in manifest["persons"] for t in _name_tokens(p)}
            if any(_token_count(t, decoy) for t in names):
                continue  # leurre contenant un nom de personne : ambigu, exclu / ambiguous decoy
            decoys.add("decoy_altered", decoy not in output, f"{manifest['id']}: {decoy}")
    _consistency(anonymizer, manifest, text, consistency)
    return elapsed


def _consistency(anonymizer: Anonymizer, manifest: dict, text: str, counter: Counter) -> None:
    """Rejoue l'attribution des balises pour vérifier la coréférence / replays placeholders for coreference."""
    analysis = anonymizer.analyze(text)
    replace = get_operator("replace")
    with Scope() as scope:
        scope.reserve(text)
        placeholders = [(s.start, s.end, replace(s, text[s.start:s.end], scope))
                        for s in analysis.spans if s.personal and s.entity == "PERSON"]
    seen: dict[str, int] = {}
    for index, person in enumerate(manifest["persons"]):
        found = set()
        for form in person["allowed_forms"]:
            for m in re.finditer(rf"(?<![\w]){re.escape(form)}(?![\w])", text):
                for start, end, placeholder in placeholders:
                    if start < m.end() and m.start() < end:
                        found.add(placeholder)
        if not found:
            continue
        counter["persons"] += 1
        counter["consistent" if len(found) == 1 else "split"] += 1
        for placeholder in found:
            if placeholder in seen and seen[placeholder] != index:
                counter["merged_with_other_person"] += 1
            seen[placeholder] = index


def _mutated(manifest: dict, text: str, mutation: str) -> tuple[dict, str]:
    function = MUTATIONS[mutation]
    clone = json.loads(json.dumps(manifest))
    for person in clone["persons"]:
        for key in PERSON_KEYS:
            value = person.get(key)
            if value and value in text:
                changed = function(value)
                text = text.replace(value, changed)
                person[key] = changed
    return clone, text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--profile", default="standard")
    parser.add_argument("--countries", default="FR")
    parser.add_argument("--no-mutations", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks" / "results")
    args = parser.parse_args()
    corpus = load_corpus(args.limit)
    if not corpus:
        raise SystemExit("Corpus vide / empty corpus: datasets/fr/docs/*.md")
    anonymizer = Anonymizer(countries=args.countries, profile=args.profile)
    values, persons, decoys, policy = Tally(), Tally(), Tally(), Tally()
    consistency: Counter = Counter()
    latencies = []
    characters = 0
    errors: list[str] = []
    for manifest, text in corpus:
        try:
            latencies.append(evaluate_document(anonymizer, manifest, text, values, persons, decoys, policy,
                                               consistency))
        except Exception as error:  # un plantage est une mesure / a crash is a measurement
            errors.append(f"{manifest['id']}: {type(error).__name__}: {error}"[:300])
            continue
        characters += len(text)
    mutation_rows = {}
    if not args.no_mutations:
        rng = random.Random(7)
        for mutation in MUTATIONS:
            tally = Tally()
            for manifest, text in rng.sample(corpus, k=min(len(corpus), 300)):
                clone, changed = _mutated(manifest, text, mutation)
                try:
                    evaluate_document(anonymizer, clone, changed, tally, Tally(), Tally(), Tally(), Counter())
                except Exception as error:
                    errors.append(f"{manifest['id']}[{mutation}]: {type(error).__name__}: {error}"[:300])
            mutation_rows[mutation] = tally.table()
    total_time = sum(latencies) or 1e-9
    report = {
        "documents": len(corpus),
        "errors": len(errors),
        "error_examples": errors[:20],
        "characters": characters,
        "profile": args.profile,
        "countries": args.countries,
        "native": getattr(anonymizer, "native", False),
        "values": values.table(),
        "names": persons.table(),
        "decoys": decoys.table(),
        "policy_company_ids": policy.table(),
        "consistency": dict(consistency),
        "mutations": mutation_rows,
        "throughput_mb_s": round(characters / total_time / 1e6, 3),
        "latency_ms": {"p50": round(statistics.median(latencies) * 1000, 3),
                       "p95": round(sorted(latencies)[int(0.95 * (len(latencies) - 1))] * 1000, 3)},
        "leak_examples": {k: v for t in (values, persons) for k, v in t.examples.items()},
        "decoy_examples": dict(decoys.examples),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"corpus_fr_{args.profile}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if not k.endswith("examples")}, ensure_ascii=False, indent=1))
    print(f"-> {path}")


if __name__ == "__main__":
    main()
