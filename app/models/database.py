import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database" / "panel.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            directory TEXT NOT NULL,
            startup_file TEXT NOT NULL,
            startup_command TEXT NOT NULL DEFAULT 'python',
            status TEXT DEFAULT 'stopped',
            pid INTEGER,
            restart_count INTEGER DEFAULT 0,
            auto_restart INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_started DATETIME,
            last_stopped DATETIME,
            uptime_start DATETIME
        );

        CREATE TABLE IF NOT EXISTS bot_env (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE,
            UNIQUE(bot_id, key)
        );

        CREATE TABLE IF NOT EXISTS crash_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            crashed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reason TEXT,
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            size INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
        );
    """)

    # Default admin user: admin / admin123
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    try:
        c.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", pwd_ctx.hash("admin123"))
        )
    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()
