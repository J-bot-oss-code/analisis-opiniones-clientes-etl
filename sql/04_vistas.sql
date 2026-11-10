/*
    04_vistas.sql
    Vistas de monitoreo de la extracción (en OpinionesCliente_DW).
    CREATE OR ALTER permite volver a ejecutar el script sin error.
*/
USE OpinionesCliente_DW;
GO

/* a) La última corrida del worker con el detalle de cada tabla */
CREATE OR ALTER VIEW etl.vw_UltimaEjecucion
AS
SELECT
    e.IdEjecucion,
    e.FechaInicio,
    e.FechaFin,
    e.Estado            AS EstadoEjecucion,
    e.FilasTotales,
    e.DuracionSegundos  AS DuracionTotalSegundos,
    d.Fuente,
    d.TablaDestino,
    d.Filas,
    d.DuracionSegundos,
    d.Estado            AS EstadoTabla,
    d.Mensaje
FROM etl.EjecucionExtraccion AS e
LEFT JOIN etl.DetalleExtraccion AS d
    ON d.IdEjecucion = e.IdEjecucion
WHERE e.IdEjecucion = (SELECT MAX(IdEjecucion) FROM etl.EjecucionExtraccion);
GO

/* b) Filas en cada tabla staging comparadas con el origen (nombre de 3 partes: BD.esquema.tabla) */
CREATE OR ALTER VIEW etl.vw_ConteoStaging
AS
SELECT
    t.Tabla,
    t.Fuente,
    t.FilasStaging,
    t.FilasOrigen,
    t.FilasStaging - t.FilasOrigen AS Diferencia      -- 0 = se extrajo todo
FROM (
    SELECT 'stg.Categoria' AS Tabla, 'BD' AS Fuente,
           (SELECT COUNT_BIG(*) FROM stg.Categoria)                         AS FilasStaging,
           (SELECT COUNT_BIG(*) FROM OpinionesCliente.dbo.Categoria)        AS FilasOrigen
    UNION ALL
    SELECT 'stg.Clasificacion', 'BD',
           (SELECT COUNT_BIG(*) FROM stg.Clasificacion),
           (SELECT COUNT_BIG(*) FROM OpinionesCliente.dbo.Clasificacion)
    UNION ALL
    SELECT 'stg.Cliente', 'BD',
           (SELECT COUNT_BIG(*) FROM stg.Cliente),
           (SELECT COUNT_BIG(*) FROM OpinionesCliente.dbo.Cliente)
    UNION ALL
    SELECT 'stg.FuenteDatos', 'BD',
           (SELECT COUNT_BIG(*) FROM stg.FuenteDatos),
           (SELECT COUNT_BIG(*) FROM OpinionesCliente.dbo.FuenteDatos)
    UNION ALL
    SELECT 'stg.Producto', 'BD',
           (SELECT COUNT_BIG(*) FROM stg.Producto),
           (SELECT COUNT_BIG(*) FROM OpinionesCliente.dbo.Producto)
    UNION ALL
    SELECT 'stg.Opinion', 'BD',
           (SELECT COUNT_BIG(*) FROM stg.Opinion),
           (SELECT COUNT_BIG(*) FROM OpinionesCliente.dbo.Opinion)
    UNION ALL
    SELECT 'stg.EncuestaCSV', 'CSV',
           (SELECT COUNT_BIG(*) FROM stg.EncuestaCSV), NULL              -- sin tabla de origen
    UNION ALL
    SELECT 'stg.ComentarioAPI', 'API',
           (SELECT COUNT_BIG(*) FROM stg.ComentarioAPI), NULL
) AS t;
GO

/* c) Rendimiento de cada corrida: evidencia del requisito "50,000 comentarios en menos de 5 minutos" */
CREATE OR ALTER VIEW etl.vw_RendimientoEjecuciones
AS
SELECT
    IdEjecucion,
    FechaInicio,
    FechaFin,
    Estado,
    FilasTotales,
    DuracionSegundos,
    CAST(FilasTotales / NULLIF(DuracionSegundos, 0) AS DECIMAL(12,1)) AS FilasPorSegundo,  -- NULLIF evita dividir entre 0
    CASE WHEN DuracionSegundos < 300 THEN 'Sí' ELSE 'No' END            AS MenosDe5Minutos
FROM etl.EjecucionExtraccion
WHERE Estado <> 'EnCurso';
GO

/* Prueba de las vistas (el ORDER BY va al consultar, no dentro de la vista) */
SELECT * FROM etl.vw_UltimaEjecucion ORDER BY TablaDestino;
SELECT * FROM etl.vw_ConteoStaging ORDER BY Tabla;
SELECT * FROM etl.vw_RendimientoEjecuciones ORDER BY IdEjecucion DESC;
GO
