#!/usr/bin/env python3
"""Programmatically run Set analysis for CalibSetNumber groups with exactly 4 runs.

This avoids notebook execution issues by calling library code directly.
"""
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from RTD_Calibration_VGP.src.logfile import Logfile
from RTD_Calibration_VGP.src.set import Set
from RTD_Calibration_VGP.src.utils import load_config

def main():
    lf_path = repo_root / 'RTD_Calibration_VGP' / 'data' / 'LogFile.csv'
    if not lf_path.exists():
        lf_path = repo_root / 'RTD_Calibration_VGP' / 'data' / 'LogFile_smoke.csv'

    lf = Logfile(str(lf_path))
    df = lf.log_file.copy()

    # Exclude filenames containing '_pre'
    df = df[~df['Filename'].str.contains('_pre', case=False, na=False)]

    # Keep only integer-like CalibSetNumber
    def is_int_like(x):
        try:
            return float(x).is_integer()
        except Exception:
            return False

    df = df[df['CalibSetNumber'].apply(is_int_like)]

    grouped = df.groupby('CalibSetNumber').size()
    sets_eq_4 = sorted([int(x) for x, c in grouped.items() if c == 4])

    print(f'Found {len(sets_eq_4)} sets with exactly 4 runs: {sets_eq_4}')

    cfg_path = repo_root / 'config' / 'example_config.yaml'
    cfg = load_config(str(cfg_path)) if cfg_path.exists() else None

    s = Set(lf.log_file, config=cfg)
    s.group_runs_by_set()

    # Filter runs_by_set to only selected sets
    s.runs_by_set = {k: v for k, v in s.runs_by_set.items() if int(float(k)) in sets_eq_4}
    print('Will run analysis for sets:', sorted(int(float(k)) for k in s.runs_by_set.keys()))

    s.calculate_offsets_and_rms()

    out_dir = repo_root / 'RTD_Calibration_VGP' / 'plots' / 'SET_4runs'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate plots only (no CSV/XLSX)
    s.offset_repeatability(save_dir=str(out_dir), write_csv=False, write_excel=False)

    print('Plots written to:', out_dir)

if __name__ == '__main__':
    main()
