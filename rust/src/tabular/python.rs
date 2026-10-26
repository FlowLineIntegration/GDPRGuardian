//! Interface Python de la lecture xlsx / Python interface of the xlsx reader.
//!
//! `XlsxBook` et `XlsxSheet` offrent le sous-ensemble de `CalamineWorkbook` et `CalamineSheet` dont se sert
//! `gdprguardian.tabular._reader`, avec les mêmes valeurs Python. Analyse sans GIL ; le classeur n'est gardé que le
//! temps de la lecture (l'appelant le libère). `XlsxDecline` : Python reprend avec python-calamine.
//! `XlsxBook` and `XlsxSheet` offer the subset of `CalamineWorkbook` and `CalamineSheet` used by
//! `gdprguardian.tabular._reader`, with the same Python values. Parsing without the GIL; the workbook is only kept
//! while reading (the caller drops it). `XlsxDecline`: Python falls back to python-calamine.

use std::sync::Arc;

use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyDate, PyDateTime, PyDelta, PyFloat, PyList, PyString, PyTime};

use super::cells::{self, Cell, Corner, SheetCells, Value};
use super::dates::{self, Temporal};
use super::extent::{self, Measure, Measured};
use super::parts::{SheetKind, Visibility, Workbook};
use super::xml::Reader;
use super::zip::{Directory, PartIdentity};
use super::Decline;

pyo3::create_exception!(
    gdprguardian_core,
    XlsxDecline,
    PyException,
    "Forme non reconnue : relire avec la référence / unrecognised form: read with the reference."
);

/// Surface dense maximale rendue en une fois (la garde Python borne bien en deçà) / max dense area per call.
const MAX_DENSE: usize = 1 << 26;

fn decline(reason: Decline) -> PyErr {
    XlsxDecline::new_err(reason.0)
}

/// Classeur xlsx ouvert, ses parties communes lues / opened xlsx workbook, its shared parts read.
#[pyclass(name = "XlsxBook", frozen)]
pub struct PyXlsxBook {
    data: Py<PyBytes>,
    directory: Directory,
    workbook: Arc<Workbook>,
}

#[pymethods]
impl PyXlsxBook {
    #[new]
    fn new(py: Python<'_>, data: Bound<'_, PyBytes>) -> PyResult<Self> {
        let bytes = data.as_bytes();
        let (directory, workbook) = py
            .detach(|| {
                let directory = Directory::open(bytes)?;
                let workbook = Workbook::open(&directory, bytes)?;
                Ok((directory, workbook))
            })
            .map_err(decline)?;
        Ok(Self { data: data.unbind(), directory, workbook: Arc::new(workbook) })
    }

    /// `(nom, type, visibilité)` de chaque feuille, dans l'ordre / each sheet, in order.
    #[getter]
    fn sheets(&self) -> Vec<(String, &'static str, &'static str)> {
        self.workbook
            .sheets
            .iter()
            .map(|sheet| {
                let kind = match sheet.kind {
                    SheetKind::Work => "worksheet",
                    SheetKind::Chart => "chartsheet",
                    SheetKind::Dialog => "dialogsheet",
                };
                let visibility = match sheet.visibility {
                    Visibility::Visible => "visible",
                    Visibility::Hidden => "hidden",
                    Visibility::VeryHidden => "veryhidden",
                };
                (sheet.name.clone(), kind, visibility)
            })
            .collect()
    }

    /// Feuille lue en entier (la première de ce nom, comme calamine), partie mesurée au passage comme la garde
    /// Python. Whole sheet, the first with this name; the part is measured on the way as the Python guard does.
    fn sheet(&self, py: Python<'_>, name: &str) -> PyResult<PyXlsxSheet> {
        let bytes = self.data.bind(py).as_bytes();
        let workbook = &self.workbook;
        let directory = &self.directory;
        let read = py.detach(|| {
            let sheet = workbook.sheets.iter().find(|s| s.name == name).ok_or(Decline("worksheet not found"))?;
            let index = directory.find(&sheet.path).ok_or(Decline("worksheet part not found"))?;
            let mut xml = Reader::measuring(directory.reader(bytes, index)?);
            let cells = cells::read(&mut xml, workbook)?;
            let measured = xml.into_measure().zip(directory.identity(index));
            Ok((cells, measured.map(|(measure, identity)| (identity, measure))))
        });
        let (cells, measured) = read.map_err(decline)?;
        Ok(PyXlsxSheet::new(cells, Arc::clone(&self.workbook), measured))
    }
}

/// Mesure rendue à Python : partie, taille, CRC, étendue, formules, en-têtes / measurement handed to Python.
type PartMeasure = (String, u64, u32, Option<(u128, u128)>, usize, bool);

/// Feuille lue : étendue, fusions, lignes en valeurs Python / sheet read: extent, merges, rows as Python values.
#[pyclass(name = "XlsxSheet", frozen)]
pub struct PyXlsxSheet {
    sheet: SheetCells,
    workbook: Arc<Workbook>,
    start: Option<Corner>,
    end: Corner,
    /// Partie lue et sa mesure (des comptes, aucun contenu) / part read and its measurement (counts, no content).
    measured: Option<(PartIdentity, Measure)>,
}

impl PyXlsxSheet {
    /// Bornes des cellules non vides, comme `Range::from_sparse` / bounds of the non-empty cells.
    fn new(sheet: SheetCells, workbook: Arc<Workbook>, measured: Option<(PartIdentity, Measure)>) -> Self {
        let start = sheet.cells.iter().fold(None, |acc: Option<Corner>, cell| {
            Some(acc.map_or((cell.row, cell.col), |(r, c)| (r.min(cell.row), c.min(cell.col))))
        });
        let end = sheet.cells.iter().fold((0, 0), |(r, c), cell| (r.max(cell.row), c.max(cell.col)));
        Self { sheet, workbook, start, end, measured }
    }

    fn value<'py>(&self, py: Python<'py>, cell: &Cell, empty: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
        Ok(match cell.value {
            Value::Float(f) => PyFloat::new(py, f).into_any(),
            Value::Bool(b) => PyBool::new(py, b).to_owned().into_any(),
            Value::Shared(index) => {
                let text =
                    self.workbook.strings.get(index as usize).ok_or(Decline("shared string")).map_err(decline)?;
                PyString::new(py, text).into_any()
            }
            Value::Text { start, len } => {
                let (start, stop) = (start as usize, start as usize + len as usize);
                let text = self.sheet.text.get(start..stop).ok_or(Decline("text arena")).map_err(decline)?;
                PyString::new(py, text).into_any()
            }
            Value::Error => empty.clone(),
            Value::Date { serial, duration } => {
                let temporal = dates::convert(serial, duration, self.workbook.is_1904)
                    .ok_or(Decline("date panic"))
                    .map_err(decline)?;
                temporal_value(py, temporal)?
            }
        })
    }
}

/// Objet Python d'une valeur datée (conversions chrono de PyO3) / Python object of a dated value.
fn temporal_value(py: Python<'_>, temporal: Temporal) -> PyResult<Bound<'_, PyAny>> {
    Ok(match temporal {
        Temporal::Float(f) => PyFloat::new(py, f).into_any(),
        Temporal::Date { year, month, day } => PyDate::new(py, year, month, day)?.into_any(),
        Temporal::DateTime { year, month, day, hour, minute, second, micro } => {
            PyDateTime::new(py, year, month, day, hour, minute, second, micro, None)?.into_any()
        }
        Temporal::Time { hour, minute, second, micro } => {
            PyTime::new(py, hour, minute, second, micro, None)?.into_any()
        }
        Temporal::Delta { days, seconds, micros } => {
            PyDelta::new(py, i32::try_from(days).unwrap_or(i32::MAX), seconds, micros, true)?.into_any()
        }
    })
}

#[pymethods]
impl PyXlsxSheet {
    #[getter]
    fn start(&self) -> Option<Corner> {
        self.start
    }

    #[getter]
    fn height(&self) -> usize {
        self.start.map_or(0, |(r, _)| (self.end.0 - r) as usize + 1)
    }

    #[getter]
    fn width(&self) -> usize {
        self.start.map_or(0, |(_, c)| (self.end.1 - c) as usize + 1)
    }

    /// Plages fusionnées `((ligne, colonne), (ligne, colonne))`, base 0 / merged ranges, 0-based.
    #[getter]
    fn merged(&self) -> Vec<(Corner, Corner)> {
        self.sheet.merged.clone()
    }

    /// `(partie, taille, crc, étendue | None, formules, en-têtes)` : la mesure de `_package.xlsx_extent` et
    /// `_count_sheet_parts` sur la partie lue ; `None` si sa fin était illisible.
    /// The `xlsx_extent` and `_count_sheet_parts` measurement of the part read; `None` when its end was unreadable.
    fn measured(&self, limit: u128) -> Option<PartMeasure> {
        self.measured.as_ref().map(|((part, size, crc), measure)| {
            let (extent, formulas, headers) = measure.result(limit);
            (part.clone(), *size, *crc, extent, formulas, headers)
        })
    }

    /// Les `nrows` premières lignes de la grille (toutes par défaut), comme `CalamineSheet.to_python` ; cellule
    /// vide ou en erreur : `""`. The first `nrows` grid rows (all by default), as `to_python`; empty or error: `""`.
    #[pyo3(signature = (nrows=None))]
    fn rows<'py>(&self, py: Python<'py>, nrows: Option<usize>) -> PyResult<Bound<'py, PyList>> {
        let Some((row0, col0)) = self.start else { return Ok(PyList::empty(py)) };
        let (height, width) = (self.height(), self.width());
        let take = nrows.unwrap_or(height).min(height);
        let area = take.checked_mul(width).filter(|&a| a <= MAX_DENSE).ok_or(Decline("area")).map_err(decline)?;
        // Dernière cellule d'une position : elle l'emporte, comme `from_sparse` / last cell at a position wins.
        let mut grid = vec![u32::MAX; area];
        for (index, cell) in self.sheet.cells.iter().enumerate() {
            let row = (cell.row - row0) as usize;
            if row < take {
                grid[row * width + (cell.col - col0) as usize] = index as u32;
            }
        }
        let empty = PyString::new(py, "").into_any();
        let mut rows = Vec::with_capacity(take);
        let mut values = Vec::with_capacity(width);
        for line in grid.chunks(width.max(1)) {
            values.clear();
            for &index in line {
                values.push(match self.sheet.cells.get(index as usize) {
                    Some(cell) => self.value(py, cell, &empty)?,
                    None => empty.clone(),
                });
            }
            rows.push(PyList::new(py, values.drain(..))?);
        }
        PyList::new(py, rows)
    }
}

/// `(étendue | None, formules, en-têtes)` d'une partie de feuille : chemin rapide de `xlsx_extent` (`None` :
/// chemin exact en Python) et comptes de `_count_sheet_parts`, en un passage.
/// A sheet part's fast-path extent (`None`: exact path in Python) and `_count_sheet_parts` counts, in one pass.
#[pyfunction]
fn sheet_measure(py: Python<'_>, xml: &Bound<'_, PyBytes>, limit: u128) -> Measured {
    let bytes = xml.as_bytes();
    py.detach(|| extent::measure(bytes, limit))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyXlsxBook>()?;
    m.add_class::<PyXlsxSheet>()?;
    m.add("XlsxDecline", m.py().get_type::<XlsxDecline>())?;
    m.add_function(wrap_pyfunction!(sheet_measure, m)?)?;
    Ok(())
}
