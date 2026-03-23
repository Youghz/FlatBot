"""User profile routes: GET/PUT current user info."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from flat_research.api.dependencies import get_current_user, get_db
from flat_research.db import User

router = APIRouter(prefix="/api/me", tags=["user"])


class UserResponse(BaseModel):
    id: int
    email: str
    telegram_chat_id: str | None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    telegram_chat_id: str | None = None


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
