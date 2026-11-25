"""API опроса. Тесты идут в CI, где установлен FastAPI."""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402

client = TestClient(create_app())

NOVICE = {
    "goal": ["not-sure"],
    "interest": ["interface"],
    "languages": ["none"],
    "practice": ["html"],
    "topics": ["none"],
    "experience": ["none"],
}


def body(**chosen: list[str]) -> dict:
    full = {**NOVICE, **chosen}
    return {"answers": [{"question_id": q, "option_ids": ids} for q, ids in full.items()]}


def test_questions_without_hidden_logic():
    data = client.get("/api/survey/questions").json()

    assert len(data) == 6
    assert data[0]["id"] == "goal"
    assert all("skills" not in o and "profession" not in o for q in data for o in q["options"])


def test_result_for_novice():
    response = client.post("/api/survey/result", json=body())

    assert response.status_code == 200
    assert response.json() == {
        "profession": {"id": "frontend-junior", "title": "Junior Frontend-разработчик"},
        "skills": [{"id": "html-css", "title": "HTML и CSS"}],
    }


def test_skills_come_in_catalog_order():
    response = client.post("/api/survey/result", json=body(languages=["sql", "python"], practice=["git"]))

    assert [s["id"] for s in response.json()["skills"]] == ["git", "python", "sql"]


def test_wrong_answers_are_422_with_text():
    response = client.post("/api/survey/result", json=body(practice=["none", "git"]))

    assert response.status_code == 422
    assert "нельзя выбрать вместе с другими" in response.json()["detail"]


def test_missing_question_is_422():
    data = body()
    data["answers"] = data["answers"][:-1]

    response = client.post("/api/survey/result", json=data)

    assert response.status_code == 422
    assert response.json()["detail"] == "Ответьте на вопрос: «Что у вас уже есть?»"


def test_malformed_body_is_422():
    assert client.post("/api/survey/result", json={"answers": "всё"}).status_code == 422
