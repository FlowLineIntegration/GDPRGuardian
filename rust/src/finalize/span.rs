//! Zone détectée, comme `types.Span` (Python) / detected span, as `types.Span` (Python).

use std::sync::Arc;

#[derive(Clone, Debug, PartialEq)]
pub struct Span {
    /// Positions en caractères Python / Python character offsets.
    pub start: usize,
    pub end: usize,
    pub entity: Arc<str>,
    pub label: Arc<str>,
    pub source: Arc<str>,
    pub score: f64,
    pub priority: i64,
    pub value: Option<String>,
    pub personal: bool,
    pub forms: Vec<Arc<str>>,
    pub propagate: bool,
    /// Raison propre à la règle (`types.Span.reason`, `explain`), jamais la valeur / the rule's own reason.
    pub reason: Option<Arc<str>>,
    /// Objet Python dont cette zone est l'état (modifié sur place, comme en Python), ou `None` pour un objet
    /// neuf (`dataclasses.replace`, propagation). Python object this span is the state of (mutated in place,
    /// as in Python), or `None` for a new object (`dataclasses.replace`, propagation).
    pub origin: Option<usize>,
}

impl Span {
    pub fn len(&self) -> usize {
        self.end.saturating_sub(self.start)
    }
}

/// `max(a, b)` de Python : le premier l'emporte à égalité (0.0 contre -0.0) / Python's max: first wins on ties.
pub fn py_max(a: f64, b: f64) -> f64 {
    if b > a {
        b
    } else {
        a
    }
}

#[cfg(test)]
pub fn span(start: usize, end: usize, entity: &str, priority: i64) -> Span {
    Span {
        start,
        end,
        entity: entity.into(),
        label: entity.into(),
        source: "test".into(),
        score: 0.9,
        priority,
        value: None,
        personal: true,
        forms: Vec::new(),
        propagate: false,
        reason: None,
        origin: None,
    }
}
