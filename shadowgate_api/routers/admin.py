from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from shadowgate_api.db import get_db
from shadowgate_api.routers.users import User  # reuse same ORM model
from shadowgate_api.auth_simple import hash_password

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# --- Schemas ---
class UserOut(BaseModel):
    id: int
    username: str
    role: str
    ingame_username: str | None = None
    company_code: str | None = None
    fio_apikey: str | None = None
    bases: int | None = None

    class Config:
        orm_mode = True

class UserUpdateIn(BaseModel):
    username: str
    password: str | None = None
    role: str | None = None
    ingame_username: str | None = None
    company_code: str | None = None
    fio_apikey: str | None = None
    bases: int | None = None

# --- Helpers ---
def _get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# --- Endpoints ---

@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    """Return all users in the system."""
    return db.query(User).all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Return a single user by ID."""
    user = _get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserOut)
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


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user by ID."""
    user = _get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": f"User {user.username} deleted successfully."}
