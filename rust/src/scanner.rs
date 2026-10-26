//! Analyse des motifs : même sémantique que `Anonymizer._run` (Python), sans GIL.
//!
//! Pattern scanning: same semantics as `Anonymizer._run` (Python), GIL released.
//! Candidat rejeté -> nouvelle recherche au caractère suivant (aucun identifiant avalé).
//! Rejected candidate -> search again from the next character (no identifier swallowed).
//! Chaque motif ne cherche que dans ses fenêtres (`windows`), calculées en un passage pour tous : mêmes
//! correspondances que le balayage complet. Each pattern only searches its windows, computed in one pass
//! for all of them: the same matches as the full scan.
//! Bornes (`isalnum()`, `isdigit()`) et motifs : classes de caractères de Python, jamais celles de Rust.
//! Boundaries (`isalnum()`, `isdigit()`) and patterns: Python's character classes, never Rust's.

use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, OnceLock, PoisonError, Weak};
use std::thread;

use aho_corasick::AhoCorasick;
use regex_automata::meta::Regex;
use regex_automata::util::captures::Captures;
use regex_automata::{Anchored, Input};
use regex_syntax::hir::ClassUnicode;

use crate::keywords::{Hits, KeywordIndex, MAX_KEYWORD_LEN};
use crate::pattern::{self, Compiled, Tree};
use crate::text::{char_at, char_before, next_char_boundary, previous_char_boundary, CharIndex, Classes, ALNUM, DIGIT};
use crate::validators::ValidatorFn;
use crate::windows::{Mask, Plan, Shape, WindowIndex};

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    A,
    B,
    C,
    L,
}

#[derive(Clone, Copy)]
pub enum Boundary {
    Alnum,
    Word,
    Ip,
    Hex,
    Phone,
    Digit,
    /// Suite entière de groupes (« 0764 945 16 3 ») : ni chiffre + séparateur avant, ni séparateur + chiffre
    /// après / the whole run of groups: no digit + separator before, no separator + digit after.
    Group,
    None,
}

/// Séparateurs de groupes de la borne `Group` / group separators of the `Group` boundary.
fn group_separator(c: char) -> bool {
    matches!(c, ' ' | '.' | '/' | '-')
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Policy {
    None,
    Company,
    Facility,
}

pub enum Prefilter {
    None,
    Digit,
    Any(Vec<String>),
}

pub enum Group {
    Whole,
    Index(usize),
    Name(String),
}

pub struct Recognizer {
    /// Motif compilé, partagé entre analyseurs pour les motifs des packs (`compile_all`) / compiled pattern, shared
    /// between scanners for pack patterns.
    pub pattern: Arc<Compiled>,
    /// Forme du motif, consommée par `Scanner::new` / the pattern's shape, consumed by `Scanner::new`.
    pub shape: Option<Shape>,
    pub group: Group,
    pub validator: Option<ValidatorFn>,
    pub tier: Tier,
    pub contexts: Vec<u32>,
    /// Mots qui, placés entre le mot-clé et la valeur, annulent le contexte / words that cancel it in between.
    pub vetoes: Vec<u32>,
    pub before: usize,
    pub after: usize,
    pub boundary: Boundary,
    pub prefilter: Prefilter,
    pub score: f64,
    pub policy: Policy,
    /// Clé fausse acceptée si un mot-clé est proche (faute de frappe, OCR) / wrong key accepted near a keyword.
    pub fallback: bool,
}

pub struct Settings<'a> {
    pub active: &'a [bool],
    pub strict: bool,
    pub company_mode: &'a str,
    pub facility_mask: bool,
    pub ei_groups: &'a [u32],
    /// État civil d'une personne physique (`_person_groups`) / a natural person's civil status.
    pub person_groups: &'a [u32],
    /// Personne morale (`_entity_groups`) / legal entity.
    pub entity_groups: &'a [u32],
}

/// `engine.NATURAL_PERSON_WINDOW` : état civil voisin d'un identifiant d'entreprise / civil status near the number.
pub const NATURAL_PERSON_WINDOW: (usize, usize) = (120, 120);
/// `engine.LEGAL_ENTITY_WINDOW` : une personne morale dans cette fenêtre l'emporte / a legal entity there wins.
pub const LEGAL_ENTITY_WINDOW: (usize, usize) = (80, 40);

/// Raisons propres d'un numéro d'entreprise masqué (`Anonymizer._personal`) / own reasons of a masked company id.
pub const SOLE_TRADER: &str = "sole_trader";
pub const CIVIL_STATUS: &str = "civil_status_nearby";
pub const NO_LEGAL_ENTITY: &str = "no_legal_entity";

/// `engine._REGISTER_LABELS`, `_ENTITY_WORDS`, `_ENTITY_FORMS`, `_SHORT_LINE`.
const REGISTER_LABELS: [&str; 4] = ["n° RCS :", "n° RM :", "n° RCS:", "n° RM:"];
const ENTITY_WORDS: [&str; 6] =
    ["dénomination", "denomination", "raison sociale", "forme juridique", "société", "societe"];
const ENTITY_FORMS: [&str; 21] = [
    "SA", "SAS", "SASU", "SARL", "EURL", "SCI", "SNC", "SCP", "SCM", "SCA", "SCOP", "SCEA", "SELARL", "SELAS",
    "SELAFA", "SELURL", "SELCA", "GAEC", "EARL", "SEM", "GIE",
];
const SHORT_LINE: usize = 150;

/// `engine._no_legal_entity` : « n° RCS : … » d'un avis dont aucune ligne courte ne nomme de personne morale.
/// A register number field in a notice whose short lines name no legal entity. `start` : octet / byte offset.
fn no_legal_entity(text: &str, start: usize) -> bool {
    let line_start = text[..start].rfind('\n').map_or(0, |i| i + 1);
    if !REGISTER_LABELS.contains(&text[line_start..start].trim_end_matches(' ')) {
        return false;
    }
    text.split('\n').filter(|line| line.chars().count() <= SHORT_LINE).all(|line| {
        let low = line.to_lowercase();
        !ENTITY_WORDS.iter().any(|word| low.contains(word))
            && !line.split(|c: char| !c.is_ascii_uppercase()).any(|token| ENTITY_FORMS.contains(&token))
    })
}

/// Zone trouvée (positions en caractères Python) / found span (Python character offsets).
pub struct Found {
    pub start: usize,
    pub end: usize,
    pub recognizer: usize,
    pub value: Option<String>,
    pub score: f64,
    pub personal: bool,
    /// Raison propre (`explain`), ou `None` : celle du recognizer / own reason, or `None`: the recognizer's.
    pub reason: Option<&'static str>,
}

/// `engine._line_bounds` : ligne de [start, end) en caractères, bornée aux fenêtres (`near` ne lit rien au-delà).
/// The line of [start, end) in characters, bounded by the windows. `bytes`/`chars` : mêmes bornes / same bounds.
fn line_bounds(
    text: &str,
    bytes: (usize, usize),
    chars: (usize, usize),
    before: usize,
    after: usize,
) -> (usize, usize) {
    let floor = chars.0.saturating_sub(before + MAX_KEYWORD_LEN);
    let mut lo = 0;
    for (k, c) in text[..bytes.0].chars().rev().enumerate() {
        let i = chars.0 - 1 - k;
        if i < floor {
            break;
        }
        if c == '\n' {
            lo = i + 1;
            break;
        }
    }
    let hi = text[bytes.1..].chars().take(after).position(|c| c == '\n').map_or(chars.1 + after, |k| chars.1 + k);
    (lo, hi)
}

/// `engine._block_bounds` : paragraphe de [start, end) en caractères, entre deux lignes vides (blancs seuls),
/// borné aux fenêtres. The paragraph of [start, end), between two blank lines, bounded by the windows.
fn block_bounds(
    text: &str,
    bytes: (usize, usize),
    chars: (usize, usize),
    before: usize,
    after: usize,
) -> (usize, usize) {
    let floor = chars.0.saturating_sub(before + MAX_KEYWORD_LEN);
    let mut lo = floor;
    let (mut newline, mut blank) = (None, true);
    for (k, c) in text[..bytes.0].chars().rev().enumerate() {
        let i = chars.0 - 1 - k;
        if i < floor {
            break;
        }
        if c == '\n' {
            if let (Some(after_blank), true) = (newline, blank) {
                lo = after_blank + 1;
                break;
            }
            (newline, blank) = (Some(i), true);
        } else if !matches!(c, ' ' | '\t' | '\r') {
            blank = false;
        }
    }
    let (mut newline, mut blank) = (None, true);
    let mut seen = 0;
    for c in text[bytes.1..].chars().take(after) {
        let i = chars.1 + seen;
        seen += 1;
        if c == '\n' {
            if let (Some(before_blank), true) = (newline, blank) {
                return (lo, before_blank);
            }
            (newline, blank) = (Some(i), true);
        } else if !matches!(c, ' ' | '\t' | '\r') {
            blank = false;
        }
    }
    (lo, chars.1 + seen)
}

/// Motif lu dans l'arbre de `re`, ou la raison de le laisser à Python ; None : non compilé (validateur Python).
/// Pattern read from `re`'s tree, or the reason to leave it to Python; None: not compiled (Python validator).
pub type Source = Option<Result<Tree, String>>;
/// Motif compilé (partagé), ou la raison du refus ; None : non compilé / compiled (shared) pattern, or why not.
pub type CompiledSlot = Option<Result<Arc<Compiled>, String>>;

/// Compile les motifs en parallèle (quelques motifs Unicode coûtent 50 à 200 ms chacun) ; résultats dans
/// l'ordre, `None` pour une entrée absente. Les fils sont joints avant le retour ; si le système en refuse un
/// (processus isolé sans droit de créer de fil), le fil courant fait tout le travail. Compiles patterns in
/// parallel (a few Unicode patterns cost 50-200 ms each); results in order, `None` for a missing entry. Threads
/// are joined before returning; if the system refuses one (isolated process), the current thread does all.
/// `word` : `\w` de Python / Python's `\w`. `limits` : un jeu borné (règles non sûres) se compile sur le seul
/// fil courant, dans l'ordre / a bounded set (untrusted rules) compiles on the current thread only, in order.
/// `keys` : clé de partage de chaque motif des packs (`_spec`), `None` pour les autres. Hors jeu borné, un motif
/// déjà compilé par un autre analyseur (autre ensemble de packs : « FR », « FR,DE »…) est repris tel quel :
/// automates et caches communs, une seule fois en mémoire. `keys`: each pack pattern's sharing key, `None` for
/// the others; outside a bounded set, a pattern another scanner already compiled is reused as is.
pub fn compile_all(
    sources: &[Source],
    keys: &[Option<String>],
    word: &ClassUnicode,
    limits: &pattern::Limits,
) -> Vec<CompiledSlot> {
    let share = !limits.bounded();
    let key = |i: usize| keys.get(i).and_then(Option::as_deref).filter(|_| share);
    let mut found: Vec<Option<Arc<Compiled>>> = vec![None; sources.len()];
    // Motif répété dans ce jeu : compilé une fois / pattern repeated in this set: compiled once.
    let mut first: HashMap<&str, usize> = HashMap::new();
    let mut copies: Vec<(usize, usize)> = Vec::new();
    {
        let cache = compiled_patterns().lock().unwrap_or_else(PoisonError::into_inner);
        for (i, source) in sources.iter().enumerate() {
            let (Some(Ok(_)), Some(key)) = (source, key(i)) else {
                continue;
            };
            if let Some(compiled) = cache.get(key).and_then(Weak::upgrade) {
                found[i] = Some(compiled);
            } else if let Some(&j) = first.get(key) {
                copies.push((i, j));
            } else {
                first.insert(key, i);
            }
        }
    }
    let skip: Vec<bool> =
        (0..sources.len()).map(|i| found[i].is_some() || copies.iter().any(|&(c, _)| c == i)).collect();
    let slots: Vec<Mutex<CompiledSlot>> = sources.iter().map(|_| Mutex::new(None)).collect();
    let next = AtomicUsize::new(0);
    let work = || loop {
        let i = next.fetch_add(1, Ordering::Relaxed);
        let Some(source) = sources.get(i) else {
            return;
        };
        if let (Some(source), false) = (source, skip[i]) {
            let compiled = match source {
                Ok(tree) => pattern::compile(tree, word, limits).map(Arc::new),
                Err(reason) => Err(reason.clone()),
            };
            *slots[i].lock().unwrap_or_else(PoisonError::into_inner) = Some(compiled);
        }
    };
    let threads = if limits.bounded() { 1 } else { thread::available_parallelism().map_or(1, |n| n.get()).min(8) };
    thread::scope(|scope| {
        for _ in 1..threads {
            // Fil refusé par le système : le fil courant fait le travail / thread refused: this one works.
            if thread::Builder::new().spawn_scoped(scope, work).is_err() {
                break;
            }
        }
        work();
    });
    let mut out: Vec<CompiledSlot> =
        slots.into_iter().map(|slot| slot.into_inner().unwrap_or_else(PoisonError::into_inner)).collect();
    for (i, compiled) in found.into_iter().enumerate() {
        if let Some(compiled) = compiled {
            out[i] = Some(Ok(compiled));
        }
    }
    for &(i, j) in &copies {
        out[i] = out[j].clone();
    }
    if share {
        let mut cache = compiled_patterns().lock().unwrap_or_else(PoisonError::into_inner);
        cache.retain(|_, compiled| compiled.strong_count() > 0); // analyseurs disparus / dropped scanners
        for (key, &i) in &first {
            if let Some(Some(Ok(compiled))) = out.get(i) {
                cache.insert((*key).to_owned(), Arc::downgrade(compiled));
            }
        }
    }
    out
}

/// Motifs des packs compilés, par clé (`_spec`), tant qu'un analyseur les garde : un seul exemplaire par
/// processus. Compiled pack patterns by key, while a scanner keeps them: one copy per process.
fn compiled_patterns() -> &'static Mutex<HashMap<String, Weak<Compiled>>> {
    static PATTERNS: OnceLock<Mutex<HashMap<String, Weak<Compiled>>>> = OnceLock::new();
    PATTERNS.get_or_init(Mutex::default)
}

fn left_ok(boundary: Boundary, text: &str, byte: usize, classes: &Classes) -> bool {
    let Some(c) = char_before(text, byte) else {
        return true;
    };
    let alnum = classes.is_alnum(c);
    match boundary {
        Boundary::Alnum => !alnum,
        Boundary::Word => !(alnum || "_.%+-".contains(c)),
        Boundary::Ip => !(alnum || c == '.'),
        Boundary::Hex => !(alnum || c == ':'),
        Boundary::Phone => !(alnum || c == '+'),
        Boundary::Digit => !classes.is_digit(c),
        Boundary::Group => {
            !(alnum
                || (group_separator(c) && char_before(text, byte - c.len_utf8()).is_some_and(|p| classes.is_digit(p))))
        }
        Boundary::None => true,
    }
}

/// Reprise après un échec : chaque position suivante du même mot a un prédécesseur qui ferait échouer
/// `left_ok` ; on saute donc le mot entier (comme `_next_start` en Python), résultat identique.
/// Retry after a failure: every later position in the same run would fail `left_ok`, so skip the run.
fn next_start(boundary: Boundary, text: &str, byte: usize, classes: &Classes) -> usize {
    let next = next_char_boundary(text, byte);
    let flag = match boundary {
        Boundary::Alnum => ALNUM,
        Boundary::Digit => DIGIT,
        _ => return next,
    };
    let end =
        text[byte..].char_indices().find(|&(_, c)| classes.flags(c) & flag == 0).map_or(text.len(), |(i, _)| byte + i);
    end.max(next)
}

fn right_ok(boundary: Boundary, text: &str, byte: usize, classes: &Classes) -> bool {
    let Some(c) = char_at(text, byte) else {
        return true;
    };
    let alnum = classes.is_alnum(c);
    match boundary {
        Boundary::Alnum | Boundary::Phone => !alnum,
        Boundary::Word => !(alnum || c == '_'),
        Boundary::Ip => !alnum && !(c == '.' && char_at(text, byte + 1).is_some_and(|n| classes.is_digit(n))),
        Boundary::Hex => !(alnum || c == ':'),
        Boundary::Digit => !classes.is_digit(c),
        Boundary::Group => {
            !(alnum || (group_separator(c) && char_at(text, byte + c.len_utf8()).is_some_and(|n| classes.is_digit(n))))
        }
        Boundary::None => true,
    }
}

/// Cellule de tableau Markdown et groupes de contexte de son en-tête de colonne.
/// Markdown table cell and the context groups of its column header.
pub struct Zone {
    pub start: usize,
    pub end: usize,
    pub groups: Vec<u32>,
}

pub struct Context<'a> {
    pub hits: &'a Hits,
    pub segments: Option<&'a [(usize, usize)]>,
    pub forced: Option<&'a [Vec<u32>]>,
    /// Triées et disjointes / sorted and disjoint.
    pub zones: &'a [Zone],
    /// Union des groupes des zones / union of the zones' groups.
    pub zone_groups: &'a [u32],
}

impl Context<'_> {
    fn segment(&self, pos: usize) -> (i64, usize, usize) {
        match self.segments {
            None => (-1, 0, usize::MAX),
            Some(segments) => {
                let index = segments.partition_point(|s| s.0 <= pos).saturating_sub(1);
                // Liste vide : aucun segment, sans panique / empty list: no segment, no panic.
                segments.get(index).map_or((-1, 0, usize::MAX), |&(lo, hi)| (index as i64, lo, hi))
            }
        }
    }

    fn any_context(&self, groups: &[u32]) -> bool {
        if groups.iter().any(|&g| self.hits.count(g) > 0 || self.zone_groups.contains(&g)) {
            return true;
        }
        self.forced.is_some_and(|forced| forced.iter().any(|f| groups.iter().any(|g| f.contains(g))))
    }

    /// Contexte imposé par un en-tête de colonne (classeur ou tableau Markdown) / column-header context.
    fn header_context(&self, groups: &[u32], index: i64, start: usize, end: usize) -> bool {
        // Ensemble absent (liste plus courte que les segments) : aucun en-tête, sans panique / missing set: none.
        let forced = self.forced.zip(usize::try_from(index).ok()).and_then(|(forced, index)| forced.get(index));
        if forced.is_some_and(|forced| groups.iter().any(|g| forced.contains(g))) {
            return true;
        }
        let i = self.zones.partition_point(|z| z.start <= start);
        i > 0 && end <= self.zones[i - 1].end && groups.iter().any(|g| self.zones[i - 1].groups.contains(g))
    }

    fn near(&self, groups: &[u32], start: usize, end: usize, before: usize, after: usize) -> bool {
        self.near_within(groups, start, end, before, after, (0, usize::MAX))
    }

    /// `DetectionContext.near` avec `lo`/`hi` : recherche bornée en plus (ligne, paragraphe) / further bounded.
    fn near_within(
        &self,
        groups: &[u32],
        start: usize,
        end: usize,
        before: usize,
        after: usize,
        (lo, hi): (usize, usize),
    ) -> bool {
        let (index, seg_lo, seg_hi) = self.segment(start);
        let (lo, hi) = (lo.max(seg_lo), hi.min(seg_hi));
        self.header_context(groups, index, start, end)
            || groups.iter().any(|&g| self.hits.near(g, start, end, before, after, lo, hi))
    }

    /// `Anonymizer._civil_status` : état civil d'une personne physique à côté du numéro, sans personne morale plus
    /// près. Ligne du numéro d'abord (une personne morale l'emporte, sinon l'état civil suffit), puis le paragraphe.
    /// A natural person's civil status next to the number, with no closer legal entity: the number's line first,
    /// then its paragraph. `bytes`/`chars` : bornes du numéro / the number's bounds.
    fn civil_status(&self, settings: &Settings, text: &str, bytes: (usize, usize), chars: (usize, usize)) -> bool {
        let (start, end) = chars;
        let (person, entity) = (settings.person_groups, settings.entity_groups);
        let (before, after) = NATURAL_PERSON_WINDOW;
        let (entity_before, entity_after) = LEGAL_ENTITY_WINDOW;
        let line = line_bounds(text, bytes, chars, before, after);
        if !entity.is_empty() && self.near_within(entity, start, end, entity_before, entity_after, line) {
            return false;
        }
        if self.near_within(person, start, end, before, after, line) {
            return true;
        }
        let block = block_bounds(text, bytes, chars, before, after);
        self.near_within(person, start, end, before, after, block)
            && !(!entity.is_empty() && self.near_within(entity, start, end, entity_before, entity_after, block))
    }

    /// Même règle que `DetectionContext.vetoed` (Python) / same rule as the Python version.
    fn vetoed(&self, groups: &[u32], vetoes: &[u32], start: usize, end: usize, after: usize) -> bool {
        let (index, lo, hi) = self.segment(start);
        if self.header_context(groups, index, start, end) {
            return false;
        }
        let keyword = groups.iter().filter_map(|&g| self.hits.last_end(g, start, lo)).max();
        let veto = vetoes.iter().filter_map(|&g| self.hits.last_end(g, start, lo)).max();
        let veto_wins = veto.is_some_and(|v| keyword.is_none_or(|k| v > k));
        if groups.iter().any(|&g| self.hits.near(g, start, end, 0, after, lo, hi)) {
            // Mot-clé après la valeur : seul un mot-veto collé devant l'annule / a keyword after the value: only a
            // veto word right before the value cancels it.
            return veto_wins && veto.is_some_and(|v| start - v <= VETO_ADJACENT);
        }
        veto_wins
    }
}

/// `engine._VETO_ADJACENT` : écart maximal entre un mot-veto et la valeur quand le mot-clé suit la valeur
/// (« hospitalisée le 14/09/2026, née le … ») / largest gap between a veto word and the value when the keyword
/// follows the value.
const VETO_ADJACENT: usize = 4;

/// Correspondance : bornes entières et bornes de la zone (groupe capturé) / whole match and span bounds.
struct Candidate {
    full: (usize, usize),
    part: Option<(usize, usize)>,
}

/// Recherche d'un motif, bornée à une plage du texte ; les assertions voient tout le texte.
/// One pattern's search, bounded to a range of the text; assertions see the whole text.
struct Search<'r> {
    rec: &'r Recognizer,
    /// Groupes, si un groupe ou le suffixe consommé est lu / groups, when a group or the consumed suffix is read.
    captures: Option<Captures>,
    /// Groupes de l'expression ancrée au début du texte / groups of the expression anchored at the text start.
    start_captures: Option<Captures>,
}

/// Position `count` caractères après l'octet `byte`, bornée au texte / `count` characters after `byte`, clamped.
fn advance(text: &str, byte: usize, count: usize) -> usize {
    if count == usize::MAX {
        return text.len(); // suffixe non borné / unbounded suffix
    }
    text.get(byte..).map_or(text.len(), |rest| rest.char_indices().nth(count).map_or(text.len(), |(i, _)| byte + i))
}

impl<'r> Search<'r> {
    fn new(rec: &'r Recognizer) -> Self {
        let pattern = &rec.pattern;
        let needed = pattern.post.is_some() || !matches!(rec.group, Group::Whole);
        Self {
            rec,
            captures: needed.then(|| pattern.regex.create_captures()),
            start_captures: needed.then(|| pattern.at_start.as_ref().map(Regex::create_captures)).flatten(),
        }
    }

    /// Correspondance de Python commençant à partir de `start`, dans la plage `[start, end)` ; le caractère qui
    /// précède `start` et le suffixe consommé peuvent déborder de la plage. Python's match starting from `start`,
    /// within `[start, end)`; the character before `start` and the consumed suffix may lie outside the range.
    fn find(&mut self, text: &str, start: usize, end: usize) -> Option<Candidate> {
        // La plage étendue au suffixe pourrait accueillir le début d'une correspondance au-delà de `end`, tronquée :
        // elle sera cherchée dans sa propre plage. The range extended for the suffix could host a truncated match
        // starting beyond `end`: it is searched within its own range.
        self.find_extended(text, start, end).filter(|candidate| candidate.full.0 <= end)
    }

    fn find_extended(&mut self, text: &str, start: usize, end: usize) -> Option<Candidate> {
        let rec = self.rec;
        let pattern = &rec.pattern;
        let limit = match pattern.post {
            Some((_, extent)) => advance(text, end, extent),
            None => end,
        };
        let run = |regex: &Regex, captures: Option<&mut Captures>, input: Input, previous: bool| {
            Self::run(regex, captures, rec, text, input, previous)
        };
        if !pattern.prefixed {
            return run(&pattern.regex, self.captures.as_mut(), Input::new(text).span(start..limit), false);
        }
        // Début du texte : sans caractère précédent, la correspondance de Python est essayée ancrée en 0, d'abord.
        // Text start: without a previous character, Python's match is tried anchored at 0, first.
        if start == 0 {
            if let Some(at_start) = &pattern.at_start {
                let input = Input::new(text).span(0..limit).anchored(Anchored::Yes);
                if let Some(found) = run(at_start, self.start_captures.as_mut(), input, false) {
                    return Some(found);
                }
            }
        }
        // Ailleurs : l'expression consomme le caractère précédent, la correspondance commence juste après.
        // Elsewhere: the expression consumes the previous character, the match starts right after it.
        let input = Input::new(text).span(previous_char_boundary(text, start)..limit);
        run(&pattern.regex, self.captures.as_mut(), input, true)
    }

    /// `previous` : la correspondance commence par le caractère précédent, hors de celle de Python ; un groupe
    /// ouvert avant elle commence en fait au début de celle de Python. `previous`: the match starts with the
    /// previous character, outside Python's match; a group opened before it actually starts where Python's does.
    fn run(
        regex: &Regex,
        captures: Option<&mut Captures>,
        rec: &Recognizer,
        text: &str,
        input: Input,
        previous: bool,
    ) -> Option<Candidate> {
        let python_start = |start: usize| if previous { next_char_boundary(text, start) } else { start };
        let Some(captures) = captures else {
            let m = regex.search(&input)?;
            let start = python_start(m.start());
            return Some(Candidate { full: (start, m.end()), part: Some((start, m.end())) });
        };
        regex.search_captures(&input, captures);
        let whole = captures.get_match()?;
        let start = python_start(whole.start());
        // Fin de la correspondance de Python : début du suffixe consommé / end of Python's match.
        let end = match rec.pattern.post {
            Some((index, _)) => captures.get_group(index)?.start,
            None => whole.end(),
        };
        let part = match &rec.group {
            Group::Index(i) => captures.get_group(*i),
            Group::Name(name) => captures.get_group_by_name(name),
            Group::Whole => None,
        };
        let part = match part {
            Some(span) => {
                let first = span.start.max(start);
                Some((first, span.end.max(first)))
            }
            None if matches!(rec.group, Group::Whole) => Some((start, end)),
            None => None,
        };
        Some(Candidate { full: (start, end), part })
    }
}

/// Préfiltre résolu : chiffre ASCII dans le texte, ou sous-chaînes du texte replié (indices dans
/// `Literals`). Resolved prefilter: an ASCII digit in the text, or substrings of the folded text.
struct Gate {
    open: bool,
    digit: bool,
    literals: Vec<usize>,
}

/// Sous-chaînes de tous les préfiltres, cherchées en un seul passage Aho-Corasick.
/// Every prefilter's substrings, searched in a single Aho-Corasick pass.
struct Literals {
    strings: Vec<String>,
    automaton: Option<AhoCorasick>,
}

impl Literals {
    /// Présence de chaque sous-chaîne, comme `feature in folded` (Python) / presence, as in Python.
    fn present(&self, folded: &str) -> Vec<bool> {
        let mut present = vec![false; self.strings.len()];
        match &self.automaton {
            Some(automaton) => {
                for m in automaton.find_overlapping_iter(folded) {
                    present[m.pattern().as_usize()] = true;
                }
            }
            None => present.iter_mut().zip(&self.strings).for_each(|(p, s)| *p = folded.contains(s.as_str())),
        }
        present
    }
}

pub struct Scanner {
    /// None : motif non pris en charge, laissé à Python / unsupported pattern, left to Python.
    recognizers: Vec<Option<Recognizer>>,
    pub keywords: KeywordIndex,
    windows: WindowIndex,
    plans: Vec<Option<Plan>>,
    gates: Vec<Gate>,
    literals: Literals,
}

impl Scanner {
    pub fn new(mut recognizers: Vec<Option<Recognizer>>, keywords: KeywordIndex) -> Self {
        let shapes = recognizers.iter_mut().map(|rec| rec.as_mut().and_then(|rec| rec.shape.take()));
        let (windows, plans) = WindowIndex::new(shapes);
        let mut strings: Vec<String> = Vec::new();
        let gates = recognizers
            .iter()
            .map(|rec| match rec.as_ref().map(|rec| &rec.prefilter) {
                Some(Prefilter::Digit) => Gate { open: false, digit: true, literals: Vec::new() },
                Some(Prefilter::Any(parts)) => {
                    let mut gate = Gate { open: false, digit: false, literals: Vec::new() };
                    for part in parts {
                        if part == "digit" {
                            gate.digit = true;
                        } else {
                            let index = strings.iter().position(|s| s == part).unwrap_or_else(|| {
                                strings.push(part.clone());
                                strings.len() - 1
                            });
                            gate.literals.push(index);
                        }
                    }
                    gate
                }
                _ => Gate { open: true, digit: false, literals: Vec::new() },
            })
            .collect();
        let automaton = AhoCorasick::builder().match_kind(aho_corasick::MatchKind::Standard).build(&strings).ok();
        Self { recognizers, keywords, windows, plans, gates, literals: Literals { strings, automaton } }
    }

    /// `windowed = false` : balayage complet, référence des tests différentiels / full scan, test reference.
    pub fn scan(
        &self,
        text: &str,
        folded: &str,
        ctx: &Context,
        settings: &Settings,
        classes: &Classes,
        windowed: bool,
    ) -> Vec<Found> {
        let has_digit = text.bytes().any(|b| b.is_ascii_digit());
        // Sous-chaînes des préfiltres, cherchées une fois au premier besoin / searched once, when first needed.
        let mut present: Option<Vec<bool>> = None;
        // Motifs à lancer (préfiltre et contexte passés) / patterns to run (prefilter and context passed).
        let mut todo: Vec<(usize, &Recognizer, Option<Plan>)> = Vec::new();
        let mut need: Mask = 0;
        for (rec_index, ((rec, plan), gate)) in self.recognizers.iter().zip(&self.plans).zip(&self.gates).enumerate() {
            let Some(rec) = rec else {
                continue;
            };
            if !settings.active.get(rec_index).copied().unwrap_or(false) {
                continue;
            }
            let passes = gate.open
                || (gate.digit && has_digit)
                || (!gate.literals.is_empty() && {
                    let present = present.get_or_insert_with(|| self.literals.present(folded));
                    gate.literals.iter().any(|&i| present[i])
                });
            if !passes {
                continue;
            }
            let needs_context = rec.tier == Tier::C || (rec.tier == Tier::B && !settings.strict);
            if needs_context && !ctx.any_context(&rec.contexts) {
                continue;
            }
            let plan = plan.filter(|_| windowed);
            need |= plan.map_or(0, |plan| plan.mask());
            todo.push((rec_index, rec, plan));
        }
        let windows = self.windows.windows(text, need);
        let index = CharIndex::new(text);
        let mut found = Vec::new();
        let mut spans: Vec<(usize, usize)> = Vec::new();
        for (rec_index, rec, plan) in todo {
            let ranges = match plan {
                Some(plan) => {
                    spans.clear();
                    spans.extend(windows.of(&plan));
                    if spans.is_empty() {
                        continue;
                    }
                    &spans[..]
                }
                None => &[(0, text.len())][..],
            };
            Self::run(rec_index, rec, text, ranges, &index, ctx, settings, classes, &mut found);
        }
        found
    }

    /// `ranges` : plages triées et disjointes où chercher / sorted, disjoint ranges to search.
    #[allow(clippy::too_many_arguments)]
    fn run(
        rec_index: usize,
        rec: &Recognizer,
        text: &str,
        ranges: &[(usize, usize)],
        index: &CharIndex,
        ctx: &Context,
        settings: &Settings,
        classes: &Classes,
        out: &mut Vec<Found>,
    ) {
        let needs_context = matches!(rec.tier, Tier::B | Tier::C);
        let mut search = Search::new(rec);
        let mut range = 0;
        let mut pos = 0usize;
        loop {
            // Prochaine correspondance à partir de `pos`, plage après plage / next match from `pos`.
            let mut candidate = None;
            while let Some(&(start, end)) = ranges.get(range) {
                if pos > end {
                    range += 1;
                    continue;
                }
                candidate = search.find(text, pos.max(start), end);
                if candidate.is_some() {
                    break;
                }
                range += 1;
            }
            let Some(Candidate { full: (full_start, full_end), part }) = candidate else {
                return;
            };
            // Bornes de la zone : correspondance entière ou groupe capturé / whole match or captured group.
            let Some((start, end)) = part else {
                pos = next_char_boundary(text, full_start);
                continue;
            };
            if !(left_ok(rec.boundary, text, full_start, classes) && right_ok(rec.boundary, text, full_end, classes)) {
                pos = next_start(rec.boundary, text, full_start, classes);
                continue;
            }
            let candidate = &text[start..end];
            let (c_start, c_end) = (index.to_char(start), index.to_char(end));
            let mut score = rec.score;
            let value = match rec.validator {
                Some(validate) => match validate(candidate) {
                    Some(v) => Some(v),
                    // Clé fausse : niveau L, ou mot-clé explicite proche / wrong key: tier L, or explicit keyword.
                    None if rec.tier == Tier::L
                        || (rec.fallback && ctx.near(&rec.contexts, c_start, c_end, rec.before, rec.after)) =>
                    {
                        score *= 0.6;
                        None
                    }
                    None => {
                        pos = next_start(rec.boundary, text, full_start, classes);
                        continue;
                    }
                },
                None => Some(candidate.to_string()),
            };
            let has_context = !rec.contexts.is_empty()
                && ctx.near(&rec.contexts, c_start, c_end, rec.before, rec.after)
                && (rec.vetoes.is_empty() || !ctx.vetoed(&rec.contexts, &rec.vetoes, c_start, c_end, rec.after));
            if needs_context && !has_context {
                if rec.tier == Tier::C || !settings.strict {
                    pos = next_start(rec.boundary, text, full_start, classes);
                    continue;
                }
                score = 0.6;
            } else if has_context {
                score = (score + 0.04).min(1.0);
            }
            // `Anonymizer._personal` : (personnel ?, raison propre) / (personal?, own reason).
            let (personal, reason) = match rec.policy {
                Policy::None => (true, None),
                Policy::Facility => (settings.facility_mask || settings.strict, None),
                Policy::Company => match settings.company_mode {
                    "mask" => (true, None),
                    "keep" => (false, None),
                    _ if settings.strict => (true, None),
                    // « Entrepreneur individuel » n'importe où dans le document suffit : rappel d'abord. L'état civil
                    // d'une personne physique à côté du numéro désigne aussi son titulaire, sauf personne morale
                    // plus près. "Sole trader" anywhere is enough; a natural person's civil status next to the
                    // number also names its holder, unless a legal entity is closer.
                    _ if !settings.ei_groups.is_empty() && ctx.any_context(settings.ei_groups) => {
                        (true, Some(SOLE_TRADER))
                    }
                    _ if !settings.person_groups.is_empty()
                        && ctx.civil_status(settings, text, (start, end), (c_start, c_end)) =>
                    {
                        (true, Some(CIVIL_STATUS))
                    }
                    _ if no_legal_entity(text, start) => (true, Some(NO_LEGAL_ENTITY)),
                    _ => (false, None),
                },
            };
            out.push(Found { start: c_start, end: c_end, recognizer: rec_index, value, score, personal, reason });
            pos = if full_end > full_start { full_end } else { next_char_boundary(text, full_start) };
        }
    }
}

/// `DetectionContext.near` des détecteurs du moteur fusionné, même règle que les motifs / same rule as patterns.
impl Context<'_> {
    pub(crate) fn near_groups(&self, groups: &[u32], start: usize, end: usize, before: usize, after: usize) -> bool {
        self.near(groups, start, end, before, after)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn empty() -> Source {
        Some(Ok(Tree { groups: 0, names: Vec::new(), nodes: Vec::new() }))
    }

    fn shared(slot: &CompiledSlot) -> Arc<Compiled> {
        Arc::clone(slot.as_ref().and_then(|r| r.as_ref().ok()).expect("compiled"))
    }

    #[test]
    fn pack_patterns_are_compiled_once_per_process() {
        let (word, trusted) = (ClassUnicode::empty(), pattern::Limits::trusted());
        let keys = [Some("test:shared".to_owned()), Some("test:shared".to_owned()), None];
        let sources = [empty(), empty(), empty()];
        let first = compile_all(&sources, &keys, &word, &trusted);
        let second = compile_all(&sources[..1], &keys[..1], &word, &trusted);
        // Même clé : un seul exemplaire, dans le jeu et d'un analyseur à l'autre / one copy, within and across sets.
        assert!(Arc::ptr_eq(&shared(&first[0]), &shared(&first[1])));
        assert!(Arc::ptr_eq(&shared(&first[0]), &shared(&second[0])));
        // Sans clé, ou jeu borné (règles non sûres) : jamais partagé / no key, or bounded set: never shared.
        assert!(!Arc::ptr_eq(&shared(&first[0]), &shared(&first[2])));
        let untrusted = compile_all(&sources[..1], &keys[..1], &word, &pattern::Limits::untrusted());
        assert!(!Arc::ptr_eq(&shared(&first[0]), &shared(&untrusted[0])));
        // Plus aucun analyseur : l'exemplaire est libéré / no scanner left: the copy is freed.
        let weak = Arc::downgrade(&shared(&first[0]));
        drop((first, second));
        assert!(weak.upgrade().is_none());
        let again = compile_all(&sources[..1], &keys[..1], &word, &trusted);
        assert!(again[0].as_ref().is_some_and(Result::is_ok));
    }
}
