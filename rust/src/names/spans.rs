//! Zone et forme canonique d'une suite retenue : `_span`, `_canonical`.
//!
//! Span and canonical form of an accepted run. La forme propagée est rendue telle quelle ; Python lui
//! applique `str.title()` si elle est en capitales (table de casse complète de Python). The propagated
//! form is returned as is; Python applies `str.title()` when it is all caps.

use std::collections::HashSet;

use super::cues::Cues;
use super::lexicon::{Kind, AMB_ENTITY, AMB_NONE};
use super::patterns;
use super::tokens::Run;
use super::{Doc, Element, Found, Keys, GIVEN_ALONE_MIN, MEDIUM};

impl Doc<'_> {
    /// `_last_name` : dernier mot du texte d'un élément, coupure de ligne recollée (`_unwrap(...).split()[-1]`) ;
    /// un nom à particule fusionné (« Le Verger ») est gardé entier. Last word of an element's text; a merged particle
    /// surname is kept whole. Un élément contient toujours des lettres / an element always holds letters.
    fn last_word(&self, e: &Element, keys: &Keys) -> String {
        let name = patterns::unwrap(&self.text[e.start..e.end]);
        if e.kind == Kind::Unknown && keys.get(e.key).contains(&' ') {
            return name.iter().collect();
        }
        self.det.chars.split_last(&name).map_or_else(String::new, |word| word.iter().collect())
    }

    /// `_canonical` : « Prénom Nom » sans particules ni prénoms intermédiaires, pour la coréférence.
    /// "Given Surname" without particles or middle names, for coreference.
    fn canonical<'e>(&self, elements: &'e [Element], keys: &Keys) -> Option<(String, &'e Element, &'e Element)> {
        let parts: Vec<&Element> =
            elements.iter().filter(|e| matches!(e.kind, Kind::Name | Kind::Unknown | Kind::Initial)).collect();
        if let [only] = parts[..] {
            return Some((self.last_word(only, keys), only, only));
        }
        let caps = parts.iter().rev().find(|e| e.caps && e.kind != Kind::Initial);
        let mixed = parts.iter().find(|e| !e.caps);
        let (given, surname) = match (mixed, caps) {
            (Some(&given), Some(&surname)) => (given, surname),
            _ => {
                let (first, last) = (*parts.first()?, *parts.last()?);
                // « Blanchard Olivier », « Tirole Jean » : ordre Nom Prénom / surname-first order.
                let bias = |e: &Element| e.given() as i16 - e.surname() as i16;
                if parts.len() == 2 && last.kind == Kind::Name && bias(last) > bias(first) {
                    (last, first)
                } else {
                    (first, last)
                }
            }
        };
        let mut value: String = patterns::unwrap(&self.text[given.start..given.end]).iter().collect();
        if given.kind == Kind::Initial {
            value.push('.');
        }
        value.push(' ');
        value.push_str(&self.last_word(surname, keys));
        Some((value, given, surname))
    }

    /// `_span` : zone, valeur canonique, forme propagée et drapeau de propagation d'une suite retenue.
    /// Span, canonical value, propagated form and propagation flag of an accepted run.
    pub(super) fn span(
        &self,
        run: &Run,
        all: &[Element],
        cues: &Cues,
        eponyms: &HashSet<Vec<char>>,
        keys: &Keys,
    ) -> Option<Found> {
        let mut elements = &all[run.from..run.to];
        if elements.first()?.kind == Kind::Particle && run.evidence < MEDIUM {
            elements = &elements[1..]; // article en tête (« Le Monde ») / leading article
        }
        while elements.last().is_some_and(|e| e.kind == Kind::Particle) {
            elements = &elements[..elements.len() - 1];
        }
        let (first, last) = (elements.first()?, elements.last()?);
        let mut start = first.start;
        if first.given() == 0 {
            if let Some(&particle) = cues.particle_from.get(&start) {
                start = particle; // « M. de Villepin » : la particule fait partie du nom / part of the name
            }
        }
        let mut end = last.end;
        if self.text.get(end) == Some(&'.') && last.kind == Kind::Initial {
            end += 1; // « Jean D. »
        }
        let (value, given, surname) = self.canonical(elements, keys)?;
        let names: Vec<&Element> = elements.iter().filter(|e| e.kind.is_name()).collect();
        let eponym = |e: &Element| eponyms.contains(keys.get(e.key));
        let safe_single =
            matches!(names[..], [only] if (only.kind == Kind::Unknown || only.amb() == AMB_NONE) && !eponym(only));
        // Nom seul propagé s'il est sûr ; un nom inconnu seulement à côté d'un prénom fréquent (« Jean
        // Zelensky », pas « Breizh Izel »). Surname form propagated when safe; an unknown one only next to a
        // frequent given name.
        let known_surname = surname.kind == Kind::Name
            || (given.kind == Kind::Name && given.given() >= GIVEN_ALONE_MIN && given.amb() != AMB_ENTITY);
        let form = (names.len() >= 2
            && surname.amb() == AMB_NONE
            && surname.key.len() >= 3
            && !eponym(surname)
            && known_surname)
            .then(|| self.last_word(surname, keys));
        Some(Found { start, end, value, score: run.score, propagate: names.len() >= 2 || safe_single, form })
    }
}
