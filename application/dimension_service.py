"""Servicio que orquesta la carga (L) de las dimensiones hacia el Data Warehouse.

Por cada dimensión: lee su staging, prepara las filas, las envía al procedimiento almacenado
mediante un tipo de tabla y anota el resultado en la bitácora.  Una dimensión que falla no
detiene a las demás.  Solo depende de interfaces (igual que ExtractionService).
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

import pandas as pd

from application.dimension_preparation import (OpcionesDimensiones, Preparacion, generar_fecha,
                                               preparar_clasificacion, preparar_cliente,
                                               preparar_fuente, preparar_producto)
from application.extraction_service import ErrorDestino
from application.interfaces import (ConteosCarga, IDimensionLoader, IDimensionLogRepository,
                                    IStagingReader)

TABLAS_BITACORA = ["etl.EjecucionCarga", "etl.DetalleCargaDimension"]


class ErrorStagingVacio(Exception):
    """La tabla staging que alimenta la dimensión no tiene filas."""


@dataclass(frozen=True)
class DefinicionDimension:
    nombre: str
    tabla_destino: str                       # tabla del Data Warehouse, p. ej. dbo.Dim_Cliente
    tipo_sql: str                            # tipo de tabla (script 07)
    procedimiento: str                       # procedimiento almacenado (script 08)
    tablas_staging: tuple[str, ...]          # vacío si la dimensión no sale de staging (Fecha)
    preparar: Callable[[dict[str, pd.DataFrame], Any], Preparacion]   # opciones: OpcionesDimensiones u OpcionesHechos


# Orden de carga. Entre estas dimensiones no hay claves foráneas, así que el orden no afecta
# la integridad; se cargan primero las más pequeñas. (Las tablas de hechos, que sí dependen de todas,
# se cargarán DESPUÉS de las dimensiones en la siguiente etapa.)
DIMENSIONES: dict[str, DefinicionDimension] = {d.nombre: d for d in [
    DefinicionDimension(
        "Clasificacion", "dbo.Dim_Clasificacion", "etl.T_Dim_Clasificacion",
        "etl.usp_Cargar_Dim_Clasificacion", ("stg.Clasificacion",),
        lambda t, o: preparar_clasificacion(t["stg.Clasificacion"], o)),
    DefinicionDimension(
        "Fuente", "dbo.Dim_Fuente", "etl.T_Dim_Fuente",
        "etl.usp_Cargar_Dim_Fuente", ("stg.FuenteDatos",),
        lambda t, o: preparar_fuente(t["stg.FuenteDatos"], o)),
    DefinicionDimension(
        "Fecha", "dbo.Dim_Fecha", "etl.T_Dim_Fecha",
        "etl.usp_Cargar_Dim_Fecha", (),
        lambda t, o: generar_fecha(o)),
    DefinicionDimension(
        "Producto", "dbo.Dim_Producto", "etl.T_Dim_Producto",
        "etl.usp_Cargar_Dim_Producto", ("stg.Producto", "stg.Categoria"),
        lambda t, o: preparar_producto(t["stg.Producto"], t["stg.Categoria"], o)),
    DefinicionDimension(
        "Cliente", "dbo.Dim_Cliente", "etl.T_Dim_Cliente",
        "etl.usp_Cargar_Dim_Cliente", ("stg.Cliente",),
        lambda t, o: preparar_cliente(t["stg.Cliente"], o)),
]}


@dataclass
class ResultadoDimension:
    nombre: str
    tabla_destino: str
    leidas: int
    rechazadas: int
    enviadas: int
    conteos: Optional[ConteosCarga]
    duracion_segundos: float
    estado: str                 # "Exitosa" o "Fallida"
    mensaje: Optional[str] = None


@dataclass
class ResumenCarga:
    id_ejecucion: int
    estado: str                 # "Exitosa", "Parcial" o "Fallida"
    duracion_segundos: float
    resultados: list[ResultadoDimension] = field(default_factory=list)


class DimensionLoadService:
    """Orquesta la carga de un conjunto de tablas destino.  Por defecto son las dimensiones; con otro
    `registro` (p. ej. HECHOS en fact_service.py) carga las tablas de hechos con el mismo flujo."""

    def __init__(self, lector: IStagingReader, cargador: IDimensionLoader,
                 bitacora: IDimensionLogRepository, opciones: Any,
                 logger: logging.Logger | None = None,
                 reloj: Callable[[], datetime] = datetime.now,
                 registro: dict[str, DefinicionDimension] | None = None,
                 scripts: str = "07 al 10", etiqueta: str = "dimensiones",
                 tamano_lote: int | None = None):
        self.lector = lector
        self.cargador = cargador
        self.bitacora = bitacora
        self.opciones = opciones
        self.logger = logger or logging.getLogger("extraccion.dimensiones")
        self.reloj = reloj
        self.registro = registro if registro is not None else DIMENSIONES
        self.scripts = scripts                # scripts SQL que crean lo necesario (para el mensaje de error)
        self.etiqueta = etiqueta              # "dimensiones" o "hechos" (para los mensajes)
        self.tamano_lote = tamano_lote        # filas por llamada al procedimiento (None = todas juntas)

    def _seleccionar(self, nombres: list[str] | None) -> list[DefinicionDimension]:
        if not nombres:
            return list(self.registro.values())
        desconocidas = [n for n in nombres if n not in self.registro]
        if desconocidas:
            raise ValueError("Nombre desconocido: " + ", ".join(desconocidas)
                             + f". Válidos: {', '.join(self.registro)}")
        return [d for d in self.registro.values() if d.nombre in nombres]  # siempre en orden de carga

    def verificar_destino(self, nombres: list[str] | None = None) -> None:
        """Comprueba al arrancar que existan las tablas, tipos y procedimientos necesarios."""
        definiciones = self._seleccionar(nombres)
        # No se comprueban las tablas dbo.Dim_*: el usuario del worker no tiene permisos sobre ellas
        # (mínimo privilegio), así que SQL Server no se las muestra. Si faltaran, el procedimiento
        # de carga ni siquiera se habría podido crear en el script 08.
        tablas = sorted({t for d in definiciones for t in d.tablas_staging}) + TABLAS_BITACORA
        faltantes = self.lector.tablas_faltantes(tablas)
        faltantes += self.cargador.procedimientos_faltantes(sorted({d.procedimiento for d in definiciones}))
        if faltantes:
            raise ErrorDestino(
                "Faltan objetos en el Data Warehouse: " + ", ".join(faltantes)
                + f". Ejecute los scripts de la carpeta sql/ ({self.scripts})."
            )
        self.logger.info("Destino verificado: %d tablas y %d procedimientos encontrados",
                         len(tablas), len(definiciones))

    def ejecutar(self, nombres: list[str] | None = None) -> ResumenCarga:
        definiciones = self._seleccionar(nombres)
        inicio = self.reloj()
        cronometro = time.perf_counter()
        tablas_staging = sorted({t for d in definiciones for t in d.tablas_staging})
        id_extraccion = self.lector.ultima_ejecucion(tablas_staging) if tablas_staging else None
        id_carga = self.bitacora.iniciar(inicio, id_extraccion)
        self.logger.info("Carga %d iniciada: %d %s (datos de la extracción %s)",
                         id_carga, len(definiciones), self.etiqueta, id_extraccion if id_extraccion else "-")

        resultados = [self._procesar(definicion, id_carga) for definicion in definiciones]

        duracion = time.perf_counter() - cronometro
        fallidas = [r for r in resultados if r.estado == "Fallida"]
        if not fallidas:
            estado = "Exitosa"
        elif len(fallidas) == len(resultados):
            estado = "Fallida"
        else:
            estado = "Parcial"
        mensaje = "; ".join(f"{r.nombre}: {r.mensaje}" for r in fallidas) or None
        self.bitacora.finalizar(id_carga, self.reloj(), estado, duracion, mensaje)
        nivel = logging.INFO if estado == "Exitosa" else logging.WARNING
        self.logger.log(nivel, "Carga %d %s en %.2f s (%d de %d %s con error)",
                        id_carga, estado.lower(), duracion, len(fallidas), len(resultados), self.etiqueta)
        return ResumenCarga(id_carga, estado, duracion, resultados)

    def _enviar(self, definicion: DefinicionDimension, filas: list[tuple]) -> ConteosCarga:
        """Envía las filas al procedimiento, en lotes de `tamano_lote`, y suma los conteos de cada lote.
        Cada lote es una transacción propia; como la carga es idempotente, repetirla completa lo que falte."""
        tamano = self.tamano_lote or len(filas)
        total = ConteosCarga(0, 0, 0, 0)
        for desde in range(0, len(filas), tamano):
            parcial = self.cargador.cargar(definicion.tipo_sql, definicion.procedimiento, filas[desde:desde + tamano])
            total = ConteosCarga(total.enviadas + parcial.enviadas, total.insertadas + parcial.insertadas,
                                 total.actualizadas + parcial.actualizadas, total.sin_cambios + parcial.sin_cambios)
        return total

    def _procesar(self, definicion: DefinicionDimension, id_carga: int) -> ResultadoDimension:
        cronometro = time.perf_counter()
        leidas = rechazadas = enviadas = 0
        conteos, estado, mensaje = None, "Exitosa", None
        try:
            datos = {t: self.lector.leer(t) for t in definicion.tablas_staging}
            for tabla, df in datos.items():
                if df.empty:
                    raise ErrorStagingVacio(f"{tabla} está vacía: ejecute primero la extracción (worker.py --una-vez)")
            preparacion = definicion.preparar(datos, self.opciones)
            leidas, rechazadas, enviadas = preparacion.leidas, preparacion.rechazadas, len(preparacion.filas)
            if not preparacion.filas:
                raise ValueError("no quedó ninguna fila válida para cargar")
            conteos = self._enviar(definicion, preparacion.filas)
            mensaje = "; ".join(preparacion.avisos) or None
            self.logger.info(
                "%s: %d leídas, %d rechazadas -> %d insertadas, %d actualizadas, %d sin cambios (%.2f s)",
                definicion.nombre, leidas, rechazadas, conteos.insertadas, conteos.actualizadas,
                conteos.sin_cambios, time.perf_counter() - cronometro)
            for aviso in preparacion.avisos:
                self.logger.warning("%s: %s", definicion.nombre, aviso)
        except Exception as error:  # una dimensión que falla no detiene a las demás
            estado, mensaje, conteos = "Fallida", f"{type(error).__name__}: {error}", None
            self.logger.error("%s falló: %s", definicion.nombre, mensaje.splitlines()[0])
            self.logger.debug("Detalle de %s", definicion.nombre, exc_info=True)

        duracion = time.perf_counter() - cronometro
        resultado = ResultadoDimension(definicion.nombre, definicion.tabla_destino, leidas, rechazadas,
                                       enviadas, conteos, duracion, estado, mensaje)
        try:
            self.bitacora.registrar_detalle(id_carga, definicion.nombre, definicion.tabla_destino, leidas,
                                            rechazadas, enviadas, conteos, duracion, estado, mensaje)
        except Exception:
            self.logger.exception("No se pudo registrar el detalle de %s en la bitácora", definicion.nombre)
        return resultado
