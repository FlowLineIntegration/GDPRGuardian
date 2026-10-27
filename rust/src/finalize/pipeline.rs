//! Enchaînement après la détection : filtrage, fusion, résolution, propagation, positions d'origine.
//!
//! Post-detection pipeline: filtering, merging, resolution, propagation, original offsets
//! (`Anonymizer._finalize`, `analyze`, `analyze_segments`).

use std::collections::{HashMap, HashSet};

use memchr::memmem::Finder;

use super::chars::{Chars, ALNUM, ALPHA, SPACE, UPPER};
use super::indexed::IndexedText;
use super::propagate::{propagate, Segments};
use super::render::RenderRules;
use super::resolve::{apply_keep, filter, keep_after, keep_zones, merge_same_entity, resolve, KeepRules, Policy};
use super::selfcheck::output_check;
use super::span::Span;
use super::values::propagate_values;
use super::Unsupported;
use crate::unicode::LOWER;

/// Réglages d'un `Anonymizer`, fixés à la construction / an `Anonymizer`'s settings, fixed at construction.
pub struct Finalizer {
    pub policy: Policy,
    /// Présent si l'anonymiseur a des règles personnalisées / present when the anonymizer has custom rules.
    pub keep: Option<KeepRules>,
    /// `types.PRIORITY_PROPAGATED`.
    pub priority_propagated: i64,
    /// `None` : un opérateur n'est pas reproductible en natif, le rendu reste en Python.
    /// `None`: an operator cannot be reproduced natively, rendering stays in Python.
    pub render: Option<RenderRules>,
}

impl Finalizer {
    /// `Anonymizer._finalize` : zones finales, disjointes, triées par début / final spans, disjoint, by start.
    pub fn finalize(
        &self,
        chars: &Chars,
        text: &IndexedText,
        spans: Vec<Span>,
        segments: Option<&Segments>,
    ) -> Result<Vec<Span>, Unsupported> {
        let zones = self.keep.as_ref().and_then(|keep| keep_zones(keep, &spans));
        let spans = match &self.keep {
            Some(keep) => apply_keep(keep, zones.as_ref(), spans),
            None => spans,
        };
        let mut kept = filter(&self.policy, chars, text, spans);
        if kept.is_empty() {
            // Les initiales ne dépendent d'aucune zone / initials need no span.
            initials(chars, text, &mut kept);
            if let Some(keep) = &self.keep {
                keep_after(keep, zones.as_ref(), &mut kept);
            }
            return Ok(kept);
        }
        let resolved = resolve(&self.policy, chars, text, merge_same_entity(&self.policy, kept));
        let mut spans = propagate(chars, text, resolved, segments, self.priority_propagated)?;
        spans.sort_by_key(|s| s.start);
        let mut spans = propagate_values(chars, text, spans, segments, self.priority_propagated)?;
        drop_company_names(chars, text, &mut spans);
        extend_after_civility(chars, text, &mut spans);
        civility_surnames(chars, text, &mut spans);
        signature_names(chars, text, &mut spans);
        initials(chars, text, &mut spans);
        let mut spans = output_check(chars, text, spans)?; // contrôle final de sortie / output self-check
        if let Some(keep) = &self.keep {
            keep_after(keep, zones.as_ref(), &mut spans);
        }
        for span in &mut spans {
            if span.value.is_none() {
                span.value = Some(text.slice(span.start, span.end).to_owned());
            }
        }
        Ok(spans)
    }
}

/// `engine.COMPANY_FORMS` : formes juridiques de personne morale, même liste / legal-entity forms, same list.
const COMPANY_FORMS: &[&str] = &[
    "SAS", "SASU", "SARL", "SARLU", "EURL", "SCI", "SNC", "SCP", "SCM", "SELARL", "SELAS", "SELAFA", "GAEC", "EARL",
    "SCEA", "GIE", "SCOP", "SEM", "SPL", "SCA", "S.A.R.L.", "S.A.S.", "S.A.S.U.", "E.U.R.L.", "S.C.I.", "S.N.C.",
    "S.C.P.", "G.I.E.",
];
/// `engine.COMPANY_SUFFIX_FORMS`, en plus de `COMPANY_FORMS` / in addition to `COMPANY_FORMS`.
const COMPANY_SUFFIX_ONLY: &[&str] = &["SA", "S.A."];
/// `engine.PARTNERSHIP_FORMS` : sociétés civiles professionnelles et d'exercice libéral, même liste / same list.
const PARTNERSHIP_FORMS: &[&str] = &["SCP", "SELARL", "SELAS", "SELAFA", "SELURL", "SELCA", "SCM", "S.C.P."];
/// `engine._FIRM_LINK_RE` : séparateurs entre deux associés d'une firme / separators between two partners.
const FIRM_LINKS: &[&str] = &[",", "&", "et", "-", "–"];
/// `engine._FIRM_BLANKS` : un associé enchaîné est un nom seul d'un mot / a chained partner is a one-word surname.
const FIRM_BLANKS: [char; 6] = [' ', '\t', '\n', '\r', '\u{a0}', '\u{202f}'];

/// `engine._drop_company_names` : personnes qui portent une forme juridique de société, et associés suivants d'une
/// société civile professionnelle ou d'exercice libéral (`spans` triées, disjointes). Persons carrying a company
/// legal form, and the next partners of a professional partnership (`spans` sorted, disjoint).
fn drop_company_names(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    let mut firm_end: Option<usize> = None;
    spans.retain(|span| {
        if &*span.entity == "PERSON" {
            if firm_end.is_some_and(|end| end <= span.start && firm_link(text.slice(end, span.start)))
                && !text.slice(span.start, span.end).contains(FIRM_BLANKS)
            {
                firm_end = Some(span.end);
                return false;
            }
            if company_named(chars, text, span.start, span.end) {
                firm_end = form_right_before(chars, text, span.start, PARTNERSHIP_FORMS).then_some(span.end);
                return false;
            }
        }
        firm_end = None;
        true
    });
}

/// `_FIRM_LINK_RE.fullmatch` : `[ \t]{0,2}(?:,|&|et|-|–)[ \t]{1,2}`.
fn firm_link(gap: &str) -> bool {
    let rest = gap.trim_start_matches([' ', '\t']);
    if gap.len() - rest.len() > 2 {
        return false;
    }
    FIRM_LINKS
        .iter()
        .filter_map(|sep| rest.strip_prefix(sep))
        .any(|tail| (1..=2).contains(&tail.len()) && tail.chars().all(|c| c == ' ' || c == '\t'))
}

/// `(?<![\w.])(?:forms)[ \t]{1,2}\Z` juste avant `start` / a form and 1 or 2 blanks right before `start`.
fn form_right_before(chars: &Chars, text: &IndexedText, start: usize, forms: &[&str]) -> bool {
    let word = |c: char| chars.is(c, ALNUM) || c == '_';
    let head = text.slice(0, start);
    let blanks = head.chars().rev().take_while(|&c| c == ' ' || c == '\t').count();
    if !(1..=2).contains(&blanks) {
        return false;
    }
    let before = &head[..head.len() - blanks];
    forms.iter().any(|form| {
        before.strip_suffix(form).is_some_and(|rest| !rest.chars().next_back().is_some_and(|c| word(c) || c == '.'))
    })
}

/// `engine._company_named` : « SARL DUPONT », « DUPONT SARL » (1 ou 2 blancs) / a company legal form next to it.
fn company_named(chars: &Chars, text: &IndexedText, start: usize, end: usize) -> bool {
    let word = |c: char| chars.is(c, ALNUM) || c == '_';
    let blank = |c: char| c == ' ' || c == '\t';
    if titled_before(chars, text, start) {
        return false; // « M. Jean Dupont SARL » : une personne / a person
    }
    if form_right_before(chars, text, start, COMPANY_FORMS) {
        return true;
    }
    company_tail_ends(chars, text, end).into_iter().any(|tail| {
        let rest = text.tail(tail);
        let blanks = rest.chars().take_while(|&c| blank(c)).count();
        if !(1..=2).contains(&blanks) {
            return false;
        }
        // Forme suivie d'un mot capitalisé (« Dupont SARL Lumière ») : elle appartient à ce nom-là / it belongs to
        // that next name.
        COMPANY_FORMS.iter().chain(COMPANY_SUFFIX_ONLY).any(|form| {
            rest[blanks..].strip_prefix(form).is_some_and(|after| {
                if after.chars().next().is_some_and(word) {
                    return false;
                }
                let gap = after.chars().take_while(|&c| blank(c)).count();
                !(gap > 0 && after[gap..].chars().next().is_some_and(|c| chars.is(c, ALPHA) && chars.is(c, UPPER)))
            })
        })
    })
}

/// `engine._company_tail_ends` : la personne seule, puis jusqu'à trois mots de plus, capitalisés, « & » ou « et »,
/// après un ou deux blancs (« Dupont Frères SAS », 1.0.2, troisième tour). Possible ends of a company name.
fn company_tail_ends(chars: &Chars, text: &IndexedText, end: usize) -> Vec<usize> {
    let mut ends = vec![end];
    let mut i = end;
    for _ in 0..3 {
        let mut j = i;
        while j - i < 2 && matches!(text.char_at(j), Some(' ' | '\t')) {
            j += 1;
        }
        let Some(c) = text.char_at(j).filter(|_| j > i) else {
            break;
        };
        let k = if c == '&' {
            j + 1
        } else if c == 'e'
            && text.char_at(j + 1) == Some('t')
            && !text.char_at(j + 2).is_some_and(|d| chars.is(d, ALNUM))
        {
            j + 2
        } else if chars.is(c, ALPHA) && chars.is(c, UPPER) {
            let mut k = j + 1;
            while text.char_at(k).is_some_and(|d| chars.is(d, ALNUM) || d == '\'' || d == '’' || d == '-') {
                k += 1;
            }
            k
        } else {
            break;
        };
        ends.push(k);
        i = k;
    }
    ends
}

/// `engine._CIVILITY_BEFORE_RE` : civilités, même liste / civilities, same list.
const CIVILITIES: &[&str] = &["M.", "Mme", "Mlle", "Monsieur", "Madame", "Mademoiselle"];
/// `engine._TITLE_BEFORE_RE` : civilités et titres / civilities and titles.
const TITLES: &[&str] = &["M.", "Mme", "Mlle", "Monsieur", "Madame", "Mademoiselle", "Me", "Maître", "Dr"];

/// Une civilité et un seul blanc juste avant `start` / a civility and one blank right before `start`.
fn civility_before(chars: &Chars, text: &IndexedText, start: usize) -> bool {
    title_in(chars, text, start, CIVILITIES)
}

/// `engine._TITLE_BEFORE_RE` : une civilité ou un titre et un seul blanc juste avant `start`.
fn titled_before(chars: &Chars, text: &IndexedText, start: usize) -> bool {
    title_in(chars, text, start, TITLES)
}

fn title_in(chars: &Chars, text: &IndexedText, start: usize, forms: &[&str]) -> bool {
    let head = text.slice(0, start);
    let Some(rest) = head.strip_suffix(' ').or_else(|| head.strip_suffix('\t')) else {
        return false;
    };
    forms.iter().any(|form| {
        rest.strip_suffix(form).is_some_and(|before| {
            !before.chars().next_back().is_some_and(|c| chars.is(c, ALNUM) || c == '_' || c == '.')
        })
    })
}

/// `engine._surname_end` : fin du mot capitalisé qui commence en `pos` / end of the capitalised word at `pos`.
fn surname_end(chars: &Chars, text: &IndexedText, pos: usize) -> Option<usize> {
    let first = text.char_at(pos)?;
    if !(chars.is(first, ALPHA) && chars.is(first, UPPER)) {
        return None;
    }
    let (mut i, mut prev) = (pos + 1, first);
    while let Some(c) = text.char_at(i).filter(|&c| chars.is(c, ALPHA) || c == '\'' || c == '-') {
        if chars.is(c, ALPHA) && !chars.is(c, LOWER) && prev != '\'' && prev != '-' {
            return None;
        }
        prev = c;
        i += 1;
    }
    if prev == '\'' || prev == '-' || i - pos < 2 || text.char_at(i).is_some_and(|c| chars.is(c, ALNUM)) {
        return None;
    }
    Some(i)
}

/// `engine._extend_after_civility` : « M. [Matthieu] Orphelin » -> « M. [Matthieu Orphelin] » (`spans` triées,
/// disjointes / sorted, disjoint).
fn extend_after_civility(chars: &Chars, text: &IndexedText, spans: &mut [Span]) {
    for k in 0..spans.len() {
        let span = &spans[k];
        if &*span.entity != "PERSON" || !span.personal || text.char_at(span.end) != Some(' ') {
            continue;
        }
        if !civility_before(chars, text, span.start) {
            continue;
        }
        let Some(end) = surname_end(chars, text, span.end + 1) else {
            continue;
        };
        if spans.get(k + 1).is_some_and(|next| next.start < end) {
            continue;
        }
        spans[k].end = end;
    }
}

/// `engine.CIVILITY_WORDS`, `engine.NOT_SURNAMES` : mêmes listes / same lists.
const CIVILITY_WORDS: &[&str] =
    &["M.", "Mme", "Mlle", "Monsieur", "Madame", "Mademoiselle", "monsieur", "madame", "mademoiselle"];
/// `engine.MAIDEN_WORDS` : nom de naissance (« née Leclerc », 1.0.2, troisième tour) / maiden name.
const MAIDEN_WORDS: &[&str] = &["née", "Née"];
const NOT_SURNAMES: &[&str] = &[
    "Le",
    "La",
    "Les",
    "L",
    "De",
    "Du",
    "Des",
    "Président",
    "Présidente",
    "Ministre",
    "Député",
    "Députée",
    "Sénateur",
    "Sénatrice",
    "Maire",
    "Rapporteur",
    "Rapporteure",
    "Secrétaire",
    "Directeur",
    "Directrice",
    "Juge",
    "Procureur",
    "Préfet",
    "Préfète",
    "Commissaire",
    "Professeur",
    "Docteur",
    "Maître",
    "Monsieur",
    "Madame",
    "Mademoiselle",
    "Et",
    "Ou",
];
/// `types.PRIORITY_HEURISTIC`.
const PRIORITY_HEURISTIC: i64 = 60;

/// `engine._civility_surnames` : « M. Orphelin » -> « M. [Orphelin] », civilité, un blanc puis un seul mot
/// capitalisé qui ne touche aucune zone, seulement si le détecteur de noms français a trouvé une personne
/// (`spans` triées, disjointes). A civility, one blank, then one capitalised word touching no span.
fn civility_surnames(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    if !spans.iter().any(|s| &*s.source == "FR_NAMES" || &*s.source == "propagated:FR_NAMES") {
        return;
    }
    let starts: Vec<usize> = spans.iter().map(|s| s.start).collect();
    let all = text.as_str();
    let mut added = Vec::new();
    let mut next_free = 0;
    for (index, (byte, c)) in all.char_indices().enumerate() {
        if index < next_free || !matches!(c, 'M' | 'm' | 'n' | 'N') {
            continue;
        }
        if index > 0 && text.char_at(index - 1).is_some_and(|p| chars.is(p, ALNUM) || p == '_' || p == '.') {
            continue;
        }
        let rest = &all[byte..];
        let Some(word) = CIVILITY_WORDS
            .iter()
            .chain(MAIDEN_WORDS)
            .find(|w| rest.strip_prefix(**w).is_some_and(|after| after.starts_with([' ', '\t'])))
        else {
            continue;
        };
        let maiden = MAIDEN_WORDS.contains(word);
        let pos = index + word.chars().count() + 1;
        next_free = pos;
        let found = match surname_end(chars, text, pos) {
            None if maiden => caps_word_end(chars, text, pos).map(|end| {
                if NAME_PARTICLES_CAPS.contains(&text.slice(pos, end)) && text.char_at(end) == Some(' ') {
                    caps_word_end(chars, text, end + 1).unwrap_or(end) // « née LE GALL »
                } else {
                    end
                }
            }),
            other => other,
        };
        let Some(end) = found else {
            continue;
        };
        let value = text.slice(pos, end);
        if NOT_SURNAMES.contains(&value) {
            continue;
        }
        let k = starts.partition_point(|&start| start < end);
        if k > 0 && spans[k - 1].end > index {
            continue;
        }
        added.push(Span {
            start: pos,
            end,
            entity: "PERSON".into(),
            label: "PERSON".into(),
            source: "FR_NAMES".into(),
            score: 0.8,
            priority: PRIORITY_HEURISTIC,
            value: Some(value.to_owned()),
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: maiden.then(|| "maiden_name".into()),
            origin: None,
        });
    }
    if !added.is_empty() {
        spans.extend(added);
        spans.sort_by_key(|s| s.start);
    }
}

/// `engine.CLOSING_FORMULAS` : formules de clôture repliées, même liste / folded closing formulas, same list.
const CLOSING_FORMULAS: &[&str] = &[
    "cordialement",
    "bien cordialement",
    "tres cordialement",
    "bien a vous",
    "merci",
    "merci beaucoup",
    "merci d'avance",
    "bonne journee",
    "bonne soiree",
    "belle journee",
    "a bientot",
    "salutations",
    "sinceres salutations",
    "amities",
    "bises",
];

/// `engine._signature_names` : ligne de signature en minuscules (1.0.2), un ou deux mots égaux (repliés) au prénom,
/// au nom ou aux deux d'une seule personne déjà masquée, après une formule de clôture ou en dernière ligne non vide.
/// Lowercase signature line equal to exactly one masked person's given name, surname or both (`spans` sorted).
fn signature_names(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    let fold_words = |words: &[&str]| words.iter().map(|w| chars.fold(w)).collect::<Vec<_>>().join(" ");
    // (forme repliée -> personnes) ; valeur d'origine de chaque personne, la première vue / first-seen value.
    // (folded form -> persons); each person's original value.
    let mut people: HashMap<String, Vec<String>> = HashMap::new();
    let mut values: HashMap<String, String> = HashMap::new();
    for span in spans.iter() {
        if &*span.entity != "PERSON" || !span.personal {
            continue;
        }
        let value = span.value.clone().unwrap_or_else(|| text.slice(span.start, span.end).to_owned());
        let words: Vec<&str> = value.split(|c: char| chars.is(c, SPACE)).filter(|w| !w.is_empty()).collect();
        if words.len() < 2 {
            continue;
        }
        let key = fold_words(&words);
        let (given, surname) = (chars.fold(words[0]), chars.fold(words[words.len() - 1]));
        for part in [given.clone(), surname.clone(), format!("{given} {surname}")] {
            let owners = people.entry(part).or_default();
            if !owners.contains(&key) {
                owners.push(key.clone());
            }
        }
        values.entry(key).or_insert(value);
    }
    if people.is_empty() {
        return;
    }
    let all = text.as_str();
    let mut lines: Vec<(usize, usize)> = Vec::new();
    let mut start = 0;
    for (index, c) in all.chars().enumerate() {
        if c == '\n' {
            lines.push((start, index));
            start = index + 1;
        }
    }
    lines.push((start, text.len()));
    let blank = |&(s, e): &(usize, usize)| chars.strip(text.slice(s, e)).is_empty();
    let mut candidates: Vec<usize> = Vec::new();
    for (k, &(s, e)) in lines.iter().enumerate() {
        let folded = chars.fold(text.slice(s, e));
        let formula = chars.strip(chars.strip(&folded).trim_end_matches([',', '.', '!', ':', ';']));
        if CLOSING_FORMULAS.contains(&formula) {
            if let Some(next) = (k + 1..lines.len()).find(|&j| !blank(&lines[j])) {
                candidates.push(next);
            }
        }
    }
    if let Some(last) = (0..lines.len()).rev().find(|&j| !blank(&lines[j])) {
        candidates.push(last);
    }
    let mut seen: HashSet<usize> = HashSet::new();
    let mut added = Vec::new();
    for k in candidates {
        if !seen.insert(k) {
            continue;
        }
        let (s, e) = lines[k];
        let raw = text.slice(s, e);
        let content = chars.strip(raw);
        let words: Vec<&str> = content.split(' ').collect();
        let lower_word =
            |w: &&str| w.chars().count() >= 2 && w.chars().all(|c| chars.is(c, ALPHA) && chars.is(c, LOWER));
        if !(1..=2).contains(&words.len()) || !words.iter().all(lower_word) {
            continue;
        }
        let Some(owners) = people.get(&fold_words(&words)) else {
            continue;
        };
        let [owner] = owners.as_slice() else {
            continue;
        };
        let leading = raw.chars().count() - raw.trim_start_matches(|c| chars.is(c, SPACE)).chars().count();
        let lo = s + leading;
        let hi = lo + content.chars().count();
        let k = spans.partition_point(|span| span.start < hi);
        if k > 0 && spans[k - 1].end > lo {
            continue;
        }
        let Some(value) = values.get(owner) else {
            continue;
        };
        added.push(Span {
            start: lo,
            end: hi,
            entity: "PERSON".into(),
            label: "PERSON".into(),
            source: "FR_SIGNATURE".into(),
            score: 0.8,
            priority: PRIORITY_HEURISTIC,
            value: Some(value.clone()),
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: Some("signature".into()),
            origin: None,
        });
    }
    if !added.is_empty() {
        spans.extend(added);
        spans.sort_by_key(|s| s.start);
    }
}

/// `engine.INITIALS_CUES`, `engine.NOT_INITIALS` : mêmes listes, même ordre / same lists, same order.
const INITIALS_CUES: &[&str] = &[
    "redige par",
    "redigee par",
    "etabli par",
    "etablie par",
    "valide par",
    "validee par",
    "vise par",
    "visee par",
    "signe par",
    "signee par",
    "saisi par",
    "saisie par",
    "relu par",
    "relue par",
    "de la part de",
    "initiales",
    "paraphe",
    "auteur",
    "visa",
    "trigramme",
    "paraphes",
];
const NOT_INITIALS: &[&str] = &[
    "RH", "DG", "DRH", "DSI", "CA", "CE", "CSE", "SA", "TVA", "UE", "IT", "PDG", "DAF", "QA", "IA", "DGS", "DGA",
    "DPO", "CNIL", "SAS", "EI", "PME", "TPE", "CEO", "CTO", "CFO", "COO", "AI", "OK", "PS", "MOA", "MOE", "DSN", "CB",
    "SNCF", "RATP", "CPAM", "CNAM", "MDPH", "DDTM", "DDPP", "GRDF", "UGAP", "SASU", "SARL", "EURL",
];

fn upper_at(text: &IndexedText, i: usize) -> bool {
    text.char_at(i).is_some_and(|c| c.is_ascii_uppercase())
}

/// `engine._initials_at` : fin des initiales qui commencent en `p` / end of the initials at `p`.
fn initials_at(chars: &Chars, text: &IndexedText, p: usize) -> Option<usize> {
    let alnum = |i: usize| text.char_at(i).is_some_and(|c| chars.is(c, ALNUM));
    let mut i = p;
    while i - p < 4 && upper_at(text, i) {
        i += 1;
    }
    // Quatre lettres admises depuis le troisième tour (« Visa : FXLD ») / four letters since the third round.
    if (2..=4).contains(&(i - p)) && !alnum(i) && !(text.char_at(i) == Some('.') && alnum(i + 1)) {
        return (!NOT_INITIALS.contains(&text.slice(p, i))).then_some(i);
    }
    if !(upper_at(text, p) && text.char_at(p + 1) == Some('.')) {
        return None;
    }
    let mut i = p + 2;
    if text.char_at(i) == Some(' ') && upper_at(text, i + 1) {
        i += 1;
    }
    if !upper_at(text, i) {
        return None;
    }
    i += 1;
    if text.char_at(i) == Some('.') {
        i += 1;
    }
    let mut j = if text.char_at(i) == Some(' ') { i + 1 } else { i };
    if upper_at(text, j) {
        j += 1;
        if text.char_at(j) == Some('.') {
            j += 1;
        }
        if !alnum(j) {
            return Some(j);
        }
    }
    (!alnum(i)).then_some(i)
}

/// `engine._initials` : « Rédigée par NB », « visa : F.L. » ; raison `initials_after_cue` (`spans` triées).
/// Initials of a person after a cue (`spans` sorted, disjoint).
fn initials(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    let folded = chars.fold(text.as_str());
    let Some(index) = IndexedText::new(&folded) else {
        return;
    };
    let alnum = |i: usize| text.char_at(i).is_some_and(|c| chars.is(c, ALNUM));
    let mut added: Vec<Span> = Vec::new();
    for cue in INITIALS_CUES {
        let finder = Finder::new(cue.as_bytes());
        let mut from = 0;
        while let Some(at) = folded.as_bytes().get(from..).and_then(|rest| finder.find(rest)) {
            let byte = from + at;
            from = byte + 1;
            let pos = index.char_index(byte);
            let after = pos + cue.len();
            if (pos > 0 && alnum(pos - 1)) || alnum(after) {
                continue;
            }
            let mut p = after;
            while p - after < 3 && matches!(text.char_at(p), Some(' ' | ':')) {
                p += 1;
            }
            if p == after {
                continue;
            }
            let Some(end) = initials_at(chars, text, p) else {
                continue;
            };
            let k = spans.partition_point(|s| s.start < end);
            if (k > 0 && spans[k - 1].end > p) || added.iter().any(|a| a.start < end && p < a.end) {
                continue;
            }
            added.push(Span {
                start: p,
                end,
                entity: "PERSON".into(),
                label: "PERSON".into(),
                source: "FR_INITIALS".into(),
                score: 0.8,
                priority: PRIORITY_HEURISTIC,
                value: Some(text.slice(p, end).to_owned()),
                personal: true,
                forms: Vec::new(),
                propagate: false,
                reason: Some("initials_after_cue".into()),
                origin: None,
            });
            more_initials(chars, text, end, spans, &mut added);
        }
    }
    // « Jean-Marc Delaunay (JMD) » : initiales entre parenthèses juste après une personne masquée, égales aux
    // initiales de son nom (1.0.2, fort et essentiel). Bracketed initials right after a masked person.
    for s in spans.iter().filter(|s| &*s.entity == "PERSON") {
        let p = if text.char_at(s.end) == Some(' ') { s.end + 1 } else { s.end };
        if text.char_at(p) != Some('(') {
            continue;
        }
        let mut q = p + 1;
        while q - p <= 5 && upper_at(text, q) {
            q += 1;
        }
        let shaped = (2..=4).contains(&(q - p - 1)) && text.char_at(q) == Some(')');
        if !shaped || text.slice(p + 1, q) != name_initials(chars, text.slice(s.start, s.end)) {
            continue;
        }
        let k = spans.partition_point(|o| o.start < q);
        if (k > 0 && spans[k - 1].end > p + 1) || added.iter().any(|a| a.start < q && p + 1 < a.end) {
            continue;
        }
        added.push(Span {
            start: p + 1,
            end: q,
            entity: "PERSON".into(),
            label: "PERSON".into(),
            source: "FR_INITIALS".into(),
            score: 0.8,
            priority: PRIORITY_HEURISTIC,
            value: Some(text.slice(p + 1, q).to_owned()),
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: Some("initials_of_person".into()),
            origin: None,
        });
    }
    if !added.is_empty() {
        spans.extend(added);
        spans.sort_by_key(|s| s.start);
    }
    names_r3(chars, text, spans);
}

/// `engine.DOTTED_NOT_INITIALS`, `_INITIAL_PREPOSITIONS`, `_INITIAL_PARTICLES`, `_NAME_PARTICLES_CAPS` : mêmes
/// listes, même ordre (noms, troisième tour) / same lists, same order (names, third round).
const DOTTED_NOT_INITIALS: &[&str] = &[
    "NB", "PJ", "HT", "TTC", "JO", "RCS", "TGI", "PV", "AR", "RN", "RD", "ZI", "ZA", "ZAC", "BP", "CS", "CV", "ID",
    "US", "UK", "ND", "VO", "SNC", "SCI", "MM", "CGI", "CP", "CC", "CT", "TA", "RIB", "AE", "RC", "DCE", "BPU", "DQE",
    "SPS", "OPC", "VRD", "TCE", "PLU", "ERP", "BTP", "CAA", "TI", "TC", "JAF", "CPH", "QPC", "AM", "PM", "SVP", "STP",
    "ONU", "USA", "TV", "PC", "CD", "DVD", "GPS", "SMS", "NC", "SO", "NO", "NE", "SE", "QC", "OPJ", "APJ", "CAF",
    "CGV", "CGU", "FAQ", "HLM", "BO", "PO", "EDF", "SDF", "RER", "TGV", "VTC", "PMR", "RSA", "APL", "CMU", "AME",
    "IRM", "ASE", "PMA",
];
const INITIAL_PREPOSITIONS: &[&str] = &["de", "par", "pour", "avec", "chez", "à"];
const INITIAL_PARTICLES: &[&str] =
    &["de", "du", "des", "van", "von", "der", "di", "da", "del", "le", "la", "Le", "La", "De", "Du"];
const NAME_PARTICLES_CAPS: &[&str] = &["LE", "LA", "DE", "DU", "DA", "DI", "VAN", "VON", "DEL", "DES"];

/// `text.startswith(word, pos)` en positions de caractères / in character positions.
fn starts_at(text: &IndexedText, pos: usize, word: &str) -> bool {
    word.chars().enumerate().all(|(o, c)| text.char_at(pos + o) == Some(c))
}

/// `engine._caps_word_end` : fin du mot en capitales qui commence en `pos` / end of the all-capitals word at `pos`.
fn caps_word_end(chars: &Chars, text: &IndexedText, pos: usize) -> Option<usize> {
    let mut i = pos;
    while let Some(c) = text.char_at(i) {
        if (chars.is(c, ALPHA) && chars.is(c, UPPER)) || ((c == '\'' || c == '-') && i > pos) {
            i += 1;
        } else {
            break;
        }
    }
    if i - pos < 2
        || matches!(text.char_at(i - 1), Some('\'' | '-'))
        || text.char_at(i).is_some_and(|c| chars.is(c, ALNUM))
    {
        return None;
    }
    Some(i)
}

/// `engine._dotted_initials_at` : `[A-Z]\.` puis jusqu'à deux fois `[ -]?[A-Z]\.` ; (fin, lettres).
fn dotted_initials_at(chars: &Chars, text: &IndexedText, p: usize) -> Option<(usize, String)> {
    if !(upper_at(text, p) && text.char_at(p + 1) == Some('.')) {
        return None;
    }
    let mut letters = String::new();
    letters.push(text.char_at(p)?);
    let mut i = p + 2;
    while letters.len() < 3 {
        let j = if matches!(text.char_at(i), Some(' ' | '-')) { i + 1 } else { i };
        if !(upper_at(text, j) && text.char_at(j + 1) == Some('.')) {
            break;
        }
        letters.push(text.char_at(j)?);
        i = j + 2;
    }
    if text.char_at(i).is_some_and(|c| chars.is(c, ALNUM)) {
        return None;
    }
    Some((i, letters))
}

fn initials_ok(letters: &str) -> bool {
    !NOT_INITIALS.contains(&letters) && !DOTTED_NOT_INITIALS.contains(&letters)
}

/// `engine._capital_word_follows` : un blanc puis une lettre capitale en `end` / a blank then a capital letter.
fn capital_word_follows(chars: &Chars, text: &IndexedText, end: usize) -> bool {
    text.char_at(end) == Some(' ') && text.char_at(end + 1).is_some_and(|c| chars.is(c, ALPHA) && chars.is(c, UPPER))
}

/// `engine._particle_surname_end` : jusqu'à deux particules puis un nom capitalisé / particles then a surname.
fn particle_surname_end(chars: &Chars, text: &IndexedText, pos: usize) -> Option<usize> {
    let mut q = pos;
    for _ in 0..2 {
        let particle = INITIAL_PARTICLES.iter().find(|particle| {
            let k = q + particle.chars().count();
            starts_at(text, q, particle)
                && text.char_at(k) == Some(' ')
                && text.char_at(k + 1).is_some_and(|c| chars.is(c, ALPHA))
        });
        match particle {
            Some(particle) => q += particle.chars().count() + 1,
            None => {
                if matches!(text.char_at(q), Some('d' | 'D'))
                    && text.char_at(q + 1) == Some('\'')
                    && text.char_at(q + 2).is_some_and(|c| chars.is(c, ALPHA))
                {
                    q += 2;
                }
                break;
            }
        }
    }
    let end = surname_end(chars, text, q)?;
    (!NOT_SURNAMES.contains(&text.slice(q, end))).then_some(end)
}

/// `engine._preposition_before` : « de », « par », « pour », « avec », « chez » ou « à », puis un blanc, avant `p`.
fn preposition_before(chars: &Chars, text: &IndexedText, p: usize) -> bool {
    if p < 2 || text.char_at(p - 1) != Some(' ') {
        return false;
    }
    INITIAL_PREPOSITIONS.iter().any(|word| {
        let n = word.chars().count();
        p > n && {
            let start = p - 1 - n;
            text.slice(start, p - 1) == *word
                && !(start > 0 && text.char_at(start - 1).is_some_and(|c| chars.is(c, ALNUM)))
        }
    })
}

/// `engine._LIST_LINK_RE.fullmatch` : `[ \t]?(?:,|et|&)[ \t]{1,2}`.
fn list_link(gap: &str) -> bool {
    let body = gap.strip_prefix([' ', '\t']).unwrap_or(gap);
    [",", "et", "&"]
        .iter()
        .filter_map(|sep| body.strip_prefix(sep))
        .any(|tail| (1..=2).contains(&tail.len()) && tail.chars().all(|c| c == ' ' || c == '\t'))
}

/// `engine._LINE_BREAK_GAP_RE.fullmatch` : `[ \t]{0,2}\r?\n[ \t]{0,2}`.
fn line_break_gap(gap: &str) -> bool {
    let rest = gap.trim_start_matches([' ', '\t']);
    if gap.len() - rest.len() > 2 {
        return false;
    }
    rest.strip_prefix("\r\n")
        .or_else(|| rest.strip_prefix('\n'))
        .is_some_and(|tail| tail.len() <= 2 && tail.chars().all(|c| c == ' ' || c == '\t'))
}

/// `engine._LINE_BREAK_GAP_RE.match(text, k)` : fin de la correspondance, sinon None / end of the match.
fn line_break_at(text: &IndexedText, k: usize) -> Option<usize> {
    let mut i = k;
    while i - k < 2 && matches!(text.char_at(i), Some(' ' | '\t')) {
        i += 1;
    }
    if text.char_at(i) == Some('\r') && text.char_at(i + 1) == Some('\n') {
        i += 2;
    } else if text.char_at(i) == Some('\n') {
        i += 1;
    } else {
        return None;
    }
    let j = i;
    while i - j < 2 && matches!(text.char_at(i), Some(' ' | '\t')) {
        i += 1;
    }
    Some(i)
}

/// `text.rfind("\n", 0, pos) + 1` : début de la ligne de `pos` / start of the line holding `pos`.
fn line_start_before(text: &IndexedText, pos: usize) -> usize {
    (0..pos).rev().find(|&i| text.char_at(i) == Some('\n')).map_or(0, |i| i + 1)
}

/// `engine._after_closing` : la ligne d'avant finit par « , » ou est une formule de clôture, ou le texte commence.
fn after_closing(chars: &Chars, text: &IndexedText, line_start: usize) -> bool {
    if line_start == 0 {
        return true;
    }
    let begin = line_start_before(text, line_start - 1);
    let before = chars.strip(text.slice(begin, line_start - 1));
    if before.ends_with(',') {
        return true;
    }
    let folded = chars.fold(before);
    CLOSING_FORMULAS.contains(&chars.strip(chars.strip(&folded).trim_end_matches([',', '.', '!', ':', ';'])))
}

/// `engine._names_r3` : initiales pointées après ou avant une personne, entre parenthèses, dans une liste, à trait
/// d'union avec un nom, en début de ligne ou après une préposition (1.0.2, troisième tour ; `spans` triées).
/// Third round of initials (`spans` sorted, disjoint).
fn names_r3(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    let n = text.len();
    let person = |s: &Span| &*s.entity == "PERSON" && s.personal;
    let free = |spans: &[Span], added: &[Span], a: usize, b: usize| {
        let k = spans.partition_point(|s| s.start < b);
        !(k > 0 && spans[k - 1].end > a) && !added.iter().any(|x| x.start < b && a < x.end)
    };
    // Initiales juste après une personne / initials right after a person.
    for k in 0..spans.len() {
        let end = spans[k].end;
        if !person(&spans[k]) || text.char_at(end) != Some(' ') {
            continue;
        }
        let Some((stop, letters)) = dotted_initials_at(chars, text, end + 1) else {
            continue;
        };
        if !initials_ok(&letters) || capital_word_follows(chars, text, stop) {
            continue;
        }
        if free(&spans[..], &[], end + 1, stop) {
            spans[k].end = stop;
        }
    }
    let index: HashMap<usize, usize> = spans.iter().enumerate().map(|(k, s)| (s.start, k)).collect();
    let mut added: Vec<Span> = Vec::new();
    let mut p = 0;
    while p < n {
        let boundary = p > 0 && text.char_at(p - 1).is_some_and(|c| chars.is(c, ALNUM) || ".-'’_@/".contains(c));
        if !(upper_at(text, p) && text.char_at(p + 1) == Some('.')) || boundary {
            p += 1;
            continue;
        }
        if text.char_at(p) == Some('M')
            && text.char_at(p + 2) == Some(' ')
            && !(p > 0 && text.char_at(p - 1) == Some('('))
            && !listed(text, &spans[..], &added, p)
        {
            p += 2; // civilité « M. » (« M. J.-B. de La Fontaine ») / a civility
            continue;
        }
        let Some((mut end, letters)) = dotted_initials_at(chars, text, p) else {
            p += 1;
            continue;
        };
        if letters.len() >= 2 && initials_ok(&letters) && free(&spans[..], &added, p, end) {
            let k = if text.char_at(end) == Some(' ') { index.get(&(end + 1)).copied() } else { None };
            let mut reason: Option<&str> = None;
            let mut stop = end;
            if let Some(k) = k.filter(|&k| person(&spans[k])) {
                spans[k].start = p; // « J.-B. Lemoine »
            } else if p > 0 && text.char_at(p - 1) == Some('(') && text.char_at(end) == Some(')') {
                // Trois lettres collées entre parenthèses : un sigle (« (C.C.P.) ») / three glued letters: an acronym.
                if letters.len() == 2 || text.slice(p, end).contains([' ', '-']) {
                    reason = Some("initials_in_brackets");
                }
            } else {
                if listed(text, &spans[..], &added, p) {
                    reason = Some("initials_in_list");
                } else if text.slice(p, end).contains('-') && text.char_at(end) == Some(' ') {
                    if let Some(surname) = particle_surname_end(chars, text, end + 1) {
                        if free(&spans[..], &added, p, surname) {
                            reason = Some("initials_with_surname");
                            stop = surname;
                        }
                    }
                }
                if reason.is_none()
                    && (letters.len() == 2 || text.slice(p, end).contains('-'))
                    && !text.slice(p, end).contains(' ')
                {
                    let line_start = p == 0 || text.char_at(p - 1) == Some('\n');
                    let line_end = end >= n
                        || matches!(text.char_at(end), Some('\r' | '\n'))
                        || capital_word_follows(chars, text, end);
                    if (line_start && line_end) || preposition_before(chars, text, p) {
                        reason = Some("initials_dotted");
                    }
                }
            }
            if let Some(reason) = reason {
                added.push(Span {
                    start: p,
                    end: stop,
                    entity: "PERSON".into(),
                    label: "PERSON".into(),
                    source: "FR_INITIALS".into(),
                    score: 0.8,
                    priority: PRIORITY_HEURISTIC,
                    value: Some(text.slice(p, stop).to_owned()),
                    personal: true,
                    forms: Vec::new(),
                    propagate: false,
                    reason: Some(reason.into()),
                    origin: None,
                });
                end = stop;
            }
        }
        p = end;
    }
    if !added.is_empty() {
        spans.extend(added);
        spans.sort_by_key(|s| s.start);
    }
    bare_initials_in_list(chars, text, spans);
    join_split_names(chars, text, spans);
}

/// `listed` de `engine._names_r3` : une personne (ou des initiales déjà prises), puis « , », « et » ou « & » juste
/// avant `p`. A person (or initials already taken), then a list link, right before `p`.
fn listed(text: &IndexedText, spans: &[Span], added: &[Span], p: usize) -> bool {
    let i = spans.partition_point(|s| s.start < p);
    let mut prev: Option<&Span> = (i > 0 && spans[i - 1].end <= p).then(|| &spans[i - 1]);
    if let Some(last) = added.last() {
        if last.end <= p && prev.is_none_or(|pv| last.end > pv.end) {
            prev = Some(last);
        }
    }
    prev.is_some_and(|pv| &*pv.entity == "PERSON" && list_link(text.slice(pv.end, p)))
}

/// `engine._list_link_end` : `_LIST_LINK_RE.match(text, pos)`, fin du lien / end of the list link.
fn list_link_end(text: &IndexedText, pos: usize) -> Option<usize> {
    let mut i = pos;
    if matches!(text.char_at(i), Some(' ' | '\t')) {
        i += 1;
    }
    let sep = [",", "et", "&"].into_iter().find(|sep| starts_at(text, i, sep))?;
    let start = i + sep.chars().count();
    let mut j = start;
    while j - start < 2 && matches!(text.char_at(j), Some(' ' | '\t')) {
        j += 1;
    }
    (j > start).then_some(j)
}

/// `engine._bare_initials_in_list` : « Présents : Quentin Moreau, Mathéo Moreau, AC » : initiales en capitales
/// après deux personnes d'une même liste, raison `initials_in_list` (`spans` triées, disjointes).
fn bare_initials_in_list(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    let mut added = Vec::new();
    for k in 1..spans.len() {
        let (a, b) = (&spans[k - 1], &spans[k]);
        if &*a.entity != "PERSON" || &*b.entity != "PERSON" || a.end > b.start || !list_link(text.slice(a.end, b.start))
        {
            continue;
        }
        if !text.slice(a.start, a.end).contains(' ') || !text.slice(b.start, b.end).contains(' ') {
            continue; // deux personnes en prénom et nom (« Fonte, Grès, PRV » : non) / two full names
        }
        let Some(q) = list_link_end(text, b.end) else {
            continue;
        };
        if !upper_at(text, q) || text.char_at(q + 1) == Some('.') {
            continue;
        }
        let Some(end) = initials_at(chars, text, q) else {
            continue;
        };
        if !initials_ok(text.slice(q, end)) || spans.get(k + 1).is_some_and(|c| c.start < end) {
            continue;
        }
        added.push(Span {
            start: q,
            end,
            entity: "PERSON".into(),
            label: "PERSON".into(),
            source: "FR_INITIALS".into(),
            score: 0.8,
            priority: PRIORITY_HEURISTIC,
            value: Some(text.slice(q, end).to_owned()),
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: Some("initials_in_list".into()),
            origin: None,
        });
    }
    if !added.is_empty() {
        spans.extend(added);
        spans.sort_by_key(|s| s.start);
    }
}

/// `engine._join_split_names` : « "DUPONT, Jean" », « Jean⏎Dupont », « Yann LE⏎GALL » : une seule personne.
/// One person for a capitals surname, a comma and a given name, and for a name cut by a line break.
fn join_split_names(chars: &Chars, text: &IndexedText, spans: &mut Vec<Span>) {
    let n = text.len();
    let mut out: Vec<Span> = Vec::with_capacity(spans.len());
    for s in spans.drain(..) {
        if let Some(prev) = out.last_mut() {
            if &*prev.entity == "PERSON" && prev.personal && &*s.entity == "PERSON" && s.personal {
                let left = text.slice(prev.start, prev.end);
                let right = text.slice(s.start, s.end);
                let single = !left.contains([' ', '\n']) && !right.contains([' ', '\n']);
                let titled = right.chars().next().is_some_and(|c| chars.is(c, UPPER))
                    && right.chars().count() >= 2
                    && right.chars().skip(1).all(|c| chars.is(c, ALPHA) && chars.is(c, LOWER));
                if single
                    && text.slice(prev.end, s.start) == ", "
                    && left.chars().count() >= 2
                    && chars.is_upper(left)
                    && titled
                    && !text.char_at(s.end).is_some_and(|c| chars.is(c, ALNUM))
                {
                    prev.end = s.end; // « DUPONT, Jean »
                    continue;
                }
                if single && line_break_gap(text.slice(prev.end, s.start)) {
                    let line_start = line_start_before(text, prev.start);
                    if chars.strip(text.slice(line_start, prev.start)).is_empty()
                        && (s.end >= n || matches!(text.char_at(s.end), Some('\r' | '\n')))
                        && after_closing(chars, text, line_start)
                    {
                        let first = prev.value.clone().filter(|v| !v.is_empty()).unwrap_or_else(|| left.to_owned());
                        let second = s.value.clone().filter(|v| !v.is_empty()).unwrap_or_else(|| right.to_owned());
                        prev.value = Some(format!("{first} {second}")); // « Jean⏎Dupont »
                        prev.end = s.end;
                        continue;
                    }
                }
            }
        }
        out.push(s);
    }
    // Fix 1.0.2 (temps quadratique) : `out` est triée par début ; `reach` est la plus grande fin d'avant, et seules
    // les zones d'après qui commencent avant `stop` sont lues. Même résultat, temps linéaire. `out` is sorted by
    // start: `reach` is the furthest earlier end, and only later spans starting before `stop` are read; linear time.
    let mut reach = 0;
    for idx in 0..out.len() {
        let end = out[idx].end;
        if &*out[idx].entity == "PERSON" && out[idx].personal && text.char_at(end) == Some(' ') {
            for particle in NAME_PARTICLES_CAPS {
                if !starts_at(text, end + 1, particle) {
                    continue;
                }
                let Some(gap) = line_break_at(text, end + 1 + particle.chars().count()) else {
                    continue;
                };
                if let Some(stop) = caps_word_end(chars, text, gap) {
                    let line_end = stop >= n || matches!(text.char_at(stop), Some('\r' | '\n'));
                    let clear =
                        reach <= end && out[idx + 1..].iter().take_while(|o| o.start < stop).all(|o| o.end <= end);
                    if line_end && clear {
                        out[idx].end = stop; // « Yann LE⏎GALL »
                    }
                }
                break;
            }
        }
        reach = reach.max(out[idx].end);
    }
    *spans = out;
}

/// `engine._more_initials` : « Paraphes : JBR / MEA » : jusqu'à trois autres initiales après « / » ou « , ».
/// Up to three more initials separated by "/" or ",".
fn more_initials(chars: &Chars, text: &IndexedText, mut end: usize, spans: &[Span], added: &mut Vec<Span>) {
    for _ in 0..3 {
        let mut k = end;
        while k - end < 2 && text.char_at(k) == Some(' ') {
            k += 1;
        }
        if !matches!(text.char_at(k), Some('/' | ',')) {
            return;
        }
        k += 1;
        let mut m = k;
        while m - k < 2 && text.char_at(m) == Some(' ') {
            m += 1;
        }
        let Some(next) = initials_at(chars, text, m) else {
            return;
        };
        let i = spans.partition_point(|s| s.start < next);
        if (i > 0 && spans[i - 1].end > m) || added.iter().any(|a| a.start < next && m < a.end) {
            return;
        }
        added.push(Span {
            start: m,
            end: next,
            entity: "PERSON".into(),
            label: "PERSON".into(),
            source: "FR_INITIALS".into(),
            score: 0.8,
            priority: PRIORITY_HEURISTIC,
            value: Some(text.slice(m, next).to_owned()),
            personal: true,
            forms: Vec::new(),
            propagate: false,
            reason: Some("initials_after_cue".into()),
            origin: None,
        });
        end = next;
    }
}

/// `engine._name_initials` : première lettre A-Z de chaque partie (blancs, « - », apostrophes) / A-Z initials.
fn name_initials(chars: &Chars, name: &str) -> String {
    let mut out = String::new();
    let mut part_start = true;
    for c in name.chars() {
        if chars.is(c, SPACE) || matches!(c, '-' | '\'' | '’') {
            part_start = true;
            continue;
        }
        if part_start && c.is_ascii_uppercase() {
            out.push(c);
        }
        part_start = false;
    }
    out
}

/// Positions d'origine d'avant normalisation (`array('q')` de `_text.normalize`) / pre-normalisation offsets.
pub fn map_offsets(spans: &mut [Span], offsets: &[i64]) -> Result<(), Unsupported> {
    let at = |index: usize| offsets.get(index).and_then(|&o| usize::try_from(o).ok()).ok_or(Unsupported);
    for span in spans {
        let start = at(span.start)?;
        let end = at(span.end.checked_sub(1).ok_or(Unsupported)?)?.checked_add(1).ok_or(Unsupported)?;
        span.start = start;
        span.end = end;
    }
    Ok(())
}

/// `analyze_segments` : zones de chaque segment, en positions locales d'origine ; une zone à cheval sur deux
/// segments n'appartient à aucun et garde ses positions jointes. Per-segment spans in local original offsets;
/// a span straddling two segments belongs to none and keeps its joined offsets.
pub fn split_segments(
    spans: &mut [Span],
    segments: &Segments,
    offsets: &[Option<Vec<i64>>],
) -> Result<Vec<Vec<usize>>, Unsupported> {
    let mut members: Vec<Vec<usize>> = vec![Vec::new(); segments.len()];
    for (position, span) in spans.iter_mut().enumerate() {
        let (index, lo, hi) = segments.locate(span.start).ok_or(Unsupported)?;
        if span.end > hi {
            continue;
        }
        span.start -= lo;
        span.end -= lo;
        if let Some(offsets) = offsets.get(index).ok_or(Unsupported)? {
            map_offsets(std::slice::from_mut(span), offsets)?;
        }
        members.get_mut(index).ok_or(Unsupported)?.push(position);
    }
    Ok(members)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::finalize::chars::test_rules;

    #[test]
    fn initials_follow_the_python_shapes() {
        let rules = test_rules();
        let chars = Chars::new(&rules);
        let end = |s: &str| {
            let text = IndexedText::new(s).expect("small");
            initials_at(&chars, &text, 0).map(|e| text.slice(0, e).to_owned())
        };
        assert_eq!(end("NB le").as_deref(), Some("NB"));
        assert_eq!(end("NB.").as_deref(), Some("NB"));
        assert_eq!(end("F.L.").as_deref(), Some("F.L."));
        assert_eq!(end("R. G. x").as_deref(), Some("R. G."));
        assert_eq!(end("A.B.C.").as_deref(), Some("A.B.C."));
        assert_eq!(end("DRH"), None);
        assert_eq!(end("ABCD"), None);
        assert_eq!(end("Jean"), None);
    }

    #[test]
    fn initials_after_a_cue_only() {
        let rules = test_rules();
        let chars = Chars::new(&rules);
        let text = IndexedText::new("redige par NB, relu par la DRH, visa : F.L.").expect("small");
        let mut spans = Vec::new();
        initials(&chars, &text, &mut spans);
        let found: Vec<&str> = spans.iter().map(|s| text.slice(s.start, s.end)).collect();
        assert_eq!(found, ["NB", "F.L."]);
    }
}
