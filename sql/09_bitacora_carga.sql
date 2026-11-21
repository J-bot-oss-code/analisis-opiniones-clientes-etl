/*
    09_bitacora_carga.sql
    Bitácora de la carga de dimensiones (igual que la de extracción, aquí SÍ se guarda historial):
      etl.EjecucionCarga          : una fila por corrida de cargar_dimensiones.py
      etl.DetalleCargaDimension   : una fila por dimensión en cada corrida (leídas, insertadas, actualizadas...)
    IdEjecucionExtraccion guarda de qué corrida de la extracción (etl.EjecucionExtraccion) salieron los datos.
    Se puede ejecutar varias veces sin error.
*/
USE OpinionesCliente_DW;
GO

IF OBJECT_ID('etl.EjecucionCarga', 'U') IS NULL
BEGIN
    CREATE TABLE etl.EjecucionCarga (
        IdEjecucionCarga      INT IDENTITY(1,1) NOT NULL,
        FechaInicio           DATETIME2(0)      NOT NULL,
        FechaFin              DATETIME2(0)      NULL,
        Estado                NVARCHAR(20)      NOT NULL,
        IdEjecucionExtraccion INT               NULL,
        DuracionSegundos      DECIMAL(10,3)     NULL,
        Mensaje               NVARCHAR(4000)    NULL,
        CONSTRAINT PK_EjecucionCarga PRIMARY KEY (IdEjecucionCarga),
        CONSTRAINT CK_EjecucionCarga_Estado
            CHECK (Estado IN ('EnCurso', 'Exitosa', 'Parcial', 'Fallida'))
    );
END
GO

IF OBJECT_ID('etl.DetalleCargaDimension', 'U') IS NULL
BEGIN
    CREATE TABLE etl.DetalleCargaDimension (
        IdDetalle             INT IDENTITY(1,1) NOT NULL,
        IdEjecucionCarga      INT               NOT NULL,
        Dimension             NVARCHAR(50)      NOT NULL,
        TablaDestino          NVARCHAR(128)     NOT NULL,
        Leidas                INT               NOT NULL,
        Rechazadas            INT               NOT NULL,
        Enviadas              INT               NOT NULL,   -- Leidas - Rechazadas (+1 si se agregó el miembro Desconocido)
        Insertadas            INT               NOT NULL,
        Actualizadas          INT               NOT NULL,
        SinCambios            INT               NOT NULL,
        DuracionSegundos      DECIMAL(10,3)     NOT NULL,
        Estado                NVARCHAR(20)      NOT NULL,
        Mensaje               NVARCHAR(4000)    NULL,
        CONSTRAINT PK_DetalleCargaDimension PRIMARY KEY (IdDetalle),
        CONSTRAINT FK_DetalleCargaDimension_EjecucionCarga
            FOREIGN KEY (IdEjecucionCarga) REFERENCES etl.EjecucionCarga (IdEjecucionCarga),
        CONSTRAINT CK_DetalleCargaDimension_Estado
            CHECK (Estado IN ('Exitosa', 'Fallida'))
    );
END
GO

SELECT TABLE_NAME, COUNT(*) AS Columnas
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'etl' AND TABLE_NAME IN ('EjecucionCarga', 'DetalleCargaDimension')
GROUP BY TABLE_NAME;
GO
