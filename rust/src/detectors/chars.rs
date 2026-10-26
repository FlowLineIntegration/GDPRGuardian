//! Texte en points de code, comme `str` en Python / text as code points, like Python's `str`.
//!
//! Les détecteurs transcrivent du code Python indexé par caractère : une vue `Chars` sur `[char]` garde la même
//! arithmétique de positions. Une vue tronquée (`upto`) reproduit `endpos` de `re` : rien n'existe au-delà.
//! The detectors transcribe character-indexed Python code: a `Chars` view keeps the same position arithmetic.
//! A truncated view (`upto`) reproduces `re`'s `endpos`: nothing exists past its end.

use super::unicode::{CiPattern, UnicodeTable};

#[derive(Clone, Copy)]
pub struct Chars<'a> {
    pub s: &'a [char],
    pub u: &'a UnicodeTable,
}

impl<'a> Chars<'a> {
    pub fn new(s: &'a [char], u: &'a UnicodeTable) -> Self {
        Self { s, u }
    }

    #[inline]
    pub fn len(&self) -> usize {
        self.s.len()
    }

    /// Vue limitée à `[0, end)`, comme `endpos` / view limited to `[0, end)`, like `endpos`.
    #[inline]
    pub fn upto(&self, end: usize) -> Self {
        Self { s: &self.s[..end.min(self.s.len())], u: self.u }
    }

    #[inline]
    pub fn get(&self, i: usize) -> Option<char> {
        self.s.get(i).copied()
    }

    #[inline]
    pub fn is(&self, i: usize, c: char) -> bool {
        self.s.get(i) == Some(&c)
    }

    #[inline]
    pub fn test(&self, i: usize, predicate: impl Fn(char) -> bool) -> bool {
        self.s.get(i).is_some_and(|&c| predicate(c))
    }

    /// `[ \t]`.
    #[inline]
    pub fn blank(&self, i: usize) -> bool {
        matches!(self.s.get(i), Some(' ' | '\t'))
    }

    /// `[0-9]`.
    #[inline]
    pub fn digit(&self, i: usize) -> bool {
        self.s.get(i).is_some_and(char::is_ascii_digit)
    }

    /// `\w`.
    #[inline]
    pub fn word(&self, i: usize) -> bool {
        self.test(i, |c| self.u.is_word(c))
    }

    /// `str.isalnum()`.
    #[inline]
    pub fn alnum(&self, i: usize) -> bool {
        self.test(i, |c| self.u.is_alnum(c))
    }

    /// `[^\W\d_]`.
    #[inline]
    pub fn letter(&self, i: usize) -> bool {
        self.test(i, |c| self.u.is_letter(c))
    }

    /// `\s`, `str.isspace()`.
    #[inline]
    pub fn space(&self, i: usize) -> bool {
        self.test(i, |c| self.u.is_space(c))
    }

    /// Nombre de caractères consécutifs vérifiant `predicate` depuis `i`, au plus `max`.
    /// Number of consecutive characters matching `predicate` from `i`, at most `max`.
    #[inline]
    pub fn run(&self, i: usize, max: usize, predicate: impl Fn(char) -> bool) -> usize {
        self.s.get(i..).map_or(0, |rest| rest.iter().take(max).take_while(|&&c| predicate(c)).count())
    }

    /// `[ \t]{0,max}` glouton / greedy.
    #[inline]
    pub fn blanks(&self, i: usize, max: usize) -> usize {
        self.run(i, max, |c| c == ' ' || c == '\t')
    }

    /// `[0-9]{0,max}` glouton / greedy.
    #[inline]
    pub fn digits(&self, i: usize, max: usize) -> usize {
        self.run(i, max, |c| c.is_ascii_digit())
    }

    /// Littéral sensible à la casse en `i` / case-sensitive literal at `i`.
    #[inline]
    pub fn literal(&self, i: usize, literal: &str) -> bool {
        (i..).zip(literal.chars()).all(|(k, c)| self.is(k, c))
    }

    /// Motif `(?i:…)` en `i`, sémantique de `re` / `(?i:…)` pattern at `i`, `re` semantics.
    #[inline]
    pub fn literal_ci(&self, i: usize, pattern: &CiPattern) -> bool {
        pattern.matches(self.s, i)
    }

    /// Texte de `[start, end)` / text of `[start, end)`.
    pub fn string(&self, start: usize, end: usize) -> String {
        self.s[start..end].iter().collect()
    }
}

/// Positions en caractères d'offsets d'octets croissants, en un seul passage (O(n) au total).
/// Character offsets of increasing byte offsets, in a single pass (O(n) overall).
pub struct CharCursor<'a> {
    bytes: &'a [u8],
    byte: usize,
    chars: usize,
}

impl<'a> CharCursor<'a> {
    pub fn new(text: &'a str) -> Self {
        Self { bytes: text.as_bytes(), byte: 0, chars: 0 }
    }

    /// Position en caractères de l'octet `byte` (frontière de caractère) ; un recul repart du début.
    /// Character offset of byte `byte` (a char boundary); moving backwards restarts from the beginning.
    pub fn char_index(&mut self, byte: usize) -> usize {
        if byte < self.byte {
            self.byte = 0;
            self.chars = 0;
        }
        let end = byte.min(self.bytes.len());
        // Un caractère commence par tout octet qui n'est pas de continuation / chars start at non-continuation bytes.
        self.chars += self.bytes[self.byte..end].iter().filter(|&&b| (b as i8) >= -0x40).count();
        self.byte = end;
        self.chars
    }
}

/// Texte décodé en points de code ; les suites ASCII, majoritaires, sont copiées d'un bloc.
/// Text decoded into code points; ASCII runs, the bulk of the text, are copied in one go.
pub fn decode(text: &str) -> Vec<char> {
    let bytes = text.as_bytes();
    let mut chars = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        let ascii = bytes[i..].iter().take_while(|b| b.is_ascii()).count();
        chars.extend(bytes[i..i + ascii].iter().map(|&b| char::from(b)));
        i += ascii;
        if let Some(c) = text[i..].chars().next() {
            chars.push(c);
            i += c.len_utf8();
        }
    }
    chars
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cursor_counts_code_points() {
        let text = "aé😀b";
        let mut cursor = CharCursor::new(text);
        assert_eq!(cursor.char_index(1), 1);
        assert_eq!(cursor.char_index(3), 2);
        assert_eq!(cursor.char_index(7), 3);
        assert_eq!(cursor.char_index(8), 4);
        assert_eq!(cursor.char_index(3), 2);
    }

    #[test]
    fn decode_matches_chars() {
        for text in ["", "abc", "é", "aé😀b", "Zoé Ñúñez, 12 rue\u{301}"] {
            assert_eq!(decode(text), text.chars().collect::<Vec<_>>());
        }
    }
}
