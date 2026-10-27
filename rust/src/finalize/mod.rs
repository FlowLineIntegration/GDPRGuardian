//! Finalisation native : résolution, propagation, rendu et portée irréversible.
//!
//! Native finalisation: resolution, propagation, rendering and the irreversible scope. Port exact de
//! `Anonymizer._finalize`, `_propagate`, `_render` et de `scope.Scope` (Python), qui restent la référence :
//! les tests différentiels exigent des zones, des textes et des rapports identiques. Exact port of the
//! Python code, which stays the reference: differential tests require identical spans, texts and reports.
//!
//! Python fournit toutes les données (sémantique Unicode de `str`, table de repli, civilités, libellés) ;
//! Rust ne relit aucun fichier. Aucun état tiré d'un document ne survit à un appel, et la clé de la portée
//! n'existe que dans Rust, effacée à la fermeture. Python provides all the data; Rust reads no file. No
//! document-derived state outlives a call, and the scope key only exists in Rust, wiped on close.

mod chars;
mod fused;
mod indexed;
mod pipeline;
mod propagate;
mod python;
mod render;
mod resolve;
mod scope;
mod selfcheck;
mod span;
mod values;

pub use python::register;

// Moteur fusionné (`crate::engine`) : sémantique des caractères et finalisation sans objets Python par zone.
// Fused engine: character semantics and finalisation without one Python object per span.
pub(crate) use fused::{read_object, span_objects, tally_objects, Cells, Detected, PyFinalSpans, Text};
pub(crate) use indexed::IndexedText;
pub(crate) use python::{PyFinalizer, PyScope};
pub(crate) use span::Span;

/// Entrée hors du domaine natif : le moteur Python, référence, la traite / outside the native domain.
#[derive(Debug, PartialEq, Eq)]
pub struct Unsupported;
