# KimiXP - Discord Bot
# Copyright (C) 2026 BrunoDevPe
#
# This file is part of KimiXP.
#
# KimiXP is free software licensed under the GNU General Public License v3.0.
# See the LICENSE file in the root directory for more information.

import os
import shutil
import sqlite3
import asyncio
import logging
import datetime
from typing import Optional, Dict, Any, List, Tuple
import time 
logger = logging.getLogger("KimiBot.Database")


class Database:
    """
    Gestor de base de datos SQLite asíncrono para Botlevel.
    Soporta múltiples servidores con configuración por guild.
    """

    def __init__(self, db_path: str = "data/bot.db", schema_path: str = "database/schema.sql"):
        self.db_path = db_path
        self.schema_path = schema_path
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Asegura que el directorio data/ exista."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Crea y retorna una conexión a SQLite con dict rows."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    async def initialize(self) -> None:
        """Inicializa la base de datos ejecutando el esquema SQL y migra datos antiguos."""
        def _init_sync():
            if not os.path.exists(self.schema_path):
                raise FileNotFoundError(f"Esquema SQL no encontrado en {self.schema_path}")
            
            with open(self.schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            with self._get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
                
                # Migrar datos antiguos si existen
                self._migrate_legacy_data(conn)

        await asyncio.to_thread(_init_sync)
        logger.info("Base de datos SQLite inicializada correctamente (%s).", self.db_path)

    def _migrate_legacy_data(self, conn: sqlite3.Connection) -> None:
        """Migra datos del schema antiguo al nuevo si es necesario."""
        cursor = conn.cursor()
        
        # Verificar si existe la tabla users con guild_id
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            return
            
        # Migrar datos de usuarios existentes a la tabla users actual
        # (ya tienen guild_id, así que solo necesitamos asegurar que los guilds existen)
        cursor.execute("SELECT DISTINCT guild_id FROM users WHERE guild_id IS NOT NULL")
        guild_ids = [row[0] for row in cursor.fetchall()]
        
        for guild_id in guild_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO guilds (guild_id, name, joined_at, updated_at) VALUES (?, ?, ?, ?)",
                (guild_id, f"Guild {guild_id}", time.time(), time.time())
            )
            cursor.execute(
                "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
                (guild_id,)
            )
        
        # Migrar level_roles desde config si existe la tabla
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='level_roles'")
        if cursor.fetchone():
            cursor.execute("SELECT DISTINCT guild_id FROM level_roles WHERE guild_id IS NOT NULL")
            role_guild_ids = [row[0] for row in cursor.fetchall()]
            for guild_id in role_guild_ids:
                cursor.execute(
                    "INSERT OR IGNORE INTO guilds (guild_id, name, joined_at, updated_at) VALUES (?, ?, ?, ?)",
                    (guild_id, f"Guild {guild_id}", time.time(), time.time())
                )
                cursor.execute(
                    "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
                    (guild_id,)
                )
        
        conn.commit()

    # --- Guilds ---
    async def get_or_create_guild(self, guild_id: int, name: str) -> Dict[str, Any]:
        """Obtiene o crea un servidor en la base de datos."""
        def _query():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM guilds WHERE guild_id = ?",
                    (guild_id,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                cursor.execute(
                    "INSERT INTO guilds (guild_id, name, joined_at, updated_at) VALUES (?, ?, ?, ?)",
                    (guild_id, name, time.time(), time.time())
                )
                conn.commit()
                
                # Crear configuración por defecto
                cursor.execute(
                    "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
                    (guild_id,)
                )
                conn.commit()
                
                cursor.execute("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,))
                return dict(cursor.fetchone())

        return await asyncio.to_thread(_query)

    async def update_guild(self, guild_id: int, name: str) -> None:
        """Actualiza información básica de un servidor."""
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE guilds SET name = ?, updated_at = ? WHERE guild_id = ?",
                    (name, time.time(), guild_id)
                )
                conn.commit()
        await asyncio.to_thread(_update)

    # --- Guild Settings ---
    async def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Obtiene la configuración de un servidor, creando defaults si no existe."""
        def _query():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM guild_settings WHERE guild_id = ?",
                    (guild_id,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                # Crear configuración por defecto
                cursor.execute(
                    "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
                    (guild_id,)
                )
                conn.commit()
                cursor.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
                return dict(cursor.fetchone())

        return await asyncio.to_thread(_query)

    async def get_guild_config_summary(self, guild_id: int) -> Dict[str, Any]:
        """Obtiene un resumen de la configuración efectiva de un servidor."""
        settings = await self.get_guild_settings(guild_id)
        return {
            "xp_message": settings.get("xp_message", 20),
            "xp_multimedia": settings.get("xp_multimedia", 25),
            "xp_voice": settings.get("xp_voice", 10),
            "voice_interval_minutes": settings.get("voice_interval_minutes", 10),
            "message_cooldown": settings.get("message_cooldown", 45),
            "max_recovery_xp": settings.get("max_recovery_xp", 500),
            "max_recovery_messages": settings.get("max_recovery_messages", 50),
            "recovery_batch_size": settings.get("recovery_batch_size", 200),
            "recovery_max_run_messages": settings.get("recovery_max_run_messages", 10000),
            "leveling_enabled": bool(settings.get("leveling_enabled", 1)),
        }

    async def update_guild_setting(self, guild_id: int, key: str, value: Any) -> None:
        """Actualiza una configuración específica de un servidor."""
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE guild_settings SET {key} = ?, updated_at = ? WHERE guild_id = ?",
                    (value, time.time(), guild_id)
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        f"INSERT INTO guild_settings (guild_id, {key}) VALUES (?, ?)",
                        (guild_id, value)
                    )
                conn.commit()
        await asyncio.to_thread(_update)

    # --- Users ---
    async def get_user(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Obtiene o crea los datos de un usuario en un servidor especifico."""
        def _query():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                # Crear nuevo registro si no existe
                cursor.execute(
                    """
                    INSERT INTO users (guild_id, user_id, xp, level, total_messages, total_multimedia, total_voice_minutes, total_xp_earned, last_xp_timestamp)
                    VALUES (?, ?, 0, 1, 0, 0, 0, 0, 0.0)
                    """,
                    (guild_id, user_id)
                )
                conn.commit()
                
                cursor.execute(
                    "SELECT * FROM users WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id)
                )
                return dict(cursor.fetchone())

        return await asyncio.to_thread(_query)

    async def update_user_xp(
        self,
        guild_id: int,
        user_id: int,
        added_xp: int,
        new_level: int,
        timestamp: float,
        increment_message: bool = True,
        increment_multimedia: bool = False,
        voice_minutes: int = 0
    ) -> Dict[str, Any]:
        """Actualiza los puntos de XP, nivel y estadísticas de un usuario."""
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                msg_inc = 1 if increment_message else 0
                multimedia_inc = 1 if increment_multimedia else 0
                voice_inc = voice_minutes
                
                cursor.execute(
                    """
                    UPDATE users
                    SET xp = xp + ?,
                        total_xp_earned = total_xp_earned + ?,
                        level = ?,
                        total_messages = total_messages + ?,
                        total_multimedia = total_multimedia + ?,
                        total_voice_minutes = total_voice_minutes + ?,
                        last_xp_timestamp = ?,
                        updated_at = ?
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (added_xp, added_xp, new_level, msg_inc, multimedia_inc, voice_inc, timestamp, time.time(), guild_id, user_id)
                )
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                return dict(cursor.fetchone())

        return await asyncio.to_thread(_update)

    async def set_user_level_and_xp(self, guild_id: int, user_id: int, level: int, xp: int) -> None:
        """Establece directamente el nivel y XP de un usuario."""
        def _set():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users (guild_id, user_id, xp, level, total_messages, total_multimedia, total_voice_minutes, total_xp_earned, last_xp_timestamp)
                    VALUES (?, ?, ?, ?, 0, 0, 0, ?, 0.0)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        xp = excluded.xp,
                        level = excluded.level,
                        total_xp_earned = excluded.xp
                    """,
                    (guild_id, user_id, xp, level, xp)
                )
                conn.commit()

        await asyncio.to_thread(_set)

    async def get_user_rank(self, guild_id: int, user_id: int) -> Tuple[int, int]:
        """Calcula la posición del usuario en la clasificación del servidor."""
        def _rank():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT total_xp_earned FROM users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                user_row = cursor.fetchone()
                if not user_row:
                    return 0, 0
                
                target_xp = user_row["total_xp_earned"]
                
                cursor.execute(
                    "SELECT COUNT(*) as rank FROM users WHERE guild_id = ? AND total_xp_earned > ?",
                    (guild_id, target_xp)
                )
                rank = cursor.fetchone()["rank"] + 1

                cursor.execute("SELECT COUNT(*) as total FROM users WHERE guild_id = ?", (guild_id,))
                total = cursor.fetchone()["total"]

                return rank, total

        return await asyncio.to_thread(_rank)

    async def get_leaderboard(self, guild_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene la lista de los usuarios con mas experiencia acumulada en un servidor."""
        def _leaderboard():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT user_id, xp, level, total_xp_earned, total_messages, total_multimedia, total_voice_minutes
                    FROM users
                    WHERE guild_id = ?
                    ORDER BY total_xp_earned DESC, xp DESC
                    LIMIT ?
                    """,
                    (guild_id, limit)
                )
                return [dict(row) for row in cursor.fetchall()]

        return await asyncio.to_thread(_leaderboard)

    # --- Channel Cursors ---
    async def get_channel_cursor(self, guild_id: int, channel_id: int) -> Optional[int]:
        """Obtiene el ID del ultimo mensaje procesado en un canal."""
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT last_processed_message_id FROM channel_cursors WHERE guild_id = ? AND channel_id = ?",
                    (guild_id, channel_id)
                )
                row = cursor.fetchone()
                return row["last_processed_message_id"] if row else None

        return await asyncio.to_thread(_get)

    async def update_channel_cursor(self, guild_id: int, channel_id: int, message_id: int) -> None:
        """Actualiza el puntero del ultimo mensaje procesado en un canal."""
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO channel_cursors (guild_id, channel_id, last_processed_message_id, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(guild_id, channel_id) DO UPDATE SET
                        last_processed_message_id = excluded.last_processed_message_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (guild_id, channel_id, message_id)
                )
                conn.commit()

        await asyncio.to_thread(_update)

    # --- Level Roles ---
    async def get_level_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """Obtiene los roles automáticos por nivel de un servidor."""
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT level, role_id FROM level_roles WHERE guild_id = ? ORDER BY level ASC",
                    (guild_id,)
                )
                return [dict(row) for row in cursor.fetchall()]

        return await asyncio.to_thread(_get)

    async def set_level_role(self, guild_id: int, level: int, role_id: int) -> None:
        """Establece un rol automático por nivel."""
        def _set():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, level) DO UPDATE SET role_id = excluded.role_id
                    """,
                    (guild_id, level, role_id)
                )
                conn.commit()

        await asyncio.to_thread(_set)

    async def remove_level_role(self, guild_id: int, level: int) -> None:
        """Elimina un rol automático por nivel."""
        def _remove():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM level_roles WHERE guild_id = ? AND level = ?",
                    (guild_id, level)
                )
                conn.commit()

        await asyncio.to_thread(_remove)

    # --- Voice Sessions ---
    async def get_voice_session(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene la sesión de voz activa de un usuario."""
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM voice_sessions WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id)
                )
                row = cursor.fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_get)

    async def upsert_voice_session(self, guild_id: int, user_id: int, channel_id: int, joined_at: float, last_xp_at: float) -> None:
        """Crea o actualiza una sesión de voz."""
        def _upsert():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO voice_sessions (guild_id, user_id, channel_id, joined_at, last_xp_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        channel_id = excluded.channel_id,
                        joined_at = excluded.joined_at,
                        last_xp_at = excluded.last_xp_at
                    """,
                    (guild_id, user_id, channel_id, joined_at, last_xp_at)
                )
                conn.commit()

        await asyncio.to_thread(_upsert)

    async def remove_voice_session(self, guild_id: int, user_id: int) -> None:
        """Elimina una sesión de voz."""
        def _remove():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM voice_sessions WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id)
                )
                conn.commit()

        await asyncio.to_thread(_remove)

    async def get_active_voice_sessions(self, guild_id: int) -> List[Dict[str, Any]]:
        """Obtiene todas las sesiones de voz activas de un servidor."""
        def _get():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM voice_sessions WHERE guild_id = ?",
                    (guild_id,)
                )
                return [dict(row) for row in cursor.fetchall()]

        return await asyncio.to_thread(_get)

    async def update_guild_setting(self, guild_id: int, key: str, value: Any) -> None:
        """Actualiza una configuración específica de un servidor."""
        def _update():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE guild_settings SET {key} = ?, updated_at = ? WHERE guild_id = ?",
                    (value, time.time(), guild_id)
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        f"INSERT INTO guild_settings (guild_id, {key}) VALUES (?, ?)",
                        (guild_id, value)
                    )
                conn.commit()

        await asyncio.to_thread(_update)

    async def backup_database(self) -> str:
        """Crea una copia de seguridad de la base de datos y retorna la ruta del archivo."""
        def _backup():
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Base de datos no encontrada en {self.db_path}")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}"
            shutil.copy2(self.db_path, backup_path)
            return backup_path
        return await asyncio.to_thread(_backup)

    async def reset_guild_stats(self, guild_id: int) -> int:
        """Reinicia las estadísticas de todos los usuarios de un servidor. Retorna filas afectadas."""
        def _reset():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users
                    SET xp = 0,
                        level = 1,
                        total_messages = 0,
                        total_multimedia = 0,
                        total_voice_minutes = 0,
                        total_xp_earned = 0,
                        last_xp_timestamp = 0.0,
                        updated_at = ?
                    WHERE guild_id = ?
                    """,
                    (time.time(), guild_id)
                )
                conn.commit()
                return cursor.rowcount
        return await asyncio.to_thread(_reset)

    async def reset_channel_cursors(self, guild_id: int) -> None:
        """Elimina los cursores de canal de un servidor para permitir reprocesamiento completo."""
        def _reset():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM channel_cursors WHERE guild_id = ?", (guild_id,))
                conn.commit()
        await asyncio.to_thread(_reset)
