import aiohttp
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from database import get_connection
from config import TIMEZONE as TZ_ARG
from flags_map import ESPN_NAMES_INVERSO
import unicodedata

ESPN_API_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

def normalizar(texto):
    """Normaliza texto: quita acentos, pasa a minúsculas, elimina espacios extra."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.strip().lower()

def buscar_en_db(home_raw, away_raw):
    """Busca el nombre de DB usando normalización para manejar encoding roto."""
    home_db = None
    away_db = None
    for key, val in ESPN_NAMES_INVERSO.items():
        if normalizar(key) == normalizar(home_raw):
            home_db = val
            break
    for key, val in ESPN_NAMES_INVERSO.items():
        if normalizar(key) == normalizar(away_raw):
            away_db = val
            break
    return home_db, away_db

async def get_fixtures_espn(fechas: list):
    """
    Obtiene eventos de ESPN para una o más fechas (formato YYYYMMDD).
    Devuelve lista de eventos deduplicada por ID de competencia.
    """
    vistos = set()
    eventos = []

    async with aiohttp.ClientSession() as session:
        for fecha in fechas:
            try:
                async with session.get(f"{ESPN_API_URL}?dates={fecha}", timeout=10) as resp:
                    if resp.status != 200:
                        print(f"[resultados_auto] ❌ Error HTTP ESPN ({fecha}): {resp.status}")
                        continue
                    data = await resp.json()
                    for event in data.get("events", []):
                        eid = event.get("id")
                        if eid and eid not in vistos:
                            vistos.add(eid)
                            eventos.append(event)
            except Exception as e:
                print(f"[resultados_auto] ❌ Error al conectar con ESPN ({fecha}): {e}")

    return eventos

async def procesar_resultado_espn(event, bot=None):
    """Extrae los datos de ESPN y actualiza la DB si el partido está en curso o finalizó."""
    try:
        competition = event["competitions"][0]
        status_obj  = competition["status"]["type"]
        status      = status_obj.get("name", "")
        completed   = status_obj.get("completed", False)
        state       = status_obj.get("state", "")

        team1 = competition["competitors"][0]
        team2 = competition["competitors"][1]

        if team1["homeAway"] == "home":
            home_raw, away_raw = team1["team"]["name"], team2["team"]["name"]
            home_score, away_score = int(team1.get("score", 0) or 0), int(team2.get("score", 0) or 0)
        else:
            home_raw, away_raw = team2["team"]["name"], team1["team"]["name"]
            home_score, away_score = int(team2.get("score", 0) or 0), int(team1.get("score", 0) or 0)

    except (KeyError, IndexError, ValueError) as e:
        print(f"[resultados_auto] Error parseando JSON de ESPN: {e}")
        return False

    home_db, away_db = buscar_en_db(home_raw, away_raw)
    if not home_db or not away_db:
        STATUSES_IGNORAR = {"STATUS_SCHEDULED", "STATUS_POSTPONED", "STATUS_CANCELLED", "STATUS_DELAYED"}
        if status not in STATUSES_IGNORAR:
            print(f"[resultados_auto] ⚠️  No se reconoció: '{home_raw}' vs '{away_raw}' (status={status})")
        return False

    # --- Clasificación del status ---
    STATUSES_IGNORAR   = {"STATUS_SCHEDULED", "STATUS_POSTPONED", "STATUS_CANCELLED", "STATUS_DELAYED"}
    STATUSES_EN_VIVO   = {"STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD",
                          "STATUS_FIRST_HALF", "STATUS_SECOND_HALF"}
    STATUSES_FINALES   = {"STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}

    # Partido terminado: nombre explícito, flag completed=True, o state=="post"
    es_final = status in STATUSES_FINALES or completed or state == "post"
    # STATUS_END_PERIOD es ambiguo (puede ser descanso); solo cerramos si completed=True
    if status == "STATUS_END_PERIOD" and not completed:
        es_final = False

    if status in STATUSES_IGNORAR:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM partidos WHERE equipo_local = ? AND equipo_visitante = ? AND cerrado = 0",
        (home_db, away_db)
    )
    partido = cursor.fetchone()

    if not partido:
        conn.close()
        return False

    partido_id = partido["id"]

    if status in STATUSES_EN_VIVO and not es_final:
        # Actualizar marcador en vivo sin cerrar el partido
        cursor.execute(
            "UPDATE partidos SET goles_local = ?, goles_visitante = ? WHERE id = ?",
            (home_score, away_score, partido_id)
        )
        conn.commit()
        conn.close()
        return False

    elif es_final:
        cursor.execute(
            "UPDATE partidos SET goles_local = ?, goles_visitante = ?, cerrado = 1 WHERE id = ?",
            (home_score, away_score, partido_id)
        )
        cursor.execute("SELECT * FROM predicciones WHERE partido_id = ?", (partido_id,))
        predicciones = cursor.fetchall()

        resultados_pred = []
        for pred in predicciones:
            puntos = calcular_puntos(pred["pred_local"], pred["pred_visitante"], home_score, away_score)
            cursor.execute("UPDATE predicciones SET puntos = ? WHERE id = ?", (puntos, pred["id"]))
            resultados_pred.append({
                "usuario_id": pred["usuario_id"],
                "pred_local": pred["pred_local"],
                "pred_visitante": pred["pred_visitante"],
                "puntos": puntos,
            })

        conn.commit()
        conn.close()
        print(
            f"[resultados_auto] ✅ Partido #{partido_id} finalizado "
            f"(status='{status}', completed={completed}, state='{state}'): "
            f"{home_db} {home_score}-{away_score} {away_db}"
        )

        if bot:
            await notificar_resultado_partido(
                bot, partido_id, home_db, away_db, home_score, away_score, resultados_pred
            )
        return True

    else:
        # Status genuinamente desconocido — loguearlo para investigar
        print(
            f"[resultados_auto] ⚠️ Status desconocido para {home_db} vs {away_db}: "
            f"'{status}' (state='{state}', completed={completed})"
        )
        conn.close()
        return False


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

async def notificar_resultado_partido(bot, partido_id, equipo_local, equipo_visitante, goles_local, goles_visitante, resultados_pred):
    """Envía al canal configurado un resumen de quién acertó el resultado del partido."""
    import discord
    from utils import bandera

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM config WHERE clave = 'canal_recordatorios'")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return

    canal = bot.get_channel(int(row["valor"]))
    if not canal:
        return

    # Recuperar nombres de usuarios
    conn = get_connection()
    cursor = conn.cursor()
    ids = [r["usuario_id"] for r in resultados_pred]
    nombres = {}
    if ids:
        placeholders = ",".join("?" * len(ids))
        cursor.execute(f"SELECT id, nombre FROM usuarios WHERE id IN ({placeholders})", ids)
        for row in cursor.fetchall():
            nombres[row["id"]] = row["nombre"]
    conn.close()

    plenos   = [r for r in resultados_pred if r["puntos"] == 3]
    aciertos = [r for r in resultados_pred if r["puntos"] == 1]

    bl = bandera(equipo_local)
    bv = bandera(equipo_visitante)

    embed = discord.Embed(
        title=f"📊 Resultado final — {bl} {equipo_local} {goles_local}-{goles_visitante} {bv} {equipo_visitante}",
        color=discord.Color.gold() if plenos else (discord.Color.green() if aciertos else discord.Color.red())
    )

    if plenos:
        lineas = []
        for r in plenos:
            nombre = nombres.get(r["usuario_id"], f"<@{r['usuario_id']}>")
            lineas.append(f"**{nombre}** `{r['pred_local']}-{r['pred_visitante']}`")
        embed.add_field(name=f"🎯 Pleno (+3 pts) — {len(plenos)}", value="\n".join(lineas), inline=False)

    if aciertos:
        lineas = []
        for r in aciertos:
            nombre = nombres.get(r["usuario_id"], f"<@{r['usuario_id']}>")
            lineas.append(f"**{nombre}** `{r['pred_local']}-{r['pred_visitante']}`")
        embed.add_field(name=f"✅ Acierto (+1 pt) — {len(aciertos)}", value="\n".join(lineas), inline=False)

    if not plenos and not aciertos:
        if resultados_pred:
            embed.description = "😬 Nadie acertó el resultado ni el ganador esta vez."
        else:
            embed.description = "ℹ️ Nadie hizo una predicción para este partido."

    await canal.send(embed=embed)


class ResultadosAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_resultados.start()

    def cog_unload(self):
        self.check_resultados.cancel()

    @tasks.loop(minutes=3)
    async def check_resultados(self):
        ahora = datetime.now(TZ_ARG)
        hora  = ahora.hour

        # Activo de 13:00 a 03:59 ARG (cubre el rango real de partidos: 13hs a ~03hs)
        # Fuera de ese rango no hay partidos, no tiene sentido consultar
        if not (hora >= 13 or hora <= 3):
            return

        conn = get_connection()
        cursor = conn.cursor()

        # Calcular ventana de jornada correcta según la hora actual
        # Si estamos entre medianoche y las 05:59, la jornada empezó "ayer"
        if hora < 6:
            inicio_jornada = (ahora - timedelta(days=1)).strftime("%Y-%m-%d") + " 06:00"
        else:
            inicio_jornada = ahora.strftime("%Y-%m-%d") + " 06:00"

        fin_jornada = (
            datetime.strptime(inicio_jornada, "%Y-%m-%d %H:%M") + timedelta(days=1)
        ).strftime("%Y-%m-%d %H:%M")  # = 06:00 del día siguiente = equivalente a 05:59

        cursor.execute(
            "SELECT COUNT(*) as total FROM partidos WHERE fecha_hora >= ? AND fecha_hora < ? AND cerrado = 0",
            (inicio_jornada, fin_jornada)
        )
        pendientes = cursor.fetchone()["total"]
        conn.close()

        if pendientes == 0:
            return

        # Entre medianoche y las 03:59 ARG, ESPN puede tener los partidos
        # indexados bajo la fecha anterior → pedimos ambas fechas para no perder nada
        fechas_espn = [ahora.strftime("%Y%m%d")]
        if hora < 6:
            fecha_ayer = (ahora - timedelta(days=1)).strftime("%Y%m%d")
            fechas_espn.append(fecha_ayer)

        try:
            eventos_espn = await get_fixtures_espn(fechas_espn)
            print(
                f"[resultados_auto] {ahora.strftime('%H:%M')} — "
                f"ESPN {'+'.join(fechas_espn)}. "
                f"{pendientes} pendientes, {len(eventos_espn)} eventos recibidos."
            )
            for event in eventos_espn:
                await procesar_resultado_espn(event, bot=self.bot)
        except Exception as e:
            print(f"[resultados_auto] Error en loop: {e}")

    @check_resultados.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ResultadosAuto(bot))
