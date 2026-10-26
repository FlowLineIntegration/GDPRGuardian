//! Liaison Python : règles de texte, portée et finaliseur / Python bindings: text rules, scope, finalizer.
//!
//! Chaque méthode lit les zones Python, rend le GIL pendant le calcul, puis écrit les résultats. `None`
//! signifie « hors du domaine natif » : rien n'a été modifié et le moteur Python, la référence, reprend
//! avec les mêmes entrées. Each method reads the Python spans, releases the GIL for the work, then writes
//! the results. `None` means "outside the native domain": nothing was changed and the reference Python
//! engine takes over with the same inputs.

use std::collections::{BTreeMap, HashMap};
use std::sync::{Arc, Mutex, PoisonError, TryLockError};

use pyo3::exceptions::{PyOSError, PyRuntimeError, PyValueError};
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple, PyType};

use super::chars::{Chars, Rules};
use super::indexed::IndexedText;
use super::pipeline::{map_offsets, split_segments, Finalizer};
use super::propagate::Segments;
use super::render::{ExplainLine, Operator, Recognizer, RenderRules, Tally};
use super::resolve::{KeepRules, Policy};
use super::scope::{split_person_name, Scope, ScopeClosed};
use super::span::Span;
use super::Unsupported;
use crate::unicode::PyUnicodeTables;

const CLOSED: &str = "Portée fermée / scope closed";

/// Échec d'un calcul sans GIL / failure of a GIL-free computation.
pub(super) enum Failure {
    /// Le moteur Python prend le relais / the Python engine takes over.
    Unsupported,
    Closed,
    Randomness(String),
}

impl From<Unsupported> for Failure {
    fn from(_: Unsupported) -> Self {
        Self::Unsupported
    }
}

impl From<ScopeClosed> for Failure {
    fn from(_: ScopeClosed) -> Self {
        Self::Closed
    }
}

fn closed_error(_: ScopeClosed) -> PyErr {
    PyRuntimeError::new_err(CLOSED)
}

/// Règles de texte partagées, construites une fois par processus (`_native.text_rules`).
/// Shared text rules, built once per process.
#[pyclass(name = "TextRules", frozen, module = "gdprguardian_core")]
pub struct PyTextRules {
    rules: Arc<Rules>,
}

impl PyTextRules {
    /// Charge, GIL tenu, les plans hors BMP de ces textes dans la table partagée (une fois par processus) : une
    /// erreur de Python remonte ici, et aucun appel à Python ne suit. Loads, GIL held, these texts' astral planes
    /// into the shared table (once per process): a Python error propagates here, and no Python call follows.
    pub(super) fn prepare<'a>(&self, py: Python<'_>, texts: impl IntoIterator<Item = &'a str>) -> PyResult<()> {
        let texts: Vec<&str> = texts.into_iter().collect();
        self.rules.unicode.prepare(py, &texts)
    }

    /// `Python::detach` après `prepare` ; un plan manqué pendant le calcul (filet de sécurité) le fait échouer.
    /// `Python::detach` after `prepare`; a plane missed during the work (safety net) makes it fail.
    pub(super) fn detach<T: Send>(&self, py: Python<'_>, work: impl FnOnce() -> T + Send) -> PyResult<T> {
        self.rules.unicode.detach(py, work)
    }

    fn with_chars<T>(&self, py: Python<'_>, text: &str, f: impl FnOnce(&Chars) -> T) -> PyResult<T> {
        self.prepare(py, [text])?;
        Ok(f(&Chars::new(&self.rules)))
    }
}

#[pymethods]
impl PyTextRules {
    /// `tables` : table Unicode partagée (`_native.unicode_tables()`), repliement compris ; `honorifics` :
    /// civilités repliées ; `particles` : particules de tête d'un nom de famille, repliées. `tables`: the shared
    /// Unicode table, folding included; `honorifics`: folded titles; `particles`: folded leading surname particles.
    #[new]
    fn new(tables: &Bound<'_, PyUnicodeTables>, honorifics: Vec<String>, particles: Vec<String>) -> Self {
        Self { rules: Arc::new(Rules::new(tables.get().shared(), honorifics, particles)) }
    }

    /// Drapeaux de chaque caractère (tests différentiels) / each character's flags (differential tests).
    fn flags(&self, py: Python<'_>, text: &str) -> PyResult<Vec<u16>> {
        self.with_chars(py, text, |chars| text.chars().map(|c| chars.flags(c)).collect())
    }

    /// `str.upper()` (tests différentiels) / differential tests.
    fn upper(&self, py: Python<'_>, text: &str) -> PyResult<String> {
        self.with_chars(py, text, |chars| chars.upper(text))
    }

    /// `_text.fold` (tests différentiels) / differential tests.
    fn fold(&self, py: Python<'_>, text: &str) -> PyResult<String> {
        self.with_chars(py, text, |chars| chars.fold(text))
    }

    /// `scope.split_person_name` (tests différentiels) / differential tests.
    fn split_person_name(&self, py: Python<'_>, text: &str) -> PyResult<Option<(Option<String>, String)>> {
        self.with_chars(py, text, |chars| split_person_name(chars, text))
    }
}

/// Portée native de `scope.Scope` : la clé ne quitte jamais Rust / native scope, the key never leaves Rust.
#[pyclass(name = "Scope", frozen, module = "gdprguardian_core")]
pub struct PyScope {
    rules: Py<PyTextRules>,
    /// Tenu sans GIL pendant un rendu (`with_scope`). Règle : rien sous ce verrou n'appelle Python, et personne ne
    /// l'attend GIL tenu (`with`) ; sinon l'interpréteur entier s'arrêterait le temps du rendu, voire se bloquerait.
    /// Held without the GIL while rendering. Rule: nothing under this lock calls Python, and nobody waits for it
    /// with the GIL held; otherwise the whole interpreter would stall for the rendering, or even deadlock.
    state: Mutex<Scope>,
}

impl PyScope {
    /// La portée sous son verrou, jamais attendu GIL tenu : pris ailleurs (rendu en cours), le GIL est rendu le
    /// temps de l'attente. `work` ne reçoit pas `py` : il ne peut pas appeler Python. The scope under its lock,
    /// never waited for with the GIL held: when taken elsewhere, the GIL is released while waiting. `work` gets no
    /// `py`: it cannot call Python.
    fn with<T: Send>(&self, py: Python<'_>, work: impl FnOnce(&mut Scope) -> T + Send) -> T {
        // Aucun code de la portée ne panique ; un verrou empoisonné reste cohérent / no scope code panics.
        match self.state.try_lock() {
            Ok(mut scope) => work(&mut scope),
            Err(TryLockError::Poisoned(poisoned)) => work(&mut poisoned.into_inner()),
            Err(TryLockError::WouldBlock) => {
                py.detach(|| work(&mut self.state.lock().unwrap_or_else(PoisonError::into_inner)))
            }
        }
    }
}

#[pymethods]
impl PyScope {
    #[new]
    fn new(rules: Py<PyTextRules>) -> PyResult<Self> {
        let scope = Scope::new().map_err(PyOSError::new_err)?;
        Ok(Self { rules, state: Mutex::new(scope) })
    }

    #[getter]
    fn closed(&self, py: Python<'_>) -> bool {
        self.with(py, |scope| scope.closed())
    }

    /// Efface la clé et les empreintes / wipes the key and the digests.
    fn close(&self, py: Python<'_>) {
        self.with(py, Scope::close);
    }

    /// Balises déjà présentes dans l'entrée / placeholders already in the input.
    fn reserve(&self, py: Python<'_>, text: &Bound<'_, PyString>) {
        // Motif ASCII : remplacer un substitut isolé ne change aucune correspondance / ASCII pattern.
        let text = text.to_string_lossy();
        self.with(py, |scope| scope.reserve(&text));
    }

    /// `Scope.placeholder`, libellé déjà affiché / with the displayed label.
    fn placeholder(
        &self,
        py: Python<'_>,
        display: &str,
        entity: &Bound<'_, PyString>,
        value: &Bound<'_, PyString>,
    ) -> PyResult<String> {
        // L'entité n'est comparée qu'à « PERSON » : une version sans substitut suffit, comme en Python.
        // The entity is only compared with "PERSON": a surrogate-free copy is enough, as in Python.
        let entity = entity.to_string_lossy();
        let entity = &*entity;
        let rules = self.rules.get();
        if let Ok(text) = value.to_str() {
            rules.prepare(py, [text])?;
            let chars = Chars::new(&rules.rules);
            return self.with(py, |scope| scope.placeholder(&chars, display, entity, text)).map_err(closed_error);
        }
        // Substituts isolés : Python ne peut pas les encoder dans l'empreinte ; seule la clé d'un nom reconnu
        // (faite de lettres, donc sans eux) passe. Lone surrogates cannot be encoded into the digest; only the
        // key of a recognised name (made of letters, hence without them) goes through.
        let lossy = value.to_string_lossy();
        rules.prepare(py, [&*lossy])?;
        let chars = Chars::new(&rules.rules);
        let numbered = self
            .with(py, |scope| -> Result<Option<String>, ScopeClosed> {
                if scope.closed() {
                    return Err(ScopeClosed);
                }
                let key = if entity == "PERSON" { scope.person_key(&chars, &lossy)? } else { None };
                key.map(|key| scope.numbered(display, &key)).transpose()
            })
            .map_err(closed_error)?;
        // Python (`encode`, peut-être d'une sous-classe de `str`) seulement une fois le verrou rendu ; la portée
        // n'a pas changé. Python only once the lock is released; the scope has not changed.
        numbered.ok_or_else(|| {
            value
                .call_method1(intern!(py, "encode"), ("utf-8",))
                .err()
                .unwrap_or_else(|| PyValueError::new_err("valeur non encodable / unencodable value"))
        })
    }

    /// `Scope.person_key` ; `None` : clé brute, calculée par Python / raw key, computed by Python.
    fn person_key(&self, py: Python<'_>, text: &Bound<'_, PyString>) -> PyResult<Option<String>> {
        let lossy = text.to_string_lossy();
        let rules = self.rules.get();
        rules.prepare(py, [&*lossy])?;
        let chars = Chars::new(&rules.rules);
        self.with(py, |scope| scope.person_key(&chars, &lossy)).map_err(closed_error)
    }
}

/// Zones lues en Python : objets d'origine et état natif / spans read from Python: objects and native state.
struct Input<'py> {
    objects: Vec<Bound<'py, PyAny>>,
    spans: Vec<Span>,
}

impl Input<'_> {
    /// Textes à classer : valeurs, formes et sources des zones / strings to classify.
    fn strings(&self) -> impl Iterator<Item = &str> {
        self.spans.iter().flat_map(|s| {
            s.value.as_deref().into_iter().chain(s.forms.iter().map(|f| &**f)).chain(std::iter::once(&*s.source))
        })
    }
}

fn exact_str(value: &Bound<'_, PyAny>) -> Option<Arc<str>> {
    if !value.is_exact_instance_of::<PyString>() {
        return None;
    }
    Some(value.cast::<PyString>().ok()?.to_str().ok()?.into())
}

/// Une zone Python aux types exacts (`types.Span`), sinon `None` / a Python span with exact types.
pub(super) fn read_span<'py>(object: &Bound<'py, PyAny>, origin: usize, length: usize) -> Option<Span> {
    let py = object.py();
    let get = |name: &Bound<'py, PyString>| object.getattr(name).ok();
    let position = |value: Bound<'py, PyAny>| -> Option<usize> {
        let position: usize = value.is_exact_instance_of::<PyInt>().then(|| value.extract().ok())??;
        (position <= length).then_some(position)
    };
    let flag = |value: Bound<'_, PyAny>| value.is_exact_instance_of::<PyBool>().then(|| value.is_truthy().ok())?;
    let score = get(intern!(py, "score"))?;
    let score: f64 = score.is_exact_instance_of::<PyFloat>().then(|| score.extract().ok())??;
    let priority = get(intern!(py, "priority"))?;
    let value = get(intern!(py, "value"))?;
    let reason = get(intern!(py, "reason"))?;
    let forms = get(intern!(py, "forms"))?;
    let forms = forms.is_exact_instance_of::<PyTuple>().then(|| forms.cast_into::<PyTuple>().ok())??;
    Some(Span {
        start: position(get(intern!(py, "start"))?)?,
        end: position(get(intern!(py, "end"))?)?,
        entity: exact_str(&get(intern!(py, "entity"))?)?,
        label: exact_str(&get(intern!(py, "label"))?)?,
        source: exact_str(&get(intern!(py, "source"))?)?,
        // NaN : ordre de tri Python indéfini / NaN: undefined Python sort order.
        score: (!score.is_nan()).then_some(score)?,
        priority: priority.is_exact_instance_of::<PyInt>().then(|| priority.extract().ok())??,
        value: if value.is_none() { None } else { Some(exact_str(&value)?.to_string()) },
        personal: flag(get(intern!(py, "personal"))?)?,
        forms: forms.iter().map(|form| exact_str(&form)).collect::<Option<_>>()?,
        propagate: flag(get(intern!(py, "propagate"))?)?,
        reason: if reason.is_none() { None } else { Some(exact_str(&reason)?) },
        origin: Some(origin),
    })
}

/// Lit les zones ; `None` si l'une sort du domaine natif (type inattendu, position hors du texte, objet
/// présent deux fois). Reads the spans; `None` if one is outside the native domain.
fn read_spans<'py>(list: &Bound<'py, PyList>, span_type: &Bound<'py, PyType>, length: usize) -> Option<Input<'py>> {
    let objects: Vec<Bound<'py, PyAny>> = list.iter().collect();
    let mut identities: Vec<usize> = objects.iter().map(|o| o.as_ptr() as usize).collect();
    identities.sort_unstable();
    if identities.windows(2).any(|w| w[0] == w[1]) {
        return None; // Python modifierait deux fois le même objet / Python would mutate one object twice.
    }
    let spans = objects
        .iter()
        .enumerate()
        .map(|(origin, object)| object.is_exact_instance(span_type).then(|| read_span(object, origin, length))?)
        .collect::<Option<Vec<Span>>>()?;
    Some(Input { objects, spans })
}

/// `array('q')` de `_text.normalize`, en octets natifs / native-endian bytes.
fn read_offsets(bytes: Option<&Bound<'_, PyBytes>>) -> Option<Option<Vec<i64>>> {
    let Some(bytes) = bytes else {
        return Some(None);
    };
    let (chunks, rest) = bytes.as_bytes().as_chunks::<8>();
    rest.is_empty().then(|| Some(chunks.iter().map(|&c| i64::from_ne_bytes(c)).collect()))
}

/// Libellé affiché de chaque libellé des zones, par `display` (Python) / displayed label of each span label.
/// `labels` : `(LABELS.display, langue, neutre)`, soit `Scope.label_text` sans enveloppe Python.
/// `labels`: `(LABELS.display, language, neutral)`, i.e. `Scope.label_text` without a Python wrapper.
fn read_labels(labels: &Bound<'_, PyTuple>, spans: &[Span]) -> PyResult<HashMap<Arc<str>, String>> {
    let (display, language, neutral) = (labels.get_item(0)?, labels.get_item(1)?, labels.get_item(2)?);
    let mut shown: HashMap<Arc<str>, String> = HashMap::new();
    for span in spans {
        if !shown.contains_key(&span.label) {
            let text: String = display.call1((&*span.label, &language, &neutral))?.extract()?;
            shown.insert(span.label.clone(), text);
        }
    }
    Ok(shown)
}

pub(super) fn displays<'a>(labels: &'a HashMap<Arc<str>, String>, spans: &[Span]) -> Result<Vec<&'a str>, Unsupported> {
    spans.iter().map(|s| labels.get(&s.label).map(String::as_str).ok_or(Unsupported)).collect()
}

/// Portée de l'appel : celle de Python, ou une portée propre effacée à la fin / the caller's or an own one.
/// Appelée sans GIL ; `work` n'appelle jamais Python (voir `PyScope::state`) / called without the GIL; `work`
/// never calls Python.
pub(super) fn with_scope<T>(
    shared: Option<&Mutex<Scope>>,
    work: impl FnOnce(&mut Scope) -> Result<T, Failure>,
) -> Result<T, Failure> {
    match shared {
        Some(state) => work(&mut state.lock().unwrap_or_else(PoisonError::into_inner)),
        None => work(&mut Scope::new().map_err(Failure::Randomness)?),
    }
}

pub(super) fn counts<'py>(py: Python<'py>, counts: &BTreeMap<String, u64>) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);
    for (key, count) in counts {
        dict.set_item(key, count)?;
    }
    Ok(dict)
}

/// `engine._aggregate` : une ligne par (balise, règle, raison) / one line per (tag, rule, reason).
pub(super) fn explain_lines<'py>(py: Python<'py>, lines: Option<Vec<ExplainLine>>) -> PyResult<Bound<'py, PyAny>> {
    let Some(lines) = lines else {
        return Ok(py.None().into_bound(py));
    };
    let list = PyList::empty(py);
    for line in lines {
        let entry = PyDict::new(py);
        entry.set_item(if line.kept { intern!(py, "kept") } else { intern!(py, "tag") }, line.tag)?;
        entry.set_item(intern!(py, "rule"), line.rule)?;
        entry.set_item(intern!(py, "reason"), line.reason)?;
        entry.set_item(intern!(py, "count"), line.count)?;
        list.append(entry)?;
    }
    Ok(list.into_any())
}

/// Finaliseur d'un `Anonymizer` : résolution, propagation, rendu / an `Anonymizer`'s finalizer.
#[pyclass(name = "Finalizer", frozen, module = "gdprguardian_core")]
pub struct PyFinalizer {
    inner: Finalizer,
    rules: Py<PyTextRules>,
    span_type: Py<PyType>,
}

impl PyFinalizer {
    fn read<'py>(&self, py: Python<'py>, spans: &Bound<'py, PyList>, length: usize) -> Option<Input<'py>> {
        read_spans(spans, self.span_type.bind(py), length)
    }

    pub(super) fn failure(failure: Failure) -> PyResult<()> {
        match failure {
            Failure::Unsupported => Ok(()),
            Failure::Closed => Err(PyRuntimeError::new_err(CLOSED)),
            Failure::Randomness(message) => Err(PyOSError::new_err(message)),
        }
    }

    /// Objets Python des zones finales : l'objet d'origine modifié sur place, comme en Python, ou un neuf.
    /// Python objects of the final spans: the original object mutated in place, as in Python, or a new one.
    fn objects<'py>(&self, py: Python<'py>, input: &Input<'py>, spans: &[Span]) -> PyResult<Vec<Bound<'py, PyAny>>> {
        spans
            .iter()
            .map(|span| match span.origin.and_then(|i| Some((input.objects.get(i)?, input.spans.get(i)?))) {
                Some((object, before)) => {
                    sync(object, before, span)?;
                    Ok(object.clone())
                }
                None => span_object(self.span_type.bind(py), span),
            })
            .collect()
    }
}

/// Nouvel objet `types.Span` d'une zone / a new `types.Span` object for a span.
pub(super) fn span_object<'py>(span_type: &Bound<'py, PyType>, span: &Span) -> PyResult<Bound<'py, PyAny>> {
    let forms = PyTuple::new(span_type.py(), span.forms.iter().map(|f| &**f))?;
    span_type.call1((
        span.start,
        span.end,
        &*span.entity,
        &*span.label,
        &*span.source,
        span.score,
        span.priority,
        span.value.as_deref(),
        span.personal,
        forms,
        span.propagate,
        span.reason.as_deref(),
    ))
}

/// Reporte sur l'objet Python les champs que le moteur Python modifie sur place / in-place field updates.
pub(super) fn sync(object: &Bound<'_, PyAny>, before: &Span, after: &Span) -> PyResult<()> {
    let py = object.py();
    if after.start != before.start {
        object.setattr(intern!(py, "start"), after.start)?;
    }
    if after.end != before.end {
        object.setattr(intern!(py, "end"), after.end)?;
    }
    if after.value != before.value {
        object.setattr(intern!(py, "value"), after.value.as_deref())?;
    }
    if after.personal != before.personal {
        object.setattr(intern!(py, "personal"), after.personal)?;
    }
    if after.source != before.source {
        object.setattr(intern!(py, "source"), &*after.source)?;
    }
    if after.propagate != before.propagate {
        object.setattr(intern!(py, "propagate"), after.propagate)?;
    }
    if after.reason != before.reason {
        object.setattr(intern!(py, "reason"), after.reason.as_deref())?;
    }
    Ok(())
}

#[pymethods]
impl PyFinalizer {
    /// Réglages d'un `Anonymizer` ; `operators=None` : rendu laissé à Python / rendering left to Python.
    #[new]
    #[pyo3(signature = (rules, span_type, *, min_score, allow, mergeable, keep_entity, unmaskable,
                        priority_validated, priority_propagated, operators, forced_replace, detector_reasons,
                        recognizers))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        rules: Py<PyTextRules>,
        span_type: Py<PyType>,
        min_score: f64,
        allow: Vec<String>,
        mergeable: Vec<String>,
        keep_entity: Option<String>,
        unmaskable: Vec<String>,
        priority_validated: i64,
        priority_propagated: i64,
        operators: Option<Vec<(String, String)>>,
        forced_replace: Vec<String>,
        detector_reasons: Vec<(String, String)>,
        recognizers: Vec<(String, String, bool)>,
    ) -> PyResult<Self> {
        let operators: Option<HashMap<String, Operator>> = operators.and_then(|pairs| {
            pairs.into_iter().map(|(key, name)| Operator::from_name(&name).map(|op| (key, op))).collect()
        });
        let render = operators.map(|operators| RenderRules {
            operators,
            forced_replace: forced_replace.into_iter().collect(),
            detector_reasons: detector_reasons.into_iter().collect(),
            recognizers: recognizers
                .into_iter()
                .map(|(id, tier, validator)| (id, Recognizer { tier, validator }))
                .collect(),
        });
        let inner = Finalizer {
            policy: Policy {
                min_score,
                allow: allow.into_iter().collect(),
                mergeable: mergeable.into_iter().map(String::into_boxed_str).collect(),
            },
            keep: keep_entity.map(|entity| KeepRules {
                entity: entity.into_boxed_str(),
                unmaskable: unmaskable.into_iter().map(String::into_boxed_str).collect(),
                priority_validated,
            }),
            priority_propagated,
            render,
        };
        Ok(Self { inner, rules, span_type })
    }

    /// Le rendu natif est-il disponible ? / is native rendering available?
    #[getter]
    fn renders(&self) -> bool {
        self.inner.render.is_some()
    }

    /// `analyze` après détection : zones finales en positions d'origine, ou `None`.
    /// `analyze` after detection: final spans in original offsets, or `None`.
    #[pyo3(signature = (spans, text, offsets=None))]
    fn analyze<'py>(
        &self,
        py: Python<'py>,
        spans: &Bound<'py, PyList>,
        text: &Bound<'py, PyString>,
        offsets: Option<&Bound<'py, PyBytes>>,
    ) -> PyResult<Option<Bound<'py, PyList>>> {
        let Ok(norm) = text.to_str() else { return Ok(None) };
        let (Some(index), Some(offsets)) = (IndexedText::new(norm), read_offsets(offsets)) else { return Ok(None) };
        let Some(input) = self.read(py, spans, index.len()) else { return Ok(None) };
        let rules = self.rules.get();
        rules.prepare(py, input.strings().chain([norm]))?;
        let finalizer = &self.inner;
        let outcome = rules.detach(py, || -> Result<Vec<Span>, Failure> {
            let chars = Chars::new(&rules.rules);
            let mut spans = finalizer.finalize(&chars, &index, input.spans.clone(), None)?;
            if let Some(offsets) = &offsets {
                map_offsets(&mut spans, offsets)?;
            }
            Ok(spans)
        })?;
        let finals = match outcome {
            Ok(finals) => finals,
            Err(failure) => return Self::failure(failure).map(|()| None),
        };
        Ok(Some(PyList::new(py, self.objects(py, &input, &finals)?)?))
    }

    /// `analyze_segments` après détection : (zones par segment, toutes les zones), ou `None`.
    /// `analyze_segments` after detection: (spans per segment, all spans), or `None`.
    fn analyze_segments<'py>(
        &self,
        py: Python<'py>,
        spans: &Bound<'py, PyList>,
        text: &Bound<'py, PyString>,
        starts: Vec<usize>,
        ends: Vec<usize>,
        offsets: Vec<Option<Bound<'py, PyBytes>>>,
    ) -> PyResult<Option<Bound<'py, PyTuple>>> {
        let Ok(joined) = text.to_str() else { return Ok(None) };
        let (Some(index), Some(segments)) = (IndexedText::new(joined), Segments::new(starts, ends)) else {
            return Ok(None);
        };
        let Some(offsets) = offsets.iter().map(|o| read_offsets(o.as_ref())).collect::<Option<Vec<_>>>() else {
            return Ok(None);
        };
        let Some(input) = self.read(py, spans, index.len()) else { return Ok(None) };
        let rules = self.rules.get();
        rules.prepare(py, input.strings().chain([joined]))?;
        let finalizer = &self.inner;
        let outcome = rules.detach(py, || -> Result<_, Failure> {
            let chars = Chars::new(&rules.rules);
            let mut spans = finalizer.finalize(&chars, &index, input.spans.clone(), Some(&segments))?;
            let members = split_segments(&mut spans, &segments, &offsets)?;
            Ok((spans, members))
        })?;
        let (finals, members) = match outcome {
            Ok(result) => result,
            Err(failure) => return Self::failure(failure).map(|()| None),
        };
        let objects = self.objects(py, &input, &finals)?;
        let per_segment = PyList::empty(py);
        for positions in members {
            per_segment.append(PyList::new(py, positions.iter().filter_map(|&p| objects.get(p)))?)?;
        }
        Ok(Some(PyTuple::new(py, [per_segment.into_any(), PyList::new(py, objects)?.into_any()])?))
    }

    /// `anonymize` après détection, en un appel : (texte, zones, remplacées, conservées, explications), ou
    /// `None`. `scope=None` : portée propre, effacée à la fin. In one call: (text, spans, replaced, kept,
    /// explain), or `None`; `scope=None`: an own scope, wiped at the end.
    #[pyo3(signature = (spans, text, offsets, original, scope, labels, explain))]
    #[allow(clippy::too_many_arguments)]
    fn anonymize<'py>(
        &self,
        py: Python<'py>,
        spans: &Bound<'py, PyList>,
        text: &Bound<'py, PyString>,
        offsets: Option<&Bound<'py, PyBytes>>,
        original: &Bound<'py, PyString>,
        scope: Option<&Bound<'py, PyScope>>,
        labels: &Bound<'py, PyTuple>,
        explain: bool,
    ) -> PyResult<Option<Bound<'py, PyTuple>>> {
        let Some(render) = &self.inner.render else { return Ok(None) };
        let (Ok(norm), Ok(source)) = (text.to_str(), original.to_str()) else { return Ok(None) };
        let (Some(index), Some(source_index), Some(offsets)) =
            (IndexedText::new(norm), IndexedText::new(source), read_offsets(offsets))
        else {
            return Ok(None);
        };
        let Some(input) = self.read(py, spans, index.len()) else { return Ok(None) };
        let labels = read_labels(labels, &input.spans)?;
        let rules = self.rules.get();
        rules.prepare(py, input.strings().chain([norm, source]))?;
        let shared = scope.map(|s| &s.get().state);
        let finalizer = &self.inner;
        let outcome = rules.detach(py, || -> Result<_, Failure> {
            let chars = Chars::new(&rules.rules);
            let mut spans = finalizer.finalize(&chars, &index, input.spans.clone(), None)?;
            if let Some(offsets) = &offsets {
                map_offsets(&mut spans, offsets)?;
            }
            // Tout ce qui peut renvoyer à Python précède la première modification de la portée.
            // Everything that may hand over to Python happens before the scope's first change.
            let shown = displays(&labels, &spans)?;
            let mut tally = Tally::new(explain);
            let output = with_scope(shared, |scope| {
                scope.reserve(source);
                let items = spans.iter().zip(shown.iter().copied());
                Ok(render.render(&chars, scope, &source_index, items, &mut tally)?)
            })?;
            Ok((output, spans, tally))
        })?;
        let (output, finals, tally) = match outcome {
            Ok(result) => result,
            Err(failure) => return Self::failure(failure).map(|()| None),
        };
        let objects = PyList::new(py, self.objects(py, &input, &finals)?)?;
        let fields = [
            output.into_pyobject(py)?.into_any(),
            objects.into_any(),
            counts(py, &tally.replaced)?.into_any(),
            counts(py, &tally.kept)?.into_any(),
            explain_lines(py, tally.explain)?,
        ];
        Ok(Some(PyTuple::new(py, fields)?))
    }

    /// `anonymize_segments` après détection, en un appel, sans aucun objet par zone : (sorties, remplacées,
    /// conservées, explications), ou `None`. In one call, with no object per span: (outputs, replaced, kept,
    /// explain), or `None`.
    #[pyo3(signature = (spans, text, starts, ends, offsets, originals, scope, labels, explain))]
    #[allow(clippy::too_many_arguments)]
    fn anonymize_segments<'py>(
        &self,
        py: Python<'py>,
        spans: &Bound<'py, PyList>,
        text: &Bound<'py, PyString>,
        starts: Vec<usize>,
        ends: Vec<usize>,
        offsets: Vec<Option<Bound<'py, PyBytes>>>,
        originals: Vec<Bound<'py, PyString>>,
        scope: &Bound<'py, PyScope>,
        labels: &Bound<'py, PyTuple>,
        explain: bool,
    ) -> PyResult<Option<Bound<'py, PyTuple>>> {
        let Some(render) = &self.inner.render else { return Ok(None) };
        let Ok(joined) = text.to_str() else { return Ok(None) };
        let (Some(index), Some(segments)) = (IndexedText::new(joined), Segments::new(starts, ends)) else {
            return Ok(None);
        };
        let Some(offsets) = offsets.iter().map(|o| read_offsets(o.as_ref())).collect::<Option<Vec<_>>>() else {
            return Ok(None);
        };
        let Some(sources) = originals.iter().map(|o| o.to_str().ok()).collect::<Option<Vec<&str>>>() else {
            return Ok(None);
        };
        let Some(source_indexes) = sources.iter().map(|s| IndexedText::new(s)).collect::<Option<Vec<_>>>() else {
            return Ok(None);
        };
        if sources.len() != segments.len() || offsets.len() != segments.len() {
            return Ok(None);
        }
        let Some(input) = self.read(py, spans, index.len()) else { return Ok(None) };
        let labels = read_labels(labels, &input.spans)?;
        let rules = self.rules.get();
        rules.prepare(py, input.strings().chain([joined]).chain(sources.iter().copied()))?;
        let state = &scope.get().state;
        let finalizer = &self.inner;
        let outcome = rules.detach(py, || -> Result<_, Failure> {
            let chars = Chars::new(&rules.rules);
            let mut spans = finalizer.finalize(&chars, &index, input.spans.clone(), Some(&segments))?;
            let members = split_segments(&mut spans, &segments, &offsets)?;
            let shown = displays(&labels, &spans)?;
            let mut tally = Tally::new(explain);
            let mut outputs = Vec::with_capacity(source_indexes.len());
            with_scope(Some(state), |scope| {
                for (source, positions) in source_indexes.iter().zip(&members) {
                    let items = positions.iter().filter_map(|&p| Some((spans.get(p)?, *shown.get(p)?)));
                    outputs.push(render.render(&chars, scope, source, items, &mut tally)?);
                }
                Ok(())
            })?;
            Ok((outputs, tally))
        })?;
        let (outputs, tally) = match outcome {
            Ok(result) => result,
            Err(failure) => return Self::failure(failure).map(|()| None),
        };
        let fields = [
            PyList::new(py, outputs)?.into_any(),
            counts(py, &tally.replaced)?.into_any(),
            counts(py, &tally.kept)?.into_any(),
            explain_lines(py, tally.explain)?,
        ];
        Ok(Some(PyTuple::new(py, fields)?))
    }
}

// --- Moteur fusionné : accès en lecture aux réglages / fused engine: read access to the settings ----------------

impl PyTextRules {
    /// Règles de texte partagées / shared text rules.
    pub(crate) fn rules(&self) -> &Rules {
        &self.rules
    }
}

impl PyFinalizer {
    pub(super) fn core(&self) -> &Finalizer {
        &self.inner
    }

    pub(super) fn text_rules(&self) -> &PyTextRules {
        self.rules.get()
    }

    pub(super) fn span_type<'py>(&self, py: Python<'py>) -> &Bound<'py, PyType> {
        self.span_type.bind(py)
    }
}

impl PyScope {
    /// Verrou de la portée, pris sans GIL par le rendu ; rien sous ce verrou n'appelle Python.
    /// The scope's lock, taken without the GIL by rendering; nothing under this lock calls Python.
    pub(super) fn state(&self) -> &Mutex<Scope> {
        &self.state
    }
}

/// Enregistre les classes du module / registers the module's classes.
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyTextRules>()?;
    module.add_class::<PyScope>()?;
    module.add_class::<PyFinalizer>()?;
    Ok(())
}
