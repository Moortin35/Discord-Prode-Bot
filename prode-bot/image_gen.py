from PIL import Image, ImageDraw, ImageFont
from flags_map import codigo_pais

import os
import requests

FONT_DIR = "assets/fonts"
FLAGS_DIR = "assets/flags"
os.makedirs(FLAGS_DIR, exist_ok=True)

ANCHO = 640
ALTO_HEADER = 50
ALTO_FILA = 40
PADDING = 15

COLOR_FONDO = (30, 33, 36)
COLOR_HEADER = (50, 54, 58)
COLOR_FILA_PAR = (40, 43, 47)
COLOR_FILA_IMPAR = (35, 38, 42)
COLOR_TEXTO = (230, 230, 230)
COLOR_TEXTO_HEADER = (255, 255, 255)
COLOR_CLASIFICA = (87, 242, 135)  # verde para top 2

COLUMNAS = ["Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "PTS"]
ANCHOS_COL = [220, 45, 45, 45, 45, 45, 45, 45, 50]


def _font(size, bold=False):
    try:
        nombre = "GoogleSans-Bold.ttf" if bold else "GoogleSans-Regular.ttf"
        path = os.path.join(FONT_DIR, nombre)
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()
    
def obtener_bandera(codigo, ancho=40):
    """Descarga (si no existe) y devuelve la imagen PIL de la bandera."""
    if not codigo:
        return None

    path = os.path.join(FLAGS_DIR, f"{codigo}_{ancho}.png")

    if not os.path.exists(path):
        url = f"https://flagcdn.com/w{ancho}/{codigo}.png"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                with open(path, "wb") as f:
                    f.write(resp.content)
            else:
                return None
        except requests.RequestException:
            return None

    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def generar_tabla_grupo(letra, filas):
    """
    filas: lista de tuplas (equipo, pj, pg, pe, pp, gf, gc, dg, pts)
    """
    alto_total = ALTO_HEADER + ALTO_FILA * len(filas) + PADDING * 2 + 80

    img = Image.new("RGB", (ANCHO, alto_total), COLOR_FONDO)
    draw = ImageDraw.Draw(img)

    font_titulo = _font(24, bold=True)
    font_header = _font(16, bold=True)
    font_celda = _font(15)
    font_leyenda = _font(13)

    # Título
    draw.text((PADDING, PADDING), f"Grupo {letra}", font=font_titulo, fill=COLOR_TEXTO_HEADER)

    y = PADDING + 40

    # Header
    draw.rectangle([PADDING, y, ANCHO - PADDING, y + ALTO_HEADER], fill=COLOR_HEADER)
    x = PADDING
    for col, w in zip(COLUMNAS, ANCHOS_COL):
        draw.text((x + w / 2, y + ALTO_HEADER / 2), col, font=font_header, fill=COLOR_TEXTO_HEADER, anchor="mm")
        x += w

    y += ALTO_HEADER

    # Filas
    for i, fila in enumerate(filas):
        color_fondo_fila = COLOR_FILA_PAR if i % 2 == 0 else COLOR_FILA_IMPAR
        draw.rectangle([PADDING, y, ANCHO - PADDING, y + ALTO_FILA], fill=color_fondo_fila)

        equipo = fila[0]
        valores = fila[1:]
        color_texto = COLOR_CLASIFICA if i < 2 else COLOR_TEXTO

        x = PADDING
        # Bandera
        codigo = codigo_pais(equipo)
        bandera_img = obtener_bandera(codigo, ancho=40)

        ANCHO_BANDERA = 28  # ancho fijo para todas

        if bandera_img:
            ratio = bandera_img.height / bandera_img.width
            alto_bandera = int(ANCHO_BANDERA * ratio)
            bandera_resized = bandera_img.resize((ANCHO_BANDERA, alto_bandera))
            offset_y = int(y + (ALTO_FILA - alto_bandera) / 2)
            img.paste(bandera_resized, (x + 10, offset_y), bandera_resized)
            texto_x = x + 10 + ANCHO_BANDERA + 8
        else:
            texto_x = x + 10

        # Nombre del equipo
        draw.text((texto_x, y + ALTO_FILA / 2), equipo, font=font_celda, fill=color_texto, anchor="lm")
        x += ANCHOS_COL[0]

        # Resto de columnas (PJ, PG, PE, PP, GF, GC, DG, PTS)
        for idx, (valor, w) in enumerate(zip(valores, ANCHOS_COL[1:]), start=1):
            col_nombre = COLUMNAS[idx]
            if col_nombre == "DG":
                texto = f"{valor:+d}"
            else:
                texto = str(valor)
            draw.text((x + w / 2, y + ALTO_FILA / 2), texto, font=font_celda, fill=color_texto, anchor="mm")
            x += w

        y += ALTO_FILA

    # Leyenda
    y += 15
    draw.ellipse([PADDING, y, PADDING + 14, y + 14], fill=COLOR_CLASIFICA)
    draw.text((PADDING + 22, y + 7), "Clasifica a Octavos", font=font_leyenda, fill=COLOR_TEXTO, anchor="lm")

    output_path = f"data/grupo_{letra}.png"
    img.save(output_path)
    return output_path