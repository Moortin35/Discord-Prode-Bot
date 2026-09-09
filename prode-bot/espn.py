"""Cliente de la API pública de ESPN para la UEFA Champions League.

Se usa para dos cosas: importar el fixture de la fase liga (`/importar_fixture`)
y para el polling de resultados en vivo (`cogs/resultados_auto.py`).
"""
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo

from config import ESPN_LIGA, FECHAS_FASE_LIGA, TIMEZONE as TZ_ARG

BASE_URL = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{ESPN_LIGA}"
SCOREBOARD_URL = f"{BASE_URL}/scoreboard"

# Separación mínima entre dos jornadas de la fase liga. Los partidos de una misma
# fecha se juegan en días consecutivos (mar/mié/jue), y entre fechas pasan
# semanas, así que un corte de 3 días separa las jornadas sin ambigüedad.
DIAS_ENTRE_JORNADAS = 3


async def _get(session, params):
    async with session.get(SCOREBOARD_URL, params=params, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"ESPN respondió HTTP {resp.status}")
        return await resp.json()


async def obtener_eventos(fechas: list):
    """Devuelve los eventos de ESPN para una lista de fechas 'YYYYMMDD',
    deduplicados por ID. Los errores por fecha se loguean y no cortan el resto."""
    vistos = set()
    eventos = []

    async with aiohttp.ClientSession() as session:
        for fecha in fechas:
            try:
                data = await _get(session, {"dates": fecha, "limit": 500})
            except Exception as e:
                print(f"[espn] ❌ Error al consultar {fecha}: {e}")
                continue

            for event in data.get("events", []):
                eid = event.get("id")
                if eid and eid not in vistos:
                    vistos.add(eid)
                    eventos.append(event)

    return eventos


async def obtener_rango_fase_liga():
    """Lee el calendario de la temporada actual y devuelve (desde, hasta) como
    'YYYYMMDD' para la fase liga. Así el bot se adapta solo a cada temporada."""
    async with aiohttp.ClientSession() as session:
        data = await _get(session, {})

    calendario = data["leagues"][0].get("calendar") or []
    for bloque in calendario:
        for entrada in bloque.get("entries", []):
            if entrada.get("label") == "League Phase":
                desde = entrada["startDate"][:10].replace("-", "")
                hasta = entrada["endDate"][:10].replace("-", "")
                return desde, hasta

    raise RuntimeError("ESPN no devolvió la fase liga en el calendario de la temporada.")


async def obtener_fixture_fase_liga():
    """Devuelve los partidos de la fase liga ya parseados y con su jornada
    asignada, ordenados por fecha."""
    desde, hasta = await obtener_rango_fase_liga()

    async with aiohttp.ClientSession() as session:
        data = await _get(session, {"dates": f"{desde}-{hasta}", "limit": 500})

    partidos = []
    for event in data.get("events", []):
        partido = parsear_evento(event)
        if partido:
            partidos.append(partido)

    partidos.sort(key=lambda p: p["fecha_hora"])
    _asignar_jornadas(partidos)
    return partidos


def _asignar_jornadas(partidos):
    """Agrupa los partidos en jornadas cortando cada vez que hay un salto de más
    de DIAS_ENTRE_JORNADAS días. Muta la lista agregando la clave 'jornada'."""
    jornada = 1
    anterior = None

    for p in partidos:
        actual = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M").date()
        if anterior is not None and (actual - anterior).days > DIAS_ENTRE_JORNADAS:
            jornada += 1
        p["jornada"] = jornada
        anterior = actual

    if jornada != FECHAS_FASE_LIGA:
        print(
            f"[espn] ⚠️ Se detectaron {jornada} jornadas en vez de {FECHAS_FASE_LIGA}. "
            "Revisá el fixture importado antes de abrir las predicciones."
        )


def parsear_evento(event):
    """Extrae de un evento de ESPN los datos que le importan al prode.

    Devuelve None si el evento no tiene la forma esperada o si alguno de los dos
    equipos todavía no está definido (cruces por definir en fases eliminatorias).
    """
    try:
        competition = event["competitions"][0]
        estado = competition["status"]["type"]

        equipos = {c["homeAway"]: c for c in competition["competitors"]}
        local, visitante = equipos["home"], equipos["away"]

        fecha_utc = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ")
        fecha_local = fecha_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(TZ_ARG)
    except (KeyError, IndexError, ValueError) as e:
        print(f"[espn] Error parseando evento {event.get('id')}: {e}")
        return None

    pais_sede = (competition.get("venue") or {}).get("address", {}).get("country")

    return {
        "espn_id": str(event["id"]),
        "fecha_hora": fecha_local.strftime("%Y-%m-%d %H:%M"),
        # El país de la sede es el del local, que juega en su casa
        "local": _datos_equipo(local, pais_sede),
        "visitante": _datos_equipo(visitante),
        "goles_local": _goles(local),
        "goles_visitante": _goles(visitante),
        "status": estado.get("name", ""),
        "state": estado.get("state", ""),
        "completed": bool(estado.get("completed", False)),
    }


def _datos_equipo(competidor, pais=None):
    equipo = competidor["team"]
    nombre = equipo.get("displayName") or equipo.get("name")
    return {
        "nombre": nombre,
        "espn_id": str(equipo.get("id")),
        "nombre_corto": equipo.get("shortDisplayName") or nombre,
        "abreviatura": equipo.get("abbreviation") or "",
        "logo_url": equipo.get("logo"),
        "pais": pais,
    }


def _goles(competidor):
    try:
        return int(competidor.get("score") or 0)
    except (TypeError, ValueError):
        return 0
