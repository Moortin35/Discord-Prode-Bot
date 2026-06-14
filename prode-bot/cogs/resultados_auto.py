import os
import discord
import requests
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from database import get_connection
from flags_map import API_NAMES_INVERSO
from config import TIMEZONE as TZ_ARG

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
LEAGUE_ID = 1
SEASON = 2026


def get_fixtures_hoy():
    """Obtiene los partidos del día desde API-Football."""
    hoy = datetime.now(TZ_ARG).strftime("%Y-%m-%d")
    resp = requests.get(
        f"{API_URL}/fixtures",
        headers=HEADERS,
        params={"league": LEAGUE_ID, "season": SEASON, "date": hoy},
        timeout=10
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("response", [])


def procesar_resultado(fixture):
    """Dado un fixture de API-Football, intenta cerrar el partido en la DB."""
    status = fixture["fixture"]["status"]["short"]

    # Solo procesar partidos terminados (FT = Full Time, AET = After Extra Time, PEN = Penalties)
    if status not in ("FT", "AET", "PEN"):
        return False

    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]
    goles_local = fixture["goals"]["home"]
    goles_visitante = fixture["goals"]["away"]

    if goles_local is None or goles_visitante is None:
        return False

    # Convertir nombres API → nombres DB
    home_db = API_NAMES_INVERSO.get(home)
    away_db = API_NAMES_INVERSO.get(away)

    if not home_db or not away_db:
        print(f"[resultados_auto] Nombres no mapeados: {home} vs {away}")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # Buscar el partido en la DB que no esté cerrado
    cursor.execute("""
        SELECT id FROM partidos
        WHERE equipo_local = ? AND equipo_visitante = ? AND cerrado = 0
    """, (home_db, away_db))
    partido = cursor.fetchone()

    if not partido:
        conn.close()
        return False  # ya estaba cerrado o no existe

    partido_id = partido["id"]

    # Cerrar el partido y calcular puntos
    cursor.execute(
        "UPDATE partidos SET goles_local = ?, goles_visitante = ?, cerrado = 1 WHERE id = ?",
        (goles_local, goles_visitante, partido_id)
    )

    cursor.execute("SELECT * FROM predicciones WHERE partido_id = ?", (partido_id,))
    predicciones = cursor.fetchall()

    for pred in predicciones:
        puntos = calcular_puntos(
            pred["pred_local"], pred["pred_visitante"],
            goles_local, goles_visitante
        )
        cursor.execute(
            "UPDATE predicciones SET puntos = ? WHERE id = ?",
            (puntos, pred["id"])
        )

    conn.commit()
    conn.close()

    print(f"[resultados_auto] Partido #{partido_id} cerrado: {home_db} {goles_local}-{goles_visitante} {away_db}")
    return True


def calcular_puntos(pred_local, pred_visitante, real_local, real_visitante):
    if pred_local == real_local and pred_visitante == real_visitante:
        return 3
    pred_res = signo(pred_local - pred_visitante)
    real_res = signo(real_local - real_visitante)
    return 1 if pred_res == real_res else 0


def signo(n):
    if n > 0: return 1
    if n < 0: return -1
    return 0


class ResultadosAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_resultados.start()

    def cog_unload(self):
        self.check_resultados.cancel()

    @tasks.loop(minutes=10)
    async def check_resultados(self):
        ahora = datetime.now(TZ_ARG)

        # Solo correr entre las 13:00 y las 03:00 (horario de partidos)
        hora = ahora.hour
        if not (13 <= hora <= 23 or hora <= 3):
            return

        try:
            fixtures = get_fixtures_hoy()
            for fixture in fixtures:
                procesar_resultado(fixture)
        except Exception as e:
            print(f"[resultados_auto] Error: {e}")

    @check_resultados.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ResultadosAuto(bot))