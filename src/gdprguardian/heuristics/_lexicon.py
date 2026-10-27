"""Listes de noms, mots courants et codes postaux, chargées une fois / gazetteers, loaded once per process.

Chaque jeton replié reçoit un code entier compact (rangs de fréquence, ambiguïté, sexe) : un seul dict, des
entiers partagés, aucune donnée par document. Each folded token maps to one compact int code.
"""

from __future__ import annotations

import gzip
import re
import threading
import unicodedata
from dataclasses import dataclass
from importlib import resources
from itertools import chain

from .._text import fold
from . import _vocab as V

# Code : bits 0-4 rang prénom, 5-9 rang nom, 10-11 ambiguïté, 12-13 sexe / code bit layout.
GIVEN_MASK = 0x1F
SURNAME_SHIFT = 5
RANK_MASK = GIVEN_MASK | GIVEN_MASK << SURNAME_SHIFT  # prénom ou nom connu / known given name or surname
AMB_SHIFT = 10
SEX_SHIFT = 12  # 1 masculin, 2 féminin, 3 mixte : réservé à la cohérence civilité-prénom / reserved
AMB_NONE, AMB_WORD, AMB_STRONG, AMB_ENTITY = 0, 1, 2, 3
CURATED_GIVEN_RANK = 6  # prénom de la liste manuelle, sans fréquence connue / curated name, no known frequency

# Sortes de jetons capitalisés / capitalised token kinds.
K_COMMON, K_NAME, K_UNKNOWN, K_INITIAL, K_PARTICLE = range(5)

_RANKS = {"": 0, "c": CURATED_GIVEN_RANK, **{str(i): i for i in range(32)}}
_AMB = {"": AMB_NONE, "w": AMB_WORD, "s": AMB_STRONG, "e": AMB_ENTITY}
_SEX = {"": 0, "M": 1, "F": 2, "X": 3}
SAINT = {"saint": "st", "sainte": "ste", "saints": "sts", "saintes": "stes"}
PLACE_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Chiffres romains, ordinaux compris (« XIV », « Ier », « VIe ») / Roman numerals, ordinals included.
ORDINAL_RE = re.compile(r"[IVXLCDM]{1,6}(?:er|re|e|ème|eme)?")
SAINT_PREFIXES = ("saint-", "sainte-", "st-", "ste-")


def given_rank(code: int) -> int:
    return code & GIVEN_MASK


def surname_rank(code: int) -> int:
    return (code >> SURNAME_SHIFT) & GIVEN_MASK


def ambiguity(code: int) -> int:
    return (code >> AMB_SHIFT) & 3


LINE_WINDOW = 512  # recherche de fin de ligne bornée : coût constant par appel / bounded line lookup


def line_bounds(text: str, pos: int, window: int = LINE_WINDOW) -> tuple[int, int, bool]:
    """(début, fin, ligne complète ?) autour de `pos`, dans une fenêtre bornée (pas de coût quadratique).

    (start, end, whole line?) around `pos`, within a bounded window: no quadratic cost on huge lines.
    """
    lo = max(0, pos - window)
    start = text.rfind("\n", lo, pos) + 1
    whole = start > 0 or lo == 0
    if not whole:
        start = lo
    hi = min(len(text), pos + window)
    end = text.find("\n", pos, hi)
    if end < 0:
        whole = whole and hi == len(text)
        end = hi
    return start, end, whole


def place_key(name: str) -> str:
    """Clé de commune : repliée, ponctuation -> espace, « saint » -> « st » / commune key."""
    return " ".join(SAINT.get(t, t) for t in PLACE_TOKEN_RE.findall(fold(name)))


def _upper_class() -> str:
    """Classe regex des majuscules latines, grecques et cyrilliques / uppercase letter class."""
    points = [cp for cp in chain(range(0x41, 0x250), range(0x370, 0x530), range(0x1E00, 0x1F00))
              if unicodedata.category(chr(cp)) in ("Lu", "Lt")]
    ranges: list[str] = []
    start = prev = points[0]
    for cp in [*points[1:], -1]:
        if cp != prev + 1:
            ranges.append(f"\\u{start:04x}" if start == prev else f"\\u{start:04x}-\\u{prev:04x}")
            start = cp
        prev = cp
    return "".join(ranges)


UPPER = _upper_class()
# Jeton capitalisé, composés à trait d'union ou apostrophe compris, quantificateurs bornés. La classe vient en
# tête (avant le contrôle de borne) pour que `re` balaie vite le texte : 2,4 fois plus rapide. Une apostrophe ou
# un tiret final (guillemet ’, coupure de ligne « Anne-⏎Sophie ») n'empêche pas le jeton.
# Capitalised token, compounds included, bounded quantifiers; the class comes first so `re` scans fast. A
# trailing quote or hyphen (closing ’, line-break hyphen) does not prevent the token.
TOKEN_RE = re.compile(rf"[{UPPER}](?<!\w.)[^\W\d_]{{0,40}}(?:['-][^\W\d_]{{1,40}}){{0,4}}(?!\w|['-][^\W\d_])")


@dataclass(slots=True, frozen=True)
class Lexicon:
    names: dict[str, int]
    words: frozenset[str]
    postal: dict[str, frozenset[str]]
    departments: dict[str, frozenset[str]]
    communes: frozenset[str]   # clés de communes, toutes / every commune key (« levallois perret »)

    def code(self, key: str) -> int | None:
        """Code d'un jeton replié, variantes d'apostrophe comprises / code of a folded token."""
        code = self.names.get(key)
        if code is None and "'" in key:
            code = self.names.get(key.replace("'", " ")) or self.names.get(key.replace("'", ""))
        return code

    def classify(self, key: str, original: str) -> tuple[int, int]:
        """(sorte, code) d'un jeton capitalisé / (kind, code) of a capitalised token."""
        if key in V.STOP:
            return K_COMMON, 0
        if original.lower() in V.ACCENTED_WORDS:
            return K_COMMON, 0  # « Marié le 12/06/2015 » : pas le prénom « Marie » (1.0.2) / not the given name
        if key in V.PARTICLES:
            return K_PARTICLE, self.names.get(key, 0)
        if len(key) > 1 and key in V.FUNCTION:
            return K_COMMON, 0  # « Puis », « Pour », « Selon » en tête de phrase / sentence-initial function word
        if key.startswith(SAINT_PREFIXES):
            return K_UNKNOWN, 0  # « Saint-Martin » : lieu le plus souvent ; nom seulement avec un indice
        if original[0] in "IVXLCDM" and ORDINAL_RE.fullmatch(original):
            return K_COMMON, 0  # « Louis XIV », « VIe siècle », « François Ier »
        if "'" in key and "-" not in key.partition("'")[0]:
            return self._elision(key, original)
        code = self.names.get(key)
        if code is not None:
            return K_NAME, code
        if key in self.words:
            return K_COMMON, 0
        if len(key) == 1:
            return K_INITIAL, 0
        if "-" in key:
            return self._compound(key, original)
        return K_UNKNOWN, 0

    def _elision(self, key: str, original: str) -> tuple[int, int]:
        head, _, rest = key.partition("'")
        tail = original[len(head) + 1:]
        if rest == "s":
            return self.classify(head, original[:len(head)])  # possessif / possessive « Dupont's »
        if head.endswith("c") and rest.startswith("h"):
            # « Guivarc'h », « Kerc'hoz » : le c'h breton appartient au nom, jamais une élision (1.0.2, fort et
            # essentiel). The Breton c'h belongs to the name: known as a whole, else an unknown name.
            code = self.code(key)
            return (K_NAME, code) if code is not None else (K_UNKNOWN, 0)
        if not tail or not tail[0].isupper() or head == "l":
            return K_COMMON, 0  # « C'est », « L'Europe », « L'Union » : élision d'un mot-outil / elision
        # « N'Diaye », « O'Brien », « D'Amico », « M'Bappé » : la base les écrit avec ou sans espace.
        code = self.names.get(key) or self.names.get(f"{head} {rest}") or self.names.get(head + rest)
        if code is not None:
            return K_NAME, code
        kind, code = self.classify(rest, tail)
        return (K_NAME, code) if kind == K_NAME else (K_UNKNOWN, 0)

    def _compound(self, key: str, original: str) -> tuple[int, int]:
        parts = key.split("-")
        if any(p and not p[0].isupper() for p in original.split("-")[1:]):
            return K_COMMON, 0  # « Aix-en-Provence », « Arc-en-Ciel »
        codes = [self.code(p) for p in parts]
        known = [c for c in codes if c is not None]
        if len(known) != len(parts):
            return K_UNKNOWN, 0
        given = min(given_rank(c) for c in known)
        surname = min(surname_rank(c) for c in known) if all(surname_rank(c) for c in known) else 0
        if not given and not surname:
            surname = max(max(given_rank(c), surname_rank(c)) for c in known)
        ambiguities = [ambiguity(c) for c in known]
        if AMB_ENTITY in ambiguities and not all(given_rank(c) for c in known):
            amb = AMB_ENTITY  # « Paris-Brest », « France-Allemagne » ; mais « Heinz-Peter » est un prénom
        elif AMB_NONE in ambiguities or any(given_rank(c) for c in known):
            amb = AMB_NONE  # un composé de prénoms ou de noms est sans ambiguïté / unambiguous compound
        else:
            amb = AMB_WORD
        return K_NAME, given | surname << SURNAME_SHIFT | amb << AMB_SHIFT


_LOCK = threading.Lock()
_LEXICON: Lexicon | None = None


def _read(name: str) -> list[str]:
    raw = (resources.files(__package__) / "data" / name).read_bytes()
    return [line for line in gzip.decompress(raw).decode("utf-8").splitlines() if line and line[0] != "#"]


def _load() -> Lexicon:
    names: dict[str, int] = {}
    shared: dict[int, int] = {}
    ranks, amb, sex = _RANKS, _AMB, _SEX
    for line in _read("names.tsv.gz"):
        token, g, s, n, a = line.split("\t")
        code = ranks[g] | ranks[n] << SURNAME_SHIFT | amb[a] << AMB_SHIFT | sex[s] << SEX_SHIFT
        names[token] = shared.setdefault(code, code)
    # « Rendu le 3 mars » : forme verbale ; « AVENANT N° 2 » : type de document ; pas des noms sûrs.
    # A verb form or a document type, not a safe name.
    for token in V.VERB_FORMS | V.DOCUMENT_WORDS:
        code = names.get(token)
        if code is not None and ambiguity(code) == AMB_NONE:
            names[token] = code | AMB_WORD << AMB_SHIFT
    postal: dict[str, frozenset[str]] = {}
    by_department: dict[str, set[str]] = {}
    for line in _read("postal.tsv.gz"):
        code, keys = line.split("\t")
        entries = frozenset(keys.split("|"))
        postal[code] = entries
        by_department.setdefault(department(code), set()).update(entries)
    communes = frozenset(k for keys in postal.values() for k in keys)
    words = frozenset(_read("words.txt.gz")) | (V.EXTRA_WORDS - names.keys())
    return Lexicon(names, words, postal, {d: frozenset(v) for d, v in by_department.items()}, communes)


def department(postcode: str) -> str:
    """Département d'un code postal (97x et 98x sur trois chiffres) / department of a postcode."""
    return postcode[:3] if postcode[:2] in ("97", "98") else postcode[:2]


def lexicon() -> Lexicon:
    """Chargement paresseux, une seule fois, sûr entre threads / lazy, once, thread-safe."""
    global _LEXICON
    if _LEXICON is None:
        with _LOCK:
            if _LEXICON is None:
                _LEXICON = _load()
    return _LEXICON
