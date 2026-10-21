#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = "/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis/figures"
df = pd.read_csv(os.path.join(OUTPUT_DIR, "new_smoothness_method_results.csv"))

# Filter strictly to PEEK-1 only
df = df[df["Fiber"] == "PEEK-1"].copy()
df = df[df["Spline_RMS_mK"] < 15.0].copy()
df = df[df["PTP_mK"] < 150.0].copy()

plt.rcParams.update({
    "font.size": 11,
    "font.family": "sans-serif",
    "axes.labelsize": 12,
    "axes.titlesize": 12.5,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "legend.fontsize": 10.0
})

fig, ax1 = plt.subplots(1, 1, figsize=(8.5, 6.2), dpi=300)

run_colors = {
    "PEEK-1 R1 (26/09/24)": "#9467bd",
    "PEEK-1 R2 (30/09/24)": "#d62728",
    "PEEK-1 R3 (01/10/24)": "#8c564b"
}

run_labels = {
    "PEEK-1 R1 (26/09/24)": "Run 1 (26/09/24)",
    "PEEK-1 R2 (30/09/24)": "Run 2 (30/09/24)",
    "PEEK-1 R3 (01/10/24)": "Run 3 (01/10/24)"
}

for run_name, group in df.groupby("Run"):
    c = run_colors.get(run_name, "#333333")
    lbl = run_labels.get(run_name, run_name)
    ax1.scatter(group["Spline_RMS_mK"], group["FBG_RMS_mK"], marker='s', color=c, s=100, 
                edgecolor='black', lw=0.9, alpha=0.9, label=lbl, zorder=3)

# Add plateau names next to points for clarity
for _, row in df.iterrows():
    p_name = row["Plateau"].replace("PEEK-1_", "")
    ax1.annotate(p_name, (row["Spline_RMS_mK"], row["FBG_RMS_mK"]),
                 xytext=(5, 4), textcoords="offset points", fontsize=8.5, color='#1f2937')

# Reference benchmark line 5.0 mK
ax1.axhline(5.0, color='#d90429', linestyle='--', lw=2.0, label=r'Benchmark RMS $\leq 5.0$ mK', zorder=2)
ax1.axvline(1.5, color='#023047', linestyle=':', lw=1.8, label=r'Blind Cut RTD Spline $\leq 1.5$ mK', zorder=2)

r1 = df["Spline_RMS_mK"].corr(df["FBG_RMS_mK"])

ax1.set_xlabel('RTD Non-Smoothness: Spline Residual RMS (mK)', fontweight='bold')
ax1.set_ylabel(r'FBG Tracking Residual RMS: $\mathrm{RMS}(T_{\mathrm{FBG}} - T_{\mathrm{RTD}})$ (mK)', fontweight='bold')
ax1.set_title(f'PEEK-1 Fiber: FBG Tracking RMS vs. RTD Spline Smoothness (r = {r1:.2f})', fontweight='bold', pad=12)
ax1.set_xlim(0, 4.0)
ax1.set_ylim(0, 16.5)
ax1.grid(True, linestyle=":", alpha=0.6)
ax1.legend(loc='upper left', framealpha=0.9)

plt.tight_layout()
png_out = os.path.join(OUTPUT_DIR, "peek1_smoothness_no_cuts.png")
pdf_out = os.path.join(OUTPUT_DIR, "peek1_smoothness_no_cuts.pdf")
plt.savefig(png_out, bbox_inches='tight')
plt.savefig(pdf_out, bbox_inches='tight')
plt.savefig("/afs/cern.ch/user/v/vgarciap/.gemini/antigravity-ide/brain/81cafc34-7bab-4d53-9c9d-8bd02d211614/peek1_smoothness_no_cuts.png", bbox_inches='tight')
print(f"Generated PEEK-1 only plot! r(Spline)={r1:.2f}", flush=True)
