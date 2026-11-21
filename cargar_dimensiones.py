"""Carga (L) de las dimensiones del Data Warehouse OpinionesCliente_DW.

Toma los datos que la extracción dejó en staging (stg.*), los prepara y los envía a los
procedimientos almacenados etl.usp_Cargar_Dim_*.  No se ejecuta en ciclo: es un paso aparte
que se corre cuando la extracción ya terminó.

Uso:
    python cargar_dimensiones.py                          # las cinco dimensiones
    python cargar_dimensiones.py --dimension Cliente      # solo una (se puede repetir)
    python cargar_dimensiones.py --config otra_ruta.json
"""

import argparse
import sys

from sqlalchemy.exc import DBAPIError

from application.dimension_service import DIMENSIONES, ResumenCarga
from application.extraction_service import ErrorDestino
from infrastructure.factory import crear_servicio_dimensiones
from infrastructure.logging_config import configurar_logging
from infrastructure.settings import ErrorConfiguracion, cargar_configuracion
from worker import CODIGOS_SALIDA, describir_error_bd


def leer_argumentos(argv=None):
    parser = argparse.ArgumentParser(description="Carga de dimensiones hacia el Data Warehouse")
    parser.add_argument("--dimension", action="append", choices=list(DIMENSIONES),
                        help="dimensión a cargar (por defecto, todas); se puede repetir")
    parser.add_argument("--config", help="ruta alternativa de appsettings.json")
    return parser.parse_args(argv)


def imprimir_resumen(resumen: ResumenCarga) -> None:
    """Tabla final en consola: sirve como evidencia de la carga."""
    columnas = ["Dimensión", "Leídas", "Rechaz.", "Enviadas", "Insertadas", "Actualiz.", "Sin cambios", "Estado"]
    filas = []
    for r in resumen.resultados:
        c = r.conteos
        filas.append([r.nombre, r.leidas, r.rechazadas, r.enviadas,
                      c.insertadas if c else "-", c.actualizadas if c else "-",
                      c.sin_cambios if c else "-", r.estado])
    anchos = [max(len(str(x)) for x in [col] + [f[i] for f in filas]) for i, col in enumerate(columnas)]
    linea = "  ".join(str(col).ljust(anchos[i]) for i, col in enumerate(columnas))
    print()
    print(f"Carga {resumen.id_ejecucion}: {resumen.estado} en {resumen.duracion_segundos:.2f} s")
    print(linea)
    print("-" * len(linea))
    for fila in filas:
        print("  ".join(str(valor).ljust(anchos[i]) for i, valor in enumerate(fila)))
    print()


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
        servicio, motores = crear_servicio_dimensiones(config, logger)
        servicio.verificar_destino(argumentos.dimension)
        resumen = servicio.ejecutar(argumentos.dimension)
        imprimir_resumen(resumen)
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
        logger.exception("Error inesperado en la carga de dimensiones")
        return 1
    finally:
        for motor in motores:
            motor.dispose()


if __name__ == "__main__":
    sys.exit(main())
