//! Préparation du texte : normalisation, repliement et table des positions en un appel ; langue.
//!
//! Text preparation: normalisation, folding and offset map in one call; language.
//! Réplique exacte de `gdprguardian._text.normalize`/`fold` et de `gdprguardian.locale.detect_language`, construite
//! à partir des tables de Python (une seule source de vérité). Exact replica of those Python functions,
//! built from Python's own tables (a single source of truth).

use std::borrow::Cow;
use std::collections::HashMap;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyString};

use crate::text::{char_at, char_before, Classes, INVISIBLE, LETTER, LOWER};
use crate::unicode::PyUnicodeTables;

const BMP: usize = 0x10000;
const IDENTITY: u16 = u16::MAX;

/// Table caractère -> caractère de `str.translate`, en deux niveaux (blocs de 256 points du BMP, seuls les
/// blocs modifiés sont stockés) puis les points hors BMP. Character -> character table of `str.translate`,
/// two-level (256-point BMP blocks, only changed blocks stored), then points beyond the BMP.
struct CharMap {
    /// Cibles des caractères ASCII, lues octet par octet / targets of ASCII characters, read byte by byte.
    ascii: [char; 128],
    index: Vec<u16>,
    blocks: Vec<[char; 256]>,
    astral: Vec<(u32, char)>,
}

impl CharMap {
    /// `bmp` : table dense de Python encodée en UTF-32 LE (65 536 points) / Python's dense table, UTF-32 LE.
    fn new(bmp: &[u8], astral: &[(u32, u32)]) -> PyResult<Self> {
        let invalid = || PyValueError::new_err("table de transcodage invalide / invalid translation table");
        if bmp.len() != 4 * BMP {
            return Err(invalid());
        }
        let targets = bmp.as_chunks::<4>().0;
        Self::build(|cp| char::from_u32(u32::from_le_bytes(targets[cp as usize])).ok_or_else(invalid), astral)
    }

    /// `target(cp)` : cible de chaque point du BMP / the target of each BMP point.
    fn build(target: impl Fn(u32) -> PyResult<char>, astral: &[(u32, u32)]) -> PyResult<Self> {
        let invalid = || PyValueError::new_err("table de transcodage invalide / invalid translation table");
        let mut index = vec![IDENTITY; BMP / 256];
        let mut blocks = Vec::new();
        for (block, slot) in index.iter_mut().enumerate() {
            let mut entries = ['\0'; 256];
            let mut changed = false;
            for (low, entry) in entries.iter_mut().enumerate() {
                let source = (block * 256 + low) as u32;
                // Demi-codets (U+D800–U+DFFF) : absents d'un texte Rust / surrogates never occur in Rust text.
                let Some(source) = char::from_u32(source) else {
                    continue;
                };
                let target = target(u32::from(source))?;
                *entry = target;
                changed |= target != source;
            }
            if changed {
                *slot = blocks.len() as u16;
                blocks.push(entries);
            }
        }
        let mut astral: Vec<(u32, char)> = astral
            .iter()
            .map(|&(cp, target)| char::from_u32(target).map(|t| (cp, t)).ok_or_else(invalid))
            .collect::<PyResult<_>>()?;
        astral.sort_unstable();
        // Python applique la table hors BMP après la table dense : une cible hors BMP de celle-ci est
        // transcodée à son tour. Python applies the astral table after the dense one: an astral target of
        // the latter is translated in turn.
        for entry in blocks.iter_mut().flatten().filter(|entry| **entry as usize >= BMP) {
            *entry = astral_target(&astral, *entry);
        }
        let mut map = Self { ascii: ['\0'; 128], index, blocks, astral };
        map.ascii = std::array::from_fn(|b| map.map(char::from(b as u8)));
        Ok(map)
    }

    #[inline]
    fn map(&self, c: char) -> char {
        let cp = c as u32;
        if cp < BMP as u32 {
            match self.index[(cp >> 8) as usize] {
                IDENTITY => c,
                block => self.blocks[block as usize][(cp & 0xFF) as usize],
            }
        } else {
            astral_target(&self.astral, c)
        }
    }

    /// `str.translate` en un passage : les tronçons inchangés sont copiés d'un bloc, aucune copie si rien
    /// ne change. One pass: unchanged stretches are copied wholesale, no copy at all if nothing changes.
    fn translate<'a>(&self, text: &'a str) -> Cow<'a, str> {
        let bytes = text.as_bytes();
        let mut out: Option<String> = None;
        let (mut copied, mut i) = (0, 0);
        while i < bytes.len() {
            let (source, width) = match bytes[i] {
                b if b < 0x80 => (char::from(b), 1),
                _ => {
                    let c = text[i..].chars().next().unwrap_or(char::REPLACEMENT_CHARACTER);
                    (c, c.len_utf8())
                }
            };
            let target = if width == 1 { self.ascii[bytes[i] as usize] } else { self.map(source) };
            if target != source {
                let out = out.get_or_insert_with(|| String::with_capacity(text.len()));
                out.push_str(&text[copied..i]);
                out.push(target);
                copied = i + width;
            }
            i += width;
        }
        match out {
            None => Cow::Borrowed(text),
            Some(mut out) => {
                out.push_str(&text[copied..]);
                Cow::Owned(out)
            }
        }
    }
}

/// Cible d'un caractère hors BMP dans la table triée / an astral character's target in the sorted table.
#[inline]
fn astral_target(astral: &[(u32, char)], c: char) -> char {
    astral.binary_search_by_key(&(c as u32), |entry| entry.0).map_or(c, |i| astral[i].1)
}

#[inline]
fn is_emphasis(b: u8) -> bool {
    b == b'*' || b == b'_'
}

/// `_EMPHASIS_RE.sub(_unbold, text)` : `[*_]{2,3}` hors d'un mot -> espaces, longueur gardée.
/// Markdown emphasis outside a word becomes spaces, length kept.
fn unbold<'a>(text: Cow<'a, str>, classes: &Classes) -> Cow<'a, str> {
    let bytes = text.as_bytes();
    let alnum = |c: char| classes.is_alnum(c);
    let mut blanks: Vec<(usize, usize)> = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if !is_emphasis(bytes[i]) {
            i += 1;
            continue;
        }
        let run_start = i;
        while i < bytes.len() && is_emphasis(bytes[i]) {
            i += 1;
        }
        // Correspondances gloutonnes successives de 3, puis 2 ; un reste de 1 ne correspond pas.
        // Successive greedy matches of 3, then 2; a remainder of 1 does not match.
        let mut start = run_start;
        while i - start >= 2 {
            let end = start + (i - start).min(3);
            let inside_word = char_before(&text, start).is_some_and(alnum) && char_at(&text, end).is_some_and(alnum);
            if !inside_word {
                blanks.push((start, end));
            }
            start = end;
        }
    }
    if blanks.is_empty() {
        return text;
    }
    let mut out = String::with_capacity(text.len());
    let mut last = 0;
    for (start, end) in blanks {
        out.push_str(&text[last..start]);
        out.extend(std::iter::repeat_n(' ', end - start));
        last = end;
    }
    out.push_str(&text[last..]);
    Cow::Owned(out)
}

/// Nombre de tabulations ou espaces à partir de `i`, au plus 3 / spaces or tabs from `i`, at most 3.
fn blanks_at(bytes: &[u8], i: usize) -> usize {
    bytes[i.min(bytes.len())..].iter().take(3).take_while(|&&b| b == b' ' || b == b'\t').count()
}

/// Fin (octet) de la césure `-[ \t]{0,2}\r?\n[ \t]{0,2}` commençant à `dash`, si elle existe.
/// End byte of the hyphen break starting at `dash`, if any.
fn hyphen_break_end(bytes: &[u8], dash: usize) -> Option<usize> {
    let mut i = dash + 1;
    let before = blanks_at(bytes, i);
    if before > 2 {
        return None;
    }
    i += before;
    if bytes.get(i) == Some(&b'\r') {
        i += 1;
    }
    if bytes.get(i) != Some(&b'\n') {
        return None;
    }
    i += 1;
    let after = blanks_at(bytes, i);
    (after <= 2).then_some(i + after)
}

/// Coupes en positions de caractères : invisibles et césures de fin de ligne, triées, disjointes.
/// Cuts in character positions: invisible characters and end-of-line hyphenation, sorted, disjoint.
fn cuts(text: &str, classes: &Classes) -> Vec<(usize, usize)> {
    let invisible = !text.is_ascii();
    let hyphens = text.contains('-') && text.contains('\n');
    let mut cuts = Vec::new();
    if !invisible && !hyphens {
        return cuts;
    }
    let bytes = text.as_bytes();
    let letter = |c: char| classes.flags(c) & LETTER != 0;
    // Octet par octet ; seuls les caractères non ASCII sont décodés / byte by byte, decoding non-ASCII only.
    let (mut position, mut byte) = (0, 0);
    while byte < bytes.len() {
        let (c, width) = match bytes[byte] {
            b if b < 0x80 => (char::from(b), 1),
            _ => {
                let c = text[byte..].chars().next().unwrap_or(char::REPLACEMENT_CHARACTER);
                (c, c.len_utf8())
            }
        };
        if invisible && classes.flags(c) & INVISIBLE != 0 {
            cuts.push((position, position + 1));
        } else if hyphens && c == '-' && char_before(text, byte).is_some_and(letter) {
            // « Du-\npont » -> « Dupont » ; « Jean-\nPierre » garde son trait d'union / keeps its hyphen.
            if let Some(end) = hyphen_break_end(bytes, byte) {
                if let Some(next) = char_at(text, end).filter(|&n| letter(n)) {
                    // Césure faite d'octets ASCII : longueur en caractères = longueur en octets.
                    // The break is ASCII bytes: its length in characters equals its length in bytes.
                    let start = if classes.flags(next) & LOWER != 0 { position } else { position + 1 };
                    cuts.push((start, position + end - byte));
                }
            }
        }
        position += 1;
        byte += width;
    }
    cuts
}

/// Texte privé des coupes et table des positions (une par caractère gardé, puis la longueur).
/// Text without the cuts and offset map (one per kept character, then the length).
fn assemble(text: &str, cuts: &[(usize, usize)]) -> (String, Vec<i64>) {
    let mut out = String::with_capacity(text.len());
    let mut offsets = Vec::with_capacity(text.len() + 1);
    let mut cut = cuts.iter().peekable();
    let mut length = 0;
    for (position, c) in text.chars().enumerate() {
        length = position + 1;
        while cut.next_if(|&&(_, end)| end <= position).is_some() {}
        if cut.peek().is_some_and(|&&(start, _)| start <= position) {
            continue;
        }
        out.push(c);
        offsets.push(position as i64);
    }
    offsets.push(length as i64);
    (out, offsets)
}

/// Résultat de la préparation ; `None` = texte d'entrée inchangé / preparation result; None = unchanged.
struct Prepared {
    norm: Option<String>,
    folded: Option<String>,
    offsets: Option<Vec<i64>>,
}

/// Tables de normalisation et de repliement de `gdprguardian._text` / normalisation and folding tables.
#[pyclass(name = "Preparer", frozen)]
pub struct Preparer {
    tables: Py<PyUnicodeTables>,
    normalize: CharMap,
    fold: CharMap,
    /// Cibles hors BMP des tables, à classer avec le texte / targets beyond the BMP, classified with the text.
    astral_targets: String,
}

impl Preparer {
    /// `normalize()` : transcodage, gras Markdown, coupes / translation, emphasis, cuts.
    fn normalize_text<'a>(&self, text: &'a str, classes: &Classes) -> (Cow<'a, str>, Option<Vec<i64>>) {
        // Comme Python : pas de transcodage pour un texte ASCII / like Python: no translation for ASCII.
        let mut mapped = if text.is_ascii() { Cow::Borrowed(text) } else { self.normalize.translate(text) };
        if mapped.contains("**") || mapped.contains("__") {
            mapped = unbold(mapped, classes);
        }
        let cuts = cuts(&mapped, classes);
        if cuts.is_empty() {
            return (mapped, None);
        }
        let (norm, offsets) = assemble(&mapped, &cuts);
        (Cow::Owned(norm), Some(offsets))
    }

    /// `fold()` : minuscules ASCII, sinon table de repliement / ASCII lowercase, else the folding table.
    fn fold_text<'a>(&self, text: &'a str) -> Cow<'a, str> {
        if text.is_ascii() {
            if text.bytes().any(|b| b.is_ascii_uppercase()) {
                Cow::Owned(text.to_ascii_lowercase())
            } else {
                Cow::Borrowed(text)
            }
        } else {
            self.fold.translate(text)
        }
    }

    fn prepare_text(&self, text: &str, classes: &Classes) -> Prepared {
        let (norm, offsets) = self.normalize_text(text, classes);
        let folded = match self.fold_text(&norm) {
            Cow::Borrowed(_) => None,
            Cow::Owned(folded) => Some(folded),
        };
        let norm = match norm {
            Cow::Borrowed(_) => None,
            Cow::Owned(norm) => Some(norm),
        };
        Prepared { norm, folded, offsets }
    }
}

fn offsets_bytes<'py>(py: Python<'py>, offsets: &[i64]) -> Bound<'py, PyBytes> {
    let bytes: Vec<u8> = offsets.iter().flat_map(|o| o.to_ne_bytes()).collect();
    PyBytes::new(py, &bytes)
}

#[pymethods]
impl Preparer {
    /// `tables` : table Unicode partagée, dont le repliement (`_text.fold`) ; `normalize_*` : `_NORMALIZE_BMP`
    /// (UTF-32 LE) et `_ASTRAL_NORMALIZE`. `tables`: the shared Unicode table, its folding included.
    #[new]
    fn new(
        tables: Py<PyUnicodeTables>,
        normalize_bmp: &Bound<'_, PyBytes>,
        normalize_astral: Vec<(u32, u32)>,
    ) -> PyResult<Self> {
        let normalize = CharMap::new(normalize_bmp.as_bytes(), &normalize_astral)?;
        let unicode = tables.get().shared();
        let fold = CharMap::build(|cp| Ok(char::from_u32(cp).map_or('\0', |c| unicode.fold(c))), &[])?;
        let mut astral_targets: Vec<char> = normalize
            .astral
            .iter()
            .map(|entry| entry.1)
            .chain(normalize.blocks.iter().flatten().copied())
            .filter(|&c| c as usize >= BMP)
            .collect();
        astral_targets.sort_unstable();
        astral_targets.dedup();
        Ok(Self { tables, normalize, fold, astral_targets: astral_targets.into_iter().collect() })
    }

    /// (texte normalisé, texte replié, positions en `int64` natifs ou None), sans GIL.
    /// (normalised text, folded text, offsets as native `int64` bytes or None), GIL released.
    /// Les textes inchangés sont rendus tels quels, sans copie / unchanged texts are returned as is.
    #[allow(clippy::type_complexity)]
    fn prepare<'py>(
        &self,
        py: Python<'py>,
        text: &Bound<'py, PyString>,
    ) -> PyResult<(Bound<'py, PyString>, Bound<'py, PyString>, Option<Bound<'py, PyBytes>>)> {
        let source = text.to_str()?;
        let classes = self.tables.get().classes(py, &[source, &self.astral_targets])?;
        let prepared = py.detach(|| self.prepare_text(source, classes));
        let norm = prepared.norm.map_or_else(|| text.clone(), |norm| PyString::new(py, &norm));
        let folded = prepared.folded.map_or_else(|| norm.clone(), |folded| PyString::new(py, &folded));
        Ok((norm, folded, prepared.offsets.map(|offsets| offsets_bytes(py, &offsets))))
    }

    /// `normalize()` seul / `normalize()` alone.
    fn normalize<'py>(
        &self,
        py: Python<'py>,
        text: &Bound<'py, PyString>,
    ) -> PyResult<(Bound<'py, PyString>, Option<Bound<'py, PyBytes>>)> {
        let source = text.to_str()?;
        let classes = self.tables.get().classes(py, &[source, &self.astral_targets])?;
        let (norm, offsets) = py.detach(|| {
            let (norm, offsets) = self.normalize_text(source, classes);
            (if let Cow::Owned(norm) = norm { Some(norm) } else { None }, offsets)
        });
        let norm = norm.map_or_else(|| text.clone(), |norm| PyString::new(py, &norm));
        Ok((norm, offsets.map(|offsets| offsets_bytes(py, &offsets))))
    }

    /// `fold()` seul / `fold()` alone.
    fn fold<'py>(&self, py: Python<'py>, text: &Bound<'py, PyString>) -> PyResult<Bound<'py, PyString>> {
        let source = text.to_str()?;
        let folded = py.detach(|| if let Cow::Owned(folded) = self.fold_text(source) { Some(folded) } else { None });
        Ok(folded.map_or_else(|| text.clone(), |folded| PyString::new(py, &folded)))
    }
}

/// Langue majoritaire par comptage de mots outils, comme `gdprguardian.locale.detect_language`.
/// Dominant language by stop-word counts, as `gdprguardian.locale.detect_language`.
#[pyclass(name = "LanguageDetector", frozen)]
pub struct LanguageDetector {
    /// Mots de 8 lettres au plus, rangés dans un entier : table à adressage ouvert (puissance de 2, au plus
    /// un quart pleine, 0 = vide) -> indice dans `ids`. Words of up to 8 letters packed in an integer:
    /// open-addressing table (power of 2, at most a quarter full, 0 = empty) -> index into `ids`.
    slots: Vec<(u64, usize)>,
    /// Langues de chaque mot (indices, ordre de Python) / each word's languages (indices, Python's order).
    ids: Vec<Vec<usize>>,
    /// Mots plus longs / longer words.
    long: HashMap<Vec<u8>, Vec<usize>>,
    languages: Vec<Py<PyString>>,
    undetermined: Py<PyString>,
    /// Échantillon en caractères (`LANGUAGE_SAMPLE`) / sample size in characters.
    sample: usize,
}

/// Mot `[a-z]{1,8}` rangé dans un entier (sans octet nul, donc sans collision) / word packed in an integer.
fn pack(word: &[u8]) -> Option<u64> {
    (word.len() <= 8).then(|| {
        let mut bytes = [0u8; 8];
        bytes[..word.len()].copy_from_slice(word);
        u64::from_le_bytes(bytes)
    })
}

impl LanguageDetector {
    /// Case du mot, ou première case vide sur son chemin / the word's slot, or the first empty one on its path.
    fn slot(slots: &[(u64, usize)], key: u64) -> usize {
        let mask = slots.len() - 1;
        let mut i = (key.wrapping_mul(0x9E37_79B9_7F4A_7C15) >> 32) as usize & mask;
        while slots[i].0 != 0 && slots[i].0 != key {
            i = (i + 1) & mask;
        }
        i
    }

    fn languages_of(&self, word: &[u8]) -> Option<&[usize]> {
        match pack(word) {
            Some(key) => {
                let (found, id) = self.slots[Self::slot(&self.slots, key)];
                (found == key).then(|| self.ids[id].as_slice())
            }
            None if self.long.is_empty() => None,
            None => self.long.get(word).map(Vec::as_slice),
        }
    }
}

#[pymethods]
impl LanguageDetector {
    #[new]
    fn new(py: Python<'_>, word_languages: Vec<(String, Vec<String>)>, sample: usize) -> Self {
        let mut names: Vec<String> = Vec::new();
        let (mut short, mut long) = (Vec::<(u64, Vec<usize>)>::new(), HashMap::new());
        for (word, languages) in word_languages {
            let ids: Vec<usize> = languages
                .into_iter()
                .map(|language| {
                    names.iter().position(|n| *n == language).unwrap_or_else(|| {
                        names.push(language);
                        names.len() - 1
                    })
                })
                .collect();
            // Seuls des mots `[a-z]+` peuvent être comptés / only `[a-z]+` words can ever be counted.
            if word.is_empty() || !word.bytes().all(|b| b.is_ascii_lowercase()) {
                continue;
            }
            match pack(word.as_bytes()) {
                Some(key) => short.push((key, ids)),
                None => {
                    long.insert(word.into_bytes(), ids);
                }
            }
        }
        let mut slots = vec![(0u64, 0usize); (4 * short.len()).max(8).next_power_of_two()];
        let mut ids = Vec::with_capacity(short.len());
        for (key, languages) in short {
            let i = Self::slot(&slots, key);
            if slots[i].0 == 0 {
                slots[i] = (key, ids.len());
                ids.push(languages);
            }
        }
        let languages = names.iter().map(|name| PyString::intern(py, name).unbind()).collect();
        Self { slots, ids, long, languages, undetermined: PyString::intern(py, "und").unbind(), sample }
    }

    /// Travail borné par l'échantillon : pas besoin de libérer le GIL / bounded by the sample.
    #[pyo3(signature = (folded, minimum=2))]
    fn detect(&self, py: Python<'_>, folded: &str, minimum: i64) -> Py<PyString> {
        let mut counts = vec![0i64; self.languages.len()];
        // Ordre de première apparition, comme un dict Python / first-seen order, like a Python dict.
        let mut order: Vec<usize> = Vec::new();
        let mut count = |word: &[u8]| {
            for &language in self.languages_of(word).into_iter().flatten() {
                if counts[language] == 0 {
                    order.push(language);
                }
                counts[language] += 1;
            }
        };
        // `[a-z]+` sur les `sample` premiers caractères, octet par octet : un octet de tête par caractère.
        // `[a-z]+` on the first `sample` characters, byte by byte: one lead byte per character.
        let bytes = folded.as_bytes();
        let (mut word_start, mut chars, mut end) = (None, 0, bytes.len());
        for (i, &b) in bytes.iter().enumerate() {
            if (b as i8) >= -0x40 {
                if chars == self.sample {
                    end = i;
                    break;
                }
                chars += 1;
            }
            if b.is_ascii_lowercase() {
                word_start.get_or_insert(i);
            } else if let Some(start) = word_start.take() {
                count(&bytes[start..i]);
            }
        }
        if let Some(start) = word_start {
            count(&bytes[start..end]);
        }
        // `minimum - 1` sans débordement : les comptes valent au moins 1, le résultat reste exact.
        // `minimum - 1` without overflow: counts are at least 1, so the result stays exact.
        let (mut best, mut best_count) = (None, minimum.saturating_sub(1));
        for language in order {
            if counts[language] > best_count {
                (best, best_count) = (Some(language), counts[language]);
            }
        }
        best.map_or(&self.undetermined, |language| &self.languages[language]).clone_ref(py)
    }
}

// --- Moteur fusionné : appels directs, sans aller-retour par Python / fused engine: direct calls ----------------

/// Texte normalisé et texte replié (`None` : inchangés), table des positions / normalised and folded texts.
pub(crate) type PreparedParts = (Option<String>, Option<String>, Option<Vec<i64>>);

impl Preparer {
    /// Classes de ces textes et des cibles hors BMP des tables, à demander avec le GIL.
    /// Classes of these texts and of the tables' astral targets, requested with the GIL held.
    pub(crate) fn classes_for<'a>(&'a self, py: Python<'_>, texts: &[&str]) -> PyResult<&'a Classes> {
        let mut all = texts.to_vec();
        all.push(&self.astral_targets);
        self.tables.get().classes(py, &all)
    }

    /// `prepare()` : (texte normalisé, texte replié, positions), sans GIL / without the GIL.
    pub(crate) fn prepare_parts(&self, text: &str, classes: &Classes) -> PreparedParts {
        let prepared = self.prepare_text(text, classes);
        (prepared.norm, prepared.folded, prepared.offsets)
    }

    /// `normalize()` : (texte normalisé ou `None` s'il est inchangé, positions), sans GIL / without the GIL.
    pub(crate) fn normalize_parts(&self, text: &str, classes: &Classes) -> (Option<String>, Option<Vec<i64>>) {
        let (norm, offsets) = self.normalize_text(text, classes);
        (if let Cow::Owned(norm) = norm { Some(norm) } else { None }, offsets)
    }

    /// `fold()`, sans GIL / without the GIL.
    pub(crate) fn fold_parts<'a>(&self, text: &'a str) -> Cow<'a, str> {
        self.fold_text(text)
    }
}

impl LanguageDetector {
    /// `detect_language(folded)` (seuil par défaut) / with the default minimum.
    pub(crate) fn language_of(&self, py: Python<'_>, folded: &str) -> Py<PyString> {
        self.detect(py, folded, 2)
    }
}
