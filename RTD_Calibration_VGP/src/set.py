import pandas as pd
import os
import math
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap
from typing import Literal
import numpy as np
try:
    from .run import Run
    from .utils import load_config, DEFAULT_CONFIG
except ImportError:
    from run import Run
    from utils import load_config, DEFAULT_CONFIG
import yaml
from typing import Optional

# Module-level default sensors (fallback) - kept here for backward compatibility but can be moved to config
DEFAULT_SENSORS = {
    'discarded_sensors': {
        3.0: [48205, 48478],
        4.0: [48485, 48490],
        5.0: [48797],
        6.0: [48733, 48746],
        7.0: [48751, 48754, 48836],
        8.0: [48841, 48848],
        14.0: [48957, 48960, 48961],
        15.0: [48520, 48965],
        16.0: [49107, 49108],
        17.0: [49117, 49124],
        18.0: [49166],
        19.0: [49169],
        21.0: [49191, 49200],
        22.0: [49205, 49210],
        23.0: [49226, 49235, 49236, 49237],
        24.0: [49242],
        25.0: [49251, 49253],
        26.0: [55190, 55043, 55104],
        27.0: [55103, 55075, 55072],
        28.0: [55199, 55198],
        29.0: [55193],
        30.0: [55255, 55173, 54926],
        31.0: [55195],
        32.0: [54931],
        33.0: [54934],
        35.0: [55231, 55232, 55245],
        36.0: [55040],
        37.0: [55015, 55083],
        38.0: [55237],
        40.0: [55205],
        42.0: [55019],
        46.0: [49107],
        47.0: [55199],
        48.0: [55245],
        60.0: [58384],
    },
    'sensors_raised_by_set': {
        3.0: [48203, 48479],
        4.0: [48484, 48491],
        5.0: [48673, 48800],
        6.0: [48731, 48747],
        7.0: [48753, 48839],
        8.0: [48845, 48851],
        9.0: [48857, 48863],
        10.0: [48869, 48875],
        11.0: [48884, 48887],
        13.0: [48905, 48911],
        14.0: [48956, 48963],
        15.0: [48521, 48964],
        16.0: [49106, 49112],
        17.0: [49119, 49123],
        18.0: [49126, 49131],
        19.0: [49167, 49176],
        20.0: [49181, 49186],
        21.0: [49192, 49197],
        22.0: [49204, 49211],
        23.0: [49227, 49233],
        24.0: [49238, 49244],
        25.0: [49250, 49257],
        26.0: [54875, 55044],
        27.0: [55073, 54881],
        28.0: [55208, 55215],
        29.0: [55264, 55263],
        30.0: [55253, 55168],
        31.0: [55186, 55194],
        32.0: [55166, 54930],
        33.0: [54878, 54876],
        34.0: [54878, 54876],
        35.0: [55241, 55233],
        36.0: [55050, 55041],
        37.0: [55014, 55084],
        38.0: [55217, 55221],
        39.0: [55252, 55188],
        40.0: [54869, 54870],
        41.0: [54840, 54841],
        42.0: [54897, 55022],
        43.0: [55021, 55023],
        44.0: [54856, 54845],
        45.0: [55056, 55061],
        46.0: [48957, 49235],
        47.0: [55075, 55195],
        48.0: [55015, 55173],
        59.0: [58400, 58367],
        60.0: [58385, 58381],
        49.0: [48484, 48747],
        50.0: [48869, 48956],
        51.0: [49112, 49167],
        52.0: [49233, 55073],
        53.0: [55253, 55227],
        54.0: [55233, 55221],
    },
    'set_rounds': {},
}

class Set:
    def __init__(self, logfile: pd.DataFrame, config: dict = None, config_path: Optional[str] = None) -> None:
        """Initialize a Set that groups multiple Run instances by CalibSetNumber.
        
        Parameters:
            logfile (pd.DataFrame): DataFrame containing sensor assignments and metadata
            config (dict, optional): Configuration dict with per-set sensor mappings.
                If provided, overrides default discarded_sensors/sensors_raised_by_set.
        """
        # If config_path provided, load it; otherwise normalize provided config dict
        combined_cfg = None
        try:
            if config_path:
                combined_cfg = load_config(config_path)
            elif isinstance(config, dict):
                # merge with defaults
                merged = DEFAULT_CONFIG.copy()
                for k, v in config.items():
                    if isinstance(v, dict) and isinstance(merged.get(k), dict):
                        merged[k] = {**merged[k], **v}
                    else:
                        merged[k] = v
                combined_cfg = merged
        except Exception as e:
            print(f"Warning: could not load config: {e}")

        # Configure logfile source: logfile parameter may be a DataFrame, or a path, or None
        if isinstance(logfile, pd.DataFrame):
            self.logfile = logfile
        else:
            # prefer path from config if available
            lf_path = None
            if combined_cfg:
                lf_path = combined_cfg.get('paths', {}).get('logfile')
            lf_path = logfile or lf_path
            from .logfile import Logfile
            lf = Logfile(filepath=lf_path)
            self.logfile = lf.log_file
        self.runs_by_set = {}  # Dict mapping CalibSetNumber to Run instances
        self.offsets_data = None  # Matrix of offsets from all runs
        self.rms_offsets_data = None  # Matrix of RMS errors from all runs
        self.calibration_constants = None  # Calibration constants calculated
        # Defaults; these can be overridden by passing a `config` dict or a `config_path` to Set
        self.discarded_sensors = DEFAULT_SENSORS.get('discarded_sensors', {})
        self.sensors_raised_by_set = DEFAULT_SENSORS.get('sensors_raised_by_set', {})
        # Default rounds mapping (can be overridden by config)
        self.set_rounds = DEFAULT_SENSORS.get('set_rounds', {})

        # Apply config overrides if provided (config dict or config_path)
        loaded_cfg = None
        if config_path and not config:
            try:
                with open(config_path, 'r') as f:
                    loaded_cfg = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: could not load config_path '{config_path}': {e}")
        elif isinstance(config, str) and not config_path:
            # config passed as a path string
            try:
                with open(config, 'r') as f:
                    loaded_cfg = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: could not load config from string path '{config}': {e}")
        elif isinstance(config, dict):
            loaded_cfg = config

        if loaded_cfg:
            try:
                sensors_cfg = loaded_cfg.get("sensors", {})
                # If user provided unified per-set structure under sensors.sets, prefer it
                sets_cfg = sensors_cfg.get("sets")
                if isinstance(sets_cfg, dict) and sets_cfg:
                    # normalize and populate the three dictionaries
                    sd = {}
                    sr = {}
                    srounds = {}
                    for ks, vv in sets_cfg.items():
                        # Normalize set key to float if possible; skip if not
                        try:
                            kf = float(ks)
                        except Exception:
                            try:
                                kf = float(str(ks))
                            except Exception:
                                # skip entries with non-numeric keys
                                continue
                        # support both Spanish and English keys inside each set entry
                        discarded_list = vv.get("discarded") or vv.get("descartados") or vv.get("discarded_sensors") or []
                        raised_list = vv.get("raised") or vv.get("rojo") or vv.get("sensors_raised") or []
                        sd[kf] = discarded_list
                        sr[kf] = raised_list
                        # parse round robustly; allow numeric strings, otherwise skip this field
                        round_raw = vv.get("round", 1)
                        try:
                            srounds[kf] = int(float(round_raw))
                        except Exception:
                            # ignore invalid non-numeric round values (e.g., 'Refs')
                            pass
                    # assign to English-named attributes consistently
                    self.discarded_sensors = sd
                    self.sensors_raised_by_set = sr
                    self.set_rounds = srounds
                else:
                    # backward-compatible fields (accept both English and Spanish keys)
                    if sensors_cfg.get("discarded_sensors") or sensors_cfg.get("descartados"):
                        raw = sensors_cfg.get("discarded_sensors") or sensors_cfg.get("descartados")
                        self.discarded_sensors = {float(k): v for k, v in raw.items()}
                    if sensors_cfg.get("sensors_raised_by_set") or sensors_cfg.get("sensors_raised") or sensors_cfg.get("rojo"):
                        raw = sensors_cfg.get("sensors_raised_by_set") or sensors_cfg.get("sensors_raised") or sensors_cfg.get("rojo")
                        self.sensors_raised_by_set = {float(k): v for k, v in raw.items()}
                    if sensors_cfg.get("set_rounds"):
                        normalized_rounds = {}
                        for k, v in sensors_cfg.get("set_rounds", {}).items():
                            try:
                                kf = float(k)
                            except Exception:
                                try:
                                    kf = float(str(k))
                                except Exception:
                                    continue
                            try:
                                normalized_rounds[kf] = int(float(v))
                            except Exception:
                                # skip invalid round values
                                continue
                        self.set_rounds = normalized_rounds
            except Exception as e:
                print(f"Warning: failed to apply sensors config: {e}")

        # plots default directory (can be controlled via config paths)
        self.plots_dir = None
        if config and isinstance(config, dict):
            paths_cfg = config.get("paths", {})
            self.plots_dir = paths_cfg.get("plots_dir")
        if not self.plots_dir:
            self.plots_dir = "RTD_Calibration_VGP/notebooks/Plots"
        # Output write defaults (can be overridden by providing 'output' in config loaded earlier)
        # Default to True for backward compatibility
        if not hasattr(self, 'write_csv'):
            self.write_csv = True
        if not hasattr(self, 'write_excel'):
            self.write_excel = True
        

    
    def group_runs_by_set(self, selected_sets=None) -> None:
        """
        Group runs by 'CalibSetNumber' and create instances of the 'Run' class for each one.
        Excludes filenames that contain certain keywords (e.g. 'pre', 'st', 'lar') and runs
        marked as 'BAD' in the Selection column.
        """
        try:
            import numpy as np
            # Usar .copy() para evitar SettingWithCopyWarning
            self.logfile = self.logfile.copy()
            self.logfile["CalibSetNumber"] = pd.to_numeric(self.logfile["CalibSetNumber"], errors='coerce')
            calib_set_numbers = self.logfile["CalibSetNumber"].unique()
            calib_set_numbers = sorted([
                calib_set_number for calib_set_number in calib_set_numbers
                if isinstance(calib_set_number, (int, float, np.integer, np.floating)) 
                and not pd.isna(calib_set_number)
                and float(calib_set_number).is_integer()
                and calib_set_number > 0
                and len(str(int(calib_set_number))) <= 2  # Verify that the number has two or fewer digits
            ])
            excluded_keywords = ['pre', 'st', 'lar']  # Palabras a excluir de los filenames
            # Agrupar los runs por CalibSetNumber
            for calib_set_number in calib_set_numbers:
                if selected_sets and calib_set_number not in selected_sets:
                    continue
                print(f"\nProcessing CalibSetNumber: {calib_set_number}")
                # Filtramos el logfile para obtener todos los runs de este CalibSetNumber
                runs_in_set = self.logfile[self.logfile["CalibSetNumber"] == calib_set_number]
                valid_runs = {}
                # self.runs_by_set[calib_set_number] = {} now initialized later with valid sets

                # Iteramos por cada run en el set
                for _, run_row in runs_in_set.iterrows():
                    filename = run_row["Filename"]
                    selection = run_row["Selection"]

                    if isinstance(filename, str) and all(keyword not in filename.lower() for keyword in excluded_keywords):
                        # Include runs where Selection is not 'BAD' (including NaN/empty values)
                        if pd.isna(selection) or selection != "BAD":
                            run_instance = Run(filename, self.logfile)
                            # Try to associate sensors, read run info, and filter faulty channels
                            try:
                                run_instance.associate_sensors()
                                run_instance.read_run_info()
                                # Call filter_faulty_channels to detect additional issues beyond NaN counts
                                faulty = run_instance.filter_faulty_channels()
                                # Update defective_channels with any additional issues found
                                if faulty:
                                    # Merge detected faults into defective_channels (avoid duplicates)
                                    existing_defective = set(run_instance.defective_channels or [])
                                    existing_defective.update(faulty.keys())
                                    run_instance.defective_channels = list(existing_defective)
                            except Exception as e:
                                print(f"    Warning: failed to associate sensors or read run info for {filename}: {e}. Skipping this run.")
                                continue
                            # If association succeeded, keep the run
                            valid_runs[filename] = run_instance
                            print(f"    Included: {filename}")
                        else:
                            print(f"    Excluded: {filename} (marked as 'BAD' in Selection)")
                    else:
                        print(f"    Excluded: {filename} (contains 'pre' or 'st')")
                        
                # Only save the group if there are valid runs
                if valid_runs:
                    self.runs_by_set[calib_set_number] = valid_runs
                        
        except KeyError as e:
            print(f"Error: {e}")
            raise
            
        except Exception as e:
            raise RuntimeError(f"Error grouping runs: {e}")

    def get_reference_sensors_for_set(self, calib_set_number: float) -> dict:
        """
        Get reference sensor information for a specific set.
        
        Returns a dict with aggregated reference sensor info from all runs in the set:
        {
            'ref_sensor_ids': set of all reference sensor IDs found across runs,
            'runs_with_refs': list of (filename, [ref_ids]) tuples
        }
        
        Reference sensors (channels 13-14) are repeated across sets for monitoring
        and should NOT be considered as "raised" sensors or part of the calibration tree.
        """
        result = {
            'ref_sensor_ids': set(),
            'runs_with_refs': []
        }
        
        if calib_set_number not in self.runs_by_set:
            return result
            
        runs_in_set = self.runs_by_set[calib_set_number]
        
        for filename, run_instance in runs_in_set.items():
            try:
                ref_ids = run_instance.get_reference_sensor_ids()
                if ref_ids:
                    result['ref_sensor_ids'].update(ref_ids)
                    result['runs_with_refs'].append((filename, ref_ids))
            except AttributeError:
                # Run object doesn't have get_reference_sensor_ids method (older version)
                pass
                
        return result
    
    def get_all_reference_sensors(self) -> dict:
        """
        Get reference sensor information for all sets.
        
        Returns dict mapping CalibSetNumber -> reference sensor info:
        {
            set_num: {
                'ref_sensor_ids': set of reference sensor IDs,
                'runs_with_refs': list of (filename, [ref_ids])
            }
        }
        """
        all_refs = {}
        
        for calib_set_number in self.runs_by_set.keys():
            refs = self.get_reference_sensors_for_set(calib_set_number)
            if refs['ref_sensor_ids']:  # Only include sets that have reference sensors
                all_refs[calib_set_number] = refs
                
        return all_refs
    
    def export_reference_sensors_to_yaml(self, output_path: str = "reference_sensors.yaml") -> None:
        """
        Export reference sensor information to a YAML file.
        
        Creates a YAML file with reference sensor IDs for each set that has them.
        
        Args:
            output_path: Path where the YAML file will be saved
            
        Example output:
            reference_sensors:
              3:
                ref1_id: 48176
                ref2_id: 48177
              4:
                ref1_id: 48176
                ref2_id: 48177
        """
        all_refs = self.get_all_reference_sensors()
        
        if not all_refs:
            print("No reference sensors found to export")
            return
        
        # Build export structure
        export_data = {'reference_sensors': {}}
        
        for set_num, ref_info in all_refs.items():
            ref_ids = sorted(ref_info['ref_sensor_ids'])
            
            if len(ref_ids) >= 1:
                export_data['reference_sensors'][int(set_num)] = {
                    'ref1_id': ref_ids[0] if len(ref_ids) > 0 else None,
                    'ref2_id': ref_ids[1] if len(ref_ids) > 1 else None,
                }
        
        # Write to YAML
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True, sort_keys=True)
            print(f"✅ Reference sensors exported to: {output_path}")
            print(f"   Sets with references: {len(export_data['reference_sensors'])}")
        except Exception as e:
            print(f"❌ Error exporting to YAML: {e}")

    def calculate_offsets_and_rms(self, selected_sets=None) -> None:
        """
        Calcula los offsets y errores RMS para todos los runs en el conjunto,
        manteniendo el orden de los sensores basado en el primer run (con más sensores).
        Si el orden de sensores difiere en algún run, se reorganizan las matrices
        para que coincidan con el del run de referencia.
        """
        try:
            offsets_list = []
            rms_list = []
            keys_for_concat = []

            # Itera sobre los runs y calcula offsets y RMS
            for calib_set_number, runs_in_set in self.runs_by_set.items():
                if selected_sets and calib_set_number not in selected_sets:
                    continue
                print(f"\nProcessing CalibSetNumber: {calib_set_number}")

                # Find the run with the most sensors (reference) within this set
                max_sensors = 0
                reference_run = None
                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        num_sensors = len(run_instance.sensor_mapping)
                        if num_sensors > max_sensors:
                            max_sensors = num_sensors
                            reference_run = run_instance
                    else:
                        print(f"Warning: sensor_mapping is None for run {run_instance.filename}. Skipping this run.")

                if not reference_run:
                    print(f"No valid run found to compute offsets in set {calib_set_number}.")
                    continue

                print(f"Reference run has {max_sensors} sensors: {reference_run.filename}")
                print("Reference sensor mapping:")
                print(f"Sensor_mapping : {reference_run.sensor_mapping}")

                # Usa el orden del run de referencia
                reference_sensors = list(reference_run.sensor_mapping.values())
                print(f"Reference based on run: {reference_run.filename} with sensors: {reference_sensors}")

                for filename, run_instance in runs_in_set.items():
                    print(f"  Processing Run: {filename}")

                    if run_instance.sensor_mapping is not None:
                        current_sensors = list(run_instance.sensor_mapping.values())
                        print(f"Current sensors: {current_sensors}")

                        try:
                            # Calcular offsets y RMS
                            offsets = run_instance.offsets()
                            rms_offsets = run_instance.stat_err_offsets()

                            # Crear DataFrames con el orden actual
                            offsets_df = pd.DataFrame(offsets, index=current_sensors, columns=current_sensors)
                            rms_df = pd.DataFrame(rms_offsets, index=current_sensors, columns=current_sensors)

                            print("  → ORIGINAL offsets matrix:")
                            print(offsets_df)

                            # Reorder rows and columns according to reference order
                            offsets_df = offsets_df.reindex(index=reference_sensors, columns=reference_sensors)
                            rms_df = rms_df.reindex(index=reference_sensors, columns=reference_sensors)

                            print("  → REORDERED offsets matrix:")
                            print(offsets_df)

                            offsets_list.append(offsets_df)
                            rms_list.append(rms_df)
                            keys_for_concat.append(calib_set_number)

                            print(f"  Dimensiones de la matriz de offsets: {offsets_df.shape}")
                            print(f"  Dimensiones de la matriz de RMS: {rms_df.shape}")
                        except Exception as e:
                            print(f"  ⚠️  Warning: Could not compute offsets for run {filename}: {str(e)[:100]}")
                            print(f"  ⏭️  Skipping this run and continuing with the rest...")
                    else:
                        print(f"Warning: Cannot compute offsets or RMS for run {run_instance} because sensor_mapping is None.")

            # Construye las matrices de offsets y RMS
            if offsets_list:
                # keys_for_concat aligns with each appended run matrix in offsets_list/rms_list
                self.offsets_data = pd.concat(offsets_list, axis=1, keys=keys_for_concat)
                self.rms_offsets_data = pd.concat(rms_list, axis=1, keys=keys_for_concat)

            print("Offsets and RMS calculations complete.")

        except ValueError as e:
            print(f"Error: {e}")
            raise RuntimeError(f"Error calculating offsets and RMS errors: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise RuntimeError(f"Error calculating offsets and RMS errors: {e}")


    def offset_repeatability(self, tini=20, tend=40, save_dir="offset_repeatability_copy", selected_sets=None, ref=2, write_csv=None, write_excel=None):

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        self.global_stats = {}
        # record skipped runs due to defective channels for auditing
        skipped_runs_list = []
        # record outliers filtered by IQR method
        outliers_filtered = []
        calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else set(selected_sets)

        for calib_set_number in calib_sets_to_process:
            runs = self.runs_by_set.get(calib_set_number)
            if runs is None:
                print(f"WARNING: Set {calib_set_number} not in self.runs_by_set, skipping.")
                continue

            print(f"\nProcessing CalibSetNumber: {calib_set_number}")

            filenames = list(runs.keys())
            first_run = runs[filenames[0]]

            if first_run.sensor_mapping is None:
                print(f"WARNING: sensor_mapping is None for the first run of set {calib_set_number}, skipping set.")
                continue

            mapping = first_run.sensor_mapping

            sensor_names = {}
            for ch in range(1, 15):
                sensor_names[ch] = mapping.get(f"channel_{ch}", None)

            # Determine dynamic or fixed references
            ref_channel_por_sensor = {}

            red_ids = self.sensors_raised_by_set.get(calib_set_number, [])
            if red_ids and len(red_ids) >= 2:
                # Mapear IDs a canales
                red_channels = []
                for red_id in red_ids[:2]:  # solo usar los primeros dos
                    for ch, sid in sensor_names.items():
                        if str(sid).strip() == str(red_id).strip():
                            red_channels.append(ch)
                            break

                if len(red_channels) < 2:
                    print(f"WARNING: Could not find both raised sensors in mapping for set {calib_set_number}, using fixed reference channel {ref}.")
                    red_channels = []
            else:
                red_channels = []

            if len(red_channels) == 2:
                print(f"OK: Set {calib_set_number}: Using dynamic references from raised sensors in channels {red_channels}")
                for ch in range(1, 15):
                    if sensor_names[ch] is None:
                        continue
                    if ch in red_channels:
                        # If it's one of the raised sensors, use the other as reference
                        ref_channel_por_sensor[ch] = [r for r in red_channels if r != ch][0]
                    else:
                        # Distancia circular
                        distances = [
                            (abs(ch - red) % 12 if abs(ch - red) % 12 <= 6 else 12 - abs(ch - red) % 12)
                            for red in red_channels
                        ]
                        closest_idx = np.argmin(distances)
                        ref_channel_por_sensor[ch] = red_channels[closest_idx]
            else:
                # No raised sensors: use fixed reference channel
                print(f"INFO: Set {calib_set_number}: Using fixed reference channel {ref} → Sensor ID {sensor_names.get(ref)}")
                for ch in range(1, 15):
                    if sensor_names[ch] is not None:
                        ref_channel_por_sensor[ch] = ref

            # Plot setup
            fig, axes = plt.subplots(3, 5, figsize=(21, 13))
            axes = axes.flatten()
            fig.subplots_adjust(top=0.80)
            for ax in axes[14:]:
                ax.set_visible(False)

            for idx in range(14):
                channel_num = idx + 1
                sensor_id = sensor_names.get(channel_num, None)

                if sensor_id is None:
                    axes[idx].set_visible(False)
                    continue

                ref_ch = ref_channel_por_sensor[channel_num]
                ref_sensor_id = sensor_names.get(ref_ch, "Unknown")

                # Avoid duplicates between raised sensor pairs
                if channel_num in red_channels and ref_ch in red_channels:
                    if channel_num > ref_ch:
                        axes[idx].set_visible(False)
                        continue

                axes[idx].set_title(
                    f"Offset: Ref Ch {ref_ch} ({ref_sensor_id}) - Ch {channel_num} ({sensor_id})",
                    fontsize=11,
                    fontweight="bold"
                )
                axes[idx].set_xlabel("Time (minutes)", fontsize=10, fontweight="bold")
                axes[idx].set_ylabel("Offset (mK)", fontsize=10, fontweight="bold")
                axes[idx].grid(which='both', linestyle='--', linewidth=0.5)

                run_means = []
                run_stds = []
                run_labels = []

                for run_index, filename in enumerate(filenames):
                    run_label = f"Run {run_index + 1}"
                    run = runs[filename]

                    if run.sensor_mapping is None:
                        print(f"WARNING: sensor_mapping is None for run {filename} in set {calib_set_number}, skipping run.")
                        continue

                    # If this run detected defective channels, skip it for this sensor pair
                    defective = getattr(run, 'defective_channels', []) or []
                    # defective contains channel names like 'channel_8'; map sensor ids back to channel names
                    # find the channel name(s) corresponding to sensor_id and ref_sensor_id
                    skip_due_to_defect = False
                    try:
                        # find channel key for this sensor_id and ref_sensor_id
                        channel_for_sensor = None
                        channel_for_ref = None
                        for ch_key, sid in run.sensor_mapping.items():
                            if str(sid) == str(sensor_id):
                                channel_for_sensor = ch_key
                            if str(sid) == str(ref_sensor_id):
                                channel_for_ref = ch_key
                        if channel_for_sensor in defective or channel_for_ref in defective:
                            skip_due_to_defect = True
                    except Exception:
                        skip_due_to_defect = False

                    if skip_due_to_defect:
                        print(f"  Skipping run {filename} for sensor {sensor_id} because defective channels detected: {defective}")
                        # record skipped runs for auditing
                        skipped_entry = {
                            'CalibSetNumber': calib_set_number,
                            'SensorID': sensor_id,
                            'RunFilename': filename,
                            'DefectiveChannels': ";".join(defective) if defective else ''
                        }
                        skipped_runs_list.append(skipped_entry)
                        continue

                    temperature_data = run.temperature_data
                    time_start = temperature_data.index.min()
                    time_20min = time_start + pd.Timedelta(minutes=tini)
                    time_40min = time_start + pd.Timedelta(minutes=tend)
                    mask = (temperature_data.index >= time_20min) & (temperature_data.index <= time_40min)
                    filtered_data = temperature_data.loc[mask]
                    #filtered_data = temperature_data.loc[time_20min:time_40min]
                    time_relative = (filtered_data.index - time_20min).total_seconds() / 60

                    try:
                        ref_temp = filtered_data[str(ref_sensor_id)]
                        sensor_temp = filtered_data[str(sensor_id)]
                        offset = 1e3 * (ref_temp - sensor_temp)
                    except KeyError:
                        offset = pd.Series([float('nan')] * len(filtered_data), index=filtered_data.index)

                    offset_values = offset.dropna().values
                    if len(offset_values) > 1:
                        run_mean = np.mean(offset_values)
                        run_std = np.std(offset_values, ddof=1)
                        print(f"  [Sensor Ch {channel_num} vs Ref Ch {ref_ch} | {run_label}] Mean: {run_mean:.3f} mK, Std: {run_std:.3f} mK")
                    else:
                        run_mean = np.nan
                        run_std = np.nan

                    run_means.append(run_mean)
                    run_stds.append(run_std)
                    run_labels.append(run_label)

                    axes[idx].plot(time_relative, offset, label=run_label)

                run_means = np.array(run_means)
                run_stds = np.array(run_stds)
                valid = ~np.isnan(run_means) & ~np.isnan(run_stds) & (run_stds > 0)

                if np.sum(valid) >= 2:
                    # Filter outliers using IQR method to remove extreme values
                    valid_means = run_means[valid]
                    valid_stds = run_stds[valid]
                    valid_labels = [run_labels[i] for i, v in enumerate(valid) if v]
                    
                    # Calculate IQR on valid means
                    q1 = np.percentile(valid_means, 25)
                    q3 = np.percentile(valid_means, 75)
                    iqr = q3 - q1
                    
                    # Define outlier bounds (using 3*IQR for extreme outliers)
                    lower_bound = q1 - 3 * iqr
                    upper_bound = q3 + 3 * iqr
                    
                    # Filter out extreme outliers
                    outlier_mask = (valid_means >= lower_bound) & (valid_means <= upper_bound)
                    
                    # Log outliers that were filtered out
                    num_outliers = np.sum(~outlier_mask)
                    if num_outliers > 0:
                        print(f"  ⚠️  Filtered {num_outliers} outlier(s) for sensor channel {idx} using IQR (bounds: [{lower_bound:.2f}, {upper_bound:.2f}] mK)")
                        for i, is_outlier in enumerate(~outlier_mask):
                            if is_outlier:
                                print(f"      - {valid_labels[i]}: mean={valid_means[i]:.2f} mK (outside IQR bounds)")
                                outlier_record = {
                                    'CalibSetNumber': calib_set_number,
                                    'SensorID': idx,
                                    'RunLabel': valid_labels[i],
                                    'Mean_mK': valid_means[i],
                                    'Std_mK': valid_stds[i],
                                    'IQR_Lower': lower_bound,
                                    'IQR_Upper': upper_bound,
                                    'Reason': 'IQR_outlier'
                                }
                                outliers_filtered.append(outlier_record)
                    
                    if np.sum(outlier_mask) >= 2:
                        # Recalculate with filtered data
                        filtered_means = valid_means[outlier_mask]
                        filtered_stds = valid_stds[outlier_mask]
                        weights = 1 / filtered_stds ** 2
                        global_mean = np.average(filtered_means, weights=weights)
                        global_sigma = np.std(filtered_means, ddof=1)
                    elif np.sum(outlier_mask) == 1:
                        # Only one point remains after filtering, use it but mark sigma as NaN
                        global_mean = valid_means[outlier_mask][0]
                        global_sigma = np.nan
                    else:
                        # All points were outliers (unlikely), fall back to unfiltered calculation
                        weights = 1 / valid_stds ** 2
                        global_mean = np.average(valid_means, weights=weights)
                        global_sigma = np.std(valid_means, ddof=1)
                else:
                    # Not enough valid runs to compute a reproducibility estimate.
                    # Use NaN so downstream aggregation and histograms can ignore these.
                    global_mean = np.nan
                    global_sigma = np.nan

                # DEBUG: Print sigma values to identify sources of high sigmas
                if global_sigma > 100:
                    print(f"⚠️  HIGH SIGMA DETECTED: Set {calib_set_number}, Channel {idx}, σ={global_sigma:.2f} mK")
                    print(f"    Valid means: {valid_means[outlier_mask] if np.sum(outlier_mask) > 0 else valid_means}")
                    print(f"    IQR bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")
                
                if calib_set_number not in self.global_stats:
                    self.global_stats[calib_set_number] = {}
                self.global_stats[calib_set_number][idx] = {
                    "mean": global_mean,
                    "sigma": global_sigma,
                    "run_means": run_means.tolist(),
                    "run_stds": run_stds.tolist(),
                    "run_labels": run_labels
                }

                # Display 'N/A' for non-finite values to avoid 'nan' showing up on plots
                def fmt(x):
                    try:
                        if x is None or (isinstance(x, float) and (np.isnan(x) or not np.isfinite(x))):
                            return 'N/A'
                        return f"{x:.3f}"
                    except Exception:
                        return 'N/A'

                stats_text = f"$\\mu$ = {fmt(global_mean)} mK\n$\\sigma$ = {fmt(global_sigma)} mK"
                axes[idx].text(
                    0.95, 0.95,
                    stats_text,
                    fontsize=9,
                    fontweight="bold",
                    ha="right",
                    va="top",
                    transform=axes[idx].transAxes,
                    bbox=dict(boxstyle="round", facecolor="white", edgecolor="black", alpha=0.8)
                )

                axes[idx].legend(fontsize=8, loc="upper left", ncol=1)

            fig.suptitle(
                f"Offset Repeatability for Set {int(calib_set_number)} (Ref channels assigned per sensor)",
                fontsize=20,
                fontweight="bold"
            )
            fig.tight_layout()
            plot_filename = os.path.join(save_dir, f"offset_repeatability_set_{calib_set_number}.png")
            fig.savefig(plot_filename)
            print(f"Plot saved to: {plot_filename}")
            plt.close(fig)

        print("Global data saved in self.global_stats")

        # Save summary CSV/Excel (guarded by flags)
        csv_rows = []
        for calib_set, sensors in self.global_stats.items():
            for idx, stats in sensors.items():
                row = {
                    "CalibSetNumber": calib_set,
                    "SensorIndex": idx,
                    "WeightedMean": stats["mean"],
                    "SigmaOfMeans": stats["sigma"]
                }
                for i, (mean, std, label) in enumerate(zip(stats["run_means"], stats["run_stds"], stats["run_labels"])):
                    row[f"Run_{i + 1}_Label"] = label
                    row[f"Run_{i + 1}_Mean"] = mean
                    row[f"Run_{i + 1}_Std"] = std
                csv_rows.append(row)

        df_csv = pd.DataFrame(csv_rows)
        # Resolve effective flags: prefer explicit args, otherwise use instance defaults
        effective_write_csv = self.write_csv if write_csv is None else bool(write_csv)
        effective_write_excel = self.write_excel if write_excel is None else bool(write_excel)

        csv_path = os.path.join(save_dir, "offset_repeatability_summary.csv")
        if effective_write_csv:
            df_csv.to_csv(csv_path, index=False)
            print(f"Summary CSV saved to: {csv_path}")
        else:
            print("Skipping CSV write (write_csv disabled)")

        # Additionally save a CSV with skipped runs due to defective channels, if any
        try:
            skipped_csv_path = os.path.join(save_dir, 'skipped_runs_due_to_defects.csv')
            if 'skipped_runs_list' in locals() and skipped_runs_list:
                pd.DataFrame(skipped_runs_list).to_csv(skipped_csv_path, index=False)
                print(f"Skipped runs (defects) saved to: {skipped_csv_path}")
            else:
                print("No skipped runs due to defects were recorded.")
        except Exception as e:
            print(f"Warning: could not write skipped-runs CSV ({e})")
        
        # Save a CSV with outliers filtered by IQR method, if any
        try:
            outliers_csv_path = os.path.join(save_dir, 'outliers_filtered_by_iqr.csv')
            if 'outliers_filtered' in locals() and outliers_filtered:
                pd.DataFrame(outliers_filtered).to_csv(outliers_csv_path, index=False)
                print(f"Outliers filtered by IQR saved to: {outliers_csv_path}")
            else:
                print("No outliers were filtered by IQR method.")
        except Exception as e:
            print(f"Warning: could not write outliers CSV ({e})")

        excel_path = os.path.join(save_dir, "offset_repeatability_summary.xlsx")
        if effective_write_excel:
            try:
                df_csv.to_excel(excel_path, index=False)
                print(f"Excel saved to: {excel_path}")
            except Exception as e:
                print(f"Warning: could not write Excel file ({e}), continuing.")
        else:
            print("Skipping Excel write (write_excel disabled)")


    def calculate_weighted_mean_offsets(self, selected_sets=None) -> dict:
        """
        Calcula una matriz de constantes de calibración y los errores asociados (RMS de offsets)
        para cada CalibSetNumber.

        Retorna:
            dict: Un diccionario donde las claves son los CalibSetNumber y los valores son
                  las matrices 14x14 de constantes de calibración con nombres de sensores.
        """
        try:
            calibration_constants = {}  # Dictionary to store calibration constant matrices
            calibration_errors = {}     # Diccionario para almacenar matrices de errores asociados
            
            # Filtrar conjuntos de datos si se proporciona `selected_sets`, donde seleccionamos 1 o varios del total de sets
            calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else set(selected_sets)

            for calib_set_number, runs_in_set in self.runs_by_set.items():
                if calib_set_number not in calib_sets_to_process:
                    continue
                print(f"\nProcessing CalibSetNumber: {calib_set_number}")

                # Find the run with the most sensors (reference) that is usually the first to reorder the offset matrices if in any run the same mapping does not occur
                max_sensors = 0
                reference_run = None

                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        num_sensors = len(run_instance.sensor_mapping)
                        if num_sensors > max_sensors:
                            max_sensors = num_sensors
                            reference_run = run_instance
                    else:
                        print(f"Warning: sensor_mapping is None for run {run_instance.filename}. Skipping this run.")

                if not reference_run:
                    print(f"Warning: No valid run found to compute offsets for CalibSetNumber {calib_set_number}, skipping this set.")
                    continue

                print(f"  Selected reference run: {reference_run.filename}")
                print(f"  Reference sensor mapping: {reference_run.sensor_mapping}")

                reference_sensors = list(reference_run.sensor_mapping.values())
                print(f"  Reference sensors: {reference_sensors}")

                # Extraer las matrices de offsets y RMS para este set
                offsets_matrices = []
                rms_matrices = []

                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        offsets = run_instance.offsets()
                        rms_offsets = run_instance.stat_err_offsets()

                        # Crear DataFrames con el orden actual
                        offsets_df = pd.DataFrame(offsets)
                        rms_df = pd.DataFrame(rms_offsets)

                        # Reorder rows and columns according to reference order. WE SHOULD CALCULATE IT ONLY FOR THE LAST 20 MIN.
                        offsets_df = offsets_df.reindex(index=reference_sensors, columns=reference_sensors)
                        rms_df = rms_df.reindex(index=reference_sensors, columns=reference_sensors)

                        print(f"  → Offsets matrix for {run_instance.filename}:")
                        print(offsets_df)
                        print(f"  → Errors (RMS) matrix for {run_instance.filename}:")
                        print(rms_df)

                        offsets_matrices.append(offsets_df.values)
                        rms_matrices.append(rms_df.values)

                    else:
                        print(f"Advertencia: No se puede calcular offsets ni RMS para el run {run_instance.filename} porque sensor_mapping es None.")

                # Convertir las listas de matrices a arrays numpy para facilitar las operaciones
                offsets_array = np.array(offsets_matrices)  # Forma (num_runs, 14, 14)
                rms_array = np.array(rms_matrices)          # Forma (num_runs, 14, 14)

                # Create a valid boolean mask: excludes NaN and values greater than 1 in offsets
                valid_mask = ~np.isnan(offsets_array) & (offsets_array <= 1)

                # Create a mask for valid values in RMS (excludes NaN)
                valid_rms_mask = ~np.isnan(rms_array)

                # Combined final mask: valid values in both offsets and RMS
                final_mask = valid_mask & valid_rms_mask

                # Calcular los pesos como el inverso del cuadrado de los RMS
                # Avoid division by zero: only compute weights where rms != 0
                weights = np.zeros_like(rms_array, dtype=float)  # Inicializar matriz de pesos
                mask_nonzero_rms = final_mask & (rms_array != 0)
                if np.any(mask_nonzero_rms):
                    weights[mask_nonzero_rms] = 1.0 / (rms_array[mask_nonzero_rms] ** 2)

                # Calcular el numerador y el denominador de la media ponderada
                weighted_sum = np.sum(offsets_array * weights, axis=0)  # Suma ponderada de offsets
                total_weights = np.sum(weights, axis=0)  # Suma de los pesos

                # Avoid division by zero at positions where all weights are zero
                with np.errstate(divide='ignore', invalid='ignore'):
                    constants_matrix = np.divide(weighted_sum, total_weights)
                    constants_matrix[total_weights == 0] = np.nan  # Assign NaN where there is no valid data
                    
                print("\n=== ERROR CALCULATION ===")
                print(f"offsets_array shape: {offsets_array.shape}")
                print("Example offsets_array[0]:")
                print(offsets_array[0])  # First run

                # Calculate the associated error as the RMS of offsets for each position (i, j). REVIEW. 
                #errors_matrix = np.sqrt(np.mean(offsets_array ** 2, axis=0))
                errors_matrix = np.std(offsets_array, axis=0, ddof=1)
                
                print("Calculated RMS errors matrix (errors_matrix):")
                print(errors_matrix)

                # Obtener los nombres de los sensores desde el primer run
                sensor_names = list(runs_in_set.values())[0].sensor_mapping.values()
                

                # Crear DataFrames para las matrices de constantes y errores
                constants_df = pd.DataFrame(constants_matrix, index=sensor_names, columns=sensor_names)
                errors_df = pd.DataFrame(errors_matrix, index=sensor_names, columns=sensor_names)
                

                # Print matrices for debugging
                print(f"Constants matrix for CalibSetNumber {calib_set_number}:")
                print(constants_df)
                print(f"Errors matrix for CalibSetNumber {calib_set_number}:")
                print(errors_df)

                # Almacenar las matrices resultantes en los diccionarios
                calibration_constants[calib_set_number] = constants_df
                calibration_errors[calib_set_number] = errors_df

            # Save the calibration and error matrices to an Excel file only if we have content
            if calibration_constants:
                excel_filename = 'calibration_constants_and_errors.xlsx'
                with pd.ExcelWriter(excel_filename) as writer:
                    for calib_set_number in calibration_constants:
                        # Save calibration constant matrices
                        constants_df = calibration_constants[calib_set_number]
                        # Use a safe sheet name
                        sheet_name_consts = f'CalibSet_{int(calib_set_number)}'
                        constants_df.to_excel(writer, sheet_name=sheet_name_consts)

                        # Guardar matrices de errores asociados
                        errors_df = calibration_errors[calib_set_number]
                        sheet_name_errors = f'Errors_CalibSet_{int(calib_set_number)}'
                        errors_df.to_excel(writer, sheet_name=sheet_name_errors)

                print(f"Calculation of constants and errors complete and saved in '{excel_filename}'.")
            else:
                print("No calibration constants calculated; skipping Excel export.")
            return calibration_constants, calibration_errors  # Add the errors

        except Exception as e:
            raise RuntimeError(f"Error calculating constants and associated errors: {e}")
            

    def plot_error_vs_distance_general(
        self,
        calibration_errors: dict,
        reference_selection: Literal['red_only', 'all_12', 'all_12_excl_discards'] = 'all_12',
        convert_to_mK: bool = True,
        title_prefix: str = ""
    ):
        all_distances = []
        all_errors = []
        processed_sets = []

        for calib_set_number, runs in self.runs_by_set.items():
            if calib_set_number not in calibration_errors:
                continue

            reference_run = next((run for run in runs.values() if run.sensor_mapping and len(run.sensor_mapping) >= 12), None)
            if reference_run is None:
                continue

            mapping_values = list(reference_run.sensor_mapping.values())[:12]
            mapping_order = [int(s) for s in mapping_values]

            if reference_selection == 'red_only':
                red_sensors = self.sensors_raised_by_set.get(calib_set_number, [])
                ref_pairs = [(r, o) for r in red_sensors if r in mapping_order for o in mapping_order if o != r]
            elif reference_selection == 'all_12':
                ref_pairs = [(mapping_order[i], mapping_order[j]) for i in range(len(mapping_order)) for j in range(len(mapping_order)) if i != j]
            elif reference_selection == 'all_12_excl_discards':
                excluded_sensors = self.discarded_sensors.get(calib_set_number, [])
                filtered_mapping = [s for s in mapping_order if s not in excluded_sensors]
                if len(filtered_mapping) < 2:
                    continue
                ref_pairs = [(filtered_mapping[i], filtered_mapping[j]) for i in range(len(filtered_mapping)) for j in range(i + 1, len(filtered_mapping))]
                processed_sets.append(str(int(calib_set_number)))  # Solo registro en este modo
            else:
                raise ValueError(f"Unknown reference_selection: {reference_selection}")

            errors_df = calibration_errors[calib_set_number]
            errors_df.index = errors_df.index.astype(int)
            errors_df.columns = errors_df.columns.astype(int)

            for s1, s2 in ref_pairs:
                try:
                    dist_idx_1 = mapping_order.index(s1)
                    dist_idx_2 = mapping_order.index(s2)
                except ValueError:
                    continue

                dist = min(abs(dist_idx_1 - dist_idx_2), 12 - abs(dist_idx_1 - dist_idx_2))
                if not (1 <= dist <= 6):
                    continue

                try:
                    error_val = errors_df.loc[s1, s2]
                except KeyError:
                    try:
                        error_val = errors_df.loc[s2, s1]
                    except KeyError:
                        continue

                if not pd.isna(error_val):
                    if convert_to_mK:
                        error_val *= 1000
                    all_distances.append(dist)
                    all_errors.append(error_val)

        distances = np.arange(1, 7)
        mean_errors = []
        stderr_errors = []

        for d in distances:
            errores_d = [e for dist, e in zip(all_distances, all_errors) if dist == d]
            if errores_d:
                media = np.mean(errores_d)
                std = np.std(errores_d)
                stderr = std / np.sqrt(len(errores_d))
            else:
                media = np.nan
                stderr = np.nan
            mean_errors.append(media)
            stderr_errors.append(stderr)

        # --- Auxiliary function to format numbers ---
        def format_value(value, is_mK=True):
            if pd.isna(value):
                return "NaN"
            if is_mK:
                if 0 < abs(value) < 0.01:
                    return f"{value:.3f}"
                else:
                    return f"{value:.2f}"
            else: # Asumimos Kelvin
                if 0 < abs(value) < 0.00001:
                    return f"{value:.6f}"
                else:
                    return f"{value:.4f}"

        
        ### **Plot 1: Scatter**
       
        plt.figure(figsize=(7, 5))
        plt.scatter(all_distances, all_errors, color='teal', alpha=0.5, edgecolors='black')
        plt.title(f"{title_prefix} - Calibration Error vs Circular Distance", fontsize=13, fontweight='bold')
        plt.xlabel("Circular Distance", fontsize=11)
        plt.ylabel("Calibration Error (RMS, mK)" if convert_to_mK else "Calibration Error (RMS, K)", fontsize=11)
        plt.xticks(range(1, 7))

        # Y limit logic for Plot 1: Dynamic if 'all_12_excl_discards', Fixed to 5 mK if not
        if reference_selection == 'all_12_excl_discards':
            if all_errors:
                max_error = np.max(all_errors)
                plt.ylim(0, max_error * 1.2 if max_error > 0 else (0.1 if convert_to_mK else 0.0001))
            else:
                plt.ylim(0, 1) # Default value if no errors
        else: # 'red_only' or 'all_12'
            plt.ylim(0, 5) # Fixed limit of 5 mK

        plt.grid(True, linestyle='--', alpha=0.6)

        if reference_selection == 'all_12_excl_discards':
            if processed_sets:
                plt.figtext(0.5, -0.08, f"Processed Sets: {', '.join(processed_sets)}", wrap=True, horizontalalignment='center', fontsize=9)

        plt.tight_layout()
        plt.show()

        
        ### **Plot 2: Mean and Error**
        
        plt.figure(figsize=(8, 6))
        plt.errorbar(distances, mean_errors, yerr=stderr_errors, fmt='-o', color='darkorange', ecolor='gray',
                     capsize=5, label='Mean ± Standard Error of the Mean')

        for d, m, s in zip(distances, mean_errors, stderr_errors):
            if not np.isnan(m) and not np.isnan(s):
                m_str = format_value(m, convert_to_mK)
                s_str = format_value(s, convert_to_mK)
                offset_y = 0.1 if convert_to_mK else (0.0001 if m+s > 0 else 0.00001)
                plt.text(d, m + s + offset_y, f"{m_str}±{s_str}", ha='center', fontsize=9, color='darkorange')


        plt.title(f"{title_prefix} - Mean Error vs Circular Distance", fontsize=13, fontweight='bold')
        plt.xlabel("Circular Distance", fontsize=11)
        plt.ylabel("Mean Calibration Error (mK)" if convert_to_mK else "Mean Calibration Error (K)", fontsize=11)
        plt.xticks(distances)

        # Y limit logic for Plot 2: Dynamic if 'all_12_excl_discards', Fixed to 5 mK if not
        if reference_selection == 'all_12_excl_discards':
            valid_ymax_vals = [m + s for m, s in zip(mean_errors, stderr_errors) if not (np.isnan(m) or np.isnan(s))]
            if valid_ymax_vals:
                ymax = max(valid_ymax_vals)
                plt.ylim(0, ymax * 1.2 if ymax > 0 else (0.1 if convert_to_mK else 0.0001))
            else:
                plt.ylim(0, 1) # Default value
        else: # 'red_only' or 'all_12'
            plt.ylim(0, 5) # Fixed limit of 5 mK

        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.show()

        
        ### **Plot 3: Histograms**
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 8))
        axes = axes.flatten()

        # X limit logic for Histograms: Dynamic if 'all_12_excl_discards', Fixed to 5 mK if not
        if reference_selection == 'all_12_excl_discards':
            # Calculate the maximum error observed in all_errors to dynamically adjust the upper xlim
            if all_errors:
                max_all_errors = np.max(all_errors)
                if convert_to_mK:
                    hist_xlim_upper = np.ceil(max_all_errors / 0.5) * 0.5 if max_all_errors > 0 else 1
                    bin_edges_step = 0.5
                else: # Kelvin
                    hist_xlim_upper = max(0.0055, max_all_errors * 1.15 if max_all_errors > 0 else 0.001)
                    bin_edges_step = hist_xlim_upper / 11
            else:
                hist_xlim_upper = 1 if convert_to_mK else 0.001
                bin_edges_step = 0.1 if convert_to_mK else 0.0001
        else: # 'red_only' or 'all_12'
            hist_xlim_upper = 5 # Fixed limit of 5 mK
            bin_edges_step = 0.5 # Fixed step

        bin_edges = np.arange(0, hist_xlim_upper + bin_edges_step/2, bin_edges_step)

        for i, d in enumerate(distances):
            errores_d = [e for dist, e in zip(all_distances, all_errors) if dist == d]
            if errores_d:
                mu = np.mean(errores_d)
                sigma = np.std(errores_d)

                mu_str = format_value(mu, convert_to_mK)
                sigma_str = format_value(sigma, convert_to_mK)

                axes[i].hist(errores_d, bins=bin_edges, alpha=0.7, color='steelblue', edgecolor='black')
                axes[i].set_title(f"Dist {d} – μ={mu_str}, σ={sigma_str}", fontsize=11)
                axes[i].set_xlabel("Calibration Error (mK)" if convert_to_mK else "Calibration Error (K)")
                axes[i].set_ylabel("Frequency")

                axes[i].set_xlim(0, hist_xlim_upper)

                axes[i].grid(True, linestyle='--', alpha=0.5)
            else:
                axes[i].set_visible(False)

        plt.suptitle(f"{title_prefix} - Error Distributions by Circular Distance", fontsize=14, fontweight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()


    def plot_global_means(self, save_dir="plot_global_means", selected_sets=None, max_sets_per_plot=7):
        """
        Genera gráficos de la media global de los offsets (global_mean)
        para cada sensor en todos los CalibSetNumber, dividiendo los plots en grupos según max_sets_per_plot.
        Excluye sensores descartados y los dos últimos canales de referencia (13 y 14).
        Ajusta visualización según número de sets y sensores, y asigna colores distintos por set.

        Parámetros:
            save_dir (str): Directorio donde se guardarán las imágenes de los gráficos.
            selected_sets (list, optional): Lista de CalibSetNumber a incluir. Si es None, se usan todos.
            max_sets_per_plot (int): Número máximo de sets por gráfico.
        """
      

        if not hasattr(self, "global_stats"):
            print("Error: No se encontraron datos en self.global_stats. Primero ejecuta offset_repeatability().")
            return

        # Close any existing figures to avoid residual data from previous executions
        plt.close('all')
        
        os.makedirs(save_dir, exist_ok=True)

        calib_sets = list(self.global_stats.keys())
        if selected_sets:
            calib_sets = [cs for cs in calib_sets if cs in selected_sets]

        num_sets = len(calib_sets)
        print(f"Processing {num_sets} sets.")
        if num_sets == 0:
            print("No sets available to plot. Exiting plot_global_means.")
            return

        num_plots = math.ceil(num_sets / max_sets_per_plot)
        chunk_size = math.ceil(num_sets / num_plots)
        chunks = [calib_sets[i:i + chunk_size] for i in range(0, num_sets, chunk_size)]

        all_means = []

        for i, subset in enumerate(chunks):
            total_sensors = sum(len(self.global_stats[cs]) for cs in subset)
            width = max(12, len(subset) * 1.5, total_sensors * 0.2)
            plt.figure(figsize=(width, 6))
            subset_means = []

            # Colormap para diferenciar sets
            cmap = get_cmap('tab10')
            colors = [cmap(j % 10) for j in range(len(subset))]

            for j, calib_set_number in enumerate(subset):
                color = colors[j]
                sensors_data = self.global_stats[calib_set_number]
                discarded = set(self.discarded_sensors.get(calib_set_number, []))

                sensor_keys = [k for k in sensors_data.keys() if isinstance(k, (int, float, str)) and str(k).isdigit()]
                use_ids = all(int(k) >= 48000 for k in sensor_keys)

                example_run = next(iter(self.runs_by_set[calib_set_number].values()), None)
                channel_to_id = {}
                if example_run and example_run.sensor_mapping:
                    channel_to_id = {int(k.replace("channel_", "")) - 1: int(v) for k, v in example_run.sensor_mapping.items()}
                    for ch in [12, 13]:
                        sensor_id_ult = channel_to_id.get(ch)
                        if sensor_id_ult is not None:
                            discarded.add(sensor_id_ult)

                sensor_ids = []
                if use_ids:
                    sensor_ids = [str(k) for k in sensor_keys if int(k) not in discarded]
                else:
                    for k in sensor_keys:
                        ch_index = int(k)
                        sensor_id = channel_to_id.get(ch_index, ch_index)
                        if sensor_id not in discarded:
                            sensor_ids.append(str(k))

                # Build aligned lists of sensor_names and global_means
                sensor_names = []
                global_means = []
                
                for sid in sensor_ids:
                    key = sid
                    if sid in sensors_data:
                        key = sid
                    elif sid.isdigit() and int(sid) in sensors_data:
                        key = int(sid)
                    else:
                        continue
                    
                    mean_val = sensors_data[key].get("mean")
                    
                    # Convert masked arrays to regular values (fill masked with nan)
                    if isinstance(mean_val, np.ma.core.MaskedConstant) or (hasattr(mean_val, 'mask') and np.ma.is_masked(mean_val)):
                        continue  # Skip masked values entirely
                    
                    # Only include finite values
                    if mean_val is not None and pd.notnull(mean_val) and np.isfinite(mean_val):
                        # Determine sensor name - ensure it's a plain string
                        if example_run and example_run.sensor_mapping:
                            try:
                                ch_index = int(sid)
                                raw_sensor_id = example_run.sensor_mapping.get(f"channel_{ch_index+1}", f"Sensor {ch_index+1}")
                                # Ensure raw_sensor_id is converted properly even if it's a masked value
                                sensor_name = str(raw_sensor_id) if not (isinstance(raw_sensor_id, np.ma.core.MaskedConstant) or (hasattr(raw_sensor_id, 'mask') and np.ma.is_masked(raw_sensor_id))) else f"Sensor {ch_index+1}"
                            except Exception:
                                sensor_name = f"Sensor {sid}"
                        else:
                            sensor_name = f"Sensor {sid}"
                        
                        sensor_names.append(sensor_name)
                        global_means.append(mean_val)

                subset_means.extend(global_means)
                all_means.extend(global_means)

                # Only scatter if we have valid data
                if global_means and sensor_names:
                    # Debug: Check what types we have
                    print(f"Set {calib_set_number}: len sensor_names={len(sensor_names)}, len global_means={len(global_means)}")
                    if sensor_names:
                        print(f"  First sensor_name: {sensor_names[0]!r} (type: {type(sensor_names[0])})")
                        print(f"  All sensor_name types: {set(type(x).__name__ for x in sensor_names)}")
                    if global_means:
                        print(f"  First global_mean: {global_means[0]!r} (type: {type(global_means[0])})")
                        print(f"  All global_mean types: {set(type(x).__name__ for x in global_means)}")
                    
                    plt.scatter(sensor_names, global_means, marker='o', color=color, label=f"Set {calib_set_number}")

            # Skip this plot if no valid data was collected for any set in this subset
            # Filter out non-finite values from subset_means
            subset_means_array = np.array(subset_means)
            finite_subset = subset_means_array[np.isfinite(subset_means_array)]
            
            if len(finite_subset) == 0:
                plt.close()
                print(f"Skipping plot part {i+1}: no valid finite data in sets {subset[0]:.0f} to {subset[-1]:.0f}")
                continue

            overall_mean = np.mean(finite_subset)
            overall_std = np.std(finite_subset)
            legend_title = f"Mean: {overall_mean:.2f} mK\nStd: {overall_std:.2f} mK"

            plt.xlabel("Sensor ID", fontsize=14, fontweight='bold')
            plt.ylabel("Global Mean Offset (mK)", fontsize=14, fontweight='bold')

            if len(subset) == 1:
                plt.title(f"Offset Variability - Set {subset[0]:.0f}", fontsize=16, fontweight='bold')
            else:
                plt.title(f"Offset Variability - Sets {subset[0]:.0f} to {subset[-1]:.0f}", fontsize=16, fontweight='bold')

            num_sensors = max(len(self.global_stats[cs]) for cs in subset)
            if num_sensors <= 5:
                rotation = 0
            elif num_sensors <= 15:
                rotation = 30
            elif num_sensors <= 30:
                rotation = 45
            else:
                rotation = 60

            plt.xticks(rotation=rotation, ha="right", fontsize=6)
            plt.legend(title=legend_title, title_fontproperties={'weight': 'bold'}, loc='upper right')
            plt.grid(True, linestyle="--", alpha=0.5)

            plot_filename = os.path.join(save_dir, f"global_mean_offsets_part_{i+1}.png")
            plt.savefig(plot_filename, bbox_inches='tight')
            print(f"Plot saved to: {plot_filename}")
            plt.show()


    def plot_global_sigmas(self, save_dir="plot_global_sigmas", selected_sets=None, max_sets_per_plot=7):
        if not hasattr(self, "global_stats"):
            print("Error: No data found in self.global_stats. Run offset_repeatability() first.")
            return

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        calib_sets = list(self.global_stats.keys())
        if selected_sets:
            calib_sets = [cs for cs in calib_sets if cs in selected_sets]

        num_sets = len(calib_sets)
        print(f"Processing {num_sets} sets.")

        if num_sets == 0:
            print("No sets available to plot. Exiting plot_global_sigmas.")
            return

        num_plots = math.ceil(num_sets / max_sets_per_plot)
        chunk_size = math.ceil(num_sets / num_plots)
        chunks = [calib_sets[i:i + chunk_size] for i in range(0, num_sets, chunk_size)]

        all_sigmas = []
        all_sigmas_descartados = []

        # =========================
        # SCATTER PLOTS POR SETS
        # =========================
        for i, subset in enumerate(chunks):
            plt.figure(figsize=(12, 6))
            subset_sigmas = []

            for calib_set_number in subset:
                sensors_data = self.global_stats[calib_set_number]
                descartados = set(self.discarded_sensors.get(float(calib_set_number), []))

                sensor_keys = [k for k in sensors_data.keys() if isinstance(k, (int, float, str)) and str(k).isdigit()]
                use_ids = all(int(k) >= 48000 for k in sensor_keys)

                example_run = next(iter(self.runs_by_set[calib_set_number].values()), None)
                channel_to_id = {}

                if example_run and example_run.sensor_mapping:
                    channel_to_id = {int(k.replace("channel_", "")) - 1: int(v)
                                     for k, v in example_run.sensor_mapping.items()}
                    for ch in [12, 13]:
                        sensor_id_ult = channel_to_id.get(ch)
                        if sensor_id_ult is not None:
                            descartados.add(sensor_id_ult)

                for k in sensor_keys:
                    try:
                        key_int = int(k)
                    except:
                        continue

                    if example_run and example_run.sensor_mapping:
                        sensor_id_candidato = channel_to_id.get(key_int, key_int)
                    else:
                        sensor_id_candidato = key_int

                    ultimos_canales_ids = [channel_to_id.get(12), channel_to_id.get(13)]
                    if sensor_id_candidato in descartados and sensor_id_candidato not in ultimos_canales_ids:
                        key_use = k if k in sensors_data else key_int
                        sigma = sensors_data[key_use].get("sigma")
                        # only collect finite numeric sigmas (skip None, NaN and inf)
                        if sigma is not None and pd.notnull(sigma) and np.isfinite(sigma):
                            all_sigmas_descartados.append(sigma)

                if use_ids:
                    sensor_ids = [str(k) for k in sensor_keys if int(k) not in descartados]
                else:
                    sensor_ids = []
                    for k in sensor_keys:
                        ch_index = int(k)
                        sensor_id = channel_to_id.get(ch_index)
                        if sensor_id is None:
                            sensor_ids.append(str(k))
                        elif sensor_id not in descartados:
                            sensor_ids.append(str(k))

                # Build aligned lists of names and sigmas so x and y have same length
                plot_names = []
                plot_sigmas = []
                for sid in sensor_ids:
                    key = sid
                    if sid in sensors_data:
                        key = sid
                    elif sid.isdigit() and int(sid) in sensors_data:
                        key = int(sid)
                    else:
                        continue

                    sigma = sensors_data[key].get("sigma")
                    # only collect finite numeric sigmas; skip NaN/None and infinities
                    if sigma is not None and pd.notnull(sigma) and np.isfinite(sigma):
                        # determine display name for this sensor
                        if example_run and example_run.sensor_mapping:
                            try:
                                ch_index = int(sid)
                                sensor_name = str(example_run.sensor_mapping.get(f"channel_{ch_index+1}", f"Sensor {ch_index+1}"))
                            except Exception:
                                sensor_name = f"Sensor {sid}"
                        else:
                            sensor_name = f"Sensor {sid}"

                        plot_names.append(sensor_name)
                        plot_sigmas.append(sigma)

                subset_sigmas.extend(plot_sigmas)
                all_sigmas.extend(plot_sigmas)

                # Scatter only the aligned pairs
                if plot_names and plot_sigmas:
                    plt.scatter(plot_names, plot_sigmas, marker='o')

            # Use NaN-safe aggregations to avoid NaN propagation
            overall_sigma_mean = float(np.nanmean(subset_sigmas)) if subset_sigmas else 0.0
            overall_sigma_std = float(np.nanstd(subset_sigmas)) if subset_sigmas else 0.0
            legend_title = f"μ: {overall_sigma_mean:.2f} mK\nσ: {overall_sigma_std:.2f} mK"

            plt.xlabel("Sensor ID", fontsize=14, fontweight='bold')
            plt.ylabel("Calibration Constant Systematic Errors (mK)", fontsize=12, fontweight='bold')
            plt.ylim(0, 6)
            plt.title(f"Sets {subset[0]:.0f} to {subset[-1]:.0f}", fontsize=18, fontweight='bold')
            plt.xticks(rotation=45, ha="right", fontsize=6)
            plt.legend(title=legend_title, title_fontproperties={'weight': 'bold'}, loc='upper left')
            plt.grid(True, linestyle="--", alpha=0.5)

            plot_filename = os.path.join(save_dir, f"global_sigma_offsets_part_{i+1}.png")
            plt.savefig(plot_filename)
            plt.show()

        # =========================
        # HISTOGRAMS BY ROUNDS (dynamic up to 4 rounds)
        # =========================
        def collect_sigmas(sets, include_descartados=False):
            """Collects sigmas for a set of sets."""
            sigmas_list = []
            for s in sets:
                sensors_data = self.global_stats[s]
                example_run = next(iter(self.runs_by_set[s].values()), None)
                channel_to_id = {}
                if example_run and example_run.sensor_mapping:
                    channel_to_id = {int(k.replace("channel_", "")) - 1: int(v) for k, v in example_run.sensor_mapping.items()}
                ultimos_canales = [channel_to_id.get(12), channel_to_id.get(13)]

                descartados = set(self.discarded_sensors.get(float(s), [])) if not include_descartados else set()
                if not include_descartados:
                    if example_run and example_run.sensor_mapping:
                        for ch in [12, 13]:
                            sid = channel_to_id.get(ch)
                            if sid is not None:
                                descartados.add(sid)

                for k in sensors_data.keys():
                    if not str(k).isdigit():
                        continue
                    sid = int(k)
                    sid_mapped = channel_to_id.get(sid, sid) if channel_to_id else sid

                    if include_descartados:
                        if sid_mapped in ultimos_canales:
                            continue
                    else:
                        if sid_mapped in descartados:
                            continue

                    sigma = sensors_data[k].get("sigma")
                    # skip None, NaN and infinite values (these indicate insufficient/invalid data)
                    if sigma is not None and pd.notnull(sigma) and np.isfinite(sigma):
                        sigmas_list.append(sigma)
            return sigmas_list

        def plot_hist_rounds(include_descartados=False, filename_prefix="global_sigma_histogram_rounds"):
            # Build rounds from self.set_rounds if available
            # Only include sets that are in self.global_stats (i.e., were processed)
            available_sets = set(self.global_stats.keys())
            
            rounds_map = {}
            if hasattr(self, "set_rounds") and self.set_rounds:
                # invert mapping: round -> list of sets, filtered by available sets
                for s, r in self.set_rounds.items():
                    if s in available_sets:
                        rounds_map.setdefault(int(r), []).append(s)
            else:
                # fallback to the originally coded logic
                rounds_map = {
                    1: [s for s in calib_sets if s in available_sets and (3 <= int(s) <= 48 or int(s) in [59, 60, 61])],
                    2: [s for s in calib_sets if s in available_sets and 49 <= int(s) <= 55],
                    3: [s for s in calib_sets if s in available_sets and int(s) in [57, 62]],
                    4: [s for s in calib_sets if s in available_sets and int(s) == 63],
                }

            # Build human-readable labels and filter empties
            rounds = {}
            for rnum, sets_list in rounds_map.items():
                if not sets_list:
                    continue
                # build compact label for sets_list (e.g., '3-48,59-60')
                sorted_sets = sorted(int(x) for x in sets_list)
                compact_parts = []
                start = None
                prev = None
                for v in sorted_sets:
                    if start is None:
                        start = v
                        prev = v
                        continue
                    if v == prev + 1:
                        prev = v
                        continue
                    # close previous range
                    if start == prev:
                        compact_parts.append(str(start))
                    else:
                        compact_parts.append(f"{start}-{prev}")
                    start = v
                    prev = v
                if start is not None:
                    if start == prev:
                        compact_parts.append(str(start))
                    else:
                        compact_parts.append(f"{start}-{prev}")

                label = f"Round {rnum} (sets: {','.join(compact_parts)})"
                rounds[label] = sets_list

            # Recoger sigmas
            rounds_sigmas = {label: collect_sigmas(sets, include_descartados) for label, sets in rounds.items()}
            # Flatten while skipping NaN (collect_sigmas already skips NaN)
            combined_sigmas = [x for vals in rounds_sigmas.values() for x in vals]
            if not combined_sigmas:
                return

            # Use numpy functions that are robust to NaN (though sigmas lists should not contain NaN)
            mu_total = float(np.nanmean(combined_sigmas)) if combined_sigmas else 0
            sigma_total = float(np.nanstd(combined_sigmas)) if combined_sigmas else 0
            # Calculate bins based on data range: 1 bin per mK for both versions
            data_range = max(combined_sigmas) - min(combined_sigmas)
            if include_descartados:
                n_bins = max(int(np.ceil(data_range)), 20)  # At least 20 bins
            else:
                n_bins = max(int(np.ceil(data_range)), 12)  # At least 12 bins
            bins = np.histogram_bin_edges(combined_sigmas, bins=n_bins)
            ymax = max([max(np.histogram(v, bins=bins, density=True)[0]) if (v and len(v) > 0) else 0 for v in rounds_sigmas.values()]) * 1.1

            # Subplots separados - solo rounds con datos
            rounds_with_data = {label: sigmas for label, sigmas in rounds_sigmas.items() if sigmas}
            n_rounds = len(rounds_with_data)
            if n_rounds == 0:
                print("No hay datos para generar histogramas por ronda")
                return
            # Crear grid óptima: 1 fila si n<=3, 2 filas si n==4
            if n_rounds <= 3:
                nrows, ncols = 1, n_rounds
            else:  # n_rounds == 4
                nrows, ncols = 2, 2
            fig, axes = plt.subplots(nrows, ncols, figsize=(7*ncols, 6*nrows), sharey=True, squeeze=False)
            axes = axes.flatten()

            fig.suptitle("Errors Distribution by Round" + (" (Including discarded sensors)" if include_descartados else ""),
                         fontsize=16, fontweight='bold')

            for ax, (label, sigmas) in zip(axes, rounds_with_data.items()):
                # skip NaN in per-round stats (collect_sigmas already filtered)
                valid_sigmas = [x for x in sigmas if pd.notnull(x)]
                mu = float(np.nanmean(valid_sigmas)) if valid_sigmas else 0
                sigma = float(np.nanstd(valid_sigmas)) if valid_sigmas else 0
                ax.hist(valid_sigmas, bins=bins, alpha=0.7, density=True)
                ax.set_title(label, fontweight='bold')
                ax.set_xlabel("Calibration Constant Reproducibility (mK)", fontweight='bold')
                ax.set_ylabel("Density", fontweight='bold')
                ax.text(0.95, 0.95, f"μ = {mu:.2f} mK\nσ = {sigma:.2f} mK",
                        ha='right', va='top', transform=ax.transAxes, fontsize=10,
                        bbox=dict(facecolor='white', alpha=0.8))
                ax.set_ylim(0, ymax)
                ax.grid(True, linestyle="--", alpha=0.5)

            # Ocultar subplots sobrantes (solo si hay subplot vacío)
            for idx in range(n_rounds, len(axes)):
                axes[idx].axis('off')

            plt.tight_layout()
            plt.savefig(os.path.join(save_dir, f"{filename_prefix}_subplots.png"))
            plt.show()

            # Solapado
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            colors = ["blue", "orange", "green", "red"]
            for (label, sigmas), c in zip(rounds_sigmas.items(), colors):
                valid_sigmas = [x for x in sigmas if pd.notnull(x)]
                mu = float(np.nanmean(valid_sigmas)) if valid_sigmas else 0
                sigma = float(np.nanstd(valid_sigmas)) if valid_sigmas else 0
                ax2.hist(valid_sigmas, bins=bins, alpha=0.5, color=c, density=True,
                         label=f"{label}\nμ={mu:.2f} mK\nσ={sigma:.2f} mK")
            ax2.set_xlabel("Calibration Constant Reproducibility (mK)", fontweight='bold')
            ax2.set_ylabel("Density", fontweight='bold')
            ax2.set_ylim(0, ymax)
            ax2.set_title("Errors Distribution by Round (Overlapped)" + (" (Including discarded)" if include_descartados else ""),
                          fontweight='bold')
            ax2.grid(True, linestyle="--", alpha=0.5)
            ax2.legend()
            # Calcular ancho de bin
            bin_width = bins[1] - bins[0] if len(bins) > 1 else 0
            ax2.text(0.95, 0.50,
                     f"Total μ={mu_total:.2f} mK\nTotal σ={sigma_total:.2f} mK\nbins={n_bins}\nbin width={bin_width:.2f} mK",
                     ha='right', va='top', transform=ax2.transAxes,
                     fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
            plt.savefig(os.path.join(save_dir, f"{filename_prefix}_overlap.png"))
            plt.show()

        # Execute for valid sensors and for discarded sensors
        plot_hist_rounds(include_descartados=False, filename_prefix="global_sigma_histogram_rounds")
        plot_hist_rounds(include_descartados=True, filename_prefix="global_sigma_histogram_rounds_all_sensors")


def _ensure_numeric(val):
    try:
        return float(val)
    except Exception:
        return None


def _safe_int(val):
    try:
        return int(float(val))
    except Exception:
        return None


def plot_runs_vs_set_and_repeatability(self, output_dir="runs_vs_set_plots", include_bad_for_repeatability=True):
    """
    Standalone function (can be bound to a Set instance) that:
    - Plots number of logfile rows per CalibSetNumber (bar plot)
    - For sets with >4 rows, calls the instance method offset_repeatability including BAD runs

    This is implemented as a standalone function to avoid restructuring existing class methods.
    It expects `self` to be an instance of `Set`.
    """
    import matplotlib.pyplot as plt
    os.makedirs(output_dir, exist_ok=True)

    # Coerce CalibSetNumber to numeric and keep only integer-like values (e.g., 3.0)
    try:
        self.logfile['CalibSetNumber'] = pd.to_numeric(self.logfile['CalibSetNumber'], errors='coerce')
    except Exception:
        pass

    # Keep only rows where CalibSetNumber is numeric and integer-like
    cs_numeric = pd.to_numeric(self.logfile['CalibSetNumber'], errors='coerce')
    integer_mask = cs_numeric.notna() & (cs_numeric % 1 == 0)
    numeric_log = self.logfile[integer_mask].copy()

    # Exclude filenames that contain '_pre' for the counts as well
    numeric_log_no_pre = numeric_log[~numeric_log['Filename'].str.contains('_pre', case=False, na=False)]

    counts = numeric_log_no_pre.groupby('CalibSetNumber').size().dropna()
    counts = counts[counts.index.notna()]
    counts = counts.sort_index()

    # Bar plot
    plt.figure(figsize=(12, 5))
    plt.bar([_safe_int(x) or x for x in counts.index], counts.values)
    plt.xlabel('CalibSetNumber')
    plt.ylabel('Number of runs (rows in logfile)')
    plt.title('Runs per integer CalibSetNumber (excluding filenames with "_pre")')
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    barpath = os.path.join(output_dir, 'runs_per_set.png')
    plt.tight_layout()
    plt.savefig(barpath)
    plt.close()
    print(f"Saved runs-per-set bar plot to: {barpath}")

    # Identify large sets (count >= 4)
    large_sets = [int(k) for k, v in counts.items() if v >= 4]
    if not large_sets:
        print("No eligible sets with 4 or more runs found after filtering.")
        return

    original_runs_by_set = getattr(self, 'runs_by_set', {}).copy()

    try:
        for cs in large_sets:
            print(f"Preparing repeatability for set {cs} (rows={counts.loc[float(cs)]})")
            rows = numeric_log[numeric_log['CalibSetNumber'] == float(cs)]
            if not include_bad_for_repeatability:
                rows = rows[rows['Selection'] != 'BAD']

            # Exclude filenames that contain '_pre'
            rows = rows[~rows['Filename'].str.contains('_pre', case=False, na=False)]

            temp_runs = {}
            for _, row in rows.iterrows():
                fname = row['Filename']
                try:
                    # Skip if filename contains _pre (extra safety)
                    if isinstance(fname, str) and '_pre' in fname.lower():
                        print(f"  Skipping filename with _pre: {fname}")
                        continue
                    r = Run(fname, self.logfile)
                    # Best-effort: try to associate sensors
                    try:
                        r.associate_sensors()
                    except Exception:
                        pass
                    temp_runs[fname] = r
                except Exception as e:
                    print(f"  Warning: could not create Run for {fname}: {e}")

            if not temp_runs:
                print(f"  No valid run instances for set {cs} after filtering, skipping.")
                continue

            # Only proceed if at least 4 runs remain for this set
            if len(temp_runs) < 4:
                print(f"  Skipping set {cs}: only {len(temp_runs)} eligible runs after filtering")
                continue

            # Set temporary mapping and call the instance method
            self.runs_by_set = {float(cs): temp_runs}
            set_save_dir = os.path.join(output_dir, f"repeatability_set_{cs}")
            try:
                # Call offset_repeatability which will save plots inside set_save_dir
                # set write_csv and write_excel to False so only plots are generated for now
                self.offset_repeatability(save_dir=set_save_dir, write_csv=False, write_excel=False)
            except Exception as e:
                print(f"  Error while running offset_repeatability for set {cs}: {e}")

    finally:
        # restore
        self.runs_by_set = original_runs_by_set


# Bind the helper function as a method on the Set class for convenience
try:
    Set.plot_runs_vs_set_and_repeatability = plot_runs_vs_set_and_repeatability  # type: ignore
except Exception:
    pass

