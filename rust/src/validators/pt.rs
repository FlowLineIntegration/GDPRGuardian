//! Portugal : transcription de `gdprguardian/validators/pt.py` (AT, Segurança Social, AMA) / Portugal.

use super::pystr;
use super::{ascii_digits, char_len, is_digits, number, strip_separators, weighted_sum, zfill};

/// NIF : clé = 11 - (Σ d_i × (9 - i) mod 11), 10 et 11 donnent 0 / check = 11 - weighted sum mod 11.
const NIF_WEIGHTS: [i64; 8] = [9, 8, 7, 6, 5, 4, 3, 2];
/// NISS : poids 29…2, clé = 9 - (somme mod 10) / NISS weights, check digit = 9 - (sum mod 10).
const NISS_WEIGHTS: [i64; 10] = [29, 23, 19, 17, 13, 11, 7, 5, 3, 2];
/// Fixes 2x, mobiles 91/92/93/96, nomades 30, services / landlines, mobiles, nomadic, services.
const PHONE_PREFIXES: [&str; 13] = ["2", "91", "92", "93", "96", "30", "707", "708", "760", "761", "762", "800", "808"];

/// NIF / NIPC : 9 chiffres, premier non nul, clé mod 11 / 9 digits, first non-zero, mod-11 check digit.
pub fn nif(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 9 || !is_digits(&value) || value.starts_with('0') {
        return None;
    }
    let total = weighted_sum(&value[..8], &NIF_WEIGHTS);
    ((11 - total % 11) % 11 % 10 == number(&value[8..]) as i64).then_some(value)
}

/// Personnes morales (5) et organismes publics (6) / legal persons (5) and public bodies (6).
fn collective(value: &str) -> bool {
    value.starts_with(['5', '6'])
}

/// NIF d'une personne physique ou d'un cas assimilé (préfixes autres que 5 et 6) / natural persons.
pub fn nif_person(candidate: &str) -> Option<String> {
    nif(candidate).filter(|value| !collective(value))
}

/// NIPC d'une personne morale (5) ou d'un organisme public (6) / legal persons and public bodies.
pub fn nipc(candidate: &str) -> Option<String> {
    nif(candidate).filter(|value| collective(value))
}

/// TVA PT d'un entrepreneur individuel : PT + NIF de la personne / PT VAT of a sole trader: PT + NIF.
pub fn vat_person(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    nif_person(value.strip_prefix("PT")?)?;
    Some(value)
}

/// TVA PT d'une personne morale : PT + NIPC / PT VAT of a legal person: PT + NIPC.
pub fn vat_company(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    nipc(value.strip_prefix("PT")?)?;
    Some(value)
}

/// NISS : 11 chiffres, premier 1 ou 2, clé = 9 - (Σ poids mod 10) / 11 digits, first 1 or 2.
pub fn niss(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 11 || !is_digits(&value) || !value.starts_with(['1', '2']) {
        return None;
    }
    let total = weighted_sum(&value[..10], &NISS_WEIGHTS);
    (9 - total % 10 == number(&value[10..]) as i64).then_some(value)
}

/// Cartão de Cidadão : NIC (8), clé, version (2), clé finale ; Luhn en base 36 depuis la droite (un caractère
/// sur deux doublé, moins 9 au-delà de 9). Citizen card number; base-36 Luhn from the right.
pub fn cc(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 12 || !value.is_ascii() {
        return None;
    }
    let b = value.as_bytes();
    if !(is_digits(&value[..9]) && b[11].is_ascii_digit()) || !b[9..11].iter().all(u8::is_ascii_alphanumeric) {
        return None;
    }
    let total: u32 = b
        .iter()
        .rev()
        .enumerate()
        .map(|(position, &c)| {
            // `int(char, 36)` d'un caractère ASCII alphanumérique / of an ASCII alphanumeric character.
            let number = char::from(c).to_digit(36).unwrap_or(0);
            // Seul un nombre doublé perd 9 (une lettre non doublée garde 10 à 35) / only a doubled number loses 9.
            match (position % 2 == 1, 2 * number) {
                (true, doubled) if doubled > 9 => doubled - 9,
                (true, doubled) => doubled,
                (false, _) => number,
            }
        })
        .sum();
    total.is_multiple_of(10).then_some(value)
}

/// Número de identificação civil (ex-BI) : 7-8 chiffres, clé facultative ; valeur canonique sans clé.
/// Civil identification number (former BI): 7-8 digits, optional check digit; canonical value without it.
pub fn nic(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if !(7..=9).contains(&value.len()) || !is_digits(&value) {
        return None;
    }
    Some(if value.len() == 9 { value[..8].to_string() } else { zfill(&value, 8) })
}

/// Número de utente du SNS : 9 chiffres, sans clé publiée / 9 digits, no published check.
pub fn sns(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    (value.len() == 9 && is_digits(&value)).then_some(value)
}

/// Numéro national : 9 chiffres, fixes 2x, mobiles 91/92/93/96, nomades 30, services -> E.164.
/// National number: 9 digits, landlines 2x, mobiles 91/92/93/96, nomadic 30, services -> E.164.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = ascii_digits(candidate);
    let prefixed = PHONE_PREFIXES.iter().any(|prefix| digits.starts_with(prefix));
    (digits.len() == 9 && prefixed).then(|| format!("+351{digits}"))
}
