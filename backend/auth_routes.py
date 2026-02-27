"""Authentication API routes."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.database import get_db, hash_password, verify_password, log_usage
from backend.auth import create_token, get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    invite_code: str


class InviteCodeCreate(BaseModel):
    count: int = 1


# --- Public endpoints ---

@router.post("/login")
async def login(req: LoginRequest):
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, password_hash, password_salt, is_admin FROM users WHERE username = ?",
            (req.username,),
        ).fetchone()
    if not user or not verify_password(req.password, user["password_hash"], user["password_salt"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_token(user["id"], user["username"], bool(user["is_admin"]))
    return {
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "is_admin": bool(user["is_admin"])},
    }


@router.post("/register")
async def register(req: RegisterRequest):
    with get_db() as conn:
        code_row = conn.execute(
            "SELECT id FROM invite_codes WHERE code = ? AND used_by IS NULL",
            (req.invite_code,),
        ).fetchone()
        if not code_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or used invite code")

        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (req.username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

        pw_hash, salt = hash_password(req.password)
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, password_salt) VALUES (?, ?, ?)",
            (req.username, pw_hash, salt),
        )
        user_id = cur.lastrowid
        conn.execute(
            "UPDATE invite_codes SET used_by = ?, used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id, code_row["id"]),
        )

    token = create_token(user_id, req.username, False)
    return {
        "token": token,
        "user": {"id": user_id, "username": req.username, "is_admin": False},
    }


# --- Authenticated endpoints ---

@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# --- Admin endpoints ---

@router.post("/invite-codes")
async def create_invite_codes(req: InviteCodeCreate, admin: dict = Depends(require_admin)):
    codes = []
    with get_db() as conn:
        for _ in range(min(req.count, 20)):
            code = secrets.token_urlsafe(8)
            conn.execute(
                "INSERT INTO invite_codes (code, created_by) VALUES (?, ?)",
                (code, admin["id"]),
            )
            codes.append(code)
    return {"codes": codes}


@router.get("/invite-codes")
async def list_invite_codes(admin: dict = Depends(require_admin)):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT ic.id, ic.code, ic.created_at,
                   creator.username AS created_by,
                   user.username AS used_by, ic.used_at
            FROM invite_codes ic
            LEFT JOIN users creator ON ic.created_by = creator.id
            LEFT JOIN users user ON ic.used_by = user.id
            ORDER BY ic.created_at DESC
        """).fetchall()
    return [dict(r) for r in rows]


@router.get("/usage")
async def usage_stats(admin: dict = Depends(require_admin)):
    with get_db() as conn:
        stats = conn.execute("""
            SELECT u.username, ul.endpoint, ul.model,
                   COUNT(*) as count,
                   MIN(ul.timestamp) as first_use,
                   MAX(ul.timestamp) as last_use
            FROM usage_log ul
            JOIN users u ON ul.user_id = u.id
            GROUP BY u.username, ul.endpoint, ul.model
            ORDER BY u.username, count DESC
        """).fetchall()
    return [dict(r) for r in stats]
