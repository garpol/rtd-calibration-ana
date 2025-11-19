# DEWAR Analysis Module Documentation

## Overview

This module provides a reusable framework for analyzing Fiber Bragg Grating (FBG) and temperature data from DEWAR 1m calibration runs.

## Files

- **`dewar_analysis.py`**: Main Python module with classes and functions
- **`DEWAR_GENERAL_ANALYSIS.ipynb`**: General notebook demonstrating the module usage
- **`ROOT_DEWAR_*.ipynb`**: Individual run notebooks (historical)

## Key Components

### 1. Classes

#### `DewarDataLoader`
Handles loading and preprocessing ROOT data files.

```python
loader = DewarDataLoader(file_path, time_correction_hours=2.0)
loader.load_data()
```

**Key features:**
- Automatic timestamp conversion
- Time correction for peak data (+2h by default)
- Easy sensor data extraction

#### `DewarAnalyzer`
Performs analysis on loaded data.

```python
analyzer = DewarAnalyzer(loader, config)
peak_res, temp_res = analyzer.resample_sensor_data(sensor_idx, start_time, end_time)
```

**Key features:**
- Data resampling with statistics (mean, std, se)
- Weighted linear fitting (Temperature vs λB)
- Sensor offset calculations
- Residual analysis

#### `DewarPlotter`
Creates publication-quality plots.

```python
plotter = DewarPlotter(config)
fig = plotter.plot_time_series(peak_res, temp_res, sensor_name)
```

**Key features:**
- Time series plots (λB and Temperature)
- Scatter plots with fits
- Multi-sensor comparison plots
- Sensor offset plots

#### `SensorConfig`
Configuration container for sensor properties.

```python
config = SensorConfig(
    sensor_indices=[0, 2, 3, 4],  # Sensors 1, 3, 4, 5
    colors=["tab:blue", "tab:orange", "tab:green", "tab:red"]
)
```

### 2. Quick Analysis Function

For rapid single-sensor analysis:

```python
from dewar_analysis import quick_analysis

loader, analyzer, plotter, fit_results = quick_analysis(
    file_path="/path/to/file.root",
    date="2025-11-19",
    start_hour=16,
    end_hour=18,
    sensor_idx=2,  # Sensor 3
    resample_interval="5min"
)
```

## Usage Examples

### Example 1: Single Sensor Analysis

```python
import datetime
from dewar_analysis import DewarDataLoader, DewarAnalyzer, DewarPlotter

# Load data
loader = DewarDataLoader("/path/to/20251119.root")
loader.load_data()

# Define time window
start = datetime.datetime(2025, 11, 19, 16, 0, 0)
end = datetime.datetime(2025, 11, 19, 17, 30, 0)

# Analyze
analyzer = DewarAnalyzer(loader)
peak_res, temp_res = analyzer.resample_sensor_data(
    sensor_idx=2,  # Sensor 3
    start_time=start,
    end_time=end,
    resample_interval="5min"
)

# Fit
fit_results = analyzer.fit_temperature_vs_wavelength(peak_res, temp_res)
print(f"Slope: {fit_results['slope_mK_pm']:.2f} mK/pm")

# Plot
plotter = DewarPlotter()
plotter.plot_wavelength_vs_temperature(fit_results, "Sensor 3")
```

### Example 2: Multiple Sensors

```python
# Plot all sensors at once
sensor_indices = [0, 2, 3, 4]  # Sensors 1, 3, 4, 5
fig = plotter.plot_multiple_sensors_fit(
    analyzer, sensor_indices, start, end, resample_interval="2min"
)
```

### Example 3: Sensor Offsets

```python
# Compute offsets relative to Sensor 5
lambda_offsets, temp_offsets, peak_all, temp_all = analyzer.compute_sensor_offsets(
    start, end, resample_interval="2min", reference_sensor_idx=4
)

# Plot
plotter.plot_sensor_offsets(lambda_offsets, temp_offsets, peak_all, temp_all)

# Statistics
print(lambda_offsets.describe())
```

### Example 4: Batch Processing

```python
runs = [
    {"file": "20251107.root", "date": "2025-11-07", "start": 14, "end": 15},
    {"file": "20251119.root", "date": "2025-11-19", "start": 16, "end": 17},
]

results = {}
for run in runs:
    _, _, _, fit = quick_analysis(run["file"], run["date"], 
                                   run["start"], run["end"], sensor_idx=2)
    results[run["date"]] = fit["slope_mK_pm"]

# Compare slopes
for date, slope in results.items():
    print(f"{date}: {slope:.2f} mK/pm")
```

## Key Analysis Outputs

### Fit Results Dictionary

```python
fit_results = {
    'slope_K_nm': float,      # Slope in K/nm
    'slope_mK_pm': float,     # Slope in mK/pm
    'intercept_K': float,     # Intercept in K
    'x': np.ndarray,          # Wavelength data (nm)
    'y': np.ndarray,          # Temperature data (K)
    'yerr': np.ndarray,       # Temperature uncertainties
    'y_fit': np.ndarray,      # Fitted values
    'residuals': np.ndarray,  # Fit residuals
    'n_points': int           # Number of data points
}
```

### Resampled DataFrames

Resampled data has a MultiIndex structure:

```python
peak_resampled.columns = [('lambdaB_nm', 'mean'), ('lambdaB_nm', 'std'), ('lambdaB_nm', 'se')]
temp_resampled.columns = [('temp_K', 'mean'), ('temp_K', 'std'), ('temp_K', 'se')]
```

Access data:
```python
mean_lambda = peak_resampled['lambdaB_nm']['mean']
std_temp = temp_resampled['temp_K']['std']
```

## Sensor Configuration

### Default Sensor Mapping

- **Sensor 1** (index 0): Height 2m
- **Sensor 2** (index 1): Height 3m (often excluded from temperature)
- **Sensor 3** (index 2): Height 4m
- **Sensor 4** (index 3): Height 5m
- **Sensor 5** (index 4): Height 6m (often used as reference)

### Time Correction

Peak data timestamps require a +2 hour correction to align with temperature data. This is applied automatically by `DewarDataLoader`.

## Best Practices

1. **Always load data first**: Call `loader.load_data()` before analysis
2. **Check time ranges**: Print data intervals after loading
3. **Use appropriate resampling**: "2min" for detailed analysis, "5min" for overview
4. **Reference sensor**: Use Sensor 5 (index 4) as reference for offsets
5. **Error bars**: Always plot with error bars for publication
6. **Save results**: Export fitted parameters and plots for records

## Troubleshooting

### FileNotFoundError
- Check file path is correct
- Verify file exists on EOS

### Empty DataFrames after resampling
- Check time window overlaps with actual data
- Verify time correction is appropriate
- Print `loader.peak_timestamps.min()` and `.max()` to check range

### KeyError in sensor data
- Verify sensor index is valid (0-4 for 5 sensors)
- Check if sensor has data in the file

### Plotting errors
- Ensure data is not empty before plotting
- Check matplotlib backend is configured correctly

## Advanced Usage

### Custom Sensor Configuration

```python
from dewar_analysis import SensorConfig

config = SensorConfig(
    sensor_indices=[0, 2, 3],
    sensor_names=["Top", "Middle", "Bottom"],
    colors=["red", "green", "blue"],
    heights_fbg={"Top": 1.5, "Middle": 3.0, "Bottom": 4.5}
)
```

### Direct Data Access

```python
# Get raw data for custom analysis
lambdaB, peak_times, temp, temp_times = loader.get_sensor_data(sensor_idx=2)

# Apply custom filtering
custom_mask = (peak_times.hour >= 16) & (peak_times.hour < 18)
filtered_lambda = lambdaB[custom_mask]
```

### Custom Plots

```python
import matplotlib.pyplot as plt

# Create custom figure
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(fit_results['x'], fit_results['y'], label='Data')
ax.plot(fit_results['x'], fit_results['y_fit'], 'r--', label='Fit')
ax.set_xlabel('λB (nm)')
ax.set_ylabel('Temperature (K)')
ax.legend()
plt.show()
```

## Version History

- **v1.0** (2025-11-19): Initial release
  - Core classes: DataLoader, Analyzer, Plotter
  - Quick analysis function
  - Comprehensive plotting tools
  - Offset analysis

## Contact

For questions or issues, contact the DUNE HD Calibration Team.
