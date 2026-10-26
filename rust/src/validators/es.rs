//! Espagne : transcription de `gdprguardian/validators/es.py` (Interior, AEAT, TGSS) / Spain.

use super::checksums::LUHN_DOUBLE;
use super::pystr;
use super::{ascii_digits, char_len, is_digits, number, slice, strip_separators, zfill};

/// Lettre de contrôle = table[nombre mod 23] ; I, Ñ, O, U jamais utilisées / check letter = table[n mod 23].
const DNI_LETTERS: &[u8; 23] = b"TRWAGMYFPDXBNJZSQVHLCKE";
/// Types de CIF, ceux à clé lettre, ceux à clé chiffre / CIF kinds, letter-key kinds, digit-key kinds.
const CIF_KINDS: &str = "ABCDEFGHJNPQRSUVW";
const CIF_LETTER_KINDS: &str = "NPQRSW";
const CIF_DIGIT_KINDS: &str = "ABEH";
/// Clé lettre du CIF, de 0 (J) à 9 (I) / CIF letter key, from 0 (J) to 9 (I).
const CIF_LETTERS: &[u8; 10] = b"JABCDEFGHI";

/// Lettre du DNI pour un nombre / DNI letter for a number.
fn dni_letter(number: u64) -> char {
    char::from(DNI_LETTERS[(number % 23) as usize])
}

/// DNI / NIF de personne physique : 7 ou 8 chiffres + lettre (ancien DNI à 7 chiffres complété par un 0) ;
/// K, L, M + 7 chiffres + lettre. 7 or 8 digits + letter (7-digit DNIs zero-padded); K, L, M + 7 digits + letter.
pub fn dni(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let size = char_len(&value);
    if !(8..=9).contains(&size) {
        return None;
    }
    let prefixed = value.starts_with(['K', 'L', 'M']);
    let digits = slice(&value, usize::from(prefixed), size - 1);
    if !is_digits(&digits) || (prefixed && digits.len() != 7) || number(&digits) == 0 {
        return None;
    }
    if !value.ends_with(dni_letter(number(&digits))) {
        return None;
    }
    Some(if prefixed { value } else { zfill(&value, 9) })
}

/// NIE : X, Y ou Z (-> 0, 1, 2) + 7 chiffres + lettre du DNI ; 8 chiffres pour les anciens X.
/// X, Y or Z (-> 0, 1, 2) + 7 digits + DNI letter; 8 digits for older X numbers.
pub fn nie(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let size = char_len(&value);
    let first = value.chars().next();
    if !(size == 9 || (size == 10 && first == Some('X'))) {
        return None;
    }
    let prefix = match first {
        Some('X') => '0',
        Some('Y') => '1',
        Some('Z') => '2',
        _ => return None,
    };
    let digits = slice(&value, 1, size - 1);
    if !is_digits(&digits) {
        return None;
    }
    value.ends_with(dni_letter(number(&format!("{prefix}{digits}")))).then_some(value)
}

/// Clé du CIF : chiffre de Luhn des 7 chiffres centraux / CIF key: Luhn check digit of the 7 digits.
fn cif_control(digits: &str) -> usize {
    let total: u32 = digits
        .bytes()
        .enumerate()
        .map(|(i, b)| {
            let d = u32::from(b - b'0');
            if i % 2 == 0 {
                LUHN_DOUBLE[d as usize]
            } else {
                d
            }
        })
        .sum();
    ((10 - total % 10) % 10) as usize
}

/// CIF (NIF de personne morale) : type, 7 chiffres, clé chiffre ou lettre (JABCDEFGHI). Lettre exigée pour N, P,
/// Q, R, S, W et les non-résidents (province 00) ; chiffre pour A, B, E, H.
/// Legal-person NIF: kind, 7 digits, digit or letter key. Letter for N, P, Q, R, S, W and non-residents
/// (province 00); digit for A, B, E, H.
pub fn cif(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let kind = value.chars().next()?;
    let digits = slice(&value, 1, 8);
    if char_len(&value) != 9 || !CIF_KINDS.contains(kind) || !is_digits(&digits) {
        return None;
    }
    let control = cif_control(&digits);
    let (letter, digit) = (char::from(CIF_LETTERS[control]), char::from(b'0' + control as u8));
    let last = value.chars().nth(8)?;
    let valid = if CIF_LETTER_KINDS.contains(kind) {
        last == letter
    } else if CIF_DIGIT_KINDS.contains(kind) {
        last == digit
    } else if digits.starts_with("00") {
        last == letter
    } else {
        last == digit || last == letter
    };
    valid.then_some(value)
}

/// NIF d'une personne physique (DNI, K/L/M ou NIE) / natural-person NIF.
pub fn nif_person(candidate: &str) -> Option<String> {
    dni(candidate).or_else(|| nie(candidate))
}

/// TVA ES d'une personne physique (autónomo) : ES + DNI ou NIE / ES VAT of a natural person.
pub fn vat_person(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let body = nif_person(value.strip_prefix("ES")?)?;
    (char_len(&body) == 9).then(|| format!("ES{body}"))
}

/// TVA ES d'une personne morale : ES + CIF / ES VAT of a legal person.
pub fn vat_company(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    cif(value.strip_prefix("ES")?)?;
    Some(value)
}

/// Número de la Seguridad Social : province (2), numéro (8), clé (2) = N mod 97, N officiel (province x 10^7 +
/// numéro sous 10^7) ou concaténé. Province, number, key = N mod 97, official or concatenated N.
pub fn nss(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 12 || !is_digits(&value) || value.starts_with("00") {
        return None;
    }
    let (province, serial, control) = (number(&value[..2]), number(&value[2..10]), number(&value[10..]));
    let concatenated = number(&value[..10]) % 97;
    let official = if serial < 10_000_000 { (province * 10_000_000 + serial) % 97 } else { concatenated };
    (control == official || control == concatenated).then_some(value)
}

/// Numéro national : 9 chiffres, 6/7 mobiles, 8/9 fixes et services -> E.164 / 9 digits -> E.164.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = ascii_digits(candidate);
    (digits.len() == 9 && matches!(digits.as_bytes()[0], b'6'..=b'9')).then(|| format!("+34{digits}"))
}
