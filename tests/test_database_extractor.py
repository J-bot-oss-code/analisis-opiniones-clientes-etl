import asyncio

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from infrastructure.extractors import DatabaseExtractor


def motor_en_memoria():
    # SQLite en memoria: una sola conexión compartida, porque el extractor lee en otro hilo.
    return create_engine("sqlite://", poolclass=StaticPool,
                         connect_args={"check_same_thread": False})


def test_lee_por_lotes_y_une_el_resultado():
    motor = motor_en_memoria()
    with motor.begin() as conexion:
        conexion.execute(text("CREATE TABLE Cliente (IdCliente INT, Nombre TEXT, Email TEXT)"))
        conexion.execute(text("INSERT INTO Cliente VALUES (:i, :n, :e)"),
                         [{"i": i, "n": f"Cliente_{i}", "e": f"c{i}@mail.com"} for i in range(1, 12)])

    extractor = DatabaseExtractor("BD_Cliente", "stg.Cliente", motor,
                                  "SELECT IdCliente, Nombre, Email FROM Cliente", tamano_lote=5)
    datos = asyncio.run(extractor.extraer())

    assert len(datos) == 11                     # 3 lotes: 5 + 5 + 1
    assert list(datos.columns) == ["IdCliente", "Nombre", "Email"]


def test_tabla_vacia_conserva_las_columnas():
    motor = motor_en_memoria()
    with motor.begin() as conexion:
        conexion.execute(text("CREATE TABLE Categoria (IdCategoria INT, Nombre TEXT)"))

    extractor = DatabaseExtractor("BD_Categoria", "stg.Categoria", motor,
                                  "SELECT IdCategoria, Nombre FROM Categoria")
    datos = asyncio.run(extractor.extraer())

    assert datos.empty
    assert list(datos.columns) == ["IdCategoria", "Nombre"]
