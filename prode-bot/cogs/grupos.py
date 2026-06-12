import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import get_connection
from utils import bandera
from image_gen import generar_tabla_grupo


class Grupos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="grupo", description="Mostrá la tabla de posiciones de un grupo")
    @app_commands.describe(letra="Letra del grupo (A, B, C, ...)")
    async def grupo(self, interaction: discord.Interaction, letra: str):
        letra = letra.strip().upper()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM partidos
            WHERE fase = 'Grupos' AND grupo = ?
            ORDER BY fecha_hora
        """, (letra,))
        partidos = cursor.fetchall()
        conn.close()

        if not partidos:
            await interaction.response.send_message(f"No se encontraron partidos para el grupo {letra}.", ephemeral=True)
            return

        tabla = {}

        def get_equipo(nombre):
            if nombre not in tabla:
                tabla[nombre] = {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "PTS": 0}
            return tabla[nombre]

        for p in partidos:
            local = p["equipo_local"]
            visitante = p["equipo_visitante"]

            get_equipo(local)
            get_equipo(visitante)

            if not p["cerrado"]:
                continue

            gl, gv = p["goles_local"], p["goles_visitante"]

            eq_local = get_equipo(local)
            eq_visitante = get_equipo(visitante)

            eq_local["PJ"] += 1
            eq_visitante["PJ"] += 1
            eq_local["GF"] += gl
            eq_local["GC"] += gv
            eq_visitante["GF"] += gv
            eq_visitante["GC"] += gl

            if gl > gv:
                eq_local["PG"] += 1
                eq_local["PTS"] += 3
                eq_visitante["PP"] += 1
            elif gl < gv:
                eq_visitante["PG"] += 1
                eq_visitante["PTS"] += 3
                eq_local["PP"] += 1
            else:
                eq_local["PE"] += 1
                eq_visitante["PE"] += 1
                eq_local["PTS"] += 1
                eq_visitante["PTS"] += 1

        filas = []
        for equipo, datos in tabla.items():
            dg = datos["GF"] - datos["GC"]
            filas.append((equipo, datos["PJ"], datos["PG"], datos["PE"], datos["PP"], datos["GF"], datos["GC"], dg, datos["PTS"]))

        filas.sort(key=lambda x: (x[8], x[7], x[5]), reverse=True)


        # Generar imagen de la tabla
        imagen_path = generar_tabla_grupo(letra, filas)
        file = discord.File(imagen_path, filename=f"grupo_{letra}.png")

        embed = discord.Embed(title=f"📊 Tabla — Grupo {letra}", color=discord.Color.purple())
        embed.set_image(url=f"attachment://grupo_{letra}.png")

        # Sección de partidos
        lineas_partidos = []
        for p in partidos:  
            fecha_display = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M").strftime("%d/%m %H:%M")
            local = f"{bandera(p['equipo_local'])} {p['equipo_local']}"
            visitante = f"{bandera(p['equipo_visitante'])} {p['equipo_visitante']}"

            if p["cerrado"]:
                resultado = f"`{p['goles_local']} - {p['goles_visitante']}`"
            else:
                resultado = "vs"

            lineas_partidos.append(f"{local} {resultado} {visitante} — _{fecha_display}_")

        valor_partidos = "\n".join(lineas_partidos)
        if len(valor_partidos) > 1024:
            valor_partidos = valor_partidos[:1010] + "\n... (truncado)"

        embed.add_field(name="Partidos", value=valor_partidos, inline=False)

        await interaction.response.send_message(embed=embed, file=file)



async def setup(bot):
    await bot.add_cog(Grupos(bot))