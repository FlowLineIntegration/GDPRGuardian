"""Moteur de détection et d'anonymisation / detection and anonymisation engine.

Cascade, du moins cher au plus cher / cascade, cheapest first:
normalisation -> mots-clés (1 passage) -> motifs + validateurs -> détecteurs -> fusion -> propagation.

Avec le noyau Rust, un document traverse toute la cascade en Rust (« moteur fusionné ») : Python n'exécute que
le code sans jumeau natif, et, sur un texte décomposé (NFD), les trois détecteurs à vue NFC. Sans lui, ou hors de
son domaine, le chemin par étapes ci-dessous, la référence, donne les mêmes résultats. With the Rust core, a
document goes through the whole cascade in Rust (the "fused engine"): Python only runs code without a native twin,
and, on a decomposed (NFD) text, the three NFC-view detectors. Without it, or outside its domain, the staged path
below, the reference, gives the same results.
"""

from __future__ import annotations

import re
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cache, partial
from itertools import accumulate, pairwise
from pathlib import PurePath
from time import perf_counter
from typing import Any

from . import _native
from ._text import _native_preparer, delimited_tables, fold, normalize, prepare
from .categories import _FORT_ONLY_RULES, Gate, mode_warning, resolve_mode
from .custom import CUSTOM_PACK, KEEP_ENTITY, RuleError, RuleSet, load_rules, parse_rules
from .heuristics._compose import _COMMON_MARKS
from .keywords import MAX_KEYWORD_LEN, KeywordHits, KeywordIndex, longest_matches
from .labels import LABELS
from .locale import _native_detector as _native_language
from .locale import detect_language, evidence, select_countries
from .operators import FORCED_REPLACE, NATIVE_NAMES, get_operator
from .packs import Pack, PatternRecognizer, available_packs, load_pack
from .sanitize import sanitize_output
from .scope import HONORIFICS, Scope, native_rules
from .selfcheck import output_check
from .types import (
    MERGEABLE_ENTITIES,
    PRIORITY_CONTEXT_ONLY,
    PRIORITY_HEURISTIC,
    PRIORITY_PROPAGATED,
    PRIORITY_VALIDATED,
    Analysis,
    AnonymizedText,
    Span,
)

try:  # automate de la propagation des valeurs / value propagation automaton
    import ahocorasick_rs as _ahocorasick
except ImportError:  # pragma: no cover - recherche par clé, même résultat / per-key search, same result
    _ahocorasick = None

# `profile` : ancien réglage, alias déprécié de `mode` (categories.PROFILE_MODES) ; « strict » garde en plus ses
# effets d'avant (niveau B sans contexte, seuil 0,3, organisations masquées). Deprecated alias of `mode`; "strict"
# also keeps its former effects (tier B without context, threshold 0.3, organisations masked).
PROFILES = ("fast", "standard", "strict")
COUNTRY_MODES = ("all", "auto")
_MIN_SCORE = {"fast": 0.5, "standard": 0.5, "strict": 0.3}
_SEGMENT_SEPARATOR = "\n\n"
# Fenêtre [avant, après] où l'état civil d'une personne rend personnel un identifiant d'entreprise (« n° RCS :
# … ⏎ Nom : … ⏎ Prénom : … »). Window where a natural person's civil status makes a company number personal.
NATURAL_PERSON_WINDOW = (120, 120)
# Une personne morale dans cette fenêtre l'emporte (« la société X SAS, SIRET … ») / a legal entity there wins.
LEGAL_ENTITY_WINDOW = (80, 40)
_DIGIT_RE = re.compile(r"[0-9]")
# Liaison de l'indice de naissance (`DetectionContext.cue_spent`, `scanner.rs`) : groupe-veto des dates de naissance,
# « nom de naissance » (un nom), suites de chiffres. Birth cue binding: the birth dates' veto group, the birth-name
# cue, digit runs.
_DATE_VETO = "INTL:other_date"
_BIRTH_NAME = "nom de naissance"
_DIGIT_RUN_RE = re.compile(r"[0-9]+")


def _date_seen(text: str, lo: int, hi: int) -> bool:
    """Une date entre `lo` et `hi` : une année (4 chiffres 18xx, 19xx, 20xx) ou une date chiffrée à l'année sur deux
    chiffres (« 12/05/84 », séparateurs « / . - ») ; suites de chiffres prises dans [lo, hi). A date in [lo, hi): a
    year (4 digits 18xx-20xx) or a numeric date with a two-digit year; digit runs read inside [lo, hi)."""
    runs = [m.span() for m in _DIGIT_RUN_RE.finditer(text, lo, hi)]
    for k, (a, b) in enumerate(runs):
        if b - a == 4 and text[a:a + 2] in ("18", "19", "20"):
            return True
        # Troisième tour : forme compacte « 19751021 » / third round: compact form.
        if (b - a == 8 and text[a:a + 2] in ("18", "19", "20") and "01" <= text[a + 4:a + 6] <= "12"
                and "01" <= text[a + 6:b] <= "31"):
            return True
        if k >= 2 and b - a == 2:
            (a1, b1), (a2, b2) = runs[k - 2], runs[k - 1]
            if (b1 - a1 <= 2 and b2 - a2 <= 2 and a2 == b1 + 1 and a == b2 + 1
                    and text[b1] in "/.-" and text[b2] in "/.-"):
                return True
        # Troisième tour : mois en mots, année sur deux chiffres (« 3 mars 85 ») / month word, two-digit year.
        if k >= 1 and b - a == 2:
            a1, b1 = runs[k - 1]
            if b1 - a1 <= 2 and _month_gap(text[b1:a]):
                return True
    return False


# Mois en mots et abréviations (`validators/intl._MONTH_WORDS`, « jui » compris ; `scanner.rs: SEEN_MONTHS`).
# Month words and abbreviations, "jui" included.
_SEEN_MONTHS = frozenset({"janvier", "février", "fevrier", "mars", "avril", "mai", "juin", "juillet", "août", "aout",
                          "septembre", "octobre", "novembre", "décembre", "decembre", "janv", "févr", "fevr", "fév",
                          "fev", "avr", "juil", "jui", "sept", "oct", "nov", "déc", "dec"})


def _month_gap(gap: str) -> bool:
    """Entre le jour et l'année : « er » facultatif, blancs, un mois (point final permis), blancs (« 1er janv. »).
    Between day and year: optional "er", spaces, one month word (final dot allowed), spaces."""
    if len(gap) > 18:
        return False
    g = gap[2:] if gap[:2].lower() == "er" else gap
    if not g or not g[0].isspace() or not g[-1].isspace():
        return False
    words = g.split()
    return len(words) == 1 and words[0].lower().removesuffix(".") in _SEEN_MONTHS


# Nom de société : une forme juridique de personne morale juste avant (« SARL DUPONT ») ou juste après (« DUPONT
# SARL ») reste lisible (considérant 14 du RGPD) ; « M. Dupont » reste masqué ; l'entrepreneur individuel (« EI »)
# est une personne. Même liste dans rust/src/finalize/pipeline.rs. A company name: a legal-entity form right before
# or right after stays readable; a sole trader is a person. Same list in rust/src/finalize/pipeline.rs.
COMPANY_FORMS = ("SAS", "SASU", "SARL", "SARLU", "EURL", "SCI", "SNC", "SCP", "SCM", "SELARL", "SELAS", "SELAFA",
                 "GAEC", "EARL", "SCEA", "GIE", "SCOP", "SEM", "SPL", "SCA", "S.A.R.L.", "S.A.S.", "S.A.S.U.",
                 "E.U.R.L.", "S.C.I.", "S.N.C.", "S.C.P.", "G.I.E.")
COMPANY_SUFFIX_FORMS = (*COMPANY_FORMS, "SA", "S.A.")
_COMPANY_BEFORE_RE = re.compile(r"(?<![\w.])(?:" + "|".join(map(re.escape, COMPANY_FORMS)) + r")[ \t]{1,2}\Z")
_COMPANY_AFTER_RE = re.compile(r"[ \t]{1,2}(?:" + "|".join(map(re.escape, COMPANY_SUFFIX_FORMS)) + r")(?!\w)")


# Civilité juste avant une personne trouvée : le mot capitalisé qui suit le nom en fait partie, même s'il est aussi un
# mot courant ou une commune (« Mme Christine Pires Beaune », « M. Matthieu Orphelin »). Même règle dans
# rust/src/finalize/pipeline.rs. A civility right before a found person: the capitalised word after the name belongs
# to it, even when it is also a common word or a town.
_CIVILITY_BEFORE_RE = re.compile(r"(?<![\w.])(?:M\.|Mme|Mlle|Monsieur|Madame|Mademoiselle)[ \t]\Z")
# Civilité ou titre juste avant un nom suivi d'une forme juridique : une personne (« M. Martin SA »). Même liste
# dans rust/src/finalize/pipeline.rs. A civility or title before a name with a legal form: a person.
_TITLE_BEFORE_RE = re.compile(
    r"(?<![\w.])(?:M\.|Mme|Mlle|Monsieur|Madame|Mademoiselle|Me|Maître|Dr)[ \t]\Z")


def _surname_end(text: str, pos: int) -> int | None:
    """Fin du mot capitalisé (« Orphelin », « Prud'homme », « Pires-Beaune ») qui commence en `pos`, sinon None.
    End of the capitalised word starting at `pos`, else None."""
    n = len(text)
    if pos >= n or not (text[pos].isalpha() and text[pos].isupper()):
        return None
    i, prev = pos + 1, text[pos]
    while i < n and (text[i].isalpha() or text[i] in "'-"):
        if text[i].isalpha() and not text[i].islower() and prev not in "'-":
            return None
        prev = text[i]
        i += 1
    if text[i - 1] in "'-" or i - pos < 2 or (i < n and text[i].isalnum()):
        return None
    return i


def _caps_word_end(text: str, pos: int) -> int | None:
    """Fin du mot en capitales (« LECLERC », « LE-GALL ») qui commence en `pos`, sinon None (1.0.2, troisième tour).
    End of the all-capitals word starting at `pos`, else None."""
    n = len(text)
    i = pos
    while i < n and ((text[i].isalpha() and text[i].isupper()) or (text[i] in "'-" and i > pos)):
        i += 1
    if i - pos < 2 or text[i - 1] in "'-" or (i < n and text[i].isalnum()):
        return None
    return i


def _extend_after_civility(spans: list[Span], text: str) -> None:
    """« M. [Matthieu] Orphelin » -> « M. [Matthieu Orphelin] » (`spans` triées, disjointes / sorted, disjoint)."""
    for k, span in enumerate(spans):
        if span.entity != "PERSON" or not span.personal or span.end >= len(text) or text[span.end] != " ":
            continue
        if _CIVILITY_BEFORE_RE.search(text, max(0, span.start - 14), span.start) is None:
            continue
        end = _surname_end(text, span.end + 1)
        if end is not None and not (k + 1 < len(spans) and spans[k + 1].start < end):
            span.end = end


# « M. Orphelin », « monsieur Orphelin » : une civilité suivie d'un blanc puis d'un seul mot capitalisé encore libre
# est un nom de famille, même homonyme d'un mot courant (débats parlementaires) ; jamais un article (« M. Le Maire »)
# ni un titre (« Monsieur Président »). Même règle dans rust/src/finalize/pipeline.rs. A civility, one blank, then one
# free capitalised word is a surname, even when it is also a common word; never an article nor a title.
CIVILITY_WORDS = ("M.", "Mme", "Mlle", "Monsieur", "Madame", "Mademoiselle", "monsieur", "madame", "mademoiselle")
# Nom de naissance (1.0.2, troisième tour, revue du 26/10) : « née Leclerc », « née LECLERC » : le mot qui suit est un
# nom de famille, capitalisé ou en capitales, raison `maiden_name` (fort et essentiel). Maiden name after « née ».
MAIDEN_WORDS = ("née", "Née")
_CIVILITY_RE = re.compile(r"(?<![\w.])(?:" + "|".join(map(re.escape, (*CIVILITY_WORDS, *MAIDEN_WORDS))) + r")[ \t]")
NOT_SURNAMES = frozenset({
    "Le", "La", "Les", "L", "De", "Du", "Des", "Président", "Présidente", "Ministre", "Député", "Députée",
    "Sénateur", "Sénatrice", "Maire", "Rapporteur", "Rapporteure", "Secrétaire", "Directeur", "Directrice", "Juge",
    "Procureur", "Préfet", "Préfète", "Commissaire", "Professeur", "Docteur", "Maître", "Monsieur", "Madame",
    "Mademoiselle", "Et", "Ou"})
_FR_NAME_SOURCES = frozenset({"FR_NAMES", "propagated:FR_NAMES"})


def _civility_surnames(spans: list[Span], text: str) -> list[Span]:
    """« M. Orphelin » -> « M. [Orphelin] » : nouvelle personne après une civilité (`spans` triées, disjointes).

    Seulement si le détecteur de noms français a trouvé une personne dans le texte (pays FR demandé). A new person
    after a civility, when the capitalised word touches no span (`spans` sorted, disjoint); only when the French
    name detector found a person in the text (country FR requested).
    """
    if not any(s.source in _FR_NAME_SOURCES for s in spans):
        return spans
    starts = [s.start for s in spans]
    added: list[Span] = []
    for m in _CIVILITY_RE.finditer(text):
        pos = m.end()
        maiden = text[m.start():pos - 1] in MAIDEN_WORDS
        end = _surname_end(text, pos)
        if end is None and maiden:
            end = _caps_word_end(text, pos)
            if end is not None and text[pos:end] in _NAME_PARTICLES_CAPS and text[end:end + 1] == " ":
                end = _caps_word_end(text, end + 1) or end  # « née LE GALL »
        if end is None or text[pos:end] in NOT_SURNAMES:
            continue
        i = bisect_right(starts, end - 1) - 1  # dernière zone qui commence avant la fin / last span starting before
        if i >= 0 and spans[i].end > m.start():
            continue
        added.append(Span(pos, end, "PERSON", "PERSON", "FR_NAMES", 0.8, PRIORITY_HEURISTIC, text[pos:end], True,
                          reason="maiden_name" if maiden else None))
    if not added:
        return spans
    return sorted([*spans, *added], key=lambda s: s.start)


# Signature en minuscules (1.0.2, docs/REGLES.md « Signatures ») : formules de clôture, repliées, ponctuation finale
# retirée. Même liste dans rust/src/finalize/pipeline.rs. Lowercase signature: closing formulas, folded.
CLOSING_FORMULAS = frozenset({
    "cordialement", "bien cordialement", "tres cordialement", "bien a vous", "merci", "merci beaucoup",
    "merci d'avance", "bonne journee", "bonne soiree", "belle journee", "a bientot", "salutations",
    "sinceres salutations", "amities", "bises"})


def _signature_names(spans: list[Span], text: str) -> list[Span]:
    """Ligne de signature en minuscules : la première ligne non vide après une formule de clôture, ou la dernière
    ligne non vide du texte, qui ne tient qu'un ou deux mots en minuscules égaux (repliés) au prénom, au nom ou aux
    deux d'une seule personne déjà masquée dans le document : même balise qu'elle (sa valeur), raison `signature`.
    A lowercase signature line (first non-empty line after a closing formula, or the text's last non-empty line)
    holding one or two lowercase words equal to the given name, surname or both of exactly one person already masked
    in the document gets that person's tag, reason `signature`.
    """
    people: dict[str, set[str]] = {}
    values: dict[str, str] = {}
    for span in spans:
        if span.entity != "PERSON" or not span.personal:
            continue
        value = span.value if span.value is not None else text[span.start:span.end]
        words = value.split()
        if len(words) < 2:
            continue
        key = " ".join(fold(w) for w in words)
        values.setdefault(key, value)
        given, surname = fold(words[0]), fold(words[-1])
        for part in (given, surname, f"{given} {surname}"):
            people.setdefault(part, set()).add(key)
    if not people:
        return spans
    lines: list[tuple[int, int]] = []
    pos = 0
    while pos <= len(text):
        end = text.find("\n", pos)
        end = len(text) if end < 0 else end
        lines.append((pos, end))
        pos = end + 1
    candidates: list[int] = []
    for k, (start, end) in enumerate(lines):
        if fold(text[start:end]).strip().rstrip(",.!:;").strip() in CLOSING_FORMULAS:
            nxt = next((j for j in range(k + 1, len(lines)) if text[lines[j][0]:lines[j][1]].strip()), None)
            if nxt is not None:
                candidates.append(nxt)
    last = next((j for j in range(len(lines) - 1, -1, -1) if text[lines[j][0]:lines[j][1]].strip()), None)
    if last is not None:
        candidates.append(last)
    starts = [s.start for s in spans]
    added: list[Span] = []
    for k in dict.fromkeys(candidates):
        start, end = lines[k]
        raw = text[start:end]
        content = raw.strip()
        words = content.split(" ")
        if not 1 <= len(words) <= 2 or not all(len(w) >= 2 and all(c.isalpha() and c.islower() for c in w)
                                                for w in words):
            continue
        owners = people.get(" ".join(fold(w) for w in words), set())
        if len(owners) != 1:
            continue
        lo = start + len(raw) - len(raw.lstrip())
        hi = lo + len(content)
        i = bisect_right(starts, hi - 1) - 1  # dernière zone qui commence avant la fin / last span starting before
        if i >= 0 and spans[i].end > lo:
            continue
        added.append(Span(lo, hi, "PERSON", "PERSON", "FR_SIGNATURE", 0.8, PRIORITY_HEURISTIC,
                          values[next(iter(owners))], True, reason="signature"))
    if not added:
        return spans
    return sorted([*spans, *added], key=lambda s: s.start)


# Initiales après un indice (1.0.2, docs/REGLES.md « Initiales ») : indices repliés, sigles exclus. Même listes dans
# rust/src/finalize/pipeline.rs. Initials after a cue: folded cues, excluded acronyms.
INITIALS_CUES = (
    "redige par", "redigee par", "etabli par", "etablie par", "valide par", "validee par", "vise par", "visee par",
    "signe par", "signee par", "saisi par", "saisie par", "relu par", "relue par", "de la part de", "initiales",
    "paraphe", "auteur", "visa", "trigramme", "paraphes")
NOT_INITIALS = frozenset({
    "RH", "DG", "DRH", "DSI", "CA", "CE", "CSE", "SA", "TVA", "UE", "IT", "PDG", "DAF", "QA", "IA", "DGS", "DGA",
    "DPO", "CNIL", "SAS", "EI", "PME", "TPE", "CEO", "CTO", "CFO", "COO", "AI", "OK", "PS", "MOA", "MOE", "DSN",
    "CB", "SNCF", "RATP", "CPAM", "CNAM", "MDPH", "DDTM", "DDPP", "GRDF", "UGAP", "SASU", "SARL", "EURL"})


def _upper_at(text: str, i: int) -> bool:
    return i < len(text) and "A" <= text[i] <= "Z"


def _initials_at(text: str, p: int) -> int | None:
    """Fin des initiales qui commencent en `p` : `[A-Z]{2,3}` hors sigle exclu, ou
    `[A-Z]\\.\\s?[A-Z]\\.?(\\s?[A-Z]\\.?)?`, suivies d'un non-alphanumérique ; sinon None.
    End of the initials at `p`, else None."""
    i = p
    while i < len(text) and i - p < 4 and _upper_at(text, i):
        i += 1
    nxt = text[i] if i < len(text) else ""
    # « NB » puis un non-alphanumérique ou un point final (« … par NB. ») / then a non-alnum or a final full stop.
    # Quatre lettres admises depuis le troisième tour (« Visa : FXLD ») / four letters since the third round.
    if 2 <= i - p <= 4 and not nxt.isalnum() and not (nxt == "." and i + 1 < len(text) and text[i + 1].isalnum()):
        return None if text[p:i] in NOT_INITIALS else i
    if not (_upper_at(text, p) and text[p + 1:p + 2] == "."):
        return None
    i = p + 2
    if text[i:i + 1] == " " and _upper_at(text, i + 1):
        i += 1
    if not _upper_at(text, i):
        return None
    i += 1
    if text[i:i + 1] == ".":
        i += 1
    j = i + 1 if text[i:i + 1] == " " else i
    if _upper_at(text, j):
        j += 1
        if text[j:j + 1] == ".":
            j += 1
        if not (j < len(text) and text[j].isalnum()):
            return j
    return None if i < len(text) and text[i].isalnum() else i


def _initials(spans: list[Span], text: str, folded: str) -> list[Span]:
    """« Rédigée par NB », « visa : F.L. » : initiales d'une personne après un indice, raison `initials_after_cue`
    (`spans` triées, disjointes). Initials of a person after a cue (`spans` sorted, disjoint)."""
    starts = [s.start for s in spans]
    added: list[Span] = []
    for cue in INITIALS_CUES:
        pos = folded.find(cue)
        while pos >= 0:
            after = pos + len(cue)
            if not ((pos > 0 and text[pos - 1].isalnum()) or (after < len(text) and text[after].isalnum())):
                p = after
                while p < len(text) and p - after < 3 and text[p] in " :":
                    p += 1
                end = _initials_at(text, p) if p > after else None
                if end is not None:
                    i = bisect_right(starts, end - 1) - 1
                    if not (i >= 0 and spans[i].end > p) and not any(a.start < end and p < a.end for a in added):
                        added.append(Span(p, end, "PERSON", "PERSON", "FR_INITIALS", 0.8, PRIORITY_HEURISTIC,
                                          text[p:end], True, reason="initials_after_cue"))
                        _more_initials(text, end, spans, starts, added)
            pos = folded.find(cue, pos + 1)
    for s in spans:
        # « Jean-Marc Delaunay (JMD) » : initiales entre parenthèses juste après une personne masquée, égales aux
        # initiales de son nom (1.0.2, fort et essentiel). Bracketed initials right after a masked person, equal to
        # the initials of that person's name.
        if s.entity != "PERSON":
            continue
        p = s.end + 1 if text[s.end:s.end + 1] == " " else s.end
        if text[p:p + 1] != "(":
            continue
        q = p + 1
        while q - p <= 5 and _upper_at(text, q):
            q += 1
        if not (2 <= q - p - 1 <= 4 and text[q:q + 1] == ")") or text[p + 1:q] != _name_initials(text[s.start:s.end]):
            continue
        i = bisect_right(starts, q - 1) - 1
        if not (i >= 0 and spans[i].end > p + 1) and not any(a.start < q and p + 1 < a.end for a in added):
            added.append(Span(p + 1, q, "PERSON", "PERSON", "FR_INITIALS", 0.8, PRIORITY_HEURISTIC, text[p + 1:q],
                              True, reason="initials_of_person"))
    if added:
        spans = sorted([*spans, *added], key=lambda s: s.start)
    return _names_r3(spans, text)


def _more_initials(text: str, end: int, spans: list[Span], starts: list[int], added: list[Span]) -> None:
    """« Paraphes : JBR / MEA » : jusqu'à trois autres initiales séparées par « / » ou « , » (1.0.2, fort et
    essentiel). Up to three more initials separated by "/" or ",", each one shaped like the first."""
    for _ in range(3):
        k = end
        while k < len(text) and k - end < 2 and text[k] == " ":
            k += 1
        if text[k:k + 1] not in ("/", ","):
            return
        k += 1
        m = k
        while m < len(text) and m - k < 2 and text[m] == " ":
            m += 1
        nxt = _initials_at(text, m)
        if nxt is None:
            return
        i = bisect_right(starts, nxt - 1) - 1
        if (i >= 0 and spans[i].end > m) or any(a.start < nxt and m < a.end for a in added):
            return
        added.append(Span(m, nxt, "PERSON", "PERSON", "FR_INITIALS", 0.8, PRIORITY_HEURISTIC, text[m:nxt], True,
                          reason="initials_after_cue"))
        end = nxt


def _name_initials(name: str) -> str:
    """Initiales d'un nom : première lettre A-Z de chaque partie (blancs, « - », apostrophes), les parties en
    minuscules (« de ») ou à lettre accentuée ne comptent pas. Initials of a name: the A-Z first letter of each part."""
    out = []
    part_start = True
    for c in name:
        if c.isspace() or c in "-'’":
            part_start = True
            continue
        if part_start and "A" <= c <= "Z":
            out.append(c)
        part_start = False
    return "".join(out)


# Noms, troisième tour (1.0.2, revue du 26/10, docs/REGLES.md « Noms, troisième tour ») : initiales pointées, nom
# coupé par un saut de ligne, « DUPONT, Jean ». Règles des personnes : fort et essentiel ; personnalise sauf si
# « personnes » est coupée. Mêmes listes et même ordre dans rust/src/finalize/pipeline.rs. Names, third round:
# dotted initials, a name cut by a line break, "DUPONT, Jean"; person rules, fort and essentiel.
DOTTED_NOT_INITIALS = frozenset({
    "NB", "PJ", "HT", "TTC", "JO", "RCS", "TGI", "PV", "AR", "RN", "RD", "ZI", "ZA", "ZAC", "BP", "CS", "CV", "ID",
    "US", "UK", "ND", "VO", "SNC", "SCI", "MM", "CGI", "CP", "CC", "CT", "TA", "RIB", "AE", "RC", "DCE", "BPU", "DQE",
    "SPS", "OPC", "VRD", "TCE", "PLU", "ERP", "BTP", "CAA", "TI", "TC", "JAF", "CPH", "QPC", "AM", "PM", "SVP", "STP",
    "ONU", "USA", "TV", "PC", "CD", "DVD", "GPS", "SMS", "NC", "SO", "NO", "NE", "SE", "QC", "OPJ", "APJ", "CAF",
    "CGV", "CGU", "FAQ", "HLM", "BO", "PO", "EDF", "SDF", "RER", "TGV", "VTC", "PMR", "RSA", "APL", "CMU", "AME",
    "IRM", "ASE", "PMA"})
_INITIAL_PREPOSITIONS = ("de", "par", "pour", "avec", "chez", "à")
_INITIAL_PARTICLES = ("de", "du", "des", "van", "von", "der", "di", "da", "del", "le", "la", "Le", "La", "De", "Du")
_NAME_PARTICLES_CAPS = ("LE", "LA", "DE", "DU", "DA", "DI", "VAN", "VON", "DEL", "DES")


def _dotted_initials_at(text: str, p: int) -> tuple[int, str] | None:
    """`[A-Z]\\.` puis jusqu'à deux fois `[ -]?[A-Z]\\.` (« J.D. », « J.-B. », « M. T. ») : (fin, lettres), ou None si
    un alphanumérique suit. Dotted initials at `p`: (end, letters), or None when an alphanumeric follows."""
    if not (_upper_at(text, p) and text[p + 1:p + 2] == "."):
        return None
    letters = text[p]
    i = p + 2
    while len(letters) < 3:
        j = i + 1 if text[i:i + 1] in (" ", "-") else i
        if not (_upper_at(text, j) and text[j + 1:j + 2] == "."):
            break
        letters += text[j]
        i = j + 2
    if i < len(text) and text[i].isalnum():
        return None
    return i, letters


def _initials_ok(letters: str) -> bool:
    return letters not in NOT_INITIALS and letters not in DOTTED_NOT_INITIALS


def _capital_word_follows(text: str, end: int) -> bool:
    """Un blanc puis une lettre capitale en `end` / one blank then a capital letter at `end`."""
    return text[end:end + 1] == " " and end + 1 < len(text) and text[end + 1].isalpha() and text[end + 1].isupper()


def _particle_surname_end(text: str, pos: int) -> int | None:
    """« de La Fontaine », « Martin » : jusqu'à deux particules puis un nom capitalisé (`_surname_end`), sinon None.
    Up to two particles then a capitalised surname, else None."""
    q = pos
    for _ in range(2):
        for particle in _INITIAL_PARTICLES:
            k = q + len(particle)
            if text.startswith(particle, q) and text[k:k + 1] == " " and k + 1 < len(text) and text[k + 1].isalpha():
                q = k + 1
                break
        else:
            if text[q:q + 2] in ("d'", "D'") and q + 2 < len(text) and text[q + 2].isalpha():
                q += 2
            break
    end = _surname_end(text, q)
    if end is None or text[q:end] in NOT_SURNAMES:
        return None
    return end


def _preposition_before(text: str, p: int) -> bool:
    """« de », « par », « pour », « avec », « chez » ou « à », non précédé d'un alphanumérique, puis un blanc juste
    avant `p`. A preposition, then one blank, right before `p`."""
    if p < 2 or text[p - 1] != " ":
        return False
    for word in _INITIAL_PREPOSITIONS:
        start = p - 1 - len(word)
        if start >= 0 and text[start:p - 1] == word and not (start > 0 and text[start - 1].isalnum()):
            return True
    return False


_LIST_LINK_RE = re.compile(r"[ \t]?(?:,|et|&)[ \t]{1,2}")
_LINE_BREAK_GAP_RE = re.compile(r"[ \t]{0,2}\r?\n[ \t]{0,2}")


def _names_r3(spans: list[Span], text: str) -> list[Span]:
    """Initiales et noms, troisième tour (`spans` triées, disjointes ; renvoyées triées) :

    - « Lefebvre-Durand M.-H. », « Lemoine P. » : initiales pointées juste après une personne, ajoutées à sa zone ;
    - « J.-B. Lemoine » : initiales d'au moins deux lettres juste avant une personne, ajoutées à sa zone ;
    - « (M. T.) » : initiales pointées entre parenthèses, raison `initials_in_brackets` ;
    - « Paul Morel, Sophie Blanc, C.M. » : initiales pointées après une personne et « , », « et » ou « & », raison
      `initials_in_list` ;
    - « J.-B. de La Fontaine » : initiales à trait d'union puis particules et nom, raison `initials_with_surname` ;
    - « J.D. Contactez », « Adresse de I.P. » : initiales pointées en début de ligne (puis fin de ligne ou mot
      capitalisé) ou après « de », « par », « pour », « avec », « chez », « à », raison `initials_dotted` ;
    - « "DUPONT, Jean" » : nom en capitales, virgule, prénom : une seule personne ;
    - « Jean⏎Dupont », « Yann LE⏎GALL » : nom coupé par un saut de ligne, une seule personne.

    Sigles exclus (`NOT_INITIALS`, `DOTTED_NOT_INITIALS`). Third round of initials and names; excluded acronyms.
    """
    n = len(text)
    starts = [s.start for s in spans]
    added: list[Span] = []

    def free(a: int, b: int) -> bool:
        i = bisect_right(starts, b - 1) - 1
        return not (i >= 0 and spans[i].end > a) and not any(x.start < b and a < x.end for x in added)

    def person(s: Span) -> bool:
        return s.entity == "PERSON" and s.personal

    # Initiales juste après une personne / initials right after a person.
    for s in spans:
        if not person(s) or text[s.end:s.end + 1] != " ":
            continue
        found = _dotted_initials_at(text, s.end + 1)
        if found is None or not _initials_ok(found[1]) or _capital_word_follows(text, found[0]):
            continue
        if free(s.end + 1, found[0]):
            s.end = found[0]
    def listed(p: int) -> bool:
        """Une personne (ou des initiales déjà prises), puis « , », « et » ou « & » juste avant `p`."""
        i = bisect_right(starts, p - 1) - 1
        prev = spans[i] if i >= 0 and spans[i].end <= p else None
        if added and added[-1].end <= p and (prev is None or added[-1].end > prev.end):
            prev = added[-1]
        return prev is not None and prev.entity == "PERSON" and _LIST_LINK_RE.fullmatch(text, prev.end, p) is not None

    index = {s.start: k for k, s in enumerate(spans)}
    p = 0
    while p < n:
        if not (_upper_at(text, p) and text[p + 1:p + 2] == ".") or (
                p > 0 and (text[p - 1].isalnum() or text[p - 1] in ".-'’_@/")):
            p += 1
            continue
        if text[p] == "M" and text[p + 2:p + 3] == " " and not (p > 0 and text[p - 1] == "(") and not listed(p):
            p += 2  # civilité « M. » (« M. J.-B. de La Fontaine ») / a civility
            continue
        found = _dotted_initials_at(text, p)
        if found is None:
            p += 1
            continue
        end, letters = found
        if len(letters) >= 2 and _initials_ok(letters) and free(p, end):
            k = index.get(end + 1) if text[end:end + 1] == " " else None
            reason = None
            stop = end
            if k is not None and person(spans[k]):
                spans[k].start = p  # « J.-B. Lemoine »
                starts[k] = p
            elif p > 0 and text[p - 1] == "(" and text[end:end + 1] == ")":
                # Trois lettres collées entre parenthèses : un sigle (« (C.C.P.) ») / three glued letters: an acronym.
                if len(letters) == 2 or " " in text[p:end] or "-" in text[p:end]:
                    reason = "initials_in_brackets"
            else:
                if listed(p):
                    reason = "initials_in_list"
                elif "-" in text[p:end] and text[end:end + 1] == " ":
                    surname = _particle_surname_end(text, end + 1)
                    if surname is not None and free(p, surname):
                        reason, stop = "initials_with_surname", surname
                if reason is None and (len(letters) == 2 or "-" in text[p:end]) and " " not in text[p:end]:
                    line_start = p == 0 or text[p - 1] == "\n"
                    line_end = end >= n or text[end] in "\r\n" or _capital_word_follows(text, end)
                    if (line_start and line_end) or _preposition_before(text, p):
                        reason = "initials_dotted"
            if reason is not None:
                added.append(Span(p, stop, "PERSON", "PERSON", "FR_INITIALS", 0.8, PRIORITY_HEURISTIC, text[p:stop],
                                  True, reason=reason))
                end = stop
        p = end
    if added:
        spans = sorted([*spans, *added], key=lambda s: s.start)
    return _join_split_names(_bare_initials_in_list(spans, text), text)


def _list_link_end(text: str, pos: int) -> int | None:
    """`_LIST_LINK_RE.match(text, pos)` : fin du lien, sinon None / end of the list link, else None."""
    m = _LIST_LINK_RE.match(text, pos)
    return None if m is None else m.end()


def _bare_initials_in_list(spans: list[Span], text: str) -> list[Span]:
    """« Présents : Quentin Moreau, Mathéo Moreau, AC » : initiales en capitales (`_initials_at`, sigles exclus)
    après deux personnes d'une même liste, raison `initials_in_list` (`spans` triées, disjointes). Bare capital
    initials after two persons of one list."""
    added: list[Span] = []
    for k in range(1, len(spans)):
        a, b = spans[k - 1], spans[k]
        if a.entity != "PERSON" or b.entity != "PERSON" or not _LIST_LINK_RE.fullmatch(text, a.end, b.start):
            continue
        if " " not in text[a.start:a.end] or " " not in text[b.start:b.end]:
            continue  # deux personnes en prénom et nom (« Fonte, Grès, PRV » : non) / two full names
        q = _list_link_end(text, b.end)
        if q is None or not _upper_at(text, q) or text[q + 1:q + 2] == ".":
            continue
        end = _initials_at(text, q)
        if end is None or not _initials_ok(text[q:end]) or (k + 1 < len(spans) and spans[k + 1].start < end):
            continue
        added.append(Span(q, end, "PERSON", "PERSON", "FR_INITIALS", 0.8, PRIORITY_HEURISTIC, text[q:end], True,
                          reason="initials_in_list"))
    if not added:
        return spans
    return sorted([*spans, *added], key=lambda s: s.start)


def _after_closing(text: str, line_start: int) -> bool:
    """La ligne juste avant `line_start` finit par « , » ou est une formule de clôture (signature), ou `line_start`
    ouvre le texte. The line right before ends with a comma or is a closing formula, or `line_start` opens the text."""
    if line_start == 0:
        return True
    before = text[text.rfind("\n", 0, line_start - 1) + 1:line_start - 1].strip()
    return before.endswith(",") or fold(before).strip().rstrip(",.!:;").strip() in CLOSING_FORMULAS


def _join_split_names(spans: list[Span], text: str) -> list[Span]:
    """« "DUPONT, Jean" », « Jean⏎Dupont », « Yann LE⏎GALL » : une seule personne (`spans` triées, disjointes).

    One person for a capitals surname, a comma and a given name, for one-word names on two lines (the first starts
    its line, the second ends it), and for a name followed by a capitals particle, a line break and a capitals word.
    """
    out: list[Span] = []
    n = len(text)
    for s in spans:
        prev = out[-1] if out else None
        if prev is not None and prev.entity == "PERSON" and prev.personal and s.entity == "PERSON" and s.personal:
            left, right = text[prev.start:prev.end], text[s.start:s.end]
            single = " " not in left and " " not in right and "\n" not in left and "\n" not in right
            if single and text[prev.end:s.start] == ", " and len(left) >= 2 and left.isupper() and right[:1].isupper() \
                    and len(right) >= 2 and all(c.isalpha() and c.islower() for c in right[1:]) \
                    and not (s.end < n and text[s.end].isalnum()):
                prev.end = s.end  # « DUPONT, Jean »
                continue
            gap = _LINE_BREAK_GAP_RE.fullmatch(text, prev.end, s.start)
            line_start = text.rfind("\n", 0, prev.start) + 1
            if single and gap is not None and not text[line_start:prev.start].strip() and (
                    s.end >= n or text[s.end] in "\r\n") and _after_closing(text, line_start):
                prev.value = f"{prev.value or left} {s.value or right}"  # « Jean⏎Dupont »
                prev.end = s.end
                continue
        out.append(s)
    # Fix 1.0.2 (revue d'intégrité, temps quadratique) : `out` est triée par début ; une zone d'avant ne gêne que si
    # sa fin dépasse (`reach`, plus grande fin déjà vue), une zone d'après que si elle commence avant `end`. Même
    # résultat que le parcours complet, en temps linéaire. `out` is sorted by start: an earlier span blocks only when
    # its end passes (`reach`), a later one only when it starts before `end`; same result, linear time.
    reach = -1
    for i, s in enumerate(out):
        if s.entity == "PERSON" and s.personal and text[s.end:s.end + 1] == " ":
            for particle in _NAME_PARTICLES_CAPS:
                k = s.end + 1 + len(particle)
                if not text.startswith(particle, s.end + 1):
                    continue
                gap = _LINE_BREAK_GAP_RE.match(text, k)
                if gap is None:
                    continue
                end = _caps_word_end(text, gap.end())
                if end is not None and (end >= n or text[end] in "\r\n") and reach <= s.end \
                        and _clear_after(out, i, s.end, end):
                    s.end = end  # « Yann LE⏎GALL »
                break
        reach = max(reach, s.end)
    return out


def _clear_after(out: list[Span], i: int, start: int, end: int) -> bool:
    """Aucune zone après `out[i]` ne commence avant `end` en finissant après `start` / no later span overlaps."""
    for j in range(i + 1, len(out)):  # sans copie de la liste / no list copy
        o = out[j]
        if o.start >= end:
            return True
        if o.end > start:
            return False
    return True


def _company_named(text: str, start: int, end: int) -> bool:
    """« SARL DUPONT », « DUPONT SARL » : le nom porte une forme juridique de société / a company legal form.

    Revue du 26/10 : une civilité ou un titre juste avant (« M. Jean Dupont SARL ») fait une personne, et une forme
    suivie d'un mot capitalisé (« Dupont SARL Lumière ») appartient à ce nom-là. Review of 26/10: a civility or title
    right before makes a person, and a form followed by a capitalised word belongs to that next name.
    """
    if _TITLE_BEFORE_RE.search(text, max(0, start - 14), start) is not None:
        return False
    if _COMPANY_BEFORE_RE.search(text, max(0, start - 12), start) is not None:
        return True
    for tail in _company_tail_ends(text, end):
        after = _COMPANY_AFTER_RE.match(text, tail)
        if after is None:
            continue
        i = after.end()
        while i < len(text) and text[i] in " \t":
            i += 1
        if not (i > after.end() and i < len(text) and text[i].isalpha() and text[i].isupper()):
            return True
    return False


def _company_tail_ends(text: str, end: int) -> list[int]:
    """Fins possibles du nom d'une société qui commence par une personne : la personne seule, puis jusqu'à trois mots
    de plus, capitalisés, « & » ou « et », après un ou deux blancs (« Dupont Frères SAS », « Martin & Fils SARL »,
    1.0.2, troisième tour, fort et essentiel). Possible ends of a company name starting with a person: up to three more
    capitalised words, "&" or "et", each after one or two blanks."""
    ends = [end]
    i, n = end, len(text)
    for _ in range(3):
        j = i
        while j < n and j - i < 2 and text[j] in " \t":
            j += 1
        if j == i or j >= n:
            break
        if text[j] == "&":
            k = j + 1
        elif text.startswith("et", j) and not (j + 2 < n and text[j + 2].isalnum()):
            k = j + 2
        elif text[j].isalpha() and text[j].isupper():
            k = j + 1
            while k < n and (text[k].isalnum() or text[k] in "'’-"):
                k += 1
        else:
            break
        ends.append(k)
        i = k
    return ends


# Société civile professionnelle ou d'exercice libéral (« SCP Dupont, Martin et Durand », « SELARL Testa & Testi ») :
# le nom entier de la firme reste lisible, chaque associé compris ; les noms suivants n'en sont séparés que par une
# virgule, « et », « & » ou un tiret. Même liste dans rust/src/finalize/pipeline.rs. A professional partnership's
# whole firm name stays readable, every partner included.
PARTNERSHIP_FORMS = ("SCP", "SELARL", "SELAS", "SELAFA", "SELURL", "SELCA", "SCM", "S.C.P.")
_PARTNERSHIP_BEFORE_RE = re.compile(r"(?<![\w.])(?:" + "|".join(map(re.escape, PARTNERSHIP_FORMS)) + r")[ \t]{1,2}\Z")
_FIRM_LINK_RE = re.compile(r"[ \t]{0,2}(?:,|&|et|-|–)[ \t]{1,2}")
# Un associé enchaîné est un nom seul, d'un seul mot (« Durand », « Testa-Testi ») : un prénom et un nom (« Jean
# Moulu ») arrêtent la firme et restent masqués. A chained partner is a lone one-word surname; a given name and a
# surname end the firm and stay masked.
_FIRM_BLANKS = " \t\n\r\xa0\u202f"


def _drop_company_names(text: str, spans: list[Span]) -> list[Span]:
    """Retire les personnes qui portent une forme juridique de société (`_company_named`) et, après une société
    civile professionnelle ou d'exercice libéral, les associés suivants de la même firme, noms seuls d'un mot
    (`spans` disjointes).

    Drops persons carrying a company legal form and, after a professional partnership, the next partners of the
    same firm, lone one-word surnames (`spans` disjoint); returns them sorted by start.
    """
    kept: list[Span] = []
    firm_end = -1
    for span in sorted(spans, key=lambda s: s.start):
        if span.entity == "PERSON":
            if firm_end >= 0 and _FIRM_LINK_RE.fullmatch(text, firm_end, span.start) is not None \
                    and not any(c in _FIRM_BLANKS for c in text[span.start:span.end]):
                firm_end = span.end
                continue
            if _company_named(text, span.start, span.end):
                partnership = _PARTNERSHIP_BEFORE_RE.search(text, max(0, span.start - 12), span.start)
                firm_end = -1 if partnership is None else span.end
                continue
        firm_end = -1
        kept.append(span)
    return kept
# Avertissement du rapport quand le pays FR n'est pas demandé / report warning when FR is not requested.
NAMES_FRENCH_ONLY = ("Noms et adresses : détectés par les lexiques français seulement ; sans le pays FR, ils ne "
                     "sont pas masqués / Names and addresses are detected by the French lexicons only; without "
                     "country FR they are not masked")
_DENY_LABEL = "DENY"
# Cellule de tableau (début, fin) et groupes de contexte de son en-tête / table cell and its header's groups.
Zone = tuple[int, int, frozenset[str]]
NOTICE_FR = ("Anonymisation irréversible des identifiants détectés : aucune table de correspondance n'est "
             "conservée. Des éléments de contexte non détectés peuvent subsister.")
NOTICE_EN = ("Irreversible anonymisation of detected identifiers: no mapping table is kept. Undetected "
             "contextual details may remain.")


@dataclass(slots=True, frozen=True)
class Settings:
    """Réglages d'anonymisation / anonymisation settings."""

    # Pays explicites (recommandé), "all" (tous les packs, contexte requis pour les identifiants faibles)
    # ou "auto" (EXPÉRIMENTAL : pays deviné). Explicit countries (recommended), "all" (every pack, weak
    # identifiers need context) or "auto" (EXPERIMENTAL: inferred country).
    countries: str | tuple[str, ...] = ("FR",)
    default_countries: tuple[str, ...] = ("FR",)
    # Mode du filtre (docs/REGLES.md « Modes ») : « fort » (défaut), « essentiel », « personnalise » ; alias anglais
    # strong, essential (basique, basic), custom. `disable` : catégories laissées en clair (categories.CATEGORIES),
    # personnalise seulement ; sans mode, il le choisit. Filter mode: fort (default), essentiel, personnalise;
    # `disable`: categories left in clear, personnalise only (selects it when no mode is given).
    mode: str | None = None
    disable: str | Sequence[str] = ()
    # Déprécié : alias de `mode` (strict -> fort, standard et fast -> essentiel) / deprecated alias of `mode`.
    profile: str | None = None
    label_language: str = "fr"
    neutral_labels: bool = False
    company_ids: str = "auto"
    facility_ids: str = "keep"
    entities: frozenset[str] | None = None
    exclude_entities: frozenset[str] = frozenset()
    operators: Mapping[str, str] = field(default_factory=dict)
    deny_list: Mapping[str, Sequence[str]] = field(default_factory=dict)
    allow_list: Sequence[str] = ()
    min_score: float | None = None
    sanitize: bool = True
    detectors: Sequence[Any] = ()
    # Noyau Rust si installé (résultats identiques) / Rust core when installed (identical results).
    native: bool = True
    # Jeu de règles de l'organisation (custom.parse_rules / load_rules) / the organisation's rule set.
    rules: Any = None
    # Rapport détaillé : pour chaque balise, la règle et la raison (jamais la valeur) / per-tag rule and reason.
    explain: bool = False

    def validate(self) -> None:
        if isinstance(self.countries, str):
            if self.countries not in COUNTRY_MODES:
                raise ValueError(f"countries : liste de codes pays ou / list of country codes or {COUNTRY_MODES}")
        else:
            unknown = sorted(set(self.countries) - set(available_packs()))
            if unknown or not self.countries:
                raise ValueError(f"Pays sans pack / countries without pack: {unknown or '[]'} "
                                 f"(disponibles / available: {available_packs()})")
        if self.profile is not None and self.profile not in PROFILES:
            raise ValueError(f"profile (déprécié, utilisez mode / deprecated, use mode) ∈ {PROFILES}")
        resolve_mode(self.mode, self.profile, self.disable)  # ValueError avec la liste / with the list
        if self.company_ids not in ("auto", "keep", "mask") or self.facility_ids not in ("keep", "mask"):
            raise ValueError("company_ids ∈ auto|keep|mask, facility_ids ∈ keep|mask")
        if self.label_language not in ("fr", "en", "auto"):
            raise ValueError("label_language ∈ fr|en|auto")
        if self.rules is not None and not isinstance(self.rules, RuleSet):
            raise ValueError("rules : RuleSet, dict ou chemin de fichier / RuleSet, dict or file path")


class DetectionContext:
    """Vue partagée par les recognizers et détecteurs / view shared by recognizers and detectors."""

    __slots__ = ("_composed", "_features", "_zone_groups", "_zone_starts", "countries", "counts", "folded", "forced",
                 "found", "hits", "language", "seg_ends", "seg_starts", "settings", "strict", "text", "zones")

    def __init__(self, text: str, folded: str, hits: Any, countries: tuple[str, ...], language: str,
                 settings: Settings, seg_starts: list[int] | None = None, seg_ends: list[int] | None = None,
                 forced: Sequence[frozenset[str]] | None = None,
                 zones: Sequence[Zone] = ()) -> None:
        self.text = text
        self.folded = folded
        # Sans index de mots-clés (tests de détecteurs isolés) : aucun mot-clé / no keyword index: no keyword.
        self.hits = hits if hits is not None else KeywordHits()
        self.counts: dict[str, int] = self.hits.counts
        self.countries = countries
        self.language = language
        self.settings = settings
        self.strict = settings.profile == "strict"
        self.seg_starts = seg_starts
        self.seg_ends = seg_ends
        self.forced = forced
        # Cellules de tableau Markdown et groupes de contexte de leur en-tête de colonne (triées, disjointes).
        # Markdown table cells and the context groups of their column header (sorted, disjoint).
        self.zones = list(zones)
        self._zone_starts = [z[0] for z in self.zones]
        self._zone_groups = frozenset().union(*(z[2] for z in self.zones)) if self.zones else frozenset()
        # Zones déjà trouvées dans ce passage (motifs avant détecteurs), en lecture seule pour les détecteurs.
        # Spans already found in this pass (patterns before detectors), read-only for detectors.
        self.found: list[Span] = []
        self._features: dict[str, bool] = {}
        # Vue NFC d'un texte décomposé, faite une fois pour les détecteurs qui la lisent (`_compose`).
        # NFC view of a decomposed text, built once for the detectors that read it.
        self._composed: Any = None

    def has(self, feature: str | tuple[str, ...]) -> bool:
        """Préfiltre bon marché : 'digit' ou sous-chaînes cherchées dans le texte replié.

        Cheap prefilter: 'digit' or substrings searched in the folded text (any of them).
        """
        if isinstance(feature, tuple):
            return any(self.has(f) for f in feature)
        cached = self._features.get(feature)
        if cached is None:
            cached = (_DIGIT_RE.search(self.text) is not None) if feature == "digit" else feature in self.folded
            self._features[feature] = cached
        return cached

    def segment(self, pos: int) -> tuple[int, int, int]:
        if self.seg_starts is None:
            return -1, 0, len(self.text)
        index = bisect_right(self.seg_starts, pos) - 1
        return index, self.seg_starts[index], self.seg_ends[index]

    def any_context(self, groups: Sequence[str]) -> bool:
        counts = self.counts
        if any(g in counts for g in groups):
            return True
        if any(g in self._zone_groups for g in groups):
            return True
        return bool(self.forced) and any(any(g in f for g in groups) for f in self.forced)

    def _header_context(self, groups: Sequence[str], index: int, start: int, end: int) -> bool:
        """Contexte imposé par un en-tête de colonne (classeur ou tableau Markdown) / column-header context."""
        if self.forced is not None and index >= 0 and any(g in self.forced[index] for g in groups):
            return True
        if not self.zones:
            return False
        i = bisect_right(self._zone_starts, start) - 1
        return i >= 0 and end <= self.zones[i][1] and any(g in self.zones[i][2] for g in groups)

    def near(self, groups: Sequence[str], start: int, end: int, before: int, after: int, lo: int = 0,
             hi: int = 1 << 62) -> bool:
        """`lo`/`hi` bornent en plus la recherche (ligne, paragraphe) / further bound the search (line, block)."""
        index, seg_lo, seg_hi = self.segment(start)
        lo, hi = max(lo, seg_lo), min(hi, seg_hi)
        return (self._header_context(groups, index, start, end)
                or any(self.hits.near(g, start, end, before, after, lo, hi) for g in groups))

    def vetoed(self, groups: Sequence[str], vetoes: Sequence[str], start: int, end: int, after: int) -> bool:
        """Un mot-veto placé entre le dernier mot-clé et la valeur annule le contexte : l'indice le plus proche
        l'emporte (« né le 3 mai 1953. … la réunion du 12/02/2026 »). Les en-têtes ne sont jamais annulés ; un
        mot-clé après la valeur ne l'est que par un mot-veto collé devant elle, à 4 caractères au plus
        (« hospitalisée le 14/09/2026, née le … », `scanner.rs: VETO_ADJACENT`).

        A veto word between the last keyword and the value cancels the context: the nearest cue wins. Column
        headers are never vetoed; a keyword after the value only by a veto word right before the value (4
        characters at most).
        """
        index, lo, hi = self.segment(start)
        if self._header_context(groups, index, start, end):
            return False
        keyword = max(self.hits.last_end(g, start, lo) for g in groups)
        veto = max(self.hits.last_end(g, start, lo) for g in vetoes)
        veto_wins = veto >= 0 and veto > keyword
        if any(self.hits.near(g, start, end, 0, after, lo, hi) for g in groups):
            return veto_wins and start - veto <= 4
        return veto_wins

    def cue_spent(self, groups: Sequence[str], start: int, end: int, after: int) -> bool:
        """Liaison de l'indice de naissance (1.0.2, 2e test terrain, modes fort et essentiel) : « né le », « date de
        naissance » ne valent que pour la PREMIÈRE date qui les suit. Une date déjà passée entre le dernier indice et
        la valeur (`_date_seen`) annule le contexte (« né le 12 juin 1934 à Nantes, entré le 5 janvier 2024 », un
        journal horodaté sous « Date de naissance : … ») ; « nom de naissance » désigne un nom, pas une date. Les
        en-têtes et un indice placé après la valeur ne sont jamais annulés (`scanner.rs: cue_spent`).

        Birth cue binding: a birth cue binds only to the FIRST date after it. A date already passed between the
        last cue and the value cancels the context; "nom de naissance" (birth name) names a name, not a date.
        Column headers and a cue after the value are never cancelled.
        """
        index, lo, hi = self.segment(start)
        if self._header_context(groups, index, start, end):
            return False
        if any(self.hits.near(g, start, end, 0, after, lo, hi) for g in groups):
            return False
        keyword = max(self.hits.last_end(g, start, lo) for g in groups)
        if keyword < 0:
            return False
        if keyword >= len(_BIRTH_NAME) and self.text[keyword - len(_BIRTH_NAME):keyword].lower() == _BIRTH_NAME:
            return True
        return _date_seen(self.text, keyword, start)


class _FoundView(Sequence[Span]):
    """`ctx.found` des détecteurs Python du moteur fusionné : les zones du passage, lues dans Rust au premier
    usage, relues seulement si le passage a changé (aucun objet créé sans lecture). The fused engine's
    `ctx.found`: the pass's spans, read from Rust on first use, read again only once the pass has changed (no
    object built unless read). Lecture seule, comme `ctx.found` / read-only, as `ctx.found`. Chaque zone garde
    son objet, et un objet modifié est vu, comme dans la liste de Python / each span keeps its object, and a
    changed object is seen, as in Python's list.
    """

    __slots__ = ("_document", "_key", "_spans")

    def __init__(self, document: Any) -> None:
        self._document = document
        self._key: tuple[int, int] | None = None
        self._spans: list[Span] = []

    def _current(self) -> list[Span]:
        key = self._document.found_key
        if key != self._key:
            self._spans, self._key = self._document.found(True), key
        return self._spans

    def __getitem__(self, index: Any) -> Any:
        return self._current()[index]

    def __len__(self) -> int:
        return len(self._current())

    def __iter__(self) -> Iterator[Span]:
        return iter(self._current())


class _Host:
    """Code Python que le moteur fusionné appelle : `calls[i](ctx)` rend les zones d'un détecteur ou de
    recognizers sans jumeau, `context(document)` construit leur `DetectionContext`, `select(document)` choisit les
    pays du mode auto. Python code the fused engine calls: detectors and recognizers without a twin, their context,
    and the auto-mode country choice.
    """

    __slots__ = ("calls", "context", "select")

    def __init__(self, calls: Sequence[Callable[[DetectionContext], list[Span]]],
                 context: Callable[[Any], DetectionContext],
                 select: Callable[[Any], tuple[tuple[str, ...], dict[str, list[str]]]]) -> None:
        self.calls = tuple(calls)
        self.context = context
        self.select = select


# Ligne de délimitation GFM (au moins deux colonnes) / GFM delimiter row (two columns or more).
_TABLE_DELIMITER_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)+\|?[ \t\r]*$", re.MULTILINE)
_PIPE_RE = re.compile(r"(?<!\\)\|")


def _cells(line: str, offset: int) -> list[tuple[int, int]]:
    """Cellules d'une ligne GFM (barres échappées ignorées), positions absolues rognées.

    GFM row cells (escaped pipes ignored), trimmed absolute offsets.
    """
    edges = [-1, *(m.start() for m in _PIPE_RE.finditer(line)), len(line)]
    cells: list[tuple[int, int]] = []
    for left, right in pairwise(edges):
        start, end = left + 1, right
        while start < end and line[start].isspace():
            start += 1
        while end > start and line[end - 1].isspace():
            end -= 1
        cells.append((offset + start, offset + end))
    # Barres de bord : pas de cellule avant la première ni après la dernière / edge pipes open no cell.
    if len(edges) > 2 and not line[:edges[1]].strip():
        cells.pop(0)
    if len(edges) > 2 and cells and not line[edges[-2] + 1:].strip():
        cells.pop()
    return cells


def markdown_table_zones(text: str, groups_of: Callable[[str], frozenset[str]]) -> list[Zone]:
    """Cellules dont l'en-tête de colonne porte un contexte (« Date de naissance », « Passeport »…).

    Cells whose column header carries context ("Date de naissance", "Passeport"…): the header then acts as
    context for every cell below it, however far. Zones triées et disjointes / sorted, disjoint zones. Depuis
    1.0.2, aussi les tableaux CSV et TSV (`_text.delimited_tables`) ; leurs en-têtes sont lus avec « _ » et « - »
    changés en espaces (« date_naissance »), et une cellule déjà couverte par un tableau Markdown reste à lui.
    Since 1.0.2, CSV and TSV tables too; their headers are read with "_" and "-" as spaces, and a cell already
    covered by a Markdown table stays with it.
    """
    zones = _gfm_zones(text, groups_of) if "|" in text else []
    extra: list[Zone] = []
    for table in delimited_tables(text):
        columns = [groups_of(text[s:e].replace("_", " ").replace("-", " ")) for s, e in table[0]]
        if not any(columns):
            continue
        for row in table[1:]:
            for column, (start, stop) in enumerate(row):
                if column < len(columns) and columns[column] and stop > start:
                    extra.append((start, stop, columns[column]))
    if not extra:
        return zones
    if zones:
        starts = [z[0] for z in zones]
        extra = [z for z in extra if not _overlaps(zones, starts, z[0], z[1])]
        zones = sorted(zones + extra, key=lambda z: z[0])
        return zones
    return extra


def _overlaps(zones: list[Zone], starts: list[int], start: int, end: int) -> bool:
    """[start, end) chevauche-t-il une zone (triées, disjointes) ? / overlaps a sorted, disjoint zone?"""
    i = bisect_right(starts, start) - 1
    if i >= 0 and zones[i][1] > start:
        return True
    return i + 1 < len(zones) and zones[i + 1][0] < end


def _gfm_zones(text: str, groups_of: Callable[[str], frozenset[str]]) -> list[Zone]:
    """Tableaux Markdown (GFM) / Markdown tables."""
    zones: list[Zone] = []
    consumed = 0
    for delimiter in _TABLE_DELIMITER_RE.finditer(text):
        # Une délimitation dans un tableau déjà lu est une simple ligne (GFM) / inside a table, just a row.
        if delimiter.start() < consumed or delimiter.start() == 0:
            continue
        header_start = text.rfind("\n", 0, delimiter.start() - 1) + 1
        header = text[header_start:delimiter.start() - 1]
        if "|" not in header:
            continue
        columns = [groups_of(text[s:e]) for s, e in _cells(header, header_start)]
        pos = delimiter.end() + 1
        while pos < len(text):
            end = text.find("\n", pos)
            end = len(text) if end < 0 else end
            line = text[pos:end]
            if "|" not in line:
                break
            if any(columns):
                for column, (start, stop) in enumerate(_cells(line, pos)):
                    if column < len(columns) and columns[column] and stop > start:
                        zones.append((start, stop, columns[column]))
            pos = end + 1
        consumed = pos
    return zones


# --- Contrôles de bornes / boundary checks ---------------------------------------------------------


def _not_alnum(ch: str) -> bool:
    return not ch.isalnum()


def _boundary_checks() -> dict[str, tuple[Callable[[str, int], bool], Callable[[str, int], bool]]]:
    def left(pred: Callable[[str], bool]) -> Callable[[str, int], bool]:
        return lambda text, pos: pos == 0 or pred(text[pos - 1])

    def right(pred: Callable[[str], bool]) -> Callable[[str, int], bool]:
        return lambda text, pos: pos >= len(text) or pred(text[pos])

    def ip_right(text: str, pos: int) -> bool:
        if pos >= len(text):
            return True
        ch = text[pos]
        if ch.isalnum():
            return False
        return not (ch == "." and pos + 1 < len(text) and text[pos + 1].isdigit())

    # Groupes de chiffres regroupés librement (« 0764 945 16 3 ») : la valeur est toute la suite de groupes, jamais
    # sa fin ni son début (pas de chiffre + séparateur avant, ni de séparateur + chiffre après). Freely regrouped
    # digit groups: the value is the whole run of groups (no digit + separator before, no separator + digit after).
    def group_left(text: str, pos: int) -> bool:
        if pos == 0:
            return True
        ch = text[pos - 1]
        return not (ch.isalnum() or (ch in " ./-" and pos >= 2 and text[pos - 2].isdigit()))

    def group_right(text: str, pos: int) -> bool:
        if pos >= len(text):
            return True
        ch = text[pos]
        return not (ch.isalnum() or (ch in " ./-" and pos + 1 < len(text) and text[pos + 1].isdigit()))

    always = lambda text, pos: True  # noqa: E731
    return {
        "group": (group_left, group_right),
        "alnum": (left(_not_alnum), right(_not_alnum)),
        "word": (left(lambda c: not (c.isalnum() or c in "_.%+-")), right(lambda c: not (c.isalnum() or c == "_"))),
        "ip": (left(lambda c: not (c.isalnum() or c == ".")), ip_right),
        "hex": (left(lambda c: not (c.isalnum() or c == ":")), right(lambda c: not (c.isalnum() or c == ":"))),
        "phone": (left(lambda c: not (c.isalnum() or c == "+")), right(_not_alnum)),
        "digit": (left(lambda c: not c.isdigit()), right(lambda c: not c.isdigit())),
        "none": (always, always),
    }


_BOUNDARIES = _boundary_checks()

# Après un échec, chaque position suivante du même mot a un prédécesseur alphanumérique (ou chiffre) et
# échouerait à la borne gauche : on saute le mot entier, résultat identique. After a failure, every later
# position in the same run has an alnum (or digit) predecessor and would fail the left check: skip the run.
_SKIP_RUN = {"alnum": re.compile(r"[^\W_]+"), "digit": re.compile(r"\d+")}


def _next_start(skip: re.Pattern[str] | None, text: str, start: int) -> int:
    run = skip.match(text, start) if skip is not None else None
    return max(run.end(), start + 1) if run is not None else start + 1


# --- Résolution des chevauchements / overlap resolution ----------------------------------------------


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and not text[start].isalnum():
        start += 1
    while end > start and not text[end - 1].isalnum():
        end -= 1
    return start, end


def merge_same_entity(spans: list[Span]) -> list[Span]:
    """Fusionne les chevauchements d'un même type composite (personne, adresse…) / merge same-type overlaps."""
    merged: list[Span] = []
    by_entity: dict[str, list[Span]] = {}
    for span in spans:
        if span.entity in MERGEABLE_ENTITIES:
            by_entity.setdefault(span.entity, []).append(span)
        else:
            merged.append(span)
    for group in by_entity.values():
        group.sort(key=lambda s: (s.start, -s.end, -s.priority, s.source))
        current = group[0]
        for span in group[1:]:
            if span.start < current.end:
                if span.end > current.end or span.priority > current.priority:
                    current = replace(
                        current,
                        end=max(current.end, span.end),
                        priority=max(current.priority, span.priority),
                        score=max(current.score, span.score),
                        forms=current.forms + span.forms,
                        propagate=current.propagate or span.propagate,
                        value=None,
                        source=current.source if current.source == span.source else f"{current.source}+{span.source}",
                    )
                else:
                    current.propagate = current.propagate or span.propagate
            else:
                merged.append(current)
                current = span
        merged.append(current)
    return merged


def resolve(spans: list[Span], text: str) -> list[Span]:
    """Priorité, puis longueur, puis score ; les zones composites perdantes sont rognées, pas perdues.

    Priority, then length, then score; losing composite zones are trimmed, not dropped.
    """
    # Ordre total (source en dernier) : résultat indépendant de l'ordre de détection.
    # Total order (source last): result independent of detection order.
    order = sorted(spans, key=lambda s: (-s.priority, -(s.end - s.start), -s.score, s.start, s.source))
    starts: list[int] = []
    accepted: list[Span] = []
    for span in order:
        i = bisect_left(starts, span.end)
        j = i - 1
        overlaps: list[Span] = []
        while j >= 0 and accepted[j].end > span.start:
            overlaps.append(accepted[j])
            j -= 1
        if not overlaps:
            starts.insert(i, span.start)
            accepted.insert(i, span)
            continue
        if span.entity not in MERGEABLE_ENTITIES:
            continue
        cursor = span.start
        pieces: list[tuple[int, int]] = []
        for other in sorted(overlaps, key=lambda s: s.start):
            if other.start > cursor:
                pieces.append((cursor, other.start))
            cursor = max(cursor, other.end)
        if cursor < span.end:
            pieces.append((cursor, span.end))
        for piece_start, piece_end in pieces:
            piece_start, piece_end = _trim(text, piece_start, piece_end)
            if piece_end - piece_start >= 3:
                piece = replace(span, start=piece_start, end=piece_end, value=None)
                k = bisect_left(starts, piece_start)
                starts.insert(k, piece_start)
                accepted.insert(k, piece)
    return accepted


def _priority(rec: PatternRecognizer, value: str | None) -> int:
    """Clé fausse gardée sur contexte : priorité « contexte seul » / wrong key kept on context: context-only."""
    return PRIORITY_CONTEXT_ONLY if value is None and rec.fallback else rec.priority


def _line_bounds(text: str, start: int, end: int, before: int, after: int) -> tuple[int, int]:
    """Ligne de [start, end), bornée aux fenêtres (`KeywordHits.near` ne lit rien au-delà) : coût constant.

    The line of [start, end), bounded by the windows (`KeywordHits.near` reads nothing beyond): constant cost.
    """
    lo = text.rfind("\n", max(0, start - before - MAX_KEYWORD_LEN), start) + 1
    hi = text.find("\n", end, end + after)
    return lo, end + after if hi < 0 else hi


def _block_bounds(text: str, start: int, end: int, before: int, after: int) -> tuple[int, int]:
    """Paragraphe de [start, end) : entre deux lignes vides (blancs seuls), borné aux fenêtres.

    The paragraph of [start, end): between two blank lines (blanks only), bounded by the windows.
    """
    floor = max(0, start - before - MAX_KEYWORD_LEN)
    lo, newline, blank = floor, -1, True
    for i in range(start - 1, floor - 1, -1):
        c = text[i]
        if c == "\n":
            if newline >= 0 and blank:
                lo = newline + 1
                break
            newline, blank = i, True
        elif c not in " \t\r":
            blank = False
    ceiling = min(len(text), end + after)
    hi, newline, blank = ceiling, -1, True
    for i in range(end, ceiling):
        c = text[i]
        if c == "\n":
            if newline >= 0 and blank:
                hi = newline
                break
            newline, blank = i, True
        elif c not in " \t\r":
            blank = False
    return lo, hi


# Numéro d'un registre en tête de ligne (« n° RCS : … », « n° RM : … », avis du BODACC) / a register number field.
_REGISTER_LABELS = frozenset({"n° RCS :", "n° RM :", "n° RCS:", "n° RM:"})
# Marques d'une personne morale dans une ligne courte du document / legal-entity marks in a short line.
_ENTITY_WORDS = ("dénomination", "denomination", "raison sociale", "forme juridique", "société", "societe")
_ENTITY_FORMS = frozenset({"SA", "SAS", "SASU", "SARL", "EURL", "SCI", "SNC", "SCP", "SCM", "SCA", "SCOP", "SCEA",
                           "SELARL", "SELAS", "SELAFA", "SELURL", "SELCA", "GAEC", "EARL", "SEM", "GIE"})
_ASCII_CAPS_RE = re.compile(r"[A-Z]+")
_SHORT_LINE = 150


def _no_legal_entity(text: str, start: int) -> bool:
    """« n° RCS : 123 456 789 RCS Ville » d'un avis qui ne nomme aucune personne morale : un entrepreneur individuel.

    A register number field in a notice that names no legal entity: no short line (150 characters at most; a
    long free-text paragraph may cite the liquidator's firm) holds « Dénomination », « Raison sociale », « Forme
    juridique », « société » or a legal form (« SARL »). Then the number is a sole trader's, hence personal.
    """
    line_start = text.rfind("\n", 0, start) + 1
    if text[line_start:start].rstrip(" ") not in _REGISTER_LABELS:
        return False
    for line in text.split("\n"):
        if len(line) > _SHORT_LINE:
            continue
        low = line.lower()
        if any(word in low for word in _ENTITY_WORDS) \
                or any(token in _ENTITY_FORMS for token in _ASCII_CAPS_RE.findall(line)):
            return False
    return True


@cache
def _packs_for(countries: tuple[str, ...] | str) -> tuple[Pack, ...]:
    ids = available_packs() if countries in COUNTRY_MODES else tuple(dict.fromkeys(("INTL", *countries)))
    return tuple(load_pack(pack_id) for pack_id in ids)


@cache
def _keyword_groups(pack_ids: tuple[str, ...]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for pack_id in pack_ids:
        for group, words in load_pack(pack_id).context.items():
            groups.setdefault(group, []).extend(words)
    return groups


@cache
def _keyword_index(pack_ids: tuple[str, ...]) -> KeywordIndex:
    return KeywordIndex(_keyword_groups(pack_ids))


@cache
def _native_scanner(pack_ids: tuple[str, ...], keys: tuple[tuple[str, str], ...]) -> _native.NativeScanner | None:
    """Analyseur Rust compilé une fois par ensemble de packs / Rust scanner compiled once per pack set."""
    by_key = {(r.pack, r.id): r for pack_id in pack_ids for r in load_pack(pack_id).recognizers}
    return _native.build([by_key[k] for k in keys], _keyword_groups(pack_ids), fold)


class Anonymizer:
    """Point d'entrée principal ; réutilisable et sûr entre threads (état par appel).

    Main entry point; reusable and thread-safe (per-call state only).
    """

    def __init__(self, settings: Settings | None = None, **overrides: Any) -> None:
        settings = replace(settings or Settings(), **overrides) if overrides else (settings or Settings())
        if isinstance(settings.countries, str) and settings.countries.lower() in COUNTRY_MODES:
            settings = replace(settings, countries=settings.countries.lower())
        elif isinstance(settings.countries, str):
            settings = replace(settings, countries=tuple(c.strip() for c in settings.countries.split(",") if c.strip()))
        if isinstance(settings.countries, list):
            settings = replace(settings, countries=tuple(settings.countries))
        if isinstance(settings.countries, tuple):
            settings = replace(settings, countries=tuple(c.upper() for c in settings.countries))
        # Règles : objet validé, dict (JSON) ou fichier TOML/JSON (de confiance) / rules: object, dict or file path.
        if isinstance(settings.rules, Mapping):
            settings = replace(settings, rules=parse_rules(settings.rules))
        elif isinstance(settings.rules, (str, PurePath)):
            settings = replace(settings, rules=load_rules(settings.rules))
        settings.validate()
        # Mode canonique (alias et `profile` déprécié résolus) / canonical mode (aliases, deprecated profile).
        mode, disable = resolve_mode(settings.mode, settings.profile, settings.disable)
        settings = replace(settings, mode=mode, disable=disable)
        self._gate = Gate(mode, disable)
        self.settings = settings
        self._packs = _packs_for(settings.countries)
        self._keywords = _keyword_index(tuple(p.id for p in self._packs))
        self._recognizers: dict[str, list[PatternRecognizer]] = {}
        self._detectors: dict[str, list[Any]] = {}
        for pack in self._packs:
            allowed = [r for r in pack.recognizers if self._entity_allowed(r.entity)]
            self._recognizers[pack.id] = allowed
            self._detectors[pack.id] = pack.build_detectors()
        # Rust prend les recognizers qu'il sait traiter, Python garde les autres.
        # Rust takes the recognizers it supports, Python keeps the others.
        self._native: _native.NativeScanner | None = None
        self._python_recognizers = self._recognizers
        if settings.native and _native.available():
            keys = tuple((r.pack, r.id) for p in self._packs for r in self._recognizers[p.id])
            scanner = _native_scanner(tuple(p.id for p in self._packs), keys)
            if scanner is not None and scanner.supported:
                self._native = scanner
                self._python_recognizers = {
                    pack_id: [r for r in recs if (r.pack, r.id) not in scanner.supported]
                    for pack_id, recs in self._recognizers.items()
                }
        self._extra_detectors = list(settings.detectors)
        self._ei_groups = tuple(g for p in self._packs for g in p.context if g.endswith(":ei"))
        self._person_groups = tuple(g for p in self._packs for g in p.context if g.endswith(":natural_person"))
        self._entity_groups = tuple(g for p in self._packs for g in p.context if g.endswith(":legal_entity"))
        self._min_score = settings.min_score if settings.min_score is not None else _MIN_SCORE[
            settings.profile or "standard"]
        rules: RuleSet | None = settings.rules
        allow, deny = tuple(settings.allow_list), dict(settings.deny_list)
        if rules is not None:
            allow += rules.allow
            for label, terms in rules.deny.items():
                deny[label] = (*deny.get(label, ()), *terms)
        self._allow = frozenset(fold(term).strip() for term in allow)
        self._deny = self._build_deny(deny)
        # Règles personnalisées : compilées pour cette instance seulement, jamais en cache partagé.
        # Custom rules: compiled for this instance only, never in a shared cache.
        self._custom: list[PatternRecognizer] = rules.recognizers() if rules is not None else []
        self._custom_native: _native.NativeScanner | None = None
        self._custom_keywords: KeywordIndex | None = None
        if self._custom:
            groups = rules.keyword_groups()
            if settings.native and _native.available():
                # Règles non sûres : compilation bornée (un fil, budget mémoire commun) / bounded compile.
                self._custom_native = _native.build(self._custom, groups, fold, untrusted=not rules.trusted)
            unsupported = [] if self._custom_native is None else [
                (i, error) for i, (ok, error) in enumerate(zip(self._custom_native.flags, self._custom_native.errors,
                                                                strict=True), 1) if not ok]
            if not rules.trusted and (self._custom_native is None or unsupported):
                # Règles non sûres : moteur linéaire obligatoire (aucun retour arrière exponentiel possible).
                # Untrusted rules: linear-time engine required (no catastrophic backtracking possible).
                if self._custom_native is None:
                    raise RuleError("Règles personnalisées indisponibles : noyau Rust requis / Rust core required")
                index, error = unsupported[0]
                raise RuleError(f"Règle n°{index} ({rules.rules[index - 1].label}) : construction refusée par le "
                                f"moteur linéaire / refused by the linear-time engine: {(error or '')[:200]}")
            if unsupported:
                self._custom_native = None  # de confiance : repli sur Python / trusted: Python fallback
            if self._custom_native is None:
                self._custom_keywords = KeywordIndex(groups) if groups else None
        self._operators = {k: get_operator(v) for k, v in settings.operators.items()}
        self._default_operator = get_operator("replace")
        # Après la détection, tout en Rust si possible : mêmes zones, même texte, même rapport.
        # After detection, everything in Rust when possible: same spans, same text, same report.
        # Personnes coupées (mode personnalisé) : la finalisation Python, qui retire aussi les personnes qu'elle crée
        # (civilités, initiales, signatures). Persons switched off: Python finalisation, which also drops the persons
        # it creates.
        self._finalizer = self._native_finalizer() if settings.native and not self._gate.post_entities else None
        # Moteur fusionné : la détection aussi, en un appel par document, puis la finalisation avec ce finaliseur-là.
        # Hors du mode fort (voie perf, 26/10) : la détection fusionnée aussi, en un appel ; puis la porte du mode trie
        # en Python les zones détectées (`_gated`) et le même finaliseur Rust termine (mêmes zones, même texte
        # que le chemin par étapes). Fused engine: detection too, then finalisation with this very finalizer. Outside
        # mode fort, the same one-call detection; the mode gate then sorts the detected spans in Python and the same
        # Rust finalizer ends (same spans, same text as the staged path).
        self._host: _Host | None = None
        self._fused = self._fused_engine() if self._finalizer is not None else None
        self._fused_finalizer = self._finalizer

    def _fused_engine(self) -> Any:
        """Moteur Rust fusionné, composé des composants natifs déjà construits, ou None.

        Fused Rust engine, composed of the native components already built, or None: detection in one call,
        finalisation in a second / détection en un appel, finalisation en un second. Chaque détecteur décrit son
        jumeau (`native_plan`) ; un détecteur sans plan propre (classe dérivée comprise), les recognizers sans
        jumeau, la liste de refus et les règles en Python deviennent des appels Python. Each detector describes its
        twin; one without its own plan (subclasses included), recognizers without a twin, the deny list and Python
        rules become Python calls.
        """
        preparer, language = _native_preparer(), _native_language()
        if self._native is None or preparer is None or language is None:
            return None
        calls: list[Callable[[DetectionContext], list[Span]]] = []

        def python(function: Callable[[DetectionContext], list[Span]]) -> int:
            calls.append(function)
            return len(calls) - 1

        packs = []
        for pack in self._packs:
            slots = []
            for detector in self._detectors[pack.id]:
                own = "native_plan" in vars(type(detector))  # une classe dérivée peut changer `detect`
                plan = detector.native_plan() if own else None
                fallback = python(partial(self._detector_spans, detector))
                slots.append({"kind": "python", "call": fallback} if plan is None else {**plan, "fallback": fallback})
            left = self._python_recognizers[pack.id]  # sans équivalent natif / without a native equivalent
            packs.append({"id": pack.id, "country": pack.country, "always_on": pack.always_on, "slots": slots,
                          "recognizers": python(partial(self._recognizer_spans, pack.id)) if left else None})
        index = {pack.id: i for i, pack in enumerate(self._packs)}
        # Prototype de zone de chaque motif natif, priorité d'une clé fausse, pack / prototype, wrong-key priority.
        recognizers = [(Span(0, 0, r.entity, r.label, r.id, 0.0, r.priority), _priority(r, None), index[r.pack])
                       for r in self._native.recognizers]
        extras = [(python(partial(self._detector_spans, d)), f"detector:{getattr(d, 'id', type(d).__name__)}")
                  for d in self._extra_detectors]
        deny = python(self._deny_spans) if self._deny is not None else None
        custom: dict[str, Any] | None = None
        if self._custom and self._custom_native is not None:
            custom = {"scanner": self._custom_native._scanner,
                      "rules": [Span(0, 0, r.entity, r.label, r.id, 0.0, r.priority) for r in self._custom]}
        elif self._custom:
            custom = {"call": python(self._custom_spans)}
        # Packs actifs et `ctx.countries`, comme `_detect_all` / active packs and `ctx.countries`, as there.
        mode = self.settings.countries
        if mode == "auto":
            active, countries = [], ()
        elif mode == "all":
            active, countries = [True] * len(self._packs), tuple(p.country for p in self._packs if p.country)
        else:
            countries = tuple(c for c in mode if c != "INTL")
            chosen = set(countries)
            active = [p.always_on or p.country in chosen or p.id in chosen for p in self._packs]
        self._host = _Host(calls, self._fused_context, self._fused_select)
        return _native.engine(
            preparer=preparer, language=language, scanner=self._native._scanner, table=_native.unicode_table(),
            span_type=Span, recognizers=recognizers, packs=packs, auto=mode == "auto", active=active,
            countries=countries, strict=self.settings.profile == "strict", company_ids=self.settings.company_ids,
            facility_mask=self.settings.facility_ids == "mask", ei_groups=list(self._ei_groups),
            person_groups=list(self._person_groups), entity_groups=list(self._entity_groups),
            entities=None if self.settings.entities is None else set(self.settings.entities),
            excluded=set(self.settings.exclude_entities), extras=extras, deny=deny, custom=custom,
            marks=list(_COMMON_MARKS))

    def _native_finalizer(self) -> Any:
        """Finaliseur Rust, avec les données mêmes du chemin Python / Rust finalizer, fed the Python path's data."""
        rules = native_rules()
        if rules is None:
            return None
        operators = [(key, NATIVE_NAMES.get(operator)) for key, operator in self._operators.items()]
        native_operators = all(name for _, name in operators) and NATIVE_NAMES.get(self._default_operator) == "replace"
        try:
            return _native.finalizer(
                rules, Span, min_score=self._min_score, allow=sorted(self._allow),
                mergeable=sorted(MERGEABLE_ENTITIES), keep_entity=KEEP_ENTITY if self._custom else None,
                unmaskable=sorted(_UNMASKABLE), priority_validated=PRIORITY_VALIDATED,
                priority_propagated=PRIORITY_PROPAGATED, operators=operators if native_operators else None,
                forced_replace=sorted(FORCED_REPLACE), detector_reasons=sorted(_DETECTOR_REASONS.items()),
                recognizers=[(r.id, r.tier, r.validator is not None) for r in self._recognizer_index().values()])
        except (TypeError, ValueError, OverflowError):
            # Réglage hors du domaine natif (terme avec substitut isolé, seuil géant…) : la référence Python
            # le traite. Setting outside the native domain (lone surrogate, huge threshold…): Python handles it.
            return None

    # --- configuration ---

    def _entity_allowed(self, entity: str) -> bool:
        if entity in self.settings.exclude_entities:
            return False
        return self.settings.entities is None or entity in self.settings.entities

    @staticmethod
    def _build_deny(deny: Mapping[str, Sequence[str]]) -> KeywordIndex | None:
        groups: dict[str, list[str]] = {}
        for label, terms in deny.items():
            key = re.sub(r"[^A-Z0-9]+", "_", fold(label).upper()).strip("_") or "CUSTOM"
            if not key[0].isalpha():
                key = "X_" + key
            if terms:
                groups.setdefault(f"{_DENY_LABEL}:{key}", []).extend(terms)
        return KeywordIndex(groups) if groups else None

    @property
    def packs(self) -> tuple[Pack, ...]:
        return self._packs

    @property
    def native(self) -> bool:
        """Le noyau Rust est-il utilisé ? / is the Rust core in use?"""
        return self._native is not None

    def _scan_keywords(self, folded: str) -> Any:
        return self._native.keywords(folded) if self._native is not None else self._keywords.scan(folded)

    def context_groups(self, text: str) -> frozenset[str]:
        """Groupes de contexte présents dans un court texte (en-tête) / context groups in a short text."""
        return frozenset(self._keywords.groups_in(text))

    # --- moteur fusionné / fused engine ---

    def _fused_document(self, text: str) -> Any:
        """Texte détecté par le moteur fusionné (document Rust), ou None : chemin par étapes (pas de moteur,
        finaliseur remplacé, texte hors du domaine natif). Text detected by the fused engine, or None: staged path.
        """
        if self._fused is None or self._finalizer is not self._fused_finalizer:
            return None
        return self._fused.detect(text, self._host)

    def _fused_cells(self, texts: Sequence[str], forced: Sequence[frozenset[str]] | None) -> Any:
        """Cellules détectées par le moteur fusionné, ou None / cells detected by the fused engine, or None."""
        if self._fused is None or self._finalizer is not self._fused_finalizer:
            return None
        return self._fused.detect_cells(texts, forced, self._host)

    def _fused_context(self, document: Any) -> DetectionContext:
        """`DetectionContext` sur le texte, les mots-clés et les zones d'un document Rust, pour le code Python.

        `DetectionContext` over a Rust document's text, keywords and zones, for Python code.
        """
        segments = document.segments
        starts, ends = segments if segments is not None else (None, None)
        forced = document.forced
        zones = [(start, end, frozenset(groups)) for start, end, groups in document.zones]
        ctx = DetectionContext(document.text, document.folded, document.hits, document.countries, document.language,
                               self.settings, starts, ends, list(forced) if forced is not None else None, zones)
        ctx.found = _FoundView(document)  # type: ignore[assignment]
        return ctx

    def _fused_select(self, document: Any) -> tuple[tuple[str, ...], dict[str, list[str]]]:
        """Mode auto : pays tirés des preuves du premier passage, comme `_detect_all` / auto-mode countries.

        Preuves lues en Rust sans objet par zone ; une valeur non ASCII (casse de Python) passe par `evidence`.
        Evidence read in Rust without one object per span; a non-ASCII value (Python's case rules) uses `evidence`.
        """
        found = document.evidence()
        ibans, phones, tlds = found if found is not None else evidence(document.found())
        return select_countries(document.hits, self._packs, self.settings.default_countries, document.language,
                                ibans, phones, tlds)

    def _fused_countries(self, document: Any) -> tuple[tuple[str, ...], dict[str, list[str]]]:
        """Pays d'un document et leurs raisons, comme `_detect_all` / a document's countries and reasons."""
        mode = self.settings.countries
        if mode == "auto":
            return document.countries, document.reasons
        countries = document.countries
        return countries, {c: ["all" if mode == "all" else "explicit"] for c in countries}

    def _fused_fallback(self, document: Any) -> tuple[DetectionContext, list[Span], dict[str, list[str]], Any,
                                                      dict[str, float]] | None:
        """Entrées du chemin par étapes tirées d'un document que Rust ne finalise pas (zone Python hors du domaine
        natif, opérateur Python) ; None s'il n'y a pas de document ou si ses zones ont déjà été remises à Rust.
        Staged-path inputs from a document Rust does not finalise; None without a document or once its spans
        were handed over to Rust (the staged path then starts again).
        """
        detected = None if document is None else document.detected()
        if detected is None:
            return None
        ctx = self._fused_context(document)
        ctx.countries, reasons = self._fused_countries(document)
        return ctx, detected, reasons, _offset_array(document.offsets), dict(document.timings)

    def _fused_cells_fallback(self, document: Any) -> tuple[DetectionContext, list[Span], dict[str, list[str]],
                                                            list[tuple[str | None, Any]], dict[str, float]] | None:
        """`_fused_fallback` pour des cellules / for cells."""
        staged = self._fused_fallback(document)
        if staged is None:
            return None
        ctx, detected, reasons, _, timings = staged
        return ctx, detected, reasons, [(None, _offset_array(raw)) for raw in document.cell_offsets], timings

    # --- détection / detection ---

    def analyze(self, text: str) -> Analysis:
        t0 = perf_counter()
        document = self._fused_document(text)
        if document is not None and not self._gate.active:  # porte active : `_gated` d'abord / gate first
            t1 = perf_counter()
            spans = document.analyze(self._finalizer)
            if spans is not None:
                timings = dict(document.timings)
                timings["resolve"] = (perf_counter() - t1) * 1000
                timings["total"] = (perf_counter() - t0) * 1000
                countries, reasons = self._fused_countries(document)
                return Analysis(text, spans, countries, reasons, document.language, timings)
        ctx, detected, reasons, offsets, timings = self._fused_fallback(document) or self._detect_text(text)
        detected, _ = self._gated(ctx.text, detected)
        t1 = perf_counter()
        spans = self._final_spans(ctx, detected, offsets)
        timings["resolve"] = (perf_counter() - t1) * 1000
        timings["total"] = (perf_counter() - t0) * 1000
        return Analysis(text, spans, ctx.countries, reasons, ctx.language, timings)

    def _detect_text(self, text: str) -> tuple[DetectionContext, list[Span], dict[str, list[str]], Any,
                                               dict[str, float]]:
        """Normalisation, contexte et détection d'un texte / normalisation, context and detection of a text."""
        timings: dict[str, float] = {}
        t0 = perf_counter()
        native = self.settings.native
        norm, folded, offsets = prepare(text, native=native)
        hits = self._scan_keywords(folded)
        language = detect_language(folded, native=native)
        zones = markdown_table_zones(norm, self.context_groups)
        timings["prepare"] = (perf_counter() - t0) * 1000
        ctx = DetectionContext(norm, folded, hits, (), language, self.settings, zones=zones)
        spans, reasons = self._detect_all(ctx, timings)
        return ctx, spans, reasons, offsets, timings

    def _final_spans(self, ctx: DetectionContext, detected: list[Span], offsets: Any) -> list[Span]:
        """Zones finales en positions d'origine (Rust si possible) / final spans in original offsets."""
        if self._finalizer is not None:
            spans = self._finalizer.analyze(detected, ctx.text, _offset_bytes(offsets))
            if spans is not None:
                return spans
        spans = self._finalize(ctx, detected)
        if offsets is not None:
            for span in spans:
                span.start = offsets[span.start]
                span.end = offsets[span.end - 1] + 1
        return spans

    def analyze_segments(self, texts: Sequence[str], forced: Sequence[frozenset[str]] | None = None,
                         ) -> tuple[list[list[Span]], Analysis]:
        """Détecte sur plusieurs segments en un seul passage (cellules, lignes…).

        Detects over many segments in one pass (cells, lines…). Le contexte ne traverse pas les
        segments, sauf les groupes `forced` (en-têtes de colonnes), un ensemble par segment / context never
        crosses segments, except `forced` groups (column headers), one set per segment.
        """
        _check_forced(texts, forced)
        document = self._fused_cells(texts, forced)
        if document is not None and not self._gate.active:  # porte active : `_gated` d'abord / gate first
            found = document.analyze_cells(self._finalizer)
            if found is not None:
                per_segment, spans = found
                countries, reasons = self._fused_countries(document)
                return per_segment, Analysis(document.text, spans, countries, reasons, document.language,
                                             dict(document.timings))
        staged = self._fused_cells_fallback(document) or self._detect_segments(texts, forced)
        ctx, detected, reasons, normalized, timings = staged
        detected, _ = self._gated(ctx.text, detected)
        per_segment, spans = self._segment_spans(ctx, detected, normalized)
        return per_segment, Analysis(ctx.text, spans, ctx.countries, reasons, ctx.language, timings)

    def _detect_segments(self, texts: Sequence[str], forced: Sequence[frozenset[str]] | None,
                         ) -> tuple[DetectionContext, list[Span], dict[str, list[str]], list[tuple[str, Any]],
                                    dict[str, float]]:
        normalized = [normalize(t) for t in texts]
        seg_starts: list[int] = []
        seg_ends: list[int] = []
        pieces: list[str] = []
        cursor = 0
        for norm, _ in normalized:
            seg_starts.append(cursor)
            pieces.append(norm)
            cursor += len(norm)
            seg_ends.append(cursor)
            cursor += len(_SEGMENT_SEPARATOR)
        joined = _SEGMENT_SEPARATOR.join(pieces)
        folded = fold(joined)
        hits = self._scan_keywords(folded)
        language = detect_language(folded, native=self.settings.native)
        ctx = DetectionContext(joined, folded, hits, (), language, self.settings,
                               seg_starts, seg_ends, list(forced) if forced is not None else None)
        timings: dict[str, float] = {}
        detected, reasons = self._detect_all(ctx, timings)
        return ctx, detected, reasons, normalized, timings

    def _segment_spans(self, ctx: DetectionContext, detected: list[Span], normalized: list[tuple[str, Any]],
                       ) -> tuple[list[list[Span]], list[Span]]:
        """Zones par segment, en positions locales d'origine (Rust si possible) / per-segment spans."""
        if self._finalizer is not None:
            native = self._finalizer.analyze_segments(detected, ctx.text, ctx.seg_starts, ctx.seg_ends,
                                                      [_offset_bytes(offsets) for _, offsets in normalized])
            if native is not None:
                return native
        spans = self._finalize(ctx, detected)
        per_segment: list[list[Span]] = [[] for _ in normalized]
        for span in spans:
            index, lo, hi = ctx.segment(span.start)
            if span.end > hi:
                continue
            offsets = normalized[index][1]
            span.start -= lo
            span.end -= lo
            if offsets is not None:
                span.start = offsets[span.start]
                span.end = offsets[span.end - 1] + 1
            per_segment[index].append(span)
        return per_segment, spans

    def _detect_all(self, ctx: DetectionContext, timings: dict[str, float]) -> tuple[list[Span], dict[str, list[str]]]:
        """Pays explicites : un passage. Mode auto : packs toujours actifs, puis pays déduits des preuves validées.

        Explicit countries: one pass. Auto mode: always-on packs first, then countries inferred from the
        validated evidence they produced (IBAN, E.164 phones, e-mail domains) plus context keywords.
        """
        mode = self.settings.countries
        if mode == "all":
            ctx.countries = tuple(p.country for p in self._packs if p.country)
            packs = frozenset(p.id for p in self._packs)
            return self._detect(ctx, timings, packs, extras=True), {c: ["all"] for c in ctx.countries}
        if mode != "auto":
            ctx.countries = tuple(c for c in mode if c != "INTL")
            active = set(ctx.countries)
            packs = frozenset(p.id for p in self._packs if p.always_on or p.country in active or p.id in active)
            return self._detect(ctx, timings, packs, extras=True), {c: ["explicit"] for c in ctx.countries}
        spans = self._detect(ctx, timings, frozenset(p.id for p in self._packs if p.always_on), extras=False)
        ibans, phones, tlds = evidence(spans)
        ctx.countries, reasons = select_countries(ctx.hits, self._packs, self.settings.default_countries,
                                                  ctx.language, ibans, phones, tlds)
        active = set(ctx.countries)
        country_packs = frozenset(p.id for p in self._packs
                                  if not p.always_on and (p.country in active or p.id in active))
        spans.extend(self._detect(ctx, timings, country_packs, extras=True))
        return spans, reasons

    def _detect(self, ctx: DetectionContext, timings: dict[str, float], active_packs: frozenset[str],
                extras: bool) -> list[Span]:
        spans: list[Span] = []
        ctx.found = spans
        if self._native is not None and active_packs:
            t0 = perf_counter()
            segments = list(zip(ctx.seg_starts, ctx.seg_ends, strict=True)) if ctx.seg_starts is not None else None
            found = self._native.scan(ctx.hits, ctx.text, ctx.folded, active_packs, ctx.strict,
                                      self.settings.company_ids, self.settings.facility_ids == "mask",
                                      self._ei_groups, segments, ctx.forced, ctx.zones,
                                      person_groups=self._person_groups, entity_groups=self._entity_groups)
            recognizers = self._native.recognizers
            for start, end, index, value, score, personal, reason in found:
                rec = recognizers[index]
                spans.append(Span(start, end, rec.entity, rec.label, rec.id, score, _priority(rec, value), value,
                                  personal, reason=reason))
            timings["native"] = timings.get("native", 0.0) + (perf_counter() - t0) * 1000
        for pack in self._packs:
            if pack.id not in active_packs:
                continue
            t0 = perf_counter()
            spans.extend(self._recognizer_spans(pack.id, ctx))
            for detector in self._detectors[pack.id]:
                spans.extend(self._detector_spans(detector, ctx))
            timings[f"pack:{pack.id}"] = (perf_counter() - t0) * 1000
        if not extras:
            return spans
        for detector in self._extra_detectors:
            t0 = perf_counter()
            spans.extend(self._detector_spans(detector, ctx))
            timings[f"detector:{getattr(detector, 'id', type(detector).__name__)}"] = (perf_counter() - t0) * 1000
        if self._deny is not None:
            spans.extend(self._deny_spans(ctx))
        if self._custom:
            t0 = perf_counter()
            spans.extend(self._custom_spans(ctx))
            timings["custom"] = (perf_counter() - t0) * 1000
        return spans

    def _recognizer_spans(self, pack_id: str, ctx: DetectionContext) -> list[Span]:
        """Recognizers d'un pack laissés à Python (motif ou validateur sans équivalent natif).

        A pack's recognizers left to Python (pattern or validator without a native equivalent).
        """
        spans: list[Span] = []
        for recognizer in self._python_recognizers[pack_id]:
            if recognizer.prefilter and not ctx.has(recognizer.prefilter):
                continue
            # Sans aucun mot-clé dans le texte, inutile de lancer la regex / no keyword, skip the regex.
            needs_context = recognizer.tier == "C" or (recognizer.tier == "B" and not ctx.strict)
            if needs_context and not ctx.any_context(recognizer.contexts):
                continue
            self._run(recognizer, ctx, spans)
        return spans

    def _detector_spans(self, detector: Any, ctx: DetectionContext) -> list[Span]:
        """Zones d'un détecteur, entités choisies seulement / a detector's spans, chosen entities only."""
        return [s for s in detector.detect(ctx) if self._entity_allowed(s.entity)]

    def _custom_spans(self, ctx: DetectionContext) -> list[Span]:
        """Règles de l'organisation, avec leurs propres mots-clés / the organisation's rules, own keywords."""
        spans: list[Span] = []
        if self._custom_native is not None:
            hits = self._custom_native.keywords(ctx.folded)
            segments = list(zip(ctx.seg_starts, ctx.seg_ends, strict=True)) if ctx.seg_starts is not None else None
            found = self._custom_native.scan(hits, ctx.text, ctx.folded, frozenset({CUSTOM_PACK}), ctx.strict,
                                             "keep", False, (), segments)
            for start, end, index, value, score, _personal, _reason in found:
                rec = self._custom[index]
                spans.append(Span(start, end, rec.entity, rec.label, rec.id, score, rec.priority, value, True))
            return spans
        hits = self._custom_keywords.scan(ctx.folded) if self._custom_keywords is not None else KeywordHits()
        own = DetectionContext(ctx.text, ctx.folded, hits, ctx.countries, ctx.language, self.settings,
                               ctx.seg_starts, ctx.seg_ends)
        for rec in self._custom:
            self._run(rec, own, spans)
        return spans

    def _run(self, rec: PatternRecognizer, ctx: DetectionContext, out: list[Span]) -> None:
        text = ctx.text
        search = rec.regex.search
        check_left, check_right = _BOUNDARIES[rec.boundary]
        skip = _SKIP_RUN.get(rec.boundary)
        validator = rec.validator
        needs_context = rec.tier in ("B", "C")
        pos = 0
        # `search` ramène une position au-delà du texte à sa fin : sans ce test, une règle qui peut correspondre
        # à vide bouclerait à la fin. `search` clamps a position past the end back to it: without this check, a
        # rule that can match empty would loop forever at the end.
        while pos <= len(text):
            m = search(text, pos)
            if m is None:
                return
            full_start, full_end = m.span()
            # Échec : on relance plus loin, sans avaler de candidat / retry further on, swallowing no candidate.
            if not (check_left(text, full_start) and check_right(text, full_end)):
                pos = _next_start(skip, text, full_start)
                continue
            start, end = m.span(rec.group)
            if start < 0:
                pos = full_start + 1
                continue
            candidate = text[start:end]
            value: str | None = candidate
            score = rec.score
            if validator is not None:
                value = validator(candidate)
                if value is None:
                    # Clé fausse : gardé en niveau L, ou si un mot-clé explicite l'accompagne (faute de frappe, OCR).
                    # Wrong key: kept for tier L, or when an explicit keyword comes with it (typo, OCR error).
                    if not (rec.tier == "L" or (rec.fallback and ctx.near(rec.contexts, start, end, rec.before,
                                                                          rec.after))):
                        pos = _next_start(skip, text, full_start)
                        continue
                    score *= 0.6
            has_context = (bool(rec.contexts) and ctx.near(rec.contexts, start, end, rec.before, rec.after)
                           and not (rec.vetoes and ctx.vetoed(rec.contexts, rec.vetoes, start, end, rec.after))
                           # Une date de naissance : l'indice ne vaut que pour la première date / first date only.
                           and not (_DATE_VETO in rec.vetoes
                                    and ctx.cue_spent(rec.contexts, start, end, rec.after)))
            if needs_context and not has_context:
                if rec.tier == "C" or not ctx.strict:
                    pos = _next_start(skip, text, full_start)
                    continue
                score = 0.6
            elif has_context:
                score = min(1.0, score + 0.04)
            personal, reason = self._personal(rec, ctx, start, end)
            out.append(Span(start, end, rec.entity, rec.label, rec.id, score, _priority(rec, value), value,
                            personal, reason=reason))
            pos = full_end if full_end > full_start else full_start + 1

    def _personal(self, rec: PatternRecognizer, ctx: DetectionContext, start: int, end: int,
                  ) -> tuple[bool, str | None]:
        """Politique des identifiants de personnes morales : (personnel ?, raison propre ou None).

        Legal-entity identifier policy: (personal?, specific reason or None).
        """
        if rec.policy is None:
            return True, None
        if rec.policy == "facility":
            return self.settings.facility_ids == "mask" or ctx.strict, None
        mode = self.settings.company_ids
        if mode != "auto":
            return mode == "mask", None
        if ctx.strict:
            return True, None
        # « Entrepreneur individuel » dans le paragraphe du numéro, ou ailleurs sans personne morale près du numéro
        # (1.0.2 : un seul repère masquait le SIREN d'une société nommée 300 mots plus loin). L'état civil d'une
        # personne physique (prénom, date de naissance) à côté du numéro désigne aussi son titulaire. "Sole trader"
        # in the number's paragraph, or elsewhere when no legal entity is near the number; a natural person's civil
        # status next to the number also names its holder.
        if self._ei_groups and self._sole_trader(ctx, start, end):
            return True, "sole_trader"
        if self._person_groups and self._civil_status(ctx, start, end):
            return True, "civil_status_nearby"
        if _no_legal_entity(ctx.text, start):
            return True, "no_legal_entity"
        return False, None

    def _sole_trader(self, ctx: DetectionContext, start: int, end: int) -> bool:
        """« Entrepreneur individuel », « EI », « auto-entrepreneur »… : rend le numéro personnel (1.0.2).

        A sole-trader cue in the number's paragraph (its line, or the lines around it up to a blank line, within the
        natural-person window); or anywhere in the document when no legal entity (« société », « SAS »…) is near
        the number in that paragraph. Runs in every mode (fort and essentiel).
        """
        lo, hi = _block_bounds(ctx.text, start, end, *NATURAL_PERSON_WINDOW)
        if ctx.near(self._ei_groups, start, end, *NATURAL_PERSON_WINDOW, lo, hi):
            return True
        return ctx.any_context(self._ei_groups) and not (
            self._entity_groups and ctx.near(self._entity_groups, start, end, *LEGAL_ENTITY_WINDOW, lo, hi))

    def _civil_status(self, ctx: DetectionContext, start: int, end: int) -> bool:
        """État civil d'une personne physique à côté du numéro, sans personne morale plus près.

        Sur la ligne du numéro : une personne morale l'emporte (« Employeur : TESTIVO, … SIRET … »), sinon l'état
        civil suffit (« M. Jean Dupont, né le …, RM … »). Ligne muette : le paragraphe, sans personne morale proche
        (« n° RCS : … ⏎ Nom : … ⏎ Prénom : … »). Jamais au-delà d'une ligne vide. On the number's line, a legal entity
        wins, otherwise the civil status is enough; on a silent line, the paragraph, with no nearby legal entity.
        Never past a blank line.
        """
        text = ctx.text
        line_lo, line_hi = _line_bounds(text, start, end, *NATURAL_PERSON_WINDOW)
        if self._entity_groups and ctx.near(self._entity_groups, start, end, *LEGAL_ENTITY_WINDOW, line_lo, line_hi):
            return False
        if ctx.near(self._person_groups, start, end, *NATURAL_PERSON_WINDOW, line_lo, line_hi):
            return True
        lo, hi = _block_bounds(text, start, end, *NATURAL_PERSON_WINDOW)
        return ctx.near(self._person_groups, start, end, *NATURAL_PERSON_WINDOW, lo, hi) and not (
            self._entity_groups and ctx.near(self._entity_groups, start, end, *LEGAL_ENTITY_WINDOW, lo, hi))

    def _deny_spans(self, ctx: DetectionContext) -> list[Span]:
        hits = self._deny.scan(ctx.folded) if self._deny else None
        spans: list[Span] = []
        if hits is None:
            return spans
        for group in hits.groups():
            label = group.split(":", 1)[1]
            for start, end in hits.occurrences(group):
                spans.append(Span(start, end, "CUSTOM", label, "deny_list", 1.0, 99, ctx.folded[start:end]))
        return spans

    def _finalize(self, ctx: DetectionContext, spans: list[Span]) -> list[Span]:
        zones = _keep_zones(spans) if self._custom else None
        spans = _apply_keep(spans, zones)
        text = ctx.text
        minimum = self._min_score
        allow = self._allow
        kept = []
        for span in spans:
            if span.score < minimum or span.end <= span.start:
                continue
            if allow and fold(text[span.start:span.end]).strip() in allow:
                continue
            if span.entity == "PERSON":
                _trim_honorific(span, text)
                if span.end <= span.start:
                    continue
            if span.value is None and span.entity in MERGEABLE_ENTITIES:
                span.value = text[span.start:span.end]
            kept.append(span)
        post = self._gate.post_entities  # entités coupées par le mode (personnes) / switched off by the mode
        if not kept:
            resolved = _initials([], text, ctx.folded)  # les initiales ne dépendent d'aucune zone / need no span
            _keep_after(zones, resolved)
            return [s for s in resolved if s.entity not in post] if post else resolved
        resolved = resolve(merge_same_entity(kept), text)
        resolved = self._propagate(ctx, resolved)
        resolved = self._propagate_values(ctx, resolved)
        resolved = _drop_company_names(text, resolved)
        _extend_after_civility(resolved, text)
        resolved = _civility_surnames(resolved, text)
        resolved = _signature_names(resolved, text)
        resolved = _initials(resolved, text, ctx.folded)
        resolved = output_check(text, ctx.folded, resolved)  # contrôle final de sortie / output self-check
        _keep_after(zones, resolved)
        if post:
            resolved = [s for s in resolved if s.entity not in post]
        for span in resolved:
            if span.value is None:
                span.value = text[span.start:span.end]
        resolved.sort(key=lambda s: s.start)
        return resolved

    def _propagate(self, ctx: DetectionContext, spans: list[Span]) -> list[Span]:
        """Masque toutes les autres occurrences des noms trouvés / masks every other occurrence of found names."""
        text = ctx.text
        sources: dict[str, Span] = {}
        for span in spans:
            if not span.propagate or not span.personal:
                continue
            for form in (text[span.start:span.end], *span.forms):
                form = form.strip()
                if len(form) >= 3 and any(c.isalpha() for c in form):
                    sources.setdefault(form, span)
                    upper = form.upper()
                    if upper != form:
                        sources.setdefault(upper, span)
        if not sources:
            return spans
        forms = list(sources)
        ordered = sorted(spans, key=lambda s: s.start)
        starts = [s.start for s in ordered]
        added = False
        for index, start, end in longest_matches(forms, text):
            if (start > 0 and text[start - 1].isalnum()) or (end < len(text) and text[end].isalnum()):
                continue
            if _after_saint(text, start):
                continue  # « Saint-Claude » : une commune, pas la personne « CLAUDE Martin » (1.0.2) / a town
            source = sources[forms[index]]
            if not _place(ctx, ordered, starts, start, end, source, None):
                continue
            added = True
        return ordered if added else spans

    def _propagate_values(self, ctx: DetectionContext, spans: list[Span]) -> list[Span]:
        """Propagation universelle des valeurs (1.0.2, docs/REGLES.md « Propagation des valeurs ») : chaque valeur
        personnelle trouvée est masquée partout, sous toutes ses graphies, avec la même balise (valeur héritée).
        Universal value propagation: every personal value found is masked everywhere, in every written variant,
        with the same tag (inherited value). Familles / families: noms de plusieurs mots repliés, dates de
        naissance (formes générées), téléphones (numéro national de 9 chiffres), codes (squelette alphanumérique).
        """
        text, folded = ctx.text, ctx.folded
        spans = sorted(spans, key=lambda s: s.start)
        names: dict[str, tuple[Span, str]] = {}
        dates: dict[str, tuple[Span, str]] = {}
        phones: dict[str, tuple[Span, str]] = {}
        codes: dict[str, tuple[Span, str]] = {}
        for span in spans:
            if not span.personal:
                continue
            surface = text[span.start:span.end]
            if span.entity == "PERSON":
                if not span.propagate:
                    continue
                for form in (surface, *span.forms):
                    form = form.strip()
                    if " " in form and "\n" not in form and len(form) >= 5:
                        names.setdefault(fold(form), (span, form))
            elif span.entity == "BIRTH_DATE":
                iso = _iso_date(span.value) or _iso_date(surface)
                if iso is not None:
                    span.value = iso  # valeur canonique ISO / canonical ISO value
                    for form in _date_forms(iso):
                        dates.setdefault(form, (span, iso))
            elif span.entity == "PHONE":
                national = _national_number(_skeleton_of(surface))
                if national is not None:
                    phones.setdefault(national, (span, span.value if span.value is not None else surface))
            elif span.entity in _SKELETON_ENTITIES:
                key = _skeleton_of(surface)
                digits = sum(c in "0123456789" for c in key)
                if digits and (len(key) >= _SKELETON_MIN if digits < len(key) else len(key) >= _DIGITS_MIN):
                    codes.setdefault(key, (span, span.value if span.value is not None else surface))
        if not (names or dates or phones or codes):
            return spans
        ordered = spans
        starts = [s.start for s in ordered]
        for table in (names, dates):
            if not table:
                continue
            forms = list(table)
            for index, start, end in longest_matches(forms, folded):
                if (start > 0 and text[start - 1].isalnum()) or (end < len(text) and text[end].isalnum()):
                    continue
                source, value = table[forms[index]]
                _place(ctx, ordered, starts, start, end, source, value)
        if phones or codes:
            skeleton, positions = _skeleton_positions(folded)
            for table, phone in ((phones, True), (codes, False)):
                if not table:
                    continue
                hits = []
                keys = list(table)
                for order, (key, found) in enumerate(zip(keys, _all_occurrences(keys, skeleton), strict=True)):
                    hits.extend((s, e, order, key) for s, e in _skeleton_hits(text, folded, skeleton, positions,
                                                                              key, phone, found))
                hits.sort(key=lambda h: (h[0], h[0] - h[1], h[2]))
                last = -1
                for start, end, _order, key in hits:
                    if start < last:
                        continue
                    last = end
                    source, value = table[key]
                    _place(ctx, ordered, starts, start, end, source, value)
        return ordered

    # --- anonymisation ---

    def anonymize(self, text: str, scope: Scope | None = None) -> AnonymizedText:
        """Remplace chaque zone détectée ; la portée locale est détruite à la fin.

        Replaces every detected zone; a locally-created scope is destroyed at the end. Avec le moteur fusionné,
        un document ne quitte pas Rust de la détection au rendu, et aucun objet `Span` n'est créé tant qu'on ne
        lit pas `analysis.spans` ; une portée locale y naît et y meurt. With the fused engine, a document stays in
        Rust from detection to rendering, and no `Span` object is built unless `analysis.spans` is read; a local
        scope lives only there.
        """
        t0 = perf_counter()
        native_scope = _native_scope(scope)
        document = self._fused_document(text) if scope is None or native_scope is not None else None
        if document is not None and not self._gate.active:  # porte active : `_gated` d'abord / gate first
            t1 = perf_counter()
            language = document.language
            # `explain` vrai au sens de Python (1, "oui"…), comme `_render_text` ; `sanitize_output` en Rust (jumeau
            # exact). Python truthiness, as there; `sanitize_output` in Rust (exact twin).
            done = document.anonymize(self._finalizer, native_scope, self._labels(scope, language, _display_all),
                                      bool(self.settings.explain), bool(self.settings.sanitize))
            if done is not None:
                output, replaced, kept, explain, spans = done
                timings = dict(document.timings)
                timings["resolve"] = (perf_counter() - t1) * 1000
                timings["total"] = (perf_counter() - t0) * 1000
                countries, reasons = self._fused_countries(document)
                analysis = Analysis.deferred(text, spans.objects, countries, reasons, language, timings)
                return AnonymizedText(output, analysis,
                                      self._report(language, countries, reasons, timings, replaced, kept, explain))
        ctx, detected, reasons, offsets, timings = self._fused_fallback(document) or self._detect_text(text)
        detected, left = self._gated(ctx.text, detected)
        t1 = perf_counter()
        native = None
        if self._finalizer is not None and (scope is None or native_scope is not None):
            native = self._finalizer.anonymize(detected, ctx.text, _offset_bytes(offsets), text, native_scope,
                                               self._labels(scope, ctx.language), bool(self.settings.explain))
        if native is not None:
            output, spans, replaced, kept, explain = native
        else:
            spans = self._final_spans(ctx, detected, offsets)
            output, replaced, kept, explain = self._render_text(text, spans, scope, ctx.language)
        # Tout l'après-détection : résolution, propagation et rendu / all post-detection work.
        timings["resolve"] = (perf_counter() - t1) * 1000
        if self.settings.sanitize:
            output = sanitize_output(output)
        timings["total"] = (perf_counter() - t0) * 1000
        analysis = Analysis(text, spans, ctx.countries, reasons, ctx.language, timings)
        return AnonymizedText(output, analysis,
                              self._report(ctx.language, ctx.countries, reasons, timings, replaced, kept, explain,
                                           left))

    def _labels(self, scope: Scope | None, language: str, display: Callable[..., Any] = LABELS.display,
                ) -> tuple[Callable[..., Any], str, bool]:
        """Libellés affichés comme `Scope.label_text` : (fonction, langue, neutre) / displayed labels."""
        if scope is not None:
            return display, scope.label_language, scope.neutral
        return display, self._label_language(language), self.settings.neutral_labels

    def _render_text(self, text: str, spans: list[Span], scope: Scope | None, language: str,
                     ) -> tuple[str, Mapping[str, int], Mapping[str, int], list[dict[str, Any]] | None]:
        """Rendu Python d'un texte ; une portée locale est détruite à la fin / Python rendering of one text."""
        own_scope = scope is None
        if scope is None:
            scope = self.new_scope(language)
        explain: list[dict[str, Any]] | None = [] if self.settings.explain else None
        try:
            scope.reserve(text)
            output, replaced, kept = self._render(text, spans, scope, explain)
        finally:
            if own_scope:
                scope.close()
        return output, replaced, kept, _aggregate(explain) if explain is not None else None

    def anonymize_segments(self, texts: Sequence[str], scope: Scope,
                           forced: Sequence[frozenset[str]] | None = None) -> tuple[list[str], dict[str, Any]]:
        """Anonymise des segments (cellules) avec une portée partagée / segments with a shared scope.

        Avec le moteur fusionné : détection et rendu en Rust, aucun objet Python par zone / with the fused
        engine: detection and rendering in Rust, no Python object per span.
        """
        _check_forced(texts, forced)
        native_scope = _native_scope(scope)
        document = self._fused_cells(texts, forced) if native_scope is not None else None
        if document is not None and not self._gate.active:  # porte active : `_gated` d'abord / gate first
            done = document.anonymize_cells(self._finalizer, native_scope,
                                            self._labels(scope, document.language, _display_all),
                                            bool(self.settings.explain), bool(self.settings.sanitize))
            if done is not None:
                outputs, replaced, kept, explain = done
                countries, reasons = self._fused_countries(document)
                return outputs, self._report(document.language, countries, reasons, dict(document.timings),
                                             replaced, kept, explain)
        staged = self._fused_cells_fallback(document) or self._detect_segments(texts, forced)
        ctx, detected, reasons, normalized, timings = staged
        detected, left = self._gated(ctx.text, detected)
        native = None
        if self._finalizer is not None and native_scope is not None:
            native = self._finalizer.anonymize_segments(
                detected, ctx.text, ctx.seg_starts, ctx.seg_ends, [_offset_bytes(o) for _, o in normalized],
                list(texts), native_scope, self._labels(scope, ctx.language), bool(self.settings.explain))
        if native is not None:
            outputs, replaced, kept, explain = native
            if self.settings.sanitize:
                outputs = [sanitize_output(out) for out in outputs]
        else:
            per_segment, _ = self._segment_spans(ctx, detected, normalized)
            outputs = []
            replaced, kept = Counter(), Counter()
            entries: list[dict[str, Any]] | None = [] if self.settings.explain else None
            for text, segment_spans in zip(texts, per_segment, strict=True):
                out, rep, kep = self._render(text, segment_spans, scope, entries)
                outputs.append(sanitize_output(out) if self.settings.sanitize else out)
                replaced.update(rep)
                kept.update(kep)
            explain = _aggregate(entries) if entries is not None else None
        return outputs, self._report(ctx.language, ctx.countries, reasons, timings, replaced, kept, explain, left)

    def new_scope(self, language: str = "und") -> Scope:
        return Scope(self._label_language(language), self.settings.neutral_labels, native=self.settings.native)

    def _label_language(self, detected: str) -> str:
        if self.settings.label_language != "auto":
            return self.settings.label_language
        return "fr" if detected in ("fr", "und") else "en"

    def _render(self, text: str, spans: Sequence[Span], scope: Scope, explain: list[dict[str, Any]] | None = None,
                ) -> tuple[str, Counter[str], Counter[str]]:
        parts: list[str] = []
        replaced: Counter[str] = Counter()
        kept: Counter[str] = Counter()
        last = 0
        for span in spans:
            if not span.personal:
                kept[span.label] += 1
                if explain is not None:
                    explain.append({"kept": scope.label_text(span.label), "rule": _rule_of(span),
                                    "reason": "keep_rule" if span.source.startswith("keep:") else "company_policy"})
                continue
            original = text[span.start:span.end]
            operator = self._operators.get(span.entity) or self._operators.get(span.label) or self._default_operator
            if span.entity in FORCED_REPLACE:
                operator = self._default_operator
            parts.append(text[last:span.start])
            output = operator(span, original, scope)
            parts.append(output)
            last = span.end
            replaced[scope.label_text(span.label)] += 1
            if explain is not None:
                # La balise produite, jamais la valeur d'origine / the produced tag, never the original value.
                explain.append({"tag": output, "rule": _rule_of(span), "reason": self._reason(span)})
        parts.append(text[last:])
        return "".join(parts), replaced, kept

    def _reason(self, span: Span) -> str:
        """Raison stable et documentée d'une détection (docs/EXPLAIN.md) / stable, documented reason code."""
        source = span.source.split("+", 1)[0]
        if source.startswith("propagated:"):
            return "propagation"
        if source == "deny_list":
            return "deny_list"
        if source.startswith("CUSTOM_"):
            return "custom_rule"
        if span.reason is not None:
            return span.reason  # raison propre à la règle (« civil_status_nearby ») / the rule's own reason
        if source == "INTL_IBAN":
            return "validated" if span.value is not None else "iban_layout_despite_invalid_key"
        reason = _DETECTOR_REASONS.get(source) or ("ner_model" if source.lower().startswith("ner") else None)
        if reason is not None:
            return reason
        rec = self._recognizer_index().get(source)
        if rec is None:
            return "detector"
        # « validated » : clé de contrôle ou règles officielles vérifiées (plan de numérotation, calendrier…).
        # "validated": checksum or official rules checked (numbering plan, calendar…).
        if rec.tier == "L":
            return "validated" if span.value is not None else "printed_layout"
        if rec.validator is not None and span.value is None:
            return "keyword_despite_invalid_key"  # clé fausse, mot-clé explicite / wrong key, explicit keyword
        if rec.validator is not None:
            return "validated" if rec.tier == "A" else "validated_and_keyword"
        return "format" if rec.tier == "A" else "keyword"

    def _recognizer_index(self) -> dict[str, PatternRecognizer]:
        return _recognizers_by_id(tuple(p.id for p in self._packs))

    def _report(self, language: str, countries: Sequence[str], reasons: dict[str, list[str]],
                timings: Mapping[str, float], replaced: Mapping[str, int], kept: Mapping[str, int],
                explain: list[dict[str, Any]] | None = None,
                left: Sequence[tuple[str, str]] | None = None) -> dict[str, Any]:
        """Rapport ; `explain` : lignes déjà agrégées (`_aggregate`) ; `left` : (catégorie, règle) des zones que le
        mode laisse en clair. Report; `explain`: aggregated lines; `left`: (category, rule) of the spans the mode
        leaves in clear."""
        report = self._report_body(language, countries, reasons, timings, replaced, kept, explain)
        # Mode (docs/REGLES.md « Modes ») : nom canonique, catégories coupées, zones laissées en clair par catégorie,
        # avertissement qui nomme ce qui reste en clair ; `explain` : une ligne par (catégorie, règle), raison
        # « mode_essentiel » ou « mode_personnalise ». Mode, disabled categories, spans left in clear per category, a
        # warning naming what stays in clear; `explain`: one line per (category, rule).
        report["mode"] = self.settings.mode
        report["disable"] = list(self.settings.disable)
        if self._gate.active:
            report["left_in_clear_by_mode"] = dict(sorted(Counter(category for category, _ in left or ()).items()))
        warning = mode_warning(self.settings.mode, self.settings.disable)
        if warning is not None:
            report["warnings"] = [*report.get("warnings", ()), warning]
        if explain is not None and left:
            # Ordre stable, le même dans les deux moteurs / stable order, the same in both engines.
            report["explain"] = [*explain, *_aggregate([{"left_in_clear": category, "rule": rule,
                                                         "reason": f"mode_{self.settings.mode}"}
                                                        for category, rule in sorted(left)])]
        return report

    def _gated(self, text: str, detected: list[Span]) -> tuple[list[Span], list[tuple[str, str]]]:
        """Porte du mode : (zones gardées, (catégorie, règle) des zones laissées en clair). Mode fort : tout passe.

        Mode gate: (kept spans, (category, rule) of the spans left in clear). Mode fort: everything passes.
        """
        gate = self._gate
        if not gate.active:
            return detected, []
        kept: list[Span] = []
        left: list[tuple[str, str]] = []
        zones: list[tuple[int, int]] = []
        for span in detected:
            category = gate.left_in_clear(span, text)
            if category is None:
                kept.append(span)
            else:
                rule = _rule_of(span)
                left.append((category, rule))
                # Une règle du seul mode fort (« @pseudo » sans indice) ne protège pas la règle à indice de la même
                # zone (« X : @jpdupont ») / a fort-only rule never shields the cued rule on the same span.
                if category not in _CATCH_ALL and rule not in _FORT_ONLY_RULES:
                    zones.append((span.start, span.end))
        if not zones:
            return kept, left
        # Une zone laissée en clair l'est en entier : les zones d'autres règles qu'elle contient (la carte dans un
        # IBAN, le code dans un pseudonyme) restent en clair, sauf les règles de l'organisation. Sauf les règles
        # attrape-tout (codes, nombres longs) : coupées, elles ne protègent jamais un passeport, une CNI, un IBAN ou
        # un NIR qu'elles recouvrent (essentiel les laissait en clair). A zone left in clear is left whole: other
        # rules' spans inside it stay in clear too, except the organisation's rules; the catch-all rules (codes, long
        # numbers) never shield the validated identifier they overlap.
        zones.sort()
        starts = [start for start, _ in zones]
        reach = list(accumulate((end for _, end in zones), max))

        def inside(span: Span) -> bool:
            i = bisect_right(starts, span.start) - 1
            return i >= 0 and reach[i] >= span.end and not (
                span.source.startswith(("CUSTOM_", "keep:")) or span.source == "deny_list")

        return [span for span in kept if not inside(span)], left

    def _report_body(self, language: str, countries: Sequence[str], reasons: dict[str, list[str]],
                     timings: Mapping[str, float], replaced: Mapping[str, int], kept: Mapping[str, int],
                     explain: list[dict[str, Any]] | None) -> dict[str, Any]:
        mode = self.settings.countries if isinstance(self.settings.countries, str) else "explicit"
        report: dict[str, Any] = {
            "entities": dict(sorted(replaced.items())),
            "kept_by_policy": dict(sorted(kept.items())),
            "total_replaced": sum(replaced.values()),
            "country_mode": mode,
            "countries": list(countries),
            "country_reasons": reasons,
            "language": language,
            "profile": self.settings.profile,
            "native": self.native,
            "timings_ms": {k: round(v, 3) for k, v in timings.items()},
            "irreversible": True,
            "notice": NOTICE_FR if self._label_language(language) == "fr" else NOTICE_EN,
        }
        warnings = ["country_mode=auto est expérimental / is experimental"] if mode == "auto" else []
        if "FR" not in countries:
            warnings.append(NAMES_FRENCH_ONLY)
        if warnings:
            report["warnings"] = warnings
        if self.settings.rules is not None:
            report["rules"] = self.settings.rules.name
        if explain is not None:
            report["explain"] = explain
        return report


# Raisons des détecteurs (docs/EXPLAIN.md) / detector reason codes.
# Catégories attrape-tout : coupées, leurs zones ne protègent pas les autres règles / catch-all categories: their
# switched-off spans never shield other rules' spans.
_CATCH_ALL = frozenset({"codes", "nombres_longs"})
_DETECTOR_REASONS = {
    "EMAIL": "format", "INTL_MRZ": "format", "INTL_PHONE": "phone_numbering_plan", "FR_NAMES": "name_lexicon",
    "FR_ADDRESS": "postcode_and_town", "ORGANIZATIONS": "legal_form", "FR_NIR_BIRTH_DATE": "matches_nir",
    "NER": "ner_model",
    # Filtre fort 1.0.2 (REGLES.md § 4) / strong filter 1.0.2.
    "ID_CODE": "identifier_code", "FR_PHONE_COMPACT": "phone_numbering_plan",
    "FR_PHONE_FRAGMENT": "phone_fragment", "SECRET_SESSION": "keyword", "SECRET_API_KEY": "keyword",
    "SECRET_BASIC_AUTH": "keyword", "ID_BIOMETRIC": "keyword", "LOGIN": "keyword", "FR_PSEUDONYM": "keyword",
    "FR_PSEUDONYM_QUOTED": "keyword", "SECRET_COOKIE": "keyword", "FR_LABELLED_NUMBER": "keyword",
    "FR_LABELLED_NUMBER_START": "keyword", "ID_LONG_NUMBER": "long_number",
    # 1.0.2, second tour (items H, J) : valeurs liées à leur libellé / values bound to their label.
    "LOGIN_BARE": "keyword", "LOGIN_BARE_WORD": "keyword", "LOGIN_BARE_WORD_NOUN": "keyword",
    "SECRET_PASSWORD_PHRASE": "keyword",
    "SECRET_URL_PARAM": "keyword", "SECRET_ASSIGNMENT": "keyword", "FR_ORDER_NUMBER": "keyword",
    "FR_IBAN_LABELLED": "keyword",
    "URL_PERSONAL_NAME": "personal_site_name",
    # 1.0.2, dernier tour (voie « codes ») : pseudonymes, comptes et identifiants de plateforme annoncés.
    # Last round: announced pseudonyms, accounts and platform handles.
    "HANDLE_CUED": "keyword", "HANDLE_PLATFORM": "keyword", "HANDLE_PLATFORM_TEAMS": "keyword",
    "LOGIN_DOMAIN": "keyword", "PSEUDONYM_LABEL": "keyword",
    "PSEUDONYM_LABEL_LOWER": "keyword", "PSEUDONYM_BARE": "keyword", "PSEUDONYM_BARE_WORD": "keyword",
    # Fix 1.0.2 : comptes de messagerie, dossier personnel d'un chemin, pseudonyme capitalisé / chat accounts, the
    # user folder of a path, a capitalised pseudonym.
    "HANDLE_PLATFORM_CHAT_WORD": "keyword", "LOGIN_PATH": "keyword", "PSEUDONYM_LABEL_CAPS": "keyword",
}


def _check_forced(texts: Sequence[str], forced: Sequence[frozenset[str]] | None) -> None:
    """Groupes imposés : un ensemble par segment, sur les deux chemins / forced groups: one set per segment."""
    if forced is not None and len(forced) != len(texts):
        raise ValueError("forced : un ensemble par segment / one forced set per segment")


def _native_scope(scope: Scope | None) -> Any:
    """Portée Rust d'une `Scope` exacte (pas d'une sous-classe), sinon None / Rust scope of an exact `Scope`."""
    return scope._native_scope if type(scope) is Scope else None


def _offset_bytes(offsets: Any) -> bytes | None:
    """Table de positions de `normalize` (`array('q')`) pour le noyau / `normalize`'s offset map for the core."""
    return offsets.tobytes() if offsets is not None else None


def _display_all(keys: Sequence[str], language: str, neutral: bool) -> list[str]:
    """`LABELS.display` de plusieurs clés, en un seul appel du moteur fusionné / in one fused-engine call."""
    display = LABELS.display
    return [display(key, language, neutral) for key in keys]


def _offset_array(raw: bytes | None) -> array | None:
    """Table de positions rendue par le noyau, en `array('q')` comme `normalize` / the core's offset map."""
    if raw is None:
        return None
    offsets = array("q")
    offsets.frombytes(raw)
    return offsets


# --- Propagation des valeurs (1.0.2) / value propagation -------------------------------------------------------
# Entités cherchées par squelette alphanumérique (séparateurs retirés) / entities searched by alphanumeric skeleton.
_SKELETON_ENTITIES = frozenset({
    "ID", "NATIONAL_ID", "ID_CARD", "BANK_ACCOUNT", "PLATE", "TAX_ID", "SOCIAL_ID", "HEALTH_ID", "PASSPORT",
    "DRIVER_LICENSE", "RESIDENCE_PERMIT", "STUDENT_ID", "IBAN", "IP", "MAC", "CARD", "IMEI", "CRYPTO", "SECRET",
    "HANDLE"})
_SKELETON_MIN = 6   # lettres et chiffres, au moins un chiffre / letters and digits, at least one digit
_DIGITS_MIN = 9     # chiffres seuls / digits only
_SKELETON_RUN_RE = re.compile(r"[0-9a-z]+")
_AUTOMATON_KEYS = 8  # au-delà, un automate trouve les occurrences / beyond, an automaton finds the occurrences
_CODE_GAP = frozenset(" -./_")
_PHONE_GAP = frozenset(" -./_()")
_PHONE_PREFIXES = ("00330", "0033", "330", "33", "0", "")
_DIGIT_CHARS = frozenset("0123456789")
_MONTH_NAMES: dict[int, tuple[str, ...]] = {
    1: ("janvier", "janv"), 2: ("fevrier", "fevr", "fev"), 3: ("mars",), 4: ("avril", "avr"), 5: ("mai",),
    6: ("juin",), 7: ("juillet", "juil"), 8: ("aout",), 9: ("septembre", "sept"), 10: ("octobre", "oct"),
    11: ("novembre", "nov"), 12: ("decembre", "dec")}
_MONTHS = {name: month for month, names in _MONTH_NAMES.items() for name in names}
_ISO_DATE_RE = re.compile(r"([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})")
_DMY_DATE_RE = re.compile(r"([0-9]{1,2})[/.\- ]([0-9]{1,2})[/.\- ]([0-9]{4})")
_TEXT_DATE_RE = re.compile(r"([0-9]{1,2})(?:er)? ([a-z]+)\.? ([0-9]{4})")
_SAINT_HEADS = frozenset({"saint", "sainte", "st", "ste"})


def _after_saint(text: str, start: int) -> bool:
    """Occurrence collée à « Saint- » (« Saint-Claude ») : un lieu, jamais propagé (1.0.2) / glued to "Saint-"."""
    if start < 3 or text[start - 1] != "-":
        return False
    k = start - 1
    while k > 0 and text[k - 1].isalpha():
        k -= 1
    return text[k:start - 1].lower() in _SAINT_HEADS


def _place(ctx: DetectionContext, ordered: list[Span], starts: list[int], start: int, end: int, source: Span,
           value: str | None) -> bool:
    """Insère une occurrence propagée dans `ordered` (triée, disjointe). Elle remplace les zones de la même entité
    qu'elle contient strictement (« sohan [Kervadec] » -> « [sohan Kervadec] ») ; une date de naissance remplace aussi
    une date ordinaire qu'elle couvre ; tout autre chevauchement l'écarte. Inserts a propagated occurrence; it
    replaces same-entity spans it strictly contains (a birth date also replaces an ordinary date it covers); any
    other overlap drops it.
    """
    if end > ctx.segment(start)[2]:
        return False
    lo = bisect_right(starts, start) - 1
    if lo < 0 or ordered[lo].end <= start:
        lo += 1
    hi = bisect_left(starts, end)
    for inner in ordered[lo:hi]:
        if inner.start < start or inner.end > end:
            return False
        if source.entity == "BIRTH_DATE" and inner.entity == "DATE":
            continue
        if inner.entity != source.entity or not inner.personal or inner.end - inner.start >= end - start:
            return False
    ordered[lo:hi] = [Span(start, end, source.entity, source.label, f"propagated:{source.source}",
                           source.score * 0.95, PRIORITY_PROPAGATED, value, True)]
    starts[lo:hi] = [start]
    return True


def _skeleton_of(text: str) -> str:
    """Squelette : lettres ASCII et chiffres du texte replié / ASCII letters and digits of the folded text."""
    return "".join(_SKELETON_RUN_RE.findall(fold(text)))


def _skeleton_positions(folded: str) -> tuple[str, array]:
    """Squelette du document et position de chacun de ses caractères (tableau compact, 8 octets par position) /
    document skeleton and its positions (compact array, 8 bytes per position)."""
    pieces: list[str] = []
    positions = array("q")
    for m in _SKELETON_RUN_RE.finditer(folded):
        pieces.append(m.group())
        positions.extend(range(m.start(), m.end()))
    return "".join(pieces), positions


def _all_occurrences(keys: list[str], haystack: str) -> list[list[int]]:
    """Débuts de toutes les occurrences (chevauchantes comprises) de chaque clé, croissants : un automate au-delà de
    `_AUTOMATON_KEYS` clés (un export de milliers d'identifiants reste linéaire), sinon une recherche par clé ; même
    résultat. Starts of every occurrence (overlapping included) of each key, increasing: an automaton beyond
    `_AUTOMATON_KEYS` keys (an export of thousands of identifiers stays linear), else one search per key; same result.
    """
    starts: list[list[int]] = [[] for _ in keys]
    if len(keys) > _AUTOMATON_KEYS and _ahocorasick is not None:
        automaton = _ahocorasick.AhoCorasick(keys, matchkind=_ahocorasick.MatchKind.Standard)
        for index, start, _end in automaton.find_matches_as_indexes(haystack, overlapping=True):
            starts[index].append(start)
        for found in starts:
            found.sort()
        return starts
    for index, key in enumerate(keys):
        i = haystack.find(key)
        while i >= 0:
            starts[index].append(i)
            i = haystack.find(key, i + 1)
    return starts


def _skeleton_hits(text: str, folded: str, skeleton: str, positions: Sequence[int], key: str,
                   phone: bool, occurrences: list[int]) -> list[tuple[int, int]]:
    """Occurrences de `key` dans le squelette, en positions du texte. Entre deux caractères : au plus deux
    séparateurs `[ -./_]` (et parenthèses pour un téléphone), jamais de saut de ligne ; bornes alphanumériques ;
    une suite de chiffres ne se prolonge pas au-delà. Occurrences of `key` in the skeleton, as text positions:
    at most two separators between two characters, never a line break; alphanumeric boundaries; a digit run does
    not continue past them. Téléphone : `key` est le numéro national, précédé au plus de 0, 33, 330, 0033, 00330.
    Phone: `key` is the national number, preceded at most by those prefixes.
    """
    gaps = _PHONE_GAP if phone else _CODE_GAP

    def linked(k: int) -> bool:
        p, q = positions[k], positions[k + 1]
        return q - p - 1 <= 2 and all(c in gaps for c in folded[p + 1:q])

    def start_ok(s: int) -> bool:
        p = positions[s]
        if p > 0 and text[p - 1].isalnum():
            return False
        return not (s > 0 and skeleton[s] in _DIGIT_CHARS and skeleton[s - 1] in _DIGIT_CHARS and linked(s - 1))

    def end_ok(j: int) -> bool:
        p = positions[j - 1] + 1
        if p < len(text) and text[p].isalnum():
            return False
        return not (j < len(skeleton) and skeleton[j - 1] in _DIGIT_CHARS and skeleton[j] in _DIGIT_CHARS
                    and linked(j - 1))

    hits: list[tuple[int, int]] = []
    size = len(key)
    free = 0  # après une occurrence retenue, la suivante commence au-delà / after a hit, the next starts past it
    for i in occurrences:
        if i < free:
            continue
        j = i + size
        first: int | None = None
        if all(linked(k) for k in range(i, j - 1)) and end_ok(j):
            if phone:
                for prefix in _PHONE_PREFIXES:
                    s = i - len(prefix)
                    if s >= 0 and skeleton[s:i] == prefix and all(linked(k) for k in range(s, i)) and start_ok(s):
                        first = s
                        break
            elif start_ok(i):
                first = i
        if first is None:
            continue
        begin = positions[first]
        if phone and begin > 0 and text[begin - 1] == "+":
            begin -= 1
        hits.append((begin, positions[j - 1] + 1))
        free = j
    return hits


def _national_number(skeleton: str) -> str | None:
    """Numéro national à 9 chiffres d'un téléphone (préfixes 0033, 33, 0 retirés) / 9-digit national number."""
    if not skeleton or any(c not in _DIGIT_CHARS for c in skeleton):
        return None
    for prefix in ("0033", "33"):
        if skeleton.startswith(prefix) and len(skeleton) - len(prefix) in (9, 10):
            skeleton = skeleton[len(prefix):]
            break
    if len(skeleton) == 10 and skeleton[0] == "0":
        skeleton = skeleton[1:]
    return skeleton if len(skeleton) == 9 and skeleton[0] != "0" else None


def _iso_date(value: str | None) -> str | None:
    """Date ISO d'une date de naissance écrite (« 12/03/1985 », « 12 mars 1985 », « 1985-03-12 ») / ISO date."""
    if value is None:
        return None
    flat = " ".join(fold(value).split())
    m = _ISO_DATE_RE.fullmatch(flat)
    if m is not None:
        year, month, day = m.groups()
    else:
        m = _DMY_DATE_RE.fullmatch(flat)
        if m is not None:
            day, month, year = m.groups()
        else:
            m = _TEXT_DATE_RE.fullmatch(flat)
            if m is None or m.group(2) not in _MONTHS:
                return None
            day, year = m.group(1), m.group(3)
            month = str(_MONTHS[m.group(2)])
    d, mo = int(day), int(month)
    if not (1 <= d <= 31 and 1 <= mo <= 12):
        return None
    return f"{year}-{mo:02d}-{d:02d}"


def _date_forms(iso: str) -> list[str]:
    """Graphies repliées d'une date de naissance ISO / folded written forms of an ISO birth date."""
    year, month, day = iso.split("-")
    d, mo = int(day), int(month)
    days = list(dict.fromkeys((str(d), f"{d:02d}")))
    months = list(dict.fromkeys((str(mo), f"{mo:02d}")))
    forms = [f"{dd}{sep}{mm}{sep}{year}" for sep in "/.-" for dd in days for mm in months]
    forms.append(iso)
    words = days + (["1er"] if d == 1 else [])
    for k, name in enumerate(_MONTH_NAMES[mo]):
        for dd in words:
            forms.append(f"{dd} {name} {year}")
            if k:
                forms.append(f"{dd} {name}. {year}")
    return list(dict.fromkeys(forms))


def _rule_of(span: Span) -> str:
    """Règle à l'origine d'une zone, préfixes retirés / rule behind a span, prefixes removed."""
    source = span.source.split("+", 1)[0]
    for prefix in ("keep:", "propagated:"):
        if source.startswith(prefix):
            source = source[len(prefix):]
    return source


@cache
def _recognizers_by_id(pack_ids: tuple[str, ...]) -> dict[str, PatternRecognizer]:
    return {r.id: r for pack_id in pack_ids for r in load_pack(pack_id).recognizers}


def _aggregate(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Une ligne par (balise, règle, raison), avec le nombre d'occurrences / one line per tag, rule, reason."""
    lines: dict[tuple[Any, ...], dict[str, Any]] = {}
    for entry in entries:
        key = tuple(entry.items())
        line = lines.get(key)
        if line is None:
            lines[key] = {**entry, "count": 1}
        else:
            line["count"] += 1
    return list(lines.values())


# Identifiants officiels qu'une règle « keep » ne démasque jamais une fois leur clé validée.
# Official identifiers that a keep rule never unmasks once their checksum is validated.
_UNMASKABLE = frozenset({"NATIONAL_ID", "TAX_ID", "SOCIAL_ID", "IBAN", "BANK_ACCOUNT", "CARD", "PASSPORT", "ID_CARD",
                         "DRIVER_LICENSE", "MRZ", "SECRET", "CRYPTO"})


_KeepZones = tuple[list[int], list[int], list[str]]


def _keep_zones(spans: list[Span]) -> _KeepZones | None:
    """Zones « keep » des règles de l'organisation : (débuts triés, fin la plus lointaine parmi les zones 0..i, sa
    règle), ou None. Keep zones of the organisation's rules: (sorted starts, furthest end among zones 0..i, its rule).
    """
    keep = sorted((s.start, s.end, s.source) for s in spans if s.entity == KEEP_ENTITY)
    if not keep:
        return None
    starts = [k[0] for k in keep]
    reach: list[int] = []
    owner: list[str] = []
    for _start, end, source in keep:
        if not reach or end > reach[-1]:
            reach.append(end)
            owner.append(source)
        else:
            reach.append(reach[-1])
            owner.append(owner[-1])
    return starts, reach, owner


def _keep_span(zones: _KeepZones, span: Span) -> None:
    """Une détection entièrement comprise dans une zone « keep » reste en clair, sauf un identifiant officiel validé
    par sa clé (NIR, IBAN, carte…), que rien ne démasque. A detection fully inside a keep zone stays in clear, except
    a validated official identifier.
    """
    starts, reach, owner = zones
    # Zones commençant avant la détection : la plus lointaine la contient-elle ? / does the furthest one contain it?
    i = bisect_right(starts, span.start) - 1
    protected = span.priority >= PRIORITY_VALIDATED and span.entity in _UNMASKABLE
    if not protected and i >= 0 and reach[i] >= span.end:
        span.personal = False
        if not span.source.startswith("keep:"):
            span.source = f"keep:{owner[i]}"


def _apply_keep(spans: list[Span], zones: _KeepZones | None) -> list[Span]:
    """Zones « keep » d'une règle : les détections entièrement comprises dans une zone restent en clair (voir
    `_keep_span`). Une détection qui déborde reste masquée (rappel d'abord). Keep zones leave detections fully inside
    them in clear; a detection that sticks out stays masked (recall first).
    """
    if zones is None:
        return spans
    kept = []
    for span in spans:
        if span.entity == KEEP_ENTITY:
            continue
        _keep_span(zones, span)
        kept.append(span)
    return kept


def _keep_after(zones: _KeepZones | None, spans: list[Span]) -> None:
    """Filtre fort 1.0.2 : les zones « keep » l'emportent aussi sur tout ce qui s'ajoute après la résolution
    (propagation des valeurs, signatures, initiales) : une zone gardée n'est jamais masquée. Keep zones also win over
    everything added after resolution (value propagation, signatures, initials): a kept zone is never masked.
    """
    if zones is None:
        return
    for span in spans:
        if span.personal:
            _keep_span(zones, span)


def _trim_honorific(span: Span, text: str) -> None:
    """Laisse « M. », « Mme »… hors de la zone (accords grammaticaux) / keeps honorifics outside the span."""
    while True:
        segment = text[span.start:span.end]
        token_end = 0
        while token_end < len(segment) and (segment[token_end].isalpha()):
            token_end += 1
        if token_end == 0 or fold(segment[:token_end]) not in HONORIFICS:
            return
        if segment[token_end:token_end + 1] in ("'", "’"):
            return  # « M'testa », « M’testo » : un nom, pas « M. » / a name, not an honorific
        rest = token_end
        while rest < len(segment) and segment[rest] in ".  ":
            rest += 1
        if rest >= len(segment):
            return
        span.start += rest


@cache
def default_anonymizer() -> Anonymizer:
    return Anonymizer()


def anonymize(text: str, **settings: Any) -> AnonymizedText:
    """Raccourci / shortcut: `anonymize("Jean Dupont, NIR 1 85 05 78 006 084 91")`."""
    anonymizer = Anonymizer(**settings) if settings else default_anonymizer()
    return anonymizer.anonymize(text)


__all__ = ["PRIORITY_HEURISTIC", "Anonymizer", "DetectionContext", "Settings", "anonymize", "resolve"]
