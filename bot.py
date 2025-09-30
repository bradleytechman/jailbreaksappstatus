import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import aiohttp

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Optional webhook URL from .env

class JBAppBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.status")
        await self.load_extension("cogs.configure")
        await self.tree.sync()

    async def on_error(self, event, *args, **kwargs):
        error_info = "unknown action"
        context = args[0] if args else None
        if isinstance(context, discord.Interaction):
            if context.command:
                error_info = f"command /{context.command.name}"
            elif context.data.get("custom_id"):
                error_info = f"interaction with {context.data.get('custom_id')}"
        error_message = f"Error in {error_info}: {''.join(traceback.format_exception_only(*sys.exc_info()[:2]))}"

        # Send to webhook if configured
        if WEBHOOK_URL:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                await webhook.send(error_message)

intents = discord.Intents.default()
intents.message_content = True
bot = JBAppBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"logged in as {bot.user}")

bot.run(DISCORD_TOKEN)
