//! Dates Excel -> valeurs Python, comme python-calamine 0.9 (calamine 0.36.1 et chrono 0.4.45).
//! Excel dates -> Python values, as python-calamine 0.9 does.
//!
//! Une valeur de style date devient une durée (format `[h]:mm:ss`), une heure (valeur < 1), une date (valeur
//! entière) ou une date et heure, comptées en millisecondes arrondies depuis le 30/12/1899 (1904 : +1462 jours ;
//! bogue de l'an 1900 : +1 jour avant le 60e). Hors des années 1 à 9999, le nombre reste tel quel. Là où
//! chrono paniquerait (milliseconde `i64::MIN`), `None` : la lecture est refusée et la référence répond.
//! A date-styled value becomes a duration, a time (value < 1), a date (whole value) or a datetime, counted in
//! rounded milliseconds from 1899-12-30 (1904: +1462 days; year-1900 bug: +1 day before the 60th). Outside years
//! 1 to 9999 the number stays as is. Where chrono would panic, `None`: reading is declined.

const MS_PER_DAY: f64 = 86_400_000.0;
const MS_PER_DAY_INT: i64 = 86_400_000;
const EXCEL_1900_1904_DIFF: f64 = 1462.0;
/// 30/12/1899 en jours depuis le 01/01/1970 / 1899-12-30 in days from 1970-01-01.
const EPOCH_DAYS: i64 = -25_569;
/// Bornes de `NaiveDate` (chrono 0.4.45) / `NaiveDate` bounds.
const MIN_YEAR: i64 = -262_143;
const MAX_YEAR: i64 = 262_142;

/// Valeur Python d'une cellule datée / Python value of a date-styled cell.
#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) enum Temporal {
    Float(f64),
    Date {
        year: i32,
        month: u8,
        day: u8,
    },
    DateTime {
        year: i32,
        month: u8,
        day: u8,
        hour: u8,
        minute: u8,
        second: u8,
        micro: u32,
    },
    Time {
        hour: u8,
        minute: u8,
        second: u8,
        micro: u32,
    },
    /// Arguments de `timedelta(days, seconds, microseconds)` tels que PyO3 les passe / as PyO3 passes them.
    Delta {
        days: i64,
        seconds: i32,
        micros: i32,
    },
}

/// Millisecondes arrondies ; `None` là où `TimeDelta::milliseconds` paniquerait / where chrono would panic.
fn milliseconds(days: f64) -> Option<i64> {
    // `as` sature (NaN -> 0), comme dans calamine / `as` saturates (NaN -> 0), as in calamine.
    let ms = (days * MS_PER_DAY).round() as i64;
    (ms != i64::MIN).then_some(ms)
}

/// Date civile d'un nombre de jours depuis le 01/01/1970 (algorithme de H. Hinnant) / civil date from days.
fn civil(days: i64) -> (i64, u8, u8) {
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    (yoe + era * 400 + i64::from(month <= 2), month as u8, day as u8)
}

/// Date et heure de chrono : `None` hors de ses bornes / chrono's datetime, `None` outside its bounds.
struct Moment {
    year: i64,
    month: u8,
    day: u8,
    ms_of_day: i64,
}

/// `ExcelDateTime::as_datetime` : `Err` = panique de chrono, `Ok(None)` = hors bornes / panic or out of range.
fn as_datetime(value: f64, is_1904: bool) -> Result<Option<Moment>, ()> {
    let f = if is_1904 { value + EXCEL_1900_1904_DIFF } else { value };
    let f = if f >= 60.0 { f } else { f + 1.0 };
    let ms = milliseconds(f).ok_or(())?;
    let (year, month, day) = civil(EPOCH_DAYS + ms.div_euclid(MS_PER_DAY_INT));
    if !(MIN_YEAR..=MAX_YEAR).contains(&year) {
        return Ok(None);
    }
    Ok(Some(Moment { year, month, day, ms_of_day: ms.rem_euclid(MS_PER_DAY_INT) }))
}

fn clock(ms_of_day: i64) -> (u8, u8, u8, u32) {
    let seconds = ms_of_day / 1_000;
    ((seconds / 3_600) as u8, (seconds / 60 % 60) as u8, (seconds % 60) as u8, (ms_of_day % 1_000 * 1_000) as u32)
}

fn in_python_range(year: i64) -> Option<i32> {
    (1..=9_999).contains(&year).then_some(year as i32)
}

/// Valeur d'une cellule datée, comme `CellValue::from` de python-calamine ; `None` = panique de calamine.
/// Value of a date-styled cell, as python-calamine's `CellValue::from`; `None` = calamine panic.
pub(crate) fn convert(value: f64, duration: bool, is_1904: bool) -> Option<Temporal> {
    if duration {
        // `as_duration` : ni époque ni décalage 1904 ; découpe de chrono (troncature vers zéro).
        // `as_duration`: no epoch nor 1904 shift; chrono's split (truncation toward zero).
        let ms = milliseconds(value)?;
        let days = ms / 1_000 / 86_400;
        let rest = ms - days * MS_PER_DAY_INT;
        let days = i64::from(i32::try_from(days).unwrap_or(i32::MAX));
        return Some(Temporal::Delta { days, seconds: (rest / 1_000) as i32, micros: (rest % 1_000 * 1_000) as i32 });
    }
    let moment = as_datetime(value, is_1904).ok()?;
    let fallback = Temporal::Float(value);
    let Some(moment) = moment else { return Some(fallback) };
    let (hour, minute, second, micro) = clock(moment.ms_of_day);
    if value < 1.0 {
        return Some(Temporal::Time { hour, minute, second, micro });
    }
    let Some(year) = in_python_range(moment.year) else { return Some(fallback) };
    let (month, day) = (moment.month, moment.day);
    if value == (value as u64) as f64 {
        return Some(Temporal::Date { year, month, day });
    }
    Some(Temporal::DateTime { year, month, day, hour, minute, second, micro })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn epoch_and_leap_bug() {
        // 1 -> 1900-01-01 ; 59 -> 1900-02-28 ; 60 -> 1900-03-01 (calamine, 29/02/1900 inexistant).
        assert_eq!(convert(1.0, false, false), Some(Temporal::Date { year: 1900, month: 1, day: 1 }));
        assert_eq!(convert(59.0, false, false), Some(Temporal::Date { year: 1900, month: 2, day: 28 }));
        assert_eq!(convert(60.0, false, false), Some(Temporal::Date { year: 1900, month: 2, day: 28 }));
        assert_eq!(convert(61.0, false, false), Some(Temporal::Date { year: 1900, month: 3, day: 1 }));
        assert_eq!(convert(45_000.0, false, false), Some(Temporal::Date { year: 2023, month: 3, day: 15 }));
        assert_eq!(convert(0.0, false, true), Some(Temporal::Time { hour: 0, minute: 0, second: 0, micro: 0 }));
        assert_eq!(convert(1.0, false, true), Some(Temporal::Date { year: 1904, month: 1, day: 2 }));
    }

    #[test]
    fn times_durations_and_bounds() {
        assert_eq!(convert(0.5, false, false), Some(Temporal::Time { hour: 12, minute: 0, second: 0, micro: 0 }));
        assert_eq!(
            convert(45_000.25, false, false),
            Some(Temporal::DateTime { year: 2023, month: 3, day: 15, hour: 6, minute: 0, second: 0, micro: 0 })
        );
        assert_eq!(convert(1.5, true, false), Some(Temporal::Delta { days: 1, seconds: 43_200, micros: 0 }));
        assert_eq!(convert(-0.25, true, false), Some(Temporal::Delta { days: 0, seconds: -21_600, micros: 0 }));
        assert_eq!(convert(3_000_000.0, false, false), Some(Temporal::Float(3_000_000.0)));
        assert_eq!(convert(f64::NEG_INFINITY, false, false), None);
        assert_eq!(convert(f64::INFINITY, false, false), Some(Temporal::Float(f64::INFINITY)));
        assert!(matches!(convert(f64::NAN, false, false), Some(Temporal::DateTime { year: 1899, .. })));
    }
}
