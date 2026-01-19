import discord
from discord.ext import commands
from discord import app_commands
from .config_manager import ConfigManager
import traceback
import sys

class ConfigModal(discord.ui.Modal, title="Configure Bot"):
    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id
        cfg = ConfigManager.load_config().get(str(guild_id), {})
        self.channel_id = discord.ui.TextInput(label="Channel ID for notifications", required=False, placeholder=cfg.get("channel_id", "Enter Channel ID"))
        self.ping_role_id = discord.ui.TextInput(label="Ping Role ID (optional)", required=False, placeholder=cfg.get("ping_role_id", "Enter Role ID to ping"))
        self.approved_role_id = discord.ui.TextInput(label="Approved Role ID (optional)", required=False, placeholder=cfg.get("approved_role_id", "Role that can use /configure"))
        self.add_item(self.channel_id)
        self.add_item(self.ping_role_id)
        self.add_item(self.approved_role_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cfg = ConfigManager.load_config()
            guild_cfg = cfg.get(str(self.guild_id), {})
            if self.channel_id.value: guild_cfg["channel_id"] = self.channel_id.value
            if self.ping_role_id.value: guild_cfg["ping_role_id"] = self.ping_role_id.value
            if self.approved_role_id.value: guild_cfg["approved_role_id"] = self.approved_role_id.value
            cfg[str(self.guild_id)] = guild_cfg
            ConfigManager.save_config(cfg)
            await interaction.response.send_message("Configuration saved.", ephemeral=True)
        except Exception:
            # Send trace to stderr which should be captured by webhook stream
            traceback.print_exc()
            try:
                await interaction.response.send_message("An error occurred while saving configuration.", ephemeral=True)
            except Exception:
                # In case response fails (rare), fallback to webhook-captured stderr
                traceback.print_exc(file=sys.stderr)

class ResetConfirmModal(discord.ui.Modal, title="Confirm Reset"):
    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id
        self.confirm = discord.ui.TextInput(label="Type 'RESET' to confirm", placeholder="This action cannot be undone.")
        self.add_item(self.confirm)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.confirm.value.upper() == "RESET":
                cfg = ConfigManager.load_config()
                if cfg.pop(str(self.guild_id), None):
                    ConfigManager.save_config(cfg)
                    await interaction.response.send_message("Settings for this server have been reset.", ephemeral=True)
                else:
                    await interaction.response.send_message("No settings were found to reset.", ephemeral=True)
            else:
                await interaction.response.send_message("Phrase was typed incorrectly, reset cancelled.", ephemeral=True)
        except Exception:
            traceback.print_exc()
            try:
                await interaction.response.send_message("An error occurred while resetting configuration.", ephemeral=True)
            except Exception:
                traceback.print_exc(file=sys.stderr)

class ConfigureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configure", description="Adjust settings for status announcement messages")
    async def configure(self, interaction: discord.Interaction):
        try:
            # First check whether this interaction came from a guild (server)
            if interaction.guild is None:
                # User account / DM - cannot use this command
                embed = discord.Embed(
                    title="Cannot use command here",
                    description="You cannot use this command on a user account (DM). This command must be used in a server.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            cfg = ConfigManager.load_config().get(str(interaction.guild_id), {})
            approved_role_id = cfg.get("approved_role_id")
            member = interaction.user
            # Ensure approved_role_id is treated safely
            has_approved_role = False
            try:
                if approved_role_id:
                    has_approved_role = any(role.id == int(approved_role_id) for role in member.roles)
            except Exception:
                # In case of malformed saved ID or other issues, log to stderr for webhook capture
                traceback.print_exc()

            has_permission = member.guild_permissions.administrator or has_approved_role
            if not has_permission:
                embed = discord.Embed(
                    title="Insufficient Permissions",
                    description="You need to be an Administrator or have an approved role to use this command.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="Configure", style=discord.ButtonStyle.primary, custom_id="open_config"))
            view.add_item(discord.ui.Button(label="View Settings", style=discord.ButtonStyle.secondary, custom_id="view_config"))
            view.add_item(discord.ui.Button(label="Reset", style=discord.ButtonStyle.danger, custom_id="reset_config"))

            embed = discord.Embed(
                title="Bot Configuration",
                description="Use the buttons below to manage settings for status announcements.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception:
            # Ensure any unexpected errors are printed to stderr so the webhook capture can send them
            traceback.print_exc()
            try:
                await interaction.response.send_message("An unexpected error occurred while processing the command.", ephemeral=True)
            except Exception:
                traceback.print_exc(file=sys.stderr)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.guild or interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id")
        try:
            if custom_id == "open_config":
                await interaction.response.send_modal(ConfigModal(interaction.guild_id))
            elif custom_id == "view_config":
                cfg = ConfigManager.load_config().get(str(interaction.guild_id), {})
                desc = "\n".join(f"**{k}**: {v}" for k, v in cfg.items()) if cfg else "No settings configured."
                await interaction.response.send_message(embed=discord.Embed(title="Current Settings", description=desc, color=discord.Color.blue()), ephemeral=True)
            elif custom_id == "reset_config":
                await interaction.response.send_modal(ResetConfirmModal(interaction.guild_id))
        except Exception:
            traceback.print_exc()
            try:
                await interaction.response.send_message("An unexpected error occurred while handling interaction.", ephemeral=True)
            except Exception:
                traceback.print_exc(file=sys.stderr)

async def setup(bot):
    await bot.add_cog(ConfigureCog(bot))
