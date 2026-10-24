"""Needs: fastapi, httpx, mongomock, pyjwt (pip install -r requirements.txt)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip("fastapi")
pytest.importorskip("mongomock")
from fastapi.testclient import TestClient  # noqa: E402
import mongomock  # noqa: E402

from app import auth, config  # noqa: E402
from app.main import app  # noqa: E402
from app.roles import role_for_email  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "x" * 40)
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@x.com"})
    db = mongomock.MongoClient().db
    for sub, email in (("1", "boss@x.com"), ("2", "shopper@x.com")):
        db.users.insert_one({"google_sub": sub, "email": email, "name": email})
    app.dependency_overrides[auth.db_dep] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def as_user(c, sub):
    c.cookies.set(auth.COOKIE, auth.make_session_token(sub))
    return c


def test_role_comes_only_from_env():
    assert role_for_email(" Boss@X.com ", {"boss@x.com"}) == "admin"
    assert role_for_email("anyone@x.com", {"boss@x.com"}) == "customer"


def test_admin_routes_require_auth_and_admin_role(client):
    assert client.get("/api/admin/overview").status_code == 401
    assert as_user(client, "2").get("/api/admin/overview").status_code == 403
    assert as_user(client, "1").get("/api/admin/overview").status_code == 200


def test_customer_cannot_self_promote(client):
    r = as_user(client, "2").post("/api/auth/google", json={"credential": "bad", "role": "admin"})
    assert r.status_code == 401
    assert as_user(client, "2").get("/api/auth/me").json()["role"] == "customer"


def test_favorites_flow_and_isolation(client):
    c = as_user(client, "2")
    c.app.dependency_overrides[auth.db_dep]().events.insert_one(
        {"product_id": 7, "event_type": "view", "price": 1.0, "brand": "b", "category_code": "c"})
    assert c.post("/api/customer/favorites", json={"product_id": 999}).status_code == 404
    assert c.post("/api/customer/favorites", json={"product_id": 7}).status_code == 201
    assert len(c.get("/api/customer/favorites").json()) == 1
    assert len(as_user(client, "1").get("/api/customer/favorites").json()) == 0
