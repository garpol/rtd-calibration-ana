import os
import shutil
import pandas as pd
from RTD_Calibration_VGP.src.set import Set


def test_offset_repeatability_no_csv_xlsx(tmp_path):
    # Minimal fake logfile: CalibSetNumber integer-like and filenames
    df = pd.DataFrame({
        'Filename': ['file1.txt', 'file2.txt', 'file3.txt', 'file4.txt'],
        'CalibSetNumber': [1.0, 1.0, 1.0, 1.0],
        'Selection': ['OK', 'OK', 'OK', 'OK']
    })

    s = Set(df)
    # Build minimal fake Run-like objects with required attributes/methods
    class FakeRun:
        def __init__(self, filename):
            self.filename = filename
            # minimal sensor mapping with 14 channels mapped to string IDs
            self.sensor_mapping = {f'channel_{i+1}': str(1000 + i + 1) for i in range(14)}
            # create a dummy temperature_data DataFrame with datetime index
            idx = pd.date_range('2025-01-01', periods=60, freq='T')
            data = {str(1000 + i + 1): 20.0 + i*0.01 for i in range(14)}
            self.temperature_data = pd.DataFrame([data]*60, index=idx)
        def associate_sensors(self):
            return
        def offsets(self):
            # return 14x14 zeros
            import numpy as np
            return np.zeros((14,14))
        def stat_err_offsets(self):
            import numpy as np
            return np.ones((14,14))*0.001

    # populate runs_by_set with 4 runs (should be accepted)
    s.runs_by_set = {1.0: {f'file{i+1}.txt': FakeRun(f'file{i+1}.txt') for i in range(4)}}

    outdir = tmp_path / 'out'
    outdir_str = str(outdir)
    s.offset_repeatability(save_dir=outdir_str, write_csv=False, write_excel=False)

    # Check that no CSV/XLSX files were created
    files = list(outdir.rglob('*'))
    ext = [p.suffix.lower() for p in files if p.is_file()]
    assert '.csv' not in ext
    assert '.xlsx' not in ext

    # But PNGs should exist
    pngs = [p for p in files if p.suffix.lower() == '.png']
    assert len(pngs) > 0
