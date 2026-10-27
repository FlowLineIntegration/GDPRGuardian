# Corpus massif de test d’anonymisation RGPD : données entièrement fictives

> **Jeu de test synthétique.** Aucun dossier ne décrit une personne réelle. Les identités sont générées pour ce corpus, les domaines de courriel sont des domaines de test, les IP appartiennent à des plages de documentation, les téléphones utilisent un bloc réservé aux œuvres audiovisuelles, et les identifiants financiers/nationaux sont volontairement invalides ou réservés à des tests. Ne pas utiliser ces données pour une transaction, une authentification ou une prise de contact.
>
> **Objectif.** Évaluer un anonymiseur sur des textes français réalistes, mêlant champs structurés, narration, citations, tableaux Markdown, répétitions, variantes de casse, extraits bruités, données sensibles, quasi-identifiants et éléments non personnels à préserver.
>
> **Important.** Le fichier de vérité terrain est séparé dans le pack. Ne le fournissez pas à l’anonymiseur testé. Le corpus contient des contrôles négatifs explicitement non personnels dans leur contexte : leur suppression compte comme une sur-anonymisation. La qualification juridique d’une donnée dépend toujours du contexte, de la finalité et des possibilités de recoupement ; ce jeu est un banc d’essai technique, pas un avis juridique.

## Périmètre couvert

- Identité : noms et prénoms, variantes de casse, proches fictifs, pseudonymes.
- Coordonnées : adresses, emails individuels, téléphones et variantes internationales.
- Identifiants : numéros nationaux fictifs invalides, références client/salarié/dossier, IBAN invalide, carte de paiement de test, plaque de véhicule fictive.
- Traces numériques : IPv4/IPv6 de documentation, UUID, cookie, identifiants biométriques synthétiques.
- Données sensibles ou à risque : santé, handicap, opinions politiques fictives, croyance fictive, appartenance syndicale simulée, orientation sexuelle mentionnée dans un scénario, données judiciaires inventées, situation sociale.
- Quasi-identifiants : profession, rémunération, dates, organisation, petite localité fictive, parenté et recoupements.
- Contrôles négatifs : références de catalogue, lots de production, boîte fonctionnelle partagée et raison sociale générique.

## Corpus


## Cas 001 : RH / gestion du personnel | dossier fictif INC-2026-00017

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Sohan Clairclaire, née le 2010-01-01. Le dossier la rattache à 1, rue des Brumes, 99900 Val-des-Nuages, France. Son email est sohan.clairclaire00@example.invalid et son téléphone est 06 39 98 00 11; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 00 11. La fiche de contact porte le pseudonyme s.clairclaire_000. Le compte client est CLT-000001-Q, et la référence RH éventuelle est EMP-100101. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Clairclaire.

**Traitement du dossier.** Le 2025-01-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Maëlys Belaubier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 400,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 60 01 99 001 345 00. La domiciliation bancaire fictive indique FR00 1111 2222 3333 4444 5555 666, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.1; la trace IPv6 associée est 2001:db8:00::0. Le poste de travail porte l’identifiant 12345678-1234-4000-a000-0123456789ab, le cookie de test est cookie-demo-00001-00000, et le gabarit biométrique est BIO-DEMO-000007 (référence vocale distincte : VOICE-TEST-00001). Le véhicule mentionné est ZZ-000-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sohan Clairclaire et ajouté une note de suivi à CLT-000001-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient sohan CLAIRCLAIRE; vérifier que le changement de casse ne bloque pas la détection.

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 00 11. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2010-01-01. Le proche de référence est Maëlys Belaubier. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0042; la référence du lot est BATCH-OPS-2026-042. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sohan Clairclaire |
| Date | 2010-01-01 |
| Contact | sohan.clairclaire00@example.invalid |
| Client | CLT-000001-Q |
| Incident | INC-2026-00017 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0042 |

**Autre formulation observée.** Le message reçu disait : « Pour Sohan Clairclaire, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-00017. »


## Cas 002 : CRM / relation client | dossier fictif INC-2026-00058

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Lina Ormeplaine, née le 1970-06-14. Le dossier la rattache à 18, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est lina.ormeplaine01@example.invalid et son téléphone est 06 39 98 00 48; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 00 48. La fiche de contact porte le pseudonyme l.ormeplaine_023. Le compte client est CLT-000002-Q, et la référence RH éventuelle est EMP-100120. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Ormeplaine.

**Traitement du dossier.** Le 2026-04-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Younès Fauvevalon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 573,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 61 02 99 002 482 00. La domiciliation bancaire fictive indique FR00 1212 2335 3460 4575 5692 805, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.18; la trace IPv6 associée est 2001:db8:01::1f. Le poste de travail porte l’identifiant 12345689-123b-4001-a00d-0123456789ca, le cookie de test est cookie-demo-00002-00097, et le gabarit biométrique est BIO-DEMO-000060 (référence vocale distincte : VOICE-TEST-00002). Le véhicule mentionné est ZZ-037-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lina Ormeplaine et ajouté une note de suivi à CLT-000002-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0055; la référence du lot est BATCH-OPS-2026-059. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lina Ormeplaine |
| Date | 1970-06-14 |
| Contact | lina.ormeplaine01@example.invalid |
| Client | CLT-000002-Q |
| Incident | INC-2026-00058 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0055 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Lina Ormeplaine, identifiant CLT-000002-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 003 : Santé / prise de rendez-vous | dossier fictif INC-2026-00099

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Younès Pluvivelin, née le 1977-11-27. Le dossier la rattache à 35, rue des Nuages Bas, 99900 Mirebrise, France. Son email est younes.pluvivelin02@example.invalid et son téléphone est 06 39 98 00 85; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 00 85. La fiche de contact porte le pseudonyme y.pluvivelin_046. Le compte client est CLT-000003-Q, et la référence RH éventuelle est EMP-100139. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pluvivelin.

**Traitement du dossier.** Le 2025-07-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Inès Dorémeline, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 746,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 62 03 99 003 619 00. La domiciliation bancaire fictive indique FR00 1313 2448 3587 4706 5829 944, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.35; la trace IPv6 associée est 2001:db8:02::3e. Le poste de travail porte l’identifiant 1234569a-1242-4002-a01a-0123456789e9, le cookie de test est cookie-demo-00003-00194, et le gabarit biométrique est BIO-DEMO-000113 (référence vocale distincte : VOICE-TEST-00003). Le véhicule mentionné est ZZ-074-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Younès Pluvivelin et ajouté une note de suivi à CLT-000003-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0068; la référence du lot est BATCH-OPS-2026-076. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Younès Pluvivelin |
| Date | 1977-11-27 |
| Contact | younes.pluvivelin02@example.invalid |
| Client | CLT-000003-Q |
| Incident | INC-2026-00099 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0068 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Younès Pluvivelin, 06 39 98 00 85, younes.pluvivelin02@example.invalid; le rappel est prévu autour du 2025-07-15.”


## Cas 004 : Banque / assurance | dossier fictif INC-2026-00140

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Apolline Nacreclairon, née le 1984-04-13. Le dossier la rattache à 52, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est apolline.nacreclairon03@example.invalid et son téléphone est 06 39 98 01 22; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 01 22. La fiche de contact porte le pseudonyme a.nacreclairon_069. Le compte client est CLT-000004-Q, et la référence RH éventuelle est EMP-100158. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nacreclairon.

**Traitement du dossier.** Le 2026-10-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Anaïs Corvivalise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 919,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 63 04 99 004 756 00. La domiciliation bancaire fictive indique FR00 1414 2561 3714 4837 5966 083, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.52; la trace IPv6 associée est 2001:db8:03::5d. Le poste de travail porte l’identifiant 123456ab-1249-4003-a027-012345678a08, le cookie de test est cookie-demo-00004-00291, et le gabarit biométrique est BIO-DEMO-000166 (référence vocale distincte : VOICE-TEST-00004). Le véhicule mentionné est ZZ-111-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Apolline Nacreclairon et ajouté une note de suivi à CLT-000004-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0081; la référence du lot est BATCH-OPS-2026-093. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Apolline Nacreclairon |
| Date | 1984-04-13 |
| Contact | apolline.nacreclairon03@example.invalid |
| Client | CLT-000004-Q |
| Incident | INC-2026-00140 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0081 |

**Autre formulation observée.** Note d’audit : le lien entre a.nacreclairon_069, 192.0.2.52 et 123456ab-1249-4003-a027-012345678a08 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 005 : Éducation / accompagnement | dossier fictif INC-2026-00181

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Romane Perrivigne, née le 1991-09-26. Le dossier la rattache à 69, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est romane.perrivigne04@example.invalid et son téléphone est 06 39 98 01 59; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 01 59. La fiche de contact porte le pseudonyme r.perrivigne_092. Le compte client est CLT-000005-Q, et la référence RH éventuelle est EMP-100177. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Perrivigne.

**Traitement du dossier.** Le 2025-01-02, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Clémence Lisirune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 092,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 64 05 99 005 893 00. La domiciliation bancaire fictive indique FR00 1515 2674 3841 4968 6103 222, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.69; la trace IPv6 associée est 2001:db8:04::7c. Le poste de travail porte l’identifiant 123456bc-1250-4004-a034-012345678a27, le cookie de test est cookie-demo-00005-00388, et le gabarit biométrique est BIO-DEMO-000219 (référence vocale distincte : VOICE-TEST-00005). Le véhicule mentionné est ZZ-148-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Romane Perrivigne et ajouté une note de suivi à CLT-000005-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0094; la référence du lot est BATCH-OPS-2026-110. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Romane Perrivigne |
| Date | 1991-09-26 |
| Contact | romane.perrivigne04@example.invalid |
| Client | CLT-000005-Q |
| Incident | INC-2026-00181 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0094 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 006 : Juridique / contrat | dossier fictif INC-2026-00222

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Ambre Pavofleur, née le 1998-02-12. Le dossier la rattache à 86, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est ambre.pavofleur05@example.invalid et son téléphone est 06 39 98 01 96; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 01 96. La fiche de contact porte le pseudonyme a.pavofleur_115. Le compte client est CLT-000006-Q, et la référence RH éventuelle est EMP-100196. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pavofleur.

**Traitement du dossier.** Le 2026-04-09, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Eden Lorimurel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 265,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 65 06 99 006 030 00. La domiciliation bancaire fictive indique FR00 1616 2787 3968 5099 6240 361, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.86; la trace IPv6 associée est 2001:db8:05::9b. Le poste de travail porte l’identifiant 123456cd-1257-4005-a041-012345678a46, le cookie de test est cookie-demo-00006-00485, et le gabarit biométrique est BIO-DEMO-000272 (référence vocale distincte : VOICE-TEST-00006). Le véhicule mentionné est ZZ-185-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ambre Pavofleur et ajouté une note de suivi à CLT-000006-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ambre PAVOFLEUR; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0107; la référence du lot est BATCH-OPS-2026-127. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ambre Pavofleur |
| Date | 1998-02-12 |
| Contact | ambre.pavofleur05@example.invalid |
| Client | CLT-000006-Q |
| Incident | INC-2026-00222 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0107 |

**Autre formulation observée.** Version importée : Ambre Pavofleur; date=1998-02-12; rue=86, rue des Brumes, 99900 Soleil-des-Falaises, France; téléphone=06 39 98 01 96; courriel=ambre.pavofleur05@example.invalid; statut=à contrôler.


## Cas 007 : Support informatique | dossier fictif INC-2026-00263

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Théo Noroorée, née le 2005-07-25. Le dossier la rattache à 103, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est theo.norooree06@example.invalid et son téléphone est 06 39 98 02 33; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 02 33. La fiche de contact porte le pseudonyme t.noroorée_138. Le compte client est CLT-000007-Q, et la référence RH éventuelle est EMP-100215. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Noroorée.

**Traitement du dossier.** Le 2025-07-16, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Léonie Briscendre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 438,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 66 07 99 007 167 00. La domiciliation bancaire fictive indique FR00 1717 2900 4095 5230 6377 500, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.103; la trace IPv6 associée est 2001:db8:06::ba. Le poste de travail porte l’identifiant 123456de-125e-4006-a04e-012345678a65, le cookie de test est cookie-demo-00007-00582, et le gabarit biométrique est BIO-DEMO-000325 (référence vocale distincte : VOICE-TEST-00007). Le véhicule mentionné est ZZ-222-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Théo Noroorée et ajouté une note de suivi à CLT-000007-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0120; la référence du lot est BATCH-OPS-2026-144. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Théo Noroorée |
| Date | 2005-07-25 |
| Contact | theo.norooree06@example.invalid |
| Client | CLT-000007-Q |
| Incident | INC-2026-00263 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0120 |

**Autre formulation observée.** Le message reçu disait : « Pour Théo Noroorée, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-00263. »


## Cas 008 : Voyage / réservation | dossier fictif INC-2026-00304

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Naël Rosibrise, née le 1969-12-11. Le dossier la rattache à 120, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est nael.rosibrise07@example.invalid et son téléphone est 06 39 98 02 70; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 02 70. La fiche de contact porte le pseudonyme n.rosibrise_161. Le compte client est CLT-000008-Q, et la référence RH éventuelle est EMP-100234. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rosibrise.

**Traitement du dossier.** Le 2026-10-23, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Romane Lunémistral, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 611,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 67 08 99 008 304 00. La domiciliation bancaire fictive indique FR00 1818 3013 4222 5361 6514 639, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.120; la trace IPv6 associée est 2001:db8:07::d9. Le poste de travail porte l’identifiant 123456ef-1265-4007-a05b-012345678a84, le cookie de test est cookie-demo-00008-00679, et le gabarit biométrique est BIO-DEMO-000378 (référence vocale distincte : VOICE-TEST-00008). Le véhicule mentionné est ZZ-259-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Naël Rosibrise et ajouté une note de suivi à CLT-000008-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 02 70. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0133; la référence du lot est BATCH-OPS-2026-161. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Naël Rosibrise |
| Date | 1969-12-11 |
| Contact | nael.rosibrise07@example.invalid |
| Client | CLT-000008-Q |
| Incident | INC-2026-00304 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0133 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Naël Rosibrise, identifiant CLT-000008-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 009 : Marketing / consentement | dossier fictif INC-2026-00345

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Titouan Solravel, née le 1976-05-24. Le dossier la rattache à 137, rue du Phare Éteint, 99900 Pluviane, France. Son email est titouan.solravel08@example.invalid et son téléphone est 06 39 98 03 07; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 03 07. La fiche de contact porte le pseudonyme t.solravel_184. Le compte client est CLT-000009-Q, et la référence RH éventuelle est EMP-100253. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Solravel.

**Traitement du dossier.** Le 2025-01-03, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Mélina Épilune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 784,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 68 09 99 009 441 00. La domiciliation bancaire fictive indique FR00 1919 3126 4349 5492 6651 778, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.137; la trace IPv6 associée est 2001:db8:08::f8. Le poste de travail porte l’identifiant 12345700-126c-4008-a068-012345678aa3, le cookie de test est cookie-demo-00009-00776, et le gabarit biométrique est BIO-DEMO-000431 (référence vocale distincte : VOICE-TEST-00009). Le véhicule mentionné est ZZ-296-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Titouan Solravel et ajouté une note de suivi à CLT-000009-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0146; la référence du lot est BATCH-OPS-2026-178. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Titouan Solravel |
| Date | 1976-05-24 |
| Contact | titouan.solravel08@example.invalid |
| Client | CLT-000009-Q |
| Incident | INC-2026-00345 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0146 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Titouan Solravel, 06 39 98 03 07, titouan.solravel08@example.invalid; le rappel est prévu autour du 2025-01-03.”


## Cas 010 : Recherche / enquête | dossier fictif INC-2026-00386

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Inès Avelroche, née le 2011-10-10. Le dossier la rattache à 154, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est ines.avelroche09@example.invalid et son téléphone est 06 39 98 03 44; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 03 44. La fiche de contact porte le pseudonyme i.avelroche_207. Le compte client est CLT-000010-Q, et la référence RH éventuelle est EMP-100272. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Avelroche.

**Traitement du dossier.** Le 2026-04-10, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Bastien Florilacier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 957,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 69 10 99 010 578 00. La domiciliation bancaire fictive indique FR00 2020 3239 4476 5623 6788 917, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.154; la trace IPv6 associée est 2001:db8:09::117. Le poste de travail porte l’identifiant 12345711-1273-4009-a075-012345678ac2, le cookie de test est cookie-demo-00010-00873, et le gabarit biométrique est BIO-DEMO-000484 (référence vocale distincte : VOICE-TEST-00010). Le véhicule mentionné est ZZ-333-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Inès Avelroche et ajouté une note de suivi à CLT-000010-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2011-10-10. Le proche de référence est Bastien Florilacier. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0159; la référence du lot est BATCH-OPS-2026-195. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Inès Avelroche |
| Date | 2011-10-10 |
| Contact | ines.avelroche09@example.invalid |
| Client | CLT-000010-Q |
| Incident | INC-2026-00386 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0159 |

**Autre formulation observée.** Note d’audit : le lien entre i.avelroche_207, 192.0.2.154 et 12345711-1273-4009-a075-012345678ac2 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 011 : Logistique / livraison | dossier fictif INC-2026-00427

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Mila Tremlombre, née le 1990-03-23. Le dossier la rattache à 171, rue des Brumes, 99900 Cendrelac, France. Son email est mila.tremlombre10@example.invalid et son téléphone est 06 39 98 03 81; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 03 81. La fiche de contact porte le pseudonyme m.tremlombre_230. Le compte client est CLT-000011-Q, et la référence RH éventuelle est EMP-100291. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Tremlombre.

**Traitement du dossier.** Le 2025-07-17, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Salomé Orielserein, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 130,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 70 11 99 011 715 00. La domiciliation bancaire fictive indique FR00 2121 3352 4603 5754 6925 056, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.171; la trace IPv6 associée est 2001:db8:0a::136. Le poste de travail porte l’identifiant 12345722-127a-4000-a082-012345678ae1, le cookie de test est cookie-demo-00011-00970, et le gabarit biométrique est BIO-DEMO-000537 (référence vocale distincte : VOICE-TEST-00011). Le véhicule mentionné est ZZ-370-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mila Tremlombre et ajouté une note de suivi à CLT-000011-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient mila TREMLOMBRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0172; la référence du lot est BATCH-OPS-2026-212. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mila Tremlombre |
| Date | 1990-03-23 |
| Contact | mila.tremlombre10@example.invalid |
| Client | CLT-000011-Q |
| Incident | INC-2026-00427 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0172 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 012 : Sécurité / contrôle d’accès | dossier fictif INC-2026-00468

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Mélina Varnedorin, née le 1997-08-09. Le dossier la rattache à 8, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est melina.varnedorin11@example.invalid et son téléphone est 06 39 98 04 18; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 04 18. La fiche de contact porte le pseudonyme m.varnedorin_253. Le compte client est CLT-000012-Q, et la référence RH éventuelle est EMP-100310. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Varnedorin.

**Traitement du dossier.** Le 2026-10-24, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Eliott Érablefarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 303,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 71 12 99 012 852 00. La domiciliation bancaire fictive indique FR00 2222 3465 4730 5885 7062 195, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.188; la trace IPv6 associée est 2001:db8:0b::155. Le poste de travail porte l’identifiant 12345733-1281-4001-a08f-012345678b00, le cookie de test est cookie-demo-00012-01067, et le gabarit biométrique est BIO-DEMO-000590 (référence vocale distincte : VOICE-TEST-00012). Le véhicule mentionné est ZZ-407-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mélina Varnedorin et ajouté une note de suivi à CLT-000012-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0185; la référence du lot est BATCH-OPS-2026-229. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mélina Varnedorin |
| Date | 1997-08-09 |
| Contact | melina.varnedorin11@example.invalid |
| Client | CLT-000012-Q |
| Incident | INC-2026-00468 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0185 |

**Autre formulation observée.** Version importée : Mélina Varnedorin; date=1997-08-09; rue=8, allée des Sept Lanternes, 99900 Églan-sur-Roche, France; téléphone=06 39 98 04 18; courriel=melina.varnedorin11@example.invalid; statut=à contrôler.


## Cas 013 : RH / gestion du personnel | dossier fictif INC-2026-00509

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Maël Célvaux, née le 2004-01-22. Le dossier la rattache à 25, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est mael.celvaux12@example.invalid et son téléphone est 06 39 98 04 55; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 04 55. La fiche de contact porte le pseudonyme m.célvaux_276. Le compte client est CLT-000013-Q, et la référence RH éventuelle est EMP-100329. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Célvaux.

**Traitement du dossier.** Le 2025-01-04, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Ariane Valnette, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 476,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 72 01 99 013 989 00. La domiciliation bancaire fictive indique FR00 2323 3578 4857 6016 7199 334, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.205; la trace IPv6 associée est 2001:db8:0c::174. Le poste de travail porte l’identifiant 12345744-1288-4002-a09c-012345678b1f, le cookie de test est cookie-demo-00013-01164, et le gabarit biométrique est BIO-DEMO-000643 (référence vocale distincte : VOICE-TEST-00013). Le véhicule mentionné est ZZ-444-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maël Célvaux et ajouté une note de suivi à CLT-000013-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0198; la référence du lot est BATCH-OPS-2026-246. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maël Célvaux |
| Date | 2004-01-22 |
| Contact | mael.celvaux12@example.invalid |
| Client | CLT-000013-Q |
| Incident | INC-2026-00509 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0198 |

**Autre formulation observée.** Le message reçu disait : « Pour Maël Célvaux, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-00509. »


## Cas 014 : CRM / relation client | dossier fictif INC-2026-00550

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Célestin Seredorelle, née le 1968-06-08. Le dossier la rattache à 42, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est celestin.seredorelle13@example.invalid et son téléphone est 06 39 98 04 92; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 04 92. La fiche de contact porte le pseudonyme c.seredorelle_299. Le compte client est CLT-000014-Q, et la référence RH éventuelle est EMP-100348. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Seredorelle.

**Traitement du dossier.** Le 2026-04-11, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Théo Mirasorel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 649,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 73 02 99 014 126 00. La domiciliation bancaire fictive indique FR00 2424 3691 4984 6147 7336 473, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.222; la trace IPv6 associée est 2001:db8:0d::193. Le poste de travail porte l’identifiant 12345755-128f-4003-a0a9-012345678b3e, le cookie de test est cookie-demo-00014-01261, et le gabarit biométrique est BIO-DEMO-000696 (référence vocale distincte : VOICE-TEST-00014). Le véhicule mentionné est ZZ-481-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Célestin Seredorelle et ajouté une note de suivi à CLT-000014-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0211; la référence du lot est BATCH-OPS-2026-263. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Célestin Seredorelle |
| Date | 1968-06-08 |
| Contact | celestin.seredorelle13@example.invalid |
| Client | CLT-000014-Q |
| Incident | INC-2026-00550 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0211 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Célestin Seredorelle, identifiant CLT-000014-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 015 : Santé / prise de rendez-vous | dossier fictif INC-2026-00591

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Léandre Églanbelle, née le 1975-11-21. Le dossier la rattache à 59, rue des Pivoines Grises, 99900 Valmousse, France. Son email est leandre.eglanbelle14@example.invalid et son téléphone est 06 39 98 05 29; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 05 29. La fiche de contact porte le pseudonyme l.églanbelle_322. Le compte client est CLT-000015-Q, et la référence RH éventuelle est EMP-100367. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Églanbelle.

**Traitement du dossier.** Le 2025-07-18, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Célestin Brumemarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 822,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 74 03 99 015 263 00. La domiciliation bancaire fictive indique FR00 2525 3804 5111 6278 7473 612, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.239; la trace IPv6 associée est 2001:db8:0e::1b2. Le poste de travail porte l’identifiant 12345766-1296-4004-a0b6-012345678b5d, le cookie de test est cookie-demo-00015-01358, et le gabarit biométrique est BIO-DEMO-000749 (référence vocale distincte : VOICE-TEST-00015). Le véhicule mentionné est ZZ-518-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léandre Églanbelle et ajouté une note de suivi à CLT-000015-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 05 29. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0224; la référence du lot est BATCH-OPS-2026-280. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léandre Églanbelle |
| Date | 1975-11-21 |
| Contact | leandre.eglanbelle14@example.invalid |
| Client | CLT-000015-Q |
| Incident | INC-2026-00591 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0224 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Léandre Églanbelle, 06 39 98 05 29, leandre.eglanbelle14@example.invalid; le rappel est prévu autour du 2025-07-18.”


## Cas 016 : Banque / assurance | dossier fictif INC-2026-00632

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Nora Rivbrume, née le 1982-04-07. Le dossier la rattache à 76, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est nora.rivbrume15@example.invalid et son téléphone est 06 39 98 05 66; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 05 66. La fiche de contact porte le pseudonyme n.rivbrume_345. Le compte client est CLT-000016-Q, et la référence RH éventuelle est EMP-100386. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rivbrume.

**Traitement du dossier.** Le 2026-10-25, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Ilyan Mélidune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 995,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 75 04 99 016 400 00. La domiciliation bancaire fictive indique FR00 2626 3917 5238 6409 7610 751, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.3; la trace IPv6 associée est 2001:db8:0f::1d1. Le poste de travail porte l’identifiant 12345777-129d-4005-a0c3-012345678b7c, le cookie de test est cookie-demo-00016-01455, et le gabarit biométrique est BIO-DEMO-000802 (référence vocale distincte : VOICE-TEST-00016). Le véhicule mentionné est ZZ-555-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nora Rivbrume et ajouté une note de suivi à CLT-000016-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient nora RIVBRUME; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0237; la référence du lot est BATCH-OPS-2026-297. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nora Rivbrume |
| Date | 1982-04-07 |
| Contact | nora.rivbrume15@example.invalid |
| Client | CLT-000016-Q |
| Incident | INC-2026-00632 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0237 |

**Autre formulation observée.** Note d’audit : le lien entre n.rivbrume_345, 192.0.2.3 et 12345777-129d-4005-a0c3-012345678b7c doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 017 : Éducation / accompagnement | dossier fictif INC-2026-00673

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Anaïs Alouloriot, née le 1989-09-20. Le dossier la rattache à 93, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est anais.alouloriot16@example.invalid et son téléphone est 06 39 98 06 03; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 06 03. La fiche de contact porte le pseudonyme a.alouloriot_368. Le compte client est CLT-000017-Q, et la référence RH éventuelle est EMP-100405. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Alouloriot.

**Traitement du dossier.** Le 2025-01-05, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Lucile Vanisac, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 168,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 76 05 99 017 537 00. La domiciliation bancaire fictive indique FR00 2727 4030 5365 6540 7747 890, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.20; la trace IPv6 associée est 2001:db8:10::1f0. Le poste de travail porte l’identifiant 12345788-12a4-4006-a0d0-012345678b9b, le cookie de test est cookie-demo-00017-01552, et le gabarit biométrique est BIO-DEMO-000855 (référence vocale distincte : VOICE-TEST-00017). Le véhicule mentionné est ZZ-592-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Anaïs Alouloriot et ajouté une note de suivi à CLT-000017-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0250; la référence du lot est BATCH-OPS-2026-314. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Anaïs Alouloriot |
| Date | 1989-09-20 |
| Contact | anais.alouloriot16@example.invalid |
| Client | CLT-000017-Q |
| Incident | INC-2026-00673 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0250 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 018 : Juridique / contrat | dossier fictif INC-2026-00714

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Jade Belaubier, née le 1996-02-06. Le dossier la rattache à 110, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est jade.belaubier17@example.invalid et son téléphone est 06 39 98 06 40; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 06 40. La fiche de contact porte le pseudonyme j.belaubier_391. Le compte client est CLT-000018-Q, et la référence RH éventuelle est EMP-100424. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Belaubier.

**Traitement du dossier.** Le 2026-04-12, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Gabin Aurimousse, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 341,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 77 06 99 018 674 00. La domiciliation bancaire fictive indique FR00 2828 4143 5492 6671 7884 029, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.37; la trace IPv6 associée est 2001:db8:11::20f. Le poste de travail porte l’identifiant 12345799-12ab-4007-a0dd-012345678bba, le cookie de test est cookie-demo-00018-01649, et le gabarit biométrique est BIO-DEMO-000908 (référence vocale distincte : VOICE-TEST-00018). Le véhicule mentionné est ZZ-629-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Jade Belaubier et ajouté une note de suivi à CLT-000018-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0263; la référence du lot est BATCH-OPS-2026-331. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Jade Belaubier |
| Date | 1996-02-06 |
| Contact | jade.belaubier17@example.invalid |
| Client | CLT-000018-Q |
| Incident | INC-2026-00714 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0263 |

**Autre formulation observée.** Version importée : Jade Belaubier; date=1996-02-06; rue=110, rue des Nuages Bas, 99900 Noroît-les-Jardins, France; téléphone=06 39 98 06 40; courriel=jade.belaubier17@example.invalid; statut=à contrôler.


## Cas 019 : Support informatique | dossier fictif INC-2026-00755

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Bastien Fauvevalon, née le 2012-07-19. Le dossier la rattache à 127, rue du Phare Éteint, 99900 Nacréville, France. Son email est bastien.fauvevalon18@example.invalid et son téléphone est 06 39 98 06 77; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 06 77. La fiche de contact porte le pseudonyme b.fauvevalon_414. Le compte client est CLT-000019-Q, et la référence RH éventuelle est EMP-100443. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Fauvevalon.

**Traitement du dossier.** Le 2025-07-19, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Lina Montaroussin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 514,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 78 07 99 019 811 00. La domiciliation bancaire fictive indique FR00 2929 4256 5619 6802 8021 168, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.54; la trace IPv6 associée est 2001:db8:12::22e. Le poste de travail porte l’identifiant 123457aa-12b2-4008-a0ea-012345678bd9, le cookie de test est cookie-demo-00019-01746, et le gabarit biométrique est BIO-DEMO-000961 (référence vocale distincte : VOICE-TEST-00019). Le véhicule mentionné est ZZ-666-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Bastien Fauvevalon et ajouté une note de suivi à CLT-000019-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2012-07-19. Le proche de référence est Lina Montaroussin. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0276; la référence du lot est BATCH-OPS-2026-348. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Bastien Fauvevalon |
| Date | 2012-07-19 |
| Contact | bastien.fauvevalon18@example.invalid |
| Client | CLT-000019-Q |
| Incident | INC-2026-00755 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0276 |

**Autre formulation observée.** Le message reçu disait : « Pour Bastien Fauvevalon, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-00755. »


## Cas 020 : Voyage / réservation | dossier fictif INC-2026-00796

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Malo Dorémeline, née le 1967-12-05. Le dossier la rattache à 144, rue des Pivoines Grises, 99900 Brumeval, France. Son email est malo.doremeline19@example.invalid et son téléphone est 06 39 98 07 14; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 07 14. La fiche de contact porte le pseudonyme m.dorémeline_437. Le compte client est CLT-000020-Q, et la référence RH éventuelle est EMP-100462. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Dorémeline.

**Traitement du dossier.** Le 2026-10-26, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Titouan Nivvardin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 687,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 79 08 99 020 948 00. La domiciliation bancaire fictive indique FR00 3030 4369 5746 6933 8158 307, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.71; la trace IPv6 associée est 2001:db8:13::24d. Le poste de travail porte l’identifiant 123457bb-12b9-4009-a0f7-012345678bf8, le cookie de test est cookie-demo-00020-01843, et le gabarit biométrique est BIO-DEMO-001014 (référence vocale distincte : VOICE-TEST-00020). Le véhicule mentionné est ZZ-703-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Malo Dorémeline et ajouté une note de suivi à CLT-000020-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0289; la référence du lot est BATCH-OPS-2026-365. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Malo Dorémeline |
| Date | 1967-12-05 |
| Contact | malo.doremeline19@example.invalid |
| Client | CLT-000020-Q |
| Incident | INC-2026-00796 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0289 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Malo Dorémeline, identifiant CLT-000020-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 021 : Marketing / consentement | dossier fictif INC-2026-00837

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Ilyan Corvivalise, née le 1974-05-18. Le dossier la rattache à 161, rue des Brumes, 99900 Val-des-Nuages, France. Son email est ilyan.corvivalise20@example.invalid et son téléphone est 06 39 98 07 51; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 07 51. La fiche de contact porte le pseudonyme i.corvivalise_460. Le compte client est CLT-000021-Q, et la référence RH éventuelle est EMP-100481. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Corvivalise.

**Traitement du dossier.** Le 2025-01-06, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Nora Virenacré, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 860,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 80 09 99 021 085 00. La domiciliation bancaire fictive indique FR00 3131 4482 5873 7064 8295 446, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.88; la trace IPv6 associée est 2001:db8:14::26c. Le poste de travail porte l’identifiant 123457cc-12c0-4000-a104-012345678c17, le cookie de test est cookie-demo-00021-01940, et le gabarit biométrique est BIO-DEMO-001067 (référence vocale distincte : VOICE-TEST-00021). Le véhicule mentionné est ZZ-740-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ilyan Corvivalise et ajouté une note de suivi à CLT-000021-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ilyan CORVIVALISE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0302; la référence du lot est BATCH-OPS-2026-382. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ilyan Corvivalise |
| Date | 1974-05-18 |
| Contact | ilyan.corvivalise20@example.invalid |
| Client | CLT-000021-Q |
| Incident | INC-2026-00837 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0302 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Ilyan Corvivalise, 06 39 98 07 51, ilyan.corvivalise20@example.invalid; le rappel est prévu autour du 2025-01-06.”


## Cas 022 : Recherche / enquête | dossier fictif INC-2026-00878

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Émilie Lisirune, née le 1981-10-04. Le dossier la rattache à 178, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est emilie.lisirune21@example.invalid et son téléphone est 06 39 98 07 88; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 07 88. La fiche de contact porte le pseudonyme é.lisirune_483. Le compte client est CLT-000022-Q, et la référence RH éventuelle est EMP-100500. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lisirune.

**Traitement du dossier.** Le 2026-04-13, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Lison Cenddombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 033,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 81 10 99 022 222 00. La domiciliation bancaire fictive indique FR00 3232 4595 6000 7195 8432 585, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.105; la trace IPv6 associée est 2001:db8:15::28b. Le poste de travail porte l’identifiant 123457dd-12c7-4001-a111-012345678c36, le cookie de test est cookie-demo-00022-02037, et le gabarit biométrique est BIO-DEMO-001120 (référence vocale distincte : VOICE-TEST-00022). Le véhicule mentionné est ZZ-777-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Émilie Lisirune et ajouté une note de suivi à CLT-000022-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 07 88. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0315; la référence du lot est BATCH-OPS-2026-399. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Émilie Lisirune |
| Date | 1981-10-04 |
| Contact | emilie.lisirune21@example.invalid |
| Client | CLT-000022-Q |
| Incident | INC-2026-00878 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0315 |

**Autre formulation observée.** Note d’audit : le lien entre é.lisirune_483, 192.0.2.105 et 123457dd-12c7-4001-a111-012345678c36 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 023 : Logistique / livraison | dossier fictif INC-2026-00919

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Lison Lorimurel, née le 1988-03-17. Le dossier la rattache à 15, rue des Nuages Bas, 99900 Mirebrise, France. Son email est lison.lorimurel22@example.invalid et son téléphone est 06 39 98 08 25; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 08 25. La fiche de contact porte le pseudonyme l.lorimurel_506. Le compte client est CLT-000023-Q, et la référence RH éventuelle est EMP-100519. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lorimurel.

**Traitement du dossier.** Le 2025-07-20, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Sofia Saphvialet, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 206,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 82 11 99 023 359 00. La domiciliation bancaire fictive indique FR00 3333 4708 6127 7326 8569 724, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.122; la trace IPv6 associée est 2001:db8:16::2aa. Le poste de travail porte l’identifiant 123457ee-12ce-4002-a11e-012345678c55, le cookie de test est cookie-demo-00023-02134, et le gabarit biométrique est BIO-DEMO-001173 (référence vocale distincte : VOICE-TEST-00023). Le véhicule mentionné est ZZ-814-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lison Lorimurel et ajouté une note de suivi à CLT-000023-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0328; la référence du lot est BATCH-OPS-2026-416. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lison Lorimurel |
| Date | 1988-03-17 |
| Contact | lison.lorimurel22@example.invalid |
| Client | CLT-000023-Q |
| Incident | INC-2026-00919 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0328 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 024 : Sécurité / contrôle d’accès | dossier fictif INC-2026-00960

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Clémence Briscendre, née le 1995-08-03. Le dossier la rattache à 32, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est clemence.briscendre23@example.invalid et son téléphone est 06 39 98 08 62; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 08 62. La fiche de contact porte le pseudonyme c.briscendre_529. Le compte client est CLT-000024-Q, et la référence RH éventuelle est EMP-100538. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Briscendre.

**Traitement du dossier.** Le 2026-10-27, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Marceau Clairclaire, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 379,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 83 12 99 024 496 00. La domiciliation bancaire fictive indique FR00 3434 4821 6254 7457 8706 863, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.139; la trace IPv6 associée est 2001:db8:17::2c9. Le poste de travail porte l’identifiant 123457ff-12d5-4003-a12b-012345678c74, le cookie de test est cookie-demo-00024-02231, et le gabarit biométrique est BIO-DEMO-001226 (référence vocale distincte : VOICE-TEST-00024). Le véhicule mentionné est ZZ-851-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Clémence Briscendre et ajouté une note de suivi à CLT-000024-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0341; la référence du lot est BATCH-OPS-2026-433. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Clémence Briscendre |
| Date | 1995-08-03 |
| Contact | clemence.briscendre23@example.invalid |
| Client | CLT-000024-Q |
| Incident | INC-2026-00960 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0341 |

**Autre formulation observée.** Version importée : Clémence Briscendre; date=1995-08-03; rue=32, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France; téléphone=06 39 98 08 62; courriel=clemence.briscendre23@example.invalid; statut=à contrôler.


## Cas 025 : RH / gestion du personnel | dossier fictif INC-2026-01001

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Ismaël Lunémistral, née le 2002-01-16. Le dossier la rattache à 49, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est ismael.lunemistral24@example.invalid et son téléphone est 06 39 98 08 99; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 08 99. La fiche de contact porte le pseudonyme i.lunémistral_552. Le compte client est CLT-000025-Q, et la référence RH éventuelle est EMP-100557. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lunémistral.

**Traitement du dossier.** Le 2025-01-07, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Apolline Ormeplaine, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 552,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 84 01 99 025 633 00. La domiciliation bancaire fictive indique FR00 3535 4934 6381 7588 8843 002, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.156; la trace IPv6 associée est 2001:db8:18::2e8. Le poste de travail porte l’identifiant 12345810-12dc-4004-a138-012345678c93, le cookie de test est cookie-demo-00025-02328, et le gabarit biométrique est BIO-DEMO-001279 (référence vocale distincte : VOICE-TEST-00025). Le véhicule mentionné est ZZ-888-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ismaël Lunémistral et ajouté une note de suivi à CLT-000025-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0354; la référence du lot est BATCH-OPS-2026-450. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ismaël Lunémistral |
| Date | 2002-01-16 |
| Contact | ismael.lunemistral24@example.invalid |
| Client | CLT-000025-Q |
| Incident | INC-2026-01001 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0354 |

**Autre formulation observée.** Le message reçu disait : « Pour Ismaël Lunémistral, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-01001. »


## Cas 026 : CRM / relation client | dossier fictif INC-2026-01042

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Salomé Épilune, née le 1966-06-02. Le dossier la rattache à 66, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est salome.epilune25@example.invalid et son téléphone est 06 39 98 09 36; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 09 36. La fiche de contact porte le pseudonyme s.épilune_575. Le compte client est CLT-000026-Q, et la référence RH éventuelle est EMP-100576. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Épilune.

**Traitement du dossier.** Le 2026-04-14, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Mila Pluvivelin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 725,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 85 02 99 026 770 00. La domiciliation bancaire fictive indique FR00 3636 5047 6508 7719 8980 141, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.173; la trace IPv6 associée est 2001:db8:19::307. Le poste de travail porte l’identifiant 12345821-12e3-4005-a145-012345678cb2, le cookie de test est cookie-demo-00026-02425, et le gabarit biométrique est BIO-DEMO-001332 (référence vocale distincte : VOICE-TEST-00026). Le véhicule mentionné est ZZ-925-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Salomé Épilune et ajouté une note de suivi à CLT-000026-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient salomé ÉPILUNE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0367; la référence du lot est BATCH-OPS-2026-467. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Salomé Épilune |
| Date | 1966-06-02 |
| Contact | salome.epilune25@example.invalid |
| Client | CLT-000026-Q |
| Incident | INC-2026-01042 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0367 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Salomé Épilune, identifiant CLT-000026-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 027 : Santé / prise de rendez-vous | dossier fictif INC-2026-01083

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Nino Florilacier, née le 1973-11-15. Le dossier la rattache à 83, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est nino.florilacier26@example.invalid et son téléphone est 06 39 98 09 73; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 09 73. La fiche de contact porte le pseudonyme n.florilacier_598. Le compte client est CLT-000027-Q, et la référence RH éventuelle est EMP-100595. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Florilacier.

**Traitement du dossier.** Le 2025-07-21, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Jade Nacreclairon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 898,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 86 03 99 027 907 00. La domiciliation bancaire fictive indique FR00 3737 5160 6635 7850 9117 280, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.190; la trace IPv6 associée est 2001:db8:1a::326. Le poste de travail porte l’identifiant 12345832-12ea-4006-a152-012345678cd1, le cookie de test est cookie-demo-00027-02522, et le gabarit biométrique est BIO-DEMO-001385 (référence vocale distincte : VOICE-TEST-00027). Le véhicule mentionné est ZZ-962-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nino Florilacier et ajouté une note de suivi à CLT-000027-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0380; la référence du lot est BATCH-OPS-2026-484. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nino Florilacier |
| Date | 1973-11-15 |
| Contact | nino.florilacier26@example.invalid |
| Client | CLT-000027-Q |
| Incident | INC-2026-01083 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0380 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Nino Florilacier, 06 39 98 09 73, nino.florilacier26@example.invalid; le rappel est prévu autour du 2025-07-21.”


## Cas 028 : Banque / assurance | dossier fictif INC-2026-01124

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Lucile Orielserein, née le 2013-04-01. Le dossier la rattache à 100, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est lucile.orielserein27@example.invalid et son téléphone est 06 39 98 10 10; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 10 10. La fiche de contact porte le pseudonyme l.orielserein_621. Le compte client est CLT-000028-Q, et la référence RH éventuelle est EMP-100614. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Orielserein.

**Traitement du dossier.** Le 2026-10-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Ismaël Perrivigne, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 071,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 87 04 99 028 044 00. La domiciliation bancaire fictive indique FR00 3838 5273 6762 7981 9254 419, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.207; la trace IPv6 associée est 2001:db8:1b::345. Le poste de travail porte l’identifiant 12345843-12f1-4007-a15f-012345678cf0, le cookie de test est cookie-demo-00028-02619, et le gabarit biométrique est BIO-DEMO-001438 (référence vocale distincte : VOICE-TEST-00028). Le véhicule mentionné est ZZ-999-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lucile Orielserein et ajouté une note de suivi à CLT-000028-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2013-04-01. Le proche de référence est Ismaël Perrivigne. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0393; la référence du lot est BATCH-OPS-2026-501. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lucile Orielserein |
| Date | 2013-04-01 |
| Contact | lucile.orielserein27@example.invalid |
| Client | CLT-000028-Q |
| Incident | INC-2026-01124 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0393 |

**Autre formulation observée.** Note d’audit : le lien entre l.orielserein_621, 192.0.2.207 et 12345843-12f1-4007-a15f-012345678cf0 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 029 : Éducation / accompagnement | dossier fictif INC-2026-01165

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Noé Érablefarin, née le 1987-09-14. Le dossier la rattache à 117, rue du Phare Éteint, 99900 Pluviane, France. Son email est noe.erablefarin28@example.invalid et son téléphone est 06 39 98 10 47; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 10 47. La fiche de contact porte le pseudonyme n.érablefarin_644. Le compte client est CLT-000029-Q, et la référence RH éventuelle est EMP-100633. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Érablefarin.

**Traitement du dossier.** Le 2025-01-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Yasmine Pavofleur, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 244,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 88 05 99 029 181 00. La domiciliation bancaire fictive indique FR00 3939 5386 6889 8112 9391 558, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.224; la trace IPv6 associée est 2001:db8:1c::364. Le poste de travail porte l’identifiant 12345854-12f8-4008-a16c-012345678d0f, le cookie de test est cookie-demo-00029-02716, et le gabarit biométrique est BIO-DEMO-001491 (référence vocale distincte : VOICE-TEST-00029). Le véhicule mentionné est ZZ-036-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Noé Érablefarin et ajouté une note de suivi à CLT-000029-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 10 47. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0406; la référence du lot est BATCH-OPS-2026-518. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Noé Érablefarin |
| Date | 1987-09-14 |
| Contact | noe.erablefarin28@example.invalid |
| Client | CLT-000029-Q |
| Incident | INC-2026-01165 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0406 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 030 : Juridique / contrat | dossier fictif INC-2026-01206

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Sofia Valnette, née le 1994-02-27. Le dossier la rattache à 134, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est sofia.valnette29@example.invalid et son téléphone est 06 39 98 10 84; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 10 84. La fiche de contact porte le pseudonyme s.valnette_667. Le compte client est CLT-000030-Q, et la référence RH éventuelle est EMP-100652. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Valnette.

**Traitement du dossier.** Le 2026-04-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Mathis Noroorée, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 417,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 89 06 99 030 318 00. La domiciliation bancaire fictive indique FR00 4040 5499 7016 8243 9528 697, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.241; la trace IPv6 associée est 2001:db8:1d::383. Le poste de travail porte l’identifiant 12345865-12ff-4009-a179-012345678d2e, le cookie de test est cookie-demo-00030-02813, et le gabarit biométrique est BIO-DEMO-001544 (référence vocale distincte : VOICE-TEST-00030). Le véhicule mentionné est ZZ-073-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sofia Valnette et ajouté une note de suivi à CLT-000030-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0419; la référence du lot est BATCH-OPS-2026-535. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sofia Valnette |
| Date | 1994-02-27 |
| Contact | sofia.valnette29@example.invalid |
| Client | CLT-000030-Q |
| Incident | INC-2026-01206 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0419 |

**Autre formulation observée.** Version importée : Sofia Valnette; date=1994-02-27; rue=134, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France; téléphone=06 39 98 10 84; courriel=sofia.valnette29@example.invalid; statut=à contrôler.


## Cas 031 : Support informatique | dossier fictif INC-2026-01247

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Eden Mirasorel, née le 2001-07-13. Le dossier la rattache à 151, rue des Brumes, 99900 Cendrelac, France. Son email est eden.mirasorel30@example.invalid et son téléphone est 06 39 98 11 21; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 11 21. La fiche de contact porte le pseudonyme e.mirasorel_690. Le compte client est CLT-000031-Q, et la référence RH éventuelle est EMP-100671. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mirasorel.

**Traitement du dossier.** Le 2025-07-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Ambre Rosibrise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 490,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 90 07 99 031 455 00. La domiciliation bancaire fictive indique FR00 4141 5612 7143 8374 9665 836, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.5; la trace IPv6 associée est 2001:db8:1e::3a2. Le poste de travail porte l’identifiant 12345876-1306-4000-a186-012345678d4d, le cookie de test est cookie-demo-00031-02910, et le gabarit biométrique est BIO-DEMO-001597 (référence vocale distincte : VOICE-TEST-00031). Le véhicule mentionné est ZZ-110-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eden Mirasorel et ajouté une note de suivi à CLT-000031-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient eden MIRASOREL; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0432; la référence du lot est BATCH-OPS-2026-552. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eden Mirasorel |
| Date | 2001-07-13 |
| Contact | eden.mirasorel30@example.invalid |
| Client | CLT-000031-Q |
| Incident | INC-2026-01247 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0432 |

**Autre formulation observée.** Le message reçu disait : « Pour Eden Mirasorel, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-01247. »


## Cas 032 : Voyage / réservation | dossier fictif INC-2026-01288

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Yasmine Brumemarin, née le 1965-12-26. Le dossier la rattache à 168, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est yasmine.brumemarin31@example.invalid et son téléphone est 06 39 98 11 58; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 11 58. La fiche de contact porte le pseudonyme y.brumemarin_713. Le compte client est CLT-000032-Q, et la référence RH éventuelle est EMP-100690. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Brumemarin.

**Traitement du dossier.** Le 2026-10-02, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Maël Solravel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 663,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 91 08 99 032 592 00. La domiciliation bancaire fictive indique FR00 4242 5725 7270 8505 9802 975, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.22; la trace IPv6 associée est 2001:db8:1f::3c1. Le poste de travail porte l’identifiant 12345887-130d-4001-a193-012345678d6c, le cookie de test est cookie-demo-00032-03007, et le gabarit biométrique est BIO-DEMO-001650 (référence vocale distincte : VOICE-TEST-00032). Le véhicule mentionné est ZZ-147-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Yasmine Brumemarin et ajouté une note de suivi à CLT-000032-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0445; la référence du lot est BATCH-OPS-2026-569. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Yasmine Brumemarin |
| Date | 1965-12-26 |
| Contact | yasmine.brumemarin31@example.invalid |
| Client | CLT-000032-Q |
| Incident | INC-2026-01288 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0445 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Yasmine Brumemarin, identifiant CLT-000032-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 033 : Marketing / consentement | dossier fictif INC-2026-01329

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Eliott Mélidune, née le 1972-05-12. Le dossier la rattache à 5, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est eliott.melidune32@example.invalid et son téléphone est 06 39 98 11 95; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 11 95. La fiche de contact porte le pseudonyme e.mélidune_736. Le compte client est CLT-000033-Q, et la référence RH éventuelle est EMP-100709. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mélidune.

**Traitement du dossier.** Le 2025-01-09, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Malo Avelroche, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 836,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 92 09 99 033 729 00. La domiciliation bancaire fictive indique FR00 4343 5838 7397 8636 9939 114, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.39; la trace IPv6 associée est 2001:db8:20::3e0. Le poste de travail porte l’identifiant 12345898-1314-4002-a1a0-012345678d8b, le cookie de test est cookie-demo-00033-03104, et le gabarit biométrique est BIO-DEMO-001703 (référence vocale distincte : VOICE-TEST-00033). Le véhicule mentionné est ZZ-184-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eliott Mélidune et ajouté une note de suivi à CLT-000033-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0458; la référence du lot est BATCH-OPS-2026-586. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eliott Mélidune |
| Date | 1972-05-12 |
| Contact | eliott.melidune32@example.invalid |
| Client | CLT-000033-Q |
| Incident | INC-2026-01329 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0458 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Eliott Mélidune, 06 39 98 11 95, eliott.melidune32@example.invalid; le rappel est prévu autour du 2025-01-09.”


## Cas 034 : Recherche / enquête | dossier fictif INC-2026-01370

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Zoé Vanisac, née le 1979-10-25. Le dossier la rattache à 22, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est zoe.vanisac33@example.invalid et son téléphone est 06 39 98 12 32; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 12 32. La fiche de contact porte le pseudonyme z.vanisac_759. Le compte client est CLT-000034-Q, et la référence RH éventuelle est EMP-100728. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Vanisac.

**Traitement du dossier.** Le 2026-04-16, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Nino Tremlombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 009,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 93 10 99 034 866 00. La domiciliation bancaire fictive indique FR00 4444 5951 7524 8767 0076 253, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.56; la trace IPv6 associée est 2001:db8:21::3ff. Le poste de travail porte l’identifiant 123458a9-131b-4003-a1ad-012345678daa, le cookie de test est cookie-demo-00034-03201, et le gabarit biométrique est BIO-DEMO-001756 (référence vocale distincte : VOICE-TEST-00034). Le véhicule mentionné est ZZ-221-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Zoé Vanisac et ajouté une note de suivi à CLT-000034-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0471; la référence du lot est BATCH-OPS-2026-603. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Zoé Vanisac |
| Date | 1979-10-25 |
| Contact | zoe.vanisac33@example.invalid |
| Client | CLT-000034-Q |
| Incident | INC-2026-01370 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0471 |

**Autre formulation observée.** Note d’audit : le lien entre z.vanisac_759, 192.0.2.56 et 123458a9-131b-4003-a1ad-012345678daa doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 035 : Logistique / livraison | dossier fictif INC-2026-01411

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Gabin Aurimousse, née le 1986-03-11. Le dossier la rattache à 39, rue des Pivoines Grises, 99900 Valmousse, France. Son email est gabin.aurimousse34@example.invalid et son téléphone est 06 39 98 12 69; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 12 69. La fiche de contact porte le pseudonyme g.aurimousse_782. Le compte client est CLT-000035-Q, et la référence RH éventuelle est EMP-100747. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Aurimousse.

**Traitement du dossier.** Le 2025-07-23, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Zoé Varnedorin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 182,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 94 11 99 035 003 00. La domiciliation bancaire fictive indique FR00 4545 6064 7651 8898 0213 392, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.73; la trace IPv6 associée est 2001:db8:22::41e. Le poste de travail porte l’identifiant 123458ba-1322-4004-a1ba-012345678dc9, le cookie de test est cookie-demo-00035-03298, et le gabarit biométrique est BIO-DEMO-001809 (référence vocale distincte : VOICE-TEST-00035). Le véhicule mentionné est ZZ-258-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Gabin Aurimousse et ajouté une note de suivi à CLT-000035-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0484; la référence du lot est BATCH-OPS-2026-620. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Gabin Aurimousse |
| Date | 1986-03-11 |
| Contact | gabin.aurimousse34@example.invalid |
| Client | CLT-000035-Q |
| Incident | INC-2026-01411 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0484 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 036 : Sécurité / contrôle d’accès | dossier fictif INC-2026-01452

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Maëlys Montaroussin, née le 1993-08-24. Le dossier la rattache à 56, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est maelys.montaroussin35@example.invalid et son téléphone est 06 39 98 13 06; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 13 06. La fiche de contact porte le pseudonyme m.montaroussin_805. Le compte client est CLT-000036-Q, et la référence RH éventuelle est EMP-100766. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Montaroussin.

**Traitement du dossier.** Le 2026-10-03, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Sohan Célvaux, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 355,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 95 12 99 036 140 00. La domiciliation bancaire fictive indique FR00 4646 6177 7778 9029 0350 531, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.90; la trace IPv6 associée est 2001:db8:23::43d. Le poste de travail porte l’identifiant 123458cb-1329-4005-a1c7-012345678de8, le cookie de test est cookie-demo-00036-03395, et le gabarit biométrique est BIO-DEMO-001862 (référence vocale distincte : VOICE-TEST-00036). Le véhicule mentionné est ZZ-295-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maëlys Montaroussin et ajouté une note de suivi à CLT-000036-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient maëlys MONTAROUSSIN; vérifier que le changement de casse ne bloque pas la détection.

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 13 06. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0497; la référence du lot est BATCH-OPS-2026-637. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maëlys Montaroussin |
| Date | 1993-08-24 |
| Contact | maelys.montaroussin35@example.invalid |
| Client | CLT-000036-Q |
| Incident | INC-2026-01452 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0497 |

**Autre formulation observée.** Version importée : Maëlys Montaroussin; date=1993-08-24; rue=56, rue des Brumes, 99900 Virelune-les-Pins, France; téléphone=06 39 98 13 06; courriel=maelys.montaroussin35@example.invalid; statut=à contrôler.


## Cas 037 : RH / gestion du personnel | dossier fictif INC-2026-01493

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Marceau Nivvardin, née le 2014-01-10. Le dossier la rattache à 73, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est marceau.nivvardin36@example.invalid et son téléphone est 06 39 98 13 43; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 13 43. La fiche de contact porte le pseudonyme m.nivvardin_828. Le compte client est CLT-000037-Q, et la référence RH éventuelle est EMP-100785. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nivvardin.

**Traitement du dossier.** Le 2025-01-10, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Naël Seredorelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 528,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 96 01 99 037 277 00. La domiciliation bancaire fictive indique FR00 4747 6290 7905 9160 0487 670, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.107; la trace IPv6 associée est 2001:db8:24::45c. Le poste de travail porte l’identifiant 123458dc-1330-4006-a1d4-012345678e07, le cookie de test est cookie-demo-00037-03492, et le gabarit biométrique est BIO-DEMO-001915 (référence vocale distincte : VOICE-TEST-00037). Le véhicule mentionné est ZZ-332-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Marceau Nivvardin et ajouté une note de suivi à CLT-000037-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2014-01-10. Le proche de référence est Naël Seredorelle. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0510; la référence du lot est BATCH-OPS-2026-654. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Marceau Nivvardin |
| Date | 2014-01-10 |
| Contact | marceau.nivvardin36@example.invalid |
| Client | CLT-000037-Q |
| Incident | INC-2026-01493 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0510 |

**Autre formulation observée.** Le message reçu disait : « Pour Marceau Nivvardin, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-01493. »


## Cas 038 : CRM / relation client | dossier fictif INC-2026-01534

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Léonie Virenacré, née le 1964-06-23. Le dossier la rattache à 90, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est leonie.virenacre37@example.invalid et son téléphone est 06 39 98 13 80; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 13 80. La fiche de contact porte le pseudonyme l.virenacré_851. Le compte client est CLT-000038-Q, et la référence RH éventuelle est EMP-100804. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Virenacré.

**Traitement du dossier.** Le 2026-04-17, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Léandre Églanbelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 701,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 97 02 99 038 414 00. La domiciliation bancaire fictive indique FR00 4848 6403 8032 9291 0624 809, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.124; la trace IPv6 associée est 2001:db8:25::47b. Le poste de travail porte l’identifiant 123458ed-1337-4007-a1e1-012345678e26, le cookie de test est cookie-demo-00038-03589, et le gabarit biométrique est BIO-DEMO-001968 (référence vocale distincte : VOICE-TEST-00038). Le véhicule mentionné est ZZ-369-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léonie Virenacré et ajouté une note de suivi à CLT-000038-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0523; la référence du lot est BATCH-OPS-2026-671. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léonie Virenacré |
| Date | 1964-06-23 |
| Contact | leonie.virenacre37@example.invalid |
| Client | CLT-000038-Q |
| Incident | INC-2026-01534 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0523 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Léonie Virenacré, identifiant CLT-000038-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 039 : Santé / prise de rendez-vous | dossier fictif INC-2026-01575

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Mathis Cenddombre, née le 1971-11-09. Le dossier la rattache à 107, rue du Phare Éteint, 99900 Nacréville, France. Son email est mathis.cenddombre38@example.invalid et son téléphone est 06 39 98 14 17; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 14 17. La fiche de contact porte le pseudonyme m.cenddombre_874. Le compte client est CLT-000039-Q, et la référence RH éventuelle est EMP-100823. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Cenddombre.

**Traitement du dossier.** Le 2025-07-24, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Émilie Rivbrume, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 874,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 98 03 99 039 551 00. La domiciliation bancaire fictive indique FR00 4949 6516 8159 9422 0761 948, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.141; la trace IPv6 associée est 2001:db8:26::49a. Le poste de travail porte l’identifiant 123458fe-133e-4008-a1ee-012345678e45, le cookie de test est cookie-demo-00039-03686, et le gabarit biométrique est BIO-DEMO-002021 (référence vocale distincte : VOICE-TEST-00039). Le véhicule mentionné est ZZ-406-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mathis Cenddombre et ajouté une note de suivi à CLT-000039-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0536; la référence du lot est BATCH-OPS-2026-688. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mathis Cenddombre |
| Date | 1971-11-09 |
| Contact | mathis.cenddombre38@example.invalid |
| Client | CLT-000039-Q |
| Incident | INC-2026-01575 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0536 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Mathis Cenddombre, 06 39 98 14 17, mathis.cenddombre38@example.invalid; le rappel est prévu autour du 2025-07-24.”


## Cas 040 : Banque / assurance | dossier fictif INC-2026-01616

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Ariane Saphvialet, née le 1978-04-22. Le dossier la rattache à 124, rue des Pivoines Grises, 99900 Brumeval, France. Son email est ariane.saphvialet39@example.invalid et son téléphone est 06 39 98 14 54; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 14 54. La fiche de contact porte le pseudonyme a.saphvialet_897. Le compte client est CLT-000040-Q, et la référence RH éventuelle est EMP-100842. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Saphvialet.

**Traitement du dossier.** Le 2026-10-04, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Noé Alouloriot, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 047,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 60 04 99 040 688 00. La domiciliation bancaire fictive indique FR00 5050 6629 8286 9553 0898 087, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.158; la trace IPv6 associée est 2001:db8:27::4b9. Le poste de travail porte l’identifiant 1234590f-1345-4009-a1fb-012345678e64, le cookie de test est cookie-demo-00040-03783, et le gabarit biométrique est BIO-DEMO-002074 (référence vocale distincte : VOICE-TEST-00040). Le véhicule mentionné est ZZ-443-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ariane Saphvialet et ajouté une note de suivi à CLT-000040-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0549; la référence du lot est BATCH-OPS-2026-705. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ariane Saphvialet |
| Date | 1978-04-22 |
| Contact | ariane.saphvialet39@example.invalid |
| Client | CLT-000040-Q |
| Incident | INC-2026-01616 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0549 |

**Autre formulation observée.** Note d’audit : le lien entre a.saphvialet_897, 192.0.2.158 et 1234590f-1345-4009-a1fb-012345678e64 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 041 : Éducation / accompagnement | dossier fictif INC-2026-01657

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Sohan Clairclaire, née le 1985-09-08. Le dossier la rattache à 141, rue des Brumes, 99900 Val-des-Nuages, France. Son email est sohan.clairclaire40@example.invalid et son téléphone est 06 39 98 14 91; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 14 91. La fiche de contact porte le pseudonyme s.clairclaire_920. Le compte client est CLT-000041-Q, et la référence RH éventuelle est EMP-100861. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Clairclaire.

**Traitement du dossier.** Le 2025-01-11, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Maëlys Belaubier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 220,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 61 05 99 041 825 00. La domiciliation bancaire fictive indique FR00 5151 6742 8413 9684 1035 226, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.175; la trace IPv6 associée est 2001:db8:28::4d8. Le poste de travail porte l’identifiant 12345920-134c-4000-a208-012345678e83, le cookie de test est cookie-demo-00041-03880, et le gabarit biométrique est BIO-DEMO-002127 (référence vocale distincte : VOICE-TEST-00041). Le véhicule mentionné est ZZ-480-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sohan Clairclaire et ajouté une note de suivi à CLT-000041-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient sohan CLAIRCLAIRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0562; la référence du lot est BATCH-OPS-2026-722. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sohan Clairclaire |
| Date | 1985-09-08 |
| Contact | sohan.clairclaire40@example.invalid |
| Client | CLT-000041-Q |
| Incident | INC-2026-01657 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0562 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 042 : Juridique / contrat | dossier fictif INC-2026-01698

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Lina Ormeplaine, née le 1992-02-21. Le dossier la rattache à 158, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est lina.ormeplaine41@example.invalid et son téléphone est 06 39 98 15 28; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 15 28. La fiche de contact porte le pseudonyme l.ormeplaine_943. Le compte client est CLT-000042-Q, et la référence RH éventuelle est EMP-100880. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Ormeplaine.

**Traitement du dossier.** Le 2026-04-18, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Younès Fauvevalon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 393,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 62 06 99 042 962 00. La domiciliation bancaire fictive indique FR00 5252 6855 8540 9815 1172 365, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.192; la trace IPv6 associée est 2001:db8:29::4f7. Le poste de travail porte l’identifiant 12345931-1353-4001-a215-012345678ea2, le cookie de test est cookie-demo-00042-03977, et le gabarit biométrique est BIO-DEMO-002180 (référence vocale distincte : VOICE-TEST-00042). Le véhicule mentionné est ZZ-517-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lina Ormeplaine et ajouté une note de suivi à CLT-000042-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0575; la référence du lot est BATCH-OPS-2026-739. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lina Ormeplaine |
| Date | 1992-02-21 |
| Contact | lina.ormeplaine41@example.invalid |
| Client | CLT-000042-Q |
| Incident | INC-2026-01698 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0575 |

**Autre formulation observée.** Version importée : Lina Ormeplaine; date=1992-02-21; rue=158, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France; téléphone=06 39 98 15 28; courriel=lina.ormeplaine41@example.invalid; statut=à contrôler.


## Cas 043 : Support informatique | dossier fictif INC-2026-01739

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Younès Pluvivelin, née le 1999-07-07. Le dossier la rattache à 175, rue des Nuages Bas, 99900 Mirebrise, France. Son email est younes.pluvivelin42@example.invalid et son téléphone est 06 39 98 15 65; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 15 65. La fiche de contact porte le pseudonyme y.pluvivelin_966. Le compte client est CLT-000043-Q, et la référence RH éventuelle est EMP-100899. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pluvivelin.

**Traitement du dossier.** Le 2025-07-25, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Inès Dorémeline, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 566,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 63 07 99 043 099 00. La domiciliation bancaire fictive indique FR00 5353 6968 8667 9946 1309 504, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.209; la trace IPv6 associée est 2001:db8:2a::516. Le poste de travail porte l’identifiant 12345942-135a-4002-a222-012345678ec1, le cookie de test est cookie-demo-00043-04074, et le gabarit biométrique est BIO-DEMO-002233 (référence vocale distincte : VOICE-TEST-00043). Le véhicule mentionné est ZZ-554-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Younès Pluvivelin et ajouté une note de suivi à CLT-000043-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 15 65. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0588; la référence du lot est BATCH-OPS-2026-756. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Younès Pluvivelin |
| Date | 1999-07-07 |
| Contact | younes.pluvivelin42@example.invalid |
| Client | CLT-000043-Q |
| Incident | INC-2026-01739 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0588 |

**Autre formulation observée.** Le message reçu disait : « Pour Younès Pluvivelin, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-01739. »


## Cas 044 : Voyage / réservation | dossier fictif INC-2026-01780

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Apolline Nacreclairon, née le 1963-12-20. Le dossier la rattache à 12, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est apolline.nacreclairon43@example.invalid et son téléphone est 06 39 98 16 02; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 16 02. La fiche de contact porte le pseudonyme a.nacreclairon_989. Le compte client est CLT-000044-Q, et la référence RH éventuelle est EMP-100918. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nacreclairon.

**Traitement du dossier.** Le 2026-10-05, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Anaïs Corvivalise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 739,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 64 08 99 044 236 00. La domiciliation bancaire fictive indique FR00 5454 7081 8794 0077 1446 643, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.226; la trace IPv6 associée est 2001:db8:2b::535. Le poste de travail porte l’identifiant 12345953-1361-4003-a22f-012345678ee0, le cookie de test est cookie-demo-00044-04171, et le gabarit biométrique est BIO-DEMO-002286 (référence vocale distincte : VOICE-TEST-00044). Le véhicule mentionné est ZZ-591-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Apolline Nacreclairon et ajouté une note de suivi à CLT-000044-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0601; la référence du lot est BATCH-OPS-2026-773. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Apolline Nacreclairon |
| Date | 1963-12-20 |
| Contact | apolline.nacreclairon43@example.invalid |
| Client | CLT-000044-Q |
| Incident | INC-2026-01780 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0601 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Apolline Nacreclairon, identifiant CLT-000044-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 045 : Marketing / consentement | dossier fictif INC-2026-01821

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Romane Perrivigne, née le 1970-05-06. Le dossier la rattache à 29, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est romane.perrivigne44@example.invalid et son téléphone est 06 39 98 16 39; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 16 39. La fiche de contact porte le pseudonyme r.perrivigne_013. Le compte client est CLT-000045-Q, et la référence RH éventuelle est EMP-100937. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Perrivigne.

**Traitement du dossier.** Le 2025-01-12, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Clémence Lisirune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 912,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 65 09 99 045 373 00. La domiciliation bancaire fictive indique FR00 5555 7194 8921 0208 1583 782, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.243; la trace IPv6 associée est 2001:db8:2c::554. Le poste de travail porte l’identifiant 12345964-1368-4004-a23c-012345678eff, le cookie de test est cookie-demo-00045-04268, et le gabarit biométrique est BIO-DEMO-002339 (référence vocale distincte : VOICE-TEST-00045). Le véhicule mentionné est ZZ-628-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Romane Perrivigne et ajouté une note de suivi à CLT-000045-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0614; la référence du lot est BATCH-OPS-2026-790. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Romane Perrivigne |
| Date | 1970-05-06 |
| Contact | romane.perrivigne44@example.invalid |
| Client | CLT-000045-Q |
| Incident | INC-2026-01821 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0614 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Romane Perrivigne, 06 39 98 16 39, romane.perrivigne44@example.invalid; le rappel est prévu autour du 2025-01-12.”


## Cas 046 : Recherche / enquête | dossier fictif INC-2026-01862

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Ambre Pavofleur, née le 2015-10-19. Le dossier la rattache à 46, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est ambre.pavofleur45@example.invalid et son téléphone est 06 39 98 16 76; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 16 76. La fiche de contact porte le pseudonyme a.pavofleur_036. Le compte client est CLT-000046-Q, et la référence RH éventuelle est EMP-100956. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pavofleur.

**Traitement du dossier.** Le 2026-04-19, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Eden Lorimurel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 085,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 66 10 99 046 510 00. La domiciliation bancaire fictive indique FR00 5656 7307 9048 0339 1720 921, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.7; la trace IPv6 associée est 2001:db8:2d::573. Le poste de travail porte l’identifiant 12345975-136f-4005-a249-012345678f1e, le cookie de test est cookie-demo-00046-04365, et le gabarit biométrique est BIO-DEMO-002392 (référence vocale distincte : VOICE-TEST-00046). Le véhicule mentionné est ZZ-665-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ambre Pavofleur et ajouté une note de suivi à CLT-000046-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ambre PAVOFLEUR; vérifier que le changement de casse ne bloque pas la détection.

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2015-10-19. Le proche de référence est Eden Lorimurel. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0627; la référence du lot est BATCH-OPS-2026-807. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ambre Pavofleur |
| Date | 2015-10-19 |
| Contact | ambre.pavofleur45@example.invalid |
| Client | CLT-000046-Q |
| Incident | INC-2026-01862 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0627 |

**Autre formulation observée.** Note d’audit : le lien entre a.pavofleur_036, 192.0.2.7 et 12345975-136f-4005-a249-012345678f1e doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 047 : Logistique / livraison | dossier fictif INC-2026-01903

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Théo Noroorée, née le 1984-03-05. Le dossier la rattache à 63, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est theo.norooree46@example.invalid et son téléphone est 06 39 98 17 13; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 17 13. La fiche de contact porte le pseudonyme t.noroorée_059. Le compte client est CLT-000047-Q, et la référence RH éventuelle est EMP-100975. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Noroorée.

**Traitement du dossier.** Le 2025-07-26, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Léonie Briscendre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 258,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 67 11 99 047 647 00. La domiciliation bancaire fictive indique FR00 5757 7420 9175 0470 1857 060, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.24; la trace IPv6 associée est 2001:db8:2e::592. Le poste de travail porte l’identifiant 12345986-1376-4006-a256-012345678f3d, le cookie de test est cookie-demo-00047-04462, et le gabarit biométrique est BIO-DEMO-002445 (référence vocale distincte : VOICE-TEST-00047). Le véhicule mentionné est ZZ-702-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Théo Noroorée et ajouté une note de suivi à CLT-000047-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0640; la référence du lot est BATCH-OPS-2026-824. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Théo Noroorée |
| Date | 1984-03-05 |
| Contact | theo.norooree46@example.invalid |
| Client | CLT-000047-Q |
| Incident | INC-2026-01903 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0640 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 048 : Sécurité / contrôle d’accès | dossier fictif INC-2026-01944

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Naël Rosibrise, née le 1991-08-18. Le dossier la rattache à 80, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est nael.rosibrise47@example.invalid et son téléphone est 06 39 98 17 50; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 17 50. La fiche de contact porte le pseudonyme n.rosibrise_082. Le compte client est CLT-000048-Q, et la référence RH éventuelle est EMP-100994. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rosibrise.

**Traitement du dossier.** Le 2026-10-06, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Romane Lunémistral, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 431,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 68 12 99 048 784 00. La domiciliation bancaire fictive indique FR00 5858 7533 9302 0601 1994 199, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.41; la trace IPv6 associée est 2001:db8:2f::5b1. Le poste de travail porte l’identifiant 12345997-137d-4007-a263-012345678f5c, le cookie de test est cookie-demo-00048-04559, et le gabarit biométrique est BIO-DEMO-002498 (référence vocale distincte : VOICE-TEST-00048). Le véhicule mentionné est ZZ-739-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Naël Rosibrise et ajouté une note de suivi à CLT-000048-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0653; la référence du lot est BATCH-OPS-2026-841. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Naël Rosibrise |
| Date | 1991-08-18 |
| Contact | nael.rosibrise47@example.invalid |
| Client | CLT-000048-Q |
| Incident | INC-2026-01944 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0653 |

**Autre formulation observée.** Version importée : Naël Rosibrise; date=1991-08-18; rue=80, rue des Nuages Bas, 99900 Aubier-des-Marées, France; téléphone=06 39 98 17 50; courriel=nael.rosibrise47@example.invalid; statut=à contrôler.


## Cas 049 : RH / gestion du personnel | dossier fictif INC-2026-01985

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Titouan Solravel, née le 1998-01-04. Le dossier la rattache à 97, rue du Phare Éteint, 99900 Pluviane, France. Son email est titouan.solravel48@example.invalid et son téléphone est 06 39 98 17 87; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 17 87. La fiche de contact porte le pseudonyme t.solravel_105. Le compte client est CLT-000049-Q, et la référence RH éventuelle est EMP-101013. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Solravel.

**Traitement du dossier.** Le 2025-01-13, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Mélina Épilune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 604,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 69 01 99 049 921 00. La domiciliation bancaire fictive indique FR00 5959 7646 9429 0732 2131 338, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.58; la trace IPv6 associée est 2001:db8:30::5d0. Le poste de travail porte l’identifiant 123459a8-1384-4008-a270-012345678f7b, le cookie de test est cookie-demo-00049-04656, et le gabarit biométrique est BIO-DEMO-002551 (référence vocale distincte : VOICE-TEST-00049). Le véhicule mentionné est ZZ-776-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Titouan Solravel et ajouté une note de suivi à CLT-000049-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0666; la référence du lot est BATCH-OPS-2026-858. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Titouan Solravel |
| Date | 1998-01-04 |
| Contact | titouan.solravel48@example.invalid |
| Client | CLT-000049-Q |
| Incident | INC-2026-01985 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0666 |

**Autre formulation observée.** Le message reçu disait : « Pour Titouan Solravel, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-01985. »


## Cas 050 : CRM / relation client | dossier fictif INC-2026-02026

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Inès Avelroche, née le 2005-06-17. Le dossier la rattache à 114, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est ines.avelroche49@example.invalid et son téléphone est 06 39 98 18 24; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 18 24. La fiche de contact porte le pseudonyme i.avelroche_128. Le compte client est CLT-000050-Q, et la référence RH éventuelle est EMP-101032. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Avelroche.

**Traitement du dossier.** Le 2026-04-20, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Bastien Florilacier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 777,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 70 02 99 050 058 00. La domiciliation bancaire fictive indique FR00 6060 7759 9556 0863 2268 477, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.75; la trace IPv6 associée est 2001:db8:31::5ef. Le poste de travail porte l’identifiant 123459b9-138b-4009-a27d-012345678f9a, le cookie de test est cookie-demo-00050-04753, et le gabarit biométrique est BIO-DEMO-002604 (référence vocale distincte : VOICE-TEST-00050). Le véhicule mentionné est ZZ-813-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Inès Avelroche et ajouté une note de suivi à CLT-000050-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 18 24. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0679; la référence du lot est BATCH-OPS-2026-875. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Inès Avelroche |
| Date | 2005-06-17 |
| Contact | ines.avelroche49@example.invalid |
| Client | CLT-000050-Q |
| Incident | INC-2026-02026 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0679 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Inès Avelroche, identifiant CLT-000050-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 051 : Santé / prise de rendez-vous | dossier fictif INC-2026-02067

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Mila Tremlombre, née le 1969-11-03. Le dossier la rattache à 131, rue des Brumes, 99900 Cendrelac, France. Son email est mila.tremlombre50@example.invalid et son téléphone est 06 39 98 18 61; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 18 61. La fiche de contact porte le pseudonyme m.tremlombre_151. Le compte client est CLT-000051-Q, et la référence RH éventuelle est EMP-101051. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Tremlombre.

**Traitement du dossier.** Le 2025-07-27, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Salomé Orielserein, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 950,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 71 03 99 051 195 00. La domiciliation bancaire fictive indique FR00 6161 7872 9683 0994 2405 616, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.92; la trace IPv6 associée est 2001:db8:32::60e. Le poste de travail porte l’identifiant 123459ca-1392-4000-a28a-012345678fb9, le cookie de test est cookie-demo-00051-04850, et le gabarit biométrique est BIO-DEMO-002657 (référence vocale distincte : VOICE-TEST-00051). Le véhicule mentionné est ZZ-850-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mila Tremlombre et ajouté une note de suivi à CLT-000051-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient mila TREMLOMBRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0692; la référence du lot est BATCH-OPS-2026-892. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mila Tremlombre |
| Date | 1969-11-03 |
| Contact | mila.tremlombre50@example.invalid |
| Client | CLT-000051-Q |
| Incident | INC-2026-02067 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0692 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Mila Tremlombre, 06 39 98 18 61, mila.tremlombre50@example.invalid; le rappel est prévu autour du 2025-07-27.”


## Cas 052 : Banque / assurance | dossier fictif INC-2026-02108

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Mélina Varnedorin, née le 1976-04-16. Le dossier la rattache à 148, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est melina.varnedorin51@example.invalid et son téléphone est 06 39 98 18 98; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 18 98. La fiche de contact porte le pseudonyme m.varnedorin_174. Le compte client est CLT-000052-Q, et la référence RH éventuelle est EMP-101070. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Varnedorin.

**Traitement du dossier.** Le 2026-10-07, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Eliott Érablefarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 123,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 72 04 99 052 332 00. La domiciliation bancaire fictive indique FR00 6262 7985 9810 1125 2542 755, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.109; la trace IPv6 associée est 2001:db8:33::62d. Le poste de travail porte l’identifiant 123459db-1399-4001-a297-012345678fd8, le cookie de test est cookie-demo-00052-04947, et le gabarit biométrique est BIO-DEMO-002710 (référence vocale distincte : VOICE-TEST-00052). Le véhicule mentionné est ZZ-887-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mélina Varnedorin et ajouté une note de suivi à CLT-000052-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0705; la référence du lot est BATCH-OPS-2026-909. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mélina Varnedorin |
| Date | 1976-04-16 |
| Contact | melina.varnedorin51@example.invalid |
| Client | CLT-000052-Q |
| Incident | INC-2026-02108 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0705 |

**Autre formulation observée.** Note d’audit : le lien entre m.varnedorin_174, 192.0.2.109 et 123459db-1399-4001-a297-012345678fd8 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 053 : Éducation / accompagnement | dossier fictif INC-2026-02149

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Maël Célvaux, née le 1983-09-02. Le dossier la rattache à 165, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est mael.celvaux52@example.invalid et son téléphone est 06 39 98 19 35; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 19 35. La fiche de contact porte le pseudonyme m.célvaux_197. Le compte client est CLT-000053-Q, et la référence RH éventuelle est EMP-101089. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Célvaux.

**Traitement du dossier.** Le 2025-01-14, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Ariane Valnette, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 296,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 73 05 99 053 469 00. La domiciliation bancaire fictive indique FR00 6363 8098 9937 1256 2679 894, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.126; la trace IPv6 associée est 2001:db8:34::64c. Le poste de travail porte l’identifiant 123459ec-13a0-4002-a2a4-012345678ff7, le cookie de test est cookie-demo-00053-05044, et le gabarit biométrique est BIO-DEMO-002763 (référence vocale distincte : VOICE-TEST-00053). Le véhicule mentionné est ZZ-924-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maël Célvaux et ajouté une note de suivi à CLT-000053-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0718; la référence du lot est BATCH-OPS-2026-926. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maël Célvaux |
| Date | 1983-09-02 |
| Contact | mael.celvaux52@example.invalid |
| Client | CLT-000053-Q |
| Incident | INC-2026-02149 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0718 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 054 : Juridique / contrat | dossier fictif INC-2026-02190

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Célestin Seredorelle, née le 1990-02-15. Le dossier la rattache à 2, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est celestin.seredorelle53@example.invalid et son téléphone est 06 39 98 19 72; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 19 72. La fiche de contact porte le pseudonyme c.seredorelle_220. Le compte client est CLT-000054-Q, et la référence RH éventuelle est EMP-101108. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Seredorelle.

**Traitement du dossier.** Le 2026-04-21, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Théo Mirasorel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 469,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 74 06 99 054 606 00. La domiciliation bancaire fictive indique FR00 6464 8211 0064 1387 2816 033, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.143; la trace IPv6 associée est 2001:db8:35::66b. Le poste de travail porte l’identifiant 123459fd-13a7-4003-a2b1-012345679016, le cookie de test est cookie-demo-00054-05141, et le gabarit biométrique est BIO-DEMO-002816 (référence vocale distincte : VOICE-TEST-00054). Le véhicule mentionné est ZZ-961-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Célestin Seredorelle et ajouté une note de suivi à CLT-000054-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0731; la référence du lot est BATCH-OPS-2026-943. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Célestin Seredorelle |
| Date | 1990-02-15 |
| Contact | celestin.seredorelle53@example.invalid |
| Client | CLT-000054-Q |
| Incident | INC-2026-02190 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0731 |

**Autre formulation observée.** Version importée : Célestin Seredorelle; date=1990-02-15; rue=2, rue du Phare Éteint, 99900 Orée-du-Mistral, France; téléphone=06 39 98 19 72; courriel=celestin.seredorelle53@example.invalid; statut=à contrôler.


## Cas 055 : Support informatique | dossier fictif INC-2026-02231

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Léandre Églanbelle, née le 2016-07-01. Le dossier la rattache à 19, rue des Pivoines Grises, 99900 Valmousse, France. Son email est leandre.eglanbelle54@example.invalid et son téléphone est 06 39 98 20 09; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 20 09. La fiche de contact porte le pseudonyme l.églanbelle_243. Le compte client est CLT-000055-Q, et la référence RH éventuelle est EMP-101127. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Églanbelle.

**Traitement du dossier.** Le 2025-07-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Célestin Brumemarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 642,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 75 07 99 055 743 00. La domiciliation bancaire fictive indique FR00 6565 8324 0191 1518 2953 172, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.160; la trace IPv6 associée est 2001:db8:36::68a. Le poste de travail porte l’identifiant 12345a0e-13ae-4004-a2be-012345679035, le cookie de test est cookie-demo-00055-05238, et le gabarit biométrique est BIO-DEMO-002869 (référence vocale distincte : VOICE-TEST-00055). Le véhicule mentionné est ZZ-998-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léandre Églanbelle et ajouté une note de suivi à CLT-000055-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2016-07-01. Le proche de référence est Célestin Brumemarin. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0744; la référence du lot est BATCH-OPS-2026-960. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léandre Églanbelle |
| Date | 2016-07-01 |
| Contact | leandre.eglanbelle54@example.invalid |
| Client | CLT-000055-Q |
| Incident | INC-2026-02231 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0744 |

**Autre formulation observée.** Le message reçu disait : « Pour Léandre Églanbelle, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-02231. »


## Cas 056 : Voyage / réservation | dossier fictif INC-2026-02272

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Nora Rivbrume, née le 2004-12-14. Le dossier la rattache à 36, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est nora.rivbrume55@example.invalid et son téléphone est 06 39 98 20 46; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 20 46. La fiche de contact porte le pseudonyme n.rivbrume_266. Le compte client est CLT-000056-Q, et la référence RH éventuelle est EMP-101146. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rivbrume.

**Traitement du dossier.** Le 2026-10-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Ilyan Mélidune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 815,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 76 08 99 056 880 00. La domiciliation bancaire fictive indique FR00 6666 8437 0318 1649 3090 311, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.177; la trace IPv6 associée est 2001:db8:37::6a9. Le poste de travail porte l’identifiant 12345a1f-13b5-4005-a2cb-012345679054, le cookie de test est cookie-demo-00056-05335, et le gabarit biométrique est BIO-DEMO-002922 (référence vocale distincte : VOICE-TEST-00056). Le véhicule mentionné est ZZ-035-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nora Rivbrume et ajouté une note de suivi à CLT-000056-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient nora RIVBRUME; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0757; la référence du lot est BATCH-OPS-2026-977. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nora Rivbrume |
| Date | 2004-12-14 |
| Contact | nora.rivbrume55@example.invalid |
| Client | CLT-000056-Q |
| Incident | INC-2026-02272 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0757 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Nora Rivbrume, identifiant CLT-000056-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 057 : Marketing / consentement | dossier fictif INC-2026-02313

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Anaïs Alouloriot, née le 1968-05-27. Le dossier la rattache à 53, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est anais.alouloriot56@example.invalid et son téléphone est 06 39 98 20 83; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 20 83. La fiche de contact porte le pseudonyme a.alouloriot_289. Le compte client est CLT-000057-Q, et la référence RH éventuelle est EMP-101165. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Alouloriot.

**Traitement du dossier.** Le 2025-01-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Lucile Vanisac, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 988,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 77 09 99 057 017 00. La domiciliation bancaire fictive indique FR00 6767 8550 0445 1780 3227 450, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.194; la trace IPv6 associée est 2001:db8:38::6c8. Le poste de travail porte l’identifiant 12345a30-13bc-4006-a2d8-012345679073, le cookie de test est cookie-demo-00057-05432, et le gabarit biométrique est BIO-DEMO-002975 (référence vocale distincte : VOICE-TEST-00057). Le véhicule mentionné est ZZ-072-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Anaïs Alouloriot et ajouté une note de suivi à CLT-000057-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 20 83. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0770; la référence du lot est BATCH-OPS-2026-994. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Anaïs Alouloriot |
| Date | 1968-05-27 |
| Contact | anais.alouloriot56@example.invalid |
| Client | CLT-000057-Q |
| Incident | INC-2026-02313 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0770 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Anaïs Alouloriot, 06 39 98 20 83, anais.alouloriot56@example.invalid; le rappel est prévu autour du 2025-01-15.”


## Cas 058 : Recherche / enquête | dossier fictif INC-2026-02354

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Jade Belaubier, née le 1975-10-13. Le dossier la rattache à 70, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est jade.belaubier57@example.invalid et son téléphone est 06 39 98 21 20; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 21 20. La fiche de contact porte le pseudonyme j.belaubier_312. Le compte client est CLT-000058-Q, et la référence RH éventuelle est EMP-101184. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Belaubier.

**Traitement du dossier.** Le 2026-04-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Gabin Aurimousse, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 161,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 78 10 99 058 154 00. La domiciliation bancaire fictive indique FR00 6868 8663 0572 1911 3364 589, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.211; la trace IPv6 associée est 2001:db8:39::6e7. Le poste de travail porte l’identifiant 12345a41-13c3-4007-a2e5-012345679092, le cookie de test est cookie-demo-00058-05529, et le gabarit biométrique est BIO-DEMO-003028 (référence vocale distincte : VOICE-TEST-00058). Le véhicule mentionné est ZZ-109-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Jade Belaubier et ajouté une note de suivi à CLT-000058-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0783; la référence du lot est BATCH-OPS-2026-012. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Jade Belaubier |
| Date | 1975-10-13 |
| Contact | jade.belaubier57@example.invalid |
| Client | CLT-000058-Q |
| Incident | INC-2026-02354 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0783 |

**Autre formulation observée.** Note d’audit : le lien entre j.belaubier_312, 192.0.2.211 et 12345a41-13c3-4007-a2e5-012345679092 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 059 : Logistique / livraison | dossier fictif INC-2026-02395

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Bastien Fauvevalon, née le 1982-03-26. Le dossier la rattache à 87, rue du Phare Éteint, 99900 Nacréville, France. Son email est bastien.fauvevalon58@example.invalid et son téléphone est 06 39 98 21 57; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 21 57. La fiche de contact porte le pseudonyme b.fauvevalon_335. Le compte client est CLT-000059-Q, et la référence RH éventuelle est EMP-101203. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Fauvevalon.

**Traitement du dossier.** Le 2025-07-02, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Lina Montaroussin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 334,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 79 11 99 059 291 00. La domiciliation bancaire fictive indique FR00 6969 8776 0699 2042 3501 728, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.228; la trace IPv6 associée est 2001:db8:3a::706. Le poste de travail porte l’identifiant 12345a52-13ca-4008-a2f2-0123456790b1, le cookie de test est cookie-demo-00059-05626, et le gabarit biométrique est BIO-DEMO-003081 (référence vocale distincte : VOICE-TEST-00059). Le véhicule mentionné est ZZ-146-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Bastien Fauvevalon et ajouté une note de suivi à CLT-000059-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0796; la référence du lot est BATCH-OPS-2026-029. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Bastien Fauvevalon |
| Date | 1982-03-26 |
| Contact | bastien.fauvevalon58@example.invalid |
| Client | CLT-000059-Q |
| Incident | INC-2026-02395 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0796 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 060 : Sécurité / contrôle d’accès | dossier fictif INC-2026-02436

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Malo Dorémeline, née le 1989-08-12. Le dossier la rattache à 104, rue des Pivoines Grises, 99900 Brumeval, France. Son email est malo.doremeline59@example.invalid et son téléphone est 06 39 98 21 94; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 21 94. La fiche de contact porte le pseudonyme m.dorémeline_358. Le compte client est CLT-000060-Q, et la référence RH éventuelle est EMP-101222. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Dorémeline.

**Traitement du dossier.** Le 2026-10-09, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Titouan Nivvardin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 407,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 80 12 99 060 428 00. La domiciliation bancaire fictive indique FR00 7070 8889 0826 2173 3638 867, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.245; la trace IPv6 associée est 2001:db8:3b::725. Le poste de travail porte l’identifiant 12345a63-13d1-4009-a2ff-0123456790d0, le cookie de test est cookie-demo-00060-05723, et le gabarit biométrique est BIO-DEMO-003134 (référence vocale distincte : VOICE-TEST-00060). Le véhicule mentionné est ZZ-183-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Malo Dorémeline et ajouté une note de suivi à CLT-000060-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0809; la référence du lot est BATCH-OPS-2026-046. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Malo Dorémeline |
| Date | 1989-08-12 |
| Contact | malo.doremeline59@example.invalid |
| Client | CLT-000060-Q |
| Incident | INC-2026-02436 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0809 |

**Autre formulation observée.** Version importée : Malo Dorémeline; date=1989-08-12; rue=104, rue des Pivoines Grises, 99900 Brumeval, France; téléphone=06 39 98 21 94; courriel=malo.doremeline59@example.invalid; statut=à contrôler.


## Cas 061 : RH / gestion du personnel | dossier fictif INC-2026-02477

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Ilyan Corvivalise, née le 1996-01-25. Le dossier la rattache à 121, rue des Brumes, 99900 Val-des-Nuages, France. Son email est ilyan.corvivalise60@example.invalid et son téléphone est 06 39 98 22 31; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 22 31. La fiche de contact porte le pseudonyme i.corvivalise_381. Le compte client est CLT-000061-Q, et la référence RH éventuelle est EMP-101241. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Corvivalise.

**Traitement du dossier.** Le 2025-01-16, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Nora Virenacré, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 580,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 81 01 99 061 565 00. La domiciliation bancaire fictive indique FR00 7171 9002 0953 2304 3775 006, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.9; la trace IPv6 associée est 2001:db8:3c::744. Le poste de travail porte l’identifiant 12345a74-13d8-4000-a30c-0123456790ef, le cookie de test est cookie-demo-00061-05820, et le gabarit biométrique est BIO-DEMO-003187 (référence vocale distincte : VOICE-TEST-00061). Le véhicule mentionné est ZZ-220-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ilyan Corvivalise et ajouté une note de suivi à CLT-000061-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ilyan CORVIVALISE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0822; la référence du lot est BATCH-OPS-2026-063. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ilyan Corvivalise |
| Date | 1996-01-25 |
| Contact | ilyan.corvivalise60@example.invalid |
| Client | CLT-000061-Q |
| Incident | INC-2026-02477 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0822 |

**Autre formulation observée.** Le message reçu disait : « Pour Ilyan Corvivalise, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-02477. »


## Cas 062 : CRM / relation client | dossier fictif INC-2026-02518

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Émilie Lisirune, née le 2003-06-11. Le dossier la rattache à 138, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est emilie.lisirune61@example.invalid et son téléphone est 06 39 98 22 68; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 22 68. La fiche de contact porte le pseudonyme é.lisirune_404. Le compte client est CLT-000062-Q, et la référence RH éventuelle est EMP-101260. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lisirune.

**Traitement du dossier.** Le 2026-04-23, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Lison Cenddombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 753,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 82 02 99 062 702 00. La domiciliation bancaire fictive indique FR00 7272 9115 1080 2435 3912 145, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.26; la trace IPv6 associée est 2001:db8:3d::763. Le poste de travail porte l’identifiant 12345a85-13df-4001-a319-01234567910e, le cookie de test est cookie-demo-00062-05917, et le gabarit biométrique est BIO-DEMO-003240 (référence vocale distincte : VOICE-TEST-00062). Le véhicule mentionné est ZZ-257-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Émilie Lisirune et ajouté une note de suivi à CLT-000062-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0835; la référence du lot est BATCH-OPS-2026-080. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Émilie Lisirune |
| Date | 2003-06-11 |
| Contact | emilie.lisirune61@example.invalid |
| Client | CLT-000062-Q |
| Incident | INC-2026-02518 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0835 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Émilie Lisirune, identifiant CLT-000062-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 063 : Santé / prise de rendez-vous | dossier fictif INC-2026-02559

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Lison Lorimurel, née le 1967-11-24. Le dossier la rattache à 155, rue des Nuages Bas, 99900 Mirebrise, France. Son email est lison.lorimurel62@example.invalid et son téléphone est 06 39 98 23 05; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 23 05. La fiche de contact porte le pseudonyme l.lorimurel_427. Le compte client est CLT-000063-Q, et la référence RH éventuelle est EMP-101279. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lorimurel.

**Traitement du dossier.** Le 2025-07-03, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Sofia Saphvialet, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 926,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 83 03 99 063 839 00. La domiciliation bancaire fictive indique FR00 7373 9228 1207 2566 4049 284, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.43; la trace IPv6 associée est 2001:db8:3e::782. Le poste de travail porte l’identifiant 12345a96-13e6-4002-a326-01234567912d, le cookie de test est cookie-demo-00063-06014, et le gabarit biométrique est BIO-DEMO-003293 (référence vocale distincte : VOICE-TEST-00063). Le véhicule mentionné est ZZ-294-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lison Lorimurel et ajouté une note de suivi à CLT-000063-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0848; la référence du lot est BATCH-OPS-2026-097. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lison Lorimurel |
| Date | 1967-11-24 |
| Contact | lison.lorimurel62@example.invalid |
| Client | CLT-000063-Q |
| Incident | INC-2026-02559 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0848 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Lison Lorimurel, 06 39 98 23 05, lison.lorimurel62@example.invalid; le rappel est prévu autour du 2025-07-03.”


## Cas 064 : Banque / assurance | dossier fictif INC-2026-02600

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Clémence Briscendre, née le 2017-04-10. Le dossier la rattache à 172, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est clemence.briscendre63@example.invalid et son téléphone est 06 39 98 23 42; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 23 42. La fiche de contact porte le pseudonyme c.briscendre_450. Le compte client est CLT-000064-Q, et la référence RH éventuelle est EMP-101298. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Briscendre.

**Traitement du dossier.** Le 2026-10-10, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Marceau Clairclaire, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 099,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 84 04 99 064 976 00. La domiciliation bancaire fictive indique FR00 7474 9341 1334 2697 4186 423, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.60; la trace IPv6 associée est 2001:db8:3f::7a1. Le poste de travail porte l’identifiant 12345aa7-13ed-4003-a333-01234567914c, le cookie de test est cookie-demo-00064-06111, et le gabarit biométrique est BIO-DEMO-003346 (référence vocale distincte : VOICE-TEST-00064). Le véhicule mentionné est ZZ-331-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Clémence Briscendre et ajouté une note de suivi à CLT-000064-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 23 42. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2017-04-10. Le proche de référence est Marceau Clairclaire. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0861; la référence du lot est BATCH-OPS-2026-114. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Clémence Briscendre |
| Date | 2017-04-10 |
| Contact | clemence.briscendre63@example.invalid |
| Client | CLT-000064-Q |
| Incident | INC-2026-02600 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0861 |

**Autre formulation observée.** Note d’audit : le lien entre c.briscendre_450, 192.0.2.60 et 12345aa7-13ed-4003-a333-01234567914c doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 065 : Éducation / accompagnement | dossier fictif INC-2026-02641

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Ismaël Lunémistral, née le 1981-09-23. Le dossier la rattache à 9, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est ismael.lunemistral64@example.invalid et son téléphone est 06 39 98 23 79; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 23 79. La fiche de contact porte le pseudonyme i.lunémistral_473. Le compte client est CLT-000065-Q, et la référence RH éventuelle est EMP-101317. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lunémistral.

**Traitement du dossier.** Le 2025-01-17, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Apolline Ormeplaine, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 272,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 85 05 99 065 113 00. La domiciliation bancaire fictive indique FR00 7575 9454 1461 2828 4323 562, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.77; la trace IPv6 associée est 2001:db8:40::7c0. Le poste de travail porte l’identifiant 12345ab8-13f4-4004-a340-01234567916b, le cookie de test est cookie-demo-00065-06208, et le gabarit biométrique est BIO-DEMO-003399 (référence vocale distincte : VOICE-TEST-00065). Le véhicule mentionné est ZZ-368-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ismaël Lunémistral et ajouté une note de suivi à CLT-000065-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0874; la référence du lot est BATCH-OPS-2026-131. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ismaël Lunémistral |
| Date | 1981-09-23 |
| Contact | ismael.lunemistral64@example.invalid |
| Client | CLT-000065-Q |
| Incident | INC-2026-02641 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0874 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 066 : Juridique / contrat | dossier fictif INC-2026-02682

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Salomé Épilune, née le 1988-02-09. Le dossier la rattache à 26, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est salome.epilune65@example.invalid et son téléphone est 06 39 98 24 16; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 24 16. La fiche de contact porte le pseudonyme s.épilune_496. Le compte client est CLT-000066-Q, et la référence RH éventuelle est EMP-101336. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Épilune.

**Traitement du dossier.** Le 2026-04-24, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Mila Pluvivelin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 445,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 86 06 99 066 250 00. La domiciliation bancaire fictive indique FR00 7676 9567 1588 2959 4460 701, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.94; la trace IPv6 associée est 2001:db8:41::7df. Le poste de travail porte l’identifiant 12345ac9-13fb-4005-a34d-01234567918a, le cookie de test est cookie-demo-00066-06305, et le gabarit biométrique est BIO-DEMO-003452 (référence vocale distincte : VOICE-TEST-00066). Le véhicule mentionné est ZZ-405-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Salomé Épilune et ajouté une note de suivi à CLT-000066-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient salomé ÉPILUNE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0887; la référence du lot est BATCH-OPS-2026-148. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Salomé Épilune |
| Date | 1988-02-09 |
| Contact | salome.epilune65@example.invalid |
| Client | CLT-000066-Q |
| Incident | INC-2026-02682 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0887 |

**Autre formulation observée.** Version importée : Salomé Épilune; date=1988-02-09; rue=26, rue des Brumes, 99900 Soleil-des-Falaises, France; téléphone=06 39 98 24 16; courriel=salome.epilune65@example.invalid; statut=à contrôler.


## Cas 067 : Support informatique | dossier fictif INC-2026-02723

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Nino Florilacier, née le 1995-07-22. Le dossier la rattache à 43, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est nino.florilacier66@example.invalid et son téléphone est 06 39 98 24 53; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 24 53. La fiche de contact porte le pseudonyme n.florilacier_519. Le compte client est CLT-000067-Q, et la référence RH éventuelle est EMP-101355. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Florilacier.

**Traitement du dossier.** Le 2025-07-04, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Jade Nacreclairon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 618,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 87 07 99 067 387 00. La domiciliation bancaire fictive indique FR00 7777 9680 1715 3090 4597 840, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.111; la trace IPv6 associée est 2001:db8:42::7fe. Le poste de travail porte l’identifiant 12345ada-1402-4006-a35a-0123456791a9, le cookie de test est cookie-demo-00067-06402, et le gabarit biométrique est BIO-DEMO-003505 (référence vocale distincte : VOICE-TEST-00067). Le véhicule mentionné est ZZ-442-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nino Florilacier et ajouté une note de suivi à CLT-000067-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0900; la référence du lot est BATCH-OPS-2026-165. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nino Florilacier |
| Date | 1995-07-22 |
| Contact | nino.florilacier66@example.invalid |
| Client | CLT-000067-Q |
| Incident | INC-2026-02723 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0900 |

**Autre formulation observée.** Le message reçu disait : « Pour Nino Florilacier, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-02723. »


## Cas 068 : Voyage / réservation | dossier fictif INC-2026-02764

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Lucile Orielserein, née le 2002-12-08. Le dossier la rattache à 60, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est lucile.orielserein67@example.invalid et son téléphone est 06 39 98 24 90; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 24 90. La fiche de contact porte le pseudonyme l.orielserein_542. Le compte client est CLT-000068-Q, et la référence RH éventuelle est EMP-101374. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Orielserein.

**Traitement du dossier.** Le 2026-10-11, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Ismaël Perrivigne, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 791,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 88 08 99 068 524 00. La domiciliation bancaire fictive indique FR00 7878 9793 1842 3221 4734 979, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.128; la trace IPv6 associée est 2001:db8:43::81d. Le poste de travail porte l’identifiant 12345aeb-1409-4007-a367-0123456791c8, le cookie de test est cookie-demo-00068-06499, et le gabarit biométrique est BIO-DEMO-003558 (référence vocale distincte : VOICE-TEST-00068). Le véhicule mentionné est ZZ-479-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lucile Orielserein et ajouté une note de suivi à CLT-000068-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0913; la référence du lot est BATCH-OPS-2026-182. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lucile Orielserein |
| Date | 2002-12-08 |
| Contact | lucile.orielserein67@example.invalid |
| Client | CLT-000068-Q |
| Incident | INC-2026-02764 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0913 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Lucile Orielserein, identifiant CLT-000068-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 069 : Marketing / consentement | dossier fictif INC-2026-02805

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Noé Érablefarin, née le 1966-05-21. Le dossier la rattache à 77, rue du Phare Éteint, 99900 Pluviane, France. Son email est noe.erablefarin68@example.invalid et son téléphone est 06 39 98 25 27; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 25 27. La fiche de contact porte le pseudonyme n.érablefarin_565. Le compte client est CLT-000069-Q, et la référence RH éventuelle est EMP-101393. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Érablefarin.

**Traitement du dossier.** Le 2025-01-18, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Yasmine Pavofleur, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 964,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 89 09 99 069 661 00. La domiciliation bancaire fictive indique FR00 7979 9906 1969 3352 4871 118, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.145; la trace IPv6 associée est 2001:db8:44::83c. Le poste de travail porte l’identifiant 12345afc-1410-4008-a374-0123456791e7, le cookie de test est cookie-demo-00069-06596, et le gabarit biométrique est BIO-DEMO-003611 (référence vocale distincte : VOICE-TEST-00069). Le véhicule mentionné est ZZ-516-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Noé Érablefarin et ajouté une note de suivi à CLT-000069-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0926; la référence du lot est BATCH-OPS-2026-199. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Noé Érablefarin |
| Date | 1966-05-21 |
| Contact | noe.erablefarin68@example.invalid |
| Client | CLT-000069-Q |
| Incident | INC-2026-02805 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0926 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Noé Érablefarin, 06 39 98 25 27, noe.erablefarin68@example.invalid; le rappel est prévu autour du 2025-01-18.”


## Cas 070 : Recherche / enquête | dossier fictif INC-2026-02846

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Sofia Valnette, née le 1973-10-07. Le dossier la rattache à 94, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est sofia.valnette69@example.invalid et son téléphone est 06 39 98 25 64; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 25 64. La fiche de contact porte le pseudonyme s.valnette_588. Le compte client est CLT-000070-Q, et la référence RH éventuelle est EMP-101412. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Valnette.

**Traitement du dossier.** Le 2026-04-25, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Mathis Noroorée, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 137,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 90 10 99 070 798 00. La domiciliation bancaire fictive indique FR00 8080 0019 2096 3483 5008 257, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.162; la trace IPv6 associée est 2001:db8:45::85b. Le poste de travail porte l’identifiant 12345b0d-1417-4009-a381-012345679206, le cookie de test est cookie-demo-00070-06693, et le gabarit biométrique est BIO-DEMO-003664 (référence vocale distincte : VOICE-TEST-00070). Le véhicule mentionné est ZZ-553-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sofia Valnette et ajouté une note de suivi à CLT-000070-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0939; la référence du lot est BATCH-OPS-2026-216. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sofia Valnette |
| Date | 1973-10-07 |
| Contact | sofia.valnette69@example.invalid |
| Client | CLT-000070-Q |
| Incident | INC-2026-02846 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-0939 |

**Autre formulation observée.** Note d’audit : le lien entre s.valnette_588, 192.0.2.162 et 12345b0d-1417-4009-a381-012345679206 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 071 : Logistique / livraison | dossier fictif INC-2026-02887

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Eden Mirasorel, née le 1980-03-20. Le dossier la rattache à 111, rue des Brumes, 99900 Cendrelac, France. Son email est eden.mirasorel70@example.invalid et son téléphone est 06 39 98 26 01; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 26 01. La fiche de contact porte le pseudonyme e.mirasorel_611. Le compte client est CLT-000071-Q, et la référence RH éventuelle est EMP-101431. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mirasorel.

**Traitement du dossier.** Le 2025-07-05, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Ambre Rosibrise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 310,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 91 11 99 071 935 00. La domiciliation bancaire fictive indique FR00 8181 0132 2223 3614 5145 396, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.179; la trace IPv6 associée est 2001:db8:46::87a. Le poste de travail porte l’identifiant 12345b1e-141e-4000-a38e-012345679225, le cookie de test est cookie-demo-00071-06790, et le gabarit biométrique est BIO-DEMO-003717 (référence vocale distincte : VOICE-TEST-00071). Le véhicule mentionné est ZZ-590-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eden Mirasorel et ajouté une note de suivi à CLT-000071-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient eden MIRASOREL; vérifier que le changement de casse ne bloque pas la détection.

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 26 01. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0952; la référence du lot est BATCH-OPS-2026-233. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eden Mirasorel |
| Date | 1980-03-20 |
| Contact | eden.mirasorel70@example.invalid |
| Client | CLT-000071-Q |
| Incident | INC-2026-02887 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-0952 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 072 : Sécurité / contrôle d’accès | dossier fictif INC-2026-02928

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Yasmine Brumemarin, née le 1987-08-06. Le dossier la rattache à 128, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est yasmine.brumemarin71@example.invalid et son téléphone est 06 39 98 26 38; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 26 38. La fiche de contact porte le pseudonyme y.brumemarin_634. Le compte client est CLT-000072-Q, et la référence RH éventuelle est EMP-101450. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Brumemarin.

**Traitement du dossier.** Le 2026-10-12, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Maël Solravel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 483,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 92 12 99 072 072 00. La domiciliation bancaire fictive indique FR00 8282 0245 2350 3745 5282 535, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.196; la trace IPv6 associée est 2001:db8:47::899. Le poste de travail porte l’identifiant 12345b2f-1425-4001-a39b-012345679244, le cookie de test est cookie-demo-00072-06887, et le gabarit biométrique est BIO-DEMO-003770 (référence vocale distincte : VOICE-TEST-00072). Le véhicule mentionné est ZZ-627-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Yasmine Brumemarin et ajouté une note de suivi à CLT-000072-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0965; la référence du lot est BATCH-OPS-2026-250. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Yasmine Brumemarin |
| Date | 1987-08-06 |
| Contact | yasmine.brumemarin71@example.invalid |
| Client | CLT-000072-Q |
| Incident | INC-2026-02928 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-0965 |

**Autre formulation observée.** Version importée : Yasmine Brumemarin; date=1987-08-06; rue=128, allée des Sept Lanternes, 99900 Églan-sur-Roche, France; téléphone=06 39 98 26 38; courriel=yasmine.brumemarin71@example.invalid; statut=à contrôler.


## Cas 073 : RH / gestion du personnel | dossier fictif INC-2026-02969

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Eliott Mélidune, née le 2010-01-19. Le dossier la rattache à 145, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est eliott.melidune72@example.invalid et son téléphone est 06 39 98 26 75; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 26 75. La fiche de contact porte le pseudonyme e.mélidune_657. Le compte client est CLT-000073-Q, et la référence RH éventuelle est EMP-101469. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mélidune.

**Traitement du dossier.** Le 2025-01-19, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Malo Avelroche, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 656,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 93 01 99 073 209 00. La domiciliation bancaire fictive indique FR00 8383 0358 2477 3876 5419 674, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.213; la trace IPv6 associée est 2001:db8:48::8b8. Le poste de travail porte l’identifiant 12345b40-142c-4002-a3a8-012345679263, le cookie de test est cookie-demo-00073-06984, et le gabarit biométrique est BIO-DEMO-003823 (référence vocale distincte : VOICE-TEST-00073). Le véhicule mentionné est ZZ-664-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eliott Mélidune et ajouté une note de suivi à CLT-000073-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2010-01-19. Le proche de référence est Malo Avelroche. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0978; la référence du lot est BATCH-OPS-2026-267. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eliott Mélidune |
| Date | 2010-01-19 |
| Contact | eliott.melidune72@example.invalid |
| Client | CLT-000073-Q |
| Incident | INC-2026-02969 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-0978 |

**Autre formulation observée.** Le message reçu disait : « Pour Eliott Mélidune, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-02969. »


## Cas 074 : CRM / relation client | dossier fictif INC-2026-03010

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Zoé Vanisac, née le 2001-06-05. Le dossier la rattache à 162, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est zoe.vanisac73@example.invalid et son téléphone est 06 39 98 27 12; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 27 12. La fiche de contact porte le pseudonyme z.vanisac_680. Le compte client est CLT-000074-Q, et la référence RH éventuelle est EMP-101488. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Vanisac.

**Traitement du dossier.** Le 2026-04-26, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Nino Tremlombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 829,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 94 02 99 074 346 00. La domiciliation bancaire fictive indique FR00 8484 0471 2604 4007 5556 813, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.230; la trace IPv6 associée est 2001:db8:49::8d7. Le poste de travail porte l’identifiant 12345b51-1433-4003-a3b5-012345679282, le cookie de test est cookie-demo-00074-07081, et le gabarit biométrique est BIO-DEMO-003876 (référence vocale distincte : VOICE-TEST-00074). Le véhicule mentionné est ZZ-701-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Zoé Vanisac et ajouté une note de suivi à CLT-000074-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-0991; la référence du lot est BATCH-OPS-2026-284. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Zoé Vanisac |
| Date | 2001-06-05 |
| Contact | zoe.vanisac73@example.invalid |
| Client | CLT-000074-Q |
| Incident | INC-2026-03010 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-0991 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Zoé Vanisac, identifiant CLT-000074-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 075 : Santé / prise de rendez-vous | dossier fictif INC-2026-03051

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Gabin Aurimousse, née le 1965-11-18. Le dossier la rattache à 179, rue des Pivoines Grises, 99900 Valmousse, France. Son email est gabin.aurimousse74@example.invalid et son téléphone est 06 39 98 27 49; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 27 49. La fiche de contact porte le pseudonyme g.aurimousse_703. Le compte client est CLT-000075-Q, et la référence RH éventuelle est EMP-101507. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Aurimousse.

**Traitement du dossier.** Le 2025-07-06, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Zoé Varnedorin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 002,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 95 03 99 075 483 00. La domiciliation bancaire fictive indique FR00 8585 0584 2731 4138 5693 952, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.247; la trace IPv6 associée est 2001:db8:4a::8f6. Le poste de travail porte l’identifiant 12345b62-143a-4004-a3c2-0123456792a1, le cookie de test est cookie-demo-00075-07178, et le gabarit biométrique est BIO-DEMO-003929 (référence vocale distincte : VOICE-TEST-00075). Le véhicule mentionné est ZZ-738-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Gabin Aurimousse et ajouté une note de suivi à CLT-000075-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1004; la référence du lot est BATCH-OPS-2026-301. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Gabin Aurimousse |
| Date | 1965-11-18 |
| Contact | gabin.aurimousse74@example.invalid |
| Client | CLT-000075-Q |
| Incident | INC-2026-03051 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1004 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Gabin Aurimousse, 06 39 98 27 49, gabin.aurimousse74@example.invalid; le rappel est prévu autour du 2025-07-06.”


## Cas 076 : Banque / assurance | dossier fictif INC-2026-03092

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Maëlys Montaroussin, née le 1972-04-04. Le dossier la rattache à 16, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est maelys.montaroussin75@example.invalid et son téléphone est 06 39 98 27 86; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 27 86. La fiche de contact porte le pseudonyme m.montaroussin_726. Le compte client est CLT-000076-Q, et la référence RH éventuelle est EMP-101526. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Montaroussin.

**Traitement du dossier.** Le 2026-10-13, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Sohan Célvaux, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 175,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 96 04 99 076 620 00. La domiciliation bancaire fictive indique FR00 8686 0697 2858 4269 5830 091, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.11; la trace IPv6 associée est 2001:db8:4b::915. Le poste de travail porte l’identifiant 12345b73-1441-4005-a3cf-0123456792c0, le cookie de test est cookie-demo-00076-07275, et le gabarit biométrique est BIO-DEMO-003982 (référence vocale distincte : VOICE-TEST-00076). Le véhicule mentionné est ZZ-775-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maëlys Montaroussin et ajouté une note de suivi à CLT-000076-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient maëlys MONTAROUSSIN; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1017; la référence du lot est BATCH-OPS-2026-318. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maëlys Montaroussin |
| Date | 1972-04-04 |
| Contact | maelys.montaroussin75@example.invalid |
| Client | CLT-000076-Q |
| Incident | INC-2026-03092 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1017 |

**Autre formulation observée.** Note d’audit : le lien entre m.montaroussin_726, 192.0.2.11 et 12345b73-1441-4005-a3cf-0123456792c0 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 077 : Éducation / accompagnement | dossier fictif INC-2026-03133

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Marceau Nivvardin, née le 1979-09-17. Le dossier la rattache à 33, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est marceau.nivvardin76@example.invalid et son téléphone est 06 39 98 28 23; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 28 23. La fiche de contact porte le pseudonyme m.nivvardin_749. Le compte client est CLT-000077-Q, et la référence RH éventuelle est EMP-101545. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nivvardin.

**Traitement du dossier.** Le 2025-01-20, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Naël Seredorelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 348,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 97 05 99 077 757 00. La domiciliation bancaire fictive indique FR00 8787 0810 2985 4400 5967 230, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.28; la trace IPv6 associée est 2001:db8:4c::934. Le poste de travail porte l’identifiant 12345b84-1448-4006-a3dc-0123456792df, le cookie de test est cookie-demo-00077-07372, et le gabarit biométrique est BIO-DEMO-004035 (référence vocale distincte : VOICE-TEST-00077). Le véhicule mentionné est ZZ-812-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Marceau Nivvardin et ajouté une note de suivi à CLT-000077-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1030; la référence du lot est BATCH-OPS-2026-335. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Marceau Nivvardin |
| Date | 1979-09-17 |
| Contact | marceau.nivvardin76@example.invalid |
| Client | CLT-000077-Q |
| Incident | INC-2026-03133 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1030 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 078 : Juridique / contrat | dossier fictif INC-2026-03174

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Léonie Virenacré, née le 1986-02-03. Le dossier la rattache à 50, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est leonie.virenacre77@example.invalid et son téléphone est 06 39 98 28 60; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 28 60. La fiche de contact porte le pseudonyme l.virenacré_772. Le compte client est CLT-000078-Q, et la référence RH éventuelle est EMP-101564. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Virenacré.

**Traitement du dossier.** Le 2026-04-27, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Léandre Églanbelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 521,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 98 06 99 078 894 00. La domiciliation bancaire fictive indique FR00 8888 0923 3112 4531 6104 369, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.45; la trace IPv6 associée est 2001:db8:4d::953. Le poste de travail porte l’identifiant 12345b95-144f-4007-a3e9-0123456792fe, le cookie de test est cookie-demo-00078-07469, et le gabarit biométrique est BIO-DEMO-004088 (référence vocale distincte : VOICE-TEST-00078). Le véhicule mentionné est ZZ-849-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léonie Virenacré et ajouté une note de suivi à CLT-000078-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 28 60. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1043; la référence du lot est BATCH-OPS-2026-352. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léonie Virenacré |
| Date | 1986-02-03 |
| Contact | leonie.virenacre77@example.invalid |
| Client | CLT-000078-Q |
| Incident | INC-2026-03174 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1043 |

**Autre formulation observée.** Version importée : Léonie Virenacré; date=1986-02-03; rue=50, rue des Nuages Bas, 99900 Noroît-les-Jardins, France; téléphone=06 39 98 28 60; courriel=leonie.virenacre77@example.invalid; statut=à contrôler.


## Cas 079 : Support informatique | dossier fictif INC-2026-03215

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Mathis Cenddombre, née le 1993-07-16. Le dossier la rattache à 67, rue du Phare Éteint, 99900 Nacréville, France. Son email est mathis.cenddombre78@example.invalid et son téléphone est 06 39 98 28 97; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 28 97. La fiche de contact porte le pseudonyme m.cenddombre_795. Le compte client est CLT-000079-Q, et la référence RH éventuelle est EMP-101583. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Cenddombre.

**Traitement du dossier.** Le 2025-07-07, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Émilie Rivbrume, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 694,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 60 07 99 079 031 00. La domiciliation bancaire fictive indique FR00 8989 1036 3239 4662 6241 508, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.62; la trace IPv6 associée est 2001:db8:4e::972. Le poste de travail porte l’identifiant 12345ba6-1456-4008-a3f6-01234567931d, le cookie de test est cookie-demo-00079-07566, et le gabarit biométrique est BIO-DEMO-004141 (référence vocale distincte : VOICE-TEST-00079). Le véhicule mentionné est ZZ-886-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mathis Cenddombre et ajouté une note de suivi à CLT-000079-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1056; la référence du lot est BATCH-OPS-2026-369. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mathis Cenddombre |
| Date | 1993-07-16 |
| Contact | mathis.cenddombre78@example.invalid |
| Client | CLT-000079-Q |
| Incident | INC-2026-03215 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1056 |

**Autre formulation observée.** Le message reçu disait : « Pour Mathis Cenddombre, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-03215. »


## Cas 080 : Voyage / réservation | dossier fictif INC-2026-03256

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Ariane Saphvialet, née le 2000-12-02. Le dossier la rattache à 84, rue des Pivoines Grises, 99900 Brumeval, France. Son email est ariane.saphvialet79@example.invalid et son téléphone est 06 39 98 29 34; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 29 34. La fiche de contact porte le pseudonyme a.saphvialet_818. Le compte client est CLT-000080-Q, et la référence RH éventuelle est EMP-101602. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Saphvialet.

**Traitement du dossier.** Le 2026-10-14, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Noé Alouloriot, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 867,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 61 08 99 080 168 00. La domiciliation bancaire fictive indique FR00 9090 1149 3366 4793 6378 647, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.79; la trace IPv6 associée est 2001:db8:4f::991. Le poste de travail porte l’identifiant 12345bb7-145d-4009-a403-01234567933c, le cookie de test est cookie-demo-00080-07663, et le gabarit biométrique est BIO-DEMO-004194 (référence vocale distincte : VOICE-TEST-00080). Le véhicule mentionné est ZZ-923-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ariane Saphvialet et ajouté une note de suivi à CLT-000080-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1069; la référence du lot est BATCH-OPS-2026-386. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ariane Saphvialet |
| Date | 2000-12-02 |
| Contact | ariane.saphvialet79@example.invalid |
| Client | CLT-000080-Q |
| Incident | INC-2026-03256 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1069 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Ariane Saphvialet, identifiant CLT-000080-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 081 : Marketing / consentement | dossier fictif INC-2026-03297

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Sohan Clairclaire, née le 1964-05-15. Le dossier la rattache à 101, rue des Brumes, 99900 Val-des-Nuages, France. Son email est sohan.clairclaire80@example.invalid et son téléphone est 06 39 98 29 71; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 29 71. La fiche de contact porte le pseudonyme s.clairclaire_841. Le compte client est CLT-000081-Q, et la référence RH éventuelle est EMP-101621. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Clairclaire.

**Traitement du dossier.** Le 2025-01-21, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Maëlys Belaubier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 040,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 62 09 99 081 305 00. La domiciliation bancaire fictive indique FR00 9191 1262 3493 4924 6515 786, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.96; la trace IPv6 associée est 2001:db8:50::9b0. Le poste de travail porte l’identifiant 12345bc8-1464-4000-a410-01234567935b, le cookie de test est cookie-demo-00081-07760, et le gabarit biométrique est BIO-DEMO-004247 (référence vocale distincte : VOICE-TEST-00081). Le véhicule mentionné est ZZ-960-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sohan Clairclaire et ajouté une note de suivi à CLT-000081-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient sohan CLAIRCLAIRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1082; la référence du lot est BATCH-OPS-2026-403. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sohan Clairclaire |
| Date | 1964-05-15 |
| Contact | sohan.clairclaire80@example.invalid |
| Client | CLT-000081-Q |
| Incident | INC-2026-03297 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1082 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Sohan Clairclaire, 06 39 98 29 71, sohan.clairclaire80@example.invalid; le rappel est prévu autour du 2025-01-21.”


## Cas 082 : Recherche / enquête | dossier fictif INC-2026-03338

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Lina Ormeplaine, née le 2011-10-01. Le dossier la rattache à 118, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est lina.ormeplaine81@example.invalid et son téléphone est 06 39 98 30 08; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 30 08. La fiche de contact porte le pseudonyme l.ormeplaine_864. Le compte client est CLT-000082-Q, et la référence RH éventuelle est EMP-101640. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Ormeplaine.

**Traitement du dossier.** Le 2026-04-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Younès Fauvevalon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 213,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 63 10 99 082 442 00. La domiciliation bancaire fictive indique FR00 9292 1375 3620 5055 6652 925, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.113; la trace IPv6 associée est 2001:db8:51::9cf. Le poste de travail porte l’identifiant 12345bd9-146b-4001-a41d-01234567937a, le cookie de test est cookie-demo-00082-07857, et le gabarit biométrique est BIO-DEMO-004300 (référence vocale distincte : VOICE-TEST-00082). Le véhicule mentionné est ZZ-997-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lina Ormeplaine et ajouté une note de suivi à CLT-000082-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2011-10-01. Le proche de référence est Younès Fauvevalon. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1095; la référence du lot est BATCH-OPS-2026-420. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lina Ormeplaine |
| Date | 2011-10-01 |
| Contact | lina.ormeplaine81@example.invalid |
| Client | CLT-000082-Q |
| Incident | INC-2026-03338 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1095 |

**Autre formulation observée.** Note d’audit : le lien entre l.ormeplaine_864, 192.0.2.113 et 12345bd9-146b-4001-a41d-01234567937a doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 083 : Logistique / livraison | dossier fictif INC-2026-03379

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Younès Pluvivelin, née le 1978-03-14. Le dossier la rattache à 135, rue des Nuages Bas, 99900 Mirebrise, France. Son email est younes.pluvivelin82@example.invalid et son téléphone est 06 39 98 30 45; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 30 45. La fiche de contact porte le pseudonyme y.pluvivelin_887. Le compte client est CLT-000083-Q, et la référence RH éventuelle est EMP-101659. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pluvivelin.

**Traitement du dossier.** Le 2025-07-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Inès Dorémeline, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 386,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 64 11 99 083 579 00. La domiciliation bancaire fictive indique FR00 9393 1488 3747 5186 6789 064, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.130; la trace IPv6 associée est 2001:db8:52::9ee. Le poste de travail porte l’identifiant 12345bea-1472-4002-a42a-012345679399, le cookie de test est cookie-demo-00083-07954, et le gabarit biométrique est BIO-DEMO-004353 (référence vocale distincte : VOICE-TEST-00083). Le véhicule mentionné est ZZ-034-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Younès Pluvivelin et ajouté une note de suivi à CLT-000083-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1108; la référence du lot est BATCH-OPS-2026-437. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Younès Pluvivelin |
| Date | 1978-03-14 |
| Contact | younes.pluvivelin82@example.invalid |
| Client | CLT-000083-Q |
| Incident | INC-2026-03379 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1108 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 084 : Sécurité / contrôle d’accès | dossier fictif INC-2026-03420

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Apolline Nacreclairon, née le 1985-08-27. Le dossier la rattache à 152, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est apolline.nacreclairon83@example.invalid et son téléphone est 06 39 98 30 82; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 30 82. La fiche de contact porte le pseudonyme a.nacreclairon_910. Le compte client est CLT-000084-Q, et la référence RH éventuelle est EMP-101678. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nacreclairon.

**Traitement du dossier.** Le 2026-10-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Anaïs Corvivalise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 559,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 65 12 99 084 716 00. La domiciliation bancaire fictive indique FR00 9494 1601 3874 5317 6926 203, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.147; la trace IPv6 associée est 2001:db8:53::a0d. Le poste de travail porte l’identifiant 12345bfb-1479-4003-a437-0123456793b8, le cookie de test est cookie-demo-00084-08051, et le gabarit biométrique est BIO-DEMO-004406 (référence vocale distincte : VOICE-TEST-00084). Le véhicule mentionné est ZZ-071-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Apolline Nacreclairon et ajouté une note de suivi à CLT-000084-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1121; la référence du lot est BATCH-OPS-2026-454. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Apolline Nacreclairon |
| Date | 1985-08-27 |
| Contact | apolline.nacreclairon83@example.invalid |
| Client | CLT-000084-Q |
| Incident | INC-2026-03420 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1121 |

**Autre formulation observée.** Version importée : Apolline Nacreclairon; date=1985-08-27; rue=152, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France; téléphone=06 39 98 30 82; courriel=apolline.nacreclairon83@example.invalid; statut=à contrôler.


## Cas 085 : RH / gestion du personnel | dossier fictif INC-2026-03461

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Romane Perrivigne, née le 1992-01-13. Le dossier la rattache à 169, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est romane.perrivigne84@example.invalid et son téléphone est 06 39 98 31 19; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 31 19. La fiche de contact porte le pseudonyme r.perrivigne_933. Le compte client est CLT-000085-Q, et la référence RH éventuelle est EMP-101697. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Perrivigne.

**Traitement du dossier.** Le 2025-01-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Clémence Lisirune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 732,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 66 01 99 085 853 00. La domiciliation bancaire fictive indique FR00 9595 1714 4001 5448 7063 342, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.164; la trace IPv6 associée est 2001:db8:54::a2c. Le poste de travail porte l’identifiant 12345c0c-1480-4004-a444-0123456793d7, le cookie de test est cookie-demo-00085-08148, et le gabarit biométrique est BIO-DEMO-004459 (référence vocale distincte : VOICE-TEST-00085). Le véhicule mentionné est ZZ-108-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Romane Perrivigne et ajouté une note de suivi à CLT-000085-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 31 19. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1134; la référence du lot est BATCH-OPS-2026-471. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Romane Perrivigne |
| Date | 1992-01-13 |
| Contact | romane.perrivigne84@example.invalid |
| Client | CLT-000085-Q |
| Incident | INC-2026-03461 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1134 |

**Autre formulation observée.** Le message reçu disait : « Pour Romane Perrivigne, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-03461. »


## Cas 086 : CRM / relation client | dossier fictif INC-2026-03502

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Ambre Pavofleur, née le 1999-06-26. Le dossier la rattache à 6, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est ambre.pavofleur85@example.invalid et son téléphone est 06 39 98 31 56; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 31 56. La fiche de contact porte le pseudonyme a.pavofleur_956. Le compte client est CLT-000086-Q, et la référence RH éventuelle est EMP-101716. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pavofleur.

**Traitement du dossier.** Le 2026-04-02, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Eden Lorimurel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 905,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 67 02 99 086 990 00. La domiciliation bancaire fictive indique FR00 9696 1827 4128 5579 7200 481, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.181; la trace IPv6 associée est 2001:db8:55::a4b. Le poste de travail porte l’identifiant 12345c1d-1487-4005-a451-0123456793f6, le cookie de test est cookie-demo-00086-08245, et le gabarit biométrique est BIO-DEMO-004512 (référence vocale distincte : VOICE-TEST-00086). Le véhicule mentionné est ZZ-145-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ambre Pavofleur et ajouté une note de suivi à CLT-000086-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ambre PAVOFLEUR; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1147; la référence du lot est BATCH-OPS-2026-488. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ambre Pavofleur |
| Date | 1999-06-26 |
| Contact | ambre.pavofleur85@example.invalid |
| Client | CLT-000086-Q |
| Incident | INC-2026-03502 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1147 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Ambre Pavofleur, identifiant CLT-000086-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 087 : Santé / prise de rendez-vous | dossier fictif INC-2026-03543

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Théo Noroorée, née le 1963-11-12. Le dossier la rattache à 23, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est theo.norooree86@example.invalid et son téléphone est 06 39 98 31 93; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 31 93. La fiche de contact porte le pseudonyme t.noroorée_979. Le compte client est CLT-000087-Q, et la référence RH éventuelle est EMP-101735. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Noroorée.

**Traitement du dossier.** Le 2025-07-09, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Léonie Briscendre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 078,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 68 03 99 087 127 00. La domiciliation bancaire fictive indique FR00 9797 1940 4255 5710 7337 620, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.198; la trace IPv6 associée est 2001:db8:56::a6a. Le poste de travail porte l’identifiant 12345c2e-148e-4006-a45e-012345679415, le cookie de test est cookie-demo-00087-08342, et le gabarit biométrique est BIO-DEMO-004565 (référence vocale distincte : VOICE-TEST-00087). Le véhicule mentionné est ZZ-182-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Théo Noroorée et ajouté une note de suivi à CLT-000087-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1160; la référence du lot est BATCH-OPS-2026-505. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Théo Noroorée |
| Date | 1963-11-12 |
| Contact | theo.norooree86@example.invalid |
| Client | CLT-000087-Q |
| Incident | INC-2026-03543 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1160 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Théo Noroorée, 06 39 98 31 93, theo.norooree86@example.invalid; le rappel est prévu autour du 2025-07-09.”


## Cas 088 : Banque / assurance | dossier fictif INC-2026-03584

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Naël Rosibrise, née le 1970-04-25. Le dossier la rattache à 40, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est nael.rosibrise87@example.invalid et son téléphone est 06 39 98 32 30; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 32 30. La fiche de contact porte le pseudonyme n.rosibrise_003. Le compte client est CLT-000088-Q, et la référence RH éventuelle est EMP-101754. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rosibrise.

**Traitement du dossier.** Le 2026-10-16, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Romane Lunémistral, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 251,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 69 04 99 088 264 00. La domiciliation bancaire fictive indique FR00 9898 2053 4382 5841 7474 759, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.215; la trace IPv6 associée est 2001:db8:57::a89. Le poste de travail porte l’identifiant 12345c3f-1495-4007-a46b-012345679434, le cookie de test est cookie-demo-00088-08439, et le gabarit biométrique est BIO-DEMO-004618 (référence vocale distincte : VOICE-TEST-00088). Le véhicule mentionné est ZZ-219-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Naël Rosibrise et ajouté une note de suivi à CLT-000088-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1173; la référence du lot est BATCH-OPS-2026-522. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Naël Rosibrise |
| Date | 1970-04-25 |
| Contact | nael.rosibrise87@example.invalid |
| Client | CLT-000088-Q |
| Incident | INC-2026-03584 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1173 |

**Autre formulation observée.** Note d’audit : le lien entre n.rosibrise_003, 192.0.2.215 et 12345c3f-1495-4007-a46b-012345679434 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 089 : Éducation / accompagnement | dossier fictif INC-2026-03625

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Titouan Solravel, née le 1977-09-11. Le dossier la rattache à 57, rue du Phare Éteint, 99900 Pluviane, France. Son email est titouan.solravel88@example.invalid et son téléphone est 06 39 98 32 67; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 32 67. La fiche de contact porte le pseudonyme t.solravel_026. Le compte client est CLT-000089-Q, et la référence RH éventuelle est EMP-101773. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Solravel.

**Traitement du dossier.** Le 2025-01-23, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Mélina Épilune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 424,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 70 05 99 089 401 00. La domiciliation bancaire fictive indique FR00 9999 2166 4509 5972 7611 898, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.232; la trace IPv6 associée est 2001:db8:58::aa8. Le poste de travail porte l’identifiant 12345c50-149c-4008-a478-012345679453, le cookie de test est cookie-demo-00089-08536, et le gabarit biométrique est BIO-DEMO-004671 (référence vocale distincte : VOICE-TEST-00089). Le véhicule mentionné est ZZ-256-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Titouan Solravel et ajouté une note de suivi à CLT-000089-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1186; la référence du lot est BATCH-OPS-2026-539. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Titouan Solravel |
| Date | 1977-09-11 |
| Contact | titouan.solravel88@example.invalid |
| Client | CLT-000089-Q |
| Incident | INC-2026-03625 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1186 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 090 : Juridique / contrat | dossier fictif INC-2026-03666

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Inès Avelroche, née le 1984-02-24. Le dossier la rattache à 74, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est ines.avelroche89@example.invalid et son téléphone est 06 39 98 33 04; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 33 04. La fiche de contact porte le pseudonyme i.avelroche_049. Le compte client est CLT-000090-Q, et la référence RH éventuelle est EMP-101792. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Avelroche.

**Traitement du dossier.** Le 2026-04-03, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Bastien Florilacier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 497,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 71 06 99 090 538 00. La domiciliation bancaire fictive indique FR00 0100 2279 4636 6103 7748 037, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.249; la trace IPv6 associée est 2001:db8:59::ac7. Le poste de travail porte l’identifiant 12345c61-14a3-4009-a485-012345679472, le cookie de test est cookie-demo-00090-08633, et le gabarit biométrique est BIO-DEMO-004724 (référence vocale distincte : VOICE-TEST-00090). Le véhicule mentionné est ZZ-293-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Inès Avelroche et ajouté une note de suivi à CLT-000090-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1199; la référence du lot est BATCH-OPS-2026-556. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Inès Avelroche |
| Date | 1984-02-24 |
| Contact | ines.avelroche89@example.invalid |
| Client | CLT-000090-Q |
| Incident | INC-2026-03666 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1199 |

**Autre formulation observée.** Version importée : Inès Avelroche; date=1984-02-24; rue=74, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France; téléphone=06 39 98 33 04; courriel=ines.avelroche89@example.invalid; statut=à contrôler.


## Cas 091 : Support informatique | dossier fictif INC-2026-03707

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Mila Tremlombre, née le 2012-07-10. Le dossier la rattache à 91, rue des Brumes, 99900 Cendrelac, France. Son email est mila.tremlombre90@example.invalid et son téléphone est 06 39 98 33 41; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 33 41. La fiche de contact porte le pseudonyme m.tremlombre_072. Le compte client est CLT-000091-Q, et la référence RH éventuelle est EMP-101811. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Tremlombre.

**Traitement du dossier.** Le 2025-07-10, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Salomé Orielserein, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 670,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 72 07 99 091 675 00. La domiciliation bancaire fictive indique FR00 0201 2392 4763 6234 7885 176, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.13; la trace IPv6 associée est 2001:db8:5a::ae6. Le poste de travail porte l’identifiant 12345c72-14aa-4000-a492-012345679491, le cookie de test est cookie-demo-00091-08730, et le gabarit biométrique est BIO-DEMO-004777 (référence vocale distincte : VOICE-TEST-00091). Le véhicule mentionné est ZZ-330-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mila Tremlombre et ajouté une note de suivi à CLT-000091-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient mila TREMLOMBRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2012-07-10. Le proche de référence est Salomé Orielserein. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1212; la référence du lot est BATCH-OPS-2026-573. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mila Tremlombre |
| Date | 2012-07-10 |
| Contact | mila.tremlombre90@example.invalid |
| Client | CLT-000091-Q |
| Incident | INC-2026-03707 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1212 |

**Autre formulation observée.** Le message reçu disait : « Pour Mila Tremlombre, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-03707. »


## Cas 092 : Voyage / réservation | dossier fictif INC-2026-03748

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Mélina Varnedorin, née le 1998-12-23. Le dossier la rattache à 108, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est melina.varnedorin91@example.invalid et son téléphone est 06 39 98 33 78; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 33 78. La fiche de contact porte le pseudonyme m.varnedorin_095. Le compte client est CLT-000092-Q, et la référence RH éventuelle est EMP-101830. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Varnedorin.

**Traitement du dossier.** Le 2026-10-17, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Eliott Érablefarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 843,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 73 08 99 092 812 00. La domiciliation bancaire fictive indique FR00 0302 2505 4890 6365 8022 315, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.30; la trace IPv6 associée est 2001:db8:5b::b05. Le poste de travail porte l’identifiant 12345c83-14b1-4001-a49f-0123456794b0, le cookie de test est cookie-demo-00092-08827, et le gabarit biométrique est BIO-DEMO-004830 (référence vocale distincte : VOICE-TEST-00092). Le véhicule mentionné est ZZ-367-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mélina Varnedorin et ajouté une note de suivi à CLT-000092-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 33 78. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1225; la référence du lot est BATCH-OPS-2026-590. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mélina Varnedorin |
| Date | 1998-12-23 |
| Contact | melina.varnedorin91@example.invalid |
| Client | CLT-000092-Q |
| Incident | INC-2026-03748 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1225 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Mélina Varnedorin, identifiant CLT-000092-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 093 : Marketing / consentement | dossier fictif INC-2026-03789

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Maël Célvaux, née le 2005-05-09. Le dossier la rattache à 125, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est mael.celvaux92@example.invalid et son téléphone est 06 39 98 34 15; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 34 15. La fiche de contact porte le pseudonyme m.célvaux_118. Le compte client est CLT-000093-Q, et la référence RH éventuelle est EMP-101849. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Célvaux.

**Traitement du dossier.** Le 2025-01-24, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Ariane Valnette, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 016,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 74 09 99 093 949 00. La domiciliation bancaire fictive indique FR00 0403 2618 5017 6496 8159 454, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.47; la trace IPv6 associée est 2001:db8:5c::b24. Le poste de travail porte l’identifiant 12345c94-14b8-4002-a4ac-0123456794cf, le cookie de test est cookie-demo-00093-08924, et le gabarit biométrique est BIO-DEMO-004883 (référence vocale distincte : VOICE-TEST-00093). Le véhicule mentionné est ZZ-404-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maël Célvaux et ajouté une note de suivi à CLT-000093-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1238; la référence du lot est BATCH-OPS-2026-607. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maël Célvaux |
| Date | 2005-05-09 |
| Contact | mael.celvaux92@example.invalid |
| Client | CLT-000093-Q |
| Incident | INC-2026-03789 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1238 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Maël Célvaux, 06 39 98 34 15, mael.celvaux92@example.invalid; le rappel est prévu autour du 2025-01-24.”


## Cas 094 : Recherche / enquête | dossier fictif INC-2026-03830

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Célestin Seredorelle, née le 1969-10-22. Le dossier la rattache à 142, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est celestin.seredorelle93@example.invalid et son téléphone est 06 39 98 34 52; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 34 52. La fiche de contact porte le pseudonyme c.seredorelle_141. Le compte client est CLT-000094-Q, et la référence RH éventuelle est EMP-101868. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Seredorelle.

**Traitement du dossier.** Le 2026-04-04, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Théo Mirasorel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 189,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 75 10 99 094 086 00. La domiciliation bancaire fictive indique FR00 0504 2731 5144 6627 8296 593, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.64; la trace IPv6 associée est 2001:db8:5d::b43. Le poste de travail porte l’identifiant 12345ca5-14bf-4003-a4b9-0123456794ee, le cookie de test est cookie-demo-00094-09021, et le gabarit biométrique est BIO-DEMO-004936 (référence vocale distincte : VOICE-TEST-00094). Le véhicule mentionné est ZZ-441-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Célestin Seredorelle et ajouté une note de suivi à CLT-000094-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1251; la référence du lot est BATCH-OPS-2026-624. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Célestin Seredorelle |
| Date | 1969-10-22 |
| Contact | celestin.seredorelle93@example.invalid |
| Client | CLT-000094-Q |
| Incident | INC-2026-03830 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1251 |

**Autre formulation observée.** Note d’audit : le lien entre c.seredorelle_141, 192.0.2.64 et 12345ca5-14bf-4003-a4b9-0123456794ee doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 095 : Logistique / livraison | dossier fictif INC-2026-03871

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Léandre Églanbelle, née le 1976-03-08. Le dossier la rattache à 159, rue des Pivoines Grises, 99900 Valmousse, France. Son email est leandre.eglanbelle94@example.invalid et son téléphone est 06 39 98 34 89; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 34 89. La fiche de contact porte le pseudonyme l.églanbelle_164. Le compte client est CLT-000095-Q, et la référence RH éventuelle est EMP-101887. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Églanbelle.

**Traitement du dossier.** Le 2025-07-11, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Célestin Brumemarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 362,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 76 11 99 095 223 00. La domiciliation bancaire fictive indique FR00 0605 2844 5271 6758 8433 732, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.81; la trace IPv6 associée est 2001:db8:5e::b62. Le poste de travail porte l’identifiant 12345cb6-14c6-4004-a4c6-01234567950d, le cookie de test est cookie-demo-00095-09118, et le gabarit biométrique est BIO-DEMO-004989 (référence vocale distincte : VOICE-TEST-00095). Le véhicule mentionné est ZZ-478-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léandre Églanbelle et ajouté une note de suivi à CLT-000095-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1264; la référence du lot est BATCH-OPS-2026-641. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léandre Églanbelle |
| Date | 1976-03-08 |
| Contact | leandre.eglanbelle94@example.invalid |
| Client | CLT-000095-Q |
| Incident | INC-2026-03871 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1264 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 096 : Sécurité / contrôle d’accès | dossier fictif INC-2026-03912

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Nora Rivbrume, née le 1983-08-21. Le dossier la rattache à 176, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est nora.rivbrume95@example.invalid et son téléphone est 06 39 98 35 26; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 35 26. La fiche de contact porte le pseudonyme n.rivbrume_187. Le compte client est CLT-000096-Q, et la référence RH éventuelle est EMP-101906. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rivbrume.

**Traitement du dossier.** Le 2026-10-18, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Ilyan Mélidune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 535,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 77 12 99 096 360 00. La domiciliation bancaire fictive indique FR00 0706 2957 5398 6889 8570 871, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.98; la trace IPv6 associée est 2001:db8:5f::b81. Le poste de travail porte l’identifiant 12345cc7-14cd-4005-a4d3-01234567952c, le cookie de test est cookie-demo-00096-09215, et le gabarit biométrique est BIO-DEMO-005042 (référence vocale distincte : VOICE-TEST-00096). Le véhicule mentionné est ZZ-515-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nora Rivbrume et ajouté une note de suivi à CLT-000096-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient nora RIVBRUME; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1277; la référence du lot est BATCH-OPS-2026-658. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nora Rivbrume |
| Date | 1983-08-21 |
| Contact | nora.rivbrume95@example.invalid |
| Client | CLT-000096-Q |
| Incident | INC-2026-03912 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1277 |

**Autre formulation observée.** Version importée : Nora Rivbrume; date=1983-08-21; rue=176, rue des Brumes, 99900 Virelune-les-Pins, France; téléphone=06 39 98 35 26; courriel=nora.rivbrume95@example.invalid; statut=à contrôler.


## Cas 097 : RH / gestion du personnel | dossier fictif INC-2026-03953

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Anaïs Alouloriot, née le 1990-01-07. Le dossier la rattache à 13, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est anais.alouloriot96@example.invalid et son téléphone est 06 39 98 35 63; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 35 63. La fiche de contact porte le pseudonyme a.alouloriot_210. Le compte client est CLT-000097-Q, et la référence RH éventuelle est EMP-101925. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Alouloriot.

**Traitement du dossier.** Le 2025-01-25, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Lucile Vanisac, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 708,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 78 01 99 097 497 00. La domiciliation bancaire fictive indique FR00 0807 3070 5525 7020 8707 010, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.115; la trace IPv6 associée est 2001:db8:60::ba0. Le poste de travail porte l’identifiant 12345cd8-14d4-4006-a4e0-01234567954b, le cookie de test est cookie-demo-00097-09312, et le gabarit biométrique est BIO-DEMO-005095 (référence vocale distincte : VOICE-TEST-00097). Le véhicule mentionné est ZZ-552-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Anaïs Alouloriot et ajouté une note de suivi à CLT-000097-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1290; la référence du lot est BATCH-OPS-2026-675. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Anaïs Alouloriot |
| Date | 1990-01-07 |
| Contact | anais.alouloriot96@example.invalid |
| Client | CLT-000097-Q |
| Incident | INC-2026-03953 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1290 |

**Autre formulation observée.** Le message reçu disait : « Pour Anaïs Alouloriot, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-03953. »


## Cas 098 : CRM / relation client | dossier fictif INC-2026-03994

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Jade Belaubier, née le 1997-06-20. Le dossier la rattache à 30, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est jade.belaubier00@example.invalid et son téléphone est 06 39 98 36 00; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 36 00. La fiche de contact porte le pseudonyme j.belaubier_233. Le compte client est CLT-000098-Q, et la référence RH éventuelle est EMP-101944. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Belaubier.

**Traitement du dossier.** Le 2026-04-05, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Gabin Aurimousse, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 881,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 79 02 99 098 634 00. La domiciliation bancaire fictive indique FR00 0908 3183 5652 7151 8844 149, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.132; la trace IPv6 associée est 2001:db8:61::bbf. Le poste de travail porte l’identifiant 12345ce9-14db-4007-a4ed-01234567956a, le cookie de test est cookie-demo-00098-09409, et le gabarit biométrique est BIO-DEMO-005148 (référence vocale distincte : VOICE-TEST-00098). Le véhicule mentionné est ZZ-589-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Jade Belaubier et ajouté une note de suivi à CLT-000098-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1303; la référence du lot est BATCH-OPS-2026-692. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Jade Belaubier |
| Date | 1997-06-20 |
| Contact | jade.belaubier00@example.invalid |
| Client | CLT-000098-Q |
| Incident | INC-2026-03994 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1303 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Jade Belaubier, identifiant CLT-000098-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 099 : Santé / prise de rendez-vous | dossier fictif INC-2026-04035

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Bastien Fauvevalon, née le 2004-11-06. Le dossier la rattache à 47, rue du Phare Éteint, 99900 Nacréville, France. Son email est bastien.fauvevalon01@example.invalid et son téléphone est 06 39 98 36 37; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 36 37. La fiche de contact porte le pseudonyme b.fauvevalon_256. Le compte client est CLT-000099-Q, et la référence RH éventuelle est EMP-101963. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Fauvevalon.

**Traitement du dossier.** Le 2025-07-12, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Lina Montaroussin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 054,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 80 03 99 099 771 00. La domiciliation bancaire fictive indique FR00 1009 3296 5779 7282 8981 288, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.149; la trace IPv6 associée est 2001:db8:62::bde. Le poste de travail porte l’identifiant 12345cfa-14e2-4008-a4fa-012345679589, le cookie de test est cookie-demo-00099-09506, et le gabarit biométrique est BIO-DEMO-005201 (référence vocale distincte : VOICE-TEST-00099). Le véhicule mentionné est ZZ-626-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Bastien Fauvevalon et ajouté une note de suivi à CLT-000099-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 36 37. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1316; la référence du lot est BATCH-OPS-2026-709. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Bastien Fauvevalon |
| Date | 2004-11-06 |
| Contact | bastien.fauvevalon01@example.invalid |
| Client | CLT-000099-Q |
| Incident | INC-2026-04035 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1316 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Bastien Fauvevalon, 06 39 98 36 37, bastien.fauvevalon01@example.invalid; le rappel est prévu autour du 2025-07-12.”


## Cas 100 : Banque / assurance | dossier fictif INC-2026-04076

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Malo Dorémeline, née le 2013-04-19. Le dossier la rattache à 64, rue des Pivoines Grises, 99900 Brumeval, France. Son email est malo.doremeline02@example.invalid et son téléphone est 06 39 98 36 74; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 36 74. La fiche de contact porte le pseudonyme m.dorémeline_279. Le compte client est CLT-000100-Q, et la référence RH éventuelle est EMP-101982. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Dorémeline.

**Traitement du dossier.** Le 2026-10-19, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Titouan Nivvardin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 227,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 81 04 99 100 908 00. La domiciliation bancaire fictive indique FR00 1110 3409 5906 7413 9118 427, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.166; la trace IPv6 associée est 2001:db8:63::bfd. Le poste de travail porte l’identifiant 12345d0b-14e9-4009-a507-0123456795a8, le cookie de test est cookie-demo-00100-09603, et le gabarit biométrique est BIO-DEMO-005254 (référence vocale distincte : VOICE-TEST-00100). Le véhicule mentionné est ZZ-663-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Malo Dorémeline et ajouté une note de suivi à CLT-000100-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2013-04-19. Le proche de référence est Titouan Nivvardin. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1329; la référence du lot est BATCH-OPS-2026-726. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Malo Dorémeline |
| Date | 2013-04-19 |
| Contact | malo.doremeline02@example.invalid |
| Client | CLT-000100-Q |
| Incident | INC-2026-04076 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1329 |

**Autre formulation observée.** Note d’audit : le lien entre m.dorémeline_279, 192.0.2.166 et 12345d0b-14e9-4009-a507-0123456795a8 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 101 : Éducation / accompagnement | dossier fictif INC-2026-04117

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Ilyan Corvivalise, née le 1975-09-05. Le dossier la rattache à 81, rue des Brumes, 99900 Val-des-Nuages, France. Son email est ilyan.corvivalise03@example.invalid et son téléphone est 06 39 98 37 11; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 37 11. La fiche de contact porte le pseudonyme i.corvivalise_302. Le compte client est CLT-000101-Q, et la référence RH éventuelle est EMP-102001. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Corvivalise.

**Traitement du dossier.** Le 2025-01-26, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Nora Virenacré, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 400,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 82 05 99 101 045 00. La domiciliation bancaire fictive indique FR00 1211 3522 6033 7544 9255 566, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.183; la trace IPv6 associée est 2001:db8:64::c1c. Le poste de travail porte l’identifiant 12345d1c-14f0-4000-a514-0123456795c7, le cookie de test est cookie-demo-00101-09700, et le gabarit biométrique est BIO-DEMO-005307 (référence vocale distincte : VOICE-TEST-00101). Le véhicule mentionné est ZZ-700-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ilyan Corvivalise et ajouté une note de suivi à CLT-000101-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ilyan CORVIVALISE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1342; la référence du lot est BATCH-OPS-2026-743. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ilyan Corvivalise |
| Date | 1975-09-05 |
| Contact | ilyan.corvivalise03@example.invalid |
| Client | CLT-000101-Q |
| Incident | INC-2026-04117 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1342 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 102 : Juridique / contrat | dossier fictif INC-2026-04158

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Émilie Lisirune, née le 1982-02-18. Le dossier la rattache à 98, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est emilie.lisirune04@example.invalid et son téléphone est 06 39 98 37 48; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 37 48. La fiche de contact porte le pseudonyme é.lisirune_325. Le compte client est CLT-000102-Q, et la référence RH éventuelle est EMP-102020. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lisirune.

**Traitement du dossier.** Le 2026-04-06, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Lison Cenddombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 573,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 83 06 99 102 182 00. La domiciliation bancaire fictive indique FR00 1312 3635 6160 7675 9392 705, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.200; la trace IPv6 associée est 2001:db8:65::c3b. Le poste de travail porte l’identifiant 12345d2d-14f7-4001-a521-0123456795e6, le cookie de test est cookie-demo-00102-09797, et le gabarit biométrique est BIO-DEMO-005360 (référence vocale distincte : VOICE-TEST-00102). Le véhicule mentionné est ZZ-737-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Émilie Lisirune et ajouté une note de suivi à CLT-000102-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1355; la référence du lot est BATCH-OPS-2026-760. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Émilie Lisirune |
| Date | 1982-02-18 |
| Contact | emilie.lisirune04@example.invalid |
| Client | CLT-000102-Q |
| Incident | INC-2026-04158 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1355 |

**Autre formulation observée.** Version importée : Émilie Lisirune; date=1982-02-18; rue=98, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France; téléphone=06 39 98 37 48; courriel=emilie.lisirune04@example.invalid; statut=à contrôler.


## Cas 103 : Support informatique | dossier fictif INC-2026-04199

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Lison Lorimurel, née le 1989-07-04. Le dossier la rattache à 115, rue des Nuages Bas, 99900 Mirebrise, France. Son email est lison.lorimurel05@example.invalid et son téléphone est 06 39 98 37 85; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 37 85. La fiche de contact porte le pseudonyme l.lorimurel_348. Le compte client est CLT-000103-Q, et la référence RH éventuelle est EMP-102039. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lorimurel.

**Traitement du dossier.** Le 2025-07-13, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Sofia Saphvialet, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 746,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 84 07 99 103 319 00. La domiciliation bancaire fictive indique FR00 1413 3748 6287 7806 9529 844, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.217; la trace IPv6 associée est 2001:db8:66::c5a. Le poste de travail porte l’identifiant 12345d3e-14fe-4002-a52e-012345679605, le cookie de test est cookie-demo-00103-09894, et le gabarit biométrique est BIO-DEMO-005413 (référence vocale distincte : VOICE-TEST-00103). Le véhicule mentionné est ZZ-774-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lison Lorimurel et ajouté une note de suivi à CLT-000103-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1368; la référence du lot est BATCH-OPS-2026-777. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lison Lorimurel |
| Date | 1989-07-04 |
| Contact | lison.lorimurel05@example.invalid |
| Client | CLT-000103-Q |
| Incident | INC-2026-04199 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1368 |

**Autre formulation observée.** Le message reçu disait : « Pour Lison Lorimurel, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-04199. »


## Cas 104 : Voyage / réservation | dossier fictif INC-2026-04240

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Clémence Briscendre, née le 1996-12-17. Le dossier la rattache à 132, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est clemence.briscendre06@example.invalid et son téléphone est 06 39 98 38 22; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 38 22. La fiche de contact porte le pseudonyme c.briscendre_371. Le compte client est CLT-000104-Q, et la référence RH éventuelle est EMP-102058. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Briscendre.

**Traitement du dossier.** Le 2026-10-20, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Marceau Clairclaire, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 919,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 85 08 99 104 456 00. La domiciliation bancaire fictive indique FR00 1514 3861 6414 7937 9666 983, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.234; la trace IPv6 associée est 2001:db8:67::c79. Le poste de travail porte l’identifiant 12345d4f-1505-4003-a53b-012345679624, le cookie de test est cookie-demo-00104-09991, et le gabarit biométrique est BIO-DEMO-005466 (référence vocale distincte : VOICE-TEST-00104). Le véhicule mentionné est ZZ-811-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Clémence Briscendre et ajouté une note de suivi à CLT-000104-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1381; la référence du lot est BATCH-OPS-2026-794. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Clémence Briscendre |
| Date | 1996-12-17 |
| Contact | clemence.briscendre06@example.invalid |
| Client | CLT-000104-Q |
| Incident | INC-2026-04240 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1381 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Clémence Briscendre, identifiant CLT-000104-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 105 : Marketing / consentement | dossier fictif INC-2026-04281

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Ismaël Lunémistral, née le 2003-05-03. Le dossier la rattache à 149, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est ismael.lunemistral07@example.invalid et son téléphone est 06 39 98 38 59; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 38 59. La fiche de contact porte le pseudonyme i.lunémistral_394. Le compte client est CLT-000105-Q, et la référence RH éventuelle est EMP-102077. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lunémistral.

**Traitement du dossier.** Le 2025-01-27, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Apolline Ormeplaine, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 092,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 86 09 99 105 593 00. La domiciliation bancaire fictive indique FR00 1615 3974 6541 8068 9803 122, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.251; la trace IPv6 associée est 2001:db8:68::c98. Le poste de travail porte l’identifiant 12345d60-150c-4004-a548-012345679643, le cookie de test est cookie-demo-00105-10088, et le gabarit biométrique est BIO-DEMO-005519 (référence vocale distincte : VOICE-TEST-00105). Le véhicule mentionné est ZZ-848-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ismaël Lunémistral et ajouté une note de suivi à CLT-000105-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1394; la référence du lot est BATCH-OPS-2026-811. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ismaël Lunémistral |
| Date | 2003-05-03 |
| Contact | ismael.lunemistral07@example.invalid |
| Client | CLT-000105-Q |
| Incident | INC-2026-04281 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1394 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Ismaël Lunémistral, 06 39 98 38 59, ismael.lunemistral07@example.invalid; le rappel est prévu autour du 2025-01-27.”


## Cas 106 : Recherche / enquête | dossier fictif INC-2026-04322

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Salomé Épilune, née le 1967-10-16. Le dossier la rattache à 166, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est salome.epilune08@example.invalid et son téléphone est 06 39 98 38 96; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 38 96. La fiche de contact porte le pseudonyme s.épilune_417. Le compte client est CLT-000106-Q, et la référence RH éventuelle est EMP-102096. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Épilune.

**Traitement du dossier.** Le 2026-04-07, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Mila Pluvivelin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 265,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 87 10 99 106 730 00. La domiciliation bancaire fictive indique FR00 1716 4087 6668 8199 9940 261, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.15; la trace IPv6 associée est 2001:db8:69::cb7. Le poste de travail porte l’identifiant 12345d71-1513-4005-a555-012345679662, le cookie de test est cookie-demo-00106-10185, et le gabarit biométrique est BIO-DEMO-005572 (référence vocale distincte : VOICE-TEST-00106). Le véhicule mentionné est ZZ-885-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Salomé Épilune et ajouté une note de suivi à CLT-000106-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient salomé ÉPILUNE; vérifier que le changement de casse ne bloque pas la détection.

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 38 96. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1407; la référence du lot est BATCH-OPS-2026-828. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Salomé Épilune |
| Date | 1967-10-16 |
| Contact | salome.epilune08@example.invalid |
| Client | CLT-000106-Q |
| Incident | INC-2026-04322 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1407 |

**Autre formulation observée.** Note d’audit : le lien entre s.épilune_417, 192.0.2.15 et 12345d71-1513-4005-a555-012345679662 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 107 : Logistique / livraison | dossier fictif INC-2026-04363

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Nino Florilacier, née le 1974-03-02. Le dossier la rattache à 3, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est nino.florilacier09@example.invalid et son téléphone est 06 39 98 39 33; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 39 33. La fiche de contact porte le pseudonyme n.florilacier_440. Le compte client est CLT-000107-Q, et la référence RH éventuelle est EMP-102115. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Florilacier.

**Traitement du dossier.** Le 2025-07-14, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Jade Nacreclairon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 438,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 88 11 99 107 867 00. La domiciliation bancaire fictive indique FR00 1817 4200 6795 8330 0077 400, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.32; la trace IPv6 associée est 2001:db8:6a::cd6. Le poste de travail porte l’identifiant 12345d82-151a-4006-a562-012345679681, le cookie de test est cookie-demo-00107-10282, et le gabarit biométrique est BIO-DEMO-005625 (référence vocale distincte : VOICE-TEST-00107). Le véhicule mentionné est ZZ-922-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nino Florilacier et ajouté une note de suivi à CLT-000107-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1420; la référence du lot est BATCH-OPS-2026-845. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nino Florilacier |
| Date | 1974-03-02 |
| Contact | nino.florilacier09@example.invalid |
| Client | CLT-000107-Q |
| Incident | INC-2026-04363 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1420 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 108 : Sécurité / contrôle d’accès | dossier fictif INC-2026-04404

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Lucile Orielserein, née le 1981-08-15. Le dossier la rattache à 20, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est lucile.orielserein10@example.invalid et son téléphone est 06 39 98 39 70; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 39 70. La fiche de contact porte le pseudonyme l.orielserein_463. Le compte client est CLT-000108-Q, et la référence RH éventuelle est EMP-102134. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Orielserein.

**Traitement du dossier.** Le 2026-10-21, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Ismaël Perrivigne, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 611,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 89 12 99 108 004 00. La domiciliation bancaire fictive indique FR00 1918 4313 6922 8461 0214 539, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.49; la trace IPv6 associée est 2001:db8:6b::cf5. Le poste de travail porte l’identifiant 12345d93-1521-4007-a56f-0123456796a0, le cookie de test est cookie-demo-00108-10379, et le gabarit biométrique est BIO-DEMO-005678 (référence vocale distincte : VOICE-TEST-00108). Le véhicule mentionné est ZZ-959-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lucile Orielserein et ajouté une note de suivi à CLT-000108-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1433; la référence du lot est BATCH-OPS-2026-862. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lucile Orielserein |
| Date | 1981-08-15 |
| Contact | lucile.orielserein10@example.invalid |
| Client | CLT-000108-Q |
| Incident | INC-2026-04404 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1433 |

**Autre formulation observée.** Version importée : Lucile Orielserein; date=1981-08-15; rue=20, rue des Nuages Bas, 99900 Aubier-des-Marées, France; téléphone=06 39 98 39 70; courriel=lucile.orielserein10@example.invalid; statut=à contrôler.


## Cas 109 : RH / gestion du personnel | dossier fictif INC-2026-04445

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Noé Érablefarin, née le 2014-01-01. Le dossier la rattache à 37, rue du Phare Éteint, 99900 Pluviane, France. Son email est noe.erablefarin11@example.invalid et son téléphone est 06 39 98 40 07; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 40 07. La fiche de contact porte le pseudonyme n.érablefarin_486. Le compte client est CLT-000109-Q, et la référence RH éventuelle est EMP-102153. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Érablefarin.

**Traitement du dossier.** Le 2025-01-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Yasmine Pavofleur, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 784,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 90 01 99 109 141 00. La domiciliation bancaire fictive indique FR00 2019 4426 7049 8592 0351 678, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.66; la trace IPv6 associée est 2001:db8:6c::d14. Le poste de travail porte l’identifiant 12345da4-1528-4008-a57c-0123456796bf, le cookie de test est cookie-demo-00109-10476, et le gabarit biométrique est BIO-DEMO-005731 (référence vocale distincte : VOICE-TEST-00109). Le véhicule mentionné est ZZ-996-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Noé Érablefarin et ajouté une note de suivi à CLT-000109-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2014-01-01. Le proche de référence est Yasmine Pavofleur. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1446; la référence du lot est BATCH-OPS-2026-879. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Noé Érablefarin |
| Date | 2014-01-01 |
| Contact | noe.erablefarin11@example.invalid |
| Client | CLT-000109-Q |
| Incident | INC-2026-04445 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1446 |

**Autre formulation observée.** Le message reçu disait : « Pour Noé Érablefarin, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-04445. »


## Cas 110 : CRM / relation client | dossier fictif INC-2026-04486

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Sofia Valnette, née le 1995-06-14. Le dossier la rattache à 54, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est sofia.valnette12@example.invalid et son téléphone est 06 39 98 40 44; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 40 44. La fiche de contact porte le pseudonyme s.valnette_509. Le compte client est CLT-000110-Q, et la référence RH éventuelle est EMP-102172. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Valnette.

**Traitement du dossier.** Le 2026-04-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Mathis Noroorée, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 957,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 91 02 99 110 278 00. La domiciliation bancaire fictive indique FR00 2120 4539 7176 8723 0488 817, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.83; la trace IPv6 associée est 2001:db8:6d::d33. Le poste de travail porte l’identifiant 12345db5-152f-4009-a589-0123456796de, le cookie de test est cookie-demo-00110-10573, et le gabarit biométrique est BIO-DEMO-005784 (référence vocale distincte : VOICE-TEST-00110). Le véhicule mentionné est ZZ-033-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sofia Valnette et ajouté une note de suivi à CLT-000110-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1459; la référence du lot est BATCH-OPS-2026-896. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sofia Valnette |
| Date | 1995-06-14 |
| Contact | sofia.valnette12@example.invalid |
| Client | CLT-000110-Q |
| Incident | INC-2026-04486 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1459 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Sofia Valnette, identifiant CLT-000110-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 111 : Santé / prise de rendez-vous | dossier fictif INC-2026-04527

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Eden Mirasorel, née le 2002-11-27. Le dossier la rattache à 71, rue des Brumes, 99900 Cendrelac, France. Son email est eden.mirasorel13@example.invalid et son téléphone est 06 39 98 40 81; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 40 81. La fiche de contact porte le pseudonyme e.mirasorel_532. Le compte client est CLT-000111-Q, et la référence RH éventuelle est EMP-102191. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mirasorel.

**Traitement du dossier.** Le 2025-07-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Ambre Rosibrise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 130,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 92 03 99 111 415 00. La domiciliation bancaire fictive indique FR00 2221 4652 7303 8854 0625 956, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.100; la trace IPv6 associée est 2001:db8:6e::d52. Le poste de travail porte l’identifiant 12345dc6-1536-4000-a596-0123456796fd, le cookie de test est cookie-demo-00111-10670, et le gabarit biométrique est BIO-DEMO-005837 (référence vocale distincte : VOICE-TEST-00111). Le véhicule mentionné est ZZ-070-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eden Mirasorel et ajouté une note de suivi à CLT-000111-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient eden MIRASOREL; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1472; la référence du lot est BATCH-OPS-2026-913. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eden Mirasorel |
| Date | 2002-11-27 |
| Contact | eden.mirasorel13@example.invalid |
| Client | CLT-000111-Q |
| Incident | INC-2026-04527 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1472 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Eden Mirasorel, 06 39 98 40 81, eden.mirasorel13@example.invalid; le rappel est prévu autour du 2025-07-15.”


## Cas 112 : Banque / assurance | dossier fictif INC-2026-04568

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Yasmine Brumemarin, née le 1966-04-13. Le dossier la rattache à 88, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est yasmine.brumemarin14@example.invalid et son téléphone est 06 39 98 41 18; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 41 18. La fiche de contact porte le pseudonyme y.brumemarin_555. Le compte client est CLT-000112-Q, et la référence RH éventuelle est EMP-102210. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Brumemarin.

**Traitement du dossier.** Le 2026-10-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Maël Solravel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 303,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 93 04 99 112 552 00. La domiciliation bancaire fictive indique FR00 2322 4765 7430 8985 0762 095, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.117; la trace IPv6 associée est 2001:db8:6f::d71. Le poste de travail porte l’identifiant 12345dd7-153d-4001-a5a3-01234567971c, le cookie de test est cookie-demo-00112-10767, et le gabarit biométrique est BIO-DEMO-005890 (référence vocale distincte : VOICE-TEST-00112). Le véhicule mentionné est ZZ-107-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Yasmine Brumemarin et ajouté une note de suivi à CLT-000112-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1485; la référence du lot est BATCH-OPS-2026-930. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Yasmine Brumemarin |
| Date | 1966-04-13 |
| Contact | yasmine.brumemarin14@example.invalid |
| Client | CLT-000112-Q |
| Incident | INC-2026-04568 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1485 |

**Autre formulation observée.** Note d’audit : le lien entre y.brumemarin_555, 192.0.2.117 et 12345dd7-153d-4001-a5a3-01234567971c doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 113 : Éducation / accompagnement | dossier fictif INC-2026-04609

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Eliott Mélidune, née le 1973-09-26. Le dossier la rattache à 105, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est eliott.melidune15@example.invalid et son téléphone est 06 39 98 41 55; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 41 55. La fiche de contact porte le pseudonyme e.mélidune_578. Le compte client est CLT-000113-Q, et la référence RH éventuelle est EMP-102229. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mélidune.

**Traitement du dossier.** Le 2025-01-02, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Malo Avelroche, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 476,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 94 05 99 113 689 00. La domiciliation bancaire fictive indique FR00 2423 4878 7557 9116 0899 234, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.134; la trace IPv6 associée est 2001:db8:70::d90. Le poste de travail porte l’identifiant 12345de8-1544-4002-a5b0-01234567973b, le cookie de test est cookie-demo-00113-10864, et le gabarit biométrique est BIO-DEMO-005943 (référence vocale distincte : VOICE-TEST-00113). Le véhicule mentionné est ZZ-144-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eliott Mélidune et ajouté une note de suivi à CLT-000113-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 41 55. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1498; la référence du lot est BATCH-OPS-2026-947. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eliott Mélidune |
| Date | 1973-09-26 |
| Contact | eliott.melidune15@example.invalid |
| Client | CLT-000113-Q |
| Incident | INC-2026-04609 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1498 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 114 : Juridique / contrat | dossier fictif INC-2026-04650

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Zoé Vanisac, née le 1980-02-12. Le dossier la rattache à 122, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est zoe.vanisac16@example.invalid et son téléphone est 06 39 98 41 92; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 41 92. La fiche de contact porte le pseudonyme z.vanisac_601. Le compte client est CLT-000114-Q, et la référence RH éventuelle est EMP-102248. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Vanisac.

**Traitement du dossier.** Le 2026-04-09, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Nino Tremlombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 649,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 95 06 99 114 826 00. La domiciliation bancaire fictive indique FR00 2524 4991 7684 9247 1036 373, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.151; la trace IPv6 associée est 2001:db8:71::daf. Le poste de travail porte l’identifiant 12345df9-154b-4003-a5bd-01234567975a, le cookie de test est cookie-demo-00114-10961, et le gabarit biométrique est BIO-DEMO-005996 (référence vocale distincte : VOICE-TEST-00114). Le véhicule mentionné est ZZ-181-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Zoé Vanisac et ajouté une note de suivi à CLT-000114-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1511; la référence du lot est BATCH-OPS-2026-964. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Zoé Vanisac |
| Date | 1980-02-12 |
| Contact | zoe.vanisac16@example.invalid |
| Client | CLT-000114-Q |
| Incident | INC-2026-04650 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1511 |

**Autre formulation observée.** Version importée : Zoé Vanisac; date=1980-02-12; rue=122, rue du Phare Éteint, 99900 Orée-du-Mistral, France; téléphone=06 39 98 41 92; courriel=zoe.vanisac16@example.invalid; statut=à contrôler.


## Cas 115 : Support informatique | dossier fictif INC-2026-04691

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Gabin Aurimousse, née le 1987-07-25. Le dossier la rattache à 139, rue des Pivoines Grises, 99900 Valmousse, France. Son email est gabin.aurimousse17@example.invalid et son téléphone est 06 39 98 42 29; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 42 29. La fiche de contact porte le pseudonyme g.aurimousse_624. Le compte client est CLT-000115-Q, et la référence RH éventuelle est EMP-102267. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Aurimousse.

**Traitement du dossier.** Le 2025-07-16, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Zoé Varnedorin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 822,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 96 07 99 115 963 00. La domiciliation bancaire fictive indique FR00 2625 5104 7811 9378 1173 512, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.168; la trace IPv6 associée est 2001:db8:72::dce. Le poste de travail porte l’identifiant 12345e0a-1552-4004-a5ca-012345679779, le cookie de test est cookie-demo-00115-11058, et le gabarit biométrique est BIO-DEMO-006049 (référence vocale distincte : VOICE-TEST-00115). Le véhicule mentionné est ZZ-218-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Gabin Aurimousse et ajouté une note de suivi à CLT-000115-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1524; la référence du lot est BATCH-OPS-2026-981. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Gabin Aurimousse |
| Date | 1987-07-25 |
| Contact | gabin.aurimousse17@example.invalid |
| Client | CLT-000115-Q |
| Incident | INC-2026-04691 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1524 |

**Autre formulation observée.** Le message reçu disait : « Pour Gabin Aurimousse, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-04691. »


## Cas 116 : Voyage / réservation | dossier fictif INC-2026-04732

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Maëlys Montaroussin, née le 1994-12-11. Le dossier la rattache à 156, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est maelys.montaroussin18@example.invalid et son téléphone est 06 39 98 42 66; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 42 66. La fiche de contact porte le pseudonyme m.montaroussin_647. Le compte client est CLT-000116-Q, et la référence RH éventuelle est EMP-102286. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Montaroussin.

**Traitement du dossier.** Le 2026-10-23, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Sohan Célvaux, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 995,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 97 08 99 116 100 00. La domiciliation bancaire fictive indique FR00 2726 5217 7938 9509 1310 651, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.185; la trace IPv6 associée est 2001:db8:73::ded. Le poste de travail porte l’identifiant 12345e1b-1559-4005-a5d7-012345679798, le cookie de test est cookie-demo-00116-11155, et le gabarit biométrique est BIO-DEMO-006102 (référence vocale distincte : VOICE-TEST-00116). Le véhicule mentionné est ZZ-255-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maëlys Montaroussin et ajouté une note de suivi à CLT-000116-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient maëlys MONTAROUSSIN; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1537; la référence du lot est BATCH-OPS-2026-998. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maëlys Montaroussin |
| Date | 1994-12-11 |
| Contact | maelys.montaroussin18@example.invalid |
| Client | CLT-000116-Q |
| Incident | INC-2026-04732 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1537 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Maëlys Montaroussin, identifiant CLT-000116-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 117 : Marketing / consentement | dossier fictif INC-2026-04773

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Marceau Nivvardin, née le 2001-05-24. Le dossier la rattache à 173, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est marceau.nivvardin19@example.invalid et son téléphone est 06 39 98 43 03; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 43 03. La fiche de contact porte le pseudonyme m.nivvardin_670. Le compte client est CLT-000117-Q, et la référence RH éventuelle est EMP-102305. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nivvardin.

**Traitement du dossier.** Le 2025-01-03, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Naël Seredorelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 168,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 98 09 99 117 237 00. La domiciliation bancaire fictive indique FR00 2827 5330 8065 9640 1447 790, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.202; la trace IPv6 associée est 2001:db8:74::e0c. Le poste de travail porte l’identifiant 12345e2c-1560-4006-a5e4-0123456797b7, le cookie de test est cookie-demo-00117-11252, et le gabarit biométrique est BIO-DEMO-006155 (référence vocale distincte : VOICE-TEST-00117). Le véhicule mentionné est ZZ-292-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Marceau Nivvardin et ajouté une note de suivi à CLT-000117-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1550; la référence du lot est BATCH-OPS-2026-016. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Marceau Nivvardin |
| Date | 2001-05-24 |
| Contact | marceau.nivvardin19@example.invalid |
| Client | CLT-000117-Q |
| Incident | INC-2026-04773 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1550 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Marceau Nivvardin, 06 39 98 43 03, marceau.nivvardin19@example.invalid; le rappel est prévu autour du 2025-01-03.”


## Cas 118 : Recherche / enquête | dossier fictif INC-2026-04814

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Léonie Virenacré, née le 2015-10-10. Le dossier la rattache à 10, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est leonie.virenacre20@example.invalid et son téléphone est 06 39 98 43 40; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 43 40. La fiche de contact porte le pseudonyme l.virenacré_693. Le compte client est CLT-000118-Q, et la référence RH éventuelle est EMP-102324. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Virenacré.

**Traitement du dossier.** Le 2026-04-10, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Léandre Églanbelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 341,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 60 10 99 118 374 00. La domiciliation bancaire fictive indique FR00 2928 5443 8192 9771 1584 929, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.219; la trace IPv6 associée est 2001:db8:75::e2b. Le poste de travail porte l’identifiant 12345e3d-1567-4007-a5f1-0123456797d6, le cookie de test est cookie-demo-00118-11349, et le gabarit biométrique est BIO-DEMO-006208 (référence vocale distincte : VOICE-TEST-00118). Le véhicule mentionné est ZZ-329-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léonie Virenacré et ajouté une note de suivi à CLT-000118-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2015-10-10. Le proche de référence est Léandre Églanbelle. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1563; la référence du lot est BATCH-OPS-2026-033. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léonie Virenacré |
| Date | 2015-10-10 |
| Contact | leonie.virenacre20@example.invalid |
| Client | CLT-000118-Q |
| Incident | INC-2026-04814 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1563 |

**Autre formulation observée.** Note d’audit : le lien entre l.virenacré_693, 192.0.2.219 et 12345e3d-1567-4007-a5f1-0123456797d6 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 119 : Logistique / livraison | dossier fictif INC-2026-04855

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Mathis Cenddombre, née le 1972-03-23. Le dossier la rattache à 27, rue du Phare Éteint, 99900 Nacréville, France. Son email est mathis.cenddombre21@example.invalid et son téléphone est 06 39 98 43 77; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 43 77. La fiche de contact porte le pseudonyme m.cenddombre_716. Le compte client est CLT-000119-Q, et la référence RH éventuelle est EMP-102343. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Cenddombre.

**Traitement du dossier.** Le 2025-07-17, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Émilie Rivbrume, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 414,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 61 11 99 119 511 00. La domiciliation bancaire fictive indique FR00 3029 5556 8319 9902 1721 068, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.236; la trace IPv6 associée est 2001:db8:76::e4a. Le poste de travail porte l’identifiant 12345e4e-156e-4008-a5fe-0123456797f5, le cookie de test est cookie-demo-00119-11446, et le gabarit biométrique est BIO-DEMO-006261 (référence vocale distincte : VOICE-TEST-00119). Le véhicule mentionné est ZZ-366-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mathis Cenddombre et ajouté une note de suivi à CLT-000119-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1576; la référence du lot est BATCH-OPS-2026-050. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mathis Cenddombre |
| Date | 1972-03-23 |
| Contact | mathis.cenddombre21@example.invalid |
| Client | CLT-000119-Q |
| Incident | INC-2026-04855 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1576 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 120 : Sécurité / contrôle d’accès | dossier fictif INC-2026-04896

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Ariane Saphvialet, née le 1979-08-09. Le dossier la rattache à 44, rue des Pivoines Grises, 99900 Brumeval, France. Son email est ariane.saphvialet22@example.invalid et son téléphone est 06 39 98 44 14; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 44 14. La fiche de contact porte le pseudonyme a.saphvialet_739. Le compte client est CLT-000120-Q, et la référence RH éventuelle est EMP-102362. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Saphvialet.

**Traitement du dossier.** Le 2026-10-24, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Noé Alouloriot, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 587,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 62 12 99 120 648 00. La domiciliation bancaire fictive indique FR00 3130 5669 8446 0033 1858 207, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.253; la trace IPv6 associée est 2001:db8:77::e69. Le poste de travail porte l’identifiant 12345e5f-1575-4009-a60b-012345679814, le cookie de test est cookie-demo-00120-11543, et le gabarit biométrique est BIO-DEMO-006314 (référence vocale distincte : VOICE-TEST-00120). Le véhicule mentionné est ZZ-403-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ariane Saphvialet et ajouté une note de suivi à CLT-000120-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 44 14. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1589; la référence du lot est BATCH-OPS-2026-067. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ariane Saphvialet |
| Date | 1979-08-09 |
| Contact | ariane.saphvialet22@example.invalid |
| Client | CLT-000120-Q |
| Incident | INC-2026-04896 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1589 |

**Autre formulation observée.** Version importée : Ariane Saphvialet; date=1979-08-09; rue=44, rue des Pivoines Grises, 99900 Brumeval, France; téléphone=06 39 98 44 14; courriel=ariane.saphvialet22@example.invalid; statut=à contrôler.


## Cas 121 : RH / gestion du personnel | dossier fictif INC-2026-04937

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Sohan Clairclaire, née le 1986-01-22. Le dossier la rattache à 61, rue des Brumes, 99900 Val-des-Nuages, France. Son email est sohan.clairclaire23@example.invalid et son téléphone est 06 39 98 44 51; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 44 51. La fiche de contact porte le pseudonyme s.clairclaire_762. Le compte client est CLT-000121-Q, et la référence RH éventuelle est EMP-102381. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Clairclaire.

**Traitement du dossier.** Le 2025-01-04, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Maëlys Belaubier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 760,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 63 01 99 121 785 00. La domiciliation bancaire fictive indique FR00 3231 5782 8573 0164 1995 346, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.17; la trace IPv6 associée est 2001:db8:78::e88. Le poste de travail porte l’identifiant 12345e70-157c-4000-a618-012345679833, le cookie de test est cookie-demo-00121-11640, et le gabarit biométrique est BIO-DEMO-006367 (référence vocale distincte : VOICE-TEST-00121). Le véhicule mentionné est ZZ-440-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sohan Clairclaire et ajouté une note de suivi à CLT-000121-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient sohan CLAIRCLAIRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1602; la référence du lot est BATCH-OPS-2026-084. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sohan Clairclaire |
| Date | 1986-01-22 |
| Contact | sohan.clairclaire23@example.invalid |
| Client | CLT-000121-Q |
| Incident | INC-2026-04937 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1602 |

**Autre formulation observée.** Le message reçu disait : « Pour Sohan Clairclaire, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-04937. »


## Cas 122 : CRM / relation client | dossier fictif INC-2026-04978

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Lina Ormeplaine, née le 1993-06-08. Le dossier la rattache à 78, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est lina.ormeplaine24@example.invalid et son téléphone est 06 39 98 44 88; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 44 88. La fiche de contact porte le pseudonyme l.ormeplaine_785. Le compte client est CLT-000122-Q, et la référence RH éventuelle est EMP-102400. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Ormeplaine.

**Traitement du dossier.** Le 2026-04-11, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Younès Fauvevalon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 933,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 64 02 99 122 922 00. La domiciliation bancaire fictive indique FR00 3332 5895 8700 0295 2132 485, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.34; la trace IPv6 associée est 2001:db8:79::ea7. Le poste de travail porte l’identifiant 12345e81-1583-4001-a625-012345679852, le cookie de test est cookie-demo-00122-11737, et le gabarit biométrique est BIO-DEMO-006420 (référence vocale distincte : VOICE-TEST-00122). Le véhicule mentionné est ZZ-477-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lina Ormeplaine et ajouté une note de suivi à CLT-000122-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1615; la référence du lot est BATCH-OPS-2026-101. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lina Ormeplaine |
| Date | 1993-06-08 |
| Contact | lina.ormeplaine24@example.invalid |
| Client | CLT-000122-Q |
| Incident | INC-2026-04978 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1615 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Lina Ormeplaine, identifiant CLT-000122-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 123 : Santé / prise de rendez-vous | dossier fictif INC-2026-05019

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Younès Pluvivelin, née le 2000-11-21. Le dossier la rattache à 95, rue des Nuages Bas, 99900 Mirebrise, France. Son email est younes.pluvivelin25@example.invalid et son téléphone est 06 39 98 45 25; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 45 25. La fiche de contact porte le pseudonyme y.pluvivelin_808. Le compte client est CLT-000123-Q, et la référence RH éventuelle est EMP-102419. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pluvivelin.

**Traitement du dossier.** Le 2025-07-18, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Inès Dorémeline, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 106,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 65 03 99 123 059 00. La domiciliation bancaire fictive indique FR00 3433 6008 8827 0426 2269 624, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.51; la trace IPv6 associée est 2001:db8:7a::ec6. Le poste de travail porte l’identifiant 12345e92-158a-4002-a632-012345679871, le cookie de test est cookie-demo-00123-11834, et le gabarit biométrique est BIO-DEMO-006473 (référence vocale distincte : VOICE-TEST-00123). Le véhicule mentionné est ZZ-514-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Younès Pluvivelin et ajouté une note de suivi à CLT-000123-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1628; la référence du lot est BATCH-OPS-2026-118. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Younès Pluvivelin |
| Date | 2000-11-21 |
| Contact | younes.pluvivelin25@example.invalid |
| Client | CLT-000123-Q |
| Incident | INC-2026-05019 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1628 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Younès Pluvivelin, 06 39 98 45 25, younes.pluvivelin25@example.invalid; le rappel est prévu autour du 2025-07-18.”


## Cas 124 : Banque / assurance | dossier fictif INC-2026-05060

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Apolline Nacreclairon, née le 1964-04-07. Le dossier la rattache à 112, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est apolline.nacreclairon26@example.invalid et son téléphone est 06 39 98 45 62; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 45 62. La fiche de contact porte le pseudonyme a.nacreclairon_831. Le compte client est CLT-000124-Q, et la référence RH éventuelle est EMP-102438. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nacreclairon.

**Traitement du dossier.** Le 2026-10-25, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Anaïs Corvivalise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 279,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 66 04 99 124 196 00. La domiciliation bancaire fictive indique FR00 3534 6121 8954 0557 2406 763, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.68; la trace IPv6 associée est 2001:db8:7b::ee5. Le poste de travail porte l’identifiant 12345ea3-1591-4003-a63f-012345679890, le cookie de test est cookie-demo-00124-11931, et le gabarit biométrique est BIO-DEMO-006526 (référence vocale distincte : VOICE-TEST-00124). Le véhicule mentionné est ZZ-551-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Apolline Nacreclairon et ajouté une note de suivi à CLT-000124-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1641; la référence du lot est BATCH-OPS-2026-135. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Apolline Nacreclairon |
| Date | 1964-04-07 |
| Contact | apolline.nacreclairon26@example.invalid |
| Client | CLT-000124-Q |
| Incident | INC-2026-05060 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1641 |

**Autre formulation observée.** Note d’audit : le lien entre a.nacreclairon_831, 192.0.2.68 et 12345ea3-1591-4003-a63f-012345679890 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 125 : Éducation / accompagnement | dossier fictif INC-2026-05101

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Romane Perrivigne, née le 1971-09-20. Le dossier la rattache à 129, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est romane.perrivigne27@example.invalid et son téléphone est 06 39 98 45 99; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 45 99. La fiche de contact porte le pseudonyme r.perrivigne_854. Le compte client est CLT-000125-Q, et la référence RH éventuelle est EMP-102457. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Perrivigne.

**Traitement du dossier.** Le 2025-01-05, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Clémence Lisirune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 452,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 67 05 99 125 333 00. La domiciliation bancaire fictive indique FR00 3635 6234 9081 0688 2543 902, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.85; la trace IPv6 associée est 2001:db8:7c::f04. Le poste de travail porte l’identifiant 12345eb4-1598-4004-a64c-0123456798af, le cookie de test est cookie-demo-00125-12028, et le gabarit biométrique est BIO-DEMO-006579 (référence vocale distincte : VOICE-TEST-00125). Le véhicule mentionné est ZZ-588-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Romane Perrivigne et ajouté une note de suivi à CLT-000125-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1654; la référence du lot est BATCH-OPS-2026-152. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Romane Perrivigne |
| Date | 1971-09-20 |
| Contact | romane.perrivigne27@example.invalid |
| Client | CLT-000125-Q |
| Incident | INC-2026-05101 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1654 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 126 : Juridique / contrat | dossier fictif INC-2026-05142

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Ambre Pavofleur, née le 1978-02-06. Le dossier la rattache à 146, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est ambre.pavofleur28@example.invalid et son téléphone est 06 39 98 46 36; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 46 36. La fiche de contact porte le pseudonyme a.pavofleur_877. Le compte client est CLT-000126-Q, et la référence RH éventuelle est EMP-102476. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pavofleur.

**Traitement du dossier.** Le 2026-04-12, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Eden Lorimurel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 625,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 68 06 99 126 470 00. La domiciliation bancaire fictive indique FR00 3736 6347 9208 0819 2680 041, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.102; la trace IPv6 associée est 2001:db8:7d::f23. Le poste de travail porte l’identifiant 12345ec5-159f-4005-a659-0123456798ce, le cookie de test est cookie-demo-00126-12125, et le gabarit biométrique est BIO-DEMO-006632 (référence vocale distincte : VOICE-TEST-00126). Le véhicule mentionné est ZZ-625-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ambre Pavofleur et ajouté une note de suivi à CLT-000126-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ambre PAVOFLEUR; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1667; la référence du lot est BATCH-OPS-2026-169. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ambre Pavofleur |
| Date | 1978-02-06 |
| Contact | ambre.pavofleur28@example.invalid |
| Client | CLT-000126-Q |
| Incident | INC-2026-05142 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1667 |

**Autre formulation observée.** Version importée : Ambre Pavofleur; date=1978-02-06; rue=146, rue des Brumes, 99900 Soleil-des-Falaises, France; téléphone=06 39 98 46 36; courriel=ambre.pavofleur28@example.invalid; statut=à contrôler.


## Cas 127 : Support informatique | dossier fictif INC-2026-05183

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Théo Noroorée, née le 2016-07-19. Le dossier la rattache à 163, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est theo.norooree29@example.invalid et son téléphone est 06 39 98 46 73; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 46 73. La fiche de contact porte le pseudonyme t.noroorée_900. Le compte client est CLT-000127-Q, et la référence RH éventuelle est EMP-102495. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Noroorée.

**Traitement du dossier.** Le 2025-07-19, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Léonie Briscendre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 798,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 69 07 99 127 607 00. La domiciliation bancaire fictive indique FR00 3837 6460 9335 0950 2817 180, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.119; la trace IPv6 associée est 2001:db8:7e::f42. Le poste de travail porte l’identifiant 12345ed6-15a6-4006-a666-0123456798ed, le cookie de test est cookie-demo-00127-12222, et le gabarit biométrique est BIO-DEMO-006685 (référence vocale distincte : VOICE-TEST-00127). Le véhicule mentionné est ZZ-662-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Théo Noroorée et ajouté une note de suivi à CLT-000127-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 46 73. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2016-07-19. Le proche de référence est Léonie Briscendre. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1680; la référence du lot est BATCH-OPS-2026-186. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Théo Noroorée |
| Date | 2016-07-19 |
| Contact | theo.norooree29@example.invalid |
| Client | CLT-000127-Q |
| Incident | INC-2026-05183 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1680 |

**Autre formulation observée.** Le message reçu disait : « Pour Théo Noroorée, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-05183. »


## Cas 128 : Voyage / réservation | dossier fictif INC-2026-05224

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Naël Rosibrise, née le 1992-12-05. Le dossier la rattache à 180, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est nael.rosibrise30@example.invalid et son téléphone est 06 39 98 47 10; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 47 10. La fiche de contact porte le pseudonyme n.rosibrise_923. Le compte client est CLT-000128-Q, et la référence RH éventuelle est EMP-102514. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rosibrise.

**Traitement du dossier.** Le 2026-10-26, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Romane Lunémistral, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 971,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 70 08 99 128 744 00. La domiciliation bancaire fictive indique FR00 3938 6573 9462 1081 2954 319, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.136; la trace IPv6 associée est 2001:db8:7f::f61. Le poste de travail porte l’identifiant 12345ee7-15ad-4007-a673-01234567990c, le cookie de test est cookie-demo-00128-12319, et le gabarit biométrique est BIO-DEMO-006738 (référence vocale distincte : VOICE-TEST-00128). Le véhicule mentionné est ZZ-699-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Naël Rosibrise et ajouté une note de suivi à CLT-000128-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1693; la référence du lot est BATCH-OPS-2026-203. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Naël Rosibrise |
| Date | 1992-12-05 |
| Contact | nael.rosibrise30@example.invalid |
| Client | CLT-000128-Q |
| Incident | INC-2026-05224 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1693 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Naël Rosibrise, identifiant CLT-000128-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 129 : Marketing / consentement | dossier fictif INC-2026-05265

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Titouan Solravel, née le 1999-05-18. Le dossier la rattache à 17, rue du Phare Éteint, 99900 Pluviane, France. Son email est titouan.solravel31@example.invalid et son téléphone est 06 39 98 47 47; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 47 47. La fiche de contact porte le pseudonyme t.solravel_946. Le compte client est CLT-000129-Q, et la référence RH éventuelle est EMP-102533. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Solravel.

**Traitement du dossier.** Le 2025-01-06, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Mélina Épilune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 144,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 71 09 99 129 881 00. La domiciliation bancaire fictive indique FR00 4039 6686 9589 1212 3091 458, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.153; la trace IPv6 associée est 2001:db8:80::f80. Le poste de travail porte l’identifiant 12345ef8-15b4-4008-a680-01234567992b, le cookie de test est cookie-demo-00129-12416, et le gabarit biométrique est BIO-DEMO-006791 (référence vocale distincte : VOICE-TEST-00129). Le véhicule mentionné est ZZ-736-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Titouan Solravel et ajouté une note de suivi à CLT-000129-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1706; la référence du lot est BATCH-OPS-2026-220. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Titouan Solravel |
| Date | 1999-05-18 |
| Contact | titouan.solravel31@example.invalid |
| Client | CLT-000129-Q |
| Incident | INC-2026-05265 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1706 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Titouan Solravel, 06 39 98 47 47, titouan.solravel31@example.invalid; le rappel est prévu autour du 2025-01-06.”


## Cas 130 : Recherche / enquête | dossier fictif INC-2026-05306

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Inès Avelroche, née le 1963-10-04. Le dossier la rattache à 34, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est ines.avelroche32@example.invalid et son téléphone est 06 39 98 47 84; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 47 84. La fiche de contact porte le pseudonyme i.avelroche_969. Le compte client est CLT-000130-Q, et la référence RH éventuelle est EMP-102552. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Avelroche.

**Traitement du dossier.** Le 2026-04-13, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Bastien Florilacier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 317,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 72 10 99 130 018 00. La domiciliation bancaire fictive indique FR00 4140 6799 9716 1343 3228 597, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.170; la trace IPv6 associée est 2001:db8:81::f9f. Le poste de travail porte l’identifiant 12345f09-15bb-4009-a68d-01234567994a, le cookie de test est cookie-demo-00130-12513, et le gabarit biométrique est BIO-DEMO-006844 (référence vocale distincte : VOICE-TEST-00130). Le véhicule mentionné est ZZ-773-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Inès Avelroche et ajouté une note de suivi à CLT-000130-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1719; la référence du lot est BATCH-OPS-2026-237. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Inès Avelroche |
| Date | 1963-10-04 |
| Contact | ines.avelroche32@example.invalid |
| Client | CLT-000130-Q |
| Incident | INC-2026-05306 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1719 |

**Autre formulation observée.** Note d’audit : le lien entre i.avelroche_969, 192.0.2.170 et 12345f09-15bb-4009-a68d-01234567994a doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 131 : Logistique / livraison | dossier fictif INC-2026-05347

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Mila Tremlombre, née le 1970-03-17. Le dossier la rattache à 51, rue des Brumes, 99900 Cendrelac, France. Son email est mila.tremlombre33@example.invalid et son téléphone est 06 39 98 48 21; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 48 21. La fiche de contact porte le pseudonyme m.tremlombre_992. Le compte client est CLT-000131-Q, et la référence RH éventuelle est EMP-102571. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Tremlombre.

**Traitement du dossier.** Le 2025-07-20, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Salomé Orielserein, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 490,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 73 11 99 131 155 00. La domiciliation bancaire fictive indique FR00 4241 6912 9843 1474 3365 736, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.187; la trace IPv6 associée est 2001:db8:82::fbe. Le poste de travail porte l’identifiant 12345f1a-15c2-4000-a69a-012345679969, le cookie de test est cookie-demo-00131-12610, et le gabarit biométrique est BIO-DEMO-006897 (référence vocale distincte : VOICE-TEST-00131). Le véhicule mentionné est ZZ-810-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mila Tremlombre et ajouté une note de suivi à CLT-000131-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient mila TREMLOMBRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1732; la référence du lot est BATCH-OPS-2026-254. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mila Tremlombre |
| Date | 1970-03-17 |
| Contact | mila.tremlombre33@example.invalid |
| Client | CLT-000131-Q |
| Incident | INC-2026-05347 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1732 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 132 : Sécurité / contrôle d’accès | dossier fictif INC-2026-05388

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Mélina Varnedorin, née le 1977-08-03. Le dossier la rattache à 68, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est melina.varnedorin34@example.invalid et son téléphone est 06 39 98 48 58; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 48 58. La fiche de contact porte le pseudonyme m.varnedorin_016. Le compte client est CLT-000132-Q, et la référence RH éventuelle est EMP-102590. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Varnedorin.

**Traitement du dossier.** Le 2026-10-27, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Eliott Érablefarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 663,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 74 12 99 132 292 00. La domiciliation bancaire fictive indique FR00 4342 7025 9970 1605 3502 875, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.204; la trace IPv6 associée est 2001:db8:83::fdd. Le poste de travail porte l’identifiant 12345f2b-15c9-4001-a6a7-012345679988, le cookie de test est cookie-demo-00132-12707, et le gabarit biométrique est BIO-DEMO-006950 (référence vocale distincte : VOICE-TEST-00132). Le véhicule mentionné est ZZ-847-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mélina Varnedorin et ajouté une note de suivi à CLT-000132-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1745; la référence du lot est BATCH-OPS-2026-271. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mélina Varnedorin |
| Date | 1977-08-03 |
| Contact | melina.varnedorin34@example.invalid |
| Client | CLT-000132-Q |
| Incident | INC-2026-05388 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1745 |

**Autre formulation observée.** Version importée : Mélina Varnedorin; date=1977-08-03; rue=68, allée des Sept Lanternes, 99900 Églan-sur-Roche, France; téléphone=06 39 98 48 58; courriel=melina.varnedorin34@example.invalid; statut=à contrôler.


## Cas 133 : RH / gestion du personnel | dossier fictif INC-2026-05429

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Maël Célvaux, née le 1984-01-16. Le dossier la rattache à 85, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est mael.celvaux35@example.invalid et son téléphone est 06 39 98 48 95; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 48 95. La fiche de contact porte le pseudonyme m.célvaux_039. Le compte client est CLT-000133-Q, et la référence RH éventuelle est EMP-102609. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Célvaux.

**Traitement du dossier.** Le 2025-01-07, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Ariane Valnette, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 836,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 75 01 99 133 429 00. La domiciliation bancaire fictive indique FR00 4443 7138 0097 1736 3639 014, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.221; la trace IPv6 associée est 2001:db8:84::ffc. Le poste de travail porte l’identifiant 12345f3c-15d0-4002-a6b4-0123456799a7, le cookie de test est cookie-demo-00133-12804, et le gabarit biométrique est BIO-DEMO-007003 (référence vocale distincte : VOICE-TEST-00133). Le véhicule mentionné est ZZ-884-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maël Célvaux et ajouté une note de suivi à CLT-000133-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1758; la référence du lot est BATCH-OPS-2026-288. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maël Célvaux |
| Date | 1984-01-16 |
| Contact | mael.celvaux35@example.invalid |
| Client | CLT-000133-Q |
| Incident | INC-2026-05429 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1758 |

**Autre formulation observée.** Le message reçu disait : « Pour Maël Célvaux, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-05429. »


## Cas 134 : CRM / relation client | dossier fictif INC-2026-05470

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Célestin Seredorelle, née le 1991-06-02. Le dossier la rattache à 102, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est celestin.seredorelle36@example.invalid et son téléphone est 06 39 98 49 32; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 49 32. La fiche de contact porte le pseudonyme c.seredorelle_062. Le compte client est CLT-000134-Q, et la référence RH éventuelle est EMP-102628. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Seredorelle.

**Traitement du dossier.** Le 2026-04-14, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Théo Mirasorel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 009,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 76 02 99 134 566 00. La domiciliation bancaire fictive indique FR00 4544 7251 0224 1867 3776 153, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.238; la trace IPv6 associée est 2001:db8:85::101b. Le poste de travail porte l’identifiant 12345f4d-15d7-4003-a6c1-0123456799c6, le cookie de test est cookie-demo-00134-12901, et le gabarit biométrique est BIO-DEMO-007056 (référence vocale distincte : VOICE-TEST-00134). Le véhicule mentionné est ZZ-921-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Célestin Seredorelle et ajouté une note de suivi à CLT-000134-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 49 32. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1771; la référence du lot est BATCH-OPS-2026-305. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Célestin Seredorelle |
| Date | 1991-06-02 |
| Contact | celestin.seredorelle36@example.invalid |
| Client | CLT-000134-Q |
| Incident | INC-2026-05470 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1771 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Célestin Seredorelle, identifiant CLT-000134-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 135 : Santé / prise de rendez-vous | dossier fictif INC-2026-05511

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Léandre Églanbelle, née le 1998-11-15. Le dossier la rattache à 119, rue des Pivoines Grises, 99900 Valmousse, France. Son email est leandre.eglanbelle37@example.invalid et son téléphone est 06 39 98 49 69; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 49 69. La fiche de contact porte le pseudonyme l.églanbelle_085. Le compte client est CLT-000135-Q, et la référence RH éventuelle est EMP-102647. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Églanbelle.

**Traitement du dossier.** Le 2025-07-21, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Célestin Brumemarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 182,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 77 03 99 135 703 00. La domiciliation bancaire fictive indique FR00 4645 7364 0351 1998 3913 292, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.2; la trace IPv6 associée est 2001:db8:86::103a. Le poste de travail porte l’identifiant 12345f5e-15de-4004-a6ce-0123456799e5, le cookie de test est cookie-demo-00135-12998, et le gabarit biométrique est BIO-DEMO-007109 (référence vocale distincte : VOICE-TEST-00135). Le véhicule mentionné est ZZ-958-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léandre Églanbelle et ajouté une note de suivi à CLT-000135-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1784; la référence du lot est BATCH-OPS-2026-322. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léandre Églanbelle |
| Date | 1998-11-15 |
| Contact | leandre.eglanbelle37@example.invalid |
| Client | CLT-000135-Q |
| Incident | INC-2026-05511 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1784 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Léandre Églanbelle, 06 39 98 49 69, leandre.eglanbelle37@example.invalid; le rappel est prévu autour du 2025-07-21.”


## Cas 136 : Banque / assurance | dossier fictif INC-2026-05552

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Nora Rivbrume, née le 2017-04-01. Le dossier la rattache à 136, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est nora.rivbrume38@example.invalid et son téléphone est 06 39 98 50 06; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 50 06. La fiche de contact porte le pseudonyme n.rivbrume_108. Le compte client est CLT-000136-Q, et la référence RH éventuelle est EMP-102666. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rivbrume.

**Traitement du dossier.** Le 2026-10-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Ilyan Mélidune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 355,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 78 04 99 136 840 00. La domiciliation bancaire fictive indique FR00 4746 7477 0478 2129 4050 431, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.19; la trace IPv6 associée est 2001:db8:87::1059. Le poste de travail porte l’identifiant 12345f6f-15e5-4005-a6db-012345679a04, le cookie de test est cookie-demo-00136-13095, et le gabarit biométrique est BIO-DEMO-007162 (référence vocale distincte : VOICE-TEST-00136). Le véhicule mentionné est ZZ-995-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nora Rivbrume et ajouté une note de suivi à CLT-000136-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient nora RIVBRUME; vérifier que le changement de casse ne bloque pas la détection.

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2017-04-01. Le proche de référence est Ilyan Mélidune. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1797; la référence du lot est BATCH-OPS-2026-339. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nora Rivbrume |
| Date | 2017-04-01 |
| Contact | nora.rivbrume38@example.invalid |
| Client | CLT-000136-Q |
| Incident | INC-2026-05552 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1797 |

**Autre formulation observée.** Note d’audit : le lien entre n.rivbrume_108, 192.0.2.19 et 12345f6f-15e5-4005-a6db-012345679a04 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 137 : Éducation / accompagnement | dossier fictif INC-2026-05593

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Anaïs Alouloriot, née le 1969-09-14. Le dossier la rattache à 153, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est anais.alouloriot39@example.invalid et son téléphone est 06 39 98 50 43; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 50 43. La fiche de contact porte le pseudonyme a.alouloriot_131. Le compte client est CLT-000137-Q, et la référence RH éventuelle est EMP-102685. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Alouloriot.

**Traitement du dossier.** Le 2025-01-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Lucile Vanisac, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 528,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 79 05 99 137 977 00. La domiciliation bancaire fictive indique FR00 4847 7590 0605 2260 4187 570, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.36; la trace IPv6 associée est 2001:db8:88::1078. Le poste de travail porte l’identifiant 12345f80-15ec-4006-a6e8-012345679a23, le cookie de test est cookie-demo-00137-13192, et le gabarit biométrique est BIO-DEMO-007215 (référence vocale distincte : VOICE-TEST-00137). Le véhicule mentionné est ZZ-032-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Anaïs Alouloriot et ajouté une note de suivi à CLT-000137-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1810; la référence du lot est BATCH-OPS-2026-356. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Anaïs Alouloriot |
| Date | 1969-09-14 |
| Contact | anais.alouloriot39@example.invalid |
| Client | CLT-000137-Q |
| Incident | INC-2026-05593 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1810 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 138 : Juridique / contrat | dossier fictif INC-2026-05634

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Jade Belaubier, née le 1976-02-27. Le dossier la rattache à 170, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est jade.belaubier40@example.invalid et son téléphone est 06 39 98 50 80; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 50 80. La fiche de contact porte le pseudonyme j.belaubier_154. Le compte client est CLT-000138-Q, et la référence RH éventuelle est EMP-102704. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Belaubier.

**Traitement du dossier.** Le 2026-04-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Gabin Aurimousse, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 701,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 80 06 99 138 114 00. La domiciliation bancaire fictive indique FR00 4948 7703 0732 2391 4324 709, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.53; la trace IPv6 associée est 2001:db8:89::1097. Le poste de travail porte l’identifiant 12345f91-15f3-4007-a6f5-012345679a42, le cookie de test est cookie-demo-00138-13289, et le gabarit biométrique est BIO-DEMO-007268 (référence vocale distincte : VOICE-TEST-00138). Le véhicule mentionné est ZZ-069-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Jade Belaubier et ajouté une note de suivi à CLT-000138-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1823; la référence du lot est BATCH-OPS-2026-373. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Jade Belaubier |
| Date | 1976-02-27 |
| Contact | jade.belaubier40@example.invalid |
| Client | CLT-000138-Q |
| Incident | INC-2026-05634 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1823 |

**Autre formulation observée.** Version importée : Jade Belaubier; date=1976-02-27; rue=170, rue des Nuages Bas, 99900 Noroît-les-Jardins, France; téléphone=06 39 98 50 80; courriel=jade.belaubier40@example.invalid; statut=à contrôler.


## Cas 139 : Support informatique | dossier fictif INC-2026-05675

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Bastien Fauvevalon, née le 1983-07-13. Le dossier la rattache à 7, rue du Phare Éteint, 99900 Nacréville, France. Son email est bastien.fauvevalon41@example.invalid et son téléphone est 06 39 98 51 17; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 51 17. La fiche de contact porte le pseudonyme b.fauvevalon_177. Le compte client est CLT-000139-Q, et la référence RH éventuelle est EMP-102723. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Fauvevalon.

**Traitement du dossier.** Le 2025-07-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Lina Montaroussin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 874,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 81 07 99 139 251 00. La domiciliation bancaire fictive indique FR00 5049 7816 0859 2522 4461 848, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.70; la trace IPv6 associée est 2001:db8:8a::10b6. Le poste de travail porte l’identifiant 12345fa2-15fa-4008-a702-012345679a61, le cookie de test est cookie-demo-00139-13386, et le gabarit biométrique est BIO-DEMO-007321 (référence vocale distincte : VOICE-TEST-00139). Le véhicule mentionné est ZZ-106-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Bastien Fauvevalon et ajouté une note de suivi à CLT-000139-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1836; la référence du lot est BATCH-OPS-2026-390. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Bastien Fauvevalon |
| Date | 1983-07-13 |
| Contact | bastien.fauvevalon41@example.invalid |
| Client | CLT-000139-Q |
| Incident | INC-2026-05675 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1836 |

**Autre formulation observée.** Le message reçu disait : « Pour Bastien Fauvevalon, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-05675. »


## Cas 140 : Voyage / réservation | dossier fictif INC-2026-05716

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Malo Dorémeline, née le 1990-12-26. Le dossier la rattache à 24, rue des Pivoines Grises, 99900 Brumeval, France. Son email est malo.doremeline42@example.invalid et son téléphone est 06 39 98 51 54; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 51 54. La fiche de contact porte le pseudonyme m.dorémeline_200. Le compte client est CLT-000140-Q, et la référence RH éventuelle est EMP-102742. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Dorémeline.

**Traitement du dossier.** Le 2026-10-02, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Titouan Nivvardin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 047,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 82 08 99 140 388 00. La domiciliation bancaire fictive indique FR00 5150 7929 0986 2653 4598 987, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.87; la trace IPv6 associée est 2001:db8:8b::10d5. Le poste de travail porte l’identifiant 12345fb3-1601-4009-a70f-012345679a80, le cookie de test est cookie-demo-00140-13483, et le gabarit biométrique est BIO-DEMO-007374 (référence vocale distincte : VOICE-TEST-00140). Le véhicule mentionné est ZZ-143-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Malo Dorémeline et ajouté une note de suivi à CLT-000140-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1849; la référence du lot est BATCH-OPS-2026-407. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Malo Dorémeline |
| Date | 1990-12-26 |
| Contact | malo.doremeline42@example.invalid |
| Client | CLT-000140-Q |
| Incident | INC-2026-05716 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1849 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Malo Dorémeline, identifiant CLT-000140-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 141 : Marketing / consentement | dossier fictif INC-2026-05757

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Ilyan Corvivalise, née le 1997-05-12. Le dossier la rattache à 41, rue des Brumes, 99900 Val-des-Nuages, France. Son email est ilyan.corvivalise43@example.invalid et son téléphone est 06 39 98 51 91; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 51 91. La fiche de contact porte le pseudonyme i.corvivalise_223. Le compte client est CLT-000141-Q, et la référence RH éventuelle est EMP-102761. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Corvivalise.

**Traitement du dossier.** Le 2025-01-09, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Nora Virenacré, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 220,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 83 09 99 141 525 00. La domiciliation bancaire fictive indique FR00 5251 8042 1113 2784 4735 126, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.104; la trace IPv6 associée est 2001:db8:8c::10f4. Le poste de travail porte l’identifiant 12345fc4-1608-4000-a71c-012345679a9f, le cookie de test est cookie-demo-00141-13580, et le gabarit biométrique est BIO-DEMO-007427 (référence vocale distincte : VOICE-TEST-00141). Le véhicule mentionné est ZZ-180-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ilyan Corvivalise et ajouté une note de suivi à CLT-000141-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ilyan CORVIVALISE; vérifier que le changement de casse ne bloque pas la détection.

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 51 91. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1862; la référence du lot est BATCH-OPS-2026-424. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ilyan Corvivalise |
| Date | 1997-05-12 |
| Contact | ilyan.corvivalise43@example.invalid |
| Client | CLT-000141-Q |
| Incident | INC-2026-05757 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1862 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Ilyan Corvivalise, 06 39 98 51 91, ilyan.corvivalise43@example.invalid; le rappel est prévu autour du 2025-01-09.”


## Cas 142 : Recherche / enquête | dossier fictif INC-2026-05798

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Émilie Lisirune, née le 2004-10-25. Le dossier la rattache à 58, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est emilie.lisirune44@example.invalid et son téléphone est 06 39 98 52 28; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 52 28. La fiche de contact porte le pseudonyme é.lisirune_246. Le compte client est CLT-000142-Q, et la référence RH éventuelle est EMP-102780. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lisirune.

**Traitement du dossier.** Le 2026-04-16, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Lison Cenddombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 393,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 84 10 99 142 662 00. La domiciliation bancaire fictive indique FR00 5352 8155 1240 2915 4872 265, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.121; la trace IPv6 associée est 2001:db8:8d::1113. Le poste de travail porte l’identifiant 12345fd5-160f-4001-a729-012345679abe, le cookie de test est cookie-demo-00142-13677, et le gabarit biométrique est BIO-DEMO-007480 (référence vocale distincte : VOICE-TEST-00142). Le véhicule mentionné est ZZ-217-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Émilie Lisirune et ajouté une note de suivi à CLT-000142-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1875; la référence du lot est BATCH-OPS-2026-441. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Émilie Lisirune |
| Date | 2004-10-25 |
| Contact | emilie.lisirune44@example.invalid |
| Client | CLT-000142-Q |
| Incident | INC-2026-05798 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1875 |

**Autre formulation observée.** Note d’audit : le lien entre é.lisirune_246, 192.0.2.121 et 12345fd5-160f-4001-a729-012345679abe doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 143 : Logistique / livraison | dossier fictif INC-2026-05839

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Lison Lorimurel, née le 1968-03-11. Le dossier la rattache à 75, rue des Nuages Bas, 99900 Mirebrise, France. Son email est lison.lorimurel45@example.invalid et son téléphone est 06 39 98 52 65; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 52 65. La fiche de contact porte le pseudonyme l.lorimurel_269. Le compte client est CLT-000143-Q, et la référence RH éventuelle est EMP-102799. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lorimurel.

**Traitement du dossier.** Le 2025-07-23, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Sofia Saphvialet, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 566,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 85 11 99 143 799 00. La domiciliation bancaire fictive indique FR00 5453 8268 1367 3046 5009 404, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.138; la trace IPv6 associée est 2001:db8:8e::1132. Le poste de travail porte l’identifiant 12345fe6-1616-4002-a736-012345679add, le cookie de test est cookie-demo-00143-13774, et le gabarit biométrique est BIO-DEMO-007533 (référence vocale distincte : VOICE-TEST-00143). Le véhicule mentionné est ZZ-254-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lison Lorimurel et ajouté une note de suivi à CLT-000143-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1888; la référence du lot est BATCH-OPS-2026-458. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lison Lorimurel |
| Date | 1968-03-11 |
| Contact | lison.lorimurel45@example.invalid |
| Client | CLT-000143-Q |
| Incident | INC-2026-05839 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1888 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 144 : Sécurité / contrôle d’accès | dossier fictif INC-2026-05880

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Clémence Briscendre, née le 1975-08-24. Le dossier la rattache à 92, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est clemence.briscendre46@example.invalid et son téléphone est 06 39 98 53 02; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 53 02. La fiche de contact porte le pseudonyme c.briscendre_292. Le compte client est CLT-000144-Q, et la référence RH éventuelle est EMP-102818. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Briscendre.

**Traitement du dossier.** Le 2026-10-03, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Marceau Clairclaire, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 739,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 86 12 99 144 936 00. La domiciliation bancaire fictive indique FR00 5554 8381 1494 3177 5146 543, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.155; la trace IPv6 associée est 2001:db8:8f::1151. Le poste de travail porte l’identifiant 12345ff7-161d-4003-a743-012345679afc, le cookie de test est cookie-demo-00144-13871, et le gabarit biométrique est BIO-DEMO-007586 (référence vocale distincte : VOICE-TEST-00144). Le véhicule mentionné est ZZ-291-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Clémence Briscendre et ajouté une note de suivi à CLT-000144-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1901; la référence du lot est BATCH-OPS-2026-475. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Clémence Briscendre |
| Date | 1975-08-24 |
| Contact | clemence.briscendre46@example.invalid |
| Client | CLT-000144-Q |
| Incident | INC-2026-05880 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1901 |

**Autre formulation observée.** Version importée : Clémence Briscendre; date=1975-08-24; rue=92, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France; téléphone=06 39 98 53 02; courriel=clemence.briscendre46@example.invalid; statut=à contrôler.


## Cas 145 : RH / gestion du personnel | dossier fictif INC-2026-05921

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Ismaël Lunémistral, née le 2010-01-10. Le dossier la rattache à 109, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est ismael.lunemistral47@example.invalid et son téléphone est 06 39 98 53 39; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 53 39. La fiche de contact porte le pseudonyme i.lunémistral_315. Le compte client est CLT-000145-Q, et la référence RH éventuelle est EMP-102837. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lunémistral.

**Traitement du dossier.** Le 2025-01-10, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Apolline Ormeplaine, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 912,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 87 01 99 145 073 00. La domiciliation bancaire fictive indique FR00 5655 8494 1621 3308 5283 682, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.172; la trace IPv6 associée est 2001:db8:90::1170. Le poste de travail porte l’identifiant 12346008-1624-4004-a750-012345679b1b, le cookie de test est cookie-demo-00145-13968, et le gabarit biométrique est BIO-DEMO-007639 (référence vocale distincte : VOICE-TEST-00145). Le véhicule mentionné est ZZ-328-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ismaël Lunémistral et ajouté une note de suivi à CLT-000145-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2010-01-10. Le proche de référence est Apolline Ormeplaine. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1914; la référence du lot est BATCH-OPS-2026-492. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ismaël Lunémistral |
| Date | 2010-01-10 |
| Contact | ismael.lunemistral47@example.invalid |
| Client | CLT-000145-Q |
| Incident | INC-2026-05921 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1914 |

**Autre formulation observée.** Le message reçu disait : « Pour Ismaël Lunémistral, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-05921. »


## Cas 146 : CRM / relation client | dossier fictif INC-2026-05962

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Salomé Épilune, née le 1989-06-23. Le dossier la rattache à 126, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est salome.epilune48@example.invalid et son téléphone est 06 39 98 53 76; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 53 76. La fiche de contact porte le pseudonyme s.épilune_338. Le compte client est CLT-000146-Q, et la référence RH éventuelle est EMP-102856. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Épilune.

**Traitement du dossier.** Le 2026-04-17, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Mila Pluvivelin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 085,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 88 02 99 146 210 00. La domiciliation bancaire fictive indique FR00 5756 8607 1748 3439 5420 821, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.189; la trace IPv6 associée est 2001:db8:91::118f. Le poste de travail porte l’identifiant 12346019-162b-4005-a75d-012345679b3a, le cookie de test est cookie-demo-00146-14065, et le gabarit biométrique est BIO-DEMO-007692 (référence vocale distincte : VOICE-TEST-00146). Le véhicule mentionné est ZZ-365-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Salomé Épilune et ajouté une note de suivi à CLT-000146-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient salomé ÉPILUNE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1927; la référence du lot est BATCH-OPS-2026-509. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Salomé Épilune |
| Date | 1989-06-23 |
| Contact | salome.epilune48@example.invalid |
| Client | CLT-000146-Q |
| Incident | INC-2026-05962 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1927 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Salomé Épilune, identifiant CLT-000146-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 147 : Santé / prise de rendez-vous | dossier fictif INC-2026-06003

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Nino Florilacier, née le 1996-11-09. Le dossier la rattache à 143, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est nino.florilacier49@example.invalid et son téléphone est 06 39 98 54 13; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 54 13. La fiche de contact porte le pseudonyme n.florilacier_361. Le compte client est CLT-000147-Q, et la référence RH éventuelle est EMP-102875. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Florilacier.

**Traitement du dossier.** Le 2025-07-24, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Jade Nacreclairon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 258,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 89 03 99 147 347 00. La domiciliation bancaire fictive indique FR00 5857 8720 1875 3570 5557 960, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.206; la trace IPv6 associée est 2001:db8:92::11ae. Le poste de travail porte l’identifiant 1234602a-1632-4006-a76a-012345679b59, le cookie de test est cookie-demo-00147-14162, et le gabarit biométrique est BIO-DEMO-007745 (référence vocale distincte : VOICE-TEST-00147). Le véhicule mentionné est ZZ-402-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nino Florilacier et ajouté une note de suivi à CLT-000147-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1940; la référence du lot est BATCH-OPS-2026-526. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nino Florilacier |
| Date | 1996-11-09 |
| Contact | nino.florilacier49@example.invalid |
| Client | CLT-000147-Q |
| Incident | INC-2026-06003 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-1940 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Nino Florilacier, 06 39 98 54 13, nino.florilacier49@example.invalid; le rappel est prévu autour du 2025-07-24.”


## Cas 148 : Banque / assurance | dossier fictif INC-2026-06044

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Lucile Orielserein, née le 2003-04-22. Le dossier la rattache à 160, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est lucile.orielserein50@example.invalid et son téléphone est 06 39 98 54 50; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 54 50. La fiche de contact porte le pseudonyme l.orielserein_384. Le compte client est CLT-000148-Q, et la référence RH éventuelle est EMP-102894. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Orielserein.

**Traitement du dossier.** Le 2026-10-04, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Ismaël Perrivigne, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 431,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 90 04 99 148 484 00. La domiciliation bancaire fictive indique FR00 5958 8833 2002 3701 5694 099, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.223; la trace IPv6 associée est 2001:db8:93::11cd. Le poste de travail porte l’identifiant 1234603b-1639-4007-a777-012345679b78, le cookie de test est cookie-demo-00148-14259, et le gabarit biométrique est BIO-DEMO-007798 (référence vocale distincte : VOICE-TEST-00148). Le véhicule mentionné est ZZ-439-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lucile Orielserein et ajouté une note de suivi à CLT-000148-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 54 50. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1953; la référence du lot est BATCH-OPS-2026-543. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lucile Orielserein |
| Date | 2003-04-22 |
| Contact | lucile.orielserein50@example.invalid |
| Client | CLT-000148-Q |
| Incident | INC-2026-06044 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-1953 |

**Autre formulation observée.** Note d’audit : le lien entre l.orielserein_384, 192.0.2.223 et 1234603b-1639-4007-a777-012345679b78 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 149 : Éducation / accompagnement | dossier fictif INC-2026-06085

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Noé Érablefarin, née le 1967-09-08. Le dossier la rattache à 177, rue du Phare Éteint, 99900 Pluviane, France. Son email est noe.erablefarin51@example.invalid et son téléphone est 06 39 98 54 87; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 54 87. La fiche de contact porte le pseudonyme n.érablefarin_407. Le compte client est CLT-000149-Q, et la référence RH éventuelle est EMP-102913. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Érablefarin.

**Traitement du dossier.** Le 2025-01-11, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Yasmine Pavofleur, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 504,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 91 05 99 149 621 00. La domiciliation bancaire fictive indique FR00 6059 8946 2129 3832 5831 238, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.240; la trace IPv6 associée est 2001:db8:94::11ec. Le poste de travail porte l’identifiant 1234604c-1640-4008-a784-012345679b97, le cookie de test est cookie-demo-00149-14356, et le gabarit biométrique est BIO-DEMO-007851 (référence vocale distincte : VOICE-TEST-00149). Le véhicule mentionné est ZZ-476-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Noé Érablefarin et ajouté une note de suivi à CLT-000149-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1966; la référence du lot est BATCH-OPS-2026-560. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Noé Érablefarin |
| Date | 1967-09-08 |
| Contact | noe.erablefarin51@example.invalid |
| Client | CLT-000149-Q |
| Incident | INC-2026-06085 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-1966 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 150 : Juridique / contrat | dossier fictif INC-2026-06126

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Sofia Valnette, née le 1974-02-21. Le dossier la rattache à 14, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est sofia.valnette52@example.invalid et son téléphone est 06 39 98 55 24; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 55 24. La fiche de contact porte le pseudonyme s.valnette_430. Le compte client est CLT-000150-Q, et la référence RH éventuelle est EMP-102932. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Valnette.

**Traitement du dossier.** Le 2026-04-18, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Mathis Noroorée, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 677,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 92 06 99 150 758 00. La domiciliation bancaire fictive indique FR00 6160 9059 2256 3963 5968 377, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.4; la trace IPv6 associée est 2001:db8:95::120b. Le poste de travail porte l’identifiant 1234605d-1647-4009-a791-012345679bb6, le cookie de test est cookie-demo-00150-14453, et le gabarit biométrique est BIO-DEMO-007904 (référence vocale distincte : VOICE-TEST-00150). Le véhicule mentionné est ZZ-513-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sofia Valnette et ajouté une note de suivi à CLT-000150-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1979; la référence du lot est BATCH-OPS-2026-577. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sofia Valnette |
| Date | 1974-02-21 |
| Contact | sofia.valnette52@example.invalid |
| Client | CLT-000150-Q |
| Incident | INC-2026-06126 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-1979 |

**Autre formulation observée.** Version importée : Sofia Valnette; date=1974-02-21; rue=14, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France; téléphone=06 39 98 55 24; courriel=sofia.valnette52@example.invalid; statut=à contrôler.


## Cas 151 : Support informatique | dossier fictif INC-2026-06167

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Eden Mirasorel, née le 1981-07-07. Le dossier la rattache à 31, rue des Brumes, 99900 Cendrelac, France. Son email est eden.mirasorel53@example.invalid et son téléphone est 06 39 98 55 61; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 55 61. La fiche de contact porte le pseudonyme e.mirasorel_453. Le compte client est CLT-000151-Q, et la référence RH éventuelle est EMP-102951. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mirasorel.

**Traitement du dossier.** Le 2025-07-25, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Ambre Rosibrise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 850,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 93 07 99 151 895 00. La domiciliation bancaire fictive indique FR00 6261 9172 2383 4094 6105 516, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.21; la trace IPv6 associée est 2001:db8:96::122a. Le poste de travail porte l’identifiant 1234606e-164e-4000-a79e-012345679bd5, le cookie de test est cookie-demo-00151-14550, et le gabarit biométrique est BIO-DEMO-007957 (référence vocale distincte : VOICE-TEST-00151). Le véhicule mentionné est ZZ-550-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eden Mirasorel et ajouté une note de suivi à CLT-000151-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient eden MIRASOREL; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-1992; la référence du lot est BATCH-OPS-2026-594. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eden Mirasorel |
| Date | 1981-07-07 |
| Contact | eden.mirasorel53@example.invalid |
| Client | CLT-000151-Q |
| Incident | INC-2026-06167 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-1992 |

**Autre formulation observée.** Le message reçu disait : « Pour Eden Mirasorel, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-06167. »


## Cas 152 : Voyage / réservation | dossier fictif INC-2026-06208

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Yasmine Brumemarin, née le 1988-12-20. Le dossier la rattache à 48, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est yasmine.brumemarin54@example.invalid et son téléphone est 06 39 98 55 98; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 55 98. La fiche de contact porte le pseudonyme y.brumemarin_476. Le compte client est CLT-000152-Q, et la référence RH éventuelle est EMP-102970. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Brumemarin.

**Traitement du dossier.** Le 2026-10-05, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Maël Solravel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 023,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 94 08 99 152 032 00. La domiciliation bancaire fictive indique FR00 6362 9285 2510 4225 6242 655, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.38; la trace IPv6 associée est 2001:db8:97::1249. Le poste de travail porte l’identifiant 1234607f-1655-4001-a7ab-012345679bf4, le cookie de test est cookie-demo-00152-14647, et le gabarit biométrique est BIO-DEMO-008010 (référence vocale distincte : VOICE-TEST-00152). Le véhicule mentionné est ZZ-587-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Yasmine Brumemarin et ajouté une note de suivi à CLT-000152-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2005; la référence du lot est BATCH-OPS-2026-611. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Yasmine Brumemarin |
| Date | 1988-12-20 |
| Contact | yasmine.brumemarin54@example.invalid |
| Client | CLT-000152-Q |
| Incident | INC-2026-06208 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2005 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Yasmine Brumemarin, identifiant CLT-000152-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 153 : Marketing / consentement | dossier fictif INC-2026-06249

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Eliott Mélidune, née le 1995-05-06. Le dossier la rattache à 65, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est eliott.melidune55@example.invalid et son téléphone est 06 39 98 56 35; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 56 35. La fiche de contact porte le pseudonyme e.mélidune_499. Le compte client est CLT-000153-Q, et la référence RH éventuelle est EMP-102989. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mélidune.

**Traitement du dossier.** Le 2025-01-12, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Malo Avelroche, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 196,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 95 09 99 153 169 00. La domiciliation bancaire fictive indique FR00 6463 9398 2637 4356 6379 794, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.55; la trace IPv6 associée est 2001:db8:98::1268. Le poste de travail porte l’identifiant 12346090-165c-4002-a7b8-012345679c13, le cookie de test est cookie-demo-00153-14744, et le gabarit biométrique est BIO-DEMO-008063 (référence vocale distincte : VOICE-TEST-00153). Le véhicule mentionné est ZZ-624-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eliott Mélidune et ajouté une note de suivi à CLT-000153-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2018; la référence du lot est BATCH-OPS-2026-628. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eliott Mélidune |
| Date | 1995-05-06 |
| Contact | eliott.melidune55@example.invalid |
| Client | CLT-000153-Q |
| Incident | INC-2026-06249 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2018 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Eliott Mélidune, 06 39 98 56 35, eliott.melidune55@example.invalid; le rappel est prévu autour du 2025-01-12.”


## Cas 154 : Recherche / enquête | dossier fictif INC-2026-06290

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Zoé Vanisac, née le 2011-10-19. Le dossier la rattache à 82, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est zoe.vanisac56@example.invalid et son téléphone est 06 39 98 56 72; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 56 72. La fiche de contact porte le pseudonyme z.vanisac_522. Le compte client est CLT-000154-Q, et la référence RH éventuelle est EMP-103008. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Vanisac.

**Traitement du dossier.** Le 2026-04-19, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Nino Tremlombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 369,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 96 10 99 154 306 00. La domiciliation bancaire fictive indique FR00 6564 9511 2764 4487 6516 933, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.72; la trace IPv6 associée est 2001:db8:99::1287. Le poste de travail porte l’identifiant 123460a1-1663-4003-a7c5-012345679c32, le cookie de test est cookie-demo-00154-14841, et le gabarit biométrique est BIO-DEMO-008116 (référence vocale distincte : VOICE-TEST-00154). Le véhicule mentionné est ZZ-661-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Zoé Vanisac et ajouté une note de suivi à CLT-000154-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2011-10-19. Le proche de référence est Nino Tremlombre. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2031; la référence du lot est BATCH-OPS-2026-645. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Zoé Vanisac |
| Date | 2011-10-19 |
| Contact | zoe.vanisac56@example.invalid |
| Client | CLT-000154-Q |
| Incident | INC-2026-06290 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2031 |

**Autre formulation observée.** Note d’audit : le lien entre z.vanisac_522, 192.0.2.72 et 123460a1-1663-4003-a7c5-012345679c32 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 155 : Logistique / livraison | dossier fictif INC-2026-06331

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Gabin Aurimousse, née le 1966-03-05. Le dossier la rattache à 99, rue des Pivoines Grises, 99900 Valmousse, France. Son email est gabin.aurimousse57@example.invalid et son téléphone est 06 39 98 57 09; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 57 09. La fiche de contact porte le pseudonyme g.aurimousse_545. Le compte client est CLT-000155-Q, et la référence RH éventuelle est EMP-103027. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Aurimousse.

**Traitement du dossier.** Le 2025-07-26, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Zoé Varnedorin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 542,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 97 11 99 155 443 00. La domiciliation bancaire fictive indique FR00 6665 9624 2891 4618 6653 072, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.89; la trace IPv6 associée est 2001:db8:9a::12a6. Le poste de travail porte l’identifiant 123460b2-166a-4004-a7d2-012345679c51, le cookie de test est cookie-demo-00155-14938, et le gabarit biométrique est BIO-DEMO-008169 (référence vocale distincte : VOICE-TEST-00155). Le véhicule mentionné est ZZ-698-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Gabin Aurimousse et ajouté une note de suivi à CLT-000155-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 57 09. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2044; la référence du lot est BATCH-OPS-2026-662. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Gabin Aurimousse |
| Date | 1966-03-05 |
| Contact | gabin.aurimousse57@example.invalid |
| Client | CLT-000155-Q |
| Incident | INC-2026-06331 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2044 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 156 : Sécurité / contrôle d’accès | dossier fictif INC-2026-06372

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Maëlys Montaroussin, née le 1973-08-18. Le dossier la rattache à 116, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est maelys.montaroussin58@example.invalid et son téléphone est 06 39 98 57 46; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 57 46. La fiche de contact porte le pseudonyme m.montaroussin_568. Le compte client est CLT-000156-Q, et la référence RH éventuelle est EMP-103046. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Montaroussin.

**Traitement du dossier.** Le 2026-10-06, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Sohan Célvaux, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 715,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 98 12 99 156 580 00. La domiciliation bancaire fictive indique FR00 6766 9737 3018 4749 6790 211, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.106; la trace IPv6 associée est 2001:db8:9b::12c5. Le poste de travail porte l’identifiant 123460c3-1671-4005-a7df-012345679c70, le cookie de test est cookie-demo-00156-15035, et le gabarit biométrique est BIO-DEMO-008222 (référence vocale distincte : VOICE-TEST-00156). Le véhicule mentionné est ZZ-735-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maëlys Montaroussin et ajouté une note de suivi à CLT-000156-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient maëlys MONTAROUSSIN; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2057; la référence du lot est BATCH-OPS-2026-679. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maëlys Montaroussin |
| Date | 1973-08-18 |
| Contact | maelys.montaroussin58@example.invalid |
| Client | CLT-000156-Q |
| Incident | INC-2026-06372 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2057 |

**Autre formulation observée.** Version importée : Maëlys Montaroussin; date=1973-08-18; rue=116, rue des Brumes, 99900 Virelune-les-Pins, France; téléphone=06 39 98 57 46; courriel=maelys.montaroussin58@example.invalid; statut=à contrôler.


## Cas 157 : RH / gestion du personnel | dossier fictif INC-2026-06413

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Marceau Nivvardin, née le 1980-01-04. Le dossier la rattache à 133, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est marceau.nivvardin59@example.invalid et son téléphone est 06 39 98 57 83; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 57 83. La fiche de contact porte le pseudonyme m.nivvardin_591. Le compte client est CLT-000157-Q, et la référence RH éventuelle est EMP-103065. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nivvardin.

**Traitement du dossier.** Le 2025-01-13, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Naël Seredorelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 888,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 60 01 99 157 717 00. La domiciliation bancaire fictive indique FR00 6867 9850 3145 4880 6927 350, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.123; la trace IPv6 associée est 2001:db8:9c::12e4. Le poste de travail porte l’identifiant 123460d4-1678-4006-a7ec-012345679c8f, le cookie de test est cookie-demo-00157-15132, et le gabarit biométrique est BIO-DEMO-008275 (référence vocale distincte : VOICE-TEST-00157). Le véhicule mentionné est ZZ-772-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Marceau Nivvardin et ajouté une note de suivi à CLT-000157-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2070; la référence du lot est BATCH-OPS-2026-696. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Marceau Nivvardin |
| Date | 1980-01-04 |
| Contact | marceau.nivvardin59@example.invalid |
| Client | CLT-000157-Q |
| Incident | INC-2026-06413 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2070 |

**Autre formulation observée.** Le message reçu disait : « Pour Marceau Nivvardin, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-06413. »


## Cas 158 : CRM / relation client | dossier fictif INC-2026-06454

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Léonie Virenacré, née le 1987-06-17. Le dossier la rattache à 150, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est leonie.virenacre60@example.invalid et son téléphone est 06 39 98 58 20; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 58 20. La fiche de contact porte le pseudonyme l.virenacré_614. Le compte client est CLT-000158-Q, et la référence RH éventuelle est EMP-103084. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Virenacré.

**Traitement du dossier.** Le 2026-04-20, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Léandre Églanbelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 061,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 61 02 99 158 854 00. La domiciliation bancaire fictive indique FR00 6968 9963 3272 5011 7064 489, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.140; la trace IPv6 associée est 2001:db8:9d::1303. Le poste de travail porte l’identifiant 123460e5-167f-4007-a7f9-012345679cae, le cookie de test est cookie-demo-00158-15229, et le gabarit biométrique est BIO-DEMO-008328 (référence vocale distincte : VOICE-TEST-00158). Le véhicule mentionné est ZZ-809-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léonie Virenacré et ajouté une note de suivi à CLT-000158-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2083; la référence du lot est BATCH-OPS-2026-713. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léonie Virenacré |
| Date | 1987-06-17 |
| Contact | leonie.virenacre60@example.invalid |
| Client | CLT-000158-Q |
| Incident | INC-2026-06454 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2083 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Léonie Virenacré, identifiant CLT-000158-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 159 : Santé / prise de rendez-vous | dossier fictif INC-2026-06495

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Mathis Cenddombre, née le 1994-11-03. Le dossier la rattache à 167, rue du Phare Éteint, 99900 Nacréville, France. Son email est mathis.cenddombre61@example.invalid et son téléphone est 06 39 98 58 57; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 58 57. La fiche de contact porte le pseudonyme m.cenddombre_637. Le compte client est CLT-000159-Q, et la référence RH éventuelle est EMP-103103. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Cenddombre.

**Traitement du dossier.** Le 2025-07-27, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Émilie Rivbrume, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 234,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 62 03 99 159 991 00. La domiciliation bancaire fictive indique FR00 7069 0076 3399 5142 7201 628, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.157; la trace IPv6 associée est 2001:db8:9e::1322. Le poste de travail porte l’identifiant 123460f6-1686-4008-a806-012345679ccd, le cookie de test est cookie-demo-00159-15326, et le gabarit biométrique est BIO-DEMO-008381 (référence vocale distincte : VOICE-TEST-00159). Le véhicule mentionné est ZZ-846-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mathis Cenddombre et ajouté une note de suivi à CLT-000159-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2096; la référence du lot est BATCH-OPS-2026-730. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mathis Cenddombre |
| Date | 1994-11-03 |
| Contact | mathis.cenddombre61@example.invalid |
| Client | CLT-000159-Q |
| Incident | INC-2026-06495 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2096 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Mathis Cenddombre, 06 39 98 58 57, mathis.cenddombre61@example.invalid; le rappel est prévu autour du 2025-07-27.”


## Cas 160 : Banque / assurance | dossier fictif INC-2026-06536

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Ariane Saphvialet, née le 2001-04-16. Le dossier la rattache à 4, rue des Pivoines Grises, 99900 Brumeval, France. Son email est ariane.saphvialet62@example.invalid et son téléphone est 06 39 98 58 94; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 58 94. La fiche de contact porte le pseudonyme a.saphvialet_660. Le compte client est CLT-000160-Q, et la référence RH éventuelle est EMP-103122. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Saphvialet.

**Traitement du dossier.** Le 2026-10-07, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Noé Alouloriot, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 407,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 63 04 99 160 128 00. La domiciliation bancaire fictive indique FR00 7170 0189 3526 5273 7338 767, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.174; la trace IPv6 associée est 2001:db8:9f::1341. Le poste de travail porte l’identifiant 12346107-168d-4009-a813-012345679cec, le cookie de test est cookie-demo-00160-15423, et le gabarit biométrique est BIO-DEMO-008434 (référence vocale distincte : VOICE-TEST-00160). Le véhicule mentionné est ZZ-883-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ariane Saphvialet et ajouté une note de suivi à CLT-000160-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2109; la référence du lot est BATCH-OPS-2026-747. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ariane Saphvialet |
| Date | 2001-04-16 |
| Contact | ariane.saphvialet62@example.invalid |
| Client | CLT-000160-Q |
| Incident | INC-2026-06536 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2109 |

**Autre formulation observée.** Note d’audit : le lien entre a.saphvialet_660, 192.0.2.174 et 12346107-168d-4009-a813-012345679cec doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 161 : Éducation / accompagnement | dossier fictif INC-2026-06577

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Sohan Clairclaire, née le 1965-09-02. Le dossier la rattache à 21, rue des Brumes, 99900 Val-des-Nuages, France. Son email est sohan.clairclaire63@example.invalid et son téléphone est 06 39 98 59 31; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 59 31. La fiche de contact porte le pseudonyme s.clairclaire_683. Le compte client est CLT-000161-Q, et la référence RH éventuelle est EMP-103141. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Clairclaire.

**Traitement du dossier.** Le 2025-01-14, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Maëlys Belaubier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 580,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 64 05 99 161 265 00. La domiciliation bancaire fictive indique FR00 7271 0302 3653 5404 7475 906, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.191; la trace IPv6 associée est 2001:db8:a0::1360. Le poste de travail porte l’identifiant 12346118-1694-4000-a820-012345679d0b, le cookie de test est cookie-demo-00161-15520, et le gabarit biométrique est BIO-DEMO-008487 (référence vocale distincte : VOICE-TEST-00161). Le véhicule mentionné est ZZ-920-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sohan Clairclaire et ajouté une note de suivi à CLT-000161-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient sohan CLAIRCLAIRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2122; la référence du lot est BATCH-OPS-2026-764. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sohan Clairclaire |
| Date | 1965-09-02 |
| Contact | sohan.clairclaire63@example.invalid |
| Client | CLT-000161-Q |
| Incident | INC-2026-06577 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2122 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 162 : Juridique / contrat | dossier fictif INC-2026-06618

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Lina Ormeplaine, née le 1972-02-15. Le dossier la rattache à 38, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est lina.ormeplaine64@example.invalid et son téléphone est 06 39 98 59 68; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 59 68. La fiche de contact porte le pseudonyme l.ormeplaine_706. Le compte client est CLT-000162-Q, et la référence RH éventuelle est EMP-103160. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Ormeplaine.

**Traitement du dossier.** Le 2026-04-21, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Younès Fauvevalon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 753,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 65 06 99 162 402 00. La domiciliation bancaire fictive indique FR00 7372 0415 3780 5535 7612 045, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.208; la trace IPv6 associée est 2001:db8:a1::137f. Le poste de travail porte l’identifiant 12346129-169b-4001-a82d-012345679d2a, le cookie de test est cookie-demo-00162-15617, et le gabarit biométrique est BIO-DEMO-008540 (référence vocale distincte : VOICE-TEST-00162). Le véhicule mentionné est ZZ-957-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lina Ormeplaine et ajouté une note de suivi à CLT-000162-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 59 68. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2135; la référence du lot est BATCH-OPS-2026-781. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lina Ormeplaine |
| Date | 1972-02-15 |
| Contact | lina.ormeplaine64@example.invalid |
| Client | CLT-000162-Q |
| Incident | INC-2026-06618 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2135 |

**Autre formulation observée.** Version importée : Lina Ormeplaine; date=1972-02-15; rue=38, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France; téléphone=06 39 98 59 68; courriel=lina.ormeplaine64@example.invalid; statut=à contrôler.


## Cas 163 : Support informatique | dossier fictif INC-2026-06659

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Younès Pluvivelin, née le 2012-07-01. Le dossier la rattache à 55, rue des Nuages Bas, 99900 Mirebrise, France. Son email est younes.pluvivelin65@example.invalid et son téléphone est 06 39 98 60 05; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 60 05. La fiche de contact porte le pseudonyme y.pluvivelin_729. Le compte client est CLT-000163-Q, et la référence RH éventuelle est EMP-103179. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pluvivelin.

**Traitement du dossier.** Le 2025-07-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Inès Dorémeline, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 926,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 66 07 99 163 539 00. La domiciliation bancaire fictive indique FR00 7473 0528 3907 5666 7749 184, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.225; la trace IPv6 associée est 2001:db8:a2::139e. Le poste de travail porte l’identifiant 1234613a-16a2-4002-a83a-012345679d49, le cookie de test est cookie-demo-00163-15714, et le gabarit biométrique est BIO-DEMO-008593 (référence vocale distincte : VOICE-TEST-00163). Le véhicule mentionné est ZZ-994-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Younès Pluvivelin et ajouté une note de suivi à CLT-000163-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2012-07-01. Le proche de référence est Inès Dorémeline. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2148; la référence du lot est BATCH-OPS-2026-798. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Younès Pluvivelin |
| Date | 2012-07-01 |
| Contact | younes.pluvivelin65@example.invalid |
| Client | CLT-000163-Q |
| Incident | INC-2026-06659 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2148 |

**Autre formulation observée.** Le message reçu disait : « Pour Younès Pluvivelin, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-06659. »


## Cas 164 : Voyage / réservation | dossier fictif INC-2026-06700

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Apolline Nacreclairon, née le 1986-12-14. Le dossier la rattache à 72, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est apolline.nacreclairon66@example.invalid et son téléphone est 06 39 98 60 42; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 60 42. La fiche de contact porte le pseudonyme a.nacreclairon_752. Le compte client est CLT-000164-Q, et la référence RH éventuelle est EMP-103198. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nacreclairon.

**Traitement du dossier.** Le 2026-10-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Anaïs Corvivalise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 099,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 67 08 99 164 676 00. La domiciliation bancaire fictive indique FR00 7574 0641 4034 5797 7886 323, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.242; la trace IPv6 associée est 2001:db8:a3::13bd. Le poste de travail porte l’identifiant 1234614b-16a9-4003-a847-012345679d68, le cookie de test est cookie-demo-00164-15811, et le gabarit biométrique est BIO-DEMO-008646 (référence vocale distincte : VOICE-TEST-00164). Le véhicule mentionné est ZZ-031-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Apolline Nacreclairon et ajouté une note de suivi à CLT-000164-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2161; la référence du lot est BATCH-OPS-2026-815. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Apolline Nacreclairon |
| Date | 1986-12-14 |
| Contact | apolline.nacreclairon66@example.invalid |
| Client | CLT-000164-Q |
| Incident | INC-2026-06700 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2161 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Apolline Nacreclairon, identifiant CLT-000164-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 165 : Marketing / consentement | dossier fictif INC-2026-06741

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Romane Perrivigne, née le 1993-05-27. Le dossier la rattache à 89, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est romane.perrivigne67@example.invalid et son téléphone est 06 39 98 60 79; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 60 79. La fiche de contact porte le pseudonyme r.perrivigne_775. Le compte client est CLT-000165-Q, et la référence RH éventuelle est EMP-103217. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Perrivigne.

**Traitement du dossier.** Le 2025-01-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Clémence Lisirune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 272,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 68 09 99 165 813 00. La domiciliation bancaire fictive indique FR00 7675 0754 4161 5928 8023 462, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.6; la trace IPv6 associée est 2001:db8:a4::13dc. Le poste de travail porte l’identifiant 1234615c-16b0-4004-a854-012345679d87, le cookie de test est cookie-demo-00165-15908, et le gabarit biométrique est BIO-DEMO-008699 (référence vocale distincte : VOICE-TEST-00165). Le véhicule mentionné est ZZ-068-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Romane Perrivigne et ajouté une note de suivi à CLT-000165-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2174; la référence du lot est BATCH-OPS-2026-832. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Romane Perrivigne |
| Date | 1993-05-27 |
| Contact | romane.perrivigne67@example.invalid |
| Client | CLT-000165-Q |
| Incident | INC-2026-06741 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2174 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Romane Perrivigne, 06 39 98 60 79, romane.perrivigne67@example.invalid; le rappel est prévu autour du 2025-01-15.”


## Cas 166 : Recherche / enquête | dossier fictif INC-2026-06782

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Ambre Pavofleur, née le 2000-10-13. Le dossier la rattache à 106, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est ambre.pavofleur68@example.invalid et son téléphone est 06 39 98 61 16; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 61 16. La fiche de contact porte le pseudonyme a.pavofleur_798. Le compte client est CLT-000166-Q, et la référence RH éventuelle est EMP-103236. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pavofleur.

**Traitement du dossier.** Le 2026-04-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Eden Lorimurel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 445,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 69 10 99 166 950 00. La domiciliation bancaire fictive indique FR00 7776 0867 4288 6059 8160 601, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.23; la trace IPv6 associée est 2001:db8:a5::13fb. Le poste de travail porte l’identifiant 1234616d-16b7-4005-a861-012345679da6, le cookie de test est cookie-demo-00166-16005, et le gabarit biométrique est BIO-DEMO-008752 (référence vocale distincte : VOICE-TEST-00166). Le véhicule mentionné est ZZ-105-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ambre Pavofleur et ajouté une note de suivi à CLT-000166-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ambre PAVOFLEUR; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2187; la référence du lot est BATCH-OPS-2026-849. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ambre Pavofleur |
| Date | 2000-10-13 |
| Contact | ambre.pavofleur68@example.invalid |
| Client | CLT-000166-Q |
| Incident | INC-2026-06782 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2187 |

**Autre formulation observée.** Note d’audit : le lien entre a.pavofleur_798, 192.0.2.23 et 1234616d-16b7-4005-a861-012345679da6 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 167 : Logistique / livraison | dossier fictif INC-2026-06823

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Théo Noroorée, née le 1964-03-26. Le dossier la rattache à 123, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est theo.norooree69@example.invalid et son téléphone est 06 39 98 61 53; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 61 53. La fiche de contact porte le pseudonyme t.noroorée_821. Le compte client est CLT-000167-Q, et la référence RH éventuelle est EMP-103255. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Noroorée.

**Traitement du dossier.** Le 2025-07-02, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Léonie Briscendre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 618,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 70 11 99 167 087 00. La domiciliation bancaire fictive indique FR00 7877 0980 4415 6190 8297 740, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.40; la trace IPv6 associée est 2001:db8:a6::141a. Le poste de travail porte l’identifiant 1234617e-16be-4006-a86e-012345679dc5, le cookie de test est cookie-demo-00167-16102, et le gabarit biométrique est BIO-DEMO-008805 (référence vocale distincte : VOICE-TEST-00167). Le véhicule mentionné est ZZ-142-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Théo Noroorée et ajouté une note de suivi à CLT-000167-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2200; la référence du lot est BATCH-OPS-2026-866. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Théo Noroorée |
| Date | 1964-03-26 |
| Contact | theo.norooree69@example.invalid |
| Client | CLT-000167-Q |
| Incident | INC-2026-06823 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2200 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 168 : Sécurité / contrôle d’accès | dossier fictif INC-2026-06864

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Naël Rosibrise, née le 1971-08-12. Le dossier la rattache à 140, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est nael.rosibrise70@example.invalid et son téléphone est 06 39 98 61 90; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 61 90. La fiche de contact porte le pseudonyme n.rosibrise_844. Le compte client est CLT-000168-Q, et la référence RH éventuelle est EMP-103274. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rosibrise.

**Traitement du dossier.** Le 2026-10-09, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Romane Lunémistral, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 791,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 71 12 99 168 224 00. La domiciliation bancaire fictive indique FR00 7978 1093 4542 6321 8434 879, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.57; la trace IPv6 associée est 2001:db8:a7::1439. Le poste de travail porte l’identifiant 1234618f-16c5-4007-a87b-012345679de4, le cookie de test est cookie-demo-00168-16199, et le gabarit biométrique est BIO-DEMO-008858 (référence vocale distincte : VOICE-TEST-00168). Le véhicule mentionné est ZZ-179-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Naël Rosibrise et ajouté une note de suivi à CLT-000168-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2213; la référence du lot est BATCH-OPS-2026-883. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Naël Rosibrise |
| Date | 1971-08-12 |
| Contact | nael.rosibrise70@example.invalid |
| Client | CLT-000168-Q |
| Incident | INC-2026-06864 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2213 |

**Autre formulation observée.** Version importée : Naël Rosibrise; date=1971-08-12; rue=140, rue des Nuages Bas, 99900 Aubier-des-Marées, France; téléphone=06 39 98 61 90; courriel=nael.rosibrise70@example.invalid; statut=à contrôler.


## Cas 169 : RH / gestion du personnel | dossier fictif INC-2026-06905

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Titouan Solravel, née le 1978-01-25. Le dossier la rattache à 157, rue du Phare Éteint, 99900 Pluviane, France. Son email est titouan.solravel71@example.invalid et son téléphone est 06 39 98 62 27; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 62 27. La fiche de contact porte le pseudonyme t.solravel_867. Le compte client est CLT-000169-Q, et la référence RH éventuelle est EMP-103293. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Solravel.

**Traitement du dossier.** Le 2025-01-16, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Mélina Épilune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 964,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 72 01 99 169 361 00. La domiciliation bancaire fictive indique FR00 8079 1206 4669 6452 8571 018, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.74; la trace IPv6 associée est 2001:db8:a8::1458. Le poste de travail porte l’identifiant 123461a0-16cc-4008-a888-012345679e03, le cookie de test est cookie-demo-00169-16296, et le gabarit biométrique est BIO-DEMO-008911 (référence vocale distincte : VOICE-TEST-00169). Le véhicule mentionné est ZZ-216-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Titouan Solravel et ajouté une note de suivi à CLT-000169-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 62 27. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2226; la référence du lot est BATCH-OPS-2026-900. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Titouan Solravel |
| Date | 1978-01-25 |
| Contact | titouan.solravel71@example.invalid |
| Client | CLT-000169-Q |
| Incident | INC-2026-06905 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2226 |

**Autre formulation observée.** Le message reçu disait : « Pour Titouan Solravel, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-06905. »


## Cas 170 : CRM / relation client | dossier fictif INC-2026-06946

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Inès Avelroche, née le 1985-06-11. Le dossier la rattache à 174, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est ines.avelroche72@example.invalid et son téléphone est 06 39 98 62 64; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 62 64. La fiche de contact porte le pseudonyme i.avelroche_890. Le compte client est CLT-000170-Q, et la référence RH éventuelle est EMP-103312. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Avelroche.

**Traitement du dossier.** Le 2026-04-23, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Bastien Florilacier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 137,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 73 02 99 170 498 00. La domiciliation bancaire fictive indique FR00 8180 1319 4796 6583 8708 157, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.91; la trace IPv6 associée est 2001:db8:a9::1477. Le poste de travail porte l’identifiant 123461b1-16d3-4009-a895-012345679e22, le cookie de test est cookie-demo-00170-16393, et le gabarit biométrique est BIO-DEMO-008964 (référence vocale distincte : VOICE-TEST-00170). Le véhicule mentionné est ZZ-253-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Inès Avelroche et ajouté une note de suivi à CLT-000170-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2239; la référence du lot est BATCH-OPS-2026-917. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Inès Avelroche |
| Date | 1985-06-11 |
| Contact | ines.avelroche72@example.invalid |
| Client | CLT-000170-Q |
| Incident | INC-2026-06946 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2239 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Inès Avelroche, identifiant CLT-000170-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 171 : Santé / prise de rendez-vous | dossier fictif INC-2026-06987

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Mila Tremlombre, née le 1992-11-24. Le dossier la rattache à 11, rue des Brumes, 99900 Cendrelac, France. Son email est mila.tremlombre73@example.invalid et son téléphone est 06 39 98 63 01; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 63 01. La fiche de contact porte le pseudonyme m.tremlombre_913. Le compte client est CLT-000171-Q, et la référence RH éventuelle est EMP-103331. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Tremlombre.

**Traitement du dossier.** Le 2025-07-03, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Salomé Orielserein, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 310,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 74 03 99 171 635 00. La domiciliation bancaire fictive indique FR00 8281 1432 4923 6714 8845 296, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.108; la trace IPv6 associée est 2001:db8:aa::1496. Le poste de travail porte l’identifiant 123461c2-16da-4000-a8a2-012345679e41, le cookie de test est cookie-demo-00171-16490, et le gabarit biométrique est BIO-DEMO-009017 (référence vocale distincte : VOICE-TEST-00171). Le véhicule mentionné est ZZ-290-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mila Tremlombre et ajouté une note de suivi à CLT-000171-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient mila TREMLOMBRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2252; la référence du lot est BATCH-OPS-2026-934. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mila Tremlombre |
| Date | 1992-11-24 |
| Contact | mila.tremlombre73@example.invalid |
| Client | CLT-000171-Q |
| Incident | INC-2026-06987 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2252 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Mila Tremlombre, 06 39 98 63 01, mila.tremlombre73@example.invalid; le rappel est prévu autour du 2025-07-03.”


## Cas 172 : Banque / assurance | dossier fictif INC-2026-07028

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Mélina Varnedorin, née le 2013-04-10. Le dossier la rattache à 28, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est melina.varnedorin74@example.invalid et son téléphone est 06 39 98 63 38; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 63 38. La fiche de contact porte le pseudonyme m.varnedorin_936. Le compte client est CLT-000172-Q, et la référence RH éventuelle est EMP-103350. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Varnedorin.

**Traitement du dossier.** Le 2026-10-10, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Eliott Érablefarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 483,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 75 04 99 172 772 00. La domiciliation bancaire fictive indique FR00 8382 1545 5050 6845 8982 435, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.125; la trace IPv6 associée est 2001:db8:ab::14b5. Le poste de travail porte l’identifiant 123461d3-16e1-4001-a8af-012345679e60, le cookie de test est cookie-demo-00172-16587, et le gabarit biométrique est BIO-DEMO-009070 (référence vocale distincte : VOICE-TEST-00172). Le véhicule mentionné est ZZ-327-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mélina Varnedorin et ajouté une note de suivi à CLT-000172-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2013-04-10. Le proche de référence est Eliott Érablefarin. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2265; la référence du lot est BATCH-OPS-2026-951. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mélina Varnedorin |
| Date | 2013-04-10 |
| Contact | melina.varnedorin74@example.invalid |
| Client | CLT-000172-Q |
| Incident | INC-2026-07028 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2265 |

**Autre formulation observée.** Note d’audit : le lien entre m.varnedorin_936, 192.0.2.125 et 123461d3-16e1-4001-a8af-012345679e60 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 173 : Éducation / accompagnement | dossier fictif INC-2026-07069

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Maël Célvaux, née le 1963-09-23. Le dossier la rattache à 45, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est mael.celvaux75@example.invalid et son téléphone est 06 39 98 63 75; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 63 75. La fiche de contact porte le pseudonyme m.célvaux_959. Le compte client est CLT-000173-Q, et la référence RH éventuelle est EMP-103369. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Célvaux.

**Traitement du dossier.** Le 2025-01-17, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Ariane Valnette, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 656,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 76 05 99 173 909 00. La domiciliation bancaire fictive indique FR00 8483 1658 5177 6976 9119 574, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.142; la trace IPv6 associée est 2001:db8:ac::14d4. Le poste de travail porte l’identifiant 123461e4-16e8-4002-a8bc-012345679e7f, le cookie de test est cookie-demo-00173-16684, et le gabarit biométrique est BIO-DEMO-009123 (référence vocale distincte : VOICE-TEST-00173). Le véhicule mentionné est ZZ-364-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maël Célvaux et ajouté une note de suivi à CLT-000173-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2278; la référence du lot est BATCH-OPS-2026-968. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maël Célvaux |
| Date | 1963-09-23 |
| Contact | mael.celvaux75@example.invalid |
| Client | CLT-000173-Q |
| Incident | INC-2026-07069 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2278 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 174 : Juridique / contrat | dossier fictif INC-2026-07110

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Célestin Seredorelle, née le 1970-02-09. Le dossier la rattache à 62, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est celestin.seredorelle76@example.invalid et son téléphone est 06 39 98 64 12; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 64 12. La fiche de contact porte le pseudonyme c.seredorelle_982. Le compte client est CLT-000174-Q, et la référence RH éventuelle est EMP-103388. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Seredorelle.

**Traitement du dossier.** Le 2026-04-24, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Théo Mirasorel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 829,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 77 06 99 174 046 00. La domiciliation bancaire fictive indique FR00 8584 1771 5304 7107 9256 713, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.159; la trace IPv6 associée est 2001:db8:ad::14f3. Le poste de travail porte l’identifiant 123461f5-16ef-4003-a8c9-012345679e9e, le cookie de test est cookie-demo-00174-16781, et le gabarit biométrique est BIO-DEMO-009176 (référence vocale distincte : VOICE-TEST-00174). Le véhicule mentionné est ZZ-401-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Célestin Seredorelle et ajouté une note de suivi à CLT-000174-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2291; la référence du lot est BATCH-OPS-2026-985. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Célestin Seredorelle |
| Date | 1970-02-09 |
| Contact | celestin.seredorelle76@example.invalid |
| Client | CLT-000174-Q |
| Incident | INC-2026-07110 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2291 |

**Autre formulation observée.** Version importée : Célestin Seredorelle; date=1970-02-09; rue=62, rue du Phare Éteint, 99900 Orée-du-Mistral, France; téléphone=06 39 98 64 12; courriel=celestin.seredorelle76@example.invalid; statut=à contrôler.


## Cas 175 : Support informatique | dossier fictif INC-2026-07151

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Léandre Églanbelle, née le 1977-07-22. Le dossier la rattache à 79, rue des Pivoines Grises, 99900 Valmousse, France. Son email est leandre.eglanbelle77@example.invalid et son téléphone est 06 39 98 64 49; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 64 49. La fiche de contact porte le pseudonyme l.églanbelle_006. Le compte client est CLT-000175-Q, et la référence RH éventuelle est EMP-103407. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Églanbelle.

**Traitement du dossier.** Le 2025-07-04, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Célestin Brumemarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 002,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 78 07 99 175 183 00. La domiciliation bancaire fictive indique FR00 8685 1884 5431 7238 9393 852, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.176; la trace IPv6 associée est 2001:db8:ae::1512. Le poste de travail porte l’identifiant 12346206-16f6-4004-a8d6-012345679ebd, le cookie de test est cookie-demo-00175-16878, et le gabarit biométrique est BIO-DEMO-009229 (référence vocale distincte : VOICE-TEST-00175). Le véhicule mentionné est ZZ-438-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léandre Églanbelle et ajouté une note de suivi à CLT-000175-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2304; la référence du lot est BATCH-OPS-2026-003. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léandre Églanbelle |
| Date | 1977-07-22 |
| Contact | leandre.eglanbelle77@example.invalid |
| Client | CLT-000175-Q |
| Incident | INC-2026-07151 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2304 |

**Autre formulation observée.** Le message reçu disait : « Pour Léandre Églanbelle, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-07151. »


## Cas 176 : Voyage / réservation | dossier fictif INC-2026-07192

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Nora Rivbrume, née le 1984-12-08. Le dossier la rattache à 96, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est nora.rivbrume78@example.invalid et son téléphone est 06 39 98 64 86; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 64 86. La fiche de contact porte le pseudonyme n.rivbrume_029. Le compte client est CLT-000176-Q, et la référence RH éventuelle est EMP-103426. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rivbrume.

**Traitement du dossier.** Le 2026-10-11, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Ilyan Mélidune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 175,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 79 08 99 176 320 00. La domiciliation bancaire fictive indique FR00 8786 1997 5558 7369 9530 991, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.193; la trace IPv6 associée est 2001:db8:af::1531. Le poste de travail porte l’identifiant 12346217-16fd-4005-a8e3-012345679edc, le cookie de test est cookie-demo-00176-16975, et le gabarit biométrique est BIO-DEMO-009282 (référence vocale distincte : VOICE-TEST-00176). Le véhicule mentionné est ZZ-475-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nora Rivbrume et ajouté une note de suivi à CLT-000176-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient nora RIVBRUME; vérifier que le changement de casse ne bloque pas la détection.

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 64 86. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2317; la référence du lot est BATCH-OPS-2026-020. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nora Rivbrume |
| Date | 1984-12-08 |
| Contact | nora.rivbrume78@example.invalid |
| Client | CLT-000176-Q |
| Incident | INC-2026-07192 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2317 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Nora Rivbrume, identifiant CLT-000176-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 177 : Marketing / consentement | dossier fictif INC-2026-07233

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Anaïs Alouloriot, née le 1991-05-21. Le dossier la rattache à 113, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est anais.alouloriot79@example.invalid et son téléphone est 06 39 98 65 23; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 65 23. La fiche de contact porte le pseudonyme a.alouloriot_052. Le compte client est CLT-000177-Q, et la référence RH éventuelle est EMP-103445. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Alouloriot.

**Traitement du dossier.** Le 2025-01-18, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Lucile Vanisac, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 348,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 80 09 99 177 457 00. La domiciliation bancaire fictive indique FR00 8887 2110 5685 7500 9667 130, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.210; la trace IPv6 associée est 2001:db8:b0::1550. Le poste de travail porte l’identifiant 12346228-1704-4006-a8f0-012345679efb, le cookie de test est cookie-demo-00177-17072, et le gabarit biométrique est BIO-DEMO-009335 (référence vocale distincte : VOICE-TEST-00177). Le véhicule mentionné est ZZ-512-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Anaïs Alouloriot et ajouté une note de suivi à CLT-000177-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2330; la référence du lot est BATCH-OPS-2026-037. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Anaïs Alouloriot |
| Date | 1991-05-21 |
| Contact | anais.alouloriot79@example.invalid |
| Client | CLT-000177-Q |
| Incident | INC-2026-07233 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2330 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Anaïs Alouloriot, 06 39 98 65 23, anais.alouloriot79@example.invalid; le rappel est prévu autour du 2025-01-18.”


## Cas 178 : Recherche / enquête | dossier fictif INC-2026-07274

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Jade Belaubier, née le 1998-10-07. Le dossier la rattache à 130, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est jade.belaubier80@example.invalid et son téléphone est 06 39 98 65 60; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 65 60. La fiche de contact porte le pseudonyme j.belaubier_075. Le compte client est CLT-000178-Q, et la référence RH éventuelle est EMP-103464. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Belaubier.

**Traitement du dossier.** Le 2026-04-25, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Gabin Aurimousse, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 421,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 81 10 99 178 594 00. La domiciliation bancaire fictive indique FR00 8988 2223 5812 7631 9804 269, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.227; la trace IPv6 associée est 2001:db8:b1::156f. Le poste de travail porte l’identifiant 12346239-170b-4007-a8fd-012345679f1a, le cookie de test est cookie-demo-00178-17169, et le gabarit biométrique est BIO-DEMO-009388 (référence vocale distincte : VOICE-TEST-00178). Le véhicule mentionné est ZZ-549-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Jade Belaubier et ajouté une note de suivi à CLT-000178-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2343; la référence du lot est BATCH-OPS-2026-054. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Jade Belaubier |
| Date | 1998-10-07 |
| Contact | jade.belaubier80@example.invalid |
| Client | CLT-000178-Q |
| Incident | INC-2026-07274 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2343 |

**Autre formulation observée.** Note d’audit : le lien entre j.belaubier_075, 192.0.2.227 et 12346239-170b-4007-a8fd-012345679f1a doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 179 : Logistique / livraison | dossier fictif INC-2026-07315

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Bastien Fauvevalon, née le 2005-03-20. Le dossier la rattache à 147, rue du Phare Éteint, 99900 Nacréville, France. Son email est bastien.fauvevalon81@example.invalid et son téléphone est 06 39 98 65 97; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 65 97. La fiche de contact porte le pseudonyme b.fauvevalon_098. Le compte client est CLT-000179-Q, et la référence RH éventuelle est EMP-103483. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Fauvevalon.

**Traitement du dossier.** Le 2025-07-05, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Lina Montaroussin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 594,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 82 11 99 179 731 00. La domiciliation bancaire fictive indique FR00 9089 2336 5939 7762 9941 408, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.244; la trace IPv6 associée est 2001:db8:b2::158e. Le poste de travail porte l’identifiant 1234624a-1712-4008-a90a-012345679f39, le cookie de test est cookie-demo-00179-17266, et le gabarit biométrique est BIO-DEMO-009441 (référence vocale distincte : VOICE-TEST-00179). Le véhicule mentionné est ZZ-586-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Bastien Fauvevalon et ajouté une note de suivi à CLT-000179-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2356; la référence du lot est BATCH-OPS-2026-071. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Bastien Fauvevalon |
| Date | 2005-03-20 |
| Contact | bastien.fauvevalon81@example.invalid |
| Client | CLT-000179-Q |
| Incident | INC-2026-07315 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2356 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 180 : Sécurité / contrôle d’accès | dossier fictif INC-2026-07356

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Malo Dorémeline, née le 1969-08-06. Le dossier la rattache à 164, rue des Pivoines Grises, 99900 Brumeval, France. Son email est malo.doremeline82@example.invalid et son téléphone est 06 39 98 66 34; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 66 34. La fiche de contact porte le pseudonyme m.dorémeline_121. Le compte client est CLT-000180-Q, et la référence RH éventuelle est EMP-103502. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Dorémeline.

**Traitement du dossier.** Le 2026-10-12, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Titouan Nivvardin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 767,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 83 12 99 180 868 00. La domiciliation bancaire fictive indique FR00 9190 2449 6066 7893 0078 547, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.8; la trace IPv6 associée est 2001:db8:b3::15ad. Le poste de travail porte l’identifiant 1234625b-1719-4009-a917-012345679f58, le cookie de test est cookie-demo-00180-17363, et le gabarit biométrique est BIO-DEMO-009494 (référence vocale distincte : VOICE-TEST-00180). Le véhicule mentionné est ZZ-623-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Malo Dorémeline et ajouté une note de suivi à CLT-000180-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2369; la référence du lot est BATCH-OPS-2026-088. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Malo Dorémeline |
| Date | 1969-08-06 |
| Contact | malo.doremeline82@example.invalid |
| Client | CLT-000180-Q |
| Incident | INC-2026-07356 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2369 |

**Autre formulation observée.** Version importée : Malo Dorémeline; date=1969-08-06; rue=164, rue des Pivoines Grises, 99900 Brumeval, France; téléphone=06 39 98 66 34; courriel=malo.doremeline82@example.invalid; statut=à contrôler.


## Cas 181 : RH / gestion du personnel | dossier fictif INC-2026-07397

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Ilyan Corvivalise, née le 2014-01-19. Le dossier la rattache à 1, rue des Brumes, 99900 Val-des-Nuages, France. Son email est ilyan.corvivalise83@example.invalid et son téléphone est 06 39 98 66 71; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 66 71. La fiche de contact porte le pseudonyme i.corvivalise_144. Le compte client est CLT-000181-Q, et la référence RH éventuelle est EMP-103521. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Corvivalise.

**Traitement du dossier.** Le 2025-01-19, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Nora Virenacré, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 940,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 84 01 99 181 005 00. La domiciliation bancaire fictive indique FR00 9291 2562 6193 8024 0215 686, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.25; la trace IPv6 associée est 2001:db8:b4::15cc. Le poste de travail porte l’identifiant 1234626c-1720-4000-a924-012345679f77, le cookie de test est cookie-demo-00181-17460, et le gabarit biométrique est BIO-DEMO-009547 (référence vocale distincte : VOICE-TEST-00181). Le véhicule mentionné est ZZ-660-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ilyan Corvivalise et ajouté une note de suivi à CLT-000181-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ilyan CORVIVALISE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2014-01-19. Le proche de référence est Nora Virenacré. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2382; la référence du lot est BATCH-OPS-2026-105. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ilyan Corvivalise |
| Date | 2014-01-19 |
| Contact | ilyan.corvivalise83@example.invalid |
| Client | CLT-000181-Q |
| Incident | INC-2026-07397 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2382 |

**Autre formulation observée.** Le message reçu disait : « Pour Ilyan Corvivalise, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-07397. »


## Cas 182 : CRM / relation client | dossier fictif INC-2026-07438

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Émilie Lisirune, née le 1983-06-05. Le dossier la rattache à 18, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est emilie.lisirune84@example.invalid et son téléphone est 06 39 98 67 08; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 67 08. La fiche de contact porte le pseudonyme é.lisirune_167. Le compte client est CLT-000182-Q, et la référence RH éventuelle est EMP-103540. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lisirune.

**Traitement du dossier.** Le 2026-04-26, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Lison Cenddombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 113,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 85 02 99 182 142 00. La domiciliation bancaire fictive indique FR00 9392 2675 6320 8155 0352 825, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.42; la trace IPv6 associée est 2001:db8:b5::15eb. Le poste de travail porte l’identifiant 1234627d-1727-4001-a931-012345679f96, le cookie de test est cookie-demo-00182-17557, et le gabarit biométrique est BIO-DEMO-009600 (référence vocale distincte : VOICE-TEST-00182). Le véhicule mentionné est ZZ-697-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Émilie Lisirune et ajouté une note de suivi à CLT-000182-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2395; la référence du lot est BATCH-OPS-2026-122. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Émilie Lisirune |
| Date | 1983-06-05 |
| Contact | emilie.lisirune84@example.invalid |
| Client | CLT-000182-Q |
| Incident | INC-2026-07438 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2395 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Émilie Lisirune, identifiant CLT-000182-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 183 : Santé / prise de rendez-vous | dossier fictif INC-2026-07479

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Lison Lorimurel, née le 1990-11-18. Le dossier la rattache à 35, rue des Nuages Bas, 99900 Mirebrise, France. Son email est lison.lorimurel85@example.invalid et son téléphone est 06 39 98 67 45; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 67 45. La fiche de contact porte le pseudonyme l.lorimurel_190. Le compte client est CLT-000183-Q, et la référence RH éventuelle est EMP-103559. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lorimurel.

**Traitement du dossier.** Le 2025-07-06, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Sofia Saphvialet, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 286,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 86 03 99 183 279 00. La domiciliation bancaire fictive indique FR00 9493 2788 6447 8286 0489 964, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.59; la trace IPv6 associée est 2001:db8:b6::160a. Le poste de travail porte l’identifiant 1234628e-172e-4002-a93e-012345679fb5, le cookie de test est cookie-demo-00183-17654, et le gabarit biométrique est BIO-DEMO-009653 (référence vocale distincte : VOICE-TEST-00183). Le véhicule mentionné est ZZ-734-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lison Lorimurel et ajouté une note de suivi à CLT-000183-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 67 45. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2408; la référence du lot est BATCH-OPS-2026-139. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lison Lorimurel |
| Date | 1990-11-18 |
| Contact | lison.lorimurel85@example.invalid |
| Client | CLT-000183-Q |
| Incident | INC-2026-07479 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2408 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Lison Lorimurel, 06 39 98 67 45, lison.lorimurel85@example.invalid; le rappel est prévu autour du 2025-07-06.”


## Cas 184 : Banque / assurance | dossier fictif INC-2026-07520

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Clémence Briscendre, née le 1997-04-04. Le dossier la rattache à 52, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est clemence.briscendre86@example.invalid et son téléphone est 06 39 98 67 82; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 67 82. La fiche de contact porte le pseudonyme c.briscendre_213. Le compte client est CLT-000184-Q, et la référence RH éventuelle est EMP-103578. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Briscendre.

**Traitement du dossier.** Le 2026-10-13, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Marceau Clairclaire, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 459,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 87 04 99 184 416 00. La domiciliation bancaire fictive indique FR00 9594 2901 6574 8417 0626 103, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.76; la trace IPv6 associée est 2001:db8:b7::1629. Le poste de travail porte l’identifiant 1234629f-1735-4003-a94b-012345679fd4, le cookie de test est cookie-demo-00184-17751, et le gabarit biométrique est BIO-DEMO-009706 (référence vocale distincte : VOICE-TEST-00184). Le véhicule mentionné est ZZ-771-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Clémence Briscendre et ajouté une note de suivi à CLT-000184-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2421; la référence du lot est BATCH-OPS-2026-156. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Clémence Briscendre |
| Date | 1997-04-04 |
| Contact | clemence.briscendre86@example.invalid |
| Client | CLT-000184-Q |
| Incident | INC-2026-07520 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2421 |

**Autre formulation observée.** Note d’audit : le lien entre c.briscendre_213, 192.0.2.76 et 1234629f-1735-4003-a94b-012345679fd4 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 185 : Éducation / accompagnement | dossier fictif INC-2026-07561

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Ismaël Lunémistral, née le 2004-09-17. Le dossier la rattache à 69, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est ismael.lunemistral87@example.invalid et son téléphone est 06 39 98 68 19; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 68 19. La fiche de contact porte le pseudonyme i.lunémistral_236. Le compte client est CLT-000185-Q, et la référence RH éventuelle est EMP-103597. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Lunémistral.

**Traitement du dossier.** Le 2025-01-20, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Apolline Ormeplaine, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 632,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 88 05 99 185 553 00. La domiciliation bancaire fictive indique FR00 9695 3014 6701 8548 0763 242, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.93; la trace IPv6 associée est 2001:db8:b8::1648. Le poste de travail porte l’identifiant 123462b0-173c-4004-a958-012345679ff3, le cookie de test est cookie-demo-00185-17848, et le gabarit biométrique est BIO-DEMO-009759 (référence vocale distincte : VOICE-TEST-00185). Le véhicule mentionné est ZZ-808-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ismaël Lunémistral et ajouté une note de suivi à CLT-000185-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2434; la référence du lot est BATCH-OPS-2026-173. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ismaël Lunémistral |
| Date | 2004-09-17 |
| Contact | ismael.lunemistral87@example.invalid |
| Client | CLT-000185-Q |
| Incident | INC-2026-07561 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2434 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 186 : Juridique / contrat | dossier fictif INC-2026-07602

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Salomé Épilune, née le 1968-02-03. Le dossier la rattache à 86, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est salome.epilune88@example.invalid et son téléphone est 06 39 98 68 56; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 68 56. La fiche de contact porte le pseudonyme s.épilune_259. Le compte client est CLT-000186-Q, et la référence RH éventuelle est EMP-103616. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Épilune.

**Traitement du dossier.** Le 2026-04-27, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Mila Pluvivelin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 805,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 89 06 99 186 690 00. La domiciliation bancaire fictive indique FR00 9796 3127 6828 8679 0900 381, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.110; la trace IPv6 associée est 2001:db8:b9::1667. Le poste de travail porte l’identifiant 123462c1-1743-4005-a965-01234567a012, le cookie de test est cookie-demo-00186-17945, et le gabarit biométrique est BIO-DEMO-009812 (référence vocale distincte : VOICE-TEST-00186). Le véhicule mentionné est ZZ-845-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Salomé Épilune et ajouté une note de suivi à CLT-000186-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient salomé ÉPILUNE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2447; la référence du lot est BATCH-OPS-2026-190. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Salomé Épilune |
| Date | 1968-02-03 |
| Contact | salome.epilune88@example.invalid |
| Client | CLT-000186-Q |
| Incident | INC-2026-07602 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2447 |

**Autre formulation observée.** Version importée : Salomé Épilune; date=1968-02-03; rue=86, rue des Brumes, 99900 Soleil-des-Falaises, France; téléphone=06 39 98 68 56; courriel=salome.epilune88@example.invalid; statut=à contrôler.


## Cas 187 : Support informatique | dossier fictif INC-2026-07643

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Nino Florilacier, née le 1975-07-16. Le dossier la rattache à 103, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est nino.florilacier89@example.invalid et son téléphone est 06 39 98 68 93; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 68 93. La fiche de contact porte le pseudonyme n.florilacier_282. Le compte client est CLT-000187-Q, et la référence RH éventuelle est EMP-103635. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Florilacier.

**Traitement du dossier.** Le 2025-07-07, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Jade Nacreclairon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 978,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 90 07 99 187 827 00. La domiciliation bancaire fictive indique FR00 9897 3240 6955 8810 1037 520, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.127; la trace IPv6 associée est 2001:db8:ba::1686. Le poste de travail porte l’identifiant 123462d2-174a-4006-a972-01234567a031, le cookie de test est cookie-demo-00187-18042, et le gabarit biométrique est BIO-DEMO-009865 (référence vocale distincte : VOICE-TEST-00187). Le véhicule mentionné est ZZ-882-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nino Florilacier et ajouté une note de suivi à CLT-000187-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2460; la référence du lot est BATCH-OPS-2026-207. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nino Florilacier |
| Date | 1975-07-16 |
| Contact | nino.florilacier89@example.invalid |
| Client | CLT-000187-Q |
| Incident | INC-2026-07643 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2460 |

**Autre formulation observée.** Le message reçu disait : « Pour Nino Florilacier, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-07643. »


## Cas 188 : Voyage / réservation | dossier fictif INC-2026-07684

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Lucile Orielserein, née le 1982-12-02. Le dossier la rattache à 120, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est lucile.orielserein90@example.invalid et son téléphone est 06 39 98 69 30; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 69 30. La fiche de contact porte le pseudonyme l.orielserein_305. Le compte client est CLT-000188-Q, et la référence RH éventuelle est EMP-103654. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Orielserein.

**Traitement du dossier.** Le 2026-10-14, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Ismaël Perrivigne, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 151,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 91 08 99 188 964 00. La domiciliation bancaire fictive indique FR00 9998 3353 7082 8941 1174 659, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.144; la trace IPv6 associée est 2001:db8:bb::16a5. Le poste de travail porte l’identifiant 123462e3-1751-4007-a97f-01234567a050, le cookie de test est cookie-demo-00188-18139, et le gabarit biométrique est BIO-DEMO-009918 (référence vocale distincte : VOICE-TEST-00188). Le véhicule mentionné est ZZ-919-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lucile Orielserein et ajouté une note de suivi à CLT-000188-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2473; la référence du lot est BATCH-OPS-2026-224. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lucile Orielserein |
| Date | 1982-12-02 |
| Contact | lucile.orielserein90@example.invalid |
| Client | CLT-000188-Q |
| Incident | INC-2026-07684 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2473 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Lucile Orielserein, identifiant CLT-000188-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 189 : Marketing / consentement | dossier fictif INC-2026-07725

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Noé Érablefarin, née le 1989-05-15. Le dossier la rattache à 137, rue du Phare Éteint, 99900 Pluviane, France. Son email est noe.erablefarin91@example.invalid et son téléphone est 06 39 98 69 67; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 69 67. La fiche de contact porte le pseudonyme n.érablefarin_328. Le compte client est CLT-000189-Q, et la référence RH éventuelle est EMP-103673. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Érablefarin.

**Traitement du dossier.** Le 2025-01-21, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Yasmine Pavofleur, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 324,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 92 09 99 189 101 00. La domiciliation bancaire fictive indique FR00 0099 3466 7209 9072 1311 798, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.161; la trace IPv6 associée est 2001:db8:bc::16c4. Le poste de travail porte l’identifiant 123462f4-1758-4008-a98c-01234567a06f, le cookie de test est cookie-demo-00189-18236, et le gabarit biométrique est BIO-DEMO-009971 (référence vocale distincte : VOICE-TEST-00189). Le véhicule mentionné est ZZ-956-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Noé Érablefarin et ajouté une note de suivi à CLT-000189-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2486; la référence du lot est BATCH-OPS-2026-241. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Noé Érablefarin |
| Date | 1989-05-15 |
| Contact | noe.erablefarin91@example.invalid |
| Client | CLT-000189-Q |
| Incident | INC-2026-07725 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2486 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Noé Érablefarin, 06 39 98 69 67, noe.erablefarin91@example.invalid; le rappel est prévu autour du 2025-01-21.”


## Cas 190 : Recherche / enquête | dossier fictif INC-2026-07766

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Sofia Valnette, née le 2015-10-01. Le dossier la rattache à 154, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est sofia.valnette92@example.invalid et son téléphone est 06 39 98 70 04; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 70 04. La fiche de contact porte le pseudonyme s.valnette_351. Le compte client est CLT-000190-Q, et la référence RH éventuelle est EMP-103692. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Valnette.

**Traitement du dossier.** Le 2026-04-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Mathis Noroorée, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 497,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 93 10 99 190 238 00. La domiciliation bancaire fictive indique FR00 0200 3579 7336 9203 1448 937, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.178; la trace IPv6 associée est 2001:db8:bd::16e3. Le poste de travail porte l’identifiant 12346305-175f-4009-a999-01234567a08e, le cookie de test est cookie-demo-00190-18333, et le gabarit biométrique est BIO-DEMO-010024 (référence vocale distincte : VOICE-TEST-00190). Le véhicule mentionné est ZZ-993-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sofia Valnette et ajouté une note de suivi à CLT-000190-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 70 04. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2015-10-01. Le proche de référence est Mathis Noroorée. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2499; la référence du lot est BATCH-OPS-2026-258. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sofia Valnette |
| Date | 2015-10-01 |
| Contact | sofia.valnette92@example.invalid |
| Client | CLT-000190-Q |
| Incident | INC-2026-07766 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2499 |

**Autre formulation observée.** Note d’audit : le lien entre s.valnette_351, 192.0.2.178 et 12346305-175f-4009-a999-01234567a08e doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 191 : Logistique / livraison | dossier fictif INC-2026-07807

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Eden Mirasorel, née le 2003-03-14. Le dossier la rattache à 171, rue des Brumes, 99900 Cendrelac, France. Son email est eden.mirasorel93@example.invalid et son téléphone est 06 39 98 70 41; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 70 41. La fiche de contact porte le pseudonyme e.mirasorel_374. Le compte client est CLT-000191-Q, et la référence RH éventuelle est EMP-103711. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mirasorel.

**Traitement du dossier.** Le 2025-07-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Ambre Rosibrise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 670,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 94 11 99 191 375 00. La domiciliation bancaire fictive indique FR00 0301 3692 7463 9334 1585 076, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.195; la trace IPv6 associée est 2001:db8:be::1702. Le poste de travail porte l’identifiant 12346316-1766-4000-a9a6-01234567a0ad, le cookie de test est cookie-demo-00191-18430, et le gabarit biométrique est BIO-DEMO-010077 (référence vocale distincte : VOICE-TEST-00191). Le véhicule mentionné est ZZ-030-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eden Mirasorel et ajouté une note de suivi à CLT-000191-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient eden MIRASOREL; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2512; la référence du lot est BATCH-OPS-2026-275. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eden Mirasorel |
| Date | 2003-03-14 |
| Contact | eden.mirasorel93@example.invalid |
| Client | CLT-000191-Q |
| Incident | INC-2026-07807 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2512 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 192 : Sécurité / contrôle d’accès | dossier fictif INC-2026-07848

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Yasmine Brumemarin, née le 1967-08-27. Le dossier la rattache à 8, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est yasmine.brumemarin94@example.invalid et son téléphone est 06 39 98 70 78; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 70 78. La fiche de contact porte le pseudonyme y.brumemarin_397. Le compte client est CLT-000192-Q, et la référence RH éventuelle est EMP-103730. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Brumemarin.

**Traitement du dossier.** Le 2026-10-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Maël Solravel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 843,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 95 12 99 192 512 00. La domiciliation bancaire fictive indique FR00 0402 3805 7590 9465 1722 215, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.212; la trace IPv6 associée est 2001:db8:bf::1721. Le poste de travail porte l’identifiant 12346327-176d-4001-a9b3-01234567a0cc, le cookie de test est cookie-demo-00192-18527, et le gabarit biométrique est BIO-DEMO-010130 (référence vocale distincte : VOICE-TEST-00192). Le véhicule mentionné est ZZ-067-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Yasmine Brumemarin et ajouté une note de suivi à CLT-000192-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2525; la référence du lot est BATCH-OPS-2026-292. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Yasmine Brumemarin |
| Date | 1967-08-27 |
| Contact | yasmine.brumemarin94@example.invalid |
| Client | CLT-000192-Q |
| Incident | INC-2026-07848 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2525 |

**Autre formulation observée.** Version importée : Yasmine Brumemarin; date=1967-08-27; rue=8, allée des Sept Lanternes, 99900 Églan-sur-Roche, France; téléphone=06 39 98 70 78; courriel=yasmine.brumemarin94@example.invalid; statut=à contrôler.


## Cas 193 : RH / gestion du personnel | dossier fictif INC-2026-07889

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Eliott Mélidune, née le 1974-01-13. Le dossier la rattache à 25, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est eliott.melidune95@example.invalid et son téléphone est 06 39 98 71 15; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 71 15. La fiche de contact porte le pseudonyme e.mélidune_420. Le compte client est CLT-000193-Q, et la référence RH éventuelle est EMP-103749. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Mélidune.

**Traitement du dossier.** Le 2025-01-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Malo Avelroche, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 016,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 96 01 99 193 649 00. La domiciliation bancaire fictive indique FR00 0503 3918 7717 9596 1859 354, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.229; la trace IPv6 associée est 2001:db8:c0::1740. Le poste de travail porte l’identifiant 12346338-1774-4002-a9c0-01234567a0eb, le cookie de test est cookie-demo-00193-18624, et le gabarit biométrique est BIO-DEMO-010183 (référence vocale distincte : VOICE-TEST-00193). Le véhicule mentionné est ZZ-104-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Eliott Mélidune et ajouté une note de suivi à CLT-000193-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2538; la référence du lot est BATCH-OPS-2026-309. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Eliott Mélidune |
| Date | 1974-01-13 |
| Contact | eliott.melidune95@example.invalid |
| Client | CLT-000193-Q |
| Incident | INC-2026-07889 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2538 |

**Autre formulation observée.** Le message reçu disait : « Pour Eliott Mélidune, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-07889. »


## Cas 194 : CRM / relation client | dossier fictif INC-2026-07930

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Zoé Vanisac, née le 1981-06-26. Le dossier la rattache à 42, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est zoe.vanisac96@example.invalid et son téléphone est 06 39 98 71 52; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 71 52. La fiche de contact porte le pseudonyme z.vanisac_443. Le compte client est CLT-000194-Q, et la référence RH éventuelle est EMP-103768. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Vanisac.

**Traitement du dossier.** Le 2026-04-02, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Nino Tremlombre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 189,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 97 02 99 194 786 00. La domiciliation bancaire fictive indique FR00 0604 4031 7844 9727 1996 493, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.246; la trace IPv6 associée est 2001:db8:c1::175f. Le poste de travail porte l’identifiant 12346349-177b-4003-a9cd-01234567a10a, le cookie de test est cookie-demo-00194-18721, et le gabarit biométrique est BIO-DEMO-010236 (référence vocale distincte : VOICE-TEST-00194). Le véhicule mentionné est ZZ-141-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Zoé Vanisac et ajouté une note de suivi à CLT-000194-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2551; la référence du lot est BATCH-OPS-2026-326. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Zoé Vanisac |
| Date | 1981-06-26 |
| Contact | zoe.vanisac96@example.invalid |
| Client | CLT-000194-Q |
| Incident | INC-2026-07930 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2551 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Zoé Vanisac, identifiant CLT-000194-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 195 : Santé / prise de rendez-vous | dossier fictif INC-2026-07971

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Gabin Aurimousse, née le 1988-11-12. Le dossier la rattache à 59, rue des Pivoines Grises, 99900 Valmousse, France. Son email est gabin.aurimousse00@example.invalid et son téléphone est 06 39 98 71 89; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 71 89. La fiche de contact porte le pseudonyme g.aurimousse_466. Le compte client est CLT-000195-Q, et la référence RH éventuelle est EMP-103787. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Aurimousse.

**Traitement du dossier.** Le 2025-07-09, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Zoé Varnedorin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 362,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 98 03 99 195 923 00. La domiciliation bancaire fictive indique FR00 0705 4144 7971 9858 2133 632, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.10; la trace IPv6 associée est 2001:db8:c2::177e. Le poste de travail porte l’identifiant 1234635a-1782-4004-a9da-01234567a129, le cookie de test est cookie-demo-00195-18818, et le gabarit biométrique est BIO-DEMO-010289 (référence vocale distincte : VOICE-TEST-00195). Le véhicule mentionné est ZZ-178-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Gabin Aurimousse et ajouté une note de suivi à CLT-000195-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2564; la référence du lot est BATCH-OPS-2026-343. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Gabin Aurimousse |
| Date | 1988-11-12 |
| Contact | gabin.aurimousse00@example.invalid |
| Client | CLT-000195-Q |
| Incident | INC-2026-07971 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2564 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Gabin Aurimousse, 06 39 98 71 89, gabin.aurimousse00@example.invalid; le rappel est prévu autour du 2025-07-09.”


## Cas 196 : Banque / assurance | dossier fictif INC-2026-08012

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Maëlys Montaroussin, née le 1995-04-25. Le dossier la rattache à 76, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est maelys.montaroussin01@example.invalid et son téléphone est 06 39 98 72 26; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 72 26. La fiche de contact porte le pseudonyme m.montaroussin_489. Le compte client est CLT-000196-Q, et la référence RH éventuelle est EMP-103806. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Montaroussin.

**Traitement du dossier.** Le 2026-10-16, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Sohan Célvaux, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 535,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 60 04 99 196 060 00. La domiciliation bancaire fictive indique FR00 0806 4257 8098 9989 2270 771, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.27; la trace IPv6 associée est 2001:db8:c3::179d. Le poste de travail porte l’identifiant 1234636b-1789-4005-a9e7-01234567a148, le cookie de test est cookie-demo-00196-18915, et le gabarit biométrique est BIO-DEMO-010342 (référence vocale distincte : VOICE-TEST-00196). Le véhicule mentionné est ZZ-215-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maëlys Montaroussin et ajouté une note de suivi à CLT-000196-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient maëlys MONTAROUSSIN; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2577; la référence du lot est BATCH-OPS-2026-360. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maëlys Montaroussin |
| Date | 1995-04-25 |
| Contact | maelys.montaroussin01@example.invalid |
| Client | CLT-000196-Q |
| Incident | INC-2026-08012 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2577 |

**Autre formulation observée.** Note d’audit : le lien entre m.montaroussin_489, 192.0.2.27 et 1234636b-1789-4005-a9e7-01234567a148 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 197 : Éducation / accompagnement | dossier fictif INC-2026-08053

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Marceau Nivvardin, née le 2002-09-11. Le dossier la rattache à 93, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est marceau.nivvardin02@example.invalid et son téléphone est 06 39 98 72 63; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 72 63. La fiche de contact porte le pseudonyme m.nivvardin_512. Le compte client est CLT-000197-Q, et la référence RH éventuelle est EMP-103825. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nivvardin.

**Traitement du dossier.** Le 2025-01-23, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Naël Seredorelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 708,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 61 05 99 197 197 00. La domiciliation bancaire fictive indique FR00 0907 4370 8225 0120 2407 910, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.44; la trace IPv6 associée est 2001:db8:c4::17bc. Le poste de travail porte l’identifiant 1234637c-1790-4006-a9f4-01234567a167, le cookie de test est cookie-demo-00197-19012, et le gabarit biométrique est BIO-DEMO-010395 (référence vocale distincte : VOICE-TEST-00197). Le véhicule mentionné est ZZ-252-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Marceau Nivvardin et ajouté une note de suivi à CLT-000197-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 72 63. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2590; la référence du lot est BATCH-OPS-2026-377. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Marceau Nivvardin |
| Date | 2002-09-11 |
| Contact | marceau.nivvardin02@example.invalid |
| Client | CLT-000197-Q |
| Incident | INC-2026-08053 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2590 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention un gabarit biométrique de démonstration appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 198 : Juridique / contrat | dossier fictif INC-2026-08094

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Léonie Virenacré, née le 1966-02-24. Le dossier la rattache à 110, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est leonie.virenacre03@example.invalid et son téléphone est 06 39 98 73 00; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 73 00. La fiche de contact porte le pseudonyme l.virenacré_535. Le compte client est CLT-000198-Q, et la référence RH éventuelle est EMP-103844. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Virenacré.

**Traitement du dossier.** Le 2026-04-03, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Léandre Églanbelle, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 5 881,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 62 06 99 198 334 00. La domiciliation bancaire fictive indique FR00 1008 4483 8352 0251 2544 049, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.61; la trace IPv6 associée est 2001:db8:c5::17db. Le poste de travail porte l’identifiant 1234638d-1797-4007-aa01-01234567a186, le cookie de test est cookie-demo-00198-19109, et le gabarit biométrique est BIO-DEMO-010448 (référence vocale distincte : VOICE-TEST-00198). Le véhicule mentionné est ZZ-289-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léonie Virenacré et ajouté une note de suivi à CLT-000198-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2603; la référence du lot est BATCH-OPS-2026-394. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léonie Virenacré |
| Date | 1966-02-24 |
| Contact | leonie.virenacre03@example.invalid |
| Client | CLT-000198-Q |
| Incident | INC-2026-08094 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2603 |

**Autre formulation observée.** Version importée : Léonie Virenacré; date=1966-02-24; rue=110, rue des Nuages Bas, 99900 Noroît-les-Jardins, France; téléphone=06 39 98 73 00; courriel=leonie.virenacre03@example.invalid; statut=à contrôler.


## Cas 199 : Support informatique | dossier fictif INC-2026-08135

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Mathis Cenddombre, née le 2016-07-10. Le dossier la rattache à 127, rue du Phare Éteint, 99900 Nacréville, France. Son email est mathis.cenddombre04@example.invalid et son téléphone est 06 39 98 73 37; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 73 37. La fiche de contact porte le pseudonyme m.cenddombre_558. Le compte client est CLT-000199-Q, et la référence RH éventuelle est EMP-103863. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Cenddombre.

**Traitement du dossier.** Le 2025-07-10, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Émilie Rivbrume, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 054,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 63 07 99 199 471 00. La domiciliation bancaire fictive indique FR00 1109 4596 8479 0382 2681 188, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.78; la trace IPv6 associée est 2001:db8:c6::17fa. Le poste de travail porte l’identifiant 1234639e-179e-4008-aa0e-01234567a1a5, le cookie de test est cookie-demo-00199-19206, et le gabarit biométrique est BIO-DEMO-010501 (référence vocale distincte : VOICE-TEST-00199). Le véhicule mentionné est ZZ-326-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mathis Cenddombre et ajouté une note de suivi à CLT-000199-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2016-07-10. Le proche de référence est Émilie Rivbrume. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2616; la référence du lot est BATCH-OPS-2026-411. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mathis Cenddombre |
| Date | 2016-07-10 |
| Contact | mathis.cenddombre04@example.invalid |
| Client | CLT-000199-Q |
| Incident | INC-2026-08135 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2616 |

**Autre formulation observée.** Le message reçu disait : « Pour Mathis Cenddombre, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-08135. »


## Cas 200 : Voyage / réservation | dossier fictif INC-2026-08176

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Ariane Saphvialet, née le 1980-12-23. Le dossier la rattache à 144, rue des Pivoines Grises, 99900 Brumeval, France. Son email est ariane.saphvialet05@example.invalid et son téléphone est 06 39 98 73 74; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 73 74. La fiche de contact porte le pseudonyme a.saphvialet_581. Le compte client est CLT-000200-Q, et la référence RH éventuelle est EMP-103882. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Saphvialet.

**Traitement du dossier.** Le 2026-10-17, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Noé Alouloriot, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 227,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 64 08 99 200 608 00. La domiciliation bancaire fictive indique FR00 1210 4709 8606 0513 2818 327, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.95; la trace IPv6 associée est 2001:db8:c7::1819. Le poste de travail porte l’identifiant 123463af-17a5-4009-aa1b-01234567a1c4, le cookie de test est cookie-demo-00200-19303, et le gabarit biométrique est BIO-DEMO-010554 (référence vocale distincte : VOICE-TEST-00200). Le véhicule mentionné est ZZ-363-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ariane Saphvialet et ajouté une note de suivi à CLT-000200-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2629; la référence du lot est BATCH-OPS-2026-428. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ariane Saphvialet |
| Date | 1980-12-23 |
| Contact | ariane.saphvialet05@example.invalid |
| Client | CLT-000200-Q |
| Incident | INC-2026-08176 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2629 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Ariane Saphvialet, identifiant CLT-000200-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 201 : Marketing / consentement | dossier fictif INC-2026-08217

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Sohan Clairclaire, née le 1987-05-09. Le dossier la rattache à 161, rue des Brumes, 99900 Val-des-Nuages, France. Son email est sohan.clairclaire06@example.invalid et son téléphone est 06 39 98 74 11; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 74 11. La fiche de contact porte le pseudonyme s.clairclaire_604. Le compte client est CLT-000201-Q, et la référence RH éventuelle est EMP-103901. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Clairclaire.

**Traitement du dossier.** Le 2025-01-24, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est analyste de données. Le compte rendu cite le proche Maëlys Belaubier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 400,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 65 09 99 201 745 00. La domiciliation bancaire fictive indique FR00 1311 4822 8733 0644 2955 466, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.112; la trace IPv6 associée est 2001:db8:c8::1838. Le poste de travail porte l’identifiant 123463c0-17ac-4000-aa28-01234567a1e3, le cookie de test est cookie-demo-00201-19400, et le gabarit biométrique est BIO-DEMO-010607 (référence vocale distincte : VOICE-TEST-00201). Le véhicule mentionné est ZZ-400-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Sohan Clairclaire et ajouté une note de suivi à CLT-000201-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient sohan CLAIRCLAIRE; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2642; la référence du lot est BATCH-OPS-2026-445. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Sohan Clairclaire |
| Date | 1987-05-09 |
| Contact | sohan.clairclaire06@example.invalid |
| Client | CLT-000201-Q |
| Incident | INC-2026-08217 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2642 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Sohan Clairclaire, 06 39 98 74 11, sohan.clairclaire06@example.invalid; le rappel est prévu autour du 2025-01-24.”


## Cas 202 : Recherche / enquête | dossier fictif INC-2026-08258

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Lina Ormeplaine, née le 1994-10-22. Le dossier la rattache à 178, allée des Sept Lanternes, 99900 Bellecombe-des-Ormes, France. Son email est lina.ormeplaine07@example.invalid et son téléphone est 06 39 98 74 48; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 74 48. La fiche de contact porte le pseudonyme l.ormeplaine_627. Le compte client est CLT-000202-Q, et la référence RH éventuelle est EMP-103920. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Ormeplaine.

**Traitement du dossier.** Le 2026-04-04, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est juriste contrats. Le compte rendu cite le proche Younès Fauvevalon, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 573,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 66 10 99 202 882 00. La domiciliation bancaire fictive indique FR00 1412 4935 8860 0775 3092 605, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.129; la trace IPv6 associée est 2001:db8:c9::1857. Le poste de travail porte l’identifiant 123463d1-17b3-4001-aa35-01234567a202, le cookie de test est cookie-demo-00202-19497, et le gabarit biométrique est BIO-DEMO-010660 (référence vocale distincte : VOICE-TEST-00202). Le véhicule mentionné est ZZ-437-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Lina Ormeplaine et ajouté une note de suivi à CLT-000202-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2655; la référence du lot est BATCH-OPS-2026-462. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Lina Ormeplaine |
| Date | 1994-10-22 |
| Contact | lina.ormeplaine07@example.invalid |
| Client | CLT-000202-Q |
| Incident | INC-2026-08258 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2655 |

**Autre formulation observée.** Note d’audit : le lien entre l.ormeplaine_627, 192.0.2.129 et 123463d1-17b3-4001-aa35-01234567a202 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 203 : Logistique / livraison | dossier fictif INC-2026-08299

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Younès Pluvivelin, née le 2001-03-08. Le dossier la rattache à 15, rue des Nuages Bas, 99900 Mirebrise, France. Son email est younes.pluvivelin08@example.invalid et son téléphone est 06 39 98 74 85; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 74 85. La fiche de contact porte le pseudonyme y.pluvivelin_650. Le compte client est CLT-000203-Q, et la référence RH éventuelle est EMP-103939. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pluvivelin.

**Traitement du dossier.** Le 2025-07-11, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de sinistres. Le compte rendu cite le proche Inès Dorémeline, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 746,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 67 11 99 203 019 00. La domiciliation bancaire fictive indique FR00 1513 5048 8987 0906 3229 744, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.146; la trace IPv6 associée est 2001:db8:ca::1876. Le poste de travail porte l’identifiant 123463e2-17ba-4002-aa42-01234567a221, le cookie de test est cookie-demo-00203-19594, et le gabarit biométrique est BIO-DEMO-010713 (référence vocale distincte : VOICE-TEST-00203). Le véhicule mentionné est ZZ-474-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Younès Pluvivelin et ajouté une note de suivi à CLT-000203-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2668; la référence du lot est BATCH-OPS-2026-479. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Younès Pluvivelin |
| Date | 2001-03-08 |
| Contact | younes.pluvivelin08@example.invalid |
| Client | CLT-000203-Q |
| Incident | INC-2026-08299 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2668 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive concernant son orientation sexuelle appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 204 : Sécurité / contrôle d’accès | dossier fictif INC-2026-08340

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Apolline Nacreclairon, née le 1965-08-21. Le dossier la rattache à 32, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France. Son email est apolline.nacreclairon09@example.invalid et son téléphone est 06 39 98 75 22; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 75 22. La fiche de contact porte le pseudonyme a.nacreclairon_673. Le compte client est CLT-000204-Q, et la référence RH éventuelle est EMP-103958. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Nacreclairon.

**Traitement du dossier.** Le 2026-10-18, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est préparatrice de commandes. Le compte rendu cite le proche Anaïs Corvivalise, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 6 919,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 68 12 99 204 156 00. La domiciliation bancaire fictive indique FR00 1614 5161 9114 1037 3366 883, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.163; la trace IPv6 associée est 2001:db8:cb::1895. Le poste de travail porte l’identifiant 123463f3-17c1-4003-aa4f-01234567a240, le cookie de test est cookie-demo-00204-19691, et le gabarit biométrique est BIO-DEMO-010766 (référence vocale distincte : VOICE-TEST-00204). Le véhicule mentionné est ZZ-511-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Apolline Nacreclairon et ajouté une note de suivi à CLT-000204-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 75 22. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2681; la référence du lot est BATCH-OPS-2026-496. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Apolline Nacreclairon |
| Date | 1965-08-21 |
| Contact | apolline.nacreclairon09@example.invalid |
| Client | CLT-000204-Q |
| Incident | INC-2026-08340 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2681 |

**Autre formulation observée.** Version importée : Apolline Nacreclairon; date=1965-08-21; rue=32, rue du Phare Éteint, 99900 Sainte-Rosalie-des-Brumes, France; téléphone=06 39 98 75 22; courriel=apolline.nacreclairon09@example.invalid; statut=à contrôler.


## Cas 205 : RH / gestion du personnel | dossier fictif INC-2026-08381

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Romane Perrivigne, née le 1972-01-07. Le dossier la rattache à 49, rue des Pivoines Grises, 99900 Rive-Sereine, France. Son email est romane.perrivigne10@example.invalid et son téléphone est 06 39 98 75 59; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 75 59. La fiche de contact porte le pseudonyme r.perrivigne_696. Le compte client est CLT-000205-Q, et la référence RH éventuelle est EMP-103977. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Perrivigne.

**Traitement du dossier.** Le 2025-01-25, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est assistante de recherche. Le compte rendu cite le proche Clémence Lisirune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 092,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 69 01 99 205 293 00. La domiciliation bancaire fictive indique FR00 1715 5274 9241 1168 3503 022, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.180; la trace IPv6 associée est 2001:db8:cc::18b4. Le poste de travail porte l’identifiant 12346404-17c8-4004-aa5c-01234567a25f, le cookie de test est cookie-demo-00205-19788, et le gabarit biométrique est BIO-DEMO-010819 (référence vocale distincte : VOICE-TEST-00205). Le véhicule mentionné est ZZ-548-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Romane Perrivigne et ajouté une note de suivi à CLT-000205-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2694; la référence du lot est BATCH-OPS-2026-513. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Romane Perrivigne |
| Date | 1972-01-07 |
| Contact | romane.perrivigne10@example.invalid |
| Client | CLT-000205-Q |
| Incident | INC-2026-08381 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2694 |

**Autre formulation observée.** Le message reçu disait : « Pour Romane Perrivigne, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-08381. »


## Cas 206 : CRM / relation client | dossier fictif INC-2026-08422

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Ambre Pavofleur, née le 1979-06-20. Le dossier la rattache à 66, rue des Brumes, 99900 Soleil-des-Falaises, France. Son email est ambre.pavofleur11@example.invalid et son téléphone est 06 39 98 75 96; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 75 96. La fiche de contact porte le pseudonyme a.pavofleur_719. Le compte client est CLT-000206-Q, et la référence RH éventuelle est EMP-103996. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Pavofleur.

**Traitement du dossier.** Le 2026-04-05, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est bibliothécaire. Le compte rendu cite le proche Eden Lorimurel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 265,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 70 02 99 206 430 00. La domiciliation bancaire fictive indique FR00 1816 5387 9368 1299 3640 161, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.197; la trace IPv6 associée est 2001:db8:cd::18d3. Le poste de travail porte l’identifiant 12346415-17cf-4005-aa69-01234567a27e, le cookie de test est cookie-demo-00206-19885, et le gabarit biométrique est BIO-DEMO-010872 (référence vocale distincte : VOICE-TEST-00206). Le véhicule mentionné est ZZ-585-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Ambre Pavofleur et ajouté une note de suivi à CLT-000206-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient ambre PAVOFLEUR; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2707; la référence du lot est BATCH-OPS-2026-530. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Ambre Pavofleur |
| Date | 1979-06-20 |
| Contact | ambre.pavofleur11@example.invalid |
| Client | CLT-000206-Q |
| Incident | INC-2026-08422 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2707 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Ambre Pavofleur, identifiant CLT-000206-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 207 : Santé / prise de rendez-vous | dossier fictif INC-2026-08463

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Théo Noroorée, née le 1986-11-06. Le dossier la rattache à 83, allée des Sept Lanternes, 99900 Port-Églantine, France. Son email est theo.norooree12@example.invalid et son téléphone est 06 39 98 76 33; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 76 33. La fiche de contact porte le pseudonyme t.noroorée_742. Le compte client est CLT-000207-Q, et la référence RH éventuelle est EMP-104015. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Noroorée.

**Traitement du dossier.** Le 2025-07-12, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est gestionnaire de paie. Le compte rendu cite le proche Léonie Briscendre, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 7 438,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 71 03 99 207 567 00. La domiciliation bancaire fictive indique FR00 1917 5500 9495 1430 3777 300, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.214; la trace IPv6 associée est 2001:db8:ce::18f2. Le poste de travail porte l’identifiant 12346426-17d6-4006-aa76-01234567a29d, le cookie de test est cookie-demo-00207-19982, et le gabarit biométrique est BIO-DEMO-010925 (référence vocale distincte : VOICE-TEST-00207). Le véhicule mentionné est ZZ-622-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Théo Noroorée et ajouté une note de suivi à CLT-000207-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2720; la référence du lot est BATCH-OPS-2026-547. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Théo Noroorée |
| Date | 1986-11-06 |
| Contact | theo.norooree12@example.invalid |
| Client | CLT-000207-Q |
| Incident | INC-2026-08463 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2720 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Théo Noroorée, 06 39 98 76 33, theo.norooree12@example.invalid; le rappel est prévu autour du 2025-07-12.”


## Cas 208 : Banque / assurance | dossier fictif INC-2026-08504

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Naël Rosibrise, née le 2017-04-19. Le dossier la rattache à 100, rue des Nuages Bas, 99900 Aubier-des-Marées, France. Son email est nael.rosibrise13@example.invalid et son téléphone est 06 39 98 76 70; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 76 70. La fiche de contact porte le pseudonyme n.rosibrise_765. Le compte client est CLT-000208-Q, et la référence RH éventuelle est EMP-104034. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rosibrise.

**Traitement du dossier.** Le 2026-10-19, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est consultant ERP. Le compte rendu cite le proche Romane Lunémistral, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 511,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 72 04 99 208 704 00. La domiciliation bancaire fictive indique FR00 2018 5613 9622 1561 3914 439, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.231; la trace IPv6 associée est 2001:db8:cf::1911. Le poste de travail porte l’identifiant 12346437-17dd-4007-aa83-01234567a2bc, le cookie de test est cookie-demo-00208-20079, et le gabarit biométrique est BIO-DEMO-010978 (référence vocale distincte : VOICE-TEST-00208). Le véhicule mentionné est ZZ-659-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Naël Rosibrise et ajouté une note de suivi à CLT-000208-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2017-04-19. Le proche de référence est Romane Lunémistral. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2733; la référence du lot est BATCH-OPS-2026-564. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Naël Rosibrise |
| Date | 2017-04-19 |
| Contact | nael.rosibrise13@example.invalid |
| Client | CLT-000208-Q |
| Incident | INC-2026-08504 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2733 |

**Autre formulation observée.** Note d’audit : le lien entre n.rosibrise_765, 192.0.2.231 et 12346437-17dd-4007-aa83-01234567a2bc doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 209 : Éducation / accompagnement | dossier fictif INC-2026-08545

**Contexte.** Le dossier décrit une situation pédagogique entièrement fictive. Les échanges font intervenir une famille, une équipe éducative et un calendrier de suivi. L’exercice consiste à préserver le sens du compte rendu tout en masquant les personnes, les coordonnées et les informations relatives à un mineur.

**Identité et coordonnées.** La personne concernée se nomme Titouan Solravel, née le 2000-09-05. Le dossier la rattache à 117, rue du Phare Éteint, 99900 Pluviane, France. Son email est titouan.solravel14@example.invalid et son téléphone est 06 39 98 77 07; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 77 07. La fiche de contact porte le pseudonyme t.solravel_788. Le compte client est CLT-000209-Q, et la référence RH éventuelle est EMP-104053. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Solravel.

**Traitement du dossier.** Le 2025-01-26, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est architecte applicatif. Le compte rendu cite le proche Mélina Épilune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 684,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 73 05 99 209 841 00. La domiciliation bancaire fictive indique FR00 2119 5726 9749 1692 4051 578, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.248; la trace IPv6 associée est 2001:db8:d0::1930. Le poste de travail porte l’identifiant 12346448-17e4-4008-aa90-01234567a2db, le cookie de test est cookie-demo-00209-20176, et le gabarit biométrique est BIO-DEMO-011031 (référence vocale distincte : VOICE-TEST-00209). Le véhicule mentionné est ZZ-696-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Titouan Solravel et ajouté une note de suivi à CLT-000209-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2746; la référence du lot est BATCH-OPS-2026-581. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Titouan Solravel |
| Date | 2000-09-05 |
| Contact | titouan.solravel14@example.invalid |
| Client | CLT-000209-Q |
| Incident | INC-2026-08545 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2746 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une pratique déclarée de la tradition fictive des Aurores appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 210 : Juridique / contrat | dossier fictif INC-2026-08586

**Contexte.** Le service juridique relit un projet de courrier et consigne les faits rapportés dans un scénario inventé. Les noms, références de pièces et adresses sont fictifs. Les annotations permettent de tester les systèmes capables de repérer les identifiants présents dans les en-têtes, les citations et les paragraphes narratifs.

**Identité et coordonnées.** La personne concernée se nomme Inès Avelroche, née le 1964-02-18. Le dossier la rattache à 134, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France. Son email est ines.avelroche15@example.invalid et son téléphone est 06 39 98 77 44; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 77 44. La fiche de contact porte le pseudonyme i.avelroche_811. Le compte client est CLT-000210-Q, et la référence RH éventuelle est EMP-104072. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Avelroche.

**Traitement du dossier.** Le 2026-04-06, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est infirmier coordinateur. Le compte rendu cite le proche Bastien Florilacier, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 2 857,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 74 06 99 210 978 00. La domiciliation bancaire fictive indique FR00 2220 5839 9876 1823 4188 717, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.12; la trace IPv6 associée est 2001:db8:d1::194f. Le poste de travail porte l’identifiant 12346459-17eb-4009-aa9d-01234567a2fa, le cookie de test est cookie-demo-00210-20273, et le gabarit biométrique est BIO-DEMO-011084 (référence vocale distincte : VOICE-TEST-00210). Le véhicule mentionné est ZZ-733-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Inès Avelroche et ajouté une note de suivi à CLT-000210-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2759; la référence du lot est BATCH-OPS-2026-598. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Inès Avelroche |
| Date | 1964-02-18 |
| Contact | ines.avelroche15@example.invalid |
| Client | CLT-000210-Q |
| Incident | INC-2026-08586 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2759 |

**Autre formulation observée.** Version importée : Inès Avelroche; date=1964-02-18; rue=134, rue des Pivoines Grises, 99900 Clairval-sur-Lune, France; téléphone=06 39 98 77 44; courriel=ines.avelroche15@example.invalid; statut=à contrôler.


## Cas 211 : Support informatique | dossier fictif INC-2026-08627

**Contexte.** Le centre de support analyse un incident reproduit dans un environnement de test. Le ticket contient des coordonnées de contact, un identifiant de compte et quelques traces techniques. Les adresses IP ci-dessous appartiennent à des plages réservées à la documentation et ne décrivent aucun accès réel.

**Identité et coordonnées.** La personne concernée se nomme Mila Tremlombre, née le 1971-07-04. Le dossier la rattache à 151, rue des Brumes, 99900 Cendrelac, France. Son email est mila.tremlombre16@example.invalid et son téléphone est 06 39 98 77 81; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 77 81. La fiche de contact porte le pseudonyme m.tremlombre_834. Le compte client est CLT-000211-Q, et la référence RH éventuelle est EMP-104091. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Tremlombre.

**Traitement du dossier.** Le 2025-07-13, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est opératrice de saisie. Le compte rendu cite le proche Salomé Orielserein, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 030,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 75 07 99 211 115 00. La domiciliation bancaire fictive indique FR00 2321 5952 0003 1954 4325 856, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.29; la trace IPv6 associée est 2001:db8:d2::196e. Le poste de travail porte l’identifiant 1234646a-17f2-4000-aaaa-01234567a319, le cookie de test est cookie-demo-00211-20370, et le gabarit biométrique est BIO-DEMO-011137 (référence vocale distincte : VOICE-TEST-00211). Le véhicule mentionné est ZZ-770-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mila Tremlombre et ajouté une note de suivi à CLT-000211-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient mila TREMLOMBRE; vérifier que le changement de casse ne bloque pas la détection.

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 77 81. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2772; la référence du lot est BATCH-OPS-2026-615. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mila Tremlombre |
| Date | 1971-07-04 |
| Contact | mila.tremlombre16@example.invalid |
| Client | CLT-000211-Q |
| Incident | INC-2026-08627 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2772 |

**Autre formulation observée.** Le message reçu disait : « Pour Mila Tremlombre, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-08627. »


## Cas 212 : Voyage / réservation | dossier fictif INC-2026-08668

**Contexte.** Un conseiller reconstitue une réservation imaginaire et les demandes d’aménagement formulées par le voyageur. L’adresse, le téléphone, l’email et les informations de paiement sont synthétiques. Le texte mélange des phrases libres, des données de formulaire et une note de transmission.

**Identité et coordonnées.** La personne concernée se nomme Mélina Varnedorin, née le 1978-12-17. Le dossier la rattache à 168, allée des Sept Lanternes, 99900 Églan-sur-Roche, France. Son email est melina.varnedorin17@example.invalid et son téléphone est 06 39 98 78 18; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 78 18. La fiche de contact porte le pseudonyme m.varnedorin_857. Le compte client est CLT-000212-Q, et la référence RH éventuelle est EMP-104110. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Varnedorin.

**Traitement du dossier.** Le 2026-10-20, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est responsable de planification. Le compte rendu cite le proche Eliott Érablefarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 203,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 76 08 99 212 252 00. La domiciliation bancaire fictive indique FR00 2422 6065 0130 2085 4462 995, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.46; la trace IPv6 associée est 2001:db8:d3::198d. Le poste de travail porte l’identifiant 1234647b-17f9-4001-aab7-01234567a338, le cookie de test est cookie-demo-00212-20467, et le gabarit biométrique est BIO-DEMO-011190 (référence vocale distincte : VOICE-TEST-00212). Le véhicule mentionné est ZZ-807-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Mélina Varnedorin et ajouté une note de suivi à CLT-000212-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2785; la référence du lot est BATCH-OPS-2026-632. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Mélina Varnedorin |
| Date | 1978-12-17 |
| Contact | melina.varnedorin17@example.invalid |
| Client | CLT-000212-Q |
| Incident | INC-2026-08668 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2785 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Mélina Varnedorin, identifiant CLT-000212-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 213 : Marketing / consentement | dossier fictif INC-2026-08709

**Contexte.** Le service marketing vérifie les préférences de communication et les preuves de consentement d’un profil fictif. Les champs comprennent des données directement identifiantes, des pseudonymes et des éléments de contexte. Une préférence ou un historique rattaché à une personne reste à traiter comme une information la concernant.

**Identité et coordonnées.** La personne concernée se nomme Maël Célvaux, née le 1985-05-03. Le dossier la rattache à 5, rue des Nuages Bas, 99900 Montfleur-des-Aurores, France. Son email est mael.celvaux18@example.invalid et son téléphone est 06 39 98 78 55; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 78 55. La fiche de contact porte le pseudonyme m.célvaux_880. Le compte client est CLT-000213-Q, et la référence RH éventuelle est EMP-104129. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Célvaux.

**Traitement du dossier.** Le 2025-01-27, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est responsable qualité. Le compte rendu cite le proche Ariane Valnette, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 376,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est un gabarit biométrique de démonstration. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 77 09 99 213 389 00. La domiciliation bancaire fictive indique FR00 2523 6178 0257 2216 4599 134, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.63; la trace IPv6 associée est 2001:db8:d4::19ac. Le poste de travail porte l’identifiant 1234648c-1800-4002-aac4-01234567a357, le cookie de test est cookie-demo-00213-20564, et le gabarit biométrique est BIO-DEMO-011243 (référence vocale distincte : VOICE-TEST-00213). Le véhicule mentionné est ZZ-844-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Maël Célvaux et ajouté une note de suivi à CLT-000213-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2798; la référence du lot est BATCH-OPS-2026-649. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Maël Célvaux |
| Date | 1985-05-03 |
| Contact | mael.celvaux18@example.invalid |
| Client | CLT-000213-Q |
| Incident | INC-2026-08709 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2798 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Maël Célvaux, 06 39 98 78 55, mael.celvaux18@example.invalid; le rappel est prévu autour du 2025-01-27.”


## Cas 214 : Recherche / enquête | dossier fictif INC-2026-08750

**Contexte.** Ce compte rendu de recherche est synthétique. Le protocole associe un identifiant participant, un contexte de collecte et des notes rédigées par un opérateur. Les données indirectes peuvent devenir identifiantes lorsqu’elles sont croisées avec un métier rare, une date précise ou une petite localité fictive.

**Identité et coordonnées.** La personne concernée se nomme Célestin Seredorelle, née le 1992-10-16. Le dossier la rattache à 22, rue du Phare Éteint, 99900 Orée-du-Mistral, France. Son email est celestin.seredorelle19@example.invalid et son téléphone est 06 39 98 78 92; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 78 92. La fiche de contact porte le pseudonyme c.seredorelle_903. Le compte client est CLT-000214-Q, et la référence RH éventuelle est EMP-104148. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Seredorelle.

**Traitement du dossier.** Le 2026-04-07, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est responsable d’agence. Le compte rendu cite le proche Théo Mirasorel, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 549,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une adhésion simulée au Syndicat fictif des Verriers. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 78 10 99 214 526 00. La domiciliation bancaire fictive indique FR00 2624 6291 0384 2347 4736 273, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.80; la trace IPv6 associée est 2001:db8:d5::19cb. Le poste de travail porte l’identifiant 1234649d-1807-4003-aad1-01234567a376, le cookie de test est cookie-demo-00214-20661, et le gabarit biométrique est BIO-DEMO-011296 (référence vocale distincte : VOICE-TEST-00214). Le véhicule mentionné est ZZ-881-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Célestin Seredorelle et ajouté une note de suivi à CLT-000214-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2811; la référence du lot est BATCH-OPS-2026-666. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Célestin Seredorelle |
| Date | 1992-10-16 |
| Contact | celestin.seredorelle19@example.invalid |
| Client | CLT-000214-Q |
| Incident | INC-2026-08750 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2811 |

**Autre formulation observée.** Note d’audit : le lien entre c.seredorelle_903, 192.0.2.80 et 1234649d-1807-4003-aad1-01234567a376 doit être éliminé ou transformé de façon irréversible dans la sortie publique.


## Cas 215 : Logistique / livraison | dossier fictif INC-2026-08791

**Contexte.** Le service logistique examine une livraison simulée, le destinataire et la preuve de remise. La fiche contient une adresse, des coordonnées et des informations de suivi. Les références de produit et de lot génériques sont des contrôles négatifs : dans ce scénario, elles ne doivent pas être anonymisées.

**Identité et coordonnées.** La personne concernée se nomme Léandre Églanbelle, née le 1999-03-02. Le dossier la rattache à 39, rue des Pivoines Grises, 99900 Valmousse, France. Son email est leandre.eglanbelle20@example.invalid et son téléphone est 06 39 98 79 29; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 79 29. La fiche de contact porte le pseudonyme l.églanbelle_926. Le compte client est CLT-000215-Q, et la référence RH éventuelle est EMP-104167. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Églanbelle.

**Traitement du dossier.** Le 2025-07-14, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est technicienne support. Le compte rendu cite le proche Célestin Brumemarin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 722,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est une information fictive sur une aide sociale sollicitée. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 79 11 99 215 663 00. La domiciliation bancaire fictive indique FR00 2725 6404 0511 2478 4873 412, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 198.51.100.97; la trace IPv6 associée est 2001:db8:d6::19ea. Le poste de travail porte l’identifiant 123464ae-180e-4004-aade-01234567a395, le cookie de test est cookie-demo-00215-20758, et le gabarit biométrique est BIO-DEMO-011349 (référence vocale distincte : VOICE-TEST-00215). Le véhicule mentionné est ZZ-918-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Léandre Églanbelle et ajouté une note de suivi à CLT-000215-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2824; la référence du lot est BATCH-OPS-2026-683. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Léandre Églanbelle |
| Date | 1999-03-02 |
| Contact | leandre.eglanbelle20@example.invalid |
| Client | CLT-000215-Q |
| Incident | INC-2026-08791 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2824 |

**Autre formulation observée.** Le responsable de Éditions du Renard Blanc confirme que la mention une information fictive sur une aide sociale sollicitée appartient au scénario fictif et ne décrit aucune personne réelle.


## Cas 216 : Sécurité / contrôle d’accès | dossier fictif INC-2026-08832

**Contexte.** L’équipe sécurité examine un incident fictif impliquant un compte applicatif et un terminal de démonstration. Les traces utilisent des identifiants synthétiques. Le texte contient aussi un témoignage et un signalement non vérifié ; il faut distinguer la donnée personnelle du simple identifiant technique non rattaché à une personne.

**Identité et coordonnées.** La personne concernée se nomme Nora Rivbrume, née le 1963-08-15. Le dossier la rattache à 56, rue des Brumes, 99900 Virelune-les-Pins, France. Son email est nora.rivbrume21@example.invalid et son téléphone est 06 39 98 79 66; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 79 66. La fiche de contact porte le pseudonyme n.rivbrume_949. Le compte client est CLT-000216-Q, et la référence RH éventuelle est EMP-104186. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Rivbrume.

**Traitement du dossier.** Le 2026-10-21, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est enseignante remplaçante. Le compte rendu cite le proche Ilyan Mélidune, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 3 895,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un suivi fictif pour migraine chronique. Dans ce scénario, la donnée sensible supplémentaire est une mention de plainte fictive dans le scénario juridique. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 80 12 99 216 800 00. La domiciliation bancaire fictive indique FR00 2826 6517 0638 2609 5010 551, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 203.0.113.114; la trace IPv6 associée est 2001:db8:d7::1a09. Le poste de travail porte l’identifiant 123464bf-1815-4005-aaeb-01234567a3b4, le cookie de test est cookie-demo-00216-20855, et le gabarit biométrique est BIO-DEMO-011402 (référence vocale distincte : VOICE-TEST-00216). Le véhicule mentionné est ZZ-955-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Nora Rivbrume et ajouté une note de suivi à CLT-000216-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Variante bruitée.** Dans une exportation en minuscules/majuscules, le champ source contient nora RIVBRUME; vérifier que le changement de casse ne bloque pas la détection.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2837; la référence du lot est BATCH-OPS-2026-700. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Nora Rivbrume |
| Date | 1963-08-15 |
| Contact | nora.rivbrume21@example.invalid |
| Client | CLT-000216-Q |
| Incident | INC-2026-08832 |
| Détail sensible | un suivi fictif pour migraine chronique |
| Référence catalogue non personnelle | SKU-ALPHA-2837 |

**Autre formulation observée.** Version importée : Nora Rivbrume; date=1963-08-15; rue=56, rue des Brumes, 99900 Virelune-les-Pins, France; téléphone=06 39 98 79 66; courriel=nora.rivbrume21@example.invalid; statut=à contrôler.


## Cas 217 : RH / gestion du personnel | dossier fictif INC-2026-08873

**Contexte.** Le service RH ouvre une fiche de suivi et vérifie les pièces liées au contrat, au planning et aux absences. La personne a demandé que les échanges restent limités aux équipes habilitées. Le responsable précise que les commentaires libres ne doivent pas être recopiés dans les exports destinés aux tableaux de bord.

**Identité et coordonnées.** La personne concernée se nomme Anaïs Alouloriot, née le 2010-01-01. Le dossier la rattache à 73, allée des Sept Lanternes, 99900 Lisière-des-Lucioles, France. Son email est anais.alouloriot22@example.invalid et son téléphone est 06 39 98 80 03; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 80 03. La fiche de contact porte le pseudonyme a.alouloriot_972. Le compte client est CLT-000217-Q, et la référence RH éventuelle est EMP-104205. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Alouloriot.

**Traitement du dossier.** Le 2025-01-01, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est médiatrice sociale. Le compte rendu cite le proche Lucile Vanisac, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 068,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une limitation de mobilité temporaire. Dans ce scénario, la donnée sensible supplémentaire est une pratique déclarée de la tradition fictive des Aurores. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 81 01 99 217 937 00. La domiciliation bancaire fictive indique FR00 2927 6630 0765 2740 5147 690, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 192.0.2.131; la trace IPv6 associée est 2001:db8:d8::1a28. Le poste de travail porte l’identifiant 123464d0-181c-4006-aaf8-01234567a3d3, le cookie de test est cookie-demo-00217-20952, et le gabarit biométrique est BIO-DEMO-011455 (référence vocale distincte : VOICE-TEST-00217). Le véhicule mentionné est ZZ-992-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Anaïs Alouloriot et ajouté une note de suivi à CLT-000217-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte mineur.** Le cas concerne une personne mineure, signalée par la date de naissance 2010-01-01. Le proche de référence est Lucile Vanisac. Les échanges scolaires, médicaux et familiaux doivent être considérés comme particulièrement sensibles dans ce scénario.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2850; la référence du lot est BATCH-OPS-2026-717. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Anaïs Alouloriot |
| Date | 2010-01-01 |
| Contact | anais.alouloriot22@example.invalid |
| Client | CLT-000217-Q |
| Incident | INC-2026-08873 |
| Détail sensible | une limitation de mobilité temporaire |
| Référence catalogue non personnelle | SKU-ALPHA-2850 |

**Autre formulation observée.** Le message reçu disait : « Pour Anaïs Alouloriot, merci de confirmer les coordonnées avant la clôture du ticket INC-2026-08873. »


## Cas 218 : CRM / relation client | dossier fictif INC-2026-08914

**Contexte.** Le service relation client reconstitue l’historique des échanges, la préférence de contact et les demandes en cours. Une note libre a été rédigée après un appel et contient plusieurs éléments d’identité. La fiche sera transmise à l’équipe de résolution, puis archivée selon les règles internes de conservation fictives.

**Identité et coordonnées.** La personne concernée se nomme Jade Belaubier, née le 1977-06-14. Le dossier la rattache à 90, rue des Nuages Bas, 99900 Noroît-les-Jardins, France. Son email est jade.belaubier23@example.invalid et son téléphone est 06 39 98 80 40; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 80 40. La fiche de contact porte le pseudonyme j.belaubier_995. Le compte client est CLT-000218-Q, et la référence RH éventuelle est EMP-104224. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Belaubier.

**Traitement du dossier.** Le 2026-04-08, le service de Éditions du Renard Blanc a reçu une demande liée à la personne, dont le métier déclaré est chargé de clientèle. Le compte rendu cite le proche Gabin Aurimousse, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 241,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne un contrôle périodique de la tension. Dans ce scénario, la donnée sensible supplémentaire est une demande fictive d’aménagement lié à un handicap. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 82 02 99 218 074 00. La domiciliation bancaire fictive indique FR00 3028 6743 0892 2871 5284 829, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 198.51.100.148; la trace IPv6 associée est 2001:db8:d9::1a47. Le poste de travail porte l’identifiant 123464e1-1823-4007-ab05-01234567a3f2, le cookie de test est cookie-demo-00218-21049, et le gabarit biométrique est BIO-DEMO-011508 (référence vocale distincte : VOICE-TEST-00218). Le véhicule mentionné est ZZ-029-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Jade Belaubier et ajouté une note de suivi à CLT-000218-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Fragment à risque.** Une note tronquée ne conserve que la fin du numéro : 80 40. Cette forme partielle peut contribuer à une ré-identification lorsqu’elle est croisée avec d’autres éléments.

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2863; la référence du lot est BATCH-OPS-2026-734. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Jade Belaubier |
| Date | 1977-06-14 |
| Contact | jade.belaubier23@example.invalid |
| Client | CLT-000218-Q |
| Incident | INC-2026-08914 |
| Détail sensible | un contrôle périodique de la tension |
| Référence catalogue non personnelle | SKU-ALPHA-2863 |

**Autre formulation observée.** Note opérateur : identité indiquée comme Jade Belaubier, identifiant CLT-000218-Q; conserver les pièces uniquement dans le dossier protégé.


## Cas 219 : Santé / prise de rendez-vous | dossier fictif INC-2026-08955

**Contexte.** Le secrétariat prépare un dossier de rendez-vous de démonstration. Les informations de santé présentes ci-dessous sont entièrement inventées et servent à vérifier que les données sensibles sont détectées dans le texte libre autant que dans les champs structurés. Le professionnel fictif ne doit recevoir que les éléments nécessaires à la prise en charge.

**Identité et coordonnées.** La personne concernée se nomme Bastien Fauvevalon, née le 1984-11-27. Le dossier la rattache à 107, rue du Phare Éteint, 99900 Nacréville, France. Son email est bastien.fauvevalon24@example.invalid et son téléphone est 06 39 98 80 77; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 80 77. La fiche de contact porte le pseudonyme b.fauvevalon_019. Le compte client est CLT-000219-Q, et la référence RH éventuelle est EMP-104243. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Fauvevalon.

**Traitement du dossier.** Le 2025-07-15, le service de Institut des Cartographes a reçu une demande liée à la personne, dont le métier déclaré est conducteur-livreur. Le compte rendu cite le proche Lina Montaroussin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 414,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une audition réduite mentionnée dans le scénario. Dans ce scénario, la donnée sensible supplémentaire est une information fictive concernant son orientation sexuelle. Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 1 83 03 99 219 211 00. La domiciliation bancaire fictive indique FR00 3129 6856 1019 3002 5421 968, et le paiement de test utilise 4242 4242 4242 4242. L’adresse IPv4 observée dans le journal est 203.0.113.165; la trace IPv6 associée est 2001:db8:da::1a66. Le poste de travail porte l’identifiant 123464f2-182a-4008-ab12-01234567a411, le cookie de test est cookie-demo-00219-21146, et le gabarit biométrique est BIO-DEMO-011561 (référence vocale distincte : VOICE-TEST-00219). Le véhicule mentionné est ZZ-066-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Bastien Fauvevalon et ajouté une note de suivi à CLT-000219-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2876; la référence du lot est BATCH-OPS-2026-751. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Bastien Fauvevalon |
| Date | 1984-11-27 |
| Contact | bastien.fauvevalon24@example.invalid |
| Client | CLT-000219-Q |
| Incident | INC-2026-08955 |
| Détail sensible | une audition réduite mentionnée dans le scénario |
| Référence catalogue non personnelle | SKU-ALPHA-2876 |

**Autre formulation observée.** Compte rendu vocal transcrit : “Bastien Fauvevalon, 06 39 98 80 77, bastien.fauvevalon24@example.invalid; le rappel est prévu autour du 2025-07-15.”


## Cas 220 : Banque / assurance | dossier fictif INC-2026-08996

**Contexte.** Le gestionnaire traite une demande de remboursement fictive et rapproche les justificatifs, la référence de dossier et le moyen de paiement de test. Les valeurs financières ont été fabriquées pour cet exercice. Le compte rendu doit protéger l’identité, les coordonnées et tout identifiant pouvant être relié à la personne.

**Identité et coordonnées.** La personne concernée se nomme Malo Dorémeline, née le 1991-04-13. Le dossier la rattache à 124, rue des Pivoines Grises, 99900 Brumeval, France. Son email est malo.doremeline25@example.invalid et son téléphone est 06 39 98 81 14; la même coordonnée peut aussi apparaître sous la forme internationale +33 6 39 98 81 14. La fiche de contact porte le pseudonyme m.dorémeline_042. Le compte client est CLT-000220-Q, et la référence RH éventuelle est EMP-104262. Le texte a aussi été copié dans une note où le nom apparaît sous la forme Mme/M. Dorémeline.

**Traitement du dossier.** Le 2026-10-22, le service de Groupe Nacréon a reçu une demande liée à la personne, dont le métier déclaré est chef de projet. Le compte rendu cite le proche Titouan Nivvardin, avec lequel il faut organiser un échange distinct. Une ligne de rémunération fictive indique 4 587,00 €; cette valeur ne doit pas être confondue avec le total d’une facture générique. Le motif mentionne une absence liée à une opération inventée. Dans ce scénario, la donnée sensible supplémentaire est un soutien déclaré à la liste imaginaire « Horizon 9 ». Le responsable doit limiter les destinataires du compte rendu au strict nécessaire.

**Identifiants et traces.** Le numéro national de démonstration est 2 84 04 99 220 348 00. La domiciliation bancaire fictive indique FR00 3230 6969 1146 3133 5558 107, et le paiement de test utilise 4000 0000 0000 0002. L’adresse IPv4 observée dans le journal est 192.0.2.182; la trace IPv6 associée est 2001:db8:db::1a85. Le poste de travail porte l’identifiant 12346503-1831-4009-ab1f-01234567a430, le cookie de test est cookie-demo-00220-21243, et le gabarit biométrique est BIO-DEMO-011614 (référence vocale distincte : VOICE-TEST-00220). Le véhicule mentionné est ZZ-103-ZZ. Aucun de ces éléments n’est relié à une infrastructure réelle.

**Résumé libre du conseiller.** « J’ai vérifié la demande de Malo Dorémeline et ajouté une note de suivi à CLT-000220-Q. La personne préfère être jointe par écrit en fin de journée, sauf urgence signalée par l’équipe habilitée. Le dossier doit rester cohérent entre le CRM et l’outil de support, mais la copie destinée au reporting doit être anonymisée. Le conseiller indique que le sujet de l’appel ne doit pas être repris dans les exports publics. »

**Contexte complémentaire.** La combinaison de la profession, de la localité, de la date et de l’organisation peut suffire à distinguer un dossier, même si le nom est supprimé. Ce point vise les tests de pseudonymisation et de réduction des quasi-identifiants.

**Contrôles négatifs à conserver.** Le produit traité est SKU-ALPHA-2889; la référence du lot est BATCH-OPS-2026-768. Pour une question générale, l’équipe utilise la boîte partagée support@atelier-exemple.invalid. Le fournisseur de logiciel fictif est Atelier Exemple Fonctionnel SAS. Ces quatre éléments sont non personnels dans ce contexte pédagogique et servent à mesurer les sur-anonymisations.

**Extrait de formulaire.**

| Champ | Valeur de test |
|---|---|
| Personne | Malo Dorémeline |
| Date | 1991-04-13 |
| Contact | malo.doremeline25@example.invalid |
| Client | CLT-000220-Q |
| Incident | INC-2026-08996 |
| Détail sensible | une absence liée à une opération inventée |
| Référence catalogue non personnelle | SKU-ALPHA-2889 |

**Autre formulation observée.** Note d’audit : le lien entre m.dorémeline_042, 192.0.2.182 et 12346503-1831-4009-ab1f-01234567a430 doit être éliminé ou transformé de façon irréversible dans la sortie publique.

