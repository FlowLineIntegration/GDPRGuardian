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
| 2 | Identifiants à clé faible | SIREN, IMEI, téléphone compact | la clé est valide **et** un mot-clé est proche |
| 3 | Identifiants sans clé | passeport, carte d'identité, permis, n° client, matricule, RPPS, IPP, date de naissance | un mot-clé est proche (« Passeport : », « né le », « N° client ») ; les groupes peuvent être regroupés librement, séparés par une espace, un point, un tiret, un tiret demi-cadratin ou « / » (« 42067 58727 49 », « 1044/37321/76 », téléphone « 0764 945 16 3 » près d'un mot de téléphone, mobile 06/07 seul ; carte bancaire, RIB, SIRET, numéro fiscal et TVA aussi, avec leur clé) : la valeur est alors toute la suite de groupes, jamais un morceau d'un numéro plus long (borne `group`), ou un libellé explicite juste avant la valeur (« RPPS 10001234567 », « matricule 004587 », « contrat n° 2024-778899 », groupes espacés compris : « police n° 778 899 120 ») ; une date d'événement placée entre « né le » et la date (« hospitalisé le », « ordonné le », « signé le »…) en fait une autre date, de même qu'un mot d'événement collé devant la date quand « né le » la suit (« hospitalisée le 14/09/2026, née le 12/03/1985 ») |
| 4 | Étiquettes de formulaire | `Nom :`, `Prénom :`, `Nom de naissance :`, `Adresse :`, `Date de naissance :`, `Tél :`, `Code banque :`, `Code guichet :`, `N° de compte :`, `Clé RIB :` | la valeur qui suit sur la ligne, même en minuscules, même inconnue des listes ; `Adresse :` en début de ligne : toute la valeur (service, bâtiment, voie, boîte, code postal, commune), sauf une valeur sans chiffre ou qui commence par un code postal ; la valeur s'arrête à « ; » et à une fin de phrase après la commune (« 12000 Rodez. Le dossier… »), le reste de la ligne revient aux autres détecteurs ; une ligne qui porte un autre champ sans fin de phrase avant lui garde l'ancien comportement (`FR_ADDRESS_FIELD`) ; `Tél :` en début de ligne : formes libres (« (+33) -05-65-75-80-00 »), à condition que la valeur ait les chiffres d'un seul numéro (« (+ » : 8 à 15 chiffres, forme libre des avis, outre-mer mal formé compris ; sinon « 0 » : 10 chiffres, « 00 » : 11 à 15, « 33 » : 10 à 13, autre : 9 à 13) ; deux numéros sur la ligne ou des chiffres de la ligne suivante reviennent aux détecteurs ordinaires (`FR_PHONE_FIELD`, validateur `fr.phone_field`) |
| 5 | Heuristiques de langue | noms (fichiers Insee + civilité, salutation, rôle, signature), adresses (code postal + commune vérifiés), organisations (formes juridiques) | l'indice ou la structure est présent |
| 6 | Structure du document | en-tête de colonne (tableau Markdown, Excel), propagation, coréférence | un nom trouvé une fois est masqué partout ; « M. Dupont » et « Jean Dupont » partagent la même balise |
| 7 | Règles de l'organisation | masquer, conserver, termes imposés, termes permis | voir § 3 |
| 8 | Sortie | nettoyage (caractères invisibles, images distantes), rapport `explain` | toujours |

Mots-clés, fenêtres et motifs vivent dans des **packs pays** déclaratifs (`src/gdprguardian/packs/data/*.toml`) :
FR par défaut, BE, LU, CH, MC, DE, ES, IT, NL, PT, et INTL toujours actif. Le pays se choisit explicitement
(`countries="FR"`, `"FR,BE"`) ; `"all"` active tous les packs ; `"auto"` reste expérimental.

## 2. Ce que Gardien RGPD conserve volontairement

Code postal et ville seuls, lieu de naissance, employeur et identifiants d'entreprise (une personne morale
n'est pas une donnée personnelle, sauf entrepreneur individuel), numéros de commande, montants, dates
ordinaires. Seuls, ils n'identifient personne et l'IA en a besoin pour comprendre le document. Une
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
- `allow` l'emporte sur tout le reste pour le terme exact.

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
| `phone_numbering_plan` | numéro international validé par son plan de numérotation |
| `name_lexicon` | prénom ou nom des fichiers Insee, avec indice (civilité, salutation, rôle, étiquette…) |
| `postcode_and_town` | adresse : code postal et commune vérifiés ensemble |
| `street_and_number` | adresse sans code postal : voie numérotée (« 6 rue des Essais », suivie ou non d'une commune connue) |
| `street_after_home_word` | adresse sans code postal : voie après un mot de domicile (« Nous habitons Petite Route de la Gare ») |
| `sole_trader` | numéro d'entreprise (SIREN, SIRET, RCS, RM…) d'un entrepreneur individuel nommé dans le document |
| `civil_status_nearby` | numéro d'entreprise à côté de l'état civil d'une personne physique (§ 2) |
| `no_legal_entity` | champ « n° RCS : » ou « n° RM : » d'un avis qui ne nomme aucune personne morale (§ 2) |
| `legal_form` | organisation repérée par sa forme juridique |
| `matches_nir` | date de naissance cohérente avec un NIR du document |
| `propagation` | autre occurrence d'une valeur déjà détectée |
| `custom_rule` | règle de l'organisation |
| `deny_list` | terme imposé par l'organisation |
| `ner_model` | modèle NER local (option) |
| `company_policy` (conservé) | identifiant d'entreprise ou organisation conservés par politique |
| `keep_rule` (conservé) | conservé par une règle `keep` de l'organisation |

## 5. Limites connues

- Les noms et adresses ne sont détectés que par les lexiques **français** : sans le pays FR (`countries`), aucun
  nom ni adresse n'est masqué, et le rapport le signale (`warnings`).
- Un nom en minuscules **sans aucun indice** (« (guillaume martin, tél …) ») peut passer : cas typique d'une
  règle d'organisation (`deny`) ou du NER local.
- Les champs `Nom :` et `Prénom :` d'un même formulaire reçoivent aujourd'hui deux balises distinctes.
- Les éléments de contexte (fonction rare, événement, lieu précis) peuvent permettre une ré-identification
  indirecte : ils ne sont pas des identifiants et restent en clair.
- Code postal et ville seuls après « Adresse : » ou « Adresse du salarié : » restent en clair (§ 2), même pour une
  personne : seul un mot de domicile (« domicilié », « demeurant », « réside », « habite ») les fait masquer. Une
  organisation qui veut les masquer toujours ajoute une règle (§ 3).
- Règle GAP (couche 0) : une tabulation ou 2 à 4 blancs entre deux caractères alphanumériques dont un chiffre, et
  un seul saut de ligne (LF ou CRLF) entre deux chiffres, deviennent une espace dans le texte de détection. La règle
  BREAK recolle aussi un courriel ou un IBAN coupé et lit deux groupes alphanumériques coupés comme un seul numéro.
  Un saut de ligne entre deux lettres (« Jean\nDupont », « 12 rue des\nLilas », « Bo\nnneau ») reste une coupure :
  un nom ou une adresse coupé par la mise en page peut encore fuir (rien ne distingue « mot⏎mot » d'une fin de ligne
  ordinaire sans risquer de fusionner deux lignes). Les textes Windows (fins de ligne CRLF) sont traités comme les
  autres.
- Un nom écrit tout en minuscules (« denise germain ») n'est masqué qu'après un indice fort (§ 1, couche 4 et
  heuristiques) ; « M. Le Floch » et « Mme Le Floch » d'un couple reçoivent la même balise.
- Un nom de personne écrit sur la même ligne que le code postal, sans séparateur (« Claire Dubois 69003 Lyon »),
  est lu comme un lieu-dit et masqué avec l'adresse (« [ADRESSE_1] ») : rien ne fuit, mais la balise est celle
  d'une adresse.

Les taux mesurés (corpus de 1 000 documents, jeux publics) sont publiés dans `docs/EVALUATION.md`.
