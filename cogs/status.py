import discord
from discord.ext import commands, tasks
from discord import app_commands, ButtonStyle
from discord.ui import Button, View
import aiohttp
from config_manager import GuildConfigManager
import os

STATUS_NOTE = os.getenv("STATUS_NOTE", "")

class StatusView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Website", style=ButtonStyle.link, url="https://jailbreaks.app"))

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = GuildConfigManager()
        self.last_signed = {}
        self.check_status.start()

    @app_commands.command(name="status", description="Check jailbreaks.app status")
    async def status(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://api.jailbreaks.app/status", timeout=10) as resp:
                    data = await resp.json()
                    signed = data.get("status","unknown").lower() == "signed"
                    message = (
                        "✅ Jailbreaks.app is signed right now. This means you can install apps"
                        if signed else
                        "❌ Jailbreaks.app is not signed right now. This means you can not install apps"
                    )
                    if STATUS_NOTE:
                        message += f"\n\nNOTE: {STATUS_NOTE}"

                    embed = discord.Embed(
                        description=message,
                        color=discord.Color.green() if signed else discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, view=StatusView())
            except Exception:
                await interaction.response.send_message("Failed to fetch status", ephemeral=True)

    @app_commands.command(name="certinfo", description="Show jailbreaks.app certificate info")
    async def certinfo(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://api.jailbreaks.app/info", timeout=10) as resp:
                    data = await resp.json()
                    cert_name = data.get("name","Unknown")
                    status = data.get("status","Unknown")
                    expires = data.get("expirationDate","Unknown")
                    emoji = "✅" if status.lower() == "signed" else "❌"

                    text = (
                        f"📜 Certificate: {cert_name}\n\n"
                        f"{emoji} Status: {status}\n\n"
                        f"⏰ Expiry date: {expires}\n\n"
                        "-# Note: Expiry date does not correlate to when it is revoked; it can be revoked by Apple at any time."
                    )
                    embed = discord.Embed(description=text, color=discord.Color.blue())
                    await interaction.response.send_message(embed=embed)
            except Exception:
                await interaction.response.send_message("Failed to fetch cert info", ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_status(self):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://api.jailbreaks.app/status", timeout=10) as resp:
                    data = await resp.json()
                    signed = data.get("status","unknown").lower() == "signed"
            except Exception:
                return

        for guild in self.bot.guilds:
            cfg = self.config_manager.get_guild_config(guild.id)
            channel_id = cfg.get("channel_id")
            role_id = cfg.get("ping_role_id")
            if not channel_id:
                continue
            last = self.last_signed.get(guild.id)
            if last is not None and last == signed:
                continue
            self.last_signed[guild.id] = signed
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            role = guild.get_role(role_id) if role_id else None

            message = (
                "✅ Jailbreaks.app is signed right now. This means you can install apps"
                if signed else
                "❌ Jailbreaks.app is not signed right now. This means you can not install apps"
            )
            if STATUS_NOTE:
                message += f"\n\nNOTE: {STATUS_NOTE}"

            embed = discord.Embed(
                description=message,
                color=discord.Color.green() if signed else discord.Color.red()
            )
            view = StatusView()
            await channel.send(content=role.mention if role else None, embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(StatusCog(bot))