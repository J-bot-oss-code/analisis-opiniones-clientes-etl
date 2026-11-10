"""Genera un CSV grande de encuestas para la prueba de rendimiento (RNF: 50,000 en < 5 min).

Uso:
    python scripts/generar_carga.py            # 50,000 filas
    python scripts/generar_carga.py 100000

Crea data/carga_encuestas.csv con las mismas columnas que surveys_part1.csv.
Para usarlo, cambia "Ruta" de la fuente CSV_Encuestas en config/appsettings.json.
"""

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "data" / "carga_encuestas.csv"

COMENTARIOS = {
    "Positiva": ["Excelente producto, lo recomiendo.", "Llegó rápido y funciona perfecto."],
    "Negativa": ["Muy mala calidad, se rompió rápido.", "No cumple lo que promete."],
    "Neutra": ["Ni malo ni excelente, simplemente regular.", "Cumple, sin mayor novedad."],
}
PUNTAJE = {"Positiva": (4, 5), "Negativa": (1, 2), "Neutra": (3, 3)}


def main(cantidad: int) -> None:
    aleatorio = random.Random(2026)  # semilla fija: siempre genera el mismo archivo
    inicio = date(2024, 1, 1)
    with open(DESTINO, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["IdOpinion", "IdCliente", "IdProducto", "Fecha", "Comentario",
                           "Clasificación", "PuntajeSatisfacción", "Fuente"])
        for i in range(1, cantidad + 1):
            clase = aleatorio.choice(list(COMENTARIOS))
            escritor.writerow([
                i, aleatorio.randint(1, 499), aleatorio.randint(1, 199),
                (inicio + timedelta(days=aleatorio.randint(0, 700))).isoformat(),
                aleatorio.choice(COMENTARIOS[clase]), clase,
                aleatorio.randint(*PUNTAJE[clase]), "EncuestaInterna",
            ])
    print(f"Generadas {cantidad:,} filas en {DESTINO}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 50_000)
