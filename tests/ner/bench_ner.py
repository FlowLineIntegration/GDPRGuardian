"""Banc d'essai NER : latence par 10 Ko (avec ou sans filtre), rappel face aux heuristiques, fp32 face à INT8.

NER benchmark: latency per 10 KB (gated or not), recall versus heuristics, fp32 versus INT8 (local build and
the author's shipped file).

    python -X utf8 tests/ner/bench_ner.py [--repeat 15] [--quantized]
"""

from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import onnxruntime
from _ner_corpus import HELDOUT_PATH, Report, Sample, evaluate, load_corpus

from gdprguardian import Anonymizer, Settings
from gdprguardian._text import fold
from gdprguardian.engine import DetectionContext
from gdprguardian.ner import NerDetector, load_detector
from gdprguardian.ner.chunking import has_signal, split_units
from gdprguardian.ner.decode import softmax

# Prose sans entité, typique d'un dossier / entity-free prose typical of a business file.
NEUTRAL = (
    "Le présent contrat prend effet à la date de sa signature par les deux parties.",
    "les sommes dues sont payables à trente jours fin de mois, par virement bancaire.",
    "En cas de retard de paiement, des pénalités seront appliquées de plein droit.",
    "Le prestataire s'engage à respecter la confidentialité des informations transmises.",
    "La résiliation anticipée doit être notifiée par lettre recommandée avec accusé de réception.",
    "Le patient ne présente pas d'antécédent particulier et le traitement est bien toléré.",
    "Un contrôle biologique est prévu dans trois mois, puis une consultation de suivi.",
    "Les congés payés sont acquis à raison de deux jours et demi ouvrables par mois de travail effectif.",
    "La période d'essai peut être renouvelée une fois, pour une durée équivalente.",
    "Le salarié bénéficie d'une prime annuelle dont le montant dépend des objectifs atteints.",
    "Les données sont conservées pendant la durée strictement nécessaire au traitement.",
    "Toute modification du présent accord fera l'objet d'un avenant écrit.",
    "le locataire s'engage à entretenir le logement et à souscrire une assurance habitation.",
    "Le dépôt de garantie sera restitué dans un délai maximal de deux mois après la remise des clés.",
    "Nous vous remercions de bien vouloir nous transmettre les pièces justificatives demandées.",
    "La livraison est prévue sous huit jours ouvrés à compter de la confirmation de commande.",
    "Les frais de port sont offerts à partir de cinquante euros d'achat.",
    "En l'absence de réponse sous quinze jours, la demande sera considérée comme acceptée.",
    "La réunion a permis de faire le point sur l'avancement du projet et les prochaines étapes.",
    "les échanges se sont déroulés dans un climat constructif et chacun a pu s'exprimer.",
    "Il convient de vérifier la conformité des installations électriques avant la mise en service.",
    "Le rapport annuel sera présenté lors de la prochaine assemblée générale.",
    "Une attention particulière sera portée à la sécurité des personnes sur le chantier.",
    "Les justificatifs doivent être conservés pendant une durée de dix ans.",
)


def build_document(samples: Sequence[Sample], size: int = 10_240) -> str:
    """~10 Ko : deux phrases neutres pour une phrase du corpus, sans doublon / no duplicate sentences."""
    paragraphs: list[str] = []
    sentences: list[str] = []
    total = 0
    i = 0
    while total < size:
        sentence = samples[(i // 3) % len(samples)].text if i % 3 == 2 else NEUTRAL[i % len(NEUTRAL)]
        sentence = f"{sentence.rstrip('.')} (dossier {i})."
        sentences.append(sentence)
        total += len(sentence) + 1
        if len(sentences) == 4:
            paragraphs.append(" ".join(sentences))
            sentences = []
        i += 1
    paragraphs.append(" ".join(sentences))
    return "\n\n".join(p for p in paragraphs if p)


def build_cells(samples: Sequence[Sample], count: int = 600) -> list[str]:
    """Cellules de tableur distinctes : une mention de référence et un numéro / distinct spreadsheet cells."""
    mentions = [s.text[a:b] for s in samples for _, a, b in s.gold]
    return [f"{mentions[i % len(mentions)]} {i}" for i in range(count)]


def cells_context(cells: Sequence[str]) -> DetectionContext:
    """Contexte à segments, comme `Anonymizer.analyze_segments` / segmented context, like analyze_segments."""
    starts: list[int] = []
    ends: list[int] = []
    cursor = 0
    for cell in cells:
        starts.append(cursor)
        cursor += len(cell)
        ends.append(cursor)
        cursor += 2
    joined = "\n\n".join(cells)
    return DetectionContext(joined, fold(joined), None, ("FR",), "fr", Settings(), starts, ends)


def timed(fn: Callable[[], object], repeat: int) -> tuple[float, float]:
    fn()
    samples = []
    for _ in range(repeat):
        t0 = perf_counter()
        fn()
        samples.append((perf_counter() - t0) * 1000)
    samples.sort()
    return statistics.median(samples), samples[int(0.9 * (len(samples) - 1))]


def engine_report(anonymizer: Anonymizer, samples: Sequence[Sample]) -> Report:
    return evaluate(samples, [anonymizer.analyze(s.text).spans for s in samples])


def processable(anonymizer: Anonymizer, samples: Sequence[Sample]) -> list[Sample]:
    """Textes que le moteur traite sans erreur (modules développés en parallèle) / texts the engine handles."""
    kept = []
    for sample in samples:
        try:
            anonymizer.analyze(sample.text)
        except Exception as exc:  # signalé, puis écarté de toutes les mesures / reported, then skipped everywhere
            print(f"   ! engine error on one sample ({type(exc).__name__}), excluded from every configuration")
            continue
        kept.append(sample)
    return kept


def detector_report(detector: NerDetector, samples: Sequence[Sample], **settings: object) -> Report:
    spans = []
    for sample in samples:
        ctx = DetectionContext(sample.text, fold(sample.text), None, ("FR",), "fr", Settings(**settings))
        spans.append(detector.detect(ctx))
    return evaluate(samples, spans)


def agreement(fp32: NerDetector, other: NerDetector, samples: Sequence[Sample]) -> tuple[float, float]:
    """Accord des étiquettes argmax par jeton, global et sur les jetons PER/ORG/LOC du fp32 (comme l'outil).

    Token label agreement, overall and on fp32 PER/ORG/LOC tokens (as in tools/download_models.py).
    """
    a, b = fp32._model.get(), other._model.get()
    named = a.scheme.type_matrix.any(axis=1)
    same = total = same_entity = entity = 0
    for sample in samples:
        ids = np.array([a.tokenizer.encode(sample.text).ids], np.int64)
        feeds = {"input_ids": ids, "attention_mask": np.ones_like(ids)}
        la = softmax(a.session.run(None, feeds)[0])[0, 1:-1].argmax(-1)
        lb = softmax(b.session.run(None, feeds)[0])[0, 1:-1].argmax(-1)
        on_entity = named[la]
        same += int((la == lb).sum())
        total += la.size
        entity += int(on_entity.sum())
        same_entity += int((on_entity & (la == lb)).sum())
    return same / total, same_entity / max(entity, 1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=15)
    parser.add_argument("--quantized", action="store_true",
                        help="évalue aussi model_quantized.onnx (auteur) / also evaluate the shipped INT8")
    args = parser.parse_args(argv)
    ner = load_detector(model_file="model.onnx")
    if ner is None:
        print("modèle absent : python tools/download_models.py / model missing")
        return 1
    print(f"Python {platform.python_version()}, onnxruntime {onnxruntime.__version__}, "
          f"{os.cpu_count()} logical CPUs, {platform.processor() or platform.machine()}")
    t0 = perf_counter()
    ner.warmup()
    print(f"cold start fp32 (SHA-256 check + session + first run): {(perf_counter() - t0) * 1000:.0f} ms")
    int8 = load_detector(model_file="model_int8.onnx")
    if int8 is not None:
        t0 = perf_counter()
        int8.warmup()
        print(f"cold start INT8 (manifest check + session + first run): {(perf_counter() - t0) * 1000:.0f} ms")
    models = [("fp32", ner)] + ([("INT8 local", int8)] if int8 is not None else [])

    corpus, heldout = load_corpus(), load_corpus(HELDOUT_PATH)
    document = build_document(corpus)
    ctx_doc = DetectionContext(document, fold(document), None, ("FR",), "fr", Settings())
    units = split_units(document, [(0, len(document))])
    gated = [u for u in units if has_signal(document, fold(document), *u)]
    print(f"\n== Latency, {len(document)} chars (~10 KB), {len(units)} sentences, {len(gated)} pass the gate "
          f"({len(gated) / len(units):.0%}); median / p90 over {args.repeat} runs")
    baseline = Anonymizer()
    rows = [("heuristics only (no NER)", baseline)]
    for label, detector in models:
        rows.append((f"+ NER {label}, gating on (default)", Anonymizer(Settings(detectors=[detector]))))
        rows.append((f"+ NER {label}, gating off", Anonymizer(Settings(detectors=[detector.replace(gating=False)]))))
    for title, anonymizer in rows:
        median, p90 = timed(lambda a=anonymizer: a.anonymize(document), args.repeat)
        print(f"  {title:40} {median:8.1f} ms  p90 {p90:8.1f} ms")
    cells = build_cells(corpus)
    ctx_cells = cells_context(cells)
    print(f"\n  NER detector alone (fp32), by padded-token budget per call ({ner._model.threads} threads):")
    for budget in (64, 256, 512, 1024, 2048):
        variant = ner.replace(batch_tokens=budget)
        prose, _ = timed(lambda d=variant: d.detect(ctx_doc), args.repeat)
        table, _ = timed(lambda d=variant: d.detect(ctx_cells), max(3, args.repeat // 3))
        print(f"    budget {budget:5}: prose {prose:7.1f} ms   {len(cells)} cells {table:7.1f} ms")
    print(f"  NER detector alone, by intra-op threads (budget {ner.batch_tokens}):")
    for threads in (1, 2, 4, 8):
        if threads > (os.cpu_count() or 1):
            continue
        for label, detector in models:
            fresh = load_detector(model_file=detector.files[0], threads=threads)
            fresh.warmup()
            median, _ = timed(lambda d=fresh: d.detect(ctx_doc), args.repeat)
            print(f"    {threads} thread(s), {label:10}: {median:7.1f} ms")

    print("\n== Recall (share of gold mentions fully masked; 'typed' = right entity type)")
    for name, all_samples in (("tuning corpus", corpus), ("held-out corpus", heldout)):
        samples = processable(baseline, all_samples)
        print(f"-- {name}: {len(samples)} texts, {sum(len(s.gold) for s in samples)} gold mentions")
        configs = [("heuristics only", baseline)]
        for label, detector in models:
            configs.append((f"heuristics + NER {label} (standard)", Anonymizer(Settings(detectors=[detector]))))
            configs.append((f"heuristics + NER {label} (strict)",
                            Anonymizer(Settings(detectors=[detector], profile="strict"))))
        for title, anonymizer in configs:
            report = engine_report(anonymizer, samples)
            print(f"   {title}")
            print("      " + report.summary().replace("\n", "\n      "))
            if report.missed and "NER" in title:
                print("      missed: " + ", ".join(f"{e}:{v!r}" for e, v in report.missed))
    if int8 is not None:
        overall, on_entities = agreement(ner, int8, corpus + heldout)
        print(f"   INT8 local, token label agreement with fp32: {overall:.1%} overall, "
              f"{on_entities:.1%} on fp32 entity tokens")

    if args.quantized:
        quantized = load_detector(model_file="model_quantized.onnx")
        if quantized is None:
            print("\nmodel_quantized.onnx absent (tools/download_models.py --with-quantized)")
            return 0
        quantized.warmup()
        print("\n== Shipped dynamic INT8 (model_quantized.onnx) versus fp32 (model.onnx), NER detector alone")
        for name, samples in (("tuning corpus", corpus), ("held-out corpus", heldout)):
            for profile in ("standard", "strict"):
                fp = detector_report(ner, samples, profile=profile)
                q8 = detector_report(quantized, samples, profile=profile)
                print(f"   {name:16} {profile:8}: fp32 masked {fp.recall():6.1%} | INT8 masked {q8.recall():6.1%}"
                      f" (PERSON {q8.recall('PERSON'):.1%}), INT8 false positives {q8.false_positives}")
        overall, on_entities = agreement(ner, quantized, corpus + heldout)
        print(f"   token label agreement with fp32: {overall:.1%} overall, {on_entities:.1%} on fp32 entity tokens")
        for title, detector in (("fp32", ner), ("INT8 shipped", quantized)):
            median, _ = timed(lambda d=detector: d.detect(ctx_doc), args.repeat)
            print(f"   latency 10 KB, {title:12}: {median:7.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
