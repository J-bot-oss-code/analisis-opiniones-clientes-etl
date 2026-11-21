/*
    12_muestra_dimensiones.sql
    Muestra el contenido real de las 5 dimensiones cargadas (primeras filas de cada una).
    Sirve de evidencia de "tablas cargadas". Solo consulta; no modifica nada.
    Las claves de texto se ordenan como texto: por eso el miembro Desconocido (-1) sale primero.
*/
USE OpinionesCliente_DW;
GO

SELECT 'Dim_Clasificacion' AS Tabla, * FROM dbo.Dim_Clasificacion ORDER BY IdClasificacion;

SELECT TOP 6 'Dim_Cliente' AS Tabla, * FROM dbo.Dim_Cliente ORDER BY IdCliente;

SELECT TOP 6 'Dim_Producto' AS Tabla, * FROM dbo.Dim_Producto ORDER BY IdProducto;

SELECT TOP 6 'Dim_Fuente' AS Tabla, * FROM dbo.Dim_Fuente ORDER BY IdFuente;

SELECT TOP 6 'Dim_Fecha' AS Tabla, * FROM dbo.Dim_Fecha ORDER BY IdFecha;
GO
