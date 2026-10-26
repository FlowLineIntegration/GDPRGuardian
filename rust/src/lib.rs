//! Noyau Rust de Gardien RGPD, exposé à Python par PyO3 / GDPR Guardian Rust core, exposed to Python via PyO3.
//!
//! Le moteur Python reste la référence ; ce module accélère le chemin critique (mots-clés, motifs,
//! clés de contrôle) et produit exactement les mêmes zones. The Python engine stays the reference;
//! this module accelerates the hot path and yields exactly the same spans.

mod detectors;
mod engine;
mod finalize;
mod keywords;
mod names;
mod pattern;
mod prepare;
mod scanner;
mod tabular;
mod text;
mod unicode;
mod validators;
mod windows;

use std::collections::HashMap;
use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use keywords::{Hits, KeywordIndex};
use scanner::{Boundary, Context, Group, Policy, Prefilter, Recognizer, Scanner, Settings, Tier, Zone};
use unicode::PyUnicodeTables;

/// Occurrences de mots-clés, même interface que `gdprguardian.keywords.KeywordHits`.
/// Keyword hits, same interface as `gdprguardian.keywords.KeywordHits`.
#[pyclass(name = "KeywordHits", frozen)]
struct PyHits {
    hits: Arc<Hits>,
    names: Arc<Vec<String>>,
    ids: Arc<HashMap<String, u32>>,
}

impl PyHits {
    /// (groupe, occurrences) des groupes présents, triés par nom comme en Python (même ordre des points de code).
    /// (group, count) of the groups present, sorted by name as in Python (same code-point order).
    fn present(&self) -> Vec<(&str, usize)> {
        let mut present: Vec<(&str, usize)> = self
            .names
            .iter()
            .enumerate()
            .map(|(gid, name)| (name.as_str(), self.hits.count(gid as u32)))
            .filter(|&(_, count)| count > 0)
            .collect();
        present.sort_unstable();
        present
    }
}

#[pymethods]
impl PyHits {
    #[pyo3(signature = (group, start, end, before, after, lo=0, hi=usize::MAX))]
    #[allow(clippy::too_many_arguments)]
    fn near(&self, group: &str, start: usize, end: usize, before: usize, after: usize, lo: usize, hi: usize) -> bool {
        self.ids.get(group).is_some_and(|&g| self.hits.near(g, start, end, before, after, lo, hi))
    }

    #[pyo3(signature = (group, pos, lo=0))]
    fn last_end(&self, group: &str, pos: usize, lo: usize) -> i64 {
        self.ids.get(group).and_then(|&g| self.hits.last_end(g, pos, lo)).map_or(-1, |end| end as i64)
    }

    #[getter]
    fn counts<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        for (name, count) in self.present() {
            dict.set_item(name, count)?;
        }
        Ok(dict)
    }

    fn groups(&self) -> Vec<&str> {
        self.present().into_iter().map(|(name, _)| name).collect()
    }

    fn occurrences(&self, group: &str) -> Vec<(u32, u32)> {
        match self.ids.get(group) {
            Some(&g) => self.hits.occurrences(g).collect(),
            None => Vec::new(),
        }
    }
}

/// Analyseur compilé une fois / scanner compiled once.
#[pyclass(name = "Scanner", frozen)]
struct PyScanner {
    inner: Scanner,
    names: Arc<Vec<String>>,
    ids: Arc<HashMap<String, u32>>,
    supported: Vec<bool>,
    errors: Vec<Option<String>>,
    /// Classes de caractères de Python / Python's character classes.
    tables: Py<PyUnicodeTables>,
}

/// Arbre de `re` du motif à compiler (`gdprguardian._native.syntax`), si le validateur est natif ou absent.
/// `re`'s tree of the pattern to compile, if the validator is native or absent.
fn source(spec: &Bound<'_, PyDict>, sets: &pattern::Sets) -> PyResult<scanner::Source> {
    let validator: Option<String> = spec.get_item("validator")?.map(|v| v.extract()).transpose()?.flatten();
    if validator.is_some_and(|name| validators::lookup(&name).is_none()) {
        return Ok(None);
    }
    Ok(Some(match spec.get_item("syntax")? {
        Some(syntax) if !syntax.is_none() => pattern::read(&syntax, sets)
            .unwrap_or_else(|_| Err("arbre de `re` illisible / unreadable `re` tree".into())),
        _ => Err("arbre de `re` absent / `re` tree missing".into()),
    }))
}

/// `compiled` : motif compilé par `scanner::compile_all` / pattern compiled by `scanner::compile_all`.
fn parse_recognizer(
    spec: &Bound<'_, PyDict>,
    keywords: &KeywordIndex,
    compiled: scanner::CompiledSlot,
) -> PyResult<Result<Recognizer, String>> {
    let get = |key: &str| spec.get_item(key);
    let validator_name: Option<String> = get("validator")?.map(|v| v.extract()).transpose()?.flatten();
    let validator = match &validator_name {
        Some(name) => match validators::lookup(name) {
            Some(f) => Some(f),
            None => return Ok(Err(format!("validateur non natif / non-native validator: {name}"))),
        },
        None => None,
    };
    let compiled = match compiled {
        Some(Ok(compiled)) => compiled,
        Some(Err(e)) => return Ok(Err(e)),
        None => return Ok(Err("motif non compilé / pattern not compiled".to_string())),
    };
    let group = match get("group")? {
        None => Group::Whole,
        Some(v) => {
            if let Ok(i) = v.extract::<usize>() {
                if i == 0 {
                    Group::Whole
                } else {
                    Group::Index(i)
                }
            } else {
                Group::Name(v.extract()?)
            }
        }
    };
    let tier = match get("tier")?.map(|v| v.extract::<String>()).transpose()?.as_deref() {
        Some("B") => Tier::B,
        Some("C") => Tier::C,
        Some("L") => Tier::L,
        _ => Tier::A,
    };
    let boundary = match get("boundary")?.map(|v| v.extract::<String>()).transpose()?.as_deref() {
        Some("word") => Boundary::Word,
        Some("ip") => Boundary::Ip,
        Some("hex") => Boundary::Hex,
        Some("phone") => Boundary::Phone,
        Some("digit") => Boundary::Digit,
        Some("group") => Boundary::Group,
        Some("none") => Boundary::None,
        _ => Boundary::Alnum,
    };
    let policy = match get("policy")?.map(|v| v.extract::<Option<String>>()).transpose()?.flatten().as_deref() {
        Some("company") => Policy::Company,
        Some("facility") => Policy::Facility,
        _ => Policy::None,
    };
    let prefilter = match get("prefilter")? {
        None => Prefilter::None,
        Some(v) if v.is_none() => Prefilter::None,
        Some(v) => {
            if let Ok(s) = v.extract::<String>() {
                if s == "digit" {
                    Prefilter::Digit
                } else {
                    Prefilter::Any(vec![s])
                }
            } else {
                Prefilter::Any(v.extract::<Vec<String>>()?)
            }
        }
    };
    let group_ids = |key: &str| -> PyResult<Vec<u32>> {
        let names: Vec<String> = get(key)?.map(|v| v.extract()).transpose()?.unwrap_or_default();
        Ok(names.iter().filter_map(|c| keywords.group_ids.get(c).copied()).collect())
    };
    Ok(Ok(Recognizer {
        shape: compiled.shape.clone(),
        pattern: compiled,
        group,
        validator,
        tier,
        contexts: group_ids("contexts")?,
        vetoes: group_ids("vetoes")?,
        before: get("before")?.map(|v| v.extract()).transpose()?.unwrap_or(48),
        after: get("after")?.map(|v| v.extract()).transpose()?.unwrap_or(16),
        boundary,
        prefilter,
        score: get("score")?.map(|v| v.extract()).transpose()?.unwrap_or(0.95),
        policy,
        fallback: get("fallback")?.map(|v| v.extract()).transpose()?.unwrap_or(false),
    }))
}

#[pymethods]
impl PyScanner {
    /// `tables` : table Unicode de Python (`gdprguardian._native.unicode_tables()`), source unique des classes.
    /// `tables`: Python's Unicode table, the single source of the character classes. `untrusted` : règles reçues
    /// d'une requête, compilées sous bornes (`pattern::Limits::untrusted`) / rules received with a request,
    /// compiled under bounds.
    #[new]
    #[pyo3(signature = (recognizers, keyword_groups, tables, *, untrusted=false))]
    fn new(
        py: Python<'_>,
        recognizers: &Bound<'_, PyList>,
        keyword_groups: Vec<(String, Vec<String>)>,
        tables: Py<PyUnicodeTables>,
        untrusted: bool,
    ) -> PyResult<Self> {
        let words: Vec<&str> = keyword_groups.iter().flat_map(|(_, words)| words.iter().map(String::as_str)).collect();
        let classes = tables.get().classes(py, &words)?;
        let keywords = KeywordIndex::new(&keyword_groups, classes).map_err(PyValueError::new_err)?;
        // `\w`, `\d`, `\s` et candidats de `re.IGNORECASE`, de la table de Python / from Python's table.
        let unicode = tables.get().shared();
        let perl = unicode.perl_sets(py)?;
        let sets = pattern::Sets::new(perl, unicode.ignorecase_candidates());
        let items: Vec<Bound<'_, PyAny>> = recognizers.iter().collect();
        let sources = items.iter().map(|item| source(item.cast::<PyDict>()?, &sets)).collect::<PyResult<Vec<_>>>()?;
        // Clé de partage des motifs des packs (`_spec`) / sharing key of pack patterns.
        let keys = items
            .iter()
            .map(|item| item.cast::<PyDict>()?.get_item("key")?.map(|v| v.extract::<Option<String>>()).transpose())
            .map(|key| key.map(Option::flatten))
            .collect::<PyResult<Vec<Option<String>>>>()?;
        // Compilation sans GIL : parallèle, ou bornée sur un fil / GIL released: parallel, or bounded on one thread.
        let limits = if untrusted { pattern::Limits::untrusted() } else { pattern::Limits::trusted() };
        let compiled = py.detach(|| scanner::compile_all(&sources, &keys, &perl.word, &limits));
        let mut parsed = Vec::with_capacity(recognizers.len());
        let mut supported = Vec::with_capacity(recognizers.len());
        let mut errors = Vec::with_capacity(recognizers.len());
        for (item, compiled) in items.iter().zip(compiled) {
            let spec = item.cast::<PyDict>()?;
            match parse_recognizer(spec, &keywords, compiled)? {
                Ok(rec) => {
                    parsed.push(Some(rec));
                    supported.push(true);
                    errors.push(None);
                }
                Err(message) => {
                    // Emplacement vide, traité côté Python / empty slot, Python handles it.
                    parsed.push(None);
                    supported.push(false);
                    errors.push(Some(message));
                }
            }
        }
        let names = Arc::new(keywords.group_names.clone());
        let ids = Arc::new(keywords.group_ids.clone());
        Ok(Self { inner: Scanner::new(parsed, keywords), names, ids, supported, errors, tables })
    }

    /// Recognizers pris en charge en natif / natively supported recognizers.
    #[getter]
    fn supported(&self) -> Vec<bool> {
        self.supported.clone()
    }

    #[getter]
    fn errors(&self) -> Vec<Option<String>> {
        self.errors.clone()
    }

    /// Mots-clés de contexte, sans GIL / context keywords, GIL released.
    fn keywords(&self, py: Python<'_>, folded: &str) -> PyResult<PyHits> {
        let classes = self.tables.get().classes(py, &[folded])?;
        let hits = py.detach(|| self.inner.keywords.scan(folded, classes));
        Ok(PyHits { hits: Arc::new(hits), names: self.names.clone(), ids: self.ids.clone() })
    }

    /// Analyse des motifs, sans GIL, avec des occurrences déjà calculées par `keywords()`.
    /// Pattern scan without the GIL, reusing hits from `keywords()`.
    /// `windows=False` : balayage complet (référence des tests) / full scan (test reference).
    /// Renvoie / returns [(start, end, recognizer_index, value, score, personal, reason)].
    #[pyo3(signature = (hits, text, folded, active, strict, company_mode, facility_mask, ei_groups, segments=None, forced=None, zones=Vec::new(), windows=true, person_groups=Vec::new(), entity_groups=Vec::new()))]
    #[allow(clippy::too_many_arguments, clippy::type_complexity)]
    fn scan(
        &self,
        py: Python<'_>,
        hits: &PyHits,
        text: &str,
        folded: &str,
        active: Vec<bool>,
        strict: bool,
        company_mode: &str,
        facility_mask: bool,
        ei_groups: Vec<String>,
        segments: Option<Vec<(usize, usize)>>,
        forced: Option<Vec<Vec<String>>>,
        zones: Vec<(usize, usize, Vec<String>)>,
        windows: bool,
        person_groups: Vec<String>,
        entity_groups: Vec<String>,
    ) -> PyResult<Vec<(usize, usize, usize, Option<String>, f64, bool, Option<&'static str>)>> {
        if let (Some(segments), Some(forced)) = (&segments, &forced) {
            if segments.len() != forced.len() {
                return Err(PyValueError::new_err("forced : un ensemble par segment / one forced set per segment"));
            }
        }
        let ids = &self.ids;
        let group_ids = |groups: &[String]| -> Vec<u32> { groups.iter().filter_map(|g| ids.get(g).copied()).collect() };
        let active: Vec<bool> = active.iter().zip(&self.supported).map(|(a, s)| *a && *s).collect();
        let ei = group_ids(&ei_groups);
        let (person, entity) = (group_ids(&person_groups), group_ids(&entity_groups));
        let forced: Option<Vec<Vec<u32>>> = forced.map(|segments| segments.iter().map(|gs| group_ids(gs)).collect());
        let zones: Vec<Zone> =
            zones.iter().map(|(start, end, gs)| Zone { start: *start, end: *end, groups: group_ids(gs) }).collect();
        let mut zone_groups: Vec<u32> = zones.iter().flat_map(|z| z.groups.iter().copied()).collect();
        zone_groups.sort_unstable();
        zone_groups.dedup();
        let classes = self.tables.get().classes(py, &[text])?;
        let hits = Arc::clone(&hits.hits);
        let found = py.detach(|| {
            let ctx = Context {
                hits: &hits,
                segments: segments.as_deref(),
                forced: forced.as_deref(),
                zones: &zones,
                zone_groups: &zone_groups,
            };
            let settings = Settings {
                active: &active,
                strict,
                company_mode,
                facility_mask,
                ei_groups: &ei,
                person_groups: &person,
                entity_groups: &entity,
            };
            self.inner.scan(text, folded, &ctx, &settings, classes, windows)
        });
        Ok(found.into_iter().map(|f| (f.start, f.end, f.recognizer, f.value, f.score, f.personal, f.reason)).collect())
    }
}

/// Valide une valeur avec un validateur natif (tests différentiels) / validate with a native validator.
#[pyfunction]
fn validate(name: &str, candidate: &str) -> PyResult<Option<String>> {
    validators::lookup(name)
        .map(|f| f(candidate))
        .ok_or_else(|| PyValueError::new_err(format!("validateur inconnu / unknown validator: {name}")))
}

#[pyfunction]
fn native_validators() -> Vec<&'static str> {
    validators::NATIVE.to_vec()
}

#[pymodule]
fn gdprguardian_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Le message d'une panique pourrait citer le texte analysé : seul un libellé fixe sort sur stderr.
    // A panic message could quote the analysed text: only a fixed label goes to stderr.
    static QUIET_PANICS: std::sync::Once = std::sync::Once::new();
    QUIET_PANICS.call_once(|| std::panic::set_hook(Box::new(|_| eprintln!("gdprguardian_core: panic"))));
    m.add_class::<PyScanner>()?;
    m.add_class::<PyHits>()?;
    m.add_class::<PyUnicodeTables>()?;
    m.add_class::<prepare::Preparer>()?;
    m.add_class::<prepare::LanguageDetector>()?;
    m.add_class::<names::py::PyNameDetector>()?;
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    m.add_function(wrap_pyfunction!(native_validators, m)?)?;
    // Détecteurs natifs / native detectors.
    detectors::register(m)?;
    // Résolution, propagation, rendu et portée / resolution, propagation, rendering and scope.
    finalize::register(m)?;
    // Moteur fusionné : deux appels par document (détection, finalisation) / fused engine: two calls per document
    // (detection, finalisation).
    engine::register(m)?;
    // Lecture des classeurs xlsx / xlsx workbook reading.
    tabular::register(m)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    // Contrat avec le paquet Python (`gdprguardian._native.CONTRACT`) : à augmenter à chaque changement de nom, de
    // signature ou de sens d'une liaison. Contract with the Python package: bump at every change of a binding's
    // name, signature or semantics.
    m.add("CONTRACT", 5u32)?;
    Ok(())
}
