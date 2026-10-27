//! Validateurs natifs : transcription exacte de `gdprguardian.validators`, pack par pack.
//!
//! Native validators: exact transcription of `gdprguardian.validators`, pack by pack. Les sorties sont identiques
//! caractère pour caractère sur toute entrée, chiffres non ASCII et casse Unicode comprises (tests différentiels
//! `tests/test_validators_native.py`) ; la sémantique des chaînes de Python vient de `pystr`. Outputs are
//! identical on every input, non-ASCII digits and Unicode case included (differential tests); Python's string
//! semantics come from `pystr`.
//!
//! Un validateur est une simple fonction (`ValidatorFn`), que le balayage et les détecteurs appellent sans état :
//! ses petites tables (longueurs IBAN, lettres de contrôle, bureaux, préfixes) sont donc recopiées des modules
//! Python, et les tests les parcourent en entier contre eux. A validator is a plain function, called statelessly
//! by the scan and the detectors: its small tables are therefore mirrored from the Python modules, and the tests
//! walk them exhaustively against them.

mod be;
mod ch;
mod checksums;
mod de;
mod es;
mod fr;
mod intl;
mod it;
mod lu;
mod mc;
mod nl;
mod pt;
mod pystr;

pub use checksums::mod97_10_ok;
// API publique de l'ancien `validators.rs`, gardée pour les autres chantiers / the former public API, kept for the
// other tracks (unused here).
#[allow(unused_imports)]
pub use checksums::luhn_ok;

/// Validateur : la valeur canonique si le candidat est valide, sinon `None` / canonical value, or `None`.
pub type ValidatorFn = fn(&str) -> Option<String>;

/// Registre unique, noms Python (`gdprguardian.validators.resolve`) et fonctions Rust : `NATIVE` et `lookup` en
/// découlent. Single registry, Python names and Rust functions: `NATIVE` and `lookup` derive from it.
macro_rules! registry {
    ($($name:literal => $function:path,)+) => {
        /// Noms des validateurs natifs / native validator names.
        pub const NATIVE: &[&str] = &[$($name),+];

        /// Validateur natif d'un nom Python (« fr.nir ») / native validator for a Python name.
        pub fn lookup(name: &str) -> Option<ValidatorFn> {
            Some(match name {
                $($name => $function as ValidatorFn,)+
                _ => return None,
            })
        }
    };
}

registry! {
    "fr.nir" => fr::nir,
    "fr.nir_without_key" => fr::nir_without_key,
    "fr.spi" => fr::spi,
    "fr.siren" => fr::siren,
    "fr.siret" => fr::siret,
    "fr.tva" => fr::tva,
    "fr.rib" => fr::rib,
    "fr.luhn_digits" => fr::luhn_digits,
    "fr.finess" => fr::finess,
    "fr.siv_plate" => fr::siv_plate,
    "fr.alnum_mixed" => fr::alnum_mixed,
    "fr.contextual_id" => fr::contextual_id,
    "fr.phone_field" => fr::phone_field,
    "fr.phone" => fr::phone,
    "fr.phone_overseas" => fr::phone_overseas,
    "fr.eori" => fr::eori,
    "intl.iban" => intl::iban,
    "intl.card" => intl::card,
    "intl.card14" => intl::card14,
    "intl.imei" => intl::imei,
    "intl.ipv4" => intl::ipv4,
    "intl.ipv6" => intl::ipv6,
    "intl.mac" => intl::mac,
    "intl.btc" => intl::btc,
    "intl.eth" => intl::eth,
    "intl.email" => intl::email,
    "intl.digits_e164" => intl::digits_e164,
    "intl.calendar_date" => intl::calendar_date,
    "intl.login_word" => intl::login_word,
    "be.nn" => be::nn,
    "be.bis" => be::bis,
    "be.niss" => be::niss,
    "be.niss_unpadded" => be::niss_unpadded,
    "be.enterprise_number" => be::enterprise_number,
    "be.eid" => be::eid,
    "be.bban" => be::bban,
    "be.phone" => be::phone,
    "ch.avs" => ch::avs,
    "ch.uid" => ch::uid,
    "ch.phone" => ch::phone,
    "de.steuer_id" => de::steuer_id,
    "de.steuernummer" => de::steuernummer,
    "de.rvnr" => de::rvnr,
    "de.kvnr" => de::kvnr,
    "de.id_document" => de::id_document,
    "de.fuehrerschein" => de::fuehrerschein,
    "de.ust_idnr" => de::ust_idnr,
    "de.phone" => de::phone,
    "de.phone_mobile" => de::phone_mobile,
    "es.dni" => es::dni,
    "es.nie" => es::nie,
    "es.cif" => es::cif,
    "es.nif_person" => es::nif_person,
    "es.vat_person" => es::vat_person,
    "es.vat_company" => es::vat_company,
    "es.nss" => es::nss,
    "es.phone" => es::phone,
    "it.codice_fiscale" => it::codice_fiscale,
    "it.partita_iva" => it::partita_iva,
    "it.vat" => it::vat,
    "it.phone" => it::phone,
    "it.phone_mobile" => it::phone_mobile,
    "lu.matricule" => lu::matricule,
    "lu.matricule_legacy" => lu::matricule_legacy,
    "lu.tva" => lu::tva,
    "lu.rcs" => lu::rcs,
    "lu.phone" => lu::phone,
    "mc.tva" => mc::tva,
    "mc.rci" => mc::rci,
    "mc.phone" => mc::phone,
    "nl.bsn" => nl::bsn,
    "nl.btw" => nl::btw,
    "nl.btw_person" => nl::btw_person,
    "nl.btw_company" => nl::btw_company,
    "nl.kvk" => nl::kvk,
    "nl.document_number" => nl::document_number,
    "nl.postcode" => nl::postcode,
    "nl.phone" => nl::phone,
    "nl.phone_mobile" => nl::phone_mobile,
    "pt.nif" => pt::nif,
    "pt.nif_person" => pt::nif_person,
    "pt.nipc" => pt::nipc,
    "pt.vat_person" => pt::vat_person,
    "pt.vat_company" => pt::vat_company,
    "pt.niss" => pt::niss,
    "pt.cc" => pt::cc,
    "pt.nic" => pt::nic,
    "pt.sns" => pt::sns,
    "pt.phone" => pt::phone,
}

// --- Outils communs / shared helpers ---------------------------------------------------------------------------

/// `_text.strip_separators` : retire espaces, points, tirets et barres obliques / removes ' ', '.', '-', '/'.
fn strip_separators(value: &str) -> String {
    value.chars().filter(|c| !matches!(c, ' ' | '.' | '-' | '/')).collect()
}

/// `checksums.is_digits` : `isascii() and isdigit()`, donc non vide / hence non-empty.
fn is_digits(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|b| b.is_ascii_digit())
}

/// `len()` de Python, en points de code / Python's `len()`, in code points.
fn char_len(value: &str) -> usize {
    value.chars().count()
}

/// `value[start:end]` de Python, en points de code / Python slicing, in code points.
fn slice(value: &str, start: usize, end: usize) -> String {
    value.chars().skip(start).take(end.saturating_sub(start)).collect()
}

/// `int()` de chiffres ASCII déjà vérifiés, au plus 19 / of ASCII digits already checked, at most 19.
fn number(digits: &str) -> u64 {
    digits.bytes().fold(0u64, |acc, b| acc.wrapping_mul(10).wrapping_add(u64::from(b.wrapping_sub(b'0'))))
}

/// `re.sub("[^0-9]", "", value)` : les chiffres ASCII seuls / ASCII digits only.
fn ascii_digits(value: &str) -> String {
    value.chars().filter(char::is_ascii_digit).collect()
}

/// `digits.zfill(width)` de chiffres ASCII / of ASCII digits.
fn zfill(digits: &str, width: usize) -> String {
    format!("{digits:0>width$}")
}

/// `sum(int(d) * w for d, w in zip(digits, weights))` de chiffres ASCII / of ASCII digits.
fn weighted_sum(digits: &str, weights: &[i64]) -> i64 {
    digits.bytes().zip(weights).map(|(b, w)| (i64::from(b) - i64::from(b'0')) * w).sum()
}

/// Année bissextile grégorienne / Gregorian leap year.
fn is_leap(year: u64) -> bool {
    (year.is_multiple_of(4) && !year.is_multiple_of(100)) || year.is_multiple_of(400)
}

/// Chiffres nationaux d'un téléphone écrit avec ou sans l'indicatif `code` (« +32 », « 0032 »), `None` pour un
/// autre indicatif : `digits.removeprefix("00")` puis l'indicatif, après « + » ou « 00 ».
/// National digits of a phone written with or without the `code` country code, `None` for another code.
fn national_digits(candidate: &str, code: &str) -> Option<String> {
    let digits = ascii_digits(candidate);
    if pystr::lstrip(candidate).starts_with('+') || digits.starts_with("00") {
        let international = digits.strip_prefix("00").unwrap_or(&digits);
        return international.strip_prefix(code).map(str::to_string);
    }
    Some(digits)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Valeurs publiées (Wikipédia, organismes) reprises des tests Python / published values from the Python tests.
    #[test]
    fn reference_values() {
        let cases: &[(&str, &str, Option<&str>)] = &[
            ("fr.nir", "2 69 05 49 588 157 80", Some("269054958815780")),
            ("fr.nir", "2 69 05 49 588 157 81", None),
            ("fr.siret", "35600000049837", Some("35600000049837")),
            ("fr.phone", "+33 (0)6 12 34 56 78", Some("+33612345678")),
            ("intl.iban", "FR76 3000 6000 0112 3456 7890 189", Some("FR7630006000011234567890189")),
            ("intl.card", "4111 1111 1111 1111", Some("4111111111111111")),
            (
                "intl.eth",
                "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
                Some("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"),
            ),
            ("intl.btc", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", Some("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")),
            (
                "intl.btc",
                "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
                Some("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"),
            ),
            ("intl.ipv6", "2001:db8::1", Some("2001:db8::1")),
            ("intl.ipv6", "::ffff:1.2.3.4", Some("::ffff:102:304")),
            ("intl.ipv6", "::ffff:127.0.0.1", None),
            ("intl.calendar_date", "03/03/1985", Some("1985-03-03")),
            // Filtre fort 1.0.2 / strong filter 1.0.2.
            ("intl.calendar_date", "12 mars 1985", Some("1985-03-12")),
            ("intl.calendar_date", "1ER AOUT 1990", Some("1990-08-01")),
            ("intl.calendar_date", "31 fevrier 1985", None),
            ("intl.ipv6", "a::b", None),
            ("intl.ipv6", "fe80::1%eth0", Some("fe80::1")),
            ("intl.mac", "001a.2b3c.4d5e", Some("00:1A:2B:3C:4D:5E")),
            ("intl.mac", "1234.5678.9012", None),
            ("fr.phone", "(+33) 7 10 02 19 76", Some("+33710021976")),
            ("fr.contextual_id", "clt-204518", Some("CLT204518")),
            // 1.0.2, second tour : jamais une date ni une plage d'années / never a date or a year range.
            ("fr.contextual_id", "2024-03-15", None),
            ("fr.contextual_id", "12/03/2024", None),
            ("fr.contextual_id", "2024-2025", None),
            ("fr.contextual_id", "2026-0045", Some("20260045")),
            ("fr.contextual_id", "75/12345", Some("7512345")),
            ("intl.login_word", "jdupont", Some("jdupont")),
            ("intl.login_word", "unique", None),
            ("intl.login_word", "pouvant", None),
            ("intl.login_word", "rapidement", None),
            ("be.niss", "85.07.30-033.28", Some("85073003328")),
            ("be.niss", "98.47.28-997.65", Some("98472899765")),
            ("be.niss_unpadded", "5060712337", Some("05060712337")),
            ("be.enterprise_number", "BE (0) 403 019 261", Some("0403019261")),
            ("be.enterprise_number", "BE 0428.759.497", Some("0428759497")),
            ("be.eid", "591-1917064-58", Some("591191706458")),
            ("be.phone", "+32 (0)474 12 34 56", Some("+32474123456")),
            ("ch.avs", "756.1234.5678.97", Some("7561234567897")),
            ("ch.uid", "CHE-116.281.710 MWST", Some("CHE116281710")),
            ("ch.phone", "+41 44 668 18 00", Some("+41446681800")),
            ("de.steuer_id", "86095742719", Some("86095742719")),
            ("de.ust_idnr", "DE136695976", Some("DE136695976")),
            ("de.phone_mobile", "0151 23456789", Some("+4915123456789")),
            ("es.dni", "12345678Z", Some("12345678Z")),
            ("es.nie", "X1234567L", Some("X1234567L")),
            ("es.cif", "A58818501", Some("A58818501")),
            ("it.codice_fiscale", "RSSMRA85T10A562S", Some("RSSMRA85T10A562S")),
            ("it.partita_iva", "00743110157", Some("00743110157")),
            ("lu.tva", "LU 150 274 42", Some("LU15027442")),
            ("lu.rcs", "B123456", Some("B123456")),
            ("mc.rci", "99 S 03847", Some("99S03847")),
            ("nl.bsn", "111222333", Some("111222333")),
            ("nl.postcode", "1234ab", Some("1234 AB")),
            ("nl.postcode", "1234 SS", None),
            ("pt.nif_person", "123 456 789", Some("123456789")),
            ("pt.nipc", "500 000 000", Some("500000000")),
            ("pt.phone", "912 345 678", Some("+351912345678")),
        ];
        for &(name, candidate, expected) in cases {
            let validate = lookup(name).unwrap_or_else(|| panic!("{name} absent / missing"));
            assert_eq!(validate(candidate).as_deref(), expected, "{name}({candidate})");
        }
    }

    #[test]
    fn registry_names_are_unique_and_resolvable() {
        let mut names = NATIVE.to_vec();
        names.sort_unstable();
        names.dedup();
        assert_eq!(names.len(), NATIVE.len());
        assert!(NATIVE.iter().all(|name| lookup(name).is_some()));
        assert!(lookup("xx.unknown").is_none());
    }
}
