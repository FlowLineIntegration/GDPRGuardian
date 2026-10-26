//! Vocabulaire replié : une seule table pour le lexique Insee et toutes les listes de mots.
//!
//! Folded vocabulary: one table for the Insee lexicon and every word list. Une sonde répond à tout
//! (code du nom, mot courant, commune, mot-outil, étiquette…) ; les clés sont cherchées directement en
//! points de code, sans allocation. One probe answers everything; keys are looked up as code points,
//! without allocating.
//!
//! Disposition / layout : adressage ouvert à sondage linéaire (charge ≤ 1/2) ; chaque alvéole de 16 octets
//! porte l'empreinte, les appartenances et l'emplacement de la clé : une recherche lit une alvéole puis la
//! clé, deux accès mémoire. Linear-probing open addressing (load ≤ 1/2); each 16-byte slot holds the hash
//! tag, the memberships and where the key lies: a lookup reads one slot, then the key.

/// Appartenances d'une clé (bits) / key memberships (bits).
pub mod flag {
    /// Lexique des noms : le code est valide / names lexicon: the code is valid.
    pub const NAME: u32 = 1 << 0;
    /// `Lexicon.words`.
    pub const WORD: u32 = 1 << 1;
    /// `Lexicon.communes`.
    pub const COMMUNE: u32 = 1 << 2;
    pub const STOP: u32 = 1 << 3;
    pub const PARTICLE: u32 = 1 << 4;
    pub const FUNCTION: u32 = 1 << 5;
    pub const CONTEXTUAL: u32 = 1 << 6;
    pub const ORG_CONTEXT: u32 = 1 << 7;
    pub const ORG_FAMILY: u32 = 1 << 8;
    pub const DETERMINER: u32 = 1 << 9;
    pub const LOCATIVE: u32 = 1 << 10;
    pub const STRONG_LABEL: u32 = 1 << 11;
    pub const WEAK_LABEL: u32 = 1 << 12;
    pub const GIVEN_HEADER: u32 = 1 << 13;
    pub const SURNAME_HEADER: u32 = 1 << 14;
    pub const PERSON_HEADER: u32 = 1 << 15;
    pub const EMPTY_CELL: u32 = 1 << 16;
    pub const CASE_SENSITIVE_HONORIFIC: u32 = 1 << 17;
    pub const AUXILIARY: u32 = 1 << 18;
    /// `_vocab.NON_PERSON_LABELS` (« nom commercial »).
    pub const NON_PERSON_LABEL: u32 = 1 << 19;
    /// `_vocab.ORG_LEADS` (« ville », « syndicat »).
    pub const ORG_LEAD: u32 = 1 << 20;
    /// `_vocab.COMPANY_FORM_KEYS` (« sas », « sarl »).
    pub const COMPANY_FORM: u32 = 1 << 21;
    /// `fr_names._SAINT_WORDS` (« saint », « st »).
    pub const SAINT_WORD: u32 = 1 << 22;
    /// `_vocab.SURNAME_PARTICLES` (« le », « van »).
    pub const SURNAME_PARTICLE: u32 = 1 << 23;
    /// Codes postaux connus (`Lexicon.postal`) / known postcodes.
    pub const POSTCODE: u32 = 1 << 24;
    /// `fr_names._postcode_heads` (« 80300 albert ») : code postal et premier mot d'une de ses communes.
    /// Postcode and first word of one of its towns.
    pub const POSTCODE_HEAD: u32 = 1 << 25;
    /// `_vocab.TITLES` (« comte », « roi ») : titres, jamais un nom à particule / titles, never a particle surname.
    pub const TITLE: u32 = 1 << 26;
}

/// Réponse d'une sonde / probe answer.
#[derive(Clone, Copy, Default)]
pub struct Entry {
    code: u16,
    flags: u32,
}

impl Entry {
    #[inline]
    pub fn has(self, flag: u32) -> bool {
        self.flags & flag != 0
    }

    /// Code du lexique des noms (`names.get(key)`) / names lexicon code.
    #[inline]
    pub fn name(self) -> Option<u16> {
        self.has(flag::NAME).then_some(self.code)
    }
}

/// Alvéole : empreinte, appartenances, code et place de la clé (UTF-8) dans `bytes`.
/// Slot: hash tag, memberships, code and place of the UTF-8 key in `bytes`.
#[derive(Clone, Copy)]
struct Slot {
    tag: u32,
    flags: u32,
    code: u16,
    len: u16,
    offset: u32,
}

/// Alvéole libre / free slot.
const FREE: Slot = Slot { tag: 0, flags: 0, code: 0, len: 0, offset: u32::MAX };

pub struct Vocab {
    bytes: Vec<u8>,
    slots: Vec<Slot>,
    keys: usize,
    shift: u32,
}

impl Vocab {
    /// Table vide pour au plus `keys` clés (charge ≤ 1/2) / empty table for at most `keys` keys.
    pub fn with_capacity(keys: usize) -> Self {
        let capacity = (keys.max(8) * 2).next_power_of_two();
        Self { bytes: Vec::new(), slots: vec![FREE; capacity], keys: 0, shift: 64 - capacity.trailing_zeros() }
    }

    #[inline]
    fn home(&self, hash: u64) -> usize {
        // Bits de poids fort du produit : la table est une puissance de deux / high bits, power-of-two table.
        (hash.wrapping_mul(0x9E37_79B9_7F4A_7C15) >> self.shift) as usize
    }

    #[inline]
    fn key(&self, slot: &Slot) -> &[u8] {
        &self.bytes[slot.offset as usize..slot.offset as usize + slot.len as usize]
    }

    /// Alvéole de la clé (`Ok`), ou alvéole libre où l'insérer (`Err`) / the key's slot, or a free one.
    #[inline]
    fn find(&self, hash: u64, same: impl Fn(&[u8]) -> bool) -> Result<usize, usize> {
        let tag = (hash >> 32) as u32;
        let mask = self.slots.len() - 1;
        let mut i = self.home(hash);
        loop {
            let slot = &self.slots[i];
            if slot.offset == FREE.offset {
                return Err(i);
            }
            if slot.tag == tag && same(self.key(slot)) {
                return Ok(i);
            }
            i = (i + 1) & mask;
        }
    }

    /// Ajoute `flags` (et le code s'il est donné) à une clé ; refusée (`false`) au-delà de la capacité
    /// annoncée ou si elle est démesurée. Adds flags (and the code) to a key; refused beyond the capacity.
    pub fn insert(&mut self, key: &str, flags: u32, code: Option<u16>) -> bool {
        let hash = hash(key.chars());
        let i = match self.find(hash, |stored| stored == key.as_bytes()) {
            Ok(i) => i,
            Err(i) => {
                let (Ok(len), Ok(offset)) = (u16::try_from(key.len()), u32::try_from(self.bytes.len())) else {
                    return false;
                };
                if 2 * (self.keys + 1) > self.slots.len() || offset == FREE.offset {
                    return false;
                }
                self.bytes.extend_from_slice(key.as_bytes());
                self.slots[i] = Slot { tag: (hash >> 32) as u32, flags: 0, code: 0, len, offset };
                self.keys += 1;
                i
            }
        };
        let slot = &mut self.slots[i];
        slot.flags |= flags;
        if let Some(code) = code {
            slot.code = code;
        }
        true
    }

    /// Entrée d'une clé (vide si absente) / entry of a key (empty when absent).
    pub fn get(&self, key: &[char]) -> Entry {
        let same = |stored: &[u8]| {
            if stored.is_ascii() {
                // Cas courant : un octet par caractère / common case: one byte per character.
                stored.len() == key.len() && stored.iter().zip(key).all(|(&b, &c)| b as u32 == c as u32)
            } else {
                // Clés venues de `&str` : UTF-8 valide / keys come from `&str`: valid UTF-8.
                std::str::from_utf8(stored).is_ok_and(|s| s.chars().eq(key.iter().copied()))
            }
        };
        match self.find(hash(key.iter().copied()), same) {
            Ok(i) => Entry { code: self.slots[i].code, flags: self.slots[i].flags },
            Err(_) => Entry::default(),
        }
    }
}

/// FNV-1a sur les points de code, puis mélange final / FNV-1a over code points, then a final mix.
#[inline]
fn hash(key: impl Iterator<Item = char>) -> u64 {
    let mut h: u64 = 0xCBF2_9CE4_8422_2325;
    for c in key {
        h = (h ^ c as u64).wrapping_mul(0x0000_0100_0000_01B3);
    }
    h ^= h >> 31;
    h = h.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    h ^ (h >> 29)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(s: &str) -> Vec<char> {
        s.chars().collect()
    }

    #[test]
    fn lookups_merge_every_list() {
        let mut vocab = Vocab::with_capacity(4);
        assert!(vocab.insert("dupont", flag::NAME, Some(300)));
        assert!(vocab.insert("dupont", flag::COMMUNE, None));
        assert!(vocab.insert("le", flag::PARTICLE, None));
        assert!(vocab.insert("le", flag::DETERMINER, None));
        assert!(vocab.insert("à", flag::LOCATIVE, None));
        assert_eq!(vocab.keys, 3);
        let dupont = vocab.get(&v("dupont"));
        assert_eq!(dupont.name(), Some(300));
        assert!(dupont.has(flag::COMMUNE) && !dupont.has(flag::WORD));
        assert!(vocab.get(&v("le")).has(flag::DETERMINER));
        assert!(vocab.get(&v("à")).has(flag::LOCATIVE) && !vocab.get(&v("a")).has(flag::LOCATIVE));
        assert_eq!(vocab.get(&v("absent")).name(), None);
        assert_eq!(vocab.get(&[]).name(), None);
    }

    #[test]
    fn many_keys_are_all_found_and_capacity_is_bounded() {
        let mut vocab = Vocab::with_capacity(5000);
        for i in 0..5000u16 {
            assert!(vocab.insert(&format!("k{i}"), flag::NAME, Some(i)));
        }
        for i in 0..5000u16 {
            assert_eq!(vocab.get(&v(&format!("k{i}"))).name(), Some(i));
        }
        assert_eq!(vocab.get(&v("k5000")).name(), None);
        let mut small = Vocab::with_capacity(1);
        let accepted = (0..100).filter(|i| small.insert(&format!("w{i}"), flag::WORD, None)).count();
        assert_eq!(accepted, 8); // 16 alvéoles, charge ≤ 1/2 / 16 slots, load ≤ 1/2
        let mut fresh = Vocab::with_capacity(1);
        assert!(!fresh.insert(&"x".repeat(70_000), flag::WORD, None)); // clé démesurée / oversized key
    }
}
