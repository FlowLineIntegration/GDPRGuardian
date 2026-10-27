//! Jumeau de `detectors/intl.py:PersonalSiteDetector` (`URL_PERSONAL_NAME`, raison `personal_site_name`) : site
//! personnel dont l'hôte reprend le nom d'une personne citée dans le même texte (voie perf, 1.0.2).
//!
//! Twin of `PersonalSiteDetector`: a personal website whose host repeats the name of a person quoted in the same
//! text. Mêmes zones, même valeur (l'hôte replié), dans le même ordre ; positions en caractères Python. Le code
//! Python reste la référence. Hors du domaine du jumeau, `None` : le détecteur Python reprend le texte entier
//! (caractères que `re.IGNORECASE` égale à une lettre ASCII : « İ », « ı », « ſ », « K » ; mot replié vide). Le
//! repli des mots non ASCII (`_fold_word` : NFKD, minuscules, sans diacritiques) reste en Python (`fold`). Same
//! spans, same value, same order; outside the twin's domain, `None`: the Python detector takes the whole text.

use std::collections::HashSet;

use super::chars::decode;

/// Domaines de premier niveau de `_url` et `_tld`, dans l'ordre de l'alternative (aucun n'est préfixe d'un autre).
/// Top-level domains of `_url` and `_tld`, in the alternation's order (none is a prefix of another).
const TLDS: [&str; 18] = [
    "fr", "com", "net", "org", "eu", "me", "io", "info", "blog", "site", "online", "page", "dev", "be", "ch", "ca",
    "pro", "name",
];
/// Lettres non ASCII que `re.IGNORECASE` égale à `[a-z]` / non-ASCII letters `re.IGNORECASE` equates with `[a-z]`.
const IGNORECASE_EXTRA: [char; 4] = ['\u{130}', '\u{131}', '\u{17F}', '\u{212A}'];
/// `_reach` : le nom est cherché à 2 000 caractères au plus de l'adresse / name searched within 2,000 characters.
const REACH: usize = 2000;
/// Longueur minimale d'un hôte replié et d'une forme de nom / minimal host and form length.
const MIN_LENGTH: usize = 6;

/// Une zone trouvée : (début, fin, hôte replié) / a span found: (start, end, folded host).
pub(crate) type Found = (usize, usize, String);

/// `PersonalSiteDetector.detect` après le préfiltre (`ctx.has(_prefilters)`, lu par l'appelant) ; `None` hors du
/// domaine (le détecteur Python reprend). `fold` : `_fold_word` d'un mot non ASCII, `None` en cas d'erreur.
/// After the prefilter (read by the caller); `None` outside the domain. `fold`: `_fold_word` of a non-ASCII word.
pub(crate) fn detect(
    norm: &str,
    is_word: impl Fn(char) -> bool,
    is_letter: impl Fn(char) -> bool,
    mut fold: impl FnMut(&str) -> Option<String>,
) -> Option<Vec<Found>> {
    if norm.chars().any(|c| IGNORECASE_EXTRA.contains(&c)) {
        return None;
    }
    let text = decode(norm);
    let candidates: Vec<Found> =
        urls(&text, &is_word).into_iter().filter(|(_, _, host)| host.chars().count() >= MIN_LENGTH).collect();
    if candidates.is_empty() {
        return Some(Vec::new());
    }
    // Fenêtres fusionnées : chaque caractère lu une fois au plus / merged windows: each character read once at most.
    let mut windows: Vec<(usize, usize)> = Vec::new();
    for &(start, end, _) in &candidates {
        let (lo, hi) = (start.saturating_sub(REACH), (end + REACH).min(text.len()));
        match windows.last_mut() {
            Some(last) if lo <= last.1 => last.1 = last.1.max(hi),
            _ => windows.push((lo, hi)),
        }
    }
    let mut forms = Vec::with_capacity(windows.len());
    for &(lo, hi) in &windows {
        forms.push(name_forms(&text[lo..hi], &is_letter, &mut fold)?);
    }
    let mut spans = Vec::new();
    for (start, end, host) in candidates {
        let index = windows.iter().position(|&(lo, hi)| lo <= start && end <= hi)?;
        if forms[index].contains(&host) {
            spans.push((start, end, host));
        }
    }
    Some(spans)
}

/// `(?i)` sur un caractère ASCII (les lettres non ASCII équivalentes sont hors domaine) / ASCII case-insensitive.
fn eq_ci(c: Option<char>, lower: u8) -> bool {
    c.is_some_and(|c| c.is_ascii() && c.to_ascii_lowercase() as u32 == u32::from(lower))
}

fn literal_ci(text: &[char], at: usize, literal: &str) -> bool {
    literal.bytes().enumerate().all(|(k, b)| eq_ci(text.get(at + k).copied(), b))
}

/// Fin du domaine de premier niveau qui commence en `at`, ou `None` / end of the TLD starting at `at`.
fn tld_at(text: &[char], at: usize) -> Option<usize> {
    TLDS.iter().find(|tld| literal_ci(text, at, tld)).map(|tld| at + tld.len())
}

/// `_urls` : les correspondances de `_url`, ligne par ligne sur les lignes qui portent un domaine connu ; hôte replié
/// (minuscules, sans « . », « - », « _ »). `_url`'s matches on the lines holding a known TLD; folded host.
fn urls(text: &[char], is_word: &impl Fn(char) -> bool) -> Vec<Found> {
    let mut found = Vec::new();
    let mut line_end = 0;
    for at in 0..text.len() {
        if at < line_end || text[at] != '.' || tld_at(text, at + 1).is_none() {
            continue;
        }
        let line_start = text[..at].iter().rposition(|&c| c == '\n').map_or(0, |p| p + 1);
        line_end = text[at..].iter().position(|&c| c == '\n').map_or(text.len(), |p| at + p);
        // `finditer(text, start, end)` : regard arrière sur le vrai texte, rien au-delà de `end`.
        // Look-behind on the real text, nothing past `end`.
        let view = &text[..line_end];
        let mut start = line_start;
        while start < line_end {
            match url_at(view, start, is_word) {
                Some((end, host_start, host_end)) => {
                    let host: String = view[host_start..host_end]
                        .iter()
                        .filter(|c| !matches!(c, '.' | '-' | '_'))
                        .map(char::to_ascii_lowercase)
                        .collect();
                    found.push((start, end, host));
                    start = end;
                }
                None => start += 1,
            }
        }
    }
    found
}

/// `[a-z0-9]` sous `re.IGNORECASE` (domaine ASCII) / under `re.IGNORECASE` (ASCII domain).
fn host_end_char(c: char) -> bool {
    c.is_ascii_alphanumeric()
}

/// `[a-z0-9.\-_]` sous `re.IGNORECASE`.
fn host_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | '_')
}

/// `_url.match` en `start`, ordre de retour arrière de `re` : (fin, début et fin de l'hôte), ou `None`.
/// `_url.match` at `start`, in `re`'s backtracking order: (end, host start and end), or `None`.
fn url_at(text: &[char], start: usize, is_word: &impl Fn(char) -> bool) -> Option<(usize, usize, usize)> {
    // (?<![\w@.\-/])
    if start > 0 {
        let before = text[start - 1];
        if is_word(before) || matches!(before, '@' | '.' | '-' | '/') {
            return None;
        }
    }
    // (?:https?://)? : « s » pris d'abord, puis sans « s », puis sans préfixe / "s" first, then without, then none.
    let mut protocols = Vec::with_capacity(3);
    if literal_ci(text, start, "http") {
        if literal_ci(text, start + 4, "s://") {
            protocols.push(8);
        }
        if literal_ci(text, start + 4, "://") {
            protocols.push(7);
        }
    }
    protocols.push(0);
    for protocol in protocols {
        let after_protocol = start + protocol;
        let www: &[usize] = if literal_ci(text, after_protocol, "www.") { &[4, 0] } else { &[0] };
        for &w in www {
            let host_start = after_protocol + w;
            if !text.get(host_start).copied().is_some_and(host_end_char) {
                continue;
            }
            // (?:[a-z0-9.\-_]{0,60}[a-z0-9])? glouton, puis absent / greedy, then absent.
            let run = text
                .get(host_start + 1..)
                .map_or(0, |rest| rest.iter().take(61).take_while(|&&c| host_char(c)).count());
            let longest = run.min(61);
            let mut ends: Vec<usize> = (0..longest)
                .rev()
                .filter(|&k| k <= 60 && host_end_char(text[host_start + 1 + k]))
                .map(|k| host_start + 2 + k)
                .collect();
            ends.push(host_start + 1);
            for host_end in ends {
                if let Some(end) = after_host(text, host_end, is_word) {
                    return Some((end, host_start, host_end));
                }
            }
        }
    }
    None
}

/// `\.(?:tld)(?:/[\w.\-%~/]{0,100})?(?<![.,;:)])(?![\w@\-])` en `at` : fin de la correspondance, ou `None`.
fn after_host(text: &[char], at: usize, is_word: &impl Fn(char) -> bool) -> Option<usize> {
    if text.get(at) != Some(&'.') {
        return None;
    }
    let tld_end = tld_at(text, at + 1)?;
    let mut ends = Vec::new();
    if text.get(tld_end) == Some(&'/') {
        let path = text.get(tld_end + 1..).map_or(0, |rest| {
            rest.iter().take(100).take_while(|&&c| is_word(c) || matches!(c, '.' | '-' | '%' | '~' | '/')).count()
        });
        ends.extend((0..=path).rev().map(|j| tld_end + 1 + j));
    }
    ends.push(tld_end);
    ends.into_iter().find(|&end| {
        !matches!(text[end - 1], '.' | ',' | ';' | ':' | ')')
            && !text.get(end).is_some_and(|&c| is_word(c) || matches!(c, '@' | '-'))
    })
}

/// `[A-ZÀ-ÖØ-ÞŒ]`.
fn capital(c: char) -> bool {
    c.is_ascii_uppercase() || ('\u{C0}'..='\u{D6}').contains(&c) || ('\u{D8}'..='\u{DE}').contains(&c) || c == '\u{152}'
}

/// `[ \-\u00A0]`.
fn separator(c: char) -> bool {
    matches!(c, ' ' | '-' | '\u{A0}')
}

/// `_name_forms` sur la fenêtre `text` (une tranche : rien avant, rien après) ; `None` si un repli échoue ou rend un
/// mot vide (Python lèverait). `_name_forms` over the window (a slice); `None` when a fold fails or is empty.
fn name_forms(
    text: &[char],
    is_letter: &impl Fn(char) -> bool,
    fold: &mut impl FnMut(&str) -> Option<String>,
) -> Option<HashSet<String>> {
    let letters = |at: usize| text.get(at..).map_or(0, |rest| rest.iter().take_while(|&&c| is_letter(c)).count());
    let mut forms = HashSet::new();
    let mut at = 0;
    while at < text.len() {
        // _run : (?<![^\W\d_])[A-ZÀ-ÖØ-ÞŒ][^\W\d_]+(?:[ \- ][A-ZÀ-ÖØ-ÞŒ][^\W\d_]+)+
        if !capital(text[at]) || (at > 0 && is_letter(text[at - 1])) {
            at += 1;
            continue;
        }
        let first = letters(at + 1);
        if first == 0 {
            at += 1;
            continue;
        }
        let mut words = vec![(at, at + 1 + first)];
        let mut pos = at + 1 + first;
        while pos + 1 < text.len() && separator(text[pos]) && capital(text[pos + 1]) {
            let more = letters(pos + 2);
            if more == 0 {
                break;
            }
            words.push((pos + 1, pos + 2 + more));
            pos += 2 + more;
        }
        if words.len() < 2 {
            at += 1;
            continue;
        }
        let mut run = Vec::with_capacity(words.len());
        for &(start, end) in &words {
            let word = &text[start..end];
            let folded = if word.iter().all(char::is_ascii) {
                word.iter().map(char::to_ascii_lowercase).collect()
            } else {
                fold(&word.iter().collect::<String>())?
            };
            if folded.is_empty() {
                return None;
            }
            run.push(folded);
        }
        add_forms(&run, &mut forms);
        at = pos;
    }
    Some(forms)
}

/// Formes collées d'une suite de noms repliés, 6 caractères ou plus / glued forms of a folded run, 6 or more.
fn add_forms(run: &[String], forms: &mut HashSet<String>) {
    let initial = |word: &String| word.chars().next().map(String::from).unwrap_or_default();
    for i in 1..run.len() {
        for size in [2, 3] {
            if i + 1 < size {
                continue;
            }
            let parts = &run[i + 1 - size..=i];
            let candidates = [
                parts.concat(),
                parts.iter().rev().map(String::as_str).collect::<String>(),
                initial(&parts[0]) + &parts[1..].concat(),
                initial(&parts[size - 1]) + &parts[..size - 1].concat(),
            ];
            forms.extend(candidates.into_iter().filter(|form| form.chars().count() >= MIN_LENGTH));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn word(c: char) -> bool {
        c.is_alphanumeric() || c == '_'
    }

    fn letter(c: char) -> bool {
        c.is_alphabetic()
    }

    fn run(text: &str) -> Option<Vec<Found>> {
        detect(text, word, letter, |w| Some(w.to_lowercase()))
    }

    #[test]
    fn personal_sites_follow_the_quoted_name() {
        let text =
            "Kevin Lambert publie sur https://kevinlambert.fr et kevin-lambert.fr/blog ; voir aussi klambert.fr.";
        let found = run(text).unwrap();
        let hosts: Vec<&str> = found.iter().map(|(_, _, h)| h.as_str()).collect();
        assert_eq!(hosts, ["kevinlambert", "kevinlambert", "klambert"]);
        assert_eq!(run("Voir https://www.service-public.fr pour Jean Dupont.").unwrap(), Vec::<Found>::new());
        assert!(run("Kevin Lambert : kevınlambert.fr").is_none());
    }
}
