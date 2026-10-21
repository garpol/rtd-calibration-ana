#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = "/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis/figures"
df = pd.read_csv(os.path.join(OUTPUT_DIR, "new_smoothness_method_results.csv"))

# Filter strictly to PEEK-4 only, excluding the rapid cooldown transient descent PEEK-4_P7_R3
df = df[df["Fiber"] == "PEEK-4"].copy()
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

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.2), dpi=300)

run_colors = {
    "PEEK-4 R1 (09/06/26)": "#1f77b4",
    "PEEK-4 R2 (10/06/26)": "#ff7f0e",
    "PEEK-4 R3 (11/06/26)": "#2ca02c"
}

run_labels = {
    "PEEK-4 R1 (09/06/26)": "Run 1 (09/06/26)",
    "PEEK-4 R2 (10/06/26)": "Run 2 (10/06/26)",
    "PEEK-4 R3 (11/06/26)": "Run 3 (11/06/26)"
}

for run_name, group in df.groupby("Run"):
    c = run_colors.get(run_name, "#333333")
    lbl = run_labels.get(run_name, run_name)
    
    # Left: Spline Residual RMS
    ax1.scatter(group["Spline_RMS_mK"], group["FBG_RMS_mK"], marker='o', color=c, s=95, 
                edgecolor='black', lw=0.9, alpha=0.9, label=lbl, zorder=3)
    # Right: Second Difference Roughness
    ax2.scatter(group["Sigma_Rough_mK"], group["FBG_RMS_mK"], marker='o', color=c, s=95, 
                edgecolor='black', lw=0.9, alpha=0.9, label=lbl, zorder=3)

# Add plateau names next to points for clarity
for _, row in df.iterrows():
    p_name = row["Plateau"].replace("PEEK-4_", "")
    
    # Subplot 1
    ax1.annotate(p_name, (row["Spline_RMS_mK"], row["FBG_RMS_mK"]),
                 xytext=(4, 4), textcoords="offset points", fontsize=8.5, color='#1f2937')
    # Subplot 2
    ax2.annotate(p_name, (row["Sigma_Rough_mK"], row["FBG_RMS_mK"]),
                 xytext=(4, 4), textcoords="offset points", fontsize=8.5, color='#1f2937')

# Reference benchmark line 5.0 mK
ax1.axhline(5.0, color='#d90429', linestyle='--', lw=2.0, label=r'Benchmark RMS $\leq 5.0$ mK', zorder=2)
ax2.axhline(5.0, color='#d90429', linestyle='--', lw=2.0, label=r'Benchmark RMS $\leq 5.0$ mK', zorder=2)

r1 = df["Spline_RMS_mK"].corr(df["FBG_RMS_mK"])
r2 = df["Sigma_Rough_mK"].corr(df["FBG_RMS_mK"])

ax1.set_xlabel('RTD Non-Smoothness: Spline Residual RMS (mK)')
ax1.set_ylabel(r'FBG Tracking Residual RMS: $\mathrm{RMS}(T_{\mathrm{FBG}} - T_{\mathrm{RTD}})$ (mK)')
ax1.set_title(f'(a) PEEK-4: FBG RMS vs. Spline Residual Dispersion (r = {r1:.2f})', fontweight='bold')
ax1.set_xlim(0, 4.5)
ax1.set_ylim(0, 16.5)
ax1.grid(True, linestyle=":", alpha=0.6)
ax1.legend(loc='upper left', framealpha=0.9)

ax2.set_xlabel(r'RTD High-Frequency Noise: Discrete $\sigma_{\mathrm{rough}}$ (mK)')
ax2.set_ylabel(r'FBG Tracking Residual RMS: $\mathrm{RMS}(T_{\mathrm{FBG}} - T_{\mathrm{RTD}})$ (mK)')
ax2.set_title(f'(b) PEEK-4: FBG RMS vs. 2nd Difference Roughness (r = {r2:.2f})', fontweight='bold')
ax2.set_xlim(0, 1.25)
ax2.set_ylim(0, 16.5)
ax2.grid(True, linestyle=":", alpha=0.6)
ax2.legend(loc='upper left', framealpha=0.9)

plt.tight_layout()
png_out = os.path.join(OUTPUT_DIR, "peek4_smoothness_no_cuts.png")
pdf_out = os.path.join(OUTPUT_DIR, "peek4_smoothness_no_cuts.pdf")
plt.savefig(png_out, bbox_inches='tight')
plt.savefig(pdf_out, bbox_inches='tight')
plt.savefig("/afs/cern.ch/user/v/vgarciap/.gemini/antigravity-ide/brain/81cafc34-7bab-4d53-9c9d-8bd02d211614/peek4_smoothness_no_cuts.png", bbox_inches='tight')
print(f"Generated PEEK-4 only plot! r(Spline)={r1:.2f}, r(Roughness)={r2:.2f}", flush=True)
