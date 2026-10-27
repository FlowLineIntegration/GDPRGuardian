//! Codes du lexique et classement des jetons : portage de `Lexicon.code` et `Lexicon.classify`.
//!
//! Lexicon codes and token classification: port of `Lexicon.code` and `Lexicon.classify`.

use super::chars::{eq, sub};
use super::patterns;
use super::vocab::{flag, Entry};
use super::NameDetector;

// Disposition des codes (`_lexicon`) : bits 0-4 rang prénom, 5-9 rang nom, 10-11 ambiguïté.
// Code layout: bits 0-4 given-name rank, 5-9 surname rank, 10-11 ambiguity (checked at construction).
pub const GIVEN_MASK: u16 = 0x1F;
pub const SURNAME_SHIFT: u32 = 5;
pub const AMB_SHIFT: u32 = 10;
pub const RANK_MASK: u16 = GIVEN_MASK | GIVEN_MASK << SURNAME_SHIFT;
pub const AMB_NONE: u8 = 0;
pub const AMB_WORD: u8 = 1;
pub const AMB_STRONG: u8 = 2;
pub const AMB_ENTITY: u8 = 3;

#[inline]
pub fn given_rank(code: u16) -> u8 {
    (code & GIVEN_MASK) as u8
}

#[inline]
pub fn surname_rank(code: u16) -> u8 {
    ((code >> SURNAME_SHIFT) & GIVEN_MASK) as u8
}

#[inline]
pub fn ambiguity(code: u16) -> u8 {
    ((code >> AMB_SHIFT) & 3) as u8
}

/// Plutôt prénom (> 0) ou plutôt nom (< 0) ? `_given_bias` / given-name rather than surname bias.
#[inline]
pub fn given_bias(code: Option<u16>) -> i16 {
    code.map_or(0, |c| given_rank(c) as i16 - surname_rank(c) as i16)
}

/// Sortes de jetons capitalisés (`K_*`) / capitalised token kinds.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Common,
    Name,
    Unknown,
    Initial,
    Particle,
}

impl Kind {
    /// Nom connu ou inconnu (`kind in (K_NAME, K_UNKNOWN)`) / known or unknown name.
    #[inline]
    pub fn is_name(self) -> bool {
        matches!(self, Kind::Name | Kind::Unknown)
    }
}

/// `a or b or c` de Python sur des codes : premier code non nul, sinon le dernier tel quel.
/// Python's `a or b or c` over codes: first non-zero code, else the last one as is.
fn first_truthy<const N: usize>(codes: [Option<u16>; N]) -> Option<u16> {
    codes.iter().copied().find(|c| c.is_some_and(|c| c != 0)).unwrap_or(codes[N - 1])
}

fn replaced(key: &[char], from: char, to: Option<char>) -> Vec<char> {
    key.iter().filter_map(|&c| if c == from { to } else { Some(c) }).collect()
}

impl NameDetector {
    /// `Lexicon.code` : code d'un jeton replié, variantes d'apostrophe comprises.
    /// Code of a folded token, apostrophe variants included.
    pub(super) fn code(&self, key: &[char]) -> Option<u16> {
        let code = self.vocab.get(key).name();
        if code.is_some() || !key.contains(&'\'') {
            return code;
        }
        let spaced = replaced(key, '\'', Some(' '));
        let joined = replaced(key, '\'', None);
        first_truthy([self.vocab.get(&spaced).name(), self.vocab.get(&joined).name()])
    }

    /// `Lexicon.classify` : (sorte, code) d'un jeton capitalisé ; `entry` est `vocab.get(key)`.
    /// (kind, code) of a capitalised token; `entry` is `vocab.get(key)`, looked up by the caller.
    pub(super) fn classify(&self, key: &[char], original: &[char], entry: Entry) -> (Kind, u16) {
        if entry.has(flag::STOP) {
            return (Kind::Common, 0);
        }
        // La minuscule n'allonge jamais moins : un jeton plus long que tous les mots ne peut pas en être un.
        // Lowercasing never shortens: a token longer than every listed word cannot be one of them.
        if self.text_sets.accented_words.iter().any(|w| w.len() >= original.len()) {
            // « Marié le 12/06/2015 » : l'accent distingue le mot du prénom « Marie » (1.0.2, fort et essentiel).
            // The accent tells the word from the given name.
            let mut lower = Vec::with_capacity(original.len());
            self.chars.push_lower(original, &mut lower);
            if self.text_sets.accented_words.contains(&lower) {
                return (Kind::Common, 0);
            }
        }
        if entry.has(flag::PARTICLE) {
            return (Kind::Particle, entry.name().unwrap_or(0));
        }
        if key.len() > 1 && entry.has(flag::FUNCTION) {
            return (Kind::Common, 0); // « Puis », « Selon » en tête de phrase / sentence-initial function word
        }
        if self.text_sets.saint_prefixes.iter().any(|prefix| key.starts_with(prefix)) {
            return (Kind::Unknown, 0); // « Saint-Martin » : un lieu le plus souvent / usually a place
        }
        if original.first().is_some_and(|&c| "IVXLCDM".contains(c)) && patterns::ordinal(original) {
            return (Kind::Common, 0); // « Louis XIV », « François Ier »
        }
        if let Some(apostrophe) = key.iter().position(|&c| c == '\'') {
            if !key[..apostrophe].contains(&'-') {
                return self.elision(key, original, apostrophe, entry);
            }
        }
        if let Some(code) = entry.name() {
            return (Kind::Name, code);
        }
        if entry.has(flag::WORD) {
            return (Kind::Common, 0);
        }
        if key.len() == 1 {
            return (Kind::Initial, 0);
        }
        if key.contains(&'-') {
            return self.compound(key, original);
        }
        (Kind::Unknown, 0)
    }

    /// « N'Diaye », « O'Brien », « L'Europe », « Dupont's » : `Lexicon._elision`.
    fn elision(&self, key: &[char], original: &[char], apostrophe: usize, entry: Entry) -> (Kind, u16) {
        let (head, rest) = (&key[..apostrophe], &key[apostrophe + 1..]);
        let tail = original.get(apostrophe + 1..).unwrap_or_default();
        if eq(rest, "s") {
            // Possessif (« Dupont's ») / possessive.
            return self.classify(head, sub(original, 0, apostrophe), self.vocab.get(head));
        }
        if head.last() == Some(&'c') && rest.first() == Some(&'h') {
            // « Guivarc'h », « Kerc'hoz » : le c'h breton appartient au nom, jamais une élision (1.0.2, fort et
            // essentiel). The Breton c'h belongs to the name: known as a whole, else an unknown name.
            return self.code(key).map_or((Kind::Unknown, 0), |code| (Kind::Name, code));
        }
        if tail.is_empty() || !self.chars.is_upper(&tail[..1]) || eq(head, "l") {
            return (Kind::Common, 0); // « C'est », « L'Union » : élision d'un mot-outil / function-word elision
        }
        // Seule la première apostrophe change (`partition`) : f"{head} {rest}", head + rest / only the first one.
        let spaced = [head, &[' '], rest].concat();
        let joined = [head, rest].concat();
        let code = first_truthy([entry.name(), self.vocab.get(&spaced).name(), self.vocab.get(&joined).name()]);
        if let Some(code) = code {
            return (Kind::Name, code);
        }
        match self.classify(rest, tail, self.vocab.get(rest)) {
            (Kind::Name, code) => (Kind::Name, code),
            _ => (Kind::Unknown, 0),
        }
    }

    /// « Jean-Pierre », « Paris-Brest » : `Lexicon._compound`, en un seul passage sur les parties.
    /// Hyphenated compound, in one pass over the parts.
    fn compound(&self, key: &[char], original: &[char]) -> (Kind, u16) {
        let lowercase_part =
            original.split(|&c| c == '-').skip(1).any(|p| !p.is_empty() && !self.chars.is_upper(&p[..1]));
        if lowercase_part {
            return (Kind::Common, 0); // « Aix-en-Provence », « Arc-en-Ciel »
        }
        let (mut given, mut surname, mut top) = (u8::MAX, u8::MAX, 0u8);
        let (mut all_surnames, mut all_given, mut any_given, mut any_entity, mut any_plain) =
            (true, true, false, false, false);
        for part in key.split(|&c| c == '-') {
            let Some(code) = self.code(part) else {
                return (Kind::Unknown, 0);
            };
            let (g, s, amb) = (given_rank(code), surname_rank(code), ambiguity(code));
            given = given.min(g);
            surname = surname.min(s);
            top = top.max(g.max(s));
            all_surnames &= s > 0;
            all_given &= g > 0;
            any_given |= g > 0;
            any_entity |= amb == AMB_ENTITY;
            any_plain |= amb == AMB_NONE;
        }
        let mut surname = if all_surnames { surname } else { 0 };
        if given == 0 && surname == 0 {
            surname = top;
        }
        let amb = if any_entity && !all_given {
            AMB_ENTITY // « Paris-Brest », « France-Allemagne » ; mais « Heinz-Peter » est un prénom
        } else if any_plain || any_given {
            AMB_NONE // composé de prénoms ou de noms : sans ambiguïté / unambiguous compound
        } else {
            AMB_WORD
        };
        (Kind::Name, given as u16 | (surname as u16) << SURNAME_SHIFT | (amb as u16) << AMB_SHIFT)
    }
}
