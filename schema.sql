-- BotPanel SQLite Schema
-- Auto-created by app/models/database.py on first run

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,      -- bcrypt hash
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,               -- Display name
    directory TEXT NOT NULL,          -- Absolute path to bot folder
    startup_file TEXT NOT NULL,       -- e.g. main.py
    startup_command TEXT NOT NULL DEFAULT 'python',  -- e.g. python3
    status TEXT DEFAULT 'stopped',    -- running | stopped
    pid INTEGER,                      -- OS process ID when running
    restart_count INTEGER DEFAULT 0,  -- Total auto-restart count
    auto_restart INTEGER DEFAULT 1,   -- 1=enabled, 0=disabled
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_started DATETIME,
    last_stopped DATETIME,
    uptime_start DATETIME             -- When current run started
);

CREATE TABLE IF NOT EXISTS bot_env (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    key TEXT NOT NULL,                -- e.g. BOT_TOKEN, API_ID
    value TEXT NOT NULL,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE,
    UNIQUE(bot_id, key)               -- One value per key per bot
);

CREATE TABLE IF NOT EXISTS crash_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    crashed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,                      -- Crash reason / description
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    filename TEXT NOT NULL,           -- ZIP filename in /backups/
    size INTEGER DEFAULT 0,           -- File size in bytes
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
);

-- Default admin user (admin / admin123) is inserted on first run
-- Change password immediately in production!
