# Gardien RGPD · GDPR Guardian

**L'anonymisation intelligente des documents avant leur passage dans une IA.**
**Smart anonymisation of documents before they reach an AI.**

Un seul logiciel, deux noms : **Gardien RGPD** en français, **GDPR Guardian** en anglais.
One piece of software, two names: **Gardien RGPD** in French, **GDPR Guardian** in English.

Gardien RGPD retire les données personnelles d'un document (noms, identifiants nationaux, coordonnées
bancaires, téléphones, adresses, secrets…) **de façon irréversible**, tout en conservant le sens :
chaque personne devient `[PERSONNE_1]`, `[PERSONNE_2]`… de manière cohérente dans tout le document.
Un LLM peut alors résumer, analyser ou comparer le contenu **sans jamais savoir de qui il s'agit**.

Offert gratuitement par [Flow Line Intégration](https://www.flowlineintegration.com/) · conçu par
[Guillaume CLEMENT](https://www.linkedin.com/in/guillaume-clement-erp-cloud/), CTO Data & IA · Licence MIT.
Offered free of charge by Flow Line Intégration · designed by Guillaume CLEMENT, CTO Data & AI · MIT licence.
Version 1.0.1, en phase de recherche et développement / in research and development.

**Vidéo / Video** (muette, 2 min 48 / silent, 2 min 50) : [lancement en français](video/out/gardien-rgpd-lancement-fr.mp4) ·
[launch in English](video/out/gdpr-guardian-launch-en.mp4) ; sur le site / on the site :
<https://gardienrgpd.fr/#video>, <https://gdprguardian.com/#video>.

---

## Pourquoi Gardien RGPD

| | |
|---|---|
| 🔒 **Irréversible, par conception** | Une clé aléatoire est créée pour chaque document puis détruite. Aucune table de correspondance n'existe : ni vous, ni nous, ni l'IA ne pouvons retrouver les noms d'origine. |
| 🧠 **Cohérent pour l'IA** | « M. Dupont », « Jean Dupont », « J. Dupont » et « DUPONT Jean » deviennent la même `[PERSONNE_1]` ; sur 2 463 personnes fictives, 92,2 % gardent une seule balise (26 octobre 2026). Les rôles, les relations et le fil du document sont préservés. |
| 🇫🇷 **Expert des identifiants européens** | NIR (y compris Corse, DOM, NIA), SIREN/SIRET (exception La Poste), TVA, RIB, IBAN de 89 pays, CNI, passeport, permis, RPPS, FINESS… validés par leurs **clés de contrôle officielles**, et pas seulement par des expressions régulières. |
| 🌍 **Packs pays** | `countries=["FR"]` (défaut), plusieurs pays, ou `"all"` pour un document d'origine inconnue : identifiants à clé forte masqués partout, identifiants faibles seulement avec leurs mots-clés locaux. Le mode `"auto"` (pays deviné) reste expérimental. |
| ⚡ **Rapide, sur CPU** | Aucun GPU, aucun appel à un LLM. Noyau optionnel en **Rust** (sans GIL) aux résultats identiques au moteur Python : un message de 2 Ko est traité en moins d'une milliseconde. |
| 📄 **Documents et tableurs** | PDF, Word, PowerPoint, HTML, e-mails, Excel et CSV sont convertis en **Markdown anonymisé**, prêt pour l'IA. Feuilles masquées, commentaires et métadonnées ne fuient pas. |
| 🤖 **Fait pour Claude et les agents** | Serveur **MCP** en ligne ou **sur votre poste** (plugins Claude pour Claude Code, Claude Desktop et Cowork ; VS Code, Cursor…), même logiciel et même version, et **deux skills Claude**, légère (service public, rien à installer) ou lourde (moteur embarqué, rien ne quitte la machine) : Claude fait anonymiser le document sans le lire et ne lit que le Markdown anonymisé. |
| 💻 **Sur votre poste, sans rien envoyer** | Pour les plus prudents : installation locale, aucune connexion réseau pendant le traitement (vérifié à chaque version), ou conteneur Docker sans réseau. Voir [docs/LOCAL.md](docs/LOCAL.md). |
| 🧩 **Vos règles en plus** | Chaque organisation ajoute ses règles dans l'appel (références internes à masquer, numéros de commande à conserver, projets confidentiels), exécutées par un moteur d'expressions **à temps linéaire**, jamais conservées. |
| 🔎 **Explicable** | `explain=true` : pour chaque balise, la règle et la raison (clé de contrôle validée, mot-clé, étiquette de formulaire, règle de l'organisation…), jamais la valeur. Voir [docs/REGLES.md](docs/REGLES.md). |
| 🛡️ **Privacy by design** | Traitement en mémoire uniquement, un processus neuf par document converti, aucun contenu journalisé, hébergement européen, sortie nettoyée des vecteurs d'injection (caractères invisibles, images distantes). |

## Exemple

```text
Entrée :  M. Jean Dupont (jean.dupont@exemple.fr, 06 12 34 56 78), NIR 1 85 05 78 006 084 91,
          IBAN FR76 3000 6000 0112 3456 7890 189. M. Dupont rappellera Mme Claire Martin.

Sortie :  M. [PERSONNE_1] ([EMAIL_1], [TEL_1]), NIR [NIR_1],
          IBAN [IBAN_1]. M. [PERSONNE_1] rappellera Mme [PERSONNE_2].
```

## Service en ligne, gratuit et sans clé / free online service, no key

| | |
|---|---|
| API REST | `https://api.gardienrgpd.fr` · `https://api.gdprguardian.com` (`POST /v1/anonymize/text`, `POST /v1/anonymize/file`, envoi hors bande `/v1/uploads`) |
| MCP en ligne | `https://api.gardienrgpd.fr/mcp` · `https://api.gdprguardian.com/mcp`, **sans clé** : `claude mcp add --transport http gdprguardian https://api.gardienrgpd.fr/mcp`, ou connecteur personnalisé dans claude.ai |
| Page et essai | [gardienrgpd.fr](https://gardienrgpd.fr) · [gdprguardian.com](https://gdprguardian.com) |

```bash
curl -s https://api.gardienrgpd.fr/v1/anonymize/text -H 'Content-Type: application/json' \
  -d '{"text": "Contactez Jean Dupont au 06 12 34 56 78."}'
```

- **Aucune clé, aucun compte, aucun cookie.** Traitement en mémoire, un processus neuf par requête, rien
  n'est conservé ni journalisé ; un résultat différé est effacé 2 minutes après sa lecture complète, ou 10 minutes
  après la dernière lecture.
- **Gros documents** : l'envoi (`PUT`) répond `202` dès le fichier reçu ; le traitement continue et la lecture du
  résultat (`get_anonymized` ou `GET /v1/results/…`) donne l'étape, l'avancement et `retry_after_s` jusqu'au
  résultat.
- **Limites par client**, tenues en mémoire sous un pseudonyme renouvelé chaque jour : quelques documents de
  10 Mo d'affilée puis un toutes les 8 secondes, des centaines de petits textes par minute, 50 Mo au plus par
  fichier et 1 million de caractères par texte ; au-delà, `429` ou `503` avec `Retry-After`. Détails :
  [deploy/README.md](deploy/README.md).
- **Qualité minimale du texte** : un texte lisible (PDF avec couche texte, Word, courriel…). Les images et les pages
  numérisées sans couche texte ne sont pas lues (avertissement). Un PDF dont la couche texte vient d'un OCR de
  mauvaise qualité (mots déformés, césures cassées, symboles parasites) est traité, avec l'avertissement « Texte de
  mauvaise qualité (OCR probable) : détection dégradée, relisez le résultat » : un nom déformé peut échapper à la
  détection. Ce contrôle ne porte que sur les PDF (le produit ne fait pas d'OCR) ; jamais sur un texte collé.
- **Documents très sensibles** (santé, RH, dossier judiciaire, secret professionnel) : sur le service en ligne,
  nous sommes un tiers, sans contrat de traitement ; préférez la **version locale**, où rien ne quitte le poste
  ([docs/LOCAL.md](docs/LOCAL.md)).

**EN.** REST and MCP at `https://api.gdprguardian.com` and `https://api.gardienrgpd.fr` (MCP on `/mcp`), **no key, no
account, no cookie**; in-memory processing, nothing kept or logged; per-client limits (a few 10 MB documents in a
row, then one every 8 seconds; hundreds of small texts per minute; 50 MB per file; 429 or 503 with `Retry-After`
beyond). Big documents: the upload answers `202` once received, then reading the result reports the stage, progress
and `retry_after_s`. Minimum text quality: readable text (scanned pages without a text layer are not read, with a
warning); a PDF whose text layer comes from low-quality OCR is processed with the warning "Low-quality text (likely
OCR): degraded detection, check the result" (PDFs only: the product does no OCR; never on pasted text). For very sensitive documents, use the local version: nothing leaves your computer.

## Skills Claude : légère ou locale / Claude skills: light or local

Claude **n'ouvre jamais le document** : il le fait anonymiser, puis ne lit que le Markdown anonymisé. Deux skills,
archives prêtes à téléverser dans [`skills/`](skills/README.md) ; installées ensemble, **la locale passe d'abord**,
et la légère n'envoie un document qu'après l'accord de l'utilisateur.

| Skill | Ce qu'elle fait | Archive | Plugin |
|---|---|---|---|
| `gdprguardian-online`, légère | envoie le document au service public gratuit (MCP ou API REST), rien à installer | `gdprguardian-online.zip` | `gdprguardian-online` (MCP en ligne + skill) : claude.ai, Claude Desktop, Cowork, Claude Code |
| `gdprguardian-local`, lourde | anonymise **là où elle tourne**, moteur complet embarqué, sans réseau, Python 3.11 à 3.14 | `gdprguardian-local.zip` (Linux : claude.ai et conversation de Claude Desktop, même sur Windows ou Mac ; Linux, WSL) ; `gdprguardian-local-windows-macos.zip` (Claude Code directement sous Windows ou macOS Apple Silicon) | `gdprguardian` (MCP local + skill + garde-fou) : Claude Code, Cowork |

- **claude.ai et Claude Desktop** : Personnaliser > Plugins > Ajouter > Ajouter une marketplace
  `FlowLineIntegration/GDPRGuardian` > `gdprguardian-online`, puis onglet Connecteurs du plugin ; ou Personnaliser >
  Skills > « + » > Créer une skill > Téléverser une skill (exécution de code activée).
- **Claude Code** : `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, puis
  `claude plugin install gdprguardian-online@gdprguardian` ou `claude plugin install gdprguardian@gdprguardian` ; ou
  dézipper une archive dans `~/.claude/skills/`. Le plugin local exige le paquet `gdprguardian` sur PyPI ; sans lui,
  les archives.
- Explications sur demande (règle et raison de chaque balise, jamais la valeur), limites et mode d'emploi :
  [`integrations/claude/README.md`](integrations/claude/README.md). Dans claude.ai, un fichier joint à la
  conversation est déjà parti chez Anthropic : pour qu'il ne quitte pas le poste, Claude Code ou Cowork.

**EN.** Claude **never opens the document**: it has it anonymised, then reads only the anonymised Markdown. Two
skills, as ready-to-upload archives in [`skills/`](skills/README.md); installed together, **the local one comes
first**, and the light one sends a document only once the user agrees. The light `gdprguardian-online` uses the free
public service through MCP or REST, nothing to install (plugin `gdprguardian-online`, for claude.ai, Claude Desktop,
Cowork and Claude Code). The heavy `gdprguardian-local` bundles the full engine and runs with no network, Python 3.11
to 3.14: `gdprguardian-local.zip` (Linux) for claude.ai and the Claude Desktop chat, even on Windows or a Mac, and for
Linux and WSL; `gdprguardian-local-windows-macos.zip` only for Claude Code running directly on Windows or
Apple-silicon macOS; plugin `gdprguardian` (local MCP server and guardrail) for Claude Code and Cowork, which needs the
`gdprguardian` package on PyPI. claude.ai and Claude Desktop: Customize > Plugins > Add > Add marketplace, then the
plugin's Connectors tab, or Customize > Skills > "+" > Create skill > Upload a skill (code execution on); Claude
Code: `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, then install either plugin, or unzip an
archive into `~/.claude/skills/`. Details and limits: [`integrations/claude/README.md`](integrations/claude/README.md).

## Indice de confiance : nous nous notons en public / confidence index: we rate ourselves in public

Protocole 1.1 ([docs/PROTOCOLE.md](docs/PROTOCOLE.md)), deux notes. **Documents normalisés**, l'usage visé (cible :
95 % ou plus) : **<!--q:confidence_index:fr-->—<!--/q--> %**
[<!--q:confidence_ci_low:fr-->—<!--/q-->–<!--q:confidence_ci_high:fr-->—<!--/q-->] (IC 95 %), <!--q:protocol_docs:fr-->—<!--/q-->
documents. **Documents difficiles**, toute l'équipe rouge (51 façons de piéger un texte) :
**<!--q:hard_index:fr-->—<!--/q--> %** [<!--q:hard_ci_low:fr-->—<!--/q-->–<!--q:hard_ci_high:fr-->—<!--/q-->],
<!--q:hard_docs:fr-->—<!--/q--> documents. Campagne du <!--q:protocol_date:fr-->—<!--/q-->, par le **vrai service**,
moteur <!--q:protocol_engine:fr-->—<!--/q--> (« — » : pas encore mesuré, ou sans objet). L'usage mesuré : les textes
qu'une organisation envoie à une IA, de bonne foi (courriels, demandes collées, comptes rendus, courriers RH, contrats,
factures). Une **fuite**, c'est un seul caractère lisible d'une adresse postale, d'un téléphone, d'un courriel ou d'un
autre identifiant direct, quel qu'en soit le titulaire, ou du nom d'une personne ; un nom de société (RGPD,
considérant 14) ou une ville citée comme lieu n'en sont pas. Chaque note est la part des documents sans fuite :
documents normalisés, calculée par famille puis moyennée à poids égal (le volume n'achète aucun poids) ; documents
difficiles, chaque document piégé compte une fois. Intervalle à 95 % par rééchantillonnage stratifié (2 000 tirages,
graine fixe) ; mentions directes entièrement masquées : <!--q:mention_recall_pct:fr-->—<!--/q--> % (normalisés),
<!--q:hard_mention_recall_pct:fr-->—<!--/q--> % (difficiles). Définition et empreintes publiées avant la campagne
([PROTOCOL-REGISTRATION-1.1.json](PROTOCOL-REGISTRATION-1.1.json)). Réserve : les moitiés test des corpus réels ne
sont plus aveugles (déjà notées par la campagne 1.0 et pendant la mise au point du moteur), donc les chiffres réels
sont optimistes.
Protocole 1.0, 7 familles dont les plus faibles (sorties de l'indice en 1.1) : 61,8 % [58,6–66,9], résultat gardé publié ([protocol-2026-10-26.md](benchmarks/results/protocol-2026-10-26.md)).

| Famille (corpus réels : moitié test) / family (real corpora: test half) | Documents | Sans fuite / no leak (%) | Mentions masquées / masked (%) | Précision / precision (%) |
|---|---:|---:|---:|---:|
| *Documents normalisés, l'indice / normalised documents, the index* | | | | |
| Synthétique FR, 10 graines, leurres / synthetic FR, 10 seeds, decoys | <!--q:f_syn_docs:fr-->—<!--/q--> | <!--q:f_syn_nl:fr-->—<!--/q--> | <!--q:f_syn_mr:fr-->—<!--/q--> | <!--q:f_syn_pr:fr-->—<!--/q--> |
| BODACC | <!--q:f_bod_docs:fr-->—<!--/q--> | <!--q:f_bod_nl:fr-->—<!--/q--> | <!--q:f_bod_mr:fr-->—<!--/q--> | <!--q:f_bod_pr:fr-->—<!--/q--> |
| BOAMP | <!--q:f_boa_docs:fr-->—<!--/q--> | <!--q:f_boa_nl:fr-->—<!--/q--> | <!--q:f_boa_mr:fr-->—<!--/q--> | <!--q:f_boa_pr:fr-->—<!--/q--> |
| ParlaMint-FR (gold partiel : borne haute / partial gold: upper bound) | <!--q:f_par_docs:fr-->—<!--/q--> | <!--q:f_par_nl:fr-->—<!--/q--> | <!--q:f_par_mr:fr-->—<!--/q--> | <!--q:f_par_pr:fr-->—<!--/q--> |
| *Documents difficiles, la seconde note / difficult documents, the second score* | | | | |
| Formats du quotidien abîmés (25) / damaged everyday formats (25) | <!--q:f_red_docs:fr-->—<!--/q--> | <!--q:f_red_nl:fr-->—<!--/q--> | <!--q:f_red_mr:fr-->—<!--/q--> | <!--q:f_red_pr:fr-->—<!--/q--> |
| Déguisements volontaires (25) / deliberate obfuscations (25) | <!--q:f_obf_docs:fr-->—<!--/q--> | <!--q:f_obf_nl:fr-->—<!--/q--> | <!--q:f_obf_mr:fr-->—<!--/q--> | <!--q:f_obf_pr:fr-->—<!--/q--> |
| Bruit d'OCR / OCR noise | <!--q:f_ocr_docs:fr-->—<!--/q--> | <!--q:f_ocr_nl:fr-->—<!--/q--> | <!--q:f_ocr_mr:fr-->—<!--/q--> | <!--q:f_ocr_pr:fr-->—<!--/q--> |
| *Publiés à part, hors des deux notes / published apart, outside both scores* | | | | |
| Presse ancienne, OCR de mauvaise qualité / old press, low-quality OCR | <!--q:f_old_docs:fr-->—<!--/q--> | <!--q:f_old_nl:fr-->—<!--/q--> | <!--q:f_old_mr:fr-->—<!--/q--> | <!--q:f_old_pr:fr-->—<!--/q--> |
| MAPA FR (6 documents) | <!--q:f_mapa_docs:fr-->—<!--/q--> | <!--q:f_mapa_nl:fr-->—<!--/q--> | <!--q:f_mapa_mr:fr-->—<!--/q--> | <!--q:f_mapa_pr:fr-->—<!--/q--> |
| Autres langues / other languages (DE, ES, IT, NL, PT, EN) | <!--q:f_oth_docs:fr-->—<!--/q--> | <!--q:f_oth_nl:fr-->—<!--/q--> | <!--q:f_oth_mr:fr-->—<!--/q--> | <!--q:f_oth_pr:fr-->—<!--/q--> |

Garde-fous / guards (%) : texte neutre masqué à tort / neutral text masked by mistake
<!--q:g_overmask:fr-->—<!--/q-->, leurres masqués / decoys masked <!--q:g_decoys:fr-->—<!--/q-->. Témoin négatif
Judilibre (sans annotation) / negative control: <!--q:f_jud_docs:fr-->—<!--/q--> décisions / decisions,
<!--q:f_jud_spans:fr-->—<!--/q--> zones masquées pour 10 000 caractères / masked spans per 10,000 characters.
Limites, sans détour : une première barrière, pas une certification ; les fuites qui restent sont surtout dans les
documents difficiles (retour à la ligne à l'intérieur d'un identifiant, lettres espacées d'un PDF, barres obliques ou
doubles espaces entre chiffres, RIB écrit champ par champ) et dans les adresses des avis BOAMP ; la conversion des PDF, Word et Excel n'est pas mesurée ;
par l'API, un pays choisi sans la France ne masque ni noms ni adresses. Résultats bruts datés et historique des
campagnes, versions précédentes comprises : [benchmarks/results/](benchmarks/results/).

**EN.** Protocol 1.1, two scores. **Normalised documents**, the intended use (target: 95% or more):
**<!--q:confidence_index:en-->—<!--/q-->%** [<!--q:confidence_ci_low:en-->—<!--/q-->–<!--q:confidence_ci_high:en-->—<!--/q-->]
(95% CI), <!--q:protocol_docs:en-->—<!--/q--> documents. **Difficult documents**, the whole red team (51 ways to trap
a text): **<!--q:hard_index:en-->—<!--/q-->%** [<!--q:hard_ci_low:en-->—<!--/q-->–<!--q:hard_ci_high:en-->—<!--/q-->],
<!--q:hard_docs:en-->—<!--/q--> documents. Run of <!--q:protocol_date:en-->—<!--/q-->, through the **real service**,
engine <!--q:protocol_engine:en-->—<!--/q--> ("—": not measured yet, or not applicable). The use case measured: the
texts an organisation sends to an AI, in good faith (e-mails, pasted requests, minutes, HR letters, contracts,
invoices). A **leak** is a single readable character of a postal address, a phone number, an e-mail address or another
direct identifier, whoever it belongs to, or of a person's name; a company name (GDPR, recital 14) or a town named as
a place is not one. Each score is the share of documents with no leak: normalised documents, computed per family, then
averaged with equal weight (volume buys no weight); difficult documents, every trapped document counts once. 95%
interval by stratified resampling (2,000 draws, fixed seed); direct mentions fully masked:
<!--q:mention_recall_pct:en-->—<!--/q-->% (normalised), <!--q:hard_mention_recall_pct:en-->—<!--/q-->% (difficult).
Definition and digests published before the run (PROTOCOL-REGISTRATION-1.1.json). Caveat: the test halves of the real
corpora are no longer blind (scored by the 1.0 run and while the engine was tuned), so the real-corpus figures are
optimistic.
Protocol 1.0, 7 families including the weakest (moved out of the index in 1.1): 61.8% [58.6–66.9], result kept published ([protocol-2026-10-26.md](benchmarks/results/protocol-2026-10-26.md)).
Published apart, outside both scores, with their figures in the table above: old newspapers (low-quality OCR), MAPA FR,
other languages, and the Judilibre control. Known limits: a first barrier, not a certification; the leaks that remain
are mostly in the difficult documents (a line break inside an identifier, the spaced-out letters of a PDF, slashes or
double spaces between digits, French bank details written field by field) and in the addresses of BOAMP notices; the conversion of PDF, Word and Excel files
is not measured; through the API, a country chosen without France masks neither names nor addresses. Dated raw results
and the history of runs, earlier versions included: [benchmarks/results/](benchmarks/results/).

## Démarrage rapide

```bash
pip install "gdprguardian[all]"      # bibliothèque, convertisseurs, API et MCP en ligne
pip install "gdprguardian[local]"    # ou seulement l'usage sur le poste : convertisseurs et MCP local
```

Le noyau Rust (`gdprguardian-core`) s'installe de lui-même sous Windows x64, macOS et Linux (x86-64, ARM64) ;
ailleurs, le moteur Python donne les mêmes résultats, plus lentement. Claude Code, Claude Desktop, Cowork,
VS Code, Cursor : voir [docs/LOCAL.md](docs/LOCAL.md).

```python
from gdprguardian import anonymize

result = anonymize("Contactez Jean Dupont au 06 12 34 56 78.")
print(result.text)     # Contactez [PERSONNE_1] au [TEL_1].
print(result.report)   # entités remplacées, pays retenus, temps de traitement…
```

## Comment ça marche

```
document ──► conversion Markdown ──► normalisation (homoglyphes, caractères invisibles)
        ──► mots-clés de contexte (1 passage) ──► motifs + clés de contrôle (packs pays)
        ──► noms, adresses, organisations ──► fusion, propagation, coréférence
        ──► balises cohérentes ([PERSONNE_1]…) ──► clé détruite ──► Markdown anonymisé
```

Chaque identifiant a un **niveau de confiance** :
- **A** : clé de contrôle forte (NIR, IBAN…), masqué sans condition ;
- **B** : clé faible (Luhn…), masqué si le contexte le confirme ;
- **C** : sans clé, masqué uniquement en présence de contexte.

Gardien RGPD est une **première barrière** : automatique, mesurée, explicable et réglable, pas une promesse de
« zéro fuite ». La cartographie complète des règles, le format des règles d'organisation et le glossaire des
raisons sont dans [docs/REGLES.md](docs/REGLES.md).

```python
from gdprguardian import Anonymizer

rules = {"rules": [{"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}"}], "deny": {"PROJET": ["Opération Phénix"]}}
result = Anonymizer(countries="FR", rules=rules, explain=True).anonymize("Client CLT-204518, Opération Phénix.")
print(result.text)               # Client [CLIENT_ID_1], [PROJET_1].
print(result.report["explain"])  # [{'tag': '[CLIENT_ID_1]', 'rule': 'CUSTOM_1_CLIENT_ID', 'reason': 'custom_rule', ...}]
```

## Performances

Mesures d'octobre 2026, sur un corpus de 1 000 documents fictifs de 1,9 Ko en moyenne (moteur : un cœur ;
service : 16 cœurs sous Linux).

| Mesure | Résultat |
|---|---|
| Document de 2 Ko, noyau Rust | 0,45 ms sous Windows (4,2 Mo/s), 0,48 ms sous Linux |
| Même corpus, moteur Python seul | 3,9 ms sous Windows, 3,7 ms sous Linux |
| Texte de 10 Mo | 2 s |
| Service, texte de 2 Ko de bout en bout | médiane 5,2 ms, 99 % des requêtes sous 8,6 ms |
| Service, 100 PDF de 10 Mo envoyés ensemble | tous traités en 8,7 s |
| Service, 100 fichiers de 10 Mo (Word, PDF, Excel, texte) | tous traités en 34,8 s |

Les temps du service comprennent l'isolement de chaque requête dans un processus neuf. Le noyau Rust donne des
résultats identiques au moteur Python, qui reste la référence. Moteur déployé, remesuré le 26 octobre sur un
portable Windows partagé (Ryzen 7 5800H) : 0,30 ms pour 1 000 caractères, 2,2 ms pour 10 000, médianes sur un cœur
([bench-2026-10-26-standard-rules3.md](benchmarks/results/bench-2026-10-26-standard-rules3.md)). Méthode et détails :
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) et [deploy/README.md](deploy/README.md).

## Nous écrire / Contact us

**FR.** Demandes d'évolution, problèmes de performance, identifiants mal traités ou autres problèmes :
[ouvrez une issue](https://github.com/FlowLineIntegration/GDPRGuardian/issues/new/choose). **Ne collez jamais de
données personnelles réelles** dans une issue : reproduisez le problème avec un exemple fictif. Une faille de
sécurité se signale en privé (voir [SECURITY.md](SECURITY.md)). Contribuer : [CONTRIBUTING.md](CONTRIBUTING.md).

**EN.** Feature requests, performance problems, mishandled identifiers or other problems:
[open an issue](https://github.com/FlowLineIntegration/GDPRGuardian/issues/new/choose). **Never paste real personal
data** into an issue: reproduce the problem with a fictitious example. Report security vulnerabilities privately
(see [SECURITY.md](SECURITY.md)). Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).

## Un outil offert, remerciements / A gift, acknowledgements

**FR.** Chacun peut l'utiliser, s'en inspirer, le reprendre, sans rien imposer. Merci à
[Flow Line Intégration](https://www.flowlineintegration.com/), qui fournit gratuitement le service en ligne.
Conçu par [Guillaume CLEMENT](https://www.linkedin.com/in/guillaume-clement-erp-cloud/), CTO Data & IA. Données,
polices et composants de tiers, avec leurs licences et attributions : [THIRD_PARTY.md](THIRD_PARTY.md).

**EN.** Anyone may use it, learn from it, build on it, with nothing imposed. Thanks to
[Flow Line Intégration](https://www.flowlineintegration.com/), which provides the online service free of charge.
Designed by [Guillaume CLEMENT](https://www.linkedin.com/in/guillaume-clement-erp-cloud/), CTO Data & AI.
Third-party data, fonts and components, with their licences and attributions: [THIRD_PARTY.md](THIRD_PARTY.md).

## Avertissement / Disclaimer

**FR.** Logiciel fourni « en l'état », sans garantie d'aucune sorte, expresse ou implicite.
Guillaume CLEMENT et Flow Line Intégration déclinent toute responsabilité quant à son utilisation,
notamment en cas de donnée personnelle non détectée. Aucune détection automatique n'est exhaustive :
des éléments de contexte (fonction, lieu, date, événement rare) peuvent permettre une ré-identification
indirecte. Gardien RGPD n'est ni une certification de conformité RGPD ni un conseil juridique ; chaque
responsable de traitement reste seul responsable de sa conformité.

**EN.** Software provided "as is", without warranty of any kind, express or implied. Guillaume CLEMENT
and Flow Line Intégration accept no liability for its use, including for undetected personal data.
No automated detection is exhaustive: contextual details (role, place, date, rare event) may allow
indirect re-identification. GDPR Guardian is neither a GDPR compliance certification nor legal advice; each
controller remains solely responsible for its own compliance.

---

Feuille de route et choix techniques : [docs/PLAN.md](docs/PLAN.md). Architecture (noyau Rust, contrat de
parité avec la référence Python, service à un processus par requête) : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Déploiement : [deploy/README.md](deploy/README.md). Sur le poste : [docs/LOCAL.md](docs/LOCAL.md). Publication
d'une version : [docs/PUBLISHING.md](docs/PUBLISHING.md). Protocole public d'auto-évaluation :
[docs/PROTOCOLE.md](docs/PROTOCOLE.md) ; corpus réels : [docs/CORPUS_REELS.md](docs/CORPUS_REELS.md).
