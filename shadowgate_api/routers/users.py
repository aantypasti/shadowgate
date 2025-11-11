from datetime import datetime, timedelta
import os

from fastapi import APIRouter, HTTPException, Depends
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import Session

from shadowgate_api.db import Base, get_db

router = APIRouter(prefix="/api", tags=["Users"])

# --- Auth config ---
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24h

def _hash(pw: str) -> str:
    return pwd_ctx.hash(pw)

def _verify(pw: str, pw_hash: str) -> bool:
    return pwd_ctx.verify(pw, pw_hash)

def _make_token(sub: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": sub, "role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

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
    bases = Column(Integer, nullable=True, default=0)  # keep as integer
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Schemas ---
class RegisterIn(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)
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
        password_hash=_hash(body.password),
        ingame_username=body.ingame_username,
        company_code=body.company_code,
        fio_apikey=body.fio_apikey,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": _make_token(user.username, user.role), "role": user.role}

@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = _get_user_by_username(db, body.username)
    if not user or not _verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": _make_token(user.username, user.role), "role": user.role}
