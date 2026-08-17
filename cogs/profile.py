# KimiXP - Discord Bot
# Copyright (C) 2026 BrunoDevPe
#
# This file is part of KimiXP.
#
# KimiXP is free software licensed under the GNU General Public License v3.0.
# See the LICENSE file in the root directory for more information.

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from database.database import Database
from utils.config import ConfigManager
from utils.leveling import LevelCalculator

logger = logging.getLogger("KimiBot.Profile")


class LeaderboardView(discord.ui.View):
    """Vista de paginación interactiva con botones para el comando /leaderboard."""

    def __init__(self, data: list, items_per_page: int, config_mgr: ConfigManager, calculator: LevelCalculator):
        super().__init__(timeout=120)
        self.data = data
        self.items_per_page = items_per_page
        self.config_mgr = config_mgr
        self.calculator = calculator
        self.current_page = 0
        self.max_pages = max(1, (len(data) + items_per_page - 1) // items_per_page)

    def create_embed(self, guild: discord.Guild) -> discord.Embed:
        cfg = self.config_mgr.config.get("leaderboard_command", {})
        color = self.config_mgr.get_color(cfg.get("embed_color", "color_primary"))
        title = cfg.get("embed_title", "🏆 Tabla de Clasificación")
        footer_text = cfg.get("embed_footer", self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.data[start:end]

        if not page_items:
            embed.description = "No hay registros disponibles en la tabla de clasificación."
            embed.set_footer(text=footer_text)
            return embed

        total_users = len(self.data)
        lines = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}

        for idx, user_row in enumerate(page_items, start=start + 1):
            user_id = user_row["user_id"]
            member = guild.get_member(user_id)
            name = member.display_name if member else f"Usuario ({user_id})"

            level = user_row["level"]
            xp = user_row["total_xp_earned"]
            details = self.calculator.get_progress_details(xp)
            progress_bar = LevelCalculator.render_progress_bar(details["percentage"])

            medal = medals.get(idx, f"**#{idx}**")
            pos_label = f"{medal} **{name}**"

            if details["percentage"] >= 100.0:
                progress_label = "🏆 **Nivel máximo**"
            else:
                remaining = details["xp_needed_for_next"] - details["xp_in_level"]
                progress_label = f"Faltan `{remaining:,}` XP para nivel {level + 1}"

            lines.append(
                f"{pos_label}\n"
                f"Nivel **{level}** • `{xp:,}` XP total\n"
                f"`{progress_bar}` **{details['percentage']}%**\n"
                f"{progress_label}\n"
            )

        embed.description = "\n".join(lines)

        if self.data:
            top_member = guild.get_member(self.data[0]["user_id"])
            if top_member and top_member.display_avatar:
                embed.set_thumbnail(url=top_member.display_avatar.url)

        embed.set_footer(
            text=f"Página {self.current_page + 1} de {self.max_pages} • {total_users} miembros • {footer_text}"
        )
        return embed

    @discord.ui.button(label="◀ Anterior", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Siguiente ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            embed = self.create_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()


class LevelsView(discord.ui.View):
    """Vista de paginación para el comando /levels."""

    def __init__(self, members: list, items_per_page: int, config_mgr: ConfigManager, calculator: LevelCalculator, author_id: int):
        cfg = config_mgr.config.get("levels_command", {})
        timeout = cfg.get("button_timeout", 120)
        super().__init__(timeout=timeout)
        self.members = members
        self.items_per_page = items_per_page
        self.config_mgr = config_mgr
        self.calculator = calculator
        self.author_id = author_id
        self.current_page = 0
        self.max_pages = max(1, (len(members) + items_per_page - 1) // items_per_page)

    def create_embed(self) -> discord.Embed:
        cfg = self.config_mgr.config.get("levels_command", {})
        color = self.config_mgr.get_color(cfg.get("embed_color", "color_primary"))
        title = cfg.get("embed_title", "⭐ Niveles — Botlevel")
        footer = cfg.get("embed_footer", "Botlevel")

        embed = discord.Embed(title=title, color=color)

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_members = self.members[start:end]

        description_lines = []
        for idx, info in enumerate(page_members, start=start + 1):
            member = info["member"]
            level = info["level"]
            xp = info["xp"]
            details = self.calculator.get_progress_details(xp)
            progress_bar = LevelCalculator.render_progress_bar(details["percentage"])

            if details["percentage"] >= 100.0:
                progress_text = "🏆 NIVEL MÁXIMO"
            else:
                remaining = details["xp_needed_for_next"] - details["xp_in_level"]
                progress_text = f"Faltan `{remaining:,}` XP"

            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            pos_str = medals.get(idx, f"**#{idx}**")

            description_lines.append(
                f"{pos_str} {member.mention}\n"
                f"Nivel `{level}`\n"
                f"`{details['xp_in_level']:,} / {details['xp_needed_for_next']:,}` XP\n"
                f"`{progress_bar}` **{details['percentage']}%**\n"
                f"{progress_text}\n"
            )

        embed.description = "\n".join(description_lines)
        embed.set_footer(text=f"Página {self.current_page + 1} de {self.max_pages} • {footer}")
        return embed

    @discord.ui.button(label="◀ Anterior", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ No puedes controlar este menú.", ephemeral=True)
            return

        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Siguiente ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ No puedes controlar este menú.", ephemeral=True)
            return

        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()


class ProfileCog(commands.Cog):
    """Cog para slash commands y comandos de prefijo de perfil, nivel, ranking y tabla de clasificación."""

    def __init__(self, bot: commands.Bot, db: Database, config_mgr: ConfigManager):
        self.bot = bot
        self.db = db
        self.config_mgr = config_mgr

    @property
    def calculator(self) -> LevelCalculator:
        formula_cfg = self.config_mgr.config.get("formula", {})
        return LevelCalculator(
            base_multiplier=formula_cfg.get("base_multiplier", 50.0),
            linear_increment=formula_cfg.get("linear_increment", 100.0)
        )

    # --- Slash commands ---
    @app_commands.command(name="level", description="Muestra tu nivel actual y progreso de XP.")
    @app_commands.describe(usuario="El usuario del que deseas consultar el nivel (opcional).")
    async def level_slash(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None) -> None:
        target = usuario or interaction.user
        if target.bot:
            await interaction.response.send_message("❌ Los bots no acumulan experiencia ni niveles.", ephemeral=True)
            return

        if not await self.config_mgr.is_leveling_enabled(interaction.guild_id):
            await interaction.response.send_message("❌ El sistema de niveles está desactivado en este servidor.", ephemeral=True)
            return

        user_data = await self.db.get_user(interaction.guild_id, target.id)
        details = self.calculator.get_progress_details(user_data["xp"])
        progress_bar = LevelCalculator.render_progress_bar(details["percentage"])

        embed = discord.Embed(
            title=f"⭐ Nivel de {target.display_name}",
            color=self.config_mgr.get_color("color_primary")
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Nivel Actual", value=f"**{details['level']}**", inline=True)
        embed.add_field(name="XP Acumulada", value=f"`{details['xp_in_level']:,} / {details['xp_needed_for_next']:,} XP`", inline=True)
        embed.add_field(name="Progreso", value=f"`{progress_bar}` **{details['percentage']}%**", inline=False)
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rank", description="Muestra tu posición exacta en el ranking del servidor.")
    @app_commands.describe(usuario="El usuario a consultar (opcional).")
    async def rank_slash(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None) -> None:
        target = usuario or interaction.user
        if target.bot:
            await interaction.response.send_message("❌ Los bots no poseen ranking.", ephemeral=True)
            return

        if not await self.config_mgr.is_leveling_enabled(interaction.guild_id):
            await interaction.response.send_message("❌ El sistema de niveles está desactivado en este servidor.", ephemeral=True)
            return

        user_data = await self.db.get_user(interaction.guild_id, target.id)
        rank, total_users = await self.db.get_user_rank(interaction.guild_id, target.id)

        embed = discord.Embed(
            title=f"🏆 Posición en el Ranking — {target.display_name}",
            color=self.config_mgr.get_color("color_primary")
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Posición", value=f"**#{rank}** de `{total_users}` usuarios", inline=True)
        embed.add_field(name="Nivel", value=f"**{user_data['level']}**", inline=True)
        embed.add_field(name="XP Total Ganada", value=f"`{user_data['total_xp_earned']:,}` XP", inline=False)
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Muestra la tabla de líderes con los usuarios de mayor nivel.")
    async def leaderboard_slash(self, interaction: discord.Interaction) -> None:
        if not await self.config_mgr.is_leveling_enabled(interaction.guild_id):
            await interaction.response.send_message("❌ El sistema de niveles está desactivado en este servidor.", ephemeral=True)
            return

        leaderboard_data = await self.db.get_leaderboard(interaction.guild_id, limit=100)
        
        if not leaderboard_data:
            await interaction.response.send_message("⚠️ Aún no hay usuarios en la tabla de clasificación.", ephemeral=True)
            return

        cfg = self.config_mgr.config.get("leaderboard_command", {})
        items_per_page = cfg.get("items_per_page", 10)

        view = LeaderboardView(
            data=leaderboard_data,
            items_per_page=items_per_page,
            config_mgr=self.config_mgr,
            calculator=self.calculator
        )
        embed = view.create_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="levels", description="Muestra el progreso de niveles de los miembros del servidor.")
    async def levels_slash(self, interaction: discord.Interaction) -> None:
        if not await self.config_mgr.is_leveling_enabled(interaction.guild_id):
            await interaction.response.send_message("❌ El sistema de niveles está desactivado en este servidor.", ephemeral=True)
            return

        cfg = self.config_mgr.config.get("levels_command", {})
        members_per_page = cfg.get("members_per_page", 10)
        staff_only = cfg.get("staff_only", False)

        if staff_only and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Este comando solo está disponible para el staff.", ephemeral=True)
            return

        guild = interaction.guild
        leaderboard_data = await self.db.get_leaderboard(interaction.guild_id, limit=1000)

        filtered = []
        for row in leaderboard_data:
            member = guild.get_member(row["user_id"])
            if member is None or member.bot:
                continue
            filtered.append({
                "member": member,
                "level": row["level"],
                "xp": row["xp"],
                "total_xp_earned": row["total_xp_earned"],
                "total_messages": row["total_messages"]
            })

        if not filtered:
            await interaction.response.send_message("⚠️ No hay usuarios con estadísticas de niveles todavía.", ephemeral=True)
            return

        filtered.sort(key=lambda m: (m["level"], m["total_xp_earned"]), reverse=True)

        view = LevelsView(
            members=filtered,
            items_per_page=members_per_page,
            config_mgr=self.config_mgr,
            calculator=self.calculator,
            author_id=interaction.user.id
        )
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="profile", description="Muestra la tarjeta de perfil completa del usuario.")
    @app_commands.describe(usuario="El usuario del que deseas ver el perfil (opcional).")
    async def profile_slash(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None) -> None:
        target = usuario or interaction.user
        if target.bot:
            await interaction.response.send_message("❌ Los bots no poseen tarjeta de perfil.", ephemeral=True)
            return

        if not await self.config_mgr.is_leveling_enabled(interaction.guild_id):
            await interaction.response.send_message("❌ El sistema de niveles está desactivado en este servidor.", ephemeral=True)
            return

        user_data = await self.db.get_user(interaction.guild_id, target.id)
        rank, total_users = await self.db.get_user_rank(interaction.guild_id, target.id)
        details = self.calculator.get_progress_details(user_data["xp"])
        progress_bar = LevelCalculator.render_progress_bar(details["percentage"])

        embed = discord.Embed(
            title=f"👤 Perfil de {target.display_name}",
            color=self.config_mgr.get_color("color_primary")
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="⭐ Nivel Actual", value=f"**{user_data['level']}**", inline=True)
        embed.add_field(name="🏆 Posición", value=f"**#{rank}** / `{total_users}`", inline=True)
        embed.add_field(name="💬 Mensajes Contabilizados", value=f"`{user_data['total_messages']:,}`", inline=True)
        embed.add_field(name="🖼️ Multimedia", value=f"`{user_data['total_multimedia']:,}`", inline=True)
        embed.add_field(name="🎙️ Minutos en voz", value=f"`{user_data['total_voice_minutes']:,}`", inline=True)
        embed.add_field(name="✨ Experiencia Actual", value=f"`{details['xp_in_level']:,} / {details['xp_needed_for_next']:,} XP`", inline=False)
        embed.add_field(name="📊 Progreso", value=f"`{progress_bar}` **{details['percentage']}%**", inline=False)
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        await interaction.response.send_message(embed=embed)

    # --- Prefix commands ---
    @commands.command(name="level")
    async def level_prefix(self, ctx: commands.Context, usuario: Optional[discord.Member] = None) -> None:
        target = usuario or ctx.author
        if target.bot:
            await ctx.send("❌ Los bots no acumulan experiencia ni niveles.")
            return

        if not await self.config_mgr.is_leveling_enabled(ctx.guild.id):
            await ctx.send("❌ El sistema de niveles está desactivado en este servidor.")
            return

        user_data = await self.db.get_user(ctx.guild.id, target.id)
        details = self.calculator.get_progress_details(user_data["xp"])
        progress_bar = LevelCalculator.render_progress_bar(details["percentage"])

        embed = discord.Embed(
            title=f"⭐ Nivel de {target.display_name}",
            color=self.config_mgr.get_color("color_primary")
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Nivel Actual", value=f"**{details['level']}**", inline=True)
        embed.add_field(name="XP Acumulada", value=f"`{details['xp_in_level']:,} / {details['xp_needed_for_next']:,} XP`", inline=True)
        embed.add_field(name="Progreso", value=f"`{progress_bar}` **{details['percentage']}%**", inline=False)
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        await ctx.send(embed=embed)

    @commands.command(name="rank")
    async def rank_prefix(self, ctx: commands.Context, usuario: Optional[discord.Member] = None) -> None:
        target = usuario or ctx.author
        if target.bot:
            await ctx.send("❌ Los bots no poseen ranking.")
            return

        if not await self.config_mgr.is_leveling_enabled(ctx.guild.id):
            await ctx.send("❌ El sistema de niveles está desactivado en este servidor.")
            return

        user_data = await self.db.get_user(ctx.guild.id, target.id)
        rank, total_users = await self.db.get_user_rank(ctx.guild.id, target.id)

        embed = discord.Embed(
            title=f"🏆 Posición en el Ranking — {target.display_name}",
            color=self.config_mgr.get_color("color_primary")
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Posición", value=f"**#{rank}** de `{total_users}` usuarios", inline=True)
        embed.add_field(name="Nivel", value=f"**{user_data['level']}**", inline=True)
        embed.add_field(name="XP Total Ganada", value=f"`{user_data['total_xp_earned']:,}` XP", inline=False)
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        await ctx.send(embed=embed)

    @commands.command(name="leaderboard")
    async def leaderboard_prefix(self, ctx: commands.Context) -> None:
        if not await self.config_mgr.is_leveling_enabled(ctx.guild.id):
            await ctx.send("❌ El sistema de niveles está desactivado en este servidor.")
            return

        leaderboard_data = await self.db.get_leaderboard(ctx.guild.id, limit=100)
        
        if not leaderboard_data:
            await ctx.send("⚠️ Aún no hay usuarios en la tabla de clasificación.")
            return

        cfg = self.config_mgr.config.get("leaderboard_command", {})
        items_per_page = cfg.get("items_per_page", 10)

        view = LeaderboardView(
            data=leaderboard_data,
            items_per_page=items_per_page,
            config_mgr=self.config_mgr,
            calculator=self.calculator
        )
        embed = view.create_embed(ctx.guild)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="levels")
    async def levels_prefix(self, ctx: commands.Context) -> None:
        if not await self.config_mgr.is_leveling_enabled(ctx.guild.id):
            await ctx.send("❌ El sistema de niveles está desactivado en este servidor.")
            return

        cfg = self.config_mgr.config.get("levels_command", {})
        members_per_page = cfg.get("members_per_page", 10)
        staff_only = cfg.get("staff_only", False)

        if staff_only and not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Este comando solo está disponible para el staff.")
            return

        guild = ctx.guild
        leaderboard_data = await self.db.get_leaderboard(ctx.guild.id, limit=1000)

        filtered = []
        for row in leaderboard_data:
            member = guild.get_member(row["user_id"])
            if member is None or member.bot:
                continue
            filtered.append({
                "member": member,
                "level": row["level"],
                "xp": row["xp"],
                "total_xp_earned": row["total_xp_earned"],
                "total_messages": row["total_messages"]
            })

        if not filtered:
            await ctx.send("⚠️ No hay usuarios con estadísticas de niveles todavía.")
            return

        filtered.sort(key=lambda m: (m["level"], m["total_xp_earned"]), reverse=True)

        view = LevelsView(
            members=filtered,
            items_per_page=members_per_page,
            config_mgr=self.config_mgr,
            calculator=self.calculator,
            author_id=ctx.author.id
        )
        embed = view.create_embed()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="profile")
    async def profile_prefix(self, ctx: commands.Context, usuario: Optional[discord.Member] = None) -> None:
        target = usuario or ctx.author
        if target.bot:
            await ctx.send("❌ Los bots no poseen tarjeta de perfil.")
            return

        if not await self.config_mgr.is_leveling_enabled(ctx.guild.id):
            await ctx.send("❌ El sistema de niveles está desactivado en este servidor.")
            return

        user_data = await self.db.get_user(ctx.guild.id, target.id)
        rank, total_users = await self.db.get_user_rank(ctx.guild.id, target.id)
        details = self.calculator.get_progress_details(user_data["xp"])
        progress_bar = LevelCalculator.render_progress_bar(details["percentage"])

        embed = discord.Embed(
            title=f"👤 Perfil de {target.display_name}",
            color=self.config_mgr.get_color("color_primary")
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="⭐ Nivel Actual", value=f"**{user_data['level']}**", inline=True)
        embed.add_field(name="🏆 Posición", value=f"**#{rank}** / `{total_users}`", inline=True)
        embed.add_field(name="💬 Mensajes Contabilizados", value=f"`{user_data['total_messages']:,}`", inline=True)
        embed.add_field(name="🖼️ Multimedia", value=f"`{user_data['total_multimedia']:,}`", inline=True)
        embed.add_field(name="🎙️ Minutos en voz", value=f"`{user_data['total_voice_minutes']:,}`", inline=True)
        embed.add_field(name="✨ Experiencia Actual", value=f"`{details['xp_in_level']:,} / {details['xp_needed_for_next']:,} XP`", inline=False)
        embed.add_field(name="📊 Progreso", value=f"`{progress_bar}` **{details['percentage']}%**", inline=False)
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        await ctx.send(embed=embed)
