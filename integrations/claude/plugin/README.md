# Gardien RGPD, plugin Claude local / GDPR Guardian, local Claude plugin

[Français](#français) · [English](#english)

## Français

Ce plugin installe Gardien RGPD **sur votre poste** pour Claude Code et Cowork (application Claude Desktop). Claude
anonymise un document avec l'outil `anonymize_file` **sans jamais le lire**, puis ne travaille que sur le
Markdown anonymisé (`[PERSONNE_1]`, `[EMAIL_1]`, `[NIR_1]`…). Les balises sont irréversibles : aucune table de
correspondance n'existe. **Le document ne quitte pas la machine** : seul son Markdown anonymisé part vers le
modèle (détails plus bas).

| Élément | Rôle |
|---|---|
| `.mcp.json` | Lance le serveur local : `uvx --from "gdprguardian[local]==1.0.1" gdprguardian mcp --stdio --allow-dir <dossier>`. Même logiciel, même version que le service en ligne. |
| `skills/gdprguardian-local` | Dit à Claude d'utiliser `anonymize_file`, sans jamais ouvrir l'original ; à défaut, le script de la skill, qui anonymise sur le poste avec le moteur embarqué (roues fournies dans les archives de [`skills/`](../../../skills/README.md), absentes du plugin) ou un Gardien RGPD déjà installé. Jamais de service en ligne sans l'accord de l'utilisateur. |
| `hooks/hooks.json` | Hook `PreToolUse` : refuse `Read`, `Grep`, `cat`, `Get-Content`, `Import-Csv`… et les outils MCP tiers sur un document brut. |

Version légère, sans rien installer (service public, MCP en HTTP) : le plugin `gdprguardian-online`,
[`../plugin-online`](../plugin-online/README.md).

### Prérequis

- **uv** ([installation](https://docs.astral.sh/uv/getting-started/installation/)), qui installe Python et
  Gardien RGPD.
- **Une fois, avec le réseau**, dans un terminal : `uv tool install "gdprguardian[local]==1.0.1"` (environ 40 Mo,
  plus Python si uv doit l'installer). Le serveur démarre ensuite **sans réseau**, et sans dépasser le délai de
  démarrage du client. Sans cette étape, le plugin fonctionne aussi, mais `uvx` télécharge Gardien RGPD au premier
  lancement, puis a besoin du réseau à chaque démarrage dès que sa copie de l'index des paquets (PyPI) date de
  plus de quelques minutes : hors ligne, le serveur ne démarre pas. Après une mise à jour du plugin, relancez
  `uv tool install` avec la nouvelle version (celle de `.mcp.json`).
- **Le paquet `gdprguardian` doit être publié sur PyPI**. Tant que ce n'est
  pas le cas, ou si `uv tool install` échoue, utilisez la skill lourde : l'archive `gdprguardian-local.zip` ou
  `gdprguardian-local-windows-macos.zip` de [`skills/`](../../../skills/README.md), qui embarque le moteur.

### Installer

- **Claude Code** : `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, puis
  `claude plugin install gdprguardian@gdprguardian`. Autre dossier dès l'installation :
  `claude plugin install gdprguardian@gdprguardian --config allowed_dir="D:\Dossiers\GDPRGuardian"`.
- **Cowork** : Personnaliser > Plugins > Ajouter > Ajouter une marketplace `FlowLineIntegration/GDPRGuardian`, puis
  ajouter `gdprguardian` (ou Ajouter > Téléverser un plugin, avec une archive zip de ce dossier). Le serveur local
  et le hook tournent quand la session Cowork s'exécute sur votre ordinateur.
- **Conversation de claude.ai et de Claude Desktop** : ce plugin n'y sert pas. Un plugin ajouté au compte s'y
  retrouve, mais seule sa skill s'y charge, sans roues ni serveur local ni hook ; elle répond alors « engine
  missing ». Téléversez plutôt l'archive `gdprguardian-local.zip` comme skill (voir [`../README.md`](../README.md)).

### Le dossier autorisé

Le serveur n'accepte que les fichiers d'**un dossier dédié** : par défaut `GDPRGuardian` dans votre dossier personnel
(`~/GDPRGuardian`, soit `C:\Users\<vous>\GDPRGuardian` sous Windows et `/Users/<vous>/GDPRGuardian` sous macOS).
**Créez-le**, puis déposez-y les documents à anonymiser. Le dossier est relu à chaque appel : le créer après
l'installation suffit, sans redémarrage.

Pourquoi ce défaut :

- Cowork ignore un serveur MCP de plugin dont une option n'a pas de valeur par défaut (il ne pose pas la
  question) : une valeur par défaut est indispensable.
- Un dossier dédié, vide au départ, n'expose rien tant que vous n'y déposez rien. Le modèle ne peut pas faire
  traiter un fichier que vous n'y avez pas mis, ni un fichier qui n'est pas un document (clé SSH, `.env`) : ses
  secrets ne sont pas des données personnelles et passeraient tels quels.
- Ne choisissez jamais votre dossier personnel entier ni un dossier de projet.

Changer de dossier : dans Claude Code, `/plugin` > Installés > gdprguardian > Configurer, puis redémarrer la
session.

### Ce qui reste sur le poste, ce qui part

- **Reste sur le poste** : le fichier, la conversion, l'anonymisation, le texte d'origine. Le nom du fichier
  n'apparaît jamais dans le résultat (seule l'extension sert).
- **Part vers le modèle** : le Markdown anonymisé, le chemin du fichier que Claude passe à l'outil (donc son
  nom : préférez des noms neutres) et, dans les messages d'erreur, le nom du dossier autorisé tel que vous
  l'avez écrit.
- Le hook est un garde-fou, pas un bac à sable ; un texte collé dans la conversation a déjà été lu. Voir les
  limites dans [`../README.md`](../README.md).

### Vérifier

Toujours avec des documents **fictifs** :

1. Déposez un PDF dans `~/GDPRGuardian` et demandez « Résume ~/GDPRGuardian/contrat.pdf » : Claude appelle
   `anonymize_file`, jamais `Read`.
2. Demandez « affiche les 5 premières lignes de ~/GDPRGuardian/clients.csv » : le hook refuse `cat` et `Read`
   (Claude Code et Cowork seulement : la conversation de claude.ai n'exécute pas de hook).
3. Le résumé ne contient que des balises (`[PERSONNE_1]`…).

## English

This plugin installs GDPR Guardian **on your computer** for Claude Code and Cowork (in the Claude Desktop app).
Claude anonymises a document with the `anonymize_file` tool **without ever reading it**, then works only from
the anonymised Markdown (`[PERSONNE_1]`, `[EMAIL_1]`…). Placeholders are irreversible: no mapping table exists.
**The document never leaves the machine**: only its anonymised Markdown goes to the model (details below).

- **Contents.** `.mcp.json` starts the local server (`uvx --from "gdprguardian[local]==1.0.1" gdprguardian mcp --stdio
  --allow-dir <folder>`, the same software and version as the online service); the `gdprguardian-local` skill
  tells Claude to use `anonymize_file` and never open the original, falling back to the skill's script, which
  anonymises on the computer with the bundled engine (wheels shipped in the `skills/` archives, not in the plugin)
  or an installed GDPR Guardian, never an online service without the user's agreement; the `PreToolUse` hook
  denies `Read`, `Grep`, shell
  readers and third-party MCP tools on raw documents. The light plugin `gdprguardian-online` (online MCP over HTTP,
  nothing to install) lives in [`../plugin-online`](../plugin-online/README.md).
- **Prerequisite.** [uv](https://docs.astral.sh/uv/getting-started/installation/). Once, with the network, run
  `uv tool install "gdprguardian[local]==1.0.1"` in a terminal: the server then starts **without any network** and
  within the client's start-up timeout. Without this step the plugin still works, but `uvx` downloads GDPR Guardian
  at first start and then needs the network at every start once its copy of the package index (PyPI) is more
  than a few minutes old: offline, the server does not start. After a plugin update, run `uv tool install` again
  with the new version (the one in `.mcp.json`). **The `gdprguardian` package must be published on PyPI**; until
  then, or whenever `uv tool install` fails, use the heavy skill
  archives from [`skills/`](../../../skills/README.md), which carry the engine.
- **Install.** Claude Code: `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, then
  `claude plugin install gdprguardian@gdprguardian` (add `--config allowed_dir=<folder>` to choose another folder).
  Cowork: Customize > Plugins > Add > Add marketplace `FlowLineIntegration/GDPRGuardian`, then add `gdprguardian`
  (or Add > Upload plugin with a zip of this folder); the local server and the hook run when the Cowork session runs
  on your computer. **Not for the claude.ai or Claude Desktop chat**: a plugin added to the account appears there,
  but only its skill loads, with no wheels, no local server and no hook ("engine missing"); upload the
  `gdprguardian-local.zip` archive as a skill instead.
- **Check**, with fictitious documents only: "Summarise ~/GDPRGuardian/contrat.pdf" calls `anonymize_file`, never
  `Read`; "show the first 5 lines of ~/GDPRGuardian/clients.csv" is denied by the hook (Claude Code and Cowork).
- **Allowed folder.** Only files in **one dedicated folder** are accepted, by default `GDPRGuardian` in your home
  folder (`~/GDPRGuardian`): **create it** and drop the documents there; it is re-read at every call, so no restart
  is needed. A default is required because Cowork ignores a plugin MCP server whose option has no default. A
  dedicated, initially empty folder exposes nothing you did not put there, and keeps non-document files (SSH
  keys, `.env`), whose secrets are not personal data, out of reach. Never pick your whole home folder or a
  project folder. Change it in Claude Code with `/plugin` > Installed > gdprguardian > Configure.
- **What leaves the computer.** Only the anonymised Markdown, the file path Claude passes to the tool (hence the
  file name: prefer neutral names; the name never appears in the result) and, in error messages, the allowed
  folder as you wrote it. The hook is a guardrail, not a sandbox; see the limits in
  [`../README.md`](../README.md).
