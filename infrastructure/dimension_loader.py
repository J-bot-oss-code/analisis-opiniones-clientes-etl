"""Envía las filas de una dimensión a su procedimiento almacenado con un parámetro de tipo tabla (TVP).

pyodbc recibe el TVP como una lista: primero el NOMBRE del tipo, luego su ESQUEMA y después una tupla
por fila.  Se usa la conexión ODBC directa porque SQLAlchemy no maneja TVP.
El procedimiento hace su propia transacción; aquí se confirma (commit) al terminar bien y se revierte si falla.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from application.interfaces import ConteosCarga, IDimensionLoader
from infrastructure.staging_writer import separar_tabla


def construir_parametro_tabla(tipo_sql: str, filas: list[tuple]) -> list:
    """['T_Dim_Cliente', 'etl', (fila1), (fila2), ...] — formato que espera pyodbc."""
    esquema, nombre = separar_tabla(tipo_sql)
    return [nombre, esquema, *filas]


class SqlServerDimensionLoader(IDimensionLoader):
    def __init__(self, engine: Engine):
        self.engine = engine

    def cargar(self, tipo_sql: str, procedimiento: str, filas: list[tuple]) -> ConteosCarga:
        if not filas:
            raise ValueError("No se puede enviar un lote vacío al procedimiento")
        esquema, nombre = separar_tabla(procedimiento)  # valida el nombre antes de usarlo en SQL
        sentencia = f"EXEC [{esquema}].[{nombre}] @Datos = ?"
        conexion = self.engine.raw_connection()
        try:
            cursor = conexion.cursor()
            cursor.execute(sentencia, (construir_parametro_tabla(tipo_sql, filas),))
            resultado = cursor.fetchone()
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()
        return ConteosCarga(enviadas=int(resultado[0]), insertadas=int(resultado[1]),
                            actualizadas=int(resultado[2]), sin_cambios=int(resultado[3]))

    def procedimientos_faltantes(self, procedimientos: list[str]) -> list[str]:
        with self.engine.connect() as conexion:
            existentes = {
                f"{fila[0]}.{fila[1]}".lower()
                for fila in conexion.execute(text(
                    "SELECT SCHEMA_NAME(schema_id), name FROM sys.procedures"))
            }
        return [p for p in procedimientos if p.lower() not in existentes]
