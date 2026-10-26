# gdprguardian-mcp

<!-- mcp-name: io.github.FlowLineIntegration/gdprguardian -->

**Serveur MCP local de Gardien RGPD : vos documents sont anonymisés sur votre poste, rien ne sort.**
**GDPR Guardian local MCP server: documents are anonymised on your computer, nothing leaves it.**

Ce paquet ne contient aucun code : il installe `gdprguardian[local]` de la même version (moteur, noyau Rust,
convertisseurs PDF, Word, Excel, e-mails) et fournit la commande `gdprguardian-mcp`, identique à
`gdprguardian mcp --stdio`. C'est la même version que le service en ligne ; seule change la porte d'entrée.

This package holds no code: it installs `gdprguardian[local]` of the same version and provides the `gdprguardian-mcp`
command, identical to `gdprguardian mcp --stdio`. Same release as the hosted service; only the entry point differs.

## Ce que garantit la variante locale / what the local variant guarantees

- Aucune connexion réseau : le serveur parle à son client par stdin et stdout, n'écoute sur aucun port et
  n'appelle aucun service (vérifié à chaque version par un test qui interdit toute connexion, résolution de nom
  ou lancement de programme imprévu). / No network connection: stdin and stdout only, no port, no remote call
  (checked for every release by a test that forbids any connection, name lookup or unexpected program launch).
- Seuls les fichiers des dossiers de `GDPRGUARDIAN_ALLOWED_DIRS` sont lisibles ; l'IA ne reçoit que le Markdown
  anonymisé, jamais l'original. / Only files under `GDPRGUARDIAN_ALLOWED_DIRS` can be read; the AI only receives the
  anonymised Markdown.
- Anonymisation irréversible : aucune table de correspondance, rien n'est conservé entre deux appels.
  Irreversible: no mapping table, nothing kept between calls.

## Lancer / launch

Il faut [uv](https://docs.astral.sh/uv/). `GDPRGUARDIAN_ALLOWED_DIRS` : dossiers autorisés, séparés par `;` sous
Windows et `:` ailleurs ; ou `--allow-dir <dossier>`, répétable, qui la remplace. / Requires uv. Allowed
directories, separated by `;` on Windows, `:` elsewhere; or `--allow-dir <dir>`, repeatable, which replaces it.

```bash
uvx gdprguardian-mcp@1.0.1
```

Claude Desktop (`claude_desktop_config.json`), Cursor (`~/.cursor/mcp.json`) :

```json
{
  "mcpServers": {
    "gdprguardian": {
      "command": "uvx",
      "args": ["gdprguardian-mcp@1.0.1"],
      "env": { "GDPRGUARDIAN_ALLOWED_DIRS": "C:\\Users\\moi\\Documents\\Dossiers" }
    }
  }
}
```

Claude Code :

```bash
claude mcp add --transport stdio --env GDPRGUARDIAN_ALLOWED_DIRS=/home/moi/dossiers gdprguardian -- uvx gdprguardian-mcp@1.0.1
```

VS Code (`.vscode/mcp.json`) :

```json
{
  "servers": {
    "gdprguardian": {
      "type": "stdio",
      "command": "uvx",
      "args": ["gdprguardian-mcp@1.0.1"],
      "env": { "GDPRGUARDIAN_ALLOWED_DIRS": "${workspaceFolder}" }
    }
  }
}
```

Claude Cowork charge les serveurs locaux déclarés par un plugin : installez le plugin Gardien RGPD (Personnaliser >
Plugins). / Claude Cowork loads local servers declared by a plugin: install the GDPR Guardian plugin.

Sans uv / without uv : `pip install gdprguardian-mcp==1.0.1`, puis la commande `gdprguardian-mcp`. Une application
graphique ne voit pas toujours le PATH du terminal : donnez alors le chemin complet de `uvx` ou de
`gdprguardian-mcp`. / A desktop app may not see the terminal's PATH: give the full path of `uvx` or `gdprguardian-mcp`.

Sans `--offline`, `uvx` consulte l'index (PyPI) à chaque démarrage dès que son cache a plus de quelques minutes :
sans réseau, il échoue. Pour démarrer à coup sûr hors ligne, voir ci-dessous. / Without `--offline`, `uvx` checks
the index (PyPI) at start-up once its cache is a few minutes old, and fails without network; see below.

## Outils / tools

| Outil / tool | Rôle / role |
|---|---|
| `anonymize_file` | lit un fichier autorisé (PDF, Word, Excel, CSV, e-mail…) et renvoie la page 1 du Markdown anonymisé / reads an allowed file, returns page 1 |
| `get_anonymized` | pages suivantes ; le résultat est effacé 2 min après lecture complète / next pages; deleted 2 min after a full read |
| `anonymize_text` | anonymise un texte / anonymises a text |
| `list_packs` | packs pays disponibles / available country packs |

## Pour les plus prudents / for the most cautious

- Installer une fois (`uvx gdprguardian-mcp@1.0.1 --version`), puis lancer avec `--offline` : uv ne contacte plus
  aucun index et démarre depuis son cache (vérifié sans aucune interface réseau). Dans la configuration du client :
  `"args": ["--offline", "gdprguardian-mcp@1.0.1"]`. / Install once, then start with `--offline`: uv contacts no
  index and starts from its cache (checked with no network interface at all).
- Ou installer la commande une fois pour toutes : `uv tool install gdprguardian-mcp==1.0.1`, puis donner au client le
  chemin complet de `gdprguardian-mcp` (affiché par `uv tool dir --bin`) ; uv n'intervient plus au lancement. / Or
  install the command once: `uv tool install gdprguardian-mcp==1.0.1`, then give the client the full path of
  `gdprguardian-mcp` (shown by `uv tool dir --bin`); uv is no longer involved at start-up.
- Poste sans Internet : `pip install --no-index --find-links <dossier de roues> gdprguardian-mcp`. / Air-gapped
  computer: install from a folder of wheels.
- Docker : `--network none --read-only`, dossier monté en lecture seule (voir `deploy/README.md` du dépôt).

Chaque version est construite par GitHub Actions et publiée avec les attestations PyPI (PEP 740) et des SBOM
CycloneDX. / Each release is built by GitHub Actions, published with PyPI attestations and CycloneDX SBOMs.

Licence MIT · Guillaume CLEMENT - Flow Line Intégration.
