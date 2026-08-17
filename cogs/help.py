# KimiXP - Discord Bot
# Copyright (C) 2026 BrunoDevPe
#
# This file is part of KimiXP.
#
# KimiXP is free software licensed under the GNU General Public License v3.0.
# See the LICENSE file in the root directory for more information.

import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import ConfigManager

logger = logging.getLogger("KimiBot.Help")


class HelpCog(commands.Cog):
    """Cog para comandos de ayuda del bot."""

    def __init__(self, bot: commands.Bot, config_mgr: ConfigManager):
        self.bot = bot
        self.config_mgr = config_mgr

    def _build_help_embed(self, user: discord.abc.User) -> discord.Embed:
        embed = discord.Embed(
            title="📖 Comandos Disponibles",
            color=self.config_mgr.get_color("color_primary")
        )
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))
        embed.set_thumbnail(url=getattr(user, "display_avatar", None).url if hasattr(user, "display_avatar") else None)

        embed.add_field(
            name="📊 Perfil y Niveles",
            value=(
                "`!level` / `/level` — Muestra tu nivel y progreso.\n"
                "`!rank` / `/rank` — Muestra tu posición en el ranking.\n"
                "`!profile` / `/profile` — Tarjeta de perfil completa.\n"
                "`!leaderboard` / `/leaderboard` — Tabla de clasificación.\n"
                "`!levels` / `/levels` — Progreso de niveles de todos los miembros."
            ),
            inline=False
        )
        embed.add_field(
            name="🛡️ Administración",
            value=(
                "`!admin_add_xp` / `/admin_add_xp` — Añade XP a un usuario.\n"
                "`!admin_set_level` / `/admin_set_level` — Establece el nivel de un usuario.\n"
                "`!admin_sync` / `/admin_sync` — Sincroniza comandos slash.\n"
                "`!admin_reload_config` / `/admin_reload_config` — Recarga la configuración.\n"
                "`!reset` / `/reset` — Reinicia estadísticas del servidor.\n"
                "`!recuperar` / `/recuperar` — Recupera historial de mensajes."
            ),
            inline=False
        )
        embed.add_field(
            name="ℹ️ Ayuda",
            value="`!help` / `/help` — Muestra este mensaje.",
            inline=False
        )

        prefix = self.config_mgr.config.get("prefix", {}).get("default", "!")
        embed.set_footer(text=f"Prefijo actual: {prefix} • {self.config_mgr.config.get('embeds', {}).get('footer_text', '')}")

        return embed

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context) -> None:
        embed = self._build_help_embed(ctx.author)
        await ctx.send(embed=embed)

    @app_commands.command(name="help", description="Muestra la lista de comandos disponibles.")
    async def help_slash(self, interaction: discord.Interaction) -> None:
        embed = self._build_help_embed(interaction.user)
        await interaction.response.send_message(embed=embed)
