# 🔍 Análisis con Runs 'BAD' - Localización del Código

## 📍 **Función Principal**

La función que permite analizar **todos los sets incluyendo runs marcados como 'BAD'** está en:

```python
# Ubicación: RTD_Calibration_VGP/src/set.py (línea ~1622)

def plot_runs_vs_set_and_repeatability(
    self, 
    output_dir="runs_vs_set_plots", 
    include_bad_for_repeatability=True  # ← Parámetro clave
):
    """
    - Genera gráfico de barras: número de runs por CalibSetNumber
    - Para sets con ≥4 runs, ejecuta offset_repeatability() 
    - INCLUYE runs 'BAD' si include_bad_for_repeatability=True
    """
```

### **Características:**
- ✅ **Procesa todos los sets** con ≥4 runs (automático)
- ✅ **Incluye runs 'BAD'** por defecto (`include_bad_for_repeatability=True`)
- ✅ **Excluye automáticamente** filenames con `_pre`, `_st`, `lar`
- ✅ **Genera plots** de repeatability por set (dentro de subdirectorios)
- ✅ **No requiere** especificar `selected_sets` manualmente

---

## 🚀 **Cómo Usar la Función**

### **Opción 1: Desde Python/Notebook (RECOMENDADO)**

```python
from RTD_Calibration_VGP.src.logfile import Logfile
from RTD_Calibration_VGP.src.set import Set

# Cargar logfile
lf = Logfile('RTD_Calibration_VGP/data/LogFile.csv')
s = Set(lf.log_file)

# Ejecutar análisis completo (incluye BAD runs)
s.plot_runs_vs_set_and_repeatability(
    output_dir='analysis_all_sets_with_bad',
    include_bad_for_repeatability=True  # Incluir runs 'BAD'
)
```

**Outputs generados:**
```
analysis_all_sets_with_bad/
├── runs_per_set.png                    # Gráfico de barras (runs por set)
├── repeatability_set_3/                # Plots del set 3
│   ├── offset_repeatability_set_3.0.png
│   └── ...
├── repeatability_set_4/                # Plots del set 4
└── ...
```

---

### **Opción 2: Excluir runs 'BAD'**

```python
# Si quieres excluir los runs marcados como 'BAD'
s.plot_runs_vs_set_and_repeatability(
    output_dir='analysis_all_sets_no_bad',
    include_bad_for_repeatability=False  # Excluir runs 'BAD'
)
```

---

## 📂 **Scripts Relacionados**

Aunque NO usan `plot_runs_vs_set_and_repeatability()`, estos scripts hacen análisis similares:

### **1. `scripts/count_sets.py`**
```bash
python scripts/count_sets.py
```
**Función:** Cuenta cuántos runs tiene cada CalibSetNumber (excluyendo `_pre`)

**Output ejemplo:**
```
Total integer-like sets: 48
Sets with exactly 4 runs: 24
IDs (exactly 4): 2, 4, 5, 7, 8, ...
Sets with more than 4 runs: 18
IDs (>4): 3, 6, 10, 11, 14, ...
```

---

### **2. `scripts/run_sets_4runs.py`**
```bash
python scripts/run_sets_4runs.py
```
**Función:** Ejecuta análisis **solo para sets con exactamente 4 runs** (NO usa `plot_runs_vs_set_and_repeatability`)

**Output:** 
```
RTD_Calibration_VGP/plots/SET_4runs/
├── offset_repeatability_set_2.0.png
├── offset_repeatability_set_4.0.png
└── ...
```

---

## 🔧 **Comparación de Funciones**

| Función | Ubicación | Incluye BAD? | Auto-detecta sets? | Plots? |
|---------|-----------|--------------|-------------------|--------|
| **`plot_runs_vs_set_and_repeatability()`** | `set.py:1622` | ✅ Sí (configurable) | ✅ Sí (≥4 runs) | ✅ Sí |
| `offset_repeatability()` | `set.py:~400` | ❌ No (filtra BAD en `group_runs_by_set`) | ❌ No (requiere `selected_sets`) | ✅ Sí |
| `group_runs_by_set()` | `set.py:~250` | ❌ No (excluye BAD) | ✅ Sí (configurable) | ❌ No |

---

## 🎯 **¿Cuál es la diferencia con tu workflow normal?**

### **Workflow Normal (SET_BUENO.ipynb):**
```python
# Excluye runs 'BAD' automáticamente en group_runs_by_set()
s.group_runs_by_set(selected_sets=[2, 4, 5, ...])  # ← Lista manual
s.calculate_offsets_and_rms(selected_sets=[2, 4, 5, ...])
s.offset_repeatability(selected_sets=[2, 4, 5, ...], ref=2)
```
- ❌ Requiere especificar `selected_sets` manualmente
- ❌ Excluye runs 'BAD' en `group_runs_by_set()` (línea 287)
- ✅ Control fino sobre qué sets procesar

---

### **Análisis Completo con `plot_runs_vs_set_and_repeatability()`:**
```python
# Incluye runs 'BAD' si lo deseas
s.plot_runs_vs_set_and_repeatability(
    output_dir='all_sets_analysis',
    include_bad_for_repeatability=True  # ← Incluir BAD
)
```
- ✅ Procesa **todos los sets** automáticamente (≥4 runs)
- ✅ **Incluye runs 'BAD'** (configurable)
- ✅ Genera gráfico de barras de runs por set
- ❌ Menos control fino (procesa todo)

---

## 📝 **Cómo Crear un Notebook para Este Análisis**

Te recomiendo crear un notebook específico:

### **Archivo: `RTD_Calibration_VGP/notebooks/ALL_SETS_INCLUDING_BAD.ipynb`**

```python
# Celda 1: Imports
import sys
from pathlib import Path
repo_root = Path('../..').resolve()
sys.path.insert(0, str(repo_root))

from RTD_Calibration_VGP.src.logfile import Logfile
from RTD_Calibration_VGP.src.set import Set

# Celda 2: Cargar datos
lf = Logfile('RTD_Calibration_VGP/data/LogFile.csv')
s = Set(lf.log_file)

# Celda 3: Análisis completo (incluye BAD)
s.plot_runs_vs_set_and_repeatability(
    output_dir='outputs/analysis_all_sets_with_bad',
    include_bad_for_repeatability=True
)
print("✅ Análisis completo con runs 'BAD' incluidos")

# Celda 4 (opcional): Análisis sin BAD para comparar
s.plot_runs_vs_set_and_repeatability(
    output_dir='outputs/analysis_all_sets_no_bad',
    include_bad_for_repeatability=False
)
print("✅ Análisis completo SIN runs 'BAD'")
```

---

## 🔍 **Filtros Aplicados por `plot_runs_vs_set_and_repeatability()`**

### **Siempre excluye (no configurable):**
- ❌ Filenames con `_pre` (case-insensitive)
- ❌ Filenames con `_st` (excluidos en `group_runs_by_set`)
- ❌ Filenames con `lar` (excluidos en `group_runs_by_set`)
- ❌ CalibSetNumber no enteros (ej: 3.5)

### **Excluye opcionalmente (configurable):**
- ⚙️ Runs con `Selection == 'BAD'` (según `include_bad_for_repeatability`)

### **⚠️ NO filtra (pero debería):**
- ❗ **Liquid Media** — La función NO filtra por `'LN2'` vs `'LAr'`
  - El LogFile contiene 703 runs con LN2 y 6 con LAr
  - La función procesa ambos tipos mezclados
  - **Solución**: Ver notebook `ANALYSIS_ALL_SETS_LN2.ipynb` con filtro mejorado

### **Siempre incluye:**
- ✅ Sets con ≥4 runs válidos después de filtros
- ✅ Todos los sensores (no excluye por `discarded_sensors` a este nivel)

---

## 🚨 **Importante: Diferencia con `group_runs_by_set()`**

La función `group_runs_by_set()` (línea ~250 en `set.py`) **SIEMPRE excluye runs 'BAD'**:

```python
# Línea 287 en group_runs_by_set()
if selection != "BAD":  # ← Filtro hard-coded
    # Procesar run...
else:
    print(f"    Excluded: {filename} (marked as 'BAD' in Selection)")
```

Por eso, **para incluir runs 'BAD'** necesitas usar `plot_runs_vs_set_and_repeatability()` que:
1. Carga los runs directamente desde el logfile
2. Opcionalmente filtra `Selection == 'BAD'` según el parámetro
3. NO pasa por `group_runs_by_set()`

---

## 📊 **Resumen Visual**

```
LogFile.csv (todas las filas)
    ↓
plot_runs_vs_set_and_repeatability()
    ↓
[Excluye _pre, _st, lar automáticamente]
    ↓
include_bad_for_repeatability?
    ├─ True  → Incluye runs 'BAD'
    └─ False → Excluye runs 'BAD'
    ↓
[Agrupa por CalibSetNumber]
    ↓
[Selecciona sets con ≥4 runs]
    ↓
[Genera plots de repeatability por set]
    ↓
Output: runs_per_set.png + repeatability_set_X/
```

---

## 🎯 **¿Quieres que cree el notebook `ALL_SETS_INCLUDING_BAD.ipynb`?**

Puedo generarlo ahora con:
- ✅ Análisis de todos los sets (≥4 runs)
- ✅ Opción para incluir/excluir runs 'BAD'
- ✅ Gráficos comparativos
- ✅ Exportación de estadísticas

**¿Te interesa?**

---

## ⚠️ IMPORTANTE: Filtro de Liquid Media Faltante

### **Problema Detectado:**

La función `plot_runs_vs_set_and_repeatability()` **NO filtra por `Liquid Media`**.

Esto significa que mezcla runs de:
- **LN2** (Liquid Nitrogen - 703 runs en el LogFile)
- **LAr** (Liquid Argon - 6 runs en el LogFile)

### **Solución Implementada:**

He creado el notebook **`ANALYSIS_ALL_SETS_LN2.ipynb`** que:

✅ **Filtra correctamente por `Liquid Media = 'LN2'`**  
✅ Aplica todos los filtros necesarios:
  - CalibSetNumber entero
  - Filename sin `_pre`, `_st`, `lar`
  - **Liquid Media = LN2** (NUEVO)
  - Selection BAD (configurable)
  
✅ **Incluye análisis exploratorio** con estadísticas de filtrado  
✅ **Genera gráficos comparativos**  
✅ **Exporta CSVs** con resultados por set

### **Ubicación:**
```
RTD_Calibration_VGP/notebooks/ANALYSIS_ALL_SETS_LN2.ipynb
```

### **Uso Rápido:**
```python
# Abrir el notebook y ejecutar todas las celdas
# Configurar en Celda 3:
INCLUDE_BAD_RUNS = True      # True/False
LIQUID_MEDIA_FILTER = 'LN2'  # 'LN2', 'LAr', o None
MIN_RUNS_PER_SET = 4
```

### **Outputs:**
```
outputs/analysis_all_sets_LN2_with_bad/
├── runs_per_set_filtered.png           # Gráfico de barras
├── repeatability_set_3/                # Plots por set
│   ├── offset_repeatability_set_3.0.png
│   ├── skipped_runs_due_to_defects.csv
│   └── offset_repeatability_summary.csv
└── ...
```

---

## 📊 Comparación de Implementaciones

| Característica | `plot_runs_vs_set_and_repeatability()` | `ANALYSIS_ALL_SETS_LN2.ipynb` |
|----------------|---------------------------------------|-------------------------------|
| Filtra por LN2 | ❌ NO | ✅ SÍ |
| Incluye BAD runs | ✅ Configurable | ✅ Configurable |
| Análisis exploratorio | ❌ NO | ✅ SÍ |
| Gráficos estadísticos | ⚠️ Solo bar plot | ✅ Múltiples |
| Exporta CSVs | ⚠️ Limitado | ✅ Completo |
| Transparencia de filtros | ❌ Poca | ✅ Alta |

**Recomendación: Usar el notebook `ANALYSIS_ALL_SETS_LN2.ipynb` para análisis exhaustivos.**
