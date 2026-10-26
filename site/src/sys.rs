//! Charge du serveur : processeur (écarts de /proc/stat) et mémoire (/proc/meminfo) / server load.

/// Temps processeur cumulés (en tics) / cumulative processor times (ticks).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CpuTimes {
    pub total: u64,
    pub idle: u64,
}

/// Ligne « cpu » de /proc/stat : user nice system idle iowait irq softirq steal [guest guest_nice].
/// Total = les huit premiers champs (guest est déjà compté dans user) ; repos = idle + iowait.
/// Total = first eight fields (guest is already part of user); idle = idle + iowait.
pub fn parse_cpu(stat: &str) -> Option<CpuTimes> {
    let line = stat.lines().find(|line| line.starts_with("cpu "))?;
    let fields: Vec<u64> = line
        .split_whitespace()
        .skip(1)
        .map(str::parse)
        .collect::<Result<_, _>>()
        .ok()?;
    if fields.len() < 4 {
        return None;
    }
    let total = fields
        .iter()
        .take(8)
        .fold(0u64, |sum, value| sum.saturating_add(*value));
    let idle = fields[3].saturating_add(fields.get(4).copied().unwrap_or(0));
    Some(CpuTimes { total, idle })
}

/// Charge entre deux relevés, en pourcentage ; None sans écart / load between two readings; None without delta.
pub fn cpu_percent(before: CpuTimes, after: CpuTimes) -> Option<f64> {
    let total = after.total.checked_sub(before.total)?;
    let idle = after.idle.checked_sub(before.idle)?;
    if total == 0 {
        return None;
    }
    Some((total.saturating_sub(idle) as f64 * 100.0 / total as f64).clamp(0.0, 100.0))
}

/// (utilisée, totale) en octets : MemTotal - MemAvailable / (used, total) in bytes.
pub fn parse_meminfo(meminfo: &str) -> Option<(u64, u64)> {
    let field = |name: &str| -> Option<u64> {
        let line = meminfo
            .lines()
            .find(|line| line.split(':').next() == Some(name))?;
        let kib: u64 = line
            .split(':')
            .nth(1)?
            .split_whitespace()
            .next()?
            .parse()
            .ok()?;
        kib.checked_mul(1024)
    };
    let total = field("MemTotal")?;
    // Noyaux d'avant 3.14 : pas de MemAvailable / kernels before 3.14 have no MemAvailable.
    let available = field("MemAvailable").or_else(|| {
        Some(field("MemFree")? + field("Buffers").unwrap_or(0) + field("Cached").unwrap_or(0))
    })?;
    Some((total.saturating_sub(available), total))
}

/// Relevés successifs du système / successive system readings.
#[derive(Default)]
pub struct Sampler {
    previous: Option<CpuTimes>,
    last_percent: f64,
}

impl Sampler {
    pub fn new() -> Sampler {
        Sampler::default()
    }

    /// Ajoute un relevé de /proc/stat ; renvoie la charge depuis le précédent / adds a reading, returns the load.
    pub fn push_cpu(&mut self, stat: &str) -> f64 {
        if let Some(now) = parse_cpu(stat) {
            if let Some(percent) = self.previous.and_then(|before| cpu_percent(before, now)) {
                self.last_percent = percent;
            }
            self.previous = Some(now);
        }
        self.last_percent
    }

    /// (charge %, mémoire utilisée, mémoire totale) lus dans /proc ; zéros hors Linux / zeros outside Linux.
    pub fn sample(&mut self) -> (f64, u64, u64) {
        let cpu = std::fs::read_to_string("/proc/stat")
            .map(|stat| self.push_cpu(&stat))
            .unwrap_or(0.0);
        let (used, total) = std::fs::read_to_string("/proc/meminfo")
            .ok()
            .and_then(|meminfo| parse_meminfo(&meminfo))
            .unwrap_or((0, 0));
        (cpu, used, total)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const STAT_1: &str = include_str!("../tests/fixtures/proc/stat.1");
    const STAT_2: &str = include_str!("../tests/fixtures/proc/stat.2");
    const MEMINFO: &str = include_str!("../tests/fixtures/proc/meminfo");

    #[test]
    fn cpu_lines_are_read() {
        let first = parse_cpu(STAT_1).unwrap();
        assert_eq!(
            first,
            CpuTimes {
                total: 10_000 + 200 + 3_000 + 80_000 + 500 + 100 + 150 + 50,
                idle: 80_500
            }
        );
        assert_eq!(parse_cpu("cpu0 1 2 3 4\n"), None);
        assert_eq!(parse_cpu("cpu  1 2 x 4\n"), None);
        assert_eq!(parse_cpu("cpu  1 2 3\n"), None);
        assert_eq!(
            parse_cpu("cpu  1 2 3 4\n"),
            Some(CpuTimes { total: 10, idle: 4 })
        );
    }

    #[test]
    fn cpu_load_comes_from_deltas() {
        let (first, second) = (parse_cpu(STAT_1).unwrap(), parse_cpu(STAT_2).unwrap());
        // Écart : 2000 tics dont 1500 de repos -> 25 % / delta: 2000 ticks, 1500 idle -> 25 %.
        assert_eq!(cpu_percent(first, second), Some(25.0));
        assert_eq!(cpu_percent(first, first), None);
        assert_eq!(cpu_percent(second, first), None);
        let mut sampler = Sampler::new();
        assert_eq!(sampler.push_cpu(STAT_1), 0.0);
        assert_eq!(sampler.push_cpu(STAT_2), 25.0);
        // Relevé identique ou illisible : la dernière charge reste / same or unreadable reading: last load kept.
        assert_eq!(sampler.push_cpu(STAT_2), 25.0);
        assert_eq!(sampler.push_cpu("garbage"), 25.0);
    }

    #[test]
    fn memory_is_total_minus_available() {
        assert_eq!(
            parse_meminfo(MEMINFO),
            Some(((16_303_420 - 12_212_336) * 1024, 16_303_420 * 1024))
        );
        let old = "MemTotal: 1000 kB\nMemFree: 100 kB\nBuffers: 50 kB\nCached: 250 kB\n";
        assert_eq!(parse_meminfo(old), Some((600 * 1024, 1000 * 1024)));
        assert_eq!(parse_meminfo("MemFree: 1 kB\n"), None);
        assert_eq!(parse_meminfo(""), None);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn the_real_proc_files_are_readable() {
        let mut sampler = Sampler::new();
        let (_, used, total) = sampler.sample();
        assert!(total > 0 && used <= total);
    }
}
