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

from database.database import Database
from utils.config import ConfigManager
from utils.leveling import LevelCalculator

logger = logging.getLogger("KimiBot.Admin")


class AdminCog(commands.Cog):
    """Cog para comandos administrativos de gestión del sistema de niveles."""

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
    @app_commands.command(name="admin_add_xp", description="Añade experiencia manualmente a un usuario.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(usuario="Usuario al que otorgar XP", cantidad="Cantidad de XP a añadir")
    async def add_xp_slash(self, interaction: discord.Interaction, usuario: discord.Member, cantidad: int) -> None:
        if not await self.config_mgr.is_leveling_enabled(interaction.guild_id):
            await interaction.response.send_message("❌ El sistema de niveles está desactivado en este servidor.", ephemeral=True)
            return

        if cantidad <= 0:
            await interaction.response.send_message("❌ La cantidad debe ser mayor que 0.", ephemeral=True)
            return

        user_data = await self.db.get_user(interaction.guild_id, usuario.id)
        new_xp = user_data["xp"] + cantidad
        new_level = self.calculator.get_level_from_xp(new_xp)

        await self.db.update_user_xp(
            guild_id=interaction.guild_id,
            user_id=usuario.id,
            added_xp=cantidad,
            new_level=new_level,
            timestamp=interaction.created_at.timestamp(),
            increment_message=False
        )

        embed = discord.Embed(
            title="✅ Experiencia Añadida",
            description=f"Se han otorgado `{cantidad:,} XP` a {usuario.mention}.\nNuevo nivel: **{new_level}**",
            color=self.config_mgr.get_color("color_success")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_set_level", description="Establece el nivel directo de un usuario.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(usuario="Usuario a modificar", nivel="Nuevo nivel a establecer")
    async def set_level_slash(self, interaction: discord.Interaction, usuario: discord.Member, nivel: int) -> None:
        if not await self.config_mgr.is_leveling_enabled(interaction.guild_id):
            await interaction.response.send_message("❌ El sistema de niveles está desactivado en este servidor.", ephemeral=True)
            return

        if nivel < 1:
            await interaction.response.send_message("❌ El nivel mínimo permitido es 1.", ephemeral=True)
            return

        required_xp = self.calculator.get_xp_for_level(nivel)
        await self.db.set_user_level_and_xp(interaction.guild_id, usuario.id, nivel, required_xp)

        embed = discord.Embed(
            title="✅ Nivel Actualizado",
            description=f"El nivel de {usuario.mention} ha sido establecido en **{nivel}** (`{required_xp:,} XP`).",
            color=self.config_mgr.get_color("color_success")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_sync", description="Fuerza la sincronización de comandos slash.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_slash(self, interaction: discord.Interaction) -> None:
        try:
            synced = await self.bot.tree.sync(guild=discord.Object(id=interaction.guild_id))
            await interaction.response.send_message(
                f"✅ Sincronizados **{len(synced)}** comandos para este servidor.", ephemeral=True
            )
            logger.info("Sync forzado por %s: %d comandos.", interaction.user.id, len(synced))
        except Exception as e:
            await interaction.response.send_message(f"❌ Error en sincronización: {e}", ephemeral=True)

    @app_commands.command(name="admin_reload_config", description="Recarga la configuración y mensajes desde los archivos JSON.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_slash(self, interaction: discord.Interaction) -> None:
        try:
            self.config_mgr.load()
            msg = self.config_mgr.get_msg("config_reloaded")
            await interaction.response.send_message(msg, ephemeral=True)
            logger.info("Configuración y mensajes recargados mediante comando administrativo.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error recargando configuración: {e}", ephemeral=True)

    @app_commands.command(name="admin_set_xp", description="Configura la cantidad de XP por tipo de actividad para este servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(tipo="Tipo de actividad", cantidad="Cantidad de XP")
    async def set_xp_slash(self, interaction: discord.Interaction, tipo: str, cantidad: int) -> None:
        tipo = tipo.lower().strip()
        valid_types = {"message", "multimedia", "voice"}
        if tipo not in valid_types:
            await interaction.response.send_message(
                f"❌ Tipo inválido. Usa: {', '.join(valid_types)}",
                ephemeral=True
            )
            return

        if cantidad <= 0:
            await interaction.response.send_message("❌ La cantidad debe ser mayor que 0.", ephemeral=True)
            return

        db_key = f"xp_{tipo}"
        await self.db.update_guild_setting(interaction.guild_id, db_key, cantidad)
        
        tipo_label = {"message": "mensaje", "multimedia": "multimedia", "voice": "voz"}.get(tipo, tipo)
        await interaction.response.send_message(
            f"✅ XP por **{tipo_label}** establecida en `{cantidad}` para este servidor.",
            ephemeral=True
        )
        logger.info("XP %s establecida a %d en servidor %s por %s", tipo, cantidad, interaction.guild_id, interaction.user.id)

    @app_commands.command(name="admin_set_voice_interval", description="Configura el intervalo de XP por voz en minutos.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(minutos="Minutos entre cada otorgamiento de XP de voz")
    async def set_voice_interval_slash(self, interaction: discord.Interaction, minutos: int) -> None:
        if minutos <= 0:
            await interaction.response.send_message("❌ Los minutos deben ser mayor que 0.", ephemeral=True)
            return

        await self.db.update_guild_setting(interaction.guild_id, "voice_interval_minutes", minutos)
        await interaction.response.send_message(
            f"✅ Intervalo de XP por voz establecido en **{minutos}** minutos para este servidor.",
            ephemeral=True
        )

    # --- Prefix commands ---
    @commands.command(name="admin_add_xp")
    @commands.has_permissions(administrator=True)
    async def add_xp_prefix(self, ctx: commands.Context, usuario: discord.Member, cantidad: int) -> None:
        if not await self.config_mgr.is_leveling_enabled(ctx.guild.id):
            await ctx.send("❌ El sistema de niveles está desactivado en este servidor.")
            return

        if cantidad <= 0:
            await ctx.send("❌ La cantidad debe ser mayor que 0.")
            return

        user_data = await self.db.get_user(ctx.guild.id, usuario.id)
        new_xp = user_data["xp"] + cantidad
        new_level = self.calculator.get_level_from_xp(new_xp)

        await self.db.update_user_xp(
            guild_id=ctx.guild.id,
            user_id=usuario.id,
            added_xp=cantidad,
            new_level=new_level,
            timestamp=ctx.message.created_at.timestamp(),
            increment_message=False
        )

        embed = discord.Embed(
            title="✅ Experiencia Añadida",
            description=f"Se han otorgado `{cantidad:,} XP` a {usuario.mention}.\nNuevo nivel: **{new_level}**",
            color=self.config_mgr.get_color("color_success")
        )
        await ctx.send(embed=embed)

    @commands.command(name="admin_set_level")
    @commands.has_permissions(administrator=True)
    async def set_level_prefix(self, ctx: commands.Context, usuario: discord.Member, nivel: int) -> None:
        if not await self.config_mgr.is_leveling_enabled(ctx.guild.id):
            await ctx.send("❌ El sistema de niveles está desactivado en este servidor.")
            return

        if nivel < 1:
            await ctx.send("❌ El nivel mínimo permitido es 1.")
            return

        required_xp = self.calculator.get_xp_for_level(nivel)
        await self.db.set_user_level_and_xp(ctx.guild.id, usuario.id, nivel, required_xp)

        embed = discord.Embed(
            title="✅ Nivel Actualizado",
            description=f"El nivel de {usuario.mention} ha sido establecido en **{nivel}** (`{required_xp:,} XP`).",
            color=self.config_mgr.get_color("color_success")
        )
        await ctx.send(embed=embed)

    @commands.command(name="admin_sync")
    @commands.has_permissions(administrator=True)
    async def sync_prefix(self, ctx: commands.Context) -> None:
        try:
            synced = await ctx.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
            await ctx.send(f"✅ Sincronizados **{len(synced)}** comandos para este servidor.")
            logger.info("Sync forzado por %s: %d comandos.", ctx.author.id, len(synced))
        except Exception as e:
            await ctx.send(f"❌ Error en sincronización: {e}")

    @commands.command(name="admin_reload_config")
    @commands.has_permissions(administrator=True)
    async def reload_prefix(self, ctx: commands.Context) -> None:
        try:
            self.config_mgr.load()
            msg = self.config_mgr.get_msg("config_reloaded")
            await ctx.send(msg)
            logger.info("Configuración y mensajes recargados mediante comando administrativo.")
        except Exception as e:
            await ctx.send(f"❌ Error recargando configuración: {e}")

    @commands.command(name="admin_set_xp")
    @commands.has_permissions(administrator=True)
    async def set_xp_prefix(self, ctx: commands.Context, tipo: str, cantidad: int) -> None:
        tipo = tipo.lower().strip()
        valid_types = {"message", "multimedia", "voice"}
        if tipo not in valid_types:
            await ctx.send(f"❌ Tipo inválido. Usa: {', '.join(valid_types)}")
            return

        if cantidad <= 0:
            await ctx.send("❌ La cantidad debe ser mayor que 0.")
            return

        db_key = f"xp_{tipo}"
        await self.db.update_guild_setting(ctx.guild.id, db_key, cantidad)
        
        tipo_label = {"message": "mensaje", "multimedia": "multimedia", "voice": "voz"}.get(tipo, tipo)
        await ctx.send(f"✅ XP por **{tipo_label}** establecida en `{cantidad}` para este servidor.")

    @commands.command(name="admin_set_voice_interval")
    @commands.has_permissions(administrator=True)
    async def set_voice_interval_prefix(self, ctx: commands.Context, minutos: int) -> None:
        if minutos <= 0:
            await ctx.send("❌ Los minutos deben ser mayor que 0.")
            return

        await self.db.update_guild_setting(ctx.guild.id, "voice_interval_minutes", minutos)
        await ctx.send(f"✅ Intervalo de XP por voz establecido en **{minutos}** minutos para este servidor.")

    # --- Reset ---
    class ResetConfirmView(discord.ui.View):
        def __init__(self, author_id, callback):
            super().__init__(timeout=60)
            self.author_id = author_id
            self.callback = callback

        @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("❌ No puedes controlar este menú.", ephemeral=True)
                return
            await interaction.response.edit_message(view=None)
            await self.callback()

        @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("❌ No puedes controlar este menú.", ephemeral=True)
                return
            await interaction.response.edit_message(content="❌ Reset cancelado.", embed=None, view=None)

    async def _execute_reset(self, guild, author):
        cfg = self.config_mgr.config.get("reset_command", {})
        backup_path = None

        try:
            if cfg.get("backup_enabled", True):
                backup_path = await self.db.backup_database()
                logger.info("Backup creado en %s", backup_path)

            if cfg.get("reset_xp", True) or cfg.get("reset_levels", True) or cfg.get("reset_messages", True):
                affected = await self.db.reset_guild_stats(guild.id)
                logger.info("Stats reiniciadas por %s: %d filas afectadas.", author.id, affected)

            if cfg.get("reset_cursors", False):
                await self.db.reset_channel_cursors(guild.id)
                logger.info("Cursosres reiniciados por %s.", author.id)

            logger.info("Reset completado por %s (%s) en %s", author.id, author, guild.name)
            return backup_path, affected

        except Exception as e:
            logger.error("Error durante el reset: %s", e, exc_info=True)
            raise

    @app_commands.command(name="reset", description="Reinicia los datos de niveles y actividad del servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_slash(self, interaction: discord.Interaction) -> None:
        cfg = self.config_mgr.config.get("reset_command", {})
        if cfg.get("staff_only", True) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Este comando solo está disponible para el staff.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚠️ Confirmar Reset",
            description="Esta acción reiniciara **XP, niveles y estadisticas** de todos los miembros.\nSe creara una copia de seguridad automatica antes de continuar.",
            color=self.config_mgr.get_color("color_warning")
        )
        embed.set_footer(text="Esta accion no se puede deshacer.")

        async def do_reset():
            try:
                backup_path, affected = await self._execute_reset(interaction.guild, interaction.user)
                desc = f"✅ Reset completado.\nFilas afectadas: **{affected}**"
                if backup_path:
                    desc += f"\nBackup: `{backup_path}`"
                await interaction.edit_original_response(content=None, embed=discord.Embed(title="✅ Reset Completado", description=desc, color=self.config_mgr.get_color("color_success")))
            except Exception as e:
                await interaction.edit_original_response(content=None, embed=discord.Embed(title="❌ Error", description=str(e), color=self.config_mgr.get_color("color_danger")))

        view = AdminCog.ResetConfirmView(interaction.user.id, do_reset)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset_prefix(self, ctx: commands.Context) -> None:
        cfg = self.config_mgr.config.get("reset_command", {})
        if cfg.get("staff_only", True) and not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Este comando solo está disponible para el staff.")
            return

        embed = discord.Embed(
            title="⚠️ Confirmar Reset",
            description="Esta acción reiniciara **XP, niveles y estadisticas** de todos los miembros.\nSe creara una copia de seguridad automatica antes de continuar.",
            color=self.config_mgr.get_color("color_warning")
        )
        embed.set_footer(text="Esta accion no se puede deshacer.")

        async def do_reset():
            try:
                backup_path, affected = await self._execute_reset(ctx.guild, ctx.author)
                desc = f"✅ Reset completado.\nFilas afectadas: **{affected}**"
                if backup_path:
                    desc += f"\nBackup: `{backup_path}`"
                await ctx.send(embed=discord.Embed(title="✅ Reset Completado", description=desc, color=self.config_mgr.get_color("color_success")))
            except Exception as e:
                await ctx.send(embed=discord.Embed(title="❌ Error", description=str(e), color=self.config_mgr.get_color("color_danger")))

        view = AdminCog.ResetConfirmView(ctx.author.id, do_reset)
        await ctx.send(embed=embed, view=view)

    # --- Recuperar ---
    @app_commands.command(name="recuperar", description="Analiza el historial y actualiza las estadisticas de niveles.")
    async def recover_slash(self, interaction: discord.Interaction) -> None:
        cfg = self.config_mgr.config.get("recover_command", {})
        max_xp_per_user = cfg.get("max_xp_per_user", 500)
        max_msgs_per_user = cfg.get("max_messages_per_user", 50)
        xp_min = await self.config_mgr.get_xp_amount(interaction.guild_id, "message")
        xp_max = xp_min
        staff_only = cfg.get("staff_only", False)

        if staff_only and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Este comando solo está disponible para el staff.", ephemeral=True)
            return

        leveling_cog = self.bot.get_cog("LevelingCog")
        if not leveling_cog:
            await interaction.response.send_message("❌ Error interno: LevelingCog no encontrado.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            stats = await leveling_cog.scan_guild_history(interaction.guild, xp_min, xp_max, max_xp_per_user, max_msgs_per_user)
            embed = discord.Embed(
                title="✅ Recuperacion Completada",
                description=(
                    f"Mensajes procesados: **{stats['processed_messages']:,}**\n"
                    f"Usuarios actualizados: **{stats['users_updated']:,}**\n"
                    f"Subidas de nivel: **{stats['levels_up']:,}**"
                ),
                color=self.config_mgr.get_color("color_success")
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info("Recuperacion manual ejecutada por %s: %d mensajes, %d usuarios, %d niveles.", interaction.user.id, stats['processed_messages'], stats['users_updated'], stats['levels_up'])
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(title="❌ Error", description=str(e), color=self.config_mgr.get_color("color_danger")), ephemeral=True)
            logger.error("Error en recuperacion manual: %s", e, exc_info=True)

    @commands.command(name="recuperar")
    async def recover_prefix(self, ctx: commands.Context) -> None:
        cfg = self.config_mgr.config.get("recover_command", {})
        max_xp_per_user = cfg.get("max_xp_per_user", 500)
        max_msgs_per_user = cfg.get("max_messages_per_user", 50)
        xp_min = await self.config_mgr.get_xp_amount(ctx.guild.id, "message")
        xp_max = xp_min
        staff_only = cfg.get("staff_only", False)

        if staff_only and not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Este comando solo está disponible para el staff.")
            return

        leveling_cog = self.bot.get_cog("LevelingCog")
        if not leveling_cog:
            await ctx.send("❌ Error interno: LevelingCog no encontrado.")
            return

        msg = await ctx.send("⏳ Procesando historial...")

        try:
            stats = await leveling_cog.scan_guild_history(ctx.guild, xp_min, xp_max, max_xp_per_user, max_msgs_per_user)
            embed = discord.Embed(
                title="✅ Recuperacion Completada",
                description=(
                    f"Mensajes procesados: **{stats['processed_messages']:,}**\n"
                    f"Usuarios actualizados: **{stats['users_updated']:,}**\n"
                    f"Subidas de nivel: **{stats['levels_up']:,}**"
                ),
                color=self.config_mgr.get_color("color_success")
            )
            await msg.edit(content=None, embed=embed)
            logger.info("Recuperacion manual ejecutada por %s: %d mensajes, %d usuarios, %d niveles.", ctx.author.id, stats['processed_messages'], stats['users_updated'], stats['levels_up'])
        except Exception as e:
            await msg.edit(content=None, embed=discord.Embed(title="❌ Error", description=str(e), color=self.config_mgr.get_color("color_danger")))
            logger.error("Error en recuperacion manual: %s", e, exc_info=True)

    @app_commands.command(name="admin_config", description="Muestra o modifica la configuración del servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        seccion="Sección de configuración (xp, voice, recovery, system)",
        clave="Clave a modificar (opcional)",
        valor="Nuevo valor (opcional)"
    )
    async def admin_config_slash(self, interaction: discord.Interaction, seccion: str = "view", clave: str = "", valor: str = "") -> None:
        guild_id = interaction.guild_id
        seccion = seccion.lower().strip()

        if seccion == "view" or not clave:
            summary = await self.db.get_guild_config_summary(guild_id)
            embed = discord.Embed(
                title="⚙️ Configuración del Servidor",
                color=self.config_mgr.get_color("color_primary")
            )
            embed.add_field(name="💬 XP Mensaje", value=f"`{summary['xp_message']}`", inline=True)
            embed.add_field(name="🖼️ XP Multimedia", value=f"`{summary['xp_multimedia']}`", inline=True)
            embed.add_field(name="🎙️ XP Voz", value=f"`{summary['xp_voice']}` / `{summary['voice_interval_minutes']}` min", inline=True)
            embed.add_field(name="⏱️ Cooldown", value=f"`{summary['message_cooldown']}` seg", inline=True)
            embed.add_field(name="📦 Recuperación", value=f"`{summary['max_recovery_messages']}` msgs / `{summary['max_recovery_xp']}` XP", inline=True)
            embed.add_field(name="🔁 Batch", value=f"`{summary['recovery_batch_size']}` msgs / `{summary['recovery_max_run_messages']}` max", inline=True)
            embed.add_field(name="✅ Estado", value=f"Leveling: **{'Activado' if summary['leveling_enabled'] else 'Desactivado'}**", inline=False)
            embed.set_footer(text="Usa /admin_config para modificar valores")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        valid_sections = {
            "xp": ["message", "multimedia", "voice"],
            "voice": ["interval"],
            "recovery": ["max_user_messages", "max_user_xp", "batch_size", "max_run_messages"],
            "system": ["cooldown"]
        }

        if seccion not in valid_sections:
            await interaction.response.send_message(f"❌ Sección inválida. Usa: {', '.join(valid_sections.keys())}", ephemeral=True)
            return

        if clave not in valid_sections[seccion]:
            await interaction.response.send_message(f"❌ Clave inválida para '{seccion}'. Usa: {', '.join(valid_sections[seccion])}", ephemeral=True)
            return

        if not valor:
            await interaction.response.send_message("❌ Debes proporcionar un valor numérico.", ephemeral=True)
            return

        try:
            num_val = int(valor)
            if num_val <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ El valor debe ser un número entero mayor que 0.", ephemeral=True)
            return

        db_key_map = {
            "message": "xp_message",
            "multimedia": "xp_multimedia",
            "voice": "xp_voice",
            "interval": "voice_interval_minutes",
            "max_user_messages": "max_recovery_messages",
            "max_user_xp": "max_recovery_xp",
            "batch_size": "recovery_batch_size",
            "max_run_messages": "recovery_max_run_messages",
            "cooldown": "message_cooldown"
        }

        db_key = db_key_map.get(clave)
        if not db_key:
            await interaction.response.send_message("❌ Configuración no reconocida.", ephemeral=True)
            return

        await self.db.update_guild_setting(guild_id, db_key, num_val)
        
        label_map = {
            "message": "XP por mensaje",
            "multimedia": "XP por multimedia",
            "voice": "XP por voz",
            "interval": "Intervalo de voz (min)",
            "max_user_messages": "Máx mensajes recuperación",
            "max_user_xp": "Máx XP recuperación",
            "batch_size": "Batch size",
            "max_run_messages": "Máx mensajes por ejecución",
            "cooldown": "Cooldown (seg)"
        }
        
        await interaction.response.send_message(
            f"✅ **{label_map.get(clave, clave)}** establecido en `{num_val}` para este servidor.",
            ephemeral=True
        )
        logger.info("Config %s = %d actualizada en servidor %s por %s", db_key, num_val, guild_id, interaction.user.id)

    @commands.command(name="admin_config")
    async def admin_config_prefix(self, ctx: commands.Context, seccion: str = "view", clave: str = "", valor: str = "") -> None:
        guild_id = ctx.guild.id
        seccion = seccion.lower().strip()

        if seccion == "view" or not clave:
            summary = await self.db.get_guild_config_summary(guild_id)
            embed = discord.Embed(
                title="⚙️ Configuración del Servidor",
                color=self.config_mgr.get_color("color_primary")
            )
            embed.add_field(name="💬 XP Mensaje", value=f"`{summary['xp_message']}`", inline=True)
            embed.add_field(name="🖼️ XP Multimedia", value=f"`{summary['xp_multimedia']}`", inline=True)
            embed.add_field(name="🎙️ XP Voz", value=f"`{summary['xp_voice']}` / `{summary['voice_interval_minutes']}` min", inline=True)
            embed.add_field(name="⏱️ Cooldown", value=f"`{summary['message_cooldown']}` seg", inline=True)
            embed.add_field(name="📦 Recuperación", value=f"`{summary['max_recovery_messages']}` msgs / `{summary['max_recovery_xp']}` XP", inline=True)
            embed.add_field(name="🔁 Batch", value=f"`{summary['recovery_batch_size']}` msgs / `{summary['recovery_max_run_messages']}` max", inline=True)
            embed.add_field(name="✅ Estado", value=f"Leveling: **{'Activado' if summary['leveling_enabled'] else 'Desactivado'}**", inline=False)
            embed.set_footer(text="Usa !admin_config para modificar valores")
            await ctx.send(embed=embed)
            return

        valid_sections = {
            "xp": ["message", "multimedia", "voice"],
            "voice": ["interval"],
            "recovery": ["max_user_messages", "max_user_xp", "batch_size", "max_run_messages"],
            "system": ["cooldown"]
        }

        if seccion not in valid_sections:
            await ctx.send(f"❌ Sección inválida. Usa: {', '.join(valid_sections.keys())}")
            return

        if clave not in valid_sections[seccion]:
            await ctx.send(f"❌ Clave inválida para '{seccion}'. Usa: {', '.join(valid_sections[seccion])}")
            return

        if not valor:
            await ctx.send("❌ Debes proporcionar un valor numérico.")
            return

        try:
            num_val = int(valor)
            if num_val <= 0:
                raise ValueError
        except ValueError:
            await ctx.send("❌ El valor debe ser un número entero mayor que 0.")
            return

        db_key_map = {
            "message": "xp_message",
            "multimedia": "xp_multimedia",
            "voice": "xp_voice",
            "interval": "voice_interval_minutes",
            "max_user_messages": "max_recovery_messages",
            "max_user_xp": "max_recovery_xp",
            "batch_size": "recovery_batch_size",
            "max_run_messages": "recovery_max_run_messages",
            "cooldown": "message_cooldown"
        }

        db_key = db_key_map.get(clave)
        if not db_key:
            await ctx.send("❌ Configuración no reconocida.")
            return

        await self.db.update_guild_setting(guild_id, db_key, num_val)
        
        label_map = {
            "message": "XP por mensaje",
            "multimedia": "XP por multimedia",
            "voice": "XP por voz",
            "interval": "Intervalo de voz (min)",
            "max_user_messages": "Máx mensajes recuperación",
            "max_user_xp": "Máx XP recuperación",
            "batch_size": "Batch size",
            "max_run_messages": "Máx mensajes por ejecución",
            "cooldown": "Cooldown (seg)"
        }
        
        await ctx.send(f"✅ **{label_map.get(clave, clave)}** establecido en `{num_val}` para este servidor.")
