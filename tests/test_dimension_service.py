from datetime import date, datetime

import pandas as pd
import pytest

from application.dimension_preparation import OpcionesDimensiones
from application.dimension_service import DimensionLoadService
from application.extraction_service import ErrorDestino
from application.interfaces import (ConteosCarga, IDimensionLoader, IDimensionLogRepository,
                                    IStagingReader)

OPCIONES = OpcionesDimensiones(date(2025, 1, 1), date(2025, 1, 3))


class LectorFalso(IStagingReader):
    def __init__(self, tablas=None, faltantes=()):
        self.tablas = tablas if tablas is not None else {
            "stg.Clasificacion": pd.DataFrame({"IdClasificacion": [1, 2], "Nombre": ["Positiva", "Negativa"]}),
            "stg.FuenteDatos": pd.DataFrame({"IdFuente": [1], "TipoFuente": ["Web"]}),
            "stg.Categoria": pd.DataFrame({"IdCategoria": [1], "Nombre": ["Hogar"]}),
            "stg.Producto": pd.DataFrame({"IdProducto": [1], "Nombre": ["P1"], "IdCategoria": [1]}),
            "stg.Cliente": pd.DataFrame({"IdCliente": [1, 2], "Nombre": ["Ana", "Luis"], "Email": [None, "l@m.n"]}),
        }
        self.faltantes = list(faltantes)

    def leer(self, tabla):
        return self.tablas[tabla]

    def ultima_ejecucion(self, tablas):
        return 7

    def tablas_faltantes(self, tablas):
        return [t for t in tablas if t in self.faltantes]


class CargadorFalso(IDimensionLoader):
    def __init__(self, falla_en=None, procedimientos_faltantes=()):
        self.llamadas, self.falla_en = [], falla_en
        self._faltan = list(procedimientos_faltantes)

    def cargar(self, tipo_sql, procedimiento, filas):
        if procedimiento == self.falla_en:
            raise RuntimeError("deadlock")
        self.llamadas.append((tipo_sql, procedimiento, len(filas)))
        return ConteosCarga(enviadas=len(filas), insertadas=len(filas), actualizadas=0, sin_cambios=0)

    def procedimientos_faltantes(self, procedimientos):
        return [p for p in procedimientos if p in self._faltan]


class BitacoraFalsa(IDimensionLogRepository):
    def __init__(self):
        self.iniciada, self.detalles, self.final = None, [], None

    def iniciar(self, fecha_inicio, id_ejecucion_extraccion):
        self.iniciada = id_ejecucion_extraccion
        return 5

    def registrar_detalle(self, id_ejecucion_carga, dimension, tabla_destino, leidas, rechazadas,
                          enviadas, conteos, duracion_segundos, estado, mensaje):
        self.detalles.append((dimension, leidas, rechazadas, enviadas, estado, mensaje))

    def finalizar(self, id_ejecucion_carga, fecha_fin, estado, duracion_segundos, mensaje):
        self.final = (estado, mensaje)


def crear(lector=None, cargador=None):
    bitacora = BitacoraFalsa()
    return DimensionLoadService(lector or LectorFalso(), cargador or CargadorFalso(), bitacora, OPCIONES), bitacora


def test_carga_las_cinco_dimensiones_en_orden():
    cargador = CargadorFalso()
    servicio, bitacora = crear(cargador=cargador)

    resumen = servicio.ejecutar()

    assert resumen.estado == "Exitosa"
    assert [r.nombre for r in resumen.resultados] == ["Clasificacion", "Fuente", "Fecha", "Producto", "Cliente"]
    assert [c[1] for c in cargador.llamadas] == [
        "etl.usp_Cargar_Dim_Clasificacion", "etl.usp_Cargar_Dim_Fuente", "etl.usp_Cargar_Dim_Fecha",
        "etl.usp_Cargar_Dim_Producto", "etl.usp_Cargar_Dim_Cliente"]
    # Fuente, Producto y Cliente reciben además la fila "Desconocido"; Fecha genera 3 días.
    assert [c[2] for c in cargador.llamadas] == [2, 2, 3, 2, 3]
    assert bitacora.iniciada == 7 and bitacora.final == ("Exitosa", None)
    assert len(bitacora.detalles) == 5


def test_una_dimension_que_falla_no_detiene_a_las_demas():
    servicio, bitacora = crear(cargador=CargadorFalso(falla_en="etl.usp_Cargar_Dim_Producto"))

    resumen = servicio.ejecutar()

    assert resumen.estado == "Parcial"
    por_nombre = {r.nombre: r for r in resumen.resultados}
    assert por_nombre["Producto"].estado == "Fallida" and "deadlock" in por_nombre["Producto"].mensaje
    assert por_nombre["Cliente"].estado == "Exitosa"
    assert bitacora.final[0] == "Parcial" and "Producto" in bitacora.final[1]


def test_staging_vacio_es_un_error_claro_y_no_llama_al_procedimiento():
    lector = LectorFalso()
    lector.tablas["stg.Cliente"] = pd.DataFrame({"IdCliente": [], "Nombre": [], "Email": []})
    cargador = CargadorFalso()
    servicio, _ = crear(lector, cargador)

    resumen = servicio.ejecutar(["Cliente"])

    assert resumen.estado == "Fallida"
    assert "stg.Cliente está vacía" in resumen.resultados[0].mensaje
    assert cargador.llamadas == []


def test_se_puede_elegir_una_dimension():
    cargador = CargadorFalso()
    servicio, _ = crear(cargador=cargador)
    resumen = servicio.ejecutar(["Fecha"])
    assert [r.nombre for r in resumen.resultados] == ["Fecha"]
    assert len(cargador.llamadas) == 1


def test_dimension_desconocida_se_rechaza():
    servicio, _ = crear()
    with pytest.raises(ValueError, match="Dimensión desconocida"):
        servicio.ejecutar(["Inventada"])


def test_verificar_destino_lista_lo_que_falta():
    servicio, _ = crear(LectorFalso(faltantes=["stg.Cliente"]),
                        CargadorFalso(procedimientos_faltantes=["etl.usp_Cargar_Dim_Fecha"]))
    with pytest.raises(ErrorDestino) as error:
        servicio.verificar_destino()
    assert "stg.Cliente" in str(error.value) and "usp_Cargar_Dim_Fecha" in str(error.value)


def test_verificar_destino_correcto_no_falla():
    servicio, _ = crear()
    servicio.verificar_destino()


def test_resultados_cuadran_leidas_rechazadas_enviadas():
    servicio, _ = crear()
    for r in servicio.ejecutar().resultados:
        c = r.conteos
        assert c.insertadas + c.actualizadas + c.sin_cambios == r.enviadas
