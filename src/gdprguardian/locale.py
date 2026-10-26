"""Choix des packs pays en mode « auto » / country-pack selection in "auto" mode.

La langue ne décide jamais seule : le français couvre FR, BE, CH, LU, MC, CA, MA…
Language never decides alone: French covers FR, BE, CH, LU, MC, CA, MA…
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from functools import cache
from typing import Any

from . import _native
from .packs import Pack
from .types import Span

ACTIVATION_THRESHOLD = 3.0
LANGUAGE_SAMPLE = 3000
_WORD_RE = re.compile(r"[a-z]+")

# Mots outils distinctifs par langue / distinctive stopwords per language.
_STOPWORDS = {
    "fr": ("le", "la", "les", "des", "une", "est", "pour", "dans", "avec", "sur", "qui", "pas", "nous", "vous",
           "cette", "aux", "ete", "etre", "mais", "ou"),
    "en": ("the", "and", "is", "are", "of", "to", "for", "with", "that", "this", "was", "were", "have", "has",
           "from", "which"),
    "de": ("der", "die", "das", "und", "ist", "nicht", "mit", "fur", "ein", "eine", "auf", "sind", "wir", "ich"),
    "es": ("el", "los", "las", "que", "y", "para", "con", "por", "una", "es", "del", "como", "pero"),
    "it": ("il", "che", "di", "per", "non", "con", "una", "sono", "della", "gli", "anche", "questo"),
    "nl": ("het", "een", "van", "en", "niet", "met", "zijn", "voor", "op", "dat", "ook", "wij"),
    "pt": ("nao", "uma", "pelo", "pela", "tambem", "sao", "isso", "ate", "muito", "ao", "aos"),
}
_WORD_LANGUAGES: dict[str, tuple[str, ...]] = {}
for _language, _words in _STOPWORDS.items():
    for _word in _words:
        _WORD_LANGUAGES[_word] = (*_WORD_LANGUAGES.get(_word, ()), _language)


@cache
def _native_detector() -> Any:
    return _native.language_detector(_WORD_LANGUAGES, LANGUAGE_SAMPLE)


def detect_language(folded: str, minimum: int = 2, *, native: bool = False) -> str:
    """Langue majoritaire sur un échantillon (comptage de mots outils) / dominant language on a sample.

    `native=True` : noyau Rust s'il est installé, même résultat / Rust core when installed, same result.
    """
    detector = _native_detector() if native else None
    if detector is not None:
        try:
            return detector.detect(folded, minimum)
        except (UnicodeEncodeError, OverflowError):  # demi-codet isolé, `minimum` hors 64 bits : voie Python
            pass  # lone surrogate or `minimum` beyond 64 bits: Python path
    counts: dict[str, int] = {}
    for word in _WORD_RE.findall(folded, 0, LANGUAGE_SAMPLE):
        for language in _WORD_LANGUAGES.get(word, ()):
            counts[language] = counts.get(language, 0) + 1
    best, best_count = "und", minimum - 1
    for language, count in counts.items():
        if count > best_count:
            best, best_count = language, count
    return best


def evidence(spans: Iterable[Span]) -> tuple[list[str], list[str], list[str]]:
    """Indices de pays tirés des zones VALIDÉES : IBAN, téléphones E.164, domaines des e-mails.

    Country evidence from VALIDATED spans: IBAN, E.164 phones, e-mail domains.
    """
    ibans: list[str] = []
    phones: list[str] = []
    tlds: list[str] = []
    for span in spans:
        value = span.value or ""
        if span.entity == "IBAN" and len(value) >= 2:
            ibans.append(value[:2].upper())
        elif span.entity == "PHONE" and value.startswith("+"):
            phones.append(value[1:4])
        elif span.entity == "EMAIL":
            tld = value.rsplit(".", 1)[-1].lower()
            if len(tld) == 2:
                tlds.append(tld)
    return ibans, phones, tlds


def select_countries(
    hits: Any,
    packs: Iterable[Pack],
    defaults: Sequence[str],
    language: str,
    ibans: Sequence[str] = (),
    phones: Sequence[str] = (),
    tlds: Sequence[str] = (),
) -> tuple[tuple[str, ...], dict[str, list[str]]]:
    country_packs = [p for p in packs if p.country]
    scores: dict[str, float] = defaultdict(float)
    reasons: dict[str, list[str]] = defaultdict(list)
    for country in defaults:
        scores[country] += ACTIVATION_THRESHOLD
        reasons[country].append("default")
    # Un indicatif, un code IBAN ou un domaine peut appartenir à plusieurs packs (MC et FR) : tous crédités.
    # A dialling code, IBAN code or domain may belong to several packs (MC and FR): all are credited.
    phone_owners: dict[str, list[str]] = defaultdict(list)
    iban_owners: dict[str, list[str]] = defaultdict(list)
    tld_owners: dict[str, list[str]] = defaultdict(list)
    counts = hits.counts
    for pack in country_packs:
        # Groupes passifs (sigles partagés : NIF, NSS…) : contexte de proximité, jamais preuve de pays.
        # Passive groups (shared acronyms: NIF, NSS…): proximity context, never country evidence.
        passive = {pack.group(name) for name in pack.locale.get("passive_context", ())}
        groups = [g for g in pack.context if not g.endswith(":ei") and g not in passive]
        found = sum(1 for g in groups if g in counts)
        if found:
            scores[pack.country] += 3.0 * min(found, 3)
            reasons[pack.country].append(f"keywords:{found}")
        for code in pack.locale.get("phone_codes", ()):
            phone_owners[code].append(pack.country)
        for code in pack.locale.get("iban_countries", ()):
            iban_owners[code].append(pack.country)
        for tld in pack.locale.get("tlds", ()):
            tld_owners[tld].append(pack.country)
        if language in pack.locale.get("languages", ()):
            scores[pack.country] += 0.5
    for digits in phones:
        for size in (3, 2, 1):
            owners = phone_owners.get(digits[:size])
            if owners:
                for owner in owners:
                    scores[owner] += 3.0
                    reasons[owner].append(f"phone:+{digits[:size]}")
                break
    for code in ibans:
        for owner in iban_owners.get(code, ()):
            scores[owner] += 3.0
            reasons[owner].append(f"iban:{code}")
    for tld in tlds:
        for owner in tld_owners.get(tld, ()):
            scores[owner] += 1.0
            reasons[owner].append(f"tld:.{tld}")
    available = {p.country for p in country_packs}
    active = tuple(sorted(c for c, s in scores.items() if s >= ACTIVATION_THRESHOLD and c in available))
    # Raisons dédoublonnées : un texte de 100 Ko citait 911 fois « tld:.fr » / deduplicated reasons.
    return active, {c: list(dict.fromkeys(reasons[c])) for c in active}
