"""API справочника. Тесты идут в CI, где установлен FastAPI."""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402

client = TestClient(create_app())


def test_professions_list():
    data = client.get("/api/catalog/professions").json()

    assert [p["id"] for p in data] == ["backend-junior", "frontend-junior", "data-analyst-junior"]
    assert all(p["skills_count"] >= 6 for p in data)


def test_profession_skills_in_learning_order():
    response = client.get("/api/catalog/professions/frontend-junior")

    assert response.status_code == 200
    ids = [s["id"] for s in response.json()["skills"]]
    assert ids.index("html-css") < ids.index("javascript") < ids.index("react")


def test_unknown_profession_is_404():
    response = client.get("/api/catalog/professions/devops-senior")

    assert response.status_code == 404
    assert response.json()["detail"] == "Такой профессии нет в справочнике"


def test_all_skills_for_manual_choice():
    data = client.get("/api/catalog/skills").json()

    assert len(data) == 20
    assert {"id", "title", "why"} <= set(data[0])
