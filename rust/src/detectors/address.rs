//! Adresses postales françaises : transcription exacte de `heuristics/fr_address.py` / French postal addresses.
//!
//! Chaque expression régulière Python est rendue par une fonction qui en reproduit la sémantique (gloutonnerie,
//! retour arrière, `pos`/`endpos`, assertions) ; le commentaire de chaque fonction cite le motif d'origine.
//! Each Python regex becomes a function reproducing its semantics (greediness, backtracking, `pos`/`endpos`,
//! assertions); each function's comment quotes the original pattern.

use std::collections::{HashMap, HashSet};
use std::sync::Arc;

use aho_corasick::{AhoCorasick, MatchKind};

use super::automaton;
use super::chars::{decode, CharCursor, Chars};
use super::unicode::{CharSet, CiPattern, UnicodeTable};
use crate::unicode::TITLE;

/// Fenêtre de recherche du numéro avant le type de voie / house-number window before the street type.
const NUMBER_WINDOW: usize = 24;
/// Fenêtre de la commune après le code postal / commune window after the postcode.
const COMMUNE_WINDOW: usize = 60;
const COMMUNE_TOKENS: usize = 8;
/// « Lyon (69003) » : fenêtre et jetons de la commune avant la parenthèse / commune before the bracket.
const COMMUNE_BEFORE_WINDOW: usize = 50;
const COMMUNE_BEFORE_TOKENS: usize = 4;
/// Fenêtre de l'indice de domicile (« domicilié rue … ») / home-cue window.
const CUE_WINDOW: usize = 45;
/// `_HOME_WINDOW` : mot de domicile avant un code postal et sa commune seuls / home word before a lone postcode.
const HOME_WINDOW: usize = 50;
/// `_HOME_RE` sans son assertion arrière / without its look-behind.
const HOME_WORDS: [&str; 4] = ["domicil", "demeur", "resid", "habit"];
/// Particules de `_TOWN_TAIL_RE`, dans l'ordre de l'alternative / particles, in the alternation's order.
const TOWN_PARTICLES: [&str; 13] =
    ["les", "le", "la", "sur", "sous", "en", "lès", "lez", "aux", "au", "des", "du", "de"];

/// Données de `fr_address.py`, de `_vocab.py` et du lexique postal, fournies par Python.
/// Data from `fr_address.py`, `_vocab.py` and the postal lexicon, provided by Python.
pub struct AddressData {
    pub street_types: Vec<String>,
    pub abbreviations: HashSet<String>,
    pub strong_types: HashSet<String>,
    /// Clés de communes, numérotées une fois / commune keys, numbered once.
    pub communes: HashMap<String, u32>,
    /// Code postal (ou département) -> communes connues (La Poste, COG), identifiants triés.
    /// Postcode (or department) -> known communes, sorted ids.
    pub postal: HashMap<String, Box<[u32]>>,
    pub departments: HashMap<String, Box<[u32]>>,
    pub saint: HashMap<String, String>,
    pub name_particles: HashSet<String>,
    pub stop_lower: HashSet<String>,
    pub complement_hints: Vec<String>,
    pub max_street_name: usize,
    pub max_link: usize,
    pub max_complement: usize,
    /// `_STREET_ADJECTIVES` (« grande », « petite »), repliés / folded.
    pub adjectives: HashSet<String>,
    /// `_NOT_PLACE_LEADS` : formules de politesse et civilités, repliées / closings, greetings, honorifics.
    pub not_place_leads: HashSet<String>,
    /// `_ADDRESS_WORDS` : mots d'adresse d'une ligne d'adresse, repliés / address words of an address line, folded.
    pub address_words: HashSet<String>,
    /// `_given_names` : prénoms connus, ni lieu ni fête, repliés / known given names, neither places nor feasts.
    pub given_names: HashSet<String>,
    /// `_vocab.COMPANY_FORM_KEYS` : formes de société, repliées, sans points / company forms, folded, dotless.
    pub company_forms: HashSet<String>,
}

/// Raisons propres des voies sans commune vérifiée (`STREET_NUMBERED`, `STREET_CUED`) / own reasons of streets.
pub const STREET_NUMBERED: &str = "street_and_number";
pub const STREET_CUED: &str = "street_after_home_word";
/// Zone d'adresse : (début, fin, score, raison propre) / address span: (start, end, score, own reason).
pub type AddressSpan = (usize, usize, f64, Option<&'static str>);

/// `_PLACE_WORDS_MAX`, `_PLACE_SEGMENT_MAX` : mots et longueur d'un lieu-dit / words and length of a named place.
const PLACE_WORDS_MAX: usize = 6;
const PLACE_SEGMENT_MAX: usize = 80;
/// `_NEAR_STREET` : une voie finie aussi près complète le code postal / a street ending that close.
const NEAR_STREET: usize = 40;
/// Fenêtre de la commune après une voie (`_town_after`) / town window after a street.
const TOWN_WINDOW: usize = 60;
/// Fenêtre de l'adjectif avant le type de voie (`_ADJECTIVE_BEFORE_RE`) / adjective window before the type.
const ADJECTIVE_WINDOW: usize = 12;

struct StreetKind {
    abbreviation: bool,
    strong: bool,
    ends_with_dot: bool,
    ends_alnum: bool,
}

struct Anchor {
    start: usize,
    end: usize,
    score: f64,
}

struct Street {
    start: usize,
    end: usize,
    numbered: bool,
}

pub struct AddressDetector {
    table: Arc<UnicodeTable>,
    types: AhoCorasick,
    kinds: Vec<StreetKind>,
    communes: HashMap<String, u32>,
    postal: HashMap<String, Box<[u32]>>,
    departments: HashMap<String, Box<[u32]>>,
    saint: HashMap<String, String>,
    name_particles: HashSet<String>,
    stop_lower: HashSet<String>,
    /// `_COMPLEMENT_HINTS`, cherchés en un passage / searched in one pass.
    complement_hints: AhoCorasick,
    /// Mots de `_COMPLEMENT`, options développées / `_COMPLEMENT` keywords, optional parts expanded.
    complement_words: Vec<CiPattern>,
    /// Longueur maximale d'une ligne de compléments / maximum length of a complement line.
    complement_line_max: usize,
    cedex: CiPattern,
    house_suffixes: Vec<CiPattern>,
    box_words: Vec<CiPattern>,
    /// Premiers caractères possibles d'une boîte postale / possible first characters of a PO box.
    box_first: CharSet,
    max_street_name: usize,
    max_link: usize,
    max_complement: usize,
    adjectives: HashSet<String>,
    not_place_leads: HashSet<String>,
    address_words: HashSet<String>,
    /// Suffixes de `_HOUSE_NUMBER_RE` : `(?i:bis|ter|[a-h])` / house-number suffixes of a named place.
    place_suffixes: Vec<CiPattern>,
    given_names: HashSet<String>,
    company_forms: HashSet<String>,
    /// `(?i:les|le|…)` de `_TOWN_TAIL_RE`.
    town_particles: Vec<CiPattern>,
}

/// `(?i:b[aâ]t(?:iment)?\.?|esc(?:alier)?\.?|appartement|appt?\.?|[ée]tage|entr[ée]e|r[ée]sidence|r[ée]s\.|
/// immeuble|imm\.|tour|bo[iî]te|zac|za|zi|zone|parc|lotissement|domaine|villa|h[oô]tel|quartier|hameau|lieu-?dit|
/// espace)`, chaque option développée / each optional part expanded.
#[rustfmt::skip]
const COMPLEMENT_WORDS: &[&str] = &[
    "b[aâ]t", "b[aâ]t.", "b[aâ]timent", "b[aâ]timent.", "esc", "esc.", "escalier", "escalier.", "appartement", "app",
    "app.", "appt", "appt.", "[ée]tage", "entr[ée]e", "r[ée]sidence", "r[ée]s.", "immeuble", "imm.", "tour", "bo[iî]te",
    "zac", "za", "zi", "zone", "parc", "lotissement", "domaine", "villa", "h[oô]tel", "quartier", "hameau", "lieu-dit",
    "lieudit", "espace",
];
/// Bornes de `_COMPLEMENT` après le mot : `[ \t]{0,2}[\w'’-]{1,20}(?:[ \t][\w'’-]{1,20}){0,3}?[ \t]{0,2}[,;–-]?
/// [ \t]{0,3}`, et `{1,3}` éléments précédés de `[ \t]{0,6}` sur une ligne entière.
/// Bounds of `_COMPLEMENT` after the keyword, `{1,3}` units, `[ \t]{0,6}` before a whole line.
const COMPLEMENT_TAIL_MAX: usize = 2 + 20 + 3 * 21 + 2 + 1 + 3;
const COMPLEMENT_UNITS: usize = 3;
const COMPLEMENT_LINE_INDENT: usize = 6;

impl AddressDetector {
    pub fn new(data: AddressData, table: Arc<UnicodeTable>) -> Result<Self, String> {
        let types = automaton(&data.street_types, MatchKind::LeftmostLongest)?;
        let kinds = data
            .street_types
            .iter()
            .map(|kind| StreetKind {
                abbreviation: data.abbreviations.contains(kind),
                strong: data.strong_types.contains(kind),
                ends_with_dot: kind.ends_with('.'),
                ends_alnum: kind.chars().next_back().is_some_and(|c| table.is_alnum(c)),
            })
            .collect();
        let patterns = |words: &[&str]| -> Vec<CiPattern> { words.iter().map(|w| CiPattern::new(w, &table)).collect() };
        let complement_words = patterns(COMPLEMENT_WORDS);
        let keyword_max = complement_words.iter().map(CiPattern::len).max().unwrap_or(0);
        let box_words = patterns(&["case postale", "boîte postale"]);
        let box_first = CharSet::new(
            ['B', 'C', 'T', 'b', 'c', 't'].into_iter().chain(box_words.iter().flat_map(|w| w.first()).copied()),
        );
        Ok(Self {
            types,
            kinds,
            communes: data.communes,
            postal: data.postal,
            departments: data.departments,
            saint: data.saint,
            name_particles: data.name_particles,
            stop_lower: data.stop_lower,
            complement_hints: automaton(&data.complement_hints, MatchKind::Standard)?,
            complement_line_max: COMPLEMENT_LINE_INDENT + COMPLEMENT_UNITS * (keyword_max + COMPLEMENT_TAIL_MAX),
            complement_words,
            cedex: CiPattern::new("c[eé]dex", &table),
            house_suffixes: patterns(&["bis", "ter", "quater", "quinquies", "[abcdefgh]"]),
            place_suffixes: patterns(&["bis", "ter", "[abcdefgh]"]),
            town_particles: patterns(&TOWN_PARTICLES),
            given_names: data.given_names,
            company_forms: data.company_forms,
            box_words,
            box_first,
            table,
            max_street_name: data.max_street_name,
            max_link: data.max_link,
            max_complement: data.max_complement,
            adjectives: data.adjectives,
            not_place_leads: data.not_place_leads,
            address_words: data.address_words,
        })
    }

    /// `FrenchAddressDetector.detect` : (début, fin, score, raison propre) / (start, end, score, own reason). Les
    /// préfiltres viennent du contexte Python (`ctx.has`) / the prefilters come from the Python context.
    pub fn detect(
        &self,
        text: &str,
        folded: &str,
        has_digit: bool,
        has_trigger: bool,
        has_box_hint: bool,
    ) -> Result<Vec<AddressSpan>, String> {
        if !has_digit && !has_trigger {
            return Ok(Vec::new());
        }
        let (text_chars, folded_chars) = (decode(text), decode(folded));
        if text_chars.len() != folded_chars.len() {
            return Err("texte replié de longueur différente / folded text of another length".into());
        }
        let t = Chars::new(&text_chars, &self.table);
        let f = Chars::new(&folded_chars, &self.table);
        let anchors = if has_digit { self.anchors(t, f) } else { Vec::new() };
        let streets = self.streets(t, f, folded);
        let boxes = if has_box_hint { self.boxes(t) } else { Vec::new() };
        let mut street_parts: Vec<(usize, usize)> = streets.iter().map(|s| (s.start, s.end)).collect();
        street_parts.sort_by_key(|part| part.1); // tri stable, comme `sorted` / stable sort, like `sorted`
        let mut spans = Vec::new();
        let mut used = HashSet::new();
        for anchor in anchors {
            let (mut left, mut score) = (anchor.start, anchor.score);
            let first_box = self.before(t, &boxes, left);
            if let Some(found) = first_box {
                left = found.0;
            }
            if let Some(street) = self.before(t, &street_parts, left) {
                used.insert(street.0);
                left = street.0;
                score = score.max(0.92);
                if let Some(found) = self.before(t, &boxes, left) {
                    left = found.0; // « BP 24 - 3 rue … » : boîte avant la voie / box before the street
                }
            } else if let Some(place) = if score >= 0.85 {
                // « 2 la Testière 50700 … », puis « Rue des prés, 38000 … » / named place, then address line
                self.place_before(t, f, left).or_else(|| self.address_line(t, f, left))
            } else {
                None
            } {
                left = place; // « 2 la Testière 50700 … » : lieu-dit / named place
            } else if score < 0.8
                || (first_box.is_none()
                    && self.complement(t, left) == left
                    && !self.street_near(t, &street_parts, left)
                    && !home(f, left))
            {
                // Commune non vérifiée sans voie ; code postal et commune seuls, sans complément, voie proche ni mot
                // de domicile : conservés. Unverified town without a street; postcode and town alone, with no
                // complement, nearby street or home word: kept.
                continue;
            }
            spans.push((self.complement(t, left), anchor.end, score, None));
        }
        for street in &streets {
            if used.contains(&street.start) || !(street.numbered || (has_trigger && cued(f, street.start))) {
                continue;
            }
            let mut end = street.end;
            let mut tail = false;
            if has_digit {
                if let Some((code, tail_end)) = postcode_tail(t, end) {
                    if self.postal.contains_key(&code) {
                        end = tail_end; // « 40 avenue de la Grande Armée 75017 »
                        tail = true;
                    }
                }
            }
            if !tail {
                end = self.town_after(t, f, end); // « 6 rue des Essais, Vouziers », « Place du Théâtre, Testville »
            }
            let (score, reason) = if street.numbered { (0.85, STREET_NUMBERED) } else { (0.75, STREET_CUED) };
            spans.push((self.complement(t, street.start), end, score, Some(reason)));
        }
        // Boîte postale seule (« CS61336 », « BP 60120, Contact … ») / a lone postal box (`lone_box`).
        for &(start, end) in &boxes {
            if lone_box(t.s, start, end) {
                spans.push((start, end, 0.8, None));
            }
        }
        Ok(spans)
    }

    // --- lieux-dits et communes sans code / named places and towns without a postcode -------------------------

    /// `_place_before` : début d'un lieu-dit juste avant un code postal vérifié / start of a named place.
    fn place_before(&self, t: Chars, f: Chars, pos: usize) -> Option<usize> {
        let mut line_start =
            (pos.saturating_sub(PLACE_SEGMENT_MAX)..pos).rev().find(|&i| t.is(i, '\n')).map_or(0, |i| i + 1);
        let real = !(line_start == 0 && pos > PLACE_SEGMENT_MAX);
        if !real {
            // Ligne longue : fenêtre dont le bord n'est pas un début de ligne / long line: window edge.
            line_start = pos - PLACE_SEGMENT_MAX;
        }
        if (line_start..pos).all(|i| t.blank(i)) {
            // Code postal en tête de ligne : la ligne précédente / postcode at line start: the previous line.
            if line_start < 2 || !real {
                return None;
            }
            let mut end = line_start - 1;
            if t.is(end - 1, '\r') {
                end -= 1;
            }
            let start =
                (end.saturating_sub(PLACE_SEGMENT_MAX)..end).rev().find(|&i| t.is(i, '\n')).map_or(0, |i| i + 1);
            if start == 0 && end > PLACE_SEGMENT_MAX {
                return None;
            }
            let mut stop = end;
            while stop > start && t.blank(stop - 1) {
                stop -= 1;
            }
            if stop > start && t.is(stop - 1, ',') {
                stop -= 1;
                while stop > start && t.blank(stop - 1) {
                    stop -= 1;
                }
            }
            // Ligne qui nomme une personne ou une société (« Claire Dubois », « TESTIVO SAS ») : pas un lieu-dit.
            // A line naming a person or a company is not a named place.
            return self.place_words(t, f, start, stop, true).filter(|&place| !self.named(t, f, place, stop));
        }
        let mut stop = pos;
        while stop > line_start && t.blank(stop - 1) {
            stop -= 1;
        }
        if !(1..=2).contains(&(pos - stop)) {
            return None;
        }
        if stop > line_start && t.is(stop - 1, ',') {
            stop -= 1;
            while stop > line_start && t.blank(stop - 1) {
                stop -= 1;
            }
            if pos - stop > 5 {
                return None;
            }
        }
        self.place_words(t, f, line_start, stop, real)
    }

    /// `_place_words` : mots d'un lieu-dit qui finissent en `end`, lus de droite à gauche / place words.
    /// `real` faux : `line_start` est le bord d'une fenêtre / false: `line_start` is a window edge.
    fn place_words(&self, t: Chars, f: Chars, line_start: usize, end: usize, real: bool) -> Option<usize> {
        let (mut words, mut first, mut first_end, mut cursor, mut capitalised) = (0, line_start, line_start, end, true);
        while cursor > line_start {
            let mut k = cursor;
            while k > line_start && !t.blank(k - 1) {
                k -= 1;
            }
            let mut gap = 0;
            while k - gap > line_start && t.blank(k - gap - 1) {
                gap += 1;
            }
            let at_line_start = k - gap == line_start;
            if words > 0 && self.house_number_token(t, k, cursor) {
                // Numéro en tête de ligne, ou après une étiquette ou une virgule / at line start, or after a label.
                return ((at_line_start && real) || t.test(k - gap - 1, |c| matches!(c, ':' | ';' | ',' | '(' | '|')))
                    .then_some(k);
            }
            let home = || {
                let view = f.upto(cursor);
                (k..cursor).any(|p| trigger_at(view, p).is_some())
            };
            if words > 0 && (t.test(cursor - 1, |c| c == ':' || c == '|') || home()) {
                break; // étiquette, cellule ou mot de domicile / label, cell or home word
            }
            if words == PLACE_WORDS_MAX || !self.place_word(t, k, cursor) {
                return None;
            }
            let particle = self.name_particles.contains(&lowercase(&t.s[k..cursor]));
            if words == 0 && particle {
                return None; // « Livraison au 97400 … » : un lieu ne finit pas par une particule / no trailing particle
            }
            if !t.u.is_upper(t.s[k]) && !particle {
                capitalised = false;
            }
            (words, first, first_end) = (words + 1, k, cursor);
            if at_line_start {
                if !real {
                    return None; // bord de fenêtre sans étiquette ni mot de domicile / window edge, no label
                }
                break; // début de ligne, blancs compris / line start, blanks included
            }
            if gap > 2 {
                return None;
            }
            cursor = k - gap;
        }
        if words == 0
            || !capitalised
            || !t.u.is_upper(t.s[first])
            || self.not_place_leads.contains(&f.string(first, first_end))
        {
            return None;
        }
        Some(first)
    }

    /// `_named` : « Claire Dubois », « TESTIVO SAS » : une personne (deux mots ou plus, dont un prénom connu) ou une
    /// société (forme juridique), pas un lieu-dit. Mots de `str.split()`. A person or a company, not a named place.
    fn named(&self, t: Chars, f: Chars, start: usize, end: usize) -> bool {
        let (mut words, mut given) = (0, false);
        let mut k = start;
        while k < end {
            if t.space(k) {
                k += 1;
                continue;
            }
            let mut stop = k;
            while stop < end && !t.space(stop) {
                stop += 1;
            }
            let word = f.string(k, stop);
            if (is_upper_word(t, k, stop) || (k..stop).any(|i| t.is(i, '.')))
                && self.company_forms.contains(&word.replace('.', ""))
            {
                return true;
            }
            words += 1;
            given |= self.given_names.contains(&word);
            k = stop;
        }
        words >= 2 && given
    }

    /// `_TOWN_TAIL_RE.match` : `(?:[ \t-]{1,2}(?i:les|le|la|sur|sous|en|lès|lez|aux|au|des|du|de)[ \t-]{1,2}
    /// [UPPER][^\W\d_'’-]{1,30}){1,2}(?![\w'’])`, fin de la commune (« Gallargues le Monteux »). Chaque élément n'a
    /// qu'une analyse (blancs entiers, une seule particule suivie d'un blanc, mot entier) : deux éléments si
    /// l'assertion tient après le second, sinon un. Each unit has one parse: two units when the look-ahead holds
    /// after the second, else one.
    fn town_tail(&self, t: Chars, p: usize) -> Option<usize> {
        let gap = |c: char| matches!(c, ' ' | '\t' | '-');
        let unit = |at: usize| -> Option<usize> {
            let lead = t.run(at, 3, gap);
            if !(1..=2).contains(&lead) {
                return None;
            }
            let q = at + lead;
            let particle = self.town_particles.iter().find(|w| t.literal_ci(q, w) && t.test(q + w.len(), gap))?;
            let r = q + particle.len();
            let inner = t.run(r, 3, gap);
            if !(1..=2).contains(&inner) {
                return None;
            }
            let w = r + inner;
            if !t.test(w, |c| t.u.is_capital(c)) {
                return None;
            }
            let letters = t.run(w + 1, 31, |c| t.u.is_letter(c));
            (1..=30).contains(&letters).then_some(w + 1 + letters)
        };
        let free = |end: usize| !t.test(end, |c| t.u.is_word(c) || c == '\'' || c == '’');
        let first = unit(p)?;
        match unit(first) {
            Some(second) if free(second) => Some(second),
            _ => free(first).then_some(first),
        }
    }

    /// `_address_line` : début des segments d'adresse (« Rue des prés, 38000 … ») juste avant un code postal
    /// vérifié, sur la même ligne, après le début de ligne, une étiquette ou une cellule / start of the address
    /// chunks right before a verified postcode.
    fn address_line(&self, t: Chars, f: Chars, pos: usize) -> Option<usize> {
        let mut line_start =
            (pos.saturating_sub(PLACE_SEGMENT_MAX)..pos).rev().find(|&i| t.is(i, '\n')).map_or(0, |i| i + 1);
        if line_start == 0 && pos > PLACE_SEGMENT_MAX {
            line_start = pos - PLACE_SEGMENT_MAX; // ligne longue : fenêtre / long line: window
        }
        let after = |c: char| (line_start..pos).rev().find(|&i| t.is(i, c)).map_or(0, |i| i + 1);
        let begin = line_start.max(after(':')).max(after('|'));
        let separator = |i: usize| t.test(i, |c| matches!(c, ',' | '–' | '—' | '-'));
        let mut cursor = pos;
        while cursor > begin && t.blank(cursor - 1) {
            cursor -= 1;
        }
        if cursor == begin || !separator(cursor - 1) {
            return None; // séparateur obligatoire / a separator is required
        }
        let mut found = None;
        loop {
            while cursor > begin && (t.blank(cursor - 1) || separator(cursor - 1)) {
                cursor -= 1;
            }
            if cursor == begin {
                return found;
            }
            let mut start = cursor;
            while start > begin
                && !(t.is(start - 1, ',')
                    || (t.test(start - 1, |c| matches!(c, '–' | '—' | '-'))
                        && start >= begin + 2
                        && t.blank(start - 2)))
            {
                start -= 1;
            }
            let mut first = start;
            while t.blank(first) {
                first += 1;
            }
            if !self.address_chunk(t, f, first, cursor) {
                // Rien d'adresse : code postal et commune seuls masqués / no address word: postcode and town alone.
                return found.or(Some(pos));
            }
            (found, cursor) = (Some(first), start);
        }
    }

    /// `_address_chunk` : segment mené par un numéro ou portant un mot d'adresse / chunk led by a number or with an
    /// address word.
    fn address_chunk(&self, t: Chars, f: Chars, start: usize, end: usize) -> bool {
        let (mut k, mut first) = (start, true);
        while k < end {
            let mut stop = k;
            while stop < end && !t.blank(stop) {
                stop += 1;
            }
            if first && self.chunk_number_token(t, k, stop) {
                return true;
            }
            let word = f.string(k, stop);
            if self.address_words.contains(&word) || self.address_words.contains(word.trim_end_matches('.')) {
                return true;
            }
            first = false;
            k = stop;
            while k < end && t.blank(k) {
                k += 1;
            }
        }
        false
    }

    /// `_CHUNK_NUMBER_RE.fullmatch` : `[0-9]{1,4}(?:[-/][0-9]{1,4})?(?i:bis|ter|[a-h])?,?` sur `t[a..b]`.
    fn chunk_number_token(&self, t: Chars, a: usize, b: usize) -> bool {
        let view = t.upto(b);
        let digits = view.digits(a, 5);
        if digits == 0 || digits > 4 {
            return false;
        }
        let ends = |x: usize| x == b || (x + 1 == b && t.is(x, ','));
        let suffixed =
            |x: usize| ends(x) || self.place_suffixes.iter().any(|w| view.literal_ci(x, w) && ends(x + w.len()));
        let rest = a + digits;
        if suffixed(rest) {
            return true;
        }
        if !t.test(rest, |c| c == '-' || c == '/') {
            return false;
        }
        let more = view.digits(rest + 1, 5);
        (1..=4).contains(&more) && suffixed(rest + 1 + more)
    }

    /// `_PLACE_WORD_RE.fullmatch` : `[^\W\d_][^\W\d_'’-]*` sur `t[a..b]`.
    fn place_word(&self, t: Chars, a: usize, b: usize) -> bool {
        b > a && t.letter(a) && (a + 1..b).all(|i| t.letter(i) || t.test(i, |c| matches!(c, '\'' | '’' | '-')))
    }

    /// `_HOUSE_NUMBER_RE.fullmatch` : `[0-9]{1,4}(?i:bis|ter|[a-h])?,?` sur `t[a..b]`.
    fn house_number_token(&self, t: Chars, a: usize, b: usize) -> bool {
        let digits = t.upto(b).digits(a, 5);
        if digits == 0 || digits > 4 {
            return false;
        }
        let rest = a + digits;
        let ends = |x: usize| x == b || (x + 1 == b && t.is(x, ','));
        ends(rest) || self.place_suffixes.iter().any(|w| t.upto(b).literal_ci(rest, w) && ends(rest + w.len()))
    }

    /// `_street_near` : une voie finit peu avant `pos`, à une fin de ligne au plus / a street ends shortly before.
    fn street_near(&self, t: Chars, parts: &[(usize, usize)], pos: usize) -> bool {
        let count = parts.partition_point(|part| part.1 <= pos);
        parts[..count]
            .iter()
            .rev()
            .take_while(|part| pos - part.1 <= NEAR_STREET)
            .any(|part| (part.1..pos).filter(|&i| t.is(i, '\n')).count() <= 1)
    }

    /// `_town_after` : commune connue après une voie numérotée, sans code postal, puis fin de ligne ou ponctuation.
    /// A known town after a numbered street, without a postcode, then line end or punctuation.
    fn town_after(&self, t: Chars, f: Chars, end: usize) -> usize {
        let Some(gap_end) = town_gap(t, end) else {
            return end;
        };
        if !t.test(gap_end, |c| t.u.is_upper(c)) {
            return end;
        }
        let window = f.upto(gap_end + TOWN_WINDOW);
        let mut tokens: Vec<(usize, usize)> = Vec::new();
        let mut cursor = gap_end;
        while let Some((start, stop)) = place_token(window, cursor) {
            if start != cursor && !place_gap(t, cursor, start) {
                break;
            }
            tokens.push((start, stop));
            cursor = stop;
            if tokens.len() == COMMUNE_TOKENS {
                break;
            }
        }
        let (key, bounds) = self.joined_keys(f, &tokens);
        for k in (1..=tokens.len()).rev() {
            let town_end = tokens[k - 1].1;
            if self.communes.contains_key(&key[..bounds[k - 1].1]) && town_end_at(t, town_end) {
                return town_end;
            }
        }
        end
    }

    // --- ancres code postal + commune / postcode + commune anchors ---------------------------------------

    /// `_POSTCODE_RE.finditer` puis la commune / then the commune. Le motif ne peut réussir qu'au début d'une suite
    /// d'exactement cinq chiffres : on saute de suite en suite. The pattern can only match at the start of a run of
    /// exactly five digits: the scan jumps from run to run.
    fn anchors(&self, t: Chars, f: Chars) -> Vec<Anchor> {
        let mut anchors = Vec::new();
        let mut s = 0;
        while let Some(offset) = t.s.get(s..).and_then(|rest| rest.iter().position(char::is_ascii_digit)) {
            let start = s + offset;
            let end = start + t.digits(start, usize::MAX);
            s = end;
            if end - start != 5 || !postcode_at(t, start) {
                continue;
            }
            let code = t.string(start, end);
            let head = (code.as_bytes()[0] - b'0') * 10 + (code.as_bytes()[1] - b'0');
            if head == 0 || head == 99 {
                continue;
            }
            let names = self.postal.get(&code);
            let known: &[u32] = match names {
                Some(ids) => ids,
                None => self.departments.get(department(&code)).map_or(&[][..], |ids| &ids[..]),
            };
            match self.commune(t, f, end, names.is_some(), known) {
                Some((commune_end, score)) => {
                    // « 30660 Gallargues le Monteux » : fin de la commune / rest of a multi-word town.
                    let commune_end = self.town_tail(t, commune_end).unwrap_or(commune_end);
                    anchors.push(Anchor { start, end: suffix(self, t, commune_end), score });
                }
                None if start > 0 && t.is(start - 1, '(') && t.is(end, ')') => {
                    if let Some(left) = self.commune_before(f, start - 1, known) {
                        anchors.push(Anchor { start: left, end: end + 1, score: 0.85 });
                    }
                }
                None => {}
            }
        }
        anchors
    }

    /// `_commune` : fin de la commune après le code, et confiance / end of the commune, and confidence.
    fn commune(&self, t: Chars, f: Chars, pos: usize, verified: bool, known: &[u32]) -> Option<(usize, f64)> {
        let gap_end = commune_gap(t, pos)?;
        let window = f.upto(gap_end + COMMUNE_WINDOW);
        let mut tokens: Vec<(usize, usize)> = Vec::new();
        let mut cursor = gap_end;
        while let Some((start, end)) = place_token(window, cursor) {
            if start != cursor && !place_gap(t, cursor, start) {
                break;
            }
            tokens.push((start, end));
            cursor = end;
            if tokens.len() == COMMUNE_TOKENS {
                break;
            }
        }
        // Clés des k premiers jetons, de la plus longue à la plus courte / keys of the first k tokens, longest first.
        let (key, bounds) = self.joined_keys(f, &tokens);
        for k in (1..=tokens.len()).rev() {
            if self.is_known(&key[..bounds[k - 1].1], known) {
                return Some((tokens[k - 1].1, if verified { 0.9 } else { 0.85 }));
            }
        }
        // Commune inconnue : mots capitalisés, retenus seulement avec une voie ou CEDEX / unknown commune.
        let words_end = capital_words(t, gap_end)?;
        let cedex = {
            let at = words_end + t.blanks(words_end, 2);
            at > words_end && t.literal_ci(at, &self.cedex) && !t.word(at + self.cedex.len())
        };
        Some((words_end, if cedex { 0.85 } else { 0.6 }))
    }

    /// `_commune_before` : « Lyon (69003) », commune vérifiée avant la parenthèse / commune before the bracket.
    fn commune_before(&self, f: Chars, paren: usize, known: &[u32]) -> Option<usize> {
        let window = f.upto(paren);
        let mut tokens = Vec::new();
        let mut cursor = paren.saturating_sub(COMMUNE_BEFORE_WINDOW);
        while let Some(token) = place_token(window, cursor) {
            tokens.push(token);
            cursor = token.1;
        }
        let last_end = tokens.last()?.1;
        if (last_end..paren).any(|i| !f.space(i)) {
            return None;
        }
        // Clés des k derniers jetons, de la plus longue à la plus courte / keys of the last k tokens, longest first.
        let chosen = &tokens[tokens.len() - tokens.len().min(COMMUNE_BEFORE_TOKENS)..];
        let (key, bounds) = self.joined_keys(f, chosen);
        (0..chosen.len()).find(|&i| self.is_known(&key[bounds[i].0..], known)).map(|i| chosen[i].0)
    }

    /// `" ".join(SAINT.get(t, t) for t in tokens)` et les bornes de chaque jeton dans la clé : préfixes et suffixes
    /// de la clé sont les clés des sous-suites. The joined key and each token's bounds in it: the key's prefixes and
    /// suffixes are the keys of the sub-sequences.
    fn joined_keys(&self, f: Chars, tokens: &[(usize, usize)]) -> (String, Vec<(usize, usize)>) {
        let mut key = String::new();
        let mut bounds = Vec::with_capacity(tokens.len());
        for (i, &(start, end)) in tokens.iter().enumerate() {
            if i > 0 {
                key.push(' ');
            }
            let token = f.string(start, end);
            let first = key.len();
            key.push_str(self.saint.get(&token).unwrap_or(&token));
            bounds.push((first, key.len()));
        }
        (key, bounds)
    }

    /// `key in known` : commune connue pour ce code ou ce département / commune known for this code or department.
    fn is_known(&self, key: &str, known: &[u32]) -> bool {
        self.communes.get(key).is_some_and(|id| known.binary_search(id).is_ok())
    }

    // --- voies / streets ------------------------------------------------------------------------------------

    /// `_streets` : types de voie (Aho-Corasick, le plus long à gauche) sur le texte replié / street types.
    fn streets(&self, t: Chars, f: Chars, folded: &str) -> Vec<Street> {
        let mut streets = Vec::new();
        let mut cursor = CharCursor::new(folded);
        for m in self.types.find_iter(folded) {
            let kind = &self.kinds[m.pattern().as_usize()];
            let start = cursor.char_index(m.start());
            let mut end = cursor.char_index(m.end());
            if (start > 0 && f.alnum(start - 1)) || (f.alnum(end) && kind.ends_alnum) {
                continue;
            }
            // « 22 Grande Rue » : l'adjectif fait partie du nom, qui peut s'arrêter au type / the adjective belongs
            // to the name, which may then end at the type.
            let adjective = adjective_before(t, start).filter(|&(a, b)| self.adjectives.contains(&f.string(a, b)));
            let head = adjective.map_or(start, |(a, _)| a);
            let number = number_before(t.upto(head), head.saturating_sub(NUMBER_WINDOW), &self.house_suffixes);
            if number.is_none() && kind.abbreviation {
                continue;
            }
            if t.is(end, '.') && !kind.ends_with_dot {
                end += 1;
            }
            let name_end = match self.street_name(t, end, kind.strong, number.is_some()) {
                Some(name_end) => name_end,
                None if adjective.is_some() => end,
                None => continue,
            };
            streets.push(Street { start: number.unwrap_or(head), end: name_end, numbered: number.is_some() });
        }
        streets
    }

    /// `_street_name` : fin du nom de voie / end of the street name.
    fn street_name(&self, t: Chars, pos: usize, strong: bool, numbered: bool) -> Option<usize> {
        let mut limit = (pos + self.max_street_name).min(t.len());
        if let Some(line_end) = (pos..limit).find(|&i| t.is(i, '\n')) {
            limit = line_end;
        }
        let view = t.upto(limit);
        let mut end = None;
        let mut mode = Case::Any;
        let mut count = 0;
        let mut cursor = pos;
        let mut search = pos;
        while let Some((start, stop)) = name_word(view, search) {
            search = stop;
            let glued = cursor > pos && start == cursor && view.test(cursor - 1, |c| c == '\'' || c == '’');
            if !(cursor..start).all(|i| view.blank(i)) || (start == cursor && !glued) {
                break; // mots séparés par des espaces / words separated by spaces
            }
            cursor = stop;
            let word = &view.s[start..stop];
            let core = elided(word);
            if self.name_particles.contains(lowercase(word).trim_end_matches(['\'', '’'])) {
                continue;
            }
            let first = core[0];
            if self.table.is_digit(first) {
                if core.len() >= 5 {
                    break;
                }
            } else if self.table.is_upper(first) {
                mode = Case::Upper; // « rue du général Leclerc » : la suite capitalisée continue le nom / continues
            } else if mode == Case::Upper
                || !(strong && numbered)
                || self.stop_lower.contains(&lowercase(core))
                || count >= 4
            {
                break;
            } else {
                mode = Case::Lower;
            }
            end = Some(stop);
            count += 1;
        }
        end
    }

    // --- assemblage / assembly --------------------------------------------------------------------------------

    /// `_before` : élément fini juste avant `pos` (triés par fin) / part ending right before `pos` (sorted by end).
    fn before(&self, t: Chars, parts: &[(usize, usize)], pos: usize) -> Option<(usize, usize)> {
        let count = parts.partition_point(|part| part.1 <= pos);
        parts[..count]
            .iter()
            .rev()
            .take_while(|part| pos - part.1 <= self.max_link)
            .find(|part| link(t, part.1, pos))
            .copied()
    }

    /// `_complement` : extension à gauche sur « Bât. B, Résidence Les Lilas, » / left extension over complements.
    fn complement(&self, t: Chars, start: usize) -> usize {
        let window = self.max_complement;
        let mut line_start = (start.saturating_sub(window)..start).rev().find(|&i| t.is(i, '\n')).map_or(0, |i| i + 1);
        if line_start == 0 && start > window {
            line_start = start - window;
        }
        if (line_start..start).any(|i| !t.space(i)) {
            if !self.complement_hints.is_match(&t.string(line_start, start).to_lowercase()) {
                return start; // préfiltre : aucun mot de complément / prefilter: no complement word
            }
            // `_COMPLEMENT_RE.search(text, line_start, start)` : le premier début qui finit en `start` (`$`).
            // The leftmost start whose match ends at `start` (`$`).
            let starts = self.complement_starts(t.upto(start), line_start);
            return starts[..starts.len() - 1].iter().position(|&ok| ok).map_or(start, |i| line_start + i);
        }
        if line_start >= 2 {
            let previous = ((line_start - 1).saturating_sub(window)..line_start - 1)
                .rev()
                .find(|&i| t.is(i, '\n'))
                .map_or(0, |i| i + 1);
            let mut line_end = line_start - 1;
            while line_end > previous && t.is(line_end - 1, '\r') {
                line_end -= 1; // fins de ligne Windows / CRLF line endings
            }
            if self.complement_line(t.upto(line_end), previous) {
                return previous + t.run(previous, line_end - previous, |c| self.table.is_space(c));
            }
        }
        start
    }

    /// `_COMPLEMENT_LINE_RE.fullmatch(line)` : `[ \t]{0,6}` puis 1 à 3 éléments / then 1 to 3 units.
    fn complement_line(&self, line: Chars, start: usize) -> bool {
        if line.len() - start > self.complement_line_max {
            return false; // plus long que tout complément possible / longer than any possible complement
        }
        let starts = self.complement_starts(line, start);
        (0..=line.len().min(start + COMPLEMENT_LINE_INDENT) - start)
            .take_while(|&j| j == 0 || line.blank(start + j - 1))
            .any(|j| starts[j])
    }

    /// Débuts `x` de `[lo, fin]` tels que `_COMPLEMENT{1,3}` couvre exactement `t[x..fin]` (fin de la vue).
    /// Calcul à rebours sur des ensembles de positions : linéaire, sans retour arrière exponentiel.
    /// Starts `x` such that `_COMPLEMENT{1,3}` covers exactly `t[x..end]`; computed backwards over position
    /// sets: linear, with no exponential backtracking.
    fn complement_starts(&self, t: Chars, lo: usize) -> Vec<bool> {
        let size = t.len() - lo + 1;
        let mut target = vec![false; size];
        target[size - 1] = true;
        let mut starts = vec![false; size];
        for _ in 0..COMPLEMENT_UNITS {
            target = self.complement_unit_starts(t, lo, &target);
            starts.iter_mut().zip(&target).for_each(|(s, &x)| *s |= x);
            if !target.contains(&true) {
                break;
            }
        }
        starts
    }

    /// Un élément de `_COMPLEMENT`, à rebours depuis l'ensemble de ses fins / one unit, backwards from its ends.
    fn complement_unit_starts(&self, t: Chars, lo: usize, ends: &[bool]) -> Vec<bool> {
        let set = before_blanks(t, lo, ends, 3);
        let set = before_optional(t, lo, &set, |c| matches!(c, ',' | ';' | '–' | '-'));
        let tail = before_blanks(t, lo, &set, 2);
        // `(?:[ \t][\w'’-]{1,20}){0,3}?`
        let mut repeated = tail.clone();
        let mut layer = tail.clone();
        for _ in 0..3 {
            let tokens = before_tokens(t, lo, &layer);
            layer = (0..tokens.len()).map(|i| t.blank(lo + i) && tokens.get(i + 1) == Some(&true)).collect();
            repeated.iter_mut().zip(&layer).for_each(|(r, &x)| *r |= x);
        }
        let set = before_tokens(t, lo, &repeated);
        let set = before_blanks(t, lo, &set, 2);
        // `(?<![\w])` : le mot de complément commence un mot (« Contour » ne contient pas « tour »).
        // The complement keyword starts a word ("Contour" does not contain "tour").
        (0..set.len())
            .map(|i| {
                (lo + i == 0 || !t.word(lo + i - 1))
                    && (self
                        .complement_words
                        .iter()
                        .any(|w| t.literal_ci(lo + i, w) && set.get(i + w.len()) == Some(&true))
                        || floor_rank(t, lo, i, &tail))
            })
            .collect()
    }

    // --- boîtes postales / PO boxes -------------------------------------------------------------------------

    /// `_BOX_RE.finditer` : `(?<![\w])(?:[Bb]\.?[Pp]\.?|[Cc]\.?[Ss]\.?|[Tt]\.?[Ss]\.?[Aa]\.?|(?i:case postale|
    /// boîte postale))[ \t]?[0-9]{1,5}(?![\w])`.
    fn boxes(&self, t: Chars) -> Vec<(usize, usize)> {
        let mut boxes = Vec::new();
        let mut p = 0;
        // Seules les positions d'un premier caractère possible sont essayées / only possible first characters.
        while let Some(at) = t.s.get(p..).and_then(|rest| rest.iter().position(|&c| self.box_first.contains(c))) {
            let at = p + at;
            match self.box_at(t, at) {
                Some(end) => {
                    boxes.push((at, end));
                    p = end;
                }
                None => p = at + 1,
            }
        }
        boxes
    }

    fn box_at(&self, t: Chars, p: usize) -> Option<usize> {
        if p > 0 && t.word(p - 1) {
            return None;
        }
        for letters in [&['B', 'P'][..], &['C', 'S'], &['T', 'S', 'A']] {
            if let Some(end) = dotted_ends(t, p, letters).into_iter().find_map(|q| box_number(t, q)) {
                return Some(end);
            }
        }
        self.box_words.iter().find_map(|w| if t.literal_ci(p, w) { box_number(t, p + w.len()) } else { None })
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Case {
    Any,
    Upper,
    Lower,
}

/// `str.lower()` (correspondances complètes) / full case mapping.
fn lowercase(chars: &[char]) -> String {
    chars.iter().collect::<String>().to_lowercase()
}

/// Mot sans son élision (« d'Arc » -> « Arc ») / word without its elision.
fn elided(word: &[char]) -> &[char] {
    match word {
        ['d' | 'l' | 'D' | 'L', '\'' | '’', rest @ ..] if !rest.is_empty() => rest,
        _ => word,
    }
}

/// `department` : 97x et 98x sur trois chiffres / three digits for 97x and 98x.
fn department(code: &str) -> &str {
    if code.starts_with("97") || code.starts_with("98") {
        &code[..3]
    } else {
        &code[..2]
    }
}

/// `[0-9](?<![\w.,/-][0-9])[0-9]{4}(?![0-9]|[.,][0-9])` en `s`.
fn postcode_at(t: Chars, s: usize) -> bool {
    (s..s + 5).all(|i| t.digit(i))
        && !(s > 0 && t.test(s - 1, |c| t.u.is_word(c) || matches!(c, '.' | ',' | '/' | '-')))
        && !(t.digit(s + 5) || (t.test(s + 5, |c| c == '.' || c == ',') && t.digit(s + 6)))
}

/// `_COMMUNE_GAP_RE.match` : `[ \t]{1,2}(?:-[ \t]{1,2})?|[ \t]{0,2},[ \t]{1,2}`.
fn commune_gap(t: Chars, pos: usize) -> Option<usize> {
    let lead = t.blanks(pos, 2);
    if lead > 0 {
        let dash = pos + lead;
        let tail = if t.is(dash, '-') { t.blanks(dash + 1, 2) } else { 0 };
        return Some(if tail > 0 { dash + 1 + tail } else { dash });
    }
    let tail = if t.is(pos, ',') { t.blanks(pos + 1, 2) } else { 0 };
    (tail > 0).then_some(pos + 1 + tail)
}

/// `PLACE_TOKEN_RE` (`[a-z0-9]+`) : prochain jeton à partir de `from` dans la vue / next token from `from`.
fn place_token(f: Chars, from: usize) -> Option<(usize, usize)> {
    let place = |c: char| c.is_ascii_lowercase() || c.is_ascii_digit();
    let start = from + f.s.get(from..)?.iter().position(|&c| place(c))?;
    Some((start, start + f.run(start, usize::MAX, place)))
}

/// `_PLACE_GAP_RE.fullmatch` : `[ \t]{1,2}|[ \t]?[-'][ \t]?` sur `t[a..b]`.
fn place_gap(t: Chars, a: usize, b: usize) -> bool {
    let mark = |i: usize| t.test(i, |c| c == '-' || c == '\'');
    match b - a {
        1 => t.blank(a) || mark(a),
        2 => (t.blank(a) && t.blank(a + 1)) || (t.blank(a) && mark(a + 1)) || (mark(a) && t.blank(a + 1)),
        3 => t.blank(a) && mark(a + 1) && t.blank(a + 2),
        _ => false,
    }
}

/// `_CAPITAL_WORDS_RE.match` : `[UPPER][^\W\d_'-]{1,30}(?:[ '-][UPPER][^\W\d_'-]{1,30}){0,3}`.
fn capital_words(t: Chars, p: usize) -> Option<usize> {
    let word = |at: usize| -> Option<usize> {
        if !t.test(at, |c| t.u.is_capital(c)) {
            return None;
        }
        let tail = t.run(at + 1, 30, |c| t.u.is_letter(c));
        (tail > 0).then_some(at + 1 + tail)
    };
    let mut end = word(p)?;
    for _ in 0..3 {
        match word(end + 1) {
            Some(next) if t.test(end, |c| matches!(c, ' ' | '\'' | '-')) => end = next,
            _ => break,
        }
    }
    Some(end)
}

/// `_SUFFIX_RE.match` : arrondissement puis CEDEX, chacun facultatif / district then CEDEX, both optional.
fn suffix(detector: &AddressDetector, t: Chars, p: usize) -> usize {
    let district = district(t, p).unwrap_or(p);
    cedex_suffix(t, district, &detector.cedex).unwrap_or(district)
}

/// `[ \t]{1,2}[0-9]{1,2}(?:e|er|ème|eme|è)?(?![\w])`.
fn district(t: Chars, p: usize) -> Option<usize> {
    let i = p + t.blanks(p, 2);
    if i == p {
        return None;
    }
    for count in (1..=t.digits(i, 2)).rev() {
        let j = i + count;
        for ordinal in ["e", "er", "ème", "eme", "è", ""] {
            let k = j + ordinal.chars().count();
            if t.literal(j, ordinal) && !t.word(k) {
                return Some(k);
            }
        }
    }
    None
}

/// `[ \t]{1,2}(?i:cedex)(?:[ \t]{1,2}[0-9]{1,2})?(?![\w])`.
fn cedex_suffix(t: Chars, q: usize, cedex: &CiPattern) -> Option<usize> {
    let i = q + t.blanks(q, 2);
    if i == q || !t.literal_ci(i, cedex) {
        return None;
    }
    let j = i + cedex.len();
    for gap in (1..=t.blanks(j, 2)).rev() {
        for count in (1..=t.digits(j + gap, 2)).rev() {
            let k = j + gap + count;
            if !t.word(k) {
                return Some(k);
            }
        }
    }
    (!t.word(j)).then_some(j)
}

/// `_NUMBER_BEFORE_RE.search(text, lo, hi)` (vue tronquée en `hi`) : début du groupe 1, c'est-à-dire du premier
/// numéro qui mène à la fin. Seule l'existence d'un chemin compte : on calcule les positions atteignables.
/// Start of group 1 of the leftmost match (view truncated at `hi`). Only the existence of a path matters, so the
/// reachable positions are computed. Pattern: `(?<![\w.,])([0-9]{1,4}(?:[ \t]?(?i:bis|ter|quater|quinquies|
/// [a-h])(?![\w]))?(?:[ \t]?[-/][ \t]?[0-9]{1,4})?)[ \t]{0,2},?[ \t]{0,2}$`.
fn number_before(t: Chars, lo: usize, suffixes: &[CiPattern]) -> Option<usize> {
    (lo..t.len()).find(|&p| house_number_at(t, p, suffixes))
}

fn house_number_at(t: Chars, p: usize, suffixes: &[CiPattern]) -> bool {
    if !t.digit(p) || (p > 0 && t.test(p - 1, |c| t.u.is_word(c) || c == '.' || c == ',')) {
        return false;
    }
    // `(?<!\b[LRDA]\.[ \t])(?<![0-9]-)` : pas un article de code (« L. 1221-3 »), ni la fin d'un intervalle déjà lu
    // / not a code article number, nor the end of a range.
    if p >= 2 && t.is(p - 1, '-') && t.digit(p - 2) {
        return false;
    }
    if p >= 3
        && t.test(p - 1, |c| c == ' ' || c == '\t')
        && t.is(p - 2, '.')
        && t.test(p - 3, |c| matches!(c, 'L' | 'R' | 'D' | 'A'))
        && (p == 3 || !t.test(p - 4, |c| t.u.is_word(c)))
    {
        return false;
    }
    let numbers: Vec<usize> = (1..=t.digits(p, 4)).map(|count| p + count).collect();
    let mut with_suffix = numbers.clone();
    for &x in &numbers {
        for y in [x, x + 1] {
            if y == x + 1 && !t.blank(x) {
                continue;
            }
            for word in suffixes {
                let z = y + word.len();
                if t.literal_ci(y, word) && !t.word(z) {
                    with_suffix.push(z);
                }
            }
        }
    }
    let mut with_range = with_suffix.clone();
    for &x in &with_suffix {
        for y in [x, x + 1] {
            if (y == x + 1 && !t.blank(x)) || !t.test(y, |c| c == '-' || c == '/') {
                continue;
            }
            for z in [y + 1, y + 2] {
                if z == y + 2 && !t.blank(y + 1) {
                    continue;
                }
                with_range.extend((1..=t.digits(z, 4)).map(|count| z + count));
            }
        }
    }
    with_range.into_iter().any(|x| separator_then_end(t, x))
}

/// `[ \t]{0,2},?[ \t]{0,2}$` depuis `x` ; `$` : fin de la vue, ou juste avant un « \n » final.
/// From `x`; `$`: end of the view, or right before a final newline.
fn separator_then_end(t: Chars, x: usize) -> bool {
    let n = t.len();
    let ends = [Some(n), (n > 0 && t.is(n - 1, '\n')).then(|| n - 1)];
    ends.into_iter().flatten().filter(|&end| end >= x).any(|end| {
        let len = end - x;
        let lead = t.blanks(x, len);
        if lead == len {
            return lead <= 4;
        }
        let rest = len - lead - 1;
        lead <= 2 && t.is(x + lead, ',') && rest <= 2 && t.blanks(x + lead + 1, rest) == rest
    })
}

/// `_NAME_WORD_RE.finditer(text, pos, limit)` : prochain mot à partir de `from` / next word from `from`.
/// `[^\W\d_][^\W\d_'’-]{0,30}(?:['’-][^\W\d_]{1,30}){0,4}|[0-9]{1,4}(?:er|e|ème)?(?!\w)`.
fn name_word(t: Chars, from: usize) -> Option<(usize, usize)> {
    (from..t.len()).find_map(|p| name_word_at(t, p).map(|end| (p, end)))
}

fn name_word_at(t: Chars, p: usize) -> Option<usize> {
    let letters = |at: usize| t.run(at, 30, |c| t.u.is_letter(c));
    if t.letter(p) {
        let mut end = p + 1 + letters(p + 1);
        for _ in 0..4 {
            if !(t.test(end, |c| matches!(c, '\'' | '’' | '-')) && t.letter(end + 1)) {
                break;
            }
            end += 1 + letters(end + 1);
        }
        return Some(end);
    }
    for count in (1..=t.digits(p, 4)).rev() {
        let j = p + count;
        for ordinal in ["er", "e", "ème", ""] {
            let k = j + ordinal.chars().count();
            if t.literal(j, ordinal) && !t.word(k) {
                return Some(k);
            }
        }
    }
    None
}

/// `_LINK_RE.fullmatch(text, a, b)` : `[ \t]{0,3}[,;–—-]?[ \t]{0,3}(?:\r?\n[ \t]{0,6}(?:[–—-][ \t]{0,3})?)?`.
fn link(t: Chars, a: usize, b: usize) -> bool {
    let s = t.upto(b);
    let lead = s.blanks(a, usize::MAX);
    let mut i = a + lead;
    if s.test(i, |c| matches!(c, ',' | ';' | '–' | '—' | '-')) {
        let rest = s.blanks(i + 1, usize::MAX);
        if lead > 3 || rest > 3 {
            return false;
        }
        i += 1 + rest;
    } else if lead > 6 {
        return false;
    }
    if i == b {
        return true;
    }
    if s.is(i, '\r') {
        i += 1;
    }
    if !s.is(i, '\n') {
        return false;
    }
    let indent = s.blanks(i + 1, usize::MAX);
    if indent > 6 {
        return false;
    }
    let after = i + 1 + indent;
    if after == b {
        return true;
    }
    // Tiret en tête de ligne (« …⏎– 59000 Lille ») / dash at the start of the line.
    s.test(after, |c| matches!(c, '–' | '—' | '-'))
        && s.blanks(after + 1, usize::MAX) <= 3
        && after + 1 + s.blanks(after + 1, usize::MAX) == b
}

/// Littéral insensible à la casse, écrit en minuscules / case-insensitive literal written in lowercase.
fn literal_lower(t: Chars, at: usize, word: &str) -> bool {
    word.chars().enumerate().all(|(k, w)| t.test(at + k, |c| c == w || c.to_lowercase().eq(std::iter::once(w))))
}

/// Étage écrit avec son rang (`_COMPLEMENT`) : `[0-9]{1,2}(?i:er|re|e|[eè]me)[ \t]{1,2}(?i:[ée]tage)` depuis
/// `lo + i`, jusqu'à une position de `tail`. A floor written with its rank first, up to a position of `tail`.
fn floor_rank(t: Chars, lo: usize, i: usize, tail: &[bool]) -> bool {
    let start = lo + i;
    let digits = t.run(start, 2, |c| c.is_ascii_digit());
    (1..=digits).any(|d| {
        ["er", "re", "e", "ème", "eme"].iter().any(|suffix| {
            let p = start + d;
            if !literal_lower(t, p, suffix) {
                return false;
            }
            let p = p + suffix.chars().count();
            (1..=t.blanks(p, 2)).any(|k| {
                ["étage", "etage"].iter().any(|w| literal_lower(t, p + k, w) && tail.get(p + k + 5 - lo) == Some(&true))
            })
        })
    })
}

/// Positions d'où `[ \t]{0,max}` mène dans `set` / positions from which `[ \t]{0,max}` leads into `set`.
fn before_blanks(t: Chars, lo: usize, set: &[bool], max: usize) -> Vec<bool> {
    (0..set.len()).map(|i| (0..=t.blanks(lo + i, max)).any(|j| set.get(i + j) == Some(&true))).collect()
}

/// Positions d'où `[\w'’-]{1,20}` mène dans `set` / positions from which a `[\w'’-]{1,20}` token leads into `set`.
fn before_tokens(t: Chars, lo: usize, set: &[bool]) -> Vec<bool> {
    let token = |c: char| t.u.is_word(c) || matches!(c, '\'' | '’' | '-');
    (0..set.len()).map(|i| (1..=t.run(lo + i, 20, token)).any(|j| set.get(i + j) == Some(&true))).collect()
}

/// Positions d'où un caractère facultatif de la classe mène dans `set` / an optional class character.
fn before_optional(t: Chars, lo: usize, set: &[bool], class: impl Fn(char) -> bool) -> Vec<bool> {
    (0..set.len()).map(|i| set[i] || (t.test(lo + i, &class) && set.get(i + 1) == Some(&true))).collect()
}

/// `_cued` : un mot de domicile dans la même phrase, juste avant / a home cue right before, same sentence.
fn cued(f: Chars, start: usize) -> bool {
    let view = f.upto(start);
    let mut p = start.saturating_sub(CUE_WINDOW);
    let mut last = None;
    while p < start {
        match trigger_at(view, p) {
            Some(end) => {
                last = Some(end);
                p = end;
            }
            None => p += 1,
        }
    }
    last.is_some_and(|end| !(end..start).any(|i| view.is(i, '\n') || view.is(i, '.')))
}

/// `_home` : « domiciliée à 69003 Lyon », un mot de domicile avant `pos`, même ligne, même phrase (dernière
/// occurrence de `_HOME_RE` dans `[pos - 50, pos)`) / a home word before `pos`, same line and sentence.
fn home(f: Chars, pos: usize) -> bool {
    let view = f.upto(pos);
    let mut p = pos.saturating_sub(HOME_WINDOW);
    let mut last = None;
    while p < pos {
        match home_at(view, p) {
            Some(end) => {
                last = Some(end);
                p = end;
            }
            None => p += 1,
        }
    }
    last.is_some_and(|end| !(end..pos).any(|i| view.is(i, '\n') || view.is(i, '.')))
}

/// `_HOME_RE` en `p` : `(?<!\w)(?:domicil|demeur|resid|habit)` (l'assertion voit avant `pos`) / the look-behind
/// sees before `pos`.
fn home_at(f: Chars, p: usize) -> Option<usize> {
    if p > 0 && f.word(p - 1) {
        return None;
    }
    HOME_WORDS.into_iter().find(|w| f.literal(p, w)).map(|w| p + w.len())
}

/// `str.isupper()` de `t[a..b]` : aucune minuscule ni casse de titre, au moins une majuscule.
/// No lowercase nor titlecase character, at least one uppercase character.
fn is_upper_word(t: Chars, a: usize, b: usize) -> bool {
    let mut cased = false;
    for &c in &t.s[a..b] {
        if t.u.is_lower(c) || t.u.is(c, TITLE) {
            return false;
        }
        cased |= t.u.is_upper(c);
    }
    cased
}

/// `_TRIGGER_RE` en `p` : `domicili|demeur|resid|habit|adresse|\bsise?\b` (`\b` voit avant `pos`, pas après
/// `endpos`) / `\b` sees before `pos`, not after `endpos`.
fn trigger_at(f: Chars, p: usize) -> Option<usize> {
    if let Some(word) = ["domicili", "demeur", "resid", "habit", "adresse"].into_iter().find(|w| f.literal(p, w)) {
        return Some(p + word.len());
    }
    if (p > 0 && f.word(p - 1)) || !f.literal(p, "sis") {
        return None;
    }
    let end = p + 3;
    if f.is(end, 'e') && !f.word(end + 1) {
        return Some(end + 1);
    }
    (!f.word(end)).then_some(end)
}

/// `_BOX_ALONE_DIGITS` : chiffres d'une boîte postale masquée seule / digits of a postal box masked alone.
const BOX_ALONE_DIGITS: usize = 3;
/// `_BOX_SURE_DIGITS`, `_BOX_NEAR_BEFORE`, `_BOX_NEAR_AFTER`.
const BOX_SURE_DIGITS: usize = 5;
const BOX_NEAR_BEFORE: usize = 80;
const BOX_NEAR_AFTER: usize = 160;

/// `_lone_box` : boîte postale en capitales, 3 chiffres au moins et pas une année ; sous 5 chiffres, un code postal
/// ou CEDEX sur sa ligne ou la suivante. Capitals, 3 digits or more, not a year; under 5 digits, a nearby
/// postcode or CEDEX.
fn lone_box(s: &[char], start: usize, end: usize) -> bool {
    if !matches!(s.get(start), Some('B' | 'C' | 'T')) {
        return false;
    }
    let digits: Vec<char> = s[start..end].iter().copied().filter(char::is_ascii_digit).collect();
    if digits.len() < BOX_ALONE_DIGITS || (digits.len() == 4 && matches!(digits[..2], ['1', '9'] | ['2', '0'])) {
        return false;
    }
    if digits.len() >= BOX_SURE_DIGITS {
        return true;
    }
    let floor = start.saturating_sub(BOX_NEAR_BEFORE);
    let lo = (floor..start).rev().find(|&i| s[i] == '\n').map_or(floor, |i| i + 1);
    let limit = s.len().min(end + BOX_NEAR_AFTER);
    let hi = match (end..limit).find(|&i| s[i] == '\n') {
        None => limit,
        Some(first) => (first + 1..limit).find(|&i| s[i] == '\n').unwrap_or(limit),
    };
    near_postcode(&s[lo..hi.max(lo)])
}

/// `_BOX_NEAR_RE.search` : 5 chiffres exactement, ou « cedex » / exactly 5 digits, or "cedex".
fn near_postcode(w: &[char]) -> bool {
    let mut i = 0;
    while i < w.len() {
        if w[i].is_ascii_digit() {
            let run = w[i..].iter().take_while(|c| c.is_ascii_digit()).count();
            if run == 5 {
                return true;
            }
            i += run;
            continue;
        }
        if w.len() - i >= 5
            && matches!(w[i], 'C' | 'c')
            && matches!(w[i + 1], 'E' | 'e' | 'É' | 'é')
            && matches!(w[i + 2], 'D' | 'd')
            && matches!(w[i + 3], 'E' | 'e')
            && matches!(w[i + 4], 'X' | 'x')
        {
            return true;
        }
        i += 1;
    }
    false
}

/// `_TOWN_GAP_RE.match` : `[ \t]{0,2},[ \t]{1,2}|[ \t]{1,2}[à–-][ \t]{1,2}` -> fin / end.
fn town_gap(t: Chars, pos: usize) -> Option<usize> {
    let lead = t.blanks(pos, 3);
    let sep = pos + lead;
    if lead > 2 {
        return None;
    }
    let comma = t.is(sep, ',');
    if !comma && (lead == 0 || !(t.is(sep, 'à') || t.is(sep, '–') || t.is(sep, '-'))) {
        return None;
    }
    let trail = t.blanks(sep + 1, 2);
    (trail > 0).then_some(sep + 1 + trail)
}

/// `_TOWN_END_RE.match` : `[ \t]{0,2}(?:[\r\n.,;)]|$)`.
fn town_end_at(t: Chars, pos: usize) -> bool {
    let at = pos + t.blanks(pos, 2);
    at == t.len() || t.test(at, |c| matches!(c, '\r' | '\n' | '.' | ',' | ';' | ')'))
}

/// `_ADJECTIVE_BEFORE_RE.search(text, start - 12, start)` : `(?<![\w.,'’-])([^\W\d_]{3,9})[ \t]{1,2}$`, début
/// du groupe / group start. Seul le début de la suite de lettres peut passer l'assertion arrière / only the start of
/// the letter run can pass the look-behind.
fn adjective_before(t: Chars, start: usize) -> Option<(usize, usize)> {
    let lo = start.saturating_sub(ADJECTIVE_WINDOW);
    let gap = (0..3).take_while(|&i| start > i && t.blank(start - 1 - i)).count();
    if !(1..=2).contains(&gap) {
        return None;
    }
    let word_end = start - gap;
    let mut word_start = word_end;
    while word_start > 0 && t.letter(word_start - 1) && word_end - word_start < 10 {
        word_start -= 1;
    }
    let free =
        word_start == 0 || !t.test(word_start - 1, |c| t.u.is_word(c) || matches!(c, '.' | ',' | '\'' | '’' | '-'));
    ((3..=9).contains(&(word_end - word_start)) && word_start >= lo && free).then_some((word_start, word_end))
}

/// `_POSTCODE_TAIL_RE.match` : `[ \t]{0,2},?[ \t]{1,2}([0-9]{5})(?![\w]|[.,][0-9])` -> (code, fin / end).
fn postcode_tail(t: Chars, end: usize) -> Option<(String, usize)> {
    for lead in (0..=t.blanks(end, 2)).rev() {
        let i = end + lead;
        for comma in [true, false] {
            if comma && !t.is(i, ',') {
                continue;
            }
            let j = i + usize::from(comma);
            for gap in (1..=t.blanks(j, 2)).rev() {
                let k = j + gap;
                let after = k + 5;
                if t.digits(k, 5) == 5
                    && !t.word(after)
                    && !(t.test(after, |c| c == '.' || c == ',') && t.digit(after + 1))
                {
                    return Some((t.string(k, after), after));
                }
            }
        }
    }
    None
}

/// Fins possibles de `[Ll]\.?[Ll]\.?…` (lettres ASCII des deux casses, points facultatifs), dans l'ordre glouton.
/// Possible ends of `[Ll]\.?[Ll]\.?…` (ASCII letters of either case, optional dots), in greedy order.
fn dotted_ends(t: Chars, p: usize, letters: &[char]) -> Vec<usize> {
    let Some((&first, rest)) = letters.split_first() else {
        return vec![p];
    };
    if !t.test(p, |c| c.eq_ignore_ascii_case(&first)) {
        return Vec::new();
    }
    let mut ends = Vec::new();
    if t.is(p + 1, '.') {
        ends.extend(dotted_ends(t, p + 2, rest));
    }
    ends.extend(dotted_ends(t, p + 1, rest));
    ends
}

/// `[ \t]?[0-9]{1,5}(?![\w])`.
fn box_number(t: Chars, q: usize) -> Option<usize> {
    for i in [q + 1, q] {
        if i == q + 1 && !t.blank(q) {
            continue;
        }
        for count in (1..=t.digits(i, 5)).rev() {
            if !t.word(i + count) {
                return Some(i + count);
            }
        }
    }
    None
}
