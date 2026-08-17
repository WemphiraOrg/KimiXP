-- Servidores donde KimiXP está instalado
CREATE TABLE IF NOT EXISTS guilds (
    guild_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Configuración por servidor con valores predeterminados
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    leveling_enabled INTEGER DEFAULT 1,
    xp_message INTEGER DEFAULT 20,
    xp_multimedia INTEGER DEFAULT 25,
    xp_voice INTEGER DEFAULT 10,
    voice_interval_minutes INTEGER DEFAULT 10,
    message_cooldown INTEGER DEFAULT 45,
    max_recovery_xp INTEGER DEFAULT 500,
    max_recovery_messages INTEGER DEFAULT 50,
    recovery_batch_size INTEGER DEFAULT 200,
    recovery_max_run_messages INTEGER DEFAULT 10000,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Tabla principal de usuarios por servidor
CREATE TABLE IF NOT EXISTS users (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    total_messages INTEGER DEFAULT 0,
    total_multimedia INTEGER DEFAULT 0,
    total_voice_minutes INTEGER DEFAULT 0,
    total_xp_earned INTEGER DEFAULT 0,
    last_xp_timestamp REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Roles automáticos por nivel por servidor
CREATE TABLE IF NOT EXISTS level_roles (
    guild_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, level),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Seguimiento de mensajes procesados por canal (para recuperación)
CREATE TABLE IF NOT EXISTS channel_cursors (
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    last_processed_message_id INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, channel_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Sesiones de voz activas para otorgar XP por intervalo
CREATE TABLE IF NOT EXISTS voice_sessions (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    joined_at REAL NOT NULL,
    last_xp_at REAL NOT NULL,
    PRIMARY KEY (guild_id, user_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_users_guild_xp ON users(guild_id, total_xp_earned DESC);
CREATE INDEX IF NOT EXISTS idx_users_guild_level ON users(guild_id, level DESC);
CREATE INDEX IF NOT EXISTS idx_users_updated ON users(guild_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_channel_cursors_guild ON channel_cursors(guild_id);
CREATE INDEX IF NOT EXISTS idx_level_roles_guild ON level_roles(guild_id);
CREATE INDEX IF NOT EXISTS idx_guild_settings_guild ON guild_settings(guild_id);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_guild_user ON voice_sessions(guild_id, user_id);
