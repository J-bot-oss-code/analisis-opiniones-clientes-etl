import pandas as pd


class CsvExtractor:
    def __init__(self, ruta_archivo):
        self.ruta_archivo = ruta_archivo

    def extraer(self):
        try:
            datos = pd.read_csv(self.ruta_archivo, encoding="utf-8")
        except (OSError, UnicodeError, pd.errors.ParserError) as error:
            raise RuntimeError(f"No se pudo leer el CSV {self.ruta_archivo}: {error}") from error
        if datos.empty:
            raise ValueError(f"El CSV no contiene registros: {self.ruta_archivo}")
        return datos
