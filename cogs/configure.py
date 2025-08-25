import discord
from discord import app_commands
from discord.ext import commands
from config_manager import GuildConfigManager

class ConfigureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = GuildConfigManager()

    @app_commands.command(name="configure", description="Configure bot status announcements")
    async def configure(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        cfg = self.config_manager.get_guild_config(guild_id)
        approved_roles = cfg.get("approved_role_ids", [])
        # check admin permission or approved role
        has_perm = interaction.user.guild_permissions.administrator or any(
            r.id in approved_roles for r in interaction.user.roles
        )
        if not has_perm:
            embed = discord.Embed(
                description="You do not have permission to do this.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title="Bot Configuration", color=discord.Color.green())
        view = discord.ui.View()

        async def view_settings(inter: discord.Interaction):
            data = self.config_manager.get_guild_config(guild_id)
            embed2 = discord.Embed(title="Current Configuration", color=discord.Color.blue())
            embed2.add_field(name="Channel ID", value=str(data.get("channel_id", "Not set")), inline=False)
            embed2.add_field(name="Ping Role ID", value=str(data.get("ping_role_id", "Not set")), inline=False)
            embed2.add_field(name="Approved Role ID(s)", value=str(data.get("approved_role_ids", [])), inline=False)
            await inter.response.send_message(embed=embed2, ephemeral=True)

        async def change_settings(inter: discord.Interaction):
            modal = ConfigModal(self.config_manager, guild_id)
            await inter.response.send_modal(modal)

        view.add_item(discord.ui.Button(label="Change Settings", style=discord.ButtonStyle.green))
        view.add_item(discord.ui.Button(label="View Settings", style=discord.ButtonStyle.blurple))
        view.children[0].callback = change_settings
        view.children[1].callback = view_settings

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfigModal(discord.ui.Modal, title="Configure Bot"):
    def __init__(self, manager: GuildConfigManager, guild_id: int):
        super().__init__()
        self.manager = manager
        self.guild_id = guild_id

        cfg = manager.get_guild_config(guild_id)
        self.channel_id_input = discord.ui.TextInput(
            label="Channel ID", required=False, default=str(cfg.get("channel_id", ""))
        )
        self.ping_role_input = discord.ui.TextInput(
            label="Role ID to ping", required=False, default=str(cfg.get("ping_role_id", ""))
        )
        self.approved_roles_input = discord.ui.TextInput(
            label="Approved Role ID(s) (comma-separated)", required=False,
            default=",".join(map(str, cfg.get("approved_role_ids", [])))
        )

        self.add_item(self.channel_id_input)
        self.add_item(self.ping_role_input)
        self.add_item(self.approved_roles_input)

    async def on_submit(self, interaction: discord.Interaction):
        channel_id = int(self.channel_id_input.value) if self.channel_id_input.value else None
        ping_role_id = int(self.ping_role_input.value) if self.ping_role_input.value else None
        approved_roles = [int(r.strip()) for r in self.approved_roles_input.value.split(",") if r.strip()]

        self.manager.set_guild_config(
            self.guild_id,
            channel_id=channel_id,
            ping_role_id=ping_role_id,
        )
        cfg = self.manager.get_guild_config(self.guild_id)
        cfg["approved_role_ids"] = approved_roles
        self.manager.set_guild_config(self.guild_id, **cfg)

        await interaction.response.send_message("✅ Configuration updated!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ConfigureCog(bot))