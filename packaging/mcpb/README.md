# Paquet MCPB pour Claude Desktop / MCPB bundle for Claude Desktop

[Français](#français) · [English](#english)

## Français

`gdprguardian-1.0.2.mcpb` s'installe dans Claude Desktop (macOS, Windows) par double-clic ou Paramètres >
Extensions. Il ne contient que `manifest.json`, `icon.png` et `LICENSE` : au premier lancement, `uvx` installe
Gardien RGPD à la version épinglée, **la même que celle du plugin Claude et du service en ligne**, puis lance le
serveur MCP local. Rien ne quitte le poste.

```
uvx --from "gdprguardian[local]==1.0.2" gdprguardian mcp --stdio --allow-dir <dossier 1> <dossier 2> ...
```

### Choix du manifeste

| Champ | Valeur | Pourquoi |
|---|---|---|
| `manifest_version` | `0.2` | Version finalisée, celle que la CLI officielle donne aux nouveaux paquets et que tout hôte MCPB connaît. La 0.3 (marquée « WIP » par la CLI 2.1.2) n'ajoute que `icons`, `localization` et `_meta`, inutiles ici ; la 0.4 ajoute `server.type: "uv"`, expérimental, dont la prise en charge par Claude Desktop n'est pas vérifiée. |
| `server.type` | `binary` | Le paquet n'embarque aucun code : l'hôte lance une commande déjà présente (`uvx`). `python` promettrait des dépendances embarquées (`server/lib`), impossibles ici de façon portable (roues compilées : noyau Rust, pypdfium2) ; `node` ajouterait un lanceur à maintenir. |
| `server.entry_point` | `uvx` | Champ obligatoire : l'exécutable réellement lancé. |
| `mcp_config` | la commande ci-dessus | Même ligne que le plugin Claude ; les tests la comparent à `gdprguardian.cli.local_server_args`. |
| `platform_overrides` | `PATH` pour macOS et Linux | Une application graphique ne reçoit pas le `PATH` du terminal : `~/.local/bin` (installateur de uv), `/opt/homebrew/bin` et `/usr/local/bin` y sont ajoutés pour trouver `uvx`. Rien pour Windows, où l'installateur de uv met `uvx` dans le `PATH` de l'utilisateur. |
| `user_config.allowed_directories` | `directory`, `multiple`, `required` | Sélecteur de dossiers. Chaque dossier choisi devient un argument séparé après `--allow-dir` (élément exactement `${user_config.allowed_directories}`). Obligatoire : sans dossier, Claude Desktop ne lance pas le serveur et demande la configuration. |
| `privacy_policies` | absent | Aucun service tiers : rien ne quitte le poste. |
| `compatibility.platforms` | `darwin`, `win32`, `linux` | Roues du noyau prévues pour ces trois systèmes ; Claude Desktop existe sur les deux premiers, d'autres hôtes MCPB sur Linux. |

### Construire

```bash
npm install -g @anthropic-ai/mcpb          # CLI officielle, une fois
python packaging/mcpb/build.py            # mcpb validate, puis mcpb pack -> dist/gdprguardian-1.0.2.mcpb
```

Le script vérifie que la version du manifeste, l'épinglage de `uvx` et la version du plugin Claude sont
identiques, prépare `build/mcpb/` (seulement les trois fichiers), valide puis empaquette. **Il ne signe pas** :
la signature (`mcpb sign --cert … --key …`) revient à l'éditeur, avec son certificat de signature de code.

### Reste à vérifier sur un Claude Desktop vierge (macOS et Windows)

Vérifié ici : `mcpb validate` et `mcpb pack` ; la commande que la fonction officielle `getMcpConfigForManifest`
tire du manifeste (Windows, Linux, macOS simulé), installée depuis un index local qui imite PyPI et pilotée par
le client MCP officiel (outils, anonymisation d'un PDF dans un dossier autorisé, refus hors des dossiers).
Sans réseau, `uvx` ne démarre le serveur que si sa copie de l'index est récente ; après
`uv tool install "gdprguardian[local]==1.0.2"`, il démarre sans réseau (vérifié sous Windows et Linux, réseau
coupé). Non vérifié, faute de machine vierge avec Claude Desktop :

1. Installation par double-clic, affichage de l'icône, du sélecteur de dossiers multiple et de l'obligation
   de choisir au moins un dossier.
2. macOS : `uvx` trouvé grâce au `PATH` de `platform_overrides` (uv installé par son installateur, puis par
   Homebrew) ; sinon, message de Claude Desktop.
3. Windows : `uvx` trouvé après une installation de uv faite avant le lancement de Claude Desktop.
4. Premier lancement : durée du téléchargement de Gardien RGPD face au délai de démarrage de Claude Desktop ;
   sinon, pré-installer avec `uv tool install "gdprguardian[local]==1.0.2"`.
5. Plusieurs dossiers choisis : tous acceptés, un fichier hors dossiers refusé (`not_found`).
6. Disponibilité de l'extension dans Cowork : non documentée pour un `.mcpb` installé seul ; la voie documentée
   vers Cowork est le plugin (`integrations/claude/plugin`).
7. Paquet signé : avertissement de Claude Desktop absent après `mcpb sign` avec le certificat de l'éditeur.

## English

`gdprguardian-1.0.2.mcpb` installs in Claude Desktop (macOS, Windows) by double-click or Settings > Extensions. It
only holds `manifest.json`, `icon.png` and `LICENSE`: at first start, `uvx` installs GDPR Guardian at the pinned
version, **the same as the Claude plugin's and the online service's**, then starts the local MCP server. Nothing
leaves the computer.

- **Manifest choices.** `manifest_version` `0.2`, the finalised version that the official CLI gives new bundles
  and that every MCPB host knows (0.3, marked "WIP" by CLI 2.1.2, only adds `icons`, `localization` and
  `_meta`, unused here; 0.4 adds the experimental `server.type: "uv"`, whose Claude Desktop support is
  unverified). `server.type` `binary` with `entry_point`
  `uvx`: the bundle ships no code and the host runs a command already on the machine (`python` would promise
  bundled dependencies, impossible portably with compiled wheels; `node` would add a launcher to maintain).
  `platform_overrides` add the usual uv locations to `PATH` on macOS and Linux, because GUI apps do not get the
  terminal's `PATH`. `allowed_directories` is a required multiple directory picker; each folder becomes a
  separate argument after `--allow-dir`. No `privacy_policies`: no third-party service is involved.
- **Build.** `npm install -g @anthropic-ai/mcpb`, then `python packaging/mcpb/build.py` (checks that the
  manifest version, the `uvx` pin and the Claude plugin version agree, stages `build/mcpb/`, runs `mcpb
  validate` and `mcpb pack` into `dist/`). It never signs: signing is up to the publisher.
- **Still to check on a clean Claude Desktop (macOS and Windows).** Double-click install and the multiple folder
  picker; `uvx` found on macOS through the `PATH` override and on Windows; first-start download time against
  Claude Desktop's start-up timeout (pre-install with `uv tool install "gdprguardian[local]==1.0.2"`, which also lets
  the server start without any network; without it, `uvx` needs the network once its index copy is a few
  minutes old);
  several folders accepted and a file outside refused; availability in Cowork (the documented path to Cowork is
  the plugin); no warning once signed by the publisher.
