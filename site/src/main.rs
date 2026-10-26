//! gdprguardian-site : démon du site de Gardien RGPD / GDPR Guardian website daemon.

use std::process::ExitCode;

const USAGE: &str = "\
gdprguardian-site [--socket CHEMIN] [--stats-socket CHEMIN] [--state CHEMIN]

  --socket        socket HTTP pour Nginx / HTTP socket for Nginx
                  (GDPRGUARDIAN_SITE_SOCKET, défaut / default /run/gdprguardian-site/site.sock)
  --stats-socket  socket des datagrammes d'usage du service / service usage datagram socket
                  (GDPRGUARDIAN_STATS_SOCKET, défaut / default /run/gdprguardian-stats/usage.sock)
  --state         fichier d'état (compteurs seulement) / state file (counters only)
                  (GDPRGUARDIAN_SITE_STATE, défaut / default /var/lib/gdprguardian-site/state.json)
  GDPRGUARDIAN_STATS_GID  groupe du socket d'usage (défaut 10001, vide : inchangé) / usage socket group
  --version, --help
";

#[cfg(unix)]
fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("gdprguardian-site: {error}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(not(unix))]
fn main() -> ExitCode {
    eprintln!(
        "gdprguardian-site: Linux seulement (sockets Unix) / Linux only (Unix sockets)\n\n{USAGE}"
    );
    ExitCode::FAILURE
}

#[cfg(unix)]
fn run() -> Result<(), String> {
    use gdprguardian_site::server::{self, Config};
    use std::env;
    use std::path::PathBuf;

    let setting = |name: &str, default: &str| {
        PathBuf::from(env::var_os(name).unwrap_or_else(|| default.into()))
    };
    let mut socket = setting(
        "GDPRGUARDIAN_SITE_SOCKET",
        "/run/gdprguardian-site/site.sock",
    );
    let mut stats_socket = setting(
        "GDPRGUARDIAN_STATS_SOCKET",
        "/run/gdprguardian-stats/usage.sock",
    );
    let mut state = setting(
        "GDPRGUARDIAN_SITE_STATE",
        "/var/lib/gdprguardian-site/state.json",
    );
    let mut args = env::args_os().skip(1);
    while let Some(arg) = args.next() {
        let arg = arg
            .into_string()
            .map_err(|_| String::from("argument non UTF-8 / non UTF-8 argument"))?;
        let (name, inline) = match arg.split_once('=') {
            Some((name, value)) if name.starts_with("--") => {
                (name.to_string(), Some(value.to_string()))
            }
            _ => (arg, None),
        };
        let mut value = || -> Result<PathBuf, String> {
            inline
                .clone()
                .map(PathBuf::from)
                .or_else(|| args.next().map(PathBuf::from))
                .filter(|path| !path.as_os_str().is_empty())
                .ok_or_else(|| format!("{name} : chemin attendu / path expected"))
        };
        match name.as_str() {
            "--socket" => socket = value()?,
            "--stats-socket" => stats_socket = value()?,
            "--state" => state = value()?,
            "--version" | "-V" => {
                println!("gdprguardian-site {}", gdprguardian_site::VERSION);
                return Ok(());
            }
            "--help" | "-h" => {
                print!("{USAGE}");
                return Ok(());
            }
            other => {
                return Err(format!(
                    "argument inconnu / unknown argument: {other}\n\n{USAGE}"
                ));
            }
        }
    }
    let stats_gid = match env::var("GDPRGUARDIAN_STATS_GID") {
        Ok(value) if value.trim().is_empty() => None,
        Ok(value) => Some(
            value
                .trim()
                .parse::<u32>()
                .map_err(|_| format!("GDPRGUARDIAN_STATS_GID: {value}"))?,
        ),
        Err(_) => Some(10001),
    };
    let config = Config {
        socket,
        stats_socket,
        stats_gid,
        state,
    };
    // Un seul fil, un petit moteur ; un fil d'appoint au plus, pour écrire l'état / one thread, a small runtime; at
    // most one helper thread, to write the state.
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_io()
        .enable_time()
        .max_blocking_threads(1)
        .build()
        .map_err(|error| format!("tokio: {error}"))?;
    runtime.block_on(async move {
        let shutdown = server::signals()?;
        server::serve(config, shutdown).await
    })
}
