# Análisis y Mejora de TREE.ipynb - Celda 27

**Fecha**: 30 de octubre de 2025  
**Issue**: Celda 27 generaba warnings excesivos y usaba lógica incorrecta

---

## 🔍 Problema Identificado

### Síntomas Reportados
```
23:20:02 | WARNING  | No se encontró offset entre 48203 y 48484 en la matriz
23:20:02 | WARNING  | No se encontró offset entre 48203 y 48484 en la matriz
[repetido muchas veces...]
23:20:02 | INFO | Usando sensor de referencia absoluta 48484 del set 4 (ronda 1)
```

### Análisis de Causa Raíz

**Problema 1: Concepto erróneo sobre sensores "raised"**
- **Error conceptual**: Se asumía que sensores de R3 eran exclusivos de ese set
- **Realidad**: Los sensores "raised" SUBEN por las rondas
  - Sensor 48484 está en Set 4 (R1), Set 49 (R2) Y Set 57 (R3)
  - Esto es **CORRECTO** y parte del diseño del árbol
- **Consecuencia**: Buscar "sensor de referencia" encontraba Set 4 (R1) primero

**Problema 2: API ambigua**
- La celda buscaba automáticamente en qué set estaba el sensor de referencia
- Encontraba el PRIMER set (Set 4, R1) en lugar del set de referencia (Set 57, R3)
- La función necesita que se especifique EXPLÍCITAMENTE el set de referencia

**Problema 3: Parámetros incorrectos**
- **ANTES**: `SENSOR_REFERENCIA = 48484` ← buscaba el sensor
- **DESPUÉS**: `SET_REFERENCIA = 57` ← especifica el set directamente
- La función `compute_offset_to_top_reference(sensor_id, ref_set)` necesita el SET, no el sensor

---

## ✅ Solución Implementada

### Cambios en Celda 27

#### 1. Cambio Fundamental: Especificar SET en vez de SENSOR
```python
# ANTES (incorrecto - busca sensor automáticamente):
SENSOR_REFERENCIA = 48484  # ← Encontraba Set 4 (R1) primero ❌

# DESPUÉS (correcto - especifica el set directamente):
SET_REFERENCIA = 57  # ← Set de referencia R3 explícito ✅

# Llamada a la función:
offset, error, path = net.compute_offset_to_top_reference(
    sensor_id=str(SENSOR_OBJETIVO),
    ref_set=SET_REFERENCIA  # ← Parámetro correcto
)
```

#### 2. Validación de Ronda
```python
# Nuevo código agregado:
ref_round = get_set_round(set_ref, sensors_config)

if ref_round != 3:
    print(f"[ADVERTENCIA] El sensor de referencia NO esta en Ronda 3!")
    print(f"[SOLUCION] Usa un sensor de Set 57 (R3):")
    # Listar sensores disponibles en R3
```

#### 3. Mensajes Informativos por Pasos
```
[PASO 1/3] Validando sensor de referencia...
   OK Sensor 48480 encontrado en Set 57 (Ronda 3)
   OK Sensor de referencia es de Ronda 3 (referencia absoluta)

[PASO 2/3] Localizando sensor objetivo...
   OK Sensor 48203 encontrado en Set 3 (Ronda 1)
   [INFO] Ruta esperada: R1 (Set 3) -> R2 (Set intermedio) -> R3 (Set 57)

[PASO 3/3] Calculando offset encadenado...
```

#### 4. Detección Automática de Ruta
- Detecta automáticamente las rondas de ambos sensores
- Informa la ruta esperada antes de calcular
- Proporciona contexto sobre qué tipo de offset se calculará

#### 5. Interpretación de Resultados
```python
print(f"El sensor {SENSOR_OBJETIVO} lee {abs(offset):.6f}°C MAS/MENOS que {SENSOR_REFERENCIA}")
```

---

## 🌳 Estructura Real del Árbol de Calibración

### Concepto Clave: Sensores "Raised" Suben por las Rondas

**Los sensores NO son exclusivos de una ronda**. Un sensor "raised" se mide en múltiples rondas:

```
Sensor 48484:
   ├── Set 4 (R1)  ← Medición inicial en calibración de Set 4
   ├── Set 49 (R2) ← Re-medición como "raised" (conecta R1 con R2)
   └── Set 57 (R3) ← Re-medición como referencia final
```

### Por Qué Esto es Correcto

1. **Conexión entre rondas**: Los sensores raised son el "puente" entre niveles
2. **Propagación de offsets**: Permiten calcular R1 → R2 → R3 siguiendo el mismo sensor
3. **Referencia común**: Todos los sensores se calibran respecto a la misma referencia absoluta

### Implicaciones para el Código

- ✅ **Es normal** que `48484` esté en `sets_dict[4]`, `sensor_mappings[49]` y `sensor_mappings[57]`
- ❌ **No buscar** automáticamente en qué set está un sensor (puede estar en varios)
- ✅ **Especificar** explícitamente el set de referencia (Set 57 para R3)

---

## 📊 Comparación: Celda 27 vs Celda 39

### Celda 27: Ejemplo Individual (Didáctico)
- **Propósito**: Calcular offset de UN sensor → referencia
- **Uso**: Exploración interactiva, debugging, ejemplos
- **Características**:
  - Validación exhaustiva
  - Mensajes paso a paso
  - Interpretación detallada
  - Fácil modificación de parámetros

### Celda 39: Procesamiento Masivo (Producción)
- **Propósito**: Calcular offsets de TODOS los sensores R1 → R3
- **Uso**: Análisis completo, exportación a CSV, visualizaciones
- **Características**:
  - Itera sobre todos los sets R1
  - Genera DataFrame con todos los offsets
  - Crea matrices por set
  - Estadísticas globales

**Ambas celdas usan**:
```python
offset, error, path = net.compute_offset_to_top_reference(
    sensor_id=sensor_str,
    ref_set=set_ref
)
```

---

## 🔧 Función `compute_offset_to_top_reference()`

### Lógica Interna (calibration_network.py)

```python
def compute_offset_to_top_reference(self, sensor_id, ref_set=None):
    """
    Calcula offset siguiendo la jerarquía vertical del árbol:
    
    1. Identifica set del sensor objetivo
    2. Identifica set de referencia (R3 si ref_set=None)
    3. Obtiene sensores "raised" del set actual
    4. Busca el siguiente set en la ronda superior que contenga ese sensor raised
    5. Calcula offset dentro del set (sensor → raised)
    6. Repite desde paso 3 hasta llegar a R3
    7. Suma offsets y propaga errores
    """
```

### Por Qué Fallaba Antes

```
Sensor 48203 (Set 3, R1) → Sensor 48484 (Set 4, R1)
                ↓
         compute_offset_to_top_reference()
                ↓
    Busca sensores raised de Set 3: [48203, 48479]
                ↓
    Busca raised[0] (48203) en Set 4 (R1)  ← ❌ AQUÍ FALLA
                ↓
    Set 4 NO es "ronda siguiente" (ambos son R1)
                ↓
    No encuentra path → genera warnings infinitos
```

### Por Qué Funciona Ahora

```
Sensor 48203 (Set 3, R1) → Sensor 48480 (Set 57, R3)
                ↓
         compute_offset_to_top_reference()
                ↓
    Busca sensores raised de Set 3: [48203, 48479]
                ↓
    Busca raised[0] (48203) en Sets de R2  ✅
                ↓
    Encuentra 48203 en Set 49 (R2)
                ↓
    Calcula offset: Sensor48203(R1) → Sensor48203(R2)
                ↓
    Repite para R2 → R3
                ↓
    Encuentra 48203 en Set 57 (R3)
                ↓
    Calcula offset: Sensor48203(R2) → Sensor48480(R3)
                ↓
    Suma offsets: Total = offset(R1→R2) + offset(R2→R3)
```

---

## 🎯 Mejores Prácticas

### Para Usar Celda 27

1. **Siempre usa un sensor de R3 como referencia**
   ```python
   SENSOR_REFERENCIA = 48480  # Set 57, R3 ✅
   ```

2. **Verifica la ronda de tu sensor objetivo**
   - R1 → R3: 2 saltos (R1→R2→R3)
   - R2 → R3: 1 salto (R2→R3)
   - R3 → R3: 0 saltos (offset = 0)

3. **Lee los mensajes de validación**
   - Si dice "ADVERTENCIA", hay un problema conceptual
   - Si dice "INFO", todo está correcto

4. **Sensores recomendados de R3 (Set 57)**
   ```python
   48480, 48481, 48482, 48483, 48484, 48485, ...
   ```

### Para Procesamiento Masivo

**Usa Celda 39** en lugar de hacer un loop manual sobre Celda 27:
- Más eficiente (optimizado para batch)
- Genera DataFrames listos para análisis
- Incluye estadísticas automáticas
- Exportable a CSV

---

## 📝 Próximos Pasos

### Inmediato
- [ ] Ejecutar Celda 27 con valores por defecto y verificar output limpio
- [ ] Probar con diferentes sensores de R1 y R2
- [ ] Ejecutar Celda 39 para análisis masivo completo

### Mejoras Futuras

1. **Refactorizar `compute_offset_to_top_reference()`**
   - Mover lógica de validación fuera de la función
   - Separar detección de ronda en método auxiliar
   - Mejorar manejo de errores para casos edge

2. **Agregar Tests Unitarios**
   ```python
   def test_offset_same_round_fails():
       """Verifica que R1→R1 lanza error apropiado"""
   
   def test_offset_r1_to_r3_succeeds():
       """Verifica que R1→R3 funciona correctamente"""
   ```

3. **Documentación**
   - Agregar docstring detallado a `compute_offset_to_top_reference()`
   - Documentar la estructura del árbol en README
   - Crear diagrama visual de la jerarquía

4. **Optimización**
   - Cachear rutas ya calculadas
   - Evitar recalcular offsets duplicados
   - Implementar path finding más eficiente (Dijkstra)

---

## 🐛 Bugs Relacionados Conocidos

### Bug en `compute_offset_to_top_reference()`

**Ubicación**: `calibration_network.py` línea ~1760

**Problema**: Cuando el set de referencia (R3) no tiene sensores "raised" definidos (lo cual es correcto, porque ES la referencia), la función puede fallar.

**Workaround actual**: La función detecta si es R3 y usa el primer sensor de `calibration_constants` como referencia.

**Solución propuesta**: Refactorizar para que R3 no necesite lógica especial:
```python
if round == max_round:
    # Es el set de referencia, no necesita "raised"
    return first_sensor_in_calibration_constants()
else:
    # Sets no-referencia SÍ necesitan "raised"
    return get_raised_sensors_from_config()
```

---

## 📚 Referencias

- **`RTD_Calibration_VGP/src/calibration_network.py`**: Implementación de CalibrationNetwork
- **`RTD_Calibration_VGP/config/sensors.yaml`**: Configuración de sensores y rondas
- **`RTD_Calibration_VGP/notebooks/TREE.ipynb`**:
  - Celda 3: Función `get_set_round()`
  - Celda 27: Cálculo individual mejorado
  - Celda 39: Cálculo masivo optimizado
- **Commits relacionados**:
  - `3c1b677`: Fixes principales (7 bugs)
  - `bdb7e02`: Fix Unicode
  - `199ce0c`: Documentación
  - [Pendiente]: Este fix de celda 27

---

## 🎉 Resumen Ejecutivo

**Problema**: Celda 27 usaba sensor de referencia incorrecto (R1 en vez de R3), causando warnings infinitos y offsets incorrectos.

**Solución**: 
1. Cambió sensor por defecto a R3 (48480)
2. Agregó validación de ronda
3. Mejoró mensajes informativos
4. Documentó diferencias con celda 39

**Resultado esperado**: Ejecución limpia sin warnings, offsets correctos, mensajes claros.

**Próximo paso**: Ejecutar celda 27 y verificar funcionamiento.
