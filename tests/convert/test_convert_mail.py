"""Courriels EML et MSG, RTF compressé / EML and MSG e-mails, compressed RTF."""

from __future__ import annotations

import dataclasses
import struct
import time
from email.message import EmailMessage

import pytest
from convert_samples import EMAIL, IBAN, NIR, PHONE, lzfu_literal, make_cfb, make_eml, make_msg
from hypothesis import given, settings
from hypothesis import strategies as st

from gdprguardian.convert import _mail, to_markdown
from gdprguardian.convert._mail import decompress_rtf
from gdprguardian.documents import DocumentError, DocumentOptions, EncryptedDocumentError, UnsupportedFormatError

LOCAL = DocumentOptions(sandbox=False)
HEADERS = (f"- De : Jean Dupont <{EMAIL}>\n- À : Marie Martin <marie.martin@exemple.fr>\n- Cc : rh@exemple.fr\n"
           f"- Date : 2026-10-24T10:00+02:00\n- Objet : Dossier NIR {NIR}")


def convert(data: bytes, name: str = "message.eml", **options: object):
    return to_markdown(data, name, dataclasses.replace(LOCAL, **options))


def test_eml_keeps_only_the_useful_headers() -> None:
    result = convert(make_eml())
    assert result.markdown.startswith(HEADERS)
    for absent in ("cache@exemple.fr", "192.168.1.42", "abc@mail.example", "mx.example"):
        assert absent not in result.markdown  # Cci, IP, Message-ID, Received
    assert result.dropped["email_headers"] >= 4


def test_eml_plain_body_and_attachments() -> None:
    result = convert(make_eml(html=True))
    assert f"mon IBAN est {IBAN}.\nTél. {PHONE}" in result.markdown
    assert "Version" not in result.markdown  # texte brut préféré / plain text preferred
    # Numéro et type, jamais le nom de fichier (souvent celui d'une personne) / number and type, never the name.
    assert result.markdown.endswith("## Pièces jointes\n\n- Pièce jointe 1 (application/pdf)")
    assert "bulletin-dupont" not in result.markdown
    assert "fake" not in result.markdown and result.dropped["attachments"] == 1


def test_eml_html_only_body_is_cleaned() -> None:
    markdown = convert(make_eml(html=True, plain=False)).markdown
    assert f"Version **HTML** : IBAN {IBAN}" in markdown and "x()" not in markdown


def test_eml_encoded_words_and_bad_charset() -> None:
    raw = ("From: =?utf-8?q?J=C3=A9r=C3=B4me?= <j@x.fr>\r\nSubject: =?iso-8859-1?q?R=E9sum=E9?=\r\n"
           "Content-Type: text/plain; charset=unknown-xyz\r\n\r\nCaf\xe9 cr\xe8me\r\n").encode("latin-1")
    markdown = convert(raw).markdown
    assert "- De : Jérôme <j@x.fr>" in markdown and "- Objet : Résumé" in markdown
    assert "Café crème" in markdown


@pytest.mark.parametrize("content_type", ["text/plain", "text/plain; charset=us-ascii", "text/plain; charset=utf-8"])
def test_eml_body_with_missing_or_wrong_charset_is_not_garbled(content_type: str) -> None:
    # Le module email remplacerait les accents par U+FFFD : « Jérôme » échapperait à la détection.
    # The email module would replace accents with U+FFFD: "Jérôme" would escape detection.
    raw = f"From: a@b.fr\r\nSubject: x\r\nContent-Type: {content_type}\r\n\r\nJérôme Dupont, née à Évry\r\n"
    assert "Jérôme Dupont, née à Évry" in convert(raw.encode("cp1252")).markdown


def test_eml_attached_message_is_listed_not_opened() -> None:
    inner = EmailMessage()
    inner["Subject"] = "Secret interne"
    inner.set_content("CONTENU-INTERNE")
    outer = EmailMessage()
    outer["From"] = "a@b.fr"
    outer["Subject"] = "Transfert"
    outer.set_content("Voir pièce jointe")
    outer.add_attachment(inner)
    markdown = convert(outer.as_bytes()).markdown
    assert "CONTENU-INTERNE" not in markdown
    assert "- Pièce jointe 1 (message/rfc822)" in markdown


def test_attachment_names_never_reach_the_output() -> None:
    # « CV_Jean_Dupont.pdf » : un nom de personne que la détection ne verrait pas / a name detection would miss.
    message = EmailMessage()
    message["From"] = "a@b.fr"
    message["Subject"] = "Candidature"
    message.set_content("Voir les pièces jointes.")
    message.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename="CV_Jean_Dupont.pdf")
    message.add_attachment(b"x", maintype="application", subtype="octet-stream", filename="bulletin_paie_jdupont")
    markdown = convert(message.as_bytes()).markdown
    assert "dupont" not in markdown.lower() and "jean" not in markdown.lower()
    assert markdown.endswith("- Pièce jointe 1 (application/pdf)\n- Pièce jointe 2 (application/octet-stream)")


@pytest.mark.parametrize(("content_type", "error"), [
    ('application/pkcs7-mime; smime-type=enveloped-data; name="smime.p7m"', EncryptedDocumentError),
    ('multipart/encrypted; protocol="application/pgp-encrypted"; boundary="b"', EncryptedDocumentError),
    ('application/pkcs7-mime; smime-type=signed-data; name="smime.p7m"', UnsupportedFormatError),
])
def test_encrypted_eml(content_type: str, error: type[Exception]) -> None:
    raw = f"From: a@b.fr\r\nSubject: x\r\nMIME-Version: 1.0\r\nContent-Type: {content_type}\r\n\r\nMIIB\r\n"
    with pytest.raises(error):
        convert(raw.encode())


def test_msg_headers_body_and_attachments() -> None:
    result = convert(make_msg(body=f"Corps : IBAN {IBAN}"), "message.msg")
    assert result.kind == "msg"
    assert result.markdown.startswith(f"- De : Jean Dupont <{EMAIL}>\n- À : Marie Martin <marie.martin@exemple.fr>\n"
                                      "- Date : ")
    assert f"- Objet : Dossier NIR {NIR}\n\nCorps : IBAN {IBAN}" in result.markdown
    assert "- Pièce jointe 1 (application/pdf)" in result.markdown and "bulletin-dupont" not in result.markdown
    assert "cache@exemple.fr" not in result.markdown and "10.0.0.1" not in result.markdown
    assert result.dropped["email_headers"] >= 2


def test_msg_html_and_compressed_rtf_bodies() -> None:
    html = convert(make_msg(html=b"<p>Corps <b>HTML</b></p><script>x()</script>"), "m.msg").markdown
    assert "Corps **HTML**" in html and "x()" not in html
    rtf = convert(make_msg(rtf=b"{\\rtf1\\ansi Corps RTF compress\\'e9 " + IBAN.encode() + b"\\par}"), "m.msg")
    assert f"Corps RTF compressé {IBAN}" in rtf.markdown


def test_msg_smime_is_encrypted() -> None:
    with pytest.raises(EncryptedDocumentError):
        convert(make_msg(body="x", message_class="IPM.Note.SMIME"), "m.msg")


def test_damaged_msg() -> None:
    with pytest.raises(DocumentError, match="OLE"):
        convert(make_msg(body="x")[:1536], "m.msg")  # conteneur tronqué / truncated container
    # Propriétés illisibles : conversion vide mais sans plantage / unreadable properties: empty, no crash.
    empty = convert(make_cfb({"__properties_version1.0": b"\0" * 8, "__substg1.0_0037001F": b"\xff"}), "m.msg")
    assert empty.kind == "msg" and empty.markdown == ""


def test_compressed_rtf_matches_the_specification_examples() -> None:
    # Exemples 1 et 2 de [MS-OXRTFCP] §3.1 : références au dictionnaire initial et copies chevauchantes.
    # [MS-OXRTFCP] examples 1 and 2: references into the initial dictionary and overlapping copies.
    first = bytes.fromhex("2d0000002b0000004c5a4675f1c5c7a703000a007263706731323542320af32068656c0900206277"
                          "05b06c647d0a800fa0")
    assert decompress_rtf(first, 1 << 20) == b"{\\rtf1\\ansi\\ansicpg1252\\pard hello world}\r\n"
    second = bytes.fromhex("1a0000001c0000004c5a4675e2d44b51410004205758595a0d6e7d010eb0")
    assert decompress_rtf(second, 1 << 20) == b"{\\rtf1 WXYZWXYZWXYZWXYZWXYZ}"
    assert decompress_rtf(lzfu_literal(b"{\\rtf1 abcdefgh}"), 1 << 20) == b"{\\rtf1 abcdefgh}"


def test_mbox_envelope_line_is_still_an_email() -> None:
    # Sinon pris pour du texte brut : Cci, Received et adresses IP partaient tels quels.
    # Otherwise read as plain text: Bcc, Received and IP addresses went out verbatim.
    raw = b"From jean@exemple.fr Sat Oct 24 10:00:00 2026\n" + make_eml()
    result = convert(raw)
    assert result.kind == "eml" and result.markdown.startswith(HEADERS)
    assert "cache@exemple.fr" not in result.markdown and "192.168.1.42" not in result.markdown


def test_long_recipient_lists_are_never_cut_inside_an_address() -> None:
    # Tronqué à 2000 caractères, l'en-tête finissait par « personne.numero33@entreprise-exe » : non détectable.
    # Cut at 2000 characters, the header ended with a partial, undetectable address.
    addresses = [f"personne.numero{i}@entreprise-exemple.fr" for i in range(80)]
    raw = f"From: a@b.fr\r\nTo: {', '.join(addresses)}\r\nSubject: {'mot ' * 900}\r\n\r\nCorps\r\n".encode()
    markdown = convert(raw).markdown
    assert all(address in markdown for address in addresses)
    assert markdown.count("mot") == 900


def test_msg_html_body_with_a_stray_byte_is_still_read() -> None:
    # python-oxmsg lève sur un seul octet invalide : le corps était perdu / raised on one invalid byte.
    html = "<p>Café de Jérôme Dupont</p>".encode() + b"\xff"
    markdown = convert(make_msg(html=html, codepage=65001), "m.msg").markdown
    assert "Café de Jérôme Dupont" in markdown


def _reference_lzfu(blob: bytes) -> bytes:
    """Décompresseur de référence, octet par octet / byte-by-byte reference decompressor (MS-OXRTFCP)."""
    window = bytearray(4096)
    prebuf = _mail._RTF_PREBUF
    window[:len(prebuf)] = prebuf
    write, out, pos, end = len(prebuf), bytearray(), 16, len(blob)
    while pos < end:
        control = blob[pos]
        pos += 1
        for bit in range(8):
            if pos >= end:
                break
            if control >> bit & 1:
                if pos + 1 >= end:
                    return bytes(out)
                token = blob[pos] << 8 | blob[pos + 1]
                pos += 2
                offset, length = token >> 4, (token & 0xF) + 2
                if offset == write:
                    return bytes(out)
                for _ in range(length):
                    out.append(window[offset])
                    window[write] = window[offset]
                    write, offset = (write + 1) & 0xFFF, (offset + 1) & 0xFFF
            else:
                out.append(blob[pos])
                window[write] = blob[pos]
                write, pos = (write + 1) & 0xFFF, pos + 1
    return bytes(out)


@settings(max_examples=300, deadline=None)
@given(st.binary(max_size=6000))
def test_compressed_rtf_block_copies_match_the_reference(stream: bytes) -> None:
    # Tout flux est valide (littéraux et références) : copies en bloc et fenêtre circulaire comparées.
    # Any stream is valid (literals and references): block copies and the circular window are compared.
    blob = struct.pack("<IIII", len(stream) + 12, 1 << 20, 0x75465A4C, 0) + stream
    assert decompress_rtf(blob, 1 << 20) == _reference_lzfu(blob)


def test_compressed_rtf_is_fast() -> None:
    rtf = b"{\\rtf1\\ansi " + b"Jean Dupont habite au 12 rue de la Paix. " * 50_000 + b"}"
    started = time.perf_counter()
    assert decompress_rtf(lzfu_literal(rtf), 1 << 30) == rtf
    assert time.perf_counter() - started < 2


def test_compressed_rtf_limits() -> None:
    with pytest.raises(DocumentError):
        decompress_rtf(b"short", 1 << 20)
    with pytest.raises(DocumentError):
        decompress_rtf(lzfu_literal(b"{\\rtf1 x}")[:8] + b"XXXX" + b"\0" * 8, 1 << 20)
    with pytest.raises(DocumentError, match="RTF"):
        decompress_rtf(lzfu_literal(b"{\\rtf1 " + b"x" * 5000 + b"}"), 1000)
