import os
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import uproot
from scipy.interpolate import interp1d

PATM_PATERNA_BAR = 1.006
A_NIST, B_NIST, C_NIST = 3.7362, 264.651, -6.788

def nist_antoine_T(p_abs):
    return B_NIST / (A_NIST - np.log10(p_abs)) - C_NIST

def nist_antoine_P(T_k):
    return 10.0 ** (A_NIST - B_NIST / (T_k + C_NIST))

DATA_RUNS = [
    # PEEK (450 µm) — 3 runs
    {'fiber_group': 'PEEK (450 µm)', 'label': 'PEEK-7 Run 1',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20250227.root', 'rtd_col': 7},
    {'fiber_group': 'PEEK (450 µm)', 'label': 'PEEK-7 Run 2',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20250228.root', 'rtd_col': 7},
    {'fiber_group': 'PEEK (450 µm)', 'label': 'PEEK-7 Run 3',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20250310.root', 'rtd_col': 7},

    # PEEK-3 / FBGS-2 (2025 setup)
    {'fiber_group': 'PEEK-3 / FBGS-2 (2025)', 'label': 'PEEK-3/FBGS-2 2025',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20250515.root'},

    # PEEK-3 (200 µm) — 3 runs
    {'fiber_group': 'PEEK-3 (200 µm)', 'label': 'PEEK-3 Run 1',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260326.root'},
    {'fiber_group': 'PEEK-3 (200 µm)', 'label': 'PEEK-3 Run 2',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260327.root'},
    {'fiber_group': 'PEEK-3 (200 µm)', 'label': 'PEEK-3 Run 3',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260420.root'},

    # FBGS-2 / ORMOCER (200 µm) — 3 runs
    {'fiber_group': 'FBGS-2 / ORMOCER (200 µm)', 'label': 'FBGS-2 Run 1',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260423.root'},
    {'fiber_group': 'FBGS-2 / ORMOCER (200 µm)', 'label': 'FBGS-2 Run 2',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260427.root'},
    {'fiber_group': 'FBGS-2 / ORMOCER (200 µm)', 'label': 'FBGS-2 Run 3',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260428.root'},

    # Polyimide-2 (200 µm) — 3 runs
    {'fiber_group': 'Polyimide-2 (200 µm)', 'label': 'POLY-2 Run 1',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260430.root'},
    {'fiber_group': 'Polyimide-2 (200 µm)', 'label': 'POLY-2 Run 2',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260511.root'},
    {'fiber_group': 'Polyimide-2 (200 µm)', 'label': 'POLY-2 Run 3',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260512.root'},

    # PEEK-4 (200 µm) — 3 runs (Run 3 DAQ time shift = +7200 s)
    {'fiber_group': 'PEEK-4 (200 µm)', 'label': 'PEEK-4 Run 1',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260609.root'},
    {'fiber_group': 'PEEK-4 (200 µm)', 'label': 'PEEK-4 Run 2',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260610.root'},
    {'fiber_group': 'PEEK-4 (200 µm)', 'label': 'PEEK-4 Run 3',
     'root': '/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20260611.root',
     'time_shift': 7200.0},
]

def find_plateaus(values, times_sec, tolerance=0.15, min_length=240):
    plateaus = []
    n = len(values)
    i = 0
    while i < n:
        ref = values[i]
        j = i
        while j < n and abs(values[j] - ref) < tolerance:
            ref = np.mean(values[i:j+1])
            j += 1
        duration = times_sec[min(j, n-1)] - times_sec[i]
        if duration >= min_length and (j - i) >= 10:
            plateaus.append({
                't0': times_sec[i],
                'tfin': times_sec[min(j-1, n-1)],
                'mean': np.mean(values[i:j]),
                'std': np.std(values[i:j]),
                'n': j - i
            })
            i = j
        else:
            i += 1
    return plateaus

def extract_all_plateaus(patm=PATM_PATERNA_BAR):
    all_points = []
    for run in DATA_RUNS:
        if not os.path.exists(run['root']):
            continue
        try:
            with uproot.open(run['root']) as f:
                if 'press' not in f or 'temp' not in f:
                    continue
                p_arr = f['press'].arrays(library='np')
                t_arr = f['temp'].arrays(library='np')
            
            p_ts = p_arr['t'].reshape(-1)
            p_vals = p_arr['press'].reshape(-1)
            t_ts = t_arr['t'].reshape(-1) + run.get('time_shift', 0.0)
            
            # Canal 6 (RTD 7 "Inside Capsule 1")
            n_rtds = t_arr['temp'].shape[1]
            rtd_col = run.get('rtd_col', n_rtds - 2 if n_rtds >= 8 else n_rtds - 1)
            t_vals = t_arr['temp'][:, rtd_col]
            
            valid_p = (p_vals >= -0.3) & (p_vals <= 6.0)
            p_ts_v = p_ts[valid_p]
            p_vals_v = p_vals[valid_p]
            
            if len(p_ts_v) < 20 or len(t_ts) < 20:
                continue
            
            plats = find_plateaus(p_vals_v, p_ts_v, tolerance=0.15, min_length=240)
            t_interp = interp1d(t_ts, t_vals, bounds_error=False, fill_value=np.nan)
            
            for pl in plats:
                t_in = t_ts[(t_ts >= pl['t0']) & (t_ts <= pl['tfin'])]
                if len(t_in) < 5:
                    continue
                tv = t_interp(t_in)
                val = ~np.isnan(tv)
                if val.sum() < 5:
                    continue
                
                T_mean = float(np.mean(tv[val]))
                T_std = float(np.std(tv[val]))
                P_abs = float(pl['mean'] + patm)
                P_std = float(pl['std'])
                
                if T_mean < 70 or T_mean > 100 or P_abs < 0.6 or P_abs > 6.0:
                    continue
                
                T_nist = float(nist_antoine_T(P_abs))
                if abs(T_mean - T_nist) > 1.8 or T_std > 0.8:
                    continue
                
                all_points.append({
                    'fiber_group': run['fiber_group'],
                    'label': run['label'],
                    'P_abs': P_abs,
                    'P_std': P_std,
                    'T_rtd': T_mean,
                    'T_std': T_std,
                    'T_nist': T_nist,
                    'res_nist': T_mean - T_nist
                })
        except Exception as e:
            print(f"Error {run['label']}: {e}")
    return all_points

# Extract plateaus
pts = extract_all_plateaus()
print(f"Total plateaus extraídos: {len(pts)}")
with open('figures/n2_saturation_plateaus_all_fibers.json', 'w') as f:
    json.dump(pts, f, indent=2)

P_data = np.array([p['P_abs'] for p in pts])
T_data = np.array([p['T_rtd'] for p in pts])

def antoine_fit_func(T, A, B, C):
    return A - B / (T + C)

popt, _ = curve_fit(antoine_fit_func, T_data, np.log10(P_data), p0=[3.7, 260.0, -7.0], maxfev=10000)
A_fit, B_fit, C_fit = popt

def fit_antoine_T(p_abs):
    return B_fit / (A_fit - np.log10(p_abs)) - C_fit

def fit_antoine_P(T_k):
    return 10.0 ** (A_fit - B_fit / (T_k + C_fit))

for p in pts:
    p['T_fit'] = float(fit_antoine_T(p['P_abs']))
    p['res_fit'] = p['T_rtd'] - p['T_fit']

rmse_fit = float(np.sqrt(np.mean([p['res_fit']**2 for p in pts])))
rmse_nist = float(np.sqrt(np.mean([p['res_nist']**2 for p in pts])))
mean_res_nist = float(np.mean([p['res_nist'] for p in pts]))

# Crear figura de calidad de publicación con leyendas limpias y ordenadas
fig, (ax_main, ax_res) = plt.subplots(
    2, 1, figsize=(9.5, 8.8),
    gridspec_kw={'height_ratios': [3.3, 1.2], 'hspace': 0.08},
    sharex=True, dpi=300
)

group_styles = {
    'PEEK (450 µm)':          {'color': '#6A4C93', 'marker': 'D', 'ms': 6.0, 'label': 'PEEK (450 µm) — 3 runs'},
    'PEEK-3 / FBGS-2 (2025)': {'color': '#1982C4', 'marker': 'v', 'ms': 6.5, 'label': 'PEEK-3 / FBGS-2 (2025)'},
    'PEEK-3 (200 µm)':        {'color': '#118AB2', 'marker': '^', 'ms': 6.5, 'label': 'PEEK-3 (200 µm) — 3 runs'},
    'FBGS-2 / ORMOCER (200 µm)':{'color': '#E63946', 'marker': 'o', 'ms': 6.5, 'label': 'FBGS-2 / ORMOCER (200 µm) — 3 runs'},
    'Polyimide-2 (200 µm)':   {'color': '#2A9D8F', 'marker': 's', 'ms': 6.0, 'label': 'Polyimide-2 (200 µm) — 3 runs'},
    'PEEK-4 (200 µm)':        {'color': '#F4A261', 'marker': 'P', 'ms': 6.5, 'label': 'PEEK-4 (200 µm) — 3 runs'},
}

T_dense = np.linspace(74.0, 95.0, 500)
ax_main.plot(T_dense, nist_antoine_P(T_dense), 'k--', lw=2.0, alpha=0.85,
             label=r'NIST $N_2$ theoretical saturation (Edejer & Thodos, 1967)', zorder=4)
ax_main.plot(T_dense, fit_antoine_P(T_dense), color='#073B4C', lw=2.4,
             label=r'Experimental Antoine fit (All fibers, RTD 7)', zorder=5)

# Línea de presión atmosférica con entrada clara y limpia en la leyenda
ax_main.axhline(PATM_PATERNA_BAR, color='#6C757D', ls=':', lw=1.5, zorder=3,
                label=r'Atmospheric pressure $P_{\mathrm{atm}} = 1.006\ \mathrm{bar}$ (Paterna, 65 m)')

for grp_name, style in group_styles.items():
    grp_pts = [p for p in pts if p['fiber_group'] == grp_name]
    if not grp_pts:
        continue
    ax_main.errorbar([p['T_rtd'] for p in grp_pts], [p['P_abs'] for p in grp_pts],
                     xerr=[p['T_std'] for p in grp_pts], yerr=[p['P_std'] for p in grp_pts],
                     fmt=style['marker'], color=style['color'], markersize=style['ms'],
                     mec='black', mew=0.5, ecolor=style['color'], elinewidth=0.8, capsize=2,
                     label=f"{style['label']} (N = {len(grp_pts)})", zorder=10)
    ax_res.plot([p['T_rtd'] for p in grp_pts], [p['res_nist'] for p in grp_pts],
                style['marker'], color=style['color'], markersize=style['ms']-0.5,
                mec='black', mew=0.5, zorder=10)

# Caja de información termodinámica: esquina superior izquierda (T in [75, 83.5], P in [3.5, 5.0], zona 100% despejada)
eq_lines = [
    r'Antoine Saturation Calibration ($N_2$)',
    r'$\log_{10}(P_{\mathrm{abs}}/\mathrm{bar}) = A - \frac{B}{T + C}$',
    f'• Exp. Fit (RTD 7): A = {A_fit:.4f}, B = {B_fit:.2f}, C = {C_fit:.2f} K',
    f'  RMSE vs Fit = {rmse_fit:.3f} K (N = {len(pts)} plateaus)',
    '• NIST Theory: A = 3.7362, B = 264.65, C = -6.79 K',
    f'  Mean Residual (Exp - NIST): {mean_res_nist:+.2f} K (RMSE = {rmse_nist:.2f} K)',
    f'• Atmospheric Pressure: P_atm = {PATM_PATERNA_BAR:.3f} bar (P_abs = P_gauge + P_atm)',
]
eq_text = '\n'.join(eq_lines)

ax_main.text(0.025, 0.965, eq_text, transform=ax_main.transAxes, fontsize=8.2, va='top',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#4A5568', alpha=0.92, lw=1.0))

ax_main.set_ylabel(r'Absolute Pressure $P_{\mathrm{abs}}$ (bar)', fontsize=12, fontweight='bold')
ax_main.set_ylim(0.6, 5.0)
ax_main.set_title(r'Vessel Thermodynamic Equilibrium: $N_2$ Saturation Curve vs. NIST Reference', fontsize=13, fontweight='bold', pad=12)

# Leyenda principal: ubicada en la esquina inferior derecha vacía
ax_main.legend(loc='lower right', ncol=1, fontsize=8.0, framealpha=0.92, edgecolor='#ADB5BD',
               borderpad=0.3, labelspacing=0.22, handletextpad=0.35)
ax_main.grid(True, which='major', linestyle='--', alpha=0.35)
ax_main.minorticks_on()
ax_main.grid(True, which='minor', linestyle=':', alpha=0.15)
ax_main.tick_params(labelbottom=False)

# Panel de residuales
ax_res.axhline(0.0, color='black', lw=1.3, label='NIST theoretical saturation (0 K)')
ax_res.axhline(+0.3, color='#2B9348', ls='--', lw=0.9, alpha=0.7)
ax_res.axhline(-0.3, color='#2B9348', ls='--', lw=0.9, alpha=0.7)
ax_res.fill_between([73, 97], -0.3, 0.3, color='#2B9348', alpha=0.08, label='±0.3 K agreement band')

ax_res.set_xlabel(r'Temperature $T_{\mathrm{RTD}}$ (K)', fontsize=12, fontweight='bold')
ax_res.set_ylabel(r'$T_{\mathrm{RTD}} - T_{\mathrm{NIST}}$ (K)', fontsize=11, fontweight='bold')
ax_res.set_xlim(75.0, 94.0)
ax_res.set_ylim(-1.0, 1.0)
ax_res.legend(loc='upper left', fontsize=8.2, framealpha=0.9, borderpad=0.3, labelspacing=0.3)
ax_res.grid(True, which='major', linestyle='--', alpha=0.35)
ax_res.minorticks_on()
ax_res.grid(True, which='minor', linestyle=':', alpha=0.15)

out_artifact = '/afs/cern.ch/user/v/vgarciap/.gemini/antigravity-ide/brain/81cafc34-7bab-4d53-9c9d-8bd02d211614/n2_saturation_all_fibers.png'
fig.savefig(out_artifact, dpi=300, bbox_inches='tight')
fig.savefig('figures/n2_saturation_all_fibers.png', dpi=300, bbox_inches='tight')
fig.savefig('figures/n2_saturation_all_fibers.pdf', bbox_inches='tight')
fig.savefig('figures/n2_saturation_with_data.png', dpi=300, bbox_inches='tight')
fig.savefig('figures/n2_saturation_with_data.pdf', bbox_inches='tight')
plt.close(fig)

print("¡Gráficos generados con éxito!")
