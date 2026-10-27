# Gardien RGPD en ligne, plugin Claude léger / GDPR Guardian online, light Claude plugin

[Français](#français) · [English](#english)

## Français

Ce plugin branche Claude (conversation de claude.ai et de Claude Desktop, Cowork, Claude Code) sur le **service
public gratuit** de Gardien RGPD, **sans rien installer** : ni Python, ni uv, ni clé. Claude fait anonymiser un
document **sans le lire**, puis ne travaille que sur le Markdown anonymisé (`[PERSONNE_1]`, `[EMAIL_1]`,
`[NIR_1]`…), aux balises irréversibles.

| Élément | Rôle |
|---|---|
| `.mcp.json` | Serveur MCP en ligne, en HTTP : `https://api.gardienrgpd.fr/mcp`, sans en-tête ni clé. Outils `create_upload`, `get_anonymized`, `anonymize_text`, `list_packs`. |
| `skills/gdprguardian-online` | Dit à Claude de ne jamais ouvrir l'original, de préférer la skill locale si elle est là et de prévenir l'utilisateur avant le premier envoi ; envoie le fichier avec son script (Python 3.9+, bibliothèque standard seule, depuis le disque, seule l'extension du nom part) ou avec les outils MCP ; explications (`--explain`), erreurs (429 et 503 avec `Retry-After`), limites ; puis une seconde passe pour les données sensibles (RGPD, art. 9 et 10 : santé, origine, opinions, religion, syndicat, génétique, biométrie, vie sexuelle, infractions), faite par un modèle léger de l'IA de l'utilisateur (sous-agent `haiku` dans Claude Code ; sans sous-agent, l'agent lui-même, qui lit alors ces faits) sur une copie du Markdown (`[SANTE_1]`, `[INFRACTION_1]`…), sauf si la tâche en a besoin : faite par votre IA, pas par Gardien RGPD, probabiliste, non mesurée par le protocole public, hors des garanties déterministes, et rien n'est renvoyé au service. |

### Installer

- **claude.ai, Claude Desktop, Cowork** : Personnaliser > Plugins > Ajouter > Ajouter une marketplace
  `FlowLineIntegration/GDPRGuardian`, puis ajouter `gdprguardian-online`. **Ajouter le plugin n'ajoute pas le
  connecteur** : ouvrez le plugin, onglet **Connecteurs**, puis ajoutez et connectez le connecteur Gardien RGPD.
  Sur les offres Team et Enterprise, un Owner l'ajoute pour l'organisation ; chacun le connecte ensuite. Sans
  connecteur, la skill se charge mais n'a pas les outils MCP. Le plugin est rattaché au compte : il apparaît aussi
  dans Cowork et, à la session suivante, dans Claude Code.
- **Claude Code** : `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, puis
  `claude plugin install gdprguardian-online@gdprguardian`.
- **Sans marketplace** : téléverser l'archive
  [`skills/gdprguardian-online.zip`](../../../skills/README.md) (Personnaliser > Skills > « + » > Créer une skill >
  Téléverser une skill) et ajouter le connecteur personnalisé `https://api.gardienrgpd.fr/mcp` (Team et Enterprise :
  un Owner).

### Où va le document

Vers le service Gardien RGPD (hébergé dans l'UE, traitement en mémoire, rien n'est conservé), jamais vers Claude ;
seul le Markdown anonymisé revient. Nous y sommes un tiers, sans contrat de traitement : la skill prévient donc
l'utilisateur et attend son accord avant le premier envoi (sauf s'il l'a demandé), et elle cède la place à la
skill locale `gdprguardian-local` (plugin `gdprguardian`, rien ne quitte la machine) quand celle-ci est installée.
Les règles de l'organisation ne partent qu'avec `--rules`. Limites et détails : [`../README.md`](../README.md).

Ce plugin léger n'a pas de garde-fou (hook) : il exigerait uv, et la conversation de claude.ai n'exécute pas de
hook. Pour bloquer aussi la lecture directe des documents dans Claude Code, installez le hook décrit dans
[`../README.md`](../README.md) (section « Garde-fou sans le plugin »).

## English

This plugin connects Claude (the claude.ai and Claude Desktop chat, Cowork, Claude Code) to GDPR Guardian's **free
public service**, with **nothing to install**: no Python, no uv, no key. Claude has a document anonymised **without
reading it**, then works only from the anonymised Markdown, whose placeholders are irreversible.

- **Contents.** `.mcp.json`: the online MCP server over HTTP (`https://api.gardienrgpd.fr/mcp`, no header, no key);
  `skills/gdprguardian-online`: never open the original, prefer the local skill when present, tell the user before
  the first upload; send the file with the skill's script (Python 3.9+, standard library only, streamed from disk,
  only the name's extension is sent) or the MCP tools; explanations, errors (429 and 503 with `Retry-After`) and
  limits; then a second pass for sensitive data (GDPR art. 9 and 10: health, origin, opinions, religion, trade
  union, genetic, biometric, sex life, offences), done by a light model of the user's own AI (a `haiku` subagent in
  Claude Code; without subagents, the agent itself, which then reads those facts) on a copy of the Markdown
  (`[SANTE_1]`, `[INFRACTION_1]`...), unless the task needs those facts: done by your AI, not by GDPR Guardian,
  probabilistic, not measured by the public protocol, outside the deterministic guarantees, and nothing goes back to
  the service.
- **Install in claude.ai, Claude Desktop and Cowork.** Customize > Plugins > Add > Add marketplace
  `FlowLineIntegration/GDPRGuardian`, then add `gdprguardian-online`. **Adding the plugin does not add its
  connector**: open the plugin's **Connectors** tab, then add and connect the GDPR Guardian connector. On Team and
  Enterprise plans an Owner adds it for the organisation; each member then connects it. Without the connector the
  skill loads but has no MCP tools. The plugin belongs to the account, so it also appears in Cowork and, at the next
  session, in Claude Code.
- **Install in Claude Code.** `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, then
  `claude plugin install gdprguardian-online@gdprguardian`.
- **Without the marketplace**: upload
  `skills/gdprguardian-online.zip` (Customize > Skills > "+" > Create skill > Upload a skill) and add the custom
  connector `https://api.gardienrgpd.fr/mcp` (an Owner on Team and Enterprise).
- **Where the document goes.** To the GDPR Guardian service (EU-hosted, in-memory, nothing kept), never to Claude;
  only the anonymised Markdown comes back. We are a third party there, with no processing agreement: the skill tells
  the user and waits for a yes before the first upload (unless they asked for it), and steps aside for the local
  `gdprguardian-local` skill (plugin `gdprguardian`) when it is installed. The organisation's rules leave only with
  `--rules`. This light plugin ships no hook (it would need uv, and the claude.ai chat runs no hooks); add the hook
  from [`../README.md`](../README.md) to also block direct reads in Claude Code.
