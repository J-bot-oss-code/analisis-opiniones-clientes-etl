"""Extrae datos de la base relacional OpinionesCliente (equivale a ADO.NET)."""

import asyncio
import logging

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from application.interfaces import IExtractorAsync


class DatabaseExtractor(IExtractorAsync):
    """Ejecuta una consulta fija (definida en appsettings.json) y la lee por lotes.

    La consulta viene del archivo de configuración, nunca de datos de entrada,
    así que no hay riesgo de inyección SQL.
    """

    def __init__(self, nombre: str, tabla_destino: str, engine: Engine, consulta: str,
                 tamano_lote: int = 5000, logger: logging.Logger | None = None):
        super().__init__(nombre, "BD", tabla_destino)
        self.engine = engine
        self.consulta = consulta
        self.tamano_lote = tamano_lote
        self.logger = logger or logging.getLogger(f"extraccion.{nombre}")

    async def extraer(self) -> pd.DataFrame:
        # pyodbc es bloqueante: se ejecuta en un hilo para no detener a las demás fuentes.
        return await asyncio.to_thread(self._leer)

    def _leer(self) -> pd.DataFrame:
        lotes = []
        with self.engine.connect() as conexion:
            resultado = conexion.execute(text(self.consulta))
            columnas = list(resultado.keys())
            # partitions() pide las filas al servidor de `tamano_lote` en `tamano_lote`.
            for numero, filas in enumerate(resultado.partitions(self.tamano_lote), start=1):
                lotes.append(pd.DataFrame(filas, columns=columnas))
                self.logger.debug("%s: lote %d leído (%d filas)", self.nombre, numero, len(filas))

        if not lotes:
            return pd.DataFrame(columns=columnas)
        return pd.concat(lotes, ignore_index=True)
