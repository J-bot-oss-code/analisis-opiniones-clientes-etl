import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL


SERVIDOR = os.getenv("SQL_SERVER", r".\SQLEXPRESS")
BASE_DATOS = os.getenv("SQL_DATABASE", "OpinionesCliente")
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

CADENA_CONEXION = URL.create(
    "mssql+pyodbc",
    host=SERVIDOR,
    database=BASE_DATOS,
    query={
        "driver": ODBC_DRIVER,
        "Trusted_Connection": "yes",
    },
)

engine = create_engine(CADENA_CONEXION, echo=False, fast_executemany=True)
