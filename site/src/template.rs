//! Gabarits des pages : découpés une fois, rendus par quelques ajouts / page templates: split once, rendered by
//! a few appends.
//!
//! build.rs inclut aussi ce fichier (`#[path]`) : les gabarits sont découpés et contrôlés à la construction, les
//! valeurs de qualité (`{{q.*}}`, fixes) y sont déjà écrites dans la langue de la page ; seules les valeurs en
//! direct (`{{live.*}}`) restent à remplir à chaque requête. Tout autre `{{...}}` fait échouer la construction.
//! build.rs includes this file too: templates are split and checked at build time, quality values are written in
//! then; only live values are filled per request. Any other `{{...}}` fails the build.

use crate::format::{self, Lang};
use std::collections::BTreeMap;

/// Valeur en direct d'une page (`{{live.<nom>}}`) / a live value of a page.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Live {
    UsesHour,
    /// Dont essais du protocole public, dans l'heure / of which public protocol runs, in the last hour.
    UsesHourProtocol,
    BytesHour,
    DocsTotal,
    /// Documents des essais du protocole public, compris dans le total / public protocol documents, in the total.
    DocsProtocol,
    BytesTotal,
    VisitorsTotal,
    VisitorsToday,
    CpuPercent,
    RamUsed,
    RamTotal,
    RamPercent,
    Since,
}

impl Live {
    /// Toutes les valeurs, dans l'ordre du contrat / every value, in contract order.
    pub const ALL: [Live; 13] = [
        Live::UsesHour,
        Live::UsesHourProtocol,
        Live::BytesHour,
        Live::DocsTotal,
        Live::DocsProtocol,
        Live::BytesTotal,
        Live::VisitorsTotal,
        Live::VisitorsToday,
        Live::CpuPercent,
        Live::RamUsed,
        Live::RamTotal,
        Live::RamPercent,
        Live::Since,
    ];

    /// Nom dans `{{live.<nom>}}` et dans `data-live="<nom>"` / name in placeholders and `data-live`.
    pub fn name(self) -> &'static str {
        match self {
            Live::UsesHour => "uses_hour",
            Live::UsesHourProtocol => "uses_hour_protocol",
            Live::BytesHour => "bytes_hour",
            Live::DocsTotal => "docs_total",
            Live::DocsProtocol => "docs_protocol",
            Live::BytesTotal => "bytes_total",
            Live::VisitorsTotal => "visitors_total",
            Live::VisitorsToday => "visitors_today",
            Live::CpuPercent => "cpu_percent",
            Live::RamUsed => "ram_used",
            Live::RamTotal => "ram_total",
            Live::RamPercent => "ram_percent",
            Live::Since => "since",
        }
    }

    /// Nom de la variante, pour le code produit par build.rs / variant name, for build.rs generated code.
    pub fn ident(self) -> &'static str {
        match self {
            Live::UsesHour => "UsesHour",
            Live::UsesHourProtocol => "UsesHourProtocol",
            Live::BytesHour => "BytesHour",
            Live::DocsTotal => "DocsTotal",
            Live::DocsProtocol => "DocsProtocol",
            Live::BytesTotal => "BytesTotal",
            Live::VisitorsTotal => "VisitorsTotal",
            Live::VisitorsToday => "VisitorsToday",
            Live::CpuPercent => "CpuPercent",
            Live::RamUsed => "RamUsed",
            Live::RamTotal => "RamTotal",
            Live::RamPercent => "RamPercent",
            Live::Since => "Since",
        }
    }

    pub fn from_name(name: &str) -> Option<Live> {
        Live::ALL.into_iter().find(|live| live.name() == name)
    }

    /// Mise à jour en direct par le JavaScript (attribut `data-live`) ; la date de lancement ne change pas.
    /// Updated live by the JavaScript (`data-live` attribute); the launch date never changes.
    pub fn is_streamed(self) -> bool {
        self != Live::Since
    }
}

/// Morceau d'un gabarit découpé / a piece of a split template.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Seg<S> {
    Lit(S),
    Live(Live),
}

/// Valeur de quality.json : nombre (texte JSON d'origine) ou chaîne / number (original JSON text) or string.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum QValue {
    Num(String),
    Str(String),
}

/// Texte HTML d'une valeur de qualité dans une langue ; une date ISO seule s'écrit en toutes lettres (« 25 octobre
/// 2026 »). HTML text of a quality value in a language; a bare ISO date is written in words ("25 October 2026").
pub fn quality_text(value: &QValue, lang: Lang) -> Option<String> {
    match value {
        QValue::Num(raw) => format::decimal_text(raw, lang),
        QValue::Str(text) => Some(match format::parse_iso_date(text) {
            Some(days) => format::date_words(days, lang),
            None => escape_html(text),
        }),
    }
}

/// Valeur « pas encore mesurée » de quality.json, affichée « pas encore mesuré » / "not measured yet" mark.
pub const PENDING: &str = "\u{2014}";
/// Clés du protocole public en pourcentage (0 à 100) : indice « documents normalisés », puis « documents
/// difficiles » (hard_*, protocole 1.1) / public protocol keys in percent: normalised index, then difficult index.
pub const PROTOCOL_PERCENT: [&str; 8] = [
    "confidence_index",
    "confidence_ci_low",
    "confidence_ci_high",
    "mention_recall_pct",
    "hard_index",
    "hard_ci_low",
    "hard_ci_high",
    "hard_mention_recall_pct",
];
/// Clés du protocole public entières / integer public protocol keys.
pub const PROTOCOL_COUNTS: [&str; 5] = [
    "protocol_docs",
    "protocol_families",
    "real_corpora",
    "real_docs",
    "hard_docs",
];
/// Publiées avec l'indice difficile / published with the difficult index.
const WITH_HARD_INDEX: [&str; 3] = ["hard_ci_low", "hard_ci_high", "hard_docs"];
/// Publiées avec l'indice : sans elles, l'indice n'est pas lisible / published with the index, which needs them.
const WITH_INDEX: [&str; 6] = [
    "confidence_ci_low",
    "confidence_ci_high",
    "protocol_docs",
    "protocol_families",
    "protocol_date",
    "protocol_engine",
];

/// Deux notes par mode (fort, essentiel), en pourcentage : anonymisation (indice, intervalle, documents difficiles)
/// et codes utiles perdus (leurres masqués) / two scores per mode, in percent: anonymisation and useful codes lost.
pub const MODE_PREFIXES: [&str; 2] = ["fort", "ess"];
const MODE_SUFFIXES: [&str; 5] = ["index", "ci_low", "ci_high", "hard_index", "code_loss"];
/// Publiées avec l'indice d'un mode / published with a mode's index.
const WITH_MODE_INDEX: [&str; 3] = ["ci_low", "ci_high", "code_loss"];
/// Source des notes par mode : le protocole public, ou une mesure interne affichée comme telle.
/// Source of the per-mode scores: the public protocol, or an internal measurement shown as such.
pub const MODE_SOURCES: [&str; 2] = ["protocole 1.2", "mesure interne, moitié dev"];
const MODE_STRINGS: [&str; 3] = ["modes_source", "modes_date", "modes_engine"];

/// Version de moteur : 1 à 32 caractères, alphanumérique au début, puis [0-9A-Za-z.+-] / engine version shape.
fn version_shape(text: &str) -> bool {
    (1..=32).contains(&text.len())
        && text.starts_with(|c: char| c.is_ascii_alphanumeric())
        && text
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b".+-".contains(&byte))
}

/// Contrat des notes par mode : chaque clé présente, « — » ou bien formée ; l'indice d'un mode publié emporte son
/// intervalle (qui l'encadre), ses codes perdus, la source, la date et le moteur ; sans indice, rien du mode n'est
/// publié. Per-mode contract: every key present, pending or well formed; a published mode index brings its interval
/// (around it), its code loss, source, date and engine; without the index, nothing of that mode is published.
pub fn mode_contract_errors(quality: &BTreeMap<String, QValue>) -> Vec<String> {
    let mut errors = Vec::new();
    let pending =
        |key: &str| matches!(quality.get(key), Some(QValue::Str(text)) if text == PENDING);
    let number = |key: &str| match quality.get(key) {
        Some(QValue::Num(raw)) => raw.parse::<f64>().ok(),
        _ => None,
    };
    let percent_keys: Vec<String> = MODE_PREFIXES
        .iter()
        .flat_map(|prefix| {
            MODE_SUFFIXES
                .iter()
                .map(move |suffix| format!("{prefix}_{suffix}"))
        })
        .collect();
    let keys = percent_keys
        .iter()
        .map(String::as_str)
        .chain(MODE_STRINGS.iter().copied());
    for key in keys {
        let Some(value) = quality.get(key) else {
            errors.push(format!(
                "« {key} » absente (« {PENDING} » tant qu'elle n'est pas mesurée) / missing"
            ));
            continue;
        };
        if pending(key) {
            continue;
        }
        let well_formed = match (key, value) {
            ("modes_source", QValue::Str(text)) => MODE_SOURCES.contains(&text.as_str()),
            ("modes_date", QValue::Str(text)) => format::parse_iso_date(text).is_some(),
            ("modes_engine", QValue::Str(text)) => version_shape(text),
            (_, QValue::Num(_)) if !MODE_STRINGS.contains(&key) => {
                number(key).is_some_and(|value| (0.0..=100.0).contains(&value))
            }
            _ => false,
        };
        if !well_formed {
            errors.push(format!(
                "« {key} » = {value:?} : forme attendue / expected shape: {}",
                match key {
                    "modes_source" => "« protocole 1.2 » ou « mesure interne, moitié dev »",
                    "modes_date" => "date ISO / ISO date",
                    "modes_engine" => "version (« 1.0.2 »)",
                    _ => "pourcentage 0-100 / percentage 0-100",
                }
            ));
        }
    }
    for prefix in MODE_PREFIXES {
        let index = format!("{prefix}_index");
        if pending(&index) {
            for suffix in &MODE_SUFFIXES[1..] {
                let key = format!("{prefix}_{suffix}");
                if quality.contains_key(&key) && !pending(&key) {
                    errors.push(format!(
                        "« {key} » publiée sans « {index} » / published without the mode index"
                    ));
                }
            }
            continue;
        }
        for key in WITH_MODE_INDEX
            .iter()
            .map(|suffix| format!("{prefix}_{suffix}"))
            .chain(MODE_STRINGS.iter().map(|key| key.to_string()))
        {
            if pending(&key) {
                errors.push(format!(
                    "indice du mode publié sans « {key} » / mode index published without {key}"
                ));
            }
        }
        if let (Some(low), Some(value), Some(high)) = (
            number(&format!("{prefix}_ci_low")),
            number(&index),
            number(&format!("{prefix}_ci_high")),
        ) {
            if !(low <= value && value <= high) {
                errors.push(format!(
                    "intervalle {low}-{high} hors de « {index} » {value} / interval does not hold the mode index"
                ));
            }
        }
    }
    errors
}

/// Contrat des valeurs du protocole public dans quality.json (contrat D) : chaque clé présente, « — » tant qu'elle
/// n'est pas mesurée, sinon de la bonne forme (pourcentage, entier, date ISO, version) ; un indice publié emporte son
/// intervalle (qui l'encadre), le nombre de documents et de familles, la date et la version du moteur ; corpus et
/// documents réels vont ensemble. Public protocol values in quality.json: every key present, "—" until measured,
/// otherwise well formed; a published index brings its interval (around it), counts, date and engine version; real
/// corpora and real documents go together.
pub fn contract_errors(quality: &BTreeMap<String, QValue>) -> Vec<String> {
    let mut errors = Vec::new();
    let pending =
        |key: &str| matches!(quality.get(key), Some(QValue::Str(text)) if text == PENDING);
    let number = |key: &str| match quality.get(key) {
        Some(QValue::Num(raw)) => raw.parse::<f64>().ok(),
        _ => None,
    };
    let keys = PROTOCOL_PERCENT
        .iter()
        .chain(PROTOCOL_COUNTS.iter())
        .chain(["protocol_date", "protocol_engine"].iter());
    for &key in keys {
        let Some(value) = quality.get(key) else {
            errors.push(format!(
                "« {key} » absente (« {PENDING} » tant qu'elle n'est pas mesurée) / missing"
            ));
            continue;
        };
        if pending(key) {
            continue;
        }
        let well_formed = match (key, value) {
            ("protocol_date", QValue::Str(text)) => format::parse_iso_date(text).is_some(),
            ("protocol_engine", QValue::Str(text)) => version_shape(text),
            (_, QValue::Num(raw)) if PROTOCOL_COUNTS.contains(&key) => {
                raw.bytes().all(|byte| byte.is_ascii_digit())
            }
            (_, QValue::Num(_)) if PROTOCOL_PERCENT.contains(&key) => {
                number(key).is_some_and(|value| (0.0..=100.0).contains(&value))
            }
            _ => false,
        };
        if !well_formed {
            errors.push(format!(
                "« {key} » = {value:?} : forme attendue / expected shape: {}",
                match key {
                    "protocol_date" => "date ISO / ISO date",
                    "protocol_engine" => "version (« 1.0.0 »)",
                    _ if PROTOCOL_COUNTS.contains(&key) => "entier / integer",
                    _ => "pourcentage 0-100 / percentage 0-100",
                }
            ));
        }
    }
    if !pending("confidence_index") {
        for key in WITH_INDEX {
            if pending(key) {
                errors.push(format!(
                    "indice publié sans « {key} » / index published without {key}"
                ));
            }
        }
        if let (Some(low), Some(index), Some(high)) = (
            number("confidence_ci_low"),
            number("confidence_index"),
            number("confidence_ci_high"),
        ) {
            if !(low <= index && index <= high) {
                errors.push(format!(
                    "intervalle {low}-{high} hors de l'indice {index} / interval does not hold the index"
                ));
            }
        }
    }
    if !pending("hard_index") {
        for key in WITH_HARD_INDEX {
            if pending(key) {
                errors.push(format!(
                    "indice difficile publié sans « {key} » / difficult index published without {key}"
                ));
            }
        }
        if let (Some(low), Some(index), Some(high)) = (
            number("hard_ci_low"),
            number("hard_index"),
            number("hard_ci_high"),
        ) {
            if !(low <= index && index <= high) {
                errors.push(format!(
                    "intervalle {low}-{high} hors de l'indice difficile {index} / interval does not hold the difficult index"
                ));
            }
        }
    }
    if pending("real_corpora") != pending("real_docs") {
        errors.push("« real_corpora » et « real_docs » vont ensemble / go together".to_string());
    }
    errors.extend(mode_contract_errors(quality));
    errors
}

/// Échappement HTML (texte et attributs) / HTML escaping (text and attributes).
pub fn escape_html(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for character in text.chars() {
        match character {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#39;"),
            other => out.push(other),
        }
    }
    out
}

/// Découpe un gabarit : `{{q.*}}` remplacées, `{{live.*}}` gardées ; erreurs avec leur ligne.
/// Splits a template: quality placeholders replaced, live ones kept; errors carry their line.
pub fn compile(
    source: &str,
    quality: &BTreeMap<String, QValue>,
    lang: Lang,
) -> Result<Vec<Seg<String>>, Vec<String>> {
    let mut segs: Vec<Seg<String>> = Vec::new();
    let mut errors = Vec::new();
    let mut literal = String::with_capacity(source.len());
    let mut rest = source;
    let mut consumed = 0;
    while let Some(start) = rest.find("{{") {
        literal.push_str(&rest[..start]);
        let line = source[..consumed + start].matches('\n').count() + 1;
        let after = &rest[start + 2..];
        let Some(end) = after.find("}}") else {
            errors.push(format!(
                "ligne / line {line}: « {{{{ » sans « }}}} » / unterminated placeholder"
            ));
            rest = "";
            break;
        };
        let key = after[..end].trim();
        if let Some(name) = key.strip_prefix("live.") {
            match Live::from_name(name) {
                Some(live) => {
                    if !literal.is_empty() {
                        segs.push(Seg::Lit(std::mem::take(&mut literal)));
                    }
                    segs.push(Seg::Live(live));
                }
                None => errors.push(format!("ligne / line {line}: valeur en direct inconnue / unknown live value {{{{{key}}}}}")),
            }
        } else if let Some(name) = key.strip_prefix("q.") {
            match quality.get(name).map(|value| (value, quality_text(value, lang))) {
                Some((_, Some(text))) => literal.push_str(&text),
                Some((value, None)) => errors.push(format!(
                    "ligne / line {line}: nombre illisible dans quality.json / unreadable number {{{{{key}}}}} = {value:?}"
                )),
                None => errors.push(format!(
                    "ligne / line {line}: clé absente de quality.json / key missing from quality.json {{{{{key}}}}}"
                )),
            }
        } else {
            errors.push(format!(
                "ligne / line {line}: espace réservé inconnu / unknown placeholder {{{{{key}}}}}"
            ));
        }
        consumed += start + 2 + end + 2;
        rest = &after[end + 2..];
    }
    literal.push_str(rest);
    if !literal.is_empty() {
        segs.push(Seg::Lit(literal));
    }
    if errors.is_empty() {
        Ok(segs)
    } else {
        Err(errors)
    }
}

/// Rend une page : morceaux fixes et valeurs en direct / renders a page: fixed pieces and live values.
pub fn render<S: AsRef<str>>(segs: &[Seg<S>], mut value: impl FnMut(Live) -> String) -> String {
    let fixed: usize = segs
        .iter()
        .map(|seg| match seg {
            Seg::Lit(text) => text.as_ref().len(),
            Seg::Live(_) => 24,
        })
        .sum();
    let mut out = String::with_capacity(fixed);
    for seg in segs {
        match seg {
            Seg::Lit(text) => out.push_str(text.as_ref()),
            Seg::Live(live) => out.push_str(&value(*live)),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn quality() -> BTreeMap<String, QValue> {
        BTreeMap::from([
            ("tests_linux".to_string(), QValue::Num("3751".into())),
            ("ms_per_doc".to_string(), QValue::Num("0.45".into())),
            (
                "measured_on".to_string(),
                QValue::Str("2026-10-25 <OVH>".into()),
            ),
            ("bad".to_string(), QValue::Num("1e3".into())),
        ])
    }

    #[test]
    fn quality_values_are_written_in_the_page_language() {
        let source = "<p>{{q.tests_linux}} tests, {{ q.ms_per_doc }} ms, {{q.measured_on}}</p>";
        let fr = compile(source, &quality(), Lang::Fr).unwrap();
        assert_eq!(
            fr,
            vec![Seg::Lit(
                "<p>3\u{202F}751 tests, 0,45 ms, 2026-10-25 &lt;OVH&gt;</p>".to_string()
            )]
        );
        let en = compile(source, &quality(), Lang::En).unwrap();
        assert_eq!(
            en,
            vec![Seg::Lit(
                "<p>3,751 tests, 0.45 ms, 2026-10-25 &lt;OVH&gt;</p>".to_string()
            )]
        );
    }

    #[test]
    fn bare_iso_dates_are_written_in_words() {
        let quality = BTreeMap::from([
            ("measured_on".to_string(), QValue::Str("2026-10-25".into())),
            ("first".to_string(), QValue::Str("2027-05-01".into())),
            ("pending".to_string(), QValue::Str("\u{2014}".into())),
            ("bad".to_string(), QValue::Str("2026-02-30".into())),
        ]);
        let source = "{{q.measured_on}}|{{q.first}}|{{q.pending}}|{{q.bad}}";
        assert_eq!(
            compile(source, &quality, Lang::Fr).unwrap(),
            vec![Seg::Lit(
                "25 octobre 2026|1er mai 2027|\u{2014}|2026-02-30".to_string()
            )]
        );
        assert_eq!(
            compile(source, &quality, Lang::En).unwrap(),
            vec![Seg::Lit(
                "25 October 2026|1 May 2027|\u{2014}|2026-02-30".to_string()
            )]
        );
    }

    #[test]
    fn live_values_stay_as_segments() {
        let source = "{{live.uses_hour}}<b>{{live.since}}</b>{{live.ram_percent}}";
        let segs = compile(source, &quality(), Lang::Fr).unwrap();
        assert_eq!(
            segs,
            vec![
                Seg::Live(Live::UsesHour),
                Seg::Lit("<b>".to_string()),
                Seg::Live(Live::Since),
                Seg::Lit("</b>".to_string()),
                Seg::Live(Live::RamPercent),
            ]
        );
        let page = render(&segs, |live| live.name().to_uppercase());
        assert_eq!(page, "USES_HOUR<b>SINCE</b>RAM_PERCENT");
    }

    #[test]
    fn unknown_placeholders_are_errors_with_their_line() {
        let source = "a\n{{live.nope}}\n{{q.missing}} {{q.bad}}\n{{other}}\n{{live.uses_hour";
        let errors = compile(source, &quality(), Lang::En).unwrap_err();
        assert_eq!(errors.len(), 5, "{errors:?}");
        assert!(errors[0].contains("line 2") && errors[0].contains("{{live.nope}}"));
        assert!(errors[1].contains("line 3") && errors[1].contains("{{q.missing}}"));
        assert!(errors[2].contains("line 3") && errors[2].contains("{{q.bad}}"));
        assert!(errors[3].contains("line 4") && errors[3].contains("{{other}}"));
        assert!(errors[4].contains("line 5") && errors[4].contains("unterminated"));
    }

    #[test]
    fn every_live_name_round_trips() {
        for live in Live::ALL {
            assert_eq!(Live::from_name(live.name()), Some(live));
        }
        assert_eq!(Live::from_name("ram_used_bytes"), None);
        assert_eq!(Live::from_name("docs_protocol"), Some(Live::DocsProtocol));
        assert_eq!(
            Live::from_name("uses_hour_protocol"),
            Some(Live::UsesHourProtocol)
        );
        assert!(!Live::Since.is_streamed() && Live::RamPercent.is_streamed());
    }

    fn protocol(values: &[(&str, QValue)]) -> BTreeMap<String, QValue> {
        let mut quality: BTreeMap<String, QValue> = PROTOCOL_PERCENT
            .iter()
            .chain(PROTOCOL_COUNTS.iter())
            .chain(["protocol_date", "protocol_engine"].iter())
            .map(|key| (key.to_string(), QValue::Str(PENDING.into())))
            .collect();
        for prefix in MODE_PREFIXES {
            for suffix in MODE_SUFFIXES {
                quality.insert(format!("{prefix}_{suffix}"), QValue::Str(PENDING.into()));
            }
        }
        for key in MODE_STRINGS {
            quality.insert(key.to_string(), QValue::Str(PENDING.into()));
        }
        for (key, value) in values {
            quality.insert(key.to_string(), value.clone());
        }
        quality
    }

    #[test]
    fn protocol_values_are_pending_or_well_formed() {
        assert!(contract_errors(&protocol(&[])).is_empty());
        let num = |raw: &str| QValue::Num(raw.into());
        let published = protocol(&[
            ("confidence_index", num("91.4")),
            ("confidence_ci_low", num("89.0")),
            ("confidence_ci_high", num("93.2")),
            ("mention_recall_pct", num("96.1")),
            ("protocol_docs", num("12400")),
            ("protocol_families", num("7")),
            ("real_corpora", num("5")),
            ("real_docs", num("6100")),
            ("protocol_date", QValue::Str("2026-11-02".into())),
            ("protocol_engine", QValue::Str("1.0.0".into())),
            ("hard_index", num("74.0")),
            ("hard_ci_low", num("73.5")),
            ("hard_ci_high", num("74.6")),
            ("hard_docs", num("548907")),
            ("hard_mention_recall_pct", num("90.0")),
        ]);
        assert!(
            contract_errors(&published).is_empty(),
            "{:?}",
            contract_errors(&published)
        );
        // Formes fausses / wrong shapes.
        for (key, value) in [
            ("confidence_index", num("101")),
            ("protocol_docs", num("12.5")),
            ("protocol_date", QValue::Str("2026-02-30".into())),
            ("protocol_engine", QValue::Str("v 1".into())),
            ("mention_recall_pct", QValue::Str("n/a".into())),
        ] {
            let mut quality = published.clone();
            quality.insert(key.to_string(), value);
            let errors = contract_errors(&quality);
            assert!(
                errors.iter().any(|error| error.contains(key)),
                "{key}: {errors:?}"
            );
        }
        // Indice publié seul, intervalle qui ne l'encadre pas, corpus réels sans documents.
        // Index alone, interval not holding it, real corpora without documents.
        let alone = protocol(&[("confidence_index", num("91.4"))]);
        assert_eq!(contract_errors(&alone).len(), WITH_INDEX.len());
        let mut outside = published.clone();
        outside.insert("confidence_ci_high".to_string(), num("90.0"));
        assert!(contract_errors(&outside)[0].contains("interval"));
        let mut half = published.clone();
        half.insert("real_docs".to_string(), QValue::Str(PENDING.into()));
        assert_eq!(contract_errors(&half).len(), 1);
        // Indice difficile seul, ou hors de son intervalle / difficult index alone, or outside its interval.
        let hard_alone = protocol(&[("hard_index", num("74.0"))]);
        assert_eq!(contract_errors(&hard_alone).len(), WITH_HARD_INDEX.len());
        let mut hard_outside = published.clone();
        hard_outside.insert("hard_ci_low".to_string(), num("75.0"));
        assert!(contract_errors(&hard_outside)[0].contains("difficult index"));
        let mut hard_shape = published.clone();
        hard_shape.insert("hard_docs".to_string(), num("1.5"));
        assert!(contract_errors(&hard_shape)[0].contains("hard_docs"));
        let mut missing = protocol(&[]);
        missing.remove("protocol_engine");
        assert!(contract_errors(&missing)[0].contains("protocol_engine"));
    }

    #[test]
    fn mode_scores_are_pending_or_published_with_their_interval_and_source() {
        let num = |raw: &str| QValue::Num(raw.into());
        let text = |raw: &str| QValue::Str(raw.into());
        assert!(contract_errors(&protocol(&[])).is_empty());
        let internal = protocol(&[
            ("fort_index", num("96.1")),
            ("fort_ci_low", num("95.4")),
            ("fort_ci_high", num("96.8")),
            ("fort_hard_index", num("85.0")),
            ("fort_code_loss", num("17.4")),
            ("ess_index", num("94.0")),
            ("ess_ci_low", num("93.1")),
            ("ess_ci_high", num("94.9")),
            ("ess_code_loss", num("3.7")),
            ("modes_source", text("mesure interne, moitié dev")),
            ("modes_date", text("2026-10-26")),
            ("modes_engine", text("1.0.2")),
        ]);
        assert!(
            contract_errors(&internal).is_empty(),
            "{:?}",
            contract_errors(&internal)
        );
        // Une source inconnue, une date fausse, un pourcentage hors bornes / unknown source, bad date, bad percent.
        for (key, value) in [
            ("modes_source", text("protocole 1.1")),
            ("modes_date", text("2026-13-01")),
            ("modes_engine", text("v 1")),
            ("fort_code_loss", num("120")),
            ("ess_index", text("n/a")),
        ] {
            let mut quality = internal.clone();
            quality.insert(key.to_string(), value);
            let errors = contract_errors(&quality);
            assert!(
                errors.iter().any(|error| error.contains(key)),
                "{key}: {errors:?}"
            );
        }
        // Indice seul : intervalle, codes perdus, source, date et moteur manquent / index alone: five missing.
        let alone = protocol(&[("fort_index", num("96.1"))]);
        assert_eq!(
            contract_errors(&alone).len(),
            WITH_MODE_INDEX.len() + MODE_STRINGS.len()
        );
        // Intervalle qui n'encadre pas l'indice / interval not holding the index.
        let mut outside = internal.clone();
        outside.insert("ess_ci_high".to_string(), num("93.5"));
        assert!(contract_errors(&outside)[0].contains("ess_index"));
        // Codes perdus publiés sans l'indice du mode / code loss published without the mode index.
        let mut orphan = internal.clone();
        orphan.insert("ess_index".to_string(), text(PENDING));
        orphan.insert("ess_ci_low".to_string(), text(PENDING));
        orphan.insert("ess_ci_high".to_string(), text(PENDING));
        let errors = contract_errors(&orphan);
        assert_eq!(errors.len(), 1, "{errors:?}");
        assert!(errors[0].contains("ess_code_loss"));
        // Une clé absente / a missing key.
        let mut missing = internal.clone();
        missing.remove("modes_engine");
        assert!(contract_errors(&missing)[0].contains("modes_engine"));
    }

    #[test]
    fn single_braces_are_plain_text() {
        let source = "{\"a\": {\"b\": 1}} { {x} }";
        assert_eq!(
            compile(source, &quality(), Lang::En).unwrap(),
            vec![Seg::Lit(source.to_string())]
        );
    }
}
