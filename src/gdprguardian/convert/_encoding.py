"""Décodage des textes hérités / legacy text decoding.

Ordre : BOM, jeu déclaré, UTF-8 strict, UTF-8 tolérant (quelques octets parasites), puis
charset-normalizer. Pour les pages de code latines, charset-normalizer confond souvent cp1252 et
cp1250/cp1257 sur du français (« crčme ») : on départage alors par la vraisemblance des lettres accentuées.
Order: BOM, declared charset, strict UTF-8, lenient UTF-8 (a few stray bytes), then charset-normalizer.
For Latin code pages it often mistakes French cp1252 for cp1250/cp1257, so candidates are ranked by how
plausible the accented letters they yield are.
"""

from __future__ import annotations

import codecs
import re
import unicodedata
from collections import Counter
from functools import lru_cache

_BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"), (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"),
)
_ASCII = bytes(range(128))
_HIGH_RUN_RE = re.compile(rb"[\x80-\xff]{3,64}")
# Pages de code latines départagées, par ordre de préférence / Latin code pages ranked, in preference order.
_LATIN_CANDIDATES = ("cp1252", "cp1250", "cp1257", "cp1254")
_SCRIPT_CANDIDATES = ("cp1251", "cp1253", "cp1255", "cp1256")  # cyrillique, grec, hébreu, arabe
_EAST_ASIAN = frozenset({
    "big5", "big5hkscs", "cp932", "cp949", "cp950", "euc_jis_2004", "euc_jisx0213", "euc_jp", "euc_kr", "gb18030",
    "gb2312", "gbk", "hz", "iso2022_jp", "iso2022_kr", "johab", "shift_jis", "shift_jis_2004", "shift_jisx0213",
})
_LATIN_FAMILY = frozenset({
    "cp1252", "cp1250", "cp1257", "cp1254", "cp1258", "latin_1", "iso8859_2", "iso8859_3", "iso8859_4",
    "iso8859_9", "iso8859_10", "iso8859_13", "iso8859_14", "iso8859_15", "iso8859_16", "mac_latin2", "mac_roman",
    "mac_iceland", "mac_turkish", "cp437", "cp775", "cp850", "cp852", "cp858",
})
# Fréquence relative des caractères non ASCII dans les langues européennes / relative frequency of non-ASCII chars.
_WEIGHTS: dict[str, float] = {
    # Ouest / Western
    "é": 10, "è": 5, "à": 5, "ç": 2, "ê": 2, "ô": 1.5, "â": 1, "î": 1, "û": 0.8, "ù": 0.8, "ë": 0.5, "ï": 0.5,
    "ü": 3, "ö": 3, "ä": 3, "ß": 2, "ñ": 2, "á": 3, "í": 3, "ó": 3, "ú": 2, "ã": 1.5, "õ": 0.5, "ì": 0.5,
    "ò": 0.5, "ø": 1, "å": 1, "æ": 0.5, "œ": 1, "É": 1, "È": 0.5, "À": 0.5, "Ç": 0.3, "Ü": 0.5, "Ö": 0.5,
    "Ä": 0.5, "Ñ": 0.3, "Á": 0.3, "Í": 0.3, "Ó": 0.3, "Ú": 0.3, "Ê": 0.2, "Ô": 0.2, "Â": 0.2, "Î": 0.2, "Œ": 0.2,
    # Centre / Central
    "č": 3, "ř": 2, "ě": 2.5, "ů": 1, "š": 3, "ž": 2.5, "ý": 2, "ť": 0.5, "ď": 0.5, "ň": 0.5, "ł": 3, "ś": 1.5,
    "ź": 0.5, "ż": 1.5, "ą": 2, "ę": 2, "ń": 1.5, "ć": 1.5, "ő": 1.5, "ű": 0.5, "ş": 1, "ţ": 0.5, "ă": 1.5,
    "ľ": 0.5, "ĺ": 0.2, "ŕ": 0.1, "Č": 0.5, "Ř": 0.3, "Š": 0.5, "Ž": 0.5, "Ł": 0.5, "Ś": 0.3, "Ż": 0.3,
    # Baltique et turc / Baltic and Turkish
    "ā": 1.5, "ē": 1, "ī": 1, "ū": 1, "ė": 1, "į": 0.5, "ų": 0.5, "ķ": 0.3, "ļ": 0.3, "ņ": 0.5, "ģ": 0.2,
    "ı": 3, "ğ": 1.5, "İ": 0.5,
    # Typographie / typography
    "’": 1, "‘": 0.5, "“": 0.5, "”": 0.5, "–": 1, "—": 0.5, "…": 0.5,
    "€": 0.5, "«": 1, "»": 1, "°": 0.5, "\xa0": 0.5, "•": 0.5, "²": 0.2, "·": 0.2, "©": 0.1, "®": 0.1, "™": 0.1,
}


@lru_cache(maxsize=256)  # borné : l'étiquette vient du document / bounded: the label comes from the document
def _codec_name(label: str) -> str | None:
    """Nom canonique ; latin-1 et ASCII déclarés valent windows-1252 (norme WHATWG).

    Canonical name; declared latin-1 and ASCII mean windows-1252 (WHATWG encoding standard). Codecs that
    are not text encodings (« base64 », « rot13 », « hex »...) are refused: `bytes.decode` rejects them.
    """
    try:
        info = codecs.lookup(label.strip().strip("\"'"))
    except (LookupError, ValueError):
        return None
    if not getattr(info, "_is_text_encoding", True):  # drapeau lu par bytes.decode / flag checked by bytes.decode
        return None
    return "cp1252" if info.name in ("iso8859-1", "latin-1", "ascii") else info.name


def decode_text(data: bytes, declared: str | None = None) -> str:
    """Décode un texte d'encodage inconnu ; ne lève jamais / decodes text of unknown encoding; never raises."""
    for bom, codec in _BOMS:
        if data.startswith(bom):
            return data.decode(codec, errors="replace")
    codec = _codec_name(declared) if declared else None
    if codec is not None and codec != "utf-8":
        return data.decode(codec, errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass  # UTF-8 déclaré mais invalide : souvent du cp1252 mal étiqueté / mislabelled, often cp1252
    lenient = data.decode("utf-8", errors="replace")
    # UTF-8 à quelques octets parasites près : sinon tout le texte deviendrait illisible (« JĆ©rĆ´me »),
    # nom que la détection manquerait mais qu'un LLM lirait. UTF-8 but for a few stray bytes: otherwise
    # the whole text turns to mojibake, which detection misses but an LLM reads.
    bad = lenient.count("\N{REPLACEMENT CHARACTER}") - data.count("\N{REPLACEMENT CHARACTER}".encode())
    if bad * 5 <= len(data.translate(None, _ASCII)):  # au moins 4 octets valides par octet fautif / 4:1
        return lenient
    return _decode_legacy(data)


def _decode_legacy(data: bytes) -> str:
    from charset_normalizer import from_bytes

    best = from_bytes(data).best()
    if best is not None and best.encoding not in _LATIN_FAMILY and not _latin_script(data):
        if best.encoding not in _EAST_ASIAN or len(data[:1 << 20].translate(None, _ASCII)) >= 64:
            return str(best)
        # Texte court pris pour du chinois ou du japonais : page européenne d'abord.
        # Short text mistaken for Chinese or Japanese: European code pages first.
        codec = script_codec(data)
        return data.decode(codec, errors="replace") if codec else str(best)
    codec = latin_codec(data)
    if codec is None:
        return str(best) if best is not None else data.decode("cp1252", errors="replace")
    return data.decode(codec, errors="replace")


def script_codec(data: bytes) -> str | None:
    """Page de code non latine dont les lettres relèvent toutes d'une même écriture, ou None.

    Non-Latin code page whose letters all belong to a single script (Cyrillic, Greek...), or None.
    """
    counts = Counter(data[:1 << 20].translate(None, _ASCII))
    total = sum(counts.values())
    for codec in _SCRIPT_CANDIDATES:
        scripts: Counter[str] = Counter()
        try:
            for byte, count in counts.items():
                char = bytes((byte,)).decode(codec)
                if char.isalpha():
                    scripts[unicodedata.name(char, "?").split(" ", 1)[0]] += count
        except UnicodeDecodeError:
            continue  # octet non défini / undefined byte
        letters = sum(scripts.values())
        if letters >= 0.6 * total and scripts.most_common(1)[0][1] >= 0.95 * letters:
            return codec
    return None


def _latin_script(data: bytes) -> bool:
    """Écriture latine : octets hauts isolés dans des mots ASCII (« caf\\xe9 »), pas en longues suites.

    Latin script: high bytes isolated inside ASCII words ("caf\\xe9"), not in long runs (Cyrillic,
    Greek, Arabic words are entirely high bytes). Decided on the first MiB.
    """
    sample = data[:1 << 20]
    high = len(sample.translate(None, _ASCII))
    in_runs = sum(map(len, _HIGH_RUN_RE.findall(sample)))
    return high > 0 and in_runs * 2 < high


def latin_codec(data: bytes) -> str | None:
    """Page de code latine la plus vraisemblable, ou None / most plausible Latin code page, or None."""
    counts = Counter(data.translate(None, _ASCII))
    if not counts:
        return "cp1252"
    best_codec, best_score = None, float("-inf")
    for codec in _LATIN_CANDIDATES:
        score = 0.0
        for byte, count in counts.items():
            try:
                char = bytes((byte,)).decode(codec)
            except UnicodeDecodeError:
                break  # octet non défini : candidat éliminé / undefined byte: candidate rejected
            score += count * _WEIGHTS.get(char, 0.1 if char.isalpha() else -1.0)
        else:
            if score > best_score:
                best_codec, best_score = codec, score
    return best_codec


__all__ = ["decode_text", "latin_codec", "script_codec"]
