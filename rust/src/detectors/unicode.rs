//! Classes de caractères de l'interpréteur Python / the Python interpreter's character classes.
//!
//! `\w`, `\d`, `\s`, `str.isupper()`… et les équivalents de `re.IGNORECASE` suivent la version Unicode de
//! l'interpréteur, pas celle de Rust : les détecteurs lisent la table unique du noyau (`crate::unicode`),
//! construite par Python une fois par processus. These classes and the `re.IGNORECASE` equivalents follow the
//! interpreter's Unicode version, not Rust's: the detectors read the core's single table, built by Python once.

pub use crate::unicode::Unicode as UnicodeTable;

/// Motif littéral insensible à la casse, résolu à la construction : pour chaque position, les caractères acceptés
/// (« b[aâ]t » -> {b, B}, {a, A, â, Â}, {t, T}). Case-insensitive literal pattern, resolved at construction: the
/// accepted characters of each position.
pub struct CiPattern(Box<[Box<[char]>]>);

impl CiPattern {
    /// Syntaxe : lettres, et classes entre crochets (« r[ée]s. ») / letters, and bracketed classes.
    pub fn new(pattern: &str, table: &UnicodeTable) -> Self {
        let mut positions: Vec<Box<[char]>> = Vec::new();
        let mut chars = pattern.chars();
        while let Some(c) = chars.next() {
            let letters: Vec<char> =
                if c == '[' { chars.by_ref().take_while(|&x| x != ']').collect() } else { vec![c] };
            let mut accepted: Vec<char> = letters.iter().flat_map(|&letter| table.equivalents(letter)).collect();
            accepted.sort_unstable();
            accepted.dedup();
            positions.push(accepted.into_boxed_slice());
        }
        Self(positions.into_boxed_slice())
    }

    /// Longueur en caractères / length in characters.
    pub fn len(&self) -> usize {
        self.0.len()
    }

    /// Caractères acceptés en tête / characters accepted first.
    pub fn first(&self) -> &[char] {
        self.0.first().map_or(&[], |accepted| accepted)
    }

    /// Le motif occupe-t-il `text[at..]` ? / does the pattern match at `at`?
    #[inline]
    pub fn matches(&self, text: &[char], at: usize) -> bool {
        text.get(at..at + self.0.len())
            .is_some_and(|window| window.iter().zip(&self.0).all(|(c, accepted)| accepted.contains(c)))
    }
}

/// Petit ensemble de caractères, un test de bit pour l'ASCII / small character set, one bit test for ASCII.
pub struct CharSet {
    ascii: u128,
    other: Box<[char]>,
}

impl CharSet {
    pub fn new(chars: impl IntoIterator<Item = char>) -> Self {
        let (mut ascii, mut other) = (0u128, Vec::new());
        for c in chars {
            if c.is_ascii() {
                ascii |= 1 << c as u32;
            } else {
                other.push(c);
            }
        }
        Self { ascii, other: other.into_boxed_slice() }
    }

    #[inline]
    pub fn contains(&self, c: char) -> bool {
        if c.is_ascii() {
            self.ascii >> c as u32 & 1 == 1
        } else {
            self.other.contains(&c)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::unicode::test_unicode;

    #[test]
    fn classes_come_from_the_shared_table() {
        let table = test_unicode();
        assert!(table.is_word('_') && !table.is_alnum('_') && table.is_alnum('a'));
        assert!(table.is_letter('a') && !table.is_letter('7') && !table.is_letter('_'));
        assert!(!table.is_word('\u{10FFFF}'));
    }

    #[test]
    fn case_insensitive_patterns() {
        let table = test_unicode();
        let pattern = CiPattern::new("r[ée]s.", &table);
        assert_eq!(pattern.len(), 4);
        let text: Vec<char> = "RÉS.".chars().collect();
        assert!(pattern.matches(&text, 0));
        assert!(!pattern.matches(&text, 1));
        assert!(!CiPattern::new("cedex", &table).matches(&text, 0));
        assert!(table.case_insensitive_eq('e', 'E') && !table.case_insensitive_eq('.', ','));
        let set = CharSet::new(['B', 'é', '\u{7f}']);
        assert!(set.contains('B') && set.contains('é') && set.contains('\u{7f}') && !set.contains('b'));
    }
}
