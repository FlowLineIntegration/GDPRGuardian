//! Démon : socket Unix HTTP (Nginx), socket Unix de datagrammes (le service), relevés, état enregistré.
//! Daemon: HTTP Unix socket (Nginx), datagram Unix socket (the service), readings, saved state.
//!
//! Aucune écoute TCP. Aucune requête journalisée : une ligne au démarrage, puis seulement des erreurs qui ne citent
//! aucune requête. No TCP listener. No request logged: one line at start, then only errors quoting no request.

use crate::http::{App, unix_now};
use crate::stats::{MAX_DATAGRAM, Stats};
use crate::sys::Sampler;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper_util::rt::{TokioIo, TokioTimer};
use std::convert::Infallible;
use std::fs;
use std::future::Future;
use std::io::{self, Write};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{FileTypeExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, PoisonError};
use std::time::Duration;
use tokio::net::{UnixDatagram, UnixListener};

/// Connexions HTTP simultanées au plus (flux /api/live compris) / simultaneous HTTP connections at most.
pub const MAX_CONNECTIONS: usize = 4096;
/// Relevé du système et rafraîchissement des compteurs / system reading period.
pub const SAMPLE_PERIOD: Duration = Duration::from_secs(2);
/// Enregistrement de l'état / state saving period.
pub const SAVE_PERIOD: Duration = Duration::from_secs(60);
/// Début du nom abstrait (Linux) que doit tenir l'expéditeur des datagrammes d'usage / start of the abstract name
/// (Linux) the usage datagram sender must hold.
pub const USAGE_SENDER_PREFIX: &[u8] = b"gdprguardian-usage:";
/// Nom abstrait le plus long : `sun_path` (108 octets) moins l'octet nul initial / longest abstract name.
const MAX_ABSTRACT_NAME: usize = 107;

/// Réglages du démon / daemon settings.
#[derive(Clone, Debug)]
pub struct Config {
    /// Socket HTTP (Nginx) / HTTP socket.
    pub socket: PathBuf,
    /// Socket de datagrammes d'usage (le service) / usage datagram socket.
    pub stats_socket: PathBuf,
    /// Groupe du socket de datagrammes (None : inchangé) / datagram socket group (None: unchanged).
    pub stats_gid: Option<u32>,
    /// Fichier d'état / state file.
    pub state: PathBuf,
}

/// Nom abstrait que doit tenir l'expéditeur des datagrammes : `gdprguardian-usage:` suivi du chemin du socket
/// d'usage, coupé à 107 octets (`gdprguardian.server.usage.sender_name`, côté service).
///
/// Le processus d'accueil du service le prend à son démarrage, avant tout travailleur, et le garde : le noyau
/// refuse un second détenteur, si bien qu'un travailleur, même compromis par un document piégé, ne peut ni compter
/// de faux documents ni faire passer quoi que ce soit par les chiffres publiés. Un datagramme venu d'ailleurs est
/// ignoré. Service et démon doivent voir le socket au même chemin (`compose.yaml`).
///
/// Abstract name the datagram sender must hold: `gdprguardian-usage:` then the usage socket path, cut to 107 bytes.
/// The service's front process takes it at start, before any worker, and keeps it: the kernel refuses a second
/// holder, so a worker, even one compromised by a booby-trapped document, can neither count fake documents nor pass
/// anything through the published figures. A datagram from anywhere else is ignored. Service and daemon must see
/// the socket at the same path.
pub fn usage_sender_name(socket: &Path) -> Vec<u8> {
    let mut name = USAGE_SENDER_PREFIX.to_vec();
    name.extend_from_slice(socket.as_os_str().as_bytes());
    name.truncate(MAX_ABSTRACT_NAME);
    name
}

/// Vrai si le datagramme vient du détenteur du nom attendu / true when the datagram comes from the expected name.
#[cfg(any(target_os = "linux", target_os = "android"))]
fn from_sender(from: &tokio::net::unix::SocketAddr, sender: &[u8]) -> bool {
    from.as_abstract_name() == Some(sender)
}

/// Sans espace de noms abstrait, aucun expéditeur ne peut prouver qui il est : tout est ignoré.
/// Without the abstract namespace, no sender can prove who it is: everything is ignored.
#[cfg(not(any(target_os = "linux", target_os = "android")))]
fn from_sender(_: &tokio::net::unix::SocketAddr, _: &[u8]) -> bool {
    false
}

/// Lit l'état enregistré ; absent : compteurs neufs ; illisible : mis de côté (`.corrupt`) puis compteurs neufs.
/// Reads the saved state; missing: fresh counters; unreadable: moved aside (`.corrupt`), then fresh counters.
pub fn load_state(path: &Path, now: u64) -> Result<Stats, String> {
    match fs::read_to_string(path) {
        Ok(text) => match Stats::from_json(&text, now) {
            Ok(stats) => Ok(stats),
            Err(error) => {
                let aside = path.with_extension("json.corrupt");
                fs::rename(path, &aside).map_err(|e| format!("{}: {e}", path.display()))?;
                eprintln!(
                    "gdprguardian-site: état illisible mis de côté / unreadable state moved aside ({error}): {}",
                    aside.display()
                );
                Ok(Stats::new(now))
            }
        },
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(Stats::new(now)),
        Err(error) => Err(format!("{}: {error}", path.display())),
    }
}

/// Fichier d'état : écritures atomiques, une seule à la fois (l'enregistrement périodique, hors du fil du moteur,
/// et celui de l'arrêt ne se croisent jamais). State file: atomic writes, one at a time (the periodic save, off the
/// runtime thread, and the one at stop never interleave).
pub struct StateFile {
    path: PathBuf,
    writing: Mutex<()>,
}

impl StateFile {
    pub fn new(path: PathBuf) -> StateFile {
        StateFile {
            path,
            writing: Mutex::new(()),
        }
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Fichier temporaire, synchronisation, renommage, synchronisation du dossier ; bloquant.
    /// Temp file, sync, rename, folder sync; blocking.
    pub fn write(&self, text: &str) -> io::Result<()> {
        let _turn = self.writing.lock().unwrap_or_else(PoisonError::into_inner);
        let temporary = self.path.with_extension("json.tmp");
        {
            let mut file = fs::File::create(&temporary)?;
            file.write_all(text.as_bytes())?;
            file.sync_all()?;
        }
        fs::rename(&temporary, &self.path)?;
        if let Some(parent) = self
            .path
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
        {
            fs::File::open(parent)?.sync_all()?;
        }
        Ok(())
    }

    /// Enregistre les compteurs (texte bâti sous le verrou, écrit ensuite) / saves the counters.
    pub fn save(&self, app: &App, now: u64) -> io::Result<()> {
        let text = app.stats().to_json(now);
        self.write(&text)
    }
}

/// Retire un socket resté d'un arrêt brutal ; refuse de remplacer autre chose qu'un socket.
/// Removes a socket left by a crash; refuses to replace anything but a socket.
fn remove_stale_socket(path: &Path) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Ok(meta) if meta.file_type().is_socket() => {
            fs::remove_file(path).map_err(|error| format!("{}: {error}", path.display()))
        }
        Ok(_) => Err(format!(
            "{}: existe et n'est pas un socket / exists and is not a socket",
            path.display()
        )),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(format!("{}: {error}", path.display())),
    }
}

fn set_mode(path: &Path, mode: u32) -> Result<(), String> {
    fs::set_permissions(path, fs::Permissions::from_mode(mode))
        .map_err(|error| format!("{}: {error}", path.display()))
}

/// Socket HTTP, mode 0660 (groupe www-data par l'unité systemd) / HTTP socket, mode 0660.
pub fn bind_http(path: &Path) -> Result<UnixListener, String> {
    remove_stale_socket(path)?;
    let listener =
        UnixListener::bind(path).map_err(|error| format!("{}: {error}", path.display()))?;
    set_mode(path, 0o660)?;
    Ok(listener)
}

/// Socket de datagrammes, mode 0660, groupe du service / datagram socket, mode 0660, the service's group.
pub fn bind_usage(path: &Path, gid: Option<u32>) -> Result<UnixDatagram, String> {
    remove_stale_socket(path)?;
    let socket =
        UnixDatagram::bind(path).map_err(|error| format!("{}: {error}", path.display()))?;
    if let Some(gid) = gid {
        std::os::unix::fs::chown(path, None, Some(gid))
            .map_err(|error| format!("{}: groupe / group {gid}: {error}", path.display()))?;
    }
    set_mode(path, 0o660)?;
    Ok(socket)
}

/// Sert jusqu'à `shutdown`, puis enregistre l'état et retire les sockets.
/// Serves until `shutdown`, then saves the state and removes the sockets.
pub async fn serve(config: Config, shutdown: impl Future<Output = ()>) -> Result<(), String> {
    let now = unix_now();
    let app = App::new(load_state(&config.state, now)?);
    let state = Arc::new(StateFile::new(config.state.clone()));
    // Premier enregistrement tout de suite : date de lancement gardée, dossier inscriptible vérifié.
    // First save at once: launch date kept, writable folder checked.
    state
        .save(&app, now)
        .map_err(|error| format!("{}: {error}", config.state.display()))?;
    let listener = bind_http(&config.socket)?;
    let usage = bind_usage(&config.stats_socket, config.stats_gid)?;
    eprintln!(
        "gdprguardian-site {}: http {} ; usage {} ; state {}",
        env!("CARGO_PKG_VERSION"),
        config.socket.display(),
        config.stats_socket.display(),
        config.state.display()
    );

    let sender = usage_sender_name(&config.stats_socket);
    let receiver = tokio::spawn(receive_usage(Arc::clone(&app), usage, sender));
    let ticker = tokio::spawn(tick(Arc::clone(&app), Arc::clone(&state)));
    let connections = Arc::new(AtomicUsize::new(0));
    tokio::pin!(shutdown);
    loop {
        tokio::select! {
            accepted = listener.accept() => match accepted {
                Ok((stream, _)) => {
                    if connections.fetch_add(1, Ordering::AcqRel) >= MAX_CONNECTIONS {
                        connections.fetch_sub(1, Ordering::AcqRel);
                        continue; // fermée aussitôt / closed at once
                    }
                    let app = Arc::clone(&app);
                    let connections = Arc::clone(&connections);
                    tokio::spawn(async move {
                        let service = service_fn(move |request| {
                            let response = app.handle(&request, unix_now());
                            async move { Ok::<_, Infallible>(response) }
                        });
                        let _ = http1::Builder::new()
                            .timer(TokioTimer::new())
                            .header_read_timeout(Duration::from_secs(10))
                            .max_buf_size(16 * 1024)
                            .serve_connection(TokioIo::new(stream), service)
                            .await;
                        connections.fetch_sub(1, Ordering::AcqRel);
                    });
                }
                // Trop de fichiers ouverts, par exemple : on attend un peu / e.g. too many open files: wait a bit.
                Err(_) => tokio::time::sleep(Duration::from_millis(50)).await,
            },
            () = &mut shutdown => break,
        }
    }
    receiver.abort();
    ticker.abort();
    // Attend, s'il y en a une, l'écriture périodique en cours (verrou du fichier) / waits for any periodic write.
    let saved = state.save(&app, unix_now());
    let _ = fs::remove_file(&config.socket);
    let _ = fs::remove_file(&config.stats_socket);
    saved.map_err(|error| format!("{}: {error}", config.state.display()))
}

/// Datagrammes du service : jamais bloquants pour lui ; ignorés s'ils ne viennent pas du nom attendu
/// ([`usage_sender_name`]) ou s'ils sont mal formés. Service datagrams: never blocking it; ignored unless they come
/// from the expected name, or when malformed.
async fn receive_usage(app: Arc<App>, socket: UnixDatagram, sender: Vec<u8>) {
    // Un octet de plus que la limite : un datagramme tronqué à 513 est trop grand / one byte more than the limit.
    let mut buffer = [0u8; MAX_DATAGRAM + 1];
    loop {
        match socket.recv_from(&mut buffer).await {
            Ok((length, from)) => {
                if from_sender(&from, &sender) {
                    app.usage_datagram(&buffer[..length], unix_now());
                }
            }
            Err(_) => tokio::time::sleep(Duration::from_millis(50)).await,
        }
    }
}

/// Toutes les 2 s : processeur, mémoire, jour ; toutes les 60 s : état enregistré, hors du fil du moteur (un disque
/// lent ne fige ni les pages ni les flux). Every 2 s: processor, memory, day; every 60 s: state saved off the runtime
/// thread (a slow disk freezes neither pages nor streams).
async fn tick(app: Arc<App>, state: Arc<StateFile>) {
    let mut sampler = Sampler::new();
    sampler.sample();
    let mut interval = tokio::time::interval(SAMPLE_PERIOD);
    interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);
    let saves_every = (SAVE_PERIOD.as_secs() / SAMPLE_PERIOD.as_secs()).max(1);
    let mut ticks: u64 = 0;
    let mut failing = false;
    loop {
        interval.tick().await;
        let (cpu, used, total) = sampler.sample();
        let now = unix_now();
        {
            let mut stats = app.stats();
            stats.set_system(cpu, used, total);
            stats.roll_day(now);
        }
        ticks += 1;
        if ticks % saves_every == 0 {
            let text = app.stats().to_json(now);
            let file = Arc::clone(&state);
            let written = tokio::task::spawn_blocking(move || file.write(&text))
                .await
                .unwrap_or_else(|_| Err(io::Error::other("écriture interrompue / write aborted")));
            match written {
                Ok(()) => failing = false,
                // Une ligne au premier échec, pas à chaque fois / one line on the first failure only.
                Err(error) if !failing => {
                    failing = true;
                    eprintln!("gdprguardian-site: {}: {error}", state.path().display());
                }
                Err(_) => {}
            }
        }
    }
}

/// Inscrit SIGTERM et SIGINT ; le futur rendu s'achève au premier reçu (à appeler dans le moteur tokio).
/// Registers SIGTERM and SIGINT; the returned future ends at the first one (call inside the tokio runtime).
pub fn signals() -> Result<impl Future<Output = ()>, String> {
    use tokio::signal::unix::{SignalKind, signal};
    let mut terminate =
        signal(SignalKind::terminate()).map_err(|error| format!("SIGTERM: {error}"))?;
    let mut interrupt =
        signal(SignalKind::interrupt()).map_err(|error| format!("SIGINT: {error}"))?;
    Ok(async move {
        tokio::select! {
            _ = terminate.recv() => {}
            _ = interrupt.recv() => {}
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_sender_name_follows_the_socket_path() {
        assert_eq!(
            usage_sender_name(Path::new("/run/gdprguardian-stats/usage.sock")),
            b"gdprguardian-usage:/run/gdprguardian-stats/usage.sock"
        );
        let long = format!("/{}", "x".repeat(106));
        let name = usage_sender_name(Path::new(&long));
        assert_eq!(name.len(), MAX_ABSTRACT_NAME);
        assert!(name.starts_with(USAGE_SENDER_PREFIX));
    }
}
