"""Preuve hors ligne : la variante locale ne touche jamais le réseau / offline proof: the local variant never
touches the network.

Chaque processus Python lancé ici (l'anonymisation, le serveur MCP stdio, et leurs travailleurs isolés) charge
d'abord une garde (`sitecustomize`, transmis par PYTHONPATH) : un crochet d'audit (`sys.addaudithook`) qui tue le
processus (`os._exit`, impossible à rattraper) à la moindre connexion, résolution de nom, requête HTTP ou création
de processus non prévue, et l'écrit dans un journal. Seules exceptions, justifiées :
  - les travailleurs du bac à sable (`gdprguardian.convert._sandbox`), interpréteurs Python lancés par
    multiprocessing, eux-mêmes gardés ; sous Linux, le fork des travailleurs par le zygote ;
  - sous Windows, la paire de sockets locale qu'asyncio crée pour sa boucle (Windows n'a pas de socketpair : Python
    l'émule par une connexion 127.0.0.1 -> 127.0.0.1 dans `socket.socketpair`) ;
  - sous Windows, la commande fixe `cmd /c ver` de la bibliothèque standard (`platform._syscmd_ver`, appelée par
    `platform.system()` jusqu'à Python 3.11 ; pypdfium2 l'appelle à l'import) : elle lit la version de Windows,
    sans réseau, et le Job Object du travailleur la refuse de toute façon.
Every Python process started here (anonymisation, stdio MCP server, their isolated workers) first loads a guard
(`sitecustomize`, through PYTHONPATH): an audit hook that kills the process (`os._exit`, uncatchable) on any
connection, name lookup, HTTP request or unexpected process creation, and logs it. Only justified exceptions: the
sandbox's own workers (Python interpreters started by multiprocessing, guarded too; on Linux, the zygote's forks),
on Windows asyncio's local socket pair (Python emulates socketpair with a 127.0.0.1 connection), and on Windows the
standard library's fixed `cmd /c ver` (`platform.system()` up to Python 3.11, called by pypdfium2 at import): it
reads the Windows version, without network, and the worker's Job Object refuses it anyway.

CPython n'émet aucun événement d'audit pour `_posixsubprocess.fork_exec`, par lequel multiprocessing lance ses
interpréteurs sous POSIX : la garde l'enveloppe donc, avec les mêmes règles.
CPython raises no audit event for `_posixsubprocess.fork_exec`, which multiprocessing uses on POSIX: the guard
wraps it, with the same rules.

Recette Docker (`--network none --read-only`, CLI et serveur MCP) : GDPRGUARDIAN_OFFLINE_IMAGE=<image> active les
deux derniers tests. Docker recipe (CLI and MCP server): GDPRGUARDIAN_OFFLINE_IMAGE=<image> enables the last two tests.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parent.parent
VIOLATION_EXIT = 86
LOG_ENV = "OFFLINE_PROOF_LOG"  # hors GDPRGUARDIAN_* : ces variables sont retirées avant les travailleurs

GUARD = r'''
"""Garde hors ligne des tests (tests/test_offline.py) / offline guard of the tests."""
import os
import sys

_LOG = os.environ.get("OFFLINE_PROOF_LOG")
_NETWORK = frozenset({
    "socket.connect", "socket.bind", "socket.sendto", "socket.sendmsg", "socket.getaddrinfo",
    "socket.gethostbyname", "socket.gethostbyaddr", "socket.getnameinfo", "urllib.Request", "http.client.connect",
    "ftplib.connect", "smtplib.connect", "imaplib.open", "poplib.connect", "nntplib.connect", "telnetlib.Telnet.open",
    "webbrowser.open"})
_PROCESS = frozenset({"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork",
                      "os.forkpty", "os.startfile", "pty.spawn", "_winapi.CreateProcess",
                      "_posixsubprocess.fork_exec"})
_WATCHED = _NETWORK | _PROCESS
_SANDBOX = "gdprguardian.convert._sandbox"
_LAUNCHERS = frozenset({"multiprocessing.popen_spawn_win32", "multiprocessing.popen_spawn_posix",
                        "multiprocessing.util", "multiprocessing.resource_tracker"})
# Commandes fixes de platform._syscmd_ver (shell=True : « cmd.exe /c "<commande>" »).
# platform._syscmd_ver's fixed commands (shell=True: 'cmd.exe /c "<command>"').
_WINDOWS_VER = ('/c "ver"', '/c "command /c ver"', '/c "cmd /c ver"')


def _log(line):
    if _LOG:
        fd = os.open(_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, (line + "\n").encode("utf-8", "backslashreplace"))
        finally:
            os.close(fd)


def _frames():
    frame = sys._getframe(2)
    while frame is not None:
        yield frame.f_globals.get("__name__", ""), frame.f_code.co_name
        frame = frame.f_back


def _same_file(path, candidates):
    try:
        real = os.path.normcase(os.path.realpath(os.fsdecode(path)))
    except (TypeError, ValueError):
        return False
    return any(real == os.path.normcase(os.path.realpath(c)) for c in candidates if c)


def _python(path):
    return _same_file(path, (sys.executable, getattr(sys, "_base_executable", None)))


def _windows_version_query(event, args, frames):
    """`cmd /c ver` de platform._syscmd_ver (Windows, Python <= 3.11) / the stdlib's Windows version query.

    Popen : la ligne de commande exacte ; CreateProcess (ligne de commande illisible dans l'événement) : cmd.exe.
    Popen: the exact command line; CreateProcess (command line unreadable in the event): cmd.exe.
    """
    if sys.platform != "win32" or ("platform", "_syscmd_ver") not in frames or len(args) < 2:
        return False
    if event == "subprocess.Popen":
        return isinstance(args[1], str) and args[1].strip().endswith(_WINDOWS_VER)
    return event == "_winapi.CreateProcess" and _same_file(args[0], (os.environ.get("COMSPEC"),))


def _allowed(event, args):
    frames = list(_frames())
    modules = {module for module, _ in frames}
    if _windows_version_query(event, args, frames):
        return True
    if event in ("socket.connect", "socket.bind"):
        # Windows : paire de sockets émulée par socket.socketpair (boucle asyncio) / emulated socketpair.
        address = args[1] if len(args) > 1 else None
        return (sys.platform == "win32" and isinstance(address, tuple) and address[:1] in (("127.0.0.1",), ("::1",))
                and any(module == "socket" and name in ("socketpair", "_fallback_socketpair")
                        for module, name in frames))
    if event == "socket.sendmsg":
        return len(args) > 1 and args[1] is None  # socket déjà reliée (passage de descripteur) / connected socket
    if event == "os.fork":
        # Linux : le zygote crée un travailleur / the zygote creates a worker.
        return (_SANDBOX, "_make_child") in frames
    if event == "_winapi.CreateProcess":
        return _SANDBOX in modules and bool(_LAUNCHERS & modules) and _python(args[0])
    if event == "_posixsubprocess.fork_exec":
        executables = args[1] if len(args) > 1 else ()
        return (_SANDBOX in modules and bool(_LAUNCHERS & modules) and len(executables) == 1
                and _python(executables[0]))
    return False


def _guard(event, args):
    if event not in _WATCHED:
        return
    try:
        allowed = _allowed(event, args)
    except BaseException as exc:  # garde défaillante : échec fermé / broken guard: fail closed
        allowed = False
        args = (type(exc).__name__,)
    if allowed:
        if event in _PROCESS:
            _log(f"allowed {event} pid={os.getpid()}")
        return
    _log(f"VIOLATION {event} pid={os.getpid()} {args!r:.300}")
    os._exit(86)


sys.addaudithook(_guard)
if os.name == "posix":
    import _posixsubprocess

    _fork_exec = _posixsubprocess.fork_exec

    def _guarded_fork_exec(*args, **kwargs):
        _guard("_posixsubprocess.fork_exec", args[:2])
        return _fork_exec(*args, **kwargs)

    _posixsubprocess.fork_exec = _guarded_fork_exec
_log(f"armed pid={os.getpid()} parent={os.getppid()}")
'''


def _samples() -> ModuleType:
    spec = importlib.util.spec_from_file_location("offline_convert_samples", ROOT / "tests/convert/convert_samples.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAMPLES = _samples()


class Guarded:
    """Environnement d'un processus gardé et lecture de son journal / guarded process environment and its log."""

    def __init__(self, tmp_path: Path) -> None:
        site = tmp_path / "guard"
        site.mkdir()
        (site / "sitecustomize.py").write_text(GUARD, encoding="utf-8")
        self.log = tmp_path / "offline-proof.log"
        # La garde d'abord, puis le chemin déjà en place (même gdprguardian) / the guard first, then the current path.
        path = [str(site), *filter(None, os.environ.get("PYTHONPATH", "").split(os.pathsep))]
        self.env = {**os.environ, "PYTHONPATH": os.pathsep.join(path), LOG_ENV: str(self.log),
                    "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

    def lines(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def violations(self) -> list[str]:
        return [line for line in self.lines() if line.startswith("VIOLATION")]

    def armed_processes(self) -> set[str]:
        return {line.split()[1] for line in self.lines() if line.startswith("armed")}

    def run(self, code: str, *args: str, timeout: float = 600) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-c", code, *args], env=self.env, capture_output=True, text=True,
                              encoding="utf-8", timeout=timeout, check=False)


@pytest.fixture
def guarded(tmp_path: Path) -> Guarded:
    return Guarded(tmp_path)


def _assert_clean(guarded: Guarded, done: subprocess.CompletedProcess[str] | None = None) -> None:
    assert guarded.violations() == [], guarded.violations()
    if done is not None:
        assert done.returncode == 0, done.stderr[-3000:]


def _secrets_left(text: str) -> list[str]:
    variants = set(SAMPLES.SECRETS) | {secret.replace(" ", "") for secret in SAMPLES.SECRETS}
    return sorted(variant for variant in variants if variant in text)


# --- la garde elle-même / the guard itself -------------------------------------------------------------------

_ESCAPES = {
    "name_lookup": "import socket; socket.getaddrinfo('example.invalid', 443)",
    "connection_caught": ("import socket\ntry:\n    socket.create_connection(('192.0.2.1', 9), timeout=0.1)\n"
                          "except OSError:\n    pass"),
    # Adresse numérique : aucune résolution de nom, seule la connexion trahit la sortie.
    # Numeric address: no name lookup, only the connection gives the escape away.
    "raw_connect": ("import socket\ns = socket.socket()\ns.settimeout(0.1)\ntry:\n    s.connect(('192.0.2.1', 9))\n"
                    "except OSError:\n    pass"),
    "udp_datagram": "import socket; socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'x', ('192.0.2.1', 53))",
    # L'exception Windows (paire de sockets d'asyncio) ne couvre pas une connexion locale ordinaire.
    # The Windows exception (asyncio's socket pair) does not cover an ordinary local connection.
    "loopback_connect": ("import socket\ns = socket.socket()\ns.settimeout(0.1)\ntry:\n"
                         "    s.connect(('127.0.0.1', 9))\nexcept OSError:\n    pass"),
    "http": "import urllib.request; urllib.request.urlopen('http://example.invalid/', timeout=0.1)",
    "subprocess": "import subprocess, sys; subprocess.run([sys.executable, '-c', 'pass'])",
}


@pytest.mark.parametrize("code", list(_ESCAPES.values()), ids=list(_ESCAPES))
def test_the_guard_kills_any_escape(guarded: Guarded, code: str) -> None:
    """La garde est armée et rien ne la contourne, pas même un `except` / armed, and no `except` gets around it."""
    done = guarded.run(code)
    assert done.returncode == VIOLATION_EXIT, done.stderr[-2000:]
    assert len(guarded.violations()) == 1


def test_the_guard_lets_local_machinery_run(guarded: Guarded) -> None:
    # Boucle asyncio (paire de sockets sous Windows) et version de Windows lue par la bibliothèque standard.
    # asyncio loop (socket pair on Windows) and the Windows version read by the standard library.
    done = guarded.run("import asyncio, platform; asyncio.run(asyncio.sleep(0)); "
                       "getattr(platform, '_syscmd_ver', lambda: None)(); print('ok')")
    _assert_clean(guarded, done)
    assert done.stdout.strip() == "ok" and len(guarded.armed_processes()) == 1


# --- anonymisation de documents réels / anonymisation of real documents -------------------------------------


def _documents(folder: Path) -> dict[str, bytes]:
    pytest.importorskip("docx")
    xlsxwriter = pytest.importorskip("xlsxwriter")
    import io

    buffer = io.BytesIO()
    with xlsxwriter.Workbook(buffer) as workbook:
        sheet = workbook.add_worksheet("Salariés")
        for row, values in enumerate([("Nom", "Courriel", "IBAN"),
                                      ("Jean Dupont", SAMPLES.EMAIL, SAMPLES.IBAN),
                                      ("Marie Martin", "marie.martin@exemple.fr", SAMPLES.PHONE)]):
            sheet.write_row(row, 0, values)
    files = {"contrat.pdf": SAMPLES.contract_pdf(), "contrat.docx": SAMPLES.make_docx(),
             "salaries.xlsx": buffer.getvalue(), "courrier.eml": SAMPLES.make_eml(html=True),
             # Ressources distantes (image, feuille de style, cadre) : jamais chargées / never fetched.
             "page.html": SAMPLES.HTML.encode("utf-8"),
             "clients.csv": (f"nom;courriel;telephone;nir\nJean Dupont;{SAMPLES.EMAIL};{SAMPLES.PHONE};"
                             f"{SAMPLES.NIR}\n").encode()}
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (folder / name).write_bytes(data)
    return files


_LIBRARY_AND_CLI = r'''
import json, sys
from pathlib import Path
from gdprguardian import Anonymizer, cli
source, target = Path(sys.argv[1]), Path(sys.argv[2])
results = {"text": Anonymizer(countries="FR").anonymize(sys.argv[3]).text}
for path in sorted(source.iterdir()):
    output = target / (path.name + ".md")
    code = cli.main(["anonymize", str(path), "--countries", "FR", "-o", str(output)])
    results[path.name] = [code, output.read_text(encoding="utf-8") if output.exists() else ""]
print(json.dumps(results))
'''


def test_library_and_cli_anonymise_documents_offline(guarded: Guarded, tmp_path: Path) -> None:
    files = _documents(tmp_path / "originaux")
    (tmp_path / "anonymes").mkdir()
    text = f"M. Jean Dupont, NIR {SAMPLES.NIR}, {SAMPLES.EMAIL}, IBAN {SAMPLES.IBAN}."
    done = guarded.run(_LIBRARY_AND_CLI, str(tmp_path / "originaux"), str(tmp_path / "anonymes"), text)
    _assert_clean(guarded, done)
    results = json.loads(done.stdout.strip().splitlines()[-1])
    assert "[NIR_1]" in results["text"] and _secrets_left(results["text"]) == []
    for name in files:
        code, markdown = results[name]
        assert code == 0 and markdown.strip() and f"document{Path(name).suffix}" not in markdown, name
        assert _secrets_left(markdown) == [], name
    # La garde couvrait aussi les travailleurs du bac à sable / the guard covered the sandbox workers too.
    assert len(guarded.armed_processes()) >= 2, guarded.lines()


# --- session MCP locale complète / full local MCP session ---------------------------------------------------


def _long_csv(rows: int) -> bytes:
    lines = ["nom;courriel;telephone"]
    lines += [f"Personne {i};contact{i}@exemple.fr;06 12 34 {i // 100 % 100:02d} {i % 100:02d}" for i in range(rows)]
    return ("\n".join(lines) + "\n").encode()


@pytest.mark.anyio
async def test_local_mcp_session_offline(guarded: Guarded, tmp_path: Path) -> None:
    pytest.importorskip("fastmcp")
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    allowed = tmp_path / "dossiers"
    _documents(allowed)
    (allowed / "annuaire.csv").write_bytes(_long_csv(1500))  # plusieurs pages / several pages
    env = {**guarded.env, "GDPRGUARDIAN_ALLOWED_DIRS": str(allowed)}
    transport = StdioTransport(sys.executable, ["-m", "gdprguardian.cli", "mcp", "--stdio"], env=env, keep_alive=False)
    async with Client(transport, timeout=300, init_timeout=300) as client:
        tools = {tool.name for tool in await client.list_tools()}
        text = await client.call_tool("anonymize_text", {"text": f"Courriel : {SAMPLES.EMAIL}"})
        pdf = await client.call_tool("anonymize_file", {"path": str(allowed / "contrat.pdf")})
        first = await client.call_tool("anonymize_file", {"path": str(allowed / "annuaire.csv")})
        meta = first.structured_content
        second = await client.call_tool("get_anonymized", {"upload_id": meta["upload_id"], "page": 2})
        packs = await client.call_tool("list_packs", {})
    _assert_clean(guarded)
    assert tools == {"anonymize_file", "anonymize_text", "get_anonymized", "list_packs"}
    assert text.content[0].text == "Courriel : [EMAIL_1]"
    assert "[NIR_1]" in pdf.content[0].text and _secrets_left(pdf.content[0].text) == []
    assert meta["next_page"] == 2 and "@exemple.fr" not in second.content[0].text
    assert "FR" in packs.content[0].text
    # Serveur et au moins un travailleur gardés / server and at least one worker guarded.
    assert len(guarded.armed_processes()) >= 2, guarded.lines()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --- recette Docker pour les plus prudents / Docker recipe for the most cautious -----------------------------


def _docker_run(image: str, data: Path, *command: str) -> subprocess.CompletedProcess[bytes]:
    """La recette de deploy/README.md, telle quelle / deploy/README.md's recipe, as is."""
    recipe = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
              "--security-opt", "no-new-privileges", "-v", f"{data}:/data:ro", image, *command]
    return subprocess.run(recipe, capture_output=True, timeout=600, check=False)


_DOCKER = pytest.mark.skipif(not os.environ.get("GDPRGUARDIAN_OFFLINE_IMAGE") or shutil.which("docker") is None,
                             reason="GDPRGUARDIAN_OFFLINE_IMAGE=<image> et docker requis / required")


@_DOCKER
def test_docker_recipe_without_network(tmp_path: Path) -> None:
    image = os.environ["GDPRGUARDIAN_OFFLINE_IMAGE"]
    files = _documents(tmp_path / "dossiers")
    (tmp_path / "dossiers").chmod(0o755)
    for name in files:
        done = _docker_run(image, tmp_path / "dossiers", "gdprguardian", "anonymize", f"/data/{name}", "--countries",
                           "FR")
        markdown = done.stdout.decode("utf-8")
        assert done.returncode == 0, (name, done.stderr.decode("utf-8", "replace")[-2000:])
        assert markdown.strip() and f"document{Path(name).suffix}" not in markdown, name
        assert _secrets_left(markdown) == [], name
    # Dans le conteneur, aucune interface hors boucle locale / inside, no interface but loopback.
    interfaces = _docker_run(image, tmp_path / "dossiers", "python", "-c",
                             "import socket; print(sorted(name for _, name in socket.if_nameindex()))")
    assert interfaces.stdout.decode().strip() == "['lo']"


@_DOCKER
@pytest.mark.anyio
async def test_docker_mcp_server_without_network(tmp_path: Path) -> None:
    """Le serveur MCP stdio dans le conteneur, lancé par le client avec « docker run -i » / the stdio MCP server
    inside the container, launched by the client with "docker run -i"."""
    pytest.importorskip("fastmcp")
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    folder = tmp_path / "dossiers"
    _documents(folder)
    folder.chmod(0o755)
    args = ["run", "-i", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt",
            "no-new-privileges", "-v", f"{folder}:/data:ro", "-e", "GDPRGUARDIAN_ALLOWED_DIRS=/data",
            os.environ["GDPRGUARDIAN_OFFLINE_IMAGE"], "gdprguardian", "mcp", "--stdio"]
    async with Client(StdioTransport("docker", args, keep_alive=False), timeout=300, init_timeout=300) as client:
        pdf = await client.call_tool("anonymize_file", {"path": "/data/contrat.pdf"})
        mail = await client.call_tool("anonymize_file", {"path": "/data/courrier.eml"})
    for result in (pdf, mail):
        assert _secrets_left(result.content[0].text) == [] and result.structured_content["deleted"] is True
    assert "[NIR_1]" in pdf.content[0].text
