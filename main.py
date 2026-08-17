# KimiXP - Discord Bot
# Copyright (C) 2026 BrunoDevPe
#
# This file is part of KimiXP.
#
# KimiXP is free software licensed under the GNU General Public License v3.0.
# See the LICENSE file in the root directory for more information.

import os
import sys
import asyncio
import signal
import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database.database import Database
from utils.config import ConfigManager, ConfigError
from utils.logging import setup_logging

from cogs.leveling import LevelingCog
from cogs.profile import ProfileCog
from cogs.admin import AdminCog
from cogs.help import HelpCog

# Cargar variables de entorno desde .env
load_dotenv()

class KimiLevelBot(commands.Bot):
    """Clase principal del bot para Botlevel."""

    def __init__(self, config_mgr: ConfigManager, db: Database):
        prefix = config_mgr.config.get("prefix", {}).get("default", "!")
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=prefix,
            intents=intents,
            help_command=None
        )

        self.config_mgr = config_mgr
        self.db = db
        self.is_shutting_down = False

    async def setup_hook(self) -> None:
        """Inicializa componentes, cogs y sincroniza slash commands."""
        await self.db.initialize()

        # Registrar Cogs
        await self.add_cog(LevelingCog(self, self.db, self.config_mgr))
        await self.add_cog(ProfileCog(self, self.db, self.config_mgr))
        await self.add_cog(AdminCog(self, self.db, self.config_mgr))
        await self.add_cog(HelpCog(self, self.config_mgr))

        # Iniciar tarea de voz
        leveling_cog = self.get_cog("LevelingCog")
        if leveling_cog:
            await leveling_cog.start_voice_task()

        # Sincronizar slash commands globalmente
        try:
            synced = await self.tree.sync()
            logging.getLogger("KimiBot").info("Sincronizados %d comandos globalmente.", len(synced))
        except Exception as e:
            logging.getLogger("KimiBot").error("Error sincronizando comandos: %s", e)

    async def on_ready(self) -> None:
        """Evento ejecutado cuando el bot se conecta satisfactoriamente a Discord."""
        logger = logging.getLogger("KimiBot")
        logger.info("Bot conectado exitosamente como %s (ID: %s)", self.user, self.user.id)

        # Registrar todos los servidores actuales
        for guild in self.guilds:
            await self.db.get_or_create_guild(guild.id, guild.name)
            await self.db.update_guild(guild.id, guild.name)
            logger.info("Servidor registrado: %s (ID: %s)", guild.name, guild.id)

        # Iniciar tarea de voz si no está iniciada
        leveling_cog = self.get_cog("LevelingCog")
        if leveling_cog:
            await leveling_cog.start_voice_task()

        # Ejecutar recuperación de mensajes si está habilitado
        if leveling_cog:
            await leveling_cog.recover_downtime_activity()

        # Notificar reactivación en canal de anuncios si está configurado
        await self._send_system_notice(
            title_key="system_resumed_title",
            desc_key="system_resumed_desc",
            color_key="color_success"
        )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Registra automáticamente un nuevo servidor cuando el bot se une."""
        logger = logging.getLogger("KimiBot")
        await self.db.get_or_create_guild(guild.id, guild.name)
        logger.info("Nuevo servidor detectado: %s (ID: %s)", guild.name, guild.id)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        """Actualiza el nombre del servidor si cambia."""
        if before.name != after.name:
            await self.db.update_guild(after.id, after.name)

    async def _send_system_notice(self, title_key: str, desc_key: str, color_key: str) -> None:
        """Envía una notificación embed al canal de anuncios definido en config.json."""
        ann_id = self.config_mgr.config.get("channels", {}).get("announcement")
        if not ann_id or not str(ann_id).isdigit():
            return

        channel = self.get_channel(int(ann_id))
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        title = self.config_mgr.get_msg(title_key)
        desc = self.config_mgr.get_msg(desc_key)
        color = self.config_mgr.get_color(color_key)

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text=self.config_mgr.config.get("embeds", {}).get("footer_text", ""))

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            logging.getLogger("KimiBot").warning("No se pudo enviar notificación de sistema a canal %s: %s", ann_id, e)

    async def graceful_shutdown(self) -> None:
        """Procedimiento de apagado limpio (Ctrl+C / SIGTERM)."""
        if self.is_shutting_down:
            return
        self.is_shutting_down = True

        logger = logging.getLogger("KimiBot")
        logger.info("Iniciando apagado controlado del bot...")

        # Enviar mensaje de suspensión al servidor si Discord sigue conectado
        if not self.is_closed():
            await self._send_system_notice(
                title_key="system_suspended_title",
                desc_key="system_suspended_desc",
                color_key="color_warning"
            )
            await self.close()

        logger.info("Apagado finalizado. Todos los recursos fueron liberados.")


def main():
    # Cargar y validar configuración externa
    try:
        config_mgr = ConfigManager()
        config_mgr.load()
    except ConfigError as e:
        print(f"\n❌ ERROR FATAL DE CONFIGURACIÓN:\n{e}\n", file=sys.stderr)
        sys.exit(1)

    # Configurar sistema de logs
    debug_mode = config_mgr.config.get("development", {}).get("debug", False)
    logger = setup_logging(debug=debug_mode)

    # Validar Token de Discord
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "tu_token_aqui":
        logger.critical("El token de Discord no está configurado en el archivo .env")
        sys.exit(1)

    # Instanciar Base de Datos y Bot
    db = Database()
    config_mgr.db = db
    bot = KimiLevelBot(config_mgr=config_mgr, db=db)

    # Captura de señales de interrupción (Ctrl + C / SIGINT / SIGTERM)
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Interrupción detectada (SIGINT/Ctrl+C). Executando graceful shutdown...")
        asyncio.create_task(bot.graceful_shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Para entornos donde add_signal_handler no esté soportado (Windows)
            pass

    try:
        loop.run_until_complete(bot.start(token))
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt recibido.")
    finally:
        if not bot.is_closed():
            loop.run_until_complete(bot.graceful_shutdown())


if __name__ == "__main__":
    main()
