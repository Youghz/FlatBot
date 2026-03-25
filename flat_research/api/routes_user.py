"""User profile routes: GET/PUT current user info, change password."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from flat_research.api.dependencies import get_current_user, get_db
from flat_research.auth import hash_password, verify_password
from flat_research.db import User

router = APIRouter(prefix="/api/me", tags=["user"])


class UserResponse(BaseModel):
    id: int
    email: str
    telegram_chat_id: str | None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    telegram_chat_id: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)):
    return user


@router.put("", response_model=UserResponse)
def update_profile(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/password")
def change_password(body: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=422, detail="Le nouveau mot de passe doit faire au moins 8 caractères")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Mot de passe modifié"}
