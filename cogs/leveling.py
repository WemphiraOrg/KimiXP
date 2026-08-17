# KimiXP - Discord Bot
# Copyright (C) 2026 BrunoDevPe
#
# This file is part of KimiXP.
#
# KimiXP is free software licensed under the GNU General Public License v3.0.
# See the LICENSE file in the root directory for more information.

import time
import asyncio
import logging
from typing import Dict, Tuple, Optional, List

import discord
from discord.ext import commands

from database.database import Database
from utils.config import ConfigManager
from utils.leveling import LevelCalculator, AntiSpamFilter

logger = logging.getLogger("KimiBot.Leveling")


class LevelingCog(commands.Cog):
    """
    Cog principal para la recolección de XP, asignación de roles, multimedia y voz.
    Soporta múltiples servidores simultáneamente.
    """

    def __init__(self, bot: commands.Bot, db: Database, config_mgr: ConfigManager):
        self.bot = bot
        self.db = db
        self.config_mgr = config_mgr
        
        # Cooldowns en memoria: (guild_id, user_id) -> timestamp_ultimo_xp
        self.cooldowns: Dict[Tuple[int, int], float] = {}

    @property
    def calculator(self) -> LevelCalculator:
        formula_cfg = self.config_mgr.config.get("formula", {})
        return LevelCalculator(
            base_multiplier=formula_cfg.get("base_multiplier", 50.0),
            linear_increment=formula_cfg.get("linear_increment", 100.0)
        )

    def _is_channel_allowed(self, channel: discord.TextChannel) -> bool:
        """Comprueba si el canal está autorizado para otorgar XP."""
        cfg_channels = self.config_mgr.config.get("channels", {})
        ignored = [int(cid) for cid in cfg_channels.get("ignored_channels", []) if str(cid).isdigit()]
        allowed = [int(cid) for cid in cfg_channels.get("leveling", []) if str(cid).isdigit()]

        if channel.id in ignored:
            return False

        if not allowed:
            return True

        return channel.id in allowed

    async def _assign_level_roles(self, member: discord.Member, new_level: int) -> None:
        """Verifica y asigna roles correspondientes al nivel del usuario respetando jerarquias."""
        if not member.guild:
            return
            
        level_roles = await self.db.get_level_roles(member.guild.id)
        remove_previous = await self.config_mgr.get_guild_setting(member.guild.id, "remove_previous_roles", False)
        
        bot_member = member.guild.me
        if not bot_member.guild_permissions.manage_roles:
            logger.warning("No se pueden gestionar roles en '%s': Permiso 'manage_roles' ausente.", member.guild.name)
            return

        roles_to_add: List[discord.Role] = []
        roles_to_remove: List[discord.Role] = []

        sorted_levels = sorted([int(lvl) for lvl in level_roles.keys()])

        for lvl in sorted_levels:
            role_id = level_roles.get(str(lvl))
            if not role_id:
                continue

            role = member.guild.get_role(int(role_id))
            if not role:
                logger.warning("Rol con ID %s no encontrado en el servidor %s.", role_id, member.guild.name)
                continue

            if role.position >= bot_member.top_role.position:
                logger.warning("No se puede asignar el rol '%s' (ID %s): Posición jerárquica superior al bot.", role.name, role.id)
                continue

            if new_level >= lvl:
                if remove_previous and lvl < max([l for l in sorted_levels if new_level >= l], default=lvl):
                    if role in member.roles:
                        roles_to_remove.append(role)
                else:
                    if role not in member.roles:
                        roles_to_add.append(role)

        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Recompensa de sistema de niveles")
                logger.info("Roles asignados a %s: %s", member.display_name, [r.name for r in roles_to_add])
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Limpieza de roles de nivel anterior")
        except discord.HTTPException as e:
            logger.error("Error asignando roles a %s: %s", member.display_name, e)

    async def _send_level_up_notice(self, member: discord.Member, new_level: int, xp: int, message: Optional[discord.Message] = None, guild: Optional[discord.Guild] = None, template_key: str = "level_up", **template_kwargs) -> None:
        cfg_channels = self.config_mgr.config.get("channels", {})
        level_up_channel_id = cfg_channels.get("level_up_channel", "")
        
        target_channel = None
        if level_up_channel_id and str(level_up_channel_id).isdigit():
            g = guild or (message.guild if message else None)
            if g:
                target_channel = g.get_channel(int(level_up_channel_id))
        
        if not target_channel or not isinstance(target_channel, discord.TextChannel):
            target_channel = message.channel if message else None
        
        if not target_channel:
            return

        template_kwargs.setdefault("user", member.mention)
        template_kwargs.setdefault("username", member.display_name)
        template_kwargs.setdefault("level", new_level)
        template_kwargs.setdefault("xp", xp)
        
        msg_template = self.config_mgr.get_msg(template_key, **template_kwargs)

        embed = discord.Embed(
            description=msg_template,
            color=self.config_mgr.get_color("color_success")
        )
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        try:
            await target_channel.send(embed=embed)
        except discord.HTTPException:
            logger.warning("No se pudo enviar embed de level up en el canal ID %s", target_channel.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Manejador principal de mensajes para otorgar XP en tiempo real."""
        if message.author.bot or not message.guild:
            return

        if not await self.config_mgr.is_leveling_enabled(message.guild.id):
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        if not self._is_channel_allowed(message.channel):
            return

        if AntiSpamFilter.is_spam(message.content):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = time.time()

        # Determinar tipo de XP
        xp_type = "message"
        if message.attachments or message.embeds:
            xp_type = "multimedia"

        xp_amount = await self.config_mgr.get_xp_amount(guild_id, xp_type)

        cooldown_seconds = await self.config_mgr.get_guild_setting(guild_id, "message_cooldown", 45)
        last_time = self.cooldowns.get((guild_id, user_id), 0.0)
        if now - last_time < cooldown_seconds:
            return

        await self.db.update_channel_cursor(guild_id, message.channel.id, message.id)

        user_data = await self.db.get_user(guild_id, user_id)
        current_xp = user_data["xp"] + xp_amount
        old_level = user_data["level"]
        new_level = self.calculator.get_level_from_xp(current_xp)

        increment_multimedia = (xp_type == "multimedia")

        await self.db.update_user_xp(
            guild_id=guild_id,
            user_id=user_id,
            added_xp=xp_amount,
            new_level=new_level,
            timestamp=now,
            increment_message=True,
            increment_multimedia=increment_multimedia
        )

        self.cooldowns[(guild_id, user_id)] = now

        if new_level > old_level:
            logger.info("¡%s ha subido al nivel %d en %s!", message.author.display_name, new_level, message.guild.name)
            
            if isinstance(message.author, discord.Member):
                await self._assign_level_roles(message.author, new_level)

            await self._send_level_up_notice(message.author, new_level, current_xp, message=message)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Maneja eventos de voz para otorgar XP por actividad."""
        if member.bot:
            return

        if not member.guild:
            return

        if not await self.config_mgr.is_leveling_enabled(member.guild.id):
            return

        # Ignorar canales AFK
        if after.channel and after.channel.afk:
            await self.db.remove_voice_session(member.guild.id, member.id)
            return

        # Usuario se conectó a un canal de voz
        if after.channel and not before.channel:
            # Verificar que hay al menos otro humano en el canal
            human_count = sum(1 for m in after.channel.members if not m.bot)
            if human_count < 2:
                return
            
            interval_minutes = await self.config_mgr.get_guild_setting(member.guild.id, "voice_interval_minutes", 10)
            await self.db.upsert_voice_session(
                member.guild.id,
                member.id,
                after.channel.id,
                time.time(),
                time.time()
            )
            logger.debug("Usuario %s conectado a voz en %s", member.display_name, member.guild.name)

        # Usuario se desconectó de un canal de voz
        elif before.channel and not after.channel:
            session = await self.db.get_voice_session(member.guild.id, member.id)
            if session:
                await self.db.remove_voice_session(member.guild.id, member.id)
                logger.debug("Usuario %s desconectado de voz en %s", member.display_name, member.guild.name)

        # Usuario cambió de canal de voz
        elif before.channel != after.channel and after.channel:
            if after.channel.afk:
                await self.db.remove_voice_session(member.guild.id, member.id)
                return
            
            human_count = sum(1 for m in after.channel.members if not m.bot)
            if human_count < 2:
                await self.db.remove_voice_session(member.guild.id, member.id)
                return
            
            await self.db.upsert_voice_session(
                member.guild.id,
                member.id,
                after.channel.id,
                time.time(),
                time.time()
            )

    async def _process_voice_xp(self, guild_id: int) -> None:
        """Procesa XP por voz para todos los usuarios activos en un servidor."""
        if not await self.config_mgr.is_leveling_enabled(guild_id):
            return

        voice_xp = await self.config_mgr.get_xp_amount(guild_id, "voice")
        interval_minutes = await self.config_mgr.get_guild_setting(guild_id, "voice_interval_minutes", 10)
        interval_seconds = interval_minutes * 60

        sessions = await self.db.get_active_voice_sessions(guild_id)
        now = time.time()

        for session in sessions:
            user_id = session["user_id"]
            last_xp_at = session["last_xp_at"]
            
            if now - last_xp_at >= interval_seconds:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue
                
                member = guild.get_member(user_id)
                if not member or member.bot:
                    await self.db.remove_voice_session(guild_id, user_id)
                    continue
                
                # Verificar que sigue en un canal de voz válido
                if not member.voice or not member.voice.channel or member.voice.channel.afk:
                    await self.db.remove_voice_session(guild_id, user_id)
                    continue
                
                # Verificar que hay al menos otro humano
                human_count = sum(1 for m in member.voice.channel.members if not m.bot)
                if human_count < 2:
                    await self.db.remove_voice_session(guild_id, user_id)
                    continue

                user_data = await self.db.get_user(guild_id, user_id)
                current_xp = user_data["xp"] + voice_xp
                old_level = user_data["level"]
                new_level = self.calculator.get_level_from_xp(current_xp)

                await self.db.update_user_xp(
                    guild_id=guild_id,
                    user_id=user_id,
                    added_xp=voice_xp,
                    new_level=new_level,
                    timestamp=now,
                    increment_message=False,
                    voice_minutes=interval_minutes
                )

                await self.db.upsert_voice_session(guild_id, user_id, session["channel_id"], session["joined_at"], now)

                if new_level > old_level:
                    await self._assign_level_roles(member, new_level)
                    await self._send_level_up_notice(member, new_level, current_xp, guild=guild)

                logger.debug("XP de voz otorgada a %s en %s: +%d XP", member.display_name, guild.name, voice_xp)

    async def scan_guild_history(self, guild, xp_min: int, xp_max: int, max_xp_per_user: int, max_msgs_per_user: int, batch_size: int = 200, max_run_messages: int = 10000) -> Dict[str, int]:
        user_recovery_msgs: Dict[int, int] = {}
        user_recovery_xp: Dict[int, int] = {}
        user_initial_levels: Dict[int, int] = {}
        total_processed_messages = 0
        channels_scanned = 0
        channels_skipped = 0

        for channel in guild.text_channels:
            if not self._is_channel_allowed(channel):
                channels_skipped += 1
                continue

            perms = channel.permissions_for(guild.me)
            if not perms.read_messages or not perms.read_message_history:
                logger.warning("Sin permisos para leer historial en #%s", channel.name)
                channels_skipped += 1
                continue

            channels_scanned += 1
            last_msg_id = await self.db.get_channel_cursor(guild.id, channel.id)
            if not last_msg_id:
                try:
                    async for msg in channel.history(limit=1):
                        await self.db.update_channel_cursor(guild.id, channel.id, msg.id)
                except discord.HTTPException:
                    pass
                continue

            after_object = discord.Object(id=last_msg_id)
            latest_safe_msg_id = last_msg_id
            batch_count = 0

            try:
                async for message in channel.history(limit=batch_size, after=after_object, oldest_first=True):
                    if total_processed_messages >= max_run_messages:
                        break

                    if message.author.bot or AntiSpamFilter.is_spam(message.content):
                        continue

                    u_id = message.author.id
                    curr_msgs = user_recovery_msgs.get(u_id, 0)
                    curr_xp = user_recovery_xp.get(u_id, 0)

                    if curr_msgs >= max_msgs_per_user or curr_xp >= max_xp_per_user:
                        continue

                    xp_type = "message"
                    if message.attachments or message.embeds:
                        xp_type = "multimedia"

                    gained = await self.config_mgr.get_xp_amount(guild.id, xp_type)
                    if curr_xp + gained > max_xp_per_user:
                        gained = max_xp_per_user - curr_xp

                    if gained > 0:
                        if u_id not in user_initial_levels:
                            user_db = await self.db.get_user(guild.id, u_id)
                            user_initial_levels[u_id] = user_db["level"]

                        user_recovery_msgs[u_id] = curr_msgs + 1
                        user_recovery_xp[u_id] = curr_xp + gained
                        total_processed_messages += 1
                        latest_safe_msg_id = message.id
                        batch_count += 1

                if latest_safe_msg_id != last_msg_id:
                    await self.db.update_channel_cursor(guild.id, channel.id, latest_safe_msg_id)

            except discord.HTTPException as e:
                logger.warning("Error leyendo historial en #%s: %s", channel.name, e)

        levels_up = 0
        for u_id, gained_xp in user_recovery_xp.items():
            user_db = await self.db.get_user(guild.id, u_id)
            new_xp = user_db["xp"] + gained_xp
            old_lvl = user_initial_levels.get(u_id, user_db["level"])
            new_lvl = self.calculator.get_level_from_xp(new_xp)

            await self.db.update_user_xp(
                guild_id=guild.id,
                user_id=u_id,
                added_xp=gained_xp,
                new_level=new_lvl,
                timestamp=time.time(),
                increment_message=True
            )

            member = guild.get_member(u_id)
            if member and new_lvl > old_lvl:
                await self._assign_level_roles(member, new_lvl)
                
                template_key = "level_up_multi" if new_lvl - old_lvl > 1 else "level_up"
                await self._send_level_up_notice(
                    member, new_lvl, new_xp,
                    guild=guild,
                    template_key=template_key,
                    old_level=old_lvl
                )
                levels_up += 1

        return {
            "processed_messages": total_processed_messages,
            "users_updated": len(user_recovery_xp),
            "levels_up": levels_up,
            "channels_scanned": channels_scanned,
            "channels_skipped": channels_skipped
        }

    async def recover_downtime_activity(self) -> None:
        """Lee e incrementa XP de los mensajes enviados mientras el bot estuvo fuera de servicio."""
        recovery_cfg = self.config_mgr.config.get("recovery", {})
        if not recovery_cfg.get("enabled", True):
            logger.info("Recuperación de actividad en apagado desactivada en la configuración.")
            return

        logger.info("Iniciando escaneo y recuperación de actividad durante el apagado...")
        max_xp_per_user = recovery_cfg.get("max_xp_per_user", 500)
        max_msgs_per_user = recovery_cfg.get("max_messages_per_user", 50)

        total_processed_messages = 0
        total_users_updated = 0
        total_levels_up = 0

        for guild in self.bot.guilds:
            if not await self.config_mgr.is_leveling_enabled(guild.id):
                continue

            batch_size = await self.config_mgr.get_guild_setting(guild.id, "recovery_batch_size", 200)
            max_run_messages = await self.config_mgr.get_guild_setting(guild.id, "recovery_max_run_messages", 10000)
            xp_min = await self.config_mgr.get_xp_amount(guild.id, "message")
            xp_max = xp_min

            stats = await self.scan_guild_history(guild, xp_min, xp_max, max_xp_per_user, max_msgs_per_user, batch_size=batch_size, max_run_messages=max_run_messages)
            total_processed_messages += stats["processed_messages"]
            total_users_updated += stats["users_updated"]
            total_levels_up += stats["levels_up"]

        logger.info("Recuperación completada. Mensajes: %d | Usuarios: %d | Subidas de nivel: %d", total_processed_messages, total_users_updated, total_levels_up)

    async def start_voice_task(self) -> None:
        """Inicia la tarea periódica de XP por voz."""
        if not hasattr(self, '_voice_task_started'):
            self._voice_task_started = True
            self.bot.loop.create_task(self._voice_loop())

    async def _voice_loop(self) -> None:
        """Loop periódico para procesar XP por voz."""
        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    if await self.config_mgr.is_leveling_enabled(guild.id):
                        await self._process_voice_xp(guild.id)
            except Exception as e:
                logger.error("Error en loop de voz: %s", e, exc_info=True)
            
            await asyncio.sleep(60)  # Verificar cada minuto
