#!/usr/bin/env python3
import os
import datetime
import uproot
import numpy as np
import pandas as pd
from scipy.interpolate import splrep, splev
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = '/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis/figures'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load Run 3 (Plateau P3_R3: 14:40 - 14:50 local CEST = 12:40 - 12:50 UTC)
f = uproot.open('/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260611.root')
p = f['peak'].arrays(['t', 'wav'], library='np')
temp = f['temp'].arrays(['t', 'temp'], library='np')

t_fbg = p['t'][:, 0]
w1 = (p['wav'][:, 0, 0] + p['wav'][:, 1, 0]) * 1e9 / 2.0
w2 = (p['wav'][:, 0, 1] + p['wav'][:, 1, 1]) * 1e9 / 2.0
good = (w1 > 1500) & (w2 > 1500) & np.isfinite(w1) & np.isfinite(w2)
t_fbg, w1, w2 = t_fbg[good], w1[good], w2[good]

t_rtd = np.asarray(temp['t'], dtype=float).reshape(-1)
T_rtd = np.asarray(temp['temp'][:, 7], dtype=float) # RTD-8

t0 = (datetime.datetime(2026, 6, 11, 12, 40) - datetime.datetime(1970, 1, 1)).total_seconds()
tf = (datetime.datetime(2026, 6, 11, 12, 50) - datetime.datetime(1970, 1, 1)).total_seconds()

m_f = (t_fbg >= t0) & (t_fbg <= tf)
t_p = (t_fbg[m_f] - t0) / 60.0 # min
w1_p = w1[m_f]
w2_p = w2[m_f]

m_r = (t_rtd >= t0) & (t_rtd <= tf)
t_r = (t_rtd[m_r] - t0) / 60.0
T_r = T_rtd[m_r]

# 1.0 s rolling averages
dt = np.median(np.diff(t_p)) * 60.0 # s
n_win = max(1, int(round(1.0 / dt)))

w1_s = pd.Series(w1_p).rolling(n_win, center=True).mean().values
w2_s = pd.Series(w2_p).rolling(n_win, center=True).mean().values

S1 = 17.765 # pm/K
S2 = 19.380 # pm/K

# Temperatures relative to mean (mK)
T1_mK = (w1_s - np.nanmean(w1_s)) * 1000.0 / (S1 / 1000.0)
T2_mK = (w2_s - np.nanmean(w2_s)) * 1000.0 / (S2 / 1000.0)
Tr_mK = (T_r - np.mean(T_r)) * 1000.0

# Differential wavelength delta lambda (pm)
d_lambda_pm = (w2_p - w1_p) * 1000.0
d_lambda_filt = pd.Series(d_lambda_pm).rolling(n_win, center=True).mean().values
d_lambda_rel = d_lambda_filt - np.nanmean(d_lambda_filt)

# Fit smoothing spline to delta lambda to capture micro-trend (due to delta S * delta T)
valid = np.isfinite(d_lambda_rel)
tp_v = t_p[valid]
dl_v = d_lambda_rel[valid]

# Downsample for robust spline knot placement
step = max(1, len(tp_v) // 600)
tp_sub = tp_v[::step]
dl_sub = dl_v[::step]
spl_dl = splrep(tp_sub, dl_sub, s=len(tp_sub) * 0.05)
spl_dl_vals = splev(t_p, spl_dl)

# Spline residual of delta lambda (pure high-frequency optical noise)
dl_spl_resid = d_lambda_rel - spl_dl_vals
rms_spl_dl = np.nanstd(dl_spl_resid)

# Overall RMS of delta lambda and differential temperature
rms_dlam = np.nanstd(dl_v)
dT_mK = T2_mK - T1_mK
rms_dT = np.nanstd(dT_mK[valid])

# Configure ultra-clean typography and aesthetics
plt.rcParams.update({
    'font.size': 10.5,
    'font.family': 'sans-serif',
    'axes.labelsize': 11,
    'axes.titlesize': 11.5,
    'xtick.labelsize': 9.5,
    'ytick.labelsize': 9.5,
    'legend.fontsize': 9.0
})

fig = plt.figure(figsize=(14, 8.5), dpi=300)
gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], hspace=0.38, wspace=0.25)

# Panel (a): Top spanning both columns - Absolute tracking of both FBGs and RTD
ax_a = fig.add_subplot(gs[0, :])
ax_a.plot(t_r, Tr_mK, 'o', color='#2b2d42', markersize=3.5, alpha=0.45, label='Reference RTD-8 (smooth bath drift)')
ax_a.plot(t_p, T1_mK, color='#1f77b4', lw=1.8, label=r'PEEK-4 Sensor 1 ($\lambda_1 \approx 1532.4$ nm, $S_1 = 17.77$ pm/K)')
ax_a.plot(t_p, T2_mK, color='#ff7f0e', lw=1.8, linestyle='--', label=r'PEEK-4 Sensor 2 ($\lambda_2 \approx 1534.8$ nm, $S_2 = 19.38$ pm/K)')
ax_a.set_xlabel('Elapsed Time in Plateau (min)', labelpad=6)
ax_a.set_ylabel(r'$\Delta T$ from plateau mean (mK)', labelpad=6)
ax_a.set_title(r'(a) Simultaneous Thermal Tracking in PEEK-4 Dual-Sensor Array (Plateau P3_R3, Total Drift $\approx 90$ mK)',
               fontweight='bold', pad=10)
ax_a.grid(True, linestyle=':', alpha=0.6)
ax_a.legend(loc='lower right', framealpha=0.92)

# Panel (b): Bottom Left - Differential wavelength delta lambda + Spline fit
ax_b = fig.add_subplot(gs[1, 0])
ax_b.plot(t_p, d_lambda_rel, color='#2a9d8f', lw=1.2, alpha=0.75, label=rf'Raw $\Delta\lambda = \lambda_2 - \lambda_1$ ($\mathrm{{RMS}} = {rms_dlam:.2f}$ pm)')
ax_b.plot(t_p, spl_dl_vals, color='#e76f51', lw=2.0, linestyle='-', label=rf'Spline fit of micro-drift ($\Delta S \cdot \Delta T$)')
ax_b.axhline(0, color='black', lw=0.8, ls=':')
ax_b.set_xlabel('Elapsed Time in Plateau (min)', labelpad=6)
ax_b.set_ylabel(r'$\Delta\lambda - \langle\Delta\lambda\rangle$ (pm)', labelpad=6)
ax_b.set_title(r'(b) Common-Mode Bath Drift Cancellation ($\Delta\lambda = \lambda_2 - \lambda_1$)',
               fontweight='bold', pad=10)
ax_b.set_ylim(-0.6, 0.6)
ax_b.grid(True, linestyle=':', alpha=0.6)
ax_b.legend(loc='upper right', framealpha=0.92)

# Panel (c): Bottom Right - Residual of delta lambda from Spline & equivalent temperature
ax_c = fig.add_subplot(gs[1, 1])
ax_c.plot(t_p, dl_spl_resid, color='#8338ec', lw=1.2, label=rf'Residual optical noise ($\mathrm{{RMS}} = {rms_spl_dl:.2f}$ pm)')
ax_c.axhline(0, color='black', lw=0.8, ls=':')
ax_c.axhline(+rms_spl_dl, color='#d90429', ls='--', lw=1.2, label=rf'$\pm 1\sigma = \pm {rms_spl_dl:.2f}\ \mathrm{{pm}}\ (\equiv \pm {rms_spl_dl/0.018:.1f}\ \mathrm{{mK}})$')
ax_c.axhline(-rms_spl_dl, color='#d90429', ls='--', lw=1.2)
ax_c.set_xlabel('Elapsed Time in Plateau (min)', labelpad=6)
ax_c.set_ylabel(r'$\Delta\lambda - \mathrm{Spline}(\Delta\lambda)$ (pm)', labelpad=6)
ax_c.set_title(r'(c) Intrinsic Optical Interrogation Noise (Independent of RTD)',
               fontweight='bold', pad=10)
ax_c.set_ylim(-0.45, 0.45)
ax_c.grid(True, linestyle=':', alpha=0.6)
ax_c.legend(loc='upper right', framealpha=0.92)

png_out = os.path.join(OUTPUT_DIR, 'peek4_two_sensors_delta_lambda.png')
pdf_out = os.path.join(OUTPUT_DIR, 'peek4_two_sensors_delta_lambda.pdf')
plt.savefig(png_out, bbox_inches='tight')
plt.savefig(pdf_out, bbox_inches='tight')
plt.savefig('/afs/cern.ch/user/v/vgarciap/.gemini/antigravity-ide/brain/81cafc34-7bab-4d53-9c9d-8bd02d211614/peek4_two_sensors_delta_lambda.png', bbox_inches='tight')
print(f'Done! RMS raw = {rms_dlam:.2f} pm | Spline residual RMS = {rms_spl_dl:.2f} pm ({rms_spl_dl/0.018:.2f} mK)', flush=True)
