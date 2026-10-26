"""Corpus français annoté et mesures de rappel / annotated French corpus and recall metrics."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from gdprguardian.types import Span

CORPUS_PATH = Path(__file__).with_name("data") / "fr_sentences.txt"
# Rédigé après le réglage des seuils, jamais utilisé pour régler / written after tuning, never used to tune.
HELDOUT_PATH = CORPUS_PATH.with_name("fr_heldout.txt")
GOLD_RE = re.compile(r"\[\[(PER|ORG|LOC):([^\]]+)\]\]")
ENTITY_OF = {"PER": "PERSON", "ORG": "ORG", "LOC": "LOCATION"}
# Types acceptés pour un lieu : une adresse le couvre aussi / an address also covers a location.
ACCEPTED = {"PERSON": {"PERSON"}, "ORG": {"ORG"}, "LOCATION": {"LOCATION", "ADDRESS"}}
NAMED = frozenset({"PERSON", "ORG", "LOCATION"})


@dataclass(frozen=True, slots=True)
class Sample:
    text: str
    gold: tuple[tuple[str, int, int], ...]


def parse(line: str) -> Sample:
    """`[[PER:Jean]] à [[LOC:Lyon]]` -> texte brut + zones de référence / plain text + gold zones."""
    line = line.replace("\\n", "\n")
    parts: list[str] = []
    gold: list[tuple[str, int, int]] = []
    cursor = 0
    length = 0
    for m in GOLD_RE.finditer(line):
        parts.append(line[cursor:m.start()])
        length += m.start() - cursor
        value = m.group(2)
        gold.append((ENTITY_OF[m.group(1)], length, length + len(value)))
        parts.append(value)
        length += len(value)
        cursor = m.end()
    parts.append(line[cursor:])
    return Sample("".join(parts), tuple(gold))


def load_corpus(path: Path = CORPUS_PATH) -> list[Sample]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [parse(line) for line in lines if line.strip() and not line.startswith("#")]


@dataclass(slots=True)
class Report:
    gold: dict[str, int] = field(default_factory=dict)
    covered: dict[str, int] = field(default_factory=dict)
    typed: dict[str, int] = field(default_factory=dict)
    false_positives: int = 0
    predicted: int = 0
    missed: list[tuple[str, str]] = field(default_factory=list)

    def recall(self, entity: str | None = None, typed: bool = False) -> float:
        counts = self.typed if typed else self.covered
        keys = [entity] if entity else list(self.gold)
        total = sum(self.gold.get(k, 0) for k in keys)
        return sum(counts.get(k, 0) for k in keys) / total if total else 1.0

    def summary(self) -> str:
        rows = [f"{e:9} {self.covered.get(e, 0):3}/{n:3} masked ({self.recall(e):.1%}), "
                f"typed {self.recall(e, typed=True):.1%}" for e, n in sorted(self.gold.items())]
        rows.append(f"ALL       masked {self.recall():.1%}, typed {self.recall(typed=True):.1%}, "
                    f"false positives {self.false_positives}/{self.predicted}")
        return "\n".join(rows)


def _covers(spans: Iterable[Span], text: str, start: int, end: int) -> bool:
    """Tous les caractères alphanumériques de la zone sont masqués / every alphanumeric char is masked."""
    needed = {i for i in range(start, end) if text[i].isalnum()}
    for span in spans:
        needed.difference_update(range(span.start, span.end))
    return not needed


def evaluate(samples: Sequence[Sample], predictions: Sequence[Sequence[Span]]) -> Report:
    report = Report()
    for sample, spans in zip(samples, predictions, strict=True):
        personal = [s for s in spans if s.personal]
        for entity, start, end in sample.gold:
            report.gold[entity] = report.gold.get(entity, 0) + 1
            if _covers(personal, sample.text, start, end):
                report.covered[entity] = report.covered.get(entity, 0) + 1
            else:
                report.missed.append((entity, sample.text[start:end]))
            if _covers([s for s in personal if s.entity in ACCEPTED[entity]], sample.text, start, end):
                report.typed[entity] = report.typed.get(entity, 0) + 1
        for span in personal:
            if span.entity not in NAMED:
                continue
            report.predicted += 1
            if not any(span.start < end and start < span.end for _, start, end in sample.gold):
                report.false_positives += 1
    return report
