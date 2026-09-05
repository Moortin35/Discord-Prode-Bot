from PIL import Image, ImageDraw, ImageFont

import os
import requests

from config import CLASIFICAN_DIRECTO, CLASIFICAN_PLAYOFF

FONT_DIR = "assets/fonts"
LOGOS_DIR = "assets/logos"
os.makedirs(LOGOS_DIR, exist_ok=True)

ANCHO = 720
ALTO_HEADER = 46
ALTO_FILA = 38
PADDING = 15

COLOR_FONDO = (30, 33, 36)
COLOR_HEADER = (50, 54, 58)
COLOR_FILA_PAR = (40, 43, 47)
COLOR_FILA_IMPAR = (35, 38, 42)
COLOR_TEXTO = (230, 230, 230)
COLOR_TEXTO_HEADER = (255, 255, 255)
COLOR_TENUE = (150, 155, 160)

COLOR_DIRECTO = (87, 242, 135)   # verde  — 1-8   clasifican a octavos
COLOR_PLAYOFF = (254, 231, 92)   # amarillo — 9-24 juegan el playoff
COLOR_ELIMINADO = (237, 66, 69)  # rojo   — 25-36 eliminados

COLUMNAS = ["#", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "PTS"]
ANCHOS_COL = [40, 250, 42, 42, 42, 42, 42, 42, 45, 50]

ANCHO_LOGO = 26


def _font(size, bold=False):
    try:
        nombre = "GoogleSans-Bold.ttf" if bold else "GoogleSans-Regular.ttf"
        path = os.path.join(FONT_DIR, nombre)
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def obtener_logo(espn_id, logo_url=None):
    """Descarga (si no existe) y devuelve el escudo del equipo como imagen PIL."""
    if not espn_id:
        return None

    path = os.path.join(LOGOS_DIR, f"{espn_id}.png")

    if not os.path.exists(path):
        url = logo_url or f"https://a.espncdn.com/i/teamlogos/soccer/500/{espn_id}.png"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return None
            with open(path, "wb") as f:
                f.write(resp.content)
        except requests.RequestException:
            return None

    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def _color_posicion(pos):
    if pos <= CLASIFICAN_DIRECTO:
        return COLOR_DIRECTO
    if pos <= CLASIFICAN_PLAYOFF:
        return COLOR_PLAYOFF
    return COLOR_ELIMINADO


def generar_tabla_liga(filas, subtitulo=None):
    """
    filas: lista de dicts con las claves
           equipo, espn_id, logo_url, pj, pg, pe, pp, gf, gc, dg, pts
           ya ordenada de la posición 1 en adelante.
    """
    alto_leyenda = 90
    alto_total = PADDING * 2 + 50 + ALTO_HEADER + ALTO_FILA * len(filas) + alto_leyenda

    img = Image.new("RGB", (ANCHO, alto_total), COLOR_FONDO)
    draw = ImageDraw.Draw(img)

    font_titulo = _font(24, bold=True)
    font_subtitulo = _font(14)
    font_header = _font(15, bold=True)
    font_celda = _font(15)
    font_leyenda = _font(13)

    draw.text((PADDING, PADDING), "Fase Liga", font=font_titulo, fill=COLOR_TEXTO_HEADER)
    if subtitulo:
        draw.text((PADDING, PADDING + 28), subtitulo, font=font_subtitulo, fill=COLOR_TENUE)

    y = PADDING + 50

    # Header
    draw.rectangle([PADDING, y, ANCHO - PADDING, y + ALTO_HEADER], fill=COLOR_HEADER)
    x = PADDING
    for i, (col, w) in enumerate(zip(COLUMNAS, ANCHOS_COL)):
        # "Equipo" alineado a la izquierda como los nombres; el resto centrado
        if i == 1:
            draw.text((x + 10, y + ALTO_HEADER / 2), col, font=font_header,
                      fill=COLOR_TEXTO_HEADER, anchor="lm")
        else:
            draw.text((x + w / 2, y + ALTO_HEADER / 2), col, font=font_header,
                      fill=COLOR_TEXTO_HEADER, anchor="mm")
        x += w

    y += ALTO_HEADER

    for i, fila in enumerate(filas):
        pos = i + 1
        color_fondo_fila = COLOR_FILA_PAR if i % 2 == 0 else COLOR_FILA_IMPAR
        draw.rectangle([PADDING, y, ANCHO - PADDING, y + ALTO_FILA], fill=color_fondo_fila)

        # Franja de color a la izquierda según la zona de la tabla
        color_zona = _color_posicion(pos)
        draw.rectangle([PADDING, y, PADDING + 4, y + ALTO_FILA], fill=color_zona)

        x = PADDING
        draw.text((x + ANCHOS_COL[0] / 2, y + ALTO_FILA / 2), str(pos),
                  font=font_celda, fill=color_zona, anchor="mm")
        x += ANCHOS_COL[0]

        logo = obtener_logo(fila.get("espn_id"), fila.get("logo_url"))
        if logo:
            ratio = logo.height / logo.width
            alto_logo = int(ANCHO_LOGO * ratio)
            logo_resized = logo.resize((ANCHO_LOGO, alto_logo))
            offset_y = int(y + (ALTO_FILA - alto_logo) / 2)
            img.paste(logo_resized, (x + 8, offset_y), logo_resized)
            texto_x = x + 8 + ANCHO_LOGO + 8
        else:
            texto_x = x + 8

        draw.text((texto_x, y + ALTO_FILA / 2), fila["equipo"],
                  font=font_celda, fill=COLOR_TEXTO, anchor="lm")
        x += ANCHOS_COL[1]

        valores = [fila["pj"], fila["pg"], fila["pe"], fila["pp"],
                   fila["gf"], fila["gc"], fila["dg"], fila["pts"]]
        for idx, (valor, w) in enumerate(zip(valores, ANCHOS_COL[2:]), start=2):
            texto = f"{valor:+d}" if COLUMNAS[idx] == "DG" else str(valor)
            negrita = COLUMNAS[idx] == "PTS"
            draw.text((x + w / 2, y + ALTO_FILA / 2), texto,
                      font=_font(15, bold=True) if negrita else font_celda,
                      fill=COLOR_TEXTO, anchor="mm")
            x += w

        y += ALTO_FILA

    # Leyenda
    y += 14
    leyendas = [
        (COLOR_DIRECTO, f"1-{CLASIFICAN_DIRECTO} · Clasifican directo a Octavos"),
        (COLOR_PLAYOFF, f"{CLASIFICAN_DIRECTO + 1}-{CLASIFICAN_PLAYOFF} · Juegan el Playoff de Octavos"),
        (COLOR_ELIMINADO, f"{CLASIFICAN_PLAYOFF + 1}-{len(filas)} · Eliminados"),
    ]
    for color, texto in leyendas:
        draw.ellipse([PADDING, y, PADDING + 12, y + 12], fill=color)
        draw.text((PADDING + 20, y + 6), texto, font=font_leyenda, fill=COLOR_TEXTO, anchor="lm")
        y += 22

    output_path = "data/tabla_liga.png"
    img.save(output_path)
    return output_path
