//! Site embarqué à la construction (build.rs) / site embedded at build time.

use crate::format::Lang;
use crate::template::{Live, Seg};

/// Fichier statique et ses variantes précompressées / static file and its precompressed variants.
#[derive(Debug)]
pub struct Asset {
    /// Chemin sous /assets/ / path under /assets/.
    pub path: &'static str,
    pub content_type: &'static str,
    /// ETag de chaque variante, guillemets compris / each variant's ETag, quotes included.
    pub etag: &'static str,
    pub etag_br: &'static str,
    pub etag_gzip: &'static str,
    pub identity: &'static [u8],
    pub br: Option<&'static [u8]>,
    pub gzip: Option<&'static [u8]>,
}

include!(concat!(env!("OUT_DIR"), "/embedded.rs"));

/// Fichier statique par chemin exact (liste triée) / static file by exact path (sorted list).
pub fn asset(path: &str) -> Option<&'static Asset> {
    ASSETS
        .binary_search_by(|asset| asset.path.cmp(path))
        .ok()
        .map(|index| &ASSETS[index])
}

/// Gabarit découpé d'une langue / split template of a language.
pub fn page(lang: Lang) -> &'static [Seg<&'static str>] {
    match lang {
        Lang::Fr => PAGE_FR,
        Lang::En => PAGE_EN,
    }
}

/// Toutes les valeurs en direct utilisées par une page / every live value a page uses.
pub fn live_values(lang: Lang) -> Vec<Live> {
    let mut found: Vec<Live> = page(lang)
        .iter()
        .filter_map(|seg| match seg {
            Seg::Live(live) => Some(*live),
            Seg::Lit(_) => None,
        })
        .collect();
    found.dedup();
    found
}
