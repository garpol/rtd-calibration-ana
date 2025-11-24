import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import os
import numpy as np
import glob
from datetime import datetime
from pathlib import Path

class Run:
    def __init__(self, filename: str, logfile: pd.DataFrame, tmin: int = None, tmax: int = None, show_references: bool = True) -> None:
        """
        Clase que asocia los canales de temperatura de un archivo con los IDs de sensores del logfile.
        
        Args:
            filename: Nombre del archivo de temperatura
            logfile: DataFrame con el LogFile completo
            tmin: Tiempo inicial en minutos desde el inicio del run (None = últimos 20 min)
            tmax: Tiempo final en minutos desde el inicio del run (None = hasta el final)
            show_references: Si True muestra los 14 canales, si False solo los 12 primeros (corona, sin referencias)
        """
        self.filename = filename
        self.logfile = logfile
        self.temperature_data = None
        self.sensor_mapping = None
        self.path_to_file = None
        self.tmin = tmin  # Tiempo en minutos
        self.tmax = tmax  # Tiempo en minutos
        self.show_references = show_references  # Controla si se muestran canales 13 y 14 (referencias)

        # Filtrar el archivo y los datos
        self.load_temperature_file()
        self.filter_faulty_channels()  # detectar canales defectuosos
        self.associate_sensors()
        self.read_run_info()

    def load_temperature_file(self) -> None:
        """
        Busca y carga el archivo de datos de temperatura desde data/temperature_files/. Reemplaza con NaN los datos inválidos.
        """
        try:
            # Determine repository root and local data path
            repo_root = Path(__file__).parents[1].resolve()
            local_base = repo_root / "data" / "temperature_files"

            # Buscar el archivo .txt que coincida con el filename
            text_file = glob.glob(os.path.join(str(local_base), "**", self.filename + ".txt"), recursive=True)

            if not text_file:
                raise FileNotFoundError(
                    f"No se encontró el archivo '{self.filename}.txt' en {local_base}.\n"
                    f"Asegúrate de colocar los archivos de datos en RTD_Calibration_VGP/data/temperature_files/"
                )

            self.path_to_file = text_file[0]
            print(f"Archivo de temperatura encontrado: {self.path_to_file}")

            # Leer el archivo, sin encabezados
            self.temperature_data = pd.read_csv(self.path_to_file, sep='\t', header=None)

            # Asignar nombres de columnas: Día, Hora y 14 canales
            column_names = ["Date", "Time"] + [f"channel_{i}" for i in range(1, 15)]
            self.temperature_data.columns = column_names

            # Intentar con formato con AM/PM
            self.temperature_data['datetime'] = pd.to_datetime(
                self.temperature_data['Date'] + ' ' + self.temperature_data['Time'],
                errors='coerce',
                format='%m/%d/%Y %I:%M:%S %p'
            )

            # Reintentar con formato de 24 horas si fallan algunos valores
            if self.temperature_data['datetime'].isna().any():
                self.temperature_data['datetime'] = pd.to_datetime(
                    self.temperature_data['Date'] + ' ' + self.temperature_data['Time'],
                    errors='coerce',
                    format='%m/%d/%Y %H:%M:%S'
                )

            # Reintentar con dayfirst=True si persisten errores
            if self.temperature_data['datetime'].isna().any():
                self.temperature_data['datetime'] = pd.to_datetime(
                    self.temperature_data['Date'] + ' ' + self.temperature_data['Time'],
                    errors='coerce',
                    dayfirst=True
                )

            # Si aún hay fechas inválidas, lanzar error
            if self.temperature_data['datetime'].isna().any():
                raise ValueError(f"No se pudo procesar correctamente las fechas y horas en el archivo {self.path_to_file}.")

            # Eliminar las columnas originales de fecha y hora
            del self.temperature_data["Date"]
            del self.temperature_data["Time"]

            # Separar la columna 'datetime' y las columnas de temperatura
            datetime_col = self.temperature_data.pop('datetime')
            temperature_cols = self.temperature_data

            # Filtrar los datos de temperatura según el rango deseado (60 K a 350 K). Asigna NaN a los valores fuera del rango.
            valid_range_mask = (temperature_cols >= 60) & (temperature_cols <= 350)
            temperature_cols = temperature_cols.where(valid_range_mask)
            
             # Eliminar filas donde todos los valores sean NaN en las columnas de temperatura
            temperature_cols = temperature_cols.dropna(how='all')
            
            # Contar los valores NaN después de eliminar las filas
            nan_count_after_dropping = temperature_cols.isna().sum().sum()  # Recontar los NaN después de la limpieza
            print(f"Valores NaN (contador): {nan_count_after_dropping}")
            
             # Reemplazar columnas con más de 20 valores NaN con NaN al completo porque no nos fiamos de las medidas de este sensor
            max_nan_threshold = 40 #definimos este valor pero podemos modificarlo 
            nan_count = temperature_cols.isna().sum()
            columns_to_replace = nan_count > max_nan_threshold
            
            # Mostrar las columnas con datos defectuosos
            if columns_to_replace.any():
                defective_columns = temperature_cols.columns[columns_to_replace].tolist()
                print(f"Se han encontrado datos defectuosos en las siguientes columnas (todo valores NaN): {defective_columns}")
                
            # Identificar columnas que tienen al menos un NaN pero menos de 20
            partially_defective_columns_mask = (nan_count > 0) & (nan_count <= max_nan_threshold)
            partially_defective_columns = temperature_cols.columns[partially_defective_columns_mask].tolist()

            # Mostrar las columnas que cumplen esta condición
            if partially_defective_columns:
                print(f"Las siguientes columnas tienen algunos valores NaN pero están por debajo del límite de {max_nan_threshold}:{partially_defective_columns}")
                
            # Capturar los NaN en un DataFrame separado para mostrarlos con su tiempo 
            nan_locations = temperature_cols[temperature_cols.isna().any(axis=1)].copy()
            nan_locations['datetime'] = datetime_col.loc[nan_locations.index]
            #print(nan_locations)
            nan_df = nan_locations.melt(id_vars='datetime', var_name='channel', value_name='value')
            
            # Mantener solo las filas donde "value" es NaN para no mostrar todo el df
            nan_df = nan_df[nan_df['value'].isna()]
            self.nan_data = nan_df  # Guardar como atributo para análisis posterior
            print(nan_df)
    
            temperature_cols.loc[:, columns_to_replace] = np.nan #reemplazamos con nan la columna que supera el límite de 20 

            # Reincorporar la columna 'datetime' como índice
            self.temperature_data = temperature_cols
            self.temperature_data['datetime'] = datetime_col.loc[temperature_cols.index]
            self.temperature_data = self.temperature_data.set_index('datetime')


            print(f"Archivo de temperatura procesado correctamente: {self.path_to_file}")
            return self

        except Exception as e:
            print(f"Error al cargar el archivo de temperatura: {e}")
            self.temperature_data = pd.DataFrame()  # Vacía si ocurre un error

    def associate_sensors(self) -> None:
        """
        Asocia cada canal del archivo de temperatura con los IDs de sensores RTD del Logfile.
        """
        try:
            if self.temperature_data.empty:
                raise ValueError("No se han cargado datos de temperatura.")

            # Filtrar el logfile para obtener la fila del filename en cuestión
            matching_row = self.logfile[self.logfile["Filename"] == self.filename]

            if matching_row.empty:
                raise ValueError(f"No se encontró el filename '{self.filename}' en el logfile.")

            # Extraer los IDs de sensores de las columnas S7 a S20 (ignorando huecos vacíos con .dropna().values
            sensor_columns = [f"S{i}" for i in range(1, 21)]
            #print(f"Columnas de sensores a procesar: {sensor_columns}")
            
            #print(f"Fila de datos antes de extraer los IDs:\n{matching_row[sensor_columns]}")
            sensor_ids = matching_row.loc[:, sensor_columns].iloc[0].dropna().values
            print(f"Valores de sensores extraídos (antes de filtrado y conversión): {sensor_ids}")

            # Convertir los IDs a string (añadimos el if)
            #sensor_ids = [str(int(sensor_id)) for sensor_id in sensor_ids if str(sensor_id).isdigit()]
            #print(f"IDs de sensores después de la conversión: {sensor_ids}")
            
            # Convertir los IDs a string
            # Maneja tanto IDs numéricos (RTD) como alfanuméricos (resistencias PDHD-HP-X)
            converted_ids = []
            for sensor_id in sensor_ids:
                if isinstance(sensor_id, (int, float)):
                    # IDs numéricos: convertir a entero si es posible
                    try:
                        converted_ids.append(str(int(sensor_id)))
                    except (ValueError, OverflowError):
                        converted_ids.append(str(sensor_id))
                else:
                    # IDs alfanuméricos (resistencias): mantener como string
                    converted_ids.append(str(sensor_id))
            sensor_ids = converted_ids
            print(f"IDs de sensores después de la conversión: {sensor_ids}")

            # Asociar IDs con canales
            channels = [f"channel_{i}" for i in range(1, 15)]
            self.sensor_mapping = dict(zip(channels, sensor_ids))

            print("Asociación de canales con IDs de sensores:")
            for channel, sensor_id in self.sensor_mapping.items():
                print(f"{channel}: Sensor ID {sensor_id}")

            # Renombrar las columnas del archivo de temperatura con los IDs de sensores
            self.temperature_data = self.temperature_data.rename(columns=self.sensor_mapping)
        except Exception as e:
            print(f"Error al asociar sensores con canales: {e}")
                
    def filter_faulty_channels(self, min_temp: float = 70, max_temp: float = 320) -> None:
        """
        Detecta los canales con lecturas fuera del rango permitido, lecturas constantes,
        o valores faltantes, e indica la razón específica por la que se consideran defectuosos.
        """
        try:
            if self.temperature_data.empty:
                raise ValueError("No se han cargado datos de temperatura para filtrar.")

            faulty_channels = {}

            for channel in self.temperature_data.columns:
                reasons = []

                # Verificar si todas las lecturas están fuera del rango aceptable
                if self.temperature_data[channel].min() < min_temp:
                    reasons.append(f"contiene un mínimo por debajo de {min_temp} K")
                if self.temperature_data[channel].max() > max_temp:
                    reasons.append(f"contiene un máximo por encima de {max_temp} K")

                # Verificar si el canal tiene valores constantes
                if self.temperature_data[channel].nunique() == 1:
                    reasons.append("lee valores constantes")

                # Verificar si el canal tiene valores faltantes (NaN)
                if self.temperature_data[channel].isna().any():
                    reasons.append(" contiene valores faltantes (NaN)")

                if reasons:
                    faulty_channels[channel] = reasons

            # Imprimir los canales defectuosos y sus razones
            if faulty_channels:
                print("Canales defectuosos detectados:")
                for channel, reason_list in faulty_channels.items():
                    print(f"  - {channel}: {', '.join(reason_list)}")
            else:
                print("No se detectaron canales defectuosos.")

        except Exception as e:
            print(f"Error al detectar canales defectuosos: {e}")

    def read_run_info(self) -> None:
        """
        Lee y almacena la información del run (CalibSetNumber, Date, N_Run) para el archivo dado.
        """
        try:
            # Filtrar el logfile para obtener la fila del filename en cuestión
            matching_row = self.logfile[self.logfile["Filename"] == self.filename]

            if matching_row.empty:
                raise ValueError(f"No se encontró el filename '{self.filename}' en el logfile.")

            # Extraer las columnas relevantes
            calib_set_number = matching_row["CalibSetNumber"].iloc[0]
            date = matching_row["Date"].iloc[0]
            n_run = matching_row["N_Run"].iloc[0]

          # Extraer los sensores de las columnas S7, S18, S19, y S20
            first_sensor_id = matching_row["S7"].iloc[0]
            last_sensor_id = matching_row["S18"].iloc[0]
            ref_sensor_1 = matching_row["S19"].iloc[0]
            ref_sensor_2 = matching_row["S20"].iloc[0]
            
            # Convertir los valores de los sensores manejando tanto IDs numéricos como alfanuméricos
            def convert_sensor_id(sensor_id):
                """Convierte sensor ID a formato apropiado (int para RTD, str para resistencias)"""
                if pd.isna(sensor_id):
                    return None
                if isinstance(sensor_id, (int, float)):
                    try:
                        return int(sensor_id)
                    except (ValueError, OverflowError):
                        return str(sensor_id)
                else:
                    # ID alfanumérico (resistencias)
                    return str(sensor_id)
            
            first_sensor_id = convert_sensor_id(first_sensor_id)
            last_sensor_id = convert_sensor_id(last_sensor_id)
            ref_sensor_1 = convert_sensor_id(ref_sensor_1)
            ref_sensor_2 = convert_sensor_id(ref_sensor_2)

            # Almacenar la información del run en el atributo `run_info`
            self.run_info = {
                "CalibSetNumber": calib_set_number,
                "Date": date,
                "N_Run": n_run,
                "First_Sensor_ID": first_sensor_id,
                "Last_Sensor_ID": last_sensor_id,
                "Ref_Sensor_1": ref_sensor_1,
                "Ref_Sensor_2": ref_sensor_2
            }

            # Imprimir la fecha del run y los sensores
            print(f"Fecha del Run: {date}")
            print(f"Primer Sensor: {first_sensor_id}")
            print(f"Último Sensor: {last_sensor_id}")
            print(f"Sensor de Referencia 1: {ref_sensor_1}")
            print(f"Sensor de Referencia 2: {ref_sensor_2}")

            print(f"Información del run cargada: {self.run_info}")


        except Exception as e:
            print(f"Error al leer la información del run: {e}")
            self.run_info = None


    def format_datetime_axis(self, ax) -> None:
        """
        Formatea el eje X para mostrar el día como número y hora:minuto cada 10 minutos.
        """
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %H:%M'))  # Formato de día y hora:minuto
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))  # Marca cada 10 minutos
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")  # Rotar etiquetas para legibilidad

    def _calculate_time_window(self):
        """
        Calcula los tiempos inicial y final para el análisis.
        Si tmin/tmax no están especificados, usa los últimos 20 minutos del run.
        
        Returns:
            tuple: (time_start, time_20min, time_40min) como timestamps
        """
        time_start = self.temperature_data.index.min()
        time_max = self.temperature_data.index.max()
        
        # Si no se especificaron tiempos, usar los últimos 20 minutos
        if self.tmin is None and self.tmax is None:
            # Últimos 20 minutos del run
            time_40min = time_max
            time_20min = time_max - pd.Timedelta(minutes=20)
        else:
            # Usar los tiempos especificados (en minutos desde el inicio)
            if self.tmin is not None:
                time_20min = time_start + pd.Timedelta(minutes=self.tmin)
            else:
                time_20min = time_start + pd.Timedelta(minutes=20)  # Default 20 min
            
            if self.tmax is not None:
                time_40min = time_start + pd.Timedelta(minutes=self.tmax)
            else:
                time_40min = time_max  # Hasta el final
        
        return time_start, time_20min, time_40min

    def create_temperature_plot(self, output_dir: str = "./Plots/") -> None:
        """
        Crea y guarda el gráfico de temperaturas de los sensores vs tiempo.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Calcular ventana de tiempo usando el método helper
        time_start, time_20min, time_40min = self._calculate_time_window()
        
         # Información adicional de los sensores y del run
        first_sensor = self.run_info.get("First_Sensor_ID", "Desconocido")
        last_sensor = self.run_info.get("Last_Sensor_ID", "Desconocido")
        ref_sensor_1 = self.run_info.get("Ref_Sensor_1", "Desconocido")
        ref_sensor_2 = self.run_info.get("Ref_Sensor_2", "Desconocido")
        calib_set_number = self.run_info.get("CalibSetNumber", "Desconocido")
        date = self.run_info.get("Date", "Desconocido")
        n_run = self.run_info.get("N_Run", "Desconocido")

        plt.figure(figsize=(10, 5))  # Ajustar el tamaño de la figura a más pequeño y cuadrado

        # Filtrar sensores según show_references
        sensors_to_plot = list(self.sensor_mapping.values())
        if not self.show_references and len(sensors_to_plot) > 12:
            sensors_to_plot = sensors_to_plot[:12]  # Solo los primeros 12 (corona)

        for sensor in sensors_to_plot:
            if sensor in self.temperature_data.columns:
                plt.plot(self.temperature_data.index, self.temperature_data[sensor], label=f"Sensor {sensor}")


        #plt.title(f"RTD Temperature Readings {self.filename}", fontsize=16, fontweight="bold")
        # Título del gráfico con la información de los sensores y el run
        plt.title(f"RTD Temperature Readings\n"
                  f"Run Number: {n_run} | Date: {date}\n"
                  f"CalibSet: {calib_set_number}\n"
                  f"Ref Sensors: {ref_sensor_1}, {ref_sensor_2}", fontsize=14, fontweight="bold")
        plt.xlabel("Time", fontsize=12, fontweight="bold")
        plt.ylabel("Temperature (K)", fontsize=12, fontweight="bold")
        #plt.ylim(76, 78)
        plt.axvline(time_20min, color='red', linestyle='--', linewidth=2, label="20 minutes")
        plt.axvline(time_40min, color='blue', linestyle='--', linewidth=2, label="40 minutes")
        plt.legend(fontsize=10, loc="upper left", ncol=2)
        plt.grid(which='both', linestyle='--', linewidth=0.5)  # Cuadrícula más densa
        self.format_datetime_axis(plt.gca())  # Formatear eje de fecha y hora
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{self.filename}_temperatures_vs_time.png"))
        plt.show()
        plt.close()

    def create_offset_plot(self, output_dir: str = "./Plots/") -> None:
        """
        Crea y guarda el gráfico de offsets centrados entre sensores, limitado al intervalo configurado.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Calcular ventana de tiempo usando el método helper
        time_start, time_20min, time_40min = self._calculate_time_window()

        # Filtrar datos para el intervalo configurado
        filtered_data = self.temperature_data.loc[time_20min:time_40min]
        
         # Información adicional de los sensores y del run
        first_sensor = self.run_info.get("First_Sensor_ID", "Desconocido")
        last_sensor = self.run_info.get("Last_Sensor_ID", "Desconocido")
        ref_sensor_1 = self.run_info.get("Ref_Sensor_1", "Desconocido")
        ref_sensor_2 = self.run_info.get("Ref_Sensor_2", "Desconocido")
        calib_set_number = self.run_info.get("CalibSetNumber", "Desconocido")
        date = self.run_info.get("Date", "Desconocido")
        n_run = self.run_info.get("N_Run", "Desconocido")

        # Filtrar sensores según show_references
        sensor_ids = list(self.sensor_mapping.values())
        if not self.show_references and len(sensor_ids) > 12:
            sensor_ids = sensor_ids[:12]  # Solo los primeros 12 (corona)
        
        # Crear subplots ajustados al número de sensores
        n_sensors = len(sensor_ids)
        n_rows = (n_sensors + 1) // 2  # Redondear hacia arriba
        fig, axes = plt.subplots(n_rows, 2, figsize=(14, n_rows * 2.7))
        axes = axes.flatten()
        
        # Título general de la figura
        # Calcular minutos para el título
        tmin_label = int((time_20min - time_start).total_seconds() / 60)
        tmax_label = int((time_40min - time_start).total_seconds() / 60)
        
        fig.suptitle(
            f"Centered Temperature Offsets ({tmin_label}-{tmax_label} min)\n"
            f"Run Number: {n_run} | Date: {date} | CalibSet: {calib_set_number}\n"
            f"Ref. Sensors: {ref_sensor_1}, {ref_sensor_2}",
            fontsize=16, fontweight="bold", y=1.02
        )

        for i, sensor in enumerate(sensor_ids):
            ax = axes[i]
            # Verificar que el sensor esté presente en los datos filtrados antes de intentar operar
            if sensor in filtered_data.columns:
                for other_sensor in sensor_ids:
                    if other_sensor in filtered_data.columns:
                        offset = filtered_data[sensor] - filtered_data[other_sensor]
                        offset_mean = offset.mean()
                        
                        #offset_centered = offset - offset_mean #queremos restar el primer minuto y no la media
                        #offset_centered = offset - offset.iloc[0]
                        first_minute_mask = (filtered_data.index - filtered_data.index[0]).total_seconds() <= 60
                        offset_baseline = offset[first_minute_mask].mean()
                        offset_centered = offset - offset_baseline
                        
           
                        ax.plot(filtered_data.index, offset_centered, label=f"{sensor}-{other_sensor}")
            else:
                ax.set_title(f"Sensor {sensor} no encontrado", fontsize=11, fontweight="bold")
                ax.axis("off")

            #ax.set_title(f"Sensor {sensor} ({self.filename})", fontsize=11, fontweight="bold")
            #ax.set_title(f"Sensor {sensor}\n"
                  #f"Run Number: {n_run} | Date: {date}\n"
                  #f"CalibSet: {calib_set_number}\n"
                  #f"Ref Sensors: {ref_sensor_1}, {ref_sensor_2}", fontsize=14, fontweight="bold")
            ax.set_title(f"Sensor {sensor}", fontsize=11, fontweight="bold")
            ax.set_xlabel("Time", fontsize=10, fontweight="bold")
            ax.set_ylabel("Centered Offset (K)", fontsize=10, fontweight="bold")
            ax.axvline(time_20min, color='red', linestyle='--', linewidth=2)
            ax.axvline(time_40min, color='blue', linestyle='--', linewidth=2)
            ax.legend(fontsize=8, loc="upper left", ncol=2)
            ax.grid(which='both', linestyle='--', linewidth=0.5)

        for ax in axes[len(sensor_ids):]:
            ax.axis("off")

        #fig.tight_layout()
        fig.tight_layout(rect=[0, 0, 1, 0.9991])  # dejar espacio para el suptitle
        fig.savefig(os.path.join(output_dir, f"{self.filename}_offsets_between_sensors_20_to_40_min.png"))
        plt.show()
        plt.close()
        
    def create_raw_offset_plot(self, output_dir: str = "./Plots/") -> None:
        """
        Crea y guarda el gráfico de offsets sin centrar entre sensores.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Calcular ventana de tiempo usando el método helper
        time_start, time_20min, time_40min = self._calculate_time_window()
        
         # Información adicional de los sensores y del run
        first_sensor = self.run_info.get("First_Sensor_ID", "Desconocido")
        last_sensor = self.run_info.get("Last_Sensor_ID", "Desconocido")
        ref_sensor_1 = self.run_info.get("Ref_Sensor_1", "Desconocido")
        ref_sensor_2 = self.run_info.get("Ref_Sensor_2", "Desconocido")
        calib_set_number = self.run_info.get("CalibSetNumber", "Desconocido")
        date = self.run_info.get("Date", "Desconocido")
        n_run = self.run_info.get("N_Run", "Desconocido")

        # Filtrar sensores según show_references
        sensor_ids = list(self.sensor_mapping.values())
        if not self.show_references and len(sensor_ids) > 12:
            sensor_ids = sensor_ids[:12]  # Solo los primeros 12 (corona)
        
        # Crear subplots ajustados al número de sensores
        n_sensors = len(sensor_ids)
        n_rows = (n_sensors + 1) // 2  # Redondear hacia arriba
        fig, axes = plt.subplots(n_rows, 2, figsize=(14, n_rows * 2.7))
        axes = axes.flatten()
        
        fig.suptitle(
        f"Raw Temperature Offsets\n"
        f"Run Number: {n_run} | Date: {date} | CalibSet: {calib_set_number}\n"
        f"Ref. Sensors: {ref_sensor_1}, {ref_sensor_2}",
        fontsize=16, fontweight="bold", y=1.02
    )

        for i, sensor in enumerate(sensor_ids):
            ax = axes[i]
            # Verificar que el sensor esté presente en los datos antes de intentar operar
            if sensor in self.temperature_data.columns:
                for other_sensor in sensor_ids:
                    if other_sensor in self.temperature_data.columns:
                        offset = self.temperature_data[sensor] - self.temperature_data[other_sensor]
                        ax.plot(self.temperature_data.index, offset, label=f"{sensor}-{other_sensor}")
            else:
                ax.set_title(f"Sensor {sensor} no encontrado", fontsize=11, fontweight="bold")
                ax.axis("off")
            
            #ax.set_title(f"Sensor {sensor} Raw Offsets ({self.filename})", fontsize=11, fontweight="bold")
            #ax.set_title(f"Sensor {sensor} Raw Offsets\n"
                 # f"Run Number: {n_run} | Date: {date}\n"
                 # f"CalibSet: {calib_set_number}\n"
                  #f"Ref Sensors: {ref_sensor_1}, {ref_sensor_2}", fontsize=14, fontweight="bold")
            ax.set_title(f"Sensor {sensor}", fontsize=11, fontweight="bold")
            ax.set_xlabel("Time", fontsize=10, fontweight="bold")
            ax.set_ylabel("Raw Offset (K)", fontsize=10, fontweight="bold")
            #ax.set_ylim(-0.1, 0.1)
            ax.axvline(time_20min, color='red', linestyle='--', linewidth=2)
            ax.axvline(time_40min, color='blue', linestyle='--', linewidth=2)
            ax.legend(fontsize=8, loc="upper left", ncol=2)
            ax.grid(which='both', linestyle='--', linewidth=0.5)

        for ax in axes[len(sensor_ids):]:
            ax.axis("off")

        #fig.tight_layout()
        fig.tight_layout(rect=[0, 0, 1, 0.9991])
        fig.savefig(os.path.join(output_dir, f"{self.filename}_raw_offsets_between_sensors.png"))
        plt.show()
        plt.close()

    def save_control_plots(self, output_dir: str = "./Plots/") -> None:
        """
        Llama a las funciones para crear y guardar los gráficos.
        """
        self.create_temperature_plot(output_dir=output_dir)
        self.create_offset_plot(output_dir=output_dir)
        self.create_raw_offset_plot(output_dir=output_dir)
        print(f"Plots saved in {output_dir}")

    def offsets(self, tini: int = 20, tend: int = 40) -> pd.DataFrame:
        """
        Calcula los offsets como la media de las diferencias entre pares de sensores
        en una ventana temporal específica.
        
        Args:
            tini: Tiempo inicial en minutos desde el inicio del run (default: 20)
            tend: Tiempo final en minutos desde el inicio del run (default: 40)
        
        Retorna un DataFrame organizado como una matriz de sensores (filas y columnas).
        """
        try:
            # Calcular ventana temporal
            time_start = self.temperature_data.index.min()
            time_20min = time_start + pd.Timedelta(minutes=tini)
            time_40min = time_start + pd.Timedelta(minutes=tend)
            
            # Filtrar datos en la ventana temporal
            filtered_data = self.temperature_data.loc[time_20min:time_40min]
            
            if filtered_data.empty:
                print(f"⚠️  WARNING: No data in time window {tini}-{tend} minutes")
                return pd.DataFrame()
            
            # Obtener los sensores activos (excluyendo los defectuosos)
            active_sensors = [sensor for sensor in self.sensor_mapping.values() if sensor in filtered_data.columns]

            offset_matrix = pd.DataFrame(index=active_sensors, columns=active_sensors, dtype=float)

            # Calcular los offsets solo entre sensores activos
            for i, sensor1 in enumerate(active_sensors):
                for j, sensor2 in enumerate(active_sensors):
                    if i == j:
                        offset_matrix.loc[sensor1, sensor2] = 0  # Diagonal con ceros
                    elif i < j:
                        # Verificar si toda la columna de cualquiera de los dos sensores es NaN
                        if filtered_data[sensor1].isna().all() or filtered_data[sensor2].isna().all():
                            offset_matrix.loc[sensor1, sensor2] = float('nan')
                            offset_matrix.loc[sensor2, sensor1] = float('nan')
                        else:
                            mean_offset = (filtered_data[sensor1] - filtered_data[sensor2]).mean()
                            offset_matrix.loc[sensor1, sensor2] = mean_offset
                            offset_matrix.loc[sensor2, sensor1] = -mean_offset  # Relación simétrica inversa

            print(f"Offsets medios calculados exitosamente para ventana {tini}-{tend} min.")
            self.offsets_data = offset_matrix
            return offset_matrix

        except Exception as e:
            print(f"Error al calcular offsets del run: {e}")
            return pd.DataFrame()


    def stat_err_offsets(self, tini: int = -20, tend: int = 0) -> pd.DataFrame:
        """
        Calcula el error RMS respecto a la media para cada pareja de sensores
        en una ventana temporal específica (relativa al final del run).
        
        Args:
            tini: Tiempo inicial en minutos desde el FINAL del run (default: -20, últimos 20 minutos)
            tend: Tiempo final en minutos desde el FINAL del run (default: 0, hasta el final)
        
        Retorna un DataFrame organizado como una matriz de sensores (filas y columnas).
        """
        try:
            if not hasattr(self, 'offsets_data'):
                raise ValueError("Debe calcular los offsets antes de calcular los errores RMS.")

            # Calcular ventana temporal relativa al final
            time_end = self.temperature_data.index.max()
            time_start_window = time_end + pd.Timedelta(minutes=tini)  # tini es negativo, ej: -20
            time_end_window = time_end + pd.Timedelta(minutes=tend)    # tend es 0
            
            # Filtrar datos en la ventana temporal
            filtered_data = self.temperature_data.loc[time_start_window:time_end_window]
            
            if filtered_data.empty:
                print(f"⚠️  WARNING: No data in RMS time window {tini}-{tend} minutes from end")
                return pd.DataFrame()

            # Filtrar solo los sensores activos
            active_sensors = [sensor for sensor in self.sensor_mapping.values() if sensor in filtered_data.columns]
            
            if not active_sensors:
                raise ValueError("No hay sensores activos para calcular los errores RMS.")

            # Inicializar el DataFrame de RMS
            rms_matrix = pd.DataFrame(index=active_sensors, columns=active_sensors, dtype=float)

            for i, sensor1 in enumerate(active_sensors):
                for j, sensor2 in enumerate(active_sensors):
                    if i == j:
                        rms_matrix.loc[sensor1, sensor2] = 0  # Diagonal con ceros
                    elif i < j:
                        mean_offset = self.offsets_data.loc[sensor1, sensor2]  # Obtener el offset promedio
                        rms_error = ((filtered_data[sensor1] - filtered_data[sensor2] - mean_offset) ** 2).mean() ** 0.5
                        rms_matrix.loc[sensor1, sensor2] = rms_error
                        rms_matrix.loc[sensor2, sensor1] = rms_error  # Simetría

            print(f"Errores RMS calculados exitosamente para ventana {tini}-{tend} min desde final.")
            self.rms_offsets = rms_matrix
            return rms_matrix

        except Exception as e:
            print(f"Error al calcular errores RMS del run: {e}")
            return pd.DataFrame()

    def plot_rms_vs_time(self, output_dir: str = "./Plots/") -> None:
        """
        Genera gráficos RMS vs. tiempo para cada sensor activo respecto al primer sensor como referencia.
        Muestra 14 gráficos juntos en una figura de subplots y calcula la RMS del intervalo de 20 minutos.
        Los gráficos comparten la misma escala vertical y se muestra el valor de referencia.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Filtrar sensores activos (sensores presentes en los datos) que serán todos los del logfile en principio
        active_sensors = [sensor for sensor in self.sensor_mapping.values() if sensor in self.temperature_data.columns]

        if not active_sensors:
            print("No hay sensores activos disponibles para graficar.")
            return

        # Inicializar la figura con 14 subplots (2 columnas por 7 filas)
        num_sensors = len(active_sensors)
        rows = (num_sensors // 2) + (num_sensors % 2)  # Calcular filas necesarias
        fig, axes = plt.subplots(rows, 2, figsize=(14, 19))
        axes = axes.flatten()  # Aplanar para un acceso más sencillo

        # Obtener el primer sensor RTD como referencia
        reference_sensor = active_sensors[0]

        # Lista para almacenar todos los valores de RMS (para calcular escala global)
        all_rms_values = []

        # Calcular el tiempo de inicio y los intervalos de 20 minutos
        time_start = self.temperature_data.index.min()
        time_max = self.temperature_data.index.max()
        time_20min = time_start + pd.Timedelta(minutes=20)
        time_40min = time_max
        
         # Información adicional de los sensores y del run
        first_sensor = self.run_info.get("First_Sensor_ID", "Desconocido")
        last_sensor = self.run_info.get("Last_Sensor_ID", "Desconocido")
        ref_sensor_1 = self.run_info.get("Ref_Sensor_1", "Desconocido")
        ref_sensor_2 = self.run_info.get("Ref_Sensor_2", "Desconocido")
        calib_set_number = self.run_info.get("CalibSetNumber", "Desconocido")
        date = self.run_info.get("Date", "Desconocido")
        n_run = self.run_info.get("N_Run", "Desconocido")

        # Preprocesar RMS de todos los sensores activos para obtener el mínimo y máximo global
        for sensor in active_sensors:
            offset = self.temperature_data[reference_sensor] - self.temperature_data[sensor]
            rms_per_minute = offset.resample('1min').std()
            all_rms_values.extend(rms_per_minute.dropna().values)  # Guardar los valores válidos

        # Calcular escala vertical global
        global_min = min(all_rms_values)
        global_max = max(all_rms_values)

        # Crear los subplots para cada sensor activo
        for i, sensor in enumerate(active_sensors):
            ax = axes[i]

            # Calcular el offset y RMS
            offset = self.temperature_data[reference_sensor] - self.temperature_data[sensor]
            rms_per_minute = offset.resample('1min').std()

            # Calcular RMS para el intervalo de 20 minutos
            interval_data = rms_per_minute.loc[time_20min:time_40min]
            rms_20min = interval_data.std()

            # Graficar RMS vs tiempo
            ax.plot(rms_per_minute.index, rms_per_minute, label="RMS por minuto")
            ax.axvline(time_20min, color='red', linestyle='--', linewidth=2, label="20 minutos")
            ax.axvline(time_40min, color='blue', linestyle='--', linewidth=2, label="40 minutos")

            # Ajustar la escala vertical
            ax.set_ylim(global_min, global_max)

            # Agregar título y etiquetas
            ax.set_title(f"RMS: {rms_20min:.4f} | Sensor {sensor}\nRef: {reference_sensor}", 
                         fontsize=10, fontweight="bold")
            ax.set_xlabel("Time", fontsize=10, fontweight="bold")
            ax.set_ylabel("RMS (K)", fontsize=10, fontweight="bold")
            ax.legend(fontsize=8, loc="upper left", ncol=2)
            ax.grid(which='both', linestyle='--', linewidth=0.5)

        # Desactivar subplots no utilizados
        for ax in axes[len(active_sensors):]:
            ax.axis("off")

        # Ajustar el diseño y guardar la figura
        fig.tight_layout()
        output_file = os.path.join(output_dir, f"{self.filename}_rms_vs_time.png")
        plt.savefig(output_file)
        print(f"Gráfico guardado en: {output_file}")
        plt.show()
        plt.close()
