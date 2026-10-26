//! Mots-clés de contexte : un passage Aho-Corasick sur le texte replié / context keywords, one pass.
//!
//! Les mots sont repliés par Python (même table que `gdprguardian._text.fold`) pour garantir l'identité.
//! Words are folded by Python (same table as `gdprguardian._text.fold`) to guarantee identical results.

use std::collections::HashMap;

use aho_corasick::{AhoCorasick, AhoCorasickKind, MatchKind};

use crate::text::{char_at, char_before, Classes};

pub const MAX_KEYWORD_LEN: usize = 64;

pub struct KeywordIndex {
    automaton: Option<AhoCorasick>,
    pattern_groups: Vec<Vec<u32>>,
    /// Longueur de chaque mot en caractères / each word's length in characters.
    pattern_chars: Vec<u32>,
    check_left: Vec<bool>,
    check_right: Vec<bool>,
    pub group_names: Vec<String>,
    pub group_ids: HashMap<String, u32>,
}

/// Positions de caractères au fil de fins croissantes, sans table / character positions along increasing ends.
struct CharCursor<'t> {
    text: &'t str,
    ascii: bool,
    byte: usize,
    char: usize,
}

impl CharCursor<'_> {
    fn advance(&mut self, byte: usize) -> usize {
        if self.ascii {
            return byte;
        }
        if byte < self.byte {
            (self.byte, self.char) = (0, 0);
        }
        // Octets de tête UTF-8 : un par caractère / UTF-8 lead bytes: one per character.
        self.char += self.text.as_bytes()[self.byte..byte].iter().filter(|&&b| (b as i8) >= -0x40).count();
        self.byte = byte;
        self.char
    }
}

impl KeywordIndex {
    /// Mots repliés par Python ; `classes` couvre au moins leurs caractères.
    /// Words folded by Python; `classes` covers at least their characters.
    pub fn new(groups: &[(String, Vec<String>)], classes: &Classes) -> Result<Self, String> {
        let mut group_ids: HashMap<String, u32> = HashMap::new();
        let mut group_names = Vec::new();
        let mut patterns: Vec<String> = Vec::new();
        let mut pattern_index: HashMap<String, usize> = HashMap::new();
        let mut pattern_groups: Vec<Vec<u32>> = Vec::new();
        for (group, words) in groups {
            let gid = *group_ids.entry(group.clone()).or_insert_with(|| {
                group_names.push(group.clone());
                (group_names.len() - 1) as u32
            });
            for word in words {
                let word = word.trim();
                if word.is_empty() {
                    continue;
                }
                let index = *pattern_index.entry(word.to_string()).or_insert_with(|| {
                    patterns.push(word.to_string());
                    pattern_groups.push(Vec::new());
                    patterns.len() - 1
                });
                if !pattern_groups[index].contains(&gid) {
                    pattern_groups[index].push(gid);
                }
            }
        }
        let alnum = |c: char| classes.is_alnum(c);
        let check_left = patterns.iter().map(|p| p.chars().next().is_some_and(alnum)).collect();
        let check_right = patterns.iter().map(|p| p.chars().next_back().is_some_and(alnum)).collect();
        let pattern_chars = patterns.iter().map(|p| p.chars().count() as u32).collect();
        let automaton = if patterns.is_empty() {
            None
        } else {
            // DFA : 3 à 4x plus rapide que l'automate par défaut en recherche chevauchante, quelques centaines
            // de Ko ; repli sur le choix par défaut s'il est trop gros. DFA: 3-4x faster than the default
            // automaton for overlapping search, a few hundred KB; default choice if it is too large.
            let builder = |kind| AhoCorasick::builder().match_kind(MatchKind::Standard).kind(kind).build(&patterns);
            Some(builder(Some(AhoCorasickKind::DFA)).or_else(|_| builder(None)).map_err(|e| e.to_string())?)
        };
        Ok(Self { automaton, pattern_groups, pattern_chars, check_left, check_right, group_names, group_ids })
    }

    /// Occurrences par groupe, en positions de caractères / per-group hits in character offsets.
    pub fn scan(&self, folded: &str, classes: &Classes) -> Hits {
        let mut hits = Hits::new(self.group_names.len());
        let Some(automaton) = &self.automaton else {
            return hits;
        };
        // Fins croissantes en recherche chevauchante : un curseur suffit / increasing ends: a cursor suffices.
        let mut cursor = CharCursor { text: folded, ascii: folded.is_ascii(), byte: 0, char: 0 };
        let alnum = |c: char| classes.is_alnum(c);
        for m in automaton.find_overlapping_iter(folded) {
            let pattern = m.pattern().as_usize();
            if self.check_left[pattern] && char_before(folded, m.start()).is_some_and(alnum) {
                continue;
            }
            if self.check_right[pattern] && char_at(folded, m.end()).is_some_and(alnum) {
                continue;
            }
            let end = cursor.advance(m.end()) as u32;
            let start = end - self.pattern_chars[pattern];
            for &gid in &self.pattern_groups[pattern] {
                hits.add(gid, start, end);
            }
        }
        hits.finalize();
        hits
    }
}

/// Occurrences triées par groupe / per-group sorted occurrences.
#[derive(Clone, Default)]
pub struct Hits {
    starts: Vec<Vec<u32>>,
    ends: Vec<Vec<u32>>,
}

impl Hits {
    pub fn new(groups: usize) -> Self {
        Self { starts: vec![Vec::new(); groups], ends: vec![Vec::new(); groups] }
    }

    fn add(&mut self, gid: u32, start: u32, end: u32) {
        self.starts[gid as usize].push(start);
        self.ends[gid as usize].push(end);
    }

    fn finalize(&mut self) {
        for gid in 0..self.starts.len() {
            let starts = &self.starts[gid];
            if starts.windows(2).any(|w| w[0] > w[1]) {
                let mut pairs: Vec<(u32, u32)> = starts.iter().copied().zip(self.ends[gid].iter().copied()).collect();
                pairs.sort_unstable();
                self.starts[gid] = pairs.iter().map(|p| p.0).collect();
                self.ends[gid] = pairs.iter().map(|p| p.1).collect();
            }
        }
    }

    pub fn count(&self, gid: u32) -> usize {
        self.starts.get(gid as usize).map_or(0, Vec::len)
    }

    pub fn occurrences(&self, gid: u32) -> impl Iterator<Item = (u32, u32)> + '_ {
        self.starts[gid as usize].iter().copied().zip(self.ends[gid as usize].iter().copied())
    }

    /// Fin du dernier mot-clé fini avant `pos` (début ≥ `lo`), comme `KeywordHits.last_end` (Python).
    /// End of the last keyword finished before `pos` (start ≥ `lo`), as in the Python version.
    pub fn last_end(&self, gid: u32, pos: usize, lo: usize) -> Option<usize> {
        let starts = self.starts.get(gid as usize)?;
        let ends = &self.ends[gid as usize];
        let mut best: Option<usize> = None;
        let mut i = starts.partition_point(|&s| s as usize <= pos);
        while i > 0 {
            i -= 1;
            let (start, end) = (starts[i] as usize, ends[i] as usize);
            if start < lo || best.is_some_and(|b| start + MAX_KEYWORD_LEN <= b) {
                break;
            }
            if end <= pos && best.is_none_or(|b| end > b) {
                best = Some(end);
            }
        }
        best
    }

    /// Même algorithme que `KeywordHits.near` (Python) / same algorithm as the Python version.
    #[allow(clippy::too_many_arguments)]
    pub fn near(&self, gid: u32, start: usize, end: usize, before: usize, after: usize, lo: usize, hi: usize) -> bool {
        let Some(starts) = self.starts.get(gid as usize) else {
            return false;
        };
        let ends = &self.ends[gid as usize];
        let left = start.saturating_sub(before).max(lo) as i64;
        // Sans débordement ; borné à u32::MAX, ce qui ne change rien (positions en u32).
        // No overflow; capped at u32::MAX, which changes nothing (positions are u32).
        let right = end.saturating_add(after).min(hi).min(u32::MAX as usize) as u32;
        let mut i = starts.partition_point(|&s| s <= right) as i64 - 1;
        while i >= 0 {
            let hit_start = starts[i as usize] as i64;
            if hit_start < left - MAX_KEYWORD_LEN as i64 {
                return false;
            }
            if ends[i as usize] as i64 >= left && hit_start >= lo as i64 {
                return true;
            }
            i -= 1;
        }
        false
    }
}
