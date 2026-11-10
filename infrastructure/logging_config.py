"""Configuración de logs (equivalente a ILogger / Serilog en .NET).

Escribe cada evento en la consola y en un archivo rotativo: cuando el archivo
llega a `MaxBytes` se renombra a extraccion.log.1, .2, ... hasta `Respaldos`.
"""

import logging
from logging.handlers import RotatingFileHandler

from infrastructure.settings import ruta_del_proyecto

FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def configurar_logging(opciones: dict) -> logging.Logger:
    nivel = getattr(logging, str(opciones.get("Nivel", "INFO")).upper(), logging.INFO)
    archivo = ruta_del_proyecto(opciones.get("Archivo", "logs/extraccion.log"))
    archivo.parent.mkdir(parents=True, exist_ok=True)

    formato = logging.Formatter(FORMATO, FORMATO_FECHA)

    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    rotativo = RotatingFileHandler(
        archivo,
        maxBytes=int(opciones.get("MaxBytes", 1_048_576)),
        backupCount=int(opciones.get("Respaldos", 5)),
        encoding="utf-8",
    )
    rotativo.setFormatter(formato)

    raiz = logging.getLogger("extraccion")
    raiz.setLevel(nivel)
    raiz.handlers.clear()
    raiz.addHandler(consola)
    raiz.addHandler(rotativo)
    raiz.propagate = False

    # httpx registra cada petición en INFO; se baja a WARNING para no llenar el log.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return raiz
