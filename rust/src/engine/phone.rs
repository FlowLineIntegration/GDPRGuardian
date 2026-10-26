//! Candidats des numéros internationaux : port exact de `InternationalPhoneDetector._candidate` (Python).
//!
//! International phone candidates: exact port of the Python pattern
//! `(?<![\w+.\-])(?:\+[1-9]|00[1-9])[0-9 .\-()]{6,20}[0-9](?![0-9])`, cherché comme `finditer` : la position la
//! plus à gauche, puis la plus longue que permet le retour arrière de `{6,20}`. Searched as `finditer`: the
//! leftmost position, then the longest length `{6,20}`'s backtracking allows. La validation (phonenumbers)
//! reste en Python / validation (phonenumbers) stays in Python.

use memchr::memchr2;

/// `[0-9 .\-()]`.
fn body(b: u8) -> bool {
    b.is_ascii_digit() || matches!(b, b' ' | b'.' | b'-' | b'(' | b')')
}

/// Fin (octet) de la correspondance qui commence en `start`, hors regard arrière / end byte of the match.
fn match_at(bytes: &[u8], start: usize) -> Option<usize> {
    let at = |i: usize| bytes.get(i).copied();
    let body_start = match (at(start), at(start + 1), at(start + 2)) {
        (Some(b'+'), Some(b'1'..=b'9'), _) => start + 2,
        (Some(b'0'), Some(b'0'), Some(b'1'..=b'9')) => start + 3,
        _ => return None,
    };
    // `{6,20}` glouton puis `[0-9](?![0-9])` : de la plus longue à la plus courte / longest first.
    let run = bytes.get(body_start..).map_or(0, |rest| rest.iter().take(21).take_while(|&&b| body(b)).count());
    (6..=run.min(20)).rev().find_map(|length| {
        let last = body_start + length;
        let digit = |i: usize| at(i).is_some_and(|b| b.is_ascii_digit());
        (digit(last) && !digit(last + 1)).then_some(last + 1)
    })
}

/// (début, fin) des candidats, en positions de caractères Python. `is_word` : `\w` de `re` (`str.isalnum` ou
/// « _ »), seule classe Unicode du motif, pour le regard arrière. (start, end) of the candidates, in Python
/// character positions; `is_word` is `re`'s `\w`, the pattern's only Unicode class, for the lookbehind.
pub(crate) fn candidates(text: &str, is_word: impl Fn(char) -> bool) -> Vec<(usize, usize)> {
    let bytes = text.as_bytes();
    let mut found = Vec::new();
    // Positions croissantes : caractères comptés par octets de tête / increasing positions: lead bytes counted.
    let (mut counted, mut chars) = (0, 0);
    let mut char_index = |byte: usize| {
        chars += bytes.get(counted..byte).map_or(0, |part| part.iter().filter(|&&b| (b as i8) >= -0x40).count());
        counted = byte;
        chars
    };
    let mut pos = 0;
    while let Some(offset) = bytes.get(pos..).and_then(|rest| memchr2(b'+', b'0', rest)) {
        let start = pos + offset;
        let before = text.get(..start).and_then(|head| head.chars().next_back());
        let free = before.is_none_or(|c| !(is_word(c) || matches!(c, '+' | '.' | '-')));
        match match_at(bytes, start).filter(|_| free) {
            Some(end) => {
                found.push((char_index(start), char_index(end)));
                pos = end;
            }
            None => pos = start + 1,
        }
    }
    found
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Positions en caractères / character positions.
    fn found(text: &str) -> Vec<String> {
        let found = candidates(text, |c: char| c.is_alphanumeric() || c == '_');
        found.into_iter().map(|(s, e)| text.chars().skip(s).take(e - s).collect()).collect()
    }

    #[test]
    fn leftmost_then_longest_like_finditer() {
        assert_eq!(
            found("Tél. +33 6 12 34 56 78, ou 0033 (0)6 12 34 56 78."),
            ["+33 6 12 34 56 78", "0033 (0)6 12 34 56 78"]
        );
        // Regard arrière, préfixe et longueur minimale / lookbehind, prefix and minimum length.
        assert_eq!(found("a+33612345678 x.+33612345678 +0612345678 +3361234+"), Vec::<String>::new());
        // `{6,20}` puis un chiffre : 23 caractères au plus / at most 23 characters.
        assert_eq!(found("+33 6 12 34 56 78 90 12 34 56"), ["+33 6 12 34 56 78 90 12"]);
        assert_eq!(found("00033 6 12 34 56 78"), Vec::<String>::new());
    }
}
