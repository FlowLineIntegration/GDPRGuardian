# Gardien RGPD · GDPR Guardian

[Français](#français) · [English](#english)

## Français

**Gardien RGPD** anonymise vos documents, de façon irréversible, avant qu'ils ne soient confiés à une IA. Noms,
identifiants, coordonnées bancaires, adresses et secrets deviennent des balises cohérentes (`[PERSONNE_1]`,
`[IBAN_1]`…) : l'IA garde le sens du texte sans jamais savoir de qui il s'agit. Aucune table de correspondance
n'existe : la clé tirée pour chaque document est détruite.

- Site : [gardienrgpd.fr](https://gardienrgpd.fr) · service en ligne : `https://api.gardienrgpd.fr` (API REST et MCP).
- Sur votre poste : serveur MCP local pour Claude Code, Claude Desktop, Cowork, VS Code, Cursor ; rien ne quitte
  la machine.
- Moteur : Python, avec un noyau Rust aux résultats identiques ; sur processeur seul, sans LLM.

**État.** Version 1.0.0, en phase de recherche et développement. Le code source sera publié ici sous licence MIT ;
ce dépôt sert d'abord à recevoir vos demandes.

**Nous écrire.** Demandes d'évolution, problèmes de performance, identifiants mal traités ou autres problèmes :
[ouvrez une issue](https://github.com/FlowLineIntegration/GDPRGuardian/issues/new/choose). **Ne collez jamais de
données personnelles réelles** dans une issue : reproduisez le problème avec un exemple fictif. Une faille de
sécurité se signale en privé (voir [SECURITY.md](SECURITY.md)).

Gardien RGPD est une première barrière automatique et explicable, pas une certification de conformité ni un conseil
juridique.

**Un outil offert.** Chacun peut l'utiliser, s'en inspirer, le reprendre, sans rien imposer. Merci à
[Flow Line Intégration](https://www.flowlineintegration.com/), qui fournit gratuitement le service en ligne.
Conçu par [Guillaume CLEMENT](https://www.linkedin.com/in/guillaume-clement-erp-cloud/), CTO Data & IA.

Licence MIT.

## English

**GDPR Guardian** irreversibly anonymises your documents before they are handed to an AI. Names, identifiers,
bank details, addresses and secrets become consistent placeholders (`[PERSONNE_1]`, `[IBAN_1]`…): the AI keeps the
meaning of the text without ever knowing who is who. No mapping table exists: the key drawn for each document is
destroyed.

- Website: [gdprguardian.com](https://gdprguardian.com) · online service: `https://api.gdprguardian.com` (REST API
  and MCP).
- On your computer: a local MCP server for Claude Code, Claude Desktop, Cowork, VS Code, Cursor; nothing leaves the
  machine.
- Engine: Python with a Rust core giving identical results; CPU only, no LLM.

**Status.** Version 1.0.0, in research and development. The source code will be published here under the MIT
licence; this repository first collects your requests.

**Contact us.** Feature requests, performance problems, mishandled identifiers or other problems:
[open an issue](https://github.com/FlowLineIntegration/GDPRGuardian/issues/new/choose). **Never paste real personal
data** into an issue: reproduce the problem with a fictitious example. Report security vulnerabilities privately
(see [SECURITY.md](SECURITY.md)).

GDPR Guardian is an automated, explainable first barrier, not a compliance certification or legal advice.

**A gift.** Anyone may use it, learn from it, build on it, with nothing imposed. Thanks to
[Flow Line Intégration](https://www.flowlineintegration.com/), which provides the online service free of charge.
Designed by [Guillaume CLEMENT](https://www.linkedin.com/in/guillaume-clement-erp-cloud/), CTO Data & AI.

MIT licence.
