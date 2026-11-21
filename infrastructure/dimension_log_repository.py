"""Bitácora de la carga en las tablas etl.EjecucionCarga y etl.DetalleCargaDimension."""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from application.interfaces import ConteosCarga, IDimensionLogRepository
from infrastructure.run_log_repository import _recortar


class SqlServerDimensionLogRepository(IDimensionLogRepository):
    def __init__(self, engine: Engine):
        self.engine = engine

    def iniciar(self, fecha_inicio: datetime, id_ejecucion_extraccion: int | None) -> int:
        with self.engine.begin() as conexion:
            return conexion.execute(
                text(
                    "INSERT INTO etl.EjecucionCarga (FechaInicio, Estado, IdEjecucionExtraccion) "
                    "OUTPUT INSERTED.IdEjecucionCarga "
                    "VALUES (:inicio, 'EnCurso', :extraccion)"
                ),
                {"inicio": fecha_inicio, "extraccion": id_ejecucion_extraccion},
            ).scalar_one()

    def registrar_detalle(self, id_ejecucion_carga: int, dimension: str, tabla_destino: str,
                          leidas: int, rechazadas: int, enviadas: int,
                          conteos: ConteosCarga | None, duracion_segundos: float,
                          estado: str, mensaje: str | None) -> None:
        with self.engine.begin() as conexion:
            conexion.execute(
                text(
                    "INSERT INTO etl.DetalleCargaDimension "
                    "(IdEjecucionCarga, Dimension, TablaDestino, Leidas, Rechazadas, Enviadas, "
                    " Insertadas, Actualizadas, SinCambios, DuracionSegundos, Estado, Mensaje) "
                    "VALUES (:id, :dimension, :tabla, :leidas, :rechazadas, :enviadas, "
                    " :insertadas, :actualizadas, :sin_cambios, :duracion, :estado, :mensaje)"
                ),
                {
                    "id": id_ejecucion_carga,
                    "dimension": dimension,
                    "tabla": tabla_destino,
                    "leidas": leidas,
                    "rechazadas": rechazadas,
                    "enviadas": enviadas,
                    "insertadas": conteos.insertadas if conteos else 0,
                    "actualizadas": conteos.actualizadas if conteos else 0,
                    "sin_cambios": conteos.sin_cambios if conteos else 0,
                    "duracion": round(duracion_segundos, 3),
                    "estado": estado,
                    "mensaje": _recortar(mensaje),
                },
            )

    def finalizar(self, id_ejecucion_carga: int, fecha_fin: datetime, estado: str,
                  duracion_segundos: float, mensaje: str | None) -> None:
        with self.engine.begin() as conexion:
            conexion.execute(
                text(
                    "UPDATE etl.EjecucionCarga "
                    "SET FechaFin = :fin, Estado = :estado, DuracionSegundos = :duracion, Mensaje = :mensaje "
                    "WHERE IdEjecucionCarga = :id"
                ),
                {
                    "id": id_ejecucion_carga,
                    "fin": fecha_fin,
                    "estado": estado,
                    "duracion": round(duracion_segundos, 3),
                    "mensaje": _recortar(mensaje),
                },
            )
