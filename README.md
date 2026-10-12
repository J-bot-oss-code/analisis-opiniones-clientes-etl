# ETL de opiniones de clientes

Aplicación de consola que extrae los CSV de `data/`, valida y transforma sus registros y los carga en SQL Server respetando las relaciones del modelo.

## Requisitos

- Python 3.10 o posterior.
- SQL Server con la base de datos `OpinionesCliente` creada y accesible.
- Microsoft ODBC Driver 17 o 18 para SQL Server.
- Los seis CSV en la carpeta `data/`.

## Preparación y ejecución

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SQL_SERVER = ".\SQLEXPRESS"
$env:SQL_DATABASE = "OpinionesCliente"
$env:ODBC_DRIVER = "ODBC Driver 17 for SQL Server"
python main.py
```

La conexión usa autenticación integrada de Windows. `main.py` crea las tablas del modelo si faltan, completa las categorías y clasificaciones requeridas, y procesa las tablas en orden: fuentes, clientes, productos y opiniones.

## Archivos CSV

| Archivo | Columnas de origen |
| --- | --- |
| `clients.csv` | `IdCliente, Nombre, Email` |
| `fuente_datos.csv` | `IdFuente, TipoFuente, FechaCarga` |
| `products.csv` | `IdProducto, Nombre, Categoría` |
| `surveys_part1.csv` | `IdOpinion, IdCliente, IdProducto, Fecha, Comentario, Clasificación, PuntajeSatisfacción, Fuente` |
| `social_comments.csv` | `IdComment, IdCliente, IdProducto, Fuente, Fecha, Comentario` |
| `web_reviews.csv` | `IdReview, IdCliente, IdProducto, Fecha, Comentario, Rating` |

Se aceptan encabezados con acentos correctos y variantes con codificación alterada en las columnas de categoría y clasificación. Los CSV se excluyen de Git porque contienen datos de clientes.

## Validaciones y carga

- Comprueba que existan las columnas obligatorias y que los campos requeridos no estén vacíos.
- Convierte identificadores prefijados como `C019`, fechas y puntuaciones a sus tipos de destino.
- Elimina duplicados del mismo archivo, normaliza espacios y minúsculas del correo.
- Valida las referencias de cliente, producto, fuente y clasificación antes de cargar opiniones.
- Omite claves primarias que ya están en la tabla para hacer seguros los reintentos.
- Imprime por conjunto el total procesado, insertado y rechazado. Los errores de lectura, estructura o base de datos se muestran y detienen la ejecución.

## Organización

- `application/`: transformación y coordinación del proceso ETL.
- `infrastructure/`: lectura de CSV, configuración de SQL Server y carga.
- `domain/`: tablas y restricciones PK/FK del modelo relacional.
- `main.py`: preparación de catálogos y orden de ejecución.
