//! Routes HTTP du site, sans socket : testables telles quelles / site HTTP routes, socket-free and testable.
//!
//! Aucune requête n'est journalisée ; seule la page d'accueil (GET « / ») compte les visiteurs. Chaque réponse porte
//! les en-têtes de sécurité, jamais de cookie. No request is logged; only GET "/" counts visitors. Every response
//! carries the security headers, never a cookie.

use crate::embedded::{self, Asset};
use crate::format::{self, Lang};
use crate::stats::{self, Snapshot, Stats};
use crate::template;
use hyper::body::{Body as HttpBody, Bytes, Frame, SizeHint};
use hyper::header::{self, HeaderMap, HeaderName, HeaderValue};
use hyper::{Method, Request, Response, StatusCode};
use std::convert::Infallible;
use std::pin::Pin;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, MutexGuard};
use std::task::{Context, Poll};
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::time::{Instant, Interval, MissedTickBehavior};

/// Politique de sécurité du contenu des pages (contrat, point 5) ; `media-src 'self'` pour la vidéo de lancement,
/// servie par Nginx sous /media/ avec cette même politique (deploy/server/nginx-site.conf). Page content security
/// policy; `media-src 'self'` for the launch video, served by Nginx under /media/ with this same policy.
pub const CSP_SITE: &str = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; \
                            media-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none'; \
                            form-action 'none'; frame-ancestors 'none'";
/// Politique des réponses /api/* / policy of /api/* responses.
pub const CSP_API: &str = "default-src 'none'";
/// Flux /api/live simultanés au plus (environ 17 Ko de mémoire chacun) / simultaneous /api/live streams at most
/// (about 17 KB of memory each). Nginx en accorde 10 par adresse IPv4 ou par /64 IPv6 / Nginx allows 10 per address.
pub const MAX_LIVE_STREAMS: usize = 2000;
/// Période des événements « stats » / "stats" event period.
pub const LIVE_PERIOD: Duration = Duration::from_secs(2);
/// Période des commentaires de maintien / keep-alive comment period.
pub const KEEPALIVE_PERIOD: Duration = Duration::from_secs(15);
/// Durée de vie d'un flux, moins un écart d'au plus un tiers ; le navigateur se reconnecte 5 s après la fin : un
/// onglet oublié ne garde pas sa place indéfiniment. A stream's lifetime, minus a spread of up to a third; the
/// browser reconnects 5 s after the end, so a forgotten tab does not hold its slot forever.
pub const LIVE_MAX_AGE: Duration = Duration::from_secs(30 * 60);
/// Nom servi en français ; tout autre nom reçoit l'anglais / name served in French; any other gets English.
pub const FR_HOST: &str = "gardienrgpd.fr";
/// En-tête posé par Nginx : adresse du client déjà tronquée (/24, /48) / set by Nginx: truncated client address.
pub const CLIENT_ADDRESS_HEADER: &str = "x-gg-ip";
const ROBOTS_TXT: &str = "User-agent: *\nAllow: /\n";
const KEEPALIVE: &[u8] = b": keep-alive\n\n";

/// Secondes Unix actuelles / current Unix seconds.
pub fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |elapsed| elapsed.as_secs())
}

/// Limites des flux /api/live, réglables pour les essais / /api/live stream limits, adjustable for tests.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LiveLimits {
    /// Flux simultanés au plus / simultaneous streams at most.
    pub streams: usize,
    /// Période des événements / event period.
    pub period: Duration,
    /// Période des commentaires de maintien / keep-alive period.
    pub keepalive: Duration,
    /// Durée de vie d'un flux (moins un écart d'au plus un tiers) / stream lifetime (minus up to a third).
    pub max_age: Duration,
}

impl Default for LiveLimits {
    fn default() -> LiveLimits {
        LiveLimits {
            streams: MAX_LIVE_STREAMS,
            period: LIVE_PERIOD,
            keepalive: KEEPALIVE_PERIOD,
            max_age: LIVE_MAX_AGE,
        }
    }
}

/// État partagé du site / shared site state.
pub struct App {
    stats: Mutex<Stats>,
    live_streams: AtomicUsize,
    live_opened: AtomicUsize,
    limits: LiveLimits,
}

impl App {
    pub fn new(stats: Stats) -> Arc<App> {
        App::with_limits(stats, LiveLimits::default())
    }

    /// Limites réglables pour les essais / limits adjustable for tests.
    pub fn with_limits(stats: Stats, limits: LiveLimits) -> Arc<App> {
        Arc::new(App {
            stats: Mutex::new(stats),
            live_streams: AtomicUsize::new(0),
            live_opened: AtomicUsize::new(0),
            limits,
        })
    }

    /// Compteurs, verrouillés / counters, locked.
    pub fn stats(&self) -> MutexGuard<'_, Stats> {
        self.stats
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
    }

    pub fn snapshot(&self, now: u64) -> Snapshot {
        self.stats().snapshot(now)
    }

    /// Flux /api/live ouverts / open /api/live streams.
    pub fn live_streams(&self) -> usize {
        self.live_streams.load(Ordering::Acquire)
    }

    /// Datagramme d'usage du service (expéditeur déjà vérifié) : lecture, plafond de débit, comptage ; vrai s'il est
    /// compté. Lu avant le plafond : un datagramme invalide n'use pas le débit des bons. Service usage datagram
    /// (sender already checked): parsing, rate cap, counting; true when counted. Parsed before the cap, so an invalid
    /// datagram does not use up the budget of valid ones.
    pub fn usage_datagram(&self, data: &[u8], now: u64) -> bool {
        let Some(usage) = stats::parse_datagram(data) else {
            return false;
        };
        let mut stats = self.stats();
        if !stats.admit_datagram(now) {
            return false;
        }
        stats.record(usage, now);
        true
    }

    /// Répond à une requête (le corps de la requête est ignoré) / answers a request (its body is ignored).
    pub fn handle<B>(self: &Arc<Self>, request: &Request<B>, now: u64) -> Response<Body> {
        let path = request.uri().path();
        let api = path.starts_with("/api/");
        let head = match *request.method() {
            Method::GET => false,
            Method::HEAD => true,
            _ => {
                let response = reply(
                    StatusCode::METHOD_NOT_ALLOWED,
                    Body::from_static(b"405\n"),
                    &[
                        (header::CONTENT_TYPE, "text/plain; charset=utf-8"),
                        (header::ALLOW, "GET, HEAD"),
                    ],
                );
                return secure(response, api);
            }
        };
        let headers = request.headers();
        let response = match path {
            "/" => self.page(headers, head, now),
            "/favicon.svg" => asset_response(embedded::asset("favicon.svg"), headers),
            "/robots.txt" => reply(
                StatusCode::OK,
                Body::from_static(ROBOTS_TXT.as_bytes()),
                &[
                    (header::CONTENT_TYPE, "text/plain; charset=utf-8"),
                    (header::CACHE_CONTROL, "public, max-age=3600"),
                ],
            ),
            "/.well-known/security.txt" => reply(
                StatusCode::OK,
                Body::full(security_txt(now)),
                &[
                    (header::CONTENT_TYPE, "text/plain; charset=utf-8"),
                    (header::CACHE_CONTROL, "public, max-age=3600"),
                ],
            ),
            "/api/stats" => reply(
                StatusCode::OK,
                Body::full(self.snapshot(now).json()),
                &[
                    (header::CONTENT_TYPE, "application/json"),
                    (header::CACHE_CONTROL, "no-store"),
                ],
            ),
            "/api/live" => self.live(head),
            _ => match path.strip_prefix("/assets/") {
                Some(relative) => asset_response(embedded::asset(relative), headers),
                None => not_found(),
            },
        };
        secure(response, api)
    }

    fn page(&self, headers: &HeaderMap, head: bool, now: u64) -> Response<Body> {
        let lang = language(headers);
        let snapshot = {
            let mut stats = self.stats();
            if !head {
                let address = headers
                    .get(CLIENT_ADDRESS_HEADER)
                    .map_or(&b""[..], HeaderValue::as_bytes);
                let agent = headers
                    .get(header::USER_AGENT)
                    .map_or(&b""[..], HeaderValue::as_bytes);
                stats.visit(address, agent, now);
            }
            stats.snapshot(now)
        };
        let html = template::render(embedded::page(lang), |live| snapshot.text(live, lang));
        reply(
            StatusCode::OK,
            Body::full(html),
            &[
                (header::CONTENT_TYPE, "text/html; charset=utf-8"),
                (header::CACHE_CONTROL, "no-cache"),
                (header::CONTENT_LANGUAGE, lang.code()),
            ],
        )
    }

    fn live(self: &Arc<Self>, head: bool) -> Response<Body> {
        let body = if head {
            Body::empty()
        } else {
            if self.live_streams.fetch_add(1, Ordering::AcqRel) >= self.limits.streams {
                self.live_streams.fetch_sub(1, Ordering::AcqRel);
                return reply(
                    StatusCode::SERVICE_UNAVAILABLE,
                    Body::from_static(b"503\n"),
                    &[
                        (header::CONTENT_TYPE, "text/plain; charset=utf-8"),
                        (header::CACHE_CONTROL, "no-store"),
                        (header::RETRY_AFTER, "30"),
                    ],
                );
            }
            // Écart régulier sur seize crans : des flux ouverts ensemble ne finissent pas ensemble.
            // Even spread over sixteen steps: streams opened together do not end together.
            let step = (self.live_opened.fetch_add(1, Ordering::Relaxed) % 16) as u32;
            let lifetime = self.limits.max_age - self.limits.max_age / 3 * step / 16;
            Body::Live(Box::new(LiveStream {
                app: Arc::clone(self),
                started: false,
                ends: Instant::now() + lifetime,
                stats_timer: None,
                keepalive_timer: None,
            }))
        };
        reply(
            StatusCode::OK,
            body,
            &[
                (header::CONTENT_TYPE, "text/event-stream"),
                (header::CACHE_CONTROL, "no-cache"),
                (HeaderName::from_static("x-accel-buffering"), "no"),
            ],
        )
    }
}

/// Langue d'après le nom demandé (port, casse et point final ignorés) / language from the requested name.
pub fn language(headers: &HeaderMap) -> Lang {
    let host = headers
        .get(header::HOST)
        .and_then(|value| value.to_str().ok())
        .unwrap_or_default();
    let name = host
        .split(':')
        .next()
        .unwrap_or_default()
        .trim_end_matches('.');
    if name.eq_ignore_ascii_case(FR_HOST) {
        Lang::Fr
    } else {
        Lang::En
    }
}

/// security.txt (RFC 9116) : expire un an plus tard / expires one year later.
pub fn security_txt(now: u64) -> String {
    let expires = format::iso_date((now / 86_400) as i64 + 365);
    format!(
        "Contact: mailto:contact@gardienrgpd.fr\nExpires: {expires}T00:00:00Z\nPreferred-Languages: fr, en\n\
         Canonical: https://gardienrgpd.fr/.well-known/security.txt\n\
         Canonical: https://gdprguardian.com/.well-known/security.txt\n"
    )
}

/// Codage choisi pour un fichier statique / encoding chosen for a static file.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Encoding {
    Brotli,
    Gzip,
    Identity,
}

/// Choix selon Accept-Encoding (valeurs q comprises) : brotli, sinon gzip, sinon tel quel.
/// Choice from Accept-Encoding (q-values honoured): brotli, else gzip, else identity.
pub fn negotiate(accept: Option<&HeaderValue>, has_brotli: bool, has_gzip: bool) -> Encoding {
    let Some(accept) = accept.and_then(|value| value.to_str().ok()) else {
        return Encoding::Identity;
    };
    let (mut brotli, mut gzip, mut any) = (None, None, None);
    for item in accept.split(',') {
        let mut parts = item.split(';');
        let coding = parts.next().unwrap_or_default().trim().to_ascii_lowercase();
        let mut quality = 1.0_f32;
        for parameter in parts {
            let parameter = parameter.trim();
            if let Some(value) = parameter
                .strip_prefix("q=")
                .or_else(|| parameter.strip_prefix("Q="))
            {
                quality = value.trim().parse().unwrap_or(0.0);
            }
        }
        match coding.as_str() {
            "br" => brotli = Some(quality),
            "gzip" | "x-gzip" => gzip = Some(quality),
            "*" => any = Some(quality),
            _ => {}
        }
    }
    let brotli = if has_brotli {
        brotli.or(any).unwrap_or(0.0)
    } else {
        0.0
    };
    let gzip = if has_gzip {
        gzip.or(any).unwrap_or(0.0)
    } else {
        0.0
    };
    if brotli > 0.0 && brotli >= gzip {
        Encoding::Brotli
    } else if gzip > 0.0 {
        Encoding::Gzip
    } else {
        Encoding::Identity
    }
}

/// If-None-Match : « * » ou l'une des ETag du fichier (comparaison faible) / "*" or one of the file's ETags.
fn etag_matches(value: &HeaderValue, asset: &Asset) -> bool {
    let Ok(text) = value.to_str() else {
        return false;
    };
    text.split(',').map(str::trim).any(|tag| {
        let tag = tag.strip_prefix("W/").unwrap_or(tag);
        tag == "*" || tag == asset.etag || tag == asset.etag_br || tag == asset.etag_gzip
    })
}

fn asset_response(asset: Option<&'static Asset>, headers: &HeaderMap) -> Response<Body> {
    let Some(asset) = asset else {
        return not_found();
    };
    let encoding = negotiate(
        headers.get(header::ACCEPT_ENCODING),
        asset.br.is_some(),
        asset.gzip.is_some(),
    );
    let (data, etag, coding) = match (encoding, asset.br, asset.gzip) {
        (Encoding::Brotli, Some(data), _) => (data, asset.etag_br, Some("br")),
        (Encoding::Gzip, _, Some(data)) => (data, asset.etag_gzip, Some("gzip")),
        _ => (asset.identity, asset.etag, None),
    };
    let mut fields = vec![
        (header::ETAG, etag),
        (header::CACHE_CONTROL, "public, max-age=3600"),
    ];
    if asset.br.is_some() || asset.gzip.is_some() {
        fields.push((header::VARY, "Accept-Encoding"));
    }
    if headers
        .get(header::IF_NONE_MATCH)
        .is_some_and(|value| etag_matches(value, asset))
    {
        return reply(StatusCode::NOT_MODIFIED, Body::empty(), &fields);
    }
    fields.push((header::CONTENT_TYPE, asset.content_type));
    if let Some(coding) = coding {
        fields.push((header::CONTENT_ENCODING, coding));
    }
    reply(StatusCode::OK, Body::from_static(data), &fields)
}

fn not_found() -> Response<Body> {
    reply(
        StatusCode::NOT_FOUND,
        Body::from_static(b"404\n"),
        &[
            (header::CONTENT_TYPE, "text/plain; charset=utf-8"),
            (header::CACHE_CONTROL, "no-cache"),
        ],
    )
}

fn reply(status: StatusCode, body: Body, fields: &[(HeaderName, &'static str)]) -> Response<Body> {
    let mut response = Response::new(body);
    *response.status_mut() = status;
    let headers = response.headers_mut();
    for (name, value) in fields {
        headers.insert(name.clone(), HeaderValue::from_static(value));
    }
    response
}

/// En-têtes de sécurité de chaque réponse / security headers of every response.
fn secure(mut response: Response<Body>, api: bool) -> Response<Body> {
    let headers = response.headers_mut();
    let csp = if api { CSP_API } else { CSP_SITE };
    headers.insert(
        header::CONTENT_SECURITY_POLICY,
        HeaderValue::from_static(csp),
    );
    headers.insert(
        header::STRICT_TRANSPORT_SECURITY,
        HeaderValue::from_static("max-age=63072000"),
    );
    headers.insert(
        header::X_CONTENT_TYPE_OPTIONS,
        HeaderValue::from_static("nosniff"),
    );
    headers.insert(
        header::REFERRER_POLICY,
        HeaderValue::from_static("no-referrer"),
    );
    headers.insert(
        HeaderName::from_static("permissions-policy"),
        HeaderValue::from_static("camera=(), microphone=(), geolocation=()"),
    );
    headers.insert(
        HeaderName::from_static("cross-origin-opener-policy"),
        HeaderValue::from_static("same-origin"),
    );
    headers.insert(
        HeaderName::from_static("cross-origin-resource-policy"),
        HeaderValue::from_static("same-origin"),
    );
    response
}

/// Corps de réponse : entier, ou flux d'événements / response body: whole, or event stream.
pub enum Body {
    Full(Option<Bytes>),
    Live(Box<LiveStream>),
}

impl Body {
    pub fn empty() -> Body {
        Body::Full(None)
    }

    pub fn full(data: impl Into<Bytes>) -> Body {
        let data = data.into();
        if data.is_empty() {
            Body::Full(None)
        } else {
            Body::Full(Some(data))
        }
    }

    pub fn from_static(data: &'static [u8]) -> Body {
        Body::full(Bytes::from_static(data))
    }

    /// Contenu d'un corps entier (None pour un flux) / content of a whole body (None for a stream).
    pub fn whole(&self) -> Option<Bytes> {
        match self {
            Body::Full(data) => Some(data.clone().unwrap_or_default()),
            Body::Live(_) => None,
        }
    }
}

impl HttpBody for Body {
    type Data = Bytes;
    type Error = Infallible;

    fn poll_frame(
        self: Pin<&mut Self>,
        context: &mut Context<'_>,
    ) -> Poll<Option<Result<Frame<Bytes>, Infallible>>> {
        match self.get_mut() {
            Body::Full(data) => Poll::Ready(data.take().map(|data| Ok(Frame::data(data)))),
            Body::Live(stream) => stream.poll_next(context),
        }
    }

    fn is_end_stream(&self) -> bool {
        matches!(self, Body::Full(None))
    }

    fn size_hint(&self) -> SizeHint {
        match self {
            Body::Full(data) => {
                SizeHint::with_exact(data.as_ref().map_or(0, |data| data.len() as u64))
            }
            Body::Live(_) => SizeHint::default(),
        }
    }
}

/// Flux /api/live : un événement tout de suite, puis toutes les 2 s ; un commentaire toutes les 15 s ; fin après
/// sa durée de vie (le navigateur se reconnecte). /api/live stream: one event at once, then every 2 s; a comment
/// every 15 s; ends after its lifetime (the browser reconnects).
pub struct LiveStream {
    app: Arc<App>,
    started: bool,
    ends: Instant,
    stats_timer: Option<Interval>,
    keepalive_timer: Option<Interval>,
}

fn ticker(period: Duration) -> Interval {
    let mut interval = tokio::time::interval_at(Instant::now() + period, period);
    interval.set_missed_tick_behavior(MissedTickBehavior::Delay);
    interval
}

impl LiveStream {
    fn poll_next(
        &mut self,
        context: &mut Context<'_>,
    ) -> Poll<Option<Result<Frame<Bytes>, Infallible>>> {
        if !self.started {
            self.started = true;
            return Poll::Ready(Some(Ok(Frame::data(self.event(true)))));
        }
        let period = self.app.limits.period;
        if self
            .stats_timer
            .get_or_insert_with(|| ticker(period))
            .poll_tick(context)
            .is_ready()
        {
            // Vérifiée à chaque tic : la fin tombe au plus une période après l'échéance / checked at each tick.
            if Instant::now() >= self.ends {
                return Poll::Ready(None);
            }
            return Poll::Ready(Some(Ok(Frame::data(self.event(false)))));
        }
        let period = self.app.limits.keepalive;
        if self
            .keepalive_timer
            .get_or_insert_with(|| ticker(period))
            .poll_tick(context)
            .is_ready()
        {
            return Poll::Ready(Some(Ok(Frame::data(Bytes::from_static(KEEPALIVE)))));
        }
        Poll::Pending
    }

    fn event(&self, first: bool) -> Bytes {
        let json = self.app.snapshot(unix_now()).json();
        let mut text = String::with_capacity(json.len() + 40);
        if first {
            // Reconnexion du navigateur après 5 s / browser reconnects after 5 s.
            text.push_str("retry: 5000\n");
        }
        text.push_str("event: stats\ndata: ");
        text.push_str(&json);
        text.push_str("\n\n");
        Bytes::from(text)
    }
}

impl Drop for LiveStream {
    fn drop(&mut self) {
        self.app.live_streams.fetch_sub(1, Ordering::AcqRel);
    }
}
