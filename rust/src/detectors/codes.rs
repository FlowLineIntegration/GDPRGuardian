//! Codes d'identifiant du filtre fort 1.0.2 : jumeau de `detectors/codes.py` (règles `ID_CODE`, `ID_LONG_NUMBER`,
//! `SECRET_COOKIE`, REGLES.md § 2) / Rust twin of `detectors/codes.py`.
//!
//! Mêmes zones, mêmes valeurs, mêmes exclusions que Python, en positions de caractères Python : les jetons sont
//! ASCII (lus octet par octet), les voisins et les fenêtres d'exclusion suivent les classes de l'interpréteur
//! (`\w`, `str.isdigit`, `str.isspace`, `re.IGNORECASE` par la table Unicode du noyau). Les motifs d'exclusion
//! des jetons sont ceux de Python (envoyés par `native_plan`). Rien n'est gardé d'un appel à l'autre.
//! Same spans, values and exclusions as Python, in Python character offsets: tokens are ASCII (read byte by
//! byte); neighbours and exclusion windows follow the interpreter's classes through the core's Unicode table.
//! The token exclusion patterns are Python's own (sent by `native_plan`). Nothing is kept between calls.

use std::collections::HashSet;

use regex_automata::meta::Regex;

use crate::finalize::IndexedText;
use crate::unicode::Unicode;

/// Données de `codes.py`, lues une fois / `codes.py` data, read once.
pub(crate) struct CodeData {
    /// Motifs de `_EXCLUSIONS`, dans leur ordre / `_EXCLUSIONS` patterns, in order.
    pub exclusions: Vec<String>,
    pub short_list: Vec<String>,
    pub months: Vec<String>,
    /// Clés de `IBAN_LENGTHS` (pays d'un BIC) / `IBAN_LENGTHS` keys (a BIC's country).
    pub bic_countries: Vec<String>,
    /// `_COOKIE_ATTRIBUTES`.
    pub attributes: Vec<String>,
}

/// Règle d'une zone trouvée / rule of a found span.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub(crate) enum CodeKind {
    /// `ID_CODE`, raison `identifier_code`.
    Code,
    /// `ID_LONG_NUMBER`, raison `long_number`.
    LongNumber,
    /// `SECRET_COOKIE`, raison `keyword`.
    Cookie,
}

/// Zone trouvée, en positions de caractères Python, avec la valeur de Python / found span, Python's value.
pub(crate) struct CodeSpan {
    pub start: usize,
    pub end: usize,
    pub kind: CodeKind,
    pub value: String,
}

/// `LONG_NUMBER_MIN`.
const LONG_NUMBER_MIN: usize = 8;

/// `_AMOUNT_AFTER` : devises, puis unités, chacune suivie d'aucune lettre (`(?![A-Za-z])`).
const CURRENCY_LEADS: [&str; 5] = ["€", "$", "£", "%", "‰"];
const CURRENCY_PREFIXES: [&str; 4] = ["", "k", "m", "md"];
const CURRENCIES: [&str; 11] = ["€", "eur", "euro", "euros", "usd", "dollar", "dollars", "gbp", "chf", "xpf", "fcfa"];
const UNITS: [&str; 34] = [
    "km", "kg", "mg", "g", "cm", "mm", "m2", "m3", "m²", "m³", "m", "ml", "cl", "l", "t", "w", "kw", "kwh", "mw",
    "mwh", "v", "hz", "octet", "octets", "byte", "bytes", "ko", "mo", "go", "to", "kb", "mb", "gb", "tb",
];

/// Motifs de fenêtre de `codes.py`, sur la fenêtre normalisée (`normal`) : minuscules, sensibles à la casse.
/// `\Z` de Python devient `\z` ; `(?<![\w])` est vérifié à part, sur le texte d'origine.
/// `codes.py` window patterns, over the normalised window: lower case, case-sensitive. Python's `\Z` becomes
/// `\z`; `(?<![\w])` is checked apart, on the original text.
/// `_AMOUNT_BEFORE`, en deux : symboles, puis devises en lettres non précédées d'une lettre (`(?<![^\W\d_])`).
/// In two: symbols, then currencies in letters not preceded by a letter.
const AMOUNT_SYMBOL_BEFORE: &str = r"(?:€|\$|£)[ \t\x{a0}\x{202f}]?\z";
const AMOUNT_WORD_BEFORE: &str = r"^(?:eur|euros?|usd|gbp|chf)[ \t\x{a0}\x{202f}]?\z";
const DURATION_BEFORE: &str = r"max-age[ \t]*=[ \t]*\z";
const CLASSIFICATION_BEFORE: &str = r"^(?:cpv|naf|ape|nace|nuts|rome|nomenclature)(?:[ \t]+(?:principal|code|n[°o]\.?))?[ \t]*[:=#]?[ \t]*(?:\d+[ \t]*[,;/][ \t]*)*\z";
const PUBLICATION_BEFORE: &str = r"^(?:bodacc|balo|jorf|joafe|jo|bulletin(?:[ \t]+officiel)?|journal[ \t]+officiel)(?:[ \t]+[a-c])?[ \t]+(?:n[°o]\.?|num[ée]ro)[ \t]*:?[ \t]*\z";

/// Voie « codes » (1.0.2, dernier tour) : `_SPLIT_PREFIXED`, `_SPLIT_GROUPED` et `_SPLIT_STOP` de `codes.py` (mêmes
/// motifs, même liste) : code coupé par une espace ou une espace insécable. Same patterns and list as Python.
const SPLIT_PREFIXED: &str = r"[A-Z]{2,5}[ \x{a0}\x{202f}][0-9]{6,7}";
const SPLIT_GROUPED: &str = r"[A-Z0-9]{3,6}(?:[ \x{a0}\x{202f}][A-Z0-9]{3,6}){2,7}";
const SPLIT_GAPS: [char; 3] = [' ', '\u{a0}', '\u{202f}'];
const SPLIT_STOP: [&str; 45] = [
    "AN", "APE", "ART", "ARTS", "BALO", "BOAMP", "BODACC", "BP", "CEDEX", "CEI", "CHF", "CP", "CPV", "CS", "DIN",
    "ECLI", "EN", "EUR", "FR", "GBP", "IEC", "ISO", "JO", "JORF", "NACE", "NAF", "NF", "NO", "NOR", "NUM", "NUTS",
    "RCS", "RD", "RM", "RN", "RNA", "ROME", "RT", "SIREN", "SIRET", "TOME", "TSA", "TVA", "USD", "VOL",
];

/// `_split_glued` : code coupé collé à un mot ou à un signe de jeton / a split code glued to a word or a token sign.
fn split_glued(text: &str, start: usize, end: usize, table: &Unicode) -> bool {
    let before = text[..start].chars().next_back();
    let mut following = text[end..].chars();
    let (after, after2) = (following.next(), following.next());
    if before.is_some_and(|c| table.is_alnum(c) || "_@.-/#\\".contains(c)) {
        return true;
    }
    if after.is_some_and(|c| table.is_alnum(c) || "_@-/#\\".contains(c)) {
        return true;
    }
    matches!(after, Some('.' | ',')) && after2.is_some_and(|c| table.is_alnum(c))
}

fn regex(pattern: &str) -> Result<Regex, String> {
    Regex::new(pattern).map_err(|e| format!("motif de code invalide / invalid code pattern: {e}"))
}

pub(crate) struct CodeDetector {
    /// `^(?:motif)$` : `fullmatch` / `fullmatch`.
    exclusions: Vec<Regex>,
    short_list: HashSet<String>,
    months: Vec<String>,
    bic_countries: HashSet<String>,
    attributes: Vec<String>,
    amount_symbol_before: Regex,
    amount_word_before: Regex,
    duration_before: Regex,
    classification_before: Regex,
    publication_before: Regex,
    split_prefixed: Regex,
    split_grouped: Regex,
}

/// `[A-Za-z0-9]` de `_ALNUM` / `_ALNUM`.
#[inline]
fn alnum(b: u8) -> bool {
    b.is_ascii_alphanumeric()
}

/// `_token_start` : début du jeton `_TOKEN` qui contient l'octet `pos` (ASCII), mêmes coupures.
/// Start of the `_TOKEN` token holding byte `pos`, same breaks.
fn token_start(bytes: &[u8], mut pos: usize) -> usize {
    loop {
        while pos > 0 && alnum(bytes[pos - 1]) {
            pos -= 1;
        }
        if pos < 2 || !alnum(bytes[pos - 2]) {
            return pos;
        }
        let separator = bytes[pos - 1];
        let capitalised = bytes.get(pos).is_some_and(u8::is_ascii_uppercase)
            && bytes.get(pos + 1).is_some_and(u8::is_ascii_lowercase);
        let joined = matches!(separator, b'-' | b'_' | b'/' | b'#') || (separator == b'.' && !capitalised);
        if !joined {
            return pos;
        }
        pos -= 1;
    }
}

/// Fin de `_TOKEN.match(text, start)` : `[A-Za-z0-9]+(?:(?:[-_/]|\.(?![A-Z][a-z]))[A-Za-z0-9]+)*`.
fn token_end(bytes: &[u8], start: usize) -> usize {
    let run = |mut at: usize| {
        while at < bytes.len() && alnum(bytes[at]) {
            at += 1;
        }
        at
    };
    let mut end = run(start);
    loop {
        let Some(&separator) = bytes.get(end) else {
            return end;
        };
        let next = end + 1;
        let joins = match separator {
            b'-' | b'_' | b'/' | b'#' => true,
            b'.' => {
                !(bytes.get(next).is_some_and(u8::is_ascii_uppercase)
                    && bytes.get(next + 1).is_some_and(u8::is_ascii_lowercase))
            }
            _ => false,
        };
        if !joins || !bytes.get(next).is_some_and(|&b| alnum(b)) {
            return end;
        }
        end = run(next);
    }
}

/// Squelette d'un morceau : sans `-_/.#` / skeleton of a piece: without `-_/.#`.
fn skeleton(piece: &str) -> String {
    piece.chars().filter(|c| !matches!(c, '-' | '_' | '/' | '.' | '#')).collect()
}

/// `is_code` : une lettre, un chiffre, 6 caractères alphanumériques au moins (jeton ASCII).
fn is_code(skeleton: &str) -> bool {
    skeleton.len() >= 6
        && skeleton.bytes().all(alnum)
        && !skeleton.bytes().all(|b| b.is_ascii_digit())
        && !skeleton.bytes().all(|b| b.is_ascii_alphabetic())
}

/// `_PLACEHOLDER_TOKEN.fullmatch` : `[A-Z][A-Z0-9_]*_\d+` sur un jeton ASCII / on an ASCII token.
fn placeholder(token: &[u8]) -> bool {
    let digits = token.iter().rev().take_while(|b| b.is_ascii_digit()).count();
    let Some(underscore) = token.len().checked_sub(digits + 1) else {
        return false;
    };
    digits >= 1
        && underscore >= 1
        && token[underscore] == b'_'
        && token[0].is_ascii_uppercase()
        && token.iter().all(|&b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
}

/// `_compact_date` : AAAAMMJJ ou JJMMAAAA, ou horodatage AAAAMMJJhhmm(ss) / compact date or timestamp.
fn compact_date(run: &[u8]) -> bool {
    let number = |from: usize, to: usize| run[from..to].iter().fold(0u32, |n, &d| n * 10 + u32::from(d - b'0'));
    let valid = |year: u32, month: u32, day: u32| {
        (1800..=2199).contains(&year) && (1..=12).contains(&month) && (1..=31).contains(&day)
    };
    match run.len() {
        8 => valid(number(0, 4), number(4, 6), number(6, 8)) || valid(number(4, 8), number(2, 4), number(0, 2)),
        12 | 14 => {
            valid(number(0, 4), number(4, 6), number(6, 8))
                && number(8, 10) < 24
                && number(10, 12) < 60
                && (run.len() == 12 || number(12, 14) < 60)
        }
        _ => false,
    }
}

/// Caractère d'une fenêtre sous `re.IGNORECASE` : la lettre ASCII minuscule (ou « é ») qu'il égale pour `re`,
/// sinon lui-même. Seuls des littéraux minuscules ASCII, « é » et des signes sans casse figurent dans les motifs.
/// A window character under `re.IGNORECASE`: the ASCII lowercase letter (or "é") it equals for `re`, else
/// itself. The patterns only hold ASCII lowercase literals, "é" and caseless signs.
fn normal(table: &Unicode, c: char) -> char {
    if c.is_ascii() {
        return c.to_ascii_lowercase();
    }
    if let Some(letter) = ('a'..='z').find(|&letter| table.case_insensitive_eq(letter, c)) {
        return letter;
    }
    if table.case_insensitive_eq('é', c) {
        return 'é';
    }
    c
}

/// Fenêtre normalisée des `size` caractères avant l'octet `start`, positions d'octet de chacun dans la fenêtre,
/// caractères d'origine, et caractère d'avant la fenêtre (pour `(?<![\w])`).
/// Normalised window of the `size` characters before byte `start`, each one's byte offset in the window, the
/// original characters, and the character before the window (for `(?<![\w])`).
struct Window {
    normalised: String,
    offsets: Vec<usize>,
    originals: Vec<char>,
    before: Option<char>,
}

impl Window {
    fn before(text: &str, start: usize, size: usize, table: &Unicode) -> Self {
        let mut originals: Vec<char> = text[..start].chars().rev().take(size + 1).collect();
        originals.reverse();
        let before = if originals.len() > size { Some(originals.remove(0)) } else { None };
        let mut normalised = String::with_capacity(originals.len());
        let mut offsets = Vec::with_capacity(originals.len());
        for &c in &originals {
            offsets.push(normalised.len());
            normalised.push(normal(table, c));
        }
        Self { normalised, offsets, originals, before }
    }

    /// Un départ `p` de la fenêtre dont le caractère précédent n'est pas `refused` (`(?<![…])` de Python, qui voit
    /// avant la fenêtre), d'où `anchored` couvre la fin. A start `p` whose previous character is not `refused`
    /// (Python's look-behind, which sees before the window), from which `anchored` covers the end.
    fn matches_from_start(&self, anchored: &Regex, refused: impl Fn(char) -> bool) -> bool {
        (0..self.originals.len()).any(|p| {
            let previous = if p == 0 { self.before } else { self.originals.get(p - 1).copied() };
            !previous.is_some_and(&refused) && anchored.is_match(&self.normalised[self.offsets[p]..])
        })
    }
}

impl CodeDetector {
    pub(crate) fn new(data: CodeData) -> Result<Self, String> {
        let exclusions =
            data.exclusions.iter().map(|pattern| regex(&format!("^(?:{pattern})$"))).collect::<Result<Vec<_>, _>>()?;
        Ok(Self {
            exclusions,
            short_list: data.short_list.into_iter().collect(),
            months: data.months,
            bic_countries: data.bic_countries.into_iter().collect(),
            attributes: data.attributes,
            amount_symbol_before: regex(AMOUNT_SYMBOL_BEFORE)?,
            amount_word_before: regex(AMOUNT_WORD_BEFORE)?,
            duration_before: regex(DURATION_BEFORE)?,
            classification_before: regex(CLASSIFICATION_BEFORE)?,
            publication_before: regex(PUBLICATION_BEFORE)?,
            split_prefixed: regex(SPLIT_PREFIXED)?,
            split_grouped: regex(SPLIT_GROUPED)?,
        })
    }

    /// `split_code_spans` : codes coupés par une espace, après les jetons, triés dans l'ordre du texte.
    /// Split codes, after the tokens, sorted in text order.
    fn split_codes(&self, indexed: &IndexedText<'_>, table: &Unicode, spans: &mut Vec<CodeSpan>) {
        let text = indexed.as_str();
        let mut found: Vec<(usize, usize, String)> = Vec::new();
        for m in self.split_prefixed.find_iter(text) {
            let (start, end) = (m.start(), m.end());
            if split_glued(text, start, end, table) {
                continue;
            }
            let token = &text[start..end];
            let digits = token.bytes().rev().take_while(u8::is_ascii_digit).count();
            let prefix = token[..token.len() - digits].trim_end_matches(SPLIT_GAPS);
            if SPLIT_STOP.contains(&prefix) || self.long_number_excluded(text, end - digits, end, table) {
                continue;
            }
            found.push((start, end, format!("{prefix}{}", &token[token.len() - digits..])));
        }
        for m in self.split_grouped.find_iter(text) {
            let (start, end) = (m.start(), m.end());
            if split_glued(text, start, end, table) {
                continue;
            }
            let groups: Vec<&str> = text[start..end].split(SPLIT_GAPS).collect();
            let mixed = groups
                .iter()
                .filter(|g| g.bytes().any(|b| b.is_ascii_alphabetic()) && g.bytes().any(|b| b.is_ascii_digit()))
                .count();
            if mixed < 2 || SPLIT_STOP.contains(&groups[0]) {
                continue;
            }
            found.push((start, end, groups.concat()));
        }
        found.sort();
        for (start, end, value) in found {
            spans.push(CodeSpan {
                start: indexed.char_index(start),
                end: indexed.char_index(end),
                kind: CodeKind::Code,
                value,
            });
        }
    }

    /// `IdentifierCodeDetector.detect` : témoins d'abord, puis codes et longues suites, dans l'ordre du texte.
    /// Cookies first, then codes and long runs, in text order.
    pub(crate) fn detect(
        &self,
        text: &IndexedText<'_>,
        folded: &str,
        has_digit: bool,
        table: &Unicode,
    ) -> Vec<CodeSpan> {
        let mut spans = Vec::new();
        if folded.contains("cookie") {
            self.cookies(text, table, &mut spans);
        }
        if has_digit {
            self.codes(text, table, &mut spans);
        }
        spans
    }

    fn codes(&self, indexed: &IndexedText<'_>, table: &Unicode, spans: &mut Vec<CodeSpan>) {
        let text = indexed.as_str();
        let bytes = text.as_bytes();
        let mut pos = 0;
        while let Some(offset) = bytes.get(pos..).and_then(|rest| rest.iter().position(u8::is_ascii_digit)) {
            let start = token_start(bytes, pos + offset);
            let end = token_end(bytes, start);
            pos = end;
            if end - start < 6 {
                continue;
            }
            let before = text[..start].chars().next_back();
            let after = text[end..].chars().next();
            // Jamais collé à un mot ni à « @ » / never glued to a word or to "@".
            let glued = |c: Option<char>| c.is_some_and(|c| c == '@' || table.is_word(c));
            if glued(before) || glued(after) {
                continue;
            }
            let token = &text[start..end];
            if !token.bytes().any(|b| b.is_ascii_alphabetic()) {
                if end - start >= LONG_NUMBER_MIN
                    && token.bytes().all(|b| b.is_ascii_digit())
                    && !self.long_number_excluded(text, start, end, table)
                {
                    spans.push(CodeSpan {
                        start: indexed.char_index(start),
                        end: indexed.char_index(end),
                        kind: CodeKind::LongNumber,
                        value: token.to_owned(),
                    });
                }
                continue;
            }
            // Balise déjà produite : jamais relue comme un code / a produced tag is never read as a code.
            if before == Some('[') && after == Some(']') && placeholder(token.as_bytes()) {
                continue;
            }
            let pieces: Vec<(usize, &str)> = if token.contains('/') && token.contains('.') {
                let mut offset = start;
                token
                    .split('/')
                    .map(|piece| {
                        let at = offset;
                        offset += piece.len() + 1;
                        (at, piece)
                    })
                    .collect()
            } else {
                vec![(start, token)]
            };
            for (at, piece) in pieces {
                let skeleton = skeleton(piece);
                if is_code(&skeleton) && !self.excluded(piece, &skeleton) {
                    spans.push(CodeSpan {
                        start: indexed.char_index(at),
                        end: indexed.char_index(at + piece.len()),
                        kind: CodeKind::Code,
                        value: skeleton.to_ascii_uppercase(),
                    });
                }
            }
        }
        // Codes coupés par une espace, après les jetons (comme Python) / split codes, after the tokens.
        self.split_codes(indexed, table, spans);
    }

    /// `exclusion(piece) is not None` (morceau ASCII) / for an ASCII piece.
    fn excluded(&self, piece: &str, skeleton: &str) -> bool {
        if self.exclusions.iter().any(|pattern| pattern.is_match(piece)) {
            return true;
        }
        if self.short_list.contains(&skeleton.to_ascii_uppercase()) {
            return true;
        }
        // `_BIC` : [A-Z]{4}([A-Z]{2})[A-Z0-9]{2}(?:[A-Z0-9]{3})?, pays connu / known country.
        let b = piece.as_bytes();
        let bic = (b.len() == 8 || b.len() == 11)
            && b[..6].iter().all(u8::is_ascii_uppercase)
            && b[6..].iter().all(|c| c.is_ascii_uppercase() || c.is_ascii_digit())
            && self.bic_countries.contains(&piece[4..6]);
        if bic {
            return true;
        }
        let lowered = piece.to_ascii_lowercase();
        self.months.iter().any(|month| lowered.contains(month.as_str()))
    }

    /// `long_number_exclusion(...) is not None` pour les octets [start, end) d'une suite de chiffres ASCII.
    /// For the bytes [start, end) of an ASCII digit run.
    fn long_number_excluded(&self, text: &str, start: usize, end: usize, table: &Unicode) -> bool {
        let mut following = text[end..].chars();
        let (after, after2) = (following.next(), following.next());
        let mut preceding = text[..start].chars().rev();
        let (before, before2) = (preceding.next(), preceding.next());
        // Forme décimale ou de milliers / decimal or thousands form.
        let digit = |c: Option<char>| c.is_some_and(|c| table.is_digit(c));
        if (matches!(after, Some(',' | '.')) && digit(after2)) || (matches!(before, Some(',' | '.')) && digit(before2))
        {
            return true;
        }
        if self.amount_after(text, end, table) {
            return true;
        }
        let currency = Window::before(text, start, 6, table);
        if self.amount_symbol_before.is_match(currency.normalised.as_str())
            || currency.matches_from_start(&self.amount_word_before, |c| table.is_letter(c))
        {
            return true;
        }
        if compact_date(&text.as_bytes()[start..end]) {
            return true;
        }
        if self.duration_before.is_match(Window::before(text, start, 12, table).normalised.as_str()) {
            return true;
        }
        let word = |c: char| table.is_word(c);
        if Window::before(text, start, 24, table).matches_from_start(&self.classification_before, word) {
            return true;
        }
        Window::before(text, start, 30, table).matches_from_start(&self.publication_before, word)
    }

    /// `_AMOUNT_AFTER.match(text, end)` : espace facultative, puis une devise ou une unité non suivie d'une lettre.
    /// Optional space, then a currency or a unit not followed by a letter.
    fn amount_after(&self, text: &str, end: usize, table: &Unicode) -> bool {
        let mut chars: Vec<char> = text[end..].chars().take(12).map(|c| normal(table, c)).collect();
        if chars.first().is_some_and(|c| matches!(c, ' ' | '\t' | '\u{a0}' | '\u{202f}')) {
            chars.remove(0);
        }
        let rest: String = chars.iter().collect();
        if CURRENCY_LEADS.iter().any(|lead| rest.starts_with(lead)) {
            return true;
        }
        // `(?![A-Za-z])` sous `re.IGNORECASE` : la fenêtre normalisée n'a plus que des minuscules ASCII.
        let free = |length: usize| !rest[length..].chars().next().is_some_and(|c| c.is_ascii_lowercase());
        let currency = CURRENCY_PREFIXES.iter().any(|prefix| {
            rest.starts_with(prefix)
                && CURRENCIES
                    .iter()
                    .any(|name| rest[prefix.len()..].starts_with(name) && free(prefix.len() + name.len()))
        });
        currency || UNITS.iter().any(|unit| rest.starts_with(unit) && free(unit.len()))
    }

    /// `cookie_spans` : sur une ligne `Cookie:` ou `Set-Cookie:`, chaque valeur `nom=valeur` de 8 caractères ou
    /// plus, hors attributs. On a `Cookie:` or `Set-Cookie:` line, every value of 8 characters or more.
    fn cookies(&self, indexed: &IndexedText<'_>, table: &Unicode, spans: &mut Vec<CodeSpan>) {
        let text = indexed.as_str();
        let mut line_start = 0;
        for line in text.split('\n') {
            let begin = line_start;
            line_start += line.len() + 1;
            if let Some(value) = cookie_value(line, table) {
                self.pairs(indexed, begin + value, begin + line.len(), table, spans);
            }
        }
    }

    /// `_COOKIE_PAIR.finditer(text, from, to)` : `([^=;\s]+)[ \t]*=[ \t]*([^;\n]*)`.
    fn pairs(&self, indexed: &IndexedText<'_>, from: usize, to: usize, table: &Unicode, spans: &mut Vec<CodeSpan>) {
        let region = &indexed.as_str()[from..to];
        let chars: Vec<(usize, char)> = region.char_indices().collect();
        let byte = |k: usize| chars.get(k).map_or(region.len(), |&(b, _)| b);
        let name_char = |c: char| c != '=' && c != ';' && !table.is_space(c);
        let blank = |c: char| c == ' ' || c == '\t';
        let mut i = 0;
        while i < chars.len() {
            if !name_char(chars[i].1) {
                i += 1;
                continue;
            }
            let name_start = i;
            let mut q = i;
            while q < chars.len() && name_char(chars[q].1) {
                q += 1;
            }
            let mut r = q;
            while r < chars.len() && blank(chars[r].1) {
                r += 1;
            }
            if r >= chars.len() || chars[r].1 != '=' {
                // Aucun départ dans ce nom ne peut réussir / no start inside this name can succeed.
                i = q;
                continue;
            }
            let mut value_start = r + 1;
            while value_start < chars.len() && blank(chars[value_start].1) {
                value_start += 1;
            }
            let mut value_end = value_start;
            while value_end < chars.len() && chars[value_end].1 != ';' && chars[value_end].1 != '\n' {
                value_end += 1;
            }
            i = value_end;
            let name = &region[byte(name_start)..byte(q)];
            if self.attributes.iter().any(|attribute| name.eq_ignore_ascii_case(attribute)) {
                continue;
            }
            let mut end = value_end;
            while end > value_start && matches!(chars[end - 1].1, ' ' | '\t' | '\r') {
                end -= 1;
            }
            if end - value_start >= 8 {
                spans.push(CodeSpan {
                    start: indexed.char_index(from + byte(value_start)),
                    end: indexed.char_index(from + byte(end)),
                    kind: CodeKind::Cookie,
                    value: region[byte(value_start)..byte(end)].to_owned(),
                });
            }
        }
    }
}

/// `_COOKIE_LINE` (`(?im)^[ \t]*(?:set-)?cookie[ \t]*:[ \t]*([^\n]*)$`) sur une ligne : octet du groupe 1.
/// On one line: byte of group 1.
fn cookie_value(line: &str, table: &Unicode) -> Option<usize> {
    let first = line.trim_start_matches([' ', '\t']).chars().next()?;
    if first.is_ascii() && !matches!(first, 's' | 'S' | 'c' | 'C') {
        return None;
    }
    let chars: Vec<(usize, char)> = line.char_indices().collect();
    let blank = |c: char| c == ' ' || c == '\t';
    let literal = |at: usize, word: &str| -> Option<usize> {
        let mut k = at;
        for letter in word.chars() {
            let c = chars.get(k)?.1;
            if !table.case_insensitive_eq(letter, c) {
                return None;
            }
            k += 1;
        }
        Some(k)
    };
    let mut k = 0;
    while k < chars.len() && blank(chars[k].1) {
        k += 1;
    }
    let mut k = literal(k, "set-").and_then(|at| literal(at, "cookie")).or_else(|| literal(k, "cookie"))?;
    while k < chars.len() && blank(chars[k].1) {
        k += 1;
    }
    if chars.get(k)?.1 != ':' {
        return None;
    }
    k += 1;
    while k < chars.len() && blank(chars[k].1) {
        k += 1;
    }
    Some(chars.get(k).map_or(line.len(), |&(b, _)| b))
}

#[cfg(test)]
mod tests {
    use super::{compact_date, placeholder, token_end, token_start};

    #[test]
    fn tokens_break_like_python() {
        let text = b"voir CLT-204518.Le dossier AB12.cd/EF-9";
        let start = token_start(text, 9);
        assert_eq!(&text[start..token_end(text, start)], b"CLT-204518");
        let start = token_start(text, 30);
        assert_eq!(&text[start..token_end(text, start)], b"AB12.cd/EF-9");
    }

    #[test]
    fn placeholders_and_dates() {
        assert!(placeholder(b"IDENTIFIANT_12"));
        assert!(!placeholder(b"_12"));
        assert!(!placeholder(b"ID12"));
        assert!(compact_date(b"20260131"));
        assert!(compact_date(b"31012026"));
        assert!(!compact_date(b"12345678"));
    }
}
