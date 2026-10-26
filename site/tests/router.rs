//! Routes sans socket : en-têtes, pages, fichiers, visiteurs, API, flux / socket-free routes.

use gdprguardian_site::embedded::{self, ASSETS};
use gdprguardian_site::format::Lang;
use gdprguardian_site::http::{
    App, Body, CSP_API, CSP_SITE, Encoding, LiveLimits, MAX_LIVE_STREAMS, language, negotiate,
};
use gdprguardian_site::stats::Stats;
use gdprguardian_site::template::Live;
use hyper::body::{Body as _, Bytes};
use hyper::header::{HeaderMap, HeaderValue};
use hyper::{Method, Request, Response, StatusCode};
use serde_json::Value;
use std::collections::BTreeSet;
use std::io::Read;
use std::pin::Pin;
use std::sync::Arc;
use std::time::Duration;

const NOW: u64 = 1_793_016_000; // 2026-10-26 12:00:00 UTC
const FIREFOX: &str = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0";

fn app() -> Arc<App> {
    App::new(Stats::new(NOW))
}

fn request(method: Method, path: &str, headers: &[(&str, &str)]) -> Request<()> {
    let mut builder = Request::builder().method(method).uri(path);
    for (name, value) in headers {
        builder = builder.header(*name, *value);
    }
    builder.body(()).unwrap()
}

fn get(app: &Arc<App>, path: &str, headers: &[(&str, &str)]) -> Response<Body> {
    app.handle(&request(Method::GET, path, headers), NOW)
}

fn bytes_of(response: &Response<Body>) -> Bytes {
    response.body().whole().expect("corps entier / whole body")
}

fn text_of(response: &Response<Body>) -> String {
    String::from_utf8(bytes_of(response).to_vec()).unwrap()
}

fn assert_secure(response: &Response<Body>, api: bool, what: &str) {
    let headers = response.headers();
    let expect = |name: &str, value: &str| {
        assert_eq!(
            headers.get(name).map(|v| v.to_str().unwrap()),
            Some(value),
            "{what}: {name}"
        )
    };
    expect(
        "content-security-policy",
        if api { CSP_API } else { CSP_SITE },
    );
    expect("strict-transport-security", "max-age=63072000");
    expect("x-content-type-options", "nosniff");
    expect("referrer-policy", "no-referrer");
    expect(
        "permissions-policy",
        "camera=(), microphone=(), geolocation=()",
    );
    expect("cross-origin-opener-policy", "same-origin");
    expect("cross-origin-resource-policy", "same-origin");
    assert!(headers.get("set-cookie").is_none(), "{what}: set-cookie");
    assert!(headers.get("server").is_none(), "{what}: server");
    assert!(
        headers.get("x-powered-by").is_none(),
        "{what}: x-powered-by"
    );
}

fn first_asset() -> &'static embedded::Asset {
    ASSETS
        .first()
        .expect("au moins un fichier statique / at least one static file")
}

#[test]
fn every_route_carries_the_security_headers_and_no_cookie() {
    let app = app();
    let asset_path = format!("/assets/{}", first_asset().path);
    let asset = asset_path.as_str();
    // (méthode, chemin, en-têtes, statut attendu, route /api) / (method, path, headers, expected status, /api route)
    type Case<'a> = (Method, &'a str, Vec<(&'a str, &'a str)>, StatusCode, bool);
    let cases: Vec<Case> = vec![
        (
            Method::GET,
            "/",
            vec![("host", "gardienrgpd.fr"), ("user-agent", FIREFOX)],
            StatusCode::OK,
            false,
        ),
        (
            Method::GET,
            "/",
            vec![("host", "gdprguardian.com")],
            StatusCode::OK,
            false,
        ),
        (Method::HEAD, "/", vec![], StatusCode::OK, false),
        (Method::GET, "/?utm_source=x", vec![], StatusCode::OK, false),
        (Method::GET, "/favicon.svg", vec![], StatusCode::OK, false),
        (
            Method::GET,
            asset,
            vec![("accept-encoding", "br, gzip")],
            StatusCode::OK,
            false,
        ),
        (
            Method::GET,
            asset,
            vec![("if-none-match", first_asset().etag)],
            StatusCode::NOT_MODIFIED,
            false,
        ),
        (
            Method::GET,
            "/assets/nope.css",
            vec![],
            StatusCode::NOT_FOUND,
            false,
        ),
        (
            Method::GET,
            "/assets/../Cargo.toml",
            vec![],
            StatusCode::NOT_FOUND,
            false,
        ),
        (
            Method::GET,
            "/assets/",
            vec![],
            StatusCode::NOT_FOUND,
            false,
        ),
        (Method::GET, "/robots.txt", vec![], StatusCode::OK, false),
        (
            Method::GET,
            "/.well-known/security.txt",
            vec![],
            StatusCode::OK,
            false,
        ),
        (Method::GET, "/api/stats", vec![], StatusCode::OK, true),
        (Method::GET, "/api/live", vec![], StatusCode::OK, true),
        (Method::HEAD, "/api/live", vec![], StatusCode::OK, true),
        (
            Method::GET,
            "/api/nope",
            vec![],
            StatusCode::NOT_FOUND,
            true,
        ),
        (
            Method::GET,
            "/index.html",
            vec![],
            StatusCode::NOT_FOUND,
            false,
        ),
        (Method::GET, "//", vec![], StatusCode::NOT_FOUND, false),
        (
            Method::POST,
            "/",
            vec![],
            StatusCode::METHOD_NOT_ALLOWED,
            false,
        ),
        (
            Method::PUT,
            "/assets/x",
            vec![],
            StatusCode::METHOD_NOT_ALLOWED,
            false,
        ),
        (
            Method::DELETE,
            "/api/stats",
            vec![],
            StatusCode::METHOD_NOT_ALLOWED,
            true,
        ),
        (
            Method::OPTIONS,
            "/api/live",
            vec![],
            StatusCode::METHOD_NOT_ALLOWED,
            true,
        ),
    ];
    for (method, path, headers, status, api) in cases {
        let what = format!("{method} {path}");
        let response = app.handle(&request(method, path, &headers), NOW);
        assert_eq!(response.status(), status, "{what}");
        assert_secure(&response, api, &what);
        if status == StatusCode::METHOD_NOT_ALLOWED {
            assert_eq!(response.headers()["allow"], "GET, HEAD");
        }
        if status == StatusCode::NOT_FOUND {
            assert!(
                bytes_of(&response).len() < 16,
                "{what}: petit corps / tiny body"
            );
        }
    }
    assert_eq!(app.live_streams(), 0, "flux rendus / streams released");
}

#[test]
fn the_language_follows_the_host() {
    let lang = |host: Option<&str>| {
        let mut headers = HeaderMap::new();
        if let Some(host) = host {
            headers.insert("host", HeaderValue::from_str(host).unwrap());
        }
        language(&headers)
    };
    assert_eq!(lang(Some("gardienrgpd.fr")), Lang::Fr);
    assert_eq!(lang(Some("GardienRGPD.fr:443")), Lang::Fr);
    assert_eq!(lang(Some("gardienrgpd.fr.")), Lang::Fr);
    assert_eq!(lang(Some("gdprguardian.com")), Lang::En);
    assert_eq!(lang(Some("api.gardienrgpd.fr")), Lang::En);
    assert_eq!(lang(Some("gardienrgpd.fr.evil.example")), Lang::En);
    assert_eq!(lang(None), Lang::En);
    let app = app();
    let fr = get(&app, "/", &[("host", "gardienrgpd.fr")]);
    assert_eq!(fr.headers()["content-language"], "fr");
    assert!(text_of(&fr).contains("lang=\"fr"));
    assert!(
        text_of(&fr).contains("https://gdprguardian.com"),
        "lien vers l'autre domaine / link to the other domain"
    );
    let en = get(&app, "/", &[("host", "gdprguardian.com")]);
    assert_eq!(en.headers()["content-language"], "en");
    assert!(text_of(&en).contains("lang=\"en"));
    assert!(
        text_of(&en).contains("https://gardienrgpd.fr"),
        "link to the other domain"
    );
}

#[test]
fn pages_show_the_live_values_in_their_language() {
    let app = app();
    for datagram in [
        r#"{"v":1,"kind":"file","fmt":"pdf","bytes":13002342,"ms":120,"ok":true}"#,
        r#"{"v":1,"kind":"text","fmt":"text","bytes":2048,"ms":1,"ok":true}"#,
    ] {
        assert!(app.usage_datagram(datagram.as_bytes(), NOW));
    }
    app.stats()
        .set_system(37.25, 3 * 1024 * 1024 * 1024, 16 * 1024 * 1024 * 1024);
    for (host, lang) in [("gardienrgpd.fr", Lang::Fr), ("gdprguardian.com", Lang::En)] {
        let response = get(&app, "/", &[("host", host)]);
        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(
            response.headers()["content-type"],
            "text/html; charset=utf-8"
        );
        assert_eq!(response.headers()["cache-control"], "no-cache");
        assert!(response.headers().get("etag").is_none());
        let html = text_of(&response);
        assert!(
            !html.contains("{{"),
            "espace réservé restant / placeholder left"
        );
        let snapshot = app.snapshot(NOW);
        for live in embedded::live_values(lang) {
            let text = snapshot.text(live, lang);
            assert!(html.contains(&text), "{lang:?} {}: {text}", live.name());
        }
    }
    let snapshot = app.snapshot(NOW);
    assert_eq!(snapshot.text(Live::BytesTotal, Lang::Fr), "12,4\u{a0}Mo");
    assert_eq!(snapshot.text(Live::CpuPercent, Lang::En), "37.3");
    assert_eq!(snapshot.text(Live::RamPercent, Lang::Fr), "18,8");
}

#[test]
fn visitors_are_counted_on_the_home_page_only() {
    let app = app();
    let today = |app: &Arc<App>| app.snapshot(NOW).visitors_today;
    let visitor = |ip: &'static str| vec![("user-agent", FIREFOX), ("x-gg-ip", ip)];
    get(&app, "/", &visitor("192.0.2.0"));
    assert_eq!(today(&app), 1);
    get(&app, "/", &visitor("192.0.2.0"));
    assert_eq!(today(&app), 1, "même visiteur / same visitor");
    app.handle(&request(Method::HEAD, "/", &visitor("198.51.100.0")), NOW);
    get(
        &app,
        &format!("/assets/{}", first_asset().path),
        &visitor("198.51.100.0"),
    );
    get(&app, "/favicon.svg", &visitor("198.51.100.0"));
    get(&app, "/api/stats", &visitor("198.51.100.0"));
    get(&app, "/robots.txt", &visitor("198.51.100.0"));
    get(&app, "/nope", &visitor("198.51.100.0"));
    app.handle(&request(Method::POST, "/", &visitor("198.51.100.0")), NOW);
    assert_eq!(
        today(&app),
        1,
        "HEAD, fichiers, API, 404, POST : rien / nothing"
    );
    for robot in [
        "Googlebot/2.1",
        "curl/8.5.0",
        "Mozilla/5.0 (compatible; bingbot/2.0)",
        "python-httpx/0.28",
    ] {
        get(
            &app,
            "/",
            &[("user-agent", robot), ("x-gg-ip", "203.0.113.0")],
        );
    }
    get(&app, "/", &[("x-gg-ip", "203.0.113.0")]);
    assert_eq!(
        today(&app),
        1,
        "robots et agent absent / robots and missing agent"
    );
    get(&app, "/?ref=x", &visitor("198.51.100.0"));
    get(
        &app,
        "/",
        &[
            ("user-agent", "Mozilla/5.0 Safari/605.1.15"),
            ("x-gg-ip", "192.0.2.0"),
        ],
    );
    assert_eq!(today(&app), 3);
    // Le lendemain : compte du jour clos, même visiteur de nouveau compté / next day: closed, counted again.
    let tomorrow = NOW + 86_400;
    app.handle(&request(Method::GET, "/", &visitor("192.0.2.0")), tomorrow);
    let snapshot = app.snapshot(tomorrow);
    assert_eq!((snapshot.visitors_today, snapshot.visitors_total), (1, 4));
}

#[test]
fn invalid_datagrams_do_not_use_up_the_rate_budget() {
    let app = app();
    for _ in 0..5000 {
        assert!(!app.usage_datagram(b"garbage", NOW));
        assert!(!app.usage_datagram(
            br#"{"v":1,"kind":"text","fmt":"text","bytes":18446744073709551615,"ms":1,"ok":true}"#,
            NOW,
        ));
    }
    let valid = br#"{"v":1,"kind":"text","fmt":"text","bytes":10,"ms":1,"ok":true}"#;
    let counted = (0..2500).filter(|_| app.usage_datagram(valid, NOW)).count();
    assert_eq!(counted, 2000);
    assert_eq!(app.snapshot(NOW).docs_total, 2000);
    // 20 000 octets, affichés « 19,5 Ko » : 19,5 × 1024 = 19 968 / 20,000 bytes, shown as 19.5 KB.
    assert_eq!(app.snapshot(NOW).bytes_total, 19_968);
}

#[test]
fn api_stats_is_the_contract_json() {
    let app = app();
    app.usage_datagram(
        br#"{"v":1,"kind":"upload","fmt":"docx","bytes":5000,"ms":30,"ok":true}"#,
        NOW,
    );
    let response = get(&app, "/api/stats", &[]);
    assert_eq!(response.headers()["content-type"], "application/json");
    assert_eq!(response.headers()["cache-control"], "no-store");
    let value: Value = serde_json::from_slice(&bytes_of(&response)).unwrap();
    let keys: BTreeSet<&str> = value
        .as_object()
        .unwrap()
        .keys()
        .map(String::as_str)
        .collect();
    let expected: BTreeSet<&str> = [
        "uses_hour",
        "uses_hour_protocol",
        "bytes_hour",
        "docs_total",
        "docs_protocol",
        "bytes_total",
        "visitors_total",
        "visitors_today",
        "cpu_percent",
        "ram_used_bytes",
        "ram_total_bytes",
        "since",
        "updated",
    ]
    .into();
    assert_eq!(keys, expected);
    assert_eq!(value["uses_hour"], 1);
    assert_eq!(value["uses_hour_protocol"], 0);
    assert_eq!(value["docs_protocol"], 0);
    // 5000 octets s'affichent « 4,9 Ko » : le JSON dit 4,9 × 1024, pas la taille exacte / shown as 4.9 KB.
    assert_eq!(value["bytes_total"], 5018);
    assert_eq!(value["bytes_hour"], 5018);
    assert!(value["cpu_percent"].is_f64());
    assert_eq!(value["since"], "2026-10-26");
    assert_eq!(value["updated"], NOW);
}

#[test]
fn protocol_runs_are_shown_apart_and_inside_the_total() {
    let app = app();
    for datagram in [
        // Sans « src » (ancien service) : public / without "src" (older service): public.
        r#"{"v":1,"kind":"text","fmt":"text","bytes":100,"ms":1,"ok":true}"#,
        r#"{"v":1,"kind":"file","fmt":"pdf","bytes":100,"ms":9,"ok":true,"src":"public"}"#,
        r#"{"v":1,"kind":"text","fmt":"text","bytes":100,"ms":1,"ok":true,"src":"protocol"}"#,
        r#"{"v":1,"kind":"file","fmt":"docx","bytes":100,"ms":3,"ok":true,"src":"protocol"}"#,
    ] {
        assert!(app.usage_datagram(datagram.as_bytes(), NOW), "{datagram}");
    }
    for refused in [
        r#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":true,"src":"admin"}"#,
        r#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":true,"origin":"protocol"}"#,
    ] {
        assert!(!app.usage_datagram(refused.as_bytes(), NOW), "{refused}");
    }
    // Un essai échoué ne compte pas / a failed run does not count.
    app.usage_datagram(
        br#"{"v":1,"kind":"text","fmt":"text","bytes":1,"ms":1,"ok":false,"src":"protocol"}"#,
        NOW,
    );
    let value: Value = serde_json::from_slice(&bytes_of(&get(&app, "/api/stats", &[]))).unwrap();
    assert_eq!(
        (
            &value["docs_total"],
            &value["docs_protocol"],
            &value["uses_hour"],
            &value["uses_hour_protocol"]
        ),
        (
            &Value::from(4),
            &Value::from(2),
            &Value::from(4),
            &Value::from(2)
        )
    );
    assert_eq!(app.stats().failed_total(), 1);
    for (host, lang) in [("gardienrgpd.fr", Lang::Fr), ("gdprguardian.com", Lang::En)] {
        let html = text_of(&get(&app, "/", &[("host", host)]));
        for live in [Live::DocsProtocol, Live::UsesHourProtocol] {
            assert!(
                embedded::live_values(lang).contains(&live),
                "{lang:?}: {{{{live.{}}}}} absent de la page / missing from the page",
                live.name()
            );
            assert!(
                html.contains(&format!("data-live=\"{}\"", live.name())),
                "{lang:?} {}",
                live.name()
            );
        }
    }
}

#[test]
fn robots_and_security_txt() {
    let app = app();
    let robots = get(&app, "/robots.txt", &[]);
    assert_eq!(text_of(&robots), "User-agent: *\nAllow: /\n");
    let security = get(&app, "/.well-known/security.txt", &[]);
    assert_eq!(
        security.headers()["content-type"],
        "text/plain; charset=utf-8"
    );
    let text = text_of(&security);
    assert!(text.contains("Contact: mailto:contact@gardienrgpd.fr\n"));
    assert!(text.contains("Expires: 2027-10-26T00:00:00Z\n"), "{text}");
    assert!(text.contains("Preferred-Languages: fr, en\n"));
}

fn decompress(encoding: &str, data: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    match encoding {
        "br" => brotli::Decompressor::new(data, 4096)
            .read_to_end(&mut out)
            .unwrap(),
        "gzip" => flate2::read::GzDecoder::new(data)
            .read_to_end(&mut out)
            .unwrap(),
        other => panic!("{other}"),
    };
    out
}

#[test]
fn assets_are_negotiated_compressed_and_cached() {
    let app = app();
    assert!(
        embedded::asset("favicon.svg").is_some(),
        "site/static/favicon.svg"
    );
    for asset in ASSETS {
        let path = format!("/assets/{}", asset.path);
        let plain = get(&app, &path, &[]);
        assert_eq!(plain.status(), StatusCode::OK, "{path}");
        assert_eq!(bytes_of(&plain).as_ref(), asset.identity, "{path}");
        assert_eq!(plain.headers()["content-type"], asset.content_type);
        assert_eq!(plain.headers()["cache-control"], "public, max-age=3600");
        assert_eq!(plain.headers()["etag"], asset.etag);
        assert!(plain.headers().get("content-encoding").is_none());
        let compressed = asset.br.is_some() || asset.gzip.is_some();
        assert_eq!(
            plain.headers().get("vary").is_some(),
            compressed,
            "{path}: vary"
        );
        for (accept, expected) in [
            ("br", asset.br.map(|_| "br")),
            ("gzip, deflate", asset.gzip.map(|_| "gzip")),
            (
                "gzip, deflate, br, zstd",
                asset.br.map(|_| "br").or(asset.gzip.map(|_| "gzip")),
            ),
            ("br;q=0, gzip", asset.gzip.map(|_| "gzip")),
            ("identity", None),
        ] {
            let response = get(&app, &path, &[("accept-encoding", accept)]);
            let coding = response
                .headers()
                .get("content-encoding")
                .map(|value| value.to_str().unwrap().to_string());
            assert_eq!(coding.as_deref(), expected, "{path} {accept}");
            let body = bytes_of(&response);
            match expected {
                Some(coding) => {
                    assert_eq!(decompress(coding, &body), asset.identity, "{path} {coding}");
                    assert!(
                        body.len() < asset.identity.len(),
                        "{path}: {coding} plus petit / smaller"
                    );
                    let etag = if coding == "br" {
                        asset.etag_br
                    } else {
                        asset.etag_gzip
                    };
                    assert_eq!(response.headers()["etag"], etag);
                }
                None => assert_eq!(body.as_ref(), asset.identity),
            }
        }
        // Validation : 304 sans corps pour chaque ETag, forme faible comprise / 304 for each ETag, weak form too.
        for tag in [
            asset.etag.to_string(),
            format!("W/{}", asset.etag_br),
            format!("\"x\", {}", asset.etag_gzip),
            "*".into(),
        ] {
            let response = get(
                &app,
                &path,
                &[("if-none-match", &tag), ("accept-encoding", "br")],
            );
            assert_eq!(response.status(), StatusCode::NOT_MODIFIED, "{path} {tag}");
            assert!(bytes_of(&response).is_empty());
            assert!(response.headers().get("etag").is_some());
            assert_eq!(response.headers()["cache-control"], "public, max-age=3600");
        }
        let changed = get(&app, &path, &[("if-none-match", "\"0000000000000000\"")]);
        assert_eq!(changed.status(), StatusCode::OK);
    }
    let favicon = get(&app, "/favicon.svg", &[]);
    assert_eq!(favicon.headers()["content-type"], "image/svg+xml");
}

#[test]
fn negotiation_honours_q_values() {
    let accept = |value: &str| Some(HeaderValue::from_str(value).unwrap());
    assert_eq!(negotiate(None, true, true), Encoding::Identity);
    assert_eq!(
        negotiate(accept("gzip, br").as_ref(), true, true),
        Encoding::Brotli
    );
    assert_eq!(
        negotiate(accept("gzip, br").as_ref(), false, true),
        Encoding::Gzip
    );
    assert_eq!(
        negotiate(accept("gzip;q=1.0, br;q=0.5").as_ref(), true, true),
        Encoding::Gzip
    );
    assert_eq!(
        negotiate(accept("br;q=0").as_ref(), true, true),
        Encoding::Identity
    );
    assert_eq!(
        negotiate(accept("*").as_ref(), true, true),
        Encoding::Brotli
    );
    assert_eq!(
        negotiate(accept("*;q=0, gzip").as_ref(), true, true),
        Encoding::Gzip
    );
    assert_eq!(
        negotiate(accept("BR").as_ref(), true, false),
        Encoding::Brotli
    );
    assert_eq!(
        negotiate(accept("x-gzip").as_ref(), true, true),
        Encoding::Gzip
    );
    assert_eq!(
        negotiate(accept("deflate, zstd").as_ref(), true, true),
        Encoding::Identity
    );
    assert_eq!(
        negotiate(accept("br;q=abc").as_ref(), true, true),
        Encoding::Identity
    );
}

async fn next_frame(body: &mut Body) -> String {
    let frame = tokio::time::timeout(
        Duration::from_secs(3),
        std::future::poll_fn(|cx| Pin::new(&mut *body).poll_frame(cx)),
    )
    .await
    .expect("trame à temps / frame in time")
    .expect("flux ouvert / stream open")
    .unwrap();
    String::from_utf8(frame.into_data().unwrap().to_vec()).unwrap()
}

#[tokio::test]
async fn the_live_stream_sends_an_event_at_once_then_periodically() {
    let app = App::with_limits(
        Stats::new(NOW),
        LiveLimits {
            period: Duration::from_millis(40),
            keepalive: Duration::from_millis(150),
            ..LiveLimits::default()
        },
    );
    let response = get(&app, "/api/live", &[]);
    assert_eq!(response.headers()["content-type"], "text/event-stream");
    assert_eq!(response.headers()["cache-control"], "no-cache");
    assert_eq!(response.headers()["x-accel-buffering"], "no");
    assert_eq!(app.live_streams(), 1);
    let mut body = response.into_body();
    assert!(!body.is_end_stream());
    let first = next_frame(&mut body).await;
    let event = first
        .strip_prefix("retry: 5000\nevent: stats\ndata: ")
        .expect(&first);
    let json: Value = serde_json::from_str(event.strip_suffix("\n\n").unwrap()).unwrap();
    assert_eq!(json.as_object().unwrap().len(), 13);
    assert_eq!(json["docs_protocol"], 0);
    assert_eq!(json["uses_hour_protocol"], 0);
    app.usage_datagram(
        br#"{"v":1,"kind":"mcp_text","fmt":"md","bytes":10,"ms":1,"ok":true}"#,
        gdprguardian_site::http::unix_now(),
    );
    let second = next_frame(&mut body).await;
    assert!(
        second.starts_with("event: stats\ndata: {\"uses_hour\":1,"),
        "{second}"
    );
    let mut keepalive = false;
    for _ in 0..20 {
        if next_frame(&mut body).await == ": keep-alive\n\n" {
            keepalive = true;
            break;
        }
    }
    assert!(keepalive, "commentaire de maintien / keep-alive comment");
    drop(body);
    assert_eq!(app.live_streams(), 0);
}

#[tokio::test]
async fn a_live_stream_ends_after_its_lifetime() {
    let app = App::with_limits(
        Stats::new(NOW),
        LiveLimits {
            period: Duration::from_millis(20),
            keepalive: Duration::from_secs(60),
            max_age: Duration::from_millis(150),
            ..LiveLimits::default()
        },
    );
    let mut body = get(&app, "/api/live", &[]).into_body();
    let started = std::time::Instant::now();
    let mut events = 0;
    let ended = tokio::time::timeout(Duration::from_secs(3), async {
        while let Some(frame) = std::future::poll_fn(|cx| Pin::new(&mut body).poll_frame(cx)).await
        {
            let data = frame.unwrap().into_data().unwrap();
            assert!(String::from_utf8_lossy(&data).contains("event: stats"));
            events += 1;
        }
    })
    .await;
    assert!(ended.is_ok(), "fin du flux / end of stream");
    // Premier flux : durée pleine, à une période près / first stream: full lifetime, within one period.
    let lived = started.elapsed();
    assert!(
        lived >= Duration::from_millis(150) && lived < Duration::from_millis(1500),
        "{lived:?}"
    );
    assert!(events >= 3, "{events}");
    drop(body);
    assert_eq!(app.live_streams(), 0);
}

#[tokio::test]
async fn live_streams_are_capped() {
    let app = app();
    assert_eq!(MAX_LIVE_STREAMS, 2000);
    let held: Vec<Response<Body>> = (0..MAX_LIVE_STREAMS)
        .map(|_| get(&app, "/api/live", &[]))
        .collect();
    assert!(
        held.iter()
            .all(|response| response.status() == StatusCode::OK)
    );
    assert_eq!(app.live_streams(), MAX_LIVE_STREAMS);
    let refused = get(&app, "/api/live", &[]);
    assert_eq!(refused.status(), StatusCode::SERVICE_UNAVAILABLE);
    assert_eq!(refused.headers()["retry-after"], "30");
    assert_secure(&refused, true, "503");
    // HEAD n'ouvre pas de flux / HEAD opens no stream.
    assert_eq!(
        app.handle(&request(Method::HEAD, "/api/live", &[]), NOW)
            .status(),
        StatusCode::OK
    );
    assert_eq!(app.live_streams(), MAX_LIVE_STREAMS);
    drop(held);
    assert_eq!(app.live_streams(), 0);
    let mut again = get(&app, "/api/live", &[]).into_body();
    assert!(next_frame(&mut again).await.contains("event: stats"));
}

// --- les pages et fichiers embarqués / the embedded pages and files -----------------------------------------------

type Tag = (String, Vec<(String, String)>);

/// Balises d'un texte HTML (nom, attributs), commentaires ignorés / tags of an HTML text, comments skipped.
fn tags(html: &str) -> Vec<Tag> {
    let mut found = Vec::new();
    let mut rest = html;
    while let Some(start) = rest.find('<') {
        rest = &rest[start + 1..];
        if let Some(after) = rest.strip_prefix("!--") {
            rest = after.find("-->").map_or("", |end| &after[end + 3..]);
            continue;
        }
        if rest.starts_with('!') || rest.starts_with('/') || rest.starts_with('?') {
            rest = rest.find('>').map_or("", |end| &rest[end + 1..]);
            continue;
        }
        let name_end = rest
            .find(|c: char| !(c.is_ascii_alphanumeric() || c == '-' || c == ':'))
            .unwrap_or(rest.len());
        let name = rest[..name_end].to_ascii_lowercase();
        if name.is_empty() {
            continue;
        }
        rest = &rest[name_end..];
        let mut attributes = Vec::new();
        loop {
            rest = rest.trim_start_matches(|c: char| c.is_whitespace() || c == '/');
            if rest.is_empty() || rest.starts_with('>') {
                rest = rest.get(1..).unwrap_or("");
                break;
            }
            let end = rest
                .find(|c: char| c.is_whitespace() || c == '=' || c == '>' || c == '/')
                .unwrap_or(rest.len());
            let attribute = rest[..end].to_ascii_lowercase();
            rest = rest[end..].trim_start();
            let mut value = String::new();
            if let Some(after) = rest.strip_prefix('=') {
                let after = after.trim_start();
                let (text, remaining) = match after.chars().next() {
                    Some(quote @ ('"' | '\'')) => {
                        let close = after[1..]
                            .find(quote)
                            .map_or(after.len(), |index| index + 1);
                        (&after[1..close], after.get(close + 1..).unwrap_or(""))
                    }
                    _ => {
                        let close = after
                            .find(|c: char| c.is_whitespace() || c == '>')
                            .unwrap_or(after.len());
                        (&after[..close], &after[close..])
                    }
                };
                value = text.to_string();
                rest = remaining;
            }
            if attribute.is_empty() {
                rest = rest.get(1..).unwrap_or("");
                continue;
            }
            attributes.push((attribute, value));
        }
        found.push((name, attributes));
    }
    found
}

fn rendered_pages() -> Vec<(Lang, String)> {
    let app = app();
    [(Lang::Fr, "gardienrgpd.fr"), (Lang::En, "gdprguardian.com")]
        .into_iter()
        .map(|(lang, host)| (lang, text_of(&get(&app, "/", &[("host", host)]))))
        .collect()
}

fn same_origin(url: &str) -> bool {
    url.starts_with('/') && !url.starts_with("//")
}

#[test]
fn embedded_pages_respect_the_content_security_policy() {
    const FETCHING_RELS: [&str; 9] = [
        "stylesheet",
        "icon",
        "preload",
        "modulepreload",
        "manifest",
        "apple-touch-icon",
        "mask-icon",
        "prefetch",
        "shortcut",
    ];
    for (lang, html) in rendered_pages() {
        let mut problems = Vec::new();
        for (name, attributes) in tags(&html) {
            let attribute = |wanted: &str| {
                attributes
                    .iter()
                    .find(|(key, _)| key == wanted)
                    .map(|(_, value)| value.as_str())
            };
            if name == "style" {
                problems.push("élément <style> / <style> element".to_string());
            }
            for (key, value) in &attributes {
                if key == "style" {
                    problems.push(format!("<{name} style=…> (CSP style-src 'self')"));
                }
                if key.starts_with("on") {
                    problems.push(format!(
                        "<{name} {key}=…> (gestionnaire en ligne / inline handler)"
                    ));
                }
                if value
                    .trim_start()
                    .to_ascii_lowercase()
                    .starts_with("javascript:")
                {
                    problems.push(format!("<{name} {key}=\"javascript:…\">"));
                }
            }
            match name.as_str() {
                "script" => match attribute("src") {
                    Some(src) if same_origin(src) => {}
                    Some(src) => {
                        problems.push(format!("<script src=\"{src}\"> hors du site / third-party"))
                    }
                    None if attribute("type") == Some("application/ld+json") => {}
                    None => problems.push("<script> en ligne / inline script".to_string()),
                },
                "link" => {
                    let rel = attribute("rel").unwrap_or_default().to_ascii_lowercase();
                    let href = attribute("href").unwrap_or_default();
                    if rel
                        .split_whitespace()
                        .any(|rel| FETCHING_RELS.contains(&rel))
                        && !same_origin(href)
                    {
                        problems.push(format!(
                            "<link rel=\"{rel}\" href=\"{href}\"> hors du site / third-party"
                        ));
                    }
                }
                "img" | "source" | "video" | "audio" | "track" | "input" => {
                    for key in ["src", "srcset", "poster"] {
                        if let Some(url) = attribute(key) {
                            if !same_origin(url) && !url.starts_with("data:") {
                                problems.push(format!(
                                    "<{name} {key}=\"{url}\"> hors du site / third-party"
                                ));
                            }
                        }
                    }
                }
                "iframe" | "frame" | "object" | "embed" | "base" => {
                    problems.push(format!("<{name}> interdit / forbidden"))
                }
                _ => {}
            }
        }
        assert!(
            problems.is_empty(),
            "page {lang:?}:\n{}",
            problems.join("\n")
        );
    }
}

#[test]
fn every_file_a_page_refers_to_is_embedded() {
    for (lang, html) in rendered_pages() {
        for (name, attributes) in tags(&html) {
            for (key, value) in attributes {
                if !matches!(key.as_str(), "src" | "href") {
                    continue;
                }
                let path = value.split(['?', '#']).next().unwrap_or_default();
                if let Some(relative) = path.strip_prefix("/assets/") {
                    assert!(
                        embedded::asset(relative).is_some(),
                        "page {lang:?}: <{name} {key}=\"{value}\"> absent"
                    );
                } else if path == "/favicon.svg" {
                    assert!(embedded::asset("favicon.svg").is_some());
                }
            }
        }
    }
    // Feuilles de style : url(...) vers des fichiers embarqués, rien d'extérieur / stylesheets: embedded files only.
    for asset in ASSETS.iter().filter(|asset| asset.path.ends_with(".css")) {
        let css = String::from_utf8_lossy(asset.identity);
        let folder = asset.path.rsplit_once('/').map_or("", |(folder, _)| folder);
        for piece in css.split("url(").skip(1) {
            let url = piece
                .split(')')
                .next()
                .unwrap_or_default()
                .trim()
                .trim_matches(['"', '\'']);
            if url.starts_with("data:") || url.starts_with('#') {
                continue;
            }
            assert!(
                !url.contains("//"),
                "{}: url({url}) hors du site / third-party",
                asset.path
            );
            let target = match url.strip_prefix("/assets/") {
                Some(relative) => relative.to_string(),
                None => resolve(folder, url.split(['?', '#']).next().unwrap_or_default()),
            };
            assert!(
                embedded::asset(&target).is_some(),
                "{}: url({url}) -> {target} absent",
                asset.path
            );
        }
        assert!(
            !css.contains("@import url(http") && !css.contains("@import \"http"),
            "{}: @import",
            asset.path
        );
    }
}

/// Chemin relatif résolu depuis un dossier de /assets / relative path resolved from an /assets folder.
fn resolve(folder: &str, relative: &str) -> String {
    let mut parts: Vec<&str> = folder.split('/').filter(|part| !part.is_empty()).collect();
    for part in relative.split('/') {
        match part {
            "" | "." => {}
            ".." => {
                parts.pop();
            }
            other => parts.push(other),
        }
    }
    parts.join("/")
}

#[test]
fn data_live_names_are_those_of_the_contract() {
    let streamed: BTreeSet<&str> = Live::ALL
        .iter()
        .filter(|live| live.is_streamed())
        .map(|live| live.name())
        .collect();
    for (lang, html) in rendered_pages() {
        for (name, attributes) in tags(&html) {
            for (key, value) in attributes {
                if key == "data-live" {
                    assert!(
                        streamed.contains(value.as_str()),
                        "page {lang:?}: <{name} data-live=\"{value}\">"
                    );
                }
            }
        }
    }
}

#[test]
fn the_page_policy_takes_media_and_images_from_the_site_only() {
    // La vidéo de lancement et son affiche viennent de /media/ (Nginx) : 'self', rien d'autre.
    // The launch video and its poster come from /media/ (Nginx): 'self', nothing else.
    let sources = |name: &str| -> Option<Vec<&str>> {
        CSP_SITE.split(';').find_map(|directive| {
            let mut words = directive.split_whitespace();
            (words.next() == Some(name)).then(|| words.collect())
        })
    };
    assert_eq!(sources("default-src"), Some(vec!["'none'"]));
    assert_eq!(sources("media-src"), Some(vec!["'self'"]));
    assert_eq!(sources("img-src"), Some(vec!["'self'", "data:"]));
}

#[test]
fn media_files_are_cited_with_their_version() {
    // Nginx garde les fichiers de /media/ un an (immutable) : chaque lien porte l'empreinte du fichier (?v=, 8
    // chiffres hexadécimaux du SHA-256), comparée à video/out par tests/server/test_deploy_config.py et à
    // l'installation par install.sh site. Nginx caches /media/ files for a year (immutable): every link carries the
    // file's digest, checked against video/out by the deployment tests and at install time.
    for (lang, html) in rendered_pages() {
        let mut videos = 0;
        for (name, attributes) in tags(&html) {
            let has = |wanted: &str| attributes.iter().any(|(key, _)| key == wanted);
            if name == "video" {
                videos += 1;
                assert!(
                    has("controls") && has("playsinline") && has("poster"),
                    "page {lang:?}: <video> sans contrôles, playsinline ou affiche / without controls"
                );
                assert!(
                    attributes
                        .iter()
                        .any(|(key, value)| key == "preload" && value == "none"),
                    "page {lang:?}: <video preload=\"none\"> attendu / expected"
                );
            }
            for (key, value) in &attributes {
                let Some(rest) = value.strip_prefix("/media/") else {
                    continue;
                };
                let (file, version) = rest.split_once("?v=").unwrap_or((rest, ""));
                assert!(
                    !file.is_empty()
                        && file
                            .bytes()
                            .all(|byte| byte.is_ascii_alphanumeric() || b"._-".contains(&byte)),
                    "page {lang:?}: <{name} {key}=\"{value}\"> nom / name"
                );
                assert!(
                    version.len() == 8
                        && version
                            .bytes()
                            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte)),
                    "page {lang:?}: <{name} {key}=\"{value}\"> sans ?v=<empreinte> / without ?v=<digest>"
                );
            }
        }
        if !embedded::USING_FIXTURES {
            assert_eq!(videos, 1, "page {lang:?}: une vidéo / one video");
        }
    }
}

#[test]
fn the_fixture_flag_is_reported() {
    // Information seulement : vrai tant que le site réel manque / information only: true while the real site is missing.
    eprintln!("jeux d'essai / fixtures: {}", embedded::USING_FIXTURES);
    assert!(!embedded::page(Lang::Fr).is_empty() && !embedded::page(Lang::En).is_empty());
}
