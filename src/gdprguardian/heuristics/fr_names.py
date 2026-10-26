"""Détection des personnes sans ML, français d'abord / ML-free person detection, French first.

Deux niveaux : un nom sans ambiguïté suffit quand il est capitalisé ; un nom ambigu (Pierre, Rose, Blanc) exige
un indice : civilité, salutation, signature, étiquette, nom voisin, adresse e-mail, mention confirmée ailleurs.
Two tiers: a capitalised unambiguous name suffices; an ambiguous one needs a cue (honorific, greeting,
signature, label, adjacent name, e-mail address, or a mention confirmed elsewhere in the document).
"""

from __future__ import annotations

import re
import threading
from bisect import bisect_right
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from itertools import pairwise
from typing import Any

import ahocorasick_rs

from .. import _native
from .._text import fold
from ..types import PRIORITY_HEURISTIC, Span
from . import _vocab as V
from ._compose import composed_view
from ._lexicon import (
    AMB_ENTITY,
    AMB_NONE,
    AMB_SHIFT,
    AMB_STRONG,
    AMB_WORD,
    GIVEN_MASK,
    K_COMMON,
    K_INITIAL,
    K_NAME,
    K_PARTICLE,
    K_UNKNOWN,
    ORDINAL_RE,
    RANK_MASK,
    SAINT_PREFIXES,
    SURNAME_SHIFT,
    TOKEN_RE,
    UPPER,
    Lexicon,
    ambiguity,
    given_rank,
    lexicon,
    line_bounds,
    surname_rank,
)

# Seuils de rang (log2 du nombre de naissances) / rank thresholds (log2 of births).
GIVEN_ALONE_MIN = 9     # prénom seul : au moins 512 naissances / given name alone: at least 512 births
SURNAME_ALONE_MIN = 8   # nom seul : au moins 256 porteurs / surname alone: at least 256 bearers
GIVEN_START_MIN = 14    # prénom ambigu en tête de phrase : au moins 16 384 naissances / ambiguous, sentence start
COMMUNE_SURNAME_MIN = 12  # nom homonyme d'une commune, seul : au moins 4 096 porteurs / commune homonym, alone
_ENTITY_GIVEN_MIN = 12    # prénom homonyme d'un lieu ou d'une fête (Noël, Florence), dans une paire / in a pair
CAPS_ALONE_MIN = 10       # nom en capitales seul dans la prose : au moins 1 024 porteurs / caps name alone in prose
MAX_RUN = 6             # jetons capitalisés par nom au plus / capitalised tokens per name at most

# Force des indices / cue strength: négatif (éponyme), aucun, faible (signature), moyen, fort (civilité).
NEG, NONE, WEAK, MEDIUM, STRONG = -1, 0, 1, 2, 3

# Drapeaux des déclencheurs / trigger flags.
T_HONORIFIC, T_GREETING, T_CLOSING, T_ROLE, T_EPONYM, T_EPONYM_DIRECT = 1, 2, 4, 8, 16, 32

_PARTICLES = r"(?:de|du|des|van|von|der|den|di|da|del|della|dos|das|do|ben|bin|ibn|al|el|y|zu|ter|ten|le|la)"
_SPACE_GAP_RE = re.compile(rf"[ \t]{{1,2}}(?:{_PARTICLES}[ \t]{{1,2}}){{0,2}}(?:[dl]')?")
_NEWLINE_GAP_RE = re.compile(r"[ \t]{0,2}\r?\n[ \t]{0,2}")
_INITIAL_GAP_RE = re.compile(r"\.(?:[ \t]{0,2}|-)")
_PARTICLE_AT_RE = re.compile(r"(?:(?:de|du|des|van|von|der|den|di|da|del|della|dos|das)[ \t]{1,2}){1,2}|[dD]'")
_AFTER_HONORIFIC_RE = re.compile(r"\.?[ \t]{0,3}")
_ARTICLE_AT_RE = re.compile(r"(?:le|la|les)(?![^\W\d_])|l'")
_AFTER_CUE_RE = re.compile(r"[ \t]{1,3}(?:,[ \t]{0,2})?|,[ \t]{1,2}")
_AFTER_EPONYM_RE = re.compile(
    r"\.?(?:[ \t]{1,3}|[ \t]{0,2}\r?\n[ \t]{0,2})(?:(?:de[ \t]{1,2}la|du|des|de|la|le|les)[ \t]{1,2}"
    r"|(?:de[ \t]{1,2})?[dlDL]')?")
_AFTER_DIRECT_RE = re.compile(r"[ \t]{1,2}")
_AFTER_LABEL_RE = re.compile(r"[ \t*_]{0,4}")
_LABEL_SPLIT_RE = re.compile(r"[ \t]{2,}|\||\t")
_LIST_GAP_RE = re.compile(
    r"[ \t]{0,2}(?:,[ \t]{0,2}(?:(?:et|and|ou|or|und|y|e)[ \t]{1,2})?|;[ \t]{0,2}|&[ \t]{0,2}"
    r"|(?:et|and|ou|or|und|y|e)[ \t]{1,2})")
_DISPLAY_AT_RE = re.compile(r"[<(\[][ \t]?[\w.+-]{1,64}@")
_EMAIL_LOCAL_RE = re.compile(r"(?<![\w.+-])([a-z][a-z0-9.\-_+]{1,63})@[a-z0-9]")
_LOCAL_SPLIT_RE = re.compile(r"[._\-+]+")
_WORD4_RE = re.compile(r"[^\W\d_]{4,}")
# Séparateur de tableau Markdown, fin de ligne Windows comprise. Quantificateurs bornés : deux `[ \t]*` voisins
# coûtaient un temps quadratique sur une longue ligne d'espaces (30 s pour 50 Ko).
# Markdown table separator, CRLF included. Bounded: adjacent `[ \t]*` were quadratic on a long run of spaces.
_TABLE_SEP_RE = re.compile(r"(?m)^[ \t]{0,3}\|?[ \t]{0,3}:?-{3,512}:?[ \t]{0,3}"
                           r"(?:\|[ \t]{0,3}:?-{3,512}:?[ \t]{0,3}){1,256}\|?[ \t]{0,3}\r?$")
# Trait d'union en fin de ligne au milieu d'un nom (« Anne-⏎Sophie ») / line-break hyphen inside a name.
_HYPHEN_WRAP_RE = re.compile(r"-[ \t]{0,2}\r?\n[ \t]{0,2}")
# Valeur en minuscules d'un champ (« Nom : dupont ») / lowercase field value.
_FIELD_WORD_RE = re.compile(r"[^\W\d_]{2,30}(?:['-][^\W\d_]{1,30}){0,3}")
_FIELD_GAP_RE = re.compile(r"[ \t]{1,2}")
_FIELD_END_RE = re.compile(rf"[ \t]{{0,2}}(?:[\r\n,;|()\[\]/]|$)|[ \t]{{2}}|[ \t](?=[{UPPER}])")
_NAME_CELL_RE = re.compile(r"[^\W\d_](?:[^\W\d_'. -]|[ '.-](?=[^\W\d_ ])){0,58}\.?")
_NUMBER_AFTER_RE = re.compile(r"[ \t]{1,2}(?:[0-9]|[IVXLCDM]{1,6}\b)")
_YEAR_AFTER_RE = re.compile(r"[ \t]{1,2}(?:19|20)[0-9]{2}(?![0-9])")
# Balisage sauté en remontant ; ponctuation qui ouvre une phrase ou un segment (titre, parenthèse, citation).
# Markup skipped backwards; punctuation that opens a sentence or a segment (heading, bracket, quote).
_SKIP_BACK = frozenset(" *_#>•·–—-=~")
_SENTENCE_END = frozenset(".!?…:;\n\t|([{«“\"")
# Terminaisons d'un impératif ou d'un présent en tête de phrase (« Appelle », « Préviens », « Dites »).
# Endings of a sentence-initial imperative or present-tense verb.
_VERB_TAILS = ("e", "s", "z")
_NEXT_WORD_RE = re.compile(r"[ \t]{1,2}([a-zà-ÿœæ'’-]{2,30})")
_VOCATIVE_RE = re.compile(r"[ \t]{0,2}(?:[,!?]|\r?\n|$)")
# Formes juridiques à points (« S.A. », « S.p.A. », « B.V. »), liste finie : un passage Aho-Corasick.
# Dotted legal forms, a finite list: one Aho-Corasick pass on the original text.
_DOTTED_FORMS = sorted({f for f in V.LEGAL_FORMS_SUFFIX if "." in f})
_DOTTED_AC = ahocorasick_rs.AhoCorasick(_DOTTED_FORMS, matchkind=ahocorasick_rs.MatchKind.LeftmostLongest)
# Formes verbales fréquentes après un sujet, aussi présentes comme noms dans les lexèmes / frequent verb forms.
_AUXILIARIES = frozenset({"a", "est", "etait", "sera", "serait", "fut", "va", "vont", "fait", "dit", "peut", "doit",
                          "avait", "aura", "sait", "veut", "part", "reste", "passe", "porte", "pense", "travaille"})
# « Saint Quentin », « SAINT GERMAIN » sans trait d'union : un lieu ou un saint, comme « Saint-Quentin ».
# Hyphenless saint names: a place or a saint, like "Saint-Quentin".
_SAINT_WORDS = frozenset({"saint", "sainte", "st", "ste"})
# Valeur d'une étiquette de champ examinée pour y reconnaître une organisation : une ligne, bornée.
# Field value examined for an organisation: one line, bounded.
_LABEL_VALUE_MAX = 80
_VALUE_STRIP = ",;:()[]\"'«»"
# La valeur propre d'un champ s'arrête avant « pour », « de », « chez » ou un tiret isolé (« Mercier pour Testivo
# SAS »), comme avant une parenthèse ou une virgule. A field's own value stops before these words or a lone dash.
_VALUE_STOPS = frozenset({"pour", "de", "chez"})
_VALUE_DASHES = frozenset({"-", "–", "—"})
# Étiquette suivante sur la même ligne : un à quatre mots puis « : » (« Nom : Dupont Prénom : Jean »).
# The next field label on the same line: one to four words, then ':'.
_LABEL_AHEAD_RE = re.compile(r"(?:[ \t]{1,4}[^\W\d_][\w'’()-]{0,40}){1,4}[ \t]{0,4}:")
# Étiquette de champ : (début de la valeur, force, demande un nom ?, demande un prénom ?).
# Field label cue: (value start, strength, asks for a name?, asks for a given name?).
_LabelCue = tuple[int, int, bool, bool]
# Valeur entière d'un champ d'état civil (« Nom : PANTALON », « Prénom : Chantal, sylvie ») : elle s'arrête en fin
# de ligne ou de colonne ; mots séparés par des espaces ; civilité en tête et mention d'entrepreneur individuel en
# queue retirées. Whole civil-status field value: ends at a line or column end; words split on spaces; a leading
# honorific and a trailing sole-trader mention are dropped.
_FIELD_VALUE_STOP = frozenset("\n\r|\t:")
_FIELD_VALUE_WORD_RE = re.compile(r"[^  ]+")
_FIELD_VALUE_MAX_WORDS = 6
_FIELD_CIVILITIES = frozenset({"monsieur", "madame", "mademoiselle", "m.", "mme", "mlle", "mr"})
_FIELD_SOLE_TRADER = frozenset({"ei", "eirl"})
_FIELD_TRIM = "()[],.;-–—"
# Lettre suivie d'un numéro (« Bodacc A n° 2026… », « Annexe B 2 ») : une lettre de série, pas une initiale.
# A letter followed by a number is a series letter, not an initial.
_SERIES_AFTER_RE = re.compile(r"[ \t]{1,2}(?:[nN][°º]|[0-9])")
# Après un code postal connu vient la commune, jamais une personne (« 30600 VAUVERT ») / a town follows a postcode.
_POSTCODE_CUE_RE = re.compile(r"(?<![\w.,/-])([0-9]{5})[ \t]{1,2}")
# Premier mot replié après le code postal, comparé aux communes du code (« 80300 albert ») / first folded word.
_PLACE_HEAD_RE = re.compile(r"[a-z0-9]+")
_SAINT_LONG = {"st": "saint", "ste": "sainte", "sts": "saints", "stes": "saintes"}


def _given_bias(code: int | None) -> int:
    """Plutôt prénom (> 0) ou plutôt nom (< 0) ? / given-name rather than surname bias of a code."""
    return 0 if code is None else given_rank(code) - surname_rank(code)


def _unwrap(name: str) -> str:
    """« Anne-⏎Sophie » -> « Anne-Sophie » (forme canonique) / rejoins a line-break hyphen."""
    return _HYPHEN_WRAP_RE.sub("-", name) if "\n" in name else name


@cache
def _postcode_heads() -> frozenset[str]:
    """« 80300 albert » : code postal et premier mot de chacune de ses communes, « saint » écrit en entier compris.

    Postcode and first word of each of its towns, the spelled-out "saint" included (built once).
    """
    heads: set[str] = set()
    for code, towns in lexicon().postal.items():
        for town in towns:
            head = town.split(" ", 1)[0]
            heads.add(f"{code} {head}")
            if head in _SAINT_LONG:
                heads.add(f"{code} {_SAINT_LONG[head]}")
    return frozenset(heads)


def surname_form(form: str) -> str:
    """Forme propagée d'un nom trouvé par le noyau : « DUPONT » -> « Dupont ». `str.title()` reste en Python
    (table de casse complète de l'interpréteur). Propagated form of a name found by the core; `str.title()`
    stays in Python (the interpreter's full case table).
    """
    return form.title() if form.isupper() else form


@dataclass(slots=True)
class _Element:
    """Élément d'un nom : un jeton, ou un nom composé de plusieurs jetons / one name element."""

    start: int
    end: int
    kind: int
    code: int
    key: str
    caps: bool

    @property
    def given(self) -> int:
        return given_rank(self.code) if self.kind == K_NAME else 0

    @property
    def surname(self) -> int:
        return surname_rank(self.code) if self.kind == K_NAME else 0

    @property
    def amb(self) -> int:
        return ambiguity(self.code) if self.kind == K_NAME else AMB_NONE

    @property
    def solid(self) -> bool:
        """Nom sûr, ou prénom très fréquent / unambiguous name, or very frequent given name."""
        if self.kind != K_NAME:
            return False
        amb = self.amb
        return (amb == AMB_NONE and bool(self.code & RANK_MASK)) or (amb == AMB_WORD and self.given >= GIVEN_START_MIN)

    @property
    def safe(self) -> bool:
        """Ni mot courant ni lieu : sa forme seule désigne la personne / not a word nor a place."""
        return self.kind == K_UNKNOWN or (self.kind == K_NAME and self.amb == AMB_NONE)


@dataclass(slots=True)
class _Run:
    """Suite de jetons capitalisés qui peut former un nom / capitalised tokens that may form one name."""

    elements: list[_Element]
    cap_left: bool
    cap_right: bool
    evidence: int = NONE
    score: float = 0.0
    addressed: bool = False  # désigné par un rôle ou interpellé (« Bonjour Nath, ») / named by a role or vocative
    labelled: bool = False   # valeur d'une étiquette de champ (« Nom : … ») / value of a field label

    @property
    def start(self) -> int:
        return self.elements[0].start

    @property
    def end(self) -> int:
        return self.elements[-1].end

    def names(self) -> list[_Element]:
        return [e for e in self.elements if e.kind in (K_NAME, K_UNKNOWN)]


@dataclass(slots=True)
class _Cues:
    """Indices d'un document, état local à l'appel / per-call document cues.

    `particle_from` : position d'un nom -> début de la particule qu'un indice désignait (« M. de Villepin »).
    `particle_from`: name position -> start of the particle a cue pointed at.
    """

    at: dict[int, int]
    signature: list[tuple[int, int]]
    strong: list[tuple[int, int]]
    display: set[int]
    particle_from: dict[int, int]
    roles: set[int]       # après « le juge », « mon fils » / after a role or kinship word
    greetings: set[int]   # après « Bonjour », « Cher » / after a greeting
    labels: set[int]      # après une étiquette de champ (« Nom : ») / after a field label
    # Indice négatif d'un code postal dont le mot suivant ne commence aucune de ses communes : un prénom suivi d'un
    # autre nom l'emporte (« Matricule 75012 Sophie Martin »). A postcode's negative cue whose next word starts none
    # of its towns: a given name followed by another name overrides it.
    postcodes: set[int]

    @staticmethod
    def inside(zones: list[tuple[int, int]], start: int, end: int) -> bool:
        i = bisect_right(zones, (start, 1 << 62)) - 1
        return i >= 0 and zones[i][0] <= start and end <= zones[i][1]


class _Triggers:
    """Automate unique des déclencheurs repliés (Aho-Corasick) / single automaton of folded triggers."""

    def __init__(self) -> None:
        flags: dict[str, int] = {}
        for words, flag in ((V.HONORIFICS, T_HONORIFIC), (V.GREETINGS, T_GREETING), (V.CLOSINGS, T_CLOSING),
                            (V.ROLES, T_ROLE), (V.EPONYMS, T_EPONYM), (V.EPONYMS_DIRECT, T_EPONYM_DIRECT)):
            for word in words:
                flags[word] = flags.get(word, 0) | flag
        self.patterns = list(flags)
        self.flags = [flags[p] for p in self.patterns]
        self.check_left = [p[0].isalnum() for p in self.patterns]
        self.check_right = [p[-1].isalnum() for p in self.patterns]
        self.automaton = ahocorasick_rs.AhoCorasick(self.patterns, matchkind=ahocorasick_rs.MatchKind.LeftmostLongest)


# Compilé une fois à l'import (quelques millisecondes), partagé en lecture seule entre threads.
# Compiled once at import (a few milliseconds), shared read-only between threads.
_TRIGGERS = _Triggers()


def _native_data() -> dict[str, Any]:
    """Données du noyau Rust : une seule source, ce module, `_lexicon` et `_vocab`.

    Data for the Rust core, single source of truth: this module, `_lexicon` and `_vocab`. Le noyau compare
    `constants` aux siennes et refuse tout écart / the core checks `constants` against its own.
    """
    lex = lexicon()
    return {
        "unicode": _native.unicode_tables(),  # table Unicode unique du noyau / the core's single Unicode table
        "names": lex.names,
        "words": lex.words,
        "communes": lex.communes,
        "vocabulary": {
            "stop": V.STOP, "particles": V.PARTICLES, "function": V.FUNCTION, "contextual": V.CONTEXTUAL,
            "org_context": V.ORG_CONTEXT, "org_family": V.ORG_FAMILY, "determiners": V.DETERMINERS,
            "locatives": V.LOCATIVES, "strong_labels": V.STRONG_LABELS, "weak_labels": V.WEAK_LABELS,
            "given_headers": V.GIVEN_HEADERS, "surname_headers": V.SURNAME_HEADERS,
            "person_headers": V.PERSON_HEADERS, "empty_cells": V.EMPTY_CELLS,
            "case_sensitive_honorifics": V.CASE_SENSITIVE_HONORIFICS, "auxiliaries": _AUXILIARIES,
            "non_person_labels": V.NON_PERSON_LABELS, "org_leads": V.ORG_LEADS, "company_forms": V.COMPANY_FORM_KEYS,
            "saint_words": _SAINT_WORDS, "surname_particles": V.SURNAME_PARTICLES, "postcodes": lex.postal.keys(),
            "postcode_heads": _postcode_heads(), "titles": V.TITLES,
        },
        "triggers": list(zip(_TRIGGERS.patterns, _TRIGGERS.flags, _TRIGGERS.check_left, _TRIGGERS.check_right,
                             strict=True)),
        "dotted_forms": _DOTTED_FORMS,
        "text_sets": {"saint_prefixes": list(SAINT_PREFIXES), "verb_tails": list(_VERB_TAILS),
                      "skip_back": "".join(sorted(_SKIP_BACK)), "sentence_end": "".join(sorted(_SENTENCE_END))},
        "constants": {
            "GIVEN_MASK": GIVEN_MASK, "SURNAME_SHIFT": SURNAME_SHIFT, "AMB_SHIFT": AMB_SHIFT, "RANK_MASK": RANK_MASK,
            "AMB_NONE": AMB_NONE, "AMB_WORD": AMB_WORD, "AMB_STRONG": AMB_STRONG, "AMB_ENTITY": AMB_ENTITY,
            "T_HONORIFIC": T_HONORIFIC, "T_GREETING": T_GREETING, "T_CLOSING": T_CLOSING, "T_ROLE": T_ROLE,
            "T_EPONYM": T_EPONYM, "T_EPONYM_DIRECT": T_EPONYM_DIRECT, "GIVEN_ALONE_MIN": GIVEN_ALONE_MIN,
            "SURNAME_ALONE_MIN": SURNAME_ALONE_MIN, "GIVEN_START_MIN": GIVEN_START_MIN,
            "COMMUNE_SURNAME_MIN": COMMUNE_SURNAME_MIN, "_ENTITY_GIVEN_MIN": _ENTITY_GIVEN_MIN,
            "CAPS_ALONE_MIN": CAPS_ALONE_MIN, "MAX_RUN": MAX_RUN,
        },
    }


_NATIVE_LOCK = threading.Lock()
_NATIVE: dict[str, Any] = {}


def _native_detector() -> Any:
    """Noyau Rust du détecteur, construit au premier usage, une fois par processus ; None sans noyau.

    Rust core of the detector, built on first use, once per process; None without the core. Rien n'est
    construit si le natif est désactivé. Ensuite en lecture seule, partagé entre threads, sans aucune donnée
    de document. Nothing is built when native code is disabled; then read-only, shared, holding no document data.
    """
    if "core" not in _NATIVE:
        with _NATIVE_LOCK:
            if "core" not in _NATIVE:
                _NATIVE["core"] = _native.name_detector(_native_data)
    return _NATIVE["core"]


class FrenchNameDetector:
    """Personnes : prénoms et noms Insee, déclencheurs, forme canonique pour la coréférence / persons."""

    id = "FR_NAMES"

    def __init__(self, pack: Any = None) -> None:
        self.pack = pack
        self._lex: Lexicon = lexicon()
        self._triggers = _TRIGGERS
        context = getattr(pack, "context", {}) or {}
        # Colonnes de tableur marquées « personne » par leur en-tête / spreadsheet columns tagged "person".
        self._person_groups = tuple(g for g in context if g.endswith(":person"))

    # --- point d'entrée / entry point ---------------------------------------------------------------------

    @composed_view
    def detect(self, ctx: Any) -> list[Span]:
        # Noyau Rust si disponible, mêmes zones que la référence Python / Rust core when available, same spans.
        spans = self._detect_native(ctx) if ctx.settings.native else None
        if spans is None:
            spans = self._detect_python(ctx)
        if ctx.seg_starts is not None:
            # Jamais à cheval sur deux segments / never across segments.
            spans = [s for s in spans if s.end <= ctx.segment(s.start)[2]]
        return spans

    def _detect_native(self, ctx: Any) -> list[Span] | None:
        """Chemin Rust, sans GIL ; None sans noyau, ou si le texte contient des demi-paires isolées ou dépasse 1 Go.

        Rust path, GIL released; None without the core, or when the text holds lone surrogates (not encodable
        as UTF-8) or exceeds 1 GB: the Python path then takes over.
        """
        core = _native_detector()
        found = None if core is None else core.detect(ctx.text, ctx.folded, self._person_rows(ctx))
        if found is None:
            return None
        return [self._native_span(start, end, value, score, propagate, form)
                for start, end, value, score, propagate, form in found]

    def _native_span(self, start: int, end: int, value: str, score: float, propagate: bool,
                     form: str | None) -> Span:
        """Zone d'une personne trouvée par le noyau / a person span found by the core."""
        return Span(start, end, "PERSON", "PERSON", self.id, score, PRIORITY_HEURISTIC, value, True,
                    () if form is None else (surname_form(form),), propagate)

    def native_plan(self) -> dict[str, Any] | None:
        """Moteur fusionné : noyau du détecteur, groupes « personne » des en-têtes / fused engine: core, groups."""
        core = _native_detector()
        if core is None:
            return None
        return {"kind": "names", "twin": core, "prototype": self._native_span(0, 0, "", 0.0, False, None),
                "person_groups": list(self._person_groups), "surname_form": surname_form}

    def _detect_python(self, ctx: Any) -> list[Span]:
        """Référence Python : la spécification du noyau Rust / Python reference: the Rust core's specification."""
        text: str = ctx.text
        spans, strong_zones, confirmed = self._structured(ctx)
        labels = list(self._label_cues(text)) if ":" in text else []
        if labels:
            spans.extend(self._lowercase_fields(text, labels))
            spans.extend(self._field_values(text, labels, spans))
        tokens = self._tokens(text, ctx.folded)
        cues = self._cues(ctx, strong_zones, labels)
        spans.extend(self._lowercase_after_cues(text, cues, spans))
        if tokens:
            if "@" in text:
                confirmed |= self._email_names(ctx)
            runs = self._runs(tokens, text, sorted((s.start, s.end) for s in spans))
            accepted, eponyms = self._decide(ctx, runs, cues, confirmed)
            spans.extend(self._span(run, text, cues, eponyms) for run in accepted)
        return spans

    def _person_rows(self, ctx: Any) -> list[tuple[int, int]]:
        """Segments marqués « personne » par l'en-tête de leur colonne / segments tagged "person" by header."""
        if not (self._person_groups and ctx.forced and ctx.seg_starts is not None):
            return []
        return [(ctx.seg_starts[index], ctx.seg_ends[index]) for index, groups in enumerate(ctx.forced)
                if any(g in groups for g in self._person_groups)]

    # --- jetons et suites / tokens and runs ---------------------------------------------------------------

    def _tokens(self, text: str, folded: str) -> list[_Element]:
        classify = self._lex.classify
        forms = self._dotted_forms(text) if "." in text else set()
        tokens: list[_Element] = []
        append = tokens.append
        for m in TOKEN_RE.finditer(text):
            start, end = m.span()
            if start > 1 and text[start - 1] == "-" and text[start - 2].isalpha():
                continue  # fin d'un composé en minuscules (« anti-Macron ») / tail of a lowercase compound
            if end - start > 3 and folded.startswith("'s", end - 2):
                end -= 2  # possessif hors de la zone (« Johnson's ») / possessive kept outside the span
            original = text[start:end]
            key = folded[start:end]
            if start in forms:
                kind, code = K_COMMON, 0  # « S.p.A. », « B.V. » : forme juridique, pas des initiales
            elif key == "n" and text[end:end + 1] == "°":
                kind, code = K_COMMON, 0  # « AVENANT N° 2 » : signe de numéro, pas une initiale / a number sign
            elif end - start == 1 and text[end:end + 1] == "." and key not in V.STOP:
                kind, code = K_INITIAL, 0  # « A. Lambert » : initiale, même si « a » est un mot / an initial
            else:
                kind, code = classify(key, original)
            if (tokens and text.startswith("-", tokens[-1].end) and kind in (K_NAME, K_UNKNOWN)
                    and tokens[-1].kind in (K_NAME, K_UNKNOWN)
                    and _HYPHEN_WRAP_RE.fullmatch(text, tokens[-1].end, start) is not None):
                # « Anne-⏎Sophie » : un seul nom composé, coupé en fin de ligne / one compound split by a line break.
                left = tokens.pop()
                start, key = left.start, f"{left.key}-{key}"
                kind, code = classify(key, f"{text[left.start:left.end]}-{original}")
                original = f"{text[left.start:left.end]}{original}"
            append(_Element(start, end, kind, code, key, end - start > 1 and original.isupper()))
        return self._compound_tokens(tokens, text)

    @staticmethod
    def _compound_tokens(tokens: list[_Element], text: str) -> list[_Element]:
        """Deux jetons séparés d'une espace qui ne forment qu'un élément / two tokens that make one element.

        « Saint Quentin » sans trait d'union : un lieu ou un saint, comme « Saint-Quentin » (inconnu, nom seulement
        avec un indice). « Paul Le Verger » : après un prénom, une particule capitalisée et le mot qui la suit forment
        le nom de famille, même si ce mot est un mot courant. "Saint Quentin" without a hyphen is one unknown
        element, like "Saint-Quentin"; after a given name, a capitalised particle and the next word form the
        surname, even when that word is a common word.
        """
        out: list[_Element] = []
        k, n = 0, len(tokens)
        while k < n:
            token = tokens[k]
            nxt = tokens[k + 1] if k + 1 < n else None
            if nxt is not None and text[token.end:nxt.start] == " ":
                saint = token.key in _SAINT_WORDS and nxt.kind in (K_NAME, K_UNKNOWN)
                prev = out[-1] if out else None
                particle = (token.key in V.SURNAME_PARTICLES and text[token.start].isupper() and prev is not None
                            and prev.kind == K_NAME and given_rank(prev.code) > 0
                            and ambiguity(prev.code) != AMB_ENTITY and text[prev.end:token.start] == " "
                            and nxt.kind == K_COMMON and len(nxt.key) >= 2 and nxt.key not in V.STOP
                            and ORDINAL_RE.fullmatch(text, nxt.start, nxt.end) is None)
                if saint or particle:
                    out.append(_Element(token.start, nxt.end, K_UNKNOWN, 0, f"{token.key} {nxt.key}",
                                        token.caps and nxt.caps))
                    k += 2
                    continue
            out.append(token)
            k += 1
        return out

    @staticmethod
    def _dotted_forms(text: str) -> set[int]:
        """Positions des lettres des formes juridiques à points (« S.A.R.L. », « S.p.A. ») / their letters."""
        covered: set[int] = set()
        for _, start, end in _DOTTED_AC.find_matches_as_indexes(text, overlapping=False):
            if (start == 0 or not text[start - 1].isalnum()) and (end == len(text) or not text[end].isalnum()):
                covered.update(range(start, end))
        return covered

    @staticmethod
    def _joins(text: str, left: _Element, right: _Element) -> bool:
        """Deux jetons forment-ils un même nom (espace, particule, initiale) ? / same-name gap test."""
        gap = text[left.end:right.start]
        if gap == " ":
            return True
        if left.kind == K_INITIAL:
            return _INITIAL_GAP_RE.fullmatch(gap) is not None
        if "\n" in gap:
            # Retour à la ligne forcé au milieu d'un nom : « Mme Claire⏎Martin-Dubois » / hard-wrapped name.
            return (_NEWLINE_GAP_RE.fullmatch(gap) is not None and left.given > 0 and right.kind in (K_NAME, K_UNKNOWN)
                    and not right.given and text[left.start - 1:left.start] == " ")
        if _SPACE_GAP_RE.fullmatch(gap) is None:
            return False
        if not gap.strip(" \t"):
            return True
        # Après une particule vient un nom de famille (« de Gaulle »), pas un prénom ni un lieu (« de Simon »,
        # « de Bretagne ») : sinon « de » relie deux entités. After a particle comes a surname, not a given name.
        if right.kind == K_UNKNOWN:
            return not (right.caps and len(right.key) <= 3)  # « du FC Barcelone » : sigle / acronym
        return right.kind == K_PARTICLE or (
            right.kind == K_NAME and right.amb in (AMB_NONE, AMB_WORD) and right.surname >= right.given)

    def _runs(self, tokens: list[_Element], text: str, claimed: list[tuple[int, int]]) -> list[_Run]:
        runs: list[_Run] = []
        n = len(tokens)
        joins = self._joins

        def is_trigger(i: int) -> bool:
            # Un mot de rôle ou de voie suivi d'un nom sert de déclencheur ; en capitales, c'est un nom de
            # famille (« VALLÉE Nath »). A role or street word before a name is a trigger; in capitals, a surname.
            return (tokens[i].key in V.CONTEXTUAL and not tokens[i].caps and i + 1 < n
                    and tokens[i + 1].kind != K_COMMON and joins(text, tokens[i], tokens[i + 1]))

        def content_word(i: int) -> bool:
            # Mot courant capitalisé voisin : « Mont Blanc », « Radio France ». Le contexte d'organisation
            # (« Boulangerie Petit SARL ») et les ordinaux (« François Ier ») n'en sont pas.
            # Adjacent capitalised common word; organisation context and ordinals are not.
            token = tokens[i]
            return (token.kind == K_COMMON and token.key not in V.FUNCTION and token.key not in V.ORG_CONTEXT
                    and ORDINAL_RE.fullmatch(text, token.start, token.end) is None)

        i = 0
        while i < n:
            if tokens[i].kind == K_COMMON or is_trigger(i):
                i += 1
                continue
            j = i
            while (j + 1 < n and j - i < MAX_RUN - 1 and tokens[j + 1].kind != K_COMMON
                   and joins(text, tokens[j], tokens[j + 1]) and not is_trigger(j + 1)):
                j += 1
            elements = self._merge(tokens[i:j + 1], text)
            first = elements[0]
            rare = first.kind == K_UNKNOWN or (first.kind == K_NAME and not first.given
                                                and first.surname < SURNAME_ALONE_MIN)
            if (len(elements) > 1 and rare and not first.caps and first.key.endswith(_VERB_TAILS)
                    and elements[1].given and self._sentence_start(text, first.start)):
                elements = elements[1:]  # « Appelle Pierre » : verbe en tête / leading verb
            useful = any(e.kind != K_PARTICLE for e in elements)
            if useful and not (claimed and _Cues.inside(claimed, elements[0].start, elements[-1].end)):
                cap_left = i > 0 and content_word(i - 1) and joins(text, tokens[i - 1], tokens[i])
                cap_right = j + 1 < n and content_word(j + 1) and joins(text, tokens[j], tokens[j + 1])
                runs.extend(_Run(part, cap_left and part[0] is elements[0], cap_right and part[-1] is elements[-1])
                            for part in self._split(elements))
            i = j + 1
        return runs

    @staticmethod
    def _split(elements: list[_Element]) -> list[list[_Element]]:
        """Sépare deux personnes accolées et retire un lieu en bordure / splits adjacent persons, trims places.

        « Olivier Blanchard Jean Tirole » (bibliographie) ; « maire de Paris Anne Hidalgo ».
        """
        if len(elements) == 4 and all(e.kind == K_NAME for e in elements) and elements[0].given \
                and elements[2].given and elements[1].surname and elements[3].surname \
                and elements[2].given > elements[2].surname and elements[1].surname >= elements[1].given:
            return [elements[:2], elements[2:]]
        if sum(1 for e in elements if e.kind in (K_NAME, K_UNKNOWN)) >= 3:
            # En tête, un lieu ou un mot inconnu avant le prénom n'appartient pas au nom (« DeepMind Stuart
            # Russell ») ; en queue, un lieu non plus. A leading place or unknown word before the given name is cut.
            while len(elements) > 2 and not elements[0].given and (
                    elements[0].kind == K_UNKNOWN or (elements[0].kind == K_NAME and elements[0].amb == AMB_ENTITY)) \
                    and any(e.given for e in elements[1:]):
                elements = elements[1:]
            if elements[-1].kind == K_NAME and elements[-1].amb == AMB_ENTITY and len(elements) > 2:
                elements = elements[:-1]
        return [elements]

    def _merge(self, tokens: list[_Element], text: str) -> list[_Element]:
        """Fusionne les noms à plusieurs mots connus (Le Goff, Da Silva) / merges known multiword names."""
        if len(tokens) < 2:
            return tokens
        names = self._lex.names
        out: list[_Element] = []
        i = 0
        while i < len(tokens):
            merged = None
            for width in (3, 2):
                group = tokens[i:i + width]
                if len(group) == width and all(text[a.end:b.start] == " " for a, b in pairwise(group)):
                    key = " ".join(t.key for t in group)
                    code = names.get(key)
                    if code is not None:
                        merged = _Element(group[0].start, group[-1].end, K_NAME, code, key, all(t.caps for t in group))
                        i += width
                        break
            if merged is None:
                merged = tokens[i]
                i += 1
            out.append(merged)
        return out

    # --- indices / cues --------------------------------------------------------------------------------------

    def _cues(self, ctx: Any, strong_zones: list[tuple[int, int]], labels: list[_LabelCue]) -> _Cues:
        text: str = ctx.text
        folded: str = ctx.folded
        length = len(text)
        trig = self._triggers
        at: dict[int, int] = {}
        negative: set[int] = set()
        signature: list[tuple[int, int]] = []
        particle_from: dict[int, int] = {}
        roles: set[int] = set()
        greetings: set[int] = set()
        labelled: set[int] = set()

        def put(pos: int, level: int, shift: bool = True, kind: set[int] | None = None) -> None:
            # L'indice vaut aussi après une particule (« M. de Villepin ») ; un éponyme l'emporte toujours.
            # The cue also holds past a particle; an eponym always wins.
            shifted = _PARTICLE_AT_RE.match(text, pos) if shift else None
            targets = (pos,)
            if shifted is not None:
                targets = (pos, shifted.end())
                particle_from[shifted.end()] = pos
            for p in targets:
                current = at.get(p, NONE)
                if level == NEG or (current != NEG and current < level):
                    at[p] = level
                if kind is not None:
                    kind.add(p)

        for index, start, end in trig.automaton.find_matches_as_indexes(folded, overlapping=False):
            # Un trait d'union lie les mots : « Notre-Dame » ne contient pas la civilité « Dame ».
            # A hyphen binds words: "Notre-Dame" does not contain the honorific "Dame".
            if (trig.check_left[index] and start > 0 and (folded[start - 1].isalnum() or folded[start - 1] == "-")) \
                    or (trig.check_right[index] and end < length and (folded[end].isalnum() or folded[end] == "-")):
                continue
            flags = trig.flags[index]
            if flags & T_HONORIFIC and trig.patterns[index] in V.CASE_SENSITIVE_HONORIFICS \
                    and not text[start].isupper():
                flags &= ~T_HONORIFIC
            if flags & (T_EPONYM | T_EPONYM_DIRECT | T_ROLE) and end - start > 1 and text[start:end].isupper():
                flags &= ~(T_EPONYM | T_EPONYM_DIRECT | T_ROLE)  # « VALLÉE Nath » : nom en capitales / caps surname
            if flags & T_CLOSING:
                zone = self._signature_zone(text, end)
                if zone is not None:
                    signature.append(zone)
            if flags & T_EPONYM or start in negative:
                # « rue du Docteur Roux » : l'éponyme se transmet à la civilité suivante / eponym chains on.
                after = _AFTER_EPONYM_RE.match(text, end)
                if after is not None:
                    negative.add(after.end())
                    put(after.end(), NEG)
            elif flags & T_EPONYM_DIRECT:
                after = _AFTER_DIRECT_RE.match(text, end)  # « tour Eiffel », pas « le tour de Pierre »
                if after is not None:
                    negative.add(after.end())
                    put(after.end(), NEG, shift=False)
            elif flags & T_HONORIFIC:
                nxt = _AFTER_HONORIFIC_RE.match(text, end).end()
                # « M. le Maire » n'est pas un nom, « M. Le Verger » en est un / is not a name, "M. Le Verger" is.
                if (nxt > end or folded[end - 1] == ".") and (_ARTICLE_AT_RE.match(folded, nxt) is None
                                                              or self._particle_surname(text, folded, nxt)):
                    put(nxt, STRONG)
            elif flags & (T_GREETING | T_ROLE):
                m = _AFTER_CUE_RE.match(text, end)
                if m is not None:
                    # « chez » désigne aussi un lieu ou un organisme : pas d'interpellation / not addressing anyone.
                    kind = greetings if flags & T_GREETING else None if trig.patterns[index] == "chez" else roles
                    put(m.end(), MEDIUM, kind=kind)
        postal = self._lex.postal
        postcodes: set[int] = set()
        for m in _POSTCODE_CUE_RE.finditer(text):
            code = m.group(1)
            if code in postal:
                pos = m.end()
                head = _PLACE_HEAD_RE.match(folded, pos)
                if at.get(pos) != NEG and (head is None or f"{code} {head.group()}" not in _postcode_heads()):
                    postcodes.add(pos)  # pas le début d'une de ses communes / not the start of one of its towns
                put(pos, NEG, shift=False)  # « 30600 VAUVERT » : la commune / the town
        for pos, level, *_ in labels:
            put(pos, level, kind=labelled)
        signature.sort()
        display = self._display_ends(text) if "@" in text else set()
        return _Cues(at, signature, sorted(strong_zones), display, particle_from, roles, greetings, labelled,
                     postcodes)

    def _particle_surname(self, text: str, folded: str, pos: int) -> bool:
        """« M. Le Verger » : article capitalisé et mot suivant formant un nom connu (« le verger »), ni rôle ni titre.

        A capitalised article and the next word forming a known name, neither a role ("M. Le Maire") nor a title.
        """
        if not (text[pos:pos + 1].isupper() and folded[pos:pos + 3] in ("le ", "la ")):
            return False
        token = TOKEN_RE.match(text, pos + 3)
        if token is None:
            return False
        word = folded[pos + 3:token.end()]
        return (folded[pos:token.end()] in self._lex.names and word not in V.CONTEXTUAL
                and word not in V.TITLES)

    def _label_cues(self, text: str) -> Iterator[_LabelCue]:
        """« Nom : Dupont », « De : Jean Martin » en début de ligne ou de colonne / field labels.

        Produit (début de la valeur, force, l'étiquette demande-t-elle un nom ?) / yields (value start, strength,
        does the label ask for a name?). « Nom commercial : » n'est pas une étiquette de personne, et une valeur qui
        est une organisation (« Ville de … », « … SAS ») n'est pas un nom. "Nom commercial :" is not a person
        label, and a value that is an organisation is not a name.
        """
        pos = text.find(":")
        while pos != -1:
            line_start = text.rfind("\n", max(0, pos - 61), pos) + 1
            if line_start or pos <= 61:
                raw = _LABEL_SPLIT_RE.split(text[line_start:pos])[-1]
                label = fold(raw).strip(" >*_#-`•")
                level = STRONG if label in V.STRONG_LABELS else MEDIUM if label in V.WEAK_LABELS else NONE
                if not level and " " in label and label not in V.NON_PERSON_LABELS:
                    # « Étaient présents : », « Le médecin traitant : » : dernier mot / last word of the label.
                    last = label.rsplit(" ", 1)[-1]
                    level = MEDIUM if last in V.STRONG_LABELS or last in V.WEAK_LABELS else NONE
                if level:
                    value = _AFTER_LABEL_RE.match(text, pos + 1).end()
                    if not self._organisation_value(text, value):
                        given = label in V.GIVEN_HEADERS
                        yield value, level, given or label in V.SURNAME_HEADERS, given
            pos = text.find(":", pos + 1)

    def _organisation_value(self, text: str, pos: int) -> bool:
        """La valeur d'un champ est-elle une organisation ? / is the field value an organisation?

        Une forme juridique de société (« SAS », « S.A.R.L. », pas « EI ») parmi les mots de la valeur propre, avant
        « pour », « de », « chez », une parenthèse, une virgule ou un tiret (« Mercier pour Testivo SAS » reste un
        nom), ou un premier mot d'organisme (« Ville », « Syndicat ») suivi d'autre chose qu'un prénom (« MAISON
        Pierre » reste un nom). A company legal form among the words of the value itself (before "pour", "de",
        "chez", a bracket, a comma or a dash), or an organisation first word followed by anything but a given name.
        """
        end = text.find("\n", pos, pos + _LABEL_VALUE_MAX)
        value = text[pos:end if end >= 0 else pos + _LABEL_VALUE_MAX]
        for raw in value.split("(", 1)[0].split(",", 1)[0].split():
            if raw in _VALUE_DASHES or fold(raw) in _VALUE_STOPS:
                break
            word = raw.strip(_VALUE_STRIP)
            if word and (word.isupper() or "." in word) and fold(word).replace(".", "") in V.COMPANY_FORM_KEYS:
                return True
        words = [w.strip(_VALUE_STRIP) for w in value.split()]
        words = [w for w in words if w]
        if len(words) < 2 or fold(words[0]) not in V.ORG_LEADS:
            return False
        code = self._lex.code(fold(words[1]))
        return code is None or given_rank(code) < GIVEN_ALONE_MIN

    def _field_values(self, text: str, labels: list[_LabelCue], found: list[Span]) -> list[Span]:
        """« Nom : PANTALON ⏎ Prénom : Chantal, sylvie » : valeur entière d'un champ d'état civil.

        Whole value of a civil-status field, whatever its case or whether its words are in the dictionary. Only
        in a document with a given-name field (« Prénom : »), so that « Nom : TESTIX INDUSTRIES » alone stays a
        company. The value ends at the end of the line or column, within 80 characters, with no other label on
        the line; it holds 1 to 6 words, no digit and no « @ », and is not an empty cell (« Non précisé »). A
        value already found with the same bounds (`found`, « Nom : dupont jean ») keeps its span and its
        propagation choice.
        """
        if not any(given for *_, given in labels):
            return []
        taken = {(s.start, s.end) for s in found}
        spans: list[Span] = []
        length = len(text)
        for pos, level, asks_name, _ in labels:
            if level != STRONG or not asks_name:
                continue
            limit = min(length, pos + _LABEL_VALUE_MAX)
            end = pos
            while end < limit and text[end] not in _FIELD_VALUE_STOP:
                end += 1
            if (end == limit and limit < length) or (end < length and text[end] == ":"):
                continue  # trop longue, ou autre étiquette sur la ligne / too long, or another label on the line
            words = [[m.start(), m.end()] for m in _FIELD_VALUE_WORD_RE.finditer(text, pos, end)]
            if words and fold(text[words[0][0]:words[0][1]]) in _FIELD_CIVILITIES:
                words.pop(0)
            while words:
                key = fold(text[words[-1][0]:words[-1][1]]).strip(_FIELD_TRIM)
                if not key or key in _FIELD_SOLE_TRADER:
                    words.pop()
                elif key == "individuel" and len(words) >= 2 \
                        and fold(text[words[-2][0]:words[-2][1]]).strip(_FIELD_TRIM) == "entrepreneur":
                    del words[-2:]
                else:
                    break
            if not words or len(words) > _FIELD_VALUE_MAX_WORDS:
                continue
            start, stop = words[0][0], words[-1][1]
            while stop > start and text[stop - 1] in _FIELD_TRIM:
                stop -= 1
            value = text[start:stop]
            if not any(c.isalnum() for c in value) or any(c in "0123456789@" for c in value) \
                    or fold(value) in V.EMPTY_CELLS or (start, stop) in taken:
                continue
            # Propagée seulement si aucun mot n'est un mot courant, une commune ou un nom ambigu (« Nom : LYON »,
            # « ROUGE », « LA POSTE » : la valeur seule est masquée). Valeur en capitales : aussi propagée en casse
            # de titre (« TESTAGAR » -> « Nom commercial : Testagar »). Propagated only when no word is a common
            # word, a town or an ambiguous name; a capitals value is also propagated in title case.
            safe = self._field_safe(text, words)
            forms = (surname_form(value),) if safe and value.isupper() else ()
            spans.append(Span(start, stop, "PERSON", "PERSON", self.id, 0.85, PRIORITY_HEURISTIC, value, True,
                              forms, propagate=safe))
        return spans

    def _field_safe(self, text: str, words: list[list[int]]) -> bool:
        """Un mot au moins de la valeur (particules à part) n'est ni un mot courant, ni une commune, ni un nom
        ambigu : « LYON », « LA POSTE » non, « Testo le Magnifique » oui.

        At least one word of the value (particles aside) is not a common word, a town or an ambiguous name.
        """
        lex = self._lex
        names = risky = 0
        for ws, we in words:
            key = fold(text[ws:we]).strip(_FIELD_TRIM)
            if not key or key in V.PARTICLES:
                continue
            names += 1
            code = lex.code(key)
            if key in lex.words or key.replace("-", " ") in lex.communes \
                    or (code is not None and ambiguity(code) != AMB_NONE):
                risky += 1
        return risky < names

    def _lowercase_fields(self, text: str, labels: list[_LabelCue]) -> list[Span]:
        """« Nom : dupont », « Prénom : jean » : valeur en minuscules après une étiquette forte.

        Lowercase value after a strong field label (the token path only sees capitalised words). The value
        stops at a common word; a lone unknown word counts only after a label that asks for a name.
        """
        lex = self._lex
        spans: list[Span] = []
        for pos, level, asks_name, _ in labels:
            first = _FIELD_WORD_RE.match(text, pos) if level == STRONG else None
            if first is None or not first.group().islower():
                continue
            # Les mots suivants peuvent être capitalisés (« jean Dupont ») / later words may be capitalised.
            words: list[tuple[int, int, str, int | None]] = []
            m: re.Match[str] | None = first
            while m is not None and len(words) < 4:
                key = fold(m.group())
                code = lex.code(key)
                if key not in V.PARTICLES and (key in V.FUNCTION or key in V.STOP or key in V.EMPTY_CELLS
                                               or (code is None and key in lex.words)):
                    break  # mot courant : ce n'est pas un nom / a common word: not a name
                words.append((m.start(), m.end(), key, code))
                gap = _FIELD_GAP_RE.match(text, m.end())
                m = _FIELD_WORD_RE.match(text, gap.end()) if gap is not None else None
            while words and words[-1][2] in V.PARTICLES:
                words.pop()
            names = [w for w in words if w[2] not in V.PARTICLES]
            if not names or _FIELD_END_RE.match(text, words[-1][1]) is None:
                continue  # rien, ou une phrase qui continue / nothing, or a sentence going on
            if not asks_name and all(code is None for *_, code in names):
                continue  # « Bénéficiaire : désigné » : mot inconnu seul / unknown word under a role label
            given, surname = names[0], names[-1]
            if len(names) >= 2 and _given_bias(surname[3]) > _given_bias(given[3]):
                given, surname = surname, given  # « dupont jean » : ordre Nom Prénom / surname-first order
            value = " ".join(dict.fromkeys(text[w[0]:w[1]] for w in (given, surname)))
            safe = all(code is None or ambiguity(code) == AMB_NONE for *_, code in names)
            spans.append(Span(words[0][0], words[-1][1], "PERSON", "PERSON", self.id, 0.85, PRIORITY_HEURISTIC,
                              value, True, propagate=safe))
        return spans

    def _lowercase_after_cues(self, text: str, cues: _Cues, taken: list[Span]) -> list[Span]:
        """« client guillaume », « Bonjour guillaume », « M. dupont » : nom en minuscules juste après un indice.

        Lowercase name right after a cue (chats, tickets, text messages). Only known given names or surnames
        with no other reading count: « client fidèle » and « mon fils pierre » stay as they are.
        """
        lex = self._lex
        covered = sorted((s.start, s.end) for s in taken)
        spans: list[Span] = []
        for pos, level in cues.at.items():
            first = _FIELD_WORD_RE.match(text, pos) if level >= MEDIUM else None
            if first is None or not first.group().islower() or _Cues.inside(covered, pos, first.end()):
                continue
            # Le mot suivant peut être capitalisé (« guillaume Martin ») / the next word may be capitalised.
            words: list[tuple[int, int, int]] = []
            m: re.Match[str] | None = first
            while m is not None and len(words) < 3:
                key = fold(m.group())
                code = lex.code(key)
                if code is None or key in V.FUNCTION or key in V.STOP:
                    break
                if words:
                    # Après un prénom retenu, un nom connu suffit, même homonyme (« guillaume martin »).
                    # After an accepted given name, a known surname is enough, even a homonym.
                    if surname_rank(code) < SURNAME_ALONE_MIN:
                        break
                elif (key in lex.words or ambiguity(code) != AMB_NONE
                      or (given_rank(code) < GIVEN_ALONE_MIN and surname_rank(code) < SURNAME_ALONE_MIN)):
                    break  # mot courant, rare ou ambigu : pas un nom / common, rare or ambiguous word
                words.append((m.start(), m.end(), code))
                gap = _FIELD_GAP_RE.match(text, m.end())
                m = _FIELD_WORD_RE.match(text, gap.end()) if gap is not None else None
            if not words:
                continue
            given, surname = words[0], words[-1]
            if len(words) >= 2 and _given_bias(surname[2]) > _given_bias(given[2]):
                given, surname = surname, given  # « dupont jean » : ordre Nom Prénom / surname-first order
            value = " ".join(dict.fromkeys(text[w[0]:w[1]] for w in (given, surname)))
            spans.append(Span(words[0][0], words[-1][1], "PERSON", "PERSON", self.id, 0.8, PRIORITY_HEURISTIC,
                              value, True, propagate=True))
        return spans

    @staticmethod
    def _signature_zone(text: str, end: int) -> tuple[int, int] | None:
        """Les trois lignes non vides après une formule de fin seule sur sa ligne / three lines after a closing."""
        line_end = text.find("\n", end, end + 80)
        if line_end < 0 or text[end:line_end].strip(" \t\r,.!") != "":
            return None
        pos, lines, limit = line_end, 0, min(len(text), line_end + 300)
        while pos < limit and lines < 3:
            nxt = text.find("\n", pos + 1)
            nxt = limit if nxt < 0 or nxt > limit else nxt
            if text[pos + 1:nxt].strip():
                lines += 1
            pos = nxt
        return line_end, pos

    @staticmethod
    def _display_ends(text: str) -> set[int]:
        """Fins de « Jean Dupont <jean.dupont@…> » / positions right before an e-mail in brackets."""
        ends = set()
        for m in _DISPLAY_AT_RE.finditer(text):
            j = m.start()
            while j > 0 and text[j - 1] in " \t":
                j -= 1
            if j > 0 and text[j - 1] == '"':
                j -= 1
            ends.add(j)
        return ends

    def _email_names(self, ctx: Any) -> set[str]:
        """Noms tirés des parties locales prenom.nom@ / names from e-mail local parts (folded)."""
        lex = self._lex
        found: set[str] = set()
        for m in _EMAIL_LOCAL_RE.finditer(ctx.folded):
            parts = [p.strip("0123456789") for p in _LOCAL_SPLIT_RE.split(m.group(1))]
            parts = [p for p in parts if p.isalpha() and len(p) >= 2]
            codes = [lex.code(p) for p in parts]
            if len(parts) >= 2:
                # « jean.dupont@ » (un prénom), ou deux parties qui ne sont pas des mots (« detlev.wagenknecht@ »).
                # A given name among the parts, or two parts that are not common words.
                plain = [p for p in parts if p not in lex.words and p not in V.STOP]
                if any(c is not None and given_rank(c) and ambiguity(c) != AMB_ENTITY for c in codes) or (
                        len(parts) == 2 and len(plain) == 2 and all(len(p) >= 3 for p in parts)):
                    found.update(plain)
            elif len(parts) == 1:
                part = parts[0]
                for candidate in (part, part[1:], part[:-1]):  # « jdupont », « dupontj »
                    code = lex.code(candidate) if len(candidate) >= 4 else None
                    if code is not None and ambiguity(code) == AMB_NONE and (
                            surname_rank(code) >= SURNAME_ALONE_MIN or (candidate == part and given_rank(code))):
                        found.add(candidate)
                        break
        return found

    # --- tableaux et cellules / tables and cells ------------------------------------------------------------

    def _structured(self, ctx: Any) -> tuple[list[Span], list[tuple[int, int]], set[str]]:
        """Colonnes de personnes : tableaux Markdown, segments étiquetés par leur en-tête.

        Person columns: Markdown tables, header-tagged segments. Returns emitted spans, strong-cue cells
        (not name-shaped) and confirmed ambiguous forms.
        """
        spans: list[Span] = []
        zones: list[tuple[int, int]] = []
        confirmed: set[str] = set()
        text: str = ctx.text
        if "|" in text and "---" in text:
            for row in self._table_rows(text):
                self._row_spans(text, row, spans, zones, confirmed)
        for start, end in self._person_rows(ctx):
            self._row_spans(text, [(start, end, "full")], spans, zones, confirmed)
        return spans, zones, confirmed

    @staticmethod
    def _cells(text: str, start: int, end: int) -> list[tuple[int, int]]:
        line = text[start:end]
        bars = [i for i, ch in enumerate(line) if ch == "|"]
        if not bars:
            return []
        edges = ([-1] if line[:bars[0]].strip() else []) + bars + ([len(line)] if line[bars[-1] + 1:].strip() else [])
        cells = []
        for left, right in pairwise(edges):
            cell = line[left + 1:right]
            offset = start + left + 1 + len(cell) - len(cell.lstrip())
            cells.append((offset, offset + len(cell.strip())))
        return cells

    def _table_rows(self, text: str) -> list[list[tuple[int, int, str]]]:
        rows: list[list[tuple[int, int, str]]] = []
        consumed = 0
        for sep in _TABLE_SEP_RE.finditer(text):
            header_end = sep.start() - 1
            if header_end <= 0 or sep.start() < consumed:
                continue  # séparateur déjà lu comme ligne d'un tableau / already read as a table row
            header_start, _, whole = line_bounds(text, header_end, 2048)
            if not whole:
                continue
            roles = []
            for s, e in self._cells(text, header_start, header_end):
                label = fold(text[s:e]).strip(" *_`")
                roles.append("given" if label in V.GIVEN_HEADERS else "surname" if label in V.SURNAME_HEADERS
                             else "full" if label in V.PERSON_HEADERS else "")
            if not any(roles):
                continue
            pos = sep.end() + 1
            while pos < len(text):
                line_end = text.find("\n", pos)
                line_end = len(text) if line_end < 0 else line_end
                if "|" not in text[pos:line_end]:
                    break
                cells = self._cells(text, pos, line_end)
                rows.append([(s, e, roles[k]) for k, (s, e) in enumerate(cells) if k < len(roles) and roles[k]])
                pos = line_end + 1
            consumed = pos
        return rows

    def _row_spans(self, text: str, row: list[tuple[int, int, str]], spans: list[Span],
                   zones: list[tuple[int, int]], confirmed: set[str]) -> None:
        """Une ligne : prénom et nom partagent la même forme canonique / given and surname share one value."""
        cells = []
        for start, end, role in row:
            raw = text[start:end]
            content = raw.strip()
            if not content or fold(content) in V.EMPTY_CELLS:
                continue
            start += len(raw) - len(raw.lstrip())
            end = start + len(content)
            if _NAME_CELL_RE.fullmatch(content) and len(content.split()) <= 6:
                cells.append((start, end, role, content))
            else:
                zones.append((start, end))  # « Jean Dupont (DRH) » : indice fort pour les noms de la cellule
        given = next((c[3] for c in cells if c[2] == "given"), None)
        surname = next((c[3] for c in cells if c[2] == "surname"), None)
        for start, end, role, content in cells:
            value = f"{given} {surname}" if given and surname and role in ("given", "surname") else content
            key = fold(content)
            code = self._lex.code(key) if " " not in content else None
            # Un mot courant (« Direction ») est masqué ici mais jamais propagé / a common word is never propagated.
            safe = ambiguity(code) == AMB_NONE if code is not None else key not in self._lex.words
            if not safe:
                confirmed.add(key)  # forme ambiguë : propagation prudente / ambiguous: careful propagation
            spans.append(Span(start, end, "PERSON", "PERSON", self.id, 0.9, PRIORITY_HEURISTIC, value, True,
                              propagate=safe))

    # --- décision / decision ---------------------------------------------------------------------------------

    def _decide(self, ctx: Any, runs: list[_Run], cues: _Cues, confirmed: set[str]) -> tuple[list[_Run], set[str]]:
        """Runs retenus, et formes vues comme éponymes (jamais propagées) / accepted runs, eponym forms."""
        text: str = ctx.text
        accepted: list[_Run] = []
        rejected: list[_Run] = []
        deferred: list[_Run] = []
        eponyms: set[str] = set()
        style_cache: dict[int, tuple[bool, bool]] = {}
        previous: _Run | None = None
        for run in runs:
            listed = previous is not None and _LIST_GAP_RE.fullmatch(text, previous.end, run.start) is not None
            run.addressed = run.start in cues.roles or (
                run.start in cues.greetings and _VOCATIVE_RE.match(text, run.end) is not None)
            run.labelled = run.start in cues.labels
            only = run.elements[0] if len(run.elements) == 1 else None
            if (only is not None and only.kind == K_UNKNOWN and cues.at.get(only.start) != STRONG
                    and only.end not in cues.display and not cues.strong and not run.addressed
                    and not (listed and previous is not None and previous.evidence == STRONG)):
                # Mot inconnu seul (souvent un verbe) : un nom seulement après un indice fort, ou s'il est confirmé
                # ailleurs (second passage). A lone unknown word: a name only after a strong cue, or if confirmed.
                deferred.append(run)
                continue
            run.evidence = self._evidence(text, run, cues, confirmed)
            if run.evidence == NEG:
                eponyms.update(e.key for e in run.names())  # « tour Eiffel » : « Eiffel » ne sera pas propagé
                continue
            if listed and previous is not None and run.evidence in (NONE, WEAK) and not self._marker(run):
                # Suite d'une liste : « MM. Dupont et Petit », « Jean Dupont, Rose et Paul » / list continuation.
                run.evidence = STRONG if previous.evidence == STRONG else MEDIUM
            run.score = self._score(ctx, run, style_cache)
            if run.score > 0:
                accepted.append(run)
                previous = run
                names = run.names()
                # Seule une mention sûre confirme ses formes : un mot ambigu seul n'en confirme aucune, et un lieu
                # n'est confirmé que seul après un indice fort (« M. Paris », pas « Anne de Bretagne »).
                # Only a reliable mention confirms its forms; a place only alone after a strong cue.
                if run.evidence >= MEDIUM or len(names) >= 2 or names[0].amb == AMB_NONE:
                    entity_ok = len(names) == 1 and run.evidence == STRONG
                    # Un mot-nom d'une paire n'est confirmé qu'à côté d'un prénom (« Pierre Blanc », pas « Grand
                    # Corbin ») / an ambiguous element of a pair is confirmed only next to a given name.
                    anchored = run.evidence >= MEDIUM or len(names) == 1 or any(e.given for e in names)
                    # Un mot inconnu n'est confirmé que sous un indice ou à côté d'un prénom connu : « Jean
                    # Zelensky », pas « Facture Dupont ». An unknown word needs a cue or a known given name.
                    unknown_ok = run.evidence >= MEDIUM or any(e.given for e in names)
                    confirmed.update(e.key for e in names if len(e.key) >= 3
                                     and (e.amb != AMB_ENTITY or entity_ok)
                                     and (e.amb == AMB_NONE or anchored)
                                     and (e.kind != K_UNKNOWN or unknown_ok))
            else:
                rejected.append(run)
        # Propagation interne des formes confirmées / internal propagation of confirmed forms.
        for run in (*rejected, *deferred):
            names = run.names()
            if cues.at.get(run.start) == NEG or not any(e.key in confirmed for e in names):
                continue
            run.evidence = MEDIUM
            if len(names) == 1 and names[0].safe and names[0].key not in eponyms \
                    and not self._after_determiner(text, run.start):
                # Forme sûre confirmée (« Mme Ferhati » … « Ferhati Solutions ») : masquée partout, comme le
                # moteur la propagerait ; utile quand une organisation conservée la recouvre.
                # Safe confirmed form: masked everywhere, as the engine would; matters inside a kept organisation.
                run.score = 0.8
            else:
                run.score = self._score(ctx, run, style_cache, confirmed_only=True)
            if run.score > 0:
                accepted.append(run)
        accepted.sort(key=lambda r: r.start)
        return accepted, eponyms

    @staticmethod
    def _marker(run: _Run) -> bool:
        """Mot de rôle ou de raison sociale seul (« NÉE », « Fils ») : pas la suite d'une liste de noms.

        A lone role or family-business word is not the continuation of a list of names.
        """
        names = run.names()
        return len(names) == 1 and (names[0].key in V.CONTEXTUAL or names[0].key in V.ORG_FAMILY)

    def _evidence(self, text: str, run: _Run, cues: _Cues, confirmed: set[str]) -> int:
        start = run.start
        evidence = cues.at.get(start, NONE)
        if evidence == NEG:
            # « Matricule 75012 Sophie Martin » : un prénom et un autre nom après un code postal qui n'annonce pas sa
            # commune forment une personne. A given name and another name after a postcode not followed by its town.
            names = run.names()
            if not (start in cues.postcodes and len(names) >= 2
                    and any(e.kind == K_NAME and e.given >= GIVEN_ALONE_MIN for e in names)):
                return NEG
            evidence = NONE
        if cues.strong and _Cues.inside(cues.strong, start, run.end):
            return STRONG
        if run.end in cues.display:
            return STRONG  # « Jean Dupont <jean.dupont@…> »
        if evidence == NONE and cues.signature and _Cues.inside(cues.signature, start, run.end) \
                and self._line_start(text, start):
            evidence = WEAK
        if evidence < MEDIUM and confirmed and all(e.key in confirmed for e in run.names()):
            evidence = MEDIUM
        return evidence

    def _score(self, ctx: Any, run: _Run, style_cache: dict[int, tuple[bool, bool]],
               confirmed_only: bool = False) -> float:
        names = run.names()
        evidence = run.evidence
        if not names or evidence == NEG:
            return 0.0
        text: str = ctx.text
        if evidence == STRONG:
            # « Nom : TESTIX INDUSTRIES » : un mot seul suivi de mots courants capitalisés est une raison sociale ;
            # mais pas s'ils commencent l'étiquette suivante (« Nom : Dupont Prénom : Jean »). A single word followed
            # by capitalised common words under a field label is a company name, unless they start the next label.
            if run.labelled and run.cap_right and len(names) == 1 and not names[0].given \
                    and _LABEL_AHEAD_RE.match(text, run.end) is None:
                return 0.0
            return 0.95
        lead = run.elements[0]
        if lead.kind == K_PARTICLE and lead.key in V.DETERMINERS:
            return 0.0  # « La Rose », « Le Monde » : article capitalisé / capitalised article
        if self._after_determiner(text, run.start):
            return 0.0
        initials = sum(1 for e in run.elements if e.kind == K_INITIAL)
        if evidence >= WEAK:
            return self._score_cued(text, run, names, confirmed_only)
        title_line, caps_line = self._line_style(text, run.start, style_cache)
        if len(names) + initials >= 2:
            return self._score_pair(text, run, names, initials, title_line, caps_line)
        return self._score_single(text, run, names[0], title_line, caps_line)

    def _score_cued(self, text: str, run: _Run, names: list[_Element], confirmed_only: bool) -> float:
        """Avec un indice moyen ou faible (salutation, rôle, signature) / with a medium or weak cue."""
        single = len(names) == 1
        if confirmed_only and single and (run.cap_left or run.cap_right):
            return 0.0
        known = [e for e in names if e.kind == K_NAME and (e.amb != AMB_ENTITY or confirmed_only)]
        if not known:
            # Noms inconnus : « le patient Ansgar Davids », « Bonjour Nath, », « Présents : Testarossi P », deux ou
            # trois mots capitalisés, ou un mot et une initiale, sous un indice. Unknown names: two or three
            # capitalised words, or one word and an initial, under a cue, or a role or vocative.
            plain = all(e.kind == K_UNKNOWN and not e.caps and len(e.key) >= 3 for e in names)
            initial = single and any(e.kind == K_INITIAL for e in run.elements)
            if plain and (2 <= len(names) <= 3 or initial or run.addressed):
                return 0.75
            return 0.0
        if confirmed_only and single and known[0].amb == AMB_ENTITY and self._after_locative(text, run.start, True):
            return 0.0
        if run.evidence == WEAK and single:
            # Signature : un prénom ou un nom sûr, pas « Chargé d'affaires » / a name, not a job title.
            e = known[0]
            if not ((e.given and e.amb != AMB_ENTITY) or e.solid):
                return 0.0
        return 0.8 if confirmed_only or run.evidence == WEAK else 0.85

    @staticmethod
    def _score_pair(text: str, run: _Run, names: list[_Element], initials: int, title_line: bool,
                    caps_line: bool) -> float:
        solid = [e for e in names if e.solid]
        if caps_line:
            # Ligne en capitales : un prénom sûr et un nom (sûr ou inconnu) / all-caps line: stricter.
            others = [e for e in names if e not in solid[:1] and (e.solid or e.kind == K_UNKNOWN)]
            return 0.85 if solid and solid[0].given and others else 0.0
        if solid:
            return 0.9
        if initials and len(names) == 1:
            e = names[0]
            # Après un mot inconnu, une lettre sans point suivie d'un numéro est une lettre de série (« Bodacc A
            # n° 2026… »), pas une initiale (« MBAPPA K », « Testarossi P, »). After an unknown word, a dotless letter
            # followed by a number is a series letter, not an initial.
            initial = any(i.kind == K_INITIAL and (i.start < e.start or text.startswith(".", i.end)
                                                   or _SERIES_AFTER_RE.match(text, i.end) is None)
                          for i in run.elements)
            ok = (e.kind == K_NAME and e.surname and e.amb != AMB_ENTITY) or (
                e.kind == K_UNKNOWN and len(e.key) >= 3 and initial)
            return 0.8 if ok else 0.0
        givens = [e for e in names if e.given and not e.caps and (
            e.amb in (AMB_WORD, AMB_STRONG) or (e.amb == AMB_ENTITY and e.given >= _ENTITY_GIVEN_MIN))]
        if givens and not (title_line or run.cap_left or run.cap_right):
            others = [e for e in names if e is not givens[0]
                      and ((e.surname and e.amb != AMB_ENTITY) or e.kind == K_UNKNOWN)]
            if others:
                return 0.8  # « Pierre Blanc », « Rose Petit », « Noël Lopes »
        caps = [e for e in names if e.caps and e.amb != AMB_ENTITY and (e.kind == K_UNKNOWN or e.surname)]
        lower = [e for e in names if not e.caps and e.given and e.amb != AMB_ENTITY]
        if caps and lower:
            return 0.85  # « DUPONT Jean », « MARTIN Pierre »
        # « VALLÉE Nath » : nom fréquent en capitales, prénom inconnu / frequent caps surname, unknown given name.
        caps_known = any(e.caps and e.kind == K_NAME and e.surname >= SURNAME_ALONE_MIN for e in names)
        lower_unknown = any(not e.caps and e.kind == K_UNKNOWN and len(e.key) >= 3 for e in names)
        return 0.8 if caps_known and lower_unknown and not title_line else 0.0

    def _score_single(self, text: str, run: _Run, e: _Element, title_line: bool, caps_line: bool) -> float:
        if e.kind != K_NAME or e.amb == AMB_ENTITY or len(e.key) < 3:
            return 0.0
        if e.caps and (caps_line or title_line or e.amb != AMB_NONE or len(e.key) < 4
                       or max(e.given, e.surname) < CAPS_ALONE_MIN):
            return 0.0  # en capitales : sigle ou titre, sauf nom sûr et fréquent en prose (« Selon DUPONT »)
        if (run.cap_left or run.cap_right) and e.amb != AMB_NONE:
            # « Mont Blanc », « Radio France » : mot ambigu. Un nom sûr reste masqué (« Dossier Dupont »,
            # « Affaire Delacroix ») ; les lieux (« avenue », « musée ») passent par les éponymes.
            # Ambiguous word next to a capitalised word; a safe name stays masked, places go through eponyms.
            return 0.0
        if not (e.given >= GIVEN_ALONE_MIN or e.surname >= SURNAME_ALONE_MIN):
            return 0.0
        if (title_line or caps_line) and e.amb != AMB_NONE:
            return 0.0
        if _NUMBER_AFTER_RE.match(text, e.end) is not None and not (
                e.amb == AMB_NONE and _YEAR_AFTER_RE.match(text, e.end) is not None):
            return 0.0  # « Louis XIV », « Ariane 5 » ; mais « Rapport Lefèvre 2024 » reste un nom / but a year
        commune = e.key.replace("-", " ") in self._lex.communes  # « Doignies », « Levallois-Perret »
        if self._after_locative(text, e.start) and (e.amb != AMB_NONE or commune):
            return 0.0  # « à Albert », « en Lorraine »
        if commune and not e.given and e.surname < COMMUNE_SURNAME_MIN:
            return 0.0  # nom rare homonyme d'une commune (« Doignies ») : un indice est exigé / needs a cue
        if e.amb == AMB_NONE:
            return 0.8
        # Mot ambigu seul : seul un prénom passe sans indice (« j'ai vu Pierre »), jamais un nom-mot (« de Coupe »,
        # « Petit ») ; en tête de phrase, seul un prénom très fréquent. Ambiguous word alone: given names only.
        if e.given < GIVEN_ALONE_MIN:
            return 0.0
        if self._sentence_start(text, e.start) and (e.amb == AMB_STRONG or e.given < GIVEN_START_MIN):
            return 0.0
        if e.amb == AMB_STRONG:
            # « Marine nationale », « Rose des vents » : suivi d'un nom ou d'un adjectif, c'est le mot courant ;
            # suivi d'un verbe (absent du lexique de mots) ou d'un mot-outil, c'est une personne.
            # Followed by a noun or adjective it is the common word; by a verb or function word, a person.
            m = _NEXT_WORD_RE.match(text, e.end)
            if m is not None:
                nxt = fold(m.group(1))
                if nxt in self._lex.words and nxt not in V.FUNCTION and nxt not in _AUXILIARIES:
                    return 0.0
        return 0.7

    # --- contexte local / local context ----------------------------------------------------------------------

    @staticmethod
    def _sentence_start(text: str, pos: int) -> bool:
        """Début de phrase, de ligne, de cellule ou de colonne (deux espaces) / sentence, line or column start."""
        i = pos - 1
        while i >= 0 and text[i] in _SKIP_BACK and pos - i < 12:
            i -= 1
        return i < 0 or text[i] in _SENTENCE_END or text[i + 1:pos].startswith("  ")

    @staticmethod
    def _line_start(text: str, pos: int) -> bool:
        line_start = text.rfind("\n", max(0, pos - 32), pos) + 1
        return (line_start > 0 or pos <= 32) and not text[line_start:pos].strip(" \t*_->#|•")

    @staticmethod
    def _previous_word(text: str, pos: int) -> str:
        """Mot qui précède en minuscules, élision comprise (« l' ») / previous word, elision included."""
        if pos >= 2 and text[pos - 1] == "'" and text[pos - 2].isalpha() and (pos < 3 or not text[pos - 3].isalpha()):
            return text[pos - 2:pos].lower()
        j = pos - 1
        while j >= 0 and text[j] in " \t" and pos - j < 4:
            j -= 1
        k = j
        while k >= 0 and text[k].isalpha() and j - k < 20:
            k -= 1
        return text[k + 1:j + 1].lower()

    def _after_determiner(self, text: str, pos: int) -> bool:
        word = self._previous_word(text, pos)
        return bool(word) and fold(word) in V.DETERMINERS

    def _after_locative(self, text: str, pos: int, verbs: bool = False) -> bool:
        word = self._previous_word(text, pos)
        return word in V.LOCATIVES or (verbs and word in V.PLACE_VERBS)

    def _line_style(self, text: str, pos: int, cache: dict[int, tuple[bool, bool]]) -> tuple[bool, bool]:
        """(ligne en Casse De Titre, ligne en capitales) / (Title Case line, all-caps line).

        Un titre capitalise des mots courants (« Rapport Annuel De La Direction ») ; une liste de noms, non.
        A heading capitalises common words; a list of names does not.
        """
        line_start, line_end, whole = line_bounds(text, pos)
        style = cache.get(line_start)
        if style is None and not whole:
            style = (False, False)  # ligne très longue : de la prose, pas un titre / very long line: prose
            cache[line_start] = style
        if style is None:
            words = _WORD4_RE.findall(text, line_start, line_end)
            capitals = [w for w in words if w[0].isupper()]
            common = sum(1 for w in capitals if fold(w) in self._lex.words or fold(w) in V.FUNCTION)
            line = text[line_start:line_end]
            # Un titre n'a pas de fin de phrase en son milieu / a heading has no inner sentence break.
            heading = ". " not in line.strip()
            style = (heading and len(words) >= 3 and len(capitals) >= 0.75 * len(words) and common >= 2,
                     len(words) >= 2 and line.isupper())
            cache[line_start] = style
        return style

    # --- zone et forme canonique / span and canonical form --------------------------------------------------

    def _span(self, run: _Run, text: str, cues: _Cues, eponyms: set[str]) -> Span:
        elements = run.elements
        if elements[0].kind == K_PARTICLE and run.evidence < MEDIUM:
            elements = elements[1:]  # article en tête (« Le Monde ») / leading article
        while elements and elements[-1].kind == K_PARTICLE:
            elements = elements[:-1]
        start = elements[0].start
        if start in cues.particle_from and not elements[0].given:
            start = cues.particle_from[start]  # « M. de Villepin » : la particule fait partie du nom
        end = elements[-1].end
        if end < len(text) and text[end] == "." and elements[-1].kind == K_INITIAL:
            end += 1  # « Jean D. »
        value, given, surname = self._canonical(elements, text)
        names = [e for e in elements if e.kind in (K_NAME, K_UNKNOWN)]
        safe_single = len(names) == 1 and (names[0].kind == K_UNKNOWN or names[0].amb == AMB_NONE) \
            and names[0].key not in eponyms
        # Nom seul propagé s'il est sûr ; un nom inconnu seulement à côté d'un prénom fréquent (« Jean Zelensky »,
        # pas « Breizh Izel »). Surname form propagated when safe; an unknown one only next to a frequent given name.
        forms: tuple[str, ...] = ()
        known_surname = surname.kind == K_NAME or (given.kind == K_NAME and given.given >= GIVEN_ALONE_MIN
                                                   and given.amb != AMB_ENTITY)
        if len(names) >= 2 and surname.amb == AMB_NONE and len(surname.key) >= 3 and surname.key not in eponyms \
                and known_surname:
            form = self._last_name(surname, text)
            forms = (form.title(),) if form.isupper() else (form,)
        return Span(start, end, "PERSON", "PERSON", self.id, run.score, PRIORITY_HEURISTIC, value, True,
                    forms, len(names) >= 2 or safe_single)

    @staticmethod
    def _canonical(elements: list[_Element], text: str) -> tuple[str, _Element, _Element]:
        """« Prénom Nom » sans particules ni prénoms intermédiaires, pour la coréférence de `Scope`.

        "Given Surname" without particles or middle names, for `Scope` coreference.
        """
        parts = [e for e in elements if e.kind in (K_NAME, K_UNKNOWN, K_INITIAL)]
        if len(parts) == 1:
            only = parts[0]
            return FrenchNameDetector._last_name(only, text), only, only
        caps = [e for e in parts if e.caps and e.kind != K_INITIAL]
        mixed = [e for e in parts if not e.caps]
        if caps and mixed:
            given, surname = mixed[0], caps[-1]
        elif len(parts) == 2 and parts[1].kind == K_NAME and \
                parts[1].given - parts[1].surname > parts[0].given - parts[0].surname:
            given, surname = parts[1], parts[0]  # « Blanchard Olivier », « Tirole Jean » : ordre Nom Prénom
        else:
            given, surname = parts[0], parts[-1]
        given_text = _unwrap(text[given.start:given.end]) + ("." if given.kind == K_INITIAL else "")
        surname_text = FrenchNameDetector._last_name(surname, text)
        return f"{given_text} {surname_text}", given, surname

    @staticmethod
    def _last_name(element: _Element, text: str) -> str:
        """Dernier mot d'un élément ; un nom à particule fusionné garde sa particule (« Le Verger »).

        Last word of an element; a merged particle surname keeps its particle ("Le Verger"), so that it is propagated
        whole. Les éléments inconnus à espace viennent tous de `_compound_tokens` / unknown spaced elements all come
        from `_compound_tokens`.
        """
        name = _unwrap(text[element.start:element.end])
        return name if element.kind == K_UNKNOWN and " " in element.key else name.split()[-1]


__all__ = ["FrenchNameDetector"]
