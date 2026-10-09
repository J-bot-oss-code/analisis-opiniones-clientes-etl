from abc import ABC, abstractmethod # abc es un módulo que proporciona herramientas para definir clases abstractas en Python.
import pandas as pd # pandas es una biblioteca de Python para manipulación y análisis de datos, especialmente útil para trabajar con estructuras de datos tabulares como DataFrames.
from typing import Tuple # typing es un módulo que proporciona soporte para anotaciones de tipo en Python, y Tuple es una de las estructuras de datos que se pueden usar para especificar tipos.


class IExtractor(ABC):
    """Contrato para cualquier fuente de datos (csv, api, base de datos)."""
    @abstractmethod
    def extraer(self) -> pd.DataFrame: 
     pass 
    """Extrae los datos de la fuente especificada."""

class ITransformer(ABC): 
    """Contrato para cualquier transformador de datos."""
    @abstractmethod
    def transformar(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]: 
     pass
    """Transforma los datos según las reglas de negocio."""

class ILoader(ABC):
    """Contrato para guardar los datos (sql server, postgresql, etc.)."""
    @abstractmethod
    def cargar(self, df: pd.DataFrame) -> Tuple[int, int]:
     pass    

    