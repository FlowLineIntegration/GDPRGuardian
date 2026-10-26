//! Table Unicode unique du noyau : classes, casse et repliement selon CET interpréteur Python.
//!
//! The core's single Unicode table: classes, case and folding as THIS Python interpreter sees them.
//! Python la construit une fois par processus (`gdprguardian._native.unicode_tables`) avec ses propres prédicats
//! (`str.isalnum()`, `\w` de `re`…), en code C ; Rust ne recalcule jamais une propriété Unicode, dont la version
//! diffère. Le plan de base est donné à la construction ; chaque autre plan est demandé à Python la première
//! fois qu'un de ses caractères paraît, une seule fois par processus, jamais à chaque appel. Les tables ne
//! contiennent que des propriétés Unicode, jamais de contenu. Python builds it once per process with its own
//! predicates, in C code; Rust never recomputes a Unicode property, whose version differs. The Basic
//! Multilingual Plane is given at construction; any other plane is requested from Python the first time one of
//! its characters shows up, once per process, never per call. The tables hold Unicode properties only.

use std::collections::{HashMap, HashSet};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, OnceLock};

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex_syntax::hir::{ClassUnicode, ClassUnicodeRange};

// Bits, dans l'ordre de `gdprguardian._text` / bits, in the order of `gdprguardian._text`.
/// `\w` de `re` : `str.isalnum()` ou « _ » / `re`'s `\w`.
pub const WORD: u16 = 1 << 0;
/// `str.isalnum()`, soit `[^\W_]` / i.e. `[^\W_]`.
pub const ALNUM: u16 = 1 << 1;
/// `[^\W\d_]` : lettre au sens de `re`, nombres non décimaux compris (« ² ») / a letter as `re` sees it.
pub const LETTER: u16 = 1 << 2;
/// `\d` de `re`, `str.isdecimal()`.
pub const DECIMAL: u16 = 1 << 3;
/// `str.isdigit()`.
pub const DIGIT: u16 = 1 << 4;
/// `\s` de `re`, `str.isspace()`.
pub const SPACE: u16 = 1 << 5;
/// `str.isalpha()`.
pub const ALPHA: u16 = 1 << 6;
/// `str.isupper()` d'un caractère (propriété Uppercase) / of one character (Uppercase property).
pub const UPPER: u16 = 1 << 7;
/// `str.islower()` d'un caractère (propriété Lowercase) / of one character (Lowercase property).
pub const LOWER: u16 = 1 << 8;
/// Casse de titre, catégorie Lt (`Py_UNICODE_ISTITLE`) / titlecase, category Lt.
pub const TITLE: u16 = 1 << 9;
/// `("A" + c).isupper()` : ni minuscule ni casse de titre / neither lowercase nor titlecase.
pub const UPPER_SAFE: u16 = 1 << 10;
/// Classe `UPPER` des heuristiques (majuscules latines, grecques, cyrilliques) / the heuristics' capitals.
pub const CAPITAL: u16 = 1 << 11;
/// Invisible retiré à la normalisation (`_text.INVISIBLE_RE`) / invisible character removed by normalisation.
pub const INVISIBLE: u16 = 1 << 12;
/// `str.upper()` change le caractère / `str.upper()` changes the character.
pub const MAPS_UPPER: u16 = 1 << 13;
/// `str.lower()` change le caractère / `str.lower()` changes the character.
pub const MAPS_LOWER: u16 = 1 << 14;

/// Bits fournis par Python ; les autres se déduisent / bits Python provides; the others are derived.
const GIVEN: u16 = WORD | LETTER | DECIMAL | DIGIT | SPACE | ALPHA | UPPER | LOWER | TITLE | CAPITAL | INVISIBLE;
/// Points de code d'un plan / code points in one plane.
const PLANE: usize = 0x10000;
/// Plans Unicode (0 à 16) / Unicode planes (0 to 16).
const PLANES: usize = 17;

/// Correspondances de casse complètes d'un plan, triées (16 bits bas du point) / a plane's full case mappings.
type CaseMap = Box<[(u16, Box<str>)]>;

/// Données d'un plan telles que Python les rend (`_text.plane_classes`) : intervalles [début, fin) de chaque bit
/// dans le plan, puis `str.upper()` et `str.lower()` des points qu'ils changent. A plane's data as Python returns
/// it: [start, end) runs of each bit within the plane, then the characters `str.upper()`/`str.lower()` change.
pub type PlaneData = (Vec<(u16, Vec<(u32, u32)>)>, Vec<(u32, String)>, Vec<(u32, String)>);

/// Un plan : drapeaux de chaque point et correspondances de casse / a plane: each point's flags, case mappings.
struct Plane {
    flags: Box<[u16]>,
    upper: CaseMap,
    lower: CaseMap,
}

impl Plane {
    /// Plan sans aucune propriété / a plane without any property.
    fn empty() -> Self {
        // Sans minuscule ni titre, chaque caractère garde un mot en capitales / no lower nor title character.
        Self { flags: vec![UPPER_SAFE; PLANE].into_boxed_slice(), upper: Box::new([]), lower: Box::new([]) }
    }

    fn new(plane: usize, (runs, upper, lower): PlaneData) -> Result<Self, String> {
        let mut flags = vec![0u16; PLANE];
        for (bit, spans) in runs {
            if bit & !GIVEN != 0 {
                return Err(format!("bit inconnu / unknown bit {bit}"));
            }
            for (start, end) in spans {
                let slots = flags
                    .get_mut(start as usize..end as usize)
                    .ok_or_else(|| format!("intervalle invalide / invalid run {start}..{end}"))?;
                slots.iter_mut().for_each(|slot| *slot |= bit);
            }
        }
        let mut map = |pairs: Vec<(u32, String)>, bit: u16| -> Result<CaseMap, String> {
            let mut map = Vec::with_capacity(pairs.len());
            for (low, mapped) in pairs {
                let slot = flags.get_mut(low as usize).ok_or("correspondance hors du plan / mapping beyond plane")?;
                *slot |= bit;
                map.push((low as u16, mapped.into_boxed_str()));
            }
            map.sort_unstable_by_key(|entry| entry.0);
            Ok(map.into_boxed_slice())
        };
        let upper = map(upper, MAPS_UPPER)?;
        let lower = map(lower, MAPS_LOWER)?;
        for (low, slot) in flags.iter_mut().enumerate() {
            // `str.isalnum()` = `\w` sauf « _ » ; `("A" + c).isupper()` = ni minuscule ni titre.
            // `str.isalnum()` = `\w` but '_'; `("A" + c).isupper()` = neither lower nor title.
            if *slot & WORD != 0 && (plane != 0 || low != usize::from(b'_')) {
                *slot |= ALNUM;
            }
            if *slot & (LOWER | TITLE) == 0 {
                *slot |= UPPER_SAFE;
            }
        }
        Ok(Self { flags: flags.into_boxed_slice(), upper, lower })
    }

    #[inline]
    fn mapping(map: &CaseMap, low: u16) -> Option<&str> {
        map.binary_search_by_key(&low, |entry| entry.0).ok().map(|i| &*map[i].1)
    }
}

/// `\w`, `\d`, `\s` de `re` sur tous les plans, pour le compilateur de motifs / for the pattern compiler.
pub struct PerlSets {
    pub word: ClassUnicode,
    pub digit: ClassUnicode,
    pub space: ClassUnicode,
}

/// Données de `re.IGNORECASE` reçues de Python (`_text.ignorecase_data`) / received from Python.
#[derive(Default)]
pub struct IgnoreCaseData {
    /// (caractère, minuscule simple de `_sre`) des candidats / (character, `_sre` simple lowercase).
    pub lower: Vec<(u32, u32)>,
    /// Caractères à casse pour `_sre` (`unicode_iscased`) / cased characters for `_sre`.
    pub cased: Vec<u32>,
    /// Cas supplémentaires de `re` (« i » et « ı », « s » et « ſ »…) / `re`'s extra cases.
    pub fixes: Vec<(u32, Vec<u32>)>,
}

/// `re.IGNORECASE`, prêt à l'emploi / ready to use.
#[derive(Default)]
struct IgnoreCase {
    lower: HashMap<char, char>,
    cased: HashSet<char>,
    /// Minuscule simple -> caractères qui y mènent / simple lowercase -> characters leading to it.
    by_lower: HashMap<char, Vec<char>>,
    fixes: HashMap<char, Vec<char>>,
    /// Caractères dont la correspondance insensible à la casse peut différer de la sensible, triés.
    /// Characters whose case-insensitive match may differ from the case-sensitive one, sorted.
    candidates: Vec<char>,
}

fn code(cp: u32) -> Result<char, String> {
    char::from_u32(cp).ok_or_else(|| format!("point de code invalide / invalid code point {cp}"))
}

impl IgnoreCase {
    fn new(data: IgnoreCaseData) -> Result<Self, String> {
        let mut case = Self::default();
        for (cp, lower) in data.lower {
            let (c, lower) = (code(cp)?, code(lower)?);
            case.lower.insert(c, lower);
            case.by_lower.entry(lower).or_default().push(c);
            case.candidates.push(c);
        }
        case.candidates.sort_unstable();
        case.candidates.dedup();
        case.cased = data.cased.into_iter().map(code).collect::<Result<_, _>>()?;
        for (cp, others) in data.fixes {
            case.fixes.insert(code(cp)?, others.into_iter().map(code).collect::<Result<_, _>>()?);
        }
        Ok(case)
    }
}

/// La table partagée / the shared table.
pub struct Unicode {
    /// Plan de base, lu sans détour / Basic Multilingual Plane, read directly.
    base: Plane,
    /// Plans 1 à 16, chargés au premier besoin / planes 1 to 16, loaded when first needed.
    astral: [OnceLock<Plane>; PLANES - 1],
    /// `plane_classes(plane)` de Python ; None : plans hors BMP vides (tests Rust) / None: empty planes.
    loader: Option<Py<PyAny>>,
    empty: Plane,
    /// `_text.fold` (`FOLD_TABLE`), dense jusqu'à sa plus grande clé du BMP / dense up to its largest BMP key.
    fold: Box<[char]>,
    ignorecase: IgnoreCase,
    /// Plans hors BMP où `\w`, `\d`, `\s` peuvent avoir des membres / astral planes that may hold them.
    perl_planes: Vec<usize>,
    perl: OnceLock<PerlSets>,
    /// Plans lus sans préparation et restés vides (erreur de Python, interpréteur arrêté) ; jamais remis à zéro :
    /// un appel compare sa valeur avant et après son calcul. Planes read without preparation that stayed empty;
    /// never reset: a call compares its value before and after its work.
    missed: AtomicUsize,
}

/// Plans hors BMP dont des caractères paraissent dans ces textes (un bit par plan).
/// Astral planes with characters in these texts (one bit per plane).
pub fn planes_in(texts: &[&str]) -> u32 {
    let mut needed = 0u32;
    // Octet de tête d'une séquence de 4 octets : seul indice d'un caractère hors BMP ; son plan se lit dans les
    // deux premiers octets. Lead byte of a 4-byte sequence: the only sign of a character beyond the BMP; its
    // plane is in the first two bytes.
    for text in texts.iter().filter(|text| text.bytes().any(|b| b >= 0xF0)) {
        let bytes = text.as_bytes();
        for (i, &b) in bytes.iter().enumerate().filter(|&(_, &b)| b >= 0xF0) {
            let second = bytes.get(i + 1).copied().unwrap_or(0);
            needed |= 1 << ((u32::from(b & 0x07) << 2) | u32::from((second >> 4) & 0x03));
        }
    }
    needed
}

/// Intervalle de points de code en caractères, demi-codets exclus / code point range as chars, no surrogates.
fn push_range(ranges: &mut Vec<ClassUnicodeRange>, first: u32, last: u32) {
    for (lo, hi) in [(first, last.min(0xD7FF)), (first.max(0xE000), last)] {
        if let (Some(lo), Some(hi)) = (char::from_u32(lo), char::from_u32(hi)) {
            if lo <= hi {
                ranges.push(ClassUnicodeRange::new(lo, hi));
            }
        }
    }
}

impl Unicode {
    /// Table complète : plan de base, chargeur des autres plans, repliement, données de `re.IGNORECASE`.
    /// Full table: base plane, loader of the other planes, folding, `re.IGNORECASE` data.
    pub fn new(
        bmp: PlaneData,
        loader: Option<Py<PyAny>>,
        fold: &[(u32, u32)],
        ignorecase: IgnoreCaseData,
        perl_planes: Vec<usize>,
    ) -> Result<Self, String> {
        if perl_planes.iter().any(|&p| p == 0 || p >= PLANES) {
            return Err("plan invalide / invalid plane".into());
        }
        // Comme `_dense_bmp` : seules les clés du BMP comptent / as `_dense_bmp`: only BMP keys count.
        let keys = fold.iter().filter(|(cp, _)| (*cp as usize) < PLANE);
        let size = keys.clone().map(|(cp, _)| *cp + 1).max().unwrap_or(0);
        let mut dense: Vec<char> = (0..size).map(|cp| char::from_u32(cp).unwrap_or('\u{fffd}')).collect();
        for &(cp, target) in keys {
            if let Some(slot) = dense.get_mut(cp as usize) {
                *slot = code(target)?;
            }
        }
        Ok(Self {
            base: Plane::new(0, bmp)?,
            astral: Default::default(),
            loader,
            empty: Plane::empty(),
            fold: dense.into_boxed_slice(),
            ignorecase: IgnoreCase::new(ignorecase)?,
            perl_planes,
            perl: OnceLock::new(),
            missed: AtomicUsize::new(0),
        })
    }

    /// Plan d'un point de code ; un plan absent est demandé à Python, une fois / a missing plane is requested once.
    #[inline]
    fn plane(&self, plane: usize) -> &Plane {
        if plane == 0 {
            return &self.base;
        }
        match self.astral.get(plane.wrapping_sub(1)) {
            Some(slot) => slot.get().unwrap_or_else(|| self.load_anywhere(plane)),
            None => &self.empty,
        }
    }

    /// Filet de sécurité : chaque point d'entrée prépare les plans de ses textes, GIL tenu, avant de le rendre
    /// (`prepare`, `without_gil`) ; un plan absent n'arrive donc ici que par oubli. Le GIL est alors repris le
    /// temps du calcul, sans attente bloquante (deux fils peuvent calculer le même plan, le premier installé
    /// reste). Si Python échoue (mémoire épuisée, interruption, interpréteur arrêté), le plan reste vide pour ce
    /// calcul et l'échec est compté (`missed`) : l'appel en cours échoue au lieu de rendre un résultat approché.
    /// Safety net: every entry point prepares its texts' planes, GIL held, before releasing it; a missing plane
    /// only gets here by mistake. The GIL is then taken for the computation, without blocking. If Python fails
    /// (out of memory, interrupt, interpreter shut down), the plane stays empty for this computation and the
    /// failure is counted: the current call fails instead of returning an approximate result.
    #[cold]
    fn load_anywhere(&self, plane: usize) -> &Plane {
        // Table de test sans chargeur : plans hors BMP vides par construction / test table: empty by design.
        let Some(loader) = &self.loader else {
            return &self.empty;
        };
        match Python::try_attach(|py| Self::load(loader, py, plane)) {
            Some(Ok(built)) => self.install(plane, built),
            Some(Err(_)) | None => {
                self.missed.fetch_add(1, Ordering::Relaxed);
                &self.empty
            }
        }
    }

    /// Plans manqués jusqu'ici (`load_anywhere`) / planes missed so far.
    pub fn missed(&self) -> usize {
        self.missed.load(Ordering::Relaxed)
    }

    /// Erreur si un plan a manqué depuis `before` (`missed()` relevé avant le calcul) : jamais de résultat
    /// approché. Error if a plane was missed since `before`: never an approximate result.
    pub fn unchanged(&self, before: usize) -> PyResult<()> {
        if self.missed() == before {
            return Ok(());
        }
        Err(PyRuntimeError::new_err(
            "plan Unicode non chargé (erreur de Python) / Unicode plane not loaded (Python error)",
        ))
    }

    /// `Python::detach` sur des textes déjà préparés, puis erreur si un plan a manqué pendant le calcul.
    /// `Python::detach` over already prepared texts, then an error if a plane was missed during the work.
    pub fn detach<T: Send>(&self, py: Python<'_>, work: impl FnOnce() -> T + Send) -> PyResult<T> {
        let before = self.missed();
        let out = py.detach(work);
        self.unchanged(before)?;
        Ok(out)
    }

    /// Calcul sans GIL sur ces textes : leurs plans sont chargés avant, GIL tenu (une erreur de Python remonte),
    /// et un plan manqué pendant le calcul le fait échouer. GIL-free work over these texts: their planes are
    /// loaded first, GIL held (a Python error propagates), and a plane missed during the work makes it fail.
    pub fn without_gil<T: Send>(&self, py: Python<'_>, texts: &[&str], work: impl FnOnce() -> T + Send) -> PyResult<T> {
        self.prepare(py, texts)?;
        self.detach(py, work)
    }

    fn install(&self, plane: usize, built: Plane) -> &Plane {
        let Some(slot) = self.astral.get(plane.wrapping_sub(1)) else {
            return &self.empty;
        };
        let _ = slot.set(built); // déjà installé par un autre fil : gardé / already installed by another thread
        slot.get().unwrap_or(&self.empty)
    }

    fn load(loader: &Py<PyAny>, py: Python<'_>, plane: usize) -> PyResult<Plane> {
        let data: PlaneData = loader.bind(py).call1((plane,))?.extract()?;
        Plane::new(plane, data).map_err(PyValueError::new_err)
    }

    /// Charge, GIL tenu, les plans des caractères de ces textes ; ensuite, de simples lectures de table.
    /// Loads, GIL held, the planes of these texts' characters; afterwards, plain table reads.
    pub fn prepare(&self, py: Python<'_>, texts: &[&str]) -> PyResult<()> {
        self.prepare_planes(py, planes_in(texts))
    }

    fn prepare_planes(&self, py: Python<'_>, mask: u32) -> PyResult<()> {
        let Some(loader) = &self.loader else {
            return Ok(());
        };
        for plane in 1..PLANES {
            if (mask >> plane) & 1 == 1 && self.astral[plane - 1].get().is_none() {
                let built = Self::load(loader, py, plane)?;
                self.install(plane, built);
            }
        }
        Ok(())
    }

    /// Plans chargés (tests de paresse) / loaded planes (laziness tests).
    pub fn loaded_planes(&self) -> Vec<usize> {
        std::iter::once(0).chain((1..PLANES).filter(|&p| self.astral[p - 1].get().is_some())).collect()
    }

    #[inline]
    pub fn flags(&self, c: char) -> u16 {
        let cp = c as usize;
        match self.base.flags.get(cp) {
            Some(&flags) => flags,
            None => self.plane(cp >> 16).flags.get(cp & 0xFFFF).copied().unwrap_or(0),
        }
    }

    #[inline]
    pub fn is(&self, c: char, bits: u16) -> bool {
        self.flags(c) & bits != 0
    }

    /// `\w`.
    #[inline]
    pub fn is_word(&self, c: char) -> bool {
        self.is(c, WORD)
    }

    /// `str.isalnum()`.
    #[inline]
    pub fn is_alnum(&self, c: char) -> bool {
        self.is(c, ALNUM)
    }

    /// `[^\W\d_]` : lettre, ou nombre non décimal (« ² ») / letter, or non-decimal number.
    #[inline]
    pub fn is_letter(&self, c: char) -> bool {
        self.is(c, LETTER)
    }

    /// `\s`, `str.isspace()`.
    #[inline]
    pub fn is_space(&self, c: char) -> bool {
        self.is(c, SPACE)
    }

    /// `str.isupper()` d'un caractère / of one character.
    #[inline]
    pub fn is_upper(&self, c: char) -> bool {
        self.is(c, UPPER)
    }

    /// `str.islower()` d'un caractère / of one character.
    #[inline]
    pub fn is_lower(&self, c: char) -> bool {
        self.is(c, LOWER)
    }

    /// `str.isdigit()`.
    #[inline]
    pub fn is_digit(&self, c: char) -> bool {
        self.is(c, DIGIT)
    }

    /// Classe `UPPER` des heuristiques / the heuristics' capital class.
    #[inline]
    pub fn is_capital(&self, c: char) -> bool {
        self.is(c, CAPITAL)
    }

    /// `str.upper()` d'un caractère, s'il le change / of one character, when it changes it.
    #[inline]
    pub fn upper(&self, c: char) -> Option<&str> {
        if self.flags(c) & MAPS_UPPER == 0 {
            return None;
        }
        Plane::mapping(&self.plane(c as usize >> 16).upper, c as u16)
    }

    /// `str.lower()` d'un caractère, s'il le change (sans sigma final) / when it changes it (no final sigma).
    #[inline]
    pub fn lower(&self, c: char) -> Option<&str> {
        if self.flags(c) & MAPS_LOWER == 0 {
            return None;
        }
        Plane::mapping(&self.plane(c as usize >> 16).lower, c as u16)
    }

    /// `_text.fold` d'un caractère d'un texte non ASCII : table du BMP, sinon inchangé.
    /// `_text.fold` of a character of a non-ASCII text: the BMP table, otherwise unchanged.
    #[inline]
    pub fn fold(&self, c: char) -> char {
        self.fold.get(c as usize).copied().unwrap_or(c)
    }

    /// Caractères égaux à `letter` sous `re.IGNORECASE`, elle comprise ; sans casse, elle seule. Règle de `re`
    /// pour un littéral : même minuscule simple de `_sre` que `letter`, ou que l'un de ses cas supplémentaires.
    /// Characters equal to `letter` under `re.IGNORECASE`, itself included; without case, only itself. `re`'s
    /// rule for a literal: the same `_sre` simple lowercase as `letter`, or as one of its extra cases.
    pub fn equivalents(&self, letter: char) -> Vec<char> {
        let case = &self.ignorecase;
        let mut equal = vec![letter];
        if case.cased.contains(&letter) {
            let lowered = case.lower.get(&letter).copied().unwrap_or(letter);
            let targets = std::iter::once(lowered).chain(case.fixes.get(&lowered).into_iter().flatten().copied());
            for target in targets {
                equal.extend(case.by_lower.get(&target).into_iter().flatten().copied());
            }
        }
        equal.sort_unstable();
        equal.dedup();
        equal
    }

    /// `c` égale-t-il `letter` sous `re.IGNORECASE` ? Même règle que `equivalents`, sans allocation : `c` a pour
    /// minuscule celle de `letter` ou l'un de ses cas supplémentaires (`by_lower` et `lower` viennent des mêmes
    /// données). Does `c` equal `letter` under `re.IGNORECASE`? Same rule as `equivalents`, without allocating.
    pub fn case_insensitive_eq(&self, letter: char, c: char) -> bool {
        if c == letter {
            return true;
        }
        let case = &self.ignorecase;
        if !case.cased.contains(&letter) {
            return false;
        }
        let lowered = case.lower.get(&letter).copied().unwrap_or(letter);
        case.lower.get(&c).is_some_and(|&lc| lc == lowered || case.fixes.get(&lowered).is_some_and(|f| f.contains(&lc)))
    }

    /// Candidats de `re.IGNORECASE` : hors d'eux, un ensemble insensible à la casse est l'ensemble lui-même.
    /// `re.IGNORECASE` candidates: outside them, a case-insensitive set is the set itself.
    pub fn ignorecase_candidates(&self) -> &[char] {
        &self.ignorecase.candidates
    }

    /// `\w`, `\d`, `\s` de `re` sur tous les plans ; les plans concernés sont chargés une fois (GIL tenu).
    /// `re`'s `\w`, `\d`, `\s` over every plane; the planes involved are loaded once (GIL held).
    pub fn perl_sets(&self, py: Python<'_>) -> PyResult<&PerlSets> {
        if let Some(sets) = self.perl.get() {
            return Ok(sets);
        }
        self.prepare_planes(py, self.perl_planes.iter().fold(0u32, |mask, &p| mask | 1 << p))?;
        let planes: Vec<usize> = std::iter::once(0).chain(self.perl_planes.iter().copied()).collect();
        let class = |bit: u16| {
            let mut ranges = Vec::new();
            for &plane in &planes {
                let first = (plane * PLANE) as u32;
                let mut start = None;
                for (low, &flags) in self.plane(plane).flags.iter().enumerate() {
                    match (flags & bit != 0, start) {
                        (true, None) => start = Some(first + low as u32),
                        (false, Some(from)) => {
                            push_range(&mut ranges, from, first + low as u32 - 1);
                            start = None;
                        }
                        _ => {}
                    }
                }
                if let Some(from) = start {
                    push_range(&mut ranges, from, first + PLANE as u32 - 1);
                }
            }
            ClassUnicode::new(ranges)
        };
        let _ = self.perl.set(PerlSets { word: class(WORD), digit: class(DECIMAL), space: class(SPACE) });
        self.perl.get().ok_or_else(|| PyValueError::new_err("classes indisponibles / classes unavailable"))
    }
}

/// La table, côté Python (`gdprguardian._native.unicode_tables()`) / the table, Python side.
#[pyclass(name = "UnicodeTables", frozen, module = "gdprguardian_core")]
pub struct PyUnicodeTables {
    inner: Arc<Unicode>,
}

fn item<'py>(dict: &Bound<'py, PyDict>, name: &str) -> PyResult<Bound<'py, PyAny>> {
    dict.get_item(name)?.ok_or_else(|| PyValueError::new_err(format!("donnée manquante / missing data: {name}")))
}

/// Correspondance caractère par caractère / character-by-character mapping.
fn map_chars<'a>(text: &str, mapping: impl Fn(char) -> Option<&'a str>) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match mapping(c) {
            Some(mapped) => out.push_str(mapped),
            None => out.push(c),
        }
    }
    out
}

#[pymethods]
impl PyUnicodeTables {
    #[classattr]
    const WORD: u16 = WORD;
    #[classattr]
    const ALNUM: u16 = ALNUM;
    #[classattr]
    const LETTER: u16 = LETTER;
    #[classattr]
    const DECIMAL: u16 = DECIMAL;
    #[classattr]
    const DIGIT: u16 = DIGIT;
    #[classattr]
    const SPACE: u16 = SPACE;
    #[classattr]
    const ALPHA: u16 = ALPHA;
    #[classattr]
    const UPPER: u16 = UPPER;
    #[classattr]
    const LOWER: u16 = LOWER;
    #[classattr]
    const TITLE: u16 = TITLE;
    #[classattr]
    const UPPER_SAFE: u16 = UPPER_SAFE;
    #[classattr]
    const CAPITAL: u16 = CAPITAL;
    #[classattr]
    const INVISIBLE: u16 = INVISIBLE;
    #[classattr]
    const MAPS_UPPER: u16 = MAPS_UPPER;
    #[classattr]
    const MAPS_LOWER: u16 = MAPS_LOWER;

    /// `bmp` : `_text.plane_classes(0)` ; `loader(plane)` rend un autre plan ; `fold` : `FOLD_TABLE` ;
    /// `ignorecase` : `_text.ignorecase_data()` ; `perl_planes` : plans hors BMP où `\w`, `\d`, `\s` existent.
    /// `bmp`: plane 0's data; `loader(plane)` returns another plane; `perl_planes`: astral planes that may hold
    /// `\w`, `\d`, `\s` characters.
    #[new]
    #[pyo3(signature = (*, bmp, loader, fold, ignorecase, perl_planes))]
    fn new(
        bmp: PlaneData,
        loader: Py<PyAny>,
        fold: Vec<(u32, u32)>,
        ignorecase: &Bound<'_, PyDict>,
        perl_planes: Vec<usize>,
    ) -> PyResult<Self> {
        let data = IgnoreCaseData {
            lower: item(ignorecase, "lower")?.extract()?,
            cased: item(ignorecase, "cased")?.extract()?,
            fixes: item(ignorecase, "fixes")?.extract()?,
        };
        let inner = Unicode::new(bmp, Some(loader), &fold, data, perl_planes).map_err(PyValueError::new_err)?;
        Ok(Self { inner: Arc::new(inner) })
    }

    /// Drapeaux d'un caractère (tests différentiels) / a character's flags (differential tests).
    fn flags(&self, py: Python<'_>, ch: char) -> PyResult<u16> {
        let mut buffer = [0u8; 4];
        self.inner.prepare(py, &[ch.encode_utf8(&mut buffer)])?;
        Ok(self.inner.flags(ch))
    }

    /// Drapeaux de chaque caractère de `text` (tests) / flags of each character of `text` (tests).
    fn flags_of(&self, py: Python<'_>, text: &str) -> PyResult<Vec<u16>> {
        self.inner.prepare(py, &[text])?;
        Ok(text.chars().map(|c| self.inner.flags(c)).collect())
    }

    /// `str.upper()` caractère par caractère (tests) / character by character (tests).
    fn upper(&self, py: Python<'_>, text: &str) -> PyResult<String> {
        self.inner.prepare(py, &[text])?;
        Ok(map_chars(text, |c| self.inner.upper(c)))
    }

    /// `str.lower()` caractère par caractère, sans sigma final (tests) / without final sigma (tests).
    fn lower(&self, py: Python<'_>, text: &str) -> PyResult<String> {
        self.inner.prepare(py, &[text])?;
        Ok(map_chars(text, |c| self.inner.lower(c)))
    }

    /// `_text.fold` d'un texte non ASCII (tests) / of a non-ASCII text (tests).
    fn fold(&self, text: &str) -> String {
        text.chars().map(|c| self.inner.fold(c)).collect()
    }

    /// Caractères égaux à `letter` sous `re.IGNORECASE` (tests) / equal under `re.IGNORECASE` (tests).
    fn equivalents(&self, letter: char) -> String {
        self.inner.equivalents(letter).into_iter().collect()
    }

    /// `c` égale-t-il `letter` sous `re.IGNORECASE` ? (tests) / does `c` equal `letter` under IGNORECASE?
    fn case_insensitive_eq(&self, letter: char, c: char) -> bool {
        self.inner.case_insensitive_eq(letter, c)
    }

    /// Intervalles [début, fin] de `\w`, `\d` ou `\s` (« w », « d », « s ») tels que le compilateur les voit.
    /// Inclusive ranges of `\w`, `\d` or `\s` as the pattern compiler sees them.
    fn perl_class(&self, py: Python<'_>, name: &str) -> PyResult<Vec<(u32, u32)>> {
        let sets = self.inner.perl_sets(py)?;
        let class = match name {
            "w" => &sets.word,
            "d" => &sets.digit,
            "s" => &sets.space,
            _ => return Err(PyValueError::new_err("w, d ou / or s")),
        };
        Ok(class.iter().map(|r| (r.start() as u32, r.end() as u32)).collect())
    }

    /// Plans chargés (tests de paresse) / loaded planes (laziness tests).
    #[getter]
    fn loaded_planes(&self) -> Vec<usize> {
        self.inner.loaded_planes()
    }
}

impl PyUnicodeTables {
    /// Vue pour un appel : les plans des caractères des textes sont chargés avant de libérer le GIL.
    /// Per-call view: the planes of the texts' characters are loaded before the GIL is released.
    pub fn classes<'a>(&'a self, py: Python<'_>, texts: &[&str]) -> PyResult<&'a Unicode> {
        self.inner.prepare(py, texts)?;
        Ok(&self.inner)
    }

    /// La table partagée, pour un détecteur construit une fois / the shared table, for a detector built once.
    pub fn shared(&self) -> Arc<Unicode> {
        Arc::clone(&self.inner)
    }

    /// La table partagée, empruntée (moteur fusionné) / the shared table, borrowed (fused engine).
    pub(crate) fn table(&self) -> &Unicode {
        &self.inner
    }
}

/// Table de test : ASCII, « É » et « é », plans hors BMP vides, d'après des prédicats Rust (tests Rust seuls).
/// Test table: ASCII, "É" and "é", empty astral planes, from Rust predicates (Rust tests only).
#[cfg(test)]
pub fn test_unicode() -> Arc<Unicode> {
    let column = |test: fn(char) -> bool| -> Vec<(u32, u32)> {
        (0..PLANE as u32).filter(|&cp| char::from_u32(cp).is_some_and(test)).map(|cp| (cp, cp + 1)).collect()
    };
    let runs = vec![
        (WORD, column(|c| c.is_ascii_alphanumeric() || c == '_' || c == 'É' || c == 'é')),
        (LETTER, column(|c| c.is_ascii_alphabetic() || c == 'É' || c == 'é')),
        (DECIMAL, column(|c| c.is_ascii_digit())),
        (DIGIT, column(|c| c.is_ascii_digit())),
        (SPACE, column(|c| c == ' ' || c == '\u{a0}' || ('\t'..='\r').contains(&c) || ('\x1c'..='\x1f').contains(&c))),
        (ALPHA, column(|c| c.is_ascii_alphabetic() || c == 'É' || c == 'é')),
        (UPPER, column(|c| c.is_ascii_uppercase() || c == 'É')),
        (LOWER, column(|c| c.is_ascii_lowercase() || c == 'é')),
        (CAPITAL, column(|c| c.is_ascii_uppercase() || c == 'É')),
        (INVISIBLE, column(|c| c == '\u{ad}' || c == '\u{200b}')),
    ];
    let upper = (b'a'..=b'z').map(|b| (u32::from(b), (b as char).to_ascii_uppercase().to_string()));
    let lower = (b'A'..=b'Z').map(|b| (u32::from(b), (b as char).to_ascii_lowercase().to_string()));
    let bmp =
        (runs, upper.chain([(0xE9, "É".to_string())]).collect(), lower.chain([(0xC9, "é".to_string())]).collect());
    let fold: Vec<(u32, u32)> = (0x41..0x5B).map(|cp| (cp, cp + 32)).chain([(0xC9, 0x65), (0xE9, 0x65)]).collect();
    let mut ignorecase = IgnoreCaseData::default();
    for cp in (0x41..=0x5A).chain([0xC9]) {
        let lower = cp + 32;
        ignorecase.lower.extend([(cp, lower), (lower, lower)]);
        ignorecase.cased.extend([cp, lower]);
    }
    Arc::new(Unicode::new(bmp, None, &fold, ignorecase, Vec::new()).expect("valid test table"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn derived_bits_and_mappings() {
        let u = test_unicode();
        assert!(u.is('a', ALNUM) && u.is('a', WORD | LETTER | LOWER) && u.is('_', WORD) && !u.is('_', ALNUM));
        assert!(u.is('A', UPPER_SAFE) && !u.is('a', UPPER_SAFE) && u.is('-', UPPER_SAFE));
        assert_eq!(u.upper('é'), Some("É"));
        assert_eq!(u.lower('A'), Some("a"));
        assert_eq!(u.upper('-'), None);
        assert_eq!(u.fold('É'), 'e');
        assert_eq!(u.fold('\u{1F600}'), '\u{1F600}');
        // Plans hors BMP sans chargeur : vides / astral planes without a loader: empty.
        assert_eq!(u.flags('\u{1D400}'), UPPER_SAFE);
        assert_eq!(u.equivalents('e'), vec!['E', 'e']);
        assert_eq!(u.equivalents('É'), vec!['É', 'é']);
        assert_eq!(u.equivalents('-'), vec!['-']);
        assert_eq!(u.loaded_planes(), vec![0]);
    }

    #[test]
    fn case_insensitive_eq_is_membership_in_equivalents() {
        let u = test_unicode();
        let sample: Vec<char> = (0..0x300).filter_map(char::from_u32).collect();
        for &letter in &sample {
            let equivalents = u.equivalents(letter);
            for &c in &sample {
                assert_eq!(u.case_insensitive_eq(letter, c), equivalents.contains(&c), "{letter:?} {c:?}");
            }
        }
    }

    #[test]
    fn a_missed_plane_fails_the_call() {
        let u = test_unicode();
        let before = u.missed();
        assert!(u.unchanged(before).is_ok());
        u.missed.fetch_add(1, Ordering::Relaxed);
        assert!(u.unchanged(before).is_err() && u.unchanged(u.missed()).is_ok());
    }

    #[test]
    fn planes_in_texts() {
        assert_eq!(planes_in(&["abc", "é"]), 0);
        assert_eq!(planes_in(&["a\u{1F600}", "\u{20000}"]), 0b110);
        assert_eq!(planes_in(&["\u{E0041}\u{10FFFF}"]), (1 << 14) | (1 << 16));
    }

    #[test]
    fn malformed_planes_are_refused() {
        assert!(Plane::new(0, (vec![(WORD, vec![(0, PLANE as u32 + 1)])], vec![], vec![])).is_err());
        assert!(Plane::new(0, (vec![(ALNUM, vec![(0, 1)])], vec![], vec![])).is_err());
        assert!(Plane::new(0, (vec![], vec![(PLANE as u32, "x".into())], vec![])).is_err());
        assert!(Unicode::new((vec![], vec![], vec![]), None, &[], IgnoreCaseData::default(), vec![0]).is_err());
    }
}
