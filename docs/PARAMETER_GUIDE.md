# Parameter Modification Guide

Quick reference for common parameter modifications in RTD calibration analysis.

## 🎯 Quick Parameter Lookup

| What you want to change | File | Function/Line | Parameter |
|-------------------------|------|---------------|-----------|
| Time window for offsets | `set.py` | `offset_repeatability()` | `tini`, `tend` |
| Reference sensor | `set.py` | `offset_repeatability()` | `ref` |
| IQR outlier threshold | `set.py` | ~line 600 | IQR multiplier (3×) |
| Include BAD runs | Notebook | Cell 3 | `INCLUDE_BAD_RUNS` |
| Liquid media filter | Notebook | Cell 3 | `LIQUID_MEDIA_FILTER` |
| Min runs per set | Notebook | Cell 3 | `MIN_RUNS_PER_SET` |
| Output directory | Any function call | — | `save_dir` |
| Discard specific sensors | `set.py` | `discarded_sensors` dict | Add set: sensor list |
| Faulty channel thresholds | `run.py` | `filter_faulty_channels()` | Temp range, NaN count |
| Temperature file path | `run.py` | `load_temperature_file()` | `cernbox_base` |

---

## 📘 Detailed Examples

### Example 1: Analyze only GOOD runs with 30-60s time window

**File:** `ANALYSIS_ALL_SETS_LN2.ipynb`

**Cell 3 — Configuration:**
```python
INCLUDE_BAD_RUNS = False  # ← Changed from True
MIN_RUNS_PER_SET = 4
LIQUID_MEDIA_FILTER = 'LN2'
OUTPUT_DIR = 'outputs/analysis_good_runs_only'  # ← Custom name
```

**Cell 6 — Function definition (modify analyze_all_sets_with_filters):**
```python
set_instance.offset_repeatability(
    selected_sets=[float(cs)],
    ref=2,
    tini=30,              # ← Changed from 20
    tend=60,              # ← Changed from 40
    save_dir=set_save_dir,
    write_csv=False,
    write_excel=False
)
```

**Expected result:** Only sets with ≥4 GOOD runs processed, using 30-60 second window.

---

### Example 2: Use stricter outlier filtering (2×IQR instead of 3×IQR)

**File:** `set.py`

**Function:** `offset_repeatability()` around line 600

**Change:**
```python
# Before:
lower_bound = q1 - 3 * iqr
upper_bound = q3 + 3 * iqr

# After:
lower_bound = q1 - 2 * iqr  # ← Stricter
upper_bound = q3 + 2 * iqr  # ← Stricter
```

**Don't forget:** Reload module in notebook before re-running:
```python
import importlib
from RTD_Calibration_VGP.src import set as set_module
importlib.reload(set_module)
from RTD_Calibration_VGP.src.set import Set
```

**Expected result:** More measurements flagged as outliers in `outliers_filtered_by_iqr.csv`.

---

### Example 3: Discard sensor 5 from Set 42

**File:** `set.py`

**Location:** `__init__` method, `discarded_sensors` dictionary (around line 130)

**Change:**
```python
self.discarded_sensors = {
    3.0: [8],
    4.0: [8, 14],
    5.0: [8],
    # ... existing entries ...
    42.0: [5],  # ← Add this line
}
```

**Expected result:** Sensor 5 excluded from Set 42 calculations and plots.

---

### Example 4: Change temperature valid range

**File:** `run.py`

**Function:** `filter_faulty_channels()` around line 260

**Change:**
```python
# Before:
valid_temp = (temp >= 70) & (temp <= 320)

# After:
valid_temp = (temp >= 60) & (temp <= 350)  # ← Wider range
```

**Expected result:** Channels with temperatures 60-70K or 320-350K no longer filtered out.

---

### Example 5: Analyze only LAr runs

**File:** `ANALYSIS_ALL_SETS_LN2.ipynb`

**Cell 3 — Configuration:**
```python
INCLUDE_BAD_RUNS = True
MIN_RUNS_PER_SET = 4
LIQUID_MEDIA_FILTER = 'LAr'  # ← Changed from 'LN2'
OUTPUT_DIR = 'outputs/analysis_LAr_runs'  # ← Descriptive name
```

**Expected result:** Only runs with `Liquid Media == 'LAr'` processed.

---

### Example 6: Use sensor 7 as reference for all sets

**File:** Notebook calling `offset_repeatability()`

**Change:**
```python
s.offset_repeatability(
    selected_sets=[3.0, 4.0, 5.0],
    ref=7,  # ← Changed from 2 or 'auto'
    save_dir='outputs/ref_sensor_7',
    write_csv=False,
    write_excel=False
)
```

**Expected result:** All offsets calculated relative to sensor at position 7.

---

### Example 7: Process sets with minimum 3 runs (instead of 4)

**File:** `ANALYSIS_ALL_SETS_LN2.ipynb`

**Cell 3 — Configuration:**
```python
MIN_RUNS_PER_SET = 3  # ← Changed from 4
```

**Expected result:** More sets eligible for processing (any with ≥3 runs).

---

### Example 8: Analyze specific date range only

**File:** Notebook custom filtering

**Add after loading logfile:**
```python
# After: lf = Logfile(str(logfile_path))
df_original = lf.log_file.copy()

# Add date filtering
df_original['Date'] = pd.to_datetime(df_original['Date'], errors='coerce')
df_original = df_original[
    (df_original['Date'] >= '2022-05-01') & 
    (df_original['Date'] <= '2022-06-30')
]
lf.log_file = df_original  # Update logfile
```

**Expected result:** Only runs from May-June 2022 processed.

---

### Example 9: Change temperature file base path

**File:** `run.py`

**Function:** `load_temperature_file()` around line 170

**Change:**
```python
# Before:
cernbox_base = Path('/eos/user/j/jcapotor/RTDdata/')

# After:
cernbox_base = Path('/your/custom/path/RTDdata/')
```

**Alternative (without code change):**
```bash
# Create symlink to your actual data location
sudo ln -s /your/actual/data/path /eos/user/j/jcapotor/RTDdata
```

---

### Example 10: Generate CSV summaries (re-enable CSV export)

**File:** Notebook calling `offset_repeatability()`

**Change:**
```python
s.offset_repeatability(
    selected_sets=[3.0],
    ref=2,
    save_dir='outputs/with_csv',
    write_csv=True,    # ← Changed from False
    write_excel=True   # ← Changed from False
)
```

**Expected result:** CSV and Excel files generated alongside plots.

---

## 🔍 Parameter Impact Summary

| Parameter | Low value → High value | Impact |
|-----------|----------------------|--------|
| `tini`, `tend` | Narrow window → Wide window | Less stable data → More data points |
| IQR multiplier | 2× → 4× | More outliers → Fewer outliers filtered |
| `MIN_RUNS_PER_SET` | 3 → 6 | More sets → Fewer sets, higher quality |
| NaN threshold | 20 → 60 | More channels filtered → More channels kept |
| Temperature range | 70-320K → 50-350K | More channels filtered → More channels kept |

---

## ⚠️ Important Reminders

1. **Always reload modules** after editing `src/` code:
   ```python
   import importlib
   from RTD_Calibration_VGP.src import set as set_module
   importlib.reload(set_module)
   ```

2. **Use descriptive output directories** for different analyses:
   ```python
   save_dir='outputs/test_stricter_iqr_20221015'
   ```

3. **Check logs** after changes:
   - `skipped_runs_due_to_defects.csv` — Filtered channels
   - `outliers_filtered_by_iqr.csv` — Statistical outliers

4. **Backup before major changes:**
   ```bash
   cp RTD_Calibration_VGP/src/set.py RTD_Calibration_VGP/src/set.py.backup
   ```

5. **Document your changes** in notebook markdown cells

---

## 📊 Before/After Comparison Template

When testing parameter changes, use this template:

```python
# ============= BASELINE =============
s_baseline = Set(lf.log_file)
s_baseline.group_runs_by_set(selected_sets=[3.0])
s_baseline.calculate_offsets_and_rms()
s_baseline.offset_repeatability(
    tini=20, tend=40, ref=2,
    save_dir='outputs/comparison/baseline',
    write_csv=False, write_excel=False
)

# ============= MODIFIED =============
s_modified = Set(lf.log_file)
s_modified.group_runs_by_set(selected_sets=[3.0])
s_modified.calculate_offsets_and_rms()
s_modified.offset_repeatability(
    tini=30, tend=60, ref=2,  # ← Your changes
    save_dir='outputs/comparison/modified',
    write_csv=False, write_excel=False
)

# Compare results
print("Baseline stats:", s_baseline.global_stats)
print("Modified stats:", s_modified.global_stats)
```

---

## 🆘 Getting Help

If a parameter modification doesn't work as expected:

1. **Check the README:** `RTD_Calibration_VGP/notebooks/README.md` — Full documentation
2. **Read source code docstrings:** Each function has usage examples
3. **Review logs:** CSV files show what was filtered/excluded
4. **Test on single set first:** Use `selected_sets=[3.0]` before processing all
5. **Check notebook output:** Look for warnings/errors in cell output

---

## 📝 Contributing Your Modifications

If you create a useful parameter configuration:

1. Document it in this file under "Detailed Examples"
2. Create a notebook cell with the configuration
3. Add before/after comparison plots
4. Update the quick lookup table at the top

Example contribution:
```markdown
### Example 11: Your modification title

**Use case:** Brief description

**Changes:**
- File X, line Y: change A to B
- Rationale: why this helps

**Expected result:** What you'll see

**Plots:** Link or embed comparison
```
