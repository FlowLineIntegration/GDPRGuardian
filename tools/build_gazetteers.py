"""Construit les listes de noms et la base postale figées / builds the frozen name lists and postal base.

Bibliothèque standard uniquement ; ne tourne jamais à l'exécution, ses sorties sont versionnées.
Stdlib only; never runs at runtime, its outputs are committed to the repository.

Usage::

    python -I tools/build_gazetteers.py --cache <dossier de téléchargement / download dir>

Sorties / outputs (src/gdprguardian/heuristics/data/):
    names.tsv.gz    jeton replié -> rang de fréquence prénom, sexe, rang nom de famille, ambiguïté
    words.txt.gz    mots courants qui ne sont pas des noms (lexèmes Wikidata, liste manuelle)
    postal.tsv.gz   code postal -> communes et localités (clés normalisées)
    sources.json    provenance : URL, empreinte SHA-256, taille, licence, date
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import importlib.util
import io
import json
import math
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "gdprguardian" / "heuristics" / "data"
USER_AGENT = "GDPRGuardian-gazetteer-build/1.0 (https://pypi.org/project/gdprguardian/)"
MAX_DOWNLOAD = 64 * 1024 * 1024
GIVEN_MIN_COUNT = 20           # prénoms donnés au moins 20 fois depuis 1900 / given at least 20 times since 1900
# Noms portés par au moins 256 personnes : en dessous, un nom inconnu se comporte de la même façon (voisin d'un
# prénom, civilité, propagation) ; seul un nom fréquent peut être masqué seul. Surnames with at least 256 bearers:
# below that, an unknown capitalised token behaves the same; only a frequent surname is masked alone.
SURNAME_MIN_COUNT = 256
SEX_SHARE = 0.9                # part d'un sexe pour marquer M ou F / share of one sex to mark M or F
PLACE_OVERRIDE_COUNT = 10_000  # prénom fréquent homonyme d'un lieu : mot ambigu, pas entité / plain ambiguous word


def _load_runtime_text() -> object:
    """Charge `_text.py` seul (sans le paquet) : un seul repliement, partagé avec l'exécution.

    Loads `_text.py` alone (not the package): one folding function shared with the runtime.
    """
    spec = importlib.util.spec_from_file_location("_gdprguardian_text", ROOT / "src" / "gdprguardian" / "_text.py")
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("gdprguardian/_text.py introuvable / not found")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fold = _load_runtime_text().fold  # type: ignore[attr-defined]


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


@dataclass(frozen=True, slots=True)
class Source:
    key: str
    url: str
    licence: str
    attribution: str
    query: str = ""  # SPARQL envoyé en POST / SPARQL sent with POST


LEXEME_QUERY = """SELECT DISTINCT ?form ?cat WHERE {
  ?l dct:language wd:%s ; wikibase:lexicalCategory ?cat ; ontolex:lexicalForm ?f .
  ?f ontolex:representation ?form . FILTER(LANG(?form)="%s")
}"""

LO2 = "Licence Ouverte / Open Licence 2.0 (Etalab)"
COG = "Source : Insee, Code officiel géographique 2026"
_COG_URL = "https://www.insee.fr/fr/statistiques/fichier/8740222/"
SOURCES = {
    s.key: s for s in (
        Source("prenoms", "https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2025-nat_csv.zip", LO2,
               "Source : Insee, Fichier des prénoms, édition 2025 (naissances 1900-2025)"),
        Source("noms", "https://www.insee.fr/fr/statistiques/fichier/3536630/noms2008nat_txt.zip", LO2,
               "Source : Insee, Fichier des noms de famille, édition 2008 (naissances 1891-2000)"),
        Source("hexasmal", "https://data.laposte.fr/data-fair/api/v1/datasets/laposte-hexasmal/raw", LO2,
               "Source : La Poste, Base officielle des codes postaux"),
        Source("cog_communes", _COG_URL + "v_commune_2026.csv", LO2, COG),
        Source("cog_departements", _COG_URL + "v_departement_2026.csv", LO2, COG),
        Source("cog_regions", _COG_URL + "v_region_2026.csv", LO2, COG),
        Source("cog_arrondissements", _COG_URL + "v_arrondissement_2026.csv", LO2, COG),
        Source("cog_pays", _COG_URL + "v_pays_territoire_2026.csv", LO2, COG),
        Source("lexemes", "https://query.wikidata.org/sparql", "CC0 1.0 (Wikidata)",
               "Wikidata, lexèmes français (formes)", LEXEME_QUERY % ("Q150", "fr")),
        Source("lexemes_en", "https://query.wikidata.org/sparql", "CC0 1.0 (Wikidata)",
               "Wikidata, lexèmes anglais (formes)", LEXEME_QUERY % ("Q1860", "en")),
    )
}

# Catégories lexicales Wikidata exclues des mots courants / Wikidata lexical categories not taken as common words:
# verbe (formes conjuguées, rarement capitalisées), nom propre (mélange lieux et prénoms), lettres, affixes.
EXCLUDED_CATEGORIES = frozenset({"Q24905", "Q147276", "Q9788", "Q102047", "Q134830", "Q162940", "Q3976700",
                                 "Q66614509"})

# --- Listes manuelles (faits, aucune reprise de tiers) / hand-curated lists (facts, nothing copied) ---------

# Prénoms qui sont aussi des mots très courants : jamais seuls en début de phrase sans indice.
# Given names that are also very common words: never alone at sentence start without a cue.
STRONG_WORDS = _words("""
    rose marine claire blanche fleur perle olive prune ambre jade iris aurore reine ange victoire constance
    clemence prudence patience esperance felicite grace harmonie melodie celeste modeste fortune constant desire
    desiree aime aimee capucine violette marguerite colombe oceane ocean soleil lune etoile cerise eglantine hermine
    liberte verite belle bijou princesse prince parfait sage gentil joyeux heureux fidele loyal juste franc vrai
""")

# Entités qui ne sont des personnes qu'avec un indice : mois, jours, fêtes, lieux connus, marques, institutions.
# Entities that are persons only with a cue: months, days, holidays, well-known places, brands, institutions.
ENTITY_WORDS = _words("""
    janvier fevrier mars avril mai juin juillet aout septembre octobre novembre decembre
    lundi mardi mercredi jeudi vendredi samedi dimanche
    january february march april may june july august september october november december
    monday tuesday wednesday thursday friday saturday sunday
    januar februar marz juni juli oktober dezember montag dienstag mittwoch donnerstag freitag samstag sonntag
    enero febrero marzo abril mayo junio agosto septiembre octubre noviembre diciembre lunes martes miercoles
    jueves viernes sabado gennaio febbraio aprile maggio giugno luglio settembre ottobre dicembre lunedi martedi
    mercoledi giovedi venerdi sabato domenica
    noel paques toussaint pentecote ascension assomption epiphanie chandeleur ramadan careme hanoucca
    france paris florence nancy lorraine valence lourdes vienne orange lyon marseille nice toulouse bordeaux lille
    nantes rennes brest calais laval avignon cholet blois pau albi agen metz reims tours dijon angers nimes
    grenoble montpellier strasbourg limoges poitiers versailles cannes antibes bayonne biarritz vichy sedan verdun
    rome milan venise naples turin genes berlin londres madrid barcelone seville lisbonne porto bruxelles liege namur
    anvers gand geneve berne lausanne zurich bale moscou prague varsovie cracovie athenes dublin amsterdam
    rotterdam budapest bucarest oslo stockholm copenhague helsinki sydney melbourne georgie jordanie alexandrie
    lima damas jerusalem bethleem nazareth
    bretagne normandie provence loire seine rhone garonne savoie corse alsace champagne bourgogne picardie
    touraine anjou berry vendee gironde ardeche dordogne charente maine vermont auvergne gascogne aquitaine
    occitanie limousin perigord quercy bearn roussillon artois flandre hainaut brabant sologne beauce brie
    camargue cevennes
    europe afrique asie amerique oceanie australie canada quebec belgique suisse allemagne italie espagne portugal
    irlande ecosse angleterre autriche pologne hongrie grece turquie russie ukraine chine japon inde bresil mexique
    renault peugeot citroen michelin dassault bouygues lacoste chanel hermes dior cartier boucheron ricard pernod
    hennessy martell moet chandon bic leclerc auchan carrefour casino total thales safran airbus alstom vinci
    lagardere pathe gaumont bollore ferrari porsche lamborghini bugatti mercedes opel siemens bosch philips nestle
    dell disney boeing gillette kellogg colgate hilton marriott ritz dyson tesla bayer merck pfizer roche
    sanofi servier clarins guerlain lancome rossignol salomon lafuma darty boulanger picard lidl aldi danone
    lactalis bonduelle panzani lustucru amora maille vuitton givenchy balenciaga lanvin kenzo rolex omega swatch
    nokia ericsson samsung sony toyota honda nissan mazda suzuki hyundai fiat maserati volvo saab skoda dacia
    jaguar bentley ikea decathlon intermarche monoprix franprix conforama castorama
    python java perl linux windows excel outlook oracle docker android chrome firefox safari mistral gemini siri
    alexa cortana copilot llama google amazon apple microsoft netflix uber spotify zoom slack
    etat republique gouvernement parlement senat assemblee ministere prefecture mairie tribunal academie eglise
    gendarmerie armee police justice defense nation commission
    saint sainte
    mercure venus terre jupiter saturne uranus neptune pluton ceres eris charon sirius vega orion andromede
    pegase cassiopee zeus apollon athena poseidon hades aphrodite ares artemis dionysos demeter junon minerve
    vulcain cupidon chronos gaia promethee
    gallimard flammarion hachette larousse fayard grasset plon julliard denoel dunod eyrolles vuibert springer
    elsevier tallandier hatier bordas seuil
    tokyo pekin shanghai delhi bombay mumbai bangkok singapour dubai istanbul alger tunis rabat casablanca dakar
    abidjan kinshasa johannesburg chicago montreal toronto vancouver bogota caracas galles monte-carlo
""")

# Mots anglais courants qui sont aussi des prénoms / common English words that are also given names.
ENGLISH_WORDS = _words("""
    will grace hope joy faith charity mark bill ray summer dawn chance hunter mason cooper carter parker sky river
    storm star angel honey holly ivy heather willow hazel violet cherry melody destiny trinity liberty unity nova
    rain autumn crystal diamond ruby amber pearl daisy lily poppy sunny happy lucky baby sugar candy ginger pepper
    king queen lady lord duke earl baron dear best regards team world love peace art gene pat sue rob don jack
""")

# Prénoms européens courants absents (ou presque) du fichier Insee / common EU given names missing from Insee.
INTERNATIONAL_GIVEN = _words("""
    uwe jorg torsten rudiger birgit heike svenja franziska gertrud inmaculada krzysztof andrzej marcin grzegorz
    mariusz dariusz rafal jacek janusz ryszard malgorzata agnieszka elzbieta beata dorota grazyna iwona urszula
    justyna gerrit jacobus bram thijs jeroen ruud wouter stijn koen joost maarten kees henk joop geert femke sanne
    lieke annelies mieke hendrika fenna morten rasmus olof bengt jukka mikko pekka juha birgitta malin mette hanne
    aino tuula paivi jiri petr frantisek zdenek ondrej jozsef janos ferenc tamas zsolt erzsebet zsuzsanna judit
    georgios konstantinos nikolaos panagiotis vasileios athanasios evangelos aikaterini vasiliki angeliki dimitra
    saoirse andris martins mindaugas andrius ruta
""")

# Mots-outils et mots de structure toujours courants / function and structure words, always common.
FUNCTION_WORDS = _words("""
    le la les l un une des du de d au aux ce cet cette ces mon ma mes ton ta tes son sa ses notre nos votre vos
    leur leurs et ou mais donc or ni car que qui quoi dont si il elle ils elles on nous vous je tu me te se lui y
    en ne pas plus pour par sur sous dans avec sans chez vers entre selon depuis pendant avant apres contre parmi
    malgre voici voila oui non merci bonjour bonsoir salut cordialement objet date page annexe article tableau
    figure note total titre chapitre section partie resume introduction conclusion sommaire table
    the and or of to for with from by on in at as is are was were be this that these those it its an a
    der die das und oder mit von zu fur den dem des ein eine el los las y con por para del il lo gli di che
""")

PLACE_TOKEN_RE = re.compile(r"[a-z0-9]+")
SAINT = {"saint": "st", "sainte": "ste", "saints": "sts", "saintes": "stes"}


def place_key(name: str) -> str:
    """Clé de lieu : repliée, ponctuation -> espace, « saint » -> « st » (identique à l'exécution).

    Place key: folded, punctuation -> space, "saint" -> "st" (same as runtime).
    """
    return " ".join(SAINT.get(t, t) for t in PLACE_TOKEN_RE.findall(fold(name)))


# --- Téléchargement / download -------------------------------------------------------------------------------


def fetch(source: Source, cache: Path, offline: bool) -> bytes:
    """Télécharge une fois dans son propre dossier, puis relit le cache / downloads once, then reads the cache."""
    folder = cache / source.key
    target = folder / "raw.bin"
    if target.exists():
        return target.read_bytes()
    if offline:
        raise SystemExit(f"{source.key}: absent du cache / missing from cache ({target})")
    folder.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/csv" if source.query else "*/*"}
    body = urllib.parse.urlencode({"query": source.query}).encode() if source.query else None
    request = urllib.request.Request(source.url, data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=300) as response:  # URL fixes en code / URLs fixed in code
        raw = response.read(MAX_DOWNLOAD + 1)
    if len(raw) > MAX_DOWNLOAD:
        raise SystemExit(f"{source.key}: réponse trop volumineuse / response too large")
    target.write_bytes(raw)
    return raw


def _unzip_single(raw: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if len(members) != 1 or members[0].file_size > MAX_DOWNLOAD:
            raise SystemExit("archive inattendue / unexpected archive")
        return archive.read(members[0])


# --- Analyse des sources / source parsing --------------------------------------------------------------------


def parse_given(raw: bytes) -> dict[str, tuple[int, int]]:
    """Prénom replié -> (naissances masculines, féminines) / folded given name -> (male, female) births."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    reader = csv.reader(io.StringIO(_unzip_single(raw).decode("utf-8")), delimiter=";")
    header = next(reader)
    if header[:4] != ["sexe", "prenom", "periode", "valeur"]:
        raise SystemExit(f"prénoms : en-tête inattendu / unexpected header {header}")
    for sex, name, _period, value, *_ in reader:
        if not name or name.startswith("_") or sex not in ("1", "2"):
            continue  # agrégats « prénoms rares » / "rare names" aggregates
        counts[fold(name.strip())][int(sex) - 1] += int(value)
    return {name: (male, female) for name, (male, female) in counts.items()}


def parse_surnames(raw: bytes) -> dict[str, int]:
    """Nom replié -> naissances 1891-2000 / folded surname -> births 1891-2000."""
    lines = _unzip_single(raw).decode("utf-8").splitlines()
    if not lines[0].startswith("NOM\t_1891_1900"):
        raise SystemExit("noms : en-tête inattendu / unexpected header")
    counts: dict[str, int] = defaultdict(int)
    for line in lines[1:]:
        name, *decades = line.split("\t")
        if name and name != "AUTRES NOMS":  # agrégat des noms rares / rare-names aggregate
            counts[fold(name.strip())] += sum(int(x) for x in decades if x)
    return dict(counts)


def parse_lexemes(raw: bytes) -> set[str]:
    """Formes françaises courantes à un seul jeton / single-token common French forms."""
    words: set[str] = set()
    reader = csv.reader(io.StringIO(raw.decode("utf-8")))
    if next(reader) != ["form", "cat"]:
        raise SystemExit("lexèmes : en-tête inattendu / unexpected header")
    for form, category in reader:
        if category.rsplit("/", 1)[-1] in EXCLUDED_CATEGORIES:
            continue
        folded = fold(form.strip().replace("’", "'"))
        if len(folded) >= 2 and " " not in folded and folded[0].isalpha():
            words.add(folded)
    return words


def _cog_rows(raw: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))


def parse_places(raw: dict[str, bytes]) -> set[str]:
    """Lieux connus : pays, régions, départements, chefs-lieux / well-known places (folded single tokens).

    LIBELLE garde l'article (« Le Blanc ») : un nom à article n'est jamais un jeton seul.
    LIBELLE keeps the article ("Le Blanc"): a name with an article is never a single token.
    """
    communes = {row["COM"]: row["LIBELLE"] for row in _cog_rows(raw["cog_communes"]) if row["TYPECOM"] == "COM"}
    names: set[str] = set()
    for key in ("cog_departements", "cog_regions", "cog_arrondissements"):
        for row in _cog_rows(raw[key]):
            names.add(row["LIBELLE"])
            names.add(communes.get(row["CHEFLIEU"], ""))
    for row in _cog_rows(raw["cog_pays"]):
        names.add(row["LIBCOG"])
    return {fold(n) for n in names if n and " " not in n and "'" not in n}


def parse_postal(raw: dict[str, bytes]) -> dict[str, set[str]]:
    """Code postal -> clés de communes et localités (La Poste + COG) / postcode -> commune keys."""
    cog: dict[str, set[str]] = defaultdict(set)
    for row in _cog_rows(raw["cog_communes"]):
        if row["TYPECOM"] in ("COM", "ARM"):
            cog[row["COM"]].update((row["NCCENR"], row["LIBELLE"]))
    # Le fichier La Poste est en CP1252 malgré son en-tête HTTP / the La Poste file is CP1252 despite its header.
    lines = raw["hexasmal"].decode("cp1252").splitlines()
    if not lines[0].lstrip("#").startswith("Code_commune_INSEE;Nom_de_la_commune;Code_postal"):
        raise SystemExit("hexasmal : en-tête inattendu / unexpected header")
    postal: dict[str, set[str]] = defaultdict(set)
    for line in lines[1:]:
        insee, commune, code, label, line5 = (line.split(";") + [""] * 5)[:5]
        if not re.fullmatch(r"[0-9]{5}", code):
            continue
        for name in (commune, label, line5, *cog.get(insee, ())):
            key = place_key(name)
            if key:
                postal[code].add(key)
    return postal


# --- Assemblage / assembly -----------------------------------------------------------------------------------


def bucket(count: int) -> int:
    """Rang logarithmique : 2^b <= n < 2^(b+1) / log2 bucket."""
    return int(math.log2(count)) if count > 0 else 0


def ambiguity(token: str, given_total: int, lexemes: set[str], places: set[str]) -> str:
    """'' sûr, w mot courant, s mot très courant, e entité (lieu, mois, marque) / ambiguity class."""
    if token in ENTITY_WORDS:
        return "e"
    if token in places:
        # Prénom fréquent homonyme d'un lieu (Aude) : simple mot ambigu / frequent given name: plain word.
        return "w" if given_total >= PLACE_OVERRIDE_COUNT else "e"
    if token in STRONG_WORDS:
        return "s"
    if token in lexemes or token in ENGLISH_WORDS or token in FUNCTION_WORDS:
        return "w"
    return ""


def build_names(given: dict[str, tuple[int, int]], surnames: dict[str, int], lexemes: set[str],
                places: set[str]) -> list[str]:
    frequent = {t for t, (m, f) in given.items() if m + f >= GIVEN_MIN_COUNT}
    surnames = {t: n for t, n in surnames.items() if n >= SURNAME_MIN_COUNT}
    rows = []
    for token in sorted(frequent | set(surnames) | INTERNATIONAL_GIVEN):
        male, female = given.get(token, (0, 0))
        total = male + female
        if token in frequent:
            g = str(bucket(total))
            sex = "M" if male >= SEX_SHARE * total else "F" if female >= SEX_SHARE * total else "X"
        elif token in INTERNATIONAL_GIVEN:
            g, sex = "c", "X"
        else:
            g, sex = "", ""
        s = str(bucket(surnames[token])) if token in surnames else ""
        rows.append(f"{token}\t{g}\t{sex}\t{s}\t{ambiguity(token, total, lexemes, places)}")
    return rows


def write_gzip(path: Path, header: Iterable[str], lines: Iterable[str]) -> None:
    """Gzip reproductible (mtime=0, sans nom) / reproducible gzip (mtime=0, no file name)."""
    payload = "\n".join([*(f"# {h}" for h in header), *lines]).encode("utf-8") + b"\n"
    with open(path, "wb") as handle, gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0,
                                                   compresslevel=9) as archive:
        archive.write(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, required=True, help="dossier de téléchargement / download dir")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--offline", action="store_true", help="cache seulement / cache only")
    args = parser.parse_args(argv)
    if args.cache.resolve().is_relative_to(ROOT):
        raise SystemExit("le cache doit être hors du dépôt / the cache must be outside the repository")

    raw = {key: fetch(source, args.cache, args.offline) for key, source in SOURCES.items()}
    given = parse_given(raw["prenoms"])
    surnames = parse_surnames(raw["noms"])
    # Mots anglais aussi : « Independence Day », « Tokyo Tower » ne sont pas des personnes / English words too.
    lexemes = parse_lexemes(raw["lexemes"]) | parse_lexemes(raw["lexemes_en"])
    places = parse_places(raw)
    postal = parse_postal(raw)

    names = build_names(given, surnames, lexemes, places)
    name_tokens = {row.split("\t", 1)[0] for row in names}
    # Un lieu ou une marque qui n'est pas un nom reste un mot courant (« Aquitaine ») / non-name entities are words.
    words = sorted((lexemes | ENGLISH_WORDS | FUNCTION_WORDS | ENTITY_WORDS | places) - name_tokens)
    today = dt.date.today().isoformat()

    args.out.mkdir(parents=True, exist_ok=True)
    write_gzip(args.out / "names.tsv.gz", [
        "Gardien RGPD · GDPR Guardian - prénoms et noms de famille / given names and surnames. Voir / see SOURCES.md.",
        "Source : Insee, Fichier des prénoms (2025) et Fichier des noms (2008). Licence Ouverte 2.0.",
        "jeton\tprénom (log2 naissances, c = liste manuelle)\tsexe\tnom (log2 naissances)\tambiguïté (w s e)",
    ], names)
    write_gzip(args.out / "words.txt.gz", [
        "Gardien RGPD · GDPR Guardian - mots courants (non-noms) / common words (not names). "
        "Wikidata lexèmes (CC0) + liste manuelle.",
    ], words)
    write_gzip(args.out / "postal.tsv.gz", [
        "Gardien RGPD · GDPR Guardian - codes postaux / postcodes. "
        "Source : La Poste (Base officielle des codes postaux) et Insee (COG).",
        "Licence Ouverte 2.0. code postal\tcommunes et localités (clés normalisées, séparées par |)",
    ], (f"{code}\t{'|'.join(sorted(keys))}" for code, keys in sorted(postal.items())))

    provenance = {
        key: {"url": source.url, "sha256": hashlib.sha256(raw[key]).hexdigest(), "bytes": len(raw[key]),
              "licence": source.licence, "attribution": source.attribution, "built": today}
        for key, source in SOURCES.items()
    }
    (args.out / "sources.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
    print(f"names={len(names)} words={len(words)} postcodes={len(postal)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
