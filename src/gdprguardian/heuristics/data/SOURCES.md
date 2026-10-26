# Données des heuristiques : sources, licences, attribution

Fichiers produits par `tools/build_gazetteers.py` (bibliothèque standard seule), figés et versionnés.
Aucun téléchargement à l'exécution. Empreintes SHA-256 des fichiers sources et date de construction :
`sources.json`. Pour reconstruire : `python -I tools/build_gazetteers.py --cache <dossier hors du dépôt>`.

Ces fichiers ne contiennent que des **agrégats** (rangs de fréquence) et des listes de mots ou de lieux :
aucune donnée individuelle, aucun enregistrement d'état civil.

## Attribution

- **Source : Insee**, *Fichier des prénoms*, édition 2025 (naissances 1900-2025, publié le 16/07/2026).
  https://www.insee.fr/fr/statistiques/8595130
- **Source : Insee**, *Fichier des noms de famille*, édition 2008 (naissances 1891-2000, publié le 22/05/2018).
  https://www.insee.fr/fr/statistiques/3536630
- **Source : Insee**, *Code officiel géographique* au 1er janvier 2026 (communes, départements, régions,
  arrondissements, pays et territoires). https://www.insee.fr/fr/information/8740222
- **Source : La Poste**, *Base officielle des codes postaux* (mise à jour du 08/09/2026).
  https://www.data.gouv.fr/datasets/base-officielle-des-codes-postaux
- **Wikidata**, lexèmes français et anglais (formes), extraits le 24/10/2026. https://www.wikidata.org

## Licences

| Source | Licence | Vérification |
|---|---|---|
| Insee (prénoms, noms, COG) | Licence Ouverte / Open Licence 2.0 (Etalab) : réutilisation libre, y compris commerciale, en mentionnant « Source : Insee » et la date de dernière mise à jour | mentions légales https://www.insee.fr/fr/information/2008466, lues le 24/10/2026 |
| La Poste (codes postaux) | Licence Ouverte 2.0 (`lov2`) | API data.gouv.fr, champ `license`, lu le 24/10/2026 |
| Wikidata (lexèmes) | CC0 1.0 | https://www.wikidata.org/wiki/Wikidata:Licensing, lu le 24/10/2026 |

Les listes manuelles du script (mois, fêtes, lieux connus, marques, mots anglais, prénoms européens,
civilités, types de voie, formes juridiques) sont des faits linguistiques rédigés pour ce projet, sous la
licence MIT du dépôt. Aucune donnée ODbL (OSM, BANO), CC BY-SA (Wiktionnaire, Lexique), LGPL ou GPL.

## Transformations (sans altération du sens)

- Repliement identique à l'exécution (`gdprguardian._text.fold`) : minuscules, sans accents, longueur conservée.
- `names.tsv.gz` : prénoms donnés au moins 20 fois depuis 1900 et noms portés par au moins 256 personnes
  (en dessous, un nom se comporte comme un mot inconnu : il n'est masqué qu'à côté d'un prénom, après une
  civilité ou par propagation). Colonnes : jeton, rang du prénom (log2 des naissances ; `c` = liste
  manuelle de prénoms européens absents du fichier Insee), sexe (M, F ou X si moins de 90 % d'un sexe),
  rang du nom, ambiguïté (`w` mot courant, `s` mot très courant, `e` lieu, mois, fête ou marque).
- `words.txt.gz` : mots courants qui ne sont pas des noms (formes des lexèmes, hors verbes et noms propres).
- `postal.tsv.gz` : code postal -> communes, libellés d'acheminement, lignes 5 et noms du COG, en clés
  normalisées (ponctuation -> espace, « saint » -> « st »). Le fichier La Poste est encodé en CP1252.
- À l'exécution, deux listes manuelles de `_vocab.py` complètent ces fichiers : `EXTRA_WORDS` (mots courants
  absents des lexèmes Wikidata : « facture », « paie »…) et `VERB_FORMS` (formes verbales qui sont aussi des
  noms de famille : « Rendu », « Donne »… ; elles deviennent des mots ambigus).

---

# Heuristics data: sources, licences, attribution

Built by `tools/build_gazetteers.py` (stdlib only), frozen and committed; nothing is downloaded at runtime.
SHA-256 digests of every source file and the build date are in `sources.json`. The files hold only
aggregates (frequency ranks) and word or place lists: no individual record.

At runtime, two hand-written lists in `_vocab.py` amend these files: `EXTRA_WORDS` (common words missing from
the Wikidata lexemes) and `VERB_FORMS` (verb forms that are also surnames, downgraded to ambiguous words).

Attribution: "Source : Insee" (Fichier des prénoms 2025, Fichier des noms 2008, COG 2026),
"Source : La Poste" (Base officielle des codes postaux), Wikidata lexemes (CC0). Insee and La Poste data are
under Licence Ouverte 2.0 (free reuse, attribution and last-update date required); Wikidata under CC0.
