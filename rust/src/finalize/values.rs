//! Propagation universelle des valeurs (1.0.2, `engine._propagate_values`).
//!
//! Universal value propagation: every personal value found is masked everywhere, in every written variant, with the
//! same tag (the occurrence inherits its source's value). Familles / families : noms de plusieurs mots repliés,
//! dates de naissance (formes générées depuis la date ISO), téléphones (numéro national de 9 chiffres), codes
//! (squelette alphanumérique). Rien n'est conservé après l'appel / nothing outlives the call.

use std::cmp::Reverse;
use std::collections::HashSet;
use std::sync::Arc;

use aho_corasick::{AhoCorasick, MatchKind};
use memchr::memmem::Finder;

use super::chars::{Chars, ALNUM, SPACE};
use super::indexed::IndexedText;
use super::propagate::{longest_matches, place_all, propagated_span, Segments};
use super::span::Span;
use super::Unsupported;

/// `engine._SKELETON_ENTITIES`.
const SKELETON_ENTITIES: &[&str] = &[
    "ID",
    "NATIONAL_ID",
    "ID_CARD",
    "BANK_ACCOUNT",
    "PLATE",
    "TAX_ID",
    "SOCIAL_ID",
    "HEALTH_ID",
    "PASSPORT",
    "DRIVER_LICENSE",
    "RESIDENCE_PERMIT",
    "STUDENT_ID",
    "IBAN",
    "IP",
    "MAC",
    "CARD",
    "IMEI",
    "CRYPTO",
    "SECRET",
    "HANDLE",
];
const SKELETON_MIN: usize = 6;
const DIGITS_MIN: usize = 9;
const CODE_GAP: &[char] = &[' ', '-', '.', '/', '_'];
const PHONE_GAP: &[char] = &[' ', '-', '.', '/', '_', '(', ')'];
const PHONE_PREFIXES: &[&str] = &["00330", "0033", "330", "33", "0", ""];
/// `engine._MONTH_NAMES` : nom complet puis abréviations, repliés / full name then abbreviations, folded.
const MONTH_NAMES: [&[&str]; 12] = [
    &["janvier", "janv"],
    &["fevrier", "fevr", "fev"],
    &["mars"],
    &["avril", "avr"],
    &["mai"],
    &["juin"],
    &["juillet", "juil"],
    &["aout"],
    &["septembre", "sept"],
    &["octobre", "oct"],
    &["novembre", "nov"],
    &["decembre", "dec"],
];

/// Zone source d'une famille, figée à la lecture / a family's source span, frozen when read.
struct Source {
    entity: Arc<str>,
    label: Arc<str>,
    source: Arc<str>,
    score: f64,
    value: Option<String>,
}

/// Formes d'une famille dans l'ordre d'insertion, la première zone l'emporte (`dict.setdefault`).
/// A family's forms in insertion order; the first span wins.
#[derive(Default)]
struct Table {
    keys: Vec<String>,
    owners: Vec<usize>,
    seen: HashSet<String>,
}

impl Table {
    fn add(&mut self, key: String, owner: usize) {
        if self.seen.insert(key.clone()) {
            self.keys.push(key);
            self.owners.push(owner);
        }
    }
}

/// `engine._skeleton_of` : lettres ASCII et chiffres du texte replié / ASCII letters and digits, folded.
fn skeleton_of(chars: &Chars, text: &str) -> String {
    chars.folded(text).filter(|c| c.is_ascii_digit() || c.is_ascii_lowercase()).collect()
}

/// `engine._national_number`.
fn national_number(skeleton: &str) -> Option<String> {
    if skeleton.is_empty() || !skeleton.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    let mut rest = skeleton;
    for prefix in ["0033", "33"] {
        if let Some(tail) = rest.strip_prefix(prefix) {
            if tail.len() == 9 || tail.len() == 10 {
                rest = tail;
                break;
            }
        }
    }
    if rest.len() == 10 && rest.starts_with('0') {
        rest = &rest[1..];
    }
    (rest.len() == 9 && !rest.starts_with('0')).then(|| rest.to_owned())
}

/// Nombre de chiffres ASCII à partir de `at` / ASCII digits from `at`.
fn digits(bytes: &[u8], at: usize) -> usize {
    bytes.get(at..).map_or(0, |rest| rest.iter().take_while(|b| b.is_ascii_digit()).count())
}

/// `_ISO_DATE_RE` : `([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})` en entier / full match.
fn parse_iso(b: &[u8]) -> Option<(usize, usize, usize)> {
    if digits(b, 0) != 4 || b.get(4) != Some(&b'-') {
        return None;
    }
    let m = digits(b, 5);
    if !(1..=2).contains(&m) || b.get(5 + m) != Some(&b'-') {
        return None;
    }
    let d = digits(b, 6 + m);
    ((1..=2).contains(&d) && 6 + m + d == b.len()).then_some((0, 5, 6 + m))
}

/// `_DMY_DATE_RE` : `([0-9]{1,2})[/.\- ]([0-9]{1,2})[/.\- ]([0-9]{4})` en entier ; (jour, mois, année).
fn parse_dmy(b: &[u8]) -> Option<(usize, usize, usize)> {
    let sep = |at: usize| b.get(at).is_some_and(|c| b"/.- ".contains(c));
    let d = digits(b, 0);
    if !(1..=2).contains(&d) || !sep(d) {
        return None;
    }
    let m = digits(b, d + 1);
    if !(1..=2).contains(&m) || !sep(d + 1 + m) {
        return None;
    }
    let year = d + 2 + m;
    (digits(b, year) == 4 && year + 4 == b.len()).then_some((0, d + 1, year))
}

/// `_TEXT_DATE_RE` : `([0-9]{1,2})(?:er)? ([a-z]+)\.? ([0-9]{4})` en entier ; (jour, mois 1-12, début de l'année).
fn parse_text(b: &[u8]) -> Option<(usize, usize, usize)> {
    let d = digits(b, 0);
    if !(1..=2).contains(&d) {
        return None;
    }
    let mut i = d;
    if b.get(i..i + 3) == Some(b"er ") {
        i += 2;
    }
    if b.get(i) != Some(&b' ') {
        return None;
    }
    let name_start = i + 1;
    let name_len = b.get(name_start..).map_or(0, |rest| rest.iter().take_while(|c| c.is_ascii_lowercase()).count());
    if name_len == 0 {
        return None;
    }
    let mut j = name_start + name_len;
    if b.get(j) == Some(&b'.') {
        j += 1;
    }
    if b.get(j) != Some(&b' ') || digits(b, j + 1) != 4 || j + 5 != b.len() {
        return None;
    }
    let name = std::str::from_utf8(&b[name_start..name_start + name_len]).ok()?;
    let month = MONTH_NAMES.iter().position(|names| names.contains(&name))? + 1;
    Some((0, month, j + 1))
}

/// `engine._iso_date` : date ISO d'une date de naissance écrite / ISO date of a written birth date.
fn iso_date(chars: &Chars, value: &str) -> Option<String> {
    let folded = chars.fold(value);
    let flat = folded.split(|c: char| chars.is(c, SPACE)).filter(|w| !w.is_empty()).collect::<Vec<_>>().join(" ");
    let b = flat.as_bytes();
    let number =
        |from: usize, len: usize| -> Option<usize> { std::str::from_utf8(b.get(from..from + len)?).ok()?.parse().ok() };
    let (day, month, year) = if let Some((year, month, day)) = parse_iso(b) {
        let m = digits(b, month);
        (number(day, digits(b, day))?, number(month, m)?, year)
    } else if let Some((day, month, year)) = parse_dmy(b) {
        (number(day, digits(b, day))?, number(month, digits(b, month))?, year)
    } else {
        let (day, month, year) = parse_text(b)?;
        (number(day, digits(b, day))?, month, year)
    };
    if !(1..=31).contains(&day) || !(1..=12).contains(&month) {
        return None;
    }
    let year = std::str::from_utf8(b.get(year..year + 4)?).ok()?;
    Some(format!("{year}-{month:02}-{day:02}"))
}

/// `list(dict.fromkeys(...))`.
fn unique(items: Vec<String>) -> Vec<String> {
    let mut seen = HashSet::new();
    items.into_iter().filter(|item| seen.insert(item.clone())).collect()
}

/// `engine._date_forms` : graphies repliées d'une date ISO / folded written forms of an ISO date.
fn date_forms(iso: &str) -> Vec<String> {
    let (Some(year), Some(Ok(month)), Some(Ok(day))) =
        (iso.get(..4), iso.get(5..7).map(str::parse::<usize>), iso.get(8..10).map(str::parse::<usize>))
    else {
        return Vec::new();
    };
    let days = unique(vec![day.to_string(), format!("{day:02}")]);
    let months = unique(vec![month.to_string(), format!("{month:02}")]);
    let mut forms = Vec::new();
    for sep in ['/', '.', '-'] {
        for dd in &days {
            for mm in &months {
                forms.push(format!("{dd}{sep}{mm}{sep}{year}"));
            }
        }
    }
    forms.push(iso.to_owned());
    let mut words = days.clone();
    if day == 1 {
        words.push("1er".to_owned());
    }
    for (k, name) in MONTH_NAMES.get(month.wrapping_sub(1)).copied().unwrap_or_default().iter().enumerate() {
        for dd in &words {
            forms.push(format!("{dd} {name} {year}"));
            if k > 0 {
                forms.push(format!("{dd} {name}. {year}"));
            }
        }
    }
    unique(forms)
}

/// `engine._skeleton_hits` : occurrences de `key` dans le squelette, en positions du texte / as text positions.
#[allow(clippy::too_many_arguments)]
fn skeleton_hits(
    chars: &Chars,
    text: &IndexedText,
    folded: &[char],
    skeleton: &[u8],
    positions: &[usize],
    key: &[u8],
    phone: bool,
    occurrences: &[usize],
) -> Vec<(usize, usize)> {
    let gaps = if phone { PHONE_GAP } else { CODE_GAP };
    let linked = |k: usize| {
        let (p, q) = (positions[k], positions[k + 1]);
        q - p - 1 <= 2 && folded[p + 1..q].iter().all(|c| gaps.contains(c))
    };
    let alnum = |i: usize| text.char_at(i).is_some_and(|c| chars.is(c, ALNUM));
    let digit = |k: usize| skeleton[k].is_ascii_digit();
    let start_ok = |s: usize| {
        let p = positions[s];
        if p > 0 && alnum(p - 1) {
            return false;
        }
        !(s > 0 && digit(s) && digit(s - 1) && linked(s - 1))
    };
    let end_ok = |j: usize| {
        if alnum(positions[j - 1] + 1) {
            return false;
        }
        !(j < skeleton.len() && digit(j - 1) && digit(j) && linked(j - 1))
    };
    let mut hits = Vec::new();
    // Après une occurrence retenue, la suivante commence au-delà / after a hit, the next one starts past it.
    let mut free = 0;
    for &i in occurrences {
        if i < free {
            continue;
        }
        let j = i + key.len();
        let mut first = None;
        if (i..j - 1).all(linked) && end_ok(j) {
            if phone {
                first = PHONE_PREFIXES.iter().find_map(|prefix| {
                    let s = i.checked_sub(prefix.len())?;
                    (&skeleton[s..i] == prefix.as_bytes() && (s..i).all(linked) && start_ok(s)).then_some(s)
                });
            } else if start_ok(i) {
                first = Some(i);
            }
        }
        let Some(first) = first else {
            continue;
        };
        let mut begin = positions[first];
        if phone && begin > 0 && text.char_at(begin - 1) == Some('+') {
            begin -= 1;
        }
        hits.push((begin, positions[j - 1] + 1));
        free = j;
    }
    hits
}

/// `engine._AUTOMATON_KEYS`.
const AUTOMATON_KEYS: usize = 8;

/// `engine._all_occurrences` : débuts de toutes les occurrences (chevauchantes comprises) de chaque clé,
/// croissants ; un automate au-delà de 8 clés, sinon une recherche par clé (même résultat). Starts of every
/// occurrence of each key, increasing; an automaton beyond 8 keys, else one search per key (same result).
fn all_occurrences(keys: &[String], haystack: &[u8]) -> Result<Vec<Vec<usize>>, Unsupported> {
    let mut starts: Vec<Vec<usize>> = vec![Vec::new(); keys.len()];
    if keys.len() > AUTOMATON_KEYS {
        let automaton = AhoCorasick::builder()
            .match_kind(MatchKind::Standard)
            .build(keys.iter().map(String::as_bytes))
            .map_err(|_| Unsupported)?;
        for found in automaton.find_overlapping_iter(haystack) {
            if let Some(list) = starts.get_mut(found.pattern().as_usize()) {
                list.push(found.start());
            }
        }
        starts.iter_mut().for_each(|list| list.sort_unstable());
        return Ok(starts);
    }
    for (key, list) in keys.iter().zip(starts.iter_mut()) {
        let finder = Finder::new(key.as_bytes());
        let mut from = 0;
        while let Some(at) = haystack.get(from..).and_then(|rest| finder.find(rest)) {
            list.push(from + at);
            from += at + 1;
        }
    }
    Ok(starts)
}

/// `engine._propagate_values` : `spans` triées par début et disjointes ; le résultat l'est aussi.
/// `spans` sorted by start and disjoint; so is the result.
// L'index sert aussi à réécrire la valeur ISO d'une date après l'emprunt de la zone / the index also rewrites a
// date's ISO value once the span's borrow ends.
#[allow(clippy::needless_range_loop)]
pub fn propagate_values(
    chars: &Chars,
    text: &IndexedText,
    mut spans: Vec<Span>,
    segments: Option<&Segments>,
    priority: i64,
) -> Result<Vec<Span>, Unsupported> {
    let (mut names, mut dates, mut phones, mut codes) =
        (Table::default(), Table::default(), Table::default(), Table::default());
    let mut sources: Vec<Source> = Vec::new();
    for index in 0..spans.len() {
        let span = &spans[index];
        if !span.personal {
            continue;
        }
        let surface = text.slice(span.start, span.end);
        let entity = span.entity.clone();
        let mut source = |value: Option<String>, span: &Span| {
            sources.push(Source {
                entity: span.entity.clone(),
                label: span.label.clone(),
                source: format!("propagated:{}", span.source).into(),
                score: span.score,
                value,
            });
            sources.len() - 1
        };
        match &*entity {
            "PERSON" => {
                if !span.propagate {
                    continue;
                }
                let forms: Vec<&str> = std::iter::once(surface).chain(span.forms.iter().map(|f| &**f)).collect();
                for form in forms {
                    let form = chars.strip(form);
                    if form.contains(' ') && !form.contains('\n') && form.chars().count() >= 5 {
                        let key = chars.fold(form);
                        if !names.seen.contains(&key) {
                            let owner = source(Some(form.to_owned()), span);
                            names.add(key, owner);
                        }
                    }
                }
            }
            "BIRTH_DATE" => {
                let iso = span.value.as_deref().and_then(|v| iso_date(chars, v)).or_else(|| iso_date(chars, surface));
                if let Some(iso) = iso {
                    let owner = source(Some(iso.clone()), span);
                    for form in date_forms(&iso) {
                        dates.add(form, owner);
                    }
                    spans[index].value = Some(iso);
                }
            }
            "PHONE" => {
                if let Some(national) = national_number(&skeleton_of(chars, surface)) {
                    if !phones.seen.contains(&national) {
                        let value = span.value.clone().unwrap_or_else(|| surface.to_owned());
                        let owner = source(Some(value), span);
                        phones.add(national, owner);
                    }
                }
            }
            entity if SKELETON_ENTITIES.contains(&entity) => {
                let key = skeleton_of(chars, surface);
                let count = key.bytes().filter(u8::is_ascii_digit).count();
                let long = if count < key.len() { key.len() >= SKELETON_MIN } else { key.len() >= DIGITS_MIN };
                if count > 0 && long && !codes.seen.contains(&key) {
                    let value = span.value.clone().unwrap_or_else(|| surface.to_owned());
                    let owner = source(Some(value), span);
                    codes.add(key, owner);
                }
            }
            _ => {}
        }
    }
    if names.keys.is_empty() && dates.keys.is_empty() && phones.keys.is_empty() && codes.keys.is_empty() {
        return Ok(spans);
    }
    let candidate = |owner: usize, start: usize, end: usize| {
        let source = &sources[owner];
        let template = Span {
            start,
            end,
            entity: source.entity.clone(),
            label: source.label.clone(),
            source: source.source.clone(),
            score: source.score,
            priority,
            value: None,
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: None,
            origin: None,
        };
        propagated_span(&template, source.source.clone(), start, end, source.value.clone(), priority)
    };
    let alnum = |c: Option<char>| c.is_some_and(|c| chars.is(c, ALNUM));
    if !(names.keys.is_empty() && dates.keys.is_empty()) {
        let folded = chars.fold(text.as_str());
        let index = IndexedText::new(&folded).ok_or(Unsupported)?;
        for table in [&names, &dates] {
            if table.keys.is_empty() {
                continue;
            }
            let mut found = Vec::new();
            for (key, start_byte, end_byte) in longest_matches(&table.keys, &folded)? {
                let (start, end) = (index.char_index(start_byte), index.char_index(end_byte));
                if (start > 0 && alnum(text.char_at(start - 1))) || alnum(text.char_at(end)) {
                    continue;
                }
                found.push(candidate(table.owners[key], start, end));
            }
            spans = place_all(spans, found, segments);
        }
    }
    if !(phones.keys.is_empty() && codes.keys.is_empty()) {
        let folded: Vec<char> = chars.folded(text.as_str()).collect();
        let mut skeleton: Vec<u8> = Vec::new();
        let mut positions: Vec<usize> = Vec::new();
        for (i, &c) in folded.iter().enumerate() {
            if c.is_ascii_digit() || c.is_ascii_lowercase() {
                skeleton.push(c as u8);
                positions.push(i);
            }
        }
        for (table, phone) in [(&phones, true), (&codes, false)] {
            if table.keys.is_empty() {
                continue;
            }
            let mut hits: Vec<(usize, usize, usize)> = Vec::new();
            let occurrences = all_occurrences(&table.keys, &skeleton)?;
            for (order, (key, found)) in table.keys.iter().zip(&occurrences).enumerate() {
                let found = skeleton_hits(chars, text, &folded, &skeleton, &positions, key.as_bytes(), phone, found);
                hits.extend(found.into_iter().map(|(start, end)| (start, end, order)));
            }
            hits.sort_by_key(|&(start, end, order)| (start, Reverse(end - start), order));
            let mut last = 0;
            let mut found = Vec::new();
            for (start, end, order) in hits {
                if start < last {
                    continue;
                }
                last = end;
                found.push(candidate(table.owners[order], start, end));
            }
            spans = place_all(spans, found, segments);
        }
    }
    Ok(spans)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dates_parse_and_expand() {
        assert_eq!(national_number("0612345678").as_deref(), Some("612345678"));
        assert_eq!(national_number("0033612345678").as_deref(), Some("612345678"));
        assert_eq!(national_number("330612345678").as_deref(), Some("612345678"));
        assert_eq!(national_number("1234"), None);
        assert_eq!(parse_iso(b"1985-03-12"), Some((0, 5, 8)));
        assert_eq!(parse_dmy(b"12/03/1985"), Some((0, 3, 6)));
        assert_eq!(parse_text(b"1er mars 1985"), Some((0, 3, 9)));
        let forms = date_forms("1985-03-01");
        assert!(forms.contains(&"1/3/1985".to_owned()) && forms.contains(&"1er mars 1985".to_owned()));
        assert!(forms.contains(&"01.03.1985".to_owned()) && forms.contains(&"1985-03-01".to_owned()));
    }
}
