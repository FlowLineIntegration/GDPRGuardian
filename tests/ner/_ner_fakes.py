"""Doublures de test : tokenizer WordPiece en mémoire et session ONNX sans contexte.

Test doubles: in-memory WordPiece tokenizer and a context-free ONNX session.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from types import SimpleNamespace
from typing import Any

import numpy as np

from gdprguardian._text import fold, normalize
from gdprguardian.engine import DetectionContext, Settings

# Étiquettes au format du modèle cmarkea (schéma IO) / cmarkea-style labels (IO scheme).
IO_LABELS = {0: "O", 1: "I-LOC", 2: "I-PER", 3: "I-MISC", 4: "I-ORG"}
OUT, LOC, PER, MISC, ORG = range(5)
BIO_LABELS = {0: "O", 1: "B-PER", 2: "I-PER", 3: "B-ORG", 4: "I-ORG", 5: "B-LOC", 6: "I-LOC", 7: "B-MISC",
              8: "I-MISC"}

# Mot -> (classe, probabilité). « Dupont » n'existe qu'en sous-mots « Dup » + « ##ont » (seul « Dup » est
# étiqueté) : teste l'extension au mot entier / "Dupont" only exists as sub-words, only "Dup" is labelled.
LEXICON: dict[str, tuple[int, float]] = {
    "Jean": (PER, 0.99), "Pierre": (PER, 0.99), "Dup": (PER, 0.99), "##ont": (OUT, 0.9),
    "Martin": (PER, 0.97), "Claire": (PER, 0.98), "Vasseur": (PER, 0.98), "Léa": (PER, 0.4),
    "Ollivier": (PER, 0.95), "Fabienne": (PER, 0.95), "Orléans": (PER, 0.9), "il": (PER, 0.9),
    "Lyon": (LOC, 0.99), "Paris": (LOC, 0.99), "Necker": (LOC, 0.9), "hôpital": (LOC, 0.6),
    "Renault": (ORG, 0.99), "Transports": (ORG, 0.3), "Rivière": (ORG, 0.8), "Coupe": (MISC, 0.99),
}
_PLAIN_WORDS = (
    "le la les de du d l a à et en est un une avec chez pour M Mme Dr Bonjour contrat signé Le Il vu vient habite "
    "travaille dit que rue Monde hier marie curie madame dossier rapport prêt Signé Rendez vous Dossier Famille "
    "ORG_2 PERSONNE_3"
)
SPECIALS = ("[PAD]", "[UNK]", "[CLS]", "[SEP]")
VOCAB = {w: i for i, w in enumerate(dict.fromkeys(
    [*SPECIALS, *LEXICON, *_PLAIN_WORDS.split(), *".,;:!?'’-|«»()"]))}


def make_tokenizer() -> Any:
    from tokenizers import Tokenizer, models, pre_tokenizers, processors

    tokenizer = Tokenizer(models.WordPiece(VOCAB, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    tokenizer.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=[("[CLS]", VOCAB["[CLS]"]), ("[SEP]", VOCAB["[SEP]"])])
    return tokenizer


def _logits(label: int, probability: float, classes: int) -> np.ndarray:
    """Logits : `probability` pour la classe, le reste pour O (presque rien ailleurs).

    Logits giving `probability` to the class and the rest to O (almost nothing elsewhere).
    """
    probs = np.full(classes, 1e-6)
    probs[OUT] += 1.0 - probability
    probs[label] += probability
    return np.log(probs / probs.sum()).astype(np.float32)


class FakeSession:
    """Session ONNX factice et sans contexte : la classe dépend du seul jeton / context-free fake session."""

    def __init__(self, lexicon: Mapping[str, tuple[int, float]] = LEXICON, classes: int = 5,
                 extra_inputs: Sequence[str] = ()) -> None:
        self.table = np.tile(_logits(OUT, 0.99, classes), (len(VOCAB), 1))
        for word, (label, probability) in lexicon.items():
            self.table[VOCAB[word]] = _logits(label, probability, classes)
        self.inputs = ("input_ids", "attention_mask", *extra_inputs)
        self.calls: list[tuple[int, ...]] = []
        self.feeds: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def get_inputs(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(name=n) for n in self.inputs]

    def get_outputs(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(name="logits", shape=["batch", "sequence", self.table.shape[1]])]

    def run(self, names: Sequence[str], feeds: Mapping[str, Any]) -> list[Any]:
        ids = feeds["input_ids"]
        assert list(names) == ["logits"] and set(feeds) == set(self.inputs)
        assert ids.dtype == np.int64 and feeds["attention_mask"].shape == ids.shape
        with self._lock:
            self.calls.append(ids.shape)
            self.feeds.append(dict(feeds))
        return [self.table[ids]]

    @property
    def sequences(self) -> int:
        return sum(shape[0] for shape in self.calls)


def make_classifier(session: FakeSession, labels: Mapping[int, str] = IO_LABELS) -> Any:
    from gdprguardian.ner import TokenClassifier

    return TokenClassifier(session, make_tokenizer(), labels, pad_id=VOCAB["[PAD]"])


def make_ctx(text: str | Sequence[str], **settings: Any) -> DetectionContext:
    """Contexte de détection ; une liste de textes donne des segments / a list gives segments."""
    if isinstance(text, str):
        norm, _ = normalize(text)
        return DetectionContext(norm, fold(norm), None, ("FR",), "fr", Settings(**settings))
    starts: list[int] = []
    ends: list[int] = []
    cursor = 0
    for piece in text:
        starts.append(cursor)
        cursor += len(piece)
        ends.append(cursor)
        cursor += 2
    joined = "\n\n".join(text)
    return DetectionContext(joined, fold(joined), None, ("FR",), "fr", Settings(**settings), starts, ends)
