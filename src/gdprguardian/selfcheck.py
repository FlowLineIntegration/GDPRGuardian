"""Contrôle final de sortie, variante restreinte (1.0.2, REGLES.md « Contrôle final de sortie ») / output self-check.

Après la résolution et toutes les propagations, juste avant les règles « keep » de l'organisation : toute valeur
d'identifiant que le moteur a masquée quelque part dans le document (au moins 6 caractères, un chiffre ou « @ ») et
qui reste en clair ailleurs, à la casse et aux accents près (texte replié), est masquée avec la même balise (même
valeur), règle `output_check:<règle source>`, raison `output_check`. Les variantes d'espacement et de séparateurs
des codes et des téléphones sont déjà couvertes par la propagation des valeurs (squelette) ; ce contrôle couvre ce
qu'elle ne voit pas : une occurrence collée à un mot (« Tel0612345678 », « refCLT-204518 »), une e-mail, toute
entité hors squelette. Jamais au milieu d'un nombre (deux chiffres de part et d'autre d'une borne), jamais sur une
zone existante (masquée ou gardée) ; les règles « keep » passent après et l'emportent. Il ne fait que ré-appliquer ce
que le mode a déjà masqué : il tourne dans tous les modes. Déterministe, rien n'est gardé ; jumeau Rust :
`rust/src/finalize/selfcheck.rs`.

After resolution and every propagation, right before the organisation's keep rules: every identifier value the
engine masked somewhere in the document (6 characters or more, a digit or "@") that is still in clear elsewhere, up
to case and accents (folded text), is masked with the same tag (same value), rule `output_check:<source rule>`,
reason `output_check`. Never inside a number (two digits across a bound), never over an existing span (masked or
kept); keep rules run afterwards and win. It only re-applies what the mode already masked, so it runs in every
mode. Deterministic, nothing is kept; Rust twin: `rust/src/finalize/selfcheck.rs`.
"""

from __future__ import annotations

from bisect import bisect_left

from .keywords import longest_matches
from .types import Span

CHECK_MIN = 6
# Au-delà, ce n'est plus une valeur d'identifiant (une e-mail tient en 128) : borne le coût sur un texte hostile
# (« 1 » × 100 000 masqué d'un bloc coûtait 23 s à l'automate). Beyond this, not an identifier value: bounds the
# cost on hostile input.
CHECK_MAX = 128
CHECK_REASON = "output_check"
_MARKS = frozenset("0123456789@")


def _inside_number(a: str, b: str) -> bool:
    """Deux chiffres voisins : une borne au milieu d'un nombre / two neighbouring digits: a bound inside a number."""
    return a.isdigit() and b.isdigit()


# Montant (revue du 26/10, troisième tour) : une valeur faite de chiffres seuls n'est jamais ré-appliquée sur un
# montant ou une mesure (« Contrat 100000 … capital 100000 € »). Devise ou unité juste après (une espace permise),
# devise juste avant, forme décimale ou de milliers. Mots ASCII, casse ignorée ; jumeau Rust : `selfcheck.rs`.
# Amount: a digits-only value is never re-applied to an amount or a measure.
_AMOUNT_SIGNS_AFTER = frozenset("€$£%‰")
_AMOUNT_SIGNS_BEFORE = frozenset("€$£")
_AMOUNT_WORDS_AFTER = frozenset({
    "eur", "euro", "euros", "keur", "meur", "usd", "dollar", "dollars", "gbp", "chf", "xpf", "fcfa", "km", "kg", "mg",
    "cm", "mm", "ml", "cl", "kw", "kwh", "mw", "mwh", "ko", "mo", "go", "kb", "mb", "gb", "octet", "octets", "byte",
    "bytes", "ht", "ttc"})
_AMOUNT_WORDS_BEFORE = frozenset({"eur", "euro", "euros", "usd", "gbp", "chf"})
_AMOUNT_BLANKS = frozenset(" \t  ")
_ASCII_LETTERS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
_ASCII_DIGITS = frozenset("0123456789")


def _amount(text: str, start: int, end: int) -> bool:
    """`text[start:end]` (chiffres seuls) est-il un montant ou une mesure ? / is the digit run an amount or measure?"""
    size = len(text)
    if end + 1 < size and text[end] in ",." and text[end + 1] in _ASCII_DIGITS:
        return True
    if start > 1 and text[start - 1] in ",." and text[start - 2] in _ASCII_DIGITS:
        return True
    i = end + 1 if end < size and text[end] in _AMOUNT_BLANKS else end
    if i < size and text[i] in _AMOUNT_SIGNS_AFTER:
        return True
    j = i
    while j < size and text[j] in _ASCII_LETTERS:
        j += 1
    word = text[i:j].lower()
    if word in _AMOUNT_WORDS_AFTER or (word in ("k", "m", "md") and j < size and text[j] == "€"):
        return True
    k = start - 1 if start > 0 and text[start - 1] in _AMOUNT_BLANKS else start
    if k > 0 and text[k - 1] in _AMOUNT_SIGNS_BEFORE:
        return True
    m = k
    while m > 0 and text[m - 1] in _ASCII_LETTERS:
        m -= 1
    return text[m:k].lower() in _AMOUNT_WORDS_BEFORE


def output_check(text: str, folded: str, spans: list[Span]) -> list[Span]:
    """Zones finales complétées par le contrôle de sortie ; `spans` triées par début et disjointes, le résultat aussi.

    Final spans completed by the output self-check; `spans` sorted by start and disjoint, so is the result.
    """
    sources: dict[str, Span] = {}
    for span in spans:
        if not span.personal:
            continue
        key = folded[span.start:span.end]
        if not CHECK_MIN <= len(key) <= CHECK_MAX or "\n" in key or not any(c in _MARKS for c in key):
            continue
        sources.setdefault(key, span)
    if not sources:
        return spans
    keys = list(sources)
    numeric = [all(c in _ASCII_DIGITS for c in key) for key in keys]
    starts = [s.start for s in spans]
    added: list[Span] = []
    size = len(text)
    for index, start, end in longest_matches(keys, folded):
        if (start > 0 and _inside_number(text[start - 1], text[start])) or (
                end < size and _inside_number(text[end - 1], text[end])):
            continue
        if numeric[index] and _amount(text, start, end):
            continue
        k = bisect_left(starts, end)
        if k > 0 and spans[k - 1].end > start:
            continue  # déjà une zone, masquée ou gardée / already a span, masked or kept
        source = sources[keys[index]]
        value = source.value if source.value is not None else text[source.start:source.end]
        added.append(Span(start, end, source.entity, source.label, f"{CHECK_REASON}:{source.source}", source.score,
                          source.priority, value, True, reason=CHECK_REASON))
    if not added:
        return spans
    return sorted(spans + added, key=lambda s: s.start)
