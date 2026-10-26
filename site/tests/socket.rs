//! Démon complet sur de vrais sockets Unix (Linux) / the whole daemon on real Unix sockets (Linux).
#![cfg(target_os = "linux")]

use gdprguardian_site::server::{self, Config};
use serde_json::Value;
use std::os::linux::net::SocketAddrExt;
use std::os::unix::fs::{FileTypeExt, PermissionsExt};
use std::os::unix::net::{SocketAddr, UnixDatagram as StdDatagram};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::UnixStream;
use tokio::sync::oneshot;
use tokio::task::JoinHandle;

static NEXT: AtomicUsize = AtomicUsize::new(0);

/// Dossier temporaire retiré à la fin de l'essai / temporary folder removed at the end of the test.
struct TempDir(PathBuf);

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

impl std::ops::Deref for TempDir {
    type Target = Path;

    fn deref(&self) -> &Path {
        &self.0
    }
}

fn fresh_dir(name: &str) -> TempDir {
    let dir = std::env::temp_dir().join(format!(
        "gg-site-{}-{}-{name}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed)
    ));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    TempDir(dir)
}

fn config(dir: &Path) -> Config {
    Config {
        socket: dir.join("site.sock"),
        stats_socket: dir.join("usage.sock"),
        stats_gid: None,
        state: dir.join("state.json"),
    }
}

struct Running {
    config: Config,
    stop: oneshot::Sender<()>,
    task: JoinHandle<Result<(), String>>,
}

async fn start(dir: &Path) -> Running {
    let config = config(dir);
    let (stop, stopped) = oneshot::channel::<()>();
    let task = tokio::spawn(server::serve(config.clone(), async move {
        let _ = stopped.await;
    }));
    // Prêt quand le socket HTTP accepte (un socket resté d'avant refuse) / ready when the HTTP socket accepts.
    for _ in 0..200 {
        if UnixStream::connect(&config.socket).await.is_ok() && config.stats_socket.exists() {
            return Running { config, stop, task };
        }
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
    panic!("sockets absents / missing: {:?}", task.await);
}

impl Running {
    async fn stop(self) -> Config {
        self.stop.send(()).unwrap();
        self.task.await.unwrap().unwrap();
        self.config
    }
}

/// Requête HTTP/1.1 brute, connexion fermée après la réponse / raw HTTP/1.1 request, closed after the answer.
async fn exchange(socket: &Path, method: &str, path: &str, headers: &[&str]) -> (String, Vec<u8>) {
    let mut stream = UnixStream::connect(socket).await.unwrap();
    let mut request =
        format!("{method} {path} HTTP/1.1\r\nHost: gardienrgpd.fr\r\nConnection: close\r\n");
    for header in headers {
        request.push_str(header);
        request.push_str("\r\n");
    }
    request.push_str("\r\n");
    stream.write_all(request.as_bytes()).await.unwrap();
    let mut raw = Vec::new();
    tokio::time::timeout(Duration::from_secs(5), stream.read_to_end(&mut raw))
        .await
        .unwrap()
        .unwrap();
    let split = raw
        .windows(4)
        .position(|window| window == b"\r\n\r\n")
        .expect("fin d'en-têtes / end of headers");
    (
        String::from_utf8(raw[..split].to_vec())
            .unwrap()
            .to_ascii_lowercase(),
        raw[split + 4..].to_vec(),
    )
}

/// Expéditeur légitime : tient le nom abstrait attendu, comme le processus d'accueil du service.
/// Legitimate sender: holds the expected abstract name, like the service's front process.
fn front_sender(config: &Config) -> StdDatagram {
    let name = server::usage_sender_name(&config.stats_socket);
    StdDatagram::bind_addr(&SocketAddr::from_abstract_name(name).unwrap()).unwrap()
}

/// Attend que `docs_total` vaille `expected` (2 s au plus) / waits until `docs_total` equals `expected`.
async fn docs_total_reaches(socket: &Path, expected: u64) -> Value {
    let mut value = Value::Null;
    for _ in 0..200 {
        value = stats(socket).await;
        if value["docs_total"] == expected {
            break;
        }
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
    value
}

fn header<'a>(head: &'a str, name: &str) -> Option<&'a str> {
    head.lines()
        .find_map(|line| line.strip_prefix(name)?.strip_prefix(':').map(str::trim))
}

async fn stats(socket: &Path) -> Value {
    let (head, body) = exchange(socket, "GET", "/api/stats", &[]).await;
    assert!(head.starts_with("http/1.1 200"), "{head}");
    serde_json::from_slice(&body).unwrap()
}

#[tokio::test]
async fn serves_pages_over_a_unix_socket_without_cookie() {
    let dir = fresh_dir("pages");
    let running = start(&dir).await;
    for path in [&running.config.socket, &running.config.stats_socket] {
        let meta = std::fs::symlink_metadata(path).unwrap();
        assert!(meta.file_type().is_socket());
        assert_eq!(
            meta.permissions().mode() & 0o777,
            0o660,
            "{}",
            path.display()
        );
    }
    let (head, body) = exchange(
        &running.config.socket,
        "GET",
        "/",
        &[
            "User-Agent: Mozilla/5.0 Firefox/140.0",
            "X-GG-IP: 192.0.2.0",
        ],
    )
    .await;
    assert!(head.starts_with("http/1.1 200"), "{head}");
    assert_eq!(header(&head, "content-language"), Some("fr"));
    assert_eq!(
        header(&head, "content-length"),
        Some(body.len().to_string().as_str())
    );
    assert!(header(&head, "set-cookie").is_none() && header(&head, "server").is_none());
    assert!(header(&head, "content-security-policy").is_some());
    assert!(String::from_utf8(body).unwrap().contains("lang=\"fr"));
    // HEAD : longueur annoncée, aucun corps / HEAD: announced length, no body.
    let (head, body) = exchange(&running.config.socket, "HEAD", "/", &[]).await;
    assert!(head.starts_with("http/1.1 200"), "{head}");
    assert!(
        header(&head, "content-length")
            .unwrap()
            .parse::<usize>()
            .unwrap()
            > 100
    );
    assert!(body.is_empty());
    let (head, _) = exchange(
        &running.config.socket,
        "GET",
        "/favicon.svg",
        &["Accept-Encoding: br"],
    )
    .await;
    assert!(
        head.starts_with("http/1.1 200") && header(&head, "etag").is_some(),
        "{head}"
    );
    let (head, _) = exchange(&running.config.socket, "POST", "/", &["Content-Length: 0"]).await;
    assert!(head.starts_with("http/1.1 405"), "{head}");
    let (head, _) = exchange(&running.config.socket, "GET", "/nope", &[]).await;
    assert!(head.starts_with("http/1.1 404"), "{head}");
    assert_eq!(stats(&running.config.socket).await["visitors_today"], 1);
    running.stop().await;
}

#[tokio::test]
async fn usage_datagrams_are_counted_and_bad_ones_ignored() {
    let dir = fresh_dir("usage");
    let running = start(&dir).await;
    let sender = front_sender(&running.config);
    let target = &running.config.stats_socket;
    let oversized = format!(
        r#"{{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":true,"pad":"{}"}}"#,
        "x".repeat(600)
    );
    for datagram in [
        r#"{"v":1,"kind":"file","fmt":"pdf","bytes":1048576,"ms":250,"ok":true}"#,
        r#"{"v":1,"kind":"mcp_text","fmt":"text","bytes":2048,"ms":1.5,"ok":true}"#,
        r#"{"v":1,"kind":"file","fmt":"pdf","bytes":999,"ms":3,"ok":false}"#,
        r#"{"v":1,"kind":"nope","fmt":"pdf","bytes":1,"ms":1,"ok":true}"#,
        "garbage",
        &oversized,
    ] {
        sender.send_to(datagram.as_bytes(), target).unwrap();
    }
    let value = docs_total_reaches(&running.config.socket, 2).await;
    assert_eq!(value["docs_total"], 2, "{value}");
    // 1 Mio + 2 Kio s'affichent « 1,0 Mo » : le JSON public n'en dit pas plus / shown as 1.0 MB, no more in JSON.
    assert_eq!(value["bytes_total"], 1_048_576);
    assert_eq!(value["uses_hour"], 2);
    assert_eq!(value["bytes_hour"], 1_048_576);
    // Le refus d'un datagramme ne coupe pas la réception / a refused datagram does not stop the receiver.
    sender
        .send_to(
            br#"{"v":1,"kind":"upload","fmt":"xlsx","bytes":10,"ms":1,"ok":true}"#,
            target,
        )
        .unwrap();
    let value = docs_total_reaches(&running.config.socket, 3).await;
    assert_eq!(value["docs_total"], 3);
    running.stop().await;
}

#[tokio::test]
async fn only_the_holder_of_the_sender_name_is_counted() {
    let dir = fresh_dir("sender");
    let running = start(&dir).await;
    let target = &running.config.stats_socket;
    let valid = br#"{"v":1,"kind":"text","fmt":"text","bytes":10,"ms":1,"ok":true}"#;
    // Un travailleur compromis : socket sans nom, autre nom abstrait, chemin de fichier ; jamais compté.
    // A compromised worker: unnamed socket, another abstract name, a file path; never counted.
    let unnamed = StdDatagram::unbound().unwrap();
    let other = StdDatagram::bind_addr(
        &SocketAddr::from_abstract_name(b"gdprguardian-usage:/elsewhere").unwrap(),
    )
    .unwrap();
    let pathname = StdDatagram::bind(dir.join("worker.sock")).unwrap();
    // Peu d'envois : un envoi bloquant sur une file pleine figerait ce fil, qui fait aussi tourner le démon.
    // Few sends: a blocking send on a full queue would freeze this thread, which also runs the daemon.
    for sender in [&unnamed, &other, &pathname] {
        for _ in 0..3 {
            sender.send_to(valid, target).unwrap();
        }
    }
    // Le nom est tenu : personne d'autre ne peut le prendre / the name is held: nobody else can take it.
    let front = front_sender(&running.config);
    let name = server::usage_sender_name(target);
    let taken = StdDatagram::bind_addr(&SocketAddr::from_abstract_name(&name).unwrap());
    assert_eq!(
        taken.unwrap_err().kind(),
        std::io::ErrorKind::AddrInUse,
        "second détenteur / second holder"
    );
    front.send_to(valid, target).unwrap();
    let value = docs_total_reaches(&running.config.socket, 1).await;
    assert_eq!(value["docs_total"], 1, "{value}");
    // Rien d'autre n'arrive ensuite / nothing else arrives afterwards.
    tokio::time::sleep(Duration::from_millis(100)).await;
    assert_eq!(stats(&running.config.socket).await["docs_total"], 1);
    running.stop().await;
}

#[tokio::test]
async fn the_live_stream_answers_at_once() {
    let dir = fresh_dir("live");
    let running = start(&dir).await;
    let mut stream = UnixStream::connect(&running.config.socket).await.unwrap();
    stream
        .write_all(b"GET /api/live HTTP/1.1\r\nHost: gdprguardian.com\r\n\r\n")
        .await
        .unwrap();
    let mut received = Vec::new();
    let mut chunk = [0u8; 4096];
    let first = tokio::time::timeout(Duration::from_secs(2), async {
        loop {
            let read = stream.read(&mut chunk).await.unwrap();
            assert!(read > 0, "fermé / closed");
            received.extend_from_slice(&chunk[..read]);
            if received
                .windows(13)
                .any(|window| window == b"event: stats\n")
            {
                break;
            }
        }
    })
    .await;
    assert!(
        first.is_ok(),
        "premier événement en moins de 2 s / first event within 2 s"
    );
    let text = String::from_utf8_lossy(&received).to_ascii_lowercase();
    assert!(text.starts_with("http/1.1 200"), "{text}");
    assert!(text.contains("content-type: text/event-stream"));
    assert!(text.contains("x-accel-buffering: no"));
    assert!(text.contains("transfer-encoding: chunked"));
    assert!(text.contains("content-security-policy: default-src 'none'"));
    assert!(!text.contains("set-cookie"));
    drop(stream);
    running.stop().await;
}

#[tokio::test]
async fn state_is_saved_at_shutdown_and_read_back() {
    let dir = fresh_dir("state");
    let running = start(&dir).await;
    let sender = front_sender(&running.config);
    for datagram in [
        &br#"{"v":1,"kind":"text","fmt":"text","bytes":4096,"ms":2,"ok":true,"src":"public"}"#[..],
        br#"{"v":1,"kind":"file","fmt":"pdf","bytes":1024,"ms":7,"ok":true,"src":"protocol"}"#,
    ] {
        sender
            .send_to(datagram, &running.config.stats_socket)
            .unwrap();
    }
    docs_total_reaches(&running.config.socket, 2).await;
    drop(sender);
    let since = stats(&running.config.socket).await["since"].clone();
    let config = running.stop().await;
    assert!(
        !config.socket.exists() && !config.stats_socket.exists(),
        "sockets retirés / sockets removed"
    );
    let saved: Value =
        serde_json::from_str(&std::fs::read_to_string(&config.state).unwrap()).unwrap();
    assert_eq!(saved["docs_total"], 2);
    assert_eq!(saved["docs_protocol"], 1);
    assert_eq!(saved["bytes_total"], 5120);
    assert_eq!(saved["kinds"]["text"], 1);
    assert!(!dir.join("state.json.tmp").exists());
    let again = start(&dir).await;
    let value = stats(&again.config.socket).await;
    assert_eq!(
        (value["docs_total"].clone(), value["since"].clone()),
        (Value::from(2), since)
    );
    assert_eq!(value["docs_protocol"], 1);
    assert_eq!(value["uses_hour"], 2);
    again.stop().await;
}

#[tokio::test]
async fn stale_sockets_are_replaced_and_other_files_refused() {
    let dir = fresh_dir("stale");
    let config = config(&dir);
    // Socket resté d'un arrêt brutal / socket left by a crash.
    drop(std::os::unix::net::UnixListener::bind(&config.socket).unwrap());
    drop(StdDatagram::bind(&config.stats_socket).unwrap());
    assert!(config.socket.exists() && config.stats_socket.exists());
    let running = start(&dir).await;
    assert_eq!(stats(&running.config.socket).await["docs_total"], 0);
    running.stop().await;
    // Un fichier ordinaire à la place du socket n'est jamais effacé / a regular file is never deleted.
    std::fs::write(&config.socket, b"keep me").unwrap();
    let error = server::serve(config.clone(), async {}).await.unwrap_err();
    assert!(error.contains("not a socket"), "{error}");
    assert_eq!(std::fs::read(&config.socket).unwrap(), b"keep me");
}

#[tokio::test]
async fn an_unreadable_state_is_moved_aside() {
    let dir = fresh_dir("corrupt");
    std::fs::write(dir.join("state.json"), b"{ not json").unwrap();
    let running = start(&dir).await;
    assert_eq!(stats(&running.config.socket).await["docs_total"], 0);
    running.stop().await;
    assert_eq!(
        std::fs::read(dir.join("state.json.corrupt")).unwrap(),
        b"{ not json"
    );
    let saved: Value =
        serde_json::from_str(&std::fs::read_to_string(dir.join("state.json")).unwrap()).unwrap();
    assert_eq!(saved["version"], 1);
}
