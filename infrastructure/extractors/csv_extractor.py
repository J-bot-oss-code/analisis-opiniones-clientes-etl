"""Extrae las encuestas internas desde un CSV (equivale a CsvHelper)."""

import asyncio
from pathlib import Path

import pandas as pd

from application.interfaces import IExtractorAsync
from infrastructure.csv_extractor import CsvExtractor


class CsvExtractorAsync(IExtractorAsync):
    """Reutiliza el `CsvExtractor` del ETL relacional y lo adapta a staging.

    - Lee todas las columnas como texto: staging guarda los datos tal como vienen.
    - Valida que estén las columnas esperadas y las renombra (quita tildes)
      según el mapa `columnas` de appsettings.json.
    """

    def __init__(self, nombre: str, tabla_destino: str, ruta: Path,
                 columnas: dict[str, str], codificacion: str = "utf-8-sig"):
        super().__init__(nombre, "CSV", tabla_destino)
        self.ruta = ruta
        self.columnas = columnas
        self.lector = CsvExtractor(ruta, encoding=codificacion, opciones_lectura={"dtype": str})

    async def extraer(self) -> pd.DataFrame:
        return await asyncio.to_thread(self._leer)

    def _leer(self) -> pd.DataFrame:
        datos = self.lector.extraer()
        datos.columns = [str(c).strip() for c in datos.columns]

        faltantes = [c for c in self.columnas if c not in datos.columns]
        if faltantes:
            raise ValueError(
                f"{self.ruta.name} no tiene las columnas esperadas: {', '.join(faltantes)}"
            )
        return datos[list(self.columnas)].rename(columns=self.columnas)
