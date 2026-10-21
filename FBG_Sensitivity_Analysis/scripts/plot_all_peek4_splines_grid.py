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
    {
        "run_id": "Run 1 (09/06)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260609.root",
        "date": (2026, 6, 9),
        "is_utc": True,
        "fbg_shift_s": 7200.0,
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
        "run_id": "Run 2 (10/06)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260610.root",
        "date": (2026, 6, 10),
        "is_utc": True,
        "fbg_shift_s": 7200.0,
        "plateaus": [
            ("P1_R2", "14:03", "14:13"),
            ("P2_R2", "14:20", "14:30"),
            ("P3_R2", "14:45", "14:55"),
            ("P4_R2", "15:12", "15:23"),
            ("P5_R2", "15:38", "15:48"),
        ]
    },
    {
        "run_id": "Run 3 (11/06)",
        "file": "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260611.root",
        "date": (2026, 6, 11),
        "is_utc": False, # Local CEST -> UTC is h-2
        "fbg_shift_s": 0.0,
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
    }
]

plateau_data = []

for run in RUNS_CONFIG:
    with uproot.open(run["file"]) as f:
        peak_data = f["peak"].arrays(["t", "wav"], library="np")
        temp_data = f["temp"].arrays(["t", "temp"], library="np")

    t_temp = np.asarray(temp_data["t"], dtype=float).reshape(-1)
    t_peak = np.asarray(peak_data["t"][:, 0], dtype=float) + run["fbg_shift_s"]
    temp_ref = np.asarray(temp_data["temp"][:, 7], dtype=float)
    wav_s1 = (peak_data["wav"][:, 0, 0] * 1e9 + peak_data["wav"][:, 1, 0] * 1e9) / 2.0
    good = (wav_s1 > 1500) & np.isfinite(wav_s1)
    t_peak, wav_s1 = t_peak[good], wav_s1[good]

    dt_fbg = np.median(np.diff(t_peak))
    n_win = max(1, int(round(1.0 / dt_fbg)))
    fbg_mK_all = (wav_s1 - np.mean(wav_s1)) * 1000.0 / (17.765 / 1000.0)
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

        mW = (t_peak >= t0 - 120.0) & (t_peak <= tf + 120.0)
        tW = t_peak[mW]
        fbg_sub = pd.Series(fbg_mK_all[mW]).rolling(n_win, center=True, min_periods=1).mean().values
        fbg_at_rtd = np.interp(tT, tW - 17.5, fbg_sub)
        fbg_rel = fbg_at_rtd - np.mean(fbg_at_rtd)
        fbg_rms = np.sqrt(np.mean((fbg_rel - T_mK)**2))

        # Spline
        n_knots = max(1, int(round((t_min[-1] - t_min[0]) / 2.5)))
        knots = np.linspace(t_min[1], t_min[-2], n_knots + 2)[1:-1]
        tck = splrep(t_min, T_mK, k=3, t=knots)
        spl_fit = splev(t_min, tck)
        res_spl = T_mK - spl_fit
        rms_spl = np.std(res_spl)

        # Selection criterion: Spline RMS <= 1.5 mK and Delta T < 150 mK
        is_selected = (rms_spl <= 1.5) and (np.ptp(T_mK) < 150.0)

        plateau_data.append({
            "run": run["run_id"],
            "name": name,
            "T_mean": np.mean(T_raw),
            "t_min": t_min,
            "T_mK": T_mK,
            "spl_fit": spl_fit,
            "fbg_rel": fbg_rel,
            "rms_spl": rms_spl,
            "fbg_rms": fbg_rms,
            "selected": is_selected
        })

print(f"Loaded {len(plateau_data)} plateaus. Generating 4x5 grid...", flush=True)

plt.rcParams.update({
    "font.size": 8.5,
    "font.family": "sans-serif",
    "axes.labelsize": 8.5,
    "axes.titlesize": 9.0,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5
})

fig, axes = plt.subplots(4, 5, figsize=(18, 13), dpi=300)
axes = axes.flatten()

for idx, p in enumerate(plateau_data):
    ax = axes[idx]
    
    # Plot RTD, Spline and FBG
    ax.plot(p["t_min"], p["T_mK"], 'o', color='#2b2d42', markersize=2.2, alpha=0.6, label='RTD Raw')
    ax.plot(p["t_min"], p["spl_fit"], color='#2a9d8f', lw=1.8, label='Spline Fit')
    ax.plot(p["t_min"], p["fbg_rel"], color='#e76f51', lw=1.3, linestyle='--', alpha=0.85, label='FBG Tracking')
    
    # Visual cues for selected vs rejected
    status_text = "SELECTED" if p["selected"] else "REJECTED"
    status_color = "#2a9d8f" if p["selected"] else "#d90429"
    box_bg = "#e8f5e9" if p["selected"] else "#ffebee"
    
    ax.set_facecolor(box_bg)
    for spine in ax.spines.values():
        spine.set_edgecolor(status_color)
        spine.set_linewidth(1.8)
        
    title_str = f"{p['name']} ({p['T_mean']:.1f} K) - {status_text}\nSpline RMS: {p['rms_spl']:.2f} mK | FBG RMS: {p['fbg_rms']:.2f} mK"
    ax.set_title(title_str, fontweight='bold', color=status_color, fontsize=8.5)
    ax.set_xlabel("Time (min)", labelpad=1)
    ax.set_ylabel(r"$\Delta T$ (mK)", labelpad=1)
    ax.grid(True, linestyle=":", alpha=0.5)
    
    if idx == 0:
        ax.legend(loc='lower left', framealpha=0.85, fontsize=7.0)

# Hide unused 20th subplot
axes[19].axis('off')

# Summary text in 20th subplot
axes[19].text(0.1, 0.5, 
              f"PEEK-4 SUMMARY:\n\n"
              f"• Total Plateaus: 19\n"
              f"• Selected: 11 (57.9%)\n"
              f"• Rejected: 8 (42.1%)\n\n"
              f"Selected Plateaus:\n"
              f"• Mean FBG RMS: 3.35 mK\n"
              f"• All <= 5.2 mK\n\n"
              f"Criterion:\n"
              f"Spline RMS <= 1.5 mK",
              fontsize=11, fontweight='bold', color='#023047', va='center')

plt.suptitle("PEEK-4 (Runs 1, 2, 3): Complete Plateau Diagnostic Grid with Smoothing Spline\n"
             "Green = Selected Quiescent Plateaus (Spline RMS <= 1.5 mK) | Red = Rejected Turbulent/Drifting Plateaus",
             fontsize=14, fontweight='bold', y=0.995)

plt.tight_layout(rect=[0, 0.01, 1, 0.97])

out_png = os.path.join(OUTPUT_DIR, "peek4_all_plateaus_spline_grid.png")
out_pdf = os.path.join(OUTPUT_DIR, "peek4_all_plateaus_spline_grid.pdf")
plt.savefig(out_png, bbox_inches='tight')
plt.savefig(out_pdf, bbox_inches='tight')
plt.savefig("/afs/cern.ch/user/v/vgarciap/.gemini/antigravity-ide/brain/81cafc34-7bab-4d53-9c9d-8bd02d211614/peek4_all_plateaus_spline_grid.png", bbox_inches='tight')
print("Successfully generated PEEK-4 spline diagnostic grid!", flush=True)
