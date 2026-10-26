//! Fenêtres de recherche : chaque motif ne parcourt que les passages où il peut correspondre.
//!
//! Search windows: each pattern only scans the stretches of text where it can match.
//!
//! Preuve / proof. Tout caractère consommé par une correspondance appartient à `allowed` (union des
//! littéraux et classes du motif) et au moins un appartient à `required`. Une correspondance tient donc
//! dans un passage maximal de caractères `allowed` qui contient un caractère `required` et mesure au
//! moins `min_len` octets : une fenêtre. Every character a match consumes is in `allowed` (union of the
//! pattern's literals and classes) and at least one is in `required`, so a match lies inside a maximal
//! run of `allowed` characters holding a `required` one and at least `min_len` bytes long: a window.
//! La recherche bornée à une fenêtre voit tout le texte pour les assertions (`\b`, `^`, `$`) : depuis
//! toute position, elle rend la même correspondance que la recherche complète (le chemin prioritaire de
//! la recherche complète finit dans la fenêtre). A search bounded to a window still sees the whole text
//! for assertions: from any position it returns the same match as the full search (the full search's
//! preferred path ends inside the window).

use regex_syntax::hir::{Class, Hir, HirKind};

/// Groupes distincts au plus (un bit chacun) ; au-delà, balayage complet / at most this many groups.
const MAX_SETS: usize = Mask::BITS as usize;

/// Ensemble de caractères : bits ASCII + intervalles au-delà / character set: ASCII bits + wider ranges.
#[derive(Clone, PartialEq, Eq, Default)]
pub struct CharSet {
    ascii: u128,
    /// Intervalles hors ASCII, triés et fusionnés, bornes incluses / sorted, merged, inclusive.
    wide: Vec<(u32, u32)>,
}

impl CharSet {
    fn add_range(&mut self, lo: u32, hi: u32) {
        for cp in lo..=hi.min(0x7F) {
            self.ascii |= 1 << cp;
        }
        if hi >= 0x80 {
            self.wide.push((lo.max(0x80), hi));
        }
    }

    fn add_char(&mut self, c: char) {
        self.add_range(c as u32, c as u32);
    }

    fn union(&mut self, other: &CharSet) {
        self.ascii |= other.ascii;
        self.wide.extend_from_slice(&other.wide);
        self.normalize();
    }

    fn normalize(&mut self) {
        self.wide.sort_unstable();
        let mut merged: Vec<(u32, u32)> = Vec::with_capacity(self.wide.len());
        for &(lo, hi) in &self.wide {
            match merged.last_mut() {
                Some(last) if lo <= last.1.saturating_add(1) => last.1 = last.1.max(hi),
                _ => merged.push((lo, hi)),
            }
        }
        self.wide = merged;
    }

    /// Classe d'un octet du texte : exacte en ASCII, sinon « un caractère non ASCII quelconque ».
    /// Class of a text byte: exact for ASCII, otherwise "any non-ASCII character".
    fn has_byte(&self, b: u8) -> bool {
        if b < 0x80 {
            self.ascii >> b & 1 == 1
        } else {
            !self.wide.is_empty()
        }
    }

    /// Fréquence estimée dans un texte courant : choisit le caractère requis le plus rare. Tout octet non
    /// ASCII comptant pour un ensemble non ASCII, celui-ci pèse comme les lettres accentuées (~2,5 %).
    /// Estimated frequency in ordinary text: picks the rarest required character. Any non-ASCII byte
    /// counting for a non-ASCII set, such a set weighs as much as accented letters (~2.5%).
    fn weight(&self) -> f64 {
        let ascii: f64 = (0u8..0x80).filter(|&b| self.has_byte(b)).map(ascii_weight).sum();
        ascii + if self.wide.is_empty() { 0.0 } else { 25.0 }
    }

    /// Prose courante : espace et presque toutes les minuscules / ordinary prose: space and most letters.
    fn is_prose(&self) -> bool {
        let lowercase = (b'a'..=b'z').filter(|&b| self.ascii >> b & 1 == 1).count();
        self.ascii >> b' ' & 1 == 1 && lowercase >= 20
    }
}

/// Fréquence approximative pour 1 000 caractères de prose / approximate frequency per 1,000 characters.
fn ascii_weight(b: u8) -> f64 {
    match b {
        b' ' => 160.0,
        b'e' => 120.0,
        b'a' | b'i' | b's' | b'n' | b't' | b'r' | b'u' | b'o' | b'l' => 60.0,
        b'a'..=b'z' | b'\n' => 15.0,
        b'.' | b',' | b'\'' => 10.0,
        b'A'..=b'Z' => 4.0,
        b'0'..=b'9' => 3.0,
        b'-' | b':' | b'(' | b')' | b'/' => 2.0,
        _ => 0.5,
    }
}

/// Forme d'un motif : caractères permis, caractères dont un est requis, longueur minimale (octets).
/// A pattern's shape: allowed characters, characters one of which is required, minimum length (bytes).
#[derive(Clone)]
pub struct Shape {
    allowed: CharSet,
    required: CharSet,
    min_len: usize,
}

/// Forme d'un motif, ou None s'il peut correspondre à vide ou sans caractère requis.
/// A pattern's shape, or None when it may match the empty string or has no required character.
pub fn shape(hir: &Hir) -> Option<Shape> {
    let min_len = hir.properties().minimum_len()?;
    if min_len == 0 {
        return None;
    }
    let mut allowed = CharSet::default();
    if !collect_allowed(hir, &mut allowed) {
        return None;
    }
    allowed.normalize();
    let required = required(hir)?;
    Some(Shape { allowed, required, min_len })
}

fn collect_allowed(hir: &Hir, set: &mut CharSet) -> bool {
    match hir.kind() {
        HirKind::Empty | HirKind::Look(_) => true,
        HirKind::Literal(literal) => match std::str::from_utf8(&literal.0) {
            Ok(text) => {
                text.chars().for_each(|c| set.add_char(c));
                true
            }
            Err(_) => false,
        },
        HirKind::Class(Class::Unicode(class)) => {
            class.iter().for_each(|r| set.add_range(r.start() as u32, r.end() as u32));
            true
        }
        // Octets hors ASCII : pas de caractère sûr / non-ASCII bytes: no safe character.
        HirKind::Class(Class::Bytes(class)) => class.iter().all(|r| {
            set.add_range(u32::from(r.start()), u32::from(r.end()));
            r.end() < 0x80
        }),
        HirKind::Repetition(repetition) => collect_allowed(&repetition.sub, set),
        HirKind::Capture(capture) => collect_allowed(&capture.sub, set),
        HirKind::Concat(subs) | HirKind::Alternation(subs) => subs.iter().all(|sub| collect_allowed(sub, set)),
    }
}

/// Ensemble dont toute correspondance consomme au moins un caractère / every match consumes one of them.
fn required(hir: &Hir) -> Option<CharSet> {
    let rarest = |sets: Vec<CharSet>| sets.into_iter().min_by(|a, b| a.weight().total_cmp(&b.weight()));
    match hir.kind() {
        HirKind::Empty | HirKind::Look(_) => None,
        HirKind::Literal(literal) => {
            let text = std::str::from_utf8(&literal.0).ok()?;
            rarest(
                text.chars()
                    .map(|c| {
                        let mut set = CharSet::default();
                        set.add_char(c);
                        set
                    })
                    .collect(),
            )
        }
        HirKind::Class(Class::Unicode(class)) => {
            let mut set = CharSet::default();
            class.iter().for_each(|r| set.add_range(r.start() as u32, r.end() as u32));
            set.normalize();
            Some(set)
        }
        HirKind::Class(Class::Bytes(class)) => {
            let mut set = CharSet::default();
            for r in class.iter() {
                if r.end() >= 0x80 {
                    return None;
                }
                set.add_range(u32::from(r.start()), u32::from(r.end()));
            }
            Some(set)
        }
        HirKind::Repetition(repetition) if repetition.min >= 1 => required(&repetition.sub),
        HirKind::Repetition(_) => None,
        HirKind::Capture(capture) => required(&capture.sub),
        HirKind::Concat(subs) => rarest(subs.iter().filter_map(required).collect()),
        HirKind::Alternation(subs) => {
            let mut union = CharSet::default();
            for sub in subs {
                union.union(&required(sub)?);
            }
            Some(union)
        }
    }
}

/// Un bit par groupe (ensemble permis, ensemble requis) / one bit per (allowed, required) group.
pub type Mask = u128;

/// Fenêtres d'un motif : son groupe et sa longueur minimale / a pattern's windows: group, minimum length.
#[derive(Clone, Copy)]
pub struct Plan {
    group: usize,
    min_len: usize,
}

impl Plan {
    pub fn mask(&self) -> Mask {
        1 << self.group
    }
}

/// Groupes de tous les motifs, construits une fois / every pattern's groups, built once.
///
/// Le passage lit des octets, pas des caractères : un octet ASCII a ses classes exactes ; tout octet
/// non ASCII reçoit celles d'un caractère non ASCII quelconque (permis ou requis s'il l'est pour un
/// caractère non ASCII). Les fenêtres ne peuvent que grandir, la preuve tient ; les octets d'un même
/// caractère partageant leurs classes, les bornes restent entre deux caractères. The pass reads bytes,
/// not characters: an ASCII byte has its exact classes; every non-ASCII byte gets those of an arbitrary
/// non-ASCII character. Windows can only grow, so the proof holds; since all bytes of a character share
/// their classes, window edges stay between characters.
pub struct WindowIndex {
    /// (permis, requis) distincts / distinct (allowed, required) pairs.
    groups: Vec<(CharSet, CharSet)>,
    /// Plus courte longueur minimale des motifs du groupe / shortest minimum length in the group.
    min_len: Vec<usize>,
    /// Masques (permis, requis) de chaque octet / (allowed, required) masks of each byte.
    bytes: [(Mask, Mask); 256],
}

impl WindowIndex {
    /// Groupes et plans de tous les motifs, en une fois / groups and plans of all patterns, at once.
    pub fn new(shapes: impl IntoIterator<Item = Option<Shape>>) -> (Self, Vec<Option<Plan>>) {
        let mut index = Self { groups: Vec::new(), min_len: Vec::new(), bytes: [(0, 0); 256] };
        let plans = shapes.into_iter().map(|shape| shape.and_then(|shape| index.plan(shape))).collect();
        for (b, entry) in (0..=u8::MAX).zip(index.bytes.iter_mut()) {
            for (k, (allowed, required)) in index.groups.iter().enumerate() {
                entry.0 |= Mask::from(allowed.has_byte(b)) << k;
                entry.1 |= Mask::from(required.has_byte(b)) << k;
            }
        }
        (index, plans)
    }

    /// Fenêtres d'un motif, ou None si elles n'aideraient pas (prose courante, trop de groupes).
    /// A pattern's windows, or None when they would not help (ordinary prose, too many groups).
    fn plan(&mut self, shape: Shape) -> Option<Plan> {
        if shape.allowed.is_prose() {
            return None;
        }
        let pair = (shape.allowed, shape.required);
        let group = match self.groups.iter().position(|g| *g == pair) {
            Some(group) => group,
            None if self.groups.len() < MAX_SETS => {
                self.groups.push(pair);
                self.min_len.push(shape.min_len);
                self.groups.len() - 1
            }
            None => return None,
        };
        self.min_len[group] = self.min_len[group].min(shape.min_len);
        Some(Plan { group, min_len: shape.min_len })
    }

    /// Fenêtres des groupes demandés (positions en octets). Passage avant : un passage est « armé » dès
    /// qu'il contient un caractère requis ; les passages armés fermés attendent. Dès qu'aucun n'est armé,
    /// une seule marche arrière trouve leurs débuts. Windows of the requested groups (byte offsets).
    /// Forward pass: a run is "armed" once it holds a required character; closed armed runs wait. As soon
    /// as none is armed, a single backward walk finds their starts.
    pub fn windows(&self, text: &str, need: Mask) -> Windows {
        // (groupe, début, fin) de toutes les fenêtres, croissantes par groupe / all windows, ascending per group.
        let mut found: Vec<(usize, usize, usize)> = Vec::new();
        if need != 0 {
            // Passages armés fermés : (fin, groupes), fins croissantes / closed armed runs, increasing ends.
            let mut pending: Vec<(usize, Mask)> = Vec::new();
            // Fin du passage de chaque groupe, écrite avant d'être lue / each group's run end, written first.
            let mut ends = [0usize; MAX_SETS];
            let mut armed: Mask = 0;
            let bytes = text.as_bytes();
            for (i, &b) in bytes.iter().enumerate() {
                let (allowed, required) = self.bytes[b as usize];
                let allowed = allowed & need;
                // Cet octet ferme ces passages et n'en fait pas partie / this byte closes these runs.
                let closed = armed & !allowed;
                if closed != 0 {
                    pending.push((i, closed));
                }
                armed = (armed & allowed) | (required & allowed);
                if armed == 0 && !pending.is_empty() {
                    self.resolve(bytes, &mut pending, &mut ends, &mut found);
                }
            }
            if armed != 0 {
                pending.push((bytes.len(), armed));
            }
            self.resolve(bytes, &mut pending, &mut ends, &mut found);
        }
        Windows::by_group(found, self.groups.len())
    }

    /// Débuts des passages en attente, en une marche arrière depuis la dernière fin. Chaque position est
    /// parcourue au plus une fois par groupe : coût linéaire. Starts of the pending runs, in one backward
    /// walk from the last end. Each position is walked at most once per group: linear cost.
    fn resolve(
        &self,
        bytes: &[u8],
        pending: &mut Vec<(usize, Mask)>,
        ends: &mut [usize; MAX_SETS],
        found: &mut Vec<(usize, usize, usize)>,
    ) {
        let Some(&(top, _)) = pending.last() else {
            return;
        };
        let first = found.len();
        let mut alive: Mask = 0;
        for j in (0..top).rev() {
            // Passages qui contiennent cet octet : leur fin est après lui / runs holding this byte.
            while let Some(&(end, groups)) = pending.last().filter(|&&(end, _)| end > j) {
                pending.pop();
                Self::each(groups, |k| ends[k] = end);
                alive |= groups;
            }
            let allowed = self.bytes[bytes[j] as usize].0;
            let ended = alive & !allowed;
            if ended != 0 {
                Self::each(ended, |k| self.push(k, j + 1, ends[k], found));
                alive &= allowed;
            }
            if alive == 0 && pending.is_empty() {
                break;
            }
        }
        Self::each(alive, |k| self.push(k, 0, ends[k], found));
        // Trouvées à rebours : remises dans l'ordre / found backwards: put back in order.
        found[first..].reverse();
    }

    #[inline]
    fn each(mut groups: Mask, mut f: impl FnMut(usize)) {
        while groups != 0 {
            f(groups.trailing_zeros() as usize);
            groups &= groups - 1;
        }
    }

    fn push(&self, k: usize, start: usize, end: usize, found: &mut Vec<(usize, usize, usize)>) {
        if end - start >= self.min_len[k] {
            found.push((k, start, end));
        }
    }
}

/// Fenêtres d'un texte, rangées par groupe, triées et disjointes / a text's windows by group, sorted.
pub struct Windows {
    /// Fenêtres du groupe k : `spans[offsets[k]..offsets[k + 1]]` / group k's windows.
    offsets: Vec<usize>,
    spans: Vec<(usize, usize)>,
}

impl Windows {
    /// Tri par dénombrement, stable : l'ordre croissant de chaque groupe est gardé.
    /// Stable counting sort: each group's ascending order is kept.
    fn by_group(found: Vec<(usize, usize, usize)>, groups: usize) -> Self {
        let mut offsets = vec![0usize; groups + 1];
        for &(k, _, _) in &found {
            offsets[k + 1] += 1;
        }
        for k in 0..groups {
            offsets[k + 1] += offsets[k];
        }
        let mut next = offsets.clone();
        let mut spans = vec![(0, 0); found.len()];
        for (k, start, end) in found {
            spans[next[k]] = (start, end);
            next[k] += 1;
        }
        Self { offsets, spans }
    }

    /// Fenêtres (début, fin) d'un plan / a plan's (start, end) windows.
    pub fn of(&self, plan: &Plan) -> impl Iterator<Item = (usize, usize)> + '_ {
        let min_len = plan.min_len;
        let range = match (self.offsets.get(plan.group), self.offsets.get(plan.group + 1)) {
            (Some(&lo), Some(&hi)) => lo..hi,
            _ => 0..0,
        };
        self.spans[range].iter().copied().filter(move |(start, end)| end - start >= min_len)
    }
}
