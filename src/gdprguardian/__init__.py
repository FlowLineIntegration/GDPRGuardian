"""Gardien RGPD : anonymisation irréversible et cohérente, sans LLM / GDPR Guardian: irreversible, consistent, LLM-free.

>>> from gdprguardian import anonymize
>>> anonymize("Jean Dupont, NIR 1 85 05 78 006 084 91").text  # doctest: +SKIP
"""

from .engine import Anonymizer, DetectionContext, Settings, anonymize
from .scope import Scope
from .types import Analysis, AnonymizedText, Span

# Recopiée depuis pyproject.toml par `tools/release.py set` ; tests/test_release.py vérifie l'égalité.
# Copied from pyproject.toml by `tools/release.py set`; tests/test_release.py checks they match.
__version__ = "1.0.2"

__all__ = ["Analysis", "AnonymizedText", "Anonymizer", "DetectionContext", "Scope", "Settings", "Span", "anonymize"]
