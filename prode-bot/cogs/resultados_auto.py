from discord.ext import commands, tasks
from datetime import datetime

from database import get_connection
from config import TIMEZONE as TZ_ARG, PUNTOS_PLENO, PUNTOS_ACIERTO
from espn import obtener_eventos, parsear_evento

STATUSES_IGNORAR = {"STATUS_SCHEDULED", "STATUS_POSTPONED", "STATUS_CANCELLED", "STATUS_DELAYED"}
STATUSES_EN_VIVO = {"STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD",
                    "STATUS_FIRST_HALF", "STATUS_SECOND_HALF"}
STATUSES_FINALES = {"STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}


def calcular_puntos(pred_local, pred_visitante, real_local, real_visitante):
    if pred_local == real_local and pred_visitante == real_visitante:
        return PUNTOS_PLENO
    if signo(pred_local - pred_visitante) == signo(real_local - real_visitante):
        return PUNTOS_ACIERTO
    return 0


def signo(n):
    if n > 0:
        return 1
    if n < 0:
        return -1
    return 0


def _buscar_partido(cursor, datos):
    """Busca el partido por el espn_id que quedó guardado al importar el fixture.

    Si el partido se cargó a mano y no tiene espn_id, cae al match por nombres,
    que funciona porque esos nombres también salen de ESPN.
    """
    cursor.execute(
        "SELECT id FROM partidos WHERE espn_id = ? AND cerrado = 0",
        (datos["espn_id"],)
    )
    partido = cursor.fetchone()
    if partido:
        return partido["id"]

    cursor.execute(
        "SELECT id FROM partidos WHERE equipo_local = ? AND equipo_visitante = ? AND cerrado = 0",
        (datos["local"]["nombre"], datos["visitante"]["nombre"])
    )
    partido = cursor.fetchone()
    return partido["id"] if partido else None


async def procesar_evento(event, bot=None):
    """Actualiza la DB si el partido está en curso o finalizó.
    Devuelve True solo cuando cierra un partido."""
    datos = parsear_evento(event)
    if not datos:
        return False

    status = datos["status"]
    if status in STATUSES_IGNORAR:
        return False

    # STATUS_END_PERIOD es ambiguo (puede ser el entretiempo): solo cerramos si
    # ESPN además marca completed=True.
    es_final = status in STATUSES_FINALES or datos["completed"] or datos["state"] == "post"
    if status == "STATUS_END_PERIOD" and not datos["completed"]:
        es_final = False

    goles_local = datos["goles_local"]
    goles_visitante = datos["goles_visitante"]

    conn = get_connection()
    cursor = conn.cursor()

    partido_id = _buscar_partido(cursor, datos)
    if partido_id is None:
        conn.close()
        return False

    if status in STATUSES_EN_VIVO and not es_final:
        cursor.execute(
            "UPDATE partidos SET goles_local = ?, goles_visitante = ? WHERE id = ?",
            (goles_local, goles_visitante, partido_id)
        )
        conn.commit()
        conn.close()
        return False

    if not es_final:
        print(
            f"[resultados_auto] ⚠️ Status desconocido para "
            f"{datos['local']['nombre']} vs {datos['visitante']['nombre']}: "
            f"'{status}' (state='{datos['state']}', completed={datos['completed']})"
        )
        conn.close()
        return False

    cursor.execute(
        "UPDATE partidos SET goles_local = ?, goles_visitante = ?, cerrado = 1 WHERE id = ?",
        (goles_local, goles_visitante, partido_id)
    )
    cursor.execute("SELECT * FROM predicciones WHERE partido_id = ?", (partido_id,))
    predicciones = cursor.fetchall()

    resultados_pred = []
    for pred in predicciones:
        puntos = calcular_puntos(pred["pred_local"], pred["pred_visitante"],
                                 goles_local, goles_visitante)
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
        f"[resultados_auto] ✅ Partido #{partido_id} finalizado (status='{status}'): "
        f"{datos['local']['nombre']} {goles_local}-{goles_visitante} {datos['visitante']['nombre']}"
    )

    if bot:
        await notificar_resultado_partido(
            bot, partido_id,
            datos["local"]["nombre"], datos["visitante"]["nombre"],
            goles_local, goles_visitante, resultados_pred
        )
    return True


async def notificar_resultado_partido(bot, partido_id, equipo_local, equipo_visitante,
                                      goles_local, goles_visitante, resultados_pred):
    """Envía al canal configurado un resumen de quién acertó el resultado del partido."""
    import discord
    from utils import nombre_corto

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

    plenos = [r for r in resultados_pred if r["puntos"] == PUNTOS_PLENO]
    aciertos = [r for r in resultados_pred if r["puntos"] == PUNTOS_ACIERTO]

    embed = discord.Embed(
        title=(f"📊 Resultado final — {nombre_corto(equipo_local)} "
               f"{goles_local}-{goles_visitante} {nombre_corto(equipo_visitante)}"),
        color=discord.Color.gold() if plenos else (discord.Color.green() if aciertos else discord.Color.red())
    )

    secciones = (
        (f"🎯 Pleno (+{PUNTOS_PLENO} pts)", plenos),
        (f"✅ Acierto (+{PUNTOS_ACIERTO} pt)", aciertos),
    )
    for titulo, lista in secciones:
        if not lista:
            continue
        lineas = []
        for r in lista:
            nombre = nombres.get(r["usuario_id"]) or f"<@{r['usuario_id']}>"
            lineas.append(f"**{nombre}** `{r['pred_local']}-{r['pred_visitante']}`")
        embed.add_field(name=f"{titulo} — {len(lista)}", value="\n".join(lineas), inline=False)

    if not plenos and not aciertos:
        embed.description = (
            "😬 Nadie acertó el resultado ni el ganador esta vez."
            if resultados_pred else
            "ℹ️ Nadie hizo una predicción para este partido."
        )

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

        # Los partidos de Champions arrancan 13:45 y 16:00 ARG; fuera de esa
        # franja no tiene sentido consultar la API.
        if not 13 <= ahora.hour <= 20:
            return

        hoy = ahora.strftime("%Y-%m-%d")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS total FROM partidos "
            "WHERE fecha_hora >= ? AND fecha_hora <= ? AND cerrado = 0",
            (f"{hoy} 00:00", f"{hoy} 23:59")
        )
        pendientes = cursor.fetchone()["total"]
        conn.close()

        if pendientes == 0:
            return

        try:
            eventos = await obtener_eventos([ahora.strftime("%Y%m%d")])
            print(
                f"[resultados_auto] {ahora.strftime('%H:%M')} — "
                f"{pendientes} pendientes, {len(eventos)} eventos recibidos."
            )
            for event in eventos:
                await procesar_evento(event, bot=self.bot)
        except Exception as e:
            print(f"[resultados_auto] Error en loop: {e}")

    @check_resultados.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ResultadosAuto(bot))
