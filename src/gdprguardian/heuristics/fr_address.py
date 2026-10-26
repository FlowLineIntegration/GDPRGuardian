"""Détection des adresses postales françaises / French postal address detection.

Ancre : code postal suivi d'une commune vérifiée dans la base La Poste et le COG (Corse, DOM, Monaco, CEDEX) ;
extension à gauche vers le numéro, le type et le nom de voie, les boîtes postales (BP, CS, TSA) et les
compléments. Aussi les adresses sans code (« 12 rue de la Paix »).
Anchor: postcode followed by a commune validated against La Poste and COG; extended left to number, street
type and name, PO boxes and complements. Street-only addresses too.
Jumeau Rust aux résultats identiques si le noyau est installé ; ce module reste la référence.
Identical Rust twin when the core is installed; this module stays the reference.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from functools import cache, cached_property
from typing import Any

import ahocorasick_rs

from .. import _native
from .._text import fold
from ..types import PRIORITY_HEURISTIC, Span
from . import _vocab as V
from ._compose import composed_view
from ._lexicon import (
    AMB_ENTITY,
    PLACE_TOKEN_RE,
    SAINT,
    UPPER,
    Lexicon,
    ambiguity,
    department,
    given_rank,
    lexicon,
)
from .fr_names import GIVEN_ALONE_MIN

# Code postal : départements 01-95, Corse 20, DOM-TOM 97-98 (Monaco 98000) / postcode.
_POSTCODE_RE = re.compile(r"[0-9](?<![\w.,/-][0-9])[0-9]{4}(?![0-9]|[.,][0-9])")
_COMMUNE_GAP_RE = re.compile(r"[ \t]{1,2}(?:-[ \t]{1,2})?|[ \t]{0,2},[ \t]{1,2}")
_PLACE_GAP_RE = re.compile(r"[ \t]{1,2}|[ \t]?[-'][ \t]?")
_SUFFIX_RE = re.compile(
    r"(?:[ \t]{1,2}[0-9]{1,2}(?:e|er|ème|eme|è)?(?![\w]))?"
    r"(?:[ \t]{1,2}(?i:c[eé]dex)(?:[ \t]{1,2}[0-9]{1,2})?(?![\w]))?")
_CEDEX_RE = re.compile(r"[ \t]{1,2}(?i:c[eé]dex)(?![\w])")
# Fin d'une commune en plusieurs mots après la partie reconnue : particule puis mot capitalisé (« Gallargues le
# Monteux », « SAINT DENIS LA PLAINE », « Gallargues-le-Monteux »). The rest of a multi-word town after the
# recognised part: a particle, then a capitalised word.
_TOWN_TAIL_RE = re.compile(rf"(?:[ \t-]{{1,2}}(?i:les|le|la|sur|sous|en|lès|lez|aux|au|des|du|de)[ \t-]{{1,2}}"
                           rf"[{UPPER}][^\W\d_'’-]{{1,30}}){{1,2}}(?![\w'’])")
# Code postal seul juste après une voie / bare postcode right after a street.
_POSTCODE_TAIL_RE = re.compile(r"[ \t]{0,2},?[ \t]{1,2}([0-9]{5})(?![\w]|[.,][0-9])")
_CAPITAL_WORDS_RE = re.compile(rf"[{UPPER}][^\W\d_'-]{{1,30}}(?:[ '-][{UPPER}][^\W\d_'-]{{1,30}}){{0,3}}")
_NUMBER_BEFORE_RE = re.compile(
    r"(?<![\w.,])([0-9]{1,4}(?:[ \t]?(?i:bis|ter|quater|quinquies|[a-h])(?![\w]))?(?:[ \t]?[-/][ \t]?[0-9]{1,4})?)"
    r"[ \t]{0,2},?[ \t]{0,2}$")
_NAME_WORD_RE = re.compile(r"[^\W\d_][^\W\d_'’-]{0,30}(?:['’-][^\W\d_]{1,30}){0,4}|[0-9]{1,4}(?:er|e|ème)?(?!\w)")
_NAME_LOWER_PARTICLES = frozenset({"de", "du", "des", "d", "l", "la", "le", "les", "aux", "au", "en", "sur", "sous",
                                   "lès", "lez", "et"})
# Adjectifs devant le type de voie (« Grande Rue », « Petite Route », « Contre Allée ») : ils font partie du nom.
# Adjectives before the street type: part of the street name.
_STREET_ADJECTIVES = frozenset({"grande", "grand", "petite", "petit", "vieux", "vieille", "haute", "haut", "basse",
                                "bas", "contre", "nouvelle", "ancienne", "ancien", "belle"})
_ADJECTIVE_BEFORE_RE = re.compile(r"(?<![\w.,'’-])([^\W\d_]{3,9})[ \t]{1,2}$")
# Lieu-dit devant un code postal vérifié (« 2 la Testière 50700 … », « Adresse : La Testière 16570 … »).
# Named place before a verified postcode.
_PLACE_WORDS_MAX = 6
_PLACE_SEGMENT_MAX = 80
_HOUSE_NUMBER_RE = re.compile(r"[0-9]{1,4}(?i:bis|ter|[a-h])?,?")
_PLACE_WORD_RE = re.compile(r"[^\W\d_](?:[^\W\d_]|['’-])*")
# Premier mot d'une ligne qui n'est pas un lieu-dit (« Cordialement », « Madame ») / not a place name's first word.
_NOT_PLACE_LEADS = V.CLOSINGS | V.GREETINGS | V.HONORIFICS
_NEAR_STREET = 40  # une voie finie à moins de 40 caractères complète le code postal / a street that close
# Ligne d'adresse : segments séparés par une virgule ou un tiret avant un code postal vérifié, chacun mené par un
# numéro ou portant un mot d'adresse (« Rue des prés, 38000 … », « BP 8 Cedex 02, 49000 … »). Mots repliés : types de
# voie d'un mot (sauf « cour » et « mail », trop ambigus), boîtes et compléments. Address line: comma- or dash-
# separated chunks before a verified postcode, each led by a number or holding an address word (folded).
_ADDRESS_WORDS = frozenset({t for t in V.STREET_TYPES if " " not in t} - {"cour", "mail"}) | frozenset({
    "bp", "b.p.", "b.p", "cs", "c.s.", "tsa", "cedex", "bat", "bat.", "batiment", "esc", "esc.", "escalier",
    "appartement", "app", "app.", "appt", "appt.", "etage", "entree", "immeuble", "imm.", "tour", "boite", "hotel",
    "espace", "lieudit", "rd", "rn", "cd"})
# Numéro en tête d'un segment, intervalle permis (« 22-24 ») / number leading a chunk, ranges allowed.
_CHUNK_NUMBER_RE = re.compile(r"[0-9]{1,4}(?:[-/][0-9]{1,4})?(?i:bis|ter|[a-h])?,?")
_LINE_SEPARATORS = ",–—-"
# « 6 rue des Essais, VOUZIERS » : commune après une virgule, puis fin de ligne ou ponctuation.
# Town after a comma, then line end or punctuation.
_TOWN_GAP_RE = re.compile(r"[ \t]{0,2},[ \t]{1,2}")
_TOWN_END_RE = re.compile(r"[ \t]{0,2}(?:[\r\n.,;)]|$)")
_STOP_LOWER = frozenset({"depuis", "pour", "avec", "et", "mais", "où", "qui", "que", "dans", "chez", "ou", "puis",
                         "il", "elle", "je", "nous", "vous", "est", "sont", "a", "ont", "était", "à", "au", "en",
                         "pendant", "car", "donc", "lorsque", "quand", "si", "ne", "pas", "on", "se", "sa", "son"})
_BOX_RE = re.compile(r"(?<![\w])(?:[Bb]\.?[Pp]\.?|[Cc]\.?[Ss]\.?|[Tt]\.?[Ss]\.?[Aa]\.?|(?i:case postale|boîte postale))"
                     r"[ \t]?[0-9]{1,5}(?![\w])")
_LINK_RE = re.compile(r"[ \t]{0,3}[,;–—-]?[ \t]{0,3}(?:\r?\n[ \t]{0,6}(?:[–—-][ \t]{0,3})?)?")
# Compléments d'adresse avant la voie : bâtiment, résidence, et zone, parc ou lotissement (« ZAC des Prés - 2 rue … »).
# Address complements before the street: building, residence, and zone, park or housing estate.
_COMPLEMENT = (r"(?:(?<![\w])(?i:b[aâ]t(?:iment)?\.?|esc(?:alier)?\.?|appartement|appt?\.?|[ée]tage|entr[ée]e|"
               r"r[ée]sidence|r[ée]s\.|immeuble|imm\.|tour|bo[iî]te|zac|za|zi|zone|parc|lotissement|domaine|villa|"
               r"h[oô]tel|quartier|hameau|lieu-?dit|espace)[ \t]{0,2}[\w'’-]{1,20}"
               r"(?:[ \t][\w'’-]{1,20}){0,3}?[ \t]{0,2}[,;–-]?[ \t]{0,3}){1,3}")
_COMPLEMENT_RE = re.compile(_COMPLEMENT + "$")
_COMPLEMENT_HINTS = ("bat", "bât", "esc", "app", "tage", "entr", "sidence", "s.", "imm", "tour", "boite", "boîte",
                     "za", "zi", "zone", "parc", "lotissement", "domaine", "villa", "tel", "quartier", "hameau", "dit",
                     "espace")
_COMPLEMENT_LINE_RE = re.compile(r"[ \t]{0,6}" + _COMPLEMENT)
# Domicile d'une personne (« domicilié rue … », « demeurant … ») / a person's home address cue.
_TRIGGER_RE = re.compile(r"domicili|demeur|resid|habit|adresse|\bsise?\b")
_TRIGGERS = ("domicili", "demeur", "resid", "habit", "adresse", " sis")
# Mot de domicile en début de mot, juste avant un code postal et sa commune seuls, sur la même ligne et dans la même
# phrase (« domiciliée à 69003 Lyon », « Domicile : 59000 Lille ») : lieu de résidence d'une personne, masqué. Pas
# « Adresse : », étiquette des adresses d'organismes (marchés publics). A home word at a word start, right before a
# postcode and town alone, same line and sentence: a person's place of residence, masked. Not "Adresse :", the label
# of organisations' addresses (public procurement).
_HOME_RE = re.compile(r"(?<!\w)(?:domicil|demeur|resid|habit)")
_HOME_HINTS = ("domicil", "demeur", "resid", "habit")
_HOME_WINDOW = 50
_BOX_HINTS = ("bp", "b.p", "cs", "c.s", "tsa", "t.s.a", "postale")  # préfiltre de _BOX_RE / _BOX_RE prefilter
# Raisons propres des adresses sans commune vérifiée (`explain`, REGLES.md § 4) / own reasons of addresses without a
# verified town; the others keep the detector's reason, « postcode_and_town ».
STREET_NUMBERED = "street_and_number"
STREET_CUED = "street_after_home_word"
_MAX_STREET_NAME = 70
_MAX_LINK = 24         # écart maximal entre voie et code postal / max gap between street and postcode
_MAX_COMPLEMENT = 160  # longueur maximale des compléments d'adresse / max length of address complements
# Types de voie, cherchés en un passage sur le texte replié ; compilé une fois / street types, one pass, compiled once.
_TYPES = sorted(V.STREET_TYPES)
_TYPE_AC = ahocorasick_rs.AhoCorasick(_TYPES, matchkind=ahocorasick_rs.MatchKind.LeftmostLongest)


class FrenchAddressDetector:
    """Adresses postales : ancre code postal + commune vérifiée, voie à gauche / postal addresses."""

    id = "FR_ADDRESS"

    def __init__(self, pack: Any = None) -> None:
        self.pack = pack
        self._lex: Lexicon = lexicon()
        self._given = _given_names()

    @cached_property
    def _native(self) -> Any:
        """Jumeau Rust, construit au premier usage natif / Rust twin, built on first native use."""
        return _native_twin()

    @composed_view
    def detect(self, ctx: Any) -> list[Span]:
        has_digit = ctx.has("digit")
        has_trigger = ctx.has(_TRIGGERS)
        if not has_digit and not has_trigger:
            return []
        has_box = has_digit and ctx.has(_BOX_HINTS)
        if ctx.settings.native and self._native is not None:
            spans = [self._span(start, end, score, reason) for start, end, score, reason
                     in self._native.detect(ctx.text, ctx.folded, has_digit, has_trigger, has_box)]
        else:
            spans = self._spans(ctx, has_digit, has_trigger, has_box)
        segmented = ctx.seg_starts is not None
        return [s for s in spans if not segmented or s.end <= ctx.segment(s.start)[2]]

    def _spans(self, ctx: Any, has_digit: bool, has_trigger: bool, has_box: bool) -> list[Span]:
        text: str = ctx.text
        anchors = self._anchors(text, ctx.folded) if has_digit else []
        streets = self._streets(text, ctx.folded)
        has_home = bool(anchors) and ctx.has(_HOME_HINTS)
        boxes = [m.span() for m in _BOX_RE.finditer(text)] if has_box else []
        spans: list[Span] = []
        used: set[int] = set()
        street_parts = sorted(((s, e) for s, e, _ in streets), key=lambda p: p[1])
        street_ends = [e for _, e in street_parts]
        box_ends = [e for _, e in boxes]  # déjà triées par position / already sorted
        for start, end, score in anchors:
            left = start
            box = self._before(boxes, box_ends, left, text)
            if box is not None:
                left = box[0]
            street = self._before(street_parts, street_ends, left, text)
            if street is not None:
                used.add(street[0])
                left = street[0]
                score = max(score, 0.92)
                box = self._before(boxes, box_ends, left, text)  # « BP 24 - 3 rue … » : boîte avant la voie
                if box is not None:
                    left = box[0]
            else:
                place = self._place_before(text, left) if score >= 0.85 else None
                if place is None and score >= 0.85:
                    place = self._address_line(text, ctx.folded, left)  # « Rue des prés, 38000 … »
                if place is not None:
                    left = place  # « 2 la Testière 50700 … » : lieu-dit / named place
                elif score < 0.8 or (box is None and self._complement(text, left) == left
                                     and not self._street_near(street_parts, street_ends, left, text)
                                     and not (has_home and self._home(ctx.folded, left))):
                    # Commune non vérifiée sans voie ; code postal et commune seuls, sans complément, voie proche ni
                    # mot de domicile : conservés (REGLES.md § 2). Unverified town without a street; postcode and
                    # town alone, with no complement, nearby street or home word: kept (REGLES.md § 2).
                    continue
            spans.append(self._span(self._complement(text, left), end, score))
        for start, end, numbered in streets:
            if start in used:
                continue
            if numbered or (has_trigger and self._cued(ctx.folded, start)):
                tail = _POSTCODE_TAIL_RE.match(text, end) if has_digit else None
                if tail is not None and tail.group(1) in self._lex.postal:
                    end = tail.end()  # « 40 avenue de la Grande Armée 75017 » : code postal sans commune
                elif numbered:
                    end = self._town_after(text, ctx.folded, end)  # « 6 rue des Essais, Vouziers »
                # Raison propre (`explain`) : voie numérotée, ou voie après un mot de domicile, sans commune vérifiée.
                # Own reason: numbered street, or street after a home word, without a verified town.
                spans.append(self._span(self._complement(text, start), end, 0.85 if numbered else 0.75,
                                        STREET_NUMBERED if numbered else STREET_CUED))
        return spans

    def _place_before(self, text: str, pos: int) -> int | None:
        """Début d'un lieu-dit juste avant un code postal vérifié, ou None / start of a named place, or None.

        Sur la même ligne : « 2 la Testière 50700 … » (numéro puis un à six mots, toutes casses), ou des mots
        capitalisés après une étiquette (« Adresse : La Testière 16570 … », cellule « | Le Bourg, 20250 … »), après un
        mot de domicile (« à l'adresse Le Bourg, … ») ou en tête de ligne. Code postal en tête de ligne : la ligne
        précédente entière (« Le Bourg⏎29200 Brest »). On the same line: house number then one to six words, or
        capitalised words after a label, a home word or at line start; postcode at line start: the whole previous
        line.
        """
        line_start = text.rfind("\n", max(0, pos - _PLACE_SEGMENT_MAX), pos) + 1
        real = not (line_start == 0 and pos > _PLACE_SEGMENT_MAX)
        if not real:
            # Ligne longue (prose) : fenêtre de 80 caractères, dont le bord n'est pas un début de ligne.
            # Long line (prose): an 80-character window whose edge is not a line start.
            line_start = pos - _PLACE_SEGMENT_MAX
        if not text[line_start:pos].strip(" \t"):
            # Code postal en tête de ligne : la ligne précédente / postcode at line start: the previous line.
            if line_start < 2 or not real:
                return None
            end = line_start - 1
            if text[end - 1] == "\r":
                end -= 1
            start = text.rfind("\n", max(0, end - _PLACE_SEGMENT_MAX), end) + 1
            if start == 0 and end > _PLACE_SEGMENT_MAX:
                return None
            segment = text[start:end].rstrip(" \t")
            segment = segment[:-1].rstrip(" \t") if segment.endswith(",") else segment
            place = self._place_words(text, start, start + len(segment))
            # Ligne qui nomme une personne ou une société (« Claire Dubois », « TESTIVO SAS ») : pas un lieu-dit.
            # A line naming a person or a company is not a named place.
            return None if place is not None and self._named(text, place, start + len(segment)) else place
        segment = text[line_start:pos]
        stripped = segment.rstrip(" \t")
        if not 1 <= len(segment) - len(stripped) <= 2:
            return None
        if stripped.endswith(","):
            stripped = stripped[:-1].rstrip(" \t")
            if len(segment) - len(stripped) > 5:
                return None
        return self._place_words(text, line_start, line_start + len(stripped), real)

    @staticmethod
    def _place_words(text: str, line_start: int, end: int, real: bool = True) -> int | None:
        """Mots d'un lieu-dit qui finissent en `end`, lus de droite à gauche / place words ending at `end`.

        Numéro de maison puis mots de toutes casses ; sinon des mots capitalisés (particules en minuscules
        permises) après une étiquette, une cellule, un mot de domicile ou en tête de ligne, dont le premier n'est
        ni une formule de politesse ni une civilité. House number then words of any case; otherwise capitalised
        words after a label, a cell, a home word or at line start, the first one being neither a greeting, a
        closing nor an honorific. `real` faux : `line_start` est le bord d'une fenêtre, pas un début de ligne /
        false: `line_start` is a window edge, not a line start.
        """
        words, first, first_end, cursor, capitalised = 0, line_start, line_start, end, True
        while cursor > line_start:
            k = cursor
            while k > line_start and text[k - 1] not in " \t":
                k -= 1
            token = text[k:cursor]
            gap = 0
            while k - gap > line_start and text[k - gap - 1] in " \t":
                gap += 1
            at_line_start = k - gap == line_start
            if words and _HOUSE_NUMBER_RE.fullmatch(token):
                # Numéro en tête de ligne, ou après une étiquette ou une virgule / at line start, or after a label.
                return k if (at_line_start and real) or text[k - gap - 1] in ":;,(|" else None
            if words and (token.endswith((":", "|")) or _TRIGGER_RE.search(fold(token)) is not None):
                break  # étiquette, cellule ou mot de domicile / label, cell or home word
            if words == _PLACE_WORDS_MAX or _PLACE_WORD_RE.fullmatch(token) is None:
                return None
            particle = token.lower() in _NAME_LOWER_PARTICLES
            if not words and particle:
                return None  # « Livraison au 97400 … » : un lieu ne finit pas par une particule / no trailing particle
            if not token[0].isupper() and not particle:
                capitalised = False
            words, first, first_end = words + 1, k, cursor
            if at_line_start:
                if not real:
                    return None  # bord de fenêtre sans étiquette ni mot de domicile / window edge, no label
                break  # début de ligne, blancs compris / line start, blanks included
            if gap > 2:
                return None
            cursor = k - gap
        if not (words and capitalised and text[first].isupper()) or fold(text[first:first_end]) in _NOT_PLACE_LEADS:
            return None
        return first

    def _named(self, text: str, start: int, end: int) -> bool:
        """« Claire Dubois », « TESTIVO SAS » : une personne (deux mots ou plus, dont un prénom connu, ni lieu ni fête)
        ou une société (forme juridique), pas un lieu-dit. A person (two words or more, one a known given name that
        is neither a place nor a feast) or a company (legal form), not a named place.
        """
        words = text[start:end].split()
        for word in words:
            if (word.isupper() or "." in word) and fold(word).replace(".", "") in V.COMPANY_FORM_KEYS:
                return True
        return len(words) >= 2 and any(fold(word) in self._given for word in words)

    @staticmethod
    def _home(folded: str, pos: int) -> bool:
        """« domiciliée à 69003 Lyon » : un mot de domicile avant `pos`, même ligne, même phrase / a home word."""
        cues = list(_HOME_RE.finditer(folded, max(0, pos - _HOME_WINDOW), pos))
        if not cues:
            return False
        between = folded[cues[-1].end():pos]
        return "\n" not in between and "." not in between

    def _address_line(self, text: str, folded: str, pos: int) -> int | None:
        """Début des segments d'adresse juste avant un code postal vérifié, ou None / start of the address chunks.

        Sur la même ligne, après le début de ligne, une étiquette (« : ») ou une cellule (« | ») : un séparateur
        (virgule ou tiret) avant le code postal, puis, de droite à gauche, les segments menés par un numéro ou portant
        un mot d'adresse ; le premier segment sans l'un ni l'autre arrête (« Jean Martin, rue des prés, … » : le nom
        reste hors de l'adresse). Si le segment le plus proche n'a rien d'une adresse, `pos` : le code postal et la
        commune, précédés d'autre chose sur leur ligne, ne sont pas seuls et sont masqués. On the same line, after the
        line start, a label or a cell: a separator before the postcode, then, right to left, the chunks led by a
        number or holding an address word; the first other chunk stops the walk. When the nearest chunk has nothing of
        an address, `pos`: a postcode and town preceded by something else on their line are not alone, and are masked.
        """
        line_start = text.rfind("\n", max(0, pos - _PLACE_SEGMENT_MAX), pos) + 1
        if line_start == 0 and pos > _PLACE_SEGMENT_MAX:
            line_start = pos - _PLACE_SEGMENT_MAX  # ligne longue : fenêtre / long line: window
        begin = max(line_start, text.rfind(":", line_start, pos) + 1, text.rfind("|", line_start, pos) + 1)
        cursor = pos
        while cursor > begin and text[cursor - 1] in " \t":
            cursor -= 1
        if cursor == begin or text[cursor - 1] not in _LINE_SEPARATORS:
            return None  # séparateur obligatoire / a separator is required
        found = None
        while True:
            while cursor > begin and (text[cursor - 1] in " \t" or text[cursor - 1] in _LINE_SEPARATORS):
                cursor -= 1
            if cursor == begin:
                return found
            start = cursor
            while start > begin and not (text[start - 1] == "," or (
                    text[start - 1] in "–—-" and start - 2 >= begin and text[start - 2] in " \t")):
                start -= 1
            first = start
            while text[first] in " \t":
                first += 1
            if not self._address_chunk(text, folded, first, cursor):
                # Rien d'adresse dans ce segment : code postal et commune seuls masqués, comme une adresse dont la
                # voie n'est pas reconnue. No address word: the postcode and town alone are masked, as an address
                # whose street is not recognised.
                return found if found is not None else pos
            found, cursor = first, start

    @staticmethod
    def _address_chunk(text: str, folded: str, start: int, end: int) -> bool:
        """Segment mené par un numéro ou portant un mot d'adresse / chunk led by a number or with an address word."""
        k = start
        first = True
        while k < end:
            stop = k
            while stop < end and text[stop] not in " \t":
                stop += 1
            if first and _CHUNK_NUMBER_RE.fullmatch(text, k, stop):
                return True
            word = folded[k:stop]
            if word in _ADDRESS_WORDS or word.rstrip(".") in _ADDRESS_WORDS:
                return True
            first = False
            k = stop
            while k < end and text[k] in " \t":
                k += 1
        return False

    def _town_after(self, text: str, folded: str, end: int) -> int:
        """« 6 rue des Essais, VOUZIERS » : commune connue après une voie numérotée, sans code postal, puis fin de ligne
        ou ponctuation. A known town after a numbered street, without a postcode, then line end or punctuation."""
        gap = _TOWN_GAP_RE.match(text, end)
        if gap is None or not text[gap.end():gap.end() + 1].isupper():
            return end
        tokens: list[tuple[int, int, str]] = []
        cursor = gap.end()
        for m in PLACE_TOKEN_RE.finditer(folded, cursor, min(len(text), cursor + 60)):
            if m.start() != cursor and _PLACE_GAP_RE.fullmatch(text, cursor, m.start()) is None:
                break
            tokens.append((m.start(), m.end(), SAINT.get(m.group(), m.group())))
            cursor = m.end()
            if len(tokens) == 8:
                break
        for k in range(len(tokens), 0, -1):
            town_end = tokens[k - 1][1]
            if " ".join(t[2] for t in tokens[:k]) in self._lex.communes and _TOWN_END_RE.match(text, town_end):
                return town_end
        return end

    # --- ancres code postal + commune / postcode + commune anchors -------------------------------------------

    def _anchors(self, text: str, folded: str) -> list[tuple[int, int, float]]:
        anchors = []
        postal = self._lex.postal
        for m in _POSTCODE_RE.finditer(text):
            code = m.group()
            head = int(code[:2])
            if head == 0 or head == 99:
                continue
            start, end = m.span()
            names = postal.get(code)
            known = self._lex.departments.get(department(code), frozenset()) if names is None else names
            commune_end, score = self._commune(text, folded, end, names, known)
            if commune_end is None and start > 0 and text[start - 1] == "(" and text[end:end + 1] == ")":
                left = self._commune_before(folded, start - 1, known)
                if left is not None:
                    anchors.append((left, end + 1, 0.85))
                continue
            if commune_end is None:
                continue
            tail = _TOWN_TAIL_RE.match(text, commune_end)  # « 30660 Gallargues le Monteux »
            if tail is not None:
                commune_end = tail.end()
            suffix = _SUFFIX_RE.match(text, commune_end)
            anchors.append((start, suffix.end() if suffix else commune_end, score))
        return anchors

    def _commune(self, text: str, folded: str, pos: int, names: frozenset[str] | None,
                 known: frozenset[str]) -> tuple[int | None, float]:
        """Fin de la commune après le code, et confiance / end of the commune after the code, and confidence."""
        gap = _COMMUNE_GAP_RE.match(text, pos)
        if gap is None:
            return None, 0.0
        tokens: list[tuple[int, int, str]] = []
        cursor = gap.end()
        limit = min(len(text), cursor + 60)
        for m in PLACE_TOKEN_RE.finditer(folded, cursor, limit):
            if m.start() != cursor and _PLACE_GAP_RE.fullmatch(text, cursor, m.start()) is None:
                break
            tokens.append((m.start(), m.end(), SAINT.get(m.group(), m.group())))
            cursor = m.end()
            if len(tokens) == 8:
                break
        for k in range(len(tokens), 0, -1):
            if " ".join(t[2] for t in tokens[:k]) in known:
                return tokens[k - 1][1], 0.9 if names is not None else 0.85
        # Commune inconnue : mots capitalisés, retenus seulement avec une voie ou CEDEX / unknown commune.
        words = _CAPITAL_WORDS_RE.match(text, gap.end())
        if words is None:
            return None, 0.0
        cedex = _CEDEX_RE.match(text, words.end())
        return words.end(), 0.85 if cedex is not None else 0.6

    def _commune_before(self, folded: str, paren: int, known: frozenset[str]) -> int | None:
        """« Lyon (69003) » : commune vérifiée avant la parenthèse / verified commune before the bracket."""
        window_start = max(0, paren - 50)
        tokens = list(PLACE_TOKEN_RE.finditer(folded, window_start, paren))
        for k in range(min(4, len(tokens)), 0, -1):
            chosen = tokens[-k:]
            if folded[chosen[-1].end():paren].strip() != "":
                return None
            if " ".join(SAINT.get(t.group(), t.group()) for t in chosen) in known:
                return chosen[0].start()
        return None

    # --- voies / streets ---------------------------------------------------------------------------------------

    def _streets(self, text: str, folded: str) -> list[tuple[int, int, bool]]:
        streets = []
        length = len(folded)
        for index, start, end in _TYPE_AC.find_matches_as_indexes(folded, overlapping=False):
            kind = _TYPES[index]
            if (start > 0 and folded[start - 1].isalnum()) or (end < length and folded[end].isalnum()
                                                                  and kind[-1].isalnum()):
                continue
            # « 22 Grande Rue », « Petite Route de … » : l'adjectif fait partie du nom, qui peut s'arrêter au type.
            # A leading adjective belongs to the name, which may then end at the type.
            adjective = _ADJECTIVE_BEFORE_RE.search(text, max(0, start - 12), start)
            if adjective is not None and fold(adjective.group(1)) not in _STREET_ADJECTIVES:
                adjective = None
            head = adjective.start(1) if adjective is not None else start
            number = _NUMBER_BEFORE_RE.search(text, max(0, head - 24), head)
            if number is None and kind in V.STREET_ABBREVIATIONS:
                continue
            if end < length and text[end] == "." and not kind.endswith("."):
                end += 1
            name_end = self._street_name(text, end, strong=kind in V.STRONG_STREET_TYPES, numbered=bool(number))
            if name_end is None:
                if adjective is None:
                    continue
                name_end = end
            streets.append((number.start(1) if number else head, name_end, number is not None))
        return streets

    @staticmethod
    def _street_name(text: str, pos: int, strong: bool, numbered: bool) -> int | None:
        """Fin du nom de voie : mots capitalisés, ou minuscules après un numéro / end of the street name.

        Les particules ne comptent que suivies d'un mot ; un code postal arrête le nom.
        Particles count only when followed by a word; a postcode stops the name.
        """
        limit = min(len(text), pos + _MAX_STREET_NAME)
        line_end = text.find("\n", pos, limit)
        if line_end >= 0:
            limit = line_end
        end: int | None = None
        mode = ""   # "upper" : nom capitalisé, "lower" : nom en minuscules / capitalised or lowercase name
        count = 0
        cursor = pos
        for m in _NAME_WORD_RE.finditer(text, pos, limit):
            gap = text[cursor:m.start()]
            glued = cursor > pos and not gap and text[cursor - 1] in "'’"
            if gap.strip(" \t") or not (gap or glued):
                break  # mots séparés par des espaces, ou collés après « l' » / spaces, or glued after "l'"
            cursor = m.end()
            word = m.group()
            core = word[2:] if len(word) > 2 and word[1] in "'’" and word[0] in "dlDL" else word
            if word.lower().rstrip("'’") in _NAME_LOWER_PARTICLES:
                continue
            if core[0].isdigit():
                if len(core) >= 5:
                    break
            elif core[0].isupper():
                mode = "upper"  # « rue du général Leclerc » : la suite capitalisée continue le nom / continues
            elif mode == "upper" or not (strong and numbered) or core.lower() in _STOP_LOWER or count >= 4:
                break
            else:
                mode = "lower"
            end = m.end()
            count += 1
        return end

    # --- assemblage / assembly ---------------------------------------------------------------------------------

    @staticmethod
    def _before(parts: list[tuple[int, int]], ends: list[int], pos: int, text: str) -> tuple[int, int] | None:
        """Élément qui se termine juste avant `pos` (même ligne ou ligne précédente) / part ending right before.

        `parts` est trié par fin : recherche dichotomique, aucun parcours quadratique / sorted by end, bisect.
        """
        i = bisect_right(ends, pos) - 1
        while i >= 0 and pos - ends[i] <= _MAX_LINK:
            start, end = parts[i]
            if _LINK_RE.fullmatch(text, end, pos) is not None:
                return start, end
            i -= 1
        return None

    @staticmethod
    def _street_near(parts: list[tuple[int, int]], ends: list[int], pos: int, text: str) -> bool:
        """Une voie finit peu avant `pos`, à une fin de ligne au plus (« 70, 35 allée des Essais⏎– 59000 … »).

        A street ends shortly before `pos`, one line break at most: the postcode completes that address.
        """
        i = bisect_right(ends, pos) - 1
        while i >= 0 and pos - ends[i] <= _NEAR_STREET:
            if text.count("\n", ends[i], pos) <= 1:
                return True
            i -= 1
        return False

    @staticmethod
    def _complement(text: str, start: int) -> int:
        """Étend à gauche sur « Bât. B, Résidence Les Lilas, » (même ligne ou ligne précédente).

        Extends left over address complements (same line, or the whole previous line); bounded windows.
        """
        line_start = text.rfind("\n", max(0, start - _MAX_COMPLEMENT), start) + 1
        if line_start == 0 and start > _MAX_COMPLEMENT:
            line_start = start - _MAX_COMPLEMENT
        before = text[line_start:start]
        if before.strip():
            if not any(hint in before.lower() for hint in _COMPLEMENT_HINTS):
                return start  # préfiltre : aucun mot de complément / prefilter: no complement word
            m = _COMPLEMENT_RE.search(text, line_start, start)
            return m.start() if m is not None and m.end() == start else start
        if line_start >= 2:
            previous = text.rfind("\n", max(0, line_start - 1 - _MAX_COMPLEMENT), line_start - 1) + 1
            line = text[previous:line_start - 1].rstrip("\r")  # fins de ligne Windows / CRLF line endings
            if _COMPLEMENT_LINE_RE.fullmatch(line) is not None:
                return previous + len(line) - len(line.lstrip())
        return start

    @staticmethod
    def _cued(folded: str, start: int) -> bool:
        """« domicilié rue … » : un mot de domicile dans la même phrase, juste avant / home cue right before."""
        cues = list(_TRIGGER_RE.finditer(folded, max(0, start - 45), start))
        if not cues:
            return False
        between = folded[cues[-1].end():start]  # le dernier indice compte / the last cue counts
        return "\n" not in between and "." not in between

    def _span(self, start: int, end: int, score: float, reason: str | None = None) -> Span:
        return Span(start, end, "ADDRESS", "ADDRESS", self.id, score, PRIORITY_HEURISTIC, reason=reason)

    def native_plan(self) -> dict[str, Any] | None:
        """Moteur fusionné : jumeau et préfiltres de ce module / fused engine: twin and this module's prefilters."""
        if self._native is None:
            return None
        return {"kind": "address", "twin": self._native, "prototype": self._span(0, 0, 0.0),
                "triggers": list(_TRIGGERS), "box_hints": list(_BOX_HINTS)}


@cache
def _given_names() -> frozenset[str]:
    """Prénoms connus (au moins 512 naissances), ni lieu ni fête, repliés / known given names, neither places nor
    feasts, folded (built once)."""
    return frozenset(key for key, code in lexicon().names.items()
                     if given_rank(code) >= GIVEN_ALONE_MIN and ambiguity(code) != AMB_ENTITY)


@cache
def _native_twin() -> Any:
    """Jumeau Rust, construit une fois avec les données de ce module / Rust twin, built once from this module's data."""
    core = _native.core()
    if core is None:
        return None
    lex = lexicon()
    return core.AddressDetector(
        _native.unicode_table(), street_types=_TYPES, abbreviations=V.STREET_ABBREVIATIONS,
        strong_types=V.STRONG_STREET_TYPES, communes=lex.communes, postal=lex.postal, departments=lex.departments,
        saint=SAINT, name_particles=_NAME_LOWER_PARTICLES, stop_lower=_STOP_LOWER,
        complement_hints=_COMPLEMENT_HINTS, max_street_name=_MAX_STREET_NAME, max_link=_MAX_LINK,
        max_complement=_MAX_COMPLEMENT, adjectives=_STREET_ADJECTIVES, not_place_leads=_NOT_PLACE_LEADS,
        address_words=_ADDRESS_WORDS, given_names=_given_names(), company_forms=V.COMPANY_FORM_KEYS)


__all__ = ["FrenchAddressDetector"]
