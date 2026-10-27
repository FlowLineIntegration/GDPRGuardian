"""Interface en ligne de commande / command-line interface.

    gdprguardian anonymize contrat.pdf -o contrat.md      gdprguardian anonymize - < notes.txt
    gdprguardian serve --host 127.0.0.1 --port 8000       gdprguardian packs
    gdprguardian mcp --stdio --allow-dir ~/GDPRGuardian
    gdprguardian mcp-config claude-desktop --allow-dir ~/GDPRGuardian
"""

from __future__ import annotations

import argparse
import contextlib
import ipaddress
import json
import os
import re
import shlex
import sys
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from . import __version__

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
# Guillemets doubles : compris par cmd.exe, PowerShell et les shells POSIX / understood by every shell.
_INSTALL_HINT = 'pip install "gdprguardian[{extras}]"'
# Clients MCP dont `mcp-config` connaît le format / MCP clients whose format `mcp-config` knows.
MCP_CLIENTS = ("claude-desktop", "claude-code", "vscode", "cursor", "generic")
LOCAL_SERVER_NAME = "gdprguardian"


class CliError(Exception):
    """Erreur affichée sur stderr, sans contenu du document / error shown on stderr, no document content."""

    def __init__(self, message: str, code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.code = code


def build_parser() -> argparse.ArgumentParser:
    from .categories import CATEGORIES_HELP
    from .engine import PROFILES
    from .server.options import LABEL_LANGUAGES

    parser = argparse.ArgumentParser(
        prog="gdprguardian",
        description="Anonymisation irréversible de documents avant IA / irreversible anonymisation before AI.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    anonymize = commands.add_parser("anonymize", help="anonymise un fichier ou stdin / anonymise a file or stdin")
    anonymize.add_argument("input", help="fichier, ou « - » pour du texte UTF-8 sur stdin / file, or '-' for stdin")
    # Pays explicite, FR par défaut, comme l'API et le MCP ; « auto » reste expérimental.
    # Explicit country, FR by default, as in the API and MCP; "auto" stays experimental.
    anonymize.add_argument("--countries", default="FR",
                           help="packs pays séparés par des virgules (défaut : FR), « all », ou « auto » "
                                "(expérimental) / country packs, comma-separated (default: FR), 'all', or 'auto' "
                                "(experimental)")
    # Trois modes (docs/REGLES.md « Modes ») ; fort par défaut / three modes, fort by default.
    anonymize.add_argument("--mode", default=None,
                           help="fort (défaut, EN strong), essentiel (EN essential ; basique accepté) ou personnalise "
                                "(EN custom) / fort (default), essentiel or personnalise")
    anonymize.add_argument("--disable", default=None, metavar="CATEGORIES",
                           help="catégories laissées en clair, séparées par des virgules (mode personnalise ; sans "
                                f"--mode, il le choisit) : {CATEGORIES_HELP} / categories left in clear, "
                                "comma-separated (personnalise mode)")
    anonymize.add_argument("--profile", choices=PROFILES, default=None,
                           help="déprécié, utilisez --mode : strict = fort, standard et fast = essentiel / deprecated, "
                                "use --mode")
    anonymize.add_argument("--label-language", choices=LABEL_LANGUAGES, default="fr")
    anonymize.add_argument("--format", choices=("md", "json"), default="md", help="md (défaut) ou json + rapport")
    anonymize.add_argument("-o", "--output", help="fichier de sortie (défaut : stdout) / output file")
    anonymize.set_defaults(handler=_anonymize)

    serve = commands.add_parser("serve", help="API REST + MCP en ligne (/mcp) / REST API + online MCP")
    _add_http_arguments(serve)
    serve.set_defaults(handler=_serve)

    mcp = commands.add_parser("mcp", help="serveur MCP (stdio par défaut) / MCP server (stdio by default)")
    transport = mcp.add_mutually_exclusive_group()
    transport.add_argument("--stdio", action="store_true",
                           help="local, rien ne quitte le poste (défaut) / local, nothing leaves the computer")
    transport.add_argument("--http", action="store_true", help="en ligne : identique à « serve » / same as serve")
    _add_allow_dir(mcp, "dossiers autorisés en stdio, plusieurs après un même --allow-dir ou en le répétant ; "
                        "défaut : GDPRGUARDIAN_ALLOWED_DIRS / allowed directories for stdio, several after one "
                        "--allow-dir or by repeating it; default: GDPRGUARDIAN_ALLOWED_DIRS")
    _add_http_arguments(mcp)
    mcp.set_defaults(handler=_mcp)

    config = commands.add_parser("mcp-config", help="configuration prête à coller du serveur MCP local / ready-to-"
                                                    "paste configuration of the local MCP server")
    config.add_argument("client", choices=MCP_CLIENTS, help="client MCP / MCP client")
    _add_allow_dir(config, "dossiers autorisés (obligatoire) / allowed directories (required)", required=True)
    config.add_argument("--shell", choices=("posix", "powershell"),
                        help="syntaxe des commandes (claude-code, generic) ; défaut : celle du système / command "
                             "syntax; default: this system's")
    config.set_defaults(handler=_mcp_config)

    packs = commands.add_parser("packs", help="liste les packs pays / lists the country packs")
    packs.add_argument("--json", action="store_true", help="sortie JSON / JSON output")
    packs.set_defaults(handler=_packs)
    return parser


def _add_allow_dir(parser: argparse.ArgumentParser, help_text: str, *, required: bool = False) -> None:
    # « --allow-dir A B » et « --allow-dir A --allow-dir B » : un sélecteur de dossiers MCPB se développe en
    # arguments séparés après l'option. Both forms: an MCPB directory picker expands into separate arguments.
    parser.add_argument("--allow-dir", action="extend", nargs="+", metavar="DIR", required=required, help=help_text)


def _add_http_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="127.0.0.1", help="adresse d'écoute (défaut : 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--uds", metavar="SOCKET",
                        help="socket Unix d'écoute à la place de --host et --port, joint par un proxy local (Nginx) "
                             "/ Unix socket to listen on instead of --host and --port, reached by a local proxy")
    parser.add_argument("--proxy-headers", action="store_true",
                        help="faire confiance à X-Forwarded-* (derrière un proxy TLS) / trust X-Forwarded-*")
    parser.add_argument("--forwarded-allow-ips", default="127.0.0.1", help="proxys de confiance / trusted proxies")
    parser.add_argument("--log-level", default="info", choices=("debug", "info", "warning", "error"))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except CliError as exc:
        print(f"gdprguardian: {exc}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        return 130
    # Jamais de trace ni de message tiers : il peut citer le document, et un agent IA lit stderr.
    # Never a traceback or a third-party message: it may quote the document, and an AI agent reads stderr.
    except OSError as exc:
        print(f"gdprguardian: erreur d'entrée-sortie / I/O error ({exc.strerror or type(exc).__name__})",
              file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:
        print(f"gdprguardian: erreur interne / internal error ({type(exc).__name__})", file=sys.stderr)
        return EXIT_ERROR


# --- anonymize ---------------------------------------------------------------------------------------


def _anonymize(args: argparse.Namespace) -> int:
    from . import documents
    from .documents import DocumentError, DocumentOptions
    from .server.errors import from_document_error
    from .server.filenames import neutral_filename
    from .server.options import AnonymizeOptions

    try:
        options = AnonymizeOptions.build(args.countries, args.profile, args.label_language, mode=args.mode,
                                         disable=args.disable)
    except ValueError as exc:
        raise CliError(str(exc), EXIT_USAGE) from None
    anonymizer = options.anonymizer()
    output = Path(args.output) if args.output else None
    payload: dict[str, Any]
    if args.input == "-":
        text = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        result = anonymizer.anonymize(text)
        body, payload = result.text, {"text": result.text, "report": result.report}
    else:
        source = Path(args.input)
        if not source.is_file():
            raise CliError("fichier introuvable / file not found", EXIT_USAGE)
        if output is not None and output.exists() and output.resolve() == source.resolve():
            raise CliError("la sortie écraserait l'original / output would overwrite the original", EXIT_USAGE)
        limits = DocumentOptions()
        if source.stat().st_size > limits.max_bytes:
            raise CliError(f"fichier trop volumineux / file too large (> {limits.max_bytes} octets/bytes)")
        try:
            # Le nom du fichier n'entre jamais dans la sortie : seule son extension sert / only the extension is used.
            document = documents.anonymize_document(source.read_bytes(), neutral_filename(source.name), anonymizer,
                                                    limits)
        except DocumentError as exc:
            error = from_document_error(exc)
            raise CliError(f"{error.code}: {error.message}") from None
        except (ImportError, NotImplementedError):
            raise CliError("convertisseur indisponible pour ce format / converter unavailable "
                           f"({_INSTALL_HINT.format(extras='office')})") from None
        body = document.markdown
        payload = {"markdown": document.markdown, "kind": document.kind, "pages": document.pages,
                   "report": document.report, "warnings": document.warnings, "dropped": document.dropped}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) if args.format == "json" else body
    if not rendered.endswith("\n"):
        rendered += "\n"
    if output is None:
        sys.stdout.buffer.write(rendered.encode("utf-8"))
        sys.stdout.buffer.flush()
    else:
        output.write_text(rendered, encoding="utf-8", newline="")
    return EXIT_OK


# --- serve / mcp -------------------------------------------------------------------------------------


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn

        from .server import ServerConfig, create_app
        from .server.config import ConfigError, scrub_settings
        from .server.logs import configure_logging
    except ImportError:
        raise CliError(f"dépendances manquantes / missing dependencies: {_INSTALL_HINT.format(extras='api,mcp')}"
                       ) from None
    configure_logging(args.log_level)
    try:
        config = ServerConfig.from_env()
    except ConfigError as exc:
        raise CliError(str(exc), EXIT_USAGE) from None
    from ._hardening import HardeningError, harden_process

    # Réglages lus, clés comprises : retirés de l'environnement (aucun processus enfant n'en hérite, pas même
    # dans son bloc d'environnement initial) ; processus non lisible. Settings read, keys included: removed from
    # the environment (no child inherits them, not even in its initial environment block); process unreadable.
    scrub_settings()
    try:
        harden_process()
    except HardeningError as exc:
        raise CliError(f"durcissement impossible / hardening failed: {exc}") from None
    # Mode de développement sans clé (GDPRGUARDIAN_DEV_NO_AUTH) : boucle locale seulement, jamais sur un socket Unix,
    # qu'un proxy ouvert sur l'extérieur rejoint. Derrière un proxy, le service sans clé est le mode public
    # (GDPRGUARDIAN_PUBLIC=1 : limites par client, résultats lisibles par leur seule capacité) ; un déploiement à clés
    # donne leurs empreintes (GDPRGUARDIAN_API_KEY_SHA256). Development mode without key: loopback only, never on a
    # Unix socket, which an outward-facing proxy reaches. Behind a proxy, the keyless service is the public mode
    # (per-client limits, results readable through their capability only); a keyed deployment gives key digests.
    if config.dev_no_auth and (args.uds or not is_loopback(args.host)):
        raise CliError("GDPRGUARDIAN_DEV_NO_AUTH=1 exige une adresse locale (--host 127.0.0.1, sans --uds) / requires "
                       "a loopback host, without --uds", EXIT_USAGE)
    # Un seul processus : le dépôt des résultats est en mémoire / one process, the result store is in memory.
    uvicorn.run(create_app(config), host=args.host, port=args.port, uds=args.uds, access_log=False,
                server_header=False, proxy_headers=args.proxy_headers, forwarded_allow_ips=args.forwarded_allow_ips,
                log_config=None, timeout_graceful_shutdown=10)
    return EXIT_OK


def _mcp(args: argparse.Namespace) -> int:
    if args.http:
        return _serve(args)
    # stderr en UTF-8 : les clients MCP le lisent ainsi (journal de Claude Desktop) ; sous Windows, un tube serait
    # sinon en cp1252 et les accents illisibles. stderr in UTF-8, as MCP clients read it (cp1252 pipe otherwise).
    reconfigure = getattr(sys.stderr, "reconfigure", None)
    if reconfigure is not None:
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        from .server.logs import configure_logging
        from .server.mcp_local import allowed_dirs_from_env, no_allowed_dirs_message, resolve_roots, run_stdio
    except ImportError as exc:
        # Le serveur local demande l'extra « local » (MCP, convertisseurs) ; le module fautif aide au diagnostic.
        # The local server needs the "local" extra; the failing module helps diagnosis.
        raise CliError(f"dépendances manquantes / missing dependencies ({exc.name or 'fastmcp'}): "
                       f"{_INSTALL_HINT.format(extras='local')}") from None
    # --allow-dir l'emporte sur l'environnement, sans les cumuler ; une valeur vide (option de plugin sans valeur,
    # « --allow-dir "" ») ne compte pas. --allow-dir wins over the environment; an empty value does not count.
    given = args.allow_dir
    dirs = allowed_dirs_from_env() if given is None else [entry for entry in given if entry.strip()]
    roots = resolve_roots(dirs)
    if not dirs:
        raise CliError(no_allowed_dirs_message(roots), EXIT_USAGE)
    # Dossier absent (pas encore créé) : le serveur démarre et le relit à chaque appel ; message sur stderr, que
    # les clients MCP gardent dans leur journal. Missing folder (not created yet): the server starts and re-reads
    # it at every call; message on stderr, which MCP clients keep in their log. stdout appartient au protocole.
    if not roots:
        print(f"gdprguardian: {no_allowed_dirs_message(roots)}", file=sys.stderr)
    for entry, reason in roots.unusable if roots else ():
        print(f'gdprguardian: dossier ignoré / directory ignored: "{entry}": {reason}', file=sys.stderr)
    configure_logging("warning")
    run_stdio(dirs)
    return EXIT_OK


def mcp_main(argv: Sequence[str] | None = None) -> int:
    """Commande `gdprguardian-mcp` (paquet du registre MCP) : `gdprguardian mcp --stdio`, sans transport HTTP.

    `gdprguardian-mcp` command (MCP Registry package): `gdprguardian mcp --stdio`, without the HTTP transport. Rien
    n'écoute sur le réseau : le serveur ne parle qu'à son client, par stdin et stdout. Nothing listens on the
    network: the server only talks to its client, over stdin and stdout.
    """
    parser = argparse.ArgumentParser(
        prog="gdprguardian-mcp",
        description="Serveur MCP local (stdio) de Gardien RGPD / GDPR Guardian local MCP server (stdio).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--stdio", action="store_true", help="transport stdio, le seul / stdio, the only transport")
    _add_allow_dir(parser, "dossiers autorisés, plusieurs après un même --allow-dir ou en le répétant (défaut : "
                           "GDPRGUARDIAN_ALLOWED_DIRS) / allowed directories, several after one --allow-dir or "
                           "repeated")
    args = parser.parse_args(argv)
    # « --allow-dir=DIR » : un dossier commençant par « - » reste un dossier / a dir starting with "-" stays a dir.
    return main(["mcp", "--stdio", *(f"--allow-dir={folder}" for folder in args.allow_dir or ())])


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


# --- mcp-config --------------------------------------------------------------------------------------

# Où coller chaque extrait (affiché sur stderr : stdout reste copiable tel quel).
# Where to paste each snippet (shown on stderr: stdout stays copyable as is).
_CONFIG_HINTS = {
    "claude-desktop": "à fusionner dans claude_desktop_config.json (Windows : %APPDATA%\\Claude ; macOS : "
                      "~/Library/Application Support/Claude ; si « spawn uvx ENOENT », remplacez uvx par le chemin "
                      "que donne `which uvx`) ; pour Cowork, installez plutôt le plugin / merge into "
                      "claude_desktop_config.json (macOS, on 'spawn uvx ENOENT': use the path given by `which "
                      "uvx`); for Cowork, install the plugin instead",
    "claude-code": "à lancer dans un terminal / run it in a terminal",
    "vscode": "dans .vscode/mcp.json (espace de travail) ou « MCP: Open User Configuration » / in .vscode/mcp.json "
              "(workspace) or 'MCP: Open User Configuration'",
    "cursor": "dans ~/.cursor/mcp.json (global) ou .cursor/mcp.json (projet) / global or per-project",
    "generic": "commande stdio pour tout client MCP / stdio command for any MCP client",
}
# Mots que PowerShell passe tels quels à un exécutable / words PowerShell passes as is to an executable.
_POWERSHELL_SAFE = re.compile(r"[A-Za-z0-9_./:\\=+-]+")


def local_server_args(dirs: Sequence[str], version: str = __version__) -> list[str]:
    """Arguments de `uvx` du serveur local, version épinglée : la même ligne pour le plugin Claude, le paquet MCPB
    et chaque client (les tests comparent leurs fichiers à cette fonction).

    `uvx` arguments of the local server, pinned version: the same line for the Claude plugin, the MCPB bundle and
    every client (the tests compare their files with this function).
    """
    return ["--from", f"gdprguardian[local]=={version}", "gdprguardian", "mcp", "--stdio", "--allow-dir", *dirs]


def mcp_client_config(client: str, dirs: Sequence[str], *, version: str = __version__, shell: str = "posix") -> str:
    """Extrait de configuration pour `client` : JSON (clés documentées du client) ou commande.

    Configuration snippet for `client`: JSON (the client's documented keys) or a command.
    """
    args = local_server_args(dirs, version)
    # JSON en ASCII (« é » -> é) : intact quel que soit l'encodage d'une redirection (PowerShell 5.1, cmd).
    # ASCII JSON: intact whatever the encoding of a redirection.
    if client in ("claude-desktop", "cursor"):
        return json.dumps({"mcpServers": {LOCAL_SERVER_NAME: {"command": "uvx", "args": args}}}, indent=2)
    if client == "vscode":
        server = {"type": "stdio", "command": "uvx", "args": args}
        return json.dumps({"servers": {LOCAL_SERVER_NAME: server}}, indent=2)
    command = ["uvx", *args]
    if client == "claude-code":
        command = ["claude", "mcp", "add", "--scope", "user", "--transport", "stdio", LOCAL_SERVER_NAME, "--",
                   *command]
    elif client != "generic":
        raise ValueError(f"client inconnu / unknown client: {client}")
    return join_command(command, shell)


def join_command(words: Sequence[str], shell: str) -> str:
    """Commande copiable dans un shell POSIX ou PowerShell / command to paste into a POSIX shell or PowerShell."""
    if shell == "posix":
        return shlex.join(words)
    # Entre apostrophes, PowerShell n'interprète rien. « -- » toujours cité : nu, PowerShell (5.1 et 7) le consomme
    # quand `claude` est le lanceur .ps1 installé par npm. In single quotes PowerShell interprets nothing. "--" is
    # always quoted: bare, PowerShell (5.1 and 7) swallows it when `claude` is the .ps1 launcher installed by npm.
    return " ".join(word if word != "--" and _POWERSHELL_SAFE.fullmatch(word) else "'" + word.replace("'", "''") + "'"
                    for word in words)


def _config_dir(entry: str) -> str:
    """Chemin relatif rendu absolu ; chemins absolus (POSIX ou Windows), « ~ » et variables du client
    (${workspaceFolder}) gardés tels quels. A relative path made absolute; absolute paths (POSIX or Windows), "~"
    and the client's variables are kept as written.
    """
    if (entry.startswith("~") or "${" in entry or PurePosixPath(entry).is_absolute()
            or PureWindowsPath(entry).is_absolute()):
        return entry
    return str(Path(entry).absolute())


def _mcp_config(args: argparse.Namespace) -> int:
    dirs = [_config_dir(entry) for entry in args.allow_dir]
    shell = args.shell or ("powershell" if os.name == "nt" else "posix")
    sys.stdout.buffer.write((mcp_client_config(args.client, dirs, shell=shell) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()
    # Sans `uv tool install`, uvx revérifie l'index à chaque démarrage dès que sa copie a quelques minutes : hors
    # ligne, le serveur ne démarrerait pas. Without it, uvx re-checks the index once its copy is a few minutes old.
    print(f"gdprguardian: {_CONFIG_HINTS[args.client]}. Prérequis / prerequisite: uv (https://docs.astral.sh/uv/), "
          f"puis, une fois avec le réseau, pour démarrer ensuite sans réseau / then, once online, to start offline "
          f"afterwards: uv tool install \"gdprguardian[local]=={__version__}\"", file=sys.stderr)
    for entry in dirs:
        if "${" not in entry and not Path(entry).expanduser().is_dir():
            print(f'gdprguardian: attention, dossier introuvable sur ce poste / warning, directory not found on this '
                  f'computer: "{entry}"', file=sys.stderr)
    return EXIT_OK


# --- packs -------------------------------------------------------------------------------------------


def _packs(args: argparse.Namespace) -> int:
    from .packs import available_packs, load_pack

    rows = []
    for pack_id in available_packs():
        pack = load_pack(pack_id)
        rows.append({"id": pack.id, "name": pack.name, "version": pack.version, "country": pack.country,
                     "recognizers": len(pack.recognizers),
                     "entities": sorted({r.entity for r in pack.recognizers})})
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return EXIT_OK
    for row in rows:
        print(f"{row['id']:<6} {row['name']:<20} {row['version']:<12} {row['recognizers']:>3} "
              f"{', '.join(row['entities'])}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
