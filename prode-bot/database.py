import sqlite3

DB_PATH = "data/prode.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY,
            equipo_local TEXT NOT NULL,
            equipo_visitante TEXT NOT NULL,
            fecha_hora TEXT NOT NULL,
            fase TEXT,
            jornada INTEGER,
            espn_id TEXT UNIQUE,
            goles_local INTEGER DEFAULT NULL,
            goles_visitante INTEGER DEFAULT NULL,
            cerrado INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predicciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id TEXT NOT NULL,
            partido_id INTEGER NOT NULL,
            pred_local INTEGER NOT NULL,
            pred_visitante INTEGER NOT NULL,
            puntos INTEGER DEFAULT NULL,
            FOREIGN KEY (partido_id) REFERENCES partidos(id),
            UNIQUE(usuario_id, partido_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predicciones_especiales (
            usuario_id TEXT PRIMARY KEY,
            campeon TEXT,
            puntos_especiales INTEGER DEFAULT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resultados_especiales (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            campeon TEXT,
            cerrado INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recordatorios_enviados (
            partido_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            PRIMARY KEY (partido_id, tipo)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY,
            espn_id TEXT UNIQUE,
            nombre_corto TEXT,
            abreviatura TEXT,
            logo_url TEXT,
            pais TEXT
        )
    """)

    _migrar(cursor)

    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")


def _migrar(cursor):
    """Agrega columnas nuevas a bases creadas con versiones anteriores del bot."""
    cursor.execute("PRAGMA table_info(partidos)")
    columnas = {fila["name"] for fila in cursor.fetchall()}

    if "jornada" not in columnas:
        cursor.execute("ALTER TABLE partidos ADD COLUMN jornada INTEGER")
        print("[migracion] Columna 'jornada' agregada a partidos.")

    if "espn_id" not in columnas:
        # SQLite no permite agregar una columna UNIQUE con ALTER TABLE:
        # la creamos suelta y forzamos la unicidad con un índice.
        cursor.execute("ALTER TABLE partidos ADD COLUMN espn_id TEXT")
        print("[migracion] Columna 'espn_id' agregada a partidos.")

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_partidos_espn_id ON partidos(espn_id)"
    )

    cursor.execute("PRAGMA table_info(equipos)")
    columnas_equipos = {fila["name"] for fila in cursor.fetchall()}

    if "pais" not in columnas_equipos:
        cursor.execute("ALTER TABLE equipos ADD COLUMN pais TEXT")
        print("[migracion] Columna 'pais' agregada a equipos.")