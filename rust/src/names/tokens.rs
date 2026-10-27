//! Jetons capitalisés et suites de jetons : `_tokens`, `_dotted_forms`, `_joins`, `_runs`, `_merge`, `_split`.
//!
//! Capitalised tokens and runs of tokens. Clés en arène, éléments `Copy` : aucune allocation par jeton.
//! Keys live in an arena and elements are `Copy`: no allocation per token.

use super::chars::{eq, is_blank, sub, CharCursor, ALPHA, CAP};
use super::lexicon::{Kind, AMB_ENTITY, AMB_NONE, AMB_WORD};
use super::patterns;
use super::vocab::flag;
use super::{inside, Doc, Element, Keys, MAX_RUN, NONE, SURNAME_ALONE_MIN};
use crate::unicode::DIGIT;

/// Suite de jetons qui peut former un nom (`_Run`) : les éléments `elements[from..to]`.
/// Capitalised tokens that may form one name: elements `elements[from..to]`.
pub(super) struct Run {
    pub from: usize,
    pub to: usize,
    pub cap_left: bool,
    pub cap_right: bool,
    pub evidence: i8,
    pub score: f64,
    /// Désigné par un rôle ou interpellé (« Bonjour Nath, ») / named by a role or vocative.
    pub addressed: bool,
    /// Valeur d'une étiquette de champ (« Nom : … ») / value of a field label.
    pub labelled: bool,
}

/// Position couverte par une forme juridique à points / position inside a dotted legal form.
fn covers(forms: &[(usize, usize)], pos: usize) -> bool {
    let i = forms.partition_point(|&(start, _)| start <= pos);
    i > 0 && pos < forms[i - 1].1
}

/// `_split` : sépare deux personnes accolées et retire un lieu en bordure (au plus deux parties).
/// Splits adjacent persons, trims places at the edges (at most two parts, as index ranges).
fn split(e: &[Element]) -> [Option<(usize, usize)>; 2] {
    // « Olivier Blanchard Jean Tirole » (bibliographie) / two persons side by side.
    if e.len() == 4
        && e.iter().all(|x| x.kind == Kind::Name)
        && e[0].given() > 0
        && e[2].given() > 0
        && e[1].surname() > 0
        && e[3].surname() > 0
        && e[2].given() > e[2].surname()
        && e[1].surname() >= e[1].given()
    {
        return [Some((0, 2)), Some((2, 4))];
    }
    let (mut a, mut b) = (0, e.len());
    if e.iter().filter(|x| x.kind.is_name()).count() >= 3 {
        // En tête, un lieu ou un mot inconnu avant le prénom n'appartient pas au nom (« DeepMind Stuart
        // Russell ») ; en queue, un lieu non plus. A leading place or unknown word before the given name is cut.
        while b - a > 2
            && e[a].given() == 0
            && (e[a].kind == Kind::Unknown || (e[a].kind == Kind::Name && e[a].amb() == AMB_ENTITY))
            && e[a + 1..b].iter().any(|x| x.given() > 0)
        {
            a += 1;
        }
        if e[b - 1].kind == Kind::Name && e[b - 1].amb() == AMB_ENTITY && b - a > 2 {
            b -= 1;
        }
    }
    [Some((a, b)), None]
}

impl Doc<'_> {
    /// `_tokens` : jetons capitalisés classés, dans l'ordre du texte / classified capitalised tokens.
    pub(super) fn tokens(&self, keys: &mut Keys) -> Vec<Element> {
        let (det, text, folded) = (self.det, &self.text, &self.folded);
        let forms = if text.contains(&'.') { self.dotted_forms() } else { Vec::new() };
        let mut tokens: Vec<Element> = Vec::new();
        let mut pos = 0;
        // Un jeton commence par la classe `UPPER` : saut direct au prochain candidat / jump to the next candidate.
        while let Some(offset) = text[pos..].iter().position(|&c| det.chars.is(c, CAP)) {
            pos += offset;
            let Some(match_end) = patterns::token(&det.chars, text, pos) else {
                pos += 1;
                continue;
            };
            let mut start = pos;
            pos = match_end; // `finditer` reprend après la correspondance / resumes after the match
            if start > 1 && text[start - 1] == '-' && det.chars.is(text[start - 2], ALPHA) {
                continue; // fin d'un composé en minuscules (« anti-Macron ») / tail of a lowercase compound
            }
            let mut end = match_end;
            if end - start > 3 && folded[end - 2] == '\'' && folded[end - 1] == 's' {
                end -= 2; // possessif hors de la zone (« Johnson's ») / possessive kept outside the span
            }
            let (original, folded_key) = (&text[start..end], &folded[start..end]);
            let mut entry = det.vocab.get(folded_key);
            // « S.p.A. », « B.V. » : forme juridique ; « AVENANT N° 2 » : signe de numéro ; pas des initiales.
            // A dotted legal form or a number sign, not initials.
            // « Jean Dupont CLT-204518 » : la tête d'un code n'est jamais un nom (1.0.2) / the head of a code.
            let code_head = matches!(text.get(end), Some(&'-') | Some(&'_'))
                && text.get(end + 1).is_some_and(|&c| det.chars.is(c, DIGIT));
            let (mut kind, mut code) =
                if covers(&forms, start) || (eq(folded_key, "n") && text.get(end) == Some(&'°')) || code_head {
                    (Kind::Common, 0)
                } else if end - start == 1 && text.get(end) == Some(&'.') && !entry.has(flag::STOP) {
                    (Kind::Initial, 0) // « A. Lambert » : initiale, même si « a » est un mot / an initial
                } else {
                    det.classify(folded_key, original, entry)
                };
            let wrapped = tokens.last().copied().filter(|left| {
                text.get(left.end) == Some(&'-')
                    && kind.is_name()
                    && left.kind.is_name()
                    && patterns::hyphen_wrap(sub(text, left.end, start))
            });
            let (key, caps) = match wrapped {
                // « Anne-⏎Sophie » : un seul nom composé, coupé en fin de ligne / one compound split by a line break.
                Some(left) => {
                    tokens.pop();
                    let left_text = &text[left.start..left.end];
                    let key = keys.extend(left.key, &[&['-'], folded_key]);
                    entry = det.vocab.get(keys.get(key));
                    (kind, code) = det.classify(keys.get(key), &[left_text, &['-'], original].concat(), entry);
                    start = left.start;
                    (key, end - start > 1 && det.chars.is_upper(&[left_text, original].concat()))
                }
                None => (keys.push(&[folded_key]), end - start > 1 && det.chars.is_upper(original)),
            };
            tokens.push(Element { start, end, kind, code, key, entry, caps });
        }
        self.compound_tokens(tokens, keys)
    }

    /// `_compound_tokens` : « Saint Quentin » (comme « Saint-Quentin ») et, après un prénom, « Le Verger » forment
    /// un seul élément inconnu. "Saint Quentin" (like "Saint-Quentin") and, after a given name, "Le Verger" make one
    /// unknown element.
    fn compound_tokens(&self, tokens: Vec<Element>, keys: &mut Keys) -> Vec<Element> {
        let (det, text) = (self.det, &self.text);
        let mut out: Vec<Element> = Vec::with_capacity(tokens.len());
        let mut k = 0;
        while k < tokens.len() {
            let token = tokens[k];
            if let Some(&next) = tokens.get(k + 1) {
                if eq(sub(text, token.end, next.start), " ") {
                    let saint = token.entry.has(flag::SAINT_WORD) && next.kind.is_name();
                    let particle = token.entry.has(flag::SURNAME_PARTICLE)
                        && det.chars.is_upper(&text[token.start..token.start + 1])
                        && out.last().is_some_and(|prev| {
                            prev.kind == Kind::Name
                                && prev.given() > 0
                                && prev.amb() != AMB_ENTITY
                                && eq(sub(text, prev.end, token.start), " ")
                        })
                        && next.kind == Kind::Common
                        && next.key.len() >= 2
                        && !next.entry.has(flag::STOP)
                        && !patterns::ordinal(&text[next.start..next.end]);
                    if saint || particle {
                        let joined: Vec<char> = [keys.get(token.key), &[' '][..], keys.get(next.key)].concat();
                        let key = keys.push(&[&joined]);
                        let entry = det.vocab.get(&joined);
                        out.push(Element {
                            start: token.start,
                            end: next.end,
                            kind: Kind::Unknown,
                            code: 0,
                            key,
                            entry,
                            caps: token.caps && next.caps,
                        });
                        k += 2;
                        continue;
                    }
                }
            }
            out.push(token);
            k += 1;
        }
        out
    }

    /// `_dotted_forms` : lettres des formes juridiques à points (« S.A.R.L. », « S.p.A. »), un passage
    /// Aho-Corasick sur le texte. Letters of dotted legal forms, one Aho-Corasick pass.
    fn dotted_forms(&self) -> Vec<(usize, usize)> {
        let (chars, text) = (&self.det.chars, &self.text);
        let mut cursor = CharCursor::new(self.text_utf8);
        let mut covered = Vec::new();
        for m in self.det.dotted_forms.find_iter(self.text_utf8) {
            let (start, end) = (cursor.at(m.start()), cursor.at(m.end()));
            let free_left = start == 0 || !chars.is_alnum(text[start - 1]);
            let free_right = end >= text.len() || !chars.is_alnum(text[end]);
            if free_left && free_right {
                covered.push((start, end));
            }
        }
        covered
    }

    /// `_joins` : deux jetons forment-ils un même nom (espace, particule, initiale) ? / same-name gap test.
    fn joins(&self, left: &Element, right: &Element) -> bool {
        let text = &self.text;
        let gap = sub(text, left.end, right.start);
        if eq(gap, " ") {
            return true;
        }
        if left.kind == Kind::Initial {
            return patterns::initial_gap(gap);
        }
        if gap.len() > patterns::MAX_SPACE_GAP {
            return false; // trop long pour les deux motifs : coût constant / too long for both patterns
        }
        if gap.contains(&'\n') {
            // Retour à la ligne forcé au milieu d'un nom : « Mme Claire⏎Martin-Dubois » / hard-wrapped name.
            return patterns::newline_gap(gap)
                && left.given() > 0
                && right.kind.is_name()
                && right.given() == 0
                && left.start > 0
                && text[left.start - 1] == ' ';
        }
        if !patterns::space_gap(gap) {
            return false;
        }
        if gap.contains(&'\t') && crate::text::tab_row_chars(text, left.end) {
            return false; // colonnes d'un tableau TSV : deux cellules, pas un nom (1.0.2) / TSV columns: two cells
        }
        if gap.iter().all(|&c| is_blank(c)) {
            return true;
        }
        // Après une particule vient un nom de famille (« de Gaulle »), pas un prénom ni un lieu.
        // After a particle comes a surname, not a given name nor a place.
        if right.kind == Kind::Unknown {
            return !(right.caps && right.key.len() <= 3); // « du FC Barcelone » : sigle / acronym
        }
        right.kind == Kind::Particle
            || (right.kind == Kind::Name
                && matches!(right.amb(), AMB_NONE | AMB_WORD)
                && right.surname() >= right.given())
    }

    /// `_runs` : suites de jetons pouvant former un nom ; les éléments sont rangés à plat.
    /// Runs of tokens that may form a name; elements are stored flat.
    pub(super) fn runs(
        &self,
        tokens: &[Element],
        claimed: &[(usize, usize)],
        keys: &mut Keys,
    ) -> (Vec<Element>, Vec<Run>) {
        let (det, text, n) = (self.det, &self.text, tokens.len());
        // Sans effet de bord, `_joins` est calculé une fois par paire voisine / side-effect free: once per pair.
        let joined: Vec<bool> = tokens.windows(2).map(|pair| self.joins(&pair[0], &pair[1])).collect();
        // Un mot de rôle ou de voie suivi d'un nom sert de déclencheur ; en capitales, c'est un nom de famille.
        // A role or street word before a name is a trigger; in capitals, a surname.
        let trigger: Vec<bool> = (0..n)
            .map(|i| {
                i + 1 < n
                    && tokens[i].entry.has(flag::CONTEXTUAL)
                    && !tokens[i].caps
                    && tokens[i + 1].kind != Kind::Common
                    && joined[i]
            })
            .collect();
        // Mot courant capitalisé voisin (« Mont Blanc ») ; ni contexte d'organisation ni ordinal (« Ier »).
        // Adjacent capitalised common word; organisation context and ordinals are not.
        let content: Vec<bool> = tokens
            .iter()
            .map(|t| {
                t.kind == Kind::Common
                    && !t.entry.has(flag::FUNCTION)
                    && !t.entry.has(flag::ORG_CONTEXT)
                    && !patterns::ordinal(&text[t.start..t.end])
            })
            .collect();
        let mut elements: Vec<Element> = Vec::with_capacity(n);
        let mut runs = Vec::new();
        let mut i = 0;
        while i < n {
            if tokens[i].kind == Kind::Common || trigger[i] {
                i += 1;
                continue;
            }
            let mut j = i;
            while j + 1 < n && j - i < MAX_RUN - 1 && tokens[j + 1].kind != Kind::Common && joined[j] && !trigger[j + 1]
            {
                j += 1;
            }
            let from = elements.len();
            self.merge(&tokens[i..=j], &mut elements, keys);
            let lead = elements[from];
            let rare = lead.kind == Kind::Unknown
                || (lead.kind == Kind::Name && lead.given() == 0 && lead.surname() < SURNAME_ALONE_MIN);
            let verb = || det.text_sets.verb_tails.iter().any(|tail| keys.get(lead.key).ends_with(tail));
            let first = if elements.len() - from > 1
                && rare
                && !lead.caps
                && verb()
                && elements[from + 1].given() > 0
                && self.sentence_start(lead.start)
            {
                from + 1 // « Appelle Pierre » : verbe en tête / leading verb
            } else {
                from
            };
            let group = &elements[first..];
            let useful = group.iter().any(|e| e.kind != Kind::Particle);
            if useful && !inside(claimed, group[0].start, group[group.len() - 1].end) {
                let cap_left = i > 0 && content[i - 1] && joined[i - 1];
                let cap_right = j + 1 < n && content[j + 1] && joined[j];
                for (a, b) in split(group).into_iter().flatten() {
                    runs.push(Run {
                        from: first + a,
                        to: first + b,
                        cap_left: cap_left && a == 0,
                        cap_right: cap_right && b == group.len(),
                        evidence: NONE,
                        score: 0.0,
                        addressed: false,
                        labelled: false,
                    });
                }
            }
            i = j + 1;
        }
        (elements, runs)
    }

    /// `_merge` : fusionne les noms à plusieurs mots connus (« Le Goff », « Da Silva »).
    /// Merges known multiword names, three words first.
    fn merge(&self, tokens: &[Element], out: &mut Vec<Element>, keys: &mut Keys) {
        if tokens.len() < 2 {
            out.extend_from_slice(tokens);
            return;
        }
        let mut joined_key: Vec<char> = Vec::new();
        let mut i = 0;
        while i < tokens.len() {
            let mut merged = None;
            for width in [3, 2] {
                let Some(group) = tokens.get(i..i + width) else {
                    continue;
                };
                if !group.windows(2).all(|pair| eq(sub(&self.text, pair[0].end, pair[1].start), " ")) {
                    continue;
                }
                joined_key.clear();
                for (k, token) in group.iter().enumerate() {
                    if k > 0 {
                        joined_key.push(' ');
                    }
                    joined_key.extend_from_slice(keys.get(token.key));
                }
                let entry = self.det.vocab.get(&joined_key);
                if let Some(code) = entry.name() {
                    let (start, end) = (group[0].start, group[width - 1].end);
                    let key = keys.push(&[&joined_key]);
                    let caps = group.iter().all(|t| t.caps);
                    merged = Some((Element { start, end, kind: Kind::Name, code, key, entry, caps }, width));
                    break;
                }
            }
            let (element, width) = merged.unwrap_or((tokens[i], 1));
            out.push(element);
            i += width;
        }
    }
}
