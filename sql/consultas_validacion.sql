USE OpinionesCliente;
GO

/*
    Consultas de validación del proceso ETL.
    Ejecutar después de cargar los CSV. Las consultas de integridad deben
    devolver cero filas o cero registros inválidos.
*/

-- 1. Cantidad de registros cargados en cada tabla.
SELECT 'Categoria' AS Tabla, COUNT_BIG(*) AS Registros FROM dbo.Categoria
UNION ALL
SELECT 'Clasificacion', COUNT_BIG(*) FROM dbo.Clasificacion
UNION ALL
SELECT 'Cliente', COUNT_BIG(*) FROM dbo.Cliente
UNION ALL
SELECT 'FuenteDatos', COUNT_BIG(*) FROM dbo.FuenteDatos
UNION ALL
SELECT 'Producto', COUNT_BIG(*) FROM dbo.Producto
UNION ALL
SELECT 'Opinion', COUNT_BIG(*) FROM dbo.Opinion;
GO

-- 2. Opiniones que apuntan a clientes, productos, fuentes o clasificaciones inexistentes.
--    Debe devolver 0.
SELECT
    o.IdOpinion,
    o.IdCliente,
    o.IdProducto,
    o.IdFuente,
    o.IdClasificacion
FROM dbo.Opinion AS o
LEFT JOIN dbo.Cliente AS c ON c.IdCliente = o.IdCliente
LEFT JOIN dbo.Producto AS p ON p.IdProducto = o.IdProducto
LEFT JOIN dbo.FuenteDatos AS f ON f.IdFuente = o.IdFuente
LEFT JOIN dbo.Clasificacion AS cl ON cl.IdClasificacion = o.IdClasificacion
WHERE c.IdCliente IS NULL
   OR p.IdProducto IS NULL
   OR (o.IdFuente IS NOT NULL AND f.IdFuente IS NULL)
   OR (o.IdClasificacion IS NOT NULL AND cl.IdClasificacion IS NULL);
GO

-- 3. Productos que apuntan a categorías inexistentes.
--    Debe devolver 0.
SELECT p.IdProducto, p.Nombre, p.IdCategoria
FROM dbo.Producto AS p
LEFT JOIN dbo.Categoria AS c ON c.IdCategoria = p.IdCategoria
WHERE p.IdCategoria IS NULL OR c.IdCategoria IS NULL;
GO

-- 4. Registros con campos obligatorios vacíos o nulos.
--    Cada fila debe mostrar 0 en RegistrosInvalidos.
SELECT 'Cliente' AS Tabla, COUNT_BIG(*) AS RegistrosInvalidos
FROM dbo.Cliente
WHERE IdCliente IS NULL OR Nombre IS NULL OR LTRIM(RTRIM(Nombre)) = ''
   OR Email IS NULL OR LTRIM(RTRIM(Email)) = ''
UNION ALL
SELECT 'Producto', COUNT_BIG(*)
FROM dbo.Producto
WHERE IdProducto IS NULL OR Nombre IS NULL OR LTRIM(RTRIM(Nombre)) = ''
   OR IdCategoria IS NULL
UNION ALL
SELECT 'Opinion', COUNT_BIG(*)
FROM dbo.Opinion
WHERE IdCliente IS NULL OR IdProducto IS NULL OR IdFuente IS NULL
   OR Fecha IS NULL OR Comentario IS NULL OR LTRIM(RTRIM(Comentario)) = '';
GO

-- 5. Puntuaciones fuera del rango permitido (1 a 5).
--    Debe devolver 0.
SELECT IdOpinion, PuntajeSatisfaccion
FROM dbo.Opinion
WHERE PuntajeSatisfaccion IS NOT NULL
  AND (PuntajeSatisfaccion < 1 OR PuntajeSatisfaccion > 5);
GO

-- 6. Resumen de opiniones por fuente y clasificación.
--    Permite comprobar que se cargaron opiniones asociadas a los catálogos.
SELECT
    COALESCE(f.TipoFuente, 'Sin fuente') AS Fuente,
    COALESCE(cl.Nombre, 'Sin clasificación') AS Clasificacion,
    COUNT_BIG(*) AS CantidadOpiniones
FROM dbo.Opinion AS o
LEFT JOIN dbo.FuenteDatos AS f ON f.IdFuente = o.IdFuente
LEFT JOIN dbo.Clasificacion AS cl ON cl.IdClasificacion = o.IdClasificacion
GROUP BY f.TipoFuente, cl.Nombre
ORDER BY Fuente, Clasificacion;
GO

-- 7. Clientes con correos duplicados.
--    Debe devolver 0 filas (Email tiene restricción UNIQUE en el modelo).
SELECT Email, COUNT_BIG(*) AS Cantidad
FROM dbo.Cliente
GROUP BY Email
HAVING COUNT_BIG(*) > 1;
GO

-- 8. Verificación resumida de las relaciones entre tablas.
--    Los conteos deben coincidir; los registros sin relación deben ser 0.
SELECT
    (SELECT COUNT_BIG(*) FROM dbo.Opinion) AS TotalOpiniones,
    (SELECT COUNT_BIG(*) FROM dbo.Opinion AS o
     INNER JOIN dbo.Cliente AS c ON c.IdCliente = o.IdCliente
     INNER JOIN dbo.Producto AS p ON p.IdProducto = o.IdProducto
     INNER JOIN dbo.FuenteDatos AS f ON f.IdFuente = o.IdFuente) AS OpinionesConRelacionesValidas,
    (SELECT COUNT_BIG(*) FROM dbo.Opinion AS o
     LEFT JOIN dbo.Cliente AS c ON c.IdCliente = o.IdCliente
     LEFT JOIN dbo.Producto AS p ON p.IdProducto = o.IdProducto
     LEFT JOIN dbo.FuenteDatos AS f ON f.IdFuente = o.IdFuente
     WHERE c.IdCliente IS NULL OR p.IdProducto IS NULL OR f.IdFuente IS NULL)
        AS OpinionesConReferenciasInvalidas;
GO
