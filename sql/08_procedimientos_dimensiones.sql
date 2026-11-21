/*
    08_procedimientos_dimensiones.sql
    Un procedimiento almacenado por dimensión.  Todos siguen el mismo patrón:
      1) Reciben el lote en un parámetro de tipo tabla (script 07), de solo lectura.
      2) UPDATE: corrige las filas que ya existen y cambiaron (la dimensión guarda el valor más reciente).
      3) INSERT: agrega las filas cuya clave todavía no existe.
      4) Todo dentro de UNA transacción: si algo falla, no queda nada a medias.
      5) Devuelven una fila con los conteos: Leidas, Insertadas, Actualizadas y SinCambios.
    Son seguros de repetir: ejecutar el mismo lote dos veces no duplica nada
    (la segunda vez todo sale en SinCambios).
    Se puede ejecutar varias veces sin error (CREATE OR ALTER).
*/
USE OpinionesCliente_DW;
GO

/* ---------- Dim_Clasificacion ---------- */
CREATE OR ALTER PROCEDURE etl.usp_Cargar_Dim_Clasificacion
    @Datos etl.T_Dim_Clasificacion READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Leidas INT = (SELECT COUNT(*) FROM @Datos), @Insertadas INT = 0, @Actualizadas INT = 0;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE d
           SET d.Nombre = s.Nombre
          FROM dbo.Dim_Clasificacion AS d
          JOIN @Datos                AS s ON s.IdClasificacion = d.IdClasificacion
         WHERE d.Nombre <> s.Nombre;
        SET @Actualizadas = @@ROWCOUNT;

        INSERT INTO dbo.Dim_Clasificacion (IdClasificacion, Nombre)
        SELECT s.IdClasificacion, s.Nombre
          FROM @Datos AS s
         WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Clasificacion AS d WHERE d.IdClasificacion = s.IdClasificacion);
        SET @Insertadas = @@ROWCOUNT;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @Leidas AS Leidas, @Insertadas AS Insertadas, @Actualizadas AS Actualizadas,
           @Leidas - @Insertadas - @Actualizadas AS SinCambios;
END
GO

/* ---------- Dim_Cliente ---------- */
-- El correo vacío ('') llega desde Python en lugar de NULL y aquí se convierte en NULL.
CREATE OR ALTER PROCEDURE etl.usp_Cargar_Dim_Cliente
    @Datos etl.T_Dim_Cliente READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Leidas INT = (SELECT COUNT(*) FROM @Datos), @Insertadas INT = 0, @Actualizadas INT = 0;

    DECLARE @Lote TABLE (IdCliente NVARCHAR(50) NOT NULL PRIMARY KEY, Nombre NVARCHAR(100) NOT NULL, Email NVARCHAR(100) NULL);
    INSERT INTO @Lote (IdCliente, Nombre, Email)
    SELECT IdCliente, Nombre, NULLIF(LTRIM(RTRIM(Email)), N'') FROM @Datos;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE d
           SET d.Nombre = s.Nombre, d.Email = s.Email
          FROM dbo.Dim_Cliente AS d
          JOIN @Lote           AS s ON s.IdCliente = d.IdCliente
         WHERE d.Nombre <> s.Nombre OR ISNULL(d.Email, N'') <> ISNULL(s.Email, N'');
        SET @Actualizadas = @@ROWCOUNT;

        INSERT INTO dbo.Dim_Cliente (IdCliente, Nombre, Email)
        SELECT s.IdCliente, s.Nombre, s.Email
          FROM @Lote AS s
         WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Cliente AS d WHERE d.IdCliente = s.IdCliente);
        SET @Insertadas = @@ROWCOUNT;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @Leidas AS Leidas, @Insertadas AS Insertadas, @Actualizadas AS Actualizadas,
           @Leidas - @Insertadas - @Actualizadas AS SinCambios;
END
GO

/* ---------- Dim_Producto ---------- */
CREATE OR ALTER PROCEDURE etl.usp_Cargar_Dim_Producto
    @Datos etl.T_Dim_Producto READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Leidas INT = (SELECT COUNT(*) FROM @Datos), @Insertadas INT = 0, @Actualizadas INT = 0;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE d
           SET d.Nombre = s.Nombre, d.Categoria = s.Categoria
          FROM dbo.Dim_Producto AS d
          JOIN @Datos           AS s ON s.IdProducto = d.IdProducto
         WHERE d.Nombre <> s.Nombre OR d.Categoria <> s.Categoria;
        SET @Actualizadas = @@ROWCOUNT;

        INSERT INTO dbo.Dim_Producto (IdProducto, Nombre, Categoria)
        SELECT s.IdProducto, s.Nombre, s.Categoria
          FROM @Datos AS s
         WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Producto AS d WHERE d.IdProducto = s.IdProducto);
        SET @Insertadas = @@ROWCOUNT;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @Leidas AS Leidas, @Insertadas AS Insertadas, @Actualizadas AS Actualizadas,
           @Leidas - @Insertadas - @Actualizadas AS SinCambios;
END
GO

/* ---------- Dim_Fuente ---------- */
CREATE OR ALTER PROCEDURE etl.usp_Cargar_Dim_Fuente
    @Datos etl.T_Dim_Fuente READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Leidas INT = (SELECT COUNT(*) FROM @Datos), @Insertadas INT = 0, @Actualizadas INT = 0;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE d
           SET d.TipoFuente = s.TipoFuente
          FROM dbo.Dim_Fuente AS d
          JOIN @Datos         AS s ON s.IdFuente = d.IdFuente
         WHERE d.TipoFuente <> s.TipoFuente;
        SET @Actualizadas = @@ROWCOUNT;

        INSERT INTO dbo.Dim_Fuente (IdFuente, TipoFuente)
        SELECT s.IdFuente, s.TipoFuente
          FROM @Datos AS s
         WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Fuente AS d WHERE d.IdFuente = s.IdFuente);
        SET @Insertadas = @@ROWCOUNT;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @Leidas AS Leidas, @Insertadas AS Insertadas, @Actualizadas AS Actualizadas,
           @Leidas - @Insertadas - @Actualizadas AS SinCambios;
END
GO

/* ---------- Dim_Fecha ---------- */
CREATE OR ALTER PROCEDURE etl.usp_Cargar_Dim_Fecha
    @Datos etl.T_Dim_Fecha READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Leidas INT = (SELECT COUNT(*) FROM @Datos), @Insertadas INT = 0, @Actualizadas INT = 0;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE d
           SET d.Fecha = s.Fecha, d.Dia = s.Dia, d.Mes = s.Mes, d.Trimestre = s.Trimestre, d.Anio = s.Anio
          FROM dbo.Dim_Fecha AS d
          JOIN @Datos        AS s ON s.IdFecha = d.IdFecha
         WHERE d.Fecha <> s.Fecha OR d.Dia <> s.Dia OR d.Mes <> s.Mes
            OR d.Trimestre <> s.Trimestre OR d.Anio <> s.Anio;
        SET @Actualizadas = @@ROWCOUNT;

        INSERT INTO dbo.Dim_Fecha (IdFecha, Fecha, Dia, Mes, Trimestre, Anio)
        SELECT s.IdFecha, s.Fecha, s.Dia, s.Mes, s.Trimestre, s.Anio
          FROM @Datos AS s
         WHERE NOT EXISTS (SELECT 1 FROM dbo.Dim_Fecha AS d WHERE d.IdFecha = s.IdFecha);
        SET @Insertadas = @@ROWCOUNT;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @Leidas AS Leidas, @Insertadas AS Insertadas, @Actualizadas AS Actualizadas,
           @Leidas - @Insertadas - @Actualizadas AS SinCambios;
END
GO

/* ---------- Verificación: deben salir 5 procedimientos ---------- */

SELECT name AS Procedimiento
FROM sys.procedures
WHERE SCHEMA_NAME(schema_id) = 'etl' AND name LIKE 'usp[_]Cargar[_]Dim[_]%'
ORDER BY name;
GO
