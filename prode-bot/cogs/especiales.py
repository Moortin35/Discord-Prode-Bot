import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from database import get_connection
from config import TIMEZONE as TZ_ARG, PUNTOS_CAMPEON


def _cierre_campeon():
    """Fecha límite para predecir campeón, configurable con
    /configurar_cierre_campeon. Si no está seteada, la predicción queda abierta."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM config WHERE clave = 'cierre_campeon'")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    try:
        return datetime.strptime(row["valor"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ_ARG)
    except ValueError:
        return None


async def autocomplete_equipo(interaction: discord.Interaction, current: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM equipos ORDER BY nombre")
    equipos = [fila["nombre"] for fila in cursor.fetchall()]
    conn.close()

    return [
        app_commands.Choice(name=equipo, value=equipo)
        for equipo in equipos
        if current.lower() in equipo.lower()
    ][:25]  # Discord limita a 25 opciones


class Especiales(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="predecir_campeon", description="Elegí qué equipo creés que ganará la Champions")
    @app_commands.describe(campeon="Equipo que creés será campeón")
    @app_commands.autocomplete(campeon=autocomplete_equipo)
    async def predecir_campeon(self, interaction: discord.Interaction, campeon: str):
        cierre = _cierre_campeon()
        if cierre and datetime.now(TZ_ARG) >= cierre:
            await interaction.response.send_message(
                f"La predicción de campeón ya está cerrada (cerró el {cierre.strftime('%d/%m %H:%M')}).",
                ephemeral=True
            )
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM equipos WHERE nombre = ?", (campeon,))
        if not cursor.fetchone():
            conn.close()
            await interaction.response.send_message(
                f"**{campeon}** no está entre los equipos del torneo. Elegí uno de la lista.",
                ephemeral=True
            )
            return

        cursor.execute(
            "INSERT OR IGNORE INTO usuarios (id, nombre) VALUES (?, ?)",
            (str(interaction.user.id), str(interaction.user.display_name))
        )

        cursor.execute("""
            INSERT INTO predicciones_especiales (usuario_id, campeon)
            VALUES (?, ?)
            ON CONFLICT(usuario_id)
            DO UPDATE SET campeon = ?
        """, (str(interaction.user.id), campeon, campeon))

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"Predicción guardada: creés que **{campeon}** ganará la Champions 🏆 (+{PUNTOS_CAMPEON} pts si acertás)",
            ephemeral=True
        )

    @app_commands.command(name="mi_campeon", description="Mostrá tu predicción de campeón")
    async def mi_campeon(self, interaction: discord.Interaction):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM predicciones_especiales WHERE usuario_id = ?", (str(interaction.user.id),))
        pred = cursor.fetchone()
        conn.close()

        if not pred or not pred["campeon"]:
            await interaction.response.send_message("Todavía no elegiste tu campeón.", ephemeral=True)
            return

        mensaje = f"Tu predicción de campeón: **{pred['campeon']}**"
        if pred["puntos_especiales"] is not None:
            mensaje += f"\nPuntos obtenidos: {pred['puntos_especiales']}"

        await interaction.response.send_message(mensaje, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Especiales(bot))
