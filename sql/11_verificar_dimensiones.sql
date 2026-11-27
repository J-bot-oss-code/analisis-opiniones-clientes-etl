/*
    11_verificar_dimensiones.sql
    Consultas de comprobación después de ejecutar:  python cargar_dimensiones.py
    (solo lectura; sirven como evidencia de la carga).
*/
USE OpinionesCliente_DW;
GO

/* 1) Filas por dimensión.  Esperado con los datos de la entrega:
      Clasificacion 3, Cliente 501, Producto 201, Fuente 101, Fecha 731
      (la primera carga incluyó la fila Desconocido, clave -1, en Cliente, Producto y Fuente).
      Después de ejecutar 19_quitar_miembro_desconocido.sql: Cliente 500, Producto 200, Fuente 100 y sin filas -1. */
SELECT 'Dim_Clasificacion' AS Dimension, COUNT(*) AS Filas FROM dbo.Dim_Clasificacion
UNION ALL SELECT 'Dim_Cliente',  COUNT(*) FROM dbo.Dim_Cliente
UNION ALL SELECT 'Dim_Producto', COUNT(*) FROM dbo.Dim_Producto
UNION ALL SELECT 'Dim_Fuente',   COUNT(*) FROM dbo.Dim_Fuente
UNION ALL SELECT 'Dim_Fecha',    COUNT(*) FROM dbo.Dim_Fecha;
GO

/* 2) Filas "Desconocido" (clave -1) */
SELECT 'Dim_Cliente' AS Dimension, IdCliente AS Clave, Nombre FROM dbo.Dim_Cliente WHERE IdCliente = N'-1'
UNION ALL SELECT 'Dim_Producto', IdProducto, Nombre FROM dbo.Dim_Producto WHERE IdProducto = N'-1'
UNION ALL SELECT 'Dim_Fuente', CAST(IdFuente AS NVARCHAR(50)), TipoFuente FROM dbo.Dim_Fuente WHERE IdFuente = -1;
GO

/* 3) Rango y consistencia de Dim_Fecha */
SELECT MIN(Fecha) AS Desde, MAX(Fecha) AS Hasta, COUNT(*) AS Dias,
       SUM(CASE WHEN IdFecha <> CONVERT(INT, CONVERT(CHAR(8), Fecha, 112)) THEN 1 ELSE 0 END) AS IdFechaIncorrecto
FROM dbo.Dim_Fecha;
GO

/* 4) Productos agrupados por categoría */
SELECT Categoria, COUNT(*) AS Productos FROM dbo.Dim_Producto GROUP BY Categoria ORDER BY Categoria;
GO

/* 5) Idempotencia: ejecute  python cargar_dimensiones.py  una segunda vez.
      Las columnas Insertadas y Actualizadas deben quedar en 0 y todo en SinCambios. */
SELECT TOP (10) c.IdEjecucionCarga, c.Estado AS EstadoCarga, c.IdEjecucionExtraccion,
       d.Dimension, d.Leidas, d.Rechazadas, d.Enviadas, d.Insertadas, d.Actualizadas, d.SinCambios, d.Estado
FROM etl.EjecucionCarga AS c
JOIN etl.DetalleCargaDimension AS d ON d.IdEjecucionCarga = c.IdEjecucionCarga
ORDER BY c.IdEjecucionCarga DESC, d.IdDetalle;
GO
