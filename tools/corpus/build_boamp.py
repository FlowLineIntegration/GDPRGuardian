"""Corpus BOAMP à gold exact (Licence Ouverte) / exact-gold BOAMP corpus (dev tooling, never shipped).

Source: DILA, Bulletin officiel des annonces des marchés publics, open-data API (Opendatasoft), Licence Ouverte /
Open Licence 2.0. Notices published 2022-2023 in the "IDENTITE" XML schema (national FNS and MAPA notices, and
European JOUE notices before eForms); the eForms schema used since 2024 is not converted.

Text: the notice's "donnees" tree is rendered in its own order as "Label : value" lines (labels in French, ours),
which keeps every word of the notice. HTML entities of the source ("&quot;", "&#xE9;") are decoded and the C1
controls left from Windows-1252 text ("\\x92") are mapped back to their characters. Long free-text values (over 80
characters: description, additional information, selection criteria...) are marked "ignore" (left out of
precision), because they may hold contact details that no field describes.

Gold (exact by construction, positions known while rendering):
- EMAIL (MEL), PHONE (TEL, FAX), ADDRESS (street + postal code + city) of every party block (buyer, contact
  addresses, review bodies, awardees), whoever owns them: the engine masks e-mails, phones and street addresses
  without knowing the owner; also the "Lieu ouverture offres" field when it holds a street type or a postal box;
- PERSON: the name part of CONTACT / CORRESPONDANT when it looks like a person's name (civility stripped, role
  after a comma or dash dropped, role words rejected); an awardee written with a civility, or as "SURNAME
  Given-name" without one (two or three words, one of them an Insee given name, no organisation word); exact
  repeats of these values elsewhere are added;
- kept by policy: ORG (organisation names), ORG_ID (SIRET), LOCATION (postal code + city without street), URL of
  organisations is left unlabelled.

Privacy: the output stays in the cache folder outside the repository, for local evaluation only.

Usage:
    python tools/corpus/build_boamp.py --cache DIR [--per-month 125] [--start 2022-01] [--end 2023-12]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.corpus.real_common import (  # noqa: E402
    TextBuilder,
    check_outside_repo,
    corpus_path,
    default_cache,
    find_all,
    http_json,
    log,
    raw_dir,
    record,
    update_manifest,
    write_jsonl,
)

from gdprguardian._text import fold  # noqa: E402

API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
FREE_TEXT_MIN = 80
PARTY_KEYS = {"DENOMINATION", "ADRESSE", "CP", "VILLE", "TEL", "FAX", "MEL", "CONTACT", "CORRESPONDANT"}
SECTION_LABELS = {
    "IDENTITE": "Identification de l'organisme qui passe le marché",
    "OBJET": "Objet du marché",
    "PROCEDURE": "Procédure",
    "CONDITION_DELAI": "Délais",
    "CONDITION_PARTICIPATION": "Conditions de participation",
    "CONDITION_RELATIVE_MARCHE": "Conditions relatives au marché",
    "CONDITION_ADMINISTRATIVE": "Conditions administratives",
    "RENSEIGNEMENTS_COMPLEMENTAIRES": "Renseignements complémentaires",
    "ADRESSES_COMPLEMENTAIRES": "Adresses complémentaires",
    "ATTRIBUTION": "Attribution",
    "DECISION": "Décision",
    "TITULAIRE": "Titulaire",
    "LOTS": "Lots",
    "LOT": "Lot",
    "RECTIF": "Rectificatif",
}
FIELD_LABELS = {
    "TITRE_MARCHE": "Intitulé du marché", "OBJET_COMPLET": "Description", "RENS_COMPLEMENT": "Autres informations",
    "RECEPT_OFFRES": "Date limite de réception des offres", "CAP_ECO": "Capacité économique et financière",
    "CAP_TECH": "Capacité technique et professionnelle", "SITUATION_JURIDIQUE": "Situation juridique",
    "DESCRIPTION": "Description", "INTITULE": "Intitulé", "NUM": "Numéro", "NUM_LOT": "Lot n°",
    "LIEU_PRINCIPAL": "Lieu principal d'exécution", "DUREE_MOIS": "Durée (mois)", "PRINCIPAL": "Code CPV",
    "URL_PROFIL_ACHETEUR": "Profil d'acheteur", "URL_DOCUMENT": "Documents", "URL": "Adresse internet",
    "DATE_ATTRIBUTION": "Date d'attribution", "NB_OFFRE_RECU": "Nombre d'offres reçues",
    "REF_MARCHE": "Référence", "INFO_COMPLEMENTAIRE": "Informations complémentaires",
    "MODIFICATION": "Modification", "CRITERE_SELECTION": "Critères de sélection",
}
CIVILITY = re.compile(r"^(?:M\.|Mme\.?|Mlle\.?|Mr\.?|Monsieur|Madame|Mademoiselle|Me|Maître|Dr\.?|Docteur)\s+",
                      re.IGNORECASE)
ROLE_WORDS = {
    "maire", "président", "presidente", "présidente", "president", "directeur", "directrice", "service", "services",
    "responsable", "pôle", "pole", "direction", "département", "departement", "achats", "achat", "marchés",
    "marches", "marché", "commande", "publique", "cellule", "secrétariat", "secretariat", "mairie", "le", "la",
    "les", "l'", "des", "du", "au", "aux", "et", "en", "pour", "chef", "chargé", "chargée", "adjoint", "adjointe",
    "général", "générale", "general", "generale", "gestionnaire", "juridique", "technique", "techniques",
    "administratif", "administrative", "accueil", "bureau", "agence", "conseil", "conseiller", "ingénieur",
    "commune", "ville", "communauté", "syndicat", "contact", "affaires", "travaux", "voir", "dossier",
    "acheteur", "acheteuse", "ordonnateur", "délégué", "déléguée", "représentant", "représentante", "monsieur",
    "madame", "comptable", "trésorier", "secrétaire", "élu", "élus", "dga", "dgs", "dst", "cabinet",
    "unité", "unite", "hôtel", "hotel", "centre", "mission", "division", "plateforme", "guichet", "équipe",
    "equipe", "sous-directeur", "sous-directrice", "messieurs", "mesdames",
    "service-marches", "standard", "régie", "regie", "délégation", "delegation", "sdis", "saf", "intendance",
    "région", "region", "agglomération", "agglomeration", "métropole", "metropole", "université", "universite",
    "institut", "hôpital", "hopital", "chu", "ministère", "ministere", "préfecture", "prefecture", "tribunal",
    "greffe", "office", "établissement", "etablissement", "groupement", "société", "societe", "sas", "sarl",
    "association", "fondation", "cnrs", "collège", "lycée", "école", "ecole", "académie", "rectorat", "port",
}
# Une adresse « postale » a un numéro de voie ou de boîte (pas un code postal seul) ou un type de voie.
# A street address has a house or box number (not a bare 5-digit postcode) or a street type.
STREET = re.compile(r"(?<!\d)\d{1,4}(?!\d)|\b(?:rue|avenue|av|bd|boulevard|place|pl|chemin|route|allée|allee|quai|"
                    r"impasse|cours|square|esplanade|parvis|rond-point|voie|lieu-dit|hameau|zone|za|zi|zac|bp|cs|"
                    r"parc)\b", re.IGNORECASE)
NAME_TOKEN = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’.-]*$")
EMAIL_IN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_IN = re.compile(r"(?:\(\+\d{2}\)\s?|\+\d{2}\s?)?\d{1,2}(?:[\s.-]?\d{2}){4}")
CONTACT_SPLIT = re.compile(r",|;|/|\(|\)|\s[-–]\s|\s(?:et|ou)\s|:|\n")
PARTICLES = {"de", "du", "des", "le", "la", "van", "von", "da", "di", "d'", "ben", "el"}
CIVILITY_WORDS = re.compile(r"^(?:M\.|Mme\.?|Mlle\.?|Mr\.?|MM\.|Mmes|Monsieur|Madame|Mademoiselle|Messieurs|"
                            r"Mesdames|Me|Maître|Dr\.?|Docteur)\s+", re.IGNORECASE)
# Champ d'adresse hors des blocs de partie (« Lieu ouverture offres ») : une adresse seulement avec un type de
# voie ou une boîte postale, jamais sur un simple nombre. Address field outside the party blocks: a street type
# or a postal box is required, never a bare number.
STREET_WORD = re.compile(r"\b(?:rue|avenue|av|bd|boulevard|place|pl|chemin|route|allée|allee|quai|impasse|cours|"
                         r"square|esplanade|parvis|rond-point|voie|lieu-dit|hameau|zone|za|zi|zac|bp|cs|parc)\b",
                         re.IGNORECASE)
ADDRESS_FIELDS = ("LIEU_OUVERTURE_OFFRES",)
# Titulaire personne physique écrit « NOM Prénom » sans civilité : deux à trois mots alphabétiques, dont un prénom
# du fichier Insee (jamais un mot courant), sans mot d'organisation. Sole trader written "SURNAME Given-name"
# without civility: two or three alphabetic words, one of them an Insee given name (never a common word).
SOLE_TRADER_MIN_RANK = 6  # au moins 64 naissances / at least 64 births
_SOLE_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]{1,30}")
_CP1252 = {i: bytes([i]).decode("cp1252", errors="ignore") for i in range(0x80, 0xA0)}


def clean(value: str) -> str:
    """Entités HTML décodées (« &amp;quot; », « &#xE9; ») et caractères C1 de Windows-1252 (« \\x92 » -> « ’ »).

    Decodes HTML entities until stable (the source sometimes escapes twice) and maps the C1 controls that the
    source left from Windows-1252 text to their characters; nothing else changes.
    """
    for _ in range(3):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    return value.translate({k: v for k, v in _CP1252.items() if v}) if any(
        "\x80" <= ch <= "\x9f" for ch in value) else value


def decoded(obj: Any) -> Any:
    """`clean` sur chaque chaîne de l'arbre `donnees` / `clean` on every string of the tree."""
    if isinstance(obj, str):
        return clean(obj)
    if isinstance(obj, list):
        return [decoded(v) for v in obj]
    if isinstance(obj, dict):
        return {k: decoded(v) for k, v in obj.items()}
    return obj


@cache
def _lexicon_sets() -> tuple[dict[str, int], frozenset[str], frozenset[str]]:
    """(prénoms Insee hors mots courants -> rang, mots courants, mots d'organisation) / given names, words, org words.

    Lexique du paquet : il ne décide que du libellé (PERSON ou ORG) d'un champ entier, jamais des bornes.
    The package lexicon only decides the label of a whole field value, never its boundaries.
    """
    from gdprguardian.heuristics import _vocab as V
    from gdprguardian.heuristics._lexicon import AMB_NONE, ambiguity, given_rank, lexicon
    lex = lexicon()
    given = {k: given_rank(c) for k, c in lex.names.items()
             if given_rank(c) and ambiguity(c) == AMB_NONE and k not in lex.words}
    org = frozenset(V.ORG_KEYWORDS | V.LEGAL_FORM_KEYS | V.ORG_FAMILY | {fold(w) for w in ROLE_WORDS})
    return given, lex.words, org


def sole_trader(name: str) -> bool:
    """« DUPONT JEAN », « DUPONT Jean Paul » : titulaire personne physique dans l'ordre Nom Prénom de l'Insee.

    Sole trader written in the Insee "SURNAME Given-name(s)" order: a surname in capitals that is neither a given
    name, a common word nor an organisation word, then one or two unambiguous Insee given names. "LÉON GROSSE"
    (given name first) stays an organisation: company names often take a founder's name in that order.
    """
    words = name.split()
    if not 2 <= len(words) <= 3 or not all(_SOLE_WORD.fullmatch(w) for w in words):
        return False
    given, common, org = _lexicon_sets()
    surname, *firsts = [fold(w) for w in words]
    if not words[0].isupper() or len(surname) < 4 or surname in given or surname in common or surname in org:
        return False
    return all(given.get(f, 0) >= SOLE_TRADER_MIN_RANK and f not in org for f in firsts)


def person_spans(value: str) -> list[tuple[int, int, str]]:
    """Personnes, e-mails et téléphones d'un champ CONTACT / persons, e-mails, phones in a CONTACT field.

    "Anne-Marie EXEMPLE" -> one PERSON; "Paule TESTEUR, Directrice" -> "Paule TESTEUR";
    "M. Le Président, Jean Essai" -> "Jean Essai"; "Mesdames ESSAI Anne et Lucie TEST" -> two;
    "Mme ESSAI x.y@z.fr" -> PERSON "ESSAI" and EMAIL; "M. le Maire", "Service des marchés" -> none.
    A chunk keeps its longest prefix of capitalised name tokens (role words stop it); two name tokens, or one
    after a civility, make a PERSON.
    """
    out: list[tuple[int, int, str]] = []
    masked = list(value)
    for regex, label in ((EMAIL_IN, "EMAIL"), (PHONE_IN, "PHONE")):
        for m in regex.finditer("".join(masked)):
            out.append((m.start(), m.end(), label))
            masked[m.start():m.end()] = " " * (m.end() - m.start())
    clean = "".join(masked)
    pos = 0
    for piece in [*CONTACT_SPLIT.split(clean)]:
        start = clean.find(piece, pos)
        pos = start + len(piece)
        civ = CIVILITY_WORDS.match(piece.lstrip())
        offset = start + (len(piece) - len(piece.lstrip())) + (civ.end() if civ else 0)
        rest = clean[offset:pos]
        names: list[tuple[int, int]] = []
        for tok in re.finditer(r"\S+", rest):
            word = tok.group(0)
            if word.lower().strip(".,") in ROLE_WORDS:
                break
            if word.lower() in PARTICLES and names:
                continue
            if not NAME_TOKEN.match(word) or len(word.rstrip(".")) < 2:
                break
            names.append((offset + tok.start(), offset + tok.end()))
        if len(names) >= 2 or (len(names) == 1 and civ):
            out.append((names[0][0], names[-1][1], "PERSON"))
    return sorted(out)


def humanise(key: str) -> str:
    return FIELD_LABELS.get(key) or key.replace("_", " ").capitalize()


class Renderer:
    def __init__(self) -> None:
        self.tb = TextBuilder()
        self.values: list[tuple[str, str]] = []  # (value, label) to look for elsewhere

    def labelled_line(self, prefix: str, value: str) -> None:
        """« Préfixe : valeur » avec les personnes, e-mails et téléphones de la valeur annotés."""
        tb = self.tb
        tb.add(prefix)
        pos = 0
        for start, end, label in person_spans(value):
            if start < pos:
                continue
            tb.add(value[pos:start])
            tb.add(value[start:end], label)
            self.values.append((value[start:end], label))
            pos = end
        tb.add(value[pos:] + "\n")

    def party(self, obj: dict[str, Any], title: str) -> None:
        tb = self.tb
        tb.add(f"{title}\n")
        typ = obj.get("TYPE")
        if isinstance(typ, dict) and typ:
            tb.add("Type : " + ", ".join(humanise(k) for k in typ) + "\n")
        name = obj.get("DENOMINATION")
        if isinstance(name, str) and CIVILITY_WORDS.match(name.strip()):
            # « Maître Jeanne EXEMPLE » : un titulaire personne physique / an individual awardee
            self.labelled_line("Nom complet : ", name.strip())
        elif isinstance(name, str) and title == SECTION_LABELS["TITULAIRE"] and sole_trader(name.strip()):
            # « EXEMPLE Jeanne » sans civilité : titulaire personne physique / sole trader without civility
            tb.line("Nom complet : ", name, "PERSON")
            self.values.append((name.strip(), "PERSON"))
        else:
            tb.line("Nom complet : ", name, "ORG")
        ident = obj.get("CODE_IDENT_NATIONAL")
        if isinstance(ident, str) and ident.strip():
            digits = sum(ch.isdigit() for ch in ident)
            label = "ORG_ID" if digits >= 9 else ("ADDRESS" if STREET.search(ident) else None)
            tb.line("Numéro national d'identification : ", ident, label)
        for key, prefix in (("CORRESPONDANT", "Correspondant : "), ("CONTACT", "Point de contact : ")):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                self.labelled_line(prefix, value.strip())
        street = obj.get("ADRESSE") if isinstance(obj.get("ADRESSE"), str) else ""
        street = street.strip()
        city = " ".join(str(obj.get(k)).strip() for k in ("CP", "VILLE")
                        if isinstance(obj.get(k), str) and obj.get(k).strip())
        if street or city:
            text = f"{street}, {city}" if street and city else (street or city)
            tb.line("Adresse : ", text, "ADDRESS" if STREET.search(street) else "LOCATION")
        tb.line("Pays : ", obj.get("PAYS"))
        for key, prefix, label in (("TEL", "Tél : ", "PHONE"), ("FAX", "Fax : ", "PHONE"),
                                   ("MEL", "Courriel : ", "EMAIL")):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                tb.line(prefix, value, label)
                self.values.append((value.strip(), label))
        for key in ("URL", "URL_PROFIL_ACHETEUR", "URL_DOCUMENT"):
            tb.line(f"{humanise(key)} : ", obj.get(key))
        rest = {k: v for k, v in obj.items() if k not in PARTY_KEYS | {"TYPE", "CODE_IDENT_NATIONAL", "PAYS", "URL",
                                                                       "URL_PROFIL_ACHETEUR", "URL_DOCUMENT"}}
        self.walk(rest, 1)

    def walk(self, obj: Any, depth: int, key: str = "") -> None:
        tb = self.tb
        if depth > 8:
            return
        if isinstance(obj, dict):
            if any(isinstance(obj.get(k), str) for k in ("DENOMINATION", "ADRESSE", "MEL", "TEL", "CONTACT")):
                self.party(obj, SECTION_LABELS.get(key, humanise(key) if key else "Organisme"))
                return
            if "#text" in obj:
                unit = obj.get("@DEVISE") or obj.get("@POIDS") or ""
                tb.line(f"{humanise(key)} : ", f"{obj['#text']} {unit}".strip())
                return
            if key and key in SECTION_LABELS:
                tb.add(f"{SECTION_LABELS[key]}\n")
            for k, v in obj.items():
                if k.startswith("@"):
                    continue
                self.walk(v, depth + 1, k)
        elif isinstance(obj, list):
            for item in obj:
                self.walk(item, depth + 1, key)
        elif isinstance(obj, str):
            value = obj.strip()
            if not value:
                return  # drapeaux vides (XXX_OUI / XXX_NON) / empty flag elements
            if key.startswith("DATE") or key in ("RECEPT_OFFRES",):
                tb.line(f"{humanise(key)} : ", value, "DATE")
            elif key in ADDRESS_FIELDS and len(value) <= FREE_TEXT_MIN and STREET_WORD.search(value):
                tb.line(f"{humanise(key)} : ", value, "ADDRESS")  # « Lieu ouverture offres » / address field
            else:
                tb.line(f"{humanise(key)} : ", value, ignore=len(value) > FREE_TEXT_MIN)
        elif obj is not None:
            tb.line(f"{humanise(key)} : ", str(obj))

    def repeats(self) -> list[tuple[int, int, str, str]]:
        text = self.tb.text
        out: list[tuple[int, int, str, str]] = []
        for value, label in self.values:
            if len(value) >= 4:
                out.extend((s, e, label, "repeat") for s, e in find_all(text, value))
        return out


def render(row: dict[str, Any]) -> dict[str, Any] | None:
    try:
        donnees = json.loads(row["donnees"]) if isinstance(row.get("donnees"), str) else row.get("donnees")
    except json.JSONDecodeError:
        return None
    if not isinstance(donnees, dict) or "IDENTITE" not in donnees:
        return None
    donnees = decoded(donnees)
    r = Renderer()
    tb = r.tb
    deps = row.get("code_departement") or []
    tb.add(f"Avis n° {row.get('idweb')}\n{clean(row.get('famille_libelle') or '')} - "
           f"{clean(row.get('nature_libelle') or '')}\n")
    tb.line("Département(s) de publication : ", ", ".join(deps) if isinstance(deps, list) else str(deps))
    tb.line("Date de parution : ", row.get("dateparution"), "DATE")
    tb.line("Procédure : ", clean(row.get("procedure_libelle") or ""))
    r.walk(donnees, 0)
    text = tb.text
    meta = {"family": row.get("famille"), "nature": row.get("nature"), "date": row.get("dateparution"),
            "schema": row.get("source_schema")}
    return record(f"boamp:{row.get('idweb')}", "boamp_fr", "fr", text, [*tb.spans, *r.repeats()], tb.ignore, meta)


def months(start: str, end: str) -> Iterator[tuple[str, str]]:
    year, month = int(start[:4]), int(start[5:7])
    last = (int(end[:4]), int(end[5:7]))
    while (year, month) <= last:
        nxt = (year + (month == 12), 1 if month == 12 else month + 1)
        yield f"{year:04d}-{month:02d}-01", f"{nxt[0]:04d}-{nxt[1]:02d}-01"
        year, month = nxt


def fetch(cache: Path, per_month: int, start: str, end: str) -> list[dict[str, Any]]:
    folder = raw_dir(cache, "boamp")
    rows: list[dict[str, Any]] = []
    for first, nxt in months(start, end):
        path = folder / f"{first[:7]}_{per_month}.json"
        if path.exists():
            kept = json.loads(path.read_text(encoding="utf-8"))
        else:
            kept = []
            offset = 0
            where = f"dateparution >= date'{first}' and dateparution < date'{nxt}'"
            while len(kept) < per_month and offset < 1000:
                page = http_json(API, {"limit": 100, "offset": offset, "where": where, "order_by": "idweb"})
                batch = page.get("results") or []
                kept.extend(r for r in batch if str(r.get("donnees") or "").startswith('{"IDENTITE"'))
                offset += 100
                if len(batch) < 100:
                    break
            kept = kept[:per_month]
            path.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
        log(f"boamp {first[:7]}: {len(kept)} notices")
        rows.extend(kept)
    return rows


def build(cache: Path, per_month: int, start: str, end: str) -> dict[str, Any]:
    rows = fetch(cache, per_month, start, end)

    def gen() -> Iterator[dict[str, Any]]:
        for row in rows:
            rec = render(row)
            if rec is not None:
                yield rec

    info = write_jsonl(corpus_path(cache, "boamp_fr"), gen())
    info.update({"source": "DILA BOAMP (API Opendatasoft), IDENTITE schema",
                 "licence": "Licence Ouverte / Open Licence", "window": [start, end], "per_month": per_month})
    update_manifest(cache, "boamp_fr", info)
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", type=Path, default=default_cache(), help="cache folder, outside the repository")
    parser.add_argument("--per-month", type=int, default=125, help="notices per month")
    parser.add_argument("--start", default="2022-01", help="first month (YYYY-MM)")
    parser.add_argument("--end", default="2023-12", help="last month (YYYY-MM)")
    args = parser.parse_args()
    cache = check_outside_repo(args.cache)
    info = build(cache, args.per_month, args.start, args.end)
    log(f"boamp_fr: {info['documents']} documents, {info['mentions']} gold spans {info['labels']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
