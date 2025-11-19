# FBG Sensitivity Analysis - Archivos Creados

## 📁 Estructura del Proyecto

```
Sensitivity (Press.)/
├── fbg_press_sensitivity_analysis.py  # ⭐ PRINCIPAL: Script/librería completo
├── example_usage.py                    # 📖 Ejemplos de uso
├── test_analysis_script.ipynb          # 🧪 Notebook de prueba
├── README.md                           # 📚 Documentación completa
├── install_dependencies.sh             # 🔧 Script de instalación
└── QUICK_START.md                      # 👉 ESTE ARCHIVO
```

## 🚀 Quick Start

### Opción 1: Desde Terminal (sin plots)

```bash
# 1. Navegar al directorio
cd "/eos/user/v/vgarciap/SWAN_projects/Sensitivity (Press.)"

# 2. Ejecutar con auto-detección de plateaus
python3 fbg_press_sensitivity_analysis.py \
    --file /eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/resampled20250310.root \
    --auto-plateaus

# 3. O con plateaus manuales
python3 fbg_press_sensitivity_analysis.py \
    --file /eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/resampled20250310.root \
    --plateaus "14:50-15:13,15:30-15:52,16:05-16:30,16:40-16:57,17:06-17:12"
```

### Opción 2: Desde Notebook/SWAN

```python
# Importar el módulo
from fbg_press_sensitivity_analysis import run_analysis

# Ejecutar análisis (auto plateaus)
results = run_analysis(
    filepath="/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/resampled20250310.root",
    auto_plateaus=True,
    tolerance=0.01,
    min_plateau_length=500
)

# O con plateaus manuales
plateau_times = [
    ("Plateau 1", "14:50", "15:13"),
    ("Plateau 2", "15:30", "15:52"),
    ("Plateau 3", "16:05", "16:30"),
    ("Plateau 4", "16:40", "16:57"),
    ("Plateau 5", "17:06", "17:12"),
]

results = run_analysis(
    filepath="/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/resampled20250310.root",
    plateau_times=plateau_times
)
```

### Opción 3: Probar con el Notebook de Test

```bash
# Abrir en SWAN o Jupyter
test_analysis_script.ipynb
```

## 📊 Salida del Script

El script genera una tabla en terminal/notebook con:

1. **Tabla de sensibilidades**: Todos los FBG vs RTD-7 y RTD-8
2. **Valores de R²**: Calidad del ajuste lineal
3. **Estadísticas**: Mean, Std, Min, Max por referencia de temperatura
4. **Sin gráficos**: Ideal para ejecución rápida en terminal

Ejemplo de salida:
```
FBG Sensor   Pol  S#  RTD-7 (pm/K)   RTD-7 R²      RTD-8 (pm/K)   RTD-8 R²     
--------------------------------------------------------------------------------
FBG-1-P      P    1   19.45          0.9987        19.52          0.9991       
FBG-1-S      S    1   19.38          0.9985        19.45          0.9989       
...
```

## 🎯 Características Principales

### ✅ Funcionalidad Completa
- ✓ Carga datos ROOT (uproot)
- ✓ Filtrado automático μ±3σ
- ✓ **Detección automática de plateaus** (función `find_plateaus`)
- ✓ **Definición manual de plateaus** (opción alternativa)
- ✓ Corrección temporal (+1h)
- ✓ Análisis multi-sensor (6 FBG × 2 RTD)
- ✓ Tabla de resultados en terminal (sin plots)
- ✓ R² y estadísticas por sensor

### 🔧 Opciones de Uso
1. **Script ejecutable**: `python3 fbg_press_sensitivity_analysis.py --file ... --auto-plateaus`
2. **Librería Python**: `from fbg_press_sensitivity_analysis import run_analysis`
3. **Funciones individuales**: Importar funciones específicas

### 📈 Detección Automática de Plateaus
```python
from fbg_press_sensitivity_analysis import find_plateaus

# Detectar plateaus en presión
plateaus = find_plateaus(
    values=pressure_data,
    times=timestamps,
    tolerance=0.01,      # 1% de variación permitida
    min_plateau_length=500  # 500 segundos mínimo
)
```

## 🔍 Funciones Disponibles

### Principal
- `run_analysis()` - Análisis completo de sensibilidad

### Carga y Filtrado
- `load_root_data()` - Carga archivo ROOT
- `filter_wavelength_data()` - Filtro μ±3σ para wavelength
- `filter_temperature_data()` - Filtro para temperatura
- `apply_time_shift()` - Corrección temporal

### Plateaus
- `find_plateaus()` - **Detección automática**
- `define_plateaus()` - Definición manual
- `convert_plateaus_to_dict()` - Conversión de formato

### Análisis
- `calculate_plateau_means()` - Promedios por plateau
- `calculate_thermal_sensitivity()` - Sensibilidad individual
- `calculate_all_sensitivities()` - Multi-sensor

### Utilidades
- `get_default_fbg_config()` - Configuración FBG
- `get_default_rtd_config()` - Configuración RTD
- `print_sensitivity_summary()` - Tabla de resultados

## 📝 Parámetros CLI

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--file` | Path al ROOT (REQUERIDO) | - |
| `--auto-plateaus` | Auto-detectar plateaus | False |
| `--plateaus` | Plateaus manuales "HH:MM-HH:MM,..." | None |
| `--tolerance` | % variación auto-detección | 0.01 |
| `--min-length` | Segundos mínimos plateau | 500 |
| `--time-shift` | Corrección temporal (horas) | 1.0 |
| `--temp-sensors` | RTDs: "RTD-7,RTD-8" | "RTD-7,RTD-8" |

## 🎓 Ejemplos Avanzados

### Solo RTD-7 como referencia
```bash
python3 fbg_press_sensitivity_analysis.py \
    --file data.root \
    --auto-plateaus \
    --temp-sensors "RTD-7"
```

### Detección más estricta
```bash
python3 fbg_press_sensitivity_analysis.py \
    --file data.root \
    --auto-plateaus \
    --tolerance 0.005 \
    --min-length 600
```

### Sin corrección temporal
```bash
python3 fbg_press_sensitivity_analysis.py \
    --file data.root \
    --auto-plateaus \
    --time-shift 0
```

## 📚 Documentación

- **README.md**: Documentación completa con algoritmos y troubleshooting
- **example_usage.py**: Ejemplos de uso como librería
- **test_analysis_script.ipynb**: Tests interactivos en notebook

## ⚡ Performance

- Tiempo de ejecución: ~10-30 segundos (depende de tamaño de datos)
- Sin generación de plots: Muy rápido para análisis batch
- Ideal para: Scripts automáticos, análisis en lote, CI/CD

## 🐛 Troubleshooting

**ModuleNotFoundError: No module named 'uproot'**
```bash
pip install --user uproot
# O en notebook: !pip install uproot
```

**"Found 0 plateaus"**
- Reduce `--tolerance` (ej: 0.005)
- Reduce `--min-length` (ej: 300)

**Sensitividades anormales**
- Verifica `--time-shift` (debe ser 1.0 para PEEK-7)
- Verifica que plateaus tengan buen rango de temperatura

## 📞 Soporte

Para issues o preguntas, contacta a Victor Garcia.

---

**Última actualización**: Noviembre 2025
**Versión**: 1.0.0
**Python**: ≥3.7
**Dependencias**: uproot, numpy, scipy, matplotlib (opcional)
