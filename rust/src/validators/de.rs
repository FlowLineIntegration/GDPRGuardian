//! Allemagne : transcription de `gdprguardian/validators/de.py` (BZSt, VKVV, FeV, ICAO 9303) / Germany.

use super::checksums::{icao_check_digit, iso7064_mod11_10_ok};
use super::pystr;
use super::{ascii_digits, char_len, is_digits, number, strip_separators};

/// Préfixe Land des formes fédérales à 12 et 13 chiffres / Land prefix of the 12- and 13-digit federal forms.
const STNR_LAENDER: [&str; 16] =
    ["10", "11", "21", "22", "23", "24", "26", "27", "28", "30", "31", "32", "40", "41", "5", "9"];
/// Caractères des numéros de document (ni voyelles ni B, D, Q, S) / document number characters.
const DOCUMENT_ALPHABET: &str = "0123456789CFGHJKLMNPRTVWXYZ";
/// Poids des clés RVNR, KVNR et du permis de conduire / RVNR, KVNR and driving licence key weights.
const RVNR_WEIGHTS: [u32; 12] = [2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1];
const KVNR_WEIGHTS: [u32; 10] = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2];
const LICENSE_WEIGHTS: [u32; 9] = [9, 8, 7, 6, 5, 4, 3, 2, 1];

/// Somme des sommes de chiffres des produits, modulo 10 / sum of the products' digit sums, mod 10.
fn cross_sum_mod10(digits: &str, weights: &[u32]) -> u32 {
    let total: u32 = digits
        .bytes()
        .zip(weights)
        .map(|(b, w)| {
            let product = u32::from(b - b'0') * w;
            product / 10 + product % 10
        })
        .sum();
    total % 10
}

/// Rang alphabétique sur deux chiffres (A=01 ... Z=26) / alphabet rank on two digits.
fn letter_code(letter: u8) -> String {
    format!("{:02}", letter - b'A' + 1)
}

/// Steuer-ID (IdNr, § 139b AO) : 11 chiffres, ISO 7064 MOD 11,10 et règle de répétition du BZSt : parmi les 10
/// premiers chiffres, une seule valeur se répète, 2 ou 3 fois, jamais 3 fois de suite.
/// 11 digits, ISO 7064 MOD 11,10 and the BZSt repetition rule: among the first 10 digits one value repeats,
/// twice or three times, never three times in a row.
pub fn steuer_id(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 11 || !is_digits(&value) || value.starts_with('0') {
        return None;
    }
    let body = &value.as_bytes()[..10];
    let mut counts = [0u8; 10];
    for &b in body {
        counts[usize::from(b - b'0')] += 1;
    }
    // 9 valeurs distinctes = un doublon ; 8 = un triplet ou deux doublons / 9 = one pair; 8 = one triple or two pairs.
    match counts.iter().filter(|&&count| count > 0).count() {
        9 => {}
        8 => {
            let in_a_row = body.windows(3).any(|w| w[0] == w[1] && w[1] == w[2]);
            if !counts.contains(&3) || in_a_row {
                return None;
            }
        }
        _ => return None,
    }
    iso7064_mod11_10_ok(&value).then_some(value)
}

/// Steuernummer : forme régionale (10-11 chiffres) ou fédérale (12 chiffres, ou 13 avec un 0 en 5e position)
/// derrière un préfixe de Land. Regional form (10-11 digits) or federal form (12, or 13 with a 0 as 5th digit).
pub fn steuernummer(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if !is_digits(&value) {
        return None;
    }
    match value.len() {
        12 | 13 => {
            let land = STNR_LAENDER.iter().any(|prefix| value.starts_with(prefix));
            (land && (value.len() == 12 || value.as_bytes()[4] == b'0')).then_some(value)
        }
        10 | 11 => Some(value),
        _ => None,
    }
}

/// Rentenversicherungsnummer (VKVV § 2) : zone, JJMMAA, initiale, série, clé.
/// Pension insurance number: area, DDMMYY, initial, serial, check digit.
pub fn rvnr(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 12 || !value.is_ascii() || !(is_digits(&value[..8]) && is_digits(&value[9..])) {
        return None;
    }
    let letter = value.as_bytes()[8];
    if !letter.is_ascii_uppercase() {
        return None;
    }
    // Jour +50 toléré (numéros de série épuisés), 00 pour une date inconnue / day +50 and 00 tolerated.
    let (day, month) = (number(&value[2..4]), number(&value[4..6]));
    if month > 12 || !(day <= 31 || (50..=81).contains(&day)) {
        return None;
    }
    let digits = format!("{}{}{}", &value[..8], letter_code(letter), &value[9..11]);
    (u64::from(cross_sum_mod10(&digits, &RVNR_WEIGHTS)) == number(&value[11..])).then_some(value)
}

/// Krankenversichertennummer (§ 290 SGB V), partie fixe : lettre, 8 chiffres, clé.
/// Health insurance number, fixed part: letter, 8 digits, check digit.
pub fn kvnr(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 10
        || !value.is_ascii()
        || !(value.as_bytes()[0].is_ascii_uppercase() && is_digits(&value[1..]))
    {
        return None;
    }
    let digits = format!("{}{}", letter_code(value.as_bytes()[0]), &value[1..9]);
    (u64::from(cross_sum_mod10(&digits, &KVNR_WEIGHTS)) == number(&value[9..])).then_some(value)
}

/// Personalausweis / Reisepass : 9 caractères (chiffres et CFGHJKLMNPRTVWXYZ), clé ICAO facultative en 10e
/// caractère ; valeur canonique sur 9 caractères. 9 characters, optional ICAO check digit as a 10th character.
pub fn id_document(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if !matches!(char_len(&value), 9 | 10) || !value.chars().all(|c| DOCUMENT_ALPHABET.contains(c)) {
        return None;
    }
    if value.len() == 10 {
        let key = value.as_bytes()[9];
        if !key.is_ascii_digit() || icao_check_digit(&value[..9]) != u32::from(key - b'0') {
            return None;
        }
        return Some(value[..9].to_string());
    }
    Some(value)
}

/// Führerscheinnummer (FeV Anlage 8) : clé A=10…Z=35, poids 9…1, mod 11, 10 s'écrit X ; valeur canonique sans
/// le numéro d'exemplaire (11e caractère). Key A=10..Z=35, weights 9..1, mod 11, 10 written X; canonical value
/// without the issue number (11th character).
pub fn fuehrerschein(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 11 || !value.bytes().all(|b| b.is_ascii_alphanumeric()) {
        return None;
    }
    // `int(c, 36)` d'un caractère ASCII alphanumérique / of an ASCII alphanumeric character.
    let base36 = |b: u8| char::from(b).to_digit(36).unwrap_or(0);
    let remainder = value.bytes().zip(LICENSE_WEIGHTS).map(|(b, w)| base36(b) * w).sum::<u32>() % 11;
    let key = if remainder == 10 { b'X' } else { b'0' + remainder as u8 };
    (value.as_bytes()[9] == key).then(|| value[..10].to_string())
}

/// USt-IdNr : DE + 9 chiffres (premier non nul), ISO 7064 MOD 11,10 / DE + 9 digits, MOD 11,10.
pub fn ust_idnr(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 11 {
        return None;
    }
    let digits = value.strip_prefix("DE")?;
    if !is_digits(digits) || digits.starts_with('0') || !iso7064_mod11_10_ok(digits) {
        return None;
    }
    Some(value)
}

/// Numéro national (0 + indicatif + abonné, 6 à 11 chiffres utiles) -> E.164.
/// National number (trunk 0 + area code + subscriber, 6 to 11 significant digits) -> E.164.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = ascii_digits(candidate);
    let b = digits.as_bytes();
    if b.first() != Some(&b'0') || matches!(b.get(1), None | Some(b'0')) || !(7..=12).contains(&b.len()) {
        return None;
    }
    Some(format!("+49{}", &digits[1..]))
}

/// Mobile 015x, 016x, 017x : 10 ou 11 chiffres utiles / mobile ranges, 10 or 11 significant digits.
pub fn phone_mobile(candidate: &str) -> Option<String> {
    phone(candidate).filter(|value| matches!(&value[3..5], "15" | "16" | "17") && matches!(value.len(), 13 | 14))
}
