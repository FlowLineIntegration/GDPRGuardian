"""Aiguillage vers les convertisseurs (dans le bac à sable) / dispatch to converters (inside the sandbox)."""

from __future__ import annotations

import importlib
import logging
import threading
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from ..documents import ConvertedDocument, DocumentOptions
from ._base import FORMAT_NAMES, output_limit, too_large
from ._detect import identify, sniff
from ._markdown import finalize

_CONVERTERS = {
    "pdf": "_pdf", "docx": "_docx", "pptx": "_pptx", "odt": "_odf", "odp": "_odf", "odg": "_odf",
    "odf-xml": "_odf", "rtf": "_rtf", "html": "_html", "eml": "_mail", "msg": "_mail", "txt": "_plaintext",
    "md": "_plaintext",
}
EXTENSION_KINDS = {
    ".pdf": "pdf", ".docx": "docx", ".docm": "docx", ".dotx": "docx", ".dotm": "docx", ".pptx": "pptx",
    ".pptm": "pptx", ".ppsx": "pptx", ".potx": "pptx", ".odt": "odt", ".ott": "odt", ".fodt": "odt",
    ".odp": "odp", ".otp": "odp", ".fodp": "odp", ".odg": "odg", ".rtf": "rtf", ".html": "html", ".htm": "html",
    ".xhtml": "html", ".eml": "eml", ".mht": "eml", ".mhtml": "eml", ".msg": "msg", ".txt": "txt", ".text": "txt",
    ".md": "md", ".markdown": "md",
}

# Les journaux des analyseurs peuvent citer le document : coupés pendant la conversion.
# Parser logs may quote the document: muted during conversion.
_NOISY_LOGGERS = ("pypdf", "pypdfium2", "olefile", "bs4", "mammoth", "docx", "pptx", "charset_normalizer",
                  "markdownify", "oxmsg", "PIL", "defusedxml")
_quiet_lock = threading.Lock()
_quiet_depth = 0
_saved_levels: dict[str, int] = {}
warnings.filterwarnings("ignore", module=r"(pypdf|pypdfium2|olefile|bs4|mammoth|docx|pptx|markdownify|oxmsg|"
                                         r"charset_normalizer)(\.|$)")


@contextmanager
def quiet_libraries() -> Iterator[None]:
    """Coupe les journaux des analyseurs (compteur sûr entre threads) / mutes parser logs (thread-safe count)."""
    global _quiet_depth
    with _quiet_lock:
        if _quiet_depth == 0:
            for name in _NOISY_LOGGERS:
                logger = logging.getLogger(name)
                _saved_levels[name] = logger.level
                logger.setLevel(logging.CRITICAL + 1)
        _quiet_depth += 1
    try:
        yield
    finally:
        with _quiet_lock:
            _quiet_depth -= 1
            if _quiet_depth == 0:
                for name, level in _saved_levels.items():
                    logging.getLogger(name).setLevel(level)
                _saved_levels.clear()


def convert_document(data: bytes, extension: str, options: DocumentOptions) -> ConvertedDocument:
    """Identifie, convertit et normalise ; `extension` ne sert que d'indice / `extension` is only a hint."""
    with quiet_libraries():
        source = identify(data, sniff(data, extension))
        module = importlib.import_module(f"{__package__}.{_CONVERTERS[source.kind]}")
        document: ConvertedDocument = module.convert(source, options)
        document.markdown = finalize(document.markdown)
    limit = output_limit(options)
    if len(document.markdown) > limit:
        raise too_large("texte extrait (caractères)", "extracted text (characters)", limit)
    if not document.markdown:
        document.warnings.append("Aucun texte extrait / no text extracted")
    expected = EXTENSION_KINDS.get(extension)
    if expected and expected != document.kind and {expected, document.kind} != {"txt", "md"}:
        name = FORMAT_NAMES.get(document.kind, document.kind)
        document.warnings.append(f"Extension trompeuse : le contenu est au format {name} / misleading extension: "
                                 f"content is {name}")
    return document


def convert_in_worker(data: bytes, extension: str, options: DocumentOptions) -> tuple[Any, ...]:
    """Point d'entrée du travailleur ; renvoie un tuple simple à transmettre / worker entry, plain tuple result."""
    document = convert_document(data, extension, options)
    return document.markdown, document.kind, document.pages, document.warnings, document.dropped


def preload() -> None:
    """Charge les convertisseurs à l'avance (travailleur chaud) / imports converters ahead of time (warm worker)."""
    for module in sorted(set(_CONVERTERS.values())):
        importlib.import_module(f"{__package__}.{module}")


__all__ = ["EXTENSION_KINDS", "convert_document", "convert_in_worker", "preload", "quiet_libraries"]
