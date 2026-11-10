"""Worker de extracción (E) hacia el Data Warehouse OpinionesCliente_DW.

Equivale a un Worker Service (BackgroundService) de .NET: se queda corriendo
y repite la extracción cada `IntervaloMinutos`. Ctrl+C lo detiene de forma ordenada.

Uso:
    python worker.py              # ciclo continuo
    python worker.py --una-vez    # una sola ejecución (útil para pruebas y evidencias)
    python worker.py --intervalo 5
"""

import argparse
import asyncio
import logging
import signal
import sys

from sqlalchemy.exc import DBAPIError

from application.extraction_service import ErrorDestino, ExtractionService
from infrastructure.factory import crear_servicio
from infrastructure.logging_config import configurar_logging
from infrastructure.settings import ErrorConfiguracion, cargar_configuracion

CODIGOS_SALIDA = {"Exitosa": 0, "Fallida": 1, "Parcial": 2}

PISTAS_SQL = {
    "18456": "Login rechazado: revise que el modo mixto esté activo (y el servicio reiniciado) "
             "y que la clave de config/.env sea la del login.",
    "IM002": "No se encontró el driver ODBC: revise \"Driver\" en config/appsettings.json.",
    "08001": "No se pudo llegar al servidor: revise \"Servidor\" y que SQL Server esté encendido.",
}


def describir_error_bd(error: DBAPIError) -> str:
    """Mensaje corto y útil en vez de un traceback largo (nunca incluye la clave)."""
    mensaje = str(error.orig).strip()
    pistas = [pista for codigo, pista in PISTAS_SQL.items() if codigo in mensaje]
    return mensaje + ("\n  -> " + " ".join(pistas) if pistas else "")


def leer_argumentos(argv=None):
    parser = argparse.ArgumentParser(description="Extracción de opiniones hacia el DW")
    parser.add_argument("--una-vez", action="store_true", help="ejecuta una sola vez y termina")
    parser.add_argument("--intervalo", type=float, help="minutos entre ejecuciones")
    parser.add_argument("--config", help="ruta alternativa de appsettings.json")
    return parser.parse_args(argv)


async def ciclo(servicio: ExtractionService, intervalo_minutos: float, una_vez: bool,
                logger: logging.Logger) -> int:
    detener = asyncio.Event()
    try:  # SIGTERM (p. ej. al detener un servicio). En Windows no existe y se ignora.
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, detener.set)
    except (NotImplementedError, AttributeError, ValueError):
        pass

    while True:
        codigo = 1
        try:
            resumen = await servicio.ejecutar()
            codigo = CODIGOS_SALIDA[resumen.estado]
        except DBAPIError as error:
            logger.error("Error de base de datos: %s", describir_error_bd(error))
            logger.debug("Detalle técnico", exc_info=True)
        except Exception:
            # Por ejemplo, SQL Server apagado: se registra y se reintenta en el próximo ciclo.
            logger.exception("La ejecución no pudo completarse")

        if una_vez:
            return codigo

        logger.info("Próxima ejecución en %.1f minutos (Ctrl+C para detener)", intervalo_minutos)
        try:
            await asyncio.wait_for(detener.wait(), timeout=intervalo_minutos * 60)
            logger.info("Señal de parada recibida")
            return 0
        except asyncio.TimeoutError:
            continue


def main(argv=None) -> int:
    argumentos = leer_argumentos(argv)
    try:
        config = cargar_configuracion(argumentos.config)
    except ErrorConfiguracion as error:
        print(f"Error de configuración: {error}", file=sys.stderr)
        return 1

    logger = configurar_logging(config.logging)
    intervalo = argumentos.intervalo or config.intervalo_minutos
    motores = []
    try:
        servicio, motores = crear_servicio(config, logger)
        servicio.verificar_destino()
        logger.info("Worker iniciado (%s)", "una vez" if argumentos.una_vez
                    else f"cada {intervalo:g} min")
        return asyncio.run(ciclo(servicio, intervalo, argumentos.una_vez, logger))
    except (ErrorConfiguracion, ErrorDestino) as error:
        logger.error("%s", error)
        return 1
    except DBAPIError as error:
        logger.error("No se pudo conectar a SQL Server: %s", describir_error_bd(error))
        logger.debug("Detalle técnico", exc_info=True)
        return 1
    except KeyboardInterrupt:
        logger.info("Worker detenido por el usuario")
        return 0
    except Exception:
        logger.exception("Error inesperado al iniciar el worker")
        return 1
    finally:
        for motor in motores:
            motor.dispose()


if __name__ == "__main__":
    sys.exit(main())
