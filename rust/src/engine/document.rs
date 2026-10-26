//! Document d'un appel : texte préparé, contexte, zones détectées, puis finalisation sans objets par zone.
//!
//! One call's document: prepared text, context, detected spans, then finalisation without per-span objects.
//! Il vit le temps d'un `anonymize` ou d'un `analyze` et ne garde rien au-delà ; le code Python (détecteurs sans
//! jumeau) le lit par les accesseurs ci-dessous. It lives for one `anonymize` or `analyze` call and keeps nothing
//! beyond; Python code (detectors without a twin) reads it through the accessors below.

use std::collections::HashSet;
use std::sync::{Arc, Mutex, MutexGuard, PoisonError};

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyList, PyString, PyTuple};

use crate::finalize::{
    read_object, span_objects, tally_objects, Cells, Detected, PyFinalSpans, PyFinalizer, PyScope, Span, Text,
};
use crate::keywords::Hits;
use crate::scanner::Zone;
use crate::PyHits;

use super::python::PyEngine;
use super::sanitize;

/// Textes d'origine et tables de positions / original texts and offset maps.
pub(super) enum Origin {
    /// Un texte (`anonymize`, `analyze`) / one text.
    Text { original: Py<PyString>, offsets: Option<Vec<i64>> },
    /// Des cellules jointes (`anonymize_segments`, `analyze_segments`) / joined cells.
    Cells {
        originals: Vec<Py<PyString>>,
        offsets: Vec<Option<Vec<i64>>>,
        segments: Vec<(usize, usize)>,
        /// Groupes imposés par les en-têtes (identifiants), et l'objet Python reçu / forced groups and the object.
        forced: Option<Vec<Vec<u32>>>,
        forced_object: Option<Py<PyAny>>,
    },
}

/// État modifié pendant la détection, puis consommé par la finalisation / state changed while detecting.
#[derive(Default)]
pub(super) struct State {
    pub detected: Detected,
    /// Début du passage courant dans `detected.spans` (`ctx.found`) / start of the current pass.
    pub pass_start: usize,
    /// Identités des objets rendus par Python : un objet rendu deux fois sort du domaine natif.
    /// Identities of the objects returned by Python: an object returned twice leaves the native domain.
    pub identities: HashSet<usize>,
    /// Une zone faite par Python sort du domaine natif : finalisation par la référence Python.
    /// A Python-made span is outside the native domain: finalisation by the Python reference.
    pub outside: bool,
    /// Mesures dans l'ordre d'insertion d'un dict Python / timings in Python dict insertion order.
    pub timings: Vec<(String, f64)>,
    /// Mode auto : pays choisis par Python, et leurs raisons / auto mode: countries chosen by Python, reasons.
    pub countries: Option<(Py<PyTuple>, Py<PyAny>)>,
    /// `DetectionContext` des détecteurs Python, construit au premier besoin / built on first need.
    pub context: Option<Py<PyAny>>,
    /// Zones remises à la finalisation / spans handed over to finalisation.
    pub finished: bool,
    /// `ctx.found` a remis des objets à Python : relus après chaque appel Python (`Document::refresh`).
    /// `ctx.found` handed objects to Python: read again after each Python call.
    pub exposed: bool,
}

impl State {
    /// `timings[key] = ms` d'un dict Python : la place d'une clé est celle de sa première écriture.
    /// A Python dict assignment: a key keeps the place of its first write.
    pub fn set_timing(&mut self, key: &str, ms: f64, accumulate: bool) {
        match self.timings.iter_mut().find(|(k, _)| k == key) {
            Some((_, value)) => *value = if accumulate { *value + ms } else { ms },
            None => self.timings.push((key.to_owned(), ms)),
        }
    }

    /// Ajoute une zone faite par du code Python ; hors du domaine natif, l'objet est gardé tel quel.
    /// Adds a span made by Python code; outside the native domain, the object is kept as is.
    pub fn push_object(&mut self, object: Py<PyAny>, span: Option<Span>) {
        let origin = self.detected.objects.len();
        if !self.identities.insert(object.as_ptr() as usize) {
            self.outside = true; // Python modifierait deux fois le même objet / Python would mutate it twice
        }
        // Zone illisible : un emplacement garde l'ordre, l'objet seul compte / unreadable: a slot keeps the order.
        let span = span.unwrap_or_else(|| {
            self.outside = true;
            Span {
                start: 0,
                end: 0,
                entity: "".into(),
                label: "".into(),
                source: "".into(),
                score: 0.0,
                priority: 0,
                value: None,
                personal: true,
                forms: Vec::new(),
                propagate: false,
                reason: None,
                origin: None,
            }
        });
        let span = Span { origin: Some(origin), ..span };
        self.detected.objects.push((object, span.clone()));
        self.detected.spans.push(span);
    }
}

#[pyclass(name = "Document", frozen, module = "gdprguardian_core")]
pub struct Document {
    pub(super) engine: Py<PyEngine>,
    /// Texte de détection (normalisé) et texte replié / detection (normalised) and folded texts.
    pub(super) norm: String,
    pub(super) folded: String,
    /// Longueur en caractères Python / length in Python characters.
    pub(super) length: usize,
    pub(super) origin: Origin,
    pub(super) hits: Arc<Hits>,
    pub(super) zones: Vec<Zone>,
    pub(super) zone_groups: Vec<u32>,
    pub(super) language: Py<PyString>,
    pub(super) state: Mutex<State>,
}

impl Document {
    pub(super) fn lock(&self) -> MutexGuard<'_, State> {
        // Aucun code sous ce verrou ne panique ; un verrou empoisonné reste cohérent / no code here panics.
        self.state.lock().unwrap_or_else(PoisonError::into_inner)
    }

    pub(super) fn segment_bounds(&self) -> Option<&[(usize, usize)]> {
        match &self.origin {
            Origin::Cells { segments, .. } => Some(segments),
            Origin::Text { .. } => None,
        }
    }

    pub(super) fn forced_groups(&self) -> Option<&[Vec<u32>]> {
        match &self.origin {
            Origin::Cells { forced, .. } => forced.as_deref(),
            Origin::Text { .. } => None,
        }
    }

    /// Fin du segment de `pos` (`ctx.segment(pos)[2]`), `None` sans segments / end of `pos`'s segment.
    pub(super) fn segment_end(&self, pos: usize) -> Option<usize> {
        let segments = self.segment_bounds()?;
        let index = segments.partition_point(|s| s.0 <= pos).checked_sub(1)?;
        segments.get(index).map(|s| s.1)
    }

    /// Zones remises à la finalisation (une seule fois), si toutes sont dans le domaine natif.
    /// Spans handed over to finalisation (once), when all of them are in the native domain.
    fn take(&self) -> Option<Detected> {
        let mut state = self.lock();
        if state.outside || state.finished {
            return None;
        }
        state.finished = true;
        Some(std::mem::take(&mut state.detected))
    }

    /// Objets `Span` de zones, dans l'ordre : objet d'origine pour les zones Python, neuf sinon. `adopt` : chaque
    /// objet neuf devient celui de sa zone, comme la liste `ctx.found` de Python garde les mêmes objets d'un
    /// détecteur à l'autre. `Span` objects of spans, in order: the original object for Python-made spans, a new
    /// one otherwise; `adopt`: each new object becomes its span's own, as Python's `ctx.found` list keeps the
    /// same objects from one detector to the next.
    fn objects<'py>(
        &self,
        py: Python<'py>,
        from: impl FnOnce(&State) -> usize,
        adopt: bool,
    ) -> PyResult<Bound<'py, PyList>> {
        let (start, spans, objects) = {
            let state = self.lock();
            let start = from(&state).min(state.detected.spans.len());
            let objects: Vec<(Py<PyAny>, Span)> =
                state.detected.objects.iter().map(|(object, span)| (object.clone_ref(py), span.clone())).collect();
            (start, state.detected.spans[start..].to_vec(), objects)
        };
        // Hors verrou : créer un objet `Span` exécute du code Python / outside the lock: building runs Python code.
        let built = span_objects(self.engine.get().span_type.bind(py), &spans, &objects)?;
        if adopt {
            self.adopt(start, &spans, &built);
        }
        PyList::new(py, built)
    }

    /// Les objets neufs des zones natives deviennent les leurs : même objet à chaque lecture, et une modification
    /// par Python est vue (`refresh`). New objects of native spans become their own: the same object on every
    /// read, and a change made by Python is seen.
    fn adopt(&self, start: usize, spans: &[Span], built: &[Bound<'_, PyAny>]) {
        let mut state = self.lock();
        state.exposed = true;
        for (index, (span, object)) in (start..).zip(spans.iter().zip(built)) {
            // Pendant la détection, les zones ne sont qu'ajoutées : l'indice désigne encore la même zone.
            // While detecting, spans are only appended: the index still designates the same span.
            if span.origin.is_some() || state.detected.spans.get(index).is_none_or(|s| s.origin.is_some()) {
                continue;
            }
            let origin = state.detected.objects.len();
            state.identities.insert(object.as_ptr() as usize);
            state.detected.objects.push((object.clone().unbind(), Span { origin: Some(origin), ..span.clone() }));
            if let Some(slot) = state.detected.spans.get_mut(index) {
                slot.origin = Some(origin);
            }
        }
    }

    /// Après un appel Python, si `ctx.found` a remis des objets : un objet modifié (la référence Python verrait
    /// la modification) fait finaliser le document par la référence Python, sur ces objets mêmes. After a Python
    /// call, once `ctx.found` handed objects out: a changed object (the Python reference would see the change)
    /// has the document finalised by the Python reference, over these very objects.
    pub(super) fn refresh(&self, py: Python<'_>) {
        let objects: Vec<(Py<PyAny>, Span)> = {
            let state = self.lock();
            if !state.exposed || state.outside {
                return;
            }
            state.detected.objects.iter().map(|(object, span)| (object.clone_ref(py), span.clone())).collect()
        };
        let span_type = self.engine.get().span_type.bind(py);
        let changed = objects.iter().any(|(object, before)| {
            let now = read_object(object.bind(py), span_type, before.origin.unwrap_or(0), self.length);
            // Score au bit près : 0.0 et -0.0 sont égaux pour `==` / score bit for bit: 0.0 == -0.0.
            now.is_none_or(|now| now != *before || now.score.to_bits() != before.score.to_bits())
        });
        if changed {
            self.lock().outside = true;
        }
    }

    /// `sanitize_output` d'une sortie, sans GIL, ses plans chargés avant / of an output, GIL released.
    fn sanitized(&self, py: Python<'_>, output: String) -> PyResult<String> {
        let table = self.engine.get().table.get();
        table.table().prepare(py, &[&output])?;
        table.table().detach(py, || sanitize::sanitize(table, output))
    }

    fn original<'py>(&self, py: Python<'py>) -> PyResult<(Bound<'py, PyString>, Option<&[i64]>)> {
        match &self.origin {
            Origin::Text { original, offsets } => Ok((original.bind(py).clone(), offsets.as_deref())),
            Origin::Cells { .. } => Err(PyRuntimeError::new_err("document de cellules / a cells document")),
        }
    }

    /// Cellules d'origine, tables des positions et bornes des cellules / original cells, offset maps, bounds.
    #[allow(clippy::type_complexity)]
    fn cells<'a, 'py>(
        &'a self,
        py: Python<'py>,
    ) -> PyResult<(Vec<Bound<'py, PyString>>, &'a [Option<Vec<i64>>], &'a [(usize, usize)])> {
        match &self.origin {
            Origin::Cells { originals, offsets, segments, .. } => {
                Ok((originals.iter().map(|o| o.bind(py).clone()).collect(), offsets, segments))
            }
            Origin::Text { .. } => Err(PyRuntimeError::new_err("document d'un texte / a single-text document")),
        }
    }
}

/// Résultat d'un `anonymize` : (texte, remplacées, conservées, explications, zones à la demande).
/// An `anonymize` result: (text, replaced, kept, explanations, spans on demand).
type Anonymized<'py> = (String, Bound<'py, PyAny>, Bound<'py, PyAny>, Bound<'py, PyAny>, PyFinalSpans);

#[pymethods]
impl Document {
    /// Texte de détection / detection text.
    #[getter]
    fn text<'py>(&self, py: Python<'py>) -> Bound<'py, PyString> {
        PyString::new(py, &self.norm)
    }

    #[getter]
    fn folded<'py>(&self, py: Python<'py>) -> Bound<'py, PyString> {
        PyString::new(py, &self.folded)
    }

    /// Occurrences des mots-clés (`KeywordHits`) / keyword hits.
    #[getter]
    fn hits(&self) -> PyHits {
        let scanner = self.engine.get().scanner.get();
        PyHits { hits: Arc::clone(&self.hits), names: Arc::clone(&scanner.names), ids: Arc::clone(&scanner.ids) }
    }

    #[getter]
    fn language(&self, py: Python<'_>) -> Py<PyString> {
        self.language.clone_ref(py)
    }

    /// Pays du contexte : fixés, ou choisis en mode auto (vide avant le choix) / countries of the context.
    #[getter]
    fn countries(&self, py: Python<'_>) -> Py<PyTuple> {
        match &self.lock().countries {
            Some((countries, _)) => countries.clone_ref(py),
            None => self.engine.get().countries.clone_ref(py),
        }
    }

    /// Raisons du choix des pays en mode auto, sinon `None` / auto-mode country reasons, else `None`.
    #[getter]
    fn reasons(&self, py: Python<'_>) -> Option<Py<PyAny>> {
        self.lock().countries.as_ref().map(|(_, reasons)| reasons.clone_ref(py))
    }

    /// (débuts, fins) des cellules, ou `None` / (starts, ends) of the cells, or `None`.
    #[getter]
    fn segments(&self) -> Option<(Vec<usize>, Vec<usize>)> {
        self.segment_bounds().map(|segments| segments.iter().copied().unzip())
    }

    /// Groupes imposés tels que reçus, ou `None` / forced groups as received, or `None`.
    #[getter]
    fn forced(&self, py: Python<'_>) -> Option<Py<PyAny>> {
        match &self.origin {
            Origin::Cells { forced_object, .. } => forced_object.as_ref().map(|f| f.clone_ref(py)),
            Origin::Text { .. } => None,
        }
    }

    /// Cellules de tableau Markdown : [(début, fin, noms des groupes)] / Markdown table cells.
    #[getter]
    fn zones(&self) -> Vec<(usize, usize, Vec<String>)> {
        let names = &self.engine.get().scanner.get().names;
        let name = |g: &u32| names.get(*g as usize).cloned();
        self.zones.iter().map(|z| (z.start, z.end, z.groups.iter().filter_map(name).collect())).collect()
    }

    /// Table des positions d'origine (`array('q')` en octets), ou `None` / original offsets, or `None`.
    #[getter]
    fn offsets<'py>(&self, py: Python<'py>) -> Option<Bound<'py, PyBytes>> {
        let bytes =
            |offsets: &[i64]| PyBytes::new(py, &offsets.iter().flat_map(|o| o.to_ne_bytes()).collect::<Vec<u8>>());
        match &self.origin {
            Origin::Text { offsets, .. } => offsets.as_deref().map(bytes),
            Origin::Cells { .. } => None,
        }
    }

    /// Tables des positions de chaque cellule / each cell's offset map.
    #[getter]
    fn cell_offsets<'py>(&self, py: Python<'py>) -> Vec<Option<Bound<'py, PyBytes>>> {
        let bytes =
            |offsets: &[i64]| PyBytes::new(py, &offsets.iter().flat_map(|o| o.to_ne_bytes()).collect::<Vec<u8>>());
        match &self.origin {
            Origin::Cells { offsets, .. } => offsets.iter().map(|o| o.as_deref().map(bytes)).collect(),
            Origin::Text { .. } => Vec::new(),
        }
    }

    /// Mesures (clé, ms), dans l'ordre / timings (key, ms), in order.
    #[getter]
    fn timings(&self) -> Vec<(String, f64)> {
        self.lock().timings.clone()
    }

    /// Une zone Python est hors du domaine natif : la référence Python finalise / Python finalises.
    #[getter]
    fn outside(&self) -> bool {
        self.lock().outside
    }

    /// Zones du passage en cours, en objets `Span` ; `adopt` pour `ctx.found` (objets gardés et surveillés), pas
    /// pour une simple lecture (`evidence`). Spans of the current pass as `Span` objects; `adopt` for
    /// `ctx.found` (objects kept and watched), not for a plain read.
    #[pyo3(signature = (adopt=false))]
    fn found<'py>(&self, py: Python<'py>, adopt: bool) -> PyResult<Bound<'py, PyList>> {
        self.objects(py, |state| state.pass_start, adopt)
    }

    /// `locale.evidence(ctx.found)` sans objet par zone : (IBAN, indicatifs, domaines), ou `None` si une valeur
    /// non ASCII demande la casse de Python (ou si une zone Python est illisible) : `evidence` reprend.
    /// `locale.evidence(ctx.found)` without one object per span; `None` when a non-ASCII value needs Python's
    /// case rules (or a Python span is unreadable): `evidence` takes over.
    fn evidence(&self) -> Option<(Vec<String>, Vec<String>, Vec<String>)> {
        let state = self.lock();
        if state.outside {
            return None;
        }
        let (mut ibans, mut phones, mut tlds) = (Vec::new(), Vec::new(), Vec::new());
        for span in state.detected.spans.get(state.pass_start..).unwrap_or_default() {
            let value = span.value.as_deref().unwrap_or("");
            match &*span.entity {
                // `value[:2].upper()`, `len(value) >= 2`
                "IBAN" if value.chars().nth(1).is_some() => {
                    let head: String = value.chars().take(2).collect();
                    if !head.is_ascii() {
                        return None;
                    }
                    ibans.push(head.to_ascii_uppercase());
                }
                // `value[1:4]` si `value.startswith("+")`
                "PHONE" if value.starts_with('+') => phones.push(value.chars().skip(1).take(3).collect()),
                // `value.rsplit(".", 1)[-1].lower()`, gardé à deux caractères / kept at two characters
                "EMAIL" => {
                    let tld = value.rsplit('.').next().unwrap_or(value);
                    if !tld.is_ascii() {
                        return None;
                    }
                    if tld.len() == 2 {
                        tlds.push(tld.to_ascii_lowercase());
                    }
                }
                _ => {}
            }
        }
        Some((ibans, phones, tlds))
    }

    /// (début du passage, nombre de zones) : inchangé, `found()` rendrait les mêmes zones (on n'en retire jamais
    /// pendant la détection). Unchanged, `found()` would give the same spans (none is removed while detecting).
    #[getter]
    fn found_key(&self) -> (usize, usize) {
        let state = self.lock();
        (state.pass_start, state.detected.spans.len())
    }

    /// Toutes les zones détectées, en objets `Span`, pour la finalisation Python ; `None` une fois remises.
    /// All detected spans as `Span` objects, for the Python finalisation; `None` once handed over.
    fn detected<'py>(&self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyList>>> {
        if self.lock().finished {
            return Ok(None);
        }
        self.objects(py, |_| 0, false).map(Some)
    }

    /// Résolution, propagation, rendu et nettoyage (`sanitize_output`) en Rust ; `None` : la référence Python
    /// finalise. Resolution, propagation, rendering and output hygiene in Rust; `None`: Python finalises.
    #[allow(clippy::too_many_arguments)]
    fn anonymize<'py>(
        &self,
        py: Python<'py>,
        finalizer: &Bound<'py, PyAny>,
        scope: Option<&Bound<'py, PyScope>>,
        labels: &Bound<'py, PyTuple>,
        explain: bool,
        sanitize: bool,
    ) -> PyResult<Option<Anonymized<'py>>> {
        let Ok(finalizer) = finalizer.cast::<PyFinalizer>() else { return Ok(None) };
        if !finalizer.get().renders_natively() {
            return Ok(None);
        }
        let (original, offsets) = self.original(py)?;
        let original = original.to_str()?;
        let Some(detected) = self.take() else { return Ok(None) };
        let text = Text { norm: &self.norm, offsets, original };
        let Some((output, tally, spans)) =
            finalizer.get().anonymize_detected(py, detected, text, scope, labels, explain)?
        else {
            return Ok(None);
        };
        let output = if sanitize { self.sanitized(py, output)? } else { output };
        let (replaced, kept, explain) = tally_objects(py, tally)?;
        Ok(Some((output, replaced.into_any(), kept.into_any(), explain, spans)))
    }

    /// Zones finales en positions d'origine ; `None` : la référence Python finalise.
    /// Final spans in original offsets; `None`: the Python reference finalises.
    fn analyze<'py>(&self, py: Python<'py>, finalizer: &Bound<'py, PyAny>) -> PyResult<Option<Bound<'py, PyList>>> {
        let Ok(finalizer) = finalizer.cast::<PyFinalizer>() else { return Ok(None) };
        let (_, offsets) = self.original(py)?;
        let Some(detected) = self.take() else { return Ok(None) };
        finalizer.get().analyze_detected(py, detected, &self.norm, offsets)
    }

    /// `anonymize_segments` : (sorties, remplacées, conservées, explications), sans objet par zone ; ou `None`.
    /// (outputs, replaced, kept, explanations), with no per-span object; or `None`.
    #[allow(clippy::type_complexity, clippy::too_many_arguments)]
    fn anonymize_cells<'py>(
        &self,
        py: Python<'py>,
        finalizer: &Bound<'py, PyAny>,
        scope: &Bound<'py, PyScope>,
        labels: &Bound<'py, PyTuple>,
        explain: bool,
        sanitize: bool,
    ) -> PyResult<Option<(Vec<String>, Bound<'py, PyAny>, Bound<'py, PyAny>, Bound<'py, PyAny>)>> {
        let Ok(finalizer) = finalizer.cast::<PyFinalizer>() else { return Ok(None) };
        if !finalizer.get().renders_natively() {
            return Ok(None);
        }
        let (originals, offsets, segments) = self.cells(py)?;
        let originals = originals.iter().map(|o| o.to_str()).collect::<PyResult<Vec<&str>>>()?;
        let Some(detected) = self.take() else { return Ok(None) };
        let (starts, ends) = segments.iter().copied().unzip();
        let cells = Cells { joined: &self.norm, starts, ends, offsets, originals: &originals };
        let Some((outputs, tally)) =
            finalizer.get().anonymize_detected_cells(py, detected, cells, scope, labels, explain)?
        else {
            return Ok(None);
        };
        let outputs = if sanitize {
            outputs.into_iter().map(|out| self.sanitized(py, out)).collect::<PyResult<Vec<String>>>()?
        } else {
            outputs
        };
        let (replaced, kept, explain) = tally_objects(py, tally)?;
        Ok(Some((outputs, replaced.into_any(), kept.into_any(), explain)))
    }

    /// `analyze_segments` : (zones par cellule, toutes les zones), ou `None` / (per cell, all), or `None`.
    fn analyze_cells<'py>(
        &self,
        py: Python<'py>,
        finalizer: &Bound<'py, PyAny>,
    ) -> PyResult<Option<(Bound<'py, PyList>, Bound<'py, PyList>)>> {
        let Ok(finalizer) = finalizer.cast::<PyFinalizer>() else { return Ok(None) };
        let (_, offsets, segments) = self.cells(py)?;
        let Some(detected) = self.take() else { return Ok(None) };
        let (starts, ends) = segments.iter().copied().unzip();
        let cells = Cells { joined: &self.norm, starts, ends, offsets, originals: &[] };
        finalizer.get().analyze_detected_cells(py, detected, cells)
    }
}

/// Lit les zones rendues par du code Python (hors verrou), puis les ajoute au document.
/// Reads the spans returned by Python code (outside the lock), then adds them to the document.
pub(super) fn add_python_spans(document: &Document, py: Python<'_>, objects: Vec<Bound<'_, PyAny>>) {
    let span_type = document.engine.get().span_type.bind(py);
    let read: Vec<(Py<PyAny>, Option<Span>)> = objects
        .into_iter()
        .map(|object| {
            // L'indice d'origine est fixé à l'ajout / the origin index is set when added.
            let span = read_object(&object, span_type, 0, document.length);
            (object.unbind(), span)
        })
        .collect();
    let mut state = document.lock();
    for (object, span) in read {
        state.push_object(object, span);
    }
}
