# FBG Thermal Sensitivity Analysis

Herramienta para análisis de sensibilidad térmica de sensores FBG (Fiber Bragg Grating) en experimentos de presión con fibra PEEK-7.

## 📋 Características

- **Carga automática** de archivos ROOT con datos de FBG y RTD
- **Filtrado automático** de wavelength usando método μ±3σ
- **Detección automática de plateaus** desde datos de presión
- **Definición manual de plateaus** para control preciso
- **Análisis multi-sensor**: 6 canales FBG × 2 referencias de temperatura
- **Salida en formato tabla** sin gráficos (ideal para terminal)
- **Corrección temporal** automática (+1h por defecto)
- **Cálculo de sensibilidad térmica** en pm/K

## 🚀 Uso Rápido

### Desde Terminal

```bash
# Auto-detección de plateaus
python fbg_press_sensitivity_analysis.py \
    --file /path/to/resampled20250310.root \
    --auto-plateaus

# Plateaus manuales
python fbg_press_sensitivity_analysis.py \
    --file /path/to/resampled20250310.root \
    --plateaus "14:50-15:13,15:30-15:52,16:05-16:30"
```

### Desde Python/Notebook

```python
from fbg_press_sensitivity_analysis import run_analysis

# Auto-detección
results = run_analysis(
    filepath="/path/to/data.root",
    auto_plateaus=True
)

# Plateaus manuales
plateau_times = [
    ("Plateau 1", "14:50", "15:13"),
    ("Plateau 2", "15:30", "15:52"),
    # ...
]

results = run_analysis(
    filepath="/path/to/data.root",
    plateau_times=plateau_times
)
```

## 📊 Output

Genera una tabla completa de sensibilidades:

```
================================================================================
THERMAL SENSITIVITY SUMMARY
================================================================================

FBG Sensor   Pol  S#  RTD-7 (pm/K)   RTD-7 R²      RTD-8 (pm/K)   RTD-8 R²     
--------------------------------------------------------------------------------
FBG-1-P      P    1   19.45          0.9987        19.52          0.9991       
FBG-1-S      S    1   19.38          0.9985        19.45          0.9989       
...
================================================================================

STATISTICAL SUMMARY:
RTD-7:  Mean: 19.432 pm/K, Std: 0.058 pm/K
RTD-8:  Mean: 19.502 pm/K, Std: 0.057 pm/K
```

## 📚 Documentación

Ver `QUICK_START.md` para guía detallada con ejemplos y troubleshooting.

## 🔧 Dependencias

```bash
pip install uproot scipy numpy matplotlib
```

O ejecuta:
```bash
./install_dependencies.sh
```

## 🧪 Testing

El notebook `test_analysis_script.ipynb` incluye ejemplos de uso:
- Test 1: Auto-detección de plateaus
- Test 2: Plateaus manuales
- Test 3: Solo RTD-7 como referencia
- Test 4: Comparación de parámetros
- Test 5: Análisis rápido

## 📝 Configuración

### FBG Sensors (PEEK-7)
- 3 sensores × 2 polarizaciones (P, S) = 6 canales
- Sensibilidad esperada: 19-20 pm/K

### RTD Sensors
- RTD 1-4: Sensores externos
- RTD 7-8: Sensores internos (referencia)

### Unidades
- Wavelength: **pm** (picometers)
- Temperature: **K** (Kelvin)
- Pressure: **bar**
- Sensitivity: **pm/K**

## 👤 Autor

Victoria Garcia - victoriagarciapol@gmail.com

## 📄 Licencia

MIT License
