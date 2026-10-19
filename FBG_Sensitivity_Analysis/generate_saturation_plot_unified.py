import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

PATM_PATERNA_BAR = 1.006
A_NIST, B_NIST, C_NIST = 3.7362, 264.651, -6.788

def nist_antoine_T(p_abs):
    return B_NIST / (A_NIST - np.log10(p_abs)) - C_NIST

def nist_antoine_P(T_k):
    return 10.0 ** (A_NIST - B_NIST / (T_k + C_NIST))

# Cargar los 124 plateaus ya extraídos
with open('figures/n2_saturation_plateaus_all_fibers.json', 'r') as f:
    pts = json.load(f)

print(f"Total plateaus cargados: {len(pts)}")

P_data = np.array([p['P_abs'] for p in pts])
T_data = np.array([p['T_rtd'] for p in pts])
T_err = np.array([p['T_std'] for p in pts])
P_err = np.array([p['P_std'] for p in pts])
res_nist = np.array([p['res_nist'] for p in pts])

def antoine_fit_func(T, A, B, C):
    return A - B / (T + C)

popt, _ = curve_fit(antoine_fit_func, T_data, np.log10(P_data), p0=[3.7, 260.0, -7.0], maxfev=10000)
A_fit, B_fit, C_fit = popt

def fit_antoine_P(T_k):
    return 10.0 ** (A_fit - B_fit / (T_k + C_fit))

res_fit = T_data - (B_fit / (A_fit - np.log10(P_data)) - C_fit)
rmse_fit = float(np.sqrt(np.mean(res_fit**2)))
rmse_nist = float(np.sqrt(np.mean(res_nist**2)))
mean_res_nist = float(np.mean(res_nist))

fig, (ax_main, ax_res) = plt.subplots(
    2, 1, figsize=(9.2, 7.8),
    gridspec_kw={'height_ratios': [2.8, 1.2], 'hspace': 0.08}
)

T_dense = np.linspace(74.0, 95.0, 500)

# Curvas teóricas y fits
ax_main.plot(T_dense, nist_antoine_P(T_dense), 'k--', lw=2.0, alpha=0.85,
             label=r'NIST $N_2$ theoretical saturation (Edejer & Thodos, 1967)', zorder=4)
ax_main.plot(T_dense, fit_antoine_P(T_dense), color='#D90429', lw=2.2,
             label=r'Experimental Antoine fit (RTD 7, all runs)', zorder=5)

# Línea atmosférica
ax_main.axhline(PATM_PATERNA_BAR, color='#6C757D', ls=':', lw=1.5, zorder=3,
                label=r'Atmospheric pressure $P_{\mathrm{atm}} = 1.006\ \mathrm{bar}$ (Paterna)')

# PUNTOS EXPERIMENTALES UNIFICADOS
ax_main.errorbar(T_data, P_data, xerr=T_err, yerr=P_err,
                 fmt='o', color='#1D3557', markersize=6.0,
                 mec='black', mew=0.5, ecolor='#457B9D', elinewidth=0.8, capsize=2,
                 label=r'Experimental steady plateaus ($N = 124$, all runs)', zorder=10)

# Caja de información termodinámica
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

ax_main.text(0.025, 0.965, eq_text, transform=ax_main.transAxes, fontsize=8.5, va='top',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#4A5568', alpha=0.92, lw=1.0))

ax_main.set_ylabel(r'Absolute Pressure $P_{\mathrm{abs}}$ (bar)', fontsize=12, fontweight='bold')
ax_main.set_ylim(0.6, 5.0)
ax_main.set_title(r'Vessel Thermodynamic Equilibrium: $N_2$ Saturation Curve vs. NIST Reference', fontsize=13, fontweight='bold', pad=12)

# Leyenda limpia de 4 entradas
ax_main.legend(loc='lower right', ncol=1, fontsize=8.8, framealpha=0.92, edgecolor='#ADB5BD',
               borderpad=0.4, labelspacing=0.35, handletextpad=0.4)
ax_main.grid(True, which='major', linestyle='--', alpha=0.35)
ax_main.minorticks_on()
ax_main.grid(True, which='minor', linestyle=':', alpha=0.15)
ax_main.tick_params(labelbottom=False)

# PANEL DE RESIDUALES UNIFICADO
ax_res.plot(T_data, res_nist, 'o', color='#1D3557', markersize=5.0,
            mec='black', mew=0.5, alpha=0.85, zorder=10,
            label=r'Plateau residuals ($T_{\mathrm{RTD}} - T_{\mathrm{NIST}}$)')
ax_res.axhline(0.0, color='black', lw=1.3, label='NIST theoretical saturation (0 K)')
ax_res.axhline(+0.3, color='#2B9348', ls='--', lw=0.9, alpha=0.7)
ax_res.axhline(-0.3, color='#2B9348', ls='--', lw=0.9, alpha=0.7)
ax_res.fill_between([73, 97], -0.3, 0.3, color='#2B9348', alpha=0.08, label='±0.3 K agreement band')

ax_res.set_xlabel(r'Temperature $T_{\mathrm{RTD}}$ (K)', fontsize=12, fontweight='bold')
ax_res.set_ylabel(r'$T_{\mathrm{RTD}} - T_{\mathrm{NIST}}$ (K)', fontsize=11, fontweight='bold')
ax_res.set_xlim(75.0, 94.0)
ax_res.set_ylim(-1.0, 1.0)
ax_res.legend(loc='upper left', fontsize=8.2, ncol=2, framealpha=0.9, borderpad=0.3, labelspacing=0.25)
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

print("¡Gráfico unificado generado con éxito!")
