"""Database models and session management."""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    telegram_chat_id = Column(String(64), nullable=True)
    telegram_link_code = Column(String(10), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    criteria = relationship("SearchCriteria", back_populates="user", uselist=False, cascade="all, delete-orphan")
    seen_listings = relationship("SeenListing", back_populates="user", cascade="all, delete-orphan")


class SearchCriteria(Base):
    __tablename__ = "search_criteria"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    neighbourhoods = Column(JSON, nullable=False, default=dict)
    price_min = Column(Integer, nullable=False, default=1000)
    price_max = Column(Integer, nullable=False, default=3000)
    bedrooms_min = Column(Integer, nullable=False, default=1)
    bedrooms_max = Column(Integer, nullable=True)
    furnished = Column(Boolean, nullable=False, default=False)
    parking = Column(Boolean, nullable=False, default=False)
    move_in_after = Column(Date, nullable=True)
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="criteria")


class ListingRecord(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True)
    listing_id = Column(String(255), unique=True, nullable=False, index=True)
    source = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False, default="")
    price = Column(Float, nullable=False, default=0.0)
    url = Column(String(1000), nullable=False, default="")
    address = Column(String(500), nullable=False, default="")
    neighbourhood = Column(String(100), nullable=False, default="")
    bedrooms = Column(Integer, nullable=False, default=0)
    furnished = Column(Boolean, nullable=False, default=False)
    parking = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=False, default="")
    move_in_date = Column(String(20), nullable=False, default="")
    published_date = Column(String(20), nullable=False, default="")
    surface_sqft = Column(Integer, nullable=False, default=0)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    seen_by = relationship("SeenListing", back_populates="listing")


class SeenListing(Base):
    __tablename__ = "seen_listings"
    __table_args__ = (UniqueConstraint("user_id", "listing_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id = Column(String(255), ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=False)
    notified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="seen_listings")
    listing = relationship("ListingRecord", back_populates="seen_by")


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        database_url = os.environ.get("DATABASE_URL", "postgresql://localhost/flatbot")
        _engine = create_engine(database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal


def get_db() -> Session:
    """Create a new database session."""
    factory = get_session_factory()
    return factory()


def criteria_to_config(criteria: SearchCriteria) -> dict:
    """Convert a SearchCriteria DB row to the config dict format matches_criteria() expects."""
    config = {
        "criteria": {
            "neighbourhoods": criteria.neighbourhoods or {},
            "price_min": criteria.price_min,
            "price_max": criteria.price_max,
            "bedrooms_min": criteria.bedrooms_min,
            "furnished": criteria.furnished,
            "parking": criteria.parking,
        }
    }
    if criteria.bedrooms_max is not None:
        config["criteria"]["bedrooms_max"] = criteria.bedrooms_max
    if criteria.move_in_after is not None:
        config["criteria"]["move_in_after"] = criteria.move_in_after.isoformat()
    return config


def get_all_active_criteria(db: Session) -> list[tuple[User, SearchCriteria]]:
    """Load all active users with their search criteria."""
    return db.query(User, SearchCriteria).join(SearchCriteria).filter(User.is_active.is_(True)).all()


def get_seen_listing_ids(db: Session, user_id: int) -> set[str]:
    """Get all listing IDs already seen by a user."""
    rows = db.query(SeenListing.listing_id).filter(SeenListing.user_id == user_id).all()
    return {r[0] for r in rows}


def save_listings(db: Session, listings: list) -> None:
    """Save scraped listings to DB. Skips duplicates by listing_id."""
    existing_ids = {r[0] for r in db.query(ListingRecord.listing_id).all()}
    for listing in listings:
        if listing.listing_id not in existing_ids:
            # "semi" → True, None → False (DB requires non-null boolean)
            from flat_research.parsing import coerce_bool

            furnished = coerce_bool(listing.furnished)
            parking = coerce_bool(listing.parking)
            db.add(
                ListingRecord(
                    listing_id=listing.listing_id,
                    source=listing.source,
                    title=listing.title,
                    price=listing.price,
                    url=listing.url,
                    address=listing.address,
                    neighbourhood=listing.neighbourhood,
                    bedrooms=listing.bedrooms,
                    furnished=furnished,
                    parking=parking,
                    description=listing.description,
                    move_in_date=listing.move_in_date or "",
                    published_date=listing.published_date or "",
                    surface_sqft=listing.surface_sqft or 0,
                )
            )
            existing_ids.add(listing.listing_id)
    db.commit()


def mark_listings_seen(db: Session, user_id: int, listing_ids: list[str]) -> None:
    """Record that a user has been notified about these listings."""
    existing = get_seen_listing_ids(db, user_id)
    for lid in listing_ids:
        if lid not in existing:
            db.add(SeenListing(user_id=user_id, listing_id=lid))
    db.commit()
