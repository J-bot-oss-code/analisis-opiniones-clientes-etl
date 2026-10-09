import pandas as pd
from sqlalchemy.exc import IntegrityError
from application.interfaces import ILoader
from infrastructure.db_config import engine


class SqlLoader(ILoader):
    def __init__(self, nombre_tabla: str):
        self.nombre_tabla = nombre_tabla

    def cargar(self, df: pd.DataFrame) -> tuple[int, int]:
        if df.empty:
            return 0, 0 

        try:
            df.to_sql(self.nombre_tabla, con=engine, if_exists='append', index=False)
            return len(df), 0
            
        except IntegrityError as e:
            print(f"[ERROR INTEGRIDAD - {self.nombre_tabla}] Violación PK/FK: {e.args[0]}")
            return 0, len(df)
        except Exception as e:
            print(f"[ERROR BD - {self.nombre_tabla}] Falla inesperada: {e}")
            return 0, len(df)