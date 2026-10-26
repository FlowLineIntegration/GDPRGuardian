# syntax=docker/dockerfile:1.7
# Image du service Gardien RGPD (API REST + MCP en ligne), CPU seul, sans torch.
# GDPR Guardian service image (REST API + online MCP), CPU only, no torch.
#
#   docker build -f deploy/Dockerfile -t gdprguardian .          (depuis la racine du dépôt / from the repo root)
#   docker run --rm -p 127.0.0.1:8000:8000 -e GDPRGUARDIAN_PUBLIC=1 -e GDPRGUARDIAN_PUBLIC_URL=https://... \
#     gdprguardian
#   Service public sans clé (limites par client), comme le service officiel ; ou service à clés avec leurs seules
#   empreintes, -e GDPRGUARDIAN_API_KEY_SHA256=<sha256 hex>,… (une clé en clair, GDPRGUARDIAN_API_KEYS, est refusée).
#   Public keyless service (per-client limits), like the official one; or a keyed service given key digests only.
#   Recettes complètes (proxy, durcissement, sans réseau) / full recipes: deploy/README.md.
#   --build-arg PGO=0 : noyau sans optimisation par profil, reproductible au bit près / plain, bit-reproducible core.

ARG PYTHON_IMAGE=python:3.12-slim
ARG RUST_TOOLCHAIN=1.99.1
ARG MATURIN_VERSION=1.15.0
# 1 : noyau optimisé par profil (défaut) ; 0 : construction directe / 1: profile-guided core (default); 0: plain.
ARG PGO=1

# --- Noyau Rust / Rust core --------------------------------------------------------------------------
# Construit sur la même image que l'exécution (même glibc). Sans lui : moteur Python environ 8 fois plus lent sur
# du texte (7 à 9 fois mesuré, plus de 15 fois sur un texte de 10 Mo), et règles personnalisées refusées en ligne
# (moteur d'expressions à temps linéaire requis).
# Built on the runtime image (same glibc). Without it: Python engine about 8x slower on text (7-9x measured, over
# 15x on a 10 MB text), and online custom rules refused (linear-time regex engine required).
# PGO=1 (tools/pgo.py) : noyau instrumenté, charge représentative sur le corpus fictif du dépôt, fusion des profils
# par le llvm-profdata de la chaîne épinglée, puis construction finale. Retenu par défaut : 10 à 12 % de temps en
# moins sur le moteur complet (mesures dans deploy/README.md). PGO=0 donne une roue reproductible au bit près. Jeu
# d'instructions x86-64 de base dans les deux cas : l'image tourne sur toute VM x86-64 (x86-64-v2 mesuré sans gain).
# PGO=1: instrumented core, representative workload on the repository's fictitious corpus, profiles merged by the
# pinned toolchain's llvm-profdata, then the final build. The default: 10-12% less time on the whole engine.
# PGO=0 gives a bit-reproducible wheel. Baseline x86-64 instruction set either way: the image runs on any x86-64
# VM (x86-64-v2: no gain).
FROM ${PYTHON_IMAGE} AS toolchain
ARG RUST_TOOLCHAIN
ARG MATURIN_VERSION
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 CARGO_HOME=/opt/cargo RUSTUP_HOME=/opt/rustup \
    PATH=/opt/cargo/bin:$PATH PYTHONDONTWRITEBYTECODE=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gcc libc6-dev \
 && rm -rf /var/lib/apt/lists/* \
 && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o /tmp/rustup-init.sh \
 && sh /tmp/rustup-init.sh -y --profile minimal --default-toolchain "${RUST_TOOLCHAIN}" \
      --component llvm-tools-preview \
 && pip install "maturin==${MATURIN_VERSION}" "ahocorasick-rs>=0.22"
WORKDIR /core
COPY rust ./rust

# Une étape par variante ; BuildKit ne construit que celle choisie par PGO. Sans PGO, le noyau ne dépend que de
# rust/ : modifier le Python ne le reconstruit pas, et le corpus n'est pas requis.
# One stage per variant; BuildKit only builds the one PGO selects. Without PGO the core only depends on rust/:
# Python edits do not rebuild it, and the corpus is not required.
FROM toolchain AS core-0
RUN maturin build --release -m rust/Cargo.toml --out /wheels

# Charge du profil : sources Python et corpus fictif, jamais copiés dans l'image finale.
# Profile workload: Python sources and fictitious corpus, never copied into the final image.
FROM toolchain AS core-1
COPY src ./src
COPY tools/pgo.py ./tools/pgo.py
COPY datasets/fr/docs ./datasets/fr/docs
RUN python tools/pgo.py --out /wheels

FROM core-${PGO} AS core

# --- Construction / build ----------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS build
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY --from=core /wheels /wheels
# Extras d'exécution seulement : pas de NER, donc ni onnxruntime ni torch / runtime extras only, no NER.
RUN python -m venv /opt/gdprguardian \
 && /opt/gdprguardian/bin/pip install --no-compile ".[office,phone,api,mcp]" /wheels/gdprguardian_core-*.whl \
 && /opt/gdprguardian/bin/python -c "from gdprguardian import Anonymizer; assert Anonymizer().native" \
 && /opt/gdprguardian/bin/python -m compileall -q -x 'olefile/olefile2\.py$' /opt/gdprguardian/lib
# olefile2.py : ancien module Python 2 livré par olefile, jamais importé / legacy Python 2 module, never imported.

# --- Exécution / runtime -----------------------------------------------------------------------------
FROM ${PYTHON_IMAGE}
LABEL org.opencontainers.image.title="GDPR Guardian" \
      org.opencontainers.image.description="Irreversible document anonymisation before AI (REST API + MCP)" \
      org.opencontainers.image.licenses="MIT"
ENV PATH=/opt/gdprguardian/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2
# Utilisateur sans privilège, sans shell ni répertoire personnel / unprivileged user, no shell, no home.
RUN groupadd --system --gid 10001 gdprguardian \
 && useradd --system --uid 10001 --gid gdprguardian --no-create-home --home-dir /nonexistent \
            --shell /usr/sbin/nologin gdprguardian
COPY --from=build /opt/gdprguardian /opt/gdprguardian
USER 10001:10001
WORKDIR /tmp
EXPOSE 8000
# Pas de HEALTHCHECK dans l'image : le service officiel écoute sur un socket Unix, sans réseau, et une sonde de
# l'hôte l'interroge par ce socket (deploy/server/gdprguardian-watchdog) ; une sonde TCP y échouerait toujours. En
# mode TCP, la donner au lancement / no HEALTHCHECK in the image: the official service listens on a Unix socket with
# no network and a host-side probe checks it through that socket; a TCP probe would always fail there. In TCP mode:
#   docker run --health-cmd 'python -c "import sys, urllib.request as u; sys.exit(u.urlopen(\"http://127.0.0.1:8000/health\", timeout=2).status != 200)"' …
# Un seul processus : les résultats vivent en mémoire de ce processus / one process, results live in its memory.
CMD ["gdprguardian", "serve", "--host", "0.0.0.0", "--port", "8000"]
