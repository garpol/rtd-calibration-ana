import pandas as pd
import os

class Logfile:
    def __init__(self, filepath: str) -> None: 
        """
        Class to handle reading a local CSV file.

        Parameters:
            filepath (str): Path to the local CSV file.
        """
        self.filepath = filepath
        self.log_file = self.download_logfile()

    def download_logfile(self):
        """
        Function to read data from a local CSV file.

        Returns:
            pandas.DataFrame: DataFrame containing the data from the CSV file.
        """
        try:
            # Leer el archivo CSV
            df = pd.read_csv(self.filepath)
            print(f"Archivo CSV cargado correctamente desde '{self.filepath}'.")
            return df
        except Exception as e:
            raise RuntimeError(f"An error occurred while reading the log file: {e}")

    def select_files(self, **kwargs): 
        """
        Select files from a log file DataFrame based on given conditions.

        Parameters:
            kwargs (dict): Dictionary of column-value pairs specifying conditions for selection.
                Values can be a single value or a list of values.

        Returns:
            pandas.DataFrame: DataFrame containing selected rows based on the conditions.
        """
        try:
            selection = self.log_file.copy()  # Crea una copia del DataFrame original para no modificarlo directamente

            for column, value in kwargs.items():
                # Verifica que la columna existe en el DataFrame
                if column not in selection.columns:
                    raise ValueError(f"Column '{column}' does not exist in the DataFrame.")

                # Verifica si el valor es una lista (valor proporcionado como argumento kwargs)
                if isinstance(value, list):
                    # Usa isin() para filtrar las filas donde el valor de la columna esté en la lista
                    selection = selection.loc[selection[column].isin(value)]
                else:
                    # Si el valor no es una lista, filtra las filas donde el valor de la columna coincida
                    selection = selection.loc[selection[column] == value]

            return selection

        except Exception as e:
            # En caso de error, se lanza una excepción detallada
            raise RuntimeError(f"An error occurred while selecting files: {e}")
