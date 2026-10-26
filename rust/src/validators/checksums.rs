//! Sommes de contrôle : transcription de `gdprguardian/validators/checksums.py` (ISO 7064, ISO/IEC 7812, ICAO 9303,
//! Verhoeff, BIP-173/350, EIP-55). Checksums: transcription of `checksums.py`.

use sha2::{Digest, Sha256};
use sha3::Keccak256;

use super::is_digits;
use super::pystr::{self, Is};

/// Chiffre doublé de Luhn, ramené à un chiffre / Luhn's doubled digit, brought back to one digit.
pub const LUHN_DOUBLE: [u32; 10] = [0, 2, 4, 6, 8, 1, 3, 5, 7, 9];

/// ISO/IEC 7812 (Luhn).
pub fn luhn_ok(digits: &str) -> bool {
    if !is_digits(digits) {
        return false;
    }
    let total: u32 = digits
        .bytes()
        .rev()
        .enumerate()
        .map(|(i, b)| {
            let d = u32::from(b - b'0');
            if i % 2 == 1 {
                LUHN_DOUBLE[d as usize]
            } else {
                d
            }
        })
        .sum();
    total.is_multiple_of(10)
}

/// ISO 7064 MOD 97-10 sur alphanumérique (A=10..Z=35), comme Python : `upper()`, lettres converties, puis
/// `isdecimal()` et `int()`. Ici `isdigit()` puis `int()` : un chiffre non décimal (« ² ») est rejeté par
/// la conversion, même résultat. ISO 7064 MOD 97-10 on alphanumeric input, as Python: `upper()`, letters
/// converted, then `isdecimal()` and `int()`. Here `isdigit()` then `int()`: a non-decimal digit ("²") is
/// rejected by the conversion, same result.
pub fn mod97_10_ok(value: &str) -> bool {
    let Some(upper) = pystr::upper(value) else {
        return false;
    };
    let mut numeric = String::with_capacity(2 * upper.len());
    for c in upper.chars() {
        if c.is_ascii_uppercase() {
            let rank = c as u8 - b'A' + 10;
            numeric.push(char::from(b'0' + rank / 10));
            numeric.push(char::from(b'0' + rank % 10));
        } else {
            numeric.push(c);
        }
    }
    pystr::isdigit(&numeric) == Some(true) && pystr::int_mod(&numeric, 97) == Some(1)
}

/// ISO 7064 MOD 11,10 (Steuer-ID DE).
pub fn iso7064_mod11_10_ok(digits: &str) -> bool {
    if !is_digits(digits) || digits.len() < 2 {
        return false;
    }
    let (body, key) = digits.as_bytes().split_at(digits.len() - 1);
    let mut product = 10;
    for &b in body {
        let total = match (u32::from(b - b'0') + product) % 10 {
            0 => 10,
            total => total,
        };
        product = (2 * total) % 11;
    }
    (11 - product) % 10 == u32::from(key[0] - b'0')
}

#[rustfmt::skip]
const VERHOEFF_D: [[u8; 10]; 10] = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
];
#[rustfmt::skip]
const VERHOEFF_P: [[u8; 10]; 8] = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
];

/// Verhoeff (matricule LU).
pub fn verhoeff_ok(digits: &str) -> bool {
    if !is_digits(digits) {
        return false;
    }
    let check = digits.bytes().rev().enumerate().fold(0u8, |check, (i, b)| {
        VERHOEFF_D[usize::from(check)][usize::from(VERHOEFF_P[i % 8][usize::from(b - b'0')])]
    });
    check == 0
}

/// ICAO 9303 : poids 7-3-1, A=10..Z=35, tout autre caractère 0 (appelants en ASCII).
/// ICAO 9303: weights 7-3-1, A=10..Z=35, any other character 0 (ASCII callers).
pub fn icao_check_digit(field: &str) -> u32 {
    const WEIGHTS: [u32; 3] = [7, 3, 1];
    let total: u32 = field
        .bytes()
        .enumerate()
        .map(|(i, b)| {
            let value = match b {
                b'0'..=b'9' => u32::from(b - b'0'),
                b'A'..=b'Z' => u32::from(b - b'A') + 10,
                _ => 0,
            };
            value * WEIGHTS[i % 3]
        })
        .sum();
    total % 10
}

// --- Bitcoin ---

const B58_ALPHABET: &str = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

/// Base58Check : nombre en base 58, zéros de tête pour les « 1 », double SHA-256 des 4 derniers octets.
/// Base58Check: base-58 number, leading zero bytes for the "1"s, double SHA-256 of the last 4 bytes.
pub fn base58check_ok(value: &str) -> bool {
    let mut bytes: Vec<u8> = Vec::new();
    for ch in value.chars() {
        let Some(index) = B58_ALPHABET.find(ch) else {
            return false;
        };
        let mut carry = index as u32;
        for byte in bytes.iter_mut().rev() {
            carry += u32::from(*byte) * 58;
            *byte = (carry & 0xff) as u8;
            carry >>= 8;
        }
        while carry > 0 {
            bytes.insert(0, (carry & 0xff) as u8);
            carry >>= 8;
        }
    }
    let leading = value.chars().take_while(|&c| c == '1').count();
    let mut raw = vec![0u8; leading];
    raw.extend(bytes);
    if raw.len() < 5 {
        return false;
    }
    let (payload, checksum) = raw.split_at(raw.len() - 4);
    let digest = Sha256::digest(Sha256::digest(payload));
    &digest[..4] == checksum
}

const BECH32_CHARSET: &str = "qpzry9x8gf2tvdw0s3jn54khce6mua7l";

fn bech32_polymod(values: &[u32]) -> u32 {
    const GEN: [u32; 5] = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3];
    let mut chk: u32 = 1;
    for &value in values {
        let top = chk >> 25;
        chk = ((chk & 0x1FFFFFF) << 5) ^ value;
        for (i, g) in GEN.iter().enumerate() {
            if (top >> i) & 1 == 1 {
                chk ^= g;
            }
        }
    }
    chk
}

/// BIP-173 (bech32) et BIP-350 (bech32m), en points de code comme Python (`ord(c)` de la partie lisible).
/// BIP-173 and BIP-350, on code points as in Python (`ord(c)` of the human-readable part).
pub fn bech32_ok(address: &str) -> bool {
    let (Some(lower), Some(upper)) = (pystr::lower(address), pystr::upper(address)) else {
        return false;
    };
    if lower != address && upper != address {
        return false;
    }
    let chars: Vec<char> = lower.chars().collect();
    let Some(pos) = chars.iter().rposition(|&c| c == '1') else {
        return false;
    };
    if pos < 1 || pos + 7 > chars.len() {
        return false;
    }
    let (hrp, data) = (&chars[..pos], &chars[pos + 1..]);
    let mut values: Vec<u32> = Vec::with_capacity(2 * hrp.len() + 1 + data.len());
    values.extend(hrp.iter().map(|&c| u32::from(c) >> 5));
    values.push(0);
    values.extend(hrp.iter().map(|&c| u32::from(c) & 31));
    for &c in data {
        match BECH32_CHARSET.find(c) {
            Some(v) => values.push(v as u32),
            None => return false,
        }
    }
    matches!(bech32_polymod(&values), 1 | 0x2BC830A3)
}

/// Adresse ETH : casse uniforme acceptée, sinon somme EIP-55 (Keccak-256 de la forme minuscule en UTF-8).
/// ETH address: uniform case accepted, else the EIP-55 checksum (Keccak-256 of the lower-case UTF-8 form).
pub fn eip55_ok(address: &str) -> bool {
    let body: String = address.chars().skip(2).collect();
    if body.chars().count() != 40 {
        return false;
    }
    let (Some(lower), Some(upper)) = (pystr::lower(&body), pystr::upper(&body)) else {
        return false;
    };
    if lower == body || upper == body {
        return body.bytes().all(|b| b.is_ascii_hexdigit());
    }
    // Seuls les 40 premiers quartets du hachage comptent / only the first 40 hash nibbles matter.
    let digest = Keccak256::digest(lower.as_bytes());
    let nibble = |i: usize| (digest[i / 2] >> if i.is_multiple_of(2) { 4 } else { 0 }) & 0x0f;
    let (Some(alpha), Some(capital)) = (pystr::each(&body, Is::Alpha), pystr::each(&body, Is::Upper)) else {
        return false;
    };
    (0..40).all(|i| !alpha[i] || capital[i] == (nibble(i) >= 8))
}
