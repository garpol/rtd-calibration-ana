#!/usr/bin/env python3
"""Count CalibSetNumber groups in the logfile.
Rules:
 - Exclude any Filename containing '_pre' (case-insensitive)
 - Only consider integer-like CalibSetNumber values (e.g., 3.0 is ok)
 - Print sets with exactly 4 runs and sets with >4 runs, plus their counts and IDs
"""
import re
import sys
from pathlib import Path
import pandas as pd

# Add repo root to path if run directly
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from RTD_Calibration_VGP.src.logfile import Logfile

LOGFILE = Path('RTD_Calibration_VGP/data/LogFile.csv')
if not LOGFILE.exists():
    # fallback to smoke logfile if main logfile is missing
    LOGFILE = Path('RTD_Calibration_VGP/data/LogFile_smoke.csv')

lf = Logfile(str(LOGFILE))
df = lf.log_file.copy()

# Coerce CalibSetNumber to numeric if needed (already done by Logfile but be safe)
df['CalibSetNumber'] = pd.to_numeric(df['CalibSetNumber'], errors='coerce')

# Exclude filenames containing '_pre' case-insensitive
mask_pre = df['Filename'].str.contains('_pre', case=False, na=False)
df = df[~mask_pre]

# Keep only integer-like CalibSetNumber (e.g., 3.0)
# Build a boolean mask aligned with df's index
def is_int_like(x):
    try:
        return float(x).is_integer()
    except Exception:
        return False

mask_int_like = df['CalibSetNumber'].apply(is_int_like)
df = df[mask_int_like]

# Group and count
grouped = df.groupby('CalibSetNumber').size().sort_index()

sets_eq_4 = grouped[grouped == 4]
sets_gt_4 = grouped[grouped > 4]

print(f"Total integer-like sets (after excluding '_pre'): {len(grouped)}")
print(f"Sets with exactly 4 runs: {len(sets_eq_4)}")
if len(sets_eq_4) > 0:
    print('IDs (exactly 4):', ', '.join(str(int(x)) for x in sets_eq_4.index))

print(f"Sets with more than 4 runs: {len(sets_gt_4)}")
if len(sets_gt_4) > 0:
    print('IDs (>4):', ', '.join(str(int(x)) for x in sets_gt_4.index))

# For convenience, print a short table
print('\nSummary (CalibSetNumber -> count):')
for csn, cnt in grouped.items():
    print(f"  {int(csn)} -> {cnt}")
