import discord
from discord import app_commands
from discord.ext import commands


class Ayuda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ayuda", description="Mostrá todos los comandos disponibles del prode")
    async def ayuda(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Comandos del Prode Mundial 2026",
            description="Guía rápida de todos los comandos disponibles.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="⚽ Predicciones",
            value=(
                "`/predecir` — Cargá tu pronóstico para un partido\n"
                "`/mis_predicciones` — Vé tus pronósticos y puntos obtenidos\n"
                "`/predecir_campeon` — Elegí qué selección será campeona\n"
                "`/mi_campeon` — Vé tu predicción de campeón"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Información",
            value=(
                "`/partidos_hoy` — Partidos del día con su ID (para predecir)\n"
                "`/listar_partidos` — Vé el fixture completo\n"
                "`/grupo <letra>` — Tabla de posiciones de un grupo (ej: `/grupo A`)\n"
                "`/ranking` — Tabla de posiciones del prode"
            ),
            inline=False
        )

        embed.add_field(
            name="🔔 Avisos automáticos",
            value=(
                "Todos los días a las 12:00 el bot publica los partidos del día.\n"
                "Antes de cada partido, el bot recuerda con 2hs y 1h de anticipación."
            ),
            inline=False
        )

        embed.set_footer(text="💡 Tip: predecí antes de que empiece cada partido, ¡no se puede modificar después!")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Ayuda(bot))