"""Lecture multipart en mémoire, bornée / bounded in-memory multipart reader.

Starlette déverse les fichiers de plus de 1 Mo dans un fichier temporaire sur disque ; ce lecteur garde
tout en mémoire et applique des limites strictes (un seul fichier, champs courts et peu nombreux).
Starlette spills files over 1 MB to a temporary file on disk; this reader keeps everything in memory
and enforces hard limits (one file, few short fields).
"""

from __future__ import annotations

from collections.abc import AsyncIterable
from dataclasses import dataclass, field

from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header

from .errors import InvalidRequest, PayloadTooLarge, file_too_large
from .filenames import neutral_filename

_MAX_FIELDS = 8
_MAX_FIELD_BYTES = 1024
_MAX_RULES_BYTES = 64 * 1024  # champ « rules » : jeu de règles en JSON / rule set as JSON
_MAX_HEADER_BYTES = 4096


@dataclass(slots=True)
class MultipartForm:
    fields: dict[str, str] = field(default_factory=dict)
    filename: str | None = field(default=None, repr=False)
    data: bytes | bytearray = field(default=b"", repr=False)


class _Collector:
    """Rappels du parseur : un fichier (`file_field`) et des champs texte / parser callbacks."""

    def __init__(self, file_field: str, max_file_bytes: int) -> None:
        self.file_field = file_field
        self.max_file_bytes = max_file_bytes
        self.form = MultipartForm()
        self._file = bytearray()
        self._header_name = bytearray()
        self._header_value = bytearray()
        self._headers_bytes = 0
        self._disposition = b""
        self._name: str | None = None
        self._is_file = False
        self._buffer = bytearray()
        self._seen_file = False

    def callbacks(self) -> dict[str, object]:
        return {
            "on_part_begin": self._part_begin, "on_part_data": self._part_data, "on_part_end": self._part_end,
            "on_header_field": self._header_field, "on_header_value": self._header_value_cb,
            "on_header_end": self._header_end, "on_headers_finished": self._headers_finished,
        }

    def _part_begin(self) -> None:
        self._disposition = b""
        self._name = None
        self._is_file = False
        self._buffer = bytearray()

    def _header_field(self, data: bytes, start: int, end: int) -> None:
        self._grow_headers(end - start)
        self._header_name += data[start:end]

    def _header_value_cb(self, data: bytes, start: int, end: int) -> None:
        self._grow_headers(end - start)
        self._header_value += data[start:end]

    def _grow_headers(self, size: int) -> None:
        self._headers_bytes += size
        if self._headers_bytes > _MAX_HEADER_BYTES * _MAX_FIELDS:
            raise InvalidRequest("En-têtes multipart trop longs / multipart headers too long")

    def _header_end(self) -> None:
        if bytes(self._header_name).lower() == b"content-disposition":
            self._disposition = bytes(self._header_value)
        self._header_name.clear()
        self._header_value.clear()

    def _headers_finished(self) -> None:
        _, options = parse_options_header(self._disposition)
        name = options.get(b"name")
        if name is None:
            raise InvalidRequest("Partie multipart sans nom / multipart part without a name")
        self._name = name.decode("utf-8", "replace")
        self._is_file = b"filename" in options
        if self._is_file:
            if self._name != self.file_field or self._seen_file:
                raise InvalidRequest(f"Un seul fichier, champ « {self.file_field} » / one file, field "
                                     f"'{self.file_field}'")
            self._seen_file = True
            # Neutralisé dès la lecture : le nom complet ne survit pas au rappel / neutralised at parse time.
            self.form.filename = neutral_filename(options[b"filename"].decode("utf-8", "replace"))
        elif len(self.form.fields) >= _MAX_FIELDS:
            raise InvalidRequest("Trop de champs / too many fields")

    def _part_data(self, data: bytes, start: int, end: int) -> None:
        if self._is_file:
            if len(self._file) + (end - start) > self.max_file_bytes:
                raise file_too_large(self.max_file_bytes)
            self._file += data[start:end]
        else:
            limit = _MAX_RULES_BYTES if self._name == "rules" else _MAX_FIELD_BYTES
            if len(self._buffer) + (end - start) > limit:
                raise InvalidRequest("Champ trop long / field too long")
            self._buffer += data[start:end]

    def _part_end(self) -> None:
        if not self._is_file and self._name is not None:
            self.form.fields[self._name] = self._buffer.decode("utf-8", "replace")

    def finish(self) -> MultipartForm:
        # Le tampon est transmis tel quel : pas de seconde copie du fichier / handed over, no second copy.
        self.form.data, self._file = self._file, bytearray()
        return self.form


async def read_multipart(content_type: str | None, stream: AsyncIterable[bytes], *, max_file_bytes: int,
                         file_field: str = "file") -> MultipartForm:
    """Analyse un corps multipart/form-data en flux / parses a multipart/form-data body as a stream."""
    media_type, params = parse_options_header(content_type or "")
    boundary = params.get(b"boundary")
    if media_type != b"multipart/form-data" or not boundary:
        raise InvalidRequest("multipart/form-data attendu / expected multipart/form-data")
    collector = _Collector(file_field, max_file_bytes)
    try:
        parser = MultipartParser(boundary, collector.callbacks())  # type: ignore[arg-type]
        async for chunk in stream:
            parser.write(chunk)
        parser.finalize()
    except (InvalidRequest, PayloadTooLarge):
        raise
    except ValueError:
        # FormParserError hérite de ValueError ; message ignoré / message discarded.
        raise InvalidRequest("Corps multipart mal formé / malformed multipart body") from None
    form = collector.finish()
    if form.filename is None:
        raise InvalidRequest(f"Champ fichier « {file_field} » manquant / missing file field '{file_field}'")
    return form
