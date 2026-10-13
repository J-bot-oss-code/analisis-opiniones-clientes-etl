"""Punto de entrada de la aplicación ETL."""

from application.etl_setup import ejecutar_etl


def main():
    try:
        ejecutar_etl()
    except Exception as error:
        print(f"ETL detenido: {error}")
        raise


if __name__ == "__main__":
    main()
