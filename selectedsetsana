import pandas as pd
import os
import math
import matplotlib.pyplot as plt
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
        manteniendo el orden de los sensores basado en el run con más sensores.
        """
        try:
            offsets_list = []
            rms_list = []

            # Encuentra el run con más sensores
            max_sensors = 0
            reference_run = None

            for runs_in_set in self.runs_by_set.values():
                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        num_sensors = len(run_instance.sensor_mapping)
                        if num_sensors > max_sensors:
                            max_sensors = num_sensors
                            reference_run = run_instance
                    else:
                        print(f"Advertencia: sensor_mapping es None para el run {run_instance}. Se omite este run.")

            if not reference_run:
                raise RuntimeError("No se encontró un run válido para calcular los offsets.")

            # Usa el orden del run de referencia
            reference_sensors = list(reference_run.sensor_mapping.keys())
            print(f"Referencia basada en el run: {reference_run} con sensores: {reference_sensors}")

            # Itera sobre los runs y calcula offsets y RMS
            for calib_set_number, runs_in_set in self.runs_by_set.items():
                if selected_sets and calib_set_number not in selected_sets:
                    continue
                print(f"\nProcesando CalibSetNumber: {calib_set_number}")

                for filename, run_instance in runs_in_set.items():
                    print(f"  Procesando Run: {filename}")

                    if run_instance.sensor_mapping is not None:
                        # Calcular offsets y RMS
                        print(run_instance.sensor_mapping)
                        offsets = run_instance.offsets()
                        rms_offsets = run_instance.stat_err_offsets()

                        # **Agregar print para inspeccionar las matrices**
                        #print(f"Offsets matrix for run {filename}:\n{offsets}")
                        #print(f"RMS matrix for run {filename}:\n{rms_offsets}")

                        # Convertir matrices numpy a DataFrame para concatenación
                        offsets_df = pd.DataFrame(offsets, index=reference_sensors, columns=reference_sensors)
                        rms_df = pd.DataFrame(rms_offsets, index=reference_sensors, columns=reference_sensors)

                        offsets_list.append(offsets_df)
                        rms_list.append(rms_df)

                        print(f"Dimensiones de la matriz de offsets: {offsets_df.shape}")
                        print(f"Dimensiones de la matriz de RMS: {rms_df.shape}")
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

    def offset_repeatability(self, tini=20, tend=40, ref=2, save_dir="plots", selected_sets=None):
        """
        Calcula la repetibilidad de los offsets para cada CalibSetNumber.
        Genera y guarda una figura con 14 subplots donde se superponen todos los runs en cada subplot.
        Guarda las medias y sigmas globales en un diccionario dentro de la instancia (self.global_stats[calib_set_number][idx]["mean"]). 
        También los sensores que se utilizan en los sets. 
        """
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        self.global_stats = {}  # Diccionario para almacenar los resultados
         # Si se especifican conjuntos, filtrar los que se procesarán
        calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else set(selected_sets)

        for calib_set_number, runs in self.runs_by_set.items():
            if calib_set_number not in calib_sets_to_process:
                continue  # Saltar los sets no seleccionados
            print(f"\nProcesando CalibSetNumber: {calib_set_number}")
            filenames = list(runs.keys())  # Obtener los nombres de los archivos
            fig, axes = plt.subplots(3, 5, figsize=(21, 13))
            axes = axes.flatten()
            fig.subplots_adjust(top=0.80)  # Reduce la ocupación de los subplots y deja más espacio arriba
            # Ocultar los subplots vacíos si hay menos de 16 (en este caso, 14 usados)
            for ax in axes[14:]:  
                ax.set_visible(False)
                
            # Inicializar all_offsets como una lista de 14 listas vacías
            all_offsets = [[] for _ in range(14)]
            sensor_names = {}
            for run_index, filename in enumerate(filenames):
                run = runs[filename]
                if run.sensor_mapping is None:
                    print(f"Advertencia: 'sensor_mapping' es None para el run {filename}.")
                    continue
                for idx in range(14):
                    #if idx + 1 == ref:
                       # continue
                    if idx not in sensor_names:
                        try:
                            sensor_names[idx] = run.sensor_mapping[f"channel_{idx+1}"]
                            #print(sensor_names[idx])
                        except keyError:
                            sensor_names[idx] = "Unknown"
                            
            for idx in range(14): #las siguientes lineas se pueden comentar para no saltar el sensor de referencia 
                #if idx + 1 == ref:
                    #continue
                    #pass
                    
                sensor_id = sensor_names.get(idx, "Unknown")
                axes[idx].set_title(f"Offset Ch{ref}-Ch{idx+1} ({sensor_id})", fontsize=11, fontweight="bold")
                axes[idx].set_xlabel("Time (minutes)", fontsize=10, fontweight="bold")
                axes[idx].set_ylabel("Offset (mK)", fontsize=10, fontweight="bold")
                axes[idx].grid(which='both', linestyle='--', linewidth=0.5)

                # Inicializar una lista de etiquetas para la leyenda de este subplot
                for run_index, filename in enumerate(filenames):
                #lo que está comentado es para numerar los runs por la columna de N_Run y no en orden:
                #for filename in filenames:
                    # Obtener el número de run desde el LogFile
                    #n_run = self.logfile.loc[self.logfile["Filename"] == filename, "N_Run"].values
                    #if len(n_run) == 0:
                        #print(f"Advertencia: No se encontró 'N_Run' para {filename}.")
                        #continue
                    #run_label = f"Run {int(n_run[0])}"  # Etiqueta del run según 'N_Run'
                    run_label = f"Run {run_index + 1}"  # Etiqueta del run
                    
                    run = runs[filename]  # Instancia de la clase Run
                    temperature_data = run.temperature_data
                    # Comprobar que 'sensor_mapping' no es None
                    if run.sensor_mapping is None:
                        print(f"Advertencia: 'sensor_mapping' es None para el run {filename}.")
                        continue  # Saltar este run si 'sensor_mapping' es None
                    # Calcular el tiempo inicial y el intervalo relativo en minutos
                    time_start = temperature_data.index.min()
                    time_max = temperature_data.index.max()
                    
                    #time_20min = time_start 
                    #time_40min = time_max
                    ###desfijar y borrar lo anterior!
                    time_20min = time_start + pd.Timedelta(minutes=tini)
                    time_40min = time_start + pd.Timedelta(minutes=tend)
                    
                    filtered_data = temperature_data.loc[time_20min:time_40min]
                    time_relative = (filtered_data.index - time_20min).total_seconds() / 60  # Tiempo en minutos desde tini

                    try:
                        # Intentar acceder a los sensores y calcular el offset
                        ref_sensor = run.sensor_mapping[f"channel_{ref}"]
                        sensor_i = run.sensor_mapping[f"channel_{idx + 1}"]
                        offset = 1e3 * (filtered_data[ref_sensor] - filtered_data[sensor_i])
                    except KeyError:
                        # Si el sensor no se encuentra, asignar NaN
                        offset = pd.Series([float('nan')] * len(filtered_data), index=filtered_data.index)
                    
                    #offset_centered = offset - offset.mean()
                    offset_centered = offset 

                    # Almacenar los offsets para calcular la media y sigma global
                    all_offsets[idx].extend(offset_centered)

                    # Agregar línea al subplot con etiqueta del run
                    axes[idx].plot(
                        time_relative,
                        offset_centered,
                        label=run_label  # Etiqueta del run
                    )
                    
                # Filtrar valores NaN antes de calcular la media y sigma global
                valid_offsets = np.array(all_offsets[idx])
                valid_offsets = valid_offsets[~np.isnan(valid_offsets)]  # Filtrar valores NaN
                
                global_mean = np.mean(valid_offsets) if len(valid_offsets) > 0 else 0
                global_sigma = np.std(valid_offsets) if len(valid_offsets) > 0 else 0

                # Guardar en el diccionario
                if calib_set_number not in self.global_stats:
                    self.global_stats[calib_set_number] = {}
                    # Mostrar lo que se va a guardar
                #print(f"Guardando estadísticas para CalibSetNumber: {calib_set_number}, Sensor: {idx + 1}")
                #print(f"Mean: {global_mean}, Sigma: {global_sigma}")
                self.global_stats[calib_set_number][idx] = {"mean": global_mean, "sigma": global_sigma}

                # Calcular media y sigma global(lo comentamos porq probamos el calculo antes sin nan)
                #global_mean = np.mean(all_offsets[idx])
                #global_sigma = np.std(all_offsets[idx])

                # Mostrar media y sigma global en un cuadro de texto en el subplot
                stats_text = f"Mean: {global_mean:.4e} mK\nSigma: {global_sigma:.2f} mK"
                axes[idx].text(
                    0.95, 0.95,  # Coordenadas del cuadro (dentro del subplot, en porcentaje)
                    stats_text,
                    fontsize=9,
                    fontweight="bold",
                    ha="right",
                    va="top",
                    transform=axes[idx].transAxes,
                    bbox=dict(boxstyle="round", facecolor="white", edgecolor="black", alpha=0.8)  # Estilo del cuadro
                )

                # Mostrar leyenda solo con los números de los runs
                axes[idx].legend(
                    fontsize=8, loc="upper left", ncol=1
                )

            fig.suptitle(f"Offset Repeatability for CalibSetNumber {calib_set_number}: With respect to Channel {ref}", fontsize=20, fontweight="bold")
            fig.tight_layout()
            plot_filename = os.path.join(save_dir, f"offset_repeatability_set_{calib_set_number}.png")
            fig.savefig(plot_filename)
            print(f"Gráfico guardado en: {plot_filename}")
            plt.close(fig)  # Cerrar el gráfico para liberar memoria

        print("Datos globales guardados en self.global_stats")
        
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
            # Filtrar conjuntos de datos si se proporciona `selected_sets`
            calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else set(selected_sets)
            for calib_set_number, runs_in_set in self.runs_by_set.items():
                if calib_set_number not in calib_sets_to_process:
                    continue
                #print(f"Calculando constantes y errores para CalibSetNumber: {calib_set_number}")
                #if not runs:  # Si no hay runs válidos en este grupo, lo saltamos
                   # print(f"Skipping CalibSetNumber {calib_set_number} (no valid runs)")
                    #continue
                # Extraer las matrices de offsets y RMS para este set
                offsets_matrices = []
                rms_matrices = []

                for run_instance in runs_in_set.values():
                    offsets = run_instance.offsets()
                    rms_offsets = run_instance.stat_err_offsets()

                    offsets_matrices.append(offsets)
                    rms_matrices.append(rms_offsets)

                # Convertir las listas de matrices a arrays numpy para facilitar las operaciones
                offsets_array = np.array(offsets_matrices)  # Forma (num_runs, 14, 14)
                rms_array = np.array(rms_matrices)          # Forma (num_runs, 14, 14)

                # Crear una máscara booleana válida: excluye NaN y valores mayores a 1 en offsets
                valid_mask = ~np.isnan(offsets_array) & (offsets_array <= 1)

                # Crear una máscara para valores válidos en RMS (también excluye NaN)
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

                # Calcular el error asociado como la RMS de los offsets para cada posición (i, j)
                errors_matrix = np.sqrt(np.mean(offsets_array ** 2, axis=0))

                # Obtener los nombres de los sensores desde el primer run
                sensor_names = list(runs_in_set.values())[0].sensor_mapping.values()

                # Crear DataFrames para las matrices de constantes y errores
                constants_df = pd.DataFrame(constants_matrix, index=sensor_names, columns=sensor_names)
                errors_df = pd.DataFrame(errors_matrix, index=sensor_names, columns=sensor_names)

                # Imprimir matrices para depuración
                print(f"Matriz de constantes para CalibSetNumber {calib_set_number}:\n{constants_df}")
                print(f"Matriz de errores para CalibSetNumber {calib_set_number}:\n{errors_df}")

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
            return calibration_constants

        except Exception as e:
            raise RuntimeError(f"Error al calcular las constantes y los errores asociados: {e}")
            

    def plot_global_means(self, save_dir="pllots", selected_sets=None):
        """
        Genera gráficos de la media global de los offsets (global_mean)
        para cada sensor en todos los CalibSetNumber, dividiendo los plots en grupos de 8 sets.

        Parámetros:
            save_dir (str): Directorio donde se guardarán las imágenes de los gráficos.
        """
        if not hasattr(self, "global_stats"):
            print("Error: No se encontraron datos en self.global_stats. Primero ejecuta offset_repeatability().")
            return

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # 📢 Verificar qué sensores hay en cada CalibSet
        print("\n=== Verificación de sensores en self.global_stats ===")
        for calib_set_number in self.global_stats:
            sensors_detected = list(self.global_stats[calib_set_number].keys())
            print(f"CalibSet {calib_set_number}: {sensors_detected}")

        calib_sets = list(self.global_stats.keys())
        if selected_sets:
            calib_sets = [cs for cs in calib_sets if cs in selected_sets]
        num_sets = len(calib_sets)
        num_plots = (num_sets // 8) + (1 if num_sets % 8 != 0 else 0)

        for i in range(num_plots):
            plt.figure(figsize=(12, 6))

            subset = calib_sets[i * 8: (i + 1) * 8]
            all_means = []
            for calib_set_number in subset:
                sensors_data = self.global_stats[calib_set_number]
                sensor_indices = list(sensors_data.keys())
                #print(f"Sensores detectados en {calib_set_number}: {sensor_indices}")
                global_means = [sensors_data[idx]["mean"] for idx in sensor_indices]
                all_means.extend(global_means)

                # Obtener nombres de sensores desde cualquier Run dentro del conjunto
                example_run = next(iter(self.runs_by_set[calib_set_number].values()), None)
                if example_run and example_run.sensor_mapping:
                    sensor_names = [example_run.sensor_mapping.get(f"channel_{idx+1}", f"Sensor {idx+1}") for idx in sensor_indices]
                else:
                    sensor_names = [f"Sensor {idx+1}" for idx in sensor_indices]

                plt.scatter(sensor_names, global_means, marker='o')

            # Calcular media y desviación estándar de todos los valores en el gráfico
            overall_mean = np.mean(all_means)
            overall_std = np.std(all_means)
            legend_title = f"Mean: {overall_mean:.2f} mK\nStd: {overall_std:.2f} mK"

            plt.xlabel("Sensor ID", fontsize=14, fontweight='bold')
            plt.ylabel("Global Mean Offset (mK)", fontsize=14, fontweight='bold')
            plt.title(f"Offset Variability - Sets {subset[0]:.0f} to {subset[-1]:.0f}", fontsize=16, fontweight='bold')
            plt.xticks(rotation=45, ha="right", fontsize=6)
            plt.legend(title=legend_title, title_fontproperties={'weight': 'bold'}, loc='upper right')
            plt.grid(True, linestyle="--", alpha=0.5)

            plot_filename = os.path.join(save_dir, f"global_mean_offsets_part_{i+1}.png")
            plt.savefig(plot_filename)
            print(f"Gráfico guardado en: {plot_filename}")
            plt.show()



    def plot_global_sigmas(self, save_dir="plloots", selected_sets=None, max_sets_per_plot=7):
        """
        Genera gráficos de la sigma global de los offsets (global_sigma)
        para cada sensor en todos los CalibSetNumber, dividiendo los plots en grupos de 8 sets.

        Parámetros:
            save_dir (str): Directorio donde se guardarán las imágenes de los gráficos.
        """
        if not hasattr(self, "global_stats"):
            print("Error: No se encontraron datos en self.global_stats. Primero ejecuta offset_repeatability().")
            return

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        calib_sets = list(self.global_stats.keys())
        if selected_sets:
            calib_sets = [cs for cs in calib_sets if cs in selected_sets]
        num_sets = len(calib_sets)
        print(num_sets)
        
        #num_plots = (num_sets // 8) + (1 if num_sets % 8 != 0 else 0)
        #print(num_plots)
        
        # Calcular número de gráficos óptimos y dividir calib_sets equitativamente
        num_plots = math.ceil(num_sets / max_sets_per_plot)
        chunk_size = math.ceil(num_sets / num_plots)
        chunks = [calib_sets[i:i + chunk_size] for i in range(0, num_sets, chunk_size)]

        all_sigmas = []
        print(all_sigmas)
        
        #for i in range(num_plots):
        for i, subset in enumerate(chunks):
            plt.figure(figsize=(12, 6))

            #subset = calib_sets[i * 8: (i + 1) * 8]
            subset_sigmas = []
            print("sigmas del subset:", subset_sigmas)
            print(f"\nSubset {i+1}: {subset}")
            
            for calib_set_number in subset:
                print("set", calib_set_number)
                sensors_data = self.global_stats[calib_set_number]
                sensor_indices = list(sensors_data.keys())[:-2]  # Eliminar los dos últimos sensores (de referencia)
                global_sigmas = [sensors_data[idx]["sigma"] for idx in sensor_indices]  # Extraer global_sigma
                print(f"Sigmas agregados: {len(global_sigmas)}")
                print(global_sigmas)
                
                subset_sigmas.extend(global_sigmas)
                all_sigmas.extend(global_sigmas)

                # Obtener nombres de sensores desde cualquier Run dentro del conjunto
                example_run = next(iter(self.runs_by_set[calib_set_number].values()), None)
                if example_run and example_run.sensor_mapping:
                    sensor_names = [str(example_run.sensor_mapping.get(f"channel_{idx+1}", f"Sensor {idx+1}")) for idx in sensor_indices]
                else:
                    sensor_names = [str(f"Sensor {idx+1}") for idx in sensor_indices]  # Fallback si no hay mapeo

                plt.scatter(sensor_names, global_sigmas, marker='o')

            # Calcular media y desviación estándar de todos los valores en el gráfico
            overall_sigma_mean = np.mean(subset_sigmas)
            print(overall_sigma_mean)
            overall_sigma_std = np.std(subset_sigmas)
            legend_title = f"CalibSetNumber\nSigma Mean: {overall_sigma_mean:.2f} mK\nSigma Std: {overall_sigma_std:.2f} mK"

            plt.xlabel("Sensor ID", fontsize=14, fontweight='bold')
            plt.ylabel("Calibration Constant Systematic Errors (mK)", fontsize=12, fontweight='bold')
            plt.ylim(0, 5)
            plt.title(f"Sets {subset[0]:.0f} to {subset[-1]:.0f}", fontsize=18, fontweight='bold')
            plt.xticks(rotation=45, ha="right", fontsize=6)

            legend_title = f"Mean: {overall_sigma_mean:.2f} mK\nStd: {overall_sigma_std:.2f} mK"
            #legend_text = f"Sigma Mean: {overall_sigma_mean:.2f} mK\nSigma Std: {overall_sigma_std:.2f} mK"
            plt.legend(title=legend_title, title_fontproperties={'weight': 'bold'}, loc='upper left')
            #plt.gca().add_artist(plt.gcf().text(0.75, 0.8, legend_text, fontsize=10))
            plt.grid(True, linestyle="--", alpha=0.5)

            plot_filename = os.path.join(save_dir, f"global_sigma_offsets_part_{i+1}.png")
            plt.savefig(plot_filename)
            print(f"Gráfico guardado en: {plot_filename}")
            plt.show()
        
        print("Final all_sigmas:", all_sigmas)
        plt.figure(figsize=(8, 6))
        mu= np.mean(all_sigmas)
        sigma = np.std(all_sigmas)
        x = np.linspace(min(all_sigmas), max(all_sigmas), 100)
        plt.hist(all_sigmas, bins=12, density=False, alpha=0.6, color='b', label=f"Histogram\nμ={mu:.2f} mK"
)

        # Ajustar una distribución gaussiana
        gaussian_fit = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
        #plt.plot(x, gaussian_fit, 'r-', label=f"Gaussian Fit\nμ={mu:.2f}, σ={sigma:.2f}")

        plt.xlabel("Calibration Constant Systematic Errors (mK)", fontweight='bold')
        plt.ylabel("Frequency", fontweight='bold')
        plt.title(f"Errors Distribution: Sets {selected_sets[0]:.1f} to {selected_sets[-1]:.1f}", fontweight='bold')
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.5)
        hist_filename = os.path.join(save_dir, "global_sigma_histogram.png")
        plt.savefig(hist_filename)
        print(f"Histograma guardado en: {hist_filename}")
        plt.show()


