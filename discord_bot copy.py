import discord
from discord import app_commands, ButtonStyle
from discord.ui import Button, View
import aiohttp
import os
from dotenv import load_dotenv
import logging
from discord.ext import tasks

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
STATUS_NOTE = os.getenv('STATUS_NOTE', '')
STATUS_CHANNEL_ID = int(os.getenv('STATUS_CHANNEL_ID', 0))
PING_ROLE_ID = os.getenv('PING_ROLE_ID')
if not DISCORD_BOT_TOKEN:
    logger.error("DISCORD_BOT_TOKEN not found in .env file")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

last_signed = None

class StatusView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(
            label="Website",
            style=ButtonStyle.link,
            url="https://jailbreaks.app"
        ))

@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user.name}')
    try:
        await tree.sync()
        logger.info("Global slash commands synced")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    check_jailbreak_status.start()

async def send_error_response(interaction: discord.Interaction, message: str):
    error_msg = f"{message}. :( If this continues to happen, please make an issue at https://github.com/bradleytechman/jailbreaksappstatus/issues"
    try:
        await interaction.response.send_message(error_msg, ephemeral=True)
    except discord.errors.InteractionResponded:
        await interaction.followup.send(error_msg, ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@tree.command(name="status", description="Check jailbreaks.app status")
async def status(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://api.jailbreaks.app/status', timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get('status', 'Unknown').lower()
                    message = (
                        "✅ Jailbreaks.app is signed right now. This means you **can** install apps"
                        if status == 'signed'
                        else "❌ Jailbreaks.app is not signed right now. This means you **can not** install apps"
                    )
                    if STATUS_NOTE:
                        message += f"\n\nNOTE: {STATUS_NOTE}"
                    await interaction.response.send_message(message, view=StatusView())
                else:
                    await send_error_response(interaction, f"Failed to fetch status (HTTP {response.status})")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            await send_error_response(interaction, "Failed to connect to jailbreaks.app API")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await send_error_response(interaction, f"Unexpected error: {e}")

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@tree.command(name="certinfo", description="Get current certificate information")
async def certinfo(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://api.jailbreaks.app/info', timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    cert_name = data.get('name', 'Unknown')
                    cert_status = data.get('status', 'Unknown')
                    cert_expires = data.get('expirationDate', 'Unknown')
                    icon = "✅" if cert_status.lower() == "signed" else "❌"
                    message = (
                        f"📜 **Certificate**: {cert_name}\n"
                        f"{icon} **Status**: {cert_status}\n"
                        f"⏰ **Expires**: {cert_expires}\n"
                        f"-# Note: Expiry date does not correlate to when it is revoked; it can be revoked by apple at **any** time."
                    )
                    await interaction.response.send_message(message)
                else:
                    await send_error_response(interaction, f"Failed to fetch certificate info (HTTP {response.status})")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            await send_error_response(interaction, "Failed to connect to jailbreaks.app API")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await send_error_response(interaction, f"Unexpected error: {e}")

@tasks.loop(seconds=60)
async def check_jailbreak_status():
    global last_signed
    channel = client.get_channel(STATUS_CHANNEL_ID)
    if not channel:
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.jailbreaks.app/status', timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get('status', 'Unknown').lower()
                    signed = status == 'signed'
                    if signed != last_signed:
                        last_signed = signed
                        message_text = (
                            "✅ Jailbreaks.app is signed right now. This means you **can** install apps"
                            if signed else
                            "❌ Jailbreaks.app is not signed right now. This means you **can not** install apps"
                        )
                        if STATUS_NOTE:
                            message_text += f"\n\nNOTE: {STATUS_NOTE}"
                        if signed and PING_ROLE_ID:
                            message_text = f"<@&{PING_ROLE_ID}>\n" + message_text
                        embed = discord.Embed(
                            description=message_text,
                            color=discord.Color.green() if signed else discord.Color.red()
                        )
                        await channel.send(embed=embed, view=StatusView())
                else:
                    logger.error(f"Failed to fetch status (HTTP {response.status})")
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error in background task: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in background task: {e}")

def run_bot():
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        logger.error("Invalid bot token. Check DISCORD_BOT_TOKEN in .env file")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    run_bot()
