//! Compteurs du site : usage du service, visiteurs, charge du serveur / site counters: service usage, visitors,
//! server load.
//!
//! Que des nombres : aucune adresse, aucune empreinte, aucun nom de fichier n'est gardé ni écrit. Les visiteurs du
//! jour sont reconnus par une empreinte SipHash à clé de (adresse déjà tronquée par Nginx, agent utilisateur) ; la
//! clé (128 bits) est tirée au démarrage et à chaque changement de jour UTC, l'ensemble des empreintes du jour ne vit
//! qu'en mémoire et disparaît avec la clé. Only numbers: no address, digest or file name is kept or written. Today's
//! visitors are recognised by a keyed SipHash of (address already truncated by Nginx, user agent); the key is drawn
//! at start and at every UTC day change, and today's digests live in memory only, dropped with the key.
//!
//! Un redémarrage (déploiement, panne) oublie les empreintes du jour : un visiteur déjà venu ce jour-là est alors
//! compté une seconde fois. C'est voulu : garder empreintes et clé hors du processus ne vaut pas ce léger surcompte.
//! A restart forgets today's digests, so a visitor already seen that day counts again: keeping digests and key
//! outside the process is not worth avoiding that small overcount.

use crate::format::{self, Lang};
use crate::template::Live;
use serde_json::{Map, Value, json};
use siphasher::sip::SipHasher24;
use std::collections::{HashMap, HashSet};
use std::hash::Hasher;

/// Sortes d'opérations du service (contrat, point 6) / service operation kinds (contract item 6).
pub const KINDS: [&str; 5] = ["text", "file", "upload", "mcp_text", "mcp_file"];
/// Formats d'entrée (contrat, point 6) / input formats (contract item 6).
pub const FORMATS: [&str; 18] = [
    "text", "pdf", "docx", "doc", "xlsx", "xls", "pptx", "odt", "ods", "odp", "rtf", "eml", "msg",
    "html", "csv", "tsv", "md", "other",
];
/// Origines d'une opération (champ facultatif `src`, absent = `public`) : trafic ordinaire, ou essai du protocole
/// public lancé sur le serveur lui-même (principal local, sans en-tête d'adresse client). Operation origins
/// (optional `src` field, missing = `public`): ordinary traffic, or a public protocol run launched on the server.
pub const SOURCES: [&str; 2] = ["public", "protocol"];
/// Taille maximale d'un datagramme accepté / largest accepted datagram.
pub const MAX_DATAGRAM: usize = 512;
/// Datagrammes traités par seconde au plus / datagrams handled per second at most.
pub const MAX_DATAGRAMS_PER_SECOND: u32 = 2000;
/// Visiteurs distincts reconnus par jour au plus (mémoire bornée) / distinct visitors recognised per day at most.
pub const MAX_VISITORS_PER_DAY: usize = 200_000;
/// Agents distincts comptés par adresse tronquée et par jour : un hôte qui change d'agent à chaque requête ne gonfle
/// pas le compte. Distinct user agents counted per truncated address per day: a host changing its user agent on
/// every request cannot inflate the count.
pub const MAX_AGENTS_PER_ADDRESS: u8 = 8;
/// Plus gros envoi plausible (bien au-delà des 50 Mo du service) ; au-delà, datagramme refusé.
/// Largest plausible input (far above the service's 50 MB); beyond it, the datagram is refused.
pub const MAX_INPUT_BYTES: u64 = 1 << 28;
/// Plus longue durée plausible d'une opération, en millisecondes (une heure) / longest plausible operation (1 h).
pub const MAX_OPERATION_MS: f64 = 3_600_000.0;
const MINUTES: usize = 60;
const DAY: u64 = 86_400;

/// Agents utilisateurs des robots évidents (en minuscules) / obvious robot user agents (lowercase).
const ROBOTS: [&str; 12] = [
    "bot",
    "crawl",
    "spider",
    "slurp",
    "curl",
    "wget",
    "python",
    "go-http",
    "java/",
    "headless",
    "monitoring",
    "uptime",
];

/// Une opération terminée, lue d'un datagramme / a finished operation, read from a datagram.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Usage {
    pub kind: usize,
    pub format: usize,
    pub bytes: u64,
    pub ms: f64,
    pub ok: bool,
    /// Essai du protocole public (`"src":"protocol"`) / public protocol run.
    pub protocol: bool,
}

/// Lit un datagramme du service ; None s'il est mal formé, trop grand, hors bornes, ou d'une sorte, d'un format ou
/// d'une origine inconnus. Reads a service datagram; None when malformed, too large, out of bounds, or of an unknown
/// kind, format or origin.
///
/// Forme exacte / exact shape: `{"v":1,"kind":K,"fmt":F,"bytes":N,"ms":M,"ok":B,"src":S}`, `src` facultatif
/// (absent : `public`) parmi [`SOURCES`], aucun autre champ ; `N` ≤ [`MAX_INPUT_BYTES`], `M` dans / in
/// `0..=`[`MAX_OPERATION_MS`]. `src` is optional (missing: `public`), no other field.
pub fn parse_datagram(data: &[u8]) -> Option<Usage> {
    if data.len() > MAX_DATAGRAM {
        return None;
    }
    let value: Value = serde_json::from_slice(data).ok()?;
    let fields = value.as_object()?;
    if fields.get("v")?.as_u64()? != 1 {
        return None;
    }
    // Six champs, ou sept avec `src` : tout autre champ fait refuser le datagramme / six fields, or seven with `src`.
    let protocol = match fields.len() {
        6 => false,
        7 => match fields.get("src")?.as_str()? {
            "public" => false,
            "protocol" => true,
            _ => return None,
        },
        _ => return None,
    };
    let kind = fields.get("kind")?.as_str()?;
    let format = fields.get("fmt")?.as_str()?;
    let bytes = fields.get("bytes")?.as_u64()?;
    let ms = fields.get("ms")?.as_f64()?;
    // NaN échoue aussi / NaN fails too.
    if bytes > MAX_INPUT_BYTES || !(0.0..=MAX_OPERATION_MS).contains(&ms) {
        return None;
    }
    Some(Usage {
        kind: KINDS.iter().position(|known| *known == kind)?,
        format: FORMATS.iter().position(|known| *known == format)?,
        bytes,
        ms,
        ok: fields.get("ok")?.as_bool()?,
        protocol,
    })
}

/// Robot évident, ou agent absent / obvious robot, or no user agent.
pub fn is_robot(user_agent: &[u8]) -> bool {
    let text = String::from_utf8_lossy(user_agent).to_ascii_lowercase();
    text.trim().is_empty() || ROBOTS.iter().any(|robot| text.contains(robot))
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct Bucket {
    minute: u64,
    count: u64,
    bytes: u64,
    /// Dont essais du protocole public / of which public protocol runs.
    protocol: u64,
}

/// Valeurs montrées par la page et par /api/stats / values shown by the page and /api/stats.
///
/// Les tailles (`bytes_hour`, `bytes_total`) sont arrondies à la précision affichée ([`format::rounded_bytes`]) :
/// quand le trafic est faible, une variation ne donne pas la taille exacte du document d'un utilisateur. Sizes are
/// rounded to the shown precision, so a change never reveals one user's exact document size.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Snapshot {
    pub uses_hour: u64,
    /// Documents du protocole public dans l'heure, compris dans `uses_hour` : une campagne ne passe pas pour du
    /// trafic. Public protocol documents in the last hour, included in `uses_hour`, so a run never reads as traffic.
    pub uses_hour_protocol: u64,
    pub bytes_hour: u64,
    pub docs_total: u64,
    /// Documents des essais du protocole public, compris dans `docs_total` / public protocol documents, included in
    /// `docs_total`.
    pub docs_protocol: u64,
    pub bytes_total: u64,
    pub visitors_total: u64,
    pub visitors_today: u64,
    pub cpu_percent: f64,
    pub ram_used: u64,
    pub ram_total: u64,
    /// Jour de lancement (jours depuis 1970-01-01) / launch day.
    pub since: i64,
    pub updated: u64,
}

impl Snapshot {
    /// Mémoire utilisée en pourcentage, calculée comme le JavaScript (utilisée / totale × 100).
    /// Memory used in percent, computed like the JavaScript (used / total × 100).
    pub fn ram_percent(&self) -> f64 {
        if self.ram_total == 0 {
            0.0
        } else {
            self.ram_used as f64 / self.ram_total as f64 * 100.0
        }
    }

    fn cpu(&self) -> f64 {
        if self.cpu_percent.is_finite() {
            self.cpu_percent.clamp(0.0, 100.0)
        } else {
            0.0
        }
    }

    /// JSON du contrat (point 3) ; processeur arrondi au dixième / contract JSON (item 3); processor to a tenth.
    pub fn json(&self) -> String {
        let cpu = format::tenth_text(self.cpu());
        format!(
            concat!(
                "{{\"uses_hour\":{},\"uses_hour_protocol\":{},\"bytes_hour\":{},\"docs_total\":{},",
                "\"docs_protocol\":{},\"bytes_total\":{},\"visitors_total\":{},\"visitors_today\":{},",
                "\"cpu_percent\":{},\"ram_used_bytes\":{},\"ram_total_bytes\":{},\"since\":\"{}\",\"updated\":{}}}"
            ),
            self.uses_hour,
            self.uses_hour_protocol,
            self.bytes_hour,
            self.docs_total,
            self.docs_protocol,
            self.bytes_total,
            self.visitors_total,
            self.visitors_today,
            cpu,
            self.ram_used,
            self.ram_total,
            format::iso_date(self.since),
            self.updated,
        )
    }

    /// Texte d'une valeur en direct dans une langue / a live value's text in a language.
    pub fn text(&self, live: Live, lang: Lang) -> String {
        match live {
            Live::UsesHour => format::int(self.uses_hour, lang),
            Live::UsesHourProtocol => format::int(self.uses_hour_protocol, lang),
            Live::BytesHour => format::bytes(self.bytes_hour, lang),
            Live::DocsTotal => format::int(self.docs_total, lang),
            Live::DocsProtocol => format::int(self.docs_protocol, lang),
            Live::BytesTotal => format::bytes(self.bytes_total, lang),
            Live::VisitorsTotal => format::int(self.visitors_total, lang),
            Live::VisitorsToday => format::int(self.visitors_today, lang),
            Live::CpuPercent => format::one_decimal(self.cpu(), lang),
            Live::RamUsed => format::bytes(self.ram_used, lang),
            Live::RamTotal => format::bytes(self.ram_total, lang),
            Live::RamPercent => format::one_decimal(self.ram_percent(), lang),
            Live::Since => format::date_words(self.since, lang),
        }
    }
}

/// Tous les compteurs / every counter.
pub struct Stats {
    launch: i64,
    visitors_closed: u64,
    today: i64,
    visitors_today: u64,
    seen: HashSet<u64>,
    /// Agents comptés aujourd'hui par adresse tronquée (empreinte à clé) / agents counted today per address.
    per_address: HashMap<u64, u8>,
    key: [u8; 16],
    docs_total: u64,
    docs_protocol: u64,
    bytes_total: u64,
    failed_total: u64,
    ms_total: u64,
    kinds: [u64; KINDS.len()],
    formats: [u64; FORMATS.len()],
    minutes: [Bucket; MINUTES],
    rate_second: u64,
    rate_count: u32,
    cpu_percent: f64,
    ram_used: u64,
    ram_total: u64,
}

fn day_of(now: u64) -> i64 {
    (now / DAY) as i64
}

/// Clé de 128 bits tirée par le système / 128-bit key drawn by the operating system.
fn fresh_key() -> [u8; 16] {
    let mut key = [0u8; 16];
    // Sous Linux, getrandom(2) n'échoue plus après l'amorçage / never fails after boot on Linux.
    getrandom::fill(&mut key).expect("getrandom");
    key
}

impl Stats {
    /// Compteurs neufs : lancement aujourd'hui / fresh counters: launched today.
    pub fn new(now: u64) -> Stats {
        Stats {
            launch: day_of(now),
            visitors_closed: 0,
            today: day_of(now),
            visitors_today: 0,
            seen: HashSet::new(),
            per_address: HashMap::new(),
            key: fresh_key(),
            docs_total: 0,
            docs_protocol: 0,
            bytes_total: 0,
            failed_total: 0,
            ms_total: 0,
            kinds: [0; KINDS.len()],
            formats: [0; FORMATS.len()],
            minutes: [Bucket::default(); MINUTES],
            rate_second: 0,
            rate_count: 0,
            cpu_percent: 0.0,
            ram_used: 0,
            ram_total: 0,
        }
    }

    /// Changement de jour UTC : total clos, empreintes oubliées, nouvelle clé / UTC day change: total closed,
    /// digests forgotten, new key.
    pub fn roll_day(&mut self, now: u64) {
        let day = day_of(now);
        if day > self.today {
            self.visitors_closed = self.visitors_closed.saturating_add(self.visitors_today);
            self.visitors_today = 0;
            self.seen = HashSet::new();
            self.per_address = HashMap::new();
            self.key = fresh_key();
            self.today = day;
        }
    }

    /// Une visite de la page ; vrai si c'est un nouveau visiteur du jour / a page visit; true for a new visitor.
    /// `address` : adresse déjà tronquée par Nginx (/24, /48) / address already truncated by Nginx.
    ///
    /// Au plus [`MAX_AGENTS_PER_ADDRESS`] agents distincts par adresse tronquée et par jour : le compte reste une
    /// borne basse prudente, jamais gonflé par un hôte qui change d'agent. At most that many distinct agents per
    /// truncated address per day: the count stays a cautious lower bound.
    pub fn visit(&mut self, address: &[u8], user_agent: &[u8], now: u64) -> bool {
        self.roll_day(now);
        if is_robot(user_agent) {
            return false;
        }
        let mut hasher = SipHasher24::new_with_key(&self.key);
        hasher.write(address);
        let network = hasher.finish();
        hasher.write_u8(0);
        hasher.write(user_agent);
        let digest = hasher.finish();
        if self.seen.contains(&digest) || self.seen.len() >= MAX_VISITORS_PER_DAY {
            return false;
        }
        let agents = self.per_address.get(&network).copied().unwrap_or(0);
        if agents >= MAX_AGENTS_PER_ADDRESS {
            return false;
        }
        self.per_address.insert(network, agents + 1);
        self.seen.insert(digest);
        self.visitors_today = self.visitors_today.saturating_add(1);
        true
    }

    /// Plafond de débit des datagrammes ; faux au-delà de 2000 dans la seconde / datagram rate cap.
    pub fn admit_datagram(&mut self, now: u64) -> bool {
        if now != self.rate_second {
            self.rate_second = now;
            self.rate_count = 0;
        }
        self.rate_count = self.rate_count.saturating_add(1);
        self.rate_count <= MAX_DATAGRAMS_PER_SECOND
    }

    /// Compte une opération terminée ; seules les réussies sont des documents, ceux du protocole public comptés
    /// aussi à part / counts a finished operation; only successful ones are documents, public protocol ones also
    /// counted apart. Compteurs saturés, jamais remis à zéro par un débordement / saturating counters.
    pub fn record(&mut self, usage: Usage, now: u64) {
        if !usage.ok {
            self.failed_total = self.failed_total.saturating_add(1);
            return;
        }
        self.docs_total = self.docs_total.saturating_add(1);
        if usage.protocol {
            self.docs_protocol = self.docs_protocol.saturating_add(1);
        }
        self.bytes_total = self.bytes_total.saturating_add(usage.bytes);
        self.ms_total = self.ms_total.saturating_add(usage.ms.round() as u64);
        self.kinds[usage.kind] = self.kinds[usage.kind].saturating_add(1);
        self.formats[usage.format] = self.formats[usage.format].saturating_add(1);
        let minute = now / 60;
        let bucket = &mut self.minutes[(minute % MINUTES as u64) as usize];
        if bucket.minute != minute {
            *bucket = Bucket {
                minute,
                ..Bucket::default()
            };
        }
        bucket.count = bucket.count.saturating_add(1);
        bucket.bytes = bucket.bytes.saturating_add(usage.bytes);
        if usage.protocol {
            bucket.protocol = bucket.protocol.saturating_add(1);
        }
    }

    /// Cases des 60 dernières minutes (minute en cours comprise) / buckets of the last 60 minutes.
    fn hour_buckets(&self, now: u64) -> impl Iterator<Item = &Bucket> {
        let current = now / 60;
        self.minutes.iter().filter(move |bucket| {
            bucket.minute <= current && bucket.minute.saturating_add(MINUTES as u64) > current
        })
    }

    /// Opérations et octets des 60 dernières minutes (minute en cours comprise) / last 60 minutes.
    pub fn last_hour(&self, now: u64) -> (u64, u64) {
        self.hour_buckets(now)
            .fold((0, 0), |(count, bytes), bucket| {
                (
                    count.saturating_add(bucket.count),
                    bytes.saturating_add(bucket.bytes),
                )
            })
    }

    /// Dont essais du protocole public, sur la même fenêtre / of which public protocol runs, same window.
    pub fn last_hour_protocol(&self, now: u64) -> u64 {
        self.hour_buckets(now)
            .fold(0, |count, bucket| count.saturating_add(bucket.protocol))
    }

    /// Dernière mesure du processeur et de la mémoire / latest processor and memory reading.
    pub fn set_system(&mut self, cpu_percent: f64, ram_used: u64, ram_total: u64) {
        self.cpu_percent = cpu_percent;
        self.ram_used = ram_used;
        self.ram_total = ram_total;
    }

    pub fn snapshot(&self, now: u64) -> Snapshot {
        let (uses_hour, bytes_hour) = self.last_hour(now);
        // Le jour a pu changer sans visite ni tic : il n'est plus « aujourd'hui » / the day may have changed.
        let today = if day_of(now) > self.today {
            0
        } else {
            self.visitors_today
        };
        Snapshot {
            uses_hour,
            uses_hour_protocol: self.last_hour_protocol(now).min(uses_hour),
            bytes_hour: format::rounded_bytes(bytes_hour),
            docs_total: self.docs_total,
            docs_protocol: self.docs_protocol,
            bytes_total: format::rounded_bytes(self.bytes_total),
            visitors_total: self.visitors_closed.saturating_add(self.visitors_today),
            visitors_today: today,
            cpu_percent: self.cpu_percent,
            ram_used: self.ram_used,
            ram_total: self.ram_total,
            since: self.launch,
            updated: now,
        }
    }

    pub fn launch_day(&self) -> i64 {
        self.launch
    }

    pub fn failed_total(&self) -> u64 {
        self.failed_total
    }

    /// Opérations réussies par sorte / successful operations per kind.
    pub fn kind_count(&self, kind: &str) -> u64 {
        KINDS
            .iter()
            .position(|known| *known == kind)
            .map_or(0, |index| self.kinds[index])
    }

    /// Opérations réussies par format / successful operations per format.
    pub fn format_count(&self, format: &str) -> u64 {
        FORMATS
            .iter()
            .position(|known| *known == format)
            .map_or(0, |index| self.formats[index])
    }

    /// État enregistré : des compteurs seulement / saved state: counters only.
    pub fn to_json(&self, now: u64) -> String {
        let current = now / 60;
        let minutes: Vec<Value> = self
            .minutes
            .iter()
            .filter(|bucket| {
                bucket.count > 0
                    && bucket.minute <= current
                    && bucket.minute + (MINUTES as u64) > current
            })
            .map(|bucket| json!([bucket.minute, bucket.count, bucket.bytes, bucket.protocol]))
            .collect();
        let named = |names: &[&str], counts: &[u64]| -> Map<String, Value> {
            names
                .iter()
                .zip(counts)
                .map(|(name, count)| (name.to_string(), json!(count)))
                .collect()
        };
        let state = json!({
            "version": 1,
            "saved": now,
            "launch": format::iso_date(self.launch),
            "visitors_closed": self.visitors_closed,
            "today": format::iso_date(self.today),
            "visitors_today": self.visitors_today,
            "docs_total": self.docs_total,
            "docs_protocol": self.docs_protocol,
            "bytes_total": self.bytes_total,
            "failed_total": self.failed_total,
            "ms_total": self.ms_total,
            "kinds": named(&KINDS, &self.kinds),
            "formats": named(&FORMATS, &self.formats),
            "minutes": minutes,
        });
        let mut text = serde_json::to_string_pretty(&state).unwrap_or_default();
        text.push('\n');
        text
    }

    /// Relit un état enregistré ; une nouvelle clé est tirée, aucune empreinte n'est reprise / reads a saved state;
    /// a new key is drawn, no digest is restored.
    pub fn from_json(text: &str, now: u64) -> Result<Stats, String> {
        let value: Value = serde_json::from_str(text).map_err(|error| format!("JSON: {error}"))?;
        let fields = value
            .as_object()
            .ok_or("objet JSON attendu / JSON object expected")?;
        if fields.get("version").and_then(Value::as_u64) != Some(1) {
            return Err("version d'état inconnue / unknown state version".into());
        }
        let count = |name: &str| fields.get(name).and_then(Value::as_u64).unwrap_or(0);
        let date = |name: &str| -> Result<i64, String> {
            fields
                .get(name)
                .and_then(Value::as_str)
                .and_then(format::parse_iso_date)
                .ok_or_else(|| format!("date « {name} » illisible / unreadable date"))
        };
        let mut stats = Stats::new(now);
        stats.launch = date("launch")?;
        stats.today = date("today")?;
        stats.visitors_closed = count("visitors_closed");
        stats.visitors_today = count("visitors_today");
        stats.docs_total = count("docs_total");
        // Absent d'un état d'avant le protocole : zéro ; jamais plus que le total / missing before: zero; capped.
        stats.docs_protocol = count("docs_protocol").min(stats.docs_total);
        stats.bytes_total = count("bytes_total");
        stats.failed_total = count("failed_total");
        stats.ms_total = count("ms_total");
        let fill = |name: &str, names: &[&str], counts: &mut [u64]| {
            if let Some(map) = fields.get(name).and_then(Value::as_object) {
                for (index, known) in names.iter().enumerate() {
                    counts[index] = map.get(*known).and_then(Value::as_u64).unwrap_or(0);
                }
            }
        };
        fill("kinds", &KINDS, &mut stats.kinds);
        fill("formats", &FORMATS, &mut stats.formats);
        let current = now / 60;
        for row in fields
            .get("minutes")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
        {
            let cells: Vec<u64> = row
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(Value::as_u64)
                .collect();
            // Trois nombres (état d'avant le protocole) ou quatre / three numbers (older state) or four.
            let (minute, count, bytes, protocol) = match cells[..] {
                [minute, count, bytes] => (minute, count, bytes, 0),
                [minute, count, bytes, protocol] => (minute, count, bytes, protocol.min(count)),
                _ => continue,
            };
            if minute <= current && minute.saturating_add(MINUTES as u64) > current {
                stats.minutes[(minute % MINUTES as u64) as usize] = Bucket {
                    minute,
                    count,
                    bytes,
                    protocol,
                };
            }
        }
        // Arrêté un autre jour : ce jour-là est clos / stopped on another day: that day is closed.
        stats.roll_day(now);
        Ok(stats)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOON: u64 = 1_793_016_000; // 2026-10-26 12:00:00 UTC
    const FIREFOX: &[u8] =
        b"Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0";

    fn datagram(kind: &str, fmt: &str, bytes: u64, ok: bool) -> Vec<u8> {
        format!("{{\"v\":1,\"kind\":\"{kind}\",\"fmt\":\"{fmt}\",\"bytes\":{bytes},\"ms\":4,\"ok\":{ok}}}").into_bytes()
    }

    #[test]
    fn datagrams_follow_the_contract_exactly() {
        let usage = parse_datagram(&datagram("mcp_file", "pdf", 2048, true)).unwrap();
        assert_eq!(
            (
                KINDS[usage.kind],
                FORMATS[usage.format],
                usage.bytes,
                usage.ok
            ),
            ("mcp_file", "pdf", 2048, true)
        );
        let float_ms = br#"{"v":1,"kind":"text","fmt":"text","bytes":10,"ms":5.25,"ok":false}"#;
        assert_eq!(parse_datagram(float_ms).unwrap().ms, 5.25);
        assert!(!parse_datagram(float_ms).unwrap().protocol);
        for kind in KINDS {
            for fmt in FORMATS {
                assert!(
                    parse_datagram(&datagram(kind, fmt, 1, true)).is_some(),
                    "{kind} {fmt}"
                );
            }
        }
        // Bornes : 256 Mio et une heure passent, un de plus non / bounds: 256 MiB and one hour pass, one more does not.
        let largest =
            br#"{"v":1,"kind":"file","fmt":"pdf","bytes":268435456,"ms":3600000,"ok":true}"#;
        assert_eq!(parse_datagram(largest).unwrap().bytes, MAX_INPUT_BYTES);
        let refused: [&[u8]; 19] = [
            b"",
            b"not json",
            b"[1,2,3]",
            br#"{"v":2,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":true}"#,
            br#"{"v":1,"kind":"chat","fmt":"text","bytes":1,"ms":1,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"exe","bytes":1,"ms":1,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"PDF","bytes":1,"ms":1,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":-1,"ms":1,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1.5,"ms":1,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":268435457,"ms":1,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":18446744073709551615,"ms":1,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":-1,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":3600000.5,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1e308,"ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":"yes"}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":"1","ok":true}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":true,"ip":"1.2.3.4"}"#,
            br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":true"#,
        ];
        for data in refused {
            assert_eq!(
                parse_datagram(data),
                None,
                "{}",
                String::from_utf8_lossy(data)
            );
        }
        // 512 octets passent, 513 non / 512 bytes pass, 513 do not.
        let base = datagram("text", "text", 1, true);
        let mut padded = base[..base.len() - 1].to_vec();
        padded.extend(std::iter::repeat_n(b' ', MAX_DATAGRAM - base.len()));
        padded.push(b'}');
        assert_eq!(padded.len(), MAX_DATAGRAM);
        assert!(parse_datagram(&padded).is_some());
        padded.insert(padded.len() - 1, b' ');
        assert_eq!(parse_datagram(&padded), None);
    }

    #[test]
    fn the_optional_source_marks_protocol_runs() {
        let with = |src: &str| {
            format!(
                "{{\"v\":1,\"kind\":\"text\",\"fmt\":\"text\",\"bytes\":10,\"ms\":2,\"ok\":true,\"src\":{src}}}"
            )
        };
        // Absent : public ; « public » ou « protocol » acceptés, n'importe où dans l'objet / anywhere in the object.
        assert!(
            !parse_datagram(&datagram("text", "text", 10, true))
                .unwrap()
                .protocol
        );
        assert!(
            !parse_datagram(with("\"public\"").as_bytes())
                .unwrap()
                .protocol
        );
        assert!(
            parse_datagram(with("\"protocol\"").as_bytes())
                .unwrap()
                .protocol
        );
        let first =
            br#"{"src":"protocol","v":1,"kind":"file","fmt":"pdf","bytes":1,"ms":1,"ok":false}"#;
        let usage = parse_datagram(first).unwrap();
        assert!(usage.protocol && !usage.ok);
        assert_eq!(SOURCES, ["public", "protocol"]);
        // Origine inconnue, mal typée, ou septième champ qui n'est pas `src` : refusé / unknown, mistyped, other.
        for refused in [
            with("\"Protocol\""),
            with("\"local\""),
            with("\"\""),
            with("true"),
            with("1"),
            with("null"),
            with("[\"protocol\"]"),
            r#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":true,"source":"protocol"}"#.into(),
            r#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":true,"src":"protocol","ip":"x"}"#.into(),
            r#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"src":"protocol"}"#.into(),
        ] {
            assert_eq!(parse_datagram(refused.as_bytes()), None, "{refused}");
        }
    }

    #[test]
    fn protocol_documents_are_counted_apart_and_in_the_total() {
        let mut stats = Stats::new(NOON);
        let usage = |ok, protocol| Usage {
            kind: 0,
            format: 0,
            bytes: 100,
            ms: 1.0,
            ok,
            protocol,
        };
        stats.record(usage(true, false), NOON);
        stats.record(usage(true, true), NOON);
        stats.record(usage(true, true), NOON);
        // Un échec du protocole n'est ni un document ni un essai compté / a failed run counts as neither.
        stats.record(usage(false, true), NOON);
        let snapshot = stats.snapshot(NOON);
        assert_eq!(
            (
                snapshot.docs_total,
                snapshot.docs_protocol,
                snapshot.uses_hour,
                snapshot.uses_hour_protocol
            ),
            (3, 2, 3, 2)
        );
        assert_eq!(stats.failed_total(), 1);
        assert_eq!(snapshot.text(Live::DocsProtocol, Lang::Fr), "2");
        assert_eq!(snapshot.text(Live::UsesHourProtocol, Lang::En), "2");
        // L'heure glisse aussi pour la part du protocole / the protocol share slides with the hour.
        assert_eq!(stats.snapshot(NOON + 3600).uses_hour_protocol, 0);
        stats.record(usage(true, false), NOON + 3600);
        assert_eq!(
            (
                stats.snapshot(NOON + 3600).uses_hour,
                stats.snapshot(NOON + 3600).uses_hour_protocol
            ),
            (1, 0)
        );
        stats.docs_protocol = 12_345;
        assert_eq!(
            stats.snapshot(NOON).text(Live::DocsProtocol, Lang::Fr),
            "12\u{202F}345"
        );
        stats.docs_protocol = u64::MAX;
        stats.record(usage(true, true), NOON);
        assert_eq!(stats.docs_protocol, u64::MAX);
    }

    #[test]
    fn datagram_rate_is_capped_per_second() {
        let mut stats = Stats::new(NOON);
        let admitted = (0..2500).filter(|_| stats.admit_datagram(NOON)).count();
        assert_eq!(admitted, 2000);
        assert!(stats.admit_datagram(NOON + 1));
    }

    #[test]
    fn the_hour_window_slides_by_minute() {
        let mut stats = Stats::new(NOON);
        let usage = |bytes| Usage {
            kind: 0,
            format: 1,
            bytes,
            ms: 3.0,
            ok: true,
            protocol: false,
        };
        stats.record(usage(100), NOON);
        stats.record(usage(50), NOON + 30);
        stats.record(usage(7), NOON + 60);
        assert_eq!(stats.last_hour(NOON + 60), (3, 157));
        // 59 minutes plus tard la première minute compte encore, à 60 elle sort / still in at 59, out at 60.
        assert_eq!(stats.last_hour(NOON + 59 * 60), (3, 157));
        assert_eq!(stats.last_hour(NOON + 60 * 60), (1, 7));
        assert_eq!(stats.last_hour(NOON + 61 * 60), (0, 0));
        // Une case réutilisée une heure plus tard repart de zéro / a bucket reused an hour later starts over.
        stats.record(usage(1), NOON + 3600);
        assert_eq!(stats.last_hour(NOON + 3600), (2, 8));
        assert_eq!((stats.docs_total, stats.bytes_total), (4, 158));
        stats.record(
            Usage {
                ok: false,
                ..usage(1_000_000)
            },
            NOON + 3600,
        );
        assert_eq!((stats.docs_total, stats.failed_total()), (4, 1));
        assert_eq!(stats.kind_count("text"), 4);
        assert_eq!(stats.format_count("pdf"), 4);
        assert_eq!(stats.format_count("nope"), 0);
    }

    #[test]
    fn visitors_are_counted_once_per_day_and_robots_never() {
        let mut stats = Stats::new(NOON);
        assert!(stats.visit(b"192.0.2.0", FIREFOX, NOON));
        assert!(!stats.visit(b"192.0.2.0", FIREFOX, NOON + 10));
        assert!(stats.visit(b"198.51.100.0", FIREFOX, NOON + 20));
        assert!(stats.visit(b"192.0.2.0", b"Mozilla/5.0 Safari/605.1.15", NOON + 30));
        for robot in [
            &b"Googlebot/2.1 (+http://www.google.com/bot.html)"[..],
            b"curl/8.5.0",
            b"Wget/1.21",
            b"python-requests/2.32",
            b"Go-http-client/2.0",
            b"Java/21.0.1",
            b"Mozilla/5.0 HeadlessChrome/120.0",
            b"UptimeRobot/2.0",
            b"Site24x7 monitoring",
            b"Yahoo! Slurp",
            b"",
            b"   ",
        ] {
            assert!(
                !stats.visit(b"203.0.113.0", robot, NOON + 40),
                "{}",
                String::from_utf8_lossy(robot)
            );
        }
        let snapshot = stats.snapshot(NOON + 50);
        assert_eq!((snapshot.visitors_today, snapshot.visitors_total), (3, 3));
    }

    #[test]
    fn the_day_change_closes_the_count_and_draws_a_new_key() {
        let mut stats = Stats::new(NOON);
        let first_key = stats.key;
        assert!(stats.visit(b"192.0.2.0", FIREFOX, NOON));
        assert!(stats.visit(b"198.51.100.0", FIREFOX, NOON));
        // Minuit passé, sans visite : « aujourd'hui » revient à zéro / past midnight, no visit: today is zero.
        let tomorrow = NOON + 12 * 3600 + 1;
        assert_eq!(stats.snapshot(tomorrow).visitors_today, 0);
        assert_eq!(stats.snapshot(tomorrow).visitors_total, 2);
        stats.roll_day(tomorrow);
        assert_ne!(stats.key, first_key);
        assert!(stats.seen.is_empty());
        // Le même visiteur compte de nouveau le lendemain / the same visitor counts again the next day.
        assert!(stats.visit(b"192.0.2.0", FIREFOX, tomorrow));
        let snapshot = stats.snapshot(tomorrow);
        assert_eq!((snapshot.visitors_today, snapshot.visitors_total), (1, 3));
        // Une horloge qui recule ne rouvre pas le jour / a clock going back does not reopen the day.
        let key = stats.key;
        stats.roll_day(NOON);
        assert_eq!(stats.key, key);
    }

    #[test]
    fn the_digest_depends_on_the_key() {
        let mut one = Stats::new(NOON);
        let mut two = Stats::new(NOON);
        one.visit(b"192.0.2.0", FIREFOX, NOON);
        two.visit(b"192.0.2.0", FIREFOX, NOON);
        assert_ne!(one.key, two.key);
        assert_ne!(one.seen.iter().next(), two.seen.iter().next());
    }

    #[test]
    fn one_address_cannot_inflate_the_count_with_varied_agents() {
        let mut stats = Stats::new(NOON);
        let counted = (0..500)
            .filter(|index| {
                let agent = format!("Mozilla/5.0 (Windows NT 10.0) rv:{index}");
                stats.visit(b"203.0.113.0", agent.as_bytes(), NOON)
            })
            .count();
        assert_eq!(counted, usize::from(MAX_AGENTS_PER_ADDRESS));
        // Les autres adresses restent comptées, et la limite tombe avec le jour / other addresses still count.
        assert!(stats.visit(b"2001:db8:1::", FIREFOX, NOON));
        let tomorrow = NOON + DAY;
        assert!(stats.visit(
            b"203.0.113.0",
            b"Mozilla/5.0 (Windows NT 10.0) rv:499",
            tomorrow
        ));
        assert_eq!(stats.per_address.len(), 1);
    }

    #[test]
    fn counters_saturate_instead_of_wrapping() {
        let mut stats = Stats::new(NOON);
        stats.docs_total = u64::MAX;
        stats.failed_total = u64::MAX;
        stats.kinds[0] = u64::MAX;
        stats.formats[0] = u64::MAX;
        let previous = NOON / 60 - 1;
        stats.minutes[(previous % MINUTES as u64) as usize] = Bucket {
            minute: previous,
            count: u64::MAX,
            bytes: u64::MAX,
            protocol: u64::MAX,
        };
        let usage = Usage {
            kind: 0,
            format: 0,
            bytes: MAX_INPUT_BYTES,
            ms: MAX_OPERATION_MS,
            ok: true,
            protocol: false,
        };
        stats.record(usage, NOON);
        stats.record(
            Usage {
                protocol: true,
                ..usage
            },
            NOON,
        );
        stats.record(Usage { ok: false, ..usage }, NOON);
        assert_eq!(stats.last_hour_protocol(NOON), u64::MAX);
        assert_eq!((stats.docs_total, stats.failed_total), (u64::MAX, u64::MAX));
        assert_eq!((stats.kinds[0], stats.formats[0]), (u64::MAX, u64::MAX));
        assert_eq!(stats.last_hour(NOON), (u64::MAX, u64::MAX));
        stats.rate_count = u32::MAX;
        stats.rate_second = NOON;
        assert!(!stats.admit_datagram(NOON));
        let snapshot = stats.snapshot(NOON);
        assert_eq!(
            (snapshot.uses_hour, snapshot.bytes_hour),
            (u64::MAX, u64::MAX)
        );
    }

    #[test]
    fn the_daily_set_is_bounded() {
        let mut stats = Stats::new(NOON);
        for index in 0..MAX_VISITORS_PER_DAY + 10 {
            stats.visit(index.to_string().as_bytes(), FIREFOX, NOON);
        }
        assert_eq!(stats.seen.len(), MAX_VISITORS_PER_DAY);
        assert_eq!(stats.visitors_today, MAX_VISITORS_PER_DAY as u64);
    }

    #[test]
    fn snapshot_json_and_texts() {
        let mut stats = Stats::new(NOON);
        stats.launch = format::parse_iso_date("2026-10-25").unwrap();
        stats.record(
            Usage {
                kind: 1,
                format: 1,
                bytes: 13_002_342,
                ms: 10.0,
                ok: true,
                protocol: true,
            },
            NOON,
        );
        stats.set_system(12.345, 2 * 1024 * 1024 * 1024, 8 * 1024 * 1024 * 1024);
        stats.visit(b"192.0.2.0", FIREFOX, NOON);
        let snapshot = stats.snapshot(NOON);
        assert_eq!(
            snapshot.json(),
            concat!(
                r#"{"uses_hour":1,"uses_hour_protocol":1,"bytes_hour":13002342,"docs_total":1,"docs_protocol":1,"#,
                r#""bytes_total":13002342,"visitors_total":1,"visitors_today":1,"cpu_percent":12.3,"#,
                r#""ram_used_bytes":2147483648,"ram_total_bytes":8589934592,"since":"2026-10-25","updated":1793016000}"#
            )
        );
        let parsed: Value = serde_json::from_str(&snapshot.json()).unwrap();
        assert_eq!(parsed["cpu_percent"], json!(12.3));
        assert_eq!(snapshot.text(Live::BytesHour, Lang::Fr), "12,4\u{a0}Mo");
        assert_eq!(snapshot.text(Live::BytesHour, Lang::En), "12.4\u{a0}MB");
        assert_eq!(snapshot.text(Live::CpuPercent, Lang::Fr), "12,3");
        assert_eq!(snapshot.text(Live::RamPercent, Lang::En), "25.0");
        assert_eq!(snapshot.text(Live::RamTotal, Lang::Fr), "8,0\u{a0}Go");
        assert_eq!(snapshot.text(Live::Since, Lang::Fr), "25 octobre 2026");
        assert_eq!(snapshot.text(Live::Since, Lang::En), "25 October 2026");
        assert_eq!(snapshot.text(Live::UsesHour, Lang::En), "1");
        let empty = Snapshot {
            ram_total: 0,
            cpu_percent: f64::NAN,
            ..snapshot
        };
        assert_eq!(empty.ram_percent(), 0.0);
        assert!(empty.json().contains("\"cpu_percent\":0.0,"));
    }

    #[test]
    fn state_round_trips_without_any_digest() {
        let mut stats = Stats::new(NOON);
        stats.launch = format::parse_iso_date("2026-10-25").unwrap();
        stats.visitors_closed = 41;
        stats.visit(b"192.0.2.0", FIREFOX, NOON);
        stats.record(
            Usage {
                kind: 3,
                format: 2,
                bytes: 5000,
                ms: 2.4,
                ok: true,
                protocol: false,
            },
            NOON - 120,
        );
        stats.record(
            Usage {
                kind: 4,
                format: 1,
                bytes: 7000,
                ms: 8.6,
                ok: true,
                protocol: true,
            },
            NOON,
        );
        stats.record(
            Usage {
                kind: 0,
                format: 0,
                bytes: 1,
                ms: 1.0,
                ok: false,
                protocol: false,
            },
            NOON,
        );
        let text = stats.to_json(NOON);
        for absent in ["192.0.2", "Mozilla", "seen", "key"] {
            assert!(!text.contains(absent), "{absent}");
        }
        let back = Stats::from_json(&text, NOON + 5).unwrap();
        assert_eq!(
            back.snapshot(NOON + 5),
            Snapshot {
                updated: NOON + 5,
                ..stats.snapshot(NOON + 5)
            }
        );
        assert_eq!((back.failed_total, back.ms_total), (1, 11));
        assert_eq!((back.docs_total, back.docs_protocol), (2, 1));
        assert!(text.contains("\"docs_protocol\": 1"), "{text}");
        // Un état d'avant le protocole se relit à zéro ; un compte incohérent est borné par le total.
        // A state from before the protocol reads as zero; an inconsistent count is capped by the total.
        let old = text.replace("\"docs_protocol\": 1,", "");
        assert_eq!(Stats::from_json(&old, NOON + 5).unwrap().docs_protocol, 0);
        let inflated = text.replace("\"docs_protocol\": 1,", "\"docs_protocol\": 99,");
        assert_eq!(
            Stats::from_json(&inflated, NOON + 5).unwrap().docs_protocol,
            2
        );
        assert_eq!(
            (back.kind_count("mcp_text"), back.format_count("docx")),
            (1, 1)
        );
        assert_eq!(back.last_hour(NOON), (2, 12_000));
        assert_eq!(back.last_hour_protocol(NOON), 1);
        // Minutes d'un état d'avant le protocole : trois nombres, aucun essai / older minutes: three numbers.
        let minute = NOON / 60;
        let old_rows = text.replace(
            &format!("{minute},\n      1,\n      7000,\n      1\n"),
            &format!("{minute},\n      1,\n      7000\n"),
        );
        assert_ne!(old_rows, text, "{text}");
        let older = Stats::from_json(&old_rows, NOON + 5).unwrap();
        assert_eq!(
            (older.last_hour(NOON), older.last_hour_protocol(NOON)),
            ((2, 12_000), 0)
        );
        assert!(back.seen.is_empty());
        assert_ne!(back.key, stats.key);
        // Relu le lendemain : la veille est close / read the next day: the previous day is closed.
        let later = Stats::from_json(&text, NOON + DAY).unwrap();
        let snapshot = later.snapshot(NOON + DAY);
        assert_eq!(
            (
                snapshot.visitors_today,
                snapshot.visitors_total,
                snapshot.uses_hour
            ),
            (0, 42, 0)
        );
        for bad in [
            "",
            "[]",
            "{\"version\":2}",
            "{\"version\":1,\"launch\":\"x\",\"today\":\"2026-10-25\"}",
        ] {
            assert!(Stats::from_json(bad, NOON).is_err(), "{bad}");
        }
    }
}
