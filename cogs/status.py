import discord
from discord.ext import commands, tasks
import aiohttp
from discord import app_commands
from .config_manager import ConfigManager
import os
from email.utils import parsedate_to_datetime
from textwrap import dedent

STATUS_URL = "https://api.jailbreaks.app/status"
INFO_URL = "https://api.jailbreaks.app/info"
STATUS_NOTE = os.getenv("STATUS_NOTE", "")

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_status = None
        self.check_status.start()

    def cog_unload(self):
        self.check_status.cancel()

    def to_discord_ts(self, dt_str: str) -> str:
        if not dt_str:
            return "None"
        try:
            dt = parsedate_to_datetime(dt_str)
            ts = int(dt.timestamp())
            return f"<t:{ts}:f>"
        except Exception:
            return dt_str

    async def send_error(self, interaction: discord.Interaction, msg: str):
        embed = discord.Embed(description=msg, color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="status", description="Check Jailbreaks.app status")
    @app_commands.describe(ephemeral="Optional: Make the bot's reply only be visible to you (Default is false)")
    async def status(self, interaction: discord.Interaction, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(STATUS_URL) as resp:
                    data = await resp.json()

            status_val = data.get("status", "")
            signed = status_val.lower() == "signed"
            color = discord.Color.green() if signed else discord.Color.red()
            message = (
                "✅ Jailbreaks.app is signed right now! This means you can install apps."
                if signed
                else "❌ Jailbreaks.app is not signed right now. This means you cannot install apps."
            )

            embed = discord.Embed(description=message, color=color)

            if STATUS_NOTE:
                embed.add_field(name="Note:", value=STATUS_NOTE, inline=False)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Website", url="https://jailbreaks.app"))
            await interaction.followup.send(embed=embed, view=view)
        except Exception:
            await self.send_error(interaction, "Sorry, something went wrong while fetching the status.")

    @app_commands.command(name="certinfo", description="Check Jailbreaks.app certificate info")
    @app_commands.describe(ephemeral="Optional: Make the bot's reply only be visible to you (Default is false)")
    async def certinfo(self, interaction: discord.Interaction, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(INFO_URL) as resp:
                    data = await resp.json()

            status = data.get("status", "Unknown")
            revocation_date = data.get("revocationDate")

            description_str = dedent(f"""
            📜 Certificate: {data.get("name", "Unknown")}

            {"✅" if status == "Signed" else "❌"} Status: {status}

            ⏰ Expiry date: {self.to_discord_ts(data.get("expirationDate"))}

            {f"⏳ Revocation date: {self.to_discord_ts(revocation_date)}" if revocation_date is not None else ""}

            -# Keep in mind that expiry date does not correlate to when it is revoked, and Revocation date is for when it was previously revoked, not a date in the future.
            """).strip().replace("\n\n\n", "\n")  # remove extra newlines if no revocation date

            embed = discord.Embed(description=description_str, color=discord.Color.blue())

            if STATUS_NOTE:
                embed.add_field(name="Note", value=STATUS_NOTE, inline=False)

            await interaction.followup.send(embed=embed)
        except Exception:
            await self.send_error(interaction, "Sorry, something went wrong while fetching the certificate info.")

    async def update_presence(self, signed: bool):
        note_lower = STATUS_NOTE.lower()
        if "global" in note_lower and "blacklist" in note_lower:
            await self.bot.change_presence(
                status=discord.Status.idle,
                activity=discord.Activity(type=discord.ActivityType.watching, name="🚧 Globally Blacklisted")
            )
        elif signed:
            await self.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(type=discord.ActivityType.watching, name="✅ Signed")
            )
        else:
            await self.bot.change_presence(
                status=discord.Status.dnd,
                activity=discord.Activity(type=discord.ActivityType.watching, name="❌ Revoked")
            )

    @tasks.loop(minutes=2)
    async def check_status(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(STATUS_URL) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.json()

            status_val = data.get("status", "")
            new_status = "signed" if status_val.lower() == "signed" else "unsigned"

            if self.last_status is None:
                self.last_status = new_status
                await self.update_presence(new_status == "signed")
                return

            if new_status != self.last_status:
                self.last_status = new_status
                signed = new_status == "signed"
                await self.announce_status_change(signed)
                await self.update_presence(signed)
        except Exception:
            pass

    async def announce_status_change(self, signed: bool):
        configs = ConfigManager.load_config()
        for guild_id, cfg in configs.items():
            if not cfg.get("channel_id"):
                continue
            try:
                gid_int = int(guild_id)
            except ValueError:
                continue
            guild = self.bot.get_guild(gid_int)
            if not guild:
                continue
            try:
                channel_id = int(cfg["channel_id"])
            except (KeyError, ValueError):
                continue
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            role = None
            if cfg.get("ping_role_id"):
                try:
                    role = guild.get_role(int(cfg["ping_role_id"]))
                except ValueError:
                    pass

            color = discord.Color.green() if signed else discord.Color.red()
            desc = "Jailbreaks.app is now signed!" if signed else "Jailbreaks.app is no longer signed."
            embed = discord.Embed(description=desc, color=color)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Website", url="https://jailbreaks.app"))

            content = role.mention if role else None
            try:
                await channel.send(content=content, embed=embed, view=view)
            except Exception:
                pass

    @check_status.before_loop
    async def before_check_status(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(StatusCog(bot))