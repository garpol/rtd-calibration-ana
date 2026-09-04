#!/usr/bin/env python3
"""
Calculate RTD Calibration Constants & Repeatability for a given Calibration Set.

Usage:
    python scripts/calculate_set_constants.py --set 12
    python scripts/calculate_set_constants.py --set 12 --ref-ch 2
    python scripts/calculate_set_constants.py --set 12 --logfile /eos/project/n/neutrinos-ific/.../Calibration-LogFile(reparado-editable).xlsx
    python scripts/calculate_set_constants.py --set 12 --save-dir outputs/set_12

Features:
    - Loads calibration data for the specified set (CSV or Excel).
    - Computes offsets between all sensors and the reference sensor across all runs.
    - Calculates the repeatability standard deviation (sigma) across runs.
    - Displays a clean formatted summary table in terminal.
    - Exports results to CSV and generates repeatability plots.
"""

import sys
import os
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from RTD_Calibration_VGP.src.logfile import Logfile
from RTD_Calibration_VGP.src.set import Set


DEFAULT_EOS_LOGFILE = (
    "/eos/project/n/neutrinos-ific/02-Temperature_Monitor_System/IFIC/"
    "Lab_Tests/RTD_Calibs/Calibration-LogFile(reparado-editable).xlsx"
)
DEFAULT_LOCAL_LOGFILE = str(repo_root / "RTD_Calibration_VGP/data/LogFile.csv")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Calculate calibration constants and repeatability for an RTD calibration set."
    )
    parser.add_argument(
        "--set", "-s",
        type=float,
        default=12.0,
        help="Calibration set number to process (e.g. 12, 11, 3). Default: 12"
    )
    parser.add_argument(
        "--logfile", "-l",
        type=str,
        default=None,
        help=(
            "Path to the logfile (.csv or .xlsx). "
            f"If not provided, uses local CSV ({DEFAULT_LOCAL_LOGFILE}). "
            "Pass '--eos' to use the official EOS Excel file."
        )
    )
    parser.add_argument(
        "--eos",
        action="store_true",
        help="Use the official EOS Excel logfile."
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=str(repo_root / "RTD_Calibration_VGP/config/config.yml"),
        help="Path to config.yml. Default: RTD_Calibration_VGP/config/config.yml"
    )
    parser.add_argument(
        "--ref-ch",
        type=int,
        default=2,
        help="Channel to use as reference sensor (default: 2)."
    )
    parser.add_argument(
        "--ref-sensor",
        type=str,
        default=None,
        help="Sensor ID to use as reference sensor (overrides --ref-ch if provided)."
    )
    parser.add_argument(
        "--fixed-ref",
        action="store_true",
        help="Force a single fixed reference channel (--ref-ch), even if the set has raised sensors."
    )
    parser.add_argument(
        "--save-dir", "-o",
        type=str,
        default=None,
        help="Directory to save output CSV and plot. Default: RTD_Calibration_VGP/outputs/set_{SET}"
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip generating repeatability plot image."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    set_num = args.set
    if set_num.is_integer():
        set_str = str(int(set_num))
    else:
        set_str = str(set_num)

    # Determine logfile path
    if args.logfile:
        logfile_path = args.logfile
    elif args.eos:
        logfile_path = DEFAULT_EOS_LOGFILE
    else:
        logfile_path = DEFAULT_LOCAL_LOGFILE

    if not os.path.exists(logfile_path):
        print(f"❌ Error: Logfile not found at '{logfile_path}'")
        sys.exit(1)

    print("=" * 80)
    print(f"  RTD CALIBRATION CONSTANTS — CALIBRATION SET {set_str}")
    print("=" * 80)
    print(f"📁 Logfile:    {logfile_path}")
    print(f"⚙️  Config:     {args.config}")

    # Output directory
    save_dir = args.save_dir or str(repo_root / f"RTD_Calibration_VGP/outputs/set_{set_str}")
    os.makedirs(save_dir, exist_ok=True)
    print(f"💾 Output dir: {save_dir}")

    # Initialize Set instance
    set_engine = Set(logfile=logfile_path, config_path=args.config)
    
    # Filter and load runs for this set
    print(f"\n🔍 Loading runs for Set {set_str}...")
    set_engine.group_runs_by_set(selected_sets=[set_num])

    if set_num not in set_engine.runs_by_set:
        print(f"❌ Error: No valid runs found for Set {set_str} in logfile.")
        sys.exit(1)

    runs = set_engine.runs_by_set[set_num]
    run_names = list(runs.keys())
    n_runs = len(run_names)
    print(f"✅ Loaded {n_runs} valid runs:")
    for idx, rname in enumerate(run_names, start=1):
        print(f"   [{idx}] {rname}")

    # Determine reference channel
    first_run = runs[run_names[0]]
    mapping = first_run.sensor_mapping or {}
    sensor_names = {ch: mapping.get(f"channel_{ch}") for ch in range(1, 15)}

    ref_ch = args.ref_ch
    if args.ref_sensor:
        found = False
        for ch, sid in sensor_names.items():
            if str(sid).strip() == str(args.ref_sensor).strip():
                ref_ch = ch
                found = True
                break
        if not found:
            print(f"⚠️ Warning: Reference sensor ID '{args.ref_sensor}' not found in Set {set_str}. Falling back to Ch {ref_ch}.")

    ref_sensor_id = sensor_names.get(ref_ch, "Unknown")

    # Check if set uses dynamic raised references or fixed reference
    raised_ids = set_engine.sensors_raised_by_set.get(set_num, [])
    has_dynamic_refs = len(raised_ids) >= 2 and not getattr(args, 'fixed_ref', False)

    if args.fixed_ref and set_num in set_engine.sensors_raised_by_set:
        # Override to force fixed reference
        set_engine.sensors_raised_by_set[set_num] = []
        has_dynamic_refs = False

    if has_dynamic_refs:
        print(f"\n🔄 Set {set_str} has raised sensors: {raised_ids}. Using dynamic circular references.")
    else:
        print(f"\n🎯 Reference sensor: Channel {ref_ch} → ID '{ref_sensor_id}' (Fixed reference)")

    # Compute offsets & RMS matrix
    print("\n⏳ Computing offsets and RMS matrices...")
    set_engine.calculate_offsets_and_rms(selected_sets=[set_num])

    # Compute repeatability
    print(f"⏳ Computing repeatability across {n_runs} runs...")
    set_engine.offset_repeatability(
        selected_sets=[set_num],
        ref=ref_ch,
        save_dir=save_dir,
        write_csv=False,
        write_excel=False
    )

    stats = set_engine.global_stats.get(set_num, {})
    if not stats:
        print("❌ Error: No repeatability statistics could be calculated.")
        sys.exit(1)

    # Build summary results
    rows = []
    for idx in range(14):
        ch = idx + 1
        sid = sensor_names.get(ch, f"CH{ch}")
        ch_stat = stats.get(idx, {})

        run_means = ch_stat.get("run_means", [])
        run_stds = ch_stat.get("run_stds", [])

        mean_val = ch_stat.get("mean", np.nan)
        sigma_val = ch_stat.get("sigma", np.nan)

        if np.isnan(mean_val) and run_means:
            valid_means = [m for m in run_means if not np.isnan(m)]
            if valid_means:
                if all(abs(m) < 1e-9 for m in valid_means):
                    mean_val = 0.0
                    sigma_val = 0.0
                else:
                    mean_val = float(np.mean(valid_means))
                    sigma_val = float(np.std(valid_means, ddof=1)) if len(valid_means) > 1 else 0.0

        if not has_dynamic_refs and ch == ref_ch:
            mean_val = 0.0
            sigma_val = 0.0
            status = "REFERENCE"
        elif np.isnan(sigma_val) or (np.isnan(mean_val) and not run_means):
            status = "NO_DATA"
        elif abs(mean_val) < 1e-9 and sigma_val < 1e-9:
            status = "REFERENCE"
        elif sigma_val < 2.0:
            status = "OK (< 2 mK)"
        elif sigma_val < 5.0:
            status = "ACCEPTABLE"
        else:
            status = "HIGH_SIGMA"

        row = {
            "Channel": f"Ch {ch}",
            "Sensor_ID": sid,
            "Offset_mK": round(mean_val, 3) if not np.isnan(mean_val) else np.nan,
            "Sigma_mK": round(sigma_val, 3) if not np.isnan(sigma_val) else np.nan,
            "Status": status,
        }

        # Add individual run values
        for r_idx, r_mean in enumerate(run_means, start=1):
            row[f"Run_{r_idx}_mK"] = round(r_mean, 3) if not np.isnan(r_mean) else np.nan

        rows.append(row)

    df_results = pd.DataFrame(rows)

    # Print clean table
    print("\n" + "=" * 95)
    ref_desc = "Dynamic (Raised Sensors)" if has_dynamic_refs else f"Fixed (Ch {ref_ch} / {ref_sensor_id})"
    print(f"  CALIBRATION CONSTANTS & REPEATABILITY — SET {set_str} [Ref: {ref_desc}]")
    print("=" * 95)

    headers = ["Channel", "Sensor ID", "Offset (mK)", "Sigma (mK)", "Status"]
    for r_idx in range(1, n_runs + 1):
        headers.append(f"Run {r_idx}")

    format_str = "{:<8} {:<11} {:>12} {:>11} {:<15}" + " {:>10}" * n_runs
    print(format_str.format(*headers))
    print("-" * 95)

    for _, r in df_results.iterrows():
        run_vals = [f"{r[f'Run_{i}_mK']:.3f}" if not pd.isna(r[f'Run_{i}_mK']) else "-" for i in range(1, n_runs + 1)]
        offset_str = f"{r['Offset_mK']:.3f}" if not pd.isna(r['Offset_mK']) else "-"
        sigma_str = f"{r['Sigma_mK']:.3f}" if not pd.isna(r['Sigma_mK']) else "-"
        print(format_str.format(
            r["Channel"],
            str(r["Sensor_ID"]),
            offset_str,
            sigma_str,
            r["Status"],
            *run_vals
        ))

    print("-" * 95)

    # Save to CSV
    csv_out = os.path.join(save_dir, f"set_{set_str}_calibration_constants.csv")
    df_results.to_csv(csv_out, index=False)
    print(f"\n💾 Table saved to CSV: {csv_out}")

    plot_file = os.path.join(save_dir, f"offset_repeatability_set_{set_str}.png")
    if os.path.exists(plot_file):
        print(f"📊 Repeatability plot saved: {plot_file}")

    print("\n🎉 Done!")


if __name__ == "__main__":
    main()
