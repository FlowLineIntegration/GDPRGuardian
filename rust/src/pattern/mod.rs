//! Compilateur des motifs Python pour le moteur linéaire, sémantique exacte de `re`.
//!
//! Compiler of Python patterns for the linear-time engine, with `re`'s exact semantics.
//! Le motif n'est pas relu par une autre grammaire : Python transmet l'arbre de `re` lui-même
//! (`gdprguardian._native.syntax`), drapeaux résolus. Les classes `\w`, `\d`, `\s` viennent de la table Unicode du
//! noyau (prédicats de Python), `re.IGNORECASE` de `re`, et les look-arounds de tête et de fin deviennent du
//! contexte consommé (`context`). Une construction hors de ces formes exactes est refusée, avec sa raison : le
//! moteur Python, la référence, la traite. The pattern is never re-read with another grammar: Python sends
//! `re`'s own tree, flags resolved. `\w`, `\d`, `\s` come from the core's Unicode table (Python's predicates),
//! `re.IGNORECASE` from `re`, and leading and trailing look-arounds become consumed context. Anything outside
//! these exact forms is refused with its reason: the reference Python engine handles it.
//! Règles non sûres (reçues avec une requête) : compilées sous bornes (`Limits::untrusted`), refusées avant
//! d'allouer au-delà. Untrusted rules (received with a request): compiled under bounds, refused before
//! allocating beyond them.

mod context;
mod hir;
mod node;

use std::sync::{Mutex, PoisonError};

use regex_automata::meta::{self, Regex};
use regex_syntax::hir::{ClassUnicode, Hir};

pub use node::{read, Sets, Tree};

use crate::windows::{self, Shape};

/// Cache du DFA paresseux par motif et par fil, alloué à la demande. À 2 Mo (défaut du crate `regex`), le
/// NIR (suites de chiffres) vide son cache sans cesse et retombe sur le PikeVM : 10x plus lent.
/// Per-pattern, per-thread lazy DFA cache, allocated on demand. At 2 MB (the `regex` default), the NIR
/// pattern (digit runs) keeps clearing it and falls back to the PikeVM: 10x slower.
const DFA_CACHE: usize = 16 * (1 << 20);
/// Motifs de confiance (packs intégrés, fichier local) : taille maximale de chaque automate d'une expression.
/// Trusted patterns (built-in packs, local file): largest automaton of one expression.
const TRUSTED_NFA: usize = 32 * (1 << 20);
/// Règles non sûres (reçues avec une requête) : un motif, ses deux expressions ensemble (`regex` et
/// `at_start`) ; le jeu entier, somme de `Regex::memory_usage` ; cache par défaut du crate `regex`.
/// Untrusted rules (received with a request): one pattern, both its expressions together; the whole set, sum of
/// `Regex::memory_usage`; the `regex` crate's default cache.
const UNTRUSTED_PATTERN: usize = 2 * (1 << 20);
const UNTRUSTED_SET: usize = 16 * (1 << 20);
const UNTRUSTED_CACHE: usize = 2 * (1 << 20);

/// Bornes de compilation d'un jeu de motifs / compile bounds of a set of patterns.
pub struct Limits {
    /// Taille maximale d'un automate (NFA avant ou arrière) / largest automaton (forward or reverse NFA).
    nfa: usize,
    /// Cache du DFA paresseux, par expression et par fil / lazy DFA cache, per expression and thread.
    cache: usize,
    /// Mémoire restante du jeu ; None : motifs de confiance, sans borne commune.
    /// Memory left for the set; None: trusted patterns, no shared bound.
    left: Option<Mutex<usize>>,
}

impl Limits {
    /// Packs intégrés et règles locales : réglages inchangés / built-in packs and local rules: unchanged settings.
    pub fn trusted() -> Self {
        Self { nfa: TRUSTED_NFA, cache: DFA_CACHE, left: None }
    }

    /// Règles d'une requête : bornes par motif et pour le jeu ; au-delà, motif refusé avec sa raison, avant
    /// d'allouer. Rules of a request: bounds per pattern and for the set; beyond them, the pattern is refused
    /// with its reason, before allocating.
    pub fn untrusted() -> Self {
        Self { nfa: UNTRUSTED_PATTERN, cache: UNTRUSTED_CACHE, left: Some(Mutex::new(UNTRUSTED_SET)) }
    }

    /// Jeu borné, à compiler sur un seul fil : le pic transitoire est celui d'une expression.
    /// Bounded set, to compile on one thread: the transient peak is one expression's.
    pub fn bounded(&self) -> bool {
        self.left.is_some()
    }

    fn left(&self) -> usize {
        self.left.as_ref().map_or(usize::MAX, |left| *left.lock().unwrap_or_else(PoisonError::into_inner))
    }

    /// Imputer `used` octets au jeu ; refus s'il ne reste pas assez / charges `used` bytes; refused beyond.
    fn charge(&self, used: usize) -> Result<(), String> {
        let Some(left) = &self.left else { return Ok(()) };
        let mut left = left.lock().unwrap_or_else(PoisonError::into_inner);
        *left = left.checked_sub(used).ok_or_else(exhausted)?;
        Ok(())
    }
}

fn exhausted() -> String {
    format!(
        "budget mémoire du jeu de règles épuisé ({} Mo au plus) / rule set memory budget exhausted (at most {} MB)",
        UNTRUSTED_SET >> 20,
        UNTRUSTED_SET >> 20
    )
}

/// Motif compilé / compiled pattern.
pub struct Compiled {
    /// Expression cherchée ; consomme le caractère précédent si `prefixed` / searched; consumes the previous
    /// character when `prefixed`.
    pub regex: Regex,
    /// Si `prefixed` : correspondance ancrée au début du texte, sans caractère précédent / anchored at the start.
    pub at_start: Option<Regex>,
    pub prefixed: bool,
    /// Groupe du suffixe consommé (son début est la fin de la correspondance de Python) et son étendue maximale
    /// en caractères. Group of the consumed suffix (its start is the end of Python's match), maximum extent.
    pub post: Option<(usize, usize)>,
    /// Forme de la correspondance de Python, pour les fenêtres / shape of Python's match, for the windows.
    pub shape: Option<Shape>,
}

/// Mêmes réglages que `regex::RegexBuilder` (sémantique, limites, messages). `room` : octets permis à chaque
/// automate de cette expression par la borne du motif ; `left` : ce qu'il reste au jeu. Same settings as
/// `regex::RegexBuilder`. `room`: bytes allowed to each automaton of this expression by the pattern's bound;
/// `left`: what the set has left.
fn build(hir: &Hir, limits: &Limits, room: usize, left: usize) -> Result<Regex, String> {
    // La plus petite borne en vigueur dit la raison d'un refus / the tightest bound in force gives the reason.
    let refusal = |limit: usize| {
        if left < room {
            exhausted()
        } else if room < limits.nfa {
            format!("Compiled regex exceeds size limit of {} bytes (with its anchored twin).", limits.nfa)
        } else {
            format!("Compiled regex exceeds size limit of {limit} bytes.")
        }
    };
    let allowed = room.min(left);
    if allowed == 0 {
        return Err(refusal(0));
    }
    let config = meta::Config::new()
        .match_kind(regex_automata::MatchKind::LeftmostFirst)
        .utf8_empty(true)
        .nfa_size_limit(Some(allowed))
        .hybrid_cache_capacity(limits.cache);
    // La limite d'automate arrête la construction avant l'allocation / the automaton limit stops before allocating.
    meta::Builder::new().configure(config).build_from_hir(hir).map_err(|error| match error.size_limit() {
        Some(limit) => refusal(limit),
        None => error.to_string(),
    })
}

/// Compile un motif lu ; `word` : `\w` de Python (pour `\b`) / compiles a read pattern; `word`: Python's `\w`.
/// Jeu borné : le motif n'est imputé au jeu qu'une fois accepté en entier / bounded set: the pattern is charged
/// to the set only once fully accepted.
pub fn compile(tree: &Tree, word: &ClassUnicode, limits: &Limits) -> Result<Compiled, String> {
    let rewritten = context::rewrite(tree.nodes.clone(), word)?;
    // Groupe du suffixe : après tous ceux de Python, leurs numéros ne changent pas / after Python's groups.
    let post_index = tree.groups + 1;
    let translate = |mode| hir::translate(&rewritten.nodes, &tree.names, mode, post_index);
    let body = translate(hir::Mode::Body)?;
    let prefixed = rewritten.filtered();
    let left = limits.left();
    let (regex, at_start) = if prefixed {
        let main = build(&translate(hir::Mode::Prefixed)?, limits, limits.nfa, left)?;
        // Jeu borné : les deux expressions d'un motif de tête partagent sa borne (pas deux fois la mise).
        // Bounded set: both expressions of a prefixed pattern share its bound (not twice the stake).
        let used = main.memory_usage();
        let room = if limits.bounded() { limits.nfa.saturating_sub(used) } else { limits.nfa };
        let first = build(&translate(hir::Mode::AtStart)?, limits, room, left.saturating_sub(used))?;
        (main, Some(first))
    } else {
        (build(&translate(hir::Mode::Plain)?, limits, limits.nfa, left)?, None)
    };
    limits.charge(regex.memory_usage() + at_start.as_ref().map_or(0, Regex::memory_usage))?;
    // Un suffixe non borné rend les fenêtres inapplicables / an unbounded suffix rules out the windows.
    let post = rewritten.post.map(|extent| (post_index as usize, extent.unwrap_or(usize::MAX)));
    let shape = if post.is_some_and(|(_, extent)| extent == usize::MAX) { None } else { windows::shape(&body) };
    Ok(Compiled { regex, at_start, prefixed, post, shape })
}

#[cfg(test)]
mod tests {
    use regex_syntax::hir::{Class, ClassUnicodeRange, Repetition};

    use super::*;

    /// Classe de 4 000 intervalles, répétée : un automate de plusieurs mégaoctets / a multi-megabyte automaton.
    fn wide(count: u32) -> Hir {
        let ranges = (0..4000u32).filter_map(|i| char::from_u32(0x100 + 2 * i)).map(|c| ClassUnicodeRange::new(c, c));
        let class = Hir::class(Class::Unicode(ClassUnicode::new(ranges)));
        Hir::repetition(Repetition { min: count, max: Some(count), greedy: true, sub: Box::new(class) })
    }

    #[test]
    fn the_set_budget_is_shared_and_refuses_beyond() {
        let limits = Limits::untrusted();
        assert!(limits.bounded() && !Limits::trusted().bounded());
        assert!(limits.charge(UNTRUSTED_SET - 10).is_ok());
        assert!(limits.charge(11).is_err_and(|error| error.contains("budget")));
        assert_eq!(limits.left(), 10);
        assert!(Limits::trusted().charge(usize::MAX).is_ok() && Limits::trusted().left() == usize::MAX);
    }

    #[test]
    fn untrusted_expressions_are_refused_before_allocating() {
        let limits = Limits::untrusted();
        let left = limits.left();
        assert!(build(&Hir::literal("CLT-".as_bytes()), &limits, limits.nfa, left).is_ok());
        // Trop grand pour un motif non sûr / too large for an untrusted pattern.
        let refused = build(&wide(100), &limits, limits.nfa, left).expect_err("refused");
        assert!(refused.contains("size limit of 2097152"), "{refused}");
        // Jumeau ancré : la borne restante du motif ; jeu presque épuisé : son budget.
        // Anchored twin: what is left of the pattern's bound; nearly exhausted set: its budget.
        assert!(build(&wide(100), &limits, 1000, left).is_err_and(|error| error.contains("anchored twin")));
        assert!(build(&wide(100), &limits, limits.nfa, 1000).is_err_and(|error| error.contains("budget")));
        // Le même automate reste permis aux motifs de confiance / the same automaton stays allowed when trusted.
        assert!(build(&wide(100), &Limits::trusted(), TRUSTED_NFA, usize::MAX).is_ok());
    }

    #[test]
    fn a_refused_pattern_charges_nothing_and_an_accepted_one_charges_both_expressions() {
        let ranges = (0..748u32).filter_map(|i| char::from_u32(0x41 + 3 * i)).map(|c| ClassUnicodeRange::new(c, c));
        let word = ClassUnicode::new(ranges);
        // \b\w{n} : deux expressions (filtre de tête et jumeau ancré) / two expressions (start filter, twin).
        let tree = |n: u32| Tree {
            groups: 0,
            names: Vec::new(),
            nodes: vec![
                node::Node::At(node::At::Boundary),
                node::Node::Repeat { min: n, max: Some(n), greedy: true, sub: vec![node::Node::Set(word.clone())] },
            ],
        };
        let limits = Limits::untrusted();
        let small = compile(&tree(1), &word, &limits).expect("accepted");
        let used = small.regex.memory_usage() + small.at_start.as_ref().map_or(0, Regex::memory_usage);
        assert!(small.at_start.is_some() && limits.left() == UNTRUSTED_SET - used);
        // Premier refus en grandissant : rien n'est imputé / first refusal while growing: nothing is charged.
        for n in (2..400).step_by(3) {
            let limits = Limits::untrusted();
            if let Err(error) = compile(&tree(n), &word, &limits) {
                assert!(error.contains("size limit"), "{error}");
                assert_eq!(limits.left(), UNTRUSTED_SET, "refused at n = {n}, budget charged anyway");
                return;
            }
        }
        panic!("never refused");
    }

    #[test]
    fn an_exhausted_set_refuses_every_further_expression() {
        let limits = Limits::untrusted();
        limits.charge(UNTRUSTED_SET).expect("whole budget");
        let refused = build(&Hir::literal("x".as_bytes()), &limits, limits.nfa, limits.left()).expect_err("refused");
        assert!(refused.contains("budget"), "{refused}");
    }
}
