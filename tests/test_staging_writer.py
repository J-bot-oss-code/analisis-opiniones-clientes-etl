from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from infrastructure.staging_writer import preparar_para_sql, separar_tabla


def test_separa_esquema_y_tabla():
    assert separar_tabla("stg.Opinion") == ("stg", "Opinion")


@pytest.mark.parametrize("malo", ["Opinion", "stg.Opinion; DROP TABLE x", "stg.[Opinion]", "a.b.c"])
def test_rechaza_nombres_peligrosos(malo):
    with pytest.raises(ValueError):
        separar_tabla(malo)


def test_agrega_auditoria_y_convierte_nulos():
    fecha = datetime(2026, 11, 10, 13, 0)
    datos = pd.DataFrame({"IdCliente": [1, np.nan], "Fecha": [pd.Timestamp("2025-01-01"), pd.NaT]})

    preparado = preparar_para_sql(datos, 7, fecha)

    assert list(preparado.columns) == ["IdCliente", "Fecha", "IdEjecucion", "FechaExtraccion"]
    assert preparado.loc[1, "IdCliente"] is None
    assert preparado.loc[1, "Fecha"] is None
    assert (preparado["IdEjecucion"] == 7).all()


def test_escribe_reemplazando_lo_anterior():
    """Prueba de integración con SQLite (que no tiene TRUNCATE, por eso se usa DELETE)."""
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.pool import StaticPool

    from infrastructure.staging_writer import SqlServerStagingWriter

    class EscritorSqlite(SqlServerStagingWriter):
        SENTENCIA_VACIAR = "DELETE FROM [{esquema}].[{tabla}]"

    motor = create_engine("sqlite://", poolclass=StaticPool,
                          connect_args={"check_same_thread": False})

    @event.listens_for(motor, "connect")
    def adjuntar_esquema(conexion, _):
        conexion.execute("ATTACH DATABASE ':memory:' AS stg")

    with motor.begin() as conexion:
        conexion.execute(text("CREATE TABLE stg.Cliente (IdCliente INT, Nombre TEXT, "
                              "IdEjecucion INT NOT NULL, FechaExtraccion TIMESTAMP NOT NULL)"))

    escritor = EscritorSqlite(motor, tamano_lote=2)
    fecha = datetime(2026, 11, 10, 13, 0)
    escritor.escribir("stg.Cliente", pd.DataFrame({"IdCliente": [1, 2, 3], "Nombre": ["a", None, "c"]}), 1, fecha)
    filas = escritor.escribir("stg.Cliente", pd.DataFrame({"IdCliente": [9], "Nombre": ["z"]}), 2, fecha)

    with motor.connect() as conexion:
        contenido = conexion.execute(text("SELECT IdCliente, Nombre, IdEjecucion FROM stg.Cliente")).all()
    assert filas == 1
    assert contenido == [(9, "z", 2)]               # la segunda corrida reemplazó a la primera
    assert escritor.tablas_faltantes(["stg.Cliente", "stg.NoExiste"]) == ["stg.NoExiste"]


def test_reintenta_si_sql_server_reporta_interbloqueo():
    from sqlalchemy.exc import DBAPIError

    from infrastructure.staging_writer import SqlServerStagingWriter

    class Conexion:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, *args):
            pass

    class MotorFalso:
        intentos = 0

        def begin(self):
            MotorFalso.intentos += 1
            if MotorFalso.intentos == 1:
                raise DBAPIError("x", {}, Exception("[40001] deadlocked ... (1205)"))
            return Conexion()

    escritor = SqlServerStagingWriter(MotorFalso(), reintentos=2)
    filas = escritor.escribir("stg.Cliente", pd.DataFrame({"IdCliente": [1, 2]}), 1, datetime.now())

    assert filas == 2
    assert MotorFalso.intentos == 2
