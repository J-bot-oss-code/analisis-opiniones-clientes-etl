"""Registro de las tablas de hechos que se cargan (L) en el Data Warehouse.

Usa el mismo servicio que las dimensiones (DimensionLoadService) con otro registro: por cada hecho lee
su staging, prepara las filas (application/fact_preparation.py), las envía al procedimiento almacenado
etl.usp_Cargar_Fact_* mediante un tipo de tabla y anota el resultado en la bitácora.
Se cargan DESPUÉS de las dimensiones, porque cada hecho depende de ellas (llaves foráneas).
"""

from application.dimension_service import DefinicionDimension
from application.fact_preparation import preparar_fact_opiniones, preparar_fact_resenas

# Tablas staging de las que salen las claves válidas de cada dimensión (cliente, producto, fuente, clasificación)
_REFERENCIAS = ("stg.Cliente", "stg.Producto", "stg.Categoria", "stg.FuenteDatos", "stg.Clasificacion")

HECHOS: dict[str, DefinicionDimension] = {d.nombre: d for d in [
    DefinicionDimension(
        "Fact_Opiniones", "dbo.Fact_Opiniones", "etl.T_Fact_Opiniones", "etl.usp_Cargar_Fact_Opiniones",
        ("stg.Opinion", "stg.EncuestaCSV") + _REFERENCIAS,
        lambda tablas, opciones: preparar_fact_opiniones(tablas, opciones)),
    DefinicionDimension(
        "Fact_Resenas", "dbo.Fact_Resenas", "etl.T_Fact_Resenas", "etl.usp_Cargar_Fact_Resenas",
        ("stg.ResenaWeb",) + _REFERENCIAS,
        lambda tablas, opciones: preparar_fact_resenas(tablas, opciones)),
]}
