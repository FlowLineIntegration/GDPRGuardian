"""Métriques de masquage : caractère, mention, entité (TAB), fuites, sur-masquage, leurres.

Masking metrics: character, mention, entity (TAB-style), leaks, over-masking, decoys. Pure functions:
inputs are a gold document and the masked intervals in ORIGINAL offsets; only alphanumeric characters
are scored (TAB ignores whitespace and punctuation; its English POS rule is not ported).
Significant/masked character sets are bytearrays combined as big integers (C speed, no per-char loop).
"""

from __future__ import annotations

import math
import random
import re
import unicodedata
from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, fields
from functools import cache
from itertools import accumulate
from typing import Any

from tools.eval.schema import DIRECT, NO_MASK, QUASI, Document, GoldSpan

LENIENT_RUN = 4          # fuite « souple » : ≥ 4 caractères consécutifs visibles / lenient leak threshold
IOU_THRESHOLD = 0.9      # appariement de zones (presidio-evaluator) / span matching threshold
F_BETA = 2.0             # F2 : le rappel pèse 4 fois plus / recall weighted 4x
# Entités textuelles (heuristiques, NER) vs identifiants structurés (motifs, clés).
# Textual entities (heuristics, NER) vs structured identifiers (patterns, checksums).
TEXTUAL_LABELS = frozenset({"PERSON", "ADDRESS", "LOCATION", "ORG"})
_SIGNIFICANT_RE = re.compile(r"[^\W_]+")
_VISIBLE_RUN_RE = re.compile(rb"\x02{%d,}" % LENIENT_RUN)
_Z95 = 1.959963984540054
# Default_Ignorable_Code_Point (Unicode DerivedCoreProperties) : sélecteurs de variante, U+034F, remplisseurs
# hangûl… ; s'ajoutent aux caractères de format (Cf). Variation selectors, U+034F, Hangul fillers, added to Cf.
_DEFAULT_IGNORABLE = ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
                      (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164),
                      (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
                      (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF))
# Ordre des statistiques par document (bootstrap) / per-document statistics order (bootstrap).
STAT_FIELDS = ("direct_gold", "direct_hit", "structured_gold", "structured_hit", "gold", "hit", "pred", "pred_ok",
               "entities_direct", "entities_direct_masked", "leak_strict", "leak_structured", "neutral",
               "neutral_masked", "decoys", "decoys_hit")


def label_group(label: str) -> str:
    return "textual" if label in TEXTUAL_LABELS else "structured"


@dataclass(frozen=True, slots=True)
class Masked:
    """Zone masquée par le système, positions du texte original / system-masked zone, original offsets."""

    start: int
    end: int
    label: str
    source: str = ""


@dataclass(slots=True)
class DocScore:
    """Note d'un document / score of one document."""

    tally: Tally
    stats: list[int]          # vecteur `STAT_FIELDS` (bootstrap) / `STAT_FIELDS` vector
    masked: list[bool]        # par zone annotée : entièrement masquée ? / per gold span: fully masked?


@dataclass(slots=True)
class Tally:
    """Compteurs additifs d'un ou plusieurs documents / additive counters for one or more documents."""

    docs: int = 0
    docs_leak_strict: int = 0
    docs_leak_structured: int = 0
    docs_leak_lenient: int = 0
    docs_leak_verbatim: int = 0
    neutral_chars: int = 0
    neutral_masked: int = 0
    pred_total: int = 0
    pred_ok_total: int = 0
    pred_on_decoys: int = 0
    gold_chars: Counter[str] = field(default_factory=Counter)
    hit_chars: Counter[str] = field(default_factory=Counter)
    mentions: Counter[str] = field(default_factory=Counter)
    mentions_masked: Counter[str] = field(default_factory=Counter)
    mentions_strict: Counter[str] = field(default_factory=Counter)
    mentions_leak_lenient: Counter[str] = field(default_factory=Counter)
    mentions_iou: Counter[str] = field(default_factory=Counter)
    mentions_typed: Counter[str] = field(default_factory=Counter)
    pred_chars: Counter[str] = field(default_factory=Counter)
    pred_ok_chars: Counter[str] = field(default_factory=Counter)
    pred_spans: Counter[str] = field(default_factory=Counter)
    pred_spans_iou: Counter[str] = field(default_factory=Counter)
    sources: Counter[str] = field(default_factory=Counter)
    entities: Counter[str] = field(default_factory=Counter)
    entities_masked: Counter[str] = field(default_factory=Counter)
    entities_strict: Counter[str] = field(default_factory=Counter)
    docs_with_label: Counter[str] = field(default_factory=Counter)
    docs_leak_label: Counter[str] = field(default_factory=Counter)
    kind_docs: Counter[str] = field(default_factory=Counter)
    kind_leaks: Counter[str] = field(default_factory=Counter)
    kind_leaks_structured: Counter[str] = field(default_factory=Counter)
    # Clés (opérateur, libellé) / keys (operator, label)
    mutation_mentions: Counter[tuple[str, str]] = field(default_factory=Counter)
    mutation_masked: Counter[tuple[str, str]] = field(default_factory=Counter)
    mutation_chars: Counter[tuple[str, str]] = field(default_factory=Counter)
    mutation_hit: Counter[tuple[str, str]] = field(default_factory=Counter)
    mutation_leak_lenient: Counter[tuple[str, str]] = field(default_factory=Counter)
    # Survie : masquées avant mutation, et encore après / survival: masked before mutation, and still after
    mutation_baseline: Counter[tuple[str, str]] = field(default_factory=Counter)
    mutation_survived: Counter[tuple[str, str]] = field(default_factory=Counter)
    confusion: Counter[tuple[str, str]] = field(default_factory=Counter)
    # Exemples avec valeurs : corpus SYNTHÉTIQUE uniquement (rapports) / with values: synthetic corpus only.
    misses: list[dict[str, Any]] = field(default_factory=list)
    false_masks: list[dict[str, Any]] = field(default_factory=list)

    def merge(self, other: Tally) -> Tally:
        """Ajoute `other` en place ; `Counter +=` omet les zéros (absent = 0) / in place; zeros are dropped."""
        for f in fields(self):
            mine = getattr(self, f.name)
            theirs = getattr(other, f.name)
            if isinstance(mine, (Counter, list)):
                mine += theirs
            else:
                setattr(self, f.name, mine + theirs)
        return self


def significant_mask(text: str) -> bytearray:
    """1 pour chaque caractère alphanumérique / 1 for every alphanumeric character."""
    mask = bytearray(len(text))
    for m in _SIGNIFICANT_RE.finditer(text):
        mask[m.start():m.end()] = b"\x01" * (m.end() - m.start())
    return mask


def _paint(size: int, intervals: Iterable[tuple[int, int]]) -> bytearray:
    mask = bytearray(size)
    for start, end in intervals:
        mask[start:end] = b"\x01" * (end - start)
    return mask


def _as_int(mask: bytes | bytearray) -> int:
    return int.from_bytes(mask, "big")


@cache
def _ignorable_re() -> re.Pattern[str]:
    """Classe regex des invisibles : format (Cf) et « default ignorable » / Cf and default-ignorable chars.

    Construite une fois par processus (balayage des catégories, ~0,1 s) / built once per process.
    """
    points = {cp for cp in range(0x110000) if unicodedata.category(chr(cp)) == "Cf"}
    for low, high in _DEFAULT_IGNORABLE:
        points.update(range(low, high + 1))
    ranges: list[list[int]] = []
    for cp in sorted(points):
        if ranges and ranges[-1][1] == cp - 1:
            ranges[-1][1] = cp
        else:
            ranges.append([cp, cp])
    return re.compile("[" + "".join(f"{re.escape(chr(a))}-{re.escape(chr(b))}" for a, b in ranges) + "]")


def canonical(text: str) -> str:
    """Forme de comparaison : sans invisibles, puis NFKC / comparison form: invisibles removed, then NFKC.

    La sortie de Gardien RGPD est nettoyée de certains invisibles : on compare donc des formes canoniques,
    des deux côtés, pour ne jamais rater une fuite littérale. GDPR Guardian strips some invisibles from its
    output, so both sides are compared in canonical form and a verbatim leak is never missed.
    """
    if text.isascii():
        return text
    return unicodedata.normalize("NFKC", _ignorable_re().sub("", text))


def _verbatim_candidate(span: GoldSpan, value: str) -> bool:
    """Valeur assez distinctive pour une recherche littérale / distinctive enough for a literal search."""
    if span.label == "PERSON":
        return len(value.split()) >= 2
    return len(value) >= 4


def score_document(doc: Document, masked: Sequence[Masked], output: str | None = None,
                   baseline: Sequence[bool] | None = None) -> DocScore:
    """Évalue un document / scores one document.

    `output` : texte anonymisé, pour la recherche littérale de fuites / anonymised text, for verbatim leaks.
    `baseline` : pour un document muté, zones masquées dans sa version d'origine (même ordre), afin de
    mesurer la survie aux mutations / for a mutated document, spans masked in its original version.
    Les zones masquées peuvent se chevaucher ; hors bornes, elles lèvent ValueError (elles décaleraient
    silencieusement tous les masques). Masked zones may overlap; out-of-bounds zones raise ValueError.
    """
    text = doc.text
    size = len(text)
    if baseline is not None and len(baseline) != len(doc.spans):
        raise ValueError(f"{doc.doc_id}: référence de survie incohérente / baseline length mismatch")
    for m in masked:
        if not 0 <= m.start <= m.end <= size:
            raise ValueError(f"{doc.doc_id}: zone masquée hors bornes / masked zone out of bounds ({m.start}, {m.end})")
    tally = Tally(docs=1)
    tally.kind_docs[doc.kind] += 1
    masked = sorted(masked, key=lambda m: m.start)
    # Fin maximale des zones 0..i (croissante) : trouve aussi les zones englobantes / running max end.
    reach = list(accumulate((m.end for m in masked), max))
    sig = significant_mask(text)
    mask = _paint(size, ((m.start, m.end) for m in masked))
    to_mask = _paint(size, ((s.start, s.end) for s in doc.spans if s.identifier_type != NO_MASK))
    decoy = _paint(size, ((s.start, s.end) for s in doc.spans if s.identifier_type == NO_MASK))
    sig_i, mask_i, to_mask_i, decoy_i = _as_int(sig), _as_int(mask), _as_int(to_mask), _as_int(decoy)
    visible_i = sig_i & ~mask_i
    # 0 = non significatif, 1 = significatif masqué, 2 = significatif visible / 0 n/a, 1 masked, 2 visible.
    code = (sig_i + visible_i).to_bytes(size, "big")
    ok_bytes = (sig_i & to_mask_i).to_bytes(size, "big")
    masked_sig_i = sig_i & mask_i

    tally.pred_total = masked_sig_i.bit_count()
    tally.pred_ok_total = (masked_sig_i & to_mask_i).bit_count()
    tally.pred_on_decoys = (masked_sig_i & decoy_i).bit_count()
    neutral_i = sig_i & ~(to_mask_i | decoy_i)
    tally.neutral_chars = neutral_i.bit_count()
    tally.neutral_masked = (neutral_i & mask_i).bit_count()

    gold_starts = [s.start for s in doc.spans]
    canonical_output = canonical(output) if output is not None else None
    # Entité masquée ssi toutes ses mentions le sont (TAB) / entity masked iff all its mentions are (TAB).
    entity_masked: dict[str, bool] = {}
    entity_strict: dict[str, bool] = {}
    entity_meta: dict[str, tuple[str, str]] = {}
    stats = dict.fromkeys(STAT_FIELDS, 0)
    leak_strict = leak_structured = leak_lenient = leak_verbatim = False
    leaked_labels: set[str] = set()
    flags: list[bool] = []

    for index, span in enumerate(doc.spans):
        segment = code[span.start:span.end]
        significant = len(segment) - segment.count(0)
        visible = segment.count(2)
        hit = significant - visible
        label = span.label
        if span.identifier_type == NO_MASK:
            stats["decoys"] += 1
            stats["decoys_hit"] += hit > 0
            tally.mentions[label] += 1
            tally.mentions_masked[label] += hit > 0  # pour un leurre : masqué à tort / decoy: wrongly masked
            flags.append(hit > 0)
            continue
        fully = significant > 0 and visible == 0
        flags.append(fully)
        strict = fully and _covered(mask, span, segment)
        lenient_leak = _VISIBLE_RUN_RE.search(segment.replace(b"\x00", b"")) is not None
        tally.gold_chars[label] += significant
        tally.hit_chars[label] += hit
        tally.mentions[label] += 1
        tally.mentions_masked[label] += fully
        tally.mentions_strict[label] += strict
        tally.mentions_leak_lenient[label] += lenient_leak
        best, best_iou = _dominant(masked, reach, span)
        if best is not None:
            tally.confusion[(label, best.label)] += 1
            tally.mentions_typed[label] += fully and best.label == label
            tally.mentions_iou[label] += best_iou >= IOU_THRESHOLD
        stats["gold"] += significant
        stats["hit"] += hit
        if span.mutation is not None:
            key = (span.mutation, label)
            tally.mutation_mentions[key] += 1
            tally.mutation_masked[key] += fully
            tally.mutation_chars[key] += significant
            tally.mutation_hit[key] += hit
            tally.mutation_leak_lenient[key] += lenient_leak
            if baseline is not None and baseline[index]:
                tally.mutation_baseline[key] += 1
                tally.mutation_survived[key] += fully
        entity_masked[span.entity_id] = entity_masked.get(span.entity_id, True) and fully
        entity_strict[span.entity_id] = entity_strict.get(span.entity_id, True) and strict
        entity_meta.setdefault(span.entity_id, (span.identifier_type, label))
        if span.identifier_type == DIRECT:
            stats["direct_gold"] += significant
            stats["direct_hit"] += hit
            if label not in TEXTUAL_LABELS:
                stats["structured_gold"] += significant
                stats["structured_hit"] += hit
            if visible:
                leak_strict = True
                leak_structured |= label not in TEXTUAL_LABELS
                leaked_labels.add(label)
            leak_lenient |= lenient_leak
            value = text[span.start:span.end]
            if canonical_output is not None and _verbatim_candidate(span, value):
                leak_verbatim |= _found(canonical(value), canonical_output)
        if not fully:
            tally.misses.append({"doc_id": doc.doc_id, "label": label, "mutation": span.mutation,
                                 "value": text[span.start:span.end], "visible": visible,
                                 "significant": significant, "masked_as": best.label if best else None})

    for entity_id, (identifier_type, label) in entity_meta.items():
        masked_ok, strict_ok = entity_masked[entity_id], entity_strict[entity_id]
        for key in (identifier_type, f"{identifier_type}:{label}"):
            tally.entities[key] += 1
            tally.entities_masked[key] += masked_ok
            tally.entities_strict[key] += strict_ok
        if identifier_type == DIRECT:
            stats["entities_direct"] += 1
            stats["entities_direct_masked"] += masked_ok

    for m in masked:
        chars = sig[m.start:m.end].count(1)
        ok = ok_bytes[m.start:m.end].count(1)
        tally.pred_chars[m.label] += chars
        tally.pred_ok_chars[m.label] += ok
        tally.pred_spans[m.label] += 1
        tally.sources[m.source] += 1
        tally.pred_spans_iou[m.label] += _best_gold_iou(doc.spans, gold_starts, m) >= IOU_THRESHOLD
        if chars and not ok:
            tally.false_masks.append({"doc_id": doc.doc_id, "label": m.label, "source": m.source,
                                      "value": text[m.start:m.end], "on_decoy": decoy[m.start:m.end].count(1) > 0})

    tally.docs_leak_strict = int(leak_strict)
    tally.docs_leak_structured = int(leak_structured)
    tally.docs_leak_lenient = int(leak_lenient)
    tally.docs_leak_verbatim = int(leak_verbatim)
    tally.docs_leak_label.update(leaked_labels)
    tally.docs_with_label.update({s.label for s in doc.spans if s.identifier_type != NO_MASK})
    tally.kind_leaks[doc.kind] += leak_strict
    tally.kind_leaks_structured[doc.kind] += leak_structured
    stats.update(pred=tally.pred_total, pred_ok=tally.pred_ok_total, leak_strict=int(leak_strict),
                 leak_structured=int(leak_structured), neutral=tally.neutral_chars,
                 neutral_masked=tally.neutral_masked)
    return DocScore(tally, [stats[name] for name in STAT_FIELDS], flags)


def _covered(mask: bytearray, span: GoldSpan, segment: bytes) -> bool:
    """Tout est couvert entre le premier et le dernier caractère significatif / all covered in between."""
    left = len(segment) - len(segment.lstrip(b"\x00"))
    right = len(segment.rstrip(b"\x00"))
    return mask[span.start + left:span.start + right].count(0) == 0


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def _dominant(masked: Sequence[Masked], reach: list[int], span: GoldSpan) -> tuple[Masked | None, float]:
    """Zone masquée qui couvre le plus la mention, et son IoU / most-overlapping masked zone and its IoU.

    `masked` est trié par début et `reach[i]` = max des fins de masked[0..i] : la première zone qui peut
    chevaucher est donc trouvée par bisection, même si une zone en englobe d'autres.
    `masked` is sorted by start and `reach` is the running max end, so nested zones are found too.
    """
    best, best_overlap = None, 0
    index = bisect_right(reach, span.start)
    while index < len(masked) and masked[index].start < span.end:
        candidate = masked[index]
        overlap = _overlap(span.start, span.end, candidate.start, candidate.end)
        if overlap > best_overlap:
            best, best_overlap = candidate, overlap
        index += 1
    if best is None:
        return None, 0.0
    union = (span.end - span.start) + (best.end - best.start) - best_overlap
    return best, best_overlap / union


def _best_gold_iou(spans: Sequence[GoldSpan], starts: list[int], m: Masked) -> float:
    best = 0.0
    index = max(0, bisect_left(starts, m.start) - 1)
    while index < len(spans) and spans[index].start < m.end:
        gold = spans[index]
        if gold.identifier_type != NO_MASK:
            overlap = _overlap(gold.start, gold.end, m.start, m.end)
            if overlap:
                best = max(best, overlap / ((gold.end - gold.start) + (m.end - m.start) - overlap))
        index += 1
    return best


def _found(value: str, output: str) -> bool:
    """Recherche littérale bornée aux mots / word-bounded literal search."""
    return re.search(rf"(?<!\w){re.escape(value)}(?!\w)", output) is not None


# --- Agrégats / aggregates ------------------------------------------------------------------------------


def ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def f_beta(precision: float | None, recall: float | None, beta: float = F_BETA) -> float | None:
    """F-bêta ; None si une composante manque, 0 si les deux sont nulles / None if undefined."""
    if precision is None or recall is None:
        return None
    if precision == 0 and recall == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * precision * recall / (b2 * precision + recall)


def wilson(successes: int, total: int, z: float = _Z95) -> tuple[float | None, float | None]:
    """Intervalle de Wilson à 95 % pour une proportion / 95% Wilson interval for a proportion."""
    if total == 0:
        return None, None
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    # Bornes exactes aux extrêmes (évite 0,9999…) / exact bounds at the extremes (avoids 0.9999…).
    low = 0.0 if successes == 0 else max(0.0, centre - half)
    high = 1.0 if successes == total else min(1.0, centre + half)
    return low, high


def headline(totals: Sequence[float], docs: int) -> dict[str, float | None]:
    """Métriques principales depuis la somme des vecteurs `STAT_FIELDS` / headline metrics from sums."""
    t = dict(zip(STAT_FIELDS, totals, strict=True))
    precision = ratio(t["pred_ok"], t["pred"])
    recall = ratio(t["hit"], t["gold"])
    return {
        "recall_direct": ratio(t["direct_hit"], t["direct_gold"]),
        "recall_structured": ratio(t["structured_hit"], t["structured_gold"]),
        "recall": recall,
        "precision": precision,
        "f2": f_beta(precision, recall),
        "entity_recall_direct": ratio(t["entities_direct_masked"], t["entities_direct"]),
        "doc_leak_rate": ratio(t["leak_strict"], docs),
        "doc_leak_rate_structured": ratio(t["leak_structured"], docs),
        "over_masking": ratio(t["neutral_masked"], t["neutral"]),
        "decoy_false_mask_rate": ratio(t["decoys_hit"], t["decoys"]),
    }


def bootstrap(stats: Sequence[Sequence[int]], metric: Callable[[Sequence[float], int], dict[str, float | None]],
              resamples: int = 1000, seed: int = 0) -> dict[str, tuple[float | None, float | None]]:
    """IC à 95 % par rééchantillonnage des DOCUMENTS (percentiles) / 95% CI resampling documents.

    numpy accélère le calcul s'il est installé ; sinon, repli en Python pur (même méthode).
    numpy speeds it up when installed; otherwise a pure-Python fallback (same method).
    """
    count = len(stats)
    if count == 0:
        return {}
    samples: dict[str, list[float]] = {}
    for totals in _resampled_totals(stats, resamples, seed):
        for key, value in metric(totals, count).items():
            if value is not None:
                samples.setdefault(key, []).append(value)
    return {key: (_percentile(values, 2.5), _percentile(values, 97.5)) for key, values in samples.items()}


def _resampled_totals(stats: Sequence[Sequence[int]], resamples: int, seed: int) -> Iterable[list[int]]:
    count = len(stats)
    try:
        import numpy as np
    except ImportError:
        rng = random.Random(seed)
        columns = list(zip(*stats, strict=True))
        for _ in range(resamples):
            picks = rng.choices(range(count), k=count)
            yield [sum(column[i] for i in picks) for column in columns]
        return
    data = np.asarray(stats, dtype=np.int64)
    generator = np.random.default_rng(seed)
    for _ in range(resamples):
        yield data[generator.integers(0, count, count)].sum(axis=0).tolist()


def _percentile(values: Sequence[float], q: float) -> float:
    """Percentile par interpolation linéaire (comme numpy par défaut) / linear-interpolation percentile."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


__all__ = ["DIRECT", "NO_MASK", "QUASI", "STAT_FIELDS", "TEXTUAL_LABELS", "DocScore", "Masked", "Tally", "bootstrap",
           "canonical", "f_beta", "headline", "label_group", "ratio", "score_document", "significant_mask", "wilson"]
