"""Preparación de catálogos y configuración de los pipelines del ETL."""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from application.etl_pipeline import ETLPipeline
from application.transformer import DataTransformer
from domain import Base
from infrastructure.csv_extractor import CsvExtractor
from infrastructure.db_config import engine
from infrastructure.sql_loader import SqlLoader

DATA = Path(__file__).resolve().parent.parent / "data"


def _crear_pipeline(nombre, archivo, tabla, requeridas, duplicados, **opciones):
    """Construye el pipeline estándar de lectura, transformación y carga."""
    return ETLPipeline(
        nombre,
        CsvExtractor(DATA / archivo),
        DataTransformer(requeridas, duplicados, **opciones),
        SqlLoader(tabla, duplicados),
    )


def _ids_de(tabla, columna):
    consulta = text(f"SELECT [{columna}] FROM [{tabla}]")
    return set(pd.read_sql(consulta, con=engine)[columna])


def _preparar_catalogos():
    """Crea las tablas y agrega las clasificaciones y categorías faltantes."""
    Base.metadata.create_all(engine)

    existentes = set(pd.read_sql(
        text("SELECT IdClasificacion FROM Clasificacion"), con=engine
    )["IdClasificacion"])
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
        (col for col in ("Categoría", "CategorÃ­a") if col in productos.columns),
        None,
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


def _mapa_categorias():
    categorias = pd.read_sql(
        text("SELECT IdCategoria, Nombre FROM Categoria"), con=engine
    )
    return dict(zip(categorias["Nombre"], categorias["IdCategoria"]))


def _pipelines_base():
    return [
        _crear_pipeline(
            "Fuentes de datos", "fuente_datos.csv", "FuenteDatos",
            ["IdFuente", "TipoFuente", "FechaCarga"], ["IdFuente"],
        ),
        _crear_pipeline(
            "Clientes", "clients.csv", "Cliente", ["IdCliente", "Nombre", "Email"],
            ["IdCliente"],
        ),
    ]


def _pipeline_productos(mapa_categorias):
    return _crear_pipeline(
        "Productos", "products.csv", "Producto",
        ["IdProducto", "Nombre", "IdCategoria"], ["IdProducto"],
        renombrar={"Categoría": "IdCategoria", "CategorÃ­a": "IdCategoria"},
        mapas={"IdCategoria": mapa_categorias},
        columnas_salida=["IdProducto", "Nombre", "IdCategoria"],
    )


def _pipelines_opiniones(referencias):
    return [
        _crear_pipeline(
            "Opiniones de encuestas", "surveys_part1.csv", "Opinion",
            ["IdCliente", "IdProducto", "Fecha", "Comentario", "IdFuente",
             "IdClasificacion", "PuntajeSatisfaccion"],
            ["IdCliente", "IdProducto", "Fecha", "Comentario"],
            renombrar={
                "Clasificación": "IdClasificacion",
                "ClasificaciÃƒÂ³n": "IdClasificacion",
                "PuntajeSatisfacciÃƒÂ³n": "PuntajeSatisfaccion",
                "PuntajeSatisfacción": "PuntajeSatisfaccion",
            },
            mapas={"IdClasificacion": {"Positiva": 1, "Negativa": 2, "Neutra": 3}},
            valores_default={"IdFuente": 2}, referencias=referencias,
            columnas_salida=["IdCliente", "IdProducto", "IdClasificacion", "IdFuente",
                             "Fecha", "Comentario", "PuntajeSatisfaccion"],
        ),
        _crear_pipeline(
            "Opiniones de redes sociales", "social_comments.csv", "Opinion",
            ["IdCliente", "IdProducto", "Fecha", "Comentario", "IdFuente"],
            ["IdCliente", "IdProducto", "Fecha", "Comentario"],
            valores_default={"IdFuente": 5}, referencias=referencias,
            columnas_salida=["IdCliente", "IdProducto", "IdFuente", "Fecha", "Comentario"],
        ),
        _crear_pipeline(
            "Opiniones de reseñas web", "web_reviews.csv", "Opinion",
            ["IdCliente", "IdProducto", "Fecha", "Comentario", "IdFuente",
             "PuntajeSatisfaccion"],
            ["IdCliente", "IdProducto", "Fecha", "Comentario"],
            renombrar={"Rating": "PuntajeSatisfaccion"},
            valores_default={"IdFuente": 1}, referencias=referencias,
            columnas_salida=["IdCliente", "IdProducto", "IdFuente", "Fecha",
                             "Comentario", "PuntajeSatisfaccion"],
        ),
    ]


def ejecutar_etl():
    """Prepara catálogos y ejecuta pipelines en orden de dependencias."""
    _preparar_catalogos()
    resumen = {"procesados": 0, "insertados": 0, "rechazados": 0}

    def ejecutar(pipeline):
        resultados = pipeline.ejecutar()
        for metrica in resumen:
            resumen[metrica] += resultados[metrica]

    for pipeline in _pipelines_base():
        ejecutar(pipeline)

    ejecutar(_pipeline_productos(_mapa_categorias()))

    referencias = {
        "IdCliente": _ids_de("Cliente", "IdCliente"),
        "IdProducto": _ids_de("Producto", "IdProducto"),
        "IdFuente": _ids_de("FuenteDatos", "IdFuente"),
        "IdClasificacion": _ids_de("Clasificacion", "IdClasificacion"),
    }
    for pipeline in _pipelines_opiniones(referencias):
        ejecutar(pipeline)

    print("\nResumen del proceso ETL")
    print(
        f"Procesados: {resumen['procesados']} | "
        f"Insertados: {resumen['insertados']} | "
        f"Rechazados: {resumen['rechazados']}"
    )
