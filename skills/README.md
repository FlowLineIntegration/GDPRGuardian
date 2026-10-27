# Skills Claude prêtes à téléverser / Claude skills, ready to upload

[Français](#français) · [English](#english)

## Français

Trois archives, construites par `tools/build_skills.py` à partir des sources du dépôt. Chacune contient **le dossier
de la skill à sa racine**, comme l'exige claude.ai. Les deux premières se téléversent telles quelles dans claude.ai
(Personnaliser > Skills > « + » > Créer une skill > Téléverser une skill) ; la troisième, jamais. Pour Claude Code,
l'archive se dézippe dans le dossier des skills : voir [Installer dans Claude Code](#installer-dans-claude-code).

| Archive | Skill | Contenu | Pour |
|---|---|---|---|
| [`gdprguardian-online.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-online.zip) (environ 53 Ko) | `gdprguardian-online`, légère | `SKILL.md`, un script en bibliothèque standard, `LICENSE` | tous les clients : utilise le service en ligne (MCP ou API REST) avec une clé API, remise sur demande (contact@gardienrgpd.fr) et lue dans `GDPRGUARDIAN_API_KEY`, rien à installer ; sans clé, prenez une archive lourde |
| [`gdprguardian-local.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-local.zip) (environ 22 Mo) | `gdprguardian-local`, lourde | `SKILL.md`, le script, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `wheels/` : Gardien RGPD, son noyau Rust et leurs dépendances pour **Linux x86_64 et aarch64** (glibc), Python 3.11 à 3.14 | claude.ai et la conversation de Claude Desktop (bac à sable Linux d'Anthropic, **même sur un poste Windows ou Mac**) ; Claude Code ou un agent sous Linux ou WSL |
| [`gdprguardian-local-windows-macos.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-local-windows-macos.zip) (environ 22 Mo) | `gdprguardian-local`, lourde | la même skill, roues pour **Windows x64 et macOS Apple Silicon** | **seulement** Claude Code (ou un autre agent) lancé directement sous Windows ou sur un Mac ; jamais pour claude.ai ni la conversation de Claude Desktop |

Deux archives lourdes plutôt qu'une : l'API refuse une skill de plus de 30 Mo (fichiers décompressés), limite
appliquée aussi à claude.ai, et les quatre plateformes ensemble en feraient environ 42. Le noyau Rust est présent
pour Linux x86_64 et Windows x64 ; ailleurs, le moteur Python de référence répond (mêmes résultats, plus lent).
Cowork : préférez les plugins. Mode d'emploi, choix entre les deux skills (la locale d'abord) et installation
client par client : [`integrations/claude/README.md`](../integrations/claude/README.md).

### Installer dans Claude Code

Dézippez l'archive de votre système dans `~/.claude/skills/` (tous les projets) ou dans le dossier `.claude/skills/`
du projet (ce projet seul). `SKILL.md` doit se trouver en `…/.claude/skills/gdprguardian-local/SKILL.md` : un
dossier de plus, et Claude Code ne découvre pas la skill.

```powershell
# Windows (PowerShell) ; pour un seul projet : -DestinationPath .claude\skills
Expand-Archive gdprguardian-local-windows-macos.zip -DestinationPath "$HOME\.claude\skills"
```

```bash
# macOS
unzip gdprguardian-local-windows-macos.zip -d ~/.claude/skills
# Linux et WSL : un système neuf n'a pas unzip ; le module zipfile de Python le remplace, sans réseau
mkdir -p ~/.claude/skills
python3 -m zipfile -e gdprguardian-local.zip ~/.claude/skills/
```

- **Explorateur Windows** : « Extraire tout » ajoute un dossier `gdprguardian-local-windows-macos\` en trop
  (`…\.claude\skills\gdprguardian-local-windows-macos\gdprguardian-local\SKILL.md`), et la skill n'est pas
  découverte. Retirez ce dernier dossier du chemin proposé, ou remontez ensuite `gdprguardian-local\` d'un niveau.
- **Vérifier** : `python <dossier de la skill>/scripts/gdprguardian_local.py --check` (`python3` sous Linux et
  macOS). Le premier appel installe le moteur, sans réseau, en quelques secondes ; la réponse doit contenir
  `"source": "bundled"` et `"engine": "rust"` (Linux x86_64, Windows x64 ; ailleurs `"engine": "python"`, mêmes
  résultats, plus lent). `"source": "environment"` : ce Python a déjà Gardien RGPD à la même version, et c'est lui
  qui sert.
- **Python 3.11 à 3.14.** Sous Windows, `python` ou `py -3`, et toujours le même, car chaque version de Python
  installe sa propre copie du moteur : `python3` n'y est souvent que l'alias du Microsoft Store, et `py` sans `-3`
  suit la ligne `#!` du script, donc le `python3` du `PATH`. Ubuntu 22.04 (Python 3.10) et Debian 11 (3.9) : installez
  d'abord un Python 3.11 ou plus (Ubuntu 22.04 : `sudo apt install python3.11`, avec le réseau), puis lancez le
  script avec lui (`python3.11 …`).
- **Moteur installé** : dans `%LOCALAPPDATA%\gdprguardian\skill` (Windows), `~/Library/Caches/gdprguardian/skill`
  (macOS) ou `~/.cache/gdprguardian/skill` (Linux ; `$XDG_CACHE_HOME/gdprguardian/skill` si la variable est
  définie ; un dossier temporaire si le dossier personnel n'est pas inscriptible) : champ `"path"` de `--check`.
  Environ 23 à 25 Mo par version de Python, chacune dans son sous-dossier ; une nouvelle version de la skill en
  ajoute un sans effacer l'ancien. `GDPRGUARDIAN_SKILL_CACHE` choisit un autre dossier. Désinstaller : supprimer ce
  dossier, puis celui de la skill.

### Reconstruire et vérifier

```bash
python tools/build_local.py                                    # roues de la version, puis ces archives
python tools/build_skills.py build --wheelhouse dist/<version>  # ces archives seules
python tools/build_skills.py check                             # archives conformes aux sources, sans réseau
python tools/build_skills.py lock                              # après un changement d'épinglage (PINS)
python tools/build_skills.py notices --wheelhouse dist/<version>  # après un changement de roue ou de crate
```

- **Reproductible à partir des mêmes roues** : entrées triées, date fixe (1980-01-01), droits fixes, aucune
  compression (les roues sont déjà compressées, et aucune version de zlib n'entre ainsi dans le résultat), fins de
  ligne LF pour les textes : mêmes fichiers de roues, mêmes octets, sous Windows comme sous Linux. La roue pure
  elle-même, reconstruite sur un autre système, peut différer (droits des fichiers ; fins de ligne d'une copie
  Windows sans `.gitattributes`) : `check` compare donc son **contenu** aux sources, pas ses octets.
- **Vérifiable** : `tests/skills/test_archives.py` exige que chaque fichier de skill soit identique à sa source, que
  la roue de Gardien RGPD contienne exactement `src/gdprguardian`, que chaque roue tierce ait l'empreinte de
  `wheels.lock.json`, que chaque noyau porte le contrat des sources et que l'archive se reconstruise au bit près.
  Une source modifiée sans reconstruction fait échouer le test, avec la commande à lancer.
- **Noyaux** : `build` importe le noyau de la plateforme où il tourne et consigne son contrat et son empreinte dans
  `core_contracts.json` ; le noyau Linux se vérifie donc par un `build` sous Linux (WSL), celui de Windows sous
  Windows. `check` refuse un noyau non vérifié ou d'un autre contrat que `src/gdprguardian/_native.py` : sinon il
  serait écarté en silence au profit du moteur Python.
- **Roues** : les tierces sont épinglées par version et empreinte SHA-256 dans `wheels.lock.json` (téléchargées une
  fois depuis PyPI dans `build/skills/wheels/`) ; celles de Gardien RGPD viennent du dossier de la version
  (`dist/<version>/`).
- **Licences** : Gardien RGPD est sous licence MIT (`LICENSE`, dans chaque archive). Les archives lourdes embarquent
  des composants sous MIT, BSD-2 et BSD-3, Apache-2.0, PSF-2.0, Zlib, Unicode-3.0 et, dans pypdfium2 (PDFium), des
  composants sous CC-BY-4.0, licences ICU, FreeType, IJG et autres : la liste complète, avec les textes que les roues
  ne portent pas (cobble, crates Rust du noyau), est dans `THIRD_PARTY_NOTICES.md`, généré par la commande
  `notices` et vérifié par `check`. Ce logiciel utilise le code de FreeType (portions copyright © The FreeType
  Project, www.freetype.org).
- Sans `lxml` ni `Pillow` (trop lourds pour la limite) : PowerPoint n'est lu que là où `python-pptx` est déjà
  installé, comme dans le bac à sable de claude.ai ; ailleurs, le script demande un export PDF.

## English

Three archives, built by `tools/build_skills.py` from the repository's sources. Each holds **the skill folder at
its root**, as claude.ai expects. The first two are uploaded to claude.ai as is (Customize > Skills > "+" > Create
skill > Upload a skill); the third, never. For Claude Code, the archive is unzipped into the skills folder: see
"Install in Claude Code" below.

| Archive | Skill | Content | For |
|---|---|---|---|
| [`gdprguardian-online.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-online.zip) (about 53 KB) | `gdprguardian-online`, light | `SKILL.md`, a standard-library script, `LICENSE` | every client: uses the online service (MCP or REST API) with an API key, given on request (contact@gardienrgpd.fr) and read from `GDPRGUARDIAN_API_KEY`, nothing to install; without a key, take a heavy archive |
| [`gdprguardian-local.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-local.zip) (about 22 MB) | `gdprguardian-local`, heavy | `SKILL.md`, the script, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `wheels/`: GDPR Guardian, its Rust core and their dependencies for **Linux x86_64 and aarch64** (glibc), Python 3.11 to 3.14 | claude.ai and the Claude Desktop chat (Anthropic's Linux sandbox, **even on a Windows or Mac computer**); Claude Code or an agent on Linux or WSL |
| [`gdprguardian-local-windows-macos.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-local-windows-macos.zip) (about 22 MB) | `gdprguardian-local`, heavy | the same skill, wheels for **Windows x64 and Apple-silicon macOS** | **only** Claude Code (or another agent) running directly on Windows or a Mac; never claude.ai or the Claude Desktop chat |

Two heavy archives rather than one: the API refuses a skill over 30 MB of uncompressed files, a limit applied to
claude.ai too, and the four platforms together would take about 42. The Rust core is bundled for Linux x86_64 and
Windows x64; elsewhere the Python reference engine answers (same results, slower). Cowork: prefer the plugins.
Usage, how to choose (local first) and per-client installation:
[`integrations/claude/README.md`](../integrations/claude/README.md).

**Install in Claude Code.** Unzip the archive for your system into `~/.claude/skills/` (every project) or into the
project's `.claude/skills/` folder (that project only). `SKILL.md` must end up at
`…/.claude/skills/gdprguardian-local/SKILL.md`: one folder too many, and Claude Code does not discover the skill.
Windows (PowerShell): `Expand-Archive gdprguardian-local-windows-macos.zip -DestinationPath "$HOME\.claude\skills"`
(one project: `-DestinationPath .claude\skills`).
macOS: `unzip gdprguardian-local-windows-macos.zip -d ~/.claude/skills`. Linux and WSL (a fresh system has no
`unzip`; Python's zipfile module replaces it, offline):
`mkdir -p ~/.claude/skills`, then `python3 -m zipfile -e gdprguardian-local.zip ~/.claude/skills/`. **Windows
Explorer**: "Extract All" adds an extra `gdprguardian-local-windows-macos\` folder
(`…\.claude\skills\gdprguardian-local-windows-macos\gdprguardian-local\SKILL.md`), and the skill is not discovered:
remove that last folder from the suggested path, or move `gdprguardian-local\` up one level afterwards.
**Check**: `python <skill folder>/scripts/gdprguardian_local.py --check` (`python3` on Linux and macOS). The first
call installs the engine, offline, in a few seconds; the answer must show `"source": "bundled"` and
`"engine": "rust"` (Linux x86_64, Windows x64; elsewhere `"engine": "python"`, same results, slower).
`"source": "environment"`: this Python already has GDPR Guardian at the same version, and that copy is used.
**Python 3.11 to 3.14.** On Windows, `python` or `py -3`, and always the same one, since each Python version installs
its own copy of the engine: `python3` is often only the Microsoft Store alias there, and `py` without `-3` follows
the script's `#!` line, hence the `python3` on `PATH`. Ubuntu 22.04 (Python 3.10) and Debian 11 (3.9): first install
a Python 3.11 or later (Ubuntu 22.04: `sudo apt install python3.11`, with the network), then run the script with it
(`python3.11 …`). **Installed engine**: in `%LOCALAPPDATA%\gdprguardian\skill` (Windows),
`~/Library/Caches/gdprguardian/skill` (macOS) or `~/.cache/gdprguardian/skill` (Linux;
`$XDG_CACHE_HOME/gdprguardian/skill` when that variable is set; a temporary folder when the home folder is not
writable): the `"path"` field of `--check`. About 23 to 25 MB per Python version, each in its own subfolder; a new
skill version adds one without deleting the old. `GDPRGUARDIAN_SKILL_CACHE` picks another folder. To uninstall,
delete that folder, then the skill's.

**Rebuild and check.** `python tools/build_local.py` (this version's wheels, then these archives), or
`python tools/build_skills.py build --wheelhouse dist/<version>` (these archives only); `python tools/build_skills.py
check` verifies them offline; `python tools/build_skills.py lock` after changing a pin; `python tools/build_skills.py
notices --wheelhouse dist/<version>` after a wheel or crate change. **Reproducible from the same wheels**: sorted
entries, fixed date (1980-01-01), fixed modes, no compression (wheels are already compressed, and no zlib version
leaks into the result), LF line endings for text: the same wheel files give the same bytes on Windows and Linux.
The pure wheel itself, rebuilt on another system, may differ (file modes; line endings of a Windows checkout without
`.gitattributes`), so `check` compares its **content** with the sources, not its bytes. `tests/skills/test_archives.py`
requires every skill file to equal its source, the GDPR Guardian wheel to hold exactly `src/gdprguardian`, every
third-party wheel to carry its `wheels.lock.json` digest, every core to carry the sources' contract and the archive
to rebuild bit for bit; a source changed without a rebuild fails the test, which prints the command to run.
**Cores**: `build` imports the core of the platform it runs on and records its contract and digest in
`core_contracts.json`, so the Linux core is verified by a `build` on Linux (WSL) and the Windows core on Windows;
`check` refuses an unverified core or one whose contract differs from `src/gdprguardian/_native.py` (it would
otherwise be dropped silently for the Python engine). Third-party wheels are pinned by version and SHA-256 in
`wheels.lock.json` (downloaded once from PyPI into `build/skills/wheels/`); GDPR Guardian's own come from
`dist/<version>/`. **Licences**: GDPR Guardian is MIT (`LICENSE`, in every archive). The heavy archives bundle
components under MIT, BSD-2 and BSD-3, Apache-2.0, PSF-2.0, Zlib, Unicode-3.0 and, inside pypdfium2 (PDFium),
CC-BY-4.0, ICU, FreeType, IJG and other licences: the full list, with the texts the wheels do not carry (cobble, the
core's Rust crates), is in `THIRD_PARTY_NOTICES.md`, generated by `notices` and verified by `check`. This software
uses the FreeType code (portions copyright © The FreeType Project, www.freetype.org). No `lxml` or `Pillow` (too
heavy for the limit): PowerPoint is only read where `python-pptx` is already installed, as in the claude.ai sandbox;
elsewhere the script asks for a PDF export.
