//! Dates de naissance liées à un NIR : transcription de `detectors/fr.py` (`NirBirthDateDetector`).
//!
//! Python fournit les couples (année, mois) des NIR déjà validés du document ; Rust cherche les dates
//! numériques et en toutes lettres qui leur correspondent. Python provides the (year, month) pairs of the
//! document's validated NIRs; Rust finds the numeric and written dates matching them.

use std::collections::HashSet;
use std::sync::Arc;

use super::chars::CharCursor;
use super::unicode::UnicodeTable;
use crate::validators::{self, ValidatorFn};

pub struct BirthDateDetector {
    table: Arc<UnicodeTable>,
    /// Mois en toutes lettres (texte replié) et leur numéro, dans l'ordre du motif / month names and numbers.
    months: Vec<(String, String)>,
    calendar_date: ValidatorFn,
}

/// Dates trouvées : numériques (début, fin, valeur ISO) et en lettres (début, fin) / found dates.
pub type BirthDates = (Vec<(usize, usize, String)>, Vec<(usize, usize)>);

impl BirthDateDetector {
    pub fn new(table: Arc<UnicodeTable>, months: Vec<(String, String)>) -> Result<Self, String> {
        let calendar_date =
            validators::lookup("intl.calendar_date").ok_or("validateur intl.calendar_date absent / missing")?;
        Ok(Self { table, months, calendar_date })
    }

    /// Les deux motifs commencent par `(?<![0-9])` puis un chiffre : seuls les débuts de suites de chiffres
    /// peuvent réussir, on saute de l'une à l'autre. Both patterns start with `(?<![0-9])` and a digit: only
    /// digit-run starts can match, so the scan jumps from one to the next.
    pub fn detect(&self, text: &str, folded: &str, births: &HashSet<(String, String)>) -> BirthDates {
        let mut numeric = Vec::new();
        let b = text.as_bytes();
        let mut cursor = CharCursor::new(text);
        let mut s = 0;
        while let Some(start) = next_run(b, s) {
            let Some(date) = numeric_date(b, start) else {
                s = run_end(b, start);
                continue;
            };
            s = date.end;
            let (year, month) = (ascii(&b[date.year.0..date.year.1]), &b[date.month.0..date.month.1]);
            // `zfill(2)` du mois / the month's `zfill(2)`.
            let month = if month.len() == 1 { format!("0{}", month[0] as char) } else { ascii(month) };
            if !births.contains(&(year, month)) {
                continue;
            }
            if let Some(value) = (self.calendar_date)(&text[start..date.end]) {
                let first = cursor.char_index(start);
                numeric.push((first, first + (date.end - start), value));
            }
        }
        let mut words = Vec::new();
        let b = folded.as_bytes();
        let mut cursor = CharCursor::new(folded);
        let mut s = 0;
        while let Some(start) = next_run(b, s) {
            let Some((end, year, month)) = self.written_date(folded, start) else {
                s = run_end(b, start);
                continue;
            };
            s = end;
            if births.contains(&(year, month.to_string())) {
                words.push((cursor.char_index(start), cursor.char_index(end)));
            }
        }
        (numeric, words)
    }

    /// `_words` sur le texte replié : `(?<![0-9])(?:1er|0?[1-9]|[12][0-9]|3[01])\s{1,3}(janvier|…|decembre)
    /// \s{1,3}(?:18|19|20)([0-9]{2})(?![0-9])` en `s` -> (fin, année, numéro du mois) / (end, year, month).
    fn written_date(&self, f: &str, s: usize) -> Option<(usize, String, &str)> {
        let b = f.as_bytes();
        if s > 0 && b[s - 1].is_ascii_digit() {
            return None;
        }
        let first = b[s..].starts_with(b"1er").then_some(s + 3);
        for day_end in first.into_iter().chain(day_ends(b, s)) {
            let i = day_end + self.spaces(f, day_end);
            if i == day_end {
                continue;
            }
            for (name, number) in &self.months {
                if !b[i..].starts_with(name.as_bytes()) {
                    continue;
                }
                let j = i + name.len();
                let k = j + self.spaces(f, j);
                let digit = |at: usize| b.get(at).is_some_and(u8::is_ascii_digit);
                let century = b.get(k..k + 2).is_some_and(|c| matches!(c, b"18" | b"19" | b"20"));
                if k > j && century && digit(k + 2) && digit(k + 3) && !digit(k + 4) {
                    return Some((k + 4, ascii(&b[k + 2..k + 4]), number));
                }
            }
        }
        None
    }

    /// `\s{1,3}` glouton, en octets (seule la plus longue suite peut réussir) / greedy, in bytes.
    fn spaces(&self, f: &str, at: usize) -> usize {
        f[at..].chars().take(3).take_while(|&c| self.table.is_space(c)).map(char::len_utf8).sum()
    }
}

fn ascii(bytes: &[u8]) -> String {
    bytes.iter().map(|&b| b as char).collect()
}

/// Prochain début de suite de chiffres à partir de `s` (qui n'est jamais au milieu d'une suite).
/// Next digit-run start from `s` (never inside a run).
fn next_run(b: &[u8], s: usize) -> Option<usize> {
    b.get(s..)?.iter().position(u8::is_ascii_digit).map(|offset| s + offset)
}

fn run_end(b: &[u8], start: usize) -> usize {
    start + b[start..].iter().take_while(|c| c.is_ascii_digit()).count()
}

fn byte(b: &[u8], i: usize) -> u8 {
    b.get(i).copied().unwrap_or(0)
}

fn nonzero(c: u8) -> bool {
    (b'1'..=b'9').contains(&c)
}

/// Fins possibles de `0?[1-9]|[12][0-9]|3[01]` en `s`, dans l'ordre du retour arrière / backtracking order.
fn day_ends(b: &[u8], s: usize) -> impl Iterator<Item = usize> {
    let (c0, c1) = (byte(b, s), byte(b, s + 1));
    [
        (c0 == b'0' && nonzero(c1)).then_some(s + 2),
        nonzero(c0).then_some(s + 1),
        (matches!(c0, b'1' | b'2') && c1.is_ascii_digit()).then_some(s + 2),
        (c0 == b'3' && matches!(c1, b'0' | b'1')).then_some(s + 2),
    ]
    .into_iter()
    .flatten()
}

/// Fins possibles de `0?[1-9]|1[0-2]` en `s`, dans l'ordre du retour arrière / backtracking order.
fn month_ends(b: &[u8], s: usize) -> impl Iterator<Item = usize> {
    let (c0, c1) = (byte(b, s), byte(b, s + 1));
    [
        (c0 == b'0' && nonzero(c1)).then_some(s + 2),
        nonzero(c0).then_some(s + 1),
        (c0 == b'1' && matches!(c1, b'0'..=b'2')).then_some(s + 2),
    ]
    .into_iter()
    .flatten()
}

struct NumericDate {
    end: usize,
    month: (usize, usize),
    year: (usize, usize),
}

/// `_numeric` en `s` : `(?<![0-9])(?:0?[1-9]|[12][0-9]|3[01])([/.\-])(0?[1-9]|1[0-2])\1(?:19|20)([0-9]{2})
/// (?![0-9])`, premier chemin du retour arrière / first backtracking path.
fn numeric_date(b: &[u8], s: usize) -> Option<NumericDate> {
    if s > 0 && b[s - 1].is_ascii_digit() {
        return None;
    }
    for day_end in day_ends(b, s) {
        let separator = byte(b, day_end);
        if !matches!(separator, b'/' | b'.' | b'-') {
            continue;
        }
        let month = day_end + 1;
        for month_end in month_ends(b, month) {
            let year = month_end + 1;
            if byte(b, month_end) == separator
                && matches!((byte(b, year), byte(b, year + 1)), (b'1', b'9') | (b'2', b'0'))
                && byte(b, year + 2).is_ascii_digit()
                && byte(b, year + 3).is_ascii_digit()
                && !byte(b, year + 4).is_ascii_digit()
            {
                return Some(NumericDate { end: year + 4, month: (month, month_end), year: (year + 2, year + 4) });
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn numeric_dates_follow_backtracking() {
        let found = |text: &str| numeric_date(text.as_bytes(), 0).map(|d| (d.end, d.month, d.year));
        assert_eq!(found("11/1/2019"), Some((9, (3, 4), (7, 9))));
        assert_eq!(found("03/03/1985"), Some((10, (3, 5), (8, 10))));
        assert_eq!(found("1/10/2020"), Some((9, (2, 4), (7, 9))));
        assert_eq!(found("03/03-1985"), None);
        assert_eq!(found("03/03/19851"), None);
    }
}
