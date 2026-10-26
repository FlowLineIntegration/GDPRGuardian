"""Local preview of the website, before (or without) the Rust daemon. Standard library only.

    python site/tools/preview.py            # http://127.0.0.1:8099/ (French) and /en (English)
    python site/tools/preview.py --check    # render both pages, validate placeholders, print sizes, exit

It does what the daemon does, with sample live values (site/tools/preview-sample.json) and the quality figures the
daemon embeds (site/data/quality.json; the sample's "q" only if that file is missing):
- replaces {{live.*}} and {{q.*}} in site/templates/index.{fr,en}.html, formatted per language
  (French: narrow no-break space thousands "3 751", decimal comma "0,45"; English: "3,751", "0.45");
  any other {{...}} is an error, as in the daemon;
- serves site/static/** at /assets/<path> and site/static/favicon.svg at /favicon.svg; and the launch video
  (video/out/<name>) at /media/<name>, as nginx does on the site hosts, but whole (no byte ranges: Safari needs the
  real nginx, see deploy/server/nginx-site.conf);
- streams /api/live (Server-Sent Events, event "stats" every 2 s, slowly changing values) and /api/stats;
- forwards POST /v1/... to a local service (--api, default http://127.0.0.1:8000), as nginx does on the site hosts
  (Sec-Fetch-Site included, so the service's cross-site check applies), so the workspace anonymises for real;
- forces errors to see how the page copes: --force-status 429 (or 403, 408, 413, 415, 422, 502, 503, 504) answers
  /v1/ calls with that error (429 and 503 with a Retry-After), --force-code picks the error code, --force-times N
  forces only the next N calls; the same at run time, preview only: GET /__force?status=429&times=2&retry=3
  (&code=too_many_unread_results), and GET /__force?status=0 to stop forcing;
- sends the daemon's security headers (same Content-Security-Policy), so CSP mistakes show up here.
Byte sizes: base 1024, one decimal from 1 KB ("12,4 Mo" / "12.4 MB"), no-break space before the unit.
Nothing is logged; forwarded bodies are held in memory for the time of the call only.

A local service for the preview, in public mode like production (no key; without a client-address header the
limiter sees the TCP peer, so 1 running + 2 queued per client apply). Run it in Linux or WSL:
    GDPRGUARDIAN_PUBLIC=1 gdprguardian serve --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse
import gzip
import html
import http.client
import json
import mimetypes
import random
import re
import sys
import threading
import time
import urllib.parse
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
TEMPLATES = SITE / "templates"
STATIC = SITE / "static"
MEDIA = SITE.parent / "video" / "out"
SAMPLE = Path(__file__).resolve().with_name("preview-sample.json")
QUALITY = SITE / "data" / "quality.json"

CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; "
       "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
LIVE_NAMES = {"uses_hour", "uses_hour_protocol", "bytes_hour", "docs_total", "docs_protocol", "bytes_total",
              "visitors_total", "visitors_today", "cpu_percent", "ram_used", "ram_total", "ram_percent"}
# Filled by the public protocol run; until then the literal string "—", which the page shows as "not measured yet"
# (CSS on data-v), never as a number.
PENDING_KEYS = {"confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct", "protocol_docs",
                "protocol_families", "real_corpora", "real_docs", "protocol_date", "protocol_engine"}
# Pending keys whose measured value is a string: an ISO date, a version.
PENDING_STRINGS = {"protocol_date": re.compile(r"\d{4}-\d{2}-\d{2}"),
                   "protocol_engine": re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,31}")}
Q_KEYS = {"tests_windows", "tests_linux", "tests_offline_image", "parity_docs", "eval_docs", "eval_mentions",
          "eval_decoys", "redteam_docs", "redteam_operators", "docs_tested", "recall_structured_pct",
          "precision_structured_pct", "recall_direct_pct", "docs_leak_structured_pct", "docs_leak_direct_pct",
          "overmask_pct",
          "ms_per_doc", "mb_per_s", "text_10mb_s", "service_p50_ms", "service_p99_ms", "pdf100_s", "image_mb",
          "core_mb", "measured_on"} | PENDING_KEYS
PENDING = "—"
# Raw bytes (the daemon serves them Brotli-compressed, about a third of that; gzip size printed as a guide).
BUDGETS = {"html": 45 * 1024, "css": 32 * 1024, "js": 30 * 1024, "fonts": 90 * 1024, "font_files": 3}
SCRIPTS = ("live.js", "cockpit.js")
# Layout rules that browser checks found missing once; a stylesheet without them is a regression.
CSS_GUARDS = (
    (r"\.cout>\.hd\{flex:none\}",
     "result header must not shrink: Copy and Download stay reachable on phones and tablets (390 and 1024 px)"),
    (r"\.ws:has\(\.pn:target\)>:is\(\.cout,\.rail\)\{visibility:hidden\}",
     "an open panel hides what it covers: no keyboard focus behind it (WCAG 2.4.11)"),
    (r"\.col\{position:relative[;}]",
     "columns contain their visually hidden elements: no page scroll bar on short screens (1366 x 768)"),
)
# The service's own codes and messages (src/gdprguardian/server/errors.py, deploy/server/nginx-service-errors.conf).
FORCED_ERRORS = {
    403: ("cross_site_request", "Requête inter-sites refusée / cross-site request refused"),
    408: ("upload_timeout", "Envoi trop lent, interrompu / upload too slow, aborted"),
    413: ("payload_too_large", "Fichier trop volumineux : 50 Mo au plus / file too large: 50 MB at most"),
    415: ("unsupported_format", "Format de document non pris en charge / unsupported document format"),
    422: ("encrypted_document", "Document chiffré ou protégé par mot de passe / encrypted or password-protected document"),
    429: ("rate_limited", "Trop de requêtes, réessayez après Retry-After / too many requests, retry after Retry-After"),
    502: ("bad_gateway", "Service indisponible / service unavailable"),
    503: ("service_busy", "Capacité temporairement atteinte, réessayez / capacity temporarily reached, retry"),
    504: ("gateway_timeout", "Délai dépassé / gateway timeout"),
}
MONTHS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
}
UNITS = {"fr": ["o", "Ko", "Mo", "Go", "To"], "en": ["B", "KB", "MB", "GB", "TB"]}
PLACEHOLDER = re.compile(r"\{\{\s*([^{}]*?)\s*\}\}")
NNBSP, NBSP = " ", " "


# ---------------------------------------------------------------------------------------------- formatting

def fmt_number(value: int | float | Decimal, lang: str, decimals: int | None = None) -> str:
    """Integer with thousands separators, or decimal number with the given (or its own) decimals."""
    if decimals is None:
        if isinstance(value, Decimal):
            exponent = value.as_tuple().exponent
            decimals = -exponent if isinstance(exponent, int) and exponent < 0 else 0
        elif isinstance(value, float) and not value.is_integer():
            decimals = len(repr(value).split(".")[1])
        else:
            decimals = 0
    text = f"{value:,.{decimals}f}"
    if lang == "fr":
        text = text.replace(",", "\x00").replace(".", ",").replace("\x00", NNBSP)
    return text


def fmt_bytes(n: int, lang: str) -> str:
    value, i = float(n), 0
    while i < 4 and round(value, 1) >= 1024:
        value /= 1024
        i += 1
    number = fmt_number(int(value), lang) if i == 0 else fmt_number(value, lang, 1)
    return f"{number}{NBSP}{UNITS[lang][i]}"


def fmt_date(iso: str, lang: str) -> str:
    year, month, day = (int(p) for p in iso.split("-"))
    if lang == "fr":
        return f"{'1er' if day == 1 else day} {MONTHS['fr'][month - 1]} {year}"
    return f"{day} {MONTHS['en'][month - 1]} {year}"


def live_values(stats: dict, lang: str) -> dict[str, str]:
    used, total = stats["ram_used_bytes"], stats["ram_total_bytes"]
    return {
        "uses_hour": fmt_number(stats["uses_hour"], lang),
        "uses_hour_protocol": fmt_number(stats["uses_hour_protocol"], lang),
        "bytes_hour": fmt_bytes(stats["bytes_hour"], lang),
        "docs_total": fmt_number(stats["docs_total"], lang),
        "docs_protocol": fmt_number(stats["docs_protocol"], lang),
        "bytes_total": fmt_bytes(stats["bytes_total"], lang),
        "visitors_total": fmt_number(stats["visitors_total"], lang),
        "visitors_today": fmt_number(stats["visitors_today"], lang),
        "cpu_percent": fmt_number(float(stats["cpu_percent"]), lang, 1),
        "ram_used": fmt_bytes(used, lang),
        "ram_total": fmt_bytes(total, lang),
        "ram_percent": fmt_number(used / total * 100 if total else 0.0, lang, 1),
        "since": fmt_date(stats["since"], lang),
    }


ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def quality_values(q: dict, lang: str) -> dict[str, str]:
    """Numbers per language; a bare ISO date in words ("25 octobre 2026"), as the daemon does."""
    out = {}
    for key, value in q.items():
        if key.startswith("_"):
            continue
        if isinstance(value, str):
            out[key] = fmt_date(value, lang) if ISO_DATE.fullmatch(value) else value
        else:
            out[key] = fmt_number(value, lang)
    return out


# ---------------------------------------------------------------------------------------------- state

class Simulation:
    """Slowly changing live values, around the sample. No protocol runs: the public campaign has not started, and
    a preview showing some would contradict the page (the sample's protocol counters stay at 0)."""

    def __init__(self, sample: dict) -> None:
        self.lock = threading.Lock()
        self.s = {k: v for k, v in sample.items()}
        self.cpu0 = float(sample["cpu_percent"])
        self.rng = random.Random(7)

    def tick(self) -> dict:
        with self.lock:
            s, r = self.s, self.rng
            if r.random() < 0.35:
                n = r.randint(1, 3)
                size = sum(r.randint(2_000, 900_000) for _ in range(n))
                s["uses_hour"] += n
                s["docs_total"] += n
                s["bytes_hour"] += size
                s["bytes_total"] += size
            elif r.random() < 0.2 and s["uses_hour"] > 0:
                s["uses_hour"] -= 1
                s["uses_hour_protocol"] = min(s["uses_hour_protocol"], s["uses_hour"])
                s["bytes_hour"] = max(0, s["bytes_hour"] - r.randint(2_000, 400_000))
            if r.random() < 0.12:
                s["visitors_total"] += 1
                s["visitors_today"] += 1
            # A random walk pulled back towards the sample value, so a long preview does not drift to a full CPU.
            pull = (self.cpu0 - s["cpu_percent"]) * 0.1
            s["cpu_percent"] = round(min(95.0, max(0.5, s["cpu_percent"] + r.uniform(-1.6, 1.6) + pull)), 1)
            s["ram_used_bytes"] = int(min(s["ram_total_bytes"] * 0.9,
                                          max(1 << 30, s["ram_used_bytes"] + r.randint(-40, 42) * (1 << 20))))
            return dict(s, updated=int(time.time()))

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.s, updated=int(time.time()))


# ---------------------------------------------------------------------------------------------- rendering

class TemplateError(Exception):
    pass


def render(lang: str, stats: dict, quality: dict) -> str:
    template = (TEMPLATES / f"index.{lang}.html").read_text(encoding="utf-8")
    values = {f"live.{k}": v for k, v in live_values(stats, lang).items()}
    values.update({f"q.{k}": v for k, v in quality_values(quality, lang).items()})
    unknown: list[str] = []

    def sub(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            unknown.append(key)
            return match.group(0)
        return html.escape(values[key], quote=True)

    page = PLACEHOLDER.sub(sub, template)
    if unknown:
        raise TemplateError(f"index.{lang}.html: unknown placeholder(s): {', '.join(sorted(set(unknown)))}")
    if "{{" in page or "}}" in page:
        raise TemplateError(f"index.{lang}.html: malformed placeholder left after rendering")
    return page


def load_quality(sample: dict) -> tuple[dict, str]:
    """The quality figures the daemon embeds (site/data/quality.json), else the sample's; and their source."""
    if QUALITY.is_file():
        return json.loads(QUALITY.read_text(encoding="utf-8"), parse_float=Decimal), "site/data/quality.json"
    return sample["q"], "site/tools/preview-sample.json (site/data/quality.json missing)"


def check(sample: dict, quality: dict, source: str) -> int:
    """Validate both templates; print sizes. Returns a process exit code."""
    problems = 0
    print(f"quality figures from {source}")
    for name, q in (("sample q", sample["q"]), (source, quality)):
        q_keys = {k for k in q if not k.startswith("_")}
        if q_keys != Q_KEYS:
            print(f"{name}: keys differ from the contract: missing {sorted(Q_KEYS - q_keys)}, extra {sorted(q_keys - Q_KEYS)}")
            problems += 1
        for key in sorted(PENDING_KEYS & q_keys):
            value, shape = q[key], PENDING_STRINGS.get(key)
            if value == PENDING:
                continue
            if shape is not None and not (isinstance(value, str) and shape.fullmatch(value)):
                print(f"{name}: {key} must be {shape.pattern!r} or the pending mark {PENDING!r}, not {value!r}")
                problems += 1
            elif shape is None and isinstance(value, str):
                print(f"{name}: {key} must be a number or the pending mark {PENDING!r}, not {value!r}")
                problems += 1
        pending = sorted(k for k in PENDING_KEYS & q_keys if q[k] == PENDING)
        if pending:
            print(f"{name}: shown as 'not measured yet': {', '.join(pending)}")
    pages = {}
    for lang in ("fr", "en"):
        try:
            pages[lang] = render(lang, sample["live"], quality)
        except (TemplateError, OSError) as exc:
            print(f"ERROR {exc}")
            problems += 1
            continue
        template = (TEMPLATES / f"index.{lang}.html").read_text(encoding="utf-8")
        used = set(PLACEHOLDER.findall(template))
        missing_q = sorted(k for k in Q_KEYS if f"q.{k}" not in used)
        names = set(re.findall(r'data-live="([^"]*)"', template)) | set(re.findall(r'data-meter="([^"]*)"', template))
        if names - LIVE_NAMES:
            print(f"ERROR index.{lang}.html: data-live/data-meter names outside the contract: {sorted(names - LIVE_NAMES)}")
            problems += 1
        if re.search(r"<style|\sstyle=|\son[a-z]+=|<script(?![^>]*\bsrc=)", template, re.I):
            print(f"ERROR index.{lang}.html: inline style, inline script or on* handler (blocked by the CSP)")
            problems += 1
        fetched = r"""(?:\ssrc=|<link\s[^>]*rel="(?:stylesheet|preload|modulepreload|icon|manifest)"[^>]*\shref=)"""
        if re.search(fetched + r"""["']?(?:https?:)?//""", template):
            print(f"ERROR index.{lang}.html: resource loaded from another origin (the CSP allows 'self' only)")
            problems += 1
        if lang == "fr":  # French spacing: narrow no-break space (U+202F) before : ; ? ! % » and after «
            loose = re.findall(r".{0,12}(?:[  ][:;?!%»]|«[  ]).{0,12}", "".join(re.findall(r">([^<]*)", template)))
            if loose:
                print(f"WARNING index.fr.html: {len(loose)} ordinary space(s) in French punctuation, e.g. {loose[:3]}")
        # Every pending-capable value must sit in an element that can show "not measured yet" instead.
        for match in re.finditer(r"\{\{\s*q\.(" + "|".join(sorted(PENDING_KEYS)) + r")\s*\}\}", template):
            if template[:match.start()].endswith('data-v="'):
                continue
            before, after = template[max(0, match.start() - 600):match.start()], template[match.end():match.end() + 400]
            if 'data-v="{{q.' not in before or 'class="pd"' not in after:
                print(f"ERROR index.{lang}.html: {match.group(0)} outside a pending-aware element (class q, data-v, .pd)")
                problems += 1
        size = len(template.encode("utf-8"))
        rendered = len(pages[lang].encode("utf-8"))
        over = max(size, rendered) > BUDGETS["html"]
        print(f"index.{lang}.html: template {size} bytes, rendered {rendered} bytes"
              f"{'  OVER BUDGET' if over else ''} (budget {BUDGETS['html']}); q keys not shown: {missing_q or 'none'}")
        problems += over
    css_text = (STATIC / "site.css").read_text(encoding="utf-8")
    css = len(css_text.encode("utf-8"))
    print(f"site.css: {css} bytes{'  OVER BUDGET' if css > BUDGETS['css'] else ''} (budget {BUDGETS['css']})")
    problems += css > BUDGETS["css"]
    for pattern, why in CSS_GUARDS:
        if not re.search(pattern, css_text):
            print(f"ERROR site.css: missing {pattern!r}: {why}")
            problems += 1
    js = {name: (STATIC / name).read_bytes() for name in SCRIPTS}
    total = sum(len(v) for v in js.values())
    packed = sum(len(gzip.compress(v, 9, mtime=0)) for v in js.values())
    print(f"scripts: {total} bytes ({', '.join(f'{k} {len(v)}' for k, v in js.items())}), gzip {packed}"
          f"{'  OVER BUDGET' if total > BUDGETS['js'] else ''} (budget {BUDGETS['js']} raw)")
    problems += total > BUDGETS["js"]
    print(f"favicon.svg: {(STATIC / 'favicon.svg').stat().st_size} bytes")
    fonts = sorted((STATIC / "fonts").glob("*.woff2"))
    total = sum(f.stat().st_size for f in fonts)
    over = len(fonts) > BUDGETS["font_files"] or total > BUDGETS["fonts"]
    print(f"fonts: {len(fonts)} woff2, {total} bytes ({', '.join(f'{f.name} {f.stat().st_size}' for f in fonts)})"
          f"{'  OVER BUDGET' if over else ''} (budget {BUDGETS['font_files']} files, {BUDGETS['fonts']} bytes)")
    problems += over
    licences = sorted(p.name for p in (STATIC / "fonts").glob("LICENSE*.txt"))
    print(f"font licences: {', '.join(licences) or 'none'}")
    problems += len(licences) < len(fonts)
    print("OK" if not problems else f"{problems} problem(s)")
    return 1 if problems else 0


# ---------------------------------------------------------------------------------------------- server

class Force:
    """Forced /v1/ answers, preview only: status (None: forward), code, Retry-After, how many calls (None: every
    call), and a delay added before each forwarded call (to watch a queue). Set by options or GET /__force."""

    lock = threading.Lock()
    status: int | None = None
    code: str | None = None
    retry: int = 7
    times: int | None = None
    delay: float = 0.0

    @classmethod
    def take(cls) -> tuple[int, str, str, int] | None:
        with cls.lock:
            if not cls.status:
                return None
            if cls.times is not None:
                if cls.times <= 0:
                    cls.status = None
                    return None
                cls.times -= 1
            code, message = FORCED_ERRORS.get(cls.status, ("http_error", "http error"))
            return cls.status, cls.code or code, message, cls.retry

    @classmethod
    def set(cls, query: dict) -> dict:
        def number(name: str, kind: type, default):
            try:
                return kind(query[name][0]) if name in query else default
            except ValueError:
                return default
        with cls.lock:
            cls.status = number("status", int, cls.status) or None
            cls.code = query["code"][0] if "code" in query else None
            cls.retry = number("retry", int, cls.retry)
            cls.times = number("times", int, None)
            cls.delay = max(0.0, number("delay", float, cls.delay))
            return {"status": cls.status, "code": cls.code, "retry": cls.retry, "times": cls.times, "delay": cls.delay}


class Handler(BaseHTTPRequestHandler):
    server_version = "preview"
    sys_version = ""
    sim: Simulation
    quality: dict
    api: urllib.parse.SplitResult

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - no access log, like the daemon
        pass

    def _headers(self, status: int, ctype: str, length: int | None = None, cache: str = "no-store") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", cache)
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self._headers(status, ctype, len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path in ("/", "/index.html", "/en", "/en/"):
            lang = "en" if path.startswith("/en") else "fr"
            try:
                page = render(lang, self.sim.snapshot(), self.quality)
            except TemplateError as exc:
                self._send(500, f"Template error: {exc}\n".encode(), "text/plain; charset=utf-8")
                return
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/stats":
            self._send(200, json.dumps(self.sim.snapshot()).encode(), "application/json")
        elif path == "/api/live":
            self._stream()
        elif path == "/__force":  # preview only: forced /v1/ answers at run time
            state = Force.set(urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query))
            self._send(200, json.dumps(state).encode(), "application/json")
        elif path == "/favicon.svg":
            self._file(STATIC / "favicon.svg")
        elif path.startswith("/assets/"):
            target = (STATIC / path[len("/assets/"):]).resolve()
            if not target.is_relative_to(STATIC.resolve()):
                self._send(404, b"Not found\n", "text/plain; charset=utf-8")
                return
            self._file(target)
        elif path.startswith("/media/") and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", path[len("/media/"):]):
            self._file(MEDIA / path[len("/media/"):])
        else:
            self._send(404, b"Not found\n", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        """Same-origin API, as nginx forwards /v1/ on the site hosts: the body goes to the local service as is."""
        if not self.path.startswith("/v1/"):
            self._send(405, b"405\n", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else b""
        forced = Force.take()
        if forced:
            status, code, message, retry = forced
            payload = json.dumps({"error": {"code": code, "message": message}}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            if status in (429, 503):
                self.send_header("Retry-After", str(retry))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        if Force.delay:
            time.sleep(Force.delay)
        headers = {"Content-Length": str(len(body)), "Host": self.api.netloc}
        for name in ("Content-Type", "Sec-Fetch-Site"):
            if self.headers.get(name):
                headers[name] = self.headers[name]
        try:
            # Comme le proxy_read_timeout de Nginx / like nginx's proxy_read_timeout (600 s).
            conn = http.client.HTTPConnection(self.api.hostname, self.api.port or 80, timeout=600)
            conn.request("POST", self.path, body, headers)
            answer = conn.getresponse()
            data = answer.read()
            status, ctype, retry = answer.status, answer.getheader("Content-Type"), answer.getheader("Retry-After")
            conn.close()
        except OSError:
            payload = b'{"error":{"code":"bad_gateway","message":"service local injoignable / local service unreachable"}}'
            self._send(502, payload, "application/json")
            return
        self.send_response(status)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        if retry:
            self.send_header("Retry-After", retry)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _file(self, target: Path) -> None:
        if not target.is_file():
            self._send(404, b"Not found\n", "text/plain; charset=utf-8")
            return
        ctype = {".woff2": "font/woff2", ".svg": "image/svg+xml", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".txt": "text/plain; charset=utf-8"}.get(
            target.suffix, mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def _stream(self) -> None:
        self._headers(200, "text/event-stream; charset=utf-8")
        if self.command == "HEAD":
            return
        try:
            self.wfile.write(b"retry: 5000\n\n")
            payload = self.sim.snapshot()
            while True:
                self.wfile.write(f"event: stats\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n".encode())
                self.wfile.flush()
                time.sleep(2)
                payload = self.sim.tick()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--check", action="store_true", help="validate the templates and print sizes, then exit")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="local service that receives POST /v1/...")
    parser.add_argument("--force-status", type=int, choices=sorted(FORCED_ERRORS),
                        help="answer /v1/ calls with this error (429 and 503 with Retry-After)")
    parser.add_argument("--force-code", help="error code of the forced answer (default: the service's for the status)")
    parser.add_argument("--force-times", type=int, help="force only the next N calls (default: every call)")
    parser.add_argument("--retry-after", type=int, default=7, help="seconds sent with a forced 429 or 503")
    parser.add_argument("--delay", type=float, default=0.0, help="seconds added before each forwarded call")
    args = parser.parse_args()
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"), parse_float=Decimal)
    sample["live"] = {k: float(v) if isinstance(v, Decimal) else v for k, v in sample["live"].items()}
    quality, source = load_quality(sample)
    if args.check:
        return check(sample, quality, source)
    for lang in ("fr", "en"):  # fail fast on a broken template
        try:
            render(lang, sample["live"], quality)
        except TemplateError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
    Handler.sim = Simulation(sample["live"])
    Handler.quality = quality
    Handler.api = urllib.parse.urlsplit(args.api)
    Force.status, Force.code, Force.times = args.force_status, args.force_code, args.force_times
    Force.retry, Force.delay = args.retry_after, max(0.0, args.delay)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    print(f"Preview: http://127.0.0.1:{args.port}/ (français)  http://127.0.0.1:{args.port}/en (English); "
          f"quality figures from {source}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
