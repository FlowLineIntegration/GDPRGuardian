# Cartographie des règles de Gardien RGPD

Gardien RGPD est une **première barrière** : automatique, déterministe, mesurée et explicable. Elle retire les
données personnelles d'un document avant son passage dans une IA, sans promettre l'impossible : aucune
détection automatique n'est exhaustive. Chaque masquage s'explique (quelle règle, pour quelle raison), et
chaque organisation peut ajouter ses propres règles.

> **EN.** GDPR Guardian is a *first barrier*: automatic, deterministic, measured and explainable. Every masked
> value can be explained (which rule, why), and every organisation can add its own rules. The layers below
> run in this order; `explain=true` reports the rule and the reason behind each placeholder, never the value.

## 1. Les couches, dans l'ordre

| # | Couche | Exemples | Masqué quand |
|---|---|---|---|
| 0 | Normalisation | caractères invisibles, homoglyphes, chiffres pleine chasse, césure PDF, gras Markdown, blancs entre les groupes d'un identifiant (règle GAP : tabulation, blancs doublés, saut de ligne entre deux chiffres), saut de ligne à l'intérieur d'un identifiant (règle BREAK : courriel coupé recollé, « jean.du⏎pont@exemple.fr », quand le morceau de gauche commence par une lettre (un numéro en fin de ligne, « 06 12 34 56 78⏎jean@… », n'est jamais collé au courriel) ; IBAN collé recollé si sa clé n'est pas déjà juste ; deux groupes en majuscules et chiffres, chacun avec un chiffre, « 47CY⏎74524 », lus comme séparés par une espace ; jamais deux lignes ordinaires), lettres espacées d'un PDF copié (« J e a n   D u p o n t », « 0 6   1 2 » : seuls les lettres et chiffres comptent, au moins quatre par bloc, ou trois pour un mot capitalisé, « Z o é » ; une minuscule suivie d'une majuscule coupe la suite ; « 4 à 6 » (chiffre, à, chiffre) n'est jamais recollé ; « il y a l' », « 4 B Rue » restent tels quels), groupes séparés par « / » (4 et plus) ou « . » (5 et plus) lus comme des espaces (« 06/12/34/56/78 » ; une date ou une IPv4 reste intacte) ; adresses électroniques déguisées : `[at]`, `(at)`, « arobase », `&#64;`, `%40`, et « @ » suivi d'un domaine en `[dot]` / `(point)` (`EMAIL_OBFUSCATED`, `EMAIL_OBFUSCATED_DOT`) | toujours appliquée au texte de détection (le texte rendu reste intact, une seule table de positions ramène chaque balise au texte d'origine) |
| 1 | Identifiants officiels à clé | NIR, IBAN, carte bancaire, SIRET, numéro fiscal, RIB | la clé de contrôle est valide, **sans mot-clé** ; clé fausse : masqué si un mot-clé explicite l'accompagne (faute de frappe, OCR) ou si le format imprimé est caractéristique |
| 2 | Identifiants à clé faible | SIREN, IMEI | la clé est valide **et** un mot-clé est proche ; depuis 1.0.2, un téléphone compact conforme au plan de numérotation (« 0317495060 ») est masqué sans mot-clé (§ 2, filtre fort) |
| 3 | Identifiants sans clé | passeport, carte d'identité, permis, n° client, matricule, RPPS, IPP, date de naissance | un mot-clé est proche (« Passeport : », « né le », « N° client ») ; les groupes peuvent être regroupés librement, séparés par une espace, un point, un tiret, un tiret demi-cadratin ou « / » (« 42067 58727 49 », « 1044/37321/76 », téléphone « 0764 945 16 3 » près d'un mot de téléphone, mobile 06/07 seul ; carte bancaire, RIB, SIRET, numéro fiscal et TVA aussi, avec leur clé) : la valeur est alors toute la suite de groupes, jamais un morceau d'un numéro plus long (borne `group`), ou un libellé explicite juste avant la valeur (« RPPS 10001234567 », « matricule 004587 », « contrat n° 2024-778899 », groupes espacés compris : « police n° 778 899 120 ») ; une date d'événement placée entre « né le » et la date (« hospitalisé le », « ordonné le », « signé le »…) en fait une autre date, de même qu'un mot d'événement collé devant la date quand « né le » la suit (« hospitalisée le 14/09/2026, née le 12/03/1985 ») |
| 4 | Étiquettes de formulaire | `Nom :`, `Prénom :`, `Nom de naissance :`, `Adresse :`, `Date de naissance :`, `Tél :`, `Code banque :`, `Code guichet :`, `N° de compte :`, `Clé RIB :` | la valeur qui suit sur la ligne, même en minuscules, même inconnue des listes ; `Adresse :` en début de ligne : toute la valeur (service, bâtiment, voie, boîte, code postal, commune), sauf une valeur sans chiffre ou qui commence par un code postal ; la valeur s'arrête à « ; » et à une fin de phrase après la commune (« 12000 Rodez. Le dossier… »), le reste de la ligne revient aux autres détecteurs ; une ligne qui porte un autre champ sans fin de phrase avant lui garde l'ancien comportement (`FR_ADDRESS_FIELD`) ; `Tél :` en début de ligne : formes libres (« (+33) -05-65-75-80-00 »), à condition que la valeur ait les chiffres d'un seul numéro (« (+ » : 8 à 15 chiffres, forme libre des avis, outre-mer mal formé compris ; sinon « 0 » : 10 chiffres, « 00 » : 11 à 15, « 33 » : 10 à 13, autre : 9 à 13) ; deux numéros sur la ligne ou des chiffres de la ligne suivante reviennent aux détecteurs ordinaires (`FR_PHONE_FIELD`, validateur `fr.phone_field`) |
| 5 | Heuristiques de langue | noms (fichiers Insee + civilité, salutation, rôle, signature), adresses (code postal + commune vérifiés), organisations (formes juridiques) | l'indice ou la structure est présent |
| 6 | Structure du document | en-tête de colonne (tableau Markdown, CSV ou TSV, Excel), propagation des noms et des valeurs (§ 2, filtre fort 1.0.2), coréférence | tout identifiant trouvé une fois est masqué partout, sous toutes ses graphies ; « M. Dupont » et « Jean Dupont » partagent la même balise |
| 7 | Règles de l'organisation | masquer, conserver, termes imposés, termes permis | voir § 3 |
| 8 | Sortie | nettoyage (caractères invisibles, images distantes), rapport `explain` | toujours |

Mots-clés, fenêtres et motifs vivent dans des **packs pays** déclaratifs (`src/gdprguardian/packs/data/*.toml`) :
FR par défaut, BE, LU, CH, MC, DE, ES, IT, NL, PT, et INTL toujours actif. Le pays se choisit explicitement
(`countries="FR"`, `"FR,BE"`) ; `"all"` active tous les packs ; `"auto"` reste expérimental.

## Modes : fort, essentiel, personnalisé (1.0.2)

Un seul réglage choisit ce que le moteur masque : `mode` (bibliothèque `Anonymizer(mode=...)`, API REST et outils MCP
`mode`, ligne de commande `--mode`). Sans réglage, c'est le mode **fort**. Les noms anglais sont acceptés.

| Mode | Nom anglais | Ce qui est masqué |
|---|---|---|
| `fort` (défaut) | `strong` | Tout ce que le moteur sait trouver : le filtre fort de la version 1.0.2, avec tous les codes, les nombres longs, les boîtes fonctionnelles, les pseudonymes « @… », les fragments de téléphone et la propagation des valeurs. Dans le doute, on masque. |
| `essentiel` | `essential` (`basique` et `basic` acceptés) | Le filtre classique : seulement ce qu'un validateur, un format reconnu ou un libellé explicite prouve. Personnes, e-mails personnels, téléphones, adresses postales, dates de naissance, IBAN, cartes (clé de Luhn), numéros nationaux (NIR, CNI, passeport, permis, numéros de santé, SIRET/SIREN/TVA d'un entrepreneur individuel), adresses IP et MAC, plaques et VIN, secrets (mots de passe, clés d'API, jetons : toujours masqués), identifiants annoncés par un libellé personnel (n° client, compte client, matricule, salarié, dossier, ticket, incident, contrat, adhérent, patient, pseudonyme, identifiant, cookie, gabarit…). Les valeurs trouvées sont propagées partout, comme en fort. |
| `personnalise` | `custom` | Le mode fort, moins les catégories listées dans `disable`. |

**Ce qui reste en clair en mode essentiel** : un code lettres + chiffres (`ID_CODE`) ou une suite de 8 chiffres ou plus
(`ID_LONG_NUMBER`) sans libellé personnel juste avant (« Le produit traité est SKU-ALPHA-0042 ») ; une boîte
fonctionnelle (« support@ », « contact@ », « rh@ », « noreply@ »… : le premier élément de la partie locale est un nom de
service) ; un pseudonyme « @awa.m » sans indice (`HANDLE`) ; un fragment de téléphone (`FR_PHONE_FRAGMENT`). Un code
après un libellé personnel sur la même ligne (« Le compte client est CLT-000001-Q », « | Client | CLT-… | », « dossier
INC-… », « gabarit biométrique est BIO-… », trois mots courts au plus entre les deux) reste masqué, comme un code en
forme de plaque (« ZZ-000-ZZ »). Le rapport le dit : `"mode": "essentiel"` et un avertissement qui nomme tout ce qui
reste en clair.

**Catégories de `disable`** (mode personnalisé ; `disable` sans `mode` choisit ce mode ; avec `fort` ou `essentiel`,
la requête est refusée ; un nom inconnu est refusé avec la liste) :

| Catégorie | Nom anglais | Règles et entités couvertes |
|---|---|---|
| `personnes` | `persons` | noms et prénoms (`PERSON` : listes de noms, civilités, signatures, initiales, propagation) |
| `emails` | `emails` | e-mails personnels (`EMAIL`) |
| `boites_fonctionnelles` | `functional_mailboxes` | e-mails de service (support@, contact@, rh@…) |
| `telephones` | `phones` | numéros de téléphone (`PHONE`) ; coupe aussi `fragments` (la fin d'un numéro laissé en clair n'est pas masquée à part) |
| `fragments` | `phone_fragments` | fin d'un numéro déjà masqué après un indice (`FR_PHONE_FRAGMENT`) |
| `adresses` | `addresses` | adresses postales (`ADDRESS`, codes postaux) |
| `dates_naissance` | `birth_dates` | dates de naissance (`BIRTH_DATE`) |
| `iban` | `iban` | IBAN et RIB |
| `cartes` | `cards` | cartes de paiement |
| `numeros_nationaux` | `national_numbers` | NIR, CNI, passeport, permis, titre de séjour, numéros de santé, fiscaux et sociaux, SIRET/SIREN/TVA d'une personne, MRZ |
| `ip` | `ip` | adresses IP et MAC |
| `identifiants_techniques` | `technical_identifiers` | UUID, IMEI, adresses de cryptomonnaie, URL personnelles, identifiants après un libellé personnel |
| `codes` | `codes` | codes lettres + chiffres sans libellé personnel (`ID_CODE`) |
| `nombres_longs` | `long_numbers` | suites de 8 chiffres ou plus sans libellé personnel (`ID_LONG_NUMBER`) |
| `plaques` | `plates` | plaques d'immatriculation et VIN |
| `pseudonymes` | `pseudonyms` | pseudonymes, identifiants de connexion, « @… » |
| `secrets` | `secrets` | mots de passe, clés d'API, jetons, témoins : **jamais coupée** |

`secrets` ne se coupe jamais : `disable` qui la nomme est refusé dans tous les points d'entrée (bibliothèque, ligne de
commande, REST, MCP), car un mot de passe ou une clé divulgués ne sont jamais acceptables. Couper `personnes` est
permis, mais le rapport avertit en toutes lettres que le texte n'est pas anonymisé. Une zone laissée en clair l'est en
entier : une autre règle ne masque pas un morceau de l'IBAN ou du pseudonyme laissé en clair. Exception : les règles
attrape-tout (`codes`, `nombres_longs`) coupées ne protègent jamais l'identifiant validé qu'elles recouvrent (un
passeport, une CNI, un IBAN, un NIR, une carte restent masqués en `essentiel` et quand `codes` est coupé).

**Dans tous les modes** : les règles de l'organisation (§ 3 : masquer, conserver, termes imposés, termes permis)
s'appliquent, et une règle « keep » l'emporte sur tout, propagation comprise. Pour garder lisibles des références de
structure précise en mode fort : `{"label": "SKU", "pattern": "SKU-[0-9]{6}", "action": "keep"}`.

**Rapport et `explain`** : `report.mode`, `report.disable` (noms français), `report.left_in_clear_by_mode` (nombre de
détections laissées en clair, par catégorie, hors mode fort) et un avertissement dans `report.warnings`. Avec
`explain=true`, une ligne par (catégorie, règle) : `{"left_in_clear": "codes", "rule": "ID_CODE", "reason":
"mode_essentiel", "count": 2}`, jamais la valeur.

**Ancien réglage `profile`** (déprécié, toujours accepté) : `strict` = `fort`, `standard` = `essentiel`, `fast` =
`essentiel` (`fast` n'a jamais eu de détection propre ; il coupe toujours le modèle NER optionnel). `strict` garde en
plus ses effets d'avant (identifiants à clé faible sans mot-clé, seuil 0,3, organisations masquées). Un `profile` qui
contredit `mode` est refusé.

**Moteurs** : en mode fort, le moteur Rust fusionné fait tout. Hors du mode fort, la détection passe aussi par le moteur
fusionné, en un appel par document (voie perf, 26/10 ; sauf `personnes` coupée) ; la porte du mode trie ensuite les zones détectées en Python,
puis la finalisation (Rust, ou Python quand `personnes` est coupé) fait le reste : mêmes zones, même texte, même
rapport dans les deux moteurs (`tests/test_modes_102.py`, `tests/test_strong_filter_102_r3_perf.py`). La fenêtre du
libellé (personnel ou commercial, 64 caractères, même ligne) cherche la fin de ligne dans la fenêtre seulement : le
coût reste linéaire sur un texte sans retour à la ligne (60 000 codes en mode essentiel).

**Téléphones coupés** (`disable=["telephones"]`) : les fragments (`FR_PHONE_FRAGMENT`, raison `phone_fragment`) le
sont aussi, dans les deux moteurs ; le contrôle final de sortie ne ré-applique que ce que le mode a masqué, il ne
rend donc pas le fragment. « le numéro finissant par 56 78 » reste lisible comme le numéro lui-même ; en mode fort et
avec toute autre coupure, il est masqué (`[TEL_n]`).

> **EN.** One setting, `mode`: `fort` (strong, the default: everything, the 1.0.2 strong filter), `essentiel`
> (essential; `basique`/`basic` accepted: only what a validator, a recognised format or an explicit label proves;
> codes and long numbers without a personal label, functional mailboxes, "@" handles without a cue and phone fragments
> stay in clear) and `personnalise` (custom: strong minus the categories in `disable`; `disable` alone selects it, and
> is refused with fort or essentiel). The organisation's rules apply in every mode and a keep rule wins over
> everything. The report carries `mode`, `disable`, `left_in_clear_by_mode` and a warning; `explain` adds one line per
> (category, rule) left in clear, never the value. Deprecated `profile`: strict = fort, standard = fast = essentiel.

## 2. Ce que Gardien RGPD conserve volontairement

Code postal et ville seuls, lieu de naissance, employeur et identifiants d'entreprise (une personne morale
n'est pas une donnée personnelle, sauf entrepreneur individuel), numéros de commande ou de facture annoncés comme
tels (« facture FA-2024-00123 », voir « Filtre fort » plus bas), montants, dates ordinaires. Seuls, ils n'identifient personne et l'IA en a besoin pour comprendre le document. Une
organisation qui veut les masquer ajoute une règle (§ 3).

Règles de décision précises (les mêmes en Python et dans le noyau Rust) :

| Cas | Décision | Raison |
|---|---|---|
| SIREN, SIRET, n° RCS ou RM d'une société | conservé | personne morale |
| nom de société collé à une forme juridique de personne morale, avant ou après (« SARL DUPONT », « DUPONT SARL », « SAS Martin » ; 1 ou 2 blancs) | conservé, même si « M. Dupont » est masqué ailleurs dans le texte ; « EI Jean Dupont » reste masqué ; une civilité ou un titre juste avant le nom (« M. », « Mme », « Me », « Maître », « Dr » : « M. Jean Dupont SARL ») et une forme suivie d'un mot capitalisé (« Jean Dupont SARL Lumière » : la forme appartient à « Lumière ») laissent le nom masqué | personne morale (considérant 14 du RGPD) ; l'entrepreneur individuel est une personne |
| même numéro avec « entrepreneur individuel », « EI », « micro-entrepreneur »… n'importe où dans le document | masqué | entrepreneur individuel |
| même numéro avec l'état civil d'une personne physique (« Prénom », « Nom d'usage », « né le », « date de naissance ») à moins de 120 caractères : d'abord sur la ligne du numéro, où une personne morale (« société », « SAS », « SARL », « dénomination », « capital social », « employeur »…) à moins de 80 caractères avant ou 40 après l'emporte ; sinon dans son paragraphe, sans personne morale à ces distances ; jamais au-delà d'une ligne vide | masqué | le numéro désigne une personne (registre BODACC : « n° RCS : … ⏎ Nom : … ⏎ Prénom : … » ; « M. Jean Dupont, né le …, RM … » sous une ligne « Société … SAS ») ; l'employeur d'un bulletin de paie reste une personne morale |
| champ « n° RCS : » ou « n° RM : » en tête de ligne, dans un document dont aucune ligne de 150 caractères au plus ne porte « dénomination », « raison sociale », « forme juridique », « société » ou une forme juridique en capitales (« SARL », « SCP », « SELARL »…) | masqué | l'avis ne nomme aucune personne morale : le numéro est celui d'un entrepreneur individuel (avis BODACC « Dépôt de l'état des créances » sans nom) ; un long paragraphe libre peut citer la société du liquidateur sans compter |
| « 75017 Paris » ou « Lyon (69003) » seul : en tête de ligne, après une étiquette (« Adresse : ») ou dans une phrase sans virgule ni tiret devant lui (« Livraison au 97400 Saint-Denis »), aucune voie à moins de 40 caractères, et aucun mot de domicile avant lui | conservé | code postal et ville seuls |
| code postal et ville après un mot de domicile sur la même ligne et dans la même phrase, à moins de 50 caractères (« domiciliée à 69003 Lyon », « demeurant », « réside à », « habite », « Domicile : », « Lieu de résidence : ») | masqués | lieu de résidence d'une personne ; « Adresse : » seule ne suffit pas (adresses d'organismes des marchés publics) |
| ligne d'adresse : segments séparés par une virgule ou un tiret juste avant le code postal, chacun mené par un numéro (« 22-24 ») ou portant un mot d'adresse (type de voie, BP, CS, Cedex, bâtiment, RD…) | masqués avec le code postal (« Rue des prés, 38000 Grenoble », « BP 8 Cedex 02, 49000 Angers ») ; un segment sans mot d'adresse arrête l'extension (« Jean Martin, rue des prés, … » : le nom n'entre pas dans l'adresse) | adresse complète, voie en minuscules ou sans numéro |
| code postal et ville précédés sur leur ligne d'un segment sans mot d'adresse (« Livré chez un voisin, 33000 Bordeaux ») | code postal et ville masqués | pas seuls : la voie a pu échapper à la détection |
| code postal et ville précédés d'une voie (même à la ligne, même après un tiret), d'une boîte postale (BP, CS, TSA), d'un complément (« Appartement 47, Escalier 1 », « 3e étage », « 1er étage »), ou d'un lieu-dit (« 2 la Testière », « Adresse : La Testière », « Le Bourg » sur la ligne précédente ; jamais un groupe qui finit par une particule, « Livraison au 97400 … », ni une ligne qui nomme une personne, deux mots dont un prénom connu, « Claire Dubois », ou une société, « TESTIVO SAS ») | masqués avec eux | adresse complète ; la personne reste une personne |
| commune en plusieurs mots au-delà de la partie reconnue : particule puis mot capitalisé (« 30660 Gallargues le Monteux », « 93211 SAINT DENIS LA PLAINE CEDEX », « Clichy-La-Garenne ») | masquée entière avec l'adresse | commune entière |
| « 6 rue des Essais, Vouziers » (commune connue sans code postal), aussi après une voie sans numéro reconnue par un indice (« Adresse : Place du Théâtre, Testville », « domiciliée rue du Général Leclerc à Rennes ») et après « à » ou un tiret (« Rue Testa à Jeumont », « Rue Testa - Lyon ») | masqué entier | adresse complète |
| boîte postale seule, en capitales (« BP », « CS », « TSA », « Boîte postale », pas « bp »), de 3 chiffres au moins et pas une année 19xx ou 20xx (« BP 2024 », budget primitif) : 5 chiffres suffisent (« CS61336 », « BP 60120, Contact … ») ; sous 5 chiffres, il faut un code postal (5 chiffres) ou « CEDEX » sur sa ligne ou la suivante | masquée ; « Le compte CS 1500 », « Référence BP123 », « BP 2025 à venir » restent lisibles | adresse postale |
| commune après une préposition de lieu (« à », « vers », « depuis »…) ; après un verbe de lieu (« quitter », « rejoindre », « regagner »…) seulement quand une personne du texte porte ce nom de lieu (« Mme Lyon … quitter Lyon ») ; un prénom ou un nom seul après un verbe de lieu reste masqué (« rejoindre Marie », « quitter Jean ») | conservée | lieu |
| « Saint Quentin », « SAINT GERMAIN » sans trait d'union | jamais une personne seule (comme « Saint-Quentin ») | lieu ou saint |
| le mot qui suit un code postal connu (« 30600 VAUVERT ») | jamais une personne, sauf un prénom connu et un autre nom qui ne commencent pas une commune de ce code (« Matricule 75012 Sophie Martin ») | commune |
| civilité (« M. », « Mme », « Mlle », « Monsieur », « Madame », « Mademoiselle ») puis un nom trouvé, suivi d'un seul mot capitalisé (« Mme Christine Pires Beaune », « M. Matthieu Orphelin », « M. Loïc Prud'homme ») | le mot entre dans la balise, même s'il est aussi un mot courant ou une commune | nom de famille homonyme d'un mot ou d'un lieu (débats parlementaires) |
| « Prénom Le Nom » (« Paul Le Verger »), « De », « Van », « Da », « Di »… capitalisés après un prénom | la particule et le mot qui la suit forment le nom, propagé entier (« Le Verger ») | nom à particule |
| civilité (« M. », « Mme », « Mlle », « Monsieur », « Madame », « Mademoiselle », aussi en minuscules pour les mots entiers), un blanc, puis un seul mot capitalisé que rien ne masque encore (« M. Orphelin », « monsieur Orphelin »), dans un texte où le détecteur de noms français a trouvé une personne | le mot est masqué comme une personne, même s'il est aussi un mot courant ; jamais un article (« M. Le Maire ») ni un titre (« Monsieur Président », « Madame Ministre ») | nom de famille homonyme d'un mot (débats parlementaires) |
| « M'testa », « M’testa » : « M » suivi d'une apostrophe en tête d'une personne | reste dans la zone masquée, jamais retiré comme la civilité « M » | nom à apostrophe |
| forme de société civile professionnelle ou d'exercice libéral (« SCP », « SELARL », « SELAS », « SELAFA », « SELURL », « SELCA », « SCM ») juste avant un nom | le nom de la firme reste lisible en entier, chaque associé compris, quand les noms suivants sont des noms seuls d'un mot (« Durand », « Testa-Testi ») séparés seulement par une virgule, « et », « & » ou un tiret (« SCP Dupont, Martin et Durand », « SELARL Testa & Testi ») ; un prénom et un nom (« SCP Testard et Jean Moulu », « SELARL MJ Testa, Jean Testi, mandataire ») arrêtent la firme et restent masqués, comme tout ce qui suit | personne morale : la firme, pas ses associés ; une personne nommée après la firme reste une personne |
| civilité puis article capitalisé formant un nom connu (« M. Le Verger », « Mme La Fontaine ») | une personne (indice fort de la civilité) ; un rôle (« M. Le Maire ») ou un titre (« M. Le Comte ») ne reçoit pas cet indice et reste jugé comme un nom seul | nom à particule |
| « Bodacc A n° 2026… », « Annexe B 2 » : mot inconnu suivi d'une lettre sans point puis d'un numéro | pas une personne | lettre de série ; « MBAPPA K », « Testarossi P, » restent des noms avec une initiale |
| « AVENANT N° 2 », « Devis », « Bordereau » : types de document homonymes de noms rares | une personne seulement avec un indice (« M. Devis ») ; « N° » n'est jamais une initiale | type de document |
| « Nom commercial : », « Nom de la société : », « Nom de domaine : »… | pas une étiquette de personne | nom d'autre chose |
| valeur d'une étiquette de personne qui porte une forme de société (« … SAS », « S.A.R.L. ») dans sa valeur propre, avant « pour », « de », « chez », une parenthèse, une virgule ou un tiret (« Signataire : Mercier pour Testivo SAS » reste un nom), ou qui commence par un mot d'organisme (« Ville de … », « Syndicat … ») non suivi d'un prénom | pas une personne | organisation |
| « Nom : TESTIX INDUSTRIES » : un mot seul suivi de mots courants capitalisés, sauf s'ils commencent l'étiquette suivante (« Nom : Dupont Prénom : Jean », un à quatre mots puis « : ») | pas une personne | raison sociale |
| dans un document qui a un champ de prénom (« Prénom : », « Prénoms : »), valeur d'un champ d'état civil en début de ligne (« Nom », « Prénom », « Nom d'usage », « Nom de naissance », « Nom marital », « Nom d'épouse », « Pseudonyme ») : 1 à 6 mots jusqu'à la fin de la ligne ou de la colonne (« \| », tabulation), en 80 caractères au plus, sans autre « : » sur la ligne, sans chiffre ni « @ », hors cellule vide (« Non précisé ») | toute la valeur masquée, quels que soient sa casse et ses mots (« Nom : PANTALON », « Prénom : Chantal, sylvie, lily-rose »), civilité en tête et « (EI) », « EI », « - ENTREPRENEUR INDIVIDUEL » en queue exclus ; la valeur est propagée (sa copie dans « Nom commercial : » est masquée), une valeur en capitales aussi en casse de titre (« TESTAGAR » puis « Nom commercial : Testagar Livraisons »), mais seulement si un de ses mots au moins (particules à part) n'est ni un mot courant, ni une commune, ni un nom ambigu : « Nom : LYON », « ROUGE », « LOI », « BOULANGER », « LA POSTE » sont masqués dans le champ seul, jamais dans « RCS Lyon » ni « Croix-Rouge » ; une valeur déjà trouvée aux mêmes bornes (« Nom : dupont jean ») garde sa zone et son choix de propagation ; une valeur d'organisation (ligne précédente) reste lisible | état civil d'une personne physique (avis BODACC) |
| pièces jointes d'un courriel ou d'un PDF | listées par numéro et type (« Pièce jointe 1 (application/pdf) »), jamais par nom | le nom d'un fichier porte souvent celui d'une personne |

> **EN.** Kept on purpose: postcode and town alone, birthplace, employer and company identifiers, order numbers,
> amounts, ordinary dates. Precise decision rules, identical in Python and in the Rust core: a company number
> (SIREN, SIRET, RCS, RM) is masked when a sole-trader mention appears anywhere in the document, or when a natural
> person's civil status ("Prénom", "né le", birth date) is within 120 characters: first on the number's line, where
> a legal entity ("société", "SAS", "dénomination", "capital social", "employeur"…) within 80 characters before or
> 40 after wins; otherwise in its paragraph, with no legal entity at those distances; never past a blank line. A
> postcode and town are masked with a street (even on the next line or after a dash), a postal box, a home word on
> their line and in their sentence ("domiciliée à 69003 Lyon", "Domicile :"; "Adresse :" alone is not one), or a
> named place ("2 la Testière", "Adresse : La Testière", "Le Bourg" on the previous line; never a group ending with
> a particle, as in "Livraison au 97400 …", nor a line naming a person, two words with a known given name, or a
> company with a legal form), or with comma- or dash-separated chunks led by a number or holding an address word
> (street type, BP, CS, Cedex, building, RD…: "Rue des prés, 38000 Grenoble"; a chunk without one stops the
> extension); when any other chunk precedes them on their line, only the postcode and town are masked; otherwise a
> postcode and town alone are kept. A multi-word town is masked whole past its recognised part ("Gallargues le
> Monteux", "SAINT DENIS LA PLAINE CEDEX"); "6 rue des Essais, Vouziers" is masked whole. Hyphenless "Saint
> Quentin" is never a person; the word after a known postcode is never a person, unless a known given name and
> another name follow that do not start one of the postcode's towns ("Matricule 75012 Sophie Martin"). In "Paul Le
> Verger" the capitalised particle and the next word form the surname, propagated whole; after an honorific, a
> capitalised article forming a known name is a surname ("M. Le Verger"), but not a role ("M. Le Maire") nor a title.
> "Bodacc A n° 2026…" (unknown word, dotless letter, then a number) is not a name, while "MBAPPA K" is; "AVENANT N° 2",
> "Devis", "Bordereau" need a cue to be names, and "N°" is never an initial. "Nom commercial :" is not a person
> label; a person-label value carrying a company form in its own phrase (before "pour", "de", "chez", a bracket, a
> comma or a dash), or starting with an organisation word not followed by a given name, or a single word followed
> by capitalised common words that do not start the next label, is not a person. E-mail and PDF attachments are
> listed by number and type, never by file name.

### Filtre fort 1.0.2 : identifiants techniques, codes, identités en ligne, téléphones

Choix du propriétaire : « un filtre fort qui anonymise tous les identifiants avec la même logique que pour les noms,
un peu excessif que l'inverse ». Dans le doute, un jeton qui a la forme d'un identifiant est masqué, sauf exclusion
nommée. Mêmes règles en Python et dans le noyau Rust (motifs des packs `intl.toml` et `fr.toml`, validateurs
jumeaux ; la règle `ID_CODE` tourne en Python dans les deux moteurs). Aucune table de correspondance : la valeur
canonique (IPv6 compressée, MAC en paires, téléphone E.164, date ISO, code en squelette majuscule) ne sert qu'à
donner la même balise aux formes d'une même valeur, dans le seul document traité.

| Règle | Exemples masqués | Balise | Raison | Reste lisible |
|---|---|---|---|---|
| `IPV6` : une suite maximale de groupes hexadécimaux (2 deux-points au moins, zone `%eth0` comprise), validée comme `ipaddress`, avec 3 groupes ou un groupe de 3 caractères | `2a01:e0a:4d43:d2::7639`, `2001:db8:85a3::8a2e:370:7334`, `fe80::1%eth0` | `[IP_n]` | `validated` | `12:30:45`, `std::vector`, `a::b`, une MAC à 6 groupes |
| `MAC` pointée (Cisco), rendue en paires | `001a.2b3c.4d5e` (même balise que `00:1A:2B:3C:4D:5E`) | `[MAC_n]` | `validated` | groupes tout en chiffres (`1234.5678.9012`) |
| `UUID` (8-4-4-4-12 hexadécimal) | `550e8400-e29b-41d4-a716-446655440000` | `[IDENTIFIANT_n]` | `format` | — |
| `SECRET_SESSION` : témoin ou jeton nommé (`PHPSESSID`, `JSESSIONID`, `sid`, `session_id`, `csrf`, `_ga`, `_gid`, `_fbp`, `auth_token`, `access_token`, `refresh_token`…), `=` ou `:`, valeur de 8 caractères ou plus avec une lettre et un chiffre | `sid=a8f5f167f44f…`, `PHPSESSID=9b2c7d1e4f5a6b8c` | `[SECRET_n]` | `keyword` | « session de formation », « Session : printemps » |
| `SECRET_COOKIE` : sur une ligne `Cookie:` ou `Set-Cookie:`, chaque valeur `nom=valeur` de 8 caractères ou plus | `Cookie: prefs=Zq81Lm2nPx` | `[SECRET_n]` | `keyword` | valeurs courtes (`lang=fr`), attributs (`Path`, `Expires`, `Max-Age`, `Domain`, `SameSite`…) |
| `SECRET_API_KEY`, `SECRET_BASIC_AUTH` : `X-Api-Key`, `api_key`, `clé API`, `access_key`, `client_secret`, `secret_key`, `private_token` puis 16 caractères ou plus ; `Authorization: Basic …` | `X-Api-Key: 0123…cdef` | `[SECRET_n]` | `keyword` | — |
| `ID_BIOMETRIC` : `voiceprint_id`, « empreinte vocale / digitale / biométrique », « gabarit biométrique / vocal », `bio_id`, `face_id`, « référence biométrique », puis une valeur qui porte un chiffre | `voiceprint_id=vp_29dded3w6o`, « gabarit biométrique BIO-184665 » | `[IDENTIFIANT_n]` | `keyword` | « empreinte digitale pour ouvrir » |
| `ID_CODE` : jeton `[A-Za-z0-9]+([-_/.][A-Za-z0-9]+)*` (un point suivi d'un mot capitalisé le coupe), jamais collé à un mot ni à « @ », avec une lettre ASCII, un chiffre et 6 caractères alphanumériques, **quel que soit son préfixe ou le mot qui le précède** (factures, commandes, devis, livraisons, produits, lots et SKU compris : choix du propriétaire, « on anonymise tout code, tant pis ») ; dans un chemin qui porte un nom de domaine (un « . » et un « / »), chaque segment est jugé seul : le domaine reste lisible ; priorité la plus basse (SIRET, IBAN, plaque, e-mail l'emportent) | `CLT-172620`, `CLT185818`, `EMP-0042`, `INC-2024-0012`, `TCK022609`, `VOX-6940-AK84`, `AY-543-SS`, `FA-2024-00123`, `CMD-2024-000123`, `SKU-ALPHA-0042`, `BATCH-OPS-2026-042`, une clé de 32 caractères hexadécimaux | `[IDENTIFIANT_n]` | `identifier_code` | nombres seuls (voir `ID_LONG_NUMBER`) ; exclusions nommées (tableau suivant) ; codes gardés par une règle `keep` de l'organisation (§ 3) |
| `ID_LONG_NUMBER` : suite nue de 8 chiffres ou plus, sans séparateur, jamais collée à un mot ; priorité la plus basse (téléphone, IBAN, SIRET, NIR… l'emportent) | « voir 98765432 au registre », `20240012345` | `[IDENTIFIANT_n]` | `long_number` | montant (devise ou unité à côté : « 12500000 € », « 15000000 EUR » ; forme décimale ou de milliers : « 12500000,50 », « 12.345.678 ») ; une devise écrite en lettres doit être un mot entier, jamais la fin d'un mot (« Compteur 912345678 », « Débiteur 12345678 » sont masqués) ; date compacte `AAAAMMJJ` ou `JJMMAAAA` et horodatage `AAAAMMJJhhmm(ss)` ; plage d'années (« 2023-2024 ») ; durée `Max-Age=` ; code de nomenclature après son libellé (`classification` : « Code CPV : 37400000 », NAF, APE, NACE, NUTS, ROME) ; numéro d'un bulletin officiel (`publication` : « BODACC A n° 20260169 », BALO, JORF, « Journal officiel n° ») ; balises ; moins de 8 chiffres (« 1234567 ») |
| `FR_LABELLED_NUMBER` : nombre pur de 4 chiffres ou plus juste après un libellé (« client », « salarié », « employé », « personne », « dossier », « matricule », « bénéficiaire », « auteur », « compte utilisateur », « utilisateur », « identifiant », « adhérent », « assuré », « patient », « contrat », « ticket », « commande », « facture », « incident », « réclamation », « demande », « login », au singulier ou au pluriel, avec « n° », « numéro », « # » ou « : » facultatifs ; « n° » ou « numéro » seuls comptent en tête de ligne, règle `FR_LABELLED_NUMBER_START`) ; seul, un nombre de moins de 8 chiffres reste lisible | « dossier 696936 », « ticket 4471 », « commande n° 20512 », « salarié : 7781 » | `[IDENTIFIANT_n]` | `keyword` | montant (« facture 1500 € », « commande 1234,56 ») ; numéro composé (« décret n° 2019-1234 ») ; moins de 4 chiffres (« le ticket 12 ») ; « n° » ou « numéro » seuls après un autre mot, qu'ils numérotent (« Annonce n° 3151 », « Lot n° 2306 ») |
| `HANDLE` : `@` puis 2 à 30 caractères `[A-Za-z0-9_]`, points internes permis, jamais dans un e-mail (lettre, chiffre, « . », « @ » ou « / » avant), pas de point final | `@awa.m`, `@ine_14` | `[PSEUDO_n]` | `format` | `jean@exemple.fr` reste `[EMAIL_n]` |
| `FR_PSEUDONYM`, `FR_PSEUDONYM_QUOTED` : « alias », « pseudo(nyme) », « surnommé(e) », « connu(e) sous le nom de », « gamertag », puis un mot entre guillemets, ou un mot seul qui porte un chiffre, « _ » ou une majuscule après sa première lettre | « alias « Tigrou44 » », « pseudo : lune_noire » | `[PSEUDO_n]` | `keyword` | « dit-il », « il a dit « oui » » (« dit » n'est pas un indice : citation), « le pseudo de l'utilisateur » ; un mot simplement capitalisé (« Pseudonyme : Testo le Magnifique ») et, sans guillemets, un champ en tête de ligne (« Pseudonyme : TESTOFLAMME » d'un avis) restent au détecteur de noms, qui propage la valeur |
| `LOGIN` : `user(name)`, `login`, « utilisateur », « identifiant (de connexion) », `uid`, `samaccountname`, `upn`, puis `=` ou `:`, puis 3 caractères ou plus avec une lettre | `user=vasseurf`, « identifiant de connexion : nadege.kerbrat » | `[PSEUDO_n]` | `keyword` | `uid=1001` ; une adresse e-mail reste `[EMAIL_n]` |
| `FR_PHONE_COMPACT` : 10 chiffres collés `0[1-589]…` conformes au plan de numérotation, sans mot-clé (06 et 07 l'étaient déjà) | `sms sent to=0317495060` | `[TEL_n]` | `phone_numbering_plan` | `0012345678` (plan refusé) |
| `FR_PHONE_INTL_LOOSE` : indicatif entre parenthèses ou groupements libres après +33 | `(+33) 7 10 02 19 76`, `+33 701 20 01 57`, `(0033) 6 12 34 56 78` | `[TEL_n]` | `validated` | — |
| `FR_PHONE_MASKED` : `0[1-9]` puis 4 groupes, au moins un écrit `xx`, `XX` ou `**` et au moins un en chiffres | `06 xx xx 22 67`, `06.XX.XX.22.67` | `[TEL_n]` | `format` | `06 xx xx xx xx` (rien d'identifiant) |
| `FR_PHONE_FRAGMENT` : mot de téléphone (numéro, ligne, tél, portable, mobile) à 30 caractères au plus avant un indice de fin (« finissant par », « se terminant par », « qui finit par », « ligne en », « les deux / quatre derniers chiffres »), ou « fin du numéro / téléphone / portable » (« de son », « de sa »…), puis `…`, `...` ou `xx` facultatif, puis 1 à 3 paires ou 2 à 6 chiffres | « le numéro finissant par 59 65 », « la ligne en …24 71 » | `[TEL_n]` | `phone_fragment` | « le contrat finissant par 2026 » (pas de mot de téléphone) |

Exclusions nommées de `ID_CODE` (`detectors/codes.py`, une par test) :

| Exclusion | Exemples |
|---|---|
| `unit_suffix` (unité, ordinal, montant) | `250km`, `1234EUR`, `12kg` |
| `digits_glued_to_word` | `2024Nombre` |
| `version` | `v1.2.3`, `1.2.3-beta` |
| `legal_article` | `L1234-5`, `R.4127-1` |
| `time` | `14h30`, `14h30-16h00` |
| `bic` (pays ISO en 5e et 6e lettres) | `AGRIFRPP882` |
| `dimensions` | `1920x1080` |
| `period` | `T1-2024`, `S2-2025`, `Q3-2024` |
| `iso_timestamp` | `2024-03-12T14`, `00.000Z` |
| `month_name` | `12mars2024` |
| `standard` | `ISO-27001`, `RFC-5952` |
| `short_list` | `COVID-19`, `SARS-CoV-2`, `H1N1`, `CO2`, `UTF-8`, `SHA256`… |
| balises | `[IDENTIFIANT_12]` n'est jamais relu comme un code |

Valeurs canoniques (une valeur, une balise, dans le document seul) : une date de naissance en mots (« né le 12 mars
1985 ») vaut `1985-03-12`, comme `12/03/1985` (validateur `intl.calendar_date`) ; un identifiant après son libellé
(`fr.contextual_id`) vaut son squelette en majuscules (« clt-204518 » et « CLT 204518 » : `CLT204518`), comme une
plaque SIV (`fr.siv_plate`) ; `ID_CODE` aussi.

Choix du propriétaire (après la porte de décision) : « toutes les références préfixées, sachant qu'on n'a aucune
idée de ce qu'ils vont utiliser : on anonymise tout code, tant pis ». Aucun indice métier ni aucune liste de
préfixes métier ne garde un code ; seules restent les exclusions de ce qui n'est pas un identifiant (tableau
ci-dessus) et les règles `keep` de chaque organisation (§ 3). Conséquence mesurée et assumée : la garde « leurres
touchés ≤ 10 % » du protocole 1.1 est dépassée sur le corpus synthétique, dont les leurres contiennent de tels codes
(numéros de commande, de facture, de suivi, références produit, tickets) : 16,73 % des leurres touchés sur le
corpus synthétique de développement (1 000 documents ; 3,43 % en 1.0.1). Elle relève de la prochaine version du
protocole. `FR_PHONE_COMPACT` seul ne touche aucun leurre.

> **EN.** Strong filter 1.0.2: in doubt, a token shaped like an identifier is masked unless a named exclusion keeps
> it. New rules: IPv6 as one maximal hex run (3 groups or one 3-character group), dotted MAC, UUID, session cookies
> and named tokens, API keys, biometric template ids, identifier codes (`ID_CODE`: an ASCII letter, a digit and 6
> alphanumerics, whatever the prefix: invoice, order, product, lot and SKU codes included, by the owner's choice;
> named exclusions only for what is not an identifier; the organisation's keep rules win), bare runs of 8 digits or
> more (`ID_LONG_NUMBER`, except amounts and compact dates), numbers of 4 digits or more after a label, handles,
> pseudonyms,
> logins (new `[PSEUDO_n]` tag), compact French numbers without a keyword, bracketed or loosely grouped +33 numbers,
> partly masked numbers and number endings (`phone_fragment`). Canonical values give every written form of a value
> one tag inside the document only; nothing is kept.

### Filtre fort 1.0.2, second tour : identifiants dans les formats courants, connexion, sites personnels

Exemples du second test terrain (items H, I, J, M), tous fictifs. Les règles du premier tableau sont des motifs des
packs (`fr.toml`, `intl.toml`) : le noyau Rust compile le même arbre de `re` (look-behind en tête de motif et
look-ahead en fin seulement) et leurs validateurs (`fr.contextual_id`, `intl.login_word`) ont un jumeau Rust. Le
second tableau est un détecteur Python, appelé par les deux moteurs. Colonne « Modes » : `fort`
seul, ou `fort` et `essentiel` (format reconnu, validateur ou libellé explicite) ; le mode `personnalise` part de
`fort`.

| Règle | Exemples masqués | Balise | Raison | Modes | Reste lisible |
|---|---|---|---|---|---|
| `FR_PLATE_SIV_GLUED` : plaque SIV sans séparateur (toute casse) ou en majuscules séparées par des espaces, sans indice de véhicule (validateur `fr.siv_plate` : ni I, O, U, ni `SS`, ni `000`) | `AB123CD`, `ab123cd`, `AB 123 CD` | `[PLAQUE_n]` (plus `[IDENTIFIANT_n]`) | `validated` | fort, essentiel | `ab 123 cd` en minuscules espacées sans indice (des mots possibles) : `FR_PLATE_SIV_LOOSE` exige « véhicule », « plaque »… |
| `FR_PLATE_FNI_BARE` : ancien format FNI en majuscules (3 ou 4 chiffres, 2 ou 3 lettres, un département) comme élément de liste : tête de ligne (puce comprise) ou après « : », « ; », « , », « ( » | « Liste : 1234 AB 75, 567 XY 29 », « - 1234 AB 75 » | `[PLAQUE_n]` | `format` | fort, essentiel | après un autre mot (« Article 1234 CE 75 », « Version 2024 RC 12 ») ; unité, taxe ou monnaie (« 1500 HT 20 % », « 1250 EUR 30 ») |
| `FR_LABELLED_NUMBER`, `FR_LABELLED_NUMBER_START` (élargies) : la valeur prend ses groupes suivants entiers (espace, « - » ou « / » puis 2 à 8 chiffres, 4 groupes au plus) ; une valeur en groupes courts compte aussi (2 ou 3 chiffres puis un groupe au moins) ; un sigle en majuscules peut séparer le libellé du numéro ; libellés ajoutés : « abonné », « badge », « id » | « dossier 2026-0045 », « dossier MDPH n° 2026-0045 », « Numéro 4970 1012 3456 7899 » (une seule zone, jamais `[IDENTIFIANT_1] 1012 3456 7899`), « Client 987 654 321 », « Client 12/345/678 », « badge 4471 2209 » | `[IDENTIFIANT_n]` | `keyword` | fort, essentiel | date (« dossier 2024-03-15 », « dossier 12/03/2024 »), plage d'années (« facture 2024-2025 »), heure (« dossier 1234 12:30 » garde `12:30`), montant (« contrat 2024 1500 € » garde `1500 €`, « client 10 000 € »), quantité (« commande 25 000 pièces », « commande 20512 15 articles » garde `15 articles`) ; un téléphone reste `[TEL_n]` (« client 06 12 34 56 78 ») |
| `LOGIN_BARE_WORD` (après `login`, `user(name)`, « connecté en tant que ») et `LOGIN_BARE_WORD_NOUN` (après « identifiant (de connexion) » ou « utilisateur », jamais après « l' » ; après un autre article, le validateur seul filtre) : sans « : », un mot en minuscules sans accent de 5 lettres ou plus ; le validateur `intl.login_word` (jumeau Rust) refuse les mots courants de sa liste, les participes en « -ant(s) » et les adverbes en « -ment » | « login jdupont », « utilisateur jdupont a été bloqué », « connecté en tant que jdupont » | `[PSEUDO_n]` | `keyword` | fort, essentiel | « identifiant » ou « utilisateur » après un article (« l'utilisateur clique », « tout identifiant pouvant… », « un identifiant participant ») ; un mot courant de la liste (« identifiant unique », « login sur le portail », « utilisateur standard ») ; un participe en « -ant » ou un adverbe en « -ment » ; un mot accentué (« oublié ») |
| `SECRET_PASSWORD`, `SECRET_PASSWORD_PHRASE` : le point, la virgule ou la parenthèse qui finit la phrase reste hors de la zone | « Son mot de passe est Zx9!kLm27pQ. » → `[SECRET_1].` | `[SECRET_n]` | `keyword` | fort, essentiel (un secret est toujours masqué) | « Le mot de passe est oublié. » |
| `URL_PERSONAL_SITE` : site personnel annoncé (« site perso(nnel) », « mon site », « son site », « page perso(nnelle) », « portfolio », « mon blog », « son blog », « CV en ligne » à 40 caractères au plus avant) : l'adresse entière, chemin compris | « Portfolio sophiemartin.com », « Mon blog https://jdupont.blog », « Site perso : https://www.kevin-lambert.fr » | `[URL_n]` | `keyword` | fort, essentiel | un site sans indice (« https://www.service-public.fr », « Lire le blog https://… ») |
| `natural_person` (SIRET, SIREN, TVA d'un entrepreneur individuel) : la civilité abrégée « M. » ou « Mr » sur la ligne compte comme état civil, à côté de « en nom propre », « artisan », « libéral », « Dr »… (une personne morale sur la ligne l'emporte toujours) | « M. Hervé Clément ⏎ SIRET 552 100 554 00013 », « Il exploite en nom propre (SIRET …) », « Hervé Clément, artisan, TVA FR… » | `[SIRET_n]`, `[SIREN_n]`, `[TVA_n]` | `civil_status_nearby` | fort, essentiel | « La société Armor Services SAS (SIRET …) », « Contact Hervé Clément de la SARL Armor, SIRET … » |

Le validateur `fr.contextual_id` (valeur après un libellé, Python et Rust) refuse désormais une date ou une plage
d'années écrite avec « - », « / » ou « . » (« 2024-03-15 », « 12/03/2024 », « 2024-2025 ») : jamais un identifiant.
Raisons `keyword` désormais nommées aussi pour `LOGIN_BARE`, `SECRET_PASSWORD_PHRASE`, `SECRET_URL_PARAM`,
`FR_ORDER_NUMBER` et `FR_IBAN_LABELLED` (valeur liée à son libellé ; `format` auparavant). Formats déjà couverts par
le premier tour et vérifiés sur les exemples du test terrain : IBAN en minuscules, collé ou espacé (`[IBAN_n]`, jamais
`[CARTE_n]`), carte à clé de Luhn juste sans mot-clé, collée, groupée ou pointée (`[CARTE_n]`), VIN après son indice,
ADELI (« n° ADELI : 75 99 1234 5 », « n° AM 29 1 23456 7 »), numéro d'Ordre (« N° Ordre 75/12345 »), CNI suivie d'un
passeport à la ligne suivante, passeport en `[PASSEPORT_n]`, FINESS et TVA belge jamais en `[ADELI_n]` ni `[TEL_n]`.

| Règle | Exemples masqués | Balise | Raison | Modes | Reste lisible |
|---|---|---|---|---|---|
| `URL_PERSONAL_NAME` (détecteur `PersonalSiteDetector` ; jumeau Rust `detectors/personal_site.rs` dans le moteur fusionné, voie perf, mêmes zones ; texte avec « İ », « ı », « ſ » ou « K » : Python) : adresse web sans indice dont l'hôte (sans « www. », sans domaine de premier niveau, sans « - », « . » ni « _ ») est exactement une forme collée d'un nom cité dans le même texte, à 2 000 caractères au plus de l'adresse : deux ou trois mots consécutifs à majuscule, dans les deux ordres, ou l'initiale du premier collée au dernier ; 6 lettres au moins ; rien n'est gardé d'un texte à l'autre | « Kevin Lambert : https://kevinlambert.fr », « LAMBERT Kevin … www.kevin-lambert.fr », « Jean Dupont … jdupont.blog » | `[URL_n]` | `personal_site_name` | fort, essentiel | un site dont l'hôte ne reprend aucun nom cité (« Kevin Lambert recommande https://www.service-public.fr ») |

> **EN.** Second round (field test 2, items H, I, J, M): glued or spaced-capital SIV plates without a vehicle cue,
> old FNI plates as list items, labelled numbers taken whole with their following groups (never an ISO date, a year
> range, a time or an amount), letters-only logins after an explicit cue (never after an article, never a listed
> common word, participle or adverb), the sentence's full stop kept outside a password, announced personal websites,
> and an abbreviated civility counting as a sole trader's civil status. All are pack patterns, run as the same `re`
> tree by the Rust core, with Rust twins of their validators; modes fort and essentiel. A website whose host is exactly a glued form of a name quoted in
> the same text (`URL_PERSONAL_NAME`, reason `personal_site_name`; Rust twin `detectors/personal_site.rs` in the fused engine, Python outside its domain) is masked too.

**Jonction du second tour (1.0.2).**
- `CARD_GROUPED` accepte aussi les groupes séparés par des points (« Numéro 4970.1012.3456.7899 » → `[CARTE_1]`), comme
  les espaces et les traits d'union.
- `LOGIN_BARE_WORD_NOUN` n'a plus qu'un look-behind d'un caractère (`(?<![\w'’-])`, exclut « l'utilisateur »), seule
  forme que le noyau Rust compile : la règle tourne donc en Rust. Après « un », « le », « tout »… le validateur
  `intl.login_word` filtre seul (mots courants, « -ant », « -ment ») ; un verbe sans accent hors liste (« cet
  utilisateur concerne ») est masqué, dans le doute.
- La tête d'un code n'est jamais un nom : dans « client Jean Dupont CLT-204518 », « CLT » (suivi de « - » ou « _ » et
  d'un chiffre) n'est plus rattaché au nom ; on obtient `[PERSONNE_1] [IDENTIFIANT_1]` au lieu de
  `[PERSONNE_1]-204518` (fuite présente aussi en 1.0.1). Python `fr_names._tokens`, Rust `names/tokens.rs`.

**Troisième tour (1.0.2, revues du 26/10).**
- Sauts de ligne (règles BREAK et GAP de `_text.py`, jumeau `prepare.rs`) : un téléphone entier en tête de la ligne
  d'après n'est jamais recollé à un « IBAN coupé » (« TVA FR44732829320⏎06 12 34 56 78 » garde son saut de ligne :
  le téléphone est masqué entier, la TVA d'une société reste lisible) ; une ligne qui commence par un code postal et
  sa ville (« 75011 Paris ») n'est jamais recollée au nombre de la ligne d'avant (« Dossier 56 78⏎75011 Paris ») ; un
  courriel déjà complet en tête de ligne (partie locale de 2 caractères ou plus) ne prend pas la fin de la ligne
  d'avant quand ce morceau porte une majuscule (« Bonjour M.⏎paul@… », « Jean.⏎marie.durand@… »,
  « SKU-123456⏎support@… ») ; un morceau en minuscules reste recollé (« michele.⏎vallee57@… »).
- `FR_LABELLED_NUMBER` et `FR_LABELLED_NUMBER_START` ne s'arrêtent jamais au milieu d'un jeton (valeur suivie de « - »
  ou « _ » et d'une lettre, ou de « _ » et d'un chiffre) : « identifiant 12345678-1234-4000-a000-0123456789ab » est
  masqué entier par la règle UUID, jamais `[IDENTIFIANT_1]-a000-…`.
- Contrôle final de sortie : une valeur faite de chiffres seuls n'est jamais ré-appliquée sur un montant ou une mesure
  (devise ou unité juste après, une espace permise : €, $, £, %, EUR, euros, k€, HT, TTC, km, Go… ; devise juste
  avant ; forme décimale ou de milliers). « Contrat 100000 … capital 100000 € » garde le capital lisible.
- `SECRET_ASSIGNMENT` (pack intl) : jeton ou clé affectés hors d'une URL (« token=… », « api_key: … »,
  « client_secret = … »), lettres et chiffres mêlés, 8 caractères ou plus : un secret dans tous les modes.
- `ID_CODE` : « # » relie deux morceaux comme « - », « _ », « / » (« CLT#204518 », « JIRA#62528 » → un code).
- Mode essentiel : « facture », « commande », « devis », « bon de livraison », « ticket de caisse », « produit »,
  « référence », « lot », « article », « SKU » ne sont pas des libellés personnels. Le numéro ou le code qui les suit
  (`FR_LABELLED_NUMBER`, `ID_CODE`, `ID_LONG_NUMBER`) reste lisible en essentiel (catégorie `codes` ou `nombres_longs`)
  et masqué en fort ; un libellé personnel plus près l'emporte (« facture du client 123456 » reste masqué).

**Dernier tour, voie « codes » (1.0.2, soir du 26/10).**
- `ID_CODE`, code coupé par une espace ou une espace insécable (Python `split_code_spans`, Rust `split_codes`) :
  2 à 5 capitales puis 6 ou 7 chiffres (« CLT 204518 », « DOS 164520 ») ; ou 3 groupes ou plus de 3 à 6 capitales et
  chiffres dont deux au moins mêlent lettres et chiffres (« AB12 CD34 EF56 »). Masqué entier, raison
  `identifier_code`, mode fort ; en essentiel seulement après un libellé personnel (catégorie `codes`). Jamais collé
  à un mot, à « @ », « . », « - », « / », « # » ou « \ » ; 5 chiffres (code postal : « PARIS 75011 ») et 8 chiffres ou
  plus (`ID_LONG_NUMBER`) hors règle ; préfixes exclus (`_SPLIT_STOP`) : nomenclatures (CPV, NAF, APE, NACE, NUTS,
  ROME), publications (BOAMP, BODACC, BALO, JO, JORF, NOR, ECLI), boîtes postales (BP, CS, TSA, CEDEX), registres
  (RCS, RM, RNA, SIREN, SIRET, TVA), normes (ISO, NF, EN, IEC, CEI, DIN), devises (EUR, USD, GBP, CHF), « FR » (sites
  Natura 2000 « FR 4211811 ») et quelques mots (ART, TOME, VOL…) ; montants, dates et classifications exclus comme pour
  les longues suites. Mesure avant activation, moitiés dev : 12 candidats sur BOAMP (tous « FR » + 7 chiffres, exclus
  depuis), 0 sur BODACC, ParlaMint et Judilibre.
- `HANDLE` (« @pseudo » sans indice, fort seulement) garde entier un trait d'union dans un morceau
  (« @jean-pierre.dupont ») et un premier morceau d'une lettre suivi d'un point (« @k.lambert »).
- `HANDLE_CUED` : « @pseudo » après une plateforme (insta, Instagram, Teams, GitHub, GitLab, LinkedIn, X, Twitter,
  Discord, TikTok, Snapchat, Mastodon, Twitch, Reddit, Threads, Bluesky) ; `HANDLE_PLATFORM` : la même plateforme
  (sauf « X ») suivie de « : » et d'un nom de compte sans « @ » de 3 caractères ASCII ou plus (« Instagram :
  jp_dupont75 », « Discord : lune#1234 »), jamais le début d'une adresse web. Catégorie `pseudonymes`, tous les modes.
  Après « Teams » (d'abord un outil de réunion), `HANDLE_PLATFORM_TEAMS` ne prend qu'un compte qui commence par une
  lettre et porte un chiffre ou « _ » (« Teams : jdupont42 ») : « Réunion Teams : lundi » et « Teams : 14h30 » restent
  lisibles (jonction). After "Teams", only an account starting with a letter and carrying a digit or "_".
- `LOGIN_DOMAIN` : compte Windows « DOMAINE\utilisateur » (« CORP\jdupont ») : seule la partie utilisateur est
  masquée, le domaine (l'organisation) reste lisible. Domaine en capitales de 2 à 15 caractères, jamais au milieu d'un
  chemin (« C:\WINDOWS\System32 », « \\SERVEUR\partage »). Tous les modes.
- Indices de connexion ajoutés : « compte AD » (`LOGIN`, `LOGIN_BARE`, `LOGIN_BARE_WORD`), « sAMAccountName » sans
  « : » (`LOGIN_BARE`, `LOGIN_BARE_WORD`), « nom d'utilisateur » sans « : » (`LOGIN_BARE_WORD`). Le validateur
  `intl.login_word` refuse aussi « reste », « restent », « devra », « pourra », « garde », « conserve »… : « chaque
  utilisateur reste responsable » n'est plus un identifiant.
- Pseudonymes : `PSEUDONYM_LABEL` (« avatar : … », « nickname : … », toute valeur ASCII de 3 caractères ou plus),
  `PSEUDONYM_LABEL_LOWER` (« pseudo : lunenoire » : valeur qui commence par une minuscule, un chiffre ou « _ » ; un mot
  capitalisé reste au détecteur de noms), `PSEUDONYM_BARE` (« son avatar dark_vador42 » : chiffre, « _ » ou « . ») et
  `PSEUDONYM_BARE_WORD` (« son avatar darkvador » : minuscules, 5 lettres ou plus, validateur `intl.login_word`, jamais
  après « l' »). Catégorie `pseudonymes`, tous les modes.
- Une balise déjà produite n'est jamais relue : la valeur de `SECRET_PASSWORD` et `SECRET_PASSWORD_PHRASE` ne commence
  jamais par « [ » suivi d'une capitale, « mot de passe : [SECRET_1] » reste `[SECRET_1]` (un mot de passe qui commence
  par « [x… » reste masqué).
- Raisons : `ID_CODE` garde `identifier_code` ; les nouvelles règles du pack intl (`HANDLE_CUED`, `HANDLE_PLATFORM`,
  `LOGIN_DOMAIN`, `PSEUDONYM_LABEL`, `PSEUDONYM_LABEL_LOWER`, `PSEUDONYM_BARE`, `PSEUDONYM_BARE_WORD`) prennent
  `keyword` (`_DETECTOR_REASONS`).
- Porte du mode : la zone de `HANDLE` (fort seulement) laissée en clair en essentiel ne protège plus la règle à indice
  de la même zone ; « X : @jpdupont » est masqué en essentiel comme en fort. The fort-only `HANDLE` span left in clear
  in essentiel no longer shields the cued rule on the same span.
- Tour de correction (après la jonction) :
  - `HANDLE_PLATFORM_TEAMS` couvre aussi Skype, Slack et WhatsApp, et prend un login pointé (« Teams : jean.dupont »,
    « Skype : j.dupont », « Slack : jean-pierre.dupont »).
  - `HANDLE_PLATFORM_CHAT_WORD` : après Teams, Skype, Slack ou WhatsApp et « : », un seul mot ASCII de 5 lettres ou
    plus, en fin de ligne ou devant « ; », « , » ou « ) », jamais un mot courant (« Teams : jdupont » masqué ; « Teams :
    lundi », « Skype : indisponible », « Slack : canal » lisibles ; validateur `intl.login_word`).
  - `PSEUDONYM_LABEL_CAPS` : « Pseudo : Kryptonix » : un seul mot capitalisé en fin de ligne ou devant une ponctuation,
    jamais un mot courant (« Pseudo : Aucun » lisible). Après « pseudo » seulement : le champ « Pseudonyme : … » d'un
    avis reste au détecteur de noms, qui propage sa valeur au « Nom commercial ».
  - `LOGIN_PATH` : le dossier personnel d'un chemin (« C:\Users\alegoff\ », « /home/alegoff/ », « /Users/alegoff/ »),
    jamais Public, Default ni Administrator.
  - Le validateur `intl.login_word` refuse aussi les jours, « demain », « visio », « dispo », « absent », « canal »,
    « groupe », « serveur », « profil », « public », « aucun », « voir », « oui », « non »… (même liste en Rust).
  - Tous les modes, catégorie `pseudonymes`, raison `keyword`. EN: Skype, Slack and WhatsApp follow the Teams rule, a
    dotted login is an account, a single 5-letter word at the line end after a chat cue is an account unless it is a
    common word, a capitalised pseudonym after « Pseudo : », and the user folder of a path are masked in every mode.

### Filtre fort 1.0.2 : propagation des valeurs, tableaux CSV, fin de phrase, boîtes fonctionnelles

**Propagation des valeurs (couche 6).** Tout identifiant trouvé une fois est masqué partout, comme un nom : chaque
autre occurrence de sa valeur, sous toutes ses graphies, reçoit la même balise (l'occurrence hérite de la valeur de
sa source). Raison `propagation`, règle : celle de la source. Mêmes règles en Python (`engine._propagate_values`) et
dans le noyau Rust (`finalize/values.rs`).

| Famille | Entités | Recherche |
|---|---|---|
| noms | `PERSON` propagé | forme repliée (minuscules, sans accents) d'un nom de **plusieurs mots** (« sohan Kervadec », « sohan kervadec », « Sohan KERVADEC » après « Sohan Kervadec ») ; un nom d'un seul mot n'est jamais cherché replié (« vin blanc » après « M. Blanc » reste lisible) |
| dates de naissance | `BIRTH_DATE` | valeur ISO (celle du validateur, sinon lue sur la date : `12/03/1985`, `12 mars 1985`, `1er mars 1985`, `1985-03-12`), puis ses formes : `j/m/aaaa` et `jj/mm/aaaa` avec `/`, `.` ou `-`, `aaaa-mm-jj`, « 12 mars 1985 », « 1er », mois abrégés (« janv. », « fév », « sept »…) ; une date ordinaire égale à une date de naissance est masquée avec elle (échange assumé) |
| téléphones | `PHONE` | numéro national de 9 chiffres, précédé au plus de `0`, `33`, `330`, `0033` ou `00330` (« + » compris) : `06 12 34 56 78`, `+33 (0)6 12 34 56 78`, `0033612345678`, `06.12.34.56.78` |
| codes | identifiants (`ID`, `NATIONAL_ID`, `IBAN`, `CARD`, `PLATE`, `PASSPORT`, `SECRET`, `HANDLE`…) | squelette alphanumérique (séparateurs retirés, replié) d'au moins 6 caractères avec un chiffre, ou de 9 chiffres pour un numéro tout en chiffres : `CLT-204518`, `clt204518`, `CLT 204518` |

Gardes, sur chaque occurrence : bornes alphanumériques des deux côtés ; entre deux caractères du squelette, au plus
deux séparateurs `[ -./_]` (parenthèses en plus pour un téléphone), jamais un saut de ligne ; une suite de chiffres
ne se prolonge pas au-delà (« 1061234567890 » n'est pas « 06 12 34 56 78 » ; « 3000 6000 euros » n'est pas un
morceau d'IBAN). Jamais propagés : dates ordinaires, code postal seul, lieux, montants, organisations, e-mails et URL
(déjà trouvés à chaque occurrence par leur forme). Une occurrence qui contient strictement des zones de la même entité
les remplace (« sohan [PERSONNE_1] » devient « [PERSONNE_1] ») ; tout autre chevauchement l'écarte. Aucune table : les
formes n'existent que pendant l'appel.

**Tableaux CSV et TSV (couche 6).** Un texte délimité par « ; », une tabulation ou « , » est lu comme un tableau
quand sa ligne d'en-tête porte au moins deux délimiteurs d'une même sorte, des cellules de 1 à 40 caractères sans
chiffre, et qu'au moins deux lignes suivantes ont le même nombre de champs (le tableau s'arrête à la première ligne
qui diffère). L'en-tête y agit comme dans un tableau Markdown, lu avec « _ » et « - » changés en espaces
(`date_naissance`, `nom`, `prenom`) : contexte de la colonne, colonnes de personnes. La barre « | » reste aux
tableaux Markdown ; un champ entre guillemets qui contient le délimiteur arrête le tableau. La règle GAP (couche 0)
ne recolle jamais une ligne qui porte au moins deux « ; », tabulations ou « , » d'une même sorte à la précédente, ni ne
change en espace la tabulation d'une ligne d'un tableau TSV reconnu comme ci-dessus (en-tête compris) ; deux cellules
voisines d'une telle ligne ne forment jamais un seul nom : chaque ligne garde ses colonnes, et le nom et le prénom d'une
même ligne partagent une balise. Une prose dont les espaces sont des tabulations n'est pas un tableau (pas d'en-tête
d'étiquettes suivi de deux lignes de même nombre de champs) : ses noms restent entiers (« Le⇥dossier⇥de⇥Jean⇥Dupont »
donne une seule balise). Mêmes règles en Python (`_text._tab_row`) et en Rust (`text.rs: tab_row_chars`,
`prepare.rs: gaps`).

**Fin de phrase après un courriel (couche 0, règle BREAK).** Un point final, un saut de ligne puis une majuscule ne
sont jamais recollés quand le courriel est déjà complet à gauche (« l.ndiaye@exemple.fr.⏎IBAN » garde « IBAN » et sa
ligne) ou absent à gauche (« … fin de la note.⏎Jean@exemple.fr »).

**Boîtes fonctionnelles.** Choix du propriétaire : `support@`, `contact@`, `noreply@`… restent masquées comme toute
adresse (`[EMAIL_n]`). Une organisation qui veut en garder une ajoute une règle `keep` (§ 3).

**Signature en minuscules (`FR_SIGNATURE`).** La première ligne non vide après une formule de clôture
(« Cordialement », « Bien cordialement », « Bien à vous », « Merci », « Merci d'avance », « Bonne journée »,
« Bonne soirée », « À bientôt », « Salutations », « Amitiés », « Bises »…, ponctuation finale permise), ou la dernière
ligne non vide du texte, qui ne tient qu'un ou deux mots en minuscules (2 lettres au moins chacun) égaux, repliés, au
prénom, au nom ou aux deux d'**une seule** personne déjà masquée dans le document (nom de deux mots au moins) : même
balise que cette personne, raison `signature` (« Cordialement,⏎noé » après « M. Noé Garnier »). Deux personnes qui
partagent ce mot : rien n'est masqué ; « L'équipe support » ou un prénom en minuscules dans la prose restent lisibles.

**Initiales après un indice (`FR_INITIALS`).** Après « rédigé(e) par », « établi(e) par », « validé(e) par »,
« visé(e) par », « signé(e) par », « saisi(e) par », « relu(e) par », « de la part de », « initiales », « paraphe »,
« auteur » ou « visa », puis 1 à 3 espaces ou « : » : 2 ou 3 capitales (« NB », « JMD », un point final permis) ou des
initiales pointées (« F.L. », « R. G. », « A.B.C. ») sont masquées `[PERSONNE_n]`, raison `initials_after_cue`. Sigles
exclus : RH, DG, DRH, DSI, CA, CE, CSE, SA, TVA, UE, IT, PDG, DAF, QA, IA, DGS, DGA, DPO, CNIL, SAS, EI, PME, TPE, CEO,
CTO, CFO, COO, AI, OK, PS, MOA, MOE, DSN, CB (« Rédigée par la DRH », « validé par RH » restent lisibles).

> **EN.** Value propagation: every identifier found once is masked everywhere, in every written form, with one tag
> (the occurrence inherits its source's value; reason `propagation`). Families: folded multi-word names, birth dates
> (forms generated from the ISO value), phones (9-digit national number with its prefixes), codes (alphanumeric
> skeleton, 6+ characters with a digit, or 9 digits). Guards: alphanumeric boundaries, at most two separators between
> characters, no line break, a digit run never extends past the match. A match strictly containing same-entity spans
> replaces them. CSV and TSV tables (";", tab, ","; a short, digit-free header and two or more rows with the same
> field count) act as Markdown tables do. BREAK never joins a final full stop, a line break and a capital when the
> e-mail is complete on the left or absent from it. Functional mailboxes stay masked. A lowercase signature line
> (first non-empty line after a closing formula, or the last non-empty line) equal to the given name, surname or
> both of exactly one masked person gets that person's tag (`FR_SIGNATURE`, reason `signature`). Initials after a
> cue ("rédigée par NB", "visa : F.L.") are masked (`FR_INITIALS`, reason `initials_after_cue`), common acronyms
> excluded. Prose whose spaces are tabs is not a TSV table: its names stay whole.

### Filtre fort 1.0.2 : contrôle final de sortie (`output_check`)

Dernière étape des zones (couche 6), après la résolution, toutes les propagations, les signatures et les initiales,
juste avant les règles `keep` de l'organisation. Variante restreinte du plan (item 8) : le contrôle ne relance aucun
détecteur, il **ré-applique ce que le moteur a déjà masqué**.

- **Valeurs contrôlées :** la forme repliée (minuscules, sans accents) de chaque zone masquée de 6 à 128 caractères
  qui porte un chiffre ou « @ » (codes, numéros, téléphones, e-mails, IBAN…), sans saut de ligne. Au-delà de 128
  caractères ce n'est plus une valeur d'identifiant ; la borne garde le coût linéaire sur un texte hostile (« 1 » ×
  100 000 masqué d'un bloc coûtait 23 s à l'automate). Les noms et les mots
  sans chiffre n'en font pas partie : leurs propres règles de propagation gardent la précision (§ 2, « Propagation des
  valeurs »).
- **Recherche :** chaque autre occurrence de cette forme dans le texte replié (casse et accents près), la plus longue
  d'abord, sans chevauchement. Les variantes d'espacement et de séparateurs des codes et des téléphones sont déjà
  couvertes par la propagation des valeurs (squelette).
- **Masquage :** même entité, même libellé, même valeur, donc **même balise** que la zone d'origine ; règle
  `output_check:<règle d'origine>`, raison `output_check` dans `explain`.
- **Ce qu'il rattrape :** une occurrence collée à un mot, que les bornes des détecteurs et de la propagation écartent
  (« Télé0612345678 » après « Tél : 0612345678 » devient « Télé[TEL_1] » ; « réfCLT-204518 » après « CLT-204518 »
  devient « réf[IDENTIFIANT_1] »).
- **Gardes :** jamais au milieu d'un nombre (deux chiffres de part et d'autre d'une borne : « 90612345678 » reste
  entier) ; jamais sur une zone existante, masquée ou gardée ; les règles `keep` passent après et l'emportent (un code
  gardé par `SKU-[0-9]{6}` reste lisible partout).
- **Modes :** tous (fort, essentiel, personnalisé) : il ne masque que des valeurs que le mode a déjà masquées.
- Déterministe, rien n'est gardé d'un appel à l'autre ; mêmes règles en Python (`selfcheck.py`) et dans le noyau Rust
  (`finalize/selfcheck.rs`).

Le détecteur des codes (`ID_CODE`, `ID_LONG_NUMBER`, `SECRET_COOKIE`) a désormais son jumeau Rust
(`rust/src/detectors/codes.rs`) : mêmes zones, mêmes valeurs, mêmes exclusions, sans passage par Python dans le moteur
fusionné.

> **EN.** Output self-check (restricted variant, last span step, before the organisation's keep rules): every masked
> value of 6 characters or more holding a digit or "@" (folded: lower case, no accents) that still occurs elsewhere
> in the folded text is masked with the same entity, label and value, hence the same tag; rule
> `output_check:<source rule>`, reason `output_check`. It catches occurrences glued to a word that detector and
> propagation boundaries refuse ("Télé0612345678", "réfCLT-204518"); never inside a number, never over an existing
> masked or kept span, keep rules win. All modes (it only re-applies what the mode already masked). Same rules in
> Python (`selfcheck.py`) and Rust (`finalize/selfcheck.rs`). The code detector now has a Rust twin
> (`rust/src/detectors/codes.rs`). A currency written in letters before a long number must be a whole word:
> "Compteur 912345678" and "Débiteur 12345678" are masked.

### Filtre fort 1.0.2 : mise en page (second test terrain)

Ces règles tournent dans les modes **fort et essentiel** (et donc personnalisé) : elles disent où finit une valeur,
pas quoi masquer. Mêmes règles en Python et dans le noyau Rust.

**Rien ne franchit un retour à la ligne par accident (couche 0, règles BREAK et GAP).**
- BREAK, courriel : un mot sans signe (ni `.`, `_`, `-`, ni chiffre) qui porte une majuscule, en fin de ligne, n'est
  jamais le début du courriel de la ligne suivante (« Agence de Tours⏎karine.lopez@… », « ACME France SAS⏎sophie.lemoine@… »
  gardent leur ligne) ; un mot sans signe n'est pas recollé non plus devant une partie locale déjà complète
  (« prénom.nom@… », séparateur intérieur). « jean.du⏎pont@exemple.fr » reste recollé (`_text._email_join`,
  `prepare.rs: email_join`).
- GAP, chiffres : un saut de ligne entre deux chiffres n'est jamais ramené à une espace quand la ligne d'après commence
  par un téléphone français entier (`0[1-9]` puis quatre groupes de deux chiffres, séparateur `␣.-` permis) ou que la
  ligne d'avant finit par un tel numéro : « Matricule 0049217⏎06 74 28 19 53 » donne un identifiant et un téléphone,
  plus un seul numéro (`_text._phone_line`, `prepare.rs: phone_line`). « 06 12 34⏎56 78 » reste recollé.

**Nom de voie coupé par un retour à la ligne (`FR_ADDRESS`).** Quand le nom de voie s'arrête en fin de ligne sur des
particules seules (« de la », « des », « du »…, au moins une), il continue sur la ligne suivante, marques de citation
« > » d'un courriel cité comprises : « 29 avenue de la⏎Gare. », « 4 impasse des⏎> Camélias, 29900 Concarneau » (une
seule adresse). Sinon le nom s'arrête toujours à la fin de ligne (`fr_address._dangling`, `address.rs: dangling`).

**Lieu-dit (`FR_ADDRESS`, raison `named_place`).** « lieu-dit » ou « lieu dit » suivi d'un nom (mots capitalisés)
désigne à lui seul un lieu d'habitation : masqué sans numéro ni mot de domicile (« lieu dit La Croix Blanche »), avec
le code postal et la commune qui suivent s'il y en a. « le lieu-dit de la bataille » (pas de nom) reste lisible. Après
une voie ou un lieu-dit, « , commune de » (ou « commune d' ») devant une commune connue fait partie de l'adresse
(« lieu dit La Croix Blanche, commune de Plouay » : une seule balise).

**Bloc d'adresse sur plusieurs lignes (`FR_ADDRESS`).** Une voie finie juste avant une ligne de compléments
(« Bât. C, 3e étage », « Appartement 12 ») ou une boîte postale, elles-mêmes juste avant le code postal et la commune,
forme une seule adresse : « 12 rue des Lilas⏎Bât. C, 3e étage⏎75011 Paris » donne une seule balise, plus deux.

**Mise en page, troisième tour (1.0.2, revue du 26/10, équipe rouge `crlf` et `line_break`).** Tous les modes (fort,
essentiel, personnalisé), Python et Rust à l'identique ; CRLF se lit exactement comme LF.
- **BREAK_NUMBER (couche 0, `_text._number_join`, `prepare.rs: number_join`).** Un saut de ligne entre deux morceaux
  faits de chiffres, de `.` et de `-` est retiré quand les deux morceaux recollés sans blanc forment un numéro prouvé :
  téléphone français entier (« 07⏎-93-28-03-42 », « 07.42.66.93⏎.70 »), IPv4 (« 5.46⏎.239.23 »), SIREN ou SIRET (clé
  de Luhn, 9 ou 14 chiffres), NIR (15 chiffres, clé 97), RIB (23 chiffres, clé 97). Un code pays seul en fin de ligne
  devant le reste d'un IBAN est recollé si la clé de l'IBAN entier est juste (« IBAN FR⏎76… »). Sans preuve, rien
  n'est recollé (« Total 12⏎-5 articles », « Réf. 12-34⏎.56 ») ; les gardes de GAP restent : jamais devant une ligne de
  tableau CSV, ni devant une ligne « code postal et ville », ni contre un téléphone entier de la ligne voisine. Un IBAN
  n'est « déjà entier » en fin de ligne qu'à partir de 15 caractères : « FR76 » seul a une clé juste par hasard et ne
  bloque plus le recollage (« IBAN : FR76⏎1660… » donne `[IBAN_1]`).
- **BREAK_PLATE (couche 0, `_text._plate_join`, `prepare.rs: plate_join`).** Une plaque d'immatriculation coupée par un
  saut de ligne est recollée : SIV (« WB 864⏎SW », « DV-185⏎-FP », « SF-112-⏎ES ») ou FNI (« 9971 ZL⏎59 », « 8871⏎LZ 59 »).
  On lit au plus 9 caractères (majuscules, chiffres, espace, tiret) de chaque côté, en morceaux qui commencent ou
  finissent sur un mot entier ; le saut devient une espace si la plaque se lit ainsi, sinon il est retiré.
- **STREET_WRAP (`FR_ADDRESS`, `fr_address._street_name`, `address.rs: street_name`).** Une voie numérotée dont le type
  finit la ligne continue sur la ligne suivante (« 84 rue⏎des Lilas, 97600 Mamoudzou », « 41 impasse⏎de la Mairie » :
  une seule adresse). Le numéro de la ligne d'avant mène la voie aussi en CRLF (« 59\r⏎place … »).
- **OFFICE_NUMBER (`fr_address._office_before`, `address.rs: office_before`).** Un numéro de bureau, de salle, de pièce,
  de porte, de local, de chambre, de poste, de casier, de guichet ou de box en fin de ligne n'est pas le numéro de la
  voie de la ligne d'après : « Bureau 1⏎rue de la Paix, 75002 Paris » donne « Bureau 1⏎[ADRESSE_1] ».
- **ADDRESS_LABEL (`fr_address._labelled`, `address.rs: labelled`).** Une étiquette d'adresse qui nomme une personne,
  juste avant un code postal vérifié et sa commune, sur la même ligne (« adresse », puis au plus 40 caractères sans
  chiffre ni `. : ;` dont un mot de personne : salarié, employé, client, patient, personnel, domicile, locataire,
  assuré, bénéficiaire, adhérent…, puis « : »), en fait une adresse : « Adresse du salarié : 75011 Paris », « Adresse
  du domicile : 69003 Lyon ». L'étiquette seule (« Adresse : 75017 PARIS ») ou sans personne (« Adresse de livraison :
  69003 Lyon ») reste lisible, comme le veut le § 2 (adresses d'organisations). Écrite comme une règle, sans assertion
  arrière (le compilateur du noyau Rust n'en prend que d'un caractère). Dans « Adresse du salarié : 75011 Paris », le
  code postal garde la balise du numéro après « salarié » (`FR_LABELLED_NUMBER`, priorité de validation) et la commune
  prend `[ADRESSE_1]` : plus rien de lisible.
- **CODE_HEAD (`fr_address._street_name`, `address.rs: street_name`).** Un mot collé à `-` ou `_` puis un chiffre est la
  tête d'un code, jamais la suite d'un nom de voie : « 12 rue des Lilas SKU-123456 » donne « [ADRESSE_1] [IDENTIFIANT_1] »
  en mode fort et « [ADRESSE_1] SKU-123456 » en mode essentiel (le code métier reste entier et lisible), au lieu de
  « [ADRESSE_1]-123456 ». Cinq chiffres juste après le tiret sont un code postal collé, pas un code : « route du Moulin
  de la Croix-99900 Val-des-Nuages » (exemple fictif) reste une seule adresse.
- **COMMUNE_WRAP (`fr_address._commune`, `address.rs: commune`).** Un code postal qui finit la ligne garde sa commune
  quand elle commence la ligne suivante et qu'elle est vérifiée pour ce code (« 84 rue des Lilas, 97600⏎MAMOUDZOU »,
  « 12320⏎Conques-en-Rouergue » : une seule adresse). Une commune inconnue ne passe jamais la ligne.

> **EN.** Layout, third round (all modes, Python and Rust alike, CRLF exactly like LF). BREAK_NUMBER removes a line
> break between two pieces of digits, dots and dashes when, joined without a blank, they make a proven number (French
> phone, IPv4, SIREN/SIRET by Luhn, NIR and RIB by their key 97), and joins a lone country code to the rest of an IBAN
> whose key is right; the GAP guards stay; an IBAN is "already whole" only from 15 characters ("FR76" alone has a right
> key by chance). BREAK_PLATE joins a SIV or FNI licence plate split by a line break (one space when the plate reads
> so, otherwise the break is removed). STREET_WRAP: a numbered street whose type ends the line continues on the
> next line. OFFICE_NUMBER: an office, room or door number ending a line is not the next line's house number.
> ADDRESS_LABEL: an address label naming a person right before a verified postcode and its town makes them an
> address; a bare "Adresse :" stays readable (§ 2). CODE_HEAD: a word glued to "-" or "_" then a digit heads a code
> and never continues a street name (essentiel keeps the business code whole and readable). COMMUNE_WRAP: a postcode
> ending a line keeps its town when the next line starts with a town verified for that postcode; an unknown town never
> crosses the line.

**Liaison de l'indice de naissance (`BIRTH_DATE`, `BIRTH_DATE_WORDS_EN`, `FR_BIRTH_DATE_WORDS`).** Un indice
(« né le », « date de naissance », « DDN »…) ne vaut que pour la **première** date qui le suit : une date déjà passée
entre le dernier indice et la valeur (une année de quatre chiffres 18xx à 20xx, ou une date chiffrée à l'année sur deux
chiffres comme « 12/05/84 ») annule le contexte. « né le 12 juin 1934 à Nantes, entré le 5 janvier 2024 » garde la
date d'entrée ; sous « Date de naissance : 12/05/1984 », les horodatages d'un journal (« [21/10/2026 09:10] ») restent
lisibles. « nom de naissance » désigne un nom, jamais une date (« Son nom de naissance est Perrin. … décédé le
3 mars 2025 » garde la date du décès). Un en-tête de colonne et un indice placé juste après la valeur (« 12/05/1984
(date de naissance) ») ne sont jamais annulés ; un nouvel indice relie la date suivante (« née le 4 juin 1981 »).
Règle des motifs dont le veto est `INTL:other_date` (`DetectionContext.cue_spent`, `scanner.rs: cue_spent`). Une
même date de naissance écrite deux fois (« 3 mai 1979 », « 03/05/1979 ») garde une seule balise (propagation des
valeurs).

**Dates de naissance, troisième tour (1.0.2 : `BIRTH_DATE_SHORT`, `BIRTH_DATE_COMPACT`, `BIRTH_DATE_ABBR_EN`,
`FR_BIRTH_DATE_ABBR`, `FR_BIRTH_DATE_MAIDEN`, `FR_BIRTH_DATE_PLACE`).** Modes fort, essentiel et personnalisé
(catégorie `dates_naissance`), Python et Rust à l'identique. Après un indice de naissance (« né le », « née le »,
« né(e) le », « DDN », « D.D.N. », « date de naissance », « date de naiss. », « naissance », « birthdate »,
« born »…), dans la même fenêtre que les autres dates de naissance (80 caractères avant, 4 après) : année sur deux
chiffres (« 06/04/69 », « DDN 08/04/79 », « 03.05.79 », « Né le 3/5/38 », jamais un morceau d'une suite plus longue
comme « 01.02.03.04.05 », `BIRTH_DATE_SHORT`) ; mois abrégés (« 12 jui. 1979 », « 1er janv. 1990 », « 4 févr. 1981 »)
et mois en toutes lettres suivi d'une année sur deux chiffres (« 3 mars 85 », `FR_BIRTH_DATE_ABBR`) ; mois anglais
abrégés (« born 3 Mar 1985 », « Sept. 3, 1985 », `BIRTH_DATE_ABBR_EN`, valeur écrite) ; forme compacte aaaammjj et
année en tête avec « . » ou « / » (« Date de naissance : 19751021 », « 1975.10.21 », fenêtre de 40 caractères,
`BIRTH_DATE_COMPACT`). Le nom de naissance entre « née » et la date (« née Leclerc le 21 janvier 1972 », « née
Leclerc, le 21/01/1972 » : un à trois mots à majuscule, virgule permise, puis « le » et la date sous toutes ces formes)
suffit, sans fenêtre (`FR_BIRTH_DATE_MAIDEN`, niveau A) ; de même le lieu de naissance (« Né à Lyon le 06/04/1969 »,
« née à Saint-Étienne (42), le 3 mars 85 », « né au Mans le … » : « à », « au », « aux » ou « en », un à cinq mots à
majuscule ou de liaison, département entre parenthèses facultatif, `FR_BIRTH_DATE_PLACE`, niveau A). Valeur ISO du
validateur `intl.calendar_date` : une année sur deux chiffres de 00 à 26 vaut 2000 à 2026, au-delà 1926 à 1999 (pivot
fixe `BIRTH_YEAR_PIVOT`, sortie déterministe) ; « jui. » (juin ou juillet) rend la date écrite, sans valeur ISO ni
propagation. Les autres formes alimentent la propagation : « Né le 3 mars 85 ; rappel : 03/03/1985 » donne une seule
balise. La liaison à la première date reconnaît aussi ces formes : une forme compacte (8 chiffres 18xx à 20xx, mois
et jour plausibles) ou un mois en mots suivi d'une année sur deux chiffres (« 3 mars 85 », « 1er janv. 90 »), passés
entre l'indice et la valeur, annulent le contexte (« Né le 3 mars 85 à Agen, entré le 05/01/2024 » garde la date
d'entrée). Sans indice (« Réunion du 06/04/69 », « Le 3 mars 85 la loi a changé »), la date reste lisible.

> **EN.** Birth dates, third round (1.0.2), modes fort, essentiel and personnalise (category `dates_naissance`),
> Python and Rust alike. After a birth cue, in the usual birth-date window: two-digit years (`BIRTH_DATE_SHORT`),
> abbreviated months and full month names with a two-digit year (`FR_BIRTH_DATE_ABBR`), abbreviated English months
> (`BIRTH_DATE_ABBR_EN`), compact yyyymmdd and year-first "1975.10.21" (40-character window, `BIRTH_DATE_COMPACT`);
> new cues "D.D.N." and "date de naiss."; the birth name between "née" and the date is enough (`FR_BIRTH_DATE_MAIDEN`,
> tier A), and so is the birthplace ("Né à Lyon le 06/04/1969", `FR_BIRTH_DATE_PLACE`, tier A).
> ISO value from `intl.calendar_date`: two-digit years 00-26 are 2000-2026, others 19xx (fixed pivot); "jui." (June or
> July) returns the written date, with no ISO value and no propagation. The first-date binding also recognises a
> compact date and a month word followed by a two-digit year. Without a birth cue the date stays readable.

> **EN.** Layout rules, modes fort and essentiel (Python and Rust alike). BREAK never makes a plain capitalised word
> ending a line, or a plain word before an already complete "first.last" local part, the start of the next line's
> e-mail. GAP never joins two digit lines when the next line starts with, or the previous one ends with, a whole French
> phone number. A street name stopping on particles at the line end continues on the next line (quote marks "> "
> included). "lieu-dit X" is an address on its own (reason `named_place`); ", commune de" before a known town belongs to
> the address; a street, its complement line and the postcode line form one address (one tag). A birth cue binds only to the first date
> after it: a year (18xx-20xx) or a two-digit-year numeric date already passed between the last cue and the value
> cancels the context; "nom de naissance" (birth name) is never a date cue; column headers and a cue right after the
> value are never cancelled.

### Filtre fort 1.0.2 : noms, sociétés et entrepreneurs individuels (second test terrain)

Ces règles tournent dans les modes **fort et essentiel** (et donc personnalisé, sauf si `personnes` y est désactivé).
Mêmes règles en Python (`heuristics/fr_names.py`, `_lexicon.py`, `_vocab.py`, `organizations.py`, `engine.py`) et
dans le noyau Rust (`names/fields.rs`, `names/cues.rs`, `names/lexicon.rs`, `engine/organizations.rs`, `scanner.rs`).

**Prénom et nom en minuscules sans indice (`FR_NAMES`, raison `name_lexicon`).** Deux mots en minuscules latines
séparés par un seul blanc, hors adresse e-mail, URL ou mot composé : le premier est un prénom sans autre lecture (au
moins 512 naissances, plus prénom que nom, ni mot courant ni commune), le second un nom d'au moins 256 porteurs, ou
d'au moins 4 096 s'il est aussi un mot courant (« martin »). Ni l'un ni l'autre n'est un mot-outil, un mot d'arrêt, une
particule ou un auxiliaire. « rdv avec sophie martin demain », « merci à sandrine lacroix » sont masqués ; « la pierre
blanche », « à paris lundi », « un martin pêcheur » restent lisibles (`_lowercase_pairs`, `fields.rs: lowercase_pairs`).

**Civilité après un éponyme.** « l'arrêt maladie de M. Jean Dupont », « l'arrêt maladie de Mme Nadia Ouazzani » : une
civilité de personne vivante (M., Mme, Mlle, Monsieur, Madame… `_vocab.CIVILITIES`) désigne la personne, l'éponyme ne
se transmet qu'à un titre (« rue du Docteur Roux », « syndrome de Down », « maladie de Parkinson » restent lisibles).

**Article élidé lié par un trait d'union.** « Pont-l'Abbé » est un lieu : la civilité « Abbé » n'y est pas un indice,
« Pont-l'Abbé. Montant facturé » ne fait plus de « Montant » une personne.

**C'h breton.** « Guivarc'h », « Kerc'hoz » : l'apostrophe du c'h appartient au nom, jamais une élision ; le mot
entier est un nom connu ou un nom inconnu (« Cc : Solenn Guivarc'h » est masqué en entier).

**Prénom_Nom dans un nom de fichier.** Deux segments capitalisés latins liés par « _ », sans lettre ni chiffre accolé :
le premier est un prénom sans autre lecture (mêmes seuils que ci-dessus), le second un nom connu qui n'est pas une
entité, ou un mot inconnu qui n'est pas un mot courant. « CV_Nadia_Haddad.pdf » donne « CV_[PERSONNE_1].pdf » ;
« rapport_Annuel_Final.pdf » reste lisible (`_file_name_people`, `fields.rs: file_name_people`).

**Précision.** Sigles d'instances et d'organismes (CSE, CSSCT, CHSCT, UDAF, EHPAD, MDPH, CCAS, PMI, ESAT, SSIAD, CMPP,
APEC, CARSAT, CNAV, CROUS) : jamais un nom, ni tirés d'une adresse e-mail (« Le CSE se réunira » malgré
« cse.morez@… »). Impératifs en tête de phrase (« Contactez », « Appelez », « Rappelez », « Écrivez »…) : des mots
courants (« J.D. Contactez P. Lemoine » garde « Contactez »). Un verbe après un rôle n'est jamais un nom (« Le salarié
doit être convoqué »). Une occurrence collée à « Saint- » (« Saint-Claude ») n'est jamais propagée depuis une personne
« CLAUDE Martin ». Un prénom rare homonyme d'une commune ne vaut pas seul (« Ville: Meylan »). « Marié », « Mariée »,
« Mariés », « Mariées » (accent compris, `_vocab.ACCENTED_WORDS`) ne sont jamais le prénom « Marie » (« Marié le
12/06/2015 »).

**Raison sociale entière lisible.** Une raison sociale qui porte une forme juridique de société (SARL, SAS, SA, SCP,
SELARL, SCI, GmbH… pas EI ni EIRL), dans ses mots, juste avant (deux blancs au plus) ou juste après (blancs, tabulations
ou une virgule, trois au plus), reste lisible **en entier**, même si elle contient un nom de personne : « SARL DUPONT
BÂTIMENT », « La SAS Dupont Frères », « Clinique Jules Verne SAS », « Le cabinet SELARL VIDAL & ASSOCIÉS ». Exceptions :
le réglage `company_ids` à `mask` ou `keep`, le profil strict, et un repère d'entrepreneur individuel à moins de
200 caractères (la raison sociale est alors celle d'une personne physique, masquée). « M. Petit » reste masqué même si
la « Boulangerie Petit SARL » reste lisible : une raison sociale n'est pas une personne (considérant 14 du RGPD).

**Portée de l'entrepreneur individuel (raison `sole_trader`).** Le repère « entrepreneur individuel », « EI »,
« auto-entrepreneur »… rend personnel un SIREN, un SIRET ou un numéro de TVA dans le **paragraphe** du numéro (sa
ligne ou les lignes voisines jusqu'à une ligne vide, fenêtre de 120 caractères de part et d'autre) ; ailleurs dans le
document, seulement si aucune personne morale (« société », forme juridique…) n'est près du numéro dans ce paragraphe
(fenêtre 80/40). « la société Armor Services SAS …, SIREN 552 100 554 » reste lisible même si un entrepreneur
individuel est cité 300 mots plus loin ; « Jean Martin exerce comme entrepreneur individuel. … SIREN 732 829 320 »
reste masqué (`Anonymizer._sole_trader`, `scanner.rs: sole_trader`).

**Initiales (`FR_INITIALS`).** Indices ajoutés : « trigramme », « paraphes » (« Le trigramme ASM signe »). Après un
indice, jusqu'à trois autres initiales séparées par « / » ou « , » (« Paraphes : JBR / MEA »), même forme que la
première (`_more_initials`). Initiales entre parenthèses juste après une personne masquée, égales aux premières
lettres A-Z des parties de son nom (« Jean-Marc Delaunay (JMD) », raison `initials_of_person`) ; « (RH) » reste
lisible. Les initiales de quatre lettres après un indice (« Visa : FXLD ») et les initiales pointées sans indice
(« (M. T.) ») sont masquées depuis le troisième tour (ci-dessous).

> **EN.** Names, companies and sole traders, modes fort and essentiel (Python and Rust alike). A lowercase given name
> (no other reading, at least 512 births) followed by a lowercase surname (at least 256 bearers, 4,096 when also a
> common word) is a person with no cue. A living person's civility after an eponym names the person ("l'arrêt maladie
> de M. Jean Dupont"); titles keep the eponym ("rue du Docteur Roux"). An elided article bound by a hyphen
> ("Pont-l'Abbé") is never an honorific. The Breton c'h belongs to the name. Given_Surname inside a file name is
> masked. Acronyms of bodies (CSE, UDAF, EHPAD…) and sentence-initial imperatives are never names. A company name
> carrying a company legal form (not EI/EIRL) stays readable as a whole, unless `company_ids` says otherwise, the
> strict profile, or a sole-trader cue within 200 characters. A sole-trader cue makes a SIREN/SIRET/VAT number
> personal within the number's paragraph (120-character window, never past a blank line), and elsewhere in the
> document only when no legal entity is near the number. New initials cues ("trigramme", "paraphes"), up to three
> more initials after "/" or ",", and bracketed initials matching the masked person right before them (reason
> `initials_of_person`).

### Filtre fort 1.0.2 : noms, troisième tour (revue du 26/10)

Règles des personnes : modes **fort et essentiel** ; en personnalisé, sauf si la catégorie « personnes » est coupée.
Mêmes règles en Python (`engine._company_named`, `_civility_surnames`, `_initials`, `_names_r3`,
`_join_split_names`, `FrenchNameDetector._lowercase_after_prepositions`) et en Rust (`finalize/pipeline.rs`,
`names/fields.rs`).

- **Société dont le nom commence par une personne.** Entre la personne et la forme juridique, jusqu'à trois mots de
  plus, capitalisés, « & » ou « et » (un ou deux blancs chacun) : « chez Dupont Frères SAS », « Martin & Fils SARL »
  restent lisibles en entier (`_company_tail_ends`). Une civilité juste avant (« M. Jean Dupont SARL ») fait toujours
  une personne ; une fin de phrase ou de ligne arrête le nom.
- **Nom de naissance (raison `maiden_name`).** « née Leclerc », « née LECLERC » : le mot qui suit « née » est un nom
  de famille, capitalisé ou en capitales, s'il ne touche aucune zone et si le texte contient déjà une personne.
- **Prénom seul en minuscules après une préposition.** « par », « avec », « chez », « pour » ou « à », un blanc, puis
  un prénom sans autre lecture (pas un mot courant, pas une commune, pas ambigu, plus prénom que nom, au moins 512
  naissances) : « prise en charge par mathéo », « rdv avec chloé ». « avec plaisir », « pour rose » restent lisibles.
- **Initiales.** Quatre lettres admises après un indice (« Visa : FXLD / CN »). Initiales pointées (`[A-Z].` jusqu'à
  trois fois, séparées par rien, un blanc ou « - ») :
  - juste après une personne, ajoutées à sa zone (« Lefebvre-Durand M.-H. »), sauf si un mot capitalisé suit ;
  - d'au moins deux lettres juste avant une personne, ajoutées à sa zone (« J.-B. Lemoine ») ;
  - entre parenthèses, raison `initials_in_brackets` (« (M. T.) ») ;
  - après une personne et « , », « et » ou « & », raison `initials_in_list` (« Paul Morel, Sophie Blanc, C.M. »,
    « …, Mathéo Haddad, M. L. ») ; en capitales sans points (« AC ») seulement après deux personnes de la même liste,
    chacune en prénom et nom (« Présents : Quentin Moreau, Mathéo Moreau, AC ») ;
  - à trait d'union puis particules et nom, raison `initials_with_surname` (« J.-B. de La Fontaine ») ;
  - deux lettres collées, ou trois avec un trait d'union, en début de ligne puis fin de ligne ou mot capitalisé, ou
    après « de », « par », « pour », « avec », « chez », « à », raison `initials_dotted` (« J.D. Contactez… »,
    « Adresse de I.P. », « Rédigée par M.-C.D. ») ; trois lettres collées sans autre indice (« de P.M.A. »,
    « (C.C.P.) ») restent lisibles. « M. » suivi d'un blanc est une civilité, sauf dans une liste de personnes ou
    entre parenthèses.
  Sigles exclus : la liste des initiales (`NOT_INITIALS`) et celle des sigles pointés (`DOTTED_NOT_INITIALS` : N.B.,
  P.J., H.T., T.T.C., R.C.S., S.A., A.R., R.C., B.P.U., E.D.F.…). Une lettre seule (« M. », « A. Objet ») n'est
  jamais prise seule.
- **Nom coupé par un saut de ligne.** « Yann LE⏎GALL » : particule en capitales, saut de ligne, mot en capitales qui
  finit la ligne, ajoutés à la personne. « Bien à vous,⏎Jean⏎Dupont » : deux noms d'un mot, le premier ouvre sa
  ligne et suit une virgule ou une formule de clôture, le second finit la sienne : une seule personne, une seule
  balise. Une liste « Martin⏎Durand » sans formule garde deux balises.
- **« "DUPONT, Jean" ».** Nom en capitales, « , », prénom capitalisé : une seule personne, une seule balise.
- **Tour de correction (après la jonction).**
  - Sigles pointés : R.G., A.J., L.R.… restent des initiales. Les exclure laissait lisibles de vraies initiales
    (« Paul Martin (A.J.) », « Présents : …, …, LR ») : en cas de doute, on masque.
  - Le rattachement « Yann LE⏎GALL » est en temps linéaire. Avant, un texte d'1 Mo fait de ces noms coûtait plus de 10 s.
  - STREET_WRAP : une voie dont le type finit la ligne (« 84 rue⏎des Lilas ») ne continue sur la ligne suivante que si
    celle-ci ressemble à un nom de voie. Il faut des particules puis un mot capitalisé ou un nombre (« du 8 Mai 1945 »),
    ou un mot capitalisé qui n'ouvre
    pas une phrase (« À revoir », « Merci ») et n'est pas un libellé (« Téléphone : »). « 12 avenue⏎les résultats »
    reste lisible, et « Adresse : 12 avenue⏎Téléphone : … » garde son libellé.
  - Le champ « Adresse : » ne prend jamais « [ » ni « ] » : une balise déjà posée n'est plus coupée.
  - Python et Rust à l'identique.

Restent à faire : le couple Garnier et la mère et la fille Tanguy (même balise quand le nom est commun), « Tran Van »
sans civilité, « Hôtellerie des Alpes SAS, 155, route… » (le détecteur d'adresses prend le nom de la société).

> **EN.** Names, third round, modes fort and essentiel (and personnalise unless "personnes" is off), Python and Rust
> alike. A company name starting with a person keeps up to three more capitalised words, "&" or "et" before its legal
> form ("Dupont Frères SAS"). "née" + a capitalised or capitals word is a maiden name (`maiden_name`). A lone
> lowercase given name with no other reading after "par", "avec", "chez", "pour" or "à" is a person. Four-letter
> initials after a cue; dotted initials right after or before a person join its span; bracketed
> (`initials_in_brackets`), listed after a person (`initials_in_list`), hyphenated with a surname
> (`initials_with_surname`), at a line start or after a preposition (`initials_dotted`); dotted acronyms excluded. A
> capitals particle and surname wrapped onto the next line join the person; one-word given name and surname on two
> signature lines share one tag; "DUPONT, Jean" is one person. Fix round: R.G., A.J., L.R. and the like stay
> initials (excluding them left real initials readable); the "LE⏎GALL" join runs in linear time; a street whose type ends the line continues only onto a line that
> looks like a street name; the address field never takes "[" or "]", so an existing tag is never cut.

## 3. Règles de l'organisation

Un jeu de règles a l'esprit d'un pack pays : déclaratif, versionnable, explicable. Il s'ajoute au moteur
automatique, dans l'appel MCP (`rules`), l'API REST (`rules`), ou la bibliothèque (`Anonymizer(rules=...)`).

```json
{
  "name": "acme",
  "rules": [
    {"label": "CLIENT_ID", "pattern": "CLT-[0-9]{6}"},
    {"label": "DOSSIER", "pattern": "[A-Z]{2}[0-9]{5}", "context": ["dossier"], "window": [48, 16]},
    {"label": "COMMANDE", "pattern": "[0-9]{6}", "action": "keep", "context": ["commande"]}
  ],
  "deny": {"PROJET": ["Opération Phénix"]},
  "allow": ["support@acme.fr"]
}
```

| Champ | Rôle |
|---|---|
| `label` | libellé de la balise, en majuscules : `CLIENT_ID` donne `[CLIENT_ID_1]` |
| `pattern` | expression régulière ; macros `{S}` (séparateur facultatif) et `{SEP}` des packs |
| `action` | `mask` (défaut) ou `keep` (conserver en clair) |
| `context` | mots-clés exigés à proximité (facultatif) ; `window` = `[avant, après]` en caractères |
| `case_sensitive`, `whole_word` | casse respectée (défaut : non) ; mot entier (défaut : oui) |
| `deny` | termes exacts toujours masqués, par libellé |
| `allow` | termes exacts jamais masqués |

Règles de priorité, simples et explicables :
- une règle `mask` passe devant les heuristiques, jamais devant un identifiant validé par sa clé ;
- une règle `keep` conserve les détections **entièrement comprises** dans sa correspondance ; une détection
  qui déborde reste masquée, et un identifiant officiel validé (NIR, IBAN, carte, passeport, numéro fiscal…)
  n'est **jamais** démasqué ;
- une zone gardée par une règle `keep` l'emporte aussi sur tout ce que le filtre fort 1.0.2 ajoute : la règle des
  codes (`ID_CODE`), les longues suites de chiffres (`ID_LONG_NUMBER`), les nombres après un libellé et la
  propagation des valeurs (une valeur masquée ailleurs n'est jamais reportée dans une zone gardée) ;
- `allow` l'emporte sur tout le reste pour le terme exact.

**Garder des codes de structure précise.** Par défaut, tout code fait de lettres et de chiffres (6 caractères au
moins, factures, commandes, produits, lots et SKU compris) et toute suite nue de 8 chiffres ou plus sont masqués
(§ 2, filtre fort : choix du propriétaire, aucune liste de préfixes métier n'est livrée). Une organisation garde
lisibles ses propres codes par une règle `keep` à motif précis :

```json
{"rules": [{"label": "SKU", "pattern": "SKU-[0-9]{6}", "action": "keep"}]}
```

« Article SKU-123456 pour le client CLT-204518. » devient « Article SKU-123456 pour le client [IDENTIFIANT_1]. » ;
`explain` porte la ligne `{"kept": "IDENTIFIANT", "rule": "CUSTOM_1_SKU", "reason": "keep_rule"}`. Des mots-clés
(`context`) restreignent la règle à un voisinage (« commande », « lot »). Une boîte fonctionnelle à garder s'écrit
dans `allow` (« support@acme.fr »).

> **EN.** Keep zones also win over everything the 1.0.2 strong filter adds (code rule, long numbers, numbers after a
> label, value propagation). By default every letter-and-digit code of 6 characters or more and every bare run of 8
> digits or more is masked, with no shipped list of business prefixes; an organisation keeps its own codes readable
> with a precise keep rule, e.g. `{"label": "SKU", "pattern": "SKU-[0-9]{6}", "action": "keep"}` keeps SKU-123456
> while CLT-204518 is masked.

Sûreté sur le service en ligne :
- motifs exécutés par le moteur d'expressions du noyau Rust, **à temps linéaire** et avec la sémantique
  exacte de `re` (`\w`, `\d`, `\s`, `re.IGNORECASE`) ;
- acceptées : les assertions de tête (un caractère avant la correspondance, comme `(?<![0-9])`, ou `\b`) et de
  fin (`(?=…)`, `(?!…)`, `$`, `\Z`, `\b`), y compris `$` en dernière position d'un look-ahead positif final ou
  d'une alternative finale (`(?=\s|$)`, `(?=$)`, `(?:$|\s)`, `(?=[.,;]|$)`) et `(?=\b)` ;
- refusées avec la raison : les assertions au milieu du motif, un `$` suivi d'autre chose (`(?!$\n)`),
  plusieurs assertions finales positives combinées (`\b(?=\s)`), les assertions arrière de plusieurs caractères
  (`(?<=n°)`) et les références arrière (`\1`) ;
- compilation bornée : 2 Mo par motif (ses deux expressions comprises quand il commence par `\b` ou une
  assertion arrière), 16 Mo pour tout le jeu, sur un seul fil ; au-delà, la règle est refusée avant d'allouer
  (repère : `\w` répété 45 fois au plus, 20 fois après `\b` ; `\w+` ou `[A-Z0-9]{2,40}` restent légers) ;
- l'accueil du service ne contrôle que la structure (nombre de règles, longueurs, libellés) : les motifs sont
  compilés dans le processus isolé de la requête, sous son plafond mémoire et son échéance. Un motif refusé
  donne la même erreur 422 `invalid_request` (« Règle n°1 (LIBELLÉ) : construction refusée par le moteur
  linéaire : raison »). Pour un envoi hors bande, `POST /v1/uploads` (et `create_upload`)
  compile les motifs dans un travailleur avant que le fichier parte : l'erreur tombe dès la création de l'envoi.
  Un motif malveillant ne peut donc pas bloquer le serveur : il ne coûte que son propre processus, borné ;
- 20 règles au plus, 500 caractères par motif, 500 termes par liste ;
- le jeu de règles est **compilé pour la requête puis jeté** : jamais en cache, jamais journalisé (un motif
  peut contenir un nom). Pour un usage récurrent, le client le garde de son côté (fichier du projet) et
  l'envoie à chaque appel.

> **EN.** Online service safety: patterns run on the Rust core's linear-time engine with `re`'s exact
> semantics. Accepted: leading assertions (one character before the match, `\b`) and trailing ones (`(?=…)`,
> `(?!…)`, `$`, `\Z`, `\b`), including `$` last in a final positive look-ahead or a final alternation
> (`(?=\s|$)`, `(?=$)`, `(?:$|\s)`, `(?=[.,;]|$)`) and `(?=\b)`. Refused with the reason: assertions inside the
> pattern, a `$` followed by anything (`(?!$\n)`), combined positive trailing assertions (`\b(?=\s)`),
> multi-character look-behinds and backreferences. Bounded compile: 2 MB per pattern (both its expressions when
> it starts with `\b` or a look-behind), 16 MB for the whole set, one thread; beyond that the rule is refused
> before allocating (about 45 repetitions of `\w`, 20 after `\b`). The service front only checks the structure
> (rule count, lengths, labels); patterns are compiled in the request's isolated process, under its memory cap
> and deadline, and a refused pattern gives the same 422 `invalid_request` ("Rule #1 (LABEL): refused by the
> linear-time engine: reason"). For an out-of-band upload, `POST /v1/uploads` (and `create_upload`) compiles
> the patterns in a worker before the file leaves: the error comes at upload creation. A
> malicious pattern therefore cannot block the server: it only costs its own bounded process.

En local, un fichier TOML a les mêmes clés (`[[rule]]` pour chaque règle) :
`Anonymizer(rules="acme.toml")`.

## 4. Expliquer chaque balise : `explain`

Avec `explain=true`, le rapport contient une ligne par balise et par raison, **jamais la valeur d'origine** :

```json
{"tag": "[NIR_1]", "rule": "FR_NIR", "reason": "validated", "count": 1}
{"tag": "[CLIENT_ID_1]", "rule": "CUSTOM_1_CLIENT_ID", "reason": "custom_rule", "count": 1}
{"kept": "ORG", "rule": "ORGANIZATIONS", "reason": "company_policy", "count": 1}
```

| Raison | Signification |
|---|---|
| `validated` | clé de contrôle ou règles officielles vérifiées (NIR, IBAN, plan de numérotation, calendrier…) |
| `validated_and_keyword` | idem, et un mot-clé exigé était présent |
| `keyword` | format reconnu près d'un mot-clé exigé |
| `format` | format structurel (e-mail, IP, URL de profil…) |
| `keyword_despite_invalid_key` | clé fausse, mais mot-clé explicite (faute de frappe, OCR) |
| `printed_layout` | clé fausse, mais format imprimé caractéristique (NIR 1-2-2-2-3-3-2, carte 4-4-4-4) |
| `iban_layout_despite_invalid_key` | IBAN à clé fausse, écrit par blocs de 4 ou près d'un mot-clé |
| `phone_numbering_plan` | numéro international validé par son plan de numérotation ; depuis 1.0.2, numéro français compact (10 chiffres collés) masqué sans mot-clé |
| `identifier_code` | code d'identifiant (lettres et chiffres, 6 caractères au moins, quel que soit son préfixe) hors exclusion nommée (§ 2, filtre fort) |
| `long_number` | suite nue de 8 chiffres ou plus, hors montant, date compacte et balise (§ 2, filtre fort, `ID_LONG_NUMBER`) |
| `output_check` | contrôle final de sortie : autre occurrence, collée à un mot, d'une valeur déjà masquée (chiffre ou « @ », 6 caractères au moins), même balise (§ 2, « Contrôle final de sortie ») |
| `phone_fragment` | fin d'un numéro de téléphone annoncée par un mot de téléphone (« le numéro finissant par 59 65 ») |
| `name_lexicon` | prénom ou nom des fichiers Insee, avec indice (civilité, salutation, rôle, étiquette…) |
| `postcode_and_town` | adresse : code postal et commune vérifiés ensemble |
| `street_and_number` | adresse sans code postal : voie numérotée (« 6 rue des Essais », suivie ou non d'une commune connue) |
| `street_after_home_word` | adresse sans code postal : voie après un mot de domicile (« Nous habitons Petite Route de la Gare ») |
| `named_place` | adresse sans code postal : lieu-dit et son nom (« lieu dit La Croix Blanche ») |
| `sole_trader` | numéro d'entreprise (SIREN, SIRET, RCS, RM…) d'un entrepreneur individuel nommé dans le document |
| `civil_status_nearby` | numéro d'entreprise à côté de l'état civil d'une personne physique (§ 2) |
| `no_legal_entity` | champ « n° RCS : » ou « n° RM : » d'un avis qui ne nomme aucune personne morale (§ 2) |
| `legal_form` | organisation repérée par sa forme juridique |
| `matches_nir` | date de naissance cohérente avec un NIR du document |
| `propagation` | autre occurrence d'une valeur déjà détectée ; depuis 1.0.2, toute graphie de la valeur (nom replié, date, téléphone, code), § 2 filtre fort |
| `signature` | ligne de signature en minuscules égale au prénom ou au nom d'une seule personne déjà masquée (§ 2, filtre fort) |
| `initials_after_cue` | initiales d'une personne après un indice (« rédigée par NB », « visa : F.L. »), sigles courants exclus (§ 2, filtre fort) |
| `custom_rule` | règle de l'organisation |
| `deny_list` | terme imposé par l'organisation |
| `ner_model` | modèle NER local (option) |
| `company_policy` (conservé) | identifiant d'entreprise ou organisation conservés par politique |
| `keep_rule` (conservé) | conservé par une règle `keep` de l'organisation ; l'emporte aussi sur la règle des codes, les longues suites de chiffres et la propagation des valeurs (§ 3) |

## 5. Limites connues

- Les noms et adresses ne sont détectés que par les lexiques **français** : sans le pays FR (`countries`), aucun
  nom ni adresse n'est masqué, et le rapport le signale (`warnings`).
- Un nom en minuscules **sans aucun indice** (« (guillaume martin, tél …) ») peut passer : cas typique d'une
  règle d'organisation (`deny`) ou du NER local.
- Les champs `Nom :` et `Prénom :` d'un même formulaire reçoivent aujourd'hui deux balises distinctes.
- Les éléments de contexte (fonction rare, événement, lieu précis) peuvent permettre une ré-identification
  indirecte : ils ne sont pas des identifiants et restent en clair.
- Code postal et ville seuls après « Adresse : » ou « Adresse de livraison : » restent en clair (§ 2) : seuls un mot
  de domicile (« domicilié », « demeurant », « réside », « habite ») ou une étiquette d'adresse qui nomme une personne
  (« Adresse du salarié : », règle ADDRESS_LABEL, 1.0.2) les font masquer. Une organisation qui veut les masquer
  toujours ajoute une règle (§ 3).
- Règle GAP (couche 0) : une tabulation ou 2 à 4 blancs entre deux caractères alphanumériques dont un chiffre, et
  un seul saut de ligne (LF ou CRLF) entre deux chiffres, deviennent une espace dans le texte de détection. La règle
  BREAK recolle aussi un courriel ou un IBAN coupé, un numéro prouvé (téléphone, IPv4, SIREN, SIRET, NIR, RIB) ou une
  plaque, et lit deux groupes alphanumériques coupés comme un seul numéro ; une voie coupée après son type ou après une
  particule continue sur la ligne suivante. Un saut de ligne entre deux lettres d'un nom (« Jean\nDupont »,
  « Bo\nnneau ») reste une coupure : un nom coupé par la mise en page peut encore fuir, comme une carte d'identité de
  12 chiffres sans clé (rien ne distingue « mot⏎mot » d'une fin de ligne ordinaire sans risquer de fusionner deux
  lignes). Les textes Windows (fins de ligne CRLF) sont traités comme les autres.
- Un nom écrit tout en minuscules (« denise germain ») n'est masqué qu'après un indice fort (§ 1, couche 4 et
  heuristiques), sauf, depuis 1.0.2, une autre graphie d'un nom de plusieurs mots déjà trouvé (propagation repliée)
  et une ligne de signature égale au prénom ou au nom d'une personne masquée (§ 2) ; un prénom seul en minuscules
  dans la prose, sans mention antérieure, peut encore passer. « M. Le Floch » et « Mme Le Floch » d'un couple
  reçoivent la même balise.
- Propagation des valeurs (1.0.2) : une date ordinaire égale à une date de naissance du document est masquée avec
  elle, même quand cette date de naissance a été reconnue par simple proximité d'un indice (rappel d'abord).
- Un nom de personne écrit sur la même ligne que le code postal, sans séparateur (« Claire Dubois 69003 Lyon »),
  est lu comme un lieu-dit et masqué avec l'adresse (« [ADRESSE_1] ») : rien ne fuit, mais la balise est celle
  d'une adresse.
- Filtre fort 1.0.2, échange assumé : dans un texte technique, les noms de fichier, les codes d'un chemin d'URL, les
  empreintes (hash) et les décorateurs de code (`@property`) qui ont la forme d'un identifiant sont masqués
  (`ID_CODE`, `HANDLE`) ; tout numéro de commande, de facture, de devis, de suivi, de lot et toute référence
  produit qui porte lettres et chiffres aussi (choix du propriétaire : « on anonymise tout code »), comme toute
  suite nue de 8 chiffres ou plus qui n'est ni un montant ni une date compacte (une population, un nombre de
  secondes écrits sans unité). Une organisation qui veut en garder un ajoute une règle `keep` (§ 3).

Les taux mesurés (corpus de 1 000 documents, jeux publics) sont publiés dans `docs/EVALUATION.md`.
