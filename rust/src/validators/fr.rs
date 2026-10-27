//! France : transcription de `gdprguardian/validators/fr.py` (INSEE, DGFiP, ANS, ANTS) / France.

use super::checksums::luhn_ok;
use super::pystr::{self, Is};
use super::{char_len, is_digits, number, slice, strip_separators};

const SEX_DIGITS: &str = "123478";

/// Corse : 2A -> 19, 2B -> 18 / Corsica.
fn corsica(dept: &str) -> Option<&'static str> {
    match dept {
        "2A" => Some("19"),
        "2B" => Some("18"),
        _ => None,
    }
}

/// 13 premiers caractères avec la Corse convertie / first 13 characters, Corsica converted.
fn nir_body(value: &str) -> Option<String> {
    if char_len(value) < 13 || !value.chars().next().is_some_and(|c| SEX_DIGITS.contains(c)) {
        return None;
    }
    let dept = slice(value, 5, 7);
    let mapped = corsica(&dept).map_or(dept.clone(), str::to_string);
    let body = format!("{}{}{}", slice(value, 0, 5), mapped, slice(value, 7, 13));
    is_digits(&body).then_some(body)
}

/// Mois du NIR : 01-12, 13 (inconnu), 20-42 (fictifs), 50-99 / NIR months.
fn nir_month_ok(month: &str) -> bool {
    month.len() == 2 && is_digits(month) && matches!(number(month), 1..=13 | 20..=42 | 50..=99)
}

/// NIR / INS : clé = 97 - (13 chiffres mod 97) / key = 97 - (13 digits mod 97).
pub fn nir(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 15 {
        return None;
    }
    let body = nir_body(&value)?;
    let key = slice(&value, 13, 15);
    if !is_digits(&key) {
        return None;
    }
    (number(&key) == 97 - number(&body) % 97).then_some(value)
}

/// NIR sans clé : structure seule / structure only.
pub fn nir_without_key(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 13 || nir_body(&value).is_none() || !nir_month_ok(&slice(&value, 3, 5)) {
        return None;
    }
    Some(value)
}

/// Numéro fiscal (SPI) : 3 derniers chiffres = 10 premiers mod 511 / last 3 digits = first 10 mod 511.
pub fn spi(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 13 || !is_digits(&value) || !"0123".contains(&value[..1]) {
        return None;
    }
    (number(&value[10..]) == number(&value[..10]) % 511).then_some(value)
}

pub fn siren(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    (char_len(&value) == 9 && value != "000000000" && luhn_ok(&value)).then_some(value)
}

/// SIRET : Luhn, sauf La Poste (356000000…, hors siège) : somme des chiffres multiple de 5.
/// Luhn, except La Poste (356000000…, head office aside): digit sum a multiple of 5.
pub fn siret(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if value.len() != 14 || !is_digits(&value) {
        return None;
    }
    if value.starts_with("356000000") && value != "35600000000048" {
        let total: u32 = value.bytes().map(|b| u32::from(b - b'0')).sum();
        return total.is_multiple_of(5).then_some(value);
    }
    (luhn_ok(&value) && luhn_ok(&value[..9])).then_some(value)
}

const TVA_ALPHABET: &str = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ";

/// TVA intracommunautaire : clé numérique (12 + 3 x (SIREN mod 97)) mod 97, ou clé alphanumérique.
/// EU VAT number: numeric key (12 + 3 x (SIREN mod 97)) mod 97, or alphanumeric key.
pub fn tva(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 13 || !value.starts_with("FR") {
        return None;
    }
    let key = slice(&value, 2, 4);
    let body = slice(&value, 4, 13);
    if !is_digits(&body) {
        return None;
    }
    // Les numéros monégasques (000…) ne sont pas des SIREN / Monaco numbers are not SIREN.
    if &body[..3] != "000" && !luhn_ok(&body) {
        return None;
    }
    let body_value = number(&body) as i64;
    if is_digits(&key) {
        let expected = (12 + 3 * (body_value % 97)) % 97;
        return (number(&key) as i64 == expected).then_some(value);
    }
    let mut chars = key.chars();
    let (k0, k1) = (chars.next()?, chars.next()?);
    let first = TVA_ALPHABET.find(k0)? as i64;
    let second = TVA_ALPHABET.find(k1)? as i64;
    let check = if k0.is_ascii_digit() { first * 24 + second - 10 } else { first * 34 + second - 100 };
    // Division et modulo « à la Python » (plancher) / Python floor division and modulo.
    ((body_value + 1 + check.div_euclid(11)).rem_euclid(11) == check.rem_euclid(11)).then_some(value)
}

/// Lettre du RIB convertie en chiffre / RIB letter converted to a digit.
fn rib_letter(c: char) -> Option<char> {
    const GROUPS: [&str; 10] = ["", "AJ", "BKS", "CLT", "DMU", "ENV", "FOW", "GPX", "HQY", "IRZ"];
    GROUPS.iter().position(|g| g.contains(c)).map(|d| char::from(b'0' + d as u8))
}

/// RIB : clé = 97 - ((89 x banque + 15 x guichet + 3 x compte) mod 97) / RIB key.
pub fn rib(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 23 {
        return None;
    }
    let converted: String = value.chars().map(|c| rib_letter(c).unwrap_or(c)).collect();
    if !is_digits(&converted) {
        return None;
    }
    let bank = number(&converted[..5]);
    let branch = number(&converted[5..10]);
    let account = number(&converted[10..21]);
    let expected = 97 - (89 * bank + 15 * branch + 3 * account) % 97;
    (number(&converted[21..]) == expected).then_some(value)
}

/// RPPS, IMEI… : chiffres + Luhn / digits + Luhn.
pub fn luhn_digits(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    luhn_ok(&value).then_some(value)
}

/// FINESS : 9 caractères ; Luhn hors Corse (contrôle structurel seul) / Luhn except Corsica.
pub fn finess(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 9 {
        return None;
    }
    if corsica(&slice(&value, 0, 2)).is_some() {
        return is_digits(&slice(&value, 2, 9)).then_some(value);
    }
    luhn_ok(&value).then_some(value)
}

/// Plaque SIV AA-123-AA : pas de I/O/U, pas de « SS », pas de « 000 » / no I/O/U, no "SS", no "000".
pub fn siv_plate(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    if char_len(&value) != 7 {
        return None;
    }
    let head = slice(&value, 0, 2);
    let middle = slice(&value, 2, 5);
    let tail = slice(&value, 5, 7);
    if head.chars().chain(tail.chars()).any(|c| matches!(c, 'I' | 'O' | 'U')) || middle == "000" {
        return None;
    }
    (head != "SS" && tail != "SS").then_some(value)
}

/// Identifiant avec au moins une lettre et un chiffre (CNIe…) / at least one letter and one digit.
pub fn alnum_mixed(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    (pystr::any(&value, Is::Digit)? && pystr::any(&value, Is::Alpha)?).then_some(value)
}

/// Date ou plage d'années écrite avec « - », « / » ou « . » (« 2024-03-15 », « 12/03/2024 », « 2024-2025 »).
/// Date or year range written with "-", "/" or "." (`_date_shaped`).
fn date_shaped(value: &str) -> bool {
    let parts: Vec<&str> = value.split(['-', '/', '.']).collect();
    if !parts.iter().all(|p| !p.is_empty() && p.bytes().all(|b| b.is_ascii_digit())) {
        return false;
    }
    let num = |p: &str| p.parse::<u32>().unwrap_or(0);
    let century = |p: &str| p.starts_with("19") || p.starts_with("20");
    match *parts.as_slice() {
        [a, b] => a.len() == 4 && b.len() == 4 && century(a) && century(b),
        [y, m, d] if y.len() == 4 && m.len() <= 2 && d.len() <= 2 => {
            (1..=12).contains(&num(m)) && (1..=31).contains(&num(d))
        }
        [d, m, y] if d.len() <= 2 && m.len() <= 2 && (y.len() == 2 || y.len() == 4) => {
            (1..=31).contains(&num(d)) && (1..=12).contains(&num(m))
        }
        _ => false,
    }
}

/// Valeur après un libellé (« n° client : … ») : au moins un chiffre, jamais une date ni une plage d'années.
/// Value after a label: at least one digit, never a date or a year range.
pub fn contextual_id(candidate: &str) -> Option<String> {
    let value = candidate.trim_matches(|c| matches!(c, ' ' | '.' | '-' | '/'));
    if date_shaped(value) {
        return None;
    }
    if pystr::any(value, Is::Digit)? && char_len(value) >= 4 {
        // 1.0.2 : squelette en majuscules / uppercase skeleton.
        return pystr::upper(&strip_separators(value));
    }
    None
}

/// Champ « Tél : … » : les chiffres d'un seul numéro, sinon les détecteurs ordinaires décident ; « (+ » (forme
/// libre des avis, outre-mer mal formé compris) : 8 à 15 chiffres.
/// Phone field: one phone's worth of digits, else the ordinary detectors decide; "(+" free form: 8 to 15 digits.
pub fn phone_field(candidate: &str) -> Option<String> {
    let digits = pystr::digits(candidate)?;
    let count = char_len(&digits);
    let ok = if candidate.starts_with("(+") {
        // Un seul indicatif, pas de « / » : jamais deux numéros / one country code, no "/": never two numbers.
        (8..=15).contains(&count) && candidate.matches('+').count() == 1 && !candidate.contains('/')
    } else if digits.starts_with("00") {
        (11..=15).contains(&count)
    } else if digits.starts_with('0') {
        count == 10
    } else if digits.starts_with("33") {
        (10..=13).contains(&count)
    } else {
        (9..=13).contains(&count)
    };
    if !ok {
        return None;
    }
    contextual_id(candidate)
}

/// Téléphone français, forme E.164 ; chiffres au sens de `isdigit()`, comme Python.
/// French phone, E.164 form; digits as `isdigit()` sees them, as in Python.
pub fn phone(candidate: &str) -> Option<String> {
    let mut digits = pystr::digits(candidate)?;
    // « (+33) … » (1.0.2) : la parenthèse ouvrante ne cache pas le « + » / an opening bracket does not hide the "+".
    let head = pystr::lstrip(candidate);
    let head = head.strip_prefix('(').map_or(head, pystr::lstrip);
    if digits.starts_with("0033") {
        digits.drain(..4);
    } else if digits.starts_with("33") && head.starts_with('+') {
        digits.drain(..2);
    }
    if digits.starts_with('0') && char_len(&digits) == 10 {
        digits.remove(0);
    } else if char_len(&digits) == 10 && digits.starts_with("00") {
        return None;
    }
    if digits.starts_with('0') && char_len(&digits) == 9 {
        digits.remove(0);
    }
    (char_len(&digits) == 9 && !digits.starts_with('0')).then(|| format!("+33{digits}"))
}

/// +262, +590, +594, +596, +269, +508, +681, +687, +689 : forme E.164 / E.164 form.
pub fn phone_overseas(candidate: &str) -> Option<String> {
    let mut digits = pystr::digits(candidate)?;
    if digits.starts_with("00") {
        digits.drain(..2);
    }
    (9..=12).contains(&char_len(&digits)).then(|| format!("+{digits}"))
}

/// EORI français : FR + SIRET / French EORI: FR + SIRET.
pub fn eori(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    siret(value.strip_prefix("FR")?)?;
    Some(value)
}
