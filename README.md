# rtd-calibration-ana

RTD calibration analysis utilities and notebooks.

This repository contains code and notebooks to analyze RTD (Resistance Temperature Detector)
calibration runs. The main processing modules are under `RTD_Calibration_VGP/src/` and the
logfile and temperature data live in `RTD_Calibration_VGP/data/`.

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
- Key behavior toggles:
  - `output.write_csv` / `output.write_excel`: control whether numeric summaries are written.
  - `paths.logfile`: path to the main `LogFile.csv` (or a test/smoke CSV).
  - Per-set metadata: `discarded_sensors`, `sensors_raised_by_set`, `set_rounds` can be provided
    in the YAML and are merged into the `Set` instance on construction.

The `Set` class accepts either a `Logfile` object, a DataFrame, or a path to a logfile.
See `RTD_Calibration_VGP/src/utils.py` and `RTD_Calibration_VGP/src/logfile.py` for details.

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
