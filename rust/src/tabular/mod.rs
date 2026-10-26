//! Lecture native des classeurs xlsx / native xlsx reading.
//!
//! La référence reste python-calamine (calamine 0.36.1) : ce module en reproduit exactement les valeurs, types,
//! étendues et fusions, mais seulement pour les formes canoniques d'un classeur (Excel, LibreOffice, openpyxl,
//! xlsxwriter…). Au moindre écart (commentaire XML, entité inconnue, encodage non UTF-8, ZIP64, valeur hors des
//! formes reconnues, erreur que calamine signalerait…), la lecture est refusée (`Decline`) et Python reprend avec
//! la référence : aucun cas douteux n'est deviné. Code sûr, sans `unsafe` ; décompression en flux, mémoire
//! bornée ; aucune donnée gardée après l'appel ; aucun contenu dans les messages.
//!
//! python-calamine (calamine 0.36.1) stays the reference: this module reproduces exactly its values, types,
//! extents and merges, but only for the canonical forms of a workbook. On any deviation, reading is declined
//! (`Decline`) and Python falls back to the reference: no doubtful case is guessed. Safe code, no `unsafe`;
//! streamed inflation, bounded memory; nothing kept after the call; no content in messages.

mod cells;
mod dates;
mod extent;
mod parts;
mod python;
mod xml;
mod zip;

pub use python::register;

/// Refus de la voie native, avec une raison fixe (jamais de contenu) / native decline, fixed reason (no content).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Decline(pub &'static str);

pub(crate) type Result<T> = std::result::Result<T, Decline>;
