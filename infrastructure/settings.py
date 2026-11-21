"""Carga la configuración del worker.

- `config/appsettings.json`: todo lo que NO es secreto (fuentes, rutas, lotes).
- `config/.env`: secretos (API key, usuario y clave de SQL). Excluido de Git.

Es el equivalente en Python a IConfiguration + appsettings.json + User Secrets.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.engine import URL

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_CONFIG_POR_DEFECTO = RAIZ_PROYECTO / "config" / "appsettings.json"
RUTA_ENV_POR_DEFECTO = RAIZ_PROYECTO / "config" / ".env"


class ErrorConfiguracion(Exception):
    """La configuración está incompleta o es inválida."""


@dataclass(frozen=True)
class Configuracion:
    datos: dict[str, Any]

    @property
    def intervalo_minutos(self) -> float:
        return float(self.datos.get("Worker", {}).get("IntervaloMinutos", 60))

    @property
    def tamano_lote(self) -> int:
        return int(self.datos.get("Extraccion", {}).get("TamanoLote", 5000))

    @property
    def fuentes_activas(self) -> list[dict[str, Any]]:
        return [f for f in self.datos.get("Fuentes", []) if f.get("Activa", True)]

    @property
    def logging(self) -> dict[str, Any]:
        return self.datos.get("Logging", {})

    @property
    def dimensiones(self) -> dict[str, Any]:
        """Opciones de la carga de dimensiones (miembro Desconocido y rango de Dim_Fecha)."""
        return self.datos.get("Dimensiones", {})

    def conexion(self, nombre: str) -> dict[str, Any]:
        try:
            return self.datos["Conexiones"][nombre]
        except KeyError as error:
            raise ErrorConfiguracion(f"Falta la conexión '{nombre}' en appsettings.json") from error


def cargar_configuracion(ruta_config: Path | str | None = None,
                         ruta_env: Path | str | None = None) -> Configuracion:
    """Lee appsettings.json y carga las variables del .env en el entorno."""
    ruta_config = Path(ruta_config or RUTA_CONFIG_POR_DEFECTO)
    ruta_env = Path(ruta_env or RUTA_ENV_POR_DEFECTO)

    # override=False: una variable ya definida en el sistema tiene prioridad sobre el .env.
    if ruta_env.exists():
        load_dotenv(ruta_env, override=False)

    try:
        datos = json.loads(ruta_config.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ErrorConfiguracion(f"No existe el archivo de configuración {ruta_config}") from error
    except json.JSONDecodeError as error:
        raise ErrorConfiguracion(f"appsettings.json no es un JSON válido: {error}") from error

    return Configuracion(datos)


def secreto(nombre_variable: str, obligatorio: bool = True) -> str | None:
    """Lee un secreto del entorno. Nunca se escribe en los logs."""
    valor = os.getenv(nombre_variable)
    if obligatorio and not valor:
        raise ErrorConfiguracion(
            f"Falta la variable de entorno {nombre_variable}. Defínela en config/.env"
        )
    return valor


def crear_url_sql_server(conexion: dict[str, Any]) -> URL:
    """Construye la URL de SQLAlchemy para SQL Server a partir de la configuración."""
    consulta = {"driver": conexion.get("Driver", "ODBC Driver 17 for SQL Server")}
    consulta.update(conexion.get("OpcionesOdbc", {}))

    usuario = clave = None
    if conexion.get("AutenticacionWindows", True):
        consulta["Trusted_Connection"] = "yes"
    else:
        usuario = secreto(conexion["VariableUsuario"])
        clave = secreto(conexion["VariableClave"])

    return URL.create(
        "mssql+pyodbc",
        username=usuario,
        password=clave,
        host=conexion["Servidor"],
        database=conexion["BaseDatos"],
        query=consulta,
    )


def ruta_del_proyecto(ruta: str) -> Path:
    """Convierte una ruta relativa del JSON en absoluta respecto a la raíz del proyecto."""
    ruta_path = Path(ruta)
    return ruta_path if ruta_path.is_absolute() else RAIZ_PROYECTO / ruta_path
