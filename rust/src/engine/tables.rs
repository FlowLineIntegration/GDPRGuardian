//! Cellules de tableau Markdown dont l'en-tête de colonne porte un contexte : port exact de
//! `engine.markdown_table_zones` et `engine._cells` (Python, la référence).
//!
//! Markdown table cells whose column header carries context: exact port of the Python functions. Les
//! caractères de structure (« \n », « | », « \ », tirets) sont ASCII : lignes et barres se trouvent sur les
//! octets ; seuls les blancs de bord (`str.isspace`) sont décodés. Structure characters are ASCII: lines and
//! pipes are found on bytes; only the edge blanks (`str.isspace`) are decoded.

use crate::scanner::Zone;

/// `_TABLE_DELIMITER_RE` appliqué à une ligne entière, sans son « \n » (`^…$` en mode multiligne) :
/// `[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)+\|?[ \t\r]*`. Chaque choix est forcé (une barre
/// suivie d'une cellule ouvre forcément une colonne), d'où une lecture sans retour arrière.
/// Every choice is forced (a pipe followed by a cell always opens a column): read without backtracking.
fn is_delimiter_row(line: &[u8]) -> bool {
    let at = |i: usize| line.get(i).copied();
    let blanks = |mut i: usize| {
        while matches!(at(i), Some(b' ' | b'\t')) {
            i += 1;
        }
        i
    };
    // `[ \t]*:?-+:?[ \t]*` : fin de la cellule, ou `None` sans tiret / end of the cell, or `None` without dashes.
    let cell = |i: usize| {
        let mut i = blanks(i);
        if at(i) == Some(b':') {
            i += 1;
        }
        let dashes = line.get(i..).map_or(0, |rest| rest.iter().take_while(|&&b| b == b'-').count());
        if dashes == 0 {
            return None;
        }
        i += dashes;
        if at(i) == Some(b':') {
            i += 1;
        }
        Some(blanks(i))
    };
    let mut i = blanks(0);
    if at(i) == Some(b'|') {
        i += 1;
    }
    let Some(mut i) = cell(i) else {
        return false;
    };
    let mut columns = 0;
    while at(i) == Some(b'|') {
        match cell(i + 1) {
            Some(next) => {
                i = next;
                columns += 1;
            }
            None => break,
        }
    }
    if columns == 0 {
        return false;
    }
    if at(i) == Some(b'|') {
        i += 1;
    }
    while matches!(at(i), Some(b' ' | b'\t' | b'\r')) {
        i += 1;
    }
    i == line.len()
}

/// `_cells` : cellules d'une ligne (barres échappées ignorées), rognées de leurs blancs, en octets absolus.
/// Cells of a line (escaped pipes ignored), trimmed of blanks, in absolute bytes.
fn cells(line: &str, offset: usize, is_space: &impl Fn(char) -> bool) -> Vec<(usize, usize)> {
    let bytes = line.as_bytes();
    // `(?<!\\)\|` : barres non précédées d'une barre oblique inverse / pipes not preceded by a backslash.
    let pipes = (0..bytes.len()).filter(|&i| bytes[i] == b'|' && (i == 0 || bytes[i - 1] != b'\\'));
    let edges: Vec<usize> = std::iter::once(0).chain(pipes.map(|i| i + 1)).collect();
    let ends: Vec<usize> = edges.iter().skip(1).map(|&e| e - 1).chain([bytes.len()]).collect();
    let blank = |part: &str| part.chars().all(is_space);
    let mut found: Vec<(usize, usize)> = edges
        .iter()
        .zip(&ends)
        .map(|(&start, &end)| {
            let part = line.get(start..end).unwrap_or("");
            let trimmed = part.trim_start_matches(is_space);
            let left = start + (part.len() - trimmed.len());
            (offset + left, offset + left + trimmed.trim_end_matches(is_space).len())
        })
        .collect();
    // Barres de bord : pas de cellule avant la première ni après la dernière / edge pipes open no cell.
    if edges.len() > 1 && blank(line.get(..ends[0]).unwrap_or("")) {
        found.remove(0);
    }
    if edges.len() > 1 && !found.is_empty() && blank(line.get(edges[edges.len() - 1]..).unwrap_or("")) {
        found.pop();
    }
    found
}

/// Positions en caractères le long d'octets croissants / character positions along increasing bytes.
struct Cursor<'t> {
    text: &'t [u8],
    byte: usize,
    char: usize,
}

impl Cursor<'_> {
    fn char_index(&mut self, byte: usize) -> usize {
        // Octets de tête UTF-8 : un par caractère / UTF-8 lead bytes: one per character.
        let lead =
            self.text.get(self.byte..byte).map_or(0, |part| part.iter().filter(|&&b| (b as i8) >= -0x40).count());
        self.char += lead;
        self.byte = byte;
        self.char
    }
}

/// `markdown_table_zones` : cellules sous un en-tête de colonne porteur de contexte, triées et disjointes,
/// en positions de caractères. `groups_of` : groupes de contexte d'un texte d'en-tête (`context_groups`).
/// Cells under a context-bearing column header, sorted and disjoint, in character positions.
pub(crate) fn zones(text: &str, groups_of: impl Fn(&str) -> Vec<u32>, is_space: impl Fn(char) -> bool) -> Vec<Zone> {
    let bytes = text.as_bytes();
    if !bytes.contains(&b'|') {
        return Vec::new();
    }
    let line_end = |from: usize| {
        bytes.get(from..).and_then(|rest| rest.iter().position(|&b| b == b'\n')).map_or(bytes.len(), |i| from + i)
    };
    let mut zones = Vec::new();
    let mut cursor = Cursor { text: bytes, byte: 0, char: 0 };
    let mut consumed = 0;
    let mut start = 0;
    while start <= bytes.len() {
        let end = line_end(start);
        let next = end + 1;
        let row = bytes.get(start..end).unwrap_or_default();
        // Une délimitation dans un tableau déjà lu est une simple ligne (GFM) / inside a table, just a row.
        if start >= consumed && start > 0 && is_delimiter_row(row) {
            let header_end = start - 1;
            let header_start = bytes[..header_end].iter().rposition(|&b| b == b'\n').map_or(0, |i| i + 1);
            let header = text.get(header_start..header_end).unwrap_or("");
            if header.contains('|') {
                let columns: Vec<Vec<u32>> = cells(header, header_start, &is_space)
                    .into_iter()
                    .map(|(s, e)| groups_of(text.get(s..e).unwrap_or("")))
                    .collect();
                let mut pos = next;
                while pos < bytes.len() {
                    let stop = line_end(pos);
                    let line = text.get(pos..stop).unwrap_or("");
                    if !line.contains('|') {
                        break;
                    }
                    if columns.iter().any(|groups| !groups.is_empty()) {
                        for (column, (s, e)) in cells(line, pos, &is_space).into_iter().enumerate() {
                            match columns.get(column) {
                                Some(groups) if !groups.is_empty() && e > s => {
                                    let (s, e) = (cursor.char_index(s), cursor.char_index(e));
                                    zones.push(Zone { start: s, end: e, groups: groups.clone() });
                                }
                                _ => {}
                            }
                        }
                    }
                    pos = stop + 1;
                }
                consumed = pos;
            }
        }
        start = next;
    }
    zones
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn delimiter_rows_follow_the_python_pattern() {
        for row in ["|---|---|", "---|---", " :--- | ---: ", "|-|-", "--|--|\r", "| --- | :---: |  \t"] {
            assert!(is_delimiter_row(row.as_bytes()), "{row}");
        }
        for row in ["|---|", "---", "| a |---|", "|---|---|x", "|---||", ":|---|---", "|- -|---|", ""] {
            assert!(!is_delimiter_row(row.as_bytes()), "{row}");
        }
    }

    #[test]
    fn cells_skip_escaped_and_edge_pipes() {
        let space = |c: char| c.is_whitespace();
        assert_eq!(cells("| a | b |", 10, &space), [(12, 13), (16, 17)]);
        assert_eq!(cells("a \\| b | c", 0, &space), [(0, 6), (9, 10)]);
        assert_eq!(cells("|  | x |", 0, &space), [(3, 3), (5, 6)]);
    }

    #[test]
    fn zones_cover_the_tagged_column_until_the_table_ends() {
        let groups_of = |header: &str| if header.contains("naissance") { vec![7] } else { Vec::new() };
        let text = "Nom \\| alias | Date de naissance\n-|-\nA \\| B | 03/03/1985\r\nC | 04/04/1990\n\nfin | 05/05/2005";
        let found: Vec<&str> = zones(text, groups_of, char::is_whitespace)
            .iter()
            .map(|z| text.get(z.start..z.end).unwrap_or(""))
            .collect();
        assert_eq!(found, ["03/03/1985", "04/04/1990"]);
        let text = "| a | naissance |\n|---|---|\n| b | 1 |\n|---|---|\n| c | 2 |";
        let found: Vec<&str> = zones(text, groups_of, char::is_whitespace)
            .iter()
            .map(|z| text.get(z.start..z.end).unwrap_or(""))
            .collect();
        assert_eq!(found, ["1", "---", "2"]);
    }
}
