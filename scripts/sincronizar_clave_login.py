"""Pone al login etl_extractor la misma clave que está en config/.env.

Evita copiar y pegar la clave a mano (fuente típica de errores).
Se conecta con TU usuario de Windows (debes ser administrador de SQL Server)
y nunca imprime la clave.

Uso (desde la raíz del proyecto, con el .venv activo):
    python scripts/sincronizar_clave_login.py
"""

import sys
from pathlib import Path

import pyodbc
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from infrastructure.settings import cargar_configuracion  # noqa: E402


def main() -> int:
    secretos = dotenv_values(RAIZ / "config" / ".env")
    usuario = secretos.get("SQL_DESTINO_USUARIO")
    clave = secretos.get("SQL_DESTINO_CLAVE")
    if not usuario or not clave:
        print("Faltan SQL_DESTINO_USUARIO o SQL_DESTINO_CLAVE en config/.env")
        return 1
    if secretos.get("SQL_ORIGEN_CLAVE") != clave:
        print("Aviso: SQL_ORIGEN_CLAVE y SQL_DESTINO_CLAVE son distintas; se usa la de destino.")

    destino = cargar_configuracion().conexion("Destino")
    cadena = (
        f"DRIVER={{{destino['Driver']}}};SERVER={destino['Servidor']};DATABASE=master;"
        "Trusted_Connection=yes;TrustServerCertificate=yes"
    )
    with pyodbc.connect(cadena, autocommit=True) as conexion:
        # ALTER LOGIN no acepta parámetros: se escapa la comilla simple duplicándola.
        nombre = usuario.replace("]", "]]")
        clave_sql = clave.replace("'", "''")
        conexion.execute(f"ALTER LOGIN [{nombre}] WITH PASSWORD = N'{clave_sql}'")
        conexion.execute(f"ALTER LOGIN [{nombre}] ENABLE")
        modo = conexion.execute("SELECT CAST(SERVERPROPERTY('IsIntegratedSecurityOnly') AS INT)").fetchval()

    print(f"Clave del login {usuario} sincronizada con config/.env")
    if modo == 1:
        print("ATENCIÓN: el servidor sigue en modo solo Windows; active el modo mixto y reinicie el servicio.")
    else:
        print("Modo mixto activo. Ya puede ejecutar: python worker.py --una-vez")
    return 0


if __name__ == "__main__":
    sys.exit(main())
