"""Consume la API REST de comentarios de redes sociales (equivale a HttpClient)."""

import asyncio
import logging
import math

import httpx
import pandas as pd

from application.interfaces import IExtractorAsync

CODIGOS_REINTENTABLES = {429, 500, 502, 503, 504}


class ErrorApi(Exception):
    """La API respondió algo que no se puede usar."""


class ErrorReintentable(ErrorApi):
    """Fallo temporal de la API (sobrecarga o error del servidor)."""


class ApiExtractor(IExtractorAsync):
    """Descarga todas las páginas de la API.

    1. Pide la página 1 para saber cuántas páginas hay.
    2. Pide el resto a la vez, con un máximo de `max_concurrencia` peticiones
       simultáneas (asyncio.Semaphore) para no saturar la API.
    3. Cada petición tiene timeout y se reintenta con espera exponencial ante
       fallos temporales. Un 401/403 (llave inválida) no se reintenta.
    """

    def __init__(self, nombre: str, tabla_destino: str, url_base: str, endpoint: str,
                 api_key: str, columnas: list[str], tamano_pagina: int = 50,
                 max_concurrencia: int = 4, timeout_segundos: float = 10,
                 reintentos: int = 3, espera_base_segundos: float = 0.5,
                 transport: httpx.AsyncBaseTransport | None = None,
                 logger: logging.Logger | None = None):
        super().__init__(nombre, "API", tabla_destino)
        self.url_base = url_base
        self.endpoint = endpoint
        self.api_key = api_key
        self.columnas = columnas
        self.tamano_pagina = tamano_pagina
        self.max_concurrencia = max_concurrencia
        self.timeout_segundos = timeout_segundos
        self.reintentos = reintentos
        self.espera_base_segundos = espera_base_segundos
        self.transport = transport  # solo se usa en las pruebas
        self.logger = logger or logging.getLogger(f"extraccion.{nombre}")

    async def extraer(self) -> pd.DataFrame:
        async with httpx.AsyncClient(
            base_url=self.url_base,
            headers={"X-API-Key": self.api_key, "Accept": "application/json"},
            timeout=self.timeout_segundos,
            transport=self.transport,
        ) as cliente:
            primera = await self._pedir_pagina(cliente, 1)
            total_paginas = int(primera.get("total_paginas", 1))

            semaforo = asyncio.Semaphore(self.max_concurrencia)

            async def pedir(pagina: int) -> dict:
                async with semaforo:
                    return await self._pedir_pagina(cliente, pagina)

            resto = await asyncio.gather(*(pedir(p) for p in range(2, total_paginas + 1)))

        registros = list(primera["datos"])
        for pagina in resto:
            registros.extend(pagina["datos"])
        self.logger.info("%s: %d páginas, %d registros", self.nombre, total_paginas, len(registros))
        return self._a_dataframe(registros)

    async def _pedir_pagina(self, cliente: httpx.AsyncClient, pagina: int) -> dict:
        intento = 0
        while True:
            intento += 1
            try:
                respuesta = await cliente.get(
                    self.endpoint, params={"pagina": pagina, "tamano": self.tamano_pagina}
                )
                if respuesta.status_code in (401, 403):
                    raise ErrorApi(f"La API rechazó la llave (HTTP {respuesta.status_code})")
                if respuesta.status_code in CODIGOS_REINTENTABLES:
                    raise ErrorReintentable(f"HTTP {respuesta.status_code} en la página {pagina}")
                respuesta.raise_for_status()
                cuerpo = respuesta.json()
                if not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("datos"), list):
                    raise ErrorApi(f"Respuesta sin la lista 'datos' en la página {pagina}")
                return cuerpo
            except (httpx.TransportError, ErrorReintentable) as error:
                if intento > self.reintentos:
                    raise ErrorApi(
                        f"Página {pagina} falló tras {intento} intentos: {error}"
                    ) from error
                espera = self.espera_base_segundos * 2 ** (intento - 1)
                self.logger.warning(
                    "%s: página %d, intento %d falló (%s); reintento en %.1f s",
                    self.nombre, pagina, intento, error, espera,
                )
                await asyncio.sleep(espera)

    def _a_dataframe(self, registros: list[dict]) -> pd.DataFrame:
        if registros:
            faltantes = [c for c in self.columnas if c not in registros[0]]
            if faltantes:
                raise ErrorApi(f"La API no devuelve los campos: {', '.join(faltantes)}")
        datos = pd.DataFrame(registros, columns=self.columnas)
        # Staging guarda texto: todo valor no nulo se convierte en str.
        return datos.astype(object).map(_como_texto)


def _como_texto(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    return str(valor)
