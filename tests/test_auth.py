"""Tests for authentication module."""

import pytest

from flat_research.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mysecretpassword")
        assert hashed != "mysecretpassword"
        assert verify_password("mysecretpassword", hashed)

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)


class TestJWT:
    def test_access_token_roundtrip(self):
        token = create_access_token(42)
        user_id = decode_token(token, expected_type="access")
        assert user_id == 42

    def test_refresh_token_roundtrip(self):
        token = create_refresh_token(42)
        user_id = decode_token(token, expected_type="refresh")
        assert user_id == 42

    def test_wrong_type_rejected(self):
        token = create_refresh_token(42)
        assert decode_token(token, expected_type="access") is None

    def test_invalid_token_rejected(self):
        assert decode_token("garbage.token.here") is None


class TestCreateUser:
    def test_create_user(self, db_session):
        user = create_user(db_session, "test@example.com", "password123")
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash != "password123"

    def test_duplicate_email_raises(self, db_session):
        create_user(db_session, "test@example.com", "password123")
        with pytest.raises(ValueError, match="already registered"):
            create_user(db_session, "test@example.com", "otherpass")


class TestAuthenticateUser:
    def test_valid_credentials(self, db_session):
        create_user(db_session, "test@example.com", "password123")
        user = authenticate_user(db_session, "test@example.com", "password123")
        assert user is not None
        assert user.email == "test@example.com"

    def test_wrong_password(self, db_session):
        create_user(db_session, "test@example.com", "password123")
        assert authenticate_user(db_session, "test@example.com", "wrong") is None

    def test_unknown_email(self, db_session):
        assert authenticate_user(db_session, "nobody@example.com", "password") is None
