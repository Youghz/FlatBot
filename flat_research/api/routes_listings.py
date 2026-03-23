"""Listings routes: GET matched listings for the current user."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from flat_research.api.dependencies import get_current_user, get_db
from flat_research.db import ListingRecord, SeenListing, User

router = APIRouter(prefix="/api/listings", tags=["listings"])


class ListingDetail(BaseModel):
    listing_id: str
    source: str
    title: str
    price: float
    url: str
    address: str
    neighbourhood: str
    bedrooms: int
    furnished: bool
    parking: bool
    description: str
    move_in_date: str
    notified_at: datetime

    model_config = {"from_attributes": True}


class ListingsResponse(BaseModel):
    listings: list[ListingDetail]
    total: int


@router.get("", response_model=ListingsResponse)
def get_listings(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(ListingRecord, SeenListing.notified_at)
        .join(SeenListing, SeenListing.listing_id == ListingRecord.listing_id)
        .filter(SeenListing.user_id == user.id)
        .order_by(desc(SeenListing.notified_at))
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    listings = []
    for record, notified_at in rows:
        listings.append(
            ListingDetail(
                listing_id=record.listing_id,
                source=record.source,
                title=record.title,
                price=record.price,
                url=record.url,
                address=record.address,
                neighbourhood=record.neighbourhood,
                bedrooms=record.bedrooms,
                furnished=record.furnished,
                parking=record.parking,
                description=record.description,
                move_in_date=record.move_in_date,
                notified_at=notified_at,
            )
        )

    return ListingsResponse(listings=listings, total=total)
