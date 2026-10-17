from abc import ABC, abstractmethod
from typing import Tuple

import pandas as pd


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

    