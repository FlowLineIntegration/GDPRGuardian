"""Minimisation des noms de fichiers / file-name minimisation."""

from __future__ import annotations

import pytest

from gdprguardian.server.filenames import neutral_filename


@pytest.mark.parametrize(("name", "expected"), [
    ("CV_Jean_Dupont.pdf", "document.pdf"),
    ("C:\\Users\\jdupont\\Bulletin_paie_DUPONT_2024.XLSX", "document.xlsx"),
    ("/home/jdupont/dossier.tar.gz", "document.gz"),
    ("contrat.pdf. ", "document.pdf"),          # points et espaces finaux ignorés par Windows
    (".csv", "document.csv"),                   # extension seule / extension only
    ("sans_extension", "document"),
    ("a.pdf:secret", "document"),               # flux NTFS / NTFS stream
    ("a.p df", "document"),
    ("a.verylongextension", "document"),
    ("a.é", "document"),
    ("", "document"),
    ("../../etc/passwd", "document"),
])
def test_only_a_safe_extension_survives(name: str, expected: str) -> None:
    assert neutral_filename(name) == expected
