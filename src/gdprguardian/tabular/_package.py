"""Garde et inventaire des classeurs / workbook guard and inventory.

Avant toute lecture par calamine : format réel, archive, chiffrement et étendue des feuilles (une seule
cellule en XFD1048576 fait allouer 512 Gio et tue le processus). Les parties jamais émises (commentaires,
propriétés…) sont seulement comptées, sans que leur contenu n'atteigne la sortie.
Before calamine reads anything: real format, archive, encryption and sheet extent (one cell at XFD1048576
allocates 512 GiB and aborts the process). Parts never emitted are only counted.

La garde ne suppose pas que calamine résout les chemins comme nous : chaque cible est mesurée sous toutes
ses lectures plausibles (littérale, normalisée, décodée), et tout désaccord retombe sur le maximum global.
The guard does not assume calamine resolves paths as we do: every target is measured under all plausible
readings, and any disagreement falls back to the global maximum.
"""

from __future__ import annotations

import io
import posixpath
import re
import struct
import zipfile
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import Any
from urllib.parse import unquote

from .. import _native
from ..documents import (
    DocumentError,
    DocumentTooLargeError,
    EncryptedDocumentError,
    MaliciousDocumentError,
    UnsupportedFormatError,
)

MAX_MEMBERS = 2_000
MAX_UNCOMPRESSED = 200 * 1024 * 1024
MAX_RATIO = 100
MAX_PART = 64 * 1024 * 1024  # partie XML lue par nous / XML part we read ourselves
# Zone dense allouée par calamine (32 octets par cellule) : 2**24 cellules = 512 Mio / dense grid allocated by calamine.
MAX_SHEET_AREA = 1 << 24
_RATIO_FLOOR = 1 << 20
_CFB_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06")
BINARY_MAGICS = (_CFB_MAGIC, *_ZIP_MAGICS)
_BOM = b"\xef\xbb\xbf"
TEXT_KINDS = frozenset({"csv", "tsv"})
# Racine de classeur -> format, dans l'ordre d'essai de calamine / workbook root -> format, calamine's order.
_ROOTS = {"xl/workbook.xml": "xlsx", "xl/workbook.bin": "xlsb", "content.xml": "ods"}
# Fin d'archive ZIP : 22 octets + commentaire de 64 Kio au plus / ZIP end record: 22 bytes + up to 64 KiB comment.
_EOCD_WINDOW = 22 + 0xFFFF

_ENCRYPTED = "Fichier chiffré ou protégé (mot de passe, IRM/MIP) : fournir une version non protégée / " \
             "encrypted or rights-protected file: provide an unprotected copy"
_CORRUPT = "Classeur illisible ou corrompu / unreadable or corrupted workbook"
_ENCODING = "Encodage XML non pris en charge (UTF-8 attendu) / unsupported XML encoding (UTF-8 expected)"
_OVERSIZED = "Feuille trop étendue / sheet extent too large"


def name_key(text: str) -> str:
    """Clé de comparaison tolérante : blancs fusionnés, casse ignorée. Elle couvre les écarts entre analyseurs
    XML (normalisation des attributs, fins de ligne). Lenient key: whitespace collapsed, case ignored."""
    return " ".join(text.split()).casefold()


@dataclass(slots=True, frozen=True)
class TableSpec:
    """Tableau Excel nommé (le nom n'est jamais conservé) / Excel table (its name is never kept)."""

    top: int
    left: int
    bottom: int
    right: int
    header_rows: int
    totals_rows: int
    columns: tuple[str, ...]


@dataclass(slots=True)
class Package:
    """Classeur contrôlé et inventorié / checked and inventoried workbook.

    Les champs après `warnings` sont internes au module / fields after `warnings` are internal to the module.
    """

    kind: str
    archive: zipfile.ZipFile | None = None
    date1904: bool = False
    dropped: Counter[str] = field(default_factory=Counter)
    warnings: list[str] = field(default_factory=list)
    members: dict[str, zipfile.ZipInfo] = field(default_factory=dict)
    by_key: dict[str, list[str]] = field(default_factory=dict)
    sheet_parts: dict[str, set[str]] = field(default_factory=dict)
    all_parts: set[str] = field(default_factory=set)
    measured: dict[str, tuple[int, int]] = field(default_factory=dict)
    extents: dict[str, tuple[int, int]] = field(default_factory=dict)
    native: bool = False
    premeasured: dict[str, tuple[tuple[int, int], int, bool]] = field(default_factory=dict)

    def summary(self) -> Package:
        """Copie sans archive ni état interne (transmissible entre processus) / picklable copy, no archive."""
        return Package(self.kind, None, self.date1904, Counter(self.dropped), list(self.warnings))

    def sheet_extent(self, name: str) -> tuple[int, int] | None:
        """Majorant (lignes, colonnes) de la grille calamine, None si borné par le format (xls) ou contrôlé
        globalement (xlsb). Plusieurs parties candidates : la plus étendue fait foi (calamine n'en charge qu'une) ;
        un nom introuvable les prend toutes.
        Upper bound (rows, columns) of calamine's grid; None when the format bounds it (xls) or it was checked
        globally (xlsb). Several candidate parts: the largest decides (calamine loads one); an unmatched name
        takes them all.
        """
        if self.kind in ("xlsx", "xlsm"):
            parts = self.sheet_parts.get(name_key(name)) or self.all_parts
            return _largest(self._part_extent(part) for part in sorted(parts))
        if self.kind == "ods":
            return self.extents.get(name_key(name)) or _largest(self.extents.values())
        return None

    def largest_extent(self) -> tuple[int, int]:
        """Majorant valable pour n'importe quelle feuille / bound valid for any sheet."""
        if self.kind in ("xlsx", "xlsm"):
            return _largest(self._part_extent(part) for part in sorted(self.all_parts))
        return _largest(self.extents.values())

    def _part_extent(self, part: str) -> tuple[int, int]:
        extent = self.measured.get(part)
        if extent is None:
            known = self.premeasured.pop(part, None)  # mesure prise par le noyau / taken by the core
            if known is None:
                xml = self.read(part)
                known = sheet_measure(xml, native=self.native) if xml is not None else ((0, 0), 0, False)
            extent, formulas, headers = known
            self.measured[part] = extent
            if formulas:
                self.dropped["formulas"] += formulas
            if headers:
                self.dropped["headers_footers"] += 1
        return extent

    def adopt_measure(self, measured: tuple[str, int, int, tuple[int, int] | None, int, bool] | None) -> None:
        """Mesure faite par le noyau en lisant une partie de feuille : mêmes octets que `read` (nom, taille et CRC
        de `zipfile` vérifiés, entrées qui se chevauchent refusées), mêmes résultats que `sheet_measure`. La garde
        ne décompresse alors pas la partie une seconde fois. Measurement made by the core while reading a sheet
        part: same bytes as `read` (zipfile's name, size and CRC checked), same results as `sheet_measure`; the
        guard then does not inflate the part a second time."""
        if measured is None:
            return
        part, size, crc, extent, formulas, headers = measured
        info = self.members.get(part)
        if (extent is None or info is None or info.file_size != size or crc != info.CRC
                or info.file_size > MAX_PART or part in self.measured):
            return
        self.premeasured[part] = (extent, formulas, headers)

    def resolve(self, base: str, target: str) -> set[str]:
        """Parties existantes qu'un lecteur pourrait associer à une cible de relation (littérale comme calamine,
        normalisée, décodée, sans tenir compte de la casse ni des blancs).
        Existing parts a reader may map a relationship target to (literal as calamine does, normalised,
        percent-decoded, ignoring case and whitespace)."""
        paths: set[str] = set()
        for variant in {target, unquote(target)}:
            variant = variant.replace("\\", "/")
            readings = {f"{base}/{variant}"}
            if variant.startswith("/"):
                readings.add(variant.lstrip("/"))
            paths |= readings | {posixpath.normpath(path) for path in readings}
        return {member for path in paths for member in self.by_key.get(name_key(path), ())}

    def tables(self, name: str) -> list[TableSpec]:
        """Tableaux Excel d'une feuille, lus dans les parties XML / Excel tables of a sheet, from the XML parts."""
        parts = self.sheet_parts.get(name_key(name)) if self.kind in ("xlsx", "xlsm") else None
        if not parts or len(parts) != 1:
            return []  # partie ambiguë : les heuristiques suffisent / ambiguous part: heuristics suffice
        directory, base = posixpath.split(next(iter(parts)))
        rels = self.read(f"{directory}/_rels/{base}.rels")
        if rels is None:
            return []
        specs: list[TableSpec] = []
        for rel_type, target, mode in _relationships(rels):
            if rel_type.endswith("/hyperlink") and mode == "External":
                self.dropped["hyperlinks"] += 1
            if not rel_type.endswith("/table") or mode == "External":
                continue
            spec = _table_spec(self.read(_resolve(directory, target)))
            if spec is not None:
                specs.append(spec)
        return specs

    def close(self) -> None:
        if self.archive is not None:
            self.archive.close()

    def read(self, name: str, limit: int = MAX_PART) -> bytes | None:
        """Partie de l'archive, taille réelle vérifiée (CRC) / archive part, real size checked (CRC)."""
        info = self.members.get(name.lower())
        if info is None or self.archive is None:
            return None
        if info.file_size > limit:
            raise DocumentTooLargeError("Partie de classeur trop volumineuse / workbook part too large")
        try:
            with self.archive.open(info) as handle:
                data = handle.read(limit + 1)
        except NotImplementedError:
            raise UnsupportedFormatError("Compression ZIP non prise en charge / unsupported ZIP compression") from None
        except (zipfile.BadZipFile, OSError, EOFError, ValueError):
            # Taille ou CRC mensongers : archive forgée / lying size or CRC: forged archive.
            raise MaliciousDocumentError(_CORRUPT) from None
        if len(data) > limit:
            raise DocumentTooLargeError("Partie de classeur trop volumineuse / workbook part too large")
        return data


# --- Détection du format / format sniffing ------------------------------------------------------------------


def open_package(data: bytes, filename: str, native: bool = False) -> Package:
    """Contrôle le fichier et dresse l'inventaire ; lève une DocumentError au message sûr.

    Checks the file and builds the inventory; raises a DocumentError with a safe message. `native` : mesures
    des feuilles par le noyau Rust (mêmes résultats) / sheet measurements by the Rust core (same results).
    """
    suffix = PurePath(filename).suffix.lower().lstrip(".")
    if data.startswith(_ZIP_MAGICS):
        return _open_zip(data, suffix, native)
    if data.startswith(_CFB_MAGIC):
        return _open_cfb(data)
    if _looks_binary(data):
        raise UnsupportedFormatError("Format de classeur non reconnu / unrecognised workbook format")
    # Texte délimité, y compris les « .xls » exportés en texte / delimited text, including text ".xls" exports.
    return Package("tsv" if suffix == "tsv" else "csv")


def _looks_binary(data: bytes) -> bool:
    """Un octet nul hors BOM UTF-16/32 : pas un texte délimité / a NUL byte outside a UTF-16/32 BOM: not text."""
    head = data[:4096]
    return b"\x00" in head and not head.startswith((b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff"))


def _open_zip(data: bytes, suffix: str, native: bool = False) -> Package:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError, ValueError, EOFError, NotImplementedError):
        raise DocumentError(_CORRUPT) from None
    try:
        infos = archive.infolist()
        _check_archive(infos)
        members: dict[str, zipfile.ZipInfo] = {}
        by_key: dict[str, list[str]] = {}
        for info in infos:
            lowered = info.filename.lower()
            # Doublons (même à la casse près) : chaque lecteur pourrait prendre une entrée différente.
            # Duplicates (even case-insensitive): each reader could pick a different entry.
            if lowered in members:
                raise MaliciousDocumentError("Archive : entrées en double / duplicate archive entries")
            members[lowered] = info
            by_key.setdefault(name_key(lowered), []).append(lowered)
        roots = [kind for root, kind in _ROOTS.items() if root in members]
        if not roots:
            raise UnsupportedFormatError("Archive sans classeur reconnu / archive without a known workbook")
        if len(roots) > 1:
            # calamine essaie chaque format à tour de rôle : un classeur rejeté laisserait lire l'autre sans garde.
            # calamine tries each format in turn: a rejected workbook would let the other be read unguarded.
            raise MaliciousDocumentError("Archive ambiguë : plusieurs classeurs / ambiguous archive: several workbooks")
        kind = roots[0]
        if kind == "xlsx" and (suffix == "xlsm" or "xl/vbaproject.bin" in members):
            kind = "xlsm"
        package = Package(kind, archive, members=members, by_key=by_key, native=native)
        if kind == "ods":
            _inventory_ods(package)
        else:
            _inventory_ooxml(package)
    except BaseException:
        archive.close()
        raise
    return package


def _check_archive(infos: list[zipfile.ZipInfo]) -> None:
    if len(infos) > MAX_MEMBERS:
        raise MaliciousDocumentError(f"Archive : plus de {MAX_MEMBERS} entrées / more than {MAX_MEMBERS} entries")
    total = 0
    for info in infos:
        if info.flag_bits & 0x1:
            raise EncryptedDocumentError(_ENCRYPTED)
        total += info.file_size
        if info.file_size > _RATIO_FLOOR and info.file_size > MAX_RATIO * max(info.compress_size, 1):
            raise MaliciousDocumentError("Taux de compression anormal (bombe ZIP) / abnormal compression ratio")
    if total > MAX_UNCOMPRESSED:
        raise DocumentTooLargeError("Classeur trop volumineux une fois décompressé / workbook too large uncompressed")


_DECLARED_ENCODING = re.compile(rb"""<\?xml[^>]{0,256}?encoding\s{0,16}=\s{0,16}["']([A-Za-z0-9._\-]{1,40})["']""")


def _require_utf8(raw: bytes) -> None:
    """Partie XML en UTF-8 : sinon deux analyseurs pourraient décoder des noms différents (latin-1 contre
    windows-1252…). XML part must be UTF-8, else two parsers could decode different names."""
    head = raw[:512]
    declared = _DECLARED_ENCODING.match(head.removeprefix(_BOM).lstrip())
    if (head.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in head
            or (declared is not None and declared.group(1).lower() not in (b"utf-8", b"utf8"))):
        raise UnsupportedFormatError(_ENCODING)


# --- OOXML -------------------------------------------------------------------------------------------------

# (motif de partie, catégorie) ; seuls les noms sont lus / (part pattern, category); only names are read.
_OOXML_PARTS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), category) for pattern, category in (
        (r"^xl/threadedcomments/[^/]{1,255}\.xml$", "threaded_comments"),
        (r"^xl/persons/[^/]{1,255}\.xml$", "comment_persons"),
        (r"^xl/pivotcache/pivotcachedefinition[^/]{0,255}\.(?:xml|bin)$", "pivot_caches"),
        (r"^xl/externallinks/externallink[^/]{0,255}\.(?:xml|bin)$", "external_links"),
        (r"(?:^|/)vbaproject\.bin$", "vba_projects"),
        (r"^xl/drawings/drawing[^/]{0,255}\.xml$", "drawings"),
        (r"^xl/charts/chart[^/]{0,255}\.xml$", "charts"),
        (r"^xl/media/[^/]{1,255}$", "images"),
        (r"^xl/embeddings/[^/]{1,255}$", "embedded_objects"),
        (r"^xl/revisions/[^/]{1,255}$", "revisions"),
        (r"^customxml/item[0-9]{1,6}\.xml$", "custom_xml"),
        (r"^xl/(?:connections\.(?:xml|bin)|querytables/[^/]{1,255})$", "connections"),
        (r"^xl/(?:slicercaches|timelinecaches)/[^/]{1,255}$", "slicers"),
        (r"^xl/richdata/[^/]{1,255}$", "rich_data"),
        (r"^docmetadata/labelinfo\.xml$", "sensitivity_labels"),
    )
)
_COMMENT_PART = re.compile(r"^xl/comments[^/]{0,255}\.(xml|bin)$")
_AUTHOR_RE = re.compile(rb"<(?:\w{1,32}:)?(?:creator|lastModifiedBy)>\s{0,4096}[^<\s]")
_PROPERTY_PARTS = ("docprops/core.xml", "docprops/app.xml", "docprops/custom.xml")


def _inventory_ooxml(package: Package) -> None:
    for name in package.members:
        comment = _COMMENT_PART.match(name)
        if comment:
            raw = package.read(name) if comment.group(1) == "xml" else None
            package.dropped["comments"] += raw.count(b"<comment ") if raw is not None else 1
            continue
        for pattern, category in _OOXML_PARTS:
            if pattern.search(name):
                package.dropped[category] += _count_entries(package, name, category)
                break
    properties = [p for p in _PROPERTY_PARTS if p in package.members]
    if properties:
        package.dropped["document_properties"] += len(properties)
    core = package.read("docProps/core.xml")
    if core is not None and _AUTHOR_RE.search(core):
        package.warnings.append("Auteur présent dans les propriétés du document, non émis / "
                                "document author present in properties, not emitted")
    custom = package.read("docProps/custom.xml")
    if custom is not None and b"MSIP_Label_" in custom:
        package.dropped["sensitivity_labels"] += 1
    # calamine lit ces parties en entier : taille réelle vérifiée ici / calamine reads them whole: real size checked.
    for part in ("xl/sharedStrings.xml", "xl/sharedStrings.bin", "xl/styles.xml", "xl/styles.bin"):
        package.read(part)
    if package.kind == "xlsb":
        _xlsb_extents(package)
        return
    _map_xlsx_sheets(package)


def _count_entries(package: Package, name: str, category: str) -> int:
    """Nombre d'éléments dans une partie (fils de commentaires, personnes) / entries in a part."""
    marker = {"threaded_comments": b"<threadedComment ", "comment_persons": b"<person "}.get(category)
    if marker is None:
        return 1
    raw = package.read(name)
    return max(raw.count(marker), 1) if raw is not None else 1


def _relationship_targets(package: Package, path: str) -> dict[str, list[str]]:
    """Cibles par identifiant (clé tolérante, doublons gardés) / targets per id (lenient key, duplicates kept)."""
    raw = package.read(path)
    targets: dict[str, list[str]] = {}
    if raw is not None:
        _require_utf8(raw)
        for rel_id, target in _relationship_ids(raw):
            targets.setdefault(name_key(rel_id), []).append(target)
    return targets


def _map_xlsx_sheets(package: Package) -> None:
    """Feuille -> parties candidates. calamine lit `name` et tout attribut `*:id` ou `id`, résout la cible
    sans la normaliser et cherche la partie sans tenir compte de la casse : on mesure toutes ces lectures.
    Sheet -> candidate parts; calamine reads `name` and any `*:id` or `id` attribute, resolves the target
    without normalising it and looks parts up case-insensitively: every such reading is measured."""
    workbook = package.read("xl/workbook.xml")
    if workbook is None:
        raise DocumentError(_CORRUPT)
    _require_utf8(workbook)
    targets = _relationship_targets(package, "xl/_rels/workbook.xml.rels")
    package.all_parts = {part for values in targets.values() for target in values
                         for part in package.resolve("xl", target)}
    package.all_parts.update(name for name in package.members if name.startswith("xl/worksheets/"))
    root = _parse_xml(workbook)
    for element in root.iter():
        tag = _local(element.tag)
        if tag == "workbookPr":
            package.date1904 = element.get("date1904", "").lower() in ("1", "true")
        elif tag == "definedName" and not element.get("name", "").startswith("_xlnm."):
            package.dropped["defined_names"] += 1  # noms intégrés exclus (zone d'impression…) / built-ins excluded
        elif tag == "sheet":
            ids = [value for key, value in element.attrib.items() if _local(key).lower() == "id"]
            parts = {part for rel_id in ids for target in targets.get(name_key(rel_id), ())
                     for part in package.resolve("xl", target)}
            package.sheet_parts.setdefault(name_key(element.get("name", "")), set()).update(parts)
    if package.date1904:
        package.warnings.append("Système de dates 1904 détecté / 1904 date system detected")


def _relationship_ids(raw: bytes) -> list[tuple[str, str]]:
    root = _parse_xml(raw)
    return [(el.get("Id", ""), el.get("Target", "")) for el in root.iter() if _local(el.tag) == "Relationship"]


def _relationships(raw: bytes) -> list[tuple[str, str, str]]:
    root = _parse_xml(raw)
    return [(el.get("Type", ""), el.get("Target", ""), el.get("TargetMode", ""))
            for el in root.iter() if _local(el.tag) == "Relationship"]


def _resolve(base: str, target: str) -> str:
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join(base, target))


_ESCAPE_RE = re.compile(r"_x([0-9A-Fa-f]{4})_")
_A1_RE = re.compile(r"^\$?([A-Za-z]{1,3})\$?([0-9]{1,7})$")


def _table_spec(raw: bytes | None) -> TableSpec | None:
    if raw is None:
        return None
    root = _parse_xml(raw)
    ref = root.get("ref", "")
    corners = [_parse_a1(part) for part in ref.split(":")]
    if any(c is None for c in corners):
        return None
    (top, left), (bottom, right) = corners[0], corners[-1]
    columns = tuple(_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), el.get("name", ""))
                    for el in root.iter() if _local(el.tag) == "tableColumn")
    try:
        header_rows = int(root.get("headerRowCount", "1"))
        totals_rows = int(root.get("totalsRowCount", "0"))
    except ValueError:
        return None
    return TableSpec(top, left, bottom, right, max(0, min(header_rows, 1)), max(0, min(totals_rows, 1)), columns)


def _parse_a1(ref: str) -> tuple[int, int] | None:
    m = _A1_RE.match(ref.strip())
    if m is None:
        return None
    return int(m.group(2)) - 1, column_index(m.group(1).encode())


def _parse_xml(raw: bytes) -> Any:
    from defusedxml import DefusedXmlException
    from defusedxml.ElementTree import ParseError, fromstring

    try:
        return fromstring(raw, forbid_dtd=True)
    except DefusedXmlException:
        raise MaliciousDocumentError("XML interdit (DTD ou entités) / forbidden XML (DTD or entities)") from None
    except ParseError:
        raise DocumentError(_CORRUPT) from None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


# --- Étendue des feuilles xlsx / xlsx sheet extent ---------------------------------------------------------

_WS_QUOTES = bytes.maketrans(b"\t\n\r'", b'   "')
# Hors de ces formes, le chemin exact est pris / outside these forms, the exact path is taken.
_FAST_BLOCKERS = (b"<!", b" r ", b" r= ", b":c", b":row")
_ODD_REF = re.compile(rb' r="(?![A-Za-z]{0,16}[0-9]{1,16}")')
_REF_DIGITS = re.compile(rb' r="[A-Za-z]{0,16}([0-9]{1,16})"')
_REF_LETTERS = re.compile(rb' r="([A-Za-z]{1,16})[0-9]')
_ROWS_OVER_99999 = re.compile(rb' r="[A-Za-z]{0,16}[0-9]{6}')
_TWO_LETTERS = re.compile(rb' r="[A-Za-z]{2}')
_THREE_LETTERS = re.compile(rb' r="[A-Za-z]{3}')
_NOISE_OPEN = re.compile(rb"<!--|<!\[CDATA\[|<\?")
_NOISE_CLOSE = {b"<!--": b"-->", b"<![CDATA[": b"]]>", b"<?": b"?>"}
_TAG = re.compile(
    rb"<(/?)(?:[A-Za-z_][\w.\-]{0,63}:)?(row|c)"
    rb"((?:\s{1,64}[^\s=>/]{1,128}\s{0,64}=\s{0,64}(?:\"[^\"]{0,65536}\"|'[^']{0,65536}')){0,256})\s{0,64}(/?)>"
)
_OPENING = re.compile(rb"<(?:[A-Za-z_][\w.\-]{0,63}:)?(?:row|c)(?=[\s/>])")
_ATTR_R = re.compile(rb"""(?:^|\s)r\s{0,64}=\s{0,64}(?:"([^"]{0,65536})"|'([^']{0,65536})')""")
_LETTERS = re.compile(rb"[A-Za-z]{1,64}")
_NOT_DIGITS = re.compile(rb"[^0-9]{1,64}")
_UNMEASURABLE = (1 << 31, 1 << 31)


def _as_utf8(xml: bytes) -> bytes | None:
    """Partie UTF-16 ré-encodée en UTF-8 pour les motifs binaires ; None si indécodable.
    UTF-16 part re-encoded as UTF-8 for the byte patterns; None when undecodable."""
    head = xml[:1024]
    if not (head.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in head):
        return xml
    codec = "utf-16" if head.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-16-le" if head[1:2] == b"\x00" \
        else "utf-16-be"
    try:
        return xml.decode(codec).encode()
    except UnicodeDecodeError:
        return None


def _strip_markup_noise(text: bytes) -> bytes:
    """Retire commentaires, sections CDATA et instructions en temps linéaire (jamais d'expression paresseuse
    rejouée sur tout le texte). Removes comments, CDATA sections and PIs in linear time."""
    pieces: list[bytes] = []
    position = 0
    while True:
        found = _NOISE_OPEN.search(text, position)
        if found is None:
            pieces.append(text[position:])
            break
        pieces.append(text[position:found.start()])
        closer = _NOISE_CLOSE[found.group()]
        end = text.find(closer, found.end())
        if end == -1:
            break  # non terminé : XML invalide, calamine échouera aussi / unterminated: calamine fails too
        position = end + len(closer)
    return b"".join(pieces)


def _largest(extents: Iterable[tuple[int, int]]) -> tuple[int, int]:
    """Étendue de plus grande surface / extent with the largest area."""
    return max(extents, key=lambda extent: extent[0] * extent[1], default=(0, 0))


def column_index(letters: bytes) -> int:
    """'A' -> 0, 'XFD' -> 16383 ; insensible à la casse / case-insensitive."""
    index = 0
    for byte in letters.upper():
        index = index * 26 + byte - 64
    return index - 1


def _native_core(native: bool, name: str) -> Any:
    """Noyau Rust s'il est permis et fournit `name`, sinon None / Rust core when allowed and providing `name`."""
    core = _native.core() if native else None
    return core if core is not None and hasattr(core, name) else None


def _measuring_core(native: bool, limit: int) -> Any:
    """Noyau pour `sheet_measure` si la limite tient dans ses entiers / core when the limit fits its integers."""
    return _native_core(native, "sheet_measure") if 0 <= limit < 1 << 127 else None


def sheet_measure(xml: bytes, limit: int = MAX_SHEET_AREA,
                  native: bool = False) -> tuple[tuple[int, int], int, bool]:
    """Étendue (`xlsx_extent`), formules et en-têtes ou pieds de page d'une partie de feuille, comptés par la
    garde ; en un passage natif s'il est permis (chemin exact toujours en Python). Extent, formulas and headers
    or footers of a sheet part; in one native pass when allowed (the exact path stays in Python)."""
    core = _measuring_core(native, limit)
    if core is not None:
        extent, formulas, headers = core.sheet_measure(xml, limit)
        return (xlsx_extent(xml, limit) if extent is None else extent), formulas, headers
    extent = xlsx_extent(xml, limit)
    formulas = xml.count(b"<f>") + xml.count(b"<f ") + xml.count(b":f>") + xml.count(b":f ")
    return extent, formulas, b"Header>" in xml or b"Footer>" in xml


def xlsx_extent(xml: bytes, limit: int = MAX_SHEET_AREA, native: bool = False) -> tuple[int, int]:
    """Majorant sûr (lignes, colonnes) des cellules à valeur d'une feuille xlsx / sound bound of valued cells.

    Chemin rapide si chaque balise porte r en premier (Excel, xlsxwriter, openpyxl, LibreOffice) : un majorant
    grossier suffit tant qu'il reste sous `limit`, sinon les maxima exacts. Autrement, analyse exacte des balises.
    Fast path when every tag carries r first: a coarse bound while it stays under `limit`, else the exact maxima.
    Otherwise, an exact tag scan. `native` : chemin rapide en Rust, même résultat ; Python garde le chemin exact.
    `native`: fast path in Rust, same result; Python keeps the exact path.
    """
    core = _measuring_core(native, limit)
    if core is not None:
        measured = core.sheet_measure(xml, limit)[0]
        if measured is not None:
            return measured
    decoded = _as_utf8(xml)
    if decoded is None:
        return _UNMEASURABLE
    text = decoded.translate(_WS_QUOTES)
    start = len(_BOM) if text.startswith(_BOM) else 0
    if (text.find(b"<?", start + 1) != -1 or any(blocker in text for blocker in _FAST_BLOCKERS)
            or _ODD_REF.search(text) is not None):
        return _xlsx_extent_exact(text)
    cells = text.count(b"<c ") + text.count(b"<c>") + text.count(b"<c/")
    rows = text.count(b"<row ") + text.count(b"<row>") + text.count(b"<row/")
    if text.count(b'<c r="') != cells or text.count(b'<row r="') != rows:
        return _xlsx_extent_exact(text)
    # Toute balise porte r : l'étendue est le plus grand r / every tag carries r: the extent is the largest r.
    max_row = 99_999 if _ROWS_OVER_99999.search(text) is None else None
    max_col = 26 if _TWO_LETTERS.search(text) is None else 702 if _THREE_LETTERS.search(text) is None else None
    if max_row is None or max_col is None or max_row * max_col > limit:
        max_row = max(map(int, set(_REF_DIGITS.findall(text))), default=0)
        max_col = max((column_index(c) + 1 for c in set(_REF_LETTERS.findall(text))), default=0)
    return max_row, max_col


def _xlsx_extent_exact(text: bytes) -> tuple[int, int]:
    """Rejoue le positionnement de calamine (r explicite, sinon rang dans la ligne) / replays calamine positioning.

    Une balise illisible rend l'étendue non mesurable, donc la feuille est écartée / an unparsable tag makes
    the extent unmeasurable, so the sheet is skipped.
    """
    text = _strip_markup_noise(text)
    tags = [tag for tag in _TAG.findall(text) if not tag[0]]
    if len(tags) != len(_OPENING.findall(text)):
        return _UNMEASURABLE
    max_row = max_col = -1
    row = -1
    row_tags = 0
    col_index = 0
    prev_col = -1
    for _closing, name, attrs, self_closing in tags:
        refs = _ATTR_R.findall(attrs)
        ref = (refs[-1][0] or refs[-1][1]) if refs else b""
        # Toutes les lettres, tous les chiffres : majorant de toute lecture de la référence / bounds any reading.
        letters = b"".join(_LETTERS.findall(ref))
        digits = _NOT_DIGITS.sub(b"", ref)
        if name == b"row":
            row_tags += 1
            row = int(digits) - 1 if digits else max(row + 1, row_tags - 1)
            col_index, prev_col = 0, -1
            continue
        col = (column_index(letters) if len(letters) <= 16 else 1 << 62) if letters else max(col_index, prev_col + 1)
        cell_row = int(digits) - 1 if digits else max(row, 0)
        col_index += 1
        prev_col = col
        if not self_closing:
            max_row = max(max_row, cell_row)
            max_col = max(max_col, col)
    return max_row + 1, max_col + 1


# --- ODS -----------------------------------------------------------------------------------------------------

_ODS_TOKEN = re.compile(
    rb"<(/?)table:(table|table-row|table-cell|covered-table-cell)(?=[\s/>])"
    rb"((?:\s{1,64}[^\s=>/]{1,128}\s{0,64}=\s{0,64}(?:\"[^\"]{0,65536}\"|'[^']{0,65536}')){0,256})\s{0,64}(/?)>"
)
_ODS_OPENING = re.compile(rb"<table:(?:table|table-row|table-cell|covered-table-cell)(?=[\s/>])")
_ODS_NAME = re.compile(rb"""table:name\s{0,64}=\s{0,64}(?:"([^"]{0,4096})"|'([^']{0,4096})')""")
_ODS_ROWS = re.compile(rb"""number-rows-repeated\s{0,64}=\s{0,64}["']([0-9]{1,12})""")
_ODS_COLS = re.compile(rb"""number-columns-repeated\s{0,64}=\s{0,64}["']([0-9]{1,12})""")


def ods_extents(content: bytes) -> dict[str, tuple[int, int]]:
    """Majorant (lignes, colonnes) par feuille ODS, répétitions comprises / per-sheet bound, repeats included.

    Une balise illisible rend toutes les feuilles non mesurables ; une table imbriquée (lue par calamine dans
    la ligne qui la contient) rend sa feuille non mesurable ; deux feuilles de même nom gardent le maximum.
    An unparsable tag makes every sheet unmeasurable; a nested table (read by calamine into its row) makes its
    sheet unmeasurable; two sheets sharing a name keep the maximum.
    """
    import html

    content = _strip_markup_noise(content)
    tokens = _ODS_TOKEN.findall(content)
    if sum(1 for token in tokens if not token[0]) != len(_ODS_OPENING.findall(content)):
        return {"": _UNMEASURABLE}
    extents: dict[str, tuple[int, int]] = {}
    depth = 0
    name = ""
    nested = False
    row = row_repeat = col = max_row = max_col = 0
    for closing, tag, attrs, self_closing in tokens:
        if tag == b"table":
            if closing:
                depth -= 1
                if depth == 0:
                    extent = _UNMEASURABLE if nested else (max_row, max_col)
                    extents[name] = _largest((extents.get(name, (0, 0)), extent))
            elif not self_closing:
                depth += 1
                if depth == 1:
                    found = _ODS_NAME.search(attrs)
                    raw_name = (found.group(1) or found.group(2)) if found else b""
                    name = html.unescape(raw_name.decode("utf-8", "replace"))
                    nested = False
                    row = row_repeat = col = max_row = max_col = 0
                else:
                    nested = True
            continue
        if depth != 1:
            continue
        if tag == b"table-row":
            if closing:
                row += row_repeat
                continue
            repeat = _ODS_ROWS.search(attrs)
            row_repeat = int(repeat.group(1)) if repeat else 1
            col = 0
            if self_closing:
                row += row_repeat
            continue
        if closing:
            continue
        repeat = _ODS_COLS.search(attrs)
        span = int(repeat.group(1)) if repeat else 1
        if not self_closing or b"value-type" in attrs:
            max_col = max(max_col, col + span)
            max_row = max(max_row, row + row_repeat)
        col += span
    if depth:
        return {"": _UNMEASURABLE}  # table non fermée / unclosed table
    return extents


def _inventory_ods(package: Package) -> None:
    manifest = package.read("META-INF/manifest.xml")
    if manifest is not None and b"encryption-data" in manifest:
        raise EncryptedDocumentError(_ENCRYPTED)
    content = package.read("content.xml")
    if content is None:
        raise DocumentError(_CORRUPT)
    _require_utf8(content)
    for name, extent in ods_extents(content).items():
        key = name_key(name)
        package.extents[key] = _largest((package.extents.get(key, (0, 0)), extent))
    annotations = content.count(b"<office:annotation ") + content.count(b"<office:annotation>")
    if annotations:
        package.dropped["comments"] += annotations
    formulas = content.count(b"table:formula=")
    if formulas:
        package.dropped["formulas"] += formulas
    if "meta.xml" in package.members:
        package.dropped["document_properties"] += 1
    for name in package.members:
        if name.startswith(("basic/", "scripts/")):
            package.dropped["vba_projects"] = 1
        elif name.startswith("pictures/"):
            package.dropped["images"] += 1
        elif name.startswith("object ") and name.endswith("/content.xml"):
            package.dropped["embedded_objects"] += 1


# --- xlsb ------------------------------------------------------------------------------------------------------

_XLSB_ROW = 0
_XLSB_CELLS = frozenset({*range(1, 12), 62})  # BrtCellBlank..BrtFmlaError, BrtCellRString
_XLSB_BUNDLE_SHEET = 156  # BrtBundleSh : feuille du classeur / workbook sheet


def _biff12_records(data: bytes) -> Iterator[tuple[int, int, int]]:
    """(type, début, fin) de chaque enregistrement BIFF12 (MS-XLSB 2.1.4) / each BIFF12 record."""
    pos, size_total = 0, len(data)
    try:
        while pos < size_total:
            byte = data[pos]
            pos += 1
            record = byte & 0x7F
            if byte & 0x80:
                record |= (data[pos] & 0x7F) << 7
                pos += 1
            size = shift = 0
            for _ in range(4):
                byte = data[pos]
                pos += 1
                size |= (byte & 0x7F) << shift
                shift += 7
                if not byte & 0x80:
                    break
            yield record, pos, pos + size
            pos += size
    except IndexError:
        raise DocumentError(_CORRUPT) from None


def xlsb_extent(data: bytes) -> tuple[int, int]:
    """Majorant (lignes, colonnes) d'une feuille BIFF12 (MS-XLSB) / bound for one BIFF12 sheet."""
    row = max_row = max_col = -1
    unpack = struct.Struct("<I").unpack_from
    try:
        for record, start, end in _biff12_records(data):
            if end - start < 4:
                continue
            if record == _XLSB_ROW:
                row = unpack(data, start)[0]
            elif record in _XLSB_CELLS:
                max_row = max(max_row, row)
                max_col = max(max_col, unpack(data, start)[0])
    except struct.error:
        raise DocumentError(_CORRUPT) from None
    return max_row + 1, max_col + 1


def _xlsb_sheet_ids(workbook: bytes) -> list[str]:
    """Identifiants de relation des feuilles (BrtBundleSh) ; un flux tronqué garde ceux déjà lus, calamine
    échouant au même endroit. Sheet relationship ids; a truncated stream keeps those read so far."""
    ids: list[str] = []
    try:
        for record, start, end in _biff12_records(workbook):
            if record != _XLSB_BUNDLE_SHEET or end - start < 12 or end > len(workbook):
                continue
            length = struct.unpack_from("<I", workbook, start + 8)[0]
            if length != 0xFFFFFFFF:  # XLNullableWideString nulle / null string
                ids.append(workbook[start + 12:min(start + 12 + 2 * length, end)].decode("utf-16-le", "replace"))
    except DocumentError:
        pass
    return ids


def _xlsb_extents(package: Package) -> None:
    """Sans correspondance nom -> partie en xlsb, la plus grande feuille fait foi : le classeur est refusé si
    une feuille candidate dépasse. No name -> part map in xlsb: any oversized candidate rejects the workbook."""
    workbook = package.read("xl/workbook.bin")
    targets = _relationship_targets(package, "xl/_rels/workbook.bin.rels")
    parts = {name for name in package.members if name.startswith("xl/worksheets/") and name.endswith(".bin")}
    for rel_id in _xlsb_sheet_ids(workbook or b""):
        parts.update(part for target in targets.get(name_key(rel_id), ()) for part in package.resolve("xl", target))
    for part in sorted(parts):
        raw = package.read(part)
        if raw is not None:
            rows, cols = xlsb_extent(raw)
            if rows * cols > MAX_SHEET_AREA:
                raise DocumentTooLargeError(_OVERSIZED)


# --- OLE (xls, OOXML chiffré) / OLE (xls, encrypted OOXML) ---------------------------------------------------

_BIFF_FILEPASS = 0x002F
_BIFF_EOF = 0x000A
_MAX_GLOBAL_RECORDS = 1_000_000


def _open_cfb(data: bytes) -> Package:
    import olefile

    try:
        ole = olefile.OleFileIO(io.BytesIO(data))
    except Exception:  # olefile lève des exceptions variées / olefile raises assorted exceptions
        raise DocumentError(_CORRUPT) from None
    try:
        if ole.exists("EncryptedPackage") or ole.exists("\x06DataSpaces"):
            raise EncryptedDocumentError(_ENCRYPTED)
        stream = "Workbook" if ole.exists("Workbook") else "Book" if ole.exists("Book") else None
        if stream is None:
            raise UnsupportedFormatError("Conteneur OLE sans classeur / OLE container without a workbook")
        if _biff_encrypted(ole.openstream(stream).read()):
            raise EncryptedDocumentError(_ENCRYPTED)
        package = Package("xls")
        for entry in ole.listdir(streams=True, storages=True):
            head = entry[0]
            if head in ("\x05SummaryInformation", "\x05DocumentSummaryInformation"):
                package.dropped["document_properties"] += 1
            elif head == "_VBA_PROJECT_CUR":
                package.dropped["vba_projects"] = 1
            elif head.startswith("MBD") and len(entry) == 1:
                package.dropped["embedded_objects"] += 1
    finally:
        ole.close()
    _guard_trailing_archive(data)
    return package


def _guard_trailing_archive(data: bytes) -> None:
    """Polyglotte OLE + ZIP : si calamine rejette le flux BIFF, il essaie ensuite de lire l'archive ZIP placée
    en fin de fichier comme un classeur ; celle-ci passe donc la même garde. OLE + ZIP polyglot: when calamine
    rejects the BIFF stream it then reads a trailing ZIP archive as a workbook, so that archive is guarded too."""
    if b"PK\x05\x06" not in data[-_EOCD_WINDOW:]:
        return
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = {name.lower() for name in archive.namelist()}
    except (zipfile.BadZipFile, OSError, ValueError, EOFError, NotImplementedError):
        return  # pas d'archive lisible en fin de fichier / no readable trailing archive
    if not names & _ROOTS.keys():
        return  # aucun classeur : rien que calamine puisse lire / no workbook calamine could read
    package = _open_zip(data, "")  # toute anomalie refuse le fichier / any anomaly rejects the file
    try:
        rows, cols = package.largest_extent()
        if rows * cols > MAX_SHEET_AREA:
            raise MaliciousDocumentError("Fichier polyglotte OLE + ZIP refusé / OLE + ZIP polyglot rejected")
    finally:
        package.close()


def _biff_encrypted(stream: bytes) -> bool:
    """FILEPASS dans le flux global BIFF / FILEPASS record in the BIFF globals substream."""
    pos = 0
    for _ in range(_MAX_GLOBAL_RECORDS):
        if pos + 4 > len(stream):
            return False
        record, size = struct.unpack_from("<HH", stream, pos)
        if record == _BIFF_FILEPASS:
            return True
        if record == _BIFF_EOF:
            return False
        pos += 4 + size
    return False
