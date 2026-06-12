import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import init_db

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    init_db()
    await bot.load_extension("cogs.admin")
    await bot.load_extension("cogs.predicciones")
    await bot.load_extension("cogs.grupos")
    await bot.load_extension("cogs.especiales")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos.")
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")
    print(f"Bot conectado como {bot.user}")


@bot.tree.command(name="ping", description="Verifica que el bot esté funcionando")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! El bot está funcionando.")
    
bot.run(TOKEN)