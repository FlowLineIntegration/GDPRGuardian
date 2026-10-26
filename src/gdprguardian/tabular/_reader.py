"""Lecture des feuilles : calamine (valeurs en cache) et texte délimité / sheet reading: calamine and delimited text.

Aucune formule n'est évaluée ; l'étendue de chaque feuille est bornée avant que calamine ne la charge, et la
lecture binaire peut tourner dans le bac à sable des convertisseurs (processus séparé, mémoire plafonnée).
No formula is ever evaluated; each sheet's extent is bounded before calamine loads it, and binary reading can
run in the converters' sandbox (separate, memory-capped process).

python-calamine reste la référence. Pour un xlsx, le noyau Rust (`XlsxBook`) lit en flux les formes canoniques
et rend exactement les mêmes valeurs ; toute autre forme est refusée (`XlsxDecline`) et relue par calamine,
pour le classeur ou pour la seule feuille concernée. python-calamine stays the reference. For an xlsx, the Rust
core streams the canonical forms and returns exactly the same values; any other form is declined and read again
by calamine, for the workbook or for that sheet only.

Le noyau, à mémoire bornée, lit chaque feuille juste avant la garde et mesure sa partie au passage : la garde
reprend cette mesure (identique à la sienne) au lieu de décompresser la partie une seconde fois. calamine, lui,
ne lit jamais qu'après la garde. The bounded-memory core reads each sheet just before the guard and measures its
part on the way: the guard takes that (identical) measurement instead of inflating the part again. calamine only
ever reads after the guard.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import itertools
from collections import Counter
from collections.abc import Callable
from dataclasses import astuple, dataclass, field, replace
from pathlib import PurePath
from time import perf_counter
from typing import Any

from .. import _native
from ..documents import (
    ConversionTimeoutError,
    DocumentError,
    DocumentOptions,
    EncryptedDocumentError,
    UnsupportedFormatError,
)
from ._package import MAX_SHEET_AREA, TEXT_KINDS, Package, TableSpec, open_package

# Excel : 16 384 colonnes au plus ; au-delà, un CSV est tronqué / Excel's column cap; wider CSV rows are cut.
MAX_COLUMNS = 16_384
_DELIMITERS = (";", "\t", ",", "|")
_SNIFF_BYTES = 65_536
_SNIFF_ROWS = 40
_LEGACY_ENCODINGS = ["cp1252", "iso8859_15"]
# UTF-32 avant UTF-16 : même préfixe FF FE / UTF-32 before UTF-16: same FF FE prefix.
_BOMS = ((b"\xef\xbb\xbf", "utf-8"), (b"\xff\xfe\x00\x00", "utf-32-le"), (b"\x00\x00\xfe\xff", "utf-32-be"),
         (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"))
_PASSWORD = "Classeur protégé par mot de passe / password-protected workbook"
_CORRUPT = "Classeur illisible ou corrompu / unreadable or corrupted workbook"


@dataclass(slots=True)
class RawSheet:
    """Grille rectangulaire de valeurs brutes et sa position dans la feuille / raw value grid and its position."""

    name: str
    rows: list[list[Any]]
    row0: int = 0
    col0: int = 0
    total_rows: int = 0
    hidden: bool = False
    merged: list[tuple[int, int, int, int]] = field(default_factory=list)
    tables: list[TableSpec] = field(default_factory=list)

    @property
    def width(self) -> int:
        return len(self.rows[0]) if self.rows else 0


@dataclass(slots=True)
class ReadResult:
    sheets: list[RawSheet]
    skipped: Counter[str] = field(default_factory=Counter)
    cell_limit_reached: bool = False


def load(data: bytes, filename: str, options: DocumentOptions,
         check_time: Callable[[], None], native: bool = False) -> tuple[Package, ReadResult]:
    """Garde, inventaire et lecture ; renvoie le résumé du paquet (sans archive) / guard, inventory, reading.

    `native` : noyau Rust permis (`Settings.native`) ; sans lui, référence Python seule / Rust core allowed.
    """
    package = open_package(data, filename, native=native)
    try:
        if package.kind in TEXT_KINDS:
            read = read_delimited(data, package.kind, PurePath(filename).stem or "data", options)
        else:
            read = read_workbook(data, package, options, check_time, native)
    finally:
        package.close()
    return package.summary(), read


def load_in_worker(data: bytes, suffix: str, options: DocumentOptions, native: bool = False) -> dict[str, Any]:
    """Point d'entrée du bac à sable : seule l'extension voyage, jamais le nom du fichier ; réponse JSON.

    Sandbox entry point: only the extension travels, never the file name; JSON reply. Le choix du noyau vient
    du parent : le travailleur ne voit aucune variable GDPRGUARDIAN_* / the core choice comes from the parent.
    """
    deadline = perf_counter() + options.timeout_s

    def check_time() -> None:
        if perf_counter() > deadline:
            raise ConversionTimeoutError("Délai de traitement dépassé / processing timeout")

    return _encode(*load(data, f"classeur{suffix}", options, check_time, native))


def load_sandboxed(data: bytes, filename: str, options: DocumentOptions,
                   remaining_s: float, native: bool = False) -> tuple[Package, ReadResult]:
    """Lecture binaire dans le bac à sable des convertisseurs : un plantage natif, un dépassement mémoire ou de
    délai y reste confiné (`gdprguardian.convert.configure_sandbox` s'applique aussi ici).
    Binary reading in the converters' sandbox: a native crash, memory blow-up or timeout stays confined there.
    """
    from ..convert import _sandbox

    suffix = PurePath(filename).suffix.lower()
    reply = _sandbox.run(f"{__name__}:load_in_worker", data,
                         (suffix, replace(options, timeout_s=remaining_s), native), remaining_s)
    return _decode(reply)


# --- Réponse JSON du travailleur / worker JSON reply -------------------------------------------------------------

_JSON_SCALARS = frozenset({str, int, float, bool, type(None)})
_TEMPORAL_TAGS: dict[str, Callable[[Any], Any]] = {
    "dt": dt.datetime.fromisoformat, "d": dt.date.fromisoformat, "t": dt.time.fromisoformat,
    "td": lambda parts: dt.timedelta(*parts),
}


def _encode_value(value: Any) -> Any:
    """Valeur JSON : dates et durées étiquetées, le reste en texte / JSON value: temporal values tagged."""
    kind = type(value)
    if kind is dt.datetime:
        return {"dt": value.isoformat()}
    if kind is dt.date:
        return {"d": value.isoformat()}
    if kind is dt.time:
        return {"t": value.isoformat()}
    if kind is dt.timedelta:
        return {"td": [value.days, value.seconds, value.microseconds]}
    return str(value)


def _decode_value(value: Any) -> Any:
    if type(value) is not dict or len(value) != 1:
        raise TypeError
    ((tag, payload),) = value.items()
    if tag == "td" and not (type(payload) is list and len(payload) == 3 and all(type(p) is int for p in payload)):
        raise TypeError
    return _TEMPORAL_TAGS[tag](payload)


def _encode_row(row: list[Any]) -> list[Any]:
    """Ligne JSON ; une ligne de seuls scalaires part telle quelle (test des types en C).

    JSON row; a row of scalars only goes as is (types tested in C).
    """
    if set(map(type, row)) <= _JSON_SCALARS:
        return row
    scalars = _JSON_SCALARS
    return [v if type(v) in scalars else _encode_value(v) for v in row]


def _encode(package: Package, read: ReadResult) -> dict[str, Any]:
    sheets = [[sheet.name, list(map(_encode_row, sheet.rows)),
               sheet.row0, sheet.col0, sheet.total_rows, sheet.hidden, sheet.merged,
               [[*astuple(table)[:6], list(table.columns)] for table in sheet.tables]]
              for sheet in read.sheets]
    return {"kind": package.kind, "date1904": package.date1904, "dropped": dict(package.dropped),
            "warnings": package.warnings, "skipped": dict(read.skipped), "cell_limit": read.cell_limit_reached,
            "sheets": sheets}


def _decode(reply: Any) -> tuple[Package, ReadResult]:
    """Réponse du travailleur, forme vérifiée ; toute anomalie devient une erreur sûre.

    Worker reply, shape checked; any anomaly becomes a safe error.
    """
    try:
        package = Package(_typed(reply["kind"], str), None, _typed(reply["date1904"], bool),
                          Counter(_counts(reply["dropped"])), [_typed(w, str) for w in reply["warnings"]])
        read = ReadResult([], Counter(_counts(reply["skipped"])), _typed(reply["cell_limit"], bool))
        for name, rows, row0, col0, total, hidden, merged, tables in reply["sheets"]:
            sheet = RawSheet(_typed(name, str), _decode_rows(rows), _typed(row0, int), _typed(col0, int),
                             _typed(total, int), _typed(hidden, bool))
            sheet.merged = [(_typed(a, int), _typed(b, int), _typed(c, int), _typed(d, int)) for a, b, c, d in merged]
            for top, left, bottom, right, header_rows, totals_rows, columns in tables:
                numbers = (_typed(n, int) for n in (top, left, bottom, right, header_rows, totals_rows))
                sheet.tables.append(TableSpec(*numbers, tuple(_typed(c, str) for c in _typed(columns, list))))
            read.sheets.append(sheet)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise DocumentError(_CORRUPT) from None
    return package, read


def _decode_rows(rows: Any) -> list[list[Any]]:
    """Grille rectangulaire, dates et durées reconstruites / rectangular grid, temporal values rebuilt."""
    width = len(rows[0]) if _typed(rows, list) else 0
    decoded: list[list[Any]] = []
    for row in rows:
        if type(row) is not list or len(row) != width:
            raise TypeError
        if set(map(type, row)) <= _JSON_SCALARS:  # que des scalaires : liste neuve gardée / scalars only: kept
            decoded.append(row)
        else:
            decoded.append([value if type(value) in _JSON_SCALARS else _decode_value(value) for value in row])
    return decoded


def _typed(value: Any, kind: type) -> Any:
    if type(value) is not kind:
        raise TypeError
    return value


def _counts(value: Any) -> dict[str, int]:
    return {_typed(key, str): _typed(count, int) for key, count in _typed(value, dict).items()}


def read_workbook(data: bytes, package: Package, options: DocumentOptions,
                  check_time: Callable[[], None], native: bool = False) -> ReadResult:
    """Feuilles de calcul visibles (ou toutes avec include_hidden), dans les limites de cellules.

    Worksheets that are visible (or all with include_hidden), within the cell limits. Une feuille que calamine
    ne sait pas convertir (date hors limites…) est écartée et comptée / a sheet calamine cannot convert is
    skipped and counted.
    """
    result = ReadResult([])
    book = _open_book(data, package, native)
    budget = options.max_cells
    try:
        for name, kind, hidden in book.sheets():
            check_time()
            if kind != _WORKSHEET:
                result.skipped["chart_sheets" if kind == _CHARTSHEET else "macro_sheets"] += 1
                continue
            if hidden and not options.include_hidden:
                result.skipped["hidden_sheets"] += 1
                continue
            if budget > 0:
                book.prepare(name, package)
            extent = package.sheet_extent(name)
            if extent is not None and extent[0] * extent[1] > MAX_SHEET_AREA:
                result.skipped["oversized_sheets"] += 1
                continue
            if budget <= 0:
                result.skipped["cell_limit_sheets"] += 1
                result.cell_limit_reached = True
                continue
            try:
                sheet = book.sheet(name)
                height, width = sheet.height, sheet.width
                limit = _row_limit(height, width, budget, options)
                rows = sheet.rows(limit if limit < height else None)
                start = sheet.start or (0, 0)
                merged = sheet.merged
            except DocumentError:
                raise
            except BaseException as exc:  # valeur hors limites (OverflowError…), panique / out-of-range value, panic
                _reraise_interrupts(exc)
                result.skipped["unreadable_sheets"] += 1
                continue
            if limit < height and width and limit * width >= budget:
                result.cell_limit_reached = True
            budget -= len(rows) * width
            row0, col0 = start
            raw = RawSheet(name, rows, row0, col0, height, hidden)
            raw.merged = [(r0 - row0, c0 - col0, r1 - row0, c1 - col0) for (r0, c0), (r1, c1) in merged
                          if r0 >= row0 and c0 >= col0]
            raw.tables = [TableSpec(t.top - row0, t.left - col0, t.bottom - row0, t.right - col0, t.header_rows,
                                    t.totals_rows, t.columns)
                          for t in package.tables(name) if t.top >= row0 and t.left >= col0]
            result.sheets.append(raw)
    finally:
        book.close()
    return result


# --- Lecteurs de classeur : python-calamine (référence) ou noyau Rust / workbook readers ------------------------

_WORKSHEET, _CHARTSHEET = "worksheet", "chartsheet"


def _open_book(data: bytes, package: Package, native: bool) -> _CalamineBook | _NativeBook:
    """Noyau Rust pour un xlsx s'il est permis et accepte le classeur, sinon calamine / Rust core or calamine."""
    core = _native.core() if native and package.kind in ("xlsx", "xlsm") else None
    if core is not None and hasattr(core, "XlsxBook"):
        try:
            return _NativeBook(core, data)
        except core.XlsxDecline:
            pass  # forme non canonique : la référence lit tout / non-canonical form: the reference reads it all
    return _CalamineBook(data)


class _CalamineSheet:
    """Feuille calamine : interface commune aux deux lecteurs / calamine sheet: interface shared by both readers."""

    __slots__ = ("_password_error", "_sheet")

    def __init__(self, sheet: Any, password_error: type[BaseException]) -> None:
        self._sheet, self._password_error = sheet, password_error

    @property
    def height(self) -> int:
        return self._sheet.height

    @property
    def width(self) -> int:
        return self._sheet.width

    @property
    def start(self) -> tuple[int, int] | None:
        return self._sheet.start

    @property
    def merged(self) -> list[Any]:
        return self._sheet.merged_cell_ranges or []

    def rows(self, nrows: int | None) -> list[list[Any]]:
        try:
            if nrows is None:
                return self._sheet.to_python()
            return self._sheet.to_python(skip_empty_area=True, nrows=nrows)
        except self._password_error:
            raise EncryptedDocumentError(_PASSWORD) from None


class _CalamineBook:
    """python-calamine, référence de lecture / python-calamine, the reading reference."""

    __slots__ = ("_book", "_password_error", "_types")

    def __init__(self, data: bytes) -> None:
        try:
            from python_calamine import CalamineWorkbook, PasswordError, SheetTypeEnum, SheetVisibleEnum
        except ImportError:  # pragma: no cover - dépendance optionnelle / optional dependency
            raise UnsupportedFormatError('python-calamine requis / required: '
                                         'pip install "gdprguardian[office]"') from None
        self._password_error = PasswordError
        self._types = (SheetTypeEnum, SheetVisibleEnum)
        try:
            self._book = CalamineWorkbook.from_filelike(io.BytesIO(data))
        except PasswordError:
            raise EncryptedDocumentError(_PASSWORD) from None
        except BaseException as exc:  # erreurs calamine, y compris les paniques Rust / calamine errors, Rust panics
            _reraise_interrupts(exc)
            raise DocumentError(_CORRUPT) from None

    def sheets(self) -> list[tuple[str, str, bool]]:
        """(nom, type, masquée) de chaque feuille / (name, type, hidden) of each sheet."""
        types, visible = self._types

        def kind(typ: Any) -> str:  # énumérations non hachables / unhashable enums
            return _WORKSHEET if typ == types.WorkSheet else _CHARTSHEET if typ == types.ChartSheet else "other"

        return [(meta.name, kind(meta.typ), meta.visible != visible.Visible) for meta in self._book.sheets_metadata]

    def prepare(self, name: str, package: Package) -> None:
        """Rien avant la garde : calamine ne lit qu'une feuille déjà bornée / nothing before the guard."""

    def sheet(self, name: str) -> _CalamineSheet:
        try:
            return _CalamineSheet(self._book.get_sheet_by_name(name), self._password_error)
        except self._password_error:
            raise EncryptedDocumentError(_PASSWORD) from None

    def close(self) -> None:
        self._book.close()


class _NativeSheet:
    """Feuille lue par le noyau ; un refus tardif repasse par calamine / native sheet, late decline via calamine."""

    __slots__ = ("_book", "_name", "_sheet")

    def __init__(self, book: _NativeBook, name: str, sheet: Any) -> None:
        self._book, self._name, self._sheet = book, name, sheet

    @property
    def height(self) -> int:
        return self._sheet.height

    @property
    def width(self) -> int:
        return self._sheet.width

    @property
    def start(self) -> tuple[int, int] | None:
        return self._sheet.start

    @property
    def merged(self) -> list[Any]:
        return self._sheet.merged

    def rows(self, nrows: int | None) -> list[list[Any]]:
        try:
            return self._sheet.rows(nrows)
        except self._book.decline:
            return self._book.reference().sheet(self._name).rows(nrows)


class _NativeBook:
    """Classeur lu par le noyau Rust ; calamine n'est ouvert qu'au premier refus / calamine opened on decline only."""

    __slots__ = ("_book", "_calamine", "_data", "_prepared", "decline")

    def __init__(self, core: Any, data: bytes) -> None:
        self.decline = core.XlsxDecline
        self._book = core.XlsxBook(data)
        self._data = data
        self._calamine: _CalamineBook | None = None
        self._prepared: tuple[str, Any] | None = None

    def prepare(self, name: str, package: Package) -> None:
        """Lit la feuille avant la garde (lecture native bornée, sans calamine) : la partie, mesurée au passage,
        n'est pas décompressée une seconde fois par la garde. Refus ou erreur : rien, `sheet` refait comme avant.
        Reads the sheet before the guard (bounded native read, no calamine): the part, measured on the way, is not
        inflated a second time by the guard. Decline or error: nothing, `sheet` does as before."""
        self._prepared = None
        try:
            sheet = self._book.sheet(name)
            measured = sheet.measured(MAX_SHEET_AREA)
        except self.decline:
            self._prepared = (name, None)  # calamine la lira après la garde / calamine reads it after the guard
            return
        except Exception:  # repris dans `sheet`, après la garde / taken up again in `sheet`, after the guard
            return
        self._prepared = (name, sheet)
        package.adopt_measure(measured)

    def reference(self) -> _CalamineBook:
        if self._calamine is None:
            self._calamine = _CalamineBook(self._data)
        return self._calamine

    def sheets(self) -> list[tuple[str, str, bool]]:
        return [(name, kind, visibility != "visible") for name, kind, visibility in self._book.sheets]

    def sheet(self, name: str) -> _NativeSheet | _CalamineSheet:
        prepared, self._prepared = self._prepared, None
        if prepared is not None and prepared[0] == name:
            sheet = prepared[1]
            return self.reference().sheet(name) if sheet is None else _NativeSheet(self, name, sheet)
        try:
            return _NativeSheet(self, name, self._book.sheet(name))
        except self.decline:
            return self.reference().sheet(name)

    def close(self) -> None:
        if self._calamine is not None:
            self._calamine.close()
        self._book = self._data = self._prepared = None


def _reraise_interrupts(exc: BaseException) -> None:
    """Interruptions et erreurs de délai remontent telles quelles / interrupts and timeouts propagate."""
    if isinstance(exc, (KeyboardInterrupt, SystemExit, DocumentError)):
        raise exc


def _row_limit(height: int, width: int, budget: int, options: DocumentOptions) -> int:
    limit = height
    if options.max_rows_per_sheet is not None:
        limit = min(limit, max(options.max_rows_per_sheet, 1))
    if width:
        limit = min(limit, max(budget // width, 1))
    return limit


# --- Texte délimité / delimited text ---------------------------------------------------------------------------


def decode_text(data: bytes) -> str:
    """BOM, puis UTF-8 strict, puis encodages occidentaux (exports Excel français en cp1252).

    BOM, then strict UTF-8, then western legacy encodings (French Excel exports are cp1252).
    """
    for bom, codec in _BOMS:
        if data.startswith(bom):
            return data[len(bom):].decode(codec, errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    encoding = "cp1252"
    try:
        from charset_normalizer import from_bytes

        # Restreint : sans cela, un court cp1252 passe pour du cp1250 / restricted: else short cp1252 reads as cp1250.
        best = from_bytes(data[:_SNIFF_BYTES], cp_isolation=_LEGACY_ENCODINGS).best()
        if best is not None:
            encoding = best.encoding
    except ImportError:  # pragma: no cover - dépendance optionnelle / optional dependency
        pass
    return data.decode(encoding, errors="replace")


def sniff_delimiter(text: str) -> str:
    """Séparateur au nombre de champs le plus régulier ; « ; » d'abord (exports français).

    Delimiter giving the most regular field count; ';' first (French exports). Plus sûr que csv.Sniffer,
    qui choisit la virgule des décimales / safer than csv.Sniffer, which picks decimal commas.
    """
    sample = text[:_SNIFF_BYTES]
    if len(text) > _SNIFF_BYTES and "\n" in sample:
        sample = sample[:sample.rindex("\n")]
    best, best_score = ",", (0.0, 0)
    for priority, delimiter in enumerate(_DELIMITERS):
        try:
            rows = list(itertools.islice(csv.reader(io.StringIO(sample, newline=""), delimiter=delimiter),
                                         _SNIFF_ROWS))
        except csv.Error:
            continue
        counts = [len(row) for row in rows if any(cell.strip() for cell in row)]
        if not counts or max(counts) < 2:
            continue
        mode, frequency = Counter(counts).most_common(1)[0]
        score = (frequency / len(counts), -priority if mode > 1 else -99)
        if score > best_score:
            best, best_score = delimiter, score
    return best


def read_delimited(data: bytes, kind: str, name: str, options: DocumentOptions) -> ReadResult:
    """CSV/TSV -> une feuille de chaînes ; numéro de ligne = numéro d'enregistrement / record number.

    La grille complétée (lignes x largeur) respecte `max_cells` et la surface maximale, comme un classeur ;
    une ligne plus large que 16 384 champs est coupée. The padded grid (rows x width) honours `max_cells` and
    the maximum area, like a workbook; a row wider than 16,384 fields is cut.
    """
    text = decode_text(data)
    delimiter = "\t" if kind == "tsv" else sniff_delimiter(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=False)
    limit = options.max_rows_per_sheet if options.max_rows_per_sheet is not None else 1 << 62
    area = max(min(options.max_cells, MAX_SHEET_AREA), 1)
    rows: list[list[str]] = []
    width = total = cut = 0
    full = False
    try:
        for record in reader:
            total += 1
            if full or len(rows) >= limit:
                continue
            if len(record) > MAX_COLUMNS:
                record = record[:MAX_COLUMNS]
                cut += 1
            if (len(rows) + 1) * max(width, len(record)) > area:
                full = True
                if rows:
                    continue
                record = record[:area]  # première ligne plus large que le budget / first row wider than the budget
            rows.append(record)
            width = max(width, len(record))
    except csv.Error:
        raise DocumentError("Fichier délimité illisible (champ trop long ?) / unreadable delimited file") from None
    for record in rows:
        if len(record) < width:
            record.extend([""] * (width - len(record)))
    result = ReadResult([RawSheet(name, rows, 0, 0, total)])
    result.cell_limit_reached = full
    if cut:
        result.skipped["truncated_rows"] = cut
    return result
