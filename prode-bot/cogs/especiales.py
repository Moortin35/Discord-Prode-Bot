import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import get_connection
from flags_map import FLAG_CODES
from config import TIMEZONE as TZ_ARG

EQUIPOS = sorted(FLAG_CODES.keys())
CIERRE_ESPECIALES = datetime(2026, 6, 18, 13, 0, tzinfo=TZ_ARG)

PUNTOS_CAMPEON = 10

async def autocomplete_equipo(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=equipo, value=equipo)
        for equipo in EQUIPOS
        if current.lower() in equipo.lower()
    ][:25]  # Discord limita a 25 opciones

class Especiales(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="predecir_campeon", description="Elegí qué selección crees que será campeona del mundial")
    @app_commands.describe(campeon="Selección que crees será campeona")
    @app_commands.autocomplete(campeon=autocomplete_equipo)
    async def predecir_campeon(self, interaction: discord.Interaction, campeon: str):
        ahora = datetime.now(TZ_ARG)
        if ahora >= CIERRE_ESPECIALES:
            await interaction.response.send_message(
                "La predicción de campeón ya está cerrada (cierra al inicio de la Fecha 2).",
                ephemeral=True
            )
            return

        conn = get_connection()
        cursor = conn.cursor()

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
            f"Predicción guardada: creés que **{campeon}** será el campeón del mundial 🏆",
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
