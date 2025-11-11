from typing import List

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from shadowgate_api.db import get_db
from shadowgate_api.routers.users import User, SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/api/admin", tags=["Admin"])

def _current_admin(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if not username or role != "admin":
            raise HTTPException(status_code=403, detail="Admin privileges required")
        admin_user = db.query(User).filter(User.username == username).first()
        if not admin_user:
            raise HTTPException(status_code=401, detail="User not found")
        return admin_user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    ingame_username: str | None = None
    company_code: str | None = None
    role: str
    created_at: str | None = None

class RoleUpdate(BaseModel):
    role: str

@router.get("/users", response_model=List[UserOut])
def list_users(token: str, db: Session = Depends(get_db)):
    _current_admin(token, db)
    return db.query(User).all()

@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(user_id: int, body: RoleUpdate, token: str, db: Session = Depends(get_db)):
    _current_admin(token, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, token: str, db: Session = Depends(get_db)):
    _current_admin(token, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": f"User '{user.username}' deleted"}
