"""Tests for the FastAPI API routes."""

import pytest
from fastapi.testclient import TestClient

from flat_research.api import create_app
from flat_research.api.dependencies import get_db


@pytest.fixture
def client(db_session):
    """FastAPI test client wired to the SQLite test DB."""
    app = create_app()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _signup(client, email="test@example.com", password="password123"):
    return client.post("/api/auth/signup", json={"email": email, "password": password})


def _login(client, email="test@example.com", password="password123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _auth_header(client, email="test@example.com", password="password123"):
    _signup(client, email, password)
    resp = _login(client, email, password)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuthRoutes:
    def test_signup(self, client):
        resp = _signup(client)
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_signup_duplicate(self, client):
        _signup(client)
        resp = _signup(client)
        assert resp.status_code == 409

    def test_signup_short_password(self, client):
        resp = _signup(client, password="short")
        assert resp.status_code == 422

    def test_login_valid(self, client):
        _signup(client)
        resp = _login(client)
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_invalid(self, client):
        _signup(client)
        resp = _login(client, password="wrong")
        assert resp.status_code == 401

    def test_refresh(self, client):
        resp = _signup(client)
        refresh_token = resp.json()["refresh_token"]
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_invalid(self, client):
        resp = client.post("/api/auth/refresh", json={"refresh_token": "garbage"})
        assert resp.status_code == 401


class TestCriteriaRoutes:
    def test_get_default_criteria(self, client):
        headers = _auth_header(client)
        resp = client.get("/api/criteria", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["price_min"] == 1000
        assert data["price_max"] == 3000
        assert data["neighbourhoods"] == {}

    def test_update_criteria(self, client):
        headers = _auth_header(client)
        resp = client.put(
            "/api/criteria",
            headers=headers,
            json={
                "neighbourhoods": {"Villeray": ["villeray", "saint-michel"]},
                "price_min": 2000,
                "price_max": 2800,
                "bedrooms_min": 3,
                "furnished": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["price_min"] == 2000
        assert data["neighbourhoods"] == {"Villeray": ["villeray", "saint-michel"]}
        assert data["furnished"] is True

    def test_partial_update(self, client):
        headers = _auth_header(client)
        client.put("/api/criteria", headers=headers, json={"price_min": 1500})
        resp = client.put("/api/criteria", headers=headers, json={"furnished": True})
        data = resp.json()
        assert data["price_min"] == 1500
        assert data["furnished"] is True

    def test_unauthenticated(self, client):
        resp = client.get("/api/criteria")
        assert resp.status_code in (401, 403)


class TestListingsRoutes:
    def test_empty_listings(self, client):
        headers = _auth_header(client)
        resp = client.get("/api/listings", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["listings"] == []
        assert resp.json()["total"] == 0

    def test_unauthenticated(self, client):
        resp = client.get("/api/listings")
        assert resp.status_code in (401, 403)


class TestUserRoutes:
    def test_get_profile(self, client):
        headers = _auth_header(client)
        resp = client.get("/api/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"
        assert resp.json()["telegram_chat_id"] is None

    def test_update_telegram(self, client):
        headers = _auth_header(client)
        resp = client.put("/api/me", headers=headers, json={"telegram_chat_id": "123456789"})
        assert resp.status_code == 200
        assert resp.json()["telegram_chat_id"] == "123456789"
