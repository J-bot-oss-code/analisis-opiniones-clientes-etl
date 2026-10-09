from application.interfaces import IExtractor, ITransformer, ILoader

class ETLPipeline:
    def __init__(self, nombre_proceso: str, extractor: IExtractor, transformer: ITransformer, loader: ILoader):
        self.nombre_proceso = nombre_proceso
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader

    def ejecutar(self):
        print(f"\n{'='*50}\nEjecutando Pipeline: {self.nombre_proceso}\n{'='*50}")
        
        # 1. Extracción
        df_crudo = self.extractor.extraer()
        total_leidos = len(df_crudo)
        
        # 2. Transformación
        df_limpio, rechazados_transformacion = self.transformer.transformar(df_crudo)
        
        # 3. Carga
        insertados, rechazados_bd = self.loader.cargar(df_limpio)
        
        # Resumen Final
        total_rechazados = rechazados_transformacion + rechazados_bd
        self._imprimir_resumen(total_leidos, insertados, total_rechazados)

    def _imprimir_resumen(self, leidos: int, insertados: int, rechazados: int):
        print("-" * 50)
        print(f"RESUMEN ETL: {self.nombre_proceso}")
        print(f" -> Procesados (Leídos): {leidos}")
        print(f" -> Insertados:         {insertados}")
        print(f" -> Rechazados:         {rechazados}")
        print("-" * 50)