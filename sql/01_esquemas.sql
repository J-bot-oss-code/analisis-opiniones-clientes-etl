/*
    01_esquemas.sql
    Crea los esquemas de la zona de extracción en el Data Warehouse.
      stg = datos crudos extraídos (staging)
      etl = bitácora del proceso
    Se puede ejecutar varias veces sin error.
*/
USE OpinionesCliente_DW;
GO

IF SCHEMA_ID('stg') IS NULL EXEC('CREATE SCHEMA stg');
IF SCHEMA_ID('etl') IS NULL EXEC('CREATE SCHEMA etl');
GO

SELECT name FROM sys.schemas WHERE name IN ('stg', 'etl');
GO
