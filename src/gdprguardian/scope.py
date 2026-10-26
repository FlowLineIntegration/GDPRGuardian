"""Portée de cohérence irréversible / irreversible consistency scope.

Une clé aléatoire de 256 bits est tirée par portée (un document, ou un lot de documents).
Seules des empreintes BLAKE2b à clé sont conservées : aucun nom, aucune valeur d'origine.
À la fermeture, la clé est effacée : personne, nous compris, ne peut relier une balise à une valeur.
Avec le noyau Rust, la clé est tirée par le système, ne passe jamais par Python et son effacement est réel
(zeroize) ; numérotation et coréférence sont identiques à cette implémentation de référence.

A random 256-bit key is drawn per scope (one document or one batch). Only keyed BLAKE2b digests
are kept: no name, no original value. On close the key is wiped: nobody, including us, can link
a placeholder back to a value. With the Rust core, the key is drawn by the OS, never goes through
Python and is truly wiped (zeroize); numbering and coreference match this reference implementation.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from functools import cache
from typing import Any

from . import _native
from ._text import fold
from .heuristics._vocab import SURNAME_PARTICLES
from .labels import LABELS

# Balise émise : [LIBELLE_N] / emitted placeholder.
PLACEHOLDER_RE = re.compile(r"\[([A-Z][A-Z0-9_]*[A-Z0-9])_([1-9][0-9]{0,6})\]")

_NAME_TOKEN_RE = re.compile(r"[^\W\d_]+(?:[\-'][^\W\d_]+)*\.?")
HONORIFICS = frozenset({
    "m", "mr", "mm", "mme", "mmes", "mlle", "mlles", "me", "dr", "pr", "mgr", "monsieur", "madame",
    "mademoiselle", "maitre", "docteur", "professeur", "herr", "frau", "sr", "sra", "srta", "don", "dona",
    "sig", "sigra", "dott", "mrs", "ms", "miss", "sir", "prof",
})


def split_person_name(text: str) -> tuple[str | None, str] | None:
    """(prénom ou None, nom) ; le nom est en capitales s'il y en a / (given or None, surname).

    Une particule en tête n'est pas un prénom : « Le Verger » est le nom seul, comme « Verger » / a leading particle is
    not a given name: "Le Verger" is the surname alone, like "Verger".
    """
    tokens = [t.rstrip(".") for t in _NAME_TOKEN_RE.findall(text)]
    tokens = [t for t in tokens if t]
    while tokens and fold(tokens[0]) in HONORIFICS:
        tokens.pop(0)
    while len(tokens) > 1 and fold(tokens[0]) in SURNAME_PARTICLES:
        tokens.pop(0)
    if not tokens:
        return None
    if len(tokens) == 1:
        return None, tokens[0]
    upper = [t for t in tokens if len(t) > 1 and t.isupper()]
    if upper and len(upper) < len(tokens):
        given = [t for t in tokens if t not in upper]
        return given[0], " ".join(upper)
    return tokens[0], tokens[-1]


@cache
def native_rules() -> Any:
    """Règles de texte du noyau Rust, construites une fois par processus, ou None sans noyau.

    The Rust core's text rules, built once per process, or None without the core. Toutes les données
    viennent de Python : table Unicode partagée (sémantique de `str`, repli `FOLD_TABLE`), civilités / all data
    comes from Python: the shared Unicode table (`str` semantics, `FOLD_TABLE` folding), honorifics.
    """
    return _native.text_rules(HONORIFICS, SURNAME_PARTICLES) if _native.available() else None


class _Cluster:
    __slots__ = ("given", "initial", "surname")

    def __init__(self, surname: bytes, given: bytes | None, initial: bytes | None) -> None:
        self.surname = surname
        self.given = given
        self.initial = initial


class Scope:
    """Numérotation cohérente par type, clé éphémère, sans table de correspondance.

    Consistent per-type numbering, ephemeral key, no mapping table. `native=False` force l'implémentation
    Python de référence / forces the reference Python implementation.
    """

    __slots__ = ("_by_given", "_by_surname", "_clusters", "_counters", "_hasher", "_indices", "_key",
                 "_native_scope", "_reserved", "label_language", "neutral")

    def __init__(self, label_language: str = "fr", neutral: bool = False, native: bool = True) -> None:
        self.label_language = label_language
        self.neutral = neutral
        rules = native_rules() if native else None
        # Portée Rust : clé, empreintes et grappes vivent hors de Python / Rust scope: key and digests outside Python.
        self._native_scope: Any = _native.new_scope(rules) if rules is not None else None
        if self._native_scope is not None:
            return
        self._key = bytearray(secrets.token_bytes(32))
        # Modèle déjà clé, copié à chaque empreinte : plus rapide, sans copie de la clé à chaque appel.
        # Pre-keyed template copied per digest: faster, no per-call copy of the key.
        self._hasher: Any = hashlib.blake2b(key=bytes(self._key), digest_size=16)
        self._indices: dict[bytes, int] = {}
        self._counters: dict[str, int] = {}
        self._reserved: dict[str, set[int]] = {}
        self._clusters: list[_Cluster] = []
        self._by_surname: dict[bytes, list[int]] = {}
        self._by_given: dict[bytes, list[int]] = {}

    def __enter__(self) -> Scope:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @property
    def native(self) -> bool:
        """La portée est-elle tenue par le noyau Rust ? / is the scope held by the Rust core?"""
        return self._native_scope is not None

    @property
    def closed(self) -> bool:
        if self._native_scope is not None:
            return self._native_scope.closed
        return not self._key

    def close(self) -> None:
        """Efface la clé et les empreintes / wipes the key and digests (best effort in CPython, real in Rust)."""
        if self._native_scope is not None:
            self._native_scope.close()
            return
        for i in range(len(self._key)):
            self._key[i] = 0
        self._key = bytearray()
        self._hasher = None
        self._indices.clear()
        self._counters.clear()
        self._reserved.clear()
        self._clusters.clear()
        self._by_surname.clear()
        self._by_given.clear()

    def _digest(self, kind: str, value: str) -> bytes:
        if self._hasher is None or not self._key:
            raise RuntimeError("Portée fermée / scope closed")
        hasher = self._hasher.copy()
        hasher.update(f"{kind}\x1f{value}".encode())
        return hasher.digest()

    def reserve(self, text: str) -> None:
        """Réserve les balises déjà présentes dans l'entrée, pour ne jamais les réutiliser.

        Reserves placeholders already present in the input so they are never reused.
        """
        if self._native_scope is not None:
            self._native_scope.reserve(text)
            return
        for m in PLACEHOLDER_RE.finditer(text):
            self._reserved.setdefault(m.group(1), set()).add(int(m.group(2)))

    def _next_index(self, display: str) -> int:
        reserved = self._reserved.get(display, ())
        index = self._counters.get(display, 0) + 1
        while index in reserved:
            index += 1
        self._counters[display] = index
        return index

    def placeholder(self, label_key: str, entity: str, value: str) -> str:
        display = LABELS.display(label_key, self.label_language, self.neutral)
        if self._native_scope is not None:
            return self._native_scope.placeholder(display, entity, value)
        canonical = self.person_key(value) if entity == "PERSON" else _canonical(value)
        digest = self._digest(display, canonical)
        index = self._indices.get(digest)
        if index is None:
            index = self._next_index(display)
            self._indices[digest] = index
        return f"[{display}_{index}]"

    def label_text(self, label_key: str) -> str:
        return LABELS.display(label_key, self.label_language, self.neutral)

    # --- Coréférence des personnes (empreintes uniquement) / person coreference (digests only) ---

    def person_key(self, text: str) -> str:
        """« M. Dupont », « Jean Dupont », « J. Dupont », « DUPONT Jean » -> même grappe / same cluster."""
        if self._native_scope is not None:
            key = self._native_scope.person_key(text)
            return key if key is not None else "raw\x1f" + _canonical(text)
        parsed = split_person_name(text)
        if parsed is None:
            return "raw\x1f" + _canonical(text)
        given, surname = parsed
        s_digest = self._digest("s", fold(surname))
        candidates = self._by_surname.get(s_digest, [])
        if given is None:
            if len(candidates) == 1:
                return f"p{candidates[0]}"
            if not candidates:
                by_given = self._by_given.get(self._digest("g", fold(surname)), [])
                if len(by_given) == 1:
                    return f"p{by_given[0]}"
                return f"p{self._new_cluster(s_digest, None, None)}"
            return "s\x1f" + s_digest.hex()
        initial_digest = self._digest("i", fold(given[0]))
        if len(given) == 1:
            matches = [c for c in candidates if self._clusters[c].initial == initial_digest]
            if len(matches) == 1:
                return f"p{matches[0]}"
            bare = [c for c in candidates if self._clusters[c].given is None]
            if not matches and len(bare) == 1 and len(candidates) == 1:
                self._clusters[bare[0]].initial = initial_digest
                return f"p{bare[0]}"
            return f"p{self._new_cluster(s_digest, None, initial_digest)}"
        g_digest = self._digest("g", fold(given))
        for c in candidates:
            if self._clusters[c].given == g_digest:
                return f"p{c}"
        upgradable = [c for c in candidates if self._clusters[c].given is None
                      and self._clusters[c].initial in (None, initial_digest)]
        if len(upgradable) == 1 and len(candidates) == 1:
            return f"p{self._set_given(upgradable[0], g_digest, initial_digest)}"
        # Un prénom vu seul (« Bonjour Pierre ») rejoint la personne complète / a lone given name joins.
        alone = [c for c in self._by_surname.get(self._digest("s", fold(given)), [])
                 if self._clusters[c].given is None]
        if len(alone) == 1 and not candidates:
            cluster = self._clusters[alone[0]]
            self._by_surname[cluster.surname].remove(alone[0])
            cluster.surname = s_digest
            self._by_surname.setdefault(s_digest, []).append(alone[0])
            return f"p{self._set_given(alone[0], g_digest, initial_digest)}"
        return f"p{self._new_cluster(s_digest, g_digest, initial_digest)}"

    def _new_cluster(self, surname: bytes, given: bytes | None, initial: bytes | None) -> int:
        index = len(self._clusters)
        self._clusters.append(_Cluster(surname, given, initial))
        self._by_surname.setdefault(surname, []).append(index)
        if given is not None:
            self._by_given.setdefault(given, []).append(index)
        return index

    def _set_given(self, index: int, given: bytes, initial: bytes) -> int:
        cluster = self._clusters[index]
        cluster.given = given
        cluster.initial = initial
        self._by_given.setdefault(given, []).append(index)
        return index


_SPACE_RE = re.compile(r"\s+")


def _canonical(value: str) -> str:
    return _SPACE_RE.sub(" ", fold(value)).strip()
