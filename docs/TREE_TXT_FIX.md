# 🔧 Diagnóstico y Solución: TXT con offsets = 0.000

## 📊 Problema Identificado

El archivo TXT generado muestra todos los offsets en `0.000 mK` porque:

### Causa Raíz
**`CalibrationNetwork.compute_offset_to_top_reference()` no puede calcular offsets** porque los objetos `Set` no tienen sus `calibration_constants` DataFrame calculado.

### Flujo Actual (INCORRECTO)
```python
1. Se crean objetos Set: ✅
   for set_id in all_set_numbers:
       s = Set(...)
       
2. Se calculan offsets internos: ✅
   s.calculate_offsets_and_rms()  # Crea matrices offset_matrix, error_matrix
   
3. ❌ FALTA: Calcular calibration_constants
   # NO se llama a s.offset_repeatability() ni calculate_weighted_mean_offsets()
   # Por tanto s.calibration_constants = None o vacío
   
4. Se construye CalibrationNetwork: ⚠️
   net = CalibrationNetwork(sets_dict, config_path=config_path)
   # CalibrationNetwork espera que cada Set tenga calibration_constants
   
5. Se intenta calcular offsets globales: ❌
   offset, error, path = net.compute_offset_to_top_reference(sensor_id, ref_set)
   # Falla porque no hay calibration_constants para calcular offsets internos
```

### Comparación con TREE_RESISTENCES (CORRECTO)

```python
# TREE_RESISTENCES (funciona):
set_sts = SetSTS(...)
set_sts.offset_repeatability(...)  # ✅ Calcula calibration_constants
# Resultado: set_sts.calibration_constants = DataFrame con offsets de cada sensor

# TREE (actual, no funciona):
s = Set(...)
s.calculate_offsets_and_rms()  # Solo crea offset_matrix
# s.calibration_constants = None ❌
```

## 🎯 Solución

### Opción 1: Agregar cálculo de `calibration_constants` (RECOMENDADO)

Modificar la celda que crea los objetos `Set` para llamar al método que calcula las constantes de calibración.

**Ubicación**: Celda ~26 (donde se crea `sets_dict`)

**Cambio necesario**:
```python
# ANTES (solo calcula offsets internos):
for set_id in all_set_numbers:
    s = Set(...)
    s.calculate_offsets_and_rms()  # Solo offsets internos
    sets_dict[set_id] = s

# DESPUÉS (calcula constantes de calibración):
for set_id in all_set_numbers:
    s = Set(...)
    s.calculate_offsets_and_rms()  # Offsets internos
    
    # ✅ AGREGAR: Calcular constantes de calibración
    try:
        # Opción A: usar offset_repeatability (como TREE_RESISTENCES)
        s.offset_repeatability(
            tini=20, 
            tend=40, 
            save_dir=None,  # No guardar archivos
            write_csv=False,  # No escribir CSV
            write_excel=False  # No escribir Excel
        )
        # Ahora s.calibration_constants tiene los offsets de cada sensor
        
    except Exception as e:
        logger.warning(f"No se pudo calcular constantes para set {set_id}: {e}")
        # Fallback: crear DataFrame vacío
        s.calibration_constants = pd.DataFrame()
    
    sets_dict[set_id] = s
```

### Opción 2: Usar CalibrationNetwork sin constantes previas

Si queremos usar CalibrationNetwork de forma más "pura", podríamos modificar el método `compute_offset_to_top_reference` para que calcule offsets on-the-fly desde `offset_matrix` en lugar de `calibration_constants`.

**Pero esto es más complejo y requiere modificar `calibration_network.py`**

## 📋 Plan de Implementación (Opción 1)

### Paso 1: Localizar celda de creación de sets
Buscar la celda que contiene:
```python
for set_id in all_set_numbers:
    s = Set(...)
    s.calculate_offsets_and_rms()
    sets_dict[set_id] = s
```

### Paso 2: Agregar cálculo de constantes
Después de `s.calculate_offsets_and_rms()`, agregar:
```python
# Calcular constantes de calibración (necesario para CalibrationNetwork)
try:
    s.offset_repeatability(
        tini=20, 
        tend=40, 
        save_dir=None,
        write_csv=False,
        write_excel=False
    )
    if s.calibration_constants is not None:
        logger.info(f"Set {set_id}: {len(s.calibration_constants)} sensores con constantes calculadas")
except Exception as e:
    logger.warning(f"Set {set_id}: No se pudieron calcular constantes - {e}")
    s.calibration_constants = pd.DataFrame()
```

### Paso 3: Verificar warnings

Los warnings que estás viendo probablemente son:
- `Could not calculate offsets for sensor X`
- `No se encontró offset entre X y Y en la matriz`

Estos desaparecerán una vez que `calibration_constants` esté calculado correctamente.

### Paso 4: Re-ejecutar celdas

1. Ejecutar celda modificada (creación de sets con constantes)
2. Ejecutar celda de CalibrationNetwork
3. Ejecutar celda 38 (cálculo masivo de offsets)
4. Ejecutar celda 40 (generación TXT)

## 🔍 Verificación

Después de implementar la solución, verificar:

### 1. Constantes de calibración existen
```python
# En la celda después de crear sets_dict:
for set_id, s in sets_dict.items():
    if hasattr(s, 'calibration_constants') and s.calibration_constants is not None:
        print(f"Set {set_id}: {len(s.calibration_constants)} sensores con constantes")
    else:
        print(f"Set {set_id}: ⚠️ SIN constantes de calibración")
```

### 2. Offsets se calculan correctamente
```python
# En celda 38, verificar output:
# Debe mostrar:
#   ✅ Procesamiento completado:
#      Exitosos: X/Y  (donde X > 0)
#      Fallidos: Z/Y  (donde Z < Y)
```

### 3. DataFrame no está vacío
```python
# En celda 38:
print(df_offsets_r1_r3['offset_millikelvin'].describe())
# Debe mostrar valores != 0.000
```

### 4. TXT contiene valores reales
```bash
# Verificar archivo generado:
head -20 calibration_constants_temperature_sensors.txt
# Los offsets deben tener valores != 0.000
```

## 📌 Notas Importantes

### Sensores en channels 13-14
Según mencionaste, los canales 13-14 se excluyen del análisis. Verificar que:
```python
# En la configuración o en el código de Set:
# Debe haber lógica para excluir channels 13-14
# Esto probablemente está en sensors.yaml o en Set.filter_faulty_channels()
```

### Sensores "raised"
Los sensores raised se determinan automáticamente comparando sets entre rondas. El método `CalibrationNetwork._detect_raised_sensors()` hace esto.

### Referencia absoluta
El sensor de referencia (offset = 0.000 por definición) debe ser:
- Un sensor de la Ronda 3 (la más alta)
- Típicamente el primer sensor del Set 57 (según la configuración)

## 🚀 Siguiente Paso

¿Quieres que:
1. **Localice la celda exacta** donde se crean los sets?
2. **Modifique esa celda** para agregar el cálculo de constantes?
3. **Cree una celda de verificación** para debuggear el estado actual?

---

**Fecha**: 10 de diciembre de 2025  
**Autor**: GitHub Copilot  
**Status**: Diagnóstico completo, listo para implementar solución
