from datetime import date

import pytest

from infrastructure.dimension_loader import SqlServerDimensionLoader, construir_parametro_tabla


class CursorFalso:
    def __init__(self, resultado, error=None):
        self.resultado, self.error, self.ejecutado = resultado, error, None

    def execute(self, sentencia, parametros):
        if self.error:
            raise self.error
        self.ejecutado = (sentencia, parametros)

    def fetchone(self):
        return self.resultado


class ConexionFalsa:
    def __init__(self, cursor):
        self._cursor, self.confirmada, self.revertida, self.cerrada = cursor, False, False, False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.confirmada = True

    def rollback(self):
        self.revertida = True

    def close(self):
        self.cerrada = True


class MotorFalso:
    def __init__(self, conexion):
        self.conexion = conexion

    def raw_connection(self):
        return self.conexion


def test_parametro_tabla_lleva_nombre_esquema_y_filas():
    filas = [(1, "Positiva"), (2, "Negativa")]
    assert construir_parametro_tabla("etl.T_Dim_Clasificacion", filas) == \
        ["T_Dim_Clasificacion", "etl", (1, "Positiva"), (2, "Negativa")]


def test_parametro_tabla_valida_el_nombre_del_tipo():
    with pytest.raises(ValueError):
        construir_parametro_tabla("etl.T_Dim; DROP TABLE x", [(1,)])


def test_cargar_ejecuta_el_procedimiento_y_confirma():
    conexion = ConexionFalsa(CursorFalso((3, 2, 1, 0)))
    cargador = SqlServerDimensionLoader(MotorFalso(conexion))
    filas = [(20250101, date(2025, 1, 1), 1, 1, 1, 2025)]

    conteos = cargador.cargar("etl.T_Dim_Fecha", "etl.usp_Cargar_Dim_Fecha", filas)

    sentencia, parametros = conexion._cursor.ejecutado
    assert sentencia == "EXEC [etl].[usp_Cargar_Dim_Fecha] @Datos = ?"
    assert parametros == (["T_Dim_Fecha", "etl", filas[0]],)
    assert (conteos.enviadas, conteos.insertadas, conteos.actualizadas, conteos.sin_cambios) == (3, 2, 1, 0)
    assert conexion.confirmada and not conexion.revertida and conexion.cerrada


def test_cargar_revierte_y_cierra_si_falla():
    conexion = ConexionFalsa(CursorFalso(None, error=RuntimeError("falló")))
    cargador = SqlServerDimensionLoader(MotorFalso(conexion))

    with pytest.raises(RuntimeError):
        cargador.cargar("etl.T_Dim_Fuente", "etl.usp_Cargar_Dim_Fuente", [(1, "Web")])

    assert conexion.revertida and not conexion.confirmada and conexion.cerrada


def test_cargar_no_acepta_lote_vacio():
    cargador = SqlServerDimensionLoader(MotorFalso(ConexionFalsa(CursorFalso(None))))
    with pytest.raises(ValueError):
        cargador.cargar("etl.T_Dim_Fuente", "etl.usp_Cargar_Dim_Fuente", [])


def test_cargar_valida_el_nombre_del_procedimiento():
    cargador = SqlServerDimensionLoader(MotorFalso(ConexionFalsa(CursorFalso((1, 1, 0, 0)))))
    with pytest.raises(ValueError):
        cargador.cargar("etl.T_Dim_Fuente", "etl.usp_X; DROP TABLE y", [(1, "Web")])
