//! Mise en forme des nombres, tailles et dates, en français et en anglais / number, size and date formatting.
//!
//! Bibliothèque standard seule : build.rs inclut aussi ce fichier (`#[path]`) pour les valeurs de qualité,
//! mises en forme une fois pour toutes à la construction. Standard library only: build.rs includes this file too.
//!
//! Règles, identiques à `Intl.NumberFormat` « fr-FR » / « en-GB » qu'emploie le JavaScript du site (site/static) :
//! rules, identical to the `Intl.NumberFormat` "fr-FR" / "en-GB" used by the site's JavaScript:
//! - entiers : séparateur des milliers espace fine insécable U+202F en français (« 3 751 »), virgule en anglais
//!   (« 3,751 ») ; integers: thousands separator U+202F in French, comma in English;
//! - décimales : virgule en français (« 0,45 »), point en anglais (« 0.45 ») ; decimal comma / point;
//! - une décimale : écriture la plus courte du nombre (`String(x)`), puis arrondi moitié vers l'extérieur
//!   (« halfExpand » d'Intl) ; one decimal: shortest writing of the number, then half away from zero;
//! - tailles : multiples de 1024, unité suivante dès que `Math.round(x * 10) / 10 >= 1024`, entier en octets,
//!   une décimale au-delà, espace insécable U+00A0 avant l'unité : « 512 o », « 12,4 Mo », « 1,2 Go » /
//!   « 512 B », « 12.4 MB », « 1.2 GB » (o Ko Mo Go To, B KB MB GB TB); sizes: powers of 1024, next unit as soon
//!   as the value rounds to 1024, integer bytes, one decimal above, no-break space before the unit;
//! - pourcentages : une décimale, sans signe % ; mémoire = utilisée / totale × 100 ; percentages: one decimal;
//! - dates : « 25 octobre 2026 » (« 1er » le premier du mois), « 25 October 2026 ».

/// Langue d'une page / a page's language.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Lang {
    Fr,
    En,
}

impl Lang {
    /// Code de langue (Content-Language) / language code.
    pub fn code(self) -> &'static str {
        match self {
            Lang::Fr => "fr",
            Lang::En => "en",
        }
    }

    fn group_separator(self) -> &'static str {
        match self {
            Lang::Fr => "\u{202F}",
            Lang::En => ",",
        }
    }

    fn decimal_separator(self) -> char {
        match self {
            Lang::Fr => ',',
            Lang::En => '.',
        }
    }
}

/// Espace insécable entre un nombre et son unité / no-break space between a number and its unit.
pub const UNIT_SPACE: char = '\u{00A0}';

const UNITS_FR: [&str; 5] = ["o", "Ko", "Mo", "Go", "To"];
const UNITS_EN: [&str; 5] = ["B", "KB", "MB", "GB", "TB"];
const MONTHS_FR: [&str; 12] = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
];
const MONTHS_EN: [&str; 12] = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];

/// Ajoute des chiffres ASCII groupés par trois / appends ASCII digits grouped by three.
fn push_grouped(digits: &str, lang: Lang, out: &mut String) {
    let count = digits.len();
    for (index, digit) in digits.chars().enumerate() {
        if index > 0 && (count - index) % 3 == 0 {
            out.push_str(lang.group_separator());
        }
        out.push(digit);
    }
}

/// Entier avec séparateur des milliers / integer with thousands separator.
pub fn int(value: u64, lang: Lang) -> String {
    let mut out = String::with_capacity(24);
    push_grouped(&value.to_string(), lang, &mut out);
    out
}

/// Nombre décimal écrit en JSON (« -1234.50 »), décimales gardées telles quelles ; None si ce n'est pas
/// `-?chiffres(.chiffres)?`. A JSON-written number, its decimals kept as given; None unless `-?digits(.digits)?`.
pub fn decimal_text(raw: &str, lang: Lang) -> Option<String> {
    let (negative, body) = match raw.strip_prefix('-') {
        Some(rest) => (true, rest),
        None => (false, raw),
    };
    let (integer, fraction) = match body.split_once('.') {
        Some((integer, fraction)) => (integer, Some(fraction)),
        None => (body, None),
    };
    let digits = |text: &str| !text.is_empty() && text.bytes().all(|byte| byte.is_ascii_digit());
    if !digits(integer) || fraction.is_some_and(|fraction| !digits(fraction)) {
        return None;
    }
    let mut out = String::with_capacity(raw.len() + 8);
    if negative {
        out.push('-');
    }
    push_grouped(integer, lang, &mut out);
    if let Some(fraction) = fraction {
        out.push(lang.decimal_separator());
        out.push_str(fraction);
    }
    Some(out)
}

/// Texte à une décimale (« 37.3 », point, sans séparateur), comme `Intl.NumberFormat` des navigateurs (ICU) :
/// écriture décimale la plus courte qui redonne le même double (celle de `String(x)` en JavaScript, « 12.35 »),
/// puis arrondi décimal moitié vers l'extérieur (« 12.4 ») ; ni NaN ni « -0.0 ». One-decimal text like the
/// browsers' `Intl.NumberFormat` (ICU): shortest round-trip decimal (JavaScript's `String(x)`), then decimal
/// rounding half away from zero; neither NaN nor "-0.0".
pub fn tenth_text(value: f64) -> String {
    if !value.is_finite() {
        return String::from("0.0");
    }
    // Display de Rust : la plus courte écriture exacte au retour, jamais d'exposant / shortest, never an exponent.
    let shortest = format!("{}", value.abs());
    let (whole, fraction) = shortest.split_once('.').unwrap_or((shortest.as_str(), ""));
    let mut fraction = fraction.bytes();
    let tenth = fraction.next().unwrap_or(b'0');
    let round_up = fraction.next().is_some_and(|digit| digit >= b'5');
    let mut digits: Vec<u8> = whole.bytes().chain(std::iter::once(tenth)).collect();
    if round_up {
        let mut index = digits.len();
        loop {
            if index == 0 {
                digits.insert(0, b'1');
                break;
            }
            index -= 1;
            if digits[index] == b'9' {
                digits[index] = b'0';
            } else {
                digits[index] += 1;
                break;
            }
        }
    }
    let negative = value < 0.0 && digits.iter().any(|digit| *digit != b'0');
    let (integer, tenth) = digits.split_at(digits.len() - 1);
    let mut out = String::with_capacity(digits.len() + 2);
    if negative {
        out.push('-');
    }
    out.extend(integer.iter().map(|digit| char::from(*digit)));
    out.push('.');
    out.push(char::from(tenth[0]));
    out
}

/// Nombre à une décimale (pourcentages, tailles) / one-decimal number (percentages, sizes).
pub fn one_decimal(value: f64, lang: Lang) -> String {
    decimal_text(&tenth_text(value), lang).unwrap_or_else(|| String::from("0"))
}

/// Valeur ramenée à son unité (1024 octets ou plus) : (valeur, rang de l'unité) / value scaled to its unit.
fn scale(value: u64) -> (f64, usize) {
    let last = UNITS_EN.len() - 1;
    let mut scaled = value as f64;
    let mut unit = 0;
    while scaled >= 1024.0 && unit < last {
        scaled /= 1024.0;
        unit += 1;
    }
    // 1023,96 Ko s'arrondirait à « 1024,0 Ko » : unité suivante / would round to 1024.0: next unit.
    if (scaled * 10.0).round() >= 10240.0 && unit < last {
        scaled /= 1024.0;
        unit += 1;
    }
    (scaled, unit)
}

/// Taille lisible, multiples de 1024 / human-readable size, powers of 1024.
pub fn bytes(value: u64, lang: Lang) -> String {
    let units = match lang {
        Lang::Fr => &UNITS_FR,
        Lang::En => &UNITS_EN,
    };
    if value < 1024 {
        return format!("{}{UNIT_SPACE}{}", int(value, lang), units[0]);
    }
    let (scaled, unit) = scale(value);
    format!("{}{UNIT_SPACE}{}", one_decimal(scaled, lang), units[unit])
}

/// Taille ramenée à ce qu'en montre [`bytes`] (une décimale de son unité, exacte sous 1024 octets) : le JSON public
/// n'en dit pas plus que la page, et une variation ne trahit pas la taille exacte d'un document. Size rounded to what
/// [`bytes`] shows (one decimal of its unit, exact below 1024 bytes): the public JSON tells no more than the page.
pub fn rounded_bytes(value: u64) -> u64 {
    if value < 1024 {
        return value;
    }
    let (scaled, unit) = scale(value);
    // Dixièmes affichés, puis plus proche entier de dixièmes × 1024^unité / 10 / shown tenths, then nearest integer.
    let tenths: u128 = tenth_text(scaled).replace('.', "").parse().unwrap_or(0);
    let rounded = (tenths * 1024_u128.pow(unit as u32) + 5) / 10;
    u64::try_from(rounded).unwrap_or(u64::MAX)
}

/// Jours depuis le 1970-01-01 -> (année, mois 1-12, jour 1-31), calendrier grégorien proleptique (H. Hinnant).
/// Days since 1970-01-01 -> (year, month, day).
pub fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let month = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    let year = yoe + era * 400 + i64::from(month <= 2);
    (year, month, day)
}

/// (année, mois, jour) -> jours depuis le 1970-01-01 / (year, month, day) -> days since 1970-01-01.
pub fn days_from_civil(year: i64, month: u32, day: u32) -> i64 {
    let year = year - i64::from(month <= 2);
    let era = year.div_euclid(400);
    let yoe = year.rem_euclid(400);
    let month = i64::from(month);
    let mp = if month > 2 { month - 3 } else { month + 9 };
    let doy = (153 * mp + 2) / 5 + i64::from(day) - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146_097 + doe - 719_468
}

/// « 2026-10-25 ».
pub fn iso_date(days: i64) -> String {
    let (year, month, day) = civil_from_days(days);
    format!("{year:04}-{month:02}-{day:02}")
}

/// « 2026-10-25 » -> jours depuis le 1970-01-01 ; None si la date n'existe pas / None for an invalid date.
pub fn parse_iso_date(text: &str) -> Option<i64> {
    let bytes = text.as_bytes();
    if bytes.len() != 10 || bytes[4] != b'-' || bytes[7] != b'-' {
        return None;
    }
    let number = |range: std::ops::Range<usize>| -> Option<u32> {
        let part = text.get(range)?;
        if part.bytes().all(|byte| byte.is_ascii_digit()) {
            part.parse().ok()
        } else {
            None
        }
    };
    let (year, month, day) = (number(0..4)?, number(5..7)?, number(8..10)?);
    let days = days_from_civil(i64::from(year), month, day);
    (civil_from_days(days) == (i64::from(year), month, day)).then_some(days)
}

/// Date en toutes lettres / date in words: « 25 octobre 2026 », « 1er mai 2027 », « 25 October 2026 ».
pub fn date_words(days: i64, lang: Lang) -> String {
    let (year, month, day) = civil_from_days(days);
    let index = (month - 1) as usize;
    match lang {
        Lang::Fr if day == 1 => format!("1er {} {year}", MONTHS_FR[index]),
        Lang::Fr => format!("{day} {} {year}", MONTHS_FR[index]),
        Lang::En => format!("{day} {} {year}", MONTHS_EN[index]),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn integers_are_grouped_per_language() {
        assert_eq!(int(0, Lang::Fr), "0");
        assert_eq!(int(999, Lang::En), "999");
        assert_eq!(int(3751, Lang::Fr), "3\u{202F}751");
        assert_eq!(int(3751, Lang::En), "3,751");
        assert_eq!(int(1_234_567, Lang::Fr), "1\u{202F}234\u{202F}567");
        assert_eq!(int(1_234_567, Lang::En), "1,234,567");
        assert_eq!(int(u64::MAX, Lang::En), "18,446,744,073,709,551,615");
    }

    #[test]
    fn decimals_keep_their_digits() {
        assert_eq!(decimal_text("0.45", Lang::Fr).as_deref(), Some("0,45"));
        assert_eq!(decimal_text("0.45", Lang::En).as_deref(), Some("0.45"));
        assert_eq!(decimal_text("99.20", Lang::Fr).as_deref(), Some("99,20"));
        assert_eq!(
            decimal_text("12345.6", Lang::Fr).as_deref(),
            Some("12\u{202F}345,6")
        );
        assert_eq!(
            decimal_text("12345.6", Lang::En).as_deref(),
            Some("12,345.6")
        );
        assert_eq!(decimal_text("-1500", Lang::En).as_deref(), Some("-1,500"));
        for bad in ["", "-", "1.", ".5", "1e3", "1.2.3", "abc", "+1", "1 000"] {
            assert_eq!(decimal_text(bad, Lang::Fr), None, "{bad}");
        }
    }

    #[test]
    fn one_decimal_rounds_and_never_shows_minus_zero() {
        assert_eq!(one_decimal(12.345, Lang::Fr), "12,3");
        // Comme Intl (ICU) : on arrondit « 12.35 », l'écriture la plus courte, pas 12.3499999… (valeur exacte).
        // Like Intl (ICU): "12.35", the shortest writing, is rounded, not the exact 12.3499999…
        assert_eq!(one_decimal(12.35, Lang::En), "12.4");
        assert_eq!(one_decimal(0.35, Lang::En), "0.4");
        assert_eq!(one_decimal(1.15, Lang::Fr), "1,2");
        assert_eq!(one_decimal(9.95, Lang::En), "10.0");
        assert_eq!(one_decimal(999.95, Lang::En), "1,000.0");
        // Moitié : vers l'extérieur / half: away from zero.
        assert_eq!(one_decimal(37.25, Lang::En), "37.3");
        assert_eq!(one_decimal(0.25, Lang::En), "0.3");
        assert_eq!(one_decimal(-0.25, Lang::En), "-0.3");
        assert_eq!(one_decimal(0.04, Lang::En), "0.0");
        assert_eq!(one_decimal(0.05, Lang::En), "0.1");
        assert_eq!(one_decimal(1e20, Lang::En), "100,000,000,000,000,000,000.0");
        assert_eq!(tenth_text(2.0), "2.0");
        assert_eq!(tenth_text(f64::INFINITY), "0.0");
        assert_eq!(one_decimal(99.96, Lang::En), "100.0");
        assert_eq!(one_decimal(-0.01, Lang::Fr), "0,0");
        assert_eq!(one_decimal(f64::NAN, Lang::En), "0.0");
        assert_eq!(one_decimal(1234.56, Lang::Fr), "1\u{202F}234,6");
    }

    #[test]
    fn sizes_use_1024_and_one_decimal() {
        assert_eq!(bytes(0, Lang::Fr), "0\u{a0}o");
        assert_eq!(bytes(1023, Lang::En), "1,023\u{a0}B");
        assert_eq!(bytes(1023, Lang::Fr), "1\u{202F}023\u{a0}o");
        assert_eq!(bytes(1024, Lang::Fr), "1,0\u{a0}Ko");
        assert_eq!(bytes(13_002_342, Lang::Fr), "12,4\u{a0}Mo");
        assert_eq!(bytes(13_002_342, Lang::En), "12.4\u{a0}MB");
        assert_eq!(bytes(1_288_490_189, Lang::Fr), "1,2\u{a0}Go");
        assert_eq!(bytes(1_288_490_189, Lang::En), "1.2\u{a0}GB");
        // Arrondi à la frontière / rounding at the boundary.
        assert_eq!(bytes(1024 * 1024 - 1, Lang::En), "1.0\u{a0}MB");
        assert_eq!(bytes(u64::MAX, Lang::En), "16,777,216.0\u{a0}TB");
        assert_eq!(bytes(5 * (1 << 40), Lang::Fr), "5,0\u{a0}To");
    }

    #[test]
    fn rounded_sizes_show_the_same_text_and_no_more() {
        assert_eq!(rounded_bytes(0), 0);
        assert_eq!(rounded_bytes(1023), 1023);
        assert_eq!(rounded_bytes(1024), 1024);
        // 4,88 Ko affichés « 4,9 Ko » : 4,9 × 1024 = 5017,6 -> 5018 / shown as 4.9 KB.
        assert_eq!(rounded_bytes(5000), 5018);
        assert_eq!(rounded_bytes(5001), 5018);
        assert_eq!(rounded_bytes(13_002_342), 13_002_342);
        assert_eq!(rounded_bytes(1_048_576 + 2048), 1_048_576);
        assert_eq!(rounded_bytes(u64::MAX), u64::MAX);
        let mut samples: Vec<u64> = (0..300_000).collect();
        samples.extend((0..64).flat_map(|shift| {
            let base = 1_u64 << shift;
            [base - 1, base, base + 1, base / 3 * 2, base / 10 * 9]
        }));
        let mut value = 1_u64;
        while let Some(next) = value.checked_mul(3) {
            samples.extend([next.saturating_sub(7), next, next.saturating_add(7)]);
            value = next;
        }
        for value in samples {
            let rounded = rounded_bytes(value);
            for lang in [Lang::Fr, Lang::En] {
                assert_eq!(
                    bytes(rounded, lang),
                    bytes(value, lang),
                    "{value} -> {rounded}"
                );
            }
            assert_eq!(rounded_bytes(rounded), rounded, "{value}: idempotent");
        }
    }

    #[test]
    fn dates_round_trip_and_read_in_words() {
        for days in [-1, 0, 1, 365, 10_957, 20_386, 20_751, 2_932_896] {
            let (y, m, d) = civil_from_days(days);
            assert_eq!(days_from_civil(y, m, d), days);
            assert_eq!(parse_iso_date(&iso_date(days)), Some(days));
        }
        let launch = parse_iso_date("2026-10-25").unwrap();
        assert_eq!(iso_date(launch), "2026-10-25");
        assert_eq!(date_words(launch, Lang::Fr), "25 octobre 2026");
        assert_eq!(date_words(launch, Lang::En), "25 October 2026");
        let first = parse_iso_date("2027-05-01").unwrap();
        assert_eq!(date_words(first, Lang::Fr), "1er mai 2027");
        assert_eq!(date_words(first, Lang::En), "1 May 2027");
        assert_eq!(
            date_words(parse_iso_date("2024-02-29").unwrap(), Lang::Fr),
            "29 février 2024"
        );
        for bad in [
            "2026-02-30",
            "2026-13-01",
            "2026-1-01",
            "20261025xx",
            "2026/10/25",
            "abcd-ef-gh",
        ] {
            assert_eq!(parse_iso_date(bad), None, "{bad}");
        }
    }
}
