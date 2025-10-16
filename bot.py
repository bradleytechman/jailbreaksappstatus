import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import aiohttp
import asyncio

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Optional webhook URL from .env

# --- Webhook Forwarder Class ---
# This class intercepts stdout/stderr and forwards messages to the webhook.
class WebhookStream:
    def __init__(self, original_stream, webhook_url, loop):
        self.original_stream = original_stream
        self.webhook_url = webhook_url
        self.loop = loop
        self.session = aiohttp.ClientSession()
        self.webhook = discord.Webhook.from_url(self.webhook_url, session=self.session)

    def write(self, message):
        # First, write the message to the actual console (stdout/stderr)
        self.original_stream.write(message)
        self.original_stream.flush()

        # If the message is just newlines or whitespace, don't send it.
        if not message.strip():
            return

        # Use run_coroutine_threadsafe to call an async function from this sync context
        asyncio.run_coroutine_threadsafe(self.send_to_webhook(message), self.loop)

    async def send_to_webhook(self, message):
        try:
            # Discord has a 2000 character limit per message.
            if len(message) > 1990: # Leave room for code block formatting
                message = message[:1990]
            
            # Send the message formatted as a code block
            await self.webhook.send(f"```\n{message.strip()}\n```")
        except Exception as e:
            # If the webhook fails, write the failure message to the original console
            # to avoid an infinite loop of logging failures.
            error_msg = f"[WebhookStream Error] Failed to send log: {e}\n"
            self.original_stream.write(error_msg)
            self.original_stream.flush()

    def flush(self):
        # This is needed to properly mimic a stream object like sys.stdout
        self.original_stream.flush()

    async def close(self):
        """A method to clean up the aiohttp session."""
        await self.session.close()


class JBAppBot(commands.Bot):
    async def setup_hook(self):
        # If a webhook URL is provided, redirect stdout and stderr
        if WEBHOOK_URL:
            # Keep original streams to restore them on close
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            
            # Create our custom stream forwarders
            self.webhook_stdout = WebhookStream(sys.stdout, WEBHOOK_URL, self.loop)
            self.webhook_stderr = WebhookStream(sys.stderr, WEBHOOK_URL, self.loop)

            # Replace the system streams
            sys.stdout = self.webhook_stdout
            sys.stderr = self.webhook_stderr

        # The rest of your original setup_hook
        # await self.load_extension("cogs.status")
        # await self.load_extension("cogs.configure")
        await self.tree.sync()

    # Your original on_error method is unchanged. Its output will now be
    # automatically captured by the new sys.stdout/sys.stderr.
    async def on_error(self, event, *args, **kwargs):
        error_info = "unknown action"
        context = args[0] if args else None
        if isinstance(context, discord.Interaction):
            if context.command:
                error_info = f"command /{context.command.name}"
            elif context.data.get("custom_id"):
                error_info = f"interaction with {context.data.get('custom_id')}"
        error_message = f"Error in {error_info}: {''.join(traceback.format_exception_only(*sys.exc_info()[:2]))}"

        # This will now be sent to the webhook because sys.stdout is redirected
        print(error_message)

    async def close(self):
        """Custom close to also clean up our logger's session and restore stdout/stderr."""
        if hasattr(self, 'original_stdout') and self.original_stdout:
            sys.stdout = self.original_stdout
            await self.webhook_stdout.close()
        if hasattr(self, 'original_stderr') and self.original_stderr:
            sys.stderr = self.original_stderr
            await self.webhook_stderr.close()
            
        await super().close()


intents = discord.Intents.default()
intents.message_content = True
# By setting command_prefix to None, the bot will no longer listen to prefix commands like "!t"
# It will only respond to slash commands.
bot = JBAppBot(command_prefix=None, intents=intents)

@bot.event
async def on_ready():
    print(f"logged in as {bot.user}")

# Your original run logic is unchanged
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    # This will also be sent to the webhook
    print("DISCORD_TOKEN not found in .env file. Bot cannot start.", file=sys.stderr)
