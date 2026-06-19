import csv
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import get_connection
from utils import bandera
from cogs.resultados_auto import notificar_resultado_partido

from flags_map import FLAG_CODES

EQUIPOS = sorted(FLAG_CODES.keys())


async def autocomplete_equipo(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=equipo, value=equipo)
        for equipo in EQUIPOS
        if current.lower() in equipo.lower()
    ][:25]

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

        cursor.execute("SELECT * FROM partidos WHERE id = ?", (partido_id,))
        partido = cursor.fetchone()

        # Calcular puntos de todas las predicciones para ese partido
        cursor.execute("SELECT * FROM predicciones WHERE partido_id = ?", (partido_id,))
        predicciones = cursor.fetchall()

        resultados_pred = []
        for pred in predicciones:
            puntos = calcular_puntos(
                pred["pred_local"], pred["pred_visitante"],
                goles_local, goles_visitante
            )
            cursor.execute(
                "UPDATE predicciones SET puntos = ? WHERE id = ?",
                (puntos, pred["id"])
            )
            resultados_pred.append({
                "usuario_id": pred["usuario_id"],
                "pred_local": pred["pred_local"],
                "pred_visitante": pred["pred_visitante"],
                "puntos": puntos,
            })

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"Resultado cargado: Partido #{partido_id} — {goles_local}-{goles_visitante}. "
            f"Puntos calculados para {len(predicciones)} predicciones."
        )

        if partido:
            await notificar_resultado_partido(
                self.bot, partido_id,
                partido["equipo_local"], partido["equipo_visitante"],
                goles_local, goles_visitante,
                resultados_pred
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

        embed = discord.Embed(title="⚽ Fixture del Prode Mundial", color=discord.Color.blue())

        # Agrupar por fase (y grupo si aplica) para no saturar
        grupos_actuales = {}
        for p in partidos:
            fase_info = f"{p['fase']} {p['grupo']}" if p["grupo"] else p["fase"]
            grupos_actuales.setdefault(fase_info, []).append(p)

        for fase_info, lista in grupos_actuales.items():
            lineas = []
            for p in lista:
                fecha_display = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M").strftime("%d/%m %H:%M")
                estado = f"`{p['goles_local']}-{p['goles_visitante']}`" if p["cerrado"] else "_pendiente_"
                lineas.append(
                    f"`#{p['id']:>3}` {bandera(p['equipo_local'])} {p['equipo_local']} vs {bandera(p['equipo_visitante'])} {p['equipo_visitante']} — {fecha_display} {estado}"
                )
            valor = "\n".join(lineas)
            if len(valor) > 1024:
                valor = valor[:1010] + "\n... (truncado)"
            embed.add_field(name=fase_info, value=valor, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cargar_fixture", description="Carga el fixture completo desde data/fixture.csv (solo admin)")
    async def cargar_fixture(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            with open("data/fixture.csv", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                filas = list(reader)
        except FileNotFoundError:
            await interaction.followup.send("No se encontró el archivo data/fixture.csv")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cargados = 0
        errores = []

        for i, fila in enumerate(filas, start=1):
            try:
                cursor.execute(
                    "INSERT INTO partidos (equipo_local, equipo_visitante, fecha_hora, fase, grupo) VALUES (?, ?, ?, ?, ?)",
                    (fila["equipo_local"], fila["equipo_visitante"], fila["fecha_hora"], fila["fase"], fila.get("grupo") or None)
                )
                cargados += 1
            except Exception as e:
                errores.append(f"Fila {i}: {e}")

        conn.commit()
        conn.close()

        mensaje = f"Fixture cargado: {cargados} partidos insertados."
        if errores:
            mensaje += f"\n{len(errores)} errores:\n" + "\n".join(errores[:10])

        await interaction.followup.send(mensaje)


    @app_commands.command(name="cargar_resultados_masivo", description="Carga resultados desde data/resultados.csv (solo admin)")
    async def cargar_resultados_masivo(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            with open("data/resultados.csv", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                filas = list(reader)
        except FileNotFoundError:
            await interaction.followup.send("No se encontró el archivo data/resultados.csv")
            return

        conn = get_connection()
        cursor = conn.cursor()
        actualizados = 0
        no_encontrados = []

        for fila in filas:
            cursor.execute(
                "SELECT id FROM partidos WHERE equipo_local = ? AND equipo_visitante = ?",
                (fila["equipo_local"], fila["equipo_visitante"])
            )
            partido = cursor.fetchone()

            if not partido:
                no_encontrados.append(f"{fila['equipo_local']} vs {fila['equipo_visitante']}")
                continue

            partido_id = partido["id"]
            goles_local = int(fila["goles_local"])
            goles_visitante = int(fila["goles_visitante"])

            cursor.execute(
                "UPDATE partidos SET goles_local = ?, goles_visitante = ?, cerrado = 1 WHERE id = ?",
                (goles_local, goles_visitante, partido_id)
            )

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

            actualizados += 1

        conn.commit()
        conn.close()

        mensaje = f"Resultados cargados: {actualizados} partidos actualizados."
        if no_encontrados:
            mensaje += f"\n{len(no_encontrados)} no encontrados:\n" + "\n".join(no_encontrados[:10])

        await interaction.followup.send(mensaje)

    @app_commands.command(name="configurar_canal_recordatorios", description="Configura el canal donde se enviarán los recordatorios (solo admin)")
    async def configurar_canal_recordatorios(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO config (clave, valor) VALUES ('canal_recordatorios', ?)
            ON CONFLICT(clave) DO UPDATE SET valor = ?
        """, (str(interaction.channel_id), str(interaction.channel_id)))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ Este canal ({interaction.channel.mention}) fue configurado para recibir los recordatorios de partidos."
        )


    @app_commands.command(name="reabrir_partido", description="Deshace el resultado de un partido y reabre las predicciones (solo admin)")
    @app_commands.describe(partido_id="ID del partido a reabrir")
    async def reabrir_partido(self, interaction: discord.Interaction, partido_id: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM partidos WHERE id = ?", (partido_id,))
        partido = cursor.fetchone()

        if not partido:
            await interaction.response.send_message(f"No existe el partido #{partido_id}.", ephemeral=True)
            conn.close()
            return

        if not partido["cerrado"]:
            await interaction.response.send_message(f"El partido #{partido_id} no está cerrado.", ephemeral=True)
            conn.close()
            return

        # Reabrir el partido
        cursor.execute(
            "UPDATE partidos SET goles_local = NULL, goles_visitante = NULL, cerrado = 0 WHERE id = ?",
            (partido_id,)
        )

        # Resetear puntos de todas las predicciones de ese partido
        cursor.execute(
            "UPDATE predicciones SET puntos = NULL WHERE partido_id = ?",
            (partido_id,)
        )

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ Partido #{partido_id} ({partido['equipo_local']} vs {partido['equipo_visitante']}) reabierto. "
            f"Resultado eliminado y puntos reseteados."
        )

    @app_commands.command(name="cargar_campeon", description="Carga el campeón real del mundial (solo admin)")
    @app_commands.describe(campeon="Selección campeona real")
    @app_commands.autocomplete(campeon=autocomplete_equipo)
    async def cargar_campeon(self, interaction: discord.Interaction, campeon: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO resultados_especiales (id, campeon, cerrado)
            VALUES (1, ?, 1)
            ON CONFLICT(id)
            DO UPDATE SET campeon = ?, cerrado = 1
        """, (campeon, campeon))

        cursor.execute("SELECT * FROM predicciones_especiales")
        predicciones = cursor.fetchall()

        for pred in predicciones:
            puntos = PUNTOS_CAMPEON if _normalizar(pred["campeon"]) == _normalizar(campeon) else 0
            cursor.execute(
                "UPDATE predicciones_especiales SET puntos_especiales = ? WHERE usuario_id = ?",
                (puntos, pred["usuario_id"])
            )

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"Campeón cargado: **{campeon}**. Puntos calculados para {len(predicciones)} usuarios."
        )



def calcular_puntos(pred_local, pred_visitante, real_local, real_visitante):
    if pred_local == real_local and pred_visitante == real_visitante:
        return 3

    pred_resultado = signo(pred_local - pred_visitante)
    real_resultado = signo(real_local - real_visitante)

    if pred_resultado == real_resultado:
        return 1

    return 0

PUNTOS_CAMPEON = 10

def _normalizar(texto):
    return (texto or "").strip().lower()

def signo(n):
    if n > 0:
        return 1
    elif n < 0:
        return -1
    return 0


async def setup(bot):
    await bot.add_cog(Admin(bot))

