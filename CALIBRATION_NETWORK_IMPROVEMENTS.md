# Mejoras en CalibrationNetwork

## Resumen de Cambios Realizados

Se han implementado mejoras significativas en el archivo `calibration_network.py` para mejorar la integración con el sistema de configuración y mantener coherencia con las clases `Set` y `Run`.

## 1. Integración con Sistema de Configuración

### Antes:
- Carga manual de configuración YAML
- No uso del sistema `utils.py`
- Configuración hardcodeada

### Después:
- Uso del sistema `load_config` de `utils.py`
- Soporte para configuración dict y archivo
- Fallback a configuración por defecto
- Manejo robusto de errores de configuración

```python
# Nuevo constructor mejorado
def __init__(self, sets_dict: Dict[float, Any], config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> None:
    # Load configuration using the same pattern as Set and Run classes
    try:
        if config is not None:
            self.config = config
        elif config_path:
            self.config = load_config(config_path)
        else:
            self.config = DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.warning(f"Could not load configuration: {e}. Using defaults.")
        self.config = DEFAULT_CONFIG.copy()
```

## 2. Eliminación de Valores Hardcodeados

### Antes:
```python
# Lógica hardcodeada para detectar rounds
if 3 <= s <= 39:
    round_by_set[s] = 1
elif 49 <= s <= 54:
    round_by_set[s] = 2
elif s == 57:
    round_by_set[s] = 3
```

### Después:
```python
# Uso de configuración para detectar rounds
round_by_set[s] = self._get_set_round(s)

def _get_set_round(self, set_id: float) -> int:
    """Get the round number for a given set ID from configuration."""
    sensors_config = self.config.get("sensors", {})
    sets_config = sensors_config.get("sets", {})
    if sets_config:
        set_data = sets_config.get(str(set_id), {})
        return set_data.get("round", 1)
    # Fallback logic...
```

## 3. Interfaz Consistente con Set y Run

### Nuevos Métodos Añadidos:

#### `from_sets()` - Constructor Alternativo
```python
@classmethod
def from_sets(cls, sets_list: List[Any], config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> 'CalibrationNetwork':
    """Create a CalibrationNetwork from a list of Set objects."""
```

#### `get_sets_by_round()` - Filtrado por Ronda
```python
def get_sets_by_round(self, round_number: int) -> List[float]:
    """Get all sets that belong to a specific round."""
```

#### `get_reference_set()` - Detección Automática de Referencia
```python
def get_reference_set(self) -> Optional[float]:
    """Get the reference set (typically the highest round set)."""
```

#### `validate_sets_structure()` - Validación
```python
def validate_sets_structure(self) -> Dict[str, List[str]]:
    """Validate that all sets have the required structure."""
```

## 4. Manejo Mejorado de Errores

### Antes:
- Manejo básico de errores
- Logging inconsistente

### Después:
- Validación robusta de entrada
- Manejo específico de diferentes tipos de errores
- Logging detallado y consistente

```python
# Validación de entrada
if not isinstance(sets_dict, dict):
    raise TypeError("sets_dict must be a dictionary")

if not sets_dict:
    logger.warning("No sets provided in sets_dict")

# Manejo específico de errores
try:
    set_id = float(set_id_str)
except (ValueError, TypeError) as e:
    logger.warning(f"Invalid set ID '{set_id_str}': {e}")
    continue
```

## 5. Lógica de Construcción de Grafo Modular

### Antes:
- Método monolítico `_build_graph_from_config()`
- Lógica difícil de mantener y testear

### Después:
- Descomposición en métodos especializados:
  - `_extract_sets_configuration()`
  - `_build_graph_edges()`
  - `_connect_to_next_round()`
  - `_find_bridge_sensors()`

```python
def _build_graph_from_config(self) -> None:
    """Main method that orchestrates graph building."""
    sets_config = self._extract_sets_configuration()
    edges_added = self._build_graph_edges(sets_config)
    logger.info(f"Graph built with {len(self.graph.nodes)} sets and {edges_added} connections.")
```

## 6. Mejoras en Type Hints

### Antes:
```python
def __init__(self, sets_dict: Dict[float, object], config_path: Optional[str] = None):
```

### Después:
```python
def __init__(self, sets_dict: Dict[float, Any], config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> None:
```

## Beneficios de las Mejoras

1. **Configurabilidad**: El sistema ahora puede usar diferentes configuraciones sin modificar código
2. **Mantenibilidad**: Código más modular y fácil de entender
3. **Robustez**: Mejor manejo de errores y casos edge
4. **Consistencia**: Interfaz coherente con otras clases del sistema
5. **Flexibilidad**: Soporte para diferentes fuentes de configuración
6. **Testabilidad**: Métodos más pequeños y específicos

## Uso Recomendado

```python
# Crear red desde configuración
network = CalibrationNetwork(sets_dict, config_path="config.yml")

# Crear red desde objetos Set
network = CalibrationNetwork.from_sets(sets_list, config_path="config.yml")

# Validar estructura
issues = network.validate_sets_structure()
if issues["missing_constants"]:
    print(f"Sets missing constants: {issues['missing_constants']}")

# Obtener sets por ronda
round_1_sets = network.get_sets_by_round(1)
reference_set = network.get_reference_set()
```

## Compatibilidad

Las mejoras mantienen compatibilidad hacia atrás con el código existente, pero se recomienda migrar al nuevo patrón de configuración para aprovechar todas las funcionalidades.
