import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
from .runSTS import Run


class SetSTS:
    """
    Clase para agrupar y analizar múltiples runs con CalibSetNumber alfanuméricos.
    
    A diferencia de la clase Set original:
    - Soporta CalibSetNumber alfanuméricos (RESIST_SET0, FRAME_SET1, etc.)
    - No requiere configuración de sensores raised o discarded
    - Usa referencia fija configurable
    - Selecciona carpeta de datos según el tipo de set (resistences o frame_sensors)
    """
    
    def __init__(self, logfile: pd.DataFrame, data_folder: str = "frame_sensors") -> None:
        """
        Inicializa una instancia de SetSTS.
        
        Args:
            logfile: DataFrame con el LogFile completo
            data_folder: Carpeta donde buscar archivos de temperatura ('frame_sensors' o 'resistences')
        """
        self.logfile = logfile
        self.data_folder = data_folder  # 'frame_sensors' o 'resistences'
        self.runs_by_set = {}  # Dict: CalibSetNumber -> {filename: Run}
        self.offsets_data = None  # Matriz de offsets concatenados
        self.rms_offsets_data = None  # Matriz de RMS concatenados
        self.global_stats = {}  # Estadísticas globales por set
        
    def group_runs_by_set(self, calibset_pattern: str = None, selected_sets: list = None) -> None:
        """
        Agrupa runs por CalibSetNumber, filtrando por patrón alfanumérico.
        
        Args:
            calibset_pattern: Patrón para filtrar CalibSetNumber (ej: 'RESIST_SET', 'FRAME_SET')
            selected_sets: Lista de CalibSetNumber específicos a procesar (ej: ['RESIST_SET0', 'RESIST_SET1'])
        """
        # Filtrar por patrón si se especifica
        if calibset_pattern:
            mask = self.logfile["CalibSetNumber"].astype(str).str.contains(calibset_pattern, na=False)
            filtered_logfile = self.logfile[mask]
        else:
            filtered_logfile = self.logfile
        
        # Obtener CalibSetNumbers únicos
        calib_set_numbers = filtered_logfile["CalibSetNumber"].unique()
        
        # Palabras a excluir de los filenames
        excluded_keywords = ['pre', 'lar']
        
        for calib_set_number in calib_set_numbers:
            # Filtrar por selected_sets si se especifica
            if selected_sets and calib_set_number not in selected_sets:
                continue
                
            print(f"\n🔄 Processing CalibSetNumber: {calib_set_number}")
            
            # Filtrar runs de este CalibSetNumber
            runs_in_set = filtered_logfile[filtered_logfile["CalibSetNumber"] == calib_set_number]
            valid_runs = {}
            
            for _, run_row in runs_in_set.iterrows():
                filename = run_row["Filename"]
                selection = run_row.get("Selection", "GOOD")
                
                # Verificar que no contenga palabras excluidas y no esté marcado como BAD
                if isinstance(filename, str) and all(kw not in filename.lower() for kw in excluded_keywords):
                    if selection != "BAD":
                        try:
                            # Crear instancia de Run (de runSTS.py)
                            run_instance = Run(filename, self.logfile)
                            run_instance.associate_sensors()
                            run_instance.read_run_info()
                            run_instance.filter_faulty_channels()
                            
                            valid_runs[filename] = run_instance
                            print(f"  ✅ Included: {filename}")
                            
                        except Exception as e:
                            print(f"  ⚠️  Warning: failed to process {filename}: {e}")
                            continue
                    else:
                        print(f"  ❌ Excluded: {filename} (marked as BAD)")
                else:
                    print(f"  ❌ Excluded: {filename} (contains excluded keyword)")
            
            # Guardar solo si hay runs válidos
            if valid_runs:
                self.runs_by_set[calib_set_number] = valid_runs
                print(f"  📊 Total valid runs in {calib_set_number}: {len(valid_runs)}")
        
        print(f"\n✅ Grouping complete. Total sets processed: {len(self.runs_by_set)}")
    
    def calculate_offsets_and_rms(self, selected_sets: list = None, tini: int = 20, tend: int = 40) -> None:
        """
        Calcula offsets y RMS para todos los runs, manteniendo el orden de sensores.
        
        Args:
            selected_sets: Lista de CalibSetNumber a procesar
            tini: Tiempo inicial en minutos para calcular offsets
            tend: Tiempo final en minutos para calcular offsets
        """
        offsets_list = []
        rms_list = []
        keys_for_concat = []
        
        for calib_set_number, runs_in_set in self.runs_by_set.items():
            if selected_sets and calib_set_number not in selected_sets:
                continue
                
            print(f"\n📊 Processing CalibSetNumber: {calib_set_number}")
            
            # Encontrar run de referencia (con más sensores)
            max_sensors = 0
            reference_run = None
            for run_instance in runs_in_set.values():
                if run_instance.sensor_mapping is not None:
                    num_sensors = len(run_instance.sensor_mapping)
                    if num_sensors > max_sensors:
                        max_sensors = num_sensors
                        reference_run = run_instance
            
            if not reference_run:
                print(f"  ⚠️  No valid run found in set {calib_set_number}")
                continue
            
            reference_sensors = list(reference_run.sensor_mapping.values())
            print(f"  📌 Reference run: {reference_run.filename} with {max_sensors} sensors")
            
            for filename, run_instance in runs_in_set.items():
                print(f"    🔄 Processing: {filename}")
                
                if run_instance.sensor_mapping is None:
                    print(f"      ⚠️  No sensor mapping, skipping")
                    continue
                
                try:
                    # Calcular offsets y RMS
                    offsets = run_instance.offsets(tini=tini, tend=tend)
                    rms_offsets = run_instance.stat_err_offsets(tini=-20, tend=0)
                    
                    current_sensors = list(run_instance.sensor_mapping.values())
                    offsets_df = pd.DataFrame(offsets, index=current_sensors, columns=current_sensors)
                    rms_df = pd.DataFrame(rms_offsets, index=current_sensors, columns=current_sensors)
                    
                    # Reordenar según run de referencia
                    offsets_df = offsets_df.reindex(index=reference_sensors, columns=reference_sensors)
                    rms_df = rms_df.reindex(index=reference_sensors, columns=reference_sensors)
                    
                    offsets_list.append(offsets_df)
                    rms_list.append(rms_df)
                    keys_for_concat.append(calib_set_number)
                    
                    print(f"      ✅ Offsets computed: {offsets_df.shape}")
                    
                except Exception as e:
                    print(f"      ⚠️  Error computing offsets: {str(e)[:100]}")
                    continue
        
        # Construir matrices concatenadas
        if offsets_list:
            self.offsets_data = pd.concat(offsets_list, axis=1, keys=keys_for_concat)
            self.rms_offsets_data = pd.concat(rms_list, axis=1, keys=keys_for_concat)
            print(f"\n✅ Offsets and RMS calculations complete")
        else:
            print(f"\n⚠️  No offsets computed")
    
    def offset_repeatability(
        self, 
        tini: int = 20, 
        tend: int = 40, 
        save_dir: str = "offset_repeatability_sts", 
        selected_sets: list = None,
        ref_channel: int = 2,
        write_csv: bool = True,
        write_excel: bool = True
    ) -> None:
        """
        Calcula la repetibilidad de offsets para cada set, genera gráficos y guarda resultados.
        
        Args:
            tini: Tiempo inicial en minutos para la ventana de análisis
            tend: Tiempo final en minutos para la ventana de análisis
            save_dir: Directorio donde guardar plots y CSVs
            selected_sets: Lista de CalibSetNumber a procesar
            ref_channel: Canal de referencia fijo (default: 2)
            write_csv: Si True, guarda archivos CSV
            write_excel: Si True, guarda archivos Excel
        """
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        self.global_stats = {}
        skipped_runs_list = []
        
        calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else selected_sets
        
        for calib_set_number in calib_sets_to_process:
            runs = self.runs_by_set.get(calib_set_number)
            if runs is None:
                print(f"⚠️  WARNING: Set {calib_set_number} not found, skipping")
                continue
            
            print(f"\n{'='*60}")
            print(f"📊 Processing CalibSetNumber: {calib_set_number}")
            print(f"{'='*60}")
            
            filenames = list(runs.keys())
            first_run = runs[filenames[0]]
            
            if first_run.sensor_mapping is None:
                print(f"⚠️  WARNING: No sensor mapping for first run, skipping set")
                continue
            
            mapping = first_run.sensor_mapping
            
            # Crear diccionario de nombres de sensores
            sensor_names = {}
            for ch in range(1, 15):
                sensor_names[ch] = mapping.get(f"channel_{ch}", None)
            
            # Usar canal de referencia fijo
            ref_channel_por_sensor = {}
            print(f"📌 Using fixed reference channel: {ref_channel} → Sensor ID: {sensor_names.get(ref_channel)}")
            
            for ch in range(1, 15):
                if sensor_names[ch] is not None:
                    ref_channel_por_sensor[ch] = ref_channel
            
            # Configurar plots (3 filas x 5 columnas = 15 subplots, usamos 14)
            fig, axes = plt.subplots(3, 5, figsize=(21, 13))
            axes = axes.flatten()
            fig.subplots_adjust(top=0.80)
            for ax in axes[14:]:
                ax.set_visible(False)
            
            # Título general de la figura
            fig.suptitle(
                f"Offset Repeatability - {calib_set_number}\n"
                f"Reference Channel: {ref_channel} (Sensor {sensor_names.get(ref_channel)})\n"
                f"Time Window: {tini}-{tend} minutes",
                fontsize=16,
                fontweight="bold"
            )
            
            # Diccionarios para estadísticas
            offsets_all_runs = {ch: [] for ch in range(1, 15) if sensor_names[ch] is not None}
            rms_all_runs = {ch: [] for ch in range(1, 15) if sensor_names[ch] is not None}
            
            # Iterar sobre cada run del set
            for run_name, run_obj in runs.items():
                print(f"  🔄 Processing run: {run_name}")
                
                if run_obj.sensor_mapping is None:
                    print(f"    ⚠️  No sensor mapping, skipping")
                    skipped_runs_list.append((calib_set_number, run_name, "No sensor mapping"))
                    continue
                
                # Verificar canales defectuosos
                if hasattr(run_obj, 'defective_channels') and run_obj.defective_channels:
                    print(f"    ⚠️  Defective channels detected: {run_obj.defective_channels}, skipping")
                    skipped_runs_list.append((calib_set_number, run_name, f"Defective: {run_obj.defective_channels}"))
                    continue
                
                try:
                    # Calcular offsets y RMS
                    offsets_mat = run_obj.offsets(tini=tini, tend=tend)
                    rms_mat = run_obj.stat_err_offsets(tini=-20, tend=0)
                    
                    print(f"      🔍 DEBUG: offsets_mat shape = {offsets_mat.shape}")
                    print(f"      🔍 DEBUG: offsets_mat index = {list(offsets_mat.index)[:5]}...")
                    
                    # Extraer offsets y RMS para cada sensor vs su referencia
                    for ch in range(1, 15):
                        if sensor_names[ch] is None:
                            continue
                        
                        sensor_id = str(sensor_names[ch])  # Asegurar que es string
                        ref_ch = ref_channel_por_sensor.get(ch)
                        
                        if ref_ch is None:
                            continue
                        
                        # Saltar si el sensor es su propia referencia (offset = 0)
                        if ch == ref_ch:
                            print(f"      ⏭️  Skipping ch {ch} (self-reference)")
                            continue
                        
                        ref_sensor_id = str(sensor_names[ref_ch])  # Asegurar que es string
                        
                        # Obtener offset y RMS de la matriz
                        if sensor_id in offsets_mat.index and ref_sensor_id in offsets_mat.columns:
                            offset_val = offsets_mat.loc[sensor_id, ref_sensor_id]
                            rms_val = rms_mat.loc[sensor_id, ref_sensor_id]
                            
                            print(f"      📊 Ch {ch} ({sensor_id} - {ref_sensor_id}): offset={offset_val:.6f} K, rms={rms_val:.6f} K")
                            
                            if pd.notna(offset_val) and pd.notna(rms_val):
                                offsets_all_runs[ch].append(offset_val * 1000)  # Convertir a mK
                                rms_all_runs[ch].append(rms_val * 1000)  # Convertir a mK
                        else:
                            print(f"      ⚠️  Ch {ch}: sensor_id {sensor_id} or ref {ref_sensor_id} not found in matrix")
                    
                    print(f"    ✅ Offsets computed successfully")
                    
                except Exception as e:
                    print(f"    ⚠️  Error computing offsets: {e}")
                    skipped_runs_list.append((calib_set_number, run_name, str(e)[:50]))
                    continue
            
            # Debug: Mostrar cuántos offsets se recolectaron
            print(f"\n  📊 Offsets collected per channel:")
            total_with_data = 0
            for ch, offset_list in offsets_all_runs.items():
                if len(offset_list) > 0:
                    print(f"    Ch {ch} ({sensor_names[ch]}): {len(offset_list)} runs")
                    total_with_data += 1
                else:
                    print(f"    Ch {ch} ({sensor_names[ch]}): ⚠️  NO DATA")
            
            print(f"\n  📊 Total channels with data: {total_with_data}")
            
            if total_with_data == 0:
                print(f"  ⚠️⚠️  WARNING: NO DATA TO PLOT! Skipping plots for {calib_set_number}")
                plt.close(fig)
                continue
            
            # Calcular estadísticas globales y graficar
            global_means = {}
            global_sigmas = {}
            
            # Usar ch_idx solo para canales que tienen datos
            plot_idx = 0
            for ch, offset_list in offsets_all_runs.items():
                if len(offset_list) == 0:
                    print(f"  ⏭️  Skipping Ch {ch} (no data)")
                    continue
                
                if plot_idx >= 14:
                    print(f"  ⚠️  WARNING: More than 14 channels with data, skipping Ch {ch}")
                    continue
                
                ax = axes[plot_idx]
                sensor_id = sensor_names[ch]
                ref_ch = ref_channel_por_sensor[ch]
                ref_sensor_id = sensor_names[ref_ch]
                
                print(f"  📈 Plotting Ch {ch} ({sensor_id}) on subplot {plot_idx}")
                
                # Calcular estadísticas
                mean_offset = np.mean(offset_list)
                sigma_offset = np.std(offset_list, ddof=1) if len(offset_list) > 1 else 0
                
                global_means[sensor_id] = mean_offset
                global_sigmas[sensor_id] = sigma_offset
                
                # Graficar
                run_indices = list(range(1, len(offset_list) + 1))
                ax.errorbar(
                    run_indices,
                    offset_list,
                    yerr=rms_all_runs[ch],
                    fmt='o',
                    markersize=4,
                    capsize=3,
                    label=f'{sensor_id} - {ref_sensor_id}'
                )
                
                # Línea de media
                ax.axhline(mean_offset, color='red', linestyle='--', linewidth=1.5, label=f'Mean: {mean_offset:.2f} mK')
                
                # Banda de ±sigma
                ax.fill_between(
                    run_indices,
                    mean_offset - sigma_offset,
                    mean_offset + sigma_offset,
                    alpha=0.2,
                    color='red'
                )
                
                ax.set_title(f'Sensor {sensor_id} (Ch {ch})', fontsize=10, fontweight='bold')
                ax.set_xlabel('Run Number', fontsize=9)
                ax.set_ylabel('Offset (mK)', fontsize=9)
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=7, loc='best')
                
                # Añadir texto con estadísticas
                ax.text(
                    0.02, 0.98,
                    f'μ={mean_offset:.2f} mK\nσ={sigma_offset:.2f} mK',
                    transform=ax.transAxes,
                    fontsize=8,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
                )
                
                plot_idx += 1  # Incrementar índice para siguiente subplot
            
            # Guardar figura
            plot_path = os.path.join(save_dir, f"{calib_set_number}_offset_repeatability.png")
            plt.tight_layout()
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"\n💾 Plot saved: {plot_path}")
            
            # Guardar estadísticas globales
            self.global_stats[calib_set_number] = {
                'means': global_means,
                'sigmas': global_sigmas
            }
            
            # Guardar CSVs si está activado
            if write_csv:
                # CSV de means
                means_df = pd.DataFrame.from_dict(global_means, orient='index', columns=['Mean_Offset_mK'])
                means_path = os.path.join(save_dir, f"{calib_set_number}_global_means.csv")
                means_df.to_csv(means_path)
                print(f"💾 Means CSV saved: {means_path}")
                
                # CSV de sigmas
                sigmas_df = pd.DataFrame.from_dict(global_sigmas, orient='index', columns=['Sigma_mK'])
                sigmas_path = os.path.join(save_dir, f"{calib_set_number}_global_sigmas.csv")
                sigmas_df.to_csv(sigmas_path)
                print(f"💾 Sigmas CSV saved: {sigmas_path}")
        
        # Guardar runs excluidos
        if skipped_runs_list and write_csv:
            skipped_df = pd.DataFrame(skipped_runs_list, columns=['CalibSetNumber', 'Filename', 'Reason'])
            skipped_path = os.path.join(save_dir, "skipped_runs.csv")
            skipped_df.to_csv(skipped_path, index=False)
            print(f"\n💾 Skipped runs saved: {skipped_path}")
        
        print(f"\n{'='*60}")
        print(f"✅ Offset repeatability analysis complete")
        print(f"{'='*60}")
    
    def plot_global_means(self, selected_sets: list = None, save_dir: str = "plots_sts") -> None:
        """
        Grafica las medias globales de offsets para cada set.
        
        Args:
            selected_sets: Lista de CalibSetNumber a graficar
            save_dir: Directorio donde guardar el plot
        """
        if not self.global_stats:
            print("⚠️  No global stats available. Run offset_repeatability first.")
            return
        
        os.makedirs(save_dir, exist_ok=True)
        
        sets_to_plot = selected_sets if selected_sets else list(self.global_stats.keys())
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for calib_set in sets_to_plot:
            if calib_set not in self.global_stats:
                continue
            
            means = self.global_stats[calib_set]['means']
            sensors = list(means.keys())
            values = list(means.values())
            
            ax.plot(sensors, values, marker='o', label=f'{calib_set}', linewidth=2)
        
        ax.set_xlabel('Sensor ID', fontsize=12, fontweight='bold')
        ax.set_ylabel('Mean Offset (mK)', fontsize=12, fontweight='bold')
        ax.set_title('Global Mean Offsets by Set', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        
        plot_path = os.path.join(save_dir, "global_means_comparison.png")
        plt.tight_layout()
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"💾 Global means plot saved: {plot_path}")
    
    def plot_global_sigmas(self, selected_sets: list = None, save_dir: str = "plots_sts") -> None:
        """
        Grafica las sigmas globales (repetibilidad) para cada set.
        Excluye sensores de referencia (IDs > 1000).
        
        Args:
            selected_sets: Lista de CalibSetNumber a graficar
            save_dir: Directorio donde guardar el plot
        """
        if not self.global_stats:
            print("⚠️  No global stats available. Run offset_repeatability first.")
            return
        
        os.makedirs(save_dir, exist_ok=True)
        
        sets_to_plot = selected_sets if selected_sets else list(self.global_stats.keys())
        
        fig, ax = plt.subplots(figsize=(18, 6))
        
        for calib_set in sets_to_plot:
            if calib_set not in self.global_stats:
                continue
            
            sigmas = self.global_stats[calib_set]['sigmas']
            
            # Filtrar sensores de referencia (> 156)
            filtered_sigmas = {}
            for k, v in sigmas.items():
                try:
                    sensor_num = int(float(str(k)))
                    if 1 <= sensor_num <= 156:
                        filtered_sigmas[k] = v
                except (ValueError, TypeError):
                    # Si no se puede convertir a número, lo incluimos por seguridad
                    pass
            
            if not filtered_sigmas:
                print(f"⚠️  No sensors found for {calib_set} after filtering")
                continue
                
            sensors = list(filtered_sigmas.keys())
            values = list(filtered_sigmas.values())
            
            ax.scatter(sensors, values, marker='s', s=100, label=f'{calib_set}', 
                      alpha=0.7, edgecolors='black', linewidth=1)
        
        ax.set_xlabel('Sensor ID', fontsize=12, fontweight='bold')
        ax.set_ylabel('Repeatability σ (mK)', fontsize=12, fontweight='bold')
        ax.set_title('Frame RTD Sensors (Standard) - Calibration Repeatability Analysis\nOffset Standard Deviation by Calibration Set', 
                     fontsize=13, fontweight='bold', pad=15)
        ax.legend(fontsize=9, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right', fontsize=6)
        
        plot_path = os.path.join(save_dir, "global_sigmas_comparison.png")
        plt.tight_layout()
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"💾 Global sigmas plot saved: {plot_path}")
