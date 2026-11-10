from fastapi.testclient import TestClient

from api_comentarios.app import RUTA_CSV_POR_DEFECTO, crear_app

cliente = TestClient(crear_app(RUTA_CSV_POR_DEFECTO, api_key="llave"))


def test_salud_no_pide_llave():
    assert cliente.get("/salud").json()["registros"] == 200


def test_sin_llave_responde_401():
    assert cliente.get("/api/comentarios").status_code == 401


def test_paginacion():
    cuerpo = cliente.get("/api/comentarios", params={"pagina": 4, "tamano": 60},
                         headers={"X-API-Key": "llave"}).json()
    assert cuerpo["total"] == 200
    assert cuerpo["total_paginas"] == 4
    assert len(cuerpo["datos"]) == 20
