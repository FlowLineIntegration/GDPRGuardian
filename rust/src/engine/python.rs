//! Interface Python du moteur fusionné : construction une fois par `Anonymizer`, puis une détection par appel.
//!
//! Python interface of the fused engine: built once per `Anonymizer`, then one detection per call. `None` :
//! l'entrée sort du domaine natif (demi-codets isolés, groupes imposés incohérents) ; rien n'a été exécuté et le
//! chemin par étapes, identique, reprend. `None`: the input is outside the native domain (lone surrogates,
//! inconsistent forced groups); nothing ran and the identical staged path takes over. Un texte décomposé (NFD)
//! reste ici : seuls les trois détecteurs à vue NFC (noms, adresses, organisations) passent par leur `detect`
//! Python. A decomposed (NFD) text stays here: only the three NFC-view detectors run their Python `detect`.

use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyTuple, PyType};

use crate::detectors::PyUnicodeTable;
use crate::finalize::IndexedText;
use crate::keywords::Hits;
use crate::prepare::{LanguageDetector, Preparer};
use crate::scanner::{Context, Zone};
use crate::text::Classes;
use crate::PyScanner;

use super::document::{Document, Origin, State};
use super::passes::{Run, Shared};
use super::plan::{Custom, Mode, Pack, Policy, Reader, Recognizer};
use super::tables;

/// Séparateur des cellules jointes (`engine._SEGMENT_SEPARATOR`) / joined-cell separator.
const SEPARATOR: &str = "\n\n";

/// Moteur d'un `Anonymizer` : composants Rust existants, plan des packs et réglages, fixés à la construction.
/// An `Anonymizer`'s engine: existing Rust components, pack plan and settings, fixed at construction.
#[pyclass(name = "Engine", frozen, module = "gdprguardian_core")]
pub struct PyEngine {
    pub(super) preparer: Py<Preparer>,
    pub(super) language: Py<LanguageDetector>,
    pub(super) scanner: Py<PyScanner>,
    pub(super) table: Py<PyUnicodeTable>,
    pub(super) span_type: Py<PyType>,
    /// Recognizers de l'analyseur, dans son ordre / the scanner's recognizers, in its order.
    pub(super) recognizers: Vec<Recognizer>,
    pub(super) packs: Vec<Pack>,
    pub(super) mode: Mode,
    /// Packs actifs (pays fixés) / active packs (fixed countries).
    pub(super) active: Vec<bool>,
    /// `ctx.countries` des pays fixés, `()` en mode auto avant le choix / before the auto choice.
    pub(super) countries: Py<PyTuple>,
    pub(super) policy: Policy,
    /// Détecteurs ajoutés (`Settings.detectors`) : (appel, clé de mesure) / added detectors: (call, timing key).
    pub(super) extras: Vec<(usize, String)>,
    pub(super) deny: Option<usize>,
    pub(super) custom: Custom,
    /// Diacritiques combinants (`_compose._COMMON_MARKS`) : dans un texte décomposé, les détecteurs à vue NFC
    /// passent par Python. Combining marks: in a decomposed text, the NFC-view detectors go through Python.
    marks: Vec<String>,
}

impl PyEngine {
    /// `_compose.decomposed` : `ctx.has(_COMMON_MARKS)` sur un texte non ASCII ; la vue NFC des détecteurs
    /// (`composed_view`) est alors faite par Python. On a non-ASCII text; the detectors' NFC view is then Python's.
    fn decomposed(&self, norm: &str, folded: &str) -> bool {
        !norm.is_ascii() && self.marks.iter().any(|mark| folded.contains(mark.as_str()))
    }

    /// Groupes de contexte d'un court texte (`context_groups`) / context groups of a short text.
    fn groups_of(&self, text: &str, classes: &Classes) -> Vec<u32> {
        let scanner = self.scanner.get();
        let hits: Hits = scanner.inner.keywords.scan(&self.preparer.get().fold_parts(text), classes);
        (0..scanner.names.len() as u32).filter(|&g| hits.count(g) > 0).collect()
    }

    /// Mots-clés, langue, zones de tableau, puis détection / keywords, language, table zones, then detection.
    /// `None` au-delà de 4 Gio (positions sur 32 bits) / `None` beyond 4 GiB (32-bit offsets).
    #[allow(clippy::too_many_arguments)]
    fn run<'py>(
        slf: &Bound<'py, Self>,
        host: &Bound<'py, PyAny>,
        norm: String,
        folded: String,
        origin: Origin,
        tables: bool,
        started: Option<Instant>,
    ) -> PyResult<Option<Py<Document>>> {
        let py = slf.py();
        let engine = slf.get();
        // Positions sur 32 bits (`IndexedText`) / 32-bit offsets.
        if u32::try_from(norm.len()).is_err() {
            return Ok(None);
        }
        let scanner = engine.scanner.get();
        let classes = scanner.tables.get().classes(py, &[&norm, &folded])?;
        // Plans préparés : un plan manqué pendant la détection (filet de sécurité) la fait échouer.
        // Planes prepared: a plane missed during detection (safety net) makes it fail.
        let missed = classes.missed();
        let decomposed = engine.decomposed(&norm, &folded);
        let hits = py.detach(|| scanner.inner.keywords.scan(&folded, classes));
        let language = engine.language.get().language_of(py, &folded);
        let zones: Vec<Zone> = if tables {
            let table = engine.table.get();
            tables::zones(&norm, |header| engine.groups_of(header, classes), |c| table.is_space(c))
        } else {
            Vec::new()
        };
        let mut zone_groups: Vec<u32> = zones.iter().flat_map(|z| z.groups.iter().copied()).collect();
        zone_groups.sort_unstable();
        zone_groups.dedup();
        let mut state = State::default();
        if let Some(started) = started {
            state.set_timing("prepare", started.elapsed().as_secs_f64() * 1000.0, false);
        }
        let document = Bound::new(
            py,
            Document {
                engine: slf.clone().unbind(),
                length: norm.chars().count(),
                norm,
                folded,
                origin,
                hits: Arc::new(hits),
                zones,
                zone_groups,
                language,
                state: Mutex::new(state),
            },
        )?;
        let doc = document.get();
        let context = Context {
            hits: &doc.hits,
            segments: doc.segment_bounds(),
            forced: doc.forced_groups(),
            zones: &doc.zones,
            zone_groups: &doc.zone_groups,
        };
        let Some(text) = IndexedText::new(&doc.norm) else { return Ok(None) };
        let has_digit = doc.norm.bytes().any(|b| b.is_ascii_digit());
        let shared = Shared { norm: &doc.norm, folded: &doc.folded, context, text, has_digit, classes, decomposed };
        let detected = Run { py, engine, document: &document, doc, host, shared }.detect();
        // Le contexte Python voit le document (`ctx.found`) : le garder ferait un cycle que le ramasse-miettes ne
        // voit pas. The Python context sees the document: keeping it would make a cycle the collector cannot see.
        let context = doc.lock().context.take();
        drop(context);
        detected?;
        classes.unchanged(missed)?;
        Ok(Some(document.unbind()))
    }
}

#[pymethods]
impl PyEngine {
    /// Construit par `Anonymizer` (`engine.py`), avec ses composants Rust et son plan / built by `Anonymizer`.
    #[new]
    #[pyo3(signature = (*, preparer, language, scanner, table, span_type, recognizers, packs, auto, active, countries,
                        strict, company_ids, facility_mask, ei_groups, person_groups, entity_groups, entities,
                        excluded, extras, deny, custom, marks))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        preparer: Py<Preparer>,
        language: Py<LanguageDetector>,
        scanner: Py<PyScanner>,
        table: Py<PyUnicodeTable>,
        span_type: &Bound<'_, PyType>,
        recognizers: &Bound<'_, PyAny>,
        packs: &Bound<'_, PyAny>,
        auto: bool,
        active: Vec<bool>,
        countries: Py<PyTuple>,
        strict: bool,
        company_ids: String,
        facility_mask: bool,
        ei_groups: Vec<String>,
        person_groups: Vec<String>,
        entity_groups: Vec<String>,
        entities: Option<HashSet<String>>,
        excluded: HashSet<String>,
        extras: Vec<(usize, String)>,
        deny: Option<usize>,
        custom: Option<&Bound<'_, PyDict>>,
        marks: Vec<String>,
    ) -> PyResult<Self> {
        let group_ids: Arc<HashMap<String, u32>> = Arc::clone(&scanner.get().ids);
        let reader = Reader { span_type, group_ids: &group_ids };
        let recognizers =
            recognizers.try_iter()?.map(|entry| reader.recognizer(&entry?)).collect::<PyResult<Vec<Recognizer>>>()?;
        let packs =
            packs.try_iter()?.map(|pack| reader.pack(pack?.cast::<PyDict>()?)).collect::<PyResult<Vec<Pack>>>()?;
        let policy = Policy {
            strict,
            company_ids,
            facility_mask,
            ei_groups: reader.groups(&ei_groups),
            person_groups: reader.groups(&person_groups),
            entity_groups: reader.groups(&entity_groups),
            entities,
            excluded,
        };
        let custom = reader.custom(custom)?;
        Ok(Self {
            preparer,
            language,
            scanner,
            table,
            span_type: span_type.clone().unbind(),
            recognizers,
            packs,
            mode: if auto { Mode::Auto } else { Mode::Fixed },
            active,
            countries,
            policy,
            extras,
            deny,
            custom,
            marks,
        })
    }

    /// Préparation et détection d'un texte (`_detect_text`) ; `None` hors du domaine natif.
    /// Preparation and detection of one text; `None` outside the native domain.
    fn detect(
        slf: &Bound<'_, Self>,
        text: &Bound<'_, PyString>,
        host: &Bound<'_, PyAny>,
    ) -> PyResult<Option<Py<Document>>> {
        let py = slf.py();
        let started = Instant::now();
        let Ok(source) = text.to_str() else { return Ok(None) };
        let preparer = slf.get().preparer.get();
        let classes = preparer.classes_for(py, &[source])?;
        let (norm, folded, offsets) = py.detach(|| preparer.prepare_parts(source, classes));
        let norm = norm.unwrap_or_else(|| source.to_owned());
        let folded = folded.unwrap_or_else(|| norm.clone());
        let origin = Origin::Text { original: text.clone().unbind(), offsets };
        Self::run(slf, host, norm, folded, origin, true, Some(started))
    }

    /// Cellules jointes (`_detect_segments`) : contexte borné à chaque cellule, sauf les groupes imposés.
    /// Joined cells: context bounded to each cell, except forced groups. `None` hors du domaine natif.
    fn detect_cells(
        slf: &Bound<'_, Self>,
        texts: &Bound<'_, PyAny>,
        forced: Option<&Bound<'_, PyAny>>,
        host: &Bound<'_, PyAny>,
    ) -> PyResult<Option<Py<Document>>> {
        let py = slf.py();
        let Ok(originals) = texts.try_iter()?.map(|t| Ok(t?.cast_into::<PyString>()?)).collect::<PyResult<Vec<_>>>()
        else {
            return Ok(None);
        };
        let Ok(sources) = originals.iter().map(|t| t.to_str()).collect::<PyResult<Vec<&str>>>() else {
            return Ok(None);
        };
        let engine = slf.get();
        let forced_ids = match forced {
            None => None,
            Some(forced) => {
                let Ok(sets) = forced.extract::<Vec<HashSet<String>>>() else { return Ok(None) };
                if sets.len() != sources.len() {
                    return Ok(None);
                }
                let ids = &engine.scanner.get().ids;
                Some(sets.iter().map(|set| set.iter().filter_map(|g| ids.get(g).copied()).collect()).collect())
            }
        };
        let preparer = engine.preparer.get();
        let classes = preparer.classes_for(py, &sources)?;
        let normalized: Vec<(Option<String>, Option<Vec<i64>>)> =
            py.detach(|| sources.iter().map(|s| preparer.normalize_parts(s, classes)).collect());
        let mut norm = String::new();
        let mut segments = Vec::with_capacity(sources.len());
        let mut cursor = 0;
        for (index, ((cell, _), source)) in normalized.iter().zip(&sources).enumerate() {
            if index > 0 {
                norm.push_str(SEPARATOR);
                cursor += SEPARATOR.len();
            }
            let cell = cell.as_deref().unwrap_or(source);
            let length = cell.chars().count();
            segments.push((cursor, cursor + length));
            cursor += length;
            norm.push_str(cell);
        }
        let folded = preparer.fold_parts(&norm).into_owned();
        let origin = Origin::Cells {
            originals: originals.into_iter().map(Bound::unbind).collect(),
            offsets: normalized.into_iter().map(|(_, offsets)| offsets).collect(),
            segments,
            forced: forced_ids,
            forced_object: forced.map(|f| f.clone().unbind()),
        };
        Self::run(slf, host, norm, folded, origin, false, None)
    }
}

/// Enregistre le moteur dans `gdprguardian_core` / registers the engine in `gdprguardian_core`.
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyEngine>()?;
    module.add_function(wrap_pyfunction!(phone_candidates, module)?)?;
    module.add_function(wrap_pyfunction!(sanitize_output, module)?)?;
    Ok(())
}

/// Jumeau de `sanitize.sanitize_output` (tests différentiels) ; `None` pour un texte non encodable en UTF-8.
/// Twin of `sanitize.sanitize_output` (differential tests); `None` for a text with lone surrogates.
#[pyfunction]
fn sanitize_output(
    py: Python<'_>,
    table: &Bound<'_, PyUnicodeTable>,
    text: &Bound<'_, PyString>,
) -> PyResult<Option<String>> {
    let (table, Ok(text)) = (table.get(), text.to_str()) else { return Ok(None) };
    table.table().without_gil(py, &[text], || super::sanitize::sanitize(table, text.to_owned())).map(Some)
}

/// Candidats de `InternationalPhoneDetector` : [(début, fin)], sans GIL ; `None` pour un texte non encodable en
/// UTF-8 (demi-codets isolés) : la regex Python reprend. Phone candidates, GIL released; `None` for a text with
/// lone surrogates: the Python regex takes over.
#[pyfunction]
fn phone_candidates(
    py: Python<'_>,
    table: &Bound<'_, PyUnicodeTable>,
    text: &Bound<'_, PyString>,
) -> PyResult<Option<Vec<(usize, usize)>>> {
    let (table, Ok(text)) = (table.get(), text.to_str()) else { return Ok(None) };
    table.table().without_gil(py, &[text], || super::phone::candidates(text, |c| table.is_word(c))).map(Some)
}
