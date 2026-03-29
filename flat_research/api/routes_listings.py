"""Listings routes: GET matched listings, PATCH to correct fields."""

import logging
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from flat_research.api.dependencies import get_current_user, get_db
from flat_research.api.rate_limit import limiter
from flat_research.db import ListingRecord, SeenListing, User

logger = logging.getLogger(__name__)

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
    published_date: str
    surface_sqft: int
    notified_at: datetime

    model_config = {"from_attributes": True}


class ListingsResponse(BaseModel):
    listings: list[ListingDetail]
    total: int


class ListingUpdate(BaseModel):
    price: float | None = None
    bedrooms: int | None = None
    furnished: bool | None = None
    parking: bool | None = None
    neighbourhood: str | None = None
    move_in_date: str | None = None
    surface_sqft: int | None = None


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
                published_date=record.published_date,
                surface_sqft=record.surface_sqft,
                notified_at=notified_at,
            )
        )

    return ListingsResponse(listings=listings, total=total)


@router.patch("/{listing_id}", response_model=ListingDetail)
@limiter.limit("10/minute")
def update_listing(
    request: Request,
    listing_id: str,
    body: ListingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a listing's fields and create a test fixture from the correction."""
    # Verify user has seen this listing
    seen = db.query(SeenListing).filter(SeenListing.user_id == user.id, SeenListing.listing_id == listing_id).first()
    if not seen:
        raise HTTPException(status_code=404, detail="Listing not found")

    record = db.query(ListingRecord).filter(ListingRecord.listing_id == listing_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Apply corrections
    corrections = body.model_dump(exclude_unset=True)
    for field, value in corrections.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)

    # Create test fixture in background (don't block the response)
    def _create_fixture_bg():
        try:
            from flat_research.api.fixture_service import create_fixture

            create_fixture(record, corrections)
        except Exception as e:
            logger.error(f"Failed to create fixture for {listing_id}: {e}")

    threading.Thread(target=_create_fixture_bg, daemon=True).start()

    return ListingDetail(
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
        published_date=record.published_date,
        surface_sqft=record.surface_sqft,
        notified_at=seen.notified_at,
    )
