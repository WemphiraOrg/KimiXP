# KimiXP - Discord Bot
# Copyright (C) 2026 BrunoDevPe
#
# This file is part of KimiXP.
#
# KimiXP is free software licensed under the GNU General Public License v3.0.
# See the LICENSE file in the root directory for more information.

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("kimi_bot.config")


class ConfigError(Exception):
    """Excepción personalizada para errores de validación de configuración."""
    pass


class ConfigManager:
    """Cargador y validador central de la configuración del bot."""

    def __init__(self, config_path: str = "config/config.json", messages_path: str = "config/messages.json", db=None):
        self.config_path = config_path
        self.messages_path = messages_path
        self.config: Dict[str, Any] = {}
        self.messages: Dict[str, Any] = {}
        self.db = db
        self.load()

    def load(self) -> None:
        """Carga y valida los archivos JSON."""
        self.config = self._load_json(self.config_path)
        self.messages = self._load_json(self.messages_path)
        self.validate()

    def _load_json(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise ConfigError(f"ERROR: El archivo de configuración '{path}' no existe.")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"ERROR: El archivo '{path}' contiene un JSON inválido -> {e}")

    def validate(self) -> None:
        """Comprueba tipos de datos y parámetros obligatorios."""
        defaults = self.config.get("defaults", {})
        
        # Validar XP por defecto
        xp = defaults.get("xp", {})
        if not isinstance(xp, dict):
            raise ConfigError("ERROR: config.json -> 'defaults.xp' debe ser un objeto.")
        if not isinstance(xp.get("message"), int) or xp.get("message", 0) <= 0:
            raise ConfigError("ERROR: config.json -> 'defaults.xp.message' debe ser un entero mayor que 0.")
        if not isinstance(xp.get("multimedia"), int) or xp.get("multimedia", 0) <= 0:
            raise ConfigError("ERROR: config.json -> 'defaults.xp.multimedia' debe ser un entero mayor que 0.")
        if not isinstance(xp.get("voice"), int) or xp.get("voice", 0) <= 0:
            raise ConfigError("ERROR: config.json -> 'defaults.xp.voice' debe ser un entero mayor que 0.")

        # Validar voice por defecto
        voice = defaults.get("voice", {})
        if not isinstance(voice, dict):
            raise ConfigError("ERROR: config.json -> 'defaults.voice' debe ser un objeto.")
        if not isinstance(voice.get("interval_minutes"), int) or voice.get("interval_minutes", 0) <= 0:
            raise ConfigError("ERROR: config.json -> 'defaults.voice.interval_minutes' debe ser un entero mayor que 0.")

        logger.info("Configuración cargada y validada correctamente.")

    def get(self, path: str, default: Any = None) -> Any:
        """
        Obtiene un valor anidado del config.json usando notación de puntos.
        Ejemplo: config.get("defaults.xp.message")
        """
        keys = path.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_msg(self, key: str, **kwargs) -> str:
        """
        Obtiene una plantilla de mensaje desde messages.json y reemplaza variables {user}, {level}, etc.
        """
        template = self.messages.get(key, f"[{key}]")
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Falta la variable {e} para formatear el mensaje '{key}'")
            return template

    def get_color(self, key: str) -> int:
        """
        Obtiene un color hexadecimal desde la sección embeds de config.json.
        """
        color_str = self.config.get("embeds", {}).get(key, "0x5865F2")
        try:
            return int(color_str, 0)
        except (ValueError, TypeError):
            return 0x5865F2

    async def get_guild_setting(self, guild_id: int, key: str, default: Any = None) -> Any:
        """
        Obtiene una configuración específica de un servidor.
        Primero revisa la configuración del servidor en SQLite, luego usa el default global.
        """
        if self.db is None:
            return self.get(f"defaults.{key}", default)
        
        try:
            settings = await self.db.get_guild_settings(guild_id)
            db_key_map = {
                "xp_message": "xp_message",
                "xp_multimedia": "xp_multimedia",
                "xp_voice": "xp_voice",
                "voice_interval_minutes": "voice_interval_minutes",
                "message_cooldown": "message_cooldown",
                "max_recovery_xp": "max_recovery_xp",
                "max_recovery_messages": "max_recovery_messages",
                "leveling_enabled": "leveling_enabled",
            }
            
            db_key = db_key_map.get(key)
            if db_key and db_key in settings and settings[db_key] is not None:
                value = settings[db_key]
                # Convertir booleanos de SQLite (0/1) a Python bool
                if isinstance(value, int) and value in (0, 1):
                    return bool(value)
                return value
        except Exception as e:
            logger.warning("Error obteniendo configuración de guild %s: %s", guild_id, e)
        
        return self.get(f"defaults.{key}", default)

    async def get_xp_amount(self, guild_id: int, xp_type: str) -> int:
        """Obtiene la cantidad de XP para un tipo de actividad en un servidor."""
        return await self.get_guild_setting(guild_id, f"xp.{xp_type}", self.get(f"defaults.xp.{xp_type}", 20))

    async def is_leveling_enabled(self, guild_id: int) -> bool:
        """Verifica si el sistema de niveles está activado en un servidor."""
        return await self.get_guild_setting(guild_id, "leveling_enabled", True)
