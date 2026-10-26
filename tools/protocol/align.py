"""Ce que le service a masqué, retrouvé depuis sa seule sortie / what the service masked, from its output alone.

Le service ne rend ni positions ni zones : seulement le texte anonymisé. Or ce texte est l'entrée où chaque zone
masquée est remplacée par une balise `[LIBELLE_N]`, puis nettoyée des caractères invisibles (`sanitize_output`).
On retire donc ces invisibles de l'entrée, on découpe la sortie en segments littéraux et balises, et on place
chaque segment littéral dans l'entrée : ce qui n'est couvert par aucun segment littéral a été masqué.

The service returns neither offsets nor spans, only the anonymised text, which is the input with each masked span
replaced by a `[LABEL_N]` placeholder, then stripped of invisible characters. Invisible characters are removed from
the input, the output is cut into literal segments and placeholders, and each literal segment is placed in the
input: whatever no literal segment covers was masked.

Ambiguïté : un segment littéral entre deux balises (« Jean Dupont 06… » -> « [PERSONNE_1] [TEL_1] ») peut parfois
se placer à plusieurs endroits. On calcule le placement le plus à gauche et le plus à droite (gloutons, tous deux
optimaux) : toute solution est entre les deux. La zone masquée représentative est le placement à gauche ; l'ensemble
des caractères PEUT-ÊTRE visibles réunit toutes les occurrences du segment entre ces bornes (borne prudente :
une mention n'est comptée masquée que si aucun de ses caractères ne peut être visible).
Ambiguity: a literal segment between two placeholders may fit at several places. The leftmost and rightmost
placements bound every solution; the representative masked zones use the leftmost one, and the set of characters
that MAY be visible joins every occurrence between the bounds (a mention counts as masked only if none of its
characters can be visible).

Bibliothèque standard seulement (lancé dans l'image du service ou par le python3 de l'hôte).
Standard library only (runs in the service image or with the host's python3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Copies exactes de gdprguardian.scope.PLACEHOLDER_RE et de la classe de gdprguardian.sanitize._INVISIBLE_RE ;
# tests/protocol/test_align.py vérifie qu'elles ne dérivent pas. Exact copies, drift-checked by the tests.
PLACEHOLDER_RE = re.compile(r"\[([A-Z][A-Z0-9_]*[A-Z0-9])_([1-9][0-9]{0,6})\]")
DROPPED_CLASS = ("[\xad᠎​‌‎‏‪-‮⁠-⁤⁦-⁩﻿"
                 "\U000e0000-\U000e007f]")
DROPPED_RE = re.compile(DROPPED_CLASS)
# Autres réécritures de sanitize_output (images distantes, balise <img>, commentaires HTML) : l'alignement échoue
# alors proprement (document compté en échec, jamais réussi). Other sanitize rewrites make alignment fail cleanly.


class AlignmentError(ValueError):
    """Sortie impossible à aligner sur l'entrée (message sans contenu) / output cannot be aligned (no content)."""


@dataclass(frozen=True, slots=True)
class Alignment:
    """Résultat d'alignement, positions dans le texte ORIGINAL / alignment result, ORIGINAL offsets."""

    masked: tuple[tuple[int, int, str], ...]   # (début, fin, libellé affiché) : placement à gauche / leftmost
    maybe_visible: bytearray                   # 1 = caractère peut-être lisible tel quel dans la sortie
    placeholders: int                          # balises émises / placeholders emitted
    ambiguous_segments: int                    # segments littéraux à plusieurs placements / multi-placement segments


def _strip_dropped(text: str) -> tuple[str, list[int] | None]:
    """Entrée sans les invisibles que la sortie perd ; table de positions si besoin / input without invisibles."""
    if DROPPED_RE.search(text) is None:
        return text, None
    index = [i for i, ch in enumerate(text) if DROPPED_RE.match(ch) is None]
    return "".join(text[i] for i in index), index


def split_output(text: str, output: str) -> tuple[list[str], list[str]]:
    """Segments littéraux (k + 1) et libellés des k balises / literal segments and the k placeholder labels.

    Une balise déjà présente dans l'entrée reste du texte : le moteur ne réutilise jamais une balise de l'entrée.
    A placeholder already present in the input stays literal text: the engine never reuses one from the input.
    """
    reserved = {m.group(0) for m in PLACEHOLDER_RE.finditer(text)} if "[" in text else set()
    literals: list[str] = []
    labels: list[str] = []
    last = 0
    for m in PLACEHOLDER_RE.finditer(output):
        if m.group(0) in reserved:
            continue
        literals.append(output[last:m.start()])
        labels.append(m.group(1))
        last = m.end()
    literals.append(output[last:])
    return literals, labels


def _placements(t: str, literals: list[str]) -> tuple[list[int], list[int]]:
    """Débuts des segments littéraux : placement glouton à gauche et à droite / leftmost and rightmost starts.

    Chaque zone masquée (entre deux segments) a au moins un caractère. Le placement le plus tôt de chaque segment
    ne gêne jamais les suivants (et réciproquement à droite) : si l'un échoue, aucune solution n'existe.
    Each masked zone holds at least one character. Placing each segment as early as possible never hurts the next
    ones (and symmetrically from the right): if the greedy pass fails, no solution exists.
    """
    k = len(literals) - 1
    n = len(t)
    head, tail = literals[0], literals[-1]
    tail_start = n - len(tail)
    if not t.startswith(head) or not t.endswith(tail) or tail_start < len(head) + k:
        raise AlignmentError("bornes / bounds")
    left = [0] * (k + 1)
    pos = len(head)
    for i in range(1, k):
        start = t.find(literals[i], pos + 1)
        if start < 0:
            raise AlignmentError("segment introuvable / segment not found")
        left[i] = start
        pos = start + len(literals[i])
    if pos >= tail_start:
        raise AlignmentError("dernière zone vide / empty last zone")
    left[k] = tail_start
    right = [0] * (k + 1)
    right[k] = tail_start
    end = tail_start
    for i in range(k - 1, 0, -1):
        start = t.rfind(literals[i], len(head) + 1, end - 1)
        if start < 0:
            raise AlignmentError("segment introuvable / segment not found")
        right[i] = start
        end = start
    return left, right


def align(text: str, output: str) -> Alignment:
    """Zones masquées et caractères peut-être visibles de `text` d'après `output` / masked zones from the output."""
    t, index = _strip_dropped(text)
    literals, labels = split_output(text, output)
    k = len(labels)
    n = len(text)
    visible = bytearray(n)

    def mark(start: int, length: int) -> None:
        if not length:
            return
        if index is None:
            visible[start:start + length] = b"\x01" * length
        else:
            for p in range(start, start + length):
                visible[index[p]] = 1

    def original(position: int) -> int:
        return position if index is None else (index[position] if position < len(index) else n)

    if k == 0:
        if output != t:
            raise AlignmentError("sortie différente sans balise / output differs without placeholder")
        mark(0, len(t))
        return Alignment((), visible, 0, 0)
    left, right = _placements(t, literals)
    ambiguous = 0
    mark(0, len(literals[0]))
    mark(left[k], len(literals[k]))
    for i in range(1, k):
        literal = literals[i]
        if left[i] == right[i] or not literal:
            ambiguous += left[i] != right[i]
            mark(left[i], len(literal))
            continue
        ambiguous += 1
        start = left[i]
        while 0 <= start <= right[i]:
            mark(start, len(literal))
            start = t.find(literal, start + 1)
    masked = []
    for i in range(1, k + 1):
        a = left[i - 1] + len(literals[i - 1])
        b = left[i]
        start = original(a)
        # Zones accolées : les invisibles retirés entre elles leur appartiennent / adjacent zones own the gap.
        end = original(b) if not literals[i] and i < k else original(b - 1) + 1
        masked.append((start, end, labels[i - 1]))
    return Alignment(tuple(masked), visible, k, ambiguous)


def masked_bytes(size: int, intervals: tuple[tuple[int, int, str], ...] | list[tuple[int, int]]) -> bytearray:
    """Masque 0/1 des zones / 0-1 mask of the zones."""
    mask = bytearray(size)
    for item in intervals:
        start, end = item[0], item[1]
        mask[start:end] = b"\x01" * (end - start)
    return mask
