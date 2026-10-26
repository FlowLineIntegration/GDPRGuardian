"""Service en ligne : API REST, serveur MCP, envois hors bande / online service: REST API, MCP, out-of-band uploads.

Import paresseux : `gdprguardian mcp --stdio` n'exige pas FastAPI / lazy import, the stdio server needs no FastAPI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import create_app
    from .config import ServerConfig

__all__ = ["ServerConfig", "create_app"]


def __getattr__(name: str) -> Any:
    if name == "create_app":
        from .app import create_app

        return create_app
    if name == "ServerConfig":
        from .config import ServerConfig

        return ServerConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
