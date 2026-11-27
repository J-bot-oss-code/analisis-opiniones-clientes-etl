"""Preparación (T) de las filas de las tablas de hechos (Fact_Opiniones y Fact_Resenas).

Son funciones puras: reciben DataFrames de staging y devuelven las filas listas para los tipos de
tabla de SQL Server (script 15).  No tocan la base de datos, por eso se prueban fácilmente.

Solo se envía lo necesario (el procedimiento además ignora lo que ya existe en el hecho):
  - Una fila con cliente o producto que no existe en su dimensión se RECHAZA: es una base analítica y todo
    hecho debe poder analizarse por cliente y por producto.  (Si se activa MiembroDesconocido en appsettings,
    esas filas se asignan al miembro "Desconocido" (-1) y se cuentan en los avisos; está desactivado.)
  - Clasificación y fecha: una fila sin clasificación válida o con fecha fuera de Dim_Fecha se rechaza.
    Lo mismo si falta el puntaje (la tabla no admite NULL) o está fuera de 1 a 5.
  - Las claves de cliente y producto se normalizan igual que en las dimensiones ('C019' y 19 -> '19').
  - Para que dos fuentes no choquen, IdOpinion lleva prefijo de origen: 'BD-12' (base relacional) y
    'ENC-12' (encuesta CSV).  Las reseñas conservan su IdReview ('W0001').
  - Una opinión de la encuesta que ya está en la base relacional (mismo cliente, producto y fecha) no se
    vuelve a cargar: el diagnóstico (script 13) encontró 6 encuestas idénticas a las 6 de la fuente CSV.
  - Las opiniones de las fuentes configuradas como "solo reseñas" (Web) se omiten aquí: se cargan en Fact_Resenas.
  - Los comentarios de redes sociales no traen puntaje ni clasificación: no pueden ser hechos y se rechazan.
  - Si una clave llega repetida se conserva la última fila.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd

from application.dimension_preparation import (ID_DESCONOCIDO, OpcionesDimensiones, Preparacion, a_entero,
                                               limpiar_texto, normalizar_clave, preparar_clasificacion,
                                               preparar_cliente, preparar_fuente, preparar_producto)

PREFIJO_BD = "BD-"
PREFIJO_ENCUESTA = "ENC-"
PUNTAJE_MINIMO = Decimal("1")
PUNTAJE_MAXIMO = Decimal("5")

# Rating de la reseña -> nombre de la clasificación (Dim_Clasificacion). Es la misma escala de las encuestas.
CLASIFICACION_POR_RATING = {1: "negativa", 2: "negativa", 3: "neutra", 4: "positiva", 5: "positiva"}


@dataclass(frozen=True)
class OpcionesHechos:
    dimensiones: OpcionesDimensiones                       # rango de Dim_Fecha y miembro Desconocido
    id_fuente_encuestas: int = 2                           # IdFuente de Dim_Fuente que representa a las encuestas CSV
    fuentes_excluidas_opiniones: frozenset = frozenset({1})  # IdFuente que se cargan como reseñas (Web)
    tamano_lote: int = 500                                 # filas por llamada al procedimiento


@dataclass
class Referencias:
    """Claves que SÍ existen en las dimensiones (se calculan con las mismas reglas con que se cargaron)."""
    clientes: set
    productos: set
    fuentes: set
    clasificaciones: dict          # nombre en minúsculas -> IdClasificacion


def construir_referencias(datos: dict[str, pd.DataFrame], opciones: OpcionesHechos) -> Referencias:
    dim = opciones.dimensiones
    return Referencias(
        clientes={fila[0] for fila in preparar_cliente(datos["stg.Cliente"], dim).filas},
        productos={fila[0] for fila in preparar_producto(datos["stg.Producto"], datos["stg.Categoria"], dim).filas},
        fuentes={fila[0] for fila in preparar_fuente(datos["stg.FuenteDatos"], dim).filas},
        clasificaciones={nombre.casefold(): id_clasificacion
                         for id_clasificacion, nombre in preparar_clasificacion(datos["stg.Clasificacion"], dim).filas},
    )


# ---------------------------------------------------------------- conversiones

def a_fecha(valor) -> date | None:
    """Fecha ISO (AAAA-MM-DD), date o datetime -> date; cualquier otra cosa -> None."""
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = limpiar_texto(valor)
    if texto is None:
        return None
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        return None


def a_id_fecha(fecha: date | None, dim: OpcionesDimensiones) -> int | None:
    """IdFecha (aaaammdd) si la fecha está dentro del rango de Dim_Fecha; si no, None."""
    if fecha is None or not dim.fecha_inicio <= fecha <= dim.fecha_fin:
        return None
    return int(fecha.strftime("%Y%m%d"))


def a_decimal(valor) -> Decimal | None:
    """Número con 2 decimales; vacío, texto o infinito -> None."""
    if valor is None or pd.isna(valor):
        return None
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except InvalidOperation:
        return None
    if not numero.is_finite():
        return None
    return numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def a_puntaje(valor) -> Decimal | None:
    numero = a_decimal(valor)
    return numero if numero is not None and PUNTAJE_MINIMO <= numero <= PUNTAJE_MAXIMO else None


def a_rating(valor) -> int | None:
    numero = a_puntaje(valor)
    return int(numero) if numero is not None and numero == numero.to_integral_value() else None


def _resolver(clave, existentes: set, desconocido):
    """(clave, es_desconocido): la clave si existe en la dimensión; si no, el miembro Desconocido; si tampoco hay, None."""
    if clave is not None and clave in existentes:
        return clave, False
    if desconocido in existentes:
        return desconocido, True
    return None, False


def _avisos(motivos: Counter, desconocidos: Counter) -> list[str]:
    avisos = []
    if motivos:
        detalle = ", ".join(f"{cantidad} {motivo}" for motivo, cantidad in motivos.most_common())
        avisos.append(f"{sum(motivos.values())} filas rechazadas ({detalle})")
    if desconocidos:
        detalle = ", ".join(f"{cantidad} con {dim} desconocido (-1)" for dim, cantidad in desconocidos.most_common())
        avisos.append(f"Filas enviadas: {detalle}")
    return avisos


def _validar_comun(fila: dict, referencias: Referencias, opciones: OpcionesHechos,
                   motivos: Counter, desconocidos: Counter):
    """Valida fecha, cliente y producto. Devuelve (id_fecha, id_cliente, id_producto, cliente_original,
    producto_original, fecha) o None (y anota el motivo)."""
    fecha = a_fecha(fila.get("Fecha"))
    id_fecha = a_id_fecha(fecha, opciones.dimensiones)
    if id_fecha is None:
        motivos["con fecha inválida o fuera de Dim_Fecha"] += 1
        return None
    cliente_original = normalizar_clave(fila.get("IdCliente"))
    producto_original = normalizar_clave(fila.get("IdProducto"))
    desconocido = str(ID_DESCONOCIDO)
    id_cliente, cliente_desconocido = _resolver(cliente_original, referencias.clientes, desconocido)
    id_producto, producto_desconocido = _resolver(producto_original, referencias.productos, desconocido)
    if id_cliente is None or id_producto is None:
        if id_cliente is None and id_producto is None:
            motivos["con cliente y producto inexistentes"] += 1
        elif id_cliente is None:
            motivos["con cliente inexistente"] += 1
        else:
            motivos["con producto inexistente"] += 1
        return None
    if cliente_desconocido:
        desconocidos["cliente"] += 1
    if producto_desconocido:
        desconocidos["producto"] += 1
    return id_fecha, id_cliente, id_producto, cliente_original, producto_original, fecha


def _clave_contenido(cliente, producto, fecha):
    """Identifica una misma opinión aunque venga de dos fuentes con distinto IdOpinion."""
    return cliente, producto, fecha


# ---------------------------------------------------------------- Fact_Opiniones

def preparar_fact_opiniones(datos: dict[str, pd.DataFrame], opciones: OpcionesHechos) -> Preparacion:
    """Opiniones de la base relacional (stg.Opinion) y de la encuesta CSV (stg.EncuestaCSV)."""
    referencias = construir_referencias(datos, opciones)
    id_clasificaciones = set(referencias.clasificaciones.values())
    desconocido_fuente = ID_DESCONOCIDO
    filas, motivos, desconocidos = {}, Counter(), Counter()
    contenido_bd, leidas = set(), 0

    def fuente_valida(id_fuente):
        resuelta, es_desconocida = _resolver(id_fuente, referencias.fuentes, desconocido_fuente)
        if es_desconocida:
            desconocidos["fuente"] += 1
        return resuelta

    def guardar(clave, fila_nueva):
        if clave in filas:
            motivos["con clave repetida"] += 1
        filas[clave] = fila_nueva

    # 1) Base relacional: IdClasificacion y IdFuente ya vienen como números
    for fila in datos["stg.Opinion"].to_dict("records"):
        leidas += 1
        id_origen = normalizar_clave(fila.get("IdOpinion"))
        id_fuente = a_entero(fila.get("IdFuente"))
        puntaje = a_puntaje(fila.get("PuntajeSatisfaccion"))
        id_clasificacion = a_entero(fila.get("IdClasificacion"))
        if id_fuente in opciones.fuentes_excluidas_opiniones:
            motivos["de fuentes que se cargan como reseñas"] += 1
        elif id_origen is None:
            motivos["sin IdOpinion"] += 1
        elif puntaje is None:
            motivos["sin puntaje válido (1 a 5)"] += 1
        elif id_clasificacion not in id_clasificaciones:
            motivos["sin clasificación válida"] += 1
        else:
            comun = _validar_comun(fila, referencias, opciones, motivos, desconocidos)
            if comun is None:
                continue
            id_fecha, id_cliente, id_producto, cliente_orig, producto_orig, fecha = comun
            id_fuente_ok = fuente_valida(id_fuente)
            if id_fuente_ok is None:
                motivos["con fuente inexistente"] += 1
                continue
            contenido_bd.add(_clave_contenido(cliente_orig, producto_orig, fecha))
            guardar(PREFIJO_BD + id_origen,
                    (PREFIJO_BD + id_origen, id_cliente, id_producto, id_fuente_ok, id_clasificacion,
                     id_fecha, puntaje))

    # 2) Encuesta CSV: la clasificación llega como texto y la fuente es siempre la de encuestas
    for fila in datos["stg.EncuestaCSV"].to_dict("records"):
        leidas += 1
        id_origen = normalizar_clave(fila.get("IdOpinion"))
        puntaje = a_puntaje(fila.get("PuntajeSatisfaccion"))
        nombre = limpiar_texto(fila.get("Clasificacion"))
        id_clasificacion = referencias.clasificaciones.get(nombre.casefold()) if nombre else None
        if id_origen is None:
            motivos["sin IdOpinion"] += 1
        elif puntaje is None:
            motivos["sin puntaje válido (1 a 5)"] += 1
        elif id_clasificacion is None:
            motivos["sin clasificación válida"] += 1
        else:
            comun = _validar_comun(fila, referencias, opciones, motivos, desconocidos)
            if comun is None:
                continue
            id_fecha, id_cliente, id_producto, cliente_orig, producto_orig, fecha = comun
            if _clave_contenido(cliente_orig, producto_orig, fecha) in contenido_bd:
                motivos["ya cargadas desde la base relacional"] += 1
                # se deshace el conteo de "desconocido" de una fila que no se envía
                if id_cliente == str(ID_DESCONOCIDO):
                    desconocidos["cliente"] -= 1
                if id_producto == str(ID_DESCONOCIDO):
                    desconocidos["producto"] -= 1
                continue
            id_fuente_ok = fuente_valida(opciones.id_fuente_encuestas)
            if id_fuente_ok is None:
                motivos["con fuente inexistente"] += 1
                continue
            guardar(PREFIJO_ENCUESTA + id_origen,
                    (PREFIJO_ENCUESTA + id_origen, id_cliente, id_producto, id_fuente_ok, id_clasificacion,
                     id_fecha, puntaje))

    desconocidos = +desconocidos     # quita los contadores en cero
    return Preparacion(filas=list(filas.values()), leidas=leidas, rechazadas=sum(motivos.values()),
                       avisos=_avisos(motivos, desconocidos))


# ---------------------------------------------------------------- Fact_Resenas

def preparar_fact_resenas(datos: dict[str, pd.DataFrame], opciones: OpcionesHechos) -> Preparacion:
    """Reseñas web (stg.ResenaWeb). La clasificación se deriva del Rating (1-2 negativa, 3 neutra, 4-5 positiva)."""
    referencias = construir_referencias(datos, opciones)
    filas, motivos, desconocidos = {}, Counter(), Counter()
    tabla = datos["stg.ResenaWeb"]
    for fila in tabla.to_dict("records"):
        id_review = limpiar_texto(fila.get("IdReview"))
        rating = a_rating(fila.get("Rating"))
        if id_review is None:
            motivos["sin IdReview"] += 1
        elif len(id_review) > 50:
            motivos["con IdReview de más de 50 caracteres"] += 1
        elif rating is None:
            motivos["sin Rating válido (1 a 5)"] += 1
        else:
            id_clasificacion = referencias.clasificaciones.get(CLASIFICACION_POR_RATING[rating])
            if id_clasificacion is None:
                motivos["sin clasificación equivalente al Rating"] += 1
                continue
            comun = _validar_comun(fila, referencias, opciones, motivos, desconocidos)
            if comun is None:
                continue
            id_fecha, id_cliente, id_producto, *_ = comun
            if id_review in filas:
                motivos["con clave repetida"] += 1
            filas[id_review] = (id_review, id_cliente, id_producto, id_fecha, id_clasificacion, rating)
    return Preparacion(filas=list(filas.values()), leidas=len(tabla), rechazadas=sum(motivos.values()),
                       avisos=_avisos(motivos, +desconocidos))
