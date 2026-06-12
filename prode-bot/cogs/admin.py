import discord
from discord import app_commands
from discord.ext import commands
from database import get_connection

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="cargar_partido", description="Carga un nuevo partido (solo admin)")
    @app_commands.describe(
        local="Equipo local",
        visitante="Equipo visitante",
        fecha_hora="Fecha y hora del partido (formato: YYYY-MM-DD HH:MM)",
        fase="Fase del torneo (ej: Grupos, Octavos, Cuartos, Semis, Final)",
        grupo="Grupo del mundial (ej: A, B, C...) - solo para fase de Grupos"
    )
    async def cargar_partido(self, interaction: discord.Interaction, local: str, visitante: str, fecha_hora: str, fase: str, grupo: str = None):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO partidos (equipo_local, equipo_visitante, fecha_hora, fase, grupo) VALUES (?, ?, ?, ?, ?)",
            (local, visitante, fecha_hora, fase, grupo)
        )
        conn.commit()
        partido_id = cursor.lastrowid
        conn.close()

        info_grupo = f" (Grupo {grupo})" if grupo else ""
        await interaction.response.send_message(
            f"Partido #{partido_id} cargado: **{local} vs {visitante}** — {fecha_hora} ({fase}{info_grupo})"
        )

    @app_commands.command(name="cargar_resultado", description="Carga el resultado de un partido (solo admin)")
    @app_commands.describe(
        partido_id="ID del partido",
        goles_local="Goles del equipo local",
        goles_visitante="Goles del equipo visitante"
    )
    async def cargar_resultado(self, interaction: discord.Interaction, partido_id: int, goles_local: int, goles_visitante: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE partidos SET goles_local = ?, goles_visitante = ?, cerrado = 1 WHERE id = ?",
            (goles_local, goles_visitante, partido_id)
        )
        conn.commit()

        # Calcular puntos de todas las predicciones para ese partido
        cursor.execute("SELECT * FROM predicciones WHERE partido_id = ?", (partido_id,))
        predicciones = cursor.fetchall()

        for pred in predicciones:
            puntos = calcular_puntos(
                pred["pred_local"], pred["pred_visitante"],
                goles_local, goles_visitante
            )
            cursor.execute(
                "UPDATE predicciones SET puntos = ? WHERE id = ?",
                (puntos, pred["id"])
            )

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"Resultado cargado: Partido #{partido_id} — {goles_local}-{goles_visitante}. "
            f"Puntos calculados para {len(predicciones)} predicciones."
        )

    @app_commands.command(name="listar_partidos", description="Lista todos los partidos cargados")
    async def listar_partidos(self, interaction: discord.Interaction):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM partidos ORDER BY fecha_hora")
        partidos = cursor.fetchall()
        conn.close()

        if not partidos:
            await interaction.response.send_message("No hay partidos cargados todavía.")
            return

        lineas = []
        for p in partidos:
            estado = f"{p['goles_local']}-{p['goles_visitante']}" if p["cerrado"] else "Pendiente"
            fase_info = f"{p['fase']} {p['grupo']}" if p["grupo"] else p["fase"]
            lineas.append(f"#{p['id']} | {p['equipo_local']} vs {p['equipo_visitante']} | {p['fecha_hora']} | {fase_info} | {estado}")

        texto = "\n".join(lineas)
        if len(texto) > 1900:
            texto = texto[:1900] + "\n... (truncado)"

        await interaction.response.send_message(f"```\n{texto}\n```")


def calcular_puntos(pred_local, pred_visitante, real_local, real_visitante):
    if pred_local == real_local and pred_visitante == real_visitante:
        return 3

    pred_resultado = signo(pred_local - pred_visitante)
    real_resultado = signo(real_local - real_visitante)

    if pred_resultado == real_resultado:
        return 1

    return 0


def signo(n):
    if n > 0:
        return 1
    elif n < 0:
        return -1
    return 0


async def setup(bot):
    await bot.add_cog(Admin(bot))