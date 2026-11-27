"""Carga (L) de las tablas de hechos del Data Warehouse OpinionesCliente_DW.

Se ejecuta DESPUÉS de cargar las dimensiones (cargar_dimensiones.py) y de una extracción que haya
llenado staging (worker.py --una-vez).  Toma stg.*, prepara las filas (valida claves contra las
dimensiones, descarta lo inválido) y las envía por lotes a los procedimientos etl.usp_Cargar_Fact_*,
que solo insertan lo que todavía no existe.  Se puede repetir sin duplicar datos.

Uso:
    python cargar_hechos.py                           # Fact_Opiniones y Fact_Resenas
    python cargar_hechos.py --hecho Fact_Resenas      # solo uno (se puede repetir)
    python cargar_hechos.py --config otra_ruta.json
"""

import argparse
import sys

from sqlalchemy.exc import DBAPIError

from application.extraction_service import ErrorDestino
from application.fact_service import HECHOS
from cargar_dimensiones import imprimir_resumen
from infrastructure.factory import crear_servicio_hechos
from infrastructure.logging_config import configurar_logging
from infrastructure.settings import ErrorConfiguracion, cargar_configuracion
from worker import CODIGOS_SALIDA, describir_error_bd


def leer_argumentos(argv=None):
    parser = argparse.ArgumentParser(description="Carga de hechos hacia el Data Warehouse")
    parser.add_argument("--hecho", action="append", choices=list(HECHOS),
                        help="tabla de hechos a cargar (por defecto, todas); se puede repetir")
    parser.add_argument("--config", help="ruta alternativa de appsettings.json")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    argumentos = leer_argumentos(argv)
    try:
        config = cargar_configuracion(argumentos.config)
    except ErrorConfiguracion as error:
        print(f"Error de configuración: {error}", file=sys.stderr)
        return 1

    logger = configurar_logging(config.logging)
    motores = []
    try:
        servicio, motores = crear_servicio_hechos(config, logger)
        servicio.verificar_destino(argumentos.hecho)
        resumen = servicio.ejecutar(argumentos.hecho)
        imprimir_resumen(resumen, objeto="Hecho", sin_cambios="Ya existían")
        return CODIGOS_SALIDA[resumen.estado]
    except (ErrorConfiguracion, ErrorDestino) as error:
        logger.error("%s", error)
        return 1
    except DBAPIError as error:
        logger.error("Error de base de datos: %s", describir_error_bd(error))
        logger.debug("Detalle técnico", exc_info=True)
        return 1
    except KeyboardInterrupt:
        logger.info("Carga detenida por el usuario")
        return 0
    except Exception:
        logger.exception("Error inesperado en la carga de hechos")
        return 1
    finally:
        for motor in motores:
            motor.dispose()


if __name__ == "__main__":
    sys.exit(main())
