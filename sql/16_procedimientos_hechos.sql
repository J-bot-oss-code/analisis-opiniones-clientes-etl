/*
    16_procedimientos_hechos.sql
    Un procedimiento por tabla de hechos.  Reciben el lote en un parámetro de tipo tabla (script 15) y
    hacen un INSERT ... SELECT ... WHERE NOT EXISTS: solo se agrega lo que todavía no está en el hecho
    (clave natural IdOpinion / IdReview).  Una tabla de hechos registra algo que ya ocurrió, así que NO se
    actualiza: lo que ya existe se cuenta como "SinCambios" (ya existía).

    Para que dos corridas simultáneas no inserten la misma clave, la subconsulta lleva
    WITH (UPDLOCK, HOLDLOCK) (bloqueo del rango de la clave mientras dura la transacción).
    Todo ocurre en una transacción: si algo falla se revierte (ROLLBACK) y se relanza el error.
    Devuelven Leidas, Insertadas, Actualizadas (siempre 0) y SinCambios, igual que las dimensiones.
    Las claves ya vienen validadas contra las dimensiones desde Python (application/fact_preparation.py).
    CREATE OR ALTER permite volver a ejecutar el script sin error.
*/
USE OpinionesCliente_DW;
GO

CREATE OR ALTER PROCEDURE etl.usp_Cargar_Fact_Opiniones
    @Datos etl.T_Fact_Opiniones READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @Leidas INT = (SELECT COUNT(*) FROM @Datos), @Insertadas INT = 0;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO dbo.Fact_Opiniones
            (IdOpinion, IdCliente, IdProducto, IdFuente, IdClasificacion, IdFecha, PuntajeSatisfaccion)
        SELECT s.IdOpinion, s.IdCliente, s.IdProducto, s.IdFuente, s.IdClasificacion, s.IdFecha, s.PuntajeSatisfaccion
        FROM @Datos AS s
        WHERE NOT EXISTS (
            SELECT 1
            FROM dbo.Fact_Opiniones AS f WITH (UPDLOCK, HOLDLOCK)
            WHERE f.IdOpinion = s.IdOpinion
        );
        SET @Insertadas = @@ROWCOUNT;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @Leidas AS Leidas, @Insertadas AS Insertadas, 0 AS Actualizadas,
           @Leidas - @Insertadas AS SinCambios;
END;
GO

CREATE OR ALTER PROCEDURE etl.usp_Cargar_Fact_Resenas
    @Datos etl.T_Fact_Resenas READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @Leidas INT = (SELECT COUNT(*) FROM @Datos), @Insertadas INT = 0;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO dbo.Fact_Resenas
            (IdReview, IdCliente, IdProducto, IdFecha, IdClasificacion, Rating)
        SELECT s.IdReview, s.IdCliente, s.IdProducto, s.IdFecha, s.IdClasificacion, s.Rating
        FROM @Datos AS s
        WHERE NOT EXISTS (
            SELECT 1
            FROM dbo.Fact_Resenas AS f WITH (UPDLOCK, HOLDLOCK)
            WHERE f.IdReview = s.IdReview
        );
        SET @Insertadas = @@ROWCOUNT;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @Leidas AS Leidas, @Insertadas AS Insertadas, 0 AS Actualizadas,
           @Leidas - @Insertadas AS SinCambios;
END;
GO

SELECT name AS Procedimiento, create_date AS Creado, modify_date AS Modificado
FROM sys.procedures
WHERE schema_id = SCHEMA_ID('etl') AND name LIKE 'usp[_]Cargar[_]Fact[_]%'
ORDER BY name;                -- deben salir 2
GO
