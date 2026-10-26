//! Noms en minuscules : valeur d'un champ (« Nom : dupont ») et nom juste après un indice (« Bonjour jean »).
//!
//! Lowercase names: a field value after a strong label, and a name right after a cue (chats, tickets).
//! Port of `_lowercase_fields` and `_lowercase_after_cues`.

use super::chars::sub;
use super::cues::{Cues, Label};
use super::lexicon::{ambiguity, given_bias, given_rank, surname_rank, AMB_NONE};
use super::patterns;
use super::vocab::flag;
use super::{inside, Doc, Found, GIVEN_ALONE_MIN, MEDIUM, STRONG, SURNAME_ALONE_MIN};

/// Mot d'un champ : (début, fin, clé repliée, code) / field word: (start, end, folded key, code).
type Word = (usize, usize, Vec<char>, Option<u16>);

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

    /// `_lowercase_fields` : valeur en minuscules après une étiquette forte ; s'arrête sur un mot courant.
    /// Lowercase value after a strong field label; stops at a common word.
    pub(super) fn lowercase_fields(&self, labels: &[Label], found: &mut Vec<Found>) {
        let (det, text) = (self.det, &self.text);
        for &(pos, level, asks_name) in labels {
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
                if entry.has(flag::FUNCTION) || entry.has(flag::STOP) {
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
}
