import pandas as pd
from sqlalchemy import create_engine
from application.interfaces import IExtractor

class DbExtractor(IExtractor):
    """Extrae datos desde una base de datos relacional ejecutando un query SQL."""
    
    def __init__(self, cadena_conexion_origen: str, query: str):
        self.cadena_conexion = cadena_conexion_origen
        self.query = query

    def extraer(self) -> pd.DataFrame:
        try:
            # Creamos un motor temporal solo para leer los datos de origen
            engine = create_engine(self.cadena_conexion)
            
            # Pandas hace la magia de ejecutar el query y devolver una tabla (DataFrame)
            df = pd.read_sql(self.query, con=engine)
            
            print(f"[EXTRACTOR DB] Éxito: Se extrajeron {len(df)} registros de la base de datos origen.")
            return df
            
        except Exception as e:
            print(f"[ERROR EXTRACTOR DB] Fallo al consultar la base de datos: {e}")
            return pd.DataFrame() # Retorna tabla vacía para no romper el pipeline