import csv
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from database import get_connection
from espn import obtener_fixture_fase_liga
from utils import nombre_corto, guardar_equipo, invalidar_cache
from config import FECHAS_FASE_LIGA, PUNTOS_CAMPEON
from cogs.resultados_auto import notificar_resultado_partido, calcular_puntos


def equipos_registrados():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM equipos ORDER BY nombre")
    equipos = [fila["nombre"] for fila in cursor.fetchall()]
    conn.close()
    return equipos


async def autocomplete_equipo(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=equipo, value=equipo)
        for equipo in equipos_registrados()
        if current.lower() in equipo.lower()
    ][:25]


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="importar_fixture", description="Importa la fase liga completa desde ESPN (solo admin)")
    @app_commands.default_permissions(administrator=True)
    async def importar_fixture(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            partidos = await obtener_fixture_fase_liga()
        except Exception as e:
            await interaction.followup.send(f"❌ No se pudo consultar ESPN: {e}")
            return

        if not partidos:
            await interaction.followup.send("ESPN no devolvió partidos para la fase liga.")
            return

        conn = get_connection()
        cursor = conn.cursor()

        nuevos = 0
        actualizados = 0

        for p in partidos:
            for lado in ("local", "visitante"):
                guardar_equipo(cursor, p[lado])

            # El espn_id hace idempotente el comando: re-importar solo actualiza
            # fecha y jornada (útil cuando la UEFA reprograma un partido).
            cursor.execute("SELECT id FROM partidos WHERE espn_id = ?", (p["espn_id"],))
            existente = cursor.fetchone()

            if existente:
                cursor.execute(
                    "UPDATE partidos SET fecha_hora = ?, jornada = ?, "
                    "equipo_local = ?, equipo_visitante = ? WHERE id = ?",
                    (p["fecha_hora"], p["jornada"], p["local"]["nombre"],
                     p["visitante"]["nombre"], existente["id"])
                )
                actualizados += 1
            else:
                cursor.execute(
                    "INSERT INTO partidos (equipo_local, equipo_visitante, fecha_hora, "
                    "fase, jornada, espn_id) VALUES (?, ?, ?, 'Liga', ?, ?)",
                    (p["local"]["nombre"], p["visitante"]["nombre"],
                     p["fecha_hora"], p["jornada"], p["espn_id"])
                )
                nuevos += 1

        conn.commit()
        conn.close()
        invalidar_cache()

        jornadas = sorted({p["jornada"] for p in partidos})
        resumen = ", ".join(
            f"F{j}: {sum(1 for p in partidos if p['jornada'] == j)}" for j in jornadas
        )

        embed = discord.Embed(
            title="✅ Fixture importado desde ESPN",
            description=(
                f"**{nuevos}** partidos nuevos · **{actualizados}** actualizados\n"
                f"**{len(equipos_registrados())}** equipos registrados"
            ),
            color=discord.Color.green()
        )
        embed.add_field(name=f"Partidos por fecha ({len(jornadas)} de {FECHAS_FASE_LIGA})",
                        value=resumen, inline=False)

        if len(jornadas) != FECHAS_FASE_LIGA:
            embed.set_footer(text="⚠️ La cantidad de fechas no es la esperada. Revisá el fixture con /fecha.")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="cargar_partido", description="Carga un partido manualmente (solo admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        local="Equipo local",
        visitante="Equipo visitante",
        fecha_hora="Fecha y hora del partido (formato: YYYY-MM-DD HH:MM)",
        fase="Fase del torneo (ej: Liga, Playoff, Octavos, Cuartos, Semis, Final)",
        jornada=f"Número de fecha (1 a {FECHAS_FASE_LIGA}) — solo para la fase Liga"
    )
    @app_commands.autocomplete(local=autocomplete_equipo, visitante=autocomplete_equipo)
    async def cargar_partido(self, interaction: discord.Interaction, local: str, visitante: str,
                             fecha_hora: str, fase: str, jornada: int = None):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO partidos (equipo_local, equipo_visitante, fecha_hora, fase, jornada) "
            "VALUES (?, ?, ?, ?, ?)",
            (local, visitante, fecha_hora, fase, jornada)
        )
        conn.commit()
        partido_id = cursor.lastrowid
        conn.close()

        info_jornada = f" — Fecha {jornada}" if jornada else ""
        await interaction.response.send_message(
            f"Partido #{partido_id} cargado: **{local} vs {visitante}** — {fecha_hora} ({fase}{info_jornada})"
        )

    @app_commands.command(name="cargar_resultado", description="Carga el resultado de un partido (solo admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        partido_id="ID del partido",
        goles_local="Goles del equipo local",
        goles_visitante="Goles del equipo visitante"
    )
    async def cargar_resultado(self, interaction: discord.Interaction, partido_id: int,
                               goles_local: int, goles_visitante: int):
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

        cursor.execute("SELECT * FROM predicciones WHERE partido_id = ?", (partido_id,))
        predicciones = cursor.fetchall()

        resultados_pred = []
        for pred in predicciones:
            puntos = calcular_puntos(
                pred["pred_local"], pred["pred_visitante"],
                goles_local, goles_visitante
            )
            cursor.execute("UPDATE predicciones SET puntos = ? WHERE id = ?", (puntos, pred["id"]))
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
        cursor.execute("SELECT * FROM partidos ORDER BY fecha_hora, id")
        partidos = cursor.fetchall()
        conn.close()

        if not partidos:
            await interaction.response.send_message(
                "No hay partidos cargados todavía. Corré `/importar_fixture`."
            )
            return

        embed = discord.Embed(title="⚽ Fixture — UEFA Champions League", color=discord.Color.blurple())

        # Un field por fecha de la fase liga (o por fase, en eliminatorias)
        secciones = {}
        for p in partidos:
            if p["fase"] == "Liga" and p["jornada"]:
                clave = f"Fase Liga — Fecha {p['jornada']}"
            else:
                clave = p["fase"] or "Sin fase"
            secciones.setdefault(clave, []).append(p)

        # Discord permite 25 fields por embed
        for clave, lista in list(secciones.items())[:25]:
            lineas = []
            for p in lista:
                fecha_display = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M").strftime("%d/%m %H:%M")
                estado = f"`{p['goles_local']}-{p['goles_visitante']}`" if p["cerrado"] else "_pendiente_"
                lineas.append(
                    f"`#{p['id']:>3}` {nombre_corto(p['equipo_local'])} vs "
                    f"{nombre_corto(p['equipo_visitante'])} — {fecha_display} {estado}"
                )
            valor = "\n".join(lineas)
            if len(valor) > 1024:
                valor = valor[:1000] + "\n... (usá `/fecha`)"
            embed.add_field(name=clave, value=valor, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cargar_resultados_masivo", description="Carga resultados desde data/resultados.csv (solo admin)")
    @app_commands.default_permissions(administrator=True)
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
            for pred in cursor.fetchall():
                puntos = calcular_puntos(
                    pred["pred_local"], pred["pred_visitante"],
                    goles_local, goles_visitante
                )
                cursor.execute("UPDATE predicciones SET puntos = ? WHERE id = ?", (puntos, pred["id"]))

            actualizados += 1

        conn.commit()
        conn.close()

        mensaje = f"Resultados cargados: {actualizados} partidos actualizados."
        if no_encontrados:
            mensaje += f"\n{len(no_encontrados)} no encontrados:\n" + "\n".join(no_encontrados[:10])

        await interaction.followup.send(mensaje)

    @app_commands.command(name="configurar_canal_recordatorios", description="Configura el canal donde se enviarán los recordatorios (solo admin)")
    @app_commands.default_permissions(administrator=True)
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

    @app_commands.command(name="configurar_cierre_campeon", description="Define hasta cuándo se puede predecir el campeón (solo admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(fecha_hora="Fecha y hora límite (formato: YYYY-MM-DD HH:MM)")
    async def configurar_cierre_campeon(self, interaction: discord.Interaction, fecha_hora: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("No tenés permisos para usar este comando.", ephemeral=True)
            return

        try:
            datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "Formato inválido. Usá `YYYY-MM-DD HH:MM` (ej: `2026-10-13 13:00`).", ephemeral=True
            )
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO config (clave, valor) VALUES ('cierre_campeon', ?)
            ON CONFLICT(clave) DO UPDATE SET valor = ?
        """, (fecha_hora, fecha_hora))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ La predicción de campeón cierra el **{fecha_hora}**."
        )

    @app_commands.command(name="reabrir_partido", description="Deshace el resultado de un partido y reabre las predicciones (solo admin)")
    @app_commands.default_permissions(administrator=True)
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

        cursor.execute(
            "UPDATE partidos SET goles_local = NULL, goles_visitante = NULL, cerrado = 0 WHERE id = ?",
            (partido_id,)
        )
        cursor.execute("UPDATE predicciones SET puntos = NULL WHERE partido_id = ?", (partido_id,))

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ Partido #{partido_id} ({partido['equipo_local']} vs {partido['equipo_visitante']}) reabierto. "
            f"Resultado eliminado y puntos reseteados."
        )

    @app_commands.command(name="cargar_campeon", description="Carga el campeón real del torneo (solo admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(campeon="Equipo campeón real")
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


def _normalizar(texto):
    return (texto or "").strip().lower()


async def setup(bot):
    await bot.add_cog(Admin(bot))
