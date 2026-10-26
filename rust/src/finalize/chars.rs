//! Sémantique des caractères de Python, fournie par Python / Python's character semantics, from Python.
//!
//! Les prédicats (`str.isalnum`, `str.isspace`…) et les casses (`str.upper`) dépendent de la base Unicode
//! de l'interpréteur : Rust ne les devine jamais. Ils viennent de la table unique du noyau (`crate::unicode`),
//! construite par Python une fois par processus ; un plan hors BMP y est chargé une fois, au premier de ses
//! caractères, jamais à chaque appel (aucun état tiré des documents). Predicates and case mappings depend on the
//! interpreter's Unicode database: Rust never guesses them. They come from the core's single table, built by
//! Python once per process; an astral plane is loaded once, at its first character, never per call.

use std::collections::HashSet;
use std::sync::Arc;

use crate::unicode::Unicode;
pub use crate::unicode::{ALNUM, ALPHA, DECIMAL, DIGIT, SPACE, UPPER, UPPER_SAFE};

/// Règles de texte partagées (une fois par processus) / shared text rules (once per process).
pub struct Rules {
    pub unicode: Arc<Unicode>,
    honorifics: HashSet<Box<str>>,
    /// Particules de tête d'un nom de famille, repliées (`_vocab.SURNAME_PARTICLES`) / leading surname particles.
    particles: HashSet<Box<str>>,
}

impl Rules {
    pub fn new(unicode: Arc<Unicode>, honorifics: Vec<String>, particles: Vec<String>) -> Self {
        let boxed = |words: Vec<String>| words.into_iter().map(String::into_boxed_str).collect();
        Self { unicode, honorifics: boxed(honorifics), particles: boxed(particles) }
    }
}

/// Vue de la sémantique Python pour un appel, une fois ses plans chargés (`PyTextRules::prepare`).
/// Python semantics for one call, once its planes are loaded.
#[derive(Clone, Copy)]
pub struct Chars<'a> {
    rules: &'a Rules,
}

impl<'a> Chars<'a> {
    pub fn new(rules: &'a Rules) -> Self {
        Self { rules }
    }

    #[inline]
    pub fn flags(&self, c: char) -> u16 {
        self.rules.unicode.flags(c)
    }

    #[inline]
    pub fn is(&self, c: char, flag: u16) -> bool {
        self.flags(c) & flag != 0
    }

    fn mapping(&self, c: char, upper: bool) -> Option<&'a str> {
        let unicode = &*self.rules.unicode;
        if upper {
            unicode.upper(c)
        } else {
            unicode.lower(c)
        }
    }

    /// `str.upper()` : correspondance complète caractère par caractère / full per-character mapping.
    pub fn upper(&self, text: &str) -> String {
        let mut out = String::with_capacity(text.len());
        for c in text.chars() {
            match self.mapping(c, true) {
                Some(mapped) => out.push_str(mapped),
                None => out.push(c),
            }
        }
        out
    }

    /// `text.lower().startswith(prefix)` sans minusculer tout le texte / without lowering the whole text.
    pub fn lower_starts_with(&self, text: &str, prefix: &str) -> bool {
        let mut lowered = String::new();
        for c in text.chars() {
            if lowered.len() >= prefix.len() {
                break;
            }
            match self.mapping(c, false) {
                Some(mapped) => lowered.push_str(mapped),
                None => lowered.push(c),
            }
        }
        lowered.starts_with(prefix)
    }

    /// `_text.fold`, caractère par caractère, sans allocation / character by character, without allocating.
    pub fn folded<'t>(&self, text: &'t str) -> impl Iterator<Item = char> + 't
    where
        'a: 't,
    {
        // Texte ASCII : `str.lower()` ; sinon `str.translate` d'une table du BMP (astraux inchangés).
        // ASCII text: `str.lower()`; otherwise a BMP translation table (astral characters unchanged).
        let ascii = text.is_ascii();
        let unicode = &*self.rules.unicode;
        text.chars().map(move |c| if ascii { c.to_ascii_lowercase() } else { unicode.fold(c) })
    }

    /// `_text.fold` : minuscules sans accents, longueur préservée / lowercase without accents, same length.
    pub fn fold(&self, text: &str) -> String {
        self.folded(text).collect()
    }

    /// `str.strip()`.
    pub fn strip<'t>(&self, text: &'t str) -> &'t str {
        text.trim_matches(|c| self.is(c, SPACE))
    }

    /// `str.isupper()` : un caractère seul, sinon aucun caractère minuscule ou de titre et au moins une majuscule.
    /// `str.isupper()`: a single character, else no lowercase or titlecase character and at least one uppercase.
    pub fn is_upper(&self, text: &str) -> bool {
        let mut chars = text.chars();
        match (chars.next(), chars.next()) {
            (None, _) => false,
            (Some(c), None) => self.is(c, UPPER),
            _ => {
                let mut cased = false;
                for c in text.chars() {
                    let flags = self.flags(c);
                    if flags & UPPER_SAFE == 0 {
                        return false;
                    }
                    cased |= flags & UPPER != 0;
                }
                cased
            }
        }
    }

    /// `fold(word) in HONORIFICS` (« M », « Mme », « Dr »…), replié sur la pile / folded on the stack.
    pub fn is_honorific(&self, word: &str) -> bool {
        self.folded_in(word, &self.rules.honorifics)
    }

    /// `fold(word) in SURNAME_PARTICLES` (« Le », « De », « Van »…) / leading surname particle.
    pub fn is_particle(&self, word: &str) -> bool {
        self.folded_in(word, &self.rules.particles)
    }

    /// `fold(word) in set`, replié sur la pile / folded on the stack.
    fn folded_in(&self, word: &str, set: &HashSet<Box<str>>) -> bool {
        let mut buffer = [0u8; 64];
        let mut length = 0;
        for c in self.folded(word) {
            match buffer.get_mut(length..length + c.len_utf8()) {
                Some(slot) => length += c.encode_utf8(slot).len(),
                // Mot plus long que le tampon : chemin général / word longer than the buffer: general path.
                None => return set.contains(self.fold(word).as_str()),
            }
        }
        std::str::from_utf8(buffer.get(..length).unwrap_or_default()).is_ok_and(|w| set.contains(w))
    }
}

/// Table de test : ASCII et « É », comme Python les classerait / test table: ASCII and "É", as Python would.
#[cfg(test)]
pub fn test_rules() -> Rules {
    let honorifics = ["m", "mme", "dr", "monsieur"].map(String::from).to_vec();
    let particles = ["le", "la", "de", "du", "van"].map(String::from).to_vec();
    Rules::new(crate::unicode::test_unicode(), honorifics, particles)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn predicates_and_mappings() {
        let rules = test_rules();
        let chars = Chars::new(&rules);
        assert!(chars.is('a', ALNUM) && !chars.is('-', ALNUM));
        assert_eq!(chars.upper("abc-é1"), "ABC-É1");
        assert_eq!(chars.fold("ÉTÉ"), "ete");
        assert_eq!(chars.fold("ABC"), "abc");
        assert_eq!(chars.strip("  x y \n"), "x y");
        assert!(chars.is_upper("AB") && !chars.is_upper("Ab") && !chars.is_upper("12") && chars.is_upper("A1"));
        assert!(chars.lower_starts_with("NER_x", "ner") && !chars.lower_starts_with("NE", "ner"));
        assert!(chars.is_honorific("Mme") && chars.is_honorific("MONSIEUR") && !chars.is_honorific("Mmes"));
        assert!(!chars.is_honorific(&"m".repeat(80)));
        assert!(chars.is_particle("Le") && chars.is_particle("VAN") && !chars.is_particle("Verger"));
    }
}
