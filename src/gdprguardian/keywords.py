"""Index de mots-clés de contexte, un seul passage Aho-Corasick / context keywords, single pass.

Les mots-clés sont repliés (minuscules, sans accents) et cherchés sur le texte replié.
Keywords are folded (lowercase, no accents) and searched in the folded text.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Iterable, Mapping, Sequence

from ._text import fold

try:
    import ahocorasick_rs

    _HAS_AC = True
except ImportError:  # pragma: no cover - repli pur Python / pure-Python fallback
    _HAS_AC = False

# Longueur maximale d'un mot-clé, bornant le retour arrière / max keyword length, bounds backtracking.
MAX_KEYWORD_LEN = 64


class KeywordHits:
    """Occurrences triées par groupe ; groupes et `counts` dans l'ordre des noms (comme le noyau Rust).

    Per-group sorted occurrences; groups and `counts` in name order (as in the Rust core).
    """

    __slots__ = ("_by_group", "counts")

    def __init__(self) -> None:
        self._by_group: dict[str, tuple[list[int], list[int]]] = {}
        self.counts: dict[str, int] = {}

    def add(self, group: str, start: int, end: int) -> None:
        entry = self._by_group.get(group)
        if entry is None:
            entry = ([], [])
            self._by_group[group] = entry
        entry[0].append(start)
        entry[1].append(end)
        self.counts[group] = self.counts.get(group, 0) + 1

    def finalize(self) -> None:
        for group, (starts, ends) in self._by_group.items():
            if any(starts[i] > starts[i + 1] for i in range(len(starts) - 1)):
                pairs = sorted(zip(starts, ends, strict=True))
                self._by_group[group] = ([p[0] for p in pairs], [p[1] for p in pairs])
        # Un ordre défini, indépendant de l'ordre des occurrences / one defined order, not the hits' order.
        self.counts = dict(sorted(self.counts.items()))

    def near(self, group: str, start: int, end: int, before: int, after: int,
             lo: int = 0, hi: int = 1 << 62) -> bool:
        """Un mot-clé du groupe touche-t-il la fenêtre ? / does a keyword hit the window?

        `lo`/`hi` bornent la recherche à un segment (cellule) / bound the search to a segment.
        """
        entry = self._by_group.get(group)
        if entry is None:
            return False
        starts, ends = entry
        left = max(start - before, lo)
        right = min(end + after, hi)
        i = bisect_right(starts, right) - 1
        while i >= 0:
            hit_start = starts[i]
            if hit_start < left - MAX_KEYWORD_LEN:
                return False
            if ends[i] >= left and hit_start >= lo:
                return True
            i -= 1
        return False

    def last_end(self, group: str, pos: int, lo: int = 0) -> int:
        """Fin du dernier mot-clé du groupe fini avant `pos` (début ≥ `lo`), sinon -1.

        End of the group's last keyword finished before `pos` (start ≥ `lo`), else -1.
        """
        entry = self._by_group.get(group)
        if entry is None:
            return -1
        starts, ends = entry
        best = -1
        i = bisect_right(starts, pos) - 1
        # Un mot plus ancien ne peut finir après `best` que s'il commence à moins d'une longueur maximale.
        # An earlier keyword can only end after `best` if it starts within one maximum length.
        while i >= 0 and starts[i] >= lo and starts[i] + MAX_KEYWORD_LEN > best:
            if best < ends[i] <= pos:
                best = ends[i]
            i -= 1
        return best

    def groups(self) -> list[str]:
        return sorted(self._by_group)

    def occurrences(self, group: str) -> list[tuple[int, int]]:
        entry = self._by_group.get(group)
        return list(zip(*entry, strict=True)) if entry else []


def longest_matches(patterns: Sequence[str], text: str) -> list[tuple[int, int, int]]:
    """Occurrences sans chevauchement, la plus longue d'abord : (motif, début, fin), en caractères.

    Non-overlapping occurrences, longest first: (pattern, start, end), in characters. Construit à chaque
    appel, sans compiler de regex (10x moins cher pour les formes propagées d'un document).
    """
    if _HAS_AC:
        automaton = ahocorasick_rs.AhoCorasick(list(patterns), matchkind=ahocorasick_rs.MatchKind.LeftmostLongest)
        return automaton.find_matches_as_indexes(text)
    regex = re.compile("|".join(re.escape(p) for p in sorted(patterns, key=len, reverse=True)))  # pragma: no cover
    index = {p: i for i, p in enumerate(patterns)}  # pragma: no cover
    return [(index[m.group()], m.start(), m.end()) for m in regex.finditer(text)]  # pragma: no cover


class KeywordIndex:
    """Automate compilé une fois par ensemble de packs / automaton compiled once per pack set."""

    def __init__(self, groups: Mapping[str, Iterable[str]]) -> None:
        pattern_groups: dict[str, list[str]] = {}
        for group, words in groups.items():
            for word in words:
                folded = fold(word.strip())
                if not folded:
                    continue
                # Un groupe une fois par mot replié : chaque occurrence compte une fois, comme en Rust.
                # A group once per folded word: each occurrence counts once, as in Rust.
                bucket = pattern_groups.setdefault(folded, [])
                if group not in bucket:
                    bucket.append(group)
        self._patterns = list(pattern_groups)
        self._groups = [tuple(pattern_groups[p]) for p in self._patterns]
        # Bornes à vérifier seulement si le mot commence/finit par une lettre ou un chiffre.
        # Boundaries checked only when the keyword starts/ends with a letter or digit.
        self._check_left = [p[0].isalnum() for p in self._patterns]
        self._check_right = [p[-1].isalnum() for p in self._patterns]
        self._ac = None
        self._regex = None
        if not self._patterns:
            return
        if _HAS_AC:
            self._ac = ahocorasick_rs.AhoCorasick(self._patterns, matchkind=ahocorasick_rs.MatchKind.Standard)
        else:  # pragma: no cover
            alternation = "|".join(re.escape(p) for p in sorted(self._patterns, key=len, reverse=True))
            self._regex = re.compile(alternation)
            self._index = {p: i for i, p in enumerate(self._patterns)}

    def scan(self, folded: str) -> KeywordHits:
        hits = KeywordHits()
        if self._ac is not None:
            matches = self._ac.find_matches_as_indexes(folded, overlapping=True)
        elif self._regex is not None:  # pragma: no cover
            matches = [(self._index[m.group()], m.start(), m.end()) for m in self._regex.finditer(folded)]
        else:
            return hits
        length = len(folded)
        check_left = self._check_left
        check_right = self._check_right
        groups = self._groups
        for idx, start, end in matches:
            if check_left[idx] and start > 0 and folded[start - 1].isalnum():
                continue
            if check_right[idx] and end < length and folded[end].isalnum():
                continue
            for group in groups[idx]:
                hits.add(group, start, end)
        hits.finalize()
        return hits

    def groups_in(self, text: str) -> set[str]:
        """Groupes présents dans un court texte (en-tête de colonne) / groups found in a short text."""
        return set(self.scan(fold(text)).groups())
