"""Smoke-тест: приложение поднимается, health отвечает, демо-карта строится."""

from fastapi.testclient import TestClient

from app import main
from app.main import create_app


def test_health_reports_degraded_without_services(monkeypatch):
    monkeypatch.setattr(main, "database_is_alive", lambda: False)
    monkeypatch.setattr(main, "redis_is_alive", lambda: False)
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


def test_health_ok_when_services_alive(monkeypatch):
    monkeypatch.setattr(main, "database_is_alive", lambda: True)
    monkeypatch.setattr(main, "redis_is_alive", lambda: True)
    client = TestClient(create_app())

    assert client.get("/api/health").json()["status"] == "ok"


def test_demo_map_endpoint():
    client = TestClient(create_app())

    data = client.get("/api/career-map/demo").json()

    assert 6 <= len(data["steps"]) <= 8
    assert sum(1 for s in data["steps"] if s["status"] == "current") == 1


def test_not_ready_modules_answer_501():
    client = TestClient(create_app())

    assert client.get("/api/auth/me").status_code == 501
