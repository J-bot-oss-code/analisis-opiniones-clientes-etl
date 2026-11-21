from datetime import date

import numpy as np
import pandas as pd
import pytest

from application.dimension_preparation import (CATEGORIA_FALTANTE, OpcionesDimensiones, a_entero,
                                               generar_fecha, normalizar_clave,
                                               preparar_clasificacion, preparar_cliente,
                                               preparar_fuente, preparar_producto)

OPCIONES = OpcionesDimensiones(date(2025, 1, 1), date(2025, 1, 31), miembro_desconocido=True)
SIN_DESCONOCIDO = OpcionesDimensiones(date(2025, 1, 1), date(2025, 1, 31), miembro_desconocido=False)


@pytest.mark.parametrize("valor, esperado", [
    ("C019", "19"), ("P003", "3"), (19, "19"), (19.0, "19"), (np.int64(7), "7"),
    (" 0042 ", "42"), ("0", "0"), ("ABC", "ABC"), (None, None), (np.nan, None), ("  ", None),
])
def test_normalizar_clave(valor, esperado):
    assert normalizar_clave(valor) == esperado


def test_a_entero():
    assert a_entero(5) == 5 and a_entero(5.0) == 5 and a_entero("7") == 7
    assert a_entero(None) is None and a_entero(np.nan) is None and a_entero("x") is None


def test_clasificacion_valida_y_rechaza():
    datos = pd.DataFrame({
        "IdClasificacion": [1, 2, 3, None, 5],
        "Nombre": ["Positiva", "  Neutra ", "", "Sin id", "X" * 21],
    })
    prep = preparar_clasificacion(datos, OPCIONES)
    assert prep.filas == [(1, "Positiva"), (2, "Neutra")]
    assert prep.leidas == 5 and prep.rechazadas == 3 and prep.desconocido == 0
    assert "3 filas rechazadas" in prep.avisos[0]


def test_clasificacion_clave_repetida_conserva_la_ultima():
    datos = pd.DataFrame({"IdClasificacion": [1, 1], "Nombre": ["Vieja", "Nueva"]})
    prep = preparar_clasificacion(datos, OPCIONES)
    assert prep.filas == [(1, "Nueva")]
    assert prep.rechazadas == 1


def test_fuente_agrega_desconocido_y_descarta_fecha_carga():
    datos = pd.DataFrame({"IdFuente": [1, 2], "TipoFuente": ["Web", "CSV"],
                          "FechaCarga": [date(2025, 1, 1)] * 2})
    prep = preparar_fuente(datos, OPCIONES)
    assert prep.filas == [(1, "Web"), (2, "CSV"), (-1, "Desconocido")]
    assert prep.desconocido == 1 and prep.rechazadas == 0
    assert len(preparar_fuente(datos, SIN_DESCONOCIDO).filas) == 2


def test_cliente_normaliza_claves_correo_y_rechaza():
    datos = pd.DataFrame({
        "IdCliente": [1, 2, 3, None],
        "Nombre": ["  Ana   Pérez ", "Luis", None, "Sin id"],
        "Email": ["ANA@Mail.COM ", None, "x@y.z", "q@w.e"],
    })
    prep = preparar_cliente(datos, OPCIONES)
    assert prep.filas == [("1", "Ana Pérez", "ana@mail.com"), ("2", "Luis", ""), ("-1", "Desconocido", "")]
    assert prep.rechazadas == 2 and prep.leidas == 4 and prep.desconocido == 1


def test_cliente_texto_demasiado_largo_se_rechaza_sin_cortarlo():
    datos = pd.DataFrame({"IdCliente": [1], "Nombre": ["N" * 101], "Email": [None]})
    prep = preparar_cliente(datos, SIN_DESCONOCIDO)
    assert prep.filas == [] and prep.rechazadas == 1


def test_cliente_no_duplica_el_desconocido_si_ya_viene():
    datos = pd.DataFrame({"IdCliente": [-1], "Nombre": ["Anónimo"], "Email": [None]})
    prep = preparar_cliente(datos, OPCIONES)
    assert prep.filas == [("-1", "Anónimo", "")] and prep.desconocido == 0


def test_cliente_leidas_rechazadas_enviadas_cuadran():
    datos = pd.DataFrame({"IdCliente": [1, 1, 2, None], "Nombre": ["A", "B", "C", "D"], "Email": [None] * 4})
    prep = preparar_cliente(datos, OPCIONES)
    assert prep.leidas - prep.rechazadas + prep.desconocido == len(prep.filas)


def test_producto_une_la_categoria_y_marca_las_faltantes():
    productos = pd.DataFrame({"IdProducto": [1, 2, 3], "Nombre": ["P1", "P2", "P3"],
                              "IdCategoria": [10, 99, np.nan]})
    categorias = pd.DataFrame({"IdCategoria": [10, 20], "Nombre": ["Hogar", "Ropa"]})
    prep = preparar_producto(productos, categorias, OPCIONES)
    assert prep.filas == [("1", "P1", "Hogar"), ("2", "P2", CATEGORIA_FALTANTE),
                          ("3", "P3", CATEGORIA_FALTANTE), ("-1", "Desconocido", CATEGORIA_FALTANTE)]
    assert prep.rechazadas == 0
    assert "2 productos sin categoría" in prep.avisos[0]


def test_fecha_genera_el_calendario_completo():
    prep = generar_fecha(OpcionesDimensiones(date(2024, 12, 30), date(2025, 1, 2)))
    assert prep.filas == [
        (20241230, date(2024, 12, 30), 30, 12, 4, 2024),
        (20241231, date(2024, 12, 31), 31, 12, 4, 2024),
        (20250101, date(2025, 1, 1), 1, 1, 1, 2025),
        (20250102, date(2025, 1, 2), 2, 1, 1, 2025),
    ]
    assert prep.leidas == 4 and prep.rechazadas == 0


def test_fecha_trimestres_y_anio_bisiesto():
    prep = generar_fecha(OpcionesDimensiones(date(2024, 1, 1), date(2024, 12, 31)))
    assert len(prep.filas) == 366
    trimestres = {fila[4] for fila in prep.filas}
    assert trimestres == {1, 2, 3, 4}
    assert [f for f in prep.filas if f[0] == 20240630][0][4] == 2
    assert [f for f in prep.filas if f[0] == 20240701][0][4] == 3


def test_fecha_rango_invertido_falla():
    with pytest.raises(ValueError):
        generar_fecha(OpcionesDimensiones(date(2025, 2, 1), date(2025, 1, 1)))
