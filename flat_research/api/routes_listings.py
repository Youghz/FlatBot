"""Listings routes: GET seen listings for the current user."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from flat_research.api.dependencies import get_current_user, get_db
from flat_research.db import SeenListing, User

router = APIRouter(prefix="/api/listings", tags=["listings"])


class ListingEntry(BaseModel):
    listing_id: str
    notified_at: datetime

    model_config = {"from_attributes": True}


class ListingsResponse(BaseModel):
    listings: list[ListingEntry]
    total: int


@router.get("", response_model=ListingsResponse)
def get_listings(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(SeenListing).filter(SeenListing.user_id == user.id).order_by(desc(SeenListing.notified_at))
    total = query.count()
    listings = query.offset(offset).limit(limit).all()
    return ListingsResponse(listings=listings, total=total)
