#!/usr/bin/env python3
import os
import datetime
import numpy as np
import pandas as pd
import uproot
from scipy.interpolate import splrep, splev
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = "/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis/figures"

RUNS_CONFIG = [
    # PEEK-4
    {
        "fiber": "PEEK-4",
        "run_id": "PEEK-4 R1 (09/06/26)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260609.root",
        "date": (2026, 6, 9),
        "is_utc": True,
        "fbg_shift_s": 7200.0,
        "rtd_idx": 7,
        "sens": 17.765,
        "lag": 17.5,
        "plateaus": [
            ("P1_R1", "14:00", "14:11"),
            ("P2_R1", "14:22", "14:33"),
            ("P3_R1", "14:50", "15:01"),
            ("P4_R1", "15:12", "15:23"),
            ("P5_R1", "15:40", "15:51"),
            ("P6_R1", "16:08", "16:19"),
        ]
    },
    {
        "fiber": "PEEK-4",
        "run_id": "PEEK-4 R2 (10/06/26)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260610.root",
        "date": (2026, 6, 10),
        "is_utc": True,
        "fbg_shift_s": 7200.0,
        "rtd_idx": 7,
        "sens": 17.765,
        "lag": 17.5,
        "plateaus": [
            ("P1_R2", "14:03", "14:13"),
            ("P2_R2", "14:20", "14:30"),
            ("P3_R2", "14:45", "14:55"),
            ("P4_R2", "15:12", "15:23"),
            ("P5_R2", "15:38", "15:48"),
        ]
    },
    {
        "fiber": "PEEK-4",
        "run_id": "PEEK-4 R3 (11/06/26)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260611.root",
        "date": (2026, 6, 11),
        "is_utc": False, # Local CEST -> UTC is h-2
        "fbg_shift_s": 0.0,
        "rtd_idx": 7,
        "sens": 17.765,
        "lag": 17.5,
        "plateaus": [
            ("P1_R3", "13:49", "13:59"),
            ("P2_R3", "14:12", "14:22"),
            ("P3_R3", "14:40", "14:50"),
            ("P4_R3", "15:10", "15:20"),
            ("P5_R3", "15:40", "15:50"),
            ("P6_R3", "16:09", "16:19"),
            ("P7_R3", "16:52", "17:02"),
            ("P8_R3", "17:10", "17:20"),
        ]
    },
    # PEEK-1
    {
        "fiber": "PEEK-1",
        "run_id": "PEEK-1 R1 (26/09/24)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20240926.root",
        "date": (2024, 9, 26),
        "is_utc": True,
        "fbg_shift_s": 4.0 * 3600.0,
        "rtd_idx": 6,
        "sens": 19.98,
        "lag": 17.5,
        "plateaus": [
            ("P1_R1", "11:29", "11:34"),
            ("P2_R1", "12:08", "12:13"),
            ("P3_R1", "13:08", "13:13"),
            ("P4_R1", "13:33", "13:38"),
            ("P5_R1", "13:48", "13:53"),
            ("P6_R1", "14:05", "14:10"),
            ("P7_R1", "14:16", "14:21"),
            ("P8_R1", "14:34", "14:39"),
        ]
    },
    {
        "fiber": "PEEK-1",
        "run_id": "PEEK-1 R2 (30/09/24)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20240930.root",
        "date": (2024, 9, 30),
        "is_utc": True,
        "fbg_shift_s": 4.0 * 3600.0,
        "rtd_idx": 6,
        "sens": 19.98,
        "lag": 17.5,
        "plateaus": [
            ("P1_R2", "11:11", "11:16"),
            ("P2_R2", "12:56", "13:01"),
            ("P3_R2", "13:29", "13:34"),
            ("P4_R2", "14:05", "14:10"),
            ("P5_R2", "14:26", "14:31"),
            ("P6_R2", "14:45", "14:50"),
        ]
    },
    {
        "fiber": "PEEK-1",
        "run_id": "PEEK-1 R3 (01/10/24)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20241001.root",
        "date": (2024, 10, 1),
        "is_utc": True,
        "fbg_shift_s": 4.0 * 3600.0,
        "rtd_idx": 6,
        "sens": 19.98,
        "lag": 17.5,
        "plateaus": [
            ("P1_R3", "11:41", "11:46"),
            ("P2_R3", "12:28", "12:33"),
            ("P3_R3", "12:54", "12:59"),
        ]
    }
]

rows = []

for run in RUNS_CONFIG:
    print(f"Analyzing {run['run_id']}...", flush=True)
    with uproot.open(run["file"]) as f:
        peak_data = f["peak"].arrays(["t", "wav"], library="np")
        temp_data = f["temp"].arrays(["t", "temp"], library="np")

    t_temp = np.asarray(temp_data["t"], dtype=float).reshape(-1)
    t_peak = np.asarray(peak_data["t"][:, 0], dtype=float) + run["fbg_shift_s"]
    temp_ref = np.asarray(temp_data["temp"][:, run["rtd_idx"]], dtype=float)
    wav_s1 = (peak_data["wav"][:, 0, 0] * 1e9 + peak_data["wav"][:, 1, 0] * 1e9) / 2.0
    good = (wav_s1 > 1500) & np.isfinite(wav_s1)
    t_peak, wav_s1 = t_peak[good], wav_s1[good]

    dt_fbg = np.median(np.diff(t_peak))
    n_win = max(1, int(round(1.0 / dt_fbg)))  # 1.0 s rolling filter
    fbg_mK_all = (wav_s1 - np.mean(wav_s1)) * 1000.0 / (run["sens"] / 1000.0)
    y, m, d = run["date"]

    for name, t_start_str, t_end_str in run["plateaus"]:
        h0, m0 = map(int, t_start_str.split(":"))
        hf, mf = map(int, t_end_str.split(":"))
        if not run["is_utc"]:
            h0 -= 2
            hf -= 2
        t0 = (datetime.datetime(y, m, d, h0, m0) - datetime.datetime(1970, 1, 1)).total_seconds()
        tf = (datetime.datetime(y, m, d, hf, mf) - datetime.datetime(1970, 1, 1)).total_seconds()
        t0_act = t0 + 120.0

        mT = (t_temp >= t0_act) & (t_temp <= tf)
        tT = t_temp[mT]
        T_raw = temp_ref[mT]
        if len(tT) < 20:
            continue

        t_min = (tT - t0_act) / 60.0
        T_mK = (T_raw - np.mean(T_raw)) * 1000.0

        # FBG Tracking Residual RMS with 1.0 s filter
        mW = (t_peak >= t0 - 120.0) & (t_peak <= tf + 120.0)
        tW = t_peak[mW]
        fbg_sub = pd.Series(fbg_mK_all[mW]).rolling(n_win, center=True, min_periods=1).mean().values
        fbg_at_rtd = np.interp(tT, tW - run["lag"], fbg_sub)
        fbg_rel = fbg_at_rtd - np.mean(fbg_at_rtd)
        fbg_rms = np.sqrt(np.mean((fbg_rel - T_mK)**2))

        # --- SMOOTHNESS METHODS ---
        # 1. Cubic Spline with uniform interior knots every ~2.5 min
        n_knots = max(1, int(round((t_min[-1] - t_min[0]) / 2.5)))
        knots = np.linspace(t_min[1], t_min[-2], n_knots + 2)[1:-1]
        tck = splrep(t_min, T_mK, k=3, t=knots)
        spl_fit = splev(t_min, tck)
        res_spl = T_mK - spl_fit
        rms_spl = np.std(res_spl)
        chi2_spl = np.sum((res_spl / 1.5)**2) / (len(tT) - len(knots) - 4)

        # 2. Second Difference Noise Floor (model-free roughness)
        diff2 = np.diff(T_mK, n=2)
        sigma_rough = np.std(diff2) / np.sqrt(6)

        rows.append({
            "Fiber": run["fiber"],
            "Run": run["run_id"],
            "Plateau": f"{run['fiber']}_{name}",
            "T_mean_K": np.mean(T_raw),
            "PTP_mK": np.ptp(T_mK),
            "Duration_min": t_min[-1] - t_min[0],
            "Spline_RMS_mK": rms_spl,
            "Spline_Chi2": chi2_spl,
            "Sigma_Rough_mK": sigma_rough,
            "FBG_RMS_mK": fbg_rms
        })

df_new = pd.DataFrame(rows)
df_new.to_csv(os.path.join(OUTPUT_DIR, "new_smoothness_method_results.csv"), index=False)
print("Saved new smoothness CSV successfully!", flush=True)
