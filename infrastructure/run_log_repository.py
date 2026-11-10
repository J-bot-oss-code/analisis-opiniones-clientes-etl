"""Bitácora de ejecuciones en las tablas etl.EjecucionExtraccion y etl.DetalleExtraccion."""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from application.interfaces import IRunLogRepository

LARGO_MAXIMO_MENSAJE = 4000  # NVARCHAR(4000) en el contrato de tablas


def _recortar(mensaje: str | None) -> str | None:
    if mensaje is None:
        return None
    return mensaje if len(mensaje) <= LARGO_MAXIMO_MENSAJE else mensaje[:LARGO_MAXIMO_MENSAJE - 3] + "..."


class SqlServerRunLogRepository(IRunLogRepository):
    def __init__(self, engine: Engine):
        self.engine = engine

    def iniciar(self, fecha_inicio: datetime) -> int:
        with self.engine.begin() as conexion:
            return conexion.execute(
                text(
                    "INSERT INTO etl.EjecucionExtraccion (FechaInicio, Estado) "
                    "OUTPUT INSERTED.IdEjecucion "
                    "VALUES (:inicio, 'EnCurso')"
                ),
                {"inicio": fecha_inicio},
            ).scalar_one()

    def registrar_detalle(self, id_ejecucion, fuente, tabla_destino, filas,
                          duracion_segundos, estado, mensaje):
        with self.engine.begin() as conexion:
            conexion.execute(
                text(
                    "INSERT INTO etl.DetalleExtraccion "
                    "(IdEjecucion, Fuente, TablaDestino, Filas, DuracionSegundos, Estado, Mensaje) "
                    "VALUES (:id, :fuente, :tabla, :filas, :duracion, :estado, :mensaje)"
                ),
                {
                    "id": id_ejecucion,
                    "fuente": fuente,
                    "tabla": tabla_destino,
                    "filas": filas,
                    "duracion": round(duracion_segundos, 3),
                    "estado": estado,
                    "mensaje": _recortar(mensaje),
                },
            )

    def finalizar(self, id_ejecucion, fecha_fin, estado, filas_totales,
                  duracion_segundos, mensaje):
        with self.engine.begin() as conexion:
            conexion.execute(
                text(
                    "UPDATE etl.EjecucionExtraccion "
                    "SET FechaFin = :fin, Estado = :estado, FilasTotales = :filas, "
                    "DuracionSegundos = :duracion, Mensaje = :mensaje "
                    "WHERE IdEjecucion = :id"
                ),
                {
                    "id": id_ejecucion,
                    "fin": fecha_fin,
                    "estado": estado,
                    "filas": filas_totales,
                    "duracion": round(duracion_segundos, 3),
                    "mensaje": _recortar(mensaje),
                },
            )
