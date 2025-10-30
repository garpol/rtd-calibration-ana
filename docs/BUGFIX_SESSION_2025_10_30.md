# Bugfix Session - 30 October 2025

## Summary

Fixed 7 critical bugs preventing TREE.ipynb and calibration network from functioning correctly. All bugs stemmed from inconsistent type handling across Python, numpy, pandas, and YAML.

## Context

- **Goal**: Verify calibration_constants calculation and automatic R1→R2→R3 matching in TREE notebook
- **Test dataset**: Limited to 4 sets [3, 4, 49, 57] for debugging
- **Expected behavior**: 
  - Set 3 (R1) → Set 49 (R2) via raised sensors [48203, 48479]
  - Set 4 (R1) → Set 49 (R2) via raised sensors [48484, 48491]
  - Set 49 (R2) → Set 57 (R3/Reference)

## Bugs Fixed

### 1. isinstance() Not Recognizing Numpy Types
**File**: `RTD_Calibration_VGP/src/set.py` line 270  
**Symptom**: 0 runs grouped, all sets skipped  
**Root cause**: `pd.to_numeric()` converts strings to `np.int64`/`np.float64`, which `isinstance(x, (int, float))` doesn't recognize  
**Fix**: Added `np.integer, np.floating` to isinstance check

### 2. Config Lookup Type Mismatch
**File**: `RTD_Calibration_VGP/src/calibration_network.py` line 695  
**Symptom**: Raised sensors not found in YAML config  
**Root cause**: Searched with `str(key)` but YAML keys are `int`  
**Fix**: Use original key type without str() conversion

### 3. Wrong Data Source for Sensor Mappings
**File**: `TREE.ipynb` Celda 21 lines 1580-1600  
**Symptom**: Tree analysis detected 0 sets instead of 4  
**Root cause**: Used `set_handler.runs_by_set` (empty) instead of `sets_dict`  
**Fix**: Extract sensors from `sets_dict[set_num].calibration_constants.index`

### 4. String vs Int Comparison in Validation (Celda 23)
**File**: `TREE.ipynb` line 2050  
**Symptom**: Sensor matching failed in R2 validation  
**Root cause**: Compared `int` sensor IDs with `str` IDs from DataFrame  
**Fix**: Normalize both to `int` before comparison

### 5. String vs Int Comparison in Validation (Celda 3)
**File**: `TREE.ipynb` lines 523-531  
**Symptom**: "⚠️ No se encontró matching con sets R2"  
**Root cause**: YAML raised sensors are `int`, DataFrame index are `str`  
**Fix**: Normalize both to `str` before comparison

### 6. Function Used Before Definition
**File**: `TREE.ipynb` Celda 3 line 138  
**Symptom**: "⚠️ WARNING: 2 sets R1 SIN conexión a referencia"  
**Root cause**: `get_set_round()` called at line 415 but defined at line ~486  
**Fix**: Moved function definition to start of cell (after imports)

### 7. Non-Existent Method Name
**File**: `TREE.ipynb` Celda 3 line 457  
**Symptom**: AttributeError: 'CalibrationNetwork' object has no attribute 'find_path_to_reference'  
**Root cause**: Called non-existent method  
**Fix**: Changed to `find_path_between_sets(set_a, set_b)`

## Verification

After all fixes:
```
🔍 Validando conectividad del grafo...
   Set de referencia (R3): 57
   Total conexiones en grafo: 3
   Sets R1 conectados a referencia: 2/2

✅ Todos los sets R1 tienen conexión a la referencia

🔍 Verificando matching automático R1 → R2 → R3:
   Ejemplo: Set R1=3
   Sensores 'raised': [48203, 48479]
   ✅ Matching R2: [49]
```

## Key Lessons

1. **Type consistency is critical**: pandas, numpy, and Python native types must be handled explicitly
2. **YAML key types matter**: Don't assume string keys, check the actual type
3. **Define before use**: Python requires function definitions before first call
4. **API knowledge**: Verify method names exist before calling them
5. **Hidden errors**: `except: pass` masks important debugging information

## Files Modified

- `RTD_Calibration_VGP/src/set.py` - isinstance fix
- `RTD_Calibration_VGP/src/calibration_network.py` - config lookup fix
- `RTD_Calibration_VGP/notebooks/TREE.ipynb` - 5 fixes across multiple cells
- `README.md` - Added sensor config section and troubleshooting
- `FINAL_FIXES_SUMMARY.md` - Complete bug documentation

## Next Steps

1. **Translate code and comments to English**
   - Rename Spanish variables to English (e.g., `sets_ronda_1` → `sets_round_1`)
   - Translate print/log messages to English
   - Update code comments
   - Maintain consistency with international standards

2. **Expand test coverage to full dataset**
   - Remove TEST_SETS limitation
   - Process all available sets
   - Validate complete graph connectivity

3. **Refactor notebook functions**
   - Move `get_set_round()` to `CalibrationNetwork` class
   - Consolidate validations into reusable methods

4. **Improve type safety**
   - Add type hints to all functions
   - Create unit tests for type conversion edge cases
   - Document type conventions in README

## References

- Commit: `3c1b677` (develop branch)
- Full bug report: `FINAL_FIXES_SUMMARY.md`
- Configuration guide: `README.md` (Configuration section)
