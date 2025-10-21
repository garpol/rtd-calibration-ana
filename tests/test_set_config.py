import os
import os
import yaml
import pandas as pd
from RTD_Calibration_VGP.src.set import Set


def test_set_loads_yaml(tmp_path):
    # Prepare a small YAML config in tmp
    cfg = {
        'sensors': {
            'sets': {
                '100': {'discarded': [11111], 'raised': [22222], 'round': 1}
            }
        }
    }
    cfg_path = tmp_path / "sensors_test.yaml"
    with open(cfg_path, 'w') as f:
        yaml.safe_dump(cfg, f)

    # Minimal logfile DataFrame with required columns
    df = pd.DataFrame([{'Filename': 'dummy', 'Selection': '', 'CalibSetNumber': 100}])

    s = Set(df, config_path=str(cfg_path))
    assert isinstance(s.discarded_sensors, dict)
    assert 100.0 in s.discarded_sensors
    assert s.discarded_sensors[100.0] == [11111]
    assert s.sensors_raised_by_set[100.0] == [22222]
