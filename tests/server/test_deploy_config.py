"""Déploiement (deploy/server) : propriétés vérifiées sur les fichiers livrés, clé de limite IPv6 de Nginx comprise.

Deployment (deploy/server): properties checked on the shipped files, Nginx's IPv6 limit key included. Le
déroulé réel (Nginx dans Docker devant le service) est fait par le banc de bout en bout ; ici, ce qui se lit.
The real run (Nginx in Docker in front of the service) is done by the end-to-end bench; here, what can be read.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import random
import re
from pathlib import Path

import pytest
from server_testkit import REPO

from gdprguardian import __version__
from gdprguardian.server.config import ServerConfig
from gdprguardian.server.errors import CrossSiteRefused, RateLimited, ServiceBusy, file_too_large
from gdprguardian.server.middleware import _FETCH_SITES

DEPLOY = REPO / "deploy" / "server"
SERVICE_SNIPPETS = ("gdprguardian-service-headers.conf", "gdprguardian-service-proxy.conf",
                    "gdprguardian-service-errors.conf")


def read(name: str) -> str:
    return (DEPLOY / name).read_text(encoding="utf-8")


def _unquoted(text: str) -> list[bool]:
    """Pour chaque caractère : hors guillemets ? (une ligne à la fois) / per character: outside quotes?"""
    flags, quote = [], ""
    for char in text:
        if char == "\n":
            quote = ""
            flags.append(True)
        elif quote:
            flags.append(False)
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
            flags.append(False)
        else:
            flags.append(True)
    return flags


def strip_comments(text: str) -> str:
    """Retire les commentaires hors guillemets / removes comments outside quotes."""
    lines = []
    for line in text.splitlines():
        flags = _unquoted(line)
        cut = next((i for i, char in enumerate(line) if char == "#" and flags[i]), len(line))
        lines.append(line[:cut])
    return "\n".join(lines)


def blocks(text: str, head: str) -> list[str]:
    """Blocs `head { … }` de premier niveau, accolades hors guillemets appariées / top-level `head { … }` blocks."""
    text = strip_comments(text)
    flags = _unquoted(text)
    found = []
    for match in re.finditer(rf"(?m)^\s*{head}\s*\{{", text):
        depth, end = 0, len(text)
        for index in range(match.end() - 1, len(text)):
            if not flags[index]:
                continue
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    end = index
                    break
        found.append(text[match.end():end])
    return found


def directives(block: str) -> list[str]:
    """Directives, séparées par « ; » ou une accolade hors guillemets / directives, split outside quotes."""
    text = strip_comments(block)
    flags = _unquoted(text)
    parts, current = [], []
    for char, free in zip(text, flags, strict=True):
        if free and char in ";{}":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return [" ".join(part.split()) for part in parts if part.strip()]


SITE = blocks(read("nginx-site.conf"), "server")
ACME = blocks(read("nginx-site-acme.conf"), "server")


def server(names: str, port: int = 443) -> str:
    matching = [block for block in SITE if f"server_name {names};" in " ".join(block.split())
                and f"listen {port}" in block]
    assert len(matching) == 1, names
    return matching[0]


# --- tous les server / every server block -----------------------------------------------------------------------


@pytest.mark.parametrize("block", SITE + ACME)
def test_every_server_hides_the_version_and_logs_nothing_with_addresses(block: str) -> None:
    lines = directives(block)
    assert "server_tokens off" in lines and "access_log off" in lines
    assert "error_log /var/log/nginx/gdprguardian.error.log emerg" in lines


def test_unknown_names_are_closed_at_both_doors() -> None:
    default_80, default_443 = (block for block in SITE if "default_server" in block)
    assert "return 444" in directives(default_80)
    assert {"ssl_reject_handshake on", "return 444"} <= set(directives(default_443))


def test_plain_http_for_the_api_serves_acme_only() -> None:
    api_80 = server("api.gdprguardian.com api.gardienrgpd.fr", 80)
    assert "return 444" in directives(api_80) and "return 301" not in api_80
    assert "location ^~ /.well-known/acme-challenge/" in " ".join(api_80.split())
    assert "client_max_body_size 0" in directives(api_80)


def test_plain_http_for_the_sites_redirects_pages_but_closes_the_service() -> None:
    # Un client configuré en http://gdprguardian.com/v1/… ne doit pas « marcher » par redirection : fermé (444).
    # A client set up with http://gdprguardian.com/v1/… must not "work" through a redirect: closed (444).
    site_80 = server("gdprguardian.com www.gdprguardian.com gardienrgpd.fr www.gardienrgpd.fr", 80)
    for location in (r"location \^~ /v1/", r"location \^~ /mcp"):
        found = blocks(site_80, location)
        assert len(found) == 1 and directives(found[0]) == ["return 444"], location
    assert directives(blocks(site_80, r"location /")[0]) == ["return 301 https://$host$request_uri"]
    assert "client_max_body_size 0" in directives(site_80)


SERVICE_GUARDS = ("limit_req zone=gdprguardian_api burst=40 nodelay", "limit_conn gdprguardian_api_conn 16",
                  "limit_conn gdprguardian_api_net 48", "limit_conn gdprguardian_api_total 1500",
                  "include /etc/nginx/snippets/gdprguardian-service-headers.conf",
                  "error_page 403 = @gdprguardian_cross_site", "error_page 429 = @gdprguardian_rate_limited",
                  "error_page 413 = @gdprguardian_too_large", "error_page 502 503 504 = @gdprguardian_unavailable")


def test_the_api_server_has_edge_limits_headers_and_json_errors() -> None:
    block = server("api.gdprguardian.com api.gardienrgpd.fr")
    api = directives(block)
    for expected in (*SERVICE_GUARDS, "client_header_timeout 10s", "client_body_timeout 15s",
                     "include /etc/nginx/snippets/gdprguardian-service-errors.conf"):
        assert expected in api, expected
    proxied = directives(blocks(block, r"location /")[0])
    assert proxied[:3] == ["if ($gdprguardian_cross_site)", "return 403", "include /etc/nginx/snippets/"
                                                                            "gdprguardian-service-proxy.conf"]


def test_the_sites_forward_v1_to_the_service_with_the_same_guards() -> None:
    site = server("gdprguardian.com gardienrgpd.fr")
    v1 = blocks(site, r"location /v1/")
    assert len(v1) == 1
    lines = directives(v1[0])
    for expected in (*SERVICE_GUARDS, "include /etc/nginx/snippets/gdprguardian-service-proxy.conf",
                     "client_max_body_size 51m", "if ($gdprguardian_cross_site)", "return 403"):
        assert expected in lines, expected
    assert lines.index("return 403") < lines.index("include /etc/nginx/snippets/gdprguardian-service-proxy.conf")
    # Le démon du site ne reçoit jamais l'adresse complète / the site daemon never gets the full address.
    for location in (*blocks(site, r"location /"), *blocks(site, r"location = /api/live")):
        assert 'proxy_set_header X-GG-Client ""' in directives(location)
        assert "proxy_set_header X-GG-IP $gdprguardian_ip" in directives(location)


# --- vidéo de lancement / launch video --------------------------------------------------------------------------

SITE_SRC = REPO / "site"
VIDEO_OUT = REPO / "video" / "out"
MEDIA_REF = re.compile(r"/media/([A-Za-z0-9._-]+)\?v=([0-9a-f]{8})\b")
# En-têtes de chaque réponse du démon (site/src/http.rs, secure()) / headers of every daemon response.
DAEMON_HEADERS = {
    "strict-transport-security": '"max-age=63072000"',
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "permissions-policy": '"camera=(), microphone=(), geolocation=()"',
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-resource-policy": "same-origin",
}


def daemon_csp() -> str:
    """CSP des pages du démon, lue dans son source (chaîne Rust sur plusieurs lignes) / the daemon's page CSP."""
    source = (SITE_SRC / "src" / "http.rs").read_text(encoding="utf-8")
    literal = re.search(r'pub const CSP_SITE: &str = "(.*?)";', source, re.S).group(1)  # type: ignore[union-attr]
    return re.sub(r"\\\n\s*", "", literal)


def media_location() -> str:
    found = blocks(server("gdprguardian.com gardienrgpd.fr"), r"location \^~ /media/")
    assert len(found) == 1
    return found[0]


def install_media_files() -> list[str]:
    listed = re.search(r"^MEDIA_FILES=\(([^)]*)\)", read("install.sh"), re.M)
    assert listed is not None
    return listed.group(1).split()


def nginx_media_names() -> set[str]:
    body = blocks(read("nginx-http.conf"), r"map \$uri \$gdprguardian_media")[0]
    entries = dict(line.strip().rstrip(";").rsplit(None, 1) for line in body.splitlines() if line.strip())
    assert entries.pop("default") == "0" and set(entries.values()) == {"1"}
    assert all(key.startswith("/media/") for key in entries)
    return {key.removeprefix("/media/") for key in entries}


def cited_media() -> dict[str, dict[str, str]]:
    """Fichiers de /media/ cités par chaque page, avec leur version (?v=) / /media/ files each page cites."""
    cited: dict[str, dict[str, str]] = {}
    for lang in ("fr", "en"):
        page = (SITE_SRC / "templates" / f"index.{lang}.html").read_text(encoding="utf-8")
        cited[lang] = dict(MEDIA_REF.findall(page))
        assert len(cited[lang]) == page.count("/media/"), f"index.{lang}.html : /media/ sans ?v= / without ?v="
    return cited


def test_the_media_list_is_one_list_everywhere() -> None:
    # Nginx (map), install.sh (copie) et les deux pages citent exactement les mêmes fichiers, chaque page dans sa
    # langue. Nginx (map), install.sh (copy) and both pages name exactly the same files, each page in its language.
    files = install_media_files()
    assert len(files) == len(set(files)) == 8
    cited = cited_media()
    assert set(files) == nginx_media_names() == set(cited["fr"]) | set(cited["en"])
    assert all(name.startswith("gardien-rgpd-lancement-fr") for name in cited["fr"])
    assert all(name.startswith("gdpr-guardian-launch-en") for name in cited["en"])
    for names in cited.values():  # vidéo, affiche, transcription, montage 4:5 / video, poster, transcript, 4:5 cut
        assert sorted(name.rsplit(".", 1)[1] for name in names) == ["mp4", "mp4", "png", "txt"]


def test_the_map_buckets_hold_the_longest_media_name() -> None:
    # Mesuré : sans map_hash_bucket_size, nginx -t refuse la table (« could not build map_hash ») sur une ligne de
    # cache de 64 octets. Case de ngx_hash : pointeur, longueur sur 2 octets et clé, alignés sur 8, plus le pointeur
    # nul de fin. Measured: without it, nginx -t refuses the table on a 64-byte cache line.
    http = strip_comments(read("nginx-http.conf"))
    size = int(re.search(r"^map_hash_bucket_size (\d+);", http, re.M).group(1))  # type: ignore[union-attr]
    assert http.index("map_hash_bucket_size") < http.index("map ")
    longest = max(len(f"/media/{name}") for name in nginx_media_names())
    assert (8 + 2 + longest + 7) // 8 * 8 + 8 <= size


def test_every_cited_media_file_exists_with_the_cited_version() -> None:
    # Nginx garde chaque fichier un an (immutable) : un nouveau rendu doit changer le ?v= des pages, sinon les
    # navigateurs garderaient l'ancien. Nginx caches every file a year (immutable): a new render must change the
    # pages' ?v=, or browsers would keep the old file.
    for lang, names in cited_media().items():
        for name, version in names.items():
            path = VIDEO_OUT / name
            assert path.is_file(), path
            assert hashlib.sha256(path.read_bytes()).hexdigest()[:8] == version, (
                f"index.{lang}.html : {name}?v={version} ne correspond plus au fichier / no longer matches the file")


def test_the_download_size_shown_is_the_file_size() -> None:
    # « MP4, 4,5 Mo » à côté du lien du montage 4:5, en base 1024 comme le reste du site / base 1024, like the site.
    for lang, unit, comma in (("fr", "Mo", ","), ("en", "MB", ".")):
        page = (SITE_SRC / "templates" / f"index.{lang}.html").read_text(encoding="utf-8")
        name, shown = re.search(r'/media/([\w.-]+-social\.mp4)\?v=\w+" download>MP4, ([\d.,]+)\xa0'
                                + unit + "<", page).groups()  # type: ignore[union-attr]
        size = (VIDEO_OUT / name).stat().st_size / 2**20
        assert shown == f"{size:.1f}".replace(".", comma), (lang, shown, size)


def test_the_sites_serve_the_media_from_nginx_with_the_daemon_headers() -> None:
    lines = directives(media_location())
    # Liste stricte d'abord, jamais le démon, fichiers du dossier d'install.sh / strict list first, never the daemon.
    assert lines[:2] == ["if ($gdprguardian_media = 0)", "return 404"]
    assert not [line for line in lines if line.startswith(("proxy_", "root", "try_files", "autoindex", "max_ranges"))]
    script = read("install.sh")
    media_dir = re.search(r"^MEDIA_DIR=(\S+)$", script, re.M).group(1)  # type: ignore[union-attr]
    old_page = re.search(r"^STATIC_PAGE=(\S+)$", script, re.M).group(1)  # type: ignore[union-attr]
    # Hors de l'ancienne page statique, que base retire quand Nginx ne la cite plus / apart from the old static page.
    assert f"alias {media_dir}/" in lines and old_page not in media_dir
    # Types fixés ici, quel que soit mime.types / types set here, whatever mime.types says.
    start = lines.index("types")
    assert lines[start + 1:start + 4] == ["video/mp4 mp4", "image/png png", "text/plain txt"]
    assert "charset utf-8" in lines  # text/plain; charset=utf-8 pour les transcriptions / for the transcripts
    # Cache d'un an pour les réponses réussies seulement (pas « always ») : une erreur n'est jamais gardée.
    # A year of caching for successful responses only (no "always"): an error is never kept.
    assert 'add_header Cache-Control "public, max-age=31536000, immutable"' in lines
    headers = {line.split()[1].lower(): line.split(None, 2)[2] for line in lines if line.startswith("add_header ")}
    for name, value in DAEMON_HEADERS.items():
        assert headers.get(name) == f"{value} always", name
    # La CSP du démon, mot pour mot : media-src 'self' pour la vidéo et l'affiche / the daemon's CSP, word for word.
    csp = daemon_csp()
    assert headers["content-security-policy"] == f'"{csp}" always'
    policy = {part.split()[0]: part.split()[1:] for part in csp.split(";") if part.strip()}
    assert policy["media-src"] == ["'self'"] and policy["img-src"] == ["'self'", "data:"]
    assert policy["default-src"] == ["'none'"]
    assert set(headers) == {*DAEMON_HEADERS, "content-security-policy", "cache-control"}


def test_the_preview_sends_the_daemon_csp() -> None:
    preview = (SITE_SRC / "tools" / "preview.py").read_text(encoding="utf-8")
    literal = re.search(r"^CSP = \((.*?)\)$", preview, re.M | re.S).group(1)  # type: ignore[union-attr]
    assert "".join(re.findall(r'"([^"]*)"', literal)) == daemon_csp()


def test_the_site_phase_installs_the_media_from_video_out() -> None:
    script = read("install.sh")
    assert 'site) site "${2:-}" "${3:-}" ;;' in script
    assert "local videos=${2:-$HERE/../../video/out}" in script
    # Contrôle avant tout changement, copie avant le nouveau démon / checked before any change, copied before the
    # new daemon.
    body = script[script.index("\nsite() {"):script.index("\n}\n", script.index("\nsite() {"))]
    assert body.index('check_media "$binary" "$videos"') < body.index('install_media "$videos"') < body.index(
        "/usr/local/bin/gdprguardian-site.new")
    assert "sha256sum" in script and "verify_media" in script and "-H 'Range: bytes=0-99'" in script


# --- extraits partagés / shared snippets ------------------------------------------------------------------------


def test_the_proxy_sets_the_client_address_and_hides_every_duplicated_header() -> None:
    proxy = directives(read("nginx-service-proxy.conf"))
    assert "proxy_set_header X-GG-Client $remote_addr" in proxy
    assert 'proxy_set_header X-GG-Local ""' in proxy  # jeton local jamais transmis du réseau / never from outside
    assert "proxy_set_header Host $gdprguardian_service_host" in proxy
    assert "proxy_redirect http:// https://" in proxy
    assert {"proxy_request_buffering off", "proxy_buffering off", "proxy_max_temp_file_size 0"} <= set(proxy)
    added = {line.split()[1].lower() for line in directives(read("nginx-service-headers.conf"))}
    hidden = {line.split()[1].lower() for line in proxy if line.startswith("proxy_hide_header")}
    assert added == hidden and "cache-control" in added and "strict-transport-security" in added


def test_security_headers_reach_nginx_errors_too() -> None:
    headers = directives(read("nginx-service-headers.conf"))
    assert headers and all(line.startswith("add_header ") and line.endswith(" always") for line in headers)
    assert "add_header Cache-Control no-store always" in headers


def test_json_error_pages_are_closed_and_secured() -> None:
    errors = read("nginx-service-errors.conf")
    named = blocks(errors, r"location @gdprguardian_\w+")
    assert len(named) == 4
    codes = {}
    for block in named:
        lines = directives(block)
        assert "include /etc/nginx/snippets/gdprguardian-service-headers.conf" in lines
        assert "default_type application/json" in lines
        status, body = re.search(r"return (\d{3}) '(.+)'", block).groups()  # type: ignore[union-attr]
        error = json.loads(body)["error"]
        assert set(error) == {"code", "message"}
        codes[error["code"]] = (int(status), error["message"])
        assert (status in {"429", "503"}) == any(line.startswith("add_header Retry-After") for line in lines)
    # Mêmes codes et messages que le service ; le 413 nomme la limite d'un fichier (50 Mo, voir test_big_documents).
    # Same codes and messages as the service; the 413 names the file limit (50 MB, see test_big_documents).
    for error in (CrossSiteRefused(), RateLimited(), file_too_large(ServerConfig(public=True).max_upload_bytes),
                  ServiceBusy()):
        assert codes[error.code] == (error.status, error.message), error.code


def test_the_cross_site_rule_matches_the_service() -> None:
    # Même règle des deux côtés : absent, same-origin ou none admis ; toute autre valeur refusée.
    # Same rule on both sides: absent, same-origin or none allowed; any other value refused.
    body = blocks(read("nginx-http.conf"), r"map \$http_sec_fetch_site \$gdprguardian_cross_site")[0]
    entries = dict(line.strip().rstrip(";").rsplit(None, 1) for line in body.splitlines() if line.strip())
    assert entries == {"default": "1", '""': "0", "same-origin": "0", "none": "0"}
    assert {key.strip('"') for key, value in entries.items() if value == "0"} == {"", *_FETCH_SITES}


def test_nothing_is_ever_cached_by_nginx() -> None:
    for path in DEPLOY.glob("nginx*.conf"):
        assert "proxy_cache" not in strip_comments(path.read_text(encoding="utf-8")), path.name


def test_the_dedicated_main_configuration() -> None:
    main = directives(read("nginx-main.conf"))
    for expected in ("worker_connections 8192", "worker_rlimit_nofile 16384", "server_tokens off", "access_log off",
                     "ssl_protocols TLSv1.2 TLSv1.3", "include /etc/nginx/conf.d/*.conf",
                     "include /etc/nginx/sites-enabled/*", "pid /run/nginx.pid"):
        assert expected in main, expected
    dropin = read("nginx.service.conf")
    for command in ("ExecStartPre", "ExecStart", "ExecReload"):
        assert f"{command}=\n" in dropin and re.search(rf"^{command}=/usr/sbin/nginx .*-c /etc/nginx/nginx-gdprguardian"
                                                       rf"\.conf", dropin, re.M)
    # Les zones de limites (adresses) ne vont jamais en swap / limit zones (addresses) never go to swap.
    assert re.search(r"^MemorySwapMax=0$", dropin, re.M)


def test_connection_caps_fit_the_worker_connections() -> None:
    # Flux en direct et connexions au service, deux connexions chacun (client, amont), sous la limite d'un processus.
    # Live streams and service connections, two connections each (client, upstream), under one worker's limit.
    totals = {name: int(value) for name, value in re.findall(r"limit_conn (gdprguardian_\w*total) (\d+);",
                                                             read("nginx-site.conf"))}
    assert totals == {"gdprguardian_api_total": 1500, "gdprguardian_live_total": 1500}
    assert 2 * sum(totals.values()) <= 8192


def test_the_stock_nginx_conf_is_never_edited() -> None:
    script = read("install.sh")
    assert not [line for line in script.splitlines() if "sed" in line and ("nginx.conf" in line or "NGINX" in line)]
    assert "force-confmiss" in script  # rétabli s'il avait été modifié / restored when it had been modified


def test_every_shipped_file_is_installed() -> None:
    script = read("install.sh")
    for path in DEPLOY.iterdir():
        if path.name != "install.sh":
            assert path.name in script, path.name


# --- compose / compose -----------------------------------------------------------------------------------------


def test_compose_runs_the_public_service_with_the_reviewed_settings() -> None:
    yaml = pytest.importorskip("yaml")
    service = yaml.safe_load(read("compose.yaml"))["services"]["gdprguardian"]
    assert "init" not in service and service["pull_policy"] == "never"
    assert service["healthcheck"] == {"disable": True} and service["network_mode"] == "none"
    assert service["image"] == f"gdprguardian:{__version__}"
    # Aucun journal d'activité : rien sous « warning » / no activity log: nothing below "warning".
    assert service["command"][-2:] == ["--log-level", "warning"]
    assert service["env_file"] == ["/etc/gdprguardian/gdprguardian.env", "/etc/gdprguardian/local.env"]
    env = service["environment"]
    assert env["GDPRGUARDIAN_PUBLIC"] == "1" and env["GDPRGUARDIAN_CLIENT_IP_HEADER"] == "X-GG-Client"
    assert (env["GDPRGUARDIAN_MAX_CONCURRENCY"], env["GDPRGUARDIAN_WORKER_MEMORY_MB"], env["GDPRGUARDIAN_QUEUE_MB"],
            env["GDPRGUARDIAN_MAX_STORE_CHARS"]) == ("3", "1280", "1024", "100000000")
    assert not any("API_KEY" in name for name in env)
    config = ServerConfig.from_env({name: str(value) for name, value in env.items()})
    assert config.public and not config.keyed and config.max_concurrency == 3
    # Mémoire : travailleurs + file + résultats (4 octets par caractère au pire : chaînes UCS-4) sous la limite du
    # conteneur, marge d'accueil comprise. Memory: workers + queue + results (4 bytes per character at worst: UCS-4
    # strings) under the container limit, front margin included.
    total = config.max_concurrency * config.worker_memory_mb * 2**20 + config.queue_bytes + 4 * config.max_store_chars
    assert total + 512 * 2**20 <= 6 * 2**30
    assert config.max_output_chars == 12_500_000  # un résultat : 1/8 du dépôt / one result: 1/8 of the store


def test_host_units() -> None:
    mount = read("run-gdprguardian.mount")
    assert "Where=/run/gdprguardian" in mount and "size=64k" in mount and "nr_inodes=16" in mount
    assert "uid=10001" in mount and "gid=33" in mount and "noexec" in mount
    assert "RequiresMountsFor=/run/gdprguardian" in read("docker.service.conf")
    assert "OnUnitActiveSec=2min" in read("gdprguardian-watchdog.timer")
    assert "ExecStart=/usr/local/sbin/gdprguardian-watchdog" in read("gdprguardian-watchdog.service")
    watchdog = read("gdprguardian-watchdog")
    assert "--unix-socket" in watchdog and "docker restart" in watchdog and "X-GG-Client" not in watchdog
    # Sonde profonde (un vrai travailleur), jeton local lu dans le fichier, jamais en argument.
    # Deep probe (a real worker), local token read from the file, never as an argument.
    assert "http://localhost/health/deep" in watchdog and '-H "@$header"' in watchdog
    assert "header=/etc/gdprguardian/local-header" in watchdog


def test_the_local_token_never_travels_in_a_command_line() -> None:
    script = read("install.sh")
    assert 'socket_curl() { sudo curl -fsS --max-time 120 --unix-socket "$SOCKET" -H "@$LOCAL_HEADER" "$@"; }' in script
    # Créé par des commandes internes du shell et des tubes / created with shell builtins and pipes.
    assert "printf 'X-GG-Local: %s\\n' \"$token\" | put \"$LOCAL_HEADER\" 600" in script
    assert "printf 'GDPRGUARDIAN_LOCAL_TOKEN_SHA256=%s\\n' \"$digest\" | put \"$LOCAL_ENV\" 600" in script
    assert "ufw logging off" in script


# --- clés d'adresse de Nginx / Nginx address keys -------------------------------------------------------------


def ngx_inet6_ntop(packed: bytes) -> str:
    """Portage de ngx_inet6_ntop (src/core/ngx_inet.c) : la forme exacte de $remote_addr en IPv6.

    Port of ngx_inet6_ntop: the exact form of $remote_addr for IPv6.
    """
    zero = last = -1
    best, run = 1, 0
    for i in range(0, 16, 2):
        if packed[i] or packed[i + 1]:
            if best < run:
                zero, best = last, run
            run = 0
            continue
        if run == 0:
            last = i
        run += 1
    if best < run:
        zero, best = last, run
    text, limit = "", 16
    if zero == 0:
        if ((best == 5 and packed[10] == 0xFF and packed[11] == 0xFF) or best == 6
                or (best == 7 and packed[14] != 0 and packed[15] != 1)):
            limit = 12
        text += ":"
    i = 0
    while i < limit:
        if i == zero:
            text += ":"
            i += best * 2
            continue
        text += f"{packed[i] * 256 + packed[i + 1]:x}"
        if i < 14:
            text += ":"
        i += 2
    if limit == 12:
        text += ".".join(str(byte) for byte in packed[12:16])
    return text


def nginx_map(name: str) -> list[tuple[re.Pattern[str] | None, str]]:
    """Lignes d'un bloc map de nginx-http.conf : (motif ou None pour default, valeur) / a map block's lines."""
    body = blocks(read("nginx-http.conf"), rf"map \$remote_addr \${name}")[0]
    entries: list[tuple[re.Pattern[str] | None, str]] = []
    for line in body.splitlines():
        line = line.strip().rstrip(";")
        if not line:
            continue
        key, value = line.rsplit(None, 1)
        key = key.strip().strip('"')
        entries.append((None if key == "default" else re.compile(key.removeprefix("~")), value))
    return entries


def apply_map(entries: list[tuple[re.Pattern[str] | None, str]], address: str) -> str:
    """Valeur de la première ligne qui correspond, variables remplacées / first matching line, variables expanded."""
    for pattern, value in entries:
        match = pattern.search(address) if pattern is not None else None
        if pattern is None or match is not None:
            variables = {"remote_addr": address, **(match.groupdict() if match is not None else {})}
            return re.sub(r"\$(\w+)", lambda found, known=variables: known[found.group(1)], value)
    raise AssertionError("pas de default / no default")


def expected_64(address: ipaddress.IPv6Address) -> str:
    return ":".join(f"{int.from_bytes(address.packed[i:i + 2], 'big'):x}" for i in range(0, 8, 2))


def interesting_addresses() -> list[bytes]:
    """Adresses aux suites de zéros placées partout, plus un tirage / zero runs everywhere, plus random draws."""
    rng = random.Random(64)
    found = [bytes(16), (1).to_bytes(16, "big"), bytes(10) + b"\xff\xff" + bytes([203, 0, 113, 7]),
             bytes(12) + bytes([1, 2, 3, 4]), bytes(14) + b"\x05\x06"]
    for _ in range(4000):
        groups = [rng.choice((0, 0, 0, rng.randrange(1, 0x10000))) for _ in range(8)]
        found.append(b"".join(group.to_bytes(2, "big") for group in groups))
    return found


def test_the_ipv6_limit_key_is_the_canonical_64_whatever_the_compression() -> None:
    entries = nginx_map("gdprguardian_limit")
    keys: dict[str, set[str]] = {}
    for packed in interesting_addresses():
        address = ipaddress.IPv6Address(packed)
        text = ngx_inet6_ntop(packed)
        assert ipaddress.IPv6Address(text) == address, text  # portage fidèle / faithful port
        key = apply_map(entries, text)
        if address.ipv4_mapped is not None:
            assert key == str(address.ipv4_mapped)  # IPv4 mappée : l'IPv4 / mapped: the IPv4
            continue
        assert key == expected_64(address), (text, key)
        keys.setdefault(expected_64(address), set()).add(key)
    assert all(len(forms) == 1 for forms in keys.values())  # une seule clé par /64 / one key per /64


@pytest.mark.parametrize("address", ["203.0.113.7", "10.0.0.1", "255.255.255.255"])
def test_the_ipv4_limit_key_is_the_full_address(address: str) -> None:
    assert apply_map(nginx_map("gdprguardian_limit"), address) == address


def test_the_visitor_key_never_keeps_more_than_a_48_or_a_24() -> None:
    entries = nginx_map("gdprguardian_ip")
    assert apply_map(entries, "203.0.113.7") == "203.0.113.0"
    for packed in interesting_addresses():
        address = ipaddress.IPv6Address(packed)
        if address.ipv4_mapped is not None or address.packed[:12] == bytes(12):
            continue
        key = apply_map(entries, ngx_inet6_ntop(packed))
        kept = [group for group in key.split(":") if group]
        assert key.endswith("::") and len(kept) <= 3, key
        assert address in ipaddress.IPv6Network(f"{key}/{16 * len(kept)}"), key  # un préfixe de l'adresse / a prefix


def test_documented_files_exist() -> None:
    for name in SERVICE_SNIPPETS:
        assert (DEPLOY / name.replace("gdprguardian-", "nginx-")).exists()
    assert Path(DEPLOY / "nginx-main.conf").exists()
