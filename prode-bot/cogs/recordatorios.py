import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, time
from database import get_connection
from utils import bandera
from config import TIMEZONE as TZ_ARG
from cogs.predicciones import construir_embed_partidos_hoy


class Recordatorios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_recordatorios.start()
        self.aviso_diario.start()

    def cog_unload(self):
        self.check_recordatorios.cancel()
        self.aviso_diario.cancel()
    

    @tasks.loop(minutes=15)
    async def check_recordatorios(self):
        conn = get_connection()
        cursor = conn.cursor()

        # Obtener canal configurado
        cursor.execute("SELECT valor FROM config WHERE clave = 'canal_recordatorios'")
        row = cursor.fetchone()
        if not row:
            conn.close()
            return

        canal_id = int(row["valor"])
        canal = self.bot.get_channel(canal_id)
        if not canal:
            conn.close()
            return

        ahora = datetime.now(TZ_ARG)

        # Partidos no cerrados
        cursor.execute("SELECT * FROM partidos WHERE cerrado = 0")
        partidos = cursor.fetchall()

        for p in partidos:
            fecha_partido = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ_ARG)
            delta = fecha_partido - ahora

            for tipo, horas in (("2h", 2), ("1h", 1)):
                limite_inferior = timedelta(hours=horas) - timedelta(minutes=15)
                limite_superior = timedelta(hours=horas)

                if limite_inferior <= delta <= limite_superior:
                    cursor.execute(
                        "SELECT 1 FROM recordatorios_enviados WHERE partido_id = ? AND tipo = ?",
                        (p["id"], tipo)
                    )
                    if cursor.fetchone():
                        continue  # ya se envió

                    hora_display = fecha_partido.strftime("%H:%M")
                    mensaje = (
                        f"⏰ **¡Faltan {horas} hora{'s' if horas > 1 else ''}!** "
                        f"{bandera(p['equipo_local'])} {p['equipo_local']} vs "
                        f"{bandera(p['equipo_visitante'])} {p['equipo_visitante']} — {hora_display} hs\n"
                        f"Cargá tu pronóstico con `/predecir partido_id:{p['id']}` antes de que empiece 🔥"
                    )
                    await canal.send(mensaje)

                    cursor.execute(
                        "INSERT INTO recordatorios_enviados (partido_id, tipo) VALUES (?, ?)",
                        (p["id"], tipo)
                    )
                    conn.commit()

        conn.close()

    @tasks.loop(time=time(12, 0, tzinfo=TZ_ARG))
    async def aviso_diario(self):
        cursor = get_connection().cursor()
        cursor.execute("SELECT valor FROM config WHERE clave = 'canal_recordatorios'")
        row = cursor.fetchone()
        cursor.connection.close()

        if not row:
            return

        canal = self.bot.get_channel(int(row["valor"]))
        if not canal:
            return

        embed = construir_embed_partidos_hoy()
        if embed is None:
            return  # no hay partidos hoy, no molestamos

        await canal.send(
            content="@everyone Los partidos del día de hoy son los siguientes 👇 ¡No se olviden de hacer sus predicciones! El ID está a la izquierda de cada partido.",
            embed=embed
        )

    @aviso_diario.before_loop
    async def before_aviso(self):
        await self.bot.wait_until_ready()

    @check_recordatorios.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Recordatorios(bot))