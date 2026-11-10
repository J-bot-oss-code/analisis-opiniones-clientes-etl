"""API REST local de comentarios de redes sociales (FastAPI).

Sirve `data/social_comments.csv` como JSON paginado y exige la llave
`X-API-Key`, igual que lo haría una API externa real.

Arranque (desde la raíz del proyecto):
    uvicorn api_comentarios.app:app --port 8000

Documentación interactiva: http://127.0.0.1:8000/docs
"""

import csv
import math
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CSV_POR_DEFECTO = RAIZ / "data" / "social_comments.csv"
VARIABLE_API_KEY = "API_COMENTARIOS_KEY"


def _leer_comentarios(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        return [
            {campo: (valor if valor not in ("", None) else None) for campo, valor in fila.items()}
            for fila in csv.DictReader(archivo)
        ]


def crear_app(ruta_csv: Path | None = None, api_key: str | None = None) -> FastAPI:
    load_dotenv(RAIZ / "config" / ".env", override=False)
    llave_esperada = api_key or os.getenv(VARIABLE_API_KEY)
    comentarios = _leer_comentarios(ruta_csv or RUTA_CSV_POR_DEFECTO)

    app = FastAPI(
        title="API de comentarios de redes sociales",
        description="Fuente REST del proyecto de análisis de opiniones de clientes.",
        version="1.0.0",
    )

    def verificar_llave(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
        if not llave_esperada:
            raise HTTPException(status_code=503, detail=f"Falta configurar {VARIABLE_API_KEY}")
        # compare_digest compara en tiempo constante (evita ataques de temporización).
        if x_api_key is None or not secrets.compare_digest(x_api_key, llave_esperada):
            raise HTTPException(status_code=401, detail="API key inválida o ausente")

    @app.get("/salud")
    def salud():
        return {"estado": "ok", "registros": len(comentarios)}

    @app.get("/api/comentarios", dependencies=[Depends(verificar_llave)])
    def listar_comentarios(pagina: int = Query(1, ge=1), tamano: int = Query(50, ge=1, le=500)):
        total = len(comentarios)
        inicio = (pagina - 1) * tamano
        return {
            "pagina": pagina,
            "tamano": tamano,
            "total": total,
            "total_paginas": max(1, math.ceil(total / tamano)),
            "datos": comentarios[inicio:inicio + tamano],
        }

    return app


app = crear_app()
