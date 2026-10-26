"""Découpage en phrases, filtre de signaux et fenêtres de jetons, avant le modèle.

Sentence splitting, signal gating and token windows, before the model. Pur Python, sans dépendance.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from .._text import fold
from .lexicon import ABBREVIATIONS, COMMON_STARTERS

Bounds = tuple[int, int]


def _char_class(predicate: Callable[[str], bool], ranges: Sequence[Bounds]) -> str:
    """Classe regex des caractères qui vérifient le prédicat / regex class of matching characters."""
    parts: list[str] = []
    for lo, hi in ranges:
        run = -1
        for cp in range(lo, hi + 1):
            inside = predicate(chr(cp))
            if inside and run < 0:
                run = cp
            if run >= 0 and (not inside or cp == hi):
                last = cp if inside else cp - 1
                parts.append(re.escape(chr(run)) + ("-" + re.escape(chr(last)) if last > run else ""))
                run = -1
    return "".join(parts)


# Latin, grec, cyrillique, latin étendu additionnel / Latin, Greek, Cyrillic, Latin Extended Additional.
_UPPER = _char_class(str.isupper, ((0x41, 0x24F), (0x370, 0x52F), (0x1E00, 0x1EFF)))
_LETTER = r"[^\W\d_]"

# Mot à majuscule initiale non précédé d'une lettre (« l'Élysée » compte) / capitalised word start.
CAPITAL_RE = re.compile(rf"(?<!{_LETTER})[{_UPPER}]")
_WORD_RE = re.compile(rf"{_LETTER}{{1,40}}")
_TWO_LETTERS_RE = re.compile(rf"{_LETTER}{{2}}")
# Civilité en minuscules (texte replié) : « madame dupont », « m. dupont », « dr martin » / lowercase honorific.
_HONORIFIC_RE = re.compile(
    rf"(?<!{_LETTER})(?:monsieur|madame|mademoiselle|maitre|docteur|professeur|mme|mlle|mr|mrs|ms|dr|pr|m\.|me\."
    rf"|mister|miss|madam|doctor|professor|sir)(?!{_LETTER})")
# Fin de phrase : ponctuation forte, espace, puis majuscule, chiffre ou guillemet / sentence end.
_BOUNDARY_RE = re.compile(rf"[.!?…]{{1,8}}[»\"”’')\]]{{0,4}}[ \t]{{1,16}}(?=[«\"“(\[-]?[ \t]?[{_UPPER}0-9])")
_WORD_BEFORE_RE = re.compile(rf"({_LETTER}{{1,24}})$")
_FENCE_RE = re.compile(r"[ \t]{0,3}(?:```|~~~)")
# Jeton opaque : 32+ caractères sans espace dont un chiffre ou un symbole (URL, e-mail, empreinte, base64).
# Opaque token: 32+ non-space characters including a digit or a symbol (URL, e-mail, hash, base64).
_LONG_RUN_RE = re.compile(r"\S{32,4096}")
_OPAQUE_MARK_RE = re.compile(r"[0-9/@=+%_:\\]")
# Instruction de code reconnaissable à sa syntaxe, pas à un mot seul : « from Jean Dupont… », « let me know… »,
# « public visé : … » restent du texte. Code statement recognised by its syntax, not by a lone keyword.
_CODE_RE = re.compile(
    r"[ \t]{0,64}(?:"
    r"\}[ \t]*(?:else|catch|finally)\b"
    r"|(?:else|try|finally|do)[ \t]*[:{][ \t]*$"
    r"|#(?:include|define|undef|ifdef|ifndef|if|elif|else|endif|pragma|region|endregion)\b"
    # Condition à opérateur ou à un seul mot : « for (more details) », « with (Jean Dupont) » restent du texte.
    # Condition with an operator or a single word: parenthesised prose stays text.
    r"|(?:if|for|foreach|while|switch|catch)[ \t]*\("
    r"(?:[^()\n]{0,256}[=<>!&|;.\[][^\n]{0,256}|[\w.]{1,64})\)[ \t]*(?:\{|:|;|$)"
    r"|(?:async[ \t]+)?(?:def|function|fn|func|fun)[ \t]+(?:\([^)\n]{0,128}\)[ \t]*)?\w{1,64}[(<]"
    r"|function[ \t]*\("
    r"|(?:class|struct|enum|interface|trait|impl)[ \t]+\w{1,64}(?:[(:<]|[ \t]*\{|[ \t]*$)"
    r"|(?:const|let|var|val)[ \t]+(?:\w{1,64}|\{[^}\n]{0,200}\}|\[[^\]\n]{0,200}\])[ \t]*[=:;]"
    r"|(?:int|long|short|float|double|char|bool|boolean|void|byte|auto|unsigned|size_t|String|string)[ \t*&]{1,8}"
    r"\w{1,64}(?:\(|[ \t]*[=;\[])"
    r"|(?:pub|public|private|protected|internal|static|final|abstract|override|virtual|export)[ \t]+"
    r"(?:[\w<>\[\],.?]{1,64}[ \t]+){0,5}[\w<>\[\]]{1,64}(?:\(|[ \t]*[;={])"
    r"|from[ \t]+[a-z_.][\w.]{0,127}[ \t]+import[ \t]"
    r"|import[ \t]+[\w.*]{1,128}(?:[ \t]+as[ \t]+\w{1,64})?[ \t]*;?[ \t]*$"
    r"|(?:use|using|namespace|mod|require)[ \t]+[\w.:\\]{1,128}[ \t]*[;{][ \t]*$"
    r"|package[ \t]+[a-z_][\w.]{0,127}[ \t]*;?[ \t]*$"
    r"|return\b[^\n]{0,256};[ \t]*$"
    r"|@[\w.]{1,64}\("
    r"|<\?php|\?>"
    r"|SELECT[ \t]+(?:\*|DISTINCT\b|TOP\b|[\w.]{1,64}[ \t]*(?:,|[ \t]FROM\b|[ \t]AS\b))"
    r"|select[ \t]+(?:\*|[\w.]{1,64}[ \t]*,)"
    r"|(?:INSERT[ \t]+INTO|DELETE[ \t]+FROM|UPDATE[ \t]+\w{1,64}[ \t]+SET|CREATE[ \t]+(?:TABLE|INDEX|VIEW)"
    r"|ALTER[ \t]+TABLE|DROP[ \t]+TABLE)\b"
    r")"
)
# Chaîne littérale ou commentaire sur la ligne : du texte libre, donc peut-être un nom (« WHERE nom = 'Dupont' »).
# String literal or comment on the line: free text, so possibly a name.
_FREE_TEXT_RE = re.compile(r"[\"'`«“]|//|/\*|<!--|(?<!\S)(?:#|--)[ \t]")
_TERMINAL = frozenset(".!?…:;")
# Ligne longue sans ponctuation finale : retour à la ligne d'un PDF ou d'un courriel, pas une liste.
# Long line without final punctuation: a PDF or e-mail hard wrap, not a list item.
SOFT_WRAP_MIN = 50


def _readable(text: str, start: int, end: int) -> bool:
    """Deux lettres de suite hors des jetons opaques / two letters in a row outside opaque tokens."""
    if _TWO_LETTERS_RE.search(text, start, end) is None:
        return False
    pos = start
    for run in _LONG_RUN_RE.finditer(text, start, end):
        if _OPAQUE_MARK_RE.search(text, run.start(), run.end()) is None:
            continue  # « Charles-Édouard-de-La-Rochefoucauld » reste lisible / stays readable
        if _TWO_LETTERS_RE.search(text, pos, run.start()) is not None:
            return True
        pos = run.end()
    return _TWO_LETTERS_RE.search(text, pos, end) is not None


def skip_line(text: str, start: int, end: int) -> bool:
    """Ligne sans rien à lire pour le modèle : chiffres, jetons opaques, ou instruction de code sans chaîne ni
    commentaire. Line with nothing for the model: digits, opaque tokens, or a code statement without any string
    literal or comment. Les e-mails, liens, JSON et commentaires passent : ils portent souvent des noms.
    """
    if not _readable(text, start, end):
        return True
    return _CODE_RE.match(text, start, end) is not None and _FREE_TEXT_RE.search(text, start, end) is None


def _strip(text: str, start: int, end: int) -> Bounds:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _sentences(text: str, start: int, end: int) -> list[Bounds]:
    """Phrases d'une ligne ; « M. Dupont », « art. 12 », « J. Martin » ne coupent pas / abbreviation-aware."""
    pieces: list[Bounds] = []
    cursor = start
    for m in _BOUNDARY_RE.finditer(text, start, end):
        punct_end = m.start() + 1
        if text[m.start()] == "." and (punct_end == end or text[punct_end] != "."):
            before = _WORD_BEFORE_RE.search(text, max(cursor, m.start() - 24), m.start())
            if before is not None:
                word = before.group(1)
                if len(word) == 1 or fold(word) in ABBREVIATIONS:
                    continue
        piece = _strip(text, cursor, m.end())
        if piece[1] > piece[0]:
            pieces.append(piece)
        cursor = m.end()
    piece = _strip(text, cursor, end)
    if piece[1] > piece[0]:
        pieces.append(piece)
    return pieces


def split_units(text: str, segments: Sequence[Bounds]) -> list[Bounds]:
    """Unités (phrases) à analyser, sans traverser de segment, de paragraphe ni de clôture de bloc de code.

    Units (sentences) to analyse, never crossing a segment, a paragraph or a code fence. Une ligne non terminée
    se poursuit sur la suivante si celle-ci commence en minuscule, ou par une lettre après une ligne longue
    (retour à la ligne de PDF) : un saut de ligne interne à une unité est donc toujours un retour souple.
    Dans un bloc ``` (journaux, données, code), chaque ligne est une unité et passe le même filtre qu'ailleurs.
    An unfinished line continues on the next one if it starts in lowercase, or with a letter after a long line
    (PDF hard wrap). Inside a ``` block, every line is its own unit and goes through the same line filter.
    """
    units: list[Bounds] = []
    for lo, hi in segments:
        pending: Bounds | None = None
        pending_line = 0
        in_fence = False
        pos = lo
        while pos < hi:
            newline = text.find("\n", pos, hi)
            line_end = hi if newline < 0 else newline
            pieces: list[Bounds] = []
            if _FENCE_RE.match(text, pos, line_end):
                in_fence = not in_fence
            elif not skip_line(text, pos, line_end):
                pieces = _sentences(text, pos, line_end)
            if pending is not None and pieces and text[pending[1] - 1] not in _TERMINAL and (
                    text[pieces[0][0]].islower() or (pending_line >= SOFT_WRAP_MIN and text[pieces[0][0]].isalpha())):
                pieces[0] = (pending[0], pieces[0][1])
            elif pending is not None:
                units.append(pending)
            pending = None
            if in_fence:
                units.extend(pieces)
            elif pieces:
                units.extend(pieces[:-1])
                pending = pieces[-1]
                pending_line = line_end - pos
            pos = line_end + 1
        if pending is not None:
            units.append(pending)
    return units


def has_signal(text: str, folded: str, start: int, end: int) -> bool:
    """Indice d'entité : majuscule hors mot d'attaque courant, ou civilité / entity cue in the unit."""
    first = _WORD_RE.search(text, start, end)
    if first is None:
        return False
    if text[first.start()].isupper() and folded[first.start():first.end()] not in COMMON_STARTERS:
        return True
    if CAPITAL_RE.search(text, first.end(), end) is not None:
        return True
    return _HONORIFIC_RE.search(folded, start, end) is not None


def plan_windows(length: int, word_starts: Sequence[bool] | None, width: int, overlap: int,
                 ) -> list[tuple[int, int, int, int]]:
    """Fenêtres (début, fin, début possédé, fin possédée) couvrant `length` jetons.

    Windows (start, end, owned start, owned end) over `length` tokens. Les fenêtres se chevauchent de
    `overlap` jetons et commencent sur un début de mot ; chaque jeton appartient à la fenêtre où il est le
    plus central / windows overlap and start on a word; each token belongs to the window where it is most
    central, so an entity cut by one window is seen whole by the next.
    """
    if length <= width:
        return [(0, length, 0, length)]
    spans: list[Bounds] = []
    start = 0
    while True:
        end = min(length, start + width)
        spans.append((start, end))
        if end == length:
            break
        nxt = end - overlap
        if word_starts is not None:
            floor = max(start + 1, end - 2 * overlap)
            probe = nxt
            while probe > floor and not word_starts[probe]:
                probe -= 1
            if word_starts[probe]:
                nxt = probe
        start = max(nxt, start + 1)
    windows: list[tuple[int, int, int, int]] = []
    owned = 0
    for i, (start, end) in enumerate(spans):
        cut = (spans[i + 1][0] + end) // 2 if i + 1 < len(spans) else length
        windows.append((start, end, owned, cut))
        owned = cut
    return windows
