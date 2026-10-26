"""Accélérateur Rust optionnel (`gdprguardian-core`) / optional Rust accelerator.

Le moteur Python reste la référence : un recognizer n'est confié à Rust que si son motif, transmis sous la forme
de l'arbre de `re` lui-même, se compile avec la sémantique exacte de `re` et si son validateur existe en natif ;
sinon Python le traite. `GDPRGUARDIAN_PURE_PYTHON=1` désactive Rust. The Python engine stays the reference: a
recognizer goes to Rust only if its pattern, sent as `re`'s own tree, compiles with `re`'s exact semantics and its
validator is native; otherwise Python handles it.
Rust reçoit de Python ses tables (classes de caractères, transcodage, mots outils) : une seule source de
vérité. Rust gets its tables from Python (character classes, translation, stop words): one source of truth.
Un noyau d'une autre version (contrat différent) est écarté à l'import, avec un avertissement : la référence
Python sert, comme sans noyau. A core of another version (other contract) is set aside at import, with a
warning: the Python reference serves, as without a core.
"""

from __future__ import annotations

import os
import re
import warnings
from collections.abc import Callable, Mapping, Sequence
from functools import cache, partial
from typing import Any

from . import _text
from .packs import PatternRecognizer

# Contrat avec le noyau (`CONTRACT` de rust/src/lib.rs) : le même nombre des deux côtés, augmenté à chaque
# changement de nom, de signature ou de sens d'une liaison. Contract with the core: the same number on both sides,
# bumped at every change of a binding's name, signature or semantics.
CONTRACT = 5

try:
    if os.environ.get("GDPRGUARDIAN_PURE_PYTHON") == "1":
        raise ImportError
    import gdprguardian_core as _core
except ImportError:
    _core = None

if _core is not None and getattr(_core, "CONTRACT", None) != CONTRACT:
    # Liaisons d'une autre version (noms, signatures, sens) : aucune n'est appelée / no binding is ever called.
    warnings.warn(
        f"gdprguardian_core {getattr(_core, '__version__', '?')} ignoré (contrat {getattr(_core, 'CONTRACT', None)}, "
        f"attendu {CONTRACT}) : moteur Python seul ; réinstaller le noyau du même arbre avec `pip install "
        f"--force-reinstall <wheel>` / ignored (contract mismatch): pure Python engine; reinstall the core built "
        f"from the same tree with `pip install --force-reinstall <wheel>`", RuntimeWarning, stacklevel=2)
    _core = None


def available() -> bool:
    return _core is not None


def _provides(name: str) -> bool:
    """Le noyau installé fournit-il cette classe ? (noyau plus ancien que le paquet) / does the core have it?"""
    return _core is not None and hasattr(_core, name)


@cache
def unicode_tables() -> Any:
    """Table Unicode unique du noyau, construite une fois par processus (~15 ms) ; None sans noyau.

    The core's single Unicode table, built once per process; None without the core. Classes de `str` et de
    `re`, casse complète, repliement de `_text.fold`, données de `re.IGNORECASE` : toutes calculées ici, par CET
    interpréteur (`_text.plane_classes`, en code C). Le plan de base tout de suite ; chaque autre plan au premier
    de ses caractères que le noyau rencontre, une fois. Every class, case mapping, fold and `re.IGNORECASE`
    datum is computed here, by THIS interpreter; the base plane now, any other plane at its first character.
    """
    if not _provides("UnicodeTables"):
        return None
    from .heuristics._lexicon import UPPER  # classe des capitales des heuristiques / the heuristics' capitals

    loader = partial(_text.plane_classes, capital=UPPER)
    return _core.UnicodeTables(
        bmp=loader(0), loader=loader, fold=sorted(_text.FOLD_TABLE.items()), ignorecase=_text.ignorecase_data(),
        # Plans hors BMP où `\w`, `\d`, `\s` ont des membres ; tous si la version d'Unicode n'est pas vérifiée.
        # Astral planes holding `\w`, `\d`, `\s` members; all of them if the Unicode version is not verified.
        perl_planes=[1, 2, 3] if _text.verified_planes() else list(range(1, 17)))


@cache
def preparer() -> Any:
    """Préparation du texte en Rust, à partir des tables de `_text` / text preparation from `_text`'s tables."""
    if not _provides("Preparer"):
        return None
    # Table dense en UTF-32 : les demi-codets (U+D800–U+DFFF) y passent tels quels ; le repliement vient de la
    # table Unicode partagée. Dense table in UTF-32: surrogates go through unchanged; folding comes from the
    # shared Unicode table.
    return _core.Preparer(unicode_tables(), _text._NORMALIZE_BMP.encode("utf-32-le", "surrogatepass"),
                          list(_text._ASTRAL_NORMALIZE.items()))


def language_detector(word_languages: Mapping[str, Sequence[str]], sample: int) -> Any:
    """Détecteur de langue en Rust, à partir des mots outils de `locale` / from `locale`'s stop words."""
    return _core.LanguageDetector(list(word_languages.items()), sample) if _provides("LanguageDetector") else None


# --- Syntaxe des motifs pour le compilateur natif / pattern syntax for the native compiler ---------------------

_CATEGORIES = {"CATEGORY_WORD": "word", "CATEGORY_NOT_WORD": "not_word", "CATEGORY_DIGIT": "digit",
               "CATEGORY_NOT_DIGIT": "not_digit", "CATEGORY_SPACE": "space", "CATEGORY_NOT_SPACE": "not_space"}
_ESCAPES = {"word": r"\w", "not_word": r"\W", "digit": r"\d", "not_digit": r"\D", "space": r"\s",
            "not_space": r"\S"}
# Assertions de `re`, sans puis avec MULTILINE / `re`'s assertions, without then with MULTILINE.
_AT = {"AT_BEGINNING": "start", "AT_BEGINNING_STRING": "start", "AT_END": "end", "AT_END_STRING": "end_text",
       "AT_BOUNDARY": "boundary", "AT_NON_BOUNDARY": "not_boundary"}
_AT_MULTILINE = {**_AT, "AT_BEGINNING": "start_line", "AT_END": "end_line"}
# Drapeaux en entiers : les opérations sur `re.RegexFlag` coûtent cher / flags as ints: enum operations are slow.
_IGNORECASE, _MULTILINE, _DOTALL, _ASCII_OR_LOCALE = (int(re.IGNORECASE), int(re.MULTILINE), int(re.DOTALL),
                                                      int(re.ASCII | re.LOCALE))
# Ensembles insensibles à la casse des packs intégrés, résolus une fois (jamais ceux des règles personnalisées).
# Case-insensitive sets of the built-in packs, resolved once (never those of custom rules).
_CASED_SETS: dict[str, list[int]] = {}


class _Unsupported(Exception):
    """Construction que le compilateur natif ne reçoit pas / construct the native compiler does not take."""


@cache
def _ignorecase_candidates() -> str:
    return "".join(map(chr, _text.ignorecase_data()["candidates"]))


def _cased_matches(negate: bool, items: list[tuple], cache: dict[str, list[int]]) -> list[int]:
    """Candidats de `re.IGNORECASE` qu'accepte cet ensemble, selon `re` lui-même (version de l'interpréteur).

    The `re.IGNORECASE` candidates this set accepts, according to `re` itself (this interpreter's version).
    `re` ne reçoit de chaque intervalle que les candidats de sa partie BMP (un autre caractère ne s'apparie qu'à
    lui-même), au plus ~2 900 au lieu de 65 536 points par intervalle. Au-delà de U+FFFF, `re` teste l'intervalle
    entier en RANGE_UNI_IGNORE (minuscule, ou majuscule simple de la minuscule, entre les bornes) : cette règle
    est appliquée ici aux candidats. `re` only gets the candidates of each range's BMP part (any other character
    only matches itself), at most ~2,900 instead of 65,536 points per range. Past U+FFFF, `re` tests the whole range
    with RANGE_UNI_IGNORE (lowercase, or simple uppercase of the lowercase, within the bounds): that rule is applied
    here to the candidates.
    """
    import bisect

    def escape(cp: int) -> str:
        return f"\\U{cp:08x}"

    candidates: list[int] = _text.ignorecase_data()["candidates"]
    literals: set[int] = set()
    categories: list[str] = []
    astral: list[tuple[int, int]] = []
    for item in items:
        if item[0] == "lit":
            literals.add(item[1])
        elif item[0] == "range":
            low, high = item[1], item[2]
            literals.update(candidates[bisect.bisect_left(candidates, low):
                                       bisect.bisect_right(candidates, min(high, 0xFFFF))])
            if high > 0xFFFF:
                astral.append((low, high))
        else:
            categories.append(_ESCAPES[item[1]])
    members = "".join([*map(escape, sorted(literals)), *categories,
                       *(f"{escape(max(low, 0x10000))}-{escape(high)}" for low, high in astral)])
    if not members:
        return list(candidates) if negate else []  # aucun candidat dans l'ensemble / no candidate in the set
    key = "[" + "^" * negate + members + "]"
    if key not in cache:
        import _sre
        from re import _compiler  # sans le cache de `re` : rien n'y reste / bypasses `re`'s cache: nothing kept

        found = set(map(ord, _compiler.compile(f"[{members}]", re.IGNORECASE).findall(_ignorecase_candidates())))
        # Intervalle purement astral : transmis tel quel, `re` le résout lui-même. Seul celui qui franchit U+FFFF
        # garde ici sa règle pour la partie BMP. A purely astral range is passed as is and `re` resolves it; only
        # one crossing U+FFFF keeps its rule here, for the BMP part.
        crossing = [(low, high) for low, high in astral if low <= 0xFFFF]
        for cp in candidates if crossing else ():
            lower = _sre.unicode_tolower(cp)
            upper = ord(chr(lower).upper()[0])  # majuscule simple de `re` / `re`'s simple uppercase
            if any(low <= lower <= high or low <= upper <= high for low, high in crossing):
                found.add(cp)
        cache[key] = sorted(set(candidates) - found) if negate else sorted(found)
    return cache[key]


def _nodes(items: Any, flags: int, cache: dict[str, list[int]]) -> list[tuple]:
    """Noeuds de `re` en tuples simples, drapeaux résolus / `re` nodes as plain tuples, flags resolved."""
    import _sre
    from re import _compiler
    from re._constants import MAXREPEAT

    if flags & _ASCII_OR_LOCALE:
        raise _Unsupported("re.ASCII")
    ignorecase = bool(flags & _IGNORECASE)
    out: list[tuple] = []
    for op, av in items:
        name = str(op)
        if name in ("LITERAL", "NOT_LITERAL"):
            negate = name == "NOT_LITERAL"
            if ignorecase and _sre.unicode_iscased(av):
                out.append(("set", negate, [("lit", av)], _cased_matches(negate, [("lit", av)], cache)))
            else:
                out.append(("set", True, [("lit", av)], None) if negate else ("lit", av))
        elif name == "IN":
            negate = bool(av) and str(av[0][0]) == "NEGATE"
            members: list[tuple] = []
            for kind, value in av[negate:]:
                if str(kind) == "LITERAL":
                    members.append(("lit", value))
                elif str(kind) == "RANGE":
                    members.append(("range", value[0], value[1]))
                elif str(kind) == "CATEGORY" and str(value) in _CATEGORIES:
                    members.append(("cat", _CATEGORIES[str(value)]))
                else:
                    raise _Unsupported(str(kind))
            out.append(("set", negate, members, _cased_matches(negate, members, cache) if ignorecase else None))
        elif name == "ANY":
            out.append(("any", bool(flags & _DOTALL)))
        elif name in ("MAX_REPEAT", "MIN_REPEAT"):
            low, high, item = av
            out.append(("repeat", low, -1 if high == MAXREPEAT else high, name == "MAX_REPEAT",
                        _nodes(item, flags, cache)))
        elif name == "SUBPATTERN":
            group, add, delete, item = av
            inner = int(_compiler._combine_flags(flags, int(add), int(delete)))
            out.append(("group", group or 0, _nodes(item, inner, cache)))
        elif name == "BRANCH":
            out.append(("branch", [_nodes(branch, flags, cache) for branch in av[1]]))
        elif name == "AT":
            out.append(("at", (_AT_MULTILINE if flags & _MULTILINE else _AT)[str(av)]))
        elif name in ("ASSERT", "ASSERT_NOT"):
            direction, item = av
            out.append(("look", direction > 0, name == "ASSERT_NOT", _nodes(item, flags, cache)))
        elif name == "FAILURE":
            out.append(("set", False, [], None))
        else:
            raise _Unsupported(name)  # références arrière, groupes atomiques… / backreferences, atomic groups…
    return out


def syntax(regex: re.Pattern[str], *, shared: bool = False) -> tuple:
    """Arbre de syntaxe de `re` lui-même pour le compilateur natif : (groupes, noms, noeuds) ou (raison,).

    `re`'s own syntax tree for the native compiler: (groups, names, nodes), or (reason,). Le noyau compile ce
    que `re` exécute : mêmes groupes, mêmes réécritures d'analyse, drapeaux résolus ici, et `re.IGNORECASE` décidé
    par `re` lui-même sur les seuls caractères où il diffère de la casse exacte. The core compiles what `re`
    executes: same groups, same parse-time rewrites, flags resolved here, and `re.IGNORECASE` decided by `re`
    itself on the only characters where it differs from exact case. `shared` : motif intégré, ses ensembles
    sont gardés pour les suivants / built-in pattern, its sets are kept for the next ones.
    """
    try:
        from re import _parser  # arbre de syntaxe de `re` / `re`'s syntax tree

        tree = _parser.parse(regex.pattern, regex.flags)
        names = sorted((name, index) for name, index in tree.state.groupdict.items())
        return tree.state.groups - 1, names, _nodes(tree, int(tree.state.flags), _CASED_SETS if shared else {})
    except _Unsupported as error:
        return (f"construction de `re` non prise en charge / unsupported `re` construct: {error}",)
    except (ImportError, AttributeError, KeyError, TypeError, ValueError) as error:  # API interne changée
        return (f"arbre de `re` illisible / unreadable `re` tree: {type(error).__name__}",)


@cache
def _native_validators() -> frozenset[str]:
    return frozenset(_core.native_validators()) if _core is not None else frozenset()


def _spec(rec: PatternRecognizer) -> dict[str, Any]:
    from .custom import CUSTOM_PACK  # import différé : `custom` dépend des packs / deferred import

    prefilter = list(rec.prefilter) if isinstance(rec.prefilter, tuple) else rec.prefilter
    # Validateur Python seulement : le motif reste à Python, inutile de l'analyser / Python-only validator.
    native = rec.validator_name is None or rec.validator_name in _native_validators()
    shared = rec.pack != CUSTOM_PACK
    return {
        "syntax": syntax(rec.regex, shared=shared) if native else None,
        # Motif des packs : compilé une fois par processus, partagé entre les analyseurs de chaque ensemble de
        # packs (« FR », « FR,DE »…) ; jamais une règle d'organisation. Pack pattern: compiled once per process and
        # shared by the scanners of every pack set; never an organisation's rule.
        "key": f"{rec.regex.flags}:{rec.regex.pattern}" if shared and native else None,
        "group": rec.group,
        "validator": rec.validator_name,
        "tier": rec.tier,
        "contexts": list(rec.contexts),
        "vetoes": list(rec.vetoes),
        "before": rec.before,
        "after": rec.after,
        "boundary": rec.boundary,
        "prefilter": prefilter,
        "score": rec.score,
        "policy": rec.policy,
        "fallback": rec.fallback,
    }


class NativeScanner:
    """Enveloppe du `Scanner` Rust / wraps the Rust scanner."""

    __slots__ = ("_packs", "_scanner", "errors", "flags", "recognizers", "supported")

    def __init__(self, recognizers: Sequence[PatternRecognizer], keyword_groups: Mapping[str, Sequence[str]],
                 fold: Callable[[str], str], untrusted: bool = False) -> None:
        groups = [(name, [fold(w).strip() for w in words]) for name, words in keyword_groups.items()]
        self.recognizers = list(recognizers)
        self._packs = [r.pack for r in self.recognizers]
        specs = [_spec(r) for r in self.recognizers]
        self._scanner = _core.Scanner(specs, groups, unicode_tables(), untrusted=untrusted)
        # Par recognizer : pris en charge ? sinon, pourquoi / per recognizer: supported? otherwise, why.
        self.flags: list[bool] = list(self._scanner.supported)
        self.errors: list[str | None] = list(self._scanner.errors)
        self.supported = frozenset(
            (r.pack, r.id) for r, ok in zip(self.recognizers, self.flags, strict=True) if ok
        )

    def keywords(self, folded: str) -> Any:
        return self._scanner.keywords(folded)

    def scan(self, hits: Any, text: str, folded: str, active_packs: frozenset[str], strict: bool,
             company_mode: str, facility_mask: bool, ei_groups: Sequence[str],
             segments: Sequence[tuple[int, int]] | None = None,
             forced: Sequence[frozenset[str]] | None = None,
             zones: Sequence[tuple[int, int, frozenset[str]]] = (), *,
             person_groups: Sequence[str] = (), entity_groups: Sequence[str] = ()) -> list[tuple]:
        active = list(map(active_packs.__contains__, self._packs))
        return self._scanner.scan(
            hits, text, folded, active, strict, company_mode, facility_mask, list(ei_groups),
            list(segments) if segments is not None else None,
            [sorted(f) for f in forced] if forced is not None else None,
            [(start, end, sorted(groups)) for start, end, groups in zones],
            person_groups=list(person_groups), entity_groups=list(entity_groups),
        )


def build(recognizers: Sequence[PatternRecognizer], keyword_groups: Mapping[str, Sequence[str]],
          fold: Callable[[str], str], *, untrusted: bool = False) -> NativeScanner | None:
    """Analyseur natif, ou None sans noyau. `untrusted` : règles reçues d'une requête, compilées sur un seul fil
    sous un budget mémoire commun (au-delà : motif refusé, avec sa raison). Native scanner, or None without the
    core. `untrusted`: rules received with a request, compiled on one thread under a shared memory budget (beyond
    it: pattern refused, with its reason).
    """
    return NativeScanner(recognizers, keyword_groups, fold, untrusted) if _core is not None else None


# --- Détecteurs natifs / native detectors -------------------------------------------------------------------------

# Points de code de plans entiers (tests) / code points of whole planes (tests).
code_points = _text.code_points


def core() -> Any | None:
    """Module Rust `gdprguardian_core`, ou None (absent, ou `GDPRGUARDIAN_PURE_PYTHON=1`) / the Rust module, or None."""
    return _core


def unicode_table() -> Any:
    """Table Unicode des détecteurs Rust : la table unique du noyau / the native detectors' table: the single one."""
    return unicode_tables()


# --- Détecteur de noms natif / native name detector ---------------------------------------------------------------

def name_detector(data: Callable[[], Mapping[str, Any]]) -> Any | None:
    """Détecteur de noms natif construit avec `data()`, None si le noyau ne le propose pas.

    Native name detector built from `data()` (only called when needed), None when the core lacks it.
    Un noyau d'une autre version (signature ou contrat différents) est écarté : la référence Python reste
    utilisée, comme sans noyau. A core from another version (other signature or contract) is set aside: the
    Python reference keeps working, as without a core.
    """
    if _core is None or not hasattr(_core, "NameDetector"):
        return None
    arguments = data()
    try:
        return _core.NameDetector(**arguments)
    except (TypeError, ValueError):
        return None


# --- Finalisation native : résolution, propagation, rendu, portée / native finalisation -----------------

def text_rules(honorifics: Sequence[str], particles: Sequence[str]) -> Any:
    """Règles de texte du noyau : table Unicode partagée (classes, casse, repliement), civilités et particules de
    tête d'un nom de famille ; ou None.

    The core's text rules: the shared Unicode table (classes, case, folding), honorifics and leading surname
    particles; or None. Aucun appel à Python pendant le traitement d'un document / no Python call while a
    document is processed.
    """
    if _core is None:
        return None
    return _core.TextRules(unicode_tables(), sorted(honorifics), sorted(particles))


def new_scope(rules: Any) -> Any:
    """Portée native : la clé est tirée et effacée dans Rust / native scope: key drawn and wiped in Rust."""
    return _core.Scope(rules)


def finalizer(rules: Any, span_type: type, **settings: Any) -> Any:
    """Finaliseur natif d'un anonymiseur (résolution, propagation, rendu) / an anonymizer's native finalizer."""
    return _core.Finalizer(rules, span_type, **settings)


# --- Moteur fusionné : deux appels Rust par document (détection, finalisation) / fused engine: two Rust calls -----

def provides_engine() -> bool:
    """Le noyau installé a-t-il le moteur fusionné ? / does the installed core have the fused engine?"""
    return _provides("Engine")


def engine(**plan: Any) -> Any | None:
    """Moteur fusionné d'un anonymiseur, composé des composants natifs ci-dessus, ou None (noyau sans moteur, ou
    plan refusé par un noyau d'une autre version : le chemin par étapes sert, mêmes résultats).

    An anonymizer's fused engine, composed of the native components above, or None (core without the engine, or
    a plan refused by a core of another version: the staged path serves, same results).
    """
    if not _provides("Engine"):
        return None
    try:
        return _core.Engine(**plan)
    except (TypeError, ValueError):
        return None
