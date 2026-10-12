from pathlib import Path

import pandas as pd
from sqlalchemy import text

from application.etl_pipeline import ETLPipeline
from application.transformer import DataTransformer
from domain import Base
from infrastructure.csv_extractor import CsvExtractor
from infrastructure.db_config import engine
from infrastructure.sql_loader import SqlLoader

DATA = Path(__file__).parent / "data"


def crear_pipeline(nombre, archivo, tabla, requeridas, duplicados, **opciones):
    return ETLPipeline(
        nombre,
        CsvExtractor(DATA / archivo),
        DataTransformer(requeridas, duplicados, **opciones),
        SqlLoader(tabla, duplicados),
    )


def ids_de(tabla, columna):
    return set(pd.read_sql(text(f"SELECT [{columna}] FROM [{tabla}]"), con=engine)[columna])


def preparar_catalogos():
    Base.metadata.create_all(engine)
    clasificaciones = pd.read_sql(text("SELECT IdClasificacion FROM Clasificacion"), con=engine)
    existentes = set(clasificaciones["IdClasificacion"])
    catalogo = pd.DataFrame([
        {"IdClasificacion": 1, "Nombre": "Positiva"},
        {"IdClasificacion": 2, "Nombre": "Negativa"},
        {"IdClasificacion": 3, "Nombre": "Neutra"},
    ])
    faltantes = catalogo[~catalogo["IdClasificacion"].isin(existentes)]
    if not faltantes.empty:
        faltantes.to_sql("Clasificacion", con=engine, if_exists="append", index=False)

    productos = pd.read_csv(DATA / "products.csv", encoding="utf-8")
    columna_categoria = next(
        (col for col in ("Categoría", "CategorÃ­a") if col in productos.columns), None
    )
    if columna_categoria is None:
        raise ValueError("products.csv debe incluir la columna Categoría")
    nombres = productos[columna_categoria].dropna().astype(str).str.strip().unique()
    categorias = pd.read_sql(text("SELECT Nombre FROM Categoria"), con=engine)["Nombre"]
    faltantes = sorted(set(nombres) - set(categorias))
    if faltantes:
        pd.DataFrame({"Nombre": faltantes}).to_sql(
            "Categoria", con=engine, if_exists="append", index=False
        )


def ejecutar_etl():
    preparar_catalogos()
    categorias = pd.read_sql(text("SELECT IdCategoria, Nombre FROM Categoria"), con=engine)
    mapa_categorias = dict(zip(categorias["Nombre"], categorias["IdCategoria"]))

    pipelines = [
        crear_pipeline(
            "Fuentes de datos", "fuente_datos.csv", "FuenteDatos",
            ["IdFuente", "TipoFuente", "FechaCarga"], ["IdFuente"],
        ),
        crear_pipeline(
            "Clientes", "clients.csv", "Cliente", ["IdCliente", "Nombre", "Email"],
            ["IdCliente"],
        ),
    ]
    for pipeline in pipelines:
        pipeline.ejecutar()

    producto_pipeline = crear_pipeline(
        "Productos", "products.csv", "Producto",
        ["IdProducto", "Nombre", "IdCategoria"], ["IdProducto"],
        renombrar={"Categoría": "IdCategoria", "CategorÃ­a": "IdCategoria"},
        mapas={"IdCategoria": mapa_categorias},
        columnas_salida=["IdProducto", "Nombre", "IdCategoria"],
    )
    producto_pipeline.ejecutar()

    referencias = {
        "IdCliente": ids_de("Cliente", "IdCliente"),
        "IdProducto": ids_de("Producto", "IdProducto"),
        "IdFuente": ids_de("FuenteDatos", "IdFuente"),
        "IdClasificacion": ids_de("Clasificacion", "IdClasificacion"),
    }
    opinion_pipeline = [
        crear_pipeline(
            "Opiniones de encuestas", "surveys_part1.csv", "Opinion",
            ["IdCliente", "IdProducto", "Fecha", "Comentario", "IdFuente", "IdClasificacion", "PuntajeSatisfaccion"],
            ["IdCliente", "IdProducto", "Fecha", "Comentario"],
            renombrar={
                "Clasificación": "IdClasificacion",
                "ClasificaciÃ³n": "IdClasificacion",
                "PuntajeSatisfacciÃ³n": "PuntajeSatisfaccion",
                "PuntajeSatisfacción": "PuntajeSatisfaccion",
            },
            mapas={"IdClasificacion": {"Positiva": 1, "Negativa": 2, "Neutra": 3}},
            valores_default={"IdFuente": 2}, referencias=referencias,
            columnas_salida=["IdCliente", "IdProducto", "IdClasificacion", "IdFuente", "Fecha", "Comentario", "PuntajeSatisfaccion"],
        ),
        crear_pipeline(
            "Opiniones de redes sociales", "social_comments.csv", "Opinion",
            ["IdCliente", "IdProducto", "Fecha", "Comentario", "IdFuente"],
            ["IdCliente", "IdProducto", "Fecha", "Comentario"],
            valores_default={"IdFuente": 5}, referencias=referencias,
            columnas_salida=["IdCliente", "IdProducto", "IdFuente", "Fecha", "Comentario"],
        ),
        crear_pipeline(
            "Opiniones de reseñas web", "web_reviews.csv", "Opinion",
            ["IdCliente", "IdProducto", "Fecha", "Comentario", "IdFuente", "PuntajeSatisfaccion"],
            ["IdCliente", "IdProducto", "Fecha", "Comentario"],
            renombrar={"Rating": "PuntajeSatisfaccion"},
            valores_default={"IdFuente": 1}, referencias=referencias,
            columnas_salida=["IdCliente", "IdProducto", "IdFuente", "Fecha", "Comentario", "PuntajeSatisfaccion"],
        ),
    ]
    for pipeline in opinion_pipeline:
        pipeline.ejecutar()


if __name__ == "__main__":
    try:
        ejecutar_etl()
    except Exception as error:
        print(f"ETL detenido: {error}")
        raise
