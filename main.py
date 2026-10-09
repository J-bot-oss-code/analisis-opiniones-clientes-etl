import pandas as pd
from config.dependencies import ensamblar_pipeline_csv
from infrastructure.db_config import engine
from domain.base import Base




def preparar_base_datos():
    """Genera las tablas y llena los catálogos faltantes para evitar errores de Foreign Key"""
    print("SISTEMA DE ANÁLISIS DE OPINIONES - PREPARANDO ENTORNO...")
    
    # Crea las tablas si no existen basándose en los modelos de /domain
    Base.metadata.create_all(engine)
    
    # 1. Insertar solo clasificaciones faltantes para que la preparación sea repetible.
    clasificaciones = pd.DataFrame({
        'IdClasificacion': [1, 2, 3],
        'Nombre': ['Positiva', 'Negativa', 'Neutra'],
    })
    existentes = pd.read_sql(
        'SELECT IdClasificacion FROM Clasificacion', con=engine
    )['IdClasificacion'].tolist()
    clasificaciones = clasificaciones[
        ~clasificaciones['IdClasificacion'].isin(existentes)
    ]
    if not clasificaciones.empty:
        clasificaciones.to_sql(
            'Clasificacion', con=engine, if_exists='append', index=False
        )

    # 2. Insertar categorías sin IdCategoria: SQL Server genera el IDENTITY.
    df_prod = pd.read_csv('data/products.csv')
    categorias = pd.Index(df_prod['Categoría'].dropna().unique(), name='Nombre')
    existentes = pd.read_sql(
        'SELECT Nombre FROM Categoria', con=engine
    )['Nombre'].tolist()
    categorias_faltantes = categorias[~categorias.isin(existentes)]
    if len(categorias_faltantes):
        pd.DataFrame({'Nombre': categorias_faltantes}).to_sql(
            'Categoria', con=engine, if_exists='append', index=False
        )

def main():
    preparar_base_datos()
    print("\nINICIANDO PROCESO ETL...")

    # ==========================================
    # 1. TABLAS INDEPENDIENTES
    # ==========================================
    pipeline_fuentes = ensamblar_pipeline_csv("Fuentes de Datos", 'data/fuente_datos.csv', 'FuenteDatos', ['IdFuente', 'TipoFuente'])
    pipeline_fuentes.ejecutar()

    pipeline_clientes = ensamblar_pipeline_csv("Clientes", 'data/clients.csv', 'Cliente', ['IdCliente', 'Nombre'])
    pipeline_clientes.ejecutar()

    # ==========================================
    # 2. TABLAS DEPENDIENTES (Nivel 1)
    # ==========================================
    # Extraemos el catálogo de la BD para hacer el cruce correcto
    cats = pd.read_sql('SELECT IdCategoria, Nombre FROM Categoria', con=engine)
    mapa_cats = dict(zip(cats['Nombre'], cats['IdCategoria']))
    
    pipe_productos = ensamblar_pipeline_csv("Productos", 'data/products.csv', 'Producto', ['IdProducto', 'Nombre'])
    
    # Le decimos al transformer que renombre la columna
    pipe_productos.transformer.renombrar_cols = {'Categoría': 'IdCategoria'}
    
    # Guardamos el método de limpieza original
    transformacion_original = pipe_productos.transformer.transformar
    
    # Creamos una función que hace la limpieza normal + el reemplazo de las categorías
    def transformacion_con_mapeo(df):
        df_limpio, rechazados = transformacion_original(df)
        if not df_limpio.empty and 'IdCategoria' in df_limpio.columns:
            df_limpio['IdCategoria'] = df_limpio['IdCategoria'].replace(mapa_cats)
        return df_limpio, rechazados
        
    # Inyectamos nuestra función mejorada (Monkey Patching)
    pipe_productos.transformer.transformar = transformacion_con_mapeo
    pipe_productos.ejecutar()

    # Validar las referencias antes de enviar opiniones en un INSERT masivo.
    ids_validos = {
        'IdCliente': set(pd.read_sql('SELECT IdCliente FROM Cliente', con=engine)['IdCliente'].dropna().astype(int)),
        'IdProducto': set(pd.read_sql('SELECT IdProducto FROM Producto', con=engine)['IdProducto'].dropna().astype(int)),
    }

    # ==========================================
    # 3. TABLAS DEPENDIENTES (Nivel 2 - OPINIONES)
    # ==========================================
    pipe_encuestas = ensamblar_pipeline_csv("Opiniones: Encuestas", 'data/surveys_part1.csv', 'Opinion', 
                                           ['IdCliente', 'IdProducto'], es_opinion=True, id_fuente_default=2,
                                           renombrar_cols={'PuntajeSatisfacción': 'PuntajeSatisfaccion'})
    pipe_encuestas.transformer.ids_validos = ids_validos
    pipe_encuestas.ejecutar()

    pipe_social = ensamblar_pipeline_csv("Opiniones: Redes Sociales", 'data/social_comments.csv', 'Opinion', 
                                        ['IdCliente', 'IdProducto'], es_opinion=True, id_fuente_default=5,
                                        renombrar_cols={'PuntajeSatisfacción': 'PuntajeSatisfaccion'})
    pipe_social.transformer.ids_validos = ids_validos
    pipe_social.ejecutar()

    pipe_web = ensamblar_pipeline_csv("Opiniones: Reseñas Web", 'data/web_reviews.csv', 'Opinion', 
                                     ['IdCliente', 'IdProducto'], es_opinion=True, 
                                     renombrar_cols={'Rating': 'PuntajeSatisfaccion'}, id_fuente_default=1)
    pipe_web.transformer.ids_validos = ids_validos
    pipe_web.ejecutar()

    print("\nPROCESO FINALIZADO EXITOSAMENTE. 🎉")

if __name__ == "__main__": 
    main()
