"""Courriels EML (bibliothèque standard) et MSG Outlook (python-oxmsg) -> Markdown.

E-mails, EML (standard library) and Outlook MSG (python-oxmsg) -> Markdown.
Seuls De, À, Cc, Date et Objet sont émis ; Received, Message-ID, DKIM, X-Originating-IP, Cci… sont
écartés (adresses IP, noms d'hôtes, minimisation). Corps : texte brut s'il existe, sinon HTML converti,
sinon RTF compressé (MSG). Les pièces jointes sont listées par type seulement, jamais ouvertes : leur nom porte
souvent celui d'une personne (« CV_Jean_Dupont.pdf »), que la détection ne verrait pas toujours. Les messages
chiffrés sont refusés.
Only From, To, Cc, Date and Subject are output; Received, Message-ID, DKIM, X-Originating-IP, Bcc... are
dropped. Body: plain text when present, else converted HTML, else compressed RTF (MSG). Attachments are
listed by type only, never opened: their file name often carries a person's name that detection would not always
see. Encrypted messages are rejected.
"""

from __future__ import annotations

import contextlib
import email
import email.header
import struct
from collections.abc import Iterator
from email import policy
from email.message import Message
from typing import Any

from ..documents import ConvertedDocument, DocumentOptions
from ._base import Report, Source, corrupt, encrypted, output_limit, too_large, unsupported
from ._encoding import decode_text
from ._html import decode_html, html_to_markdown
from ._markdown import attachment, bullet_list, inline, join_blocks, section

_LABELS = (("from", "De"), ("to", "À"), ("cc", "Cc"), ("date", "Date"), ("subject", "Objet"))
_MAX_PARTS = 1000
_MAX_DEPTH = 32


def convert(source: Source, options: DocumentOptions) -> ConvertedDocument:
    return _convert_msg(source.data, options) if source.kind == "msg" else _convert_eml(source.data, options)


def _assemble(report: Report, kind: str, headers: dict[str, str], body: str, attachments: list[str]
              ) -> ConvertedDocument:
    lines = [f"{label} : {headers[key]}" for key, label in _LABELS if headers.get(key)]
    report.drop("attachments", len(attachments))
    return report.document(join_blocks([bullet_list(lines), body, section("Pièces jointes", bullet_list(attachments))]),
                           kind)


# --- EML ---------------------------------------------------------------------------------------------


def _convert_eml(data: bytes, options: DocumentOptions) -> ConvertedDocument:
    report = Report()
    message = email.message_from_bytes(data, policy=policy.default)
    content_type = message.get_content_type()
    if content_type == "multipart/encrypted" or content_type.endswith("pkcs7-mime"):
        if (message.get_param("smime-type") or "").lower() == "signed-data":
            raise unsupported("message S/MIME signé opaque", "opaque S/MIME signed message")
        raise encrypted()
    headers: dict[str, str] = {}
    for key, _label in _LABELS:
        value = _eml_header(message, key)
        if value:
            headers[key] = value
    report.drop("email_headers", sum(1 for name in message if name.lower() not in headers))
    plain: list[str] = []
    html: list[str] = []
    attachments: list[str] = []
    for part in _leaves(message, 0):
        kind = part.get_content_type()
        attached = part.get_content_disposition() == "attachment" or _filename(part)
        if not attached and kind == "text/plain":
            plain.append(_part_text(part))
        elif not attached and kind == "text/html":
            html.append(_part_text(part))
        else:
            attachments.append(attachment(len(attachments) + 1, kind))
        if len(attachments) + len(plain) + len(html) >= _MAX_PARTS:
            report.warn("Courriel tronqué : trop de parties / e-mail truncated: too many parts")
            break
    if any(text.strip() for text in plain):
        body = "\n\n".join(plain)
    else:
        body = "\n\n".join(html_to_markdown(text, options, report) for text in html)
    return _assemble(report, "eml", headers, body, attachments)


def _eml_header(message: Message, key: str) -> str:
    try:
        values = message.get_all(key) or []
        if key == "date" and values:
            moment = getattr(values[0], "datetime", None)
            if moment is not None:
                return moment.isoformat(timespec="minutes")
        # Jamais tronqué : une adresse coupée (« jean.dupont@exem ») échapperait à la détection ; la taille
        # reste bornée par celle du message. Never truncated: a cut address would escape detection.
        return inline(", ".join(str(value) for value in values))
    except Exception:  # en-tête malformé : ignoré / malformed header: ignored
        return ""


def _leaves(part: Message, depth: int) -> Iterator[Message]:
    """Parties terminales ; un message joint (message/rfc822) n'est pas ouvert / attached messages stay closed."""
    if depth <= _MAX_DEPTH and part.get_content_maintype() == "multipart" and part.is_multipart():
        for sub in part.get_payload():
            if isinstance(sub, Message):
                yield from _leaves(sub, depth + 1)
    else:
        yield part


def _filename(part: Message) -> bool:
    """La partie porte-t-elle un nom de fichier ? (le nom n'est jamais émis) / does the part carry a file name?"""
    try:
        return bool(part.get_filename())
    except Exception:  # paramètre RFC 2231 malformé : traité comme une pièce jointe / malformed: an attachment
        return True


def _part_text(part: Message) -> str:
    """Décodage propre plutôt que `get_content()`, qui remplace en silence les octets d'un jeu absent ou faux.

    Own decoding rather than `get_content()`, which silently replaces bytes of a missing or wrong charset
    (U+FFFD in place of each accent: such names would escape detection).
    """
    payload = part.get_payload(decode=True)
    return decode_text(payload, part.get_content_charset()) if isinstance(payload, bytes) else ""


# --- MSG ---------------------------------------------------------------------------------------------

_PID_RECIPIENT_TYPE = 0x0C15
_PID_RTF_COMPRESSED = 0x1009
_PID_HTML = 0x1013
_RECIPIENT_KEYS = {1: "to", 2: "cc"}  # 3 : Cci, jamais émis / Bcc, never output


def _convert_msg(data: bytes, options: DocumentOptions) -> ConvertedDocument:
    from oxmsg import Message as OutlookMessage

    try:
        message = OutlookMessage.load(data)
        message_class = message.message_class.upper()
    except Exception:  # python-oxmsg lève des types variés / python-oxmsg raises assorted types
        raise corrupt("msg") from None
    if message_class.startswith("IPM.NOTE.SMIME") and "MULTIPARTSIGNED" not in message_class:
        raise encrypted()
    report = Report()
    transport = _safe(lambda: message.message_headers, {})
    headers: dict[str, str] = {}
    sender = _safe(lambda: message.sender, None)
    if sender:
        headers["from"] = _decoded(sender)
    for key in ("to", "cc"):
        value = next((v for k, v in transport.items() if k.lower() == key), "")
        if value:
            headers[key] = _decoded(value)
    missing = {key for key in ("to", "cc") if key not in headers}
    recipients: dict[str, list[str]] = {"to": [], "cc": []}
    hidden = 0
    for recipient in _safe(lambda: message.recipients, ()):
        key = _RECIPIENT_KEYS.get(_safe(lambda r=recipient: r.properties.int_prop_value(_PID_RECIPIENT_TYPE), 1))
        if key is None:
            hidden += 1
        elif key in missing:
            recipients[key].append(_recipient(recipient))
    for key in missing:
        if recipients[key]:
            headers[key] = ", ".join(filter(None, recipients[key]))
    sent = _safe(lambda: message.sent_date, None)
    if sent is not None:
        headers["date"] = sent.isoformat(timespec="minutes")
    subject = _safe(lambda: message.subject, "")
    if subject:
        headers["subject"] = inline(subject)
    report.drop("email_headers", hidden + sum(1 for name in transport if name.lower() not in headers))
    attachments = []
    for item in _safe(lambda: message.attachments, ()):
        kind = _safe(lambda a=item: a.mime_type, None)
        attachments.append(attachment(len(attachments) + 1, kind if isinstance(kind, str) else None))
    return _assemble(report, "msg", headers, _msg_body(message, options, report), attachments)


def _msg_body(message: Any, options: DocumentOptions, report: Report) -> str:
    body = _safe(lambda: message.body, None)
    if body and body.strip():
        return body
    # HTML lu en octets et décodé avec tolérance : `html_body` lève sur un seul octet invalide.
    # HTML read as bytes and decoded leniently: `html_body` raises on a single invalid byte.
    raw_html = _safe(lambda: message.properties.binary_prop_value(_PID_HTML), None)
    if raw_html:
        html = decode_html(raw_html, _safe(lambda: message.properties.body_encoding, None))
    else:
        html = _safe(lambda: message.html_body, None)
    if html and html.strip():
        return html_to_markdown(html, options, report)
    compressed = _safe(lambda: message.properties.binary_prop_value(_PID_RTF_COMPRESSED), None)
    if compressed:
        from ._rtf import rtf_to_markdown

        return rtf_to_markdown(decompress_rtf(compressed, output_limit(options)), options, report)
    return ""


def _recipient(recipient: Any) -> str:
    name = inline(_safe(lambda: recipient.name, "") or "")
    address = inline(_safe(lambda: recipient.email_address, "") or "")
    if name and address and name != address:
        return f"{name} <{address}>"
    return name or address


def _decoded(value: str) -> str:
    """En-tête RFC 2047 décodé (« =?utf-8?q?...?= ») / decoded RFC 2047 header."""
    with contextlib.suppress(Exception):  # encodage invalide : valeur brute / invalid encoding: raw value
        value = str(email.header.make_header(email.header.decode_header(value)))
    return inline(value)


def _safe(getter: Any, default: Any) -> Any:
    """python-oxmsg 0.0.2 peut lever (assert, KeyError) sur un champ abîmé / may raise on a damaged field."""
    try:
        value = getter()
    except Exception:
        return default
    return default if value is None else value


# --- RTF compressé (MS-OXRTFCP) / compressed RTF ------------------------------------------------------

_RTF_PREBUF = (b"{\\rtf1\\ansi\\mac\\deff0\\deftab720{\\fonttbl;}{\\f0\\fnil \\froman \\fswiss \\fmodern \\fscript "
               b"\\fdecor MS Sans SerifSymbolArialTimes New RomanCourier{\\colortbl\\red0\\green0\\blue0\r\n\\par "
               b"\\pard\\plain\\f0\\fs20\\b\\i\\u\\tab\\tx")
_LZFU, _MELA = 0x75465A4C, 0x414C454D


def decompress_rtf(blob: bytes, limit: int) -> bytes:
    """Décompresse le RTF « LZFu » des MSG (spécification publique MS-OXRTFCP) / decompresses MSG LZFu RTF."""
    if len(blob) < 16:
        raise corrupt("msg")
    compressed_size, raw_size, magic, _crc = struct.unpack_from("<IIII", blob)
    if raw_size > limit:
        raise too_large("corps RTF (octets)", "RTF body (bytes)", limit)
    if magic == _MELA:
        return blob[16:16 + raw_size]
    if magic != _LZFU:
        raise corrupt("msg")
    out = _lzfu(blob, min(len(blob), compressed_size + 4), limit)
    if len(out) > limit:
        raise too_large("corps RTF (octets)", "RTF body (bytes)", limit)
    return bytes(out)


def _lzfu(blob: bytes, end: int, limit: int) -> bytearray:
    """Boucle LZ77 ; copies en bloc sauf chevauchement / LZ77 loop; block copies unless overlapping."""
    window = bytearray(4096)
    window[:len(_RTF_PREBUF)] = _RTF_PREBUF
    write = len(_RTF_PREBUF)
    out = bytearray()
    pos = 16
    while pos < end and len(out) <= limit:
        control = blob[pos]
        pos += 1
        if control == 0 and pos + 8 <= end and write <= 4088:
            # Huit littéraux sans retour au début de la fenêtre / eight literals, no window wrap.
            out += blob[pos:pos + 8]
            window[write:write + 8] = blob[pos:pos + 8]
            pos += 8
            write = (write + 8) & 0xFFF
            continue
        for bit in range(8):
            if pos >= end:
                break
            if not control >> bit & 1:  # littéral / literal
                out.append(blob[pos])
                window[write] = blob[pos]
                pos += 1
                write = (write + 1) & 0xFFF
                continue
            if pos + 1 >= end:  # référence tronquée / truncated reference
                return out
            token = blob[pos] << 8 | blob[pos + 1]  # décalage 12 bits, longueur 4 bits / 12-bit offset, 4-bit length
            pos += 2
            offset, length = token >> 4, (token & 0xF) + 2
            if offset == write:  # marqueur de fin / end marker
                return out
            if (offset + length <= write or write + length <= offset) and max(offset, write) + length <= 4096:
                piece = window[offset:offset + length]  # zones disjointes / disjoint ranges
                out += piece
                window[write:write + length] = piece
                write = (write + length) & 0xFFF
                continue
            for _ in range(length):  # copie chevauchante (répétition) / overlapping copy (run)
                byte = window[offset]
                window[write] = byte
                out.append(byte)
                write = (write + 1) & 0xFFF
                offset = (offset + 1) & 0xFFF
    return out


__all__ = ["convert", "decompress_rtf"]
