"""Статус задачи разбора для клиента: что видит студент на каждом состоянии Celery."""

import pytest

from app.modules.profile.job_status import QUEUE_FAILED, status_from_celery
from app.modules.profile.ports import JobState


@pytest.mark.parametrize("state", ["PENDING", "RECEIVED", "STARTED", "RETRY"])
def test_still_working(state):
    assert status_from_celery(state, None).state == JobState.PENDING


def test_done_with_skills():
    result = {"skills": [{"id": "sql", "title": "SQL и базы данных", "matched": "PostgreSQL"}]}

    status = status_from_celery("SUCCESS", result)

    assert status.state == JobState.DONE
    assert [(s.skill.value, s.matched) for s in status.skills] == [("sql", "PostgreSQL")]


def test_done_without_skills_is_still_done():
    """Ничего не нашли — это не ошибка: студент отметит навыки сам."""
    status = status_from_celery("SUCCESS", {"skills": []})

    assert status.state == JobState.DONE
    assert status.skills == ()


def test_bad_file_message_is_passed_to_student():
    status = status_from_celery("SUCCESS", {"error": "В файле нет текста — похоже, это скан"})

    assert status.state == JobState.FAILED
    assert status.error == "В файле нет текста — похоже, это скан"


@pytest.mark.parametrize(("state", "result"), [("FAILURE", None), ("REVOKED", None), ("SUCCESS", "мусор")])
def test_queue_failure_gives_general_message(state, result):
    status = status_from_celery(state, result)

    assert status.state == JobState.FAILED
    assert status.error == QUEUE_FAILED
