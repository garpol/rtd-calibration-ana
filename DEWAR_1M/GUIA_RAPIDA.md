# DEWAR Analysis - Guía Rápida en Español

## 📦 Archivos Creados

1. **`dewar_analysis.py`** (22 KB)
   - Módulo principal con todas las clases y funciones
   - Reutilizable para cualquier run del DEWAR
   
2. **`DEWAR_GENERAL_ANALYSIS.ipynb`** (11 KB)
   - Notebook general que usa el módulo
   - Ejemplos completos de uso
   - Análisis individual y por lotes
   
3. **`example_quick_analysis.py`** (2.3 KB)
   - Script de ejemplo para análisis rápido
   - Configuración simple
   
4. **`README_ANALYSIS.md`** (7.3 KB)
   - Documentación completa en inglés
   - Ejemplos de código
   - Solución de problemas

## 🚀 Uso Rápido

### Opción 1: Función Quick Analysis

```python
from dewar_analysis import quick_analysis

loader, analyzer, plotter, fit_results = quick_analysis(
    file_path="/path/to/20251119.root",
    date="2025-11-19",
    start_hour=16,
    end_hour=18,
    sensor_idx=2  # Sensor 3
)
```

### Opción 2: Usando las Clases

```python
from dewar_analysis import DewarDataLoader, DewarAnalyzer, DewarPlotter
import datetime

# 1. Cargar datos
loader = DewarDataLoader("/path/to/20251119.root")
loader.load_data()

# 2. Definir ventana temporal
start = datetime.datetime(2025, 11, 19, 16, 0, 0)
end = datetime.datetime(2025, 11, 19, 18, 0, 0)

# 3. Analizar
analyzer = DewarAnalyzer(loader)
peak_res, temp_res = analyzer.resample_sensor_data(2, start, end, "5min")

# 4. Ajustar
fit = analyzer.fit_temperature_vs_wavelength(peak_res, temp_res)
print(f"Pendiente: {fit['slope_mK_pm']:.2f} mK/pm")

# 5. Graficar
plotter = DewarPlotter()
plotter.plot_wavelength_vs_temperature(fit, "Sensor 3")
```

## 📊 Clases Principales

### 1. `DewarDataLoader`
Carga archivos ROOT y preprocesa timestamps.

**Características:**
- Corrección automática de tiempo (+2h para peaks)
- Conversión de timestamps a datetime
- Extracción fácil de datos por sensor

### 2. `DewarAnalyzer`
Realiza análisis estadísticos y ajustes.

**Características:**
- Remuestreo con estadísticas (mean, std, se)
- Ajuste lineal ponderado (T vs λB)
- Cálculo de offsets entre sensores
- Análisis de residuos

### 3. `DewarPlotter`
Crea gráficos listos para publicación.

**Características:**
- Series temporales (λB y Temperatura)
- Gráficos scatter con ajustes
- Comparación multi-sensor
- Gráficos de offsets

## 🎯 Casos de Uso

### Caso 1: Análisis de un Sensor Específico
```python
# Analiza Sensor 3 del run del 19/11/2025
quick_analysis(
    "/eos/user/j/jcapotor/FBGdata/ROOTFiles/Dewar1m/20251119.root",
    "2025-11-19", 16, 18, sensor_idx=2
)
```

### Caso 2: Comparar Múltiples Sensores
```python
plotter.plot_multiple_sensors_fit(
    analyzer, 
    sensor_indices=[0, 2, 3, 4],  # Sensores 1, 3, 4, 5
    start_time=start,
    end_time=end,
    resample_interval="2min"
)
```

### Caso 3: Calcular Offsets
```python
lambda_off, temp_off, peak_all, temp_all = analyzer.compute_sensor_offsets(
    start, end, 
    resample_interval="2min",
    reference_sensor_idx=4  # Sensor 5 como referencia
)

plotter.plot_sensor_offsets(lambda_off, temp_off, peak_all, temp_all)
```

### Caso 4: Análisis por Lotes
```python
runs = [
    {"file": "20251107.root", "date": "2025-11-07", "start": 14, "end": 15},
    {"file": "20251119.root", "date": "2025-11-19", "start": 16, "end": 17},
]

for run in runs:
    _, _, _, fit = quick_analysis(
        run["file"], run["date"], run["start"], run["end"], sensor_idx=2
    )
    print(f"{run['date']}: {fit['slope_mK_pm']:.2f} mK/pm")
```

## 📝 Mapeo de Sensores

| Índice | Sensor | Altura (m) | Nota |
|--------|--------|------------|------|
| 0 | Sensor 1 | 2 | |
| 1 | Sensor 2 | 3 | Excluido de temperatura |
| 2 | Sensor 3 | 4 | |
| 3 | Sensor 4 | 5 | |
| 4 | Sensor 5 | 6 | Referencia típica |

## ⚙️ Configuración Típica

```python
# Corrección temporal
time_correction_hours = 2.0  # +2h para peaks

# Intervalo de remuestreo
resample_interval = "5min"  # o "2min" para más detalle

# Sensor de referencia para offsets
reference_sensor = 4  # Sensor 5
```

## 🔍 Resultados del Ajuste

El diccionario `fit_results` contiene:

```python
{
    'slope_K_nm': float,      # Pendiente en K/nm
    'slope_mK_pm': float,     # Pendiente en mK/pm (más común)
    'intercept_K': float,     # Intercepción en K
    'x': np.ndarray,          # Datos λB (nm)
    'y': np.ndarray,          # Datos T (K)
    'yerr': np.ndarray,       # Incertidumbres
    'y_fit': np.ndarray,      # Valores ajustados
    'residuos': np.ndarray,   # Residuos del ajuste
    'n_points': int           # Número de puntos
}
```

## 💡 Ventajas del Módulo

1. **Reutilizable**: Funciona para cualquier fecha/run
2. **Modular**: Usa solo las partes que necesites
3. **Completo**: Desde carga hasta gráficos
4. **Documentado**: Docstrings en todas las funciones
5. **Robusto**: Manejo de errores y validaciones
6. **Flexible**: Configurable para diferentes análisis

## 🛠️ Próximos Pasos

1. **Prueba el módulo** con el notebook `DEWAR_GENERAL_ANALYSIS.ipynb`
2. **Adapta los ejemplos** a tus necesidades específicas
3. **Guarda tus resultados** usando pandas: `df.to_csv()`
4. **Crea tus propios scripts** basados en `example_quick_analysis.py`

## 📚 Estructura del Código

```
DEWAR_1M/
├── dewar_analysis.py              # Módulo principal ⭐
├── DEWAR_GENERAL_ANALYSIS.ipynb   # Notebook general ⭐
├── example_quick_analysis.py      # Ejemplo rápido
├── README_ANALYSIS.md             # Documentación completa
├── GUIA_RAPIDA.md                 # Esta guía
├── ROOT_DEWAR_07_11.ipynb         # Run histórico
├── ROOT_DEWAR_19_11.ipynb         # Run del 19/11
└── ROOT_DEWAR_29_10.ipynb         # Run histórico
```

## ❓ Preguntas Frecuentes

**P: ¿Cómo cambio el sensor a analizar?**  
R: Cambia `sensor_idx` (0=Sensor1, 2=Sensor3, etc.)

**P: ¿Cómo ajusto la ventana temporal?**  
R: Modifica `start_hour` y `end_hour`, o usa objetos `datetime` directamente

**P: ¿Dónde están los datos originales?**  
R: En EOS: `/eos/user/j/jcapotor/FBGdata/ROOTFiles/Dewar1m/`

**P: ¿Puedo usar esto para otros runs?**  
R: ¡Sí! Solo cambia el `file_path` y las fechas/horas

**P: ¿Cómo guardo los resultados?**  
R: Usa pandas: `peak_res.to_csv("output.csv")`

## 🎓 Recursos Adicionales

- Ver ejemplos completos en `DEWAR_GENERAL_ANALYSIS.ipynb`
- Documentación detallada en `README_ANALYSIS.md`
- Código fuente comentado en `dewar_analysis.py`

---

**Autor**: DUNE HD Calibration Team  
**Fecha**: Noviembre 2025  
**Versión**: 1.0
