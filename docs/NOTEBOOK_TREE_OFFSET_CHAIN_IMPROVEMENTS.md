# 🌳 Mejoras en TREE.ipynb - Sistema de Calibración en Cascada

## 📋 Resumen de Cambios

Se han realizado mejoras significativas en el notebook `TREE.ipynb` para implementar un **sistema de calibración en cascada** con estructura de árbol, donde los offsets se encadenan desde sensores de Ronda 1 hasta una referencia absoluta de Ronda 3.

## 🔧 Correcciones Técnicas

### 1. **Error de Tipo en Set Constructor**
- **Problema**: Se pasaba un objeto `Logfile` en lugar de la ruta del archivo al constructor de `Set`
- **Solución**: Modificado para usar `logfile.log_file` (DataFrame) cuando `logfile` es un objeto `Logfile`
- **Código**:
```python
# Si logfile es un objeto Logfile, usar su log_file DataFrame
if hasattr(logfile, 'log_file'):
    set_handler = Set(logfile.log_file)
    print("✅ Set creado con DataFrame del logfile")
else:
    # Si es un DataFrame directamente
    set_handler = Set(logfile)
    print("✅ Set creado con DataFrame")
```

## 🌳 Nuevas Funcionalidades del Sistema de Cascada

### 2. **Estructura de Árbol de Calibración**
- **Ronda 3**: Sensor de referencia absoluta (primer sensor del sensor mapping)
- **Ronda 2**: Sensores 'raised' que se calibran contra la referencia de Ronda 3
- **Ronda 1**: Sensores de medición que se calibran contra su sensor 'raised' de Ronda 2

### 3. **Función de Cálculo de Cadena de Offsets**
```python
def calculate_offset_chain(net, sensor_r1, sensor_r2_raised, sensor_r3_reference):
    """
    Calcula la cadena completa de offsets desde un sensor de Ronda 1 hasta la referencia absoluta
    
    Args:
        sensor_r1: Sensor de Ronda 1 (el que queremos calibrar)
        sensor_r2_raised: Sensor 'raised' de Ronda 2 correspondiente
        sensor_r3_reference: Sensor de referencia absoluta de Ronda 3
    
    Returns:
        tuple: (offset_total, error_total, detalles)
    """
```

### 4. **Propagación de Errores**
- **Offset Total**: Suma de offsets individuales
- **Error Total**: Propagación cuadrática de errores: `√(Error²_R1→R2 + Error²_R2→R3)`

## 📊 Identificación Automática de Sensores

### 5. **Sistema de Identificación por Ronda**
```python
# Obtener sets por ronda
sets_round_1 = net.get_sets_by_round(1)
sets_round_2 = net.get_sets_by_round(2) 
sets_round_3 = net.get_sets_by_round(3)

# Identificar sensor de referencia absoluta
ref_set = sets_round_3[0]  # Primer set de ronda 3
ref_sensor = net._get_reference_sensor(ref_set)
```

## 🎯 Casos de Uso

### 6. **Ejemplo Práctico**
```python
# Sensores de ejemplo
sensor_r1_ejemplo = 48203      # Sensor de Ronda 1
sensor_r2_ejemplo = 48479      # Sensor 'raised' de Ronda 2
sensor_r3_ejemplo = 99999      # Sensor de referencia absoluta de Ronda 3

# Calcular cadena
offset_total, error_total, detalles = calculate_offset_chain(
    net, sensor_r1_ejemplo, sensor_r2_ejemplo, sensor_r3_ejemplo
)
```

## 📚 Documentación Completa

### 7. **Guía de Uso Detallada**
- Explicación clara de la estructura del sistema
- Fórmulas matemáticas para cálculo de offsets y errores
- Ejemplos de código para implementación
- Guía para extensión futura a 4 rondas

## 🚀 Beneficios del Sistema

### 8. **Ventajas Implementadas**
- **Modularidad**: Sistema escalable para futuras rondas
- **Claridad**: Identificación clara de cada sensor y su función
- **Precisión**: Propagación correcta de errores a través de la cadena
- **Flexibilidad**: Permite seleccionar cualquier sensor de Ronda 1 para calibración
- **Trazabilidad**: Breakdown detallado de cada offset en la cadena

## 🔮 Extensión Futura

### 9. **Preparación para 4 Rondas**
El sistema está diseñado para crecer automáticamente cuando se implementen 4 rondas:
- Ronda 4: Nueva referencia absoluta
- Ronda 3: Sensores 'raised' intermedios
- Ronda 2: Sensores 'raised' intermedios  
- Ronda 1: Sensores de medición final

## 📝 Archivos Modificados

- `RTD_Calibration_VGP/notebooks/TREE.ipynb`: Notebook principal con todas las mejoras
- `NOTEBOOK_TREE_OFFSET_CHAIN_IMPROVEMENTS.md`: Este archivo de documentación

## ✅ Estado del Sistema

El sistema de calibración en cascada está ahora completamente implementado y documentado, permitiendo:
- Identificación automática de sensores por ronda
- Cálculo de offsets en cadena con propagación de errores
- Documentación clara del proceso
- Preparación para futuras extensiones

El notebook `TREE.ipynb` ahora proporciona una demostración completa y funcional del sistema de calibración en cascada.
