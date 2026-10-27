//! Noms en minuscules : valeur d'un champ (« Nom : dupont ») et nom juste après un indice (« Bonjour jean »).
//!
//! Lowercase names: a field value after a strong label, and a name right after a cue (chats, tickets).
//! Port of `_lowercase_fields` and `_lowercase_after_cues`.

use super::chars::{eq, strip_chars, sub, WORD};
use super::cues::{Cues, Label, LABEL_VALUE_MAX};
use super::lexicon::{ambiguity, given_bias, given_rank, surname_rank, AMB_ENTITY, AMB_NONE, AMB_WORD};
use super::patterns;
use super::vocab::{flag, Entry};
use super::{inside, Doc, Found, GIVEN_ALONE_MIN, MEDIUM, PAIR_HOMONYM_MIN, STRONG, SURNAME_ALONE_MIN};

/// Mot d'un champ : (début, fin, clé repliée, code) / field word: (start, end, folded key, code).
type Word = (usize, usize, Vec<char>, Option<u16>);

/// `_FIELD_VALUE_STOP`, `_FIELD_VALUE_MAX_WORDS`, `_FIELD_CIVILITIES`, `_FIELD_SOLE_TRADER`, `_FIELD_TRIM`.
const FIELD_VALUE_STOP: &str = "\n\r|\t:";
const FIELD_VALUE_MAX_WORDS: usize = 6;
const FIELD_CIVILITIES: [&str; 7] = ["monsieur", "madame", "mademoiselle", "m.", "mme", "mlle", "mr"];
const FIELD_SOLE_TRADER: [&str; 2] = ["ei", "eirl"];
const FIELD_TRIM: &str = "()[],.;-–—";

impl Doc<'_> {
    /// Mot suivant d'un champ (`_FIELD_GAP_RE` puis `_FIELD_WORD_RE`) / next field word.
    fn next_field_word(&self, end: usize) -> Option<(usize, usize)> {
        let start = patterns::field_gap(&self.text, end)?;
        patterns::field_word(&self.det.chars, &self.text, start).map(|word_end| (start, word_end))
    }

    fn folded_word(&self, start: usize, end: usize) -> Vec<char> {
        let mut key = Vec::with_capacity(end - start);
        self.det.chars.push_fold(&self.text[start..end], &mut key);
        key
    }

    /// « Prénom Nom » sans doublon (`" ".join(dict.fromkeys(...))`), ordre Nom Prénom corrigé.
    /// "Given Surname" without duplicates; surname-first order fixed by the given-name bias.
    fn field_value(&self, words: &[(usize, usize, Option<u16>)]) -> String {
        let (mut given, mut surname) = (words[0], words[words.len() - 1]);
        if words.len() >= 2 && given_bias(surname.2) > given_bias(given.2) {
            (given, surname) = (surname, given); // « dupont jean » : ordre Nom Prénom / surname-first order
        }
        let (given, surname) = (&self.text[given.0..given.1], &self.text[surname.0..surname.1]);
        let mut value: String = given.iter().collect();
        if given != surname {
            value.push(' ');
            value.extend(surname.iter());
        }
        value
    }

    /// Mot replié sans la ponctuation de bord (`fold(word).strip(_FIELD_TRIM)`) / folded, edge punctuation off.
    fn trimmed_key(&self, word: (usize, usize)) -> Vec<char> {
        strip_chars(&self.folded_word(word.0, word.1), FIELD_TRIM).to_vec()
    }

    /// `_field_values` : valeur entière d'un champ d'état civil (« Nom : PANTALON »), quels que soient sa casse
    /// et ses mots, dans un document qui a un champ de prénom. Whole civil-status field value, in a document
    /// with a given-name field; ends at the line or column end within 80 characters, no other label on the line.
    pub(super) fn field_values(&self, labels: &[Label], found: &mut Vec<Found>) {
        let (det, text) = (self.det, &self.text);
        if !labels.iter().any(|label| label.3) {
            return;
        }
        // Valeur déjà trouvée aux mêmes bornes : sa zone et son choix de propagation restent / already found.
        let taken: Vec<(usize, usize)> = found.iter().map(|f| (f.start, f.end)).collect();
        let length = text.len();
        for &(pos, level, asks_name, _) in labels {
            if level != STRONG || !asks_name {
                continue;
            }
            let limit = length.min(pos + LABEL_VALUE_MAX);
            let mut end = pos;
            while end < limit && !FIELD_VALUE_STOP.contains(text[end]) {
                end += 1;
            }
            if (end == limit && limit < length) || (end < length && text[end] == ':') {
                continue; // trop longue, ou autre étiquette sur la ligne / too long, or another label on the line
            }
            // `[^  ]+` : mots séparés par des espaces / words split on spaces.
            let mut words: Vec<(usize, usize)> = Vec::new();
            let mut i = pos;
            while i < end {
                if text[i] == ' ' || text[i] == '\u{a0}' {
                    i += 1;
                    continue;
                }
                let start = i;
                while i < end && text[i] != ' ' && text[i] != '\u{a0}' {
                    i += 1;
                }
                words.push((start, i));
            }
            if let Some(&first) = words.first() {
                let key = self.folded_word(first.0, first.1);
                if FIELD_CIVILITIES.iter().any(|c| eq(&key, c)) {
                    words.remove(0);
                }
            }
            while let Some(&last) = words.last() {
                let key = self.trimmed_key(last);
                if key.is_empty() || FIELD_SOLE_TRADER.iter().any(|c| eq(&key, c)) {
                    words.pop();
                } else if eq(&key, "individuel")
                    && words.len() >= 2
                    && eq(&self.trimmed_key(words[words.len() - 2]), "entrepreneur")
                {
                    words.truncate(words.len() - 2);
                } else {
                    break;
                }
            }
            if words.is_empty() || words.len() > FIELD_VALUE_MAX_WORDS {
                continue;
            }
            let start = words[0].0;
            let mut stop = words[words.len() - 1].1;
            while stop > start && FIELD_TRIM.contains(text[stop - 1]) {
                stop -= 1;
            }
            let value = &text[start..stop];
            if !value.iter().any(|&c| det.chars.is_alnum(c))
                || value.iter().any(|&c| c.is_ascii_digit() || c == '@')
                || det.vocab.get(&self.folded_word(start, stop)).has(flag::EMPTY_CELL)
                || taken.contains(&(start, stop))
            {
                continue;
            }
            // Propagée seulement si aucun mot n'est courant, une commune ou un nom ambigu (`_field_safe`) ; valeur
            // en capitales : aussi en casse de titre (`surname_form`, côté Python). Propagated only when safe; a
            // capitals value is also propagated in title case.
            let safe = self.field_safe(&words);
            let form = (safe && det.chars.is_upper(value)).then(|| value.iter().collect());
            found.push(Found { start, end: stop, value: value.iter().collect(), score: 0.85, propagate: safe, form });
        }
    }

    /// `_field_safe` : un mot au moins (particules à part) n'est ni courant, ni une commune, ni un nom ambigu.
    /// At least one word (particles aside) is not a common word, a town or an ambiguous name.
    fn field_safe(&self, words: &[(usize, usize)]) -> bool {
        let det = self.det;
        let (mut names, mut risky) = (0usize, 0usize);
        for &word in words {
            let key = self.trimmed_key(word);
            let entry = det.vocab.get(&key);
            if key.is_empty() || entry.has(flag::PARTICLE) {
                continue;
            }
            names += 1;
            let commune = if key.contains(&'-') {
                let spaced: Vec<char> = key.iter().map(|&c| if c == '-' { ' ' } else { c }).collect();
                det.vocab.get(&spaced).has(flag::COMMUNE)
            } else {
                entry.has(flag::COMMUNE)
            };
            let ambiguous = det.code(&key).is_some_and(|code| ambiguity(code) != AMB_NONE);
            if entry.has(flag::WORD) || commune || ambiguous {
                risky += 1;
            }
        }
        risky < names
    }

    /// `_lowercase_fields` : valeur en minuscules après une étiquette forte ; s'arrête sur un mot courant.
    /// Lowercase value after a strong field label; stops at a common word.
    pub(super) fn lowercase_fields(&self, labels: &[Label], found: &mut Vec<Found>) {
        let (det, text) = (self.det, &self.text);
        for &(pos, level, asks_name, _) in labels {
            if level != STRONG {
                continue;
            }
            let Some(first_end) = patterns::field_word(&det.chars, text, pos) else {
                continue;
            };
            if !det.chars.is_lower(&text[pos..first_end]) {
                continue;
            }
            // Les mots suivants peuvent être capitalisés (« jean Dupont ») / later words may be capitalised.
            let mut words: Vec<Word> = Vec::new();
            let mut word = Some((pos, first_end));
            while let Some((start, end)) = word {
                if words.len() >= 4 {
                    break;
                }
                let key = self.folded_word(start, end);
                let entry = det.vocab.get(&key);
                let code = det.code(&key);
                let common = entry.has(flag::FUNCTION)
                    || entry.has(flag::STOP)
                    || entry.has(flag::EMPTY_CELL)
                    || (code.is_none() && entry.has(flag::WORD));
                if !entry.has(flag::PARTICLE) && common {
                    break; // mot courant : ce n'est pas un nom / a common word: not a name
                }
                words.push((start, end, key, code));
                word = self.next_field_word(end);
            }
            let particle = |w: &Word| det.vocab.get(&w.2).has(flag::PARTICLE);
            while words.last().is_some_and(particle) {
                words.pop();
            }
            let names: Vec<(usize, usize, Option<u16>)> =
                words.iter().filter(|w| !particle(w)).map(|w| (w.0, w.1, w.3)).collect();
            let Some(last) = words.last() else {
                continue;
            };
            if names.is_empty() || !patterns::field_end(&det.chars, text, last.1) {
                continue; // rien, ou une phrase qui continue / nothing, or a sentence going on
            }
            if !asks_name && names.iter().all(|w| w.2.is_none()) {
                continue; // « Bénéficiaire : désigné » : mot inconnu seul / unknown word under a role label
            }
            let safe = names.iter().all(|w| w.2.is_none_or(|code| ambiguity(code) == AMB_NONE));
            found.push(Found {
                start: words[0].0,
                end: last.1,
                value: self.field_value(&names),
                score: 0.85,
                propagate: safe,
                form: None,
            });
        }
    }

    /// `_lowercase_after_cues` : « client guillaume », « M. dupont » ; seuls les prénoms et noms connus
    /// sans autre lecture comptent. Lowercase name right after a cue; only known names with no other reading.
    pub(super) fn lowercase_after_cues(&self, cues: &Cues, found: &mut Vec<Found>) {
        let (det, text) = (self.det, &self.text);
        let mut covered: Vec<(usize, usize)> = found.iter().map(|f| (f.start, f.end)).collect();
        covered.sort_unstable();
        for (pos, level) in cues.at.iter() {
            if level < MEDIUM {
                continue;
            }
            let Some(first_end) = patterns::field_word(&det.chars, text, pos) else {
                continue;
            };
            if !det.chars.is_lower(sub(text, pos, first_end)) || inside(&covered, pos, first_end) {
                continue;
            }
            // Le mot suivant peut être capitalisé (« guillaume Martin ») / the next word may be capitalised.
            let mut words: Vec<(usize, usize, Option<u16>)> = Vec::new();
            let mut word = Some((pos, first_end));
            while let Some((start, end)) = word {
                if words.len() >= 3 {
                    break;
                }
                let key = self.folded_word(start, end);
                let entry = det.vocab.get(&key);
                let Some(code) = det.code(&key) else {
                    break;
                };
                // « Le salarié doit être convoqué » : un verbe après un rôle n'est jamais un nom (1.0.2).
                // A verb after a role word is never a name.
                if entry.has(flag::FUNCTION) || entry.has(flag::STOP) || entry.has(flag::AUXILIARY) {
                    break;
                }
                if !words.is_empty() {
                    // Après un prénom retenu, un nom connu suffit, même homonyme (« guillaume martin »).
                    // After an accepted given name, a known surname is enough, even a homonym.
                    if surname_rank(code) < SURNAME_ALONE_MIN {
                        break;
                    }
                } else if entry.has(flag::WORD)
                    || ambiguity(code) != AMB_NONE
                    || (given_rank(code) < GIVEN_ALONE_MIN && surname_rank(code) < SURNAME_ALONE_MIN)
                {
                    break; // mot courant, rare ou ambigu : pas un nom / common, rare or ambiguous word
                }
                words.push((start, end, Some(code)));
                word = self.next_field_word(end);
            }
            let Some(last) = words.last() else {
                continue;
            };
            found.push(Found {
                start: words[0].0,
                end: last.1,
                value: self.field_value(&words),
                score: 0.8,
                propagate: true,
                form: None,
            });
        }
    }

    /// `_lowercase_pairs` : « rdv avec sophie martin » : prénom puis nom en minuscules, sans indice (1.0.2, fort
    /// et essentiel). Lowercase given name then surname with no cue. `_LOWER_PAIR_RE.finditer` : le premier mot
    /// seul est consommé, le second est lu en avance / only the first word is consumed, the second is a lookahead.
    pub(super) fn lowercase_pairs(&self, found: &mut Vec<Found>) {
        let (det, text) = (self.det, &self.text);
        let mut covered: Vec<(usize, usize)> = found.iter().map(|f| (f.start, f.end)).collect();
        covered.sort_unstable();
        let common = |entry: Entry| {
            entry.has(flag::FUNCTION)
                || entry.has(flag::STOP)
                || entry.has(flag::PARTICLE)
                || entry.has(flag::AUXILIARY)
        };
        let mut added = Vec::new();
        let mut key: Vec<char> = Vec::with_capacity(32);
        let mut pos = 0;
        while pos < text.len() {
            // `(?<![\w'’.@/-])` puis le premier mot, suivi d'un seul blanc / then the first word and one blank.
            let free = pos == 0 || !(det.chars.is(text[pos - 1], WORD) || "'’.@/-".contains(text[pos - 1]));
            let first_end = if free { lower_word(text, pos) } else { None };
            let Some(first_end) = first_end.filter(|&e| matches!(text.get(e), Some(' ' | '\t'))) else {
                pos += 1;
                continue;
            };
            let start = pos;
            pos = first_end;
            let second_start = first_end + 1;
            let Some(second_end) = lower_word(text, second_start) else {
                continue;
            };
            // `(?![\w'’@-])` après le second mot / after the second word.
            if text.get(second_end).is_some_and(|&c| det.chars.is(c, WORD) || "'’@-".contains(c)) {
                continue;
            }
            // Tampon réutilisé : la plupart des mots de la prose passent ici / reused buffer: most prose words get here.
            key.clear();
            det.chars.push_fold(&text[start..first_end], &mut key);
            let first_entry = det.vocab.get(&key);
            let Some(code1) = det.code(&key) else {
                continue;
            };
            if ambiguity(code1) != AMB_NONE
                || given_rank(code1) < GIVEN_ALONE_MIN
                || given_rank(code1) <= surname_rank(code1)
                || first_entry.has(flag::WORD)
                || first_entry.has(flag::COMMUNE)
                || common(first_entry)
            {
                continue;
            }
            let second_key = self.folded_word(second_start, second_end);
            let second_entry = det.vocab.get(&second_key);
            let Some(code2) = det.code(&second_key) else {
                continue;
            };
            if surname_rank(code2) < SURNAME_ALONE_MIN || second_entry.has(flag::WORD) || common(second_entry) {
                continue;
            }
            let amb = ambiguity(code2);
            let accepted = amb == AMB_NONE || (amb == AMB_WORD && surname_rank(code2) >= PAIR_HOMONYM_MIN);
            if !accepted {
                continue;
            }
            if inside(&covered, start, second_end) {
                continue;
            }
            added.push(Found {
                start,
                end: second_end,
                value: self.field_value(&[(start, first_end, Some(code1)), (second_start, second_end, Some(code2))]),
                score: 0.8,
                propagate: amb == AMB_NONE,
                form: None,
            });
        }
        found.extend(added);
    }

    /// `_lowercase_after_prepositions` : « prise en charge par mathéo » : prénom seul en minuscules après « par »,
    /// « avec », « chez », « pour » ou « à » (1.0.2, troisième tour, fort et essentiel). `_PREPOSITION_NAME_RE.finditer` :
    /// après une correspondance, la recherche reprend après le mot / after a match, the search resumes after the word.
    pub(super) fn lowercase_after_prepositions(&self, found: &mut Vec<Found>) {
        let (det, text) = (self.det, &self.text);
        let mut covered: Vec<(usize, usize)> = found.iter().map(|f| (f.start, f.end)).collect();
        covered.sort_unstable();
        let common = |entry: Entry| {
            entry.has(flag::FUNCTION)
                || entry.has(flag::STOP)
                || entry.has(flag::PARTICLE)
                || entry.has(flag::AUXILIARY)
        };
        let mut added = Vec::new();
        let mut pos = 0;
        while pos < text.len() {
            let free = pos == 0 || !(det.chars.is(text[pos - 1], WORD) || "'’.@/-".contains(text[pos - 1]));
            let prep_end = if free { preposition_end(text, pos) } else { None };
            let start = prep_end.filter(|&e| matches!(text.get(e), Some(' ' | '\t'))).map(|e| e + 1);
            let Some(start) = start else {
                pos += 1;
                continue;
            };
            let Some(end) = lower_word(text, start)
                .filter(|&e| !text.get(e).is_some_and(|&c| det.chars.is(c, WORD) || "'’@-".contains(c)))
            else {
                pos += 1;
                continue;
            };
            pos = end;
            let key = self.folded_word(start, end);
            let entry = det.vocab.get(&key);
            let Some(code) = det.code(&key) else {
                continue;
            };
            if ambiguity(code) != AMB_NONE
                || given_rank(code) < GIVEN_ALONE_MIN
                || given_rank(code) <= surname_rank(code)
                || entry.has(flag::WORD)
                || entry.has(flag::COMMUNE)
                || common(entry)
                || inside(&covered, start, end)
            {
                continue;
            }
            added.push(Found {
                start,
                end,
                value: text[start..end].iter().collect(),
                score: 0.8,
                propagate: true,
                form: None,
            });
        }
        found.extend(added);
    }

    /// `_file_name_people` : « CV_Nadia_Haddad.pdf » : Prénom_Nom dans un nom de fichier (1.0.2, fort et essentiel).
    /// Given_Surname inside a file name. `_FILE_PAIR_RE.finditer` : les deux segments sont consommés.
    pub(super) fn file_name_people(&self, found: &mut Vec<Found>) {
        let (det, text) = (self.det, &self.text);
        let mut covered: Vec<(usize, usize)> = found.iter().map(|f| (f.start, f.end)).collect();
        covered.sort_unstable();
        // `(?<![^\W_])` et `(?![^\W_])` : ni lettre ni chiffre accolé, « _ » admis / no glued letter or digit.
        let glued = |c: Option<&char>| c.is_some_and(|&c| det.chars.is(c, WORD) && c != '_');
        let mut added = Vec::new();
        let mut pos = 0;
        while pos < text.len() {
            let free = pos == 0 || !glued(text.get(pos - 1));
            let first_end = if free { file_segment(text, pos) } else { None };
            let pair = first_end
                .filter(|&e| text.get(e) == Some(&'_'))
                .and_then(|e| file_segment(text, e + 1).map(|second_end| (e, second_end)))
                .filter(|&(_, second_end)| !glued(text.get(second_end)));
            let Some((first_end, second_end)) = pair else {
                pos += 1;
                continue;
            };
            let start = pos;
            pos = second_end;
            let second_start = first_end + 1;
            let first_key = self.folded_word(start, first_end);
            let second_key = self.folded_word(second_start, second_end);
            let (first_entry, second_entry) = (det.vocab.get(&first_key), det.vocab.get(&second_key));
            let Some(code1) = det.code(&first_key) else {
                continue;
            };
            if ambiguity(code1) != AMB_NONE
                || given_rank(code1) < GIVEN_ALONE_MIN
                || given_rank(code1) <= surname_rank(code1)
                || first_entry.has(flag::STOP)
            {
                continue;
            }
            let code2 = det.code(&second_key);
            let rejected = match code2 {
                Some(code) => ambiguity(code) == AMB_ENTITY,
                None => second_entry.has(flag::WORD),
            };
            if second_entry.has(flag::STOP) || second_entry.has(flag::FUNCTION) || rejected {
                continue;
            }
            if inside(&covered, start, second_end) {
                continue;
            }
            added.push(Found {
                start,
                end: second_end,
                value: self.field_value(&[(start, first_end, Some(code1)), (second_start, second_end, code2)]),
                score: 0.8,
                propagate: code2.is_some_and(|code| ambiguity(code) == AMB_NONE),
                form: None,
            });
        }
        found.extend(added);
    }
}

/// Segment `[UPPER][L]{1,30}` d'un nom de fichier (majuscule latine puis minuscules latines), fin ou `None`.
/// A file-name segment: a Latin capital then 1 to 30 Latin lowercase letters (a longer run can never match).
fn file_segment(text: &[char], pos: usize) -> Option<usize> {
    let upper = |c: char| matches!(c, 'A'..='Z' | '\u{c0}'..='\u{d6}' | '\u{d8}'..='\u{de}');
    if !text.get(pos).is_some_and(|&c| upper(c)) {
        return None;
    }
    let lowers = text.get(pos + 1..).map_or(0, |rest| rest.iter().take(31).take_while(|&&c| is_lower_latin(c)).count());
    (1..=30).contains(&lowers).then_some(pos + 1 + lowers)
}

/// Minuscule latine de `_LOWER_LETTERS` / Latin lowercase letter.
fn is_lower_latin(c: char) -> bool {
    matches!(c, 'a'..='z' | '\u{df}'..='\u{f6}' | '\u{f8}'..='\u{ff}' | '\u{153}')
}

/// `_LOWER_WORD` en `pos` : `[L]{2,30}(?:-[L]{2,30})?` (lettres minuscules latines), fin du mot ou `None`. Un
/// mot plus long, ou un trait d'union sans seconde partie, ne peut jamais réussir dans le motif : `None`.
/// Lowercase Latin word at `pos`; a longer run, or a hyphen without a valid second part, can never match.
/// `_PREPOSITION_NAME_RE` : « par », « avec », « chez », « pour » ou « à » en `pos` ; fin du mot, sinon None.
/// A strong preposition at `pos`: its end, else None.
fn preposition_end(text: &[char], pos: usize) -> Option<usize> {
    const PREPOSITIONS: [&str; 5] = ["par", "avec", "chez", "pour", "à"];
    PREPOSITIONS.iter().find_map(|word| {
        let n = word.chars().count();
        let slice = text.get(pos..pos + n)?;
        slice.iter().copied().eq(word.chars()).then_some(pos + n)
    })
}

fn lower_word(text: &[char], pos: usize) -> Option<usize> {
    let run = |from: usize| {
        text.get(from..).map_or(0, |rest| rest.iter().take(31).take_while(|&&c| is_lower_latin(c)).count())
    };
    let first = run(pos);
    if !(2..=30).contains(&first) {
        return None;
    }
    let end = pos + first;
    if text.get(end) != Some(&'-') {
        return Some(end);
    }
    let second = run(end + 1);
    (2..=30).contains(&second).then_some(end + 1 + second)
}
