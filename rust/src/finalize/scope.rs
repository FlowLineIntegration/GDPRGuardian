//! Portée irréversible : empreintes BLAKE2b à clé, numérotation cohérente, coréférence des personnes.
//!
//! Irreversible scope: keyed BLAKE2b digests, consistent numbering, person coreference (`scope.Scope`).
//! La clé de 256 bits est tirée par le système, ne quitte jamais Rust et n'existe qu'à travers un état
//! BLAKE2b déjà clé, effacé (zeroize) à la fermeture : personne ne peut ensuite relier une balise à une
//! valeur. The 256-bit key is drawn by the OS, never leaves Rust and lives only inside a pre-keyed BLAKE2b
//! state that is wiped (zeroize) on close: nobody can then link a placeholder back to a value.

use std::borrow::Cow;
use std::collections::{HashMap, HashSet};
use std::fmt::Write;
use std::hash::{BuildHasherDefault, Hash, Hasher};

use blake2::digest::block_api::{Block, Buffer, UpdateCore, VariableOutputCore};
use blake2::digest::Output;
use blake2::Blake2bVarCore;
use zeroize::{Zeroize, Zeroizing};

use super::chars::{Chars, ALNUM, DECIMAL, SPACE};

const KEY_SIZE: usize = 32;
const DIGEST_SIZE: usize = 16;

/// BLAKE2b-128 à clé, comme `hashlib.blake2b(key=…, digest_size=16)`, dont le bloc de clé est compressé une
/// seule fois : chaque empreinte coûte une compression au lieu de deux (les messages ne sont jamais vides).
/// Keyed BLAKE2b-128, as `hashlib.blake2b(key=…, digest_size=16)`, whose key block is compressed once:
/// each digest costs one compression instead of two (messages are never empty). L'état est effacé à sa
/// destruction (fonction « zeroize » de blake2) / the state is wiped when dropped.
#[derive(Clone)]
struct Keyed(Blake2bVarCore);

impl Keyed {
    fn new(key: &[u8; KEY_SIZE]) -> Self {
        let mut core = Blake2bVarCore::new_with_params(&[], &[], KEY_SIZE, DIGEST_SIZE);
        // Construction à clé de BLAKE2b : la clé complétée de zéros forme le premier bloc.
        // BLAKE2b keyed mode: the zero-padded key is the first block.
        let mut block = Block::<Blake2bVarCore>::default();
        block.iter_mut().zip(key).for_each(|(slot, byte)| *slot = *byte);
        core.update_blocks(std::slice::from_ref(&block));
        block.as_mut_slice().zeroize();
        Self(core)
    }

    /// Empreinte de la concaténation des morceaux / digest of the concatenated parts.
    fn digest(&self, parts: &[&[u8]]) -> Digest {
        let mut core = self.0.clone();
        let mut buffer = Buffer::<Blake2bVarCore>::default();
        for part in parts {
            buffer.digest_blocks(part, |blocks| core.update_blocks(blocks));
        }
        let mut full = Output::<Blake2bVarCore>::default();
        core.finalize_variable_core(&mut buffer, &mut full);
        let mut digest = [0u8; DIGEST_SIZE];
        digest.iter_mut().zip(full.iter()).for_each(|(slot, byte)| *slot = *byte);
        Digest(digest)
    }
}

/// Empreinte à clé de 128 bits ; jamais exposée à Python / 128-bit keyed digest, never exposed to Python.
#[derive(Clone, Copy, PartialEq, Eq)]
struct Digest([u8; 16]);

impl Hash for Digest {
    fn hash<H: Hasher>(&self, state: &mut H) {
        let [a, b, c, d, e, f, g, h, ..] = self.0;
        state.write_u64(u64::from_le_bytes([a, b, c, d, e, f, g, h]));
    }
}

/// Hachage identité : sortie d'une fonction pseudo-aléatoire à clé secrète, déjà uniforme et imprévisible
/// (aucune collision provoquée sans la clé). Identity hashing: the output of a secret-keyed PRF is already
/// uniform and unpredictable (no crafted collisions without the key).
#[derive(Default)]
struct DigestHasher(u64);

impl Hasher for DigestHasher {
    fn finish(&self) -> u64 {
        self.0
    }

    fn write(&mut self, bytes: &[u8]) {
        for &byte in bytes {
            self.0 = self.0.rotate_left(8) ^ u64::from(byte);
        }
    }

    fn write_u64(&mut self, value: u64) {
        self.0 = value;
    }
}

type DigestMap<V> = HashMap<Digest, V, BuildHasherDefault<DigestHasher>>;

/// Portée fermée (`RuntimeError` en Python) / closed scope (`RuntimeError` in Python).
#[derive(Debug, PartialEq, Eq)]
pub struct ScopeClosed;

struct Cluster {
    surname: Digest,
    given: Option<Digest>,
    initial: Option<Digest>,
}

pub struct Scope {
    /// État déjà clé, copié pour chaque empreinte ; `None` une fois fermée (effacé à la destruction).
    /// Pre-keyed state copied per digest; `None` once closed (wiped when dropped).
    keyed: Option<Keyed>,
    indices: DigestMap<u64>,
    counters: HashMap<String, u64>,
    reserved: HashMap<String, HashSet<u64>>,
    clusters: Vec<Cluster>,
    by_surname: DigestMap<Vec<usize>>,
    by_given: DigestMap<Vec<usize>>,
}

impl Scope {
    /// Nouvelle portée, clé tirée par le système d'exploitation / new scope, key drawn by the OS.
    pub fn new() -> Result<Self, String> {
        let mut key = Zeroizing::new([0u8; KEY_SIZE]);
        getrandom::fill(&mut key[..]).map_err(|e| format!("aléa système indisponible / no OS randomness: {e}"))?;
        Ok(Self::with_key(&key))
    }

    fn with_key(key: &[u8; KEY_SIZE]) -> Self {
        Self {
            keyed: Some(Keyed::new(key)),
            indices: DigestMap::default(),
            counters: HashMap::new(),
            reserved: HashMap::new(),
            clusters: Vec::new(),
            by_surname: DigestMap::default(),
            by_given: DigestMap::default(),
        }
    }

    pub fn closed(&self) -> bool {
        self.keyed.is_none()
    }

    /// Efface la clé et les empreintes / wipes the key and the digests.
    pub fn close(&mut self) {
        // L'état BLAKE2b déjà clé est effacé à sa destruction (fonction « zeroize » de blake2).
        // The pre-keyed BLAKE2b state is wiped when dropped (blake2's "zeroize" feature).
        self.keyed = None;
        for cluster in &mut self.clusters {
            for digest in
                [Some(&mut cluster.surname), cluster.given.as_mut(), cluster.initial.as_mut()].into_iter().flatten()
            {
                digest.0.zeroize();
            }
        }
        self.clusters = Vec::new();
        self.indices = DigestMap::default();
        self.counters = HashMap::new();
        self.reserved = HashMap::new();
        self.by_surname = DigestMap::default();
        self.by_given = DigestMap::default();
    }

    fn digest(&self, kind: &str, value: &str) -> Result<Digest, ScopeClosed> {
        // Même entrée qu'en Python : f"{kind}\x1f{value}" en UTF-8 / same input as Python.
        Ok(self.keyed.as_ref().ok_or(ScopeClosed)?.digest(&[kind.as_bytes(), b"\x1f", value.as_bytes()]))
    }

    /// Réserve les balises déjà présentes dans l'entrée (`PLACEHOLDER_RE`) / reserves existing placeholders.
    pub fn reserve(&mut self, text: &str) {
        let bytes = text.as_bytes();
        let mut pos = 0;
        while let Some(open) = bytes.get(pos..).and_then(|rest| rest.iter().position(|&b| b == b'[')) {
            let open = pos + open;
            match placeholder_at(bytes, open) {
                Some((label, index, end)) => {
                    self.reserved.entry(label.to_owned()).or_default().insert(index);
                    pos = end;
                }
                None => pos = open + 1,
            }
        }
    }

    fn next_index(&mut self, display: &str) -> u64 {
        let mut index = self.counters.get(display).copied().unwrap_or(0) + 1;
        if let Some(reserved) = self.reserved.get(display) {
            while reserved.contains(&index) {
                index += 1;
            }
        }
        match self.counters.get_mut(display) {
            Some(counter) => *counter = index,
            None => {
                self.counters.insert(display.to_owned(), index);
            }
        }
        index
    }

    /// `Scope.placeholder` : balise numérotée, cohérente dans la portée / consistent numbered placeholder.
    pub fn placeholder(
        &mut self,
        chars: &Chars,
        display: &str,
        entity: &str,
        value: &str,
    ) -> Result<String, ScopeClosed> {
        let mut out = String::new();
        self.placeholder_into(chars, display, entity, value, &mut out)?;
        Ok(out)
    }

    /// `Scope.placeholder`, écrite à la suite de `out`. La clé canonique (`f"{libellé}\x1f{clé}"`) est hachée
    /// par morceaux, repliée sur la pile : aucune allocation pour un nom ou une valeur courte. Written at the
    /// end of `out`; the canonical key is hashed piece by piece, folded on the stack: no allocation for a short
    /// name or value.
    pub fn placeholder_into(
        &mut self,
        chars: &Chars,
        display: &str,
        entity: &str,
        value: &str,
        out: &mut String,
    ) -> Result<(), ScopeClosed> {
        let label = display.as_bytes();
        let digest = if entity == "PERSON" {
            match self.person(chars, value)? {
                Some(PersonKey::Cluster(index)) => {
                    let mut digits = [0u8; 20];
                    self.digest_parts(&[label, b"\x1fp", decimal(index, &mut digits)])?
                }
                Some(PersonKey::Surname(surname)) => self.digest_parts(&[label, b"\x1fs\x1f", &surname.hex()])?,
                None => {
                    self.digest_parts(&[label, b"\x1fraw\x1f", canonical_text(chars, value).as_str().as_bytes()])?
                }
            }
        } else {
            self.digest_parts(&[label, b"\x1f", canonical_text(chars, value).as_str().as_bytes()])?
        };
        let index = self.index_of(display, digest);
        // Écrire dans une `String` n'échoue pas / writing into a `String` cannot fail.
        let _ = write!(out, "[{display}_{index}]");
        Ok(())
    }

    /// Numéro de la clé canonique pour ce libellé / number of the canonical key for this label.
    pub fn numbered(&mut self, display: &str, key: &str) -> Result<String, ScopeClosed> {
        let digest = self.digest(display, key)?;
        let index = self.index_of(display, digest);
        Ok(format!("[{display}_{index}]"))
    }

    /// Numéro d'une empreinte : le sien, ou le suivant libre du libellé / a digest's number, or the next free one.
    fn index_of(&mut self, display: &str, digest: Digest) -> u64 {
        match self.indices.get(&digest) {
            Some(&index) => index,
            None => {
                let index = self.next_index(display);
                self.indices.insert(digest, index);
                index
            }
        }
    }

    /// Empreinte de la concaténation des morceaux / digest of the concatenated parts.
    fn digest_parts(&self, parts: &[&[u8]]) -> Result<Digest, ScopeClosed> {
        Ok(self.keyed.as_ref().ok_or(ScopeClosed)?.digest(parts))
    }

    /// `digest(kind, fold(text))`, replié sur la pile / folded on the stack.
    fn digest_folded(&self, chars: &Chars, kind: &str, text: &str) -> Result<Digest, ScopeClosed> {
        let mut folded = StackText::new();
        chars.folded(text).for_each(|c| folded.push(c));
        self.digest_parts(&[kind.as_bytes(), b"\x1f", folded.as_str().as_bytes()])
    }

    fn given_of(&self, cluster: usize) -> Option<Digest> {
        self.clusters.get(cluster).and_then(|c| c.given)
    }

    fn initial_of(&self, cluster: usize) -> Option<Digest> {
        self.clusters.get(cluster).and_then(|c| c.initial)
    }

    /// `Scope.person_key` : « M. Dupont », « Jean Dupont », « J. Dupont », « DUPONT Jean » -> même grappe.
    /// Same cluster for name variants; `None` when no name is recognisable (raw key, computed by the caller).
    pub fn person_key(&mut self, chars: &Chars, text: &str) -> Result<Option<String>, ScopeClosed> {
        Ok(self.person(chars, text)?.map(|key| key.text()))
    }

    /// Clé de personne de `person_key` / `person_key`'s person key.
    fn person(&mut self, chars: &Chars, text: &str) -> Result<Option<PersonKey>, ScopeClosed> {
        let Some((given, surname)) = split_name(chars, text) else {
            return Ok(None);
        };
        let cluster = |index: usize| Ok(Some(PersonKey::Cluster(index)));
        let surname_digest = self.digest_folded(chars, "s", &surname)?;
        let candidates: Vec<usize> = self.by_surname.get(&surname_digest).cloned().unwrap_or_default();
        let Some(given) = given else {
            if let [only] = candidates[..] {
                return cluster(only);
            }
            if candidates.is_empty() {
                let by_given = self.digest_folded(chars, "g", &surname)?;
                if let Some(&[only]) = self.by_given.get(&by_given).map(Vec::as_slice) {
                    return cluster(only);
                }
                return cluster(self.new_cluster(surname_digest, None, None));
            }
            return Ok(Some(PersonKey::Surname(surname_digest)));
        };
        let first = given.get(..given.chars().next().map_or(0, char::len_utf8)).unwrap_or_default();
        let initial = self.digest_folded(chars, "i", first)?;
        if given.chars().nth(1).is_none() {
            let matches: Vec<usize> =
                candidates.iter().copied().filter(|&c| self.initial_of(c) == Some(initial)).collect();
            if let [only] = matches[..] {
                return cluster(only);
            }
            let bare: Vec<usize> = candidates.iter().copied().filter(|&c| self.given_of(c).is_none()).collect();
            if let ([], [only], [_]) = (&matches[..], &bare[..], &candidates[..]) {
                if let Some(entry) = self.clusters.get_mut(*only) {
                    entry.initial = Some(initial);
                }
                return cluster(*only);
            }
            return cluster(self.new_cluster(surname_digest, None, Some(initial)));
        }
        let given_digest = self.digest_folded(chars, "g", given)?;
        if let Some(&found) = candidates.iter().find(|&&c| self.given_of(c) == Some(given_digest)) {
            return cluster(found);
        }
        let upgradable: Vec<usize> = candidates
            .iter()
            .copied()
            .filter(|&c| self.given_of(c).is_none() && self.initial_of(c).is_none_or(|i| i == initial))
            .collect();
        if let ([only], [_]) = (&upgradable[..], &candidates[..]) {
            return cluster(self.set_given(*only, given_digest, initial));
        }
        // Un prénom vu seul (« Bonjour Pierre ») rejoint la personne complète / a lone given name joins.
        let alone_digest = self.digest_folded(chars, "s", given)?;
        let alone: Vec<usize> = self
            .by_surname
            .get(&alone_digest)
            .map(|list| list.iter().copied().filter(|&c| self.given_of(c).is_none()).collect())
            .unwrap_or_default();
        if let ([only], true) = (&alone[..], candidates.is_empty()) {
            let only = *only;
            if let Some(old) = self.clusters.get(only).map(|c| c.surname) {
                if let Some(list) = self.by_surname.get_mut(&old) {
                    if let Some(position) = list.iter().position(|&c| c == only) {
                        list.remove(position);
                    }
                }
            }
            if let Some(entry) = self.clusters.get_mut(only) {
                entry.surname = surname_digest;
            }
            self.by_surname.entry(surname_digest).or_default().push(only);
            return cluster(self.set_given(only, given_digest, initial));
        }
        cluster(self.new_cluster(surname_digest, Some(given_digest), Some(initial)))
    }

    fn new_cluster(&mut self, surname: Digest, given: Option<Digest>, initial: Option<Digest>) -> usize {
        let index = self.clusters.len();
        self.clusters.push(Cluster { surname, given, initial });
        self.by_surname.entry(surname).or_default().push(index);
        if let Some(given) = given {
            self.by_given.entry(given).or_default().push(index);
        }
        index
    }

    fn set_given(&mut self, index: usize, given: Digest, initial: Digest) -> usize {
        if let Some(entry) = self.clusters.get_mut(index) {
            entry.given = Some(given);
            entry.initial = Some(initial);
        }
        self.by_given.entry(given).or_default().push(index);
        index
    }
}

impl Drop for Scope {
    fn drop(&mut self) {
        self.close();
    }
}

/// `PLACEHOLDER_RE` (`\[([A-Z][A-Z0-9_]*[A-Z0-9])_([1-9][0-9]{0,6})\]`) à un « [ » : (libellé, numéro, fin).
/// The pattern at an opening bracket: (label, number, end). Le corps ne contient que [A-Z0-9_] ; le numéro
/// suit forcément le dernier « _ » (aucun « _ » dans les chiffres). The number necessarily follows the last "_".
fn placeholder_at(bytes: &[u8], open: usize) -> Option<(&str, u64, usize)> {
    let body_start = open + 1;
    let length = bytes
        .get(body_start..)?
        .iter()
        .take_while(|&&b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
        .count();
    let close = body_start + length;
    if bytes.get(close) != Some(&b']') {
        return None;
    }
    let body = bytes.get(body_start..close)?;
    let underscore = body.iter().rposition(|&b| b == b'_')?;
    let (label, digits) = (body.get(..underscore)?, body.get(underscore + 1..)?);
    let [first, .., last] = label else {
        return None;
    };
    let [lead, rest @ ..] = digits else {
        return None;
    };
    if !first.is_ascii_uppercase() || *last == b'_' || !(b'1'..=b'9').contains(lead) || rest.len() > 6 {
        return None;
    }
    let number = digits.iter().try_fold(0u64, |n, &d| d.is_ascii_digit().then(|| n * 10 + u64::from(d - b'0')))?;
    Some((std::str::from_utf8(label).ok()?, number, close + 1))
}

/// Texte court écrit sur la pile, repli sur le tas au-delà : une clé se hache sans allocation ni copie durable.
/// Short text written on the stack, heap beyond: a key is hashed without allocation nor lasting copy.
struct StackText {
    bytes: [u8; 192],
    len: usize,
    spilled: Option<String>,
}

impl StackText {
    fn new() -> Self {
        Self { bytes: [0; 192], len: 0, spilled: None }
    }

    fn push(&mut self, c: char) {
        if let Some(spilled) = &mut self.spilled {
            spilled.push(c);
            return;
        }
        let width = c.len_utf8();
        match self.bytes.get_mut(self.len..self.len + width) {
            Some(slot) => {
                c.encode_utf8(slot);
                self.len += width;
            }
            None => {
                let mut spilled = String::with_capacity(2 * (self.len + width));
                spilled.push_str(self.as_str());
                spilled.push(c);
                self.spilled = Some(spilled);
            }
        }
    }

    fn as_str(&self) -> &str {
        match &self.spilled {
            Some(spilled) => spilled,
            // Seuls des caractères entiers y sont écrits / only whole characters are written there.
            None => std::str::from_utf8(self.bytes.get(..self.len).unwrap_or_default()).unwrap_or_default(),
        }
    }
}

/// Clé d'une personne dans la portée / a person's key within the scope.
enum PersonKey {
    /// Grappe : « p<n> » / cluster: "p<n>".
    Cluster(usize),
    /// Nom seul porté par plusieurs grappes : « s\x1f<empreinte> » / bare surname of several clusters.
    Surname(Digest),
}

impl PersonKey {
    /// Forme textuelle de `Scope.person_key` (Python) / text form of the Python `Scope.person_key`.
    fn text(&self) -> String {
        match self {
            Self::Cluster(index) => format!("p{index}"),
            Self::Surname(digest) => format!("s\x1f{}", std::str::from_utf8(&digest.hex()).unwrap_or_default()),
        }
    }
}

impl Digest {
    /// Hexadécimal minuscule, comme `bytes.hex()` / lowercase hexadecimal, as `bytes.hex()`.
    fn hex(&self) -> [u8; 2 * DIGEST_SIZE] {
        const DIGITS: &[u8; 16] = b"0123456789abcdef";
        let mut hex = [0u8; 2 * DIGEST_SIZE];
        for (pair, byte) in hex.as_chunks_mut::<2>().0.iter_mut().zip(self.0) {
            *pair = [DIGITS[usize::from(byte >> 4)], DIGITS[usize::from(byte & 0x0F)]];
        }
        hex
    }
}

/// Écriture décimale d'un entier dans `buffer` / decimal digits of an integer, written into `buffer`.
fn decimal(mut value: usize, buffer: &mut [u8; 20]) -> &[u8] {
    let mut start = buffer.len();
    loop {
        start -= 1;
        buffer[start] = b'0' + (value % 10) as u8;
        value /= 10;
        if value == 0 {
            return &buffer[start..];
        }
    }
}

/// `re.sub(r"\s+", " ", fold(value)).strip()` en une passe : une espace seulement entre deux mots.
/// In one pass: a single space only between two words.
fn canonical_into(chars: &Chars, value: &str, mut push: impl FnMut(char)) {
    let (mut started, mut space) = (false, false);
    for c in chars.folded(value) {
        if chars.is(c, SPACE) {
            space = started;
        } else {
            if space {
                push(' ');
                space = false;
            }
            push(c);
            started = true;
        }
    }
}

/// `scope._canonical` : repli, espaces fusionnés, rognage, écrit sur la pile / fold, collapsed spaces, stripped,
/// written on the stack.
fn canonical_text(chars: &Chars, value: &str) -> StackText {
    let mut out = StackText::new();
    canonical_into(chars, value, |c| out.push(c));
    out
}

/// Lettre au sens de `[^\W\d_]` (Python) : alphanumérique mais pas un chiffre décimal / alnum, not decimal.
fn is_letter(chars: &Chars, c: char) -> bool {
    chars.flags(c) & (ALNUM | DECIMAL) == ALNUM
}

/// `_NAME_TOKEN_RE.findall` : `[^\W\d_]+(?:[\-'][^\W\d_]+)*\.?`, puis `t.rstrip(".")` et les vides retirés.
/// Then `t.rstrip(".")`, empty tokens removed.
fn name_tokens<'t>(chars: &Chars, text: &'t str) -> Vec<&'t str> {
    let letters_end = |from: usize| -> usize {
        text.get(from..).map_or(from, |rest| {
            from + rest.chars().take_while(|&c| is_letter(chars, c)).map(char::len_utf8).sum::<usize>()
        })
    };
    let char_at = |pos: usize| text.get(pos..).and_then(|rest| rest.chars().next());
    let mut tokens = Vec::new();
    let mut pos = 0;
    while let Some(c) = char_at(pos) {
        if !is_letter(chars, c) {
            pos += c.len_utf8();
            continue;
        }
        let start = pos;
        pos = letters_end(pos);
        while let Some(sep @ ('-' | '\'')) = char_at(pos) {
            match char_at(pos + sep.len_utf8()) {
                Some(next) if is_letter(chars, next) => pos = letters_end(pos + sep.len_utf8()),
                _ => break,
            }
        }
        // Le point final ne fait pas partie du jeton retenu / the final dot is not part of the kept token.
        let token = text.get(start..pos).unwrap_or("").trim_end_matches('.');
        if char_at(pos) == Some('.') {
            pos += 1;
        }
        if !token.is_empty() {
            tokens.push(token);
        }
    }
    tokens
}

/// `scope.split_person_name` : (prénom ou rien, nom) ; le nom est en capitales s'il y en a.
/// (given or none, surname); the surname is the uppercase part when there is one.
pub fn split_person_name(chars: &Chars, text: &str) -> Option<(Option<String>, String)> {
    split_name(chars, text).map(|(given, surname)| (given.map(str::to_owned), surname.into_owned()))
}

/// `split_person_name`, empruntés au texte (seul un nom de plusieurs mots en capitales est assemblé).
/// Borrowed from the text (only a multi-word uppercase surname is assembled).
fn split_name<'t>(chars: &Chars, text: &'t str) -> Option<(Option<&'t str>, Cow<'t, str>)> {
    let tokens = name_tokens(chars, text);
    let skip = tokens.iter().take_while(|t| chars.is_honorific(t)).count();
    let tokens = tokens.get(skip..).unwrap_or(&[]);
    // Une particule en tête n'est pas un prénom (« Le Verger » : le nom seul), tant qu'un mot suit.
    // A leading particle is not a given name ("Le Verger": the surname alone), while a word follows.
    let lead = tokens.iter().take(tokens.len().saturating_sub(1)).take_while(|t| chars.is_particle(t)).count();
    let tokens = &tokens[lead..];
    match *tokens {
        [] => None,
        [only] => Some((None, Cow::Borrowed(only))),
        [first, .., last] => {
            let upper = |t: &str| t.chars().nth(1).is_some() && chars.is_upper(t);
            let mut capitals = tokens.iter().copied().filter(|t| upper(t));
            let count = capitals.clone().count();
            if count > 0 && count < tokens.len() {
                if let Some(&given) = tokens.iter().find(|t| !upper(t)) {
                    let surname = match (capitals.next(), count) {
                        (Some(only), 1) => Cow::Borrowed(only),
                        _ => Cow::Owned(tokens.iter().copied().filter(|t| upper(t)).collect::<Vec<&str>>().join(" ")),
                    };
                    return Some((Some(given), surname));
                }
            }
            Some((Some(first), Cow::Borrowed(last)))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::finalize::chars::test_rules;

    fn with<T>(f: impl FnOnce(&Chars) -> T) -> T {
        let rules = test_rules();
        f(&Chars::new(&rules))
    }

    #[test]
    fn same_construction_as_python_hashlib() {
        // hashlib.blake2b(b"PERSONNE\x1fp0", key=bytes(range(32)), digest_size=16).hexdigest()
        let key: [u8; 32] = std::array::from_fn(|i| i as u8);
        let scope = Scope::with_key(&key);
        let hex = |kind: &str, value: &str| -> String {
            scope.digest(kind, value).expect("open").0.iter().map(|b| format!("{b:02x}")).collect()
        };
        assert_eq!(hex("PERSONNE", "p0"), "4a73fde1e7c1f761e30690e2cbda941a");
        // Message de 128 octets exactement, puis sur plusieurs blocs / exactly one block, then several blocks.
        assert_eq!(hex("AB", &"y".repeat(125)), "7a8e4ab232eff404c8618a10d3febdb1");
        assert_eq!(hex("s", &"x".repeat(300)), "9ee3ce4b691d2bf00a20d146ec24d646");
        assert_eq!(hex("EMAIL", &"é".repeat(100)), "9af65b1dbe49592e1be7aaa52a35e408");
    }

    #[test]
    fn name_variants_share_one_placeholder() {
        with(|chars| {
            let mut scope = Scope::new().expect("randomness");
            let first = scope.placeholder(chars, "PERSONNE", "PERSON", "Jean Dupont").expect("open");
            for variant in ["M. Dupont", "J. Dupont", "DUPONT Jean", "jean dupont"] {
                assert_eq!(scope.placeholder(chars, "PERSONNE", "PERSON", variant).expect("open"), first);
            }
            assert_ne!(scope.placeholder(chars, "PERSONNE", "PERSON", "Claire Martin").expect("open"), first);
        });
    }

    #[test]
    fn reserved_numbers_are_skipped_and_closing_wipes() {
        with(|chars| {
            let mut scope = Scope::new().expect("randomness");
            scope.reserve("[PERSONNE_1] [PERSONNE_2] [X_0] [A_B_12345678] [[EMAIL_3]");
            assert_eq!(scope.placeholder(chars, "PERSONNE", "PERSON", "Jean Dupont"), Ok("[PERSONNE_3]".into()));
            assert_eq!(scope.placeholder(chars, "EMAIL", "EMAIL", "a@b.fr"), Ok("[EMAIL_1]".into()));
            assert_eq!(scope.placeholder(chars, "EMAIL", "EMAIL", "c@d.fr"), Ok("[EMAIL_2]".into()));
            assert_eq!(scope.placeholder(chars, "EMAIL", "EMAIL", "C@D.FR"), Ok("[EMAIL_2]".into()));
            assert_eq!(scope.placeholder(chars, "EMAIL", "EMAIL", "e@f.fr"), Ok("[EMAIL_4]".into()));
            scope.close();
            assert!(scope.closed());
            assert_eq!(scope.placeholder(chars, "EMAIL", "EMAIL", "a@b.fr"), Err(ScopeClosed));
        });
    }

    #[test]
    fn placeholder_pattern() {
        let at = |text: &str| placeholder_at(text.as_bytes(), 0).map(|(label, number, _)| (label.to_owned(), number));
        assert_eq!(at("[NOM_A_12]"), Some(("NOM_A".into(), 12)));
        assert_eq!(at("[A1_9999999]"), Some(("A1".into(), 9_999_999)));
        assert_eq!(at("[A_1]"), None);
        assert_eq!(at("[AB_01]"), None);
        assert_eq!(at("[AB__1]"), None);
        assert_eq!(at("[AB_12345678]"), None);
        assert_eq!(at("[AB_1"), None);
    }

    #[test]
    fn person_names() {
        with(|chars| {
            let split = |text: &str| split_person_name(chars, text);
            assert_eq!(split("M. Jean Dupont"), Some((Some("Jean".into()), "Dupont".into())));
            assert_eq!(split("DUPONT Jean"), Some((Some("Jean".into()), "DUPONT".into())));
            assert_eq!(split("Mme Martin"), Some((None, "Martin".into())));
            assert_eq!(split("J. Dupont"), Some((Some("J".into()), "Dupont".into())));
            assert_eq!(split("Jean-Pierre O'Neil-"), Some((Some("Jean-Pierre".into()), "O'Neil".into())));
            assert_eq!(split("42 !"), None);
            assert_eq!(canonical_text(chars, "  A\t\n B  ").as_str(), "a b");
            // Au-delà du tampon de pile, repli sur le tas / beyond the stack buffer, the heap.
            let long = "Ab ".repeat(100);
            assert_eq!(canonical_text(chars, &long).as_str(), "ab ".repeat(100).trim_end());
            assert_eq!(decimal(0, &mut [0; 20]), b"0");
            assert_eq!(decimal(usize::MAX, &mut [0; 20]), usize::MAX.to_string().as_bytes());
        });
    }
}
