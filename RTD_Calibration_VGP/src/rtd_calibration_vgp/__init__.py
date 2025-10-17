# Package shim to expose top-level modules in RTD_Calibration_VGP/src as
# the package `rtd_calibration_vgp` without moving existing files.
# It dynamically loads the existing module files into the package namespace.
import importlib.util
import importlib.machinery
import sys
from pathlib import Path

_pkg_src = Path(__file__).parent.parent  # points to RTD_Calibration_VGP/src
_modules = ['logfile', 'run', 'set', 'utils']

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
try:
    from .logfile import Logfile  # type: ignore
except Exception:
    pass
try:
    from .run import Run  # type: ignore
except Exception:
    pass
try:
    from .set import Set  # type: ignore
except Exception:
    pass

__all__ = ['Logfile', 'Run', 'Set']
