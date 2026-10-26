"""RTF -> Markdown, analyseur maison linéaire / in-house linear RTF parser.

Jetons par expression régulière (aucune boucle par caractère), pile explicite (aucune récursion),
\\binN sauté sans analyse, \\uN avec repli \\ucN et paires de substitution, \\'hh décodés par lots selon la
page de code de la police courante (\\fcharset), titres (\\outlinelevel), listes et tableaux GFM.
Jamais émis : métadonnées (\\info, \\docvar), tables de polices et de styles, images, objets OLE, codes de
champ, révisions supprimées (\\deleted) ; texte masqué (\\v) et commentaires selon les options.
Regex tokens (no per-character loop), explicit stack (no recursion), \\binN skipped unparsed, \\uN with
\\ucN fallback and surrogate pairs, \\'hh decoded in batches with the current font's code page, headings,
lists and GFM tables. Never output: metadata, font and style tables, pictures, OLE objects, field codes,
tracked deletions; hidden text (\\v) and comments per options.
"""

from __future__ import annotations

import codecs
import re
from functools import lru_cache

from ..documents import ConvertedDocument, DocumentOptions
from ._base import Report, Source, corrupt, output_limit, too_large
from ._markdown import gfm_table, heading, inline

_TOKEN_RE = re.compile(
    r"\\([a-zA-Z]{1,32})(-?[0-9]{1,10})? ?"  # 1-2 : mot de contrôle et paramètre / control word, parameter
    r"|\\'([0-9a-fA-F]{2})"  # 3 : octet hexadécimal / hex byte
    r"|\\(.)"  # 4 : symbole de contrôle / control symbol
    r"|([{}])"  # 5 : groupe / group
    r"|([^\\{}\r\n]{1,65536})"  # 6 : texte / text
    r"|[\r\n]{1,65536}",  # fins de ligne brutes, sans effet en RTF / raw line ends, meaningless in RTF
    re.DOTALL,
)
# Destinations jamais lues (texte et sous-groupes ignorés) / destinations never read.
_SKIPPED = frozenset({
    "colortbl", "stylesheet", "objdata", "objclass", "objname", "nonshppict", "shprslt", "sp", "fldinst",
    "tc", "tcn", "xe", "txe", "rxe", "bkmkstart", "bkmkend", "atnid", "atnauthor", "atntime", "atndate", "atnref",
    "atnparent", "atnicn", "atrfstart", "atrfend", "revtbl", "rsidtbl", "listtable", "listoverridetable",
    "generator", "themedata", "colorschememapping", "datastore", "latentstyles", "xmlnstbl", "mmathPr",
    "pgdsctbl", "filetbl", "template", "do", "pn", "pnseclvl", "fchars", "lchars", "aftnsep", "aftnsepc",
    "aftncn", "ftnsep", "ftnsepc", "ftncn", "protusertbl", "wgrffmtfilter", "pgptbl", "formfield", "datafield",
    "picprop", "blipuid", "hl", "falt", "panose", "fname", "oleclsid", "passwordhash", "keycode",
})
_METADATA = frozenset({"userprops", "docvar"})
_KEPT_STARRED = frozenset({"shpinst", "shppict", "annotation"})
_INFO_FIELDS = frozenset({"title", "subject", "author", "manager", "company", "operator", "category", "keywords",
                          "comment", "doccomm", "hlinkbase", "creatim", "revtim", "printim", "buptim"})
_CHARACTERS = {
    "line": "\n", "tab": "\t", "lquote": "\N{LEFT SINGLE QUOTATION MARK}",
    "rquote": "\N{RIGHT SINGLE QUOTATION MARK}", "ldblquote": "\N{LEFT DOUBLE QUOTATION MARK}",
    "rdblquote": "\N{RIGHT DOUBLE QUOTATION MARK}", "bullet": "\N{BULLET}", "endash": "\N{EN DASH}",
    "emdash": "\N{EM DASH}", "enspace": "\N{EN SPACE}", "emspace": "\N{EM SPACE}",
    "qmspace": "\N{FOUR-PER-EM SPACE}", "nestcell": " ", "nestrow": " ",
}
_SYMBOLS = {"\\": "\\", "{": "{", "}": "}", "~": "\xa0", "_": "-"}
# \fcharset -> page de code Windows / Windows code page.
_CHARSETS = {77: 10000, 128: 932, 129: 949, 130: 1361, 134: 936, 136: 950, 161: 1253, 162: 1254, 163: 1258,
             177: 1255, 178: 1256, 186: 1257, 204: 1251, 222: 874, 238: 1250, 254: 437, 255: 850}
_MAX_DEPTH = 10_000
# (skip, uc, font, deleted, hidden, mode, closer, outline, list_level, in_table)
_GroupState = tuple[bool, int, int, bool, bool, str, str, int, int, bool]


@lru_cache(maxsize=64)  # borné : la page de code vient du document / bounded: the code page comes from the document
def _codec(code_page: int) -> str:
    name = "mac_roman" if code_page == 10000 else f"cp{code_page}"
    try:
        return codecs.lookup(name).name
    except LookupError:
        return "cp1252"


class _Parser:
    """Machine à états RTF ; l'état de groupe (formatage) est empilé à chaque « { » / group state is stacked."""

    def __init__(self, options: DocumentOptions, report: Report) -> None:
        self.options = options
        self.report = report
        self.limit = output_limit(options)
        self.size = 0
        self.blocks: list[tuple[str, bool]] = []  # (Markdown, élément de liste / list item)
        self.para: list[str] = []
        self.row: list[str] = []
        self.table: list[list[str]] = []
        self.cells = 0
        # Polices / fonts
        self.ansi = "cp1252"
        self.default_font = -1
        self.font_def = -1
        self.charsets: dict[int, int] = {}
        self.code_pages: dict[int, int] = {}
        self.pending = bytearray()
        self.fallback = 0
        self.high = 0
        self.dest_pending = False
        self.starred = False
        self.marker = False  # puce \listtext ou \pntext vue pour ce paragraphe / bullet seen for this paragraph
        self.dropping = ""  # clé du rapport de la série en cours d'omission / report key of the dropped run
        # État de groupe empilé / stacked group state
        self.skip = False
        self.uc = 1
        self.font = -1
        self.deleted = False
        self.hidden = False
        self.mode = ""  # "", "fonttbl", "info" ou "note"
        self.closer = ""
        self.outline = -1
        self.list_level = -1
        self.in_table = False
        self.stack: list[_GroupState] = []

    # --- boucle principale / main loop ---

    def parse(self, s: str) -> str:
        match = _TOKEN_RE.match
        pos, end = 0, len(s)
        while pos < end:
            m = match(s, pos)
            if m is None:
                break
            pos = m.end()
            kind = m.lastindex
            if kind == 3:
                self._hex(int(m.group(3), 16))
                continue
            if kind is None:
                continue  # fin de ligne brute : ne coupe pas une suite d'octets / raw line end: keeps a byte run
            if self.pending:
                self._flush_bytes()
            if kind == 6:
                self._text(m.group(6))
            elif kind <= 2:
                word, param = m.group(1), m.group(2)
                value = int(param) if param is not None else None
                if word == "bin":
                    if value is not None and value > 0:
                        pos = min(end, pos + value)  # binaire brut, jamais analysé / raw binary, never parsed
                    continue
                self._word(word, value)
            elif kind == 5:
                if m.group(5) == "{":
                    self._open()
                else:
                    self._close()
            else:
                self._symbol(m.group(4))
        if self.pending:
            self._flush_bytes()
        self._end_paragraph()
        self._flush_table()
        parts: list[str] = []
        for index, (text, is_item) in enumerate(self.blocks):
            if index:
                parts.append("\n" if is_item and self.blocks[index - 1][1] else "\n\n")
            parts.append(text)
        return "".join(parts)

    # --- groupes / groups ---

    def _open(self) -> None:
        self.stack.append((self.skip, self.uc, self.font, self.deleted, self.hidden, self.mode, self.closer,
                           self.outline, self.list_level, self.in_table))
        if len(self.stack) > _MAX_DEPTH:
            raise corrupt("rtf")
        self.closer = ""
        self.fallback = 0
        self.dest_pending = True
        self.starred = False

    def _close(self) -> None:
        if self.closer and not self.skip:
            while self.para and not self.para[-1].strip():
                self.para.pop()
            if self.para:
                self.para[-1] = self.para[-1].rstrip()
            self.para.append(self.closer)
        if self.stack:
            (self.skip, self.uc, self.font, self.deleted, self.hidden, self.mode, self.closer, self.outline,
             self.list_level, self.in_table) = self.stack.pop()
        self.fallback = 0
        self.dest_pending = self.starred = False

    def _destination(self, word: str) -> bool:
        """Traite un mot de destination en tête de groupe ; True s'il est consommé / True when consumed."""
        starred, self.starred = self.starred, False
        if word == "fonttbl":
            self.skip, self.mode = True, "fonttbl"
        elif word == "info":
            self.skip, self.mode = True, "info"
        elif word in ("footnote", "annotation"):
            if word == "annotation" and not self.options.include_comments:
                self.report.drop("comments")
                self.skip = True
            else:
                self.para.append(" [note : " if word == "footnote" else " [commentaire : ")
                self.closer, self.mode = "]", "note"
        elif word in ("listtext", "pntext"):
            self.marker = True
            self.skip = True
        elif word == "pict":
            self.report.drop("images")
            self.skip = True
        elif word == "object":
            # Données OLE ignorées ; le rendu (\result) reste lu / OLE data skipped; the rendering (\result) is read.
            self.report.drop("embedded_objects")
        elif word in _METADATA:
            self.report.drop("metadata")
            self.skip = True
        elif word in _SKIPPED or (starred and word not in _KEPT_STARRED):
            self.skip = True
        else:
            return False
        return True

    # --- jetons / tokens ---

    def _word(self, word: str, value: int | None) -> None:
        if self.dest_pending:
            self.dest_pending = False
            if not self.skip and self._destination(word):
                return
        if self.skip:
            if self.mode == "fonttbl":
                self._font_table(word, value)
            elif self.mode == "info" and word in _INFO_FIELDS:
                self.report.drop("metadata")
            return
        if word in _SKIPPED or word == "pict":
            self._destination(word)
            return
        if word == "par" or word == "sect" or word == "page":
            if self.mode == "note" or self.in_table:
                self.para.append(" ")
            else:
                self._end_paragraph()
        elif word in _CHARACTERS:
            self._text(_CHARACTERS[word])
        elif word == "u" and value is not None:
            self._unicode(value)
        elif word == "cell":
            self._end_cell()
        elif word == "row":
            self._end_row()
        elif word == "pard":
            self.outline, self.list_level, self.in_table = -1, -1, False
        elif word == "intbl":
            self.in_table = True
        elif word == "outlinelevel" and value is not None:
            self.outline = value
        elif word == "ls":
            self.list_level = max(self.list_level, 0)
        elif word == "ilvl" and value is not None:
            self.list_level = max(value, 0)
        elif word == "plain":
            self.deleted = self.hidden = False
            self.font = self.default_font
        elif word == "deleted":
            self.deleted = value != 0
        elif word == "v":
            self.hidden = value != 0
        elif word == "f" and value is not None:
            self.font = value
        elif word == "uc" and value is not None:
            self.uc = min(max(value, 0), 16)
        elif word == "deff" and value is not None:
            self.default_font = self.font = value
        elif word == "ansicpg" and value:
            self.ansi = _codec(value)
        elif word in ("mac", "pc", "pca"):
            self.ansi = _codec({"mac": 10000, "pc": 437, "pca": 850}[word])

    def _font_table(self, word: str, value: int | None) -> None:
        if value is None:
            return
        if word == "f":
            self.font_def = value
        elif word == "fcharset":
            self.charsets[self.font_def] = value
        elif word == "cpg":
            self.code_pages[self.font_def] = value

    def _symbol(self, char: str) -> None:
        if char == "*":
            self.starred = self.dest_pending
            return
        self.dest_pending = False
        if char in ("\n", "\r"):
            self._word("par", None)
        elif char in _SYMBOLS:
            if self.fallback:
                self.fallback -= 1
            else:
                self._text(_SYMBOLS[char])

    def _hex(self, byte: int) -> None:
        self.dest_pending = False
        if self.fallback:
            self.fallback -= 1
        elif not self.skip:
            self.pending.append(byte)

    def _flush_bytes(self) -> None:
        data = bytes(self.pending)
        self.pending.clear()
        font = self.font
        code_page = self.code_pages.get(font) or _CHARSETS.get(self.charsets.get(font, 0))
        self._text(data.decode(_codec(code_page) if code_page else self.ansi, errors="replace"))

    def _unicode(self, value: int) -> None:
        # \uN est un entier signé sur 16 bits ; hors bornes : U+FFFD / signed 16-bit; out of range: U+FFFD.
        code = value + 65536 if -32768 <= value < 0 else value
        if 0xD800 <= code < 0xDC00:
            self.high = code
        else:
            if 0xDC00 <= code < 0xE000:
                code = 0x10000 + ((self.high - 0xD800) << 10) + (code - 0xDC00) if self.high else 0xFFFD
            elif 0xF020 <= code <= 0xF0FF:  # zone privée des polices Symbol / Symbol-font private area
                code -= 0xF000
            elif not 0 <= code <= 0x10FFFF:
                code = 0xFFFD
            self.high = 0
            self._text(chr(code))
        self.fallback = self.uc  # caractères de repli ANSI à ignorer / ANSI fallback characters to skip

    def _text(self, text: str) -> None:
        self.dest_pending = False
        if self.skip:
            return
        if self.fallback:
            cut = min(self.fallback, len(text))
            text, self.fallback = text[cut:], self.fallback - cut
            if not text:
                return
        key = "tracked_deletions" if self.deleted else (
            "hidden_text" if self.hidden and not self.options.include_hidden else "")
        if key:
            if self.dropping != key:
                self.report.drop(key)
                self.dropping = key
            return
        self.dropping = ""
        self.size += len(text)
        if self.size > self.limit:
            raise too_large("texte extrait (caractères)", "extracted text (characters)", self.limit)
        self.para.append(text)

    # --- paragraphes et tableaux / paragraphs and tables ---

    def _end_paragraph(self) -> None:
        text = "".join(self.para).strip()
        marker, self.marker = self.marker, False
        self.para.clear()
        if self.table and not self.in_table:
            self._flush_table()
        if not text:
            return
        if 0 <= self.outline < 9:
            self.blocks.append((heading(self.outline + 1, text), False))
        elif self.list_level >= 0 or marker:
            self.blocks.append((f"{'  ' * min(max(self.list_level, 0), 8)}- {inline(text)}", True))
        else:
            self.blocks.append((text, False))

    def _end_cell(self) -> None:
        self.row.append(inline("".join(self.para)))
        self.para.clear()
        self.cells += 1
        if self.cells > self.options.max_cells:
            raise too_large("cellules de tableau", "table cells", self.options.max_cells)

    def _end_row(self) -> None:
        if any(piece.strip() for piece in self.para):
            self._end_cell()  # dernière cellule sans \cell / last cell without \cell
        self.para.clear()
        if self.row:
            self.table.append(self.row)
            self.row = []

    def _flush_table(self) -> None:
        self._end_row()
        if self.table:
            self.blocks.append((gfm_table(self.table), False))
            self.table = []


def rtf_to_markdown(data: bytes, options: DocumentOptions, report: Report) -> str:
    """Convertit des octets RTF (aussi utilisé pour les corps RTF des MSG) / converts RTF bytes (also MSG bodies)."""
    start = data.find(b"{\\rtf")
    if start < 0:
        raise corrupt("rtf")
    # latin-1 : un octet = un caractère ; le RTF est en 7 bits, le reste passe par \'hh et \uN.
    # latin-1: one byte = one char; RTF is 7-bit, everything else goes through \'hh and \uN.
    return _Parser(options, report).parse(data[start:].decode("latin-1"))


def convert(source: Source, options: DocumentOptions) -> ConvertedDocument:
    report = Report()
    return report.document(rtf_to_markdown(source.data, options, report), "rtf")


__all__ = ["convert", "rtf_to_markdown"]
