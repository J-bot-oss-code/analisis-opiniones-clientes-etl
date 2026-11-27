/*
    15_tipos_hechos.sql
    Tipos de tabla (TYPE) para cargar las tablas de hechos: la "forma" del lote que Python le envía
    a cada procedimiento almacenado (parámetro de tipo tabla, TVP).  Repiten las columnas de
    dbo.Fact_Opiniones y dbo.Fact_Resenas; la clave primaria del tipo rechaza un lote con la misma
    opinión o reseña repetida antes de tocar la tabla de hechos.

    PuntajeSatisfaccion es DECIMAL(3,2), igual que la columna de la tabla destino (se verificó en el script 13).
    Un TYPE no se puede modificar: para cambiarlo hay que borrar primero el procedimiento que lo usa
    (script 16), borrar el tipo y volver a crear ambos.  Se puede ejecutar varias veces sin error.
*/
USE OpinionesCliente_DW;
GO

IF TYPE_ID('etl.T_Fact_Opiniones') IS NULL
    CREATE TYPE etl.T_Fact_Opiniones AS TABLE (
        IdOpinion           NVARCHAR(50)  NOT NULL PRIMARY KEY,
        IdCliente           NVARCHAR(50)  NOT NULL,
        IdProducto          NVARCHAR(50)  NOT NULL,
        IdFuente            INT           NOT NULL,
        IdClasificacion     INT           NOT NULL,
        IdFecha             INT           NOT NULL,
        PuntajeSatisfaccion DECIMAL(3,2)  NOT NULL
    );
GO

IF TYPE_ID('etl.T_Fact_Resenas') IS NULL
    CREATE TYPE etl.T_Fact_Resenas AS TABLE (
        IdReview            NVARCHAR(50)  NOT NULL PRIMARY KEY,
        IdCliente           NVARCHAR(50)  NOT NULL,
        IdProducto          NVARCHAR(50)  NOT NULL,
        IdFecha             INT           NOT NULL,
        IdClasificacion     INT           NOT NULL,
        Rating              INT           NOT NULL
    );
GO

/* Permiso para usar los tipos desde Python (usuario del ETL). Si el usuario no existe, no hace nada. */
IF DATABASE_PRINCIPAL_ID('etl_extractor') IS NOT NULL
BEGIN
    GRANT EXECUTE ON TYPE::etl.T_Fact_Opiniones TO etl_extractor;
    GRANT EXECUTE ON TYPE::etl.T_Fact_Resenas   TO etl_extractor;
END
GO

SELECT name AS Tipo, is_table_type AS EsTipoTabla
FROM sys.types
WHERE schema_id = SCHEMA_ID('etl') AND name LIKE 'T[_]Fact[_]%'
ORDER BY name;                -- deben salir 2
GO
