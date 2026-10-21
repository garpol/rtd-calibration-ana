#!/usr/bin/env python3
import os
import datetime
import numpy as np
import pandas as pd
import uproot
from scipy.interpolate import UnivariateSpline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

f = uproot.open('/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260611.root')
temp_data = f['temp'].arrays(['t', 'temp'], library='np')
peak_data = f['peak'].arrays(['t', 'wav'], library='np')

t_temp = np.asarray(temp_data['t'], dtype=float).reshape(-1)
temp_ref = np.asarray(temp_data['temp'][:, 7], dtype=float)
t_peak = np.asarray(peak_data['t'][:, 0], dtype=float)
wav_s1 = (peak_data['wav'][:, 0, 0] * 1e9 + peak_data['wav'][:, 1, 0] * 1e9) / 2.0
good = (wav_s1 > 1500) & np.isfinite(wav_s1)
t_peak, wav_s1 = t_peak[good], wav_s1[good]

# 14:40 to 14:50 local = 12:40 to 12:50 UTC
t0 = (datetime.datetime(2026, 6, 11, 12, 40) - datetime.datetime(1970, 1, 1)).total_seconds()
tf = (datetime.datetime(2026, 6, 11, 12, 50) - datetime.datetime(1970, 1, 1)).total_seconds()
t0_act = t0 + 120.0

mT = (t_temp >= t0_act) & (t_temp <= tf)
tT = t_temp[mT]
T_raw = temp_ref[mT]
t_min = (tT - t0_act) / 60.0
T_mK = (T_raw - np.mean(T_raw)) * 1000.0

# FBG tracking
fbg_mK_all = (wav_s1 - np.mean(wav_s1)) * 1000.0 / (17.765 / 1000.0)
mW = (t_peak >= t0 - 120.0) & (t_peak <= tf + 120.0)
tW = t_peak[mW]
fbg_sub = pd.Series(fbg_mK_all[mW]).rolling(5, center=True, min_periods=1).mean().values
fbg_at_rtd = np.interp(tT, tW - 17.5, fbg_sub)
fbg_rel = fbg_at_rtd - np.mean(fbg_at_rtd)
res_fbg = fbg_rel - T_mK
fbg_rms = np.sqrt(np.mean(res_fbg**2))

# Poly 3 fit
p3 = np.poly1d(np.polyfit(t_min, T_mK, 3))
res_p3 = T_mK - p3(t_min)
rms_p3 = np.std(res_p3)
chi2_p3 = np.sum((res_p3 / 1.5)**2) / (len(t_min) - 4)

# Spline fit
spl = UnivariateSpline(t_min, T_mK, s=len(t_min)*1.8**2)
res_spl = T_mK - spl(t_min)
rms_spl = np.std(res_spl)

plt.rcParams.update({
    "font.size": 11,
    "font.family": "sans-serif",
    "axes.labelsize": 12,
    "axes.titlesize": 12.5,
    "legend.fontsize": 10.0
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

# Panel 1: RTD and fits
ax1.plot(t_min, T_mK, 'o', color='#2b2d42', markersize=3.5, alpha=0.7, label='RTD Reference Data')
ax1.plot(t_min, p3(t_min), color='#d90429', lw=2.2, linestyle='--', 
         label=f'Poly-3 Fit (RMS = {rms_p3:.1f} mK, $\\chi^2/\\mathrm{{ndf}} = {chi2_p3:.1f}$)')
ax1.plot(t_min, spl(t_min), color='#2a9d8f', lw=2.5, 
         label=f'Smoothing Spline (RMS = {rms_spl:.2f} mK)')
ax1.set_xlabel('Elapsed Time (min)')
ax1.set_ylabel(r'$\Delta T$ from mean (mK)')
ax1.set_title(r'(a) RTD Fits in Plateau P3_R3 (Total $\Delta T \approx 92$ mK)', fontweight='bold')
ax1.grid(True, linestyle=":", alpha=0.6)
ax1.legend(loc='lower right', framealpha=0.9)

# Panel 2: FBG tracking
ax2.plot(t_min, T_mK, color='#2b2d42', lw=2.0, label='RTD Reference (Smooth drift)')
ax2.plot(t_min, fbg_rel, color='#e76f51', lw=1.6, linestyle='--', label=f'PEEK-4 FBG (RMS error = {fbg_rms:.2f} mK)')
ax2.set_xlabel('Elapsed Time (min)')
ax2.set_ylabel(r'$\Delta T$ from mean (mK)')
ax2.set_title(r'(b) Real-Time FBG Tracking in P3_R3', fontweight='bold')
ax2.grid(True, linestyle=":", alpha=0.6)
ax2.legend(loc='lower right', framealpha=0.9)

# Scale arrow 5 mK
ax2.annotate('', xy=(1.0, 20), xytext=(1.0, 25),
             arrowprops=dict(arrowstyle='<->', color='#7209b7', lw=2.0))
ax2.text(1.2, 22.5, '5 mK Resolution Target', color='#7209b7', fontweight='bold', va='center')

plt.tight_layout()
out_png = '/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis/figures/plateau_p3_r3_spline_explanation.png'
plt.savefig(out_png, bbox_inches='tight')
plt.savefig('/afs/cern.ch/user/v/vgarciap/.gemini/antigravity-ide/brain/81cafc34-7bab-4d53-9c9d-8bd02d211614/plateau_p3_r3_spline_explanation.png', bbox_inches='tight')
print('Generated P3_R3 explanation plot successfully!')
