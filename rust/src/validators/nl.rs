//! Pays-Bas : transcription de `gdprguardian/validators/nl.py` (Logius, Belastingdienst, PostNL) / Netherlands.

use super::checksums::mod97_10_ok;
use super::pystr;
use super::{ascii_digits, char_len, is_digits, slice, strip_separators, weighted_sum, zfill};

/// 11-proef : 9a + 8b + … + 2h - i ≡ 0 (mod 11) / BSN and RSIN eleven test.
const BSN_WEIGHTS: [i64; 9] = [9, 8, 7, 6, 5, 4, 3, 2, -1];

/// 11-proef sur 9 chiffres ASCII / eleven test on 9 ASCII digits.
fn eleven_test(digits: &str) -> bool {
    weighted_sum(digits, &BSN_WEIGHTS).rem_euclid(11) == 0
}

/// Burgerservicenummer : 9 chiffres (8 si Excel a retiré le 0 initial), 11-proef.
/// Citizen service number: 9 digits (8 when Excel dropped the leading 0), eleven test.
pub fn bsn(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if !(8..=9).contains(&value.len()) || !is_digits(&value) {
        return None;
    }
    let value = zfill(&value, 9);
    (value != "000000000" && eleven_test(&value)).then_some(value)
}

/// NL + 9 chiffres + B + 2 chiffres, ni zéros seuls / NL + 9 digits + B + 2 digits, not all zeros.
fn btw_shape(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 14 || !value.starts_with("NL") || value.chars().nth(11) != Some('B') {
        return None;
    }
    let (digits, suffix) = (slice(&value, 2, 11), slice(&value, 12, 14));
    if !(is_digits(&digits) && is_digits(&suffix)) || digits == "000000000" || suffix == "00" {
        return None;
    }
    Some(value)
}

/// Btw-id : MOD 97-10 (depuis 2020) ou 11-proef (avant) / VAT id: MOD 97-10 (since 2020) or eleven test.
pub fn btw(candidate: &str) -> Option<String> {
    btw_shape(candidate).filter(|value| mod97_10_ok(value) || eleven_test(&value[2..11]))
}

/// Btw-id MOD 97-10 : réservé depuis 2020 aux eenmanszaken, donc à une personne physique.
/// MOD 97-10 VAT id: issued since 2020 to sole traders only, hence to a natural person.
pub fn btw_person(candidate: &str) -> Option<String> {
    btw_shape(candidate).filter(|value| mod97_10_ok(value))
}

/// Btw-nummer à 11-proef (RSIN d'une personne morale, ou ancien numéro fondé sur le BSN).
/// Eleven-test VAT number (a legal entity's RSIN, or an older BSN-based number).
pub fn btw_company(candidate: &str) -> Option<String> {
    btw_shape(candidate).filter(|value| !mod97_10_ok(value) && eleven_test(&value[2..11]))
}

/// KvK-nummer : 8 chiffres, sans clé / Chamber of Commerce number: 8 digits, no check digit.
pub fn kvk(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    (value.len() == 8 && is_digits(&value)).then_some(value)
}

/// Paspoort / identiteitskaart : `[A-NP-Z]{2}[A-NP-Z0-9]{6}[0-9]` en entier ; jamais la lettre O.
/// Passport / ID card number, full match; the letter O is never used.
pub fn document_number(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let b = value.as_bytes();
    let letter = |c: u8| c.is_ascii_uppercase() && c != b'O';
    let valid = b.len() == 9
        && b[..2].iter().all(|&c| letter(c))
        && b[2..8].iter().all(|&c| letter(c) || c.is_ascii_digit())
        && b[8].is_ascii_digit();
    valid.then_some(value)
}

/// Postcode : 4 chiffres (sans 0 initial) + 2 lettres, jamais SA, SD ni SS -> « 1234 AB ».
/// Postcode: 4 digits (no leading 0) + 2 letters, never SA, SD or SS -> "1234 AB".
pub fn postcode(candidate: &str) -> Option<String> {
    let value = pystr::upper(&candidate.replace(' ', ""))?;
    if char_len(&value) != 6 || value.starts_with('0') || !is_digits(&slice(&value, 0, 4)) {
        return None;
    }
    let letters = slice(&value, 4, 6);
    let valid = letters.bytes().all(|b| b.is_ascii_uppercase()) && !matches!(letters.as_str(), "SA" | "SD" | "SS");
    valid.then(|| format!("{} {letters}", &value[..4]))
}

/// Numéro national : 0 + 9 chiffres -> E.164 / national number: 0 + 9 digits -> E.164.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = ascii_digits(candidate);
    let b = digits.as_bytes();
    if b.len() != 10 || b[0] != b'0' || b[1] == b'0' {
        return None;
    }
    Some(format!("+31{}", &digits[1..]))
}

/// Mobile 06 + 8 chiffres / mobile 06 + 8 digits.
pub fn phone_mobile(candidate: &str) -> Option<String> {
    phone(candidate).filter(|value| value.as_bytes()[3] == b'6')
}
