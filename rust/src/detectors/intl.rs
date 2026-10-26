//! Détecteurs internationaux : transcription de `detectors/intl.py` (e-mail, IBAN, MRZ).
//!
//! Leurs ancres sont ASCII (« @ », « FR76 », « < ») : l'analyse se fait sur les octets UTF-8, les positions
//! sont converties en caractères Python à la sortie. Their anchors are ASCII: the scan runs over UTF-8 bytes and
//! positions are converted to Python characters on output.

use std::collections::HashMap;
use std::sync::Arc;

use super::chars::CharCursor;
use super::unicode::UnicodeTable;
use crate::validators;

/// Caractère qui commence à l'octet `byte` / character starting at byte `byte`.
fn char_at(text: &str, byte: usize) -> Option<char> {
    text.get(byte..)?.chars().next()
}

// --- E-mail --------------------------------------------------------------------------------------------------

/// Taille de la fenêtre de la partie locale / local-part window.
const LOCAL_WINDOW: usize = 64;

pub struct EmailDetector {
    table: Arc<UnicodeTable>,
}

impl EmailDetector {
    pub fn new(table: Arc<UnicodeTable>) -> Self {
        Self { table }
    }

    /// `EmailDetector._candidates` : (début, fin). La validation et la valeur restent à `email` (Python) : le
    /// `str.lower` de l'interpréteur et le `to_lowercase` de Rust suivent des versions d'Unicode différentes
    /// (sigma final devant « ʕ »). Validation and value stay with Python's `email`: the interpreter's
    /// `str.lower` and Rust's `to_lowercase` follow different Unicode versions (final sigma before "ʕ").
    pub fn detect(&self, text: &str) -> Vec<(usize, usize)> {
        let mut found = Vec::new();
        let mut cursor = CharCursor::new(text);
        for (at, _) in text.match_indices('@') {
            let at_char = cursor.char_index(at);
            if let Some(span) = self.around(text, at, at_char) {
                found.push(span);
            }
        }
        found
    }

    fn around(&self, text: &str, at: usize, at_char: usize) -> Option<(usize, usize)> {
        // `_local.search(text, at - 64, at)` : `[\w.%+\-]{1,64}$`, `$` en `at` ou avant un « \n » final.
        // `$` at `at` or before a final newline.
        let window: Vec<(usize, char)> = {
            let mut chars: Vec<(usize, char)> = text[..at].char_indices().rev().take(LOCAL_WINDOW).collect();
            chars.reverse();
            chars
        };
        let window_start = at_char - window.len();
        let local_class = |c: char| self.table.is_word(c) || matches!(c, '.' | '%' | '+' | '-');
        let local_end = if window.last().is_some_and(|&(_, c)| c == '\n') { window.len() - 1 } else { window.len() };
        let mut first = local_end;
        while first > 0 && local_class(window[first - 1].1) {
            first -= 1;
        }
        if first == local_end {
            return None;
        }
        let domain_end = self.domain_end(text, at + 1)?;
        while first < window.len() && window[first].1 == '.' {
            first += 1;
        }
        let cut = first == 0
            && window_start > 0
            && text[..window[0].0]
                .chars()
                .next_back()
                .is_some_and(|c| self.table.is_alnum(c) || matches!(c, '_' | '.' | '%' | '+' | '-'));
        if cut {
            return None;
        }
        let end_char = at_char + 1 + text[at + 1..domain_end].chars().count();
        Some((window_start + first, end_char))
    }

    /// `_domain.match(text, at + 1)` : `(?:[\w\-]{1,63}\.){1,8}[A-Za-z]{2,24}(?![\w\-])` -> fin en octets.
    /// Les étiquettes vont jusqu'au point ; on essaie le domaine de premier niveau après la dernière, puis
    /// les précédentes (retour arrière de `{1,8}`). Labels run to the dot; the top-level domain is tried
    /// after the last one, then earlier ones (backtracking of `{1,8}`).
    fn domain_end(&self, text: &str, from: usize) -> Option<usize> {
        let label_char = |c: char| self.table.is_word(c) || c == '-';
        let mut after_dots = Vec::with_capacity(8);
        let mut p = from;
        while after_dots.len() < 8 {
            let (mut count, mut q) = (0, p);
            for c in text[p..].chars().take(64) {
                if !label_char(c) {
                    break;
                }
                count += 1;
                q += c.len_utf8();
            }
            if count == 0 || count > 63 || text.as_bytes().get(q) != Some(&b'.') {
                break;
            }
            p = q + 1;
            after_dots.push(p);
        }
        after_dots.iter().rev().find_map(|&q| {
            let letters = text.as_bytes()[q..].iter().take(25).take_while(|b| b.is_ascii_alphabetic()).count();
            let end = q + letters;
            ((2..=24).contains(&letters) && !char_at(text, end).is_some_and(label_char)).then_some(end)
        })
    }
}

// --- IBAN ----------------------------------------------------------------------------------------------------

pub struct IbanDetector {
    table: Arc<UnicodeTable>,
    lengths: HashMap<String, usize>,
}

/// Candidat IBAN : valeur si la clé est juste, sinon `None` ; mise en page « par quatre ».
/// IBAN candidate: value when the key is right, else `None`; "printed in fours" layout.
pub type IbanCandidate = (usize, usize, Option<String>, bool);

impl IbanDetector {
    pub fn new(table: Arc<UnicodeTable>, lengths: HashMap<String, usize>) -> Self {
        Self { table, lengths }
    }

    /// `IbanDetector.detect` sans le contexte : le mot-clé proche est vérifié par Python (`ctx.near`).
    /// Without the context: a nearby keyword is checked by Python.
    pub fn detect(&self, text: &str) -> Vec<IbanCandidate> {
        let b = text.as_bytes();
        let mut found = Vec::new();
        let mut cursor = CharCursor::new(text);
        let mut s = 0;
        // L'ancre commence par une majuscule ASCII : on saute de l'une à l'autre / the anchor starts with a capital.
        let next_capital = |from: usize| b.get(from..)?.iter().position(u8::is_ascii_uppercase).map(|i| from + i);
        while let Some(start) = next_capital(s) {
            let Some(anchor_end) = iban_anchor(b, start) else {
                s = start + 1;
                continue;
            };
            s = anchor_end;
            let country = &text[start..start + 2];
            let Some(&expected) = self.lengths.get(country) else {
                continue;
            };
            let check = &text[anchor_end - 2..anchor_end];
            // Longueur de pays sous 4 : `len(chars) != needed` toujours vrai en Python, candidat écarté ; capacité
            // bornée par le texte. Country length under 4: always dropped by Python; capacity bounded by the text.
            let Some(needed) = expected.checked_sub(4) else {
                continue;
            };
            let mut bban = String::with_capacity(needed.min(b.len() - anchor_end));
            let (mut pos, mut end) = (anchor_end, anchor_end);
            while bban.len() < needed && pos < b.len() {
                let c = b[pos];
                if c.is_ascii_alphanumeric() {
                    bban.push(c.to_ascii_uppercase() as char);
                    pos += 1;
                    end = pos;
                } else if (c == b' ' || c == b'-')
                    && (bban.is_empty() || char_at(text, pos + 1).is_some_and(|n| self.table.is_alnum(n)))
                {
                    pos += 1;
                } else {
                    break;
                }
            }
            if bban.len() != needed || char_at(text, end).is_some_and(|n| self.table.is_alnum(n)) {
                continue;
            }
            let start_char = cursor.char_index(start);
            let end_char = start_char + (end - start); // caractères ASCII / ASCII characters
            if validators::mod97_10_ok(&format!("{bban}{country}{check}")) {
                found.push((start_char, end_char, Some(format!("{country}{check}{bban}")), false));
            } else {
                found.push((start_char, end_char, None, printed_in_fours(&text[start..end])));
            }
        }
        found
    }
}

/// `(?<![A-Za-z0-9])([A-Z]{2}) ?([0-9]{2})(?=[ \-]?[A-Za-z0-9])` en `s` -> fin de l'ancre / anchor end.
fn iban_anchor(b: &[u8], s: usize) -> Option<usize> {
    let alnum = |i: usize| b.get(i).is_some_and(u8::is_ascii_alphanumeric);
    let digit = |i: usize| b.get(i).is_some_and(u8::is_ascii_digit);
    if (s > 0 && alnum(s - 1)) || !(b.get(s)?.is_ascii_uppercase() && b.get(s + 1)?.is_ascii_uppercase()) {
        return None;
    }
    let mut i = s + 2;
    if b.get(i) == Some(&b' ') && digit(i + 1) && digit(i + 2) {
        i += 1;
    }
    if !(digit(i) && digit(i + 1)) {
        return None;
    }
    let end = i + 2;
    (alnum(end) || (matches!(b.get(end), Some(b' ' | b'-')) && alnum(end + 1))).then_some(end)
}

/// `_printed_in_fours` : « FR76 3000 6000 … » / printed layout.
fn printed_in_fours(raw: &str) -> bool {
    let groups: Vec<&str> = raw.split(' ').collect();
    let Some((last, head)) = groups.split_last() else {
        return false;
    };
    groups.len() >= 4 && head.iter().all(|g| g.chars().count() == 4) && (1..=4).contains(&last.chars().count())
}

// --- MRZ -----------------------------------------------------------------------------------------------------

/// `MrzDetector.detect` : (début, fin, score) des bandes MRZ / MRZ bands.
pub fn mrz(text: &str) -> Vec<(usize, usize, f64)> {
    let b = text.as_bytes();
    let mut found = Vec::new();
    let mut cursor = CharCursor::new(text);
    let mut line = Some(0);
    while let Some(s) = line {
        // `(?m)^` : seulement en début de ligne / only at line starts.
        let resume = match mrz_block(b, s) {
            Some(end) => {
                let block = &b[s..end];
                let indent = block.iter().take_while(|&&c| c == b' ' || c == b'\t').count();
                if block.iter().filter(|&&c| c == b'<').count() >= 4 && b"PIACV".contains(&block[indent]) {
                    let score = (0.9 + 0.08 * mrz_check_ratio(block)).min(1.0);
                    let start_char = cursor.char_index(s);
                    found.push((start_char + indent, start_char + block.len(), score));
                }
                end
            }
            None => s,
        };
        line = b[resume..].iter().position(|&c| c == b'\n').map(|i| resume + i + 1);
    }
    found
}

/// `(?m)^[ \t]*[A-Z0-9<]{28,46}[ \t]*\r?\n[ \t]*[A-Z0-9<]{28,46}(?:[ \t]*\r?\n[ \t]*[A-Z0-9<]{28,46})?` en `s`.
/// Une première ligne de plus de 46 caractères échoue ; les suivantes sont coupées à 46.
/// A first line over 46 characters fails; the following ones are cut at 46.
fn mrz_block(b: &[u8], s: usize) -> Option<usize> {
    let run =
        |i: usize, class: fn(u8) -> bool| b.get(i..).map_or(0, |rest| rest.iter().take_while(|&&c| class(c)).count());
    let blank = |c: u8| c == b' ' || c == b'\t';
    let mrz = |c: u8| c.is_ascii_uppercase() || c.is_ascii_digit() || c == b'<';
    let newline = |i: usize| -> Option<usize> {
        let mut j = i + run(i, blank);
        if b.get(j) == Some(&b'\r') {
            j += 1;
        }
        (b.get(j) == Some(&b'\n')).then_some(j + 1)
    };
    let mut i = s + run(s, blank);
    let first = run(i, mrz);
    if !(28..=46).contains(&first) {
        return None;
    }
    i = newline(i + first)?;
    i += run(i, blank);
    let second = run(i, mrz);
    if second < 28 {
        return None;
    }
    let end = i + second.min(46);
    if let Some(j) = newline(end) {
        let j = j + run(j, blank);
        let third = run(j, mrz);
        if third >= 28 {
            return Some(j + third.min(46));
        }
    }
    Some(end)
}

/// `_mrz_check_ratio` : part des clés ICAO justes de la seconde ligne (bande à deux lignes, TD3).
/// Share of correct ICAO check digits on the second line (two-line band).
fn mrz_check_ratio(block: &[u8]) -> f64 {
    let lines: Vec<&[u8]> = block.split(|&c| c == b'\n').collect();
    if lines.len() != 2 {
        return 0.0;
    }
    let line = lines[1].trim_ascii();
    if line.len() < 28 {
        return 0.0;
    }
    let fields = [(&line[0..9], line[9]), (&line[13..19], line[19]), (&line[21..27], line[27])];
    let good = fields
        .iter()
        .filter(|(value, check)| check.is_ascii_digit() && icao_check_digit(value) == check - b'0')
        .count();
    good as f64 / fields.len() as f64
}

/// ICAO 9303 : poids 7-3-1, A=10..Z=35, « < » = 0 / weights 7-3-1.
fn icao_check_digit(field: &[u8]) -> u8 {
    const WEIGHTS: [u32; 3] = [7, 3, 1];
    let total: u32 = field
        .iter()
        .enumerate()
        .map(|(i, &c)| {
            let value = match c {
                b'0'..=b'9' => u32::from(c - b'0'),
                b'A'..=b'Z' => u32::from(c - b'A') + 10,
                _ => 0,
            };
            value * WEIGHTS[i % 3]
        })
        .sum();
    (total % 10) as u8
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mrz_blocks() {
        let line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<";
        let line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10";
        let text = format!("x\n  {line1}\r\n{line2}\nfin");
        let found = mrz(&text);
        assert_eq!(found.len(), 1);
        let (start, end, score) = found[0];
        assert_eq!((start, end), (4, 4 + line1.len() + 2 + line2.len()));
        assert!((score - 0.98).abs() < 1e-12);
        assert!(mrz(&format!("{line1}{line1}\n{line2}")).is_empty());
    }

    #[test]
    fn iban_layout() {
        assert!(printed_in_fours("FR76 3000 6000 0112 3456 7890 189"));
        assert!(!printed_in_fours("FR7630006000011234567890189"));
        assert_eq!(iban_anchor(b"FR76 3000", 0), Some(4));
        assert_eq!(iban_anchor(b"xFR76 3000", 1), None);
    }
}
