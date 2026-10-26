"""Accès aux outils du protocole (hors paquet publié) / access to the protocol tooling (not shipped)."""

from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class EngineTransport:
    """Faux service : le moteur en processus derrière la même interface que le socket / fake service, in process.

    Options en clair, réponses JSON comme le vrai service ; `fail_after` simule une panne (OSError) après n
    anonymisations, `statuses` impose des codes HTTP successifs, `packs` change l'empreinte du moteur, `deep` est le
    code de /health/deep (404 : jeton local refusé), `counters` ajoute les compteurs croissants de /status,
    `switch_after` change le moteur (il ne masque plus rien) après n anonymisations, `restart_after` remet les
    compteurs à zéro (redémarrage) après n anonymisations. `deep` is the /health/deep status (404: local token
    refused), `counters` adds the growing /status counters, `switch_after` changes the engine (it masks nothing any
    more) after n anonymisations, `restart_after` resets the counters (restart) after n anonymisations.
    """

    def __init__(self, *, fail_after: int | None = None, statuses: list[int] | None = None,
                 packs: Any = None, visitors: int = 0, deep: int = 200, counters: bool = False,
                 switch_after: int | None = None, restart_after: int | None = None, delay: float = 0.0) -> None:
        self.delay = delay  # durée de chaque anonymisation, pour des campagnes à plusieurs contrôles / per-call delay
        self.calls = 0
        self.fail_after = fail_after
        self.statuses = list(statuses or [])
        self.packs = packs if packs is not None else [{"id": "FR", "version": "test"}]
        self.visitors = visitors  # requêtes de visiteurs vues par /status / visitor requests seen by /status
        self.deep = deep
        self.counters = counters
        self.switch_after = switch_after
        self.restart_after = restart_after
        self.accepted = 0
        self.engines: dict[Any, Any] = {}
        self._lock = threading.Lock()

    def _engine(self, countries: Any) -> Any:
        from gdprguardian import Anonymizer

        key = countries if isinstance(countries, str) else tuple(countries)
        if key not in self.engines:
            self.engines[key] = Anonymizer(countries=tuple(key.split(",")) if "," in key or key.isupper() else key,
                                           profile="standard", label_language="fr")
        return self.engines[key]

    def request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, Mapping[str, str], bytes]:
        if path == "/health":
            return 200, {}, json.dumps({"status": "ok", "version": "1.0.0"}).encode()
        if path == "/health/deep":
            return self.deep, {}, json.dumps({"status": "ok", "version": "1.0.0"}).encode()
        if path == "/v1/packs":
            return 200, {}, json.dumps({"packs": self.packs}).encode()
        if path == "/status":
            status: dict[str, Any] = {"workers": {"slots": 3, "busy": 0, "waiting": self.visitors}}
            if self.counters:
                status["counters"] = {"accepted": self.accepted, "limited": 0, "shed": 0, "errors": 0}
            return 200, {}, json.dumps(status).encode()
        assert method == "POST" and path == "/v1/anonymize/text" and body is not None
        if self.statuses:
            status_code = self.statuses.pop(0)
            if status_code != 200:
                return status_code, {"retry-after": "0"}, b'{"error": {"code": "x"}}'
        if self.fail_after is not None and self.calls >= self.fail_after:
            raise ConnectionRefusedError
        if self.delay:
            time.sleep(self.delay)
        with self._lock:
            self.calls += 1
            self.accepted += 1
            if self.restart_after is not None and self.calls == self.restart_after:
                self.accepted = 1  # nouveau processus : compteurs repartis de zéro / new process, counters reset
            switched = self.switch_after is not None and self.calls > self.switch_after
        payload = json.loads(body)
        if switched:  # autre moteur : ne masque plus rien / another engine: masks nothing any more
            return 200, {}, json.dumps({"text": payload["text"], "report": {}}, ensure_ascii=False).encode()
        result = self._engine(payload.get("countries", "FR")).anonymize(payload["text"])
        return 200, {}, json.dumps({"text": result.text, "report": {}}, ensure_ascii=False).encode()

    def close(self) -> None:
        pass


@pytest.fixture
def engine_transport() -> type[EngineTransport]:
    return EngineTransport
