import discord
from discord.ext import commands
from discord import app_commands
from config_manager import ConfigManager

class ConfigModal(discord.ui.Modal, title="Configure Bot"):
    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

        # Load existing config for the guild
        cfg = ConfigManager.load_config()
        guild_cfg = cfg.get(str(guild_id), {})

        # Initialize form fields with existing values as placeholders
        self.channel_id = discord.ui.TextInput(
            label="Channel ID",
            required=True,
            placeholder=guild_cfg.get("channel_id", "Enter Channel ID")
        )
        self.ping_role_id = discord.ui.TextInput(
            label="Ping Role ID (optional)",
            required=False,
            placeholder=guild_cfg.get("ping_role_id", "Enter Ping Role ID") or ""
        )
        self.approved_role_id = discord.ui.TextInput(
            label="Approved Role ID (optional)",
            required=False,
            placeholder=guild_cfg.get("approved_role_id", "Enter Approved Role ID") or ""
        )

        # Add inputs to the modal
        self.add_item(self.channel_id)
        self.add_item(self.ping_role_id)
        self.add_item(self.approved_role_id)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = ConfigManager.load_config()
        cfg[str(self.guild_id)] = {
            "channel_id": self.channel_id.value,
            "ping_role_id": self.ping_role_id.value or None,
            "approved_role_id": self.approved_role_id.value or None
        }
        ConfigManager.save_config(cfg)
        await interaction.response.send_message(embed=discord.Embed(
            title="Configuration Saved",
            description="Your settings have been updated.",
            color=discord.Color.green()
        ), ephemeral=True)

class ConfigureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="configure", description="Adjust settings for status announcement messages")
    async def configure(self, interaction: discord.Interaction):
        member = interaction.user
        cfg = ConfigManager.load_config()
        guild_cfg = cfg.get(str(interaction.guild_id), {})

        approved_role_id = guild_cfg.get("approved_role_id")
        has_permission = (
            member.guild_permissions.administrator
            or (approved_role_id and discord.utils.get(member.roles, id=int(approved_role_id)))
        )
        if not has_permission:
            await interaction.response.send_message(embed=discord.Embed(
                title="Permission Denied",
                description="You do not have permission to do this.",
                color=discord.Color.red()
            ), ephemeral=True)
            return

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Configuration Form", style=discord.ButtonStyle.primary, custom_id="open_config"))
        view.add_item(discord.ui.Button(label="View Current Settings", style=discord.ButtonStyle.secondary, custom_id="view_config"))

        await interaction.response.send_message(embed=discord.Embed(
            title="Bot Configuration",
            description="Adjust settings for status announcement messages. If it says 'Something went wrong. Try again later.' on the form, just press submit again and then cancel.",
            color=discord.Color.blue()
        ), view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        guild_id = interaction.guild_id

        if custom_id == "open_config":
            modal = ConfigModal(guild_id)
            await interaction.response.send_modal(modal)

        elif custom_id == "view_config":
            cfg = ConfigManager.load_config()
            guild_cfg = cfg.get(str(guild_id), {})
            description = "\n".join(f"**{k}**: {v}" for k, v in guild_cfg.items()) or "No settings configured."
            embed = discord.Embed(
                title="Current Settings",
                description=description,
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConfigureCog(bot))