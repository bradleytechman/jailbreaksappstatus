import discord
from discord import app_commands, ButtonStyle
from discord.ui import Button, View
import aiohttp
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize the bot with intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Create a View with a Website button
class StatusView(View):
    def __init__(self):
        super().__init__(timeout=None)  # No timeout for persistent buttons
        website_button = Button(
            label="Website",
            style=ButtonStyle.link,
            url="https://jailbreaks.app"
        )
        self.add_item(website_button)

# Event: Bot is ready
@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user.name}')
    try:
        # Sync global slash commands
        await tree.sync()
        logger.info("Global slash commands synced successfully")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {str(e)}")

# Slash command: Check jailbreaks.app status
@tree.command(name="status", description="Check the status of jailbreaks.app")
async def status(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://api.jailbreaks.app/status', timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get('status', 'Unknown').lower()  # Case-insensitive status check
                    if status == 'signed':
                        status_message = "✅ Jailbreaks.app is signed right now. This means you **can** install apps"
                    else:
                        status_message = "❌ Jailbreaks.app is not signed right now. This means you **can not** install apps"
                    # Send message with Website button
                    view = StatusView()
                    await interaction.response.send_message(status_message, view=view)
                else:
                    await interaction.response.send_message(
                        f"Failed to fetch status. HTTP Status: {response.status}. Please ping @bradleytechman for assistance."
                    )
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            await interaction.response.send_message(
                f"Failed to connect to jailbreaks.app API. Please ping @bradleytechman for assistance."
            )
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}. Please ping @bradleytechman for assistance."
            )

# Run the bot with token from environment variable
try:
    client.run(os.getenv('DISCORD_BOT_TOKEN'))
except discord.errors.LoginFailure:
    logger.error("Invalid bot token provided. Please check your DISCORD_BOT_TOKEN in the .env file.")
except Exception as e:
    logger.error(f"Failed to start bot: {str(e)}")