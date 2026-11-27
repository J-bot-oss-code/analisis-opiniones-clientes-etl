/*
    19_quitar_miembro_desconocido.sql
    Decisión revisada: es una base analítica y cada hecho debe poder analizarse por cliente y por producto,
    así que los hechos que no tengan cliente o producto válido se RECHAZAN en lugar de asignarse a "Desconocido".
    Este script borra las filas "Desconocido" (clave -1) que la carga de dimensiones había creado en
    Dim_Cliente, Dim_Producto y Dim_Fuente.  Con "MiembroDesconocido": false en appsettings.json la carga
    de dimensiones ya no las vuelve a crear.

    Seguridad: solo borra si ningún hecho usa esas filas (hoy los hechos están vacíos).  Todo en una transacción.
    Se puede ejecutar varias veces: si ya no existen, no hace nada.
    Ejecútalo con tu usuario de SSMS (el usuario del ETL no tiene permisos sobre dbo.Dim_*, a propósito).
*/
USE OpinionesCliente_DW;
GO

SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    IF EXISTS (SELECT 1 FROM dbo.Fact_Opiniones WHERE IdCliente = N'-1' OR IdProducto = N'-1' OR IdFuente = -1)
       OR EXISTS (SELECT 1 FROM dbo.Fact_Resenas WHERE IdCliente = N'-1' OR IdProducto = N'-1')
        THROW 50001, 'Hay hechos que usan el miembro Desconocido: no se borra nada.', 1;

    DELETE FROM dbo.Dim_Cliente  WHERE IdCliente  = N'-1';
    DELETE FROM dbo.Dim_Producto WHERE IdProducto = N'-1';
    DELETE FROM dbo.Dim_Fuente   WHERE IdFuente   = -1;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

/* Verificación: 500 clientes, 200 productos, 100 fuentes y ningún -1 */
SELECT 'Dim_Cliente'  AS Dimension, COUNT(*) AS Filas, SUM(CASE WHEN IdCliente  = N'-1' THEN 1 ELSE 0 END) AS Desconocidos FROM dbo.Dim_Cliente
UNION ALL
SELECT 'Dim_Producto', COUNT(*), SUM(CASE WHEN IdProducto = N'-1' THEN 1 ELSE 0 END) FROM dbo.Dim_Producto
UNION ALL
SELECT 'Dim_Fuente',   COUNT(*), SUM(CASE WHEN IdFuente   = -1   THEN 1 ELSE 0 END) FROM dbo.Dim_Fuente;
GO
