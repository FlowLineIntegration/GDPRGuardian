#!/usr/bin/env python3
"""Gardien RGPD en ligne : anonymise un document ou un texte sans que l'IA le lise, n'affiche que le Markdown anonymisé.

GDPR Guardian online: anonymises a document or a text without the AI reading it, prints ONLY the anonymised Markdown.

    python gdprguardian_online.py contrat.pdf -o contrat.anon.md     un document / a document (PDF, DOCX, XLSX, CSV...)
    python gdprguardian_online.py --text notes.txt                    un texte UTF-8 (fichier ou « - ») / a UTF-8 text
    python gdprguardian_online.py --limits                            service et limites / service and limits

Service : GDPRGUARDIAN_URL, sinon le service public gratuit, sans clé ni compte (https://api.gardienrgpd.fr).
Service: GDPRGUARDIAN_URL, else the free public service, no key, no account. GDPRGUARDIAN_API_KEY seulement pour un
serveur à clés : envoyée à ce seul serveur, jamais affichée, aucune redirection suivie / only for a keyed server.

Bibliothèque standard seule, Python 3.9+ / standard library only. Le fichier part du disque vers le service en flux,
seule son extension est transmise ; 429 et 503 sont retentés en respectant Retry-After. The file is streamed from disk,
only its extension is sent; 429 and 503 are retried, honouring Retry-After.
"""

from __future__ import annotations

import argparse
import contextlib
import http.client
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, BinaryIO

# --- Limites publiées du service public : le seul endroit à mettre à jour / published limits: the one place to edit.
PUBLIC_URL = "https://api.gardienrgpd.fr"
# Modes du service (alias anglais acceptés aussi) / service modes (English aliases accepted too).
MODES = ("fort", "essentiel", "personnalise", "strong", "essential", "custom")
MAX_FILE_MB = 50                 # par fichier / per file
MAX_TEXT_CHARS = 1_000_000       # par texte / per text
# ---

USER_AGENT = "gdprguardian-online-skill"
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_BUSY = 3                    # 429 / 503 persistants : réessayer plus tard / retry later
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
PRINT_LIMIT = 100_000            # au-delà, le Markdown va dans un fichier / beyond, the Markdown goes to a file
PAGE_CHARS = 200_000             # page la plus grande admise par le service / largest page the service accepts
_LOOPBACK = frozenset({"localhost", "127.0.0.1", "::1"})
_MESSAGE_MAX = 200
_RETRY_STATUSES = (429, 503)
_RETRIES = 3
_RETRY_MAX_S = 30.0
_RETICKET_WAIT_S = 10.0          # avant une nouvelle adresse d'envoi / before a new upload URL
_BUSY_HINT = ("service chargé, réessayez plus tard ou utilisez la skill locale / service busy, retry later or use "
              "the local skill (gdprguardian-local)")


class Failure(Exception):
    """Erreur sans contenu du document / error without document content."""

    def __init__(self, message: str, code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.code = code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # Une redirection emporterait le document (et la clé, s'il y en a une) ailleurs / a redirect would carry the
    # document (and the key, if any) elsewhere.
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any,
                         newurl: str) -> urllib.request.Request | None:
        raise Failure("redirection refusée par sécurité / redirect refused for safety")


_OPENER = urllib.request.build_opener(_NoRedirect)


def base_url(env: Mapping[str, str]) -> str:
    """GDPRGUARDIAN_URL, sinon le service public ; https seulement (http sur la boucle locale) / https only."""
    url = (env.get("GDPRGUARDIAN_URL", "").strip() or PUBLIC_URL).rstrip("/")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in _LOOPBACK):
        return url
    raise Failure("GDPRGUARDIAN_URL doit être en https (http seulement en local) / GDPRGUARDIAN_URL must use https "
                  "(http only on localhost)", EXIT_USAGE)


def _host(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or "?"


def request(method: str, url: str, key: str | None, *, payload: Any = None, upload: BinaryIO | None = None,
            size: int = 0, timeout: float = 60.0) -> tuple[int, dict[str, str], bytes]:
    """Un appel ; la clé n'est envoyée que si elle est configurée / one call; the key is sent only when set."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data: Any = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    elif upload is not None:
        data = upload
        headers["Content-Type"] = "application/octet-stream"
        headers["Content-Length"] = str(size)
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with _OPENER.open(req, timeout=max(timeout, 1.0)) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()
    except urllib.error.URLError as error:
        # Raison réseau seule (jamais de donnée du document) : aide à reconnaître un bac à sable sans accès sortant.
        # Network reason only (never document data): helps recognise a sandbox without outbound access.
        reason = "".join(ch for ch in str(error.reason) if ch.isprintable())[:120]
        raise Failure(f"serveur injoignable / server unreachable: {_host(url)} ({type(error.reason).__name__}: "
                      f"{reason})") from None
    except (OSError, http.client.HTTPException) as error:
        # Connexion coupée ou délai de lecture dépassé / connection cut or read timeout.
        raise Failure(f"connexion interrompue / connection lost: {_host(url)} ({type(error).__name__})") from None


def retry_after(headers: Mapping[str, str]) -> float:
    """Délai demandé par le serveur, borné ; 5 s sans en-tête (quota de résultats non lus) / the server's requested
    delay, bounded; 5 s without the header (unread-results quota)."""
    raw = next((v for k, v in headers.items() if k.lower() == "retry-after"), "5")
    try:
        return min(max(float(raw), 0.5), _RETRY_MAX_S)
    except ValueError:
        return 5.0


def _retry_after_text(headers: Mapping[str, str]) -> str:
    raw = next((v for k, v in headers.items() if k.lower() == "retry-after"), "")
    return f" (Retry-After: {raw.strip()[:10]} s)" if raw.strip() else ""


def with_retries(call: Callable[[], tuple[int, dict[str, str], bytes]], deadline: float,
                 sleep: Callable[[float], None] = time.sleep) -> tuple[int, dict[str, str], bytes]:
    """429 / 503 : nouvel essai après Retry-After, trois fois au plus / up to three retries after Retry-After."""
    for attempt in range(_RETRIES + 1):
        status, headers, body = call()
        if status not in _RETRY_STATUSES or attempt == _RETRIES:
            return status, headers, body
        wait = retry_after(headers)
        if time.monotonic() + wait > deadline:
            return status, headers, body
        sleep(wait)
    raise AssertionError("unreachable")


def _json(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _check(status: int, body: bytes, expected: tuple[int, ...], headers: Mapping[str, str] | None = None
           ) -> dict[str, Any]:
    data = _json(body)
    if status in expected:
        return data
    error = data.get("error") if isinstance(data.get("error"), dict) else {}
    # Messages du serveur : codes et textes fixes, bornés ici par prudence / fixed server messages, bounded anyway.
    text = f"{error.get('code', 'error')}: {error.get('message', '')}".rstrip(": ")
    text = "".join(ch for ch in text if ch.isprintable())[:_MESSAGE_MAX]
    if status in _RETRY_STATUSES:
        raise Failure(f"HTTP {status} {text}{_retry_after_text(headers or {})}: {_BUSY_HINT}", EXIT_BUSY)
    if status == 401:
        raise Failure("HTTP 401 unauthorized : ce serveur exige une clé (GDPRGUARDIAN_API_KEY) ou refuse celle "
                      "configurée / this server requires a key or refuses the configured one")
    raise Failure(f"HTTP {status} {text}")


def upload_name(path: Path) -> str:
    """« document » + extension : le nom réel ne quitte pas le poste / the real name never leaves the computer."""
    suffix = path.suffix.lower()
    return f"document{suffix}" if suffix[1:].isalnum() and suffix[1:].isascii() else "document"


def unsent_rules(env: Mapping[str, str]) -> bool:
    """Des règles existent (GDPRGUARDIAN_RULES, .gdprguardian/rules.json) mais ne partent pas sans --rules.

    Rules exist (GDPRGUARDIAN_RULES, the project's .gdprguardian/rules.json) but are not sent without --rules.
    """
    return bool(env.get("GDPRGUARDIAN_RULES", "").strip()) or (Path(".gdprguardian") / "rules.json").is_file()


def load_rules(explicit: str | None) -> dict[str, Any] | None:
    """Règles de l'organisation, seulement si --rules est donné : elles partent avec le document vers le service
    (une liste de noms à masquer est une donnée personnelle), jamais sans demande explicite. Jamais conservées par
    le serveur. The organisation's rules, only with --rules: they travel to the service with the document (a
    deny-list of names is personal data), never without an explicit request. Never kept by the server.
    """
    if not explicit:
        return None
    path = Path(explicit)
    if not path.is_file():
        raise Failure("fichier de règles introuvable / rules file not found", EXIT_USAGE)
    try:
        rules = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise Failure("fichier de règles illisible (JSON attendu) / unreadable rules file (JSON expected)",
                      EXIT_USAGE) from None
    if not isinstance(rules, dict):
        raise Failure("fichier de règles : objet JSON attendu / rules file: JSON object expected", EXIT_USAGE)
    return rules


def _options(countries: str, profile: str | None, label_language: str, explain: bool,
             rules: dict[str, Any] | None, mode: str | None = None,
             disable: Sequence[str] | None = None) -> dict[str, Any]:
    # Sans « mode », le service applique le mode fort ; « profile » n'est plus envoyé que s'il est demandé (alias
    # déprécié : standard = essentiel). Without "mode" the service applies fort; "profile" only when asked.
    options: dict[str, Any] = {"countries": countries, "label_language": label_language, "explain": explain}
    if mode:
        options["mode"] = mode
    if disable:
        options["disable"] = list(disable)
    if profile:
        options["profile"] = profile
    if rules is not None:
        options["rules"] = rules
    return options


def anonymize_text(text: str, env: Mapping[str, str], *, countries: str = "FR", profile: str | None = None,
                   label_language: str = "fr", timeout: float = 120.0, rules: dict[str, Any] | None = None,
                   explain: bool = False, mode: str | None = None,
                   disable: Sequence[str] | None = None) -> tuple[str, dict[str, Any]]:
    """Texte -> texte anonymisé, rien n'est gardé par le service / text -> anonymised text, nothing kept."""
    if len(text) > MAX_TEXT_CHARS:
        raise Failure(f"texte trop long ({len(text)} caractères > {MAX_TEXT_CHARS}) : enregistrez-le dans un fichier "
                      f".txt et anonymisez le fichier / text too long: save it as a .txt file and anonymise the file",
                      EXIT_USAGE)
    base = base_url(env)
    key = env.get("GDPRGUARDIAN_API_KEY", "").strip() or None
    deadline = time.monotonic() + timeout
    payload = {"text": text, **_options(countries, profile, label_language, explain, rules, mode, disable)}
    status, headers, body = with_retries(
        lambda: request("POST", f"{base}/v1/anonymize/text", key, payload=payload,
                        timeout=deadline - time.monotonic()), deadline)
    result = _check(status, body, (200,), headers)
    return str(result.get("text") or ""), dict(result.get("report") or {})


def _put(put_url: str, path: Path, size: int, key: str | None, deadline: float) -> tuple[int, dict[str, str], bytes]:
    """Envoi en flux depuis le disque ; une connexion coupée en cours d'envoi est retentée une fois.

    Streamed from disk; a connection cut while sending (refusal before the body was read) is retried once.
    """
    for attempt in range(2):
        try:
            with path.open("rb") as handle:
                return request("PUT", put_url, key, upload=handle, size=size, timeout=deadline - time.monotonic())
        except Failure:
            if attempt or time.monotonic() + 5 > deadline:
                raise
            time.sleep(5)
    raise AssertionError("unreachable")


def anonymize(path: Path, env: Mapping[str, str], *, countries: str = "FR", profile: str | None = None,
              label_language: str = "fr", timeout: float = 900.0, rules: dict[str, Any] | None = None,
              explain: bool = False, sink: Callable[[str], None] | None = None, mode: str | None = None,
              disable: Sequence[str] | None = None) -> tuple[str, dict[str, Any]]:
    """Envoi hors bande puis lecture de toutes les pages / out-of-band upload, then every page is read.

    Avec `sink`, chaque page lui est passée et le Markdown rendu est vide / with `sink`, pages go to it.
    """
    base = base_url(env)
    # Service public : aucune clé. Serveur à clés : GDPRGUARDIAN_API_KEY. Public service: no key at all.
    key = env.get("GDPRGUARDIAN_API_KEY", "").strip() or None
    if not path.is_file():
        raise Failure("fichier introuvable / file not found", EXIT_USAGE)
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise Failure(f"fichier trop volumineux ({size / 2**20:.1f} Mo > {MAX_FILE_MB} Mo) : découpez-le ou "
                      f"utilisez la skill locale / file too large ({size / 2**20:.1f} MB > {MAX_FILE_MB} MB): split "
                      f"it or use the local skill", EXIT_USAGE)
    deadline = time.monotonic() + timeout
    options = {"filename": upload_name(path),
               **_options(countries, profile, label_language, explain, rules, mode, disable)}
    for round_ in range(2):
        status, headers, body = with_retries(
            lambda: request("POST", f"{base}/v1/uploads", key, payload=options, timeout=deadline - time.monotonic()),
            deadline)
        ticket = _check(status, body, (201,), headers)
        if size > int(ticket.get("max_bytes", size)):
            raise Failure(f"fichier trop volumineux pour ce serveur ({size / 2**20:.1f} Mo > "
                          f"{int(ticket['max_bytes']) / 2**20:.0f} Mo) / file too large for this server")
        # URL reconstruite sur GDPRGUARDIAN_URL : rien ne part ailleurs / rebuilt on GDPRGUARDIAN_URL only.
        token = str(ticket["upload_url"]).rstrip("/").rsplit("/", 1)[-1]
        upload_id = urllib.parse.quote(str(ticket["upload_id"]), safe="")
        put_url = f"{base}/v1/uploads/{urllib.parse.quote(token, safe='')}"
        refused: list[int] = []

        def put(put_url: str = put_url, refused: list[int] = refused) -> tuple[int, dict[str, str], bytes]:
            answer = _put(put_url, path, size, key, deadline)
            refused.append(answer[0])
            return answer

        try:
            status, headers, body = with_retries(put, deadline)
            if status == 404 and any(code in _RETRY_STATUSES for code in refused[:-1]):
                # Un refus après traitement (quota de résultats non lus) consomme l'adresse d'envoi à usage unique :
                # nouvelle adresse une fois, sinon « occupé ». A refusal after processing (unread-results quota)
                # burns the single-use upload URL: one new URL, else "busy".
                if round_ == 0 and time.monotonic() + _RETICKET_WAIT_S < deadline:
                    time.sleep(_RETICKET_WAIT_S)
                    continue
                raise Failure(f"HTTP 429 too_many_unread_results: {_BUSY_HINT}", EXIT_BUSY)
            # 202 : fichier reçu, traitement en arrière-plan (200 : ancien service, traitement fini).
            # 202: file received, processing in the background (200: older service, processing done).
            _check(status, body, (200, 202), headers)
            return _read_pages(base, upload_id, key, deadline, sink)
        except BaseException:
            # Résultat partiel effacé tout de suite (sinon à l'expiration) / partial result wiped now (else on expiry).
            with contextlib.suppress(Failure, OSError):
                request("DELETE", f"{base}/v1/results/{upload_id}", key, timeout=10)
            raise
    raise AssertionError("unreachable")


def _read_pages(base: str, upload_id: str, key: str | None, deadline: float,
                sink: Callable[[str], None] | None) -> tuple[str, dict[str, Any]]:
    pages: list[str] = []
    report: dict[str, Any] = {}
    page, delay = 1, 0.5
    while True:
        url = f"{base}/v1/results/{upload_id}?page={page}&page_chars={PAGE_CHARS}"
        status, headers, body = with_retries(
            lambda url=url: request("GET", url, key, timeout=deadline - time.monotonic()), deadline)
        if status == 202:
            # Traitement en cours : étape et avancement sur stderr, délai conseillé par le service.
            # Still processing: stage and progress on stderr, delay advised by the service.
            progress = _json(body)
            if time.monotonic() > deadline:
                raise Failure("délai dépassé / timed out")
            _progress(progress)
            advised = progress.get("retry_after_s")
            wait = min(max(float(advised), 0.5), 10.0) if isinstance(advised, (int, float)) else delay
            time.sleep(min(wait, max(0.0, deadline - time.monotonic())))
            delay = min(delay * 2, 5.0)
            continue
        result = _check(status, body, (200,), headers)
        markdown = str(result.get("markdown") or "")
        if sink is None:
            pages.append(markdown)
        else:
            sink(markdown)
        report = result.get("report") or report
        next_page = result.get("next_page")
        if not next_page:
            return "".join(pages), report
        page = int(next_page)


def _progress(progress: Mapping[str, Any]) -> None:
    """Avancement sur stderr (étape, pages, pourcentage ; aucune donnée du document) / progress on stderr."""
    stage = progress.get("stage")
    if not isinstance(stage, str) or not stage.replace("_", "").isalpha():
        return
    parts = [stage[:20]]
    done, total, percent = progress.get("pages_done"), progress.get("pages_total"), progress.get("percent")
    if isinstance(total, int) and total > 0 and isinstance(done, int):
        parts.append(f"page {done}/{total}")
    if isinstance(percent, int):
        parts.append(f"{percent} %")
    print(f"gdprguardian: {', '.join(parts)}", file=sys.stderr)


class Output:
    """Sortie standard pour un petit résultat, fichier sinon / stdout for a small result, else a file.

    Écriture dans un fichier « .part » renommé à la fin : jamais de résultat tronqué / written to a .part file
    renamed at the end: never a truncated result.
    """

    def __init__(self, target: Path | None, source: Path | None) -> None:
        self.target = target
        self.source = source
        self.buffer: list[str] = []
        self.size = 0
        self.handle: Any = None
        self.part: Path | None = None
        self.auto = False

    def check(self) -> None:
        """Avant tout envoi : la sortie n'écrase jamais l'original / before sending: never overwrite the original."""
        target, source = self.target, self.source
        if target is not None and source is not None and target.exists() and target.resolve() == source.resolve():
            raise Failure("la sortie écraserait l'original / output would overwrite the original", EXIT_USAGE)

    def _open(self, target: Path) -> None:
        self.part = target.with_name(target.name + ".part")
        self.handle = self.part.open("w", encoding="utf-8", newline="")
        self.target = target

    def write(self, text: str) -> None:
        if self.handle is None and self.target is not None:
            self._open(self.target)
        if self.handle is None and self.size + len(text) > PRINT_LIMIT:
            fd, name = tempfile.mkstemp(prefix="gdprguardian-", suffix=".anon.md")
            os.close(fd)
            self.auto = True
            self._open(Path(name))
        if self.handle is None:
            self.buffer.append(text)
        else:
            for chunk in self.buffer:
                self.handle.write(chunk)
            self.buffer.clear()
            self.handle.write(text)
        self.size += len(text)

    def close(self) -> None:
        if self.handle is None and self.target is not None:
            self._open(self.target)
        if self.handle is None:
            sys.stdout.buffer.write("".join(self.buffer).encode("utf-8"))
            sys.stdout.buffer.flush()
            return
        for chunk in self.buffer:
            self.handle.write(chunk)
        self.handle.close()
        assert self.part is not None and self.target is not None
        os.replace(self.part, self.target)
        notice = f"[gdprguardian] Markdown anonymisé écrit / anonymised Markdown written: {self.target} " \
                 f"({self.size} caractères/chars)"
        if self.auto:
            # Trop long pour la sortie standard : le chemin, à lire par parties / too long for stdout: read in parts.
            print(notice + " ; lisez-le par parties / read it in parts")
        else:
            print(f"gdprguardian: {notice}", file=sys.stderr)

    def discard(self) -> None:
        if self.handle is not None:
            self.handle.close()
            assert self.part is not None
            with contextlib.suppress(OSError):
                self.part.unlink()


def _report(report: dict[str, Any]) -> None:
    # `explain` : règle et raison de chaque balise, jamais la valeur / rule and reason of each placeholder, never value.
    summary = {k: report[k] for k in ("entities", "total_replaced", "countries", "notice", "warnings", "explain")
               if k in report}
    sys.stderr.buffer.write((json.dumps(summary, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stderr.buffer.flush()


def _read_text(source: str) -> str:
    try:
        raw = sys.stdin.buffer.read() if source == "-" else Path(source).read_bytes()
    except OSError:
        raise Failure("texte illisible / unreadable text", EXIT_USAGE) from None
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Failure("texte : UTF-8 attendu (sinon, anonymisez le fichier) / text: UTF-8 expected (else, anonymise "
                      "the file)", EXIT_USAGE) from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    parser.add_argument("file", nargs="?", help="document à anonymiser / document to anonymise")
    parser.add_argument("--text", metavar="SOURCE",
                        help="texte UTF-8 à anonymiser : un fichier, ou « - » pour l'entrée standard / UTF-8 text: a "
                             "file, or '-' for standard input")
    parser.add_argument("--countries", default="FR",
                        help="packs pays, ex. FR (défaut), FR,BE, all, auto (expérimental) / country packs")
    parser.add_argument("--mode", choices=MODES,
                        help="fort (défaut : tout ce qu'on peut, codes compris), essentiel (codes métier lisibles), "
                             "personnalise (le fort moins --disable) / fort (default), essentiel, personnalise")
    parser.add_argument("--disable", help="catégories laissées en clair, séparées par des virgules (mode "
                                          "personnalise ; jamais secrets) / categories left in clear (custom mode)")
    parser.add_argument("--profile", choices=("fast", "standard", "strict"),
                        help="ancien réglage, déprécié : standard = essentiel, strict = fort / deprecated")
    parser.add_argument("--label-language", default="fr", choices=("fr", "en", "auto"))
    parser.add_argument("--rules", help="règles de l'organisation (JSON), envoyées au service avec le document ; "
                                        "jamais sans cette option / organisation rules (JSON), sent to the service "
                                        "with the document; never without this option")
    parser.add_argument("--explain", action="store_true",
                        help="règle et raison de chaque balise, dans le rapport sur stderr / rule and reason of each "
                             "placeholder, in the report on stderr")
    parser.add_argument("-o", "--output", help="écrire le Markdown dans ce fichier / write the Markdown to a file")
    parser.add_argument("--report", action="store_true", help="résumé du rapport sur stderr / report on stderr")
    parser.add_argument("--timeout", type=float, default=900.0, help="secondes, en tout / seconds, overall")
    parser.add_argument("--limits", action="store_true", help="service et limites / service and limits")
    return parser


def utf8_streams() -> None:
    """Sorties en UTF-8 même redirigées sous Windows (sinon cp1252) / UTF-8 output even when piped on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):
                reconfigure(encoding="utf-8", errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.limits:
        try:
            url = base_url(os.environ)
        except Failure as failure:
            print(f"gdprguardian: {failure}", file=sys.stderr)
            return failure.code
        print(json.dumps({"service": url, "max_file_mb": MAX_FILE_MB, "max_text_chars": MAX_TEXT_CHARS,
                          "public": url == PUBLIC_URL}))
        return EXIT_OK
    if (args.file is None) == (args.text is None):
        parser.error("un document OU --text / a document OR --text")
    source = Path(args.file) if args.file is not None else None
    output = Output(Path(args.output) if args.output else None, source)
    try:
        output.check()
        rules = load_rules(args.rules)
        if rules is None and unsent_rules(os.environ):
            print("gdprguardian: règles du projet NON envoyées ; --rules <fichier> pour les envoyer au service / "
                  "project rules NOT sent; pass --rules <file> to send them to the service", file=sys.stderr)
        disable = [item.strip() for item in args.disable.split(",") if item.strip()] if args.disable else None
        settings = {"countries": args.countries, "profile": args.profile, "label_language": args.label_language,
                    "rules": rules, "explain": args.explain, "mode": args.mode, "disable": disable}
        if source is None:
            text, report = anonymize_text(_read_text(args.text), os.environ, timeout=min(args.timeout, 300.0),
                                          **settings)
            output.write(text)
        else:
            _, report = anonymize(source, os.environ, timeout=args.timeout, sink=output.write, **settings)
        output.close()
    except Failure as failure:
        output.discard()
        print(f"gdprguardian: {failure}", file=sys.stderr)
        return failure.code
    except Exception as exc:
        output.discard()
        # Jamais de trace : l'IA lit stderr / never a traceback, the AI reads stderr (timeout, reset...).
        print(f"gdprguardian: échec / failed ({type(exc).__name__})", file=sys.stderr)
        return EXIT_ERROR
    # Avertissements du service (textes fixes : OCR de mauvaise qualité, contenus écartés...) toujours signalés.
    # Service warnings (fixed texts: low-quality OCR, dropped content...) always shown.
    warnings = report.get("warnings")
    for warning in warnings if isinstance(warnings, list) else []:
        if isinstance(warning, str):
            print(f"gdprguardian: avertissement / warning: {warning[:300]}", file=sys.stderr)
    if args.report or args.explain:
        _report(report)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
