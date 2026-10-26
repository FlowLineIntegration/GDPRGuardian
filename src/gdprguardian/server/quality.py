"""Qualité minimale du texte : repère un texte d'OCR dégradé, sans jamais le refuser / minimum text quality.

Un texte d'OCR de mauvaise qualité (mots déformés, césures cassées, symboles parasites) défait la détection : un nom
déformé n'est plus reconnu. Le service le signale par un avertissement, et traite le document quand même. A low-quality
OCR text defeats detection (a garbled name is no longer recognised): the service warns, and still processes it.

Mesure (texte converti, avant anonymisation, dans le travailleur ; échantillon borné) / measure (converted text, before
anonymisation, in the worker; bounded sample):
- part des mots en minuscules (3 lettres ou plus) absents des listes de mots et de noms du paquet ET dont un 4-gramme
  de lettres n'y apparaît jamais (« dlreîfetftèirt », « avrtl ») : une forme conjuguée absente de la liste (« avons »)
  reste plausible ; share of lowercase words unknown to the package's word and name lists AND holding a letter 4-gram
  never seen there; a conjugated form missing from the list stays plausible;
- mots d'une ou deux lettres hors mots-outils (« fJ », « aS ») et jetons mêlant chiffres et lettres ou casse
  incohérente (« l908 », « KJbFU »), césures cassées comprises / one- or two-letter non-function words and tokens
  mixing digits and letters or with inconsistent case, broken hyphenation included;
- codes en capitales et chiffres, noms de produits en casse chameau et sigles de deux capitales écartés (écriture
  propre de l'informatique et des affaires) / upper-case codes, camel-case product names and two-capital acronyms set
  aside (clean IT and business writing).

Appliquée aux seuls PDF : le produit ne fait pas d'OCR, un texte d'OCR n'arrive que par la couche texte d'un PDF ;
jamais au texte collé, aux e-mails ni aux documents bureautiques. Applied to PDFs only: the product does no OCR, so an
OCR text only arrives as a PDF text layer; never to pasted text, e-mails or office documents.

Étalonnage (moitiés « dev », vérifié sur les moitiés « test ») au seuil 0,12 : aucune fausse alerte sur ParlaMint,
Judilibre, MAPA (fr) et TAB (en), 0 à 0,1 % sur BODACC et BOAMP (1 à 2 documents sur 1 200 à 1 500) ; presse ancienne
signalée pour ses pages les plus dégradées (Europeana 12 à 13 %, HIPE 1,5 à 7 %). Langue : français et anglais
seulement (les listes du paquet ; un texte allemand ou néerlandais propre aurait l'air dégradé). Calibration (dev
halves, checked on test halves) at threshold 0.12: no false alarm on ParlaMint, Judilibre, MAPA (fr) and TAB (en),
0 to 0.1 % on BODACC and BOAMP; old press flagged for its most degraded pages (Europeana 12-13 %, HIPE 1.5-7 %).
Language: French and English only. Étalonnage mesuré avant l'exclusion des codes, noms de produits et sigles, qui ne
peut que baisser un score / calibration measured before codes, product names and acronyms were set aside, which can
only lower a score. Coût borné : échantillon de 200 000 caractères au plus, jetons de 64 caractères au
plus / bounded cost: 200,000-character sample at most, tokens of 64 characters at most.
"""

from __future__ import annotations

import re
import threading

from .._text import fold

LOW_QUALITY_WARNING = ("Texte de mauvaise qualité (OCR probable) : détection dégradée, relisez le résultat / "
                       "Low-quality text (likely OCR): degraded detection, check the result")
THRESHOLD = 0.12
# Langues couvertes par les listes du paquet / languages covered by the package's lists.
LANGUAGES = frozenset({"fr", "en"})
MIN_WORDS = 40                     # en deçà, aucune conclusion / below, no conclusion
_SAMPLE_WINDOWS = 8
_WINDOW_CHARS = 25_000
_GRAM = 4
_WORD_RE = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")
# Jetons bornés (au-delà : ignorés, jamais d'expression régulière sur un jeton géant) ; adresses, liens et balises
# écartés. Bounded tokens (longer ones ignored: no regex on a giant token); addresses, links, placeholders set aside.
_MAX_TOKEN = 64
_NOISE_RE = re.compile(r"@|/|^(?:https?:|www\.)|\.(?:fr|com|org|eu|net)\b|\[[A-Z_]+\d*\]", re.I)
_GARBLED_RE = re.compile(r"[a-zà-ÿ][A-ZÀ-Þ]|[^\W\d_]\d|\d[^\W\d_]{2,}")
_ORDINAL_RE = re.compile(r"\d+(?:er|e|ème|eme|es|re|nd|st|th|h\d*|min|km|kg|cm|mm|m²|ha)[.,;:)]?")
_BROKEN_HYPHEN_RE = re.compile(r"[^\W\d_]-[ \t]*\n[ \t]*[^\W\d_]")
_SPLIT_RE = re.compile(r"['-]")
# Écriture propre de l'informatique et des affaires, jamais comptée comme déformée : codes en capitales et chiffres
# (« EC2 », « SRV-PRD-WEB01 », « CHG0012877 »), noms de produits en casse chameau (« PowerPoint », « MySQL »,
# « gRPC », « vSphere ») et sigles de deux capitales (« DB », « RH »). Clean IT and business writing, never counted as
# garbled: upper-case codes with digits, camel-case product names and two-capital acronyms.
_EDGE_PUNCT = ".,;:()[]!?\"'«»“”"
_CODE_RE = re.compile(r"(?=[A-Z0-9_-]*\d)(?=[A-Z0-9_-]*[A-Z])[A-Z0-9]+(?:[-_][A-Z0-9]+)*")
_CAMEL_RE = re.compile(r"(?:[A-Z][a-z]+){2,}|[A-Z][a-z]+[A-Z]{2,}|[a-z][A-Z]{2,}|[a-z][A-Z][a-z]{3,}")
_SHORT_WORDS = frozenset({
    "a", "y", "l", "d", "j", "m", "n", "s", "t", "c", "qu", "de", "du", "la", "le", "un", "en", "et", "il", "ne",
    "se", "ce", "ou", "on", "au", "ma", "ta", "sa", "me", "te", "je", "tu", "mr", "mm", "dr", "st", "no", "si",
    "ni", "eu", "vu", "pu", "su", "lu", "of", "to", "in", "is", "it", "an", "as", "at", "be", "by", "he", "we",
    "or", "so", "do", "up", "us", "i", "e", "o", "x", "if", "my", "am", "ok", "vs", "ca"})


def _clean_token(token: str) -> bool:
    """Code, nom de produit ou sigle propre (voir plus haut) / clean code, product name or acronym (see above)."""
    core = token.strip(_EDGE_PUNCT)
    return bool(core) and (_CODE_RE.fullmatch(core) is not None or _CAMEL_RE.fullmatch(core) is not None
                           or (len(core) == 2 and core.isalpha() and core.isupper()))

_lock = threading.Lock()
_lists: tuple[frozenset[str], dict[str, int], frozenset[str], frozenset[str]] | None = None


def _resources() -> tuple[frozenset[str], dict[str, int], frozenset[str], frozenset[str]]:
    """Listes du paquet et 4-grammes de lettres, une fois par processus / package lists and letter 4-grams, once."""
    global _lists
    if _lists is None:
        with _lock:
            if _lists is None:
                from ..heuristics._lexicon import lexicon

                lexicon_ = lexicon()
                grams: set[str] = set()
                for entry in (*lexicon_.words, *lexicon_.names):
                    padded = f"^{entry}$"
                    grams.update(padded[i:i + _GRAM] for i in range(len(padded) - _GRAM + 1))
                _lists = (lexicon_.words, lexicon_.names, lexicon_.communes, frozenset(grams))
    return _lists


def prepare() -> None:
    """Préchargement (zygote) / preload (zygote)."""
    _resources()


def _sample(text: str) -> str:
    """Fenêtres réparties sur tout le texte, coût borné / windows spread over the whole text, bounded cost."""
    if len(text) <= _SAMPLE_WINDOWS * _WINDOW_CHARS:
        return text
    step = (len(text) - _WINDOW_CHARS) // (_SAMPLE_WINDOWS - 1)
    return "\n".join(text[i * step:i * step + _WINDOW_CHARS] for i in range(_SAMPLE_WINDOWS))


def quality_score(text: str) -> float | None:
    """Score de dégradation (0 : propre) ; None si le texte est trop court pour conclure.

    Degradation score (0: clean); None when the text is too short to conclude.
    """
    words_list, names, communes, grams = _resources()
    sample = _sample(text)
    tokens = [token for token in sample.split()
              if len(token) <= _MAX_TOKEN and not _NOISE_RE.search(token) and not _clean_token(token)]
    words = [word for token in tokens for word in _WORD_RE.findall(token)]
    long_words = [word for word in words if len(word) >= 3]
    if len(long_words) < MIN_WORDS:
        return None

    def known(key: str) -> bool:
        if key in words_list or key in names or key in communes:
            return True
        for part in _SPLIT_RE.split(key):
            if len(part) < 3 or part in words_list or part in names:
                continue
            padded = f"^{part}$"
            if any(padded[i:i + _GRAM] not in grams for i in range(len(padded) - _GRAM + 1)):
                return False
        return True

    lower = [word for word in long_words if word[0].islower()]
    implausible = sum(1 for word in lower if not known(fold(word).replace("’", "'")))
    junk = sum(1 for word in words if len(word) <= 2 and fold(word) not in _SHORT_WORDS)
    garbled = sum(1 for token in tokens if _GARBLED_RE.search(token) and not _ORDINAL_RE.fullmatch(token))
    garbled += len(_BROKEN_HYPHEN_RE.findall(sample))
    return (implausible / max(1, len(lower)) + 0.5 * junk / max(1, len(words))
            + 0.5 * garbled / max(1, len(tokens)))


def low_quality(text: str, language: object) -> bool:
    """Texte trop dégradé pour une bonne détection (français et anglais seulement) / too degraded (fr, en only)."""
    if language not in LANGUAGES:
        return False
    score = quality_score(text)
    return score is not None and score >= THRESHOLD


__all__ = ["LOW_QUALITY_WARNING", "THRESHOLD", "low_quality", "prepare", "quality_score"]
