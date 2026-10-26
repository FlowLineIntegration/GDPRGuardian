//! Belgique : transcription de `gdprguardian/validators/be.py` (Registre national, BCE, BIPT) / Belgium.

use super::pystr;
use super::{char_len, is_digits, national_digits, number, strip_separators, zfill};

/// Mois du registre national : 0 à 12 (0 = inconnu) / national register months: 0 to 12 (0 = unknown).
fn nn_month(month: u64) -> bool {
    month <= 12
}

/// Mois d'un numéro BIS : +20 ou +40 / BIS number months: +20 or +40.
fn bis_month(month: u64) -> bool {
    (20..=32).contains(&month) || (40..=52).contains(&month)
}

fn niss_month(month: u64) -> bool {
    nn_month(month) || bis_month(month)
}

/// Clé = 97 - (9 premiers chiffres mod 97), précédés d'un 2 pour les naissances depuis 2000.
/// Key = 97 - (first 9 digits mod 97), prefixed with a 2 for births from 2000 on.
fn check(value: String, months: fn(u64) -> bool) -> Option<String> {
    if value.len() != 11 || !is_digits(&value) {
        return None;
    }
    let (month, day) = (number(&value[2..4]), number(&value[4..6]));
    // Mois inconnu (0, 20, 40) : le jour sert de compteur une fois les rangs épuisés ; sinon jour <= 31.
    // Unknown month (0, 20, 40): the day counts on once serials run out; otherwise day <= 31.
    if !months(month) || (day > 31 && month % 20 != 0) {
        return None;
    }
    let (body, key) = (number(&value[..9]), number(&value[9..]));
    if key == 97 - body % 97 {
        return Some(value);
    }
    // Branche 2000 seulement pour une année déjà atteinte, à l'horloge locale comme Python.
    // 2000s branch only for a year already reached, on the local clock as in Python.
    let born_2000s = key == 97 - (2_000_000_000 + body) % 97 && pystr::year_reached(2000 + number(&value[..2]));
    born_2000s.then_some(value)
}

/// Numéro de registre national (NN, RRN) / national register number.
pub fn nn(candidate: &str) -> Option<String> {
    check(strip_separators(candidate), nn_month)
}

/// Numéro BIS (mois + 20 ou + 40) / BIS number (month + 20 or + 40).
pub fn bis(candidate: &str) -> Option<String> {
    check(strip_separators(candidate), bis_month)
}

/// NISS / INSZ : numéro de registre national ou numéro BIS / national register or BIS number.
pub fn niss(candidate: &str) -> Option<String> {
    check(strip_separators(candidate), niss_month)
}

/// NISS dont un tableur a retiré les zéros de tête (8 à 10 chiffres). Le `zfill(11)` de Python laisse en place
/// tout caractère autre qu'un chiffre, refusé ensuite : seuls les chiffres sont complétés.
/// NISS stripped of leading zeros (8 to 10 digits). Python's `zfill(11)` keeps any non-digit, rejected next:
/// only digits are padded.
pub fn niss_unpadded(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if !(8..=10).contains(&char_len(&value)) || !is_digits(&value) {
        return None;
    }
    check(zfill(&value, 11), niss_month)
}

/// Numéro d'entreprise BCE/KBO, aussi numéro de TVA : 10 chiffres commençant par 0 ou 1, clé = 97 - (8 premiers
/// mod 97) ; formes à 9 chiffres et « BE (0) » acceptées. Enterprise number, also the VAT number: 10 digits
/// starting with 0 or 1, key = 97 - (first 8 mod 97); 9-digit and "BE (0)" forms accepted.
pub fn enterprise_number(candidate: &str) -> Option<String> {
    let upper = pystr::upper(&strip_separators(candidate))?;
    let mut value = upper.strip_prefix("BE").unwrap_or(&upper).replace("(0)", "0");
    if char_len(&value) == 9 {
        value.insert(0, '0');
    }
    if value.len() != 10 || !is_digits(&value) || !value.starts_with(['0', '1']) {
        return None;
    }
    (number(&value[8..]) == 97 - number(&value[..8]) % 97).then_some(value)
}

/// 12 chiffres, clé = 10 premiers mod 97, 97 si le reste est nul / key = first 10 mod 97, 97 for 0.
fn mod97_tail(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 12 || !is_digits(&value) {
        return None;
    }
    let key = match number(&value[..10]) % 97 {
        0 => 97,
        remainder => remainder,
    };
    (number(&value[10..]) == key).then_some(value)
}

/// Numéro de carte eID (xxx-xxxxxxx-yy) / eID card number.
pub fn eid(candidate: &str) -> Option<String> {
    mod97_tail(candidate)
}

/// Ancien numéro de compte bancaire (même clé que l'eID) / legacy bank account (same key as the eID).
pub fn bban(candidate: &str) -> Option<String> {
    mod97_tail(candidate)
}

/// Téléphone belge, forme E.164 : 9 chiffres pour un mobile (4…), 8 sinon, après le 0 ou le +32.
/// Belgian phone, E.164 form: 9 national digits for a mobile (4…), 8 otherwise.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = national_digits(candidate, "32")?;
    // Préfixe interurbain, ou « (0) » écrit après l'indicatif / trunk prefix, or "(0)" after the code.
    let digits = digits.strip_prefix('0').unwrap_or(&digits);
    let first = digits.bytes().next();
    let valid = (digits.len() == 9 && first == Some(b'4')) || (digits.len() == 8 && first != Some(b'0'));
    valid.then(|| format!("+32{digits}"))
}
