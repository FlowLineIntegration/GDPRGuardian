//! Plan du moteur : ce que l'`Anonymizer` fixe à sa construction (packs, détecteurs, réglages), lu une fois.
//!
//! Engine plan: what the `Anonymizer` fixes at construction (packs, detectors, settings), read once. Toutes les
//! données viennent de Python : listes de mots, groupes de contexte, constantes et prototypes de zones construits
//! par les détecteurs Python eux-mêmes (une seule source de vérité). All data comes from Python: word lists,
//! context groups, constants and span prototypes built by the Python detectors themselves.

use std::collections::{HashMap, HashSet};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyType};

use crate::detectors::{
    CodeData, CodeDetector, PyAddressDetector, PyBirthDateDetector, PyEmailDetector, PyIbanDetector,
    PyOrganizationDetector,
};
use crate::finalize::{read_object, Span};
use crate::names::py::PyNameDetector;
use crate::validators::{self, ValidatorFn};
use crate::PyScanner;

use super::organizations::Decision;

/// Modèle des zones d'un détecteur natif, lu sur un prototype `types.Span` fait par le détecteur Python :
/// entité, libellé, source, score, priorité, politique. Template of a native detector's spans, read from a
/// prototype made by the Python detector: entity, label, source, score, priority, policy.
#[derive(Clone)]
pub(crate) struct Template(Span);

impl Template {
    fn new(prototype: &Bound<'_, PyAny>, span_type: &Bound<'_, PyType>) -> PyResult<Self> {
        // Une zone du modèle est faite par Rust : aucun objet Python d'origine / made by Rust: no Python object.
        read_object(prototype, span_type, 0, 0)
            .map(|span| Self(Span { origin: None, ..span }))
            .ok_or_else(|| PyValueError::new_err("prototype de zone invalide / invalid span prototype"))
    }

    /// Zone de ce modèle en [start, end) / a span of this template.
    pub(crate) fn span(&self, start: usize, end: usize) -> Span {
        Span { start, end, ..self.0.clone() }
    }

    pub(crate) fn priority(&self) -> i64 {
        self.0.priority
    }
}

/// Recognizer de l'analyseur natif : modèle, priorité « contexte seul » d'une clé fausse, pack.
/// Native-scanner recognizer: template, "context only" priority of a wrong key, pack.
pub(crate) struct Recognizer {
    pub template: Template,
    /// `_priority(rec, None)` : priorité d'une clé fausse gardée sur contexte / priority of a kept wrong key.
    pub context_only: i64,
    pub pack: usize,
}

pub(crate) struct Names {
    pub twin: Py<PyNameDetector>,
    pub template: Template,
    /// Groupes « personne » des en-têtes de colonne (`_person_groups`) / person column-header groups.
    pub person_groups: Vec<u32>,
    /// `fr_names.surname_form` : `str.title()` reste en Python / `str.title()` stays in Python.
    pub surname_form: Py<PyAny>,
    /// Détecteur Python, si le jumeau refuse le texte / the Python detector, when the twin refuses the text.
    pub fallback: usize,
}

pub(crate) struct Address {
    pub twin: Py<PyAddressDetector>,
    pub template: Template,
    /// `_TRIGGERS`, `_BOX_HINTS` : préfiltres sur le texte replié / prefilters on the folded text.
    pub triggers: Vec<String>,
    pub box_hints: Vec<String>,
    /// Détecteur Python, pour un texte décomposé / the Python detector, for a decomposed text.
    pub fallback: usize,
}

pub(crate) struct Organizations {
    pub twin: Py<PyOrganizationDetector>,
    /// Lexique des noms (`Lexicon.code`) / names lexicon.
    pub names: Py<PyNameDetector>,
    pub decision: Decision,
    /// Détecteur Python, pour un texte décomposé / the Python detector, for a decomposed text.
    pub fallback: usize,
}

pub(crate) struct BirthDates {
    pub twin: Py<PyBirthDateDetector>,
    pub template: Template,
    /// `_nir_source` : source des NIR validés du passage / source of the pass's validated NIRs.
    pub nir_source: String,
    pub fallback: usize,
}

pub(crate) struct Email {
    pub twin: Py<PyEmailDetector>,
    pub template: Template,
    /// `validators.intl.email` : `str.lower` de l'interpréteur / the interpreter's `str.lower`.
    pub validate: Py<PyAny>,
    /// Le même validateur en natif, exact pour un candidat ASCII (minuscules ASCII) / the same validator,
    /// native, exact for an ASCII candidate (ASCII lowercase).
    pub ascii: Option<ValidatorFn>,
}

pub(crate) struct Iban {
    pub twin: Py<PyIbanDetector>,
    pub valid: Template,
    pub lenient: Template,
    pub contexts: Vec<u32>,
    pub before: usize,
    pub after: usize,
}

pub(crate) struct Mrz {
    pub template: Template,
    pub prefilter: String,
}

pub(crate) struct Phone {
    pub template: Template,
    pub prefilters: Vec<String>,
    /// `InternationalPhoneDetector.value` : (valeur, score, priorité) ou `None` (phonenumbers).
    pub value: Py<PyAny>,
}

/// `PersonalSiteDetector` (`URL_PERSONAL_NAME`) : jumeau natif, repli des mots non ASCII par `_fold_word`.
/// Native twin; non-ASCII words folded by `_fold_word`.
pub(crate) struct PersonalSite {
    pub template: Template,
    pub prefilters: Vec<String>,
    pub fold: Py<PyAny>,
    /// Détecteur Python, pour un texte hors du domaine du jumeau / the Python detector, outside the twin's domain.
    pub fallback: usize,
}

/// `IdentifierCodeDetector` (`ID_CODE`, `ID_LONG_NUMBER`, `SECRET_COOKIE`) : jumeau natif et modèles des trois
/// règles / native twin and the three rules' templates.
pub(crate) struct Codes {
    pub detector: CodeDetector,
    pub code: Template,
    pub long_number: Template,
    pub cookie: Template,
}

/// Détecteur d'un pack : jumeau natif, ou appel Python (indice dans les appels de l'hôte).
/// A pack's detector: native twin, or a Python call (index into the host's calls).
pub(crate) enum Slot {
    Python(usize),
    Names(Names),
    Address(Address),
    Organizations(Box<Organizations>),
    BirthDates(BirthDates),
    Email(Email),
    Iban(Iban),
    Mrz(Mrz),
    Phone(Phone),
    PersonalSite(PersonalSite),
    Codes(Box<Codes>),
}

impl Slot {
    /// Appel Python d'un détecteur à vue NFC (`composed_view` : noms, adresses, organisations), pour un texte
    /// décomposé. Python call of an NFC-view detector (names, addresses, organisations), for a decomposed text.
    pub(crate) fn composed_view(&self) -> Option<usize> {
        match self {
            Slot::Names(names) => Some(names.fallback),
            Slot::Address(address) => Some(address.fallback),
            Slot::Organizations(organizations) => Some(organizations.fallback),
            _ => None,
        }
    }
}

pub(crate) struct Pack {
    pub id: String,
    pub country: Option<String>,
    pub always_on: bool,
    /// Recognizers laissés à Python (appel), ou `None` / recognizers left to Python (call), or `None`.
    pub recognizers: Option<usize>,
    pub slots: Vec<Slot>,
    /// « pack:ID » des mesures / timing key.
    pub timing: String,
}

/// Mode de choix des pays / country mode.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Mode {
    /// Pays explicites ou « all » : un passage sur les packs actifs / one pass over the active packs.
    Fixed,
    /// « auto » : packs toujours actifs, choix des pays par Python, puis packs des pays / two passes.
    Auto,
}

/// Règles de l'organisation en natif : analyseur et (entité, libellé, source, priorité) de chaque règle.
/// Native custom rules: scanner and (entity, label, source, priority) of each rule.
pub(crate) struct CustomScan {
    pub scanner: Py<PyScanner>,
    pub rules: Vec<Template>,
}

pub(crate) enum Custom {
    None,
    Python(usize),
    Native(CustomScan),
}

/// Réglages de détection de l'`Anonymizer` / the `Anonymizer`'s detection settings.
pub(crate) struct Policy {
    pub strict: bool,
    pub company_ids: String,
    pub facility_mask: bool,
    pub ei_groups: Vec<u32>,
    /// `Anonymizer._person_groups`, `Anonymizer._entity_groups`.
    pub person_groups: Vec<u32>,
    pub entity_groups: Vec<u32>,
    pub entities: Option<HashSet<String>>,
    pub excluded: HashSet<String>,
}

impl Policy {
    /// `Anonymizer._entity_allowed`.
    pub(crate) fn allowed(&self, entity: &str) -> bool {
        !self.excluded.contains(entity) && self.entities.as_ref().is_none_or(|e| e.contains(entity))
    }
}

/// Lecture des spécifications Python / reading the Python specifications.
pub(crate) struct Reader<'a, 'py> {
    pub span_type: &'a Bound<'py, PyType>,
    pub group_ids: &'a HashMap<String, u32>,
}

fn field<'py>(spec: &Bound<'py, PyDict>, key: &str) -> PyResult<Bound<'py, PyAny>> {
    spec.get_item(key)?.ok_or_else(|| PyValueError::new_err(format!("champ manquant / missing field: {key}")))
}

impl<'py> Reader<'_, 'py> {
    pub(crate) fn template(&self, spec: &Bound<'py, PyDict>, key: &str) -> PyResult<Template> {
        Template::new(&field(spec, key)?, self.span_type)
    }

    /// Identifiants des groupes connus de l'index ; un groupe inconnu ne peut rien trouver.
    /// Ids of the groups the index knows; an unknown group can never match anything.
    pub(crate) fn groups(&self, names: &[String]) -> Vec<u32> {
        names.iter().filter_map(|name| self.group_ids.get(name).copied()).collect()
    }

    pub(crate) fn recognizer(&self, entry: &Bound<'py, PyAny>) -> PyResult<Recognizer> {
        let (prototype, context_only, pack): (Bound<'py, PyAny>, i64, usize) = entry.extract()?;
        Ok(Recognizer { template: Template::new(&prototype, self.span_type)?, context_only, pack })
    }

    pub(crate) fn slot(&self, spec: &Bound<'py, PyDict>) -> PyResult<Slot> {
        let kind: String = field(spec, "kind")?.extract()?;
        let words = |key: &str| -> PyResult<Vec<String>> { field(spec, key)?.extract() };
        let groups = |key: &str| -> PyResult<Vec<u32>> { Ok(self.groups(&words(key)?)) };
        Ok(match kind.as_str() {
            "python" => Slot::Python(field(spec, "call")?.extract()?),
            "names" => Slot::Names(Names {
                twin: field(spec, "twin")?.extract()?,
                template: self.template(spec, "prototype")?,
                person_groups: groups("person_groups")?,
                surname_form: field(spec, "surname_form")?.unbind(),
                fallback: field(spec, "fallback")?.extract()?,
            }),
            "address" => Slot::Address(Address {
                twin: field(spec, "twin")?.extract()?,
                template: self.template(spec, "prototype")?,
                triggers: words("triggers")?,
                box_hints: words("box_hints")?,
                fallback: field(spec, "fallback")?.extract()?,
            }),
            "organizations" => {
                let set = |key: &str| -> PyResult<HashSet<String>> { field(spec, key)?.extract() };
                let (surname_min, given_min, frequent) = field(spec, "thresholds")?.extract()?;
                let (amb_none, amb_word, amb_entity) = field(spec, "ambiguities")?.extract()?;
                Slot::Organizations(Box::new(Organizations {
                    twin: field(spec, "twin")?.extract()?,
                    names: field(spec, "names")?.extract()?,
                    decision: Decision {
                        keywords: set("keywords")?,
                        function: set("function")?,
                        particles: set("particles")?,
                        family: set("family")?,
                        ei_groups: groups("ei_groups")?,
                        surname_min,
                        given_min,
                        frequent,
                        amb_none,
                        amb_word,
                        amb_entity,
                        person: self.template(spec, "person")?,
                        masked: self.template(spec, "masked")?,
                        kept: self.template(spec, "kept")?,
                    },
                    fallback: field(spec, "fallback")?.extract()?,
                }))
            }
            "birth_dates" => Slot::BirthDates(BirthDates {
                twin: field(spec, "twin")?.extract()?,
                template: self.template(spec, "prototype")?,
                nir_source: field(spec, "nir_source")?.extract()?,
                fallback: field(spec, "fallback")?.extract()?,
            }),
            "email" => Slot::Email(Email {
                twin: field(spec, "twin")?.extract()?,
                template: self.template(spec, "prototype")?,
                validate: field(spec, "validate")?.unbind(),
                ascii: validators::lookup("intl.email"),
            }),
            "iban" => {
                let (before, after) = field(spec, "window")?.extract()?;
                Slot::Iban(Iban {
                    twin: field(spec, "twin")?.extract()?,
                    valid: self.template(spec, "valid")?,
                    lenient: self.template(spec, "lenient")?,
                    contexts: groups("contexts")?,
                    before,
                    after,
                })
            }
            "mrz" => Slot::Mrz(Mrz {
                template: self.template(spec, "prototype")?,
                prefilter: field(spec, "prefilter")?.extract()?,
            }),
            "phone" => Slot::Phone(Phone {
                template: self.template(spec, "prototype")?,
                prefilters: words("prefilters")?,
                value: field(spec, "value")?.unbind(),
            }),
            "personal_site" => Slot::PersonalSite(PersonalSite {
                template: self.template(spec, "prototype")?,
                prefilters: words("prefilters")?,
                fold: field(spec, "fold")?.unbind(),
                fallback: field(spec, "fallback")?.extract()?,
            }),
            "codes" => Slot::Codes(Box::new(Codes {
                detector: CodeDetector::new(CodeData {
                    exclusions: words("exclusions")?,
                    short_list: words("short_list")?,
                    months: words("months")?,
                    bic_countries: words("bic_countries")?,
                    attributes: words("attributes")?,
                })
                .map_err(PyValueError::new_err)?,
                code: self.template(spec, "code")?,
                long_number: self.template(spec, "long_number")?,
                cookie: self.template(spec, "cookie")?,
            })),
            other => return Err(PyValueError::new_err(format!("détecteur inconnu / unknown detector: {other}"))),
        })
    }

    pub(crate) fn pack(&self, spec: &Bound<'py, PyDict>) -> PyResult<Pack> {
        let id: String = field(spec, "id")?.extract()?;
        let slots = field(spec, "slots")?
            .try_iter()?
            .map(|slot| self.slot(slot?.cast::<PyDict>()?))
            .collect::<PyResult<Vec<Slot>>>()?;
        Ok(Pack {
            timing: format!("pack:{id}"),
            id,
            country: field(spec, "country")?.extract()?,
            always_on: field(spec, "always_on")?.extract()?,
            recognizers: field(spec, "recognizers")?.extract()?,
            slots,
        })
    }

    pub(crate) fn custom(&self, spec: Option<&Bound<'py, PyDict>>) -> PyResult<Custom> {
        let Some(spec) = spec else {
            return Ok(Custom::None);
        };
        if let Some(call) = spec.get_item("call")? {
            return Ok(Custom::Python(call.extract()?));
        }
        let rules = field(spec, "rules")?
            .try_iter()?
            .map(|rule| Template::new(&rule?, self.span_type))
            .collect::<PyResult<Vec<Template>>>()?;
        Ok(Custom::Native(CustomScan { scanner: field(spec, "scanner")?.extract()?, rules }))
    }
}
