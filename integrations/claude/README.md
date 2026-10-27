# Gardien RGPD pour Claude / GDPR Guardian for Claude

[Français](#français) · [English](#english)

## Français

Objectif : Claude **n'ouvre jamais** le document d'origine. Il le fait anonymiser sans le lire, puis ne
travaille que sur le **Markdown anonymisé** (`[PERSONNE_1]`, `[EMAIL_1]`, `[NIR_1]`…). Les balises sont
**irréversibles** : aucune table de correspondance n'existe.

**Une seule version de Gardien RGPD**, la même en ligne et sur le poste, avec les mêmes outils MCP
(`get_anonymized`, `anonymize_text`, `list_packs`, mêmes options) ; seule l'entrée du document change :
`anonymize_file` lit un fichier du poste, `create_upload` reçoit un envoi.

### Deux skills : la locale d'abord

| | Skill **légère** `gdprguardian-online` | Skill **lourde** `gdprguardian-local` |
|---|---|---|
| Principe | envoie le document au service en ligne, réservé aux détenteurs d'une clé API (MCP ou API REST), ne lit que le Markdown anonymisé | anonymise **là où tourne la skill**, moteur complet embarqué, sans réseau, sans clé |
| À installer | rien (Python 3.9+ pour son script, sinon le connecteur MCP) ; une clé API, remise sur demande | l'archive avec le moteur (22 Mo), Python 3.11 à 3.14 ; ou le plugin local |
| Où va le document | vers le service Gardien RGPD (UE, en mémoire, rien conservé), sous accord de sous-traitance ; jamais vers Claude | nulle part ailleurs : sur le poste (Claude Code, Cowork) ; dans claude.ai et la conversation de Claude Desktop, le bac à sable d'Anthropic, où un fichier joint est déjà parti |
| Quand | aucune voie locale possible, avec une clé API et l'accord de l'utilisateur | **toujours, dès qu'elle peut tourner** ; santé, RH, juridique, secret professionnel ; hors ligne |
| Archive à téléverser ([`skills/`](../../skills/README.md)) | [`gdprguardian-online.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-online.zip) (53 Ko) | `gdprguardian-local.zip` (Linux x86_64 et aarch64) : claude.ai et conversation de Claude Desktop (bac à sable Linux d'Anthropic, **même sur un poste Windows ou Mac**), Claude Code sous Linux ou WSL ; `gdprguardian-local-windows-macos.zip` (Windows x64, macOS Apple Silicon) : **seulement** Claude Code ou un agent lancé directement sous Windows ou macOS |
| Plugin | `gdprguardian-online` : MCP en ligne (HTTP, clé API) + skill | `gdprguardian` : MCP local + skill + garde-fou (Claude Code, Cowork) |

Installées ensemble, la skill locale passe **toujours** en premier ; la skill légère n'envoie un document qu'après
avoir prévenu l'utilisateur (service en ligne, sous accord de sous-traitance) et obtenu son accord, sauf s'il l'a
demandée lui-même. Les deux skills ont les mêmes options (`countries`, `mode` : `fort` par défaut, `essentiel`, ou
`personnalise` avec `disable` ; `label_language`, `rules`, `explain` ; `profile` reste un alias déprécié), les mêmes balises, les mêmes explications (règle et raison de chaque balise, jamais la valeur) et la
même règle : ne jamais lire l'original.

**Seconde passe : données sensibles (RGPD, art. 9 et 10).** Gardien RGPD masque les identifiants, pas les faits
sensibles (santé, origine, opinions politiques, religion, syndicat, génétique, biométrie, vie sexuelle,
infractions). Après l'anonymisation, sauf si la tâche en a besoin (un soignant qui résume un dossier médical garde
la santé, pas la religion), les deux skills font remplacer chaque mention, dans une copie du Markdown faite par le
shell, par `[SANTE_1]`, `[ORIGINE_1]`, `[OPINION_POLITIQUE_1]`, `[RELIGION_1]`, `[SYNDICAT_1]`, `[GENETIQUE_1]`,
`[BIOMETRIE_1]`, `[VIE_SEXUELLE_1]` ou `[INFRACTION_1]` ; l'agent ne travaille ensuite que sur cette copie. Les
balises ne gardent aucune table de correspondance, mais le premier `.anon.md` contient toujours ces faits : à
l'utilisateur de le supprimer. Cette passe est faite par votre IA, pas par Gardien RGPD : probabiliste, non mesurée
par le protocole public, hors des garanties déterministes du produit, et `--explain` ne la couvre pas. Avec un
sous-agent léger chez le même fournisseur (`haiku` dans Claude Code), elle tient ces faits hors du contexte de
l'agent principal, de ses réponses et des outils appelés ensuite, pas hors de portée du fournisseur. Sans sous-agent
(claude.ai, conversation de Claude Desktop), l'agent fait la passe lui-même et lit donc ces faits : elle ne les tient
alors que hors de ses réponses et des outils appelés ensuite. Rien n'est envoyé au service Gardien RGPD.
L'anonymisation reste la barrière ; pour un document très sensible, la skill locale et une relecture humaine restent
conseillées.

### Installer, client par client

| Client | Skill légère | Skill lourde |
|---|---|---|
| **claude.ai** (web) et **conversation de Claude Desktop** | Plugin, le plus simple : Personnaliser > Plugins > Ajouter > Ajouter une marketplace `FlowLineIntegration/GDPRGuardian`, ajouter `gdprguardian-online`, puis, dans l'onglet **Connecteurs** du plugin, ajouter et connecter le connecteur (ajouter un plugin n'ajoute aucun connecteur ; Team et Enterprise : un Owner l'ajoute pour l'organisation). Ou : Personnaliser > Skills > « + » > Créer une skill > Téléverser une skill (`gdprguardian-online.zip`), et le connecteur personnalisé `https://api.gardienrgpd.fr/mcp`. Le service exige la clé API dans l'en-tête de requête `Authorization` (valeur `Bearer` suivie de la clé) | Personnaliser > Skills > « + » > Créer une skill > Téléverser une skill : `gdprguardian-local.zip` (l'archive Linux, même sur un poste Windows ou Mac). Pas le plugin `gdprguardian` : dans la conversation, seule sa skill se charge, sans roues ni serveur local. Dans l'application Claude Desktop, le paquet [MCPB](../../packaging/mcpb/README.md) ajoute l'outil local `anonymize_file`, qui lit le fichier sur le poste |
| **Cowork** | plugin `gdprguardian-online` (même marketplace), puis onglet **Connecteurs** : ajouter et connecter ; clé API dans l'en-tête `Authorization`, comme ci-dessus | plugin `gdprguardian` : serveur MCP local sur le poste, skill, garde-fou |
| **Claude Code** | `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, puis `claude plugin install gdprguardian-online@gdprguardian` ; ou dézipper `gdprguardian-online.zip` dans `~/.claude/skills/` ; clé API dans la variable d'environnement `GDPRGUARDIAN_API_KEY` | `claude plugin install gdprguardian@gdprguardian` (même marketplace) ; ou dézipper `gdprguardian-local-windows-macos.zip` (Windows, macOS) ou `gdprguardian-local.zip` (Linux, WSL) dans `~/.claude/skills/` |
| **Autres agents** (format Agent Skills) | dossier `gdprguardian-online/` de l'archive | dossier `gdprguardian-local/` de l'archive |

- **Avant la publication sur PyPI** : le plugin `gdprguardian` lance
  `uvx --from "gdprguardian[local]==1.0.2"`, qui exige le paquet sur PyPI (la marketplace,
  elle, fonctionne : le dépôt est public). D'ici là, ou si `uv tool install` échoue : téléverser ou dézipper les
  archives de [`skills/`](../../skills/README.md).
- claude.ai et Claude Desktop : les skills exigent l'exécution de code (Paramètres > Capacités ; pour Team et
  Enterprise, selon les réglages de l'organisation). L'archive se téléverse telle quelle : son dossier est à la
  racine, comme l'exige claude.ai.
- **Synchronisation** : un plugin ou une skill ajouté au compte claude.ai se retrouve dans Cowork et, à la session
  suivante, dans Claude Code (v2.1.273 et plus). L'archive Linux téléversée dans claude.ai ne tourne donc pas dans
  Claude Code sous Windows ou macOS (« platform not covered ») : y installer le plugin `gdprguardian` (son outil
  `anonymize_file` passe en premier), ou dézipper `gdprguardian-local-windows-macos.zip` dans `~/.claude/skills/`
  (la copie locale prend le nom court `/gdprguardian-local`, la copie synchronisée ne répond plus qu'à
  `/anthropic-skills:gdprguardian-local`). Un plugin installé en ligne de commande dans Claude Code reste sur ce
  poste.
- Skill lourde : au premier usage, le script installe le moteur **sans réseau** depuis le dossier `wheels/` de la
  skill, dans un dossier privé (cache de l'utilisateur, sinon dossier temporaire) ; `--check` affiche le moteur
  (`rust`, le noyau natif, sur Linux x86_64 et Windows x64 ; `python`, le moteur de référence, ailleurs : mêmes
  résultats, plus lent) et les formats disponibles. Autre voie, pour un environnement Python dédié :
  `pip install --no-index --find-links wheels -r wheels/requirements.txt` (Linux x86_64, Windows x64), ou
  `python scripts/gdprguardian_local.py --setup --pip` (toutes les plateformes couvertes).
- Le plugin local ne contient pas les roues (elles ne vivent que dans les archives) : il utilise d'abord l'outil MCP
  local `anonymize_file`, lancé par `uvx` (voir [`plugin/README.md`](plugin/README.md)).

### Plugin Claude local (recommandé pour les documents sensibles)

Prérequis : [uv](https://docs.astral.sh/uv/getting-started/installation/), puis, une fois avec le réseau,
`uv tool install "gdprguardian[local]==1.0.2"` : le serveur démarre ensuite sans réseau (sans cette étape, `uvx`
revérifie l'index des paquets à chaque démarrage dès que sa copie date de quelques minutes). Le plugin apporte le
serveur MCP local, la skill `gdprguardian-local` et le hook qui bloque la lecture des documents bruts. Seuls les
fichiers du dossier autorisé sont acceptés : par défaut `~/GDPRGuardian`, **à créer**. Le serveur local et le hook
tournent dans Claude Code et dans Cowork, pas dans la conversation de claude.ai ni de Claude Desktop. Détails :
[`plugin/README.md`](plugin/README.md).

### Autres clients MCP, sur le poste

`gdprguardian mcp-config <client> --allow-dir DOSSIER [DOSSIER ...]` affiche la configuration exacte, à la
version installée, pour `claude-desktop`, `claude-code`, `vscode`, `cursor` ou `generic` (où la coller
s'affiche sur la sortie d'erreur). Exemple pour VS Code (`.vscode/mcp.json`) :

```json
{"servers": {"gdprguardian": {"type": "stdio", "command": "uvx",
  "args": ["--from", "gdprguardian[local]==1.0.2", "gdprguardian", "mcp", "--stdio", "--allow-dir", "${workspaceFolder}/Documents"]}}}
```

Claude Desktop (`claude_desktop_config.json`) et Cursor (`mcp.json`) utilisent la clé `mcpServers` ;
Claude Code reçoit une commande `claude mcp add … -- uvx …`. Les serveurs de `claude_desktop_config.json` ne
sont pas chargés par Cowork : pour Cowork, utilisez le plugin.

### Garde-fou sans le plugin

Skill seule : dézipper l'archive dans `~/.claude/skills/` (tous les projets) ou `.claude/skills/` (un projet).
Claude la déclenche seul dès qu'un document est en jeu, ou avec `/gdprguardian-local` ou `/gdprguardian-online`.
Le nom du fichier n'est jamais envoyé ni écrit dans le résultat : seule son extension sert (un nom comme
`CV_Jean_Dupont.pdf` est une donnée personnelle ; le chemin passé au script ou à l'outil figure en revanche dans la
conversation).

Hook : copier `plugin/hooks/block_raw_documents.py` dans `~/.claude/hooks/`, puis ajouter à
`~/.claude/settings.json` (ou `.claude/settings.json` du projet, avec `${CLAUDE_PROJECT_DIR}` dans le chemin) :

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Bash|PowerShell",
        "hooks": [{"type": "command", "command": "python \"$HOME/.claude/hooks/block_raw_documents.py\"; exit $LASTEXITCODE", "timeout": 10}]
      },
      {
        "matcher": "mcp__.*",
        "hooks": [{"type": "command", "command": "python \"$HOME/.claude/hooks/block_raw_documents.py\"; exit $LASTEXITCODE", "timeout": 10}]
      }
    ]
  },
  "permissions": {
    "deny": ["Read(//**/*.pdf)", "Read(//**/*.docx)", "Read(//**/*.doc)", "Read(//**/*.xlsx)", "Read(//**/*.xls)",
             "Read(//**/*.csv)", "Read(//**/*.pptx)", "Read(//**/*.odt)", "Read(//**/*.ods)", "Read(//**/*.msg)",
             "Read(//**/*.eml)"]
  }
}
```

- Un refus sort avec le **code 2** (raison sur stderr et en JSON) : il bloque l'appel quel que soit le mode de
  permission, `bypassPermissions` compris.
- `PowerShell` est l'outil shell de Claude Code sous Windows : sans lui dans `matcher`, `Get-Content` passe.
- Sans réglage, le hook protège ces extensions **partout**. Pour le limiter à des dossiers :
  `GDPRGUARDIAN_PROTECTED_DIRS="/chemin/Clients:/chemin/RH"` (séparateur `;` sous Windows).
  `GDPRGUARDIAN_PROTECTED_EXTENSIONS=".pdf,.docx"` remplace la liste d'extensions.
- Les règles `permissions.deny` forment une **seconde barrière** pour l'outil `Read`. Le préfixe `//` les
  ancre à la racine du disque : elles valent dans tous les projets, même depuis les réglages utilisateur.
- Les scripts des deux skills (`python …/gdprguardian_local.py contrat.pdf`) ne sont pas des lecteurs : le hook les
  laisse passer.
- Le plugin lance le hook par `uv run` (uv étant déjà requis), en forme shell, chemin entre guillemets, suivi de
  `; exit $LASTEXITCODE` : sans ce suffixe, PowerShell (Windows sans Git Bash) rendrait 1 au lieu de 2, un refus
  qui ne bloque pas ; bash et sh, où la variable est vide, gardent le code de la commande. La forme exec (`args`)
  n'est pas utilisée : un hôte qui l'ignorerait lancerait `uv` seul, dont le code 2 bloquerait chaque appel
  d'outil. À la main, si `python` n'est pas dans le `PATH` (Windows), utiliser `py` ou le chemin complet de
  l'interpréteur.
- Échec fermé (facultatif) : `"onFailure": "block"` dans la définition du hook bloque l'appel si le hook
  plante ou dépasse son délai. À activer après avoir vérifié que la commande du hook fonctionne.

### Service en ligne

Le **service en ligne est réservé aux détenteurs d'une clé API**, remise sur demande (contact@gardienrgpd.fr) avec
un accord de sous-traitance (art. 28 RGPD) : `https://api.gardienrgpd.fr` (ou `https://api.gdprguardian.com`), MCP
sur `/mcp`. La clé passe dans l'en-tête `Authorization: Bearer <clé>`, le seul accepté ; sans clé, 401. Il traite en
mémoire et ne garde rien, avec des limites par client (50 Mo au plus par fichier, 1 million de caractères par texte,
quelques documents de 10 Mo d'affilée puis un toutes les 8 secondes, des centaines de petits textes par minute ; 429
ou 503 au-delà, avec `Retry-After`). Il agit pour votre compte, en sous-traitant, sous cet accord : **pour un
document très sensible, préférez la skill lourde ou le plugin local** (sans clé).

- **MCP** : Claude Code, `claude mcp add --transport http gdprguardian https://api.gardienrgpd.fr/mcp --header
  "Authorization: Bearer $GDPRGUARDIAN_API_KEY"` (ou le plugin `gdprguardian-online`) ; claude.ai, Claude Desktop et
  Cowork, le plugin `gdprguardian-online` (onglet Connecteurs) ou un connecteur personnalisé avec cette URL (Team et
  Enterprise : un Owner l'ajoute pour l'organisation), avec un en-tête de requête `Authorization` (valeur `Bearer`
  suivie de la clé) ; Cursor et VS Code, le champ `headers` de la configuration MCP.
- **Script de la skill légère** : service en ligne par défaut, clé lue dans `GDPRGUARDIAN_API_KEY` ;
  `GDPRGUARDIAN_URL` choisit un autre serveur (https, ou http sur la boucle locale seulement). Les limites publiées
  sont au début du script (`MAX_FILE_MB`, `MAX_TEXT_CHARS`). Les règles de l'organisation ne partent qu'avec `--rules` : le script n'envoie jamais de
  lui-même `.gdprguardian/rules.json` ni `GDPRGUARDIAN_RULES` (une liste de noms est une donnée personnelle), et il
  le signale.

**Votre propre serveur** (`deploy/README.md`) : public (`GDPRGUARDIAN_PUBLIC=1`), ou à clés, dont il ne
reçoit que les empreintes (`GDPRGUARDIAN_API_KEY_SHA256`). Avec des clés, le script lit aussi
`GDPRGUARDIAN_API_KEY` (jamais dans un fichier versionné), et le MCP se branche dans Claude Code par `.mcp.json`,
où `${GDPRGUARDIAN_API_KEY}` est lu dans l'environnement au démarrage :
`{"mcpServers": {"gdprguardian": {"type": "http", "url": "https://rgpd.example.eu/mcp",
"headers": {"Authorization": "Bearer ${GDPRGUARDIAN_API_KEY}"}}}}` (`claude mcp add --header …` écrirait la clé en
clair dans la configuration).

### Vérifier

Toujours avec un document **fictif** :

1. Demander à Claude : « Résume `~/GDPRGuardian/contrat.pdf`. » Il doit appeler `anonymize_file` ou le script de la
   skill locale, jamais `Read` ; avec la seule skill légère, il annonce d'abord l'envoi au service et attend
   l'accord avant `create_upload` ou son script.
2. **Seulement avec le hook installé** (plugin `gdprguardian` ou garde-fou ci-dessus) : demander « affiche les 5
   premières lignes de `clients.csv` » ; le hook doit refuser `cat`/`head`. Sans hook (skill légère seule), rien
   ne bloque cette lecture : ne pas faire ce test sur un vrai fichier.
3. Le résumé ne contient que des balises (`[PERSONNE_1]`…) ; « pourquoi cette balise ? » donne la règle et la
   raison (`--explain`), jamais la valeur.

### Limites (à lire)

- **claude.ai et la conversation de Claude Desktop** : un fichier joint à la conversation est déjà parti chez
  Anthropic, et son texte est souvent déjà dans le contexte du modèle ; aucune skill ne l'efface. Les deux skills le
  disent alors une fois, ne citent aucune donnée personnelle du texte brut et font anonymiser la copie jointe (skill
  lourde) ou un envoi depuis le poste de l'utilisateur (skill légère). La skill lourde y tourne dans le bac à sable
  d'exécution de code d'Anthropic (Linux x86_64, Python 3.11) : rien ne part ailleurs, mais ce n'est pas « le
  poste ». La skill légère y passe par le connecteur MCP, car le bac à sable n'atteint en général que les registres
  de paquets (pour Team et Enterprise, un administrateur peut autoriser `api.gardienrgpd.fr`) ; l'utilisateur lance
  alors lui-même, sur son ordinateur, la commande d'envoi renvoyée par `create_upload`, que Claude lui montre (c'est
  l'usage prévu de cette commande à usage unique). Pour que le document ne quitte pas le poste : Claude Code ou
  Cowork, avec la skill lourde ou le plugin local.
- **Taille des archives** : l'API accepte une skill de 30 Mo au plus, fichiers décompressés (limite appliquée aussi
  à claude.ai) ; d'où deux archives lourdes (Linux d'un côté, Windows et macOS de l'autre). Mac Intel, Linux musl,
  Python 3.15 : pas de roues natives dans les archives ; sur Mac Intel seuls le texte, Word et CSV fonctionnent
  (`--check`). PowerPoint : seulement là où `python-pptx` est installé (bac à sable de claude.ai) ; ailleurs, le
  script demande un export PDF.
- **Description des skills** : sous la limite de 1 024 caractères de la spécification Agent Skills et de la page
  « Create custom skills » de claude.com (vérifiée par un test) ; un article d'aide de claude.ai parle encore de
  200 caractères : à confirmer au premier téléversement réel.
- **Français d'abord** : noms et adresses viennent de lexiques français et exigent `FR` dans `countries` ; les noms
  d'autres langues sont souvent manqués. Gardien RGPD est une première barrière, explicable, pas une certification.
- Le hook est un **garde-fou**, pas un bac à sable : il repère les lecteurs courants (y compris derrière
  `sudo`, `xargs`, `find -exec`, `bash -c`, un here-doc, `pwsh -EncodedCommand`, un motif `*.pd?`), mais pas
  un script maison qui lit puis affiche un fichier, ni un glob nu (`cat *`). `Grep` sur un dossier sans filtre
  n'est bloqué que dans `GDPRGUARDIAN_PROTECTED_DIRS`. Gardez les règles `permissions.deny`.
- Un texte **collé dans la conversation** a déjà été lu par le modèle : l'anonymiser ensuite ne le protège
  pas. `anonymize_text` et `--text` ne servent qu'au texte rédigé par l'agent ou déjà partagé.
- En local, le modèle reçoit le Markdown anonymisé, le chemin du fichier qu'il passe à l'outil et, dans les
  messages d'erreur, les dossiers autorisés tels que vous les avez écrits.
- Service en ligne : les utilisateurs qui arrivent par la même adresse de sortie (fournisseur d'IA, réseau
  d'entreprise) partagent un même budget par client.
- Sortie en Markdown seulement (v1) : la mise en page d'origine (DOCX, PDF) n'est pas reconstruite.
- Aucune détection automatique n'est exhaustive : des détails de contexte peuvent subsister.

## English

Goal: Claude **never opens** the original document. It has it anonymised without reading it, then works only
from the **anonymised Markdown**. Placeholders are **irreversible**: no mapping table exists. **One GDPR Guardian
version**, the same online and on the computer, with the same MCP tools and options; only the document intake
differs (`anonymize_file` reads a local file, `create_upload` receives an upload).

**Two skills, local first.**

| | **Light** `gdprguardian-online` | **Heavy** `gdprguardian-local` |
|---|---|---|
| How | sends the document to the online service, reserved for API key holders (MCP or REST), reads only the anonymised Markdown | anonymises **where the skill runs**, full engine bundled, no network, no key |
| Install | nothing (Python 3.9+ for its script, else the MCP connector); an API key, given on request | the archive with the engine (22 MB), Python 3.11 to 3.14; or the local plugin |
| The document goes to | the GDPR Guardian service (EU, in memory, nothing kept), under a processing agreement; never to Claude | nowhere else: the computer (Claude Code, Cowork); in claude.ai and the Claude Desktop chat, Anthropic's sandbox, where an attached file already is |
| When | no local route is possible, with an API key and the user's agreement | **always, whenever it can run**; health, HR, legal, professional secrecy; offline |
| Archive ([`skills/`](../../skills/README.md)) | [`gdprguardian-online.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-online.zip) (53 KB) | `gdprguardian-local.zip` (Linux x86_64 and aarch64): claude.ai and the Claude Desktop chat (Anthropic's Linux sandbox, **even on a Windows or Mac computer**), Claude Code on Linux or WSL; `gdprguardian-local-windows-macos.zip` (Windows x64, Apple-silicon macOS): **only** Claude Code or an agent running directly on Windows or macOS |
| Plugin | `gdprguardian-online`: online MCP (HTTP, API key) + skill | `gdprguardian`: local MCP + skill + guardrail (Claude Code, Cowork) |

Installed together, the local skill **always** comes first; the light skill sends a document only after telling
the user (an online service, under a processing agreement) and getting their agreement, unless they asked for it.

**Second pass: sensitive data (GDPR art. 9 and 10).** GDPR Guardian masks identifiers, not the sensitive facts
(health, origin, political opinions, religion, trade union, genetic, biometric, sex life, offences). After the
anonymisation, unless the task needs them (a clinician summarising a medical file keeps health, not religion), both
skills have each mention replaced, in a shell copy of the Markdown, with `[SANTE_1]`, `[ORIGINE_1]`,
`[OPINION_POLITIQUE_1]`, `[RELIGION_1]`, `[SYNDICAT_1]`, `[GENETIQUE_1]`, `[BIOMETRIE_1]`, `[VIE_SEXUELLE_1]` or
`[INFRACTION_1]` (English tags with English labels); the agent then works only on that copy. The tags keep no
mapping, but the first `.anon.md` still holds those facts: deleting it is the user's decision. The pass is done by
your AI, not by GDPR Guardian: probabilistic, not measured by the public protocol, outside the product's
deterministic guarantees, and `--explain` does not cover it. With a light subagent from the same provider (`haiku`
in Claude Code), it keeps those facts out of the main agent's context, its answers and the tools it calls next, not
out of the provider's reach. Without subagents (claude.ai, the Claude Desktop chat), the agent does the pass itself
and so reads those facts: the pass then only keeps them out of its answers and of the tools it calls next. Nothing
goes to the GDPR Guardian service. The anonymisation remains the barrier; for a very sensitive document, the local
skill and a human check remain advised.

**Install per client.**

- **claude.ai and the Claude Desktop chat.** Light: simplest as a plugin: Customize > Plugins > Add > Add marketplace
  `FlowLineIntegration/GDPRGuardian`, add `gdprguardian-online`, then on the plugin's **Connectors** tab add and
  connect its connector (adding a plugin adds no connector; on Team and Enterprise an Owner adds it for the
  organisation). Or Customize > Skills > "+" > Create skill > Upload a skill (`gdprguardian-online.zip`) plus the
  custom connector `https://api.gardienrgpd.fr/mcp`. The service requires the API key in the `Authorization`
  request header (value `Bearer` followed by the key). Heavy: Customize > Skills > "+" > Create skill > Upload a
  skill with `gdprguardian-local.zip` (the Linux archive, even on a Windows or Mac computer). Not the `gdprguardian`
  plugin there: in chat only its skill loads, with no wheels and no local server. In the Claude Desktop app, the
  [MCPB bundle](../../packaging/mcpb/README.md) adds the local `anonymize_file` tool, which reads the file on the
  computer. Code execution must be on (Settings > Capabilities; on Team and Enterprise, per the organisation's
  settings).
- **Cowork.** The `gdprguardian-online` plugin (then its Connectors tab; API key in the `Authorization` header, as
  above), or the `gdprguardian` plugin (local MCP server on the computer, skill, guardrail).
- **Claude Code.** `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, then `claude plugin install
  gdprguardian-online@gdprguardian` or `claude plugin install gdprguardian@gdprguardian`; or unzip an archive into
  `~/.claude/skills/` (`gdprguardian-local-windows-macos.zip` on Windows and macOS, `gdprguardian-local.zip` on Linux
  and WSL); for the light one, the API key in the `GDPRGUARDIAN_API_KEY` environment variable.
- **Other agents.** The skill folder from the archive (Agent Skills format).
- **Before the package is on PyPI**, the `gdprguardian` plugin
  (`uvx --from "gdprguardian[local]==1.0.2"`) does not work yet (the marketplace itself works: the
  repository is public): upload or unzip the [`skills/`](../../skills/README.md) archives instead,
  which is also the fallback whenever `uv tool install` fails.
- **Sync.** A plugin or skill added to the claude.ai account also appears in Cowork and, at the next session, in
  Claude Code (v2.1.273 and later). The Linux archive uploaded to claude.ai therefore does not run in Claude Code on
  Windows or macOS ("platform not covered"): install the `gdprguardian` plugin there (its `anonymize_file` tool
  comes first), or unzip `gdprguardian-local-windows-macos.zip` into `~/.claude/skills/` (the local copy takes the
  short name `/gdprguardian-local`; the synced one then answers only to `/anthropic-skills:gdprguardian-local`).
  A plugin installed from the Claude Code command line stays on that machine.

**Heavy skill.** On first use the script installs the engine **without any network** from the skill's `wheels/`
folder into a private folder (user cache, else a temporary folder); `--check` prints the engine (`rust`, the native
core, on Linux x86_64 and Windows x64; `python`, the reference engine, elsewhere: same results, slower) and the
available formats. For a dedicated Python environment: `pip install --no-index --find-links wheels -r
wheels/requirements.txt` (Linux x86_64, Windows x64) or `python scripts/gdprguardian_local.py --setup --pip` (every
covered platform). The local plugin carries no wheels (only the archives do): it first uses the local MCP tool
`anonymize_file`, started by `uvx` (prerequisite: [uv](https://docs.astral.sh/uv/), then once, online,
`uv tool install "gdprguardian[local]==1.0.2"`; allowed folder `~/GDPRGuardian`, to create; see
[`plugin/README.md`](plugin/README.md)). Its local server and hook run in Claude Code and Cowork, not in the claude.ai
or Claude Desktop chat.

**Other MCP clients.** `gdprguardian mcp-config <client> --allow-dir DIR [DIR ...]` prints the exact, pinned
configuration for `claude-desktop`, `claude-code`, `vscode`, `cursor` or `generic`. Servers in
`claude_desktop_config.json` are not loaded by Cowork: use the plugin there.

**Guardrail without the plugin.** Copy `plugin/hooks/block_raw_documents.py` to `~/.claude/hooks/` and add the
`settings.json` snippet above (keep `PowerShell` in the matcher: it is Claude Code's shell tool on Windows; keep
`; exit $LASTEXITCODE`: without it, PowerShell turns exit code 2 into 1, a denial that does not block). It denies
`Read`, `Grep`, Bash and PowerShell readers (`cat`, `head`, `type`, `Get-Content`, `Import-Csv`…, also behind
`sudo`, `xargs`, `find -exec`, `bash -c`, here-docs or `pwsh -EncodedCommand`) and MCP tools given a raw document;
the two skills' scripts are not readers and pass. A denial exits with code 2, which blocks the call in every
permission mode, `bypassPermissions` included. Restrict it with `GDPRGUARDIAN_PROTECTED_DIRS` (`os.pathsep`-separated)
and override extensions with `GDPRGUARDIAN_PROTECTED_EXTENSIONS`. Keep the `permissions.deny` rules as a second
layer for `Read`.

**Online service.** **Reserved for API key holders**: the key is given on request (contact@gardienrgpd.fr) with a
processing agreement (GDPR art. 28); `https://api.gdprguardian.com` (or `https://api.gardienrgpd.fr`), MCP on `/mcp`;
the key goes in the `Authorization: Bearer <key>` header, the only one accepted (no key: 401); in memory, nothing
kept; per-client limits (50 MB per file, 1 million characters per text, a few 10 MB documents in a row then one every
8 seconds, hundreds of small texts per minute; 429 or 503 beyond, with `Retry-After`). The service processes the
documents on your behalf, under that agreement: **for a very sensitive document, use the heavy skill or the local
plugin** (no key). MCP: `claude mcp add --transport http gdprguardian https://api.gdprguardian.com/mcp --header
"Authorization: Bearer $GDPRGUARDIAN_API_KEY"` in Claude Code (or the `gdprguardian-online` plugin); in claude.ai,
Claude Desktop and Cowork, the `gdprguardian-online` plugin (Connectors tab) or a custom connector (on Team and
Enterprise an Owner adds it), with an `Authorization` request header (value `Bearer` followed by the key); in Cursor
and VS Code, the `headers` field of the MCP configuration. The light skill's script uses the online service by
default, with the key from `GDPRGUARDIAN_API_KEY`; `GDPRGUARDIAN_URL` picks another server (https, or http
on localhost only); the published limits sit at the top of the script (`MAX_FILE_MB`, `MAX_TEXT_CHARS`). The
organisation's rules leave only with `--rules`: the script never sends `.gdprguardian/rules.json` or
`GDPRGUARDIAN_RULES` on its own (a deny-list of names is personal data) and says so when it finds them. Your own
server can be public (`GDPRGUARDIAN_PUBLIC=1`) or keyed with digests only (`GDPRGUARDIAN_API_KEY_SHA256`); with
keys, the script also reads `GDPRGUARDIAN_API_KEY` (never in a committed file), and in Claude Code prefer `.mcp.json`
with `"Bearer ${GDPRGUARDIAN_API_KEY}"`, read from the environment at start-up.

**Check**, always with a **fictitious** document: ask "Summarise `~/GDPRGuardian/contrat.pdf`": Claude calls
`anonymize_file` or the local skill's script, never `Read` (with only the light skill, it first announces the upload
and waits for a yes). **Only with the hook installed** (the `gdprguardian` plugin or the guardrail above), ask "show
the first 5 lines of `clients.csv`": the hook denies `cat`/`head`; without a hook nothing blocks that read, so never
try it on a real file. The summary only holds placeholders; "why this placeholder?" gives the rule and the reason.

**Limits.** In claude.ai and the Claude Desktop chat, a file attached to the conversation has already been sent to
Anthropic and its text is often already in the model's context; no skill can undo that. Both skills then say so
once, quote no personal data from the raw text, and have the attached copy anonymised (heavy skill) or an upload
sent from the user's computer (light skill). The heavy skill runs there in Anthropic's code sandbox (Linux x86_64,
Python 3.11): nothing goes anywhere else, but it is not "the computer". The light skill goes through the MCP
connector there, because the sandbox usually only reaches package registries (Team and Enterprise admins can allow
`api.gardienrgpd.fr`); the user then runs, on their own computer, the upload command returned by `create_upload`,
which Claude shows them (the intended use of that single-use command). To keep the document on the computer: Claude
Code or Cowork, with the heavy skill or the local plugin. The API takes skills of at most 30 MB of uncompressed
files (applied to claude.ai too), hence two heavy archives; Intel Macs, musl Linux and Python 3.15 have no native
wheels in them (on an Intel Mac only text, Word and CSV work); PowerPoint only where `python-pptx` is installed (the
claude.ai sandbox), elsewhere the script asks for a PDF export. Skill descriptions stay under the 1,024 characters
of the Agent Skills specification and claude.com's "Create custom skills" page (a test checks it); a claude.ai help
article still says 200 characters: confirm on the first real upload. Names and addresses come from French lexicons
and need `FR` in `countries`; names from other languages
are often missed. The hook is a guardrail, not a sandbox: a home-made script that reads then prints a file, or a bare
glob (`cat *`), is not detected. Text pasted into the chat has already been seen by the model. Locally, the model
receives the anonymised Markdown, the file path it passes to the tool and, in error messages, the allowed folders as
you wrote them. On the online service, users behind the same egress address share one client budget. Output is
Markdown only (v1). GDPR Guardian is a first barrier, not a certification; no automated detection is exhaustive.
