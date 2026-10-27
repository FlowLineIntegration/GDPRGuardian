# Publier une version / Publishing a release

[Français](#français) · [English](#english)

## Français

Une version de Gardien RGPD est **une seule version partout** : les paquets `gdprguardian-core` (noyau Rust),
`gdprguardian` et `gdprguardian-mcp`, le plugin Claude, le paquet MCPB, l'image Docker et le service en ligne.
`pyproject.toml` (`[project] version`) fait référence ; `tools/release.py` recopie et contrôle tous les champs
qui en dépendent (fichiers de paquets, plugin, MCPB, image du déploiement, épinglages des guides).

**Phase actuelle : R&D.** Tout se construit localement, sans GitHub Actions, et rien n'est publié sur PyPI ni
dans un registre. Le service en ligne tourne sur le serveur du projet. La publication publique (PyPI, registre
MCP, GHCR) est préparée dans des workflows GitHub Actions (`ci.yml`, `release.yml`) gardés hors du dépôt public tant
que GitHub Actions n'est pas utilisé (`.github/workflows/` est ignoré) ; voir la dernière section.

### Changer de version

```bash
python tools/release.py set 1.1.0        # préversion : 1.1.0rc1 (Cargo reçoit 1.1.0-rc.1)
python tools/release.py check
uv lock
```

### Construire localement

```bash
python tools/build_local.py --mcpb <CLI mcpb>       # noyau pour ce système, sources, roues pures, paquet MCPB
python tools/build_local.py --linux --image --skip-host   # sous Linux (WSL) : roue manylinux, image Docker
```

Tout arrive dans `dist/<version>/` : roues et sources à la racine, `claude/` (paquet MCPB), `docker/` (archive de
l'image, noyau PGO), `SHA256SUMS`. Le script vérifie les versions avant de construire, puis le contenu des
archives (`release.py dists` : noms, versions, licence, étiquettes abi3, épinglages, commandes). La CLI officielle
`mcpb` s'installe avec `npm install -g @anthropic-ai/mcpb` ; sans elle, le paquet MCPB est sauté.

Installer depuis ce dossier, sur un poste d'essai :

```bash
pip install --find-links dist/<version> "gdprguardian[local]==<version>"
gdprguardian mcp --stdio --allow-dir ~/GDPRGuardian
```

Tant que rien n'est sur PyPI, le plugin Claude, le paquet MCPB et `gdprguardian mcp-config` (qui lancent
`uvx --from "gdprguardian[local]==<version>"`) ne trouvent pas le paquet : pour un essai local, déclarer au client
la commande installée ci-dessus.

### Service en ligne

Le service, **réservé aux détenteurs d'une clé d'API** (remise sur demande à contact@gardienrgpd.fr, avec un accord
de sous-traitance, art. 28 RGPD), répond sur `https://api.gdprguardian.com` et `https://api.gardienrgpd.fr` (API REST
et MCP sur `/mcp`), avec des limites par client tenues en mémoire ; il tourne sur le serveur OVH du projet, durci
au préalable (pare-feu, fail2ban, mises à jour automatiques, journaux bornés, aucun vidage mémoire). Installation : `deploy/server/` (voir [`deploy/README.md`](../deploy/README.md)). Le conteneur n'a aucun
réseau ; Nginx le joint par un socket Unix, en mémoire, et rien du document ne touche le disque.

Mettre à jour le service après une nouvelle version (le démon du site d'abord) :

```bash
scp dist/<version>/docker/gdprguardian-<version>.tar.gz <serveur>:
ssh <serveur> mkdir -p gdprguardian-video              # vidéo de lancement du site, servie par Nginx sous /media/
scp video/out/*.mp4 video/out/*.png video/out/*.txt <serveur>:gdprguardian-video/
ssh <serveur> bash gdprguardian-deploy/install.sh site <binaire du site> gdprguardian-video
ssh <serveur> bash gdprguardian-deploy/install.sh base
ssh <serveur> bash gdprguardian-deploy/install.sh image gdprguardian-<version>.tar.gz
ssh <serveur> bash gdprguardian-deploy/install.sh start
ssh <serveur> bash gdprguardian-deploy/install.sh verify
```

Une clé d'API par organisation : le service n'en reçoit que l'empreinte SHA-256, ajoutée à
`GDPRGUARDIAN_API_KEY_SHA256` dans `/etc/gdprguardian/gdprguardian.env`, puis `install.sh start` (qui recrée le
conteneur) ; révocation : retirer l'empreinte, puis `install.sh start`. Une clé en clair (`GDPRGUARDIAN_API_KEYS`) est
refusée au démarrage. `install.sh base` crée aussi le **jeton local** des requêtes du serveur lui-même (sonde de santé,
`verify`, protocole de mesure), dans `/etc/gdprguardian/local-header` (root 0600, jamais affiché ni passé en
argument). `install.sh verify` attend encore le mode public (contrôles sans clé) et reste à adapter.

Après toute version qui change le moteur, relancer la **campagne du protocole public** sur le serveur, puis
reporter ses clés dans `site/data/quality.json` : [`docs/PROTOCOLE.md`](PROTOCOLE.md), sections 9, 10 et 15. Jusqu'à
la campagne, toute mesure des corpus réels se fait sur la seule moitié `dev` (`evaluate_real.py --split dev`,
`pack-real --split dev`) ; une mesure d'une moitié `test` s'ajoute à `PROTOCOLE.md` (section 3) et à
`spec.TEST_HALVES_MEASURED_BEFORE`, puis on enregistre à nouveau. Dans l'ordre, depuis la racine du dépôt :

1. Geler le moteur et le déployer ; ne plus redéployer pendant la campagne (une campagne = un moteur : l'image du
   service et ses sorties sur une sonde fixe sont contrôlées du début à la fin).
2. Refaire le contrôle croisé sur ce moteur (`crosscheck` pour les pays `auto` et `FR`, puis `crosscheck-summary`
   vers `benchmarks/results/`, `PROTOCOLE.md` section 11) ; son empreinte de sonde doit égaler celle de la campagne.
3. `python -m tools.protocol bundle --out X/gg-protocol.pyz`, puis `python -m tools.protocol registration --bundle
   X/gg-protocol.pyz` (`matches_repository: true`) ; **publier ces empreintes avant le lancement**. Le paquet est
   à reconstruire après toute retouche de `tools/` (dont `tools/corpus/evaluate_real.py`) ou de `PROTOCOLE.md`.
4. Sur le serveur, `gg-protocol/` contenant `gg-protocol.pyz` et `tools/protocol/server/run-protocol.sh` :
   `sudo swapoff -a` (swap zram : `sudo systemctl mask --runtime --now dev-zram0.swap`, sinon systemd le relance ;
   levé après la campagne), puis `bash gg-protocol/run-protocol.sh prepare`.
5. **Essai chronométré** (jamais publié) : `python -m tools.protocol pack-real --cache C --out P --split dev`, copier
   `P` vers `/dev/shm/gg-protocol/real-corpora.jsonl.gz` par `ssh <serveur> "sudo install -m 0400 -o 10001 -g 10001
   /dev/stdin /dev/shm/gg-protocol/real-corpora.jsonl.gz" < P` (jamais un fichier à l'utilisateur dans /dev/shm :
   systemd-logind l'efface à la fin de sa session), `GG_PROTOCOL_ARGS="--synthetic-docs 3000 --redteam-bases
   30" bash gg-protocol/run-protocol.sh start`, `status` jusqu'à la fin (débit en documents par seconde, d'où la
   durée des 1 019 385 documents), `finish` (résultats dans `results/trial-<date>/`). Effacer `P`.
6. Campagne : `prepare` à nouveau (`finish` a vidé la mémoire vive), `pack-real` **complet** (sans `--split`),
   copie vers `/dev/shm/gg-protocol/real-corpora.jsonl.gz`, effacer la copie locale ;
   `GG_PROTOCOL_HOURS=3 bash gg-protocol/run-protocol.sh start`, en évitant la maintenance du serveur (mises à jour
   de sécurité chaque nuit à 2 h, heure de Paris, 1 h 45 le lundi, avec redémarrage si nécessaire ; redémarrage
   chaque lundi à 2 h) ; `status` jusqu'à `units_done` = `units_planned` ; après une pause, `start` reprend.
7. `bash gg-protocol/run-protocol.sh finish` : image vérifiée, résultats copiés dans `gg-protocol/results/`, dossier
   de travail **archivé** (`/var/lib/gg-protocol-<date>-<plan>`), mémoire vive vidée ; un `start` sur une campagne
   terminée est refusé. Copier `protocol-<version>-<date>.{json,md}` dans `benchmarks/results/`.
8. `python -I site/tools/protocol_table.py benchmarks/results/protocol-<version>-<date>.json` (il appelle
   `merge_quality.py` puis écrit le tableau par famille, les deux indices et le README), puis
   `python -I site/tools/preview.py --check`, reconstruire et déployer le site. `merge_quality.py` seul ne suffit
   pas : `preview.py --check` refuse alors l'indice. Tout écart déclaré qu'il rappelle se publie avec l'indice. Une
   campagne répétée sur les mêmes moitiés `test` liste les précédentes dans `spec.EARLIER_CAMPAIGNS` (sinon refus).

### Plus tard : publication publique

Le jour où GitHub Actions est adopté : retirer `.github/workflows/` de `.gitignore` et valider `ci.yml` et
`release.yml` (jusque-là absents du dépôt public, aucune action ne s'y exécute). When GitHub Actions is adopted,
remove `.github/workflows/` from `.gitignore` and commit both workflows (until then no action runs in the public
repository).

1. **Dépôt GitHub** : fait, `FlowLineIntegration/GDPRGuardian` est public (`tools/release.py set-owner` déjà appliqué).
2. **PyPI** (double authentification) : éditeur de confiance en attente pour `gdprguardian-core`, `gdprguardian`
   et `gdprguardian-mcp` (propriétaire `<compte>`, dépôt `GDPRGuardian`, workflow `release.yml`, environnement
   `pypi`). Ces trois noms étaient libres le 25 octobre 2026.
3. **GitHub** > Settings > Environments : `pypi`, avec validation manuelle.
4. **Essai à blanc** : Actions > Release > Run workflow (sept roues du noyau, essais hors ligne, SBOM, rien de
   publié).
5. **Publication** : `python tools/release.py check --release --tag v<version>`, `git tag v<version>`, pousser.
   Le workflow publie PyPI (noyau, puis `gdprguardian`, puis `gdprguardian-mcp`, avec attestations), la version
   GitHub, le registre MCP `io.github.<compte>/gdprguardian` et l'image `ghcr.io/<compte>/gdprguardian`.
6. **Ensuite** : rendre l'image GHCR publique ; joindre le paquet MCPB à la version (le signer avec un certificat
   de signature de code si possible) ; essayer le plugin (`claude plugin marketplace add <compte>/GDPRGuardian`)
   dans Claude Code, Claude Desktop et Cowork. `server.json` déclare déjà les deux points MCP en ligne
   (`remotes`, `streamable-http`), sans y annoncer encore l'en-tête `Authorization` que le service exige désormais.

## English

One GDPR Guardian release is **one version everywhere**: the `gdprguardian-core`, `gdprguardian` and
`gdprguardian-mcp` packages, the Claude plugin, the MCPB bundle, the Docker image and the online service.
`pyproject.toml` is the reference; `tools/release.py` copies and checks every field that depends on it.

**Current phase: R&D.** Everything is built locally, without GitHub Actions; nothing is published to PyPI or a
registry. The online service runs on the project's server. Public publishing is prepared in GitHub Actions
workflows (`ci.yml`, `release.yml`) that stay out of the public repository while GitHub Actions is not used
(`.github/workflows/` is ignored).

- **Change version:** `python tools/release.py set X.Y.Z`, `python tools/release.py check`, `uv lock`.
- **Build locally:** `python tools/build_local.py --mcpb <mcpb CLI>` (core for this system, sdists, pure wheels,
  MCPB bundle), then under Linux (WSL) `python tools/build_local.py --linux --image --skip-host` (manylinux wheel,
  Docker image). Output: `dist/<version>/` with `claude/`, `docker/` and `SHA256SUMS`; versions are checked
  before building and archive contents after.
- **Try it:** `pip install --find-links dist/<version> "gdprguardian[local]==<version>"`. Until the packages are on
  PyPI, the plugin, the MCPB bundle and `mcp-config` (all `uvx --from …`) cannot find them: point the client at
  the installed `gdprguardian mcp --stdio --allow-dir <folder>` instead.
- **Online service:** the service at `https://api.gdprguardian.com` and `https://api.gardienrgpd.fr` (REST API,
  MCP on `/mcp`), **reserved for API key holders** (given on request at contact@gardienrgpd.fr, with a data
  processing agreement, GDPR art. 28), per-client limits kept in memory; installed with `deploy/server/` (see [`deploy/README.md`](../deploy/README.md)); the container has no
  network and Nginx reaches it through an in-memory Unix socket. Update (site daemon first): `install.sh site
  <site binary> <copy of video/out>`, `install.sh base`, `install.sh image <archive>`, `install.sh start`, `install.sh verify`. One API
  key per organisation: the service only gets its SHA-256 digest, added to `GDPRGUARDIAN_API_KEY_SHA256` in
  `/etc/gdprguardian/gdprguardian.env`, then `install.sh start` (which recreates the container); revocation: remove the
  digest, then `install.sh start`. A plaintext `GDPRGUARDIAN_API_KEYS` is refused at start-up. `install.sh base` also
  creates the **local token** of the server's own requests (health probe, `verify`, measurement protocol) in
  `/etc/gdprguardian/local-header` (root 0600, never printed nor passed as an argument). `install.sh verify` still
  expects public mode (checks without a key) and is yet to be adapted. After any release
  that changes the engine, run the **public protocol campaign** again on the server and merge its keys into
  `site/data/quality.json`: [`docs/PROTOCOLE.md`](PROTOCOLE.md), sections 9, 10 and 15. Until the campaign, every
  real-corpus measurement uses the `dev` half only (`evaluate_real.py --split dev`, `pack-real --split dev`); a
  `test`-half measurement is added to `PROTOCOLE.md` (section 3) and `spec.TEST_HALVES_MEASURED_BEFORE`, then the
  protocol is registered again. In order: (1) freeze and deploy the engine, no redeploy during the campaign; (2)
  redo the cross-check on it (`crosscheck` for `auto` and `FR`, then `crosscheck-summary` into
  `benchmarks/results/`); its probe digest must equal the campaign's; (3) `bundle --out X/gg-protocol.pyz`, then
  `registration --bundle X/gg-protocol.pyz` (`matches_repository: true`) and **publish these digests before the
  launch**; rebuild the bundle after any change to `tools/` (including `tools/corpus/evaluate_real.py`) or
  `PROTOCOLE.md`; (4) on the server, with `gg-protocol.pyz` and `run-protocol.sh` in `gg-protocol/`: `sudo swapoff
  -a` (zram: `sudo systemctl mask --runtime --now dev-zram0.swap`, lifted after the campaign), `run-protocol.sh
  prepare`; packs are written with `ssh <server> "sudo install -m 0400 -o 10001 -g 10001 /dev/stdin
  /dev/shm/gg-protocol/real-corpora.jsonl.gz" < pack`, never as a file owned by the user (systemd-logind wipes it
  when the session ends); (5) **timed trial**, never published: a `--split dev` pack in
  `/dev/shm/gg-protocol/real-corpora.jsonl.gz`, `GG_PROTOCOL_ARGS="--synthetic-docs 3000 --redteam-bases 30"
  run-protocol.sh start`, `status` for the throughput (hence the duration of the 1,019,385 documents), `finish`
  (results in `results/trial-<date>/`); (6) campaign: `prepare` again (`finish` emptied the RAM folder), the **full**
  pack (no `--split`) copied to the same place, the local copy deleted, `GG_PROTOCOL_HOURS=3 run-protocol.sh start` away from the server maintenance (security updates every night at 02:00 Paris time, 01:45 on Mondays, with a reboot if needed; a reboot every Monday at 02:00), `status`
  until `units_done` = `units_planned`, `start` again after a pause; (7) `run-protocol.sh finish` checks the image,
  copies the results, **archives** the work folder (`/var/lib/gg-protocol-<date>-<plan>`) and empties the RAM folder
  (`start` on a completed campaign is refused); copy `protocol-<version>-<date>.{json,md}` into `benchmarks/results/`;
  (8) `python -I site/tools/protocol_table.py benchmarks/results/protocol-<version>-<date>.json` (it runs
  `merge_quality.py`, then writes the per-family table, both indexes and the README), then
  `python -I site/tools/preview.py --check`, rebuild and deploy the site (`merge_quality.py` alone is not enough:
  `preview.py --check` then refuses the index); any disclosed departure it recalls is
  published with the index; a repeat campaign on the same `test` halves lists the earlier ones in
  `spec.EARLIER_CAMPAIGNS` (refused otherwise).
- **Later, public publishing:**
  1. GitHub repository: done, `FlowLineIntegration/GDPRGuardian` is public (`set-owner` already applied).
  2. Add PyPI pending trusted publishers for the three projects, which were free on 25 October 2026.
  3. Create a `pypi` environment.
  4. Do a dry run of the release workflow.
  5. Tag `v<version>`: the workflow publishes PyPI, the GitHub release, the MCP Registry entry and GHCR.
  6. Attach the MCPB bundle and try the plugin; `server.json` already declares the two online MCP endpoints
     (`remotes`, `streamable-http`), without announcing yet the `Authorization` header the service now requires.
