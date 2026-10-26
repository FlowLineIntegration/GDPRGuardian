//! Enchaînement après la détection : filtrage, fusion, résolution, propagation, positions d'origine.
//!
//! Post-detection pipeline: filtering, merging, resolution, propagation, original offsets
//! (`Anonymizer._finalize`, `analyze`, `analyze_segments`).

use super::chars::{Chars, ALNUM, ALPHA, UPPER};
use super::indexed::IndexedText;
use super::propagate::{propagate, Segments};
use super::render::RenderRules;
use super::resolve::{apply_keep, filter, merge_same_entity, resolve, KeepRules, Policy};
use super::span::Span;
use super::Unsupported;
use crate::unicode::LOWER;

/// Réglages d'un `Anonymizer`, fixés à la construction / an `Anonymizer`'s settings, fixed at construction.
pub struct Finalizer {
    pub policy: Policy,
    /// Présent si l'anonymiseur a des règles personnalisées / present when the anonymizer has custom rules.
    pub keep: Option<KeepRules>,
    /// `types.PRIORITY_PROPAGATED`.
    pub priority_propagated: i64,
    /// `None` : un opérateur n'est pas reproductible en natif, le rendu reste en Python.
    /// `None`: an operator cannot be reproduced natively, rendering stays in Python.
    pub render: Option<RenderRules>,
}

impl Finalizer {
    /// `Anonymizer._finalize` : zones finales, disjointes, triées par début / final spans, disjoint, by start.
    pub fn finalize(
        &self,
        chars: &Chars,
        text: &IndexedText,
        spans: Vec<Span>,
        segments: Option<&Segments>,
    ) -> Result<Vec<Span>, Unsupported> {
        let spans = match &self.keep {
            Some(keep) => apply_keep(keep, spans),
            None => spans,
        };
        let kept = filter(&self.policy, chars, text, spans);
        if kept.is_empty() {
            return Ok(kept);
        }
        let resolved = resolve(&self.policy, chars, text, merge_same_entity(&self.policy, kept));
        let mut spans = propagate(chars, text, resolved, segments, self.priority_propagated)?;
        spans.sort_by_key(|s| s.start);
        drop_company_names(chars, text, &mut spans);
        extend_after_civility(chars, text, &mut spans);
        civility_surnames(chars, text, &mut spans);
        for span in &mut spans {
            if span.value.is_none() {
                span.value = Some(text.slice(span.start, span.end).to_owned());
            }
        }
        Ok(spans)
    }
}

/// `engine.COMPANY_FORMS` : formes juridiques de personne morale, même liste / legal-entity forms, same list.
const COMPANY_FORMS: &[&str] = &[
    "SAS", "SASU", "SARL", "SARLU", "EURL", "SCI", "SNC", "SCP", "SCM", "SELARL", "SELAS", "SELAFA", "GAEC", "EARL",
    "SCEA", "GIE", "SCOP", "SEM", "SPL", "SCA", "S.A.R.L.", "S.A.S.", "S.A.S.U.", "E.U.R.L.", "S.C.I.", "S.N.C.",
    "S.C.P.", "G.I.E.",
];
/// `engine.COMPANY_SUFFIX_FORMS`, en plus de `COMPANY_FORMS` / in addition to `COMPANY_FORMS`.
const COMPANY_SUFFIX_ONLY: &[&str] = &["SA", "S.A."];
/// `engine.PARTNERSHIP_FORMS` : sociétés civiles professionnelles et d'exercice libéral, même liste / same list.
const PARTNERSHIP_FORMS: &[&str] = &["SCP", "SELARL", "SELAS", "SELAFA", "SELURL", "SELCA", "SCM", "S.C.P."];
/// `engine._FIRM_LINK_RE` : séparateurs entre deux associés d'une firme / separators between two partners.
const FIRM_LINKS: &[&str] = &[",", "&", "et", "-", "–"];
/// `engine._FIRM_BLANKS` : un associé enchaîné est un nom seul d'un mot / a chained partner is a one-word surname.
const FIRM_BLANKS: [char; 6] = [' ', '\t', '\n', '\r', '\u{a0}', '\u{202f}'];

/// `engine._drop_company_names` : personnes qui portent une forme juridique de société, et associés suivants d'une
/// société civile professionnelle ou d'exercice libéral (`spans` triées, disjointes). Persons carrying a company
/// legal form, and the next partners of a professional partnership (`spans` sorted, disjoint).
fn drop_company_names(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    let mut firm_end: Option<usize> = None;
    spans.retain(|span| {
        if &*span.entity == "PERSON" {
            if firm_end.is_some_and(|end| end <= span.start && firm_link(text.slice(end, span.start)))
                && !text.slice(span.start, span.end).contains(FIRM_BLANKS)
            {
                firm_end = Some(span.end);
                return false;
            }
            if company_named(chars, text, span.start, span.end) {
                firm_end = form_right_before(chars, text, span.start, PARTNERSHIP_FORMS).then_some(span.end);
                return false;
            }
        }
        firm_end = None;
        true
    });
}

/// `_FIRM_LINK_RE.fullmatch` : `[ \t]{0,2}(?:,|&|et|-|–)[ \t]{1,2}`.
fn firm_link(gap: &str) -> bool {
    let rest = gap.trim_start_matches([' ', '\t']);
    if gap.len() - rest.len() > 2 {
        return false;
    }
    FIRM_LINKS
        .iter()
        .filter_map(|sep| rest.strip_prefix(sep))
        .any(|tail| (1..=2).contains(&tail.len()) && tail.chars().all(|c| c == ' ' || c == '\t'))
}

/// `(?<![\w.])(?:forms)[ \t]{1,2}\Z` juste avant `start` / a form and 1 or 2 blanks right before `start`.
fn form_right_before(chars: &Chars, text: &IndexedText, start: usize, forms: &[&str]) -> bool {
    let word = |c: char| chars.is(c, ALNUM) || c == '_';
    let head = text.slice(0, start);
    let blanks = head.chars().rev().take_while(|&c| c == ' ' || c == '\t').count();
    if !(1..=2).contains(&blanks) {
        return false;
    }
    let before = &head[..head.len() - blanks];
    forms.iter().any(|form| {
        before.strip_suffix(form).is_some_and(|rest| !rest.chars().next_back().is_some_and(|c| word(c) || c == '.'))
    })
}

/// `engine._company_named` : « SARL DUPONT », « DUPONT SARL » (1 ou 2 blancs) / a company legal form next to it.
fn company_named(chars: &Chars, text: &IndexedText, start: usize, end: usize) -> bool {
    let word = |c: char| chars.is(c, ALNUM) || c == '_';
    let blank = |c: char| c == ' ' || c == '\t';
    if titled_before(chars, text, start) {
        return false; // « M. Jean Dupont SARL » : une personne / a person
    }
    if form_right_before(chars, text, start, COMPANY_FORMS) {
        return true;
    }
    let rest = text.tail(end);
    let blanks = rest.chars().take_while(|&c| blank(c)).count();
    if !(1..=2).contains(&blanks) {
        return false;
    }
    // Forme suivie d'un mot capitalisé (« Dupont SARL Lumière ») : elle appartient à ce nom-là / it belongs to
    // that next name.
    COMPANY_FORMS.iter().chain(COMPANY_SUFFIX_ONLY).any(|form| {
        rest[blanks..].strip_prefix(form).is_some_and(|after| {
            if after.chars().next().is_some_and(word) {
                return false;
            }
            let gap = after.chars().take_while(|&c| blank(c)).count();
            !(gap > 0 && after[gap..].chars().next().is_some_and(|c| chars.is(c, ALPHA) && chars.is(c, UPPER)))
        })
    })
}

/// `engine._CIVILITY_BEFORE_RE` : civilités, même liste / civilities, same list.
const CIVILITIES: &[&str] = &["M.", "Mme", "Mlle", "Monsieur", "Madame", "Mademoiselle"];
/// `engine._TITLE_BEFORE_RE` : civilités et titres / civilities and titles.
const TITLES: &[&str] = &["M.", "Mme", "Mlle", "Monsieur", "Madame", "Mademoiselle", "Me", "Maître", "Dr"];

/// Une civilité et un seul blanc juste avant `start` / a civility and one blank right before `start`.
fn civility_before(chars: &Chars, text: &IndexedText, start: usize) -> bool {
    title_in(chars, text, start, CIVILITIES)
}

/// `engine._TITLE_BEFORE_RE` : une civilité ou un titre et un seul blanc juste avant `start`.
fn titled_before(chars: &Chars, text: &IndexedText, start: usize) -> bool {
    title_in(chars, text, start, TITLES)
}

fn title_in(chars: &Chars, text: &IndexedText, start: usize, forms: &[&str]) -> bool {
    let head = text.slice(0, start);
    let Some(rest) = head.strip_suffix(' ').or_else(|| head.strip_suffix('\t')) else {
        return false;
    };
    forms.iter().any(|form| {
        rest.strip_suffix(form).is_some_and(|before| {
            !before.chars().next_back().is_some_and(|c| chars.is(c, ALNUM) || c == '_' || c == '.')
        })
    })
}

/// `engine._surname_end` : fin du mot capitalisé qui commence en `pos` / end of the capitalised word at `pos`.
fn surname_end(chars: &Chars, text: &IndexedText, pos: usize) -> Option<usize> {
    let first = text.char_at(pos)?;
    if !(chars.is(first, ALPHA) && chars.is(first, UPPER)) {
        return None;
    }
    let (mut i, mut prev) = (pos + 1, first);
    while let Some(c) = text.char_at(i).filter(|&c| chars.is(c, ALPHA) || c == '\'' || c == '-') {
        if chars.is(c, ALPHA) && !chars.is(c, LOWER) && prev != '\'' && prev != '-' {
            return None;
        }
        prev = c;
        i += 1;
    }
    if prev == '\'' || prev == '-' || i - pos < 2 || text.char_at(i).is_some_and(|c| chars.is(c, ALNUM)) {
        return None;
    }
    Some(i)
}

/// `engine._extend_after_civility` : « M. [Matthieu] Orphelin » -> « M. [Matthieu Orphelin] » (`spans` triées,
/// disjointes / sorted, disjoint).
fn extend_after_civility(chars: &Chars, text: &IndexedText, spans: &mut [Span]) {
    for k in 0..spans.len() {
        let span = &spans[k];
        if &*span.entity != "PERSON" || !span.personal || text.char_at(span.end) != Some(' ') {
            continue;
        }
        if !civility_before(chars, text, span.start) {
            continue;
        }
        let Some(end) = surname_end(chars, text, span.end + 1) else {
            continue;
        };
        if spans.get(k + 1).is_some_and(|next| next.start < end) {
            continue;
        }
        spans[k].end = end;
    }
}

/// `engine.CIVILITY_WORDS`, `engine.NOT_SURNAMES` : mêmes listes / same lists.
const CIVILITY_WORDS: &[&str] =
    &["M.", "Mme", "Mlle", "Monsieur", "Madame", "Mademoiselle", "monsieur", "madame", "mademoiselle"];
const NOT_SURNAMES: &[&str] = &[
    "Le",
    "La",
    "Les",
    "L",
    "De",
    "Du",
    "Des",
    "Président",
    "Présidente",
    "Ministre",
    "Député",
    "Députée",
    "Sénateur",
    "Sénatrice",
    "Maire",
    "Rapporteur",
    "Rapporteure",
    "Secrétaire",
    "Directeur",
    "Directrice",
    "Juge",
    "Procureur",
    "Préfet",
    "Préfète",
    "Commissaire",
    "Professeur",
    "Docteur",
    "Maître",
    "Monsieur",
    "Madame",
    "Mademoiselle",
    "Et",
    "Ou",
];
/// `types.PRIORITY_HEURISTIC`.
const PRIORITY_HEURISTIC: i64 = 60;

/// `engine._civility_surnames` : « M. Orphelin » -> « M. [Orphelin] », civilité, un blanc puis un seul mot
/// capitalisé qui ne touche aucune zone, seulement si le détecteur de noms français a trouvé une personne
/// (`spans` triées, disjointes). A civility, one blank, then one capitalised word touching no span.
fn civility_surnames(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    if !spans.iter().any(|s| &*s.source == "FR_NAMES" || &*s.source == "propagated:FR_NAMES") {
        return;
    }
    let starts: Vec<usize> = spans.iter().map(|s| s.start).collect();
    let all = text.as_str();
    let mut added = Vec::new();
    let mut next_free = 0;
    for (index, (byte, c)) in all.char_indices().enumerate() {
        if index < next_free || (c != 'M' && c != 'm') {
            continue;
        }
        if index > 0 && text.char_at(index - 1).is_some_and(|p| chars.is(p, ALNUM) || p == '_' || p == '.') {
            continue;
        }
        let rest = &all[byte..];
        let Some(word) =
            CIVILITY_WORDS.iter().find(|w| rest.strip_prefix(**w).is_some_and(|after| after.starts_with([' ', '\t'])))
        else {
            continue;
        };
        let pos = index + word.chars().count() + 1;
        next_free = pos;
        let Some(end) = surname_end(chars, text, pos) else {
            continue;
        };
        let value = text.slice(pos, end);
        if NOT_SURNAMES.contains(&value) {
            continue;
        }
        let k = starts.partition_point(|&start| start < end);
        if k > 0 && spans[k - 1].end > index {
            continue;
        }
        added.push(Span {
            start: pos,
            end,
            entity: "PERSON".into(),
            label: "PERSON".into(),
            source: "FR_NAMES".into(),
            score: 0.8,
            priority: PRIORITY_HEURISTIC,
            value: Some(value.to_owned()),
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: None,
            origin: None,
        });
    }
    if !added.is_empty() {
        spans.extend(added);
        spans.sort_by_key(|s| s.start);
    }
}

/// Positions d'origine d'avant normalisation (`array('q')` de `_text.normalize`) / pre-normalisation offsets.
pub fn map_offsets(spans: &mut [Span], offsets: &[i64]) -> Result<(), Unsupported> {
    let at = |index: usize| offsets.get(index).and_then(|&o| usize::try_from(o).ok()).ok_or(Unsupported);
    for span in spans {
        let start = at(span.start)?;
        let end = at(span.end.checked_sub(1).ok_or(Unsupported)?)?.checked_add(1).ok_or(Unsupported)?;
        span.start = start;
        span.end = end;
    }
    Ok(())
}

/// `analyze_segments` : zones de chaque segment, en positions locales d'origine ; une zone à cheval sur deux
/// segments n'appartient à aucun et garde ses positions jointes. Per-segment spans in local original offsets;
/// a span straddling two segments belongs to none and keeps its joined offsets.
pub fn split_segments(
    spans: &mut [Span],
    segments: &Segments,
    offsets: &[Option<Vec<i64>>],
) -> Result<Vec<Vec<usize>>, Unsupported> {
    let mut members: Vec<Vec<usize>> = vec![Vec::new(); segments.len()];
    for (position, span) in spans.iter_mut().enumerate() {
        let (index, lo, hi) = segments.locate(span.start).ok_or(Unsupported)?;
        if span.end > hi {
            continue;
        }
        span.start -= lo;
        span.end -= lo;
        if let Some(offsets) = offsets.get(index).ok_or(Unsupported)? {
            map_offsets(std::slice::from_mut(span), offsets)?;
        }
        members.get_mut(index).ok_or(Unsupported)?.push(position);
    }
    Ok(members)
}
