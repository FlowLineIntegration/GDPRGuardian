//! Parties du classeur : relations, `workbook.xml`, styles, chaînes partagées / workbook-level parts.
//!
//! Transcription de `Xlsx::new` de calamine 0.36.1 (MIT) : mêmes parties, même ordre, mêmes règles ; ce que
//! calamine signalerait comme erreur devient un refus. Transcribes calamine 0.36.1's `Xlsx::new` (MIT): same
//! parts, order and rules; what calamine would report as an error becomes a decline.

use std::collections::HashMap;

use super::xml::{push_text, unescape, Event, Reader};
use super::zip::Directory;
use super::{Decline, Result};

/// Format de nombre d'un style de cellule (`CellFormat` de calamine) / number format of a cell style.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum CellFormat {
    Other,
    DateTime,
    TimeDelta,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum SheetKind {
    Work,
    Chart,
    Dialog,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Visibility {
    Visible,
    Hidden,
    VeryHidden,
}

pub(crate) struct Sheet {
    pub(crate) name: String,
    pub(crate) path: String,
    pub(crate) kind: SheetKind,
    pub(crate) visibility: Visibility,
}

/// Ce que calamine lit à l'ouverture / what calamine reads when opening.
pub(crate) struct Workbook {
    pub(crate) sheets: Vec<Sheet>,
    pub(crate) strings: Vec<Box<str>>,
    pub(crate) formats: Vec<CellFormat>,
    pub(crate) is_1904: bool,
}

/// Dossier attendu du classeur ; tout autre emplacement est laissé à la référence / expected workbook folder.
const XL_PATH: &str = "xl/";

pub(crate) fn part<'a>(directory: &Directory, data: &'a [u8], path: &str) -> Result<Option<Reader<'a>>> {
    match directory.find(path) {
        Some(index) => Ok(Some(Reader::new(directory.reader(data, index)?))),
        None => Ok(None),
    }
}

/// Valeur d'attribut décodée (`decode_attr`) / decoded attribute value.
fn decode(raw: &[u8]) -> Result<String> {
    let text = std::str::from_utf8(raw).map_err(|_| Decline("xml: invalid UTF-8"))?;
    unescape(text).ok_or(Decline("xml: bad attribute reference"))
}

fn utf8(raw: &[u8]) -> Result<&str> {
    std::str::from_utf8(raw).map_err(|_| Decline("xml: invalid UTF-8"))
}

impl Workbook {
    pub(crate) fn open(directory: &Directory, data: &[u8]) -> Result<Self> {
        let xl_path = package_relationships(directory, data)?;
        if xl_path != XL_PATH {
            return Err(Decline("workbook outside xl/"));
        }
        let strings = shared_strings(directory, data)?;
        let formats = styles(directory, data)?;
        let relationships = workbook_relationships(directory, data)?;
        let (sheets, is_1904) = workbook(directory, data, &relationships)?;
        Ok(Self { sheets, strings, formats, is_1904 })
    }
}

/// `_rels/.rels` : dossier de la cible `officeDocument` (la dernière) / folder of the last officeDocument target.
fn package_relationships(directory: &Directory, data: &[u8]) -> Result<String> {
    let mut xml = part(directory, data, "_rels/.rels")?.ok_or(Decline("missing package relationships"))?;
    loop {
        match xml.next()? {
            Event::Start { local: b"Relationships", .. } => break,
            Event::Eof => return Err(Decline("no Relationships element")),
            _ => {}
        }
    }
    let mut target = None;
    loop {
        match xml.next()? {
            Event::Start { local: b"Relationship", attrs, .. } => {
                let [kind, value] = attrs.get_many([b"Type", b"Target"]);
                if kind.is_some_and(|k| k.ends_with(b"/relationships/officeDocument")) {
                    if let Some(value) = value {
                        target = Some(decode(value)?);
                    }
                }
            }
            Event::End { local: b"Relationships", .. } => break,
            Event::Eof => return Err(Decline("unterminated Relationships")),
            _ => {}
        }
    }
    let target = target.ok_or(Decline("no officeDocument relationship"))?;
    let folder = target.rfind('/').map_or("", |i| &target[..=i]);
    Ok(folder.strip_prefix('/').unwrap_or(folder).to_string())
}

/// Tampons réutilisés d'une chaîne à l'autre / buffers reused from one string to the next.
#[derive(Default)]
pub(crate) struct StringBuffers {
    text: String,
    element: Vec<u8>,
}

/// Chaîne simple ou riche jusqu'à la fermeture `closing` (`read_string_with_bufs`) : les textes `<t>` hors
/// phonétique (`<rPh>`), bout à bout ; jamais absente, au pire vide. Plain or rich string up to `closing`: the
/// `<t>` texts outside phonetic runs, concatenated; never absent, at worst empty.
pub(crate) fn read_string(
    xml: &mut Reader<'_>,
    closing: &[u8],
    out: &mut String,
    buffers: &mut StringBuffers,
) -> Result<()> {
    let mut phonetic = false;
    loop {
        match xml.next()? {
            Event::Start { local: b"rPh", .. } => phonetic = true,
            Event::End { name, .. } if name == closing => return Ok(()),
            Event::End { local: b"rPh", .. } => phonetic = false,
            Event::Start { name, local: b"t", attrs } if !phonetic => {
                let preserve = attrs.get(b"xml:space") == Some(b"preserve".as_slice());
                buffers.element.clear();
                buffers.element.extend_from_slice(name);
                buffers.text.clear();
                loop {
                    match xml.next()? {
                        Event::Text(raw) => push_text(raw, &mut buffers.text)?,
                        Event::Ref(reference) => reference.push_to(&mut buffers.text),
                        Event::End { name, .. } if name == buffers.element.as_slice() => break,
                        Event::Eof => return Err(Decline("unterminated t")),
                        _ => {}
                    }
                }
                // Blancs ASCII rognés sauf `xml:space="preserve"` ; les espaces insécables restent.
                // ASCII whitespace trimmed unless preserved; non-breaking spaces stay.
                let text = &buffers.text;
                let value = if preserve { text.as_str() } else { text.trim_matches([' ', '\t', '\r', '\n']) };
                unescape_excel(value, out);
            }
            Event::Eof => return Err(Decline("unterminated string")),
            _ => {}
        }
    }
}

/// Échappements Excel `_x00HH_` (`unescape_xml` de calamine) / Excel `_x00HH_` escapes.
pub(crate) fn unescape_excel(value: &str, out: &mut String) {
    // Le plus souvent, aucun `_` : copie directe / most often no `_` at all: plain copy.
    if memchr::memchr(b'_', value.as_bytes()).is_none() || !value.contains("_x00") {
        out.push_str(value);
        return;
    }
    let bytes = value.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if i + 7 <= bytes.len() && bytes[i..i + 4] == *b"_x00" && bytes[i + 6] == b'_' {
            // `u8::from_str_radix` accepte un `+` initial, comme calamine / accepts a leading `+`, as calamine.
            let parsed =
                std::str::from_utf8(&bytes[i + 4..i + 6]).ok().and_then(|hex| u8::from_str_radix(hex, 16).ok());
            if let Some(code) = parsed {
                out.push(code as char);
                i += 7;
                continue;
            }
        }
        match value[i..].chars().next() {
            Some(c) => {
                out.push(c);
                i += c.len_utf8();
            }
            None => break,
        }
    }
}

/// `sharedStrings.xml` (`read_shared_strings`) ; absente : aucune chaîne / absent: no string.
fn shared_strings(directory: &Directory, data: &[u8]) -> Result<Vec<Box<str>>> {
    let Some(mut xml) = part(directory, data, &format!("{XL_PATH}sharedStrings.xml"))? else { return Ok(Vec::new()) };
    loop {
        match xml.next()? {
            Event::Start { local: b"sst", .. } => break,
            Event::Eof => return Err(Decline("no sst element")),
            _ => {}
        }
    }
    let mut strings = Vec::new();
    let (mut text, mut closing, mut buffers) = (String::new(), Vec::new(), StringBuffers::default());
    loop {
        match xml.next()? {
            Event::Start { name, local: b"si", .. } => {
                closing.clear();
                closing.extend_from_slice(name);
                text.clear();
                read_string(&mut xml, &closing, &mut text, &mut buffers)?;
                strings.push(text.as_str().into());
            }
            Event::End { local: b"sst", .. } => break,
            Event::Eof => return Err(Decline("unterminated sst")),
            _ => {}
        }
    }
    Ok(strings)
}

/// `styles.xml` (`read_styles`) : format de chaque style de cellule / number format of each cell style.
fn styles(directory: &Directory, data: &[u8]) -> Result<Vec<CellFormat>> {
    let Some(mut xml) = part(directory, data, &format!("{XL_PATH}styles.xml"))? else { return Ok(Vec::new()) };
    let mut number_formats: HashMap<Vec<u8>, String> = HashMap::new();
    let mut formats = Vec::new();
    loop {
        match xml.next()? {
            Event::Start { local: b"numFmts", .. } => loop {
                match xml.next()? {
                    Event::Start { local: b"numFmt", attrs, .. } => {
                        if let [Some(id), Some(code)] = attrs.get_many([b"numFmtId", b"formatCode"]) {
                            let code = decode(code)?;
                            number_formats.insert(id.to_vec(), code);
                        }
                    }
                    Event::End { local: b"numFmts", .. } => break,
                    Event::Eof => return Err(Decline("unterminated numFmts")),
                    _ => {}
                }
            },
            Event::Start { local: b"cellXfs", .. } => loop {
                match xml.next()? {
                    Event::Start { local: b"xf", attrs, .. } => {
                        formats.push(match attrs.get(b"numFmtId") {
                            None => CellFormat::Other,
                            Some(id) => match number_formats.get(id) {
                                Some(code) => custom_format(code),
                                None => builtin_format(id),
                            },
                        });
                    }
                    Event::End { local: b"cellXfs", .. } => break,
                    Event::Eof => return Err(Decline("unterminated cellXfs")),
                    _ => {}
                }
            },
            Event::End { local: b"styleSheet", .. } => break,
            Event::Eof => return Err(Decline("unterminated styleSheet")),
            _ => {}
        }
    }
    Ok(formats)
}

/// Format intégré d'après son identifiant brut (`builtin_format_by_id`) / builtin format from its raw id.
fn builtin_format(id: &[u8]) -> CellFormat {
    match id {
        b"14" | b"15" | b"16" | b"17" | b"18" | b"19" | b"20" | b"21" | b"22" | b"45" | b"47" => CellFormat::DateTime,
        b"46" => CellFormat::TimeDelta,
        _ => CellFormat::Other,
    }
}

/// Format personnalisé : date, durée ou autre (`detect_custom_number_format`) / custom format detection.
pub(crate) fn custom_format(format: &str) -> CellFormat {
    let mut escaped = false;
    let mut is_quote = false;
    let mut brackets = 0u8;
    let mut prev = ' ';
    let mut hms = false;
    let mut ap = false;
    for s in format.chars() {
        match (s, escaped, is_quote, ap, brackets) {
            (_, true, ..) => escaped = false,
            ('_' | '\\' | '*', ..) => escaped = true,
            ('"', _, true, _, _) => is_quote = false,
            (_, _, true, _, _) => (),
            ('"', _, _, _, _) => is_quote = true,
            (';', ..) => return CellFormat::Other,
            ('[', ..) => brackets = brackets.wrapping_add(1),
            (']', .., 1) if hms => return CellFormat::TimeDelta,
            (']', ..) => brackets = brackets.saturating_sub(1),
            ('a' | 'A', _, _, false, 0) => ap = true,
            ('p' | 'm' | '/' | 'P' | 'M', _, _, true, 0) => return CellFormat::DateTime,
            ('d' | 'm' | 'h' | 'y' | 's' | 'D' | 'M' | 'H' | 'Y' | 'S', _, _, false, 0) => {
                return CellFormat::DateTime;
            }
            _ => {
                if !(hms && s.eq_ignore_ascii_case(&prev)) {
                    hms = prev == '[' && matches!(s, 'm' | 'h' | 's' | 'M' | 'H' | 'S');
                }
            }
        }
        prev = s;
    }
    CellFormat::Other
}

/// `xl/_rels/workbook.xml.rels` : identifiant brut -> (cible, type) / raw id -> (target, type).
fn workbook_relationships(directory: &Directory, data: &[u8]) -> Result<HashMap<Vec<u8>, (String, String)>> {
    let path = format!("{XL_PATH}_rels/workbook.xml.rels");
    let mut xml = part(directory, data, &path)?.ok_or(Decline("missing workbook relationships"))?;
    let mut relationships = HashMap::new();
    loop {
        match xml.next()? {
            Event::Start { local: b"Relationship", attrs, .. } => {
                let [id, kind, target] = attrs.get_many([b"Id", b"Type", b"Target"]);
                if let Some(id) = id {
                    let kind = kind.map(utf8).transpose()?.unwrap_or_default().to_string();
                    let target = target.map(utf8).transpose()?.unwrap_or_default().to_string();
                    relationships.insert(id.to_vec(), (target, kind));
                }
            }
            Event::End { local: b"Relationships", .. } => break,
            Event::Eof => return Err(Decline("unterminated Relationships")),
            _ => {}
        }
    }
    Ok(relationships)
}

/// L'attribut porte-t-il ce nom local, préfixe ignoré (`local_name_matches`) / local attribute name match.
fn key_is(key: &[u8], name: &[u8]) -> bool {
    key == name || key.strip_suffix(name).is_some_and(|prefix| prefix.last() == Some(&b':'))
}

/// `workbook.xml` (`read_workbook`) : feuilles dans l'ordre, système 1904 / sheets in order, 1904 system.
fn workbook(
    directory: &Directory,
    data: &[u8],
    relationships: &HashMap<Vec<u8>, (String, String)>,
) -> Result<(Vec<Sheet>, bool)> {
    let mut sheets = Vec::new();
    let mut is_1904 = false;
    let Some(mut xml) = part(directory, data, &format!("{XL_PATH}workbook.xml"))? else { return Ok((sheets, false)) };
    let mut scratch = String::new();
    loop {
        match xml.next()? {
            Event::Start { local: b"sheet", attrs, .. } => {
                let mut sheet_name = String::new();
                let mut rel_id: &[u8] = b"";
                let mut visibility = Visibility::Visible;
                for (key, value) in attrs.iter() {
                    match key {
                        b"name" => sheet_name = decode(value)?,
                        b"state" => {
                            visibility = match value {
                                b"visible" => Visibility::Visible,
                                b"hidden" => Visibility::Hidden,
                                b"veryHidden" => Visibility::VeryHidden,
                                _ => return Err(Decline("unrecognized sheet state")),
                            }
                        }
                        key if key_is(key, b"id") => rel_id = value,
                        _ => {}
                    }
                }
                let (target, kind) = relationships.get(rel_id).ok_or(Decline("sheet relationship not found"))?;
                let path = match target.strip_prefix('/') {
                    Some(absolute) => absolute.to_string(),
                    None => format!("{XL_PATH}{target}"),
                };
                let kind = match kind.rsplit('/').next() {
                    Some("worksheet") => SheetKind::Work,
                    Some("chartsheet") => SheetKind::Chart,
                    Some("dialogsheet") => SheetKind::Dialog,
                    _ => return Err(Decline("unrecognized sheet type")),
                };
                sheets.push(Sheet { name: sheet_name, path, kind, visibility });
            }
            Event::Start { local: b"workbookPr", attrs, .. } => {
                is_1904 = attrs.get(b"date1904").is_some_and(|v| v == b"1" || v == b"true");
            }
            Event::Start { name, local: b"definedName", attrs } => {
                if let Some(value) = attrs.get(b"name") {
                    decode(value)?;
                    let element = name.to_vec();
                    scratch.clear();
                    loop {
                        match xml.next()? {
                            Event::Text(raw) => push_text(raw, &mut scratch)?,
                            Event::End { name, .. } if name == element.as_slice() => break,
                            Event::Eof => return Err(Decline("unterminated workbook")),
                            _ => {}
                        }
                    }
                }
            }
            Event::End { local: b"workbook", .. } => break,
            Event::Eof => return Err(Decline("unterminated workbook")),
            _ => {}
        }
    }
    Ok((sheets, is_1904))
}
