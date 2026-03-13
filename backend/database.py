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

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                storage_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id),
                UNIQUE(owner_id, name)
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                folder TEXT DEFAULT '__root__',
                filename TEXT NOT NULL,
                parsed_text TEXT,
                size INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, folder, filename)
            );

            CREATE TABLE IF NOT EXISTS generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL,
                title TEXT DEFAULT '',
                model TEXT,
                inputs_json TEXT,
                result_text TEXT,
                status TEXT DEFAULT 'complete',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS qa_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT DEFAULT '새 대화',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS qa_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES qa_sessions(id) ON DELETE CASCADE
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

    # Bootstrap invite codes from env var (comma-separated)
    init_codes = os.environ.get("INIT_INVITE_CODES", "")
    if init_codes:
        with get_db() as conn:
            for code in init_codes.split(","):
                code = code.strip()
                if not code:
                    continue
                existing = conn.execute(
                    "SELECT id FROM invite_codes WHERE code = ?", (code,)
                ).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO invite_codes (code, created_by) VALUES (?, 1)",
                        (code,),
                    )
                    print(f"[DB] Invite code '{code}' bootstrapped.")

    # Migrate existing rag_storage projects to SQLite
    migrate_rag_projects_to_db()


def migrate_rag_projects_to_db():
    """One-time migration: rag_storage/_projects.json → SQLite projects table."""
    rag_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag_storage")
    projects_file = os.path.join(rag_root, "_projects.json")
    if not os.path.exists(projects_file):
        return
    try:
        with open(projects_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    migrated = 0
    with get_db() as conn:
        for p in data.get("projects", []):
            owner_id = p.get("owner_id")
            if owner_id is None:
                owner_id = 1
            existing = conn.execute(
                "SELECT id FROM projects WHERE name = ? AND owner_id = ?",
                (p["name"], owner_id)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO projects (name, owner_id, storage_name, created_at) VALUES (?, ?, ?, ?)",
                    (p["name"], owner_id, p.get("storage_name", p["name"]),
                     p.get("created", "2026-01-01T00:00:00"))
                )
                migrated += 1
    if migrated:
        print(f"[DB] Migrated {migrated} projects from rag_storage to SQLite.")


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


def save_generation(user_id: int, endpoint: str, title: str,
                    model: str | None, inputs: dict | None,
                    result_text: str, status: str = "complete") -> int:
    """생성 작업 결과를 이력에 저장하고 ID를 반환한다."""
    inputs_json = json.dumps(inputs, ensure_ascii=False) if inputs else None
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO generation_history
               (user_id, endpoint, title, model, inputs_json, result_text, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, endpoint, title, model, inputs_json, result_text, status),
        )
        return cur.lastrowid


def list_generations(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    """사용자의 생성 이력을 최신순으로 반환한다."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, endpoint, title, model, status, created_at
               FROM generation_history
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def get_generation(gen_id: int, user_id: int) -> dict | None:
    """특정 생성 이력의 상세 정보를 반환한다."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, endpoint, title, model, inputs_json, result_text, status, created_at
               FROM generation_history
               WHERE id = ? AND user_id = ?""",
            (gen_id, user_id),
        ).fetchone()
    if row:
        d = dict(row)
        if d.get("inputs_json"):
            try:
                d["inputs"] = json.loads(d["inputs_json"])
            except (json.JSONDecodeError, TypeError):
                d["inputs"] = None
        else:
            d["inputs"] = None
        del d["inputs_json"]
        return d
    return None


def delete_generation(gen_id: int, user_id: int) -> bool:
    """생성 이력 삭제."""
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM generation_history WHERE id = ? AND user_id = ?",
            (gen_id, user_id),
        )
        return cur.rowcount > 0


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
