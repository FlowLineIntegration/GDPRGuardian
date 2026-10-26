//! Passages de détection : port de `Anonymizer._detect_all` et `_detect` (Python), même ordre, mêmes mesures.
//!
//! Detection passes: port of the Python methods, same order, same timings. Analyseur natif sur les packs actifs,
//! puis, pack par pack, ses recognizers laissés à Python et ses détecteurs (jumeaux natifs ou code Python), puis
//! les extras : détecteurs ajoutés, liste de refus, règles de l'organisation. Native scanner over the active
//! packs, then pack by pack its Python recognizers and its detectors (native twins or Python code), then the
//! extras: added detectors, deny list, organisation rules. Les zones restent des structures Rust ; le GIL est
//! rendu pendant chaque calcul natif / spans stay Rust structures; the GIL is released for each native step.

use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use std::time::Instant;

use pyo3::exceptions::PyValueError;
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::PyTuple;

use crate::detectors::mrz_spans;
use crate::finalize::{IndexedText, Span};
use crate::scanner::{Context, Settings};
use crate::text::Classes;

use super::document::{add_python_spans, Document};
use super::organizations::Facts;
use super::phone;
use super::plan::{Address, BirthDates, Custom, CustomScan, Email, Iban, Mode, Mrz, Names, Organizations, Phone, Slot};
use super::python::PyEngine;

/// Millisecondes écoulées, comme `(perf_counter() - t0) * 1000` / elapsed milliseconds.
fn elapsed_ms(started: Instant) -> f64 {
    started.elapsed().as_secs_f64() * 1000.0
}

/// `fr_names.surname_form` d'une forme ASCII (`form.title() if form.isupper() else form`) : seules les lettres
/// ont une casse, un mot est une suite de lettres. `None` hors ASCII : Python et sa table de casse décident.
/// For an ASCII form: only letters are cased, a word is a run of letters. `None` beyond ASCII: Python decides.
fn ascii_surname_form(form: &str) -> Option<String> {
    if !form.is_ascii() {
        return None;
    }
    let upper = form.bytes().any(|b| b.is_ascii_uppercase()) && !form.bytes().any(|b| b.is_ascii_lowercase());
    if !upper {
        return Some(form.to_owned());
    }
    let mut cased = false;
    Some(
        form.chars()
            .map(|c| {
                let title = if cased { c.to_ascii_lowercase() } else { c.to_ascii_uppercase() };
                cased = c.is_ascii_alphabetic();
                title
            })
            .collect(),
    )
}

/// Ce que lit le calcul natif, partagé sans GIL / what native work reads, shared without the GIL.
pub(super) struct Shared<'a> {
    /// Texte de détection et texte replié / detection and folded texts.
    pub norm: &'a str,
    pub folded: &'a str,
    /// Requêtes de contexte, mêmes règles que les motifs / context queries, same rules as patterns.
    pub context: Context<'a>,
    /// Texte de détection indexé par caractère / detection text indexed by character.
    pub text: IndexedText<'a>,
    /// `ctx.has("digit")` : un chiffre ASCII dans le texte / an ASCII digit in the text.
    pub has_digit: bool,
    /// Classes de caractères des deux textes, pour l'analyseur / both texts' character classes, for the scanner.
    pub classes: &'a Classes,
    /// Texte décomposé (`_compose.decomposed`) : les détecteurs à vue NFC passent par Python.
    /// Decomposed text: the NFC-view detectors go through Python.
    pub decomposed: bool,
}

/// Une détection en cours : moteur, document et hôte Python / one detection in progress.
pub(super) struct Run<'a, 'py> {
    pub py: Python<'py>,
    pub engine: &'a PyEngine,
    /// Le document, tel que le code Python le reçoit / the document, as Python code receives it.
    pub document: &'a Bound<'py, Document>,
    pub doc: &'a Document,
    /// `calls`, `context(document)`, `select(document)` : code Python de l'`Anonymizer` / Python code.
    pub host: &'a Bound<'py, PyAny>,
    pub shared: Shared<'a>,
}

impl Run<'_, '_> {
    /// `_detect_all` : un passage (pays fixés), ou deux (mode auto) / one pass, or two in auto mode.
    pub fn detect(&self) -> PyResult<()> {
        let packs = &self.engine.packs;
        if self.engine.mode == Mode::Fixed {
            return self.pass(&self.engine.active, true);
        }
        let always: Vec<bool> = packs.iter().map(|p| p.always_on).collect();
        self.pass(&always, false)?;
        // Pays déduits des preuves validées du premier passage, par Python (`evidence`, `select_countries`).
        // Countries inferred from the first pass's validated evidence, by Python.
        let chosen = self.host.getattr(intern!(self.py, "select"))?.call1((self.document,))?;
        let (countries, reasons): (Bound<'_, PyTuple>, Bound<'_, PyAny>) = chosen.extract()?;
        let active: HashSet<String> = countries.extract::<Vec<String>>()?.into_iter().collect();
        let in_pass: Vec<bool> = packs
            .iter()
            .map(|p| !p.always_on && (p.country.as_ref().is_some_and(|c| active.contains(c)) || active.contains(&p.id)))
            .collect();
        let context = {
            let mut state = self.doc.lock();
            state.countries = Some((countries.clone().unbind(), reasons.unbind()));
            state.context.as_ref().map(|c| c.clone_ref(self.py))
        };
        if let Some(context) = context {
            context.bind(self.py).setattr(intern!(self.py, "countries"), countries)?;
        }
        self.pass(&in_pass, true)
    }

    /// `_detect` sur les packs actifs / over the active packs.
    fn pass(&self, active: &[bool], extras: bool) -> PyResult<()> {
        {
            let mut state = self.doc.lock();
            state.pass_start = state.detected.spans.len();
        }
        if active.iter().any(|&a| a) {
            self.scan(active)?;
        }
        for (pack, _) in self.engine.packs.iter().zip(active).filter(|(_, &on)| on) {
            let started = Instant::now();
            if let Some(call) = pack.recognizers {
                self.python(call)?;
            }
            for slot in &pack.slots {
                self.slot(slot)?;
            }
            self.doc.lock().set_timing(&pack.timing, elapsed_ms(started), false);
        }
        if !extras {
            return Ok(());
        }
        for (call, key) in &self.engine.extras {
            let started = Instant::now();
            self.python(*call)?;
            self.doc.lock().set_timing(key, elapsed_ms(started), false);
        }
        if let Some(call) = self.engine.deny {
            self.python(call)?;
        }
        let started = Instant::now();
        match &self.engine.custom {
            Custom::None => return Ok(()),
            Custom::Python(call) => self.python(*call)?,
            Custom::Native(custom) => self.custom(custom)?,
        }
        self.doc.lock().set_timing("custom", elapsed_ms(started), false);
        Ok(())
    }

    /// Analyseur natif des motifs des packs actifs (« native ») / native pattern scan of the active packs.
    fn scan(&self, active: &[bool]) -> PyResult<()> {
        let started = Instant::now();
        let engine = self.engine;
        let scanner = engine.scanner.get();
        let flags: Vec<bool> =
            engine.recognizers.iter().map(|r| active.get(r.pack).copied().unwrap_or(false)).collect();
        let shared = &self.shared;
        let policy = &engine.policy;
        let settings = Settings {
            active: &flags,
            strict: policy.strict,
            company_mode: &policy.company_ids,
            facility_mask: policy.facility_mask,
            ei_groups: &policy.ei_groups,
            person_groups: &policy.person_groups,
            entity_groups: &policy.entity_groups,
        };
        let found = self.py.detach(|| {
            scanner.inner.scan(shared.norm, shared.folded, &shared.context, &settings, shared.classes, true)
        });
        let spans = found.into_iter().filter_map(|f| {
            let recognizer = engine.recognizers.get(f.recognizer)?;
            // `_priority` : clé fausse gardée sur contexte / wrong key kept on context.
            let priority = if f.value.is_none() { recognizer.context_only } else { recognizer.template.priority() };
            Some(Span {
                score: f.score,
                priority,
                value: f.value,
                personal: f.personal,
                reason: f.reason.map(Arc::from),
                ..recognizer.template.span(f.start, f.end)
            })
        });
        let mut state = self.doc.lock();
        state.detected.spans.extend(spans);
        state.set_timing("native", elapsed_ms(started), true);
        Ok(())
    }

    /// Code Python (détecteur sans jumeau, recognizers d'un pack, liste de refus…) : ses zones entrent telles
    /// quelles. Python code (detector without a twin, a pack's recognizers, deny list…): its spans enter as is.
    fn python(&self, call: usize) -> PyResult<()> {
        let context = self.python_context()?;
        let function = self.host.getattr(intern!(self.py, "calls"))?.get_item(call)?;
        let returned = function.call1((context,))?;
        let objects = returned.try_iter()?.collect::<PyResult<Vec<_>>>()?;
        add_python_spans(self.doc, self.py, objects);
        // Objets de `ctx.found` modifiés par ce code ? / `ctx.found` objects changed by this code?
        self.doc.refresh(self.py);
        Ok(())
    }

    /// `DetectionContext` des détecteurs Python, construit une fois par document / built once per document.
    fn python_context(&self) -> PyResult<Bound<'_, PyAny>> {
        let cached = self.doc.lock().context.as_ref().map(|c| c.clone_ref(self.py));
        if let Some(context) = cached {
            return Ok(context.into_bound(self.py));
        }
        let context = self.host.getattr(intern!(self.py, "context"))?.call1((self.document,))?;
        self.doc.lock().context = Some(context.clone().unbind());
        Ok(context)
    }

    /// Zones d'un détecteur natif, filtrées par entité (`_entity_allowed`) / filtered by entity.
    fn push(&self, spans: impl IntoIterator<Item = Span>) {
        let policy = &self.engine.policy;
        self.doc.lock().detected.spans.extend(spans.into_iter().filter(|s| policy.allowed(&s.entity)));
    }

    /// Jamais à cheval sur deux cellules / never across cells.
    fn within_segment(&self, start: usize, end: usize) -> bool {
        self.doc.segment_end(start).is_none_or(|hi| end <= hi)
    }

    fn slot(&self, slot: &Slot) -> PyResult<()> {
        // Texte décomposé : noms, adresses et organisations travaillent sur sa vue NFC (`composed_view`), faite par
        // leur `detect` Python ; tout le reste demeure natif. Decomposed text: names, addresses and organisations
        // run on its NFC view, made by their Python `detect`; everything else stays native.
        if let Some(call) = slot.composed_view().filter(|_| self.shared.decomposed) {
            return self.python(call);
        }
        match slot {
            Slot::Python(call) => self.python(*call),
            Slot::Names(names) => self.names(names),
            Slot::Address(address) => self.address(address),
            Slot::Organizations(organizations) => self.organizations(organizations),
            Slot::BirthDates(birth_dates) => self.birth_dates(birth_dates),
            Slot::Email(email) => self.email(email),
            Slot::Iban(iban) => self.iban(iban),
            Slot::Mrz(mrz) => self.mrz(mrz),
            Slot::Phone(phone) => self.phone(phone),
        }
    }

    /// `FrenchNameDetector.detect` ; texte refusé par le jumeau : le détecteur Python reprend.
    /// Text refused by the twin: the Python detector takes over.
    fn names(&self, slot: &Names) -> PyResult<()> {
        let rows = self.person_rows(&slot.person_groups);
        let detector = slot.twin.get().detector();
        let shared = &self.shared;
        let Some(found) = self.py.detach(|| detector.detect(shared.norm, shared.folded, &rows)) else {
            return self.python(slot.fallback);
        };
        let surname_form = slot.surname_form.bind(self.py);
        let mut spans = Vec::with_capacity(found.len());
        for person in found {
            if !self.within_segment(person.start, person.end) {
                continue;
            }
            // `surname_form` : en Python, sauf pour l'ASCII où `isupper` et `title` sont ceux de l'ASCII.
            // In Python, except for ASCII, where `isupper` and `title` are ASCII's.
            let forms = match person.form {
                Some(form) => match ascii_surname_form(&form) {
                    Some(form) => vec![form.into()],
                    None => vec![surname_form.call1((form,))?.extract::<String>()?.into()],
                },
                None => Vec::new(),
            };
            spans.push(Span {
                value: Some(person.value),
                score: person.score,
                propagate: person.propagate,
                forms,
                ..slot.template.span(person.start, person.end)
            });
        }
        self.push(spans);
        Ok(())
    }

    /// `_person_rows` : cellules marquées « personne » par leur en-tête / cells tagged "person" by their header.
    fn person_rows(&self, groups: &[u32]) -> Vec<(usize, usize)> {
        let (Some(forced), Some(segments)) = (self.doc.forced_groups(), self.doc.segment_bounds()) else {
            return Vec::new();
        };
        if groups.is_empty() || forced.is_empty() {
            return Vec::new();
        }
        forced.iter().zip(segments).filter(|(f, _)| groups.iter().any(|g| f.contains(g))).map(|(_, s)| *s).collect()
    }

    fn address(&self, slot: &Address) -> PyResult<()> {
        let shared = &self.shared;
        let has_trigger = slot.triggers.iter().any(|t| shared.folded.contains(t.as_str()));
        if !shared.has_digit && !has_trigger {
            return Ok(());
        }
        let has_box = shared.has_digit && slot.box_hints.iter().any(|h| shared.folded.contains(h.as_str()));
        let twin = slot.twin.get();
        let found = self
            .py
            .detach(|| twin.spans(shared.norm, shared.folded, shared.has_digit, has_trigger, has_box))
            .map_err(PyValueError::new_err)?;
        self.push(found.into_iter().filter(|&(start, end, ..)| self.within_segment(start, end)).map(
            |(start, end, score, reason)| Span {
                score,
                reason: reason.map(Arc::from),
                ..slot.template.span(start, end)
            },
        ));
        Ok(())
    }

    fn organizations(&self, slot: &Organizations) -> PyResult<()> {
        let twin = slot.twin.get();
        let shared = &self.shared;
        let found =
            self.py.detach(|| twin.candidate_spans(shared.norm, shared.folded)).map_err(PyValueError::new_err)?;
        if found.is_empty() {
            return Ok(());
        }
        let engine = self.engine;
        let facts = Facts {
            names: slot.names.get(),
            table: engine.table.get(),
            preparer: engine.preparer.get(),
            text: &shared.text,
            context: &shared.context,
            company_ids: &engine.policy.company_ids,
            strict: engine.policy.strict,
        };
        let spans = self.py.detach(|| slot.decision.spans(&facts, found));
        self.push(spans);
        Ok(())
    }

    /// `NirBirthDateDetector.detect` : années et mois des NIR validés du passage (`ctx.found`).
    /// Years and months of the pass's validated NIRs.
    fn birth_dates(&self, slot: &BirthDates) -> PyResult<()> {
        let births: Option<HashSet<(String, String)>> = {
            let state = self.doc.lock();
            // Une zone Python illisible : seul le détecteur Python sait la lire / only Python can read it.
            (!state.outside).then(|| {
                let pass = state.detected.spans.get(state.pass_start..).unwrap_or_default();
                pass.iter()
                    .filter(|s| *s.source == *slot.nir_source)
                    .filter_map(|s| s.value.as_deref().filter(|v| !v.is_empty()))
                    .map(|v| (v.chars().skip(1).take(2).collect(), v.chars().skip(3).take(2).collect()))
                    .collect()
            })
        };
        let Some(births) = births else {
            return self.python(slot.fallback);
        };
        if births.is_empty() {
            return Ok(());
        }
        let twin = slot.twin.get();
        let shared = &self.shared;
        let (numeric, written) = self.py.detach(|| twin.dates(shared.norm, shared.folded, &births));
        // Valeur : date ISO (numérique), sinon le texte même (en lettres) / ISO date, else the written text.
        let written = written.into_iter().map(|(start, end)| (start, end, shared.text.slice(start, end).to_owned()));
        let spans = numeric.into_iter().chain(written);
        self.push(spans.map(|(start, end, value)| Span { value: Some(value), ..slot.template.span(start, end) }));
        Ok(())
    }

    /// `EmailDetector.detect` : candidats natifs, validation par `email` (le `str.lower` de l'interpréteur).
    /// Native candidates, validated by `email` (the interpreter's `str.lower`).
    fn email(&self, slot: &Email) -> PyResult<()> {
        let twin = slot.twin.get();
        let shared = &self.shared;
        let found = self.py.detach(|| twin.candidate_spans(shared.norm));
        let validate = slot.validate.bind(self.py);
        let mut spans = Vec::new();
        for (start, end) in found {
            let candidate = shared.text.slice(start, end);
            let value = match slot.ascii.filter(|_| candidate.is_ascii()) {
                Some(native) => native(candidate),
                None => validate.call1((candidate,))?.extract()?,
            };
            if let Some(value) = value {
                spans.push(Span { value: Some(value), ..slot.template.span(start, end) });
            }
        }
        self.push(spans);
        Ok(())
    }

    /// `IbanDetector.detect` : clé juste, ou mise en page imprimée, ou mot-clé proche / right key, layout, keyword.
    fn iban(&self, slot: &Iban) -> PyResult<()> {
        let shared = &self.shared;
        if !shared.has_digit {
            return Ok(());
        }
        let twin = slot.twin.get();
        let found = self.py.detach(|| twin.candidate_spans(shared.norm));
        let near = |start, end| shared.context.near_groups(&slot.contexts, start, end, slot.before, slot.after);
        self.push(found.into_iter().filter_map(|(start, end, value, printed)| match value {
            Some(value) => Some(Span { value: Some(value), ..slot.valid.span(start, end) }),
            None if printed || near(start, end) => Some(slot.lenient.span(start, end)),
            None => None,
        }));
        Ok(())
    }

    fn mrz(&self, slot: &Mrz) -> PyResult<()> {
        let shared = &self.shared;
        if !shared.folded.contains(slot.prefilter.as_str()) {
            return Ok(());
        }
        let bands = self.py.detach(|| mrz_spans(shared.norm));
        self.push(bands.into_iter().map(|(start, end, score)| Span { score, ..slot.template.span(start, end) }));
        Ok(())
    }

    /// `InternationalPhoneDetector.detect` : candidats natifs, validation phonenumbers en Python (mémo de cet
    /// appel seulement). Native candidates, phonenumbers validation in Python (this call's memo only).
    fn phone(&self, slot: &Phone) -> PyResult<()> {
        let shared = &self.shared;
        if !slot.prefilters.iter().any(|p| shared.folded.contains(p.as_str())) {
            return Ok(());
        }
        let table = self.engine.table.get();
        let found = self.py.detach(|| phone::candidates(shared.norm, |c| table.is_word(c)));
        let value = slot.value.bind(self.py);
        let mut seen: HashMap<&str, Option<(String, f64, i64)>> = HashMap::new();
        let mut spans = Vec::new();
        for (start, end) in found {
            let candidate = shared.text.slice(start, end);
            let validated = match seen.get(candidate) {
                Some(known) => known.clone(),
                None => {
                    let validated: Option<(String, f64, i64)> = value.call1((candidate,))?.extract()?;
                    seen.insert(candidate, validated.clone());
                    validated
                }
            };
            if let Some((value, score, priority)) = validated {
                spans.push(Span { value: Some(value), score, priority, ..slot.template.span(start, end) });
            }
        }
        self.push(spans);
        Ok(())
    }

    /// Règles de l'organisation en natif : leurs propres mots-clés, ni en-têtes ni cellules imposés.
    /// Native organisation rules: their own keywords, no forced headers nor table cells.
    fn custom(&self, custom: &CustomScan) -> PyResult<()> {
        let scanner = custom.scanner.get();
        let shared = &self.shared;
        let classes = scanner.tables.get().classes(self.py, &[shared.norm, shared.folded])?;
        let hits = self.py.detach(|| scanner.inner.keywords.scan(shared.folded, classes));
        let context =
            Context { hits: &hits, segments: self.doc.segment_bounds(), forced: None, zones: &[], zone_groups: &[] };
        let active = vec![true; custom.rules.len()];
        let settings = Settings {
            active: &active,
            strict: self.engine.policy.strict,
            company_mode: "keep",
            facility_mask: false,
            ei_groups: &[],
            person_groups: &[],
            entity_groups: &[],
        };
        let found =
            self.py.detach(|| scanner.inner.scan(shared.norm, shared.folded, &context, &settings, classes, true));
        let spans = found.into_iter().filter_map(|f| {
            let rule = custom.rules.get(f.recognizer)?;
            Some(Span { score: f.score, value: f.value, personal: true, ..rule.span(f.start, f.end) })
        });
        self.doc.lock().detected.spans.extend(spans);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::ascii_surname_form;

    #[test]
    fn ascii_surname_forms_follow_str_title() {
        // Valeurs de Python : `form.title() if form.isupper() else form` / Python's values.
        for (form, expected) in [
            ("DUPONT", "Dupont"),
            ("LE GOFF", "Le Goff"),
            ("O'NEIL-SMITH", "O'Neil-Smith"),
            ("D2X", "D2X"),
            ("MC2B", "Mc2B"),
            ("Dupont", "Dupont"),
            ("123", "123"),
        ] {
            assert_eq!(ascii_surname_form(form).as_deref(), Some(expected), "{form}");
        }
        assert_eq!(ascii_surname_form("ÉLODIE"), None);
    }
}
