import pandas as pd 
from application.interfaces import IExtractor

class CsvExtractor(IExtractor):
    def __init__(self, ruta_archivo: str):
        self.ruta_archivo = ruta_archivo

    def extraer(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.ruta_archivo)
        except Exception as e:
            print(f"[ERROR EXTRACTOR] no se pudo leer {self.ruta_archivo}: {e}")
            return pd.DataFrame()
            


