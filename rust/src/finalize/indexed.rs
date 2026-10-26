//! Texte indexé par caractère : les positions sont celles de Python (points de code).
//!
//! Text indexed by character: offsets are Python's (code points). Rust garde l'UTF-8 et ne note que les
//! caractères non ASCII, avec le nombre cumulé d'octets en plus : un texte français (quelques accents) est
//! indexé en une passe rapide, mémoire proportionnelle aux seuls caractères non ASCII. Rust keeps UTF-8 and
//! records only non-ASCII characters with the cumulative extra bytes: one fast pass, memory proportional to
//! the non-ASCII characters only.

/// Premier octet non ASCII, cherché par blocs de 16 (un « ou » par bloc, vectorisable).
/// First non-ASCII byte, searched 16 bytes at a time (one "or" per block, vectorisable).
fn first_non_ascii(bytes: &[u8]) -> Option<usize> {
    let (blocks, rest) = bytes.as_chunks::<16>();
    let mut offset = 0;
    for block in blocks {
        if !block.iter().fold(0u8, |any, &b| any | b).is_ascii() {
            if let Some(i) = block.iter().position(|b| !b.is_ascii()) {
                return Some(offset + i);
            }
        }
        offset += 16;
    }
    rest.iter().position(|b| !b.is_ascii()).map(|i| offset + i)
}

pub struct IndexedText<'a> {
    text: &'a str,
    /// Pour chaque caractère non ASCII : (indice, octets en plus cumulés, lui compris).
    /// For each non-ASCII character: (index, cumulative extra bytes, itself included).
    wide: Vec<(u32, u32)>,
    chars: usize,
}

impl<'a> IndexedText<'a> {
    /// `None` au-delà de 4 Gio (positions sur 32 bits) / `None` beyond 4 GiB (32-bit offsets).
    pub fn new(text: &'a str) -> Option<Self> {
        u32::try_from(text.len()).ok()?;
        let bytes = text.as_bytes();
        let mut wide = Vec::new();
        let mut extra = 0usize;
        let mut pos = 0;
        while let Some(skip) = bytes.get(pos..).and_then(first_non_ascii) {
            pos += skip;
            let width = text.get(pos..).and_then(|rest| rest.chars().next()).map_or(1, char::len_utf8);
            let index = pos - extra;
            extra += width - 1;
            wide.push((index as u32, extra as u32));
            pos += width;
        }
        Some(Self { text, wide, chars: text.len() - extra })
    }

    pub fn as_str(&self) -> &'a str {
        self.text
    }

    /// Longueur en caractères (`len()` de Python) / length in characters (Python's `len()`).
    pub fn len(&self) -> usize {
        self.chars
    }

    /// Octet du caractère `index`, borné à la fin du texte / byte of character `index`, clamped to the end.
    #[inline]
    pub fn byte(&self, index: usize) -> usize {
        let before = self.wide.partition_point(|&(i, _)| (i as usize) < index);
        let extra = before.checked_sub(1).and_then(|k| self.wide.get(k)).map_or(0, |&(_, e)| e as usize);
        (index + extra).min(self.text.len())
    }

    /// Indice du caractère qui commence à cet octet / index of the character starting at this byte.
    pub fn char_index(&self, byte: usize) -> usize {
        // Un caractère non ASCII d'indice i finit à l'octet i + 1 + octets en plus / ends at byte i + 1 + extra.
        let before = self.wide.partition_point(|&(i, e)| i as usize + 1 + e as usize <= byte);
        let extra = before.checked_sub(1).and_then(|k| self.wide.get(k)).map_or(0, |&(_, e)| e as usize);
        byte.min(self.text.len()) - extra
    }

    /// `text[start:end]` (indices positifs, bornés comme en Python) / Python slicing, clamped.
    pub fn slice(&self, start: usize, end: usize) -> &'a str {
        if start >= end {
            return "";
        }
        self.text.get(self.byte(start)..self.byte(end)).unwrap_or("")
    }

    /// `text[start:]`.
    pub fn tail(&self, start: usize) -> &'a str {
        self.text.get(self.byte(start)..).unwrap_or("")
    }

    /// `text[index]`, ou `None` hors du texte / or `None` outside the text.
    pub fn char_at(&self, index: usize) -> Option<char> {
        if index >= self.chars {
            return None;
        }
        self.text.get(self.byte(index)..)?.chars().next()
    }
}

#[cfg(test)]
mod tests {
    use super::{first_non_ascii, IndexedText};

    #[test]
    fn block_search_finds_the_first_byte() {
        for length in 0..40 {
            assert_eq!(first_non_ascii(&vec![b'a'; length]), None);
            for at in 0..length {
                let mut bytes = vec![b'a'; length];
                bytes[at] = 0xC3;
                bytes[length - 1] = if at == length - 1 { 0xC3 } else { 0xF0 };
                assert_eq!(first_non_ascii(&bytes), Some(at));
            }
        }
    }

    #[test]
    fn python_offsets() {
        let text = IndexedText::new("aé😀b").expect("small");
        assert_eq!(text.len(), 4);
        assert_eq!(text.slice(1, 3), "é😀");
        assert_eq!(text.slice(3, 1), "");
        assert_eq!(text.slice(2, 99), "😀b");
        assert_eq!(text.tail(3), "b");
        assert_eq!(text.char_at(2), Some('😀'));
        assert_eq!(text.char_at(4), None);
        for index in 0..=4 {
            assert_eq!(text.char_index(text.byte(index)), index);
        }
        let ascii = IndexedText::new("abc").expect("small");
        assert_eq!((ascii.slice(1, 9), ascii.char_index(2), ascii.char_at(3)), ("bc", 2, None));
    }

    #[test]
    fn matches_a_dense_index() {
        let sample = "Zoé, ÉLODIE 😀 et 𝐀 — fin. ".repeat(7);
        let text = IndexedText::new(&sample).expect("small");
        let starts: Vec<usize> = sample.char_indices().map(|(b, _)| b).chain([sample.len()]).collect();
        assert_eq!(text.len(), sample.chars().count());
        for (index, &byte) in starts.iter().enumerate() {
            assert_eq!((text.byte(index), text.char_index(byte)), (byte, index));
        }
    }
}
