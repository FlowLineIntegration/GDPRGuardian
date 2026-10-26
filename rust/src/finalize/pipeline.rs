//! Enchaînement après la détection : filtrage, fusion, résolution, propagation, positions d'origine.
//!
//! Post-detection pipeline: filtering, merging, resolution, propagation, original offsets
//! (`Anonymizer._finalize`, `analyze`, `analyze_segments`).

use super::chars::Chars;
use super::indexed::IndexedText;
use super::propagate::{propagate, Segments};
use super::render::RenderRules;
use super::resolve::{apply_keep, filter, merge_same_entity, resolve, KeepRules, Policy};
use super::span::Span;
use super::Unsupported;

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
        for span in &mut spans {
            if span.value.is_none() {
                span.value = Some(text.slice(span.start, span.end).to_owned());
            }
        }
        Ok(spans)
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
