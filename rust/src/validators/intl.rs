//! International : transcription de `gdprguardian/validators/intl.py` / international validators.

use std::borrow::Cow;

use super::checksums::{base58check_ok, bech32_ok, eip55_ok, luhn_ok, mod97_10_ok};
use super::pystr::{self, Is};
use super::{char_len, is_digits, is_leap, number, slice, strip_separators};

/// Longueur IBAN par pays (registre SWIFT), comme `intl.IBAN_LENGTHS` / IBAN length per country.
fn iban_length(country: &str) -> Option<usize> {
    #[rustfmt::skip]
    const TABLE: &[(&str, usize)] = &[
        ("AD", 24), ("AE", 23), ("AL", 28), ("AT", 20), ("AZ", 28), ("BA", 20), ("BE", 16), ("BG", 22),
        ("BH", 22), ("BI", 27), ("BR", 29), ("BY", 28), ("CH", 21), ("CR", 22), ("CY", 28), ("CZ", 24),
        ("DE", 22), ("DJ", 27), ("DK", 18), ("DO", 28), ("EE", 20), ("EG", 29), ("ES", 24), ("FI", 18),
        ("FK", 18), ("FO", 18), ("FR", 27), ("GB", 22), ("GE", 22), ("GI", 23), ("GL", 18), ("GR", 27),
        ("GT", 28), ("HN", 28), ("HR", 21), ("HU", 28), ("IE", 22), ("IL", 23), ("IQ", 23), ("IS", 26),
        ("IT", 27), ("JO", 30), ("KW", 30), ("KZ", 20), ("LB", 28), ("LC", 32), ("LI", 21), ("LT", 20),
        ("LU", 20), ("LV", 21), ("LY", 25), ("MC", 27), ("MD", 24), ("ME", 22), ("MK", 19), ("MN", 20),
        ("MR", 27), ("MT", 31), ("MU", 30), ("NI", 28), ("NL", 18), ("NO", 15), ("OM", 23), ("PK", 24),
        ("PL", 28), ("PS", 29), ("PT", 25), ("QA", 29), ("RO", 24), ("RS", 22), ("RU", 33), ("SA", 24),
        ("SC", 31), ("SD", 18), ("SE", 24), ("SI", 19), ("SK", 24), ("SM", 27), ("SO", 23), ("ST", 25),
        ("SV", 28), ("TL", 23), ("TN", 24), ("TR", 26), ("UA", 29), ("VA", 22), ("VG", 24), ("XK", 20),
        ("YE", 30),
    ];
    TABLE.iter().find(|(c, _)| *c == country).map(|(_, n)| *n)
}

/// IBAN : longueur du pays, clé à deux chiffres (`isdigit()`), MOD 97-10 / country length, check digits.
pub fn iban(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let expected = iban_length(&slice(&value, 0, 2))?;
    if char_len(&value) != expected || !pystr::isdigit(&slice(&value, 2, 4))? {
        return None;
    }
    let rearranged = slice(&value, 4, expected) + &slice(&value, 0, 4);
    mod97_10_ok(&rearranged).then_some(value)
}

/// Préfixes (IIN) et longueurs des réseaux de cartes, identiques à `intl._CARD_RULES` (Python).
/// Card network prefixes and lengths, identical to the Python table.
#[rustfmt::skip]
const CARD_RULES: &[(u32, u32, &[usize])] = &[
    (4, 4, &[13, 16, 19]), (51, 55, &[16]), (2221, 2720, &[16]), (34, 34, &[15]), (37, 37, &[15]),
    (300, 305, &[14, 16]), (36, 36, &[14, 16]), (38, 39, &[14, 16]), (6011, 6011, &[16, 17, 18, 19]),
    (644, 649, &[16, 17, 18, 19]), (65, 65, &[16, 17, 18, 19]), (3528, 3589, &[16, 17, 18, 19]),
    (62, 62, &[16, 17, 18, 19]), (2200, 2204, &[16, 17, 18, 19]), (50, 50, &[16, 17, 18, 19]),
    (56, 69, &[16, 17, 18, 19]),
];

fn card_network_ok(value: &str) -> bool {
    CARD_RULES.iter().any(|&(low, high, lengths)| {
        let width = low.to_string().len();
        lengths.contains(&value.len()) && (low..=high).contains(&(number(&value[..width]) as u32))
    })
}

fn card_value(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    if !(13..=19).contains(&char_len(&value)) || !is_digits(&value) {
        return None;
    }
    let first = value.chars().next()?;
    if value.chars().all(|c| c == first) {
        return None;
    }
    (card_network_ok(&value) && luhn_ok(&value)).then_some(value)
}

/// Toute carte sauf 14 chiffres (forme d'un SIRET) / any card except 14 digits (a SIRET's shape).
pub fn card(candidate: &str) -> Option<String> {
    card_value(candidate).filter(|v| v.len() != 14)
}

/// Carte Diners à 14 chiffres, exigée avec un mot-clé / 14-digit Diners card, keyword required.
pub fn card14(candidate: &str) -> Option<String> {
    card_value(candidate).filter(|v| v.len() == 14)
}

pub fn imei(candidate: &str) -> Option<String> {
    let value = strip_separators(candidate);
    (char_len(&value) == 15 && luhn_ok(&value)).then_some(value)
}

pub fn ipv4(candidate: &str) -> Option<String> {
    let first = candidate.split('.').next().unwrap_or("");
    (!matches!(first, "0" | "127" | "255")).then(|| candidate.to_string())
}

/// `ipaddress.IPv4Address(text)` : quatre octets décimaux ASCII, sans zéro de tête / four ASCII decimal octets.
fn parse_ipv4(text: &str) -> Option<u32> {
    let mut address = 0u32;
    let mut octets = 0;
    for octet in text.split('.') {
        octets += 1;
        let digits = !octet.is_empty() && octet.bytes().all(|b| b.is_ascii_digit());
        if octets > 4 || !digits || octet.len() > 3 || (octet.len() > 1 && octet.starts_with('0')) {
            return None;
        }
        let value = u32::try_from(number(octet)).ok().filter(|&v| v <= 255)?;
        address = (address << 8) | value;
    }
    (octets == 4).then_some(address)
}

/// `_BaseV6._parse_hextet` : 1 à 4 chiffres hexadécimaux ASCII / 1 to 4 ASCII hex digits.
fn parse_hextet(text: &str) -> Option<u128> {
    let hex = !text.is_empty() && text.len() <= 4 && text.bytes().all(|b| b.is_ascii_hexdigit());
    hex.then(|| u128::from_str_radix(text, 16).ok()).flatten()
}

/// `ipaddress.IPv6Address(text)` transcrit pas à pas (Python 3.11+) : « / » refusé, identifiant de zone après
/// « % », suffixe IPv4, un seul « :: ». Transcribed step by step: no "/", zone id after "%", IPv4 suffix,
/// at most one "::".
fn parse_ipv6(text: &str) -> Option<u128> {
    if text.contains('/') {
        return None;
    }
    let address = match text.split_once('%') {
        None => text,
        Some((_, zone)) if zone.is_empty() || zone.contains('%') => return None,
        Some((address, _)) => address,
    };
    // `split(':', maxsplit=9)` : au plus 10 parties / at most 10 parts.
    let mut parts: Vec<Cow<'_, str>> = address.splitn(10, ':').map(Cow::Borrowed).collect();
    if parts.len() < 3 {
        return None;
    }
    if parts.last().is_some_and(|last| last.contains('.')) {
        let ipv4 = parse_ipv4(&parts.pop()?)?;
        parts.push(Cow::Owned(format!("{:x}", ipv4 >> 16)));
        parts.push(Cow::Owned(format!("{:x}", ipv4 & 0xFFFF)));
    }
    let count = parts.len();
    if count > 9 {
        return None;
    }
    let mut skip = None;
    for (i, part) in parts.iter().enumerate().take(count - 1).skip(1) {
        if part.is_empty() {
            if skip.is_some() {
                return None;
            }
            skip = Some(i);
        }
    }
    // Parties avant et après « :: », et hextets sautés / parts before and after "::", and skipped hextets.
    let (high, low, skipped) = match skip {
        Some(i) => {
            let (mut high, mut low) = (i, count - i - 1);
            if parts[0].is_empty() {
                high -= 1;
                if high != 0 {
                    return None;
                }
            }
            if parts[count - 1].is_empty() {
                low -= 1;
                if low != 0 {
                    return None;
                }
            }
            let skipped = 8usize.checked_sub(high + low).filter(|&s| s >= 1)?;
            (high, low, skipped)
        }
        None => {
            if count != 8 || parts[0].is_empty() || parts[count - 1].is_empty() {
                return None;
            }
            (count, 0, 0)
        }
    };
    let mut value: u128 = 0;
    for part in &parts[..high] {
        value = (value << 16) | parse_hextet(part)?;
    }
    // « :: » seul saute 8 hextets : décalage de 128 bits d'une valeur nulle, qui le reste.
    // A bare "::" skips 8 hextets: a 128-bit shift of a zero value, which stays zero.
    value = value.checked_shl(16 * skipped as u32).unwrap_or(0);
    for part in &parts[count - low..] {
        value = (value << 16) | parse_hextet(part)?;
    }
    Some(value)
}

/// Forme compressée RFC 5952, identique à `intl._compress_ipv6` (Python) / same as the Python function.
fn compress_ipv6(address: u128) -> String {
    let segments: [u16; 8] = std::array::from_fn(|i| (address >> (112 - 16 * i)) as u16);
    let (mut best_start, mut best_len) = (usize::MAX, 0usize);
    let mut i = 0;
    while i < 8 {
        if segments[i] == 0 {
            let start = i;
            while i < 8 && segments[i] == 0 {
                i += 1;
            }
            if i - start > best_len {
                best_start = start;
                best_len = i - start;
            }
        } else {
            i += 1;
        }
    }
    let hex =
        |range: std::ops::Range<usize>| -> Vec<String> { segments[range].iter().map(|s| format!("{s:x}")).collect() };
    if best_len > 1 {
        let left = hex(0..best_start).join(":");
        let right = hex(best_start + best_len..8).join(":");
        format!("{left}::{right}")
    } else {
        hex(0..8).join(":")
    }
}

pub fn ipv6(candidate: &str) -> Option<String> {
    if candidate.matches(':').count() < 2 || pystr::count(candidate, Is::Alnum)? < 3 {
        return None;
    }
    let address = parse_ipv6(candidate)?;
    // Boucle locale, non spécifiée, ou leur forme IPv4 encapsulée : jamais une donnée personnelle.
    // Loopback, unspecified, or their IPv4-mapped form: never personal data.
    let mapped = (address >> 32 == 0xFFFF).then_some(address as u32);
    if address <= 1 || mapped.is_some_and(|v4| v4 >> 24 == 127 || v4 == 0) {
        return None;
    }
    Some(compress_ipv6(address))
}

pub fn mac(candidate: &str) -> Option<String> {
    let value = pystr::upper(&candidate.replace('-', ":"))?;
    (value != "00:00:00:00:00:00" && value != "FF:FF:FF:FF:FF:FF").then_some(value)
}

pub fn btc(candidate: &str) -> Option<String> {
    let prefix = pystr::lower(&slice(candidate, 0, 3))?;
    if prefix == "bc1" || prefix == "tb1" {
        return if bech32_ok(candidate) { pystr::lower(candidate) } else { None };
    }
    base58check_ok(candidate).then(|| candidate.to_string())
}

pub fn eth(candidate: &str) -> Option<String> {
    if eip55_ok(candidate) {
        pystr::lower(candidate)
    } else {
        None
    }
}

pub fn email(candidate: &str) -> Option<String> {
    let at = candidate.rfind('@')?;
    let (local, domain) = (&candidate[..at], &candidate[at + 1..]);
    if local.is_empty() || local.starts_with('.') || local.ends_with('.') || local.contains("..") {
        return None;
    }
    Some(format!("{local}@{}", pystr::lower(domain)?))
}

/// Numéro international (+CC) : 8 à 15 chiffres / 8 to 15 digits.
pub fn digits_e164(candidate: &str) -> Option<String> {
    let mut digits = pystr::digits(candidate)?;
    if pystr::lstrip(candidate).starts_with("00") {
        digits = slice(&digits, 2, usize::MAX);
    }
    ((8..=15).contains(&char_len(&digits)) && is_digits(&digits)).then(|| format!("+{digits}"))
}

/// Date jj/mm/aaaa, jj.mm.aaaa ou aaaa-mm-jj valide ; chaque partie lue par `int()`, comme Python.
/// Valid calendar date; each part read by `int()`, as in Python.
pub fn calendar_date(candidate: &str) -> Option<String> {
    let normalized = candidate.replace(['.', '-'], "/");
    let parts: Vec<&str> = normalized.split('/').filter(|p| !p.is_empty()).collect();
    let [first, second, third] = parts[..] else {
        return None;
    };
    let numbers = (pystr::int(first)?, pystr::int(second)?, pystr::int(third)?);
    let (year, month, day) = if char_len(first) == 4 { numbers } else { (numbers.2, numbers.1, numbers.0) };
    if !(1..=9999).contains(&year) || !(1..=12).contains(&month) || day < 1 {
        return None;
    }
    let max_day = match month {
        2 if is_leap(year) => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    };
    (day <= max_day).then(|| format!("{year:04}-{month:02}-{day:02}"))
}
