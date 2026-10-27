# Guide d’évaluation du corpus d’anonymisation

## Fichiers

- `corpus_anonymisation_rgpd_fictif.md` : corpus à transmettre au système testé.
- `gold_standard_mentions.csv` : vérité terrain des mentions à masquer. Ne pas la donner au système testé.
- `gold_standard_safe_controls.csv` : mentions non personnelles à préserver dans le contexte décrit. Ne pas la donner au système testé.
- `evaluate_anonymisation.py` : script d’évaluation de sortie.

## Taille et annotation

- Dossiers : 220
- Mots estimés dans le corpus : 129,475
- Lignes Markdown : 6,993
- Mentions annotées à protéger : 8,705
- Contrôles négatifs à préserver : 1,100

## Métriques

1. **Protection des mentions de référence** : 1 − (mentions de référence encore reconnaissables / mentions de référence totales). C’est un rappel de masquage par occurrence, pas une garantie juridique d’anonymisation.
2. **Conservation des contrôles négatifs** : proportion des valeurs volontairement non personnelles encore présentes dans la sortie.
3. **Sur-anonymisation sur contrôles négatifs** : 1 − conservation des contrôles négatifs.
4. **Score équilibré** : moyenne harmonique de la protection des mentions et de la conservation des contrôles. Il pénalise les systèmes qui protègent mal les données ou qui effacent excessivement le contexte.

## Lancer le test

Placez la sortie de votre système, idéalement en conservant la structure du Markdown, dans `sortie_anonymisee.md`, puis lancez :

```bash
python evaluate_anonymisation.py sortie_anonymisee.md
```

Les chemins des fichiers de référence peuvent être remplacés avec `--original`, `--pii` et `--safe`.

## Conseils pour comparer plusieurs versions

- Conservez la même version du corpus et les mêmes paramètres du système.
- Calculez les scores globaux, puis comparez les catégories en particulier les identifiants nationaux, les données sensibles, les variantes de casse et les fragments de téléphone.
- Vérifiez manuellement les sorties qui ont un score élevé : la présence d’un nom supprimé ne garantit pas qu’un dossier ne soit plus ré-identifiable par date + profession + lieu + organisation.
- Évitez de mettre les fichiers `gold_standard_*.csv` dans le prompt ou dans le répertoire accessible à l’anonymiseur pendant le test.

## Limites

Le script compte les valeurs de référence qui restent reconnaissables sur une même ligne et protège contre les changements courants de casse, d’accents, d’espaces ou de séparateurs pour les identifiants. Il suppose que la sortie conserve globalement le texte et les lignes. Une reformulation complète du document peut réduire la fiabilité du comptage. Le score ne remplace ni une revue des faux négatifs non annotés, ni une analyse des possibilités de recoupement, ni une validation juridique.

## Conventions de sécurité des données de test

Les noms, adresses, dates de naissance, identifiants de compte, références de dossier et informations sensibles ont été inventés. Les adresses IPv4 utilisent les réseaux de documentation `192.0.2.0/24`, `198.51.100.0/24` ou `203.0.113.0/24`, et les adresses IPv6 utilisent `2001:db8::/32`. Les numéros de téléphone utilisent la racine `06 39 98`, réservée en France aux œuvres audiovisuelles. Les NIR et IBAN sont délibérément invalides ; les données de carte sont des PAN de test.
