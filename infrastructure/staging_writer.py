"""Escribe los datos extraídos en las tablas staging (equivale al DataLoader)."""

import logging
import re
import time
from datetime import datetime

import pandas as pd
from sqlalchemy import column, insert, inspect, table, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from application.interfaces import IStagingWriter

# Solo se aceptan nombres "esquema.tabla" con letras, números y guion bajo.
# El nombre viene de appsettings.json, pero se valida antes de usarlo en SQL.
PATRON_TABLA = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$")


def separar_tabla(tabla: str) -> tuple[str, str]:
    coincidencia = PATRON_TABLA.match(tabla)
    if not coincidencia:
        raise ValueError(f"Nombre de tabla inválido '{tabla}': use el formato esquema.tabla")
    return coincidencia.group(1), coincidencia.group(2)


def preparar_para_sql(datos: pd.DataFrame, id_ejecucion: int,
                      fecha_extraccion: datetime) -> pd.DataFrame:
    """Agrega las columnas de auditoría y deja solo tipos que entiende el driver:
    NaN/NaT pasan a None (NULL en SQL) y los Timestamp de pandas a datetime de Python."""
    preparado = datos.copy()
    for nombre_columna in preparado.columns:
        if pd.api.types.is_datetime64_any_dtype(preparado[nombre_columna]):
            preparado[nombre_columna] = pd.Series(
                list(preparado[nombre_columna].dt.to_pydatetime()), index=preparado.index, dtype=object
            )
    preparado = preparado.astype(object)
    preparado = preparado.where(preparado.notna(), None)
    preparado["IdEjecucion"] = pd.Series([id_ejecucion] * len(preparado), index=preparado.index, dtype=object)
    preparado["FechaExtraccion"] = pd.Series([fecha_extraccion] * len(preparado), index=preparado.index, dtype=object)
    return preparado


def es_interbloqueo(error: DBAPIError) -> bool:
    """SQL Server 1205 / SQLSTATE 40001: la transacción fue elegida víctima de un interbloqueo."""
    mensaje = str(error.orig)
    return "1205" in mensaje or "40001" in mensaje


class SqlServerStagingWriter(IStagingWriter):
    """Vacía la tabla con TRUNCATE y la llena con inserción masiva, todo en UNA transacción.

    Si algo falla a mitad de la inserción, la transacción se revierte y la
    tabla conserva los datos de la ejecución anterior.
    """

    # TRUNCATE es mucho más rápido que DELETE: no registra fila por fila en el log de transacciones.
    SENTENCIA_VACIAR = "TRUNCATE TABLE [{esquema}].[{tabla}]"

    def __init__(self, engine: Engine, tamano_lote: int = 5000, reintentos: int = 3,
                 logger: logging.Logger | None = None):
        self.engine = engine  # creado con fast_executemany=True
        self.tamano_lote = tamano_lote
        self.reintentos = reintentos
        self.logger = logger or logging.getLogger("extraccion.staging")

    def escribir(self, tabla: str, datos: pd.DataFrame, id_ejecucion: int,
                 fecha_extraccion: datetime) -> int:
        esquema, nombre = separar_tabla(tabla)
        preparado = preparar_para_sql(datos, id_ejecucion, fecha_extraccion)
        registros = preparado.to_dict("records")
        # Tabla "ligera": se arma con los nombres de columna conocidos, sin consultar el
        # catálogo de SQL Server. Así no se leen metadatos mientras otras tablas hacen
        # TRUNCATE en paralelo (eso provocaba interbloqueos).
        destino = table(nombre, *(column(c) for c in preparado.columns), schema=esquema)

        intento = 0
        while True:
            intento += 1
            try:
                with self.engine.begin() as conexion:
                    conexion.execute(text(self.SENTENCIA_VACIAR.format(esquema=esquema, tabla=nombre)))
                    for inicio in range(0, len(registros), self.tamano_lote):
                        conexion.execute(insert(destino), registros[inicio:inicio + self.tamano_lote])
                return len(registros)
            except DBAPIError as error:
                # Un interbloqueo es temporal: SQL Server pide "Rerun the transaction".
                if not es_interbloqueo(error) or intento > self.reintentos:
                    raise
                espera = 0.2 * intento
                self.logger.warning("%s: interbloqueo, reintento %d en %.1f s", tabla, intento, espera)
                time.sleep(espera)

    def tablas_faltantes(self, tablas: list[str]) -> list[str]:
        inspector = inspect(self.engine)
        faltantes = []
        for tabla in tablas:
            esquema, nombre = separar_tabla(tabla)
            if not inspector.has_table(nombre, schema=esquema):
                faltantes.append(tabla)
        return faltantes
