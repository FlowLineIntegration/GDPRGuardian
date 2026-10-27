"""Codes d'identifiant du filtre fort 1.0.2 (règle `ID_CODE`, REGLES.md § 2) / identifier codes of the strong filter.

Un jeton fait de lettres ASCII et de chiffres (« CLT-204518 », « TCK022609 », « VOX-6940-AK84 ») est masqué en
`[IDENTIFIANT_n]` (raison `identifier_code`) dès qu'il porte une lettre, un chiffre et 6 caractères alphanumériques,
quel que soit son préfixe (facture, commande, produit, lot compris : choix du propriétaire, « on anonymise tout
code »), sauf exclusion nommée pour ce qui n'est pas un identifiant (unités, versions, articles de loi, heures, BIC,
dimensions, périodes, horodatages, mois, courte liste, balises). Une suite nue de 8 chiffres ou plus est masquée de
même (règle `ID_LONG_NUMBER`, raison `long_number`), sauf montant ou date compacte. Une organisation garde ses codes
lisibles par ses propres règles « keep » (custom.py), qui l'emportent. Priorité la plus basse des règles : tout
recognizer plus précis (SIRET, IBAN, plaque, e-mail) l'emporte. Rien n'est gardé d'un appel à l'autre.

A token made of ASCII letters and digits is masked as `[IDENTIFIANT_n]` (reason `identifier_code`) once it holds a
letter, a digit and 6 alphanumeric characters, whatever its prefix, unless a named exclusion for what is not an
identifier applies. A bare run of 8 digits or more is masked too (rule `ID_LONG_NUMBER`, reason `long_number`),
except an amount or a compact date. An organisation keeps its codes readable with its own keep rules, which win.
Lowest rule priority: any more specific recognizer wins. Nothing is kept between calls. Le moteur fusionné utilise son
jumeau Rust (`rust/src/detectors/codes.rs`, `native_plan`), mêmes zones et mêmes valeurs / the fused engine uses its
Rust twin, same spans and values.
"""

from __future__ import annotations

import re
from typing import Any

from .. import _native
from ..types import PRIORITY_NER, PRIORITY_PROPAGATED, PRIORITY_STRUCTURAL, Span
from ..validators.intl import IBAN_LENGTHS

# Sous les heuristiques et le NER, au-dessus des occurrences propagées / below heuristics and NER, above propagation.
PRIORITY_ID_CODE = (PRIORITY_PROPAGATED + PRIORITY_NER) // 2

# Jeton maximal ; un point suivi d'un mot capitalisé (« AB12.Le ») coupe le jeton. Motif linéaire (pas de retour
# arrière quadratique sur un long jeton sans chiffre) ; le chiffre est vérifié ensuite, en C. Maximal token; a full
# stop before a capitalised word breaks the token. Linear pattern; the digit is checked afterwards, in C.
# Troisième tour (revue du 26/10) : « # » relie aussi deux morceaux (« CLT#204518 », « JIRA#62528 »).
# Third round: "#" joins two pieces too.
_TOKEN = re.compile(r"[A-Za-z0-9]+(?:(?:[-_/#]|\.(?![A-Z][a-z]))[A-Za-z0-9]+)*")
_DIGIT = re.compile(r"[0-9]")
_LETTER = re.compile(r"[A-Za-z]")
_SEPARATORS = str.maketrans("", "", "-_/.#")

_MONTHS = ("janvier", "fevrier", "février", "mars", "avril", "juillet", "aout", "août", "septembre", "octobre",
           "novembre", "decembre", "décembre", "january", "february", "march", "april", "june", "july", "august",
           "september", "october", "november", "december")

# Exclusions nommées (REGLES.md, tests) / named exclusions (REGLES.md, tests).
_EXCLUSIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("unit_suffix", re.compile(
        r"(?i)\d+(?:[.,]\d+)?(?:km|kg|mg|g|cm|mm|m2|m3|m|ml|cl|l|h|min|ms|s|eur|euros?|usd|ko|mo|go|to|kb|mb|gb|tb"
        r"|kwh|kw|mw|w|v|hz|khz|mhz|ghz|px|pt|er|re|e|eme|nd|rd|th|st|ans?|j|jours?|mois|k)")),
    ("digits_glued_to_word", re.compile(r"\d+[A-Z]?[a-z]{2,}")),
    ("version", re.compile(r"(?i)v{0,2}\d+(?:\.\d+){1,3}(?:[-.+]?(?:alpha|beta|rc|dev|post|pre|a|b)\d*)?")),
    ("legal_article", re.compile(r"[LRDAO]\.?\d{1,4}(?:-\d+)*")),
    ("time", re.compile(r"(?i)\d{1,2}h(?:\d{2})?(?:-\d{1,2}h(?:\d{2})?)?")),
    ("dimensions", re.compile(r"(?i)\d+x\d+(?:x\d+)?")),
    ("period", re.compile(r"(?i)[TSQH][1-4]-?\d{4}|\d{4}-?[TSQH][1-4]|FY\d{2,4}")),
    ("iso_timestamp", re.compile(r"(?i)\d{4}-\d{2}-\d{2}t\d{1,2}|\d{1,2}(?:\.\d+)?z")),
    ("standard", re.compile(r"(?i)(?:iso|iec|rfc|din)[-_/.]?\d+(?:[-_/.]\d+)*")),
)
_SHORT_LIST = frozenset({"COVID19", "SARSCOV2", "H1N1", "H5N1", "CO2", "MP3", "MP4", "MPEG4", "IPV4", "IPV6",
                         "UTF8", "UTF16", "BASE64", "SHA256", "SHA512", "SHA1", "MD5", "X509", "OAUTH2", "HTTP2"})
_BIC = re.compile(r"[A-Z]{4}([A-Z]{2})[A-Z0-9]{2}(?:[A-Z0-9]{3})?")
_PLACEHOLDER_TOKEN = re.compile(r"[A-Z][A-Z0-9_]*_\d+")

# Voie « codes » (1.0.2, dernier tour) : code coupé par une espace ou une espace insécable. Préfixe de 2 à 5 capitales
# puis 6 ou 7 chiffres (« CLT 204518 », « DOS 164520 » ; 8 chiffres ou plus relèvent déjà de `ID_LONG_NUMBER`,
# 5 chiffres seraient un code postal) ; ou 3 groupes ou plus de 3 à 6 capitales et chiffres dont deux mêlent lettres
# et chiffres (« AB12 CD34 EF56 »). Même règle `ID_CODE` (raison `identifier_code`, mode fort ; en essentiel
# seulement après un libellé personnel). Jamais collé à un mot, à « @ », « . », « - », « / », « # », « \ » ;
# préfixes de nomenclature, de publication, de boîte postale, de norme ou de devise exclus (`_SPLIT_STOP`) ;
# montants, dates et classifications exclus comme pour les longues suites. A code split by a space or a no-break
# space: a 2-to-5-capital prefix and 6 or 7 digits, or 3 groups or more of 3 to 6 capitals and digits, two of
# them mixing letters and digits. Same `ID_CODE` rule.
_SPLIT_PREFIXED = re.compile("[A-Z]{2,5}[   ][0-9]{6,7}")
_SPLIT_GROUPED = re.compile("[A-Z0-9]{3,6}(?:[   ][A-Z0-9]{3,6}){2,7}")
_SPLIT_GAPS = str.maketrans("", "", "   ")
_SPLIT_STOP = frozenset({
    "AN", "APE", "ART", "ARTS", "BALO", "BOAMP", "BODACC", "BP", "CEDEX", "CEI", "CHF", "CP", "CPV", "CS", "DIN",
    "ECLI", "EN", "EUR", "FR", "GBP", "IEC", "ISO", "JO", "JORF", "NACE", "NAF", "NF", "NO", "NOR", "NUM", "NUTS",
    "RCS", "RD", "RM", "RN", "RNA", "ROME", "RT", "SIREN", "SIRET", "TOME", "TSA", "TVA", "USD", "VOL"})
_SPLIT_BEFORE = frozenset("_@.-/#\\")


def _split_glued(text: str, start: int, end: int) -> bool:
    """Code coupé collé à un mot ou à un signe de jeton / a split code glued to a word or a token sign."""
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    if before and (before.isalnum() or before in _SPLIT_BEFORE):
        return True
    if after and (after.isalnum() or after in "_@-/#\\"):
        return True
    return after in ".," and end + 1 < len(text) and text[end + 1].isalnum()


def split_code_spans(text: str) -> list[tuple[int, int, str]]:
    """Codes coupés par une espace, (début, fin, valeur) dans l'ordre du texte / split codes, in text order."""
    found: list[tuple[int, int, str]] = []
    for m in _SPLIT_PREFIXED.finditer(text):
        start, end = m.span()
        if _split_glued(text, start, end):
            continue
        token = m.group()
        digits = len(token) - len(token.rstrip("0123456789"))
        prefix = token[:len(token) - digits - 1]
        if prefix in _SPLIT_STOP or long_number_exclusion(text, end - digits, end) is not None:
            continue
        found.append((start, end, prefix + token[len(token) - digits:]))
    for m in _SPLIT_GROUPED.finditer(text):
        start, end = m.span()
        if _split_glued(text, start, end):
            continue
        groups = m.group().translate(str.maketrans("  ", "  ")).split(" ")
        mixed = sum(1 for g in groups if _LETTER.search(g) and _DIGIT.search(g))
        if mixed < 2 or groups[0] in _SPLIT_STOP:
            continue
        found.append((start, end, m.group().translate(_SPLIT_GAPS)))
    found.sort()
    return found


_ALNUM = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
_UPPER = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_LOWER = frozenset("abcdefghijklmnopqrstuvwxyz")


def _token_start(text: str, pos: int) -> int:
    """Début du jeton `_TOKEN` qui contient `text[pos]`, tel que `finditer` le trouverait (mêmes coupures).

    Start of the `_TOKEN` token holding `text[pos]`, as `finditer` would find it (same breaks).
    """
    while True:
        while pos > 0 and text[pos - 1] in _ALNUM:
            pos -= 1
        if pos < 2 or text[pos - 2] not in _ALNUM:
            return pos
        separator = text[pos - 1]
        joined = separator in "-_/#" or (separator == "." and not (
            text[pos] in _UPPER and pos + 1 < len(text) and text[pos + 1] in _LOWER))
        if not joined:
            return pos
        pos -= 1


def _pieces(token: str, start: int) -> list[tuple[str, int]]:
    """Le jeton, ou les segments d'un chemin qui porte un nom de domaine (un « . » et un « / ») : le domaine
    reste lisible, seul le code d'un segment est masqué (« site.fr/dossiers/CLT-204518 »).

    The token, or the segments of a path holding a domain name (a "." and a "/"): the domain stays readable, only
    a segment's code is masked.
    """
    if "/" not in token or "." not in token:
        return [(token, start)]
    pieces, offset = [], start
    for piece in token.split("/"):
        pieces.append((piece, offset))
        offset += len(piece) + 1
    return pieces


def exclusion(token: str) -> str | None:
    """Nom de l'exclusion qui garde ce jeton lisible, ou None / name of the exclusion that keeps it, or None."""
    for name, pattern in _EXCLUSIONS:
        if pattern.fullmatch(token):
            return name
    if token.translate(_SEPARATORS).upper() in _SHORT_LIST:
        return "short_list"
    bic = _BIC.fullmatch(token)
    if bic is not None and bic.group(1) in IBAN_LENGTHS:
        return "bic"
    lowered = token.lower()
    if any(month in lowered for month in _MONTHS):
        return "month_name"
    return None


def is_code(token: str) -> bool:
    """Jeton de `_TOKEN` (ASCII) : une lettre, un chiffre, 6 caractères alphanumériques au moins.

    A `_TOKEN` token (ASCII): a letter, a digit, 6 alphanumerics at least.
    """
    skeleton = token.translate(_SEPARATORS)
    return (len(skeleton) >= 6 and skeleton.isascii() and skeleton.isalnum() and not skeleton.isdigit()
            and not skeleton.isalpha())


class IdentifierCodeDetector:
    """Règle `ID_CODE` du filtre fort / the strong filter's `ID_CODE` rule."""

    id = "ID_CODE"

    def __init__(self, pack: Any) -> None:
        self.pack = pack

    def detect(self, ctx: Any) -> list[Span]:
        # Témoins dans le même appel : un seul passage par Python pour le moteur fusionné.
        # Cookies in the same call: a single trip through Python for the fused engine.
        spans = cookie_spans(ctx)
        if not ctx.has("digit"):
            return spans
        text = ctx.text
        size = len(text)
        search, token_at, letter = _DIGIT.search, _TOKEN.match, _LETTER.search
        # Seuls les jetons qui portent un chiffre sont visités, chacun une fois ; sans lettre (date, montant),
        # écartés aussitôt. Only tokens holding a digit are visited, once each; without a letter, dropped at once.
        pos = 0
        while (digit := search(text, pos)) is not None:
            m = token_at(text, _token_start(text, digit.start()))
            start, end = m.span()
            pos = end
            if end - start < 6:
                continue
            token = m.group()
            before = text[start - 1] if start > 0 else ""
            after = text[end] if end < size else ""
            # Jamais collé à un mot ni à « @ » (e-mail, accent) / never glued to a word or to "@".
            if before == "@" or after == "@" or (before and (before.isalnum() or before == "_")) or (
                    after and (after.isalnum() or after == "_")):
                continue
            if letter(text, start, end) is None:
                # Suite nue de 8 chiffres ou plus, sans séparateur (règle `ID_LONG_NUMBER`) ; une date, un montant,
                # une plage d'années portent un séparateur ou une exclusion. A bare run of 8 digits or more, with no
                # separator; dates, amounts and year ranges carry a separator or an exclusion.
                if end - start >= LONG_NUMBER_MIN and token.isdigit() and long_number_exclusion(
                        text, start, end) is None:
                    spans.append(Span(start, end, "ID", "ID", "ID_LONG_NUMBER", 0.8, PRIORITY_ID_CODE, token,
                                      reason="long_number"))
                continue
            # Balise déjà produite (« [IDENTIFIANT_12] ») : jamais relue comme un code / never read as a code.
            if before == "[" and after == "]" and _PLACEHOLDER_TOKEN.fullmatch(token):
                continue
            for piece, piece_start in _pieces(token, start):
                if is_code(piece) and exclusion(piece) is None:
                    spans.append(self._span(ctx, piece, piece_start))
        # Codes coupés par une espace, après les jetons (même ordre dans le jumeau Rust) / split codes, after tokens.
        for start, end, value in split_code_spans(text):
            spans.append(Span(start, end, "ID", "ID", self.id, 0.8, PRIORITY_ID_CODE, value, reason="identifier_code"))
        return spans

    def _span(self, ctx: Any, piece: str, start: int) -> Span:
        end, value = start + len(piece), piece.translate(_SEPARATORS).upper()
        return Span(start, end, "ID", "ID", self.id, 0.8, PRIORITY_ID_CODE, value, reason="identifier_code")

    def native_plan(self) -> dict[str, Any] | None:
        """Moteur fusionné : jumeau Rust (`rust/src/detectors/codes.rs`), mêmes zones, valeurs et exclusions,
        données de ce module ; un noyau sans jumeau (`code_twin`) garde l'appel Python.

        Fused engine: Rust twin, same spans, values and exclusions, this module's data; a core without the twin
        keeps the Python call.
        """
        core = _native.core()
        if core is None or not getattr(core, "code_twin", False):
            return None
        return {"kind": "codes",
                "code": Span(0, 0, "ID", "ID", self.id, 0.8, PRIORITY_ID_CODE, None, reason="identifier_code"),
                "long_number": Span(0, 0, "ID", "ID", "ID_LONG_NUMBER", 0.8, PRIORITY_ID_CODE, None,
                                    reason="long_number"),
                "cookie": Span(0, 0, "SECRET", "SECRET", "SECRET_COOKIE", 0.9, PRIORITY_STRUCTURAL, None,
                               reason="keyword"),
                "exclusions": [pattern.pattern for _, pattern in _EXCLUSIONS], "short_list": sorted(_SHORT_LIST),
                "months": list(_MONTHS), "bic_countries": sorted(IBAN_LENGTHS),
                "attributes": sorted(_COOKIE_ATTRIBUTES)}


# --- Longues suites de chiffres / long digit runs (règle `ID_LONG_NUMBER`) -------------------------------------------

LONG_NUMBER_MIN = 8
# Devise ou unité juste après (« 12500000 € », « 15000000 habitants » n'en est pas une) / currency or unit right after.
_AMOUNT_AFTER = re.compile(
    r"[ \t  ]?(?:€|\$|£|%|‰|(?:k|m|md)?(?:€|eur|euros?|usd|dollars?|gbp|chf|xpf|fcfa)(?![A-Za-z])"
    r"|(?:km|kg|mg|g|cm|mm|m2|m3|m²|m³|m|ml|cl|l|t|w|kw|kwh|mw|mwh|v|hz|octets?|bytes?|ko|mo|go|to|kb|mb|gb|tb)"
    r"(?![A-Za-z]))", re.IGNORECASE)
# Une devise en lettres est un mot entier : « Compteur 912345678 », « Débiteur 12345678 » ne sont pas des
# montants / a currency written in letters is a whole word: "Compteur 912345678" is not an amount.
_AMOUNT_BEFORE = re.compile(r"(?:€|\$|£|(?<![^\W\d_])(?:eur|euros?|usd|gbp|chf))[ \t  ]?\Z",
                            re.IGNORECASE)
# Durée d'un attribut de témoin (« Max-Age=31536000 ») / a cookie attribute's duration.
_DURATION_BEFORE = re.compile(r"max-age[ \t]*=[ \t]*\Z", re.IGNORECASE)
# Code de nomenclature après son libellé (« Code CPV : 37400000 », « NAF 4711000 ») : une classification, pas un
# identifiant / a nomenclature code after its label: a classification, not an identifier.
_CLASSIFICATION_BEFORE = re.compile(
    r"(?<![\w])(?:cpv|naf|ape|nace|nuts|rome|nomenclature)(?:[ \t]+(?:principal|code|n[°o]\.?))?[ \t]*[:=#]?[ \t]*"
    r"(?:\d+[ \t]*[,;/][ \t]*)*\Z", re.IGNORECASE)
# Numéro d'un bulletin officiel (« BODACC A n° 20260169 », « JORF n° 0123 ») : une publication, pas une personne.
# An official bulletin's number: a publication, not a person.
_PUBLICATION_BEFORE = re.compile(
    r"(?<![\w])(?:bodacc|balo|jorf|joafe|jo|bulletin(?:[ \t]+officiel)?|journal[ \t]+officiel)(?:[ \t]+[A-C])?"
    r"[ \t]+(?:n[°o]\.?|num[ée]ro)[ \t]*:?[ \t]*\Z", re.IGNORECASE)


def _compact_date(run: str) -> bool:
    """Date compacte AAAAMMJJ ou JJMMAAAA, ou horodatage AAAAMMJJhhmm(ss) / compact date or timestamp."""
    def valid(year: int, month: int, day: int) -> bool:
        return 1800 <= year <= 2199 and 1 <= month <= 12 and 1 <= day <= 31
    if len(run) == 8:
        return valid(int(run[:4]), int(run[4:6]), int(run[6:])) or valid(int(run[4:]), int(run[2:4]), int(run[:2]))
    if len(run) in (12, 14):
        return (valid(int(run[:4]), int(run[4:6]), int(run[6:8])) and int(run[8:10]) < 24 and int(run[10:12]) < 60
                and (len(run) == 12 or int(run[12:]) < 60))
    return False


def long_number_exclusion(text: str, start: int, end: int) -> str | None:
    """Nom de l'exclusion qui garde lisible la suite de chiffres `text[start:end]`, ou None.

    Name of the exclusion that keeps the digit run readable, or None: amount (currency or unit next to it, decimal
    or thousands form), compact date or timestamp.
    """
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    # Forme décimale ou de milliers (« 12345678,90 », « 1.234567890 ») / decimal or thousands form.
    if (after in ",." and end + 1 < len(text) and text[end + 1].isdigit()) or (
            before in ",." and start > 1 and text[start - 2].isdigit()):
        return "amount"
    if _AMOUNT_AFTER.match(text, end) or _AMOUNT_BEFORE.search(text, max(0, start - 6), start):
        return "amount"
    if _compact_date(text[start:end]):
        return "date"
    if _DURATION_BEFORE.search(text, max(0, start - 12), start):
        return "duration"
    if _CLASSIFICATION_BEFORE.search(text, max(0, start - 24), start):
        return "classification"
    if _PUBLICATION_BEFORE.search(text, max(0, start - 30), start):
        return "publication"
    return None


# --- En-têtes de témoins / cookie headers ---------------------------------------------------------------------------

_COOKIE_LINE = re.compile(r"(?im)^[ \t]*(?:set-)?cookie[ \t]*:[ \t]*([^\n]*)$")
_COOKIE_PAIR = re.compile(r"([^=;\s]+)[ \t]*=[ \t]*([^;\n]*)")
# Attributs de `Set-Cookie`, jamais des valeurs propres à une personne / `Set-Cookie` attributes, never personal.
_COOKIE_ATTRIBUTES = frozenset({"expires", "max-age", "domain", "path", "samesite", "secure", "httponly", "priority",
                                "partitioned", "version", "comment"})


def cookie_spans(ctx: Any) -> list[Span]:
    """Règle `SECRET_COOKIE` : sur une ligne `Cookie:` ou `Set-Cookie:`, chaque valeur `nom=valeur` de 8 caractères
    ou plus est un secret (raison `keyword`) ; les attributs (`Path`, `Expires`…) restent. Appelée par
    `IdentifierCodeDetector`, dans le même passage par Python.

    `SECRET_COOKIE` rule: on a `Cookie:` or `Set-Cookie:` line, every `name=value` value of 8 characters or more is
    a secret (reason `keyword`); attributes stay. Called by `IdentifierCodeDetector`, in the same Python trip.
    """
    if not ctx.has("cookie"):
        return []
    text = ctx.text
    spans: list[Span] = []
    for line in _COOKIE_LINE.finditer(text):
        for pair in _COOKIE_PAIR.finditer(text, line.start(1), line.end(1)):
            if pair.group(1).lower() in _COOKIE_ATTRIBUTES:
                continue
            start, end = pair.span(2)
            while end > start and text[end - 1] in " \t\r":
                end -= 1
            if end - start >= 8:
                spans.append(Span(start, end, "SECRET", "SECRET", "SECRET_COOKIE", 0.9, PRIORITY_STRUCTURAL,
                                  text[start:end], reason="keyword"))
    return spans
