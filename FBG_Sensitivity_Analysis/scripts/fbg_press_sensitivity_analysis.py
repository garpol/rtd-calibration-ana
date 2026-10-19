"""
FBG Sensitivity Analysis Library
=================================
Library for analyzing Fiber Bragg Grating (FBG) thermal sensitivity 
in pressure experiments with PEEK-7 fiber.

Author: Victor Garcia
Date: November 2025

Usage:
------
# Run from terminal with automatic plateau detection:
python fbg_press_sensitivity_analysis.py --file /path/to/data.root --auto-plateaus

# Run with manual plateau times:
python fbg_press_sensitivity_analysis.py --file /path/to/data.root --plateaus "14:50-15:13,15:30-15:52"

# Run with custom parameters:
python fbg_press_sensitivity_analysis.py --file /path/to/data.root --auto-plateaus --tolerance 0.01 --min-length 500
"""

import numpy as np
import datetime
from scipy import stats
from typing import Dict, List, Tuple, Any, Optional
import argparse
import sys

# Try to import uproot, provide helpful error if not available
try:
    import uproot
except ImportError:
    print("ERROR: uproot not installed. Install with: pip install uproot")
    print("In SWAN/Jupyter environment, run: !pip install uproot")
    sys.exit(1)


# ============================================================================
# DATA LOADING AND PREPROCESSING
# ============================================================================

def load_root_data(filepath: str) -> Dict[str, np.ndarray]:
    """
    Load ROOT file data using uproot.
    
    Parameters:
    -----------
    filepath : str
        Path to the ROOT file
        
    Returns:
    --------
    dict : Dictionary containing times, pressure, temperature, and wavelength data
    """
    with uproot.open(filepath) as file:
        tree = file["resampled_data"]
        data = tree.arrays(library="np")
    
    return {
        "times": data["t"],
        "press": data["press"],
        "temp": data["temp"],
        "wav": data["wav"]
    }


def convert_timestamps(times: np.ndarray) -> np.ndarray:
    """
    Convert Unix timestamps to datetime objects.
    
    Parameters:
    -----------
    times : np.ndarray
        Array of Unix timestamps
        
    Returns:
    --------
    np.ndarray : Array of datetime objects
    """
    return np.array([datetime.datetime.utcfromtimestamp(float(t)) for t in times])


# ============================================================================
# FBG WAVELENGTH FILTERING
# ============================================================================

def filter_wavelength_data(wav_data: np.ndarray, 
                          timestamps: np.ndarray,
                          sigma_threshold: float = 3.0) -> Dict[str, Any]:
    """
    Filter wavelength data using automatic outlier detection (μ±3σ method).
    
    Parameters:
    -----------
    wav_data : np.ndarray
        Raw wavelength data
    timestamps : np.ndarray
        Corresponding timestamps
    sigma_threshold : float
        Number of standard deviations for outlier detection (default: 3.0)
        
    Returns:
    --------
    dict : Filtered data with statistics
    """
    # Step 1: Remove sentinels and negative values
    mask_positive = wav_data > 0
    wav_positive = wav_data[mask_positive]
    
    # Step 2: Calculate thresholds (mean ± sigma_threshold*std)
    mean_wav = np.mean(wav_positive)
    std_wav = np.std(wav_positive)
    threshold_min = mean_wav - sigma_threshold * std_wav
    threshold_max = mean_wav + sigma_threshold * std_wav
    
    # Step 3: Apply complete filter
    mask_filtered = (wav_data > 0) & (wav_data >= threshold_min) & (wav_data <= threshold_max)
    
    return {
        "timestamps": timestamps[mask_filtered],
        "wavelength": wav_data[mask_filtered],
        "mean": mean_wav,
        "std": std_wav,
        "threshold_min": threshold_min,
        "threshold_max": threshold_max,
        "n_valid": np.sum(mask_filtered),
        "n_total": len(wav_data)
    }


def process_all_fbg_sensors(wav_array: np.ndarray, 
                            timestamps: np.ndarray,
                            fbg_config: List[Dict]) -> Dict[str, Dict]:
    """
    Process all FBG sensors and polarizations.
    
    Parameters:
    -----------
    wav_array : np.ndarray
        3D array of wavelength data [time, polarization, sensor]
    timestamps : np.ndarray
        Array of datetime objects
    fbg_config : list
        List of sensor configuration dictionaries
        
    Returns:
    --------
    dict : Filtered data for each sensor/polarization
    """
    filtered_data = {}
    
    for cfg in fbg_config:
        pol, sensor, label = cfg["pol"], cfg["sensor"], cfg["label"]
        wav_data = wav_array[:, pol, sensor]
        filtered_data[label] = filter_wavelength_data(wav_data, timestamps)
    
    return filtered_data


# ============================================================================
# TEMPERATURE DATA FILTERING
# ============================================================================

def filter_temperature_data(temp_array: np.ndarray, 
                           timestamps: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Filter temperature data by removing invalid values (≤0).
    
    Parameters:
    -----------
    temp_array : np.ndarray
        2D array of temperature data [time, sensor]
    timestamps : np.ndarray
        Array of datetime objects
        
    Returns:
    --------
    tuple : (filtered_timestamps, filtered_temp)
    """
    # Filter out entries where ANY sensor has invalid values
    mask_valid = np.all(temp_array > 0, axis=1)
    return timestamps[mask_valid], temp_array[mask_valid]


# ============================================================================
# TEMPORAL SHIFT CORRECTION
# ============================================================================

def apply_time_shift(filtered_data: Dict[str, Dict], 
                    time_shift_hours: float = 1.0) -> Dict[str, Dict]:
    """
    Apply temporal shift to wavelength timestamps.
    
    Parameters:
    -----------
    filtered_data : dict
        Dictionary of filtered wavelength data
    time_shift_hours : float
        Time shift in hours (default: 1.0)
        
    Returns:
    --------
    dict : Data with shifted timestamps
    """
    time_shift = datetime.timedelta(hours=time_shift_hours)
    shifted_data = {}
    
    for label, data in filtered_data.items():
        shifted_data[label] = {
            "timestamps": data["timestamps"] + time_shift,
            "wavelength": data["wavelength"],
            "mean": data["mean"],
            "std": data["std"],
            "threshold_min": data["threshold_min"],
            "threshold_max": data["threshold_max"],
            "n_valid": data["n_valid"],
            "n_total": data["n_total"]
        }
    
    return shifted_data


# ============================================================================
# PLATEAU DETECTION AND ANALYSIS
# ============================================================================

def find_plateaus(values: np.ndarray, 
                 times: np.ndarray, 
                 tolerance: float = 0.01, 
                 min_plateau_length: float = 500) -> List[Dict[str, Any]]:
    """
    Encuentra plateaus automáticamente en los datos.
    
    Parameters:
    -----------
    values : np.ndarray
        Array de valores (e.g., temperatura o presión)
    times : np.ndarray
        Array de timestamps (datetime objects)
    tolerance : float
        Tolerancia relativa (porcentaje de variación permitida, default: 0.01 = 1%)
    min_plateau_length : float
        Duración mínima del plateau en segundos (default: 500)
        
    Returns:
    --------
    list : Lista de plateaus detectados con t0, tfin, mean, std, data
    """
    plateaus = []
    start_idx = 0

    for i in range(1, len(values)):
        # Tolerancia relativa basada en el primer valor del plateau
        threshold = abs(values[start_idx]) * tolerance

        # Si la variación supera el % permitido, cerramos el plateau
        if abs(values[i] - values[start_idx]) > threshold:
            duration_seconds = (times[i - 1] - times[start_idx]).total_seconds()
            
            if duration_seconds >= min_plateau_length:
                segment = values[start_idx:i]
                plateaus.append({
                    "t0": times[start_idx],
                    "tfin": times[i - 1],
                    "mean": np.mean(segment),
                    "std": np.std(segment),
                    "data": segment
                })
            
            start_idx = i  # Reiniciar búsqueda de un nuevo plateau
    
    # Check last segment
    duration_seconds = (times[-1] - times[start_idx]).total_seconds()
    if duration_seconds >= min_plateau_length:
        segment = values[start_idx:]
        plateaus.append({
            "t0": times[start_idx],
            "tfin": times[-1],
            "mean": np.mean(segment),
            "std": np.std(segment),
            "data": segment
        })
    
    return plateaus


def convert_plateaus_to_dict(plateaus_list: List[Dict[str, Any]]) -> Dict[str, Dict]:
    """
    Convierte lista de plateaus a formato diccionario para análisis.
    
    Parameters:
    -----------
    plateaus_list : list
        Lista de plateaus de find_plateaus()
        
    Returns:
    --------
    dict : Plateaus en formato {"Plateau 1": {"start": time, "end": time}, ...}
    """
    plateau_dict = {}
    
    for idx, plateau in enumerate(plateaus_list):
        plateau_dict[f"Plateau {idx + 1}"] = {
            "start": plateau["t0"].time(),
            "end": plateau["tfin"].time()
        }
    
    return plateau_dict


def define_plateaus(plateau_times: List[Tuple[str, str, str]]) -> Dict[str, Dict]:
    """
    Define plateau time windows.
    
    Parameters:
    -----------
    plateau_times : list
        List of tuples (name, start_time, end_time) where times are "HH:MM" format
        
    Returns:
    --------
    dict : Plateau definitions with datetime.time objects
    """
    plateaus = {}
    
    for name, start_str, end_str in plateau_times:
        start_hour, start_min = map(int, start_str.split(':'))
        end_hour, end_min = map(int, end_str.split(':'))
        
        plateaus[name] = {
            "start": datetime.time(start_hour, start_min),
            "end": datetime.time(end_hour, end_min)
        }
    
    return plateaus


def calculate_plateau_means(plateaus: Dict[str, Dict],
                            filtered_data_shifted: Dict[str, Dict],
                            temp_filtered: np.ndarray,
                            timestamps_temp: np.ndarray,
                            press: np.ndarray,
                            timestamps_press: np.ndarray,
                            fbg_config: List[Dict],
                            rtd_config: List[Dict]) -> Dict[str, Dict]:
    """
    Calculate mean values for each plateau.
    
    Parameters:
    -----------
    plateaus : dict
        Plateau time window definitions
    filtered_data_shifted : dict
        Filtered wavelength data with time shift applied
    temp_filtered : np.ndarray
        Filtered temperature data
    timestamps_temp : np.ndarray
        Temperature timestamps
    press : np.ndarray
        Pressure data
    timestamps_press : np.ndarray
        Pressure timestamps
    fbg_config : list
        FBG sensor configuration
    rtd_config : list
        RTD sensor configuration
        
    Returns:
    --------
    dict : Mean values and statistics for each plateau
    """
    plateau_results = {}
    
    for plateau_name, times in plateaus.items():
        plateau_results[plateau_name] = {
            "time_start": times["start"],
            "time_end": times["end"],
            "wavelength": {},
            "temperature": {},
            "pressure": None
        }
        
        # 1. FBG Wavelength means
        for cfg in fbg_config:
            label = cfg["label"]
            data_source = filtered_data_shifted[label]
            
            mask_window = np.array([times["start"] <= t.time() <= times["end"] 
                                   for t in data_source["timestamps"]])
            wav_window = data_source["wavelength"][mask_window]
            
            if len(wav_window) > 0:
                plateau_results[plateau_name]["wavelength"][label] = {
                    "mean": np.mean(wav_window),
                    "std": np.std(wav_window),
                    "n_points": len(wav_window)
                }
        
        # 2. RTD Temperature means
        mask_temp_window = np.array([times["start"] <= t.time() <= times["end"] 
                                     for t in timestamps_temp])
        temp_window = temp_filtered[mask_temp_window]
        
        if len(temp_window) > 0:
            for cfg in rtd_config:
                sensor_id = cfg["id"]
                label = cfg["label"]
                temp_sensor_window = temp_window[:, sensor_id]
                
                plateau_results[plateau_name]["temperature"][label] = {
                    "mean": np.mean(temp_sensor_window),
                    "std": np.std(temp_sensor_window),
                    "n_points": len(temp_sensor_window)
                }
        
        # 3. Pressure means
        mask_press_window = np.array([times["start"] <= t.time() <= times["end"] 
                                      for t in timestamps_press])
        press_window = press[mask_press_window]
        
        if len(press_window) > 0:
            plateau_results[plateau_name]["pressure"] = {
                "mean": np.mean(press_window),
                "std": np.std(press_window),
                "n_points": len(press_window)
            }
    
    return plateau_results


# ============================================================================
# SENSITIVITY ANALYSIS
# ============================================================================

def calculate_thermal_sensitivity(plateau_results: Dict[str, Dict],
                                  sensor_label_wav: str,
                                  sensor_label_temp: str) -> Dict[str, Any]:
    """
    Calculate thermal sensitivity (Δλ/ΔT) using linear regression.
    
    Parameters:
    -----------
    plateau_results : dict
        Plateau mean values
    sensor_label_wav : str
        FBG sensor label (e.g., "FBG-1-P")
    sensor_label_temp : str
        RTD sensor label (e.g., "RTD-7")
        
    Returns:
    --------
    dict : Sensitivity results including slope, R², p-value
    """
    wavelength_means = []
    wavelength_stds = []
    temperature_means = []
    temperature_stds = []
    
    for results in plateau_results.values():
        wav_mean = results["wavelength"][sensor_label_wav]["mean"]
        wav_std = results["wavelength"][sensor_label_wav]["std"]
        temp_mean = results["temperature"][sensor_label_temp]["mean"]
        temp_std = results["temperature"][sensor_label_temp]["std"]
        
        wavelength_means.append(wav_mean * 1e12)  # Convert to pm
        wavelength_stds.append(wav_std * 1e12)
        temperature_means.append(temp_mean)
        temperature_stds.append(temp_std)
    
    # Linear regression
    wavelength_means = np.array(wavelength_means)
    temperature_means = np.array(temperature_means)
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        temperature_means, wavelength_means
    )
    
    return {
        "slope_pm_K": slope,
        "intercept_pm": intercept,
        "r_squared": r_value**2,
        "p_value": p_value,
        "std_err": std_err,
        "wavelength_means": wavelength_means,
        "wavelength_stds": np.array(wavelength_stds),
        "temperature_means": temperature_means,
        "temperature_stds": np.array(temperature_stds)
    }


def calculate_all_sensitivities(plateau_results: Dict[str, Dict],
                                fbg_config: List[Dict],
                                temp_sensors: List[str]) -> Dict[str, Dict]:
    """
    Calculate thermal sensitivity for all FBG sensors vs all temp sensors.
    
    Parameters:
    -----------
    plateau_results : dict
        Plateau mean values
    fbg_config : list
        FBG sensor configuration
    temp_sensors : list
        List of temperature sensor labels
        
    Returns:
    --------
    dict : Sensitivity results for all combinations
    """
    sensitivity_results = {}
    
    for cfg in fbg_config:
        label_wav = cfg["label"]
        sensitivity_results[label_wav] = {}
        
        for temp_label in temp_sensors:
            result = calculate_thermal_sensitivity(
                plateau_results, label_wav, temp_label
            )
            sensitivity_results[label_wav][temp_label] = result
    
    return sensitivity_results


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_default_fbg_config() -> List[Dict]:
    """Get default FBG sensor configuration."""
    return [
        {"pol": 0, "sensor": 0, "label": "FBG-1-P", "color": "blue"},
        {"pol": 1, "sensor": 0, "label": "FBG-1-S", "color": "cyan"},
        {"pol": 0, "sensor": 1, "label": "FBG-2-P", "color": "green"},
        {"pol": 1, "sensor": 1, "label": "FBG-2-S", "color": "lime"},
        {"pol": 0, "sensor": 2, "label": "FBG-3-P", "color": "red"},
        {"pol": 1, "sensor": 2, "label": "FBG-3-S", "color": "orange"},
    ]


def get_default_rtd_config() -> List[Dict]:
    """Get default RTD sensor configuration."""
    return [
        {"id": 0, "label": "RTD-1", "location": "External", "color": "blue"},
        {"id": 1, "label": "RTD-2", "location": "External", "color": "cyan"},
        {"id": 2, "label": "RTD-3", "location": "External", "color": "green"},
        {"id": 3, "label": "RTD-4", "location": "External", "color": "lime"},
        {"id": 6, "label": "RTD-7", "location": "Internal", "color": "purple"},
        {"id": 7, "label": "RTD-8", "location": "Internal", "color": "magenta"},
    ]


def print_sensitivity_summary(sensitivity_results: Dict[str, Dict], 
                             fbg_config: List[Dict],
                             temp_sensors: List[str]) -> None:
    """
    Print formatted summary table of sensitivities.
    
    Parameters:
    -----------
    sensitivity_results : dict
        Sensitivity calculation results
    fbg_config : list
        FBG sensor configuration
    temp_sensors : list
        List of temperature sensor labels
    """
    print("=" * 80)
    print("THERMAL SENSITIVITY SUMMARY")
    print("=" * 80)
    
    # Print header
    header = f"{'FBG Sensor':<12} {'Pol':<4} {'S#':<3}"
    for temp_label in temp_sensors:
        header += f" {temp_label} (pm/K)  {temp_label} R²     "
    print("\n" + header)
    print("-" * 80)
    
    # Print data rows
    for cfg in fbg_config:
        label = cfg["label"]
        pol_name = "P" if cfg["pol"] == 0 else "S"
        sensor_num = cfg["sensor"] + 1
        
        row = f"{label:<12} {pol_name:<4} {sensor_num:<3}"
        
        for temp_label in temp_sensors:
            if label in sensitivity_results and temp_label in sensitivity_results[label]:
                data = sensitivity_results[label][temp_label]
                sens = f"{data['slope_pm_K']:.2f}"
                r2 = f"{data['r_squared']:.4f}"
                row += f" {sens:<13} {r2:<10}"
            else:
                row += f" {'N/A':<13} {'N/A':<10}"
        
        print(row)
    
    print("=" * 80)


# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def run_analysis(filepath: str, 
                plateau_times: Optional[List[Tuple[str, str, str]]] = None,
                auto_plateaus: bool = False,
                tolerance: float = 0.01,
                min_plateau_length: float = 500,
                time_shift_hours: float = 1.0,
                temp_sensors: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Ejecuta el análisis completo de sensibilidad térmica.
    
    Parameters:
    -----------
    filepath : str
        Path al archivo ROOT
    plateau_times : list, optional
        Lista de tuplas (name, start_time, end_time) para plateaus manuales
    auto_plateaus : bool
        Si True, detecta plateaus automáticamente de presión
    tolerance : float
        Tolerancia para detección automática de plateaus (default: 0.01)
    min_plateau_length : float
        Longitud mínima de plateau en segundos (default: 500)
    time_shift_hours : float
        Corrección temporal en horas (default: 1.0)
    temp_sensors : list, optional
        Lista de sensores de temperatura a usar (default: ["RTD-7", "RTD-8"])
        
    Returns:
    --------
    dict : Resultados de sensibilidad para todos los sensores
    """
    print("=" * 80)
    print("FBG THERMAL SENSITIVITY ANALYSIS")
    print("=" * 80)
    print(f"\nLoading data from: {filepath}")
    
    # 1. Load data
    data = load_root_data(filepath)
    timestamps = convert_timestamps(data["times"])
    
    # 2. Filter FBG data
    print("\nFiltering FBG wavelength data (μ±3σ method)...")
    fbg_config = get_default_fbg_config()
    filtered_data = process_all_fbg_sensors(data["wav"], timestamps, fbg_config)
    
    # 3. Apply time shift
    print(f"Applying time shift: +{time_shift_hours} hour(s)...")
    filtered_data_shifted = apply_time_shift(filtered_data, time_shift_hours)
    
    # 4. Filter temperature data
    print("Filtering temperature data...")
    timestamps_temp, temp_filtered = filter_temperature_data(data["temp"], timestamps)
    
    # 5. Define plateaus
    if auto_plateaus:
        print(f"\nDetecting plateaus automatically (tolerance={tolerance}, min_length={min_plateau_length}s)...")
        plateaus_list = find_plateaus(data["press"], timestamps, tolerance, min_plateau_length)
        print(f"Found {len(plateaus_list)} plateaus:")
        for idx, p in enumerate(plateaus_list):
            print(f"  Plateau {idx+1}: {p['t0'].strftime('%H:%M:%S')} - {p['tfin'].strftime('%H:%M:%S')} "
                  f"(P={p['mean']:.2f}±{p['std']:.2f} bar)")
        plateaus = convert_plateaus_to_dict(plateaus_list)
    elif plateau_times is not None:
        print(f"\nUsing {len(plateau_times)} manual plateau definitions...")
        plateaus = define_plateaus(plateau_times)
    else:
        raise ValueError("Must provide either plateau_times or set auto_plateaus=True")
    
    # 6. Calculate plateau means
    print("\nCalculating plateau means for all sensors...")
    rtd_config = get_default_rtd_config()
    plateau_results = calculate_plateau_means(
        plateaus, filtered_data_shifted, temp_filtered, timestamps_temp,
        data["press"], timestamps, fbg_config, rtd_config
    )
    
    # 7. Calculate sensitivities
    if temp_sensors is None:
        temp_sensors = ["RTD-7", "RTD-8"]
    
    print(f"\nCalculating thermal sensitivities vs {temp_sensors}...")
    sensitivity_results = calculate_all_sensitivities(
        plateau_results, fbg_config, temp_sensors
    )
    
    # 8. Print summary
    print("\n")
    print_sensitivity_summary(sensitivity_results, fbg_config, temp_sensors)
    
    # 9. Print statistics
    print("\nSTATISTICAL SUMMARY:")
    print("-" * 80)
    for temp_label in temp_sensors:
        sensitivities = []
        for cfg in fbg_config:
            label = cfg["label"]
            if label in sensitivity_results and temp_label in sensitivity_results[label]:
                sensitivities.append(sensitivity_results[label][temp_label]["slope_pm_K"])
        
        if sensitivities:
            print(f"\n{temp_label}:")
            print(f"  Mean:   {np.mean(sensitivities):.3f} pm/K")
            print(f"  Std:    {np.std(sensitivities):.3f} pm/K")
            print(f"  Min:    {np.min(sensitivities):.3f} pm/K")
            print(f"  Max:    {np.max(sensitivities):.3f} pm/K")
            print(f"  Range:  {np.max(sensitivities) - np.min(sensitivities):.3f} pm/K")
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)
    
    return sensitivity_results


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def parse_plateau_string(plateau_str: str) -> List[Tuple[str, str, str]]:
    """
    Parse plateau string from command line.
    Format: "14:50-15:13,15:30-15:52,16:05-16:30"
    """
    plateau_list = []
    for idx, p in enumerate(plateau_str.split(',')):
        start, end = p.strip().split('-')
        plateau_list.append((f"Plateau {idx+1}", start, end))
    return plateau_list


def main():
    parser = argparse.ArgumentParser(
        description='FBG Thermal Sensitivity Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect plateaus from pressure data:
  python %(prog)s --file data.root --auto-plateaus

  # Manual plateau times:
  python %(prog)s --file data.root --plateaus "14:50-15:13,15:30-15:52"

  # Custom detection parameters:
  python %(prog)s --file data.root --auto-plateaus --tolerance 0.02 --min-length 300
        """
    )
    
    parser.add_argument('--file', '-f', required=True,
                       help='Path to ROOT file with FBG data')
    
    parser.add_argument('--auto-plateaus', '-a', action='store_true',
                       help='Automatically detect plateaus from pressure data')
    
    parser.add_argument('--plateaus', '-p', type=str,
                       help='Manual plateau times (format: "HH:MM-HH:MM,HH:MM-HH:MM,...)"')
    
    parser.add_argument('--tolerance', '-t', type=float, default=0.01,
                       help='Tolerance for auto plateau detection (default: 0.01 = 1%%)')
    
    parser.add_argument('--min-length', '-m', type=float, default=500,
                       help='Minimum plateau length in seconds (default: 500)')
    
    parser.add_argument('--time-shift', '-s', type=float, default=1.0,
                       help='Time shift in hours (default: 1.0)')
    
    parser.add_argument('--temp-sensors', '-r', type=str, default="RTD-7,RTD-8",
                       help='Temperature sensors to use (default: "RTD-7,RTD-8")')
    
    args = parser.parse_args()
    
    # Validate input
    if not args.auto_plateaus and not args.plateaus:
        parser.error("Must provide either --auto-plateaus or --plateaus")
    
    # Parse plateau times if provided
    plateau_times = None
    if args.plateaus:
        try:
            plateau_times = parse_plateau_string(args.plateaus)
        except Exception as e:
            parser.error(f"Invalid plateau format: {e}")
    
    # Parse temperature sensors
    temp_sensors = [s.strip() for s in args.temp_sensors.split(',')]
    
    # Run analysis
    try:
        sensitivity_results = run_analysis(
            filepath=args.file,
            plateau_times=plateau_times,
            auto_plateaus=args.auto_plateaus,
            tolerance=args.tolerance,
            min_plateau_length=args.min_length,
            time_shift_hours=args.time_shift,
            temp_sensors=temp_sensors
        )
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
