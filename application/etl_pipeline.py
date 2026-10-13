class ETLPipeline:
    def __init__(self, nombre_proceso, extractor, transformer, loader):
        self.nombre_proceso = nombre_proceso
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader

    def ejecutar(self):
        print(f"\n{'=' * 50}\nEjecutando ETL: {self.nombre_proceso}\n{'=' * 50}")
        datos = self.extractor.extraer()
        listos, rechazados_transformacion = self.transformer.transformar(datos)
        insertados, rechazados_carga = self.loader.cargar(listos)
        rechazados = rechazados_transformacion + rechazados_carga

        print(f"Procesados: {len(datos)} | Insertados: {insertados} | Rechazados: {rechazados}")
        return {
            "procesados": len(datos),
            "insertados": insertados,
            "rechazados": rechazados,
        }
