import pandas as pd

from application.interfaces import ITransformer


class DataTransformer(ITransformer):
    """Valida y adapta un CSV al esquema de su tabla de destino."""

    COLUMNAS_ID = {"IdCliente", "IdProducto", "IdFuente", "IdCategoria", "IdClasificacion"}
    COLUMNAS_TEXTO = {"Nombre", "Email", "TipoFuente", "Comentario"}

    def __init__(self, columnas_requeridas, clave_duplicados=None, renombrar=None,
                 columnas_salida=None, mapas=None, valores_default=None, referencias=None):
        self.columnas_requeridas = columnas_requeridas
        self.clave_duplicados = clave_duplicados or columnas_requeridas
        self.renombrar = renombrar or {}
        self.columnas_salida = columnas_salida
        self.mapas = mapas or {}
        self.valores_default = valores_default or {}
        self.referencias = referencias or {}

    def transformar(self, datos):
        datos = self._renombrar_columnas(datos)
        datos = self._aplicar_valores_default(datos)
        self._validar_columnas_requeridas(datos)

        total = len(datos)
        datos = self._eliminar_duplicados(datos)
        datos = self._aplicar_mapas(datos)
        datos = self._normalizar_ids(datos)
        datos = self._filtrar_por_referencias(datos)
        datos = self._limpiar_texto(datos)
        datos = self._normalizar_fechas_y_puntajes(datos)
        datos = self._validar_campos_requeridos(datos)
        datos = self._validar_textos_no_vacios(datos)
        datos = self._validar_email(datos)
        datos = self._validar_puntaje(datos)

        if self.columnas_salida:
            datos = datos[self.columnas_salida]

        return datos.reset_index(drop=True), total - len(datos)

    def _renombrar_columnas(self, datos):
        return datos.rename(columns=self.renombrar).copy()

    def _aplicar_valores_default(self, datos):
        for columna, valor in self.valores_default.items():
            datos[columna] = valor
        return datos

    def _validar_columnas_requeridas(self, datos):
        faltantes = set(self.columnas_requeridas) - set(datos.columns)
        if faltantes:
            raise ValueError(f"Faltan columnas obligatorias: {', '.join(sorted(faltantes))}")

    def _eliminar_duplicados(self, datos):
        return datos.drop_duplicates(subset=self.clave_duplicados)

    def _aplicar_mapas(self, datos):
        for columna, valores in self.mapas.items():
            if columna in datos.columns:
                datos[columna] = datos[columna].map(valores)
        return datos

    def _normalizar_ids(self, datos):
        for columna in datos.columns:
            if columna in self.COLUMNAS_ID:
                valores = datos[columna].astype("string").str.extract(
                    r"^[A-Za-z]*(\d+)$", expand=False
                )
                datos[columna] = pd.to_numeric(valores, errors="coerce")

        for columna in self.COLUMNAS_ID:
            if columna in self.columnas_requeridas:
                datos = datos.dropna(subset=[columna])
        return datos

    def _filtrar_por_referencias(self, datos):
        for columna, permitidos in self.referencias.items():
            if columna in datos.columns:
                datos = datos[datos[columna].isin(permitidos)]
        return datos

    def _limpiar_texto(self, datos):
        for columna in self.COLUMNAS_TEXTO:
            if columna in datos.columns:
                datos[columna] = datos[columna].astype("string").str.strip()
        if "Email" in datos.columns:
            datos["Email"] = datos["Email"].str.lower()
        return datos

    def _normalizar_fechas_y_puntajes(self, datos):
        if "Fecha" in datos.columns:
            datos["Fecha"] = pd.to_datetime(datos["Fecha"], errors="coerce").dt.date
        if "FechaCarga" in datos.columns:
            datos["FechaCarga"] = pd.to_datetime(datos["FechaCarga"], errors="coerce").dt.date
        if "PuntajeSatisfaccion" in datos.columns:
            datos["PuntajeSatisfaccion"] = pd.to_numeric(datos["PuntajeSatisfaccion"], errors="coerce")
        return datos

    def _validar_campos_requeridos(self, datos):
        campos_a_validar = [c for c in self.columnas_requeridas if c in datos.columns]
        return datos.dropna(subset=campos_a_validar)

    def _validar_textos_no_vacios(self, datos):
        for columna in self.COLUMNAS_TEXTO:
            if columna in self.columnas_requeridas:
                datos = datos[datos[columna].astype("string").str.strip().ne("")]
        return datos

    def _validar_email(self, datos):
        if "Email" in self.columnas_requeridas:
            datos = datos[datos["Email"].str.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", na=False)]
        return datos

    def _validar_puntaje(self, datos):
        if "PuntajeSatisfaccion" in datos.columns:
            datos = datos[datos["PuntajeSatisfaccion"].between(1, 5)]
        return datos
