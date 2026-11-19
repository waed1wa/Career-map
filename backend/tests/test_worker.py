"""Фоновые задачи вызываются напрямую, без Redis: Celery выполняет задачу как обычную функцию."""

from app.worker import build_map, check_deadlines


def test_build_map_task_returns_steps():
    result = build_map("backend-junior", ["python", "git"])

    assert result["profession_id"] == "backend-junior"
    assert 6 <= len(result["steps"]) <= 8


def test_check_deadlines_runs():
    assert check_deadlines() == 0
