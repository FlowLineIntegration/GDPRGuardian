//! Italie : transcription de `gdprguardian/validators/it.py` (DM 23/12/1976, DPR 633/1972) / Italy.

use super::checksums::luhn_ok;
use super::pystr;
use super::{ascii_digits, char_len, is_digits, number, strip_separators};

/// Lettres des mois du codice fiscale / codice fiscale month letters.
const MONTHS: &[u8; 12] = b"ABCDEHLMPRST";
/// Jours au plus par mois, 29 en février (année inconnue) / maximum days per month, 29 in February.
const MONTH_DAYS: [u64; 12] = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
/// Omocodia : chiffres remplacés par LMNPQRSTUV / homocody: digits replaced by LMNPQRSTUV.
const HOMOCODY: &[u8; 10] = b"LMNPQRSTUV";
/// Rangs impairs (1re, 3e…) : table officielle, chiffres = lettres A-J / odd positions: official table.
const ODD_TABLE: [u32; 26] =
    [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23];

/// Rang d'un caractère : chiffre 0-9, ou lettre A=0…Z=25 / a character's rank: digit 0-9, or letter A=0..Z=25.
fn rank(b: u8) -> u32 {
    u32::from(if b.is_ascii_digit() { b - b'0' } else { b - b'A' })
}

/// Caractère de contrôle des 15 premiers caractères / check character of the first 15 characters.
fn codice_fiscale_check(body: &[u8]) -> u8 {
    let total: u32 =
        body.iter().enumerate().map(|(i, &b)| if i % 2 == 0 { ODD_TABLE[rank(b) as usize] } else { rank(b) }).sum();
    b'A' + (total % 26) as u8
}

/// `[A-Z]{6}[0-9LMNP-V]{2}[ABCDEHLMPRST][0-9LMNP-V]{2}[A-Z][0-9LMNP-V]{3}[A-Z]`, en entier / full match.
fn codice_fiscale_shape(value: &[u8]) -> bool {
    let number_like = |b: u8| b.is_ascii_digit() || HOMOCODY.contains(&b);
    value.len() == 16
        && value.iter().enumerate().all(|(i, &b)| match i {
            0..=5 | 11 | 15 => b.is_ascii_uppercase(),
            8 => MONTHS.contains(&b),
            _ => number_like(b),
        })
}

/// Chiffre d'une position numérique, omocodia défaite / digit of a numeric position, homocody undone.
fn undo_homocody(b: u8) -> u64 {
    HOMOCODY.iter().position(|&h| h == b).map_or(u64::from(b.wrapping_sub(b'0')), |digit| digit as u64)
}

/// Codice fiscale d'une personne : 16 caractères, date (jour +40 pour les femmes), clé mod 26 ; omocodes acceptés.
/// Personal tax code: 16 characters, date (day +40 for women), mod-26 check letter; homocodes accepted.
pub fn codice_fiscale(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let b = value.as_bytes();
    if char_len(&value) != 16 || !codice_fiscale_shape(b) {
        return None;
    }
    let day = (10 * undo_homocody(b[9]) + undo_homocody(b[10])) % 40;
    let month = MONTHS.iter().position(|&m| m == b[8])?;
    if !(1..=MONTH_DAYS[month]).contains(&day) {
        return None;
    }
    (codice_fiscale_check(&b[..15]) == b[15]).then_some(value)
}

/// Bureaux provinciaux de la partita IVA : 001-100, 120-121, 888, 999 / VAT number office codes.
fn office_ok(code: &str) -> bool {
    matches!(number(code), 1..=100 | 120 | 121 | 888 | 999)
}

/// Partita IVA (ou codice fiscale numérique) : 11 chiffres, bureau, Luhn ; sans bureau pour 8… et 9….
/// VAT number (or numeric tax code): 11 digits, office, Luhn; no office code for 8… and 9….
pub fn partita_iva(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 11 || !is_digits(&value) || value.starts_with("0000000") {
        return None;
    }
    if !value.starts_with(['8', '9']) && !office_ok(&value[7..10]) {
        return None;
    }
    luhn_ok(&value).then_some(value)
}

/// TVA intracommunautaire : IT + partita IVA / EU VAT number: IT + partita IVA.
pub fn vat(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    partita_iva(value.strip_prefix("IT")?)?;
    Some(value)
}

/// Fixe 0x (6 à 11 chiffres, 0 conservé) ou mobile 3x (9-10 chiffres) -> E.164.
/// Landline 0x (6 to 11 digits, the 0 is kept) or mobile 3x (9-10 digits) -> E.164.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = ascii_digits(candidate);
    let b = digits.as_bytes();
    if b.first() == Some(&b'0') && !matches!(b.get(1), None | Some(b'0')) && (6..=11).contains(&b.len()) {
        return Some(format!("+39{digits}"));
    }
    phone_mobile(&digits)
}

/// Mobile : 3 puis 8 ou 9 chiffres / mobile: 3 then 8 or 9 digits.
pub fn phone_mobile(candidate: &str) -> Option<String> {
    let digits = ascii_digits(candidate);
    let b = digits.as_bytes();
    (b.first() == Some(&b'3') && b.get(1) != Some(&b'0') && (9..=10).contains(&b.len())).then(|| format!("+39{digits}"))
}
