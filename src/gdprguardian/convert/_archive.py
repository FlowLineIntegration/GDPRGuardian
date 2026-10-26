"""Garde ZIP et XML sûr pour OOXML et OpenDocument / ZIP guard and safe XML for OOXML and OpenDocument.

La garde s'exécute avant tout analyseur : nombre d'entrées, tailles et taux de compression déclarés
(zipfile refuse ensuite de lire au-delà), chemins, doublons, chiffrement, et aucune DTD dans les entrées.
The guard runs before any parser: member count, declared sizes and compression ratios (zipfile then
refuses to read past them), paths, duplicates, encryption, and no DTD in any member.
"""

from __future__ import annotations

import io
import posixpath
import re
import zipfile
import zlib
from dataclasses import dataclass
from typing import IO
from xml.etree.ElementTree import Element, ParseError

from defusedxml import ElementTree as SafeElementTree
from defusedxml.common import DefusedXmlException

from ._base import corrupt, encrypted, malicious


@dataclass(frozen=True, slots=True)
class ZipLimits:
    max_members: int = 5_000
    max_member_size: int = 256 << 20
    max_total_size: int = 1 << 30
    max_member_ratio: float = 250.0
    ratio_floor: int = 1 << 20  # taux contrôlé au-delà d'1 Mio (le XML court se compresse à 1000:1)
    max_archive_ratio: float = 100.0
    archive_ratio_floor: int = 64 << 20
    max_xml_size: int = 64 << 20  # le DOM pèse 10 fois le XML / the DOM weighs 10x the XML
    max_name_length: int = 512
    max_prolog: int = 1 << 20  # octets lus au plus avant l'élément racine / bytes read before the root


DEFAULT_LIMITS = ZipLimits()
_READ_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError, OSError, NotImplementedError, RuntimeError, ValueError)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class SafeArchive:
    """Archive ZIP vérifiée, lectures bornées / checked ZIP archive, bounded reads."""

    __slots__ = ("_by_lower", "_zip", "limits")

    def __init__(self, data: bytes, limits: ZipLimits = DEFAULT_LIMITS) -> None:
        self.limits = limits
        try:
            self._zip = zipfile.ZipFile(io.BytesIO(data))
            infos = self._zip.infolist()
        except _READ_ERRORS:
            raise corrupt("zip") from None
        self._by_lower: dict[str, zipfile.ZipInfo] = {}
        self._check(infos, len(data))

    def _check(self, infos: list[zipfile.ZipInfo], archive_size: int) -> None:
        limits = self.limits
        if len(infos) > limits.max_members:
            raise malicious("trop d'entrées dans l'archive", "too many archive members")
        total = 0
        for info in infos:
            name = info.filename
            parts = name.replace("\\", "/").split("/")
            if (len(name) > limits.max_name_length or "\x00" in name or name.startswith(("/", "\\"))
                    or ".." in parts or ":" in name[:3]):
                raise malicious("chemin d'entrée suspect", "suspicious member path")
            key = name.lower()
            if key in self._by_lower:
                raise malicious("entrée en double", "duplicate member")
            self._by_lower[key] = info
            if info.flag_bits & 0x1:
                raise encrypted()
            size = info.file_size
            if size > limits.max_member_size:
                raise malicious("entrée trop volumineuse une fois décompressée", "member too large when expanded")
            if size >= limits.ratio_floor and size > info.compress_size * limits.max_member_ratio:
                raise malicious("taux de compression anormal (bombe ZIP)", "abnormal compression ratio (zip bomb)")
            total += size
        if total > limits.max_total_size:
            raise malicious("archive trop volumineuse une fois décompressée", "archive too large when expanded")
        if total >= limits.archive_ratio_floor and total > archive_size * limits.max_archive_ratio:
            raise malicious("taux de compression anormal (bombe ZIP)", "abnormal compression ratio (zip bomb)")

    # --- lecture / reading ---

    @property
    def names(self) -> list[str]:
        return [info.filename for info in self._by_lower.values()]

    def info(self, name: str) -> zipfile.ZipInfo | None:
        """Les noms de parties OPC sont insensibles à la casse / OPC part names are case-insensitive."""
        return self._by_lower.get(name.lstrip("/").lower())

    def has(self, name: str) -> bool:
        return self.info(name) is not None

    def read(self, name: str, limit: int | None = None) -> bytes | None:
        """Contenu borné de l'entrée, ou None si absente / bounded member content, or None when absent."""
        info = self.info(name)
        if info is None:
            return None
        limit = self.limits.max_member_size if limit is None else limit
        try:
            with self._zip.open(info) as handle:
                blob = handle.read(limit + 1)
        except _READ_ERRORS:
            raise corrupt("zip") from None
        if len(blob) > limit:
            raise malicious("entrée trop volumineuse", "member too large")
        return blob

    def xml(self, name: str) -> Element | None:
        """Entrée XML analysée par defusedxml, sans DTD / XML member parsed by defusedxml, no DTD."""
        blob = self.read(name, self.limits.max_xml_size)
        return None if blob is None else parse_xml(blob)

    def check_xml_prologs(self) -> None:
        """Refuse toute DTD (bombe d'entités, XXE) avant que les bibliothèques tierces lisent l'archive.

        Rejects any DTD (entity bomb, XXE) before third-party libraries read the archive. Only the prolog
        is parsed: expat stops at the root element, so the cost is a few kilobytes per member.
        """
        for info in self._by_lower.values():
            if info.is_dir() or info.file_size == 0:
                continue
            try:
                with self._zip.open(info) as handle:
                    _probe_prolog(handle, self.limits.max_prolog)
            except _READ_ERRORS:
                raise corrupt("zip") from None


class _RootReached(Exception):
    pass


class _ProbeTarget:
    """Cible expat qui s'arrête à l'élément racine / expat target stopping at the root element."""

    def start(self, tag: str, attrib: dict[str, str]) -> None:
        raise _RootReached

    def end(self, tag: str) -> None:
        return None

    def data(self, data: str) -> None:
        return None

    def close(self) -> None:
        return None


def _probe_prolog(handle: IO[bytes], max_prolog: int) -> None:
    parser = SafeElementTree.DefusedXMLParser(target=_ProbeTarget(), forbid_dtd=True)
    fed = 0
    size = 4096
    while fed < max_prolog:
        chunk = handle.read(size)
        if not chunk:
            return
        fed += len(chunk)
        size = 65536
        try:
            parser.feed(chunk)
        except _RootReached:
            return
        except DefusedXmlException:
            raise malicious("DTD ou entités XML interdites", "forbidden XML DTD or entities") from None
        except (ParseError, UnicodeError):
            return  # pas du XML : les analyseurs le refuseront / not XML: parsers will reject it
        except (ValueError, LookupError):
            # Encodage déclaré inconnu d'expat (Shift_JIS, UTF-7...), mais peut-être lu par lxml : recherche
            # d'une DTD dans le texte décodé par Python. Declared encoding expat cannot read, lxml may: the
            # text decoded by Python is searched for a DTD instead.
            _scan_undecodable(chunk + handle.read(max_prolog - fed))
            return
    raise malicious("prologue XML anormal", "abnormal XML prolog")


_ENCODING_RE = re.compile(rb"""\s{0,64}<\?xml[^>]{0,256}?encoding\s{0,8}=\s{0,8}["']([A-Za-z0-9._:-]{1,40})""")
_DTD_RE = re.compile(r"<!\s{0,16}(?:doctype|entity)", re.IGNORECASE)


def _scan_undecodable(head: bytes) -> None:
    match = _ENCODING_RE.match(head)
    try:
        text = head.decode(match.group(1).decode("ascii") if match else "utf-8", errors="replace")
    except LookupError:  # inconnu de Python aussi, ou codec non textuel / unknown to Python too, or non-text
        raise corrupt("zip") from None
    if _DTD_RE.search(text) is not None:
        raise malicious("DTD ou entités XML interdites", "forbidden XML DTD or entities")


def parse_xml(blob: bytes, kind: str = "zip") -> Element:
    """XML via defusedxml, DTD interdite / XML through defusedxml, DTD forbidden."""
    try:
        return SafeElementTree.fromstring(blob, forbid_dtd=True)
    except DefusedXmlException:
        raise malicious("DTD ou entités XML interdites", "forbidden XML DTD or entities") from None
    except (ParseError, ValueError, UnicodeError):
        raise corrupt(kind) from None


# --- OOXML ------------------------------------------------------------------------------------------

_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


@dataclass(frozen=True, slots=True)
class Relationship:
    type: str  # dernier segment de l'URI de type, ex. « header » / last segment of the type URI
    target: str  # nom de partie résolu, sans « / » initial / resolved part name, no leading slash
    external: bool


def relationships(archive: SafeArchive, part: str) -> list[Relationship]:
    """Relations d'une partie OPC (« » pour le paquet) / relationships of an OPC part ("" for the package)."""
    directory, name = posixpath.split(part)
    root = archive.xml(posixpath.join(directory, "_rels", f"{name}.rels"))
    if root is None:
        return []
    found: list[Relationship] = []
    for rel in root.iter(f"{_REL_NS}Relationship"):
        target = rel.get("Target", "")
        external = rel.get("TargetMode") == "External"
        if not external:
            base = "/" if target.startswith("/") else f"/{directory}"
            target = posixpath.normpath(posixpath.join(base, target)).lstrip("/")
        found.append(Relationship(rel.get("Type", "").rsplit("/", 1)[-1], target, external))
    return found


def main_part(archive: SafeArchive, default: str) -> str:
    for rel in relationships(archive, ""):
        if rel.type == "officeDocument" and not rel.external and archive.has(rel.target):
            return rel.target
    return default


_APP_PERSONAL = frozenset({"Company", "Manager", "HyperlinkBase"})


def ooxml_metadata_count(archive: SafeArchive) -> int:
    """Champs de métadonnées non vides, jamais émis (docProps) / non-empty metadata fields, never output."""
    count = 0
    for rel in relationships(archive, ""):
        if rel.external or rel.type not in ("core-properties", "extended-properties", "custom-properties"):
            continue
        root = archive.xml(rel.target)
        if root is None:
            continue
        if rel.type == "custom-properties":
            count += sum(1 for el in root if local_name(el.tag) == "property")
        elif rel.type == "extended-properties":
            count += sum(1 for el in root if local_name(el.tag) in _APP_PERSONAL and (el.text or "").strip())
        else:
            count += sum(1 for el in root if (el.text or "").strip())
    return count


def odf_metadata_count(archive: SafeArchive) -> int:
    root = archive.xml("meta.xml")
    return 0 if root is None else odf_meta_fields(root)


def odf_meta_fields(root: Element) -> int:
    """Champs non vides sous office:meta / non-empty fields under office:meta."""
    count = 0
    for meta in root.iter("{urn:oasis:names:tc:opendocument:xmlns:office:1.0}meta"):
        count += sum(1 for el in meta if (el.text or "").strip() or local_name(el.tag) == "user-defined")
    return count


__all__ = ["DEFAULT_LIMITS", "Relationship", "SafeArchive", "ZipLimits", "local_name", "main_part",
           "odf_meta_fields", "odf_metadata_count", "ooxml_metadata_count", "parse_xml", "relationships"]
