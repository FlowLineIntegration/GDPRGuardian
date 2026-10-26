//! Colonnes de personnes : tableaux Markdown et segments marqués « personne » par leur en-tête.
//!
//! Person columns: Markdown tables and header-tagged segments. Port of `_structured`, `_cells`,
//! `_table_rows` and `_row_spans`.

use super::chars::{contains, find, strip_chars, sub};
use super::lexicon::{ambiguity, AMB_NONE};
use super::patterns;
use super::vocab::flag;
use super::{Confirmed, Doc, Found};

/// Rôle d'une colonne d'après son en-tête / column role from its header.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Role {
    None,
    Given,
    Surname,
    Full,
}

type Cell = (usize, usize, Role);

impl Doc<'_> {
    /// `_structured` : zones émises, cellules d'indice fort (pas en forme de nom), formes ambiguës confirmées.
    /// Emitted spans, strong-cue cells (not name-shaped) and confirmed ambiguous forms.
    pub(super) fn structured(
        &self,
        person_rows: &[(usize, usize)],
        found: &mut Vec<Found>,
        zones: &mut Vec<(usize, usize)>,
        confirmed: &mut Confirmed,
    ) {
        if self.text.contains(&'|') && contains(&self.text, &['-', '-', '-']) {
            for row in self.table_rows() {
                self.row_spans(&row, found, zones, confirmed);
            }
        }
        for &(start, end) in person_rows {
            self.row_spans(&[(start, end, Role::Full)], found, zones, confirmed);
        }
    }

    /// `_cells` : cellules d'une ligne, sans les blancs / the cells of a line, whitespace stripped.
    fn cells(&self, start: usize, end: usize) -> Vec<(usize, usize)> {
        let chars = &self.det.chars;
        let line = sub(&self.text, start, end);
        let bars: Vec<usize> = line.iter().enumerate().filter(|(_, &c)| c == '|').map(|(i, _)| i).collect();
        let (Some(&first), Some(&last)) = (bars.first(), bars.last()) else {
            return Vec::new();
        };
        // Bords : -1 et len(line) quand du texte déborde des barres / edges, as `isize` offsets.
        let mut edges: Vec<isize> = Vec::with_capacity(bars.len() + 2);
        if !chars.strip(&line[..first]).is_empty() {
            edges.push(-1);
        }
        edges.extend(bars.iter().map(|&b| b as isize));
        if !chars.strip(&line[last + 1..]).is_empty() {
            edges.push(line.len() as isize);
        }
        edges
            .windows(2)
            .map(|pair| {
                let (left, right) = ((pair[0] + 1) as usize, pair[1] as usize);
                let cell = &line[left..right];
                let offset = start + left + chars.leading_spaces(cell);
                (offset, offset + chars.strip(cell).len())
            })
            .collect()
    }

    /// `_table_rows` : lignes des tableaux dont l'en-tête désigne des personnes / rows of person tables.
    fn table_rows(&self) -> Vec<Vec<Cell>> {
        let (det, text) = (self.det, &self.text);
        let mut rows = Vec::new();
        let mut consumed = 0;
        let mut header: Vec<char> = Vec::new();
        let mut line_start = 0;
        // `(?m)^…$` : chaque ligne entière est candidate / every whole line is a candidate.
        while line_start <= text.len() {
            let line_end = find(text, '\n', line_start, text.len()).unwrap_or(text.len());
            let (sep_start, sep_end) = (line_start, line_end);
            line_start = line_end + 1;
            if !patterns::table_separator(&text[sep_start..sep_end]) {
                continue;
            }
            if sep_start < 2 || sep_start < consumed {
                continue; // séparateur déjà lu comme ligne d'un tableau / already read as a table row
            }
            let header_end = sep_start - 1;
            let (header_start, _, whole) = self.line_bounds(header_end, 2048);
            if !whole {
                continue;
            }
            let roles: Vec<Role> = self
                .cells(header_start, header_end)
                .into_iter()
                .map(|(s, e)| {
                    header.clear();
                    det.chars.push_fold(&text[s..e], &mut header);
                    let label = det.vocab.get(strip_chars(&header, " *_`"));
                    if label.has(flag::GIVEN_HEADER) {
                        Role::Given
                    } else if label.has(flag::SURNAME_HEADER) {
                        Role::Surname
                    } else if label.has(flag::PERSON_HEADER) {
                        Role::Full
                    } else {
                        Role::None
                    }
                })
                .collect();
            if roles.iter().all(|&r| r == Role::None) {
                continue;
            }
            let mut pos = sep_end + 1;
            while pos < text.len() {
                let row_end = find(text, '\n', pos, text.len()).unwrap_or(text.len());
                if !text[pos..row_end].contains(&'|') {
                    break;
                }
                let cells = self.cells(pos, row_end);
                rows.push(
                    cells
                        .into_iter()
                        .zip(roles.iter())
                        .filter(|(_, &role)| role != Role::None)
                        .map(|((s, e), &role)| (s, e, role))
                        .collect(),
                );
                pos = row_end + 1;
            }
            consumed = pos;
        }
        rows
    }

    /// `_row_spans` : une ligne ; prénom et nom partagent la même forme canonique.
    /// One row: given name and surname share one canonical value.
    fn row_spans(
        &self,
        row: &[Cell],
        found: &mut Vec<Found>,
        zones: &mut Vec<(usize, usize)>,
        confirmed: &mut Confirmed,
    ) {
        let (det, text) = (self.det, &self.text);
        let chars = &det.chars;
        let mut cells: Vec<(usize, usize, Role, &[char])> = Vec::new();
        let mut key: Vec<char> = Vec::new();
        for &(start, end, role) in row {
            let raw = sub(text, start, end);
            let content = chars.strip(raw);
            key.clear();
            chars.push_fold(content, &mut key);
            if content.is_empty() || det.vocab.get(&key).has(flag::EMPTY_CELL) {
                continue;
            }
            let start = start + chars.leading_spaces(raw);
            let end = start + content.len();
            if patterns::name_cell(chars, content) && chars.split_count(content) <= 6 {
                cells.push((start, end, role, content));
            } else {
                zones.push((start, end)); // « Jean Dupont (DRH) » : indice fort pour la cellule / strong cue
            }
        }
        let given = cells.iter().find(|c| c.2 == Role::Given).map(|c| c.3);
        let surname = cells.iter().find(|c| c.2 == Role::Surname).map(|c| c.3);
        for &(start, end, role, content) in &cells {
            let value: String = match (given, surname) {
                (Some(g), Some(s)) if matches!(role, Role::Given | Role::Surname) => {
                    g.iter().chain(std::iter::once(&' ')).chain(s.iter()).collect()
                }
                _ => content.iter().collect(),
            };
            key.clear();
            chars.push_fold(content, &mut key);
            let code = if content.contains(&' ') { None } else { det.code(&key) };
            // Un mot courant (« Direction ») est masqué ici mais jamais propagé / a common word is never propagated.
            let safe = match code {
                Some(code) => ambiguity(code) == AMB_NONE,
                None => !det.vocab.get(&key).has(flag::WORD),
            };
            if !safe {
                confirmed.insert(key.clone()); // forme ambiguë : propagation prudente / careful propagation
            }
            found.push(Found { start, end, value, score: 0.9, propagate: safe, form: None });
        }
    }
}
