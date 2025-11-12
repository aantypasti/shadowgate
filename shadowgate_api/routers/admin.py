from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import List, Optional
import os

from shadowgate_api.db import get_db
from shadowgate_api.routers.users import User
from shadowgate_api.auth_simple import hash_password

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# --- Auth config ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"

# --- Schemas ---
class UserOut(BaseModel):
    id: int
    username: str
    role: str
    ingame_username: Optional[str] = None
    company_code: Optional[str] = None
    fio_apikey: Optional[str] = None
    bases: Optional[int] = None

    class Config:
        orm_mode = True


class UserUpdateIn(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    ingame_username: Optional[str] = None
    company_code: Optional[str] = None
    fio_apikey: Optional[str] = None
    bases: Optional[int] = None


# --- Helpers ---
def _get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_current_admin(authorization: str = Header(None)):
    """
    Extracts and validates JWT token from Authorization header.
    Only allows access if role == 'admin'.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin privileges required")
        return payload  # payload contains sub (username) and role
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# --- Endpoints (admin-only) ---

@router.get("/users", response_model=List[UserOut], dependencies=[Depends(get_current_admin)])
def list_users(db: Session = Depends(get_db)):
    """Return all users in the system."""
    return db.query(User).all()


@router.get("/users/{user_id}", response_model=UserOut, dependencies=[Depends(get_current_admin)])
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Return a single user by ID."""
    user = _get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserOut, dependencies=[Depends(get_current_admin)])
def update_user(user_id: int, data: UserUpdateIn, db: Session = Depends(get_db)):
    """Update a user's fields (including password if given)."""
    user = _get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.username:
        user.username = data.username
    if data.role:
        user.role = data.role
    if data.ingame_username:
        user.ingame_username = data.ingame_username
    if data.company_code:
        user.company_code = data.company_code
    if data.fio_apikey:
        user.fio_apikey = data.fio_apikey
    if data.bases is not None:
        user.bases = data.bases
    if data.password:
        user.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", dependencies=[Depends(get_current_admin)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user by ID."""
    user = _get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": f"User {user.username} deleted successfully."}
