# rtd-calibration-ana

RTD calibration analysis utilities and notebooks.

This repository contains code and notebooks to analyze RTD (Resistance Temperature Detector)
calibration runs. The main processing modules are under `RTD_Calibration_VGP/src/` and the
logfile and temperature data live in `RTD_Calibration_VGP/data/`.

## 🚀 Quick Start: RTD Calibration Constants

Calibrate any RTD set directly from the terminal without opening Jupyter:

```bash
# Calibrate Set 12 (default: Channel 2 as reference)
python3 scripts/calculate_set_constants.py --set 12

# Calibrate Set 12 using official EOS Excel LogFile
python3 scripts/calculate_set_constants.py --set 12 --eos

# Specify a custom reference channel (e.g. Channel 13 / probe 49215)
python3 scripts/calculate_set_constants.py --set 12 --ref-ch 13
```

Outputs:
- Terminal summary table with offsets, repeatability $\sigma$, and per-run values.
- CSV table saved to `RTD_Calibration_VGP/outputs/set_{SET}/set_{SET}_calibration_constants.csv`.
- Repeatability multi-panel plot saved to `RTD_Calibration_VGP/outputs/set_{SET}/offset_repeatability_set_{SET}.png`.

### Precision Resistances (STS) Constants
For STS resistance calibration sets (`RESIST_SET1` to `5`):
```bash
python3 RTD_Calibration_VGP/notebooks/calculate_calibration_constants.py
```
Outputs: `calibration_constants_resistences.csv` and `.txt`.


## Quick start

1. Create and activate a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run a minimal analysis from a Python REPL or a notebook (uses the repo example config):

```python
from RTD_Calibration_VGP.src.utils import load_config
from RTD_Calibration_VGP.src.logfile import Logfile
from RTD_Calibration_VGP.src.set import Set

# example config shipped with the repo
cfg = load_config('config/example_config.yaml')

# Logfile can be a path or a pre-loaded DataFrame
lf = Logfile('RTD_Calibration_VGP/data/LogFile_smoke.csv')
s = Set(lf.log_file, config=cfg)
s.group_runs_by_set()            # group runs by CalibSetNumber
s.calculate_offsets_and_rms()    # compute offsets and RMS per run
# generate repeatability plots for eligible sets (plots-only by default in example config)
s.offset_repeatability(write_csv=False, write_excel=False)
```

3. Open the notebooks (optional):

- `notebooks/SET_BUENO.ipynb` — set-level analysis and plotting
- `notebooks/RUN_BUENO.ipynb` — run-level visual checks

Notes: The code was made more defensive to run in CI-like environments. By default the
example config disables CSV/XLSX summary writing and only writes PNG plots to
`RTD_Calibration_VGP/plots/analysis_runs_vs_set_no_pre`.

## Configuration

- Example config: `config/example_config.yaml` (used by the quick-start snippet above).
- **Sensor configuration**: `RTD_Calibration_VGP/config/sensors.yaml` — Defines per-set metadata including:
  - `discarded`: Sensors to exclude from analysis
  - `raised`: Bridge sensors that appear in multiple calibration rounds
  - `round`: Calibration round number (1=R1, 2=R2, 3=R3/Reference)
- Key behavior toggles:
  - `output.write_csv` / `output.write_excel`: control whether numeric summaries are written.
  - `paths.logfile`: path to the main `LogFile.csv` (or a test/smoke CSV).
  - Per-set metadata: `discarded_sensors`, `sensors_raised_by_set`, `set_rounds` can be provided
    in the YAML and are merged into the `Set` instance on construction.

The `Set` class accepts either a `Logfile` object, a DataFrame, or a path to a logfile.
See `RTD_Calibration_VGP/src/utils.py` and `RTD_Calibration_VGP/src/logfile.py` for details.

### Sensor Configuration Format

Example `sensors.yaml` structure:
```yaml
sensors:
  sets:
    3:
      discarded: [48205, 48478]
      raised: [48203, 48479]
      round: 1
    49:
      discarded: []
      raised: [48203, 48479]  # Same sensors appear in R2
      round: 2
    57:
      discarded: []
      raised: []
      round: 3  # Reference set
```

**Important**: The calibration network automatically detects connections between sets based on shared "raised" sensors. Set 3 (R1) connects to Set 49 (R2) because they share sensors 48203 and 48479.

## Smoke dataset (for CI)

The repo includes a tiny smoke dataset for CI and fast iteration:

- `RTD_Calibration_VGP/data/LogFile_smoke.csv`
- `RTD_Calibration_VGP/data/temperature_files/CalSetN_1/smoke_run_*.txt`

Use the example config `config/example_config.yaml` to point the code at the smoke dataset.

## Tests

Run unit tests with pytest (from the repo root inside the venv):

```bash
source .venv/bin/activate
pytest -q
```

A small test ensures that when `write_csv=False` and `write_excel=False` only PNGs are produced
and no CSV/XLSX files get written.

## Advanced Features: Multi-Path Calibration Offset Calculation

The `CalibrationNetwork` class in `src/calibration_network.py` provides advanced methods for computing calibration offsets using multiple paths through the calibration chain.

### Single-Path Offset Calculation

```python
from RTD_Calibration_VGP.src.calibration_network import CalibrationNetwork
from RTD_Calibration_VGP.src.logfile import Logfile

# Initialize network
net = CalibrationNetwork()
logfile = Logfile('RTD_Calibration_VGP/data/LogFile.csv')

# Build calibration chain for a sensor (finds path from R1 → R2 → R3)
chain = net.build_calibration_chain(
    sensor_id=48203,
    logfile_df=logfile.log_file,
    verbose=True
)

# Calculate offset along the chain
offset, error, details = net.calculate_offset_from_chain(chain, verbose=True)
print(f"Offset: {offset:.6f} ± {error:.6f}")
```

### Multi-Path Weighted Offset Calculation

For sensors with multiple "raised" sensors (bridge sensors appearing in multiple rounds), you can calculate offsets through **all possible paths** and compute a weighted average:

```python
# Calculate offset using ALL possible paths through raised sensors
offset_weighted, error_weighted, info = net.compute_weighted_offset_all_paths(
    sensor_id=48203,
    logfile_df=logfile.log_file,
    verbose=True
)

print(f"Number of paths found: {info['n_paths']}")
print(f"Best path error: {info['error_best']:.6f}")
print(f"Weighted average offset: {offset_weighted:.6f} ± {error_weighted:.6f}")
```

**How it works:**
1. Finds all "raised" sensors configured for the calibration set
2. Builds a calibration chain for each raised sensor
3. Calculates offset and error for each path
4. Computes weighted average using inverse variance weighting:
   - Weight: `w_i = 1 / error_i²`
   - Final offset: `Σ(offset_i × w_i) / Σ(w_i)`
   - Final error: `1 / √(Σw_i)`

This approach typically reduces the final uncertainty by combining information from multiple independent calibration paths.

**Example output:**
```
 RESUMEN DE CAMINOS CALCULADOS
   Total de caminos válidos: 3/3

 MEJOR CAMINO (menor error):
   Camino #2: Sensor raised 48204
   Offset: 0.123456 ± 0.000234

 RESULTADO FINAL (MEDIA PONDERADA):
   Offset ponderado: 0.123450
   Error ponderado:  0.000198
   
 COMPARACIÓN CON MEJOR CAMINO:
    Media ponderada tiene MENOR error (0.000198 < 0.000234)
```

See `notebooks/TREE.ipynb` for a complete working example.

## Plotting behavior and important rules

- The helper that generates repeatability plots excludes any `Filename` containing `_pre`
  (case-insensitive).
- Only integer-like `CalibSetNumber` values are processed (e.g. 3.0 is accepted, 3.5 is ignored).
- Sets with exactly 4 runs are included (threshold is `>= 4`).

## Troubleshooting

- If notebooks fail to import the package when executed programmatically, ensure the repo root is
  on `PYTHONPATH` or open the notebook from the repo root. The quick-start snippet uses direct
  imports which assume the venv's working directory is the repo root.
- If Excel writing fails in minimal CI environments, disable `output.write_excel` in the config or
  pass `write_excel=False` to `Set.offset_repeatability()`.
- **Type handling**: The codebase handles mixed types (Python int/float, numpy int64/float64, pandas objects) gracefully. If you encounter type-related errors:
  - Ensure `sensors.yaml` uses numeric keys (not strings): `3:` not `"3":`
  - CalibSetNumber in LogFile.csv can be any numeric-like format (will be converted)
  - Use `isinstance(x, (int, float, np.integer, np.floating))` for type checks involving pandas data

## Contributing / Next steps

- Add a CI workflow that runs pytest and the smoke integration test on push (recommended).
- Optionally add a small CLI (`scripts/run_analysis.py`) to make common workflows easier.

If you'd like, I can add the integration test that runs the pipeline end-to-end on the smoke dataset
and a GitHub Actions workflow that runs the tests on push. Tell me which you'd like first.

## Project Structure

```
rtd-calibration-ana/
├── RTD_Calibration_VGP/          # Main package
│   ├── src/                      # Source code (run.py, set.py, logfile.py, utils.py)
│   ├── data/                     # LogFile.csv and temperature files
│   ├── config/                   # Configuration files (config.yaml, config.example.yaml)
│   ├── notebooks/                # Jupyter notebooks for analysis
│   │   ├── RUN_BUENO.ipynb      # Run-level analysis
│   │   ├── SET_BUENO.ipynb      # Set-level analysis (main workflow)
│   │   └── outputs/             # Generated plots and CSV summaries
│   └── plots/                    # Additional generated plots
├── scripts/                      # Utility scripts
│   ├── cleanup_temp_dirs.sh     # Clean temporary test directories
│   ├── run_set_notebook.py      # Programmatic notebook execution
│   └── count_sets.py            # Dataset analysis utilities
├── tests/                        # Unit tests
├── docs/                         # Documentation and reference files
└── README.md                     # This file
```

## Utility Scripts

- **`scripts/cleanup_temp_dirs.sh`** — Clean temporary test/debug directories
  ```bash
  ./scripts/cleanup_temp_dirs.sh --dry-run  # Preview what would be deleted
  ./scripts/cleanup_temp_dirs.sh            # Delete tmp_* directories
  ```
