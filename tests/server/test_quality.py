"""Qualité minimale du texte : un OCR dégradé est signalé, jamais refusé / minimum text quality: warned, never refused.

Données entièrement fictives ; le texte dégradé est fabriqué ici par des substitutions typiques de l'OCR.
Entirely fictitious data; the degraded text is made here with typical OCR substitutions.
"""

from __future__ import annotations

import random
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from server_testkit import AUTH_A

from gdprguardian import documents
from gdprguardian.documents import DocumentResult
from gdprguardian.server import quality
from gdprguardian.server.isolation import _WARM_UP_TEXT

CLEAN = (
    "Madame, Monsieur,\n\nSuite à notre entretien du lundi 11 mars, je vous confirme que le dossier de prestation "
    "sera repris par notre service juridique à compter du premier avril. Les pièces justificatives demandées "
    "seront transmises par courrier recommandé dans les meilleurs délais. Nous restons à votre disposition pour "
    "toute question relative au contrat, à la facturation ou au calendrier des travaux prévus dans les locaux de "
    "la société. Le comité de suivi se réunira chaque trimestre afin de vérifier l'avancement du projet et de "
    "proposer, le cas échéant, les ajustements nécessaires au bon déroulement de la mission confiée.\n"
) * 3
_OCR_SWAPS = (("e", "c"), ("n", "u"), ("l", "1"), ("m", "rn"), ("a", "à"), ("i", "î"), ("t", "f"), ("o", "0"))


def degrade(text: str, rate: float = 0.12, seed: int = 7) -> str:
    """Substitutions de caractères et fragments typiques d'un OCR de presse ancienne / typical old-press OCR noise."""
    rng = random.Random(seed)
    out = []
    for char in text:
        roll = rng.random()
        if roll < rate:
            swap = next((new for old, new in _OCR_SWAPS if old == char), None)
            out.append(swap if swap is not None else char)
            if rng.random() < 0.15:
                out.append(rng.choice(" »•'.,"))
        else:
            out.append(char)
    return "".join(out)


def test_clean_french_and_english_texts_are_not_flagged() -> None:
    assert not quality.low_quality(CLEAN, "fr")
    assert not quality.low_quality(_WARM_UP_TEXT * 3, "fr")
    english = ("The committee will meet every quarter to review the progress of the project and to propose, where "
               "appropriate, the adjustments needed for the assignment. The supporting documents requested will be "
               "sent by registered mail as soon as possible. ") * 4
    assert not quality.low_quality(english, "en")


def test_degraded_ocr_text_is_flagged() -> None:
    noisy = degrade(CLEAN)
    score = quality.quality_score(noisy)
    assert score is not None and score >= quality.THRESHOLD
    assert quality.low_quality(noisy, "fr")


def test_other_languages_and_short_texts_are_never_judged() -> None:
    noisy = degrade(CLEAN)
    assert not quality.low_quality(noisy, "de") and not quality.low_quality(noisy, "und")
    assert quality.quality_score("Bonjour Jean, à demain.") is None


def test_big_texts_are_sampled() -> None:
    big = CLEAN * 2000  # environ 3 millions de caractères / about 3 million characters
    assert len(quality._sample(big)) < 250_000
    assert not quality.low_quality(big, "fr")


_PATHOLOGICAL = {"giant_token": ("x", 1_000_000), "tiny_tokens": ("x ", 500_000),
                 "hyphen_spaces": ("a-" + " " * 5_000, 40), "at_signs": ("@", 300_000), "slashes": ("w/", 100_000)}


@pytest.mark.parametrize("name", sorted(_PATHOLOGICAL))
def test_pathological_texts_are_measured_quickly(name: str) -> None:
    # Jetons géants ou répétitifs : jamais de coût quadratique / giant or repetitive tokens: never quadratic.
    unit, count = _PATHOLOGICAL[name]
    text = unit * count
    started = time.perf_counter()
    quality.quality_score(text)
    assert time.perf_counter() - started < 2.0


# Écrits professionnels propres et fictifs, riches en sigles, codes et noms de produits / clean, fictitious business
# writing, full of acronyms, codes and product names.
_TECHNICAL = {
    "en": ("Deployment guide\n1. Pull the image: docker pull registry.example.com/app:v2.4.1 and check the SHA256 "
           "digest.\n2. Set the env vars DB_HOST, DB_PORT and REDIS_URL in the .env file; never commit secrets to "
           "Git.\n"
           "3. Run kubectl apply -f k8s/ and wait until every pod is Ready; the HPA scales from 2 to 8 replicas.\n"
           "4. Smoke test: curl the /healthz endpoint, then run the e2e suite with npm run test:e2e on Node 20.\n"
           "5. If the rollout fails, run kubectl rollout undo and open an incident in PagerDuty with the logs from "
           "Grafana and Loki.\nThe service exposes gRPC on port 50051 and REST on 8080; TLS is terminated at the "
           "ingress (nginx) with certs from Let's Encrypt.\nFor S3 backups we use AWS EC2 instances in eu-west-3; IAM "
           "roles are managed in Terraform modules (tf v1.6)."),
    "fr": ("Incident P2 - VM SRV-PRD-WEB01 inaccessible\nConstat : à 07h42 l'alerte Zabbix a remonté un CPU à 100 % "
           "sur srv-prd-web01, puis le healthcheck HAProxy a sorti le nœud du pool.\nActions : snapshot vSphere, "
           "redémarrage du service php-fpm, purge du cache Redis, vérification des logs nginx (erreurs 502 et 504).\n"
           "Cause probable : un cron mal configuré (backup MySQL lancé en double) a saturé les IOPS du datastore "
           "SAN-02.\nCorrectif : désactivation du cron en double, ajout d'une alerte sur la latence disque, ticket "
           "CHG0012877 pour revoir le planning des sauvegardes.\nImpact : 25 minutes d'indisponibilité de l'extranet "
           "clients ; aucun incident de sécurité, pas de perte de données.\nRédigé par l'ingénieur d'astreinte N2."),
}


@pytest.mark.parametrize("language", sorted(_TECHNICAL))
def test_clean_technical_writing_is_not_flagged(language: str) -> None:
    assert not quality.low_quality(_TECHNICAL[language], language)


def _fake_pdf(data: bytes, filename: str, anonymizer: Any = None, options: Any = None) -> DocumentResult:
    """Faux PDF à couche texte (le texte reçu), même contrat que la façade / fake PDF with a text layer."""
    result = anonymizer.anonymize(data.decode("utf-8"))
    return DocumentResult(result.text, "pdf", dict(result.report), [], {})


@pytest.mark.usefixtures("fake_documents")
def test_the_warning_reaches_pdf_uploads_only_without_refusing(client: TestClient,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    noisy = degrade(CLEAN)
    # Texte collé : jamais d'avertissement (pas d'OCR) / pasted text: never a warning (no OCR).
    text = client.post("/v1/anonymize/text", headers=AUTH_A, json={"text": noisy})
    assert text.status_code == 200 and quality.LOW_QUALITY_WARNING not in text.json()["report"]["warnings"]

    def upload(filename: str) -> dict[str, Any]:
        ticket = client.post("/v1/uploads", headers=AUTH_A, json={"filename": filename}).json()
        put = client.put(ticket["upload_url"].removeprefix("http://testserver"), headers=AUTH_A,
                         content=noisy.encode())
        assert put.status_code == 202
        return client.get(ticket["result_url"].removeprefix("http://testserver"), headers=AUTH_A).json()

    plain = upload("scan.txt")
    assert plain["markdown"] and quality.LOW_QUALITY_WARNING not in plain["report"]["warnings"]
    monkeypatch.setattr(documents, "anonymize_document", _fake_pdf)
    pdf = upload("scan.pdf")
    assert quality.LOW_QUALITY_WARNING in pdf["report"]["warnings"]
    assert quality.LOW_QUALITY_WARNING in pdf["warnings"] and pdf["markdown"]
