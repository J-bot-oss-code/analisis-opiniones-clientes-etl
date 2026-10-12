# Informe de revisión y limpieza del ETL

## Estado inicial

El repositorio ya tenía una carga ETL funcional para clientes, fuentes, productos y opiniones. El flujo principal leía CSV, preparaba catálogos, adaptaba identificadores y fechas, y respetaba las dependencias entre las tablas. Los modelos SQLAlchemy existentes definen las claves primarias y foráneas.

La carga estaba hecha; durante esta limpieza no se ejecutó el proceso contra SQL Server ni se modificaron datos de la base poblada.

## Cambios realizados

- Se mantuvo un flujo simple por capas: extracción CSV, transformación/validación y carga SQL.
- Se mantuvieron el orden de carga y la preparación de los catálogos de categorías y clasificaciones.
- Se añadieron validaciones de columnas, campos requeridos, IDs, fechas, puntuaciones y formato de correo.
- Se normalizan espacios y correos; se eliminan duplicados del archivo y se omiten registros que ya existen según sus claves.
- Se valida que las claves foráneas de opiniones existan antes de insertarlas.
- Los errores de lectura, estructura o base de datos ahora se muestran y detienen el proceso; no se silencian como CSV vacío ni como carga exitosa.
- Se actualizó el README para describir el flujo real y sus requisitos.

## Elementos extra eliminados

- Extractores para API y base de datos, junto con sus fábricas, que no se usaban en esta práctica.
- Dependencia `requests`, que solo se necesitaba para el extractor API.
- Clasificación heurística de sentimiento, métricas derivadas y limpieza de texto que alteraba comentarios. Las clasificaciones y puntuaciones proporcionadas por los CSV se conservan y transforman para el esquema.
- Monkey patch del transformador de productos; el mapeo de categoría se configura directamente.
- Interfaces abstractas que solo añadían una capa para este flujo único.

## Verificación local

- Los módulos Python compilan y `import main` funciona.
- `git diff --check` no reporta errores de espacios.
- Se ejecutó la transformación de los seis CSV sin conexión ni escritura en SQL Server:

| Conjunto | Procesados | Válidos para carga | Rechazados |
| --- | ---: | ---: | ---: |
| Fuentes | 100 | 100 | 0 |
| Clientes | 500 | 500 | 0 |
| Productos | 200 | 200 | 0 |
| Encuestas | 500 | 6 | 494 |
| Redes sociales | 200 | 112 | 88 |
| Reseñas web | 200 | 200 | 0 |

Los rechazos de opiniones se deben a IDs de clientes o productos sin correspondencia en los archivos padre locales; se descartan para proteger la integridad referencial. Conviene cotejar las tablas padre reales de SQL Server antes de una nueva ejecución para confirmar si contienen IDs adicionales.

## Pendiente fuera de esta limpieza

El repositorio no contiene el script SQL de entrega, procedimientos almacenados, vistas, las cinco consultas de validación ni capturas de evidencia. Esta tarea se centró en simplificar y verificar el código del ETL, por lo que esos artefactos siguen pendientes como entregables separados.
