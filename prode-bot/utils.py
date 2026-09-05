"""Presentación de nombres de equipos.

Los datos salen de la tabla `equipos`, que se llena sola al importar el fixture
desde ESPN. Se cachean en memoria porque se consultan en casi todos los embeds.
"""
from database import get_connection

_cache = None


def _equipos():
    global _cache
    if _cache is None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM equipos")
        _cache = {fila["nombre"]: dict(fila) for fila in cursor.fetchall()}
        conn.close()
    return _cache


def invalidar_cache():
    """Llamar después de escribir en la tabla `equipos`."""
    global _cache
    _cache = None


def nombre_corto(equipo: str) -> str:
    """Nombre acortado para listados largos: 'Borussia Dortmund' → 'Dortmund'."""
    datos = _equipos().get(equipo)
    return (datos or {}).get("nombre_corto") or equipo


def abreviatura(equipo: str) -> str:
    """Sigla de 3 letras del equipo, o el nombre si todavía no se importó."""
    datos = _equipos().get(equipo)
    return (datos or {}).get("abreviatura") or equipo


def espn_id(equipo: str):
    datos = _equipos().get(equipo)
    return (datos or {}).get("espn_id")


def guardar_equipo(cursor, datos: dict):
    """Inserta o actualiza un equipo. No hace commit: lo hace quien llama."""
    cursor.execute("""
        INSERT INTO equipos (nombre, espn_id, nombre_corto, abreviatura, logo_url)
        VALUES (:nombre, :espn_id, :nombre_corto, :abreviatura, :logo_url)
        ON CONFLICT(nombre) DO UPDATE SET
            espn_id      = excluded.espn_id,
            nombre_corto = excluded.nombre_corto,
            abreviatura  = excluded.abreviatura,
            logo_url     = excluded.logo_url
    """, datos)
