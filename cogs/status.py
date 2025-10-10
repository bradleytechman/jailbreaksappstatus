import discord
from discord.ext import commands, tasks
import aiohttp
import json
from discord import app_commands
from .config_manager import ConfigManager
import os

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

    @app_commands.command(name="status", description="Check Jailbreaks.app status")
    @app_commands.describe(ephemeral="Optional: Make the bot's reply only be visible to you (Default if not set is false)")
    async def status(self, interaction: discord.Interaction, ephemeral: bool = False):
        async with aiohttp.ClientSession() as session:
            async with session.get(STATUS_URL) as resp:
                data = await resp.json()

        status_val = data.get("status", "")
        signed = status_val == "Signed"

        if signed:
            color = discord.Color.green()
            message = "✅ Jailbreaks.app is signed right now! This means you can install apps."
        else:
            color = discord.Color.red()
            message = "❌ Jailbreaks.app is not signed right now. This means you can not install apps"

        embed = discord.Embed(description=message, color=color)
        if STATUS_NOTE:
            embed.add_field(name="Note:", value=STATUS_NOTE, inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Website", url="https://jailbreaks.app"))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)

    @app_commands.command(name="certinfo", description="Check Jailbreaks.app certificate info")
    @app_commands.describe(ephemeral="Optional: Make the bot's reply only be visible to you (Default if not set is false)")
    async def certinfo(self, interaction: discord.Interaction, ephemeral: bool = False):
        async with aiohttp.ClientSession() as session:
            async with session.get(INFO_URL) as resp:
                data = await resp.json()

        cert_name = data.get("name", "Unknown")
        status = data.get("status", "Unknown")
        expires = data.get("expirationDate", "Unknown")
        revoked = data.get("revocationDate", "Unknown")

        emoji = "✅" if status == "Signed" else "❌"

        embed = discord.Embed(color=discord.Color.blue())
        embed.description = (
            f"📜 Certificate: {cert_name}\n\n"
            f"{emoji} Status: {status}\n\n"
            f"⏰ Expiry date: {expires}\n\n"
            f"⏳ Revocation date: {revoked}\n\n"
            f"-# Keep in mind that expiry date does not correlate to when it is revoked, and Revocation date is for when it was previously revoked, not a date in the future."
        )
        if STATUS_NOTE:
            embed.add_field(name="Note", value=STATUS_NOTE, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @tasks.loop(minutes=1)
    async def check_status(self):
        await self.bot.wait_until_ready()

        async with aiohttp.ClientSession() as session:
            async with session.get(STATUS_URL) as resp:
                if resp.status != 200:
                    return
                data = await resp.json()

        status_val = data.get("status", "")
        signed = status_val == "Signed"
        new_status = "signed" if signed else "unsigned"

        if self.last_status is None:
            self.last_status = new_status
            return

        if new_status != self.last_status:
            self.last_status = new_status
            try:
                await self.announce_status_change(signed)
            except Exception:
                pass

    async def announce_status_change(self, signed: bool):
        configs = ConfigManager.load_config()

        for guild_id, cfg in configs.items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue

            channel_id = cfg.get("channel_id")
            role_id = cfg.get("ping_role_id")

            if not channel_id:
                continue

            channel = guild.get_channel(int(channel_id))
            role = guild.get_role(int(role_id)) if role_id else None

            if signed:
                color = discord.Color.green()
                embed = discord.Embed(
                    description="Jailbreaks.app is signed!",
                    color=color
                )
            else:
                color = discord.Color.red()
                embed = discord.Embed(
                    description="Jailbreaks.app is no longer signed.",
                    color=color
                )

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Website", url="https://jailbreaks.app"))

            content = role.mention if role else None
            await channel.send(content=content, embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(StatusCog(bot))
