import asyncio

import pytest

from infrastructure.extractors import CsvExtractorAsync

COLUMNAS = {"IdOpinion": "IdOpinion", "Clasificación": "Clasificacion",
            "PuntajeSatisfacción": "PuntajeSatisfaccion"}


def test_lee_todo_como_texto_y_quita_tildes(tmp_path):
    ruta = tmp_path / "encuestas.csv"
    ruta.write_text("﻿IdOpinion,Clasificación,PuntajeSatisfacción\n1,Neutra,3\n2,,5\n",
                    encoding="utf-8")
    extractor = CsvExtractorAsync("CSV", "stg.EncuestaCSV", ruta, COLUMNAS)

    datos = asyncio.run(extractor.extraer())

    assert list(datos.columns) == ["IdOpinion", "Clasificacion", "PuntajeSatisfaccion"]
    assert datos.loc[0, "IdOpinion"] == "1"            # texto, no número
    assert datos.loc[0, "PuntajeSatisfaccion"] == "3"
    assert datos["Clasificacion"].isna().iloc[1]        # celda vacía -> nulo


def test_falla_si_falta_una_columna(tmp_path):
    ruta = tmp_path / "malo.csv"
    ruta.write_text("IdOpinion\n1\n", encoding="utf-8")
    extractor = CsvExtractorAsync("CSV", "stg.EncuestaCSV", ruta, COLUMNAS)

    with pytest.raises(ValueError, match="Clasificación"):
        asyncio.run(extractor.extraer())


def test_lee_el_csv_real_de_encuestas():
    from infrastructure.settings import cargar_configuracion, ruta_del_proyecto

    fuente = next(f for f in cargar_configuracion().fuentes_activas if f["Tipo"] == "CSV")
    extractor = CsvExtractorAsync(fuente["Nombre"], fuente["TablaDestino"],
                                  ruta_del_proyecto(fuente["Ruta"]), fuente["Columnas"])
    datos = asyncio.run(extractor.extraer())
    assert len(datos) == 500
    assert "Clasificacion" in datos.columns
