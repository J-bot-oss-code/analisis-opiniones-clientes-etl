/*
    10_permisos_carga.sql
    El usuario etl_extractor (script 06) puede cargar las dimensiones SIN poder tocar dbo directamente:
      - EXECUTE sobre el esquema etl y sobre cada tipo T_Dim_*: puede llamar a los procedimientos
        usp_Cargar_Dim_* y enviarles un lote como parámetro de tipo tabla.
      - Los procedimientos escriben en dbo.Dim_* gracias al "encadenamiento de propiedad":
        etl, stg y dbo pertenecen al mismo dueño (dbo), así que SQL Server no vuelve a pedir
        permisos sobre las tablas dentro del procedimiento.
      - SELECT/INSERT/UPDATE sobre etl (script 06) ya cubre las tablas de bitácora nuevas.
    Resultado: sigue sin poder leer ni escribir dbo.Dim_* por su cuenta (mínimo privilegio).
    Se puede ejecutar varias veces sin error.
*/
USE OpinionesCliente_DW;
GO

GRANT EXECUTE ON SCHEMA::etl TO etl_extractor;
GRANT EXECUTE ON TYPE::etl.T_Dim_Clasificacion TO etl_extractor;
GRANT EXECUTE ON TYPE::etl.T_Dim_Cliente       TO etl_extractor;
GRANT EXECUTE ON TYPE::etl.T_Dim_Producto      TO etl_extractor;
GRANT EXECUTE ON TYPE::etl.T_Dim_Fuente        TO etl_extractor;
GRANT EXECUTE ON TYPE::etl.T_Dim_Fecha         TO etl_extractor;
GO

/* ---------- Pruebas de mínimo privilegio (evidencia para el documento) ---------- */
EXECUTE AS USER = 'etl_extractor';

BEGIN TRY
    INSERT INTO dbo.Dim_Clasificacion (IdClasificacion, Nombre) VALUES (-999, N'Prueba');
    PRINT 'FALLO: puede insertar directamente en la dimension';
END TRY
BEGIN CATCH
    PRINT 'OK: no puede escribir en dbo.Dim_* por su cuenta -> ' + ERROR_MESSAGE();
END CATCH;

BEGIN TRY
    DECLARE @vacio etl.T_Dim_Clasificacion;
    EXEC etl.usp_Cargar_Dim_Clasificacion @Datos = @vacio;   -- lote vacío: no cambia nada
    PRINT 'OK: si puede ejecutar el procedimiento de carga';
END TRY
BEGIN CATCH
    PRINT 'FALLO: no puede ejecutar el procedimiento -> ' + ERROR_MESSAGE();
END CATCH;

REVERT;
GO
