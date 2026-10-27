//! Décision et scores : `_decide`, `_evidence`, `_score*`, et le contexte local (phrase, ligne, mot précédent).
//!
//! Decision and scoring, plus the local context helpers (sentence start, line style, previous word).

use std::collections::HashSet;

use super::chars::{rfind, strip_chars, sub, ALPHA, LETTER};
use super::cues::Cues;
use super::lexicon::{Kind, AMB_ENTITY, AMB_NONE, AMB_STRONG, AMB_WORD};
use super::patterns;
use super::tokens::Run;
use super::vocab::flag;
use super::{
    inside, Confirmed, Doc, Element, Keys, PositionMap, CAPS_ALONE_MIN, COMMUNE_SURNAME_MIN, ENTITY_GIVEN_MIN,
    GIVEN_ALONE_MIN, GIVEN_START_MIN, MEDIUM, NEG, NONE, STRONG, SURNAME_ALONE_MIN, WEAK,
};

/// Recherche de fin de ligne bornée (`LINE_WINDOW`) / bounded line lookup.
const LINE_WINDOW: usize = 512;

/// `_vocab.PLACE_VERBS` : verbes de lieu, seulement pour un nom de lieu repris d'une personne trouvée ailleurs.
/// Place verbs, only for a place name repeated from a person found elsewhere.
const PLACE_VERBS: &[&str] = &[
    "quitter",
    "quitte",
    "quittent",
    "quitté",
    "quittée",
    "quittera",
    "rejoindre",
    "rejoint",
    "rejoindra",
    "regagner",
    "regagne",
];

/// Style d'une ligne : (Casse De Titre, capitales), mis en cache par début de ligne / per line start.
type StyleCache = PositionMap<(bool, bool)>;

/// Éléments d'une suite qui sont des noms (`_Run.names`) / the run's name elements.
fn names<'e>(run: &Run, elements: &'e [Element]) -> impl Iterator<Item = &'e Element> + Clone {
    elements[run.from..run.to].iter().filter(|e| e.kind.is_name())
}

impl Doc<'_> {
    /// `_decide` : suites retenues (triées) et formes vues comme éponymes (jamais propagées).
    /// Accepted runs (sorted indexes) and eponym forms (never propagated).
    pub(super) fn decide(
        &self,
        elements: &[Element],
        runs: &mut [Run],
        cues: &Cues,
        confirmed: &mut Confirmed,
        keys: &Keys,
    ) -> (Vec<usize>, HashSet<Vec<char>>) {
        let text = &self.text;
        let (mut accepted, mut rejected, mut deferred) = (Vec::new(), Vec::new(), Vec::new());
        let mut eponyms: HashSet<Vec<char>> = HashSet::new();
        let mut styles = StyleCache::default();
        let mut previous: Option<usize> = None;
        for r in 0..runs.len() {
            let (start, end) = (elements[runs[r].from].start, elements[runs[r].to - 1].end);
            let listed = previous.is_some_and(|p| {
                let gap = sub(text, elements[runs[p].to - 1].end, start);
                gap.len() <= 12 && patterns::list_gap(gap)
            });
            let previous_strong = previous.is_some_and(|p| runs[p].evidence == STRONG);
            runs[r].addressed =
                cues.roles.contains(&start) || (cues.greetings.contains(&start) && patterns::vocative(text, end));
            runs[r].labelled = cues.labels.contains(&start);
            let run = &runs[r];
            if let [only] = &elements[run.from..run.to] {
                // Mot inconnu seul (souvent un verbe) : un nom seulement après un indice fort, ou s'il est
                // confirmé ailleurs (second passage). A lone unknown word: a name only after a strong cue.
                if only.kind == Kind::Unknown
                    && cues.at.get(only.start) != Some(STRONG)
                    && !cues.display.contains(&only.end)
                    && cues.strong.is_empty()
                    && !run.addressed
                    && !(listed && previous_strong)
                {
                    deferred.push(r);
                    continue;
                }
            }
            let found: Vec<&Element> = names(run, elements).collect();
            let evidence = self.evidence(run, elements, &found, cues, confirmed, keys);
            runs[r].evidence = evidence;
            if evidence == NEG {
                // « tour Eiffel » : « Eiffel » ne sera pas propagé / will not be propagated.
                eponyms.extend(found.iter().map(|e| keys.get(e.key).to_vec()));
                continue;
            }
            if listed && matches!(evidence, NONE | WEAK) && !marker(&found) {
                // Suite d'une liste : « MM. Dupont et Petit », « Jean Dupont, Rose et Paul » / list continuation.
                runs[r].evidence = if previous_strong { STRONG } else { MEDIUM };
            }
            runs[r].score = self.score(&runs[r], elements, &found, &mut styles, false, keys);
            if runs[r].score <= 0.0 {
                rejected.push(r);
                continue;
            }
            accepted.push(r);
            previous = Some(r);
            let run = &runs[r];
            // Seule une mention sûre confirme ses formes : un mot ambigu seul n'en confirme aucune, et un lieu
            // n'est confirmé que seul après un indice fort (« M. Paris », pas « Anne de Bretagne »).
            // Only a reliable mention confirms its forms; a place only alone after a strong cue.
            if run.evidence >= MEDIUM || found.len() >= 2 || found[0].amb() == AMB_NONE {
                let entity_ok = found.len() == 1 && run.evidence == STRONG;
                let any_given = found.iter().any(|e| e.given() > 0);
                // Un mot-nom d'une paire n'est confirmé qu'à côté d'un prénom (« Pierre Blanc »).
                // An ambiguous element of a pair is confirmed only next to a given name.
                let anchored = run.evidence >= MEDIUM || found.len() == 1 || any_given;
                // Un mot inconnu n'est confirmé que sous un indice ou à côté d'un prénom connu.
                // An unknown word needs a cue or a known given name.
                let unknown_ok = run.evidence >= MEDIUM || any_given;
                for e in found {
                    if e.key.len() >= 3
                        && (e.amb() != AMB_ENTITY || entity_ok)
                        && (e.amb() == AMB_NONE || anchored)
                        && (e.kind != Kind::Unknown || unknown_ok)
                    {
                        confirmed.insert(keys.get(e.key).to_vec());
                    }
                }
            }
        }
        // Propagation interne des formes confirmées / internal propagation of confirmed forms.
        for r in rejected.into_iter().chain(deferred) {
            let start = elements[runs[r].from].start;
            let found: Vec<&Element> = names(&runs[r], elements).collect();
            if cues.at.get(start) == Some(NEG) || !found.iter().any(|e| confirmed.contains(keys.get(e.key))) {
                continue;
            }
            runs[r].evidence = MEDIUM;
            runs[r].score = if found.len() == 1
                && found[0].safe()
                && !eponyms.contains(keys.get(found[0].key))
                && !self.after_determiner(start)
            {
                // Forme sûre confirmée (« Mme Ferhati » … « Ferhati Solutions ») : masquée partout, comme le
                // moteur la propagerait. Safe confirmed form: masked everywhere, as the engine would.
                0.8
            } else {
                self.score(&runs[r], elements, &found, &mut styles, true, keys)
            };
            if runs[r].score > 0.0 {
                accepted.push(r);
            }
        }
        // Tri stable par début (débuts tous distincts) / stable sort by start (starts are distinct).
        accepted.sort_by_key(|&r| elements[runs[r].from].start);
        (accepted, eponyms)
    }

    /// `_evidence` : force de l'indice qui porte une suite / strength of the cue behind a run.
    fn evidence(
        &self,
        run: &Run,
        elements: &[Element],
        found: &[&Element],
        cues: &Cues,
        confirmed: &Confirmed,
        keys: &Keys,
    ) -> i8 {
        let (start, end) = (elements[run.from].start, elements[run.to - 1].end);
        let mut evidence = cues.at.get(start).unwrap_or(NONE);
        if evidence == NEG {
            // « Matricule 75012 Sophie Martin » : un prénom et un autre nom après un code postal qui n'annonce pas
            // sa commune. A given name and another name after a postcode not followed by its town.
            let person = found.len() >= 2 && found.iter().any(|e| e.kind == Kind::Name && e.given() >= GIVEN_ALONE_MIN);
            if !(cues.postcodes.contains(&start) && person) {
                return NEG;
            }
            evidence = NONE;
        }
        if !cues.strong.is_empty() && inside(&cues.strong, start, end) {
            return STRONG;
        }
        if cues.display.contains(&end) {
            return STRONG; // « Jean Dupont <jean.dupont@…> »
        }
        if evidence == NONE && inside(&cues.signature, start, end) && self.line_start(start) {
            evidence = WEAK;
        }
        if evidence < MEDIUM && !confirmed.is_empty() && found.iter().all(|e| confirmed.contains(keys.get(e.key))) {
            evidence = MEDIUM;
        }
        evidence
    }

    /// `_score` : 0 si la suite n'est pas retenue ; `found` : ses noms / 0 when not accepted; `found`: its names.
    fn score(
        &self,
        run: &Run,
        elements: &[Element],
        found: &[&Element],
        styles: &mut StyleCache,
        confirmed_only: bool,
        keys: &Keys,
    ) -> f64 {
        if found.is_empty() || run.evidence == NEG {
            return 0.0;
        }
        if run.evidence == STRONG {
            // « Nom : TESTIX INDUSTRIES » : un mot seul suivi de mots courants capitalisés est une raison sociale ;
            // mais pas s'ils commencent l'étiquette suivante (« Nom : Dupont Prénom : Jean »). A single word
            // followed by capitalised common words under a field label is a company name, unless they start the
            // next label.
            if run.labelled
                && run.cap_right
                && found.len() == 1
                && found[0].given() == 0
                && !patterns::label_ahead(&self.det.chars, &self.text, elements[run.to - 1].end)
            {
                return 0.0;
            }
            return 0.95;
        }
        let lead = &elements[run.from];
        if lead.kind == Kind::Particle && lead.entry.has(flag::DETERMINER) {
            return 0.0; // « La Rose », « Le Monde » : article capitalisé / capitalised article
        }
        if self.after_determiner(lead.start) {
            return 0.0;
        }
        let initials = elements[run.from..run.to].iter().filter(|e| e.kind == Kind::Initial).count();
        if run.evidence >= WEAK {
            let initial = elements[run.from..run.to].iter().any(|e| e.kind == Kind::Initial);
            return self.score_cued(run, lead.start, found, initial, confirmed_only);
        }
        let (title_line, caps_line) = self.line_style(lead.start, styles);
        if found.len() + initials >= 2 {
            return self.score_pair(run, elements, found, initials, title_line, caps_line);
        }
        self.score_single(run, found[0], title_line, caps_line, keys)
    }

    /// `_score_cued` : avec un indice moyen ou faible (salutation, rôle, signature) / with a medium or weak cue.
    /// `initial` : la suite porte une initiale / the run holds an initial.
    fn score_cued(&self, run: &Run, start: usize, found: &[&Element], initial: bool, confirmed_only: bool) -> f64 {
        let single = found.len() == 1;
        if confirmed_only && single && (run.cap_left || run.cap_right) {
            return 0.0;
        }
        // Premier nom connu (`known[0]`) / first known name.
        let known = found.iter().find(|e| e.kind == Kind::Name && (e.amb() != AMB_ENTITY || confirmed_only));
        let Some(&first) = known else {
            // Noms inconnus : « le patient Ansgar Davids », « Bonjour Nath, », « Présents : Testarossi P » / unknown
            // names under a cue, or one word and an initial.
            let plain = found.iter().all(|e| e.kind == Kind::Unknown && !e.caps && e.key.len() >= 3);
            let accepted = (2..=3).contains(&found.len()) || (single && initial) || run.addressed;
            return if plain && accepted { 0.75 } else { 0.0 };
        };
        if confirmed_only && single && first.amb() == AMB_ENTITY && self.after_locative(start, true) {
            return 0.0;
        }
        if run.evidence == WEAK && single && !((first.given() > 0 && first.amb() != AMB_ENTITY) || first.solid()) {
            return 0.0; // signature : un prénom ou un nom sûr, pas « Chargé d'affaires » / not a job title
        }
        if confirmed_only || run.evidence == WEAK {
            0.8
        } else {
            0.85
        }
    }

    /// `_score_single` : un seul nom, sans indice / a single name, no cue.
    fn score_single(&self, run: &Run, e: &Element, title_line: bool, caps_line: bool, keys: &Keys) -> f64 {
        let det = self.det;
        if e.kind != Kind::Name || e.amb() == AMB_ENTITY || e.key.len() < 3 {
            return 0.0;
        }
        if e.caps
            && (caps_line
                || title_line
                || e.amb() != AMB_NONE
                || e.key.len() < 4
                || e.given().max(e.surname()) < CAPS_ALONE_MIN)
        {
            return 0.0; // en capitales : sigle ou titre, sauf nom sûr et fréquent (« Selon DUPONT »)
        }
        if (run.cap_left || run.cap_right) && e.amb() != AMB_NONE {
            return 0.0; // « Mont Blanc », « Radio France » : mot ambigu / ambiguous word
        }
        if !(e.given() >= GIVEN_ALONE_MIN || e.surname() >= SURNAME_ALONE_MIN) {
            return 0.0;
        }
        if (title_line || caps_line) && e.amb() != AMB_NONE {
            return 0.0;
        }
        let text = &self.text;
        if patterns::number_after(&det.chars, text, e.end)
            && !(e.amb() == AMB_NONE && patterns::year_after(text, e.end))
        {
            return 0.0; // « Louis XIV », « Ariane 5 » ; mais « Rapport Lefèvre 2024 » reste un nom
        }
        // « Doignies », « Levallois-Perret » : clé de commune, traits d'union en espaces / hyphens as spaces.
        let key = keys.get(e.key);
        let commune = if key.contains(&'-') {
            let spaced: Vec<char> = key.iter().map(|&c| if c == '-' { ' ' } else { c }).collect();
            det.vocab.get(&spaced).has(flag::COMMUNE)
        } else {
            e.entry.has(flag::COMMUNE)
        };
        if self.after_locative(e.start, false) && (e.amb() != AMB_NONE || commune) {
            return 0.0; // « à Albert », « en Lorraine »
        }
        // Nom rare homonyme d'une commune, ou prénom trop rare pour valoir seul (« chantier de Briec », 1.0.2) :
        // un indice est exigé. A rare commune homonym, or a given name too rare to stand alone, needs a cue.
        if commune && e.given() < GIVEN_ALONE_MIN && e.surname() < COMMUNE_SURNAME_MIN {
            return 0.0;
        }
        if e.amb() == AMB_NONE {
            return 0.8;
        }
        // Mot ambigu seul : seul un prénom passe sans indice ; en tête de phrase, seul un prénom très fréquent.
        // Ambiguous word alone: given names only; at sentence start, only very frequent ones.
        if e.given() < GIVEN_ALONE_MIN {
            return 0.0;
        }
        if self.sentence_start(e.start) && (e.amb() == AMB_STRONG || e.given() < GIVEN_START_MIN) {
            return 0.0;
        }
        if e.amb() == AMB_STRONG {
            // « Marine nationale », « Rose des vents » : suivi d'un nom ou d'un adjectif, c'est le mot courant ;
            // suivi d'un verbe ou d'un mot-outil, c'est une personne. Followed by a noun: the common word.
            if let Some((start, end)) = patterns::next_word(text, e.end) {
                let mut next = Vec::with_capacity(end - start);
                det.chars.push_fold(&text[start..end], &mut next);
                let entry = det.vocab.get(&next);
                if entry.has(flag::WORD) && !entry.has(flag::FUNCTION) && !entry.has(flag::AUXILIARY) {
                    return 0.0;
                }
            }
        }
        0.7
    }

    // --- contexte local / local context ---------------------------------------------------------------

    /// `line_bounds` : (début, fin, ligne complète ?) autour de `pos`, dans une fenêtre bornée ; l'index des
    /// fins de ligne remplace les deux recherches : temps logarithmique. (start, end, whole line?) within a
    /// bounded window; the newline index replaces both searches: logarithmic time.
    pub(super) fn line_bounds(&self, pos: usize, window: usize) -> (usize, usize, bool) {
        let len = self.text.len();
        let lo = pos.saturating_sub(window);
        let next = self.newlines.partition_point(|&nl| nl < pos);
        // `text.rfind("\n", lo, pos)` : dernière fin de ligne avant `pos`, dans la fenêtre / last one in the window.
        let previous = next.checked_sub(1).map(|k| self.newlines[k]).filter(|&nl| nl >= lo);
        let mut start = previous.map_or(0, |nl| nl + 1);
        let mut whole = start > 0 || lo == 0;
        if !whole {
            start = lo;
        }
        let hi = len.min(pos + window);
        // `text.find("\n", pos, hi)` : première fin de ligne dès `pos` / first one from `pos`.
        let end = match self.newlines.get(next).filter(|&&nl| nl < hi) {
            Some(&nl) => nl,
            None => {
                whole = whole && hi == len;
                hi
            }
        };
        (start, end, whole)
    }

    /// `_sentence_start` : début de phrase, de ligne, de cellule ou de colonne (deux espaces).
    /// Sentence, line, cell or column start.
    pub(super) fn sentence_start(&self, pos: usize) -> bool {
        let (text, sets) = (&self.text, &self.det.text_sets);
        let mut i = pos;
        while i > 0 && sets.skip_back.contains(&text[i - 1]) && pos - (i - 1) < 12 {
            i -= 1;
        }
        // `i` est la position suivant le caractère examiné / `i` is one past the examined character.
        i == 0 || sets.sentence_end.contains(&text[i - 1]) || (i + 1 < pos && text[i] == ' ' && text[i + 1] == ' ')
    }

    /// `_line_start` : seul du balisage précède sur la ligne / only markup before, on this line.
    fn line_start(&self, pos: usize) -> bool {
        let text = &self.text;
        let line_start = rfind(text, '\n', pos.saturating_sub(32), pos).map_or(0, |i| i + 1);
        (line_start > 0 || pos <= 32) && strip_chars(&text[line_start..pos], " \t*_->#|•").is_empty()
    }

    /// `_previous_word` en minuscules (`str.lower()`), élision comprise (« l' ») / previous word, lowercased.
    fn previous_word(&self, pos: usize) -> Vec<char> {
        let (chars, text) = (&self.det.chars, &self.text);
        let alpha = |i: usize| chars.is(text[i], ALPHA);
        let mut word = Vec::new();
        if pos >= 2 && text[pos - 1] == '\'' && alpha(pos - 2) && (pos < 3 || !alpha(pos - 3)) {
            chars.push_lower(&text[pos - 2..pos], &mut word);
            return word;
        }
        // Indices décalés de un (`j` = j_python + 1) : pas de position négative / shifted by one, never negative.
        let mut j = pos;
        while j > 0 && matches!(text[j - 1], ' ' | '\t') && pos - (j - 1) < 4 {
            j -= 1;
        }
        let mut k = j;
        while k > 0 && alpha(k - 1) && j - k < 20 {
            k -= 1;
        }
        chars.push_lower(&text[k..j], &mut word);
        word
    }

    /// `_after_determiner` : « le Pierre », « mon Rose » / right after a determiner.
    fn after_determiner(&self, pos: usize) -> bool {
        let mut word = self.previous_word(pos);
        word.iter_mut().for_each(|c| *c = self.det.chars.fold(*c)); // `fold` garde la longueur / length kept
        !word.is_empty() && self.det.vocab.get(&word).has(flag::DETERMINER)
    }

    /// `_after_locative` : « à Albert », « en Lorraine » (texte d'origine : « à » et « a » diffèrent).
    /// After a place preposition (original text: "à" and "a" differ).
    fn after_locative(&self, pos: usize, verbs: bool) -> bool {
        let word = self.previous_word(pos);
        self.det.vocab.get(&word).has(flag::LOCATIVE)
            || (verbs && PLACE_VERBS.iter().any(|verb| word.iter().copied().eq(verb.chars())))
    }

    /// `_line_style` : (ligne en Casse De Titre, ligne en capitales). Un titre capitalise des mots courants ;
    /// une liste de noms, non. (Title Case line, all-caps line): a heading capitalises common words.
    fn line_style(&self, pos: usize, styles: &mut StyleCache) -> (bool, bool) {
        let (det, text) = (self.det, &self.text);
        let (line_start, line_end, whole) = self.line_bounds(pos, LINE_WINDOW);
        if let Some(&style) = styles.get(&line_start) {
            return style;
        }
        if !whole {
            styles.insert(line_start, (false, false)); // ligne très longue : de la prose / very long line: prose
            return (false, false);
        }
        let line = &text[line_start..line_end];
        let (mut words, mut capitals, mut common) = (0usize, 0usize, 0usize);
        let mut folded: Vec<char> = Vec::new();
        // `_WORD4_RE.findall` : suites de quatre lettres ou plus / runs of four letters or more.
        for word in line.split(|&c| !det.chars.is(c, LETTER)).filter(|w| w.len() >= 4) {
            words += 1;
            if det.chars.is_upper(&word[..1]) {
                capitals += 1;
                folded.clear();
                det.chars.push_fold(word, &mut folded);
                let entry = det.vocab.get(&folded);
                common += usize::from(entry.has(flag::WORD) || entry.has(flag::FUNCTION));
            }
        }
        // Un titre n'a pas de fin de phrase en son milieu / a heading has no inner sentence break.
        let heading = !det.chars.strip(line).windows(2).any(|pair| pair == ['.', ' ']);
        // `len(capitals) >= 0.75 * len(words)`, exact en entiers / exact in integers.
        let style =
            (heading && words >= 3 && 4 * capitals >= 3 * words && common >= 2, words >= 2 && det.chars.is_upper(line));
        styles.insert(line_start, style);
        style
    }
}

/// `_marker` : mot de rôle ou de raison sociale seul (« NÉE », « Fils ») / lone role or business word.
fn marker(found: &[&Element]) -> bool {
    matches!(found, [only] if only.entry.has(flag::CONTEXTUAL) || only.entry.has(flag::ORG_FAMILY))
}

impl Doc<'_> {
    /// `_score_pair` : deux noms ou plus, ou un nom et des initiales, sans indice / two names or more, no cue.
    fn score_pair(
        &self,
        run: &Run,
        elements: &[Element],
        found: &[&Element],
        initials: usize,
        title_line: bool,
        caps_line: bool,
    ) -> f64 {
        // Premier nom sûr (`solid[0]`) / first solid name.
        let solid = found.iter().copied().find(|e| e.solid());
        if caps_line {
            // Ligne en capitales : un prénom sûr et un nom (sûr ou inconnu) / all-caps line: stricter.
            let Some(anchor) = solid else {
                return 0.0;
            };
            let others = found.iter().any(|e| !std::ptr::eq(*e, anchor) && (e.solid() || e.kind == Kind::Unknown));
            return if anchor.given() > 0 && others { 0.85 } else { 0.0 };
        }
        if solid.is_some() {
            return 0.9;
        }
        if initials > 0 && found.len() == 1 {
            let e = found[0];
            // Après un mot inconnu, une lettre sans point suivie d'un numéro est une lettre de série (« Bodacc A
            // n° 2026… »), pas une initiale. After an unknown word, a dotless letter followed by a number is a series
            // letter, not an initial.
            let initial = elements[run.from..run.to].iter().any(|i| {
                i.kind == Kind::Initial
                    && (i.start < e.start
                        || self.text.get(i.end) == Some(&'.')
                        || !patterns::series_after(&self.text, i.end))
            });
            let ok = (e.kind == Kind::Name && e.surname() > 0 && e.amb() != AMB_ENTITY)
                || (e.kind == Kind::Unknown && e.key.len() >= 3 && initial);
            return if ok { 0.8 } else { 0.0 };
        }
        score_pair_rest(run, found, title_line)
    }
}

/// Fin de `_score_pair` : prénom ambigu et nom, capitales et prénom / end of `_score_pair`.
fn score_pair_rest(run: &Run, found: &[&Element], title_line: bool) -> f64 {
    let given = found.iter().copied().find(|e| {
        e.given() > 0
            && !e.caps
            && (matches!(e.amb(), AMB_WORD | AMB_STRONG) || (e.amb() == AMB_ENTITY && e.given() >= ENTITY_GIVEN_MIN))
    });
    if let Some(given) = given {
        if !(title_line || run.cap_left || run.cap_right) {
            let others = found.iter().any(|e| {
                !std::ptr::eq(*e, given) && ((e.surname() > 0 && e.amb() != AMB_ENTITY) || e.kind == Kind::Unknown)
            });
            if others {
                return 0.8; // « Pierre Blanc », « Rose Petit », « Noël Lopes »
            }
        }
    }
    let caps = found.iter().any(|e| e.caps && e.amb() != AMB_ENTITY && (e.kind == Kind::Unknown || e.surname() > 0));
    let lower = found.iter().any(|e| !e.caps && e.given() > 0 && e.amb() != AMB_ENTITY);
    if caps && lower {
        return 0.85; // « DUPONT Jean », « MARTIN Pierre »
    }
    // « VALLÉE Nath » : nom fréquent en capitales, prénom inconnu / frequent caps surname, unknown given name.
    let caps_known = found.iter().any(|e| e.caps && e.kind == Kind::Name && e.surname() >= SURNAME_ALONE_MIN);
    let lower_unknown = found.iter().any(|e| !e.caps && e.kind == Kind::Unknown && e.key.len() >= 3);
    if caps_known && lower_unknown && !title_line {
        0.8
    } else {
        0.0
    }
}
