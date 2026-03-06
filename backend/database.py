"""SQLite database for user auth and usage tracking."""
import json
import os
import sqlite3
import hashlib
import secrets
import threading
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gemintern.db"
))

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return dk.hex(), salt.hex()


def verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return dk.hex() == stored_hash


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS invite_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                created_by INTEGER,
                used_by INTEGER NULL,
                used_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL,
                model TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                settings_json TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

    # Bootstrap admin user from env vars
    admin_user = os.environ.get("ADMIN_USERNAME")
    admin_pass = os.environ.get("ADMIN_PASSWORD")
    if admin_user and admin_pass:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?", (admin_user,)
            ).fetchone()
            pw_hash, salt = hash_password(admin_pass)
            if not existing:
                conn.execute(
                    "INSERT INTO users (username, password_hash, password_salt, is_admin) VALUES (?, ?, ?, 1)",
                    (admin_user, pw_hash, salt),
                )
                print(f"[DB] Admin user '{admin_user}' created.")
            else:
                conn.execute(
                    "UPDATE users SET password_hash = ?, password_salt = ?, is_admin = 1 WHERE username = ?",
                    (pw_hash, salt, admin_user),
                )
                print(f"[DB] Admin user '{admin_user}' password updated.")


def log_usage(user_id: int, endpoint: str, model: str | None = None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO usage_log (user_id, endpoint, model) VALUES (?, ?, ?)",
            (user_id, endpoint, model),
        )


def get_user_settings(user_id: int) -> dict:
    """Load per-user settings from DB."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT settings_json FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row:
        try:
            return json.loads(row["settings_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def save_user_settings(user_id: int, settings: dict):
    """Save per-user settings to DB."""
    settings_json = json.dumps(settings, ensure_ascii=False)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO user_settings (user_id, settings_json)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET settings_json = ?""",
            (user_id, settings_json, settings_json),
        )
