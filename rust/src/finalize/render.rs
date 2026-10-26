//! Rendu : opérateurs, compteurs du rapport et explications (`engine._render`, `operators.py`).
//!
//! Rendering: operators, report counters and explanations. Les explications donnent la balise produite,
//! la règle et la raison, jamais la valeur d'origine. Explanations give the produced tag, the rule and the
//! reason, never the original value.

use std::collections::{BTreeMap, HashMap, HashSet};

use super::chars::{Chars, ALNUM, DIGIT};
use super::indexed::IndexedText;
use super::scope::{Scope, ScopeClosed};
use super::span::Span;

/// Opérateurs de `operators.py`, tous irréversibles / the operators of `operators.py`, all irreversible.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Operator {
    Replace,
    Redact,
    Mask,
    Generalize,
    Keep,
}

impl Operator {
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "replace" => Some(Self::Replace),
            "redact" => Some(Self::Redact),
            "mask" => Some(Self::Mask),
            "generalize" => Some(Self::Generalize),
            "keep" => Some(Self::Keep),
            _ => None,
        }
    }
}

/// Ce qu'un recognizer apporte aux raisons (`docs/EXPLAIN.md`) / what a recognizer tells the reasons.
pub struct Recognizer {
    pub tier: String,
    pub validator: bool,
}

/// Réglages du rendu, fixés à la construction / rendering settings, fixed at construction.
pub struct RenderRules {
    /// `Settings.operators`, par entité ou par libellé / by entity or by label.
    pub operators: HashMap<String, Operator>,
    /// `operators.FORCED_REPLACE`.
    pub forced_replace: HashSet<String>,
    /// `engine._DETECTOR_REASONS`.
    pub detector_reasons: HashMap<String, String>,
    /// `engine._recognizers_by_id` des packs chargés / of the loaded packs.
    pub recognizers: HashMap<String, Recognizer>,
}

/// Ligne d'explication agrégée (`engine._aggregate`) / aggregated explain line.
pub struct ExplainLine {
    /// « kept » (conservée par politique) ou « tag » (remplacée) / kept by policy or replaced.
    pub kept: bool,
    pub tag: String,
    pub rule: String,
    pub reason: String,
    pub count: u64,
}

/// Compteurs et explications d'un ou plusieurs rendus / counters and explanations of one or more renderings.
#[derive(Default)]
pub struct Tally {
    /// Balises remplacées, par libellé affiché / replaced placeholders, by displayed label.
    pub replaced: BTreeMap<String, u64>,
    /// Valeurs conservées par politique, par clé de libellé / values kept by policy, by label key.
    pub kept: BTreeMap<String, u64>,
    /// Lignes dans l'ordre de première apparition / lines in first-seen order.
    pub explain: Option<Vec<ExplainLine>>,
    lines: HashMap<(bool, String, String, String), usize>,
}

impl Tally {
    pub fn new(explain: bool) -> Self {
        Self { explain: explain.then(Vec::new), ..Self::default() }
    }

    fn explain(&mut self, kept: bool, tag: String, rule: &str, reason: String) {
        let Some(lines) = self.explain.as_mut() else {
            return;
        };
        let key = (kept, tag, rule.to_owned(), reason);
        if let Some(line) = self.lines.get(&key).and_then(|&i| lines.get_mut(i)) {
            line.count += 1;
            return;
        }
        self.lines.insert(key.clone(), lines.len());
        let (kept, tag, rule, reason) = key;
        lines.push(ExplainLine { kept, tag, rule, reason, count: 1 });
    }
}

/// `Counter[key] += 1`, sans allouer de clé déjà connue / without allocating a known key.
fn count(counts: &mut BTreeMap<String, u64>, key: &str) {
    match counts.get_mut(key) {
        Some(count) => *count += 1,
        None => {
            counts.insert(key.to_owned(), 1);
        }
    }
}

/// `engine._rule_of` : règle à l'origine d'une zone, préfixes retirés / rule behind a span, prefixes removed.
fn rule_of(source: &str) -> &str {
    let mut rule = source.split_once('+').map_or(source, |(first, _)| first);
    for prefix in ["keep:", "propagated:"] {
        if let Some(rest) = rule.strip_prefix(prefix) {
            rule = rest;
        }
    }
    rule
}

/// `span.value or original`.
fn value_or<'a>(span: &'a Span, original: &'a str) -> &'a str {
    match span.value.as_deref() {
        Some(value) if !value.is_empty() => value,
        _ => original,
    }
}

/// `operators.mask` : garde les 4 derniers caractères alphanumériques / keeps the last 4 alphanumerics.
fn mask(chars: &Chars, original: &str) -> String {
    let mut out: Vec<char> = original.chars().collect();
    let mut kept = 0;
    for c in out.iter_mut().rev() {
        if chars.is(*c, ALNUM) {
            if kept < 4 {
                kept += 1;
            } else {
                *c = '*';
            }
        }
    }
    out.into_iter().collect()
}

/// `_YEAR_RE.search` : première année `(?:18|19|20)[0-9]{2}` / first year match.
fn year(text: &str) -> Option<&str> {
    let start = text.as_bytes().windows(4).position(
        |w| matches!(w, [b'1', b'8' | b'9', c, d] | [b'2', b'0', c, d] if c.is_ascii_digit() && d.is_ascii_digit()),
    )?;
    text.get(start..start + 4)
}

impl RenderRules {
    /// Opérateur configuré ; les secrets sont toujours remplacés / configured operator; secrets always replaced.
    fn operator(&self, span: &Span) -> Operator {
        if self.forced_replace.contains(&*span.entity) {
            return Operator::Replace;
        }
        self.operators
            .get(&*span.entity)
            .or_else(|| self.operators.get(&*span.label))
            .copied()
            .unwrap_or(Operator::Replace)
    }

    /// Remplacement d'une zone, écrit à la suite de `out` / a span's replacement, written at the end of `out`.
    #[allow(clippy::too_many_arguments)]
    fn apply(
        &self,
        operator: Operator,
        chars: &Chars,
        scope: &mut Scope,
        span: &Span,
        display: &str,
        original: &str,
        out: &mut String,
    ) -> Result<(), ScopeClosed> {
        let entity = &*span.entity;
        match operator {
            Operator::Replace => return scope.placeholder_into(chars, display, entity, value_or(span, original), out),
            Operator::Redact => out.extend(["[", display, "]"]),
            Operator::Mask => out.push_str(&mask(chars, original)),
            Operator::Keep => out.push_str(original),
            Operator::Generalize => {
                // Date -> année, code postal -> département ; sinon balise / date -> year, postcode -> department.
                if matches!(entity, "BIRTH_DATE" | "DATE") {
                    if let Some(year) = year(value_or(span, original)) {
                        out.push_str(year);
                        return Ok(());
                    }
                }
                if entity == "POSTAL_CODE" {
                    let digits: Vec<char> = original.chars().filter(|&c| chars.is(c, DIGIT)).collect();
                    if let [a, b, c, ..] = digits[..] {
                        if digits.len() == 5 {
                            let kept: &[char] = if a == '9' && matches!(b, '7' | '8') { &[a, b, c] } else { &[a, b] };
                            out.extend(kept);
                            out.push_str(if kept.len() == 3 { "xx" } else { "xxx" });
                            return Ok(());
                        }
                    }
                }
                return scope.placeholder_into(chars, display, entity, value_or(span, original), out);
            }
        }
        Ok(())
    }

    /// `Anonymizer._reason` : raison stable et documentée d'une détection / stable, documented reason code.
    fn reason(&self, chars: &Chars, span: &Span) -> String {
        let source = span.source.split_once('+').map_or(&*span.source, |(first, _)| first);
        let validated = span.value.is_some();
        let reason = if source.starts_with("propagated:") {
            "propagation"
        } else if source == "deny_list" {
            "deny_list"
        } else if source.starts_with("CUSTOM_") {
            "custom_rule"
        } else if let Some(reason) = span.reason.as_deref() {
            reason // raison propre à la règle (« civil_status_nearby ») / the rule's own reason
        } else if source == "INTL_IBAN" {
            if validated {
                "validated"
            } else {
                "iban_layout_despite_invalid_key"
            }
        } else if let Some(reason) = self.detector_reasons.get(source).filter(|r| !r.is_empty()) {
            return reason.clone();
        } else if chars.lower_starts_with(source, "ner") {
            "ner_model"
        } else {
            match self.recognizers.get(source) {
                None => "detector",
                Some(rec) if rec.tier == "L" => {
                    if validated {
                        "validated"
                    } else {
                        "printed_layout"
                    }
                }
                // Clé fausse, mot-clé explicite / wrong key, explicit keyword.
                Some(rec) if rec.validator && !validated => "keyword_despite_invalid_key",
                Some(rec) if rec.validator => {
                    if rec.tier == "A" {
                        "validated"
                    } else {
                        "validated_and_keyword"
                    }
                }
                Some(rec) if rec.tier == "A" => "format",
                Some(_) => "keyword",
            }
        };
        reason.to_owned()
    }

    /// `Anonymizer._render` sur un texte : chaque zone avec son libellé affiché, triées par début.
    /// `Anonymizer._render` over one text: each span with its displayed label, sorted by start.
    pub fn render<'s>(
        &self,
        chars: &Chars,
        scope: &mut Scope,
        text: &IndexedText,
        spans: impl IntoIterator<Item = (&'s Span, &'s str)>,
        tally: &mut Tally,
    ) -> Result<String, ScopeClosed> {
        let mut out = String::with_capacity(text.as_str().len());
        let mut last = 0;
        for (span, display) in spans {
            if !span.personal {
                count(&mut tally.kept, &span.label);
                if tally.explain.is_some() {
                    let reason = if span.source.starts_with("keep:") { "keep_rule" } else { "company_policy" };
                    tally.explain(true, display.to_owned(), rule_of(&span.source), reason.to_owned());
                }
                continue;
            }
            let original = text.slice(span.start, span.end);
            out.push_str(text.slice(last, span.start));
            let tag = out.len();
            self.apply(self.operator(span), chars, scope, span, display, original, &mut out)?;
            last = span.end;
            count(&mut tally.replaced, display);
            if tally.explain.is_some() {
                let reason = self.reason(chars, span);
                let output = out.get(tag..).unwrap_or_default().to_owned();
                tally.explain(false, output, rule_of(&span.source), reason);
            }
        }
        out.push_str(text.tail(last));
        Ok(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::finalize::chars::test_rules;

    #[test]
    fn operators_are_irreversible() {
        let rules = test_rules();
        let chars = Chars::new(&rules);
        assert_eq!(mask(&chars, "4111 1111 1111 1234"), "**** **** **** 1234");
        assert_eq!(year("le 03/03/1985."), Some("1985"));
        assert_eq!(year("2101 1799"), None);
        assert_eq!(rule_of("keep:propagated:FR_NIR+X"), "FR_NIR");
    }
}
