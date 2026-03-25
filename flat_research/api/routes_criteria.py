"""Criteria routes: GET/PUT search criteria for the current user."""

from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from flat_research.api.dependencies import get_current_user, get_db
from flat_research.db import SearchCriteria, User

router = APIRouter(prefix="/api/criteria", tags=["criteria"])


class CriteriaResponse(BaseModel):
    neighbourhoods: dict[str, list[str]]
    price_min: int
    price_max: int
    bedrooms_min: int
    bedrooms_max: int | None
    furnished: bool
    parking: bool
    move_in_after: date | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class CriteriaUpdate(BaseModel):
    neighbourhoods: dict[str, list[str]] | None = None
    price_min: int | None = None
    price_max: int | None = None
    bedrooms_min: int | None = None
    bedrooms_max: int | None = None
    furnished: bool | None = None
    parking: bool | None = None
    move_in_after: date | None = None


@router.get("", response_model=CriteriaResponse)
def get_criteria(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    criteria = db.query(SearchCriteria).filter(SearchCriteria.user_id == user.id).first()
    if not criteria:
        criteria = SearchCriteria(user_id=user.id)
        db.add(criteria)
        db.commit()
        db.refresh(criteria)
    return criteria


@router.put("", response_model=CriteriaResponse)
def update_criteria(body: CriteriaUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    criteria = db.query(SearchCriteria).filter(SearchCriteria.user_id == user.id).first()
    if not criteria:
        criteria = SearchCriteria(user_id=user.id)
        db.add(criteria)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(criteria, field, value)

    db.commit()
    db.refresh(criteria)
    return criteria
