import uproot
import numpy as np
import pandas as pd
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import norm

FILEPATH = "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260609.root"
TIME_SHIFT = datetime.timedelta(hours=2)

with uproot.open(FILEPATH) as f:
    peak_data = f["peak"].arrays(["t", "wav"], library="np")
    temp_data = f["temp"].arrays(["t", "temp"], library="np")

t_temp_dt = np.array([datetime.datetime.utcfromtimestamp(t) for t in temp_data["t"].reshape(-1)])
t_peak_dt = np.array([datetime.datetime.utcfromtimestamp(t) + TIME_SHIFT for t in peak_data["t"][:, 0]])
temp_ref = temp_data["temp"][:, 7] # RTD 8
wav_mean = (peak_data["wav"][:, 0, 0] * 1e9 + peak_data["wav"][:, 1, 0] * 1e9) / 2.0

# PLATEAU 3: 14:51 a 15:00
t0 = datetime.datetime(2026, 6, 9, 14, 51, 30)
tfin = datetime.datetime(2026, 6, 9, 15, 0, 0)
SENSITIVITY = 17.76 # pm/K
LAG_SECONDS = 0.0 # Probar con 0.0 o -5.0 s

mT = (t_temp_dt >= t0) & (t_temp_dt <= tfin)
mW = (t_peak_dt >= t0) & (t_peak_dt <= tfin) & (wav_mean > 1500)

t_T = t_temp_dt[mT]
T_vals = temp_ref[mT]
t_W = t_peak_dt[mW]
W_vals = wav_mean[mW]

# Conversión a mK relativo al centroide medio
mean_T = np.mean(T_vals)
mean_W = np.mean(W_vals)

delta_T_rtd = (T_vals - mean_T) * 1000.0 # mK
delta_T_fbg_raw = (W_vals - mean_W) * 1000.0 / (SENSITIVITY / 1000.0) # mK

# Filtro de media móvil de 1s (250 puntos a 250 Hz)
fbg_1s = pd.Series(delta_T_fbg_raw).rolling(250, center=True).mean().bfill().ffill().values

# Alineamiento temporal
t_T_sec = np.array([(t - t0).total_seconds() for t in t_T])
t_W_sec = np.array([(t - t0).total_seconds() for t in t_W])

fbg_interp = np.interp(t_T_sec + LAG_SECONDS, t_W_sec, fbg_1s)
residuals_mK = fbg_interp - delta_T_rtd
rms_res = np.sqrt(np.mean(residuals_mK**2))
sigma_res = np.std(residuals_mK)
mean_res = np.mean(residuals_mK)

# Plot
plt.rcParams.update({"font.size": 11, "font.family": "sans-serif"})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2), dpi=300)

# Panel 1: Time Series
ax1.plot(t_T_sec, delta_T_rtd, color="#C53030", lw=1.6, ls="--", label=f"RTD Reference (Pt-100 Capsule)", zorder=2)
ax1.plot(t_T_sec, fbg_interp, color="#1A365D", lw=1.4, alpha=0.9, label=f"PEEK-4 FBG (1s filter, S={SENSITIVITY} pm/K)", zorder=3)

# Arrow 20 mK
ax1.annotate('', xy=(t_T_sec[-1] - 30, -10), xytext=(t_T_sec[-1] - 30, 10),
             arrowprops=dict(arrowstyle='<->', color='#E85D04', lw=2.2))
ax1.text(t_T_sec[-1] - 38, 0, r"$\mathbf{\Delta T = 20\ mK}$", color='#E85D04',
         ha='right', va='center', fontweight='bold', fontsize=10.5,
         bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor='#E85D04', lw=1.2, alpha=0.95))

ax1.set_xlabel("Elapsed Time on Plateau (s)", fontweight="bold")
ax1.set_ylabel("Temperature Deviation $\Delta T$ (mK)", fontweight="bold")
ax1.set_title(f"(a) Real Micro-Kelvin Tracking (Plateau 3: T ≈ {mean_T:.2f} K)", pad=12, fontweight='bold')
ax1.set_ylim(-20, 20)
ax1.grid(True, linestyle=":", alpha=0.4)
ax1.legend(loc="upper left", frameon=True, framealpha=0.95)

# Panel 2: Residuals Histogram
count, bins, _ = ax2.hist(residuals_mK, bins=35, density=True, color="#2B6CB0", alpha=0.45,
                          edgecolor="#1A365D", lw=0.8, label=f"Residuals ($N = {len(residuals_mK)}$)")
x_pdf = np.linspace(-15, 15, 200)
ax2.plot(x_pdf, norm.pdf(x_pdf, mean_res, sigma_res), color="#C53030", lw=2.0,
         label=rf"Fit ($\sigma = {sigma_res:.2f}\ \mathrm{{mK}}$)")

ax2.axvline(0, color="black", lw=1.0, ls="-")
ax2.axvspan(-sigma_res, sigma_res, color='#2A9D8F', alpha=0.2, label=rf'$1\sigma = \pm {sigma_res:.2f}\ \mathrm{{mK}}$')
ax2.axvline(3*sigma_res, color="#E85D04", ls="--", lw=1.8, label=rf"$3\sigma\ \mathrm{{Limit}} = {3*sigma_res:.2f}\ \mathrm{{mK}}$")
ax2.axvline(-3*sigma_res, color="#E85D04", ls="--", lw=1.8)

ax2.set_xlabel("Tracking Residual: $T_{\mathrm{FBG}} - T_{\mathrm{RTD}}$ (mK)", fontweight="bold")
ax2.set_ylabel("Probability Density", fontweight="bold")
ax2.set_title(rf"(b) Real Residual Distribution (RMS = {rms_res:.2f} mK)", pad=12, fontweight='bold')
ax2.set_xlim(-16, 16)
ax2.grid(True, linestyle=":", alpha=0.4)
ax2.legend(loc="upper right", frameon=True, framealpha=0.95)

plt.tight_layout()
out_png = "/afs/cern.ch/user/v/vgarciap/.gemini/antigravity-ide/brain/81cafc34-7bab-4d53-9c9d-8bd02d211614/plateau3_real_tracking.png"
fig.savefig(out_png, dpi=300, bbox_inches='tight')
print(f"✓ Saved {out_png}")
print(f"Plateau 3 Results:")
print(f"  • RTD Std:     {np.std(delta_T_rtd):.2f} mK")
print(f"  • FBG 1s Std:  {np.std(fbg_1s):.2f} mK")
print(f"  • Residual RMS: {rms_res:.2f} mK")
print(f"  • 3-sigma Limit: {3*rms_res:.2f} mK")
