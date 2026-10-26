#!/bin/sh
# Essai des archives d'une version, installées SANS réseau dans des environnements neufs (sh POSIX : tourne aussi
# dans Alpine). Smoke test of a release's archives, installed WITHOUT network into fresh environments (POSIX sh).
#
#   smoke.sh download <archives> <travail> [python]          réseau : dépendances tierces seulement
#   smoke.sh offline  <travail> [python] [--native|--pure]    hors ligne : --no-index, cache uv neuf, --offline
#   smoke.sh all      <archives> <travail> [python] [--native|--pure]
#
# Hors ligne, chaque installation est essayée par tools/release.py smoke (--version, anonymisation, poignée de
# main MCP stdio et appels d'outils) : pip install gdprguardian, "gdprguardian[local]", gdprguardian-mcp, puis uvx
# (noyau chargé), uvx --from "gdprguardian[local]==X" gdprguardian mcp --stdio et uvx gdprguardian-mcp@X.
# Offline, each install is checked by tools/release.py smoke.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PHASE="$1"
shift
if [ "$PHASE" != offline ]; then
  DIST="$(cd "$1" && pwd)"
  shift
fi
WORK="$1"
PYTHON="${2:-python3}"
ENGINE="${3:---native}"
VERSION="$("$PYTHON" "$ROOT/tools/release.py" version)"
if [ "$("$PYTHON" -c 'import os; print(os.name)')" = nt ]; then
  BIN=Scripts
  EXE=.exe
else
  BIN=bin
  EXE=
fi

download() {
  rm -rf "$WORK"
  mkdir -p "$WORK/wheelhouse"
  "$PYTHON" -m venv "$WORK/download"
  # Nos archives d'abord, puis les dépendances tierces (et uv, pour les essais uvx) depuis l'index ; une dépendance
  # sans roue pour la plateforme (ahocorasick-rs sous musl) est construite ici, réseau disponible.
  # Our archives first, then third-party dependencies (and uv) from the index; a dependency without a wheel for
  # the platform (ahocorasick-rs on musl) is built here, while the network is available.
  "$WORK/download/$BIN/python" -m pip wheel --quiet --wheel-dir "$WORK/wheelhouse" --find-links "$DIST" \
    "gdprguardian-mcp==$VERSION" "uv==${UV_VERSION:-0.12.23}"
  cp "$DIST"/*.whl "$WORK/wheelhouse/"  # nos roues, jamais celles d'un index / our wheels, never an index's
  ls "$WORK/wheelhouse"
}

offline_venv() {  # <nom> <exigence> : environnement neuf, installation sans index / fresh env, no index
  "$PYTHON" -m venv "$WORK/$1"
  "$WORK/$1/$BIN/python" -m pip install --quiet --no-index --find-links "$WORK/wheelhouse" "$2"
  "$WORK/$1/$BIN/python" -m pip list --format=freeze | grep -i -e '^gdprguardian' -e '^uv=='
}

smoke() {
  "$PYTHON" "$ROOT/tools/release.py" smoke --version "$VERSION" "$@"
}

offline() {
  echo "== pip install gdprguardian (noyau choisi par les marqueurs / core picked by the markers)"
  offline_venv bare "gdprguardian==$VERSION"
  smoke --gdprguardian "$WORK/bare/$BIN/gdprguardian$EXE" "$ENGINE"

  echo "== pip install \"gdprguardian[local]\" puis / then gdprguardian mcp --stdio"
  offline_venv local "gdprguardian[local]==$VERSION"
  smoke --gdprguardian "$WORK/local/$BIN/gdprguardian$EXE" "$ENGINE" -- "$WORK/local/$BIN/gdprguardian$EXE" mcp --stdio

  echo "== pip install gdprguardian-mcp puis / then gdprguardian-mcp"
  offline_venv registry "gdprguardian-mcp==$VERSION"
  smoke -- "$WORK/registry/$BIN/gdprguardian-mcp$EXE"

  # uv du dossier de roues, cache neuf, --offline : tout vient du dossier / all from the wheelhouse.
  offline_venv uv "uv"
  UV="$WORK/uv/$BIN/uv$EXE"
  export UV_CACHE_DIR="$WORK/uv-cache" UV_TOOL_DIR="$WORK/uv-tools" UV_PYTHON_DOWNLOADS=never
  if [ "$ENGINE" = --native ]; then NATIVE=True; else NATIVE=False; fi
  echo "== uvx --from gdprguardian==$VERSION : noyau Rust chargé = $NATIVE / Rust core loaded"
  "$UV" tool run --offline --no-index --find-links "$WORK/wheelhouse" --python "$PYTHON" \
    --from "gdprguardian==$VERSION" python -c "from gdprguardian import _native; assert _native.available() is $NATIVE"
  echo "== uvx --from \"gdprguardian[local]==$VERSION\" gdprguardian mcp --stdio"
  smoke -- "$UV" tool run --offline --no-index --find-links "$WORK/wheelhouse" --python "$PYTHON" \
    --from "gdprguardian[local]==$VERSION" gdprguardian mcp --stdio
  echo "== uvx gdprguardian-mcp@$VERSION"
  smoke -- "$UV" tool run --offline --no-index --find-links "$WORK/wheelhouse" --python "$PYTHON" \
    "gdprguardian-mcp@$VERSION"
  echo "Essai hors ligne réussi / offline smoke test passed: $VERSION"
}

case "$PHASE" in
  download) download ;;
  offline) offline ;;
  all) download && offline ;;
  *) echo "phase inconnue / unknown phase: $PHASE" >&2; exit 2 ;;
esac
