"""Corpus BODACC à gold exact (Licence Ouverte) / exact-gold BODACC corpus (dev tooling, never shipped).

Source: DILA, Bulletin officiel des annonces civiles et commerciales, open-data API (Opendatasoft), Licence
Ouverte / Open Licence 2.0. Only announcements naming at least one natural person ("typePersonne": "pp") are kept.

Text: each announcement is rendered with the labels and field order of its detail page on bodacc.fr ("Annonce
déposée au", "n° RCS", "Nom", "Prénom", "Adresse", "Établissement(s)", "Complément Jugement"...). The words are
those of the record; the line layout is ours.

Gold (exact by construction, positions known while rendering):
- PERSON: surname, given names, usage name and pseudonym of every natural person (debtor, owner, previous owner);
  later exact repeats of a surname, or of "given name + surname", in the free-text fields are added as well;
- ADDRESS: every rendered street address (natural person, establishment, company seat);
- ID: RCS / RM number of a natural person (an individual entrepreneur's SIREN identifies that person);
- kept by policy: ORG (company names, registry court), ORG_ID (company SIREN), LOCATION (address without street),
  DATE, OTHER (nationality).
Free-text fields (judgment complement, comments, oppositions...) name court-appointed officers and other people
that no field describes: they are marked "ignore" (left out of precision); gold spans inside them still count.

Privacy: the output stays in the cache folder outside the repository, for local evaluation only.

Usage:
    python tools/corpus/build_bodacc.py --cache DIR [--per-family 500] [--start 2026-09-01] [--end 2026-09-30]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections.abc import Iterator
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

API = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"
FAMILIES = ("Procédures collectives", "Créations", "Immatriculations", "Ventes et cessions", "Modifications diverses",
            "Radiations")
PP_FILTER = 'listepersonnes like "*\\"pp\\"*"'
MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre")
ADDRESS_KEYS = ("numeroVoie", "indiceRepetition", "typeVoie", "nomVoie", "complGeographique", "localite", "BP")
FREE_TEXT_LABELS = {  # clé -> libellé affiché ; valeurs en texte libre (zone ignorée) / free text (ignored zone)
    "complementJugement": "Complément Jugement : ",
    "descriptif": "Commentaires : ",
    "opposition": "Oppositions : ",
    "declarationCreance": "Déclaration des créances : ",
    "commentaire": "Commentaires : ",
}
DATE_LABELS = {
    "dateImmatriculation": "A dater du : ",
    "dateCommencementActivite": "Date de commencement d'activité : ",
    "dateCessationActivitePP": "Date de cessation d'activité : ",
    "dateEffet": "Date d'effet : ",
    "dateRadiation": "Date de radiation : ",
}


def fr_date(iso: str | None) -> str | None:
    """« 2026-10-21 » -> « 21 octobre 2026 » ; autre forme gardée telle quelle / other forms kept as is."""
    if not iso or len(iso) < 10 or iso[4] != "-" or iso[7] != "-":
        return iso
    year, month, day = iso[:4], iso[5:7], iso[8:10]
    try:
        return f"{int(day)} {MONTHS[int(month) - 1]} {year}"
    except (ValueError, IndexError):
        return iso


def slash_date(iso: str | None) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso and len(iso) >= 10 else (iso or "")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def flat(value: Any) -> str:
    """Valeur textuelle ; une liste devient « a, b » / text value; a list becomes "a, b"."""
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if v is not None and str(v).strip())
    return str(value or "").strip()


# « Adresse de l'ancien / du nouveau propriétaire : <voie> <code postal> <ville>. » (formule des greffes)
_OWNER_ADDRESS = re.compile(
    r"Adresse (?:de l['’]|du |des |d['’])?(?:ancien|nouveau|anciens|nouveaux) propriétaires?\s*:\s*"
    r"(?P<addr>[^:;]{3,160}?\b\d{5}\s+[^\W\d][^.,;:()]*?)(?=\s*(?:[.;,]|\s-\s|$))")


# Mention « (EI) » / « EI » accolée au nom d'un entrepreneur individuel / individual-entrepreneur marker.
_EI_SUFFIX = re.compile(r"\s*\(\s*EI\s*\)\s*$|\s+EI\s*$")


def unaccent(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


def parse(value: Any) -> Any:
    if isinstance(value, str) and value[:1] in "{[":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def address_parts(addr: dict[str, Any]) -> tuple[str, bool]:
    """Adresse rendue sur une ligne, et vrai si elle a une voie / one-line address, True if it has a street."""
    street = " ".join(str(addr[k]).strip() for k in ADDRESS_KEYS if addr.get(k) and str(addr[k]).strip())
    city = " ".join(str(addr[k]).strip() for k in ("codePostal", "ville") if addr.get(k) and str(addr[k]).strip())
    pays = str(addr.get("pays") or "").strip()
    text = " ".join(p for p in (street, city, pays if pays and pays.lower() != "france" else "") if p)
    has_street = bool(addr.get("nomVoie") or addr.get("numeroVoie") or addr.get("complGeographique")
                      or addr.get("localite"))
    return text, has_street


class Renderer:
    """Rend une annonce comme sa page bodacc.fr, en notant les zones / renders one announcement, tracking spans."""

    def __init__(self) -> None:
        self.tb = TextBuilder()
        self.names: list[tuple[str, str]] = []  # (surname, given names) of natural persons, for repeats
        self.trade_zones: list[tuple[int, int]] = []  # "Nom commercial" / "Enseigne" values

    def name_line(self, prefix: str, value: str) -> None:
        """« Nom : X (EI) » : seul le nom est annoté, pas la mention EI / only the name is labelled, not "(EI)"."""
        if not value:
            return
        m = _EI_SUFFIX.search(value)
        head, tail = (value[: m.start()], value[m.start():]) if m and m.start() > 0 else (value, "")
        self.tb.add(prefix)
        self.tb.add(head, "PERSON")
        self.tb.add(tail + "\n")

    def trade_line(self, prefix: str, value: Any) -> None:
        value = flat(value)
        if value:
            self.tb.add(prefix)
            self.trade_zones.append(self.tb.add(value))
            self.tb.add("\n")

    def address(self, prefix: str, addr: Any) -> None:
        if not isinstance(addr, dict):
            return
        text, has_street = address_parts(addr)
        if text:
            self.tb.line(prefix, text, "ADDRESS" if has_street else "LOCATION")

    def person(self, pers: dict[str, Any]) -> None:
        tb = self.tb
        natural = pers.get("typePersonne") == "pp"
        imm = pers.get("numeroImmatriculation")
        if isinstance(imm, dict) and imm.get("numeroIdentification"):
            tb.add("n° RCS : ")
            tb.add(str(imm["numeroIdentification"]), "ID" if natural else "ORG_ID")
            court = imm.get("nomGreffeImmat")
            tb.add(f" {imm.get('codeRCS') or 'RCS'}" + (" " if court else ""))
            if court:
                tb.add(str(court), None if "non précisé" in str(court).lower() else "LOCATION")
            tb.add("\n")
        rm = pers.get("inscriptionRM")
        if isinstance(rm, dict) and rm.get("numeroIdentificationRM"):
            tb.add("n° RM : ")
            tb.add(str(rm["numeroIdentificationRM"]), "ID" if natural else "ORG_ID")
            tb.add(f" {rm.get('codeRM') or 'RM'} {rm.get('numeroDepartement') or ''}".rstrip() + "\n")
        if not imm and not rm and pers.get("nonInscrit") is not None:
            tb.add("RCS : Non Inscrit\n")
        if natural:
            surname = flat(pers.get("nom"))
            given = flat(pers.get("prenom"))
            self.name_line("Nom : ", surname)
            if given:
                tb.add("Prénom : ")
                for i, part in enumerate(given.split(",")):
                    if i:
                        tb.add(",")
                    tb.add(part, "PERSON")
                tb.add("\n")
            usage = flat(pers.get("nomUsage"))
            self.name_line("Nom d'usage : ", usage)
            tb.line("Nationalité : ", flat(pers.get("nationalite")), "OTHER")
            pseudo = flat(pers.get("pseudonyme"))
            tb.line("Pseudonyme : ", pseudo, "PERSON")
            self.trade_line("Nom commercial : ", pers.get("nomCommercial"))
            usage = _EI_SUFFIX.sub("", usage).strip()
            surname = _EI_SUFFIX.sub("", surname).strip()
            if surname:
                self.names.append((surname, given))
            if usage and usage != surname:
                self.names.append((usage, given))
            if pseudo:
                self.names.append((pseudo, ""))
        else:
            tb.line("Dénomination : ", pers.get("denomination"), "ORG")
            tb.line("Forme : ", pers.get("formeJuridique"))
            tb.line("Nom commercial : ", pers.get("nomCommercial"))
            tb.line("Sigle : ", pers.get("sigle"), "ORG")
        if natural:
            self.trade_line("Enseigne : ", pers.get("enseigne"))
        else:
            tb.line("Enseigne : ", pers.get("enseigne"))
        tb.line("Activité : ", pers.get("activite"))
        self.address("Adresse : ", pers.get("adressePP"))
        self.address("Adresse du siège social : ", pers.get("adresseSiegeSocial"))
        self.address("Adresse : ", pers.get("adresse"))
        capital = pers.get("capital")
        if isinstance(capital, dict) and capital.get("montantCapital"):
            tb.add(f"Capital : {capital.get('montantCapital')} {capital.get('devise') or ''}".rstrip() + "\n")
        for admin in as_list(pers.get("administration")):
            tb.line("Administration : ", admin, ignore=True)

    def free(self, obj: Any, depth: int = 0) -> None:
        """Champs d'acte, de jugement, de modification : dates, catégories, texte libre / act fields."""
        if not isinstance(obj, dict) or depth > 3:
            return
        tb = self.tb
        for key, value in obj.items():
            value = parse(value)
            if isinstance(value, dict):
                if key == "publiciteLegale":
                    when = fr_date(value.get("date"))
                    tb.line("Publication légale : ", f"{value.get('titre') or ''}" + (f" du {when}" if when else ""))
                else:
                    self.free(value, depth + 1)
            elif isinstance(value, list):
                for item in value:
                    self.free(item if isinstance(item, dict) else {key: item}, depth + 1)
            elif value is None or str(value).strip() == "":
                continue
            elif key in FREE_TEXT_LABELS:
                tb.line(FREE_TEXT_LABELS[key], value, ignore=True)
            elif key in DATE_LABELS:
                tb.line(DATE_LABELS[key], fr_date(str(value)), "DATE")
            elif key.lower().startswith("categorie") or key in ("nature",):
                tb.line("", value)
            elif key in ("type", "famille"):
                continue
            elif key.lower().startswith("date"):
                tb.line(f"{key} : ", fr_date(str(value)), "DATE")
            else:
                tb.line(f"{key} : ", value, ignore=True)

    def repeats(self) -> list[tuple[int, int, str, str]]:
        """Répétitions exactes des noms ailleurs dans l'annonce / exact name repeats elsewhere in the notice.

        Surname (as written or upper-case, 3 characters or more) and "given name + surname" in both orders,
        case-sensitive with word boundaries; a repeat that overlaps a field span is dropped by `resolve_spans`.
        """
        text = self.tb.text
        out: list[tuple[int, int, str, str]] = []
        for surname, given in self.names:
            forms = {surname, surname.upper()}
            first = given.split(",")[0].strip()
            if first and len(first) >= 2:
                forms |= {f"{first} {surname}", f"{surname} {first}", f"{first} {surname.upper()}",
                          f"{surname.upper()} {first}"}
            for form in forms:
                if len(form) >= 3:
                    out.extend((s, e, "PERSON", "repeat") for s, e in find_all(text, form))
        # Noms et prénoms dans un nom commercial ou une enseigne (« CHEZ MARIE », « Dupont Services »),
        # toutes casses, accents ou non / names inside a trade name, any case, with or without accents.
        for start, end in self.trade_zones:
            zone = text[start:end]
            for surname, given in self.names:
                for part in [surname, *(g.strip() for g in given.split(","))]:
                    for token in {part, *part.split()} if part else ():
                        if len(token) < 3:
                            continue
                        for form in {token, token.upper(), token.title(), unaccent(token).upper()}:
                            out.extend((start + s, start + e, "PERSON", "trade_name")
                                       for s, e in find_all(zone, form))
        return out


def render(rec: dict[str, Any]) -> dict[str, Any] | None:
    r = Renderer()
    tb = r.tb
    published = slash_date(rec.get("dateparution"))
    tb.add(f"Annonce n° {rec.get('numeroannonce')} du BODACC {rec.get('publicationavis') or 'A'} n° "
           f"{rec.get('parution')} publié le {published}\n")
    jugement = parse(rec.get("jugement"))
    heading = jugement.get("famille") if isinstance(jugement, dict) and jugement.get("famille") else (
        rec.get("familleavis_lib") or "")
    tb.add(f"{heading}\nPublié le {published}\n{rec.get('typeavis_lib') or ''}\n")
    tb.add("Annonce déposée au : ")
    tb.add(str(rec.get("tribunal") or ""), "ORG")
    tb.add(f"\nRéférence de publication : Bodacc {rec.get('publicationavis') or 'A'} n° {rec.get('parution')} du "
           f"{published}, annonce n° {rec.get('numeroannonce')}\n")
    if isinstance(jugement, dict):
        tb.line("Date : ", fr_date(jugement.get("date")), "DATE")
        tb.line("", jugement.get("nature"))
    persons = parse(rec.get("listepersonnes"))
    pp = 0
    for pers in as_list(persons.get("personne") if isinstance(persons, dict) else None):
        if isinstance(pers, dict):
            pp += pers.get("typePersonne") == "pp"
            r.person(pers)
    if not pp:
        return None
    etabs = parse(rec.get("listeetablissements"))
    etab_list = as_list(etabs.get("etablissement") if isinstance(etabs, dict) else None)
    if etab_list:
        tb.add("Établissement(s) :\n")
        for etab in etab_list:
            if not isinstance(etab, dict):
                continue
            tb.line("", etab.get("qualiteEtablissement"))
            tb.line("Origine du fond : ", etab.get("origineFonds"))
            r.trade_line("Enseigne : ", etab.get("enseigne"))
            r.trade_line("Nom commercial : ", etab.get("nomCommercial"))
            tb.line("Activité : ", etab.get("activite"))
            r.address("Adresse de l'établissement : ", etab.get("adresse"))
    for key, title in (("listeprecedentproprietaire", "Précédent(s) Propriétaire(s) :\n"),
                       ("listeprecedentexploitant", "Précédent(s) Exploitant(s) :\n")):
        prev = parse(rec.get(key))
        prev_list = as_list(prev.get("personne") if isinstance(prev, dict) else None)
        if prev_list:
            tb.add(title)
            for pers in prev_list:
                if isinstance(pers, dict):
                    r.person(pers)
    for key in ("acte", "modificationsgenerales", "radiationaurcs", "depot", "divers"):
        r.free(parse(rec.get(key)))
    if isinstance(jugement, dict):
        r.free({k: v for k, v in jugement.items() if k not in ("date", "nature", "famille", "type")})
    text = tb.text
    raw = [*tb.spans, *r.repeats()]
    for start, end in tb.ignore:
        raw.extend((m.start("addr"), m.end("addr"), "ADDRESS", "phrase")
                   for m in _OWNER_ADDRESS.finditer(text, start, end))
    meta = {"family": rec.get("familleavis_lib"), "date": rec.get("dateparution"), "natural_persons": pp,
            "department": rec.get("numerodepartement")}
    return record(f"bodacc:{rec.get('id')}", "bodacc_fr", "fr", text, raw, tb.ignore, meta)


def fetch(cache: Path, per_family: int, start: str, end: str) -> list[dict[str, Any]]:
    """Annonces brutes, mises en cache par famille / raw announcements cached per family."""
    folder = raw_dir(cache, "bodacc")
    out: list[dict[str, Any]] = []
    for family in FAMILIES:
        path = folder / f"{family.replace(' ', '_')}_{start}_{end}_{per_family}.json"
        if path.exists():
            rows = json.loads(path.read_text(encoding="utf-8"))
        else:
            rows = []
            where = (f'familleavis_lib="{family}" and {PP_FILTER} and dateparution >= date\'{start}\' '
                     f"and dateparution <= date'{end}'")
            offset = 0
            while len(rows) < per_family and offset < 9900:
                page = http_json(API, {"limit": 100, "offset": offset, "where": where, "order_by": "id"})
                batch = page.get("results") or []
                rows.extend(batch)
                offset += 100
                if len(batch) < 100:
                    break
            rows = rows[:per_family]
            path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        log(f"bodacc {family}: {len(rows)} announcements")
        out.extend(rows)
    return out


def build(cache: Path, per_family: int, start: str, end: str) -> dict[str, Any]:
    rows = fetch(cache, per_family, start, end)

    def gen() -> Iterator[dict[str, Any]]:
        for row in rows:
            rec = render(row)
            if rec is not None:
                yield rec

    info = write_jsonl(corpus_path(cache, "bodacc_fr"), gen())
    info.update({"source": "DILA BODACC annonces commerciales (API Opendatasoft)",
                 "licence": "Licence Ouverte / Open Licence", "window": [start, end], "per_family": per_family,
                 "families": list(FAMILIES)})
    update_manifest(cache, "bodacc_fr", info)
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", type=Path, default=default_cache(), help="cache folder, outside the repository")
    parser.add_argument("--per-family", type=int, default=500, help="announcements per family (6 families)")
    parser.add_argument("--start", default="2026-09-01", help="first publication date (ISO)")
    parser.add_argument("--end", default="2026-09-30", help="last publication date (ISO)")
    args = parser.parse_args()
    cache = check_outside_repo(args.cache)
    info = build(cache, args.per_family, args.start, args.end)
    log(f"bodacc_fr: {info['documents']} documents, {info['mentions']} gold spans {info['labels']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
