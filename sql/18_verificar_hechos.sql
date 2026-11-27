/*
    18_verificar_hechos.sql
    Verificación de la carga de hechos (solo consulta; se puede ejecutar cuantas veces quieras).
    Cada resultado empieza con la columna Revision para identificarlo en la captura.
*/
USE OpinionesCliente_DW;
GO

/* 1. Filas cargadas */
SELECT 'Filas por hecho' AS Revision,
       (SELECT COUNT(*) FROM dbo.Fact_Opiniones) AS Fact_Opiniones,
       (SELECT COUNT(*) FROM dbo.Fact_Resenas)   AS Fact_Resenas;

/* 2. Integridad: hechos cuya clave NO existe en la dimensión (todo debe ser 0) */
SELECT 'Huerfanos Fact_Opiniones' AS Revision,
       (SELECT COUNT(*) FROM dbo.Fact_Opiniones f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Cliente d        WHERE d.IdCliente = f.IdCliente))               AS SinCliente,
       (SELECT COUNT(*) FROM dbo.Fact_Opiniones f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Producto d       WHERE d.IdProducto = f.IdProducto))             AS SinProducto,
       (SELECT COUNT(*) FROM dbo.Fact_Opiniones f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Fuente d         WHERE d.IdFuente = f.IdFuente))                 AS SinFuente,
       (SELECT COUNT(*) FROM dbo.Fact_Opiniones f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Clasificacion d  WHERE d.IdClasificacion = f.IdClasificacion))   AS SinClasificacion,
       (SELECT COUNT(*) FROM dbo.Fact_Opiniones f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Fecha d          WHERE d.IdFecha = f.IdFecha))                   AS SinFecha;

SELECT 'Huerfanos Fact_Resenas' AS Revision,
       (SELECT COUNT(*) FROM dbo.Fact_Resenas f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Cliente d        WHERE d.IdCliente = f.IdCliente))               AS SinCliente,
       (SELECT COUNT(*) FROM dbo.Fact_Resenas f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Producto d       WHERE d.IdProducto = f.IdProducto))             AS SinProducto,
       (SELECT COUNT(*) FROM dbo.Fact_Resenas f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Clasificacion d  WHERE d.IdClasificacion = f.IdClasificacion))   AS SinClasificacion,
       (SELECT COUNT(*) FROM dbo.Fact_Resenas f WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Fecha d          WHERE d.IdFecha = f.IdFecha))                   AS SinFecha;

/* 3. Duplicados en la clave natural (deben ser 0) */
SELECT 'Duplicados' AS Revision,
       (SELECT COUNT(*) - COUNT(DISTINCT IdOpinion) FROM dbo.Fact_Opiniones) AS Fact_Opiniones,
       (SELECT COUNT(*) - COUNT(DISTINCT IdReview)  FROM dbo.Fact_Resenas)   AS Fact_Resenas;

/* 4. Ningún hecho debe usar el miembro "Desconocido" (-1): todo se puede analizar por cliente y producto (todo en 0) */
SELECT 'Desconocidos (debe ser 0)' AS Revision, 'Fact_Opiniones' AS Hecho, COUNT(*) AS Filas,
       SUM(CASE WHEN IdCliente = N'-1'  THEN 1 ELSE 0 END) AS ClienteDesconocido,
       SUM(CASE WHEN IdProducto = N'-1' THEN 1 ELSE 0 END) AS ProductoDesconocido,
       SUM(CASE WHEN IdFuente = -1      THEN 1 ELSE 0 END) AS FuenteDesconocida
FROM dbo.Fact_Opiniones
UNION ALL
SELECT 'Desconocidos (debe ser 0)', 'Fact_Resenas', COUNT(*),
       SUM(CASE WHEN IdCliente = N'-1'  THEN 1 ELSE 0 END),
       SUM(CASE WHEN IdProducto = N'-1' THEN 1 ELSE 0 END), 0
FROM dbo.Fact_Resenas;

/* 5. Resumen desde las vistas (primeras filas) */
SELECT TOP 8 'vw_ResumenOpiniones' AS Revision, * FROM dbo.vw_ResumenOpiniones ORDER BY Anio, Fuente, Clasificacion;
SELECT TOP 8 'vw_ResumenResenas'   AS Revision, * FROM dbo.vw_ResumenResenas   ORDER BY Anio, Categoria, Clasificacion;
SELECT TOP 5 'vw_OpinionesDetalle' AS Revision, * FROM dbo.vw_OpinionesDetalle ORDER BY IdOpinion;
SELECT TOP 5 'vw_ResenasDetalle'   AS Revision, * FROM dbo.vw_ResenasDetalle   ORDER BY IdReview;

/* 6. Bitácora de la última carga (dimensiones y hechos) */
SELECT 'Ultima carga' AS Revision, IdEjecucionCarga, EstadoCarga, Objeto, Leidas, Rechazadas, Enviadas,
       Insertadas, SinCambios AS YaExistian, EstadoObjeto
FROM etl.vw_UltimaCarga ORDER BY Objeto;

/* 7. Historial reciente de la bitácora: la 2.ª corrida debe mostrar 0 insertadas y todo "YaExistian" */
SELECT TOP 12 'Historial' AS Revision, IdEjecucionCarga, Dimension AS Objeto, Leidas, Rechazadas,
       Insertadas, SinCambios AS YaExistian, Estado
FROM etl.DetalleCargaDimension ORDER BY IdDetalle DESC;
GO
