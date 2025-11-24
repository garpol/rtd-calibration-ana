# Package shim to expose top-level modules in RTD_Calibration_VGP/src as
# the package `rtd_calibration_vgp` without moving existing files.
# It dynamically loads the existing module files into the package namespace.
import importlib.util
import importlib.machinery
import sys
from pathlib import Path

_pkg_src = Path(__file__).parent.parent  # points to RTD_Calibration_VGP/src
# Load utils first since other modules depend on it
_modules = ['utils', 'logfile', 'run', 'set']

for _m in _modules:
    _path = _pkg_src / f"{_m}.py"
    if _path.exists():
        spec = importlib.util.spec_from_file_location(f"rtd_calibration_vgp.{_m}", str(_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Register in sys.modules so normal imports work
        sys.modules[spec.name] = module
        # Expose the module in this package's globals
        globals()[_m] = module

# Re-export common names for convenience
# Access classes from the dynamically loaded modules (loaded in the loop above)
if 'logfile' in globals():
    Logfile = globals()['logfile'].Logfile
if 'run' in globals():
    Run = globals()['run'].Run
if 'set' in globals():
    Set = globals()['set'].Set

__all__ = ['Logfile', 'Run', 'Set']
