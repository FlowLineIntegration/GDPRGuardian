# Pack d'audit v1 — moteur 1.0.1 (26/10/2026) / audit pack v1 — engine 1.0.1

Corpus : `datasets/audit/pack-v1` (220 dossiers synthétiques, 8 705 mentions, 1 100 contrôles). Corpus entier en un
appel, réglages par défaut. Évaluateur du pack, sans modification. / Whole corpus in one call, default settings, the
pack's own evaluator.

| Mesure / metric | Défaut / default | Avec règles keep + allow |
|---|---:|---:|
| Protection des mentions (officielle) | 45,71 % | 45,71 % |
| Contrôles conservés | 80,00 % | 100,00 % |
| Score équilibré | 58,18 % | 62,74 % |

Les mêmes fuites, regroupées selon le périmètre du produit / the same leaks grouped by product scope:

| Périmètre / scope | Mentions | En clair / left | Protection |
|---|---:|---:|---:|
| Identifiants directs (moteur) | 7 092 | 3 113 | 56,11 % |
| Quasi-identifiants (lisibles par conception) | 953 | 953 | 0 % |
| Art. 9 et 10 (seconde passe des skills) | 660 | 660 | 0 % |

Fuites du périmètre moteur, par catégorie / engine-scope leaks by category: codes client 697/697, références de
dossier 477/477, pseudonymes 257/257, UUID 257/257, gabarits biométriques 256/256, dates de naissance 256/501, IPv6
220/220, cookies 220/220, identifiants biométriques 220/220, identifiants salarié 220/220, fragments de téléphone 32/32,
plaque 1/220. À 100 % : noms et prénoms, proches, variantes de casse, courriels, téléphones, NIR, IBAN, cartes, IPv4,
adresses.

Comptage strict du projet (en plus) / project's strict count: 60,92 % des 8 614 occurrences d'identifiants directs ;
44 prénoms en minuscules restent devant un nom masqué et 245 « code postal + ville » restent après une rue masquée,
deux fuites que l'évaluateur officiel ne voit pas. Détail : `audit-pack-v1-engine-1.0.1-keep-2026-10-26.json`.
