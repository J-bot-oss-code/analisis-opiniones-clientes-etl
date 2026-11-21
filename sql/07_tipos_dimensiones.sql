/*
    07_tipos_dimensiones.sql
    Tipos de tabla (TYPE) para cargar las dimensiones.
    Un tipo de tabla es la "forma" del lote que Python le envía al procedimiento
    almacenado: así se mandan cientos de filas en UN solo viaje a SQL Server, sin
    insertar fila por fila.  Cada tipo repite las columnas de su dimensión y su
    clave primaria, de modo que un lote con claves repetidas se rechaza antes de tocar la dimensión.

    Un TYPE no se puede modificar: para cambiarlo hay que borrar primero el procedimiento
    que lo usa (script 08), borrar el tipo y volver a crear ambos.
    Se puede ejecutar varias veces sin error.
*/
USE OpinionesCliente_DW;
GO

IF TYPE_ID('etl.T_Dim_Clasificacion') IS NULL
    CREATE TYPE etl.T_Dim_Clasificacion AS TABLE (
        IdClasificacion INT           NOT NULL PRIMARY KEY,
        Nombre          NVARCHAR(20)  NOT NULL
    );
GO

IF TYPE_ID('etl.T_Dim_Cliente') IS NULL
    CREATE TYPE etl.T_Dim_Cliente AS TABLE (
        IdCliente       NVARCHAR(50)  NOT NULL PRIMARY KEY,
        Nombre          NVARCHAR(100) NOT NULL,
        Email           NVARCHAR(100) NULL
    );
GO

IF TYPE_ID('etl.T_Dim_Producto') IS NULL
    CREATE TYPE etl.T_Dim_Producto AS TABLE (
        IdProducto      NVARCHAR(50)  NOT NULL PRIMARY KEY,
        Nombre          NVARCHAR(100) NOT NULL,
        Categoria       NVARCHAR(50)  NOT NULL
    );
GO

IF TYPE_ID('etl.T_Dim_Fuente') IS NULL
    CREATE TYPE etl.T_Dim_Fuente AS TABLE (
        IdFuente        INT           NOT NULL PRIMARY KEY,
        TipoFuente      NVARCHAR(50)  NOT NULL
    );
GO

IF TYPE_ID('etl.T_Dim_Fecha') IS NULL
    CREATE TYPE etl.T_Dim_Fecha AS TABLE (
        IdFecha         INT           NOT NULL PRIMARY KEY,   -- formato AAAAMMDD, p. ej. 20250714
        Fecha           DATE          NOT NULL,
        Dia             INT           NOT NULL,
        Mes             INT           NOT NULL,
        Trimestre       INT           NOT NULL,
        Anio            INT           NOT NULL
    );
GO

/* ---------- Verificación: deben salir 5 tipos ---------- */

SELECT t.name AS Tipo, COUNT(c.column_id) AS Columnas
FROM sys.table_types AS t
JOIN sys.columns     AS c ON c.object_id = t.type_table_object_id
WHERE SCHEMA_NAME(t.schema_id) = 'etl'
GROUP BY t.name
ORDER BY t.name;
GO
