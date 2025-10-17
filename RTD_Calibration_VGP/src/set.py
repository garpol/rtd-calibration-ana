import pandas as pd
import os
import math
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap
from typing import Literal
import numpy as np
from run import Run

class Set:
    def __init__(self, logfile: pd.DataFrame) -> None:
        """
        Inicializa el conjunto de datos que agrupa varios 'Run' por el 'CalibSetNumber'.
        """
        self.logfile = logfile
        self.runs_by_set = {}  # Diccionario para almacenar instancias de la clase Run por CalibSetNumber
        self.offsets_data = None  # Matriz de offsets de todos los runs
        self.rms_offsets_data = None  # Matriz de errores RMS de todos los runs
        self.calibration_constants = None  # Constantes de calibración calculadas
        
        self.sensores_descartados = {
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
            60.0:[58384],
            
        }
        
        self.sensor_rojo_por_set = {
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
            59.0: [58400,58367],
            60.0: [58385,58381],
            #61.0: [,], acaban primeras rondas aquí, faltan por comprar 
            
            49.0: [48484, 48747], #ya son 2a ronda:
            50.0: [48869,48956],
            51.0: [49112, 49167],
            52.0: [49233, 55073],
            53.0: [55253,55227],
            54.0: [55233,55221],
            
            #55.0: [54869,54870, 54840, 54897, 54845, 55061], aqui ya subimos 6 por ser la segunda rama del tree, 
            #2a ronda también:
            #56.0: [,],
            
            #57.0: [,], 3a ronda - 1
            #62.0: [,], 3a ronda -2 
            
            #63.0: [,], 4a ronda
            
            #58.0: [,], referencias, va a parte
        }

    
    def group_runs_by_set(self, selected_sets=None) -> None:
        """
        Agrupa los runs por el 'CalibSetNumber' y crea instancias de la clase 'Run' para cada uno,
        excluyendo aquellos cuyo 'Filename' contenga la palabra 'pre'...
        """
        try:
            self.logfile["CalibSetNumber"] = pd.to_numeric(self.logfile["CalibSetNumber"], errors='coerce')
            calib_set_numbers = self.logfile["CalibSetNumber"].unique()
            calib_set_numbers = sorted([
                calib_set_number for calib_set_number in calib_set_numbers
                if isinstance(calib_set_number, (int, float)) and float(calib_set_number).is_integer()
                and calib_set_number > 0
                and len(str(int(calib_set_number))) <= 2  # Verifica que el número tenga dos o menos caracteres
            ])
            excluded_keywords = ['pre', 'st', 'lar']  # Palabras a excluir de los filenames
            # Agrupar los runs por CalibSetNumber
            for calib_set_number in calib_set_numbers:
                if selected_sets and calib_set_number not in selected_sets:
                    continue
                print(f"\nProcesando CalibSetNumber: {calib_set_number}")  # Imprime el CalibSetNumber actual
                # Filtramos el logfile para obtener todos los runs de este CalibSetNumber
                runs_in_set = self.logfile[self.logfile["CalibSetNumber"] == calib_set_number]
                valid_runs = {}
                #self.runs_by_set[calib_set_number] = {} ahora se inicializa después con los sets válidos

                # Iteramos por cada run en el set
                for _, run_row in runs_in_set.iterrows():
                    filename = run_row["Filename"]
                    selection = run_row["Selection"]

                    if isinstance(filename, str) and all(keyword not in filename.lower() for keyword in excluded_keywords):
                        if selection != "BAD":  # Verificar que el run no esté marcado como 'BAD'
                            run_instance = Run(filename, self.logfile)
                            #self.runs_by_set[calib_set_number][filename] = run_instance
                            valid_runs[filename] = run_instance
                            print(f"    Incluido: {filename}")
                        else:
                            print(f"    Excluido: {filename} (marcado como 'BAD' en Selection)")
                    else:
                        print(f"    Excluido: {filename} (contiene 'pre' o 'st')")
                        
                # Solo guardar el grupo si hay runs válidos
                if valid_runs:
                    self.runs_by_set[calib_set_number] = valid_runs
                        
        except KeyError as e:
            print(f"Error: {e}")
            raise
            
        except Exception as e:
            raise RuntimeError(f"Error al agrupar los runs: {e}")

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

            # Itera sobre los runs y calcula offsets y RMS
            for calib_set_number, runs_in_set in self.runs_by_set.items():
                if selected_sets and calib_set_number not in selected_sets:
                    continue
                print(f"\nProcesando CalibSetNumber: {calib_set_number}")

                # Encuentra el run con más sensores (referencia) dentro de este set
                max_sensors = 0
                reference_run = None
                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        num_sensors = len(run_instance.sensor_mapping)
                        if num_sensors > max_sensors:
                            max_sensors = num_sensors
                            reference_run = run_instance
                    else:
                        print(f"Advertencia: sensor_mapping es None para el run {run_instance.filename}. Se omite este run.")

                if not reference_run:
                    print(f"No se encontró un run válido para calcular los offsets en el set {calib_set_number}.")
                    continue

                print(f"El run de referencia tiene {max_sensors} sensores y es: {reference_run.filename}")
                print("Sensor mapping de referencia:")
                print(f"Sensor_mapping : {reference_run.sensor_mapping}")
                print(reference_run.sensor_mapping.keys())
                print(reference_run.sensor_mapping.items())
                print(reference_run.sensor_mapping.values())

                # Usa el orden del run de referencia
                reference_sensors = list(reference_run.sensor_mapping.values())
                print(f"Referencia basada en el run: {reference_run.filename} con sensores: {reference_sensors}")

                for filename, run_instance in runs_in_set.items():
                    print(f"  Procesando Run: {filename}")

                    if run_instance.sensor_mapping is not None:
                        current_sensors = list(run_instance.sensor_mapping.values())
                        print(f"Current sensors: {current_sensors}")

                        # Calcular offsets y RMS
                        offsets = run_instance.offsets()
                        rms_offsets = run_instance.stat_err_offsets()

                        # Crear DataFrames con el orden actual
                        offsets_df = pd.DataFrame(offsets, index=current_sensors, columns=current_sensors)
                        rms_df = pd.DataFrame(rms_offsets, index=current_sensors, columns=current_sensors)

                        print("  → Matriz de offsets ORIGINAL:")
                        print(offsets_df)

                        # Reordenar filas y columnas según el orden de referencia
                        offsets_df = offsets_df.reindex(index=reference_sensors, columns=reference_sensors)
                        rms_df = rms_df.reindex(index=reference_sensors, columns=reference_sensors)

                        print("  → Matriz de offsets REORDENADA:")
                        print(offsets_df)

                        offsets_list.append(offsets_df)
                        rms_list.append(rms_df)

                        print(f"  Dimensiones de la matriz de offsets: {offsets_df.shape}")
                        print(f"  Dimensiones de la matriz de RMS: {rms_df.shape}")
                    else:
                        print(f"Advertencia: No se puede calcular offsets ni RMS para el run {run_instance} porque sensor_mapping es None.")

            # Construye las matrices de offsets y RMS
            if offsets_list:
                keys = list(self.runs_by_set.keys())
                self.offsets_data = pd.concat(offsets_list, axis=1, keys=keys)
                self.rms_offsets_data = pd.concat(rms_list, axis=1, keys=keys)

            print("Cálculos de offsets y RMS completos.")

        except ValueError as e:
            print(f"Error: {e}")
            raise RuntimeError(f"Error al calcular los offsets y errores RMS: {e}")
        except Exception as e:
            print(f"Error inesperado: {e}")
            raise RuntimeError(f"Error al calcular los offsets y errores RMS: {e}")


    def offset_repeatability(self, tini=20, tend=40, save_dir="offset_repeatability_copy", selected_sets=None, ref=2):

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        self.global_stats = {}
        calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else set(selected_sets)

        for calib_set_number in calib_sets_to_process:
            runs = self.runs_by_set.get(calib_set_number)
            if runs is None:
                print(f"⚠️ Set {calib_set_number} no está en self.runs_by_set, se omite.")
                continue

            print(f"\nProcesando CalibSetNumber: {calib_set_number}")

            filenames = list(runs.keys())
            first_run = runs[filenames[0]]

            if first_run.sensor_mapping is None:
                print(f"⚠️ sensor_mapping es None para el primer run del set {calib_set_number}, se omite set.")
                continue

            mapping = first_run.sensor_mapping

            sensor_names = {}
            for ch in range(1, 15):
                sensor_names[ch] = mapping.get(f"channel_{ch}", None)

            # Determinar referencias dinámicas o fijas
            ref_channel_por_sensor = {}

            red_ids = self.sensor_rojo_por_set.get(calib_set_number, [])
            if red_ids and len(red_ids) >= 2:
                # Mapear IDs a canales
                red_channels = []
                for red_id in red_ids[:2]:  # solo usar los primeros dos
                    for ch, sid in sensor_names.items():
                        if str(sid).strip() == str(red_id).strip():
                            red_channels.append(ch)
                            break

                if len(red_channels) < 2:
                    print(f"⚠️ No se encontraron ambos sensores rojos en el mapping para set {calib_set_number}, usando referencia fija canal {ref}.")
                    red_channels = []
            else:
                red_channels = []

            if len(red_channels) == 2:
                print(f"✅ Set {calib_set_number}: Usando referencias dinámicas desde sensores rojos en canales {red_channels}")
                for ch in range(1, 15):
                    if sensor_names[ch] is None:
                        continue
                    if ch in red_channels:
                        # Si es uno de los sensores rojos, usar el otro como referencia
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
                # Sin sensores rojos: usar canal ref fijo
                print(f"ℹ️ Set {calib_set_number}: Usando canal fijo de referencia {ref} → Sensor ID {sensor_names.get(ref)}")
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

                # Evitar duplicados entre pares de sensores rojos
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
                        print(f"⚠️ sensor_mapping es None para run {filename} en set {calib_set_number}, se omite run.")
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
                    weights = 1 / run_stds[valid] ** 2
                    global_mean = np.average(run_means[valid], weights=weights)
                    global_sigma = np.std(run_means[valid], ddof=1)
                else:
                    global_mean = 0
                    global_sigma = 0

                if calib_set_number not in self.global_stats:
                    self.global_stats[calib_set_number] = {}
                self.global_stats[calib_set_number][idx] = {
                    "mean": global_mean,
                    "sigma": global_sigma,
                    "run_means": run_means.tolist(),
                    "run_stds": run_stds.tolist(),
                    "run_labels": run_labels
                }

                stats_text = f"$\\mu$ = {global_mean:.3f} mK\n$\\sigma$ = {global_sigma:.3f} mK"
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
            print(f"Gráfico guardado en: {plot_filename}")
            plt.close(fig)

        print("Datos globales guardados en self.global_stats")

        # Guardar CSV resumen
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
        csv_path = os.path.join(save_dir, "offset_repeatability_summary.csv")
        df_csv.to_csv(csv_path, index=False)
        print(f"CSV de resumen guardado en: {csv_path}")

        excel_path = os.path.join(save_dir, "offset_repeatability_summary.xlsx")
        df_csv.to_excel(excel_path, index=False)
        print(f"Excel guardado en: {excel_path}")


    def calculate_weighted_mean_offsets(self, selected_sets=None) -> dict:
        """
        Calcula una matriz de constantes de calibración y los errores asociados (RMS de offsets)
        para cada CalibSetNumber.

        Retorna:
            dict: Un diccionario donde las claves son los CalibSetNumber y los valores son
                  las matrices 14x14 de constantes de calibración con nombres de sensores.
        """
        try:
            calibration_constants = {}  # Diccionario para almacenar matrices de constantes de calibración
            calibration_errors = {}     # Diccionario para almacenar matrices de errores asociados
            
            # Filtrar conjuntos de datos si se proporciona `selected_sets`, donde seleccionamos 1 o varios del total de sets
            calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else set(selected_sets)

            for calib_set_number, runs_in_set in self.runs_by_set.items():
                if calib_set_number not in calib_sets_to_process:
                    continue
                print(f"\nProcesando CalibSetNumber: {calib_set_number}")

                # Encuentra el run con más sensores (referencia) que suele ser el primero para reordenar las matrices de ofsets si en algún run no se cumple el mismo mapping
                max_sensors = 0
                reference_run = None

                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        num_sensors = len(run_instance.sensor_mapping)
                        if num_sensors > max_sensors:
                            max_sensors = num_sensors
                            reference_run = run_instance
                    else:
                        print(f"Advertencia: sensor_mapping es None para el run {run_instance.filename}. Se omite este run.")

                if not reference_run:
                    raise RuntimeError(f"No se encontró un run válido para calcular los offsets para el CalibSetNumber {calib_set_number}.")

                print(f"  Run de referencia elegido: {reference_run.filename}")
                print(f"  Sensor mapping de referencia: {reference_run.sensor_mapping}")

                reference_sensors = list(reference_run.sensor_mapping.values())
                print(f"  Sensores de referencia: {reference_sensors}")

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

                        # Reordenar filas y columnas según el orden de referencia. DEMOS CALCULARLA SOLO PARA LOS ULTIMOS 20 MIN.
                        offsets_df = offsets_df.reindex(index=reference_sensors, columns=reference_sensors)
                        rms_df = rms_df.reindex(index=reference_sensors, columns=reference_sensors)

                        print(f"  → Matriz de offsets para {run_instance.filename}:")
                        print(offsets_df)
                        print(f"  → Matriz de errores (RMS) para {run_instance.filename}:")
                        print(rms_df)

                        offsets_matrices.append(offsets_df.values)
                        rms_matrices.append(rms_df.values)

                    else:
                        print(f"Advertencia: No se puede calcular offsets ni RMS para el run {run_instance.filename} porque sensor_mapping es None.")

                # Convertir las listas de matrices a arrays numpy para facilitar las operaciones
                offsets_array = np.array(offsets_matrices)  # Forma (num_runs, 14, 14)
                rms_array = np.array(rms_matrices)          # Forma (num_runs, 14, 14)

                # Crear una máscara booleana válida: excluye NaN y valores mayores a 1 en offsets
                valid_mask = ~np.isnan(offsets_array) & (offsets_array <= 1)

                # Crear una máscara para valores válidos en RMS (excluye NaN)
                valid_rms_mask = ~np.isnan(rms_array)

                # Máscara final combinada: valores válidos tanto en offsets como en RMS
                final_mask = valid_mask & valid_rms_mask

                # Calcular los pesos como el inverso del cuadrado de los RMS
                weights = np.zeros_like(rms_array)  # Inicializar matriz de pesos
                weights[final_mask] = 1 / (rms_array[final_mask] ** 2)  # Calcular pesos solo donde final_mask es True

                # Calcular el numerador y el denominador de la media ponderada
                weighted_sum = np.sum(offsets_array * weights, axis=0)  # Suma ponderada de offsets
                total_weights = np.sum(weights, axis=0)  # Suma de los pesos

                # Evitar división por cero en posiciones donde todos los pesos sean cero
                with np.errstate(divide='ignore', invalid='ignore'):
                    constants_matrix = np.divide(weighted_sum, total_weights)
                    constants_matrix[total_weights == 0] = np.nan  # Asignar NaN donde no hay datos válidos
                    
                print("\n=== CÁLCULO DE ERRORES ===")
                print(f"offsets_array shape: {offsets_array.shape}")
                print("Ejemplo de offsets_array[0]:")
                print(offsets_array[0])  # Primer run

                # Calcular el error asociado como la RMS de los offsets para cada posición (i, j). REVISAR. 
                #errors_matrix = np.sqrt(np.mean(offsets_array ** 2, axis=0))
                errors_matrix = np.std(offsets_array, axis=0, ddof=1)
                
                print("Matriz de errores RMS calculada (errors_matrix):")
                print(errors_matrix)

                # Obtener los nombres de los sensores desde el primer run
                sensor_names = list(runs_in_set.values())[0].sensor_mapping.values()
                

                # Crear DataFrames para las matrices de constantes y errores
                constants_df = pd.DataFrame(constants_matrix, index=sensor_names, columns=sensor_names)
                errors_df = pd.DataFrame(errors_matrix, index=sensor_names, columns=sensor_names)
                

                # Imprimir matrices para depuración
                print(f"Matriz de constantes para CalibSetNumber {calib_set_number}:")
                print(constants_df)
                print(f"Matriz de errores para CalibSetNumber {calib_set_number}:")
                print(errors_df)

                # Almacenar las matrices resultantes en los diccionarios
                calibration_constants[calib_set_number] = constants_df
                calibration_errors[calib_set_number] = errors_df

            # Guardar las matrices de calibración y errores en un archivo Excel
            with pd.ExcelWriter('calibration_constants_and_errors.xlsx') as writer:
                for calib_set_number in calibration_constants:
                    # Guardar matrices de constantes de calibración
                    constants_df = calibration_constants[calib_set_number]
                    constants_df.to_excel(writer, sheet_name=f'CalibSet_{calib_set_number}')

                    # Guardar matrices de errores asociados
                    errors_df = calibration_errors[calib_set_number]
                    errors_df.to_excel(writer, sheet_name=f'Errors_CalibSet_{calib_set_number}')

            print("Cálculo de constantes y errores completo y guardado en 'calibration_constants_and_errors.xlsx'.")
            return calibration_constants, calibration_errors #añado los errores

        except Exception as e:
            raise RuntimeError(f"Error al calcular las constantes y los errores asociados: {e}")
            

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
                red_sensors = self.sensor_rojo_por_set.get(calib_set_number, [])
                ref_pairs = [(r, o) for r in red_sensors if r in mapping_order for o in mapping_order if o != r]
            elif reference_selection == 'all_12':
                ref_pairs = [(mapping_order[i], mapping_order[j]) for i in range(len(mapping_order)) for j in range(len(mapping_order)) if i != j]
            elif reference_selection == 'all_12_excl_discards':
                sensores_excluidos = self.sensores_descartados.get(calib_set_number, [])
                filtered_mapping = [s for s in mapping_order if s not in sensores_excluidos]
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

        # --- Función auxiliar para formatear números ---
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

        
        ### **Gráfico 1: Dispersión**
       
        plt.figure(figsize=(7, 5))
        plt.scatter(all_distances, all_errors, color='teal', alpha=0.5, edgecolors='black')
        plt.title(f"{title_prefix} - Calibration Error vs Circular Distance", fontsize=13, fontweight='bold')
        plt.xlabel("Circular Distance", fontsize=11)
        plt.ylabel("Calibration Error (RMS, mK)" if convert_to_mK else "Calibration Error (RMS, K)", fontsize=11)
        plt.xticks(range(1, 7))

        # Lógica de límite Y para Gráfico 1: Dinámico si 'all_12_excl_discards', Fijo a 5 mK si no
        if reference_selection == 'all_12_excl_discards':
            if all_errors:
                max_error = np.max(all_errors)
                plt.ylim(0, max_error * 1.2 if max_error > 0 else (0.1 if convert_to_mK else 0.0001))
            else:
                plt.ylim(0, 1) # Valor por defecto si no hay errores
        else: # 'red_only' o 'all_12'
            plt.ylim(0, 5) # Límite fijo de 5 mK

        plt.grid(True, linestyle='--', alpha=0.6)

        if reference_selection == 'all_12_excl_discards':
            if processed_sets:
                plt.figtext(0.5, -0.08, f"Processed Sets: {', '.join(processed_sets)}", wrap=True, horizontalalignment='center', fontsize=9)

        plt.tight_layout()
        plt.show()

        
        ### **Gráfico 2: Media y Error**
        
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

        # Lógica de límite Y para Gráfico 2: Dinámico si 'all_12_excl_discards', Fijo a 5 mK si no
        if reference_selection == 'all_12_excl_discards':
            valid_ymax_vals = [m + s for m, s in zip(mean_errors, stderr_errors) if not (np.isnan(m) or np.isnan(s))]
            if valid_ymax_vals:
                ymax = max(valid_ymax_vals)
                plt.ylim(0, ymax * 1.2 if ymax > 0 else (0.1 if convert_to_mK else 0.0001))
            else:
                plt.ylim(0, 1) # Valor por defecto
        else: # 'red_only' o 'all_12'
            plt.ylim(0, 5) # Límite fijo de 5 mK

        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.show()

        
        ### **Gráfico 3: Histogramas**
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 8))
        axes = axes.flatten()

        # Lógica de límite X para Histogramas: Dinámico si 'all_12_excl_discards', Fijo a 5 mK si no
        if reference_selection == 'all_12_excl_discards':
            # Calcular el máximo error observado en all_errors para ajustar el xlim superior dinámicamente
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
        else: # 'red_only' o 'all_12'
            hist_xlim_upper = 5 # Límite fijo de 5 mK
            bin_edges_step = 0.5 # Paso fijo

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

        os.makedirs(save_dir, exist_ok=True)

        calib_sets = list(self.global_stats.keys())
        if selected_sets:
            calib_sets = [cs for cs in calib_sets if cs in selected_sets]

        num_sets = len(calib_sets)
        print(f"Procesando {num_sets} sets.")

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
                descartados = set(self.sensores_descartados.get(calib_set_number, []))

                sensor_keys = [k for k in sensors_data.keys() if isinstance(k, (int, float, str)) and str(k).isdigit()]
                use_ids = all(int(k) >= 48000 for k in sensor_keys)

                example_run = next(iter(self.runs_by_set[calib_set_number].values()), None)
                channel_to_id = {}
                if example_run and example_run.sensor_mapping:
                    channel_to_id = {int(k.replace("channel_", "")) - 1: int(v) for k, v in example_run.sensor_mapping.items()}
                    for ch in [12, 13]:
                        sensor_id_ult = channel_to_id.get(ch)
                        if sensor_id_ult is not None:
                            descartados.add(sensor_id_ult)

                sensor_ids = []
                if use_ids:
                    sensor_ids = [str(k) for k in sensor_keys if int(k) not in descartados]
                else:
                    for k in sensor_keys:
                        ch_index = int(k)
                        sensor_id = channel_to_id.get(ch_index, ch_index)
                        if sensor_id not in descartados:
                            sensor_ids.append(str(k))

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
                    if mean_val is not None:
                        global_means.append(mean_val)

                subset_means.extend(global_means)
                all_means.extend(global_means)

                sensor_names = []
                if example_run and example_run.sensor_mapping:
                    for sid in sensor_ids:
                        try:
                            ch_index = int(sid)
                            sensor_name = str(example_run.sensor_mapping.get(f"channel_{ch_index+1}", f"Sensor {ch_index+1}"))
                        except Exception:
                            sensor_name = f"Sensor {sid}"
                        sensor_names.append(sensor_name)
                else:
                    sensor_names = [f"Sensor {sid}" for sid in sensor_ids]

                # Scatter con color por set y etiqueta
                plt.scatter(sensor_names, global_means, marker='o', color=color, label=f"Set {calib_set_number}")

            overall_mean = np.mean(subset_means) if subset_means else 0
            overall_std = np.std(subset_means) if subset_means else 0
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
            print(f"Gráfico guardado en: {plot_filename}")
            plt.show()


    def plot_global_sigmas(self, save_dir="plot_global_sigmas", selected_sets=None, max_sets_per_plot=7):
        if not hasattr(self, "global_stats"):
            print("Error: No se encontraron datos en self.global_stats. Primero ejecuta offset_repeatability().")
            return

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        calib_sets = list(self.global_stats.keys())
        if selected_sets:
            calib_sets = [cs for cs in calib_sets if cs in selected_sets]

        num_sets = len(calib_sets)
        print(f"Procesando {num_sets} sets.")

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
                descartados = set(self.sensores_descartados.get(float(calib_set_number), []))

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
                        if sigma is not None:
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

                global_sigmas = []
                for sid in sensor_ids:
                    key = sid
                    if sid in sensors_data:
                        key = sid
                    elif sid.isdigit() and int(sid) in sensors_data:
                        key = int(sid)
                    else:
                        continue

                    sigma = sensors_data[key].get("sigma")
                    if sigma is not None:
                        global_sigmas.append(sigma)

                subset_sigmas.extend(global_sigmas)
                all_sigmas.extend(global_sigmas)

                if example_run and example_run.sensor_mapping:
                    sensor_names = []
                    for sid in sensor_ids:
                        try:
                            ch_index = int(sid)
                            sensor_name = str(example_run.sensor_mapping.get(f"channel_{ch_index+1}", f"Sensor {ch_index+1}"))
                        except Exception:
                            sensor_name = f"Sensor {sid}"
                        sensor_names.append(sensor_name)
                else:
                    sensor_names = [f"Sensor {sid}" for sid in sensor_ids]

                plt.scatter(sensor_names, global_sigmas, marker='o')

            overall_sigma_mean = np.mean(subset_sigmas) if subset_sigmas else 0
            overall_sigma_std = np.std(subset_sigmas) if subset_sigmas else 0
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
        # HISTOGRAMAS POR RONDAS (dinámico hasta 4 rondas)
        # =========================
        def collect_sigmas(sets, include_descartados=False):
            """Recolecta sigmas para un conjunto de sets."""
            sigmas_list = []
            for s in sets:
                sensors_data = self.global_stats[s]
                example_run = next(iter(self.runs_by_set[s].values()), None)
                channel_to_id = {}
                if example_run and example_run.sensor_mapping:
                    channel_to_id = {int(k.replace("channel_", "")) - 1: int(v) for k, v in example_run.sensor_mapping.items()}
                ultimos_canales = [channel_to_id.get(12), channel_to_id.get(13)]

                descartados = set(self.sensores_descartados.get(float(s), [])) if not include_descartados else set()
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
                    if sigma is not None:
                        sigmas_list.append(sigma)
            return sigmas_list

        def plot_hist_rounds(include_descartados=False, filename_prefix="global_sigma_histogram_rounds"):
            # Definir rondas
            round1_sets = [s for s in calib_sets if 3 <= int(s) <= 48] + [s for s in calib_sets if int(s) in [59, 60, 61]]
            round2_sets = [s for s in calib_sets if 49 <= int(s) <= 55]
            round3_sets = [s for s in calib_sets if int(s) in [57, 62]]
            round4_sets = [s for s in calib_sets if int(s) == 63]

            rounds = {
                "Round 1 (Sets 3-48,59-61)": round1_sets,
                "Round 2 (Sets 49-55)": round2_sets,
                "Round 3 (Sets 57,62)": round3_sets,
                "Round 4 (Set 63)": round4_sets
            }
            rounds = {k: v for k, v in rounds.items() if len(v) > 0}

            # Recoger sigmas
            rounds_sigmas = {label: collect_sigmas(sets, include_descartados) for label, sets in rounds.items()}
            combined_sigmas = [x for vals in rounds_sigmas.values() for x in vals]
            if not combined_sigmas:
                return

            mu_total, sigma_total = np.mean(combined_sigmas), np.std(combined_sigmas)
            bins = np.histogram_bin_edges(combined_sigmas, bins=12)
            ymax = max([max(np.histogram(v, bins=bins, density=True)[0]) if v else 0 for v in rounds_sigmas.values()]) * 1.1

            # Subplots separados
            n_rounds = len(rounds_sigmas)
            ncols = 2 if n_rounds > 1 else 1
            nrows = math.ceil(n_rounds / ncols)
            fig, axes = plt.subplots(nrows, ncols, figsize=(7*ncols, 6*nrows), sharey=True)
            axes = np.array(axes).reshape(-1)

            fig.suptitle("Errors Distribution by Round" + (" (Including discarded sensors)" if include_descartados else ""),
                         fontsize=16, fontweight='bold')

            for ax, (label, sigmas) in zip(axes, rounds_sigmas.items()):
                mu, sigma = np.mean(sigmas), np.std(sigmas)
                ax.hist(sigmas, bins=bins, alpha=0.7, density=True)
                ax.set_title(label, fontweight='bold')
                ax.set_xlabel("Calibration Constant Reproducibility (mK)", fontweight='bold')
                ax.set_ylabel("Density", fontweight='bold')
                ax.text(0.95, 0.95, f"μ = {mu:.2f} mK\nσ = {sigma:.2f} mK",
                        ha='right', va='top', transform=ax.transAxes, fontsize=10,
                        bbox=dict(facecolor='white', alpha=0.8))
                ax.set_ylim(0, ymax)
                ax.grid(True, linestyle="--", alpha=0.5)

            plt.tight_layout()
            plt.savefig(os.path.join(save_dir, f"{filename_prefix}_subplots.png"))
            plt.show()

            # Solapado
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            colors = ["blue", "orange", "green", "red"]
            for (label, sigmas), c in zip(rounds_sigmas.items(), colors):
                mu, sigma = np.mean(sigmas), np.std(sigmas)
                ax2.hist(sigmas, bins=bins, alpha=0.5, color=c, density=True,
                         label=f"{label}\nμ={mu:.2f} mK\nσ={sigma:.2f} mK")
            ax2.set_xlabel("Calibration Constant Reproducibility (mK)", fontweight='bold')
            ax2.set_ylabel("Density", fontweight='bold')
            ax2.set_ylim(0, ymax)
            ax2.set_title("Errors Distribution by Round (Overlapped)" + (" (Including discarded)" if include_descartados else ""),
                          fontweight='bold')
            ax2.grid(True, linestyle="--", alpha=0.5)
            ax2.legend()
            ax2.text(0.95, 0.50,
                     f"Total μ={mu_total:.2f} mK\nTotal σ={sigma_total:.2f} mK",
                     ha='right', va='top', transform=ax2.transAxes,
                     fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
            plt.savefig(os.path.join(save_dir, f"{filename_prefix}_overlap.png"))
            plt.show()

        # Ejecutar para sensores válidos y para descartados
        plot_hist_rounds(include_descartados=False, filename_prefix="global_sigma_histogram_rounds")
        plot_hist_rounds(include_descartados=True, filename_prefix="global_sigma_histogram_rounds_all_sensors")
