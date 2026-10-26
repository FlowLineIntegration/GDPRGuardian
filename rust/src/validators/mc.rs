//! Monaco : transcription de `gdprguardian/validators/mc.py` (TVA au régime français, RCI, téléphones) / Monaco.

use super::{char_len, fr, national_digits, pystr, slice, strip_separators};

/// TVA monégasque : numéro français FR + clé + 9 chiffres commençant par 000 / French scheme, 000 prefix.
pub fn tva(candidate: &str) -> Option<String> {
    let mut value = pystr::upper(&strip_separators(candidate))?;
    if !value.starts_with("FR") {
        value.insert_str(0, "FR");
    }
    if char_len(&value) != 13 || slice(&value, 4, 7) != "000" {
        return None;
    }
    fr::tva(&value)
}

/// Répertoire du commerce et de l'industrie : `[0-9]{2}(?:SC|[CPS])[0-9]{5}` en entier, ex. 99 S 03847.
/// Trade register number, full match.
pub fn rci(candidate: &str) -> Option<String> {
    let value = pystr::upper(&strip_separators(candidate))?;
    let b = value.as_bytes();
    let kind = match b.len() {
        8 => matches!(b[2], b'C' | b'P' | b'S'),
        9 => &b[2..4] == b"SC",
        _ => false,
    };
    let digits = |part: &[u8]| part.iter().all(u8::is_ascii_digit);
    (kind && digits(&b[..2]) && digits(&b[b.len() - 5..])).then_some(value)
}

/// Téléphone monégasque, forme E.164 : fixe 8 chiffres (9…), mobile 8 (4…) ou 9 (6…).
/// Monaco phone, E.164 form: 8-digit landline (9…), 8 (4…) or 9-digit (6…) mobile.
pub fn phone(candidate: &str) -> Option<String> {
    let digits = national_digits(candidate, "377")?;
    // Le 0 ne précède que les mobiles 6… / the trunk 0 only precedes 6… mobiles.
    let digits = digits.strip_prefix('0').unwrap_or(&digits);
    let b = digits.as_bytes();
    let valid = (b.len() == 8 && b"3489".contains(&b[0])) || (b.len() == 9 && b"67".contains(&b[0]));
    valid.then(|| format!("+377{digits}"))
}
