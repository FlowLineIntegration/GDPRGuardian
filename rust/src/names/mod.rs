//! Détecteur de personnes : portage exact de `FrenchNameDetector` (Python), sans GIL.
//!
//! Person detector: exact port of the Python `FrenchNameDetector`, run without the GIL. Python reste la
//! référence : mêmes zones, scores, valeurs canoniques et formes propagées, prouvé par des tests
//! différentiels (corpus, fuzzing). Python stays the reference: same spans, scores, canonical values and
//! propagated forms, proven by differential tests.
//!
//! Construit une fois à partir des données de Python (lexique, listes de mots, déclencheurs, tables
//! Unicode) ; un appel ne garde rien du document. Built once from Python's data; a call keeps nothing
//! of the document. Chaque module porte une partie de `fr_names.py` / each module ports one part:
//! `tokens` (jetons, suites), `cues` (indices), `fields` (minuscules), `tables` (colonnes), `decide`
//! (décision, scores), `spans` (forme canonique).

mod chars;
mod cues;
mod decide;
mod fields;
mod lexicon;
mod patterns;
pub mod py;
mod spans;
mod tables;
mod tokens;
mod vocab;

use std::collections::{HashMap, HashSet};
use std::hash::{BuildHasherDefault, Hasher};

use aho_corasick::AhoCorasick;

use chars::Chars;
use lexicon::{ambiguity, given_rank, surname_rank, Kind, AMB_NONE, AMB_WORD, RANK_MASK};
use vocab::{Entry, Vocab};

// Forces des indices (`NEG` … `STRONG`) / cue strengths.
const NEG: i8 = -1;
const NONE: i8 = 0;
const WEAK: i8 = 1;
const MEDIUM: i8 = 2;
const STRONG: i8 = 3;

// Drapeaux des déclencheurs (`T_*`), vérifiés contre Python / trigger flags, checked against Python.
const T_HONORIFIC: u32 = 1;
const T_GREETING: u32 = 2;
const T_CLOSING: u32 = 4;
const T_ROLE: u32 = 8;
const T_EPONYM: u32 = 16;
const T_EPONYM_DIRECT: u32 = 32;

// Seuils de rang (log2 du nombre de naissances), vérifiés contre Python / rank thresholds, checked.
const GIVEN_ALONE_MIN: u8 = 9;
const SURNAME_ALONE_MIN: u8 = 8;
const GIVEN_START_MIN: u8 = 14;
const COMMUNE_SURNAME_MIN: u8 = 12;
const ENTITY_GIVEN_MIN: u8 = 12;
const CAPS_ALONE_MIN: u8 = 10;
const MAX_RUN: usize = 6;

/// Taille de texte prise en charge (octets UTF-8, donc caractères au plus) / supported text size.
const MAX_TEXT_BYTES: usize = (u32::MAX / 4) as usize;

/// Constantes partagées avec Python, comparées à la construction / constants shared with Python.
pub(crate) const CONTRACT: [(&str, i64); 21] = [
    ("GIVEN_MASK", lexicon::GIVEN_MASK as i64),
    ("SURNAME_SHIFT", lexicon::SURNAME_SHIFT as i64),
    ("AMB_SHIFT", lexicon::AMB_SHIFT as i64),
    ("RANK_MASK", RANK_MASK as i64),
    ("AMB_NONE", AMB_NONE as i64),
    ("AMB_WORD", AMB_WORD as i64),
    ("AMB_STRONG", lexicon::AMB_STRONG as i64),
    ("AMB_ENTITY", lexicon::AMB_ENTITY as i64),
    ("T_HONORIFIC", T_HONORIFIC as i64),
    ("T_GREETING", T_GREETING as i64),
    ("T_CLOSING", T_CLOSING as i64),
    ("T_ROLE", T_ROLE as i64),
    ("T_EPONYM", T_EPONYM as i64),
    ("T_EPONYM_DIRECT", T_EPONYM_DIRECT as i64),
    ("GIVEN_ALONE_MIN", GIVEN_ALONE_MIN as i64),
    ("SURNAME_ALONE_MIN", SURNAME_ALONE_MIN as i64),
    ("GIVEN_START_MIN", GIVEN_START_MIN as i64),
    ("COMMUNE_SURNAME_MIN", COMMUNE_SURNAME_MIN as i64),
    ("_ENTITY_GIVEN_MIN", ENTITY_GIVEN_MIN as i64),
    ("CAPS_ALONE_MIN", CAPS_ALONE_MIN as i64),
    ("MAX_RUN", MAX_RUN as i64),
];

/// Déclencheur replié et ses propriétés / folded trigger and its properties.
pub(crate) struct Trigger {
    flags: u32,
    /// Bornes de mot à vérifier (`p[0].isalnum()`, `p[-1].isalnum()`) / word bounds to check.
    check_left: bool,
    check_right: bool,
    /// Civilité exigée avec une majuscule (« Me », « Pr ») / honorific that needs a capital letter.
    case_sensitive: bool,
    /// « chez » désigne aussi un lieu : pas d'interpellation / "chez" may name a place.
    chez: bool,
}

/// Petites listes de `fr_names` et `_lexicon` / small lists of `fr_names` and `_lexicon`.
pub(crate) struct TextSets {
    /// `SAINT_PREFIXES` (`_lexicon`).
    saint_prefixes: Vec<Vec<char>>,
    /// `_VERB_TAILS`.
    verb_tails: Vec<Vec<char>>,
    /// `_SKIP_BACK`.
    skip_back: Vec<char>,
    /// `_SENTENCE_END`.
    sentence_end: Vec<char>,
}

/// Détecteur compilé une fois, partagé en lecture seule entre threads / compiled once, shared read-only.
pub struct NameDetector {
    chars: Chars,
    vocab: Vocab,
    triggers: AhoCorasick,
    trigger_info: Vec<Trigger>,
    dotted_forms: AhoCorasick,
    text_sets: TextSets,
}

/// Zone de personne (positions en caractères Python) / person span (Python character offsets).
pub struct Found {
    pub start: usize,
    pub end: usize,
    pub value: String,
    pub score: f64,
    pub propagate: bool,
    /// Forme du nom de famille avant `str.title()` (appliqué par Python) / surname form before `title()`.
    pub form: Option<String>,
}

/// Clé repliée d'un élément, dans l'arène de l'appel / folded key of an element, in the call's arena.
#[derive(Clone, Copy)]
struct Key {
    start: u32,
    end: u32,
}

impl Key {
    #[inline]
    fn len(self) -> usize {
        (self.end - self.start) as usize
    }
}

/// Arène des clés d'un appel : une allocation pour tous les jetons / one allocation for all tokens.
#[derive(Default)]
struct Keys(Vec<char>);

impl Keys {
    fn push(&mut self, parts: &[&[char]]) -> Key {
        let start = self.0.len() as u32;
        parts.iter().for_each(|part| self.0.extend_from_slice(part));
        Key { start, end: self.0.len() as u32 }
    }

    /// Prolonge `key` de `parts`, sur place quand c'est la dernière clé de l'arène (« Anne-⏎Sophie ») : une
    /// longue chaîne de coupures garde une mémoire linéaire. Extends `key` with `parts`, in place when it is
    /// the arena's last key: a long chain of line-break hyphens keeps linear memory.
    fn extend(&mut self, key: Key, parts: &[&[char]]) -> Key {
        let start = if key.end as usize == self.0.len() {
            key.start
        } else {
            let start = self.0.len() as u32;
            self.0.extend_from_within(key.start as usize..key.end as usize);
            start
        };
        parts.iter().for_each(|part| self.0.extend_from_slice(part));
        Key { start, end: self.0.len() as u32 }
    }

    #[inline]
    fn get(&self, key: Key) -> &[char] {
        &self.0[key.start as usize..key.end as usize]
    }
}

/// Élément d'un nom : un jeton, ou un nom composé de plusieurs jetons (`_Element`) / one name element.
/// `entry` : appartenances de sa clé, lues une fois / its key's memberships, looked up once.
#[derive(Clone, Copy)]
struct Element {
    start: usize,
    end: usize,
    kind: Kind,
    code: u16,
    key: Key,
    entry: Entry,
    caps: bool,
}

impl Element {
    #[inline]
    fn given(&self) -> u8 {
        if self.kind == Kind::Name {
            given_rank(self.code)
        } else {
            0
        }
    }

    #[inline]
    fn surname(&self) -> u8 {
        if self.kind == Kind::Name {
            surname_rank(self.code)
        } else {
            0
        }
    }

    #[inline]
    fn amb(&self) -> u8 {
        if self.kind == Kind::Name {
            ambiguity(self.code)
        } else {
            AMB_NONE
        }
    }

    /// Nom sûr, ou prénom très fréquent / unambiguous name, or very frequent given name.
    fn solid(&self) -> bool {
        self.kind == Kind::Name
            && ((self.amb() == AMB_NONE && self.code & RANK_MASK != 0)
                || (self.amb() == AMB_WORD && self.given() >= GIVEN_START_MIN))
    }

    /// Ni mot courant ni lieu : sa forme seule désigne la personne / not a word nor a place.
    fn safe(&self) -> bool {
        self.kind == Kind::Unknown || (self.kind == Kind::Name && self.amb() == AMB_NONE)
    }
}

/// `_Cues.inside` : zone triée qui commence au plus tard en `start` et contient [start, end).
/// The last sorted zone starting at or before `start` contains [start, end).
fn inside(zones: &[(usize, usize)], start: usize, end: usize) -> bool {
    let i = zones.partition_point(|&(zone_start, _)| zone_start <= start);
    i > 0 && zones[i - 1].0 <= start && end <= zones[i - 1].1
}

/// Formes confirmées d'un document (clés repliées) / confirmed forms of a document (folded keys).
type Confirmed = HashSet<Vec<char>>;

/// Hachage des positions d'un appel : mélange splitmix64, bien plus rapide que SipHash pour un entier. Les
/// positions sont bornées par la longueur du texte : des collisions fabriquées restent en nombre borné.
/// Hash of a call's positions: splitmix64 mix, much faster than SipHash for an integer. Positions are
/// bounded by the text length, so crafted collisions stay bounded.
#[derive(Default)]
struct PositionHasher(u64);

impl Hasher for PositionHasher {
    fn finish(&self) -> u64 {
        let mut z = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    fn write(&mut self, bytes: &[u8]) {
        bytes.iter().for_each(|&b| self.0 = self.0.rotate_left(8) ^ b as u64);
    }

    fn write_usize(&mut self, n: usize) {
        self.0 = n as u64;
    }
}

type Positions = HashSet<usize, BuildHasherDefault<PositionHasher>>;
type PositionMap<V> = HashMap<usize, V, BuildHasherDefault<PositionHasher>>;

/// Un appel : le texte et sa forme repliée, en points de code (positions Python), et l'index des fins
/// de ligne. One call: text and folded text as code points (Python positions), and the newline index.
struct Doc<'a> {
    det: &'a NameDetector,
    text: Vec<char>,
    folded: Vec<char>,
    text_utf8: &'a str,
    folded_utf8: &'a str,
    newlines: Vec<usize>,
}

impl NameDetector {
    /// Zones de personnes de `text` ; `None` si `folded` n'a pas la longueur de `text` (cas que la référence
    /// ne traite pas : Python garde la main). `person_rows` : segments marqués « personne » par leur en-tête.
    /// Person spans; `None` when `folded` and `text` differ in length (Python keeps that case).
    pub fn detect(&self, text: &str, folded: &str, person_rows: &[(usize, usize)]) -> Option<Vec<Found>> {
        // L'arène des clés (au plus deux fois le texte) est indexée en `u32` : au-delà, Python garde la main.
        // The key arena (at most twice the text) uses `u32` offsets: beyond that, Python keeps the case.
        if text.len() > MAX_TEXT_BYTES {
            return None;
        }
        let chars = chars::code_points(text);
        let folded_chars = chars::code_points(folded);
        if chars.len() != folded_chars.len() {
            return None;
        }
        let newlines = chars.iter().enumerate().filter(|(_, &c)| c == '\n').map(|(i, _)| i).collect();
        let doc = Doc { det: self, text: chars, folded: folded_chars, text_utf8: text, folded_utf8: folded, newlines };
        Some(doc.detect(person_rows))
    }
}

impl Doc<'_> {
    /// `FrenchNameDetector.detect`, hors vue composée et filtre de segments (restés en Python).
    /// The detector body; the composed view and the segment filter stay in Python.
    fn detect(&self, person_rows: &[(usize, usize)]) -> Vec<Found> {
        let mut found = Vec::new();
        let mut strong_zones = Vec::new();
        let mut confirmed = Confirmed::new();
        self.structured(person_rows, &mut found, &mut strong_zones, &mut confirmed);
        let labels = if self.text.contains(&':') { self.label_cues() } else { Vec::new() };
        if !labels.is_empty() {
            self.lowercase_fields(&labels, &mut found);
        }
        let mut keys = Keys::default();
        let tokens = self.tokens(&mut keys);
        let cues = self.cues(strong_zones, &labels);
        self.lowercase_after_cues(&cues, &mut found);
        if !tokens.is_empty() {
            if self.text.contains(&'@') {
                self.email_names(&mut confirmed);
            }
            let mut claimed: Vec<(usize, usize)> = found.iter().map(|f| (f.start, f.end)).collect();
            claimed.sort_unstable();
            let (elements, mut runs) = self.runs(&tokens, &claimed, &mut keys);
            let (accepted, eponyms) = self.decide(&elements, &mut runs, &cues, &mut confirmed, &keys);
            found.extend(accepted.into_iter().filter_map(|r| self.span(&runs[r], &elements, &cues, &eponyms, &keys)));
        }
        found
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn arena_extends_the_last_key_in_place() {
        let mut keys = Keys::default();
        let mut key = keys.push(&[&['a']]);
        // Chaîne de coupures : l'arène croît comme le texte, pas comme le carré / grows linearly, not quadratically.
        for _ in 0..1000 {
            key = keys.extend(key, &[&['-'], &['b', 'c']]);
        }
        assert_eq!((key.start, key.len(), keys.0.len()), (0, 3001, 3001));
        // Clé qui n'est plus la dernière : recopiée, l'originale reste intacte / no longer last: copied.
        let first = keys.push(&[&['x']]);
        let other = keys.push(&[&['y']]);
        let grown = keys.extend(first, &[&['z']]);
        assert_eq!((keys.get(first), keys.get(other), keys.get(grown)), (&['x'][..], &['y'][..], &['x', 'z'][..]));
    }
}
