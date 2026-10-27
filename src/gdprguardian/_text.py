"""Outils texte bas niveau / Low-level text helpers.

Toutes les transformations sont faites en code C (`str.translate`, regex) et préservent la longueur,
sauf la suppression des caractères invisibles, des césures de fin de ligne et des blancs en trop entre deux
groupes d'un identifiant (règle GAP), qui produit une table de positions. All transforms run in C code and
keep the length, except removing invisible characters, end-of-line hyphenation and extra blanks between two
groups of an identifier (GAP rule), which yields an offset map.

Ces fonctions sont la référence. `prepare(text, native=True)` en fait autant en un appel Rust, construit
à partir des tables de ce module (mêmes résultats, prouvés par tests différentiels). These functions are
the reference; `prepare(text, native=True)` does the same in one Rust call built from this module's tables.
"""

from __future__ import annotations

import re
import unicodedata
from array import array
from functools import cache
from itertools import pairwise
from typing import Any

# Séparateur de groupes de chiffres après normalisation / digit-group separator after normalisation.
SEP = r"[ .\-]"

# Caractères invisibles ou ignorables par défaut (Unicode), retirés avant détection : un seul suffirait à
# cacher un identifiant. Invisible or default-ignorable characters, removed before detection: a single
# one would hide an identifier (soft hyphen, ZW*, bidi, word joiners, Hangul fillers, variation selectors, tags).
INVISIBLE_RE = re.compile(
    "[­͏؜ᅟᅠ឴឵᠋-᠏​-‏‪-‮⁠-⁤"
    "⁦-⁯ㅤ︀-️﻿ﾠ\U0001bca0-\U0001bca3\U000e0000-\U000e0fff]"
)
# Césure de fin de ligne entre deux lettres (PDF) / end-of-line hyphenation between two letters (PDF).
_HYPHEN_BREAK_RE = re.compile(r"-(?<=[^\W\d_]-)[ \t]{0,2}\r?\n[ \t]{0,2}(?=[^\W\d_])")
# Gras Markdown hors d'un mot (« **N° client :** ») : remplacé par des espaces, longueur gardée. Motif
# sans assertion en tête (3x plus rapide), le contrôle du mot se fait dans `_unbold`.
# Markdown bold outside a word: replaced by spaces, length kept. No leading assertion (3x faster).
_EMPHASIS_RE = re.compile(r"[*_]{2,3}")
# Blancs entre deux groupes d'un identifiant, ramenés à une espace (règle GAP, docs/REGLES.md) : tabulation ou
# 2 à 4 blancs entre deux alphanumériques ASCII dont un chiffre (« 06\t12 », « 1  85 ») ; un seul saut de ligne
# entre deux chiffres (« 709\r\n590 »), groupes voisins de 12 caractères au plus (une ligne MRZ reste une ligne).
# Blanks between two groups of an identifier become one space (GAP rule): a tab or 2 to 4 blanks between two
# ASCII alphanumerics, one of them a digit; a single line break between two digits, neighbouring groups of at
# most 12 characters (an MRZ line stays a line).
_GAP_BLANKS_RE = re.compile(r"[ \t]*(?:\t|  )[ \t]*")
_GAP_BREAK_RE = re.compile(r"[0-9]([ \t]{0,3}\r?\n[ \t]{0,3})(?=[0-9])")
_GAP_GROUP = 12
# Groupes séparés par « / » (4 au moins) ou « . » (5 au moins), chacun de 1 à 6 majuscules ou chiffres dont un
# chiffre (« 06/12/34/56/78 », « FR76.3000.4065.0400.7691.1357.791 ») : séparateurs -> espaces, longueur gardée.
# Une date (3 groupes) ou une IPv4 (4 groupes) reste intacte. Groups split by "/" (4 or more) or "." (5 or more),
# each 1 to 6 capitals or digits with a digit: separators -> spaces, length kept. Dates and IPv4 stay intact.
_SEP_RUNS = (("/", re.compile(r"(?:[0-9A-Z]{1,6}/){3,}[0-9A-Z]{1,6}")),
             (".", re.compile(r"(?:[0-9A-Z]{1,6}\.){4,}[0-9A-Z]{1,6}")))
# Saut de ligne (LF ou CRLF, sans blanc autour) À L'INTÉRIEUR d'un identifiant, règle BREAK (docs/REGLES.md) : un
# courriel coupé par un client de messagerie (« jean.du⏎pont@x.fr », « jean@exem⏎ple.fr ») ou un IBAN collé
# (« FR76300…⏎…855 ») sont recollés ; un numéro alphanumérique (« 47CY⏎74524 ») devient deux groupes séparés par une
# espace. Deux lignes distinctes ne sont jamais recollées : chaque côté doit être un morceau du même identifiant
# (courriel incomplet d'un côté, complet une fois recollé ; groupes en majuscules et chiffres, chacun avec un chiffre).
# A line break INSIDE an identifier (BREAK rule): a wrapped e-mail or a pasted IBAN is joined back; an alphanumeric
# number becomes two space-separated groups. Two separate lines are never joined: each side must be a piece of the
# same identifier (an e-mail incomplete on one side and complete once joined; capital-and-digit groups, each with
# a digit).
_BREAK_RE = re.compile(r"(?<=[0-9A-Za-z._%+@\-])\r?\n(?=[0-9A-Za-z._%+@\-])")
_EMAIL_PART = frozenset("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz._%+-@")
_DOMAIN_RE = re.compile(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_IBAN_HEAD_RE = re.compile(r"[A-Z]{2}[0-9]{2}[0-9A-Z]*")
_BREAK_GROUP = 12
_BREAK_LOCAL = 7
# Lettres espacées d'un PDF copié (« J e a n   D u p o n t », « 0 6   1 2 ») : suite d'au moins trois caractères
# isolés (lettre, chiffre ou @ . _ - ' + , ( ), sans lettre ni chiffre collé) séparés par une espace, mots séparés
# par 2 à 4 espaces. Les espaces simples sont retirées, un séparateur de mots devient une espace. Une minuscule
# suivie d'une majuscule coupe la suite (« à J e a n » : « à » reste un mot). Lue sur le texte d'avant les
# remplacements GAP et « / » : un saut de ligne coupe toujours la suite. Letter spacing from a copied PDF: runs of
# at least three single characters separated by one space, words separated by 2 to 4 spaces; single spaces are
# removed, a word separator becomes one space. A lowercase letter followed by a capital splits the run. Read on the
# text before the GAP and "/" swaps: a line break always ends the run.
# Revue du 26/10 : seuls les lettres et chiffres comptent ; un bloc en compte au moins quatre, ou trois pour un mot
# capitalisé (« Z o é ») ; « il y a l' », « (89330), 4 B Rue » restent tels quels et « 4 à 6 » (chiffre, à/a,
# chiffre) n'est jamais recollé. Review of 26/10: only letters and digits count; a block holds at least four, or
# three for a capitalised word; a digit, à/a, digit range is never collapsed.
_SPACED_RE = re.compile(r"(?<!\w)[\w@.\-'+,()](?: {1,4}[\w@.\-'+,()](?!\w)){2,}")
# Pré-test bon marché, condition nécessaire d'une suite / cheap pre-check, a necessary condition for a run.
_SPACED_HINT_RE = re.compile(r" [\w@.\-'+,()] {1,4}[\w@.\-'+,()](?!\w)")
_SPACED_MIN = 4
_SPACED_MARKS = "@.-'+,()"


def _build_normalize_table() -> dict[int, int]:
    table: dict[int, int] = {}
    # Espaces Unicode -> espace / Unicode spaces -> space
    for cp in (0x00A0, 0x1680, *range(0x2000, 0x200B), 0x202F, 0x205F, 0x3000):
        table[cp] = 0x20
    # Tirets -> '-' / dashes -> '-'
    for cp in (*range(0x2010, 0x2016), 0x2212, 0xFE58, 0xFE63):
        table[cp] = 0x2D
    for cp in (0x2018, 0x2019, 0x02BC, 0x2032):
        table[cp] = 0x27
    table[0x2028] = table[0x2029] = 0x0A
    # Pleine chasse -> ASCII (chiffres, lettres, '@') / fullwidth -> ASCII
    for cp in range(0xFF01, 0xFF5F):
        table[cp] = cp - 0xFF01 + 0x21
    # Chiffres décimaux Unicode -> ASCII / Unicode decimal digits -> ASCII
    starts = (0x0660, 0x06F0, 0x07C0, 0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66,
              0x0CE6, 0x0D66, 0x0DE6, 0x0E50, 0x0ED0, 0x0F20, 0x1040, 0x1090, 0x17E0, 0x1810,
              0x1D7CE, 0x1D7D8, 0x1D7E2, 0x1D7EC, 0x1D7F6)
    for start in starts:
        for i in range(10):
            table[start + i] = 0x30 + i
    # Homoglyphes cyrilliques et grecs courants / common Cyrillic and Greek look-alikes
    for src, dst in zip("АВЕКМНОРСТХаеорсухіјѕΑΒΕΖΗΙΚΜΝΟΡΤΥΧο", "ABEKMHOPCTXaeopcyxijsABEZHIKMNOPTYXo",
                        strict=True):
        table[ord(src)] = ord(dst)
    return table


def _build_fold_table() -> dict[int, int]:
    """Minuscules sans accents, longueur préservée / lowercase without accents, length-preserving."""
    table: dict[int, int] = {cp: cp + 32 for cp in range(0x41, 0x5B)}
    for cp in range(0xC0, 0x250):
        ch = chr(cp)
        base = unicodedata.normalize("NFD", ch)[0]
        if base.isascii() and base.isalpha():
            table[cp] = ord(base.lower())
    for src, dst in zip("ŒœÆæØøĐđŁłÐð", "ooaaooddlldd", strict=True):
        table[ord(src)] = ord(dst)
    table[0x2019] = 0x27
    table[0x00BA] = 0x00B0  # 'nº' -> 'n°'
    return table


NORMALIZE_TABLE = _build_normalize_table()
FOLD_TABLE = _build_fold_table()


def _dense_bmp(table: dict[int, int]) -> str:
    """Table dense (chaîne de 65 536 caractères) : 4x plus rapide qu'un dict pour `str.translate`.

    Dense table (65,536-char string): 4x faster than a dict for `str.translate`.
    """
    chars = [chr(cp) for cp in range(0x10000)]
    for cp, target in table.items():
        if cp < 0x10000:
            chars[cp] = chr(target)
    return "".join(chars)


_NORMALIZE_BMP = _dense_bmp(NORMALIZE_TABLE)
_FOLD_BMP = _dense_bmp(FOLD_TABLE)
_ASTRAL_NORMALIZE = {cp: target for cp, target in NORMALIZE_TABLE.items() if cp >= 0x10000}
_ASTRAL_RE = re.compile("[\U00010000-\U0010ffff]")


_ASCII_ALNUM = frozenset("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
_ASCII_DIGITS = frozenset("0123456789")
_ASCII_LETTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
_UPPER_LETTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _group_longer(text: str, start: int, step: int) -> bool:
    """Plus de `_GAP_GROUP` alphanumériques ASCII à partir de `start` (vers la gauche si `step` = -1) ?

    More than `_GAP_GROUP` ASCII alphanumerics from `start` (leftwards when `step` is -1)?
    """
    i = start if step > 0 else start - 1
    for _ in range(_GAP_GROUP + 1):
        if not 0 <= i < len(text) or text[i] not in _ASCII_ALNUM:
            return False
        i += step
    return True


def _delimited_row(text: str, pos: int) -> bool:
    """La ligne qui commence en `pos` porte-t-elle au moins deux « ; », tabulations ou « , » d'une même sorte ?
    Une ligne de tableau CSV n'est jamais recollée à la précédente par GAP (1.0.2). Does the line starting at `pos`
    hold two or more ";", tabs or "," of one kind? A CSV row is never joined to the previous one by GAP.
    """
    end = text.find("\n", pos)
    line = text[pos:] if end < 0 else text[pos:end]
    return any(line.count(d) >= 2 for d in (";", "\t", ","))


def _tab_row(text: str, pos: int) -> bool:
    """La ligne de `pos` est une ligne (en-tête compris) d'un tableau TSV que `delimited_tables` reconnaît (en-tête
    aux cellules d'étiquette, puis au moins deux lignes de même nombre de tabulations) : ses tabulations restent des
    séparateurs de colonnes (1.0.2). Une prose dont les espaces sont des tabulations n'est pas un tableau (revue du
    26/10). The line of `pos` is a row (header included) of a TSV table `delimited_tables` finds: its tabs stay
    column separators. Prose whose spaces are tabs is not a table.
    """
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    end = len(text) if end < 0 else end
    tabs = text.count("\t", start, end)
    if tabs < 2:
        return False
    # Condition nécessaire, bon marché : une ligne voisine porte autant de tabulations. Cheap necessary condition.
    if not (start > 0 and text.count("\t", text.rfind("\n", 0, start - 1) + 1, start - 1) == tabs):
        if end >= len(text):
            return False
        after = text.find("\n", end + 1)
        if text.count("\t", end + 1, len(text) if after < 0 else after) != tabs:
            return False
    return start in _tab_table_rows(text)


# Lignes des tableaux TSV du dernier texte lu : (longueur, empreinte `hash`) -> débuts de ligne. Le texte lui-même
# n'est pas gardé. Rows of the last text's TSV tables, keyed by length and `hash`; the text itself is not kept.
_TAB_ROWS: list[tuple[tuple[int, int], frozenset[int]]] = []


def _tab_table_rows(text: str) -> frozenset[int]:
    """Débuts des lignes des tableaux TSV de `delimited_tables` / line starts of `delimited_tables`' TSV tables."""
    key = (len(text), hash(text))
    cached = _TAB_ROWS[-1] if _TAB_ROWS else None
    if cached is not None and cached[0] == key:
        return cached[1]
    rows = frozenset(start for delimiter, lines in _table_scan(text) if delimiter == "\t" for start, _ in lines)
    _TAB_ROWS[:] = [(key, rows)]
    return rows


# Numéro de téléphone français entier (10 chiffres, groupes de 2) qui commence la ligne d'après ou finit la ligne
# d'avant : la ligne est un autre champ, jamais recollé par GAP (« Matricule 0049217⏎06 74 28 19 53 », 2e test
# terrain, tous modes). A whole French phone number starting the next line or ending the previous one: another field,
# never joined by GAP (every mode).
_PHONE_HEAD_RE = re.compile(r"0[1-9](?:[ .\-]?[0-9]{2}){4}(?![0-9])")
_PHONE_TAIL_RE = re.compile(r"(?<![0-9])0[1-9](?:[ .\-]?[0-9]{2}){4}\Z")


def _phone_line(text: str, start: int, end: int) -> bool:
    """Le saut de ligne GAP [start, end) sépare-t-il un téléphone entier de son voisin ? / does the break border a
    whole phone number?"""
    if _PHONE_HEAD_RE.match(text, end) is not None:
        return True
    return _PHONE_TAIL_RE.search(text[text.rfind("\n", 0, start) + 1:start]) is not None


# Ligne qui commence par un code postal suivi de sa ville (« 75011 Paris ») : un autre champ, jamais recollé au nombre
# de la ligne d'avant (revue du 26/10, troisième tour : « Dossier 56 78⏎75011 Paris »). A line starting with a postcode
# and its town: another field, never joined to the previous line's number.
_POSTCODE_HEAD_RE = re.compile(r"[0-9]{5}[ \t]+[A-ZÀ-Ý]")


def _gaps(text: str) -> list[tuple[int, int]]:
    """Règle GAP : zones [début, fin) de blancs à ramener à une espace / GAP rule: blank zones to make one space."""
    gaps: list[tuple[int, int]] = []
    if "\t" in text or "  " in text:
        for m in _GAP_BLANKS_RE.finditer(text):
            start, end = m.span()
            if end - start > 4 or start == 0 or end == len(text):
                continue
            before, after = text[start - 1], text[end]
            if (before in _ASCII_ALNUM and after in _ASCII_ALNUM
                    and (before in _ASCII_DIGITS or after in _ASCII_DIGITS)
                    and not ("\t" in text[start:end] and _tab_row(text, start))):
                gaps.append((start, end))
    if "\n" in text:
        for m in _GAP_BREAK_RE.finditer(text):
            start, end = m.span(1)
            if not _group_longer(text, start, -1) and not _group_longer(text, end, 1) \
                    and not _delimited_row(text, end) and not _phone_line(text, start, end) \
                    and _POSTCODE_HEAD_RE.match(text, end) is None:
                gaps.append((start, end))
        gaps.sort()
    return gaps


def _token(text: str, start: int, step: int, chars: frozenset[str]) -> tuple[str, bool]:
    """Suite maximale de `chars` depuis `start` (vers la gauche si `step` = -1) et « mot entier » (pas de lettre
    ou chiffre au-delà). Maximal run of `chars` from `start` (leftwards when `step` is -1), and whether it is a
    whole word (no letter or digit beyond it)."""
    i = start if step > 0 else start - 1
    while 0 <= i < len(text) and text[i] in chars:
        i += step
    whole = not (0 <= i < len(text) and text[i].isalnum())
    return (text[start:i] if step > 0 else text[i + 1:start]), whole


def _email_join(left: str, right: str) -> bool:
    """Les deux morceaux forment-ils un seul courriel coupé ? / do both pieces make one wrapped e-mail?"""
    right = right.rstrip(".-")
    if (left + right).count("@") != 1 or not left or not right:
        return False
    # Fin de phrase (1.0.2) : un point final suivi d'un saut de ligne et d'une majuscule n'est jamais recollé quand
    # le courriel est déjà complet (« …@gmail.com.⏎IBAN ») ou absent à gauche (« … fin.⏎Jean@x.fr »).
    # End of sentence: a final full stop, a line break and a capital are never joined when the e-mail is already
    # complete on the left, or absent from the left.
    if left[-1] == "." and right[0] in _UPPER_LETTERS and (
            "@" not in left or _DOMAIN_RE.fullmatch(left.partition("@")[2].rstrip(".")) is not None):
        return False
    if "@" in left:
        local, _, domain = left.partition("@")
        return (bool(local) and "@" not in right and _DOMAIN_RE.fullmatch(domain) is None
                and _DOMAIN_RE.fullmatch(domain + right) is not None)
    # Le morceau de gauche commence par une lettre : un numéro en fin de ligne (« 06 12 34 56 78⏎jean@… ») n'est
    # pas collé au courriel. The left piece starts with a letter: a number ending the line is not glued on.
    local, _, domain = right.partition("@")
    signed = any(c in "._-0123456789" for c in left)
    # Courriel déjà complet en tête de ligne (revue du 26/10, troisième tour) : un morceau de gauche qui porte une
    # majuscule n'est pas le début de sa partie locale (« Bonjour M.⏎paul@… », « Jean.⏎marie.durand@… »,
    # « SKU-123456⏎support@… »). Un morceau en minuscules reste recollé (« michele.⏎vallee57@… », équipe rouge crlf).
    # An already complete address at the line start: a left piece holding a capital is not the start of its local
    # part; a lowercase piece is still joined back.
    if len(local) >= 2 and left != left.lower():
        return False
    # Mot de la ligne d'avant (2e test terrain, revue du 26/10, tous modes) : un mot sans signe qui porte une majuscule
    # (« Agence de Tours⏎karine.lopez@… », « ACME France SAS⏎sophie.lemoine@… ») ou suivi d'une partie locale déjà
    # complète (« prénom.nom », séparateur intérieur) n'est pas le début du courriel. A plain word with a capital, or
    # followed by an already complete "first.last" local part, is the previous line's last word, not a piece.
    if not signed and (left != left.lower() or any(c in "._-" for c in local[1:])):
        return False
    return (_DOMAIN_RE.fullmatch(domain) is not None and left[0] in _ASCII_LETTERS
            and (len(left) <= _BREAK_LOCAL or signed))


def _iban_complete(group: str) -> bool:
    """Clé ISO 7064 (mod 97) déjà juste : l'IBAN est entier, la ligne suivante n'en fait pas partie.
    Key already right: the IBAN is whole, the next line is not part of it."""
    remainder = 0
    for ch in group[4:] + group[:4]:
        for digit in str(int(ch, 36)):
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1


# Numéro coupé par un saut de ligne (règle BREAK_NUMBER, 1.0.2, équipe rouge crlf et line_break, tous modes) : les deux
# morceaux (chiffres, « . » et « - ») ne forment qu'un numéro qu'une fois recollés sans blanc, et ce numéro est prouvé
# par sa forme ou sa clé : téléphone français entier (« 07⏎-93-28-03-42 », « 07.42.66.93⏎.70 »), IPv4
# (« 5.46⏎.239.23 »), SIREN ou SIRET (clé de Luhn), NIR (clé 97), RIB (clé 97). Sans preuve, rien n'est recollé.
# A number split by a line break: both pieces make one number only once joined without a blank, proven by its shape
# or key.
_NUMBER_PART = frozenset("0123456789.-")
_PHONE_FULL_RE = re.compile(r"0[1-9](?:[.\-]?[0-9]{2}){4}")
_IPV4_RE = re.compile(r"(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}"
                      r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])")


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        value = int(ch) * (2 if i % 2 else 1)
        total += value - 9 if value > 9 else value
    return total % 10 == 0


def _number_join(left: str, right: str) -> bool:
    """Les deux morceaux forment-ils un seul numéro prouvé ? / do both pieces make one proven number?"""
    left, right = left.lstrip(".-"), right.rstrip(".-")
    if not left or not right or not any(c in _ASCII_DIGITS for c in left) \
            or not any(c in _ASCII_DIGITS for c in right):
        return False
    joined = left + right
    if _PHONE_FULL_RE.fullmatch(joined) is not None or _IPV4_RE.fullmatch(joined) is not None:
        return True
    if not all(c in _ASCII_DIGITS for c in joined):
        return False
    size = len(joined)
    if size in (9, 14):
        return _luhn(joined)
    if size == 15:
        return joined[0] in "12378" and 97 - int(joined[:13]) % 97 == int(joined[13:])
    if size == 23:
        return 97 - (89 * int(joined[:5]) + 15 * int(joined[5:10]) + 3 * int(joined[10:21])) % 97 == int(joined[21:])
    return False


def _country_code_join(left: str, right: str) -> bool:
    """Code pays seul en fin de ligne (« IBAN FR⏎7616… ») : recollé si la clé de l'IBAN entier est juste (BREAK_NUMBER).
    A country code alone ending the line: joined when the whole IBAN's key is right."""
    return (len(left) == 2 and all(c in _UPPER_LETTERS for c in left) and 13 <= len(right) <= 32
            and _IBAN_HEAD_RE.fullmatch(left + right) is not None and _iban_complete(left + right))


# Plaque d'immatriculation coupée par un saut de ligne (règle BREAK_PLATE, équipe rouge, tous modes) : SIV
# (« WB 864⏎SW », « DV-185⏎-FP », « SF-112-⏎ES ») ou FNI (« 9971 ZL⏎59 », « 8871⏎LZ 59 »). Le saut devient une espace si
# la plaque se lit ainsi (il remplaçait une espace), sinon il est retiré. A licence plate split by a line break: the
# break becomes a space when the plate reads so, otherwise it is removed.
_PLATE_PART = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -")
_PLATE_RES = (re.compile(r"[A-Z]{2}[ -]?[0-9]{3}[ -]?[A-Z]{2}"),
              re.compile(r"[0-9]{1,4}[ -]?[A-Z]{1,3}[ -]?(?:[0-9]{2}|2[AB])"))
_PLATE_SIDE = 9


def _plate_join(text: str, start: int, end: int) -> int:
    """0 : pas de plaque ; 1 : saut ramené à une espace ; 2 : saut retiré / 0: no plate; 1: one space; 2: removed."""
    if text[start - 1] not in _PLATE_PART or text[end] not in _PLATE_PART:
        return 0
    i = start
    while i > 0 and start - i < _PLATE_SIDE and text[i - 1] in _PLATE_PART:
        i -= 1
    j = end
    while j < len(text) and j - end < _PLATE_SIDE and text[j] in _PLATE_PART:
        j += 1
    lefts = [text[k:start] for k in range(i, start)
             if (k == 0 or not text[k - 1].isalnum()) and (k == i or text[k - 1] in " -")]
    rights = [text[end:k] for k in range(j, end, -1)
              if (k == len(text) or not text[k].isalnum()) and (k == j or text[k] in " -")]
    for sep in (" ", ""):
        for left in lefts:
            for right in rights:
                if any(regex.fullmatch(left + sep + right) is not None for regex in _PLATE_RES):
                    return 1 if sep else 2
    return 0


def _breaks(text: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Règle BREAK : (zones à ramener à une espace, zones à retirer) / (zones to make one space, zones to remove)."""
    gaps: list[tuple[int, int]] = []
    cuts: list[tuple[int, int]] = []
    for m in _BREAK_RE.finditer(text):
        start, end = m.span()
        left, left_whole = _token(text, start, -1, _EMAIL_PART)
        right, right_whole = _token(text, end, 1, _EMAIL_PART)
        if left_whole and right_whole and _email_join(left, right):
            cuts.append((start, end))
            continue
        left, left_whole = _token(text, start, -1, _NUMBER_PART)
        right, right_whole = _token(text, end, 1, _NUMBER_PART)
        if left_whole and right_whole and _number_join(left, right) and not _delimited_row(text, end) \
                and _POSTCODE_HEAD_RE.match(text, end) is None \
                and not (left[-1] in _ASCII_DIGITS and right[0] in _ASCII_DIGITS and _phone_line(text, start, end)):
            cuts.append((start, end))
            continue
        plate = _plate_join(text, start, end)
        if plate:
            (gaps if plate == 1 else cuts).append((start, end))
            continue
        left, left_whole = _token(text, start, -1, _ASCII_ALNUM)
        right, right_whole = _token(text, end, 1, _ASCII_ALNUM)
        if not (left and right and left_whole and right_whole):
            continue
        # Jamais un téléphone entier en tête de la ligne d'après (revue du 26/10, troisième tour : « TVA
        # FR44732829320⏎01 23 45 67 89 » n'est pas un IBAN coupé). Never a whole phone number heading the next line.
        # Un IBAN n'est « déjà entier » qu'à 15 caractères au moins : « FR76 » seul a une clé juste par hasard (équipe
        # rouge line_break, « IBAN FR76⏎1660… »). An IBAN is "already whole" only from 15 characters: "FR76" alone
        # has a right key by chance.
        if (_IBAN_HEAD_RE.fullmatch(left) and right == right.upper() and any(c in _ASCII_DIGITS for c in right)
                and 15 <= len(left) + len(right) <= 34 and not (len(left) >= 15 and _iban_complete(left))
                and _PHONE_HEAD_RE.match(text, end) is None) or _country_code_join(left, right):
            cuts.append((start, end))
        elif (left[-1] not in _ASCII_DIGITS or right[0] not in _ASCII_DIGITS) \
                and len(left) <= _BREAK_GROUP and len(right) <= _BREAK_GROUP \
                and left == left.upper() and right == right.upper() \
                and any(c in _ASCII_DIGITS for c in left) and any(c in _ASCII_DIGITS for c in right):
            gaps.append((start, end))
    return gaps, cuts


def _spaced_cuts(text: str) -> list[tuple[int, int]]:
    """Lettres espacées : zones à retirer (`_SPACED_RE`) / letter spacing: zones to remove."""
    cuts: list[tuple[int, int]] = []
    if _SPACED_HINT_RE.search(text) is None:
        return cuts
    for m in _SPACED_RE.finditer(text):
        start, end = m.span()
        cells = [i for i in range(start, end) if text[i] != " "]
        last = len(cells) - 1
        block: list[int] = []
        for k, cell in enumerate(cells):
            if (text[cell] in "aà" and 0 < k < last and text[cells[k - 1]] in _ASCII_DIGITS
                    and text[cells[k + 1]] in _ASCII_DIGITS):
                _spaced_block(text, block, cuts)  # « 4 à 6 » : l'intervalle reste tel quel / the range stays
                block = []
                continue
            if block and cell - block[-1] == 2 and text[block[-1]].islower() and text[cell].isupper():
                _spaced_block(text, block, cuts)
                block = []
            block.append(cell)
        _spaced_block(text, block, cuts)
    return cuts


def _spaced_block(text: str, block: list[int], cuts: list[tuple[int, int]]) -> None:
    letters = sum(text[cell] not in _SPACED_MARKS for cell in block)
    word = (len(block) == _SPACED_MIN - 1 and text[block[0]].isupper() and text[block[1]].islower()
            and text[block[2]].islower())  # « Z o é »
    if letters < _SPACED_MIN and not word:
        return
    for prev, cell in pairwise(block):
        if cell - prev == 2:
            cuts.append((prev + 1, cell))
        else:
            cuts.append((prev + 2, cell))


def _sep_runs(text: str) -> list[int]:
    """Positions des « / » et « . » à remplacer par une espace (`_SEP_RUNS`) / separators to turn into spaces.

    La suite est tout un mot de lettres, chiffres et séparateurs, un séparateur final permis (fin de phrase).
    The run is a whole word of letters, digits and separators; one trailing separator is allowed.
    """
    positions: list[int] = []
    for sep, regex in _SEP_RUNS:
        if sep not in text:
            continue
        for m in regex.finditer(text):
            start, end = m.span()
            if start and (text[start - 1] in _ASCII_ALNUM or text[start - 1] == sep):
                continue
            if end < len(text) and (text[end] in _ASCII_ALNUM or (
                    text[end] == sep and end + 1 < len(text)
                    and (text[end + 1] in _ASCII_ALNUM or text[end + 1] == sep))):
                continue
            value = m.group()
            if all(any(c in _ASCII_DIGITS for c in group) for group in value.split(sep)):
                positions.extend(start + i for i, c in enumerate(value) if c == sep)
    positions.sort()
    return positions


def _unbold(match: re.Match[str]) -> str:
    start, end = match.span()
    text = match.string
    # Dans un mot (« snake__case », e-mails) : inchangé / inside a word: unchanged.
    if start > 0 and text[start - 1].isalnum() and end < len(text) and text[end].isalnum():
        return match.group()
    return " " * (end - start)


def normalize(text: str) -> tuple[str, array | None]:
    """Texte de détection et table de positions / detection text and offset map.

    La table vaut None si aucune suppression n'a eu lieu (cas courant, coût nul).
    The map is None when nothing was removed (common case, zero cost).
    """
    if text.isascii():
        mapped = text
    else:
        mapped = text.translate(_NORMALIZE_BMP)
        if _ASTRAL_RE.search(mapped) is not None:
            mapped = mapped.translate(_ASTRAL_NORMALIZE)
    if "**" in mapped or "__" in mapped:
        mapped = _EMPHASIS_RE.sub(_unbold, mapped)
    # Règle GAP : le premier blanc devient une espace, les suivants sont retirés / GAP rule: the first blank
    # becomes a space, the others are removed.
    gaps = _gaps(mapped)
    break_cuts: list[tuple[int, int]] = []
    if "\n" in mapped:
        break_gaps, break_cuts = _breaks(mapped)
        if break_gaps:
            gaps = sorted(gaps + break_gaps)
    # Lettres espacées, lues avant les remplacements / letter spacing, read before the swaps.
    spaced = _spaced_cuts(mapped) if " " in mapped else []
    swaps = [start for start, _ in gaps if mapped[start] != " "]
    if "/" in mapped or "." in mapped:
        swaps = sorted(swaps + _sep_runs(mapped))
    if swaps:
        pieces: list[str] = []
        last = 0
        for start in swaps:
            pieces += (mapped[last:start], " ")
            last = start + 1
        pieces.append(mapped[last:])
        mapped = "".join(pieces)
    cuts = [] if mapped.isascii() else [m.span() for m in INVISIBLE_RE.finditer(mapped)]
    if "-" in mapped and "\n" in mapped:
        # « Du-\npont » -> « Dupont » ; « Jean-\nPierre » garde son trait d'union / keeps its hyphen.
        cuts.extend((m.start() if mapped[m.end()].islower() else m.start() + 1, m.end())
                    for m in _HYPHEN_BREAK_RE.finditer(mapped))
        cuts.sort()
    if any(end - start > 1 for start, end in gaps):
        cuts.extend((start + 1, end) for start, end in gaps if end - start > 1)
        cuts.sort()
    if break_cuts:
        cuts.extend(break_cuts)
        cuts.sort()
    if spaced:
        cuts.extend(spaced)
        cuts.sort()
    if not cuts:
        return mapped, None
    parts: list[str] = []
    offsets = array("q")
    last = 0
    for start, end in cuts:
        start = max(start, last)
        parts.append(mapped[last:start])
        offsets.extend(range(last, start))
        last = max(last, end)
    parts.append(mapped[last:])
    offsets.extend(range(last, len(mapped)))
    offsets.append(len(mapped))
    return "".join(parts), offsets


def fold(text: str) -> str:
    """Repliement pour les mots-clés / folding for keyword matching."""
    if text.isascii():
        return text.lower()
    return text.translate(_FOLD_BMP)


def prepare(text: str, *, native: bool = False) -> tuple[str, str, array | None]:
    """`normalize` puis `fold`, en un appel : (texte de détection, texte replié, table de positions).

    `normalize` then `fold` in one call. `native=True` : noyau Rust s'il est installé (mêmes résultats,
    sans GIL), sinon ces fonctions Python, qui restent la référence. Rust core when installed (same
    results, GIL released), otherwise these Python functions, which remain the reference.
    """
    preparer = _native_preparer() if native else None
    if preparer is not None:
        try:
            norm, folded, raw = preparer.prepare(text)
        except UnicodeEncodeError:  # demi-codet isolé, hors UTF-8 : voie Python / lone surrogate: Python path
            pass
        else:
            if raw is None:
                return norm, folded, None
            offsets = array("q")
            offsets.frombytes(raw)
            return norm, folded, offsets
    norm, offsets = normalize(text)
    return norm, fold(norm), offsets


@cache
def _native_preparer() -> Any:
    from . import _native  # import différé : _native dépend de ce module / deferred: _native depends on us

    return _native.preparer()


# --- Classes de caractères pour le noyau Rust / character classes for the Rust core ------------------------
#
# Une seule table pour tout le noyau (rust/src/unicode.rs), construite une fois par processus à partir des
# prédicats de CET interpréteur (`str`, `re`) : le noyau ne devine jamais une propriété Unicode. Le plan de
# base est calculé à la construction, chaque autre plan au premier de ses caractères que le noyau rencontre.
# One table for the whole core, built once per process from THIS interpreter's predicates (`str`, `re`): the
# core never guesses a Unicode property. The Basic Multilingual Plane is computed at construction, any other
# plane when the core first meets one of its characters.

# Bits de la table, dans l'ordre de rust/src/unicode.rs / table bits, in the order of rust/src/unicode.rs.
(WORD, ALNUM, LETTER, DECIMAL, DIGIT, SPACE, ALPHA, UPPER, LOWER, TITLE, UPPER_SAFE, CAPITAL, INVISIBLE,
 MAPS_UPPER, MAPS_LOWER) = (1 << bit for bit in range(15))
PLANE = 0x10000
# Version d'Unicode la plus récente dont les plans 4 à 16 sont vérifiés : aucune lettre, aucun chiffre, aucun
# espace ni aucune casse (plans 4 à 13 vides, 14 étiquettes et sélecteurs, 15 et 16 privés). Au-delà, tout est
# relu. Latest Unicode version whose planes 4-16 are known to hold no letter, digit, space nor case; beyond it,
# every plane is read.
_VERIFIED_UNICODE = (17, 0, 0)
_BLOCK = 256
_CLASSES_RE = re.compile(r"([^\W\d_]+)|(\d+)|(_+)|(\s+)")
_ANY_CLASS_RE = re.compile(r"[\w\s]")
_ONES_RE = re.compile(rb"\x01+")
# Intervalles [début, fin) de points dans un plan / [start, end) point runs within a plane.
Runs = list[tuple[int, int]]


def code_points(start: int, end: int) -> str:
    """Points de code de [start, end) (plans entiers), substituts compris, sans boucle Python : UTF-32 construit
    par tranches. Code points of [start, end) (whole planes), surrogates included, without a Python loop.
    """
    planes = range(start // PLANE, end // PLANE)
    raw = bytearray(4 * (end - start))
    raw[0::4] = bytes(range(256)) * ((end - start) // 256)
    raw[1::4] = b"".join(bytes((byte,)) * 256 for byte in range(256)) * len(planes)
    raw[2::4] = b"".join(bytes((plane,)) * PLANE for plane in planes)
    return raw.decode("utf-32-le", "surrogatepass")


def char_flags(ch: str, capital: str | None = None) -> int:
    """Référence, caractère par caractère (tests) : les bits de la table, chacun par un prédicat de `str`.

    Reference, one character at a time (tests): every table bit, each from a `str` predicate. `capital` : classe
    des capitales des heuristiques (`heuristics._lexicon.UPPER` par défaut) / the heuristics' capital class.
    """
    if capital is None:
        from .heuristics._lexicon import UPPER as capital  # import différé : _lexicon importe ce module
    alnum, decimal = ch.isalnum(), ch.isdecimal()
    lower, title = ch.islower(), unicodedata.category(ch) == "Lt"
    return ((alnum or ch == "_") * WORD | alnum * ALNUM | (alnum and not decimal) * LETTER | decimal * DECIMAL
            | ch.isdigit() * DIGIT | ch.isspace() * SPACE | ch.isalpha() * ALPHA | ch.isupper() * UPPER
            | lower * LOWER | title * TITLE | ("A" + ch).isupper() * UPPER_SAFE
            | (re.fullmatch(f"[{capital}]", ch) is not None) * CAPITAL
            | (INVISIBLE_RE.fullmatch(ch) is not None) * INVISIBLE
            | (ch.upper() != ch) * MAPS_UPPER | (ch.lower() != ch) * MAPS_LOWER)


def _runs(flags: bytes, offset: int) -> Runs:
    return [(offset + m.start(), offset + m.end()) for m in _ONES_RE.finditer(flags)]


def _has_case(chars: str) -> bool:
    """Un caractère majuscule, minuscule, de titre, ou à correspondance de casse ? / any cased character?"""
    return not ((chars + "a").islower() and (chars + "A").isupper() and chars.upper() == chars
                and chars.lower() == chars)


def _class_runs(pattern: str, chars: str, first: int) -> Runs:
    """Intervalles d'une classe `[...]` de littéraux et d'intervalles dans un plan, lus dans l'arbre de `re`
    (sans balayer le plan) ; autre forme : balayage par `re`. Runs of a `[...]` class of literals and ranges
    within a plane, read from `re`'s own parse tree (no scan); any other shape: scanned by `re`.
    """
    from re import _parser  # arbre de syntaxe de `re` / `re`'s syntax tree

    tree = list(_parser.parse(pattern))
    if len(tree) == 1 and str(tree[0][0]) == "IN" and all(str(op) in ("LITERAL", "RANGE") for op, _ in tree[0][1]):
        runs = []
        for op, av in tree[0][1]:
            lo, hi = (av, av) if str(op) == "LITERAL" else av
            lo, hi = max(lo, first), min(hi, first + PLANE - 1)
            if lo <= hi:
                runs.append((lo - first, hi + 1 - first))
        return runs
    return [m.span() for m in re.finditer(f"(?:{pattern})+", chars)]


def plane_classes(plane: int, capital: str = "") -> tuple[list[tuple[int, Runs]], list[tuple[int, str]],
                                                          list[tuple[int, str]]]:
    """Classes et casse des 65 536 points d'un plan, en code C (`re`, méthodes `str`) : quelques ms par plan.

    Classes and case of a plane's 65,536 points, in C code: a few ms per plane. Renvoie, en positions dans le
    plan, les intervalles [début, fin) de chaque bit, puis `str.upper()` et `str.lower()` des caractères qu'ils
    changent. Returns, as offsets within the plane, the [start, end) runs of each bit, then `str.upper()` and
    `str.lower()` of the characters they change. ALNUM, UPPER_SAFE et MAPS_* se déduisent / are derived.
    """
    chars = code_points(plane * PLANE, (plane + 1) * PLANE)
    letters: Runs = []
    decimals: Runs = []
    underscores: Runs = []
    spaces: Runs = []
    groups = (letters, decimals, underscores, spaces)
    # `\w` = lettres `[^\W\d_]` + `\d` + « _ », un seul balayage, sur les blocs qui en contiennent.
    # `\w` = letters + `\d` + '_', one pass, over the blocks holding any.
    for start in range(0, PLANE, _BLOCK) if _ANY_CLASS_RE.search(chars) is not None else ():
        if _ANY_CLASS_RE.search(chars, start, start + _BLOCK) is not None:
            for m in _CLASSES_RE.finditer(chars, start, start + _BLOCK):
                groups[m.lastindex - 1].append(m.span())
    alpha: Runs = []
    digits: Runs = list(decimals)
    for start, end in letters:
        run = chars[start:end]
        if run.isalpha():
            alpha.append((start, end))
            continue
        # Lettres au sens de `re` qui ne sont pas `isalpha` : nombres non décimaux (« ² », « Ⅻ »).
        # Letters for `re` that are not `isalpha`: non-decimal numbers.
        alpha += _runs(bytes(map(str.isalpha, run)), start)
        digits += _runs(bytes(not c.isalpha() and c.isdigit() for c in run), start)
    upper: Runs = []
    lower: Runs = []
    title: Runs = []
    upper_map: list[tuple[int, str]] = []
    lower_map: list[tuple[int, str]] = []
    for start in range(0, PLANE, _BLOCK) if _has_case(chars) else ():
        block = chars[start:start + _BLOCK]
        if not _has_case(block):
            continue
        singles = list(block)
        upper += _runs(bytes(map(str.isupper, singles)), start)
        lower += _runs(bytes(map(str.islower, singles)), start)
        title += _runs(bytes(unicodedata.category(c) == "Lt" for c in singles), start)
        upper_map += [(start + i, u) for i, (c, u) in enumerate(zip(singles, map(str.upper, singles), strict=True))
                      if u != c]
        lower_map += [(start + i, u) for i, (c, u) in enumerate(zip(singles, map(str.lower, singles), strict=True))
                      if u != c]
    first = plane * PLANE
    runs = [(WORD, letters + decimals + underscores), (LETTER, letters), (DECIMAL, decimals), (DIGIT, digits),
            (SPACE, spaces), (ALPHA, alpha), (UPPER, upper), (LOWER, lower), (TITLE, title),
            (INVISIBLE, _class_runs(INVISIBLE_RE.pattern, chars, first))]
    if capital:
        runs.append((CAPITAL, _class_runs(f"[{capital}]", chars, first)))
    return runs, upper_map, lower_map


def verified_planes() -> bool:
    """Les plans 4 à 16 de cet interpréteur sont-ils connus vides de lettres, chiffres, espaces et casse ?

    Are this interpreter's planes 4-16 known to hold no letter, digit, space nor case (Unicode version)?
    """
    return tuple(map(int, unicodedata.unidata_version.split("."))) <= _VERIFIED_UNICODE


@cache
def ignorecase_data() -> dict[str, Any]:
    """Données de `re.IGNORECASE`, tirées de `re` lui-même, une fois / `re.IGNORECASE` data, from `re`, once.

    `candidates` : tout caractère dont la correspondance insensible à la casse peut différer de la sensible
    (caractères à casse de `_sre`, leurs minuscules simples, cas supplémentaires de `re`) ; `lower` : minuscule
    simple de `_sre` de chacun ; `cased` : ceux à casse ; `fixes` : cas supplémentaires. Every character whose
    case-insensitive match may differ from the case-sensitive one, with `_sre`'s simple lowercase.
    """
    import _sre
    from re._casefix import _EXTRA_CASES

    planes = range(2) if verified_planes() else range(17)
    cased: list[int] = []
    for plane in planes:
        chars = code_points(plane * PLANE, (plane + 1) * PLANE)
        for start in range(0, PLANE, _BLOCK):
            block = chars[start:start + _BLOCK]
            # `_sre` : minuscule ou majuscule simple différente ; les complètes en sont un sur-ensemble.
            # `_sre`: different simple lowercase or uppercase; the full mappings are a superset.
            if block.upper() != block or block.lower() != block:
                first = plane * PLANE + start
                cased += filter(_sre.unicode_iscased, range(first, first + _BLOCK))
    candidates = set(cased) | set(map(_sre.unicode_tolower, cased)) | set(_EXTRA_CASES)
    candidates.update(cp for fixes in _EXTRA_CASES.values() for cp in fixes)
    ordered = sorted(candidates)
    return {
        "candidates": ordered,
        "lower": [(cp, _sre.unicode_tolower(cp)) for cp in ordered],
        "cased": cased,
        "fixes": sorted((cp, list(fixes)) for cp, fixes in _EXTRA_CASES.items()),
    }


def strip_separators(value: str) -> str:
    return value.translate(_STRIP_TABLE)


# Tableaux en texte délimité (1.0.2, docs/REGLES.md « Tableaux CSV et TSV ») : « ; », tabulation ou « , ». La barre
# « | » reste aux tableaux Markdown. Delimited-text tables: ";", tab or ","; "|" stays with Markdown tables.
CSV_DELIMITERS = (";", "\t", ",")
_CSV_HEADER_MAX = 40  # cellule d'en-tête : 1 à 40 caractères, sans chiffre / header cell: 1-40 chars, no digit
_CSV_MIN_ROWS = 2     # au moins deux lignes de données de même nombre de champs / at least two data rows


def _csv_cells(text: str, start: int, stop: int, delimiter: str) -> list[tuple[int, int]]:
    """Champs d'une ligne [start, stop), rognés de leurs blancs (`str.isspace`) / a line's fields, trimmed."""
    cells: list[tuple[int, int]] = []
    left = start
    while True:
        right = text.find(delimiter, left, stop)
        right = stop if right < 0 else right
        a, b = left, right
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        cells.append((a, b))
        if right >= stop:
            return cells
        left = right + 1


def delimited_tables(text: str) -> list[list[list[tuple[int, int]]]]:
    """Tableaux CSV ou TSV : un en-tête d'au moins deux délimiteurs d'une même sorte, cellules courtes sans chiffre,
    puis au moins deux lignes de même nombre de champs ; le tableau s'arrête à la première ligne qui diffère.
    Chaque tableau : ses lignes (en-tête d'abord), chaque ligne ses champs (positions). CSV or TSV tables: a header
    with two or more delimiters of one kind, short cells with no digit, then two or more lines with the same field
    count; the table ends at the first line that differs. Each table: its rows (header first), each row its fields.
    """
    return [[_csv_cells(text, start, stop, delimiter) for start, stop in lines]
            for delimiter, lines in _table_scan(text)]


def _table_scan(text: str) -> list[tuple[str, list[tuple[int, int]]]]:
    """Tableaux de `delimited_tables` : (délimiteur, lignes [début, fin) en-tête d'abord) / (delimiter, lines)."""
    if "\n" not in text:
        return []
    lines: list[tuple[int, int]] = []
    pos = 0
    while pos <= len(text):
        end = text.find("\n", pos)
        end = len(text) if end < 0 else end
        lines.append((pos, end - 1 if end > pos and text[end - 1] == "\r" else end))
        pos = end + 1
    tables: list[tuple[str, list[tuple[int, int]]]] = []
    i = 0
    while i < len(lines):
        start, stop = lines[i]
        for delimiter in CSV_DELIMITERS:
            count = text.count(delimiter, start, stop)
            if count < 2:
                continue
            header = _csv_cells(text, start, stop, delimiter)
            if not all(0 < b - a <= _CSV_HEADER_MAX and not any(c in _ASCII_DIGITS for c in text[a:b])
                       for a, b in header):
                continue
            j = i + 1
            while j < len(lines) and text.count(delimiter, *lines[j]) == count:
                j += 1
            if j - i - 1 < _CSV_MIN_ROWS:
                continue
            tables.append((delimiter, lines[i:j]))
            i = j - 1
            break
        i += 1
    return tables


_STRIP_TABLE = {ord(" "): None, ord("."): None, ord("-"): None, ord("/"): None}
