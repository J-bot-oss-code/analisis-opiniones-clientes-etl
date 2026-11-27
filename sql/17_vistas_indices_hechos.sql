/*
    17_vistas_indices_hechos.sql
    Vistas e índices del modelo dimensional (parte de análisis, no de monitoreo de la extracción).

    VISTAS (CREATE OR ALTER: se puede volver a ejecutar):
      dbo.vw_OpinionesDetalle      Fact_Opiniones con los nombres de las 5 dimensiones
      dbo.vw_ResenasDetalle        Fact_Resenas con los nombres de sus 4 dimensiones
      dbo.vw_ResumenOpiniones      total y puntaje promedio por año, fuente y clasificación
      dbo.vw_ResumenResenas        total y rating promedio por año, categoría y clasificación
      etl.vw_UltimaCarga           resultado de la última carga (dimensiones y hechos) desde la bitácora

    ÍNDICES (solo se crean si no existen):
      - Clave natural (IdOpinion / IdReview) UNIQUE: la usa el NOT EXISTS de la carga y evita duplicados.
        No se crea si la tabla ya tiene un índice que empiece por esa columna (p. ej. su clave primaria).
      - Una columna FK por índice: acelera los JOIN de las vistas y los filtros por dimensión.
        INCLUDE guarda el valor medido en el propio índice para que los resúmenes no lean la tabla.
*/
USE OpinionesCliente_DW;
GO

/* ---------------------------------- VISTAS ---------------------------------- */

CREATE OR ALTER VIEW dbo.vw_OpinionesDetalle
AS
SELECT f.IdOpinion,
       d.Fecha, d.Anio, d.Trimestre, d.Mes,
       c.IdCliente,  c.Nombre AS Cliente,
       p.IdProducto, p.Nombre AS Producto, p.Categoria,
       fu.TipoFuente AS Fuente,
       k.Nombre AS Clasificacion,
       f.PuntajeSatisfaccion
FROM dbo.Fact_Opiniones      AS f
JOIN dbo.Dim_Fecha           AS d  ON d.IdFecha           = f.IdFecha
JOIN dbo.Dim_Cliente         AS c  ON c.IdCliente         = f.IdCliente
JOIN dbo.Dim_Producto        AS p  ON p.IdProducto        = f.IdProducto
JOIN dbo.Dim_Fuente          AS fu ON fu.IdFuente         = f.IdFuente
JOIN dbo.Dim_Clasificacion   AS k  ON k.IdClasificacion   = f.IdClasificacion;
GO

CREATE OR ALTER VIEW dbo.vw_ResenasDetalle
AS
SELECT f.IdReview,
       d.Fecha, d.Anio, d.Trimestre, d.Mes,
       c.IdCliente,  c.Nombre AS Cliente,
       p.IdProducto, p.Nombre AS Producto, p.Categoria,
       k.Nombre AS Clasificacion,
       f.Rating
FROM dbo.Fact_Resenas        AS f
JOIN dbo.Dim_Fecha           AS d  ON d.IdFecha           = f.IdFecha
JOIN dbo.Dim_Cliente         AS c  ON c.IdCliente         = f.IdCliente
JOIN dbo.Dim_Producto        AS p  ON p.IdProducto        = f.IdProducto
JOIN dbo.Dim_Clasificacion   AS k  ON k.IdClasificacion   = f.IdClasificacion;
GO

CREATE OR ALTER VIEW dbo.vw_ResumenOpiniones
AS
SELECT d.Anio, fu.TipoFuente AS Fuente, k.Nombre AS Clasificacion,
       COUNT(*) AS Total,
       CAST(AVG(f.PuntajeSatisfaccion) AS DECIMAL(5,2)) AS PuntajePromedio
FROM dbo.Fact_Opiniones      AS f
JOIN dbo.Dim_Fecha           AS d  ON d.IdFecha           = f.IdFecha
JOIN dbo.Dim_Fuente          AS fu ON fu.IdFuente         = f.IdFuente
JOIN dbo.Dim_Clasificacion   AS k  ON k.IdClasificacion   = f.IdClasificacion
GROUP BY d.Anio, fu.TipoFuente, k.Nombre;
GO

CREATE OR ALTER VIEW dbo.vw_ResumenResenas
AS
SELECT d.Anio, p.Categoria, k.Nombre AS Clasificacion,
       COUNT(*) AS Total,
       CAST(AVG(CAST(f.Rating AS DECIMAL(9,2))) AS DECIMAL(5,2)) AS RatingPromedio
FROM dbo.Fact_Resenas        AS f
JOIN dbo.Dim_Fecha           AS d  ON d.IdFecha           = f.IdFecha
JOIN dbo.Dim_Producto        AS p  ON p.IdProducto        = f.IdProducto
JOIN dbo.Dim_Clasificacion   AS k  ON k.IdClasificacion   = f.IdClasificacion
GROUP BY d.Anio, p.Categoria, k.Nombre;
GO

CREATE OR ALTER VIEW etl.vw_UltimaCarga
AS
SELECT e.IdEjecucionCarga, e.FechaInicio, e.Estado AS EstadoCarga,
       e.DuracionSegundos AS DuracionTotalSegundos,
       d.Dimension AS Objeto, d.TablaDestino,
       d.Leidas, d.Rechazadas, d.Enviadas, d.Insertadas, d.Actualizadas, d.SinCambios,
       d.Estado AS EstadoObjeto, d.Mensaje
FROM etl.EjecucionCarga AS e
LEFT JOIN etl.DetalleCargaDimension AS d ON d.IdEjecucionCarga = e.IdEjecucionCarga
WHERE e.IdEjecucionCarga = (SELECT MAX(IdEjecucionCarga) FROM etl.EjecucionCarga);
GO

/* ---------------------------------- ÍNDICES ---------------------------------- */

/* Clave natural de cada hecho (única) */
IF NOT EXISTS (SELECT 1 FROM sys.index_columns ic JOIN sys.columns c
                 ON c.object_id = ic.object_id AND c.column_id = ic.column_id
               WHERE ic.object_id = OBJECT_ID('dbo.Fact_Opiniones') AND c.name = 'IdOpinion' AND ic.key_ordinal = 1)
    CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_Opiniones_IdOpinion ON dbo.Fact_Opiniones (IdOpinion);
GO
IF NOT EXISTS (SELECT 1 FROM sys.index_columns ic JOIN sys.columns c
                 ON c.object_id = ic.object_id AND c.column_id = ic.column_id
               WHERE ic.object_id = OBJECT_ID('dbo.Fact_Resenas') AND c.name = 'IdReview' AND ic.key_ordinal = 1)
    CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_Resenas_IdReview ON dbo.Fact_Resenas (IdReview);
GO

/* Fact_Opiniones: una columna FK por índice */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Opiniones_IdFecha' AND object_id = OBJECT_ID('dbo.Fact_Opiniones'))
    CREATE NONCLUSTERED INDEX IX_Fact_Opiniones_IdFecha ON dbo.Fact_Opiniones (IdFecha) INCLUDE (PuntajeSatisfaccion);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Opiniones_IdCliente' AND object_id = OBJECT_ID('dbo.Fact_Opiniones'))
    CREATE NONCLUSTERED INDEX IX_Fact_Opiniones_IdCliente ON dbo.Fact_Opiniones (IdCliente);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Opiniones_IdProducto' AND object_id = OBJECT_ID('dbo.Fact_Opiniones'))
    CREATE NONCLUSTERED INDEX IX_Fact_Opiniones_IdProducto ON dbo.Fact_Opiniones (IdProducto) INCLUDE (PuntajeSatisfaccion);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Opiniones_IdFuente' AND object_id = OBJECT_ID('dbo.Fact_Opiniones'))
    CREATE NONCLUSTERED INDEX IX_Fact_Opiniones_IdFuente ON dbo.Fact_Opiniones (IdFuente) INCLUDE (PuntajeSatisfaccion);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Opiniones_IdClasificacion' AND object_id = OBJECT_ID('dbo.Fact_Opiniones'))
    CREATE NONCLUSTERED INDEX IX_Fact_Opiniones_IdClasificacion ON dbo.Fact_Opiniones (IdClasificacion) INCLUDE (PuntajeSatisfaccion);
GO

/* Fact_Resenas: una columna FK por índice */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Resenas_IdFecha' AND object_id = OBJECT_ID('dbo.Fact_Resenas'))
    CREATE NONCLUSTERED INDEX IX_Fact_Resenas_IdFecha ON dbo.Fact_Resenas (IdFecha) INCLUDE (Rating);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Resenas_IdCliente' AND object_id = OBJECT_ID('dbo.Fact_Resenas'))
    CREATE NONCLUSTERED INDEX IX_Fact_Resenas_IdCliente ON dbo.Fact_Resenas (IdCliente);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Resenas_IdProducto' AND object_id = OBJECT_ID('dbo.Fact_Resenas'))
    CREATE NONCLUSTERED INDEX IX_Fact_Resenas_IdProducto ON dbo.Fact_Resenas (IdProducto) INCLUDE (Rating);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Resenas_IdClasificacion' AND object_id = OBJECT_ID('dbo.Fact_Resenas'))
    CREATE NONCLUSTERED INDEX IX_Fact_Resenas_IdClasificacion ON dbo.Fact_Resenas (IdClasificacion) INCLUDE (Rating);
GO

/* Verificación: índices y vistas creados */
SELECT OBJECT_NAME(i.object_id) AS Tabla, i.name AS Indice, i.type_desc AS Tipo, i.is_unique AS EsUnico
FROM sys.indexes AS i
WHERE i.object_id IN (OBJECT_ID('dbo.Fact_Opiniones'), OBJECT_ID('dbo.Fact_Resenas')) AND i.name IS NOT NULL
ORDER BY Tabla, Indice;

SELECT SCHEMA_NAME(schema_id) + '.' + name AS Vista
FROM sys.views
WHERE name IN ('vw_OpinionesDetalle', 'vw_ResenasDetalle', 'vw_ResumenOpiniones',
               'vw_ResumenResenas', 'vw_UltimaCarga')
ORDER BY Vista;               -- deben salir 5
GO
