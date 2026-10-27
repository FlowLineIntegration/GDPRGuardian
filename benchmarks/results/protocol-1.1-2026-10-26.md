# Protocole public Gardien RGPD · GDPR Guardian public protocol — 2026-10-26

Protocole 1.1 (écrit le 2026-10-26, docs/PROTOCOLE.md). Scores seulement : aucun texte, aucune valeur annotée. Scores only: no text, no annotated value.

Versions précédentes, résultats gardés publiés / previous versions, results kept published : 1.0 : 61.8 % [58.6-66.9] (7 familles / families, campagne / campaign 2026-10-26, benchmarks/results/protocol-2026-10-26.md).

> **Moitiés `test` non aveugles / test halves not blind** : déjà notées par la campagne 2026-10-26 (1.0.0+0c3ff9fc1fb0), scores par famille publiés pendant la mise au point du moteur : chiffres des corpus réels optimistes (docs/PROTOCOLE.md, « Version 1.1 ») / already scored by that campaign, per-family scores published while the engine was tuned: real-corpus figures are optimistic.

- Campagne / campaign : terminée / complete ; plan d5676bcfe40afa96 ; 1,019,385 documents ; 793/793 unités ; 10,088.3 s actives, 101.0 doc/s ; ralenti pour les visiteurs / yielded to visitors 0.0 s.
- Moteur / engine : 1.0.1+4bb5c465425e (image 4bb5c465425e, packs c92770ff020a, sonde / probe df6f7a380268 sur 200 documents) ; contrôlé / checked 155 fois / times, identique à chaque fois / identical every time.
- Enregistrement / registration : empreintes du plan conformes / plan fingerprints match: oui / yes ; outil / tool 306e2ee67dcb, spec.py 035a231d5238, PROTOCOLE.md 0fb9254c4511, paquet / bundle b64d1bac1898, Faker 40.43.0.
- Erreurs du service (comptées comme fuites) / service errors (counted as leaks) : 0 ; documents à alignement ambigu (comptés prudemment) / ambiguous alignments (scored conservatively) : 0.
- Moitiés test déjà mesurées avant cette campagne / test halves measured before this campaign : 9 mesures (docs/PROTOCOLE.md, section 3) ; campagnes antérieures / earlier campaigns : 2026-10-26 (1.0.0+0c3ff9fc1fb0).

Deux indices, même mesure : part des documents dont aucun identifiant direct ne reste lisible (pas un seul caractère alphanumérique d'une mention du gold). Les intervalles ne couvrent que le tirage des documents. Two indexes, same measure: share of documents in which no direct identifier stays readable (not one alphanumeric character of a gold mention). The intervals cover document sampling only.

## Indice de confiance, documents normalisés / confidence index, normalised documents

**96.9 %** [96.2–97.6] — moyenne à poids égal des 4 familles (moitié test des corpus réels) ; cible / target ≥ 95 %. Equal-weight mean of the 4 families (test half of the real corpora).

Rappel des mentions directes / direct-mention recall : **99.3 %** [98.8–99.6]. Tous les documents réels (dev + test) / all real documents : 96.5 % ; moitié dev (règles conçues dessus) / dev half (rules designed on it) : 96.1 %.

| Famille / family | Documents notés / scored | Sans fuite / no leak [Wilson 95 %] | Rappel mentions / mention recall | Précision / precision | Erreurs / errors |
|---|---:|---|---|---|---|
| Synthétique FR (10 graines, leurres) / Synthetic FR (10 seeds, decoys) | 450,000 | 97.2 % [97.1–97.2] | 99.6 % | 98.8 % | 0 |
| BODACC / BODACC | 1,335 | 97.5 % [96.5–98.2] | 99.5 % | 99.2 % | 0 |
| BOAMP / BOAMP | 1,408 | 95.1 % [93.8–96.1] | 98.3 % | 87.7 % | 0 |
| ParlaMint-FR / ParlaMint-FR | 143 | 97.9 % [94.0–99.3] | 99.8 % | — | 0 |

## Par corpus réel de l'indice / per index real corpus (test · dev · all)

| Corpus | Pays / countries | Sans fuite test / dev / all | Rappel mentions test / all | Précision test / all |
|---|---|---|---|---|
| bodacc_fr | FR | 97.5 % / 96.6 % / 97.0 % | 99.5 % / 99.4 % | 99.2 % / 99.2 % |
| boamp_fr | FR | 95.1 % / 95.1 % / 95.1 % | 98.3 % / 98.8 % | 87.7 % / 87.4 % |
| parlamint_fr | FR | 97.9 % / 95.5 % / 96.7 % | 99.8 % / 99.7 % | — / — |

## Documents difficiles / difficult documents

**84.0 %** [83.9–84.1] — équipe rouge, 51 opérateurs, 548,907 documents mutés notés : chaque document muté compte une fois (un groupe pèse sa part des documents), intervalle par bootstrap stratifié par groupe. Red team, 51 operators: every mutated document counts once (a group weighs its share of the documents), interval by a bootstrap stratified by group. Rappel des mentions / mention recall : 95.0 % [95.0–95.1].

| Groupe / group | Opérateurs | Documents notés / scored | Poids / weight | Sans fuite / no leak [Wilson 95 %] | Rappel mentions / mention recall |
|---|---:|---:|---:|---|---|
| Formats du quotidien abîmés / damaged everyday formats | 25 | 284,081 | 51.8 % | 84.9 % [84.7–85.0] | 96.5 % |
| Déguisements volontaires / deliberate obfuscations | 25 | 252,895 | 46.1 % | 86.6 % [86.5–86.7] | 94.5 % |
| Bruit d'OCR / OCR noise | 1 | 11,931 | 2.2 % | 9.2 % [8.7–9.7] | 72.8 % |

| Famille / family | Documents notés / scored | Sans fuite / no leak [Wilson 95 %] | Rappel mentions / mention recall | Précision / precision | Erreurs / errors |
|---|---:|---|---|---|---|
| Équipe rouge FR, formats du quotidien abîmés (25 opérateurs) / Red team FR, damaged everyday formats (25 operators) | 284,081 | 84.9 % [84.7–85.0] | 96.5 % | 98.8 % | 0 |
| Équipe rouge FR, déguisements volontaires (25 opérateurs) / Red team FR, deliberate obfuscations (25 operators) | 252,895 | 86.6 % [86.5–86.7] | 94.5 % | 98.8 % | 0 |
| Équipe rouge FR, bruit d'OCR : performance dégradée / Red team FR, OCR noise: degraded performance | 11,931 | 9.2 % [8.7–9.7] | 72.8 % | 98.6 % | 0 |

## Publiés à part, dans aucun indice / published apart, in neither index

Presse ancienne (OCR de mauvaise qualité : performance dégradée), MAPA FR (textes juridiques de l'UE, trop peu de documents). Mêmes mesures. Old press (low-quality OCR: degraded performance), MAPA FR (EU legal texts, too few documents). Same measures.

| Famille / family | Documents notés / scored | Sans fuite / no leak [Wilson 95 %] | Rappel mentions / mention recall | Précision / precision | Erreurs / errors |
|---|---:|---|---|---|---|
| Presse ancienne FR (Europeana + HIPE), OCR de mauvaise qualité : performance dégradée / Old French press (Europeana + HIPE), low-quality OCR: degraded performance | 272 | 17.3 % [13.3–22.2] | 55.2 % | 75.5 % | 0 |
| MAPA FR (6 documents notés : sans valeur statistique) / MAPA FR (6 scored documents: statistically meaningless) | 6 | 16.7 % [3.0–56.4] | 33.1 % | 46.8 % | 0 |

| Corpus | Pays / countries | Sans fuite test / dev / all | Rappel mentions test / all | Précision test / all |
|---|---|---|---|---|
| europeana_fr | FR | 21.5 % / 30.1 % / 26.1 % | 71.6 % / 72.1 % | 76.2 % / 76.5 % |
| hipe_newseye_fr | FR | 3.2 % / 5.1 % / 4.1 % | 45.5 % / 46.1 % | 75.1 % / 74.3 % |
| mapa_fr | FR | 16.7 % / 0.0 % / 11.1 % | 33.1 % / 35.1 % | 46.8 % / 42.9 % |

## Autres langues, hors périmètre : jamais dans l'indice / other languages, out of scope: never in the index

Mêmes mesures que le périmètre français, publiées à part : elles disent ce que le service fait des documents d'autres pays. Same measures as the French scope, published apart: they show what the service does with documents from other countries.

| Corpus | Pays / countries | Sans fuite test / dev / all | Rappel mentions test / all | Précision test / all |
|---|---|---|---|---|
| mapa_de | DE | 0.0 % / 0.0 % / 0.0 % | 0.0 % / 0.0 % | — / — |
| mapa_es | ES | 0.0 % / 0.0 % / 0.0 % | 0.0 % / 0.0 % | — / — |
| mapa_it | IT | 0.0 % / 0.0 % / 0.0 % | 0.0 % / 0.0 % | — / — |
| mapa_nl | NL | 0.0 % / 0.0 % / 0.0 % | 0.0 % / 0.0 % | — / 0.0 % |
| mapa_pt | PT | 0.0 % / 0.0 % / 0.0 % | 0.0 % / 0.0 % | — / — |
| meddocan_es | ES | 0.0 % / 0.0 % / 0.0 % | 10.7 % / 10.9 % | 61.1 % / 61.1 % |
| german_ler_de | DE | 0.0 % / 0.0 % / 0.0 % | 0.0 % / 0.0 % | — / 0.0 % |
| tab_en | FR | 67.3 % / 58.3 % / 62.2 % | 82.8 % / 83.3 % | 77.9 % / 77.5 % |

## Témoin négatif / negative control

- judilibre_fr : 300 décisions, 3,797 zones masquées (11.5 pour 10 000 caractères / per 10,000 chars), 100.0 % des documents avec au moins une zone. pas de gold : précision seulement par relecture manuelle / no gold: precision only through a manual review (docs/CORPUS_REELS.md, section 7)

## Équipe rouge par opérateur / red team per operator

Les trois groupes font l'indice « documents difficiles » ; aucun n'est dans l'indice « documents normalisés ». The three groups make the difficult-documents index; none is in the normalised one.

| Opérateur | Groupe / group | Documents | Sans fuite / no leak | Rappel mentions | Survie / survival |
|---|---|---:|---|---|---|
| arabic_indic | déguisement / obfuscation | 12,000 | 97.1 % | 99.5 % | 100.0 % |
| arobase | déguisement / obfuscation | 6,113 | 92.8 % | 99.1 % | 100.0 % |
| at_brackets | déguisement / obfuscation | 6,113 | 92.8 % | 99.1 % | 100.0 % |
| at_entity | déguisement / obfuscation | 6,113 | 92.8 % | 99.1 % | 100.0 % |
| at_fullwidth | déguisement / obfuscation | 6,113 | 94.9 % | 99.3 % | 100.0 % |
| at_parens | déguisement / obfuscation | 6,113 | 92.8 % | 99.1 % | 100.0 % |
| at_percent | déguisement / obfuscation | 6,113 | 92.8 % | 99.1 % | 100.0 % |
| bidi_isolate | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| bidi_mark | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| bom | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| compact | quotidien / everyday | 11,122 | 93.6 % | 98.9 % | 97.9 % |
| crlf | quotidien / everyday | 12,000 | 10.8 % | 75.5 % | 69.7 % |
| cyrillic | déguisement / obfuscation | 12,000 | 76.5 % | 96.6 % | 95.2 % |
| devanagari | déguisement / obfuscation | 12,000 | 97.1 % | 99.5 % | 100.0 % |
| dot_brackets | déguisement / obfuscation | 6,113 | 94.9 % | 99.3 % | 100.0 % |
| dot_point | déguisement / obfuscation | 6,113 | 94.9 % | 99.3 % | 100.0 % |
| dots | quotidien / everyday | 11,937 | 95.2 % | 99.4 % | 98.6 % |
| double_space | quotidien / everyday | 12,000 | 91.4 % | 98.9 % | 91.8 % |
| en_dash_groups | quotidien / everyday | 12,000 | 95.4 % | 99.4 % | 99.3 % |
| figure_space | quotidien / everyday | 12,000 | 97.1 % | 99.5 % | 100.0 % |
| fullwidth | déguisement / obfuscation | 12,000 | 97.1 % | 99.5 % | 100.0 % |
| grapheme_joiner | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| greek | déguisement / obfuscation | 11,991 | 97.1 % | 99.5 % | 100.0 % |
| hangul_filler | déguisement / obfuscation | 12,000 | 97.7 % | 99.7 % | 100.0 % |
| hyphens | quotidien / everyday | 11,681 | 95.3 % | 99.4 % | 99.2 % |
| ideographic_space | quotidien / everyday | 12,000 | 97.1 % | 99.5 % | 100.0 % |
| letter_spacing | quotidien / everyday | 12,000 | 88.3 % | 98.6 % | 98.9 % |
| line_break | quotidien / everyday | 12,000 | 15.9 % | 76.9 % | 71.1 % |
| lower | quotidien / everyday | 12,000 | 30.2 % | 79.0 % | 60.7 % |
| markdown_bold | quotidien / everyday | 12,000 | 96.1 % | 99.5 % | 99.6 % |
| math_bold | déguisement / obfuscation | 12,000 | 0.0 % | 35.8 % | 36.3 % |
| narrow_nbsp | quotidien / everyday | 12,000 | 97.1 % | 99.5 % | 100.0 % |
| nb_hyphen | quotidien / everyday | 6,047 | 97.1 % | 99.6 % | 100.0 % |
| nbsp | quotidien / everyday | 12,000 | 97.1 % | 99.5 % | 100.0 % |
| nfd | quotidien / everyday | 8,859 | 97.0 % | 99.6 % | 100.0 % |
| ocr | OCR | 11,931 | 9.2 % | 72.8 % | 28.6 % |
| pdf_hyphenation | quotidien / everyday | 12,000 | 92.9 % | 99.0 % | 99.0 % |
| regroup | quotidien / everyday | 11,997 | 89.9 % | 98.6 % | 91.6 % |
| slashes | quotidien / everyday | 12,000 | 86.1 % | 98.2 % | 94.4 % |
| soft_hyphen | quotidien / everyday | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| strip_accents | quotidien / everyday | 8,859 | 97.0 % | 99.6 % | 100.0 % |
| superscript | déguisement / obfuscation | 12,000 | 0.0 % | 55.5 % | 6.8 % |
| surname_first | quotidien / everyday | 9,579 | 95.5 % | 99.3 % | 99.5 % |
| tab | quotidien / everyday | 12,000 | 90.8 % | 98.8 % | 98.8 % |
| tag_chars | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| thin_space | quotidien / everyday | 12,000 | 97.1 % | 99.5 % | 100.0 % |
| upper | quotidien / everyday | 12,000 | 95.3 % | 99.3 % | 99.5 % |
| variation_selector | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| word_joiner | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| zero_width_joiner | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |
| zero_width_space | déguisement / obfuscation | 12,000 | 97.9 % | 99.7 % | 100.0 % |

## Garde-fous / guards

- overmask_synthetic : 0.07 % (≤ 2.0 %) — ok
- decoys_masked_synthetic : 3.71 % (≤ 10.0 %) — ok
- precision_bodacc_fr : 99.16 % (≥ 70.0 %) — ok
- precision_boamp_fr : 87.69 % (≥ 70.0 %) — ok

## Clés du site / site quality keys

```json
{
  "confidence_index": 96.9,
  "confidence_ci_low": 96.2,
  "confidence_ci_high": 97.6,
  "mention_recall_pct": 99.3,
  "protocol_docs": 1019385,
  "protocol_families": 4,
  "real_corpora": 14,
  "real_docs": 8178,
  "protocol_date": "2026-10-26",
  "protocol_engine": "1.0.1+4bb5c465425e",
  "hard_index": 84.0,
  "hard_ci_low": 83.9,
  "hard_ci_high": 84.1,
  "hard_docs": 548907,
  "hard_mention_recall_pct": 95.0
}
```

Rejouer / replay: docs/PROTOCOLE.md, section 10.
