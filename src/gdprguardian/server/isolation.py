"""Une requête, un processus : traitement isolé du service / one request, one process: isolated processing.

Chaque requête (texte ou document, REST ou MCP) est traitée de bout en bout (compilation des règles de
l'organisation, conversion, anonymisation, portée) dans un processus neuf qui meurt ensuite ; le processus
principal ne lit, ne compile ni n'anonymise jamais un contenu. Les deux côtés du protocole sont réunis ici
pour se relire ensemble. Every request (text or document, REST or MCP) is processed end to end (organisation
rules compiled, conversion, anonymisation, scope) in a fresh process that dies afterwards; the main process
never parses, compiles nor anonymises content. Both sides of the protocol live here so they can be reviewed
together.

Parent : envoie les octets (texte UTF-8 ou fichier) et une spécification JSON (options, nom neutre,
limites) ; les règles de l'organisation y voyagent en JSON et sont relues comme non sûres. Reçoit un en-tête
JSON borné puis le texte anonymisé brut, et en vérifie la forme (ensembles fermés pour ce qui est journalisé).
Parent: sends the bytes and a JSON spec; organisation rules travel as JSON and are re-parsed as untrusted.
Receives a bounded JSON header then the raw anonymised text, and shape-checks it (closed sets for anything
that gets logged).
"""

from __future__ import annotations

import gc
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from .. import documents
from ..convert import _sandbox
from ..convert._base import CRASH_MESSAGE, FORMAT_NAMES
from ..custom import RuleError
from ..documents import (
    SPREADSHEET_EXTENSIONS,
    DocumentError,
    DocumentOptions,
    DocumentResult,
    DocumentTooLargeError,
)
from .errors import OUTPUT_TOO_LARGE
from .options import DEFAULT_COUNTRIES, AnonymizeOptions

JOB_TARGET = f"{__name__}:run_job"
PRELOAD_TARGET = f"{__name__}:preload"
PRIME_TARGET = f"{__name__}:prime"
# Formats produits par les convertisseurs et le pipeline tableur / kinds produced by converters and spreadsheets.
DOCUMENT_KINDS = frozenset({*FORMAT_NAMES, "odf-xml", *(ext.lstrip(".") for ext in SPREADSHEET_EXTENSIONS)})
INVALID_RULES = "invalid_rules"
JOB_ERRORS = frozenset({"converter_unavailable", "internal", INVALID_RULES})
_DROPPED_KEY_RE = re.compile(r"[a-z][a-z0-9_]{0,39}")
_ERROR_TYPE_RE = re.compile(r"[a-z0-9_]{1,40}")
# Raison d'un refus de règles : construite par le moteur à partir des seules règles, bornée / bounded reason.
_MAX_RULES_MESSAGE = 600
_REFUSED_RULES = "Règles de l'organisation refusées / organisation rules refused"
_COSTLY_RULES = ("Règles de l'organisation trop coûteuses à compiler (mémoire, imbrication) / organisation rules too "
                 "costly to compile (memory, nesting)")
# Échéance : délai de conversion + une seconde par 250 Ko pour l'anonymisation (proportionnelle à la taille).
# Deadline: conversion timeout + one second per 250 KB for the anonymisation (proportional to the size).
_BYTES_PER_EXTRA_SECOND = 250_000
# Sortie d'un texte : les balises peuvent être plus longues que les valeurs (32 fois au pire), 64 Ki au moins.
# Output of a text: placeholders may be longer than the values (32 times at worst), at least 64 Ki.
_TEXT_EXPANSION = 32
_MIN_TEXT_OUTPUT_CHARS = 64 * 1024
# En-tête JSON (rapport, avertissements) en plus du texte / JSON header (report, warnings) on top of the text.
_REPLY_OVERHEAD = 1 << 20
_MAX_REPORTED_CPU_MS = 86_400_000
# Texte converti refusé avant le moteur au-delà de ce multiple du plafond de sortie : les balises raccourcissent
# rarement un texte de plus de moitié (tableaux d'IBAN, de NIR), et le moteur tient 2 fois le plafond en mémoire
# (25 M caractères : +0,55 Gio, 6 s). Converted text refused before the engine beyond this multiple of the output cap:
# placeholders seldom shorten a text by more than half, and the engine holds twice the cap in memory.
_CONVERTED_SLACK = 2
_DEFAULT_PAGES = DocumentOptions().max_pages
# Ramassage explicite entre conversion et moteur, pour les gros documents seulement (le zygote a gelé ses objets) /
# explicit collection between conversion and engine, for big documents only (the zygote froze its objects).
_COLLECT_FROM_BYTES = 1 << 20
# Texte de chauffe entièrement fictif (valeurs des jeux de test), du vocabulaire d'un courrier, d'un contrat et
# d'une facture. Le drapeau final (U+1F3F4 et étiquettes U+E00xx) charge le plan 14 dans le zygote : un
# travailleur neuf ne le paie plus à sa première requête. Entirely fictitious warm-up text (test-fixture values),
# the vocabulary of a letter, a contract and an invoice. The final flag (U+1F3F4 and U+E00xx tags) loads plane
# 14 in the zygote: a fresh worker no longer pays for it on its first request.
_WARM_UP_TEXT = """\
# Compte rendu de la réunion du 12 mars 2024

**Objet :** renouvellement du contrat de prestation n° 2024-118 et facture associée.

Madame, Monsieur,

Suite à notre entretien téléphonique du lundi 11 mars, je vous confirme que M. Jean Martin, né le 12/03/1985 à
Lyon (NIR 1 85 05 78 006 084 91), reprendra le dossier de Mme Claire Dubois à compter du 1er avril. Vous pouvez
le joindre au 06 12 34 56 78 ou par courriel à jean.martin@exemple.fr. Son adresse postale : 12 rue de la Paix,
75002 Paris.

Le règlement de la facture FA-2024-0042 (montant : 1 250,00 € TTC) sera effectué par virement sur le compte
IBAN FR76 3000 6000 0112 3456 7890 189 de la société Exemple SAS (SIRET 732 829 320 00074, TVA FR44 732829320),
dont le siège est situé 5 avenue des Champs-Élysées, 75008 Paris. Merci de rappeler la référence du client
CLT-204518 lors du paiement.

| Nom | Fonction | Téléphone |
|---|---|---|
| Jean Martin | Chef de projet | 01 23 45 67 89 |
| Claire Dubois | Directrice administrative | +33 6 98 76 54 32 |

Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

Pierre Lefèvre, responsable juridique \U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F
"""
# Amorce d'un travailleur neuf : courte, le meilleur rapport latence / CPU mesuré (-1,4 ms par requête pour
# +2 ms à la naissance). Prime of a fresh worker: short, the best measured latency / CPU ratio.
_PRIME_TEXT = "Dossier de M. Jean Martin, NIR 1 85 05 78 006 084 91, jean.martin@exemple.fr, 06 12 34 56 78."
_WARM_UP_CSV = b"nom;email;telephone\nJean Martin;jean.martin@exemple.fr;06 12 34 56 78\n"


class JobError(Exception):
    """Erreur applicative du travailleur, code fermé / worker application error, closed code.

    `message` : raison d'un refus de règles (`invalid_rules`) seulement, rédigée par le moteur à partir des
    règles du client (numéro, libellé, raison), jamais journalisée ; vide sinon. `message`: the reason of a rule
    refusal only, written by the engine from the client's rules, never logged; empty otherwise.
    """

    def __init__(self, code: str, error_type: str, message: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.error_type = error_type
        self.message = message


@dataclass(slots=True, frozen=True)
class Outcome:
    """Résultat vérifié d'un travailleur / checked worker result."""

    text: str
    meta: dict[str, Any]
    worker: int


# --- côté parent / parent side ----------------------------------------------------------------------


def deadline_s(timeout_s: float, payload_bytes: int) -> float:
    """Échéance d'une requête / a request's deadline."""
    return timeout_s + payload_bytes / _BYTES_PER_EXTRA_SECOND


def text_reply_limit(chars: int, max_output_chars: int) -> int:
    """Réponse maximale pour un texte : balises plus longues que les valeurs, sous le plafond de sortie, 4 octets par
    caractère. Largest reply for a text: placeholders may be longer than values, under the output cap, 4 bytes per
    character."""
    return 4 * min(max_output_chars, max(_MIN_TEXT_OUTPUT_CHARS, _TEXT_EXPANSION * chars)) + _REPLY_OVERHEAD


def document_reply_limit(max_output_chars: int) -> int:
    """Réponse maximale pour un document : le plafond de sortie, 4 octets par caractère.

    Largest reply for a document: the output cap, 4 bytes per character.
    """
    return 4 * max_output_chars + _REPLY_OVERHEAD


def text_spec(options: AnonymizeOptions, max_output_chars: int | None = None) -> str:
    """`max_output_chars` : plus long texte rendu ; au-delà, le travailleur répond « trop volumineux » (413).

    `max_output_chars`: longest text returned; beyond, the worker answers "too large" (413).
    """
    return json.dumps({"kind": "text", "options": options.to_json(), "max_chars": max_output_chars},
                      ensure_ascii=False)


def document_spec(options: AnonymizeOptions, filename: str, document_options: DocumentOptions,
                  max_output_chars: int | None = None) -> str:
    """`document_options.timeout_s` : délai interne des convertisseurs (le service y met l'échéance de la requête) ;
    `max_pages` : pages ou diapositives au plus. `timeout_s`: converters' inner deadline (the service puts the
    request's deadline there); `max_pages`: pages or slides at most."""
    return json.dumps({"kind": "document", "options": options.to_json(), "filename": filename,
                       "max_bytes": document_options.max_bytes, "timeout_s": document_options.timeout_s,
                       "max_pages": document_options.max_pages, "sandbox": document_options.sandbox,
                       "max_chars": max_output_chars}, ensure_ascii=False)


def decode_text(value: Any) -> Outcome:
    """Réponse d'un travail « texte », forme vérifiée / "text" job reply, shape checked."""
    meta, text = _body(value)
    if not isinstance(meta.get("report"), dict):
        raise DocumentError(CRASH_MESSAGE)
    return Outcome(text, {"report": meta["report"]}, _worker(meta))


def decode_document(value: Any) -> tuple[DocumentResult, int]:
    """Réponse d'un travail « document », forme vérifiée / "document" job reply, shape checked.

    `kind` et les clés de `dropped` finissent dans les journaux et le rapport : ensembles fermés.
    `kind` and `dropped` keys end up in logs and the report: closed sets.
    """
    meta, markdown = _body(value)
    kind, pages, warnings, dropped, report = (meta.get(key) for key in ("kind", "pages", "warnings", "dropped",
                                                                        "report"))
    if (isinstance(kind, str) and kind in DOCUMENT_KINDS and (pages is None or type(pages) is int)
            and isinstance(report, dict)
            and isinstance(warnings, list) and all(isinstance(item, str) for item in warnings)
            and isinstance(dropped, dict) and all(type(count) is int for count in dropped.values())
            and all(isinstance(key, str) and _DROPPED_KEY_RE.fullmatch(key) for key in dropped)):
        return DocumentResult(markdown, kind, report, warnings, dropped, pages), _worker(meta)
    raise DocumentError(CRASH_MESSAGE)


def _body(value: Any) -> tuple[dict[str, Any], str]:
    if isinstance(value, _sandbox.Body) and isinstance(value.meta, dict):
        return value.meta, value.text
    if isinstance(value, dict) and isinstance(value.get("error"), str) and value["error"] in JOB_ERRORS:
        error_type, message = value.get("type"), value.get("message")
        raise JobError(value["error"], error_type if isinstance(error_type, str)
                       and _ERROR_TYPE_RE.fullmatch(error_type) else "unknown",
                       _rules_message(message) if value["error"] == INVALID_RULES else "")
    raise DocumentError(CRASH_MESSAGE)


def _rules_message(message: Any) -> str:
    """Raison bornée, encodable en UTF-8 (un motif peut porter un demi-codet) / bounded, UTF-8-encodable reason."""
    if not isinstance(message, str) or not message:
        return _REFUSED_RULES
    return message[:_MAX_RULES_MESSAGE].encode("utf-8", "replace").decode("utf-8")


def _worker(meta: dict[str, Any]) -> int:
    pid = meta.get("worker")
    return pid if type(pid) is int else 0


def reported_cpu_s(value: Any) -> float:
    """Temps processeur que le travailleur dit avoir consommé, borné ; 0 sans réponse exploitable.

    CPU time the worker reports, bounded; 0 without a usable reply. Le limiteur prend le plus grand de cette valeur et
    du temps d'occupation mesuré ici : un travailleur compromis qui minore son temps n'y gagne rien. The limiter takes
    the larger of this and the occupancy measured here: a compromised worker under-reporting gains nothing.
    """
    meta = value.meta if isinstance(value, _sandbox.Body) else None
    cpu = meta.get("cpu_ms") if isinstance(meta, dict) else None
    return cpu / 1000 if type(cpu) is int and 0 <= cpu <= _MAX_REPORTED_CPU_MS else 0.0


class InlineRunner:
    """Même protocole, dans le processus principal : tests et intégration, jamais en service.

    Same protocol, in the main process: tests and embedding, never in production. Les conversions restent
    dans le bac à sable de la bibliothèque / conversions stay in the library's sandbox.
    """

    isolated = False

    def start(self) -> None:
        """Rien à démarrer / nothing to start."""

    def stop(self) -> None:
        """Arrête les convertisseurs inactifs de la bibliothèque / stops the library's idle converters."""
        _sandbox.shutdown()

    def run(self, payload: bytes | bytearray, spec: str, timeout_s: float, max_reply: int,
            cancel: _sandbox.CancelHandle) -> Any:
        return _sandbox.run_inline(JOB_TARGET, payload, (spec,), max_reply)


class IsolatedRunner:
    """Chaque requête dans un processus neuf, à usage unique / each request in a fresh, single-use process.

    Une réserve de `reserve` processus préchargés attend les requêtes ; sous Linux, ils naissent du zygote.
    A reserve of `reserve` preloaded processes awaits requests; on Linux they are born from the zygote.
    """

    isolated = True

    def __init__(self, memory_mb: int, reserve: int) -> None:
        self._config = _sandbox.SandboxConfig(max_idle_workers=reserve, max_jobs_per_worker=1, memory_mb=memory_mb,
                                              preload=PRELOAD_TARGET, prime=PRIME_TARGET)
        self._lock = threading.Lock()
        self.pool = _sandbox.WorkerPool(self._config, single_use=True)

    def start(self) -> None:
        """Zygote et réserve en arrière-plan / zygote and reserve in the background."""
        with self._lock:
            pool = self.pool
        pool.start(self._config.max_idle_workers)

    def stop(self) -> None:
        """Arrête tous les travailleurs ; un nouvel ensemble démarrera à la demande / a new set starts on demand."""
        with self._lock:
            pool, self.pool = self.pool, _sandbox.WorkerPool(self._config, single_use=True)
        pool.shutdown()

    def run(self, payload: bytes | bytearray, spec: str, timeout_s: float, max_reply: int,
            cancel: _sandbox.CancelHandle) -> Any:
        with self._lock:
            pool = self.pool
        return pool.call(JOB_TARGET, payload, (spec,), timeout_s, max_reply, cancel)


# --- côté travailleur / worker side -----------------------------------------------------------------


def run_job(payload: bytes, spec: str) -> _sandbox.Body | dict[str, str]:
    """Point d'entrée du travailleur : une requête, de bout en bout / worker entry point: one whole request.

    Les erreurs de document remontent par le bac à sable (classes fermées) ; les autres deviennent un code
    applicatif, avec le seul type de l'exception (son message pourrait citer le document).
    Document errors go up through the sandbox (closed classes); others become an application code, with the
    exception type only (its message could quote the document).

    Les règles de l'organisation sont compilées d'abord, avant toute lecture du contenu : un refus devient
    `invalid_rules` avec la raison du moteur (numéro, libellé, cause), rédigée à partir des seules règles.
    The organisation's rules are compiled first, before any content is read: a refusal becomes `invalid_rules`
    with the engine's reason (number, label, cause), written from the rules alone.

    La réponse rapporte le temps processeur consommé (`cpu_ms`), pour la correction du limiteur. Un résultat plus
    long que `max_chars` n'est jamais envoyé : « trop volumineux » (413), le processus principal ne le reçoit pas ;
    un document converti en plus de deux fois `max_chars` est refusé de même dès la conversion, avant le moteur.
    The reply reports the CPU time used (`cpu_ms`), for the limiter's true-up. A result longer than `max_chars` is
    never sent: "too large" (413), the main process never receives it; a document converted into more than twice
    `max_chars` is refused the same way right after conversion, before the engine.
    """
    started = time.process_time()
    try:
        job = json.loads(spec)
        options = AnonymizeOptions.from_json(job["options"])
        max_chars = job.get("max_chars")
        try:
            anonymizer = options.anonymizer()
        except RuleError as exc:
            return {"error": INVALID_RULES, "message": str(exc)[:_MAX_RULES_MESSAGE]}
        except (MemoryError, RecursionError):
            if options.rules is None:
                raise
            return {"error": INVALID_RULES, "message": _COSTLY_RULES}
        if job["kind"] == "text":
            result = anonymizer.anonymize(payload.decode("utf-8"))
            _check_output(result.text, max_chars)
            return _sandbox.Body({"report": result.report, "worker": os.getpid(), "cpu_ms": _cpu_ms(started)},
                                 result.text)
        limits = DocumentOptions(max_bytes=job["max_bytes"], timeout_s=job["timeout_s"], sandbox=job["sandbox"],
                                 max_pages=job.get("max_pages", _DEFAULT_PAGES))
        document = _anonymize_document(payload, job["filename"], anonymizer, limits, max_chars)
        _check_output(document.markdown, max_chars)
        meta = {"kind": document.kind, "pages": document.pages, "warnings": document.warnings,
                "dropped": document.dropped, "report": document.report, "worker": os.getpid(),
                "cpu_ms": _cpu_ms(started)}
        return _sandbox.Body(meta, document.markdown)
    except (DocumentError, MemoryError, RecursionError):
        raise  # traduites par le bac à sable / translated by the sandbox
    except (ImportError, NotImplementedError):
        return {"error": "converter_unavailable"}
    except Exception as exc:
        return {"error": "internal", "type": type(exc).__name__.lower()[:40]}


def _cpu_ms(started: float) -> int:
    return max(0, round((time.process_time() - started) * 1000))


def _check_output(text: str, max_chars: Any) -> None:
    """Plafond de sortie, appliqué dans le travailleur avant toute réponse / output cap, before any reply."""
    if type(max_chars) is int and len(text) > max_chars:
        raise DocumentTooLargeError(OUTPUT_TOO_LARGE)


class _CappedEngine:
    """Moteur dont `anonymize` refuse d'abord un texte converti qui ne peut pas tenir sous le plafond de sortie.

    Engine whose `anonymize` first refuses a converted text that cannot fit under the output cap. La façade
    `documents.anonymize_document` l'appelle une fois, sur le Markdown converti : le refus tombe avant le moteur, sans
    rien changer au résultat ; pour un gros document, la mémoire de la conversion (arbres HTML et XML, à références
    circulaires) est d'abord rendue. Tout autre attribut est celui du moteur. The facade calls it once, on the
    converted Markdown: the refusal comes before the engine, the result unchanged; for a big document the conversion's
    memory (cyclic HTML and XML trees) is handed back first. Any other attribute is the engine's.
    """

    __slots__ = ("__weakref__", "_collect", "_engine", "_limit")

    def __init__(self, engine: Any, limit: int | None, collect: bool) -> None:
        self._engine = engine
        self._limit = limit
        self._collect = collect

    def anonymize(self, text: str, *args: Any, **kwargs: Any) -> Any:
        if self._limit is not None and len(text) > self._limit:
            raise DocumentTooLargeError(OUTPUT_TOO_LARGE)
        if self._collect:
            gc.collect()
        return self._engine.anonymize(text, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._engine, name)


def _anonymize_document(payload: bytes, filename: str, anonymizer: Any, limits: DocumentOptions,
                        max_chars: Any) -> DocumentResult:
    """`documents.anonymize_document` avec le moteur plafonné : texte converti au-delà de `_CONVERTED_SLACK` fois
    `max_chars`, refusé avant le moteur. Les tableurs (même règle d'extension que la façade) gardent le moteur tel
    quel : leur pipeline n'appelle jamais `anonymize` (il anonymise par segments) et garde un cache par moteur. The
    facade with the capped engine: converted text beyond `_CONVERTED_SLACK` times `max_chars` is refused before the
    engine. Spreadsheets (the facade's own extension rule) keep the engine as is: their pipeline never calls
    `anonymize` (it works by segments) and keeps a per-engine cache."""
    if PurePath(filename).suffix.lower() in SPREADSHEET_EXTENSIONS:
        return documents.anonymize_document(payload, filename, anonymizer, limits)
    limit = max_chars * _CONVERTED_SLACK if type(max_chars) is int else None
    engine = _CappedEngine(anonymizer, limit, collect=len(payload) >= _COLLECT_FROM_BYTES)
    return documents.anonymize_document(payload, filename, engine, limits)


def preload() -> None:
    """Charge une fois, avant tout document, ce qui coûte : convertisseurs, lecteur de tableurs, packs,
    automates de mots-clés, analyseurs Rust, lexique des noms, moteurs par défaut et pays « all ».

    Loads once, before any document, everything costly: converters, spreadsheet reader, packs, keyword
    automata, Rust scanners, name lexicon, default and "all" engines. Données de chauffe fictives.
    """
    for countries in (DEFAULT_COUNTRIES, "all"):
        AnonymizeOptions(countries=countries).anonymizer().anonymize(_WARM_UP_TEXT)
    from ..convert import _dispatch

    _dispatch.preload()
    documents.anonymize_document(_WARM_UP_CSV, "document.csv", AnonymizeOptions().anonymizer(),
                                 DocumentOptions(sandbox=False))


def prime() -> None:
    """Amorce un travailleur neuf (données fictives) : le chemin d'une requête est parcouru une fois, et les
    pages qu'il copie à l'écriture le sont pendant l'attente en réserve plutôt que pendant la requête.

    Primes a fresh worker (fictitious data): a request's path runs once, so the pages it copies on write are
    copied while the worker waits in the reserve rather than during the request.
    """
    run_job(_PRIME_TEXT.encode(), text_spec(AnonymizeOptions()))


__all__ = ["DOCUMENT_KINDS", "INVALID_RULES", "JOB_TARGET", "PRELOAD_TARGET", "PRIME_TARGET", "InlineRunner",
           "IsolatedRunner", "JobError", "Outcome", "deadline_s", "decode_document", "decode_text",
           "document_reply_limit", "document_spec", "preload", "prime", "reported_cpu_s", "run_job", "text_reply_limit",
           "text_spec"]
