from datetime import date

import pandas as pd
import pytest

from application.dimension_preparation import OpcionesDimensiones
from application.dimension_service import DimensionLoadService
from application.extraction_service import ErrorDestino
from application.fact_preparation import OpcionesHechos
from application.fact_service import HECHOS
from application.interfaces import (ConteosCarga, IDimensionLoader, IDimensionLogRepository,
                                    IStagingReader)

OPCIONES = OpcionesHechos(OpcionesDimensiones(date(2025, 1, 1), date(2025, 12, 31)), tamano_lote=2)

TABLAS = {
    "stg.Opinion": pd.DataFrame({
        "IdOpinion": [1, 2, 3], "IdCliente": [1, 1, 2], "IdProducto": [1, 1, 1], "IdClasificacion": [1, 2, 3],
        "IdFuente": [2, 2, 5], "Fecha": [date(2025, 3, 1)] * 3, "Comentario": ["a", "b", "c"],
        "PuntajeSatisfaccion": [4.0, 2.0, 3.0]}),
    "stg.EncuestaCSV": pd.DataFrame({
        "IdOpinion": ["1", "2"], "IdCliente": ["2", "2"], "IdProducto": ["1", "1"], "Fecha": ["2025-04-01"] * 2,
        "Comentario": ["d", "e"], "Clasificacion": ["Positiva", "Negativa"], "PuntajeSatisfaccion": ["5", "1"],
        "Fuente": ["EncuestaInterna"] * 2}),
    "stg.ResenaWeb": pd.DataFrame({
        "IdReview": ["W1", "W2"], "IdCliente": ["C001", "C002"], "IdProducto": ["P001", "P001"],
        "Fecha": ["2025-05-01"] * 2, "Comentario": ["x", "y"], "Rating": ["5", "1"]}),
    "stg.Cliente": pd.DataFrame({"IdCliente": [1, 2], "Nombre": ["Ana", "Luis"], "Email": [None, None]}),
    "stg.Categoria": pd.DataFrame({"IdCategoria": [1], "Nombre": ["Hogar"]}),
    "stg.Producto": pd.DataFrame({"IdProducto": [1], "Nombre": ["P1"], "IdCategoria": [1]}),
    "stg.FuenteDatos": pd.DataFrame({"IdFuente": [1, 2, 5], "TipoFuente": ["Web", "CSV", "Red Social"]}),
    "stg.Clasificacion": pd.DataFrame({"IdClasificacion": [1, 2, 3], "Nombre": ["Positiva", "Negativa", "Neutra"]}),
}


class Lector(IStagingReader):
    def __init__(self, tablas=None, faltantes=()):
        self.tablas, self.faltantes = dict(tablas or TABLAS), list(faltantes)

    def leer(self, tabla):
        return self.tablas[tabla]

    def ultima_ejecucion(self, tablas):
        return 9

    def tablas_faltantes(self, tablas):
        return [t for t in tablas if t in self.faltantes]


class Cargador(IDimensionLoader):
    def __init__(self, ya_existian=0, procedimientos_faltantes=()):
        self.llamadas, self.ya_existian, self._faltan = [], ya_existian, list(procedimientos_faltantes)

    def cargar(self, tipo_sql, procedimiento, filas):
        self.llamadas.append((tipo_sql, procedimiento, len(filas)))
        nuevas = max(len(filas) - self.ya_existian, 0)
        return ConteosCarga(enviadas=len(filas), insertadas=nuevas, actualizadas=0, sin_cambios=len(filas) - nuevas)

    def procedimientos_faltantes(self, procedimientos):
        return [p for p in procedimientos if p in self._faltan]


class Bitacora(IDimensionLogRepository):
    def __init__(self):
        self.detalles, self.final = [], None

    def iniciar(self, fecha_inicio, id_ejecucion_extraccion):
        return 1

    def registrar_detalle(self, id_ejecucion_carga, dimension, tabla_destino, leidas, rechazadas, enviadas,
                          conteos, duracion_segundos, estado, mensaje):
        self.detalles.append((dimension, tabla_destino, leidas, rechazadas, enviadas, estado))

    def finalizar(self, id_ejecucion_carga, fecha_fin, estado, duracion_segundos, mensaje):
        self.final = estado


def crear(lector=None, cargador=None, tamano_lote=2):
    bitacora = Bitacora()
    servicio = DimensionLoadService(lector or Lector(), cargador or Cargador(), bitacora, OPCIONES,
                                    registro=HECHOS, scripts="14 al 18", etiqueta="hechos", tamano_lote=tamano_lote)
    return servicio, bitacora


def test_carga_los_dos_hechos_en_lotes_y_suma_los_conteos():
    cargador = Cargador()
    servicio, bitacora = crear(cargador=cargador)

    resumen = servicio.ejecutar()

    assert resumen.estado == "Exitosa" and bitacora.final == "Exitosa"
    assert [r.nombre for r in resumen.resultados] == ["Fact_Opiniones", "Fact_Resenas"]
    # 5 opiniones (3 BD + 2 encuesta) en lotes de 2 -> 3 llamadas; 2 reseñas -> 1 llamada
    assert cargador.llamadas == [("etl.T_Fact_Opiniones", "etl.usp_Cargar_Fact_Opiniones", 2),
                                 ("etl.T_Fact_Opiniones", "etl.usp_Cargar_Fact_Opiniones", 2),
                                 ("etl.T_Fact_Opiniones", "etl.usp_Cargar_Fact_Opiniones", 1),
                                 ("etl.T_Fact_Resenas", "etl.usp_Cargar_Fact_Resenas", 2)]
    opiniones = resumen.resultados[0]
    assert (opiniones.leidas, opiniones.rechazadas, opiniones.enviadas) == (5, 0, 5)
    assert opiniones.conteos.insertadas == 5
    assert bitacora.detalles[0][:2] == ("Fact_Opiniones", "dbo.Fact_Opiniones")


def test_una_segunda_corrida_cuenta_todo_como_ya_existente():
    servicio, _ = crear(cargador=Cargador(ya_existian=10))

    resumen = servicio.ejecutar()

    for resultado in resumen.resultados:
        assert resultado.conteos.insertadas == 0
        assert resultado.conteos.sin_cambios == resultado.enviadas


def test_un_hecho_con_staging_vacio_falla_y_el_otro_se_carga():
    tablas = dict(TABLAS)
    tablas["stg.ResenaWeb"] = TABLAS["stg.ResenaWeb"].iloc[0:0]
    servicio, bitacora = crear(lector=Lector(tablas))

    resumen = servicio.ejecutar()

    assert resumen.estado == "Parcial"
    estados = {r.nombre: r.estado for r in resumen.resultados}
    assert estados == {"Fact_Opiniones": "Exitosa", "Fact_Resenas": "Fallida"}
    assert "stg.ResenaWeb está vacía" in resumen.resultados[1].mensaje


def test_verificar_destino_indica_los_scripts_de_hechos():
    servicio, _ = crear(lector=Lector(faltantes=["stg.ResenaWeb"]),
                        cargador=Cargador(procedimientos_faltantes=["etl.usp_Cargar_Fact_Resenas"]))

    with pytest.raises(ErrorDestino, match=r"stg\.ResenaWeb.*usp_Cargar_Fact_Resenas.*14 al 18"):
        servicio.verificar_destino()


def test_se_puede_cargar_un_solo_hecho_y_un_nombre_desconocido_falla():
    cargador = Cargador()
    servicio, _ = crear(cargador=cargador)

    resumen = servicio.ejecutar(["Fact_Resenas"])

    assert [r.nombre for r in resumen.resultados] == ["Fact_Resenas"]
    with pytest.raises(ValueError, match="Nombre desconocido: Fact_Otra"):
        servicio.ejecutar(["Fact_Otra"])
