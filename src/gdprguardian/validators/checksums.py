"""Sommes de contrôle génériques, écrites d'après les normes publiques.

Generic checksums, written from public standards (ISO 7064, ISO/IEC 7812, ICAO 9303, BIP-173/350,
EIP-55). Entrées : chaînes ASCII déjà nettoyées / inputs: already-cleaned ASCII strings.
"""

from __future__ import annotations

import hashlib

_LUHN_DOUBLE = (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)


def is_digits(value: str) -> bool:
    return value.isascii() and value.isdigit()


def luhn_ok(digits: str) -> bool:
    """ISO/IEC 7812 (Luhn)."""
    if not is_digits(digits):
        return False
    total = sum(int(c) for c in digits[-1::-2])
    total += sum(_LUHN_DOUBLE[int(c)] for c in digits[-2::-2])
    return total % 10 == 0


_ALNUM_TO_DIGITS = str.maketrans({chr(65 + i): str(10 + i) for i in range(26)})


def mod97_10_ok(value: str) -> bool:
    """ISO 7064 MOD 97-10 sur une chaîne alphanumérique (IBAN réarrangé) / on alphanumeric string."""
    numeric = value.upper().translate(_ALNUM_TO_DIGITS)
    # `isdecimal` et non `isdigit` : « ² » est un chiffre que `int()` refuse / "²" is a digit `int()` rejects.
    return numeric.isdecimal() and int(numeric) % 97 == 1


def iso7064_mod11_10_ok(digits: str) -> bool:
    """ISO 7064 MOD 11,10 (Steuer-ID DE, OIB HR)."""
    if not is_digits(digits) or len(digits) < 2:
        return False
    product = 10
    for ch in digits[:-1]:
        total = (int(ch) + product) % 10 or 10
        product = (2 * total) % 11
    return (11 - product) % 10 == int(digits[-1])


def iso7064_mod11_2_check(digits: str) -> str:
    """Caractère de contrôle ISO 7064 MOD 11-2 ('X' pour 10) / check character ('X' for 10)."""
    product = 0
    for ch in digits:
        product = ((product + int(ch)) * 2) % 11
    check = (12 - product) % 11
    return "X" if check == 10 else str(check)


_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 2, 3, 4, 0, 6, 7, 8, 9, 5), (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7), (4, 0, 1, 2, 3, 9, 5, 6, 7, 8), (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2), (7, 6, 5, 9, 8, 2, 1, 0, 4, 3), (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 5, 7, 6, 2, 8, 3, 0, 9, 4), (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7), (9, 4, 5, 3, 1, 2, 6, 8, 7, 0), (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5), (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def verhoeff_ok(digits: str) -> bool:
    if not is_digits(digits):
        return False
    check = 0
    for i, ch in enumerate(reversed(digits)):
        check = _VERHOEFF_D[check][_VERHOEFF_P[i % 8][int(ch)]]
    return check == 0


def icao_check_digit(field: str) -> int:
    """ICAO 9303 : poids 7-3-1, A=10..Z=35, '<'=0 / weights 7-3-1."""
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(field):
        if ch.isdigit():
            value = ord(ch) - 48
        elif "A" <= ch <= "Z":
            value = ord(ch) - 55
        else:
            value = 0
        total += value * weights[i % 3]
    return total % 10


def weighted_mod(digits: str, weights: tuple[int, ...], modulus: int) -> int:
    return sum(int(d) * w for d, w in zip(digits, weights, strict=False)) % modulus


# --- Bitcoin ---

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {c: i for i, c in enumerate(_B58_ALPHABET)}


def base58check_ok(value: str) -> bool:
    number = 0
    for ch in value:
        index = _B58_INDEX.get(ch)
        if index is None:
            return False
        number = number * 58 + index
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(value) - len(value.lstrip("1"))) + raw
    if len(raw) < 5:
        return False
    payload, checksum = raw[:-4], raw[-4:]
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] == checksum


_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_GEN = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
BECH32_CONST, BECH32M_CONST = 1, 0x2BC830A3


def _bech32_polymod(values: list[int]) -> int:
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ value
        for i in range(5):
            if (top >> i) & 1:
                chk ^= _BECH32_GEN[i]
    return chk


def bech32_ok(address: str) -> bool:
    """BIP-173 (bech32) et BIP-350 (bech32m)."""
    if address.lower() != address and address.upper() != address:
        return False
    address = address.lower()
    pos = address.rfind("1")
    if pos < 1 or pos + 7 > len(address):
        return False
    hrp, data = address[:pos], address[pos + 1:]
    try:
        values = [_BECH32_CHARSET.index(c) for c in data]
    except ValueError:
        return False
    expanded = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
    return _bech32_polymod(expanded + values) in (BECH32_CONST, BECH32M_CONST)


# --- Keccak-256 (Ethereum, padding 0x01, différent de SHA3-256 / differs from SHA3-256) ---

_KECCAK_RC = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)
_KECCAK_ROT = ((0, 36, 3, 41, 18), (1, 44, 10, 45, 2), (62, 6, 43, 15, 61),
               (28, 55, 25, 21, 56), (27, 20, 39, 8, 14))
_MASK64 = (1 << 64) - 1


def _rol(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (64 - shift))) & _MASK64 if shift else value


def _keccak_f(state: list[list[int]]) -> None:
    for rc in _KECCAK_RC:
        c = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x][y] ^= d[x]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(state[x][y], _KECCAK_ROT[x][y])
        for x in range(5):
            for y in range(5):
                state[x][y] = b[x][y] ^ (~b[(x + 1) % 5][y] & b[(x + 2) % 5][y])
        state[0][0] ^= rc


def keccak256(data: bytes) -> bytes:
    rate = 136
    padded = bytearray(data) + b"\x01" + b"\x00" * ((-len(data) - 1) % rate)
    padded[-1] |= 0x80
    state = [[0] * 5 for _ in range(5)]
    for offset in range(0, len(padded), rate):
        block = padded[offset:offset + rate]
        for i in range(rate // 8):
            state[i % 5][i // 5] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        _keccak_f(state)
    out = b"".join(state[i % 5][i // 5].to_bytes(8, "little") for i in range(rate // 8))
    return out[:32]


def eip55_ok(address: str) -> bool:
    """Adresse ETH : casse uniforme acceptée, sinon somme EIP-55 / uniform case accepted, else EIP-55."""
    body = address[2:]
    if len(body) != 40:
        return False
    if body.lower() == body or body.upper() == body:
        return all(c in "0123456789abcdefABCDEF" for c in body)
    # Seuls les 40 premiers quartets du hachage comptent / only the first 40 hash nibbles matter.
    digest = keccak256(body.lower().encode()).hex()[:40]
    for ch, nibble in zip(body, digest, strict=True):
        if ch.isalpha() and (ch.isupper() != (int(nibble, 16) >= 8)):
            return False
    return True
