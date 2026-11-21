"""Preparación (T) de las filas de cada dimensión.

Son funciones puras: reciben DataFrames de staging y devuelven las filas listas para el
tipo de tabla de SQL Server (script 07).  No tocan la base de datos, por eso se prueban
fácilmente.  Reglas comunes:
  - Las claves de cliente y producto se guardan como texto SIN prefijo ni ceros a la izquierda
    ('C019' y 19 -> '19'), para que todas las fuentes apunten a la misma fila.
  - Se limpian espacios; un campo obligatorio vacío o más largo que la columna destino
    rechaza la fila (no se corta el texto en silencio).
  - Si una clave llega repetida se conserva la última fila (el valor más reciente).
  - Cliente, Producto y Fuente reciben una fila "Desconocido" (clave -1) para las opiniones
    cuya referencia no exista; se puede desactivar con MiembroDesconocido en appsettings.json.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

ID_DESCONOCIDO = -1
NOMBRE_DESCONOCIDO = "Desconocido"
CATEGORIA_FALTANTE = "Sin categoría"

PATRON_CLAVE = re.compile(r"^[A-Za-z]*\s*0*(\d+)$")


@dataclass(frozen=True)
class OpcionesDimensiones:
    fecha_inicio: date
    fecha_fin: date
    miembro_desconocido: bool = True


@dataclass
class Preparacion:
    filas: list[tuple]
    leidas: int                 # filas que había en staging (o días generados)
    rechazadas: int = 0         # descartadas por inválidas o repetidas
    desconocido: int = 0        # 1 si se agregó la fila "Desconocido"
    avisos: list[str] = field(default_factory=list)


def limpiar_texto(valor) -> str | None:
    """Quita espacios repetidos; texto vacío o nulo -> None."""
    if valor is None or pd.isna(valor):
        return None
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    return texto or None


def normalizar_clave(valor) -> str | None:
    """'C019' -> '19', 19 -> '19', 19.0 -> '19'. Si no tiene forma de número se deja el texto limpio."""
    texto = limpiar_texto(valor)
    if texto is None:
        return None
    if isinstance(valor, float) and valor.is_integer():
        texto = str(int(valor))
    coincidencia = PATRON_CLAVE.match(texto)
    return str(int(coincidencia.group(1))) if coincidencia else texto


def a_entero(valor) -> int | None:
    if valor is None or pd.isna(valor):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _resumen_motivos(motivos: Counter) -> list[str]:
    if not motivos:
        return []
    detalle = ", ".join(f"{cantidad} {motivo}" for motivo, cantidad in motivos.most_common())
    return [f"{sum(motivos.values())} filas rechazadas ({detalle})"]


def _cierre(filas: dict, leidas: int, motivos: Counter, extra_avisos: list[str],
            fila_desconocida: tuple | None, clave_desconocida) -> Preparacion:
    desconocido = 0
    if fila_desconocida is not None and clave_desconocida not in filas:
        filas[clave_desconocida] = fila_desconocida
        desconocido = 1
    return Preparacion(
        filas=list(filas.values()), leidas=leidas, rechazadas=sum(motivos.values()),
        desconocido=desconocido, avisos=_resumen_motivos(motivos) + extra_avisos,
    )


def preparar_clasificacion(datos: pd.DataFrame, opciones: OpcionesDimensiones) -> Preparacion:
    filas, motivos = {}, Counter()
    for fila in datos.to_dict("records"):
        id_clasificacion = a_entero(fila.get("IdClasificacion"))
        nombre = limpiar_texto(fila.get("Nombre"))
        if id_clasificacion is None:
            motivos["sin IdClasificacion"] += 1
        elif nombre is None:
            motivos["sin Nombre"] += 1
        elif len(nombre) > 20:
            motivos["con Nombre de más de 20 caracteres"] += 1
        else:
            if id_clasificacion in filas:
                motivos["con clave repetida"] += 1
            filas[id_clasificacion] = (id_clasificacion, nombre)
    return _cierre(filas, len(datos), motivos, [], None, None)


def preparar_fuente(datos: pd.DataFrame, opciones: OpcionesDimensiones) -> Preparacion:
    filas, motivos = {}, Counter()
    for fila in datos.to_dict("records"):
        id_fuente = a_entero(fila.get("IdFuente"))
        tipo = limpiar_texto(fila.get("TipoFuente"))
        if id_fuente is None:
            motivos["sin IdFuente"] += 1
        elif tipo is None:
            motivos["sin TipoFuente"] += 1
        elif len(tipo) > 50:
            motivos["con TipoFuente de más de 50 caracteres"] += 1
        else:
            if id_fuente in filas:
                motivos["con clave repetida"] += 1
            filas[id_fuente] = (id_fuente, tipo)
    desconocida = (ID_DESCONOCIDO, NOMBRE_DESCONOCIDO) if opciones.miembro_desconocido else None
    return _cierre(filas, len(datos), motivos, [], desconocida, ID_DESCONOCIDO)


def preparar_cliente(datos: pd.DataFrame, opciones: OpcionesDimensiones) -> Preparacion:
    filas, motivos = {}, Counter()
    for fila in datos.to_dict("records"):
        id_cliente = normalizar_clave(fila.get("IdCliente"))
        nombre = limpiar_texto(fila.get("Nombre"))
        correo = limpiar_texto(fila.get("Email"))
        if id_cliente is None:
            motivos["sin IdCliente"] += 1
        elif nombre is None:
            motivos["sin Nombre"] += 1
        elif len(id_cliente) > 50 or len(nombre) > 100 or (correo and len(correo) > 100):
            motivos["con texto más largo que la columna"] += 1
        else:
            if id_cliente in filas:
                motivos["con clave repetida"] += 1
            # El correo vacío viaja como '' (no NULL) y el procedimiento lo convierte en NULL.
            filas[id_cliente] = (id_cliente, nombre, correo.lower() if correo else "")
    desconocida = (str(ID_DESCONOCIDO), NOMBRE_DESCONOCIDO, "") if opciones.miembro_desconocido else None
    return _cierre(filas, len(datos), motivos, [], desconocida, str(ID_DESCONOCIDO))


def preparar_producto(productos: pd.DataFrame, categorias: pd.DataFrame,
                      opciones: OpcionesDimensiones) -> Preparacion:
    nombres_categoria = {
        normalizar_clave(f.get("IdCategoria")): limpiar_texto(f.get("Nombre"))
        for f in categorias.to_dict("records")
    }
    filas, motivos, sin_categoria = {}, Counter(), 0
    for fila in productos.to_dict("records"):
        id_producto = normalizar_clave(fila.get("IdProducto"))
        nombre = limpiar_texto(fila.get("Nombre"))
        categoria = nombres_categoria.get(normalizar_clave(fila.get("IdCategoria")))
        if id_producto is None:
            motivos["sin IdProducto"] += 1
        elif nombre is None:
            motivos["sin Nombre"] += 1
        elif len(id_producto) > 50 or len(nombre) > 100 or (categoria and len(categoria) > 50):
            motivos["con texto más largo que la columna"] += 1
        else:
            if id_producto in filas:
                motivos["con clave repetida"] += 1
            if categoria is None:
                categoria, sin_categoria = CATEGORIA_FALTANTE, sin_categoria + 1
            filas[id_producto] = (id_producto, nombre, categoria)
    avisos = [f"{sin_categoria} productos sin categoría válida (quedan como '{CATEGORIA_FALTANTE}')"] \
        if sin_categoria else []
    desconocida = (str(ID_DESCONOCIDO), NOMBRE_DESCONOCIDO, CATEGORIA_FALTANTE) \
        if opciones.miembro_desconocido else None
    return _cierre(filas, len(productos), motivos, avisos, desconocida, str(ID_DESCONOCIDO))


def generar_fecha(opciones: OpcionesDimensiones) -> Preparacion:
    """Calendario completo entre las dos fechas (inclusive). No viene de staging."""
    if opciones.fecha_fin < opciones.fecha_inicio:
        raise ValueError("Dimensiones.Fecha: 'Fin' no puede ser anterior a 'Inicio'")
    filas = []
    dia = opciones.fecha_inicio
    while dia <= opciones.fecha_fin:
        filas.append((int(dia.strftime("%Y%m%d")), dia, dia.day, dia.month,
                      (dia.month - 1) // 3 + 1, dia.year))
        dia += timedelta(days=1)
    return Preparacion(filas=filas, leidas=len(filas))
