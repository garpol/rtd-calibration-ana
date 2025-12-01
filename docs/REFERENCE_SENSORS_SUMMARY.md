# Sensores de Referencia (Channels 13-14): Resumen de Implementación

## Estado Actual

Los sensores de referencia (típicamente en channels 13-14) están **correctamente manejados** en el sistema:

### ✅ Lo que SÍ se hace

1. **Se calculan offsets incluyendo channels 13-14**
   - Los sensores de referencia están en `calibration_constants`
   - Se calculan sus offsets respecto a otros sensores
   - Esto está bien porque permite monitorear su comportamiento

2. **Se identifican automáticamente**
   - `run.py`: método `get_reference_sensor_ids()` devuelve lista de IDs de referencia
   - `set.py`: método `get_reference_sensors_for_set()` agrega info a nivel de set
   - Columnas en LogFile: `REF1_ID`, `REF2_ID`, `REF1_CHAN`, `REF2_CHAN`

3. **Se excluyen de la detección automática de "raised"**
   - `calibration_network.py`: `auto_detect_raised_sensors(exclude_reference_sensors=True)`
   - Por defecto, los sensores 13-14 NO se consideran como candidatos a "raised"
   - Esto evita falsos positivos (referencias repetidas ≠ sensores raised)

4. **Se excluyen de la construcción del árbol**
   - Los sensores 13-14 NO aparecen en la lista de "raised" en `sensors.yaml`
   - Por tanto, `_find_bridge_sensors()` NO los usa para crear edges en el grafo
   - El árbol de calibración se construye solo con sensores de calibración reales

### ❌ Lo que NO se hace (y está bien así)

1. **NO se excluyen de calibration_constants**
   - Los sensores 13-14 pueden estar en la matriz de constantes
   - Esto permite calcular sus offsets para análisis futuros
   - No causan problemas porque no están en la configuración de "raised"

2. **NO se excluyen del cálculo de offsets**
   - Los métodos `offsets()` y `stat_err_offsets()` los incluyen
   - Esto es correcto: queremos saber sus valores para monitoreo

## Flujo de Trabajo

### 1. Carga de datos (run.py)
```python
run = Run(filename, logfile)
run.associate_sensors()  # Mapea channels 1-14 a IDs
run.read_run_info()      # Extrae REF1_ID, REF2_ID

# Identificar referencias
ref_ids = run.get_reference_sensor_ids()  # Ej: [48176, 48177]
```

### 2. Cálculo de constantes (set.py)
```python
set_manager = Set(logfile, config_path)
set_manager.group_runs_by_set()
set_manager.calculate_offsets_and_rms()

# calibration_constants incluye TODOS los sensores (1-14)
# Esto es correcto - no hace daño
```

### 3. Construcción del árbol (calibration_network.py)
```python
network = CalibrationNetwork(sets_dict, config_path)

# Auto-detección excluye referencias
detected_raised = network.auto_detect_raised_sensors(
    set_id=3.0,
    exclude_reference_sensors=True  # ← Clave
)
# detected_raised NO incluirá sensores 13-14

# Validación también excluye referencias
validation = network.validate_and_suggest_raised_sensors(logfile_df)
# Las sugerencias automáticas NO incluirán sensores 13-14
```

### 4. Construcción de edges en el grafo
```python
# Solo se crean edges basados en "raised" del config
# Como los sensores 13-14 NO están en sensors.yaml como "raised",
# NO se usan para conectar sets en el grafo

# Ejemplo de sensors.yaml (sensores 13-14 ausentes):
# sets:
#   3:
#     raised: [48203, 48479]  # ← Solo sensores de calibración
#     discarded: []
#     round: 1
```

## Verificación

Para verificar que todo funciona correctamente:

1. **Revisar calibration_constants**: Pueden incluir hasta 14 sensores ✅
2. **Revisar auto-detección**: No debe sugerir sensores 13-14 como "raised" ✅
3. **Revisar grafo**: Edges solo entre sensores declarados en `sensors.yaml` ✅
4. **Revisar offsets**: Pueden calcularse para todos los sensores 1-14 ✅

## Configuración en sensors.yaml

```yaml
sensors:
  sets:
    3:
      raised: [48203, 48479]      # Sensores que suben a R2
      discarded: [48205, 48478]   # Sensores defectuosos
      round: 1
      # ⚠️ Nota: NO incluir sensores 13-14 aquí
      # Estos sensores se repiten pero NO "suben" en el árbol
```

## Ejemplo Práctico

Set 3 tiene:
- Sensores 1-12: IDs 48203, 48205, 48478, 48479, ... (calibración)
- Sensor 13: ID 48176 (referencia 1)
- Sensor 14: ID 48177 (referencia 2)

**calibration_constants del Set 3**: Tiene las 14 filas/columnas ✅

**Sensores raised del Set 3**: `[48203, 48479]` (solo calibración) ✅

**Auto-detección**: Compara sensores del Set 3 con Set 12 (R2), pero **excluye** 48176 y 48177 de la comparación ✅

**Grafo**: Solo crea edges Set3 → Set12 usando sensores 48203 y 48479 ✅

## Conclusión

El sistema ya maneja correctamente los sensores de referencia:

- ✅ Se identifican automáticamente
- ✅ Se excluyen de la detección de "raised"
- ✅ NO se usan para construir el árbol
- ✅ Pueden permanecer en calibration_constants sin causar problemas

**No es necesario excluirlos de los cálculos** - el filtrado en `auto_detect_raised_sensors` es suficiente para que no interfieran con la construcción del árbol de calibración.
