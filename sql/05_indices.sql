/*
    05_indices.sql
    Índices de la bitácora (DW) y uno opcional en el origen.
    Las tablas stg.* quedan SIN índices a propósito (heaps): se vacían y llenan
    en cada corrida, e insertar en un heap es lo más rápido.
*/
USE OpinionesCliente_DW;
GO

/* La FK IdEjecucion no tiene índice automático en SQL Server: se crea a mano.
   INCLUDE = índice de cobertura: la vista de la última ejecución lee todo desde el índice. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = 'IX_DetalleExtraccion_IdEjecucion'
                 AND object_id = OBJECT_ID('etl.DetalleExtraccion'))
    CREATE NONCLUSTERED INDEX IX_DetalleExtraccion_IdEjecucion
        ON etl.DetalleExtraccion (IdEjecucion)
        INCLUDE (Fuente, TablaDestino, Filas, DuracionSegundos, Estado);
GO

/* Para encontrar rápido las corridas más recientes */
IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = 'IX_EjecucionExtraccion_FechaInicio'
                 AND object_id = OBJECT_ID('etl.EjecucionExtraccion'))
    CREATE NONCLUSTERED INDEX IX_EjecucionExtraccion_FechaInicio
        ON etl.EjecucionExtraccion (FechaInicio DESC)
        INCLUDE (Estado, FilasTotales, DuracionSegundos);
GO

/* Opcional, en el ORIGEN: prepara una futura extracción incremental por fecha */
USE OpinionesCliente;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = 'IX_Opinion_Fecha'
                 AND object_id = OBJECT_ID('dbo.Opinion'))
    CREATE NONCLUSTERED INDEX IX_Opinion_Fecha
        ON dbo.Opinion (Fecha);
GO

/* Verificación: lista los índices creados en cada base */
USE OpinionesCliente_DW;
SELECT OBJECT_SCHEMA_NAME(i.object_id) + '.' + OBJECT_NAME(i.object_id) AS Tabla,
       i.name AS Indice, i.type_desc AS Tipo
FROM sys.indexes AS i
WHERE OBJECT_SCHEMA_NAME(i.object_id) IN ('etl', 'stg')
ORDER BY Tabla, Indice;          -- las stg.* aparecen como HEAP

USE OpinionesCliente;
SELECT name AS Indice, type_desc AS Tipo
FROM sys.indexes
WHERE object_id = OBJECT_ID('dbo.Opinion');
GO
