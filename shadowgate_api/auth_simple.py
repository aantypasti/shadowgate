# shadowgate_api/auth_simple.py
import hashlib
import secrets
import os
from types import SimpleNamespace
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError           # pip install python-jose
from sqlalchemy import text
from sqlalchemy.orm import Session

# --- existing helpers (kept) ---
def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()
    return f"{salt}${h}"

def verify_password(pw: str, stored: str) -> bool:
    try:
        salt, good = stored.split("$", 1)
    except ValueError:
        return False
    h = hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()
    return secrets.compare_digest(h, good)

# --- NEW: JWT auth dependency ---
# Must match whatever you used to SIGN the token when logging in / registering
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
bearer = HTTPBearer(auto_error=False)

def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from e

def _load_user(db: Session, username: str) -> SimpleNamespace:
    row = db.execute(
        text("SELECT id, username, role, bases FROM users WHERE username = :u LIMIT 1"),
        {"u": username},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    # return an object with attributes like .id, .username, .role, .bases
    return SimpleNamespace(**row)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(lambda: __import__("shadowgate_api.db", fromlist=["get_db"]).db.SessionLocal()),
):
    """
    FastAPI dependency:
    - Reads Bearer token
    - Decodes JWT (expects payload with 'sub' = username, optional 'role')
    - Loads user from DB and returns a SimpleNamespace with id/username/role/bases
    """
    if not creds or not creds.scheme.lower() == "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = _decode_token(creds.credentials)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token missing 'sub'")
    return _load_user(db, username)
