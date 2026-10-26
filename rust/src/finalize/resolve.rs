//! Filtrage, fusion et résolution des chevauchements / filtering, merging and overlap resolution.
//!
//! Port exact de `engine._apply_keep`, de la boucle de `engine._finalize`, de `_trim_honorific`, de
//! `merge_same_entity` et de `resolve` (Python). Exact port of the Python functions of the same names.

use std::collections::{BTreeMap, HashSet};
use std::sync::Arc;

use super::chars::{Chars, ALNUM, ALPHA};
use super::indexed::IndexedText;
use super::span::{py_max, Span};

/// Réglages de filtrage et de fusion / filtering and merging settings.
pub struct Policy {
    pub min_score: f64,
    /// Liste d'autorisation, termes repliés et rognés / allow list, folded and stripped terms.
    pub allow: HashSet<String>,
    /// `types.MERGEABLE_ENTITIES`.
    pub mergeable: Vec<Box<str>>,
}

impl Policy {
    pub fn mergeable(&self, entity: &str) -> bool {
        self.mergeable.iter().any(|m| **m == *entity)
    }
}

/// Zones « keep » des règles personnalisées / keep zones of custom rules.
pub struct KeepRules {
    /// `custom.KEEP_ENTITY`.
    pub entity: Box<str>,
    /// `engine._UNMASKABLE`.
    pub unmaskable: HashSet<Box<str>>,
    /// `types.PRIORITY_VALIDATED`.
    pub priority_validated: i64,
}

/// `engine._apply_keep` : une détection entièrement comprise dans une zone « keep » reste en clair, sauf un
/// identifiant officiel validé. A detection fully inside a keep zone stays in clear, except a validated
/// official identifier.
pub fn apply_keep(rules: &KeepRules, spans: Vec<Span>) -> Vec<Span> {
    let mut zones: Vec<(usize, usize, Arc<str>)> =
        spans.iter().filter(|s| *s.entity == *rules.entity).map(|s| (s.start, s.end, s.source.clone())).collect();
    if zones.is_empty() {
        return spans;
    }
    zones.sort();
    let starts: Vec<usize> = zones.iter().map(|z| z.0).collect();
    // Fin la plus lointaine parmi les zones 0..i, et sa règle / furthest end among zones 0..i, and its rule.
    let mut reach: Vec<(usize, Arc<str>)> = Vec::with_capacity(zones.len());
    for (_, end, source) in zones {
        let next = match reach.last() {
            Some((furthest, owner)) if end <= *furthest => (*furthest, owner.clone()),
            _ => (end, source),
        };
        reach.push(next);
    }
    spans
        .into_iter()
        .filter(|s| *s.entity != *rules.entity)
        .map(|mut span| {
            let protected = span.priority >= rules.priority_validated && rules.unmaskable.contains(&*span.entity);
            let zone = starts.partition_point(|&s| s <= span.start).checked_sub(1).and_then(|i| reach.get(i));
            if let Some((furthest, owner)) = zone {
                if !protected && *furthest >= span.end {
                    span.personal = false;
                    span.source = format!("keep:{owner}").into();
                }
            }
            span
        })
        .collect()
}

/// Boucle de `engine._finalize` : score minimal, liste d'autorisation, civilité, valeur des composites.
/// `engine._finalize` loop: minimum score, allow list, honorific trim, composite values.
pub fn filter(policy: &Policy, chars: &Chars, text: &IndexedText, spans: Vec<Span>) -> Vec<Span> {
    let mut kept = Vec::with_capacity(spans.len());
    for mut span in spans {
        if span.score < policy.min_score || span.end <= span.start {
            continue;
        }
        if !policy.allow.is_empty() && policy.allow.contains(chars.strip(&chars.fold(text.slice(span.start, span.end))))
        {
            continue;
        }
        if &*span.entity == "PERSON" {
            trim_honorific(chars, text, &mut span);
            if span.end <= span.start {
                continue;
            }
        }
        if span.value.is_none() && policy.mergeable(&span.entity) {
            span.value = Some(text.slice(span.start, span.end).to_owned());
        }
        kept.push(span);
    }
    kept
}

/// `_trim_honorific` : « M. », « Mme »… restent hors de la zone / honorifics stay outside the span.
fn trim_honorific(chars: &Chars, text: &IndexedText, span: &mut Span) {
    loop {
        let segment = text.slice(span.start, span.end);
        let mut token_chars = 0;
        let mut token_bytes = 0;
        for c in segment.chars() {
            if !chars.is(c, ALPHA) {
                break;
            }
            token_chars += 1;
            token_bytes += c.len_utf8();
        }
        if token_chars == 0 || !chars.is_honorific(segment.get(..token_bytes).unwrap_or("")) {
            return;
        }
        let separators =
            segment.get(token_bytes..).unwrap_or("").chars().take_while(|c| matches!(c, '.' | ' ' | '\u{a0}'));
        let rest = token_chars + separators.count();
        if rest >= span.len() {
            return;
        }
        span.start += rest;
    }
}

/// `merge_same_entity` : fusionne les chevauchements d'un même type composite (personne, adresse…).
/// Merges overlaps of one composite type (person, address…).
pub fn merge_same_entity(policy: &Policy, spans: Vec<Span>) -> Vec<Span> {
    let mut merged = Vec::with_capacity(spans.len());
    // Groupes dans l'ordre de première apparition (dict Python) / groups in first-seen order (Python dict).
    let mut groups: Vec<Vec<Span>> = Vec::new();
    let mut entities: Vec<Arc<str>> = Vec::new();
    for span in spans {
        if !policy.mergeable(&span.entity) {
            merged.push(span);
        } else if let Some(i) = entities.iter().position(|e| *e == span.entity) {
            if let Some(group) = groups.get_mut(i) {
                group.push(span);
            }
        } else {
            entities.push(span.entity.clone());
            groups.push(vec![span]);
        }
    }
    for mut group in groups {
        group.sort_by(|a, b| (a.start, b.end, b.priority, &a.source).cmp(&(b.start, a.end, a.priority, &b.source)));
        let mut members = group.into_iter();
        let Some(mut current) = members.next() else {
            continue;
        };
        for span in members {
            if span.start >= current.end {
                merged.push(std::mem::replace(&mut current, span));
            } else if span.end > current.end || span.priority > current.priority {
                // `dataclasses.replace` : un objet neuf / a new object.
                let source = if current.source == span.source {
                    current.source.clone()
                } else {
                    format!("{}+{}", current.source, span.source).into()
                };
                let mut forms = std::mem::take(&mut current.forms);
                forms.extend(span.forms);
                current = Span {
                    end: current.end.max(span.end),
                    priority: current.priority.max(span.priority),
                    score: py_max(current.score, span.score),
                    forms,
                    propagate: current.propagate || span.propagate,
                    value: None,
                    source,
                    origin: None,
                    ..current
                };
            } else {
                current.propagate = current.propagate || span.propagate;
            }
        }
        merged.push(current);
    }
    merged
}

/// `resolve` : priorité, puis longueur, puis score ; les zones composites perdantes sont rognées, pas perdues.
/// Priority, then length, then score; losing composite spans are trimmed, not dropped.
pub fn resolve(policy: &Policy, chars: &Chars, text: &IndexedText, mut spans: Vec<Span>) -> Vec<Span> {
    // Ordre total (source en dernier), tri stable comme `sorted` / total order (source last), stable sort.
    spans.sort_by(|a, b| {
        b.priority
            .cmp(&a.priority)
            .then(b.len().cmp(&a.len()))
            .then(b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal))
            .then(a.start.cmp(&b.start))
            .then(a.source.cmp(&b.source))
    });
    // Zones acceptées, disjointes, rangées par début (débuts uniques) : début -> (fin, indice dans `kept`). L'arbre
    // ne range que des couples, pas des zones entières ; insertion en O(log n), même sur un texte de 10 Mo.
    // Accepted spans, disjoint, by start: start -> (end, index into `kept`). The tree holds pairs, not whole
    // spans; O(log n) insertion, even on a 10 MB text.
    let mut accepted: BTreeMap<usize, (usize, usize)> = BTreeMap::new();
    let mut kept: Vec<Option<Span>> = Vec::with_capacity(spans.len());
    let mut pieces: Vec<(usize, usize)> = Vec::new();
    for span in spans {
        // Dernière zone acceptée commençant avant la fin : seule candidate au chevauchement le plus à droite.
        // Last accepted span starting before the end: the only candidate for the rightmost overlap.
        if accepted.range(..span.end).next_back().is_none_or(|(_, &(end, _))| end <= span.start) {
            accepted.insert(span.start, (span.end, kept.len()));
            kept.push(Some(span));
            continue;
        }
        if !policy.mergeable(&span.entity) {
            continue;
        }
        // Chevauchements, de gauche à droite : les zones acceptées qui finissent après le début.
        // Overlaps, left to right: the accepted spans ending after the start.
        let first = accepted.range(..span.end).rev().take_while(|(_, &(end, _))| end > span.start).last();
        let Some((&first, _)) = first else {
            continue;
        };
        let mut cursor = span.start;
        pieces.clear();
        for (&start, &(end, _)) in accepted.range(first..span.end) {
            if start > cursor {
                pieces.push((cursor, start));
            }
            cursor = cursor.max(end);
        }
        if cursor < span.end {
            pieces.push((cursor, span.end));
        }
        for &(start, end) in &pieces {
            let (start, end) = trim(chars, text, start, end);
            if end - start >= 3 {
                accepted.insert(start, (end, kept.len()));
                kept.push(Some(Span { start, end, value: None, origin: None, ..span.clone() }));
            }
        }
    }
    accepted.values().filter_map(|&(_, index)| kept.get_mut(index)?.take()).collect()
}

/// `_trim` : ni ponctuation ni espace aux bords d'un morceau / no punctuation or space at a piece's edges.
fn trim(chars: &Chars, text: &IndexedText, mut start: usize, mut end: usize) -> (usize, usize) {
    let alnum = |index: usize| text.char_at(index).is_some_and(|c| chars.is(c, ALNUM));
    while start < end && !alnum(start) {
        start += 1;
    }
    while end > start && !alnum(end - 1) {
        end -= 1;
    }
    (start, end)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::finalize::chars::test_rules;
    use crate::finalize::span::span;

    fn policy() -> Policy {
        Policy {
            min_score: 0.5,
            allow: HashSet::new(),
            mergeable: ["PERSON", "ORG", "ADDRESS", "LOCATION"].map(Box::from).to_vec(),
        }
    }

    #[test]
    fn validated_wins_and_composites_are_trimmed() {
        let rules = test_rules();
        let chars = Chars::new(&rules);
        let text = IndexedText::new("Jean Dupont 06 12 34 56 78").expect("small");
        let spans = vec![span(0, 26, "PERSON", 60), span(12, 26, "PHONE", 100)];
        let resolved = resolve(&policy(), &chars, &text, spans);
        let found: Vec<(&str, &str)> = resolved.iter().map(|s| (&*s.entity, text.slice(s.start, s.end))).collect();
        assert_eq!(found, [("PERSON", "Jean Dupont"), ("PHONE", "06 12 34 56 78")]);
    }

    #[test]
    fn honorific_is_left_outside() {
        let rules = test_rules();
        let chars = Chars::new(&rules);
        let text = IndexedText::new("Mme Dupont").expect("small");
        let kept = filter(&policy(), &chars, &text, vec![span(0, 10, "PERSON", 60)]);
        assert_eq!((kept[0].start, kept[0].value.as_deref()), (4, Some("Dupont")));
    }

    #[test]
    fn same_entity_overlaps_merge() {
        let mut first = span(0, 6, "PERSON", 60);
        first.forms = vec!["a".into()];
        let mut second = span(4, 10, "PERSON", 60);
        second.source = "other".into();
        second.forms = vec!["b".into()];
        let merged = merge_same_entity(&policy(), vec![first, second]);
        assert_eq!(merged.len(), 1);
        assert_eq!((merged[0].end, &*merged[0].source, merged[0].forms.len()), (10, "test+other", 2));
    }

    #[test]
    fn keep_zone_unmasks_contained_detections() {
        let rules = KeepRules { entity: "_KEEP".into(), unmaskable: HashSet::new(), priority_validated: 100 };
        let mut zone = span(0, 10, "_KEEP", 95);
        zone.source = "CUSTOM_1_REF".into();
        let kept = apply_keep(&rules, vec![zone, span(2, 5, "PHONE", 95), span(8, 12, "PHONE", 95)]);
        assert_eq!(kept.len(), 2);
        assert!(!kept[0].personal && &*kept[0].source == "keep:CUSTOM_1_REF");
        assert!(kept[1].personal);
    }
}
