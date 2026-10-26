"""Fabriques de classeurs pour les tests tableur / workbook factories for the spreadsheet tests.

Tout est généré en mémoire : aucun fichier réel, aucune donnée personnelle réelle.
Everything is generated in memory: no real file, no real personal data.
"""

from __future__ import annotations

import io
import struct
import warnings
import zipfile
from collections.abc import Callable, Mapping
from typing import Any

import xlsxwriter

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WORKSHEET_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
_PACKAGE_RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships '
                 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" '
                 'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                 'Target="xl/workbook.xml"/></Relationships>')
_CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8"?><Types '
                  'xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                  '<Default Extension="rels" '
                  'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                  '<Default Extension="xml" ContentType="application/xml"/></Types>')
ODS_MIME = "application/vnd.oasis.opendocument.spreadsheet"
_ODS_NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
           'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
           'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
           'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"')
_HIDDEN_STYLE = ('<office:automatic-styles><style:style style:name="hid" style:family="table">'
                 '<style:table-properties table:display="false"/></style:style></office:automatic-styles>')
_MANIFEST = ('<?xml version="1.0" encoding="UTF-8"?><manifest:manifest '
             'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">'
             f'<manifest:file-entry manifest:full-path="/" manifest:media-type="{ODS_MIME}"/>'
             '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
             '{extra}</manifest:manifest>')


def nir(body13: str) -> str:
    """NIR valide : clé = 97 - (13 chiffres mod 97) / valid NIR from its 13-digit body."""
    return f"{body13}{97 - int(body13) % 97:02d}"


def luhn_complete(prefix: str) -> str:
    """Ajoute le chiffre de Luhn / appends the Luhn check digit."""
    for digit in "0123456789":
        candidate = prefix + digit
        total = sum(int(c) for c in candidate[-1::-2])
        total += sum((2 * int(c)) // 10 + (2 * int(c)) % 10 for c in candidate[-2::-2])
        if total % 10 == 0:
            return candidate
    raise AssertionError("unreachable")


def xlsx_bytes(build: Callable[[xlsxwriter.Workbook], None], options: Mapping[str, Any] | None = None) -> bytes:
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True, **(options or {})})
    build(workbook)
    workbook.close()
    return buffer.getvalue()


def rezip(data: bytes, replace: Mapping[str, bytes | Callable[[bytes], bytes]] | None = None,
          add: Mapping[str, bytes] | None = None) -> bytes:
    """Copie d'une archive avec des parties remplacées ou ajoutées / archive copy with parts replaced or added."""
    source = zipfile.ZipFile(io.BytesIO(data))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            raw = source.read(info.filename)
            change = (replace or {}).get(info.filename)
            if change is not None:
                raw = change(raw) if callable(change) else change
            target.writestr(info.filename, raw)
        for name, raw in (add or {}).items():
            target.writestr(name, raw)
    return output.getvalue()


def zip_bytes(members: list[tuple[str, bytes]]) -> bytes:
    """Archive brute, doublons permis / raw archive, duplicates allowed."""
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # « Duplicate name » voulu / intended duplicates
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, raw in members:
                archive.writestr(name, raw)
    return output.getvalue()


def sheet_xml(*cells: str) -> bytes:
    """Feuille xlsx minimale, une chaîne par cellule / minimal sheet, one string per cell."""
    rows: dict[str, list[str]] = {}
    for cell in cells:
        rows.setdefault("".join(ch for ch in cell if ch.isdigit()), []).append(cell)
    body = "".join(f'<row r="{row}">' + "".join(f'<c r="{c}" t="inlineStr"><is><t>v</t></is></c>' for c in refs)
                   + "</row>" for row, refs in rows.items())
    return f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="{MAIN_NS}"><sheetData>{body}</sheetData>' \
           "</worksheet>".encode()


# A1 et XFD1048576 : calamine allouerait 512 Gio et tuerait le processus / calamine would allocate 512 GiB.
FAR_SHEET = sheet_xml("A1", "XFD1048576")


def raw_xlsx(sheets: str, targets: Mapping[str, str], parts: list[tuple[str, bytes]],
             rel_ns: str = REL_NS) -> bytes:
    """Classeur xlsx écrit à la main : éléments <sheet>, cibles de relation, parties / hand-written xlsx."""
    workbook = (f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="{MAIN_NS}" xmlns:r="{rel_ns}">'
                f"<sheets>{sheets}</sheets></workbook>")
    rels = "".join(f'<Relationship Id="{rel_id}" Type="{WORKSHEET_REL}" Target="{target}"/>'
                   for rel_id, target in targets.items())
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships '
            f'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>')
    return zip_bytes([("[Content_Types].xml", _CONTENT_TYPES.encode()), ("_rels/.rels", _PACKAGE_RELS.encode()),
                      ("xl/workbook.xml", workbook.encode()), ("xl/_rels/workbook.xml.rels", rels.encode()),
                      *parts])


def load_without_guard(data: bytes, suffix: str, options: Any) -> Any:
    """Cible de bac à sable : lecture sans garde d'étendue, pour vérifier le confinement d'un plantage natif.

    Sandbox target: reading without the extent guard, to check that a native crash stays confined.
    """
    from gdprguardian.tabular import _package, _reader

    original = _package.Package.sheet_extent
    _package.Package.sheet_extent = lambda self, name: None  # type: ignore[method-assign]
    try:
        return _reader.load_in_worker(data, suffix, options)
    finally:
        _package.Package.sheet_extent = original  # type: ignore[method-assign]


def ods_bytes(tables: Mapping[str, str], hidden: tuple[str, ...] = (), manifest_extra: str = "",
              extra_parts: Mapping[str, bytes] | None = None) -> bytes:
    """ODS minimal ; `tables` : nom -> XML des lignes (sans espaces entre cellules) / name -> rows XML."""
    sheets = []
    for name, rows in tables.items():
        style = ' table:style-name="hid"' if name in hidden else ""
        sheets.append(f'<table:table table:name="{name}"{style}>{rows}</table:table>')
    content = (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {_ODS_NS} office:version="1.2">'
               f"{_HIDDEN_STYLE}<office:body><office:spreadsheet>{''.join(sheets)}</office:spreadsheet>"
               "</office:body></office:document-content>")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), ODS_MIME)
        archive.writestr("content.xml", content, zipfile.ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", _MANIFEST.format(extra=manifest_extra), zipfile.ZIP_DEFLATED)
        for name, raw in (extra_parts or {}).items():
            archive.writestr(name, raw, zipfile.ZIP_DEFLATED)
    return output.getvalue()


def ods_row(*values: str | float, repeat: int = 1) -> str:
    """Ligne ODS ; '' = cellule vide / ODS row; '' = empty cell."""
    cells = []
    for value in values:
        if value == "":
            cells.append("<table:table-cell/>")
        elif isinstance(value, float):
            cells.append(f'<table:table-cell office:value-type="float" office:value="{value}">'
                         f"<text:p>{value}</text:p></table:table-cell>")
        else:
            cells.append(f'<table:table-cell office:value-type="string"><text:p>{value}</text:p></table:table-cell>')
    attribute = f' table:number-rows-repeated="{repeat}"' if repeat > 1 else ""
    return f"<table:table-row{attribute}>{''.join(cells)}</table:table-row>"


def cfb_bytes(streams: Mapping[str, bytes]) -> bytes:
    """Conteneur OLE/CFB v3 minimal (secteurs de 512 octets, sans mini-flux) / minimal CFB v3 container.

    Chaque flux est complété à 4 096 octets pour rester hors du mini-flux / streams padded to 4,096 bytes.
    """
    end, free, fat_sector, no_stream = 0xFFFFFFFE, 0xFFFFFFFF, 0xFFFFFFFD, 0xFFFFFFFF
    names = list(streams)
    if len(names) > 3:
        raise ValueError("au plus 3 flux / at most 3 streams")
    payloads = [streams[name].ljust(4096, b"\0") for name in names]
    payloads = [payload.ljust(-(-len(payload) // 512) * 512, b"\0") for payload in payloads]
    fat = [fat_sector, end]
    starts = []
    for payload in payloads:
        start = len(fat)
        starts.append(start)
        count = len(payload) // 512
        fat += [start + i + 1 for i in range(count - 1)] + [end]
    fat += [free] * (128 - len(fat))

    def entry(name: str, kind: int, child: int, right: int, start: int, size: int) -> bytes:
        encoded = name.encode("utf-16-le") + b"\0\0"
        return (encoded.ljust(64, b"\0") + struct.pack("<HBB", len(encoded), kind, 1)
                + struct.pack("<III", no_stream, right, child) + b"\0" * 36 + struct.pack("<IQ", start, size))

    directory = entry("Root Entry", 5, 1 if names else no_stream, no_stream, end, 0)
    for index, name in enumerate(names):
        right = index + 2 if index + 1 < len(names) else no_stream
        directory += entry(name, 2, no_stream, right, starts[index], len(payloads[index]))
    header = (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 16 + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6)
              + b"\0" * 6 + struct.pack("<IIIIIIIII", 0, 1, 1, 0, 4096, end, 0, end, 0)
              + struct.pack("<I", 0) + struct.pack("<I", free) * 108)
    return header + struct.pack("<128I", *fat) + directory.ljust(512, b"\0") + b"".join(payloads)
