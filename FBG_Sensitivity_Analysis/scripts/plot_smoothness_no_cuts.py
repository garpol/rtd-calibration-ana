#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = "/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis/figures"
df = pd.read_csv(os.path.join(OUTPUT_DIR, "new_smoothness_method_results.csv"))

# Filter out extreme non-plateau transients (valve refilling or descent > 150 mK)
df = df[df["Spline_RMS_mK"] < 15.0].copy()
df = df[df["PTP_mK"] < 150.0].copy()

plt.rcParams.update({
    "font.size": 11,
    "font.family": "sans-serif",
    "axes.labelsize": 12,
    "axes.titlesize": 12.5,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "legend.fontsize": 9.5
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.2), dpi=300)

markers = {"PEEK-4": "o", "PEEK-1": "s"}
colors_peek4 = {"PEEK-4 R1 (09/06/26)": "#1f77b4", "PEEK-4 R2 (10/06/26)": "#ff7f0e", "PEEK-4 R3 (11/06/26)": "#2ca02c"}
colors_peek1 = {"PEEK-1 R1 (26/09/24)": "#9467bd", "PEEK-1 R2 (30/09/24)": "#d62728", "PEEK-1 R3 (01/10/24)": "#8c564b"}

for run_name, group in df.groupby("Run"):
    fiber = group["Fiber"].iloc[0]
    m = markers[fiber]
    c = colors_peek4.get(run_name, colors_peek1.get(run_name, "#333333"))
    label_str = run_name.replace("PEEK-4 ", "PEEK-4: ").replace("PEEK-1 ", "PEEK-1: ")
    
    # Left: Spline Residual RMS
    ax1.scatter(group["Spline_RMS_mK"], group["FBG_RMS_mK"], marker=m, color=c, s=80, 
                edgecolor='black', lw=0.8, alpha=0.9, label=label_str, zorder=3)
    # Right: Second Difference Roughness
    ax2.scatter(group["Sigma_Rough_mK"], group["FBG_RMS_mK"], marker=m, color=c, s=80, 
                edgecolor='black', lw=0.8, alpha=0.9, label=label_str, zorder=3)

# Target line 5.0 mK (discreet reference benchmark)
ax1.axhline(5.0, color='#d90429', linestyle='--', lw=1.8, label=r'Benchmark RMS $\leq 5.0$ mK', zorder=2)
ax2.axhline(5.0, color='#d90429', linestyle='--', lw=1.8, label=r'Benchmark RMS $\leq 5.0$ mK', zorder=2)

# NO CUTS! NO VERTICAL LINES! NO SHADED REGIONS! Pure continuous correlation.

# Compute correlation
r1 = df["Spline_RMS_mK"].corr(df["FBG_RMS_mK"])
r2 = df["Sigma_Rough_mK"].corr(df["FBG_RMS_mK"])

ax1.set_xlabel(r'RTD Non-Smoothness: Spline Residual RMS (mK)')
ax1.set_ylabel(r'FBG Tracking Residual RMS: $\mathrm{RMS}(T_{\mathrm{FBG}} - T_{\mathrm{RTD}})$ (mK)')
ax1.set_title(f'(a) FBG Tracking RMS vs. Spline Residual Dispersion (r = {r1:.2f})', fontweight='bold')
ax1.set_xlim(0, 4.0)
ax1.set_ylim(0, 16.5)
ax1.grid(True, linestyle=":", alpha=0.6)
ax1.legend(loc='upper left', framealpha=0.9, ncol=2)

ax2.set_xlabel(r'RTD High-Frequency Roughness: Discrete $\sigma_{\mathrm{rough}}$ (mK)')
ax2.set_ylabel(r'FBG Tracking Residual RMS: $\mathrm{RMS}(T_{\mathrm{FBG}} - T_{\mathrm{RTD}})$ (mK)')
ax2.set_title(f'(b) FBG Tracking RMS vs. Finite Difference Roughness (r = {r2:.2f})', fontweight='bold')
ax2.set_xlim(0, 1.25)
ax2.set_ylim(0, 16.5)
ax2.grid(True, linestyle=":", alpha=0.6)
ax2.legend(loc='upper left', framealpha=0.9, ncol=2)

plt.tight_layout()
png_out = os.path.join(OUTPUT_DIR, "fbg_rms_vs_smoothness_no_cuts.png")
pdf_out = os.path.join(OUTPUT_DIR, "fbg_rms_vs_smoothness_no_cuts.pdf")
plt.savefig(png_out, bbox_inches='tight')
plt.savefig(pdf_out, bbox_inches='tight')
plt.savefig("/afs/cern.ch/user/v/vgarciap/.gemini/antigravity-ide/brain/81cafc34-7bab-4d53-9c9d-8bd02d211614/fbg_rms_vs_smoothness_no_cuts.png", bbox_inches='tight')
print(f"Generated clean no-cut plot! r(Spline)={r1:.2f}, r(Roughness)={r2:.2f}", flush=True)
