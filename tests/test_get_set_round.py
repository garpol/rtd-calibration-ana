import yaml
import numpy as np

# Cargar configuración
with open('RTD_Calibration_VGP/config/sensors.yaml', 'r') as f:
    sensors_config = yaml.safe_load(f)

def get_set_round(set_id, config):
    """Obtiene la ronda de un set desde la configuración"""
    if not config or 'sensors' not in config:
        return None
    
    sets_data = config['sensors'].get('sets', {})
    
    # Intentar con diferentes tipos de clave
    for key_type in [int, float, str]:
        try:
            key = key_type(set_id)
            if key in sets_data:
                return sets_data[key].get('round')
        except (ValueError, TypeError):
            continue
    
    return None

# Test con diferentes tipos
test_cases = [
    (3, "int"),
    (np.int64(3), "np.int64"),
    (3.0, "float"),
    ("3", "str"),
]

print("Testing get_set_round():")
print(f"Keys in sets_data: {list(sensors_config['sensors']['sets'].keys())[:5]}")
print(f"Key types: {[type(k).__name__ for k in list(sensors_config['sensors']['sets'].keys())[:5]]}")
print()

for test_val, test_type in test_cases:
    result = get_set_round(test_val, sensors_config)
    print(f"get_set_round({test_type}({test_val})) = {result}")
