"""Pipeline tableur : garde, lecture, structure, typage, détection, rendu / spreadsheet pipeline.

Une seule portée (clé éphémère) pour tout le classeur : même valeur, même balise sur toutes les feuilles ;
les valeurs sont dédoublonnées par colonne avant la détection. One scope (ephemeral key) for the whole
workbook: same value, same placeholder on every sheet; values are deduplicated per column before detection.
"""

from __future__ import annotations

import re
import threading
import weakref
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from operator import itemgetter
from pathlib import PurePath
from time import perf_counter
from typing import Any

from .._text import fold
from ..documents import ConversionTimeoutError, DocumentOptions, DocumentResult, DocumentTooLargeError
from ..engine import NOTICE_EN, NOTICE_FR, Anonymizer
from ..labels import LABELS
from ..locale import detect_language
from ..operators import FORCED_REPLACE, Operator, get_operator
from ..operators import replace as replace_operator
from ..sanitize import sanitize_output
from ..scope import PLACEHOLDER_RE, Scope
from ..types import PRIORITY_HEURISTIC, Span
from ..validators.intl import card
from ._columns import DETECT, MASK, YEAR, ColumnType, ColumnTyper, sample_evenly
from ._package import BINARY_MAGICS, Package
from ._persons import ANY_PLACEHOLDER_RE, KnownPersons, split_people
from ._reader import RawSheet, ReadResult, load, load_sandboxed
from ._render import TEXTS, FormView, SheetView, TableView, TextView, render_sheets
from ._structure import Region, detect_regions
from ._values import FIXED_WIDTHS, column_letter, is_null_marker, may_hold_identifier, texts_of

# Taille d'un appel au moteur (caractères) : borne la mémoire / engine call size (characters): bounds memory.
_CHUNK_CHARS = 2_000_000
_LANGUAGE_SAMPLE = 3_000
_LANGUAGE_CELLS = 20_000
_TABLE_FORMATS = ("markdown", "csv")
_ALNUM_RE = re.compile(r"[^\W_]")
# `[` + 42 caractères + `]` : la plus longue balise que `ANY_PLACEHOLDER_RE` reconnaît / longest it matches.
_SHORT_PLACEHOLDER = 44

_TYPERS: weakref.WeakKeyDictionary[Anonymizer, ColumnTyper] = weakref.WeakKeyDictionary()
_TYPERS_LOCK = threading.Lock()


def column_typer(anonymizer: Anonymizer) -> ColumnTyper:
    """Typeur compilé une fois par Anonymizer / typer compiled once per Anonymizer."""
    with _TYPERS_LOCK:
        typer = _TYPERS.get(anonymizer)
        if typer is None:
            typer = _TYPERS[anonymizer] = ColumnTyper(anonymizer.packs, anonymizer.settings)
        return typer


def anonymize_workbook(data: bytes, filename: str, anonymizer: Anonymizer,
                       options: DocumentOptions) -> DocumentResult:
    """Classeur ou CSV -> Markdown anonymisé ; aucune valeur d'origine dans la sortie ni le rapport.

    Workbook or CSV -> anonymised Markdown; no original value in the output or the report.
    """
    # Le nom de fichier porte souvent des données personnelles : seule l'extension est gardée (titre, nom
    # de la feuille d'un CSV). File names often carry personal data: only the extension is kept.
    neutral = "document" + PurePath(filename.replace("\\", "/")).suffix.lower()
    return _Job(data, neutral, anonymizer, options).run()


@dataclass(slots=True)
class _Column:
    """Colonne de données d'un tableau / data column of a table."""

    column: int
    header: str
    header_index: int
    ctype: ColumnType
    rows: list[int]
    counts: Counter[str]
    raws: dict[str, Any]
    texts: list[str] = field(default_factory=list)  # texte de chaque ligne de données / each data row's text
    segments: dict[str, int] = field(default_factory=dict)
    direct: dict[str, str] = field(default_factory=dict)  # texte -> valeur canonique, sans moteur / no engine
    final: dict[str, str] = field(default_factory=dict)
    by_row: dict[int, str] | None = None


@dataclass(slots=True)
class _Field:
    """Champ d'une feuille formulaire (libellé -> valeur) / form field (label -> value)."""

    row: int
    label: str
    label_index: int
    ctype: ColumnType
    text: str
    raw: Any
    segment: int | None = None
    final: str | None = None


@dataclass(slots=True)
class _Sheet:
    raw: RawSheet
    texts: list[list[str]]
    non_empty: int = 0
    regions: list[Region] = field(default_factory=list)
    columns: dict[int, list[_Column]] = field(default_factory=dict)
    fields: dict[int, list[_Field]] = field(default_factory=dict)
    cells: dict[tuple[int, int], int] = field(default_factory=dict)
    name_index: int = -1


class _Job:
    """État d'une requête, jamais partagé entre threads / per-request state, never shared between threads."""

    def __init__(self, data: bytes, filename: str, anonymizer: Anonymizer, options: DocumentOptions) -> None:
        self.data = data
        self.filename = filename
        self.anonymizer = anonymizer
        self.options = options
        self.started = perf_counter()
        self.timings: dict[str, float] = {}
        self.typer = column_typer(anonymizer)
        self.operators = anonymizer.settings.operators
        self.allow = frozenset(fold(term).strip() for term in anonymizer.settings.allow_list)
        self.segments: dict[tuple[frozenset[str], str], int] = {}
        self.texts: list[str] = []
        self.forced: list[frozenset[str]] = []
        self.outputs: list[str] = []
        self.reports: list[dict[str, Any]] = []
        self.persons = KnownPersons()
        self.tally: Counter[str] = Counter()
        self.truncated_cards = 0
        self.language = "fr"
        self.scope: Scope | None = None
        self.placeholders: dict[str, Callable[[str, str], str]] = {}

    # --- déroulé / flow ---

    def run(self) -> DocumentResult:
        options = self.options
        if len(self.data) > options.max_bytes:
            raise DocumentTooLargeError(f"Fichier trop volumineux / file too large (> {options.max_bytes} octets)")
        native = self.anonymizer.settings.native  # noyau Rust permis / Rust core allowed
        if options.sandbox and self.data.startswith(BINARY_MAGICS):
            remaining = options.timeout_s - (perf_counter() - self.started)
            package, read = load_sandboxed(self.data, self.filename, options, max(remaining, 1e-3), native)
        else:
            package, read = load(self.data, self.filename, options, self.check_time, native)
        self._lap("read")
        detected = self._detect_language(read.sheets)
        self.scope = self.anonymizer.new_scope(detected)
        try:
            if self.scope.label_language in TEXTS:
                self.language = self.scope.label_language
            sheets = [self._prepare(raw) for raw in read.sheets]
            for sheet in sheets:
                sheet.name_index = self._add(sheet.raw.name)
            self._lap("structure")
            for text in self.texts:
                if "[" in text:
                    self.scope.reserve(text)  # balises déjà présentes dans l'entrée / placeholders already in input
            # Colonnes d'identifiants d'abord (numérotation dans l'ordre du tableau), puis noms connus masqués
            # avant la détection : le moteur ne les voit jamais. Identifier columns first (numbered in table
            # order), then known names masked before detection: the engine never sees them.
            self._mask_person_columns(sheets)
            self._mask_direct_values(sheets)
            self._propagate(self.texts)
            self._run_engine()
            self._lap("detection")
            if self._upgrade_person_columns(sheets):
                self._propagate(self.outputs)
            for sheet in sheets:
                self._finalize(sheet)
            views = [self._view(sheet) for sheet in sheets]
            markdown = self._markdown(views, sheets, package, read)
            self._lap("render")
        finally:
            self.scope.close()
        return self._result(markdown, views, sheets, package, read, detected)

    def check_time(self) -> None:
        if perf_counter() - self.started > self.options.timeout_s:
            raise ConversionTimeoutError("Délai de traitement dépassé / processing timeout")

    def _lap(self, name: str) -> None:
        elapsed = (perf_counter() - self.started) * 1000
        self.timings[name] = round(elapsed - sum(self.timings.values()), 3)
        self.check_time()

    @staticmethod
    def _detect_language(sheets: list[RawSheet]) -> str:
        sample: list[str] = []
        size = seen = 0
        for sheet in sheets:
            for row in sheet.rows:
                for value in row:
                    seen += 1
                    if type(value) is str and value:
                        sample.append(value)
                        size += len(value) + 1
                    if size >= _LANGUAGE_SAMPLE or seen >= _LANGUAGE_CELLS:
                        return detect_language(fold(" ".join(sample)))
        return detect_language(fold(" ".join(sample)))

    def _scope(self) -> Scope:
        if self.scope is None:  # pragma: no cover - garde-fou / safeguard
            raise RuntimeError("Portée absente / no scope")
        return self.scope

    # --- structure et typage / structure and typing ---

    def _groups(self, text: str) -> frozenset[str]:
        return self.anonymizer.context_groups(text)

    def _is_label(self, text: str) -> bool:
        return self.typer.is_label(text, self._groups)

    def _add(self, text: str, forced: frozenset[str] = frozenset()) -> int:
        """Segment dédoublonné pour le moteur / deduplicated engine segment."""
        key = (forced, text)
        index = self.segments.get(key)
        if index is None:
            index = self.segments[key] = len(self.texts)
            self.texts.append(text)
            self.forced.append(forced)
        return index

    def _prepare(self, raw: RawSheet) -> _Sheet:
        booleans = ("VRAI", "FAUX") if self.language == "fr" else ("TRUE", "FALSE")
        texts = texts_of(raw.rows, booleans)
        scope = self._scope()
        for row in texts:
            # Balises déjà présentes dans n'importe quelle cellule, même hors moteur (colonnes de noms) : jamais
            # réattribuées. Placeholders already in any cell, even outside the engine (name columns): never reused.
            line = "\t".join(row)
            if "[" in line:
                scope.reserve(line)
        sheet = _Sheet(raw, texts, sum(len(row) - row.count("") for row in texts))
        sheet.regions = detect_regions(texts, raw.rows, raw.merged, raw.tables, self._is_label)
        for number, region in enumerate(sheet.regions):
            for row in (*region.title_rows, *region.note_rows):
                self._add_cells(sheet, row, region.columns)
            if region.kind == "table":
                sheet.columns[number] = self._table(sheet, region)
            elif region.kind == "form":
                sheet.fields[number] = self._form(sheet, region)
            else:
                for row in region.data_rows:
                    self._add_cells(sheet, row, region.columns)
        self.check_time()
        return sheet

    def _add_cells(self, sheet: _Sheet, row: int, columns: Iterable[int],
                   forced: frozenset[str] = frozenset()) -> None:
        for column in columns:
            text = sheet.texts[row][column]
            if text and may_hold_identifier(sheet.raw.rows[row][column], text):
                sheet.cells[(row, column)] = self._add(text, forced)

    def _table(self, sheet: _Sheet, region: Region) -> list[_Column]:
        texts, raws = sheet.texts, sheet.raw.rows
        data = [row for row in region.data_rows if row not in region.total_rows]
        # Lignes de données (mêmes listes, modifiées en place par `_pad`) / data rows (same lists, padded in place).
        data_texts, data_raws = [texts[row] for row in data], [raws[row] for row in data]
        columns: list[_Column] = []
        add = self._add
        for position, column in enumerate(region.columns):
            header = region.headers[position]
            forced = self._groups(header) if header else frozenset()
            padded = self._pad(texts, data, column, header)
            pick = itemgetter(column)
            column_texts = list(map(pick, data_texts))
            column_raws = list(map(pick, data_raws))
            # Effectifs dans l'ordre d'apparition, puis première valeur brute de chaque texte : une cellule texte
            # non complétée est sa propre valeur brute ; sinon parcours inverse (la première occurrence l'emporte).
            # Counts in order of appearance, then each text's first raw value: an unpadded text cell is its own
            # raw value; otherwise a reverse walk (the first occurrence wins).
            counts = Counter(column_texts)
            counts.pop("", None)
            if not padded and set(map(type, column_raws)) <= {str}:
                first = dict(zip(counts, counts, strict=True))
            else:
                raw_of = dict(zip(reversed(column_texts), reversed(column_raws), strict=True))
                first = dict(zip(counts, map(raw_of.__getitem__, counts), strict=True))
            sample = [(raw, text) for text, raw in sample_evenly(list(first.items())) if not is_null_marker(text)]
            ctype = self.typer.classify(header, sample, counts.total(), forced)
            entry = _Column(column, header, add(header) if header else -1, ctype, data, counts, first, column_texts)
            if ctype.action == DETECT or (ctype.action == MASK and ctype.label != "PERSON"):
                values = self.typer.direct_values(ctype.label, first) if ctype.action == MASK else None
                segments, cell_forced = entry.segments, ctype.forced
                for index, (text, raw) in enumerate(first.items()):
                    value = values[index] if values is not None else None
                    if value is not None:
                        entry.direct[text] = value
                    elif type(raw) is str or may_hold_identifier(raw, text):  # texte non vide : toujours / always
                        segments[text] = add(text, cell_forced)
            columns.append(entry)
            for row in region.total_rows:
                self._add_cells(sheet, row, (column,), forced)
        return columns

    def _pad(self, texts: list[list[str]], rows: Iterable[int], column: int, header: str) -> bool:
        """Zéros initiaux d'après l'en-tête (code postal, téléphone, SIREN…) / leading zeros from the header.

        `pad_fixed_width` en ligne, la longueur testée d'abord ; True si un texte a changé.
        `pad_fixed_width` inlined, length tested first; True when a text changed.
        """
        match = self.typer.match_header(header) if header else None
        changed = False
        if match is not None and match.label in FIXED_WIDTHS:
            width, minimum = FIXED_WIDTHS[match.label]
            for row in rows:
                cells = texts[row]
                text = cells[column]
                if minimum <= len(text) < width and text.isdigit() and text.isascii():
                    cells[column] = text.zfill(width)
                    changed = True
        return changed

    def _form(self, sheet: _Sheet, region: Region) -> list[_Field]:
        texts, raws = sheet.texts, sheet.raw.rows
        fields: list[_Field] = []
        for row, label_column, value_column in region.pairs:
            label = texts[row][label_column]
            header = label.strip().rstrip(":").strip()
            self._pad(texts, (row,), value_column, header)
            text, raw = texts[row][value_column], raws[row][value_column]
            forced = self._groups(header) if header else frozenset()
            values = [(raw, text)] if text and not is_null_marker(text) else []
            ctype = self.typer.classify(header, values, len(values), forced, single=True)
            entry = _Field(row, label, self._add(label) if label else -1, ctype, text, raw)
            if text and may_hold_identifier(raw, text) and (
                    ctype.action == DETECT or (ctype.action == MASK and ctype.label != "PERSON")):
                entry.segment = self._add(text, ctype.forced)
            fields.append(entry)
        return fields

    # --- détection / detection ---

    def _run_engine(self) -> None:
        scope = self._scope()
        start = size = 0
        for end, text in enumerate(self.texts, 1):
            size += len(text) + 2
            if size < _CHUNK_CHARS and end < len(self.texts):
                continue
            outputs, report = self.anonymizer.anonymize_segments(self.texts[start:end], scope, self.forced[start:end])
            self.outputs.extend(outputs)
            self.reports.append(report)
            start, size = end, 0
            self.check_time()

    def _operator(self, entity: str, label: str, default: str = "replace") -> Operator:
        name = "replace" if entity in FORCED_REPLACE else self.operators.get(entity) or self.operators.get(label)
        return get_operator(name or default)

    def _operate(self, entity: str, label: str, value: str, original: str, default: str = "replace") -> str:
        """Opérateur configuré (ou défaut) sur une cellule entière / configured operator on a whole cell."""
        if self.allow and fold(original).strip() in self.allow:
            return original
        operator = self._operator(entity, label, default)
        if operator is replace_operator:  # balise directe, sans zone intermédiaire / direct placeholder, no span
            placeholder = self.placeholders.get(label)
            if placeholder is None:
                placeholder = self.placeholders[label] = _placeholder_for(self._scope(), label)
            return placeholder(entity, value or original)
        span = Span(0, len(original), entity, label, "tabular", 1.0, PRIORITY_HEURISTIC, value)
        return operator(span, original, self._scope())

    def _kept(self, text: str) -> str:
        """Valeur conservée hors moteur (« n/a »…), tout de même nettoyée / value kept outside the engine, sanitised."""
        return sanitize_output(text) if self.anonymizer.settings.sanitize else text

    def _person_cell(self, text: str) -> str:
        """Cellule d'une colonne de personnes ; « n/a » ou balise déjà présente (entrée déjà anonymisée) conservés.

        Cell of a person column; "n/a" or an existing placeholder (already anonymised input) is kept as is.
        """
        return self._kept(text) if is_null_marker(text) or _covered(text) else self._person(text)

    def _person(self, text: str) -> str:
        """Une cellule de nom ; plusieurs personnes (« A ; B ») reçoivent chacune leur balise / one tag each."""
        pieces = split_people(text)
        if pieces is None:
            self.persons.add(text)
            return self._operate("PERSON", "PERSON", text.strip(), text)
        output = []
        for index, piece in enumerate(pieces):
            if index % 2:
                output.append(piece)
            else:
                self.persons.add(piece)
                output.append(self._operate("PERSON", "PERSON", piece.strip(), piece))
        return "".join(output)

    def _mask_person_columns(self, sheets: list[_Sheet]) -> None:
        """Colonnes de personnes ; prénom et nom d'une même ligne partagent la balise / shared per-row placeholder."""
        for sheet in sheets:
            for columns in sheet.columns.values():
                persons = [c for c in columns if c.ctype.action == MASK and c.ctype.label == "PERSON"]
                given = [c for c in persons if c.ctype.role == "given"]
                surnames = [c for c in persons if c.ctype.role == "surname"]
                if len(given) == 1 and surnames:
                    self._pair(sheet, given[0], surnames[0])
                for column in persons:
                    if column.by_row is None:
                        column.final = {text: self._person_cell(text) for text in column.counts}
            for fields in sheet.fields.values():
                persons = [f for f in fields if f.ctype.action == MASK and f.ctype.label == "PERSON" and f.text]
                given = [f for f in persons if f.ctype.role == "given" and _usable(f.text)]
                surnames = [f for f in persons if f.ctype.role == "surname" and _usable(f.text)]
                if len(given) == 1 and len(surnames) == 1:
                    given[0].final, surnames[0].final = self._pair_outputs(_usable(given[0].text),
                                                                           _usable(surnames[0].text))
                for entry in persons:
                    if entry.final is None:
                        entry.final = self._person_cell(entry.text)

    def _upgrade_person_columns(self, sheets: list[_Sheet]) -> bool:
        """Colonnes où la détection (noms, NER) a reconnu des personnes : masquées en entier ensuite.

        Columns where detection (names, NER) recognised persons are then masked whole; True if any.
        """
        person = self._scope().label_text("PERSON")
        upgraded = False
        for sheet in sheets:
            for columns in sheet.columns.values():
                for column in columns:
                    if column.ctype.action != DETECT or column.ctype.label not in (None, "PERSON"):
                        continue
                    values = [text for text in column.segments if not is_null_marker(text)]
                    covered = sum(1 for text in values
                                  if _single_placeholder(self.outputs[column.segments[text]], person))
                    if self.typer.person_column(covered, len(values)):
                        column.ctype = replace(column.ctype, label="PERSON", entity="PERSON", action=MASK,
                                               evidence="values+detection")
                        column.final = {text: self._person_cell(text) for text in column.counts}
                        upgraded = True
        return upgraded

    def _pair(self, sheet: _Sheet, given: _Column, surname: _Column) -> None:
        given.by_row, surname.by_row = {}, {}
        done: dict[tuple[str, str], tuple[str, str]] = {}
        usable: dict[str, str] = {}  # `_usable` est pure : une fois par texte / pure, once per text
        for row in given.rows:
            text = sheet.texts[row][given.column]
            first = usable.get(text)
            if first is None:
                first = usable[text] = _usable(text)
            text = sheet.texts[row][surname.column]
            last = usable.get(text)
            if last is None:
                last = usable[text] = _usable(text)
            if not (first or last):
                continue
            outputs = done.get((first, last))
            if outputs is None:
                outputs = done[(first, last)] = self._pair_outputs(first, last)
            if first:
                given.by_row[row] = outputs[0]
            if last:
                surname.by_row[row] = outputs[1]

    def _pair_outputs(self, first: str, last: str) -> tuple[str, str]:
        """Balise commune « Prénom Nom » par défaut, sinon opérateur par cellule / shared tag by default.

        Une partie présente dans la liste d'autorisation reste en clair / an allow-listed part stays as is.
        """
        identity = f"{first} {last}".strip()
        for part in (first, last):
            if part:
                self.persons.add(part)
        if first and last:
            self.persons.add(identity, tokens=False)
            self.persons.add(f"{last} {first}", tokens=False, canonical=identity)
        shared = (self.operators.get("PERSON") or "replace") == "replace"
        common: str | None = None
        outputs: list[str] = []
        for part in (first, last):
            if not part or (self.allow and fold(part) in self.allow):
                outputs.append(part)
            elif shared:
                if common is None:
                    common = self._operate("PERSON", "PERSON", identity, identity)
                outputs.append(common)
            else:
                outputs.append(self._operate("PERSON", "PERSON", identity, part))
        return outputs[0], outputs[1]

    def _propagate(self, texts: list[str]) -> None:
        """Noms connus remplacés dans tous les segments (en place) / known names replaced in every segment."""
        done: dict[str, str] = {}

        def replace_form(form: str, canonical: str) -> str:
            output = done.get(form)
            if output is None:
                output = done[form] = self._operate("PERSON", "PERSON", canonical, form)
            return output

        self.persons.apply(texts, range(len(texts)), replace_form)

    def _mask_direct_values(self, sheets: list[_Sheet]) -> None:
        """Identifiants valides balisés sans le moteur / valid identifier values tagged without the engine."""
        for sheet in sheets:
            for columns in sheet.columns.values():
                for column in columns:
                    if not column.direct:
                        continue
                    entity, label = column.ctype.entity or "ID", column.ctype.label or "ID"
                    if not self.allow and self._operator(entity, label) is replace_operator:
                        placeholder = _placeholder_for(self._scope(), label)
                        column.final.update({text: placeholder(entity, value or text)
                                             for text, value in column.direct.items()})
                        continue
                    for text, value in column.direct.items():
                        column.final[text] = self._operate(entity, label, value, text)

    def _finalize(self, sheet: _Sheet) -> None:
        for columns in sheet.columns.values():
            for column in columns:
                if column.by_row is None and not (column.ctype.action == MASK and column.ctype.label == "PERSON"):
                    final = column.final
                    for text in column.counts:
                        if text not in final:
                            final[text] = self._final(column.ctype, text, column.segments.get(text),
                                                      column.raws[text])
        for fields in sheet.fields.values():
            for entry in fields:
                if entry.text and entry.final is None:
                    entry.final = self._final(entry.ctype, entry.text, entry.segment, entry.raw)

    def _final(self, ctype: ColumnType, text: str, segment: int | None, raw: Any) -> str:
        output = self.outputs[segment] if segment is not None else text
        if ctype.action == DETECT or is_null_marker(text):
            # Hors moteur, seul un texte d'origine peut porter des caractères invisibles / only source text can.
            return output if segment is not None or type(raw) is not str else self._kept(text)
        if ctype.action == YEAR:
            return self._operate("BIRTH_DATE", "BIRTH_DATE", text, text, default="generalize")
        label = ctype.label or "ID"
        # Excel garde 15 chiffres significatifs : au-delà, des zéros et une clé fausse. Compté avant le raccourci,
        # car le moteur peut déjà l'avoir masquée. Excel keeps 15 significant digits: zeros and a wrong key beyond.
        if (label == "CARD" and type(raw) is float and len(text) >= 16 and not text[15:].strip("0")
                and card(text) is None):
            self.truncated_cards += 1
        if segment is not None and _covered(output):
            return output
        return self._operate(ctype.entity or label, label, self.typer.canonical(label, text), text)

    # --- vues et rendu / views and rendering ---

    def _emit(self, original: str, output: str, times: int = 1, generalized: bool = False) -> str:
        """Compte les balises d'une valeur émise (hors balises déjà présentes) / counts emitted placeholders."""
        if output == original:
            return output
        found = _labels(output) if "[" in output else ()
        if found:
            tally = self.tally
            for label in found:
                tally[label] += times
            if "[" in original:
                for label in _labels(original):
                    tally[label] -= times
        elif generalized:
            self.tally[self._scope().label_text("BIRTH_DATE")] += times
        return output

    def _segment(self, original: str, index: int) -> str:
        return self._emit(original, self.outputs[index]) if index >= 0 else original

    def _cell(self, sheet: _Sheet, row: int, column: int) -> str:
        text = sheet.texts[row][column]
        index = sheet.cells.get((row, column))
        return self._emit(text, self.outputs[index]) if index is not None else text

    def _view(self, sheet: _Sheet) -> SheetView:
        raw = sheet.raw
        view = SheetView(self._segment(raw.name, sheet.name_index), raw.hidden, shown_rows=len(raw.rows),
                         total_rows=max(raw.total_rows, len(raw.rows)))
        for number, region in enumerate(sheet.regions):
            titles = [self._joined(sheet, row, region.columns) for row in region.title_rows]
            notes = [self._joined(sheet, row, region.columns) for row in region.note_rows]
            span = _span(raw, region)
            if region.kind == "table":
                view.blocks.append(self._table_view(sheet, region, sheet.columns[number], span, titles, notes))
            elif region.kind == "form":
                items = [(self._segment(entry.label, entry.label_index),
                          self._emit(entry.text, entry.text if entry.final is None else entry.final, 1,
                                     entry.ctype.action == YEAR))
                         for entry in sheet.fields[number]]
                view.blocks.append(FormView(span, items, titles))
            else:
                view.blocks.append(TextView([(f"{column_letter(raw.col0 + column)}{raw.row0 + row + 1}",
                                              self._cell(sheet, row, column))
                                             for row in region.data_rows for column in region.columns
                                             if sheet.texts[row][column]]))
        return view

    def _table_view(self, sheet: _Sheet, region: Region, columns: list[_Column], span: str, titles: list[str],
                    notes: list[str]) -> TableView:
        headers = [self._segment(column.header, column.header_index) for column in columns]
        for column in columns:
            if column.by_row is not None:
                for row, output in column.by_row.items():
                    self._emit(sheet.texts[row][column.column], output)
            else:
                self._emit_column(column.counts, column.final, column.ctype.action == YEAR)
        # Colonne par colonne puis transposition (zip, en C) ; les textes de chaque colonne viennent de `_table`.
        # Column by column, then transposed with zip (C); each column's texts come from `_table`.
        data = [row for row in region.data_rows if row not in region.total_rows]
        outputs: list[list[str]] = []
        for column in columns:
            texts = column.texts
            if column.by_row is not None:
                by_row = column.by_row
                outputs.append([by_row.get(row) or self._kept(text) for row, text in zip(data, texts, strict=True)])
            else:
                outputs.append(list(map(column.final.get, texts, texts)))  # final.get(texte, texte), en C
        row0 = sheet.raw.row0
        if outputs and len(data) == len(region.data_rows):
            # Sans ligne de total, toutes les lignes viennent de la transposition / no total row: all transposed.
            numbers = [row0 + row + 1 for row in data]
            rows = list(zip(numbers, map(list, zip(*outputs, strict=True)), strict=True))
            return TableView(span, headers, rows, titles, notes)
        cells_by_row = dict(zip(data, map(list, zip(*outputs, strict=True)), strict=True)) if outputs else {}
        rows = [(row0 + row + 1, cells_by_row[row] if row in cells_by_row
                 else [self._cell(sheet, row, column.column) for column in columns])
                for row in region.data_rows]
        return TableView(span, headers, rows, titles, notes)

    def _emit_column(self, counts: Counter[str], final: dict[str, str], generalized: bool) -> None:
        """`_emit` sur chaque valeur distincte d'une colonne, en une boucle / `_emit` over a column's values."""
        tally = self.tally
        birth = ""
        whole = PLACEHOLDER_RE.fullmatch
        for text, times in counts.items():
            output = final.get(text, text)
            if output == text:
                continue
            if len(output) <= _SHORT_PLACEHOLDER and "[" not in text and (single := whole(output)) is not None:
                tally[single.group(1)] += times  # `_labels` d'une balise seule, en ligne / inlined lone placeholder
                continue
            found = _labels(output) if "[" in output else ()
            if found:
                for label in found:
                    tally[label] += times
                if "[" in text:
                    for label in _labels(text):
                        tally[label] -= times
            elif generalized:
                birth = birth or self._scope().label_text("BIRTH_DATE")
                tally[birth] += times

    def _joined(self, sheet: _Sheet, row: int, columns: Iterable[int]) -> str:
        return " ; ".join(self._cell(sheet, row, column) for column in columns if sheet.texts[row][column])

    def _markdown(self, views: list[SheetView], sheets: list[_Sheet], package: Package, read: ReadResult) -> str:
        """Résumé puis feuilles ; jamais le nom du fichier / summary then sheets; never the file name."""
        words = TEXTS[self.language]
        lines = [f"## {words['summary']}", ""]
        lines += [f"- {line}" for line in self._summary(views, sheets, package, read)]
        lines.append("")
        table_format = self.options.table_format if self.options.table_format in _TABLE_FORMATS else "markdown"
        lines += render_sheets(views, table_format, self.language)
        return "\n".join(lines).rstrip() + "\n"

    def _summary(self, views: list[SheetView], sheets: list[_Sheet], package: Package, read: ReadResult) -> list[str]:
        french = self.language == "fr"
        dropped = _dropped(package, read)
        rows = sum(len(block.rows) for view in views for block in view.blocks if isinstance(block, TableView))
        cells = sum(sheet.non_empty for sheet in sheets)
        total = sum(self.tally.values())
        detail = ", ".join(f"{label} {count}" for label, count in sorted(self.tally.items()))
        detail = f" ({detail})" if detail else ""
        if french:
            lines = [f"Classeur {package.kind} : {len(views)} feuille(s) émise(s), {rows} ligne(s) de tableau, "
                     f"{cells} cellule(s) non vide(s)", f"Valeurs remplacées : {total}{detail}"]
        else:
            lines = [f"{package.kind} workbook: {len(views)} sheet(s) emitted, {rows} table row(s), "
                     f"{cells} non-empty cell(s)", f"Values replaced: {total}{detail}"]
        items = [f"{count} {_DROPPED_NAMES[key][0 if french else 1]}" for key, count in sorted(dropped.items())
                 if key in _DROPPED_NAMES and count]
        if items:
            lines.append(("Non émis : " if french else "Not emitted: ") + ", ".join(items))
        if dropped.get("formulas"):
            lines.append("Formules jamais évaluées : valeurs en cache seulement" if french
                         else "Formulas never evaluated: cached values only")
        if read.cell_limit_reached:
            limit = self.options.max_cells
            lines.append(f"Limite de cellules atteinte (max_cells = {limit}) : contenu tronqué" if french
                         else f"Cell limit reached (max_cells = {limit}): content truncated")
        lines.append(NOTICE_FR if french else NOTICE_EN)
        return lines

    def _result(self, markdown: str, views: list[SheetView], sheets: list[_Sheet], package: Package,
                read: ReadResult, detected: str) -> DocumentResult:
        dropped = _dropped(package, read)
        report = {
            "kind": package.kind,
            "sheets": [self._sheet_report(view, sheet) for view, sheet in zip(views, sheets, strict=True)],
            "entities": dict(sorted(self.tally.items())),
            "total_replaced": sum(self.tally.values()),
            "kept_by_policy": _merged_kept(self.reports),
            "countries": sorted({country for report in self.reports for country in report.get("countries", ())}),
            "language": detected,
            "profile": self.anonymizer.settings.profile,
            "dropped": dict(sorted(dropped.items())),
            "segments": len(self.texts),
            "timings_ms": {**self.timings, "total": round((perf_counter() - self.started) * 1000, 3)},
            "irreversible": True,
            "notice": NOTICE_FR if self.language == "fr" else NOTICE_EN,
        }
        # Avertissements du moteur (mode auto, pays sans FR), une fois chacun / engine warnings, once each.
        engine_warnings = list(dict.fromkeys(w for r in self.reports for w in r.get("warnings", ())))
        if engine_warnings:
            report["warnings"] = engine_warnings
        return DocumentResult(markdown, package.kind, report, self._warnings(views, package, read, dropped),
                              dict(sorted(dropped.items())))

    def _warnings(self, views: list[SheetView], package: Package, read: ReadResult,
                  dropped: Counter[str]) -> list[str]:
        """Avertissements sûrs : comptes et noms de catégories, jamais de contenu / counts only, never content."""
        warnings = list(package.warnings)
        if dropped.get("hidden_sheets"):
            warnings.append(f"{dropped['hidden_sheets']} feuille(s) masquée(s) exclue(s) ; include_hidden=True pour "
                            "les inclure / hidden sheet(s) excluded; set include_hidden=True to include them")
        if self.options.include_hidden and any(view.hidden for view in views):
            warnings.append("Feuilles masquées incluses et anonymisées / hidden sheets included and anonymised")
        if dropped.get("oversized_sheets"):
            warnings.append("Feuille(s) trop étendue(s) ignorée(s) / oversized sheet(s) skipped")
        if dropped.get("unreadable_sheets"):
            warnings.append("Feuille(s) illisible(s) ignorée(s) / unreadable sheet(s) skipped")
        if dropped.get("truncated_rows"):
            warnings.append("Ligne(s) de plus de 16 384 champs coupée(s) / row(s) wider than 16,384 fields cut")
        if read.cell_limit_reached:
            warnings.append("Limite de cellules atteinte : contenu tronqué / cell limit reached: content truncated")
        for number, view in enumerate(views, 1):
            if view.total_rows > view.shown_rows:
                warnings.append(f"Feuille n°{number} tronquée : {view.shown_rows} lignes sur {view.total_rows} / "
                                f"sheet #{number} truncated: {view.shown_rows} of {view.total_rows} rows")
        if self.truncated_cards:
            warnings.append(f"{self.truncated_cards} numéro(s) de carte tronqué(s) par Excel (15 chiffres), masqué(s) "
                            "d'après l'en-tête / card number(s) truncated by Excel, masked from the header")
        if dropped.get("formulas"):
            warnings.append("Formules non évaluées : valeurs en cache seulement / formulas not evaluated: "
                            "cached values only")
        if self.options.include_comments and dropped.get("comments"):
            warnings.append("Commentaires jamais émis par le pipeline tableur / comments never emitted by the "
                            "spreadsheet pipeline")
        if self.options.table_format not in _TABLE_FORMATS:
            warnings.append("Format de tableau non pris en charge, Markdown utilisé / unsupported table format, "
                            "Markdown used")
        return warnings

    def _sheet_report(self, view: SheetView, sheet: _Sheet) -> dict[str, Any]:
        """Métadonnées d'une feuille : en-têtes anonymisés, types, actions ; aucune valeur / no value."""
        columns = []
        for number, region_columns in sheet.columns.items():
            span = _span(sheet.raw, sheet.regions[number])
            columns += [{"region": span, "column": column_letter(sheet.raw.col0 + column.column),
                         "header": self.outputs[column.header_index] if column.header_index >= 0 else "",
                         "type": column.ctype.label, "action": column.ctype.action,
                         "evidence": column.ctype.evidence} for column in region_columns]
        return {"name": view.name, "hidden": view.hidden, "rows": view.shown_rows, "total_rows": view.total_rows,
                "regions": len(sheet.regions), "columns": columns}


def _placeholder_for(scope: Scope, label: str) -> Callable[[str, str], str]:
    """`scope.placeholder(label, …)` pour un libellé fixe : le texte affiché, constant pendant la requête, est
    calculé une fois et la portée native appelée directement, comme le fait le moteur. `scope.placeholder` for a
    fixed label: the display text, constant during the request, is computed once and the native scope called
    directly, as the engine does."""
    native = scope._native_scope if type(scope) is Scope else None
    if native is None:
        return lambda entity, value: scope.placeholder(label, entity, value)
    display = LABELS.display(label, scope.label_language, scope.neutral)
    return lambda entity, value: native.placeholder(display, entity, value)


def _usable(text: str) -> str:
    """Partie de nom exploitable ; vide pour « n/a » ou une balise existante / usable name part."""
    stripped = text.strip()
    return "" if not stripped or is_null_marker(stripped) or _covered(stripped) else stripped


def _span(raw: RawSheet, region: Region) -> str:
    left, right = raw.col0 + region.columns[0], raw.col0 + region.columns[-1]
    return f"{column_letter(left)}{raw.row0 + region.top + 1}:{column_letter(right)}{raw.row0 + region.bottom + 1}"


def _dropped(package: Package, read: ReadResult) -> Counter[str]:
    dropped = Counter(package.dropped)
    dropped.update(read.skipped)
    return +dropped


def _merged_kept(reports: list[dict[str, Any]]) -> dict[str, int]:
    kept: Counter[str] = Counter()
    for report in reports:
        kept.update(report.get("kept_by_policy", {}))
    return dict(sorted(kept.items()))


def _labels(text: str) -> list[str]:
    """Libellés des balises, numérotées ou non (opérateur « redact ») / labels of numbered or redacted placeholders."""
    if len(text) <= _SHORT_PLACEHOLDER:
        # Une balise numérotée seule, assez courte pour `ANY_PLACEHOLDER_RE` : son seul libellé (cas courant).
        # A lone numbered placeholder short enough for `ANY_PLACEHOLDER_RE`: its only label (common case).
        whole = PLACEHOLDER_RE.fullmatch(text)
        if whole is not None:
            return [whole.group(1)]
    labels = []
    for found in ANY_PLACEHOLDER_RE.finditer(text):
        numbered = PLACEHOLDER_RE.fullmatch(found.group())
        labels.append(numbered.group(1) if numbered else found.group()[1:-1])
    return labels


def _single_placeholder(output: str, label: str) -> bool:
    """La sortie est exactement une balise de ce libellé / the output is exactly one placeholder of this label."""
    stripped = output.strip()
    return ANY_PLACEHOLDER_RE.fullmatch(stripped) is not None and _labels(stripped) == [label]


def _covered(output: str) -> bool:
    """Plus aucun caractère alphanumérique hors balises / no alphanumeric left outside placeholders."""
    return _ALNUM_RE.search(ANY_PLACEHOLDER_RE.sub("", output)) is None


_DROPPED_NAMES: dict[str, tuple[str, str]] = {
    "hidden_sheets": ("feuille(s) masquée(s)", "hidden sheet(s)"),
    "chart_sheets": ("feuille(s) graphique", "chart sheet(s)"),
    "macro_sheets": ("feuille(s) macro ou boîte de dialogue", "macro or dialog sheet(s)"),
    "oversized_sheets": ("feuille(s) trop étendue(s)", "oversized sheet(s)"),
    "unreadable_sheets": ("feuille(s) illisible(s) (valeur hors limites)", "unreadable sheet(s) (out-of-range value)"),
    "truncated_rows": ("ligne(s) coupée(s) à 16 384 champs", "row(s) cut at 16,384 fields"),
    "cell_limit_sheets": ("feuille(s) au-delà de la limite de cellules", "sheet(s) beyond the cell limit"),
    "comments": ("commentaire(s)", "comment(s)"),
    "threaded_comments": ("commentaire(s) en fil", "threaded comment(s)"),
    "comment_persons": ("auteur(s) de commentaires", "comment author(s)"),
    "document_properties": ("partie(s) de propriétés du document (auteur…)", "document property part(s) (author…)"),
    "sensitivity_labels": ("étiquette(s) de confidentialité", "sensitivity label(s)"),
    "pivot_caches": ("cache(s) de tableau croisé dynamique", "pivot cache(s)"),
    "external_links": ("liaison(s) externe(s)", "external link(s)"),
    "vba_projects": ("projet(s) de macros VBA", "VBA project(s)"),
    "drawings": ("dessin(s)", "drawing(s)"),
    "charts": ("graphique(s)", "chart(s)"),
    "images": ("image(s)", "image(s)"),
    "embedded_objects": ("objet(s) incorporé(s)", "embedded object(s)"),
    "revisions": ("partie(s) de révisions", "revision part(s)"),
    "custom_xml": ("partie(s) XML personnalisée(s)", "custom XML part(s)"),
    "connections": ("connexion(s) de données", "data connection(s)"),
    "slicers": ("segment(s) ou chronologie(s)", "slicer(s) or timeline(s)"),
    "rich_data": ("partie(s) de données enrichies", "rich data part(s)"),
    "defined_names": ("nom(s) défini(s)", "defined name(s)"),
    "hyperlinks": ("lien(s) hypertexte externe(s)", "external hyperlink(s)"),
    "headers_footers": ("en-tête(s) ou pied(s) de page", "header(s) or footer(s)"),
}
