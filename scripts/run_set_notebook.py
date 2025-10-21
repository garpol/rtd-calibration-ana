#!/usr/bin/env python3
"""Run SET_BUENO.ipynb restricted to sets with exactly 4 runs.

This script:
 - Finds CalibSetNumber groups that are integer-like and have exactly 4 runs (excludes filenames with '_pre').
 - Injects a code cell at the top of the notebook that defines `selected_sets` (list of ints) and disables CSV/XLSX output.
 - Executes the notebook and writes the executed version to `notebooks/SET_BUENO_4runs_executed.ipynb`.

Run from the repo root with the project's venv active:
  source .venv/bin/activate
  python3 scripts/run_set_notebook.py
"""
import sys
from pathlib import Path
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from RTD_Calibration_VGP.src.logfile import Logfile

NOTEBOOK_SRC = repo_root / 'notebooks' / 'SET_BUENO.ipynb'
NOTEBOOK_OUT = repo_root / 'notebooks' / 'SET_BUENO_4runs_executed.ipynb'

# Load logfile (prefer main, fallback to smoke)
lf_path = repo_root / 'RTD_Calibration_VGP' / 'data' / 'LogFile.csv'
if not lf_path.exists():
    lf_path = repo_root / 'RTD_Calibration_VGP' / 'data' / 'LogFile_smoke.csv'

lf = Logfile(str(lf_path))
df = lf.log_file.copy()

# Exclude filenames with '_pre' (case-insensitive)
df = df[~df['Filename'].str.contains('_pre', case=False, na=False)]

# Keep only integer-like CalibSetNumber
def is_int_like(x):
    try:
        return float(x).is_integer()
    except Exception:
        return False

mask_int = df['CalibSetNumber'].apply(is_int_like)
df = df[mask_int]

grouped = df.groupby('CalibSetNumber').size()
sets_eq_4 = sorted([int(x) for x, c in grouped.items() if c == 4])

if not NOTEBOOK_SRC.exists():
    print(f"Notebook source not found: {NOTEBOOK_SRC}")
    sys.exit(2)

print(f"Found {len(sets_eq_4)} sets with exactly 4 runs: {sets_eq_4}")

# Read the notebook
nb = nbformat.read(str(NOTEBOOK_SRC), as_version=4)

# Prepare an injection cell that defines selected_sets and disables CSV/XLSX output
injection_code = (
    f"# Injected by scripts/run_set_notebook.py\n"
    f"selected_sets = {sets_eq_4}\n"
    f"# Prefer plots-only for automated runs\n"
    f"write_csv = False\n"
    f"write_excel = False\n"
)

injection_cell = nbformat.v4.new_code_cell(injection_code)

# Insert the injection cell at the top (after any initial metadata markdown if present)
nb['cells'].insert(0, injection_cell)

# Execute the notebook
ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
try:
    ep.preprocess(nb, {'metadata': {'path': str(repo_root)}})
except Exception as e:
    print('Notebook execution failed:', e)
    # Still write whatever outputs were produced
    nbformat.write(nb, str(NOTEBOOK_OUT))
    print(f'Partial executed notebook saved to: {NOTEBOOK_OUT}')
    raise

# Write executed notebook
nbformat.write(nb, str(NOTEBOOK_OUT))
print(f'Executed notebook saved to: {NOTEBOOK_OUT}')

print('Done.')
