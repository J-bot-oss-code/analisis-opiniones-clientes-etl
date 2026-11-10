"""Contratos (interfaces) de la aplicación.

La capa de aplicación solo depende de estas abstracciones; las clases
concretas viven en `infrastructure/` (principio de inversión de dependencias).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Contratos del ETL relacional (OpinionesCliente). Se mantienen sin cambios.
# ---------------------------------------------------------------------------

class IExtractor(ABC):
    """Contrato para cualquier fuente de datos (csv, api, base de datos)."""

    @abstractmethod
    def extraer(self) -> pd.DataFrame:
        """Extrae los datos de la fuente especificada."""


class ITransformer(ABC):
    """Contrato para cualquier transformador de datos."""

    @abstractmethod
    def transformar(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Transforma los datos según las reglas de negocio."""


class ILoader(ABC):
    """Contrato para guardar los datos (sql server, postgresql, etc.)."""

    @abstractmethod
    def cargar(self, df: pd.DataFrame) -> Tuple[int, int]:
        """Guarda los datos en el destino de la carga."""


# ---------------------------------------------------------------------------
# Contratos de la extracción (E) hacia el Data Warehouse.
# ---------------------------------------------------------------------------

class IExtractorAsync(ABC):
    """Fuente de datos que se extrae de forma asíncrona hacia una tabla staging.

    Cada implementación sabe leer UN tipo de fuente (BD, CSV, API). El servicio
    de extracción no conoce los detalles: solo llama a `extraer()`.
    """

    def __init__(self, nombre: str, tipo_fuente: str, tabla_destino: str):
        self.nombre = nombre                # nombre legible, p. ej. "BD_Opinion"
        self.tipo_fuente = tipo_fuente      # "BD", "CSV" o "API" (CHECK en etl.DetalleExtraccion)
        self.tabla_destino = tabla_destino  # p. ej. "stg.Opinion"

    @abstractmethod
    async def extraer(self) -> pd.DataFrame:
        """Devuelve los datos tal como vienen de la fuente, sin transformar."""


class IStagingWriter(ABC):
    """Escribe un DataFrame en una tabla staging del Data Warehouse."""

    @abstractmethod
    def escribir(self, tabla: str, datos: pd.DataFrame, id_ejecucion: int,
                 fecha_extraccion: datetime) -> int:
        """Vacía la tabla y la llena con `datos`. Devuelve las filas insertadas."""

    @abstractmethod
    def tablas_faltantes(self, tablas: list[str]) -> list[str]:
        """Devuelve las tablas de la lista que no existen en el destino."""


class IRunLogRepository(ABC):
    """Bitácora de ejecuciones (tablas etl.EjecucionExtraccion y etl.DetalleExtraccion)."""

    @abstractmethod
    def iniciar(self, fecha_inicio: datetime) -> int:
        """Registra el inicio de una ejecución y devuelve su IdEjecucion."""

    @abstractmethod
    def registrar_detalle(self, id_ejecucion: int, fuente: str, tabla_destino: str,
                          filas: int, duracion_segundos: float, estado: str,
                          mensaje: Optional[str]) -> None:
        """Registra el resultado de una tabla extraída."""

    @abstractmethod
    def finalizar(self, id_ejecucion: int, fecha_fin: datetime, estado: str,
                  filas_totales: int, duracion_segundos: float,
                  mensaje: Optional[str]) -> None:
        """Cierra la ejecución con su estado final."""
