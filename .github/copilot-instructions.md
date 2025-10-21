# Copilot instructions for rtd-calibration-ana

Short, focused guidance to help an AI coding agent become productive in this repository.

- Project purpose: RTD calibration analysis. The main processing lives under `RTD_Calibration_VGP/src/` and uses a CSV "logfile" (`RTD_Calibration_VGP/data/LogFile.csv`) that lists runs and sensor IDs.

- Key modules:
  - `src/run.py` — Run-level loader and plotter. Important methods: `Run.load_temperature_file()`, `Run.associate_sensors()`, `Run.filter_faulty_channels()`, `Run.read_run_info()`, `Run.create_temperature_plot()` and `Run.create_offset_plot()`. Expect temperature files to be .txt files located under a CERNBox path hard-coded in `load_temperature_file()` (`/eos/user/j/jcapotor/RTDdata/`).
  - `src/set.py` — Groups multiple `Run` instances by `CalibSetNumber`, calculates offsets and repeatability, contains project-specific mappings (`discarded_sensors`, `sensors_raised_by_set`) and logic for reference sensor selection.
  - `src/logfile.py` — Simple wrapper to read `LogFile.csv` and select rows; functions used by `Set` and `Run` to find sensor IDs and run metadata.

- Data layout expectations:
  - `LogFile.csv` must contain columns used throughout the code: at minimum `Filename`, `Selection`, `CalibSetNumber`, `Date`, `N_Run`, and sensor columns named `S1`..`S20` (or similar). `Run.associate_sensors()` expects sensor columns `S1`..`S20` and maps them to channels `channel_1`..`channel_14`.
  - Temperature files: plain text, tab-separated, no header. Code expects columns `Date`, `Time`, `channel_1`..`channel_14` after loading.

- Conventions & patterns to follow when editing or extending:
  - Keep numeric sensor IDs as integers (many places use int(float(val))). When parsing the logfile use the same tolerant conversion pattern.
  - When adding new plotting or file IO, prefer returning DataFrames or simple dicts (existing code relies on Pandas objects). Avoid changing the public signatures of `Run`/`Set` methods without updating callers.
  - Hard-coded paths (CERNBox) are present in `Run.load_temperature_file()`; prefer making them configurable if adding features.

- Developer workflows (how to run/debug locally):
  - Entry points: `RTD_Calibration_VGP/main.py` is present but currently empty. Use small interactive scripts or notebooks in `/notebooks/` (e.g., `RUN.ipynb`) to drive the analysis.
  - Typical manual run pattern (example Python snippet to run in REPL or a script):

    from RTD_Calibration_VGP.src.logfile import Logfile
    from RTD_Calibration_VGP.src.set import Set

    lf = Logfile('RTD_Calibration_VGP/data/LogFile.csv')
    df = lf.log_file
    s = Set(df)
    s.group_runs_by_set(selected_sets=[3.0])
    s.calculate_offsets_and_rms()

  - If datasets are missing (temperature .txt files) the code prints errors; search for `/eos/user/j/jcapotor/RTDdata/` to find the expectation.

- Important implementation notes & gotchas (do not change silently):
  - `Run.load_temperature_file()` tries multiple date/time formats and will raise if any datetime rows remain NaT. Be careful when modifying parsing logic.
  - `associate_sensors()` builds a mapping from `channel_1..channel_14` -> sensor ID strings and then renames DataFrame columns to sensor IDs. Many downstream routines expect columns labelled by sensor ID strings.
  - `Set.group_runs_by_set()` excludes filenames containing 'pre', 'st', 'lar' and rows where `Selection == 'BAD'`. Maintain these filters if changing run selection logic.
  - `Set` contains manual per-set sensor lists (`discarded_sensors`, `sensors_raised_by_set`) — these are authoritative for reference selection and excluded sensors. Treat them as data rather than code; prefer editing the dictionaries rather than reworking logic.

- Tests and static checks:
  - There are no automated tests in the repo. When adding behavior, include a minimal pytest-compatible test under `tests/` that exercises `Run.load_temperature_file()` (mocking the file path) and `Set.group_runs_by_set()` using a small DataFrame.

- Useful grep/search targets for quick edits:
  - "CERNBox" or "/eos/user/j/jcapotor/RTDdata/" — temperature file location
  - "CalibSetNumber", "Filename", "Selection", "S1" — logfile column usage
  - "sensor_mapping" — where sensor to channel mapping is relied upon

If anything here is incorrect or you want more details (examples of the `LogFile.csv` header, typical .txt temperature file sample, or suggested tests), tell me which part to expand and I'll update the instructions.