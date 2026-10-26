"""Organisations repérées par leur forme juridique ou un mot d'introduction / organisations by legal form or cue.

Règle « physicomorale » (Cour de cassation) : une raison sociale qui contient le nom d'une personne est masquée ;
si elle n'est que ce nom (« Dupont SARL »), elle devient une zone PERSONNE (même balise que « M. Dupont »).
Les autres organisations sont signalées mais conservées, sauf réglage `company_ids="mask"` ou profil strict.
"Physicomorale" rule: a company name containing a person's name is masked; one that is only that name becomes
a PERSON span. Other organisations are reported but kept, unless `company_ids="mask"` or the strict profile.
La recherche des candidats a un jumeau Rust aux résultats identiques ; la décision (`_spans`) reste ici.
The candidate search has an identical Rust twin; the decision (`_spans`) stays here.
"""

from __future__ import annotations

import re
from functools import cache, cached_property
from typing import Any

import ahocorasick_rs

from .. import _native
from .._text import fold
from ..types import PRIORITY_HEURISTIC, PRIORITY_PROPAGATED, Span
from . import _vocab as V
from ._compose import composed_view
from ._lexicon import AMB_ENTITY, AMB_NONE, AMB_WORD, UPPER, Lexicon, ambiguity, given_rank, lexicon, surname_rank

# Mot de raison sociale : un point seulement entre lettres (« S.A »), jamais d'apostrophe finale (« L' »).
# Company-name word: a dot only between letters, never a trailing apostrophe.
_WORD = rf"[{UPPER}0-9](?:[\w&+-]|['’.](?=\w)){{0,40}}"
_FAMILY = r"(?:Fils|Filles|Fr[èe]res|Associ[ée]e?s|Cie|Compagnie|Co|Partners|Partenaires|Sons|Söhne)(?![\w])"
# « et », « & » ne joignent que « Fils », « Associés »… : sinon c'est une énumération / otherwise a list.
_JOINER = (rf"(?:(?:&|et|and|und|y|e)[ \t]{{1,2}}(?={_FAMILY})"
           r"|(?:de|du|des|la|le|les|en|sur|aux?|of|the)[ \t]{1,2}|[dl]')")
_NAME = rf"{_WORD}(?:[ \t]{{1,2}}{_JOINER}?{_WORD}){{0,5}}"
_WORD_RE = re.compile(_WORD + r"|[dlDL]['’]" + _WORD)
_JOINERS = frozenset({"de", "du", "des", "la", "le", "les", "en", "sur", "aux", "au", "of", "the"})
_OPENING = frozenset("(«“\"'[")
_NAME_RIGHT_RE = re.compile(rf"[ \t]{{1,2}}[«\"“]?[ \t]?((?:(?:du|des|de la|de l'|de|d'|l')[ \t]{{0,2}})?{_NAME})")
_WORDS_RE = re.compile(r"[^\W\d_][\w'’.-]*")
_PIECE_RE = re.compile(r"[^\s]+")
_JOIN_WORDS = frozenset({"&", "et", "and", "und", "y", "e", "of", "the"})
_NAME_ARTICLES = frozenset({"le", "la", "les"})
# Une organisation non personnelle ne doit jamais l'emporter sur un nom de personne qu'elle contient : priorité
# minimale. A non-personal organisation must never win over a person name it contains: lowest priority.
_KEPT_PRIORITY = PRIORITY_PROPAGATED
_SURNAME_MIN = 8       # nom porté par au moins 256 personnes / surname of at least 256 bearers
_GIVEN_MIN = 9         # prénom donné au moins 512 fois / given name of at least 512 births
_FREQUENT_NAME = 14    # nom ou prénom très fréquent, même homonyme d'un mot / very frequent, even if a word

# Automates compilés une fois à l'import, partagés en lecture seule / automata compiled once, shared read-only.
# Formes et suffixes : casse d'origine (« SA » mais pas « sa ») ; mots d'introduction : texte replié.
_FORMS = list(dict.fromkeys(V.LEGAL_FORMS_SUFFIX))
_CASE_PATTERNS = _FORMS + list(V.ORG_SUFFIXES)
_CASE_AC = ahocorasick_rs.AhoCorasick(_CASE_PATTERNS, matchkind=ahocorasick_rs.MatchKind.LeftmostLongest)
_KEYWORD_AC = ahocorasick_rs.AhoCorasick(sorted(V.ORG_KEYWORDS), matchkind=ahocorasick_rs.MatchKind.LeftmostLongest)


class OrganizationDetector:
    """Raisons sociales : « Acme SAS », « SARL Dupont et Fils », « la société Acme », « Martin & Associés »."""

    id = "ORGANIZATIONS"

    def __init__(self, pack: Any = None) -> None:
        self.pack = pack
        self._lex: Lexicon = lexicon()
        context = getattr(pack, "context", {}) or {}
        self._ei_groups = tuple(g for g in context if g.endswith(":ei"))

    @cached_property
    def _native(self) -> Any:
        """Jumeau Rust, construit au premier usage natif / Rust twin, built on first native use."""
        return _native_twin()

    @composed_view
    def detect(self, ctx: Any) -> list[Span]:
        if ctx.settings.native and self._native is not None:
            return self._spans(ctx, self._native.candidates(ctx.text, ctx.folded))
        return self._spans(ctx, self._candidates(ctx))

    def _candidates(self, ctx: Any) -> list[tuple[int, int, bool]]:
        """(début, fin, entrepreneur individuel) de chaque candidat / (start, end, sole trader) of each candidate."""
        text: str = ctx.text
        found: list[tuple[int, int, bool]] = []
        for index, start, end in _CASE_AC.find_matches_as_indexes(text, overlapping=False):
            if not _bounded(text, start, end):
                continue
            if index < len(_FORMS):
                self._legal_form(text, start, end, _FORMS[index], found)
            else:
                left = self._left_name(text, start)
                if left is not None:
                    found.append((left[0], end, False))
        for _, start, end in _KEYWORD_AC.find_matches_as_indexes(ctx.folded, overlapping=False):
            if not _bounded(ctx.folded, start, end):
                continue
            right = self._right_name(text, end)
            if right is not None:
                # Mot capitalisé : il fait partie du nom (« Cabinet Dupont & Associés ») / part of the name.
                found.append((start if text[start].isupper() else right[0], right[1], False))
        return found

    def _legal_form(self, text: str, start: int, end: int, form: str, found: list[tuple[int, int, bool]]) -> None:
        sole = form in V.SOLE_TRADER_FORMS
        left = self._left_name(text, start)
        if left is not None:
            found.append((left[0], left[1], sole))
        elif form in V.LEGAL_FORMS_PREFIX:
            right = self._right_name(text, end)
            if right is not None:
                found.append((right[0], right[1], sole))

    @staticmethod
    def _left_name(text: str, pos: int) -> tuple[int, int] | None:
        """Nom qui précède une forme juridique ; s'arrête après une autre forme ou une civilité.

        Name before a legal form, read backwards word by word (linear cost); starts after another legal form
        or an honorific, without leading function words.
        """
        end = pos
        while end > 0 and text[end - 1] in " \t,":
            end -= 1
        if end == pos or end == 0 or not text[end - 1].isalnum():
            return None
        pieces: list[tuple[int, int, str]] = []
        cursor = end
        while len(pieces) < 8:
            start = cursor
            while start > 0 and not text[start - 1].isspace() and cursor - start <= 42:
                start -= 1
            if start > 0 and not text[start - 1].isspace():
                break  # mot trop long / word too long
            opening = start < cursor and text[start] in _OPENING
            start += opening  # « (Acme SAS) » : la parenthèse borne le nom / the bracket bounds the name
            word = text[start:cursor]
            key = fold(word).replace(".", "")
            following = pieces[0][2] if pieces else ""
            if _WORD_RE.fullmatch(word) is None and not (
                    pieces and (key in _JOINERS or (key in _JOIN_WORDS and following in V.ORG_FAMILY))):
                break
            pieces.insert(0, (start, cursor, key))
            if opening:
                break
            gap = start
            while gap > 0 and text[gap - 1] in " \t" and start - gap < 2:
                gap -= 1
            if gap == start or gap == 0 or text[gap - 1] in "\n\r":
                break
            cursor = gap
        while pieces and text[pieces[0][0]].islower() and (pieces[0][2] in _JOINERS or pieces[0][2] in _JOIN_WORDS):
            pieces.pop(0)  # un nom ne commence pas par « de » ou « et » / a name never starts with a joiner
        cut = max((i + 1 for i, (_, _, key) in enumerate(pieces) if key in V.LEGAL_FORM_KEYS or key in V.STOP),
                  default=0)
        pieces = pieces[cut:]
        # Mots-outils en tête retirés (« Hier Acme »), sauf l'article d'une raison sociale (« Les Jardins »).
        # Leading function words dropped, except the article that opens a company name.
        while pieces and pieces[0][2] not in _NAME_ARTICLES and (
                pieces[0][2] in V.FUNCTION or pieces[0][2] in V.PARTICLES):
            pieces.pop(0)
        if not any(p[2] not in V.FUNCTION and p[2] not in V.PARTICLES for p in pieces):
            return None  # « La SCI … » : un article seul n'est pas un nom / an article alone is not a name
        return pieces[0][0], pieces[-1][1]

    @staticmethod
    def _right_name(text: str, pos: int) -> tuple[int, int] | None:
        """Nom qui suit un mot d'introduction ; s'arrête avant une forme juridique ou une civilité.

        Name after a cue word; stops before a legal form or an honorific.
        """
        m = _NAME_RIGHT_RE.match(text, pos)
        if m is None:
            return None
        start = end = m.start(1)
        for piece in _PIECE_RE.finditer(text, start, m.end(1)):
            key = fold(piece.group()).replace(".", "")
            if piece.start() > start and (key in V.LEGAL_FORM_KEYS or key in V.STOP):
                break
            if key not in V.PARTICLES and key not in _JOIN_WORDS:
                end = piece.end()  # dernier mot plein / last content word
        return (start, end) if end > start else None

    # --- décision / decision ---------------------------------------------------------------------------------

    def _spans(self, ctx: Any, found: list[tuple[int, int, bool]]) -> list[Span]:
        if not found:
            return []
        # Une seule zone par organisation, la plus longue / one span per organisation, the longest.
        found.sort(key=lambda f: (f[0], -f[1]))
        merged: list[tuple[int, int, bool]] = []
        for start, end, sole in found:
            if merged and start < merged[-1][1]:
                prev = merged[-1]
                merged[-1] = (prev[0], max(prev[1], end), prev[2] or sole)
            else:
                merged.append((start, end, sole))
        text: str = ctx.text
        mode = ctx.settings.company_ids
        spans = []
        segmented = ctx.seg_starts is not None
        for start, end, sole in merged:
            if end <= start or (segmented and end > ctx.segment(start)[2]):
                continue
            words = _WORDS_RE.findall(text, start, end)
            if not words or (len(words) == 1 and (fold(words[0]) in V.ORG_KEYWORDS or fold(words[0]) in V.FUNCTION)):
                continue  # « la Société », « le Groupe » : mot d'introduction seul / cue word alone
            person, only_person, safe = self._person_content(words)
            if only_person:
                # « Dupont SARL », « la SARL Petit » : la raison sociale n'est qu'un nom de personne, masqué comme
                # tel (même balise que « M. Dupont »). The company name is only a person name: a PERSON span.
                spans.append(self._person_span(start, end, safe))
                continue
            personal = person or sole or mode == "mask" or (mode == "auto" and (
                ctx.strict or (bool(self._ei_groups) and ctx.near(self._ei_groups, start, end, 200, 200))))
            spans.append(self._org_span(start, end, personal))
        return spans

    def _person_span(self, start: int, end: int, safe: bool) -> Span:
        return Span(start, end, "PERSON", "PERSON", self.id, 0.8, PRIORITY_HEURISTIC, propagate=safe)

    def _org_span(self, start: int, end: int, personal: bool) -> Span:
        return Span(start, end, "ORG", "ORG", self.id, 0.85, PRIORITY_HEURISTIC if personal else _KEPT_PRIORITY,
                    None, personal, (), True)

    def native_plan(self) -> dict[str, Any] | None:
        """Moteur fusionné : candidats du jumeau, décision en Rust sur le lexique du détecteur de noms natif.

        Fused engine: twin candidates, decision in Rust over the native name detector's lexicon.
        """
        from .fr_names import _native_detector  # import différé : même paquet / deferred: same package

        names = _native_detector()
        if self._native is None or names is None:
            return None
        return {"kind": "organizations", "twin": self._native, "names": names,
                "person": self._person_span(0, 0, False), "masked": self._org_span(0, 0, True),
                "kept": self._org_span(0, 0, False), "keywords": V.ORG_KEYWORDS, "function": V.FUNCTION,
                "particles": V.PARTICLES, "family": V.ORG_FAMILY, "ei_groups": list(self._ei_groups),
                "thresholds": (_SURNAME_MIN, _GIVEN_MIN, _FREQUENT_NAME),
                "ambiguities": (AMB_NONE, AMB_WORD, AMB_ENTITY)}

    def _person_content(self, words: list[str]) -> tuple[bool, bool, bool]:
        """(contient un nom de personne, n'est qu'un nom de personne, sans mot ambigu).

        (has a person name, is only a person name, has no ambiguous word). Articles et particules relient les
        mots sans être des noms ; « Fils », « Associés » non plus. Articles, particles and family-business words
        are never names here.
        """
        keys = [k for k in map(fold, words) if k not in V.PARTICLES and k not in V.FUNCTION]
        codes = [None if k in V.ORG_FAMILY else self._lex.code(k) for k in keys]
        flags = []
        for key, code in zip(keys, codes, strict=True):
            if code is None or len(key) < 3:
                flags.append(False)
                continue
            amb, given, surname = ambiguity(code), given_rank(code), surname_rank(code)
            # Nom sûr, ou nom très porté même s'il est aussi un mot (« Martin », « Petit ») / or very frequent name.
            flags.append((amb == AMB_NONE and (surname >= _SURNAME_MIN or given >= _GIVEN_MIN))
                         or (amb == AMB_WORD and max(given, surname) >= _FREQUENT_NAME))
        names = [c is not None and ambiguity(c) != AMB_ENTITY for c in codes]
        has_pair = sum(names) >= 2 and any(c is not None and given_rank(c) for c in codes)
        person = any(flags) or has_pair
        # « SCI du Moulin » : une particule en tête désigne un lieu ou une enseigne / a leading particle: a place.
        only = person and all(names) and len(keys) <= 4 and fold(words[0]) not in V.PARTICLES
        safe = all(c is not None and ambiguity(c) == AMB_NONE for c in codes)
        return person, only, safe


def _bounded(text: str, start: int, end: int) -> bool:
    """Bornes de mot ; un « . » final tient lieu de borne / word boundaries; a final '.' counts as one.

    Une élision exclut une forme juridique (« l'AG » est une assemblée générale) / an elision rules it out.
    """
    if start > 0 and (text[start - 1].isalnum() or text[start - 1] in "._-'’"):
        return False
    return end >= len(text) or not text[end].isalnum() or text[end - 1] == "."


@cache
def _native_twin() -> Any:
    """Jumeau Rust de la recherche, construit une fois avec les données de ce module / Rust twin, built once."""
    core = _native.core()
    if core is None:
        return None
    return core.OrganizationDetector(
        _native.unicode_table(), case_patterns=_CASE_PATTERNS, forms=len(_FORMS), sole_forms=V.SOLE_TRADER_FORMS,
        prefix_forms=V.LEGAL_FORMS_PREFIX, keywords=sorted(V.ORG_KEYWORDS), joiners=_JOINERS, join_words=_JOIN_WORDS,
        family=V.ORG_FAMILY, legal_form_keys=V.LEGAL_FORM_KEYS, stop=V.STOP, name_articles=_NAME_ARTICLES,
        function=V.FUNCTION, particles=V.PARTICLES)


__all__ = ["OrganizationDetector"]
