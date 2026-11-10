import asyncio
from datetime import datetime

import pandas as pd
import pytest

from application.extraction_service import ErrorDestino, ExtractionService
from application.interfaces import IExtractorAsync, IRunLogRepository, IStagingWriter


class ExtractorFalso(IExtractorAsync):
    def __init__(self, nombre, filas=3, error=None, espera=0.0):
        super().__init__(nombre, "BD", f"stg.{nombre}")
        self.filas, self.error, self.espera = filas, error, espera

    async def extraer(self):
        await asyncio.sleep(self.espera)
        if self.error:
            raise self.error
        return pd.DataFrame({"Id": range(self.filas)})


class EscritorFalso(IStagingWriter):
    def __init__(self, faltantes=()):
        self.escrito, self.faltantes = {}, list(faltantes)

    def escribir(self, tabla, datos, id_ejecucion, fecha_extraccion):
        self.escrito[tabla] = (len(datos), id_ejecucion)
        return len(datos)

    def tablas_faltantes(self, tablas):
        return [t for t in tablas if t in self.faltantes]


class BitacoraFalsa(IRunLogRepository):
    def __init__(self):
        self.detalles, self.final = [], None

    def iniciar(self, fecha_inicio):
        return 42

    def registrar_detalle(self, id_ejecucion, fuente, tabla_destino, filas,
                          duracion_segundos, estado, mensaje):
        self.detalles.append((tabla_destino, filas, estado, mensaje))

    def finalizar(self, id_ejecucion, fecha_fin, estado, filas_totales,
                  duracion_segundos, mensaje):
        self.final = (estado, filas_totales, mensaje)


def test_todas_las_fuentes_exitosas():
    escritor, bitacora = EscritorFalso(), BitacoraFalsa()
    servicio = ExtractionService([ExtractorFalso("A", 3), ExtractorFalso("B", 5)], escritor, bitacora)

    resumen = asyncio.run(servicio.ejecutar())

    assert resumen.estado == "Exitosa"
    assert resumen.filas_totales == 8
    assert escritor.escrito == {"stg.A": (3, 42), "stg.B": (5, 42)}
    assert bitacora.final == ("Exitosa", 8, None)
    assert len(bitacora.detalles) == 2


def test_una_fuente_falla_y_las_demas_siguen():
    bitacora = BitacoraFalsa()
    servicio = ExtractionService(
        [ExtractorFalso("A", 3), ExtractorFalso("B", error=RuntimeError("sin conexión"))],
        EscritorFalso(), bitacora)

    resumen = asyncio.run(servicio.ejecutar())

    assert resumen.estado == "Parcial"
    assert resumen.filas_totales == 3
    assert ("stg.B", 0, "Fallida", "RuntimeError: sin conexión") in bitacora.detalles
    assert "sin conexión" in bitacora.final[2]


def test_todas_fallan():
    servicio = ExtractionService([ExtractorFalso("A", error=ValueError("x"))],
                                 EscritorFalso(), BitacoraFalsa())
    assert asyncio.run(servicio.ejecutar()).estado == "Fallida"


def test_las_fuentes_corren_en_paralelo():
    """Tres fuentes de 0.3 s deben tardar ~0.3 s en total, no 0.9 s."""
    fuentes = [ExtractorFalso(n, espera=0.3) for n in ("A", "B", "C")]
    servicio = ExtractionService(fuentes, EscritorFalso(), BitacoraFalsa())

    resumen = asyncio.run(servicio.ejecutar())

    assert resumen.duracion_segundos < 0.6


def test_verificar_destino_avisa_tablas_faltantes():
    servicio = ExtractionService([ExtractorFalso("A")], EscritorFalso(faltantes=["stg.A"]),
                                 BitacoraFalsa())
    with pytest.raises(ErrorDestino, match="stg.A"):
        servicio.verificar_destino()
