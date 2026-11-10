/*
    03_bitacora.sql
    Bitácora del proceso de extracción. A diferencia de staging, aquí SÍ se
    guarda historial, por eso lleva PK, FK y CHECK, y NO se borra al reejecutar.
      etl.EjecucionExtraccion : una fila por corrida del worker
      etl.DetalleExtraccion   : una fila por tabla extraída en cada corrida
*/
USE OpinionesCliente_DW;
GO

IF OBJECT_ID('etl.EjecucionExtraccion', 'U') IS NULL
BEGIN
    CREATE TABLE etl.EjecucionExtraccion (
        IdEjecucion       INT IDENTITY(1,1) NOT NULL,
        FechaInicio       DATETIME2(0)      NOT NULL,
        FechaFin          DATETIME2(0)      NULL,
        Estado            NVARCHAR(20)      NOT NULL,
        FilasTotales      INT               NULL,
        DuracionSegundos  DECIMAL(10,3)     NULL,
        Mensaje           NVARCHAR(4000)    NULL,
        CONSTRAINT PK_EjecucionExtraccion PRIMARY KEY (IdEjecucion),
        CONSTRAINT CK_EjecucionExtraccion_Estado
            CHECK (Estado IN ('EnCurso', 'Exitosa', 'Parcial', 'Fallida'))
    );
END
GO

IF OBJECT_ID('etl.DetalleExtraccion', 'U') IS NULL
BEGIN
    CREATE TABLE etl.DetalleExtraccion (
        IdDetalle         INT IDENTITY(1,1) NOT NULL,
        IdEjecucion       INT               NOT NULL,
        Fuente            NVARCHAR(20)      NOT NULL,
        TablaDestino      NVARCHAR(128)     NOT NULL,
        Filas             INT               NOT NULL,
        DuracionSegundos  DECIMAL(10,3)     NOT NULL,
        Estado            NVARCHAR(20)      NOT NULL,
        Mensaje           NVARCHAR(4000)    NULL,
        CONSTRAINT PK_DetalleExtraccion PRIMARY KEY (IdDetalle),
        CONSTRAINT FK_DetalleExtraccion_EjecucionExtraccion
            FOREIGN KEY (IdEjecucion) REFERENCES etl.EjecucionExtraccion (IdEjecucion),
        CONSTRAINT CK_DetalleExtraccion_Fuente
            CHECK (Fuente IN ('BD', 'CSV', 'API')),
        CONSTRAINT CK_DetalleExtraccion_Estado
            CHECK (Estado IN ('Exitosa', 'Fallida'))
    );
END
GO

/* ---------- Verificación: el primer INSERT funciona, el segundo debe fallar por el CHECK ---------- */

BEGIN TRANSACTION;

INSERT INTO etl.EjecucionExtraccion (FechaInicio, Estado)
OUTPUT INSERTED.IdEjecucion
VALUES (SYSDATETIME(), 'EnCurso');

BEGIN TRY
    INSERT INTO etl.EjecucionExtraccion (FechaInicio, Estado)
    VALUES (SYSDATETIME(), 'Terminada');
    PRINT 'ERROR: el CHECK no bloqueó un estado inválido';
END TRY
BEGIN CATCH
    PRINT 'OK: el CHECK bloqueó el estado inválido -> ' + ERROR_MESSAGE();
END CATCH;

ROLLBACK;   -- no deja filas de prueba (el IDENTITY sí avanza, eso es normal)
GO
