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

/// `_text._tab_row` sur des caractères : la ligne de `pos` est une ligne (en-tête compris) d'un tableau TSV que
/// `delimited_tables` reconnaît ; une prose dont les espaces sont des tabulations n'en est pas un (revue du 26/10).
/// On characters: the line of `pos` is a row (header included) of a TSV table `delimited_tables` finds.
pub fn tab_row_chars(text: &[char], pos: usize) -> bool {
    let pos = pos.min(text.len());
    let tabs_in = |a: usize, b: usize| text.get(a..b).map_or(0, |part| part.iter().filter(|&&c| c == '\t').count());
    let start = text[..pos].iter().rposition(|&c| c == '\n').map_or(0, |i| i + 1);
    let end = text[pos..].iter().position(|&c| c == '\n').map_or(text.len(), |i| pos + i);
    let tabs = tabs_in(start, end);
    if tabs < 2 {
        return false;
    }
    // Condition nécessaire, bon marché : une ligne voisine porte autant de tabulations / cheap necessary condition.
    let previous_same = start > 0 && {
        let previous = text[..start - 1].iter().rposition(|&c| c == '\n').map_or(0, |i| i + 1);
        tabs_in(previous, start - 1) == tabs
    };
    let next_same = !previous_same && end < text.len() && {
        let after = text[end + 1..].iter().position(|&c| c == '\n').map_or(text.len(), |i| end + 1 + i);
        tabs_in(end + 1, after) == tabs
    };
    if !previous_same && !next_same {
        return false;
    }
    // Lignes voisines de `pos`, comparées à la copie (contrôle local bon marché) / neighbouring lines, checked.
    let lo = if start > 0 { text[..start - 1].iter().rposition(|&c| c == '\n').map_or(0, |i| i + 1) } else { 0 };
    let hi = if end < text.len() {
        text[end + 1..].iter().position(|&c| c == '\n').map_or(text.len(), |i| end + 1 + i)
    } else {
        end
    };
    TAB_ROWS.with(|cell| {
        let mut cache = cell.borrow_mut();
        let hit = cache.as_ref().is_some_and(|c| {
            c.ptr == text.as_ptr() as usize && c.copy.len() == text.len() && c.copy[lo..hi] == text[lo..hi]
        });
        if !hit {
            *cache = Some(TabRows::new(text, tab_table_rows(text)));
        }
        cache.as_ref().is_some_and(|c| c.rows.binary_search(&start).is_ok())
    })
}

/// Lignes des tableaux TSV du dernier texte vu (`delimited_tables` ou `tab_row_chars`) : adresse de la tranche, copie,
/// débuts de ligne triés. Le détecteur de noms appelle `delimited_tables` sur son texte (`tables.rs: csv_rows`) avant
/// d'assembler les jetons : chaque appel de `tab_row_chars` retrouve donc ses lignes sans relire tout le texte (coût
/// constant, plus de comparaison du texte entier à chaque jonction). Une autre tranche, ou des lignes voisines qui
/// diffèrent de la copie, refont le calcul. Rows of the last text seen: slice address, copy, sorted line starts. The
/// name detector calls `delimited_tables` on its text before joining tokens, so each `tab_row_chars` call finds its
/// rows without re-reading the whole text; another slice, or neighbouring lines that differ, recompute.
struct TabRows {
    ptr: usize,
    copy: Vec<char>,
    rows: Vec<usize>,
}

impl TabRows {
    fn new(text: &[char], rows: Vec<usize>) -> Self {
        Self { ptr: text.as_ptr() as usize, copy: text.to_vec(), rows }
    }
}

thread_local! {
    static TAB_ROWS: std::cell::RefCell<Option<TabRows>> = const { std::cell::RefCell::new(None) };
}

/// Lignes TSV d'un balayage de `table_scan`, triées / sorted TSV line starts of a `table_scan` result.
fn tab_rows_of(tables: &[(char, Vec<(usize, usize)>)]) -> Vec<usize> {
    let mut rows: Vec<usize> = tables
        .iter()
        .filter(|(delimiter, _)| *delimiter == '\t')
        .flat_map(|(_, lines)| lines.iter().map(|&(start, _)| start))
        .collect();
    rows.sort_unstable();
    rows
}

/// `str.isspace()` de Python : `char::is_whitespace` plus U+001C à U+001F / Python's `str.isspace()`.
fn py_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

/// `_text._tab_table_rows` : débuts (triés) des lignes des tableaux TSV / sorted line starts of the TSV tables.
pub fn tab_table_rows(text: &[char]) -> Vec<usize> {
    tab_rows_of(&table_scan(text, &py_space))
}

/// `_text.CSV_DELIMITERS` : « ; », tabulation, « , » (la barre reste aux tableaux Markdown) / "|" stays Markdown.
pub const CSV_DELIMITERS: [char; 3] = [';', '\t', ','];
const CSV_HEADER_MAX: usize = 40;
const CSV_MIN_ROWS: usize = 2;

/// `_text._csv_cells` : champs de [start, stop), rognés de leurs blancs / fields, trimmed of blanks.
fn csv_cells(
    text: &[char],
    start: usize,
    stop: usize,
    delimiter: char,
    is_space: &impl Fn(char) -> bool,
) -> Vec<(usize, usize)> {
    let mut cells = Vec::new();
    let mut left = start;
    loop {
        let right = text[left..stop].iter().position(|&c| c == delimiter).map_or(stop, |i| left + i);
        let (mut a, mut b) = (left, right);
        while a < b && is_space(text[a]) {
            a += 1;
        }
        while b > a && is_space(text[b - 1]) {
            b -= 1;
        }
        cells.push((a, b));
        if right >= stop {
            return cells;
        }
        left = right + 1;
    }
}

/// `_text.delimited_tables` : tableaux CSV ou TSV, chaque tableau ses lignes (en-tête d'abord), chaque ligne ses
/// champs, en positions de caractères / CSV or TSV tables: rows (header first), fields, in character positions.
pub fn delimited_tables(text: &[char], is_space: impl Fn(char) -> bool) -> Vec<Vec<Vec<(usize, usize)>>> {
    let tables = table_scan(text, &is_space);
    // Lignes TSV retenues pour `tab_row_chars` ; sans tableau TSV, l'entrée est vidée (jamais périmée, et pas de copie
    // du texte) / TSV rows recorded for `tab_row_chars`; with no TSV table the entry is cleared (never stale, no copy).
    let rows = tab_rows_of(&tables);
    TAB_ROWS.with(|cell| *cell.borrow_mut() = (!rows.is_empty()).then(|| TabRows::new(text, rows)));
    tables
        .into_iter()
        .map(|(delimiter, lines)| {
            lines.into_iter().map(|(start, stop)| csv_cells(text, start, stop, delimiter, &is_space)).collect()
        })
        .collect()
}

/// `_text._table_scan` : (délimiteur, lignes [début, fin) en-tête d'abord) de chaque tableau / each table's lines.
fn table_scan(text: &[char], is_space: &impl Fn(char) -> bool) -> Vec<(char, Vec<(usize, usize)>)> {
    if !text.contains(&'\n') {
        return Vec::new();
    }
    let mut lines: Vec<(usize, usize)> = Vec::new();
    let mut pos = 0;
    loop {
        let end = text[pos..].iter().position(|&c| c == '\n').map_or(text.len(), |i| pos + i);
        let stop = if end > pos && text[end - 1] == '\r' { end - 1 } else { end };
        lines.push((pos, stop));
        if end >= text.len() {
            break;
        }
        pos = end + 1;
    }
    let count = |(a, b): (usize, usize), d: char| text[a..b].iter().filter(|&&c| c == d).count();
    let mut tables = Vec::new();
    let mut i = 0;
    while i < lines.len() {
        for delimiter in CSV_DELIMITERS {
            let n = count(lines[i], delimiter);
            if n < 2 {
                continue;
            }
            let header = csv_cells(text, lines[i].0, lines[i].1, delimiter, is_space);
            let labels = header
                .iter()
                .all(|&(a, b)| b > a && b - a <= CSV_HEADER_MAX && !text[a..b].iter().any(char::is_ascii_digit));
            if !labels {
                continue;
            }
            let mut j = i + 1;
            while j < lines.len() && count(lines[j], delimiter) == n {
                j += 1;
            }
            if j - i - 1 < CSV_MIN_ROWS {
                continue;
            }
            tables.push((delimiter, lines[i..j].to_vec()));
            i = j - 1;
            break;
        }
        i += 1;
    }
    tables
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn delimited_tables_follow_the_python_rules() {
        let text: Vec<char> = "x\nid;nom;date_naissance\n1;A;2\n2;B;3\n\nfin, et, plus".chars().collect();
        let tables = delimited_tables(&text, char::is_whitespace);
        assert_eq!(tables.len(), 1);
        assert_eq!(tables[0].len(), 3);
        let cell = |(a, b): (usize, usize)| text[a..b].iter().collect::<String>();
        assert_eq!(cell(tables[0][0][2]), "date_naissance");
        assert_eq!(cell(tables[0][2][1]), "B");
        let digits: Vec<char> = "a;b1;c\n1;2;3\n4;5;6".chars().collect();
        assert!(delimited_tables(&digits, char::is_whitespace).is_empty());
    }
}
