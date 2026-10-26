//! Traduction de l'arbre réécrit en HIR de `regex-syntax` / translation of the rewritten tree into HIR.
//!
//! Chaque nœud a son équivalent exact : littéraux et ensembles déjà résolus, répétitions gourmandes ou
//! paresseuses, groupes aux numéros de Python, alternatives dans l'ordre de `re`, assertions `\A`, `\Z`, `^` et
//! `$` en mode MULTILINE (mêmes définitions : « \n » seul). Every node has an exact equivalent: resolved
//! literals and sets, greedy or lazy repetitions, groups with Python's numbers, alternatives in `re`'s order, and
//! the `\A`, `\Z`, MULTILINE `^`/`$` assertions (same definitions: "\n" only).

use regex_syntax::hir::{Capture, Class, Hir, Look, Repetition};

use super::node::{At, Node};

/// Traitement des marqueurs de début et de fin / handling of the start and end markers.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Correspondance de Python seule (formes des fenêtres, contenu d'assertion) / Python's match only.
    Body,
    /// Correspondance de Python puis suffixe consommé, sans filtre de début / Python's match then the suffix.
    Plain,
    /// Le caractère précédent est consommé d'abord, selon le filtre / the previous character is consumed first.
    Prefixed,
    /// Début du texte : seules les alternatives permises sans caractère précédent / text start only.
    AtStart,
}

/// `names` : (nom, numéro) des groupes ; `post` : numéro du groupe du suffixe consommé.
/// `names`: group names and numbers; `post`: number of the consumed suffix's group.
pub fn translate(nodes: &[Node], names: &[(String, u32)], mode: Mode, post: u32) -> Result<Hir, String> {
    let mut parts = Vec::with_capacity(nodes.len());
    for node in nodes {
        parts.push(match node {
            Node::Literal(c) => {
                let mut buffer = [0u8; 4];
                Hir::literal(c.encode_utf8(&mut buffer).as_bytes())
            }
            Node::Set(class) => Hir::class(Class::Unicode(class.clone())),
            Node::Repeat { min, max, greedy, sub } => Hir::repetition(Repetition {
                min: *min,
                max: *max,
                greedy: *greedy,
                sub: Box::new(translate(sub, names, mode, post)?),
            }),
            Node::Group { index: Some(index), sub } => Hir::capture(Capture {
                index: *index,
                name: names.iter().find(|(_, i)| i == index).map(|(name, _)| name.clone().into_boxed_str()),
                sub: Box::new(translate(sub, names, mode, post)?),
            }),
            Node::Group { index: None, sub } => translate(sub, names, mode, post)?,
            Node::Branch(alternatives) => Hir::alternation(
                alternatives.iter().map(|alt| translate(alt, names, mode, post)).collect::<Result<Vec<_>, _>>()?,
            ),
            Node::At(At::Start) => Hir::look(Look::Start),
            Node::At(At::StartLine) => Hir::look(Look::StartLF),
            Node::At(At::EndLine) => Hir::look(Look::EndLF),
            Node::At(At::EndText) => Hir::look(Look::End),
            Node::At(At::End | At::Boundary | At::NotBoundary) | Node::Look { .. } => {
                return Err("assertion non réécrite / assertion not rewritten".into())
            }
            Node::Start(filter) => match mode {
                Mode::Body | Mode::Plain => Hir::empty(),
                Mode::Prefixed => Hir::class(Class::Unicode(filter.previous.clone())),
                Mode::AtStart if filter.at_start => Hir::empty(),
                Mode::AtStart => Hir::fail(),
            },
            // Groupe du suffixe : son début est la fin de la correspondance de Python, même s'il figure dans
            // plusieurs branches. Suffix group: its start is the end of Python's match, even when it appears in
            // several branches.
            Node::Post(suffix) => match mode {
                Mode::Body => Hir::empty(),
                _ => Hir::capture(Capture { index: post, name: None, sub: Box::new(suffix.clone()) }),
            },
        });
    }
    Ok(Hir::concat(parts))
}

#[cfg(test)]
mod tests {
    use regex_syntax::hir::{ClassUnicode, ClassUnicodeRange};

    use super::*;
    use crate::pattern::node::Filter;

    #[test]
    fn start_markers_follow_the_mode() {
        let digits = ClassUnicode::new([ClassUnicodeRange::new('0', '9')]);
        let filter = Filter { previous: digits.clone(), at_start: false };
        let nodes = vec![Node::Start(filter), Node::Literal('a')];
        assert_eq!(translate(&nodes, &[], Mode::Body, 1).unwrap(), Hir::literal("a".as_bytes()));
        assert_eq!(translate(&nodes, &[], Mode::Plain, 1).unwrap(), Hir::literal("a".as_bytes()));
        assert_eq!(
            translate(&nodes, &[], Mode::Prefixed, 1).unwrap(),
            Hir::concat(vec![Hir::class(Class::Unicode(digits)), Hir::literal("a".as_bytes())])
        );
        assert!(translate(&nodes, &[], Mode::AtStart, 1).unwrap().properties().minimum_len().is_none());
        assert!(translate(&[Node::At(At::Boundary)], &[], Mode::Body, 1).is_err());
    }

    #[test]
    fn end_markers_are_captured_outside_the_shape() {
        let nodes = vec![Node::Literal('a'), Node::Post(Hir::literal("b".as_bytes()))];
        assert_eq!(translate(&nodes, &[], Mode::Body, 3).unwrap(), Hir::literal("a".as_bytes()));
        let plain = translate(&nodes, &[], Mode::Plain, 3).unwrap();
        assert_eq!(plain.properties().explicit_captures_len(), 1);
        assert_eq!(plain.properties().minimum_len(), Some(2));
    }
}
