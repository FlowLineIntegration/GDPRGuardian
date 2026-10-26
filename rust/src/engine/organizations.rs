//! Décision des organisations : port exact de `OrganizationDetector._spans` et `_person_content` (Python).
//!
//! Organisation decision: exact port of the Python methods. Règle « physicomorale » : une raison sociale qui
//! n'est qu'un nom de personne devient une zone PERSONNE ; une raison sociale qui en contient un est masquée ;
//! les autres sont signalées mais conservées selon `company_ids`. "Physicomorale" rule: a company name that is
//! only a person name becomes a PERSON span; one that contains a person name is masked; the others are reported
//! but kept, depending on `company_ids`.

use std::collections::HashSet;

use crate::detectors::PyUnicodeTable;
use crate::finalize::{IndexedText, Span};
use crate::names::py::PyNameDetector;
use crate::prepare::Preparer;
use crate::scanner::Context;

use super::plan::Template;

/// Données de la décision, toutes venues de `organizations.py` et `_vocab` / decision data, all from Python.
pub(crate) struct Decision {
    /// `V.ORG_KEYWORDS`, `V.FUNCTION`, `V.PARTICLES`, `V.ORG_FAMILY` (mots repliés / folded words).
    pub keywords: HashSet<String>,
    pub function: HashSet<String>,
    pub particles: HashSet<String>,
    pub family: HashSet<String>,
    /// Groupes « entrepreneur individuel » du pack (`_ei_groups`) / the pack's sole-trader groups.
    pub ei_groups: Vec<u32>,
    /// `_SURNAME_MIN`, `_GIVEN_MIN`, `_FREQUENT_NAME`.
    pub surname_min: u8,
    pub given_min: u8,
    pub frequent: u8,
    /// `AMB_NONE`, `AMB_WORD`, `AMB_ENTITY` (`_lexicon`).
    pub amb_none: u8,
    pub amb_word: u8,
    pub amb_entity: u8,
    /// Zones produites : nom de personne, organisation masquée, organisation conservée / produced spans.
    pub person: Template,
    pub masked: Template,
    pub kept: Template,
}

/// Ce que la décision lit du document et des réglages / what the decision reads.
pub(crate) struct Facts<'a> {
    pub names: &'a PyNameDetector,
    pub table: &'a PyUnicodeTable,
    pub preparer: &'a Preparer,
    pub text: &'a IndexedText<'a>,
    pub context: &'a Context<'a>,
    /// `Settings.company_ids` et profil strict / company-id policy and strict profile.
    pub company_ids: &'a str,
    pub strict: bool,
}

impl Facts<'_> {
    /// `_text.fold`.
    fn fold(&self, word: &str) -> String {
        self.preparer.fold_parts(word).into_owned()
    }

    /// Fin du segment (cellule) de `pos`, `None` sans segments / end of `pos`'s segment, `None` without them.
    fn segment_end(&self, pos: usize) -> Option<usize> {
        let segments = self.context.segments?;
        let index = segments.partition_point(|s| s.0 <= pos).checked_sub(1)?;
        segments.get(index).map(|s| s.1)
    }
}

/// `_WORDS_RE.findall` : `[^\W\d_][\w'’.-]*`.
fn words<'t>(text: &'t str, table: &PyUnicodeTable) -> Vec<&'t str> {
    let mut found = Vec::new();
    let mut chars = text.char_indices().peekable();
    while let Some((start, c)) = chars.next() {
        if !table.is_letter(c) {
            continue;
        }
        let mut end = start + c.len_utf8();
        while let Some(&(at, c)) = chars.peek() {
            if !(table.is_word(c) || matches!(c, '\'' | '’' | '.' | '-')) {
                break;
            }
            end = at + c.len_utf8();
            chars.next();
        }
        found.push(text.get(start..end).unwrap_or(""));
    }
    found
}

impl Decision {
    /// `_spans` : une zone par organisation (la plus longue), puis la décision / one span each, then the decision.
    pub(crate) fn spans(&self, facts: &Facts<'_>, mut found: Vec<(usize, usize, bool)>) -> Vec<Span> {
        // Tri stable par (début, -fin), comme `sorted` / stable sort by (start, -end), like `sorted`.
        found.sort_by(|a, b| a.0.cmp(&b.0).then(b.1.cmp(&a.1)));
        let mut merged: Vec<(usize, usize, bool)> = Vec::with_capacity(found.len());
        for (start, end, sole) in found {
            match merged.last_mut() {
                Some(last) if start < last.1 => *last = (last.0, last.1.max(end), last.2 || sole),
                _ => merged.push((start, end, sole)),
            }
        }
        let mut spans = Vec::new();
        for (start, end, sole) in merged {
            if end <= start || facts.segment_end(start).is_some_and(|hi| end > hi) {
                continue;
            }
            let words = words(facts.text.slice(start, end), facts.table);
            let Some(first) = words.first().map(|w| facts.fold(w)) else {
                continue;
            };
            // « la Société », « le Groupe » : mot d'introduction seul / cue word alone.
            if words.len() == 1 && (self.keywords.contains(&first) || self.function.contains(&first)) {
                continue;
            }
            let (person, only_person, safe) = self.person_content(facts, &words, &first);
            if only_person {
                let mut span = self.person.span(start, end);
                span.propagate = safe;
                spans.push(span);
                continue;
            }
            let personal = person
                || sole
                || facts.company_ids == "mask"
                || (facts.company_ids == "auto"
                    && (facts.strict
                        || (!self.ei_groups.is_empty()
                            && facts.context.near_groups(&self.ei_groups, start, end, 200, 200))));
            spans.push(if personal { self.masked.span(start, end) } else { self.kept.span(start, end) });
        }
        spans
    }

    /// `_person_content` : (contient un nom de personne, n'est qu'un nom de personne, sans mot ambigu).
    /// (has a person name, is only a person name, has no ambiguous word).
    fn person_content(&self, facts: &Facts<'_>, words: &[&str], first: &str) -> (bool, bool, bool) {
        let keys: Vec<String> = words
            .iter()
            .map(|w| facts.fold(w))
            .filter(|k| !self.particles.contains(k) && !self.function.contains(k))
            .collect();
        // (rang prénom, rang nom, ambiguïté) ; « Fils », « Associés » ne sont jamais des noms ici.
        // (given rank, surname rank, ambiguity); family-business words are never names here.
        let codes: Vec<Option<(u8, u8, u8)>> = keys
            .iter()
            .map(|k| {
                if self.family.contains(k) {
                    return None;
                }
                facts.names.lexicon_ranks(&k.chars().collect::<Vec<char>>())
            })
            .collect();
        let any_flag = keys.iter().zip(&codes).any(|(key, code)| match code {
            // Nom sûr, ou nom très porté même s'il est aussi un mot / safe name, or a very frequent one.
            Some((given, surname, amb)) if key.chars().nth(2).is_some() => {
                (*amb == self.amb_none && (*surname >= self.surname_min || *given >= self.given_min))
                    || (*amb == self.amb_word && (*given).max(*surname) >= self.frequent)
            }
            _ => false,
        });
        let names: Vec<bool> = codes.iter().map(|c| c.is_some_and(|(_, _, amb)| amb != self.amb_entity)).collect();
        let has_pair =
            names.iter().filter(|&&n| n).count() >= 2 && codes.iter().any(|c| c.is_some_and(|(given, _, _)| given > 0));
        let person = any_flag || has_pair;
        // « SCI du Moulin » : une particule en tête désigne un lieu ou une enseigne / a leading particle: a place.
        let only = person && names.iter().all(|&n| n) && keys.len() <= 4 && !self.particles.contains(first);
        let safe = codes.iter().all(|c| c.is_some_and(|(_, _, amb)| amb == self.amb_none));
        (person, only, safe)
    }
}
