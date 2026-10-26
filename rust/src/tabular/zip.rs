//! Archive ZIP stricte, en lecture seule / strict, read-only ZIP archive.
//!
//! Seules les archives sans ambiguïté sont acceptées : une seule fin de répertoire, exactement en fin de
//! fichier, répertoire central contigu, ni ZIP64, ni chiffrement, ni noms non ASCII, ni doublons (casse
//! ignorée), méthodes « stockée » ou « deflate » seulement. Bornes de la garde Python : nombre d'entrées,
//! taille décompressée totale et par partie, taux de compression ; taille réelle et CRC vérifiés.
//! Only unambiguous archives are accepted: a single end record, exactly at the end of the file, a contiguous
//! central directory, no ZIP64, no encryption, no non-ASCII names, no duplicates (case ignored), stored or
//! deflate only. The Python guard's bounds: entry count, total and per-part inflated size, compression ratio;
//! real size and CRC checked.

use std::collections::HashMap;

use flate2::{Decompress, FlushDecompress, Status};

use super::{Decline, Result};

const END_SIGNATURE: &[u8] = b"PK\x05\x06";
const CENTRAL_SIGNATURE: &[u8] = b"PK\x01\x02";
const LOCAL_SIGNATURE: &[u8] = b"PK\x03\x04";
const ZIP64_LOCATOR: &[u8] = b"PK\x06\x07";
const END_LEN: usize = 22;
const CENTRAL_LEN: usize = 46;
const LOCAL_LEN: usize = 30;
/// Mêmes bornes que `gdprguardian.tabular._package` / same bounds as the Python guard.
const MAX_ENTRIES: usize = 2_000;
const MAX_TOTAL: u64 = 200 * 1024 * 1024;
pub(crate) const MAX_PART: u64 = 64 * 1024 * 1024;
const MAX_RATIO: u64 = 100;
const RATIO_FLOOR: u64 = 1 << 20;

/// Entrée du répertoire central / central directory entry.
struct Entry {
    method: u16,
    crc: u32,
    compressed: usize,
    size: u64,
    /// En-tête local, puis début des données / local header, then start of the data.
    local: usize,
    data: usize,
    /// Nom en minuscules / lowercased name.
    key: Box<str>,
}

/// Identité d'une partie : nom en minuscules, taille décompressée, CRC (ceux de `zipfile`).
/// Identity of a part: lowercased name, inflated size, CRC (as `zipfile` reports them).
pub(crate) type PartIdentity = (String, u64, u32);

/// Répertoire d'une archive, sans les données / archive directory, without the data.
pub(crate) struct Directory {
    entries: Vec<Entry>,
    /// Nom en minuscules -> entrée, comme le cache de chemins de calamine / lowercased name -> entry.
    by_key: HashMap<Box<str>, usize>,
}

fn u16_at(data: &[u8], at: usize) -> Result<u16> {
    data.get(at..at + 2).map(|b| u16::from_le_bytes([b[0], b[1]])).ok_or(Decline("zip: truncated record"))
}

fn u32_at(data: &[u8], at: usize) -> Result<u32> {
    data.get(at..at + 4).map(|b| u32::from_le_bytes([b[0], b[1], b[2], b[3]])).ok_or(Decline("zip: truncated record"))
}

impl Directory {
    /// Lit et contrôle le répertoire central / reads and checks the central directory.
    pub(crate) fn open(data: &[u8]) -> Result<Self> {
        let end = end_record(data)?;
        let entries_here = u16_at(data, end + 8)? as usize;
        let entries_total = u16_at(data, end + 10)? as usize;
        let central_size = u32_at(data, end + 12)? as usize;
        let central_start = u32_at(data, end + 16)? as usize;
        if u16_at(data, end + 4)? != 0 || u16_at(data, end + 6)? != 0 || entries_here != entries_total {
            return Err(Decline("zip: multi-disk archive"));
        }
        if entries_total == 0xFFFF || central_size == 0xFFFF_FFFF || central_start == 0xFFFF_FFFF {
            return Err(Decline("zip: zip64"));
        }
        if entries_total > MAX_ENTRIES {
            return Err(Decline("zip: too many entries"));
        }
        if central_start.checked_add(central_size) != Some(end) {
            return Err(Decline("zip: central directory not contiguous"));
        }
        let mut entries = Vec::with_capacity(entries_total);
        let mut by_key = HashMap::with_capacity(entries_total);
        let mut position = central_start;
        let mut total = 0u64;
        for _ in 0..entries_total {
            let (entry, next) = central_entry(data, position, end)?;
            total = total.saturating_add(entry.size);
            if by_key.insert(entry.key.clone(), entries.len()).is_some() {
                return Err(Decline("zip: duplicate entry"));
            }
            entries.push(entry);
            position = next;
        }
        if position != end || total > MAX_TOTAL {
            return Err(Decline("zip: inconsistent directory"));
        }
        // Données qui empiètent sur l'en-tête suivant ou le répertoire : `zipfile` refuse de les lire
        // (« Overlapped entries »). Data running into the next header or the directory: `zipfile` refuses them.
        let mut order: Vec<usize> = (0..entries.len()).collect();
        order.sort_by_key(|&i| entries[i].local);
        for (rank, &i) in order.iter().enumerate() {
            let bound = order.get(rank + 1).map_or(central_start, |&next| entries[next].local);
            if entries[i].data + entries[i].compressed > bound {
                return Err(Decline("zip: overlapping entries"));
            }
        }
        Ok(Self { entries, by_key })
    }

    /// Identité de l'entrée lue / identity of the entry read.
    pub(crate) fn identity(&self, index: usize) -> Option<PartIdentity> {
        self.entries.get(index).map(|entry| (entry.key.to_string(), entry.size, entry.crc))
    }

    /// Partie au chemin donné, casse ignorée (`cached_zip_path` de calamine) / part at a path, case ignored.
    pub(crate) fn find(&self, path: &str) -> Option<usize> {
        self.by_key.get(path.to_ascii_lowercase().as_str()).copied()
    }

    /// Lecteur en flux d'une partie / streaming reader of a part.
    pub(crate) fn reader<'a>(&self, data: &'a [u8], index: usize) -> Result<EntryReader<'a>> {
        let entry = self.entries.get(index).ok_or(Decline("zip: no such entry"))?;
        if entry.size > MAX_PART {
            return Err(Decline("zip: part too large"));
        }
        let input = data.get(entry.data..entry.data + entry.compressed).ok_or(Decline("zip: truncated data"))?;
        let inflater = match entry.method {
            0 if entry.compressed as u64 == entry.size => None,
            8 => Some(Box::new(Decompress::new(false))),
            _ => return Err(Decline("zip: unsupported method")),
        };
        Ok(EntryReader {
            input,
            position: 0,
            inflater,
            crc: crc32fast::Hasher::new(),
            produced: 0,
            size: entry.size,
            expected_crc: entry.crc,
            done: false,
        })
    }
}

/// Fin de répertoire : une seule signature candidate, dont le commentaire va jusqu'à la fin du fichier.
/// End record: a single candidate signature whose comment runs exactly to the end of the file.
fn end_record(data: &[u8]) -> Result<usize> {
    let floor = data.len().saturating_sub(END_LEN + 0xFFFF);
    let mut found = None;
    let mut at = data.len().saturating_sub(END_LEN) + 1;
    while at > floor {
        at -= 1;
        if data.get(at..at + 4) == Some(END_SIGNATURE) && at + END_LEN + u16_at(data, at + 20)? as usize == data.len() {
            if found.is_some() {
                return Err(Decline("zip: ambiguous end record"));
            }
            found = Some(at);
        }
    }
    let end = found.ok_or(Decline("zip: no end record"))?;
    if end >= 20 && data.get(end - 20..end - 16) == Some(ZIP64_LOCATOR) {
        return Err(Decline("zip: zip64"));
    }
    Ok(end)
}

/// Entrée centrale et position suivante / central entry and the next position.
fn central_entry(data: &[u8], at: usize, limit: usize) -> Result<(Entry, usize)> {
    if data.get(at..at + 4) != Some(CENTRAL_SIGNATURE) || at + CENTRAL_LEN > limit {
        return Err(Decline("zip: bad central entry"));
    }
    let flags = u16_at(data, at + 8)?;
    let method = u16_at(data, at + 10)?;
    let crc = u32_at(data, at + 16)?;
    let compressed = u32_at(data, at + 20)?;
    let size = u32_at(data, at + 24)?;
    let name_len = u16_at(data, at + 28)? as usize;
    let extra_len = u16_at(data, at + 30)? as usize;
    let comment_len = u16_at(data, at + 32)? as usize;
    let disk = u16_at(data, at + 34)?;
    let local = u32_at(data, at + 42)? as usize;
    // Chiffrement (simple ou fort), données « patchées », répertoire masqué : `zipfile` lève ou refuse.
    // Encryption (simple or strong), patched data, masked directory: `zipfile` raises or refuses.
    if flags & (0x0001 | 0x0020 | 0x0040 | 0x2000) != 0 {
        return Err(Decline("zip: encrypted entry"));
    }
    if compressed == u32::MAX || size == u32::MAX || local == u32::MAX as usize || disk != 0 {
        return Err(Decline("zip: zip64 entry"));
    }
    let next = at + CENTRAL_LEN + name_len + extra_len + comment_len;
    if next > limit {
        return Err(Decline("zip: bad central entry"));
    }
    let raw_name = &data[at + CENTRAL_LEN..at + CENTRAL_LEN + name_len];
    // Noms ASCII sans « \ » : même lecture par zipfile, le crate zip et calamine / same reading by every reader.
    if raw_name.is_empty() || !raw_name.iter().all(|&b| (0x20..0x7F).contains(&b) && b != b'\\') {
        return Err(Decline("zip: irregular entry name"));
    }
    let name = std::str::from_utf8(raw_name).map_err(|_| Decline("zip: irregular entry name"))?;
    let (compressed, size) = (compressed as usize, u64::from(size));
    if size > RATIO_FLOOR && size > MAX_RATIO * (compressed as u64).max(1) {
        return Err(Decline("zip: abnormal compression ratio"));
    }
    // En-tête local : même nom, données avant le répertoire / local header: same name, data before the directory.
    if data.get(local..local + 4) != Some(LOCAL_SIGNATURE) {
        return Err(Decline("zip: bad local header"));
    }
    let local_name_len = u16_at(data, local + 26)? as usize;
    let local_extra_len = u16_at(data, local + 28)? as usize;
    let start = local + LOCAL_LEN + local_name_len + local_extra_len;
    if data.get(local + LOCAL_LEN..local + LOCAL_LEN + local_name_len) != Some(raw_name)
        || start.checked_add(compressed).is_none_or(|stop| stop > data.len())
    {
        return Err(Decline("zip: bad local header"));
    }
    let key = name.to_ascii_lowercase().into();
    Ok((Entry { method, crc, compressed, size, local, data: start, key }, next))
}

/// Lecture en flux d'une partie ; taille et CRC vérifiés à la fin / streamed part, size and CRC checked at the end.
pub(crate) struct EntryReader<'a> {
    input: &'a [u8],
    position: usize,
    inflater: Option<Box<Decompress>>,
    crc: crc32fast::Hasher,
    produced: u64,
    size: u64,
    expected_crc: u32,
    done: bool,
}

impl EntryReader<'_> {
    /// Taille décompressée annoncée (déjà bornée) / declared inflated size (already bounded).
    pub(crate) fn size(&self) -> u64 {
        self.size
    }

    /// Remplit `out` ; 0 à la fin seulement, une fois la taille et le CRC vérifiés.
    /// Fills `out`; 0 only at the end, once size and CRC are checked.
    pub(crate) fn read(&mut self, out: &mut [u8]) -> Result<usize> {
        if self.done || out.is_empty() {
            return Ok(0);
        }
        loop {
            let (consumed, produced, stream_end) = match self.inflater.as_mut() {
                None => {
                    let count = out.len().min(self.input.len() - self.position);
                    out[..count].copy_from_slice(&self.input[self.position..self.position + count]);
                    (count, count, self.position + count == self.input.len())
                }
                Some(inflater) => {
                    let (before_in, before_out) = (inflater.total_in(), inflater.total_out());
                    let status = inflater
                        .decompress(&self.input[self.position..], out, FlushDecompress::None)
                        .map_err(|_| Decline("zip: corrupt deflate stream"))?;
                    let consumed = (inflater.total_in() - before_in) as usize;
                    let produced = (inflater.total_out() - before_out) as usize;
                    (consumed, produced, status == Status::StreamEnd)
                }
            };
            self.position += consumed;
            self.account(&out[..produced])?;
            if stream_end {
                self.finish()?;
                return Ok(produced);
            }
            if produced > 0 {
                return Ok(produced);
            }
            if consumed == 0 {
                return Err(Decline("zip: truncated stream"));
            }
        }
    }

    fn account(&mut self, chunk: &[u8]) -> Result<()> {
        self.produced += chunk.len() as u64;
        if self.produced > self.size {
            return Err(Decline("zip: lying size"));
        }
        self.crc.update(chunk);
        Ok(())
    }

    fn finish(&mut self) -> Result<()> {
        self.done = true;
        if self.produced != self.size || self.crc.clone().finalize() != self.expected_crc {
            return Err(Decline("zip: size or CRC mismatch"));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use std::io::Write;

    use super::*;

    /// Membre à écrire : nom, contenu, compression, CRC et taille à annoncer (mensonges possibles).
    /// Member to write: name, content, compression, CRC and size to declare (lies allowed).
    struct Member<'a> {
        name: &'a [u8],
        content: &'a [u8],
        deflate: bool,
        crc: Option<u32>,
        size: Option<u32>,
        flags: u16,
        /// Octets ajoutés à la taille compressée annoncée / bytes added to the declared compressed size.
        overrun: u32,
    }

    fn member<'a>(name: &'a [u8], content: &'a [u8]) -> Member<'a> {
        Member { name, content, deflate: true, crc: None, size: None, flags: 0, overrun: 0 }
    }

    fn archive(members: &[Member<'_>], comment: &[u8]) -> Vec<u8> {
        let (mut out, mut central) = (Vec::new(), Vec::new());
        for m in members {
            let data = if m.deflate {
                let mut encoder = flate2::write::DeflateEncoder::new(Vec::new(), flate2::Compression::default());
                encoder.write_all(m.content).unwrap();
                encoder.finish().unwrap()
            } else {
                m.content.to_vec()
            };
            let crc = m.crc.unwrap_or_else(|| crc32fast::hash(m.content));
            let size = m.size.unwrap_or(m.content.len() as u32);
            let method: u16 = if m.deflate { 8 } else { 0 };
            let offset = out.len() as u32;
            let fixed = |signature: &[u8], central: bool| {
                let mut header = signature.to_vec();
                if central {
                    header.extend_from_slice(&20u16.to_le_bytes());
                }
                header.extend_from_slice(&20u16.to_le_bytes());
                header.extend_from_slice(&m.flags.to_le_bytes());
                header.extend_from_slice(&method.to_le_bytes());
                header.extend_from_slice(&[0; 4]);
                header.extend_from_slice(&crc.to_le_bytes());
                header.extend_from_slice(&(data.len() as u32 + m.overrun).to_le_bytes());
                header.extend_from_slice(&size.to_le_bytes());
                header.extend_from_slice(&(m.name.len() as u16).to_le_bytes());
                header.extend_from_slice(&0u16.to_le_bytes());
                header
            };
            out.extend(fixed(LOCAL_SIGNATURE, false));
            out.extend_from_slice(m.name);
            out.extend_from_slice(&data);
            central.extend(fixed(CENTRAL_SIGNATURE, true));
            // Commentaire, disque, attributs interne et externe / comment, disk, internal and external attributes.
            central.extend_from_slice(&[0; 10]);
            central.extend_from_slice(&offset.to_le_bytes());
            central.extend_from_slice(m.name);
        }
        let start = out.len() as u32;
        out.extend_from_slice(&central);
        out.extend_from_slice(END_SIGNATURE);
        out.extend_from_slice(&[0; 4]);
        out.extend_from_slice(&(members.len() as u16).to_le_bytes());
        out.extend_from_slice(&(members.len() as u16).to_le_bytes());
        out.extend_from_slice(&(central.len() as u32).to_le_bytes());
        out.extend_from_slice(&start.to_le_bytes());
        out.extend_from_slice(&(comment.len() as u16).to_le_bytes());
        out.extend_from_slice(comment);
        out
    }

    fn read_all(data: &[u8], name: &str) -> Result<Vec<u8>> {
        let directory = Directory::open(data)?;
        let mut reader = directory.reader(data, directory.find(name).ok_or(Decline("missing"))?)?;
        let mut out = Vec::new();
        let mut chunk = [0u8; 7];
        loop {
            let count = reader.read(&mut chunk)?;
            if count == 0 {
                return Ok(out);
            }
            out.extend_from_slice(&chunk[..count]);
        }
    }

    #[test]
    fn stored_and_deflated_parts_are_read_case_insensitively() {
        let text = b"<worksheet>bonjour</worksheet>".repeat(50);
        let stored = Member { deflate: false, ..member(b"xl/Stored.xml", b"abc") };
        let data = archive(&[member(b"xl/worksheets/sheet1.xml", &text), stored], b"commentaire");
        assert_eq!(read_all(&data, "XL/WORKSHEETS/SHEET1.XML").unwrap(), text);
        assert_eq!(read_all(&data, "xl/stored.xml").unwrap(), b"abc");
        assert!(Directory::open(&data).unwrap().find("xl/absent.xml").is_none());
    }

    #[test]
    fn lying_sizes_and_checksums_are_declined() {
        let text = b"0123456789".repeat(20);
        let wrong_crc = Member { crc: Some(1), ..member(b"a.xml", &text) };
        let short = Member { size: Some(10), ..member(b"a.xml", &text) };
        let long = Member { size: Some(400), ..member(b"a.xml", &text) };
        for lie in [wrong_crc, short, long] {
            assert!(read_all(&archive(&[lie], b""), "a.xml").is_err());
        }
    }

    #[test]
    fn hostile_archives_are_declined() {
        let encrypted = Member { flags: 1, ..member(b"a.xml", b"x") };
        let patched = Member { flags: 0x20, ..member(b"a.xml", b"x") };
        let overlapping = Member { overrun: 3, ..member(b"a.xml", b"x") };
        let last_overlapping = Member { overrun: 3, ..member(b"b.xml", b"y") };
        let bomb_content = vec![0u8; 4 << 20];
        let cases: Vec<Vec<u8>> = vec![
            archive(&[encrypted], b""),
            archive(&[patched], b""),
            archive(&[overlapping, member(b"b.xml", b"y")], b""),
            archive(&[member(b"a.xml", b"x"), last_overlapping], b""),
            archive(&[member(b"a.xml", b"x"), member(b"A.XML", b"y")], b""),
            archive(&[member("é.xml".as_bytes(), b"x")], b""),
            archive(&[member(b"a\\b.xml", b"x")], b""),
            archive(&[member(b"bomb.xml", &bomb_content)], b""),
        ];
        for data in &cases {
            assert!(Directory::open(data).is_err());
        }
        let good = archive(&[member(b"a.xml", b"x")], b"");
        for cut in [0, 10, good.len() / 2, good.len() - 1] {
            assert!(Directory::open(&good[..cut]).is_err());
        }
        let mut prefixed = b"junk".to_vec();
        prefixed.extend_from_slice(&good);
        assert!(Directory::open(&prefixed).is_err());
    }
}
