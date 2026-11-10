"""Servicio que orquesta la extracción (E) hacia el Data Warehouse.

Solo depende de interfaces: no sabe si una fuente es un CSV, una base de datos
o una API. Por eso agregar una fuente nueva no obliga a cambiar este archivo.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from application.interfaces import IExtractorAsync, IRunLogRepository, IStagingWriter

TABLAS_BITACORA = ["etl.EjecucionExtraccion", "etl.DetalleExtraccion"]


class ErrorDestino(Exception):
    """El Data Warehouse no tiene las tablas que el worker necesita."""


@dataclass
class ResultadoFuente:
    nombre: str
    tipo_fuente: str
    tabla_destino: str
    filas: int
    duracion_segundos: float
    estado: str                 # "Exitosa" o "Fallida"
    mensaje: Optional[str] = None


@dataclass
class ResumenEjecucion:
    id_ejecucion: int
    estado: str                 # "Exitosa", "Parcial" o "Fallida"
    filas_totales: int
    duracion_segundos: float
    resultados: list[ResultadoFuente] = field(default_factory=list)


class ExtractionService:
    def __init__(self, extractores: list[IExtractorAsync], escritor: IStagingWriter,
                 bitacora: IRunLogRepository, logger: logging.Logger | None = None,
                 reloj: Callable[[], datetime] = datetime.now):
        if not extractores:
            raise ValueError("No hay fuentes activas en appsettings.json")
        self.extractores = extractores
        self.escritor = escritor
        self.bitacora = bitacora
        self.logger = logger or logging.getLogger("extraccion.servicio")
        self.reloj = reloj

    def verificar_destino(self) -> None:
        """Comprueba al arrancar que existan todas las tablas stg.* y etl.* necesarias."""
        tablas = sorted({e.tabla_destino for e in self.extractores}) + TABLAS_BITACORA
        faltantes = self.escritor.tablas_faltantes(tablas)
        if faltantes:
            raise ErrorDestino(
                "Faltan tablas en el Data Warehouse: " + ", ".join(faltantes)
                + ". Ejecute los scripts de la carpeta sql/."
            )
        self.logger.info("Destino verificado: %d tablas encontradas", len(tablas))

    async def ejecutar(self) -> ResumenEjecucion:
        inicio = self.reloj()
        cronometro = time.perf_counter()
        id_ejecucion = await asyncio.to_thread(self.bitacora.iniciar, inicio)
        self.logger.info("Ejecución %d iniciada con %d fuentes", id_ejecucion, len(self.extractores))

        # Todas las fuentes en paralelo (equivale a Task.WhenAll en .NET).
        resultados = await asyncio.gather(
            *(self._procesar(extractor, id_ejecucion, inicio) for extractor in self.extractores)
        )

        duracion = time.perf_counter() - cronometro
        filas_totales = sum(r.filas for r in resultados)
        fallidas = [r for r in resultados if r.estado == "Fallida"]
        if not fallidas:
            estado = "Exitosa"
        elif len(fallidas) == len(resultados):
            estado = "Fallida"
        else:
            estado = "Parcial"
        mensaje = "; ".join(f"{r.nombre}: {r.mensaje}" for r in fallidas) or None

        await asyncio.to_thread(
            self.bitacora.finalizar, id_ejecucion, self.reloj(), estado,
            filas_totales, duracion, mensaje,
        )
        nivel = logging.INFO if estado == "Exitosa" else logging.WARNING
        self.logger.log(
            nivel, "Ejecución %d %s: %d filas en %.2f s (%d de %d fuentes con error)",
            id_ejecucion, estado.lower(), filas_totales, duracion, len(fallidas), len(resultados),
        )
        return ResumenEjecucion(id_ejecucion, estado, filas_totales, duracion, list(resultados))

    async def _procesar(self, extractor: IExtractorAsync, id_ejecucion: int,
                        fecha_extraccion: datetime) -> ResultadoFuente:
        cronometro = time.perf_counter()
        filas, estado, mensaje = 0, "Exitosa", None
        try:
            datos = await extractor.extraer()
            segundos_lectura = time.perf_counter() - cronometro
            filas = await asyncio.to_thread(
                self.escritor.escribir, extractor.tabla_destino, datos,
                id_ejecucion, fecha_extraccion,
            )
            duracion = time.perf_counter() - cronometro
            self.logger.info(
                "%s -> %s: %d filas (lectura %.2f s, total %.2f s)",
                extractor.nombre, extractor.tabla_destino, filas, segundos_lectura, duracion,
            )
        except Exception as error:  # una fuente que falla no detiene a las demás
            estado, mensaje = "Fallida", f"{type(error).__name__}: {error}"
            filas = 0
            # Mensaje corto en consola; el traceback completo solo con Nivel DEBUG.
            self.logger.error("%s falló: %s", extractor.nombre, mensaje.splitlines()[0])
            self.logger.debug("Detalle de %s", extractor.nombre, exc_info=True)

        duracion = time.perf_counter() - cronometro
        resultado = ResultadoFuente(extractor.nombre, extractor.tipo_fuente,
                                    extractor.tabla_destino, filas, duracion, estado, mensaje)
        try:
            await asyncio.to_thread(
                self.bitacora.registrar_detalle, id_ejecucion, resultado.tipo_fuente,
                resultado.tabla_destino, resultado.filas, resultado.duracion_segundos,
                resultado.estado, resultado.mensaje,
            )
        except Exception:
            self.logger.exception("No se pudo registrar el detalle de %s en la bitácora",
                                  extractor.nombre)
        return resultado
