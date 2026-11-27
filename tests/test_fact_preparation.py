from datetime import date, datetime
from decimal import Decimal

import pandas as pd

from application.dimension_preparation import OpcionesDimensiones
from application.fact_preparation import (OpcionesHechos, a_decimal, a_fecha, a_id_fecha, a_rating,
                                          preparar_fact_opiniones, preparar_fact_resenas)

DIM = OpcionesDimensiones(date(2025, 1, 1), date(2025, 12, 31))
OPCIONES = OpcionesHechos(DIM, id_fuente_encuestas=2, fuentes_excluidas_opiniones=frozenset({1}), tamano_lote=2)

COL_OPINION = ["IdOpinion", "IdCliente", "IdProducto", "IdClasificacion", "IdFuente", "Fecha", "Comentario",
               "PuntajeSatisfaccion"]
COL_ENCUESTA = ["IdOpinion", "IdCliente", "IdProducto", "Fecha", "Comentario", "Clasificacion",
                "PuntajeSatisfaccion", "Fuente"]
COL_RESENA = ["IdReview", "IdCliente", "IdProducto", "Fecha", "Comentario", "Rating"]


def datos(opiniones=(), encuestas=(), resenas=(), clasificaciones=None):
    """Staging mínimo: clientes 1-2, productos 1-2, fuentes 1/2/5 y las tres clasificaciones."""
    return {
        "stg.Opinion": pd.DataFrame(list(opiniones), columns=COL_OPINION),
        "stg.EncuestaCSV": pd.DataFrame(list(encuestas), columns=COL_ENCUESTA),
        "stg.ResenaWeb": pd.DataFrame(list(resenas), columns=COL_RESENA),
        "stg.Cliente": pd.DataFrame({"IdCliente": [1, 2], "Nombre": ["Ana", "Luis"], "Email": [None, None]}),
        "stg.Categoria": pd.DataFrame({"IdCategoria": [1], "Nombre": ["Hogar"]}),
        "stg.Producto": pd.DataFrame({"IdProducto": [1, 2], "Nombre": ["P1", "P2"], "IdCategoria": [1, 1]}),
        "stg.FuenteDatos": pd.DataFrame({"IdFuente": [1, 2, 5], "TipoFuente": ["Web", "CSV", "Red Social"]}),
        "stg.Clasificacion": pd.DataFrame(clasificaciones if clasificaciones is not None else
                                          {"IdClasificacion": [1, 2, 3],
                                           "Nombre": ["Positiva", "Negativa", "Neutra"]}),
    }


def opinion(id_=10, cliente=1, producto=2, clasif=1, fuente=2, fecha="2025-03-15", comentario="Muy bueno", puntaje=4):
    return [id_, cliente, producto, clasif, fuente, date.fromisoformat(fecha), comentario, puntaje]


def encuesta(id_="5", cliente="1", producto="2", fecha="2025-03-15", comentario="Muy bueno", clasif="Neutra",
             puntaje="3", fuente="EncuestaInterna"):
    return [id_, cliente, producto, fecha, comentario, clasif, puntaje, fuente]


# ------------------------------------------------------------ conversiones

def test_conversiones_basicas():
    assert a_fecha("2025-03-15") == date(2025, 3, 15)
    assert a_fecha(datetime(2025, 3, 15, 10, 0)) == date(2025, 3, 15)
    assert a_fecha("15/03/2025") is None and a_fecha(None) is None and a_fecha(float("nan")) is None
    assert a_id_fecha(date(2025, 3, 15), DIM) == 20250315
    assert a_id_fecha(date(2026, 1, 1), DIM) is None
    assert a_decimal("3,5") == Decimal("3.50") and a_decimal("x") is None and a_decimal(float("nan")) is None
    assert a_rating("4") == 4 and a_rating("4.0") == 4 and a_rating("3.5") is None and a_rating("6") is None


# ------------------------------------------------------------ Fact_Opiniones

def test_opinion_relacional_valida_se_envia_con_prefijo_y_decimal():
    p = preparar_fact_opiniones(datos(opiniones=[opinion()]), OPCIONES)

    assert p.filas == [("BD-10", "1", "2", 2, 1, 20250315, Decimal("4.00"))]
    assert (p.leidas, p.rechazadas) == (1, 0)


def test_opiniones_de_fuentes_solo_resena_no_se_cargan_aqui():
    p = preparar_fact_opiniones(datos(opiniones=[opinion(fuente=1)]), OPCIONES)

    assert p.filas == [] and p.rechazadas == 1
    assert "de fuentes que se cargan como reseñas" in p.avisos[0]


def test_se_rechaza_si_falta_puntaje_o_clasificacion_o_esta_fuera_de_escala():
    filas = [opinion(10, puntaje=None), opinion(11, puntaje=7), opinion(12, clasif=None), opinion(13, clasif=99)]

    p = preparar_fact_opiniones(datos(opiniones=filas), OPCIONES)

    assert p.filas == [] and p.rechazadas == 4
    assert "2 sin puntaje válido (1 a 5)" in p.avisos[0] and "2 sin clasificación válida" in p.avisos[0]


def test_cliente_o_producto_inexistente_va_al_miembro_desconocido():
    p = preparar_fact_opiniones(datos(opiniones=[opinion(cliente=999, producto=888)]), OPCIONES)

    assert p.filas[0][1:3] == ("-1", "-1")
    assert p.rechazadas == 0
    assert "1 con cliente desconocido (-1)" in p.avisos[0] and "1 con producto desconocido (-1)" in p.avisos[0]


def test_sin_miembro_desconocido_la_fila_se_rechaza():
    opciones = OpcionesHechos(OpcionesDimensiones(date(2025, 1, 1), date(2025, 12, 31), miembro_desconocido=False))

    p = preparar_fact_opiniones(datos(opiniones=[opinion(cliente=999)]), opciones)

    assert p.filas == [] and "1 con cliente inexistente" in p.avisos[0]


def test_fecha_fuera_de_rango_o_invalida_se_rechaza():
    filas = [opinion(10, fecha="2024-12-31"), opinion(11, fecha="2026-01-01")]
    p = preparar_fact_opiniones(datos(opiniones=filas, encuestas=[encuesta(fecha="ayer")]), OPCIONES)

    assert p.filas == [] and p.rechazadas == 3
    assert "3 con fecha inválida o fuera de Dim_Fecha" in p.avisos[0]


def test_encuesta_usa_clasificacion_por_nombre_y_la_fuente_de_encuestas():
    p = preparar_fact_opiniones(datos(encuestas=[encuesta(id_="5", clasif="  neutra ", puntaje="3")]), OPCIONES)

    assert p.filas == [("ENC-5", "1", "2", 2, 3, 20250315, Decimal("3.00"))]


def test_clientes_de_la_encuesta_fuera_de_la_dimension_quedan_como_desconocido():
    p = preparar_fact_opiniones(datos(encuestas=[encuesta(cliente="8537", producto="667")]), OPCIONES)

    assert p.filas[0][1:3] == ("-1", "-1")


def test_sin_miembro_desconocido_se_rechaza_segun_que_clave_falte():
    sin_desconocido = OpcionesHechos(OpcionesDimensiones(date(2025, 1, 1), date(2025, 12, 31),
                                                         miembro_desconocido=False))
    filas = [encuesta("1", cliente="999", producto="2"),     # cliente inexistente
             encuesta("2", cliente="1", producto="888"),     # producto inexistente
             encuesta("3", cliente="999", producto="888"),   # ambos
             encuesta("4", cliente="2", producto="1")]       # válida

    p = preparar_fact_opiniones(datos(encuestas=filas), sin_desconocido)

    assert [f[0] for f in p.filas] == ["ENC-4"]
    assert (p.leidas, p.rechazadas) == (4, 3)
    for motivo in ("1 con cliente inexistente", "1 con producto inexistente", "1 con cliente y producto inexistentes"):
        assert motivo in p.avisos[0]


def test_el_prefijo_evita_que_choquen_ids_de_distintas_fuentes():
    p = preparar_fact_opiniones(
        datos(opiniones=[opinion(id_=1, comentario="uno")],
              encuestas=[encuesta(id_="1", cliente="2", comentario="otro")]), OPCIONES)

    assert [f[0] for f in p.filas] == ["BD-1", "ENC-1"]


def test_encuesta_ya_cargada_desde_la_base_relacional_no_se_repite():
    p = preparar_fact_opiniones(
        datos(opiniones=[opinion(id_=10, comentario="Muy bueno")],
              encuestas=[encuesta(id_="5", comentario="  muy   BUENO ")]), OPCIONES)

    assert [f[0] for f in p.filas] == ["BD-10"]
    assert p.rechazadas == 1 and "1 ya cargadas desde la base relacional" in p.avisos[0]


def test_encuesta_repetida_se_detecta_aunque_el_comentario_sea_distinto():
    p = preparar_fact_opiniones(
        datos(opiniones=[opinion(id_=10, comentario="Muy bueno")],
              encuestas=[encuesta(id_="5", comentario="Excelente producto, lo recomiendo")]), OPCIONES)

    assert [f[0] for f in p.filas] == ["BD-10"] and p.rechazadas == 1


def test_clave_repetida_conserva_la_ultima_fila():
    p = preparar_fact_opiniones(
        datos(opiniones=[opinion(id_=10, puntaje=2), opinion(id_=10, puntaje=5)]), OPCIONES)

    assert len(p.filas) == 1 and p.filas[0][6] == Decimal("5.00")
    assert (p.leidas, p.rechazadas) == (2, 1)
    assert p.leidas - p.rechazadas == len(p.filas)


# ------------------------------------------------------------ Fact_Resenas

def resena(id_="W0001", cliente="C001", producto="P002", fecha="2025-02-02", rating="4"):
    return [id_, cliente, producto, fecha, "Comentario", rating]


def test_resena_se_clasifica_segun_el_rating():
    filas = [resena("W1", rating="1"), resena("W2", rating="2"), resena("W3", rating="3"),
             resena("W4", rating="4"), resena("W5", rating="5")]

    p = preparar_fact_resenas(datos(resenas=filas), OPCIONES)

    assert [(f[0], f[4], f[5]) for f in p.filas] == [("W1", 2, 1), ("W2", 2, 2), ("W3", 3, 3),
                                                      ("W4", 1, 4), ("W5", 1, 5)]


def test_resena_normaliza_las_claves_de_cliente_y_producto():
    p = preparar_fact_resenas(datos(resenas=[resena(cliente="C001", producto="P002")]), OPCIONES)

    assert p.filas == [("W0001", "1", "2", 20250202, 1, 4)]


def test_resena_invalida_se_rechaza():
    filas = [resena("W1", rating="6"), resena("W2", rating="x"), resena(None), resena("W4", fecha="2030-01-01")]

    p = preparar_fact_resenas(datos(resenas=filas), OPCIONES)

    assert p.filas == [] and p.rechazadas == 4


def test_resena_repetida_conserva_la_ultima_y_cliente_desconocido_se_avisa():
    p = preparar_fact_resenas(
        datos(resenas=[resena("W1", rating="2"), resena("W1", cliente="C900", rating="5")]), OPCIONES)

    assert p.filas == [("W1", "-1", "2", 20250202, 1, 5)]
    assert (p.leidas, p.rechazadas) == (2, 1)
    assert any("cliente desconocido" in a for a in p.avisos)


def test_resena_sin_clasificacion_equivalente_en_la_dimension_se_rechaza():
    solo_positiva = {"IdClasificacion": [1], "Nombre": ["Positiva"]}

    p = preparar_fact_resenas(datos(resenas=[resena("W1", rating="3")], clasificaciones=solo_positiva), OPCIONES)

    assert p.filas == [] and "sin clasificación equivalente al Rating" in p.avisos[0]
