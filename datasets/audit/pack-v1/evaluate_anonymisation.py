#!/usr/bin/env python3
"""Évalue un export anonymisé en le comparant à la vérité terrain synthétique.

Usage :
  python evaluate_anonymisation.py sortie_anonymisee.md
  python evaluate_anonymisation.py sortie_anonymisee.md --original corpus_anonymisation_rgpd_fictif.md

Limites : l’évaluation mesure les mentions de référence encore reconnaissables et la conservation
exacte des contrôles négatifs. Elle ne remplace pas une revue humaine, ne détecte pas toutes les
ré-identifications par recoupement et suppose que la structure générale du texte est conservée.
"""
import argparse, csv, re, unicodedata, os, sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ORIGINAL = os.path.join(BASE, 'corpus_anonymisation_rgpd_fictif.md')
DEFAULT_PII = os.path.join(BASE, 'gold_standard_mentions.csv')
DEFAULT_SAFE = os.path.join(BASE, 'gold_standard_safe_controls.csv')

DIGIT_TYPES = {'TELEPHONE','FRAGMENT_TELEPHONE','NIR_TEST','IBAN_TEST','CARTE_PAIEMENT_TEST'}
COMPACT_TYPES = {'IDENTIFIANT_CLIENT','IDENTIFIANT_SALARIE','REFERENCE_DOSSIER_PERSONNEL','IDENTIFIANT_TERMINAL','COOKIE_IDENTIFIANT','ADRESSE_IP_TEST','ADRESSE_IPV6_TEST','IDENTIFIANT_BIOMETRIQUE','DONNEE_BIOMETRIQUE','IMMATRICULATION_TEST'}

def fold(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s.casefold()).strip()

def canon(s, category):
    if category in DIGIT_TYPES:
        return ''.join(c for c in s if c.isdigit())
    if category in COMPACT_TYPES:
        return ''.join(c for c in fold(s) if c.isalnum())
    return fold(s)

def load_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def count_in_text(text, value, category):
    # Work line by line, so separators from unrelated fields cannot be concatenated across paragraphs.
    target = canon(value, category)
    if not target:
        return 0
    total = 0
    for line in text.splitlines():
        norm = canon(line, category)
        start = 0
        while True:
            pos = norm.find(target, start)
            if pos < 0: break
            total += 1
            start = pos + max(1, len(target))
    return total

def split_sections(text):
    matches = list(re.finditer(r'(?m)^## Cas (\d{3}) :', text))
    result = {}
    for i, m in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        result[f'CAS-{m.group(1)}'] = text[m.start():end]
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('anonymized', help='Chemin vers le fichier de sortie de l’anonymiseur')
    ap.add_argument('--original', default=DEFAULT_ORIGINAL)
    ap.add_argument('--pii', default=DEFAULT_PII)
    ap.add_argument('--safe', default=DEFAULT_SAFE)
    args = ap.parse_args()
    for p in (args.anonymized,args.original,args.pii,args.safe):
        if not os.path.isfile(p):
            print(f'Fichier introuvable : {p}', file=sys.stderr); return 2
    with open(args.anonymized,encoding='utf-8',errors='replace') as f: anon=f.read()
    sections = split_sections(anon)
    pii = load_csv(args.pii); safe = load_csv(args.safe)
    # Scoring is section-scoped to avoid a value in another dossier falsely compensating for a leak.
    def score(rows, is_safe=False):
        groups = defaultdict(int)
        for r in rows:
            groups[(r['doc_id'],r['category'],canon(r['text'],r['category']))] += 1
        total = len(rows)
        detected = 0
        stats = defaultdict(lambda: [0,0])
        for (doc_id,cat,norm), expected in groups.items():
            exemplar = next(r['text'] for r in rows if r['doc_id']==doc_id and r['category']==cat and canon(r['text'],cat)==norm)
            section = sections.get(doc_id, '')
            observed = min(expected, count_in_text(section, exemplar, cat))
            detected += observed
            stats[cat][0] += expected
            stats[cat][1] += observed
        return total, detected, stats
    pii_total, leaked, category_stats = score(pii)
    pii_recall = (pii_total - leaked) / pii_total if pii_total else 1.0
    safe_total, safe_kept, safe_stats = score(safe, is_safe=True)
    safe_retention = safe_kept / safe_total if safe_total else 1.0
    redaction_overreach = 1-safe_retention
    balanced = 2*pii_recall*safe_retention/(pii_recall+safe_retention) if pii_recall+safe_retention else 0
    print('\n=== ÉVALUATION DU SYSTÈME D’ANONYMISATION ===')
    print(f'Mentions personnelles / sensibles de référence : {pii_total}')
    print(f'Mentions encore reconnaissables (fuites détectées) : {leaked}')
    print(f'Protection des mentions de référence (rappel de masquage) : {100*pii_recall:.2f} %')
    print(f'Contrôles non personnels de référence : {safe_total}')
    print(f'Contrôles conservés : {safe_kept}')
    print(f'Conservation des contrôles négatifs : {100*safe_retention:.2f} %')
    print(f'Taux de sur-anonymisation sur contrôles négatifs : {100*redaction_overreach:.2f} %')
    print(f'Score équilibré (moyenne harmonique protection/conservation) : {100*balanced:.2f} %')
    print('\nPar catégorie : fuites / mentions de référence')
    for cat,(tot,leak) in sorted(category_stats.items()):
        print(f'  {cat}: {leak}/{tot} fuite(s), protection={(100*(tot-leak)/tot if tot else 100):.2f} %')
    print('\nPar contrôle négatif : conservés / mentions de référence')
    for cat,(tot,kept) in sorted(safe_stats.items()):
        print(f'  {cat}: {kept}/{tot}, conservation={(100*kept/tot if tot else 100):.2f} %')
    print('\nInterprétation : les valeurs ci-dessus évaluent uniquement les mentions annotées. Une revue humaine reste nécessaire pour les inférences, les recoupements, les entités non prévues et le maintien de l’utilité du texte.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
