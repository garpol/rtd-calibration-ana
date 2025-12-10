#!/usr/bin/env python3
"""
Calculate and print RTD Calibration Constants using Tree Method

This script calculates calibration constants for all resistance sensors
relative to a reference sensor (PDHD-HP-13) using the tree methodology
with weighted mean of multiple paths via raised sensors.

Usage:
    python calculate_calibration_constants.py

Requirements:
    - pandas, numpy
    - RTD_Calibration_VGP package
    - LogFile.csv in ../data/ or ../../data/
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

# Add src directory to path
src_dir = str(Path(__file__).parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Also add parent directory
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from RTD_Calibration_VGP.src.logfile import Logfile
    from RTD_Calibration_VGP.src.setSTS import SetSTS
except ImportError as e:
    print(f"⚠️ Could not import RTD_Calibration_VGP modules: {e}")
    print(f"   src_dir: {src_dir}")
    print(f"   parent_dir: {parent_dir}")
    print(f"   sys.path: {sys.path[:3]}")
    sys.exit(1)


def find_logfile():
    """Find LogFile.csv in possible locations."""
    possible_paths = [
        "../data/LogFile.csv",
        "../../data/LogFile.csv",
        "RTD_Calibration_VGP/data/LogFile.csv"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            return path
    
    return None


def calculate_offset_via_raised(set_A, sensor_A, set_B, sensor_B, 
                                processed_sets, raised_by_set, verbose=False):
    """
    Calculate offset between resistances from different sets using raised sensors.
    
    Returns weighted mean of all available paths (weight = 1/error²).
    """
    if set_A not in processed_sets or set_B not in processed_sets:
        return None, None
    
    if set_A not in raised_by_set or set_B not in raised_by_set:
        return None, None
    
    # Get offsets and errors for each set
    offset_means_A = processed_sets[set_A]['offset_means']
    offset_stds_A = processed_sets[set_A]['offset_stds']
    offset_means_B = processed_sets[set_B]['offset_means']
    offset_stds_B = processed_sets[set_B]['offset_stds']
    
    if sensor_A not in offset_means_A.index or sensor_B not in offset_means_B.index:
        return None, None
    
    # Raised sensors from each set
    raised_list_A = raised_by_set[set_A]
    raised_list_B = raised_by_set[set_B]
    
    # Need R2 offsets to connect raised sensors
    if 'RESIST_SET5' not in processed_sets:
        return None, None
    
    offset_means_R2 = processed_sets['RESIST_SET5']['offset_means']
    offset_stds_R2 = processed_sets['RESIST_SET5']['offset_stds']
    
    # Calculate offsets for each pair of raised sensors
    offsets_per_path = []
    errors_per_path = []
    
    for raised_A in raised_list_A:
        if raised_A not in offset_means_R2.index:
            continue
        
        for raised_B in raised_list_B:
            if raised_B not in offset_means_R2.index:
                continue
            
            # PATH: sensor_A → raised_A (in set_A) → raised_A (in R2) → 
            #       raised_B (in R2) → raised_B (in set_B) → sensor_B
            
            # Step 1: offset from sensor_A to raised_A in set A
            offset_1 = offset_means_A[sensor_A] - offset_means_A[raised_A]
            error_1 = np.sqrt(
                (offset_stds_A[sensor_A] if sensor_A in offset_stds_A.index else 0.0)**2 +
                (offset_stds_A[raised_A] if raised_A in offset_stds_A.index else 0.0)**2
            )
            
            # Step 2: offset from raised_A to raised_B in R2
            offset_2 = offset_means_R2[raised_A] - offset_means_R2[raised_B]
            error_2 = np.sqrt(
                (offset_stds_R2[raised_A] if raised_A in offset_stds_R2.index else 0.0)**2 +
                (offset_stds_R2[raised_B] if raised_B in offset_stds_R2.index else 0.0)**2
            )
            
            # Step 3: offset from raised_B to sensor_B in set B
            offset_3 = offset_means_B[raised_B] - offset_means_B[sensor_B]
            error_3 = np.sqrt(
                (offset_stds_B[raised_B] if raised_B in offset_stds_B.index else 0.0)**2 +
                (offset_stds_B[sensor_B] if sensor_B in offset_stds_B.index else 0.0)**2
            )
            
            # Total offset via this path
            offset_total = offset_1 + offset_2 + offset_3
            error_total = np.sqrt(error_1**2 + error_2**2 + error_3**2)
            
            offsets_per_path.append(offset_total)
            errors_per_path.append(error_total)
    
    if len(offsets_per_path) == 0:
        return None, None
    
    # Weighted mean (weight = 1/error²)
    weights = np.array([1.0 / (err**2) if err > 0 else 1e6 for err in errors_per_path])
    offsets_array = np.array(offsets_per_path)
    
    offset_weighted = np.sum(offsets_array * weights) / np.sum(weights)
    error_weighted = np.sqrt(1.0 / np.sum(weights))
    
    return offset_weighted, error_weighted


def calculate_direct_offset(set_name, sensor_A, sensor_B, processed_sets):
    """Calculate direct offset between sensors in the same set."""
    if set_name not in processed_sets:
        return None, None
    
    offset_means = processed_sets[set_name]['offset_means']
    offset_stds = processed_sets[set_name]['offset_stds']
    
    if sensor_A not in offset_means.index or sensor_B not in offset_means.index:
        return None, None
    
    offset = offset_means[sensor_A] - offset_means[sensor_B]
    error = np.sqrt(
        (offset_stds[sensor_A] if sensor_A in offset_stds.index else 0.0)**2 +
        (offset_stds[sensor_B] if sensor_B in offset_stds.index else 0.0)**2
    )
    
    return offset, error


def calculate_offset_universal(sensor_A, sensor_B, processed_sets, raised_by_set, verbose=False):
    """
    Calculate offset between any two sensors (same or different sets).
    Auto-detects if they're in the same set or different sets.
    """
    # Find which sets contain each sensor
    set_A = None
    set_B = None
    
    for set_name, data in processed_sets.items():
        if sensor_A in data['sensors']:
            set_A = set_name
        if sensor_B in data['sensors']:
            set_B = set_name
    
    if set_A is None or set_B is None:
        return None, None, "sensor_not_found"
    
    # Same set: direct calculation
    if set_A == set_B:
        offset, error = calculate_direct_offset(set_A, sensor_A, sensor_B, processed_sets)
        return offset, error, "direct"
    
    # Different sets: via raised sensors
    offset, error = calculate_offset_via_raised(set_A, sensor_A, set_B, sensor_B, 
                                                processed_sets, raised_by_set, verbose)
    return offset, error, "via_raised"


def main():
    """Main execution."""
    print("="*80)
    print("RTD CALIBRATION CONSTANTS CALCULATOR - TREE METHOD")
    print("="*80)
    print()
    
    # Find and load logfile
    logfile_path = find_logfile()
    if logfile_path is None:
        print("❌ Error: LogFile.csv not found")
        print("   Searched in: ../data/, ../../data/, RTD_Calibration_VGP/data/")
        return 1
    
    print(f"📁 Loading logfile: {logfile_path}")
    logfile = Logfile(logfile_path)
    print(f"✅ Logfile loaded: {len(logfile.log_file)} entries")
    print()
    
    # Process selected sets
    selected_sets = ['RESIST_SET1', 'RESIST_SET2', 'RESIST_SET3', 'RESIST_SET4', 'RESIST_SET5']
    
    print("🔄 Processing sets...")
    processed_sets = {}
    all_sensors = set()
    
    # Configuration for sets
    sets_config = {
        'RESIST_SET1': {'round': 1},
        'RESIST_SET2': {'round': 1},
        'RESIST_SET3': {'round': 1},
        'RESIST_SET4': {'round': 1},
        'RESIST_SET5': {'round': 2}
    }
    
    # Create single SetSTS instance
    try:
        set_sts = SetSTS(
            logfile=logfile.log_file,
            data_folder="resistences"
        )
        print("   ✅ SetSTS initialized")
    except Exception as e:
        print(f"   ❌ Error initializing SetSTS: {e}")
        return 1
    
    # Group runs by set
    try:
        set_sts.group_runs_by_set(calibset_pattern="RESIST_SET")
        print(f"   ✅ Runs grouped: {len(set_sts.runs_by_set)} sets")
    except Exception as e:
        print(f"   ❌ Error grouping runs: {e}")
        return 1
    
    # Calculate offsets and RMS
    try:
        set_sts.calculate_offsets_and_rms(selected_sets=selected_sets, tini=20, tend=40)
        print("   ✅ Offsets and RMS calculated")
    except Exception as e:
        print(f"   ❌ Error calculating offsets: {e}")
        return 1
    
    # Calculate repeatability
    try:
        set_sts.offset_repeatability(
            tini=20, 
            tend=40, 
            selected_sets=selected_sets,
            save_dir="offset_repeatability_resistences",
            write_csv=False,
            write_excel=False
        )
        print(f"   ✅ Statistics calculated for {len(set_sts.global_stats)} sets")
    except Exception as e:
        print(f"   ❌ Error calculating repeatability: {e}")
        return 1
    
    # Extract data from each set
    for set_name in sets_config.keys():
        if set_name not in set_sts.runs_by_set or set_name not in set_sts.global_stats:
            continue
        
        try:
            stats = set_sts.global_stats[set_name]
            
            if 'means' in stats and stats['means']:
                means_dict = stats['means']
                sigmas_dict = stats.get('sigmas', {})
                
                # Convert from mK to K
                offset_means = pd.Series(means_dict) / 1000.0
                offset_stds = pd.Series(sigmas_dict) / 1000.0 if sigmas_dict else pd.Series()
                
                # Filter sensors (exclude temperature sensors 1009, 1010)
                sensors = [s for s in offset_means.index.tolist() if s not in ['1009', '1010']]
                all_sensors.update(sensors)
                
                processed_sets[set_name] = {
                    'sensors': sensors,
                    'offset_means': offset_means,
                    'offset_stds': offset_stds,
                    'round': sets_config[set_name]['round']
                }
                
                print(f"   Processing {set_name}... ✅ {len(sensors)} sensors")
                
        except Exception as e:
            print(f"   Processing {set_name}... ❌ Error: {e}")
            continue
    
    print(f"\n✅ Processed {len(processed_sets)} sets with {len(all_sensors)} total sensors")
    print()
    
    # Add channel 2 sensors (internal reference for each set)
    channel_2_sensors = {
        'RESIST_SET1': 'PDHD-HP-14',
        'RESIST_SET2': 'PDHD-HP-26',
        'RESIST_SET3': 'PDHD-HP-38',
        'RESIST_SET4': 'PDHD-HP-50',
        'RESIST_SET5': 'PDHD-HP-19'
    }
    
    print("🔧 Adding reference sensors (channel 2)...")
    for set_name, sensor_ch2 in channel_2_sensors.items():
        if set_name in processed_sets:
            if sensor_ch2 not in processed_sets[set_name]['offset_means'].index:
                processed_sets[set_name]['offset_means'][sensor_ch2] = 0.0
                processed_sets[set_name]['offset_stds'][sensor_ch2] = 0.0
                processed_sets[set_name]['sensors'].append(sensor_ch2)
                all_sensors.add(sensor_ch2)
                print(f"   Added {sensor_ch2} to {set_name}")
    
    print()
    
    # Identify raised sensors (appear in R2 = RESIST_SET5)
    print("🔍 Identifying raised sensors (present in R2)...")
    sensors_r2 = processed_sets['RESIST_SET5']['sensors'] if 'RESIST_SET5' in processed_sets else []
    raised_sensors = set(sensors_r2)
    
    raised_by_set = {}
    for set_name in ['RESIST_SET1', 'RESIST_SET2', 'RESIST_SET3', 'RESIST_SET4']:
        if set_name not in processed_sets:
            continue
        raised_in_this_set = [s for s in processed_sets[set_name]['sensors'] if s in raised_sensors]
        raised_by_set[set_name] = raised_in_this_set
        print(f"   {set_name}: {len(raised_in_this_set)} raised sensors")
    
    # R2 itself
    raised_by_set['RESIST_SET5'] = sensors_r2
    print(f"   RESIST_SET5 (R2): {len(sensors_r2)} sensors")
    print()
    
    # Set reference sensor (first raised sensor from RESIST_SET1)
    reference_sensor = raised_by_set['RESIST_SET1'][0] if 'RESIST_SET1' in raised_by_set else 'PDHD-HP-13'
    print(f"🎯 Reference sensor: {reference_sensor} (RESIST_SET1, Round 2)")
    print(f"   Offset = 0.000 mK by definition")
    print()
    
    # Calculate calibration constants for all sensors
    print("⚙️  Calculating calibration constants...")
    calibration_constants = {}
    calibration_errors = {}
    
    total_sensors = sum(len(processed_sets[s]['sensors']) for s in processed_sets if 'SET5' not in s)
    calculated = 0
    
    for set_name in processed_sets:
        if 'SET5' in set_name:  # Skip R2
            continue
        
        for sensor_id in processed_sets[set_name]['sensors']:
            offset, error, method = calculate_offset_universal(
                sensor_id, reference_sensor, 
                processed_sets, raised_by_set, 
                verbose=False
            )
            
            if offset is not None:
                calibration_constants[sensor_id] = offset
                calibration_errors[sensor_id] = error
                calculated += 1
    
    print(f"✅ Calculated constants for {calculated}/{total_sensors} resistances")
    print()
    
    # Create DataFrame
    calibration_df = pd.DataFrame({
        'sensor_id': list(calibration_constants.keys()),
        'offset_K': list(calibration_constants.values()),
        'error_K': [calibration_errors[s] for s in calibration_constants.keys()],
        'offset_mK': [v * 1000 for v in calibration_constants.values()],
        'error_mK': [calibration_errors[s] * 1000 for s in calibration_constants.keys()]
    })
    
    # Add set and round info
    def get_set_info(sensor_id):
        for set_name, data in processed_sets.items():
            if sensor_id in data['sensors']:
                return set_name, data.get('round', -1)
        return 'Unknown', -1
    
    calibration_df['set'] = calibration_df['sensor_id'].apply(lambda x: get_set_info(x)[0])
    calibration_df['round'] = calibration_df['sensor_id'].apply(lambda x: get_set_info(x)[1])
    calibration_df['is_raised'] = calibration_df['sensor_id'].apply(lambda x: x in raised_sensors)
    
    # Sort by set and sensor_id
    calibration_df = calibration_df.sort_values(['set', 'sensor_id']).reset_index(drop=True)
    
    # Print results
    print("="*80)
    print("RTD CALIBRATION CONSTANTS - TREE METHOD")
    print("="*80)
    print(f"Reference sensor: {reference_sensor} (RESIST_SET1, Round 2)")
    print(f"Total resistances: {len(calibration_df)}")
    print(f"Method: Weighted mean via raised sensors")
    print("="*80)
    print()
    
    # Print table
    print(f"{'Sensor_ID':<20} {'Set':<15} {'Offset (mK)':<15} {'Error (mK)':<15} {'Round':<10}")
    print("-"*80)
    
    for idx, row in calibration_df.iterrows():
        print(f"{row['sensor_id']:<20} {row['set']:<15} {row['offset_mK']:>14.3f} {row['error_mK']:>14.3f} {row['round']:<10}")
    
    print()
    print("="*80)
    print("NOTES:")
    print("="*80)
    print(f"• Reference: {reference_sensor} has offset = 0.000 mK by definition")
    print("• RESIST_SET1: Direct calculation (1 path)")
    print("• RESIST_SET2/3/4: Weighted mean via R2 raised sensors (multiple paths)")
    print("• Error: Propagated uncertainty from weighted mean")
    print("• Formula: offset = Σ(offset_i × weight_i) / Σ(weight_i), weight_i = 1/error_i²")
    print()
    
    # Statistics by set
    print("="*80)
    print("STATISTICS BY SET:")
    print("="*80)
    for set_name in sorted(calibration_df['set'].unique()):
        if set_name == 'Unknown' or 'SET5' in set_name:
            continue
        subset = calibration_df[calibration_df['set'] == set_name]
        print(f"\n{set_name}:")
        print(f"  Resistances: {len(subset)}")
        print(f"  Raised: {subset['is_raised'].sum()}")
        print(f"  Offset range: [{subset['offset_mK'].min():+.3f}, {subset['offset_mK'].max():+.3f}] mK")
        print(f"  Mean error: {subset['error_mK'].mean():.3f} mK")
    
    print()
    
    # Save to files
    output_csv = "calibration_constants_resistences.csv"
    output_txt = "calibration_constants_resistences.txt"
    
    calibration_df.to_csv(output_csv, index=False)
    print(f"💾 Saved: {output_csv}")
    
    # Save TXT with same format
    with open(output_txt, 'w') as f:
        f.write("="*80 + "\n")
        f.write("RTD CALIBRATION CONSTANTS - TREE METHOD\n")
        f.write("="*80 + "\n")
        f.write(f"Reference sensor: {reference_sensor} (RESIST_SET1, Round 2)\n")
        f.write(f"Total resistances: {len(calibration_df)}\n")
        f.write(f"Method: Weighted mean via raised sensors\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"{'Sensor_ID':<20} {'Set':<15} {'Offset (mK)':<15} {'Error (mK)':<15} {'Round':<10}\n")
        f.write("-"*80 + "\n")
        
        for idx, row in calibration_df.iterrows():
            f.write(f"{row['sensor_id']:<20} ")
            f.write(f"{row['set']:<15} ")
            f.write(f"{row['offset_mK']:>14.3f} ")
            f.write(f"{row['error_mK']:>14.3f} ")
            f.write(f"{row['round']:<10}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("NOTES:\n")
        f.write("="*80 + "\n")
        f.write(f"• Reference: {reference_sensor} has offset = 0.000 mK by definition\n")
        f.write("• RESIST_SET1: Direct calculation (1 path)\n")
        f.write("• RESIST_SET2/3/4: Weighted mean via R2 raised sensors (multiple paths)\n")
        f.write("• Error: Propagated uncertainty from weighted mean\n")
        f.write("• Formula: offset = Σ(offset_i × weight_i) / Σ(weight_i), weight_i = 1/error_i²\n")
    
    print(f"💾 Saved: {output_txt}")
    print()
    print("✅ Done!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
