//! Moteur fusionné : un document traverse détection, résolution, propagation et rendu sans quitter Rust.
//!
//! Fused engine: a document goes through detection, resolution, propagation and rendering without leaving Rust.
//! Composé une fois par `Anonymizer` des composants Rust existants (préparation, langue, mots-clés, analyseur de
//! motifs, détecteur de noms, jumeaux des détecteurs, finaliseur), il garde les zones en structures Rust d'un
//! bout à l'autre. Python n'intervient que pour :
//! - le code sans jumeau Rust (téléphones validés par phonenumbers, NER, détecteurs et règles d'une
//!   organisation, recognizers des packs sans validateur natif), dont les zones entrent telles quelles ;
//! - les quelques fonctions gardées en Python par fidélité à l'interpréteur (`email`, `str.title`, libellés) ;
//! - les objets `Span` de l'API publique (`analyze`), créés à la demande.
//!
//! Composed once per `Anonymizer` from the existing Rust components, it keeps spans as Rust structures end to
//! end. Python only runs code without a Rust twin, the few functions kept in Python for interpreter fidelity,
//! and the public API's `Span` objects, built on demand. Le moteur Python reste la référence : résultats
//! identiques, prouvés par `tests/test_engine_fused.py`. The Python engine stays the reference: identical
//! results, proven by the differential tests.
//!
//! - `plan` : plan fixé à la construction / plan fixed at construction ;
//! - `document` : état d'un appel, vue des détecteurs Python, finalisation / one call's state and finalisation ;
//! - `passes` : passages de détection (`_detect_all`, `_detect`) / detection passes ;
//! - `organizations`, `tables`, `phone`, `sanitize` : ports exacts de petites parties Python / exact ports of
//!   small Python parts ;
//! - `python` : classe `Engine` / the `Engine` class.

mod document;
mod organizations;
mod passes;
mod phone;
mod plan;
mod python;
mod sanitize;
mod tables;

pub use python::register;
