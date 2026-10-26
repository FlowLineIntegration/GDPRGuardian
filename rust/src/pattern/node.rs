//! Arbre d'un motif, lu dans l'arbre de `re` lui-même / a pattern's tree, read from `re`'s own tree.
//!
//! Les ensembles arrivent résolus : classes `\w`, `\d`, `\s` de Python, négation, et `re.IGNORECASE` décidé par
//! `re` sur les caractères où il diffère de la casse exacte. Sets arrive resolved: Python's `\w`, `\d`, `\s`,
//! negation, and `re.IGNORECASE` decided by `re` on the characters where it differs from exact case.

use pyo3::prelude::*;
use pyo3::types::{PyList, PyString, PyTuple};
use regex_syntax::hir::{ClassUnicode, ClassUnicodeRange, Hir};

use crate::unicode::PerlSets;

/// Profondeur d'imbrication acceptée (l'analyseur de `re` est lui aussi récursif) / accepted nesting depth.
const MAX_DEPTH: usize = 200;

#[derive(Clone, Debug)]
pub enum Node {
    /// Littéral sensible à la casse / case-sensitive literal.
    Literal(char),
    /// Un caractère d'un ensemble résolu ; vide : échec / one character of a resolved set; empty: failure.
    Set(ClassUnicode),
    Repeat {
        min: u32,
        max: Option<u32>,
        greedy: bool,
        sub: Vec<Node>,
    },
    Group {
        index: Option<u32>,
        sub: Vec<Node>,
    },
    Branch(Vec<Vec<Node>>),
    At(At),
    Look {
        ahead: bool,
        negative: bool,
        sub: Vec<Node>,
    },
    /// Début de la correspondance de Python, posé par la réécriture des assertions de tête.
    /// Start of Python's match, placed by the rewriting of leading assertions.
    Start(Filter),
    /// Fin de la correspondance de Python, posée par la réécriture des assertions de fin : le suffixe consommé
    /// qui les remplace, dans le groupe à part. End of Python's match, placed by the rewriting of trailing
    /// assertions: the consumed suffix replacing them, in the separate group.
    Post(Hir),
}

/// Assertions de position de `re`, drapeaux résolus / `re`'s position assertions, flags resolved.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum At {
    /// `\A`, `^` sans MULTILINE / without MULTILINE.
    Start,
    /// `^` avec MULTILINE / with MULTILINE.
    StartLine,
    /// `$` sans MULTILINE : fin, ou avant un « \n » final / end, or before a final "\n".
    End,
    /// `$` avec MULTILINE / with MULTILINE.
    EndLine,
    /// `\Z`.
    EndText,
    /// `\b`, `\w` de Python / Python's `\w`.
    Boundary,
    /// `\B`.
    NotBoundary,
}

/// Contrainte sur le caractère qui précède la correspondance / constraint on the character before the match.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Filter {
    /// Caractères précédents permis / allowed previous characters.
    pub previous: ClassUnicode,
    /// Correspondance permise au début du texte, sans caractère précédent / allowed at the start of the text.
    pub at_start: bool,
}

impl Filter {
    pub fn any() -> Self {
        Self { previous: full(), at_start: true }
    }

    pub fn is_any(&self) -> bool {
        self.at_start && self.previous == full()
    }
}

/// Tous les caractères / every character.
pub fn full() -> ClassUnicode {
    ClassUnicode::new([ClassUnicodeRange::new('\0', char::MAX)])
}

/// Un seul caractère / a single character.
pub fn single(c: char) -> ClassUnicode {
    ClassUnicode::new([ClassUnicodeRange::new(c, c)])
}

pub fn intersect(a: &ClassUnicode, b: &ClassUnicode) -> ClassUnicode {
    let mut out = a.clone();
    out.intersect(b);
    out
}

pub fn difference(a: &ClassUnicode, b: &ClassUnicode) -> ClassUnicode {
    let mut out = a.clone();
    out.difference(b);
    out
}

pub fn negated(a: &ClassUnicode) -> ClassUnicode {
    let mut out = a.clone();
    out.negate();
    out
}

pub fn is_empty(a: &ClassUnicode) -> bool {
    a.ranges().is_empty()
}

/// `a` ⊆ `b`.
pub fn subset(a: &ClassUnicode, b: &ClassUnicode) -> bool {
    is_empty(&difference(a, b))
}

/// `a` ∩ `b` = ∅.
pub fn disjoint(a: &ClassUnicode, b: &ClassUnicode) -> bool {
    is_empty(&intersect(a, b))
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

/// Classe de points de code, construite en une fois (`push` trie à chaque ajout) / built at once.
fn class_of(points: impl IntoIterator<Item = u32>) -> ClassUnicode {
    let mut ranges = Vec::new();
    for cp in points {
        push_range(&mut ranges, cp, cp);
    }
    ClassUnicode::new(ranges)
}

impl Node {
    /// Classe d'un nœud qui consomme exactement un caractère / class of a node consuming exactly one character.
    pub fn atom(&self) -> Option<ClassUnicode> {
        match self {
            Node::Literal(c) => Some(single(*c)),
            Node::Set(class) => Some(class.clone()),
            _ => None,
        }
    }

    /// Classe du premier (ou dernier) caractère, si le nœud consomme au moins un caractère d'une seule classe.
    /// Class of the first (or last) character, when the node consumes at least one character of a single class.
    pub fn edge(&self) -> Option<ClassUnicode> {
        match self {
            Node::Repeat { min, sub, .. } if *min >= 1 && sub.len() == 1 => sub[0].atom(),
            other => other.atom(),
        }
    }

    /// Le nœud peut-il ne rien consommer ? / can the node consume nothing?
    pub fn nullable(&self) -> bool {
        match self {
            Node::Literal(_) | Node::Set(_) => false,
            Node::Repeat { min, sub, .. } => *min == 0 || nullable(sub),
            Node::Group { sub, .. } => nullable(sub),
            Node::Branch(alternatives) => alternatives.iter().any(|alt| nullable(alt)),
            Node::At(_) | Node::Look { .. } | Node::Start(_) | Node::Post(_) => true,
        }
    }
}

pub fn nullable(nodes: &[Node]) -> bool {
    nodes.iter().all(Node::nullable)
}

/// Motif lu : nombre de groupes, noms, nœuds / a read pattern: group count, names, nodes.
pub struct Tree {
    pub groups: u32,
    pub names: Vec<(String, u32)>,
    pub nodes: Vec<Node>,
}

/// Ensembles partagés pour la lecture / shared sets for reading.
pub struct Sets<'a> {
    pub perl: &'a PerlSets,
    pub not_word: ClassUnicode,
    pub not_digit: ClassUnicode,
    pub not_space: ClassUnicode,
    /// Candidats de `re.IGNORECASE` / `re.IGNORECASE` candidates.
    pub candidates: ClassUnicode,
}

impl<'a> Sets<'a> {
    pub fn new(perl: &'a PerlSets, candidates: &[char]) -> Self {
        Self {
            perl,
            not_word: negated(&perl.word),
            not_digit: negated(&perl.digit),
            not_space: negated(&perl.space),
            candidates: class_of(candidates.iter().map(|&c| u32::from(c))),
        }
    }

    fn category(&self, name: &str) -> Result<&ClassUnicode, String> {
        Ok(match name {
            "word" => &self.perl.word,
            "not_word" => &self.not_word,
            "digit" => &self.perl.digit,
            "not_digit" => &self.not_digit,
            "space" => &self.perl.space,
            "not_space" => &self.not_space,
            other => return Err(format!("catégorie inconnue / unknown category {other}")),
        })
    }
}

fn tag<'py>(node: &Bound<'py, PyTuple>) -> PyResult<String> {
    Ok(node.get_item(0)?.cast_into::<PyString>()?.to_str()?.to_owned())
}

fn code(cp: u32) -> Option<char> {
    char::from_u32(cp)
}

/// Lit l'arbre rendu par `gdprguardian._native.syntax` ; `Err` : motif laissé à Python, avec la raison.
/// Reads the tree returned by `gdprguardian._native.syntax`; `Err`: pattern left to Python, with the reason.
pub fn read(syntax: &Bound<'_, PyAny>, sets: &Sets) -> PyResult<Result<Tree, String>> {
    let syntax = syntax.cast::<PyTuple>()?;
    if syntax.len() == 1 {
        return Ok(Err(syntax.get_item(0)?.extract()?));
    }
    let groups: u32 = syntax.get_item(0)?.extract()?;
    let names: Vec<(String, u32)> = syntax.get_item(1)?.extract()?;
    Ok(nodes(&syntax.get_item(2)?, sets, 0)?.map(|nodes| Tree { groups, names, nodes }))
}

fn nodes(list: &Bound<'_, PyAny>, sets: &Sets, depth: usize) -> PyResult<Result<Vec<Node>, String>> {
    if depth > MAX_DEPTH {
        return Ok(Err("motif trop imbriqué / pattern nested too deeply".into()));
    }
    let list = list.cast::<PyList>()?;
    let mut out = Vec::with_capacity(list.len());
    for item in list.iter() {
        match node(item.cast::<PyTuple>()?, sets, depth)? {
            Ok(node) => out.push(node),
            Err(reason) => return Ok(Err(reason)),
        }
    }
    Ok(Ok(out))
}

fn node(item: &Bound<'_, PyTuple>, sets: &Sets, depth: usize) -> PyResult<Result<Node, String>> {
    let get = |i: usize| item.get_item(i);
    Ok(Ok(match tag(item)?.as_str() {
        // Demi-codet isolé : absent de tout texte Rust, donc jamais trouvé / lone surrogate: never in Rust text.
        "lit" => code(get(1)?.extract()?).map_or(Node::Set(ClassUnicode::empty()), Node::Literal),
        "set" => {
            let negate: bool = get(1)?.extract()?;
            let mut ranges = Vec::new();
            let mut categories = Vec::new();
            for member in get(2)?.cast::<PyList>()?.iter() {
                let member = member.cast_into::<PyTuple>()?;
                match tag(&member)?.as_str() {
                    "lit" => {
                        let cp: u32 = member.get_item(1)?.extract()?;
                        push_range(&mut ranges, cp, cp);
                    }
                    "range" => push_range(&mut ranges, member.get_item(1)?.extract()?, member.get_item(2)?.extract()?),
                    "cat" => match sets.category(member.get_item(1)?.cast_into::<PyString>()?.to_str()?) {
                        Ok(category) => categories.push(category),
                        Err(reason) => return Ok(Err(reason)),
                    },
                    other => return Ok(Err(format!("élément d'ensemble inconnu / unknown set member {other}"))),
                }
            }
            let mut class = ClassUnicode::new(ranges);
            for category in categories {
                class.union(category);
            }
            if negate {
                class.negate();
            }
            // `re.IGNORECASE` : hors des candidats, l'ensemble lui-même ; parmi eux, ce que `re` a accepté.
            // Outside the candidates, the set itself; among them, what `re` accepted.
            let cased: Option<Vec<u32>> = get(3)?.extract()?;
            if let Some(cased) = cased {
                class.difference(&sets.candidates);
                class.union(&class_of(cased));
            }
            Node::Set(class)
        }
        "any" => {
            let dotall: bool = get(1)?.extract()?;
            Node::Set(if dotall { full() } else { negated(&single('\n')) })
        }
        "repeat" => {
            let max: i64 = get(2)?.extract()?;
            let sub = match nodes(&get(4)?, sets, depth + 1)? {
                Ok(sub) => sub,
                Err(reason) => return Ok(Err(reason)),
            };
            Node::Repeat {
                min: get(1)?.extract()?,
                max: if max < 0 { None } else { u32::try_from(max).ok() },
                greedy: get(3)?.extract()?,
                sub,
            }
        }
        "group" => {
            let index: u32 = get(1)?.extract()?;
            match nodes(&get(2)?, sets, depth + 1)? {
                Ok(sub) => Node::Group { index: (index > 0).then_some(index), sub },
                Err(reason) => return Ok(Err(reason)),
            }
        }
        "branch" => {
            let mut alternatives = Vec::new();
            for alternative in get(1)?.cast::<PyList>()?.iter() {
                match nodes(&alternative, sets, depth + 1)? {
                    Ok(alternative) => alternatives.push(alternative),
                    Err(reason) => return Ok(Err(reason)),
                }
            }
            Node::Branch(alternatives)
        }
        "at" => Node::At(match get(1)?.cast_into::<PyString>()?.to_str()? {
            "start" => At::Start,
            "start_line" => At::StartLine,
            "end" => At::End,
            "end_line" => At::EndLine,
            "end_text" => At::EndText,
            "boundary" => At::Boundary,
            "not_boundary" => At::NotBoundary,
            other => return Ok(Err(format!("assertion inconnue / unknown assertion {other}"))),
        }),
        "look" => match nodes(&get(3)?, sets, depth + 1)? {
            Ok(sub) => Node::Look { ahead: get(1)?.extract()?, negative: get(2)?.extract()?, sub },
            Err(reason) => return Ok(Err(reason)),
        },
        other => return Ok(Err(format!("nœud inconnu / unknown node {other}"))),
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn class_helpers() {
        let digits = ClassUnicode::new([ClassUnicodeRange::new('0', '9')]);
        let five = single('5');
        assert!(subset(&five, &digits) && !subset(&digits, &five));
        assert!(disjoint(&single('a'), &digits) && !disjoint(&five, &digits));
        assert!(is_empty(&difference(&five, &digits)) && Filter::any().is_any());
        let mut ranges = Vec::new();
        push_range(&mut ranges, 0xD7FE, 0xE001);
        assert_eq!(ClassUnicode::new(ranges).ranges().len(), 2);
        assert_eq!(class_of([0x61, 0x62, 0xD800, 0x64]).ranges().len(), 2);
    }

    #[test]
    fn edges_and_nullability() {
        let digit = Node::Set(ClassUnicode::new([ClassUnicodeRange::new('0', '9')]));
        let plus = Node::Repeat { min: 1, max: None, greedy: true, sub: vec![digit.clone()] };
        let star = Node::Repeat { min: 0, max: None, greedy: true, sub: vec![digit.clone()] };
        assert!(plus.edge().is_some() && star.edge().is_none());
        assert!(!plus.nullable() && star.nullable() && Node::At(At::Boundary).nullable());
        assert!(nullable(&[star.clone(), Node::Branch(vec![vec![], vec![digit]])]));
    }
}
