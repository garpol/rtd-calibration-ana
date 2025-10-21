from RTD_Calibration_VGP.src.utils import load_config
from RTD_Calibration_VGP.src.set import Set
import pandas as pd


def test_set_loads_config(tmp_path):
    # load the repo config
    cfg = load_config("RTD_Calibration_VGP/config.yml")
    assert "sensors" in cfg

    # create a minimal logfile DataFrame with the required columns
    df = pd.DataFrame({
        "Filename": [],
        "Selection": [],
        "CalibSetNumber": [],
    })

    s = Set(df, config=cfg)

    # Check that some known sets are present in the mappings
    assert 3.0 in s.discarded_sensors
    assert 3.0 in s.sensors_raised_by_set
    assert 49.0 in s.set_rounds
    assert s.set_rounds[49.0] == 2