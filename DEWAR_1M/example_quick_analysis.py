#!/usr/bin/env python3
"""
Example script: Quick DEWAR analysis
=====================================

This script demonstrates the simplest way to analyze DEWAR data
using the dewar_analysis module.

Usage:
    python example_quick_analysis.py
"""

import sys
sys.path.insert(0, '/eos/user/v/vgarciap/SWAN_projects/DUNEHD/CALIB/DEWAR_1M')

from dewar_analysis import quick_analysis
import matplotlib.pyplot as plt

# ============================================================================
# CONFIGURATION
# ============================================================================

# File path to ROOT data
FILE_PATH = "/eos/user/j/jcapotor/FBGdata/ROOTFiles/Dewar1m/20251119.root"

# Date and time window
DATE = "2025-11-19"
START_HOUR = 16
END_HOUR = 18

# Sensor to analyze (0-based index: 0=Sensor1, 2=Sensor3, etc.)
SENSOR_IDX = 2  # Sensor 3

# Resampling interval
RESAMPLE_INTERVAL = "5min"

# ============================================================================
# ANALYSIS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DEWAR QUICK ANALYSIS")
    print("="*60)
    print(f"File: {FILE_PATH}")
    print(f"Date: {DATE}")
    print(f"Time window: {START_HOUR}:00 - {END_HOUR}:00")
    print(f"Sensor: {SENSOR_IDX+1}")
    print(f"Resample: {RESAMPLE_INTERVAL}")
    print("="*60 + "\n")
    
    try:
        # Run quick analysis
        loader, analyzer, plotter, fit_results = quick_analysis(
            file_path=FILE_PATH,
            date=DATE,
            start_hour=START_HOUR,
            end_hour=END_HOUR,
            sensor_idx=SENSOR_IDX,
            resample_interval=RESAMPLE_INTERVAL
        )
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nClose the plot windows to exit.")
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: File not found")
        print(f"   {e}")
        print("\n   Please check:")
        print("   1. File path is correct")
        print("   2. File exists on EOS")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {e}")
        sys.exit(1)
