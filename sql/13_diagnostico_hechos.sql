/*
    13_diagnostico_hechos.sql
    Revisión de solo lectura antes de cargar las tablas de hechos.
    Responde: qué trae cada fuente, qué claves existen en las dimensiones y qué
    restricciones tienen Fact_Opiniones y Fact_Resenas. No modifica nada.
*/
USE OpinionesCliente_DW;
GO

/* 1. Opiniones de la base relacional, por fuente */
SELECT 'Opinion por fuente' AS Revision, o.IdFuente, f.TipoFuente, COUNT(*) AS Filas,
       SUM(CASE WHEN o.IdClasificacion IS NULL THEN 1 ELSE 0 END)       AS SinClasif,
       SUM(CASE WHEN o.PuntajeSatisfaccion IS NULL THEN 1 ELSE 0 END)   AS SinPuntaje,
       SUM(CASE WHEN o.Fecha IS NULL THEN 1 ELSE 0 END)                 AS SinFecha,
       MIN(o.Fecha) AS FechaMin, MAX(o.Fecha) AS FechaMax
FROM stg.Opinion o
LEFT JOIN dbo.Dim_Fuente f ON f.IdFuente = o.IdFuente
GROUP BY o.IdFuente, f.TipoFuente
ORDER BY o.IdFuente;

/* 2. Opiniones de la base relacional: claves que no existen en la dimensión
      (SQL Server no permite SUM sobre un CASE con subconsulta: se calcula la marca por fila y luego se suma) */
SELECT 'Opinion: sin dimension' AS Revision, COUNT(*) AS Filas,
       SUM(x.SinCliente) AS ClienteNoExiste, SUM(x.SinProducto) AS ProductoNoExiste,
       SUM(x.SinFuente)  AS FuenteNoExiste,  SUM(x.SinClasif)   AS ClasifNoExiste,
       SUM(x.SinFecha)   AS FechaNoExiste
FROM (
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Dim_Cliente c WHERE c.IdCliente = CAST(o.IdCliente AS NVARCHAR(50))) THEN 1 ELSE 0 END AS SinCliente,
           CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Dim_Producto p WHERE p.IdProducto = CAST(o.IdProducto AS NVARCHAR(50))) THEN 1 ELSE 0 END AS SinProducto,
           CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Dim_Fuente f WHERE f.IdFuente = o.IdFuente) THEN 1 ELSE 0 END AS SinFuente,
           CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Dim_Clasificacion k WHERE k.IdClasificacion = o.IdClasificacion) THEN 1 ELSE 0 END AS SinClasif,
           CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Dim_Fecha d WHERE d.Fecha = o.Fecha) THEN 1 ELSE 0 END AS SinFecha
    FROM stg.Opinion o
) AS x;

/* 3. Puntaje frente a clasificación: base relacional (arriba) y encuesta CSV (abajo) */
SELECT 'Opinion: puntaje x clasif' AS Revision, IdClasificacion, PuntajeSatisfaccion, COUNT(*) AS Filas
FROM stg.Opinion GROUP BY IdClasificacion, PuntajeSatisfaccion ORDER BY IdClasificacion, PuntajeSatisfaccion;

SELECT 'EncuestaCSV: puntaje x clasif' AS Revision, Clasificacion, PuntajeSatisfaccion, COUNT(*) AS Filas
FROM stg.EncuestaCSV GROUP BY Clasificacion, PuntajeSatisfaccion ORDER BY Clasificacion, PuntajeSatisfaccion;

/* 4. Encuesta CSV: cobertura de claves y solapamiento con la base relacional */
SELECT 'EncuestaCSV: cobertura' AS Revision, COUNT(*) AS Filas,
       SUM(x.SinCliente) AS ClienteNoExiste, SUM(x.SinProducto) AS ProductoNoExiste,
       SUM(x.SinFecha) AS FechaNoExiste, SUM(x.IdYaEnRelacional) AS IdOpinionYaEnRelacional
FROM (
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Dim_Cliente c WHERE c.IdCliente = CAST(TRY_CAST(e.IdCliente AS INT) AS NVARCHAR(50))) THEN 1 ELSE 0 END AS SinCliente,
           CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Dim_Producto p WHERE p.IdProducto = CAST(TRY_CAST(e.IdProducto AS INT) AS NVARCHAR(50))) THEN 1 ELSE 0 END AS SinProducto,
           CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Dim_Fecha d WHERE d.Fecha = TRY_CAST(e.Fecha AS DATE)) THEN 1 ELSE 0 END AS SinFecha,
           CASE WHEN EXISTS (SELECT 1 FROM stg.Opinion o WHERE o.IdOpinion = TRY_CAST(e.IdOpinion AS INT)) THEN 1 ELSE 0 END AS IdYaEnRelacional
    FROM stg.EncuestaCSV e
) AS x;

/* 4b. Encuesta CSV frente a la base relacional por CONTENIDO (cliente + producto + fecha): mismas opiniones con otro IdOpinion */
SELECT 'EncuestaCSV: repetidas en relacional' AS Revision, COUNT(*) AS Filas
FROM stg.EncuestaCSV e
WHERE EXISTS (SELECT 1 FROM stg.Opinion o
              WHERE o.IdCliente = TRY_CAST(e.IdCliente AS INT)
                AND o.IdProducto = TRY_CAST(e.IdProducto AS INT)
                AND o.Fecha = TRY_CAST(e.Fecha AS DATE));

/* 5. Restricciones y tipos de las tablas de hechos */
SELECT 'Restricciones' AS Revision, OBJECT_NAME(parent_object_id) AS Tabla, name AS Restriccion,
       'FK -> ' + OBJECT_NAME(referenced_object_id) AS Detalle
FROM sys.foreign_keys WHERE OBJECT_NAME(parent_object_id) LIKE 'Fact[_]%'
UNION ALL
SELECT 'Restricciones', OBJECT_NAME(parent_object_id), name, type_desc
FROM sys.key_constraints WHERE OBJECT_NAME(parent_object_id) LIKE 'Fact[_]%'
ORDER BY 2, 4;

SELECT 'Tipos numericos' AS Revision, TABLE_NAME, COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME LIKE 'Fact[_]%' AND (COLUMN_NAME LIKE 'Puntaje%' OR COLUMN_NAME = 'Rating');

SELECT 'Filas actuales' AS Revision,
       (SELECT COUNT(*) FROM dbo.Fact_Opiniones) AS Fact_Opiniones,
       (SELECT COUNT(*) FROM dbo.Fact_Resenas)   AS Fact_Resenas;
GO
