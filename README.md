# Sistema ETL de análisis de opiniones de clientes

Aplicación de consola en Python que carga datos de clientes, productos, categorías, fuentes de datos y opiniones en Microsoft SQL Server. El proceso sigue una arquitectura ETL por capas: extrae CSV, limpia y transforma los registros, calcula una clasificación básica del sentimiento y los carga en tablas relacionales.

## Funcionalidades

- Importa clientes y fuentes desde CSV.
- Crea las tablas definidas por los modelos SQLAlchemy cuando no existen.
- Siembra las clasificaciones y las categorías que falten; SQL Server genera los IDs de categoría.
- Asocia cada producto con su categoría y cada opinión con cliente, producto, fuente y clasificación.
- Limpia IDs que incluyen prefijos, por ejemplo `C019` o `P003`.
- Clasifica comentarios con reglas de palabras positivas y negativas.
- Descarta filas incompletas o con referencias a clientes/productos que no existen, e informa cuántas filas se insertaron o rechazaron.

La clasificación de sentimiento es heurística y se implementa en `application/transformer.py`; no usa un modelo de aprendizaje automático.

## Estructura del proyecto

```text
application/       Orquestación ETL, contratos y transformaciones
config/            Ensamblado de extractores, transformadores y cargadores
domain/            Modelos y esquema relacional SQLAlchemy
infrastructure/    Lectura CSV, conexiones SQL y carga a la base
 data/             Carpeta local para los CSV (los datos no se publican)
main.py            Punto de entrada
requirements.txt   Dependencias de Python
```

## Requisitos

- Windows con Python 3.10 o superior.
- Microsoft SQL Server y una base de datos ya creada.
- Microsoft ODBC Driver 17 o 18 for SQL Server.
- Autenticación integrada de Windows para SQL Server.
- Los seis archivos CSV requeridos en la carpeta `data/` (ver sus nombres y columnas abajo).

## Archivos de entrada

Los CSV deben estar guardados en UTF-8 y usar estos nombres y encabezados. Las columnas con tilde deben conservarla:

| Archivo | Columnas esperadas |
| --- | --- |
| `clients.csv` | `IdCliente, Nombre, Email` |
| `fuente_datos.csv` | `IdFuente, TipoFuente, FechaCarga` |
| `products.csv` | `IdProducto, Nombre, Categoría` |
| `surveys_part1.csv` | `IdOpinion, IdCliente, IdProducto, Fecha, Comentario, Clasificación, PuntajeSatisfacción, Fuente` |
| `social_comments.csv` | `IdComment, IdCliente, IdProducto, Fuente, Fecha, Comentario` |
| `web_reviews.csv` | `IdReview, IdCliente, IdProducto, Fecha, Comentario, Rating` |

Los archivos de datos locales se excluyen de Git porque pueden incluir correos, comentarios u otra información de clientes. Deben colocarse manualmente en `data/` para ejecutar el ETL.

## Instalación

Desde PowerShell, en la raíz del repositorio:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Instala también Microsoft ODBC Driver 17 o 18 for SQL Server y asegúrate de que la instancia de SQL Server esté disponible.

## Configuración de SQL Server

La conexión usa autenticación integrada de Windows. Por defecto intenta conectarse a `.\SQLEXPRESS` y a la base de datos `OpinionesCliente`. Puedes cambiar esos valores en la sesión de PowerShell antes de ejecutar:

```powershell
$env:SQL_SERVER = ".\SQLEXPRESS"
$env:SQL_DATABASE = "OpinionesCliente"
$env:ODBC_DRIVER = "ODBC Driver 17 for SQL Server"
```

La base de datos debe existir antes de ejecutar el programa. `Base.metadata.create_all()` crea las tablas del proyecto, pero no crea la base de datos de SQL Server.

## Ejecución

Coloca los seis CSV en `data/`, activa el entorno virtual, configura la conexión y ejecuta desde la carpeta raíz:

```powershell
python main.py
```

El programa imprime un resumen por pipeline con el número de filas leídas, insertadas y rechazadas. La carga usa inserciones en modo `append`; usa una base de datos de desarrollo para las pruebas y evita volver a cargar IDs que ya estén presentes.

## Herramientas utilizadas

- **Python** para implementar y ejecutar el programa.
- **Pandas** para leer, transformar y preparar los CSV.
- **SQLAlchemy** para el modelo relacional y la conexión a SQL Server.
- **pyodbc** y **Microsoft ODBC Driver** para comunicarse con SQL Server.
- **Requests** para el extractor REST incluido como componente extensible.
- **Microsoft SQL Server** como destino de los datos.
- **Git y GitHub** para control de versiones y colaboración.

## Cómo probarlo

1. Crea una base de datos de desarrollo en SQL Server y verifica que tu usuario de Windows pueda conectarse.
2. Instala las dependencias y configura `SQL_SERVER`, `SQL_DATABASE` y `ODBC_DRIVER` como se explica arriba.
3. Copia los seis CSV requeridos a `data/` y confirma que sus encabezados coincidan con la tabla de archivos de entrada.
4. Ejecuta `python main.py` desde la raíz del proyecto.
5. Revisa los resúmenes del ETL y consulta el resultado en SQL Server:

   ```sql
   SELECT COUNT(*) AS Total FROM Categoria;
   SELECT COUNT(*) AS Total FROM Producto;
   SELECT COUNT(*) AS Total FROM Opinion;
   ```

El repositorio no incluye una suite de pruebas automatizadas; este procedimiento verifica la carga completa contra una base de datos de desarrollo.

