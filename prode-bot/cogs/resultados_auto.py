import os
import requests
import unicodedata
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from database import get_connection
from flags_map import ZAFRONIX_NAMES_INVERSO
from config import TIMEZONE as TZ_ARG

API_URL = "https://api.zafronix.com/fifa/worldcup/v1"


def normalizar(texto):
    """Normaliza texto: quita acentos, pasa a minúsculas, elimina espacios extra."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.strip().lower()


def get_fixtures_hoy():
    """Obtiene los partidos del 2026 y filtra los de hoy."""
    api_key = os.getenv("ZAFRONIX_API_KEY")
    if not api_key:
        print("[resultados_auto] ❌ ZAFRONIX_API_KEY no encontrada en .env")
        return []

    hoy = datetime.now(TZ_ARG).strftime("%Y-%m-%d")
    try:
        resp = requests.get(
            f"{API_URL}/matches",
            headers={"X-API-Key": api_key},
            params={"year": 2026},
            timeout=10
        )
        if resp.status_code != 200:
            print(f"[resultados_auto] Error HTTP: {resp.status_code}")
            return []
        data = resp.json().get("data", [])
        return [m for m in data if m.get("date", "").startswith(hoy)]
    except Exception as e:
        print(f"[resultados_auto] Error al obtener fixtures: {e}")
        return []


def buscar_en_db(home_raw, away_raw):
    """Busca el nombre de DB usando normalización para manejar encoding roto."""
    for key, val in ZAFRONIX_NAMES_INVERSO.items():
        if normalizar(key) == normalizar(home_raw):
            home_db = val
            break
    else:
        home_db = None

    for key, val in ZAFRONIX_NAMES_INVERSO.items():
        if normalizar(key) == normalizar(away_raw):
            away_db = val
            break
    else:
        away_db = None

    return home_db, away_db


def procesar_resultado(fixture):
    home_raw = fixture.get("homeTeam", "")
    away_raw = fixture.get("awayTeam", "")
    home_score = fixture.get("homeScore")
    away_score = fixture.get("awayScore")
    result = fixture.get("result", "")

    # Solo procesar si tiene resultado completo
    if not result or home_score is None or away_score is None:
        # Partido en curso: actualizar score parcial si existe
        if home_score is not None and away_score is not None:
            home_db, away_db = buscar_en_db(home_raw, away_raw)
            if home_db and away_db:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE partidos SET goles_local = ?, goles_visitante = ?
                    WHERE equipo_local = ? AND equipo_visitante = ? AND cerrado = 0
                """, (home_score, away_score, home_db, away_db))
                conn.commit()
                conn.close()
        return False

    home_db, away_db = buscar_en_db(home_raw, away_raw)

    if not home_db or not away_db:
        print(f"[resultados_auto] No mapeado: '{home_raw}' vs '{away_raw}'")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM partidos
        WHERE equipo_local = ? AND equipo_visitante = ? AND cerrado = 0
    """, (home_db, away_db))
    partido = cursor.fetchone()

    if not partido:
        conn.close()
        return False

    partido_id = partido["id"]

    cursor.execute(
        "UPDATE partidos SET goles_local = ?, goles_visitante = ?, cerrado = 1 WHERE id = ?",
        (home_score, away_score, partido_id)
    )

    cursor.execute("SELECT * FROM predicciones WHERE partido_id = ?", (partido_id,))
    predicciones = cursor.fetchall()

    for pred in predicciones:
        puntos = calcular_puntos(
            pred["pred_local"], pred["pred_visitante"],
            home_score, away_score
        )
        cursor.execute(
            "UPDATE predicciones SET puntos = ? WHERE id = ?",
            (puntos, pred["id"])
        )

    conn.commit()
    conn.close()

    print(f"[resultados_auto] ✅ Partido #{partido_id} cerrado: {home_db} {home_score}-{away_score} {away_db}")
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

    @tasks.loop(minutes=3)
    async def check_resultados(self):
        ahora = datetime.now(TZ_ARG)
        hora = ahora.hour

        # Solo correr entre las 13:00 y las 03:00
        if not (13 <= hora <= 23 or hora <= 3):
            return

        # Verificar si hay partidos hoy antes de consultar la API
        conn = get_connection()
        cursor = conn.cursor()
        hoy = ahora.strftime("%Y-%m-%d")
        inicio = f"{hoy} 06:00"
        fin = (ahora + timedelta(days=1)).strftime("%Y-%m-%d") + " 05:59"
        cursor.execute("""
            SELECT COUNT(*) as total FROM partidos
            WHERE fecha_hora >= ? AND fecha_hora <= ? AND cerrado = 0
        """, (inicio, fin))
        pendientes = cursor.fetchone()["total"]
        conn.close()

        if pendientes == 0:
            return  # no hay partidos pendientes hoy, no consultamos la API

        try:
            fixtures = get_fixtures_hoy()
            print(f"[resultados_auto] {ahora.strftime('%H:%M')} — {len(fixtures)} partidos hoy, {pendientes} pendientes en DB")
            for fixture in fixtures:
                procesar_resultado(fixture)
        except Exception as e:
            print(f"[resultados_auto] Error: {e}")

    @check_resultados.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ResultadosAuto(bot))