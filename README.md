# 🏆 Discord Prode Bot — Mundial 2026

Bot de Discord para gestionar un prode del Mundial FIFA 2026. Los jugadores realizan predicciones de resultados, acumulan puntos y compiten en un ranking global.

---

## 📋 Tabla de contenidos

- [🏆 Discord Prode Bot — Mundial 2026](#-discord-prode-bot--mundial-2026)
  - [📋 Tabla de contenidos](#-tabla-de-contenidos)
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
    - [Canal de recordatorios](#canal-de-recordatorios)
    - [Cargar el fixture](#cargar-el-fixture)
    - [Zona horaria](#zona-horaria)
  - [📁 Estructura del proyecto](#-estructura-del-proyecto)
  - [🛠️ Tecnologías](#️-tecnologías)
  - [📝 Licencia](#-licencia)

---

## ✨ Características

- **Predicciones por partido** — los jugadores predicen el marcador exacto antes de que empiece cada partido
- **Resultados automáticos** — el bot consulta la API de ESPN cada 3 minutos y cierra partidos automáticamente al finalizar
- **Ranking en tiempo real** — tabla de posiciones con puntaje, plenos y aciertos de todos los participantes
- **Tablas de grupos** — posiciones actualizadas de cada grupo con imágenes generadas automáticamente
- **Predicción de campeón** — predicción especial de la selección ganadora del torneo (cierra antes de la Fecha 2)
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
| `/mis_predicciones` | Mostrá todas tus predicciones con resultados y puntos |
| `/mis_predicciones_hoy` | Mostrá solo tus predicciones de los partidos de hoy |
| `/predecir_campeon campeon:<Selección>` | Elegí la selección que creés será campeona |
| `/mi_campeon` | Mostrá tu predicción de campeón actual |

### 📅 Partidos

| Comando | Descripción |
|---|---|
| `/partidos_hoy` | Listado de partidos del día con horarios y resultados |
| `/partidos_ayer` | Resultados de los partidos de ayer |
| `/partidos_manana` | Fixture de los partidos de mañana |
| `/listar_partidos` | Fixture completo del mundial |

### 📊 Estadísticas

| Comando | Descripción |
|---|---|
| `/grupo <letra>` | Tabla de posiciones de un grupo (ej: `/grupo A`) |
| `/ranking` | Tabla de posiciones global del prode |
| `/ayuda` | Muestra todos los comandos disponibles |

### 🔧 Administración *(solo admins)*

| Comando | Descripción |
|---|---|
| `/cargar_partido` | Carga un nuevo partido manualmente |
| `/cargar_fixture` | Carga el fixture completo desde `data/fixture.csv` |
| `/cargar_resultado` | Carga el resultado de un partido manualmente |
| `/cargar_resultados_masivo` | Carga resultados desde `data/resultados.csv` |
| `/reabrir_partido partido_id:<ID>` | Deshace el resultado de un partido y reabre predicciones |
| `/cargar_campeon campeon:<Selección>` | Registra la selección campeona real y calcula puntos |
| `/configurar_canal_recordatorios` | Configura el canal donde el bot enviará avisos y resultados |

---

## 🎯 Sistema de puntos

| Acierto | Puntos |
|---|---|
| 🎯 **Pleno** — marcador exacto | +3 pts |
| ✅ **Acierto** — resultado correcto (ganador o empate) | +1 pt |
| ❌ **Fallo** — resultado incorrecto | 0 pts |
| 🏆 **Campeón** — predicción de campeón correcta | +10 pts |

> Las predicciones se cierran automáticamente cuando comienza el partido. No se pueden modificar una vez iniciado.

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

### Canal de recordatorios

Una vez corriendo el bot, ejecutá en el canal deseado:

```
/configurar_canal_recordatorios
```

Ese canal recibirá:
- 📢 Anuncio diario de partidos a las **12:00 ARG**
- ⏰ Recordatorios **2h y 1h** antes de cada partido
- 📊 Notificaciones automáticas de resultados al terminar cada partido

### Cargar el fixture

Usá `/cargar_fixture` con un archivo `data/fixture.csv` con este formato:

```csv
equipo_local,equipo_visitante,fecha_hora,fase,grupo
Argentina,Canada,2026-06-11 21:00,Grupos,A
Brazil,Mexico,2026-06-11 18:00,Grupos,B
France,Belgium,2026-06-28 18:00,Octavos,
```

El campo `grupo` se deja vacío para fases eliminatorias.

### Zona horaria

El bot opera en horario de Argentina (`America/Argentina/Buenos_Aires`). Para adaptarlo a otra región, editá `config.py`:

```python
TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
```

---

## 📁 Estructura del proyecto

```
prode-bot/
├── bot.py                  # Entry point, carga de extensiones
├── config.py               # Zona horaria global
├── database.py             # Inicialización y conexión SQLite
├── utils.py                # Emojis de banderas por selección
├── flags_map.py            # Códigos de país y mapeo ESPN → DB
├── image_gen.py            # Generación de imágenes para tablas de grupos
├── cogs/
│   ├── admin.py            # Comandos de administración
│   ├── predicciones.py     # Predicciones, ranking y listado de partidos
│   ├── grupos.py           # Tabla de posiciones por grupo
│   ├── especiales.py       # Predicción de campeón
│   ├── recordatorios.py    # Recordatorios automáticos y aviso diario
│   ├── resultados_auto.py  # Polling automático a la API de ESPN
│   ├── ayuda.py            # Comando /ayuda
│   └── backup.py           # Backup diario de la base de datos
├── data/
│   ├── prode.db            # Base de datos SQLite (generada automáticamente)
│   ├── backups/            # Copias de seguridad automáticas
│   ├── fixture.csv         # Fixture para carga masiva (opcional)
│   └── resultados.csv      # Resultados para carga masiva (opcional)
└── assets/
    ├── fonts/              # Fuentes para generación de imágenes
    └── flags/              # Caché de banderas descargadas
```

---

## 🛠️ Tecnologías

- **[discord.py](https://discordpy.readthedocs.io/)** — framework principal del bot
- **SQLite** — base de datos local para partidos, predicciones y usuarios
- **[ESPN API](https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard)** — fuente de resultados en tiempo real
- **[Pillow](https://pillow.readthedocs.io/)** — generación de imágenes para tablas de grupos
- **[aiohttp](https://docs.aiohttp.org/)** — peticiones HTTP asíncronas
- **[flagcdn.com](https://flagcdn.com/)** — imágenes de banderas por país

---

## 📝 Licencia

Este proyecto es de uso personal/comunitario. ¡Libre de adaptar para tu propio prode! 🎉