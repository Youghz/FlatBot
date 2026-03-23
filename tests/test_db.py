"""Tests for database models and helpers."""

from flat_research.db import (
    SearchCriteria,
    SeenListing,
    User,
    criteria_to_config,
    get_all_active_criteria,
    get_seen_listing_ids,
    mark_listings_seen,
)


def _create_user(db, email="test@example.com"):
    user = User(email=email, password_hash="fakehash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_criteria(db, user, **kwargs):
    defaults = {
        "user_id": user.id,
        "neighbourhoods": {"Villeray": ["villeray"]},
        "price_min": 2000,
        "price_max": 3000,
        "bedrooms_min": 3,
        "furnished": True,
        "parking": False,
    }
    defaults.update(kwargs)
    criteria = SearchCriteria(**defaults)
    db.add(criteria)
    db.commit()
    db.refresh(criteria)
    return criteria


class TestCriteriaToConfig:
    def test_basic_conversion(self, db_session):
        user = _create_user(db_session)
        criteria = _create_criteria(db_session, user)
        config = criteria_to_config(criteria)

        assert config["criteria"]["price_min"] == 2000
        assert config["criteria"]["price_max"] == 3000
        assert config["criteria"]["bedrooms_min"] == 3
        assert config["criteria"]["furnished"] is True
        assert config["criteria"]["parking"] is False
        assert config["criteria"]["neighbourhoods"] == {"Villeray": ["villeray"]}

    def test_optional_fields_absent(self, db_session):
        user = _create_user(db_session)
        criteria = _create_criteria(db_session, user)
        config = criteria_to_config(criteria)

        assert "bedrooms_max" not in config["criteria"]
        assert "move_in_before" not in config["criteria"]

    def test_optional_fields_present(self, db_session):
        from datetime import date

        user = _create_user(db_session)
        criteria = _create_criteria(db_session, user, bedrooms_max=5, move_in_before=date(2026, 9, 1))
        config = criteria_to_config(criteria)

        assert config["criteria"]["bedrooms_max"] == 5
        assert config["criteria"]["move_in_before"] == "2026-09-01"


class TestActiveUsers:
    def test_returns_active_users_with_criteria(self, db_session):
        user = _create_user(db_session)
        _create_criteria(db_session, user)

        results = get_all_active_criteria(db_session)
        assert len(results) == 1
        assert results[0][0].email == "test@example.com"

    def test_excludes_inactive_users(self, db_session):
        user = _create_user(db_session)
        user.is_active = False
        db_session.commit()
        _create_criteria(db_session, user)

        results = get_all_active_criteria(db_session)
        assert len(results) == 0

    def test_excludes_users_without_criteria(self, db_session):
        _create_user(db_session)
        results = get_all_active_criteria(db_session)
        assert len(results) == 0


class TestSeenListings:
    def test_mark_and_get(self, db_session):
        user = _create_user(db_session)
        mark_listings_seen(db_session, user.id, ["kijiji_123", "centris_456"])

        seen = get_seen_listing_ids(db_session, user.id)
        assert seen == {"kijiji_123", "centris_456"}

    def test_dedup_on_mark(self, db_session):
        user = _create_user(db_session)
        mark_listings_seen(db_session, user.id, ["kijiji_123"])
        mark_listings_seen(db_session, user.id, ["kijiji_123"])

        count = db_session.query(SeenListing).filter_by(user_id=user.id).count()
        assert count == 1

    def test_per_user_isolation(self, db_session):
        user1 = _create_user(db_session, "a@test.com")
        user2 = _create_user(db_session, "b@test.com")
        mark_listings_seen(db_session, user1.id, ["kijiji_123"])

        assert get_seen_listing_ids(db_session, user1.id) == {"kijiji_123"}
        assert get_seen_listing_ids(db_session, user2.id) == set()
