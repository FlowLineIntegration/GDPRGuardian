//! Nettoyage de la sortie contre l'injection de prompt : port exact de `sanitize.sanitize_output` (Python).
//!
//! Output hygiene against prompt injection: exact port of the Python reference. Quatre passes, dans l'ordre de
//! Python : invisibles retirés, images Markdown distantes et balises `<img>` remplacées, commentaires HTML
//! retirés (sauf `<!-- page … -->`). Four passes, in Python's order. Les classes `\s`, `\w` et l'égalité sans
//! casse de `re` viennent de la table Unicode de l'interpréteur / `\s`, `\w` and `re`'s case-insensitive
//! equality come from the interpreter's Unicode table. Sans motif trouvé, aucune allocation par caractère : les
//! équivalents de « img » sont calculés une fois par appel. Without a match, no per-character allocation: the
//! equivalents of "img" are computed once per call.

use std::borrow::Cow;

use memchr::memchr;
use memchr::memmem::Finder;

use crate::detectors::PyUnicodeTable;

/// `_INVISIBLE_RE` : invisibles, contrôles bidi, caractères « tag » ; le ZWJ des émojis est gardé.
/// Invisible characters, bidi controls, tag characters; the emoji ZWJ is kept.
fn invisible(c: char) -> bool {
    matches!(c,
        '\u{ad}' | '\u{180e}' | '\u{200b}' | '\u{200c}' | '\u{200e}' | '\u{200f}' | '\u{202a}'..='\u{202e}'
        | '\u{2060}'..='\u{2064}' | '\u{2066}'..='\u{2069}' | '\u{feff}' | '\u{e0000}'..='\u{e007f}')
}

/// Remplacements d'un motif, comme `re.sub` : la correspondance la plus à gauche, puis la suite après elle.
/// Replacements of a pattern, as `re.sub`: the leftmost match, then on after it. `matcher(start)` rend la fin
/// et le remplacement d'une correspondance en `start`, dont l'octet vaut `lead` / end and replacement at `start`.
fn substitute<'a>(
    text: Cow<'a, str>,
    lead: u8,
    mut matcher: impl FnMut(&str, usize) -> Option<(usize, String)>,
) -> Cow<'a, str> {
    let mut out: Option<String> = None;
    let (mut copied, mut pos) = (0, 0);
    while let Some(start) = text.as_bytes().get(pos..).and_then(|rest| memchr(lead, rest)).map(|i| pos + i) {
        match matcher(&text, start) {
            Some((end, replacement)) => {
                let out = out.get_or_insert_with(|| String::with_capacity(text.len()));
                out.push_str(text.get(copied..start).unwrap_or_default());
                out.push_str(&replacement);
                (copied, pos) = (end, end);
            }
            None => pos = start + 1,
        }
    }
    match out {
        None => text,
        Some(mut out) => {
            out.push_str(text.get(copied..).unwrap_or_default());
            Cow::Owned(out)
        }
    }
}

/// Octet où commence `suffix`, suffixe de `text` / byte where `suffix`, a suffix of `text`, starts.
fn offset(text: &str, suffix: &str) -> usize {
    text.len() - suffix.len()
}

/// Suite la plus longue (au plus `max` caractères) sans `stop` ; `None` si le texte finit avant `stop`.
/// Longest run (at most `max` characters) without `stop`; byte length of the run and what follows.
fn run_until(text: &str, max: usize, stop: impl Fn(char) -> bool) -> (usize, usize) {
    let mut count = 0;
    for (i, c) in text.char_indices() {
        if stop(c) || count == max {
            return (i, count);
        }
        count += 1;
    }
    (text.len(), count)
}

/// `_REMOTE_IMAGE_RE` : `!\[([^\]\n]{0,200})\]\(\s*(?:https?:)?//[^)\n]{1,2000}\)`.
fn remote_image(table: &PyUnicodeTable, text: &str, start: usize) -> Option<(usize, String)> {
    let rest = text.get(start..)?.strip_prefix("![")?;
    // Classe sans « ] » : la plus longue suite doit être suivie de « ] » / the longest run must close on ']'.
    let (alt_len, _) = run_until(rest, 200, |c| c == ']' || c == '\n');
    let alt = rest.get(..alt_len)?;
    let after = rest.get(alt_len..)?.strip_prefix("](")?.trim_start_matches(|c| table.is_space(c));
    // `(?:https?:)?//` : le préfixe ne compte que suivi de « // » (sinon retour arrière) / only before "//".
    let scheme = after.strip_prefix("https:").or_else(|| after.strip_prefix("http:")).filter(|a| a.starts_with("//"));
    let url = scheme.unwrap_or(after).strip_prefix("//")?;
    let (url_len, count) = run_until(url, 2000, |c| c == ')' || c == '\n');
    let close = url.get(url_len..)?.strip_prefix(')')?;
    if count == 0 {
        return None;
    }
    let replacement = if alt.is_empty() { "[image]".to_owned() } else { format!("[image: {alt}]") };
    Some((offset(text, close), replacement))
}

/// Position en caractères d'une position en octets, suivie pas à pas (positions croissantes : coût linéaire).
/// Character position of a byte position, followed step by step (increasing positions: linear cost).
#[derive(Default)]
struct CharCursor {
    byte: usize,
    chars: usize,
}

impl CharCursor {
    fn at(&mut self, text: &[u8], byte: usize) -> usize {
        // Octets de tête UTF-8 : un par caractère / UTF-8 lead bytes: one per character.
        let leads = |part: &[u8]| part.iter().filter(|&&b| (b as i8) >= -0x40).count();
        if byte >= self.byte {
            self.chars += text.get(self.byte..byte).map_or(0, leads);
        } else {
            self.chars = self.chars.saturating_sub(text.get(byte..self.byte).map_or(0, leads));
        }
        self.byte = byte;
        self.chars
    }
}

/// Fermeture d'une balise à `limit` caractères au plus (`[^>]{0,2000}>`, `[\s\S]{0,20000}?-->`) : la première
/// occurrence de `needle` après l'ouverture, qui doit tomber dans la limite. Les ouvertures arrivent dans l'ordre :
/// chaque octet n'est lu qu'une fois, même sur un texte hostile (« <!-- » répété sans fin), là où une lecture par
/// ouverture coûterait `limit` caractères chacune. A tag's closing within `limit` characters: the first `needle`
/// after the opening must fall within the limit. Openings come in order: every byte is read once, even on a hostile
/// text, where reading per opening would cost `limit` characters each.
struct Closer {
    needle: &'static [u8],
    /// Construit à la première ouverture (la plupart des textes n'en ont pas) / built on the first opening.
    finder: Option<Finder<'static>>,
    limit: usize,
    /// (cherché depuis, première occurrence à partir de là) / (searched from, first occurrence from there).
    cached: Option<(usize, Option<usize>)>,
    opened: CharCursor,
    closed: CharCursor,
}

impl Closer {
    fn new(needle: &'static [u8], limit: usize) -> Self {
        Self { needle, finder: None, limit, cached: None, opened: CharCursor::default(), closed: CharCursor::default() }
    }

    /// Octet de la première occurrence à partir de `from`, si elle est à `limit` caractères au plus.
    /// Byte of the first occurrence from `from`, when it is within `limit` characters.
    fn find(&mut self, text: &[u8], from: usize) -> Option<usize> {
        let found = match self.cached {
            // Aucune occurrence entre l'ancien départ et celle trouvée : encore la première / still the first one.
            Some((searched, found)) if searched <= from && found.is_none_or(|f| f >= from) => found,
            _ => {
                let finder = self.finder.get_or_insert_with(|| Finder::new(self.needle));
                let found = text.get(from..).and_then(|rest| finder.find(rest)).map(|i| from + i);
                self.cached = Some((from, found));
                found
            }
        }?;
        let distance = self.closed.at(text, found).saturating_sub(self.opened.at(text, from));
        (distance <= self.limit).then_some(found)
    }
}

/// Caractères égaux à « i », « m », « g » sous `re.IGNORECASE` (« İ », « ı »…) / equal under `re.IGNORECASE`.
type Img = [Vec<char>; 3];

/// `_HTML_IMG_RE` : `<img\b[^>]{0,2000}>`, sans casse au sens de `re` / case-insensitive as `re` sees it.
fn html_img(
    table: &PyUnicodeTable,
    img: &Img,
    closer: &mut Closer,
    text: &str,
    start: usize,
) -> Option<(usize, String)> {
    let mut chars = text.get(start..)?.strip_prefix('<')?.chars();
    for equivalents in img {
        if !equivalents.contains(&chars.next()?) {
            return None;
        }
    }
    let rest = chars.as_str();
    // `\b` après une lettre : pas de caractère de mot ensuite / no word character next.
    if rest.chars().next().is_some_and(|c| table.is_word(c)) {
        return None;
    }
    let close = closer.find(text.as_bytes(), offset(text, rest))?;
    Some((close + 1, "[image]".to_owned()))
}

/// `_HTML_COMMENT_RE` : `<!--(?!\s*page\b)[\s\S]{0,20000}?-->`.
fn html_comment(table: &PyUnicodeTable, closer: &mut Closer, text: &str, start: usize) -> Option<(usize, String)> {
    let body = text.get(start..)?.strip_prefix("<!--")?;
    // Marque de page gardée (`<!-- page 3 -->`) / page marker kept.
    let lead = body.trim_start_matches(|c| table.is_space(c));
    if lead.strip_prefix("page").is_some_and(|after| !after.chars().next().is_some_and(|c| table.is_word(c))) {
        return None;
    }
    // Paresseux : la première « --> » à 20 000 caractères au plus / lazy: the first "-->" within 20,000 chars.
    let close = closer.find(text.as_bytes(), offset(text, body))?;
    Some((close + 3, String::new()))
}

/// `sanitize_output`.
pub(crate) fn sanitize(table: &PyUnicodeTable, text: String) -> String {
    let text = if text.is_ascii() || !text.chars().any(invisible) {
        Cow::Owned(text)
    } else {
        Cow::Owned(text.chars().filter(|&c| !invisible(c)).collect())
    };
    let text = substitute(text, b'!', |t, s| remote_image(table, t, s));
    let img = ['i', 'm', 'g'].map(|letter| table.table().equivalents(letter));
    let mut images = Closer::new(b">", 2000);
    let text = substitute(text, b'<', |t, s| html_img(table, &img, &mut images, t, s));
    let mut comments = Closer::new(b"-->", 20_000);
    substitute(text, b'<', |t, s| html_comment(table, &mut comments, t, s)).into_owned()
}

#[cfg(test)]
mod tests {
    use super::Closer;

    #[test]
    fn closings_are_counted_in_characters_up_to_the_limit() {
        // « --> » aux octets 3 et 7 ; « é » compte pour un caractère / "-->" at bytes 3 and 7; "é" is one character.
        let text = "aé-->b-->".as_bytes();
        let mut closer = Closer::new(b"-->", 1);
        assert_eq!(closer.find(text, 0), None); // deux caractères avant / two characters before
        assert_eq!(closer.find(text, 1), Some(3));
        assert_eq!(closer.find(text, 6), Some(7));
        // Position en arrière (jamais en pratique) : toujours exact / backwards (never in practice): still exact.
        assert_eq!(closer.find(text, 1), Some(3));
        assert_eq!(closer.find(text, 10), None);
        assert_eq!(closer.find(text, 99), None);
    }
}
