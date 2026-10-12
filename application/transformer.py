import pandas as pd


class DataTransformer:
    """Valida y adapta un CSV al esquema de su tabla de destino."""

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
        datos = datos.rename(columns=self.renombrar).copy()
        for columna, valor in self.valores_default.items():
            datos[columna] = valor
        faltantes = set(self.columnas_requeridas) - set(datos.columns)
        if faltantes:
            raise ValueError(f"Faltan columnas obligatorias: {', '.join(sorted(faltantes))}")

        total = len(datos)
        datos = datos.drop_duplicates(subset=self.clave_duplicados)

        for columna, valores in self.mapas.items():
            if columna in datos.columns:
                datos[columna] = datos[columna].map(valores)

        for columna in datos.columns:
            if columna in {"IdCliente", "IdProducto", "IdFuente", "IdCategoria", "IdClasificacion"}:
                valores = datos[columna].astype("string").str.extract(
                    r"^[A-Za-z]*(\d+)$", expand=False
                )
                datos[columna] = pd.to_numeric(valores, errors="coerce")

        for columna in ("IdCliente", "IdProducto", "IdFuente", "IdCategoria", "IdClasificacion"):
            if columna in self.columnas_requeridas:
                datos = datos.dropna(subset=[columna])

        for columna, permitidos in self.referencias.items():
            if columna in datos.columns:
                datos = datos[datos[columna].isin(permitidos)]

        for columna in ("Nombre", "Email", "TipoFuente", "Comentario"):
            if columna in datos.columns:
                datos[columna] = datos[columna].astype("string").str.strip()
        if "Email" in datos.columns:
            datos["Email"] = datos["Email"].str.lower()

        if "Fecha" in datos.columns:
            datos["Fecha"] = pd.to_datetime(datos["Fecha"], errors="coerce").dt.date
        if "FechaCarga" in datos.columns:
            datos["FechaCarga"] = pd.to_datetime(datos["FechaCarga"], errors="coerce").dt.date
        if "PuntajeSatisfaccion" in datos.columns:
            datos["PuntajeSatisfaccion"] = pd.to_numeric(datos["PuntajeSatisfaccion"], errors="coerce")

        campos_a_validar = [c for c in self.columnas_requeridas if c in datos.columns]
        datos = datos.dropna(subset=campos_a_validar)
        for columna in ("Nombre", "Email", "TipoFuente", "Comentario"):
            if columna in self.columnas_requeridas:
                datos = datos[datos[columna].astype("string").str.strip().ne("")]
        if "Email" in self.columnas_requeridas:
            datos = datos[datos["Email"].str.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", na=False)]
        if "PuntajeSatisfaccion" in datos.columns:
            datos = datos[datos["PuntajeSatisfaccion"].between(1, 5)]

        if self.columnas_salida:
            datos = datos[self.columnas_salida]

        return datos.reset_index(drop=True), total - len(datos)
