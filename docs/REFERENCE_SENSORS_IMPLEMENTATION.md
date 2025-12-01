# Sensores de Referencia: Implementación y Exclusión

## Resumen

Se ha implementado el manejo de sensores de referencia (channels 13-14) para separarlos correctamente del árbol de calibración y evitar que sean detectados erróneamente como sensores "raised".

## Problema Original

Los sensores de referencia (típicamente ubicados en los channels 13-14) se repiten en múltiples sets como monitores externos del proceso de calibración. Esto causaba dos problemas:

1. **Falsos positivos en detección de raised**: Al repetirse en varios sets, eran detectados automáticamente como sensores "raised" cuando en realidad NO forman parte del árbol de calibración.

2. **Confusión en el grafo**: Podían crear conexiones espurias entre sets que no correspondían a relaciones reales de calibración.

## Solución Implementada

### 1. Extracción de Información de Referencia (`run.py`)

#### Método modificado: `read_run_info()` (líneas 185-236)

```python
def read_run_info(self) -> None:
    """
    Lee información adicional del run desde el logfile incluyendo sensores de referencia.
    
    Los sensores de referencia (REF1, REF2) se almacenan desde las columnas dedicadas
    REF1_ID, REF2_ID, REF1_CHAN, REF2_CHAN. Si estas columnas no existen, se usa el
    método legacy de leer desde S19, S20.
    """
```

**Cambios clave:**
- Extrae `REF1_ID`, `REF2_ID` de columnas dedicadas en LogFile.csv
- Extrae `REF1_CHAN`, `REF2_CHAN` para saber en qué columnas S están
- Almacena info como: `Ref1_ID`, `Ref2_ID`, `Ref1_Channel`, `Ref2_Channel`
- Backward compatibility: si las columnas dedicadas no existen, lee de S19/S20

#### Método nuevo: `get_reference_sensor_ids()` (líneas 238-258)

```python
def get_reference_sensor_ids(self) -> list:
    """
    Devuelve lista de sensor IDs de referencia para este run.
    
    Returns:
        list: Lista de sensor IDs de referencia (típicamente 2 sensores).
              Estos sensores NO deben ser considerados parte del árbol de calibración.
    """
```

**Funcionalidad:**
- Devuelve lista con IDs de sensores de referencia (ejemplo: `[48176, 48177]`)
- Excluye valores `None` o inválidos
- Documentado que estos sensores NO son parte del árbol de calibración

### 2. Agregación a Nivel de Set (`set.py`)

#### Método nuevo: `get_reference_sensors_for_set()` (líneas 328-364)

```python
def get_reference_sensors_for_set(self, calib_set_number: float) -> dict:
    """
    Get reference sensor information for a specific set.
    
    Returns:
        dict: {
            'ref_sensor_ids': set of all reference sensor IDs found,
            'runs_with_refs': list of (filename, [ref_ids]) tuples
        }
    """
```

**Funcionalidad:**
- Agrega info de referencias de todos los runs en un set
- Devuelve set de IDs únicos encontrados
- Lista qué runs tienen qué referencias

#### Método nuevo: `get_all_reference_sensors()` (líneas 366-384)

```python
def get_all_reference_sensors(self) -> dict:
    """
    Get reference sensor information for all sets.
    
    Returns:
        dict: mapping CalibSetNumber -> reference sensor info
    """
```

**Funcionalidad:**
- Recopila referencias de todos los sets procesados
- Estructura: `{set_num: {'ref_sensor_ids': set(...), 'runs_with_refs': [...]}}`

### 3. Exclusión en Auto-Detección (`calibration_network.py`)

#### Método modificado: `auto_detect_raised_sensors()` (líneas 536-635)

**Nuevos parámetros:**
```python
def auto_detect_raised_sensors(
    self,
    set_id: Union[float, str],
    logfile_df: pd.DataFrame,
    verbose: bool = False,
    exclude_reference_sensors: bool = True  # NUEVO
) -> List[int]:
```

**Cambios clave:**

1. **Obtención de referencias del set actual:**
```python
reference_sensor_ids = set()
if exclude_reference_sensors:
    ref_info = current_set_obj.get_reference_sensors_for_set(set_id)
    reference_sensor_ids = ref_info.get('ref_sensor_ids', set())
```

2. **Exclusión de sensores actuales:**
```python
current_sensors = current_sensors - reference_sensor_ids
```

3. **Exclusión de sensores en sets de ronda superior:**
```python
for other_set_id in self.sets.keys():
    # ...
    if exclude_reference_sensors:
        other_ref_info = other_set_obj.get_reference_sensors_for_set(other_set_id)
        other_ref_ids = other_ref_info.get('ref_sensor_ids', set())
        other_sensors = other_sensors - other_ref_ids
```

**Comportamiento:**
- Por defecto (`exclude_reference_sensors=True`), excluye referencias
- Puede deshabilitarse para debugging con `exclude_reference_sensors=False`
- Excluye referencias tanto del set actual como de los sets de ronda superior
- Logging verbose muestra qué referencias fueron excluidas

#### Método modificado: `validate_and_suggest_raised_sensors()` (líneas 699-703)

**Cambio:**
```python
detected_raised = self.auto_detect_raised_sensors(
    set_id, 
    logfile_df, 
    verbose=False,
    exclude_reference_sensors=True  # Siempre excluir en validación
)
```

La validación automática SIEMPRE excluye referencias para evitar sugerencias incorrectas.

## Ejemplo de Uso

### A nivel de Run:

```python
from src.run import Run
from src.logfile import Logfile

lf = Logfile('RTD_Calibration_VGP/data/LogFile.csv')
run = Run('filename.txt', lf.log_file)
run.associate_sensors()
run.read_run_info()

# Obtener IDs de sensores de referencia
ref_ids = run.get_reference_sensor_ids()
print(f"Sensores de referencia: {ref_ids}")  # Ejemplo: [48176, 48177]
```

### A nivel de Set:

```python
from src.set import Set

set_manager = Set('RTD_Calibration_VGP/data/LogFile.csv', 
                  config_path='RTD_Calibration_VGP/config/sensors.yaml')
set_manager.group_runs_by_set(selected_sets=[3.0])
set_manager.calculate_offsets_and_rms(selected_sets=[3.0])

# Obtener referencias de un set específico
ref_info = set_manager.get_reference_sensors_for_set(3.0)
print(f"Referencias del set 3: {ref_info['ref_sensor_ids']}")

# Obtener referencias de todos los sets
all_refs = set_manager.get_all_reference_sensors()
for set_num, info in all_refs.items():
    print(f"Set {set_num}: {info['ref_sensor_ids']}")
```

### A nivel de CalibrationNetwork:

```python
from src.calibration_network import CalibrationNetwork

network = CalibrationNetwork(
    sets_dict=set_manager.runs_by_set,
    config_path='RTD_Calibration_VGP/config/sensors.yaml'
)

# Auto-detección CON exclusión de referencias (default)
raised_with_exclusion = network.auto_detect_raised_sensors(
    set_id=3.0,
    logfile_df=lf.log_file,
    verbose=True,
    exclude_reference_sensors=True  # Default
)

# Para debugging: auto-detección SIN exclusión
raised_without_exclusion = network.auto_detect_raised_sensors(
    set_id=3.0,
    logfile_df=lf.log_file,
    verbose=True,
    exclude_reference_sensors=False
)

# Comparar diferencias
false_positives = set(raised_without_exclusion) - set(raised_with_exclusion)
print(f"Falsos positivos (referencias): {false_positives}")
```

## Estructura de LogFile.csv

### Columnas relevantes:

- `REF1_ID`: ID del sensor de referencia 1
- `REF2_ID`: ID del sensor de referencia 2
- `REF1_CHAN`: Columna S donde está REF1 (ejemplo: "S19")
- `REF2_CHAN`: Columna S donde está REF2 (ejemplo: "S20")
- `S1` a `S20`: Sensor IDs mapeados a channels

### Ejemplo de datos:

```csv
Filename,REF1_ID,REF2_ID,REF1_CHAN,REF2_CHAN,S1,S2,...,S19,S20
run_1.txt,48176,48177,S19,S20,48205,48203,...,48176,48177
run_2.txt,48176,48177,S19,S20,48205,48203,...,48176,48177
```

**Nota:** Los sensores 48176, 48177 se repiten en múltiples runs/sets pero NO son "raised" - son referencias externas.

## Beneficios

1. **Detección precisa**: No más falsos positivos de sensores raised
2. **Documentación clara**: Información de referencias accesible y estructurada
3. **Flexibilidad**: Puede deshabilitarse la exclusión para análisis específicos
4. **Backward compatible**: Funciona con logfiles antiguos que usan S19/S20
5. **Validación mejorada**: Sugerencias automáticas más precisas

## Limitaciones Conocidas

1. **LogFile_smoke.csv**: No tiene columnas REF1_ID/REF2_ID, por lo que el test de exclusión no puede ejecutarse con datos smoke
2. **Sets sin referencias**: Algunos sets pueden no tener sensores de referencia; en ese caso los métodos devuelven conjuntos vacíos
3. **Posiciones variables**: Asume que referencias están típicamente en channels 13-14, pero esto puede variar por run

## Pruebas

Se creó un script de prueba `test_reference_exclusion.py` que:
- Carga datos de calibración
- Identifica sensores de referencia
- Ejecuta auto-detección con/sin exclusión
- Compara resultados y valida la exclusión correcta

**Nota:** El test requiere LogFile.csv completo, no funciona con LogFile_smoke.csv debido a columnas faltantes.

## Próximos Pasos

1. **Exportación a YAML**: Añadir método para exportar metadata de referencias a archivo YAML
2. **Validación de grafo**: Verificar que `_find_bridge_sensors()` también excluya referencias
3. **Visualización**: Marcar sensores de referencia de forma distinta en plots del grafo
4. **Tests unitarios**: Añadir tests específicos para exclusión de referencias en `tests/`
