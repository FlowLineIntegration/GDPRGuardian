//! Propagation : toutes les autres occurrences des noms trouvés sont masquées (`engine._propagate`).
//!
//! Propagation: every other occurrence of a found name is masked. Occurrences « la plus longue à gauche »
//! sans chevauchement, comme `keywords.longest_matches` (Aho-Corasick `LeftmostLongest`). Leftmost-longest,
//! non-overlapping matches, as `keywords.longest_matches`.

use std::borrow::Cow;
use std::collections::HashSet;
use std::sync::Arc;

use aho_corasick::{AhoCorasick, MatchKind};
use memchr::memmem::Finder;

use super::chars::{Chars, ALNUM, ALPHA};
use super::indexed::IndexedText;
use super::span::Span;
use super::Unsupported;
use crate::text::{char_at, char_before};

/// Au-delà de (formes × octets), un automate Aho-Corasick devient moins cher qu'une recherche SIMD par
/// forme : sa construction (~40 µs) est amortie. Mesuré : 16 formes, l'automate l'emporte vers 80 Ko.
/// Beyond (forms × bytes), an Aho-Corasick automaton beats one SIMD search per form: its ~40 µs build is
/// amortised. Measured: with 16 forms, the automaton wins from about 80 KB.
const DIRECT_SCAN_BUDGET: usize = 1 << 20;

/// Segments (cellules) d'un texte joint, positions en caractères / segments of a joined text.
pub struct Segments {
    pub starts: Vec<usize>,
    pub ends: Vec<usize>,
}

impl Segments {
    /// Contrôle comme `analyze_segments` les construit : triés, à partir de 0 / validated as Python builds them.
    pub fn new(starts: Vec<usize>, ends: Vec<usize>) -> Option<Self> {
        let ordered = starts.windows(2).all(|w| w[0] <= w[1]) && starts.iter().zip(&ends).all(|(s, e)| s <= e);
        (starts.len() == ends.len() && starts.first().is_none_or(|&s| s == 0) && ordered)
            .then_some(Self { starts, ends })
    }

    pub fn len(&self) -> usize {
        self.starts.len()
    }

    /// `DetectionContext.segment` : (indice, début, fin) du segment de `pos` / segment holding `pos`.
    pub fn locate(&self, pos: usize) -> Option<(usize, usize, usize)> {
        let index = self.starts.partition_point(|&s| s <= pos).checked_sub(1)?;
        Some((index, *self.starts.get(index)?, *self.ends.get(index)?))
    }
}

/// Formes à propager, dans l'ordre d'insertion du dict Python ; la première zone l'emporte. Empruntées au
/// texte et aux zones (seule la forme en capitales est allouée) / borrowed from the text and the spans (only
/// the uppercase form is allocated).
/// Forms to propagate, in Python dict insertion order; the first span wins.
fn sources<'a>(chars: &Chars, text: &IndexedText<'a>, spans: &'a [Span]) -> (Vec<Cow<'a, str>>, Vec<usize>) {
    let mut candidates: Vec<(Cow<'a, str>, usize)> = Vec::new();
    for (index, span) in spans.iter().enumerate() {
        if !span.propagate || !span.personal {
            continue;
        }
        let found = std::iter::once(text.slice(span.start, span.end)).chain(span.forms.iter().map(|f| &**f));
        for form in found {
            let form = chars.strip(form);
            if form.chars().nth(2).is_some() && form.chars().any(|c| chars.is(c, ALPHA)) {
                let upper = chars.upper(form);
                candidates.push((Cow::Borrowed(form), index));
                if upper != form {
                    candidates.push((Cow::Owned(upper), index));
                }
            }
        }
    }
    // `dict.setdefault` : la première occurrence d'une forme garde sa place / the first one keeps its place.
    let first: Vec<bool> = {
        let mut seen: HashSet<&str> = HashSet::with_capacity(candidates.len());
        candidates.iter().map(|(form, _)| seen.insert(form)).collect()
    };
    candidates.into_iter().zip(first).filter_map(|(candidate, first)| first.then_some(candidate)).unzip()
}

/// Occurrences par recherche SIMD de chaque forme, fusionnées « la plus longue à gauche » : chaque forme
/// garde sa prochaine occurrence après la dernière retenue. (forme, début, fin) en octets.
/// One SIMD search per form, merged leftmost-longest: each form keeps its next occurrence after the last
/// selected match. (form, start, end) in bytes.
fn direct_matches<F: AsRef<str>>(forms: &[F], text: &str) -> Vec<(usize, usize, usize)> {
    let bytes = text.as_bytes();
    let finders: Vec<Finder> = forms.iter().map(|f| Finder::new(f.as_ref().as_bytes())).collect();
    let next = |finder: &Finder, from: usize| bytes.get(from..).and_then(|rest| finder.find(rest)).map(|at| from + at);
    let mut candidates: Vec<Option<usize>> = finders.iter().map(|f| next(f, 0)).collect();
    let mut found = Vec::new();
    loop {
        // La plus à gauche, puis la plus longue (deux formes distinctes ne coïncident jamais) / leftmost, longest.
        let best = candidates
            .iter()
            .zip(forms)
            .enumerate()
            .filter_map(|(index, (start, form))| start.map(|start| (start, form.as_ref().len(), index)))
            .min_by(|a, b| a.0.cmp(&b.0).then(b.1.cmp(&a.1)));
        let Some((start, length, index)) = best else {
            return found;
        };
        let end = start + length;
        found.push((index, start, end));
        for (candidate, finder) in candidates.iter_mut().zip(&finders) {
            if candidate.is_some_and(|at| at < end) {
                *candidate = next(finder, end);
            }
        }
    }
}

/// Même résultat par un automate Aho-Corasick, pour les grands textes / same result by an automaton.
fn automaton_matches<F: AsRef<str>>(forms: &[F], text: &str) -> Result<Vec<(usize, usize, usize)>, Unsupported> {
    let automaton = AhoCorasick::builder()
        .match_kind(MatchKind::LeftmostLongest)
        .build(forms.iter().map(AsRef::as_ref))
        .map_err(|_| Unsupported)?;
    Ok(automaton.find_iter(text).map(|m| (m.pattern().as_usize(), m.start(), m.end())).collect())
}

/// `keywords.longest_matches`, en octets / in bytes.
fn longest_matches<F: AsRef<str>>(forms: &[F], text: &str) -> Result<Vec<(usize, usize, usize)>, Unsupported> {
    if forms.len().saturating_mul(text.len()) <= DIRECT_SCAN_BUDGET {
        Ok(direct_matches(forms, text))
    } else {
        automaton_matches(forms, text)
    }
}

/// `engine._propagate` : `spans` triées par début et disjointes ; le résultat l'est aussi.
/// `spans` sorted by start and disjoint; so is the result.
pub fn propagate(
    chars: &Chars,
    text: &IndexedText,
    spans: Vec<Span>,
    segments: Option<&Segments>,
    priority: i64,
) -> Result<Vec<Span>, Unsupported> {
    let (forms, owners) = sources(chars, text, &spans);
    if forms.is_empty() {
        return Ok(spans);
    }
    let haystack = text.as_str();
    let mut added: Vec<Span> = Vec::new();
    let found = longest_matches(&forms, haystack)?;
    // « propagated:<source> » d'une zone, partagé par toutes ses occurrences / shared by all its occurrences.
    let mut propagated: Vec<Option<Arc<str>>> = vec![None; spans.len()];
    for (form, start_byte, end_byte) in found {
        let alnum = |c: Option<char>| c.is_some_and(|c| chars.is(c, ALNUM));
        if alnum(char_before(haystack, start_byte)) || alnum(char_at(haystack, end_byte)) {
            continue;
        }
        let (start, end) = (text.char_index(start_byte), text.char_index(end_byte));
        // Les occurrences sont croissantes et disjointes : seules les zones d'origine peuvent chevaucher.
        // Matches are increasing and disjoint: only the original spans can overlap.
        let next = spans.partition_point(|s| s.start <= start);
        if next.checked_sub(1).and_then(|i| spans.get(i)).is_some_and(|s| s.end > start)
            || spans.get(next).is_some_and(|s| s.start < end)
        {
            continue;
        }
        if let Some(segments) = segments {
            if segments.locate(start).is_some_and(|(_, _, hi)| end > hi) {
                continue;
            }
        }
        let Some((owner, source)) = owners.get(form).and_then(|&i| Some((i, spans.get(i)?))) else {
            continue;
        };
        let label = propagated
            .get_mut(owner)
            .map(|slot| slot.get_or_insert_with(|| format!("propagated:{}", source.source).into()).clone());
        let Some(label) = label else {
            continue;
        };
        added.push(Span {
            start,
            end,
            entity: source.entity.clone(),
            label: source.label.clone(),
            source: label,
            score: source.score * 0.95,
            priority,
            value: None,
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: None,
            origin: None,
        });
    }
    if added.is_empty() {
        return Ok(spans);
    }
    // Fusion par début (jamais égaux : une occurrence ne commence pas dans une zone) / merge by start.
    let mut merged = Vec::with_capacity(spans.len() + added.len());
    let mut added = added.into_iter().peekable();
    for span in spans {
        while let Some(next) = added.next_if(|a| a.start < span.start) {
            merged.push(next);
        }
        merged.push(span);
    }
    merged.extend(added);
    Ok(merged)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::finalize::chars::test_rules;
    use crate::finalize::span::span;

    #[test]
    fn other_occurrences_are_masked_on_word_boundaries() {
        let rules = test_rules();
        let chars = Chars::new(&rules);
        let text = IndexedText::new("Dupont, DUPONT, Dupontel et Dupont.").expect("small");
        let mut name = span(0, 6, "PERSON", 60);
        name.propagate = true;
        let spans = propagate(&chars, &text, vec![name], None, 50).expect("small text");
        let found: Vec<&str> = spans.iter().map(|s| text.slice(s.start, s.end)).collect();
        assert_eq!(found, ["Dupont", "DUPONT", "Dupont"]);
        assert_eq!(&*spans[1].source, "propagated:test");
    }

    #[test]
    fn direct_search_equals_the_automaton() {
        // Générateur congruentiel : formes qui se chevauchent sur un petit alphabet, multioctets compris.
        // Linear congruential generator: overlapping forms over a small alphabet, multi-byte included.
        let alphabet = ['a', 'b', 'é', '😀', ' '];
        let mut seed = 0x2545_f491_4f6c_dd1du64;
        let mut pick = |n: usize| {
            seed = seed.wrapping_mul(6_364_136_223_846_793_005).wrapping_add(1_442_695_040_888_963_407);
            (seed >> 33) as usize % n
        };
        for _ in 0..500 {
            let text: String = (0..pick(60)).map(|_| alphabet[pick(alphabet.len())]).collect();
            let mut forms: Vec<String> = Vec::new();
            for _ in 0..1 + pick(6) {
                let form: String = (0..1 + pick(4)).map(|_| alphabet[pick(alphabet.len())]).collect();
                if !forms.contains(&form) {
                    forms.push(form);
                }
            }
            assert_eq!(direct_matches(&forms, &text), automaton_matches(&forms, &text).expect("small"), "{forms:?}");
        }
    }

    #[test]
    fn segments_bound_matches() {
        let segments = Segments::new(vec![0, 8], vec![6, 12]).expect("valid");
        assert_eq!(segments.locate(7), Some((0, 0, 6)));
        assert!(Segments::new(vec![1], vec![2]).is_none());
    }
}
