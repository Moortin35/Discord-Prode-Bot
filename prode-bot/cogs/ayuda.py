import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from config import TIMEZONE as TZ_ARG, PUNTOS_PLENO, PUNTOS_ACIERTO, PUNTOS_CAMPEON
from cogs.especiales import cierre_campeon


def _texto_cierre_campeon():
    """Línea sobre el cierre de la predicción de campeón, según cómo esté
    configurado en ese momento con /configurar_cierre_campeon."""
    cierre = cierre_campeon()

    if not cierre:
        return "⏳ La predicción de campeón todavía no tiene fecha de cierre."

    if datetime.now(TZ_ARG) >= cierre:
        return f"🔒 La predicción de campeón cerró el **{cierre.strftime('%d/%m/%Y')}**."

    return f"⏳ La predicción de campeón cierra el **{cierre.strftime('%d/%m/%Y a las %H:%M')}** hs."


class Ayuda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ayuda", description="Mostrá todos los comandos disponibles del prode")
    async def ayuda(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Comandos del Prode Champions",
            description="Guía rápida de todos los comandos disponibles.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="⚽ Predicciones",
            value=(
                "`/predecir` — Cargá tu pronóstico para un partido\n"
                "`/mis_predicciones` — Vé todos tus pronósticos y puntos\n"
                "`/mis_predicciones_hoy` — Vé tus pronósticos de los partidos de hoy\n"
                "`/predecir_campeon` — Elegí qué equipo ganará la Champions\n"
                "`/mi_campeon` — Vé tu predicción de campeón\n"
                f"\n{_texto_cierre_campeon()}"
            ),
            inline=False
        )

        embed.add_field(
            name="📅 Partidos",
            value=(
                "`/partidos_ayer` — Resultados de los partidos de ayer\n"
                "`/partidos_hoy` — Partidos del día con su ID y resultados\n"
                "`/partidos_manana` — Partidos programados para mañana\n"
                "`/listar_partidos` — Fixture completo del torneo"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Estadísticas",
            value=(
                "`/tabla` — Tabla de posiciones de la fase liga (36 equipos)\n"
                "`/fecha <1-8>` — Partidos de una fecha de la fase liga\n"
                "`/ranking` — Tabla de posiciones del prode"
            ),
            inline=False
        )

        embed.add_field(
            name="🎯 Cómo se puntúa",
            value=(
                f"🎯 **Pleno** — acertás el marcador exacto: **+{PUNTOS_PLENO} pts**\n"
                f"✅ **Acierto** — acertás ganador o empate: **+{PUNTOS_ACIERTO} pt**\n"
                "❌ **Fallo** — resultado incorrecto: **0 pts**\n"
                f"🏆 **Campeón** — acertás quién gana la Champions: **+{PUNTOS_CAMPEON} pts**"
            ),
            inline=False
        )

        embed.add_field(
            name="🔔 Avisos automáticos",
            value=(
                "Todos los días a las **12:00** el bot publica los partidos del día.\n"
                "Antes de cada partido, el bot avisa con **2hs** y **1h** de anticipación.\n"
                "Los resultados se cargan **automáticamente** al terminar cada partido."
            ),
            inline=False
        )

        embed.set_footer(text="💡 Tip: predecí antes de que empiece cada partido, ¡no se puede modificar después!")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Ayuda(bot))
