//! Suisse : transcription de `gdprguardian/validators/ch.py` (OFAS/ZAS, OFS, OFCOM) / Switzerland.

use super::pystr;
use super::{is_digits, national_digits, number, strip_separators, weighted_sum};

/// EAN-13 : poids 1, 3, 1, 3… depuis la gauche, clé comprise / weights 1, 3, 1, 3… from the left, key included.
const EAN13_WEIGHTS: [i64; 13] = [1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1];
const UID_WEIGHTS: [i64; 8] = [5, 4, 3, 2, 7, 6, 5, 4];
/// Suffixes TVA de l'IDE, dans l'ordre de Python : allemand, français, italien, romanche / UID VAT suffixes.
const VAT_SUFFIXES: [&str; 4] = ["MWST", "TVA", "IVA", "TPV"];

/// Numéro AVS/AHV à 13 chiffres : 756, 9 chiffres, clé EAN-13 / AHVN13: 756, 9 digits, EAN-13 check digit.
pub fn avs(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 13 || !value.starts_with("756") || !is_digits(&value) {
        return None;
    }
    (weighted_sum(&value, &EAN13_WEIGHTS) % 10 == 0).then_some(value)
}

/// IDE/UID (CHE-123.456.789), aussi numéro de TVA avec MWST/TVA/IVA/TPV ; forme canonique CHE + 9 chiffres.
/// Clé = 11 - (somme pondérée mod 11), 10 jamais attribué. Business identification number, also the VAT number
/// with a language suffix; key = 11 - weighted sum mod 11, 10 never issued.
pub fn uid(candidate: &str) -> Option<String> {
    let mut value = pystr::upper(&strip_separators(candidate))?;
    if let Some(suffix) = VAT_SUFFIXES.iter().find(|suffix| value.ends_with(*suffix)) {
        value.truncate(value.len() - suffix.len());
    }
    let value = value.strip_prefix("CHE").unwrap_or(&value);
    if value.len() != 9 || !is_digits(value) {
        return None;
    }
    let key = (11 - weighted_sum(value, &UID_WEIGHTS) % 11) % 11;
    (key == number(&value[8..]) as i64).then(|| format!("CHE{value}"))
}

/// Téléphone suisse, forme E.164 : 9 chiffres après le 0 ou le +41 / Swiss phone, 9 national digits.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = national_digits(candidate, "41")?;
    let digits = digits.strip_prefix('0').unwrap_or(&digits);
    (digits.len() == 9 && matches!(digits.as_bytes()[0], b'2'..=b'9')).then(|| format!("+41{digits}"))
}
