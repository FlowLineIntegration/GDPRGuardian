"""Registre des corpus réels : source, licence, nature du gold, pays évalués (outil de dev).

Registry of the real corpora: source, licence, gold type, countries used for evaluation (dev tooling).
Shared by the builders, the evaluator and the summary, so that the published metadata and the commands to
reproduce come from one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Corpus:
    name: str
    title: str
    language: str
    countries: str                 # Anonymizer(countries=...) used for the headline run
    licence: str
    url: str
    revision: str                  # pinned revision, API window or "live API"
    real_text: str                 # "yes", "yes (layout rendered from fields)", "yes (surrogate identifiers)"...
    gold: str                      # how the gold was built
    gold_complete: bool            # False: precision and over-masking are not measurable (unannotated PII)
    measures: str
    cannot_measure: str
    build: str                     # command that builds the JSONL in the cache
    negative_control: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


_CACHE = "--cache <CACHE>"
_FETCH = "python tools/corpus/fetch_real.py " + _CACHE + " --only "

CORPORA: dict[str, Corpus] = {c.name: c for c in (
    Corpus(
        "bodacc_fr", "BODACC, commercial announcements naming natural persons", "fr", "FR",
        "Licence Ouverte / Open Licence (Etalab), DILA", "https://www.data.gouv.fr/datasets/bodacc",
        "Opendatasoft API, publications of 2026-09-01..2026-09-30, fetched 2026-10-25",
        "yes (record values and free text are real; line layout rendered by us after bodacc.fr)",
        "exact by construction: values of the structured fields (surname, given names, address, RCS/RM number) "
        "are rendered at known positions; exact repeats of a person's name elsewhere in the notice are added; "
        "owner addresses in the fixed 'Adresse de l'ancien/du nouveau propriétaire :' phrase are added",
        True,
        "recall of real French names, street addresses and individual-entrepreneur SIREN; precision on the "
        "rendered fields",
        "names of court officers and other people in the free-text judgment complement (left out of precision)",
        "python tools/corpus/build_bodacc.py " + _CACHE + " --per-family 500"),
    Corpus(
        "boamp_fr", "BOAMP, public procurement notices 2022-2023 (IDENTITE schema)", "fr", "FR",
        "Licence Ouverte / Open Licence (Etalab), DILA", "https://www.data.gouv.fr/datasets/boamp",
        "Opendatasoft API, publications of 2022-01..2023-12 (125 per month), fetched 2026-10-25",
        "yes (values and free text are real; 'Label : value' layout rendered by us)",
        "exact by construction: e-mail, phone, fax and street address fields of every party block; contact "
        "person names extracted from the CONTACT/CORRESPONDANT fields by a rule (civility and role removed)",
        True,
        "recall of real e-mails, phone formats ('(+33) 1-23-45-67-89'), street addresses; contact names",
        "contact details written only in free text (left out of precision); most e-mails and addresses belong "
        "to public bodies, not to private persons",
        "python tools/corpus/build_boamp.py " + _CACHE + " --per-month 125"),
    Corpus(
        "parlamint_fr", "ParlaMint-FR 5.0, Assemblée nationale debates 2017-2022 (sample)", "fr", "FR",
        "CC BY 4.0", "http://hdl.handle.net/11356/2004", "ParlaMint-FR.tgz (handle 11356/2004, version 5.0)",
        "yes",
        "speaker labels rendered from the TEI 'who' metadata (exact); in-text mentions = exact matches of the "
        "full name, or civility + surname, of the 1,000+ persons of the corpus person list",
        False,
        "recall of politicians' names in real modern French prose (speaker labels and in-text mentions)",
        "precision (people outside the person list are not annotated); private-person identifiers",
        _FETCH + "parlamint_fr"),
    Corpus(
        "europeana_fr", "Europeana Newspapers NER, French (BnF), historical OCR press", "fr", "FR",
        "CC0 1.0", "https://github.com/EuropeanaNewspapers/ner-corpora",
        "EuropeanaNewspapers/ner-corpora@6bf838d23112c255fd81431b1187ab30ef6c2d90", "yes (noisy 19th-20th c. OCR)",
        "manual (PER, LOC, ORG, IO tags)", True,
        "person-name recall on noisy historical OCR text", "modern identifiers (none in the text)",
        _FETCH + "europeana_fr"),
    Corpus(
        "hipe_newseye_fr", "HIPE-2022 NewsEye French, historical newspapers", "fr", "FR", "CC BY 4.0",
        "https://github.com/hipe-eval/HIPE-2022-data",
        "hipe-eval/HIPE-2022-data@147f5bc3c7fb7e5c6b024a9ffd6503cd019fb9ea (v2.1)", "yes (historical OCR)",
        "manual (pers, loc, org, time, prod; coarse literal layer)", True,
        "person-name recall on historical French press", "modern identifiers (none in the text)",
        _FETCH + "hipe_newseye_fr"),
    *(Corpus(
        f"mapa_{lang}", f"MAPA EUR-Lex legal NER ({lang})", lang, country, "CC BY 4.0",
        "https://huggingface.co/datasets/joelniklaus/mapa", "joelniklaus/mapa@bbb2a0157b760465002fd12a61af81b475cd387a",
        "yes (EU legal texts and judgments, tokenised)", "manual, single annotator", True,
        "names, addresses, dates in real legal prose of each language", "contact or ID numbers (none annotated)",
        _FETCH + f"mapa_{lang}",
        notes=("12 documents per language: a smoke test, not statistical proof",))
      for lang, country in (("fr", "FR"), ("de", "DE"), ("es", "ES"), ("it", "IT"), ("nl", "NL"), ("pt", "PT"))),
    Corpus(
        "meddocan_es", "MEDDOCAN, Spanish clinical case reports (de-identification task)", "es", "ES", "CC BY 4.0",
        "https://zenodo.org/records/4279323", "Zenodo 10.5281/zenodo.4279323 (meddocan.zip)",
        "yes (real published case reports) with SURROGATE identifiers added by the corpus authors",
        "manual gold (29 PHI types), inter-annotator agreement reported at 98%", True,
        "recall of names, street addresses, e-mails, phones and IDs in Spanish clinical text",
        "real identifiers (the personal data are fictitious surrogates in a header block)",
        _FETCH + "meddocan_es"),
    Corpus(
        "german_ler_de", "German LER, federal court decisions (test split)", "de", "DE", "CC BY 4.0",
        "https://huggingface.co/datasets/elenanereiss/german-ler",
        "elenanereiss/german-ler@405b6923dfd2299da3d76a68220ee15a95bc1eab", "yes (court decisions, tokenised)",
        "manual (19 fine classes: person, judge, lawyer, street, city, country, organisation, court, law...)", True,
        "names of judges, lawyers and persons, street names in real German legal prose",
        "parties' identities (already pseudonymised by the courts); contact or ID numbers",
        _FETCH + "german_ler_de"),
    Corpus(
        "tab_en", "TAB, Text Anonymization Benchmark (ECHR, English, test split)", "en", "FR", "MIT",
        "https://github.com/NorskRegnesentral/text-anonymization-benchmark",
        "NorskRegnesentral/text-anonymization-benchmark@558e09e26d6b36f5f78440074e6a233946d98bd9",
        "yes (ECHR judgments)", "manual, DIRECT and QUASI mentions of the first annotator", True,
        "person-name recall in English legal prose (no English pack: FR pack + international detectors)",
        "dates, places and organisations are kept by policy", _FETCH + "tab_en"),
    Corpus(
        "judilibre_fr", "Judilibre (Cour de cassation, cours d'appel, tribunaux judiciaires), negative control",
        "fr", "FR", "Licence Ouverte 2.0 (etalab-2.0)", "https://huggingface.co/datasets/antoinejeannot/jurisprudence",
        "antoinejeannot/jurisprudence@8019db1080cf6dc8a34d73ee44d704a8e90b558e (mirror of the Judilibre API)",
        "yes (decisions pseudonymised by the courts before publication)",
        "none: parties are already replaced by '[X]'-style placeholders; detections are reviewed by hand", False,
        "what the engine still masks in already-pseudonymised legal text: residual identifiers (magistrates', "
        "lawyers' names, addresses) versus false positives",
        "recall (no gold)", _FETCH + "judilibre_fr", negative_control=True),
)}
