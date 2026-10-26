//! Assertions de contexte (look-arounds, `\b`, `$`) traduites en contexte consommé, sans perte d'exactitude.
//!
//! Context assertions (look-arounds, `\b`, `$`) turned into consumed context, without loss of exactness.
//!
//! Le moteur linéaire n'a pas de look-around. Deux formes exactes suffisent aux motifs réels :
//! - en tête, une contrainte sur le caractère qui précède la correspondance (`X(?<![0-9A-Za-z]{2})` après un
//!   premier caractère X de la classe, `(?<!C)`, `\b`) devient un filtre de début : la recherche consomme ce
//!   caractère d'abord (`[^C]X…`), puis la correspondance commence juste après ; au tout début du texte, une
//!   seconde expression, ancrée, dit ce que Python accepte sans caractère précédent ;
//! - en fin, des assertions sur ce qui suit (`(?!C)`, `(?=S)`, `$`, `\b`) deviennent un suffixe consommé dans
//!   un groupe à part : la fin de la correspondance de Python est le début de ce groupe. Dans une alternative
//!   finale (`(?:$|\s)`), chaque branche porte son propre suffixe, dans ce même groupe.
//!
//! La recherche « au plus tôt puis par priorité » du moteur reproduit l'ordre de retour arrière de `re` :
//! position de départ croissante, puis chemins dans l'ordre des alternatives ; une assertion ne change que
//! l'acceptation d'un chemin, jamais l'ordre. Tout ce qui sort de ces formes reste à Python, avec la raison.
//!
//! The linear engine has no look-around. Two exact forms cover real patterns: a constraint on the character
//! before the match becomes a start filter (the search consumes that character first, the match starts right
//! after; at the very start of the text, a second, anchored expression says what Python accepts without a
//! previous character); assertions on what follows become a consumed suffix in a separate group, whose start
//! is the end of Python's match (in a final alternation, each branch carries its own suffix, in that same
//! group). The engine's leftmost-first search reproduces `re`'s backtracking order: increasing start, then
//! paths in alternative order; an assertion only changes whether a path is accepted, never the order. Anything
//! outside these forms stays with Python, with the reason.
//!
//! Coût borné (règles non sûres) : pas de développement et intervalles de classes copiés sont comptés par motif.
//! Bounded cost (untrusted rules): expansion steps and copied class ranges are counted per pattern.

use regex_syntax::hir::{Class, ClassUnicode, Hir, HirKind, Look};

use super::node::{difference, disjoint, full, intersect, is_empty, negated, single, subset, At, Filter, Node};

/// Séquences développées au plus (négations finales) / at most this many expanded sequences.
const MAX_SEQUENCES: usize = 1024;
/// Longueur d'une séquence développée au plus / maximum length of an expanded sequence.
const MAX_LENGTH: usize = 32;
/// Répétition développée au plus / largest repetition expanded.
const MAX_EXPANDED_REPEAT: u32 = 16;
/// Pas de développement permis par motif (éléments copiés, régions examinées, nœuds) : sans cette borne, un
/// motif court et hostile (règle personnalisée) coûterait un temps exponentiel ou des gigaoctets avant d'être
/// refusé. Expansion steps allowed per pattern (elements copied, regions examined, nodes): without this bound, a
/// short hostile pattern (custom rule) would cost exponential time or gigabytes before being refused.
const MAX_STEPS: usize = 1 << 15;
/// Intervalles de classes copiés au plus par motif, 8 octets chacun : borne la mémoire de la réécriture, qu'un
/// nombre de pas ne borne pas (la classe `\w` de Python a 748 intervalles, 6 Ko par copie). Class ranges copied
/// at most per pattern, 8 bytes each: bounds the rewrite's memory, which a step count does not (Python's `\w`
/// class has 748 ranges, 6 KB per copy).
const MAX_RANGES: usize = 1 << 20;
/// Développements de caractères facultatifs au plus avant une assertion de tête, tous chemins confondus (chacun
/// double les chemins qui suivent) / at most this many expansions of optional characters before a leading
/// assertion, over all paths (each one doubles the paths that follow).
const MAX_OPTIONALS: usize = 32;

fn too_large() -> String {
    "assertion trop vaste pour être développée / assertion too large to expand".into()
}

fn dollar_elsewhere() -> String {
    "$ hors d'une position finale (fin du motif, d'une alternative finale ou d'un look-ahead final) / $ outside a \
     final position (end of the pattern, of a final alternative or of a final look-ahead)"
        .into()
}

/// Travail restant pour réécrire un motif / work left to rewrite one pattern.
struct Budget {
    steps: usize,
    ranges: usize,
    optionals: usize,
}

impl Budget {
    fn new() -> Self {
        Self { steps: MAX_STEPS, ranges: MAX_RANGES, optionals: MAX_OPTIONALS }
    }

    fn spend(&mut self, cost: usize) -> Result<(), String> {
        self.steps = self.steps.checked_sub(cost).ok_or_else(too_large)?;
        Ok(())
    }

    /// Intervalles de classes sur le point d'être copiés / class ranges about to be copied.
    fn copy(&mut self, ranges: usize) -> Result<(), String> {
        self.ranges = self.ranges.checked_sub(ranges).ok_or_else(too_large)?;
        Ok(())
    }
}

/// Intervalles des classes d'une séquence / class ranges of a sequence.
fn ranges_of(seq: &[Elem]) -> usize {
    seq.iter().map(|elem| if let Elem::Class(class) = elem { class.ranges().len() } else { 0 }).sum()
}

/// Intervalles des classes d'un arbre de nœuds / class ranges of a node tree.
fn node_ranges(nodes: &[Node]) -> usize {
    nodes
        .iter()
        .map(|node| match node {
            Node::Set(class) => class.ranges().len(),
            Node::Repeat { sub, .. } | Node::Group { sub, .. } | Node::Look { sub, .. } => node_ranges(sub),
            Node::Branch(alternatives) => alternatives.iter().map(|alt| node_ranges(alt)).sum(),
            Node::Start(filter) => filter.previous.ranges().len(),
            // Suffixe d'une branche finale : copié avec elle / a final branch's suffix: copied along with it.
            Node::Post(suffix) => hir_ranges(suffix),
            Node::Literal(_) | Node::At(_) => 1,
        })
        .sum()
}

/// Taille d'une expression traduite, en intervalles : ceux de ses classes, et 16 par nœud (environ 128 octets).
/// Size of a translated expression, in ranges: its classes' ranges, and 16 per node (about 128 bytes).
fn hir_ranges(hir: &Hir) -> usize {
    let mut total = 0;
    let mut stack = vec![hir];
    while let Some(hir) = stack.pop() {
        total += 16;
        match hir.kind() {
            HirKind::Class(Class::Unicode(class)) => total += class.ranges().len(),
            HirKind::Class(Class::Bytes(class)) => total += class.ranges().len(),
            HirKind::Repetition(repetition) => stack.push(&repetition.sub),
            HirKind::Capture(capture) => stack.push(&capture.sub),
            HirKind::Concat(subs) | HirKind::Alternation(subs) => stack.extend(subs),
            HirKind::Empty | HirKind::Literal(_) | HirKind::Look(_) => {}
        }
    }
    total
}

/// Motif réécrit / rewritten pattern.
pub struct Rewritten {
    /// Nœuds, un marqueur `Start` en tête de chaque alternative de départ, un nœud `Post` (suffixe consommé) en
    /// fin de chaque chemin s'il y en a / nodes, a start marker per start path, a `Post` node (consumed suffix) at
    /// the end of every path when there is one.
    pub nodes: Vec<Node>,
    /// Étendue maximale du suffixe consommé en caractères (None : non bornée), s'il existe.
    /// Largest extent of the consumed suffix in characters (None: unbounded), when there is one.
    pub post: Option<Option<usize>>,
}

impl Rewritten {
    /// Un filtre de début est-il actif ? / is any start filter active?
    pub fn filtered(&self) -> bool {
        fn walk(nodes: &[Node]) -> bool {
            nodes.iter().any(|node| match node {
                Node::Start(filter) => !filter.is_any(),
                Node::Group { sub, .. } => walk(sub),
                Node::Branch(alternatives) => alternatives.iter().any(|alt| walk(alt)),
                _ => false,
            })
        }
        walk(&self.nodes)
    }
}

/// Réécrit les assertions de tête et de fin ; `word` : `\w` de Python.
/// Rewrites leading and trailing assertions; `word`: Python's `\w`.
pub fn rewrite(mut nodes: Vec<Node>, word: &ClassUnicode) -> Result<Rewritten, String> {
    let mut budget = Budget::new();
    let conditions = take_trailing(&mut nodes, word, &mut budget)?;
    let suffix = suffix(conditions, &mut budget)?;
    // Sans assertion finale, une alternative finale peut porter les siennes, branche par branche.
    // Without a trailing assertion, a final alternation may carry its own, branch by branch.
    let post = match &suffix {
        Some((_, extent)) => Some(*extent),
        None => final_alternation(&mut nodes, word, &mut budget)?,
    };
    let mut nodes = start(nodes, word, 0, &mut budget)?;
    check(&nodes, false)?;
    nodes.extend(suffix.map(|(hir, _)| Node::Post(hir)));
    Ok(Rewritten { nodes, post })
}

// --- Fin : assertions sur ce qui suit / end: assertions on what follows -----------------------------------

/// Condition sur le texte qui suit la correspondance / condition on the text after the match.
enum Condition {
    /// Ces nœuds doivent correspondre ici / these nodes must match here.
    Positive(Vec<Node>),
    /// Ces nœuds ne doivent pas correspondre ici / these nodes must not match here.
    Negative(Vec<Node>),
}

/// `$` consommé : « \n » final puis fin du texte, ou fin du texte ; exact seulement si rien ne le suit.
/// Consumed `$`: a final "\n" then the end of the text, or the end of the text; exact only if nothing follows.
fn end_of_text() -> Node {
    Node::Branch(vec![vec![Node::Literal('\n'), Node::At(At::EndText)], vec![Node::At(At::EndText)]])
}

/// Retire les assertions finales (dans le dernier groupe aussi : il finit au même endroit).
/// Removes the trailing assertions (inside the last group too: it ends at the same place).
fn take_trailing(nodes: &mut Vec<Node>, word: &ClassUnicode, budget: &mut Budget) -> Result<Vec<Condition>, String> {
    let mut found = Vec::new();
    loop {
        match nodes.last_mut() {
            // `(?=$)`, `(?=\b)`, `(?=\B)` : la même assertion, sans look-ahead / the same assertion, unwrapped.
            Some(Node::Look { ahead: true, negative: false, sub })
                if matches!(sub.as_slice(), [Node::At(At::End | At::Boundary | At::NotBoundary)]) =>
            {
                let Some(Node::Look { mut sub, .. }) = nodes.pop() else { break };
                nodes.extend(sub.pop());
            }
            Some(Node::Look { ahead: true, .. }) => {
                let Some(Node::Look { negative, sub, .. }) = nodes.pop() else { break };
                found.push(if negative { Condition::Negative(sub) } else { Condition::Positive(sub) });
            }
            Some(Node::At(At::End)) => {
                nodes.pop();
                // `$` : fin du texte, ou « \n » final / end of text, or a final "\n".
                found.push(Condition::Positive(vec![end_of_text()]));
            }
            Some(Node::At(kind @ (At::Boundary | At::NotBoundary))) => {
                let boundary = *kind == At::Boundary;
                nodes.pop();
                // `\b` final : selon la classe du dernier caractère, « suivi d'un mot » ou « pas d'un mot ».
                // Final `\b`: by the class of the last character, "followed by a word char" or "not".
                let last = edge_of(nodes, false).ok_or(
                    "\\b ou \\B final sans dernier caractère connu / final \\b or \\B without a known last character",
                )?;
                let word_before = if subset(&last, word) {
                    true
                } else if disjoint(&last, word) {
                    false
                } else {
                    return Err("\\b final après une classe mixte / final \\b after a mixed class".into());
                };
                budget.copy(word.ranges().len())?;
                let next_word = vec![Node::Set(word.clone())];
                found.push(if boundary == word_before {
                    Condition::Negative(next_word)
                } else {
                    Condition::Positive(next_word)
                });
            }
            Some(Node::Group { sub, .. }) if ends_with_assertion(sub) => {
                found.extend(take_trailing(sub, word, budget)?);
            }
            _ => break,
        }
    }
    Ok(found)
}

/// Alternative finale (du motif, ou de ses groupes non capturants finaux) dont une branche finit par des
/// assertions : chaque branche reçoit son propre suffixe consommé (`Post`, vide pour une branche sans
/// assertion), dans le même groupe à part. Exact : rien ne suit l'alternative, et la branche choisie l'est dans
/// l'ordre de `re`. Renvoie l'étendue des suffixes, ou None s'il n'y a rien à réécrire. Final alternation (of
/// the pattern, or of its final non-capturing groups) with a branch ending in assertions: each branch gets its
/// own consumed suffix (`Post`, empty for a branch without assertion), in the same separate group. Exact: nothing
/// follows the alternation, and the branch is chosen in `re`'s order. Returns the suffixes' extent, or None when
/// there is nothing to rewrite.
fn final_alternation(
    nodes: &mut [Node],
    word: &ClassUnicode,
    budget: &mut Budget,
) -> Result<Option<Option<usize>>, String> {
    match nodes.last_mut() {
        Some(Node::Group { index: None, sub }) => final_alternation(sub, word, budget),
        Some(Node::Branch(alternatives)) if alternatives.iter().any(|alt| branch_assertion(alt)) => {
            let mut extent = Some(0);
            for alternative in alternatives.iter_mut() {
                let conditions = take_trailing(alternative, word, budget)?;
                let (hir, reach) = match suffix(conditions, budget)? {
                    Some(post) => post,
                    None => match final_alternation(alternative, word, budget)? {
                        // Suffixes posés plus bas, dans l'alternative imbriquée / suffixes placed in the nested one.
                        Some(reach) => {
                            extent = extent.zip(reach).map(|(a, b)| a.max(b));
                            continue;
                        }
                        None => (Hir::empty(), Some(0)),
                    },
                };
                extent = extent.zip(reach).map(|(a, b)| a.max(b));
                alternative.push(Node::Post(hir));
            }
            Ok(Some(extent))
        }
        _ => Ok(None),
    }
}

/// Une branche finit-elle par une assertion, ici ou dans une alternative finale imbriquée ?
/// Does a branch end with an assertion, here or in a nested final alternation?
fn branch_assertion(nodes: &[Node]) -> bool {
    ends_with_assertion(nodes)
        || match nodes.last() {
            Some(Node::Group { index: None, sub }) => branch_assertion(sub),
            Some(Node::Branch(alternatives)) => alternatives.iter().any(|alt| branch_assertion(alt)),
            _ => false,
        }
}

/// Classe du premier (`forward`) ou du dernier caractère consommé, si elle est connue : nœuds sans largeur
/// sautés, groupes ouverts. Class of the first (`forward`) or last consumed character, when known: zero-width
/// nodes skipped, groups entered.
fn edge_of(nodes: &[Node], forward: bool) -> Option<ClassUnicode> {
    let order: Vec<&Node> = if forward { nodes.iter().collect() } else { nodes.iter().rev().collect() };
    for node in order {
        match node {
            Node::At(_) | Node::Look { .. } | Node::Start(_) | Node::Post(_) => {}
            Node::Group { sub, .. } => return edge_of(sub, forward),
            other => return other.edge(),
        }
    }
    None
}

fn ends_with_assertion(nodes: &[Node]) -> bool {
    match nodes.last() {
        Some(Node::Look { ahead: true, .. } | Node::At(At::End | At::Boundary | At::NotBoundary)) => true,
        Some(Node::Group { sub, .. }) => ends_with_assertion(sub),
        _ => false,
    }
}

/// Élément d'une séquence développée : un caractère d'une classe, ou la fin du texte.
/// Element of an expanded sequence: one character of a class, or the end of the text.
#[derive(Clone, Debug, PartialEq, Eq)]
enum Elem {
    Class(ClassUnicode),
    End,
}

/// Suffixe consommé : vrai exactement là où toutes les conditions le sont / true exactly where all conditions are.
fn suffix(conditions: Vec<Condition>, budget: &mut Budget) -> Result<Option<(Hir, Option<usize>)>, String> {
    if conditions.is_empty() {
        return Ok(None);
    }
    let positives = conditions.iter().filter(|c| matches!(c, Condition::Positive(_))).count();
    if positives == 0 {
        // Négations seules : un arbre des débuts interdits, dont on garde le complément.
        // Negations only: a trie of forbidden starts, whose complement is kept.
        let mut bad = Vec::new();
        for condition in conditions {
            if let Condition::Negative(sub) = condition {
                bad.extend(sequences(&sub, true, budget)?);
                // Vérifié à chaque ajout, pas après tous / checked at each addition, not after all of them.
                if bad.len() > MAX_SEQUENCES {
                    return Err("assertion finale trop vaste / trailing assertion too large".into());
                }
            }
        }
        let refs: Vec<&[Elem]> = bad.iter().map(Vec::as_slice).collect();
        return Ok(Some(match good(&refs, 0, budget)? {
            Some(node) => (node.hir(), Some(node.depth())),
            None => (Hir::fail(), Some(0)),
        }));
    }
    match (positives, conditions.len(), conditions.into_iter().next()) {
        (1, 1, Some(Condition::Positive(mut sub))) => {
            final_dollar(&mut sub);
            check(&sub, true)?;
            let extent = max_length(&sub);
            Ok(Some((super::hir::translate(&sub, &[], super::hir::Mode::Body, 0)?, extent)))
        }
        _ => Err("assertions finales positives combinées / combined positive trailing assertions".into()),
    }
}

/// `$` en toute dernière position d'un contenu de look-ahead positif (dernier groupe, chaque branche d'une
/// alternative finale) : consommé, exact car rien ne le suit ; tout autre `$` reste, refusé par `check`.
/// `$` in the very last position of a positive look-ahead's content (last group, every branch of a final
/// alternation): consumed, exact because nothing follows it; any other `$` stays, refused by `check`.
fn final_dollar(nodes: &mut [Node]) {
    match nodes.last_mut() {
        Some(node @ Node::At(At::End)) => *node = end_of_text(),
        Some(Node::Group { sub, .. }) => final_dollar(sub),
        Some(Node::Branch(alternatives)) => alternatives.iter_mut().for_each(|alt| final_dollar(alt)),
        _ => {}
    }
}

/// Plus grande longueur en caractères, None si non bornée / largest length in characters, None if unbounded.
fn max_length(nodes: &[Node]) -> Option<usize> {
    let mut total = 0usize;
    for node in nodes {
        total = total.checked_add(match node {
            Node::Literal(_) | Node::Set(_) => 1,
            Node::Repeat { max, sub, .. } => max_length(sub)?.checked_mul(usize::try_from((*max)?).ok()?)?,
            Node::Group { sub, .. } => max_length(sub)?,
            Node::Branch(alternatives) => {
                alternatives.iter().map(|alt| max_length(alt)).collect::<Option<Vec<_>>>()?.into_iter().max()?
            }
            Node::At(_) | Node::Look { .. } | Node::Start(_) | Node::Post(_) => 0,
        })?;
    }
    Some(total)
}

/// Séquences de classes dont l'une correspond si et seulement si `nodes` correspond (contenu d'assertion).
/// `last` : rien ne suit `nodes` dans l'assertion. Un `$` (qui consomme le « \n » final) et une assertion
/// imbriquée (qui ne consomme rien) ne sont exacts qu'en toute dernière position : ailleurs, refusés.
/// Class sequences one of which matches if and only if `nodes` matches (assertion content). `last`: nothing
/// follows `nodes` in the assertion. A `$` (which consumes the final "\n") and a nested assertion (which consumes
/// nothing) are exact only in the very last position: elsewhere, refused.
fn sequences(nodes: &[Node], last: bool, budget: &mut Budget) -> Result<Vec<Vec<Elem>>, String> {
    let mut acc: Vec<Vec<Elem>> = vec![Vec::new()];
    for (i, node) in nodes.iter().enumerate() {
        let last = last && i + 1 == nodes.len();
        let options: Vec<Vec<Elem>> = match node {
            Node::Literal(_) | Node::Set(_) => {
                let class = node.atom().unwrap_or_else(ClassUnicode::empty);
                budget.copy(class.ranges().len())?;
                vec![vec![Elem::Class(class)]]
            }
            Node::Group { index: None, sub } => sequences(sub, last, budget)?,
            Node::Branch(alternatives) => {
                let mut all = Vec::new();
                for alternative in alternatives {
                    all.extend(sequences(alternative, last, budget)?);
                    if all.len() > MAX_SEQUENCES {
                        return Err(too_large());
                    }
                }
                all
            }
            Node::Repeat { min, max: Some(max), sub, .. } if *max <= MAX_EXPANDED_REPEAT => {
                // Une copie est suivie de la suivante : jamais en dernière position / a copy is followed by the next.
                let once = sequences(sub, false, budget)?;
                let mut all = Vec::new();
                let mut power: Vec<Vec<Elem>> = vec![Vec::new()];
                for count in 0..=*max {
                    if count >= *min {
                        budget.spend(power.iter().map(|seq| seq.len() + 1).sum())?;
                        budget.copy(power.iter().map(|seq| ranges_of(seq)).sum())?;
                        all.extend(power.iter().cloned());
                        if all.len() > MAX_SEQUENCES {
                            return Err(too_large());
                        }
                    }
                    // La puissance suivante ne sert que s'il reste un compte / the next power only if a count is left.
                    if count < *max {
                        power = concat(&power, &once, budget)?;
                    }
                }
                all
            }
            Node::At(At::EndText) => vec![vec![Elem::End]],
            Node::At(At::End) if last => vec![vec![Elem::Class(single('\n')), Elem::End], vec![Elem::End]],
            Node::At(At::End) => return Err(dollar_elsewhere()),
            // Assertion imbriquée en dernière position : elle porte sur le texte qui suit la séquence.
            // Nested assertion in last position: it bears on the text after the sequence.
            Node::Look { ahead: true, negative: false, sub } if last => sequences(sub, true, budget)?,
            Node::Look { ahead: true, negative: true, sub } if last => {
                let inner = sequences(sub, true, budget)?;
                let refs: Vec<&[Elem]> = inner.iter().map(Vec::as_slice).collect();
                match good(&refs, 0, budget)? {
                    Some(node) => node.sequences(budget)?,
                    None => Vec::new(),
                }
            }
            _ => {
                return Err("contenu d'assertion non élémentaire (groupe capturant, répétition non bornée, \
                            assertion imbriquée hors de la dernière position…) / non-elementary assertion content"
                    .into())
            }
        };
        acc = concat(&acc, &options, budget)?;
    }
    Ok(acc)
}

/// Produit de deux ensembles de séquences ; rien ne suit la fin du texte. Les bornes sont vérifiées à chaque
/// séquence produite, jamais après coup. Product of two sets of sequences; nothing follows the end of the text.
/// The bounds are checked at each sequence produced, never afterwards.
fn concat(left: &[Vec<Elem>], right: &[Vec<Elem>], budget: &mut Budget) -> Result<Vec<Vec<Elem>>, String> {
    let mut out: Vec<Vec<Elem>> = Vec::new();
    for a in left {
        let a_ranges = ranges_of(a);
        'next: for b in right {
            budget.spend(a.len() + b.len() + 1)?;
            budget.copy(a_ranges + ranges_of(b))?;
            let mut seq = a.clone();
            for e in b {
                match (seq.last(), e) {
                    (Some(Elem::End), Elem::End) => {}
                    // Un caractère après la fin du texte : séquence impossible / a character after the end: impossible.
                    (Some(Elem::End), Elem::Class(_)) => continue 'next,
                    _ => seq.push(e.clone()),
                }
            }
            if out.len() == MAX_SEQUENCES || seq.len() > MAX_LENGTH {
                return Err(too_large());
            }
            out.push(seq);
        }
    }
    Ok(out)
}

/// Continuations permises à une profondeur de l'arbre des séquences interdites.
/// Permitted continuations at one depth of the trie of forbidden sequences.
struct Good(Vec<Allowed>);

enum Allowed {
    /// Fin du texte / end of the text.
    End,
    /// Un caractère qui écarte toutes les séquences interdites / a character that rules out every forbidden one.
    Char(ClassUnicode),
    /// Un caractère, puis la suite / a character, then what follows.
    Step(ClassUnicode, Good),
}

/// Complément de l'arbre : None si aucune continuation n'est permise. Les alternatives commencent par des
/// caractères disjoints (ou la fin) : leur ordre est indifférent. Complement of the trie: None if no continuation
/// is permitted. Alternatives start with disjoint characters (or the end): their order does not matter.
/// Le complément peut croître exponentiellement avec la profondeur : chaque nœud et chaque région examinée
/// coûtent un pas. The complement may grow exponentially with depth: each node and region examined costs a step.
fn good(bad: &[&[Elem]], depth: usize, budget: &mut Budget) -> Result<Option<Good>, String> {
    budget.spend(1)?;
    if bad.iter().any(|seq| seq.len() == depth) {
        return Ok(None); // une séquence interdite est complète / a forbidden sequence is complete
    }
    let mut allowed = Vec::new();
    if !bad.iter().any(|seq| seq[depth] == Elem::End) {
        allowed.push(Allowed::End);
    }
    // Régions : intersections des classes à cette profondeur, avec les séquences qui les contiennent.
    // Regions: intersections of the classes at this depth, with the sequences containing them.
    let mut regions: Vec<(ClassUnicode, Vec<usize>)> = Vec::new();
    let mut covered = ClassUnicode::empty();
    for (i, seq) in bad.iter().enumerate() {
        let Elem::Class(class) = &seq[depth] else { continue };
        budget.spend(regions.len() + 1)?;
        // Classes nouvelles : au plus celle-ci et les régions qu'elle coupe / new classes: this one, cut regions.
        budget.copy(class.ranges().len() + regions.iter().map(|(region, _)| region.ranges().len()).sum::<usize>())?;
        let mut fresh = class.clone();
        let mut next = Vec::with_capacity(regions.len() + 1);
        for (region, members) in regions {
            let inside = intersect(&region, class);
            let outside = difference(&region, class);
            if !is_empty(&inside) {
                fresh.difference(&inside);
                let mut members_in = members.clone();
                members_in.push(i);
                next.push((inside, members_in));
            }
            if !is_empty(&outside) {
                next.push((outside, members));
            }
        }
        if !is_empty(&fresh) {
            next.push((fresh, vec![i]));
        }
        regions = next;
        covered.union(class);
    }
    let rest = difference(&full(), &covered);
    if !is_empty(&rest) {
        allowed.push(Allowed::Char(rest));
    }
    // Même ensemble de séquences : régions fusionnées / same sequence set: regions merged.
    regions.sort_by(|a, b| a.1.cmp(&b.1));
    let mut merged: Vec<(ClassUnicode, Vec<usize>)> = Vec::new();
    for (region, members) in regions {
        match merged.last_mut() {
            Some((class, last)) if *last == members => class.union(&region),
            _ => merged.push((region, members)),
        }
    }
    for (region, members) in merged {
        let child: Vec<&[Elem]> = members.iter().map(|&i| bad[i]).collect();
        if let Some(next) = good(&child, depth + 1, budget)? {
            allowed.push(Allowed::Step(region, next));
        }
    }
    Ok((!allowed.is_empty()).then_some(Good(allowed)))
}

impl Good {
    fn hir(&self) -> Hir {
        Hir::alternation(
            self.0
                .iter()
                .map(|allowed| match allowed {
                    Allowed::End => Hir::look(Look::End),
                    Allowed::Char(class) => Hir::class(Class::Unicode(class.clone())),
                    Allowed::Step(class, next) => {
                        Hir::concat(vec![Hir::class(Class::Unicode(class.clone())), next.hir()])
                    }
                })
                .collect(),
        )
    }

    /// Caractères consommés au plus / most characters consumed.
    fn depth(&self) -> usize {
        self.0
            .iter()
            .map(|allowed| match allowed {
                Allowed::End => 0,
                Allowed::Char(_) => 1,
                Allowed::Step(_, next) => 1 + next.depth(),
            })
            .max()
            .unwrap_or(0)
    }

    /// Séquences du complément, bornées comme celles de `sequences` / the complement's sequences, bounded alike.
    fn sequences(&self, budget: &mut Budget) -> Result<Vec<Vec<Elem>>, String> {
        let mut out = Vec::new();
        for allowed in &self.0 {
            match allowed {
                Allowed::End => out.push(vec![Elem::End]),
                Allowed::Char(class) => {
                    budget.copy(class.ranges().len())?;
                    out.push(vec![Elem::Class(class.clone())]);
                }
                Allowed::Step(class, next) => {
                    for mut tail in next.sequences(budget)? {
                        budget.spend(tail.len() + 1)?;
                        budget.copy(class.ranges().len())?;
                        tail.insert(0, Elem::Class(class.clone()));
                        out.push(tail);
                    }
                }
            }
            if out.len() > MAX_SEQUENCES {
                return Err(too_large());
            }
        }
        Ok(out)
    }
}

// --- Tête : contraintes sur le caractère précédent / start: constraints on the previous character ----------

/// Résultat d'une assertion de tête / outcome of a leading assertion.
enum Outcome {
    /// Toujours vraie (retirée) / always true (removed).
    True,
    /// Toujours fausse : ce chemin ne correspond jamais / always false: this path never matches.
    False,
    /// Vraie si le caractère précédent est dans la classe ; `at_start` : valeur sans caractère précédent.
    /// True if the previous character is in the class; `at_start`: value without a previous character.
    Previous(ClassUnicode, bool),
}

/// Pose un marqueur `Start` en tête de chaque alternative de départ, filtre compris ; descend dans les groupes
/// et alternatives de tête. Places a `Start` marker at the head of each start path, filter included; descends
/// into leading groups and alternations.
fn start(mut nodes: Vec<Node>, word: &ClassUnicode, depth: usize, budget: &mut Budget) -> Result<Vec<Node>, String> {
    if depth > 64 {
        return Err("motif trop imbriqué / pattern nested too deeply".into());
    }
    match nodes.first_mut() {
        Some(Node::Group { sub, .. }) => {
            *sub = start(std::mem::take(sub), word, depth + 1, budget)?;
            return Ok(nodes);
        }
        Some(Node::Branch(alternatives)) => {
            for alternative in alternatives.iter_mut() {
                *alternative = start(std::mem::take(alternative), word, depth + 1, budget)?;
            }
            return Ok(nodes);
        }
        _ => {}
    }
    let mut filter = Filter::any();
    let mut consumed: Vec<ClassUnicode> = Vec::new();
    let mut kept = Vec::with_capacity(nodes.len() + 1);
    let mut prefix = true;
    for i in 0..nodes.len() {
        if !prefix {
            kept.push(nodes[i].clone());
            continue;
        }
        let outcome = match &nodes[i] {
            node @ (Node::Literal(_) | Node::Set(_)) => {
                consumed.extend(node.atom());
                kept.push(node.clone());
                continue;
            }
            Node::Repeat { min: 0, max: Some(1), greedy, sub }
                if sub.len() == 1 && sub[0].atom().is_some() && needs_context(&nodes[i + 1..]) =>
            {
                // Caractère facultatif avant une assertion : les deux chemins, dans l'ordre de `re`. Chaque
                // développement double les chemins : leur nombre est borné. Optional character before an
                // assertion: both paths, in `re`'s order. Each expansion doubles the paths: their number is bounded.
                budget.optionals = budget.optionals.checked_sub(1).ok_or(
                    "trop de caractères facultatifs avant une assertion / too many optional characters before an \
                     assertion",
                )?;
                budget.spend(2 * nodes.len())?;
                budget.copy(2 * node_ranges(&nodes))?;
                let with: Vec<Node> = nodes[..i].iter().chain(sub).chain(&nodes[i + 1..]).cloned().collect();
                let without: Vec<Node> = nodes[..i].iter().chain(&nodes[i + 1..]).cloned().collect();
                let alternatives = if *greedy { vec![with, without] } else { vec![without, with] };
                return start(vec![Node::Branch(alternatives)], word, depth + 1, budget);
            }
            Node::Look { ahead: false, negative, sub } => behind(sub, &consumed, *negative)?,
            Node::At(kind @ (At::Boundary | At::NotBoundary)) => {
                match edge_of(&nodes[i + 1..], true) {
                    Some(next) => boundary(*kind == At::Boundary, consumed.last(), &next, word)?,
                    None => {
                        // Rien de connu après : affaire de la fin ou du contrôle final / left to the end or the check.
                        prefix = false;
                        kept.push(nodes[i].clone());
                        continue;
                    }
                }
            }
            _ => {
                prefix = false;
                kept.push(nodes[i].clone());
                continue;
            }
        };
        match outcome {
            Outcome::True => {}
            Outcome::False => return Ok(vec![Node::Set(ClassUnicode::empty())]),
            Outcome::Previous(class, at_start) => {
                filter.previous.intersect(&class);
                filter.at_start &= at_start;
            }
        }
    }
    kept.insert(0, Node::Start(filter));
    Ok(kept)
}

/// Une assertion de tête suit-elle, après de simples caractères ? / does a leading assertion follow single chars?
fn needs_context(rest: &[Node]) -> bool {
    for node in rest {
        match node {
            Node::Look { ahead: false, .. } | Node::At(At::Boundary | At::NotBoundary) => return true,
            Node::Literal(_) | Node::Set(_) => {}
            Node::Repeat { min: 0, max: Some(1), sub, .. } if sub.len() == 1 && sub[0].atom().is_some() => {}
            _ => return false,
        }
    }
    false
}

/// Classes d'un contenu de look-behind de longueur fixe / classes of a fixed-length look-behind content.
fn fixed_classes(nodes: &[Node], out: &mut Vec<ClassUnicode>) -> Result<(), String> {
    for node in nodes {
        match node {
            Node::Literal(_) | Node::Set(_) => out.extend(node.atom()),
            Node::Group { index: None, sub } => fixed_classes(sub, out)?,
            Node::Repeat { min, max: Some(max), sub, .. } if min == max && *max <= MAX_EXPANDED_REPEAT => {
                for _ in 0..*max {
                    fixed_classes(sub, out)?;
                }
            }
            Node::Branch(alternatives) if alternatives.iter().all(|alt| alt.len() == 1 && alt[0].atom().is_some()) => {
                let mut union = ClassUnicode::empty();
                for alternative in alternatives {
                    union.union(&alternative[0].atom().unwrap_or_else(ClassUnicode::empty));
                }
                out.push(union);
            }
            _ => return Err("look-behind non élémentaire / non-elementary look-behind".into()),
        }
        if out.len() > MAX_LENGTH {
            return Err("look-behind trop long / look-behind too long".into());
        }
    }
    Ok(())
}

/// Look-behind de tête : les caractères déjà consommés sont connus, au plus un est lu avant la correspondance.
/// Leading look-behind: the characters already consumed are known, at most one is read before the match.
fn behind(sub: &[Node], consumed: &[ClassUnicode], negative: bool) -> Result<Outcome, String> {
    let mut classes = Vec::new();
    fixed_classes(sub, &mut classes)?;
    let (k, m) = (classes.len(), consumed.len());
    let known = k.min(m);
    // Partie lue dans la correspondance : certaine, impossible, ou indécise / the part read inside the match.
    let mut certain = true;
    for (inside, wanted) in consumed[m - known..].iter().zip(&classes[k - known..]) {
        if disjoint(inside, wanted) {
            return Ok(if negative { Outcome::True } else { Outcome::False });
        }
        certain &= subset(inside, wanted);
    }
    if !certain {
        return Err("look-behind sur une classe en partie concernée / look-behind on a partly matching class".into());
    }
    Ok(match (k - known, negative) {
        (0, false) => Outcome::True,
        (0, true) => Outcome::False,
        // Sans caractère précédent, `re` ne trouve pas le contenu : une négation réussit.
        // Without a previous character `re` cannot match the content: a negation succeeds.
        (1, false) => Outcome::Previous(classes[0].clone(), false),
        (1, true) => Outcome::Previous(negated(&classes[0]), true),
        _ => return Err("look-behind avant le caractère précédent / look-behind beyond the previous character".into()),
    })
}

/// `\b` ou `\B` de tête : `last` est le caractère consommé avant (None : le caractère précédent du texte),
/// `next` la classe du suivant. Leading `\b` or `\B`: `last` is the character consumed before (None: the text's
/// previous character), `next` the class of the following one.
fn boundary(
    is_boundary: bool,
    last: Option<&ClassUnicode>,
    next: &ClassUnicode,
    word: &ClassUnicode,
) -> Result<Outcome, String> {
    let purity = |class: &ClassUnicode| -> Result<bool, String> {
        if subset(class, word) {
            Ok(true)
        } else if disjoint(class, word) {
            Ok(false)
        } else {
            Err("\\b entre classes mixtes / \\b between mixed classes".into())
        }
    };
    let next_word = purity(next)?;
    match last {
        Some(last) => {
            let differ = purity(last)? != next_word;
            Ok(if differ == is_boundary { Outcome::True } else { Outcome::False })
        }
        None => {
            // `\b` vrai si le précédent diffère du suivant ; au début du texte, le précédent n'est pas un mot.
            // `\b` holds when the previous differs from the next; at the text start the previous is not a word.
            let previous_word = next_word != is_boundary;
            let class = if previous_word { word.clone() } else { negated(word) };
            Ok(Outcome::Previous(class, !previous_word))
        }
    }
}

/// Refuse toute assertion restante hors des formes exactes, et les répétitions d'un sous-motif pouvant être
/// vide (règles d'itération vide différentes). Refuses any assertion left outside the exact forms, and the
/// repetition of a possibly empty sub-pattern (different empty-iteration rules).
fn check(nodes: &[Node], inside_assertion: bool) -> Result<(), String> {
    for node in nodes {
        match node {
            Node::Look { ahead: true, .. } => {
                return Err("look-ahead ailleurs qu'en fin de motif / look-ahead elsewhere than at the end".into())
            }
            Node::Look { ahead: false, .. } => {
                return Err("look-behind ailleurs qu'en tête de motif / look-behind elsewhere than at the start".into())
            }
            Node::At(At::End) => return Err(dollar_elsewhere()),
            Node::At(At::Boundary | At::NotBoundary) => {
                return Err("\\b ou \\B à une position non résolue / \\b or \\B at an unresolved position".into())
            }
            Node::Group { index: Some(_), .. } if inside_assertion => {
                return Err("groupe capturant dans une assertion / capturing group inside an assertion".into())
            }
            Node::Repeat { max, sub, .. } if max.is_none_or(|max| max > 1) && super::node::nullable(sub) => {
                return Err(
                    "répétition d'un sous-motif pouvant être vide / repetition of a possibly empty sub-pattern".into()
                )
            }
            Node::Repeat { sub, .. } | Node::Group { sub, .. } => check(sub, inside_assertion)?,
            Node::Branch(alternatives) => {
                for alternative in alternatives {
                    check(alternative, inside_assertion)?;
                }
            }
            Node::Literal(_) | Node::Set(_) | Node::At(_) | Node::Start(_) | Node::Post(_) => {}
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use regex_syntax::hir::ClassUnicodeRange;

    use super::*;

    fn class(lo: char, hi: char) -> ClassUnicode {
        ClassUnicode::new([ClassUnicodeRange::new(lo, hi)])
    }

    #[test]
    fn complement_of_forbidden_sequences() {
        let digit = class('0', '9');
        // (?![ .\-]?[0-9])
        let bad = [
            vec![Elem::Class(digit.clone())],
            vec![
                Elem::Class(ClassUnicode::new([ClassUnicodeRange::new(' ', ' '), ClassUnicodeRange::new('-', '.')])),
                Elem::Class(digit.clone()),
            ],
        ];
        let refs: Vec<&[Elem]> = bad.iter().map(Vec::as_slice).collect();
        let budget = &mut Budget::new();
        let node = good(&refs, 0, budget).expect("within budget").expect("some continuation");
        assert_eq!(node.depth(), 2);
        let sequences = node.sequences(budget).expect("within budget");
        assert!(sequences.contains(&vec![Elem::End]));
        assert!(!sequences.iter().any(|s| s.first() == Some(&Elem::Class(digit.clone()))));
    }

    #[test]
    fn forbidding_everything_leaves_nothing() {
        let bad = [vec![Elem::Class(full())], vec![Elem::End]];
        let refs: Vec<&[Elem]> = bad.iter().map(Vec::as_slice).collect();
        assert!(good(&refs, 0, &mut Budget::new()).expect("within budget").is_none());
    }

    #[test]
    fn leading_look_behind_becomes_a_filter() {
        let alnum = ClassUnicode::new([ClassUnicodeRange::new('0', '9'), ClassUnicodeRange::new('A', 'Z')]);
        let lookbehind =
            Node::Look { ahead: false, negative: true, sub: vec![Node::Set(alnum.clone()), Node::Set(alnum.clone())] };
        let nodes = vec![Node::Set(class('A', 'Z')), lookbehind, Node::Set(class('0', '9'))];
        let out = start(nodes, &alnum, 0, &mut Budget::new()).expect("supported");
        match &out[0] {
            Node::Start(filter) => assert!(filter.at_start && filter.previous == negated(&alnum)),
            other => panic!("{other:?}"),
        }
        assert_eq!(out.len(), 3);
    }

    #[test]
    fn ambiguous_shapes_are_refused() {
        let digit = class('0', '9');
        // Look-behind après une répétition : refusé / after a repetition: refused.
        let nodes = vec![
            Node::Repeat { min: 1, max: None, greedy: true, sub: vec![Node::Set(digit.clone())] },
            Node::Look { ahead: false, negative: true, sub: vec![Node::Set(digit.clone())] },
        ];
        assert!(rewrite(nodes, &digit).is_err());
        let empty_loop = vec![Node::Repeat {
            min: 0,
            max: None,
            greedy: true,
            sub: vec![Node::Branch(vec![vec![], vec![Node::Literal('a')]])],
        }];
        assert!(rewrite(empty_loop, &digit).is_err());
    }

    /// Motifs courts et hostiles : refusés vite, sans temps exponentiel ni gigaoctets (règles personnalisées).
    /// Short hostile patterns: refused quickly, without exponential time or gigabytes (custom rules).
    #[test]
    fn hostile_shapes_stay_bounded() {
        let digit = class('0', '9');
        let ab = Node::Set(class('a', 'b'));
        let optional = |node: &Node| Node::Repeat { min: 0, max: Some(1), greedy: true, sub: vec![node.clone()] };
        let exactly =
            |node: &Node, n: u32| Node::Repeat { min: n, max: Some(n), greedy: true, sub: vec![node.clone()] };
        // a?a?…a?(?<!x)b : chaque caractère facultatif doublait les chemins / each optional character doubled paths.
        let mut nodes: Vec<Node> = (0..40).map(|_| optional(&Node::Literal('a'))).collect();
        nodes.push(Node::Look { ahead: false, negative: true, sub: vec![Node::Literal('x')] });
        nodes.push(Node::Literal('b'));
        assert!(rewrite(nodes, &digit).is_err_and(|e| e.contains("optional")));
        // x(?![ab]{16}|ac|[ab]ac|[ab]{2}ac|…) : complément exponentiel en profondeur / exponential complement.
        let mut alternatives = vec![vec![exactly(&ab, 16)]];
        alternatives.extend((0..16).map(|k| vec![exactly(&ab, k), Node::Literal('a'), Node::Literal('c')]));
        let look = Node::Look { ahead: true, negative: true, sub: vec![Node::Branch(alternatives)] };
        assert!(rewrite(vec![Node::Literal('x'), look], &digit).is_err_and(|e| e.contains("too large")));
        // x(?!(?:\w\W|\s){9}(?:\w\W|\s){9}) : 512 x 512 séquences, jamais construites / never built.
        let pair = Node::Branch(vec![vec![Node::Set(full()), Node::Set(digit.clone())], vec![Node::Literal(' ')]]);
        let look = Node::Look { ahead: true, negative: true, sub: vec![exactly(&pair, 9), exactly(&pair, 9)] };
        assert!(rewrite(vec![Node::Literal('x'), look], &digit).is_err_and(|e| e.contains("too large")));
        // Les formes des packs restent acceptées / the packs' shapes are still accepted.
        let not_digits = Node::Look {
            ahead: true,
            negative: true,
            sub: vec![optional(&Node::Literal(' ')), exactly(&Node::Set(digit.clone()), 3)],
        };
        assert!(rewrite(vec![exactly(&Node::Set(digit.clone()), 2), not_digits], &digit).is_ok());
    }

    /// Classes de 748 intervalles (le `\w` de Python) : la mémoire, comptée en intervalles, reste bornée.
    /// 748-range classes (Python's `\w`): memory, counted in ranges, stays bounded.
    #[test]
    fn copied_classes_are_charged_by_size() {
        let ranges = (0..748u32).filter_map(|i| char::from_u32(0x41 + 3 * i)).map(|c| ClassUnicodeRange::new(c, c));
        let word = ClassUnicode::new(ranges);
        let other = negated(&word);
        // x(?!(?:\w\W|\W\w){9}) : 512 séquences de 18 classes, refusées avant d'en garder des centaines de Mo.
        // 512 sequences of 18 classes, refused before keeping hundreds of MB.
        let pair = Node::Branch(vec![
            vec![Node::Set(word.clone()), Node::Set(other.clone())],
            vec![Node::Set(other), Node::Set(word.clone())],
        ]);
        let look = Node::Look {
            ahead: true,
            negative: true,
            sub: vec![Node::Repeat { min: 9, max: Some(9), greedy: true, sub: vec![pair] }],
        };
        assert!(rewrite(vec![Node::Literal('x'), look], &word).is_err_and(|e| e.contains("too large")));
        // Une seule négation de `\w` reste acceptée / a single negated `\w` is still accepted.
        let simple = Node::Look { ahead: true, negative: true, sub: vec![Node::Set(word.clone())] };
        assert!(rewrite(vec![Node::Literal('x'), simple], &word).is_ok());
    }

    /// Suffixe d'une branche finale, copié pour chaque chemin des caractères facultatifs de tête : compté par taille.
    /// A final branch's suffix, copied for every path of the leading optional characters: charged by size.
    #[test]
    fn copied_suffixes_are_charged_by_size() {
        let ranges = (0..748u32).filter_map(|i| char::from_u32(0x41 + 3 * i)).map(|c| ClassUnicodeRange::new(c, c));
        let word = ClassUnicode::new(ranges);
        let digit = Node::Set(class('0', '9'));
        // \d?\d?\d?\d?\d?(?<![x])y(?:a(?=\w\W…)|b) : 32 chemins, chacun avec le suffixe / 32 paths, each with the suffix.
        let pattern = |pairs: usize| {
            let mut nodes: Vec<Node> =
                (0..5).map(|_| Node::Repeat { min: 0, max: Some(1), greedy: true, sub: vec![digit.clone()] }).collect();
            nodes.push(Node::Look { ahead: false, negative: true, sub: vec![Node::Literal('x')] });
            nodes.push(Node::Literal('y'));
            let sub = (0..pairs).flat_map(|_| [Node::Set(word.clone()), Node::Set(negated(&word))]).collect();
            let look = Node::Look { ahead: true, negative: false, sub };
            nodes.push(Node::Branch(vec![vec![Node::Literal('a'), look], vec![Node::Literal('b')]]));
            nodes
        };
        // 232 classes de 748 intervalles, 32 fois : refusé avant la copie / refused before copying.
        assert!(rewrite(pattern(116), &word).is_err_and(|e| e.contains("too large")));
        assert!(rewrite(pattern(1), &word).is_ok());
    }

    #[test]
    fn dollar_is_exact_only_in_final_position() {
        let digit = class('0', '9');
        let space = Node::Set(class(' ', ' '));
        // (?!$\n) et (?!(?:$)\n) : refusés (le `$` développé y consommait le « \n ») / refused.
        for sub in [
            vec![Node::At(At::End), Node::Literal('\n')],
            vec![Node::Group { index: None, sub: vec![Node::At(At::End)] }, Node::Literal('\n')],
        ] {
            let look = Node::Look { ahead: true, negative: true, sub };
            assert!(rewrite(vec![Node::Literal('x'), look], &digit).is_err_and(|e| e.contains('$')));
        }
        // (?!\n$), (?=\s|$), (?=$), (?=[.,;]|$) : acceptés, suffixe consommé / accepted, consumed suffix.
        let accepted = [
            Node::Look { ahead: true, negative: true, sub: vec![Node::Literal('\n'), Node::At(At::End)] },
            Node::Look {
                ahead: true,
                negative: false,
                sub: vec![Node::Branch(vec![vec![space.clone()], vec![Node::At(At::End)]])],
            },
            Node::Look { ahead: true, negative: false, sub: vec![Node::At(At::End)] },
            Node::Look { ahead: true, negative: false, sub: vec![Node::At(At::Boundary)] },
        ];
        for look in accepted {
            let rewritten = rewrite(vec![Node::Set(digit.clone()), look], &digit).expect("accepted");
            assert!(rewritten.post.is_some() && matches!(rewritten.nodes.last(), Some(Node::Post(_))));
        }
        // (?:$|\s) final : chaque branche porte son suffixe / each branch carries its suffix.
        let branch = Node::Branch(vec![vec![Node::At(At::End)], vec![space]]);
        let rewritten = rewrite(vec![Node::Set(digit.clone()), branch], &digit).expect("final alternation");
        assert_eq!(rewritten.post, Some(Some(1)));
        let Some(Node::Branch(alternatives)) = rewritten.nodes.last() else { panic!("branch expected") };
        assert!(alternatives.iter().all(|alt| matches!(alt.last(), Some(Node::Post(_)))));
        // Dans un groupe capturant, le suffixe se mêlerait au groupe : refusé / inside a capturing group: refused.
        let captured = Node::Group { index: Some(1), sub: vec![Node::Branch(vec![vec![Node::At(At::End)], vec![]])] };
        assert!(rewrite(vec![Node::Set(digit.clone()), captured], &digit).is_err());
    }
}
