from application.etl_pipeline import ETLPipeline
from application.transformer import DataTransformer
from infrastructure.csv_extractor import CsvExtractor
from infrastructure.db_extractor import DbExtractor
from infrastructure.api_extractor import ApiRestExtractor
from infrastructure.sql_loader import SqlLoader

# Solo cambia la función de CSV en config/dependencies.py:
def ensamblar_pipeline_csv(nombre: str, ruta_csv: str, tabla_sql: str, columnas_obligatorias: list, es_opinion: bool = False, renombrar_cols: dict = None, id_fuente_default: int = None) -> ETLPipeline:
    extractor = CsvExtractor(ruta_archivo=ruta_csv)
    transformer = DataTransformer(columnas_obligatorias=columnas_obligatorias, es_opinion=es_opinion, renombrar_cols=renombrar_cols, id_fuente_default=id_fuente_default)
    loader = SqlLoader(nombre_tabla=tabla_sql)
    
    return ETLPipeline(nombre, extractor, transformer, loader)

def ensamblar_pipeline_db(nombre: str, cadena_conexion_origen: str, query: str, tabla_sql: str, columnas_obligatorias: list, es_opinion: bool = False) -> ETLPipeline:
    """Fábrica para extraer datos desde una Base de Datos Relacional mediante SQL."""
    extractor = DbExtractor(cadena_conexion_origen=cadena_conexion_origen, query=query)
    transformer = DataTransformer(columnas_obligatorias=columnas_obligatorias, es_opinion=es_opinion)
    loader = SqlLoader(nombre_tabla=tabla_sql)
    
    return ETLPipeline(
        nombre_proceso=nombre,
        extractor=extractor,
        transformer=transformer,
        loader=loader
    )

def ensamblar_pipeline_api(nombre: str, url_api: str, tabla_sql: str, columnas_obligatorias: list, es_opinion: bool = False) -> ETLPipeline:
    """Fábrica para extraer datos desde un servicio web (API REST)."""
    extractor = ApiRestExtractor(url_api=url_api)
    transformer = DataTransformer(columnas_obligatorias=columnas_obligatorias, es_opinion=es_opinion)
    loader = SqlLoader(nombre_tabla=tabla_sql)
    
    return ETLPipeline(
        nombre_proceso=nombre,
        extractor=extractor,
        transformer=transformer,
        loader=loader
    )