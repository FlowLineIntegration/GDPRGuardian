"""Minimisation des noms de fichiers : seule l'extension est gardée / file-name minimisation: only the extension stays.

Un nom de fichier porte souvent des données personnelles (« CV_Jean_Dupont.pdf ») que le moteur ne repère
pas toujours ; il ne sert qu'à choisir le format. A file name often carries personal data that the
engine does not always catch; it is only needed to pick the format.
"""

from __future__ import annotations

import re

NEUTRAL_STEM = "document"
_EXTENSION_RE = re.compile(r"[A-Za-z0-9]{1,10}")


def neutral_filename(filename: str) -> str:
    """« document » suivi de l'extension d'origine si elle est sûre / "document" plus the original safe extension.

    >>> neutral_filename("C:\\\\RH\\\\CV_Jean_Dupont.PDF")
    'document.pdf'
    """
    # Dernier composant, sans points ni espaces finaux (ignorés par Windows) / last component, Windows-trimmed.
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip().rstrip(". ")
    _, dot, extension = name.rpartition(".")
    if dot and _EXTENSION_RE.fullmatch(extension):
        return f"{NEUTRAL_STEM}.{extension.lower()}"
    return NEUTRAL_STEM
