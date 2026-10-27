# Pack d'audit v1 / audit pack v1

Corpus synthétique d'évaluation de l'anonymisation RGPD, avec sa vérité terrain complète et son script
d'évaluation. C'est le pack qui a servi à l'audit du 26/10/2026 (moteur 1.0.1 : 45,71 % de protection). Il a été remis au
projet par son responsable, qui en autorise tout usage. Toutes les données sont inventées (domaines `example.invalid`,
IP de documentation, téléphones en `06 39 98`, NIR et IBAN invalides, cartes de test).
Synthetic GDPR anonymisation test pack with its full gold standard and evaluator, used for the 2026-10-26 audit
(engine 1.0.1: 45.71 % protection). Given to the project by its owner, free to use. Every value is invented.

Les six fichiers sont reproduits sans modification ; ne pas les éditer, pour que les scores restent comparables.
Une version améliorée sera publiée à part (`pack-v2`). / The six files are kept unchanged so scores stay
comparable; an improved version will live next to it (`pack-v2`).

| Fichier / file | Rôle / role | SHA-256 |
|---|---|---|
| `corpus_anonymisation_rgpd_fictif.md` | corpus à anonymiser (220 dossiers) / corpus | `913658e2713996aafc4157b838e3ff03aac9d7c5cf5d0ae7750c90236bdffc78` |
| `gold_standard_mentions.csv` | 8 705 mentions à masquer / mentions to mask | `55b58db843aea536da3e02b8547f5c7222a54264165dd4c2bb6c4f6c6485ef9d` |
| `gold_standard_safe_controls.csv` | 1 100 contrôles à préserver / controls to keep | `11ba669e92366f0b5c6b376e4503fac3cc90708eb9edd25a4f36cb1400d6303e` |
| `evaluate_anonymisation.py` | évaluateur / evaluator | `76b1dd8761bb7592bb52d868356b45e0eb144734240d170c333b386938d5fd10` |
| `guide_evaluation_anonymisation.md` | guide | `7af3beb6e02a795cf6b1352815aa68ff99a83d2ba20c9bab8fff4ea2ac58b3e8` |
| `corpus_manifest.json` | manifeste / manifest | `f33a3d980bc3a943b84f9c85636c3a5760c9fc5b10f413b9098bfb0e5d1e674d` |

## Lancer / run

```bash
python -c "import gdprguardian, pathlib; p = pathlib.Path('datasets/audit/pack-v1'); pathlib.Path('sortie.md').write_text(gdprguardian.anonymize((p / 'corpus_anonymisation_rgpd_fictif.md').read_text(encoding='utf-8')).text, encoding='utf-8')"
python datasets/audit/pack-v1/evaluate_anonymisation.py sortie.md
```

## Ce que mesure le pack, et ce que le moteur traite / what the pack measures vs the engine's scope

Le pack compte comme « à masquer » trois familles que le produit traite différemment :
- **identifiants directs** (noms, coordonnées, numéros, codes, IP, dates de naissance…) : le travail du moteur ;
- **quasi-identifiants** (profession, rémunération, dates d'événement, employeur) : laissés lisibles par le moteur ;
  le recoupement reste à apprécier au cas par cas ;
- **données art. 9 et 10** (santé, religion, opinions, syndicat, orientation, justice, situation sociale) : seconde passe
  des skills, par le modèle de l'IA de l'utilisateur.

Ses contrôles négatifs (références produit et lot, boîte fonctionnelle) sont masqués par le filtre fort par défaut, qui
masque tout code ; une organisation les garde avec des règles `keep` ou la liste `allow`, ou en désactivant la catégorie.
The pack counts three families as "to mask": direct identifiers (the engine's job), quasi-identifiers (left readable by
the engine) and art. 9/10 data (the skills' second pass). Its negative controls are masked by the default strong
filter; organisations keep them with keep rules, the allow list, or by disabling the category.

## Limites de l'évaluateur / evaluator limits

Il compte une mention comme protégée dès que la chaîne entière a disparu de la ligne : un prénom laissé à côté d'un nom
masqué, ou « 99900 Ville » laissé après une rue masquée, ne comptent pas comme fuites. Le comptage strict du projet
s'ajoute à ses métriques. / A mention counts as protected once the whole string is gone; partial leaks are invisible,
so the project adds a stricter count next to the official metrics.
