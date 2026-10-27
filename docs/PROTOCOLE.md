# Protocole public d'auto-évaluation de Gardien RGPD

## Version 1.2 (26 octobre 2026)

Écrite le **26 octobre 2026** au soir, après la campagne 1.1 et **avant la campagne 1.2**. Nous savions déjà, par une
mesure interne sur les moitiés dev, que le mode fort masque environ 15 % des leurres : c'est ce qui motive ce
changement. Elle sera mesurée sur le moteur **1.0.2**, après sa sortie. Le résultat 1.1 reste publié tel quel : documents normalisés **96,9 %
[96,2–97,6]**, documents difficiles **84,0 %**, leurres masqués 3,71 %, tous les garde-fous passés, moteur
`1.0.1+4bb5c465425e` ([`benchmarks/results/protocol-1.1-2026-10-26.md`](../benchmarks/results/protocol-1.1-2026-10-26.md)).
La section « Version 1.1 » et les sections 1 à 15 restent en vigueur, sauf là où cette section dit autre chose.
Définitions exécutables : [`tools/protocol/spec.py`](../tools/protocol/spec.py) (`PROTOCOL_VERSION = "1.2"`, `MODES`,
`DECOY_GUARD_MODES`, `MODE_SITE_PREFIX`).

### Pourquoi une version 1.2

Le moteur 1.0.2 a trois modes, avec les mêmes noms dans l'API, le serveur MCP et le site :

- **fort** (le mode par défaut) : on masque tout ce qu'on peut. Chaque identifiant, chaque code, les nombres longs,
  les boîtes partagées.
- **essentiel** : le filtre classique de premier niveau. On masque ce que prouve une clé de contrôle, un format connu
  ou un libellé personnel. Les codes de produit, de commande, de facture, de lot et les boîtes partagées restent
  lisibles.
- **personnalisé** : on part du mode fort et on peut couper des catégories. Les secrets ne se coupent jamais.

Dans tous les modes, les règles « codes à conserver » de l'organisation s'appliquent et l'emportent.

Le protocole 1.1 ne connaissait qu'un réglage. Son garde-fou des leurres (au plus 10 % de numéros qui ne désignent
personne masqués) a été écrit quand ces codes restaient lisibles. Le mode fort les masque tous, par choix. Mesuré avec
la règle 1.1, il afficherait un échec qui ne dit rien de sa qualité. Un garde-fou doit repérer une erreur, pas
sanctionner un choix affiché. Règle retenue : mode fort, masquer le moins de leurres possible et publier leur perte ;
mode essentiel, en garder le maximum (garde-fou des 10 %). La version 1.2 mesure donc chaque mode pour ce qu'il
promet, et montre ce qu'il coûte.

### Les changements

1. **Le plan déclare les modes notés : fort et essentiel.** Chaque document est envoyé et noté une fois par mode. Le
   service reçoit `mode`, et plus `profile` (depuis le moteur 1.0.2, `profile: standard` veut dire « essentiel »). Le
   mode personnalisé n'est pas noté : son résultat dépend des catégories choisies.
2. **Deux chiffres par mode.**
   - **Anonymisation** : l'indice « documents normalisés », avec son intervalle à 95 %, même définition qu'en 1.1.
     L'indice « documents difficiles » est donné en détail.
   - **Codes utiles perdus** : la part des leurres du corpus synthétique (numéros de commande, de facture, de
     produit, de ticket, de lot, qui ne désignent personne) masqués quand même. Plus ce chiffre est bas, mieux c'est.
     C'est la mesure du garde-fou des leurres de la 1.1, sur la famille synthétique (10 graines).
3. **Garde-fous.**
   - Lisibilité, pour les deux modes : texte neutre sur-masqué au plus 2 %, précision BODACC et BOAMP au moins 70 %.
     Ils repèrent une erreur ; ils ne sanctionnent pas un choix.
   - Leurres masqués au plus 10 % : **mode essentiel seulement**. En mode fort, la perte est publiée à côté de
     l'indice, sans garde-fou. La ligne « Tout masquer » de la section 8 a donc, pour le mode fort, cette réponse :
     les garde-fous de lisibilité, et la perte publiée sur la même carte que l'indice (le site refuse un indice de
     mode montré sans sa perte).
4. **Résultat et site.** Le mode par défaut (fort) donne les clés déjà lues par le site (`confidence_*`, `hard_*`).
   **Rupture de série déclarée** : le résultat 1.1 porte sur le réglage unique du moteur 1.0.1, ni fort ni essentiel.
   Le titre 1.2 est le mode fort, qui masque davantage. Les deux modes sont publiés côte à côte, et le 1.1 reste
   affiché.
   Chaque mode a ses clés : `fort_index`, `fort_ci_low`, `fort_ci_high`, `fort_hard_index`, `fort_code_loss`, et de
   même `ess_*`. La clé `modes_source` dit d'où viennent ces chiffres : « protocole 1.2 » ou « mesure interne, moitié
   dev ». Le résultat 1.2 garde, pour chaque mode, le détail par famille, par groupe et par opérateur.
5. **Moitiés `test` encore moins aveugles.** La campagne 1.1 s'ajoute à `spec.EARLIER_CAMPAIGNS` et à
   `spec.TEST_HALVES_MEASURED_BEFORE`. Les chiffres des corpus réels restent optimistes, et le résultat le dit.

### Ce qui ne change pas

La définition d'une fuite (une adresse électronique compte toujours, quel qu'en soit le titulaire), celle des deux
indices, les familles et leurs poids, le bootstrap, la partition `dev`/`test`, les graines, le plan et ses empreintes,
les seuils des garde-fous (le garde-fou des leurres ne s'applique plus qu'au mode essentiel, voir plus haut). Les mêmes documents sont envoyés une fois par mode : environ deux fois plus de requêtes,
soit environ 4 h 30 sur le serveur au lieu de 2 h 15.

**Conséquence déclarée.** En mode essentiel, une boîte partagée (contact@…, support@…) reste lisible par choix. Elle
compte pourtant comme une fuite, comme en 1.1. Le chiffre d'anonymisation du mode essentiel en est plus bas. Nous ne
changeons pas la définition pour l'éviter.

### D'ici la campagne 1.2 : des mesures internes, signalées comme telles

Jusqu'à la campagne 1.2, les chiffres par mode montrés sur le site sont des **mesures internes**, toujours signalées
ainsi (« mesure interne, moitié dev ») et jamais présentées comme le protocole. Elles viennent de `python -m
tools.protocol modes-dev` : moteur installé, en processus ; moitiés `dev` de BODACC, BOAMP et ParlaMint-FR ; graine de
développement 20261024 (20 000 documents synthétiques avec leurres, 600 documents de base passés par les 51
opérateurs). Aucune moitié `test` n'est lue. Ces données ont servi à régler le moteur : ces chiffres sont optimistes.

### Règles de la campagne 1.2

- Le moteur 1.0.2 est gelé et déployé. Le contrôle croisé (section 11) est refait sur lui.
- Puis `bundle`, `registration --bundle` : les champs « TO_FILL_AT_RELEASE » de
  [`PROTOCOL-REGISTRATION-1.2.json`](../PROTOCOL-REGISTRATION-1.2.json) sont remplis et publiés **avant** la campagne.
- Les résultats s'écrivent dans `benchmarks/results/protocol-1.2-<date>.{json,md}`. Le report vers le site refuse un
  résultat 1.2 sans les deux chiffres de chaque mode.
- Le résultat 1.1 reste publié, et rappelé à côté du résultat 1.2.

### English version

Written on the evening of **26 October 2026**, after the 1.1 campaign and **before the 1.2 campaign**. We already
knew, from an internal measure on the dev halves, that strong mode masks about 15% of the decoys: that is what
prompted this change. It will be measured on engine **1.0.2**, after its release. The 1.1 result stays published as it is: normalised documents
**96.9% [96.2–97.6]**, difficult documents **84.0%**, decoys masked 3.71%, every guard passed, engine
`1.0.1+4bb5c465425e` (`benchmarks/results/protocol-1.1-2026-10-26.md`). The "Version 1.1" section and sections 1 to 15
remain in force except where this section says otherwise. Executable definitions: `tools/protocol/spec.py`
(`PROTOCOL_VERSION = "1.2"`, `MODES`, `DECOY_GUARD_MODES`, `MODE_SITE_PREFIX`).

**Why.** Engine 1.0.2 has three modes, with the same names in the API, the MCP server and the site: **fort**
("strong", the default: mask everything we can, every identifier, every code, long numbers, shared mailboxes);
**essentiel** ("essential": the classic first-level filter, what a check digit, a known format or a personal label
proves; product, order, invoice and lot codes and shared mailboxes stay readable); **personnalisé** ("custom": starts
from strong, categories can be switched off, secrets never). In every mode the organisation's "codes to keep" rules
apply and win. Protocol 1.1 knew one setting only. Its decoy guard (at most 10% of numbers that designate nobody
masked) was written when those codes stayed readable. Strong mode masks them all, by choice: measured under the 1.1
rule, it would show a failure that says nothing about its quality. A guard should catch an error, not punish a stated
choice. Rule adopted: strong mode, mask as few decoys as possible and publish the loss; essential mode, keep as many
as possible (10% guard). Version 1.2 therefore measures each mode for what it promises, and shows what it costs.

**Changes.**

1. **The plan declares the scored modes: strong and essential.** Every document is sent and scored once per mode. The
   service gets `mode`, no longer `profile` (since engine 1.0.2, `profile: standard` means essential). Custom mode is
   not scored: its result depends on the categories chosen.
2. **Two numbers per mode.** **Anonymisation**: the normalised-documents index with its 95% interval, same definition
   as 1.1; the difficult-documents index as a detail. **Useful codes lost**: the share of the synthetic corpus's
   decoys (order, invoice, product, ticket, lot numbers that designate nobody) masked anyway; lower is better. It is
   the 1.1 decoy guard's measure, synthetic family (10 seeds).
3. **Guards.** Readability, for both modes: neutral text over-masked at most 2%, BODACC and BOAMP precision at least
   70%; they catch a bug, they do not punish a choice. Decoys masked at most 10%: **essential mode only**; in strong
   mode the loss is published next to the index, without a guard. For strong mode, the "Mask everything" row of
   section 8 is therefore answered by the readability guards and by the loss published on the same card as the index
   (the site refuses a mode index shown without its loss).
4. **Result and site.** The default mode (strong) gives the keys the site already reads (`confidence_*`, `hard_*`).
   **Declared series break**: the 1.1 result covers the single setting of engine 1.0.1, neither strong nor essential.
   The 1.2 headline is strong mode, which masks more. Both modes are published side by side, and 1.1 stays shown.
   Each mode has its own keys: `fort_index`, `fort_ci_low`, `fort_ci_high`, `fort_hard_index`, `fort_code_loss`, and
   likewise `ess_*`. `modes_source` says where they come from: "protocole 1.2" or "mesure interne, moitié dev"
   (internal measure, dev half). The 1.2 result keeps each mode's detail per family, group and operator.
5. **Test halves even less blind.** The 1.1 campaign is added to `spec.EARLIER_CAMPAIGNS` and
   `spec.TEST_HALVES_MEASURED_BEFORE`. Real-corpus figures stay optimistic, and the result says so.

**Unchanged**: the leak definition (an e-mail address always counts, whoever it belongs to), the two indexes, the
families and their weights, the bootstrap, the dev/test split, the seeds, the plan and its fingerprints, the guard
thresholds (the decoy guard now applies to essential mode only, see above). The same documents are sent once per mode: about twice as many requests, about 4 h 30 on the server
instead of 2 h 15. **Declared consequence**: in essential mode a shared mailbox (contact@…, support@…) stays readable
by choice, yet counts as a leak, as in 1.1; essential mode's anonymisation figure is lower for it. We do not change the
definition to avoid that.

**Until the 1.2 campaign: internal measures, labelled as such.** Per-mode figures shown on the site are **internal
measures**, always labelled so ("mesure interne, moitié dev") and never presented as the protocol. They come from
`python -m tools.protocol modes-dev`: installed engine, in process; dev halves of BODACC, BOAMP and ParlaMint-FR;
development seed 20261024 (20,000 synthetic documents with decoys, 600 base documents through the 51 operators). No
test half is read. These data were used to tune the engine: the figures are optimistic.

**1.2 campaign rules.** Engine 1.0.2 frozen and deployed; the cross-check (section 11) redone on it; then `bundle`,
`registration --bundle`: the "TO_FILL_AT_RELEASE" fields of `PROTOCOL-REGISTRATION-1.2.json` filled and published
**before** the campaign. Results go to `benchmarks/results/protocol-1.2-<date>.{json,md}`; the site merge refuses a
1.2 result without both numbers of each mode. The 1.1 result stays published and is recalled next to the 1.2 result.

## Version 1.1 (26 octobre 2026)

Écrite le **26 octobre 2026**, après la première campagne (protocole 1.0) et **avant toute campagne 1.1**. Le
résultat 1.0 reste publié tel quel : **61,8 % [58,6–66,9]**, sept familles, moteur `1.0.0+0c3ff9fc1fb0`
([`benchmarks/results/protocol-2026-10-26.md`](../benchmarks/results/protocol-2026-10-26.md)). Les sections 1 à 15
plus bas sont le texte de la version 1.0 ; elles restent en vigueur sauf là où cette section dit autre chose. La
version 1.1 publie **deux indices**, chacun avec son intervalle à 95 % : **« documents normalisés »**, l'indice
principal (cible : 95 % ou plus), et **« documents difficiles »** (le mieux possible). Ce choix des deux indices a été
fait le 26 octobre 2026 dans l'après-midi, avant tout enregistrement publié et toute campagne 1.1 ; il remplace un
premier jet à indice unique (cinq familles), jamais enregistré (tableau plus bas). Les définitions exécutables sont dans
[`tools/protocol/spec.py`](../tools/protocol/spec.py) (`PROTOCOL_VERSION = "1.1"`, `USE_CASE`, `REDTEAM_EVERYDAY`,
`REDTEAM_OBFUSCATION`, `REDTEAM_OCR`, `INDEXES`, `NORMALISED_TARGET`, `FAMILIES`, `HARD_FAMILIES`, `APART_FAMILIES`).
Les résultats 1.1 s'écrivent dans `benchmarks/results/protocol-1.1-<date>.{json,md}` (la version est dans le nom : une
campagne 1.1 lancée le 26 octobre ne peut pas écraser le fichier 1.0 du même jour, et `run-protocol.sh finish` refuse
d'écraser un résultat déjà présent).

### Pourquoi une version 1.1

La version 1.0 notait le produit contre tout ce qu'on peut lui envoyer : journaux du XIXe siècle passés à l'OCR,
identifiants déguisés exprès (alphabets mathématiques, caractères invisibles…), six textes juridiques européens. Le
responsable du produit, après la première campagne : « On doit s'évaluer pour un usage précis » ; « RGPD ce sont des
personnes, du coup les noms de sociétés, quel est le problème ? » ; « On masque toutes les adresses, tél. etc. et un
maximum de noms » ; « On doit imposer une certaine qualité ; on indiquera une performance dégradée sur les documents
OCR de mauvaise qualité ». La version 1.1 note donc le produit **pour l'usage qu'il vise**, et publie à part, avec
leurs chiffres, ce qui sort de cet usage. Puis, sur le premier jet de la 1.1, qui gardait dans l'indice l'équipe rouge
des formats du quotidien : « Les textes piégés ne sont pas représentatifs de l'usage cible : on va donner 2 notes, sur
documents normalisés, sur documents difficiles. On vise +95 % sur documents normalisés et le mieux possible sur les
autres. » D'où les deux indices :

- **Documents normalisés** (l'indice principal, clés `confidence_*` du site) : des documents tels qu'ils s'écrivent,
  sans dégât de copie ni déguisement : courriels, demandes et documents internes du corpus synthétique, et les corpus
  réels français annotés (avis BODACC et BOAMP, débats ParlaMint-FR ; point 3 plus bas). Moyenne à poids égal (1/4
  chacune) de quatre familles : synthétique FR, BODACC, BOAMP, ParlaMint-FR (moitié `test` des corpus réels).
  **Cible : 95 % ou plus.** La cible est un objectif déclaré, pas un garde-fou : le chiffre se publie quel qu'il soit,
  avec son intervalle.
- **Documents difficiles** (clés `hard_*` du site) : les documents de l'équipe rouge, **tous ses opérateurs (51)** en
  trois groupes, publiés un à un : formats du quotidien abîmés par une copie, un retour à la ligne ou une saisie
  (25 opérateurs) ; déguisements volontaires (25) ; bruit d'OCR (1). **Pondération** : chaque document muté compte
  une fois (tous les opérateurs mis en commun) ; un opérateur pèse donc le nombre de documents qu'il modifie, et un
  groupe sa part des documents (sur la moitié `dev` : 51,7 %, 46,1 % et 2,2 %). Intervalle : bootstrap stratifié par
  groupe (chaque groupe garde son nombre de documents), 2 000 tirages, graine 20261025. Pourquoi ce choix : c'est la
  mesure de la famille équipe rouge de la version 1.0 (mêmes 51 opérateurs, mêmes documents, même mise en commun),
  donc comparable d'une version à l'autre ; un poids égal par groupe donnerait à l'unique opérateur d'OCR le poids des
  25 opérateurs de chacun des deux autres groupes. Le détail par groupe et par opérateur est publié avec l'indice.

Les deux indices utilisent la même mesure (part des documents où rien de ce que le produit promet de masquer ne reste
lisible, section 5 et point 2 plus bas). Presse ancienne, MAPA FR, autres langues et témoin Judilibre restent publiés
à part, dans aucun des deux indices.

**Ce choix n'est pas aveugle.** Il est fait avant toute mesure 1.1, mais **après** la publication des chiffres 1.0
par famille sur ces mêmes moitiés `test` : on savait que la presse ancienne (16,5 %) et MAPA FR (16,7 %) étaient les
deux familles les plus basses. Sur les moitiés `dev`, même moteur (tableau plus bas), le premier jet faisait passer
l'indice de 59,7 % à 77,4 %, soit **+17,7 points : +19,1 pour la sortie de la presse ancienne et de MAPA FR, −1,3
pour l'équipe rouge restreinte aux formats du quotidien, −0,1 pour le gold BOAMP corrigé**. Les deux indices sont
décidés **après** ce premier jet, donc en sachant que l'équipe rouge du quotidien était la famille la plus basse qu'il
gardait (56,0 % sur la moitié `dev`, 57,2 % sur la moitié `test` 1.0), et pendant la mise au point du moteur 1.0.1,
dont des chiffres par famille étaient connus. La sortir de l'indice principal le fait passer, même moteur 1.0, de
77,4 % à **82,8 %** (**+5,4 points**, soit +23,1 depuis l'indice 1.0) ; elle n'est pas retirée pour autant : elle
compte, avec les déguisements et l'OCR, dans l'indice « documents difficiles », publié à côté (62,3 % sur la même
moitié `dev`). Tout le gain de l'indice principal vient donc de familles qui en sortent ; toutes restent publiées,
avec leurs chiffres.

**Sections 8 et 12 en 1.1.** Ce qu'elles disent des poids vaut pour l'indice 1.0 à sept familles ; pour l'indice
principal 1.1, cela change, et dans le sens qui l'embellit :

- les deux familles qui **favorisent** l'indice pèsent **la moitié** de l'indice principal au lieu de 2/7 : le
  synthétique (mêmes gabarits que ceux sur lesquels le moteur a été réglé) et ParlaMint-FR (gold partiel : un nom non
  annoté ne compte pas comme fuite, son chiffre est une borne haute) ; ParlaMint-FR seule pèse **un quart** au lieu
  d'un septième, sur 143 documents notés dans la moitié `test` 1.0 ;
- l'équipe rouge, qui pesait contre l'indice, en sort : « écarter les documents difficiles » (section 8), c'est ce que
  fait l'indice principal 1.1 ; ils ne sont pas retirés pour autant, ils forment l'indice « documents difficiles »,
  publié à côté avec son détail par groupe ;
- poids réel (section 12) : trois quarts de l'indice principal reposent sur les documents notés des moitiés `test` de
  BODACC, BOAMP et ParlaMint-FR, 2 886 dans la campagne 1.0 (1 335, 1 408 et 143), au lieu de cinq septièmes sur
  3 164 ;
- « le volume : poids égal par famille » (section 8) ne vaut que pour l'indice principal : l'indice difficile met
  tous ses documents en commun, un opérateur y pèse le nombre de documents qu'il modifie.

### Les changements

1. **Un usage précis.** Les textes que les organisations envoient à une IA : courriels (en-têtes, signatures, fils
   cités), demandes collées dans une conversation, documents internes (comptes rendus, courriers RH, contrats,
   factures, notes CRM, tickets), en français, en texte ou en fichiers bureautiques, **écrits de bonne foi** (un
   salarié ne cherche pas à tromper l'outil).
2. **Ce qu'est une fuite.** Un seul caractère lisible d'une **adresse postale**, d'un **numéro de téléphone**, d'une
   **adresse électronique** ou d'un **autre identifiant direct** (numéros nationaux, IBAN, cartes, plaques…), **quel
   qu'en soit le titulaire**, ou du **nom d'une personne physique**. Les **noms de sociétés ne comptent pas**, ni comme
   fuite ni comme sur-masquage du texte neutre (la précision au caractère publiée compte toujours un nom de société
   masqué comme un masquage inutile, comme en 1.0). Le moteur garde lisibles la plupart des raisons sociales, **pas
   toutes** : une société qui porte le nom d'une personne (« SARL DUPONT ») peut être masquée comme une personne
   (`SARL [PERSONNE_1]`), ce que l'arrêt cité plus bas admet, puisqu'un tel nom identifie une personne physique. Le
   RGPD protège les personnes
   physiques ; son considérant 14 dit qu'il « ne couvre pas
   le traitement des données à caractère personnel qui concernent les personnes morales, et en particulier des
   entreprises dotées de la personnalité juridique, y compris le nom, la forme juridique et les coordonnées de la
   personne morale », et la Cour de justice a jugé qu'une personne morale ne peut invoquer la protection des données
   que si son nom identifie une ou plusieurs personnes physiques (CJUE, 9 novembre 2010, *Volker und Markus Schecke
   et Eifert*, C-92/09 et C-93/09). Un **entrepreneur individuel est une personne** : son nom, son SIREN et son SIRET
   comptent. Les **coordonnées** d'une société comptent quand même (adresse, téléphone, courriel) : le moteur ne sait
   pas à qui elles sont, et la règle du produit est de toutes les masquer (plus strict que le considérant 14). **Une
   ville nommée seule, comme lieu** (« réunion à Lyon »), **n'est pas une adresse** ; un code postal suivi d'une ville,
   sans voie ni boîte postale, non plus (c'est un lieu). Une adresse, c'est une voie (numéro, type et nom de voie,
   complément, bâtiment) ou une boîte postale (BP, CS), avec le code postal et la ville qui la suivent ; un seul
   caractère lisible de l'ensemble est une fuite. Ces règles étaient déjà celles du gold 1.0 (section 4) ; la 1.1 les
   écrit et corrige les écarts trouvés (point 4).
3. **Deux indices au lieu d'un.** **Documents normalisés**, l'indice principal : **quatre familles à poids égal
   (1/4 chacune)** au lieu de sept : synthétique FR ; BODACC ; BOAMP ; ParlaMint-FR. **Documents difficiles** : l'équipe
   rouge FR entière, **51 opérateurs en trois groupes**, chaque document muté comptant une fois (pondération et
   intervalle : plus haut, « Pourquoi une version 1.1 »).
   - **Formats du quotidien abîmés** (25 opérateurs), ce que produisent Word, Outlook, un PDF copié, un tableur,
     Windows ou une saisie pressée : retour à la ligne (LF `line_break` ou CRLF `crlf`) **à l'intérieur de
     l'identifiant** (« 06 12 34⏎56 78 », « 12 rue⏎des Lilas » ; un document entier aux fins de ligne Windows n'est
     pas en cause, il est masqué comme le même document en LF) ; lettres espacées d'un PDF copié `letter_spacing`
     (« J e a n ») ; espaces de toutes sortes `nbsp`, `narrow_nbsp`, `thin_space`, `figure_space`,
     `ideographic_space`, tabulations `tab`, doubles espaces `double_space` ; séparateurs et regroupements de chiffres
     `dots`, `hyphens`, `slashes`, `compact`, `regroup`, `en_dash_groups`, `nb_hyphen` ; coupure de mots
     `pdf_hyphenation` et trait d'union conditionnel de Word `soft_hyphen` ; casse `upper`, `lower` et ordre « NOM
     Prénom » `surname_first` ; accents retirés `strip_accents` et forme de normalisation Unicode décomposée `nfd` ;
     Markdown `markdown_bold`.
   - **Déguisements volontaires** (25 opérateurs ; ils ne servent qu'à cacher un identifiant aux machines, hors usage
     de bonne foi) : alphabets et chiffres de substitution `math_bold`,
     `fullwidth`, `superscript`, `arabic_indic`, `devanagari` ; sosies d'autres écritures `cyrillic`, `greek` ;
     caractères invisibles insérés dans la valeur `zero_width_space`, `zero_width_joiner`, `word_joiner`, `bom`,
     `bidi_mark`, `bidi_isolate`, `tag_chars`, `variation_selector`, `grapheme_joiner`, `hangul_filler` ; courriels
     maquillés : entité HTML `at_entity`, encodage pour cent `at_percent`, arobase pleine chasse `at_fullwidth`,
     arobase et point écrits en toutes lettres `at_brackets`, `at_parens`, `arobase`, `dot_brackets`, `dot_point`.
   - **Bruit d'OCR : performance dégradée** (1 opérateur) : `ocr`, une confusion 0/O, 1/l, 5/S, 8/B.
   **Publiés à part, avec leurs chiffres, dans aucun des deux indices** :
   - **presse ancienne** (Europeana + HIPE), **OCR de mauvaise qualité : performance dégradée** ; hors de l'usage
     visé (des journaux anciens numérisés), elle n'entre pas non plus dans l'indice difficile, où compte pourtant le
     bruit d'OCR synthétique (`ocr`) : ses 272 documents notés (moitié `test` 1.0) y pèseraient environ 0,05 % des
     quelque 549 000 documents mis en commun ; l'y mettre ne déplacerait cet indice que de 0,02 point environ ;
   - **MAPA FR** : des textes juridiques européens (arrêts, actes), hors de l'usage visé ; s'y ajoutent 6 documents
     notés dans la moitié `test` (un document déplaçait l'indice 1.0 de 2,4 points). La version 1.0 avait gardé MAPA
     FR malgré ces 6 documents : la 1.1 **revient sur ce choix**, et le déclare. BODACC, BOAMP et ParlaMint-FR ne sont
     pas non plus des textes envoyés à une IA ; ils restent parce que ce sont les seuls corpus réels français annotés
     assez grands pour peser (156 à 1 500 documents notés par moitié) et que leurs identifiants (noms, adresses de
     siège et de contact, téléphones, courriels) sont ceux de l'usage visé ;
   - inchangés : autres langues (hors périmètre) et témoin négatif Judilibre.
   Cas limites tranchés (les trois groupes comptent dans le même indice : un classement ne change que le détail par
   groupe) : le trait d'union conditionnel (inséré par Word) et le trait d'union insécable sont du quotidien ; les
   espaces idéographique et tabulaire aussi (« espaces de toutes sortes »), bien que rares en français ; les lettres
   espacées aussi (`tools/eval/mutate.py` les décrit comme un artefact de PDF ; un premier jet de cette version les
   classait parmi les déguisements, corrigé avant tout enregistrement publié : 0,0 % sans fuite sur la moitié `test`
   1.0) ; « [at] », « (at) », « arobase », « [dot] », « (point) » sont des déguisements (leur seul but est de cacher
   une adresse aux robots), même s'ils se voient dans de vrais avis publics. Tous les opérateurs passent toujours par
   le service : **le plan de campagne, ses empreintes et sa durée ne changent pas**.
4. **Gold contrôlé contre ce périmètre.** Synthétique : libellés `DIRECT` inchangés (organisations et villes déjà
   quasi-identifiants, identifiants de sociétés déjà leurres, SIREN et SIRET d'entrepreneurs individuels seulement) ;
   le générateur couvre courriels avec signature et réponse (« Re: », « -- »), tickets avec message cité
   (« a écrit : », « > »), comptes rendus, fiches RH, contrats, factures, courriers, tableaux ; il n'a pas de gabarit
   « note CRM » ni « demande collée dans une conversation » : non ajoutés (changer le générateur change les empreintes
   enregistrées du plan), limite déclarée. BODACC : personnes physiques, toutes les adresses de voie (siège compris),
   numéro RCS d'un entrepreneur individuel ; conforme. ParlaMint-FR : orateurs et personnes de la liste du corpus,
   jamais d'organisation ; conforme (gold partiel, comme en 1.0). **BOAMP : deux écarts corrigés** dans
   [`tools/corpus/build_boamp.py`](../tools/corpus/build_boamp.py) : (a) une adresse de partie dont la boîte postale
   est collée à son numéro ou écrite avec des points (« BP60120 », « CS44416 », « C.S.80794 », aussi dans le champ
   d'identification) ou dont la voie est écrite dans les champs code postal et ville (« 97122 Rue … ») était un
   simple lieu : c'est une adresse ; (b) un service écrit dans le champ contact (« Groupe Maintenance … »,
   « DGEEP-Direction … ») était une personne : ce n'en est pas une. Effet sur les 3 000 avis : 42 adresses ajoutées
   (35 lieux requalifiés, et 7 nouvelles mentions), 5 « personnes » retirées, 40 documents touchés (22 `dev`, 18
   `test`) ; textes identiques, construction reproductible au bit près (reconstruction 1.0 identique au cache :
   SHA-256 `e87658ea3af8…`). Relecture de **toutes** les 82 zones changées : 0 erreur de libellé ; 5 des 42 adresses
   ajoutées couvrent aussi un nom de service écrit dans le champ adresse (le constructeur prend le champ entier, comme
   en 1.0) : bornes trop larges, donc plus sévères pour le moteur, gardées et déclarées. Les mesures d'erreur du gold
   de la section 2 (BOAMP 2,1 % [1,0–4,5] des mentions) restent valables pour le reste.
5. **Ce qui ne change pas** : définition de la lisibilité, de la fuite et des échecs (section 5), indice principal =
   moyenne à poids égal des familles, bootstrap stratifié (2 000 tirages, graine 20261025), garde-fous (section 7),
   partition `dev`/`test`, graines et plan de campagne (`spec.REGISTERED_PLAN`, 1 019 385 documents, environ 2 h 15
   sur le serveur), outil, conteneur, route, options du service. **Restent comparables** entre 1.0 et 1.1 : chaque
   famille et chaque corpus pris un à un (même mesure, même moitié `test`), sauf BOAMP (gold corrigé : 18 documents
   `test` sur 1 477) ; l'indice « documents difficiles » se compare à la famille équipe rouge de la 1.0 (mêmes 51
   opérateurs, mêmes documents, mise en commun identique) ; le détail par opérateur reste publié et comparable.
   Attention : la clé `redteam_fr` des résultats garde son nom mais couvre **25 opérateurs en 1.1 (formats du
   quotidien, dans l'indice difficile) et 51 en 1.0** ; comparer cette clé d'un résultat à l'autre compare deux
   populations (le titre de la famille donne le nombre d'opérateurs) ; le chiffre 1.0 se compare à `hard_index`.
   Dans le résultat 1.1, les trois groupes de l'équipe rouge sont rangés sous `families_apart` (que le site lit déjà)
   avec `"index": "hard"`, et l'indice difficile sous `hard_index` (valeur, intervalle, rappel des mentions, détail
   par groupe). **L'indice principal 1.1 n'est pas comparable à l'indice 1.0** : chaque résultat dit sa version.

### Effet du seul changement de définition (moitiés `dev`, même moteur)

Mesure en processus, le 26 octobre 2026, sur une **copie figée des sources du moteur prise avant toute modification
de ce jour** (`src/`, empreinte des fichiers Python `2705f5a61871e723`), en Python pur : moitiés `dev` des corpus
réels (celles qui ont servi à régler les règles) ; pour le synthétique et l'équipe rouge, la graine de développement
20261024 (20 000 documents, puis 27 441 documents mutés depuis 600 bases), jamais notée par une campagne. Aucune
moitié `test` n'a été mesurée. Les chiffres des deux indices 1.1 sont calculés depuis les mêmes décomptes par famille
(nombre de documents notés et sans fuite) : l'indice ne dépend que de l'issue de chaque document, donc ses intervalles
aussi. Décomptes et chiffres : [`index-definition-1.1-dev-halves-2026-10-26.json`](../benchmarks/results/index-definition-1.1-dev-halves-2026-10-26.json).

| Famille (part des documents sans fuite) | Définition 1.0 | 1.1, documents normalisés | 1.1, documents difficiles (poids) |
|---|---|---|---|
| Synthétique FR (20 000 documents) | 92,0 % | 92,0 % | — |
| BODACC, moitié `dev` (1 358 notés) | 89,0 % | 89,0 % | — |
| BOAMP, moitié `dev` (1 464 notés ; 1 465 avec le gold 1.1) | 60,9 % | 60,3 % | — |
| ParlaMint-FR, moitié `dev` (156 notés) | 89,7 % | 89,7 % | — |
| Équipe rouge FR, 51 opérateurs (27 441 mutés) | 62,3 % | — | 62,3 % (100 %) |
| · formats du quotidien abîmés, 25 opérateurs (14 197) | dans les 51 | — | 56,0 % (51,7 %) |
| · déguisements volontaires, 25 opérateurs (12 647) | dans les 51 | — | 72,0 % (46,1 %) |
| · bruit d'OCR, 1 opérateur (597) | dans les 51 | — | 7,9 % (2,2 %) |
| Presse ancienne, moitié `dev` (295 notés) | 23,7 % | à part | à part |
| MAPA FR, moitié `dev` (3 notés) | 0,0 % | à part | à part |
| **Indice** | **59,7 % [58,6–60,8]**, 7 familles | **82,8 % [81,3–84,1]**, 4 familles | **62,3 % [61,8–62,9]**, 27 441 documents |

L'intervalle 1.0 est étroit ici parce que les 3 documents MAPA FR de la moitié `dev` fuient tous (aucune variance) ;
sur la moitié `test`, il allait de 58,6 à 66,9. **Indice principal** : de 59,7 % (1.0) à 82,8 % (1.1), **+23,1
points**, tous venus de familles sorties de l'indice principal : sortie de la presse ancienne et de MAPA FR +19,1,
équipe rouge restreinte aux formats du quotidien −1,3 et gold BOAMP 1.1 −0,1 (le premier jet), puis sortie de l'équipe rouge vers l'indice difficile +5,4 (le premier
jet, cinq familles avec l'équipe rouge du quotidien, donnait 77,4 % [76,1–78,5] ; un jet antérieur à 24 opérateurs du
quotidien, 77,9 % [76,8–79,0]). Avec le gold BOAMP 1.0, l'indice principal serait de 82,9 %. **Indice difficile** :
62,3 %, exactement la famille équipe rouge de la 1.0 (mêmes opérateurs, mêmes documents, même mise en commun).

Les chiffres BODACC, BOAMP et ParlaMint-FR de la moitié `dev` sont ceux de la campagne du 26 octobre (89,0 %, 60,9 %,
89,7 %) : la copie figée se comporte comme le moteur de la campagne. Pour mémoire, recombiner les chiffres **déjà
publiés** de la moitié `test` de la campagne 1.0 (aucune nouvelle mesure) selon les deux indices 1.1 donne : documents
normalisés (91,9 + 89,9 + 60,7 + 93,0) / 4 ≈ **83,9 %** (BOAMP encore noté sur le gold 1.0) ; documents difficiles
**63,7 %** sur 548 907 documents mutés, dont formats du quotidien 57,2 % (284 081), déguisements 73,6 % (252 895),
OCR 8,6 % (11 931). Le seul changement de définition ne mène donc pas à la cible de 95 % : avec le moteur 1.0, il
manque 11 à 12 points à l'indice principal, et les fuites qui restent sont dans l'usage visé (adresses et téléphones
BOAMP, 60 % de documents sans fuite ; RIB présenté champ par champ dans le synthétique : 28 756 mentions, rappel
0 %). Dans l'équipe rouge, un retour à la ligne **à l'intérieur** d'un identifiant, les lettres espacées d'un PDF, les
barres obliques, doubles espaces et tabulations entre chiffres font l'essentiel des fuites des formats du quotidien.

### Règles de la prochaine campagne

- Les moitiés `test` ne sont plus aveugles : la campagne 1.0 du 26 octobre est listée dans `spec.EARLIER_CAMPAIGNS`
  (le report vers le site refuse une campagne répétée qui l'omet) et dans `spec.TEST_HALVES_MEASURED_BEFORE`, avec
  l'évaluation « rules3 » du 26 octobre ([`CORPUS_REELS.md`](CORPUS_REELS.md), section 13). Toute autre mesure d'une
  moitié `test` faite avant la campagne 1.1 (mise au point du moteur 1.0.1 comprise) s'ajoute à
  `spec.TEST_HALVES_MEASURED_BEFORE` et au tableau de la section 3, puis on enregistre à nouveau (section 15).
- **Moitiés `test` non aveugles : une dérogation déclarée à la section 3.** La section 3 dit que, pour une version
  ultérieure du moteur, l'indice principal devra passer sur des données neuves. La version 1.1 n'en a pas encore : le
  moteur 1.0.1 est noté sur les **mêmes** moitiés `test`, mesurées au moins neuf fois avant (tableau de la section 3)
  et dont les scores par famille, publiés, étaient connus pendant sa mise au point. **Les chiffres des corpus réels
  de la campagne 1.1 sont donc optimistes**, et le résultat le dit à côté de l'indice. Des données neuves (parutions
  BODACC et BOAMP postérieures au gel du moteur, construites avec les mêmes outils) restent l'engagement pour la
  version suivante.
- Le gold BOAMP 1.1 est celui de `build_boamp.py` à cette date ; le paquet des corpus réels de la campagne se
  construit avec lui (`pack-real` sur le cache reconstruit). Son empreinte est enregistrée : SHA-256 de
  `boamp_fr.jsonl` 1.1 = `435373ea39a1814a19b5cf4aa97801d955faefeb1753c09182bec56a35cac6f8` (celles des autres
  fichiers du cache, inchangés, aussi : `PROTOCOL-REGISTRATION-1.1.json`, `real_corpora_sha256`).
- L'enregistrement 1.1 se publie (dépôt public) **avec ses champs moteur remplis, avant le lancement** ; sans cela,
  « publié avant le lancement » ne tient pas.
- Le moteur est gelé et déployé avant l'enregistrement ; le contrôle croisé (section 11) est refait sur lui ; puis
  `bundle`, `registration --bundle` (empreintes publiées dans `PROTOCOL-REGISTRATION-1.1.json` à la racine du dépôt,
  avec la liste des changements), essai chronométré sur la moitié `dev`, campagne complète, `finish`, report vers le
  site. Clés du site : `protocol_families` : 4 ; indice difficile : `hard_index`, `hard_ci_low`, `hard_ci_high`,
  `hard_docs` (documents mutés notés), `hard_mention_recall_pct` ; détail par groupe : `f_red_*` (formats du
  quotidien), `f_obf_*`, `f_ocr_*`.
- Le résultat 1.1 se publie avec ses deux indices côte à côte, l'indice difficile et son détail par groupe aussi
  visibles que l'indice principal, les familles publiées à part et le rappel du résultat 1.0. Le report vers le site
  (`merge_quality.py`) refuse un résultat 1.1 sans indice difficile, et **refuse** tant que le site
  (`site/templates/index.*.html`) ou le `README.md` montrent encore le texte de la version 1.0 (« 7 familles »,
  « 51 déguisements »…) ou du premier jet 1.1 (« cinq familles », « 1/5 chacune », « restreinte aux 25 »…) hors d'une
  ligne qui nomme la version 1.0 (« Protocole 1.0 : 61,8 % [58,6–66,9], 7 familles ») ; `--site-text-checked` après
  relecture. « 51 façons » ou « 51 opérateurs » sont permis : l'indice difficile couvre les 51 opérateurs.
- Limite de l'intervalle de l'indice difficile : le bootstrap tire les documents mutés un à un, alors que chaque
  document de base donne jusqu'à 51 documents mutés, dont les issues se ressemblent ; l'intervalle est donc trop
  étroit (il ne couvre pas la variabilité des documents de base, 12 000 dans la campagne). Limite déclarée, non
  corrigée en 1.1 (les issues par document de base ne sont pas gardées).

### English version

Written on **26 October 2026**, after the first campaign (protocol 1.0) and **before any 1.1 campaign**. The 1.0
result stays published as it is: **61.8% [58.6–66.9]**, seven families, engine `1.0.0+0c3ff9fc1fb0`
(`benchmarks/results/protocol-2026-10-26.md`). Sections 1 to 15 below are the text of version 1.0; they remain in
force except where this section says otherwise. Version 1.1 publishes **two indexes**, each with its 95% interval:
**"normalised documents"**, the headline (target: 95% or more), and **"difficult documents"** (as good as possible).
The two indexes were decided on 26 October 2026 in the afternoon, before any published registration and any 1.1
campaign; they replace a single-index first draft (five families), never registered (table below). Executable
definitions: `tools/protocol/spec.py` (`PROTOCOL_VERSION = "1.1"`, `USE_CASE`, `REDTEAM_EVERYDAY`,
`REDTEAM_OBFUSCATION`, `REDTEAM_OCR`, `INDEXES`, `NORMALISED_TARGET`, `FAMILIES`, `HARD_FAMILIES`, `APART_FAMILIES`).
The 1.1 results are
written to `benchmarks/results/protocol-1.1-<date>.{json,md}`: the version is in the name, so a 1.1 campaign run on
26 October cannot overwrite the 1.0 file of the same day, and `run-protocol.sh finish` refuses to overwrite any result
already there.

**Why.** Version 1.0 rated the product against anything one could send it: 19th-century newspapers through OCR,
identifiers disguised on purpose (mathematical alphabets, invisible characters…), six EU legal texts. The product
owner, after the first campaign: "We must rate ourselves for a precise use"; "GDPR is about people, so company names,
what is the problem?"; "We mask every address, phone, etc. and as many names as possible"; "We must require a certain
quality; we will state degraded performance on poor-quality OCR documents". Version 1.1 rates the product **for the
use it is made for** and publishes apart, with their figures, what falls outside it. Then, on the 1.1 first draft,
which kept the everyday-format red team in the index: "The trapped texts are not representative of the target use: we
will give 2 scores, on normalised documents, on difficult documents. We aim for 95%+ on normalised documents and the
best possible on the others." Hence the two indexes:

- **Normalised documents** (the headline, site keys `confidence_*`): documents as they are written, with no copy
  damage nor disguise: the synthetic corpus's e-mails, requests and internal documents, and the annotated French real
  corpora (BODACC and BOAMP notices, ParlaMint-FR debates; item 3 below). Equal-weight mean (1/4 each) of four
  families: synthetic FR, BODACC, BOAMP, ParlaMint-FR (test half of the real corpora). **Target: 95% or more.** The
  target is a declared goal, not a guard: the figure is published whatever it is, with its interval.
- **Difficult documents** (site keys `hard_*`): the red-team documents, **all its operators (51)** in three groups,
  each published: everyday formats damaged by a copy, a line break or typing (25 operators); deliberate obfuscations
  (25); OCR noise (1). **Weighting**: every mutated document counts once (all operators pooled); an operator therefore
  weighs the number of documents it alters, and a group its share of the documents (on the dev half: 51.7%, 46.1% and
  2.2%). Interval: bootstrap stratified by group (each group keeps its document count), 2,000 resamples, seed
  20261025. Why: it is the 1.0 red-team family's measure (same 51 operators, same documents, same pooling), so it
  stays comparable across versions; equal weight per group would give the single OCR operator the weight of the 25
  operators of either other group. The per-group and per-operator detail is published with the index.

Both indexes use the same measure (share of documents in which nothing the product promises to mask stays readable,
section 5 and item 2 below). Old press, MAPA FR, other languages and the Judilibre control stay published apart, in
neither index.

**This choice is not blind.** It is made before any 1.1 measurement, but **after** the 1.0 per-family figures on the
same test halves were published: old press (16.5%) and MAPA FR (16.7%) were known to be the two lowest families. On
the dev halves, same engine (below), the first draft moved the index from 59.7% to 77.4%, i.e. **+17.7 points: +19.1
from moving old press and MAPA FR out, −1.3 from restricting the red team to everyday formats, −0.1 from the corrected
BOAMP gold**. The two indexes were decided **after** that first draft, hence knowing that the everyday red team was the
lowest family it kept (56.0% on the dev half, 57.2% on the 1.0 test half), and while engine 1.0.1 was being tuned,
with some of its per-family figures known. Moving it out of the headline raises it, same 1.0 engine, from 77.4% to
**82.8%** (**+5.4 points**, +23.1 from the 1.0 index); it is not dropped: with the obfuscations and OCR it counts in
the "difficult documents" index, published next to it (62.3% on the same dev half). All of the headline's gain thus
comes from families moved out of it; all stay published, with their figures.

**Sections 8 and 12 under 1.1.** What they say about weights holds for the seven-family 1.0 index; for the 1.1
headline it changes, and in the direction that flatters it:

- the two families that **favour** the index weigh **half** of the headline instead of 2/7: synthetic (the same
  templates the engine was tuned on) and ParlaMint-FR (partial gold: an unannotated name does not count as a leak, its
  figure is an upper bound); ParlaMint-FR alone weighs **a quarter** instead of a seventh, on 143 scored documents in
  the 1.0 test half;
- the red team, which weighed against the index, leaves it: "dropping hard documents" (section 8) is what the 1.1
  headline does; they are not removed, they make the "difficult documents" index, published next to it with its
  per-group detail;
- real weight (section 12): three quarters of the headline rest on the scored test-half documents of BODACC, BOAMP and
  ParlaMint-FR, 2,886 in the 1.0 campaign (1,335, 1,408 and 143), instead of five sevenths on 3,164;
- "Volume: equal weights" (section 8) holds for the headline only: the difficult index pools all its documents, an
  operator weighs there the number of documents it alters.

**Changes.** (1) **One use case**: texts organisations send to an AI — e-mails (headers, signatures, quoted threads),
requests pasted into a chat, internal documents (minutes, HR letters, contracts, invoices, CRM notes, tickets) — in
French, as text or office files, written in good faith (an employee is not trying to fool the tool).

(2) **Scope of a leak**: one readable character of a postal address, phone number, e-mail address or other direct
identifier (national numbers, IBAN, cards, plates…), **whoever it belongs to**, or of a natural person's name.
**Company names do not count**, neither as a leak nor as over-masking of neutral text (the published character
precision still counts a masked company name as an unneeded mask, as in 1.0). The engine keeps most company names
readable, **not all**: a company named after a person ("SARL DUPONT") may be masked as a person (`SARL [PERSONNE_1]`),
which the judgment cited below allows, since such a name identifies a natural person. GDPR recital 14 ("This
Regulation does not cover the processing of personal data which concerns legal persons and in particular undertakings
established as legal persons, including the name and the form of the legal person and the contact details of the
legal person"); CJEU, 9 November 2010, *Volker und Markus Schecke and Eifert*, C-92/09 and C-93/09 (a legal person
may claim data protection only in so far as its name identifies one or more natural persons). **Sole traders are
persons**: their name, SIREN and SIRET count. A company's contact details still count (the engine cannot know their
owner, and the product rule is to mask them all; stricter than recital 14). **A town named alone as a place is not an
address** ("meeting in Lyon"), nor is a postcode followed by a town without a street or postal box (a place); an
address is a street (number, street type and name, complement, building) or a postal box (BP, CS) with the postcode
and town that follow; one readable character of it is a leak. These were already the 1.0 gold's rules (section 4);
1.1 writes them down and fixes the departures found (item 4).

(3) **Two indexes instead of one.** **Normalised documents**, the headline: **four families, equal weight (1/4
each)** instead of seven: synthetic FR; BODACC; BOAMP; ParlaMint-FR. **Difficult documents**: the whole French red
team, **51 operators in three groups**, every mutated document counting once (weighting and interval: above, "Why").
- **Damaged everyday formats** (25 operators), what Word, Outlook, a copied PDF, a spreadsheet, Windows or hurried
  typing produce: a line break (LF `line_break` or CRLF `crlf`) **inside the identifier** ("06 12 34⏎56 78", "12
  rue⏎des Lilas"; a whole document with Windows line endings is not at issue, it is masked like the same document in
  LF); copied-PDF letter spacing `letter_spacing` ("J e a n"); spaces of all kinds `nbsp`, `narrow_nbsp`,
  `thin_space`, `figure_space`, `ideographic_space`, tabs `tab`, double spaces `double_space`; digit separators and
  grouping `dots`, `hyphens`, `slashes`, `compact`, `regroup`, `en_dash_groups`, `nb_hyphen`; hyphenation
  `pdf_hyphenation` and Word's optional hyphen `soft_hyphen`; case `upper`, `lower` and surname-first order
  `surname_first`; stripped accents `strip_accents` and decomposed Unicode `nfd`; Markdown `markdown_bold`.
- **Deliberate obfuscations** (25 operators; their only use is to hide an identifier from machines, outside
  good-faith use): substitute alphabets and digits `math_bold`, `fullwidth`, `superscript`, `arabic_indic`,
  `devanagari`; homoglyph scripts `cyrillic`, `greek`; invisible characters inserted in the value `zero_width_space`,
  `zero_width_joiner`, `word_joiner`, `bom`, `bidi_mark`, `bidi_isolate`, `tag_chars`, `variation_selector`,
  `grapheme_joiner`, `hangul_filler`; disguised e-mails: HTML entity `at_entity`, percent-encoding `at_percent`,
  full-width at sign `at_fullwidth`, "at" and "dot" spelled out `at_brackets`, `at_parens`, `arobase`, `dot_brackets`,
  `dot_point`.
- **OCR noise: degraded performance** (1 operator): `ocr`, one 0/O, 1/l, 5/S, 8/B confusion.

**Published apart with their figures, in neither index**:
- **old press** (Europeana + HIPE), **low-quality OCR: degraded performance**; outside the target use (digitised old
  newspapers), it is not in the difficult index either, where the synthetic OCR noise (`ocr`) does count: its 272
  scored documents (1.0 test half) would weigh about 0.05% of the some 549,000 pooled documents; putting it in would
  move that index by about 0.02 points only;
- **MAPA FR**: EU legal texts (judgments, acts), outside the target use; on top of that, 6 scored test documents (one
  document moved the 1.0 index by 2.4 points). Version 1.0 kept MAPA FR despite those 6 documents: 1.1 **reverses that
  choice** and says so. BODACC, BOAMP and ParlaMint-FR are not texts sent to an AI either; they stay because they are
  the only annotated French real corpora large enough to weigh (156 to 1,500 scored documents per half) and their
  identifiers (names, head-office and contact addresses, phones, e-mails) are those of the target use;
- unchanged: other languages (out of scope) and the Judilibre negative control.

Edge cases decided (the three groups count in the same index: a classification only changes the per-group detail):
Word's optional hyphen and the non-breaking hyphen are everyday; so are the ideographic and figure spaces ("spaces of
all kinds"), though rare in French; so is letter spacing (`tools/eval/mutate.py` describes it as a PDF artefact; a
first draft of this version listed it among the obfuscations, corrected before any published registration: 0.0% with
no leak on the 1.0 test half); "[at]", "(at)", "arobase", "[dot]", "(point)" are obfuscations (their only purpose is to hide an address from robots),
even though they appear in real public notices. Every operator still goes through the service: **the campaign plan,
its fingerprints and its duration do not change**.

(4) **Gold checked against this scope.** Synthetic: `DIRECT` labels unchanged (organisations and towns already
quasi-identifiers, company identifiers already decoys, SIREN and SIRET of sole traders only); the generator covers
e-mails with signature and reply ("Re:", "--"), tickets with a quoted message ("a écrit :", ">"), minutes, HR
records, contracts, invoices, letters, tables; it has no "CRM note" or "chat request" template: not added (changing
the generator changes the registered plan fingerprints), a declared limit. BODACC: natural persons, every street
address (head office included), a sole trader's RCS number; conforms. ParlaMint-FR: speakers and persons from the
corpus list, never an organisation; conforms (partial gold, as in 1.0). **BOAMP: two departures fixed** in
`tools/corpus/build_boamp.py`: (a) a party address whose postal box is glued to its number or written with dots
("BP60120", "CS44416", "C.S.80794", also in the identification field) or whose street sits in the postcode and town
fields ("97122 Rue …") was a mere place: it is an address; (b) a service written in the contact field ("Groupe
Maintenance …", "DGEEP-Direction …") was a person: it is not. On the 3,000 notices: 42 addresses added (35 places
relabelled, 7 new mentions), 5 "persons" removed, 40 documents touched (22 dev, 18 test); texts identical;
byte-reproducible build (the 1.0 rebuild is identical to the cache: SHA-256 `e87658ea3af8…`; the 1.1 file:
`435373ea39a1814a19b5cf4aa97801d955faefeb1753c09182bec56a35cac6f8`, registered). All 82 changed spans reviewed: 0
label error; 5 of the 42 new addresses also cover a service name written in the address field (the builder takes the
whole field, as in 1.0): too wide, hence harsher on the engine, kept and disclosed. The section 2 gold-error figures
(BOAMP 2.1% [1.0–4.5] of mentions) still hold for the rest.

(5) **Unchanged**: readability, leak and failure definitions (section 5), equal-weight mean for the headline,
stratified bootstrap (2,000 resamples, seed 20261025), guards (section 7), dev/test split, seeds and campaign plan
(`spec.REGISTERED_PLAN`, 1,019,385 documents, about 2 h 15 on the server), tool, container, route, service options.
Each family and each corpus remains comparable with 1.0 on its own (same measure, same test half), except BOAMP
(corrected gold: 18 of 1,477 test documents); the "difficult documents" index compares with the 1.0 red-team family
(same 51 operators, same documents, same pooling); the per-operator detail stays published and comparable. Note: the
results key `redteam_fr` keeps its name but covers **25 operators in 1.1 (everyday formats, in the difficult index)
and 51 in 1.0**; comparing that key across results compares two populations (the family title gives the operator
count); the 1.0 figure compares with `hard_index`. In the 1.1 result the three red-team groups sit under
`families_apart` (which the site already reads) with `"index": "hard"`, and the difficult index under `hard_index`
(value, interval, mention recall, per-group detail). **The 1.1 headline index is not comparable with the 1.0 index**;
every result names its version.

**Effect of the definition change alone (dev halves, same engine).** In-process measurement on 26 October 2026 on a
**frozen copy of the engine sources taken before any change of that day** (`src/`, Python-file fingerprint
`2705f5a61871e723`), pure Python: dev halves of the real corpora (those used to tune the rules); development seed
20261024 for synthetic and red team (20,000 documents, then 27,441 mutated from 600 bases), never scored by a
campaign. No test half measured. The two 1.1 indexes are computed from the same per-family counts (documents scored
and with no leak): the index only depends on each document's outcome, and so do its intervals. Counts and figures:
`benchmarks/results/index-definition-1.1-dev-halves-2026-10-26.json`.

| Family (share of documents with no leak) | 1.0 definition | 1.1, normalised documents | 1.1, difficult documents (weight) |
|---|---|---|---|
| Synthetic FR (20,000 documents) | 92.0% | 92.0% | — |
| BODACC, dev half (1,358 scored) | 89.0% | 89.0% | — |
| BOAMP, dev half (1,464 scored; 1,465 with the 1.1 gold) | 60.9% | 60.3% | — |
| ParlaMint-FR, dev half (156 scored) | 89.7% | 89.7% | — |
| Red team FR, 51 operators (27,441 mutated) | 62.3% | — | 62.3% (100%) |
| · damaged everyday formats, 25 operators (14,197) | within the 51 | — | 56.0% (51.7%) |
| · deliberate obfuscations, 25 operators (12,647) | within the 51 | — | 72.0% (46.1%) |
| · OCR noise, 1 operator (597) | within the 51 | — | 7.9% (2.2%) |
| Old press, dev half (295 scored) | 23.7% | apart | apart |
| MAPA FR, dev half (3 scored) | 0.0% | apart | apart |
| **Index** | **59.7% [58.6–60.8]**, 7 families | **82.8% [81.3–84.1]**, 4 families | **62.3% [61.8–62.9]**, 27,441 documents |

The 1.0 interval is narrow here because the 3 MAPA FR dev documents all leak (no variance); on the test half it ran
from 58.6 to 66.9. **Headline**: from 59.7% (1.0) to 82.8% (1.1), **+23.1 points**, all from families moved out of the
headline: old press and MAPA FR out +19.1, red team restricted to everyday formats −1.3 and 1.1 BOAMP gold −0.1 (the
first draft), then the red team moved to the difficult index +5.4 (the first draft, five families with the everyday red team, gave 77.4%
[76.1–78.5]; an earlier draft with 24 everyday operators, 77.9% [76.8–79.0]). With the 1.0 BOAMP gold the headline
would be 82.9%. **Difficult index**: 62.3%, exactly the 1.0 red-team family (same operators, same documents, same
pooling).

The BODACC, BOAMP and ParlaMint-FR dev-half figures are those of the 26 October campaign (89.0%, 60.9%, 89.7%): the
frozen copy behaves like the campaign engine. For the record, recombining the **already published** test-half figures
of the 1.0 campaign (no new measurement) along the two 1.1 indexes gives: normalised documents (91.9 + 89.9 + 60.7 +
93.0) / 4 ≈ **83.9%** (BOAMP still on the 1.0 gold); difficult documents **63.7%** over 548,907 mutated documents, of
which everyday formats 57.2% (284,081), obfuscations 73.6% (252,895), OCR 8.6% (11,931). The definition change alone
therefore does not reach the 95% target: with the 1.0 engine the headline is 11 to 12 points short, and the remaining
leaks are inside the target use (BOAMP addresses and phones, 60% of documents with no leak; field-by-field bank details
in the synthetic corpus: 28,756 mentions, 0% recall). In the red team, a line break **inside** an identifier, PDF
letter spacing, slashes, double spaces and tabs between digits make most of the everyday-format leaks.

**Next campaign.**
- The test halves are no longer blind: the 26 October 1.0 campaign is listed in `spec.EARLIER_CAMPAIGNS` (the site
  merge refuses a repeat campaign that omits it) and in `spec.TEST_HALVES_MEASURED_BEFORE`, with the 26 October
  "rules3" evaluation (`CORPUS_REELS.md`, section 13). Any other test-half measurement before the 1.1 campaign
  (engine 1.0.1 tuning included) is added to `spec.TEST_HALVES_MEASURED_BEFORE` and to the section 3 table, then the
  protocol is registered again (section 15).
- **Test halves not blind: a declared departure from section 3.** Section 3 says that for a later engine version the
  headline index must run on fresh data. Version 1.1 has none yet: engine 1.0.1 is rated on the **same** test halves,
  measured at least nine times before (section 3 table), whose published per-family scores were known while it was
  tuned. **The real-corpus figures of the 1.1 campaign are therefore optimistic**, and the result says so next to the
  index. Fresh data (BODACC and BOAMP notices published after the engine freeze, built with the same tools) remains
  the commitment for the next version.
- The 1.1 BOAMP gold is `build_boamp.py`'s at this date; the campaign's real-corpus pack is built from it
  (`pack-real` on the rebuilt cache). Its digest is registered (SHA-256 of the 1.1 `boamp_fr.jsonl` above; the other,
  unchanged cache files too: `PROTOCOL-REGISTRATION-1.1.json`, `real_corpora_sha256`).
- The 1.1 registration is published (public repository) **with its engine fields filled, before the launch**;
  otherwise "published before the launch" does not hold.
- Engine frozen and deployed before the registration; cross-check (section 11) redone on it; then `bundle`,
  `registration --bundle` (digests in `PROTOCOL-REGISTRATION-1.1.json` at the repository root, with the list of
  changes), timed dev-half trial, full campaign, `finish`, merge into the site. Site keys: `protocol_families`: 4;
  difficult index: `hard_index`, `hard_ci_low`, `hard_ci_high`, `hard_docs` (scored mutated documents),
  `hard_mention_recall_pct`; per-group detail: `f_red_*` (everyday formats), `f_obf_*`, `f_ocr_*`.
- The 1.1 result is published with its two indexes side by side, the difficult index and its per-group detail as
  visible as the headline, the apart families and the 1.0 result next to them. The site merge (`merge_quality.py`)
  refuses a 1.1 result without the difficult index, and **refuses** while the site (`site/templates/index.*.html`) or
  `README.md` still show 1.0 text ("7 families", "51 disguises"…) or 1.1 first-draft text ("five families", "1/5
  each", "restricted to 25 everyday"…) outside a line that names version 1.0 ("Protocol 1.0: 61.8% [58.6–66.9], 7
  families"); `--site-text-checked` after review. "51 ways" or "51 operators" are allowed: the difficult index covers
  the 51 operators.
- Limit of the difficult index's interval: the bootstrap draws mutated documents one by one, whereas each base
  document yields up to 51 mutated documents with similar outcomes; the interval is therefore too narrow (it does not
  cover the variability of the base documents, 12,000 in the campaign). A declared limit, not fixed in 1.1 (outcomes
  per base document are not kept).

---

*Texte de la version 1.0 (25 octobre 2026), en vigueur sauf où la section « Version 1.1 » dit autre chose. Text of
version 1.0, in force except where the "Version 1.1" section says otherwise.*

> **English summary (version 1.0).** GDPR Guardian rates itself under this public protocol, version 1.0, **written on
> 25 October 2026, before any campaign, and registered by publishing its digests before the launch** (section 15).
> The **confidence index** is the share of documents in which **no direct identifier stays readable** (strict: not
> one alphanumeric character of a gold direct-identifier mention left in the output), computed per corpus family,
> then averaged with **equal weight** over the seven families of the French scope (synthetic FR, red-team mutations
> FR, BODACC, BOAMP, ParlaMint-FR, old French press, MAPA FR), with a 95% interval from a stratified bootstrap over
> documents (2,000 resamples, seed 20261025). Real corpora count on their **test half**, never used to design rules
> (earlier measurements of these halves are all listed in section 3). Every document goes through the **real
> production service** (Unix socket, local token, counted as "protocol" in the public statistics): 1,019,385
> documents, of which 1,010,907 synthetic and 8,478 real; yet **five sevenths of the weight rest on the 3,164 scored
> real test-half documents, 6 of them MAPA FR**. One campaign = one engine: the service image and the service's
> outputs on a fixed probe are checked from start to end. Failures count as leaks; volume never buys weight; the
> index is published only next to precision and over-masking, and only if pre-registered guards hold. Scores only
> are published, never text. The full English version is section 14.

Version **1.0**, écrite le **25 octobre 2026**, avant toute campagne. Elle est **enregistrée** par la publication,
avant le lancement, des empreintes de ce texte, de [`tools/protocol/spec.py`](../tools/protocol/spec.py) et du paquet
de l'outil (section 15) ; chaque résultat recopie les empreintes de ce qui l'a produit. Les définitions exécutables
sont dans `spec.py`, source unique de vérité de ce document ; l'outil est [`tools/protocol/`](../tools/protocol/), ses
tests [`tests/protocol/`](../tests/protocol/). Toute modification d'une définition fait une **nouvelle version
datée** ; l'ancienne reste dans l'historique du dépôt et chaque résultat publié cite la version qui l'a produit. Texte
complété le 26 octobre 2026, avant l'enregistrement et avant toute campagne : mesures antérieures des moitiés `test`
(section 3), campagnes répétées, écarts déclarés, refus au départ (section 9) ; aucune définition de l'indice n'a
changé.

## 1. Ce que l'on mesure

Une seule question : **dans quelle part des documents le service laisse-t-il lisible au moins un identifiant
direct ?** Gardien RGPD est une première barrière, pas une promesse de « zéro fuite » ; l'indice dit combien de fois
la barrière a tenu, document par document, sur des documents dont on connaît la vérité (le « gold »).

- **Indice de confiance** : part des documents sans aucune fuite, calculée famille par famille, puis moyenne à
  **poids égal** des sept familles du périmètre français ; intervalle de confiance à 95 %.
- **Rappel des mentions directes** : part des mentions d'identifiants directs entièrement masquées, mêmes familles,
  même poids égal.
- Tous les autres chiffres (section 6) sont publiés à côté, jamais à la place.

## 2. Familles et corpus

### Périmètre français : les sept familles de l'indice

| # | Famille | Source | Documents (tous / moitié test, dont avec mention directe) | Gold | Erreur du gold mesurée | Licence |
|---|---|---|---|---|---|---|
| 1 | Synthétique FR | générateur `tools/eval/generate.py` (Faker 40.43.0 `fr_FR`, lexiques), 9 types de documents, 30 gabarits, leurres à ne pas masquer ; graines 2026102501 à 2026102510, 45 000 documents chacune | 450 000 (tous comptent) | exact par construction | 0 (positions rendues) | MIT (dépôt) |
| 2 | Équipe rouge FR | les 51 opérateurs de `tools/eval/mutate.py` (11 familles : espaces Unicode, invisibles, chiffres de substitution, sosies, tirets, séparateurs, mise en page, OCR, casse, accents, courriels maquillés) appliqués à 12 000 documents de base (graines 2026102521 à 2026102530, 1 200 chacune) | 548 907 documents mutés (décompte exact à blanc) | exact par construction | 0 | MIT |
| 3 | BODACC | annonces commerciales nommant une personne physique, parutions de septembre 2026 (`tools/corpus/build_bodacc.py`) | 2 693 / 1 335 (1 335) | exact par construction | 0/274 mentions (borne haute 95 % : 1,4 %) ; contre-relecture 0/83 | Licence Ouverte (Etalab) |
| 4 | BOAMP | avis de marchés 2022-2023, schéma `IDENTITE` (`tools/corpus/build_boamp.py`) | 3 000 / 1 477 (1 408) | exact pour e-mail, téléphone, adresse ; noms des contacts par règle | 6/287 mentions = 2,1 % [1,0–4,5] ; contre-relecture 3/96 = 3,1 % [1,1–8,8] | Licence Ouverte (Etalab) |
| 5 | ParlaMint-FR | débats de l'Assemblée nationale, ParlaMint 5.0 | 300 / 144 (143) | partiel : orateurs et personnes de la liste du corpus | non mesurée ; exact là où il annote, incomplet ailleurs | CC BY 4.0 |
| 6 | Presse ancienne FR | Europeana Newspapers FR (515 / 245, dont 209) et HIPE-2022 NewsEye FR (140 / 72, dont 63), regroupés en **une** famille | 655 / 317 (272) | manuel (auteurs des corpus) | non mesurée par nous ; HIPE inclut des titres (« abbé ») dans les noms | CC0 ; CC BY 4.0 |
| 7 | MAPA FR | textes juridiques de l'UE en français (EUR-Lex) | 12 / 8 (6) | manuel, un annotateur | non mesurée | CC BY 4.0 |

Les révisions figées, les sources et la construction du gold sont dans [`CORPUS_REELS.md`](CORPUS_REELS.md)
(sections 3 et 4 ; version anglaise : section 11) et
[`tools/corpus/real_registry.py`](../tools/corpus/real_registry.py). Environ 6 % des documents
synthétiques viennent de deux gabarits en anglais (un ticket, un e-mail) d'un contexte français : ils restent dans
la famille, comme dans l'évaluation de développement. Les 12 000 documents de base de l'équipe rouge passent
aussi par le service (pour mesurer la survie aux mutations) mais ne comptent pas dans l'indice.

### Hors périmètre, publiés à part et en évidence

| Corpus | Langue | Documents | Pays envoyés au service |
|---|---|---:|---|
| MAPA DE, ES, IT, NL, PT | de, es, it, nl, pt | 12, 9, 12, 12, 12 | DE, ES, IT, NL, PT |
| MEDDOCAN (identifiants de substitution) | es | 1 000 | ES |
| German LER (décisions fédérales) | de | 334 | DE |
| TAB (CEDH) | en | 127 | FR (pas de pack anglais) |

Mêmes chiffres que le périmètre français, jamais mêlés à l'indice. Le 25 octobre 2026, les packs DE, ES, IT, NL et
PT ne masquaient **aucun** nom : ces corpus le montrent.

### Témoin négatif : Judilibre (précision seulement)

300 décisions déjà pseudonymisées par les juridictions (Cour de cassation, cours d'appel, tribunaux judiciaires),
sans gold. Publiés : zones masquées pour 10 000 caractères et part des décisions avec au moins une zone. La part de
faux positifs ne se mesure que par relecture manuelle (dernière : 25 octobre 2026, 31,7 % [24,0–40,4] de 120
zones relues) ; la campagne ne la refait pas.

### Pas de documents bureautiques

Aucun jeu de documents bureautiques (PDF, Word, Excel) annoté n'existe dans le dépôt : la version 1.0 du protocole
mesure la route texte (`POST /v1/anonymize/text`) et non la conversion des fichiers. C'est une limite (section 12).

## 3. Sur quoi les règles ont été conçues : dev, test, graines

- **Corpus réels.** Partition fixe, écrite le 25 octobre 2026 avant toute modification des règles : SHA-256 de
  `gdprguardian-rules2-2026-10-25|<identifiant du document>`, premiers 32 bits pairs → `dev`, impairs → `test`
  ([`tools/corpus/real_common.py`](../tools/corpus/real_common.py), `split_of`). Les règles sont retouchées sur les
  moitiés `dev` à partir du 25 octobre 2026, jusqu'au **gel du moteur** avant la campagne (le moteur gelé est
  identifié dans les résultats par l'image du service et l'empreinte de ses sorties, section 9). **L'indice compte la
  moitié `test`**, jamais utilisée pour concevoir une règle. Les deux moitiés passent quand même par le service :
  l'indice sur tous les documents et sur la moitié `dev` sont publiés à côté, et l'écart `dev` − `test` mesure le
  sur-ajustement.
- **Mesures déjà faites sur les moitiés `test`** (toutes, avant la campagne ; aucune règle ne doit être réglée sur
  ces chiffres ; liste recopiée dans chaque résultat depuis `spec.TEST_HALVES_MEASURED_BEFORE`) :

  | Date (UTC) | Qui, quoi | Moteur | Résultat sur la moitié `test` |
  |---|---|---|---|
  | 25 oct. 2026 | analyse des corpus entiers ([`CORPUS_REELS.md`](CORPUS_REELS.md), sections 1 à 7), avant la partition | 1.0.0 de ce jour | rappels et fuites par corpus, pas d'indice |
  | 25 oct. 2026, 20 h 21 | mise au point du moteur : évaluation en processus des moitiés `dev` et `test`, avant toute retouche des règles ([`CORPUS_REELS.md`](CORPUS_REELS.md), section 12, colonne « avant ») | 1.0.0 | documents avec fuite stricte (définition de `tools/corpus`) : BODACC 93,0 %, BOAMP 52,8 %, ParlaMint-FR 27,3 %, Europeana 78,9 %, HIPE 98,4 %, MAPA FR 83,3 % ; pas d'indice |
  | 25 oct. 2026, 21 h 04 et 21 h 18 | essais de l'outil, plan réduit, corpus réels complets | sources de cet instant | indice 45,3 % [42,0–50,3] et 45,2 % [41,7–50,2] ; sans fuite : BODACC 8,0 %, BOAMP 47,2 %, ParlaMint-FR 72,7 %, presse ancienne 16,5 %, MAPA FR 16,7 % (synthétique 91,4 %, équipe rouge 64,5 %) |
  | 25 oct. 2026, 21 h 36 à 22 h 20 | mise au point du moteur : évaluation en processus des moitiés `test` et des corpus entiers à chaque itération des règles « rules2 » (quatre fois), et du moteur 1.0.0 sur les corpus entiers (21 h 53) ; la dernière publiée à 22 h 22 (`benchmarks/results/real-rules2-comparison-2026-10-25.{md,json}`, [`CORPUS_REELS.md`](CORPUS_REELS.md) section 12) | rules2 | documents avec fuite stricte (`tools/corpus`) : BODACC 10,1 %, BOAMP 39,4 %, ParlaMint-FR 7,0 %, Europeana 78,9 %, HIPE 98,4 %, MAPA FR 83,3 % ; pas d'indice |
  | 25 oct. 2026, 21 h 42 | audit indépendant de l'outil, plan réduit, corpus réels complets | sources de cet instant | indice 61,2 % [58,1–66,4] ; BODACC 89,4 %, BOAMP 55,5 %, ParlaMint-FR 93,0 %, presse ancienne 16,5 %, MAPA FR 16,7 % (synthétique 91,8 %, équipe rouge 65,5 %) |
  | 25 oct. 2026, 22 h 59 | relecture indépendante de la mise au point du moteur : évaluation en processus des moitiés `test` et des corpus entiers, moteurs 1.0.0 et rules2 (non publiée) | 1.0.0 et rules2 | mêmes chiffres que ceux publiés à 22 h 22 |
  | 26 oct. 2026 (ajout 1.1) | mise au point du moteur après revue indépendante : évaluation en processus des moitiés `dev` et `test` et des ensembles inédits, rules2 contre rules3 (`benchmarks/results/real-rules3-comparison-2026-10-26.{md,json}`, [`CORPUS_REELS.md`](CORPUS_REELS.md) section 13) | rules2 et rules3 | rappels et fuites par corpus, pas d'indice |
  | 26 oct. 2026 (ajout 1.1) | **campagne publique 1.0**, publiée (`benchmarks/results/protocol-2026-10-26.md`) | 1.0.0+0c3ff9fc1fb0 | indice 61,8 % [58,6–66,9] ; tous les chiffres par famille, corpus, libellé et opérateur |

  Le fichier de comparaison du 25 octobre dit que les moitiés `test` n'ont pas été « regardées » : leurs erreurs n'ont
  pas été lues, mais leurs scores ont été mesurés à chaque itération et publiés ; elles figurent donc ici. Après ces
  mesures, tout essai doit se faire sur la **seule moitié `dev`** (`pack-real --split dev` pour l'outil,
  `evaluate_real.py --split dev` pour la mise au point du moteur) ; une campagne standard refuse un tel paquet. Toute autre mesure
  d'une moitié `test` faite avant la campagne s'ajoute à ce tableau et à `spec.TEST_HALVES_MEASURED_BEFORE` avant
  l'enregistrement (section 15).
- **Campagnes répétées.** Après la première campagne publiée, les moitiés `test` ne sont plus aveugles : leurs scores
  par famille sont connus de qui retouche les règles. Une campagne suivante sur les mêmes moitiés le déclare : elle
  liste les campagnes antérieures dans `spec.EARLIER_CAMPAIGNS` (nouvelle version datée du protocole), que chaque
  résultat recopie, et le report vers le site refuse une campagne répétée qui omet celle déjà publiée. Pour une
  version ultérieure du moteur, l'indice principal devra passer sur des données neuves, construites avec les mêmes
  outils sur une période jamais mesurée (par exemple des parutions BODACC et BOAMP postérieures au gel du moteur)
  (**1.1 : dérogation déclarée**, le moteur 1.0.1 est noté sur les mêmes moitiés `test`, voir « Version 1.1 »). Les
  ensembles « inédits » BODACC d'août 2026 et BOAMP 2021 ([`CORPUS_REELS.md`](CORPUS_REELS.md), section 12) ont
  déjà été mesurés le 25 octobre : ils ne sont plus aveugles non plus.
- **Synthétique.** Graines neuves (2026102501 à 2026102510 ; 2026102521 à 2026102530 pour l'équipe rouge). La graine
  de développement (20261024, l'évaluation de 540 documents qui a servi à régler le moteur) est **exclue par le
  code** : l'outil refuse un plan qui la contient.
- **Limite assumée.** L'analyse des faiblesses du 25 octobre ([`CORPUS_REELS.md`](CORPUS_REELS.md), section 7) a porté
  sur les corpus entiers, et les mesures du tableau ci-dessus ont vu les moitiés `test` : celles-ci ne sont pas
  aveugles aux *types* d'erreurs (numéros RCS des entrepreneurs, noms à particule, adresses BOAMP…) ; entre les deux
  essais, BODACC passe de 8,0 % à 89,4 % après une modification des règles, et les scores des
  moitiés `test` étaient visibles à chaque itération de rules2. Elles le sont aux valeurs : aucun nom ni numéro d'un corpus réel ne doit
  entrer dans le moteur, dont le code est public.

## 4. Ce qu'est un identifiant direct, par corpus

- **Synthétique et équipe rouge** : les libellés du gold de type `DIRECT` ([`tools/eval/schema.py`](../tools/eval/schema.py)) :
  PERSON, EMAIL, PHONE, ADDRESS, NIR, IBAN, RIB, RIB_SPLIT, CARD, SIRET et SIREN (entrepreneurs individuels seulement),
  VAT, TAX_ID, PASSPORT, ID_CARD, PLATE, RPPS, CAF, FRANCE_TRAVAIL, IP. Ne comptent pas : les quasi-identifiants
  (BIRTH_DATE, LOCATION, ORG, ID pour les numéros de client, de patient ou de matricule) et les leurres (montants,
  numéros de commande et de facture, références légales, identifiants de sociétés…).
- **Corpus réels** : les familles personnelles de `tools/corpus` sauf la date de naissance : PERSON, ADDRESS, EMAIL,
  PHONE, NATIONAL_ID, TAX_ID, IBAN, BANK_ACCOUNT, CARD, ID, URL, IP. Présentes : BODACC PERSON, ADDRESS, ID (numéro
  RCS/RM, c'est-à-dire le SIREN d'un entrepreneur individuel) ; BOAMP PERSON, ADDRESS, EMAIL, PHONE (quel qu'en soit le
  titulaire, souvent un organisme public : le moteur ne le sait pas) ; ParlaMint PERSON ; presse ancienne PERSON ;
  MAPA FR PERSON, ADDRESS. Conservés par politique, hors calcul : ORG, ORG_ID, LOCATION, DATE, OTHER.
- Une mention ne compte que si elle contient au moins un caractère alphanumérique.

## 5. Fuite, indice, intervalle

**Lisible.** Un caractère alphanumérique de l'entrée est lisible s'il figure encore, à sa place, dans la sortie du
service. Le service ne rend pas de positions : l'outil les retrouve en alignant la sortie sur l'entrée (balises
`[LIBELLE_N]`, caractères invisibles que la sortie retire). Quand un segment de texte entre deux balises peut se
placer à plusieurs endroits, tout caractère qui **peut** être visible compte comme visible (borne prudente).
Vérification en processus, sur 48 955 documents distincts (évaluation de développement et ses 6 192 mutations,
20 000 documents synthétiques neufs, 13 745 mutés, les 8 478 documents réels) : zones reconstruites identiques à
celles du moteur sur chaque document synthétique, aucune borne prudente prise en défaut (aucun caractère vraiment
visible manqué), et 3 documents réels seulement (BODACC 1, BOAMP 2 ; 10 caractères en tout) où la borne prudente
compte comme visibles des caractères en fait masqués.

**Fuite.** Un document fuit dès qu'**un** caractère alphanumérique d'**une** mention d'identifiant direct du gold
reste lisible (le dernier chiffre d'un téléphone suffit).

**Échecs.** Un document que le service refuse ou n'arrive pas à traiter (toute erreur HTTP après les reprises), ou
dont la sortie ne s'aligne pas, compte comme une **fuite**, toutes ses mentions directes non masquées.

**Documents sans mention directe** : exclus de l'indice (ils le gonfleraient), comptés et publiés.

**Formules.** Pour chaque famille *f* : *P<sub>f</sub>* = documents sans fuite / documents ayant au moins une mention
directe. **Indice = (1/7) · Σ<sub>f</sub> *P<sub>f</sub>***, sur les sept familles, quelle que soit leur taille : un
million de documents synthétiques pèsent autant que les 6 documents MAPA FR de la moitié test. **Rappel des mentions
= (1/7) · Σ<sub>f</sub> (mentions directes entièrement masquées / mentions directes)**. Sans les sept familles, pas
d'indice.

**Intervalle à 95 %.** Bootstrap stratifié sur les **documents** : dans chaque famille, on tire avec remise autant de
documents qu'elle en compte ; 2 000 tirages, graine 20261025, percentiles 2,5 et 97,5. Le tirage s'appuie sur
l'histogramme des issues par document (mentions directes, mentions masquées) : le nombre de documents tirés dans
chaque case suit exactement une loi multinomiale, tirée par binomiales successives, soit la même loi qu'un tirage
document par document, sans tableau d'un million d'entrées ([`tools/protocol/stats.py`](../tools/protocol/stats.py),
test d'équivalence dans [`tests/protocol/test_stats.py`](../tests/protocol/test_stats.py)). Même méthode pour
l'intervalle du rappel des mentions.

**Ce que l'intervalle ne couvre pas.** Il ne mesure que le hasard du tirage des documents : ni les erreurs du gold
(section 2), ni le choix des sept familles, ni la dépendance entre documents mutés (les ~46 variantes d'un même
document de base sont retirées comme si elles étaient indépendantes, ce qui rend trop étroit l'intervalle de la famille
équipe rouge). Un seul document MAPA FR (6 notés) déplace l'indice de 1/6 × 1/7 ≈ 2,38 points : MAPA FR fait à lui
seul l'essentiel de la largeur de l'intervalle (environ 95 % de sa variance dans les essais).

## 6. Autres chiffres publiés

- **Par famille** : part des documents sans fuite (intervalle de Wilson), rappel des mentions, rappel par type
  d'identifiant, erreurs du service, alignements ambigus.
- **Familles synthétiques** (définitions de `tools/eval`) : rappel au caractère (directs, structurés, tous), précision
  (caractères masqués tombant sur une donnée personnelle du gold), sur-masquage du texte neutre, leurres masqués à tort,
  taux de fuite au sens de `tools/eval` (strict, structuré, littéral), rappel des entités.
- **Corpus réels** (définitions de `tools/corpus`, moitié test, moitié dev et tous les documents) : rappel strict et à
  80 % des mentions, rappel au caractère, précision avec intervalle bootstrap (précision non mesurable sur
  ParlaMint), sur-masquage, documents qui fuient (strict et littéral), familles conservées touchées.
- **Équipe rouge, par opérateur** : part sans fuite, rappel des mentions, **survie** (mentions masquées sans mutation
  qui le restent après).
- **Par graine** : part sans fuite (stabilité d'une graine à l'autre).
- **Hors périmètre**, dans une section à part des résultats, jamais mêlée au périmètre français, et **témoin
  Judilibre** : section 2.
- **Historique** : mesures des moitiés `test` faites avant la campagne et campagnes antérieures (section 3).
- **Écarts déclarés** : tout écart permis à la procédure (swap actif, service redéployé après la fin de la campagne),
  inscrit par `run-protocol.sh` dans le point de reprise et les résultats, et rappelé par le report vers le site.
- **Campagne** : documents, débit, temps cédé aux visiteurs, reprises, erreurs, empreinte du moteur (image du
  service, version, packs, sorties sur la sonde) et nombre de contrôles du moteur, jeton local reconnu ou non,
  empreinte du plan, empreintes SHA-256 des documents synthétiques, mutés et réels envoyés.
- **Enregistrement** : empreintes de l'outil (fichiers `tools/`, `spec.py`, ce texte, paquet, Faker) et
  comparaison du décompte envoyé (documents, empreintes) au décompte enregistré dans `spec.py` (section 15).

Fichiers : `benchmarks/results/protocol-<date>.json` et `.md` (1.0) ; à partir de la 1.1,
`protocol-<version>-<date>.json` et `.md` (`spec.RESULTS_STEM`), jamais écrasés. Le site reçoit dix clés (section 10).

## 7. Garde-fous : l'indice seul pourrait mentir

Un moteur qui masquerait tout obtiendrait 100 %. L'indice n'est donc publié que si, sur la même campagne :

| Garde-fou | Seuil | Mesure de référence (25 octobre 2026) |
|---|---|---|
| Sur-masquage du texte neutre, familles synthétiques | ≤ 2 % | 0,08 % |
| Leurres masqués à tort, famille synthétique | ≤ 10 % | 3,5 % |
| Précision au caractère, BODACC et BOAMP (moitié test) | ≥ 70 % chacun | 90,1 % et 80,9 % (tous documents) |

Le script de report vers le site refuse sinon ; le forcer (`--force-guards`) oblige à le déclarer publiquement. La
précision et le sur-masquage sont toujours publiés à côté de l'indice.

## 8. Ce qui pourrait embellir l'indice, et ce que le protocole y oppose

| Ce qui embellirait | Ce que fait le protocole |
|---|---|
| Régler les règles sur les documents mesurés | indice sur la moitié `test` ; graines neuves ; graine de développement refusée par le code ; écart `dev` − `test` publié ; toute mesure antérieure des moitiés `test` listée (section 3) et recopiée dans les résultats |
| Répéter la campagne sur des moitiés `test` déjà vues | campagnes antérieures listées dans `spec.EARLIER_CAMPAIGNS` et recopiées dans les résultats ; report vers le site refusé si la campagne publiée manque ; données neuves pour un moteur suivant |
| Taire un écart à la procédure | écarts permis (swap, redéploiement après la fin) inscrits dans les résultats et rappelés par le report vers le site ; `--force-guards` à déclarer |
| Données synthétiques faciles (mêmes gabarits que ceux sur lesquels le moteur a été réglé : les valeurs changent, pas les mises en page) | synthétique et équipe rouge ne pèsent que 2/7, quel que soit leur volume ; chaque famille est publiée |
| Le volume | poids égal par famille |
| Tout masquer | garde-fous ; précision, sur-masquage et leurres publiés à côté |
| Écarter les documents difficiles, les erreurs | une erreur ou une sortie non alignable compte comme une fuite ; documents sans gold comptés et publiés |
| Une définition indulgente de la fuite | stricte : un seul caractère alphanumérique visible suffit |
| Un alignement complaisant | borne prudente : ce qui peut être visible compte comme visible |
| Arrêter la campagne quand le chiffre plaît, garder le meilleur essai | tailles fixées ici ; la campagne va à son terme ; aucun rapport final sur une campagne incomplète ; une campagne terminée ne se relance pas dans le même dossier ; chaque campagne publiée, datée (une campagne abandonnée garde un rapport partiel, à déclarer) |
| Changer de moteur en cours de campagne | une campagne = un moteur : image du service, version, packs et sorties sur une sonde fixe contrôlés au départ, à chaque point de reprise, après toute panne ou tout redémarrage et à la fin ; un écart arrête tout, sans rien écrire après le dernier contrôle réussi ; `finish` revérifie l'image |
| Retoucher les définitions après coup | empreintes de `spec.py`, de ce texte et du paquet publiées avant le lancement et recopiées dans les résultats, recalculées depuis le contenu du paquet à chaque départ (un paquet modifié après sa construction est refusé) ; décompte du plan comparé à celui enregistré, report vers le site refusé sinon ; reprise refusée si l'outil change |
| Une surcharge du service comptée comme fuites (ou l'inverse) | `429`/`503` au-delà de 30 minutes pour un document : pause, jamais une fuite ; report refusé si une telle erreur a été comptée |
| Une campagne passée sans le jeton local (trafic compté comme public) | sonde `/health/deep` au départ : campagne standard refusée sans jeton reconnu ; report refusé sinon |
| Choisir le pays ou le profil qui arrange | réglages par défaut du produit : FR, `standard`, balises en français |
| Gold incomplet (ParlaMint, noms seuls non annotés) | il **favorise** l'indice : un nom non annoté n'est pas compté comme fuite ; c'est écrit ici et la famille ne pèse qu'un septième |
| Erreurs du gold (BOAMP 2,1 %) | elles jouent dans les deux sens ; taux mesurés publiés |
| Apprendre les valeurs des corpus publics (listes de noms) | moitié `test` jamais utilisée ; le moteur est public : toute liste tirée d'un corpus se verrait |

## 9. La campagne sur le serveur de production

- **Outil** : [`tools/protocol/`](../tools/protocol/), bibliothèque standard de Python plus Faker (MIT, pur Python),
  livré en un paquet autonome reproductible (`gg-protocol.pyz`, qui porte aussi ce texte). Il tourne dans un
  **conteneur jetable de l'image exacte du service en cours** (même Python 3.12) : aucun réseau, système en lecture
  seule, utilisateur 10001, aucune capacité, 2 Go de mémoire sans swap, aucun fichier core (`--ulimit core=0` : la
  mémoire de l'outil porte les corpus réels), un processeur à faible priorité (`--cpu-shares 256`), socket du service
  en lecture seule ; le jeton local arrive sur l'entrée standard depuis son fichier root 0600, jamais en argument ni
  sur disque ([`tools/protocol/server/run-protocol.sh`](../tools/protocol/server/run-protocol.sh)). Au départ,
  l'outil recalcule les empreintes du paquet depuis son contenu et refuse un paquet modifié après sa construction.
- **Refus au départ, avant toute requête** : une campagne standard (graines et tailles enregistrées) est refusée sans
  l'image du service, avec des tailles d'unité autres que celles enregistrées (les empreintes du plan en dépendent),
  avec un drapeau d'essai (`--allow-disk-real`, sonde fixée), ou avec un paquet de corpus réels réduit à la moitié
  `dev` ou privé d'un des quinze corpus (sans quoi l'indice manquerait après des heures de travail).
- **Jeton local vérifié** : au départ, l'outil interroge `/health/deep`, qui n'existe que pour le principal LOCAL ;
  sans jeton reconnu, une campagne standard est refusée (un essai continue, signalé comme trafic public).
- **Requêtes** : `POST /v1/anonymize/text` sur le socket Unix du service, **sans** `X-GG-Client` et **avec** le jeton
  local `X-GG-Local` : principal LOCAL, hors budgets par client, deux traitements à la fois au plus, jamais la place
  réservée aux petites requêtes. Chaque document envoie un datagramme d'usage `"src":"protocol"` : **toute la campagne
  compte dans les statistiques publiques du site, comme protocole** (sondes du moteur comprises). Options :
  `countries` FR (ou le pays du corpus hors périmètre), `profile` `standard`, `label_language` `fr`.
- **Une campagne = un moteur** : empreinte du moteur = image du conteneur du service (`docker inspect`, passée par
  `run-protocol.sh`), version, catalogue des packs et SHA-256 des **sorties** du service sur une sonde fixe (200
  documents de la graine de développement, jamais notés). Contrôlée au départ, avant chaque point de reprise (toutes
  les 60 secondes), après toute panne de connexion ou tout redémarrage du service (compteurs de `/status` en baisse)
  et à la fin. Un soupçon de redémarrage abandonne les unités en cours (refaites ensuite) et bloque les nouvelles
  jusqu'au contrôle ; une unité n'est comptée qu'après un relevé de `/status` sans redémarrage postérieur à sa fin.
  Un écart arrête la campagne sans rien écrire après le dernier contrôle réussi ; la reprise exige le même moteur ;
  `finish` vérifie encore que l'image du service est celle du début. Coût : 200 requêtes par minute de campagne
  (environ 1,5 % des requêtes ; une sonde dure 2 secondes environ sous WSL), prioritaires sur les fils de travail.
- **Priorité aux visiteurs** : l'ordonnanceur du service sert un visiteur en attente avant le traitement suivant de
  la campagne ; en plus, l'outil lit `/status` toutes les 2 secondes et ne garde qu'une requête en vol tant que
  quelqu'un d'autre occupe ou attend une place ; `429` et `503` sont respectés (`Retry-After`, gigue) ; au-delà de
  30 minutes d'attente pour un même document, la campagne se met en **pause** (une surcharge n'est jamais comptée
  comme une fuite). Mesuré sous WSL avec quatre visiteurs envoyant sans relâche des textes de 20 Ko : 95 % des
  réponses en 27 ms seuls, en 57 ms pendant la campagne (aucun refus) ; la campagne a cédé la place 24 secondes sur
  une minute.
- **Concurrence** : trois fils (deux en cours au service, un en file).
- **Reprise** : unités rejouables à l'identique (1 500 documents synthétiques, 30 bases d'équipe rouge, 100 documents
  réels) ; point de reprise atomique et durable (copie de la version précédente, `fsync`, retour à la copie si le
  dernier est illisible ; agrégats seulement) ; arrêt (`stop`, SIGTERM) = pause ; `start` reprend ; reprise refusée
  si le moteur, l'outil, le plan ou les corpus réels ont changé : ne pas redéployer le service pendant une campagne.
  Une erreur de notation d'un document compte comme une fuite (`exception:<type>`) ; une erreur de l'outil hors d'un
  document arrête la campagne avec son type, jamais en silence. Une campagne terminée ne se relance pas : `finish`
  archive son dossier de travail (`/var/lib/gg-protocol-<date>-<plan>`). Sur une campagne incomplète, `finish`
  n'efface rien (le paquet des corpus réels reste en mémoire vive si leurs unités ne sont pas faites) et `start` la
  reprend ; elle s'abandonne par `GG_PROTOCOL_ABANDON=1 bash run-protocol.sh finish`, qui garde un rapport partiel à
  déclarer.
- **Écarts permis, inscrits** : `GG_PROTOCOL_ALLOW_SWAP=1` (swap actif malgré tout) et
  `GG_PROTOCOL_REDEPLOYED_AFTER=1` (service redéployé après la fin de la campagne, avant `finish`) ne passent qu'en
  laissant une trace : `run-protocol.sh` les inscrit (`--disclose`) dans le point de reprise et les résultats, et le
  report vers le site les rappelle ; ils sont à déclarer avec l'indice.
- **Rien que des scores** : l'outil n'écrit ni n'affiche jamais un texte, une valeur annotée ou une sortie du service ;
  points de reprise et résultats ne contiennent que des compteurs, des bits (un par document) et des empreintes.
- **Corpus réels en mémoire vive seulement** : le paquet est copié dans `/dev/shm` (tmpfs), l'outil refuse un paquet
  hors mémoire vive, et `run-protocol.sh` refuse de travailler si un swap est actif (une page de tmpfs pourrait
  atteindre le disque ; `sudo swapoff -a` le temps de la campagne). Les corpus réels passent en premier (quelques
  minutes) ; dès leurs unités enregistrées, **l'outil efface le paquet**, l'oublie et l'inscrit aussitôt dans le
  point de reprise ; `finish` d'une campagne terminée ou abandonnée vide aussi `/dev/shm/gg-protocol`. Les corpus
  BODACC et BOAMP sont reconstruits depuis leur source le jour de la campagne si possible (demandes de suppression de
  la DILA), et le paquet local est effacé après la copie.
- **Durée** : mesurée sous WSL (16 cœurs, service local en mode public, jeton local, deux places LOCAL, outil dans
  un conteneur jetable) : 215 à 225 documents synthétiques par seconde, 2,4 ms de processeur client par document ;
  les 8 478 documents réels en 4 minutes environ, dont 3 pour les corpus hors périmètre (les moteurs DE, ES, IT, NL,
  PT ne sont pas préchargés : environ 0,3 s par requête). Le plan complet (1 019 385 documents) demande donc environ
  1 h 20 sur une telle machine. **Sur le serveur, la durée n'est pas mesurée** : avant la campagne, un essai
  chronométré (paquet de la seule moitié `dev`, plan réduit par `GG_PROTOCOL_ARGS`, section 10) donne le débit, d'où
  la durée du plan complet ; la campagne doit finir avant la maintenance du serveur (1 h 45, heure de Paris), sinon
  `GG_PROTOCOL_HOURS` la met en pause propre (par exemple au bout de 3 heures) et `start` la reprend plus tard.

## 10. Rejouer

Depuis la racine du dépôt (Python 3.12+), `DIR` hors du dépôt :

```
python tools/corpus/build_bodacc.py --cache DIR --per-family 500 --start 2026-09-01 --end 2026-09-30
python tools/corpus/build_boamp.py  --cache DIR --per-month 125 --start 2022-01 --end 2023-12
python tools/corpus/fetch_real.py   --cache DIR
python -m tools.protocol plan --count                      # sans service : nombres et empreintes ci-dessous
python -m tools.protocol bundle --out gg-protocol.pyz      # paquet autonome, reproductible au bit près
python -m tools.protocol registration --bundle gg-protocol.pyz   # empreintes à publier AVANT le lancement
python -m tools.protocol pack-real --cache DIR --out /dev/shm/gg/real-corpora.jsonl.gz
python -I gg-protocol.pyz run --socket /run/gdprguardian/app.sock --token-stdin --engine-id IMAGE --work WORK \
       --real /dev/shm/gg/real-corpora.jsonl.gz --wipe-real-when-done < /etc/gdprguardian/local-header
python tools/protocol/merge_quality.py WORK/results/protocol-<version>-<date>.json site/data/quality.json
```

`IMAGE` est l'image du conteneur du service (`docker inspect -f '{{.Image}}' <conteneur>`). Un service se lance comme
dans [`deploy/README.md`](../deploy/README.md) (mode public, `GDPRGUARDIAN_LOCAL_TOKEN_SHA256`). Pour un **essai**,
jamais publié : plan réduit (`--synthetic-docs`, `--redteam-bases`…) et paquet de la seule moitié `dev`
(`pack-real --split dev`), pour ne plus toucher aux moitiés `test`.

**Sur le serveur, dans l'ordre** ([`docs/PUBLISHING.md`](PUBLISHING.md) détaille les copies) : geler et déployer le
moteur ; refaire le contrôle croisé sur ce moteur (section 11) ; construire le paquet, `registration --bundle`, publier
ces empreintes ; `bash run-protocol.sh prepare` (refusé tant qu'un swap est actif : `sudo swapoff -a`) ; **essai
chronométré** avec un paquet `--split dev` et `GG_PROTOCOL_ARGS="--synthetic-docs 3000 --redteam-bases 30"`, puis
`status` (débit) et `finish` (résultats rangés à part dans `results/trial-<date>/`, jamais publiés) ; puis `prepare`
à nouveau, le paquet complet dans `/dev/shm/gg-protocol/`, `GG_PROTOCOL_HOURS=3 bash run-protocol.sh start`, `status` jusqu'à la fin,
`finish`, et le report vers le site. Empreintes attendues du plan (Faker 40.43.0),
enregistrées aussi dans `spec.REGISTERED_PLAN` et comparées par l'outil : 450 000 documents synthétiques, 12 000
bases, 548 907 documents mutés ; SHA-256 synthétique
`0b91be78435e5434ee5a3b136ab8f08dd10a2c3673dad56fc6dca469c87a955b`, équipe rouge
`d984ee1bf9dba70bf2ccf32957cab9da9bbf1fdf02adf5b7444956fa0137760b`. Les corpus BODACC et BOAMP viennent d'une API
vivante : leurs empreintes, publiées dans les résultats, peuvent changer d'un téléchargement à l'autre.

Clés du site (`site/data/quality.json`) : `confidence_index`, `confidence_ci_low`, `confidence_ci_high`,
`mention_recall_pct` (pourcentages à une décimale), `protocol_docs` (documents envoyés par la campagne, sondes du
moteur non comprises), `protocol_families` (7), `real_corpora` et `real_docs` (corpus réels annotés et leurs
documents, sans le témoin Judilibre), `protocol_date` (date ISO de la campagne), `protocol_engine` (version du service
et 12 premiers caractères de son image, par exemple `1.0.0+af877bdf62ae` : deux moteurs de même version restent
distincts). Tant qu'une campagne complète n'a pas eu lieu, elles valent « — » et le site affiche « pas encore
mesuré ».

## 11. Contrôle croisé de l'outil (fait avant la campagne, refait sur le moteur gelé)

**Méthode.** L'évaluation synthétique de développement (540 documents et 6 192 mutés, graine 20261024) passe par un
service local en mode public avec jeton local (socket Unix) ; l'outil reconstruit les zones masquées depuis la seule
sortie, puis les fonctions de `tools/eval` les notent. Chaque nombre du résumé (8 535 feuilles pour les mutés) est
comparé à l'évaluation **en processus du même moteur** (copie figée des sources, chargée par le service et par
l'évaluation) et au fichier de référence du dépôt ([`tools/protocol/crosscheck.py`](../tools/protocol/crosscheck.py),
commandes `crosscheck` puis `crosscheck-summary`). L'outil est validé quand, sur le même moteur, les dix indicateurs
principaux sont identiques, aucun document n'échoue et chaque autre écart est un effet de frontière : la frontière
entre deux balises séparées par une espace ne se lit pas dans la sortie, ce qui ne touche que les chiffres par
libellé du *système* (confusion, précision et F2 par libellé, taux typé, rappel strict d'entité), jamais ce qui est
masqué. Un écart avec le fichier de référence où le service et l'évaluation en processus s'accordent vient du moteur,
qui a changé depuis la référence (ou, pour les bornes d'intervalle, des tirages).

**Résultats.**

- **25 octobre 2026, 20 h 47 UTC, moteur d'avant rules2** : les dix indicateurs du service égalaient au bit près ceux
  de `eval-2026-10-25-standard.json` (rappel direct 99,18 %, précision 98,82 %, fuite stricte 9,07 %…). La partie
  « même moteur » de ce jour a chargé une copie prise pendant une retouche (2 documents en échec des deux côtés) :
  elle est remplacée ([`protocol-crosscheck-2026-10-25.md`](../benchmarks/results/protocol-crosscheck-2026-10-25.md),
  gardé pour l'historique).
- **26 octobre 2026, 00 h 04 UTC, copie figée des sources du moteur rules2** (empreinte de l'arbre `a992428d25533cc6`,
  moteur Python : le noyau natif installé ne faisait pas tourner ces sources ; empreinte de sonde `eeb38986e44c`, celle
  qu'une campagne enregistre pour un moteur aux mêmes sorties) : **outil validé** pour les pays `auto` et `FR` ; dix
  indicateurs identiques entre service et évaluation en processus (rappel direct 99,23 %, précision 98,82 %, fuite
  stricte 8,33 %), aucun échec ; 12 feuilles sur 773 (base) et 31 sur 8 535 (mutés) diffèrent, toutes par l'effet de
  frontière. Contre `eval-2026-10-25-standard-fr-rules2.json` (pays `FR`), les dix indicateurs sont identiques ; les
  10 feuilles des mutés qui diffèrent viennent du moteur, retouché depuis cette référence. Détail :
  [`protocol-crosscheck-2026-10-26.md`](../benchmarks/results/protocol-crosscheck-2026-10-26.md).
- Le moteur était encore en cours de mise au point pendant ce contrôle : il est **refait sur le moteur gelé**, avant
  l'enregistrement, et son empreinte de sonde doit égaler celle de la campagne.

## 12. Limites et biais connus

- Données synthétiques : gabarits connus du moteur ; l'équipe rouge ne couvre que 51 opérateurs.
- Gold : BOAMP 2,1 % d'erreurs mesurées ; ParlaMint partiel (favorable) ; titres dans les noms HIPE (défavorable) ;
  MAPA FR minuscule (6 documents notés dans la moitié test : un document déplace l'indice de 2,38 points).
- Poids réel : la campagne envoie plus d'un million de documents, mais cinq septièmes de l'indice reposent sur les
  3 164 documents notés des moitiés `test` réelles.
- L'intervalle ne couvre que le tirage des documents : ni les erreurs du gold, ni le choix des familles, ni la
  dépendance entre variantes mutées d'un même document (section 5).
- Moitiés `test` déjà mesurées avant la campagne (section 3, tableau) : par la mise au point du moteur avant les retouches
  (20 h 21 UTC) et à chaque itération des règles rules2 (21 h 36 à 22 h 20, publiée à 22 h 22), par deux essais de
  l'outil, par son audit et par la relecture de la mise au point du moteur. Leurs erreurs n'ont pas été lues, mais leurs scores
  étaient visibles pendant la mise au point : un réglage involontaire sur ces scores ne peut pas être exclu ; l'écart
  `dev` − `test` publié en donne la mesure.
- Après la première campagne publiée, les moitiés `test` ne sont plus aveugles : une campagne répétée le déclare
  (section 3) ; un moteur suivant demande des données neuves.
- Règles retouchées sur les moitiés `dev` à partir du 25 octobre 2026, jusqu'au gel du moteur ; analyse des
  faiblesses faite sur les corpus entiers.
- Seulement des identifiants directs : la ré-identification par le contexte (fonction, lieu, événement rare) n'est
  pas mesurée.
- Route texte seulement : la conversion des PDF, Word, Excel n'est pas mesurée (aucun gold bureautique).
- Mise en page de BODACC et BOAMP reconstruite ; entités HTML non décodées dans BOAMP.
- Les corpus réels contiennent des données publiques de personnes réelles : ils ne quittent jamais la machine de
  mesure que vers la mémoire vive du serveur, ne sont ni versionnés ni republiés, et sont effacés après usage.
- Le serveur sert aussi les visiteurs pendant la campagne : le débit en dépend, pas les scores.

## 13. Fichiers

| Fichier | Rôle |
|---|---|
| `tools/protocol/spec.py` | définitions pré-enregistrées (familles, graines, tailles, identifiants directs, garde-fous, mesures antérieures des moitiés `test`, campagnes antérieures, écarts à déclarer) |
| `tools/protocol/align.py` | zones masquées retrouvées depuis la seule sortie du service |
| `tools/protocol/outcomes.py`, `stats.py` | notation par document, agrégats, indice, bootstrap |
| `tools/protocol/campaign.py`, `transport.py`, `plan.py` | campagne, empreinte et contrôles du moteur, socket et jeton local, plan, reprise |
| `tools/protocol/report.py`, `merge_quality.py` | résultats JSON et Markdown, report vers le site |
| `tools/protocol/bundle.py`, `provenance.py`, `server/run-protocol.sh` | paquet autonome, empreintes de l'outil et enregistrement, lancement sur le serveur |
| `tools/protocol/crosscheck.py`, `dryrun.py` | contrôle croisé et son résumé publié, décompte à blanc |
| `tests/protocol/` | tests (alignement, bootstrap, reprise, moteur changé ou redémarré, jeton local, aucun texte écrit, report, refus au départ, paquet altéré, écarts déclarés, campagnes répétées, contrôle croisé) |

## 14. English version

**Version 1.0, written on 25 October 2026, before any campaign; registered by publishing, before the launch, the
digests of this text, of `spec.py` and of the tool bundle (section 15)**; every result copies the digests of what
produced it. Executable definitions: [`tools/protocol/spec.py`](../tools/protocol/spec.py), the single source of truth
of this document; tool: [`tools/protocol/`](../tools/protocol/); tests: [`tests/protocol/`](../tests/protocol/).
Changing a definition means a new dated version; the old one stays in the repository history and every published
result names its version. Text completed on 26 October 2026, before the registration and before any campaign:
earlier measurements of the `test` halves (item 3), repeat campaigns, disclosed departures, refusals at start (item
9); no definition of the index changed.

**1. What is measured.** One question: in what share of documents does the service leave at least one direct
identifier readable? GDPR Guardian is a first barrier, not a "zero leak" promise. The **confidence index** is the
share of documents without any leak, computed per family, then averaged with **equal weight** over the seven
French-scope families, with a 95% interval. The **direct-mention recall** is the share of direct-identifier mentions
fully masked, same families, same equal weight. Every other figure (item 6) is published next to it, never instead.

**2. Families and corpora.** French scope, the seven families of the index:

| # | Family | Source | Documents (all / test half, with a direct mention) | Gold | Measured gold error | Licence |
|---|---|---|---|---|---|---|
| 1 | Synthetic FR | `tools/eval/generate.py` (Faker 40.43.0 `fr_FR`, lexicons), 9 document kinds, 30 templates, decoys that must stay; seeds 2026102501 to 2026102510, 45,000 documents each | 450,000 (all count) | exact by construction | 0 | MIT (repository) |
| 2 | Red team FR | the 51 operators of `tools/eval/mutate.py` (11 families: Unicode spaces, invisibles, substitute digits, look-alikes, dashes, separators, layout, OCR, case, accents, obfuscated e-mails) on 12,000 base documents (seeds 2026102521 to 2026102530, 1,200 each) | 548,907 mutated documents (exact dry-run count) | exact by construction | 0 | MIT |
| 3 | BODACC | commercial announcements naming a natural person, September 2026 | 2,693 / 1,335 (1,335) | exact by construction | 0/274 mentions (95% upper bound 1.4%); independent recheck 0/83 | Licence Ouverte (Etalab) |
| 4 | BOAMP | 2022-2023 procurement notices, `IDENTITE` schema | 3,000 / 1,477 (1,408) | exact for e-mail, phone, address; contact names by a rule | 6/287 mentions = 2.1% [1.0–4.5]; independent recheck 3/96 = 3.1% [1.1–8.8] | Licence Ouverte (Etalab) |
| 5 | ParlaMint-FR | Assemblée nationale debates, ParlaMint 5.0 | 300 / 144 (143) | partial: speakers and listed persons | not measured; exact where it annotates, incomplete elsewhere | CC BY 4.0 |
| 6 | Old French press | Europeana Newspapers FR (515 / 245, 209) and HIPE-2022 NewsEye FR (140 / 72, 63) pooled as **one** family | 655 / 317 (272) | manual (corpus authors) | not measured by us; HIPE includes titles ("abbé") in names | CC0; CC BY 4.0 |
| 7 | MAPA FR | EU legal texts in French (EUR-Lex) | 12 / 8 (6) | manual, single annotator | not measured | CC BY 4.0 |

Pinned revisions, sources and gold construction: [`CORPUS_REELS.md`](CORPUS_REELS.md) (sections 3 and 4; English
version: section 11) and `tools/corpus/real_registry.py`. About 6% of the synthetic documents come from two English templates (a ticket, an
e-mail) of a French context; they stay in the family, as in the development evaluation. The 12,000 red-team base
documents also go through the service (to measure survival) but do not count in the index. **Out of scope,
published apart and prominently**: MAPA DE, ES, IT, NL, PT (12, 9, 12, 12, 12 documents; sent with DE, ES, IT, NL,
PT), MEDDOCAN (es, 1,000, surrogate identifiers; ES), German LER (de, 334; DE), TAB (en, 127; FR, no English pack);
on 25 October 2026 the DE, ES, IT, NL and PT packs masked **no** name at all. **Negative control, precision only**:
Judilibre, 300 decisions already pseudonymised by the courts, no gold; published: masked spans per 10,000
characters and share of decisions with a masked span; the false-positive share needs a manual review (last one on
25 October 2026: 31.7% [24.0–40.4] of 120 reviewed spans) that the campaign does not redo. **No office documents**:
no gold-annotated office set exists in the repository, so version 1.0 measures the text route
(`POST /v1/anonymize/text`), not file conversion.

**3. What the rules were designed on.** Real corpora: fixed split written on 25 October 2026 before any rule change,
SHA-256 of `gdprguardian-rules2-2026-10-25|<document id>`, first 32 bits even → `dev`, odd → `test`
(`tools/corpus/real_common.split_of`). Rules are adjusted on the `dev` halves from 25 October 2026 until the **engine
is frozen** before the campaign (the frozen engine is identified in the results by the service image and the digest
of its outputs, item 9); **the index counts the `test` halves**, never used to design a rule. Both halves still go
through the service: the index on all documents and on the `dev` half is published next to it, and the `dev` − `test`
gap measures overfitting. **Measurements already taken on the `test` halves** (all of them, before the campaign; no
rule may be tuned on these figures; the list is copied into every result from `spec.TEST_HALVES_MEASURED_BEFORE`),
all on 25 October 2026, UTC:

| When (UTC) | Who, what | Engine | Result on the `test` half |
|---|---|---|---|
| during the day | whole-corpus analysis (`CORPUS_REELS.md`, sections 1 to 7), before the split | 1.0.0 of that day | per-corpus recalls and leaks, no index |
| 20:21 | engine tuning: in-process evaluation of the `dev` and `test` halves before any rule change (`CORPUS_REELS.md`, section 12, "before" column) | 1.0.0 | documents with a strict leak (`tools/corpus` definition): BODACC 93.0%, BOAMP 52.8%, ParlaMint-FR 27.3%, Europeana 78.9%, HIPE 98.4%, MAPA FR 83.3%; no index |
| 21:04 and 21:18 | tool trials, scaled plan, full real corpora | sources of that moment | index 45.3% [42.0–50.3] and 45.2% [41.7–50.2]; no-leak shares BODACC 8.0%, BOAMP 47.2%, ParlaMint-FR 72.7%, old press 16.5%, MAPA FR 16.7% (synthetic 91.4%, red team 64.5%) |
| 21:36 to 22:20 | engine tuning: in-process evaluation of the `test` halves and whole corpora at each of the four "rules2" iterations, and of 1.0.0 on whole corpora (21:53); the last one published at 22:22 (`benchmarks/results/real-rules2-comparison-2026-10-25.{md,json}`, `CORPUS_REELS.md` section 12) | rules2 | documents with a strict leak (`tools/corpus`): BODACC 10.1%, BOAMP 39.4%, ParlaMint-FR 7.0%, Europeana 78.9%, HIPE 98.4%, MAPA FR 83.3%; no index |
| 21:42 | independent audit of the tool, scaled plan, full real corpora | sources of that moment | index 61.2% [58.1–66.4]; BODACC 89.4%, BOAMP 55.5%, ParlaMint-FR 93.0%, old press 16.5%, MAPA FR 16.7% (synthetic 91.8%, red team 65.5%) |
| 22:59 | independent review of the engine tuning: in-process evaluation of the `test` halves and whole corpora, engines 1.0.0 and rules2 (not published) | 1.0.0 and rules2 | same figures as published at 22:22 |

The comparison file of 25 October says the `test` halves were "not looked at": their errors were not read, but their
scores were measured at every iteration and published, so they are listed here. After these measurements every trial
must use the **`dev` half only** (`pack-real --split dev` for the tool, `evaluate_real.py --split dev` for the engine
tuning), which a standard campaign refuses; any other pre-campaign measurement of a `test` half is added to this table
and to `spec.TEST_HALVES_MEASURED_BEFORE` before the registration (section 15). **Repeat campaigns**: after the first
published campaign, the `test` halves are no longer blind (their per-family scores are known to whoever edits the
rules). A later campaign on the same halves says so: it lists the earlier campaigns in `spec.EARLIER_CAMPAIGNS` (a new
dated protocol version), which every result copies, and the merge into the site refuses a repeat campaign that omits
the published one. For a later engine version, the headline index must move to fresh data built with the same tools
over a period never measured (for example BODACC and BOAMP notices published after the engine freeze); the "unseen"
BODACC August 2026 and BOAMP 2021 sets (`CORPUS_REELS.md`, section 12) were already measured on 25 October and are no
longer blind either. Synthetic: fresh seeds; the development seed 20261024 (the 540-document evaluation used to tune
the engine) is **refused by the code**. Stated limit: the weakness analysis of 25 October (`CORPUS_REELS.md`, section
7) covered whole corpora and the measurements above saw the `test` halves, so these are not blind to the *kinds* of
errors (entrepreneurs' RCS numbers, particle names, BOAMP addresses…); between the two trials BODACC went from 8.0% to
89.4% after a rule change, and the `test` scores were visible at every rules2 iteration. They are blind to the
values: no name or number of a real corpus may enter the engine, whose code is public.

**4. What a direct identifier is.** Synthetic and red team: the gold labels of type `DIRECT` (`tools/eval/schema.py`):
PERSON, EMAIL, PHONE, ADDRESS, NIR, IBAN, RIB, RIB_SPLIT, CARD, SIRET and SIREN (sole traders only), VAT, TAX_ID,
PASSPORT, ID_CARD, PLATE, RPPS, CAF, FRANCE_TRAVAIL, IP; quasi-identifiers (BIRTH_DATE, LOCATION, ORG, ID for customer,
patient or staff numbers) and decoys do not count. Real corpora: the personal families of `tools/corpus` except the
birth date: PERSON, ADDRESS, EMAIL, PHONE, NATIONAL_ID, TAX_ID, IBAN, BANK_ACCOUNT, CARD, ID, URL, IP. Present: BODACC
PERSON, ADDRESS, ID (RCS/RM number, i.e. an individual entrepreneur's SIREN); BOAMP PERSON, ADDRESS, EMAIL, PHONE
(whoever owns them, often a public body: the engine cannot know); ParlaMint PERSON; old press PERSON; MAPA FR PERSON,
ADDRESS. Kept by policy, outside the computation: ORG, ORG_ID, LOCATION, DATE, OTHER. A mention counts only if it
holds at least one alphanumeric character.

**5. Leak, index, interval.** *Readable*: an alphanumeric character of the input that is still present, at its place,
in the service's output. The service returns no offsets: the tool aligns the output with the input (`[LABEL_N]`
placeholders, invisible characters the output strips). When a text segment between two placeholders fits at several
places, every character that **may** be visible counts as visible (conservative bound). Checked in process on 48,955
distinct documents (the development evaluation and its 6,192 mutations, 20,000 fresh synthetic, 13,745 mutated, the
8,478 real documents): rebuilt zones equal to the engine's on every synthetic document, the conservative bound never
missed a truly visible character, and only 3 real documents (BODACC 1, BOAMP 2; 10 characters in all) where it counts
characters that were in fact masked as visible. *Leak*: a document leaks as soon as **one** alphanumeric character of **one** gold
direct-identifier mention stays readable (the last digit of a phone number is enough). *Failures*: a document the
service refuses or fails on (any HTTP error after retries), or whose output cannot be aligned, counts as a **leak**
with all its direct mentions unmasked. *Documents without a direct mention*: left out of the index (they would
inflate it), counted and published. *Formulas*: for each family *f*, *P_f* = documents without leak / documents with at
least one direct mention; **index = (1/7) · Σ_f P_f** over the seven families whatever their size (a million synthetic
documents weigh as much as the 6 scored MAPA FR documents of the test half); **mention recall = (1/7) · Σ_f (fully
masked direct mentions / direct mentions)**; no index without all seven families. *95% interval*: stratified
bootstrap over **documents** (within each family, as many documents as it holds are drawn with replacement), 2,000
resamples, seed 20261025, 2.5 and 97.5 percentiles. The draw uses the histogram of per-document outcomes (direct
mentions, masked mentions): the count drawn in each cell follows exactly a multinomial law, drawn by successive
binomials, the same law as drawing documents one by one without a million-entry array (`tools/protocol/stats.py`,
equivalence test in `tests/protocol/test_stats.py`). Same method for the mention-recall interval. *What the interval
does not cover*: it measures document sampling only, not gold errors (item 2), not the choice of the seven families,
not the dependence between mutated documents (the ~46 variants of one base document are resampled as if
independent, which makes the red-team family's interval too narrow). One MAPA FR document (6 scored) moves the index
by 1/6 × 1/7 ≈ 2.38 points: MAPA FR alone makes most of the interval's width (about 95% of its variance in the
trials).

**6. Other published figures.** Per family: no-leak share (Wilson interval), mention recall, recall per identifier
type, service errors, ambiguous alignments. Synthetic families (`tools/eval` definitions): character recall (direct,
structured, all), precision (masked characters falling on gold personal data), over-masking of neutral text, decoys
wrongly masked, `tools/eval` leak rates (strict, structured, literal), entity recall. Real corpora (`tools/corpus`
definitions, test half, dev half and all documents): strict and 80% mention recall, character recall, precision with
a bootstrap interval (not measurable on ParlaMint), over-masking, leaking documents (strict and literal), kept
families touched. Red team per operator: no-leak share, mention recall, **survival** (mentions masked without the
mutation that stay masked with it). Per seed: no-leak share (stability). Out of scope, in a section of the results of
its own, never mixed with the French scope, and Judilibre control: item 2. History: the `test`-half measurements taken
before the campaign and the earlier campaigns (item 3). Disclosed departures: every allowed departure from the
procedure (swap active, service redeployed after the campaign ended), written by `run-protocol.sh` into the checkpoint
and the results and recalled by the merge into the site. Campaign: documents, throughput, time yielded to visitors, retries, errors, engine fingerprint (service image,
version, packs, outputs on the probe) and number of engine checks, whether the local token was accepted, plan
fingerprint, SHA-256 fingerprints of the synthetic, mutated and real documents sent. Registration: the tool's digests
(`tools/` files, `spec.py`, this text, bundle, Faker) and the comparison of what was sent (documents, digests) with the
count registered in `spec.py` (section 15). Files: `benchmarks/results/protocol-<date>.json` and `.md` (1.0); from
1.1 on, `protocol-<version>-<date>.json` and `.md` (`spec.RESULTS_STEM`), never overwritten; the site receives ten
keys (item 10).

**7. Guards: the index alone could lie.** An engine that masked everything would score 100%. The index is published
only if, on the same campaign, neutral-text over-masking on the synthetic families is ≤ 2% (0.08% on 25 October),
decoys wrongly masked on the synthetic family are ≤ 10% (3.5%), and character precision on BODACC and BOAMP (test
halves) is ≥ 70% each (90.1% and 80.9% on all documents on 25 October). Otherwise the merge script refuses; forcing it
(`--force-guards`) must be disclosed publicly. Precision and over-masking are always published next to the index.

**8. What could make the index look better than reality, and what the protocol does.** Tuning rules on the measured
documents: index on the `test` halves, fresh seeds, development seed refused by the code, `dev` − `test` gap published,
every earlier measurement of the `test` halves listed (item 3) and copied into the results. Repeating the campaign on
`test` halves already seen: earlier campaigns listed in `spec.EARLIER_CAMPAIGNS` and copied into the results, the merge
into the site refused when the published one is missing, fresh data for a later engine. Keeping quiet about a
departure from the procedure: allowed departures (swap, redeploy after the end) written into the results and recalled
by the merge; `--force-guards` must be disclosed.
Easy synthetic data (the same templates the engine was tuned on; values change, layouts do not): synthetic and red
team weigh 2/7 whatever their volume, each family is published. Volume: equal weights. Masking everything: guards;
precision, over-masking and decoys published next to it. Dropping hard documents or failures: an error or an
unalignable output counts as a leak; documents without gold are counted and published. A lenient leak definition:
strict, one visible alphanumeric character is enough. A convenient alignment: conservative bound. Stopping when the
number looks good, keeping the best run: sizes fixed here, the campaign runs to its end, no final report on an
incomplete campaign, a completed campaign is never run again in the same folder, every campaign published and dated
(an abandoned one keeps a partial report, to be disclosed). Changing the engine mid-campaign: one campaign = one
engine; service image, version, packs and outputs on a fixed probe are checked at start, at every checkpoint, after
any failure or restart and at the end; a difference stops everything without writing anything after the last passing
check, and `finish` checks the image again. Editing the definitions afterwards: digests of `spec.py`, of this text and
of the bundle published before the launch and copied into the results, recomputed from the bundle's contents at every
start (a bundle edited after its build is refused); the plan count compared with the registered one, the merge into
the site refused otherwise; resume refused if the tool changes. Service overload counted as leaks
(or the reverse): `429`/`503` beyond 30 minutes for one document pauses the campaign, never a leak, and the merge
refuses a campaign where such an error was counted. A campaign run without the local token (traffic counted as
public): `/health/deep` probe at start, a standard campaign is refused without an accepted token, and so is the
merge.
Picking the country or profile that suits: the product defaults (FR, `standard`, French placeholders). Incomplete gold
(ParlaMint, bare names not annotated): it **favours** the index, since an unannotated name is not counted as a leak;
stated here, and the family weighs one seventh. Gold errors (BOAMP 2.1%): they cut both ways; measured rates
published. Learning the values of public corpora (name lists): `test` halves never used; the engine is public, so any
list taken from a corpus would show.

**9. The campaign on the production server.** *Tool*: `tools/protocol/`, Python's standard library plus Faker (MIT,
pure Python), shipped as a reproducible self-contained bundle (`gg-protocol.pyz`, which also carries this text), run
in a **throwaway container of the running service's exact image** (same Python 3.12): no network, read-only root, user
10001, no capability, 2 GB of memory without swap, no core file (`--ulimit core=0`: the tool's memory holds the real
corpora), one CPU at low weight (`--cpu-shares 256`), service socket mounted read-only; the local token arrives on
standard input from its root 0600 file, never as an argument nor on disk (`tools/protocol/server/run-protocol.sh`). At
start the tool recomputes the bundle's digests from its contents and refuses a bundle edited after its build.
*Refusals at start, before any request*: a standard campaign (registered seeds and sizes) is refused without the
service image, with unit sizes other than the registered ones (the plan fingerprints depend on them), with a trial
flag (`--allow-disk-real`, fixed probe), or with a real-corpus pack reduced to the `dev` half or missing one of the
fifteen corpora (the index would otherwise be missing after hours of work). *Local token checked*: at start the tool queries `/health/deep`, which
exists for the LOCAL principal only; without an accepted token a standard campaign is refused (a trial goes on,
flagged as public traffic). *Requests*: `POST /v1/anonymize/text` on the service's Unix socket, **without**
`X-GG-Client` and **with** the local token `X-GG-Local`: the LOCAL principal, outside per-client budgets, two jobs at
once at most, never the slot reserved for small requests. Each document sends one usage datagram with
`"src":"protocol"`: **the whole campaign counts in the site's public statistics, as protocol** (engine probes
included). Options: `countries` FR (or the out-of-scope corpus' country), `profile` `standard`, `label_language` `fr`.
*One campaign = one engine*: the engine fingerprint is the service container's image (`docker inspect`, passed by
`run-protocol.sh`), version, pack catalogue and the SHA-256 of the service's **outputs** on a fixed probe (200
development-seed documents, never scored). It is checked at start, before every checkpoint (every 60 seconds), after
any connection failure or service restart (`/status` counters going down) and at the end. A suspected restart drops
the units in progress (redone later) and holds new ones until the check; a unit counts only after a `/status`
reading without restart taken after it finished. A difference stops the campaign without writing anything after the
last passing check; resuming requires the same engine; `finish` checks again that the service image is the one of
the start. Cost: 200 requests per minute of campaign (about 1.5% of the requests; one probe takes about 2 seconds
under WSL), served before the worker threads. *Visitors first*: the service's scheduler
serves a waiting visitor before the campaign's next job; on top of that the tool reads `/status` every 2 seconds and
keeps only one request in flight while anyone else holds or waits for a slot; `429` and `503` are honoured
(`Retry-After`, jitter); past 30 minutes of waiting for one document the campaign **pauses** (an overload never counts
as a leak). Measured under WSL with four visitors sending 20 KB texts non-stop: 95% of answers within 27 ms alone,
within 57 ms during the campaign (no refusal); the campaign yielded 24 seconds out of a minute. *Concurrency*: three
threads (two running at the service, one queued). *Resume*: replayable units (1,500 synthetic documents, 30 red-team
bases, 100 real documents); atomic and durable checkpoint (the previous one is copied, `fsync`, fallback to the copy
when the last one is unreadable; aggregates only); `stop` or SIGTERM pauses, `start` resumes; resume refused if the
engine, the tool, the plan or the real corpora changed, so the service must not be redeployed during a campaign. A
scoring error on one document counts as a leak (`exception:<type>`); a tool error outside a document stops the
campaign with its type, never silently. A completed campaign is never run again: `finish` archives its work folder
(`/var/lib/gg-protocol-<date>-<plan>`). On an incomplete campaign `finish` wipes nothing (the real-corpus pack stays
in RAM while its units are not done) and `start` resumes it; it is abandoned with `GG_PROTOCOL_ABANDON=1 bash
run-protocol.sh finish`, which keeps a partial report to be disclosed. *Allowed departures, written down*:
`GG_PROTOCOL_ALLOW_SWAP=1` (swap active anyway) and `GG_PROTOCOL_REDEPLOYED_AFTER=1` (service redeployed after the
campaign ended, before `finish`) only pass by leaving a trace: `run-protocol.sh` writes them (`--disclose`) into the
checkpoint and the results, and the merge into the site recalls them; they are disclosed with the index. *Scores
only*: the tool never writes nor prints
a text, an annotated value or a service output; checkpoints and results hold counters, bits (one per document) and
fingerprints. *Real corpora in RAM only*: the pack is copied to `/dev/shm` (tmpfs), the tool refuses a pack outside
RAM-backed storage, and `run-protocol.sh` refuses to work while a swap is active (a tmpfs page could reach the disk;
`sudo swapoff -a` for the campaign). Real corpora go first (a few minutes); as soon as their units are saved **the tool
wipes the pack**, drops it from memory and records the wipe in the checkpoint at once; `finish` of a completed or
abandoned campaign also empties `/dev/shm/gg-protocol`. BODACC and BOAMP are rebuilt from their source on the campaign
day when possible (DILA deletion requests), and the local pack is deleted after the copy. *Duration*: measured under
WSL (16 cores, local service in public mode, local token, two LOCAL slots, tool in a throwaway container): 215 to 225
synthetic documents per second, 2.4 ms of client CPU per document; the 8,478 real documents in about 4 minutes, 3 of
them for the out-of-scope corpora (the DE, ES, IT, NL, PT engines are not preloaded: about 0.3 s per request). The
full plan (1,019,385 documents) thus takes about 1 h 20 on such a machine. **On the server the duration is not
measured**: before the campaign, a timed trial (`dev`-half pack, plan scaled with `GG_PROTOCOL_ARGS`, item 10) gives
the throughput, hence the full plan's duration; the campaign must end before the server maintenance (01:45 Paris time), otherwise
`GG_PROTOCOL_HOURS` pauses it cleanly (for example after 3 hours) and `start` resumes it later.

**10. Replay.** The commands of section 10 above, from the repository root (Python 3.12+), `DIR` outside the
repository; `IMAGE` is the service container's image (`docker inspect -f '{{.Image}}' <container>`); a service is
started as in `deploy/README.md` (public mode, `GDPRGUARDIAN_LOCAL_TOKEN_SHA256`). A **trial**, never published, uses a
scaled plan (`--synthetic-docs`, `--redteam-bases`…) and a pack of the `dev` half only (`pack-real --split dev`), so the
`test` halves are no longer touched. **On the server, in order** (`docs/PUBLISHING.md` details the copies): freeze and
deploy the engine; redo the cross-check on that engine (item 11); build the bundle, `registration --bundle`, publish
those digests; `bash run-protocol.sh prepare` (refused while a swap is active: `sudo swapoff -a`); **timed trial** with
a `--split dev` pack and `GG_PROTOCOL_ARGS="--synthetic-docs 3000 --redteam-bases 30"`, then `status` (throughput) and
`finish` (results kept apart in `results/trial-<date>/`, never published); then `prepare` again, the full pack in
`/dev/shm/gg-protocol/`, `GG_PROTOCOL_HOURS=3 bash run-protocol.sh start`, `status` until the end, `finish`, and the
merge into the site. Expected plan fingerprints (Faker 40.43.0), also registered in
`spec.REGISTERED_PLAN` and compared by the tool: 450,000 synthetic documents, 12,000 bases, 548,907 mutated documents;
synthetic SHA-256 `0b91be78435e5434ee5a3b136ab8f08dd10a2c3673dad56fc6dca469c87a955b`, red team
`d984ee1bf9dba70bf2ccf32957cab9da9bbf1fdf02adf5b7444956fa0137760b`. BODACC and BOAMP come from a live API: their
fingerprints, published in the results, may change between downloads. Site keys (`site/data/quality.json`):
`confidence_index`, `confidence_ci_low`, `confidence_ci_high`, `mention_recall_pct` (percent, one decimal),
`protocol_docs` (documents sent by the campaign, engine probes excluded), `protocol_families` (7), `real_corpora` and
`real_docs` (annotated real corpora and their documents, without the Judilibre control), `protocol_date` (ISO date of
the campaign), `protocol_engine` (service version and the first 12 characters of its image, for example
`1.0.0+af877bdf62ae`: two engines of the same version stay distinct). Until a complete campaign has run they hold "—"
and the site shows "not measured yet".

**11. Cross-check of the tool (done before the campaign, redone on the frozen engine).** *Method*: the development
synthetic evaluation (540 documents and 6,192 mutated, seed 20261024) goes through a local service in public mode with
a local token (Unix socket); the tool rebuilds the masked zones from the output alone and the `tools/eval` functions
score them. Every number of the summary (8,535 leaves for the mutated set) is compared with the **in-process
evaluation of the same engine** (one frozen copy of the sources, loaded by the service and by the evaluation) and with
the repository's reference file (`tools/protocol/crosscheck.py`, commands `crosscheck` then `crosscheck-summary`). The
tool is validated when, on the same engine, the ten headline indicators are identical, no document fails and every
other difference is a boundary effect: the boundary between two placeholders separated by a space cannot be read from
the output, which only touches the figures per *system* label (confusion, per-label precision and F2, typed rate,
strict entity rate), never what is masked. A difference from the reference file on which the service and the
in-process evaluation agree comes from the engine, changed since the reference (or, for interval bounds, from the
random draws). *Results*: on 25 October 2026 at 20:47 UTC, engine before rules2, the service's ten indicators equalled
those of `eval-2026-10-25-standard.json` bit for bit (direct recall 99.18%, precision 98.82%, strict leak 9.07%…); that
day's "same engine" part loaded a copy taken mid-edit (2 documents failed on both sides) and is superseded
(`benchmarks/results/protocol-crosscheck-2026-10-25.md`, kept for the record). On 26 October 2026 at 00:04 UTC, frozen
copy of the rules2 engine sources (tree digest `a992428d25533cc6`, pure-Python engine because the installed native core
did not run these sources; probe digest `eeb38986e44c`, the one a campaign records for an engine with the same
outputs): **tool validated** for countries `auto` and `FR`; ten identical indicators between the service and the
in-process evaluation (direct recall 99.23%, precision 98.82%, strict leak 8.33%), no failure; 12 of 773 leaves (base)
and 31 of 8,535 (mutated) differ, all by the boundary effect. Against `eval-2026-10-25-standard-fr-rules2.json`
(countries `FR`) the ten indicators are identical; the 10 differing mutated leaves come from the engine, edited since
that reference. Details: `benchmarks/results/protocol-crosscheck-2026-10-26.md`. The engine was still being tuned during
this check: it is **redone on the frozen engine** before the registration, and its probe digest must
equal the campaign's.

**12. Known limits and biases.** Synthetic data: templates known to the engine; the red team covers 51 operators
only. Gold: BOAMP 2.1% measured errors; ParlaMint partial (favourable); titles inside HIPE names (unfavourable); MAPA FR
tiny (6 scored documents in the test half: one document moves the index by 2.38 points). Real weight: the campaign
sends over a million documents, but five sevenths of the index rest on the 3,164 scored documents of the real `test`
halves. The interval covers document sampling only: not gold errors, not the choice of families, not the dependence
between mutated variants of one document (item 5). The `test` halves were measured before the campaign (item 3): by
the engine tuning before the rule changes (20:21 UTC) and at every rules2 iteration (21:36 to 22:20, published at
22:22), by two tool trials, by the tool's audit and by the review of the engine tuning. Their errors were not read, but
their scores were visible during tuning: unintended tuning on these scores cannot be ruled out; the published `dev` −
`test` gap measures it. After the first published campaign the `test` halves are no longer blind: a repeat campaign
says so (item 3), and a later engine needs fresh data. Rules adjusted on the `dev` halves from 25 October
2026 until the engine freeze; weakness analysis done on whole corpora. Direct identifiers only: re-identification
through context
(role, place, rare event) is not measured. Text route only: PDF, Word and Excel conversion is not measured (no office
gold). BODACC and BOAMP layouts rebuilt by us; HTML entities not decoded in BOAMP. The real corpora hold public data of
real people: they leave the measuring machine only for the server's RAM, are never committed nor republished, and are
wiped after use. The server keeps serving visitors during the campaign: throughput depends on it, scores do not.

**13. Files.** See the table of section 13 above.

## 15. Enregistrement / Registration

**FR.** Ce texte ne peut pas contenir sa propre empreinte : l'enregistrement se fait donc **hors du texte**, avant le
lancement. Une fois le moteur gelé et le paquet construit, `python -m tools.protocol registration --bundle
gg-protocol.pyz` donne les empreintes à publier : `spec_sha256` (`tools/protocol/spec.py`), `protocole_md_sha256` (ce
texte), `tools_sha256` (tous les fichiers `tools/` du paquet), `bundle_sha256` (le paquet lui-même), la version de
Faker et le décompte enregistré du plan (`spec.REGISTERED_PLAN`) ; elles sont publiées (dépôt, puis étiquette de
version à son ouverture) **avant** le premier document envoyé. Chaque campagne recopie ces empreintes dans son point
de reprise (une reprise avec un autre outil est refusée) et dans ses résultats (`registration`), avec la comparaison
du décompte réellement envoyé au décompte enregistré : documents par famille, empreintes SHA-256 des documents
synthétiques et mutés, Faker. Le report vers le site refuse une campagne standard dont le décompte diffère. Chacun
peut vérifier que les empreintes d'un résultat sont celles publiées avant son lancement. Elles sont recalculées depuis
le contenu du paquet (jamais lues dans son manifeste) : un paquet modifié après sa construction est refusé. `spec.py`
porte aussi les mesures antérieures des moitiés `test` et les campagnes antérieures (section 3) : toute mesure ou
campagne nouvelle change `spec_sha256` et demande un nouvel enregistrement, avant le lancement.

**EN.** This text cannot hold its own digest, so registration happens **outside the text**, before the launch. Once
the engine is frozen and the bundle built, `python -m tools.protocol registration --bundle gg-protocol.pyz` gives the
digests to publish: `spec_sha256` (`tools/protocol/spec.py`), `protocole_md_sha256` (this text), `tools_sha256` (every
`tools/` file of the bundle), `bundle_sha256` (the bundle itself), the Faker version and the registered plan count
(`spec.REGISTERED_PLAN`); they are published (repository, then a version tag when it opens) **before** the first
document is sent. Every campaign copies these digests into its checkpoint (resuming with another tool is refused) and
into its results (`registration`), with the comparison of the count actually sent against the registered one:
documents per family, SHA-256 digests of the synthetic and mutated documents, Faker. The merge into the site refuses
a standard campaign whose count differs. Anyone can check that a result's digests are the ones published before its
launch. They are recomputed from the bundle's contents (never read from its manifest): a bundle edited after its build
is refused. `spec.py` also carries the earlier measurements of the `test` halves and the earlier campaigns (item 3):
any new measurement or campaign changes `spec_sha256` and calls for a new registration, before the launch.
