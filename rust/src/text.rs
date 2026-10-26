//! Correspondance positions octets -> caractères Python ; classes de caractères de Python.
//!
//! Byte -> Python character offsets; Python's own character classes.
//! Rust travaille en octets UTF-8, Python en points de code : on convertit aux frontières.
//! Rust works on UTF-8 bytes, Python on code points: we convert at the boundaries.
//! Les classes (`str.isalnum()`…) viennent de la table unique `crate::unicode`, construite par Python : une
//! seule source de vérité. The classes come from the single table `crate::unicode`, built by Python.

pub use crate::unicode::Unicode as Classes;
pub use crate::unicode::{ALNUM, DIGIT, INVISIBLE, LETTER, LOWER};

pub struct CharIndex {
    ascii: bool,
    byte_to_char: Vec<u32>,
}

impl CharIndex {
    pub fn new(text: &str) -> Self {
        if text.is_ascii() {
            return Self { ascii: true, byte_to_char: Vec::new() };
        }
        let mut byte_to_char = vec![0u32; text.len() + 1];
        let mut index = 0u32;
        for (byte, _) in text.char_indices() {
            byte_to_char[byte] = index;
            index += 1;
        }
        byte_to_char[text.len()] = index;
        Self { ascii: false, byte_to_char }
    }

    #[inline]
    pub fn to_char(&self, byte: usize) -> usize {
        if self.ascii {
            byte
        } else {
            self.byte_to_char[byte] as usize
        }
    }
}

#[inline]
pub fn char_before(text: &str, byte: usize) -> Option<char> {
    text[..byte].chars().next_back()
}

#[inline]
pub fn char_at(text: &str, byte: usize) -> Option<char> {
    text[byte..].chars().next()
}

/// Position de l'octet du caractère suivant / byte position of the next character.
#[inline]
pub fn next_char_boundary(text: &str, byte: usize) -> usize {
    match char_at(text, byte) {
        Some(c) => byte + c.len_utf8(),
        None => byte + 1,
    }
}

/// Position de l'octet du caractère précédent (0 au début) / byte position of the previous character.
#[inline]
pub fn previous_char_boundary(text: &str, byte: usize) -> usize {
    char_before(text, byte).map_or(0, |c| byte - c.len_utf8())
}
