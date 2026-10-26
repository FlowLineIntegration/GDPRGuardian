"""Journal sans contenu : un seul point d'entrée, valeurs typées / content-free logging: one entry point, typed values.

Seuls des nombres, des booléens et des codes courts en minuscules passent ; toute autre chaîne est
remplacée par « redacted ». Only numbers, booleans and short lowercase codes pass; any other string
is replaced by "redacted".
"""

from __future__ import annotations

import logging
import os
import re
import sys

LOGGER = logging.getLogger("gdprguardian.server")

_CODE_RE = re.compile(r"[a-z0-9_./{}-]{1,48}")
_METHODS = frozenset({"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"})
# Journaux tiers susceptibles d'être bavards / third-party loggers that may be chatty.
_THIRD_PARTY = ("mcp", "fastmcp", "sse_starlette", "multipart", "python_multipart", "httpx", "httpcore",
                "uvicorn.access")

LogValue = int | float | bool | str | None


def log_event(event: str, level: int = logging.INFO, **fields: LogValue) -> None:
    """Journalise `event` avec des métadonnées sûres / logs `event` with safe metadata."""
    if not LOGGER.isEnabledFor(level):
        return
    parts = [f"event={_format(event)}"]
    parts.extend(f"{key}={_format(value)}" for key, value in fields.items())
    LOGGER.log(level, " ".join(parts))


def _format(value: LogValue) -> str:
    if value is None or isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.1f}"
    if isinstance(value, str) and (_CODE_RE.fullmatch(value) or value in _METHODS):
        return value
    return "redacted"


class ThirdPartyTracebackFilter(logging.Filter):
    """Retire les traces des journaux tiers : un message d'exception peut citer un document.

    Strips tracebacks from third-party records: an exception message may quote a document. Le type de
    l'exception reste visible / the exception type stays visible.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.startswith("gdprguardian") or not (record.exc_info or record.exc_text or record.stack_info):
            return True
        error = record.exc_info[1] if record.exc_info else None
        suffix = f" [{type(error).__name__}, trace supprimée / traceback suppressed]" if error else ""
        record.msg = f"{record.getMessage()}{suffix}"
        record.args = None
        record.exc_info = record.exc_text = record.stack_info = None
        return True


def configure_logging(level: str = "INFO") -> None:
    """Un seul journal filtré sur stderr, bibliothèques tierces aux avertissements / one filtered stderr log.

    FastMCP installe sinon ses propres sorties Rich, non propagées et avec traces : elles sont coupées pour
    que tout passe par le même filtre. FastMCP would otherwise install its own non-propagating Rich output
    with tracebacks: it is disabled so everything goes through the same filter.
    """
    os.environ.setdefault("FASTMCP_LOG_ENABLED", "false")  # avant l'import de fastmcp / before importing it
    fastmcp_logger = logging.getLogger("fastmcp")
    fastmcp_logger.handlers.clear()
    fastmcp_logger.propagate = True
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(ThirdPartyTracebackFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for name in _THIRD_PARTY:
        logging.getLogger(name).setLevel(logging.WARNING)
