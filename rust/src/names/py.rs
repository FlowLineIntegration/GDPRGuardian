//! Interface Python du détecteur de noms / Python interface of the name detector.
//!
//! Python fournit toutes les données une fois (lexique, listes, déclencheurs, tables Unicode, constantes) :
//! aucun fichier relu, aucune liste recopiée. Python provides all data once; nothing is re-read or copied.

use std::collections::HashMap;
use std::sync::Arc;

use aho_corasick::{AhoCorasick, AhoCorasickKind, MatchKind};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

use super::chars::Chars;
use super::cues::is_chez;
use super::lexicon::{ambiguity, given_rank, surname_rank};
use super::vocab::{flag, Vocab};
use super::{NameDetector, TextSets, Trigger, CONTRACT};
use crate::unicode::{PyUnicodeTables, Unicode};

/// Listes de mots attendues et leur drapeau / expected word lists and their flag.
const VOCABULARY: [(&str, u32); 24] = [
    ("stop", flag::STOP),
    ("particles", flag::PARTICLE),
    ("function", flag::FUNCTION),
    ("contextual", flag::CONTEXTUAL),
    ("org_context", flag::ORG_CONTEXT),
    ("org_family", flag::ORG_FAMILY),
    ("determiners", flag::DETERMINER),
    ("locatives", flag::LOCATIVE),
    ("strong_labels", flag::STRONG_LABEL),
    ("weak_labels", flag::WEAK_LABEL),
    ("given_headers", flag::GIVEN_HEADER),
    ("surname_headers", flag::SURNAME_HEADER),
    ("person_headers", flag::PERSON_HEADER),
    ("empty_cells", flag::EMPTY_CELL),
    ("case_sensitive_honorifics", flag::CASE_SENSITIVE_HONORIFIC),
    ("auxiliaries", flag::AUXILIARY),
    ("non_person_labels", flag::NON_PERSON_LABEL),
    ("org_leads", flag::ORG_LEAD),
    ("company_forms", flag::COMPANY_FORM),
    ("saint_words", flag::SAINT_WORD),
    ("surname_particles", flag::SURNAME_PARTICLE),
    ("postcodes", flag::POSTCODE),
    ("postcode_heads", flag::POSTCODE_HEAD),
    ("titles", flag::TITLE),
];

fn missing(name: &str) -> PyErr {
    PyValueError::new_err(format!("donnée manquante / missing data: {name}"))
}

fn item<'py>(dict: &Bound<'py, PyDict>, name: &str) -> PyResult<Bound<'py, PyAny>> {
    dict.get_item(name)?.ok_or_else(|| missing(name))
}

/// Chaque chaîne d'un itérable Python / every string of a Python iterable.
fn for_each_str(iterable: &Bound<'_, PyAny>, mut f: impl FnMut(&str)) -> PyResult<()> {
    for value in iterable.try_iter()? {
        f(value?.cast::<PyString>()?.to_str()?);
    }
    Ok(())
}

fn char_vecs(words: Vec<String>) -> Vec<Vec<char>> {
    words.iter().map(|w| w.chars().collect()).collect()
}

/// Détecteur de personnes natif, construit une fois par processus / native person detector, built once.
#[pyclass(name = "NameDetector", frozen)]
pub struct PyNameDetector {
    inner: NameDetector,
    /// Table partagée, pour charger les plans d'un texte avant de rendre le GIL / to load a text's planes first.
    unicode: Arc<Unicode>,
}

#[pymethods]
impl PyNameDetector {
    #[new]
    #[pyo3(signature = (*, unicode, names, words, communes, vocabulary, triggers, dotted_forms, text_sets, constants))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        unicode: &Bound<'_, PyUnicodeTables>,
        names: &Bound<'_, PyDict>,
        words: &Bound<'_, PyAny>,
        communes: &Bound<'_, PyAny>,
        vocabulary: &Bound<'_, PyDict>,
        triggers: Vec<(String, u32, bool, bool)>,
        dotted_forms: Vec<String>,
        text_sets: &Bound<'_, PyDict>,
        constants: HashMap<String, i64>,
    ) -> PyResult<Self> {
        // Contrat : mêmes seuils, même disposition des codes / same thresholds, same code layout.
        let drift: Vec<&str> = CONTRACT
            .iter()
            .filter(|(name, value)| constants.get(*name) != Some(value))
            .map(|(name, _)| *name)
            .collect();
        if !drift.is_empty() {
            return Err(PyValueError::new_err(format!(
                "constantes différentes de Python / constants differ from Python: {}",
                drift.join(", ")
            )));
        }
        // Table Unicode partagée du noyau / the core's shared Unicode table.
        let unicode = unicode.get().shared();
        let chars = Chars::new(Arc::clone(&unicode));

        // Une seule table : le lexique, puis chaque liste ajoute son drapeau / one table, one flag per list.
        let mut lists = vec![(words.clone(), flag::WORD), (communes.clone(), flag::COMMUNE)];
        for (name, list_flag) in VOCABULARY {
            lists.push((item(vocabulary, name)?, list_flag));
        }
        let mut capacity = names.len();
        for (list, _) in &lists {
            capacity += list.len()?;
        }
        let mut vocab = Vocab::with_capacity(capacity);
        let full = || PyValueError::new_err("clé démesurée ou liste modifiée / oversized key or list changed");
        for (key, code) in names.iter() {
            if !vocab.insert(key.cast::<PyString>()?.to_str()?, flag::NAME, Some(code.extract::<u16>()?)) {
                return Err(full());
            }
        }
        for (list, list_flag) in &lists {
            let mut inserted = true;
            for_each_str(list, |key| inserted &= vocab.insert(key, *list_flag, None))?;
            if !inserted {
                return Err(full());
            }
        }

        // Un motif vide trouverait des correspondances vides : refusé / an empty pattern would match nothing real.
        if triggers.iter().any(|t| t.0.is_empty()) || dotted_forms.iter().any(String::is_empty) {
            return Err(PyValueError::new_err("motif vide / empty pattern"));
        }
        let trigger_info = triggers
            .iter()
            .map(|(pattern, flags, check_left, check_right)| {
                let key: Vec<char> = pattern.chars().collect();
                Trigger {
                    flags: *flags,
                    check_left: *check_left,
                    check_right: *check_right,
                    case_sensitive: vocab.get(&key).has(flag::CASE_SENSITIVE_HONORIFIC),
                    chez: is_chez(&key),
                }
            })
            .collect();
        // Même sémantique qu'`ahocorasick_rs` en `LeftmostLongest`, sans chevauchement ; automate déterministe
        // (une transition par octet) : la recherche la plus rapide du crate. Same semantics as `ahocorasick_rs`;
        // a DFA (one transition per byte) is the crate's fastest search.
        let automaton = |patterns: Vec<&str>| {
            AhoCorasick::builder()
                .match_kind(MatchKind::LeftmostLongest)
                .kind(Some(AhoCorasickKind::DFA))
                .build(patterns)
                .map_err(|e| PyValueError::new_err(e.to_string()))
        };
        let text_sets = TextSets {
            saint_prefixes: char_vecs(item(text_sets, "saint_prefixes")?.extract()?),
            verb_tails: char_vecs(item(text_sets, "verb_tails")?.extract()?),
            skip_back: item(text_sets, "skip_back")?.extract::<String>()?.chars().collect(),
            sentence_end: item(text_sets, "sentence_end")?.extract::<String>()?.chars().collect(),
        };
        Ok(Self {
            inner: NameDetector {
                chars,
                vocab,
                triggers: automaton(triggers.iter().map(|t| t.0.as_str()).collect())?,
                trigger_info,
                dotted_forms: automaton(dotted_forms.iter().map(String::as_str).collect())?,
                text_sets,
            },
            unicode,
        })
    }

    /// Zones de personnes `[(début, fin, valeur, score, propagation, forme)]`, sans GIL ; `None` si le
    /// texte n'est pas encodable en UTF-8 (demi-paires isolées) ou dépasse 1 Go : le chemin Python prend alors
    /// le relais. Person spans, GIL released; `None` for text with lone surrogates or over 1 GB: the Python
    /// path takes over.
    #[pyo3(signature = (text, folded, person_rows=Vec::new()))]
    #[allow(clippy::type_complexity)]
    fn detect(
        &self,
        py: Python<'_>,
        text: &Bound<'_, PyString>,
        folded: &Bound<'_, PyString>,
        person_rows: Vec<(usize, usize)>,
    ) -> PyResult<Option<Vec<(usize, usize, String, f64, bool, Option<String>)>>> {
        let (Ok(text), Ok(folded)) = (text.to_str(), folded.to_str()) else {
            return Ok(None);
        };
        let found = self.unicode.without_gil(py, &[text, folded], || self.inner.detect(text, folded, &person_rows))?;
        Ok(found
            .map(|found| found.into_iter().map(|f| (f.start, f.end, f.value, f.score, f.propagate, f.form)).collect()))
    }
}

// --- Moteur fusionné : appels directs, sans aller-retour par Python / fused engine: direct calls ----------------

impl PyNameDetector {
    /// Détecteur Rust, appelé directement par le moteur fusionné / the Rust detector, called by the fused engine.
    pub(crate) fn detector(&self) -> &NameDetector {
        &self.inner
    }

    /// `Lexicon.code` d'un mot replié : (rang prénom, rang nom, ambiguïté), ou `None` s'il n'est pas un nom.
    /// `Lexicon.code` of a folded word: (given-name rank, surname rank, ambiguity), or `None` for a non-name.
    pub(crate) fn lexicon_ranks(&self, key: &[char]) -> Option<(u8, u8, u8)> {
        self.inner.code(key).map(|code| (given_rank(code), surname_rank(code), ambiguity(code)))
    }
}
