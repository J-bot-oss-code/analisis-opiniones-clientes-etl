import asyncio

import httpx
import pytest

from api_comentarios.app import RUTA_CSV_POR_DEFECTO, crear_app
from infrastructure.extractors import ApiExtractor
from infrastructure.extractors.api_extractor import ErrorApi

COLUMNAS = ["IdComment", "IdCliente", "IdProducto", "Fuente", "Fecha", "Comentario"]


def crear_extractor(transport, **opciones):
    return ApiExtractor("API", "stg.ComentarioAPI", "http://api.test", "/api/comentarios",
                        api_key="llave", columnas=COLUMNAS, transport=transport,
                        espera_base_segundos=0, **opciones)


def test_descarga_todas_las_paginas_de_la_api_real():
    """ApiExtractor contra la API FastAPI real, en memoria (sin abrir puertos)."""
    app = crear_app(RUTA_CSV_POR_DEFECTO, api_key="llave")
    extractor = crear_extractor(httpx.ASGITransport(app=app), tamano_pagina=30)

    datos = asyncio.run(extractor.extraer())

    assert len(datos) == 200                      # 200 filas en social_comments.csv
    assert list(datos.columns) == COLUMNAS
    assert datos["IdComment"].is_unique
    assert datos.loc[0, "IdCliente"] == "C019"


def test_llave_incorrecta_no_se_reintenta():
    app = crear_app(RUTA_CSV_POR_DEFECTO, api_key="otra-llave")
    extractor = crear_extractor(httpx.ASGITransport(app=app))

    with pytest.raises(ErrorApi, match="401"):
        asyncio.run(extractor.extraer())


def test_reintenta_ante_error_500():
    llamadas = {"n": 0}

    def responder(request):
        llamadas["n"] += 1
        if llamadas["n"] < 3:
            return httpx.Response(500)
        return httpx.Response(200, json={"total_paginas": 1, "datos": [
            {"IdComment": "T1", "IdCliente": "C1", "IdProducto": "P1", "Fuente": "X",
             "Fecha": "2025-01-01", "Comentario": "ok"}]})

    extractor = crear_extractor(httpx.MockTransport(responder), reintentos=3)
    datos = asyncio.run(extractor.extraer())

    assert llamadas["n"] == 3
    assert len(datos) == 1


def test_se_rinde_despues_de_los_reintentos():
    extractor = crear_extractor(httpx.MockTransport(lambda r: httpx.Response(503)), reintentos=2)
    with pytest.raises(ErrorApi, match="3 intentos"):
        asyncio.run(extractor.extraer())
