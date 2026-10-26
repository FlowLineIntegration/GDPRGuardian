//! Analyseur XML strict, en flux / strict streaming XML tokenizer.
//!
//! Produit les mêmes événements que quick-xml 0.41 réglé comme calamine (éléments vides développés en ouverture
//! puis fermeture, texte non rogné, fins de balise non vérifiées), mais sur une grammaire plus étroite : noms
//! ASCII, attributs entre guillemets, références prédéfinies ou numériques valides, déclaration UTF-8 en tête
//! seulement, fermetures appariées. Commentaires, CDATA, DOCTYPE, instructions, entités inconnues, `&` isolé ou
//! document tronqué : refus, la référence prend le relais. Un texte forme toujours un seul événement, comme dans
//! quick-xml, quelle que soit la découpe du flux. Chaque balise est lue en une passe, par table d'octets.
//! Yields the same events as quick-xml 0.41 configured like calamine (empty elements expanded into a start and an
//! end, untrimmed text, end names unchecked), on a narrower grammar: ASCII names, quoted attributes, valid
//! predefined or numeric references, UTF-8 declaration at the head only, matched end tags. Comments, CDATA,
//! DOCTYPE, PIs, unknown entities, lone `&` or a truncated document: declined, the reference takes over. A text run
//! is always a single event, as in quick-xml, whatever the stream chunking. Each tag is read in one pass, through
//! a byte table.

use memchr::{memchr, memchr2};

use super::extent::Measure;
use super::zip::{EntryReader, MAX_PART};
use super::{Decline, Result};

const CHUNK: usize = 256 * 1024;
/// Une référence valide tient en 10 octets (`#x10FFFF;`) / a valid reference fits in 10 bytes.
const MAX_REFERENCE: usize = 12;

const START: u8 = 1;
const NAME: u8 = 2;
const SPACE: u8 = 4;

/// Classe de chaque octet : début de nom, suite de nom, blanc XML / class of each byte.
static CLASSES: [u8; 256] = classes();

const fn classes() -> [u8; 256] {
    let mut table = [0u8; 256];
    let mut i = 0;
    while i < 256 {
        let b = i as u8;
        if b.is_ascii_alphabetic() || b == b'_' {
            table[i] = START | NAME;
        } else if b.is_ascii_digit() || b == b'.' || b == b'-' {
            table[i] = NAME;
        } else if matches!(b, b' ' | b'\t' | b'\r' | b'\n') {
            table[i] = SPACE;
        }
        i += 1;
    }
    table
}

fn is(b: u8, class: u8) -> bool {
    CLASSES[b as usize] & class != 0
}

/// Référence résolue (`&lt;`, `&#233;`…) / resolved reference.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Reference {
    Char(char),
    Text(&'static str),
}

impl Reference {
    pub(crate) fn push_to(self, out: &mut String) {
        match self {
            Reference::Char(c) => out.push(c),
            Reference::Text(text) => out.push_str(text),
        }
    }
}

/// Événement XML ; les tranches empruntent le tampon jusqu'à l'appel suivant / slices borrow until the next call.
/// `local` : nom sans préfixe (`QName::local_name`) / name without prefix.
#[derive(Debug)]
pub(crate) enum Event<'b> {
    /// Ouverture (ou élément vide, dont la fermeture suit) : nom, nom local et attributs.
    /// Start tag (or empty element, whose end follows): name, local name and attributes.
    Start {
        name: &'b [u8],
        local: &'b [u8],
        attrs: Attrs<'b>,
    },
    End {
        name: &'b [u8],
        local: &'b [u8],
    },
    /// Texte brut, ni décodé ni normalisé / raw text, neither decoded nor normalised.
    Text(&'b [u8]),
    Ref(Reference),
    Eof,
}

/// Attribut délimité par l'analyseur : clé et valeur brute, en positions / attribute delimited by the tokenizer.
#[derive(Clone, Copy, Debug)]
struct Span {
    key: usize,
    key_end: usize,
    value: usize,
    value_end: usize,
}

/// Attributs d'une balise, lus comme `RawAttrIter` de calamine (clé exacte, valeur brute) ; déjà délimités,
/// ils ne sont jamais relus. A tag's attributes, read as calamine's `RawAttrIter`; already delimited, never re-read.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Attrs<'b> {
    buf: &'b [u8],
    spans: &'b [Span],
}

impl<'b> Attrs<'b> {
    pub(crate) fn iter(self) -> impl Iterator<Item = (&'b [u8], &'b [u8])> {
        self.spans.iter().map(move |s| (&self.buf[s.key..s.key_end], &self.buf[s.value..s.value_end]))
    }

    /// Premier attribut de ce nom (`raw_attr`) / first attribute with this key.
    pub(crate) fn get(self, key: &[u8]) -> Option<&'b [u8]> {
        self.iter().find(|(k, _)| *k == key).map(|(_, v)| v)
    }

    /// Plusieurs attributs en une passe, arrêt dès que chacun a été vu, comme la macro `get_attrs!` de calamine
    /// (un doublon compte, la dernière valeur lue l'emporte). Several attributes in one pass, as calamine's
    /// `get_attrs!` macro (a duplicate counts, the last value read wins).
    pub(crate) fn get_many<const N: usize>(self, keys: [&[u8]; N]) -> [Option<&'b [u8]>; N] {
        let mut values = [None; N];
        let mut found = 0;
        for (key, value) in self.iter() {
            if let Some(slot) = keys.iter().position(|k| *k == key) {
                values[slot] = Some(value);
                found += 1;
            }
            if found == N {
                break;
            }
        }
        values
    }
}

/// Nom local (après le premier `:`), comme `QName::local_name` / local name, as quick-xml computes it.
pub(crate) fn local(name: &[u8]) -> &[u8] {
    match memchr(b':', name) {
        Some(i) => &name[i + 1..],
        None => name,
    }
}

/// Issue de l'analyse d'un nom / outcome of scanning a name.
enum Scan {
    /// Fin du nom et position du `:` éventuel / end of the name and position of the optional `:`.
    Done(usize, Option<usize>),
    Incomplete,
    Invalid,
}

/// Nom ASCII à partir de `i`, au plus un préfixe / ASCII name from `i`, at most one prefix.
fn scan_name(b: &[u8], mut i: usize) -> Scan {
    match b.get(i) {
        None => return Scan::Incomplete,
        Some(&c) if !is(c, START) => return Scan::Invalid,
        Some(_) => i += 1,
    }
    let mut colon = None;
    loop {
        let Some(&c) = b.get(i) else { return Scan::Incomplete };
        if is(c, NAME) {
            i += 1;
        } else if c == b':' && colon.is_none() {
            match b.get(i + 1) {
                None => return Scan::Incomplete,
                Some(&next) if is(next, START) => {
                    colon = Some(i);
                    i += 1;
                }
                Some(_) => return Scan::Invalid,
            }
        } else {
            return Scan::Done(i, colon);
        }
    }
}

fn skip_spaces(b: &[u8], mut i: usize) -> usize {
    while i < b.len() && is(b[i], SPACE) {
        i += 1;
    }
    i
}

/// Balise analysée, en positions dans le tampon / parsed tag, as buffer positions.
enum Tag {
    Start { name: usize, colon: Option<usize>, name_end: usize, close: usize, empty: bool },
    End { name: usize, colon: Option<usize>, name_end: usize, close: usize },
}

macro_rules! scan {
    ($scan:expr) => {
        match $scan {
            Scan::Done(end, colon) => (end, colon),
            Scan::Incomplete => return Ok(None),
            Scan::Invalid => return Err(Decline("xml: bad name")),
        }
    };
}

/// Balise commençant à `pos` (`<`), en une passe ; ses attributs vont dans `spans`. `None` si le tampon
/// s'arrête avant sa fin. Tag starting at `pos`, in one pass; its attributes go to `spans`. `None` when the
/// buffer stops before its end.
fn parse_tag(b: &[u8], pos: usize, spans: &mut Vec<Span>) -> Result<Option<Tag>> {
    spans.clear();
    let Some(&first) = b.get(pos + 1) else { return Ok(None) };
    match first {
        b'!' => return Err(Decline("xml: comment, CDATA or DOCTYPE")),
        b'?' => return Err(Decline("xml: processing instruction")),
        b'/' => {
            let name = pos + 2;
            let (name_end, colon) = scan!(scan_name(b, name));
            let close = skip_spaces(b, name_end);
            return match b.get(close) {
                None => Ok(None),
                Some(b'>') => Ok(Some(Tag::End { name, colon, name_end, close })),
                Some(_) => Err(Decline("xml: bad end tag")),
            };
        }
        _ => {}
    }
    let name = pos + 1;
    let (name_end, colon) = scan!(scan_name(b, name));
    let mut i = name_end;
    loop {
        let spaced = skip_spaces(b, i);
        let Some(&c) = b.get(spaced) else { return Ok(None) };
        match c {
            b'>' => return Ok(Some(Tag::Start { name, colon, name_end, close: spaced, empty: false })),
            b'/' => {
                return match b.get(spaced + 1) {
                    None => Ok(None),
                    Some(b'>') => Ok(Some(Tag::Start { name, colon, name_end, close: spaced + 1, empty: true })),
                    Some(_) => Err(Decline("xml: bad empty tag")),
                };
            }
            _ if spaced == i => return Err(Decline("xml: attribute without separator")),
            _ => {}
        }
        // Attribut `nom = "valeur"`, sans `<` dans la valeur / attribute, no `<` in the value.
        let (key_end, _) = scan!(scan_name(b, spaced));
        let equals = skip_spaces(b, key_end);
        match b.get(equals) {
            None => return Ok(None),
            Some(b'=') => {}
            Some(_) => return Err(Decline("xml: attribute without value")),
        }
        let quote_at = skip_spaces(b, equals + 1);
        let quote = match b.get(quote_at) {
            None => return Ok(None),
            Some(&q @ (b'"' | b'\'')) => q,
            Some(_) => return Err(Decline("xml: unquoted attribute")),
        };
        // Valeurs courtes : une boucle simple bat `memchr` / short values: a plain loop beats `memchr`.
        let mut value_end = quote_at + 1;
        loop {
            match b.get(value_end) {
                None => return Ok(None),
                Some(&c) if c == quote => break,
                Some(b'<') => return Err(Decline("xml: '<' in attribute value")),
                Some(_) => value_end += 1,
            }
        }
        spans.push(Span { key: spaced, key_end, value: quote_at + 1, value_end });
        i = value_end + 1;
    }
}

/// Référence entre `&` et `;` : prédéfinie ou numérique valide (règles de quick-xml) / predefined or numeric.
pub(crate) fn resolve(content: &[u8]) -> Option<Reference> {
    let text = match content {
        b"lt" => "<",
        b"gt" => ">",
        b"amp" => "&",
        b"apos" => "'",
        b"quot" => "\"",
        _ => {
            let number = content.strip_prefix(b"#")?;
            let (digits, radix) = match number.strip_prefix(b"x") {
                Some(hex) => (hex, 16),
                None => (number, 10),
            };
            // Signe refusé, comme `parse_number` de quick-xml / signs refused, as quick-xml's `parse_number`.
            if digits.is_empty() || !digits.iter().all(|b| (*b as char).is_digit(radix)) {
                return None;
            }
            let code = u32::from_str_radix(std::str::from_utf8(digits).ok()?, radix).ok()?;
            return char::from_u32(code).filter(|&c| c != '\0').map(Reference::Char);
        }
    };
    Some(Reference::Text(text))
}

/// `quick_xml::escape::unescape` : références d'une valeur d'attribut, `None` si invalide / attribute value.
pub(crate) fn unescape(raw: &str) -> Option<String> {
    let bytes = raw.as_bytes();
    let mut out = String::with_capacity(raw.len());
    let mut last = 0;
    while let Some(i) = memchr(b'&', &bytes[last..]) {
        let start = last + i;
        let stop = start + 1 + memchr2(b'&', b';', &bytes[start + 1..])?;
        if bytes[stop] != b';' {
            return None;
        }
        out.push_str(&raw[last..start]);
        resolve(&bytes[start + 1..stop])?.push_to(&mut out);
        last = stop + 1;
    }
    out.push_str(&raw[last..]);
    Some(out)
}

/// Texte d'un événement : UTF-8 vérifié, fins de ligne XML 1.0 normalisées (`xml10_content`).
/// Event text: UTF-8 checked, XML 1.0 line ends normalised (`xml10_content`).
pub(crate) fn push_text(raw: &[u8], out: &mut String) -> Result<()> {
    let text = std::str::from_utf8(raw).map_err(|_| Decline("xml: invalid UTF-8"))?;
    let mut rest = text;
    while let Some(i) = memchr(b'\r', rest.as_bytes()) {
        out.push_str(&rest[..i]);
        out.push('\n');
        rest = &rest[i + 1..];
        if let Some(stripped) = rest.strip_prefix('\n') {
            rest = stripped;
        }
    }
    out.push_str(rest);
    Ok(())
}

/// Lecteur d'une partie XML / reader of an XML part.
pub(crate) struct Reader<'a> {
    source: EntryReader<'a>,
    buf: Vec<u8>,
    pos: usize,
    end: usize,
    exhausted: bool,
    begun: bool,
    /// Pile des éléments ouverts : noms bout à bout et leurs débuts / open elements: names and their starts.
    names: Vec<u8>,
    starts: Vec<usize>,
    /// Un élément vide attend son événement de fermeture / an empty element awaits its end event.
    expanded: bool,
    truncate: Option<usize>,
    /// Attributs de la dernière balise ouvrante / attributes of the last start tag.
    spans: Vec<Span>,
    limit: usize,
    /// Mesure de la garde, nourrie de chaque octet lu / guard measurement, fed with every byte read.
    measure: Option<Measure>,
}

impl<'a> Reader<'a> {
    pub(crate) fn new(source: EntryReader<'a>) -> Self {
        // Le tampon ne dépasse jamais deux fois la partie / the buffer never exceeds twice the part.
        let limit = 2 * (source.size().min(MAX_PART) as usize).max(CHUNK);
        Self {
            source,
            buf: Vec::new(),
            pos: 0,
            end: 0,
            exhausted: false,
            begun: false,
            names: Vec::with_capacity(256),
            starts: Vec::with_capacity(16),
            expanded: false,
            truncate: None,
            spans: Vec::with_capacity(16),
            limit,
            measure: None,
        }
    }

    /// Lecteur qui mesure aussi la partie comme la garde Python / reader that also measures the part.
    pub(crate) fn measuring(source: EntryReader<'a>) -> Self {
        Self { measure: Some(Measure::new()), ..Self::new(source) }
    }

    /// Mesure de la partie entière : la suite non lue est décompressée (taille et CRC vérifiés) ; `None` si
    /// elle est illisible. Measurement of the whole part: the unread rest is inflated (size and CRC checked);
    /// `None` when it is unreadable.
    pub(crate) fn into_measure(mut self) -> Option<Measure> {
        let mut measure = self.measure.take()?;
        let mut chunk = std::mem::take(&mut self.buf);
        chunk.resize(chunk.len().max(CHUNK), 0);
        loop {
            match self.source.read(&mut chunk) {
                Ok(0) => break,
                Ok(count) => measure.feed(&chunk[..count]),
                Err(_) => return None,
            }
        }
        measure.close();
        Some(measure)
    }

    /// Événement suivant ; `Decline` hors de la grammaire acceptée / next event; `Decline` outside the grammar.
    pub(crate) fn next(&mut self) -> Result<Event<'_>> {
        if let Some(at) = self.truncate.take() {
            self.names.truncate(at);
        }
        if self.expanded {
            self.expanded = false;
            let start = self.starts.pop().ok_or(Decline("xml: element stack"))?;
            self.truncate = Some(start);
            let name = &self.names[start..];
            return Ok(Event::End { name, local: local(name) });
        }
        if !self.begun {
            self.begin()?;
        }
        if self.pos == self.end && !self.fill()? {
            return if self.starts.is_empty() { Ok(Event::Eof) } else { Err(Decline("xml: unclosed element")) };
        }
        match self.buf[self.pos] {
            b'<' => self.markup(),
            b'&' => self.reference(),
            _ => self.text(),
        }
    }

    /// Lit jusqu'à remplir le tampon (doublé s'il est plein) ; le reste non consommé passe en tête. Un jeton
    /// incomplet voit donc sa part lue doubler à chaque essai : coût linéaire. Reads until the buffer is full
    /// (doubled when full); the unconsumed rest moves to the front, so retries stay linear.
    fn fill(&mut self) -> Result<bool> {
        if self.exhausted {
            return Ok(false);
        }
        if self.pos > 0 {
            self.buf.copy_within(self.pos..self.end, 0);
            self.end -= self.pos;
            self.pos = 0;
        }
        if self.end == self.buf.len() {
            let grown = (self.buf.len() * 2).max(CHUNK);
            if grown > self.limit {
                return Err(Decline("xml: token too large"));
            }
            self.buf.resize(grown, 0);
        }
        let before = self.end;
        while self.end < self.buf.len() {
            let count = self.source.read(&mut self.buf[self.end..])?;
            if count == 0 {
                self.exhausted = true;
                break;
            }
            self.end += count;
        }
        if let Some(measure) = self.measure.as_mut() {
            measure.feed(&self.buf[before..self.end]);
        }
        Ok(self.end > before)
    }

    /// Au moins `n` octets disponibles à partir de `pos`, si le flux en contient / at least `n` bytes if any.
    fn available(&mut self, n: usize) -> Result<bool> {
        while self.end - self.pos < n {
            if !self.fill()? {
                return Ok(false);
            }
        }
        Ok(true)
    }

    /// BOM UTF-8 et déclaration `<?xml …?>` en UTF-8 / UTF-8 BOM and UTF-8 declaration.
    fn begin(&mut self) -> Result<()> {
        self.begun = true;
        self.available(4)?;
        let head = &self.buf[self.pos..self.end];
        if head.starts_with(&[0xFE, 0xFF]) || head.starts_with(&[0xFF, 0xFE]) || head.iter().take(4).any(|&b| b == 0) {
            return Err(Decline("xml: not UTF-8"));
        }
        if head.starts_with(&[0xEF, 0xBB, 0xBF]) {
            self.pos += 3;
        }
        self.available(6)?;
        let head = &self.buf[self.pos..self.end];
        if !head.starts_with(b"<?xml") || !head.get(5).is_some_and(|&b| is(b, SPACE) || b == b'?') {
            return Ok(());
        }
        let mut scanned = 5;
        let stop = loop {
            match memchr(b'>', &self.buf[self.pos + scanned..self.end]) {
                Some(i) => break self.pos + scanned + i,
                None => {
                    scanned = self.end - self.pos;
                    if !self.fill()? {
                        return Err(Decline("xml: unterminated declaration"));
                    }
                }
            }
        };
        let declaration = &self.buf[self.pos + 5..stop];
        let pseudo = declaration.strip_suffix(b"?").ok_or(Decline("xml: bad declaration"))?;
        // Pseudo-attributs lus comme ceux d'une balise / pseudo-attributes read as a tag's.
        let probe = [b"<x", pseudo, b">"].concat();
        let mut spans = Vec::new();
        if !matches!(parse_tag(&probe, 0, &mut spans)?, Some(Tag::Start { close, .. }) if close + 1 == probe.len()) {
            return Err(Decline("xml: bad declaration"));
        }
        if let Some(encoding) = (Attrs { buf: &probe, spans: &spans }).get(b"encoding") {
            if !encoding.eq_ignore_ascii_case(b"utf-8") {
                return Err(Decline("xml: not UTF-8"));
            }
        }
        self.pos = stop + 1;
        Ok(())
    }

    /// Texte jusqu'au prochain `<` ou `&`, d'un seul tenant / text up to the next `<` or `&`, in one piece.
    fn text(&mut self) -> Result<Event<'_>> {
        let mut scanned = 0;
        loop {
            if let Some(i) = memchr2(b'<', b'&', &self.buf[self.pos + scanned..self.end]) {
                let start = self.pos;
                self.pos += scanned + i;
                return Ok(Event::Text(&self.buf[start..self.pos]));
            }
            scanned = self.end - self.pos;
            if !self.fill()? {
                let start = self.pos;
                self.pos = self.end;
                return Ok(Event::Text(&self.buf[start..self.end]));
            }
        }
    }

    /// `&…;` valide, résolu / valid reference, resolved.
    fn reference(&mut self) -> Result<Event<'_>> {
        self.available(MAX_REFERENCE)?;
        let window = &self.buf[self.pos + 1..self.end.min(self.pos + MAX_REFERENCE)];
        let stop = memchr(b';', window).ok_or(Decline("xml: lone ampersand"))?;
        let reference = resolve(&window[..stop]).ok_or(Decline("xml: unknown reference"))?;
        self.pos += stop + 2;
        Ok(Event::Ref(reference))
    }

    fn markup(&mut self) -> Result<Event<'_>> {
        let tag = loop {
            match parse_tag(&self.buf[..self.end], self.pos, &mut self.spans)? {
                Some(tag) => break tag,
                None => {
                    if !self.fill()? {
                        return Err(Decline("xml: unterminated tag"));
                    }
                }
            }
        };
        match tag {
            Tag::End { name, colon, name_end, close } => {
                self.pos = close + 1;
                let opened = self.starts.pop().ok_or(Decline("xml: unmatched end tag"))?;
                if self.names[opened..] != self.buf[name..name_end] {
                    return Err(Decline("xml: mismatched end tag"));
                }
                self.names.truncate(opened);
                let local = colon.map_or(name, |c| c + 1);
                Ok(Event::End { name: &self.buf[name..name_end], local: &self.buf[local..name_end] })
            }
            Tag::Start { name, colon, name_end, close, empty } => {
                self.pos = close + 1;
                self.starts.push(self.names.len());
                self.names.extend_from_slice(&self.buf[name..name_end]);
                self.expanded = empty;
                let local = colon.map_or(name, |c| c + 1);
                Ok(Event::Start {
                    name: &self.buf[name..name_end],
                    local: &self.buf[local..name_end],
                    attrs: Attrs { buf: &self.buf, spans: &self.spans },
                })
            }
        }
    }

    /// Passe le sous-arbre de l'élément qui vient de s'ouvrir (`read_to_end_into`) / skips the opened subtree.
    pub(crate) fn skip_element(&mut self) -> Result<()> {
        let mut depth = 0usize;
        loop {
            match self.next()? {
                Event::Start { .. } => depth += 1,
                Event::End { .. } if depth == 0 => return Ok(()),
                Event::End { .. } => depth -= 1,
                Event::Eof => return Err(Decline("xml: unexpected end of document")),
                _ => {}
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn events(xml: &[u8]) -> Result<Vec<String>> {
        let mut spans = Vec::new();
        let tag = parse_tag(xml, 0, &mut spans)?;
        let attrs = Attrs { buf: xml, spans: &spans };
        let pairs: Vec<String> = attrs
            .iter()
            .map(|(k, v)| format!("{}={}", String::from_utf8_lossy(k), String::from_utf8_lossy(v)))
            .collect();
        Ok(vec![match tag {
            Some(Tag::Start { name, name_end, empty, .. }) => {
                format!("start {} {pairs:?} {empty}", String::from_utf8_lossy(&xml[name..name_end]))
            }
            Some(Tag::End { name, name_end, .. }) => format!("end {}", String::from_utf8_lossy(&xml[name..name_end])),
            None => "incomplete".to_string(),
        }])
    }

    #[test]
    fn tags_follow_the_narrow_grammar() {
        assert_eq!(events(b"<c r=\"A1\" s='2'>").unwrap(), ["start c [\"r=A1\", \"s=2\"] false"]);
        assert_eq!(events(b"<x:c r = \"A>1\"/>").unwrap(), ["start x:c [\"r=A>1\"] true"]);
        assert_eq!(events(b"</x:row \n>").unwrap(), ["end x:row"]);
        assert_eq!(events(b"<c r=\"A1\"").unwrap(), ["incomplete"]);
        for bad in
            [&b"<!-- x -->"[..], b"<?pi?>", b"<c r=A1>", b"<c r=\"<\">", b"<c a=\"1\"b=\"2\">", b"<a:b:c>", b"<1a>"]
        {
            assert!(events(bad).is_err(), "{}", String::from_utf8_lossy(bad));
        }
    }

    #[test]
    fn references_and_attribute_values() {
        assert_eq!(resolve(b"amp"), Some(Reference::Text("&")));
        assert_eq!(resolve(b"#x41"), Some(Reference::Char('A')));
        assert_eq!(resolve(b"#233"), Some(Reference::Char('é')));
        for bad in [&b"#X41"[..], b"#x", b"#0", b"#+1", b"#xD800", b"nbsp", b"AMP"] {
            assert_eq!(resolve(bad), None);
        }
        assert_eq!(unescape("a;b&lt;c&#x26;").as_deref(), Some("a;b<c&"));
        assert_eq!(unescape("a & b"), None);
        assert_eq!(unescape("a &x&lt;"), None);
        let mut out = String::new();
        push_text(b"a\r\nb\rc\n", &mut out).unwrap();
        assert_eq!(out, "a\nb\nc\n");
    }
}
