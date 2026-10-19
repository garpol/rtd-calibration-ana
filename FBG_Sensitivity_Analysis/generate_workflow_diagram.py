import uproot
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import datetime
from scipy.stats import linregress
import os
import base64
import json

print("="*70)
print("Generating publication-ready Workflow Diagram (PEEK-4 Run 1, Single Unified Box)...")
print("="*70)

INPUT_FILENAME = "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260609.root"
TIME_SHIFT = datetime.timedelta(hours=2)

with uproot.open(INPUT_FILENAME) as f:
    peak_data = f["peak"].arrays(["t", "wav"], library="np")
    temp_data = f["temp"].arrays(["t", "temp"], library="np")

t_temp_raw = temp_data["t"].reshape(-1)
t_peak_raw = peak_data["t"][:, 0]

t_temp_dt = np.array([datetime.datetime.utcfromtimestamp(t) for t in t_temp_raw])
t_peak_dt = np.array([datetime.datetime.utcfromtimestamp(t) + TIME_SHIFT for t in t_peak_raw])

# RTD 8 inside capsule (index 7)
temp_vals = temp_data["temp"][:, 7]

# PEEK-4 Sensor 1: Mean of P (pol 0) and S (pol 1), sensor 0
wav_pol_p = peak_data["wav"][:, 0, 0] * 1e9  # nm
wav_pol_s = peak_data["wav"][:, 1, 0] * 1e9  # nm
wav_vals = (wav_pol_p + wav_pol_s) / 2.0

# Tuned settled plateau windows (pure steady-state after valve adjustments)
manual_plateaus = [
    ("P1", "14:01", "14:11"),
    ("P2", "14:24", "14:33"),
    ("P3", "14:51", "15:00"),
    ("P4", "15:13", "15:22"),
    ("P5", "15:41", "15:50"),
    ("P6", "16:09", "16:18"),
    ("P7", "16:25", "16:34"),
]

date_str = "2026-06-09"
plateau_stats = []

for idx, (p_name, t0_s, tfin_s) in enumerate(manual_plateaus, 1):
    t0_dt = datetime.datetime.strptime(f"{date_str} {t0_s}:00", "%Y-%m-%d %H:%M:%S")
    tfin_dt = datetime.datetime.strptime(f"{date_str} {tfin_s}:00", "%Y-%m-%d %H:%M:%S")
    
    m_temp = (t_temp_dt >= t0_dt) & (t_temp_dt <= tfin_dt)
    m_wav = (t_peak_dt >= t0_dt) & (t_peak_dt <= tfin_dt) & (wav_vals > 1500)
    
    T_seg = temp_vals[m_temp]
    W_seg = wav_vals[m_wav]
    
    T_mean = float(np.nanmean(T_seg))
    T_std = float(np.nanstd(T_seg))
    T_sem = float(T_std / np.sqrt(len(T_seg)))
    
    W_mean = float(np.nanmean(W_seg))
    W_std = float(np.nanstd(W_seg))
    W_sem = float(W_std / np.sqrt(len(W_seg)))
    
    plateau_stats.append({
        'id': idx,
        'label': p_name,
        't0_dt': t0_dt,
        'tfin_dt': tfin_dt,
        'T_mean': T_mean,
        'T_std': T_std,
        'T_sem': T_sem,
        'W_mean': W_mean,
        'W_std': W_std,
        'W_sem': W_sem,
        'N_wav': int(len(W_seg)),
        'N_temp': int(len(T_seg))
    })

# Linear fit
T_arr = np.array([p['T_mean'] for p in plateau_stats])
W_arr = np.array([p['W_mean'] for p in plateau_stats])
T_sem_arr = np.array([p['T_sem'] for p in plateau_stats]) * 1000  # mK
W_sem_arr = np.array([p['W_sem'] for p in plateau_stats]) * 1000  # pm

slope, intercept, r_val, p_val, std_err = linregress(T_arr, W_arr)
slope_pmK = slope * 1000  # pm/K
std_err_pmK = std_err * 1000  # pm/K

# Time series bounds for panel (a)
t_start_global = datetime.datetime.strptime(f"{date_str} 13:40:00", "%Y-%m-%d %H:%M:%S")
t_end_global = datetime.datetime.strptime(f"{date_str} 16:45:00", "%Y-%m-%d %H:%M:%S")

m_t_all = (t_temp_dt >= t_start_global) & (t_temp_dt <= t_end_global)
m_w_all = (t_peak_dt >= t_start_global) & (t_peak_dt <= t_end_global) & (~np.isnan(wav_vals)) & (wav_vals > 1500)

dt_t_plot = t_temp_dt[m_t_all]
val_t_plot = temp_vals[m_t_all]

dt_w_plot = t_peak_dt[m_w_all]
val_w_plot = wav_vals[m_w_all]

# ============================================================================
# MATPLOTLIB STYLING (MATCHING FIGS 2, 3, 4)
# ============================================================================
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10.5,
    "axes.labelsize": 10.5,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 8.8,
    "figure.titlesize": 11.5
})

fig = plt.figure(figsize=(11.5, 8.4), dpi=300)
gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], hspace=0.36, wspace=0.30)

ax_a = fig.add_subplot(gs[0, :])
ax_b = fig.add_subplot(gs[1, 0])
ax_c = fig.add_subplot(gs[1, 1])

# ----------------------------------------------------------------------------
# PANEL (a): TIME-SERIES AND STANDARDIZED PLATEAUS
# ----------------------------------------------------------------------------
ax_a_twin = ax_a.twinx()

color_T = '#1A365D'  # Dark Navy
color_W = '#C53030'  # Crimson Red

line_T = ax_a.plot(dt_t_plot, val_t_plot, color=color_T, lw=1.5, label=r'Reference RTD 8 ($T_{\mathrm{RTD}}$)')
line_W = ax_a_twin.plot(dt_w_plot[::10], val_w_plot[::10], color=color_W, lw=1.4, alpha=0.92,
                        label=r'PEEK-4 Sensor 1 ($\lambda_B$)')

# Shaded plateaus
for p in plateau_stats:
    ax_a.axvspan(p['t0_dt'], p['tfin_dt'], color='#2A9D8F', alpha=0.20, zorder=1)
    mid_t = p['t0_dt'] + (p['tfin_dt'] - p['t0_dt']) / 2
    ax_a.text(mid_t, 95.0, p['label'], ha='center', va='center', fontsize=8.8, fontweight='bold',
              color='#1B4332', bbox=dict(boxstyle='round,pad=0.22', facecolor='#E8F5E9', edgecolor='#A5D6A7', lw=0.9, alpha=0.95))

ax_a.set_ylabel(r'Temperature $T_{\mathrm{RTD}}$ (K)', fontsize=10.5, fontweight='bold', color=color_T)
ax_a_twin.set_ylabel(r'Bragg Wavelength $\lambda_B$ (nm)', fontsize=10.5, fontweight='bold', color=color_W)
ax_a.tick_params(axis='y', labelcolor=color_T)
ax_a_twin.tick_params(axis='y', labelcolor=color_W)

ax_a_twin.ticklabel_format(useOffset=False, style='plain', axis='y')
ax_a_twin.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.2f'))
ax_a_twin.set_ylim(1532.05, 1532.42)

ax_a.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax_a.set_xlabel('Time (UTC, HH:MM)', fontsize=10.5, fontweight='bold')
ax_a.set_title(r'(a) Temporal acquisition: stepped depressurisation and standardized plateaus ($\Delta t \approx 10\ \mathrm{min}$)',
               fontsize=11.0, fontweight='bold', loc='left', pad=10)
ax_a.grid(True, ls=':', alpha=0.4)
ax_a.set_ylim(75.0, 96.5)
ax_a.set_xlim(t_start_global, t_end_global)

legend_lines_a = [
    plt.Line2D([0], [0], color=color_T, lw=1.6, label=r'Reference RTD 8 ($T_{\mathrm{RTD}}$)'),
    plt.Line2D([0], [0], color=color_W, lw=1.6, label=r'PEEK-4 Sensor 1 ($\lambda_B$)'),
    plt.Rectangle((0, 0), 1, 1, facecolor='#2A9D8F', alpha=0.25, label=r'Standardized plateau windows ($N \approx 70{,}000$)')
]
ax_a.legend(handles=legend_lines_a, loc='lower left', fontsize=8.8, framealpha=0.95, frameon=True)

# ----------------------------------------------------------------------------
# PANEL (b): ZOOM INTO REPRESENTATIVE PLATEAU (P2: ~90.70 K - EXTREMELY STABLE)
# ----------------------------------------------------------------------------
zoom_p = plateau_stats[1]  # Plateau P2
m_zoom_w = (t_peak_dt >= zoom_p['t0_dt']) & (t_peak_dt <= zoom_p['tfin_dt'])
t_zoom_raw = t_peak_dt[m_zoom_w]
w_zoom_raw = wav_vals[m_zoom_w]

t_zoom_sec = np.array([(t - zoom_p['t0_dt']).total_seconds() for t in t_zoom_raw])
w_zoom_pm = (w_zoom_raw - zoom_p['W_mean']) * 1000  # pm deviation

sem_pm = zoom_p['W_sem'] * 1000
std_pm = zoom_p['W_std'] * 1000
dur_min = (zoom_p['tfin_dt'] - zoom_p['t0_dt']).total_seconds() / 60.0

ax_b.scatter(t_zoom_sec[::5], w_zoom_pm[::5], s=2.5, color='#457B9D', alpha=0.45, label='Raw data samples (250 Hz)', rasterized=True)
ax_b.axhline(0.0, color='#C53030', lw=1.8, label=r'Arithmetic mean $\mu_\lambda$')
ax_b.axhspan(-sem_pm, sem_pm, color='#C53030', alpha=0.35, label=rf'$\pm\mathrm{{SEM}}_\lambda = \pm {sem_pm:.3f}\ \mathrm{{pm}}$')
ax_b.axhline(std_pm, color='#4A5568', ls=':', lw=1.1)
ax_b.axhline(-std_pm, color='#4A5568', ls=':', lw=1.1, label=rf'$\pm 1\sigma = \pm {std_pm:.2f}\ \mathrm{{pm}}$')

ax_b.set_xlabel(r'Elapsed Time in Plateau $\Delta t$ (s)', fontsize=10.5, fontweight='bold')
ax_b.set_ylabel(r'$\lambda_B - \mu_\lambda$ (pm)', fontsize=10.5, fontweight='bold')
ax_b.set_title(rf'(b) Intra-plateau stability zoom (Plateau P2: $T = {zoom_p["T_mean"]:.2f}\ \mathrm{{K}}$)',
               fontsize=10.8, fontweight='bold', loc='left', pad=10)
ax_b.set_xlim(0, int(dur_min * 60))
ax_b.set_ylim(-3.5 * std_pm, 3.5 * std_pm)
ax_b.legend(loc='upper right', fontsize=8.2, framealpha=0.95, frameon=True)
ax_b.grid(True, ls=':', alpha=0.4)

stat_box_text = (
    r"$\mathbf{Plateau\ Statistics\ (P2):}$" + "\n"
    rf"• Duration: $\Delta t = {dur_min:.1f}\ \mathrm{{min}}$ ({int(dur_min*60)} s)" + "\n"
    f"• Optical Samples: N = {zoom_p['N_wav']:,}\n"
    f"• Mean Temp.: $\mu_T = {zoom_p['T_mean']:.3f}\ \mathrm{{K}}$\n"
    f"• $\mathrm{{SEM}}_T = \pm {zoom_p['T_sem']*1000:.2f}\ \mathrm{{mK}}$\n"
    f"• $\mathrm{{SEM}}_\lambda = \pm {sem_pm:.3f}\ \mathrm{{pm}}$"
)
ax_b.text(0.04, 0.05, stat_box_text, transform=ax_b.transAxes, fontsize=8.2, va='bottom',
          bbox=dict(boxstyle='round,pad=0.35', facecolor='white', edgecolor='#CBD5E0', alpha=0.95))

# ----------------------------------------------------------------------------
# PANEL (c): LINEAR REGRESSION FIT (SINGLE UNIFIED CLEAN BOX)
# ----------------------------------------------------------------------------
T_dense = np.linspace(76.0, 93.0, 200)
W_dense = slope * T_dense + intercept

# Plot centroids with SEM bars
pt_line = ax_c.errorbar(T_arr, W_arr, xerr=T_sem_arr/1000, yerr=W_sem_arr/1000, fmt='o',
                        color='#1A365D', ecolor='#1A365D', elinewidth=1.4, capsize=4, capthick=1.2, markersize=5.8,
                        label=r'Plateau centroids $\mu$ ($\pm\mathrm{SEM}$)', zorder=5)

# Plot linear fit line
fit_line, = ax_c.plot(T_dense, W_dense, color='#C53030', ls='--', lw=2.0,
                      label=rf'Linear fit ($R^2 = {r_val**2:.5f}$)', zorder=4)

ax_c.set_xlabel(r'Reference Temperature $T_{\mathrm{RTD}}$ (K)', fontsize=10.5, fontweight='bold')
ax_c.set_ylabel(r'Bragg Wavelength $\lambda_B$ (nm)', fontsize=10.5, fontweight='bold')
ax_c.set_title(r'(c) Linear sensitivity regression ($S = \mathrm{d}\lambda_B/\mathrm{d}T$)',
               fontsize=10.8, fontweight='bold', loc='left', pad=10)
ax_c.grid(True, ls=':', alpha=0.4)

ax_c.ticklabel_format(useOffset=False, style='plain', axis='y')
ax_c.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.2f'))
ax_c.set_ylim(1532.05, 1532.50)

# Clean single legend elevated well above the highest data points
ax_c.legend(handles=[pt_line, fit_line],
            labels=[
                r'Plateau centroids $\mu$ ($\pm\mathrm{SEM}$)',
                rf'Linear fit ($S = {slope_pmK:.2f} \pm {std_err_pmK:.2f}\ \mathrm{{pm/K}}$)'
            ],
            loc='upper left', bbox_to_anchor=(0.03, 0.98),
            fontsize=8.8, framealpha=0.96, frameon=True, edgecolor='#CBD5E0')

# ----------------------------------------------------------------------------
# EXPORT FIGURES
# ----------------------------------------------------------------------------
os.makedirs('paper_figures', exist_ok=True)
os.makedirs('figures', exist_ok=True)

out_png = 'paper_figures/fig0_calibration_workflow.png'
out_pdf = 'paper_figures/fig0_calibration_workflow.pdf'

fig.savefig(out_png, dpi=300, bbox_inches='tight')
fig.savefig(out_pdf, bbox_inches='tight')

# Also save to figures/workflow_diagram.pdf and .png for Overleaf compatibility
fig.savefig('figures/workflow_diagram.png', dpi=300, bbox_inches='tight')
fig.savefig('figures/workflow_diagram.pdf', bbox_inches='tight')

# Copy to CERNBox folder
cernbox_dir = '/eos/user/v/vgarciap/cernbox/TESIS/papers/figures'
if os.path.exists(cernbox_dir):
    import shutil
    shutil.copy(out_png, os.path.join(cernbox_dir, 'workflow_diagram.png'))
    shutil.copy(out_pdf, os.path.join(cernbox_dir, 'workflow_diagram.pdf'))
    shutil.copy(out_png, os.path.join(cernbox_dir, 'fig0_calibration_workflow.png'))
    shutil.copy(out_pdf, os.path.join(cernbox_dir, 'fig0_calibration_workflow.pdf'))
    print(f"✓ Copied to CERNBox: {cernbox_dir}")

# Embed PNG directly into Notebook Cell 57 outputs
with open(out_png, 'rb') as f_img:
    img_b64 = base64.b64encode(f_img.read()).decode('utf-8')

nb_path = 'Analisis_FBG_PEEK4_2sensores_20260611_3.ipynb'
if os.path.exists(nb_path):
    with open(nb_path, 'r') as f_nb:
        nb = json.load(f_nb)
    with open('generate_workflow_diagram.py', 'r') as f_code:
        code_lines = f_code.read().splitlines(keepends=True)
    nb['cells'][57]['source'] = code_lines
    nb['cells'][57]['outputs'] = [
        {
            'data': {
                'image/png': img_b64,
                'text/plain': ['<Figure size 3450x2520 with 4 Axes>']
            },
            'metadata': {},
            'output_type': 'display_data'
        }
    ]
    with open(nb_path, 'w') as f_nb:
        json.dump(nb, f_nb, indent=1)
    print("✓ Updated Notebook Cell 57 source and embedded display output!")

# plt.show()
print(f"✓ Saved {out_png} and {out_pdf}")
print("="*70)
