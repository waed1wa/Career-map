"""API входа целиком: регистрация → вход → «кто я». Хранилище подменяем на память, база не нужна."""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.modules.auth.ports import InMemoryUserRepository  # noqa: E402
from app.modules.auth.router import get_auth_service  # noqa: E402
from app.modules.auth.security import PasswordHasher, TokenService  # noqa: E402
from app.modules.auth.service import AuthService  # noqa: E402

STUDENT = {"email": "student@mail.ru", "password": "secret123", "role": "student", "consent": True}


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    service = AuthService(
        InMemoryUserRepository(),
        PasswordHasher(iterations=1_000),
        TokenService("test-secret-test-secret-test-secret", 3600),
    )
    app.dependency_overrides[get_auth_service] = lambda: service
    return TestClient(app)


def test_register_login_me(client):
    created = client.post("/api/auth/register", json=STUDENT)
    assert created.status_code == 201

    login = client.post("/api/auth/login", json={"email": "student@mail.ru", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "student"


def test_register_twice_gives_409(client):
    client.post("/api/auth/register", json=STUDENT)
    assert client.post("/api/auth/register", json=STUDENT).status_code == 409


def test_register_without_consent_gives_422(client):
    assert client.post("/api/auth/register", json={**STUDENT, "consent": False}).status_code == 422


def test_wrong_password_gives_401(client):
    client.post("/api/auth/register", json=STUDENT)
    response = client.post("/api/auth/login", json={"email": "student@mail.ru", "password": "wrong1234"})
    assert response.status_code == 401


def test_me_without_token_gives_401(client):
    assert client.get("/api/auth/me").status_code == 401
