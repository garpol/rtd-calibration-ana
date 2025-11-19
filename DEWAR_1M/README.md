# DEWAR 1m Calibration Analysis

This directory contains analysis tools and notebooks for DEWAR 1m FBG (Fiber Bragg Grating) and temperature calibration data.

## 📂 Structure

### Core Module
- **`dewar_analysis.py`** - Main Python module with reusable classes and functions
  - `DewarDataLoader`: Load and preprocess ROOT files
  - `DewarAnalyzer`: Statistical analysis and fitting
  - `DewarPlotter`: Publication-quality plotting
  - `quick_analysis()`: One-line analysis function

### Notebooks
- **`DEWAR_GENERAL_ANALYSIS.ipynb`** - General analysis notebook using the module (recommended)
- **`ROOT_DEWAR_07_11.ipynb`** - Analysis for run 2025-11-07
- **`ROOT_DEWAR_19_11.ipynb`** - Analysis for run 2025-11-19
- **`ROOT_DEWAR_29_10.ipynb`** - Analysis for run 2025-10-29
- **`DEWAR_29_10.ipynb`** - Initial analysis notebook

### Scripts
- **`example_quick_analysis.py`** - Example script for terminal execution

### Documentation
- **`README_ANALYSIS.md`** - Complete API documentation (English)
- **`GUIA_RAPIDA.md`** - Quick guide (Spanish)

## 🚀 Quick Start

### Using the Module (Recommended)

```python
from dewar_analysis import quick_analysis

# Analyze Sensor 3 from 2025-11-19, 16:00-18:00
loader, analyzer, plotter, fit_results = quick_analysis(
    file_path="/path/to/20251119.root",
    date="2025-11-19",
    start_hour=16,
    end_hour=18,
    sensor_idx=2  # Sensor 3 (0-based index)
)
```

### Using Notebooks
1. Open `DEWAR_GENERAL_ANALYSIS.ipynb`
2. Modify parameters (date, time, sensor)
3. Execute cells

## 📊 Key Features

- ✅ Reusable analysis framework
- ✅ Automatic time correction (+2h for peak data)
- ✅ Multi-sensor comparison
- ✅ Weighted linear fitting (T vs λB)
- ✅ Sensor offset analysis
- ✅ Publication-ready plots

## 🔧 Requirements

- Python 3.7+
- uproot
- numpy
- pandas
- matplotlib
- datetime

## 📝 Sensor Mapping

| Index | Sensor | Height (m) |
|-------|--------|------------|
| 0     | Sensor 1 | 2        |
| 1     | Sensor 2 | 3        |
| 2     | Sensor 3 | 4        |
| 3     | Sensor 4 | 5        |
| 4     | Sensor 5 | 6        |

## 📚 Documentation

For detailed documentation, see:
- `README_ANALYSIS.md` - Complete API reference
- `GUIA_RAPIDA.md` - Spanish quick guide

## 🎯 Typical Workflow

1. Load data: `DewarDataLoader(file_path)`
2. Analyze: `DewarAnalyzer(loader)`
3. Resample: `analyzer.resample_sensor_data()`
4. Fit: `analyzer.fit_temperature_vs_wavelength()`
5. Plot: `DewarPlotter().plot_**()`

## 📧 Contact

DUNE HD Calibration Team

---
Last Updated: November 19, 2025
