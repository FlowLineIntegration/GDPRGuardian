"""Mutations « équipe rouge » appliquées aux zones annotées / red-team mutations applied to gold spans.

Chaque opérateur réécrit les mentions éligibles d'un document ; le texte est recomposé par
concaténation et les positions recalculées, chaque zone touchée portant le nom de l'opérateur.
Each operator rewrites the eligible mentions of a document; the text is rebuilt by concatenation,
offsets are recomputed and each touched span records the operator name (recall per operator).

Usage : python -m tools.eval.mutate --in corpus.jsonl --out mutated.jsonl [--only nbsp,zero_width]
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from random import Random

if __package__ in (None, ""):  # lancé comme script / run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.eval.schema import GOLD_LABELS, NO_MASK, Document, GoldSpan, read_jsonl, write_jsonl

Rewrite = Callable[[str, Random], "str | None"]

PII_LABELS = frozenset(label for label, kind in GOLD_LABELS.items() if kind != NO_MASK)
NUMERIC = frozenset({"NIR", "IBAN", "RIB", "RIB_SPLIT", "CARD", "PHONE", "SIRET", "SIREN", "VAT", "TAX_ID", "RPPS",
                     "CAF", "FRANCE_TRAVAIL", "PASSPORT", "ID_CARD", "PLATE", "ID"})
TEXTUAL = frozenset({"PERSON", "ADDRESS", "LOCATION", "ORG"})
EMAIL = frozenset({"EMAIL"})
_SEPARATORS_RE = re.compile(r"[ .\-]+")
_GROUPS_RE = re.compile(r"[^ .\-]+")
_WORD4_RE = re.compile(r"[^\W\d_]{4,}")


@dataclass(frozen=True, slots=True)
class Mutation:
    """Opérateur de mutation / mutation operator."""

    name: str
    family: str
    labels: frozenset[str]
    rewrite: Rewrite
    description: str

    def __call__(self, value: str, rng: Random) -> str | None:
        """Valeur mutée, ou None si l'opérateur ne s'applique pas / mutated value or None."""
        result = self.rewrite(value, rng)
        return result if result is not None and result != value else None


# --- Briques / building blocks -----------------------------------------------------------------------


def _replace(old: str, new: str) -> Rewrite:
    return lambda value, _rng: value.replace(old, new) if old in value else None


def _interior(value: str, rng: Random, count: int) -> list[int]:
    """Positions internes (entre deux caractères) / interior positions (between two characters)."""
    if len(value) < 2:
        return []
    return sorted(rng.sample(range(1, len(value)), min(count, len(value) - 1)))


def _insert(char: str, count: int = 3) -> Rewrite:
    def rewrite(value: str, rng: Random) -> str | None:
        positions = _interior(value, rng, count)
        if not positions:
            return None
        pieces, last = [], 0
        for pos in positions:
            pieces += [value[last:pos], char]
            last = pos
        pieces.append(value[last:])
        return "".join(pieces)

    return rewrite


def _wrap(prefix: str, suffix: str) -> Rewrite:
    return lambda value, _rng: f"{prefix}{value}{suffix}"


def _translate(table: dict[int, str]) -> Rewrite:
    return lambda value, _rng: value.translate(table)


def _digit_table(zero: int) -> dict[int, str]:
    return {ord("0") + i: chr(zero + i) for i in range(10)}


def _partial(mapping: dict[str, str], share: float = 0.5) -> Rewrite:
    """Remplace une partie des lettres éligibles (au moins une) / replaces part of the eligible letters."""

    def rewrite(value: str, rng: Random) -> str | None:
        eligible = [i for i, ch in enumerate(value) if ch in mapping]
        if not eligible:
            return None
        chosen = {i for i in eligible if rng.random() < share} or {rng.choice(eligible)}
        return "".join(mapping[ch] if i in chosen else ch for i, ch in enumerate(value))

    return rewrite


def _regroup(separator: str, irregular: bool = False) -> Rewrite:
    """Change les séparateurs entre groupes ; recoupe une valeur compacte / changes group separators."""

    def rewrite(value: str, rng: Random) -> str | None:
        groups = _GROUPS_RE.findall(value)
        if irregular or len(groups) == 1:
            flat, groups, pos = "".join(groups), [], 0
            while pos < len(flat):
                size = rng.randint(2, 5)
                groups.append(flat[pos:pos + size])
                pos += size
        return separator.join(groups) if len(groups) > 1 else None

    return rewrite


def _compact(value: str, _rng: Random) -> str | None:
    return _SEPARATORS_RE.sub("", value)


def _line_break(breaker: str) -> Rewrite:
    """Coupe la valeur à un séparateur (ou au milieu) / breaks the value at a separator (or mid-way)."""

    def rewrite(value: str, rng: Random) -> str | None:
        if len(value) < 6:
            return None
        spaces = [i for i, ch in enumerate(value) if ch == " "]
        if spaces:
            pos = rng.choice(spaces)
            return value[:pos] + breaker + value[pos + 1:]
        pos = rng.randint(2, len(value) - 2)
        return value[:pos] + breaker + value[pos:]

    return rewrite


_OCR = {"0": "O", "1": "l", "5": "S", "8": "B"}


def _ocr(value: str, rng: Random) -> str | None:
    """Une seule confusion de reconnaissance optique / a single OCR confusion."""
    positions = [i for i, ch in enumerate(value) if ch in _OCR]
    if not positions:
        return None
    pos = rng.choice(positions)
    return value[:pos] + _OCR[value[pos]] + value[pos + 1:]


def _strip_accents(value: str, _rng: Random) -> str | None:
    decomposed = unicodedata.normalize("NFD", value)
    return unicodedata.normalize("NFC", "".join(c for c in decomposed if not unicodedata.combining(c)))


def _nfd(value: str, _rng: Random) -> str | None:
    return unicodedata.normalize("NFD", value)


def _letter_spacing(value: str, _rng: Random) -> str | None:
    """« Jean » -> « J e a n » (titres espacés extraits d'un PDF) / letter-spaced PDF headings."""
    return " ".join(value) if len(value) > 1 else None


def _pdf_hyphenation(value: str, rng: Random) -> str | None:
    """Coupure de fin de ligne d'un PDF dans un mot : « Du-\\npont » / PDF end-of-line hyphenation."""
    words = list(_WORD4_RE.finditer(value))
    if not words:
        return None
    word = rng.choice(words)
    cut = rng.randint(word.start() + 2, word.end() - 2)
    return f"{value[:cut]}-\n{value[cut:]}"


def _surname_first(value: str, _rng: Random) -> str | None:
    """« Jean Dupont » -> « DUPONT Jean » (formes « Prénom Nom » uniquement / given-name-first only)."""
    given, _, surname = value.partition(" ")
    if not surname or given.isupper() or surname.isupper() or given.endswith(".") or not given[:1].isupper():
        return None
    return f"{surname.upper()} {given}"


def _email_at(replacement: str) -> Rewrite:
    return lambda value, _rng: value.replace("@", replacement) if value.count("@") == 1 else None


def _email_dots(replacement: str) -> Rewrite:
    """Remplace les points du domaine / replaces the domain dots."""

    def rewrite(value: str, _rng: Random) -> str | None:
        local, at, domain = value.rpartition("@")
        return f"{local}{at}{domain.replace('.', replacement)}" if at else None

    return rewrite


_FULLWIDTH = {cp: chr(cp + 0xFEE0) for cp in range(0x21, 0x7F)}
_MATH_BOLD = {
    **{ord("A") + i: chr(0x1D400 + i) for i in range(26)},
    **{ord("a") + i: chr(0x1D41A + i) for i in range(26)},
    **_digit_table(0x1D7CE),
}
_SUPERSCRIPT = {ord(d): s for d, s in zip("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹", strict=True)}
# Sosies cyrilliques et grecs (UTS #39) / Cyrillic and Greek look-alikes (UTS #39 confusables).
_CYRILLIC = dict(zip("aceopxyijsABEKMHOPCTXdhl", "асеорхуіјѕАВЕКМНОРСТХԁһӏ", strict=True))
_GREEK = dict(zip("ABEZHIKMNOPTYXo", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧο", strict=True))

_ANY = PII_LABELS
_SPACED = NUMERIC | TEXTUAL
_DIGITS = NUMERIC | frozenset({"ADDRESS", "EMAIL", "IP"})

# Caractères invisibles, d'espacement ou sosies toujours en échappements \uXXXX (lisibles en revue).
# Invisible, spacing and look-alike characters are always written as \uXXXX escapes (reviewable).
MUTATIONS: tuple[Mutation, ...] = (
    # Espaces Unicode / Unicode spaces
    Mutation("nbsp", "unicode-space", _SPACED, _replace(" ", "\u00a0"), "espace insécable U+00A0"),
    Mutation("narrow_nbsp", "unicode-space", _SPACED, _replace(" ", "\u202f"), "espace fine insécable U+202F"),
    Mutation("thin_space", "unicode-space", _SPACED, _replace(" ", "\u2009"), "espace fine U+2009"),
    Mutation("figure_space", "unicode-space", _SPACED, _replace(" ", "\u2007"), "espace tabulaire U+2007"),
    Mutation("ideographic_space", "unicode-space", _SPACED, _replace(" ", "\u3000"), "espace idéographique U+3000"),
    # Caractères invisibles / invisible characters
    Mutation("zero_width_space", "invisible", _ANY, _insert("\u200b"), "U+200B insérés dans la valeur"),
    Mutation("zero_width_joiner", "invisible", _ANY, _insert("\u200d"), "U+200D insérés"),
    Mutation("word_joiner", "invisible", _ANY, _insert("\u2060"), "U+2060 insérés"),
    Mutation("bom", "invisible", _ANY, _insert("\ufeff"), "U+FEFF insérés"),
    Mutation("soft_hyphen", "invisible", _ANY, _insert("\u00ad"), "trait d'union conditionnel U+00AD"),
    Mutation("bidi_mark", "invisible", _ANY, _insert("\u200e"), "marque gauche-droite U+200E"),
    Mutation("bidi_isolate", "invisible", _ANY, _wrap("\u2066", "\u2069"), "isolat bidi U+2066…U+2069"),
    Mutation("tag_chars", "invisible", _ANY, _insert("\U000e0041"), "caractères d'étiquette U+E0041"),
    Mutation("variation_selector", "invisible", _ANY, _insert("\ufe0f"), "sélecteur de variante U+FE0F"),
    Mutation("grapheme_joiner", "invisible", _ANY, _insert("\u034f"), "U+034F (combinant invisible)"),
    Mutation("hangul_filler", "invisible", _ANY, _insert("\u3164"), "remplisseur hangul U+3164 (lettre invisible)"),
    # Chiffres et lettres de substitution / substitute digits and letters
    Mutation("fullwidth", "digits", _DIGITS | TEXTUAL, _translate(_FULLWIDTH), "pleine chasse U+FF01…U+FF5E"),
    Mutation("math_bold", "digits", _DIGITS | TEXTUAL, _translate(_MATH_BOLD), "alphanumériques mathématiques gras"),
    Mutation("arabic_indic", "digits", _DIGITS, _translate(_digit_table(0x0660)), "chiffres arabo-indiens U+0660"),
    Mutation("devanagari", "digits", _DIGITS, _translate(_digit_table(0x0966)), "chiffres dévanagaris U+0966"),
    Mutation("superscript", "digits", _DIGITS, _translate(_SUPERSCRIPT), "chiffres en exposant (²…)"),
    Mutation("cyrillic", "homoglyph", TEXTUAL | EMAIL | frozenset({"PLATE", "IBAN"}), _partial(_CYRILLIC),
             "sosies cyrilliques"),
    Mutation("greek", "homoglyph", TEXTUAL | EMAIL | frozenset({"PLATE", "IBAN"}), _partial(_GREEK),
             "sosies grecs (majuscules)"),
    Mutation("nb_hyphen", "unicode-dash", _ANY, _replace("-", "\u2011"), "trait d'union insécable U+2011"),
    Mutation("en_dash_groups", "unicode-dash", NUMERIC, _regroup("\u2013"), "groupes séparés par U+2013"),
    # Séparateurs ASCII / ASCII separators
    Mutation("dots", "ascii-separator", NUMERIC, _regroup("."), "groupes séparés par des points"),
    Mutation("hyphens", "ascii-separator", NUMERIC, _regroup("-"), "groupes séparés par des tirets"),
    Mutation("slashes", "ascii-separator", NUMERIC, _regroup("/"), "groupes séparés par des barres obliques"),
    Mutation("double_space", "ascii-separator", NUMERIC, _regroup("  "), "doubles espaces entre groupes"),
    Mutation("compact", "ascii-separator", NUMERIC, _compact, "séparateurs supprimés"),
    Mutation("regroup", "ascii-separator", NUMERIC, _regroup(" ", irregular=True), "regroupement irrégulier"),
    # Mise en page / layout
    Mutation("line_break", "layout", _ANY, _line_break("\n"), "retour à la ligne dans la valeur"),
    Mutation("crlf", "layout", _ANY, _line_break("\r\n"), "CRLF dans la valeur"),
    Mutation("tab", "layout", _SPACED, _replace(" ", "\t"), "tabulations au lieu d'espaces"),
    Mutation("letter_spacing", "layout", _SPACED | EMAIL, _letter_spacing, "lettres espacées « J e a n » (PDF)"),
    Mutation("pdf_hyphenation", "layout", TEXTUAL, _pdf_hyphenation, "coupure « Du-\\npont » en fin de ligne (PDF)"),
    Mutation("markdown_bold", "layout", _ANY, _wrap("**", "**"), "valeur en gras Markdown « **…** »"),
    # Reconnaissance optique / OCR
    Mutation("ocr", "ocr", NUMERIC, _ocr, "une confusion OCR (0/O, 1/l, 5/S, 8/B)"),
    # Casse et accents / case and accents
    Mutation("upper", "case", TEXTUAL | EMAIL, lambda v, _r: v.upper(), "tout en majuscules"),
    Mutation("lower", "case", TEXTUAL | EMAIL, lambda v, _r: v.lower(), "tout en minuscules"),
    Mutation("surname_first", "case", frozenset({"PERSON"}), _surname_first, "« NOM Prénom »"),
    Mutation("strip_accents", "accents", TEXTUAL, _strip_accents, "accents retirés"),
    Mutation("nfd", "accents", TEXTUAL, _nfd, "accents décomposés (NFD)"),
    # Courriels maquillés / obfuscated e-mails
    Mutation("at_brackets", "email", EMAIL, _email_at(" [at] "), "« [at] »"),
    Mutation("at_parens", "email", EMAIL, _email_at("(at)"), "« (at) »"),
    Mutation("arobase", "email", EMAIL, _email_at(" arobase "), "« arobase »"),
    Mutation("at_entity", "email", EMAIL, _email_at("&#64;"), "entité HTML &#64;"),
    Mutation("at_percent", "email", EMAIL, _email_at("%40"), "encodage URL %40"),
    Mutation("at_fullwidth", "email", EMAIL, _email_at("\uff20"), "arobase pleine chasse U+FF20"),
    Mutation("dot_brackets", "email", EMAIL, _email_dots(" [dot] "), "« [dot] » dans le domaine"),
    Mutation("dot_point", "email", EMAIL, _email_dots("(point)"), "« (point) » dans le domaine"),
)
MUTATIONS_BY_NAME: dict[str, Mutation] = {m.name: m for m in MUTATIONS}


def mutate_document(doc: Document, mutation: Mutation, rng: Random) -> Document | None:
    """Applique l'opérateur à toutes les zones éligibles ; None si rien ne change / None if nothing changes."""
    text = doc.text
    parts: list[str] = []
    spans: list[GoldSpan] = []
    cursor = position = changed = 0
    for span in doc.spans:
        parts.append(text[cursor:span.start])
        position += span.start - cursor
        value = text[span.start:span.end]
        tag = None
        if span.label in mutation.labels:
            mutated = mutation(value, rng)
            if mutated is not None:
                value, tag = mutated, mutation.name
                changed += 1
        spans.append(GoldSpan(position, position + len(value), span.label, span.entity_id, span.identifier_type, tag))
        parts.append(value)
        position += len(value)
        cursor = span.end
    if not changed:
        return None
    parts.append(text[cursor:])
    mutated_doc = Document(f"{doc.doc_id}~{mutation.name}", doc.kind, "".join(parts), tuple(spans), doc.language,
                           mutation.name, {**doc.meta, "base": doc.doc_id})
    mutated_doc.check()
    return mutated_doc


def mutate_corpus(docs: Iterable[Document], mutations: Iterable[Mutation] = MUTATIONS,
                  seed: int = 0) -> Iterator[Document]:
    """Chaque opérateur sur chaque document (graine par couple) / every operator on every document."""
    base = list(docs)
    for mutation in mutations:
        for doc in base:
            mutated = mutate_document(doc, mutation, Random(f"{seed}/{mutation.name}/{doc.doc_id}"))
            if mutated is not None:
                yield mutated


def select(names: str | None) -> tuple[Mutation, ...]:
    if not names:
        return MUTATIONS
    chosen = [n.strip() for n in names.split(",") if n.strip()]
    unknown = [n for n in chosen if n not in MUTATIONS_BY_NAME]
    if unknown:
        raise ValueError(f"opérateurs inconnus / unknown operators: {unknown}")
    return tuple(MUTATIONS_BY_NAME[n] for n in chosen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mutations équipe rouge / red-team mutations (JSONL -> JSONL)")
    parser.add_argument("--in", dest="source", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--only", default=None, help="opérateurs séparés par des virgules / comma-separated")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--list", action="store_true", help="liste les opérateurs / list operators")
    args = parser.parse_args(argv)
    if args.list:
        for m in MUTATIONS:
            print(f"{m.name:20} {m.family:16} {m.description}")
        return 0
    if args.source is None or args.out is None:
        parser.error("--in et --out sont requis / --in and --out are required")
    try:
        mutations = select(args.only)
    except ValueError as error:
        parser.error(str(error))
    count = write_jsonl(mutate_corpus(read_jsonl(args.source), mutations, args.seed), args.out)
    print(f"{count} documents mutés / mutated -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
