//! Finalisation d'un document du moteur fusionné (`crate::engine`) / finalisation of a fused-engine document.
//!
//! Les zones restent des structures Rust de la détection au rendu : mêmes étapes et même code que les méthodes
//! de `PyFinalizer` (`Finalizer`, `RenderRules`, `Scope`), sans lire un objet Python par zone. Seuls les objets
//! `Span` que l'API publique demande sont créés, et seulement à la demande. Spans stay Rust structures from
//! detection to rendering: same steps and same code as `PyFinalizer`'s methods, without reading one Python
//! object per span. Only the `Span` objects the public API asks for are created, and only on demand.

use std::collections::{HashMap, HashSet};
use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple, PyType};

use super::chars::Chars;
use super::indexed::IndexedText;
use super::pipeline::{map_offsets, split_segments};
use super::propagate::Segments;
use super::python::{
    counts, displays, explain_lines, read_span, span_object, sync, with_scope, Failure, PyFinalizer, PyScope,
};
use super::render::Tally;
use super::span::Span;

/// Zones d'un document, dans l'ordre de détection / a document's spans, in detection order.
#[derive(Default)]
pub(crate) struct Detected {
    /// Une zone faite par du code Python a `origin = Some(i)`, son indice dans `objects`.
    /// A span made by Python code has `origin = Some(i)`, its index in `objects`.
    pub spans: Vec<Span>,
    /// Objet de chaque zone faite par Python et son état lu : le résultat le modifie sur place, comme le chemin
    /// par étapes. Each Python-made span's object and its state as read: the result mutates it in place, as the
    /// staged path does.
    pub objects: Vec<(Py<PyAny>, Span)>,
}

/// Un texte : normalisé, table des positions d'origine, texte d'origine / normalised, offset map, original.
pub(crate) struct Text<'a> {
    pub norm: &'a str,
    pub offsets: Option<&'a [i64]>,
    pub original: &'a str,
}

/// Cellules jointes par le moteur, avec leurs positions et leurs textes d'origine / joined cells.
pub(crate) struct Cells<'a> {
    pub joined: &'a str,
    pub starts: Vec<usize>,
    pub ends: Vec<usize>,
    pub offsets: &'a [Option<Vec<i64>>],
    pub originals: &'a [&'a str],
}

/// Zone d'un objet Python aux types exacts (`types.Span`), sinon `None` / a Python span with exact types.
pub(crate) fn read_object(
    object: &Bound<'_, PyAny>,
    span_type: &Bound<'_, PyType>,
    origin: usize,
    length: usize,
) -> Option<Span> {
    object.is_exact_instance(span_type).then(|| read_span(object, origin, length))?
}

/// Objets Python des zones : l'objet d'origine (modifié sur place) ou un neuf / original object or a new one.
pub(crate) fn span_objects<'py>(
    span_type: &Bound<'py, PyType>,
    spans: &[Span],
    objects: &[(Py<PyAny>, Span)],
) -> PyResult<Vec<Bound<'py, PyAny>>> {
    let py = span_type.py();
    spans
        .iter()
        .map(|span| match span.origin.and_then(|i| objects.get(i)) {
            Some((object, before)) => {
                let object = object.bind(py);
                sync(object, before, span)?;
                Ok(object.clone())
            }
            None => span_object(span_type, span),
        })
        .collect()
}

/// Compteurs du rapport : (remplacées, conservées, explications agrégées ou `None`).
/// Report counters: (replaced, kept, aggregated explanations or `None`).
pub(crate) fn tally_objects(
    py: Python<'_>,
    tally: Tally,
) -> PyResult<(Bound<'_, PyDict>, Bound<'_, PyDict>, Bound<'_, PyAny>)> {
    Ok((counts(py, &tally.replaced)?, counts(py, &tally.kept)?, explain_lines(py, tally.explain)?))
}

/// Libellé affiché de chaque libellé des zones, en un seul appel Python : `labels = (displays, langue, neutre)`,
/// où `displays(clés, langue, neutre)` rend `[LABELS.display(clé, langue, neutre) for clé in clés]`.
/// Displayed label of each span label, in one Python call.
fn displayed_labels(labels: &Bound<'_, PyTuple>, spans: &[Span]) -> PyResult<HashMap<Arc<str>, String>> {
    let (displays, language, neutral) = (labels.get_item(0)?, labels.get_item(1)?, labels.get_item(2)?);
    let mut keys: Vec<&Arc<str>> = Vec::new();
    let mut seen: HashSet<&str> = HashSet::new();
    for span in spans {
        if seen.insert(&span.label) {
            keys.push(&span.label);
        }
    }
    let names: Vec<&str> = keys.iter().map(|k| &***k).collect();
    let shown: Vec<String> = displays.call1((names, language, neutral))?.extract()?;
    if shown.len() != keys.len() {
        return Err(PyValueError::new_err("libellés manquants / missing labels"));
    }
    Ok(keys.into_iter().cloned().zip(shown).collect())
}

/// Textes à classer : valeurs, formes et sources des zones / strings to classify.
fn strings(spans: &[Span]) -> impl Iterator<Item = &str> {
    spans.iter().flat_map(|s| {
        s.value.as_deref().into_iter().chain(s.forms.iter().map(|f| &**f)).chain(std::iter::once(&*s.source))
    })
}

/// Zones finales d'un `anonymize`, transformées en objets `Span` seulement si on les lit (`Analysis.spans`).
/// Final spans of an `anonymize`, turned into `Span` objects only when read (`Analysis.spans`).
#[pyclass(name = "FinalSpans", frozen, module = "gdprguardian_core")]
pub(crate) struct PyFinalSpans {
    spans: Vec<Span>,
    objects: Vec<(Py<PyAny>, Span)>,
    span_type: Py<PyType>,
}

#[pymethods]
impl PyFinalSpans {
    /// Objets `Span` des zones finales, créés à l'appel / the final spans' `Span` objects, built when called.
    fn objects<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        PyList::new(py, span_objects(self.span_type.bind(py), &self.spans, &self.objects)?)
    }

    fn __len__(&self) -> usize {
        self.spans.len()
    }
}

impl PyFinalizer {
    /// Le rendu natif est-il disponible ? (sinon un opérateur Python rend) / is native rendering available?
    pub(crate) fn renders_natively(&self) -> bool {
        self.core().render.is_some()
    }

    /// `anonymize` après la détection du moteur fusionné : (texte, compteurs, zones finales à la demande), ou
    /// `None` hors du domaine natif. After the fused engine's detection: (text, counters, final spans on demand),
    /// or `None` outside the native domain. Tout ce qui peut renvoyer à Python précède la première modification
    /// de la portée / everything that may hand over to Python happens before the scope's first change.
    pub(crate) fn anonymize_detected(
        &self,
        py: Python<'_>,
        detected: Detected,
        text: Text<'_>,
        scope: Option<&Bound<'_, PyScope>>,
        labels: &Bound<'_, PyTuple>,
        explain: bool,
    ) -> PyResult<Option<(String, Tally, PyFinalSpans)>> {
        let finalizer = self.core();
        let Some(render) = &finalizer.render else { return Ok(None) };
        let (Some(index), Some(source_index)) = (IndexedText::new(text.norm), IndexedText::new(text.original)) else {
            return Ok(None);
        };
        let rules = self.text_rules();
        rules.prepare(py, strings(&detected.spans).chain([text.norm, text.original]))?;
        let Detected { spans, objects } = detected;
        let finalized = rules.detach(py, || -> Result<Vec<Span>, Failure> {
            let chars = Chars::new(rules.rules());
            let mut spans = finalizer.finalize(&chars, &index, spans, None)?;
            if let Some(offsets) = text.offsets {
                map_offsets(&mut spans, offsets)?;
            }
            Ok(spans)
        })?;
        let spans = match finalized {
            Ok(spans) => spans,
            Err(failure) => return Self::failure(failure).map(|()| None),
        };
        // Libellés des seules zones finales, avant toute modification de la portée.
        // Labels of the final spans only, before any change to the scope.
        let labels = displayed_labels(labels, &spans)?;
        let shared = scope.map(|s| s.get().state());
        let outcome = rules.detach(py, || -> Result<_, Failure> {
            let chars = Chars::new(rules.rules());
            let shown = displays(&labels, &spans)?;
            let mut tally = Tally::new(explain);
            let output = with_scope(shared, |scope| {
                scope.reserve(text.original);
                let items = spans.iter().zip(shown.iter().copied());
                Ok(render.render(&chars, scope, &source_index, items, &mut tally)?)
            })?;
            Ok((output, tally))
        })?;
        match outcome {
            Ok((output, tally)) => {
                let span_type = self.span_type(py).clone().unbind();
                Ok(Some((output, tally, PyFinalSpans { spans, objects, span_type })))
            }
            Err(failure) => Self::failure(failure).map(|()| None),
        }
    }

    /// `analyze` après la détection du moteur fusionné : zones finales en positions d'origine, ou `None`.
    /// `analyze` after the fused engine's detection: final spans in original offsets, or `None`.
    pub(crate) fn analyze_detected<'py>(
        &self,
        py: Python<'py>,
        detected: Detected,
        norm: &str,
        offsets: Option<&[i64]>,
    ) -> PyResult<Option<Bound<'py, PyList>>> {
        let Some(index) = IndexedText::new(norm) else { return Ok(None) };
        let rules = self.text_rules();
        rules.prepare(py, strings(&detected.spans).chain([norm]))?;
        let finalizer = self.core();
        let Detected { spans, objects } = detected;
        let outcome = rules.detach(py, || -> Result<Vec<Span>, Failure> {
            let chars = Chars::new(rules.rules());
            let mut spans = finalizer.finalize(&chars, &index, spans, None)?;
            if let Some(offsets) = offsets {
                map_offsets(&mut spans, offsets)?;
            }
            Ok(spans)
        })?;
        match outcome {
            Ok(finals) => Ok(Some(PyList::new(py, span_objects(self.span_type(py), &finals, &objects)?)?)),
            Err(failure) => Self::failure(failure).map(|()| None),
        }
    }

    /// `analyze_segments` après la détection : (zones par cellule, toutes les zones), ou `None`.
    /// `analyze_segments` after detection: (spans per cell, all spans), or `None`.
    pub(crate) fn analyze_detected_cells<'py>(
        &self,
        py: Python<'py>,
        detected: Detected,
        cells: Cells<'_>,
    ) -> PyResult<Option<(Bound<'py, PyList>, Bound<'py, PyList>)>> {
        let (Some(index), Some(segments)) = (IndexedText::new(cells.joined), Segments::new(cells.starts, cells.ends))
        else {
            return Ok(None);
        };
        let rules = self.text_rules();
        rules.prepare(py, strings(&detected.spans).chain([cells.joined]))?;
        let finalizer = self.core();
        let Detected { spans, objects } = detected;
        let offsets = cells.offsets;
        let outcome = rules.detach(py, || -> Result<_, Failure> {
            let chars = Chars::new(rules.rules());
            let mut spans = finalizer.finalize(&chars, &index, spans, Some(&segments))?;
            let members = split_segments(&mut spans, &segments, offsets)?;
            Ok((spans, members))
        })?;
        let (finals, members) = match outcome {
            Ok(result) => result,
            Err(failure) => return Self::failure(failure).map(|()| None),
        };
        let all = span_objects(self.span_type(py), &finals, &objects)?;
        let per_cell = PyList::empty(py);
        for positions in members {
            per_cell.append(PyList::new(py, positions.iter().filter_map(|&p| all.get(p)))?)?;
        }
        Ok(Some((per_cell, PyList::new(py, all)?)))
    }

    /// `anonymize_segments` après la détection, sans aucun objet par zone : (sorties, compteurs), ou `None`.
    /// `anonymize_segments` after detection, with no object per span: (outputs, counters), or `None`.
    pub(crate) fn anonymize_detected_cells(
        &self,
        py: Python<'_>,
        detected: Detected,
        cells: Cells<'_>,
        scope: &Bound<'_, PyScope>,
        labels: &Bound<'_, PyTuple>,
        explain: bool,
    ) -> PyResult<Option<(Vec<String>, Tally)>> {
        let finalizer = self.core();
        let Some(render) = &finalizer.render else { return Ok(None) };
        let (Some(index), Some(segments)) = (IndexedText::new(cells.joined), Segments::new(cells.starts, cells.ends))
        else {
            return Ok(None);
        };
        if cells.originals.len() != segments.len() || cells.offsets.len() != segments.len() {
            return Ok(None);
        }
        let Some(sources) = cells.originals.iter().map(|s| IndexedText::new(s)).collect::<Option<Vec<_>>>() else {
            return Ok(None);
        };
        let rules = self.text_rules();
        let texts = strings(&detected.spans).chain([cells.joined]).chain(cells.originals.iter().copied());
        rules.prepare(py, texts)?;
        let spans = detected.spans;
        let offsets = cells.offsets;
        let finalized = rules.detach(py, || -> Result<_, Failure> {
            let chars = Chars::new(rules.rules());
            let mut spans = finalizer.finalize(&chars, &index, spans, Some(&segments))?;
            let members = split_segments(&mut spans, &segments, offsets)?;
            Ok((spans, members))
        })?;
        let (spans, members) = match finalized {
            Ok(result) => result,
            Err(failure) => return Self::failure(failure).map(|()| None),
        };
        // Libellés des seules zones finales, avant toute modification de la portée.
        // Labels of the final spans only, before any change to the scope.
        let labels = displayed_labels(labels, &spans)?;
        let state = scope.get().state();
        let outcome = rules.detach(py, || -> Result<_, Failure> {
            let chars = Chars::new(rules.rules());
            let shown = displays(&labels, &spans)?;
            let mut tally = Tally::new(explain);
            let mut outputs = Vec::with_capacity(sources.len());
            with_scope(Some(state), |scope| {
                for (source, positions) in sources.iter().zip(&members) {
                    let items = positions.iter().filter_map(|&p| Some((spans.get(p)?, *shown.get(p)?)));
                    outputs.push(render.render(&chars, scope, source, items, &mut tally)?);
                }
                Ok(())
            })?;
            Ok((outputs, tally))
        })?;
        match outcome {
            Ok(result) => Ok(Some(result)),
            Err(failure) => Self::failure(failure).map(|()| None),
        }
    }
}
