import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import get_connection
from utils import bandera



class Predicciones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="predecir", description="Cargá tu predicción para un partido")
    @app_commands.describe(
        partido_id="ID del partido (usá /listar_partidos para verlo)",
        goles_local="Tu predicción de goles del equipo local",
        goles_visitante="Tu predicción de goles del equipo visitante"
    )
    async def predecir(self, interaction: discord.Interaction, partido_id: int, goles_local: int, goles_visitante: int):
        if goles_local < 0 or goles_visitante < 0:
            await interaction.response.send_message("Los goles no pueden ser negativos.", ephemeral=True)
            return

        conn = get_connection()
        cursor = conn.cursor()

        # Verificar que el partido existe
        cursor.execute("SELECT * FROM partidos WHERE id = ?", (partido_id,))
        partido = cursor.fetchone()

        if not partido:
            await interaction.response.send_message(f"No existe el partido #{partido_id}.", ephemeral=True)
            conn.close()
            return

        # Verificar que el partido no haya empezado/cerrado
        if partido["cerrado"]:
            await interaction.response.send_message("Este partido ya finalizó, no podés predecir.", ephemeral=True)
            conn.close()
            return

        try:
            fecha_partido = datetime.strptime(partido["fecha_hora"], "%Y-%m-%d %H:%M")
            if datetime.now() >= fecha_partido:
                await interaction.response.send_message("Ya no podés predecir, el partido ya comenzó.", ephemeral=True)
                conn.close()
                return
        except ValueError:
            pass  # si el formato de fecha falla, no bloqueamos por esto

        # Registrar usuario si no existe
        cursor.execute(
            "INSERT OR IGNORE INTO usuarios (id, nombre) VALUES (?, ?)",
            (str(interaction.user.id), str(interaction.user.display_name))
        )

        # Insertar o actualizar predicción (UPSERT)
        cursor.execute("""
            INSERT INTO predicciones (usuario_id, partido_id, pred_local, pred_visitante)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(usuario_id, partido_id)
            DO UPDATE SET pred_local = ?, pred_visitante = ?
        """, (str(interaction.user.id), partido_id, goles_local, goles_visitante, goles_local, goles_visitante))

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"Predicción guardada: **{partido['equipo_local']} {goles_local} - {goles_visitante} {partido['equipo_visitante']}**",
            ephemeral=True
        )

    @app_commands.command(name="ranking", description="Mostrá la tabla de posiciones del prode")
    async def ranking(self, interaction: discord.Interaction):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.nombre, COALESCE(SUM(p.puntos), 0) AS total_puntos,
                   COUNT(CASE WHEN p.puntos IS NOT NULL THEN 1 END) AS partidos_jugados,
                   COUNT(CASE WHEN p.puntos = 3 THEN 1 END) AS exactos,
                   COUNT(CASE WHEN p.puntos = 1 THEN 1 END) AS acertados
            FROM usuarios u
            LEFT JOIN predicciones p ON u.id = p.usuario_id
            GROUP BY u.id
            ORDER BY total_puntos DESC, exactos DESC
        """)
        filas = cursor.fetchall()
        conn.close()

        if not filas:
            await interaction.response.send_message("Todavía no hay nadie registrado en el prode.")
            return

        embed = discord.Embed(title="🏆 Ranking del Prode Mundial", color=discord.Color.gold())

        medallas = {1: "🥇", 2: "🥈", 3: "🥉"}

        lineas = []
        for i, fila in enumerate(filas, start=1):
            pos = medallas.get(i, f"#{i}")
            lineas.append(
                f"{pos} **{fila['nombre']}** — {fila['total_puntos']} pts "
                f"({fila['partidos_jugados']} jugados, {fila['exactos']} exactos, {fila['acertados']} acertados)"
            )

        texto = "\n".join(lineas)
        if len(texto) > 4000:
            texto = texto[:4000] + "\n... (truncado)"

        embed.description = texto
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mis_predicciones", description="Mostrá todas tus predicciones cargadas")
    async def mis_predicciones(self, interaction: discord.Interaction):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, pa.equipo_local, pa.equipo_visitante, pa.fecha_hora, pa.cerrado,
                   pa.goles_local AS real_local, pa.goles_visitante AS real_visitante
            FROM predicciones p
            JOIN partidos pa ON p.partido_id = pa.id
            WHERE p.usuario_id = ?
            ORDER BY pa.fecha_hora
        """, (str(interaction.user.id),))
        predicciones = cursor.fetchall()
        conn.close()

        if not predicciones:
            await interaction.response.send_message("No tenés predicciones cargadas todavía.", ephemeral=True)
            return

        embed = discord.Embed(title="📋 Mis predicciones", color=discord.Color.green())

        lineas = []
        for p in predicciones:
            fecha_display = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M").strftime("%d/%m %H:%M")
            tu_pred = f"{p['pred_local']}-{p['pred_visitante']}"
            local = f"{bandera(p['equipo_local'])} {p['equipo_local']}"
            visitante = f"{bandera(p['equipo_visitante'])} {p['equipo_visitante']}"
            if p["cerrado"]:
                resultado = f"{p['real_local']}-{p['real_visitante']}"
                pts = p["puntos"] if p["puntos"] is not None else 0
                emoji_pts = "🎯" if pts == 3 else ("✅" if pts == 1 else "❌")
                lineas.append(f"`#{p['partido_id']:>3}` {local} vs {visitante} — {fecha_display} | Pred: `{tu_pred}` Real: `{resultado}` {emoji_pts} +{pts}")
            else:
                lineas.append(f"`#{p['partido_id']:>3}` {local} vs {visitante} — {fecha_display} | Pred: `{tu_pred}` ⏳")

        texto = "\n".join(lineas)
        if len(texto) > 4000:
            texto = texto[:4000] + "\n... (truncado)"

        embed.description = texto
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Predicciones(bot))