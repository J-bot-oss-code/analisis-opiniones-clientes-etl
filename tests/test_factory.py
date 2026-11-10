import pytest

from infrastructure.factory import crear_extractores
from infrastructure.settings import ErrorConfiguracion, cargar_configuracion, crear_url_sql_server


class MotorFalso:
    pass


def test_crea_las_ocho_fuentes_del_json(monkeypatch):
    monkeypatch.setenv("API_COMENTARIOS_KEY", "llave")
    import logging
    extractores = crear_extractores(cargar_configuracion(), logging.getLogger("t"), MotorFalso)

    tablas = {e.tabla_destino for e in extractores}
    assert len(extractores) == 8
    assert {"stg.Opinion", "stg.EncuestaCSV", "stg.ComentarioAPI"} <= tablas


def test_falta_la_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("API_COMENTARIOS_KEY", raising=False)
    import logging
    config = cargar_configuracion(ruta_env=tmp_path / "no-existe.env")
    with pytest.raises(ErrorConfiguracion, match="API_COMENTARIOS_KEY"):
        crear_extractores(config, logging.getLogger("t"), MotorFalso)


def test_url_con_autenticacion_windows_no_lleva_clave():
    url = crear_url_sql_server({"Servidor": r".\SQLEXPRESS", "BaseDatos": "OpinionesCliente_DW",
                                "Driver": "ODBC Driver 17 for SQL Server",
                                "AutenticacionWindows": True})
    assert url.query["Trusted_Connection"] == "yes"
    assert url.password is None
