//! Interface Python des détecteurs natifs / Python interface of the native detectors.
//!
//! Chaque classe est construite une fois (données de Python), puis chaque appel analyse un document sans GIL
//! et ne garde rien après ; les plans Unicode de ses textes sont chargés avant, GIL tenu, pour qu'une erreur de
//! Python remonte (`Unicode::without_gil`). Each class is built once from Python's data; each call scans one
//! document without the GIL and keeps nothing afterwards; its texts' Unicode planes are loaded first, GIL held,
//! so that a Python error propagates.

use std::collections::{HashMap, HashSet};
use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

use super::address::{AddressData, AddressDetector, AddressSpan};
use super::fr::{BirthDateDetector, BirthDates};
use super::intl::{self, EmailDetector, IbanCandidate, IbanDetector};
use super::organizations::{OrganizationData, OrganizationDetector};
use super::unicode::UnicodeTable;
/// Table Unicode unique du noyau (`gdprguardian._native.unicode_table`) / the core's single Unicode table.
pub use crate::unicode::PyUnicodeTables as PyUnicodeTable;

fn shared(table: &Bound<'_, PyUnicodeTable>) -> Arc<UnicodeTable> {
    table.get().shared()
}

/// Clés de communes (`Lexicon.communes`) numérotées, table dimensionnée d'emblée / numbered commune keys.
fn commune_numbers(communes: &Bound<'_, PyAny>) -> PyResult<HashMap<String, u32>> {
    let mut numbers = HashMap::with_capacity(communes.len()?);
    for key in communes.try_iter()? {
        let next = numbers.len() as u32;
        numbers.entry(key?.extract::<String>()?).or_insert(next);
    }
    Ok(numbers)
}

/// `{code: frozenset(clés)}` -> identifiants triés ; chaque clé est lue sans copie / sorted ids, keys read in place.
fn commune_ids(table: &Bound<'_, PyDict>, numbers: &HashMap<String, u32>) -> PyResult<HashMap<String, Box<[u32]>>> {
    let mut by_code = HashMap::with_capacity(table.len());
    for (code, keys) in table.iter() {
        let mut ids = Vec::with_capacity(keys.len()?);
        for key in keys.try_iter()? {
            let key = key?;
            let key = key.cast::<PyString>()?.to_str()?;
            let id =
                numbers.get(key).ok_or_else(|| PyValueError::new_err(format!("commune absente / missing: {key}")))?;
            ids.push(*id);
        }
        ids.sort_unstable();
        ids.dedup();
        by_code.insert(code.extract()?, ids.into_boxed_slice());
    }
    Ok(by_code)
}

/// Jumeau de `FrenchAddressDetector` / twin of `FrenchAddressDetector`.
#[pyclass(name = "AddressDetector", frozen)]
pub struct PyAddressDetector {
    inner: AddressDetector,
    unicode: Arc<UnicodeTable>,
}

#[pymethods]
impl PyAddressDetector {
    #[new]
    #[pyo3(signature = (table, *, street_types, abbreviations, strong_types, communes, postal, departments, saint,
                        name_particles, stop_lower, complement_hints, max_street_name, max_link, max_complement,
                        adjectives, not_place_leads, address_words, given_names, company_forms))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        table: &Bound<'_, PyUnicodeTable>,
        street_types: Vec<String>,
        abbreviations: HashSet<String>,
        strong_types: HashSet<String>,
        communes: &Bound<'_, PyAny>,
        postal: &Bound<'_, PyDict>,
        departments: &Bound<'_, PyDict>,
        saint: HashMap<String, String>,
        name_particles: HashSet<String>,
        stop_lower: HashSet<String>,
        complement_hints: Vec<String>,
        max_street_name: usize,
        max_link: usize,
        max_complement: usize,
        adjectives: HashSet<String>,
        not_place_leads: HashSet<String>,
        address_words: HashSet<String>,
        given_names: HashSet<String>,
        company_forms: HashSet<String>,
    ) -> PyResult<Self> {
        let communes = commune_numbers(communes)?;
        let postal = commune_ids(postal, &communes)?;
        let departments = commune_ids(departments, &communes)?;
        let data = AddressData {
            street_types,
            abbreviations,
            strong_types,
            communes,
            postal,
            departments,
            saint,
            name_particles,
            stop_lower,
            complement_hints,
            max_street_name,
            max_link,
            max_complement,
            adjectives,
            not_place_leads,
            address_words,
            given_names,
            company_forms,
        };
        let unicode = shared(table);
        let inner = AddressDetector::new(data, Arc::clone(&unicode)).map_err(PyValueError::new_err)?;
        Ok(Self { inner, unicode })
    }

    /// [(début, fin, score, raison propre ou None)] ; les préfiltres sont ceux du contexte Python / [(start, end,
    /// score, own reason or None)]; prefilters from the Python context.
    fn detect(
        &self,
        py: Python<'_>,
        text: &str,
        folded: &str,
        has_digit: bool,
        has_trigger: bool,
        has_box_hint: bool,
    ) -> PyResult<Vec<AddressSpan>> {
        self.unicode
            .without_gil(py, &[text, folded], || self.inner.detect(text, folded, has_digit, has_trigger, has_box_hint))?
            .map_err(PyValueError::new_err)
    }
}

/// Recherche des candidats de `OrganizationDetector` / candidate search of `OrganizationDetector`.
#[pyclass(name = "OrganizationDetector", frozen)]
pub struct PyOrganizationDetector {
    inner: OrganizationDetector,
    unicode: Arc<UnicodeTable>,
}

#[pymethods]
impl PyOrganizationDetector {
    #[new]
    #[pyo3(signature = (table, *, case_patterns, forms, sole_forms, prefix_forms, keywords, joiners, join_words,
                        family, legal_form_keys, stop, name_articles, function, particles))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        table: &Bound<'_, PyUnicodeTable>,
        case_patterns: Vec<String>,
        forms: usize,
        sole_forms: HashSet<String>,
        prefix_forms: HashSet<String>,
        keywords: Vec<String>,
        joiners: HashSet<String>,
        join_words: HashSet<String>,
        family: HashSet<String>,
        legal_form_keys: HashSet<String>,
        stop: HashSet<String>,
        name_articles: HashSet<String>,
        function: HashSet<String>,
        particles: HashSet<String>,
    ) -> PyResult<Self> {
        let data = OrganizationData {
            case_patterns,
            forms,
            sole_forms,
            prefix_forms,
            keywords,
            joiners,
            join_words,
            family,
            legal_form_keys,
            stop,
            name_articles,
            function,
            particles,
        };
        let unicode = shared(table);
        let inner = OrganizationDetector::new(data, Arc::clone(&unicode)).map_err(PyValueError::new_err)?;
        Ok(Self { inner, unicode })
    }

    /// [(début, fin, entrepreneur individuel)] / [(start, end, sole trader)].
    fn candidates(&self, py: Python<'_>, text: &str, folded: &str) -> PyResult<Vec<(usize, usize, bool)>> {
        self.unicode
            .without_gil(py, &[text, folded], || self.inner.candidates(text, folded))?
            .map_err(PyValueError::new_err)
    }
}

/// Jumeau de `EmailDetector` / twin of `EmailDetector`.
#[pyclass(name = "EmailDetector", frozen)]
pub struct PyEmailDetector {
    inner: EmailDetector,
    unicode: Arc<UnicodeTable>,
}

#[pymethods]
impl PyEmailDetector {
    #[new]
    fn new(table: &Bound<'_, PyUnicodeTable>) -> Self {
        let unicode = shared(table);
        Self { inner: EmailDetector::new(Arc::clone(&unicode)), unicode }
    }

    /// [(début, fin)] des candidats ; `email` (Python) valide / candidates, validated by Python's `email`.
    fn detect(&self, py: Python<'_>, text: &str) -> PyResult<Vec<(usize, usize)>> {
        self.unicode.without_gil(py, &[text], || self.inner.detect(text))
    }
}

/// Jumeau de `IbanDetector` (sans le contexte) / twin of `IbanDetector` (without the context).
#[pyclass(name = "IbanDetector", frozen)]
pub struct PyIbanDetector {
    inner: IbanDetector,
    unicode: Arc<UnicodeTable>,
}

#[pymethods]
impl PyIbanDetector {
    #[new]
    fn new(table: &Bound<'_, PyUnicodeTable>, lengths: HashMap<String, usize>) -> Self {
        let unicode = shared(table);
        Self { inner: IbanDetector::new(Arc::clone(&unicode), lengths), unicode }
    }

    /// [(début, fin, valeur ou None, mise en page par quatre)] / [(start, end, value or None, printed in fours)].
    fn detect(&self, py: Python<'_>, text: &str) -> PyResult<Vec<IbanCandidate>> {
        self.unicode.without_gil(py, &[text], || self.inner.detect(text))
    }
}

/// Bandes MRZ : [(début, fin, score)] / MRZ bands.
#[pyfunction]
fn mrz_bands(py: Python<'_>, text: &str) -> Vec<(usize, usize, f64)> {
    py.detach(|| intl::mrz(text))
}

/// Jumeau de `NirBirthDateDetector` / twin of `NirBirthDateDetector`.
#[pyclass(name = "BirthDateDetector", frozen)]
pub struct PyBirthDateDetector {
    inner: BirthDateDetector,
    unicode: Arc<UnicodeTable>,
}

#[pymethods]
impl PyBirthDateDetector {
    #[new]
    fn new(table: &Bound<'_, PyUnicodeTable>, months: Vec<(String, String)>) -> PyResult<Self> {
        let unicode = shared(table);
        let inner = BirthDateDetector::new(Arc::clone(&unicode), months).map_err(PyValueError::new_err)?;
        Ok(Self { inner, unicode })
    }

    /// ([(début, fin, valeur)], [(début, fin)]) : dates numériques, puis en lettres / numeric, then written.
    fn detect(
        &self,
        py: Python<'_>,
        text: &str,
        folded: &str,
        births: HashSet<(String, String)>,
    ) -> PyResult<BirthDates> {
        self.unicode.without_gil(py, &[text, folded], || self.inner.detect(text, folded, &births))
    }
}

// --- Moteur fusionné : appels directs, sans aller-retour par Python / fused engine: direct calls ----------------

impl PyUnicodeTable {
    /// `\w` de `re` / `re`'s `\w`.
    pub(crate) fn is_word(&self, c: char) -> bool {
        self.table().is_word(c)
    }

    /// `[^\W\d_]` de `re`.
    pub(crate) fn is_letter(&self, c: char) -> bool {
        self.table().is_letter(c)
    }

    /// `str.isspace()`, soit `\s` / i.e. `\s`.
    pub(crate) fn is_space(&self, c: char) -> bool {
        self.table().is_space(c)
    }
}

impl PyAddressDetector {
    /// `detect`, appelé par le moteur fusionné (GIL déjà libéré) / called by the fused engine (GIL released).
    pub(crate) fn spans(
        &self,
        text: &str,
        folded: &str,
        has_digit: bool,
        has_trigger: bool,
        has_box_hint: bool,
    ) -> Result<Vec<AddressSpan>, String> {
        self.inner.detect(text, folded, has_digit, has_trigger, has_box_hint)
    }
}

impl PyOrganizationDetector {
    pub(crate) fn candidate_spans(&self, text: &str, folded: &str) -> Result<Vec<(usize, usize, bool)>, String> {
        self.inner.candidates(text, folded)
    }
}

impl PyEmailDetector {
    pub(crate) fn candidate_spans(&self, text: &str) -> Vec<(usize, usize)> {
        self.inner.detect(text)
    }
}

impl PyIbanDetector {
    pub(crate) fn candidate_spans(&self, text: &str) -> Vec<(usize, usize, Option<String>, bool)> {
        self.inner.detect(text)
    }
}

/// Dates de naissance : (numériques avec valeur ISO, en lettres) / (numeric with ISO value, written).
pub(crate) type BirthDateSpans = (Vec<(usize, usize, String)>, Vec<(usize, usize)>);

impl PyBirthDateDetector {
    pub(crate) fn dates(&self, text: &str, folded: &str, births: &HashSet<(String, String)>) -> BirthDateSpans {
        self.inner.detect(text, folded, births)
    }
}

/// Bandes MRZ : [(début, fin, score)] / MRZ bands.
pub(crate) fn mrz_spans(text: &str) -> Vec<(usize, usize, f64)> {
    intl::mrz(text)
}

/// Enregistre les détecteurs dans `gdprguardian_core` / registers the detectors in `gdprguardian_core`.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyAddressDetector>()?;
    m.add_class::<PyOrganizationDetector>()?;
    m.add_class::<PyEmailDetector>()?;
    m.add_class::<PyIbanDetector>()?;
    m.add_class::<PyBirthDateDetector>()?;
    m.add_function(wrap_pyfunction!(mrz_bands, m)?)?;
    Ok(())
}
