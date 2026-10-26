//! Motifs du détecteur, écrits à la main : même résultat que `re` (Python), retours arrière compris.
//!
//! The detector's regular expressions, hand-written: same result as Python's `re`, backtracking
//! included. Chaque fonction cite le motif qu'elle reproduit ; toutes sont ancrées et bornées (temps
//! constant par appel, sauf mention). Each function quotes the pattern it mirrors; all are anchored
//! and bounded (constant time per call unless stated).

use std::borrow::Cow;

use super::chars::{blanks, is_blank, run, starts_with, Chars, CAP, LETTER, WORD};

/// Particules de `_PARTICLES` (fr_names) / particles of `_PARTICLES`.
const GAP_PARTICLES: [&str; 25] = [
    "de", "du", "des", "van", "von", "der", "den", "di", "da", "del", "della", "dos", "das", "do", "ben", "bin", "ibn",
    "al", "el", "y", "zu", "ter", "ten", "le", "la",
];
/// Particules de `_PARTICLE_AT_RE` / particles of `_PARTICLE_AT_RE`.
const SHIFT_PARTICLES: [&str; 13] =
    ["de", "du", "des", "van", "von", "der", "den", "di", "da", "del", "della", "dos", "das"];
/// Conjonctions de `_LIST_GAP_RE` / conjunctions of `_LIST_GAP_RE`.
const CONJUNCTIONS: [&str; 7] = ["et", "and", "ou", "or", "und", "y", "e"];
/// Longueur maximale d'un écart `_SPACE_GAP_RE` : 2 + 2 × (« della » + 2) + 2 / longest space gap.
pub const MAX_SPACE_GAP: usize = 18;

fn one_of(word: &[char], list: &[&str]) -> bool {
    list.iter().any(|w| word.iter().copied().eq(w.chars()))
}

/// Mot jusqu'au prochain blanc (au plus `max` caractères) / word up to the next blank.
fn word_before_blank(s: &[char], pos: usize, max: usize) -> &[char] {
    let len = run(s, pos, max, |c| !is_blank(c));
    &s[pos.min(s.len())..pos.min(s.len()) + len]
}

/// `TOKEN_RE` en `pos` : `[UPPER](?<!\w.)[^\W\d_]{0,40}(?:['-][^\W\d_]{1,40}){0,4}(?!\w|['-][^\W\d_])`.
///
/// Fin du jeton, ou `None`. Une fin au milieu de lettres ferait échouer `(?!\w)` : l'analyse gloutonne
/// est la seule possible. Token end; ending inside letters would fail `(?!\w)`, so greedy is the only parse.
pub fn token(chars: &Chars, text: &[char], pos: usize) -> Option<usize> {
    if !chars.is(text[pos], CAP) || (pos > 0 && chars.is(text[pos - 1], WORD)) {
        return None;
    }
    let letter = |c: char| chars.is(c, LETTER);
    let first = run(text, pos + 1, 41, letter);
    if first > 40 {
        return None;
    }
    let mut end = pos + 1 + first;
    let mut groups = 0;
    while matches!(text.get(end), Some('\'' | '-')) && text.get(end + 1).is_some_and(|&c| letter(c)) {
        let len = run(text, end + 1, 41, letter);
        if groups == 4 || len > 40 {
            return None;
        }
        end += 1 + len;
        groups += 1;
    }
    if text.get(end).is_some_and(|&c| chars.is(c, WORD)) {
        return None;
    }
    Some(end)
}

/// `_SPACE_GAP_RE`, correspondance totale : `[ \t]{1,2}(?:<particule>[ \t]{1,2}){0,2}(?:[dl]')?`.
pub fn space_gap(gap: &[char]) -> bool {
    let lead = blanks(gap, 0, 3);
    if lead == 0 || lead > 2 {
        return false;
    }
    let mut pos = lead;
    for _ in 0..2 {
        // Une particule n'est prise que suivie de blancs / a particle only counts when blanks follow.
        let word = word_before_blank(gap, pos, 6);
        let after = pos + word.len();
        if after == gap.len() || !one_of(word, &GAP_PARTICLES) {
            break;
        }
        let gap_blanks = blanks(gap, after, 3);
        if gap_blanks > 2 {
            return false;
        }
        pos = after + gap_blanks;
    }
    let rest = &gap[pos..];
    rest.is_empty() || (rest.len() == 2 && matches!(rest[0], 'd' | 'l') && rest[1] == '\'')
}

/// `_NEWLINE_GAP_RE`, correspondance totale : `[ \t]{0,2}\r?\n[ \t]{0,2}`.
pub fn newline_gap(gap: &[char]) -> bool {
    let lead = blanks(gap, 0, 3);
    if lead > 2 {
        return false;
    }
    let mut pos = lead;
    if gap.get(pos) == Some(&'\r') {
        pos += 1;
    }
    if gap.get(pos) != Some(&'\n') {
        return false;
    }
    let trail = blanks(gap, pos + 1, 3);
    trail <= 2 && pos + 1 + trail == gap.len()
}

/// `_HYPHEN_WRAP_RE`, correspondance totale : `-[ \t]{0,2}\r?\n[ \t]{0,2}`.
pub fn hyphen_wrap(gap: &[char]) -> bool {
    gap.first() == Some(&'-') && newline_gap(&gap[1..])
}

/// `_HYPHEN_WRAP_RE` en `pos` (recherche gloutonne) : fin de la coupure / end of the line-break hyphen.
fn hyphen_wrap_at(s: &[char], pos: usize) -> Option<usize> {
    if s.get(pos) != Some(&'-') {
        return None;
    }
    let lead = blanks(s, pos + 1, 3);
    if lead > 2 {
        return None;
    }
    let mut end = pos + 1 + lead;
    if s.get(end) == Some(&'\r') {
        end += 1;
    }
    if s.get(end) != Some(&'\n') {
        return None;
    }
    Some(end + 1 + blanks(s, end + 1, 2))
}

/// `_unwrap` : « Anne-⏎Sophie » -> « Anne-Sophie » (`_HYPHEN_WRAP_RE.sub("-", name)`).
pub fn unwrap(name: &[char]) -> Cow<'_, [char]> {
    if !name.contains(&'\n') {
        return Cow::Borrowed(name);
    }
    let mut out = Vec::with_capacity(name.len());
    let mut pos = 0;
    while pos < name.len() {
        match hyphen_wrap_at(name, pos) {
            Some(end) => {
                out.push('-');
                pos = end;
            }
            None => {
                out.push(name[pos]);
                pos += 1;
            }
        }
    }
    Cow::Owned(out)
}

/// `_INITIAL_GAP_RE`, correspondance totale : `\.(?:[ \t]{0,2}|-)`.
pub fn initial_gap(gap: &[char]) -> bool {
    match gap {
        ['.', rest @ ..] => (rest.len() <= 2 && rest.iter().all(|&c| is_blank(c))) || rest == ['-'],
        _ => false,
    }
}

/// `_PARTICLE_AT_RE` en `pos` : `(?:(?:de|du|des|van|von|der|den|di|da|del|della|dos|das)[ \t]{1,2}){1,2}|[dD]'`.
pub fn particle_at(text: &[char], pos: usize) -> Option<usize> {
    let mut end = pos;
    let mut repeats = 0;
    while repeats < 2 {
        let word = word_before_blank(text, end, 6);
        let after = end + word.len();
        if after >= text.len() || !one_of(word, &SHIFT_PARTICLES) {
            break;
        }
        end = after + blanks(text, after, 2);
        repeats += 1;
    }
    if repeats > 0 {
        return Some(end);
    }
    (matches!(text.get(pos), Some('d' | 'D')) && text.get(pos + 1) == Some(&'\'')).then_some(pos + 2)
}

/// `_AFTER_HONORIFIC_RE` en `pos` : `\.?[ \t]{0,3}` (toujours une correspondance / always matches).
pub fn after_honorific(text: &[char], pos: usize) -> usize {
    let end = pos + usize::from(text.get(pos) == Some(&'.'));
    end + blanks(text, end, 3)
}

/// `_ARTICLE_AT_RE` en `pos` (texte replié) : `(?:le|la|les)(?![^\W\d_])|l'`.
pub fn article_at(chars: &Chars, folded: &[char], pos: usize) -> bool {
    let article = ["le", "la", "les"]
        .iter()
        .any(|w| starts_with(folded, pos, w) && !folded.get(pos + w.len()).is_some_and(|&c| chars.is(c, LETTER)));
    article || starts_with(folded, pos, "l'")
}

/// `_AFTER_CUE_RE` en `pos` : `[ \t]{1,3}(?:,[ \t]{0,2})?|,[ \t]{1,2}`.
pub fn after_cue(text: &[char], pos: usize) -> Option<usize> {
    let lead = blanks(text, pos, 3);
    if lead > 0 {
        let end = pos + lead;
        return Some(if text.get(end) == Some(&',') { end + 1 + blanks(text, end + 1, 2) } else { end });
    }
    if text.get(pos) == Some(&',') {
        let trail = blanks(text, pos + 1, 2);
        return (trail > 0).then_some(pos + 1 + trail);
    }
    None
}

/// `_AFTER_EPONYM_RE` en `pos` : `\.?(?:[ \t]{1,3}|[ \t]{0,2}\r?\n[ \t]{0,2})` suivi d'un article facultatif
/// (`eponym_article`). Un point est toujours pris : sans lui, l'espace suivant ne peut commencer au point.
/// The dot is always taken: without it, the gap could not start on the dot.
pub fn after_eponym(text: &[char], pos: usize) -> Option<usize> {
    let start = pos + usize::from(text.get(pos) == Some(&'.'));
    let lead = blanks(text, start, 3);
    let end = if lead > 0 {
        start + lead
    } else {
        let mut end = start;
        if text.get(end) == Some(&'\r') {
            end += 1;
        }
        if text.get(end) != Some(&'\n') {
            return None;
        }
        end + 1 + blanks(text, end + 1, 2)
    };
    Some(eponym_article(text, end).unwrap_or(end))
}

/// Partie facultative de `_AFTER_EPONYM_RE`, dans l'ordre des alternatives :
/// `(?:(?:de[ \t]{1,2}la|du|des|de|la|le|les)[ \t]{1,2}|(?:de[ \t]{1,2})?[dlDL]')`.
/// Optional tail of `_AFTER_EPONYM_RE`, alternatives tried in order (« rue de l'Église » stops after
/// « de », as in Python).
fn eponym_article(text: &[char], pos: usize) -> Option<usize> {
    // `<mot>[ \t]{1,2}` : fin après le mot et ses blancs (deux au plus) / end after the word and its blanks.
    let word_then_blanks = |at: usize, word: &str| -> Option<usize> {
        let after = at + word.chars().count();
        let trail = blanks(text, after, 2);
        (starts_with(text, at, word) && trail > 0).then_some(after + trail)
    };
    // « de[ \t]{1,2}la » : les blancs internes doivent mener à « la » / inner blanks must lead to "la".
    if starts_with(text, pos, "de") {
        let inner = blanks(text, pos + 2, 3);
        if (1..=2).contains(&inner) {
            if let Some(end) = word_then_blanks(pos + 2 + inner, "la") {
                return Some(end);
            }
        }
    }
    for word in ["du", "des", "de", "la", "le", "les"] {
        if let Some(end) = word_then_blanks(pos, word) {
            return Some(end);
        }
    }
    let elided = |at: usize| matches!(text.get(at), Some('d' | 'l' | 'D' | 'L')) && text.get(at + 1) == Some(&'\'');
    if starts_with(text, pos, "de") {
        let inner = blanks(text, pos + 2, 3);
        if (1..=2).contains(&inner) && elided(pos + 2 + inner) {
            return Some(pos + 4 + inner);
        }
    }
    elided(pos).then_some(pos + 2)
}

/// `_AFTER_DIRECT_RE` en `pos` : `[ \t]{1,2}`.
pub fn after_direct(text: &[char], pos: usize) -> Option<usize> {
    let len = blanks(text, pos, 2);
    (len > 0).then_some(pos + len)
}

/// `_AFTER_LABEL_RE` en `pos` : `[ \t*_]{0,4}`.
pub fn after_label(text: &[char], pos: usize) -> usize {
    pos + run(text, pos, 4, |c| matches!(c, ' ' | '\t' | '*' | '_'))
}

/// `_LABEL_SPLIT_RE.split(s)[-1]` : ce qui suit le dernier séparateur `[ \t]{2,}|\||\t`.
/// What follows the last separator.
pub fn after_last_label_separator(s: &[char]) -> &[char] {
    let (mut last, mut i) = (0, 0);
    while i < s.len() {
        if is_blank(s[i]) && s.get(i + 1).is_some_and(|&c| is_blank(c)) {
            i += run(s, i, usize::MAX, is_blank);
            last = i;
        } else {
            if matches!(s[i], '|' | '\t') {
                last = i + 1;
            }
            i += 1;
        }
    }
    &s[last..]
}

/// `_LIST_GAP_RE`, correspondance totale : `[ \t]{0,2}(?:,[ \t]{0,2}(?:<conj>[ \t]{1,2})?|;[ \t]{0,2}|&[ \t]{0,2}|<conj>[ \t]{1,2})`.
pub fn list_gap(gap: &[char]) -> bool {
    // `<conj>[ \t]{1,2}` jusqu'à la fin / conjunction then 1-2 blanks up to the end.
    let conjunction = |s: &[char]| {
        let word = word_before_blank(s, 0, 4);
        let trail = s.len() - word.len();
        one_of(word, &CONJUNCTIONS) && (1..=2).contains(&trail) && s[word.len()..].iter().all(|&c| is_blank(c))
    };
    let lead = blanks(gap, 0, 3);
    if lead > 2 {
        return false;
    }
    let rest = &gap[lead..];
    match rest.first() {
        Some(',') => {
            let trail = blanks(rest, 1, 3);
            let tail = &rest[1 + trail..];
            trail <= 2 && (tail.is_empty() || conjunction(tail))
        }
        Some(';' | '&') => {
            let trail = blanks(rest, 1, 3);
            trail <= 2 && 1 + trail == rest.len()
        }
        _ => conjunction(rest),
    }
}

/// Longueur de la suite de `class` qui finit juste avant `end`, au plus `max` / run of `class` ending at `end`.
fn run_before(s: &[char], end: usize, max: usize, class: impl Fn(char) -> bool) -> usize {
    s[..end.min(s.len())].iter().rev().take(max).take_while(|&&c| class(c)).count()
}

/// Positions des « @ » / positions of the "@" signs.
pub fn at_signs(s: &[char]) -> impl Iterator<Item = usize> + '_ {
    s.iter().enumerate().filter(|(_, &c)| c == '@').map(|(i, _)| i)
}

/// `[\w.+-]` des motifs d'adresse / the address patterns' `[\w.+-]`.
fn address_char(chars: &Chars, c: char) -> bool {
    chars.is(c, WORD) || matches!(c, '.' | '+' | '-')
}

/// `_DISPLAY_AT_RE` : `[<(\[][ \t]?[\w.+-]{1,64}@`, position de l'ouvrant pour le « @ » en `at`.
///
/// Opener position for the "@" at `at`. Chaque correspondance finit sur un « @ » et ni l'ouvrant ni le
/// blanc n'appartiennent à `[\w.+-]` : l'ouvrant précède la plus longue suite de cette classe avant le « @ »,
/// un blanc permis entre les deux ; les correspondances ne se chevauchent jamais (comme `finditer`).
/// Every match ends on an "@" and neither the opener nor the blank is in the class: the opener precedes
/// the longest class run before the "@", one blank allowed; matches never overlap.
pub fn display_opener(chars: &Chars, text: &[char], at: usize) -> Option<usize> {
    let len = run_before(text, at, 65, |c| address_char(chars, c));
    let first = at - len;
    let opener = |i: usize| matches!(text.get(i), Some('<' | '(' | '['));
    if !(1..=64).contains(&len) || first == 0 {
        return None;
    }
    if opener(first - 1) {
        return Some(first - 1);
    }
    (first >= 2 && is_blank(text[first - 1]) && opener(first - 2)).then(|| first - 2)
}

/// `_EMAIL_LOCAL_RE.finditer(folded)` : `(?<![\w.+-])([a-z][a-z0-9.\-_+]{1,63})@[a-z0-9]`.
///
/// Parties locales (début, fin) / local parts (start, end). Chaque correspondance finit sur un « @ » ; la
/// classe locale est incluse dans `[\w.+-]`, donc seul le début de la plus longue suite locale avant le
/// « @ » passe `(?<![\w.+-])`. `resume` reproduit la reprise de `finditer` après une correspondance.
/// Every match ends on an "@"; the local class lies inside `[\w.+-]`, so only the start of the longest
/// local run before the "@" passes the lookbehind. `resume` mirrors where `finditer` resumes.
pub fn email_locals(chars: &Chars, folded: &[char]) -> Vec<(usize, usize)> {
    let local = |c: char| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '.' | '-' | '_' | '+');
    let mut found = Vec::new();
    let mut resume = 0;
    for at in at_signs(folded) {
        let len = run_before(folded, at, 65, local);
        let start = at - len;
        let free = start == 0 || !address_char(chars, folded[start - 1]);
        let domain = folded.get(at + 1).is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit());
        if start >= resume && (2..=64).contains(&len) && folded[start].is_ascii_lowercase() && free && domain {
            found.push((start, at));
            resume = at + 2;
        }
    }
    found
}

/// `_TABLE_SEP_RE` sur une ligne entière (sans le `\n`) : séparateur de tableau Markdown.
/// Markdown table separator on a whole line: `[ \t]{0,3}\|?[ \t]{0,3}:?-{3,512}:?[ \t]{0,3}`
/// `(?:\|[ \t]{0,3}:?-{3,512}:?[ \t]{0,3}){1,256}\|?[ \t]{0,3}\r?`. Temps linéaire / linear time.
pub fn table_separator(line: &[char]) -> bool {
    let cell = |pos: usize| -> Option<usize> {
        let start = pos + usize::from(line.get(pos) == Some(&':'));
        let dashes = run(line, start, 513, |c| c == '-');
        let end = start + dashes;
        (3..=512).contains(&dashes).then(|| end + usize::from(line.get(end) == Some(&':')))
    };
    let at_end = |pos: usize| pos == line.len() || (pos + 1 == line.len() && line[pos] == '\r');
    let lead = blanks(line, 0, 7);
    let mut pos = if line.get(lead) == Some(&'|') {
        let inner = blanks(line, lead + 1, 4);
        if lead > 3 || inner > 3 {
            return false;
        }
        lead + 1 + inner
    } else if lead > 6 {
        return false;
    } else {
        lead
    };
    let Some(end) = cell(pos) else {
        return false;
    };
    pos = end;
    let mut groups = 0;
    loop {
        let gap = blanks(line, pos, 7);
        let bar = pos + gap;
        if line.get(bar) != Some(&'|') {
            return groups >= 1 && gap <= 6 && at_end(bar);
        }
        let inner = blanks(line, bar + 1, 4);
        if gap > 3 || inner > 3 {
            return false;
        }
        match cell(bar + 1 + inner) {
            Some(end) if groups < 256 => {
                groups += 1;
                pos = end;
            }
            Some(_) => return false,
            None => return groups >= 1 && at_end(bar + 1 + inner),
        }
    }
}

/// `_NAME_CELL_RE`, correspondance totale : `[^\W\d_](?:[^\W\d_'. -]|[ '.-](?=[^\W\d_ ])){0,58}\.?`.
/// Un point final ne peut venir que de `\.?` / a final dot can only be the trailing `\.?`.
pub fn name_cell(chars: &Chars, cell: &[char]) -> bool {
    let letter = |c: Option<&char>| c.is_some_and(|&c| chars.is(c, LETTER));
    if !letter(cell.first()) {
        return false;
    }
    let body_end = if cell.len() > 1 && cell[cell.len() - 1] == '.' { cell.len() - 1 } else { cell.len() };
    body_end - 1 <= 58
        && (1..body_end)
            .all(|i| letter(cell.get(i)) || (matches!(cell[i], ' ' | '\'' | '.' | '-') && letter(cell.get(i + 1))))
}

/// `_FIELD_WORD_RE` en `pos` : `[^\W\d_]{2,30}(?:['-][^\W\d_]{1,30}){0,3}`, sans ancre de fin : gloutonne,
/// une suite de plus de 30 lettres est coupée. No end anchor: greedy, longer letter runs are cut at 30.
pub fn field_word(chars: &Chars, text: &[char], pos: usize) -> Option<usize> {
    let letter = |c: char| chars.is(c, LETTER);
    let first = run(text, pos, 31, letter);
    if first < 2 {
        return None;
    }
    let mut end = pos + first.min(30);
    if first > 30 {
        return Some(end);
    }
    for _ in 0..3 {
        if !(matches!(text.get(end), Some('\'' | '-')) && text.get(end + 1).is_some_and(|&c| letter(c))) {
            break;
        }
        let len = run(text, end + 1, 31, letter);
        end += 1 + len.min(30);
        if len > 30 {
            break;
        }
    }
    Some(end)
}

/// `_FIELD_GAP_RE` en `pos` : `[ \t]{1,2}`.
pub fn field_gap(text: &[char], pos: usize) -> Option<usize> {
    after_direct(text, pos)
}

/// `_FIELD_END_RE` en `pos` : `[ \t]{0,2}(?:[\r\n,;|()\[\]/]|$)|[ \t]{2}|[ \t](?=[UPPER])`.
pub fn field_end(chars: &Chars, text: &[char], pos: usize) -> bool {
    let lead = blanks(text, pos, 3);
    if lead >= 2 {
        return true;
    }
    let end = pos + lead;
    let closing = end == text.len() || matches!(text[end], '\r' | '\n' | ',' | ';' | '|' | '(' | ')' | '[' | ']' | '/');
    closing || (lead == 1 && text.get(end).is_some_and(|&c| chars.is(c, CAP)))
}

/// `[ \t]{1,2}` d'en-tête des motifs suivants : un troisième blanc fait échouer / a third blank fails.
fn one_or_two_blanks(text: &[char], pos: usize) -> Option<usize> {
    let len = blanks(text, pos, 3);
    (1..=2).contains(&len).then_some(pos + len)
}

/// `_NUMBER_AFTER_RE` en `pos` : `[ \t]{1,2}(?:[0-9]|[IVXLCDM]{1,6}\b)`.
pub fn number_after(chars: &Chars, text: &[char], pos: usize) -> bool {
    let Some(start) = one_or_two_blanks(text, pos) else {
        return false;
    };
    if text.get(start).is_some_and(|c| c.is_ascii_digit()) {
        return true;
    }
    let len = run(text, start, 7, |c| "IVXLCDM".contains(c));
    (1..=6).contains(&len) && !text.get(start + len).is_some_and(|&c| chars.is(c, WORD))
}

/// `_YEAR_AFTER_RE` en `pos` : `[ \t]{1,2}(?:19|20)[0-9]{2}(?![0-9])`.
pub fn year_after(text: &[char], pos: usize) -> bool {
    let Some(start) = one_or_two_blanks(text, pos) else {
        return false;
    };
    let digit = |i: usize| text.get(i).is_some_and(|c| c.is_ascii_digit());
    (starts_with(text, start, "19") || starts_with(text, start, "20"))
        && digit(start + 2)
        && digit(start + 3)
        && !digit(start + 4)
}

/// `_LABEL_AHEAD_RE` en `pos` : `(?:[ \t]{1,4}[^\W\d_][\w'’()-]{0,40}){1,4}[ \t]{0,4}:`, l'étiquette suivante
/// (un à quatre mots puis « : »). Un mot ne contient ni blanc ni « : » : l'analyse gloutonne est la seule possible.
/// The next field label (one to four words, then ':'); a word holds neither a blank nor ':', so greedy is the only
/// parse.
pub fn label_ahead(chars: &Chars, text: &[char], pos: usize) -> bool {
    let word_char = |c: char| chars.is(c, WORD) || matches!(c, '\'' | '’' | '(' | ')' | '-');
    let mut at = pos;
    for words in 0..=4 {
        let gap = blanks(text, at, 5);
        let next = at + gap;
        if words > 0 && gap <= 4 && text.get(next) == Some(&':') {
            return true;
        }
        if words == 4 || !(1..=4).contains(&gap) || !text.get(next).is_some_and(|&c| chars.is(c, LETTER)) {
            return false;
        }
        let tail = run(text, next + 1, 41, word_char);
        if tail > 40 {
            return false; // mot trop long : ni blanc ni « : » ne peut suivre / word too long
        }
        at = next + 1 + tail;
    }
    false
}

/// `_SERIES_AFTER_RE` en `pos` : `[ \t]{1,2}(?:[nN][°º]|[0-9])`, un numéro après une lettre de série.
/// A number after a series letter ("Bodacc A n° 2026…").
pub fn series_after(text: &[char], pos: usize) -> bool {
    let Some(start) = one_or_two_blanks(text, pos) else {
        return false;
    };
    text.get(start).is_some_and(char::is_ascii_digit)
        || (matches!(text.get(start), Some('n' | 'N')) && matches!(text.get(start + 1), Some('°' | 'º')))
}

/// `_NEXT_WORD_RE` en `pos` : `[ \t]{1,2}([a-zà-ÿœæ'’-]{2,30})`, renvoie le groupe 1 / returns group 1.
/// « æ » appartient déjà à `à-ÿ` / "æ" already lies in `à-ÿ`.
pub fn next_word(text: &[char], pos: usize) -> Option<(usize, usize)> {
    let start = one_or_two_blanks(text, pos)?;
    let len = run(text, start, 30, |c| matches!(c, 'a'..='z' | 'à'..='ÿ' | 'œ' | '\'' | '’' | '-'));
    (len >= 2).then_some((start, start + len))
}

/// `_VOCATIVE_RE` en `pos` : `[ \t]{0,2}(?:[,!?]|\r?\n|$)`.
pub fn vocative(text: &[char], pos: usize) -> bool {
    let lead = blanks(text, pos, 3);
    let end = pos + lead;
    lead <= 2
        && (end == text.len()
            || matches!(text[end], ',' | '!' | '?' | '\n')
            || (text[end] == '\r' && text.get(end + 1) == Some(&'\n')))
}

/// `ORDINAL_RE`, correspondance totale : `[IVXLCDM]{1,6}(?:er|re|e|ème|eme)?`.
pub fn ordinal(s: &[char]) -> bool {
    let len = run(s, 0, 7, |c| "IVXLCDM".contains(c));
    let suffix = &s[len.min(s.len())..];
    (1..=6).contains(&len)
        && (suffix.is_empty() || ["er", "re", "e", "ème", "eme"].iter().any(|w| suffix.iter().copied().eq(w.chars())))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(s: &str) -> Vec<char> {
        s.chars().collect()
    }

    #[test]
    fn gaps() {
        assert!(space_gap(&v(" ")) && space_gap(&v("  de ")) && space_gap(&v(" de la ")) && space_gap(&v(" d'")));
        assert!(!space_gap(&v("   ")) && !space_gap(&v(" de")) && !space_gap(&v(" de   ")) && !space_gap(&v(" x ")));
        assert!(newline_gap(&v("\n")) && newline_gap(&v("  \r\n ")) && !newline_gap(&v("   \n")));
        assert!(hyphen_wrap(&v("-\n")) && !hyphen_wrap(&v("- x\n")));
        assert!(initial_gap(&v(".")) && initial_gap(&v(". ")) && initial_gap(&v(".-")) && !initial_gap(&v(".   ")));
        assert!(list_gap(&v(", ")) && list_gap(&v(" et ")) && list_gap(&v(", et ")) && list_gap(&v(";")));
        assert!(!list_gap(&v(" ")) && !list_gap(&v(",   ")) && !list_gap(&v(" et")) && !list_gap(&v(" puis ")));
    }

    #[test]
    fn anchored_matches() {
        let t = v("de la  Fontaine");
        assert_eq!(particle_at(&t, 0), Some(3)); // « de » puis « la » n'est pas dans la liste / "la" not listed
        assert_eq!(particle_at(&v("des  van X"), 0), Some(9));
        assert_eq!(particle_at(&v("D'Artagnan"), 0), Some(2));
        assert_eq!(after_eponym(&v(" de l'Église"), 0), Some(4)); // s'arrête après « de » / stops after "de"
        assert_eq!(after_eponym(&v(". de la Paix"), 0), Some(8));
        assert_eq!(after_eponym(&v("\nd'Arc"), 0), Some(3));
        assert_eq!(after_eponym(&v("x"), 0), None);
        assert_eq!(after_cue(&v("  , X"), 0), Some(4));
        assert_eq!(after_cue(&v(",X"), 0), None);
        assert_eq!(unwrap(&v("Anne-\n Sophie")).as_ref(), v("Anne-Sophie").as_slice());
        assert_eq!(unwrap(&v("Anne -\n")).as_ref(), v("Anne -").as_slice());
        assert_eq!(after_last_label_separator(&v("a  b|c\td e")), v("d e").as_slice());
        assert!(table_separator(&v("|---|:---:|")) && table_separator(&v("--- | ---\r")));
        assert!(!table_separator(&v("|---|")) && !table_separator(&v("    |---|---|")));
        assert!(ordinal(&v("XIV")) && ordinal(&v("Ier")) && !ordinal(&v("IVXLCDMI")) && !ordinal(&v("Ixe")));
        assert!(year_after(&v(" 2024"), 0) && !year_after(&v(" 20245"), 0) && !year_after(&v("   2024"), 0));
        assert_eq!(next_word(&v(" rose des"), 0), Some((1, 5)));
        assert!(vocative(&v(" ,"), 0) && vocative(&v(""), 0) && !vocative(&v("   ,"), 0));
        assert!(series_after(&v(" n° 2026"), 0) && series_after(&v("  12"), 0) && series_after(&v(" Nº"), 0));
        assert!(!series_after(&v(", Brakvoort T"), 0) && !series_after(&v("   12"), 0) && !series_after(&v(""), 0));
    }

    #[test]
    fn next_label_ahead() {
        let chars = Chars::new(crate::unicode::test_unicode());
        let ahead = |s: &str| label_ahead(&chars, &v(s), 0);
        // Un à quatre mots puis « : » / one to four words, then ':'.
        assert!(ahead(" Prénom : Jean") && ahead(" Date de naissance : 1980") && ahead("\tPrénom(s): x"));
        assert!(ahead(" Né le :") && ahead("    Matricule    :"));
        assert!(!ahead(" INDUSTRIES") && !ahead(" A B C D E :") && !ahead("Prénom :") && !ahead("     Prénom :"));
        assert!(!ahead(" Prénom.") && !ahead(" 12 :") && !ahead(&format!(" {} :", "a".repeat(42))));
    }
}
