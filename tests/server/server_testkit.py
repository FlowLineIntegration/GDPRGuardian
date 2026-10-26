"""Outils partagés des tests du service / shared helpers for the service tests."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from gdprguardian.documents import DocumentResult, UnsupportedFormatError

REPO = Path(__file__).resolve().parents[2]
INTEGRATIONS = REPO / "integrations" / "claude"
# Plugin Claude (Claude Code, Claude Desktop et Cowork) : skill, hook, serveur MCP local / Claude plugin.
PLUGIN = INTEGRATIONS / "plugin"

KEY_A = "alpha-key-0123456789-abcdefghijklmnop"
KEY_B = "bravo-key-0123456789-abcdefghijklmnop"
KEY_A_SHA256 = hashlib.sha256(KEY_A.encode()).hexdigest()
KEY_B_SHA256 = hashlib.sha256(KEY_B.encode()).hexdigest()
AUTH_A = {"Authorization": f"Bearer {KEY_A}"}
AUTH_B = {"Authorization": f"Bearer {KEY_B}"}
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
# Service public derrière Nginx : l'adresse du client arrive dans cet en-tête / public service behind Nginx.
CLIENT_HEADER = "X-GG-Client"
PUBLIC = {"public": True, "client_ip_header": CLIENT_HEADER}


def from_ip(address: str) -> dict[str, str]:
    """En-tête posé par Nginx pour un client à cette adresse / header Nginx sets for a client at this address."""
    return {CLIENT_HEADER: address}

# Données personnelles fictives, qui ne doivent jamais ressortir / fictitious PII that must never leak.
NIR = "1 85 05 78 006 084 91"
EMAIL = "jean.dupont@exemple.fr"
IBAN = "FR76 3000 6000 0112 3456 7890 189"
SENSITIVE_TEXT = f"Dossier de M. Jean Dupont, NIR {NIR}, mail {EMAIL}, IBAN {IBAN}.\n"
SECRETS = (NIR, EMAIL, IBAN)


class FakeClock:
    """Horloge monotone pilotable / controllable monotonic clock."""

    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def fake_anonymize_document(data: bytes, filename: str, anonymizer: Any = None, options: Any = None
                            ) -> DocumentResult:
    """Convertisseur factice pour .txt/.md, même contrat que la façade : le nom de fichier ne choisit que le
    format et n'est jamais écrit. Fake converter, same contract: the file name only selects the format."""
    if not filename.lower().endswith((".txt", ".md")):
        raise UnsupportedFormatError("unsupported")
    result = anonymizer.anonymize(data.decode("utf-8"))
    return DocumentResult(result.text, "txt", dict(result.report), ["note"], {"comments": 1})


def load_script(path: Path, name: str) -> ModuleType:
    """Charge un script autonome sans écrire de __pycache__ à côté / loads a standalone script, no __pycache__."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def mcp_call(name: str, arguments: dict[str, Any], request_id: int = 1) -> dict[str, Any]:
    """Requête JSON-RPC tools/call brute / raw JSON-RPC tools/call request."""
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}}
