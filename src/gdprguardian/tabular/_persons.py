"""Personnes des colonnes de noms : cellules multiples et propagation / persons from name columns.

Un nom masqué dans une colonne « Nom » l'est aussi dans le texte libre des autres colonnes et feuilles
(« RDV avec Mme Dupont »). A name masked in a "Name" column is masked in free text elsewhere too.
"""

from __future__ import annotations

import re
from bisect import bisect_left, bisect_right
from collections.abc import Callable, Iterable

import ahocorasick_rs

from .._text import fold
from ..scope import HONORIFICS

_NAME_TOKEN_RE = re.compile(r"[^\W\d_]{1,40}(?:[\-'’][^\W\d_]{1,40}){0,4}")
_PARTICLES = frozenset({"de", "du", "des", "del", "della", "di", "da", "van", "von", "der", "den", "le", "la",
                        "les", "ben", "bin", "el", "al", "dit", "dite", "epouse", "veuve", "ne", "nee"})
_PEOPLE_SEPARATOR_RE = re.compile(r"(\s{0,3}(?:[;/&+\n]|\bet\b|\band\b)\s{0,3})")
_PERSON_SHAPE_RE = re.compile(r"[^\W\d_]{1,40}\.?(?:(?:[ '’\-]{1,2}|, ?)[^\W\d_]{1,40}\.?){0,6}")
# Toute balise, avec ou sans numéro (opérateur « redact ») / any placeholder, numbered or not.
ANY_PLACEHOLDER_RE = re.compile(r"\[[A-Z][A-Z0-9_]{0,40}[A-Z0-9]\]")
# Texte de moins de 8 caractères par forme connue : seules les formes présentes vont dans l'automate.
# Text under 8 characters per known form: only the forms present go into the automaton.
_SIFT_RATIO = 8


def split_people(text: str) -> list[str] | None:
    """« Jean Dupont ; Marie Durand » -> morceaux (séparateurs conservés), None si une seule personne.

    Returns pieces with separators kept (odd indexes), or None for a single person.
    """
    pieces = _PEOPLE_SEPARATOR_RE.split(text.strip())
    names = pieces[0::2]
    if len(names) < 2 or not all(_PERSON_SHAPE_RE.fullmatch(name) for name in names):
        return None
    return pieces


class KnownPersons:
    """Formes de noms à propager, construites par requête (aucun état partagé) / per-request name forms.

    Chaque forme garde sa valeur canonique : « Delacroix Hélène » renvoie à « Hélène Delacroix », car la portée
    lit « Prénom Nom ». Each form keeps its canonical value, since the scope reads "Given Surname".
    """

    __slots__ = ("_forms", "_seen")

    def __init__(self) -> None:
        self._forms: dict[str, str] = {}
        self._seen: set[str] = set()

    def __bool__(self) -> bool:
        return bool(self._forms)

    def add(self, value: str, tokens: bool = True, canonical: str | None = None) -> None:
        """Ajoute un nom et, sauf `tokens=False`, ses mots sûrs / adds a name and, unless told not to, its words."""
        if value in self._seen:
            return
        self._seen.add(value)
        value = " ".join(value.split())
        canonical = canonical or value
        if len(value) >= 3 and any(map(str.isalpha, value)):
            self._forms.setdefault(value, canonical)
            self._forms.setdefault(value.upper(), canonical)
        if not tokens:
            return
        # Les balises déjà présentes ne fournissent aucun mot / existing placeholders yield no word.
        words = ANY_PLACEHOLDER_RE.sub(" ", value) if "[" in value else value
        for token in _NAME_TOKEN_RE.findall(words):
            if len(token) < 3 or not token[0].isupper():
                continue
            folded = fold(token)
            if folded in _PARTICLES or folded in HONORIFICS:
                continue
            # « DUPONT » dans une colonne, « Dupont » dans le texte, et inversement / both casings.
            for form in (token, _capitalize(token) if token.isupper() else token.upper()):
                self._forms.setdefault(form, token)

    def apply(self, texts: list[str], indexes: Iterable[int], replace: Callable[[str, str], str]) -> int:
        """Remplace les formes connues dans `texts[i]` (en place), balises existantes préservées.

        Replaces known forms in `texts[i]` in place, keeping existing placeholders; `replace(form, canonical)`
        gives the replacement. Returns the replacement count.
        """
        if not self._forms:
            return 0
        selected = [i for i in indexes if texts[i]]
        if not selected:
            return 0
        haystack = "\n".join(texts[i] for i in selected)
        forms = sorted(self._present_forms(haystack))
        if not forms:
            return 0
        automaton = ahocorasick_rs.AhoCorasick(forms, matchkind=ahocorasick_rs.MatchKind.LeftmostLongest)
        starts: list[int] = []
        cursor = 0
        for i in selected:
            starts.append(cursor)
            cursor += len(texts[i]) + 1
        by_text: dict[int, list[tuple[int, int, int]]] = {}
        for pattern, start, end in automaton.find_matches_as_indexes(haystack):
            position = bisect_right(starts, start) - 1
            offset = starts[position]
            by_text.setdefault(position, []).append((pattern, start - offset, end - offset))
        count = 0
        for position, matches in by_text.items():
            index = selected[position]
            text = texts[index]
            # Balises existantes, triées et disjointes : seule la dernière qui commence avant la fin d'une
            # correspondance peut la chevaucher (recherche dichotomique, jamais quadratique).
            # Existing placeholders, sorted and disjoint: only the last one starting before a match's end can
            # overlap it (binary search, never quadratic).
            protected_starts: list[int] = []
            protected_ends: list[int] = []
            if "[" in text:
                for found in ANY_PLACEHOLDER_RE.finditer(text):
                    protected_starts.append(found.start())
                    protected_ends.append(found.end())
            pieces: list[str] = []
            last = 0
            for pattern, start, end in matches:
                if (start > 0 and text[start - 1].isalnum()) or (end < len(text) and text[end].isalnum()):
                    continue
                before = bisect_left(protected_starts, end) - 1
                if before >= 0 and protected_ends[before] > start:
                    continue
                pieces.append(text[last:start])
                pieces.append(replace(text[start:end], self._forms[forms[pattern]]))
                last = end
                count += 1
            if pieces:
                pieces.append(text[last:])
                texts[index] = "".join(pieces)
        return count

    def _present_forms(self, haystack: str) -> Iterable[str]:
        """Formes pouvant figurer dans `haystack` : leurs trois premiers caractères y figurent (toute forme en a
        au moins trois). Une forme absente ne change aucune correspondance « la plus à gauche, la plus longue » ;
        le tri n'a lieu que si le texte est court devant le nombre de formes (construire l'automate coûte plus).
        Forms that may occur in `haystack`: their first three characters occur in it (every form has at least
        three). An absent form changes no leftmost-longest match; sifting only pays off when the text is short
        compared with the number of forms (building the automaton costs more)."""
        forms = self._forms
        size = len(haystack)
        if size >= _SIFT_RATIO * len(forms):
            return forms
        grams = set(map(haystack.__getitem__, map(slice, range(size - 2), range(3, size + 1))))
        return [form for form in forms if form[:3] in grams]


def _capitalize(token: str) -> str:
    return "-".join(part[:1].upper() + part[1:].lower() for part in token.split("-"))
