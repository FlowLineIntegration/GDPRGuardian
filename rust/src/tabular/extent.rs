//! Jumeau du chemin rapide de `xlsx_extent` (garde Python) et des comptes de `_count_sheet_parts`, d'un seul
//! passage, sur une partie entière ou en flux pendant la lecture de la feuille.
//! Twin of the Python guard's `xlsx_extent` fast path and of `_count_sheet_parts` counts, in a single pass,
//! over a whole part or streamed while the sheet is read.
//!
//! Le texte est lu tel que Python le voit après `translate` (tabulation, saut de ligne et retour chariot en
//! espaces, apostrophe en guillemet), sans le copier. En flux, chaque motif lit au plus 40 octets en avant :
//! une traîne de 64 octets entre deux morceaux suffit, et le découpage ne change jamais le résultat. Dès que
//! Python prendrait le chemin exact (instruction, `<!`, références atypiques, balises sans `r` en tête…) ou
//! devrait décoder de l'UTF-16, l'étendue vaut `None` : Python la mesure lui-même. Formules et en-têtes sont
//! comptés sur les octets bruts, comme en Python.
//! The text is read as Python sees it after `translate`, without copying it. When streamed, each pattern reads
//! at most 40 bytes ahead: a 64-byte tail between chunks suffices and chunking never changes the result. When
//! Python would take the exact path or decode UTF-16, the extent is `None`: Python measures it itself. Formulas
//! and headers are counted on the raw bytes, as in Python.

use memchr::memmem;

const BOM: &[u8] = b"\xEF\xBB\xBF";
const UTF16_PROBE: usize = 1024;
const MAX_LETTERS: usize = 16;
const MAX_DIGITS: usize = 16;
/// Traîne gardée entre deux morceaux (lecture en avant maximale : 40 octets) / tail kept between chunks.
const TAIL: usize = 64;

/// Octets qui peuvent ouvrir un motif / bytes that may open a pattern.
const OPENERS: [bool; 256] = {
    let mut table = [false; 256];
    table[b'<' as usize] = true;
    table[b':' as usize] = true;
    table[b'r' as usize] = true;
    table
};

const LOW7: u64 = 0x7F7F_7F7F_7F7F_7F7F;
const HIGH: u64 = 0x8080_8080_8080_8080;
const ONES: u64 = 0x0101_0101_0101_0101;

/// Bit de poids fort de chaque octet de `word` égal à `<`, `:` ou `r` (exact, sans retenue entre octets).
/// High bit of each byte of `word` equal to `<`, `:` or `r` (exact, no carry between bytes).
const fn openers(word: u64) -> u64 {
    const fn equal(word: u64, byte: u8) -> u64 {
        let t = word ^ (ONES * byte as u64);
        !(((t & LOW7) + LOW7) | t) & HIGH
    }
    equal(word, b'<') | equal(word, b':') | equal(word, b'r')
}

/// Octet après `bytes.translate(_WS_QUOTES)` / byte after Python's translation.
const fn seen(b: u8) -> u8 {
    match b {
        b'\t' | b'\n' | b'\r' => b' ',
        b'\'' => b'"',
        _ => b,
    }
}

/// Résultat : étendue (`None` : chemin exact en Python), formules, en-têtes ou pieds de page.
/// Result: extent (`None`: exact path in Python), formulas, headers or footers.
pub(crate) type Measured = (Option<(u128, u128)>, usize, bool);

/// Mesure d'une partie de feuille / measurement of a sheet part.
pub(crate) struct Measure {
    /// Premiers octets bruts, pour la détection UTF-16 et le BOM ; vidés à la fin / first raw bytes, then dropped.
    head: Vec<u8>,
    utf16: bool,
    /// Traîne en attente, puis morceau courant / pending tail, then the current chunk.
    window: Vec<u8>,
    /// Position absolue de `window[0]` / absolute position of `window[0]`.
    offset: usize,
    /// Dernier octet déjà parcouru / last byte already scanned.
    previous: u8,
    exact: bool,
    cells: usize,
    cell_refs: usize,
    rows: usize,
    row_refs: usize,
    max_row: u64,
    max_col: u128,
    six_digits: bool,
    two_letters: bool,
    three_letters: bool,
    formulas: usize,
    headers: bool,
}

impl Measure {
    pub(crate) fn new() -> Self {
        Self {
            head: Vec::with_capacity(UTF16_PROBE),
            utf16: false,
            window: Vec::new(),
            offset: 0,
            previous: 0,
            exact: false,
            cells: 0,
            cell_refs: 0,
            rows: 0,
            row_refs: 0,
            max_row: 0,
            max_col: 0,
            six_digits: false,
            two_letters: false,
            three_letters: false,
            formulas: 0,
            headers: false,
        }
    }

    /// Ajoute le morceau suivant ; les 64 derniers octets attendent la suite / adds the next chunk.
    pub(crate) fn feed(&mut self, bytes: &[u8]) {
        self.probe(bytes);
        self.window.extend_from_slice(bytes);
        if self.window.len() > TAIL {
            let window = std::mem::take(&mut self.window);
            let upto = window.len() - TAIL;
            self.scan(&window, upto);
            self.window = window;
            self.window.drain(..upto);
        }
    }

    /// Fin de partie : parcourt la traîne ; il ne reste ensuite que des comptes / end of part: scans the tail;
    /// only counts remain afterwards.
    pub(crate) fn close(&mut self) {
        let window = std::mem::take(&mut self.window);
        self.scan(&window, window.len());
        let head = std::mem::take(&mut self.head);
        self.utf16 = head.starts_with(b"\xFF\xFE") || head.starts_with(b"\xFE\xFF") || head.contains(&0);
    }

    /// Décision de Python, une fois la partie close : majorant grossier sous `limit`, sinon maxima exacts.
    /// Python's decision, once the part is closed: a coarse bound under `limit`, else the exact maxima.
    pub(crate) fn result(&self, limit: u128) -> Measured {
        if self.utf16 || self.exact || self.cells != self.cell_refs || self.rows != self.row_refs {
            return (None, self.formulas, self.headers);
        }
        let max_row = if self.six_digits { None } else { Some(99_999u128) };
        let max_col = match (self.two_letters, self.three_letters) {
            (false, _) => Some(26u128),
            (true, false) => Some(702),
            (true, true) => None,
        };
        let extent = match (max_row, max_col) {
            (Some(rows), Some(cols)) if rows * cols <= limit => (rows, cols),
            _ => (u128::from(self.max_row), self.max_col),
        };
        (Some(extent), self.formulas, self.headers)
    }

    fn probe(&mut self, bytes: &[u8]) {
        let missing = UTF16_PROBE.saturating_sub(self.head.len());
        self.head.extend_from_slice(&bytes[..missing.min(bytes.len())]);
    }

    /// Parcourt les positions `[0, upto)` ; `window` reste lisible jusqu'à sa fin / scans positions below `upto`.
    fn scan(&mut self, window: &[u8], upto: usize) {
        let start = if self.head.starts_with(BOM) { BOM.len() } else { 0 };
        // Huit octets à la fois, puis la fin octet par octet / eight bytes at a time, then the end byte by byte.
        let mut base = 0;
        while base + 8 <= upto {
            let word = window[base..base + 8].try_into().unwrap_or_default();
            let mut flags = openers(u64::from_le_bytes(word));
            while flags != 0 {
                let p = base + (flags.trailing_zeros() / 8) as usize;
                flags &= flags - 1;
                self.opener(window, p, start);
            }
            base += 8;
        }
        for p in base..upto {
            if OPENERS[usize::from(window[p])] {
                self.opener(window, p, start);
            }
        }
        if !self.headers {
            // Occurrences commençant avant `upto` / occurrences starting before `upto`.
            let reach = &window[..(upto + 6).min(window.len())];
            self.headers = memmem::find(reach, b"Header>").is_some() || memmem::find(reach, b"Footer>").is_some();
        }
        if let Some(&last) = window[..upto].last() {
            self.previous = last;
        }
        self.offset += upto;
    }

    #[inline]
    fn opener(&mut self, window: &[u8], p: usize, start: usize) {
        match window[p] {
            // Balise fermante : rien à compter (le cas le plus fréquent) / end tag: nothing to count.
            b'<' if window.get(p + 1) == Some(&b'/') => {}
            b'<' => self.tag(window, p, start),
            b':' => self.colon(window, p),
            _ => {
                let previous = if p == 0 { self.previous } else { window[p - 1] };
                if seen(previous) == b' ' {
                    self.reference(window, p);
                }
            }
        }
    }

    /// `<?` hors de la tête, `<!`, `<f>`/`<f `, balises `c` et `row` et leur `r` en tête.
    /// `<?` past the head, `<!`, `<f>`/`<f `, `c` and `row` tags and their leading `r`.
    fn tag(&mut self, window: &[u8], p: usize, start: usize) {
        // Les octets traduits par Python ne sont jamais `c`, `r`, `o`, `w`, `=` / translated bytes never are these.
        let (counted, referenced) = match window.get(p + 1..) {
            Some([b'c', rest @ ..]) => Self::counts(rest),
            Some([b'r', b'o', b'w', rest @ ..]) => {
                let (counted, referenced) = Self::counts(rest);
                self.rows += counted;
                self.row_refs += referenced;
                return;
            }
            Some([b'?', ..]) if self.offset + p > start => {
                self.exact = true;
                return;
            }
            Some([b'!', ..]) => {
                self.exact = true;
                return;
            }
            Some([b'f', b'>' | b' ', ..]) => {
                self.formulas += 1;
                return;
            }
            _ => return,
        };
        self.cells += counted;
        self.cell_refs += referenced;
    }

    /// Après le nom de balise : comptée (` `, `>`, `/`) et `r="` en tête / after the tag name: counted, leading r.
    fn counts(rest: &[u8]) -> (usize, usize) {
        match rest {
            [after, b'r', b'=', quote, ..] if seen(*after) == b' ' => (1, usize::from(seen(*quote) == b'"')),
            [after, ..] => (usize::from(matches!(seen(*after), b' ' | b'>' | b'/')), 0),
            [] => (0, 0),
        }
    }

    /// Blocages `:c` et `:row`, formules `:f>` et `:f ` / blockers and prefixed formulas.
    fn colon(&mut self, window: &[u8], p: usize) {
        match window.get(p + 1) {
            Some(b'c') => self.exact = true,
            Some(b'r') if window.get(p + 2..p + 4) == Some(b"ow") => self.exact = true,
            Some(b'f') if matches!(window.get(p + 2), Some(b'>' | b' ')) => self.formulas += 1,
            _ => {}
        }
    }

    /// ` r` : blocage (` r `, ` r= `) ou référence ` r="…"` (`_ODD_REF`, maxima, indicateurs).
    /// ` r`: blocker or reference.
    fn reference(&mut self, window: &[u8], p: usize) {
        let value = match window.get(p + 1..) {
            Some([b'=', quote, value @ ..]) if seen(*quote) == b'"' => value,
            Some([space, ..] | [b'=', space, ..]) if seen(*space) == b' ' => {
                self.exact = true;
                return;
            }
            _ => return,
        };
        let letters = value.iter().take(MAX_LETTERS + 1).take_while(|b| b.is_ascii_alphabetic()).count();
        let digits = value[letters..].iter().take(MAX_DIGITS + 1).take_while(|b| b.is_ascii_digit()).count();
        let closed = value.get(letters + digits).is_some_and(|&b| seen(b) == b'"');
        if letters > MAX_LETTERS || digits == 0 || digits > MAX_DIGITS || !closed {
            self.exact = true;
            return;
        }
        self.six_digits |= digits >= 6;
        self.two_letters |= letters >= 2;
        self.three_letters |= letters >= 3;
        let row = value[letters..letters + digits].iter().fold(0u64, |n, &d| n * 10 + u64::from(d - b'0'));
        self.max_row = self.max_row.max(row);
        if letters > 0 {
            // `column_index(lettres) + 1`, base 26 / base 26.
            let col =
                value[..letters].iter().fold(0u128, |n, &c| n * 26 + u128::from(c.to_ascii_uppercase() - b'A') + 1);
            self.max_col = self.max_col.max(col);
        }
    }
}

/// Mesure d'une partie entière, sans copie / measurement of a whole part, without a copy.
pub(crate) fn measure(text: &[u8], limit: u128) -> Measured {
    let mut measure = Measure::new();
    measure.probe(text);
    measure.scan(text, text.len());
    measure.close();
    measure.result(limit)
}

#[cfg(test)]
mod tests {
    use super::*;

    const PIECES: [&[u8]; 30] = [
        b"<row r=\"1\">",
        b"<row r=\"250000\">",
        b"</row>",
        b"<c r=\"A1\">",
        b"<c r=\"ZZ9\">",
        b"<c r=\"XFD1048576\">",
        b"<c r=\"AB123456\">",
        b"<c>",
        b"<c/>",
        b"<c\tr=\"B2\" s=\"1\"/>",
        b"<c r='C3'>",
        b"<c r=\"1\">",
        b"<c r=\"AAAAAAAAAAAAAAAAA1\">",
        b"<v>1</v>",
        b"</c>",
        b" r ",
        b" r= ",
        b"<!-- -->",
        b"<?pi?>",
        b"<x:c>",
        b":row",
        b"<f>",
        b"<f t=\"shared\">",
        b":f>",
        b"Header>",
        b" ",
        b"\xEF\xBB\xBF",
        b"\n",
        b"<c r=\"A12345678901234567\">",
        b"'",
    ];

    fn chunked(text: &[u8], size: usize, limit: u128) -> Measured {
        let mut measure = Measure::new();
        for chunk in text.chunks(size) {
            measure.feed(chunk);
        }
        measure.close();
        measure.result(limit)
    }

    #[test]
    fn known_sheet_is_measured() {
        let sheet = b"\xEF\xBB\xBF<?xml version=\"1.0\"?><worksheet><sheetData><row r=\"1\"><c r=\"AB12\" s=\"1\">\
            <f>SUM(A1)</f><v>1</v></c><c\tr='C300'><v>2</v></c></row><row r=\"250000\"><c r=\"Z250000\"/></row>\
            </sheetData><headerFooter><oddHeader>x</oddHeader></headerFooter></worksheet>";
        assert_eq!(measure(sheet, 1 << 24), (Some((250_000, 28)), 1, true));
        assert_eq!(measure(b"<row r=\"1\"><c r=\"B2\"/></row>", 1 << 24), (Some((99_999, 26)), 0, false));
    }

    #[test]
    fn chunking_never_changes_the_result() {
        // Compositions pseudo-aléatoires des morceaux du test Python / pseudo-random compositions.
        let mut state = 0x2545_F491_4F6C_DD1Du64;
        for _ in 0..400 {
            let mut text = Vec::new();
            for _ in 0..(state % 40) {
                state ^= state << 13;
                state ^= state >> 7;
                state ^= state << 17;
                text.extend_from_slice(PIECES[(state % PIECES.len() as u64) as usize]);
            }
            for limit in [100, 1 << 24] {
                let whole = measure(&text, limit);
                for size in [1, 2, 3, 7, 40, 64, 65, 100, 1000] {
                    assert_eq!(chunked(&text, size, limit), whole, "{size} {}", String::from_utf8_lossy(&text));
                }
            }
            state = state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        }
    }

    #[test]
    fn exact_path_cases_return_none() {
        let cases: [&[u8]; 9] = [
            b"<!-- c --><c r=\"A1\"/>",
            b"<c r=\"A1\"/><?pi?>",
            b"<x:c r=\"A1\"/>",
            b"<c r=\"1A\"/>",
            b"<c>",
            b"<c r = \"A1\"/>",
            b"\xFF\xFE<\0c\0",
            b"<row r=\"1\"><c r=\"A1\"/></row><b r ></b>",
            b"<x:row r=\"1\">",
        ];
        for sheet in cases {
            assert_eq!(measure(sheet, 1 << 24).0, None, "{}", String::from_utf8_lossy(sheet));
            assert_eq!(chunked(sheet, 3, 1 << 24).0, None, "{}", String::from_utf8_lossy(sheet));
        }
    }
}
