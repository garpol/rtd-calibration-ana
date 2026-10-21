#!/usr/bin/env python3
"""
Generate clean Figure 4 for the paper without histogram:
- Row 1: Real-time tracking for 3 representative plateaus at different temperatures
- Row 2: Direct Tracking Residual RMS bar chart across all 9 selected plateaus (Runs 1, 2, 3)
"""
import os
import datetime
import numpy as np
import pandas as pd
import uproot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = "/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_R1 = "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260609.root"
TIME_SHIFT = 2 * 3600.0
SENSITIVITY = 17.765  # pm/K (Sensor 1)
LAG = 17.5           # s
FILTER_S = 1.0       # s

print("Loading ROOT file for PEEK-4 Run 1...", flush=True)
with uproot.open(FILE_R1) as f:
    peak_data = f["peak"].arrays(["t", "wav"], library="np")
    temp_data = f["temp"].arrays(["t", "temp"], library="np")

t_temp = np.asarray(temp_data["t"], dtype=float).reshape(-1)
t_peak = np.asarray(peak_data["t"][:, 0], dtype=float) + TIME_SHIFT
temp_ref = np.asarray(temp_data["temp"][:, 7], dtype=float)  # RTD-8
wav_s1 = (peak_data["wav"][:, 0, 0] * 1e9 + peak_data["wav"][:, 1, 0] * 1e9) / 2.0

good = (wav_s1 > 1500) & np.isfinite(wav_s1)
t_peak, wav_s1 = t_peak[good], wav_s1[good]

dt_fbg = np.median(np.diff(t_peak))
n_win = max(1, int(round(FILTER_S / dt_fbg)))
fbg_mK_all = (wav_s1 - np.mean(wav_s1)) * 1000.0 / (SENSITIVITY / 1000.0)

def epoch(h, m):
    return (datetime.datetime(2026, 6, 9, h, m) - datetime.datetime(1970, 1, 1)).total_seconds()

rep_plateaus = [
    {"name": "Plateau 1 ($T \\approx 92.0$ K)", "t0": epoch(14, 0), "tf": epoch(14, 11)},
    {"name": "Plateau 3 ($T \\approx 89.7$ K)", "t0": epoch(14, 50), "tf": epoch(15, 1)},
    {"name": "Plateau 4 ($T \\approx 86.8$ K)", "t0": epoch(15, 12), "tf": epoch(15, 23)}
]

extracted = []
for p in rep_plateaus:
    t0_active = p["t0"] + 120.0
    tf = p["tf"]
    mT = (t_temp >= t0_active) & (t_temp <= tf)
    tT = t_temp[mT]
    T_raw = temp_ref[mT]
    
    t_min = (tT - t0_active) / 60.0
    T_rel = (T_raw - np.mean(T_raw)) * 1000.0
    
    mW = (t_peak >= p["t0"] - 120.0) & (t_peak <= tf + 120.0)
    tW = t_peak[mW]
    fbg_sub = pd.Series(fbg_mK_all[mW]).rolling(n_win, center=True, min_periods=1).mean().values
    
    fbg_at_rtd = np.interp(tT, tW - LAG, fbg_sub)
    fbg_rel = fbg_at_rtd - np.mean(fbg_at_rtd)
    
    res = fbg_rel - T_rel
    extracted.append({
        "name": p["name"],
        "t_min": t_min,
        "T_rel": T_rel,
        "fbg_rel": fbg_rel,
        "rms": np.sqrt(np.mean(res**2))
    })

# Load stats from all qualified plateaus of PEEK-4
df_peek4 = pd.read_csv(os.path.join(OUTPUT_DIR, "peek4_all_runs_plateaus.csv"))
pass_peek4 = df_peek4[df_peek4["Chi2_ndf_P3"] <= 1.5].copy()
pass_peek4 = pass_peek4.sort_values("T_mean_K", ascending=False)

plt.rcParams.update({
    "font.size": 10.5,
    "font.family": "sans-serif",
    "axes.labelsize": 11,
    "axes.titlesize": 11.5,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 9.5
})

# 2-Row Figure Layout
fig = plt.figure(figsize=(15, 8.2), dpi=300)
gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1.0], hspace=0.35, wspace=0.25)

# Row 1: Real-time tracking (a1, a2, a3)
ax_t1 = fig.add_subplot(gs[0, 0])
ax_t2 = fig.add_subplot(gs[0, 1])
ax_t3 = fig.add_subplot(gs[0, 2])
track_axes = [ax_t1, ax_t2, ax_t3]
letters = ["(a1)", "(a2)", "(a3)"]

for idx, (ax, p_data) in enumerate(zip(track_axes, extracted)):
    ax.plot(p_data["t_min"], p_data["T_rel"], color="#2b2d42", lw=1.8, label="RTD Reference (Capsule)", zorder=2)
    ax.plot(p_data["t_min"], p_data["fbg_rel"], color="#d90429", lw=1.4, alpha=0.9, ls="--",
            label="PEEK-4 FBG (1 s filter)", zorder=3)
    
    # Scale arrow 20 mK
    y_min, y_max = ax.get_ylim()
    arrow_x = p_data["t_min"][-1] - 0.8
    arrow_y = y_min + 0.15 * (y_max - y_min)
    ax.annotate('', xy=(arrow_x, arrow_y), xytext=(arrow_x, arrow_y + 20.0),
                arrowprops=dict(arrowstyle='<->', color='#7209b7', lw=2.0))
    ax.text(arrow_x - 0.1, arrow_y + 10.0, "20 mK", color='#7209b7', fontweight='bold',
            fontsize=8.5, ha='right', va='center')
    
    ax.set_title(f"{letters[idx]} {p_data['name']}\nTracking RMS = {p_data['rms']:.2f} mK", fontweight='bold')
    ax.set_xlabel("Elapsed Time (min)")
    ax.set_ylabel("$\\Delta T$ (mK)")
    ax.grid(True, linestyle=":", alpha=0.6)
    if idx == 0:
        ax.legend(loc="upper right", framealpha=0.9)

# Row 2: Full-width Bar chart (b) across all 3 columns
ax_stat = fig.add_subplot(gs[1, :])

run_colors = {
    "Run 1 (09/06)": "#1f77b4",
    "Run 2 (10/06)": "#ff7f0e",
    "Run 3 (11/06)": "#2ca02c"
}

x_pos = np.arange(len(pass_peek4))
bar_colors = [run_colors[r] for r in pass_peek4["Run"]]

bars = ax_stat.bar(x_pos, pass_peek4["FBG_RMS_mK"], width=0.50, color=bar_colors, alpha=0.85, edgecolor='black', lw=1.0)

for bar in bars:
    yval = bar.get_height()
    ax_stat.text(bar.get_x() + bar.get_width()/2.0, yval + 0.15, f"{yval:.2f}", ha='center', va='bottom', fontsize=9.5, fontweight='bold')

mean_rms = pass_peek4["FBG_RMS_mK"].mean()
std_rms = pass_peek4["FBG_RMS_mK"].std()

ax_stat.axhline(mean_rms, color='#023047', linestyle='--', lw=2.0, 
                label=f'Ensemble Mean: $\\langle \\mathrm{{RMS}} \\rangle = {mean_rms:.2f} \\pm {std_rms:.2f}$ mK')

ax_stat.axhline(20.0 / 3.0, color='#d90429', linestyle='-', lw=2.2, label='Target Requirement: RMS $< 6.67$ mK ($3\\sigma < 20$ mK)')

tick_labels = [f"{row['Plateau'].replace('PEEK-4_', '')}\n({row['T_mean_K']:.1f} K)" for _, row in pass_peek4.iterrows()]
ax_stat.set_xticks(x_pos)
ax_stat.set_xticklabels(tick_labels, fontsize=10)

ax_stat.set_title("(b) Blind Metrological Validation: Tracking Residual RMS Across All Selected Plateaus (PEEK-4, Runs 1–3)", fontweight='bold')
ax_stat.set_xlabel("Stationary Plateau (Ranked by Temperature)")
ax_stat.set_ylabel("Tracking Residual RMS (mK)")
ax_stat.set_ylim(0, 8.5)
ax_stat.grid(True, linestyle=":", alpha=0.6, axis='y')

from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=run_colors["Run 1 (09/06)"], edgecolor='k', label='Run 1 (09/06)'),
    Patch(facecolor=run_colors["Run 2 (10/06)"], edgecolor='k', label='Run 2 (10/06)'),
    Patch(facecolor=run_colors["Run 3 (11/06)"], edgecolor='k', label='Run 3 (11/06)'),
    plt.Line2D([0], [0], color='#023047', lw=2.0, linestyle='--', label=f'Mean: $\\langle \\mathrm{{RMS}} \\rangle = {mean_rms:.2f}$ mK'),
    plt.Line2D([0], [0], color='#d90429', lw=2.2, linestyle='-', label='Limit: RMS $< 6.67$ mK ($3\\sigma < 20$ mK)')
]
ax_stat.legend(handles=legend_elements, loc='upper right', framealpha=0.9, fontsize=9.5, ncol=2)

out_png = os.path.join(OUTPUT_DIR, "fig4_comprehensive_resolution.png")
out_pdf = os.path.join(OUTPUT_DIR, "fig4_comprehensive_resolution.pdf")

plt.savefig(out_png, dpi=300, bbox_inches='tight')
plt.savefig(out_pdf, dpi=300, bbox_inches='tight')
print(f"Saved PNG to: {out_png}")
print(f"Saved PDF to: {out_pdf}")
