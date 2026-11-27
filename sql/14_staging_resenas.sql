/*
    14_staging_resenas.sql
    Tabla staging de las reseñas web (data/web_reviews.csv), que alimenta Fact_Resenas.
    Igual que el resto de stg.*: todo el contenido del CSV como texto, sin PK ni FK, con IdEjecucion y
    FechaExtraccion.  No borra nada: si la tabla ya existe, no hace nada (02_staging.sql también la crea
    en instalaciones nuevas).  Se puede ejecutar varias veces sin error.
*/
USE OpinionesCliente_DW;
GO

IF OBJECT_ID('stg.ResenaWeb', 'U') IS NULL
BEGIN
    CREATE TABLE stg.ResenaWeb (
        IdReview            NVARCHAR(50)   NULL,
        IdCliente           NVARCHAR(50)   NULL,
        IdProducto          NVARCHAR(50)   NULL,
        Fecha               NVARCHAR(50)   NULL,
        Comentario          NVARCHAR(1000) NULL,
        Rating              NVARCHAR(50)   NULL,
        IdEjecucion         INT            NOT NULL,
        FechaExtraccion     DATETIME2(0)   NOT NULL
    );
    PRINT 'stg.ResenaWeb creada.';
END
ELSE
    PRINT 'stg.ResenaWeb ya existía.';
GO

SELECT TABLE_NAME, COUNT(*) AS Columnas
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'stg' AND TABLE_NAME = 'ResenaWeb'
GROUP BY TABLE_NAME;          -- debe salir 8 columnas
GO
