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


def test_opciones_de_dimensiones_se_leen_de_appsettings():
    from datetime import date
    from infrastructure.factory import crear_opciones_dimensiones
    from infrastructure.settings import Configuracion

    opciones = crear_opciones_dimensiones(Configuracion({"Dimensiones": {
        "MiembroDesconocido": False, "Fecha": {"Inicio": "2023-05-01", "Fin": "2023-05-31"}}}))
    assert (opciones.fecha_inicio, opciones.fecha_fin) == (date(2023, 5, 1), date(2023, 5, 31))
    assert opciones.miembro_desconocido is False


def test_opciones_de_dimensiones_tienen_valores_por_defecto():
    from datetime import date
    from infrastructure.factory import crear_opciones_dimensiones
    from infrastructure.settings import Configuracion

    opciones = crear_opciones_dimensiones(Configuracion({}))
    assert (opciones.fecha_inicio, opciones.fecha_fin) == (date(2024, 1, 1), date(2025, 12, 31))
    assert opciones.miembro_desconocido is True


def test_opciones_de_dimensiones_rechazan_fechas_invalidas():
    import pytest
    from infrastructure.factory import crear_opciones_dimensiones
    from infrastructure.settings import Configuracion, ErrorConfiguracion

    with pytest.raises(ErrorConfiguracion):
        crear_opciones_dimensiones(Configuracion({"Dimensiones": {"Fecha": {"Inicio": "ayer"}}}))
    with pytest.raises(ErrorConfiguracion):
        crear_opciones_dimensiones(Configuracion({"Dimensiones": {"Fecha": {"Inicio": "2025-02-01", "Fin": "2025-01-01"}}}))
