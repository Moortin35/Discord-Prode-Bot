import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from database import get_connection
from image_gen import generar_tabla_liga
from utils import nombre_corto, bandera
from config import FECHAS_FASE_LIGA


def calcular_tabla():
    """Arma la tabla de la fase liga a partir de los partidos ya cerrados.

    Devuelve (filas, jugados, totales). Cada fila es un dict listo para
    `generar_tabla_liga`, ordenado por puntos, diferencia de gol y goles a favor
    (los tres primeros criterios de desempate de la UEFA)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM partidos WHERE fase = 'Liga' ORDER BY fecha_hora")
    partidos = cursor.fetchall()
    cursor.execute("SELECT nombre, espn_id, logo_url FROM equipos")
    equipos_db = {fila["nombre"]: dict(fila) for fila in cursor.fetchall()}
    conn.close()

    tabla = {}

    def entrada(nombre):
        if nombre not in tabla:
            tabla[nombre] = {"equipo": nombre, "pj": 0, "pg": 0, "pe": 0,
                             "pp": 0, "gf": 0, "gc": 0, "pts": 0}
        return tabla[nombre]

    jugados = 0
    for p in partidos:
        local = entrada(p["equipo_local"])
        visitante = entrada(p["equipo_visitante"])

        if not p["cerrado"]:
            continue

        jugados += 1
        gl, gv = p["goles_local"], p["goles_visitante"]

        local["pj"] += 1
        visitante["pj"] += 1
        local["gf"] += gl
        local["gc"] += gv
        visitante["gf"] += gv
        visitante["gc"] += gl

        if gl > gv:
            local["pg"] += 1
            local["pts"] += 3
            visitante["pp"] += 1
        elif gl < gv:
            visitante["pg"] += 1
            visitante["pts"] += 3
            local["pp"] += 1
        else:
            local["pe"] += 1
            visitante["pe"] += 1
            local["pts"] += 1
            visitante["pts"] += 1

    filas = []
    for nombre, datos in tabla.items():
        datos["dg"] = datos["gf"] - datos["gc"]
        datos["espn_id"] = equipos_db.get(nombre, {}).get("espn_id")
        datos["logo_url"] = equipos_db.get(nombre, {}).get("logo_url")
        filas.append(datos)

    filas.sort(key=lambda f: (f["pts"], f["dg"], f["gf"]), reverse=True)
    return filas, jugados, len(partidos)


class Tabla(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tabla", description="Mostrá la tabla de posiciones de la fase liga")
    async def tabla(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Sin permiso de adjuntar, Discord publica el embed pero descarta la
        # imagen sin avisar, y la tabla sale vacía. Mejor decirlo de frente.
        if interaction.guild:
            permisos = interaction.channel.permissions_for(interaction.guild.me)
            if not permisos.attach_files:
                await interaction.followup.send(
                    "No puedo publicar la tabla: me falta el permiso "
                    "**Adjuntar archivos** en este canal.\n"
                    "Un admin puede dármelo en *Editar canal → Permisos*."
                )
                return

        filas, jugados, totales = calcular_tabla()

        if not filas:
            await interaction.followup.send(
                "Todavía no hay partidos de la fase liga cargados. "
                "Un admin tiene que correr `/importar_fixture`."
            )
            return

        subtitulo = f"{jugados} de {totales} partidos jugados"
        # Dibujar la tabla es sincrónico y descarga escudos con requests, así que
        # va a un thread: en el event loop congelaría al bot entero varios
        # segundos y los demás comandos morirían con "Unknown interaction".
        imagen = await asyncio.to_thread(generar_tabla_liga, filas, subtitulo)
        file = discord.File(imagen, filename="tabla_liga.png")

        # La imagen va como adjunto suelto y no dentro de un embed. Con
        # `attachment://` Discord guardaba el PNG y devolvía su URL de CDN, pero
        # ningún cliente lo dibujaba: el embed salía con el hueco de la tabla.
        contenido = (
            "## 📊 Tabla — Fase Liga\n"
            f"-# {subtitulo} · Desempate: puntos → diferencia de gol → goles a favor"
        )
        await interaction.followup.send(content=contenido, file=file)

    @app_commands.command(name="fecha", description="Mostrá los partidos de una fecha de la fase liga")
    @app_commands.describe(numero=f"Número de fecha (1 a {FECHAS_FASE_LIGA})")
    async def fecha(self, interaction: discord.Interaction, numero: int):
        if not 1 <= numero <= FECHAS_FASE_LIGA:
            await interaction.response.send_message(
                f"La fase liga tiene {FECHAS_FASE_LIGA} fechas. Elegí un número del 1 al {FECHAS_FASE_LIGA}.",
                ephemeral=True
            )
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM partidos
            WHERE fase = 'Liga' AND jornada = ?
            ORDER BY fecha_hora, id
        """, (numero,))
        partidos = cursor.fetchall()
        conn.close()

        if not partidos:
            await interaction.response.send_message(
                f"No hay partidos cargados para la fecha {numero}.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"⚽ Fase Liga — Fecha {numero}",
            color=discord.Color.blurple()
        )

        # Un field por día para no pasarnos del límite de 1024 caracteres
        por_dia = {}
        for p in partidos:
            fecha_p = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M")
            por_dia.setdefault(fecha_p.strftime("%A %d/%m"), []).append((fecha_p, p))

        for dia, lista in por_dia.items():
            lineas = []
            for fecha_p, p in lista:
                local = f'{bandera(p["equipo_local"])} {nombre_corto(p["equipo_local"])}'
                visitante = f'{bandera(p["equipo_visitante"])} {nombre_corto(p["equipo_visitante"])}'

                if p["cerrado"]:
                    resultado = f"`{p['goles_local']}-{p['goles_visitante']}`"
                elif p["goles_local"] is not None:
                    resultado = f"`{p['goles_local']}-{p['goles_visitante']}` 🔴"
                else:
                    resultado = "`vs`"

                lineas.append(
                    f"`#{p['id']:>3}` {fecha_p.strftime('%H:%M')} · "
                    f"{local} {resultado} {visitante}"
                )

            valor = "\n".join(lineas)
            if len(valor) > 1024:
                valor = valor[:1010] + "\n... (truncado)"
            embed.add_field(name=dia, value=valor, inline=False)

        embed.set_footer(text="Usá /predecir partido_id:<ID> para cargar tu pronóstico")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Tabla(bot))
