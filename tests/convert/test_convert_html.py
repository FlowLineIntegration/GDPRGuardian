"""Convertisseur HTML (bs4 + markdownify) / HTML converter."""

from __future__ import annotations

import dataclasses
import socket

import pytest
from convert_samples import AUTHOR, EMAIL, HTML, IBAN, NIR, PHONE

from gdprguardian.convert import to_markdown
from gdprguardian.documents import DocumentOptions

LOCAL = DocumentOptions(sandbox=False)


def convert(html: str | bytes, **options: object):
    data = html.encode("utf-8") if isinstance(html, str) else html
    return to_markdown(data, "page.html", dataclasses.replace(LOCAL, **options))


def test_structure_tables_and_lists() -> None:
    markdown = convert(HTML).markdown
    assert markdown.startswith("# Contrat\n\nSalarié : Jean Dupont, NIR " + NIR)
    assert f"| Nom\\|Prénom | IBAN |\n| --- | --- |\n| Dupont | {IBAN} |" in markdown
    assert "- un\n- deux **gras**" in markdown


def test_active_content_and_metadata_are_removed_with_their_text() -> None:
    result = convert(HTML)
    markdown = result.markdown
    for absent in ("SCRIPT-SECRET", "color: red", AUTHOR, "commentaire caché", "evil.example", "tracker.example",
                   "<", "data:", "base64"):
        assert absent not in markdown
    assert result.dropped["scripts"] == 1 and result.dropped["embedded_objects"] == 1
    assert result.dropped["metadata"] == 2 and result.dropped["comments"] == 1


def test_links_keep_text_drop_targets() -> None:
    result = convert(HTML)
    assert "écrire, tél. " + PHONE in result.markdown
    assert EMAIL not in result.markdown  # seulement présent dans le mailto / only in the mailto target
    assert result.dropped["links"] == 1


def test_images_become_placeholders() -> None:
    result = convert(HTML)
    assert "[IMAGE: Logo ACME]" in result.markdown and "[IMAGE]" in result.markdown
    assert result.dropped["images"] == 2


def test_underscores_and_dashes_are_not_escaped() -> None:
    markdown = convert(HTML).markdown
    assert "jean_dupont_secours@exemple.fr" in markdown
    assert "06-12-34-56-78" in convert("<p>tél 06-12-34-56-78</p>").markdown


def test_hidden_elements_follow_option() -> None:
    default = convert(HTML)
    assert "TEXTE-MASQUE" not in default.markdown and "AUSSI-MASQUE" not in default.markdown
    assert default.dropped["hidden_content"] == 2
    shown = convert(HTML, include_hidden=True)
    assert "TEXTE-MASQUE" in shown.markdown and "AUSSI-MASQUE" in shown.markdown


def test_declared_legacy_charset() -> None:
    data = '<html><head><meta charset="iso-8859-1"></head><body><p>Élodie – 50 €</p></body></html>'
    assert convert(data.encode("cp1252")).markdown == "Élodie – 50 €"


def test_undeclared_cp1252_is_not_mistaken_for_cp1257() -> None:
    assert convert("<p>Café crème, déjà vu à l'été.</p>".encode("cp1252")).markdown == "Café crème, déjà vu à l'été."


def test_nothing_is_fetched(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("accès réseau / network access")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    remote = ('<html><head><link rel="stylesheet" href="https://evil.example/a.css"><base href="https://evil.example/">'
              '</head><body><img src="https://evil.example/p.gif"><iframe src="https://evil.example/"></iframe>'
              '<object data="https://evil.example/o"></object><p>Texte</p></body></html>')
    assert convert(remote).markdown == "[IMAGE]\n\nTexte"


def test_too_many_tags_are_refused_before_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arbre de BeautifulSoup borné : au-delà de MAX_TAGS « < », refus avant d'allouer (le courriel HTML et le
    # DOCX passent par la même fonction). Bounded BeautifulSoup tree: beyond MAX_TAGS "<", refused before allocating
    # (HTML e-mails and DOCX go through the same function).
    from gdprguardian.convert import _html
    from gdprguardian.documents import DocumentTooLargeError

    assert _html.MAX_TAGS == 1_000_000  # publié dans deploy/README.md et sur le site / published
    monkeypatch.setattr(_html, "MAX_TAGS", 40)
    table = "<table>" + "<tr><td>Jean</td></tr>" * 9 + "</table>"  # 2 + 9 × 4 = 38 balises / tags
    assert "Jean" in convert(table + "<p>x</p>").markdown  # 40 : admis / admitted
    with pytest.raises(DocumentTooLargeError, match="HTML tags > 40"):
        convert(table + "<p>x</p><p>y</p>")  # 42
    # Un « < » isolé du texte n'est pas une balise / a lone "<" in the text is not a tag.
    assert "1 < 2 < 3 < 4" in convert(table + "<p>1 < 2 < 3 < 4</p>").markdown


def test_deep_nesting_is_refused_with_its_limit_and_quickly() -> None:
    import time

    from gdprguardian.convert import _html
    from gdprguardian.documents import DocumentTooLargeError

    assert _html.MAX_DEPTH == 256  # publié dans deploy/README.md / published
    # html, body, puis les blocs / html, body, then the blocks.
    fits = "<div>" * (_html.MAX_DEPTH - 2) + "Jean Dupont" + "</div>" * (_html.MAX_DEPTH - 2)
    assert convert(fits).markdown == "Jean Dupont"
    started = time.perf_counter()
    with pytest.raises(DocumentTooLargeError, match="HTML nesting levels > 256"):
        convert("<div>" * 50_000 + "Jean Dupont" + "</div>" * 50_000)
    assert time.perf_counter() - started < 10  # avant : quadratique, plus d'une minute / before: over a minute


def test_cleanup_stays_linear_on_nested_markup() -> None:
    # Retraits imbriqués : le contenu d'un élément retiré n'est ni compté ni visité deux fois.
    # Nested removals: the content of a removed element is neither counted nor visited twice.
    result = convert("<div hidden><script>x</script><div><script>y</script></div></div><p>Texte</p>")
    assert result.markdown == "Texte" and result.dropped == {"hidden_content": 1}
