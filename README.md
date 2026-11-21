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

---

# Extracción (E) hacia el Data Warehouse

Worker en Python que extrae los datos de tres fuentes y los copia, sin transformar, a tablas staging en **OpinionesCliente_DW**. Cada corrida queda registrada en una bitácora.

| Fuente | Origen | Tabla staging |
| --- | --- | --- |
| Base de datos relacional | `OpinionesCliente` (6 tablas) | `stg.Categoria`, `stg.Clasificacion`, `stg.Cliente`, `stg.FuenteDatos`, `stg.Producto`, `stg.Opinion` |
| CSV | `data/surveys_part1.csv` (encuestas internas) | `stg.EncuestaCSV` |
| API REST | `api_comentarios/` sirve `data/social_comments.csv` | `stg.ComentarioAPI` |

## Requisitos previos

1. Scripts de `sql/` ejecutados en orden en SQL Server (esquemas `stg` y `etl`, tablas staging y bitácora).
2. Dependencias instaladas: `pip install -r requirements.txt`.
3. Secretos: copiar `config/.env.example` como `config/.env` y poner una llave en `API_COMENTARIOS_KEY`.

## Ejecución

Abrir dos terminales en la raíz del proyecto, con el entorno virtual activo:

```powershell
# Terminal 1: API de comentarios (dejarla abierta)
uvicorn api_comentarios.app:app --port 8000

# Terminal 2: worker
python worker.py --una-vez        # una sola corrida
python worker.py                  # ciclo continuo cada IntervaloMinutos (Ctrl+C para detener)
python worker.py --intervalo 5    # ciclo cada 5 minutos
```

Código de salida con `--una-vez`: `0` exitosa, `2` parcial (falló alguna fuente), `1` fallida.

Logs: consola y `logs/extraccion.log` (rotativo). Bitácora: `etl.EjecucionExtraccion` y `etl.DetalleExtraccion`.

Documentación interactiva de la API: http://127.0.0.1:8000/docs

## Configuración (`config/appsettings.json`)

- `Conexiones.Origen` / `Conexiones.Destino`: servidor, base de datos, driver ODBC y tipo de autenticación. Con `"AutenticacionWindows": false` el usuario y la clave se leen de `config/.env`.
- `Fuentes`: lista de fuentes. Cada una tiene `Tipo` (`BD`, `CSV` o `API`), `Activa` y `TablaDestino`. Para apagar una fuente, `"Activa": false`.
- `Extraccion.TamanoLote`: filas por lote al leer de la BD y al insertar en staging.
- `Worker.IntervaloMinutos` y `Logging`.

## Arquitectura

```text
worker.py                         punto de entrada de la extracción (Worker Service)
cargar_dimensiones.py             punto de entrada de la carga de dimensiones
application/
  interfaces.py                   IExtractorAsync, IStagingWriter, IRunLogRepository
  extraction_service.py           corre las fuentes en paralelo y registra la bitácora
  dimension_preparation.py        prepara las filas de cada dimensión (funciones puras)
  dimension_service.py            orquesta la carga de las cinco dimensiones
infrastructure/
  settings.py                     appsettings.json + .env
  logging_config.py               logs a consola y archivo rotativo
  factory.py                      crea extractores según el "Tipo" de cada fuente
  extractors/                     DatabaseExtractor, CsvExtractorAsync, ApiExtractor
  staging_writer.py               TRUNCATE + INSERT masivo en una transacción
  run_log_repository.py           etl.EjecucionExtraccion / etl.DetalleExtraccion
  staging_reader.py               lee stg.* para la carga de dimensiones
  dimension_loader.py             llama a etl.usp_Cargar_Dim_* con un parámetro de tipo tabla
  dimension_log_repository.py     etl.EjecucionCarga / etl.DetalleCargaDimension
api_comentarios/app.py            API REST local (FastAPI) protegida con X-API-Key
scripts/generar_carga.py          CSV de 50,000 encuestas para la prueba de rendimiento
tests/                            pruebas con pytest
```

Agregar una fuente nueva: crear una clase que herede de `IExtractorAsync`, registrarla en `FABRICAS` (`infrastructure/factory.py`) y añadirla en `appsettings.json`.

## Tecnologías

| Tecnología | Uso | Equivalente en .NET 8 |
| --- | --- | --- |
| Python 3.10+ | Lenguaje | C# |
| pandas | CSV y resultados SQL en DataFrames | CsvHelper / DataTable |
| SQLAlchemy 2 + pyodbc | Conexión, transacciones, inserción masiva (`fast_executemany`) | ADO.NET / EF Core |
| httpx | Cliente HTTP asíncrono con timeout | HttpClient / IHttpClientFactory |
| python-dotenv | Secretos en `config/.env` | User Secrets |
| FastAPI + Uvicorn | API REST local | ASP.NET Core Minimal API |
| asyncio | Fuentes en paralelo | async/await, Task.WhenAll |
| logging | Logs de eventos y errores | ILogger / Serilog |
| time.perf_counter | Medición de tiempos | Stopwatch |
| pytest | Pruebas automáticas | xUnit |

---

# Carga (L) de las dimensiones

Toma lo que la extracción dejó en `stg.*`, lo prepara y lo carga en las cinco dimensiones del modelo (`dbo.Dim_*`). Las tablas de hechos no forman parte de esta etapa.

| Dimensión | Origen | Tipo de tabla | Procedimiento |
| --- | --- | --- | --- |
| `Dim_Clasificacion` | `stg.Clasificacion` | `etl.T_Dim_Clasificacion` | `etl.usp_Cargar_Dim_Clasificacion` |
| `Dim_Fuente` | `stg.FuenteDatos` | `etl.T_Dim_Fuente` | `etl.usp_Cargar_Dim_Fuente` |
| `Dim_Fecha` | calendario generado (`Dimensiones.Fecha` en appsettings) | `etl.T_Dim_Fecha` | `etl.usp_Cargar_Dim_Fecha` |
| `Dim_Producto` | `stg.Producto` + `stg.Categoria` | `etl.T_Dim_Producto` | `etl.usp_Cargar_Dim_Producto` |
| `Dim_Cliente` | `stg.Cliente` | `etl.T_Dim_Cliente` | `etl.usp_Cargar_Dim_Cliente` |

## Cómo funciona

1. Python lee la tabla staging y prepara las filas (`application/dimension_preparation.py`): limpia espacios, quita el prefijo de las claves (`C019` pasa a `19`), rechaza filas inválidas y conserva la última de las claves repetidas.
2. Envía todo el lote en una sola llamada al procedimiento almacenado, como parámetro de tipo tabla (TVP).
3. El procedimiento actualiza lo que cambió, inserta lo que falta y devuelve los conteos. Es seguro repetirlo: la segunda corrida no duplica nada.
4. Cada corrida queda en la bitácora `etl.EjecucionCarga` y `etl.DetalleCargaDimension`.

`Dim_Cliente`, `Dim_Producto` y `Dim_Fuente` incluyen una fila `Desconocido` (clave `-1`) para las opiniones cuya referencia no exista. Se desactiva con `"MiembroDesconocido": false`.

## Ejecución

1. En SSMS, en orden: `sql/07_tipos_dimensiones.sql`, `08_procedimientos_dimensiones.sql`, `09_bitacora_carga.sql` y `10_permisos_carga.sql` (el 10 requiere haber ejecutado antes el 06).
2. Tener la extracción hecha: `python worker.py --una-vez` (si `stg.*` está vacío, la carga lo avisa).
3. Cargar:

```powershell
python cargar_dimensiones.py                       # las cinco dimensiones
python cargar_dimensiones.py --dimension Cliente   # solo una (se puede repetir)
```

4. Comprobar con `sql/11_verificar_dimensiones.sql`.

Código de salida: `0` exitosa, `2` parcial (alguna dimensión falló), `1` fallida.

## Pruebas

```powershell
python -m pytest
```

Las pruebas no necesitan SQL Server: usan SQLite en memoria, la API en memoria y dobles de prueba.

## Prueba de rendimiento

```powershell
python scripts/generar_carga.py          # crea data/carga_encuestas.csv con 50,000 filas
```

Cambiar la `Ruta` de `CSV_Encuestas` a `data/carga_encuestas.csv`, ejecutar `python worker.py --una-vez` y revisar `DuracionSegundos` en `etl.EjecucionExtraccion`.
