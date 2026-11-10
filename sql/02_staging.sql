/*
    02_staging.sql
    Tablas staging: copia cruda de cada fuente, sin transformar.
    Reglas del contrato:
      - Columnas de datos NULL: la extracción no debe fallar por un dato malo (eso lo filtra la T).
      - Sin PK ni FK: se vacían en cada corrida y las restricciones solo frenan la inserción.
      - CSV y API se guardan como texto (NVARCHAR), porque traen IDs como 'C019' o fechas vacías.
      - Todas terminan con IdEjecucion y FechaExtraccion (auditoría del lote).
    Se pueden recrear cuando sea necesario: no guardan historial.
*/
USE OpinionesCliente_DW;
GO

/* ---------- Fuente: base de datos relacional OpinionesCliente ---------- */

DROP TABLE IF EXISTS stg.Categoria;
CREATE TABLE stg.Categoria (
    IdCategoria         INT            NULL,
    Nombre              NVARCHAR(100)  NULL,
    IdEjecucion         INT            NOT NULL,
    FechaExtraccion     DATETIME2(0)   NOT NULL
);
GO

DROP TABLE IF EXISTS stg.Clasificacion;
CREATE TABLE stg.Clasificacion (
    IdClasificacion     INT            NULL,
    Nombre              NVARCHAR(100)  NULL,
    IdEjecucion         INT            NOT NULL,
    FechaExtraccion     DATETIME2(0)   NOT NULL
);
GO

DROP TABLE IF EXISTS stg.Cliente;
CREATE TABLE stg.Cliente (
    IdCliente           INT            NULL,
    Nombre              NVARCHAR(100)  NULL,
    Email               NVARCHAR(100)  NULL,
    IdEjecucion         INT            NOT NULL,
    FechaExtraccion     DATETIME2(0)   NOT NULL
);
GO

DROP TABLE IF EXISTS stg.FuenteDatos;
CREATE TABLE stg.FuenteDatos (
    IdFuente            INT            NULL,
    TipoFuente          NVARCHAR(50)   NULL,
    FechaCarga          DATE           NULL,
    IdEjecucion         INT            NOT NULL,
    FechaExtraccion     DATETIME2(0)   NOT NULL
);
GO

DROP TABLE IF EXISTS stg.Producto;
CREATE TABLE stg.Producto (
    IdProducto          INT            NULL,
    Nombre              NVARCHAR(150)  NULL,
    IdCategoria         INT            NULL,
    IdEjecucion         INT            NOT NULL,
    FechaExtraccion     DATETIME2(0)   NOT NULL
);
GO

DROP TABLE IF EXISTS stg.Opinion;
CREATE TABLE stg.Opinion (
    IdOpinion           INT            NULL,
    IdCliente           INT            NULL,
    IdProducto          INT            NULL,
    IdClasificacion     INT            NULL,
    IdFuente            INT            NULL,
    Fecha               DATE           NULL,
    Comentario          NVARCHAR(MAX)  NULL,
    PuntajeSatisfaccion FLOAT          NULL,
    IdEjecucion         INT            NOT NULL,
    FechaExtraccion     DATETIME2(0)   NOT NULL
);
GO

/* ---------- Fuente: CSV de encuestas internas (todo texto) ---------- */

DROP TABLE IF EXISTS stg.EncuestaCSV;
CREATE TABLE stg.EncuestaCSV (
    IdOpinion           NVARCHAR(50)   NULL,
    IdCliente           NVARCHAR(50)   NULL,
    IdProducto          NVARCHAR(50)   NULL,
    Fecha               NVARCHAR(50)   NULL,
    Comentario          NVARCHAR(1000) NULL,
    Clasificacion       NVARCHAR(50)   NULL,
    PuntajeSatisfaccion NVARCHAR(50)   NULL,
    Fuente              NVARCHAR(50)   NULL,
    IdEjecucion         INT            NOT NULL,
    FechaExtraccion     DATETIME2(0)   NOT NULL
);
GO

/* ---------- Fuente: API REST de comentarios de redes sociales (todo texto) ---------- */

DROP TABLE IF EXISTS stg.ComentarioAPI;
CREATE TABLE stg.ComentarioAPI (
    IdComment           NVARCHAR(50)   NULL,
    IdCliente           NVARCHAR(50)   NULL,
    IdProducto          NVARCHAR(50)   NULL,
    Fuente              NVARCHAR(50)   NULL,
    Fecha               NVARCHAR(50)   NULL,
    Comentario          NVARCHAR(1000) NULL,
    IdEjecucion         INT            NOT NULL,
    FechaExtraccion     DATETIME2(0)   NOT NULL
);
GO

/* ---------- Verificación: deben salir 8 tablas y 51 columnas ---------- */

SELECT TABLE_NAME, COUNT(*) AS Columnas
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'stg'
GROUP BY TABLE_NAME
ORDER BY TABLE_NAME;

SELECT COUNT(DISTINCT TABLE_NAME) AS Tablas, COUNT(*) AS Columnas
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'stg';
GO
