//! Classes de caractères et méthodes de `str`, avec la sémantique exacte de Python.
//!
//! Python character classes and `str` methods, exact semantics. Les réponses viennent de la table Unicode unique
//! du noyau (`crate::unicode`), calculée par Python avec SA base Unicode : `str.isupper()`, `\w` ou `str.split()`
//! répondent ici exactement comme dans la référence, quelle que soit la version d'Unicode de Rust.
//! Answers come from the core's single Unicode table, computed by Python with its own Unicode database, so they
//! never drift from the reference.

use std::sync::Arc;

use crate::unicode::Unicode;
pub use crate::unicode::{ALNUM, ALPHA, CAPITAL as CAP, LETTER, LOWER, SPACE, TITLE, UPPER, WORD};

/// Vue de la table partagée pour le détecteur de noms / the shared table, as the name detector reads it.
pub struct Chars {
    unicode: Arc<Unicode>,
}

impl Chars {
    pub fn new(unicode: Arc<Unicode>) -> Self {
        Self { unicode }
    }

    #[inline]
    pub fn class(&self, c: char) -> u16 {
        self.unicode.flags(c)
    }

    #[inline]
    pub fn is(&self, c: char, class: u16) -> bool {
        self.class(c) & class != 0
    }

    /// `str.isalnum()` d'un caractère / of one character.
    #[inline]
    pub fn is_alnum(&self, c: char) -> bool {
        self.is(c, ALNUM)
    }

    /// Repliement de `gdprguardian._text.fold` (longueur conservée) / `fold`, length-preserving.
    #[inline]
    pub fn fold(&self, c: char) -> char {
        self.unicode.fold(c)
    }

    pub fn push_fold(&self, s: &[char], out: &mut Vec<char>) {
        out.extend(s.iter().map(|&c| self.fold(c)));
    }

    /// `str.lower()`, correspondances complètes (« İ » donne deux caractères). Le sigma final n'est pas
    /// traité : le résultat n'est comparé qu'à des listes de mots latins, vérifiées sans sigma à l'export.
    /// Full mappings ("İ" gives two chars); final sigma is not handled: results are only compared with
    /// Latin word lists, checked to hold no sigma when exported.
    pub fn push_lower(&self, s: &[char], out: &mut Vec<char>) {
        for &c in s {
            match self.unicode.lower(c) {
                Some(mapped) => out.extend(mapped.chars()),
                None => out.push(c),
            }
        }
    }

    /// `str.isupper()` : aucune minuscule ni casse de titre, au moins une majuscule.
    /// No lowercase nor titlecase character, at least one uppercase character.
    pub fn is_upper(&self, s: &[char]) -> bool {
        let mut cased = false;
        for &c in s {
            let class = self.class(c);
            if class & (LOWER | TITLE) != 0 {
                return false;
            }
            cased |= class & UPPER != 0;
        }
        cased
    }

    /// `str.islower()` : aucune majuscule ni casse de titre, au moins une minuscule.
    /// No uppercase nor titlecase character, at least one lowercase character.
    pub fn is_lower(&self, s: &[char]) -> bool {
        let mut cased = false;
        for &c in s {
            let class = self.class(c);
            if class & (UPPER | TITLE) != 0 {
                return false;
            }
            cased |= class & LOWER != 0;
        }
        cased
    }

    #[inline]
    pub fn is_space(&self, c: char) -> bool {
        self.is(c, SPACE)
    }

    /// `str.strip()`.
    pub fn strip<'s>(&self, s: &'s [char]) -> &'s [char] {
        let start = self.leading_spaces(s);
        let end = s.iter().rposition(|&c| !self.is_space(c)).map_or(start, |i| i + 1);
        &s[start..end.max(start)]
    }

    /// `len(s) - len(s.lstrip())`.
    pub fn leading_spaces(&self, s: &[char]) -> usize {
        s.iter().take_while(|&&c| self.is_space(c)).count()
    }

    /// `len(s.split())`.
    pub fn split_count(&self, s: &[char]) -> usize {
        s.split(|&c| self.is_space(c)).filter(|piece| !piece.is_empty()).count()
    }

    /// `s.split()[-1]`, `None` si `s` n'a que des blancs / `None` when `s` is blank.
    pub fn split_last<'s>(&self, s: &'s [char]) -> Option<&'s [char]> {
        s.split(|&c| self.is_space(c)).rfind(|piece| !piece.is_empty())
    }
}

/// Blanc des motifs `[ \t]` / the `[ \t]` blank of the patterns.
#[inline]
pub fn is_blank(c: char) -> bool {
    c == ' ' || c == '\t'
}

/// Caractères consécutifs vérifiant `pred` depuis `pos`, au plus `max` (quantificateur borné).
/// Consecutive characters matching `pred` from `pos`, at most `max` (bounded quantifier).
#[inline]
pub fn run(s: &[char], pos: usize, max: usize, pred: impl Fn(char) -> bool) -> usize {
    s.get(pos..).map_or(0, |tail| tail.iter().take(max).take_while(|&&c| pred(c)).count())
}

/// `[ \t]` consécutifs, au plus `max` / consecutive blanks, at most `max`.
#[inline]
pub fn blanks(s: &[char], pos: usize, max: usize) -> usize {
    run(s, pos, max, is_blank)
}

/// `s[a:b]` de Python : bornes ramenées dans la chaîne, jamais de panique / clamped like Python slicing.
#[inline]
pub fn sub(s: &[char], a: usize, b: usize) -> &[char] {
    let a = a.min(s.len());
    &s[a..b.clamp(a, s.len())]
}

/// `s.startswith(lit, pos)`.
pub fn starts_with(s: &[char], pos: usize, lit: &str) -> bool {
    (pos..).zip(lit.chars()).all(|(i, c)| s.get(i) == Some(&c))
}

/// `s == lit`.
#[inline]
pub fn eq(s: &[char], lit: &str) -> bool {
    s.iter().copied().eq(lit.chars())
}

/// `s.find(c, lo, hi)`.
pub fn find(s: &[char], c: char, lo: usize, hi: usize) -> Option<usize> {
    let hi = hi.min(s.len());
    if lo >= hi {
        return None;
    }
    s[lo..hi].iter().position(|&x| x == c).map(|i| lo + i)
}

/// `s.rfind(c, lo, hi)`.
pub fn rfind(s: &[char], c: char, lo: usize, hi: usize) -> Option<usize> {
    let hi = hi.min(s.len());
    if lo >= hi {
        return None;
    }
    s[lo..hi].iter().rposition(|&x| x == c).map(|i| lo + i)
}

/// `s.strip(chars)`.
pub fn strip_chars<'s>(s: &'s [char], chars: &str) -> &'s [char] {
    let keep = |c: &char| !chars.contains(*c);
    let start = s.iter().position(keep).unwrap_or(s.len());
    let end = s.iter().rposition(keep).map_or(start, |i| i + 1);
    &s[start..end.max(start)]
}

/// Sous-suite contiguë / contiguous subsequence (`needle in s`).
pub fn contains(s: &[char], needle: &[char]) -> bool {
    !needle.is_empty() && s.windows(needle.len()).any(|w| w == needle)
}

/// Points de code d'une chaîne (positions Python), sans réallocation / code points, no reallocation.
pub fn code_points(s: &str) -> Vec<char> {
    let mut out = Vec::with_capacity(s.len()); // au plus un caractère par octet / at most one per byte
    if s.is_ascii() {
        out.extend(s.bytes().map(char::from));
    } else {
        out.extend(s.chars());
    }
    out
}

/// Positions d'octets UTF-8 croissantes -> positions de caractères, en un seul passage.
/// Increasing UTF-8 byte offsets -> character offsets, in a single forward pass.
pub struct CharCursor<'a> {
    text: &'a str,
    ascii: bool,
    byte: usize,
    char: usize,
}

impl<'a> CharCursor<'a> {
    pub fn new(text: &'a str) -> Self {
        Self { text, ascii: text.is_ascii(), byte: 0, char: 0 }
    }

    pub fn at(&mut self, byte: usize) -> usize {
        if self.ascii {
            return byte;
        }
        if byte < self.byte {
            (self.byte, self.char) = (0, 0);
        }
        self.char += self.text.get(self.byte..byte).map_or(0, |s| s.chars().count());
        self.byte = byte;
        self.char
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn chars() -> Chars {
        Chars::new(crate::unicode::test_unicode())
    }

    fn v(s: &str) -> Vec<char> {
        s.chars().collect()
    }

    #[test]
    fn case_predicates_follow_python() {
        let c = chars();
        assert!(c.is_upper(&v("AB1")) && !c.is_upper(&v("Ab")) && !c.is_upper(&v("12")));
        assert!(c.is_lower(&v("ab-")) && !c.is_lower(&v("aB")) && !c.is_lower(&v("")));
        assert!(c.is(' ', SPACE) && c.is_alnum('a') && !c.is_alnum('_') && c.fold('A') == 'a');
    }

    #[test]
    fn whitespace_helpers_follow_python() {
        let c = chars();
        assert_eq!(c.strip(&v("  a b \n")), v("a b").as_slice());
        assert_eq!(c.split_count(&v(" a  b ")), 2);
        assert_eq!(c.split_last(&v(" a  bc ")), Some(v("bc").as_slice()));
        assert_eq!(c.split_last(&v("   ")), None);
        assert_eq!(strip_chars(&v("*_a_*"), "*_"), v("a").as_slice());
    }

    #[test]
    fn slices_never_panic() {
        let s = v("abc");
        assert!(sub(&s, 5, 9).is_empty() && sub(&s, 2, 1).is_empty());
        assert_eq!(find(&s, 'c', 0, 99), Some(2));
        assert_eq!(rfind(&s, 'a', 1, 3), None);
    }

    #[test]
    fn cursor_counts_characters() {
        let text = "é a é";
        let mut cursor = CharCursor::new(text);
        assert_eq!(cursor.at(2), 1);
        assert_eq!(cursor.at(text.len()), 5);
    }
}
