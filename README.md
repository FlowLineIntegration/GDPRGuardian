# Gardien RGPD · GDPR Guardian

**Outil expérimental et open source, pour contribuer au respect du RGPD : un filtre de premier niveau à intégrer
aux outils d'IA du marché (MCP, API, skills Claude).**
**An experimental, open-source tool to help with GDPR compliance: a first-level filter to plug into the AI tools
on the market (MCP, API, Claude skills).**

Un seul logiciel, deux noms : **Gardien RGPD** en français, **GDPR Guardian** en anglais.
One piece of software, two names: **Gardien RGPD** in French, **GDPR Guardian** in English.

**Un filtre de premier niveau.** Des règles, des clés de contrôle, des indices de contexte et les règles de
votre organisation masquent les identifiants directs (noms, coordonnées, numéros, adresses IP, dates de
naissance…) avant que le texte n'atteigne une IA : toujours de la même façon, avec une raison nommée pour
chaque balise, sans retour possible. Ce qui dépend du sens (santé, opinions, infractions : RGPD, art. 9 et 10 ;
indices recoupés) revient au niveau suivant : la prochaine étape du projet est un étage LLM gouverné, sans date
annoncée. Les scores publiés mesurent le premier niveau seul. Trois modes, mêmes noms sur l'API, le MCP et le
site : fort (par défaut, on masque tout ce qu'on peut), essentiel, personnalisé (`personnalise` dans l'API).
En pratique, deux étapes : branché sur les IA du quotidien (MCP, skills Claude, API), le Gardien reçoit chaque
document d'abord, puis un modèle léger de votre IA lit le seul texte anonymisé pour signaler ou masquer, au
mieux, ce qui dépend du sens ; pas parfait, mais pragmatique (notre appréciation : cette seconde étape n'est pas
mesurée). Une école, une université ou une institution publique qui reprendrait ce sujet, pour le bien de toute
la collectivité, serait la bienvenue : le code est ouvert (MIT), le protocole public.

**A first-level filter.** Rules, check digits, context cues and your organisation's own rules mask direct
identifiers (names, contact details, numbers, IP addresses, dates of birth…) before the text reaches an AI: the
same way every time, with a named reason for every placeholder, and no way back. What depends on meaning
(health, opinions, offences: GDPR Art. 9 and 10; cross-checked clues) is left to the next level: the project's
next step is a governed LLM stage, with no date announced. The published scores measure the first level only.
Three modes, same names on the API, the MCP and the site: fort (strong, the default: masks everything it can),
essentiel (essential), personnalise (custom).
In practice, two steps: plugged into everyday AIs (MCP, Claude skills, API), the Guardian receives every
document first, then a light model of your own AI reads the anonymised text only, to flag or mask what depends
on meaning, on a best-effort basis; not perfect, but pragmatic (our assessment: this second step is not
measured). A school, university or public institution taking up this subject, for the good of the whole
community, would be most welcome: the code is open (MIT), the protocol public.

Gardien RGPD retire les données personnelles d'un document (noms, identifiants nationaux, coordonnées
bancaires, téléphones, adresses, secrets…) **de façon irréversible**, tout en conservant le sens :
chaque personne devient `[PERSONNE_1]`, `[PERSONNE_2]`… de manière cohérente dans tout le document.
Un LLM peut alors résumer, analyser ou comparer le contenu **sans voir les identifiants masqués**.

Offert gratuitement par [Flow Line Intégration](https://www.flowlineintegration.com/) · conçu par
[Guillaume CLEMENT](https://www.linkedin.com/in/guillaume-clement-erp-cloud/), CTO Data & IA · Licence MIT.
Offered free of charge by Flow Line Intégration · designed by Guillaume CLEMENT, CTO Data & AI · MIT licence.
Version 1.0.2, en phase de recherche et développement / in research and development.

**Vidéo / Video** (muette, 2 min 55 / silent, 2 min 54) : [lancement en français](video/out/gardien-rgpd-lancement-fr.mp4) ·
[launch in English](video/out/gdpr-guardian-launch-en.mp4) ; sur le site / on the site :
<https://gardienrgpd.fr/#video>, <https://gdprguardian.com/#video>.

---

## Pourquoi Gardien RGPD

| | |
|---|---|
| 🔒 **Irréversible, par conception** | Une clé aléatoire est créée pour chaque document puis détruite. Aucune table de correspondance n'existe : ni vous ni nous ne pouvons retrouver, depuis le résultat, une valeur remplacée. |
| 🧠 **Cohérent pour l'IA** | « M. Dupont », « Jean Dupont », « J. Dupont » et « DUPONT Jean » deviennent la même `[PERSONNE_1]` ; sur 2 463 personnes fictives, 92,2 % gardent une seule balise (26 octobre 2026). Les rôles, les relations et le fil du document sont préservés. |
| 🇫🇷 **Identifiants européens vérifiés** | NIR (y compris Corse, DOM, NIA), SIREN/SIRET (exception La Poste), TVA, RIB, IBAN de 89 pays, CNI, passeport, permis, RPPS, FINESS… validés par leurs **clés de contrôle officielles**, et pas seulement par des expressions régulières. |
| 🌍 **Packs pays** | `countries=["FR"]` (défaut), plusieurs pays, ou `"all"` pour un document d'origine inconnue : identifiants à clé forte masqués partout, identifiants faibles seulement avec leurs mots-clés locaux. Le mode `"auto"` (pays deviné) reste expérimental. |
| ⚡ **Rapide, sur CPU** | Aucun GPU, aucun appel à un LLM. Noyau optionnel en **Rust** (sans GIL) aux résultats identiques au moteur Python : un message de 2 Ko est traité en moins d'une milliseconde. |
| 📄 **Documents et tableurs** | PDF, Word, PowerPoint, HTML, e-mails, Excel et CSV sont convertis en **Markdown anonymisé**, prêt pour l'IA. Feuilles masquées, commentaires et métadonnées ne fuient pas. |
| 🤖 **Fait pour Claude et les agents** | Serveur **MCP** en ligne ou **sur votre poste** (plugins Claude pour Claude Code, Claude Desktop et Cowork ; VS Code, Cursor… ; sur le poste, les archives des skills tant que le paquet n'est pas sur PyPI), même logiciel et même version, et **deux skills Claude**, légère (service public, rien à installer) ou lourde (moteur embarqué, rien ne quitte la machine) : Claude fait anonymiser le document sans le lire et ne lit que le Markdown anonymisé. |
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
| `gdprguardian-online`, légère | envoie le document au service public gratuit (MCP ou API REST), rien à installer | [`gdprguardian-online.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-online.zip) | `gdprguardian-online` (MCP en ligne + skill) : claude.ai, Claude Desktop, Cowork, Claude Code |
| `gdprguardian-local`, lourde | anonymise **là où elle tourne**, moteur complet embarqué, sans réseau, Python 3.11 à 3.14 | [`gdprguardian-local.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-local.zip) (Linux : claude.ai et conversation de Claude Desktop, même sur Windows ou Mac ; Linux, WSL) ; [`gdprguardian-local-windows-macos.zip`](https://github.com/FlowLineIntegration/GDPRGuardian/raw/main/skills/gdprguardian-local-windows-macos.zip) (Claude Code directement sous Windows ou macOS Apple Silicon) | `gdprguardian` (MCP local + skill + garde-fou) : Claude Code, Cowork |

- **claude.ai et Claude Desktop** : Personnaliser > Plugins > Ajouter > Ajouter une marketplace
  `FlowLineIntegration/GDPRGuardian` > `gdprguardian-online`, puis onglet Connecteurs du plugin ; ou Personnaliser >
  Skills > « + » > Créer une skill > Téléverser une skill (exécution de code activée).
- **Claude Code** : `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, puis
  `claude plugin install gdprguardian-online@gdprguardian` ou `claude plugin install gdprguardian@gdprguardian` ; ou
  dézipper une archive dans `~/.claude/skills/`. Le plugin local lance `uvx` sur le paquet `gdprguardian`, **pas encore publié sur
  PyPI** : d'ici là, il ne démarre pas ; utilisez les archives.
- Explications sur demande (règle et raison de chaque balise, jamais la valeur), limites et mode d'emploi :
  [`integrations/claude/README.md`](integrations/claude/README.md). Dans claude.ai, un fichier joint à la
  conversation est déjà parti chez Anthropic : pour qu'il ne quitte pas le poste, Claude Code ou Cowork.
- Ensuite, sauf si la tâche en a besoin, un modèle léger de l'IA de l'utilisateur masque dans une copie les données
  sensibles restantes (RGPD, art. 9 et 10 : `[SANTE_1]`…) : une passe probabiliste, non mesurée, hors des garanties
  déterministes.

**EN.** Claude **never opens the document**: it has it anonymised, then reads only the anonymised Markdown. Two
skills, as ready-to-upload archives in [`skills/`](skills/README.md); installed together, **the local one comes
first**, and the light one sends a document only once the user agrees. The light `gdprguardian-online` uses the free
public service through MCP or REST, nothing to install (plugin `gdprguardian-online`, for claude.ai, Claude Desktop,
Cowork and Claude Code). The heavy `gdprguardian-local` bundles the full engine and runs with no network, Python 3.11
to 3.14: `gdprguardian-local.zip` (Linux) for claude.ai and the Claude Desktop chat, even on Windows or a Mac, and for
Linux and WSL; `gdprguardian-local-windows-macos.zip` only for Claude Code running directly on Windows or
Apple-silicon macOS; plugin `gdprguardian` (local MCP server and guardrail) for Claude Code and Cowork, which needs the
`gdprguardian` package on PyPI, **not published yet**: until then, use the archives. claude.ai and Claude Desktop: Customize > Plugins > Add > Add marketplace, then the
plugin's Connectors tab, or Customize > Skills > "+" > Create skill > Upload a skill (code execution on); Claude
Code: `claude plugin marketplace add FlowLineIntegration/GDPRGuardian`, then install either plugin, or unzip an
archive into `~/.claude/skills/`. Then, unless the task needs them, a light model of the user's own AI masks the
remaining sensitive data (GDPR art. 9 and 10: `[SANTE_1]`...) in a copy: a probabilistic pass, not measured, outside
the deterministic guarantees. Details and limits: [`integrations/claude/README.md`](integrations/claude/README.md).

## Indice de confiance : nous nous notons en public / confidence index: we rate ourselves in public

Protocole 1.1 ([docs/PROTOCOLE.md](docs/PROTOCOLE.md)), deux notes. **Documents normalisés**, l'usage visé (cible :
95 % ou plus) : **<!--q:confidence_index:fr-->96,9<!--/q--> %**
[<!--q:confidence_ci_low:fr-->96,2<!--/q-->–<!--q:confidence_ci_high:fr-->97,6<!--/q-->] (IC 95 %), <!--q:protocol_docs:fr-->1 019 385<!--/q-->
documents. **Documents difficiles**, toute l'équipe rouge (51 façons de piéger un texte) :
**<!--q:hard_index:fr-->84,0<!--/q--> %** [<!--q:hard_ci_low:fr-->83,9<!--/q-->–<!--q:hard_ci_high:fr-->84,1<!--/q-->],
<!--q:hard_docs:fr-->548 907<!--/q--> documents. Campagne du <!--q:protocol_date:fr-->26 octobre 2026<!--/q-->, par le **vrai service**,
moteur <!--q:protocol_engine:fr-->1.0.1+4bb5c465425e<!--/q--> (réglage unique, d'avant les modes ; « — » : pas encore mesuré, ou sans objet). L'usage mesuré : les textes
qu'une organisation envoie à une IA, de bonne foi (courriels, demandes collées, comptes rendus, courriers RH, contrats,
factures). Une **fuite**, c'est un seul caractère lisible d'une adresse postale, d'un téléphone, d'un courriel ou d'un
autre identifiant direct, quel qu'en soit le titulaire, ou du nom d'une personne ; un nom de société (RGPD,
considérant 14) ou une ville citée comme lieu n'en sont pas. Chaque note est la part des documents sans fuite :
documents normalisés, calculée par famille puis moyennée à poids égal (le volume n'achète aucun poids) ; documents
difficiles, chaque document piégé compte une fois. Intervalle à 95 % par rééchantillonnage stratifié (2 000 tirages,
graine fixe) ; mentions directes entièrement masquées : <!--q:mention_recall_pct:fr-->99,3<!--/q--> % (normalisés),
<!--q:hard_mention_recall_pct:fr-->95,0<!--/q--> % (difficiles). Définition et empreintes publiées avant la campagne
([PROTOCOL-REGISTRATION-1.1.json](PROTOCOL-REGISTRATION-1.1.json)). Réserve : les moitiés test des corpus réels ne
sont plus aveugles (déjà notées par la campagne 1.0 et pendant la mise au point du moteur), donc les chiffres réels
sont optimistes.
Protocole 1.0, 7 familles dont les plus faibles (sorties de l'indice en 1.1) : 61,8 % [58,6–66,9], résultat gardé publié ([protocol-2026-10-26.md](benchmarks/results/protocol-2026-10-26.md)).
**Notes par mode, moteur 1.0.2** (<!--q:modes_source:fr-->mesure interne, moitié dev<!--/q-->, <!--q:modes_date:fr-->27 octobre 2026<!--/q-->, moteur <!--q:modes_engine:fr-->1.0.2+src.65f7bd2b7075<!--/q--> : données de mise au point, pas encore le protocole public, chiffres optimistes) : **fort** (par défaut) <!--q:fort_index:fr-->96,3<!--/q--> % [<!--q:fort_ci_low:fr-->95,4<!--/q-->–<!--q:fort_ci_high:fr-->97,1<!--/q-->], difficiles <!--q:fort_hard_index:fr-->85,4<!--/q--> %, codes utiles perdus <!--q:fort_code_loss:fr-->14,5<!--/q--> % ; **essentiel** <!--q:ess_index:fr-->92,7<!--/q--> % [<!--q:ess_ci_low:fr-->91,6<!--/q-->–<!--q:ess_ci_high:fr-->93,7<!--/q-->], difficiles <!--q:ess_hard_index:fr-->85,1<!--/q--> %, codes utiles perdus <!--q:ess_code_loss:fr-->4,0<!--/q--> %. Le protocole 1.2 les mesurera sur le vrai service ; il est déclaré avant sa campagne ([PROTOCOL-REGISTRATION-1.2.json](PROTOCOL-REGISTRATION-1.2.json)), et le résultat 1.1 reste affiché.

| Famille (corpus réels : moitié test) / family (real corpora: test half) | Documents | Sans fuite / no leak (%) | Mentions masquées / masked (%) | Précision / precision (%) |
|---|---:|---:|---:|---:|
| *Documents normalisés, l'indice / normalised documents, the index* | | | | |
| Synthétique FR, 10 graines, leurres / synthetic FR, 10 seeds, decoys | <!--q:f_syn_docs:fr-->450 000<!--/q--> | <!--q:f_syn_nl:fr-->97,2<!--/q--> | <!--q:f_syn_mr:fr-->99,6<!--/q--> | <!--q:f_syn_pr:fr-->98,8<!--/q--> |
| BODACC | <!--q:f_bod_docs:fr-->1 335<!--/q--> | <!--q:f_bod_nl:fr-->97,5<!--/q--> | <!--q:f_bod_mr:fr-->99,5<!--/q--> | <!--q:f_bod_pr:fr-->99,2<!--/q--> |
| BOAMP | <!--q:f_boa_docs:fr-->1 408<!--/q--> | <!--q:f_boa_nl:fr-->95,1<!--/q--> | <!--q:f_boa_mr:fr-->98,3<!--/q--> | <!--q:f_boa_pr:fr-->87,7<!--/q--> |
| ParlaMint-FR (gold partiel : borne haute / partial gold: upper bound) | <!--q:f_par_docs:fr-->143<!--/q--> | <!--q:f_par_nl:fr-->97,9<!--/q--> | <!--q:f_par_mr:fr-->99,8<!--/q--> | <!--q:f_par_pr:fr-->—<!--/q--> |
| *Documents difficiles, la seconde note / difficult documents, the second score* | | | | |
| Formats du quotidien abîmés (25) / damaged everyday formats (25) | <!--q:f_red_docs:fr-->284 081<!--/q--> | <!--q:f_red_nl:fr-->84,9<!--/q--> | <!--q:f_red_mr:fr-->96,5<!--/q--> | <!--q:f_red_pr:fr-->98,8<!--/q--> |
| Déguisements volontaires (25) / deliberate obfuscations (25) | <!--q:f_obf_docs:fr-->252 895<!--/q--> | <!--q:f_obf_nl:fr-->86,6<!--/q--> | <!--q:f_obf_mr:fr-->94,5<!--/q--> | <!--q:f_obf_pr:fr-->98,8<!--/q--> |
| Bruit d'OCR / OCR noise | <!--q:f_ocr_docs:fr-->11 931<!--/q--> | <!--q:f_ocr_nl:fr-->9,2<!--/q--> | <!--q:f_ocr_mr:fr-->72,8<!--/q--> | <!--q:f_ocr_pr:fr-->98,6<!--/q--> |
| *Publiés à part, hors des deux notes / published apart, outside both scores* | | | | |
| Presse ancienne, OCR de mauvaise qualité / old press, low-quality OCR | <!--q:f_old_docs:fr-->272<!--/q--> | <!--q:f_old_nl:fr-->17,3<!--/q--> | <!--q:f_old_mr:fr-->55,2<!--/q--> | <!--q:f_old_pr:fr-->75,5<!--/q--> |
| MAPA FR (6 documents) | <!--q:f_mapa_docs:fr-->6<!--/q--> | <!--q:f_mapa_nl:fr-->16,7<!--/q--> | <!--q:f_mapa_mr:fr-->33,1<!--/q--> | <!--q:f_mapa_pr:fr-->46,8<!--/q--> |
| Autres langues / other languages (DE, ES, IT, NL, PT, EN) | <!--q:f_oth_docs:fr-->646<!--/q--> | <!--q:f_oth_nl:fr-->5,7<!--/q--> | <!--q:f_oth_mr:fr-->14,0<!--/q--> | <!--q:f_oth_pr:fr-->—<!--/q--> |

Garde-fous / guards (%) : texte neutre masqué à tort / neutral text masked by mistake
<!--q:g_overmask:fr-->0,07<!--/q-->, leurres masqués / decoys masked <!--q:g_decoys:fr-->3,7<!--/q-->. Témoin négatif
Judilibre (sans annotation) / negative control: <!--q:f_jud_docs:fr-->300<!--/q--> décisions / decisions,
<!--q:f_jud_spans:fr-->11,5<!--/q--> zones masquées pour 10 000 caractères / masked spans per 10,000 characters.
Limites, sans détour : une première barrière, pas une certification ; les fuites qui restent sont surtout dans les
documents difficiles (retour à la ligne à l'intérieur d'un identifiant, lettres espacées d'un PDF, barres obliques ou
doubles espaces entre chiffres, RIB écrit champ par champ) et dans les adresses des avis BOAMP ; la conversion des PDF, Word et Excel n'est pas mesurée ;
par l'API, un pays choisi sans la France ne masque ni noms ni adresses. Résultats bruts datés et historique des
campagnes, versions précédentes comprises : [benchmarks/results/](benchmarks/results/).

**EN.** Protocol 1.1, two scores. **Normalised documents**, the intended use (target: 95% or more):
**<!--q:confidence_index:en-->96.9<!--/q-->%** [<!--q:confidence_ci_low:en-->96.2<!--/q-->–<!--q:confidence_ci_high:en-->97.6<!--/q-->]
(95% CI), <!--q:protocol_docs:en-->1,019,385<!--/q--> documents. **Difficult documents**, the whole red team (51 ways to trap
a text): **<!--q:hard_index:en-->84.0<!--/q-->%** [<!--q:hard_ci_low:en-->83.9<!--/q-->–<!--q:hard_ci_high:en-->84.1<!--/q-->],
<!--q:hard_docs:en-->548,907<!--/q--> documents. Run of <!--q:protocol_date:en-->26 October 2026<!--/q-->, through the **real service**,
engine <!--q:protocol_engine:en-->1.0.1+4bb5c465425e<!--/q--> (single setting, before modes; "—": not measured yet, or not applicable). The use case measured: the
texts an organisation sends to an AI, in good faith (e-mails, pasted requests, minutes, HR letters, contracts,
invoices). A **leak** is a single readable character of a postal address, a phone number, an e-mail address or another
direct identifier, whoever it belongs to, or of a person's name; a company name (GDPR, recital 14) or a town named as
a place is not one. Each score is the share of documents with no leak: normalised documents, computed per family, then
averaged with equal weight (volume buys no weight); difficult documents, every trapped document counts once. 95%
interval by stratified resampling (2,000 draws, fixed seed); direct mentions fully masked:
<!--q:mention_recall_pct:en-->99.3<!--/q-->% (normalised), <!--q:hard_mention_recall_pct:en-->95.0<!--/q-->% (difficult).
Definition and digests published before the run (PROTOCOL-REGISTRATION-1.1.json). Caveat: the test halves of the real
corpora are no longer blind (scored by the 1.0 run and while the engine was tuned), so the real-corpus figures are
optimistic.
Protocol 1.0, 7 families including the weakest (moved out of the index in 1.1): 61.8% [58.6–66.9], result kept published ([protocol-2026-10-26.md](benchmarks/results/protocol-2026-10-26.md)).
**Scores per mode, engine 1.0.2** (internal measurement, dev half, <!--q:modes_date:en-->27 October 2026<!--/q-->, engine <!--q:modes_engine:en-->1.0.2+src.65f7bd2b7075<!--/q-->: tuning data, not yet the public protocol, so optimistic figures): **strong** (default) <!--q:fort_index:en-->96.3<!--/q-->% [<!--q:fort_ci_low:en-->95.4<!--/q-->–<!--q:fort_ci_high:en-->97.1<!--/q-->], difficult <!--q:fort_hard_index:en-->85.4<!--/q-->%, useful codes lost <!--q:fort_code_loss:en-->14.5<!--/q-->%; **essential** <!--q:ess_index:en-->92.7<!--/q-->% [<!--q:ess_ci_low:en-->91.6<!--/q-->–<!--q:ess_ci_high:en-->93.7<!--/q-->], difficult <!--q:ess_hard_index:en-->85.1<!--/q-->%, useful codes lost <!--q:ess_code_loss:en-->4.0<!--/q-->%. Protocol 1.2 will measure them through the real service; it is registered before its run (PROTOCOL-REGISTRATION-1.2.json), and the 1.1 result stays shown.
Published apart, outside both scores, with their figures in the table above: old newspapers (low-quality OCR), MAPA FR,
other languages, and the Judilibre control. Known limits: a first barrier, not a certification; the leaks that remain
are mostly in the difficult documents (a line break inside an identifier, the spaced-out letters of a PDF, slashes or
double spaces between digits, French bank details written field by field) and in the addresses of BOAMP notices; the conversion of PDF, Word and Excel files
is not measured; through the API, a country chosen without France masks neither names nor addresses. Dated raw results
and the history of runs, earlier versions included: [benchmarks/results/](benchmarks/results/).

## Démarrage rapide

> **Pas encore sur PyPI.** Les paquets `gdprguardian`, `gdprguardian-core` et `gdprguardian-mcp` 1.0.2 ne sont pas encore publiés : les commandes `pip install`, `uv tool install` et `uvx` ci-dessous échouent d'ici là, comme le plugin local `gdprguardian`, `gdprguardian mcp-config` et le paquet `.mcpb`. Sans rien installer : le site, l'API et le MCP en ligne. Sur le poste : les archives de [`skills/`](skills/README.md) (moteur, noyau et convertisseurs embarqués, sans réseau), ou depuis le code : `git clone` du dépôt puis `uv sync --extra local` (Python 3.11+ et Rust : le noyau se construit depuis `rust/`).
> *Not on PyPI yet: until then the commands below fail; use the online service, the `skills/` archives (engine bundled) or a clone of the repository with `uv sync --extra local` (Python 3.11+ and Rust).*

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

**FR.** Gardien RGPD est un outil expérimental et open source, pour contribuer au respect du RGPD : il aide à limiter les données personnelles confiées à une IA, sans suffire à assurer la conformité. Le logiciel (licence MIT) et le service en ligne sont fournis en l'état, sans garantie. L'outil masque des identifiants directs, pas tous, et ne lit pas le sens (santé, opinions, recoupements) : le texte produit peut encore permettre d'identifier quelqu'un. Traitez-le comme des données personnelles et vérifiez les résultats avant de vous y fier. Passer un document dans l'outil est déjà un traitement de données personnelles : vous en restez responsable. En ligne, vos documents passent par notre serveur, sans contrat de sous-traitance : à vous de juger si cet envoi est permis ; sinon, utilisez la [version locale](docs/LOCAL.md). Dans toute la mesure permise par la loi, et sans préjudice des droits qu'elle ne permet pas d'écarter, Flow Line Intégration et les auteurs du projet déclinent toute responsabilité quant à l'usage que vous faites de l'outil et de ses résultats. Ni certification ni conseil juridique.

**EN.** GDPR Guardian is an experimental, open-source tool to help with GDPR compliance: it reduces the personal data you hand to an AI, but is not enough on its own to ensure compliance. The software (MIT licence) and the online service are provided as is, without warranty. The tool masks direct identifiers, not all of them, and does not read meaning (health, opinions, combined clues): its output may still identify someone. Treat it as personal data and check the results before relying on them. Running a document through the tool is itself processing of personal data: you remain responsible for it. Online, your documents go through our server, with no processing agreement: it is for you to decide whether you may send them; if not, use the [local version](docs/LOCAL.md). To the fullest extent permitted by law, and without prejudice to rights it does not allow to be excluded, Flow Line Intégration and the project's authors accept no liability for the use you make of the tool or of its results. Neither a certification nor legal advice.

---

Feuille de route et choix techniques : [docs/PLAN.md](docs/PLAN.md). Architecture (noyau Rust, contrat de
parité avec la référence Python, service à un processus par requête) : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Déploiement : [deploy/README.md](deploy/README.md). Sur le poste : [docs/LOCAL.md](docs/LOCAL.md). Publication
d'une version : [docs/PUBLISHING.md](docs/PUBLISHING.md). Protocole public d'auto-évaluation :
[docs/PROTOCOLE.md](docs/PROTOCOLE.md) ; corpus réels : [docs/CORPUS_REELS.md](docs/CORPUS_REELS.md).
