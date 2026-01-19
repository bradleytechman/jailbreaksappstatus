import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import aiohttp
import asyncio

# Load environment variables early
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Global queue used by WebhookStream and the bot's background task
log_queue: asyncio.Queue | None = None

class WebhookStream:
    def __init__(self, original_stream):
        self.original_stream = original_stream

    def write(self, message: str):
        # Always write to original stream
        try:
            self.original_stream.write(message)
            self.original_stream.flush()
        except Exception:
            pass

        if not message or not message.strip():
            return

        # Enqueue message for async processing (if queue exists)
        global log_queue
        if log_queue is not None:
            try:
                # Non-blocking put; if queue is full or missing, we just skip
                log_queue.put_nowait(message)
            except Exception:
                # As last resort, ignore
                pass

    def flush(self):
        try:
            self.original_stream.flush()
        except Exception:
            pass

class JBAppBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_session: aiohttp.ClientSession | None = None
        self.log_webhook: discord.Webhook | None = None
        self.log_task: asyncio.Task | None = None

    async def setup_hook(self):
        # Initialize log queue in the running loop
        global log_queue
        if WEBHOOK_URL:
            if log_queue is None:
                log_queue = asyncio.Queue()

            # Create session and webhook bound to this loop
            self.log_session = aiohttp.ClientSession()
            self.log_webhook = discord.Webhook.from_url(
                WEBHOOK_URL,
                session=self.log_session,
            )

            # Start background consumer task
            self.log_task = asyncio.create_task(self.log_consumer())

        # Load Cogs
        await self.load_extension("cogs.status")
        await self.load_extension("cogs.configure")

        # Sync commands to Discord
        await self.tree.sync()

    async def log_consumer(self):
        """
        Background task that reads messages from log_queue and sends them to the webhook.
        """
        assert log_queue is not None
        while not self.is_closed():
            try:
                message = await log_queue.get()
                if not self.log_webhook:
                    continue

                # Truncate to Discord limit
                if len(message) > 1990:
                    message = message[:1990]

                await self.log_webhook.send(f"```\n{message.strip()}\n```")
            except asyncio.CancelledError:
                break
            except Exception as e:
                # If sending fails, write error to original stderr
                try:
                    sys.__stderr__.write(f"[WebhookStream Error] Failed to send log: {e}\n")
                    sys.__stderr__.flush()
                except Exception:
                    pass

    async def on_error(self, event, *args, **kwargs):
        print(f"An unhandled error occurred in event: {event}")
        traceback.print_exc()

    async def close(self):
        # Stop log task first
        if self.log_task:
            self.log_task.cancel()
            try:
                await self.log_task
            except asyncio.CancelledError:
                pass

        # Close session
        if self.log_session:
            try:
                await self.log_session.close()
            except Exception:
                pass

        # Restore original streams
        if 'original_stdout' in globals():
            try:
                sys.stdout = globals().get('original_stdout', sys.stdout)
            except Exception:
                pass
        if 'original_stderr' in globals():
            try:
                sys.stderr = globals().get('original_stderr', sys.stderr)
            except Exception:
                pass

        await super().close()

def no_prefix_callable(bot, message):
    return []

intents = discord.Intents.default()
intents.message_content = True

bot = JBAppBot(command_prefix=no_prefix_callable, intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot is ready and synced. Found {len(bot.tree.get_commands())} slash commands.")

# Initialize webhook capturing AFTER defining bot but still at import time
if WEBHOOK_URL:
    try:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = WebhookStream(sys.stdout)
        sys.stderr = WebhookStream(sys.stderr)
    except Exception:
        # If anything goes wrong setting up the webhook capture, fallback to original streams
        traceback.print_exc()

if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("FATAL: DISCORD_TOKEN not found in .env file. Bot cannot start.", file=sys.stderr)
