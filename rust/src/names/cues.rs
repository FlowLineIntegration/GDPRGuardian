//! Indices d'un document : déclencheurs, étiquettes, signatures, adresses e-mail.
//!
//! Document cues: triggers (one Aho-Corasick pass on the folded text), field labels, signature
//! blocks, e-mail display names and local parts. Port of `_cues`, `_label_cues`, `_signature_zone`,
//! `_display_ends` and `_email_names`; state local to one call.

use super::chars::{blanks, eq, find, rfind, strip_chars, sub, CharCursor, WORD};
use super::lexicon::{ambiguity, given_rank, surname_rank, AMB_ENTITY, AMB_NONE};
use super::patterns;
use super::vocab::flag;
use super::{
    Confirmed, Doc, PositionMap, Positions, GIVEN_ALONE_MIN, MEDIUM, NEG, NONE, STRONG, SURNAME_ALONE_MIN, T_CLOSING,
    T_EPONYM, T_EPONYM_DIRECT, T_GREETING, T_HONORIFIC, T_ROLE,
};

/// Étiquette de champ : (début de la valeur, force, demande un nom ?, demande un prénom ?).
/// Field label: (value start, strength, does the label ask for a name?, for a given name?).
pub(super) type Label = (usize, i8, bool, bool);

/// Positions -> force, dans l'ordre d'insertion (comme un `dict` Python) / insertion-ordered, like a dict.
#[derive(Default)]
pub(super) struct CueMap {
    order: Vec<(usize, i8)>,
    index: PositionMap<usize>,
}

impl CueMap {
    pub fn get(&self, pos: usize) -> Option<i8> {
        self.index.get(&pos).map(|&i| self.order[i].1)
    }

    fn set(&mut self, pos: usize, level: i8) {
        match self.index.get(&pos) {
            Some(&i) => self.order[i].1 = level,
            None => {
                self.index.insert(pos, self.order.len());
                self.order.push((pos, level));
            }
        }
    }

    pub fn iter(&self) -> impl Iterator<Item = (usize, i8)> + '_ {
        self.order.iter().copied()
    }
}

/// Indices d'un document (`_Cues`), état local à l'appel / per-call document cues.
#[derive(Default)]
pub(super) struct Cues {
    pub at: CueMap,
    pub signature: Vec<(usize, usize)>,
    pub strong: Vec<(usize, usize)>,
    pub display: Positions,
    /// Position d'un nom -> début de la particule qu'un indice désignait (« M. de Villepin »).
    /// Name position -> start of the particle a cue pointed at.
    pub particle_from: PositionMap<usize>,
    /// Après « le juge », « mon fils » / after a role or kinship word.
    pub roles: Positions,
    /// Après « Bonjour », « Cher » / after a greeting.
    pub greetings: Positions,
    /// Après une étiquette de champ (« Nom : ») / after a field label.
    pub labels: Positions,
    /// Indice négatif d'un code postal dont le mot suivant ne commence aucune de ses communes : un prénom suivi
    /// d'un autre nom l'emporte (« Matricule 75012 Sophie Martin »). A postcode's negative cue whose next word
    /// starts none of its towns: a given name followed by another name overrides it.
    pub postcodes: Positions,
}

/// Ensemble que `put` complète / the set `put` also fills.
#[derive(Clone, Copy)]
enum CueKind {
    Plain,
    Role,
    Greeting,
    Label,
}

/// Longueur examinée de la valeur d'une étiquette (`_LABEL_VALUE_MAX`) / field value length examined.
pub(super) const LABEL_VALUE_MAX: usize = 80;
/// Ponctuation retirée autour des mots d'une valeur (`_VALUE_STRIP`) / punctuation stripped around value words.
const VALUE_STRIP: &str = ",;:()[]\"'«»";
/// `_VALUE_STOPS` : la valeur propre d'un champ s'arrête avant ces mots / a field's own value stops before them.
const VALUE_STOPS: [&str; 3] = ["pour", "de", "chez"];

impl Cues {
    /// L'indice vaut aussi après une particule (« M. de Villepin ») ; un éponyme l'emporte toujours.
    /// The cue also holds past a particle; an eponym always wins.
    fn put(&mut self, text: &[char], pos: usize, level: i8, shift: bool, kind: CueKind) {
        let shifted = if shift { patterns::particle_at(text, pos) } else { None };
        if let Some(end) = shifted {
            self.particle_from.insert(end, pos);
        }
        for p in std::iter::once(pos).chain(shifted) {
            let current = self.at.get(p).unwrap_or(NONE);
            if level == NEG || (current != NEG && current < level) {
                self.at.set(p, level);
            }
            match kind {
                CueKind::Plain => {}
                CueKind::Role => {
                    self.roles.insert(p);
                }
                CueKind::Greeting => {
                    self.greetings.insert(p);
                }
                CueKind::Label => {
                    self.labels.insert(p);
                }
            }
        }
    }
}

impl Doc<'_> {
    /// `_cues` : déclencheurs repliés (un passage), puis étiquettes / folded triggers, then labels.
    pub(super) fn cues(&self, strong_zones: Vec<(usize, usize)>, labels: &[Label]) -> Cues {
        let (det, text, folded) = (self.det, &self.text, &self.folded);
        let chars = &det.chars;
        let mut cues = Cues::default();
        let mut negative = Positions::default();
        let mut cursor = CharCursor::new(self.folded_utf8);
        for m in det.triggers.find_iter(self.folded_utf8) {
            let trigger = &det.trigger_info[m.pattern().as_usize()];
            let (start, end) = (cursor.at(m.start()), cursor.at(m.end()));
            // Un trait d'union lie les mots : « Notre-Dame » ne contient pas la civilité « Dame ».
            // A hyphen binds words: "Notre-Dame" does not contain the honorific "Dame".
            let bound = |c: char| chars.is_alnum(c) || c == '-';
            if (trigger.check_left && start > 0 && bound(folded[start - 1]))
                || (trigger.check_right && end < text.len() && bound(folded[end]))
            {
                continue;
            }
            let mut flags = trigger.flags;
            if flags & T_HONORIFIC != 0 && trigger.case_sensitive && !chars.is_upper(&text[start..start + 1]) {
                flags &= !T_HONORIFIC;
            }
            let places = T_EPONYM | T_EPONYM_DIRECT | T_ROLE;
            if flags & places != 0 && end - start > 1 && chars.is_upper(&text[start..end]) {
                flags &= !places; // « VALLÉE Nath » : nom en capitales / caps surname
            }
            if flags & T_CLOSING != 0 {
                if let Some(zone) = self.signature_zone(end) {
                    cues.signature.push(zone);
                }
            }
            if flags & T_EPONYM != 0 || negative.contains(&start) {
                // « rue du Docteur Roux » : l'éponyme se transmet à la civilité suivante / eponym chains on.
                if let Some(after) = patterns::after_eponym(text, end) {
                    negative.insert(after);
                    cues.put(text, after, NEG, true, CueKind::Plain);
                }
            } else if flags & T_EPONYM_DIRECT != 0 {
                // « tour Eiffel », pas « le tour de Pierre » / direct apposition only.
                if let Some(after) = patterns::after_direct(text, end) {
                    negative.insert(after);
                    cues.put(text, after, NEG, false, CueKind::Plain);
                }
            } else if flags & T_HONORIFIC != 0 {
                let next = patterns::after_honorific(text, end);
                // « M. le Maire » n'est pas un nom, « M. Le Verger » en est un / is not a name, "M. Le Verger" is.
                if (next > end || folded[end - 1] == '.')
                    && (!patterns::article_at(chars, folded, next) || self.particle_surname(next))
                {
                    cues.put(text, next, STRONG, true, CueKind::Plain);
                }
            } else if flags & (T_GREETING | T_ROLE) != 0 {
                if let Some(after) = patterns::after_cue(text, end) {
                    let kind = if flags & T_GREETING != 0 {
                        CueKind::Greeting
                    } else if trigger.chez {
                        CueKind::Plain // « chez » désigne aussi un lieu / may name a place
                    } else {
                        CueKind::Role
                    };
                    cues.put(text, after, MEDIUM, true, kind);
                }
            }
        }
        // « 30600 VAUVERT » : après un code postal connu vient la commune / a town follows a known postcode.
        let mut head: Vec<char> = Vec::new();
        for (code, pos) in self.postcode_ends() {
            if cues.at.get(pos) != Some(NEG) {
                // Premier mot replié (`[a-z0-9]+`) : début d'une commune de ce code ? / starts one of its towns?
                head.clear();
                head.extend_from_slice(&text[code..code + 5]);
                head.push(' ');
                head.extend(folded[pos..].iter().take_while(|c| c.is_ascii_lowercase() || c.is_ascii_digit()));
                if head.len() == 6 || !det.vocab.get(&head).has(flag::POSTCODE_HEAD) {
                    cues.postcodes.insert(pos);
                }
            }
            cues.put(text, pos, NEG, false, CueKind::Plain);
        }
        for &(pos, level, ..) in labels {
            cues.put(text, pos, level, true, CueKind::Label);
        }
        cues.signature.sort_unstable();
        if text.contains(&'@') {
            cues.display = self.display_ends();
        }
        cues.strong = strong_zones;
        cues.strong.sort_unstable();
        cues
    }

    /// `_label_cues` : « Nom : Dupont », « De : Jean Martin » en début de ligne ou de colonne.
    /// Field labels at line or column start.
    pub(super) fn label_cues(&self) -> Vec<Label> {
        let (det, text) = (self.det, &self.text);
        let mut labels = Vec::new();
        let mut folded_label: Vec<char> = Vec::new();
        let mut colon = find(text, ':', 0, text.len());
        while let Some(pos) = colon {
            let line_start = rfind(text, '\n', pos.saturating_sub(61), pos).map_or(0, |i| i + 1);
            if line_start > 0 || pos <= 61 {
                folded_label.clear();
                det.chars.push_fold(patterns::after_last_label_separator(&text[line_start..pos]), &mut folded_label);
                let label = strip_chars(&folded_label, " >*_#-`•");
                let entry = det.vocab.get(label);
                let mut level = if entry.has(flag::STRONG_LABEL) {
                    STRONG
                } else if entry.has(flag::WEAK_LABEL) {
                    MEDIUM
                } else {
                    NONE
                };
                if level == NONE && !entry.has(flag::NON_PERSON_LABEL) {
                    // « Étaient présents : », « Le médecin traitant : » : dernier mot / last word of the label.
                    if let Some(space) = label.iter().rposition(|&c| c == ' ') {
                        let last = det.vocab.get(&label[space + 1..]);
                        if last.has(flag::STRONG_LABEL) || last.has(flag::WEAK_LABEL) {
                            level = MEDIUM;
                        }
                    }
                }
                if level != NONE {
                    let value = patterns::after_label(text, pos + 1);
                    if !self.organisation_value(value) {
                        let given = entry.has(flag::GIVEN_HEADER);
                        labels.push((value, level, given || entry.has(flag::SURNAME_HEADER), given));
                    }
                }
            }
            colon = find(text, ':', pos + 1, text.len());
        }
        labels
    }

    /// `_organisation_value` : la valeur d'un champ est-elle une organisation ? Forme juridique de société parmi
    /// les mots de la valeur propre (avant « pour », « de », « chez », une parenthèse, une virgule ou un tiret), ou
    /// premier mot d'organisme suivi d'autre chose qu'un prénom. Is the field value an organisation?
    fn organisation_value(&self, pos: usize) -> bool {
        let (det, text) = (self.det, &self.text);
        let end = find(text, '\n', pos, pos + LABEL_VALUE_MAX).unwrap_or(pos + LABEL_VALUE_MAX);
        let value = sub(text, pos, end);
        // `value.split("(", 1)[0].split(",", 1)[0]` : avant la première parenthèse ou virgule / before either.
        let own = &value[..value.iter().position(|&c| c == '(' || c == ',').unwrap_or(value.len())];
        let mut key: Vec<char> = Vec::new();
        for raw in own.split(|&c| det.chars.is_space(c)).filter(|w| !w.is_empty()) {
            key.clear();
            det.chars.push_fold(raw, &mut key);
            if matches!(raw, ['-' | '–' | '—']) || VALUE_STOPS.iter().any(|stop| eq(&key, stop)) {
                break;
            }
            let word = strip_chars(raw, VALUE_STRIP);
            if !word.is_empty() && (det.chars.is_upper(word) || word.contains(&'.')) {
                key.clear();
                det.chars.push_fold(word, &mut key);
                key.retain(|&c| c != '.');
                if det.vocab.get(&key).has(flag::COMPANY_FORM) {
                    return true;
                }
            }
        }
        let words: Vec<&[char]> = value
            .split(|&c| det.chars.is_space(c))
            .map(|w| strip_chars(w, VALUE_STRIP))
            .filter(|w| !w.is_empty())
            .collect();
        let [first, second, ..] = words[..] else {
            return false;
        };
        key.clear();
        det.chars.push_fold(first, &mut key);
        if !det.vocab.get(&key).has(flag::ORG_LEAD) {
            return false;
        }
        key.clear();
        det.chars.push_fold(second, &mut key);
        det.code(&key).is_none_or(|code| given_rank(code) < GIVEN_ALONE_MIN)
    }

    /// `_particle_surname` : « M. Le Verger », article capitalisé et mot suivant formant un nom connu (« le verger »),
    /// ni rôle ni titre. A capitalised article and the next word forming a known name, neither a role nor a title.
    fn particle_surname(&self, pos: usize) -> bool {
        let (det, text, folded) = (self.det, &self.text, &self.folded);
        if pos + 3 >= text.len()
            || !det.chars.is_upper(&text[pos..pos + 1])
            || !(eq(&folded[pos..pos + 3], "le ") || eq(&folded[pos..pos + 3], "la "))
        {
            return false;
        }
        let Some(end) = patterns::token(&det.chars, text, pos + 3) else {
            return false;
        };
        let word = det.vocab.get(&folded[pos + 3..end]);
        det.vocab.get(&folded[pos..end]).name().is_some() && !word.has(flag::CONTEXTUAL) && !word.has(flag::TITLE)
    }

    /// (début du code, fin) de `_POSTCODE_CUE_RE` (`(?<![\w.,/-])([0-9]{5})[ \t]{1,2}`) dont le code est connu.
    /// (code start, match end) of `_POSTCODE_CUE_RE` whose postcode is known.
    fn postcode_ends(&self) -> Vec<(usize, usize)> {
        let (det, text) = (self.det, &self.text);
        let digit = |i: usize| text.get(i).is_some_and(char::is_ascii_digit);
        let mut ends = Vec::new();
        let mut pos = 0;
        while pos + 5 < text.len() {
            if !digit(pos) {
                pos += 1;
                continue;
            }
            let free = pos == 0 || {
                let c = text[pos - 1];
                !(det.chars.is(c, WORD) || matches!(c, '.' | ',' | '/' | '-'))
            };
            let five = (pos..pos + 5).all(digit);
            let gap = blanks(text, pos + 5, 2);
            if free && five && gap > 0 && det.vocab.get(&text[pos..pos + 5]).has(flag::POSTCODE) {
                ends.push((pos, pos + 5 + gap));
                pos += 5 + gap;
                continue;
            }
            pos += 1;
        }
        ends
    }

    /// `_signature_zone` : les trois lignes non vides après une formule de fin seule sur sa ligne.
    /// The three non-empty lines after a closing alone on its line.
    fn signature_zone(&self, end: usize) -> Option<(usize, usize)> {
        let (chars, text) = (&self.det.chars, &self.text);
        let line_end = find(text, '\n', end, end + 80)?;
        if !strip_chars(&text[end..line_end], " \t\r,.!").is_empty() {
            return None;
        }
        let limit = text.len().min(line_end + 300);
        let (mut pos, mut lines) = (line_end, 0);
        while pos < limit && lines < 3 {
            // Recherche bornée à `limit` : même résultat, coût constant / bounded search, same result.
            let next = find(text, '\n', pos + 1, limit + 1).unwrap_or(limit);
            if sub(text, pos + 1, next).iter().any(|&c| !chars.is_space(c)) {
                lines += 1;
            }
            pos = next;
        }
        Some((line_end, pos))
    }

    /// `_display_ends` : fins de « Jean Dupont <jean.dupont@…> » / positions right before a bracketed e-mail.
    fn display_ends(&self) -> Positions {
        let (chars, text) = (&self.det.chars, &self.text);
        let mut ends = Positions::default();
        for opener in patterns::at_signs(text).filter_map(|at| patterns::display_opener(chars, text, at)) {
            let mut j = opener;
            while j > 0 && matches!(text[j - 1], ' ' | '\t') {
                j -= 1;
            }
            if j > 0 && text[j - 1] == '"' {
                j -= 1;
            }
            ends.insert(j);
        }
        ends
    }

    /// `_email_names` : noms tirés des parties locales prenom.nom@ (repliés) / names from e-mail local parts.
    pub(super) fn email_names(&self, found: &mut Confirmed) {
        let det = self.det;
        for (start, end) in patterns::email_locals(&det.chars, &self.folded) {
            let parts: Vec<&[char]> = self.folded[start..end]
                .split(|c| matches!(c, '.' | '_' | '-' | '+'))
                .map(strip_digits)
                .filter(|part| part.len() >= 2 && part.iter().all(char::is_ascii_lowercase))
                .collect();
            if parts.len() >= 2 {
                // « jean.dupont@ » (un prénom), ou deux parties qui ne sont pas des mots (« detlev.wagenknecht@ »).
                // A given name among the parts, or two parts that are not common words.
                let plain: Vec<&[char]> = parts
                    .iter()
                    .copied()
                    .filter(|part| {
                        let entry = det.vocab.get(part);
                        !entry.has(flag::WORD) && !entry.has(flag::STOP)
                    })
                    .collect();
                let given = parts.iter().any(|part| {
                    det.code(part).is_some_and(|code| given_rank(code) > 0 && ambiguity(code) != AMB_ENTITY)
                });
                if given || (parts.len() == 2 && plain.len() == 2 && parts.iter().all(|part| part.len() >= 3)) {
                    found.extend(plain.iter().map(|part| part.to_vec()));
                }
            } else if let [part] = parts[..] {
                // « jdupont », « dupontj » / initial glued to the surname.
                let candidates = [part, &part[1..], &part[..part.len() - 1]];
                for (k, candidate) in candidates.into_iter().enumerate() {
                    let code = if candidate.len() >= 4 { det.code(candidate) } else { None };
                    let named = code.is_some_and(|code| {
                        ambiguity(code) == AMB_NONE
                            && (surname_rank(code) >= SURNAME_ALONE_MIN || (k == 0 && given_rank(code) > 0))
                    });
                    if named {
                        found.insert(candidate.to_vec());
                        break;
                    }
                }
            }
        }
    }
}

/// `part.strip("0123456789")`.
fn strip_digits(part: &[char]) -> &[char] {
    strip_chars(part, "0123456789")
}

/// « chez » (`trig.patterns[index] == "chez"`).
pub(super) fn is_chez(pattern: &[char]) -> bool {
    eq(pattern, "chez")
}
