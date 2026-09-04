#!/usr/bin/env python3
"""
CLI Entrypoint for RTD Calibration Analysis.

Usage:
    python -m RTD_Calibration_VGP.main --set 12
    python RTD_Calibration_VGP/main.py --set 12
"""

import sys
from pathlib import Path

# Forward execution to scripts/calculate_set_constants.py
script_path = Path(__file__).resolve().parent.parent / "scripts" / "calculate_set_constants.py"

if __name__ == "__main__":
    import runpy
    runpy.run_path(str(script_path), run_name="__main__")
