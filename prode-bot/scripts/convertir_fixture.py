import csv
from datetime import datetime

ENTRADA = "data/fifa-world-cup-2026-ArgentinaStandardTime.csv"
SALIDA_FIXTURE = "data/fixture.csv"
SALIDA_RESULTADOS = "data/resultados.csv"

filas_fixture = []
filas_resultados = []

with open(ENTRADA, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for fila in reader:
        round_number = fila["Round Number"]

        # Solo fase de grupos (Round Number 1, 2 o 3)
        if round_number not in ("1", "2", "3"):
            continue

        fecha = datetime.strptime(fila["Date"], "%d/%m/%Y %H:%M")
        fecha_iso = fecha.strftime("%Y-%m-%d %H:%M")

        grupo = fila["Group"].replace("Group ", "").strip()

        filas_fixture.append({
            "equipo_local": fila["Home Team"],
            "equipo_visitante": fila["Away Team"],
            "fecha_hora": fecha_iso,
            "fase": "Grupos",
            "grupo": grupo
        })

        # Si ya tiene resultado cargado, lo guardamos aparte
        resultado = fila["Result"].strip()
        if resultado:
            try:
                goles_local, goles_visitante = [int(x.strip()) for x in resultado.split("-")]
                filas_resultados.append({
                    "match_number": fila["Match Number"],
                    "equipo_local": fila["Home Team"],
                    "equipo_visitante": fila["Away Team"],
                    "goles_local": goles_local,
                    "goles_visitante": goles_visitante
                })
            except ValueError:
                pass

# Escribir fixture.csv
with open(SALIDA_FIXTURE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["equipo_local", "equipo_visitante", "fecha_hora", "fase", "grupo"])
    writer.writeheader()
    writer.writerows(filas_fixture)

# Escribir resultados.csv (para cargar después con otro comando)
with open(SALIDA_RESULTADOS, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["match_number", "equipo_local", "equipo_visitante", "goles_local", "goles_visitante"])
    writer.writeheader()
    writer.writerows(filas_resultados)

print(f"Generados {len(filas_fixture)} partidos de fase de grupos en {SALIDA_FIXTURE}")
print(f"Generados {len(filas_resultados)} resultados ya jugados en {SALIDA_RESULTADOS}")