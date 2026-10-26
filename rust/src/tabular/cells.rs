//! Cellules et fusions d'une feuille, en une passe / a sheet's cells and merges, in one pass.
//!
//! Transcription de `XlsxCellReader` (valeurs) et de `merge_cells_by_sheet_name` (fusions) de calamine
//! 0.36.1 (MIT). Formes canoniques seulement : nombres décimaux simples, index et styles entiers, types connus ;
//! le reste est refusé. Les cellules vides ne sont pas gardées, comme `Range::from_sparse`.
//! Transcribes calamine 0.36.1's `XlsxCellReader` (values) and `merge_cells_by_sheet_name` (merges). Canonical
//! forms only: plain decimal numbers, integer indexes and styles, known types; the rest is declined. Empty cells
//! are not kept, as `Range::from_sparse`.

use super::parts::{read_string, CellFormat, StringBuffers, Workbook};
use super::xml::{local, push_text, Event, Reader};
use super::{Decline, Result};

/// Valeur d'une cellule non vide / value of a non-empty cell.
#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) enum Value {
    Float(f64),
    Bool(bool),
    /// Index dans les chaînes partagées / index into the shared strings.
    Shared(u32),
    /// Tranche de l'arène de texte de la feuille / slice of the sheet's text arena.
    Text {
        start: u32,
        len: u32,
    },
    /// Erreur Excel (`#DIV/0!`…), rendue vide par python-calamine / Excel error, rendered empty.
    Error,
    /// Nombre au format date ou durée / number with a date or duration format.
    Date {
        serial: f64,
        duration: bool,
    },
}

#[derive(Debug, Clone, Copy)]
pub(crate) struct Cell {
    pub(crate) row: u32,
    pub(crate) col: u32,
    pub(crate) value: Value,
}

pub(crate) type Corner = (u32, u32);

/// Feuille lue : cellules dans l'ordre du flux, textes, fusions / sheet read: cells in stream order, texts, merges.
#[derive(Default)]
pub(crate) struct SheetCells {
    pub(crate) cells: Vec<Cell>,
    pub(crate) text: String,
    pub(crate) merged: Vec<(Corner, Corner)>,
}

/// Type de cellule (attribut `t`) / cell type (`t` attribute).
#[derive(Clone, Copy, PartialEq, Eq)]
enum Kind {
    Number,
    Shared,
    Bool,
    Error,
    Str,
    Inline,
}

impl Kind {
    fn parse(t: Option<&[u8]>) -> Result<Self> {
        Ok(match t {
            None | Some(b"n") => Kind::Number,
            Some(b"s") => Kind::Shared,
            Some(b"b") => Kind::Bool,
            Some(b"e") => Kind::Error,
            Some(b"str") => Kind::Str,
            Some(b"inlineStr" | b"is") => Kind::Inline,
            // `d` (date ISO), types inconnus : laissés à la référence / ISO dates, unknown types: reference.
            _ => return Err(Decline("unsupported cell type")),
        })
    }
}

/// Entier décimal canonique (sans zéro initial ni signe) / canonical decimal integer.
fn canonical_index(raw: &[u8]) -> Result<u32> {
    let canonical =
        !raw.is_empty() && raw.len() <= 9 && raw.iter().all(u8::is_ascii_digit) && (raw[0] != b'0' || raw.len() == 1);
    if !canonical {
        return Err(Decline("non-canonical index"));
    }
    Ok(raw.iter().fold(0u32, |n, &d| n * 10 + u32::from(d - b'0')))
}

/// Nombre décimal canonique `-?chiffres(.chiffres)?(e[+-]?chiffres)?` : arrondi correct, comme fast-float2.
/// Canonical decimal number: correctly rounded, as fast-float2.
fn canonical_float(raw: &[u8]) -> Result<f64> {
    let digits = |s: &[u8]| s.iter().take_while(|b| b.is_ascii_digit()).count();
    let mut i = usize::from(raw.first() == Some(&b'-'));
    let integer = digits(&raw[i..]);
    i += integer;
    let mut valid = integer > 0;
    if raw.get(i) == Some(&b'.') {
        let fraction = digits(&raw[i + 1..]);
        valid &= fraction > 0;
        i += 1 + fraction;
    }
    if matches!(raw.get(i), Some(b'e' | b'E')) {
        i += 1;
        if matches!(raw.get(i), Some(b'+' | b'-')) {
            i += 1;
        }
        let exponent = digits(&raw[i..]);
        valid &= exponent > 0;
        i += exponent;
    }
    if !valid || i != raw.len() {
        return Err(Decline("non-canonical number"));
    }
    std::str::from_utf8(raw).ok().and_then(|s| s.parse::<f64>().ok()).ok_or(Decline("non-canonical number"))
}

/// Référence A1 en (ligne, colonne facultative), base 0 (`get_row_and_optional_column`) / A1 reference.
fn position(reference: &[u8]) -> Result<(u32, Option<u32>)> {
    let overflow = Decline("reference overflow");
    let mut col: u32 = 0;
    let mut row: u32 = 0;
    let mut i = 0;
    while i < reference.len() {
        let c = reference[i];
        i += 1;
        match c {
            b'A'..=b'Z' | b'a'..=b'z' => {
                let letter = u32::from(c.to_ascii_uppercase() - b'A') + 1;
                col = col.checked_mul(26).and_then(|n| n.checked_add(letter)).ok_or(overflow)?;
            }
            b'0'..=b'9' => {
                row = u32::from(c - b'0');
                break;
            }
            _ => return Err(Decline("bad cell reference")),
        }
    }
    for &c in &reference[i..] {
        if !c.is_ascii_digit() {
            return Err(Decline("bad cell reference"));
        }
        row = row.checked_mul(10).and_then(|n| n.checked_add(u32::from(c - b'0'))).ok_or(overflow)?;
    }
    let row = row.checked_sub(1).ok_or(Decline("reference without row"))?;
    Ok((row, col.checked_sub(1)))
}

fn cell_position(reference: &[u8]) -> Result<Corner> {
    match position(reference)? {
        (row, Some(col)) => Ok((row, col)),
        (_, None) => Err(Decline("reference without column")),
    }
}

/// Plage `A1` ou `A1:B2` (`get_dimension`) / range.
fn dimension(reference: &[u8]) -> Result<(Corner, Corner)> {
    let mut parts = reference.split(|&b| b == b':');
    let start = cell_position(parts.next().unwrap_or_default())?;
    let end = match parts.next() {
        Some(part) => cell_position(part)?,
        None => start,
    };
    if parts.next().is_some() {
        return Err(Decline("bad dimension"));
    }
    Ok((start, end))
}

/// Lecteur de cellules : état réutilisé d'une cellule à l'autre / cell reader, state reused across cells.
struct CellReader<'w> {
    workbook: &'w Workbook,
    sheet: SheetCells,
    closing: Vec<u8>,
    buffers: StringBuffers,
    value: String,
}

impl CellReader<'_> {
    /// Format du style `s` (absent : « autre ») ; style inconnu : aucun format (`formats.get`).
    /// Format of style `s` (absent: other); unknown style: no format.
    fn format(&self, style: Option<u32>) -> Option<CellFormat> {
        match style {
            None => Some(CellFormat::Other),
            Some(index) => self.workbook.formats.get(index as usize).copied(),
        }
    }

    fn number(&self, raw: &[u8], style: Option<u32>) -> Result<Value> {
        let serial = canonical_float(raw)?;
        Ok(match self.format(style) {
            Some(CellFormat::DateTime) => Value::Date { serial, duration: false },
            Some(CellFormat::TimeDelta) => Value::Date { serial, duration: true },
            _ => Value::Float(serial),
        })
    }

    fn arena(&mut self, start: usize) -> Result<Value> {
        let len = self.sheet.text.len() - start;
        let start = u32::try_from(start).map_err(|_| Decline("text arena overflow"))?;
        let len = u32::try_from(len).map_err(|_| Decline("text arena overflow"))?;
        Ok(Value::Text { start, len })
    }

    /// Valeur d'un fils de `<c>` (`read_value`) ; le dernier fils l'emporte / value of a `<c>` child.
    fn child(&mut self, xml: &mut Reader<'_>, name: &[u8], kind: Kind, style: Option<u32>) -> Result<Option<Value>> {
        match local(name) {
            b"is" => {
                self.closing.clear();
                self.closing.extend_from_slice(name);
                let start = self.sheet.text.len();
                read_string(xml, &self.closing, &mut self.sheet.text, &mut self.buffers)?;
                self.arena(start).map(Some)
            }
            b"v" if kind == Kind::Inline => xml.skip_element().map(|()| None),
            b"v" if kind == Kind::Str => {
                // Textes et références jusqu'à la fermeture de même nom / texts and references up to the end tag.
                self.closing.clear();
                self.closing.extend_from_slice(name);
                self.value.clear();
                loop {
                    match xml.next()? {
                        Event::Text(raw) => push_text(raw, &mut self.value)?,
                        Event::Ref(reference) => reference.push_to(&mut self.value),
                        Event::End { name, .. } if name == self.closing.as_slice() => break,
                        Event::Eof => return Err(Decline("unterminated v")),
                        _ => {}
                    }
                }
                let start = self.sheet.text.len();
                self.sheet.text.push_str(&self.value);
                self.arena(start).map(Some)
            }
            b"v" => {
                // Premier événement brut seulement (types n, s, b, e) / first raw event only.
                let value = match xml.next()? {
                    Event::End { .. } => return Ok(None),
                    Event::Text(raw) => Some(self.raw_value(raw, kind, style)?),
                    Event::Ref(_) => None,
                    _ => return Err(Decline("markup inside v")),
                };
                xml.skip_element()?;
                Ok(value)
            }
            b"f" => xml.skip_element().map(|()| None),
            _ => Err(Decline("unexpected cell child")),
        }
    }

    /// `read_v` pour les types lus bruts / `read_v` for the raw-read types.
    fn raw_value(&self, raw: &[u8], kind: Kind, style: Option<u32>) -> Result<Value> {
        Ok(match kind {
            Kind::Shared => {
                let index = canonical_index(raw)?;
                if index as usize >= self.workbook.strings.len() {
                    return Err(Decline("shared string index out of range"));
                }
                Value::Shared(index)
            }
            Kind::Bool => Value::Bool(raw != b"0"),
            Kind::Error => match raw {
                b"#DIV/0!" | b"#N/A" | b"#NAME?" | b"#NULL!" | b"#NUM!" | b"#REF!" | b"#VALUE!" => Value::Error,
                _ => return Err(Decline("unsupported error value")),
            },
            Kind::Number => self.number(raw, style)?,
            Kind::Str | Kind::Inline => return Err(Decline("cell type")),
        })
    }
}

/// Lit une feuille entière / reads a whole sheet.
pub(crate) fn read(xml: &mut Reader<'_>, workbook: &Workbook) -> Result<SheetCells> {
    // En-tête jusqu'à `<sheetData>` : `<dimension ref>` contrôlé (`XlsxCellReader::new`) / header.
    loop {
        match xml.next()? {
            Event::Start { local: b"dimension", attrs, .. } => {
                dimension(attrs.get(b"ref").ok_or(Decline("dimension without ref"))?)?;
            }
            Event::Start { local: b"sheetData", .. } => break,
            Event::Start { local: b"mergeCells", .. } => return Err(Decline("merges before data")),
            Event::Eof => return Err(Decline("no sheetData")),
            _ => {}
        }
    }
    let mut reader = CellReader {
        workbook,
        sheet: SheetCells::default(),
        closing: Vec::new(),
        buffers: StringBuffers::default(),
        value: String::new(),
    };
    let (mut row_index, mut col_index) = (0u32, 0u32);
    let mut child = Vec::with_capacity(16);
    loop {
        match xml.next()? {
            Event::Start { local: b"row", attrs, .. } => {
                if let Some(r) = attrs.get(b"r") {
                    row_index = position(r)?.0;
                }
            }
            Event::End { local: b"row", .. } => {
                row_index = row_index.checked_add(1).ok_or(Decline("row overflow"))?;
                col_index = 0;
            }
            Event::Start { local: b"c", attrs, .. } => {
                let [r, s, t] = attrs.get_many([b"r", b"s", b"t"]);
                let (row, col) = match r {
                    Some(r) => cell_position(r)?,
                    None => (row_index, col_index),
                };
                col_index = col;
                let style = s.map(canonical_index).transpose()?;
                let kind = Kind::parse(t)?;
                let mut value = None;
                loop {
                    match xml.next()? {
                        Event::Start { name, .. } => {
                            child.clear();
                            child.extend_from_slice(name);
                        }
                        Event::End { local: b"c", .. } => break,
                        Event::Eof => return Err(Decline("unterminated c")),
                        _ => continue,
                    }
                    value = reader.child(xml, &child, kind, style)?;
                }
                col_index = col_index.checked_add(1).ok_or(Decline("column overflow"))?;
                if let Some(value) = value {
                    reader.sheet.cells.push(Cell { row, col, value });
                }
            }
            Event::Start { local: b"mergeCells", .. } => {
                return Err(Decline("merges inside data"));
            }
            Event::End { local: b"sheetData", .. } => break,
            Event::Eof => return Err(Decline("unterminated sheetData")),
            _ => {}
        }
    }
    // Fusions : premier `<mergeCells>` du document, lu jusqu'à sa fermeture / first `<mergeCells>`, to its end.
    loop {
        match xml.next()? {
            Event::Start { local: b"mergeCells", .. } => {
                loop {
                    match xml.next()? {
                        Event::Start { local: b"mergeCell", attrs, .. } => {
                            if let Some(r) = attrs.get(b"ref") {
                                reader.sheet.merged.push(dimension(r)?);
                            }
                        }
                        Event::End { local: b"mergeCells", .. } => break,
                        Event::Eof => return Err(Decline("unterminated mergeCells")),
                        _ => {}
                    }
                }
                break;
            }
            Event::Eof => break,
            _ => {}
        }
    }
    Ok(reader.sheet)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn references_follow_calamine() {
        assert_eq!(position(b"A1").unwrap(), (0, Some(0)));
        assert_eq!(position(b"xfd1048576").unwrap(), (1_048_575, Some(16_383)));
        assert_eq!(position(b"7").unwrap(), (6, None));
        assert_eq!(position(b"A01").unwrap(), (0, Some(0)));
        for bad in [&b"A0"[..], b"A", b"", b"1A", b"A-1", b"AAAAAAAAAAAAAAAAAAAAAAAA1", b"A99999999999"] {
            assert!(position(bad).is_err(), "{}", String::from_utf8_lossy(bad));
        }
        assert_eq!(dimension(b"B2:A1").unwrap(), ((1, 1), (0, 0)));
        assert_eq!(dimension(b"C3").unwrap(), ((2, 2), (2, 2)));
        assert!(dimension(b"A1:B2:C3").is_err());
    }

    #[test]
    fn only_canonical_numbers_and_indexes_are_read() {
        assert_eq!(canonical_float(b"-1.5E+3").unwrap(), -1500.0);
        assert_eq!(canonical_float(b"007").unwrap(), 7.0);
        assert_eq!(canonical_float(b"1e400").unwrap(), f64::INFINITY);
        assert_eq!(canonical_float(b"0.1").unwrap(), 0.1);
        for bad in [&b"1."[..], b".5", b"+1", b" 1", b"nan", b"inf", b"1e", b"1,5", b"0x1", b""] {
            assert!(canonical_float(bad).is_err(), "{}", String::from_utf8_lossy(bad));
        }
        assert_eq!(canonical_index(b"0").unwrap(), 0);
        assert_eq!(canonical_index(b"123").unwrap(), 123);
        for bad in [&b"01"[..], b"", b"-1", b"1234567890", b" 1"] {
            assert!(canonical_index(bad).is_err());
        }
    }
}
