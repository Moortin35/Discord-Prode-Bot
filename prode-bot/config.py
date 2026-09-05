from zoneinfo import ZoneInfo

# Cambiar esta línea para adaptar el bot a otro país/zona horaria
TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")

# --- Torneo -----------------------------------------------------------------
TORNEO = "UEFA Champions League"

# Slug de la liga en la API de ESPN
ESPN_LIGA = "uefa.champions"

# La fase liga se juega a 8 fechas, con 36 equipos en una sola tabla
FECHAS_FASE_LIGA = 8
EQUIPOS_FASE_LIGA = 36

# Corte de posiciones al terminar la fase liga
CLASIFICAN_DIRECTO = 8    # 1-8   → Octavos de final
CLASIFICAN_PLAYOFF = 24   # 9-24  → Playoff de octavos; 25-36 quedan eliminados

# --- Puntaje ----------------------------------------------------------------
PUNTOS_PLENO = 3      # marcador exacto
PUNTOS_ACIERTO = 1    # ganador o empate acertado
PUNTOS_CAMPEON = 10   # predicción de campeón acertada
