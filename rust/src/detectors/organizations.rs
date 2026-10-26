//! Organisations : transcription de la recherche de `heuristics/organizations.py` / organisation candidates.
//!
//! Rust repère les candidats (formes juridiques, suffixes, mots d'introduction, noms à gauche et à droite) ;
//! la décision (lexique des noms, règle physicomorale, contexte) reste dans `OrganizationDetector._spans`,
//! commune aux deux chemins. Rust finds the candidates; the decision (name lexicon, person-content rule,
//! context) stays in `OrganizationDetector._spans`, shared by both paths.

use std::collections::HashSet;
use std::sync::Arc;

use aho_corasick::{AhoCorasick, MatchKind};

use super::automaton;
use super::chars::{decode, CharCursor, Chars};
use super::unicode::UnicodeTable;

/// Longueur maximale d'un mot lu à rebours / maximum length of a word read backwards.
const MAX_WORD: usize = 42;
const MAX_PIECES: usize = 8;
/// `_OPENING` : la parenthèse, le guillemet ou le crochet borne le nom / opening marks bound the name.
const OPENING: [char; 6] = ['(', '«', '“', '"', '\'', '['];
/// `_FAMILY` développé (casse exacte) / `_FAMILY` expanded (exact case).
#[rustfmt::skip]
const FAMILY: [&str; 15] = [
    "Fils", "Filles", "Frères", "Freres", "Associés", "Associées", "Associes", "Associees", "Cie", "Compagnie", "Co",
    "Partners", "Partenaires", "Sons", "Söhne",
];
/// `_JOINER`, première branche (devant `_FAMILY`) puis seconde, dans l'ordre du motif / pattern order.
const FAMILY_JOINERS: [&str; 6] = ["&", "et", "and", "und", "y", "e"];
const NAME_JOINERS: [&str; 12] = ["de", "du", "des", "la", "le", "les", "en", "sur", "aux", "au", "of", "the"];
/// Préfixes de `_NAME_RIGHT_RE`, dans l'ordre du motif / `_NAME_RIGHT_RE` prefixes, pattern order.
const RIGHT_PREFIXES: [&str; 7] = ["du", "des", "de la", "de l'", "de", "d'", "l'"];

pub struct OrganizationData {
    /// `_CASE_PATTERNS` : formes juridiques puis suffixes / legal forms then suffixes.
    pub case_patterns: Vec<String>,
    pub forms: usize,
    pub sole_forms: HashSet<String>,
    pub prefix_forms: HashSet<String>,
    /// `sorted(ORG_KEYWORDS)`, sur le texte replié / on the folded text.
    pub keywords: Vec<String>,
    pub joiners: HashSet<String>,
    pub join_words: HashSet<String>,
    pub family: HashSet<String>,
    pub legal_form_keys: HashSet<String>,
    pub stop: HashSet<String>,
    pub name_articles: HashSet<String>,
    pub function: HashSet<String>,
    pub particles: HashSet<String>,
}

struct Form {
    sole: bool,
    prefix: bool,
}

pub struct OrganizationDetector {
    table: Arc<UnicodeTable>,
    cases: AhoCorasick,
    forms: Vec<Form>,
    keywords: AhoCorasick,
    data: OrganizationData,
}

/// Pièce d'un nom lu à rebours : début, fin, clé repliée sans points / piece read backwards.
struct Piece {
    start: usize,
    end: usize,
    key: String,
}

impl OrganizationDetector {
    pub fn new(data: OrganizationData, table: Arc<UnicodeTable>) -> Result<Self, String> {
        let forms = data.case_patterns[..data.forms.min(data.case_patterns.len())]
            .iter()
            .map(|form| Form { sole: data.sole_forms.contains(form), prefix: data.prefix_forms.contains(form) })
            .collect();
        Ok(Self {
            cases: automaton(&data.case_patterns, MatchKind::LeftmostLongest)?,
            keywords: automaton(&data.keywords, MatchKind::LeftmostLongest)?,
            forms,
            table,
            data,
        })
    }

    /// Candidats (début, fin, entrepreneur individuel), dans l'ordre de `OrganizationDetector.detect`.
    /// Candidates (start, end, sole trader), in `OrganizationDetector.detect` order.
    pub fn candidates(&self, text: &str, folded: &str) -> Result<Vec<(usize, usize, bool)>, String> {
        let (text_chars, folded_chars) = (decode(text), decode(folded));
        if text_chars.len() != folded_chars.len() {
            return Err("texte replié de longueur différente / folded text of another length".into());
        }
        let t = Chars::new(&text_chars, &self.table);
        let f = Chars::new(&folded_chars, &self.table);
        let mut found = Vec::new();
        let mut cursor = CharCursor::new(text);
        for m in self.cases.find_iter(text) {
            let (start, end) = (cursor.char_index(m.start()), cursor.char_index(m.end()));
            if !bounded(t, start, end) {
                continue;
            }
            match self.forms.get(m.pattern().as_usize()) {
                // Forme juridique : nom à gauche, ou à droite pour les formes françaises / name left, or right.
                Some(form) => {
                    if let Some((left, right)) = self.left_name(t, f, start) {
                        found.push((left, right, form.sole));
                    } else if form.prefix {
                        if let Some((left, right)) = self.right_name(t, f, end) {
                            found.push((left, right, form.sole));
                        }
                    }
                }
                // Suffixe (« & Fils », « Conseil ») / suffix.
                None => {
                    if let Some((left, _)) = self.left_name(t, f, start) {
                        found.push((left, end, false));
                    }
                }
            }
        }
        let mut cursor = CharCursor::new(folded);
        for m in self.keywords.find_iter(folded) {
            let (start, end) = (cursor.char_index(m.start()), cursor.char_index(m.end()));
            if !bounded(f, start, end) {
                continue;
            }
            if let Some((left, right)) = self.right_name(t, f, end) {
                // Mot capitalisé : il fait partie du nom / a capitalised cue word is part of the name.
                found.push((if t.test(start, |c| self.table.is_upper(c)) { start } else { left }, right, false));
            }
        }
        Ok(found)
    }

    fn key(f: Chars, start: usize, end: usize) -> String {
        f.s[start..end].iter().filter(|&&c| c != '.').collect()
    }

    /// `_left_name` : nom qui précède une forme juridique, lu mot à mot à rebours / name read backwards.
    fn left_name(&self, t: Chars, f: Chars, pos: usize) -> Option<(usize, usize)> {
        let d = &self.data;
        let mut end = pos;
        while end > 0 && t.test(end - 1, |c| matches!(c, ' ' | '\t' | ',')) {
            end -= 1;
        }
        if end == pos || end == 0 || !t.alnum(end - 1) {
            return None;
        }
        // Pièces du dernier mot au premier / pieces from the last word to the first.
        let mut pieces: Vec<Piece> = Vec::new();
        let mut cursor = end;
        while pieces.len() < MAX_PIECES {
            let mut start = cursor;
            while start > 0 && !t.space(start - 1) && cursor - start <= MAX_WORD {
                start -= 1;
            }
            if start > 0 && !t.space(start - 1) {
                break; // mot trop long / word too long
            }
            let opening = start < cursor && t.test(start, |c| OPENING.contains(&c));
            if opening {
                start += 1;
            }
            let key = Self::key(f, start, cursor);
            let accepted = word_fullmatch(Chars::new(&t.s[start..cursor], t.u))
                || pieces.last().is_some_and(|following| {
                    d.joiners.contains(&key) || (d.join_words.contains(&key) && d.family.contains(&following.key))
                });
            if !accepted {
                break;
            }
            pieces.push(Piece { start, end: cursor, key });
            if opening {
                break;
            }
            let mut gap = start;
            while gap > 0 && t.blank(gap - 1) && start - gap < 2 {
                gap -= 1;
            }
            if gap == start || gap == 0 || t.test(gap - 1, |c| c == '\n' || c == '\r') {
                break;
            }
            cursor = gap;
        }
        pieces.reverse();
        // Un nom ne commence pas par « de » ou « et » / a name never starts with a joiner.
        let mut first = 0;
        while first < pieces.len()
            && t.test(pieces[first].start, |c| self.table.is_lower(c))
            && (d.joiners.contains(&pieces[first].key) || d.join_words.contains(&pieces[first].key))
        {
            first += 1;
        }
        let pieces = &pieces[first..];
        // Après une autre forme juridique ou une civilité / after another legal form or an honorific.
        let cut = pieces
            .iter()
            .rposition(|p| d.legal_form_keys.contains(&p.key) || d.stop.contains(&p.key))
            .map_or(0, |i| i + 1);
        let mut pieces = &pieces[cut..];
        // Mots-outils en tête retirés, sauf l'article d'une raison sociale / leading function words dropped.
        while let Some(head) = pieces.first() {
            if d.name_articles.contains(&head.key)
                || !(d.function.contains(&head.key) || d.particles.contains(&head.key))
            {
                break;
            }
            pieces = &pieces[1..];
        }
        if !pieces.iter().any(|p| !d.function.contains(&p.key) && !d.particles.contains(&p.key)) {
            return None; // un article seul n'est pas un nom / an article alone is not a name
        }
        Some((pieces[0].start, pieces[pieces.len() - 1].end))
    }

    /// `_right_name` : nom qui suit un mot d'introduction ; s'arrête avant une forme juridique ou une civilité.
    /// Name after a cue word; stops before a legal form or an honorific.
    fn right_name(&self, t: Chars, f: Chars, pos: usize) -> Option<(usize, usize)> {
        let (start, group_end) = name_right(t, pos)?;
        let pieces = t.upto(group_end);
        let mut end = start;
        let mut cursor = start;
        while let Some((piece_start, piece_end)) = next_piece(pieces, cursor) {
            cursor = piece_end;
            let key = Self::key(f, piece_start, piece_end);
            if piece_start > start && (self.data.legal_form_keys.contains(&key) || self.data.stop.contains(&key)) {
                break;
            }
            if !self.data.particles.contains(&key) && !self.data.join_words.contains(&key) {
                end = piece_end; // dernier mot plein / last content word
            }
        }
        (end > start).then_some((start, end))
    }
}

/// `_bounded` : bornes de mot ; un « . » final tient lieu de borne / word bounds; a final '.' counts as one.
fn bounded(s: Chars, start: usize, end: usize) -> bool {
    if start > 0 && s.test(start - 1, |c| s.u.is_alnum(c) || matches!(c, '.' | '_' | '-' | '\'' | '’')) {
        return false;
    }
    end >= s.len() || !s.alnum(end) || s.is(end - 1, '.')
}

/// `_WORD` glouton en `p` : `[UPPER0-9](?:[\w&+-]|['’.](?=\w)){0,40}` (l'assertion voit toute la vue).
/// Greedy `_WORD` at `p` (the lookahead sees the whole view).
fn company_word(t: Chars, p: usize) -> Option<usize> {
    if !t.test(p, |c| t.u.is_capital(c) || c.is_ascii_digit()) {
        return None;
    }
    let mut i = p + 1;
    for _ in 0..40 {
        match t.get(i) {
            Some(c) if t.u.is_word(c) || matches!(c, '&' | '+' | '-') => i += 1,
            Some('\'' | '’' | '.') if t.word(i + 1) => i += 1,
            _ => break,
        }
    }
    Some(i)
}

/// `_WORD_RE.fullmatch(word)` : `_WORD|[dlDL]['’]_WORD` sur le mot seul / on the word alone.
fn word_fullmatch(word: Chars) -> bool {
    let n = word.len();
    company_word(word, 0) == Some(n)
        || (word.test(0, |c| matches!(c, 'd' | 'l' | 'D' | 'L'))
            && word.test(1, |c| c == '\'' || c == '’')
            && company_word(word, 2) == Some(n))
}

/// `(?=_FAMILY)` : `(?:Fils|…|Söhne)(?![\w])`.
fn family_at(t: Chars, at: usize) -> bool {
    FAMILY.iter().any(|w| t.literal(at, w) && !t.word(at + w.chars().count()))
}

/// Fins possibles de `_JOINER` en `i`, dans l'ordre du motif ; seule la plus longue suite d'espaces peut réussir.
/// Possible `_JOINER` ends at `i`, in pattern order; only the longest blank run can succeed.
fn joiner_ends(t: Chars, i: usize) -> Vec<usize> {
    let mut ends = Vec::new();
    for word in FAMILY_JOINERS {
        let j = i + word.chars().count();
        let gap = t.blanks(j, 2);
        if t.literal(i, word) && gap > 0 && family_at(t, j + gap) {
            ends.push(j + gap);
        }
    }
    for word in NAME_JOINERS {
        let j = i + word.len();
        let gap = t.blanks(j, 2);
        if t.literal(i, word) && gap > 0 {
            ends.push(j + gap);
        }
    }
    if t.test(i, |c| c == 'd' || c == 'l') && t.is(i + 1, '\'') {
        ends.push(i + 2);
    }
    ends
}

/// `_NAME` en `p` : `_WORD(?:[ \t]{1,2}_JOINER?_WORD){0,5}`.
fn name_end(t: Chars, p: usize) -> Option<usize> {
    let mut end = company_word(t, p)?;
    for _ in 0..5 {
        let gap = t.blanks(end, 2);
        if gap == 0 {
            break;
        }
        let q = end + gap;
        match joiner_ends(t, q).into_iter().find_map(|j| company_word(t, j)).or_else(|| company_word(t, q)) {
            Some(next) => end = next,
            None => break,
        }
    }
    Some(end)
}

/// `_NAME_RIGHT_RE.match(text, pos)` -> groupe 1 / group 1:
/// `[ \t]{1,2}[«"“]?[ \t]?((?:(?:du|des|de la|de l'|de|d'|l')[ \t]{0,2})?_NAME)`. Les choix non gloutons
/// laisseraient une espace ou un guillemet en tête du groupe, qui échouerait / non-greedy choices would leave a
/// blank or a quote at the head of the group, which fails.
fn name_right(t: Chars, pos: usize) -> Option<(usize, usize)> {
    let lead = t.blanks(pos, 2);
    if lead == 0 {
        return None;
    }
    let mut group = pos + lead;
    if t.test(group, |c| matches!(c, '«' | '"' | '“')) {
        group += 1;
    }
    if t.blank(group) {
        group += 1;
    }
    RIGHT_PREFIXES
        .iter()
        .filter(|prefix| t.literal(group, prefix))
        .find_map(|prefix| {
            let j = group + prefix.chars().count();
            name_end(t, j + t.blanks(j, 2))
        })
        .or_else(|| name_end(t, group))
        .map(|end| (group, end))
}

/// `_PIECE_RE` (`[^\s]+`) : prochaine pièce à partir de `from` dans la vue / next piece from `from`.
fn next_piece(t: Chars, from: usize) -> Option<(usize, usize)> {
    let start = from + t.s.get(from..)?.iter().position(|&c| !t.u.is_space(c))?;
    Some((start, start + t.run(start, usize::MAX, |c| !t.u.is_space(c))))
}
