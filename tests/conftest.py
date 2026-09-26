import os

# Faster password hashing during tests only (must be set before importing the app)
os.environ["PBKDF2_ITERATIONS"] = "1000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Separate in-memory database for tests, so real data is never touched
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def register_and_login(client):
    """Returns a function that creates a user and returns auth headers."""

    def _register_and_login(email: str = "user@example.com", password: str = "password123"):
        response = client.post("/auth/register", json={"email": email, "password": password})
        assert response.status_code == 201, response.text

        response = client.post("/auth/login", data={"username": email, "password": password})
        assert response.status_code == 200, response.text

        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _register_and_login


@pytest.fixture
def auth_headers(register_and_login):
    """Auth headers for a default logged-in user."""
    return register_and_login()


@pytest.fixture
def make_expense(client, auth_headers):
    """Returns a function that creates an expense and returns it as JSON."""

    def _make_expense(headers: dict | None = None, **overrides):
        payload = {
            "title": "Lunch",
            "amount": 10.0,
            "category": "food",
            "spent_on": "2026-09-01",
        }
        payload.update(overrides)
        response = client.post("/expenses", json=payload, headers=headers or auth_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_expense