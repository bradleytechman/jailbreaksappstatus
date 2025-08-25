import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

class JBAppBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.status")
        await self.load_extension("cogs.configure")
        await self.tree.sync()

intents = discord.Intents.default()
bot = JBAppBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"logged in as {bot.user}")

bot.run(DISCORD_TOKEN)