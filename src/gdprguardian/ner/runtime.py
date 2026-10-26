"""Exécution ONNX : jetons, fenêtres, lots, décisions par jeton. Sans état modifiable après chargement.

ONNX execution: tokens, windows, batches, per-token decisions. No mutable state once loaded (thread-safe).
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any

import numpy as np

from .chunking import plan_windows
from .decode import LabelScheme, Runs, group_runs, run_extents, token_decisions

# Positions RoBERTa/CamemBERT décalées de pad_token_id + 1 / RoBERTa-style position offset.
_OFFSET_POSITIONS = frozenset({"roberta", "camembert", "xlm-roberta", "xlm_roberta"})
# Un jeton prolonge une entité dès la moitié du seuil / a token extends an entity at half the threshold.
EXTEND_RATIO = 0.5


@dataclass(frozen=True, slots=True)
class Prediction:
    """Zones relatives aux textes d'entrée / zones relative to the input texts."""

    text_index: np.ndarray
    start: np.ndarray
    end: np.ndarray
    entity: np.ndarray
    score: np.ndarray
    sequences: int
    tokens: int


class TokenClassifier:
    """Session ONNX partagée + tokenizer ; `predict` est sûr entre threads / shared session, thread-safe."""

    def __init__(self, session: Any, tokenizer: Any, id2label: Mapping[int, str], *, pad_id: int,
                 max_length: int = 512) -> None:
        self.session = session
        self.tokenizer = tokenizer
        self.scheme = LabelScheme.from_labels(id2label)
        self.pad_id = pad_id
        self.max_length = max_length
        inputs = {i.name for i in session.get_inputs()}
        missing = {"input_ids", "attention_mask"} - inputs
        if missing:
            raise ValueError(f"entrées ONNX manquantes / missing ONNX inputs: {sorted(missing)}")
        self._token_types = "token_type_ids" in inputs
        output = session.get_outputs()[0]
        classes = (getattr(output, "shape", None) or [None])[-1]
        if isinstance(classes, int) and classes != self.scheme.classes:
            raise ValueError(f"config.json : {self.scheme.classes} classes, modèle / model: {classes}")
        self._output = output.name
        # Sans cache de mots (Unigram, BPE) : aucun mot d'un document ne survit à l'appel ; coût mesuré +0,5 ms
        # pour 10 Ko. No word cache: no word of a document outlives the call; measured cost +0.5 ms per 10 KB.
        resize_cache = getattr(getattr(tokenizer, "model", None), "_resize_cache", None)
        if resize_cache is not None:
            resize_cache(0)
        with_special = tokenizer.encode("a", add_special_tokens=True).ids
        plain = tokenizer.encode("a", add_special_tokens=False).ids
        cut = next((i for i in range(len(with_special) - len(plain) + 1)
                    if with_special[i:i + len(plain)] == plain), None)
        if not plain or cut is None:
            raise ValueError("tokenizer : jetons spéciaux introuvables / tokenizer: special tokens not found")
        self.prefix = tuple(with_special[:cut])
        self.suffix = tuple(with_special[cut + len(plain):])

    @property
    def entities(self) -> tuple[str, ...]:
        return self.scheme.entities

    @classmethod
    def load(cls, model_path: Path, tokenizer_path: Path, config_path: Path, *, threads: int) -> TokenClassifier:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        config = json.loads(config_path.read_text(encoding="utf-8"))
        id2label = {int(k): str(v) for k, v in config["id2label"].items()}
        pad_id = int(config.get("pad_token_id") or 0)
        positions = int(config.get("max_position_embeddings") or 512)
        if config.get("model_type") in _OFFSET_POSITIONS:
            positions -= pad_id + 1
        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        tokenizer.no_truncation()
        tokenizer.no_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.log_severity_level = 3
        # Pas d'attente active entre deux appels : les cœurs restent aux regex du moteur (mesuré neutre ou mieux).
        # No busy-wait between runs: cores stay free for the engine's regex work (measured neutral or better).
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        session = ort.InferenceSession(os.fspath(model_path), sess_options=options,
                                       providers=["CPUExecutionProvider"])
        return cls(session, tokenizer, id2label, pad_id=pad_id, max_length=min(positions, 512))

    def predict(self, texts: Sequence[str], thresholds: np.ndarray, *, max_tokens: int, overlap: int,
                batch_tokens: int) -> Prediction:
        """Entités de chaque texte, en positions de caractères relatives / entities, relative char offsets.

        Chaque texte est découpé en fenêtres de `max_tokens` jetons (spéciaux compris) se chevauchant de
        `overlap` jetons ; les fenêtres sont triées par longueur puis groupées en lots d'au plus `batch_tokens`
        jetons après remplissage (beaucoup de cellules courtes ou peu de longues fenêtres par appel).
        Hystérésis : un jeton rejoint une suite dès `EXTEND_RATIO` × seuil, la suite est gardée si son maximum
        atteint le seuil (« Transports Rivière » n'est pas coupé). Each text is cut into overlapping windows,
        sorted by length and batched by padded-token budget; hysteresis keeps multi-token entities whole.
        """
        thresholds = np.asarray(thresholds, np.float32)
        token_thresholds = thresholds * np.float32(EXTEND_RATIO)
        encodings = self.tokenizer.encode_batch(list(texts), add_special_tokens=False)
        lengths = np.fromiter((len(e.ids) for e in encodings), np.intp, len(encodings))
        total = int(lengths.sum())
        if total == 0:
            return _empty_prediction()
        token_base = np.zeros(len(encodings) + 1, np.intp)
        np.cumsum(lengths, out=token_base[1:])
        ids = np.fromiter(chain.from_iterable(e.ids for e in encodings), np.int64, total)
        offsets = np.array(list(chain.from_iterable(e.offsets for e in encodings)), np.int64).reshape(total, 2)

        width = min(max_tokens, self.max_length) - len(self.prefix) - len(self.suffix)
        if width < 8:
            raise ValueError("fenêtre trop étroite / window too narrow")
        # Chevauchement <= largeur / 4 : chaque fenêtre avance d'au moins une demi-largeur (coût linéaire).
        # Overlap <= width / 4: every window moves on by at least half a width (linear cost).
        overlap = min(overlap, width // 4)
        pieces: list[tuple[int, int, int, int, int]] = []
        for index, encoding in enumerate(encodings):
            length = int(lengths[index])
            if length == 0:
                continue
            word_starts = None
            if length > width:
                words = encoding.word_ids
                word_starts = [i == 0 or words[i] != words[i - 1] for i in range(length)]
            base = int(token_base[index])
            pieces.extend((base, s, e, own_s, own_e) for s, e, own_s, own_e in
                          plan_windows(length, word_starts, width, overlap))
        pieces.sort(key=lambda p: p[2] - p[1], reverse=True)

        entity = np.full(total, -1, np.int8)
        score = np.zeros(total, np.float32)
        begin = np.zeros(total, bool)
        head = len(self.prefix)
        stop = 0
        while stop < len(pieces):
            # Trié du plus long au plus court : la première séquence fixe la largeur du lot / longest first.
            longest = pieces[stop][2] - pieces[stop][1] + head + len(self.suffix)
            batch = pieces[stop:stop + max(1, batch_tokens // longest)]
            stop += len(batch)
            input_ids = np.full((len(batch), longest), self.pad_id, np.int64)
            mask = np.zeros((len(batch), longest), np.int64)
            for row, (base, s, e, _, _) in enumerate(batch):
                size = e - s
                input_ids[row, :head] = self.prefix
                input_ids[row, head:head + size] = ids[base + s:base + e]
                input_ids[row, head + size:head + size + len(self.suffix)] = self.suffix
                mask[row, :head + size + len(self.suffix)] = 1
            feeds = {"input_ids": input_ids, "attention_mask": mask}
            if self._token_types:
                feeds["token_type_ids"] = np.zeros_like(input_ids)
            logits = self.session.run([self._output], feeds)[0]
            batch_entity, batch_score, batch_begin = token_decisions(logits, self.scheme, token_thresholds)
            for row, (base, s, _, own_s, own_e) in enumerate(batch):
                src = slice(head + own_s - s, head + own_e - s)
                dst = slice(base + own_s, base + own_e)
                entity[dst] = batch_entity[row, src]
                score[dst] = batch_score[row, src]
                begin[dst] = batch_begin[row, src]

        # Jetons sans caractère écartés : ils ne coupent ni ne bornent une zone / zero-width tokens dropped.
        keep = np.flatnonzero(offsets[:, 1] > offsets[:, 0])
        text_of = np.repeat(np.arange(len(encodings)), lengths)[keep]
        breaks = np.ones(keep.size, bool)
        breaks[1:] = text_of[1:] != text_of[:-1]
        runs: Runs = group_runs(entity[keep], score[keep], begin[keep], breaks)
        runs = runs.select(runs.score >= thresholds[runs.entity])
        starts, ends = run_extents(offsets[keep, 0], offsets[keep, 1], runs)
        return Prediction(text_of[runs.first], starts, ends, runs.entity, runs.score, len(pieces), total)


def _empty_prediction() -> Prediction:
    empty = np.zeros(0, np.int64)
    return Prediction(empty, empty, empty, np.zeros(0, np.int8), np.zeros(0, np.float32), 0, 0)
