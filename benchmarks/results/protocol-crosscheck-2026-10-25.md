# Contrôle croisé de l'outil du protocole / protocol tool cross-check — 2026-10-25

> **Remplacé par / superseded by [`protocol-crosscheck-2026-10-26.md`](protocol-crosscheck-2026-10-26.md).** Ce
> fichier décrit le moteur d'avant les règles « rules2 » ; sa partie 2 a chargé une copie du moteur prise pendant une
> retouche (2 documents en échec des deux côtés). Gardé pour l'historique. This file describes the engine before the
> "rules2" rules; its part 2 loaded a copy of the engine taken mid-edit (2 documents failed on both sides). Kept for
> the record.

L'évaluation synthétique de développement (540 documents, graine 20261024, et 6 192 documents mutés par 51 opérateurs) passe par un service local en mode public avec jeton local (socket Unix), via `tools/protocol` ; les zones masquées sont reconstruites depuis la seule sortie, puis notées par `tools.eval` (`score_document`, `summarize`). The development synthetic evaluation sent through a local service in public mode with a local token, zones rebuilt from the output alone, scored by `tools.eval`. Scores only.

## 1. Service contre le fichier de référence / service vs the reference file

Service démarré avec le moteur du 25 octobre (noyau natif) ; référence `benchmarks/results/eval-2026-10-25-standard.json` (pays `auto`). Service started with the 25 October engine.

| Indicateur / indicator | Service | Référence / reference |
|---|---|---|
| recall_direct | 99.18 % | 99.18 % |
| recall_structured | 98.83 % | 98.83 % |
| recall | 93.48 % | 93.48 % |
| precision | 98.82 % | 98.82 % |
| f2 | 94.50 % | 94.50 % |
| entity_recall_direct | 98.70 % | 98.70 % |
| doc_leak_rate | 9.07 % | 9.07 % |
| doc_leak_rate_structured | 4.63 % | 4.63 % |
| over_masking | 0.08 % | 0.08 % |
| decoy_false_mask_rate | 3.46 % | 3.46 % |

Les dix indicateurs sont identiques au bit près / the ten indicators are bit-identical: True.

- Corpus `base` : 21 feuilles différentes sur 773 / 21 of 773 leaves differ: `ci95` 9 (interval bounds: bootstrap random draws differ (numpy for the reference file on Windows, the pure-Python fallback of tools.eval.metrics in WSL); point values identical); `confusion` 6 (per system label: the boundary between two placeholders separated only by spaces cannot be recovered from the output (leftmost placement used); what is masked does not depend on it); `labels` 3 (per system label (precision, F2, IoU>=90%, typed rate, strict recall): same boundary effect); `system_labels` 3 (characters attributed to each system label: same boundary effect)
- Corpus `mutated` : 30 feuilles différentes sur 8535 / 30 of 8535 leaves differ: `confusion` 15 (per system label: the boundary between two placeholders separated only by spaces cannot be recovered from the output (leftmost placement used); what is masked does not depend on it); `entities` 3 (strict entity rate only (requires the spaces between words to be covered too): same boundary effect); `labels` 7 (per system label (precision, F2, IoU>=90%, typed rate, strict recall): same boundary effect); `system_labels` 5 (characters attributed to each system label: same boundary effect)

Pays `FR` contre `eval-2026-10-25-standard-fr.json` : indicateurs identiques True ; différences `base` {'ci95': 9, 'confusion': 6, 'labels': 3, 'system_labels': 3}, `mutated` {'confusion': 15, 'entities': 3, 'labels': 7, 'system_labels': 5}.

## 2. Même moteur, même instant / same engine, same moment

Service et évaluation en processus chargent la même copie figée du moteur (moteur Python : le contrat natif de la copie ne correspondait plus au noyau installé). Both load one frozen copy of the engine.

| Indicateur / indicator | Service | En processus / in process |
|---|---|---|
| recall_direct | 99.13 % | 99.13 % |
| recall_structured | 98.83 % | 98.83 % |
| recall | 93.42 % | 93.42 % |
| precision | 98.39 % | 98.39 % |
| f2 | 94.37 % | 94.37 % |
| entity_recall_direct | 98.70 % | 98.70 % |
| doc_leak_rate | 9.09 % | 9.09 % |
| doc_leak_rate_structured | 4.64 % | 4.64 % |
| over_masking | 0.08 % | 0.08 % |
| decoy_false_mask_rate | 4.49 % | 4.49 % |

Identiques / identical: True.

- Pays `auto`, corpus `base` : 15/778 feuilles : `confusion` 7; `errors` 2; `labels` 3; `system_labels` 3
- Pays `auto`, corpus `mutated` : 27/8537 feuilles : `confusion` 12; `entities` 2; `errors` 2; `labels` 6; `system_labels` 5
- Pays `FR`, corpus `base` : 15/778 feuilles : `confusion` 7; `errors` 2; `labels` 3; `system_labels` 3
- Pays `FR`, corpus `mutated` : 27/8537 feuilles : `confusion` 12; `entities` 2; `errors` 2; `labels` 6; `system_labels` 5

## Explication de chaque différence / every difference explained

- `ci95` : interval bounds: bootstrap random draws differ (numpy for the reference file on Windows, the pure-Python fallback of tools.eval.metrics in WSL); point values identical
- `confusion` : per system label: the boundary between two placeholders separated only by spaces cannot be recovered from the output (leftmost placement used); what is masked does not depend on it
- `labels` : per system label (precision, F2, IoU>=90%, typed rate, strict recall): same boundary effect
- `system_labels` : characters attributed to each system label: same boundary effect
- `entities` : strict entity rate only (requires the spaces between words to be covered too): same boundary effect
- `errors` : error type names: the service answers HTTP 500 (named DocumentRefused by the tool), the in-process run names the Python exception (NameError) of the frozen mid-edit engine; same documents excluded on both sides

Aucune différence inexpliquée / no unexplained difference: True.
