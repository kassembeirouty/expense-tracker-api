from app.security import create_access_token, hash_password, verify_password


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("password123")
    assert hashed != "password123"
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("password123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_same_password_gives_different_hashes():
    # A random salt is used each time
    assert hash_password("password123") != hash_password("password123")


def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"email": "  Kassem@Example.COM ", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "kassem@example.com"  # normalized
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email_is_rejected(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    response = client.post(
        "/auth/register",
        json={"email": "A@EXAMPLE.com", "password": "password456"},
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert response.status_code == 422


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/auth/register", json={"email": "not-an-email", "password": "password123"}
    )
    assert response.status_code == 422


def test_login_returns_token(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    response = client.post(
        "/auth/login", data={"username": "a@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    response = client.post(
        "/auth/login", data={"username": "a@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_unknown_email(client):
    response = client.post(
        "/auth/login", data={"username": "ghost@example.com", "password": "password123"}
    )
    assert response.status_code == 401
    # Same message as a wrong password, so emails can't be discovered
    assert response.json()["detail"] == "Incorrect email or password"


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_me_without_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_fake_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_with_token_for_deleted_or_missing_user(client):
    token = create_access_token("9999")  # valid signature, but no such user
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401