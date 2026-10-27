//! Contrôle final de sortie, variante restreinte : jumeau de `selfcheck.py` (1.0.2, REGLES.md « Contrôle final de
//! sortie ») / output self-check, restricted variant: twin of `selfcheck.py`.
//!
//! Toute valeur d'identifiant masquée quelque part (au moins 6 caractères, un chiffre ou « @ ») et restée en clair
//! ailleurs, à la casse et aux accents près, est masquée avec la même valeur (même balise), règle
//! `output_check:<règle>`, raison `output_check` ; jamais au milieu d'un nombre, jamais sur une zone existante ;
//! les règles « keep » passent après. Every identifier value masked somewhere and still in clear elsewhere, up to
//! case and accents, is masked with the same value (same tag); never inside a number, never over an existing span;
//! keep rules run afterwards.

use std::collections::HashSet;

use super::chars::{Chars, DIGIT};
use super::indexed::IndexedText;
use super::propagate::longest_matches;
use super::span::Span;
use super::Unsupported;

/// `selfcheck.CHECK_MIN`.
const CHECK_MIN: usize = 6;
/// `selfcheck.CHECK_MAX` : au-delà, pas une valeur d'identifiant ; borne le coût sur un texte hostile.
const CHECK_MAX: usize = 128;
/// `selfcheck.CHECK_REASON`.
const CHECK_REASON: &str = "output_check";

/// `_inside_number` : deux chiffres voisins, une borne au milieu d'un nombre / a bound inside a number.
fn inside_number(chars: &Chars, a: char, b: char) -> bool {
    chars.is(a, DIGIT) && chars.is(b, DIGIT)
}

/// `selfcheck._AMOUNT_*` : signes et mots d'un montant ou d'une mesure (troisième tour) / amount signs and words.
const AMOUNT_SIGNS_AFTER: [char; 5] = ['€', '$', '£', '%', '‰'];
const AMOUNT_SIGNS_BEFORE: [char; 3] = ['€', '$', '£'];
const AMOUNT_WORDS_AFTER: [&str; 35] = [
    "eur", "euro", "euros", "keur", "meur", "usd", "dollar", "dollars", "gbp", "chf", "xpf", "fcfa", "km", "kg", "mg",
    "cm", "mm", "ml", "cl", "kw", "kwh", "mw", "mwh", "ko", "mo", "go", "kb", "mb", "gb", "octet", "octets", "byte",
    "bytes", "ht", "ttc",
];
const AMOUNT_WORDS_BEFORE: [&str; 6] = ["eur", "euro", "euros", "usd", "gbp", "chf"];

fn amount_blank(c: Option<char>) -> bool {
    matches!(c, Some(' ' | '\t' | '\u{a0}' | '\u{202f}'))
}

/// `selfcheck._amount` : la suite de chiffres [start, end) est-elle un montant ou une mesure ? Positions de caractères.
/// Is the digit run an amount or a measure? Character positions.
fn amount(text: &IndexedText, start: usize, end: usize) -> bool {
    let at = |i: usize| text.char_at(i);
    let digit = |c: Option<char>| c.is_some_and(|c| c.is_ascii_digit());
    if matches!(at(end), Some(',' | '.')) && digit(at(end + 1)) {
        return true;
    }
    if start > 1 && matches!(at(start - 1), Some(',' | '.')) && digit(at(start - 2)) {
        return true;
    }
    let i = if amount_blank(at(end)) { end + 1 } else { end };
    if at(i).is_some_and(|c| AMOUNT_SIGNS_AFTER.contains(&c)) {
        return true;
    }
    let mut j = i;
    let mut word = String::new();
    while let Some(c) = at(j).filter(char::is_ascii_alphabetic) {
        word.push(c.to_ascii_lowercase());
        j += 1;
    }
    if (!word.is_empty() && AMOUNT_WORDS_AFTER.contains(&word.as_str()))
        || (matches!(word.as_str(), "k" | "m" | "md") && at(j) == Some('€'))
    {
        return true;
    }
    let k = if start > 0 && amount_blank(at(start - 1)) { start - 1 } else { start };
    if k > 0 && at(k - 1).is_some_and(|c| AMOUNT_SIGNS_BEFORE.contains(&c)) {
        return true;
    }
    let mut m = k;
    let mut before = Vec::new();
    while m > 0 {
        match at(m - 1).filter(char::is_ascii_alphabetic) {
            Some(c) => before.push(c.to_ascii_lowercase()),
            None => break,
        }
        m -= 1;
    }
    let word: String = before.iter().rev().collect();
    AMOUNT_WORDS_BEFORE.contains(&word.as_str())
}

/// `selfcheck.output_check` : `spans` triées par début et disjointes, le résultat aussi / sorted and disjoint.
pub(super) fn output_check(chars: &Chars, text: &IndexedText, spans: Vec<Span>) -> Result<Vec<Span>, Unsupported> {
    // Clés repliées zone par zone (le repli garde la longueur) : le texte entier n'est replié que s'il y en a.
    // Keys folded span by span (folding keeps the length): the whole text is folded only when there are some.
    let mut keys: Vec<String> = Vec::new();
    let mut owners: Vec<usize> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for (position, span) in spans.iter().enumerate() {
        if !span.personal {
            continue;
        }
        if span.end - span.start > CHECK_MAX {
            continue;
        }
        let key = chars.fold(text.slice(span.start, span.end));
        if key.chars().count() < CHECK_MIN || key.contains('\n') || !key.chars().any(|c| c.is_ascii_digit() || c == '@')
        {
            continue;
        }
        if seen.insert(key.clone()) {
            keys.push(key);
            owners.push(position);
        }
    }
    if keys.is_empty() {
        return Ok(spans);
    }
    let folded = chars.fold(text.as_str());
    let index = IndexedText::new(&folded).ok_or(Unsupported)?;
    let starts: Vec<usize> = spans.iter().map(|s| s.start).collect();
    let cut = |a: Option<char>, b: Option<char>| match (a, b) {
        (Some(a), Some(b)) => inside_number(chars, a, b),
        _ => false,
    };
    let mut added: Vec<Span> = Vec::new();
    for (form, start_byte, end_byte) in longest_matches(&keys, &folded)? {
        let (start, end) = (index.char_index(start_byte), index.char_index(end_byte));
        if (start > 0 && cut(text.char_at(start - 1), text.char_at(start)))
            || (end > 0 && cut(text.char_at(end - 1), text.char_at(end)))
        {
            continue;
        }
        if keys.get(form).is_some_and(|key| key.bytes().all(|b| b.is_ascii_digit())) && amount(text, start, end) {
            continue;
        }
        let k = starts.partition_point(|&s| s < end);
        if k > 0 && spans[k - 1].end > start {
            continue; // déjà une zone, masquée ou gardée / already a span, masked or kept
        }
        let Some(source) = owners.get(form).and_then(|&i| spans.get(i)) else {
            continue;
        };
        let value = source.value.clone().unwrap_or_else(|| text.slice(source.start, source.end).to_owned());
        added.push(Span {
            start,
            end,
            entity: source.entity.clone(),
            label: source.label.clone(),
            source: format!("{CHECK_REASON}:{}", source.source).into(),
            score: source.score,
            priority: source.priority,
            value: Some(value),
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: Some(CHECK_REASON.into()),
            origin: None,
        });
    }
    if added.is_empty() {
        return Ok(spans);
    }
    let mut spans = spans;
    spans.extend(added);
    spans.sort_by_key(|s| s.start);
    Ok(spans)
}
