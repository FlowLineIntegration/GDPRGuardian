# Contrôle croisé de l'outil du protocole / protocol tool cross-check — 2026-10-26

L'évaluation synthétique de développement (540 documents, graine 20261024, et leurs mutations par les 51 opérateurs) passe par un service local en mode public avec jeton local (socket Unix), via `tools/protocol` ; les zones masquées sont reconstruites depuis la seule sortie, notées par `tools.eval`, puis comparées feuille à feuille avec l'évaluation en processus du même moteur et avec le fichier de référence du dépôt. Scores seulement. The synthetic development evaluation (540 documents, seed 20261024, and their mutations by the 51 red-team operators) sent through a local GDPR Guardian service (public mode, local token, Unix socket) by tools/protocol, masked zones rebuilt from the output alone, scored with tools.eval (score_document, summarize) and compared leaf by leaf with the in-process evaluation of the same engine and with the repository's reference file.

Moteur contrôlé / engine checked: frozen copy of the engine sources taken at 00:04 UTC on 26 October 2026 (tree digest a992428d25533cc6), pure-Python engine (the installed native core did not run these sources; same outputs by the parity contract), version 1.0.0, packs 0e6be79d84cd, engine probe digest eeb38986e44c (the probe_sha256 a campaign records for an engine with the same outputs); the engine sources were still being tuned, so this check is repeated on the frozen engine before registration.

**Outil validé / tool validated: oui / yes** (même moteur : dix indicateurs identiques, aucun échec, tout autre écart est un effet de frontière / same engine: ten identical indicators, no failure, every other difference is a boundary effect).

## Pays / countries `auto` — 540 + 6192 documents

| Indicateur / indicator | Service | En processus / in process | Référence / reference |
|---|---|---|---|
| recall_direct | 99.23 % | 99.23 % | 99.18 % |
| recall_structured | 98.83 % | 98.83 % | 98.83 % |
| recall | 93.51 % | 93.51 % | 93.48 % |
| precision | 98.82 % | 98.82 % | 98.82 % |
| f2 | 94.53 % | 94.53 % | 94.50 % |
| entity_recall_direct | 98.80 % | 98.80 % | 98.70 % |
| doc_leak_rate | 8.33 % | 8.33 % | 9.07 % |
| doc_leak_rate_structured | 4.63 % | 4.63 % | 4.63 % |
| over_masking | 0.08 % | 0.08 % | 0.08 % |
| decoy_false_mask_rate | 3.46 % | 3.46 % | 3.46 % |

- Service = en processus (10 indicateurs) / service = in process: True ; service = référence / reference: False ; erreurs du service / service errors: {'base': {}, 'mutated': {}} ; 200.9 doc/s.
- `base`, service contre en processus / vs in process: 12 feuilles sur / leaves of 773, dont effet de frontière / boundary 12, inexpliquées / unexplained 0.
- `base`, service contre la référence / vs the reference: 70 feuilles sur / leaves of 773 : moteur changé depuis la référence / engine changed 42, bornes d'intervalle / interval bounds 17, frontière / boundary 11, inexpliquées / unexplained 0.
- `mutated`, service contre en processus / vs in process: 31 feuilles sur / leaves of 8535, dont effet de frontière / boundary 31, inexpliquées / unexplained 0.
- `mutated`, service contre la référence / vs the reference: 551 feuilles sur / leaves of 8535 : moteur changé depuis la référence / engine changed 392, bornes d'intervalle / interval bounds 128, frontière / boundary 31, inexpliquées / unexplained 0.

## Pays / countries `FR` — 540 + 6192 documents

| Indicateur / indicator | Service | En processus / in process | Référence / reference |
|---|---|---|---|
| recall_direct | 99.23 % | 99.23 % | 99.23 % |
| recall_structured | 98.83 % | 98.83 % | 98.83 % |
| recall | 93.51 % | 93.51 % | 93.51 % |
| precision | 98.82 % | 98.82 % | 98.82 % |
| f2 | 94.53 % | 94.53 % | 94.53 % |
| entity_recall_direct | 98.80 % | 98.80 % | 98.80 % |
| doc_leak_rate | 8.33 % | 8.33 % | 8.33 % |
| doc_leak_rate_structured | 4.63 % | 4.63 % | 4.63 % |
| over_masking | 0.08 % | 0.08 % | 0.08 % |
| decoy_false_mask_rate | 3.46 % | 3.46 % | 3.46 % |

- Service = en processus (10 indicateurs) / service = in process: True ; service = référence / reference: True ; erreurs du service / service errors: {'base': {}, 'mutated': {}} ; 196.2 doc/s.
- `base`, service contre en processus / vs in process: 12 feuilles sur / leaves of 773, dont effet de frontière / boundary 12, inexpliquées / unexplained 0.
- `base`, service contre la référence / vs the reference: 21 feuilles sur / leaves of 773 : moteur changé depuis la référence / engine changed 0, bornes d'intervalle / interval bounds 9, frontière / boundary 12, inexpliquées / unexplained 0.
- `mutated`, service contre en processus / vs in process: 31 feuilles sur / leaves of 8535, dont effet de frontière / boundary 31, inexpliquées / unexplained 0.
- `mutated`, service contre la référence / vs the reference: 41 feuilles sur / leaves of 8535 : moteur changé depuis la référence / engine changed 10, bornes d'intervalle / interval bounds 0, frontière / boundary 31, inexpliquées / unexplained 0.

## Explication de chaque catégorie / every category explained

- `boundary` : per system label (confusion, per-label precision, F2, IoU>=90%, typed rate, strict recall, strict entity rate, characters per system label): the boundary between two placeholders separated only by spaces cannot be recovered from the output (leftmost placement used); nothing that is masked depends on it
- `engine` : the service and the in-process evaluation agree with each other and differ from the reference file: the engine changed since the reference file was written
- `random_draws` : interval bounds only, the service and the in-process evaluation agree: bootstrap draws differ between the reference environment and this one (numpy or the pure-Python fallback), or the engine changed
