import os
import sqlite3
import time
from datetime import date, time as dtime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

DB_PATH = "data/prode.db"
BACKUP_DIR = "data/backups"
KEEP_DAYS = 7
ARG_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


class Backup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backup_diario.start()

    def cog_unload(self):
        self.backup_diario.cancel()

    @tasks.loop(time=dtime(hour=6, minute=0, tzinfo=ARG_TZ))
    async def backup_diario(self):
        self.hacer_backup()

    def hacer_backup(self):
        if not os.path.isfile(DB_PATH):
            print(f"[backup] ERROR: no se encontro {DB_PATH}")
            return

        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_path = os.path.join(BACKUP_DIR, f"prodeBU_{date.today().isoformat()}.db")

        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(backup_path)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()

        cutoff = time.time() - KEEP_DAYS * 86400
        for name in os.listdir(BACKUP_DIR):
            if name.startswith("prodeBU_") and name.endswith(".db"):
                path = os.path.join(BACKUP_DIR, name)
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)

        print(f"[backup] backup creado: {backup_path}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))
