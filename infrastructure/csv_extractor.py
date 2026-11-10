import pandas as pd

from application.interfaces import IExtractor


class CsvExtractor(IExtractor):
    """Lee un CSV completo en un DataFrame.

    `opciones_lectura` se pasa tal cual a `pandas.read_csv`. El ETL relacional
    no la usa; la extracción al DW la usa para leer todo como texto.
    """

    def __init__(self, ruta_archivo, encoding="utf-8", opciones_lectura=None):
        self.ruta_archivo = ruta_archivo
        self.encoding = encoding
        self.opciones_lectura = opciones_lectura or {}

    def extraer(self):
        try:
            datos = pd.read_csv(self.ruta_archivo, encoding=self.encoding, **self.opciones_lectura)
        except (OSError, UnicodeError, pd.errors.ParserError) as error:
            raise RuntimeError(f"No se pudo leer el CSV {self.ruta_archivo}: {error}") from error
        if datos.empty:
            raise ValueError(f"El CSV no contiene registros: {self.ruta_archivo}")
        return datos
