from datetime import datetime, timedelta
import os
from jose import jwt
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import Session

from shadowgate_api.db import Base, get_db
from shadowgate_api.auth_simple import hash_password, verify_password

router = APIRouter(prefix="/api", tags=["Users"])

# --- Auth config ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24h

def _make_token(sub: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": sub, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# --- ORM model ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    ingame_username = Column(String, nullable=False)
    company_code = Column(String, nullable=True)
    fio_apikey = Column(String, nullable=True)
    bases = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Schemas ---
class RegisterIn(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=3)  # shorter minimum if you prefer
    ingame_username: str
    company_code: str | None = None
    fio_apikey: str | None = None

class LoginIn(BaseModel):
    username: str
    password: str

class AuthOut(BaseModel):
    token: str
    role: str

# --- Helpers ---
def _get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

# --- Endpoints ---
@router.post("/register", response_model=AuthOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if _get_user_by_username(db, body.username):
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        ingame_username=body.ingame_username,
        company_code=body.company_code,
        fio_apikey=body.fio_apikey,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _make_token(user.username, user.role)
    return {"token": token, "role": user.role}

@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = _get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _make_token(user.username, user.role)
    return {"token": token, "role": user.role}
