//! Luxembourg : transcription de `gdprguardian/validators/lu.py` (loi du 19 juin 2013, LBR, ILR) / Luxembourg.

use super::checksums::{luhn_ok, verhoeff_ok};
use super::pystr;
use super::{is_digits, national_digits, number, strip_separators};

/// AAAAMMJJ plausible, de 1800 à l'année en cours ; 00 toléré pour un mois ou un jour inconnu. L'année en cours,
/// seule à pouvoir interroger l'interpréteur, est vérifiée en dernier.
/// Plausible YYYYMMDD, from 1800 to the current year; 00 tolerated for an unknown month or day. The current
/// year, the only check that may ask the interpreter, comes last.
fn plausible_birth_date(value: &str) -> bool {
    let (year, month, day) = (number(&value[..4]), number(&value[4..6]), number(&value[6..8]));
    year >= 1800 && month <= 12 && day <= 31 && pystr::year_reached(year)
}

/// Matricule national (13 chiffres) : AAAAMMJJ, rang (3), clé Luhn, clé Verhoeff, toutes deux sur les
/// 11 premiers chiffres. National identification number: YYYYMMDD, serial (3), Luhn and Verhoeff digits, both
/// over the first 11 digits.
pub fn matricule(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 13 || !is_digits(&value) {
        return None;
    }
    let payload = &value[..11];
    let keys = luhn_ok(&format!("{payload}{}", &value[11..12])) && verhoeff_ok(&format!("{payload}{}", &value[12..]));
    (keys && plausible_birth_date(&value)).then_some(value)
}

/// Ancien matricule à 11 chiffres, sans clé connue : structure seule / legacy 11-digit matricule, structure only.
pub fn matricule_legacy(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    (value.len() == 11 && is_digits(&value) && plausible_birth_date(&value)).then_some(value)
}

/// TVA : LU + 8 chiffres, les 2 derniers = 6 premiers mod 89 / last 2 digits = first 6 mod 89.
pub fn tva(candidate: &str) -> Option<String> {
    let upper = pystr::upper(&strip_separators(candidate))?;
    let value = upper.strip_prefix("LU").unwrap_or(&upper);
    if value.len() != 8 || !is_digits(value) {
        return None;
    }
    (number(&value[6..]) == number(&value[..6]) % 89).then(|| format!("LU{value}"))
}

/// Numéro RCS : lettre de section A à O + 1 à 6 chiffres, ex. B123456 / section letter + 1 to 6 digits.
pub fn rcs(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let mut chars = value.chars();
    let section = chars.next()?;
    let digits = chars.as_str();
    let valid =
        ('A'..='O').contains(&section) && (1..=6).contains(&digits.len()) && digits.bytes().all(|b| b.is_ascii_digit());
    valid.then_some(value)
}

/// Téléphone luxembourgeois, forme E.164 : mobile 6xx xxx xxx, fixe 6 à 8 chiffres, sans préfixe 0.
/// Luxembourg phone, E.164 form: 9-digit mobile (6…), 6 to 8-digit landline, no trunk prefix.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = national_digits(candidate, "352")?;
    let b = digits.as_bytes();
    let valid = (b.len() == 9 && b[0] == b'6') || ((6..=8).contains(&b.len()) && b"2345789".contains(&b[0]));
    valid.then(|| format!("+352{digits}"))
}
