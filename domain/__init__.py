# Este archivo convierte a la carpeta "models" en un paquete unificado.
# Al importar todo aquí, permitimos que el resto de la aplicación 
# acceda a los modelos fácilmente.

from .base import Base

# 1. Primero importamos los catálogos (Tablas que no dependen de nadie)
from .categoria import Categoria
from .clasificacion import Clasificacion
from .fuente_datos import FuenteDatos
from .cliente import Cliente

# 2. Luego importamos las que dependen de los catálogos
from .producto import Producto

# 3. Al final importamos la que depende de todas las anteriores
from .opinion import Opinion
