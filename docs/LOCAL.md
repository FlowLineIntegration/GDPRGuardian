# Gardien RGPD sur votre poste / GDPR Guardian on your computer

[Français](#français) · [English](#english)

## Français

Pour les plus prudents, Gardien RGPD s'installe sur le poste de travail : **les documents ne quittent pas la
machine**. C'est le même logiciel, à la même version, que le service en ligne (mêmes packs pays, mêmes règles,
mêmes outils MCP) ; seule change la porte d'entrée du document. Chaque version est vérifiée par un test qui
interdit toute connexion réseau, toute résolution de nom et tout lancement de programme imprévu pendant
l'anonymisation de PDF, Word, Excel, CSV, e-mails et HTML, et pendant une session MCP complète.

Le service en ligne, public et gratuit (`https://api.gardienrgpd.fr`, `https://api.gdprguardian.com`, MCP sur `/mcp`,
sans clé ni compte), traite en mémoire et ne garde rien ; mais le document y transite, et nous y sommes un tiers,
sans contrat de traitement. **Pour un document très sensible (santé, RH, dossier judiciaire, secret
professionnel), préférez cette version locale.**

### Choisir sa voie

| Vous utilisez | Installez | Guide |
|---|---|---|
| Claude Code, Cowork | le **plugin Claude** `gdprguardian` (serveur MCP local, skill `gdprguardian-local`, garde-fou) | [`integrations/claude/plugin`](../integrations/claude/plugin/README.md) |
| Claude Code, un agent, sans uv ni réseau (ou tant que le paquet n'est pas sur PyPI) | la **skill lourde** `gdprguardian-local` : moteur complet embarqué, installé sans réseau au premier usage | [`skills`](../skills/README.md) |
| Claude Desktop, en un double clic | le paquet **`gdprguardian-1.0.0.mcpb`** | [`packaging/mcpb`](../packaging/mcpb/README.md) |
| VS Code, Cursor, tout client MCP | la configuration donnée par `gdprguardian mcp-config` | ci-dessous |
| Un registre MCP | le paquet **`gdprguardian-mcp`** | [`packaging/gdprguardian-mcp`](../packaging/gdprguardian-mcp/README.md) |
| Python, la ligne de commande | `pip install "gdprguardian[local]"` | ci-dessous |
| Aucun réseau, même à l'installation | Docker `--network none`, ou des roues copiées | ci-dessous |

### Une fois, avec le réseau

1. Installer [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Installer Gardien RGPD à la version de votre client :

   ```bash
   uv tool install "gdprguardian[local]==1.0.0"
   ```

   Le serveur démarre ensuite **sans aucun réseau** et dans le délai de démarrage des clients. Sans cette
   étape, `uvx` télécharge Gardien RGPD au premier lancement, puis reconsulte l'index des paquets (PyPI) à chaque
   démarrage dès que sa copie a quelques minutes : hors ligne, le serveur ne démarre pas. Refaites cette
   commande, avec la nouvelle version, après chaque mise à jour du plugin ou du paquet.
3. Créer le **dossier autorisé**, par défaut `GDPRGuardian` dans votre dossier personnel (`~/GDPRGuardian`).
   Le serveur ne lit que les fichiers de ce dossier ; le modèle ne peut pas lui faire traiter un autre fichier
   (clé SSH, `.env`, dossier de projet). Ne choisissez jamais votre dossier personnel entier.

### Autres clients MCP

```bash
gdprguardian mcp-config vscode --allow-dir ~/GDPRGuardian        # aussi : claude-desktop, claude-code, cursor, generic
```

La commande affiche la configuration exacte, épinglée à la version installée, et indique sur la sortie
d'erreur où la coller. Elle lance toujours la même ligne :

```bash
uvx --from "gdprguardian[local]==1.0.0" gdprguardian mcp --stdio --allow-dir ~/GDPRGuardian
```

Sous macOS, une application graphique ne voit pas le `PATH` du terminal : remplacez `uvx` par le chemin donné par
`which uvx`. Les serveurs de `claude_desktop_config.json` ne sont pas chargés par Cowork : pour Cowork, utilisez
le plugin.

### Sans client MCP

```bash
pip install "gdprguardian[local]"
gdprguardian anonymize contrat.pdf -o contrat.md     # pays FR par défaut ; --countries all pour une origine inconnue
gdprguardian anonymize - < notes.txt                 # texte UTF-8 sur l'entrée standard
```

### Aucun réseau, même à l'installation

- **Docker** : l'image tourne sans aucune interface réseau autre que `lo`, en lecture seule, sans privilège ;
  recette exacte dans [`deploy/README.md`](../deploy/README.md) (section « Sans réseau »), serveur MCP compris.
- **Poste isolé** : sur une machine connectée, `pip download "gdprguardian[local]==1.0.0" -d roues` (même système et
  même version de Python que le poste cible) ; copier le dossier `roues`, puis sur le poste isolé
  `pip install --no-index --find-links roues "gdprguardian[local]==1.0.0"`.
- **Skill lourde** : les archives de [`skills/`](../skills/README.md) apportent déjà Gardien RGPD, son noyau et ses
  convertisseurs (Linux x86_64 et aarch64 ; Windows x64 et macOS Apple Silicon ; Python 3.11 à 3.14). Le script de la
  skill les installe sans réseau dans un dossier privé ; ou, dans un environnement dédié,
  `pip install --no-index --find-links wheels -r wheels/requirements.txt` (Linux x86_64, Windows x64). Sans le serveur
  MCP : ni `fastmcp`, ni lecture de PowerPoint (`python-pptx`, trop lourd pour l'archive).
- **Dans claude.ai** et la conversation de Claude Desktop, cette même skill (archive Linux `gdprguardian-local.zip`,
  même sur un poste Windows ou Mac) tourne dans le bac à sable d'exécution de code d'Anthropic : rien ne part
  ailleurs, mais ce n'est pas votre poste, et un fichier joint à la conversation y est déjà parti. Le plugin
  `gdprguardian` n'y sert pas : seule sa skill s'y charge, sans roues ni serveur local.

### Ce qui reste sur le poste, ce qui part vers le modèle

- **Reste** : le fichier, sa conversion, le texte d'origine, l'anonymisation. Aucune table de correspondance
  n'existe, rien n'est gardé entre deux appels, et un résultat est effacé dès sa lecture complète.
- **Part vers le modèle** (Claude ou autre) : le Markdown anonymisé (`[PERSONNE_1]`, `[EMAIL_1]`…), le chemin du
  fichier que le modèle passe à l'outil (donc son nom : préférez des noms neutres) et, dans les messages
  d'erreur, les dossiers autorisés tels que vous les avez écrits.
- Un texte **collé dans la conversation** a déjà été lu par le modèle : l'anonymiser ensuite ne le protège pas.

### Vérifier

1. Déposez un PDF dans `~/GDPRGuardian` et demandez « Résume ~/GDPRGuardian/contrat.pdf » : le client appelle
   `anonymize_file`, jamais la lecture directe du fichier.
2. Le résumé ne contient que des balises (`[PERSONNE_1]`…).
3. Un fichier hors du dossier autorisé est refusé (`not_found`).

Gardien RGPD est une première barrière, automatique et explicable, pas une promesse de « zéro fuite » : voir
l'avertissement du [README](../README.md).

## English

For the most cautious, GDPR Guardian installs on the workstation: **documents never leave the machine**. It is the
same software, at the same version, as the online service (same country packs, rules and MCP tools); only the
document intake differs. Every release is checked by a test that forbids any network connection, name lookup or
unexpected program launch while anonymising PDF, Word, Excel, CSV, e-mail and HTML files, and during a full MCP
session.

The free public online service (`https://api.gdprguardian.com`, `https://api.gardienrgpd.fr`, MCP on `/mcp`, no key,
no account) processes in memory and keeps nothing, but the document travels to it and we are a third party there,
with no processing agreement. **For a very sensitive document (health, HR, court file, professional secrecy), use
this local version instead.**

| You use | Install | Guide |
|---|---|---|
| Claude Code, Cowork | the **`gdprguardian` Claude plugin** (local MCP server, `gdprguardian-local` skill, guardrail) | [`integrations/claude/plugin`](../integrations/claude/plugin/README.md) |
| Claude Code, an agent, no uv and no network (or while the package is not on PyPI) | the **heavy skill** `gdprguardian-local`: full engine bundled, installed offline on first use | [`skills`](../skills/README.md) |
| Claude Desktop, one double-click | the **`gdprguardian-1.0.0.mcpb`** bundle | [`packaging/mcpb`](../packaging/mcpb/README.md) |
| VS Code, Cursor, any MCP client | the configuration printed by `gdprguardian mcp-config` | below |
| An MCP registry | the **`gdprguardian-mcp`** package | [`packaging/gdprguardian-mcp`](../packaging/gdprguardian-mcp/README.md) |
| Python, the command line | `pip install "gdprguardian[local]"` | below |
| No network at all, even to install | Docker `--network none`, or copied wheels | below |

**Once, with the network.** Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then
`uv tool install "gdprguardian[local]==1.0.0"`: the server then starts **without any network** and within client
start-up timeouts. Without this step, `uvx` downloads GDPR Guardian at first start and then re-checks the package
index (PyPI) at every start once its copy is a few minutes old, so it fails offline. Run it again with the new
version after each plugin or bundle update. Create the **allowed folder**, by default `~/GDPRGuardian`: the server
only reads files there, so the model cannot have it process anything else (SSH key, `.env`, a project folder).
Never choose your whole home folder.

**Other MCP clients.** `gdprguardian mcp-config vscode --allow-dir ~/GDPRGuardian` (also `claude-desktop`,
`claude-code`, `cursor`, `generic`) prints the exact configuration, pinned to the installed version, and says on
stderr where to paste it. It always runs the same line:
`uvx --from "gdprguardian[local]==1.0.0" gdprguardian mcp --stdio --allow-dir ~/GDPRGuardian`. On macOS, GUI apps
do not get the terminal's `PATH`: use the path given by `which uvx`. Cowork does not load `claude_desktop_config.json`
servers: use the plugin there.

**Without an MCP client.** `pip install "gdprguardian[local]"`, then `gdprguardian anonymize contrat.pdf -o contrat.md`
(countries FR by default; `--countries all` for an unknown origin) or `gdprguardian anonymize - < notes.txt`.

**No network at all.** Docker: the image runs with no interface but `lo`, read-only and unprivileged; exact recipe,
MCP server included, in [`deploy/README.md`](../deploy/README.md) ("Without network"). Air-gapped computer: on a
connected machine with the same OS and Python version, `pip download "gdprguardian[local]==1.0.0" -d wheels`; copy
the folder, then `pip install --no-index --find-links wheels "gdprguardian[local]==1.0.0"`. Heavy skill: the
[`skills/`](../skills/README.md) archives already carry GDPR Guardian, its core and its converters (Linux x86_64 and
aarch64; Windows x64 and Apple-silicon macOS; Python 3.11 to 3.14); the skill's script installs them offline into a
private folder, or, in a dedicated environment, `pip install --no-index --find-links wheels -r
wheels/requirements.txt` (Linux x86_64, Windows x64); no MCP server (`fastmcp`) and no PowerPoint (`python-pptx`,
too heavy for the archive). In claude.ai and the Claude Desktop chat the same skill (the Linux archive
`gdprguardian-local.zip`, even on a Windows or Mac computer) runs in Anthropic's code sandbox: nothing goes anywhere
else, but it is not your computer, and a file attached to the chat is already there. The `gdprguardian` plugin does
not help there: only its skill loads, with no wheels and no local server.

**What stays, what goes to the model.** Stays: the file, its conversion, the original text, the anonymisation;
no mapping table exists, nothing is kept between calls, and a result is wiped once fully read. Goes to the model:
the anonymised Markdown, the file path the model passes to the tool (so its name: prefer neutral names) and, in
error messages, the allowed folders as you wrote them. Text pasted into the chat has already been seen by the
model.

**Check.** Drop a PDF in `~/GDPRGuardian` and ask "Summarise ~/GDPRGuardian/contrat.pdf": the client calls
`anonymize_file`, never a direct read; the summary only holds placeholders; a file outside the allowed folder is
refused (`not_found`). GDPR Guardian is a first barrier, automatic and explainable, not a "zero leak" promise: see the
[README](../README.md) disclaimer.
