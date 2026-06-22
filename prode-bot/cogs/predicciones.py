import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from database import get_connection
from utils import bandera
from config import TIMEZONE as TZ_ARG
from zoneinfo import ZoneInfo

ARG = ZoneInfo("America/Argentina/Buenos_Aires")

def construir_embed_partidos_hoy():
    ahora = datetime.now(TZ_ARG)

    if ahora.hour < 6:
        inicio_jornada = (ahora - timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        inicio_jornada = ahora.replace(hour=6, minute=0, second=0, microsecond=0)

    fin_jornada = inicio_jornada + timedelta(hours=24)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM partidos
        WHERE fecha_hora >= ? AND fecha_hora < ?
        ORDER BY fecha_hora
    """, (inicio_jornada.strftime("%Y-%m-%d %H:%M"), fin_jornada.strftime("%Y-%m-%d %H:%M")))
    partidos = cursor.fetchall()
    conn.close()

    if not partidos:
        return None

    embed = discord.Embed(
        title=f"📅 Partidos de hoy — {inicio_jornada.strftime('%d/%m/%Y')}",
        color=discord.Color.blue()
    )

    lineas = []
    for p in partidos:
        fecha_p = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M")
        hora = fecha_p.strftime("%H:%M")
        sufijo = " (+1)" if fecha_p.date() > inicio_jornada.date() else ""

        local = f"{bandera(p['equipo_local'])} {p['equipo_local']}"
        visitante = f"{bandera(p['equipo_visitante'])} {p['equipo_visitante']}"

        if p["cerrado"]:
            resultado = f"`{p['goles_local']} - {p['goles_visitante']}` ✅"
        elif p["goles_local"] is not None and p["goles_visitante"] is not None:
            resultado = f"`{p['goles_local']} - {p['goles_visitante']}` 🔴 EN VIVO"
        else:
            resultado = "_pendiente_"

        lineas.append(f"`#{p['id']}` — {hora}{sufijo} hs | {local} vs {visitante} — {resultado}")

    embed.description = "\n".join(lineas)
    embed.set_footer(text="Usá /predecir partido_id:<ID> para cargar tu pronóstico")

    return embed


ORDEN_FASES = ["Grupos", "Dieciseisavos", "Octavos", "Cuartos", "Semis", "Final"]

def _label_pagina(fase, subfase):
    """Devuelve el título de la página según fase y subfase."""
    if fase == "Grupos":
        return f"📋 Mis predicciones — Fecha {subfase}"
    labels = {
        "Dieciseisavos": "📋 Mis predicciones — 16avos de Final",
        "Octavos":       "📋 Mis predicciones — Octavos de Final",
        "Cuartos":       "📋 Mis predicciones — Cuartos de Final",
        "Semis":         "📋 Mis predicciones — Semifinales",
        "Final":         "📋 Mis predicciones — Final y 3er Puesto",
    }
    return labels.get(fase, f"📋 Mis predicciones — {fase}")


def _construir_paginas(predicciones):
    from collections import defaultdict

    grupos_preds = [p for p in predicciones if p["fase"] == "Grupos"]
    otras_preds  = [p for p in predicciones if p["fase"] != "Grupos"]

    paginas = []

    # ── Fase de Grupos: dividir en 3 fechas de 24 partidos ──────────────────
    if grupos_preds:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM partidos
            WHERE fase = 'Grupos'
            ORDER BY fecha_hora, id
        """)
        orden_global = {row["id"]: idx for idx, row in enumerate(cursor.fetchall())}
        conn.close()

        por_fecha = defaultdict(list)
        for p in grupos_preds:
            pos = orden_global.get(p["partido_id"], 0)
            fecha_num = (pos // 24) + 1
            por_fecha[fecha_num].append(p)

        for fecha_num in [1, 2, 3]:  # siempre las 3 fechas
            preds_fecha = sorted(por_fecha.get(fecha_num, []), key=lambda x: x["fecha_hora"])
            paginas.append((f"📋 Mis predicciones — Fecha {fecha_num}", preds_fecha))

    # ── Fases eliminatorias ──────────────────────────────────────────────────
    fases_orden = ["Dieciseisavos", "Octavos", "Cuartos", "Semis", "Final"]
    por_fase = defaultdict(list)
    for p in otras_preds:
        por_fase[p["fase"]].append(p)

    for fase in fases_orden:
        if fase in por_fase:
            paginas.append((_label_pagina(fase, None), por_fase[fase]))

    # Páginas placeholder para fases futuras sin predicciones aún
    fases_con_preds = set(por_fase.keys())
    for fase in fases_orden:
        if fase not in fases_con_preds:
            paginas.append((_label_pagina(fase, None), []))

    return paginas


def _construir_embed_pagina(titulo, preds, pagina_actual, total_paginas):
    embed = discord.Embed(title=titulo, color=discord.Color.green())

    if not preds:
        embed.description = "_Todavía no hay predicciones para esta fase._"
        pts_total = 0
    else:
        lineas = []
        pts_total = 0
        for p in preds:
            fecha_display = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M").strftime("%d/%m %H:%M")
            tu_pred = f"{p['pred_local']}-{p['pred_visitante']}"
            local    = f"{bandera(p['equipo_local'])} {p['equipo_local']}"
            visitante = f"{bandera(p['equipo_visitante'])} {p['equipo_visitante']}"
            if p["cerrado"]:
                resultado = f"{p['real_local']}-{p['real_visitante']}"
                pts = p["puntos"] if p["puntos"] is not None else 0
                pts_total += pts
                emoji_pts = "🎯" if pts == 3 else ("✅" if pts == 1 else "❌")
                lineas.append(
                    f"`#{p['partido_id']:>3}` {local} vs {visitante} — {fecha_display}\n"
                    f"　　Pred: `{tu_pred}` · Real: `{resultado}` {emoji_pts} **+{pts} pts**"
                )
            else:
                lineas.append(
                    f"`#{p['partido_id']:>3}` {local} vs {visitante} — {fecha_display}\n"
                    f"　　Pred: `{tu_pred}` ⏳"
                )

        embed.description = "\n".join(lineas)

    cerrados = [p for p in preds if p["cerrado"]]
    if cerrados:
        embed.add_field(
            name="Puntos en esta página",
            value=f"**{pts_total} pts** de {len(cerrados)} partido{'s' if len(cerrados) != 1 else ''} jugado{'s' if len(cerrados) != 1 else ''}",
            inline=False
        )

    embed.set_footer(text=f"Página {pagina_actual + 1} de {total_paginas}")
    return embed


class PrediccionesView(discord.ui.View):
    def __init__(self, paginas, pagina_actual=0):
        super().__init__(timeout=120)
        self.paginas = paginas          # lista de (titulo, [preds])
        self.pagina_actual = pagina_actual
        self._actualizar_botones()

    def _actualizar_botones(self):
        self.btn_anterior.disabled = self.pagina_actual == 0
        self.btn_siguiente.disabled = self.pagina_actual == len(self.paginas) - 1

    def _embed_actual(self):
        titulo, preds = self.paginas[self.pagina_actual]
        return _construir_embed_pagina(titulo, preds, self.pagina_actual, len(self.paginas))

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def btn_anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_actual -= 1
        self._actualizar_botones()
        await interaction.response.edit_message(embed=self._embed_actual(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def btn_siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_actual += 1
        self._actualizar_botones()
        await interaction.response.edit_message(embed=self._embed_actual(), view=self)

    async def on_timeout(self):
        # Deshabilitar botones cuando expira
        for item in self.children:
            item.disabled = True



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
            fecha_partido = datetime.strptime(partido["fecha_hora"], "%Y-%m-%d %H:%M").replace(tzinfo=ARG)
            if datetime.now(ARG) >= fecha_partido:
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
        await interaction.response.defer()

        conn = get_connection()
        cursor = conn.cursor()

        # --- SEGUNDO CHEQUEO: recalcular puntos faltantes ---
        cursor.execute("""
            SELECT id, goles_local, goles_visitante
            FROM partidos
            WHERE cerrado = 1 AND goles_local IS NOT NULL AND goles_visitante IS NOT NULL
        """)
        partidos_cerrados = cursor.fetchall()

        correcciones = 0
        for partido in partidos_cerrados:
            pid = partido["id"]
            gl, gv = partido["goles_local"], partido["goles_visitante"]

            cursor.execute("""
                SELECT id, pred_local, pred_visitante
                FROM predicciones
                WHERE partido_id = ? AND puntos IS NULL
            """, (pid,))
            preds_sin_puntos = cursor.fetchall()

            for pred in preds_sin_puntos:
                puntos = _calcular_puntos(pred["pred_local"], pred["pred_visitante"], gl, gv)
                cursor.execute("UPDATE predicciones SET puntos = ? WHERE id = ?", (puntos, pred["id"]))
                correcciones += 1

        if correcciones > 0:
            conn.commit()
            print(f"[ranking] ⚠️ Se corrigieron {correcciones} predicciones sin puntaje.")

        # --- RANKING ---
        cursor.execute("""
            SELECT u.nombre,
                COALESCE(SUM(p.puntos), 0) + COALESCE(pe.puntos_especiales, 0) AS total_puntos,
                COUNT(CASE WHEN p.puntos IS NOT NULL THEN 1 END) AS partidos_jugados,
                COUNT(CASE WHEN p.puntos = 3 THEN 1 END) AS exactos,
                COUNT(CASE WHEN p.puntos = 1 THEN 1 END) AS acertados,
                COALESCE(pe.puntos_especiales, 0) AS pts_especiales
            FROM usuarios u
            LEFT JOIN predicciones p ON u.id = p.usuario_id
            LEFT JOIN predicciones_especiales pe ON u.id = pe.usuario_id
            GROUP BY u.id
            ORDER BY total_puntos DESC, exactos DESC
        """)
        filas = cursor.fetchall()
        conn.close()

        if not filas:
            await interaction.followup.send("Todavía no hay nadie registrado en el prode.")
            return

        embed = discord.Embed(title="🏆 Ranking del Prode Mundial", color=discord.Color.gold())

        if correcciones > 0:
            embed.set_footer(text=f"⚠️ Se corrigieron {correcciones} puntaje(s) faltante(s) antes de mostrar el ranking.")

        medallas = {1: "🥇", 2: "🥈", 3: "🥉"}

        lineas = []
        for i, fila in enumerate(filas, start=1):
            pos = medallas.get(i, f"#{i}")
            extra = f" +{fila['pts_especiales']} 🏆" if fila['pts_especiales'] else ""
            lineas.append(
                f"{pos} **{fila['nombre']}** — {fila['total_puntos']} pts "
                f"({fila['partidos_jugados']} jugados, {fila['exactos']} exactos, {fila['acertados']} acertados{extra})"
            )

        texto = "\n".join(lineas)
        if len(texto) > 4000:
            texto = texto[:4000] + "\n... (truncado)"

        embed.description = texto
        await interaction.followup.send(embed=embed)


    @app_commands.command(name="mis_predicciones", description="Mostrá todas tus predicciones cargadas")
    async def mis_predicciones(self, interaction: discord.Interaction):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, pa.equipo_local, pa.equipo_visitante, pa.fecha_hora,
                   pa.cerrado, pa.fase,
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

        paginas = _construir_paginas(predicciones)
        view    = PrediccionesView(paginas)
        embed   = view._embed_actual()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="partidos_hoy", description="Mostrá los partidos de hoy con su ID")
    async def partidos_hoy(self, interaction: discord.Interaction):
        embed = construir_embed_partidos_hoy()
        if embed is None:
            await interaction.response.send_message("No hay partidos programados para hoy.")
            return
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="partidos_ayer", description="Mostrá los partidos de ayer con sus resultados")
    async def partidos_ayer(self, interaction: discord.Interaction):
        ahora = datetime.now(TZ_ARG)

        # Jornada de ayer: 06:00 de ayer a 05:59 de hoy
        if ahora.hour < 6:
            inicio_jornada = (ahora - timedelta(days=2)).replace(hour=6, minute=0, second=0, microsecond=0)
        else:
            inicio_jornada = (ahora - timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

        fin_jornada = inicio_jornada + timedelta(hours=24)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM partidos
            WHERE fecha_hora >= ? AND fecha_hora < ?
            ORDER BY fecha_hora
        """, (inicio_jornada.strftime("%Y-%m-%d %H:%M"), fin_jornada.strftime("%Y-%m-%d %H:%M")))
        partidos = cursor.fetchall()
        conn.close()

        if not partidos:
            await interaction.response.send_message("No hubo partidos ayer.")
            return

        embed = discord.Embed(
            title=f"📅 Partidos de ayer — {inicio_jornada.strftime('%d/%m/%Y')}",
            color=discord.Color.greyple()
        )

        lineas = []
        for p in partidos:
            fecha_p = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M")
            hora = fecha_p.strftime("%H:%M")
            sufijo = " (+1)" if fecha_p.date() > inicio_jornada.date() else ""
            local = f"{bandera(p['equipo_local'])} {p['equipo_local']}"
            visitante = f"{bandera(p['equipo_visitante'])} {p['equipo_visitante']}"

            if p["cerrado"]:
                resultado = f"`{p['goles_local']} - {p['goles_visitante']}` ✅"
            else:
                resultado = "_sin resultado_"

            lineas.append(f"`#{p['id']}` — {hora}{sufijo} hs | {local} vs {visitante} — {resultado}")

        embed.description = "\n".join(lineas)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mis_predicciones_hoy", description="Mostrá tus predicciones de los partidos de hoy")
    async def mis_predicciones_hoy(self, interaction: discord.Interaction):
        ahora = datetime.now(TZ_ARG)

        if ahora.hour < 6:
            inicio_jornada = (ahora - timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        else:
            inicio_jornada = ahora.replace(hour=6, minute=0, second=0, microsecond=0)

        fin_jornada = inicio_jornada + timedelta(hours=24)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, pa.equipo_local, pa.equipo_visitante, pa.fecha_hora, pa.cerrado,
                   pa.goles_local AS real_local, pa.goles_visitante AS real_visitante
            FROM predicciones p
            JOIN partidos pa ON p.partido_id = pa.id
            WHERE p.usuario_id = ?
            AND pa.fecha_hora >= ? AND pa.fecha_hora < ?
            ORDER BY pa.fecha_hora
        """, (str(interaction.user.id), inicio_jornada.strftime("%Y-%m-%d %H:%M"), fin_jornada.strftime("%Y-%m-%d %H:%M")))
        predicciones = cursor.fetchall()
        conn.close()

        if not predicciones:
            await interaction.response.send_message("No tenés predicciones cargadas para los partidos de hoy.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 Mis predicciones de hoy — {inicio_jornada.strftime('%d/%m/%Y')}",
            color=discord.Color.green()
        )

        lineas = []
        for p in predicciones:
            fecha_p = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M")
            hora = fecha_p.strftime("%H:%M")
            sufijo = " (+1)" if fecha_p.date() > inicio_jornada.date() else ""
            tu_pred = f"{p['pred_local']}-{p['pred_visitante']}"
            local = f"{bandera(p['equipo_local'])} {p['equipo_local']}"
            visitante = f"{bandera(p['equipo_visitante'])} {p['equipo_visitante']}"

            if p["cerrado"]:
                resultado = f"{p['real_local']}-{p['real_visitante']}"
                pts = p["puntos"] if p["puntos"] is not None else 0
                emoji_pts = "🎯" if pts == 3 else ("✅" if pts == 1 else "❌")
                lineas.append(f"`#{p['partido_id']:>3}` {local} vs {visitante} — {hora}{sufijo} hs | Pred: `{tu_pred}` Real: `{resultado}` {emoji_pts} +{pts}pts")
            else:
                lineas.append(f"`#{p['partido_id']:>3}` {local} vs {visitante} — {hora}{sufijo} hs | Pred: `{tu_pred}` ⏳")

        embed.description = "\n".join(lineas)
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="partidos_manana", description="Mostrá los partidos de mañana")
    async def partidos_manana(self, interaction: discord.Interaction):
        ahora = datetime.now(TZ_ARG)

        # Jornada de mañana: 06:00 de mañana a 05:59 del día siguiente
        if ahora.hour < 6:
            inicio_jornada = ahora.replace(hour=6, minute=0, second=0, microsecond=0)
        else:
            inicio_jornada = (ahora + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

        fin_jornada = inicio_jornada + timedelta(hours=24)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM partidos
            WHERE fecha_hora >= ? AND fecha_hora < ?
            ORDER BY fecha_hora
        """, (inicio_jornada.strftime("%Y-%m-%d %H:%M"), fin_jornada.strftime("%Y-%m-%d %H:%M")))
        partidos = cursor.fetchall()
        conn.close()

        if not partidos:
            await interaction.response.send_message("No hay partidos programados para mañana.")
            return

        embed = discord.Embed(
            title=f"📅 Partidos de mañana — {inicio_jornada.strftime('%d/%m/%Y')}",
            color=discord.Color.green()
        )

        lineas = []
        for p in partidos:
            fecha_p = datetime.strptime(p["fecha_hora"], "%Y-%m-%d %H:%M")
            hora = fecha_p.strftime("%H:%M")
            sufijo = " (+1)" if fecha_p.date() > inicio_jornada.date() else ""
            local = f"{bandera(p['equipo_local'])} {p['equipo_local']}"
            visitante = f"{bandera(p['equipo_visitante'])} {p['equipo_visitante']}"

            lineas.append(f"`#{p['id']}` — {hora}{sufijo} hs | {local} vs {visitante} — _pendiente_")

        embed.description = "\n".join(lineas)
        embed.set_footer(text="Usá /predecir partido_id:<ID> para cargar tu pronóstico")
        await interaction.response.send_message(embed=embed)


def _calcular_puntos(pred_local, pred_visitante, real_local, real_visitante):
    if pred_local == real_local and pred_visitante == real_visitante:
        return 3
    def signo(n): return 1 if n > 0 else (-1 if n < 0 else 0)
    return 1 if signo(pred_local - pred_visitante) == signo(real_local - real_visitante) else 0

async def setup(bot):
    await bot.add_cog(Predicciones(bot))

