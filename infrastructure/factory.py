"""Construye los objetos del worker a partir de appsettings.json (composition root).

Para agregar un tipo de fuente nuevo:
1. Crear una clase que herede de IExtractorAsync.
2. Agregar una función `_crear_<tipo>` y registrarla en FABRICAS.
3. Añadir la fuente en appsettings.json con ese "Tipo".
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Callable

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from application.dimension_preparation import OpcionesDimensiones
from application.dimension_service import DimensionLoadService
from application.extraction_service import ExtractionService
from application.interfaces import IExtractorAsync
from infrastructure.dimension_loader import SqlServerDimensionLoader
from infrastructure.dimension_log_repository import SqlServerDimensionLogRepository
from infrastructure.extractors import ApiExtractor, CsvExtractorAsync, DatabaseExtractor
from infrastructure.run_log_repository import SqlServerRunLogRepository
from infrastructure.settings import (Configuracion, ErrorConfiguracion, crear_url_sql_server,
                                     ruta_del_proyecto, secreto)
from infrastructure.staging_reader import SqlServerStagingReader
from infrastructure.staging_writer import SqlServerStagingWriter


@dataclass
class Contexto:
    config: Configuracion
    logger: logging.Logger
    motor_origen: Callable[[], Engine]  # se crea solo si alguna fuente es de tipo BD


def _crear_bd(fuente: dict, ctx: Contexto) -> IExtractorAsync:
    return DatabaseExtractor(
        nombre=fuente["Nombre"],
        tabla_destino=fuente["TablaDestino"],
        engine=ctx.motor_origen(),
        consulta=fuente["Consulta"],
        tamano_lote=ctx.config.tamano_lote,
        logger=ctx.logger.getChild(fuente["Nombre"]),
    )


def _crear_csv(fuente: dict, ctx: Contexto) -> IExtractorAsync:
    return CsvExtractorAsync(
        nombre=fuente["Nombre"],
        tabla_destino=fuente["TablaDestino"],
        ruta=ruta_del_proyecto(fuente["Ruta"]),
        columnas=fuente["Columnas"],
        codificacion=fuente.get("Codificacion", "utf-8-sig"),
    )


def _crear_api(fuente: dict, ctx: Contexto) -> IExtractorAsync:
    return ApiExtractor(
        nombre=fuente["Nombre"],
        tabla_destino=fuente["TablaDestino"],
        url_base=fuente["UrlBase"],
        endpoint=fuente["Endpoint"],
        api_key=secreto(fuente["VariableApiKey"]),
        columnas=fuente["Columnas"],
        tamano_pagina=int(fuente.get("TamanoPagina", 50)),
        max_concurrencia=int(fuente.get("MaxConcurrencia", 4)),
        timeout_segundos=float(fuente.get("TimeoutSegundos", 10)),
        reintentos=int(fuente.get("Reintentos", 3)),
        logger=ctx.logger.getChild(fuente["Nombre"]),
    )


FABRICAS: dict[str, Callable[[dict, Contexto], IExtractorAsync]] = {
    "BD": _crear_bd,
    "CSV": _crear_csv,
    "API": _crear_api,
}


def crear_motor(conexion: dict, inserciones_masivas: bool = False) -> Engine:
    return create_engine(
        crear_url_sql_server(conexion),
        fast_executemany=inserciones_masivas,  # inserta miles de filas por viaje a SQL Server
        pool_pre_ping=True,                    # descarta conexiones caídas antes de usarlas
    )


def crear_extractores(config: Configuracion, logger: logging.Logger,
                      motor_origen: Callable[[], Engine]) -> list[IExtractorAsync]:
    ctx = Contexto(config, logger, motor_origen)
    extractores = []
    for fuente in config.fuentes_activas:
        tipo = fuente.get("Tipo")
        if tipo not in FABRICAS:
            raise ErrorConfiguracion(
                f"Tipo de fuente desconocido '{tipo}' en {fuente.get('Nombre')}. "
                f"Tipos válidos: {', '.join(FABRICAS)}"
            )
        try:
            extractores.append(FABRICAS[tipo](fuente, ctx))
        except KeyError as error:
            raise ErrorConfiguracion(
                f"A la fuente {fuente.get('Nombre')} le falta la clave {error}"
            ) from error
    return extractores


def crear_servicio(config: Configuracion, logger: logging.Logger) -> tuple[ExtractionService, list[Engine]]:
    """Devuelve el servicio listo para usar y los motores creados (para cerrarlos al final)."""
    motores: list[Engine] = []
    cache: dict[str, Engine] = {}

    def motor_origen() -> Engine:
        if "origen" not in cache:
            cache["origen"] = crear_motor(config.conexion("Origen"))
            motores.append(cache["origen"])
        return cache["origen"]

    motor_destino = crear_motor(config.conexion("Destino"), inserciones_masivas=True)
    motores.append(motor_destino)

    extractores = crear_extractores(config, logger, motor_origen)
    servicio = ExtractionService(
        extractores=extractores,
        escritor=SqlServerStagingWriter(motor_destino, config.tamano_lote),
        bitacora=SqlServerRunLogRepository(motor_destino),
        logger=logger.getChild("servicio"),
    )
    return servicio, motores


def crear_opciones_dimensiones(config: Configuracion) -> OpcionesDimensiones:
    """Lee la sección "Dimensiones" de appsettings.json (con valores por defecto razonables)."""
    datos = config.dimensiones
    rango = datos.get("Fecha", {})
    try:
        inicio = date.fromisoformat(rango.get("Inicio", "2024-01-01"))
        fin = date.fromisoformat(rango.get("Fin", "2025-12-31"))
    except ValueError as error:
        raise ErrorConfiguracion(
            f"Dimensiones.Fecha: use fechas AAAA-MM-DD en 'Inicio' y 'Fin' ({error})") from error
    if fin < inicio:
        raise ErrorConfiguracion("Dimensiones.Fecha: 'Fin' no puede ser anterior a 'Inicio'")
    return OpcionesDimensiones(inicio, fin, bool(datos.get("MiembroDesconocido", True)))


def crear_servicio_dimensiones(config: Configuracion,
                               logger: logging.Logger) -> tuple[DimensionLoadService, list[Engine]]:
    """Devuelve el servicio de carga de dimensiones y los motores creados (para cerrarlos al final)."""
    opciones = crear_opciones_dimensiones(config)
    motor_destino = crear_motor(config.conexion("Destino"))
    servicio = DimensionLoadService(
        lector=SqlServerStagingReader(motor_destino),
        cargador=SqlServerDimensionLoader(motor_destino),
        bitacora=SqlServerDimensionLogRepository(motor_destino),
        opciones=opciones,
        logger=logger.getChild("dimensiones"),
    )
    return servicio, [motor_destino]
