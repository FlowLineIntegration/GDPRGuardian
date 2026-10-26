//! Gardien RGPD · GDPR Guardian : démon du site (gardienrgpd.fr, gdprguardian.com).
//!
//! Page servie depuis le binaire avec ses valeurs en direct (usage du service sur l'heure écoulée, visiteurs, charge
//! du serveur), flux d'événements /api/live, compteurs alimentés par des datagrammes du service. Ni cookie, ni
//! journal de requêtes, ni adresse gardée. Website daemon: page served from the binary with live values, event
//! stream, counters fed by service datagrams. No cookie, no request log, no address kept.

pub mod embedded;
pub mod format;
pub mod http;
#[cfg(unix)]
pub mod server;
pub mod stats;
pub mod sys;
pub mod template;

/// Version du démon / daemon version.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
