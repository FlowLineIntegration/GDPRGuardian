"""Détecteurs internationaux : IBAN, MRZ, téléphones +CC / international detectors.

E-mail, IBAN, MRZ et la recherche des téléphones ont un jumeau Rust (`gdprguardian_core`) aux résultats identiques,
utilisé quand le noyau est installé et `Settings.native` vrai ; ce module reste la référence. `native_plan` décrit
au moteur fusionné ce que chaque jumeau reçoit de Python. E-mail, IBAN, MRZ and the phone search have a Rust twin
with identical results, used when the core is installed and `Settings.native` is true; this module stays the
reference. `native_plan` tells the fused engine what each twin receives from Python. Chaque jumeau est construit
au premier usage natif : `Settings(native=False)` ne touche jamais le noyau. Each twin is built on first native
use: `Settings(native=False)` never touches the core.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from functools import cache, cached_property, partial
from typing import Any

from .. import _native
from ..types import PRIORITY_LENIENT, PRIORITY_STRUCTURAL, PRIORITY_VALIDATED, Span
from ..validators.checksums import icao_check_digit, mod97_10_ok
from ..validators.intl import IBAN_LENGTHS, digits_e164, email

try:
    import phonenumbers

    _HAS_PHONENUMBERS = True
except ImportError:  # pragma: no cover
    _HAS_PHONENUMBERS = False


@cache
def _native_email() -> Any:
    core = _native.core()
    return None if core is None else core.EmailDetector(_native.unicode_table())


@cache
def _native_iban() -> Any:
    core = _native.core()
    return None if core is None else core.IbanDetector(_native.unicode_table(), IBAN_LENGTHS)


@cache
def _native_phone() -> Any:
    """Recherche native des candidats téléphoniques, ou None / native phone candidate search, or None."""
    core = _native.core()
    if core is None or not hasattr(core, "phone_candidates"):
        return None
    return partial(core.phone_candidates, _native.unicode_table())


def _native_mrz() -> Any:
    """Recherche native des bandes MRZ, ou None / native MRZ band search, or None."""
    core = _native.core()
    return None if core is None else core.mrz_bands


class EmailDetector:
    """Ancré sur « @ » (rare) plutôt qu'une regex tentée à chaque mot / anchored on '@' instead of every word."""

    id = "EMAIL"
    _local = re.compile(r"[\w.%+\-]{1,64}$")
    # Un tiret suivi d'autre chose qu'un domaine termine l'adresse (« x@y.fr- Lyon ») / a dash not followed by a
    # domain ends the address.
    _domain = re.compile(r"(?:[\w\-]{1,63}\.){1,8}[A-Za-z]{2,24}(?!\w)(?!-[\w\-]*\.)")

    def __init__(self, pack: Any) -> None:
        self.pack = pack

    @cached_property
    def _native(self) -> Any:
        """Jumeau Rust, construit au premier usage natif / Rust twin, built on first native use."""
        return _native_email()

    def detect(self, ctx: Any) -> list[Span]:
        text = ctx.text
        native = ctx.settings.native and self._native is not None
        spans: list[Span] = []
        # `email` valide et normalise dans les deux cas : son `str.lower` suit la version Unicode de l'interpréteur.
        # `email` validates and normalises on both paths: its `str.lower` follows the interpreter's Unicode version.
        for start, end in self._native.detect(text) if native else self._candidates(text):
            value = email(text[start:end])
            if value is not None:
                spans.append(self._span(start, end, value))
        return spans

    def _span(self, start: int, end: int, value: str | None) -> Span:
        return Span(start, end, "EMAIL", "EMAIL", self.id, 0.99, PRIORITY_STRUCTURAL, value)

    def native_plan(self) -> dict[str, Any] | None:
        """Moteur fusionné : candidats du jumeau, validés par `email` / fused engine: twin candidates, `email`."""
        if self._native is None:
            return None
        return {"kind": "email", "twin": self._native, "prototype": self._span(0, 0, None), "validate": email}

    def _candidates(self, text: str) -> Iterator[tuple[int, int]]:
        """(début, fin) des adresses candidates / (start, end) of candidate addresses."""
        at = text.find("@")
        while at != -1:
            window_start = max(0, at - 64)
            local = self._local.search(text, window_start, at)
            domain = self._domain.match(text, at + 1)
            if local and domain:
                start = local.start()
                while start < at and text[start] == ".":
                    start += 1
                cut = start == window_start and start > 0 and (text[start - 1].isalnum() or text[start - 1] in "_.%+-")
                if not cut:
                    yield start, domain.end()
            at = text.find("@", at + 1)


class IbanDetector:
    """Ancre « CC00 », puis consommation de la longueur du pays : pas de débordement sur le mot suivant.

    Anchor "CC00", then consume exactly the country length: never spills into the next word. Clé fausse :
    gardé seulement près d'un mot-clé (« IBAN », « RIB »…) / wrong key: kept only next to a keyword.
    """

    id = "INTL_IBAN"
    _anchor = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2}) ?([0-9]{2})(?=[ \-]?[A-Za-z0-9])")
    _window = (48, 16)  # mot-clé avant, après / keyword before, after

    def __init__(self, pack: Any) -> None:
        self.pack = pack
        self._contexts = (pack.group("iban"),)

    @cached_property
    def _native(self) -> Any:
        """Jumeau Rust, construit au premier usage natif / Rust twin, built on first native use."""
        return _native_iban()

    def detect(self, ctx: Any) -> list[Span]:
        if not ctx.has("digit"):
            return []
        native = ctx.settings.native and self._native is not None
        spans: list[Span] = []
        for start, end, value, printed in self._native.detect(ctx.text) if native else self._candidates(ctx.text):
            if value is not None:
                spans.append(self._valid(start, end, value))
            elif printed or ctx.near(self._contexts, start, end, *self._window):
                spans.append(self._lenient(start, end))
        return spans

    def _valid(self, start: int, end: int, value: str) -> Span:
        return Span(start, end, "IBAN", "IBAN", self.id, 0.98, PRIORITY_VALIDATED, value)

    def _lenient(self, start: int, end: int) -> Span:
        # Même priorité qu'une carte groupée : l'IBAN, plus long, l'emporte sur ses blocs internes.
        # Same priority as a grouped card: the longer IBAN wins over its inner blocks.
        return Span(start, end, "IBAN", "IBAN", self.id, 0.6, PRIORITY_LENIENT)

    def native_plan(self) -> dict[str, Any] | None:
        """Moteur fusionné : candidats du jumeau, contexte lu en Rust / fused engine: twin candidates."""
        if self._native is None:
            return None
        return {"kind": "iban", "twin": self._native, "valid": self._valid(0, 0, ""), "lenient": self._lenient(0, 0),
                "contexts": list(self._contexts), "window": self._window}

    def _candidates(self, text: str) -> Iterator[tuple[int, int, str | None, bool]]:
        """(début, fin, valeur si la clé est juste, mise en page par quatre) / (start, end, value, printed)."""
        length = len(text)
        for m in self._anchor.finditer(text):
            country = m.group(1).upper()
            expected = IBAN_LENGTHS.get(country)
            if expected is None:
                continue
            needed = expected - 4
            chars: list[str] = []
            pos = end = m.end()
            while len(chars) < needed and pos < length:
                ch = text[pos]
                if ch.isascii() and ch.isalnum():
                    chars.append(ch)
                    pos += 1
                    end = pos
                elif ch in " -" and (not chars or (pos + 1 < length and text[pos + 1].isalnum())):
                    pos += 1
                else:
                    break
            if len(chars) != needed or (end < length and text[end].isalnum()):
                continue
            bban = "".join(chars).upper()
            if mod97_10_ok(bban + country + m.group(2)):
                yield m.start(), end, country + m.group(2) + bban, False
            else:
                yield m.start(), end, None, _printed_in_fours(text[m.start():end])


def _printed_in_fours(raw: str) -> bool:
    """Format imprimé « FR76 3000 6000 … » : la forme seule trahit un IBAN / printed layout betrays an IBAN."""
    groups = raw.split(" ")
    return len(groups) >= 4 and all(len(g) == 4 for g in groups[:-1]) and 1 <= len(groups[-1]) <= 4


class MrzDetector:
    """Bande MRZ (ICAO 9303) : 2 ou 3 lignes ; masquée en bloc / masked as one block."""

    id = "INTL_MRZ"
    _block = re.compile(
        r"(?m)^[ \t]*[A-Z0-9<]{28,46}[ \t]*\r?\n[ \t]*[A-Z0-9<]{28,46}(?:[ \t]*\r?\n[ \t]*[A-Z0-9<]{28,46})?"
    )
    _prefilter = "<"

    def __init__(self, pack: Any) -> None:
        self.pack = pack

    @cached_property
    def _native(self) -> Any:
        """Jumeau Rust, pris au premier usage natif / Rust twin, taken on first native use."""
        return _native_mrz()

    def detect(self, ctx: Any) -> list[Span]:
        if not ctx.has(self._prefilter):
            return []
        native = ctx.settings.native and self._native is not None
        return [self._span(start, end, score)
                for start, end, score in (self._native(ctx.text) if native else self._bands(ctx.text))]

    def _span(self, start: int, end: int, score: float) -> Span:
        return Span(start, end, "MRZ", "MRZ", self.id, score, PRIORITY_VALIDATED)

    def native_plan(self) -> dict[str, Any] | None:
        """Moteur fusionné : bandes du jumeau / fused engine: the twin's bands."""
        if self._native is None:
            return None
        return {"kind": "mrz", "prototype": self._span(0, 0, 0.0), "prefilter": self._prefilter}

    def _bands(self, text: str) -> Iterator[tuple[int, int, float]]:
        """(début, fin, score) des bandes / (start, end, score) of the bands."""
        for m in self._block.finditer(text):
            block = m.group()
            lines = [line.strip() for line in block.splitlines()]
            if block.count("<") < 4 or lines[0][:1] not in "PIACV":
                continue
            score = 0.9 + 0.08 * _mrz_check_ratio(lines)
            yield m.start() + (len(block) - len(block.lstrip())), m.end(), min(score, 1.0)


def _mrz_check_ratio(lines: list[str]) -> float:
    """Part des champs dont la clé ICAO est juste (TD3) / share of correct ICAO check digits."""
    if len(lines) != 2 or len(lines[1]) < 28:
        return 0.0
    line = lines[1]
    fields = ((line[0:9], line[9]), (line[13:19], line[19]), (line[21:27], line[27]))
    good = sum(1 for value, check in fields if check.isdigit() and icao_check_digit(value) == int(check))
    return good / len(fields)


def _e164(raw: str) -> str | None:
    """Validation phonenumbers, sans cache partagé : un cache garderait les numéros d'une requête à l'autre et
    trahirait par sa vitesse qu'un numéro a déjà été vu. Validation without a shared cache, which would keep
    numbers across requests and reveal through its speed that a number was already seen.
    """
    try:
        parsed = phonenumbers.parse(raw, None)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class InternationalPhoneDetector:
    """Numéros écrits avec +CC ou 00CC ; validés par phonenumbers si installé / validated if installed.

    La recherche des candidats a un jumeau Rust ; la validation reste ici (`value`).
    The candidate search has a Rust twin; validation stays here (`value`).
    """

    id = "INTL_PHONE"
    _candidate = re.compile(r"(?<![\w+.\-])(?:\+[1-9]|00[1-9])[0-9 .\-()]{6,20}[0-9](?![0-9])")
    _prefilters = ("+", "00")

    def __init__(self, pack: Any) -> None:
        self.pack = pack

    @cached_property
    def _native(self) -> Any:
        """Jumeau Rust, construit au premier usage natif / Rust twin, built on first native use."""
        return _native_phone()

    def detect(self, ctx: Any) -> list[Span]:
        if not ctx.has(self._prefilters):
            return []
        text = ctx.text
        # Jumeau Rust ; None pour un texte non encodable en UTF-8 / Rust twin; None for lone surrogates.
        found = self._native(text) if ctx.settings.native and self._native is not None else None
        if found is None:
            found = [m.span() for m in self._candidate.finditer(text)]
        spans: list[Span] = []
        seen: dict[str, str | None] = {}  # mémo de cet appel seulement / this call only
        for start, end in found:
            validated = self.value(text[start:end], seen)
            if validated is not None:
                spans.append(self._span(start, end, *validated))
        return spans

    def value(self, candidate: str, seen: dict[str, str | None] | None = None) -> tuple[str, float, int] | None:
        """(valeur E.164, score, priorité) d'un candidat, ou None ; `seen` : mémo d'un seul appel.

        (E.164 value, score, priority) of a candidate, or None; `seen`: one call's memo.
        """
        digit_count = sum(c.isdigit() for c in candidate) - (2 if candidate.startswith("00") else 0)
        if not 8 <= digit_count <= 15:
            return None
        if _HAS_PHONENUMBERS:
            raw = "+" + candidate[2:] if candidate.startswith("00") else candidate
            if seen is None:
                value = _e164(raw)
            else:
                if raw not in seen:
                    seen[raw] = _e164(raw)
                value = seen[raw]
            priority, score = PRIORITY_VALIDATED, 0.95
        else:
            value = digits_e164(candidate)
            priority, score = PRIORITY_STRUCTURAL, 0.85
        return None if value is None else (value, score, priority)

    def _span(self, start: int, end: int, value: str | None, score: float, priority: int) -> Span:
        return Span(start, end, "PHONE", "PHONE", self.id, score, priority, value)

    def native_plan(self) -> dict[str, Any]:
        """Moteur fusionné : candidats en Rust, validation par `value` / fused engine: Rust candidates, `value`."""
        return {"kind": "phone", "prototype": self._span(0, 0, None, 0.0, 0), "prefilters": list(self._prefilters),
                "value": self.value}
