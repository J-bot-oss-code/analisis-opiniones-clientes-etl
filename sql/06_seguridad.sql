/*
    06_seguridad.sql
    Usuario dedicado para el worker con el mínimo privilegio:
      - OpinionesCliente     : solo lectura
      - OpinionesCliente_DW  : escritura solo en los esquemas stg y etl
    LOGIN = acceso al servidor (se crea en master).
    USER  = permisos dentro de cada base (se crea en cada una).

    ANTES DE EJECUTAR: cambia la clave de la línea marcada y NO guardes el archivo con ella.
    La clave real va únicamente en config/.env (excluido de Git).
*/

/* ---------- 0) Modo de autenticación del servidor ---------- */
SELECT CASE SERVERPROPERTY('IsIntegratedSecurityOnly')
            WHEN 1 THEN 'Solo Windows: active la autenticación mixta para poder iniciar sesión con este login'
            ELSE 'Mixta: SQL Server y Windows' END AS ModoAutenticacion;
GO

/* ---------- 1) Login en el servidor ---------- */
USE master;
GO

DECLARE @clave NVARCHAR(128) = N'ESCRIBE_AQUI_LA_CLAVE';     -- <<< cambia esta clave al ejecutar

IF @clave = N'ESCRIBE_AQUI_LA_CLAVE'
BEGIN
    PRINT 'Cambia la clave antes de ejecutar. No se ejecutó nada más.';
    SET NOEXEC ON;      -- detiene todos los lotes siguientes de este script
END
ELSE IF SUSER_ID('etl_extractor') IS NULL
BEGIN
    -- CREATE LOGIN no acepta variables: se arma con SQL dinámico y QUOTENAME para escapar la clave.
    DECLARE @sql NVARCHAR(400) =
        N'CREATE LOGIN etl_extractor WITH PASSWORD = ' + QUOTENAME(@clave, '''')
        + N', CHECK_POLICY = ON, DEFAULT_DATABASE = OpinionesCliente_DW;';
    EXEC (@sql);
    PRINT 'Login etl_extractor creado.';
END
GO

/* ---------- 2) Origen: solo lectura ---------- */
USE OpinionesCliente;
GO

IF USER_ID('etl_extractor') IS NULL
    CREATE USER etl_extractor FOR LOGIN etl_extractor;
ALTER ROLE db_datareader ADD MEMBER etl_extractor;
GO

/* ---------- 3) Data Warehouse: escritura solo en stg y etl ---------- */
USE OpinionesCliente_DW;
GO

IF USER_ID('etl_extractor') IS NULL
    CREATE USER etl_extractor FOR LOGIN etl_extractor;

GRANT SELECT, INSERT, DELETE, ALTER ON SCHEMA::stg TO etl_extractor;   -- ALTER es necesario para TRUNCATE
GRANT SELECT, INSERT, UPDATE        ON SCHEMA::etl TO etl_extractor;   -- bitácora: insertar y cerrar corridas
GO

/* ---------- 4) Pruebas de mínimo privilegio (evidencia para el documento) ---------- */
USE OpinionesCliente;
EXECUTE AS USER = 'etl_extractor';
    SELECT TOP 3 IdOpinion, Fecha FROM dbo.Opinion;                         -- debe funcionar
    BEGIN TRY
        DELETE FROM dbo.Opinion WHERE 1 = 0;
        PRINT 'FALLO: puede borrar en el origen';
    END TRY
    BEGIN CATCH
        PRINT 'OK origen: no puede borrar -> ' + ERROR_MESSAGE();
    END CATCH;
REVERT;
GO

USE OpinionesCliente_DW;
EXECUTE AS USER = 'etl_extractor';
    SELECT COUNT(*) AS FilasStgOpinion FROM stg.Opinion;                    -- debe funcionar
    BEGIN TRY
        SELECT TOP 1 * FROM dbo.Dim_Cliente;
        PRINT 'FALLO: puede leer las dimensiones';
    END TRY
    BEGIN CATCH
        PRINT 'OK DW: no puede leer dbo -> ' + ERROR_MESSAGE();
    END CATCH;
    BEGIN TRY
        EXEC ('CREATE TABLE dbo.PruebaPermisos (x INT);');
        PRINT 'FALLO: puede crear tablas';
    END TRY
    BEGIN CATCH
        PRINT 'OK DW: no puede crear tablas -> ' + ERROR_MESSAGE();
    END CATCH;
REVERT;
GO

SET NOEXEC OFF;     -- deja la sesión normal aunque se haya detenido arriba
GO
