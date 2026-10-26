//! Préparation du texte : normalisation, repliement et table des positions en un appel ; langue.
//!
//! Text preparation: normalisation, folding and offset map in one call; language.
//! Réplique exacte de `gdprguardian._text.normalize`/`fold` et de `gdprguardian.locale.detect_language`, construite
//! à partir des tables de Python (une seule source de vérité). Exact replica of those Python functions,
//! built from Python's own tables (a single source of truth).

use std::borrow::Cow;
use std::collections::HashMap;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyString};

use crate::text::{char_at, char_before, Classes, INVISIBLE, LETTER, LOWER};
use crate::unicode::PyUnicodeTables;

const BMP: usize = 0x10000;
const IDENTITY: u16 = u16::MAX;

/// Table caractère -> caractère de `str.translate`, en deux niveaux (blocs de 256 points du BMP, seuls les
/// blocs modifiés sont stockés) puis les points hors BMP. Character -> character table of `str.translate`,
/// two-level (256-point BMP blocks, only changed blocks stored), then points beyond the BMP.
struct CharMap {
    /// Cibles des caractères ASCII, lues octet par octet / targets of ASCII characters, read byte by byte.
    ascii: [char; 128],
    index: Vec<u16>,
    blocks: Vec<[char; 256]>,
    astral: Vec<(u32, char)>,
}

impl CharMap {
    /// `bmp` : table dense de Python encodée en UTF-32 LE (65 536 points) / Python's dense table, UTF-32 LE.
    fn new(bmp: &[u8], astral: &[(u32, u32)]) -> PyResult<Self> {
        let invalid = || PyValueError::new_err("table de transcodage invalide / invalid translation table");
        if bmp.len() != 4 * BMP {
            return Err(invalid());
        }
        let targets = bmp.as_chunks::<4>().0;
        Self::build(|cp| char::from_u32(u32::from_le_bytes(targets[cp as usize])).ok_or_else(invalid), astral)
    }

    /// `target(cp)` : cible de chaque point du BMP / the target of each BMP point.
    fn build(target: impl Fn(u32) -> PyResult<char>, astral: &[(u32, u32)]) -> PyResult<Self> {
        let invalid = || PyValueError::new_err("table de transcodage invalide / invalid translation table");
        let mut index = vec![IDENTITY; BMP / 256];
        let mut blocks = Vec::new();
        for (block, slot) in index.iter_mut().enumerate() {
            let mut entries = ['\0'; 256];
            let mut changed = false;
            for (low, entry) in entries.iter_mut().enumerate() {
                let source = (block * 256 + low) as u32;
                // Demi-codets (U+D800–U+DFFF) : absents d'un texte Rust / surrogates never occur in Rust text.
                let Some(source) = char::from_u32(source) else {
                    continue;
                };
                let target = target(u32::from(source))?;
                *entry = target;
                changed |= target != source;
            }
            if changed {
                *slot = blocks.len() as u16;
                blocks.push(entries);
            }
        }
        let mut astral: Vec<(u32, char)> = astral
            .iter()
            .map(|&(cp, target)| char::from_u32(target).map(|t| (cp, t)).ok_or_else(invalid))
            .collect::<PyResult<_>>()?;
        astral.sort_unstable();
        // Python applique la table hors BMP après la table dense : une cible hors BMP de celle-ci est
        // transcodée à son tour. Python applies the astral table after the dense one: an astral target of
        // the latter is translated in turn.
        for entry in blocks.iter_mut().flatten().filter(|entry| **entry as usize >= BMP) {
            *entry = astral_target(&astral, *entry);
        }
        let mut map = Self { ascii: ['\0'; 128], index, blocks, astral };
        map.ascii = std::array::from_fn(|b| map.map(char::from(b as u8)));
        Ok(map)
    }

    #[inline]
    fn map(&self, c: char) -> char {
        let cp = c as u32;
        if cp < BMP as u32 {
            match self.index[(cp >> 8) as usize] {
                IDENTITY => c,
                block => self.blocks[block as usize][(cp & 0xFF) as usize],
            }
        } else {
            astral_target(&self.astral, c)
        }
    }

    /// `str.translate` en un passage : les tronçons inchangés sont copiés d'un bloc, aucune copie si rien
    /// ne change. One pass: unchanged stretches are copied wholesale, no copy at all if nothing changes.
    fn translate<'a>(&self, text: &'a str) -> Cow<'a, str> {
        let bytes = text.as_bytes();
        let mut out: Option<String> = None;
        let (mut copied, mut i) = (0, 0);
        while i < bytes.len() {
            let (source, width) = match bytes[i] {
                b if b < 0x80 => (char::from(b), 1),
                _ => {
                    let c = text[i..].chars().next().unwrap_or(char::REPLACEMENT_CHARACTER);
                    (c, c.len_utf8())
                }
            };
            let target = if width == 1 { self.ascii[bytes[i] as usize] } else { self.map(source) };
            if target != source {
                let out = out.get_or_insert_with(|| String::with_capacity(text.len()));
                out.push_str(&text[copied..i]);
                out.push(target);
                copied = i + width;
            }
            i += width;
        }
        match out {
            None => Cow::Borrowed(text),
            Some(mut out) => {
                out.push_str(&text[copied..]);
                Cow::Owned(out)
            }
        }
    }
}

/// Cible d'un caractère hors BMP dans la table triée / an astral character's target in the sorted table.
#[inline]
fn astral_target(astral: &[(u32, char)], c: char) -> char {
    astral.binary_search_by_key(&(c as u32), |entry| entry.0).map_or(c, |i| astral[i].1)
}

#[inline]
fn is_emphasis(b: u8) -> bool {
    b == b'*' || b == b'_'
}

/// `_EMPHASIS_RE.sub(_unbold, text)` : `[*_]{2,3}` hors d'un mot -> espaces, longueur gardée.
/// Markdown emphasis outside a word becomes spaces, length kept.
fn unbold<'a>(text: Cow<'a, str>, classes: &Classes) -> Cow<'a, str> {
    let bytes = text.as_bytes();
    let alnum = |c: char| classes.is_alnum(c);
    let mut blanks: Vec<(usize, usize)> = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if !is_emphasis(bytes[i]) {
            i += 1;
            continue;
        }
        let run_start = i;
        while i < bytes.len() && is_emphasis(bytes[i]) {
            i += 1;
        }
        // Correspondances gloutonnes successives de 3, puis 2 ; un reste de 1 ne correspond pas.
        // Successive greedy matches of 3, then 2; a remainder of 1 does not match.
        let mut start = run_start;
        while i - start >= 2 {
            let end = start + (i - start).min(3);
            let inside_word = char_before(&text, start).is_some_and(alnum) && char_at(&text, end).is_some_and(alnum);
            if !inside_word {
                blanks.push((start, end));
            }
            start = end;
        }
    }
    if blanks.is_empty() {
        return text;
    }
    let mut out = String::with_capacity(text.len());
    let mut last = 0;
    for (start, end) in blanks {
        out.push_str(&text[last..start]);
        out.extend(std::iter::repeat_n(' ', end - start));
        last = end;
    }
    out.push_str(&text[last..]);
    Cow::Owned(out)
}

/// Nombre de tabulations ou espaces à partir de `i`, au plus 3 / spaces or tabs from `i`, at most 3.
fn blanks_at(bytes: &[u8], i: usize) -> usize {
    bytes[i.min(bytes.len())..].iter().take(3).take_while(|&&b| b == b' ' || b == b'\t').count()
}

/// Fin (octet) de la césure `-[ \t]{0,2}\r?\n[ \t]{0,2}` commençant à `dash`, si elle existe.
/// End byte of the hyphen break starting at `dash`, if any.
fn hyphen_break_end(bytes: &[u8], dash: usize) -> Option<usize> {
    let mut i = dash + 1;
    let before = blanks_at(bytes, i);
    if before > 2 {
        return None;
    }
    i += before;
    if bytes.get(i) == Some(&b'\r') {
        i += 1;
    }
    if bytes.get(i) != Some(&b'\n') {
        return None;
    }
    i += 1;
    let after = blanks_at(bytes, i);
    (after <= 2).then_some(i + after)
}

/// Coupes en positions de caractères : invisibles et césures de fin de ligne, triées, disjointes.
/// Cuts in character positions: invisible characters and end-of-line hyphenation, sorted, disjoint.
fn cuts(text: &str, classes: &Classes) -> Vec<(usize, usize)> {
    let invisible = !text.is_ascii();
    let hyphens = text.contains('-') && text.contains('\n');
    let mut cuts = Vec::new();
    if !invisible && !hyphens {
        return cuts;
    }
    let bytes = text.as_bytes();
    let letter = |c: char| classes.flags(c) & LETTER != 0;
    // Octet par octet ; seuls les caractères non ASCII sont décodés / byte by byte, decoding non-ASCII only.
    let (mut position, mut byte) = (0, 0);
    while byte < bytes.len() {
        let (c, width) = match bytes[byte] {
            b if b < 0x80 => (char::from(b), 1),
            _ => {
                let c = text[byte..].chars().next().unwrap_or(char::REPLACEMENT_CHARACTER);
                (c, c.len_utf8())
            }
        };
        if invisible && classes.flags(c) & INVISIBLE != 0 {
            cuts.push((position, position + 1));
        } else if hyphens && c == '-' && char_before(text, byte).is_some_and(letter) {
            // « Du-\npont » -> « Dupont » ; « Jean-\nPierre » garde son trait d'union / keeps its hyphen.
            if let Some(end) = hyphen_break_end(bytes, byte) {
                if let Some(next) = char_at(text, end).filter(|&n| letter(n)) {
                    // Césure faite d'octets ASCII : longueur en caractères = longueur en octets.
                    // The break is ASCII bytes: its length in characters equals its length in bytes.
                    let start = if classes.flags(next) & LOWER != 0 { position } else { position + 1 };
                    cuts.push((start, position + end - byte));
                }
            }
        }
        position += 1;
        byte += width;
    }
    cuts
}

/// Groupes voisins d'un saut de ligne GAP : 12 alphanumériques ASCII au plus / at most 12 ASCII alphanumerics.
const GAP_GROUP: usize = 12;

/// Plus de `GAP_GROUP` alphanumériques ASCII de suite en tête de ces octets (lus dans l'ordre donné) ?
/// More than `GAP_GROUP` ASCII alphanumerics in a row at the head of these bytes (read in the given order)?
fn group_longer<'a>(bytes: impl Iterator<Item = &'a u8>) -> bool {
    bytes.take(GAP_GROUP + 1).take_while(|b| b.is_ascii_alphanumeric()).count() > GAP_GROUP
}

/// Forme `[ \t]{0,3}\r?\n[ \t]{0,3}` d'une suite de blancs / shape of a blank run holding one line break.
fn break_shape(run: &[u8]) -> bool {
    let Some(newline) = run.iter().position(|&b| b == b'\n') else {
        return false;
    };
    let before = run[..newline].strip_suffix(b"\r").unwrap_or(&run[..newline]);
    let after = &run[newline + 1..];
    before.len() <= 3 && after.len() <= 3 && before.iter().chain(after).all(|&b| b == b' ' || b == b'\t')
}

/// Règle GAP de `_text._gaps` : (caractère de début, longueur, octet de début) de chaque suite de blancs à ramener
/// à une espace (des octets ASCII : longueur en caractères = longueur en octets). Tabulation ou 2 à 4 blancs entre
/// deux alphanumériques ASCII dont un chiffre ; un seul saut de ligne entre deux chiffres, groupes voisins de 12
/// caractères au plus. GAP rule: (start character, length, start byte) of each blank run to make one space.
fn gaps(text: &str) -> Vec<(usize, usize, usize)> {
    let mut found = Vec::new();
    if !text.contains('\t') && !text.contains("  ") && !text.contains('\n') {
        return found;
    }
    let bytes = text.as_bytes();
    let blank = |b: u8| matches!(b, b' ' | b'\t' | b'\r' | b'\n');
    let (mut position, mut i) = (0, 0);
    while i < bytes.len() {
        if !blank(bytes[i]) {
            // Un octet de tête par caractère / one lead byte per character.
            position += usize::from((bytes[i] as i8) >= -0x40);
            i += 1;
            continue;
        }
        let (start, first) = (i, position);
        while i < bytes.len() && blank(bytes[i]) {
            i += 1;
        }
        position += i - start;
        let (Some(&before), Some(&after)) = (start.checked_sub(1).map(|k| &bytes[k]), bytes.get(i)) else {
            continue;
        };
        if !before.is_ascii_alphanumeric() || !after.is_ascii_alphanumeric() {
            continue;
        }
        let run = &bytes[start..i];
        let gap = match run.iter().filter(|&&b| b == b'\n').count() {
            0 => {
                run.len() <= 4
                    && run != b" "
                    && !run.contains(&b'\r')
                    && (before.is_ascii_digit() || after.is_ascii_digit())
            }
            1 => {
                before.is_ascii_digit()
                    && after.is_ascii_digit()
                    && break_shape(run)
                    && !group_longer(bytes[..start].iter().rev())
                    && !group_longer(bytes[i..].iter())
            }
            _ => false,
        };
        if gap {
            found.push((first, run.len(), start));
        }
    }
    found
}

/// `_text._SEP_RUNS` : séparateur et nombre minimal de groupes / separator and minimum number of groups.
const SEP_RUNS: [(u8, usize); 2] = [(b'/', 4), (b'.', 5)];
/// Longueur maximale d'un groupe / longest group.
const SEP_GROUP: usize = 6;

/// `_text._sep_runs` : octets des « / » et « . » à remplacer par une espace. Mot entier de lettres, chiffres et
/// séparateurs (un séparateur final permis), groupes de 1 à 6 majuscules ou chiffres dont un chiffre.
/// Bytes of the separators to turn into spaces: a whole word of letters, digits and separators (one trailing
/// separator allowed), groups of 1 to 6 capitals or digits, each with a digit.
fn sep_runs(text: &str) -> Vec<usize> {
    let bytes = text.as_bytes();
    let mut found = Vec::new();
    for (sep, minimum) in SEP_RUNS {
        if !bytes.contains(&sep) {
            continue;
        }
        let in_word = |b: u8| b.is_ascii_alphanumeric() || b == sep;
        let mut i = 0;
        while i < bytes.len() {
            if !in_word(bytes[i]) || (i > 0 && in_word(bytes[i - 1])) {
                i += 1;
                continue;
            }
            let start = i;
            while i < bytes.len() && in_word(bytes[i]) {
                i += 1;
            }
            let body = bytes[start..i].strip_suffix(&[sep]).unwrap_or(&bytes[start..i]);
            let groups = body.split(|&b| b == sep);
            let valid = body.iter().filter(|&&b| b == sep).count() + 1 >= minimum
                && groups.clone().all(|group| {
                    (1..=SEP_GROUP).contains(&group.len())
                        && group.iter().all(|b| b.is_ascii_digit() || b.is_ascii_uppercase())
                        && group.iter().any(u8::is_ascii_digit)
                });
            if valid {
                found.extend(body.iter().enumerate().filter(|&(_, &b)| b == sep).map(|(k, _)| start + k));
            }
        }
    }
    found
}

/// Règle BREAK (`_text._breaks`) : groupes de 12 caractères au plus, partie locale de 7 caractères au plus sans
/// signe / BREAK rule: groups of at most 12 characters, local part of at most 7 characters without a sign.
const BREAK_GROUP: usize = 12;
const BREAK_LOCAL: usize = 7;

/// Caractère d'un morceau de courriel (`_text._EMAIL_PART`) / character of an e-mail piece.
fn email_part(b: u8) -> bool {
    b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'%' | b'+' | b'-' | b'@')
}

/// `_text._token` : octets [début, fin) de la suite maximale vers la gauche (`left`) ou la droite, et « mot
/// entier » / maximal run leftwards or rightwards, and whether it is a whole word.
fn token(text: &str, byte: usize, left: bool, part: fn(u8) -> bool, classes: &Classes) -> (usize, usize, bool) {
    let bytes = text.as_bytes();
    if left {
        let mut i = byte;
        while i > 0 && part(bytes[i - 1]) {
            i -= 1;
        }
        (i, byte, !char_before(text, i).is_some_and(|c| classes.is_alnum(c)))
    } else {
        let mut i = byte;
        while i < bytes.len() && part(bytes[i]) {
            i += 1;
        }
        (byte, i, !char_at(text, i).is_some_and(|c| classes.is_alnum(c)))
    }
}

/// `_text._DOMAIN_RE` en entier / full match of the domain shape.
fn domain_ok(domain: &[u8]) -> bool {
    let labels: Vec<&[u8]> = domain.split(|&b| b == b'.').collect();
    let Some((last, rest)) = labels.split_last() else {
        return false;
    };
    !rest.is_empty()
        && rest.iter().all(|l| !l.is_empty() && l.iter().all(|&b| b.is_ascii_alphanumeric() || b == b'-'))
        && last.len() >= 2
        && last.iter().all(u8::is_ascii_alphabetic)
}

/// `_text._email_join`.
fn email_join(left: &[u8], right: &[u8]) -> bool {
    let mut right = right;
    while let Some((&b'.' | &b'-', head)) = right.split_last() {
        right = head;
    }
    let ats = left.iter().chain(right).filter(|&&b| b == b'@').count();
    if ats != 1 || left.is_empty() || right.is_empty() {
        return false;
    }
    if let Some(at) = left.iter().position(|&b| b == b'@') {
        let domain = &left[at + 1..];
        let joined = [domain, right].concat();
        return at > 0 && !domain_ok(domain) && domain_ok(&joined);
    }
    let at = right.iter().position(|&b| b == b'@').unwrap_or(0);
    // Le morceau de gauche commence par une lettre / the left piece starts with a letter.
    domain_ok(&right[at + 1..])
        && left[0].is_ascii_alphabetic()
        && (left.len() <= BREAK_LOCAL || left.iter().any(|b| b"._-0123456789".contains(b)))
}

/// `_text._IBAN_HEAD_RE` en entier / full match of an IBAN head.
fn iban_head(group: &[u8]) -> bool {
    group.len() >= 4
        && group[..2].iter().all(u8::is_ascii_uppercase)
        && group[2..4].iter().all(u8::is_ascii_digit)
        && group[4..].iter().all(|b| b.is_ascii_digit() || b.is_ascii_uppercase())
}

/// `_text._iban_complete` : clé ISO 7064 (mod 97) déjà juste / the key is already right.
fn iban_complete(group: &[u8]) -> bool {
    let mut remainder = 0u32;
    for &b in group[4..].iter().chain(&group[..4]) {
        let value =
            if b.is_ascii_digit() { u32::from(b - b'0') } else { u32::from(b.to_ascii_uppercase() - b'A') + 10 };
        for digit in value.to_string().bytes() {
            remainder = (remainder * 10 + u32::from(digit - b'0')) % 97;
        }
    }
    remainder == 1
}

/// Zone GAP : (caractère de début, longueur, octet de début) / GAP zone: (start character, length, start byte).
type GapZone = (usize, usize, usize);
/// Zone retirée : [début, fin) en caractères / removed zone: [start, end) in characters.
type CutZone = (usize, usize);

/// Règle BREAK de `_text._breaks` : zones à ramener à une espace (caractère de début, longueur, octet de début)
/// et zones à retirer (positions de caractères). BREAK rule: zones to make one space and zones to remove.
fn breaks(text: &str, classes: &Classes) -> (Vec<GapZone>, Vec<CutZone>) {
    let mut gaps = Vec::new();
    let mut cuts = Vec::new();
    let bytes = text.as_bytes();
    let alnum = |b: u8| b.is_ascii_alphanumeric();
    let mut position = 0;
    for (i, &b) in bytes.iter().enumerate() {
        if b != b'\n' {
            position += usize::from((b as i8) >= -0x40);
            continue;
        }
        // Position du « \n » ; « \r » éventuel juste avant / position of the "\n"; optional "\r" just before.
        let crlf = i > 0 && bytes[i - 1] == b'\r';
        let (start, first) = if crlf { (i - 1, position - 1) } else { (i, position) };
        position += 1;
        let end = i + 1;
        let (Some(&before), Some(&after)) = (start.checked_sub(1).map(|k| &bytes[k]), bytes.get(end)) else {
            continue;
        };
        if !email_part(before) || !email_part(after) {
            continue;
        }
        let length = end - start;
        let (l0, l1, left_whole) = token(text, start, true, email_part, classes);
        let (r0, r1, right_whole) = token(text, end, false, email_part, classes);
        if left_whole && right_whole && email_join(&bytes[l0..l1], &bytes[r0..r1]) {
            cuts.push((first, first + length));
            continue;
        }
        let (l0, l1, left_whole) = token(text, start, true, alnum, classes);
        let (r0, r1, right_whole) = token(text, end, false, alnum, classes);
        let (left, right) = (&bytes[l0..l1], &bytes[r0..r1]);
        if left.is_empty() || right.is_empty() || !left_whole || !right_whole {
            continue;
        }
        let upper = |g: &[u8]| !g.iter().any(u8::is_ascii_lowercase);
        let digit = |g: &[u8]| g.iter().any(u8::is_ascii_digit);
        if iban_head(left)
            && upper(right)
            && digit(right)
            && (15..=34).contains(&(left.len() + right.len()))
            && !iban_complete(left)
        {
            cuts.push((first, first + length));
        } else if !(left.last().is_some_and(u8::is_ascii_digit) && right[0].is_ascii_digit())
            && left.len() <= BREAK_GROUP
            && right.len() <= BREAK_GROUP
            && upper(left)
            && upper(right)
            && digit(left)
            && digit(right)
        {
            gaps.push((first, length, start));
        }
    }
    (gaps, cuts)
}

/// Caractère d'une suite de lettres espacées (`_text._SPACED_RE`) / character of a letter-spaced run.
fn spaced_cell(c: char, classes: &Classes) -> bool {
    classes.is_word(c) || matches!(c, '@' | '.' | '-' | '\'' | '+' | ',' | '(' | ')')
}

/// `_text._SPACED_HINT_RE` : « ␣X␣{1,4}Y », Y sans lettre collée : condition nécessaire d'une suite (pré-test bon
/// marché). A necessary condition for a run (cheap pre-check).
fn spaced_hint(text: &str, classes: &Classes) -> bool {
    let bytes = text.as_bytes();
    for (i, _) in text.match_indices(' ') {
        let mut it = text[i + 1..].chars();
        let Some(x) = it.next() else { continue };
        if !spaced_cell(x, classes) {
            continue;
        }
        let mut k = i + 1 + x.len_utf8();
        let spaces = bytes[k..].iter().take(5).take_while(|&&b| b == b' ').count();
        if !(1..=4).contains(&spaces) {
            continue;
        }
        k += spaces;
        let mut tail = text[k..].chars();
        if tail.next().is_some_and(|y| spaced_cell(y, classes)) && !tail.next().is_some_and(|c| classes.is_word(c)) {
            return true;
        }
    }
    false
}

/// Lettres espacées (`_text._spaced_cuts`) : zones à retirer, en positions de caractères.
/// Letter spacing: zones to remove, in character positions.
fn spaced_cuts(text: &str, classes: &Classes) -> Vec<(usize, usize)> {
    let mut cuts = Vec::new();
    if !spaced_hint(text, classes) {
        return cuts;
    }
    let chars: Vec<char> = text.chars().collect();
    let n = chars.len();
    let cell = |p: usize| p < n && spaced_cell(chars[p], classes);
    let word = |p: usize| p < n && classes.is_word(chars[p]);
    let mut p = 0;
    while p < n {
        if !cell(p) || (p > 0 && word(p - 1)) {
            p += 1;
            continue;
        }
        let mut cells = vec![p];
        let mut last = p;
        loop {
            let mut q = last + 1;
            while q < n && chars[q] == ' ' && q - last <= 4 {
                q += 1;
            }
            let spaces = q - last - 1;
            if (1..=4).contains(&spaces) && cell(q) && !word(q + 1) {
                cells.push(q);
                last = q;
            } else {
                break;
            }
        }
        if cells.len() < 3 {
            p += 1;
            continue;
        }
        let digit = |k: usize| chars[cells[k]].is_ascii_digit();
        let end = cells.len() - 1;
        let mut block: Vec<usize> = Vec::new();
        for (k, &next) in cells.iter().enumerate() {
            if matches!(chars[next], 'a' | 'à') && (1..end).contains(&k) && digit(k - 1) && digit(k + 1) {
                // « 4 à 6 » : l'intervalle reste tel quel / the range stays as it is.
                spaced_block(&chars, &block, &mut cuts, classes);
                block.clear();
                continue;
            }
            let split = block.last().is_some_and(|&prev| {
                next - prev == 2 && classes.is_lower(chars[prev]) && classes.is_upper(chars[next])
            });
            if split {
                spaced_block(&chars, &block, &mut cuts, classes);
                block.clear();
            }
            block.push(next);
        }
        spaced_block(&chars, &block, &mut cuts, classes);
        p = last + 1;
    }
    cuts
}

fn spaced_block(chars: &[char], block: &[usize], cuts: &mut Vec<(usize, usize)>, classes: &Classes) {
    // Lettres et chiffres seulement ; trois pour un mot capitalisé (« Z o é ») / letters and digits only; three
    // for a capitalised word.
    let letters = block.iter().filter(|&&cell| classes.is_word(chars[cell])).count();
    let word = block.len() == 3
        && classes.is_upper(chars[block[0]])
        && classes.is_lower(chars[block[1]])
        && classes.is_lower(chars[block[2]]);
    if letters < 4 && !word {
        return;
    }
    for pair in block.windows(2) {
        let (prev, next) = (pair[0], pair[1]);
        cuts.push(if next - prev == 2 { (prev + 1, next) } else { (prev + 2, next) });
    }
}

/// Texte privé des coupes et table des positions (une par caractère gardé, puis la longueur).
/// Text without the cuts and offset map (one per kept character, then the length).
fn assemble(text: &str, cuts: &[(usize, usize)]) -> (String, Vec<i64>) {
    let mut out = String::with_capacity(text.len());
    let mut offsets = Vec::with_capacity(text.len() + 1);
    let mut cut = cuts.iter().peekable();
    let mut length = 0;
    for (position, c) in text.chars().enumerate() {
        length = position + 1;
        while cut.next_if(|&&(_, end)| end <= position).is_some() {}
        if cut.peek().is_some_and(|&&(start, _)| start <= position) {
            continue;
        }
        out.push(c);
        offsets.push(position as i64);
    }
    offsets.push(length as i64);
    (out, offsets)
}

/// Résultat de la préparation ; `None` = texte d'entrée inchangé / preparation result; None = unchanged.
struct Prepared {
    norm: Option<String>,
    folded: Option<String>,
    offsets: Option<Vec<i64>>,
}

/// Tables de normalisation et de repliement de `gdprguardian._text` / normalisation and folding tables.
#[pyclass(name = "Preparer", frozen)]
pub struct Preparer {
    tables: Py<PyUnicodeTables>,
    normalize: CharMap,
    fold: CharMap,
    /// Cibles hors BMP des tables, à classer avec le texte / targets beyond the BMP, classified with the text.
    astral_targets: String,
}

impl Preparer {
    /// `normalize()` : transcodage, gras Markdown, coupes / translation, emphasis, cuts.
    fn normalize_text<'a>(&self, text: &'a str, classes: &Classes) -> (Cow<'a, str>, Option<Vec<i64>>) {
        // Comme Python : pas de transcodage pour un texte ASCII / like Python: no translation for ASCII.
        let mut mapped = if text.is_ascii() { Cow::Borrowed(text) } else { self.normalize.translate(text) };
        if mapped.contains("**") || mapped.contains("__") {
            mapped = unbold(mapped, classes);
        }
        // Règle GAP : le premier blanc devient une espace, les suivants sont coupés / GAP rule: the first blank
        // becomes a space, the others are cut.
        let mut gaps = gaps(&mapped);
        // Règle BREAK : saut de ligne dans un identifiant / BREAK rule: line break inside an identifier.
        let (break_gaps, break_cuts) =
            if mapped.contains('\n') { breaks(&mapped, classes) } else { Default::default() };
        if !break_gaps.is_empty() {
            gaps.extend(break_gaps);
            gaps.sort_unstable();
        }
        // Lettres espacées, lues avant les remplacements / letter spacing, read before the swaps.
        let spaced = if mapped.contains(' ') { spaced_cuts(&mapped, classes) } else { Vec::new() };
        let seps = if mapped.contains('/') || mapped.contains('.') { sep_runs(&mapped) } else { Vec::new() };
        if !seps.is_empty() || gaps.iter().any(|&(_, _, byte)| mapped.as_bytes()[byte] != b' ') {
            let mut bytes = mapped.into_owned().into_bytes();
            for byte in gaps.iter().map(|gap| gap.2).chain(seps) {
                bytes[byte] = b' ';
            }
            // Octets ASCII remplacés par un octet ASCII : UTF-8 intact / ASCII bytes swapped for ASCII: valid UTF-8.
            mapped = Cow::Owned(String::from_utf8(bytes).unwrap_or_default());
        }
        let mut cuts = cuts(&mapped, classes);
        if gaps.iter().any(|&(_, length, _)| length > 1) {
            cuts.extend(gaps.iter().filter(|gap| gap.1 > 1).map(|&(first, length, _)| (first + 1, first + length)));
            cuts.sort_unstable();
        }
        if !break_cuts.is_empty() {
            cuts.extend(break_cuts);
            cuts.sort_unstable();
        }
        if !spaced.is_empty() {
            cuts.extend(spaced);
            cuts.sort_unstable();
        }
        if cuts.is_empty() {
            return (mapped, None);
        }
        let (norm, offsets) = assemble(&mapped, &cuts);
        (Cow::Owned(norm), Some(offsets))
    }

    /// `fold()` : minuscules ASCII, sinon table de repliement / ASCII lowercase, else the folding table.
    fn fold_text<'a>(&self, text: &'a str) -> Cow<'a, str> {
        if text.is_ascii() {
            if text.bytes().any(|b| b.is_ascii_uppercase()) {
                Cow::Owned(text.to_ascii_lowercase())
            } else {
                Cow::Borrowed(text)
            }
        } else {
            self.fold.translate(text)
        }
    }

    fn prepare_text(&self, text: &str, classes: &Classes) -> Prepared {
        let (norm, offsets) = self.normalize_text(text, classes);
        let folded = match self.fold_text(&norm) {
            Cow::Borrowed(_) => None,
            Cow::Owned(folded) => Some(folded),
        };
        let norm = match norm {
            Cow::Borrowed(_) => None,
            Cow::Owned(norm) => Some(norm),
        };
        Prepared { norm, folded, offsets }
    }
}

fn offsets_bytes<'py>(py: Python<'py>, offsets: &[i64]) -> Bound<'py, PyBytes> {
    let bytes: Vec<u8> = offsets.iter().flat_map(|o| o.to_ne_bytes()).collect();
    PyBytes::new(py, &bytes)
}

#[pymethods]
impl Preparer {
    /// `tables` : table Unicode partagée, dont le repliement (`_text.fold`) ; `normalize_*` : `_NORMALIZE_BMP`
    /// (UTF-32 LE) et `_ASTRAL_NORMALIZE`. `tables`: the shared Unicode table, its folding included.
    #[new]
    fn new(
        tables: Py<PyUnicodeTables>,
        normalize_bmp: &Bound<'_, PyBytes>,
        normalize_astral: Vec<(u32, u32)>,
    ) -> PyResult<Self> {
        let normalize = CharMap::new(normalize_bmp.as_bytes(), &normalize_astral)?;
        let unicode = tables.get().shared();
        let fold = CharMap::build(|cp| Ok(char::from_u32(cp).map_or('\0', |c| unicode.fold(c))), &[])?;
        let mut astral_targets: Vec<char> = normalize
            .astral
            .iter()
            .map(|entry| entry.1)
            .chain(normalize.blocks.iter().flatten().copied())
            .filter(|&c| c as usize >= BMP)
            .collect();
        astral_targets.sort_unstable();
        astral_targets.dedup();
        Ok(Self { tables, normalize, fold, astral_targets: astral_targets.into_iter().collect() })
    }

    /// (texte normalisé, texte replié, positions en `int64` natifs ou None), sans GIL.
    /// (normalised text, folded text, offsets as native `int64` bytes or None), GIL released.
    /// Les textes inchangés sont rendus tels quels, sans copie / unchanged texts are returned as is.
    #[allow(clippy::type_complexity)]
    fn prepare<'py>(
        &self,
        py: Python<'py>,
        text: &Bound<'py, PyString>,
    ) -> PyResult<(Bound<'py, PyString>, Bound<'py, PyString>, Option<Bound<'py, PyBytes>>)> {
        let source = text.to_str()?;
        let classes = self.tables.get().classes(py, &[source, &self.astral_targets])?;
        let prepared = py.detach(|| self.prepare_text(source, classes));
        let norm = prepared.norm.map_or_else(|| text.clone(), |norm| PyString::new(py, &norm));
        let folded = prepared.folded.map_or_else(|| norm.clone(), |folded| PyString::new(py, &folded));
        Ok((norm, folded, prepared.offsets.map(|offsets| offsets_bytes(py, &offsets))))
    }

    /// `normalize()` seul / `normalize()` alone.
    fn normalize<'py>(
        &self,
        py: Python<'py>,
        text: &Bound<'py, PyString>,
    ) -> PyResult<(Bound<'py, PyString>, Option<Bound<'py, PyBytes>>)> {
        let source = text.to_str()?;
        let classes = self.tables.get().classes(py, &[source, &self.astral_targets])?;
        let (norm, offsets) = py.detach(|| {
            let (norm, offsets) = self.normalize_text(source, classes);
            (if let Cow::Owned(norm) = norm { Some(norm) } else { None }, offsets)
        });
        let norm = norm.map_or_else(|| text.clone(), |norm| PyString::new(py, &norm));
        Ok((norm, offsets.map(|offsets| offsets_bytes(py, &offsets))))
    }

    /// `fold()` seul / `fold()` alone.
    fn fold<'py>(&self, py: Python<'py>, text: &Bound<'py, PyString>) -> PyResult<Bound<'py, PyString>> {
        let source = text.to_str()?;
        let folded = py.detach(|| if let Cow::Owned(folded) = self.fold_text(source) { Some(folded) } else { None });
        Ok(folded.map_or_else(|| text.clone(), |folded| PyString::new(py, &folded)))
    }
}

/// Langue majoritaire par comptage de mots outils, comme `gdprguardian.locale.detect_language`.
/// Dominant language by stop-word counts, as `gdprguardian.locale.detect_language`.
#[pyclass(name = "LanguageDetector", frozen)]
pub struct LanguageDetector {
    /// Mots de 8 lettres au plus, rangés dans un entier : table à adressage ouvert (puissance de 2, au plus
    /// un quart pleine, 0 = vide) -> indice dans `ids`. Words of up to 8 letters packed in an integer:
    /// open-addressing table (power of 2, at most a quarter full, 0 = empty) -> index into `ids`.
    slots: Vec<(u64, usize)>,
    /// Langues de chaque mot (indices, ordre de Python) / each word's languages (indices, Python's order).
    ids: Vec<Vec<usize>>,
    /// Mots plus longs / longer words.
    long: HashMap<Vec<u8>, Vec<usize>>,
    languages: Vec<Py<PyString>>,
    undetermined: Py<PyString>,
    /// Échantillon en caractères (`LANGUAGE_SAMPLE`) / sample size in characters.
    sample: usize,
}

/// Mot `[a-z]{1,8}` rangé dans un entier (sans octet nul, donc sans collision) / word packed in an integer.
fn pack(word: &[u8]) -> Option<u64> {
    (word.len() <= 8).then(|| {
        let mut bytes = [0u8; 8];
        bytes[..word.len()].copy_from_slice(word);
        u64::from_le_bytes(bytes)
    })
}

impl LanguageDetector {
    /// Case du mot, ou première case vide sur son chemin / the word's slot, or the first empty one on its path.
    fn slot(slots: &[(u64, usize)], key: u64) -> usize {
        let mask = slots.len() - 1;
        let mut i = (key.wrapping_mul(0x9E37_79B9_7F4A_7C15) >> 32) as usize & mask;
        while slots[i].0 != 0 && slots[i].0 != key {
            i = (i + 1) & mask;
        }
        i
    }

    fn languages_of(&self, word: &[u8]) -> Option<&[usize]> {
        match pack(word) {
            Some(key) => {
                let (found, id) = self.slots[Self::slot(&self.slots, key)];
                (found == key).then(|| self.ids[id].as_slice())
            }
            None if self.long.is_empty() => None,
            None => self.long.get(word).map(Vec::as_slice),
        }
    }
}

#[pymethods]
impl LanguageDetector {
    #[new]
    fn new(py: Python<'_>, word_languages: Vec<(String, Vec<String>)>, sample: usize) -> Self {
        let mut names: Vec<String> = Vec::new();
        let (mut short, mut long) = (Vec::<(u64, Vec<usize>)>::new(), HashMap::new());
        for (word, languages) in word_languages {
            let ids: Vec<usize> = languages
                .into_iter()
                .map(|language| {
                    names.iter().position(|n| *n == language).unwrap_or_else(|| {
                        names.push(language);
                        names.len() - 1
                    })
                })
                .collect();
            // Seuls des mots `[a-z]+` peuvent être comptés / only `[a-z]+` words can ever be counted.
            if word.is_empty() || !word.bytes().all(|b| b.is_ascii_lowercase()) {
                continue;
            }
            match pack(word.as_bytes()) {
                Some(key) => short.push((key, ids)),
                None => {
                    long.insert(word.into_bytes(), ids);
                }
            }
        }
        let mut slots = vec![(0u64, 0usize); (4 * short.len()).max(8).next_power_of_two()];
        let mut ids = Vec::with_capacity(short.len());
        for (key, languages) in short {
            let i = Self::slot(&slots, key);
            if slots[i].0 == 0 {
                slots[i] = (key, ids.len());
                ids.push(languages);
            }
        }
        let languages = names.iter().map(|name| PyString::intern(py, name).unbind()).collect();
        Self { slots, ids, long, languages, undetermined: PyString::intern(py, "und").unbind(), sample }
    }

    /// Travail borné par l'échantillon : pas besoin de libérer le GIL / bounded by the sample.
    #[pyo3(signature = (folded, minimum=2))]
    fn detect(&self, py: Python<'_>, folded: &str, minimum: i64) -> Py<PyString> {
        let mut counts = vec![0i64; self.languages.len()];
        // Ordre de première apparition, comme un dict Python / first-seen order, like a Python dict.
        let mut order: Vec<usize> = Vec::new();
        let mut count = |word: &[u8]| {
            for &language in self.languages_of(word).into_iter().flatten() {
                if counts[language] == 0 {
                    order.push(language);
                }
                counts[language] += 1;
            }
        };
        // `[a-z]+` sur les `sample` premiers caractères, octet par octet : un octet de tête par caractère.
        // `[a-z]+` on the first `sample` characters, byte by byte: one lead byte per character.
        let bytes = folded.as_bytes();
        let (mut word_start, mut chars, mut end) = (None, 0, bytes.len());
        for (i, &b) in bytes.iter().enumerate() {
            if (b as i8) >= -0x40 {
                if chars == self.sample {
                    end = i;
                    break;
                }
                chars += 1;
            }
            if b.is_ascii_lowercase() {
                word_start.get_or_insert(i);
            } else if let Some(start) = word_start.take() {
                count(&bytes[start..i]);
            }
        }
        if let Some(start) = word_start {
            count(&bytes[start..end]);
        }
        // `minimum - 1` sans débordement : les comptes valent au moins 1, le résultat reste exact.
        // `minimum - 1` without overflow: counts are at least 1, so the result stays exact.
        let (mut best, mut best_count) = (None, minimum.saturating_sub(1));
        for language in order {
            if counts[language] > best_count {
                (best, best_count) = (Some(language), counts[language]);
            }
        }
        best.map_or(&self.undetermined, |language| &self.languages[language]).clone_ref(py)
    }
}

// --- Moteur fusionné : appels directs, sans aller-retour par Python / fused engine: direct calls ----------------

/// Texte normalisé et texte replié (`None` : inchangés), table des positions / normalised and folded texts.
pub(crate) type PreparedParts = (Option<String>, Option<String>, Option<Vec<i64>>);

impl Preparer {
    /// Classes de ces textes et des cibles hors BMP des tables, à demander avec le GIL.
    /// Classes of these texts and of the tables' astral targets, requested with the GIL held.
    pub(crate) fn classes_for<'a>(&'a self, py: Python<'_>, texts: &[&str]) -> PyResult<&'a Classes> {
        let mut all = texts.to_vec();
        all.push(&self.astral_targets);
        self.tables.get().classes(py, &all)
    }

    /// `prepare()` : (texte normalisé, texte replié, positions), sans GIL / without the GIL.
    pub(crate) fn prepare_parts(&self, text: &str, classes: &Classes) -> PreparedParts {
        let prepared = self.prepare_text(text, classes);
        (prepared.norm, prepared.folded, prepared.offsets)
    }

    /// `normalize()` : (texte normalisé ou `None` s'il est inchangé, positions), sans GIL / without the GIL.
    pub(crate) fn normalize_parts(&self, text: &str, classes: &Classes) -> (Option<String>, Option<Vec<i64>>) {
        let (norm, offsets) = self.normalize_text(text, classes);
        (if let Cow::Owned(norm) = norm { Some(norm) } else { None }, offsets)
    }

    /// `fold()`, sans GIL / without the GIL.
    pub(crate) fn fold_parts<'a>(&self, text: &'a str) -> Cow<'a, str> {
        self.fold_text(text)
    }
}

impl LanguageDetector {
    /// `detect_language(folded)` (seuil par défaut) / with the default minimum.
    pub(crate) fn language_of(&self, py: Python<'_>, folded: &str) -> Py<PyString> {
        self.detect(py, folded, 2)
    }
}
