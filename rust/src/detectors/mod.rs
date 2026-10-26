//! Détecteurs natifs : jumeaux Rust des détecteurs Python (adresses, organisations, e-mails, IBAN, MRZ, dates de
//! naissance liées au NIR) / native twins of the Python detectors.
//!
//! Le code Python reste la référence : chaque jumeau en est la transcription, construite une fois avec les
//! données de Python (listes, lexique postal, classes Unicode de l'interpréteur), et rend exactement les mêmes
//! zones en positions de caractères Python. Code sûr, sans `unsafe` ; aucune donnée de document n'est gardée
//! entre deux appels.
//! The Python code stays the reference: each twin transcribes it, is built once from Python's data (lists,
//! postal lexicon, the interpreter's Unicode classes) and returns exactly the same spans, in Python character
//! offsets. Safe code, no `unsafe`; no document data is kept between calls.

use aho_corasick::{AhoCorasick, AhoCorasickKind, MatchKind};

mod address;
mod chars;
mod fr;
mod intl;
mod organizations;
mod python;
mod unicode;

pub use python::register;

/// Automate Aho-Corasick déterministe : la recherche la plus rapide, pour quelques centaines de Ko au plus. Même
/// sémantique que `ahocorasick_rs` côté Python (même bibliothèque). Deterministic Aho-Corasick automaton: the
/// fastest search, for a few hundred KB at most; same semantics as `ahocorasick_rs` (same library).
fn automaton(patterns: &[String], kind: MatchKind) -> Result<AhoCorasick, String> {
    AhoCorasick::builder().match_kind(kind).kind(Some(AhoCorasickKind::DFA)).build(patterns).map_err(|e| e.to_string())
}

// Jumeaux appelés directement par le moteur fusionné / twins called directly by the fused engine.
pub(crate) use python::{
    mrz_spans, PyAddressDetector, PyBirthDateDetector, PyEmailDetector, PyIbanDetector, PyOrganizationDetector,
    PyUnicodeTable,
};
