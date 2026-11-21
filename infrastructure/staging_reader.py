"""Lee las tablas staging (stg.*) del Data Warehouse para preparar la carga de dimensiones."""

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from application.interfaces import IStagingReader
from infrastructure.staging_writer import separar_tabla


class SqlServerStagingReader(IStagingReader):
    def __init__(self, engine: Engine):
        self.engine = engine

    def leer(self, tabla: str) -> pd.DataFrame:
        esquema, nombre = separar_tabla(tabla)  # valida el nombre antes de usarlo en SQL
        with self.engine.connect() as conexion:
            return pd.read_sql_query(text(f"SELECT * FROM [{esquema}].[{nombre}]"), conexion)

    def ultima_ejecucion(self, tablas: list[str]) -> int | None:
        ultimas = []
        with self.engine.connect() as conexion:
            for tabla in tablas:
                esquema, nombre = separar_tabla(tabla)
                valor = conexion.execute(text(f"SELECT MAX(IdEjecucion) FROM [{esquema}].[{nombre}]")).scalar()
                if valor is not None:
                    ultimas.append(int(valor))
        return max(ultimas) if ultimas else None

    def tablas_faltantes(self, tablas: list[str]) -> list[str]:
        inspector = inspect(self.engine)
        faltantes = []
        for tabla in tablas:
            esquema, nombre = separar_tabla(tabla)
            if not inspector.has_table(nombre, schema=esquema):
                faltantes.append(tabla)
        return faltantes
