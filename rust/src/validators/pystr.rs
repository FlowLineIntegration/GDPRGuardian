//! Sémantique des chaînes de Python pour les validateurs / Python string semantics for the validators.
//!
//! Les validateurs Python s'appuient sur `str` : `upper()`, `isdigit()`, `int()`, `lstrip()`. En ASCII, ces
//! règles sont stables : elles sont transcrites ici. Hors ASCII, elles suivent la base Unicode de l'interpréteur,
//! d'une autre version que celle de Rust (`"ɤ".upper()` diffère, par exemple) : Rust ne la devine jamais et
//! interroge l'interpréteur, le temps d'un candidat. Ces candidats sont rares, les motifs des packs étant en
//! ASCII. Sans interpréteur (tests Rust seuls), la question reste sans réponse et le validateur rejette.
//!
//! Python validators rely on `str`. In ASCII these rules are stable and transcribed here. Beyond ASCII they
//! follow the interpreter's Unicode database, of another version than Rust's (`"ɤ".upper()` differs, for
//! instance): Rust never guesses it and asks the interpreter, for one candidate. Such candidates are rare, pack
//! patterns being ASCII. Without an interpreter (Rust-only tests) the question has no answer: the validator
//! rejects.

use std::time::{SystemTime, UNIX_EPOCH};

use pyo3::prelude::*;
use pyo3::types::{PyInt, PyString};

use super::is_leap;

/// Interroge l'interpréteur, s'il est là ; une exception Python donne `None`. Possible aussi GIL relâché
/// (`py.detach`) : le fil le reprend le temps de l'appel.
/// Asks the interpreter, when there is one; a Python exception gives `None`. Also fine with the GIL released
/// (`py.detach`): the thread takes it back for the call.
fn ask<R>(f: impl for<'py> FnOnce(Python<'py>) -> PyResult<R>) -> Option<R> {
    Python::try_attach(|py| f(py).ok()).flatten()
}

/// `str.isspace()` : séparateurs Zs et classes bidirectionnelles WS, B et S (dont U+001C–U+001F). Ensemble
/// inchangé depuis Unicode 6.3, donc pour toutes les versions de Python prises en charge ; vérifié point de code
/// par point de code contre l'interpréteur par les tests.
/// Zs separators and bidi classes WS, B and S (U+001C–U+001F included). Unchanged since Unicode 6.3, hence for
/// every supported Python version; checked code point by code point against the interpreter by the tests.
pub fn is_space(c: char) -> bool {
    matches!(
        c,
        '\t'..='\r'
            | '\x1c'..=' '
            | '\u{85}'
            | '\u{a0}'
            | '\u{1680}'
            | '\u{2000}'..='\u{200a}'
            | '\u{2028}'
            | '\u{2029}'
            | '\u{202f}'
            | '\u{205f}'
            | '\u{3000}'
    )
}

/// `s.lstrip()`.
pub fn lstrip(s: &str) -> &str {
    s.trim_start_matches(is_space)
}

/// `s.<method>()` pour une méthode de `str` qui rend une chaîne / a `str` method returning a string.
fn transform(s: &str, method: &str) -> Option<String> {
    ask(|py| PyString::new(py, s).call_method0(method)?.extract())
}

/// `s.upper()`.
pub fn upper(s: &str) -> Option<String> {
    if s.is_ascii() {
        return Some(s.to_ascii_uppercase());
    }
    transform(s, "upper")
}

/// `s.lower()`.
pub fn lower(s: &str) -> Option<String> {
    if s.is_ascii() {
        return Some(s.to_ascii_lowercase());
    }
    transform(s, "lower")
}

/// Prédicat de `str` appliqué à un caractère / a `str` predicate applied to one character.
#[derive(Clone, Copy)]
pub enum Is {
    /// `isdigit()` : chiffres décimaux, mais aussi « ² » ou « ① » / decimal digits, but also "²" or "①".
    Digit,
    /// `isalpha()`.
    Alpha,
    /// `isalnum()`.
    Alnum,
    /// `isupper()`.
    Upper,
}

impl Is {
    fn ascii(self, b: u8) -> bool {
        match self {
            Is::Digit => b.is_ascii_digit(),
            Is::Alpha => b.is_ascii_alphabetic(),
            Is::Alnum => b.is_ascii_alphanumeric(),
            Is::Upper => b.is_ascii_uppercase(),
        }
    }

    fn method(self) -> &'static str {
        match self {
            Is::Digit => "isdigit",
            Is::Alpha => "isalpha",
            Is::Alnum => "isalnum",
            Is::Upper => "isupper",
        }
    }
}

/// Le prédicat pour chaque caractère de `s` ; hors ASCII, un seul passage par l'interpréteur.
/// The predicate for each character of `s`; beyond ASCII, a single visit to the interpreter.
pub fn each(s: &str, is: Is) -> Option<Vec<bool>> {
    if s.is_ascii() {
        return Some(s.bytes().map(|b| is.ascii(b)).collect());
    }
    ask(|py| {
        let mut buffer = [0u8; 4];
        s.chars()
            .map(|c| {
                if c.is_ascii() {
                    Ok(is.ascii(c as u8))
                } else {
                    PyString::new(py, c.encode_utf8(&mut buffer)).call_method0(is.method())?.extract()
                }
            })
            .collect()
    })
}

/// `any(c.<is>() for c in s)`.
pub fn any(s: &str, is: Is) -> Option<bool> {
    if s.is_ascii() {
        return Some(s.bytes().any(|b| is.ascii(b)));
    }
    Some(each(s, is)?.contains(&true))
}

/// `sum(c.<is>() for c in s)`.
pub fn count(s: &str, is: Is) -> Option<usize> {
    if s.is_ascii() {
        return Some(s.bytes().filter(|&b| is.ascii(b)).count());
    }
    Some(each(s, is)?.into_iter().filter(|&yes| yes).count())
}

/// `"".join(c for c in s if c.isdigit())`.
pub fn digits(s: &str) -> Option<String> {
    if s.is_ascii() {
        return Some(s.chars().filter(char::is_ascii_digit).collect());
    }
    let flags = each(s, Is::Digit)?;
    Some(s.chars().zip(flags).filter_map(|(c, digit)| digit.then_some(c)).collect())
}

/// `s.isdigit()` : non vide, chaque caractère un chiffre / non-empty, every character a digit.
pub fn isdigit(s: &str) -> Option<bool> {
    if s.is_ascii() {
        return Some(!s.is_empty() && s.bytes().all(|b| b.is_ascii_digit()));
    }
    Some(each(s, Is::Digit)?.into_iter().all(|digit| digit))
}

/// Chiffres ASCII seuls, au plus `max_len` : le cas courant, calculé en Rust / ASCII digits only, the usual case.
fn plain_digits(s: &str, max_len: usize) -> bool {
    !s.is_empty() && s.len() <= max_len && s.bytes().all(|b| b.is_ascii_digit())
}

/// `int(s)` s'il vaut de 0 à `u64::MAX`, sinon `None` (exception, valeur négative ou trop grande). Toute autre
/// forme que des chiffres ASCII (« +3 », « 1_000 », espaces, chiffres non ASCII, limite de
/// `sys.get_int_max_str_digits`) revient à l'interpréteur.
/// `int(s)` when it lies in 0..=`u64::MAX`, else `None` (exception, negative or too large value). Any form other
/// than ASCII digits ("+3", "1_000", spaces, non-ASCII digits, the `sys.get_int_max_str_digits` limit) goes to
/// the interpreter.
pub fn int(s: &str) -> Option<u64> {
    // 19 chiffres tiennent toujours dans un u64 / 19 digits always fit in a u64.
    if plain_digits(s, 19) {
        return s.parse().ok();
    }
    ask(|py| py.get_type::<PyInt>().call1((s,))?.extract())
}

/// `int(s) % modulus` (modulus > 0), `None` si `int(s)` lève une exception / when `int(s)` raises.
pub fn int_mod(s: &str, modulus: u32) -> Option<u32> {
    // Au-delà de 640 chiffres, Python consulte sa limite de conversion : l'interpréteur décide.
    // Beyond 640 digits Python checks its conversion limit: the interpreter decides.
    if plain_digits(s, 640) {
        let modulus = u64::from(modulus);
        let remainder = s.bytes().fold(0, |acc, b| (acc * 10 + u64::from(b - b'0')) % modulus);
        return u32::try_from(remainder).ok();
    }
    ask(|py| py.get_type::<PyInt>().call1((s,))?.rem(modulus)?.extract())
}

/// `year <= date.today().year`, sur l'horloge locale comme Python. L'année locale vaut l'année UTC à un an près :
/// seules les deux années limites interrogent l'interpréteur, qui connaît le fuseau horaire.
/// As in Python, on the local clock. The local year is the UTC year give or take one: only the two edge years ask
/// the interpreter, which knows the time zone.
pub fn year_reached(year: u64) -> bool {
    match utc_year() {
        Some(utc) if year < utc => true,
        Some(utc) if year > utc + 1 => false,
        _ => ask(|py| {
            let today = py.import("datetime")?.getattr("date")?.call_method0("today")?;
            today.getattr("year")?.extract::<u64>()
        })
        .is_some_and(|today| year <= today),
    }
}

/// Année civile UTC de l'horloge système / UTC calendar year of the system clock.
fn utc_year() -> Option<u64> {
    let mut days = SystemTime::now().duration_since(UNIX_EPOCH).ok()?.as_secs() / 86_400;
    let mut year = 1970;
    loop {
        let length = if is_leap(year) { 366 } else { 365 };
        if days < length {
            return Some(year);
        }
        days -= length;
        year += 1;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ascii_rules() {
        assert_eq!(lstrip("\x1c\u{a0}\u{3000} +32"), "+32");
        assert!(!is_space('\u{180e}') && !is_space('\u{200b}'));
        assert_eq!(upper("be0403").as_deref(), Some("BE0403"));
        assert_eq!(int("1985"), Some(1985));
        assert_eq!(int("9999999999999999999"), Some(9_999_999_999_999_999_999));
        assert_eq!(int_mod("00100", 97), Some(3));
        // 10^640 - 1 = 99…9 ; 10^640 mod 97 = 10^(640 mod 96) = 10^64 mod 97 (Fermat).
        assert_eq!(int_mod(&"9".repeat(640), 97), int_mod(&format!("1{}", "0".repeat(64)), 97).map(|r| (r + 96) % 97));
        assert_eq!(isdigit(""), Some(false));
        assert_eq!(digits("+33 (0)6").as_deref(), Some("3306"));
        assert_eq!(count("fe80::1", Is::Alnum), Some(5));
        assert!(year_reached(1999));
        assert!(!year_reached(9999));
        assert!(utc_year().is_some_and(|year| year >= 2026));
    }

    /// Sans interpréteur, une question hors ASCII reste sans réponse / without an interpreter, no answer.
    #[test]
    fn non_ascii_without_interpreter() {
        assert_eq!(upper("ɤ"), None);
        assert_eq!(digits("٣"), None);
        assert_eq!(int("+3"), None);
        assert_eq!(lower("BE"), Some("be".to_string()));
    }
}
