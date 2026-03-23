"""Database models and session management."""

import os
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
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
    created_at = Column(DateTime, default=datetime.utcnow)
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
    move_in_before = Column(Date, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="criteria")


class SeenListing(Base):
    __tablename__ = "seen_listings"
    __table_args__ = (UniqueConstraint("user_id", "listing_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id = Column(String(255), nullable=False)
    notified_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="seen_listings")


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
    if criteria.move_in_before is not None:
        config["criteria"]["move_in_before"] = criteria.move_in_before.isoformat()
    return config


def get_all_active_criteria(db: Session) -> list[tuple[User, SearchCriteria]]:
    """Load all active users with their search criteria."""
    return db.query(User, SearchCriteria).join(SearchCriteria).filter(User.is_active.is_(True)).all()


def get_seen_listing_ids(db: Session, user_id: int) -> set[str]:
    """Get all listing IDs already seen by a user."""
    rows = db.query(SeenListing.listing_id).filter(SeenListing.user_id == user_id).all()
    return {r[0] for r in rows}


def mark_listings_seen(db: Session, user_id: int, listing_ids: list[str]) -> None:
    """Record that a user has been notified about these listings."""
    existing = get_seen_listing_ids(db, user_id)
    for lid in listing_ids:
        if lid not in existing:
            db.add(SeenListing(user_id=user_id, listing_id=lid))
    db.commit()
