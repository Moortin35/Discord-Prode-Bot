# 🏆 Discord Prode Bot — UEFA Champions League

Bot de Discord para gestionar un prode de la Champions League. Los jugadores predicen los resultados de las **8 fechas de la fase liga**, acumulan puntos y compiten en un ranking global.

---

## 📋 Tabla de contenidos

- [🏆 Discord Prode Bot — UEFA Champions League](#-discord-prode-bot--uefa-champions-league)
  - [📋 Tabla de contenidos](#-tabla-de-contenidos)
  - [🧩 El formato](#-el-formato)
  - [✨ Características](#-características)
  - [🤖 Comandos](#-comandos)
    - [⚽ Predicciones](#-predicciones)
    - [📅 Partidos](#-partidos)
    - [📊 Estadísticas](#-estadísticas)
    - [🔧 Administración *(solo admins)*](#-administración-solo-admins)
  - [🎯 Sistema de puntos](#-sistema-de-puntos)
  - [⚙️ Instalación](#️-instalación)
    - [Prerrequisitos](#prerrequisitos)
    - [Pasos](#pasos)
  - [🔧 Configuración](#-configuración)
    - [Importar el fixture](#importar-el-fixture)
    - [Canal de recordatorios](#canal-de-recordatorios)
    - [Cierre de la predicción de campeón](#cierre-de-la-predicción-de-campeón)
    - [Zona horaria y torneo](#zona-horaria-y-torneo)
  - [📁 Estructura del proyecto](#-estructura-del-proyecto)
  - [🛠️ Tecnologías](#️-tecnologías)
  - [📝 Licencia](#-licencia)

---

## 🧩 El formato

Desde 2024-25 la Champions no tiene grupos: **36 equipos en una sola tabla**, cada uno juega **8 partidos** contra rivales distintos. El bot está armado sobre ese formato:

| Posición | Destino |
|---|---|
| 1-8 | Clasifican directo a Octavos |
| 9-24 | Juegan el Playoff de Octavos |
| 25-36 | Eliminados |

---

## ✨ Características

- **Predicciones por partido** — los jugadores predicen el marcador exacto antes de que empiece cada partido
- **Fixture automático** — `/importar_fixture` trae las 8 fechas completas desde la API de ESPN, con horarios ya convertidos a hora argentina
- **Resultados automáticos** — el bot consulta ESPN cada 3 minutos, actualiza el marcador en vivo y cierra los partidos al finalizar
- **Tabla de la fase liga** — imagen generada con las 36 posiciones, escudos y las tres zonas de clasificación
- **Ranking en tiempo real** — tabla de posiciones con puntaje, plenos y aciertos de todos los participantes
- **Predicción de campeón** — predicción especial del ganador del torneo, con fecha de cierre configurable
- **Recordatorios automáticos** — aviso a las 2h y 1h antes de cada partido
- **Anuncio diario** — publicación automática a las 12:00 con los partidos del día
- **Notificaciones de resultados** — embed automático al cerrar cada partido mostrando quién acertó y con qué predicción
- **Backup automático** — copia de seguridad diaria de la base de datos a las 06:00, con retención de 7 días

---

## 🤖 Comandos

### ⚽ Predicciones

| Comando | Descripción |
|---|---|
| `/predecir partido_id:<ID> goles_local:<N> goles_visitante:<N>` | Cargá tu predicción para un partido |
| `/mis_predicciones` | Mostrá todas tus predicciones, paginadas por fecha |
| `/mis_predicciones_hoy` | Mostrá solo tus predicciones de los partidos de hoy |
| `/predecir_campeon campeon:<Equipo>` | Elegí el equipo que creés será campeón |
| `/mi_campeon` | Mostrá tu predicción de campeón actual |

### 📅 Partidos

| Comando | Descripción |
|---|---|
| `/partidos_hoy` | Listado de partidos del día con horarios y resultados |
| `/partidos_ayer` | Resultados de los partidos de ayer |
| `/partidos_manana` | Fixture de los partidos de mañana |
| `/listar_partidos` | Fixture completo del torneo |

### 📊 Estadísticas

| Comando | Descripción |
|---|---|
| `/tabla` | Tabla de posiciones de la fase liga (36 equipos) |
| `/fecha <1-8>` | Partidos de una fecha de la fase liga |
| `/ranking` | Tabla de posiciones global del prode |
| `/ayuda` | Muestra todos los comandos disponibles |

### 🔧 Administración *(solo admins)*

| Comando | Descripción |
|---|---|
| `/importar_fixture` | Importa las 8 fechas de la fase liga desde ESPN |
| `/cargar_partido` | Carga un partido manualmente (útil para las eliminatorias) |
| `/cargar_resultado` | Carga el resultado de un partido manualmente |
| `/cargar_resultados_masivo` | Carga resultados desde `data/resultados.csv` |
| `/reabrir_partido partido_id:<ID>` | Deshace el resultado de un partido y reabre predicciones |
| `/cargar_campeon campeon:<Equipo>` | Registra el campeón real y calcula puntos |
| `/configurar_canal_recordatorios` | Configura el canal donde el bot enviará avisos y resultados |
| `/configurar_cierre_campeon fecha_hora:<...>` | Define hasta cuándo se puede predecir el campeón |

---

## 🎯 Sistema de puntos

| Acierto | Puntos |
|---|---|
| 🎯 **Pleno** — marcador exacto | +3 pts |
| ✅ **Acierto** — resultado correcto (ganador o empate) | +1 pt |
| ❌ **Fallo** — resultado incorrecto | 0 pts |
| 🏆 **Campeón** — predicción de campeón correcta | +10 pts |

> Las predicciones se cierran automáticamente cuando comienza el partido. No se pueden modificar una vez iniciado.

Los valores se ajustan en `config.py` (`PUNTOS_PLENO`, `PUNTOS_ACIERTO`, `PUNTOS_CAMPEON`).

---

## ⚙️ Instalación

### Prerrequisitos

- Python 3.10+
- Una aplicación de Discord con un bot token ([Discord Developer Portal](https://discord.com/developers/applications))

### Pasos

1. **Clonar el repositorio**
```bash
   git clone https://github.com/tu-usuario/Discord-Prode-Bot.git
   cd Discord-Prode-Bot/prode-bot
```

2. **Instalar dependencias**
```bash
   pip install -r requirements.txt
```

3. **Configurar variables de entorno** — crear un archivo `.env` en la raíz:
```env
   DISCORD_TOKEN=tu_token_aqui
```

4. **Crear la carpeta de datos**
```bash
   mkdir -p data/backups
```

5. **Iniciar el bot**
```bash
   python bot.py
```

---

## 🔧 Configuración

### Importar el fixture

Con el bot corriendo, un admin ejecuta:

```
/importar_fixture
```

El bot consulta el calendario de ESPN, detecta la fase liga de la temporada actual y carga los 144 partidos repartidos en 8 fechas, junto con los 36 equipos y sus escudos. El comando es **idempotente**: volver a correrlo no duplica partidos, solo actualiza fechas y horarios (útil cuando la UEFA reprograma).

Las eliminatorias se cargan a mano con `/cargar_partido` a medida que se definen los cruces, usando `fase` = `Playoff`, `Octavos`, `Cuartos`, `Semis` o `Final`.

### Canal de recordatorios

Ejecutá en el canal deseado:

```
/configurar_canal_recordatorios
```

Ese canal recibirá:
- 📢 Anuncio diario de partidos a las **12:00 ARG**
- ⏰ Recordatorios **2h y 1h** antes de cada partido
- 📊 Notificaciones automáticas de resultados al terminar cada partido

### Cierre de la predicción de campeón

```
/configurar_cierre_campeon fecha_hora:2026-10-13 13:00
```

Si no se configura, la predicción de campeón queda abierta indefinidamente.

### Zona horaria y torneo

El bot opera en horario de Argentina y convierte solo los horarios que vienen de ESPN en UTC. Para adaptarlo a otra región o a otro torneo de la UEFA, editá `config.py`:

```python
TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
ESPN_LIGA = "uefa.champions"   # ej: "uefa.europa" para la Europa League
```

---

## 📁 Estructura del proyecto

```
prode-bot/
├── bot.py                  # Entry point, carga de extensiones
├── config.py               # Zona horaria, torneo, formato y puntajes
├── database.py             # Inicialización, migraciones y conexión SQLite
├── espn.py                 # Cliente de la API de ESPN (fixture y resultados)
├── utils.py                # Nombres y escudos de los equipos
├── image_gen.py            # Generación de la imagen de la tabla
├── cogs/
│   ├── admin.py            # Comandos de administración e importación del fixture
│   ├── predicciones.py     # Predicciones, ranking y listado de partidos
│   ├── tabla.py            # Tabla de la fase liga y partidos por fecha
│   ├── especiales.py       # Predicción de campeón
│   ├── recordatorios.py    # Recordatorios automáticos y aviso diario
│   ├── resultados_auto.py  # Polling automático a la API de ESPN
│   ├── ayuda.py            # Comando /ayuda
│   └── backup.py           # Backup diario de la base de datos
├── data/
│   ├── prode.db            # Base de datos SQLite (generada automáticamente)
│   ├── backups/            # Copias de seguridad automáticas
│   └── resultados.csv      # Resultados para carga masiva (opcional)
└── assets/
    ├── fonts/              # Fuentes para generación de imágenes
    └── logos/              # Caché de escudos descargados
```

---

## 🛠️ Tecnologías

- **[discord.py](https://discordpy.readthedocs.io/)** — framework principal del bot
- **SQLite** — base de datos local para partidos, predicciones, equipos y usuarios
- **[ESPN API](https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard)** — fixture, escudos y resultados en tiempo real
- **[Pillow](https://pillow.readthedocs.io/)** — generación de la imagen de la tabla
- **[aiohttp](https://docs.aiohttp.org/)** — peticiones HTTP asíncronas

---

## 📝 Licencia

Este proyecto es de uso personal/comunitario. ¡Libre de adaptar para tu propio prode! 🎉
